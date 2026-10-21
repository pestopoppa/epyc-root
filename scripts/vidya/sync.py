"""Keep the canonical ledger current with research/intake_index.yaml (2026-10-21).

`sync` is the one entry point every trigger calls: the post-commit/post-merge safety net, the
intake skill's persistence step, `index_state.citation_check()` and the wrap-up freshness CHECK.

Freshness is decided by a sidecar `<ledger>.sync.json` that records the sha256 of every index
revision already folded in (not just the last, so worktrees on different branches whose indexes
differ do not ping-pong re-ingests). Ingest itself is the existing content-addressed, dedup-keyed
`ingest_intake_index`, so a re-run never duplicates frames or rewrites history; the sync only
ever APPENDS to the existing chain.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ledger import Ledger  # noqa: E402
from ledger_home import REPO_ROOT  # noqa: E402

KEEP_SHAS = 40
FETCH_TIMEOUT = 60
INDEX_REL = "research/intake_index.yaml"
_ID_RE = re.compile(r"^- id: intake-(\d+)", re.M)


def marker_path(ledger_path: Path) -> Path:
    return Path(str(ledger_path) + ".sync.json")


def _read_marker(ledger_path: Path) -> dict:
    try:
        return json.loads(marker_path(ledger_path).read_text())
    except (OSError, ValueError):
        return {}


def load_index(index_path: Path | None = None, *, from_worktree: bool = False, fetch: bool = True,
               repo: Path = REPO_ROOT) -> tuple[bytes, str]:
    """Return (index bytes, source note).

    DEFAULT source is merged truth: `git fetch -q origin` then `git show origin/main:<index>`, so
    every freshness check converges regardless of cwd or how far this checkout lags. If the fetch
    fails the last-fetched origin/main is used and the note says so. An explicit `index_path` or
    `from_worktree=True` reads the local file (tests, Stage-1 pre-merge previews).
    """
    if index_path is not None:
        return Path(index_path).read_bytes(), f"file:{index_path}"
    if from_worktree:
        return (repo / INDEX_REL).read_bytes(), f"worktree:{repo / INDEX_REL}"
    note = "origin/main"
    if fetch:
        try:
            r = subprocess.run(["git", "fetch", "-q", "origin"], cwd=repo, capture_output=True,
                               text=True, timeout=FETCH_TIMEOUT)
            if r.returncode != 0:
                note = "origin/main (fetch FAILED, using last-fetched ref)"
        except (subprocess.TimeoutExpired, OSError):
            note = "origin/main (fetch FAILED, using last-fetched ref)"
    r = subprocess.run(["git", "show", f"origin/main:{INDEX_REL}"], cwd=repo, capture_output=True,
                       timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"cannot read origin/main:{INDEX_REL}: {r.stderr.decode()[:200]}")
    return r.stdout, note


def _facts(data: bytes) -> tuple[str, int, int]:
    ids = [int(m) for m in _ID_RE.findall(data.decode("utf-8", "replace"))]
    return hashlib.sha256(data).hexdigest(), len(ids), (max(ids) if ids else 0)


def status(ledger_path: Path, index_path: Path | None = None, *, from_worktree: bool = False,
           fetch: bool = True, _loaded: tuple[bytes, str] | None = None) -> dict:
    """Cheap freshness report (no ledger parse). Source: origin/main unless told otherwise."""
    data, note = _loaded or load_index(index_path, from_worktree=from_worktree, fetch=fetch)
    ledger_path = Path(ledger_path)
    sha, n_entries, max_id = _facts(data)
    marker = _read_marker(ledger_path)
    seen = marker.get("seen_sha256") or []
    exists = ledger_path.exists()
    fresh = exists and sha in seen
    return {
        "ledger": str(ledger_path),
        "ledger_exists": exists,
        "ledger_mtime": (datetime.fromtimestamp(ledger_path.stat().st_mtime, timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ") if exists else None),
        "index": note,
        "index_sha256": sha,
        "index_entries": n_entries,
        "index_max_id": max_id,
        "synced_max_id": marker.get("max_id"),
        "lag_entries": (max_id - (marker.get("max_id") or 0)) if not fresh else 0,
        "last_sync": marker.get("synced_at"),
        "fresh": bool(fresh),
    }


def sync(ledger_path: Path, index_path: Path | None = None, *, as_of: str | None = None,
         force: bool = False, from_worktree: bool = False, fetch: bool = True) -> dict:
    """Fold the current (origin/main by default) intake index into the ledger if not yet folded."""
    from adapters.research_intake import ingest_intake_index  # noqa: PLC0415

    ledger_path = Path(ledger_path)
    loaded = load_index(index_path, from_worktree=from_worktree, fetch=fetch)
    st = status(ledger_path, _loaded=loaded)
    if st["fresh"] and not force:
        return {**st, "action": "skipped-fresh", "frames_emitted": 0}
    data, _note = loaded
    led = Ledger(ledger_path)
    t0 = time.monotonic()
    with led.write_lock():
        st = status(ledger_path, _loaded=loaded)  # another writer may have synced while we waited
        if st["fresh"] and not force:
            return {**st, "action": "skipped-fresh-after-wait", "frames_emitted": 0}
        stamp = as_of or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with tempfile.NamedTemporaryFile("wb", suffix=".yaml", delete=False) as tf:
            tf.write(data)
        try:
            report = ingest_intake_index(led, index_path=Path(tf.name), as_of=stamp)
        finally:
            os.unlink(tf.name)
        sha, n_entries, max_id = _facts(data)
        marker = _read_marker(ledger_path)
        seen = [x for x in (marker.get("seen_sha256") or []) if x != sha] + [sha]
        new = {"seen_sha256": seen[-KEEP_SHAS:], "max_id": max(max_id, marker.get("max_id") or 0),
               "synced_at": stamp, "index_entries": n_entries, "source": _note}
        tmp = marker_path(ledger_path).with_suffix(".json.tmp")
        tmp.write_text(json.dumps(new, indent=1, sort_keys=True))
        os.replace(tmp, marker_path(ledger_path))
    return {**status(ledger_path, _loaded=loaded), "action": "ingested",
            "frames_emitted": report["frames_emitted"], "entries_read": report["entries_read"],
            "seconds": round(time.monotonic() - t0, 1)}
