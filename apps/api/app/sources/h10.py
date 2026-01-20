from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timezone
from uuid import uuid4

import logging
import httpx

from ..config import AppConfig
from ..models import Event, EventEvidence, EventNumber
from ..services.http_client import request_with_retry

logger = logging.getLogger("source.h10")


async def fetch_h10_events(config: AppConfig) -> list[Event]:
    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(config.http_timeout, read=config.http_timeout)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        try:
            response = await request_with_retry(
                client,
                "GET",
                config.h10_url,
                retries=config.http_retries,
                backoff=config.http_backoff,
                logger=logger,
            )
        except Exception as exc:
            logger.warning("h10_fetch_failed error=%s", exc)
            return []
        if response.status_code >= 400:
            return []
        rows = _extract_rows(response.content)
        if not rows:
            return []
        latest_by_series = _latest_by_series(rows)
        series_filter = {item for item in config.h10_series}
        selected = {
            series: latest_by_series[series]
            for series in latest_by_series
            if not series_filter or series in series_filter
        }
        if not selected:
            return []

        numbers: list[EventNumber] = []
        for series, (obs_date, value) in list(selected.items())[: config.h10_max_obs]:
            numbers.append(
                EventNumber(
                    name=series,
                    value=value,
                    unit="",
                    period=obs_date,
                    source_quote_id=f"H10-{series}",
                )
            )

        latest_date = max(datetime.fromisoformat(item[0]) for item in selected.values())
        headline = "H.10 FX reference rates update"

        return [
            Event(
                event_id=str(uuid4()),
                event_time=latest_date.replace(tzinfo=timezone.utc),
                ingest_time=datetime.now(timezone.utc),
                source_type="macro_data",
                publisher="Federal Reserve H.10",
                headline=headline,
                summary="Latest FX reference rates from the H.10 release.",
                event_type="macro_release",
                markets=["FX"],
                tickers=[],
                instruments=["FX"],
                sectors=["Industrials"],
                numbers=numbers,
                stance="neutral",
                impact=58,
                confidence=0.62,
                impact_chain=[
                    "FX reference rates update informs USD cross pricing",
                    "Macro desks adjust hedging assumptions",
                    "Short-term FX sentiment refines around data",
                ],
                evidence=[
                    EventEvidence(
                        quote_id=f"H10-{uuid4().hex[:8]}",
                        source_url=config.h10_url,
                        title=headline,
                        published_at=latest_date.replace(tzinfo=timezone.utc),
                        excerpt="H.10 release with updated FX reference rates.",
                    )
                ],
                related_event_ids=None,
            )
        ]


def _extract_rows(content: bytes) -> list[dict[str, str]]:
    if _is_zip(content):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for name in archive.namelist():
                if name.lower().endswith(".csv"):
                    with archive.open(name) as file:
                        text = io.TextIOWrapper(file, encoding="utf-8", errors="ignore")
                        return list(csv.DictReader(text))
        return []
    text = content.decode("utf-8", errors="ignore")
    return list(csv.DictReader(io.StringIO(text)))


def _is_zip(content: bytes) -> bool:
    return content[:2] == b"PK"


def _latest_by_series(rows: list[dict[str, str]]) -> dict[str, tuple[str, float]]:
    latest: dict[str, tuple[str, float]] = {}
    for row in rows:
        series = row.get("Series") or row.get("series") or ""
        period = row.get("Time Period") or row.get("time_period") or ""
        value_str = row.get("Value") or row.get("value") or ""
        if not series or not period:
            continue
        try:
            value = float(value_str)
        except ValueError:
            continue
        existing = latest.get(series)
        if existing is None or period > existing[0]:
            latest[series] = (period, value)
    return latest
