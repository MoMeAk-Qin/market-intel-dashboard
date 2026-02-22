from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import DataOrigin, Event, EventEvidence, Market, QuoteSnapshot


def _make_event(
    *,
    event_id: str,
    headline: str,
    summary: str,
    tickers: list[str],
    instruments: list[str],
    markets: list[Market],
    impact: int,
    confidence: float,
    data_origin: DataOrigin = "live",
) -> Event:
    now = datetime(2026, 2, 22, 10, 0, tzinfo=timezone.utc)
    return Event(
        event_id=event_id,
        event_time=now,
        ingest_time=now,
        source_type="news",
        publisher="Test Wire",
        headline=headline,
        summary=summary,
        event_type="risk",
        markets=markets,
        tickers=tickers,
        instruments=instruments,
        sectors=["Tech"],
        numbers=[],
        stance="neutral",
        impact=impact,
        confidence=confidence,
        impact_chain=[
            "政策与需求预期变化推动估值重定价",
            "风险偏好上行带动产业链龙头扩散",
        ],
        evidence=[
            EventEvidence(
                quote_id=f"q-{event_id}",
                source_url=f"https://example.com/{event_id}",
                title=headline,
                published_at=now,
                excerpt=summary,
            )
        ],
        related_event_ids=None,
        data_origin=data_origin,
    )


def _make_quote(asset_id: str, price: float, change_pct: float) -> QuoteSnapshot:
    now = datetime(2026, 2, 22, 10, 0, tzinfo=timezone.utc)
    return QuoteSnapshot(
        asset_id=asset_id,
        price=price,
        change=price * change_pct / 100.0,
        change_pct=change_pct,
        currency="USD",
        as_of=now,
        source="yahoo",
        is_fallback=False,
    )


@contextmanager
def _prepare_app(monkeypatch, events: list[Event], quotes: dict[str, QuoteSnapshot]):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("ENABLE_LIVE_SOURCES", "false")

    import app.api as api_module
    import app.services.ingestion as ingestion_module

    async def _fake_refresh(store, config) -> None:
        store.replace_events(events)
        store.replace_quotes(quotes)
        ingestion_module.sync_unlisted_from_events(events)

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)

    with TestClient(create_app()) as client:
        yield client


def test_correlation_matrix_supports_three_presets(monkeypatch) -> None:
    events = [
        _make_event(
            event_id="evt-nvda",
            headline="NVDA rallies as AI demand accelerates",
            summary="AI capex outlook remains strong.",
            tickers=["NVDA"],
            instruments=["NASDAQ"],
            markets=["US"],
            impact=86,
            confidence=0.91,
        )
    ]
    quotes = {
        "DXY": _make_quote("DXY", 104.3, 0.5),
        "US10Y": _make_quote("US10Y", 4.18, -1.2),
        "XAUUSD": _make_quote("XAUUSD", 2361.0, 0.9),
        "NASDAQ": _make_quote("NASDAQ", 18230.0, 1.1),
        "0700.HK": _make_quote("0700.HK", 332.1, 1.6),
        "NVDA": _make_quote("NVDA", 855.0, 2.4),
        "AMD": _make_quote("AMD", 180.5, 1.9),
        "AVGO": _make_quote("AVGO", 1254.0, 1.5),
        "MSFT": _make_quote("MSFT", 412.8, 0.8),
        "GOOGL": _make_quote("GOOGL", 172.0, 0.7),
    }

    with _prepare_app(monkeypatch, events, quotes) as client:
        for preset in ("A", "B", "C"):
            resp = client.get("/correlation/matrix", params={"preset": preset, "window": 30})
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["preset"] == preset
            assert payload["window_days"] == 30
            assert len(payload["assets"]) >= 5
            assert len(payload["matrix"]) == len(payload["assets"])
            assert len(payload["matrix"][0]) == len(payload["assets"])


def test_correlation_matrix_us02y_has_fallback_note(monkeypatch) -> None:
    events = []
    quotes = {
        "DXY": _make_quote("DXY", 104.3, 0.5),
        "US10Y": _make_quote("US10Y", 4.18, -1.2),
        "XAUUSD": _make_quote("XAUUSD", 2361.0, 0.9),
        "NASDAQ": _make_quote("NASDAQ", 18230.0, 1.1),
        "0700.HK": _make_quote("0700.HK", 332.1, 1.6),
    }
    with _prepare_app(monkeypatch, events, quotes) as client:
        resp = client.get("/correlation/matrix", params={"preset": "A", "window": 7})
        assert resp.status_code == 200
        payload = resp.json()
        assert "US02Y" in payload["assets"]
        assert "US02Y" in payload["fallback_assets"]
        assert "US02Y" in (payload.get("note") or "")


def test_tech_heatmap_returns_ranked_items(monkeypatch) -> None:
    events = [
        _make_event(
            event_id="evt-nvda",
            headline="NVDA rallies as AI demand accelerates",
            summary="AI capex outlook remains strong.",
            tickers=["NVDA"],
            instruments=["NASDAQ"],
            markets=["US"],
            impact=86,
            confidence=0.91,
        ),
        _make_event(
            event_id="evt-0700",
            headline="0700.HK cloud growth surprises to upside",
            summary="Tencent cloud momentum improves.",
            tickers=["0700.HK"],
            instruments=[],
            markets=["HK"],
            impact=78,
            confidence=0.82,
        ),
        _make_event(
            event_id="evt-minimax",
            headline="MiniMax launches new multi-modal release",
            summary="MiniMax model improves agent reliability.",
            tickers=[],
            instruments=[],
            markets=["US"],
            impact=74,
            confidence=0.76,
            data_origin="seed",
        ),
    ]
    quotes = {
        "NVDA": _make_quote("NVDA", 855.0, 2.4),
        "0700.HK": _make_quote("0700.HK", 332.1, 1.6),
    }
    with _prepare_app(monkeypatch, events, quotes) as client:
        resp = client.get("/tech/heatmap", params={"limit": 10})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["items"]
        scores = [item["heat_score"] for item in payload["items"]]
        assert scores == sorted(scores, reverse=True)
        top_assets = {item["asset_id"] for item in payload["items"][:5]}
        assert "NVDA" in top_assets


def test_causal_analyze_returns_structured_nodes(monkeypatch) -> None:
    events = [
        _make_event(
            event_id="evt-nvda-live",
            headline="NVDA rallies as AI demand accelerates",
            summary="AI capex outlook remains strong.",
            tickers=["NVDA"],
            instruments=["NASDAQ"],
            markets=["US"],
            impact=86,
            confidence=0.91,
            data_origin="live",
        ),
        _make_event(
            event_id="evt-amd-seed",
            headline="AMD follows NVDA momentum in AI servers",
            summary="AI server demand broadens beyond single vendor.",
            tickers=["AMD"],
            instruments=["NASDAQ"],
            markets=["US"],
            impact=73,
            confidence=0.78,
            data_origin="seed",
        ),
    ]
    quotes = {}
    with _prepare_app(monkeypatch, events, quotes) as client:
        resp = client.post(
            "/correlation/analyze",
            json={"query": "NVDA", "max_depth": 4},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["event_id"] == "evt-nvda-live"
        assert payload["source_type"] == "mixed"
        assert len(payload["nodes"]) >= 3
        assert payload["nodes"][0]["label"] == "起点事件"
