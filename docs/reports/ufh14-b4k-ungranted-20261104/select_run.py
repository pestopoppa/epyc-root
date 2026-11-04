#!/usr/bin/env python3
"""Scratch-only exact run selector. Requires COMPLETE and grant-bound timestamps."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def select_run(root: Path, complete_path: Path, grant_path: Path) -> Path:
    root = root.resolve()
    complete = json.loads(complete_path.read_text())
    grant = json.loads(grant_path.read_text())
    required = {"id", "granted_at", "ended_at"}
    if not required.issubset(grant):
        raise ValueError("grant missing id/granted_at/ended_at")
    if complete.get("grant_id") != grant["id"]:
        raise ValueError("COMPLETE grant_id does not match grant")
    if complete.get("grant_started_at") != grant["granted_at"]:
        raise ValueError("COMPLETE grant start does not match grant")
    run = Path(complete.get("run", "")).resolve()
    runs_root = (root / "out/runs").resolve()
    if run.parent != runs_root or not run.is_dir():
        raise ValueError("COMPLETE run is not an existing direct child of out/runs")
    try:
        run_started = datetime.strptime(run.name, "%Y%m%dT%H%M%SZ").replace(tzinfo=ts(grant["granted_at"]).tzinfo)
    except ValueError as exc:
        raise ValueError("run directory lacks canonical UTC timestamp") from exc
    if not (ts(grant["granted_at"]) <= run_started <= ts(grant["ended_at"])):
        raise ValueError("run timestamp is outside grant window")
    candidates = []
    for path in runs_root.iterdir():
        if not path.is_dir() or not (path / "calls.jsonl").is_file():
            continue
        try:
            t = datetime.strptime(path.name, "%Y%m%dT%H%M%SZ").replace(tzinfo=run_started.tzinfo)
        except ValueError:
            continue
        if ts(grant["granted_at"]) <= t <= ts(grant["ended_at"]):
            candidates.append(path.resolve())
    if candidates != [run]:
        raise ValueError("grant window does not identify exactly the COMPLETE run")
    return run
