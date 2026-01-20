from __future__ import annotations

import asyncio
from typing import Iterable

from ..config import AppConfig
from ..models import Event
from ..state import InMemoryStore
from ..sources.edgar import fetch_edgar_events
from ..sources.fred import fetch_fred_events
from ..sources.h10 import fetch_h10_events
from ..sources.hkex import fetch_hkex_events
from ..sources.hkma import fetch_hkma_events
from ..sources.rss import fetch_rss_events
from ..sources.treasury import fetch_treasury_events
from .seed import HOT_TAGS, build_seed_events


async def refresh_store(store: InMemoryStore, config: AppConfig) -> None:
    seeded = build_seed_events()
    live_events: list[Event] = []

    if config.enable_live_sources:
        tasks = []
        if config.enable_rss:
            tasks.append(fetch_rss_events(config))
        if config.enable_edgar:
            tasks.append(fetch_edgar_events(config))
        if config.enable_h10:
            tasks.append(fetch_h10_events(config))
        if config.enable_treasury:
            tasks.append(fetch_treasury_events(config))
        if config.enable_fred:
            tasks.append(fetch_fred_events(config))
        if config.enable_hkex:
            tasks.append(fetch_hkex_events(config))
        if config.enable_hkma:
            tasks.append(fetch_hkma_events(config))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    continue
                live_events.extend(result)

    events = dedupe_events([*live_events, *seeded])
    store.replace_events(events)


def dedupe_events(events: Iterable[Event]) -> list[Event]:
    seen: set[str] = set()
    ordered: list[Event] = []
    for event in sorted(events, key=lambda item: item.event_time, reverse=True):
        key = _normalize_key(event.headline)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(event)
    return ordered


def _normalize_key(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).strip()


def hot_tags() -> list[str]:
    return HOT_TAGS
