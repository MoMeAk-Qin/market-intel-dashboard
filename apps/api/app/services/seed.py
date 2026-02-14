from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4
import random

from typing import TypeVar

from ..models import AssetSeriesPoint, Event, EventEvidence, EventNumber

PUBLISHERS = [
    "Bloomberg Wire",
    "Market Pulse",
    "Rates Desk",
    "Alpha Ledger",
    "Pacific Markets",
    "Crown Research",
    "Summit Macro",
    "Atlas Insight",
    "Harbor Analytics",
    "Northbridge Daily",
]

HEADLINE_TEMPLATES = [
    "Policy signals reshape {market} positioning",
    "{ticker} posts resilient demand in core segments",
    "{ticker} guides {direction} on margin outlook",
    "{market} volatility rises as liquidity thins",
    "Deal chatter lifts {sector} breadth",
    "Macro print surprises on {macro}",
    "Central bank delivers {stance} tone",
    "{ticker} announces capital return update",
    "{sector} supply chain normalizes faster than expected",
    "Risk sentiment softens after {macro} shock",
]

SUMMARY_TEMPLATES = [
    "Traders recalibrated exposure after the latest release, with follow-through expected across the next two sessions.",
    "The update shifts consensus ranges, lifting dispersion across peer names and reinforcing a more selective stance.",
    "Early price action suggests positioning was light, leaving room for a follow-on move if confirmation data arrives.",
    "Liquidity pockets remain thin, and intraday swings are likely to persist into the next macro catalyst.",
    "Analysts flagged a better mix shift, but highlighted cost discipline as the main determinant of earnings power.",
    "The announcement underscores a cautious tone in guidance while keeping optionality for upside revisions.",
]

MACRO_TAGS = ["inflation", "jobs", "growth", "liquidity", "policy"]

EVENT_TYPES = [
    "earnings",
    "guidance",
    "mna",
    "buyback",
    "rate_decision",
    "macro_release",
    "regulation",
    "risk",
]

SOURCE_TYPES = ["news", "filing", "earnings", "research", "macro_data"]

MARKETS = ["US", "HK", "FX", "RATES", "METALS"]
SECTORS = ["Tech", "Industrials"]
TICKERS = ["AAPL", "MSFT", "NVDA", "0700.HK", "9988.HK", "TSLA", "AMZN", "META"]
INSTRUMENTS = ["NASDAQ", "SPX", "DXY", "US10Y", "XAUUSD", "USDJPY"]

NUMBER_TEMPLATES = [
    {"name": "EPS", "unit": "USD", "period": "Q", "range": (1.2, 2.4), "yoy": 0.12},
    {"name": "Revenue", "unit": "B USD", "period": "Q", "range": (12, 38), "yoy": 0.08},
    {"name": "CPI", "unit": "%", "period": "M", "range": (2.4, 3.6), "yoy": 0.3},
    {"name": "Payrolls", "unit": "K", "period": "M", "range": (120, 260), "yoy": 0.05},
    {"name": "PMI", "unit": "pts", "period": "M", "range": (47, 54), "yoy": -0.02},
]

IMPACT_CHAINS = [
    "Policy tone shifts rate path expectations",
    "Rates repricing tightens financial conditions",
    "Equity multiples compress across cyclicals",
    "FX volatility spikes in high-beta pairs",
    "Commodities demand recalibrates on growth fears",
    "Credit spreads widen on risk repricing",
]

EVIDENCE_TITLES = [
    "Morning Briefing Note",
    "Macro Snapshot",
    "Earnings Call Highlights",
    "Regulatory Update Memo",
    "Rates Strategy Recap",
]

HOT_TAGS = [
    "AI capex",
    "rate cut odds",
    "USD strength",
    "China demand",
    "carry unwind",
    "buyback cadence",
]

ASSET_CATALOG = [
    {"id": "DXY", "name": "US Dollar Index", "base": 104.2, "market": "FX"},
    {"id": "XAUUSD", "name": "Gold Spot", "base": 2352.0, "market": "METALS"},
    {"id": "US10Y", "name": "US 10Y Yield", "base": 4.12, "market": "RATES"},
    {"id": "NASDAQ", "name": "Nasdaq 100", "base": 18240.0, "market": "US"},
    {"id": "AAPL", "name": "Apple Inc.", "base": 196.3, "market": "US"},
    {"id": "0700.HK", "name": "Tencent Holdings", "base": 328.4, "market": "HK"},
]

T = TypeVar("T", bound=object)


