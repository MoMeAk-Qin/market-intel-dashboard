from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import httpx

from ..config import AppConfig
from ..models import Event, EventEvidence, EventNumber

RATE_SERIES = {"DGS10", "DGS2", "DGS1MO", "FEDFUNDS"}
METAL_SERIES = {"GOLDAMGBD228NLBM"}


async def fetch_fred_events(config: AppConfig) -> list[Event]:
    if not config.fred_api_key or not config.fred_series:
        return []
    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(12.0, read=12.0)
    events: list[Event] = []
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        for series_id in config.fred_series:
            url = (
                "https://api.stlouisfed.org/fred/series/observations"
                f"?series_id={series_id}&api_key={config.fred_api_key}&file_type=json"
            )
            response = await client.get(url)
            if response.status_code >= 400:
                continue
            payload = response.json()
            observations = payload.get("observations", [])
            if not observations:
                continue
            latest = next((item for item in reversed(observations) if item.get("value") != "."), None)
            if not latest:
                continue
            date_str = latest.get("date", "")
            try:
                obs_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            except ValueError:
                obs_date = datetime.now(timezone.utc)
            try:
                value = float(latest.get("value", "0"))
            except ValueError:
                value = 0.0

            numbers = [
                EventNumber(
                    name=series_id,
                    value=value,
                    unit="",
                    period=date_str,
                    source_quote_id=series_id,
                )
            ]

            events.append(
                Event(
                    event_id=str(uuid4()),
                    event_time=obs_date,
                    ingest_time=datetime.now(timezone.utc),
                    source_type="macro_data",
                    publisher="FRED",
                    headline=f"FRED update: {series_id}",
                    summary=f"Latest observation for {series_id} from FRED.",
                    event_type="macro_release",
                    markets=_infer_market(series_id),
                    tickers=[],
                    instruments=["FRED"],
                    sectors=["Industrials"],
                    numbers=numbers,
                    stance="neutral",
                    impact=55,
                    confidence=0.6,
                    impact_chain=[
                        "Macro indicator update informs baseline assumptions",
                        "Rates and risk assets adjust to fresh signals",
                        "Cross-asset positioning recalibrates",
                    ],
                    evidence=[
                        EventEvidence(
                            quote_id=f"FRED-{uuid4().hex[:8]}",
                            source_url=url,
                            title=f"FRED {series_id}",
                            published_at=obs_date,
                            excerpt=f"Latest FRED observation for {series_id}.",
                        )
                    ],
                    related_event_ids=None,
                )
            )
    return events


def _infer_market(series_id: str) -> list[str]:
    if series_id in METAL_SERIES:
        return ["METALS"]
    if series_id in RATE_SERIES:
        return ["RATES"]
    return ["US"]
