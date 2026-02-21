from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
import time
from collections.abc import Awaitable, Iterable
from typing import TYPE_CHECKING

from ..config import AppConfig
from ..models import Event, QuoteSnapshot, RefreshReport
from ..state import InMemoryStore
from ..sources.edgar import fetch_edgar_events
from ..sources.fred import fetch_fred_events
from ..sources.h10 import fetch_h10_events
from ..sources.hkex import fetch_hkex_events
from ..sources.hkma import fetch_hkma_events
from ..sources.quotes import fetch_quote_snapshots
from ..sources.rss import fetch_rss_events
from ..sources.treasury import fetch_treasury_events
from .seed import HOT_TAGS, build_seed_events

if TYPE_CHECKING:
    from .vector_store import BaseVectorStore

logger = logging.getLogger("ingestion")


async def refresh_store(store: InMemoryStore, config: AppConfig) -> RefreshReport:
    started = time.perf_counter()
    started_at = datetime.now(UTC)
    seeded = build_seed_events() if config.enable_seed_data else []
    live_events: list[Event] = []
    live_quotes: dict[str, QuoteSnapshot] = {}
    source_errors: list[str] = []

    if config.enable_live_sources:
        source_jobs: list[tuple[str, Awaitable[list[Event]]]] = []
        if config.enable_rss:
            source_jobs.append(("rss", fetch_rss_events(config)))
        if config.enable_edgar:
            source_jobs.append(("edgar", fetch_edgar_events(config)))
        if config.enable_h10:
            source_jobs.append(("h10", fetch_h10_events(config)))
        if config.enable_treasury:
            source_jobs.append(("treasury", fetch_treasury_events(config)))
        if config.enable_fred:
            source_jobs.append(("fred", fetch_fred_events(config)))
        if config.enable_hkex:
            source_jobs.append(("hkex", fetch_hkex_events(config)))
        if config.enable_hkma:
            source_jobs.append(("hkma", fetch_hkma_events(config)))

        if source_jobs:
            source_names = [name for name, _ in source_jobs]
            source_tasks = [job for _, job in source_jobs]
            results: list[list[Event] | BaseException] = list(
                await asyncio.gather(*source_tasks, return_exceptions=True)
            )
            for name, result in zip(source_names, results, strict=False):
                if isinstance(result, BaseException):
                    logger.warning("source_failed source=%s error=%s", name, result)
                    source_errors.append(f"{name}: {result}")
                    continue
                logger.info("source_loaded source=%s count=%s", name, len(result))
                live_events.extend(result)

    seeded_events: list[Event] = []
    if config.enable_seed_data:
        if config.seed_only_when_no_live:
            seeded_events = seeded if not live_events else []
        else:
            seeded_events = seeded

    events = dedupe_events([*live_events, *seeded_events])
    store.replace_events(events)
    if config.enable_market_quotes:
        try:
            live_quotes = await fetch_quote_snapshots(config)
        except Exception as exc:
            logger.warning("quotes_refresh_failed error=%s", exc)
            source_errors.append(f"quotes: {exc}")
    store.replace_quotes(live_quotes)
    duration = time.perf_counter() - started
    logger.info(
        "refresh_complete total=%s live=%s seeded=%s quotes=%s duration=%.2fs",
        len(events),
        len(live_events),
        len(seeded_events),
        len(live_quotes),
        duration,
    )
    finished_at = datetime.now(UTC)
    return RefreshReport(
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=int(round(duration * 1000)),
        total_events=len(events),
        live_events=len(live_events),
        seed_events=len(seeded_events),
        quote_assets=len(live_quotes),
        source_errors=source_errors,
    )


def dedupe_events(events: Iterable[Event]) -> list[Event]:
    seen: set[str] = set()
    ordered: list[Event] = []
    sorted_events = sorted(
        events,
        key=lambda item: (
            _origin_priority(item),
            _to_utc(item.event_time),
            item.impact,
            item.confidence,
        ),
        reverse=True,
    )
    for event in sorted_events:
        key = _normalize_key(event.headline)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(event)
    return ordered


def _normalize_key(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).strip()


def _origin_priority(event: Event) -> int:
    return 1 if event.data_origin == "live" else 0


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def hot_tags() -> list[str]:
    return HOT_TAGS


def write_vectors(events: list[Event], config: AppConfig, vector_store: "BaseVectorStore") -> int:
    backend = config.vector_backend.strip().lower()
    if backend in {"chroma", "simple"}:
        return vector_store.upsert_events(events)
    if backend == "pgvector":
        from .pg_vector_store import PgVectorStore

        if not isinstance(vector_store, PgVectorStore):
            logger.warning(
                "vector_store_backend_mismatch expected=pgvector actual=%s",
                type(vector_store).__name__,
            )
        return vector_store.upsert_events(events)
    raise ValueError(f"Unsupported vector backend: {backend}")
