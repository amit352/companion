import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

import structlog

log = structlog.get_logger()


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    fn: Callable[..., Coroutine[Any, Any, Any]] = field(repr=False, default=None)  # type: ignore[assignment]
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: str | None = None


class JobScheduler:
    """Async job scheduler with configurable concurrency (NFR-2 performance)."""

    def __init__(self, max_concurrent: int = 5) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._jobs: dict[UUID, Job] = {}

    async def submit(
        self,
        name: str,
        fn: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> UUID:
        job = Job(name=name, fn=fn, args=args, kwargs=kwargs)
        self._jobs[job.id] = job
        asyncio.create_task(self._run(job))
        log.debug("job_submitted", job_id=str(job.id), name=name)
        return job.id

    async def _run(self, job: Job) -> None:
        async with self._semaphore:
            job.status = JobStatus.RUNNING
            try:
                job.result = await job.fn(*job.args, **job.kwargs)
                job.status = JobStatus.COMPLETED
                log.info("job_completed", job_id=str(job.id), name=job.name)
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                log.error("job_failed", job_id=str(job.id), name=job.name, error=str(exc))

    def get_status(self, job_id: UUID) -> Job | None:
        return self._jobs.get(job_id)

    def running_count(self) -> int:
        return sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING)
