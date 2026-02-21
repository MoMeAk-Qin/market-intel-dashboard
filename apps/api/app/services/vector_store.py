from __future__ import annotations

from collections.abc import Sequence
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
import json
import re
from typing import TYPE_CHECKING, Protocol

from ..config import AppConfig
from ..models import Event, EventEvidence

if TYPE_CHECKING:
    from chromadb.api.types import Metadata as ChromaMetadata, PyEmbedding
else:
    type ChromaMetadata = dict[str, str | int | float | bool | None]
    type PyEmbedding = list[float]

logger = logging.getLogger("vector_store")
_SQL_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class VectorStoreDisabled(RuntimeError):
    pass


class EmbeddingsUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class RetrievedEvidence:
    evidence: EventEvidence
    score: float


class BaseVectorStore(Protocol):
    def is_ready(self) -> bool: ...

    def upsert_events(self, events: list[Event]) -> int: ...

    def query(self, query_text: str, *, top_k: int) -> list[RetrievedEvidence]: ...


def _coerce_iso_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.utcnow()


def _validate_sql_identifier(value: str) -> str:
    normalized = value.strip()
    if not _SQL_IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid SQL identifier: {value}")
    return normalized


def _vector_literal(values: Sequence[float | int]) -> str:
    return "[" + ",".join(f"{float(item):.12g}" for item in values) + "]"


