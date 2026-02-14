from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import Event, EventEvidence, QuotePoint, QuoteSeries, QuoteSnapshot, RefreshReport


def _make_event(event_id: str) -> Event:
    now = datetime.now(timezone.utc)
    return Event(
        event_id=event_id,
        event_time=now,
        ingest_time=now,
        source_type="news",
        publisher="Test Publisher",
        headline="Asset profile event",
        summary="summary",
        event_type="risk",
        markets=["US"],
        tickers=["AAPL"],
        instruments=[],
        sectors=["Tech"],
        numbers=[],
        stance="neutral",
        impact=55,
        confidence=0.7,
        impact_chain=[],
        evidence=[
            EventEvidence(
                quote_id=f"q-{event_id}",
                source_url="https://example.com",
                title="Asset profile event",
                published_at=now,
                excerpt="excerpt",
            )
        ],
        related_event_ids=None,
    )


def _make_refresh_report(quotes_count: int) -> RefreshReport:
    now = datetime.now(timezone.utc)
    return RefreshReport(
        started_at=now,
        finished_at=now,
        duration_ms=1,
        total_events=1,
        live_events=1,
        seed_events=0,
        quote_assets=quotes_count,
        source_errors=[],
    )


@contextmanager
def _prepare_app(monkeypatch, events: list[Event], quotes: dict[str, QuoteSnapshot] | None = None):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("ENABLE_MARKET_QUOTES", "true")

    import app.api as api_module

    startup_quotes = dict(quotes or {})

    async def _fake_refresh(store, config) -> RefreshReport:
        store.replace_events(events)
        store.replace_quotes(dict(startup_quotes))
        return _make_refresh_report(len(startup_quotes))

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)
    with TestClient(create_app()) as client:
        yield client


def test_asset_profile_uses_live_quote_and_series(monkeypatch) -> None:
    import app.api as api_module

    async def _fake_fetch_snapshots(_config, *, asset_ids=None):
        return {
            "AAPL": QuoteSnapshot(
                asset_id="AAPL",
                price=191.2,
                change=1.1,
                change_pct=0.58,
                currency="USD",
                as_of=datetime(2026, 2, 14, 8, 30, tzinfo=timezone.utc),
                source="yahoo",
                is_fallback=False,
            )
        }

    async def _fake_fetch_series(_config, *, asset_id: str, range_key: str):
        return QuoteSeries(
            asset_id=asset_id,
            range=range_key,
            source="yahoo",
            is_fallback=False,
            points=[
                QuotePoint(time=datetime(2026, 2, 13, tzinfo=timezone.utc), value=189.7),
                QuotePoint(time=datetime(2026, 2, 14, tzinfo=timezone.utc), value=191.2),
            ],
        )

    monkeypatch.setattr(api_module, "fetch_quote_snapshots", _fake_fetch_snapshots)
    monkeypatch.setattr(api_module, "fetch_quote_series", _fake_fetch_series)

    with _prepare_app(monkeypatch, [_make_event("evt-1")], quotes={}) as client:
        resp = client.get("/assets/AAPL/profile", params={"range": "1M"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["asset_id"] == "AAPL"
        assert payload["quote"]["source"] == "yahoo"
        assert payload["quote"]["is_fallback"] is False
        assert payload["series"]["source"] == "yahoo"
        assert payload["series"]["is_fallback"] is False
        metric_map = {item["metric_id"]: item for item in payload["metrics"]}
        assert metric_map["spot_price"]["unit"] == "USD"
        assert metric_map["spot_price"]["value"] == 191.2
        assert metric_map["change_abs"]["value"] == 1.1
        assert metric_map["change_pct"]["value"] == 0.58
        assert payload["recent_events"][0]["event_id"] == "evt-1"


def test_asset_profile_falls_back_when_live_unavailable(monkeypatch) -> None:
    import app.api as api_module

    async def _fake_fetch_snapshots(_config, *, asset_ids=None):
        return {}

    async def _fake_fetch_series(_config, *, asset_id: str, range_key: str):
        return None

    monkeypatch.setattr(api_module, "fetch_quote_snapshots", _fake_fetch_snapshots)
    monkeypatch.setattr(api_module, "fetch_quote_series", _fake_fetch_series)

    with _prepare_app(monkeypatch, [_make_event("evt-2")], quotes={}) as client:
        resp = client.get("/assets/AAPL/profile", params={"range": "1M"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["quote"]["source"] == "seed"
        assert payload["quote"]["is_fallback"] is True
        assert payload["series"]["source"] == "seed"
        assert payload["series"]["is_fallback"] is True
        metric_map = {item["metric_id"]: item for item in payload["metrics"]}
        assert metric_map["spot_price"]["is_fallback"] is True


def test_asset_profile_rates_change_is_normalized_to_bps(monkeypatch) -> None:
    import app.api as api_module

    async def _fake_fetch_snapshots(_config, *, asset_ids=None):
        return {
            "US10Y": QuoteSnapshot(
                asset_id="US10Y",
                price=4.05,
                change=0.02,
                change_pct=0.5,
                currency="USD",
                as_of=datetime(2026, 2, 14, 8, 30, tzinfo=timezone.utc),
                source="yahoo",
                is_fallback=False,
            )
        }

    async def _fake_fetch_series(_config, *, asset_id: str, range_key: str):
        return QuoteSeries(
            asset_id=asset_id,
            range=range_key,
            source="yahoo",
            is_fallback=False,
            points=[QuotePoint(time=datetime(2026, 2, 14, tzinfo=timezone.utc), value=4.05)],
        )

    monkeypatch.setattr(api_module, "fetch_quote_snapshots", _fake_fetch_snapshots)
    monkeypatch.setattr(api_module, "fetch_quote_series", _fake_fetch_series)

    with _prepare_app(monkeypatch, [_make_event("evt-3")], quotes={}) as client:
        resp = client.get("/assets/US10Y/profile", params={"range": "1M"})
        assert resp.status_code == 200
        payload = resp.json()
        metric_map = {item["metric_id"]: item for item in payload["metrics"]}
        assert metric_map["spot_price"]["unit"] == "pct"
        assert metric_map["change_abs"]["unit"] == "bps"
        assert metric_map["change_abs"]["value"] == 2.0
