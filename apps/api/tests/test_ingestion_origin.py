from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.config import AppConfig
from app.models import DataOrigin, Event, EventEvidence
from app.services.ingestion import dedupe_events, refresh_store
from app.state import InMemoryStore


def _make_event(*, event_id: str, headline: str, data_origin: DataOrigin, hour: int) -> Event:
    event_time = datetime(2026, 2, 9, hour, 0, tzinfo=timezone.utc)
    return Event(
        event_id=event_id,
        event_time=event_time,
        ingest_time=event_time,
        source_type="news",
        publisher="Test Publisher",
        headline=headline,
        summary="summary",
        event_type="risk",
        markets=["US"],
        tickers=["AAPL"],
        instruments=[],
        sectors=["Tech"],
        numbers=[],
        stance="neutral",
        impact=60,
        confidence=0.7,
        impact_chain=[],
        evidence=[
            EventEvidence(
                quote_id=f"q-{event_id}",
                source_url="https://example.com",
                title=headline,
                published_at=event_time,
                excerpt="excerpt",
            )
        ],
        related_event_ids=None,
        data_origin=data_origin,
    )


def _base_env(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("ENABLE_RSS", "false")
    monkeypatch.setenv("ENABLE_EDGAR", "false")
    monkeypatch.setenv("ENABLE_H10", "false")
    monkeypatch.setenv("ENABLE_TREASURY", "false")
    monkeypatch.setenv("ENABLE_FRED", "false")
    monkeypatch.setenv("ENABLE_HKEX", "false")
    monkeypatch.setenv("ENABLE_HKMA", "false")


def test_refresh_store_uses_live_when_available(monkeypatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("ENABLE_LIVE_SOURCES", "true")
    monkeypatch.setenv("ENABLE_RSS", "true")
    monkeypatch.setenv("ENABLE_SEED_DATA", "true")
    monkeypatch.setenv("SEED_ONLY_WHEN_NO_LIVE", "true")

    import app.services.ingestion as ingestion_module

    live_event = _make_event(event_id="evt-live", headline="live headline", data_origin="live", hour=9)
    seed_event = _make_event(event_id="evt-seed", headline="seed headline", data_origin="seed", hour=8)

    async def _fake_rss(_config):
        return [live_event]

    monkeypatch.setattr(ingestion_module, "fetch_rss_events", _fake_rss)
    monkeypatch.setattr(ingestion_module, "build_seed_events", lambda count=80: [seed_event])

    config = AppConfig.from_env()
    store = InMemoryStore()
    asyncio.run(refresh_store(store, config))

    assert len(store.events) == 1
    assert store.events[0].data_origin == "live"


def test_refresh_store_falls_back_to_seed_without_live(monkeypatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("ENABLE_LIVE_SOURCES", "false")
    monkeypatch.setenv("ENABLE_SEED_DATA", "true")
    monkeypatch.setenv("SEED_ONLY_WHEN_NO_LIVE", "true")

    import app.services.ingestion as ingestion_module

    seed_event = _make_event(event_id="evt-seed", headline="seed headline", data_origin="seed", hour=8)
    monkeypatch.setattr(ingestion_module, "build_seed_events", lambda count=80: [seed_event])

    config = AppConfig.from_env()
    store = InMemoryStore()
    asyncio.run(refresh_store(store, config))

    assert len(store.events) == 1
    assert store.events[0].data_origin == "seed"


def test_dedupe_events_prefers_live_on_same_headline() -> None:
    live_event = _make_event(event_id="evt-live", headline="same headline", data_origin="live", hour=8)
    seed_event = _make_event(event_id="evt-seed", headline="same headline", data_origin="seed", hour=12)

    deduped = dedupe_events([seed_event, live_event])
    assert len(deduped) == 1
    assert deduped[0].event_id == "evt-live"
    assert deduped[0].data_origin == "live"
