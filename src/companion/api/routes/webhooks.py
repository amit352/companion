"""
Phase 6 — GitHub webhook integration.

When a push is made to a registered repo, Companion:
  1. Verifies the HMAC-SHA256 signature
  2. Extracts changed source files from the push payload
  3. Spawns an incremental analysis on those files only
  4. Updates the graph without re-scanning unchanged files

Setup:
  1. Set GITHUB_WEBHOOK_SECRET in .env
  2. Add a repo→path mapping in GITHUB_REPO_PATHS (JSON env var)
  3. In GitHub repo settings → Webhooks:
       Payload URL : https://<your-host>/api/v1/webhooks/github
       Content type: application/json
       Events      : Just the push event
       Secret      : same as GITHUB_WEBHOOK_SECRET
"""
import hashlib
import hmac
import json
import os
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".rb", ".java", ".go", ".rs"}


def _verify_signature(payload: bytes, sig_header: str | None) -> None:
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        return  # no secret configured — skip verification (dev mode)
    if not sig_header or not sig_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256")
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


def _repo_paths() -> dict[str, str]:
    """Read GITHUB_REPO_PATHS env var: '{"owner/repo": "/local/path"}'"""
    raw = os.environ.get("GITHUB_REPO_PATHS", "{}")
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _changed_source_files(commits: list[dict]) -> list[str]:
    changed = set()
    for commit in commits:
        for f in commit.get("added", []) + commit.get("modified", []):
            if Path(f).suffix in SOURCE_EXTENSIONS:
                changed.add(f)
    return list(changed)


def _removed_files(commits: list[dict]) -> list[str]:
    removed = set()
    for commit in commits:
        for f in commit.get("removed", []):
            if Path(f).suffix in SOURCE_EXTENSIONS:
                removed.add(f)
    return list(removed)


class WebhookResponse(BaseModel):
    status:        str
    repo:          str
    changed_files: int
    job_id:        str | None = None
    message:       str = ""


@router.post("/github", response_model=WebhookResponse)
async def github_webhook(
    request: Request,
    x_github_event: str    = Header(default="push"),
    x_hub_signature_256: str | None = Header(default=None),
) -> WebhookResponse:
    payload = await request.body()
    _verify_signature(payload, x_hub_signature_256)

    if x_github_event == "ping":
        return WebhookResponse(status="ok", repo="", changed_files=0, message="pong")

    if x_github_event != "push":
        return WebhookResponse(status="skipped", repo="", changed_files=0,
                               message=f"Ignoring event: {x_github_event}")

    data       = json.loads(payload)
    repo_name  = data.get("repository", {}).get("full_name", "")
    commits    = data.get("commits", [])
    ref        = data.get("ref", "")

    # Only process pushes to default branch
    default_branch = data.get("repository", {}).get("default_branch", "main")
    if ref != f"refs/heads/{default_branch}":
        return WebhookResponse(status="skipped", repo=repo_name, changed_files=0,
                               message=f"Push to non-default branch {ref}")

    changed = _changed_source_files(commits)
    removed = _removed_files(commits)

    if not changed and not removed:
        return WebhookResponse(status="no_change", repo=repo_name, changed_files=0,
                               message="No source file changes detected")

    # Resolve local path for this repo
    repo_paths  = _repo_paths()
    local_path  = repo_paths.get(repo_name)

    if not local_path or not Path(local_path).exists():
        return WebhookResponse(
            status="unregistered", repo=repo_name, changed_files=len(changed),
            message=(
                f"Repo '{repo_name}' not registered. "
                f"Add to GITHUB_REPO_PATHS env var: "
                f"'{{\"{repo_name}\": \"/local/path\"}}'"
            ),
        )

    engine = request.app.state.engine

    # Queue incremental analysis
    job_id = await engine.analyze_repository(Path(local_path), incremental=True)

    import structlog
    structlog.get_logger().info(
        "webhook_triggered",
        repo=repo_name, changed=len(changed), removed=len(removed), job_id=job_id
    )

    return WebhookResponse(
        status="queued",
        repo=repo_name,
        changed_files=len(changed),
        job_id=job_id,
        message=f"{len(changed)} changed, {len(removed)} removed — incremental analysis started",
    )


@router.get("/github/status")
async def webhook_status() -> dict:
    """Check webhook configuration status."""
    has_secret = bool(os.environ.get("GITHUB_WEBHOOK_SECRET"))
    repo_paths = _repo_paths()
    return {
        "signature_verification": has_secret,
        "registered_repos": list(repo_paths.keys()),
        "setup_instructions": {
            "1_env_vars": {
                "GITHUB_WEBHOOK_SECRET": "any secure random string",
                "GITHUB_REPO_PATHS": '{"owner/repo-name": "/absolute/local/path"}',
            },
            "2_github_settings": {
                "url":          "https://<host>/api/v1/webhooks/github",
                "content_type": "application/json",
                "events":       ["push"],
                "secret":       "same as GITHUB_WEBHOOK_SECRET",
            },
            "3_expose_localhost": "ngrok http 8000  (for local development)",
        },
    }
