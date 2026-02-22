from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import DataOrigin, Event, EventEvidence
from app.services.unlisted_tracker import UnlistedTracker


def _make_event(
    *,
    event_id: str,
    headline: str,
    summary: str,
    data_origin: DataOrigin = "live",
) -> Event:
    now = datetime(2026, 2, 22, 9, 0, tzinfo=timezone.utc)
    return Event(
        event_id=event_id,
        event_time=now,
        ingest_time=now,
        source_type="news",
        publisher="Tech Wire",
        headline=headline,
        summary=summary,
        event_type="risk",
        markets=["US"],
        tickers=[],
        instruments=[],
        sectors=["Tech"],
        numbers=[],
        stance="neutral",
        impact=72,
        confidence=0.81,
        impact_chain=[],
        evidence=[
            EventEvidence(
                quote_id=f"q-{event_id}",
                source_url=f"https://example.com/{event_id}",
                title=headline,
                published_at=now,
                excerpt=summary,
            )
        ],
        related_event_ids=None,
        data_origin=data_origin,
    )


def test_unlisted_tracker_seed_baseline_and_minimax() -> None:
    tracker = UnlistedTracker()
    companies = tracker.list_companies()
    company_ids = {item.company_id for item in companies}

    assert len(companies) >= 15
    assert "openai" in company_ids
    assert "deepseek" in company_ids
    assert "minimax" in company_ids
    assert all(item.source_type == "seed" for item in companies)


def test_unlisted_tracker_sync_marks_live_timeline() -> None:
    tracker = UnlistedTracker()
    event = _make_event(
        event_id="evt-openai-1",
        headline="OpenAI releases GPT roadmap update",
        summary="OpenAI discussed GPT and Sora roadmap in a partner briefing.",
        data_origin="live",
    )

    inserted = tracker.sync_from_events([event])
    detail = tracker.get_company("openai")

    assert inserted == 1
    assert detail is not None
    assert detail.company.source_type == "live"
    assert detail.total_events == 1
    assert detail.timeline[0].event_id == "evt-openai-1"
    assert detail.timeline[0].source_type == "live"


@contextmanager
def _prepare_app(monkeypatch, events: list[Event]):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("ENABLE_LIVE_SOURCES", "false")

    import app.api as api_module
    import app.services.ingestion as ingestion_module

    async def _fake_refresh(store, config) -> None:
        store.replace_events(events)
        ingestion_module.sync_unlisted_from_events(events)

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)

    with TestClient(create_app()) as client:
        yield client


def test_unlisted_company_endpoints_seed_and_live(monkeypatch) -> None:
    events = [
        _make_event(
            event_id="evt-openai-live",
            headline="OpenAI signs new enterprise AI partnership",
            summary="The OpenAI agreement extends GPT enterprise roll-out.",
            data_origin="live",
        )
    ]
    with _prepare_app(monkeypatch, events) as client:
        list_resp = client.get("/unlisted/companies")
        assert list_resp.status_code == 200
        companies = list_resp.json()
        assert len(companies) >= 15

        openai = next(item for item in companies if item["company_id"] == "openai")
        minimax = next(item for item in companies if item["company_id"] == "minimax")
        assert openai["source_type"] == "live"
        assert minimax["source_type"] == "seed"

        detail_resp = client.get("/unlisted/companies/openai")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["company"]["company_id"] == "openai"
        assert detail["company"]["source_type"] == "live"
        assert detail["total_events"] >= 1
        assert detail["timeline"][0]["source_type"] == "live"


def test_unlisted_company_detail_not_found(monkeypatch) -> None:
    with _prepare_app(monkeypatch, []) as client:
        resp = client.get("/unlisted/companies/not-exists")
        assert resp.status_code == 404
