"""
Feature deduplication across multiple extractor outputs (Phase 2).

Strategy:
  1. Exact name match — drop duplicates keeping highest confidence
  2. Fuzzy name match — merge features whose lowercased names share ≥80% token overlap
  3. Same source_files — collapse features that point to identical file sets

The merger preserves the highest-confidence version and unions tags/source_files.
"""
from __future__ import annotations

from typing import Any


def _token_overlap(a: str, b: str) -> float:
    """Jaccard overlap, treating abbreviation prefix matches as equal (auth ≈ authentication)."""
    ta = set(a.lower().split())
    tb = set(b.lower().split())
    if not ta or not tb:
        return 0.0

    # Count a token as matching if it's a prefix of a token in the other set or vice versa
    matched = set()
    for t in ta:
        for u in tb:
            if t == u or t.startswith(u) or u.startswith(t):
                matched.add(t)
                break

    return len(matched) / len(ta | tb)


def deduplicate(features: list[dict[str, Any]], threshold: float = 0.65) -> list[dict[str, Any]]:
    """
    Merge near-duplicate features from multiple extractor outputs.
    Returns a de-duplicated list sorted by confidence descending.
    """
    if not features:
        return []

    # Sort descending by confidence so we always keep the higher-confidence version
    sorted_features = sorted(features, key=lambda f: f.get("confidence", 0.0), reverse=True)
    merged: list[dict[str, Any]] = []

    for candidate in sorted_features:
        match = _find_match(candidate, merged, threshold)
        if match is None:
            merged.append(dict(candidate))
        else:
            _merge_into(match, candidate)

    return merged


def _find_match(
    candidate: dict[str, Any],
    existing: list[dict[str, Any]],
    threshold: float,
) -> dict[str, Any] | None:
    cname = candidate.get("name", "")

    for feat in existing:
        fname = feat.get("name", "")
        # Exact match (case-insensitive)
        if cname.lower() == fname.lower():
            return feat
        # Fuzzy token overlap
        if _token_overlap(cname, fname) >= threshold:
            return feat
        # Same source files
        c_files = set(candidate.get("source_files", []))
        f_files = set(feat.get("source_files", []))
        if c_files and f_files and c_files == f_files and candidate.get("domain") == feat.get("domain"):
            return feat

    return None


def _merge_into(target: dict[str, Any], source: dict[str, Any]) -> None:
    """Merge source into target in-place, unioning lists and keeping best confidence."""
    # Keep the higher-confidence name/description (target already has the better one since sorted)
    target["tags"] = list(set(target.get("tags", []) + source.get("tags", [])))
    target["source_files"] = list(set(target.get("source_files", []) + source.get("source_files", [])))
    # Boost confidence slightly when multiple extractors agree
    target["confidence"] = min(1.0, target.get("confidence", 0.0) + 0.05)
