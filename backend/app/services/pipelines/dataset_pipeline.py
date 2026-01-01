from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from app.core.config import settings
from app.services.pipelines.jobs import DatasetPipelineJob


class DatasetPipeline:
    def __init__(self, runner: Callable[[DatasetPipelineJob], Awaitable[None]]):
        self._runner = runner
        self._q: asyncio.Queue[DatasetPipelineJob] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if not settings.pipeline_enabled:
            return
        if self._worker_task and not self._worker_task.done():
            return
        self._stop_event.clear()
        self._worker_task = asyncio.create_task(self._worker_loop(), name="pipeline-worker")

    async def stop(self) -> None:
        if not self._worker_task:
            return
        self._stop_event.set()
        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        self._worker_task = None

    async def enqueue_dataset(self, dataset_id: str, url: str) -> None:
        if not settings.pipeline_enabled:
            raise RuntimeError("pipeline is disabled")
        await self._q.put(DatasetPipelineJob(dataset_id=dataset_id, url=url))

    async def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            job = await self._q.get()
            try:
                await self._runner(job)
            finally:
                self._q.task_done()


_pipeline: DatasetPipeline | None = None


def get_pipeline(runner: Callable[[DatasetPipelineJob], Awaitable[None]]):
    global _pipeline
    if _pipeline is None:
        _pipeline = DatasetPipeline(runner=runner)
    return _pipeline




