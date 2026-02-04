from __future__ import annotations

from datetime import date, datetime, timezone

from app.api import build_dashboard_summary
from app.models import Event, EventEvidence, EventType, Market, Sector, Stance


def _make_event(*, event_id: str, event_type: EventType, stance: Stance = "neutral") -> Event:
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    markets: list[Market] = ["US"]
    sectors: list[Sector] = ["Tech"]
    return Event(
        event_id=event_id,
        event_time=now,
        ingest_time=now,
        source_type="news",
        publisher="Test Publisher",
        headline=event_id,
        summary="summary",
        event_type=event_type,
        markets=markets,
        tickers=["AAPL"],
        instruments=[],
        sectors=sectors,
        numbers=[],
        stance=stance,
        impact=55,
        confidence=0.6,
        impact_chain=[],
        evidence=[
            EventEvidence(
                quote_id=f"q-{event_id}",
                source_url="https://example.com",
                title=event_id,
                published_at=now,
                excerpt="excerpt",
            )
        ],
        related_event_ids=None,
    )


def test_build_dashboard_summary_timeline_lanes() -> None:
    macro_event = _make_event(event_id="evt-macro", event_type="macro_release")
    company_event = _make_event(event_id="evt-company", event_type="earnings")
    policy_event = _make_event(event_id="evt-policy", event_type="regulation")

    summary = build_dashboard_summary(date(2024, 1, 2), [macro_event, company_event, policy_event])

    lanes = [lane.lane for lane in summary.timeline]
    assert lanes == ["macro", "industry", "company", "policy_risk"]

    lane_map = {lane.lane: lane.events for lane in summary.timeline}
    assert [event.event_id for event in lane_map["macro"]] == ["evt-macro"]
    assert lane_map["industry"] == []
    assert [event.event_id for event in lane_map["company"]] == ["evt-company"]
    assert [event.event_id for event in lane_map["policy_risk"]] == ["evt-policy"]
