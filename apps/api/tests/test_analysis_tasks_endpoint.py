from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import time

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import AnalysisResponse, RefreshReport


@contextmanager
def _prepare_app(monkeypatch):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("TIMEZONE", "Asia/Hong_Kong")

    import app.api as api_module

    async def _fake_refresh(store, config) -> RefreshReport:
        store.replace_events([])
        now = datetime.now(timezone.utc)
        return RefreshReport(
            started_at=now,
            finished_at=now,
            duration_ms=1,
            total_events=0,
            live_events=0,
            seed_events=0,
            source_errors=[],
        )

    def _fake_analyze(payload, config, vector_store=None) -> AnalysisResponse:
        time.sleep(0.02)
        return AnalysisResponse(
            answer=f"task:{payload.question}",
            model="qwen3-max",
            usage=None,
            sources=[],
        )

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)
    monkeypatch.setattr(api_module, "analyze_financial_sources", _fake_analyze)
    with TestClient(create_app()) as client:
        yield client


def test_analysis_task_endpoints(monkeypatch) -> None:
    with _prepare_app(monkeypatch) as client:
        create_resp = client.post("/analysis/tasks", json={"question": "AAPL outlook"})
        assert create_resp.status_code == 200
        created = create_resp.json()
        task_id = created["task_id"]

        duplicate_resp = client.post("/analysis/tasks", json={"question": "AAPL outlook"})
        assert duplicate_resp.status_code == 200
        assert duplicate_resp.json()["task_id"] == task_id

        completed = None
        for _ in range(40):
            detail_resp = client.get(f"/analysis/tasks/{task_id}")
            assert detail_resp.status_code == 200
            detail_payload = detail_resp.json()
            if detail_payload["status"] == "completed":
                completed = detail_payload
                break
            time.sleep(0.03)

        assert completed is not None
        assert completed["result"]["answer"] == "task:AAPL outlook"

        list_resp = client.get("/analysis/tasks", params={"limit": 5})
        assert list_resp.status_code == 200
        listing = list_resp.json()
        assert listing["total"] >= 1
        assert any(item["task_id"] == task_id for item in listing["items"])