class ChromaVectorStore:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        if not config.enable_vector_store:
            raise VectorStoreDisabled("Vector store disabled by config")

        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("chromadb is required for chroma backend") from exc

        self._dashscope = None
        if config.dashscope_api_key:
            try:
                import dashscope

                dashscope.api_key = config.dashscope_api_key
                self._dashscope = dashscope
            except ImportError as exc:
                raise RuntimeError("dashscope is required for chroma backend") from exc

        os.makedirs(config.chroma_path, exist_ok=True)
        self._client = chromadb.PersistentClient(path=config.chroma_path)
        self._collection = self._client.get_or_create_collection(
            name=config.chroma_collection_sources,
            metadata={"hnsw:space": "cosine"},
        )

    def is_ready(self) -> bool:
        return bool(self._config.dashscope_api_key)

    def _embed_texts(self, texts: list[str]) -> list[PyEmbedding]:
        if not self._config.dashscope_api_key:
            raise EmbeddingsUnavailable("DASHSCOPE_API_KEY not configured (embeddings disabled)")
        if self._dashscope is None:
            raise EmbeddingsUnavailable("dashscope client unavailable")

        resp = self._dashscope.TextEmbedding.call(
            model=self._config.dashscope_embeddings_model,
            input=texts,
        )
        status_code = getattr(resp, "status_code", None)
        if status_code is None and isinstance(resp, dict):
            status_code = resp.get("status_code")
        if status_code != HTTPStatus.OK:
            message = getattr(resp, "message", None)
            if message is None and isinstance(resp, dict):
                message = resp.get("message")
            raise EmbeddingsUnavailable(f"DashScope embeddings failed: {message or status_code}")

        output = getattr(resp, "output", None)
        if output is None and isinstance(resp, dict):
            output = resp.get("output")
        embeddings = None
        if isinstance(output, dict):
            embeddings = output.get("embeddings")
        else:
            embeddings = getattr(output, "embeddings", None)

        if not isinstance(embeddings, list):
            raise EmbeddingsUnavailable("DashScope embeddings response missing output.embeddings")

        items: list[tuple[int, PyEmbedding]] = []
        for idx, item in enumerate(embeddings):
            if not isinstance(item, dict):
                continue
            emb = item.get("embedding")
            if not isinstance(emb, list):
                continue
            text_index = item.get("text_index", idx)
            try:
                order = int(text_index)
            except Exception:
                order = idx
            items.append((order, [float(x) for x in emb]))

        items.sort(key=lambda pair: pair[0])
        vectors = [vec for _, vec in items]
        if len(vectors) != len(texts):
            logger.warning("dashscope_embeddings_mismatch expected=%s got=%s", len(texts), len(vectors))
        return vectors

    def upsert_events(self, events: list[Event]) -> int:
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[ChromaMetadata] = []

        for event in events:
            for evidence in event.evidence:
                excerpt = (evidence.excerpt or event.summary or "").strip()
                if not excerpt:
                    continue
                excerpt = excerpt[:1200]
                document = "\n".join(
                    [
                        f"headline: {event.headline}",
                        f"summary: {event.summary}",
                        f"source_title: {evidence.title}",
                        f"excerpt: {excerpt}",
                    ]
                )
                ids.append(f"evidence:{evidence.quote_id}")
                documents.append(document)
                metadatas.append(
                    {
                        "quote_id": evidence.quote_id,
                        "event_id": event.event_id,
                        "publisher": event.publisher,
                        "title": evidence.title,
                        "source_url": evidence.source_url,
                        "published_at": evidence.published_at.isoformat(),
                        "markets": ",".join(event.markets),
                        "tickers": ",".join(event.tickers),
                        "event_type": event.event_type,
                        "stance": event.stance,
                        "impact": int(event.impact),
                        "confidence": float(event.confidence),
                    }
                )

        if not ids:
            return 0

        embeddings = self._embed_texts(documents)
        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        logger.info("chroma_upsert count=%s", len(ids))
        return len(ids)

    def query(self, query_text: str, *, top_k: int) -> list[RetrievedEvidence]:
        query_text = query_text.strip()
        if not query_text:
            return []

        query_embedding = self._embed_texts([query_text])[0]
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["metadatas", "documents", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        retrieved: list[RetrievedEvidence] = []
        for doc_id, metadata, document, distance in zip(ids, metadatas, documents, distances):
            if not isinstance(metadata, dict):
                continue
            excerpt = ""
            if isinstance(document, str):
                for line in reversed(document.splitlines()):
                    if line.startswith("excerpt:"):
                        excerpt = line.removeprefix("excerpt:").strip()
                        break

            evidence = EventEvidence(
                quote_id=str(metadata.get("quote_id") or doc_id),
                source_url=str(metadata.get("source_url") or ""),
                title=str(metadata.get("title") or ""),
                published_at=_coerce_iso_datetime(str(metadata.get("published_at") or "")),
                excerpt=excerpt,
            )
            score = 1.0 - float(distance) if distance is not None else 0.0
            retrieved.append(RetrievedEvidence(evidence=evidence, score=score))

        return retrieved


class PgVectorStore:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        if not config.enable_vector_store:
            raise VectorStoreDisabled("Vector store disabled by config")

        self._dsn = config.pgvector_dsn.strip()
        if not self._dsn:
            raise RuntimeError("PGVECTOR_DSN is required when VECTOR_BACKEND=pgvector")
        self._table = _validate_sql_identifier(config.pgvector_table)

        try:
            import psycopg  # pyright: ignore[reportMissingImports] - optional pgvector dependency
        except ImportError as exc:
            raise RuntimeError(
                "psycopg is required for pgvector backend (install: uv add --project apps/api \"psycopg[binary]\")"
            ) from exc
        self._psycopg = psycopg

        self._dashscope = None
        if config.dashscope_api_key:
            try:
                import dashscope

                dashscope.api_key = config.dashscope_api_key
                self._dashscope = dashscope
            except ImportError as exc:
                raise RuntimeError("dashscope is required for pgvector backend") from exc

        self._ensure_schema()

    def _connect(self):
        return self._psycopg.connect(self._dsn, autocommit=True)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._table} (
                        doc_id TEXT PRIMARY KEY,
                        document TEXT NOT NULL,
                        embedding vector NOT NULL,
                        metadata JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )

    def is_ready(self) -> bool:
        return bool(self._config.dashscope_api_key)

    def _embed_texts(self, texts: list[str]) -> list[PyEmbedding]:
        if not self._config.dashscope_api_key:
            raise EmbeddingsUnavailable("DASHSCOPE_API_KEY not configured (embeddings disabled)")
        if self._dashscope is None:
            raise EmbeddingsUnavailable("dashscope client unavailable")

        resp = self._dashscope.TextEmbedding.call(
            model=self._config.dashscope_embeddings_model,
            input=texts,
        )
        status_code = getattr(resp, "status_code", None)
        if status_code is None and isinstance(resp, dict):
            status_code = resp.get("status_code")
        if status_code != HTTPStatus.OK:
            message = getattr(resp, "message", None)
            if message is None and isinstance(resp, dict):
                message = resp.get("message")
            raise EmbeddingsUnavailable(f"DashScope embeddings failed: {message or status_code}")

        output = getattr(resp, "output", None)
        if output is None and isinstance(resp, dict):
            output = resp.get("output")
        embeddings = None
        if isinstance(output, dict):
            embeddings = output.get("embeddings")
        else:
            embeddings = getattr(output, "embeddings", None)

        if not isinstance(embeddings, list):
            raise EmbeddingsUnavailable("DashScope embeddings response missing output.embeddings")

        items: list[tuple[int, PyEmbedding]] = []
        for idx, item in enumerate(embeddings):
            if not isinstance(item, dict):
                continue
            emb = item.get("embedding")
            if not isinstance(emb, list):
                continue
            text_index = item.get("text_index", idx)
            try:
                order = int(text_index)
            except Exception:
                order = idx
            items.append((order, [float(x) for x in emb]))

        items.sort(key=lambda pair: pair[0])
        vectors = [vec for _, vec in items]
        if len(vectors) != len(texts):
            logger.warning("dashscope_embeddings_mismatch expected=%s got=%s", len(texts), len(vectors))
        return vectors

    def upsert_events(self, events: list[Event]) -> int:
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[ChromaMetadata] = []

        for event in events:
            for evidence in event.evidence:
                excerpt = (evidence.excerpt or event.summary or "").strip()
                if not excerpt:
                    continue
                excerpt = excerpt[:1200]
                document = "\n".join(
                    [
                        f"headline: {event.headline}",
                        f"summary: {event.summary}",
                        f"source_title: {evidence.title}",
                        f"excerpt: {excerpt}",
                    ]
                )
                ids.append(f"evidence:{evidence.quote_id}")
                documents.append(document)
                metadatas.append(
                    {
                        "quote_id": evidence.quote_id,
                        "event_id": event.event_id,
                        "publisher": event.publisher,
                        "title": evidence.title,
                        "source_url": evidence.source_url,
                        "published_at": evidence.published_at.isoformat(),
                        "markets": ",".join(event.markets),
                        "tickers": ",".join(event.tickers),
                        "event_type": event.event_type,
                        "stance": event.stance,
                        "impact": int(event.impact),
                        "confidence": float(event.confidence),
                    }
                )

        if not ids:
            return 0

        embeddings = self._embed_texts(documents)
        with self._connect() as conn:
            with conn.cursor() as cursor:
                for doc_id, document, metadata, embedding in zip(ids, documents, metadatas, embeddings):
                    cursor.execute(
                        f"""
                        INSERT INTO {self._table} (doc_id, document, embedding, metadata, updated_at)
                        VALUES (%s, %s, %s::vector, %s::jsonb, NOW())
                        ON CONFLICT (doc_id) DO UPDATE
                        SET document = EXCLUDED.document,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                        """,
                        (
                            doc_id,
                            document,
                            _vector_literal(embedding),
                            json.dumps(metadata, ensure_ascii=False),
                        ),
                    )

        logger.info("pgvector_upsert count=%s table=%s", len(ids), self._table)
        return len(ids)

    def query(self, query_text: str, *, top_k: int) -> list[RetrievedEvidence]:
        normalized = query_text.strip()
        if not normalized:
            return []

        query_embedding = self._embed_texts([normalized])[0]
        vector = _vector_literal(query_embedding)
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT doc_id, document, metadata, (1 - (embedding <=> %s::vector)) AS score
                    FROM {self._table}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (vector, vector, max(top_k, 1)),
                )
                rows = cursor.fetchall()

        retrieved: list[RetrievedEvidence] = []
        for row in rows:
            doc_id, document, metadata_raw, score_raw = row
            metadata = metadata_raw
            if isinstance(metadata_raw, str):
                try:
                    metadata = json.loads(metadata_raw)
                except ValueError:
                    metadata = {}
            if not isinstance(metadata, dict):
                continue

            excerpt = ""
            if isinstance(document, str):
                for line in reversed(document.splitlines()):
                    if line.startswith("excerpt:"):
                        excerpt = line.removeprefix("excerpt:").strip()
                        break

            evidence = EventEvidence(
                quote_id=str(metadata.get("quote_id") or doc_id),
                source_url=str(metadata.get("source_url") or ""),
                title=str(metadata.get("title") or ""),
                published_at=_coerce_iso_datetime(str(metadata.get("published_at") or "")),
                excerpt=excerpt,
            )
            score = float(score_raw) if score_raw is not None else 0.0
            retrieved.append(RetrievedEvidence(evidence=evidence, score=score))

        return retrieved


VectorStore = ChromaVectorStore


def create_vector_store(config: AppConfig) -> BaseVectorStore:
    if not config.enable_vector_store:
        raise VectorStoreDisabled("Vector store disabled by config")

    backend = config.vector_backend.strip().lower()
    if backend == "chroma":
        return ChromaVectorStore(config)
    if backend == "simple":
        from .simple_vector_store import SimpleVectorStore

        return SimpleVectorStore(config)
    if backend == "pgvector":
        return PgVectorStore(config)
    raise ValueError(f"Unsupported vector backend: {backend}")
