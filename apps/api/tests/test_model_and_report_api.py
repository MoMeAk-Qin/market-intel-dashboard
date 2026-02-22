from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import AnalysisResponse, Event, EventEvidence, Market, Sector


def _make_event(*, event_id: str, headline: str) -> Event:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    markets: list[Market] = ["US"]
    sectors: list[Sector] = ["Tech"]
    return Event(
        event_id=event_id,
        event_time=now,
        ingest_time=now,
        source_type="news",
        publisher="Test Wire",
        headline=headline,
        summary="summary",
        event_type="risk",
        markets=markets,
        tickers=["NVDA"],
        instruments=["NASDAQ"],
        sectors=sectors,
        numbers=[],
        stance="neutral",
        impact=82,
        confidence=0.88,
        impact_chain=["impact chain"],
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
        data_origin="live",
    )


@contextmanager
def _prepare_app(monkeypatch, *, dashscope_key: str):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("ENABLE_LIVE_SOURCES", "false")
    monkeypatch.setenv("ANALYSIS_MODELS", "qwen3-max,qwen-plus")
    monkeypatch.setenv("DEFAULT_ANALYSIS_MODEL", "qwen3-max")
    monkeypatch.setenv("DASHSCOPE_API_KEY", dashscope_key)

    import app.api as api_module
    import app.services.ingestion as ingestion_module

    events = [_make_event(event_id="evt-1", headline="NVDA demand remains strong")]

    async def _fake_refresh(store, config) -> None:
        store.replace_events(events)
        ingestion_module.sync_unlisted_from_events(events)

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)
    with TestClient(create_app()) as client:
        yield client, api_module


def test_models_list_and_switch(monkeypatch) -> None:
    with _prepare_app(monkeypatch, dashscope_key="") as (client, _):
        listed = client.get("/models")
        assert listed.status_code == 200
        payload = listed.json()
        assert payload["active_model"] == "qwen3-max"
        assert payload["default_model"] == "qwen3-max"
        assert payload["available_models"] == ["qwen3-max", "qwen-plus"]

        switched = client.post("/models/select", json={"model": "qwen-plus"})
        assert switched.status_code == 200
        switched_payload = switched.json()
        assert switched_payload["active_model"] == "qwen-plus"

        invalid = client.post("/models/select", json={"model": "gpt-4.1"})
        assert invalid.status_code == 400


def test_reports_generate_and_latest(monkeypatch) -> None:
    with _prepare_app(monkeypatch, dashscope_key="") as (client, _):
        generated = client.post("/reports/generate?force=true")
        assert generated.status_code == 200
        payload = generated.json()
        assert payload["status"] == "completed"
        assert payload["source_type"] == "fallback"
        assert payload["model"] == "rule-based"
        assert payload["summary"]

        latest = client.get("/reports/latest")
        assert latest.status_code == 200
        latest_payload = latest.json()
        assert latest_payload["report_id"] == payload["report_id"]


def test_analysis_uses_active_model(monkeypatch) -> None:
    with _prepare_app(monkeypatch, dashscope_key="test-key") as (client, api_module):
        def _fake_analyze(payload, config, vector_store=None, model_name=None):
            return AnalysisResponse(
                answer="ok",
                model=model_name or "unknown",
                usage=None,
                sources=[],
            )

        monkeypatch.setattr(api_module, "analyze_financial_sources", _fake_analyze)

        switched = client.post("/models/select", json={"model": "qwen-plus"})
        assert switched.status_code == 200

        analysis_resp = client.post("/analysis", json={"question": "test model route"})
        assert analysis_resp.status_code == 200
        analysis_payload = analysis_resp.json()
        assert analysis_payload["model"] == "qwen-plus"
