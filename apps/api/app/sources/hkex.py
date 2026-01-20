from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin
from uuid import uuid4

import httpx

from ..config import AppConfig
from ..models import Event, EventEvidence


@dataclass
class HKEXRecord:
    release_time: str
    stock_code: str
    stock_name: str
    title: str
    link: str


class HKEXTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[HKEXRecord] = []
        self._current: dict[str, str] = {}
        self._current_key: str | None = None
        self._current_link: str | None = None
        self._in_row = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value for key, value in attrs if value is not None}
        if tag == "tr":
            self._current = {}
            self._current_link = None
            self._in_row = True
        if tag == "td":
            key = attrs_dict.get("data-title")
            if key:
                self._current_key = key.strip()
        if tag == "a" and self._current_key:
            href = attrs_dict.get("href")
            if href:
                self._current_link = href

    def handle_data(self, data: str) -> None:
        if not self._in_row or not self._current_key:
            return
        text = data.strip()
        if not text:
            return
        existing = self._current.get(self._current_key, "")
        self._current[self._current_key] = (existing + " " + text).strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "td":
            self._current_key = None
        if tag == "tr":
            self._in_row = False
            title = self._current.get("Title") or self._current.get("Headline")
            if title:
                record = HKEXRecord(
                    release_time=self._current.get("Release Time", ""),
                    stock_code=self._current.get("Stock Code", ""),
                    stock_name=self._current.get("Stock Short Name", ""),
                    title=title,
                    link=self._current_link or "",
                )
                self.records.append(record)


async def fetch_hkex_events(config: AppConfig) -> list[Event]:
    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(12.0, read=12.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        response = await client.get(config.hkex_search_url, params=config.hkex_search_params)
        if response.status_code >= 400:
            return []
        parser = HKEXTableParser()
        parser.feed(response.text)
        records = list(_dedupe_records(parser.records))

    events: list[Event] = []
    for record in records[: config.hkex_max_items]:
        event_time = _parse_release_time(record.release_time)
        ticker = _format_ticker(record.stock_code)
        headline = record.title
        summary = record.title
        link = urljoin(config.hkex_base_url, record.link) if record.link else config.hkex_base_url
        events.append(
            Event(
                event_id=str(uuid4()),
                event_time=event_time,
                ingest_time=datetime.now(timezone.utc),
                source_type="filing",
                publisher="HKEXnews",
                headline=headline,
                summary=summary,
                event_type=_infer_event_type(headline),
                markets=["HK"],
                tickers=[ticker] if ticker else [],
                instruments=[],
                sectors=_infer_sectors(headline),
                numbers=[],
                stance="neutral",
                impact=60,
                confidence=0.62,
                impact_chain=[
                    "HKEX announcement updates market attention",
                    "Investor focus shifts to disclosed items",
                    "Follow-up coverage shapes trading response",
                ],
                evidence=[
                    EventEvidence(
                        quote_id=f"HKEX-{uuid4().hex[:8]}",
                        source_url=link,
                        title=headline,
                        published_at=event_time,
                        excerpt=summary,
                    )
                ],
                related_event_ids=None,
            )
        )
    return events


def _dedupe_records(records: Iterable[HKEXRecord]) -> list[HKEXRecord]:
    seen: set[str] = set()
    ordered: list[HKEXRecord] = []
    for record in records:
        key = " ".join([record.stock_code, record.title]).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(record)
    return ordered


def _parse_release_time(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%d/%m/%Y %H:%M"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)


def _format_ticker(code: str) -> str:
    cleaned = code.strip()
    if not cleaned:
        return ""
    if cleaned.isdigit():
        return f"{cleaned}.HK"
    return cleaned


def _infer_event_type(title: str) -> str:
    lowered = title.lower()
    if "results" in lowered or "earnings" in lowered:
        return "earnings"
    if "profit warning" in lowered or "warning" in lowered:
        return "risk"
    if "announcement" in lowered or "inside information" in lowered:
        return "regulation"
    return "risk"


def _infer_sectors(title: str) -> list[str]:
    lowered = title.lower()
    if "chip" in lowered or "ai" in lowered or "cloud" in lowered:
        return ["Tech"]
    if "factory" in lowered or "manufact" in lowered:
        return ["Industrials"]
    return ["Tech"]
