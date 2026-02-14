from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from uuid import uuid4

from ..models import AnalysisRequest, AnalysisResponse, TaskInfo, TaskList, TaskStatus


@dataclass
class _TaskRecord:
    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    payload: AnalysisRequest
    result: AnalysisResponse | None = None
    error: str | None = None
    dedupe_key: str = ""


class AnalysisTaskQueue:
    def __init__(
        self,
        *,
        worker: Callable[[AnalysisRequest], AnalysisResponse],
        max_tasks: int = 300,
    ) -> None:
        self._worker = worker
        self._max_tasks = max(max_tasks, 50)
        self._lock = asyncio.Lock()
        self._tasks: dict[str, _TaskRecord] = {}
        self._dedupe_index: dict[str, str] = {}

    async def submit(self, payload: AnalysisRequest) -> TaskInfo:
        dedupe_key = _build_dedupe_key(payload)
        async with self._lock:
            existing_id = self._dedupe_index.get(dedupe_key)
            if existing_id is not None:
                existing = self._tasks.get(existing_id)
                if existing is not None and existing.status != "failed":
                    return _to_task_info(existing)

            now = datetime.now(UTC)
            task_id = uuid4().hex
            record = _TaskRecord(
                task_id=task_id,
                status="pending",
                created_at=now,
                updated_at=now,
                payload=payload.model_copy(deep=True),
                dedupe_key=dedupe_key,
            )
            self._tasks[task_id] = record
            self._dedupe_index[dedupe_key] = task_id
            self._trim_locked()

        asyncio.create_task(self._run_task(task_id), name=f"analysis-task-{task_id}")
        return _to_task_info(record)

    async def get(self, task_id: str) -> TaskInfo | None:
        async with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                return None
            return _to_task_info(record)

    async def list(self, *, limit: int = 20) -> TaskList:
        safe_limit = max(1, min(limit, 200))
        async with self._lock:
            ordered = sorted(
                self._tasks.values(),
                key=lambda item: (item.created_at, item.task_id),
                reverse=True,
            )
            items = [_to_task_info(item) for item in ordered[:safe_limit]]
            return TaskList(items=items, total=len(self._tasks))

    async def _run_task(self, task_id: str) -> None:
        async with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                return
            record.status = "running"
            record.updated_at = datetime.now(UTC)
            payload = record.payload.model_copy(deep=True)

        try:
            result = await asyncio.to_thread(self._worker, payload)
        except Exception as exc:
            async with self._lock:
                record = self._tasks.get(task_id)
                if record is None:
                    return
                record.status = "failed"
                record.error = str(exc)
                record.updated_at = datetime.now(UTC)
            return

        async with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                return
            record.status = "completed"
            record.result = result
            record.error = None
            record.updated_at = datetime.now(UTC)
            self._trim_locked()

    def _trim_locked(self) -> None:
        if len(self._tasks) <= self._max_tasks:
            return
        ordered_ids = sorted(
            self._tasks,
            key=lambda task_id: (self._tasks[task_id].created_at, task_id),
            reverse=True,
        )
        keep_ids = set(ordered_ids[: self._max_tasks])
        remove_ids = [task_id for task_id in self._tasks if task_id not in keep_ids]
        for task_id in remove_ids:
            self._tasks.pop(task_id, None)

        stale_keys = [
            key
            for key, indexed_task_id in self._dedupe_index.items()
            if indexed_task_id not in self._tasks
        ]
        for key in stale_keys:
            self._dedupe_index.pop(key, None)


def _to_task_info(record: _TaskRecord) -> TaskInfo:
    return TaskInfo(
        task_id=record.task_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        payload=record.payload,
        result=record.result,
        error=record.error,
    )


def _build_dedupe_key(payload: AnalysisRequest) -> str:
    encoded = json.dumps(
        {
            "question": payload.question.strip(),
            "context": (payload.context or "").strip(),
            "sources": payload.sources,
            "use_retrieval": payload.use_retrieval,
            "top_k": payload.top_k,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
