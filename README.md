# FeatureGraph

AI-native code intelligence platform that converts software repositories into feature-centric knowledge graphs.

## What it does

- Parses repositories with **tree-sitter** (deterministic, multi-language)
- Extracts **business features** from code using a 6-agent Claude pipeline
- Builds a **Neo4j knowledge graph**: Feature → Service → API → Database → UIComponent
- Compresses full repos to **~3K token AI contexts** (target: 70% reduction)
- Answers questions like *"What breaks if auth changes?"* via an AI chat interface

## Quick Start

```bash
# 1. Start infrastructure
docker compose up -d neo4j postgres redis

# 2. Install Python dependencies
pip install -e ".[dev]"

# 3. Set your Anthropic key
export ANTHROPIC_API_KEY=sk-ant-...

# 4. Start the API
uvicorn feature_graph.api.main:app --reload

# 5. Analyze a repository
curl -X POST http://localhost:8000/api/v1/analysis/ \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "/path/to/your/repo"}'

# 6. Start the frontend
cd frontend && npm install && npm run dev
# Open http://localhost:3000
```

## Architecture

```
Scanner → File Analyzer (parallel) → Feature Extractor → Architecture Analyzer
       → Graph Builder (Neo4j) → AI Compressor
```

6 specialized agents, each backed by a plugin. See [PLAN.md](PLAN.md) for the full architecture diagram.

## Plugin Types

| Type | Purpose | Example |
|---|---|---|
| `parser` | tree-sitter AST extraction | `python-parser`, `typescript-parser` |
| `feature-extractor` | Business feature detection via Claude | `auth-detector`, `billing-detector` |
| `documentation` | Generate SRS/ADR/API docs | `srs-generator` |
| `ai-compression` | Reduce tokens 70%+ | `default-compressor` |
| `runtime-analysis` | Map OTLP traces to features | `otel-runtime` |
| `integration` | Sync with GitHub/Jira/Slack | `github-integration` |

## Writing a Plugin

1. Create a directory with `plugin.json` and `plugin.py`
2. Extend the right base class (`ParserPlugin`, `FeaturePlugin`, etc.)
3. Expose a top-level `Plugin` class
4. Drop the directory in `plugins/` — auto-discovered on startup

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "plugin_type": "feature-extractor",
  "languages": [],
  "entrypoint": "./plugin.py"
}
```

```python
from feature_graph.sdk.base import FeaturePlugin, FeatureExtractionOutput

class Plugin(FeaturePlugin):
    async def extract_features(self, symbols, dependencies, source_context):
        ...
        return FeatureExtractionOutput(features=[...], relationships=[], ownership=[])
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI |
| Parser | tree-sitter |
| Graph DB | Neo4j 5 |
| Vector Store | pgvector |
| AI | Claude Sonnet 4.6 / Haiku 4.5 |
| Queue | Redis |
| Frontend | Next.js 15, React Flow |
| Tracing | OpenTelemetry + Jaeger |

## Implementation Phases

See [PLAN.md](PLAN.md) for the full 7-phase plan (20 weeks).

| Phase | Focus | Duration |
|---|---|---|
| 1 | Foundation — engine, SDK, Python parser | Weeks 1–3 |
| 2 | LLM feature extraction (80% accuracy target) | Weeks 4–6 |
| 3 | AI compression (70% token reduction) | Weeks 7–8 |
| 4 | Frontend — Feature Explorer + AI Chat | Weeks 9–11 |
| 5 | Documentation + Runtime plugins | Weeks 12–14 |
| 6 | Integrations + enterprise scale (10M LOC) | Weeks 15–18 |
| 7 | Production hardening, Kubernetes, 99.9% uptime | Weeks 19–20 |
