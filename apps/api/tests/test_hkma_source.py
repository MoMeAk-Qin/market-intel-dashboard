from __future__ import annotations

from app.sources.hkma import (
    _HKMAEndpointRuntime,
    _build_event_from_metrics,
    _records_to_metric_points,
)


def test_records_to_metric_points_monthly_end_of_month() -> None:
    endpoint = _HKMAEndpointRuntime(
        frequency="monthly",
        api_url="https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/monetary-statistics",
        doc_url="https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/monetary-statistics/",
        query_params=("from", "to", "offset", "pagesize"),
        field_units={"m1_total": "HK$ million"},
        field_descriptions={"m1_total": "M1 aggregate"},
    )
    records = [
        {"end_of_month": "2024-01", "m1_total": "1200.5", "m2_total": "3456.0"},
    ]
    points = _records_to_metric_points(endpoint, records)
    assert len(points) == 2
    assert all(point.date.isoformat() == "2024-01-31" for point in points)
    assert points[0].series_id.startswith("HKMA.")
    assert points[0].provider == "HKMA"
    assert points[0].unit_norm in {"HKD_mn", None}


def test_build_event_from_metrics_uses_latest_snapshot() -> None:
    endpoint = _HKMAEndpointRuntime(
        frequency="daily",
        api_url="https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-of-interbank-liquidity",
        doc_url="https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/daily-monetary-statistics/daily-figures-of-interbank-liquidity/",
        query_params=("from", "to"),
        field_units={},
        field_descriptions={},
    )
    records = [
        {"end_of_day": "2024-01-01", "hibor_overnight": "4.7"},
        {"end_of_day": "2024-01-02", "hibor_overnight": "4.9"},
    ]
    points = _records_to_metric_points(endpoint, records)
    event = _build_event_from_metrics(endpoint=endpoint, metric_points=points, max_fields=6)
    assert event is not None
    assert event.event_time.date().isoformat() == "2024-01-02"
    assert len(event.numbers) == 1
    assert event.numbers[0].name == "hibor_overnight"
    assert event.numbers[0].unit is None


def test_records_to_metric_points_supports_compact_date_and_negative_number() -> None:
    endpoint = _HKMAEndpointRuntime(
        frequency="daily",
        api_url="https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/example",
        doc_url="https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/daily-monetary-statistics/example/",
        query_params=("from", "to"),
        field_units={"metric_a": "HK$ million"},
        field_descriptions={"metric_a": "sample metric"},
    )
    records = [{"end_of_date": "20240131", "metric_a": "(1,234.5)"}]
    points = _records_to_metric_points(endpoint, records)
    assert len(points) == 1
    assert points[0].date.isoformat() == "2024-01-31"
    assert points[0].value == -1234.5
    assert points[0].unit_norm == "HKD_mn"
