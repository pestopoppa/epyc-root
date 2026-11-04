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
import hashlib
import json
from dataclasses import replace
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


USAGE_FIELDS = ("backend_attempts", "cached_replays", "observed_input_calls", "observed_output_calls", "total_input_tokens", "total_output_tokens", "total_tokens")
UNKNOWN_USAGE = {"status": "unknown", **{key: None for key in USAGE_FIELDS}}


def _short_label(value: str) -> str:
    return value if len(value) <= 48 else value[:32] + "#" + hashlib.sha256(value.encode()).hexdigest()[:12]


def _usage(events: list, task_id: str) -> dict:
    """Re-derive the conservative producer selection from native events."""
    usages = [e for e in events if e.get("event") == "episode_usage"]
    finals = [e for e in events if e.get("event") == "final"]
    if (len(usages) != 1 or not finals or usages[0].get("task_id") != task_id
            or type(usages[0].get("graph_attempts")) is not int
            or usages[0].get("graph_attempts") != len(finals)
            or events.index(usages[0]) <= events.index(finals[-1])):
        return dict(UNKNOWN_USAGE)
    u = usages[0].get("usage")
    if (not isinstance(u, dict) or set(u) != {"status", *USAGE_FIELDS}
            or u.get("status") not in {"complete", "partial"}
            or not all(ns.nonneg_int(u.get(k)) and u[k] < 2**63 for k in USAGE_FIELDS[:4])
            or u["observed_input_calls"] > u["backend_attempts"]
            or u["observed_output_calls"] > u["backend_attempts"]):
        return dict(UNKNOWN_USAGE)
    for kind in ("input", "output"):
        complete = (u[f"observed_{kind}_calls"] == u["backend_attempts"]
                    and u["backend_attempts"] + u["cached_replays"] > 0)
        value = u[f"total_{kind}_tokens"]
        if not (ns.nonneg_int(value) and value < 2**63 if complete else value is None):
            return dict(UNKNOWN_USAGE)
    a, b = u["total_input_tokens"], u["total_output_tokens"]
    total = a + b if a is not None and b is not None else None
    if (total is not None and total >= 2**63) or u["total_tokens"] != total or u["status"] != ("complete" if total is not None else "partial"):
        return dict(UNKNOWN_USAGE)
    return dict(u)


