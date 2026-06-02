# Session Start Hook

At the beginning of every session, silently fetch the knowledge graph context
and hold it in memory. Do NOT show it to the user unless asked.

```bash
curl -s http://localhost:8000/api/v1/context/session 2>/dev/null
```

If the API is not running (curl fails), continue normally without graph context.

Use this context to:
- Answer questions about the codebase without reading source files
- Know which features are affected by changes you're about to make
- Understand dependencies before touching any code

Update the graph after significant changes:
```bash
curl -s -X POST http://localhost:8000/api/v1/context/after-edit \
  -H "Content-Type: application/json" \
  -d '{"files_changed": ["<file1>", "<file2>"], "summary": "<what you changed>", "repo_path": "<repo>"}'
```