def _pick(rng: random.Random, items: Sequence[T]) -> T:
    if not items:
        raise ValueError("items must not be empty")
    return items[rng.randrange(len(items))]


def _pick_many(rng: random.Random, items: Sequence[T], minimum: int, maximum: int) -> list[T]:
    count = max(minimum, int(rng.random() * (maximum - minimum + 1)) + minimum)
    selected = [_pick(rng, items) for _ in range(count)]
    unique: list[T] = []
    for item in selected:
        if item in unique:
            continue
        unique.append(item)
    return unique


def _make_numbers(rng: random.Random) -> list[EventNumber]:
    templates = _pick_many(rng, NUMBER_TEMPLATES, 1, 2)
    numbers: list[EventNumber] = []
    for template in templates:
        low, high = template["range"]
        value = low + rng.random() * (high - low)
        numbers.append(
            EventNumber(
                name=template["name"],
                value=round(value, 2),
                unit=template["unit"],
                period=template["period"],
                yoy=template.get("yoy"),
                source_quote_id=f"Q{rng.randint(100,999)}",
            )
        )
    return numbers


def _make_evidence(rng: random.Random, published_at: datetime) -> list[EventEvidence]:
    count = max(1, int(rng.random() * 2) + 1)
    items: list[EventEvidence] = []
    for idx in range(count):
        items.append(
            EventEvidence(
                quote_id=f"E-{rng.randint(1000,9999)}-{idx}",
                source_url=f"https://example.com/source/{rng.randint(100,999)}/{idx}",
                title=_pick(rng, EVIDENCE_TITLES),
                published_at=published_at,
                excerpt=(
                    "Key takeaway: the data and guidance reinforce near-term expectations, "
                    "keeping volatility elevated."
                ),
            )
        )
    return items


def _make_headline(rng: random.Random) -> str:
    template = _pick(rng, HEADLINE_TEMPLATES)
    return (
        template.replace("{market}", _pick(rng, MARKETS))
        .replace("{ticker}", _pick(rng, TICKERS))
        .replace("{direction}", "up" if rng.random() > 0.5 else "down")
        .replace("{sector}", _pick(rng, SECTORS))
        .replace("{macro}", _pick(rng, MACRO_TAGS))
        .replace("{stance}", "hawkish" if rng.random() > 0.6 else "dovish")
    )


def build_seed_events(count: int = 80) -> list[Event]:
    rng = random.Random(42)
    events: list[Event] = []
    now = datetime.now(UTC)
    for idx in range(count):
        event_time = now - timedelta(hours=6 * idx)
        ingest_time = event_time + timedelta(minutes=20)
        impact = round(35 + rng.random() * 60)
        confidence = round(0.45 + rng.random() * 0.5, 2)
        events.append(
            Event(
                event_id=str(uuid4()),
                event_time=event_time,
                ingest_time=ingest_time,
                source_type=_pick(rng, SOURCE_TYPES),
                publisher=_pick(rng, PUBLISHERS),
                headline=_make_headline(rng),
                summary=_pick(rng, SUMMARY_TEMPLATES),
                event_type=_pick(rng, EVENT_TYPES),
                markets=_pick_many(rng, MARKETS, 1, 3),
                tickers=_pick_many(rng, TICKERS, 1, 2),
                instruments=_pick_many(rng, INSTRUMENTS, 1, 2),
                sectors=_pick_many(rng, SECTORS, 1, 2),
                numbers=_make_numbers(rng),
                stance="positive" if rng.random() > 0.64 else "neutral" if rng.random() > 0.5 else "negative",
                impact=impact,
                confidence=confidence,
                impact_chain=_pick_many(rng, IMPACT_CHAINS, 3, 5),
                evidence=_make_evidence(rng, event_time),
                related_event_ids=[] if rng.random() > 0.7 else None,
                data_origin="seed",
            )
        )
    return events


def build_asset_series(base: float, range_key: str) -> list[AssetSeriesPoint]:
    if range_key == "1D":
        points = 24
        step = 1
    elif range_key == "1W":
        points = 7
        step = 1
    elif range_key == "1M":
        points = 30
        step = 1
    else:
        points = 12
        step = 30
    series: list[AssetSeriesPoint] = []
    for idx in range(points):
        shift = (idx / max(points, 1)) * 0.006
        value = base * (1 + shift) * (1 + (idx % 3) * 0.001)
        day = date.today() - timedelta(days=(points - idx - 1) * step)
        series.append(AssetSeriesPoint(date=day, value=round(value, 2)))
    return series
