"""Read the AutoPilot EvalTower's append-only per-question sidecars.

This is a read-only view of the producer-owned JSONL contract in
``scripts/autopilot/eval_tower.py``. It deliberately consumes completed
``eval_batch_id`` batches only and never derives categories from error text.
"""
from __future__ import annotations

import json
import math
import os
import re
import stat
from pathlib import Path
from typing import Any


DEFAULT_ARTIFACT_ROOT = Path("/mnt/raid0/llm/tmp/eval_tower_trials")
ARTIFACT_ROOT_ENV = "AUTOPILOT_EVAL_ARTIFACT_ROOT"
SCHEMA_VERSION = 1
MAX_REPORT_FILES = 512
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_ROWS_PER_FILE = 100_000
_TRIAL_DIR_RE = re.compile(r"^trial_(?:[0-9]+|unknown)$")
_DISPOSITIONS = {"scored", "task_failed", "infra_failed", "scoring_failed"}


def artifact_root() -> Path:
    """Resolve the same optional root override used by EvalTower."""
    value = os.environ.get(ARTIFACT_ROOT_ENV, "").strip()
    return Path(value).expanduser() if value else DEFAULT_ARTIFACT_ROOT


def _empty(path: Path, *, status: str, detail: str) -> dict[str, Any]:
    return {
        "schema": "epyc.dashboard.autopilot_eval_errors.v1",
        "status": status,
        "artifact": str(path),
        "batch": None,
        "counts": None,
        "error": detail,
    }


def _read_file(path: Path, root: Path) -> list[dict[str, Any]]:
    resolved_root = root.resolve(strict=True)
    resolved_path = path.resolve(strict=True)
    if resolved_root not in resolved_path.parents:
        raise ValueError("report path escapes configured artifact root")
    size = resolved_path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValueError(f"report exceeds {MAX_FILE_BYTES} byte reader limit")
    rows: list[dict[str, Any]] = []
    with resolved_path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line_number > MAX_ROWS_PER_FILE:
                raise ValueError(f"report exceeds {MAX_ROWS_PER_FILE} row reader limit")
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, UnicodeError) as exc:
                raise ValueError(f"malformed JSONL row {line_number}") from exc
            if (not isinstance(row, dict)
                    or isinstance(row.get("schema_version"), bool)
                    or row.get("schema_version") != SCHEMA_VERSION):
                raise ValueError(f"unsupported producer row at line {line_number}")
            rows.append(row)
    return rows


def _batch_projection(batch_id: str, batch: dict[str, Any]) -> dict[str, Any] | None:
    start = batch.get("start")
    complete = batch.get("complete")
    results = batch.get("results")
    if (batch.get("start_count") != 1 or batch.get("complete_count") != 1
            or not isinstance(start, dict) or not isinstance(complete, dict)
            or complete.get("complete") is not True
            or start.get("complete") is not False):
        return None
    requested = start.get("requested_n")
    completed = complete.get("completed_n")
    if complete.get("requested_n") != requested:
        return None
    if (isinstance(requested, bool) or not isinstance(requested, int) or requested < 0
            or isinstance(completed, bool) or not isinstance(completed, int) or completed < 0
            or completed > requested or completed != len(results)):
        return None
    ordinals = [row.get("ordinal") for row in results]
    if any(isinstance(value, bool) or not isinstance(value, int)
           or value < 0 or value >= requested for value in ordinals):
        return None
    if len(set(ordinals)) != len(ordinals):
        return None
    for row in [*results, complete]:
        for key in ("eval_batch_id", "label", "trial_id", "requested_n"):
            left, right = row.get(key), start.get(key)
            if type(left) is not type(right) or left != right:
                return None

    counts = {
        "total": len(results),
        "non_error": 0,
        "error": 0,
        "scored_correct": 0,
        "scored_wrong": 0,
        "task_failed": 0,
        "infra_failed": 0,
        "scoring_failed": 0,
        "unclassified_error": 0,
    }
    timestamps: list[float] = []
    for row in results:
        result = row.get("result")
        ended_at = row.get("ended_at_s")
        if not isinstance(result, dict):
            return None
        if (isinstance(ended_at, bool) or not isinstance(ended_at, (int, float))
                or not math.isfinite(float(ended_at)) or float(ended_at) <= 0):
            return None
        timestamps.append(float(ended_at))

        error_value = result.get("error", False)
        if not isinstance(error_value, bool):
            return None
        counts["error" if error_value else "non_error"] += 1

        disposition = result.get("disposition", "scored")
        if not isinstance(disposition, str) or disposition not in _DISPOSITIONS:
            return None
        if disposition == "infra_failed":
            counts["infra_failed"] += 1
        elif disposition == "scoring_failed":
            counts["scoring_failed"] += 1
        elif disposition == "task_failed":
            counts["task_failed"] += 1
        elif error_value:
            # Legacy rows can record the producer's error flag without the
            # later disposition field. Keep the known error visible, but do
            # not guess whether infra or scoring caused it.
            counts["unclassified_error"] += 1
        elif result.get("correct") is True:
            counts["scored_correct"] += 1
        elif result.get("correct") is False:
            counts["scored_wrong"] += 1
        else:
            return None

    total = counts["total"]
    counts["excluded_error"] = (
        counts["infra_failed"] + counts["scoring_failed"] + counts["unclassified_error"]
    )
    counts["error_rate"] = counts["error"] / total if total else None
    counts["reliability"] = counts["non_error"] / total if total else None
    timestamp = max(timestamps) if timestamps else None
    label = start.get("label")
    trial_id = start.get("trial_id")
    return {
        "schema": "epyc.dashboard.autopilot_eval_errors.v1",
        "status": "reported" if total else "empty_batch",
        "artifact": None,
        "batch": {
            "eval_batch_id": batch_id,
            "label": str(label)[:120] if label is not None else None,
            "trial_id": trial_id,
            "requested": requested,
            "completed": completed,
            "ended_at_epoch": timestamp,
        },
        "attribution": "unattributed",
        "attribution_reason": (
            "the sidecar identifies an EvalTower batch but carries no signed "
            "source-control or live-production context"
        ),
        "counts": counts,
        "error": None,
    }


