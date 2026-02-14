from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import logging
import re
from typing import Literal
from urllib.parse import parse_qsl, urlparse
from uuid import uuid4

import httpx

from ..config import AppConfig
from ..models import Event, EventEvidence, EventNumber, MetricPoint
from ..services.http_client import request_with_retry
from .hkma_catalog import HKMACatalog, load_hkma_catalog

logger = logging.getLogger("source.hkma")

_DATE_KEYS = (
    "date",
    "time_period",
    "end_of_day",
    "end_of_month",
    "ref_date",
    "as_of_date",
)
_SKIP_VALUE_KEYS = {"record_id", "offset", "page", "pagesize"}
_UNIT_NORMALIZATION = {
    "hk$ million": "HKD_mn",
    "hkd million": "HKD_mn",
    "hk$ mn": "HKD_mn",
    "hkd mn": "HKD_mn",
    "hk$ billion": "HKD_bn",
    "hkd billion": "HKD_bn",
    "basis points": "bp",
    "basis point": "bp",
    "bp": "bp",
    "%": "pct",
    "% per annum": "pct_pa",
    "percent": "pct",
    "percentage": "pct",
    "rmb million": "CNY_mn",
    "usd/hkd for value spot": "USDHKD_spot",
    "quantity": "count",
    "hk$": "HKD",
}


@dataclass(frozen=True, slots=True)
class _HKMAEndpointRuntime:
    frequency: Literal["daily", "monthly"]
    api_url: str
    doc_url: str
    query_params: tuple[str, ...]
    field_units: dict[str, str]
    field_descriptions: dict[str, str]


async def fetch_hkma_events(config: AppConfig) -> list[Event]:
    grouped_points = await _fetch_metric_points_grouped_by_endpoint(config)
    events: list[Event] = []
    for endpoint, metric_points in grouped_points:
        event = _build_event_from_metrics(
            endpoint=endpoint,
            metric_points=metric_points,
            max_fields=config.hkma_max_fields,
        )
        if event is not None:
            events.append(event)
    return events


async def fetch_hkma_metric_points(config: AppConfig) -> list[MetricPoint]:
    grouped_points = await _fetch_metric_points_grouped_by_endpoint(config)
    metric_points: list[MetricPoint] = []
    for _, points in grouped_points:
        metric_points.extend(points)
    return metric_points


async def _fetch_metric_points_grouped_by_endpoint(
    config: AppConfig,
) -> list[tuple[_HKMAEndpointRuntime, list[MetricPoint]]]:
    endpoints = _load_endpoints(config)
    if not endpoints:
        return []

    headers = {"User-Agent": config.user_agent}
    timeout = httpx.Timeout(config.http_timeout, read=config.http_timeout)
    grouped: list[tuple[_HKMAEndpointRuntime, list[MetricPoint]]] = []
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        for endpoint in endpoints:
            records = await _fetch_records(
                client=client,
                endpoint=endpoint,
                config=config,
            )
            if not records:
                continue
            metric_points = _records_to_metric_points(endpoint, records)
            if metric_points:
                grouped.append((endpoint, metric_points))
    return grouped


def _load_endpoints(config: AppConfig) -> list[_HKMAEndpointRuntime]:
    catalog = load_hkma_catalog(config.hkma_catalog_path)
    if catalog and catalog.endpoints:
        return _load_endpoints_from_catalog(catalog)
    return [
        _HKMAEndpointRuntime(
            frequency="daily",
            api_url=url,
            doc_url=url,
            query_params=tuple(name for name, _ in parse_qsl(urlparse(url).query)),
            field_units={},
            field_descriptions={},
        )
        for url in config.hkma_endpoints
    ]


def _load_endpoints_from_catalog(catalog: HKMACatalog) -> list[_HKMAEndpointRuntime]:
    endpoints: list[_HKMAEndpointRuntime] = []
    for item in catalog.endpoints:
        units: dict[str, str] = {}
        descriptions: dict[str, str] = {}
        for field in item.fields_meta:
            if field.unit_of_measure:
                units[field.name] = field.unit_of_measure
            if field.description:
                descriptions[field.name] = field.description
        for record_field in item.openapi_summary.record_fields:
            if record_field.description and record_field.name not in descriptions:
                descriptions[record_field.name] = record_field.description
        endpoints.append(
            _HKMAEndpointRuntime(
                frequency=item.frequency,
                api_url=item.api_url,
                doc_url=item.doc_url,
                query_params=tuple(param.name for param in item.openapi_summary.query_params),
                field_units=units,
                field_descriptions=descriptions,
            )
        )
    return endpoints


