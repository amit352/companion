Analyze a code repository and populate the FeatureGraph knowledge graph.

Usage: /fg-analyze <repo-path> [--api-url http://localhost:8000]

This skill runs entirely inside the Claude Code session — no ANTHROPIC_API_KEY needed.
It replaces the direct-API extractor plugins with Claude Code agents.

---

## Step 1: Scan repository

Use Bash to discover source files in $ARGUMENTS:

```bash
find "$REPO_PATH" \
  -type f \
  \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.rb" -o -name "*.java" -o -name "*.go" \) \
  ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/__pycache__/*" \
  ! -path "*/dist/*" ! -path "*/build/*" ! -path "*/.next/*" \
  | head -300
```

Report: language breakdown, total file count.

---

## Step 2: Extract features (parallel agents)

Spawn three parallel sub-agents, each focused on a domain. Pass them batches of file paths (up to 30 files per agent). Each agent should:

1. Read each file using the Read tool
2. Identify business features it implements
3. Return structured JSON

**Agent prompt template:**
```
You are a code intelligence expert analyzing source files for business features.

Files to analyze: [list of file paths]
Repository: [repo path]

For each file, identify business features — concrete capabilities the code implements (e.g. "User Authentication", "Payment Processing", "Order Workflow").

Return ONLY valid JSON:
{
  "features": [
    {
      "name": "concise feature name",
      "description": "what business capability this represents",
      "domain": "auth|billing|workflow|data|api|ui|infra",
      "confidence": 0.7-1.0,
      "source_files": ["relative/path.ext"],
      "tags": ["relevant", "tags"]
    }
  ],
  "relationships": [
    {"source_id": "Feature Name A", "target_id": "Feature Name B", "kind": "depends_on"}
  ]
}

Rules:
- Only include features with confidence >= 0.7
- One feature can span multiple files
- Be specific: "Stripe Payment Processing" not just "Payment"
- Return empty arrays if no clear business features found
```

Spawn agents in parallel, one per domain group:
- Agent 1: auth, user management, permissions files
- Agent 2: billing, payment, subscription files  
- Agent 3: workflow, process, data, API files

---

## Step 3: Deduplicate and ingest

Collect all agent responses. Merge features with the same name (keep highest confidence, union tags).

POST to the FeatureGraph API:

```bash
curl -s -X POST "$API_URL/api/v1/analysis/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "$REPO_PATH",
    "features": [...merged features...],
    "relationships": [...merged relationships...]
  }'
```

---

## Step 4: Report

Show a summary table:
- Total features extracted
- Features by domain
- Job ID from the API
- Link: http://localhost:3000 to view the graph

---

## Execution

Parse $ARGUMENTS:
- First token = repo path
- `--api-url` option (default: http://localhost:8000)

Set REPO_PATH and API_URL from arguments, then execute steps 1-4.
