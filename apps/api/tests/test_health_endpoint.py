from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import Event, EventEvidence, RefreshReport


def _make_event(event_id: str) -> Event:
    now = datetime(2026, 2, 14, 9, 0, tzinfo=timezone.utc)
    return Event(
        event_id=event_id,
        event_time=now,
        ingest_time=now,
        source_type="news",
        publisher="Test Publisher",
        headline="Health endpoint test event",
        summary="summary",
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
                title="Health endpoint test event",
                published_at=now,
                excerpt="excerpt",
            )
        ],
        related_event_ids=None,
    )


@contextmanager
def _prepare_app(monkeypatch, events: list[Event]):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("TIMEZONE", "Asia/Hong_Kong")

    import app.api as api_module

    async def _fake_refresh(store, config) -> RefreshReport:
        store.replace_events(events)
        return RefreshReport(
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            duration_ms=120,
            total_events=len(events),
            live_events=len(events),
            seed_events=0,
            source_errors=[],
        )

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)
    with TestClient(create_app()) as client:
        yield client


def test_health_includes_store_and_vector_status(monkeypatch) -> None:
    with _prepare_app(monkeypatch, [_make_event("evt-1")]) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ok"] is True
        assert payload["store_events"] == 1
        assert payload["vector_store_enabled"] is False
        assert payload["vector_store_ready"] is False
        assert payload["updated_at"] is not None


def test_admin_refresh_returns_refresh_report(monkeypatch) -> None:
    with _prepare_app(monkeypatch, [_make_event("evt-1"), _make_event("evt-2")]) as client:
        resp = client.post("/admin/refresh")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ok"] is True
        assert payload["total_events"] == 2
        assert payload["last_error"] is None
        assert payload["report"]["total_events"] == 2
        assert payload["report"]["live_events"] == 2
        assert payload["report"]["seed_events"] == 0