async def _fetch_records(
    *,
    client: httpx.AsyncClient,
    endpoint: _HKMAEndpointRuntime,
    config: AppConfig,
) -> list[dict]:
    base_params = _build_base_query(endpoint=endpoint, config=config)
    supports_paging = _supports_paging(endpoint.query_params)
    page_size = max(config.hkma_page_size, 1)
    all_records: list[dict] = []
    offset = 0
    max_pages = 5

    for _ in range(max_pages):
        params = dict(base_params)
        if supports_paging:
            _set_query_param(params, endpoint.query_params, {"offset"}, str(offset))
            _set_query_param(params, endpoint.query_params, {"pagesize", "page_size"}, str(page_size))
        payload = await _request_payload(
            client=client,
            url=endpoint.api_url,
            params=params,
            retries=config.http_retries,
            backoff=config.http_backoff,
        )
        if payload is None:
            break
        batch = _extract_records(payload)
        if not batch:
            break
        all_records.extend(batch)
        if not supports_paging or len(batch) < page_size:
            break
        offset += len(batch)

    return all_records


def _build_base_query(*, endpoint: _HKMAEndpointRuntime, config: AppConfig) -> dict[str, str]:
    params: dict[str, str] = {}
    if _match_param(endpoint.query_params, {"format"}) is not None:
        _set_query_param(params, endpoint.query_params, {"format"}, "json")

    now = datetime.now(timezone.utc).date()
    from_value = None
    if endpoint.frequency == "daily":
        from_value = (now - timedelta(days=max(config.hkma_daily_lookback_days, 1))).strftime("%Y-%m-%d")
    if endpoint.frequency == "monthly":
        from_value = _shift_months(now, -max(config.hkma_monthly_lookback_months, 1)).strftime("%Y-%m-%d")
    to_value = now.strftime("%Y-%m-%d")

    if from_value:
        _set_query_param(
            params,
            endpoint.query_params,
            {"from", "from_date", "start_date", "date_from"},
            from_value,
        )
    _set_query_param(
        params,
        endpoint.query_params,
        {"to", "to_date", "end_date", "date_to"},
        to_value,
    )
    return params


def _supports_paging(query_params: tuple[str, ...]) -> bool:
    return _match_param(query_params, {"offset"}) is not None and (
        _match_param(query_params, {"pagesize", "page_size"}) is not None
    )


async def _request_payload(
    *,
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, str],
    retries: int,
    backoff: float,
) -> dict | list | None:
    try:
        response = await request_with_retry(
            client,
            "GET",
            url,
            retries=retries,
            backoff=backoff,
            logger=logger,
            params=params or None,
        )
    except Exception as exc:
        logger.warning("hkma_fetch_failed endpoint=%s error=%s", url, exc)
        return None
    if response.status_code >= 400:
        logger.warning("hkma_fetch_status_failed endpoint=%s status=%s", url, response.status_code)
        return None
    try:
        return response.json()
    except ValueError:
        logger.warning("hkma_fetch_invalid_json endpoint=%s", url)
        return None


