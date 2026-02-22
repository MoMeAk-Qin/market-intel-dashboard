from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.config import AppConfig
from app.models import AnalysisRequest, EarningsCard, Metric, ResearchNewsItem
import app.services.analysis as analysis_module


class _FakeCompletions:
    def __init__(self, answer: str, counter: dict[str, int]) -> None:
        self._answer = answer
        self._counter = counter

    def create(self, **kwargs):
        self._counter["calls"] += 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._answer))],
            usage=SimpleNamespace(prompt_tokens=12, completion_tokens=34, total_tokens=46),
        )


class _FakeChat:
    def __init__(self, answer: str, counter: dict[str, int]) -> None:
        self.completions = _FakeCompletions(answer, counter)


class _FakeOpenAI:
    def __init__(self, answer: str, counter: dict[str, int]) -> None:
        self.chat = _FakeChat(answer, counter)


def _build_config(monkeypatch, *, ttl_seconds: int = 3600) -> AppConfig:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("ANALYSIS_CACHE_TTL_SECONDS", str(ttl_seconds))
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    return AppConfig.from_env()


def test_analysis_preserves_valid_structured_answer(monkeypatch) -> None:
    analysis_module._ANALYSIS_CACHE.clear()
    config = _build_config(monkeypatch)
    counter = {"calls": 0}
    expected = "\n".join(
        [
            "【结论】",
            "结论内容 [1]",
            "【影响】",
            "影响内容 [1]",
            "【风险】",
            "风险内容 [1]",
            "【关注点】",
            "关注点内容 [1]",
        ]
    )
    monkeypatch.setattr(
        analysis_module,
        "OpenAI",
        lambda api_key, base_url: _FakeOpenAI(expected, counter),
    )

    response = analysis_module.analyze_financial_sources(
        AnalysisRequest(question="测试问题", sources=["https://example.com/a"]),
        config,
        vector_store=None,
    )
    assert response.answer == expected
    assert counter["calls"] == 1


def test_analysis_fallback_when_template_invalid(monkeypatch) -> None:
    analysis_module._ANALYSIS_CACHE.clear()
    config = _build_config(monkeypatch)
    counter = {"calls": 0}
    monkeypatch.setattr(
        analysis_module,
        "OpenAI",
        lambda api_key, base_url: _FakeOpenAI("这是一段非结构化回答", counter),
    )

    response = analysis_module.analyze_financial_sources(
        AnalysisRequest(question="美元走势如何", sources=["https://example.com/a"]),
        config,
        vector_store=None,
    )
    assert "【结论】" in response.answer
    assert "【影响】" in response.answer
    assert "【风险】" in response.answer
    assert "【关注点】" in response.answer
    assert "[1]" in response.answer


def test_analysis_cache_reuse(monkeypatch) -> None:
    analysis_module._ANALYSIS_CACHE.clear()
    config = _build_config(monkeypatch, ttl_seconds=600)
    counter = {"calls": 0}
    monkeypatch.setattr(
        analysis_module,
        "OpenAI",
        lambda api_key, base_url: _FakeOpenAI(
            "\n".join(
                [
                    "【结论】",
                    "结论内容 [1]",
                    "【影响】",
                    "影响内容 [1]",
                    "【风险】",
                    "风险内容 [1]",
                    "【关注点】",
                    "关注点内容 [1]",
                ]
            ),
            counter,
        ),
    )
    payload = AnalysisRequest(question="测试缓存", sources=["https://example.com/a"], use_retrieval=False)
    response_first = analysis_module.analyze_financial_sources(payload, config, vector_store=None)
    response_second = analysis_module.analyze_financial_sources(payload, config, vector_store=None)

    assert response_first.answer == response_second.answer
    assert counter["calls"] == 1


def test_research_analysis_fallback_without_dashscope_key(monkeypatch) -> None:
    analysis_module._ANALYSIS_CACHE.clear()
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    config = AppConfig.from_env()

    news = [
        ResearchNewsItem(
            event_id="evt-1",
            headline="AAPL demand remains resilient",
            summary="Channel checks show stable momentum.",
            publisher="Test Publisher",
            event_time=datetime(2026, 2, 22, 9, 0, tzinfo=timezone.utc),
            event_type="risk",
            impact=66,
            confidence=0.72,
            source_type="news",
            source_url="https://example.com/news/1",
            quote_id="q-evt-1",
        )
    ]

    response = analysis_module.analyze_research_company(
        ticker="AAPL",
        news=news,
        earnings_card=None,
        config=config,
        vector_store=None,
    )
    assert response.is_fallback is True
    assert response.model == "rule-based"
    assert response.sources[0].source_url == "https://example.com/news/1"


def test_research_analysis_uses_llm_response_and_source_fallback(monkeypatch) -> None:
    analysis_module._ANALYSIS_CACHE.clear()
    config = _build_config(monkeypatch)

    news = [
        ResearchNewsItem(
            event_id="evt-2",
            headline="AAPL margin trend stabilizes",
            summary="Cost discipline remains intact.",
            publisher="Test Publisher",
            event_time=datetime(2026, 2, 22, 10, 0, tzinfo=timezone.utc),
            event_type="risk",
            impact=62,
            confidence=0.71,
            source_type="news",
            source_url="https://example.com/news/2",
            quote_id="q-evt-2",
        )
    ]

    def _fake_analyze(payload, cfg, vector_store=None, model_name=None):
        return analysis_module.AnalysisResponse(
            answer="【结论】测试[1]\n【影响】测试[1]\n【风险】测试[1]\n【关注点】测试[1]",
            model=model_name or "qwen3-max",
            usage=None,
            sources=[],
        )

    monkeypatch.setattr(analysis_module, "analyze_financial_sources", _fake_analyze)

    response = analysis_module.analyze_research_company(
        ticker="AAPL",
        news=news,
        earnings_card=EarningsCard(
            headline="AAPL 财报快照",
            eps=Metric(value=2.3, yoy=0.1),
            revenue=Metric(value=34.1, yoy=0.06),
            guidance="Guidance stable",
            sentiment="Constructive",
        ),
        config=config,
        vector_store=None,
    )
    assert response.is_fallback is False
    assert response.model == "qwen3-max"
    assert response.sources[0].quote_id == "q-evt-2"
