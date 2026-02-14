from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import QuotePoint, QuoteSeries, QuoteSnapshot, RefreshReport


def _make_refresh_report(quotes_count: int) -> RefreshReport:
    now = datetime.now(timezone.utc)
    return RefreshReport(
        started_at=now,
        finished_at=now,
        duration_ms=1,
        total_events=0,
        live_events=0,
        seed_events=0,
        quote_assets=quotes_count,
        source_errors=[],
    )


@contextmanager
def _prepare_app(monkeypatch, *, quotes: dict[str, QuoteSnapshot] | None = None):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("ENABLE_MARKET_QUOTES", "true")

    import app.api as api_module

    startup_quotes = dict(quotes or {})

    async def _fake_refresh(store, config) -> RefreshReport:
        store.replace_events([])
        store.replace_quotes(dict(startup_quotes))
        return _make_refresh_report(len(startup_quotes))

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)
    with TestClient(create_app()) as client:
        yield client


def test_asset_quote_uses_cached_snapshot(monkeypatch) -> None:
    snapshot = QuoteSnapshot(
        asset_id="AAPL",
        price=189.5,
        change=1.2,
        change_pct=0.64,
        currency="USD",
        as_of=datetime(2026, 2, 14, 1, 0, tzinfo=timezone.utc),
        source="yahoo",
        is_fallback=False,
    )
    with _prepare_app(monkeypatch, quotes={"AAPL": snapshot}) as client:
        resp = client.get("/assets/AAPL/quote")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["asset_id"] == "AAPL"
        assert payload["price"] == 189.5
        assert payload["source"] == "yahoo"
        assert payload["is_fallback"] is False


def test_asset_quote_falls_back_when_live_snapshot_missing(monkeypatch) -> None:
    import app.api as api_module

    async def _fake_fetch_snapshots(_config, *, asset_ids=None):
        return {}

    monkeypatch.setattr(api_module, "fetch_quote_snapshots", _fake_fetch_snapshots)

    with _prepare_app(monkeypatch, quotes={}) as client:
        resp = client.get("/assets/AAPL/quote")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["asset_id"] == "AAPL"
        assert payload["source"] == "seed"
        assert payload["is_fallback"] is True
        assert payload["price"] > 0


def test_asset_series_and_chart_prefer_live_series(monkeypatch) -> None:
    import app.api as api_module

    live_series = QuoteSeries(
        asset_id="AAPL",
        range="1M",
        source="yahoo",
        is_fallback=False,
        points=[
            QuotePoint(time=datetime(2024, 1, 1, tzinfo=timezone.utc), value=180.2),
            QuotePoint(time=datetime(2024, 1, 2, tzinfo=timezone.utc), value=181.7),
        ],
    )

    async def _fake_fetch_series(_config, *, asset_id: str, range_key: str):
        assert asset_id == "AAPL"
        assert range_key == "1M"
        return live_series

    monkeypatch.setattr(api_module, "fetch_quote_series", _fake_fetch_series)

    with _prepare_app(monkeypatch, quotes={}) as client:
        resp_series = client.get("/assets/AAPL/series", params={"range": "1M"})
        assert resp_series.status_code == 200
        payload_series = resp_series.json()
        assert payload_series["source"] == "yahoo"
        assert payload_series["is_fallback"] is False
        assert payload_series["points"][0]["value"] == 180.2

        resp_chart = client.get("/assets/AAPL/chart", params={"range": "1M"})
        assert resp_chart.status_code == 200
        payload_chart = resp_chart.json()
        assert payload_chart["source"] == "yahoo"
        assert payload_chart["isFallback"] is False
        assert payload_chart["series"][0]["date"] == "2024-01-01"
        assert payload_chart["series"][0]["value"] == 180.2


def test_asset_chart_falls_back_when_live_series_missing(monkeypatch) -> None:
    import app.api as api_module

    async def _fake_fetch_series(_config, *, asset_id: str, range_key: str):
        return None

    monkeypatch.setattr(api_module, "fetch_quote_series", _fake_fetch_series)

    with _prepare_app(monkeypatch, quotes={}) as client:
        resp_chart = client.get("/assets/AAPL/chart", params={"range": "1M"})
        assert resp_chart.status_code == 200
        payload_chart = resp_chart.json()
        assert payload_chart["source"] == "seed"
        assert payload_chart["isFallback"] is True
        assert len(payload_chart["series"]) > 0


def test_asset_series_rejects_invalid_range(monkeypatch) -> None:
    with _prepare_app(monkeypatch, quotes={}) as client:
        resp = client.get("/assets/AAPL/series", params={"range": "2W"})
        assert resp.status_code == 400
        payload = resp.json()
        assert payload["detail"] == "Invalid range: 2W. Use one of: 1D, 1W, 1M, 1Y."
