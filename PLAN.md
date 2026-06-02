# FeatureGraph — Phased Implementation Plan

## Overview

FeatureGraph converts software repositories into feature-centric knowledge graphs.
It combines Understand-Anything's proven multi-agent pipeline (tree-sitter + LLM)
with an enterprise plugin SDK as defined in the SRS.

**Success targets:**
- 90% dependency extraction accuracy (FR-4)
- 80% feature clustering accuracy (FR-7)
- 70% AI token reduction (Section 10)
- < 30 min initial index for 1M LOC (NFR-2)

---

## Phase 1 — Foundation (Weeks 1–3)
**Goal: Core engine + plugin SDK + single working parser**

### Deliverables
- [x] Core Engine (`CoreEngine`, `EventBus`, `JobScheduler`, `PluginManager`)
- [x] Plugin SDK base classes (all 6 plugin types)
- [x] Plugin registry + manifest loader (FR-1, FR-2)
- [x] Graph node/relationship models (Section 8–9)
- [x] Neo4j client with schema bootstrap
- [x] Python parser plugin (tree-sitter)
- [x] Six-agent analysis pipeline scaffold
- [x] Docker Compose (Neo4j + Postgres/pgvector + Redis)
- [ ] Unit tests for plugin lifecycle (registry, load, teardown)
- [ ] Integration test: scan a small Python repo end-to-end

### Acceptance Criteria
- `docker compose up` brings all services healthy
- `POST /api/v1/analysis/` with a local Python repo path completes without error
- Parsed features appear in Neo4j Browser

### Key Technical Decisions
- tree-sitter for deterministic parsing (same as Understand-Anything)
- Plugins load from `plugin.json` manifests — no core changes needed to add types (NFR-5)
- Neo4j for graph; pgvector for future semantic search

---

## Phase 2 — LLM Feature Extraction (Weeks 4–6)
**Goal: Claude-powered feature clustering at 80%+ accuracy**

### Deliverables
- [ ] `AuthFeatureDetector` plugin — complete and tested
- [ ] `BillingFeatureDetector` plugin
- [ ] `WorkflowDetector` plugin
- [ ] Feature deduplication across multiple extractor outputs
- [ ] Confidence scoring + human feedback loop endpoint (`POST /features/{id}/feedback`)
- [ ] TypeScript parser plugin (tree-sitter-typescript)
- [ ] Benchmark harness: run against 3 open-source repos, measure accuracy

### Acceptance Criteria
- Auth features detected with >80% precision on a FastAPI/Django sample repo
- Duplicate features merged; no same-name features in graph
- Confidence scores surfaced in the API

### Risks & Mitigations
- **LLM hallucinations** → graph-grounded retrieval; only accept features that reference ≥1 real symbol
- **Token overrun** → batch symbols in groups of 100; filter to domain keywords first

---

## Phase 3 — AI Compression Layer (Weeks 7–8)
**Goal: 70% token reduction target from Section 10**

### Deliverables
- [ ] `DefaultCompressor` plugin — production-ready
- [ ] Semantic clustering (group features by domain)
- [ ] Dependency summarization (longest-path reduction)
- [ ] Compression benchmark: measure raw vs compressed token counts on 5 repos
- [ ] `GET /api/v1/features/{id}/compressed-context` endpoint
- [ ] Query-biased compression (focus context on user question)

### Acceptance Criteria
- Compression ratio ≥ 0.70 on repos with ≥10 features
- AI chat answers correct on compressed context vs full context

---

## Phase 4 — Frontend Feature Explorer (Weeks 9–11)
**Goal: Interactive React Flow graph + AI chat**

### Deliverables
- [ ] Next.js app with React Flow visualization
- [ ] Force-directed layout with layer color-coding (api/service/data/ui/utility)
- [ ] Feature Detail Panel (files, confidence, tags, impact analysis)
- [ ] Impact analysis UI — "What breaks if X changes?" (FR-4, §11.2)
- [ ] AI Chat Interface with streaming (§11.2)
- [ ] Full-text + semantic graph search (FR-9)
- [ ] Dark mode, responsive layout

### Acceptance Criteria
- Graph renders 500+ nodes without performance degradation
- Impact analysis returns results in < 2s
- Chat streaming works with no layout shift

---

## Phase 5 — Documentation & Runtime Plugins (Weeks 12–14)
**Goal: Auto-generate SRS/ADR/API docs; map runtime traces to feature graph**

### Deliverables
- [ ] `SRSDocumentationPlugin` — generates SRS from graph (FR-10, §4.3)
- [ ] `ADRDocumentationPlugin` — generates Architecture Decision Records
- [ ] `APIDocsPlugin` — OpenAPI spec generation from API nodes
- [ ] `OpenTelemetryRuntimePlugin` — ingest OTLP traces, map to features
- [ ] `POST /api/v1/docs/generate` endpoint (outputs Markdown/PDF/HTML/JSON)
- [ ] Sequence diagram generation (Mermaid)
- [ ] Requirement traceability: link Requirement nodes to Feature nodes (§9)

