from __future__ import annotations

from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.api import create_app
from app.models import Event


@contextmanager
def _prepare_app(monkeypatch, events: list[Event]):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

    import app.api as api_module

    async def _fake_refresh(store, config) -> None:
        store.replace_events(events)

    monkeypatch.setattr(api_module, "refresh_store", _fake_refresh)
    with TestClient(create_app()) as client:
        yield client


def test_asset_chart_invalid_range(monkeypatch) -> None:
    with _prepare_app(monkeypatch, []) as client:
        resp = client.get("/assets/AAPL/chart", params={"range": "2W"})
        assert resp.status_code == 400
        payload = resp.json()
        assert payload["detail"] == "Invalid range: 2W. Use one of: 1D, 1W, 1M, 1Y."


def test_asset_events_invalid_range(monkeypatch) -> None:
    with _prepare_app(monkeypatch, []) as client:
        resp = client.get("/assets/AAPL/events", params={"range": "2W"})
        assert resp.status_code == 400
        payload = resp.json()
        assert payload["detail"] == "Invalid range: 2W. Use one of: 1D, 1W, 1M, 1Y."
