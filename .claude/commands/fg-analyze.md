Analyze a code repository and populate the Companion knowledge graph with all SRS node types.

Usage: /companion <repo-path> [--api-url http://localhost:8000]

Runs entirely inside Claude Code — no ANTHROPIC_API_KEY required.
Extracts: Features, Services, APIs, DatabaseTables, UIComponents, Requirements.

---

Parse $ARGUMENTS:
- First token = repo path (REPO_PATH)
- `--api-url` = API base URL (default: http://localhost:8000)

---

## Step 1 — Scan

```bash
find "$REPO_PATH" -type f \
  \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" \
     -o -name "*.rb" -o -name "*.java" -o -name "*.go" -o -name "*.rs" \) \
  ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/vendor/*" \
  ! -path "*/dist/*" ! -path "*/build/*" ! -path "*/__pycache__/*" \
  | head -400
```

Report total files and language breakdown.

---

## Step 2 — Extract (3 parallel agents)

Spawn 3 parallel sub-agents. Each reads assigned files and returns JSON.

**Agent 1 — Features + Services:**
Read files from: auth, user, service, manager, controller, handler paths.

Return:
```json
{
  "features": [
    { "name": "...", "description": "...", "domain": "auth|billing|workflow|data|api",
      "confidence": 0.75-1.0, "source_files": ["..."], "tags": ["..."] }
  ],
  "services": [
    { "name": "...", "technology": "rails|django|express|...", "source_files": ["..."], "tags": ["..."] }
  ],
  "relationships": [
    { "source_id": "Feature Name", "target_id": "Service Name", "kind": "uses" }
  ]
}
```

**Agent 2 — APIs + DatabaseTables:**
Read files from: api, routes, endpoints, models, schema, migration, db paths.

Return:
```json
{
  "apis": [
    { "path": "/api/v1/...", "method": "GET|POST|PUT|DELETE", "service_name": "...",
      "source_files": ["..."], "auth_required": true }
  ],
  "database_tables": [
    { "name": "table_name", "database": "postgresql|mysql|mongodb",
      "engine": "postgresql", "source_files": ["..."] }
  ],
  "relationships": [
    { "source_id": "Service Name", "target_id": "table_name", "kind": "reads" }
  ]
}
```

**Agent 3 — UIComponents + cross-cutting Features:**
Read files from: components, pages, views, frontend, workflow, process paths.

Return:
```json
{
  "features": [
    { "name": "...", "description": "...", "domain": "...",
      "confidence": 0.75-1.0, "source_files": ["..."], "tags": ["..."] }
  ],
  "ui_components": [
    { "name": "ComponentName", "path": "src/components/...", "framework": "react|vue|angular",
      "source_files": ["..."] }
  ],
  "relationships": [
    { "source_id": "ComponentName", "target_id": "/api/v1/...", "kind": "calls" }
  ]
}
```

---

## Step 3 — Merge

Merge all agent results. Deduplicate features by name (keep highest confidence).

---

## Step 4 — Ingest

```bash
curl -s -X POST "$API_URL/api/v1/analysis/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "REPO_PATH",
    "repo_name": "REPO_NAME",
    "trigger": "manual",
    "features": [...],
    "services": [...],
    "apis": [...],
    "database_tables": [...],
    "ui_components": [...],
    "relationships": [...]
  }'
```

---

## Step 5 — Report

Show breakdown table:

| Node Type       | Count |
|-----------------|-------|
| Features        | N     |
| Services        | N     |
| APIs            | N     |
| Database Tables | N     |
| UI Components   | N     |
| **Total**       | **N** |

Relationships created: N

"Graph updated → http://localhost:3000"
