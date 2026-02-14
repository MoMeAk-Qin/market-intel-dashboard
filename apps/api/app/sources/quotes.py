from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Literal
from urllib.parse import quote

import httpx

from ..config import AppConfig
from ..models import QuotePoint, QuoteSeries, QuoteSnapshot
from ..services.http_client import request_with_retry

logger = logging.getLogger("source.quotes")

RangeKey = Literal["1D", "1W", "1M", "1Y"]

_ASSET_TO_SYMBOL: dict[str, str] = {
    "AAPL": "AAPL",
    "NASDAQ": "^NDX",
    "DXY": "DX-Y.NYB",
    "XAUUSD": "GC=F",
    "US10Y": "^TNX",
    "0700.HK": "0700.HK",
}
_SYMBOL_TO_ASSET = {symbol: asset_id for asset_id, symbol in _ASSET_TO_SYMBOL.items()}
_RANGE_TO_QUERY: dict[RangeKey, tuple[str, str]] = {
    "1D": ("5d", "1d"),
    "1W": ("1mo", "1d"),
    "1M": ("3mo", "1d"),
    "1Y": ("1y", "1wk"),
}


def supports_asset_quotes(asset_id: str) -> bool:
    return asset_id in _ASSET_TO_SYMBOL


async def fetch_quote_snapshots(
    config: AppConfig,
    *,
    asset_ids: list[str] | None = None,
) -> dict[str, QuoteSnapshot]:
    selected_assets = [asset_id for asset_id in (asset_ids or list(_ASSET_TO_SYMBOL.keys())) if supports_asset_quotes(asset_id)]
    if not selected_assets:
        return {}
    symbols = [_ASSET_TO_SYMBOL[asset_id] for asset_id in selected_assets]

    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(config.http_timeout, read=config.http_timeout)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        response = await request_with_retry(
            client,
            "GET",
            config.quotes_api_url,
            retries=config.http_retries,
            backoff=config.http_backoff,
            logger=logger,
            params={"symbols": ",".join(symbols)},
        )

    if response.status_code >= 400:
        logger.warning("quotes_snapshot_status_failed status=%s", response.status_code)
        return {}
    try:
        payload = response.json()
    except ValueError:
        logger.warning("quotes_snapshot_invalid_json")
        return {}

    return _parse_quote_snapshot_payload(payload)


async def fetch_quote_series(
    config: AppConfig,
    *,
    asset_id: str,
    range_key: RangeKey,
) -> QuoteSeries | None:
    symbol = _ASSET_TO_SYMBOL.get(asset_id)
    if symbol is None:
        return None
    period, interval = _RANGE_TO_QUERY[range_key]
    url = f"{config.quotes_chart_api_base_url.rstrip('/')}/{quote(symbol, safe='')}"

    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(config.http_timeout, read=config.http_timeout)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        response = await request_with_retry(
            client,
            "GET",
            url,
            retries=config.http_retries,
            backoff=config.http_backoff,
            logger=logger,
            params={"range": period, "interval": interval},
        )

    if response.status_code >= 400:
        logger.warning("quotes_series_status_failed asset=%s status=%s", asset_id, response.status_code)
        return None
    try:
        payload = response.json()
    except ValueError:
        logger.warning("quotes_series_invalid_json asset=%s", asset_id)
        return None

    return _parse_quote_series_payload(asset_id=asset_id, range_key=range_key, payload=payload)


def _parse_quote_snapshot_payload(payload: object) -> dict[str, QuoteSnapshot]:
    if not isinstance(payload, dict):
        return {}
    response_block = payload.get("quoteResponse")
    if not isinstance(response_block, dict):
        return {}
    results = response_block.get("result")
    if not isinstance(results, list):
        return {}

    snapshots: dict[str, QuoteSnapshot] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        symbol_raw = item.get("symbol")
        if not isinstance(symbol_raw, str):
            continue
        asset_id = _SYMBOL_TO_ASSET.get(symbol_raw)
        if asset_id is None:
            continue

        price = _to_float(item.get("regularMarketPrice"))
        if price is None:
            continue
        change = _to_float(item.get("regularMarketChange"))
        change_pct = _to_float(item.get("regularMarketChangePercent"))

        if asset_id == "US10Y":
            price = price / 10.0
            change = None if change is None else change / 10.0

        market_time = item.get("regularMarketTime")
        as_of = _to_datetime_utc(market_time)
        currency = item.get("currency") if isinstance(item.get("currency"), str) else None

        snapshots[asset_id] = QuoteSnapshot(
            asset_id=asset_id,
            price=round(price, 6),
            change=None if change is None else round(change, 6),
            change_pct=None if change_pct is None else round(change_pct, 6),
            currency=currency,
            as_of=as_of,
            source="yahoo",
            is_fallback=False,
        )

    return snapshots


def _parse_quote_series_payload(
    *,
    asset_id: str,
    range_key: RangeKey,
    payload: object,
) -> QuoteSeries | None:
    if not isinstance(payload, dict):
        return None
    chart = payload.get("chart")
    if not isinstance(chart, dict):
        return None
    result = chart.get("result")
    if not isinstance(result, list) or not result:
        return None
    first = result[0]
    if not isinstance(first, dict):
        return None

    timestamps_raw = first.get("timestamp")
    indicators = first.get("indicators")
    if not isinstance(timestamps_raw, list) or not isinstance(indicators, dict):
        return None
    quote_block = indicators.get("quote")
    if not isinstance(quote_block, list) or not quote_block:
        return None
    quote_item = quote_block[0]
    if not isinstance(quote_item, dict):
        return None
    close_values_raw = quote_item.get("close")
    if not isinstance(close_values_raw, list):
        return None

    deduped_by_date: dict[datetime, float] = {}
    for ts_raw, close_raw in zip(timestamps_raw, close_values_raw):
        close_value = _to_float(close_raw)
        if close_value is None:
            continue
        ts = _to_datetime_utc(ts_raw)
        day = datetime(ts.year, ts.month, ts.day, tzinfo=UTC)
        adjusted = close_value / 10.0 if asset_id == "US10Y" else close_value
        deduped_by_date[day] = adjusted

    if not deduped_by_date:
        return None

    ordered_points = [
        QuotePoint(time=day, value=round(value, 6))
        for day, value in sorted(deduped_by_date.items(), key=lambda item: item[0])
    ]

    return QuoteSeries(
        asset_id=asset_id,
        range=range_key,
        source="yahoo",
        is_fallback=False,
        points=ordered_points,
    )


def _to_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _to_datetime_utc(value: object) -> datetime:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except Exception:
            return datetime.now(UTC)
    return datetime.now(UTC)