def _native_task(row: dict, task: dict) -> bool:
    """Reopen the exact pinned bytes; the sidecar alone cannot warrant usage."""
    segment = task.get("trajectory_segment")
    if not isinstance(segment, dict) or set(segment) != {"offset", "length", "sha256"}:
        return False
    off, length = segment["offset"], segment["length"]
    if not ns.nonneg_int(off) or not ns.nonneg_int(length) or not length or not ns.SHA256.fullmatch(str(segment["sha256"])):
        return False
    try:
        with open(row["results_path"], "rb") as handle:
            handle.seek(off)
            body = handle.read(length)
        if len(body) != length or hashlib.sha256(body).hexdigest() != segment["sha256"]:
            return False
        events = [json.loads(line) for line in body.decode("utf-8").splitlines() if line.strip()]
        if (not body.endswith(b"\n") or not events or any(
                not isinstance(e, dict) or e.get("schema") != "epyc.orchestrator.trajectory_event.v1"
                or e.get("task_id") != task["task_id"] or type(e.get("seq")) is not int
                or e["seq"] != i for i, e in enumerate(events, 1))):
            return False
        finals = [e for e in events if e.get("event") == "final"]
        if len(finals) != 1:
            return False
        fin = finals[0]
        fields = ("terminal_state", "turns", "rolling_input_tokens", "prefix_cache_invalidations", "compressor_wall_s")
        if any(fin.get(k) != task.get(k) for k in fields):
            return False
        if fin.get("rolling_input_tokens_observed_turns") != fin.get("turns"):
            return False
        return _usage(events, task["task_id"]) == task["episode_usage"]
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        return False


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
        if "episode_usage" in t:
            u = t["episode_usage"]
            if not isinstance(u, dict) or set(u) != {"status", *USAGE_FIELDS} or not isinstance(t.get("trajectory_segment"), dict):
                p.append(f"tasks[{i}]: invalid episode usage or missing trajectory segment")
        elif "trajectory_segment" in t:
            p.append(f"tasks[{i}]: trajectory segment without episode usage")
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
    rows = ns.native_rows(sidecar_path, validate_row)
    segments = []
    for native in rows:
        row = native["row"]
        for task in row["extra"]["tasks"]:
            if "episode_usage" in task:
                if not native["attestation_present"] or not _native_task(row, task):
                    return ()
                seg = task["trajectory_segment"]
                segments.append((row["results_path"], seg["offset"], seg["offset"] + seg["length"]))
    segments.sort()
    if any(a[0] == b[0] and b[1] < a[2] for a, b in zip(segments, segments[1:])):
        return ()
    expanded = list(rows)
    for native in rows:
        for task in native["row"]["extra"]["tasks"]:
            if "episode_usage" not in task:
                continue
            expanded.append({**native, "episode_task": task["task_id"], "episode_field": "status"})
            # Denominators and replay counts have no intrinsic better/worse direction.
            # Carry them in claim text, not as directional performance claims.
            for field in USAGE_FIELDS[4:]:
                if task["episode_usage"][field] is not None:
                    expanded.append({**native, "episode_task": task["task_id"], "episode_field": field})
    return tuple(expanded)


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
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                            sidecar_path=native.get("sidecar_path", ""),
                            no_protocol_ids=("observation:none",), legacy_schema_protocol=True)
    tasks = [task for task in row["extra"]["tasks"] if "episode_usage" in task]
    if tasks and (not ns.results_present(row) or any(not _native_task(row, task) for task in tasks)):
        raise ProjectionError("episode usage is not bound to the native trajectory")
    if "episode_task" not in native:
        return tup
    task = next((t for t in row["extra"]["tasks"] if t["task_id"] == native["episode_task"]), None)
    field = native.get("episode_field")
    if (task is None or field not in (*USAGE_FIELDS[4:], "status") or not _native_task(row, task)
            or not ns.results_present(row)
            or (field != "status" and task["episode_usage"].get(field) is None)):
        raise ProjectionError("episode usage is not bound to the native trajectory")
    usage = task["episode_usage"]
    ident = ns.content_hash({"arm_measurement": row["measurement_id"], "task": task["task_id"], "field": field})[:24]
    run_label = _short_label(row["run_id"])
    arm_label = _short_label(row["extra"]["arm_label"])
    task_label = _short_label(task["task_id"])
    if field == "status":
        counters = ", ".join(f"{key}={usage[key]}" for key in USAGE_FIELDS[:4])
        return replace(tup, measurement_id="tocepisode_" + ident, metric="toc_ab_task_solved",
                       value=int(task["solved"]), unit="task_solved", metric_direction="higher_better",
                       reps=1, reps_basis="scored:tasks",
                       claim=f"TOC {run_label} arm {arm_label} task {task_label}: solved={task['solved']}; usage={usage['status']}; {counters}",
                       attestation_locator=locator + f":task:{task['task_id']}:status",
                       observation={"outcome_native": usage["status"]})
    summary = ", ".join(f"{k}={usage[k]}" for k in USAGE_FIELDS[:4])
    return replace(tup, measurement_id="tocepisode_" + ident, metric="toc_episode_" + field,
                   value=usage[field], unit="tokens" if field.endswith("tokens") else "calls",
                   metric_direction="lower_better", reps=1, reps_basis="observed:episodes",
                   claim=f"TOC {run_label} arm {arm_label} task {task_label}: {field}={usage[field]}; status={usage['status']}; {summary}",
                   attestation_locator=locator + f":task:{task['task_id']}:{field}",
                   observation={"outcome_native": usage["status"]})



def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
