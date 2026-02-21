from __future__ import annotations

import builtins
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.config import AppConfig
from app.models import Event, EventEvidence
from app.services.ingestion import write_vectors
from app.services.pg_vector_store import PgVectorStore
from app.services.vector_store import RetrievedEvidence, create_vector_store


def _make_event(event_id: str) -> Event:
    now = datetime(2026, 2, 21, 9, 0, tzinfo=timezone.utc)
    return Event(
        event_id=event_id,
        event_time=now,
        ingest_time=now,
        source_type="news",
        publisher="Test Publisher",
        headline=f"Headline {event_id}",
        summary="Summary",
        event_type="risk",
        markets=["US"],
        tickers=["AAPL"],
        instruments=[],
        sectors=["Tech"],
        numbers=[],
        stance="neutral",
        impact=55,
        confidence=0.6,
        impact_chain=[],
        evidence=[
            EventEvidence(
                quote_id=f"q-{event_id}",
                source_url="https://example.com",
                title=f"Evidence {event_id}",
                published_at=now,
                excerpt="Excerpt",
            )
        ],
        related_event_ids=None,
    )


class _RecorderStore:
    def __init__(self) -> None:
        self.calls = 0

    def is_ready(self) -> bool:
        return True

    def upsert_events(self, events: list[Event]) -> int:
        self.calls += 1
        return len(events)

    def query(self, query_text: str, *, top_k: int) -> list[RetrievedEvidence]:
        return []


def test_config_falls_back_to_pgvector_dsn(monkeypatch) -> None:
    monkeypatch.delenv("PG_DSN", raising=False)
    monkeypatch.setenv("PGVECTOR_DSN", "postgresql://example/legacy")

    config = AppConfig.from_env()

    assert config.pg_dsn == "postgresql://example/legacy"
    assert config.pgvector_dsn == "postgresql://example/legacy"


def test_enable_pgvector_selects_default_backend(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_PGVECTOR", "true")
    monkeypatch.delenv("VECTOR_BACKEND", raising=False)

    config = AppConfig.from_env()

    assert config.enable_pgvector is True
    assert config.vector_backend == "pgvector"


def test_vector_backend_overrides_enable_pgvector(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_PGVECTOR", "true")
    monkeypatch.setenv("VECTOR_BACKEND", "simple")

    config = AppConfig.from_env()

    assert config.vector_backend == "simple"


def test_create_vector_store_uses_pgvector_class(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "true")
    monkeypatch.setenv("VECTOR_BACKEND", "pgvector")
    monkeypatch.setenv("PG_DSN", "postgresql://example/runtime")

    config = AppConfig.from_env()

    import app.services.pg_vector_store as pg_module

    class _DummyPgStore:
        def __init__(self, cfg: AppConfig) -> None:
            self.config = cfg

        def is_ready(self) -> bool:
            return True

        def upsert_events(self, events: list[Event]) -> int:
            return len(events)

        def query(self, query_text: str, *, top_k: int) -> list[RetrievedEvidence]:
            return []

    monkeypatch.setattr(pg_module, "PgVectorStore", _DummyPgStore)

    store = create_vector_store(config)

    assert isinstance(store, _DummyPgStore)
    assert store.config is config


def test_pg_vector_store_requires_dsn() -> None:
    base = AppConfig.from_env()
    config = replace(
        base,
        enable_vector_store=True,
        vector_backend="pgvector",
        pg_dsn="",
        pgvector_dsn="",
    )

    with pytest.raises(RuntimeError, match="PG_DSN/PGVECTOR_DSN"):
        PgVectorStore(config)


def test_pg_vector_store_requires_psycopg(monkeypatch) -> None:
    base = AppConfig.from_env()
    config = replace(
        base,
        enable_vector_store=True,
        vector_backend="pgvector",
        pg_dsn="postgresql://example/runtime",
        pgvector_dsn="postgresql://example/runtime",
    )

    original_import = builtins.__import__

    def _import_hook(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "psycopg":
            raise ImportError("missing psycopg")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import_hook)

    with pytest.raises(RuntimeError, match="psycopg is required for pgvector backend"):
        PgVectorStore(config)


def test_write_vectors_routes_simple_backend() -> None:
    config = replace(AppConfig.from_env(), vector_backend="simple")
    events = [_make_event("evt-simple")]
    store = _RecorderStore()

    inserted = write_vectors(events, config, store)

    assert inserted == 1
    assert store.calls == 1


def test_write_vectors_routes_pgvector_backend(monkeypatch) -> None:
    config = replace(AppConfig.from_env(), vector_backend="pgvector")
    events = [_make_event("evt-pg")]

    import app.services.pg_vector_store as pg_module

    class _DummyPgStore(_RecorderStore):
        pass

    monkeypatch.setattr(pg_module, "PgVectorStore", _DummyPgStore)
    store = _DummyPgStore()

    inserted = write_vectors(events, config, store)

    assert inserted == 1
    assert store.calls == 1
