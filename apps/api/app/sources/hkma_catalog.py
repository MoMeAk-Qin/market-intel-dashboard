from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field

HKMAFrequency = Literal["daily", "monthly"]
_HKMA_API_PREFIX = "https://api.hkma.gov.hk/public/"
_HKMA_DOC_PREFIX = "https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/"


class HKMAQueryParam(BaseModel):
    name: str
    location: str = "query"
    required: bool = False
    schema_type: str | None = None
    schema_format: str | None = None
    description: str | None = None


class HKMARecordField(BaseModel):
    name: str
    type: str | None = None
    format: str | None = None
    description: str | None = None


class HKMAOpenAPIEndpoint(BaseModel):
    method: str
    url: str


class HKMAOpenAPISummary(BaseModel):
    base_url: str
    endpoints: list[HKMAOpenAPIEndpoint] = Field(default_factory=list)
    query_params: list[HKMAQueryParam] = Field(default_factory=list)
    record_fields: list[HKMARecordField] = Field(default_factory=list)


class HKMAFieldMeta(BaseModel):
    name: str
    type: str | None = None
    unit_of_measure: str | None = None
    description: str | None = None


class HKMAEndpointCatalog(BaseModel):
    frequency: HKMAFrequency
    doc_url: str
    api_url: str
    openapi_summary: HKMAOpenAPISummary
    fields_meta: list[HKMAFieldMeta] = Field(default_factory=list)


class HKMACatalog(BaseModel):
    generated_at: datetime
    source_root: str
    endpoints: list[HKMAEndpointCatalog] = Field(default_factory=list)


def load_hkma_catalog(path: str | Path) -> HKMACatalog | None:
    catalog_path = Path(path)
    if not catalog_path.exists():
        return None
    try:
        content = catalog_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not content.strip():
        return None
    try:
        return HKMACatalog.model_validate_json(content)
    except Exception:
        return None


def build_hkma_endpoints_value(catalog: HKMACatalog) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for endpoint in catalog.endpoints:
        if endpoint.api_url in seen:
            continue
        seen.add(endpoint.api_url)
        ordered.append(endpoint.api_url)
    return ",".join(ordered)


def build_hkma_units_map(catalog: HKMACatalog) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for endpoint in catalog.endpoints:
        endpoint_map_unsorted: dict[str, str] = {}
        for field_meta in sorted(endpoint.fields_meta, key=lambda item: item.name.lower()):
            if field_meta.unit_of_measure:
                endpoint_map_unsorted[field_meta.name] = field_meta.unit_of_measure
        endpoint_map = {
            key: endpoint_map_unsorted[key]
            for key in sorted(endpoint_map_unsorted.keys(), key=str.lower)
        }
        if endpoint_map:
            mapping[endpoint.api_url] = endpoint_map
    return mapping


def normalize_hkma_catalog(catalog: HKMACatalog) -> HKMACatalog:
    deduped_by_api: dict[str, HKMAEndpointCatalog] = {}
    for endpoint in catalog.endpoints:
        normalized = _normalize_endpoint(endpoint)
        existing = deduped_by_api.get(normalized.api_url)
        if existing is None or _endpoint_quality(normalized) > _endpoint_quality(existing):
            deduped_by_api[normalized.api_url] = normalized

    normalized_endpoints = sorted(
        deduped_by_api.values(),
        key=lambda item: (item.frequency, item.api_url),
    )
    return HKMACatalog(
        generated_at=catalog.generated_at,
        source_root=catalog.source_root,
        endpoints=normalized_endpoints,
    )


