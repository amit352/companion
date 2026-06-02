Analyze a code repository and populate the Companion knowledge graph.

Usage: /companion <repo-path> [--api-url http://localhost:8000]

Runs entirely inside the Claude Code session — no ANTHROPIC_API_KEY required.
Uses Claude Code agents to extract features, then posts to the Companion API.

---

Parse $ARGUMENTS:
- First token = repo path (required)
- `--api-url` option (default: http://localhost:8000)

Set REPO_PATH and API_URL, then execute the following steps.

---

## Step 1 — Scan

Use Bash to count and list source files in REPO_PATH:

```bash
find "$REPO_PATH" \
  -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" \
           -o -name "*.rb" -o -name "*.java" -o -name "*.go" -o -name "*.rs" \) \
  ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/vendor/*" \
  ! -path "*/dist/*" ! -path "*/build/*" ! -path "*/__pycache__/*" \
  | head -300
```

Report: total file count and language breakdown.

---

## Step 2 — Extract features (parallel agents)

Group files by domain keyword in their path/name, then spawn 3 parallel sub-agents.
Each agent reads up to 15 files and returns structured JSON.

**Agent prompt (use for each batch):**

```
You are a code intelligence expert analyzing source files for the Companion platform.

Repository: [REPO_PATH]
Files to analyze: [list of file paths]

Read each file. Identify concrete business features — capabilities the code implements.

Return ONLY valid JSON:
{
  "features": [
    {
      "name": "specific feature name (e.g. 'Invoice File Upload', not just 'Upload')",
      "description": "one sentence: what business capability this represents",
      "domain": "one of: auth|billing|workflow|data|api|ui|infra",
      "confidence": 0.75-1.0,
      "source_files": ["relative/path/from/repo/root.ext"],
      "tags": ["relevant", "tags"]
    }
  ],
  "relationships": [
    {"source_id": "Feature Name A", "target_id": "Feature Name B", "kind": "depends_on"}
  ]
}

Rules:
- Minimum confidence 0.75 — skip anything uncertain
- Be specific: "Stripe Payment Processing" not "Payment"
- One feature can span multiple files
- Return empty arrays if no clear business features found
```

Agent groupings:
- Agent 1: auth, user, session, login, entitle, permission files
- Agent 2: billing, payment, invoice, fee, deposit, reconcil files
- Agent 3: workflow, process, schedule, notification, program, offer files

---

## Step 3 — Merge and deduplicate

Collect all agent responses. For features with the same or very similar names:
- Keep the one with higher confidence
- Union their tags and source_files

---

## Step 4 — Ingest to Companion API

POST the merged features:

```bash
curl -s -X POST "$API_URL/api/v1/analysis/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "REPO_PATH",
    "features": [...],
    "relationships": [...]
  }'
```

---

## Step 5 — Report

Print a summary table:
| Domain   | Features |
|----------|----------|
| auth     | N        |
| billing  | N        |
| ...      | ...      |
| **Total**| **N**    |

End with: "Graph updated → open http://localhost:3000 to explore"