### Acceptance Criteria
- SRS generated from a real repo matches human-written SRS at 70%+ structural similarity
- Runtime spans linked back to Feature nodes in Neo4j

---

## Phase 6 — Integration Plugins & Enterprise Scale (Weeks 15–18)
**Goal: External integrations, incremental indexing, 10M+ LOC performance**

### Deliverables
- [ ] `GitHubIntegrationPlugin` — webhook-driven incremental updates on commit (FR-6)
- [ ] `JiraIntegrationPlugin` — sync requirements from Jira tickets to Requirement nodes
- [ ] `SlackIntegrationPlugin` — post impact analysis alerts to Slack
- [ ] `Neo4jExportPlugin` — export full graph to external Neo4j instance
- [ ] Incremental indexing optimization — < 2 min for changed files (NFR-2)
- [ ] Redis job queue for distributed analysis (replaces in-process scheduler)
- [ ] Performance benchmarks: 1M LOC in < 30 min (NFR-2), 10M LOC scale test
- [ ] Plugin sandboxing via subprocess isolation (NFR-4, FR-3)
- [ ] RBAC / permission-scoped plugin access (NFR-4)

### Acceptance Criteria
- GitHub webhook triggers incremental analysis within 2 min of push
- Jira tickets appear as Requirement nodes linked to relevant Features
- 1M LOC Python repo indexed in < 30 minutes on standard hardware

---

## Phase 7 — Production Readiness (Weeks 19–20)
**Goal: 99.9% uptime target, security hardening, observability**

### Deliverables
- [ ] OpenTelemetry instrumentation on all API endpoints
- [ ] Jaeger trace dashboard integrated
- [ ] Health checks + readiness probes on all services
- [ ] Kubernetes Helm chart (HPA for analyzer workers)
- [ ] Plugin signing + verification (NFR-4)
- [ ] Rate limiting + API key auth on REST API
- [ ] Load test: 100 concurrent analysis jobs
- [ ] Runbook + operator documentation

### Acceptance Criteria
- p99 analysis latency < 30 min for 1M LOC
- Zero unauthorized plugin filesystem access (sandboxed subprocess)
- 99.9% uptime measured over 30-day soak test

---

## Architecture Overview

```
                    ┌──────────────────────────────────────────┐
                    │           Next.js Frontend               │
                    │   Feature Explorer   │   AI Chat         │
                    │   (React Flow)       │   (Streaming)     │
                    └──────────────┬───────────────────────────┘
                                   │ REST / SSE
                    ┌──────────────▼───────────────────────────┐
                    │           FastAPI Backend                │
                    │  /analysis  /features  /graph  /chat     │
                    └──────────────┬───────────────────────────┘
                                   │
              ┌────────────────────▼──────────────────────────┐
              │                Core Engine                    │
              │  EventBus  PluginManager  JobScheduler        │
              └──────┬─────────────┬──────────────────────────┘
                     │             │
          ┌──────────▼──┐    ┌─────▼──────────────────────┐
          │  6-Agent    │    │   Plugin Registry           │
          │  Pipeline   │    │   Parser | Extractor        │
          │  ─────────  │    │   DocGen | Compression      │
          │  Scanner    │    │   Runtime | Integration     │
          │  Analyzer   │    └────────────────────────────┘
          │  Extractor  │
          │  ArchLayer  │    ┌─────────────────────────────┐
          │  GraphBuild │───►│  Neo4j Knowledge Graph      │
          │  Compressor │    │  Feature→Service→API→DB     │
          └─────────────┘    └─────────────────────────────┘
                                       │
                             ┌─────────▼──────────┐
                             │  pgvector (embeds) │
                             │  Redis (job queue) │
                             └────────────────────┘
```

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Parser | tree-sitter | Deterministic; proven in Understand-Anything |
| Graph DB | Neo4j | Native graph traversal for impact analysis |
| LLM | Claude Sonnet 4.6 / Haiku | Feature extraction + compression |
| Plugin isolation | subprocess sandbox | NFR-4 security |
| Incremental updates | SHA256 file hashes | NFR-2 performance |
| Event bus | In-process async queue → Redis Streams (Phase 6) | Scale path |

## Dependency Graph (Phases)

```
Phase 1 (Foundation)
    └── Phase 2 (Feature Extraction)
            └── Phase 3 (Compression)
                    └── Phase 4 (Frontend)   ← can overlap Phase 3
    └── Phase 5 (Docs + Runtime)             ← can overlap Phase 3
    └── Phase 6 (Integrations + Scale)       ← after Phase 2
            └── Phase 7 (Production)
```
