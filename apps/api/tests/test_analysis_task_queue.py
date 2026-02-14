from __future__ import annotations

import asyncio

import pytest

from app.models import AnalysisRequest, AnalysisResponse
from app.services.task_queue import AnalysisTaskQueue


async def _wait_until_done(queue: AnalysisTaskQueue, task_id: str, timeout_seconds: float = 2.0):
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        task = await queue.get(task_id)
        if task is not None and task.status in {"completed", "failed"}:
            return task
        await asyncio.sleep(0.02)
    raise AssertionError("task did not finish in time")


@pytest.mark.anyio
async def test_task_queue_dedupes_same_payload() -> None:
    def worker(payload: AnalysisRequest) -> AnalysisResponse:
        return AnalysisResponse(answer=f"answer:{payload.question}", model="test", usage=None, sources=[])

    queue = AnalysisTaskQueue(worker=worker)
    payload = AnalysisRequest(question="AAPL guidance")

    task_a = await queue.submit(payload)
    task_b = await queue.submit(payload)

    assert task_a.task_id == task_b.task_id

    completed = await _wait_until_done(queue, task_a.task_id)
    assert completed.status == "completed"
    assert completed.result is not None
    assert completed.result.answer == "answer:AAPL guidance"


@pytest.mark.anyio
async def test_task_queue_marks_failed_task() -> None:
    def worker(_: AnalysisRequest) -> AnalysisResponse:
        raise RuntimeError("analysis boom")

    queue = AnalysisTaskQueue(worker=worker)
    task = await queue.submit(AnalysisRequest(question="USDHKD"))

    failed = await _wait_until_done(queue, task.task_id)
    assert failed.status == "failed"
    assert failed.error is not None
    assert "analysis boom" in failed.error


@pytest.mark.anyio
async def test_task_queue_list_returns_latest_first() -> None:
    def worker(payload: AnalysisRequest) -> AnalysisResponse:
        return AnalysisResponse(answer=payload.question, model="test", usage=None, sources=[])

    queue = AnalysisTaskQueue(worker=worker)
    task_a = await queue.submit(AnalysisRequest(question="first"))
    await asyncio.sleep(0.01)
    task_b = await queue.submit(AnalysisRequest(question="second"))

    await _wait_until_done(queue, task_a.task_id)
    await _wait_until_done(queue, task_b.task_id)

    listing = await queue.list(limit=10)
    assert listing.total >= 2
    assert listing.items[0].payload.question == "second"
    assert listing.items[1].payload.question == "first"
