from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import httpx

from ..config import AppConfig
from ..models import Event, EventEvidence, EventNumber

DATE_KEYS = ("date", "time_period", "end_of_day", "ref_date")
VALUE_KEYS = ("value", "rate", "closing_rate", "mid_rate")


async def fetch_hkma_events(config: AppConfig) -> list[Event]:
    if not config.hkma_endpoints:
        return []
    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(12.0, read=12.0)
    events: list[Event] = []
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        for endpoint in config.hkma_endpoints:
            response = await client.get(endpoint)
            if response.status_code >= 400:
                continue
            payload = response.json()
            records = _extract_records(payload)
            if not records:
                continue
            latest = records[-1]
            obs_date = _extract_date(latest)
            numbers = _extract_numbers(latest, config.hkma_max_fields)
            if not numbers:
                continue
            headline = "HKMA market data update"
            events.append(
                Event(
                    event_id=str(uuid4()),
                    event_time=obs_date,
                    ingest_time=datetime.now(timezone.utc),
                    source_type="macro_data",
                    publisher="HKMA",
                    headline=headline,
                    summary="Latest HKMA market data snapshot.",
                    event_type="macro_release",
                    markets=["HK", "RATES"],
                    tickers=[],
                    instruments=["HKMA"],
                    sectors=["Industrials"],
                    numbers=numbers,
                    stance="neutral",
                    impact=56,
                    confidence=0.6,
                    impact_chain=[
                        "HKMA data update informs HKD funding conditions",
                        "Rates desks adjust near-term liquidity assumptions",
                        "HKD-linked assets react to updated signals",
                    ],
                    evidence=[
                        EventEvidence(
                            quote_id=f"HKMA-{uuid4().hex[:8]}",
                            source_url=endpoint,
                            title=headline,
                            published_at=obs_date,
                            excerpt="HKMA API latest record used for snapshot.",
                        )
                    ],
                    related_event_ids=None,
                )
            )
    return events


def _extract_records(payload: dict) -> list[dict]:
    if "result" in payload:
        result = payload["result"]
        for key in ("records", "data"):
            records = result.get(key)
            if isinstance(records, list):
                return records
    if "data" in payload and isinstance(payload["data"], list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    return []


def _extract_date(record: dict) -> datetime:
    for key in DATE_KEYS:
        value = record.get(key)
        if isinstance(value, str) and value:
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
    return datetime.now(timezone.utc)


def _extract_numbers(record: dict, limit: int) -> list[EventNumber]:
    numbers: list[EventNumber] = []
    for key, value in record.items():
        if key in DATE_KEYS:
            continue
        if isinstance(value, str):
            try:
                numeric = float(value)
            except ValueError:
                continue
        elif isinstance(value, (int, float)):
            numeric = float(value)
        else:
            continue
        unit = "%" if "rate" in key.lower() else ""
        numbers.append(
            EventNumber(
                name=key,
                value=numeric,
                unit=unit,
                period="",
                source_quote_id=key,
            )
        )
        if len(numbers) >= limit:
            break
    return numbers
