"""
Six-agent analysis pipeline — inspired by Understand-Anything's agent design,
adapted to Companion's plugin-driven architecture.

Agents run in this order:
  1. project_scanner    — discover files, detect languages
  2. file_analyzer      — parallel tree-sitter parse (up to 5 concurrent)
  3. feature_extractor  — LLM identifies business features per domain
  4. architecture_analyzer — assign architectural layers
  5. graph_builder      — persist nodes/edges to Neo4j
  6. ai_compressor      — generate compressed AI contexts
"""
import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from companion.core.agents.project_scanner import ProjectScanner
from companion.core.agents.file_analyzer import FileAnalyzer
from companion.core.agents.feature_extractor import FeatureExtractorAgent
from companion.core.agents.architecture_analyzer import ArchitectureAnalyzer
from companion.core.agents.graph_builder import GraphBuilder
from companion.core.agents.ai_compressor import AICompressorAgent
from companion.core.engine.event_bus import EventType

if TYPE_CHECKING:
    from companion.core.engine.core_engine import CoreEngine

log = structlog.get_logger()

_MAX_CONCURRENT_FILE_ANALYZERS = 5
_BATCH_SIZE = 20


class AnalysisPipeline:
    def __init__(self, engine: "CoreEngine", repo_path: Path, incremental: bool = False) -> None:
        self.engine = engine
        self.repo_path = repo_path
        self.incremental = incremental

    async def run(self) -> dict[str, Any]:
        log.info("pipeline_started", repo=str(self.repo_path), incremental=self.incremental)

        # Stage 1: scan
        scanner = ProjectScanner(self.repo_path)
        scan_result = await scanner.scan(incremental=self.incremental)
        log.info("stage1_done", files=len(scan_result["files"]))

        # Stage 2: parallel file analysis (batched)
        sem = asyncio.Semaphore(_MAX_CONCURRENT_FILE_ANALYZERS)
        analyzer = FileAnalyzer(
            plugin_registry=self.engine.registry,
            semaphore=sem,
        )
        all_parse_results: list[dict[str, Any]] = []
        files = scan_result["files"]
        for i in range(0, len(files), _BATCH_SIZE):
            batch = files[i : i + _BATCH_SIZE]
            batch_results = await asyncio.gather(
                *[analyzer.analyze(f) for f in batch],
                return_exceptions=False,
            )
            all_parse_results.extend(batch_results)
        log.info("stage2_done", parsed_files=len(all_parse_results))

        # Stage 3: feature extraction
        extractor = FeatureExtractorAgent(plugin_registry=self.engine.registry)
        features = await extractor.extract(all_parse_results, str(self.repo_path))
        log.info("stage3_done", features=len(features.get("features", [])))

        # Stage 4: architecture layers
        arch_analyzer = ArchitectureAnalyzer()
        arch_result = await arch_analyzer.analyze(features, all_parse_results)
        log.info("stage4_done", layers=len(arch_result.get("layers", {})))

        # Stage 5: persist to graph
        builder = GraphBuilder(neo4j=self.engine.neo4j)
        graph_summary = await builder.build(features, arch_result)
        log.info("stage5_done", nodes=graph_summary.get("nodes_created", 0))

        # Stage 6: AI compression
        compressor = AICompressorAgent(plugin_registry=self.engine.registry)
        compressed = await compressor.compress(features, graph_summary)
        log.info("stage6_done", ratio=compressed.get("compression_ratio", 0))

        await self.engine.event_bus.publish(
            EventType.GRAPH_REBUILT,
            {"repo_path": str(self.repo_path), "summary": graph_summary},
        )

        return {
            "scan": scan_result,
            "features": features,
            "architecture": arch_result,
            "graph": graph_summary,
            "compression": compressed,
        }
