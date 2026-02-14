from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import QuoteSnapshot


@contextmanager
def _prepare_app(monkeypatch, snapshot: QuoteSnapshot):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("ENABLE_LIVE_SOURCES", "false")
    monkeypatch.setenv("ENABLE_SEED_DATA", "false")
    monkeypatch.setenv("ENABLE_MARKET_QUOTES", "true")

    import app.services.ingestion as ingestion_module

    async def _fake_fetch_quote_snapshots(_config, *, asset_ids=None):
        if asset_ids and "AAPL" not in asset_ids:
            return {}
        return {"AAPL": snapshot}

    monkeypatch.setattr(ingestion_module, "fetch_quote_snapshots", _fake_fetch_quote_snapshots)

    with TestClient(create_app()) as client:
        yield client


def test_quotes_pipeline_populates_store_and_dashboard(monkeypatch) -> None:
    snapshot = QuoteSnapshot(
        asset_id="AAPL",
        price=188.88,
        change=2.31,
        change_pct=1.24,
        currency="USD",
        as_of=datetime(2026, 2, 14, 8, 30, tzinfo=timezone.utc),
        source="yahoo",
        is_fallback=False,
    )

    with _prepare_app(monkeypatch, snapshot) as client:
        quote_resp = client.get("/assets/AAPL/quote")
        assert quote_resp.status_code == 200
        quote_payload = quote_resp.json()
        assert quote_payload["asset_id"] == "AAPL"
        assert quote_payload["source"] == "yahoo"
        assert quote_payload["is_fallback"] is False
        assert quote_payload["price"] == 188.88

        summary_resp = client.get("/dashboard/summary")
        assert summary_resp.status_code == 200
        summary_payload = summary_resp.json()
        aapl = next(asset for asset in summary_payload["key_assets"] if asset["id"] == "AAPL")
        assert aapl["value"] == 188.88
        assert aapl["changePct"] == 1.24

        refresh_resp = client.post("/admin/refresh")
        assert refresh_resp.status_code == 200
        refresh_payload = refresh_resp.json()
        assert refresh_payload["report"]["quote_assets"] == 1
