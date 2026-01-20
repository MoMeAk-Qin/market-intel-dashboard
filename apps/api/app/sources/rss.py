from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import asyncio
import feedparser
import httpx

from ..config import AppConfig
from ..models import Event, EventEvidence


async def fetch_rss_events(config: AppConfig) -> list[Event]:
    if not config.rss_feeds:
        return []
    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(10.0, read=10.0)
    events: list[Event] = []
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        tasks = [client.get(feed_url) for feed_url in config.rss_feeds]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for response in responses:
            if isinstance(response, Exception):
                continue
            if response.status_code >= 400:
                continue
            parsed = feedparser.parse(response.text)
            for entry in parsed.entries[:20]:
                published = _parse_published(entry)
                headline = entry.get("title", "")
                source_url = entry.get("link", "")
                if not headline:
                    continue
                events.append(
                    Event(
                        event_id=str(uuid4()),
                        event_time=published,
                        ingest_time=datetime.now(timezone.utc),
                        source_type="news",
                        publisher=entry.get("source", {}).get("title", "RSS"),
                        headline=headline,
                        summary=entry.get("summary", "")[:240],
                        event_type=_infer_event_type(headline),
                        markets=_infer_markets(headline),
                        tickers=_infer_tickers(headline),
                        instruments=[],
                        sectors=_infer_sectors(headline),
                        numbers=[],
                        stance="neutral",
                        impact=55,
                        confidence=0.55,
                        impact_chain=_infer_impact_chain(headline),
                        evidence=[
                            EventEvidence(
                                quote_id=f"RSS-{uuid4().hex[:8]}",
                                source_url=source_url,
                                title=headline,
                                published_at=published,
                                excerpt=(entry.get("summary", "")[:180] or "RSS summary not available."),
                            )
                        ],
                        related_event_ids=None,
                    )
                )
    return events


def _parse_published(entry: dict) -> datetime:
    published = entry.get("published_parsed")
    if published:
        return datetime(*published[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _infer_event_type(text: str) -> str:
    lowered = text.lower()
    if "rate" in lowered or "fed" in lowered or "fomc" in lowered:
        return "rate_decision"
    if "inflation" in lowered or "cpi" in lowered or "gdp" in lowered:
        return "macro_release"
    if "buyback" in lowered or "repurchase" in lowered:
        return "buyback"
    if "acquire" in lowered or "merger" in lowered:
        return "mna"
    if "guidance" in lowered or "outlook" in lowered:
        return "guidance"
    return "risk"


def _infer_markets(text: str) -> list[str]:
    lowered = text.lower()
    if "hong kong" in lowered or "hk" in lowered:
        return ["HK"]
    if "fx" in lowered or "dollar" in lowered:
        return ["FX"]
    if "gold" in lowered or "metal" in lowered:
        return ["METALS"]
    if "yield" in lowered or "treasury" in lowered:
        return ["RATES"]
    return ["US"]


def _infer_tickers(text: str) -> list[str]:
    tickers: list[str] = []
    for symbol in ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "0700.HK", "9988.HK"]:
        if symbol.lower() in text.lower():
            tickers.append(symbol)
    return tickers


def _infer_sectors(text: str) -> list[str]:
    lowered = text.lower()
    if "chip" in lowered or "ai" in lowered or "cloud" in lowered:
        return ["Tech"]
    if "factory" in lowered or "manufact" in lowered:
        return ["Industrials"]
    return ["Tech"]


def _infer_impact_chain(text: str) -> list[str]:
    if "rate" in text.lower():
        return [
            "Policy tone shifts rate path expectations",
            "Rates repricing tightens financial conditions",
            "Equity multiples compress across cyclicals",
        ]
    return [
        "Risk sentiment shifts on headline impact",
        "Sector positioning adjusts amid dispersion",
        "Price discovery extends into next session",
    ]
