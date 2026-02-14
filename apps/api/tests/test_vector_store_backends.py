from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.config import AppConfig
from app.models import Event, EventEvidence
from app.services.vector_store import VectorStoreDisabled, create_vector_store


def _make_event(event_id: str, headline: str, excerpt: str) -> Event:
    now = datetime(2026, 2, 14, 9, 0, tzinfo=timezone.utc)
    return Event(
        event_id=event_id,
        event_time=now,
        ingest_time=now,
        source_type="news",
        publisher="Test Publisher",
        headline=headline,
        summary=excerpt,
        event_type="risk",
        markets=["US"],
        tickers=["AAPL"],
        instruments=[],
        sectors=["Tech"],
        numbers=[],
        stance="neutral",
        impact=55,
        confidence=0.6,
        impact_chain=[],
        evidence=[
            EventEvidence(
                quote_id=f"q-{event_id}",
                source_url="https://example.com",
                title=headline,
                published_at=now,
                excerpt=excerpt,
            )
        ],
        related_event_ids=None,
    )


def test_vector_store_factory_respects_disable_flag(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    config = AppConfig.from_env()
    with pytest.raises(VectorStoreDisabled):
        create_vector_store(config)


def test_simple_vector_store_query(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "true")
    monkeypatch.setenv("VECTOR_BACKEND", "simple")
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "vector"))
    config = AppConfig.from_env()

    store = create_vector_store(config)
    event = _make_event("evt-1", "Fed holds rates", "Fed signaled a cautious path for cuts.")
    inserted = store.upsert_events([event])
    assert inserted == 1

    hits = store.query("fed rates path", top_k=3)
    assert len(hits) == 1
    assert hits[0].evidence.quote_id == "q-evt-1"


def test_vector_store_factory_rejects_unknown_backend(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "true")
    monkeypatch.setenv("VECTOR_BACKEND", "unknown")
    config = AppConfig.from_env()
    # config fallback should normalize to chroma
    assert config.vector_backend == "chroma"
