"""Minimal freshness classifier for the handoff dashboard.

A deliberately tiny, local equivalent of the orchestrator dashboard's freshness
contract — just enough to badge the git-derived timeline artifact so a dead
regeneration hook is visible rather than silently serving stale data. The board
itself is a live per-request scan and is fresh by construction.
"""

from __future__ import annotations

import time
from pathlib import Path

# fresh  : advanced within warn_s
# aging  : older than warn_s but within stale_s
# stale  : exists but older than stale_s (regeneration likely broken)
# missing: file absent (never generated / fresh checkout)
CLASSES = ("fresh", "aging", "stale", "missing")


def classify(path: Path, warn_s: float, stale_s: float, *, now: float | None = None) -> dict:
    """Return ``{staleness_class, age_s, mtime}`` for ``path``."""
    now = time.time() if now is None else now
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {"staleness_class": "missing", "age_s": None, "mtime": None}
    age = max(0.0, now - mtime)
    if age <= warn_s:
        cls = "fresh"
    elif age <= stale_s:
        cls = "aging"
    else:
        cls = "stale"
    return {"staleness_class": cls, "age_s": round(age, 1), "mtime": round(mtime, 3)}
