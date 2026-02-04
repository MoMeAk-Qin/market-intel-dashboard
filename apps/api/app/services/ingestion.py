from __future__ import annotations

import asyncio
import logging
import time
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

logger = logging.getLogger("ingestion")


async def refresh_store(store: InMemoryStore, config: AppConfig) -> None:
    started = time.perf_counter()
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
            source_names = [
                name
                for name, enabled in [
                    ("rss", config.enable_rss),
                    ("edgar", config.enable_edgar),
                    ("h10", config.enable_h10),
                    ("treasury", config.enable_treasury),
                    ("fred", config.enable_fred),
                    ("hkex", config.enable_hkex),
                    ("hkma", config.enable_hkma),
                ]
                if enabled
            ]
            for name, result in zip(source_names, results):
                if isinstance(result, BaseException):
                    logger.warning("source_failed source=%s error=%s", name, result)
                    continue
                if not isinstance(result, list):
                    logger.warning(
                        "source_invalid_result source=%s type=%s",
                        name,
                        type(result).__name__,
                    )
                    continue
                logger.info("source_loaded source=%s count=%s", name, len(result))
                live_events.extend(result)

    events = dedupe_events([*live_events, *seeded])
    store.replace_events(events)
    duration = time.perf_counter() - started
    logger.info(
        "refresh_complete total=%s live=%s seeded=%s duration=%.2fs",
        len(events),
        len(live_events),
        len(seeded),
        duration,
    )


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
