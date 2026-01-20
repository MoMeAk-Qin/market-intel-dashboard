from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import logging
import httpx

from ..config import AppConfig
from ..models import Event, EventEvidence
from ..services.http_client import request_with_retry

logger = logging.getLogger("source.edgar")

FORM_EARNINGS = {"10-K", "10-Q", "20-F", "40-F"}
FORM_REGULATORY = {"8-K", "6-K"}

SECTOR_TECH = {"AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL"}
SECTOR_INDUSTRIALS = {"CAT", "HON", "BA", "GE"}


async def fetch_edgar_events(config: AppConfig) -> list[Event]:
    tickers = [symbol for symbol in config.market_symbols if not symbol.endswith(".HK")]
    if not tickers:
        return []
    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(config.http_timeout, read=config.http_timeout)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        mapping = await _fetch_cik_map(client, config)
        if not mapping:
            return []
        events: list[Event] = []
        for ticker in tickers:
            cik = mapping.get(ticker.upper())
            if not cik:
                continue
            submissions = await _fetch_submissions(client, config, cik)
            if not submissions:
                continue
            events.extend(_build_events_from_submissions(ticker, cik, submissions, config))
        return events


async def _fetch_cik_map(client: httpx.AsyncClient, config: AppConfig) -> dict[str, str]:
    try:
        response = await request_with_retry(
            client,
            "GET",
            config.edgar_ticker_map_url,
            retries=config.http_retries,
            backoff=config.http_backoff,
            logger=logger,
        )
    except Exception as exc:
        logger.warning("edgar_cik_map_failed error=%s", exc)
        return {}
    if response.status_code >= 400:
        logger.warning("edgar_cik_map_status status=%s", response.status_code)
        return {}
    payload = response.json()
    mapping: dict[str, str] = {}

    if isinstance(payload, list):
        for entry in payload:
            ticker = str(entry.get("ticker", "")).upper()
            cik_str = str(entry.get("cik_str", "")).zfill(10)
            if ticker and cik_str:
                mapping[ticker] = cik_str
        return mapping

    data = payload.get("data")
    fields = payload.get("fields")
    if isinstance(data, list) and isinstance(fields, list):
        try:
            ticker_idx = fields.index("ticker")
            cik_idx = fields.index("cik") if "cik" in fields else fields.index("cik_str")
        except ValueError:
            return mapping
        for row in data:
            try:
                ticker = str(row[ticker_idx]).upper()
                cik_raw = str(row[cik_idx])
            except (IndexError, TypeError):
                continue
            if ticker and cik_raw:
                mapping[ticker] = str(cik_raw).zfill(10)
    return mapping


async def _fetch_submissions(
    client: httpx.AsyncClient, config: AppConfig, cik: str
) -> dict[str, Any] | None:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        response = await request_with_retry(
            client,
            "GET",
            url,
            retries=config.http_retries,
            backoff=config.http_backoff,
            logger=logger,
        )
    except Exception as exc:
        logger.warning("edgar_submission_failed cik=%s error=%s", cik, exc)
        return None
    if response.status_code >= 400:
        logger.warning("edgar_submission_status cik=%s status=%s", cik, response.status_code)
        return None
    return response.json()


def _build_events_from_submissions(
    ticker: str, cik: str, payload: dict[str, Any], config: AppConfig
) -> list[Event]:
    recent = payload.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    documents = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])

    events: list[Event] = []
    allow_forms = {form.strip().upper() for form in config.edgar_forms}
    now = datetime.now(timezone.utc)

    for idx, form in enumerate(forms):
        form_upper = str(form).upper()
        if allow_forms and form_upper not in allow_forms:
            continue
        try:
            filing_date = datetime.fromisoformat(filing_dates[idx]).replace(tzinfo=timezone.utc)
        except (IndexError, ValueError):
            filing_date = now
        accession = str(accession_numbers[idx]) if idx < len(accession_numbers) else ""
        document = str(documents[idx]) if idx < len(documents) else ""
        description = str(descriptions[idx]) if idx < len(descriptions) else form_upper

        evidence_url = _build_edgar_url(cik, accession, document)
        event_type = _map_event_type(form_upper)
        impact = 70 if form_upper in FORM_EARNINGS else 55
        confidence = 0.75 if form_upper in FORM_EARNINGS else 0.6

        events.append(
            Event(
                event_id=str(uuid4()),
                event_time=filing_date,
                ingest_time=now,
                source_type="filing",
                publisher="SEC EDGAR",
                headline=f"{ticker} {form_upper} {description}",
                summary=description,
                event_type=event_type,
                markets=["US"],
                tickers=[ticker],
                instruments=[],
                sectors=_infer_sectors(ticker),
                numbers=[],
                stance="neutral",
                impact=impact,
                confidence=confidence,
                impact_chain=_impact_chain_for_form(form_upper),
                evidence=[
                    EventEvidence(
                        quote_id=f"EDGAR-{uuid4().hex[:8]}",
                        source_url=evidence_url,
                        title=description,
                        published_at=filing_date,
                        excerpt=f"SEC filing {form_upper} for {ticker}.",
                    )
                ],
                related_event_ids=None,
            )
        )

        if len(events) >= config.edgar_max_per_ticker:
            break

    return events


def _map_event_type(form: str) -> str:
    if form in FORM_EARNINGS:
        return "earnings"
    if form in FORM_REGULATORY:
        return "regulation"
    return "risk"


def _build_edgar_url(cik: str, accession: str, document: str) -> str:
    accession_no_dash = accession.replace("-", "")
    cik_numeric = str(int(cik))
    return f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/{accession_no_dash}/{document}"


def _infer_sectors(ticker: str) -> list[str]:
    if ticker in SECTOR_INDUSTRIALS:
        return ["Industrials"]
    return ["Tech"] if ticker in SECTOR_TECH else ["Tech"]


def _impact_chain_for_form(form: str) -> list[str]:
    if form in FORM_EARNINGS:
        return [
            "Earnings disclosure updates forward expectations",
            "Analyst models adjust with new filings",
            "Valuation ranges recalibrate across peers",
        ]
    return [
        "Regulatory disclosure reshapes risk perception",
        "Market positioning adjusts to new information",
        "Follow-up coverage expands the impact chain",
    ]