def _extract_records(payload: dict | list) -> list[dict]:
    if isinstance(payload, dict):
        if "result" in payload and isinstance(payload["result"], dict):
            result = payload["result"]
            for key in ("records", "data"):
                value = result.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        if "data" in payload and isinstance(payload["data"], list):
            return [item for item in payload["data"] if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _records_to_metric_points(
    endpoint: _HKMAEndpointRuntime,
    records: list[dict],
) -> list[MetricPoint]:
    metric_points: list[MetricPoint] = []
    api_slug = _build_api_slug(endpoint.api_url)
    for record in records:
        record_date = _extract_record_date(record, endpoint.frequency)
        if record_date is None:
            continue
        for field_name, raw_value in record.items():
            if _is_date_like_field(field_name):
                continue
            if field_name.lower() in _SKIP_VALUE_KEYS:
                continue
            numeric = _coerce_float(raw_value)
            if numeric is None:
                continue
            unit_raw = endpoint.field_units.get(field_name)
            metric_points.append(
                MetricPoint(
                    provider="HKMA",
                    series_id=_build_series_id(api_slug, field_name),
                    frequency=endpoint.frequency,
                    date=record_date,
                    value=numeric,
                    unit_raw=unit_raw,
                    unit_norm=_normalize_unit(unit_raw),
                    description=endpoint.field_descriptions.get(field_name),
                    api_url=endpoint.api_url,
                    field_name=field_name,
                )
            )
    return metric_points


def _build_event_from_metrics(
    *,
    endpoint: _HKMAEndpointRuntime,
    metric_points: list[MetricPoint],
    max_fields: int,
) -> Event | None:
    if not metric_points:
        return None
    latest_date = max(point.date for point in metric_points)
    latest_points = [point for point in metric_points if point.date == latest_date]
    if not latest_points:
        return None
    latest_points.sort(key=lambda item: item.series_id)
    numbers = [
        EventNumber(
            name=point.field_name,
            value=point.value,
            unit=point.unit_raw,
            period=point.frequency,
            source_quote_id=point.series_id,
        )
        for point in latest_points[:max_fields]
    ]
    if not numbers:
        return None

    api_slug = _build_api_slug(endpoint.api_url)
    event_time = datetime.combine(latest_date, datetime.min.time(), tzinfo=timezone.utc)
    headline = f"HKMA {api_slug} update"
    summary = f"HKMA {endpoint.frequency} snapshot ({len(latest_points)} metrics)."
    markets = ["HK", "RATES"]
    if _contains_fx_signal(api_slug):
        markets = ["HK", "FX"]
    return Event(
        event_id=str(uuid4()),
        event_time=event_time,
        ingest_time=datetime.now(timezone.utc),
        source_type="macro_data",
        publisher="HKMA",
        headline=headline,
        summary=summary,
        event_type="macro_release",
        markets=markets,
        tickers=[],
        instruments=["HKMA"],
        sectors=["Industrials"],
        numbers=numbers,
        stance="neutral",
        impact=56,
        confidence=0.6,
        impact_chain=[
            "HKMA data update informs HKD funding conditions",
            "Rates desks revise short-term liquidity assumptions",
            "HKD-linked assets react to refreshed signals",
        ],
        evidence=[
            EventEvidence(
                quote_id=f"HKMA-{uuid4().hex[:8]}",
                source_url=endpoint.api_url,
                title=headline,
                published_at=event_time,
                excerpt=f"Doc: {endpoint.doc_url}",
            )
        ],
        related_event_ids=None,
    )


def _contains_fx_signal(api_slug: str) -> bool:
    lowered = api_slug.lower()
    return any(token in lowered for token in ("exchange", "fx", "usd_hkd", "usdhkd"))


def _extract_record_date(record: dict, frequency: Literal["daily", "monthly"]) -> date | None:
    for key in _DATE_KEYS:
        value = record.get(key)
        parsed = _parse_date(value, frequency)
        if parsed is not None:
            return parsed
    for key, value in record.items():
        if _is_date_like_field(key):
            parsed = _parse_date(value, frequency)
            if parsed is not None:
                return parsed
    return None


def _parse_date(raw: object, frequency: Literal["daily", "monthly"]) -> date | None:
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    for fmt in ("%Y-%m", "%Y/%m", "%Y%m"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if frequency == "monthly":
            last_day = calendar.monthrange(parsed.year, parsed.month)[1]
            return date(parsed.year, parsed.month, last_day)
        return date(parsed.year, parsed.month, 1)
    return None


def _is_date_like_field(field_name: str) -> bool:
    lowered = field_name.lower()
    return lowered in _DATE_KEYS or "date" in lowered or "time_period" in lowered


def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    normalized = value.strip().replace(",", "")
    if not normalized or normalized in {"-", "--", "N/A", "n/a"}:
        return None
    if normalized.startswith("(") and normalized.endswith(")"):
        normalized = f"-{normalized[1:-1]}"
    if normalized.startswith("+"):
        normalized = normalized[1:]
    if normalized.endswith("%"):
        normalized = normalized[:-1]
    try:
        return float(normalized)
    except ValueError:
        return None


def _build_api_slug(api_url: str) -> str:
    parsed = urlparse(api_url)
    segments = [segment for segment in parsed.path.split("/") if segment and segment != "public"]
    if not segments:
        return "UNKNOWN"
    slug_parts = [_normalize_token(segment) for segment in segments]
    return "_".join(part for part in slug_parts if part)


def _build_series_id(api_slug: str, field_name: str) -> str:
    return f"HKMA.{api_slug}.{_normalize_token(field_name)}".upper()


def _normalize_token(value: str) -> str:
    normalized = re.sub(r"[^0-9a-zA-Z]+", "_", value.strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "UNKNOWN"


def _normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    key = unit.strip().lower()
    if not key:
        return None
    return _UNIT_NORMALIZATION.get(key, key.replace(" ", "_"))


def _match_param(query_params: tuple[str, ...], candidates: set[str]) -> str | None:
    lowered = {candidate.lower() for candidate in candidates}
    for name in query_params:
        if name.lower() in lowered:
            return name
    return None


def _set_query_param(
    params: dict[str, str],
    query_params: tuple[str, ...],
    candidates: set[str],
    value: str,
) -> None:
    match = _match_param(query_params, candidates)
    if match is not None:
        params[match] = value


def _shift_months(value: date, delta_months: int) -> date:
    year = value.year
    month = value.month + delta_months
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