def validate_hkma_catalog(catalog: HKMACatalog) -> list[str]:
    issues: list[str] = []
    seen_api_urls: set[str] = set()
    for endpoint in catalog.endpoints:
        if endpoint.api_url in seen_api_urls:
            issues.append(f"duplicate api_url: {endpoint.api_url}")
        seen_api_urls.add(endpoint.api_url)

        if not endpoint.api_url.startswith(_HKMA_API_PREFIX):
            issues.append(f"invalid api_url prefix: {endpoint.api_url}")
        if not endpoint.doc_url.startswith(_HKMA_DOC_PREFIX):
            issues.append(f"invalid doc_url prefix: {endpoint.doc_url}")
        if not endpoint.openapi_summary.base_url:
            issues.append(f"missing openapi base_url: {endpoint.api_url}")

        if not endpoint.fields_meta and not endpoint.openapi_summary.record_fields:
            issues.append(f"missing fields metadata: {endpoint.api_url}")

        for operation in endpoint.openapi_summary.endpoints:
            if not operation.url:
                issues.append(f"empty openapi endpoint url: {endpoint.api_url}")
            if not operation.method:
                issues.append(f"empty openapi endpoint method: {endpoint.api_url}")
        for query in endpoint.openapi_summary.query_params:
            if not query.name:
                issues.append(f"empty query param name: {endpoint.api_url}")
        for record_field in endpoint.openapi_summary.record_fields:
            if not record_field.name:
                issues.append(f"empty record field name: {endpoint.api_url}")

    return issues


def _normalize_endpoint(endpoint: HKMAEndpointCatalog) -> HKMAEndpointCatalog:
    return HKMAEndpointCatalog(
        frequency=endpoint.frequency,
        doc_url=_normalize_url(endpoint.doc_url),
        api_url=_normalize_url(endpoint.api_url),
        openapi_summary=HKMAOpenAPISummary(
            base_url=_normalize_url(endpoint.openapi_summary.base_url),
            endpoints=_dedupe_openapi_endpoints(endpoint.openapi_summary.endpoints),
            query_params=_dedupe_query_params(endpoint.openapi_summary.query_params),
            record_fields=_dedupe_record_fields(endpoint.openapi_summary.record_fields),
        ),
        fields_meta=_dedupe_field_meta(endpoint.fields_meta),
    )


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()
    normalized = parsed._replace(fragment="")
    return normalized.geturl().rstrip("/")


def _dedupe_openapi_endpoints(
    endpoints: list[HKMAOpenAPIEndpoint],
) -> list[HKMAOpenAPIEndpoint]:
    deduped: dict[tuple[str, str], HKMAOpenAPIEndpoint] = {}
    for endpoint in endpoints:
        key = (endpoint.method.upper(), _normalize_url(endpoint.url))
        deduped[key] = HKMAOpenAPIEndpoint(method=key[0], url=key[1])
    return sorted(deduped.values(), key=lambda item: (item.url, item.method))


def _dedupe_query_params(params: list[HKMAQueryParam]) -> list[HKMAQueryParam]:
    deduped: dict[tuple[str, str], HKMAQueryParam] = {}
    for param in params:
        key = (param.name, param.location)
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = param
            continue
        if _query_param_quality(param) > _query_param_quality(existing):
            deduped[key] = param
    return sorted(deduped.values(), key=lambda item: (item.location, item.name))


def _dedupe_record_fields(fields: list[HKMARecordField]) -> list[HKMARecordField]:
    deduped: dict[str, HKMARecordField] = {}
    for field in fields:
        existing = deduped.get(field.name)
        if existing is None:
            deduped[field.name] = field
            continue
        if _record_field_quality(field) > _record_field_quality(existing):
            deduped[field.name] = field
    return sorted(deduped.values(), key=lambda item: item.name.lower())


def _dedupe_field_meta(fields: list[HKMAFieldMeta]) -> list[HKMAFieldMeta]:
    deduped: dict[str, HKMAFieldMeta] = {}
    for field in fields:
        existing = deduped.get(field.name)
        if existing is None:
            deduped[field.name] = field
            continue
        if _field_meta_quality(field) > _field_meta_quality(existing):
            deduped[field.name] = field
    return sorted(deduped.values(), key=lambda item: item.name.lower())


def _query_param_quality(item: HKMAQueryParam) -> int:
    return int(item.required) + int(bool(item.schema_type)) + int(bool(item.description))


def _record_field_quality(item: HKMARecordField) -> int:
    return int(bool(item.type)) + int(bool(item.format)) + int(bool(item.description))


def _field_meta_quality(item: HKMAFieldMeta) -> int:
    return int(bool(item.type)) + int(bool(item.unit_of_measure)) + int(bool(item.description))


def _endpoint_quality(item: HKMAEndpointCatalog) -> int:
    return (
        len(item.fields_meta) * 3
        + len(item.openapi_summary.record_fields) * 2
        + len(item.openapi_summary.query_params)
        + len(item.openapi_summary.endpoints)
    )
