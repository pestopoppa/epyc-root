"""VB-TOC-AB-WRITE: tool-output-compression A/B arms as a prospective measurement source.

Write side (:func:`write_belief_measurements`) is called by the trajectory-artifact writer at its
native finalize boundary (event schema: ``tool-output-compression.md`` TOC-SP-6 / A/B-COST /
A/B-TRIG). One self-hashed row per run x arm. The strict reader (:func:`native_rows` /
:func:`project`) reopens every hash, re-derives the solve rate and the cost totals from the
per-task records, and projects to the existing measurement ``ClaimTuple``;
``claim_tuple.grade()`` decides. No retrospective tuple (a run with no sidecar emits zero rows),
no ladder.

Schema as filed (the producer lives in epyc-orchestrator and is edited by another session; this
module is written against the FILED event fields, not against that code): per task
``terminal_state`` in {finished, context-exhausted, turn-exhausted, killed}, ``solved``,
``turns``, ``rolling_input_tokens`` (SUM over turns, not final context), ``prefix_cache_invalidations``,
``compressor_wall_s``; per arm ``policy_digest``, ``trigger_fraction`` and its
``window_denominator`` (named), ``summary_placement``.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.toc_ab_capture.v1"
SIDECAR_NAME = "toc_ab.beliefs.jsonl"
METRIC = "toc_ab_task_solve_rate"
UNIT = "fraction_solved"
ADAPTER_ID = "vidya.adapters.toc_ab/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "toc-ab-measurement"
TERMINAL_STATES = frozenset({"finished", "context-exhausted", "turn-exhausted", "killed"})
PLACEMENTS = frozenset({"top", "tail", "none"})
TASK_INT_FIELDS = ("turns", "rolling_input_tokens", "prefix_cache_invalidations")


def _task_problems(tasks: Any) -> list[str]:
    if not isinstance(tasks, list) or not tasks:
        return ["extra.tasks must be a non-empty list of per-task records"]
    p: list[str] = []
    seen: set[str] = set()
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            p.append(f"tasks[{i}] is not an object")
            continue
        if not ns.text(t.get("task_id")) or t["task_id"] in seen:
            p.append(f"tasks[{i}].task_id must be a unique non-empty string")
        seen.add(str(t.get("task_id")))
        if t.get("terminal_state") not in TERMINAL_STATES:
            p.append(f"tasks[{i}].terminal_state must be one of {sorted(TERMINAL_STATES)}")
        if not isinstance(t.get("solved"), bool):
            p.append(f"tasks[{i}].solved must be a boolean")
        for key in TASK_INT_FIELDS:
            if not ns.nonneg_int(t.get(key)):
                p.append(f"tasks[{i}].{key} must be a non-negative integer")
        if not ns.finite(t.get("compressor_wall_s")) or t.get("compressor_wall_s", -1) < 0:
            p.append(f"tasks[{i}].compressor_wall_s must be a non-negative number")
    return p


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("metric") != METRIC:
        p.append(f"metric must be {METRIC!r}")
    for key in ("arm_label", "window_denominator"):
        if not ns.text(e.get(key)):
            p.append(f"extra.{key} must be a non-empty string (name the denominator)")
    if not ns.SHA256.match(str(e.get("policy_digest", ""))):
        p.append("extra.policy_digest must be a 64-hex digest of the compression policy")
    tf = e.get("trigger_fraction")
    if tf is not None and not (ns.finite(tf) and 0 < tf <= 1):
        p.append("extra.trigger_fraction must be in (0, 1] or null for a no-compression arm")
    if e.get("summary_placement") not in PLACEMENTS:
        p.append(f"extra.summary_placement must be one of {sorted(PLACEMENTS)}")
    if not isinstance(e.get("is_control"), bool):
        p.append("extra.is_control must be a boolean")
    else:
        want = "BASELINE" if e["is_control"] else "CANDIDATE"
        if row.get("category") != want:
            p.append(f"category must be {want} for is_control={e['is_control']}")
    tp = _task_problems(e.get("tasks"))
    p += tp
    if not tp:
        tasks = e["tasks"]
        n = len(tasks)
        solved = sum(t["solved"] for t in tasks)
        if e.get("n_tasks") != n or e.get("solved") != solved:
            p.append("extra.n_tasks / extra.solved do not match the per-task records")
        if ns.finite(row.get("value")) and abs(row["value"] - solved / n) > 1e-12:
            p.append("value must equal solved / n_tasks")
        if row.get("reps") != n:
            p.append("reps must equal the number of tasks")
        if row.get("reps_basis") != "scored:tasks":
            p.append("reps_basis must be 'scored:tasks'")
        for key in TASK_INT_FIELDS:
            if e.get(f"total_{key}") != sum(t[key] for t in tasks):
                p.append(f"extra.total_{key} does not re-derive from the per-task records")
        if not ns.finite(e.get("total_compressor_wall_s")) or abs(
                e["total_compressor_wall_s"] - sum(t["compressor_wall_s"] for t in tasks)) > 1e-9:
            p.append("extra.total_compressor_wall_s does not re-derive from the per-task records")
    if not p:
        p += ns.check_identity(row, {
            "run_id": row["run_id"], "arm": e["arm_label"], "policy": e["policy_digest"],
            "trigger": e["trigger_fraction"], "den": e["window_denominator"],
            "results": row["results_sha256"]}, "tocab")
    return p + ns.self_hash_problems(row) if isinstance(row, dict) else p


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, trajectory_path: str | Path,
    arms: Mapping[str, Mapping[str, Any]], protocol_id: str = "",
    emitted_at: str | None = None,
) -> Path:
    """Emit ``toc_ab.beliefs.jsonl`` at the trajectory writer's finalize boundary.

    ``arms`` maps arm label -> ``{policy_digest, trigger_fraction|None, window_denominator,
    summary_placement, is_control, tasks:[{task_id, terminal_state, solved, turns,
    rolling_input_tokens, prefix_cache_invalidations, compressor_wall_s}]}``.
    ``trajectory_path`` is the chronological trajectory artifact the rows attest (re-hashed on
    read). Any problem raises :class:`CaptureError`; nothing is written. Never backfills.
    """
    trajectory = Path(trajectory_path)
    if not trajectory.is_file():
        raise CaptureError(f"trajectory artifact missing: {trajectory}")
    if not arms:
        raise CaptureError("at least one arm is required")
    digest = ns.file_sha256(trajectory)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for label, a in arms.items():
        tasks = [dict(t) for t in a.get("tasks", [])]
        problems = _task_problems(tasks)
        if problems:
            raise CaptureError(f"arm {label!r}: " + "; ".join(problems))
        n, solved = len(tasks), sum(t["solved"] for t in tasks)
        extra = {
            "arm_label": label, "policy_digest": a.get("policy_digest"),
            "trigger_fraction": a.get("trigger_fraction"),
            "window_denominator": a.get("window_denominator"),
            "summary_placement": a.get("summary_placement"), "is_control": a.get("is_control"),
            "n_tasks": n, "solved": solved, "tasks": tasks,
            "total_compressor_wall_s": sum(t["compressor_wall_s"] for t in tasks),
            **{f"total_{k}": sum(t[k] for t in tasks) for k in TASK_INT_FIELDS},
        }
        row = {
            "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
            "emitted_at": when, "date": when[:10],
            "metric": METRIC, "value": solved / n, "unit": UNIT,
            "metric_direction": "higher_better",
            "category": "BASELINE" if a.get("is_control") else "CANDIDATE",
            "claim": f"TOC A/B {run_id}: arm {label} solved {solved}/{n} tasks",
            "protocol_id": protocol_id, "reps": n, "reps_basis": "scored:tasks",
            "results_path": str(trajectory), "results_sha256": digest, "extra": extra,
        }
        if not problems:
            row["measurement_id"] = "tocab_" + ns.content_hash({
                "run_id": run_id, "arm": label, "policy": extra["policy_digest"],
                "trigger": extra["trigger_fraction"], "den": extra["window_denominator"],
                "results": digest})[:24]
        ns.seal(row)
        bad = validate_row(row)
        if bad:
            raise CaptureError(f"arm {label!r}: refusing to emit an invalid row: " + "; ".join(bad))
        rows.append(row)
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("TOC A/B native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("TOC A/B row is not a producer-authored capture: " + "; ".join(problems))
    locator = f"toc-ab:{row['run_id']}:{row['extra']['arm_label']}:{row['results_path']}"
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""),
                             no_protocol_ids=("observation:none",), legacy_schema_protocol=True)


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
