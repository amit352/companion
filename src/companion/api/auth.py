"""
API key authentication — Phase 7 security baseline.

Set COMPANION_API_KEY in .env to enable. If unset, the API is open
(development mode). In production, always set a key.

Usage:
  curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/features/

The following paths are always public (no key required):
  GET  /health
  GET  /ready
  POST /api/v1/webhooks/github   (verified by webhook secret instead)
"""
import os
import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Public paths — never require a key
PUBLIC_PATHS = {"/health", "/ready", "/docs", "/openapi.json", "/redoc"}


def get_api_key(api_key: str | None = Security(_KEY_HEADER)) -> str | None:
    """
    FastAPI dependency. Returns the key if valid, raises 401 if invalid,
    or passes through if no key is configured (dev mode).
    """
    required = os.environ.get("COMPANION_API_KEY", "").strip()

    if not required:
        return None  # dev mode — no auth

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not secrets.compare_digest(api_key, required):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
