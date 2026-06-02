# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (use the venv — system python3 lacks project deps)
pip install -e ".[dev]"          # or: .venv/bin/pip install -e ".[dev]"

# Infrastructure
docker compose up -d neo4j postgres redis

# API server
.venv/bin/fg serve               # uvicorn on :8000, --reload
# or directly:
uvicorn companion.api.main:app --reload

# Frontend
cd frontend && npm install && npm run dev   # Next.js on :3000

# CLI (requires API server running)
fg analyze /path/to/repo
fg analyze /path/to/repo --incremental
fg status <job_id>
fg plugins
fg ask "What handles authentication?"

# Tests
.venv/bin/python -m pytest tests/unit/ -v                    # unit (no infra needed)
.venv/bin/python -m pytest tests/integration/ -v             # needs Neo4j running
.venv/bin/python -m pytest tests/unit/test_plugin_registry.py -v  # single file

# Lint / type check
.venv/bin/ruff check src/ plugins/ tests/
.venv/bin/mypy src/
```

Always run tests with `.venv/bin/python -m pytest`, not the system `pytest`.

## Architecture

### Source layout

```
src/companion/          # main Python package (importable as `companion`)
  api/                  # FastAPI app + routes (/analysis, /features, /graph, /chat, /plugins, /feedback)
  core/
    agents/             # 6-agent pipeline (see Pipeline section)
    engine/             # CoreEngine, EventBus, JobScheduler, PluginManager
    deduplication.py    # fuzzy-merge across extractor outputs
  graph/
    models/             # Pydantic node/relationship models for Neo4j
    neo4j_client.py     # async Neo4j driver wrapper
  sdk/
    base/               # abstract base classes for each plugin type
    registry.py         # in-memory plugin registry
  config.py             # pydantic-settings (reads .env)
  cli.py                # click CLI (entrypoint: `fg`)

plugins/                # auto-discovered on startup via plugin.json manifests
  parsers/              # python_parser, typescript_parser (tree-sitter)
  extractors/           # auth_detector, billing_detector, workflow_detector (LLM)
    _base.py            # shared call_claude / filter_symbols helpers
  compression/          # default_compressor (LLM)

tests/unit/             # no infra required — mocks Neo4j/LLM
tests/integration/      # requires docker compose up -d neo4j
```

### Six-agent pipeline (`src/companion/core/agents/pipeline.py`)

Runs sequentially when `CoreEngine.analyze_repository()` is called:

| Stage | Agent | What it does |
|---|---|---|
| 1 | `ProjectScanner` | Walk repo, detect languages, SHA256 hash files for incremental tracking |
| 2 | `FileAnalyzer` | Parallel tree-sitter parse via Parser plugins (up to 5 concurrent) |
| 3 | `FeatureExtractorAgent` | Fan-out to all registered `feature-extractor` plugins → deduplicate |
| 4 | `ArchitectureAnalyzer` | Keyword-based layer assignment (api/service/data/ui/utility/config); no LLM |
| 5 | `GraphBuilder` | Upsert Feature + relationship nodes to Neo4j |
| 6 | `AICompressorAgent` | Compress feature graph to ~3K token context via `ai-compression` plugin |

The pipeline is submitted as an async job to `JobScheduler` and runs under a semaphore. Poll `/api/v1/analysis/{job_id}/status` or `fg status <job_id>`.

### Plugin system

Every plugin is a directory with `plugin.json` + `plugin.py` exposing a top-level `Plugin` class. `PluginManager.discover_and_load()` walks all configured `plugin_dirs` at startup (rglobs for `plugin.json`).

**Six plugin types** (defined in `src/companion/sdk/base/`):

| `PluginType` | Base class | Override |
|---|---|---|
| `parser` | `ParserPlugin` | `parse(source, file_path) -> ParseResult` |
| `feature-extractor` | `FeaturePlugin` | `extract_features(symbols, deps, context) -> FeatureExtractionOutput` |
| `documentation` | `DocPlugin` | `generate(feature_graph) -> DocOutput` |
| `ai-compression` | `CompressionPlugin` | `compress(feature_graph, query_context) -> CompressedContext` |
| `runtime-analysis` | `RuntimePlugin` | `process_spans(spans) -> RuntimeMapping` |
| `integration` | `IntegrationPlugin` | `sync(event) -> SyncResult` |

`PluginBase.execute()` is the single entry point the engine calls; each base class implements it by delegating to the typed abstract method above.

### LLM calls

All LLM calls go through `plugins/extractors/_base.py::call_claude()` (extractor plugins) or directly in `plugins/compression/default_compressor/plugin.py`. Both use `anthropic.Anthropic()` (sync) with `claude-haiku-4-5-20251001`. Set `ANTHROPIC_API_KEY` in `.env` — see `.env.example`.

**Extractors short-circuit before calling Claude** if `filter_symbols()` finds no domain-relevant symbols — safe to run without an API key against repos with no matching keywords.

**The compressor always calls Claude** if any features exist. Integration tests that skip LLM must load only parser plugins (no extractors, no compressor directory).

### Neo4j graph model

Nodes: `Feature`, `Service`, `API`, `DatabaseTable`, `UIComponent`, `Requirement`  
Relationships: `DEPENDS_ON`, `USES`, `EXTENDS`, `CONFLICTS_WITH`  
Schema constraints and indexes are bootstrapped by `Neo4jClient.ensure_schema()` at startup.

### Environment

Copy `.env.example` to `.env`. The only required override is `ANTHROPIC_API_KEY`; everything else defaults to match `docker-compose.yml`.

## Integration tests

Integration tests in `tests/integration/` require Neo4j:

```bash
docker compose up -d neo4j
.venv/bin/python -m pytest tests/integration/ -v
```

Set `SKIP_INTEGRATION=1` to skip in CI. Set `ANTHROPIC_API_KEY` to also run the full 6-stage LLM test. Tests that only load parser plugins (no extractors) run without an API key.

## Implementation phases

Current status: **Phase 1 complete, Phase 2 in progress.**  
Full 7-phase plan is in `PLAN.md`. Phase 2 deliverables (billing/workflow detectors, TypeScript parser, deduplication, feedback endpoint) are already scaffolded in `plugins/` and `src/companion/`.
