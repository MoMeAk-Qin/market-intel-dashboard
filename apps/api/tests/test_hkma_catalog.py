from __future__ import annotations

from datetime import datetime, timezone

from app.sources.hkma_catalog import (
    HKMACatalog,
    HKMAEndpointCatalog,
    HKMAFieldMeta,
    HKMAOpenAPIEndpoint,
    HKMAOpenAPISummary,
    HKMAQueryParam,
    HKMARecordField,
    build_hkma_endpoints_value,
    build_hkma_units_map,
    normalize_hkma_catalog,
    validate_hkma_catalog,
)


def _make_endpoint(
    *,
    api_url: str,
    doc_url: str,
    fields_meta: list[HKMAFieldMeta],
    query_params: list[HKMAQueryParam],
    record_fields: list[HKMARecordField],
) -> HKMAEndpointCatalog:
    return HKMAEndpointCatalog(
        frequency="daily",
        doc_url=doc_url,
        api_url=api_url,
        openapi_summary=HKMAOpenAPISummary(
            base_url="https://api.hkma.gov.hk/public",
            endpoints=[HKMAOpenAPIEndpoint(method="get", url=api_url)],
            query_params=query_params,
            record_fields=record_fields,
        ),
        fields_meta=fields_meta,
    )


def test_normalize_hkma_catalog_dedupes_and_prefers_higher_quality() -> None:
    api_url = "https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/example"
    doc_url = "https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/daily-monetary-statistics/example/"
    low_quality = _make_endpoint(
        api_url=api_url,
        doc_url=doc_url,
        fields_meta=[],
        query_params=[HKMAQueryParam(name="to")],
        record_fields=[],
    )
    high_quality = _make_endpoint(
        api_url=api_url,
        doc_url=doc_url,
        fields_meta=[
            HKMAFieldMeta(name="metric_b", unit_of_measure="bp"),
            HKMAFieldMeta(name="metric_a", unit_of_measure="%"),
        ],
        query_params=[HKMAQueryParam(name="from"), HKMAQueryParam(name="to")],
        record_fields=[HKMARecordField(name="metric_a", type="number")],
    )
    catalog = HKMACatalog(
        generated_at=datetime.now(timezone.utc),
        source_root="https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/",
        endpoints=[low_quality, high_quality],
    )

    normalized = normalize_hkma_catalog(catalog)
    assert len(normalized.endpoints) == 1
    endpoint = normalized.endpoints[0]
    assert [item.name for item in endpoint.fields_meta] == ["metric_a", "metric_b"]
    assert [item.name for item in endpoint.openapi_summary.query_params] == ["from", "to"]
    assert validate_hkma_catalog(normalized) == []


def test_build_hkma_endpoints_and_units_are_stable() -> None:
    endpoint = _make_endpoint(
        api_url="https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/example",
        doc_url="https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/daily-monetary-statistics/example/",
        fields_meta=[
            HKMAFieldMeta(name="metric_b", unit_of_measure="bp"),
            HKMAFieldMeta(name="metric_a", unit_of_measure="%"),
        ],
        query_params=[HKMAQueryParam(name="to"), HKMAQueryParam(name="from")],
        record_fields=[],
    )
    catalog = HKMACatalog(
        generated_at=datetime.now(timezone.utc),
        source_root="https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/",
        endpoints=[endpoint, endpoint],
    )
    normalized = normalize_hkma_catalog(catalog)
    endpoints_value = build_hkma_endpoints_value(normalized)
    units_map = build_hkma_units_map(normalized)

    assert endpoints_value == endpoint.api_url
    assert list(units_map[endpoint.api_url].keys()) == ["metric_a", "metric_b"]


def test_validate_hkma_catalog_reports_invalid_urls() -> None:
    endpoint = _make_endpoint(
        api_url="https://example.com/not-hkma",
        doc_url="https://example.com/not-doc",
        fields_meta=[],
        query_params=[],
        record_fields=[],
    )
    catalog = HKMACatalog(
        generated_at=datetime.now(timezone.utc),
        source_root="https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/",
        endpoints=[endpoint],
    )
    issues = validate_hkma_catalog(catalog)
    assert any("invalid api_url prefix" in issue for issue in issues)
    assert any("invalid doc_url prefix" in issue for issue in issues)
