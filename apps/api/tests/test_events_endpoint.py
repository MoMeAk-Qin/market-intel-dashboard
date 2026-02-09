from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import DataOrigin, Event, EventEvidence


def _make_event(
    *,
    event_id: str,
    headline: str,
    event_time: datetime,
    data_origin: DataOrigin = "live",
) -> Event:
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
        impact=55,
        confidence=0.6,
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


@contextmanager
def _prepare_app(monkeypatch, events: list[Event]):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("TIMEZONE", "Asia/Hong_Kong")

    import app.api as api_module

    async def _fake_refresh(store, config) -> None:
        store.replace_events(events)

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)
    with TestClient(create_app()) as client:
        yield client


def test_events_accepts_naive_from_datetime(monkeypatch) -> None:
    event = _make_event(
        event_id="evt-aware",
        headline="aware event",
        event_time=datetime(2026, 2, 4, 2, 0, tzinfo=timezone.utc),
    )

    with _prepare_app(monkeypatch, [event]) as client:
        resp = client.get("/events", params={"from": "2026-02-04T10:00:00"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total"] == 1
        assert payload["items"][0]["event_id"] == "evt-aware"


def test_events_returns_400_for_invalid_datetime(monkeypatch) -> None:
    event = _make_event(
        event_id="evt-1",
        headline="event",
        event_time=datetime(2026, 2, 4, 2, 0, tzinfo=timezone.utc),
    )

    with _prepare_app(monkeypatch, [event]) as client:
        resp = client.get("/events", params={"from": "invalid-time"})
        assert resp.status_code == 400
        assert "Invalid from datetime" in resp.json()["detail"]


def test_news_today_supports_mixed_datetime_kinds(monkeypatch) -> None:
    tz = ZoneInfo("Asia/Hong_Kong")
    now_utc = datetime.now(timezone.utc).replace(hour=6, minute=0, second=0, microsecond=0)
    aware_event = _make_event(
        event_id="evt-aware",
        headline="aware event",
        event_time=now_utc - timedelta(hours=1),
    )
    naive_event = _make_event(
        event_id="evt-naive",
        headline="naive event",
        event_time=(now_utc + timedelta(hours=1)).replace(tzinfo=None),
    )

    with _prepare_app(monkeypatch, [aware_event, naive_event]) as client:
        resp = client.get("/news/today")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["date"] == datetime.now(tz).date().isoformat()
        assert payload["total"] == 2
        assert [item["event_id"] for item in payload["items"]] == ["evt-naive", "evt-aware"]


def test_events_supports_origin_filter(monkeypatch) -> None:
    live_event = _make_event(
        event_id="evt-live",
        headline="live event",
        event_time=datetime(2026, 2, 4, 2, 0, tzinfo=timezone.utc),
        data_origin="live",
    )
    seed_event = _make_event(
        event_id="evt-seed",
        headline="seed event",
        event_time=datetime(2026, 2, 4, 1, 0, tzinfo=timezone.utc),
        data_origin="seed",
    )
    with _prepare_app(monkeypatch, [live_event, seed_event]) as client:
        live_resp = client.get("/events", params={"origin": "live"})
        assert live_resp.status_code == 200
        live_payload = live_resp.json()
        assert live_payload["total"] == 1
        assert live_payload["items"][0]["event_id"] == "evt-live"

        seed_resp = client.get("/events", params={"origin": "seed"})
        assert seed_resp.status_code == 200
        seed_payload = seed_resp.json()
        assert seed_payload["total"] == 1
        assert seed_payload["items"][0]["event_id"] == "evt-seed"
