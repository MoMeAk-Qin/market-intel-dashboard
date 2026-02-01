from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import chromadb
import dashscope
from http import HTTPStatus

from ..config import AppConfig
from ..models import Event, EventEvidence

logger = logging.getLogger("vector_store")


class VectorStoreDisabled(RuntimeError):
    pass


class EmbeddingsUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class RetrievedEvidence:
    evidence: EventEvidence
    score: float


def _coerce_iso_datetime(value: str) -> datetime:
    # Chroma metadata stores only JSON-ish primitives; we persist datetime as ISO strings.
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        # Best-effort fallback; keep server running even if one record is malformed.
        return datetime.utcnow()


class VectorStore:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        if not config.enable_vector_store:
            raise VectorStoreDisabled("Vector store disabled by config")

        os.makedirs(config.chroma_path, exist_ok=True)
        self._client = chromadb.PersistentClient(path=config.chroma_path)
        self._collection = self._client.get_or_create_collection(
            name=config.chroma_collection_sources,
            metadata={"hnsw:space": "cosine"},
        )

        if config.dashscope_api_key:
            dashscope.api_key = config.dashscope_api_key

    def is_ready(self) -> bool:
        return bool(self._config.dashscope_api_key)

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self._config.dashscope_api_key:
            raise EmbeddingsUnavailable("DASHSCOPE_API_KEY not configured (embeddings disabled)")
        # DashScope embeddings API accepts either a single string or a list of strings.
        resp = dashscope.TextEmbedding.call(
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

        # Each item usually contains {"embedding": [...], "text_index": i}.
        items: list[tuple[int, list[float]]] = []
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

        items.sort(key=lambda t: t[0])
        vectors = [vec for _, vec in items]
        if len(vectors) != len(texts):
            # Best-effort: still return what we have, but warn about mismatch.
            logger.warning("dashscope_embeddings_mismatch expected=%s got=%s", len(texts), len(vectors))
        return vectors

    def upsert_events(self, events: list[Event]) -> int:
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for event in events:
            for ev in event.evidence:
                excerpt = (ev.excerpt or event.summary or "").strip()
                if not excerpt:
                    continue
                excerpt = excerpt[:1200]
                doc = "\n".join(
                    [
                        f"headline: {event.headline}",
                        f"summary: {event.summary}",
                        f"source_title: {ev.title}",
                        f"excerpt: {excerpt}",
                    ]
                )
                ids.append(f"evidence:{ev.quote_id}")
                documents.append(doc)
                metadatas.append(
                    {
                        "quote_id": ev.quote_id,
                        "event_id": event.event_id,
                        "publisher": event.publisher,
                        "title": ev.title,
                        "source_url": ev.source_url,
                        "published_at": ev.published_at.isoformat(),
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
        for doc_id, meta, doc, dist in zip(ids, metadatas, documents, distances):
            if not isinstance(meta, dict):
                continue
            excerpt = ""
            if isinstance(doc, str):
                # Recover the last line "excerpt: ..." as the most useful snippet.
                for line in reversed(doc.splitlines()):
                    if line.startswith("excerpt:"):
                        excerpt = line.removeprefix("excerpt:").strip()
                        break

            evidence = EventEvidence(
                quote_id=str(meta.get("quote_id") or doc_id),
                source_url=str(meta.get("source_url") or ""),
                title=str(meta.get("title") or ""),
                published_at=_coerce_iso_datetime(str(meta.get("published_at") or "")),
                excerpt=excerpt,
            )

            # cosine distance -> similarity score (best-effort)
            score = 1.0 - float(dist) if dist is not None else 0.0
            retrieved.append(RetrievedEvidence(evidence=evidence, score=score))

        return retrieved
