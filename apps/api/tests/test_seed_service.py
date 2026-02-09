from __future__ import annotations

from app.services.seed import build_seed_events


def test_build_seed_events_handles_unhashable_templates() -> None:
    events = build_seed_events(count=3)
    assert len(events) == 3
    assert all(len(event.numbers) >= 1 for event in events)

