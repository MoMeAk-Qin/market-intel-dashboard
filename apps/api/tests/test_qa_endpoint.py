from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import AnalysisResponse, Event, EventEvidence


def _make_event(
    *,
    event_id: str,
    headline: str,
    summary: str,
    markets: list[str],
    tickers: list[str],
) -> Event:
    now = datetime(2026, 2, 9, 9, 0, tzinfo=timezone.utc)
    return Event(
        event_id=event_id,
        event_time=now,
        ingest_time=now,
        source_type="news",
        publisher="Test Publisher",
        headline=headline,
        summary=summary,
        event_type="risk",
        markets=markets,
        tickers=tickers,
        instruments=[],
        sectors=["Tech"],
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


@contextmanager
def _prepare_app(monkeypatch, events: list[Event], *, dashscope_key: str):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("DASHSCOPE_API_KEY", dashscope_key)
    monkeypatch.setenv("TIMEZONE", "Asia/Hong_Kong")

    import app.api as api_module

    async def _fake_refresh(store, config) -> None:
        store.replace_events(events)

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)
    with TestClient(create_app()) as client:
        yield client


def test_qa_uses_analysis_chain(monkeypatch) -> None:
    events = [
        _make_event(
            event_id="evt-aapl",
            headline="AAPL reports resilient demand",
            summary="Earnings quality improves with services mix.",
            markets=["US"],
            tickers=["AAPL"],
        )
    ]

    with _prepare_app(monkeypatch, events, dashscope_key="test-key") as client:
        import app.api as api_module

        def _fake_analyze(payload, config, vector_store=None) -> AnalysisResponse:
            return AnalysisResponse(
                answer="分析主路径命中",
                model="qwen3-max",
                usage=None,
                sources=[events[0].evidence[0]],
            )

        monkeypatch.setattr(api_module, "analyze_financial_sources", _fake_analyze)
        resp = client.post("/qa", json={"question": "AAPL latest earnings?"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["answer"] == "分析主路径命中"
        assert payload["evidence"][0]["quote_id"] == "q-evt-aapl"


def test_qa_fallback_without_dashscope_key(monkeypatch) -> None:
    events = [
        _make_event(
            event_id="evt-gold",
            headline="Gold rises as real yields retreat",
            summary="Safe-haven demand supports metals pricing.",
            markets=["METALS"],
            tickers=["XAUUSD"],
        )
    ]
    with _prepare_app(monkeypatch, events, dashscope_key="") as client:
        resp = client.post("/qa", json={"question": "gold outlook"})
        assert resp.status_code == 200
        payload = resp.json()
        assert "基于事件检索的摘要" in payload["answer"]
        assert payload["evidence"][0]["quote_id"] == "q-evt-gold"


def test_qa_requires_question(monkeypatch) -> None:
    with _prepare_app(monkeypatch, [], dashscope_key="") as client:
        resp = client.post("/qa", json={"question": "   "})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "question is required"


def test_qa_empty_events_returns_empty_message(monkeypatch) -> None:
    with _prepare_app(monkeypatch, [], dashscope_key="") as client:
        resp = client.post("/qa", json={"question": "anything"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["answer"] == "当前暂无可用于回答的问题事件数据。"
        assert payload["evidence"] == []