def read_latest(root: Path | None = None) -> dict[str, Any]:
    """Return the newest structurally complete EvalTower batch under ``root``.

    Mtime is never used as the report timestamp. A complete zero-row batch is
    explicitly empty and has unknown age because the producer writes no semantic
    timestamp for that shape.
    """
    root = artifact_root() if root is None else Path(root).expanduser()
    try:
        root_stat = root.stat()
    except FileNotFoundError:
        return _empty(root, status="missing", detail="EvalTower artifact root is absent")
    except OSError as exc:
        return _empty(root, status="unreadable", detail=f"artifact root unreadable: {exc}")
    if not stat.S_ISDIR(root_stat.st_mode):
        return _empty(root, status="unreadable", detail="EvalTower artifact root is not a directory")

    try:
        files = []
        for child in root.iterdir():
            if not _TRIAL_DIR_RE.fullmatch(child.name):
                continue
            candidate = child / "question_results.jsonl"
            try:
                candidate.lstat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise ValueError(f"report path is unreadable: {candidate}") from exc
            else:
                files.append(candidate)
        if len(files) > MAX_REPORT_FILES:
            return _empty(root, status="unreadable",
                          detail=f"artifact root exceeds {MAX_REPORT_FILES} report files")
        batches: list[dict[str, Any]] = []
        saw_rows = False
        for path in files:
            rows = _read_file(path, root)
            by_id: dict[str, dict[str, Any]] = {}
            for row in rows:
                row_type = row.get("row_type")
                batch_id = row.get("eval_batch_id")
                if not isinstance(batch_id, str) or not batch_id:
                    raise ValueError("producer row is missing eval_batch_id")
                batch = by_id.setdefault(batch_id, {
                    "results": [], "start_count": 0, "complete_count": 0,
                })
                if row_type == "batch_start":
                    batch["start_count"] += 1
                    batch["start"] = row
                elif row_type == "question_result":
                    batch["results"].append(row)
                elif row_type == "batch_complete":
                    batch["complete_count"] += 1
                    batch["complete"] = row
                else:
                    raise ValueError(f"unsupported producer row_type {row_type!r}")
            saw_rows = saw_rows or bool(rows)
            for batch_id, batch in by_id.items():
                projection = _batch_projection(batch_id, batch)
                if projection is not None:
                    projection["artifact"] = str(path)
                    batches.append(projection)
        if not batches:
            status = "incomplete" if saw_rows else "missing"
            detail = ("no structurally complete eval batch is available" if saw_rows
                      else "no EvalTower question_results.jsonl report is available")
            return _empty(root, status=status, detail=detail)
        batches.sort(key=lambda item: (
            item["batch"]["ended_at_epoch"] if item["batch"]["ended_at_epoch"] is not None else -1,
            item["batch"]["eval_batch_id"],
        ))
        return batches[-1]
    except (OSError, UnicodeError, ValueError) as exc:
        return _empty(root, status="unreadable", detail=str(exc))
