"""
Redis-backed job queue using RQ (Phase 6 NFR-1/NFR-2).

Falls back to the in-process JobScheduler when Redis is unavailable
so development works without Redis running.

Usage:
  # Enqueue a job
  from companion.core.queue import enqueue_analysis
  job_id = enqueue_analysis(repo_path, incremental=False)

  # Start a worker (separate process)
  rq worker companion-analysis
"""
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

log = structlog.get_logger()

_QUEUE_NAME = "companion-analysis"


def _get_redis():
    import redis
    url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(url)


def _rq_available() -> bool:
    try:
        r = _get_redis()
        r.ping()
        return True
    except Exception:
        return False


def enqueue_analysis(
    repo_path: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    plugin_dirs: list[str],
    incremental: bool = False,
) -> str:
    """
    Enqueue an analysis job. Returns a job ID.
    Uses RQ when Redis is available, falls back to a stub when not.
    """
    if _rq_available():
        from rq import Queue
        q   = Queue(_QUEUE_NAME, connection=_get_redis())
        job = q.enqueue(
            _run_analysis_worker,
            kwargs=dict(
                repo_path=repo_path,
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                plugin_dirs=plugin_dirs,
                incremental=incremental,
            ),
            job_timeout=1800,   # 30 min max
        )
        log.info("job_queued_redis", job_id=job.id, repo=repo_path)
        return job.id
    else:
        log.warning("redis_unavailable_fallback", repo=repo_path)
        return str(uuid4())   # caller uses in-process fallback


def get_job_status(job_id: str) -> dict[str, Any]:
    """Return job status from RQ or unknown if not available."""
    if not _rq_available():
        return {"job_id": job_id, "status": "unknown", "error": "Redis not available"}
    try:
        from rq.job import Job
        job = Job.fetch(job_id, connection=_get_redis())
        return {
            "job_id": job_id,
            "status": job.get_status().value,
            "error":  str(job.exc_info) if job.exc_info else None,
            "result": job.result,
        }
    except Exception as e:
        return {"job_id": job_id, "status": "not_found", "error": str(e)}


def _run_analysis_worker(
    repo_path: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    plugin_dirs: list[str],
    incremental: bool,
) -> dict[str, Any]:
    """
    Executed by RQ worker process. Runs the full analysis pipeline.
    This function runs outside the FastAPI process.
    """
    import asyncio
    from companion.core.engine.core_engine import CoreEngine
    from companion.graph.neo4j_client import Neo4jClient

    async def _run():
        neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        engine = CoreEngine(
            neo4j_client=neo4j,
            plugin_dirs=[Path(d) for d in plugin_dirs],
        )
        await engine.start()
        result = await engine.analyze_repository(Path(repo_path), incremental=incremental)
        await engine.stop()
        return result

    return asyncio.run(_run())
