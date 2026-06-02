import asyncio
import pytest
from companion.core.engine.job_scheduler import JobScheduler, JobStatus


@pytest.mark.asyncio
async def test_submit_and_complete():
    scheduler = JobScheduler(max_concurrent=2)

    async def work():
        await asyncio.sleep(0.05)
        return "done"

    job_id = await scheduler.submit("test-job", work)
    await asyncio.sleep(0.2)

    job = scheduler.get_status(job_id)
    assert job is not None
    assert job.status == JobStatus.COMPLETED
    assert job.result == "done"


@pytest.mark.asyncio
async def test_failed_job_captured():
    scheduler = JobScheduler(max_concurrent=2)

    async def failing():
        raise ValueError("boom")

    job_id = await scheduler.submit("fail-job", failing)
    await asyncio.sleep(0.2)

    job = scheduler.get_status(job_id)
    assert job.status == JobStatus.FAILED
    assert "boom" in job.error


@pytest.mark.asyncio
async def test_concurrency_limit():
    scheduler = JobScheduler(max_concurrent=2)
    started = []

    async def slow():
        started.append(1)
        await asyncio.sleep(0.3)

    for _ in range(5):
        await scheduler.submit("slow", slow)

    await asyncio.sleep(0.05)
    assert scheduler.running_count() <= 2
