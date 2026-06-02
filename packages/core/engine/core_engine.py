from pathlib import Path

import structlog

from feature_graph.core.engine.event_bus import EventBus, EventType
from feature_graph.core.engine.job_scheduler import JobScheduler
from feature_graph.core.engine.plugin_manager import PluginManager
from feature_graph.core.indexer.repository_indexer import RepositoryIndexer
from feature_graph.graph.neo4j_client import Neo4jClient
from feature_graph.sdk.registry import PluginRegistry

log = structlog.get_logger()


class CoreEngine:
    """
    Central orchestrator. Owns plugin lifecycle, event routing, indexing, and graph persistence.
    All external interaction goes through here — plugins never touch internal state directly.
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        plugin_dirs: list[Path] | None = None,
        max_concurrent_jobs: int = 5,
    ) -> None:
        self.event_bus = EventBus()
        self.scheduler = JobScheduler(max_concurrent=max_concurrent_jobs)
        self.registry = PluginRegistry()
        self.plugin_manager = PluginManager(
            plugin_dirs=plugin_dirs or [Path("plugins")],
            registry=self.registry,
        )
        self.neo4j = neo4j_client
        self._indexer: RepositoryIndexer | None = None

    async def start(self) -> None:
        log.info("core_engine_starting")
        await self.neo4j.connect()
        await self.neo4j.ensure_schema()
        await self.plugin_manager.discover_and_load()
        log.info(
            "core_engine_started",
            plugins_loaded=self.plugin_manager.loaded_count,
        )
        # Run event bus in background
        import asyncio
        asyncio.create_task(self.event_bus.start())

    async def analyze_repository(self, repo_path: Path, incremental: bool = False) -> str:
        """Trigger full or incremental repository analysis pipeline (FR-5)."""
        from feature_graph.core.agents.pipeline import AnalysisPipeline

        await self.event_bus.publish(
            EventType.ANALYSIS_STARTED,
            {"repo_path": str(repo_path), "incremental": incremental},
        )

        pipeline = AnalysisPipeline(
            engine=self,
            repo_path=repo_path,
            incremental=incremental,
        )

        job_id = await self.scheduler.submit(
            name=f"analyze:{repo_path.name}",
            fn=pipeline.run,
        )
        return str(job_id)

    async def stop(self) -> None:
        await self.plugin_manager.shutdown_all()
        await self.event_bus.stop()
        await self.neo4j.close()
        log.info("core_engine_stopped")
