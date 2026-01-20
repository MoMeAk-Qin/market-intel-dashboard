from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from uuid import uuid4

import logging
import httpx

from ..config import AppConfig
from ..models import Event, EventEvidence, EventNumber
from ..services.http_client import request_with_retry

logger = logging.getLogger("source.treasury")

TENOR_MAP = {
    "1 Mo": "UST_1M",
    "2 Mo": "UST_2M",
    "3 Mo": "UST_3M",
    "6 Mo": "UST_6M",
    "1 Yr": "UST_1Y",
    "2 Yr": "UST_2Y",
    "5 Yr": "UST_5Y",
    "7 Yr": "UST_7Y",
    "10 Yr": "UST_10Y",
    "20 Yr": "UST_20Y",
    "30 Yr": "UST_30Y",
}


async def fetch_treasury_events(config: AppConfig) -> list[Event]:
    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(config.http_timeout, read=config.http_timeout)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        try:
            response = await request_with_retry(
                client,
                "GET",
                config.treasury_url,
                retries=config.http_retries,
                backoff=config.http_backoff,
                logger=logger,
            )
        except Exception as exc:
            logger.warning("treasury_fetch_failed error=%s", exc)
            return []
        if response.status_code >= 400:
            return []
        rows = list(csv.DictReader(io.StringIO(response.text)))
        if not rows:
            return []
        latest = rows[-1]
        date_str = latest.get("Date", "")
        try:
            obs_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
        except ValueError:
            obs_date = datetime.now(timezone.utc)

        numbers: list[EventNumber] = []
        for column, series_id in TENOR_MAP.items():
            value_str = latest.get(column)
            if not value_str:
                continue
            try:
                value = float(value_str)
            except ValueError:
                continue
            numbers.append(
                EventNumber(
                    name=series_id,
                    value=value,
                    unit="%",
                    period=date_str,
                    source_quote_id=series_id,
                )
            )

        headline = "US Treasury yield curve update"
        return [
            Event(
                event_id=str(uuid4()),
                event_time=obs_date,
                ingest_time=datetime.now(timezone.utc),
                source_type="macro_data",
                publisher="US Treasury",
                headline=headline,
                summary="Daily Treasury yield curve snapshot.",
                event_type="macro_release",
                markets=["RATES"],
                tickers=[],
                instruments=["UST"],
                sectors=["Industrials"],
                numbers=numbers,
                stance="neutral",
                impact=62,
                confidence=0.7,
                impact_chain=[
                    "Yield curve shifts recalibrate rate expectations",
                    "Rates volatility filters into credit conditions",
                    "Duration positioning adapts across portfolios",
                ],
                evidence=[
                    EventEvidence(
                        quote_id=f"UST-{uuid4().hex[:8]}",
                        source_url=config.treasury_url,
                        title=headline,
                        published_at=obs_date,
                        excerpt="Latest daily Treasury yield curve data.",
                    )
                ],
                related_event_ids=None,
            )
        ]
