from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import AnalysisResponse, Event, EventEvidence


def _fixed_now(tz: ZoneInfo) -> datetime:
    return datetime.now(tz).replace(hour=12, minute=0, second=0, microsecond=0)


def _make_event(
    *,
    headline: str,
    published_at: datetime,
    markets: list[str],
    tickers: list[str],
) -> Event:
    return Event(
        event_id=f"evt-{headline}",
        event_time=published_at,
        ingest_time=published_at,
        source_type="news",
        publisher="Test Publisher",
        headline=headline,
        summary="summary",
        event_type="risk",
        markets=markets,
        tickers=tickers,
        instruments=[],
        sectors=["Tech"],
        numbers=[],
        stance="neutral",
        impact=55,
        confidence=0.6,
        impact_chain=[],
        evidence=[
            EventEvidence(
                quote_id=f"q-{headline}",
                source_url="https://example.com",
                title=headline,
                published_at=published_at,
                excerpt="excerpt",
            )
        ],
        related_event_ids=None,
    )


@contextmanager
def _prepare_app(
    monkeypatch,
    events: list[Event],
    *,
    watchlist_markets: str = "",
    watchlist_tickers: str = "",
    watchlist_keywords: str = "",
):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("WATCHLIST_MARKETS", watchlist_markets)
    monkeypatch.setenv("WATCHLIST_TICKERS", watchlist_tickers)
    monkeypatch.setenv("WATCHLIST_KEYWORDS", watchlist_keywords)

    import app.api as api_module

    async def _fake_refresh(store, config) -> None:
        store.replace_events(events)

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)
    with TestClient(create_app()) as client:
        yield client


def test_news_today_filters(monkeypatch) -> None:
    tz = ZoneInfo("Asia/Hong_Kong")
    now = _fixed_now(tz)
    today_event = _make_event(
        headline="US AAPL headline",
        published_at=now - timedelta(hours=2),
        markets=["US"],
        tickers=["AAPL"],
    )
    today_other = _make_event(
        headline="HK headline",
        published_at=now - timedelta(hours=1),
        markets=["HK"],
        tickers=["0700.HK"],
    )
    yesterday_event = _make_event(
        headline="Old US AAPL",
        published_at=now - timedelta(days=1, hours=1),
        markets=["US"],
        tickers=["AAPL"],
    )

    with _prepare_app(monkeypatch, [today_event, today_other, yesterday_event]) as client:
        resp = client.get("/news/today", params={"market": "US", "tickers": "AAPL"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total"] == 1
        assert payload["items"][0]["headline"] == "US AAPL headline"


def test_daily_summary_empty(monkeypatch) -> None:
    tz = ZoneInfo("Asia/Hong_Kong")
    now = _fixed_now(tz)
    yesterday_event = _make_event(
        headline="Old US AAPL",
        published_at=now - timedelta(days=1, hours=1),
        markets=["US"],
        tickers=["AAPL"],
    )
    with _prepare_app(monkeypatch, [yesterday_event]) as client:
        resp = client.post("/daily/summary", json={})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total_news"] == 0
        assert payload["answer"] == "今日暂无符合条件的新闻。"


def test_daily_summary_calls_analysis(monkeypatch) -> None:
    tz = ZoneInfo("Asia/Hong_Kong")
    now = _fixed_now(tz)
    today_event = _make_event(
        headline="US AAPL headline",
        published_at=now - timedelta(hours=1),
        markets=["US"],
        tickers=["AAPL"],
    )

    with _prepare_app(monkeypatch, [today_event]) as client:
        import app.api as api_module

        def _fake_analyze(payload, config, vector_store=None) -> AnalysisResponse:
            return AnalysisResponse(
                answer="OK",
                model="qwen3-max",
                usage=None,
                sources=[],
            )

        monkeypatch.setattr(api_module, "analyze_financial_sources", _fake_analyze)

        resp = client.post("/daily/summary", json={"focus": "给出重点"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["answer"] == "OK"
        assert payload["total_news"] == 1


def test_news_today_applies_watchlist_defaults(monkeypatch) -> None:
    tz = ZoneInfo("Asia/Hong_Kong")
    now = _fixed_now(tz)
    us_event = _make_event(
        headline="US AAPL headline",
        published_at=now - timedelta(hours=2),
        markets=["US"],
        tickers=["AAPL"],
    )
    hk_event = _make_event(
        headline="HK Tencent headline",
        published_at=now - timedelta(hours=1),
        markets=["HK"],
        tickers=["0700.HK"],
    )
    with _prepare_app(
        monkeypatch,
        [us_event, hk_event],
        watchlist_markets="US",
        watchlist_tickers="AAPL",
    ) as client:
        resp = client.get("/news/today")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total"] == 1
        assert payload["items"][0]["headline"] == "US AAPL headline"


def test_daily_summary_applies_watchlist_keywords(monkeypatch) -> None:
    tz = ZoneInfo("Asia/Hong_Kong")
    now = _fixed_now(tz)
    apple_event = _make_event(
        headline="Apple demand improves",
        published_at=now - timedelta(hours=2),
        markets=["US"],
        tickers=["AAPL"],
    )
    bank_event = _make_event(
        headline="Bank funding update",
        published_at=now - timedelta(hours=1),
        markets=["US"],
        tickers=["JPM"],
    )
    with _prepare_app(
        monkeypatch,
        [apple_event, bank_event],
        watchlist_keywords="apple",
    ) as client:
        import app.api as api_module

        def _fake_analyze(payload, config, vector_store=None) -> AnalysisResponse:
            return AnalysisResponse(
                answer="OK",
                model="qwen3-max",
                usage=None,
                sources=[],
            )

        monkeypatch.setattr(api_module, "analyze_financial_sources", _fake_analyze)
        resp = client.post("/daily/summary", json={})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total_news"] == 1
        assert payload["sources"][0]["title"] == "Apple demand improves"


def test_admin_refresh(monkeypatch) -> None:
    tz = ZoneInfo("Asia/Hong_Kong")
    now = _fixed_now(tz)
    event_a = _make_event(
        headline="A",
        published_at=now,
        markets=["US"],
        tickers=[],
    )
    event_b = _make_event(
        headline="B",
        published_at=now - timedelta(minutes=5),
        markets=["US"],
        tickers=[],
    )

    with _prepare_app(monkeypatch, [event_a, event_b]) as client:
        resp = client.post("/admin/refresh")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ok"] is True
        assert payload["total_events"] == 2
