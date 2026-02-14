from __future__ import annotations

from app.sources.quotes import _parse_quote_series_payload, _parse_quote_snapshot_payload


def test_parse_quote_snapshot_payload_maps_symbols_and_normalizes_us10y() -> None:
    payload = {
        "quoteResponse": {
            "result": [
                {
                    "symbol": "^TNX",
                    "regularMarketPrice": 41.23,
                    "regularMarketChange": -0.11,
                    "regularMarketChangePercent": -0.27,
                    "regularMarketTime": 1704067200,
                    "currency": "USD",
                },
                {
                    "symbol": "AAPL",
                    "regularMarketPrice": "189.50",
                    "regularMarketChange": "1.20",
                    "regularMarketChangePercent": "0.64",
                    "regularMarketTime": 1704067200,
                    "currency": "USD",
                },
            ]
        }
    }

    snapshots = _parse_quote_snapshot_payload(payload)
    assert set(snapshots.keys()) == {"US10Y", "AAPL"}

    us10y = snapshots["US10Y"]
    assert us10y.price == 4.123
    assert us10y.change == -0.011
    assert us10y.change_pct == -0.27
    assert us10y.source == "yahoo"
    assert us10y.is_fallback is False

    aapl = snapshots["AAPL"]
    assert aapl.price == 189.5
    assert aapl.change == 1.2
    assert aapl.change_pct == 0.64
    assert aapl.source == "yahoo"
    assert aapl.is_fallback is False


def test_parse_quote_series_payload_dedupes_daily_points_and_normalizes_us10y() -> None:
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1704067200, 1704070800, 1704153600],
                    "indicators": {
                        "quote": [
                            {
                                "close": [40.0, 41.0, 42.0],
                            }
                        ]
                    },
                }
            ]
        }
    }

    series = _parse_quote_series_payload(asset_id="US10Y", range_key="1M", payload=payload)

    assert series is not None
    assert series.asset_id == "US10Y"
    assert series.range == "1M"
    assert series.source == "yahoo"
    assert series.is_fallback is False
    assert [item.time.date().isoformat() for item in series.points] == ["2024-01-01", "2024-01-02"]
    assert [item.value for item in series.points] == [4.1, 4.2]


def test_parse_quote_series_payload_returns_none_for_invalid_shape() -> None:
    assert _parse_quote_series_payload(asset_id="AAPL", range_key="1W", payload={"chart": {}}) is None
