from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from urllib.parse import quote

import httpx

from ..config import AppConfig
from ..models import EarningsCard, Metric, QuoteSnapshot
from ..services.http_client import request_with_retry

logger = logging.getLogger("source.earnings")


@dataclass(frozen=True)
class EarningsSnapshot:
    ticker: str
    quote: QuoteSnapshot
    earnings_card: EarningsCard
    source_url: str
    updated_at: datetime
    is_live: bool


async def fetch_earnings_snapshot(config: AppConfig, ticker: str) -> EarningsSnapshot | None:
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        return None

    url = (
        "https://query1.finance.yahoo.com/v10/finance/quoteSummary/"
        f"{quote(normalized_ticker, safe='')}"
    )
    params = {
        "modules": "price,financialData,defaultKeyStatistics,earningsHistory",
    }
    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(config.http_timeout, read=config.http_timeout)

    try:
        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            response = await request_with_retry(
                client,
                "GET",
                url,
                params=params,
                retries=config.http_retries,
                backoff=config.http_backoff,
                logger=logger,
            )
        if response.status_code >= 400:
            logger.warning(
                "earnings_snapshot_status_failed ticker=%s status=%s",
                normalized_ticker,
                response.status_code,
            )
            return None
        payload = response.json()
    except Exception as exc:
        logger.warning("earnings_snapshot_fetch_failed ticker=%s error=%s", normalized_ticker, exc)
        return None

    parsed = _parse_snapshot_payload(normalized_ticker, payload)
    if parsed is None:
        logger.warning("earnings_snapshot_parse_failed ticker=%s", normalized_ticker)
    return parsed


def _parse_snapshot_payload(ticker: str, payload: object) -> EarningsSnapshot | None:
    if not isinstance(payload, dict):
        return None
    summary = payload.get("quoteSummary")
    if not isinstance(summary, dict):
        return None
    result = summary.get("result")
    if not isinstance(result, list) or not result:
        return None
    root = result[0]
    if not isinstance(root, dict):
        return None

    price = root.get("price")
    financial_data = root.get("financialData")
    history = root.get("earningsHistory")

    if not isinstance(price, dict) or not isinstance(financial_data, dict):
        return None

    market_price = _extract_number(price.get("regularMarketPrice"))
    eps_value = _extract_number(financial_data.get("epsCurrentYear")) or _extract_number(
        price.get("epsTrailingTwelveMonths")
    )
    revenue_value = _extract_number(financial_data.get("totalRevenue"))
    if market_price is None or eps_value is None or revenue_value is None:
        return None

    revenue_billions = revenue_value / 1_000_000_000
    eps_yoy = _extract_eps_yoy(history)
    revenue_yoy = _extract_number(financial_data.get("revenueGrowth"))

    market_time_raw = _extract_number(price.get("regularMarketTime"))
    as_of = _to_datetime_utc(market_time_raw)
    currency_raw = price.get("currency")
    currency = currency_raw if isinstance(currency_raw, str) else None
    change = _extract_number(price.get("regularMarketChange"))
    change_pct = _extract_number(price.get("regularMarketChangePercent"))

    display_name = price.get("shortName") or price.get("longName") or ticker
    if not isinstance(display_name, str):
        display_name = ticker

    recommendation_raw = financial_data.get("recommendationKey")
    recommendation = recommendation_raw if isinstance(recommendation_raw, str) else ""
    target_price = _extract_number(financial_data.get("targetMeanPrice"))
    guidance = _build_guidance(recommendation=recommendation, target_price=target_price)

    quote = QuoteSnapshot(
        asset_id=ticker,
        price=round(market_price, 6),
        change=None if change is None else round(change, 6),
        change_pct=None if change_pct is None else round(change_pct, 6),
        currency=currency,
        as_of=as_of,
        source="yahoo",
        is_fallback=False,
    )
    earnings_card = EarningsCard(
        headline=f"{display_name} 财报快照",
        eps=Metric(value=round(eps_value, 4), yoy=eps_yoy),
        revenue=Metric(value=round(revenue_billions, 4), yoy=revenue_yoy),
        guidance=guidance,
        sentiment=_build_sentiment(recommendation),
    )
    return EarningsSnapshot(
        ticker=ticker,
        quote=quote,
        earnings_card=earnings_card,
        source_url=f"https://finance.yahoo.com/quote/{quote.asset_id}",
        updated_at=as_of,
        is_live=True,
    )


def _build_guidance(*, recommendation: str, target_price: float | None) -> str:
    normalized = recommendation.strip().replace("_", " ")
    if target_price is not None and normalized:
        return f"分析师共识：{normalized}，目标价约 {target_price:.2f}。"
    if target_price is not None:
        return f"当前暂无明确业绩指引，市场目标价约 {target_price:.2f}。"
    if normalized:
        return f"分析师共识：{normalized}。"
    return "当前暂无明确业绩指引。"


def _build_sentiment(recommendation: str) -> str:
    normalized = recommendation.strip().lower()
    if normalized in {"strong_buy", "buy"}:
        return "Constructive"
    if normalized in {"sell", "strong_sell"}:
        return "Cautious"
    if normalized == "hold":
        return "Neutral"
    return "Balanced"


def _extract_eps_yoy(history: object) -> float | None:
    if not isinstance(history, dict):
        return None
    records = history.get("history")
    if not isinstance(records, list) or len(records) < 2:
        return None
    latest = _extract_number(_extract_eps_actual(records[0]))
    previous = _extract_number(_extract_eps_actual(records[1]))
    if latest is None or previous is None or previous == 0:
        return None
    return round((latest - previous) / abs(previous), 6)


def _extract_eps_actual(record: object) -> object:
    if not isinstance(record, dict):
        return None
    eps_actual = record.get("epsActual")
    return eps_actual


def _extract_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        return _extract_number(value.get("raw"))
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _to_datetime_utc(timestamp: float | None) -> datetime:
    if timestamp is None:
        return datetime.now(UTC)
    try:
        return datetime.fromtimestamp(timestamp, tz=UTC)
    except Exception:
        return datetime.now(UTC)
