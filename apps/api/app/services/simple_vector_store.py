from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re

from ..config import AppConfig
from ..models import Event, EventEvidence
from .vector_store import RetrievedEvidence

_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


@dataclass
class _SimpleEntry:
    doc_id: str
    tokens: set[str]
    evidence: EventEvidence


class SimpleVectorStore:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._index_path = Path(config.chroma_path) / "simple_vector_store.json"
        self._entries: dict[str, _SimpleEntry] = {}
        self._load_from_disk()

    def is_ready(self) -> bool:
        return True

    def upsert_events(self, events: list[Event]) -> int:
        inserted = 0
        for event in events:
            for evidence in event.evidence:
                excerpt = (evidence.excerpt or event.summary or "").strip()
                if not excerpt:
                    continue
                document = "\n".join(
                    [
                        event.headline,
                        event.summary,
                        evidence.title,
                        excerpt,
                        " ".join(event.tickers),
                        " ".join(event.markets),
                    ]
                )
                doc_id = f"evidence:{evidence.quote_id}"
                self._entries[doc_id] = _SimpleEntry(
                    doc_id=doc_id,
                    tokens=_tokenize(document),
                    evidence=EventEvidence(
                        quote_id=evidence.quote_id,
                        source_url=evidence.source_url,
                        title=evidence.title,
                        published_at=evidence.published_at,
                        excerpt=excerpt[:1200],
                    ),
                )
                inserted += 1
        if inserted > 0:
            self._persist()
        return inserted

    def query(self, query_text: str, *, top_k: int) -> list[RetrievedEvidence]:
        tokens = _tokenize(query_text)
        if not tokens:
            return []

        scored: list[tuple[float, _SimpleEntry]] = []
        for entry in self._entries.values():
            overlap = len(tokens & entry.tokens)
            if overlap <= 0:
                continue
            denom = max(len(tokens), 1)
            score = overlap / denom
            if entry.evidence.title and entry.evidence.title.lower() in query_text.lower():
                score += 0.15
            scored.append((score, entry))

        scored.sort(
            key=lambda pair: (pair[0], pair[1].evidence.published_at),
            reverse=True,
        )

        return [
            RetrievedEvidence(evidence=item.evidence, score=score)
            for score, item in scored[: max(top_k, 1)]
        ]

    def _load_from_disk(self) -> None:
        if not self._index_path.exists():
            return
        try:
            payload = json.loads(self._index_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(payload, list):
            return

        for item in payload:
            if not isinstance(item, dict):
                continue
            doc_id = str(item.get("doc_id") or "").strip()
            if not doc_id:
                continue
            quote_id = str(item.get("quote_id") or "").strip()
            source_url = str(item.get("source_url") or "").strip()
            title = str(item.get("title") or "").strip()
            excerpt = str(item.get("excerpt") or "").strip()
            published_raw = str(item.get("published_at") or "").strip()
            tokens_raw = item.get("tokens")
            if not quote_id or not source_url:
                continue
            if not isinstance(tokens_raw, list):
                continue
            tokens = {str(token).lower() for token in tokens_raw if str(token).strip()}
            if not tokens:
                continue
            self._entries[doc_id] = _SimpleEntry(
                doc_id=doc_id,
                tokens=tokens,
                evidence=EventEvidence(
                    quote_id=quote_id,
                    source_url=source_url,
                    title=title,
                    published_at=_parse_iso_datetime(published_raw),
                    excerpt=excerpt,
                ),
            )

    def _persist(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        payload: list[dict[str, object]] = []
        for entry in self._entries.values():
            payload.append(
                {
                    "doc_id": entry.doc_id,
                    "quote_id": entry.evidence.quote_id,
                    "source_url": entry.evidence.source_url,
                    "title": entry.evidence.title,
                    "published_at": entry.evidence.published_at.isoformat(),
                    "excerpt": entry.evidence.excerpt,
                    "tokens": sorted(entry.tokens),
                }
            )
        self._index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _tokenize(text: str) -> set[str]:
    lowered = text.lower()
    return {token for token in _TOKEN_PATTERN.findall(lowered) if token}


def _parse_iso_datetime(value: str) -> datetime:
    if not value:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(UTC)
