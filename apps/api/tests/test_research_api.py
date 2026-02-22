from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import (
    EarningsCard,
    Event,
    EventEvidence,
    Market,
    Metric,
    ResearchAnalysisBlock,
    Sector,
    QuoteSnapshot,
)
from app.sources.earnings import EarningsSnapshot


def _make_event(*, event_id: str, ticker: str, headline: str) -> Event:
    now = datetime(2026, 2, 22, 9, 0, tzinfo=timezone.utc)
    markets: list[Market] = ["US"]
    sectors: list[Sector] = ["Tech"]
    return Event(
        event_id=event_id,
        event_time=now,
        ingest_time=now,
        source_type="news",
        publisher="Test Publisher",
        headline=headline,
        summary="summary",
        event_type="risk",
        markets=markets,
        tickers=[ticker],
        instruments=[],
        sectors=sectors,
        numbers=[],
        stance="neutral",
        impact=70,
        confidence=0.8,
        impact_chain=[],
        evidence=[
            EventEvidence(
                quote_id=f"q-{event_id}",
                source_url=f"https://example.com/{event_id}",
                title=headline,
                published_at=now,
                excerpt="excerpt",
            )
        ],
        related_event_ids=None,
    )


def _make_snapshot(ticker: str) -> EarningsSnapshot:
    now = datetime(2026, 2, 22, 9, 0, tzinfo=timezone.utc)
    return EarningsSnapshot(
        ticker=ticker,
        quote=QuoteSnapshot(
            asset_id=ticker,
            price=188.2,
            change=0.9,
            change_pct=0.5,
            currency="USD",
            as_of=now,
            source="yahoo",
            is_fallback=False,
        ),
        earnings_card=EarningsCard(
            headline=f"{ticker} 财报快照",
            eps=Metric(value=2.2, yoy=0.12),
            revenue=Metric(value=33.4, yoy=0.08),
            guidance="Guidance stable",
            sentiment="Constructive",
        ),
        source_url=f"https://finance.yahoo.com/quote/{ticker}",
        updated_at=now,
        is_live=True,
    )


@contextmanager
def _prepare_app(monkeypatch, events: list[Event]):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("ENABLE_LIVE_SOURCES", "false")

    import app.api as api_module

    async def _fake_refresh(store, config) -> None:
        store.replace_events(events)

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)

    with TestClient(create_app()) as client:
        yield client, api_module


def test_research_company_live_path(monkeypatch) -> None:
    events = [_make_event(event_id="evt-live", ticker="AAPL", headline="AAPL demand remains resilient")]

    with _prepare_app(monkeypatch, events) as (client, api_module):
        async def _fake_fetch(config, ticker):
            return _make_snapshot(ticker)

        def _fake_analyze(**kwargs):
            return ResearchAnalysisBlock(
                answer="结构化分析结论",
                model="qwen3-max",
                is_fallback=False,
                sources=[events[0].evidence[0]],
            )

        monkeypatch.setattr(api_module, "fetch_earnings_snapshot", _fake_fetch)
        monkeypatch.setattr(api_module, "analyze_research_company", _fake_analyze)

        resp = client.get("/research/company/AAPL")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ticker"] == "AAPL"
        assert payload["company_type"] == "listed"
        assert payload["source_type"] == "live"
        assert payload["quote"]["asset_id"] == "AAPL"
        assert payload["analysis"]["is_fallback"] is False


def test_research_company_analysis_fallback(monkeypatch) -> None:
    events = [_make_event(event_id="evt-fallback", ticker="AAPL", headline="AAPL margin pressure persists")]

    with _prepare_app(monkeypatch, events) as (client, api_module):
        async def _fake_fetch(config, ticker):
            return _make_snapshot(ticker)

        def _fake_analyze(**kwargs):
            return ResearchAnalysisBlock(
                answer="规则降级摘要",
                model="rule-based",
                is_fallback=True,
                sources=[events[0].evidence[0]],
            )

        monkeypatch.setattr(api_module, "fetch_earnings_snapshot", _fake_fetch)
        monkeypatch.setattr(api_module, "analyze_research_company", _fake_analyze)

        resp = client.get("/research/company/AAPL")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["company_type"] == "listed"
        assert payload["source_type"] == "fallback"
        assert payload["analysis"]["is_fallback"] is True
        assert "降级" in (payload.get("note") or "")


def test_research_company_unlisted_placeholder(monkeypatch) -> None:
    with _prepare_app(monkeypatch, []) as (client, api_module):
        async def _fake_fetch(config, ticker):
            return None

        def _fake_analyze(**kwargs):
            return ResearchAnalysisBlock(
                answer="暂无有效研究数据",
                model="rule-based",
                is_fallback=True,
                sources=[],
            )

        monkeypatch.setattr(api_module, "fetch_earnings_snapshot", _fake_fetch)
        monkeypatch.setattr(api_module, "analyze_research_company", _fake_analyze)

        resp = client.get("/research/company/MINIMAX")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["company_type"] == "unlisted"
        assert payload["source_type"] == "fallback"
        assert payload["quote"] is None
        assert payload["earnings_card"] is None
        assert "未识别" in (payload.get("note") or "")


def test_research_company_schema_regression(monkeypatch) -> None:
    events = [_make_event(event_id="evt-schema", ticker="AAPL", headline="AAPL launches new product")]

    with _prepare_app(monkeypatch, events) as (client, api_module):
        async def _fake_fetch(config, ticker):
            return _make_snapshot(ticker)

        def _fake_analyze(**kwargs):
            return ResearchAnalysisBlock(
                answer="结构化分析结论",
                model="qwen3-max",
                is_fallback=False,
                sources=[events[0].evidence[0]],
            )

        monkeypatch.setattr(api_module, "fetch_earnings_snapshot", _fake_fetch)
        monkeypatch.setattr(api_module, "analyze_research_company", _fake_analyze)

        payload = client.get("/research/company/AAPL").json()
        assert {
            "ticker",
            "company_type",
            "source_type",
            "updated_at",
            "quote",
            "earnings_card",
            "news",
            "analysis",
            "note",
        }.issubset(payload.keys())
        assert "reports" not in payload
        assert "fact_check" not in payload
