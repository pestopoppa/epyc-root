#!/usr/bin/env python3
"""compute_ready_daemon.py — the reconstructible compute-ready projection writer.

Owning handoff: handoffs/active/wrap-up-division-of-labor-policy.md,
"Compute-blocker intake and graded window contract". The source of truth for
compute-ready work is the accepted `task-checkpoint` receipt, its typed
compute request, and Inference's append-only intake dispositions. This daemon
is the daemon-adjacent writer that REBUILDS the read-only projection at
`coordination/session-bus/compute_ready.json` from those bus records — it
never admits, never grades, and never dispatches.

WHAT IS REIMPLEMENTED HERE, AND WHY THE AMOUNT IS DELIBERATE
-----------------------------------------------------------
None of the planner logic. `compute_ready.py` (landed, pure, replayable) is
invoked as-is via `build_projection`; this module only PROJECTS the bus wire
contracts onto the planner's fixture schemas:

    accepted task-checkpoint receipt  -> compute_ready.checkpoint.v1 row
    compute-blocker disposition event -> compute_ready.intake.v1 row
    compute-window event              -> compute_ready.window.v1 row

The worker's own free-form `compute_request` from the receipt is NOT a planner
input: the coordinator's typed `compute-blocker` forward (`state: submitted`)
is, and the daemon cross-validates that forward against the accepted receipt
it names (envelope hash + blocker_class) so the projection is reconstructible
from bus records alone and a forged/duplicated forward fails closed.

INPUT LEDGERS (all overridable; defaults under the bus root):
    checkpoints   inbox/coordinator-agent.jsonl   (accepted receipts, relayed)
    blockers      outbox/coordinator-agent.jsonl  (submissions)
    dispositions  outbox/inference.jsonl          (lifecycle events)
    windows       outbox/inference.jsonl          (graded windows)
    graph         <repo>/handoffs/active/.index-graph.json

THE OUTPUT
----------
`compute_ready.json` is derived runtime state: atomically replaced, never
hand-edited, carrying `projection_sha256`. `check` rebuilds from the same
ledgers and verifies the stored projection against the deterministic replay
through compute_ready.py's own check path.

Usage:
    compute_ready_daemon.py build --bus-root coordination/session-bus
    compute_ready_daemon.py check --bus-root coordination/session-bus
    compute_ready_daemon.py build --bus-root PATH --checkpoints F --intake F \
        --windows F --graph G --as-of 2026-08-23T12:00:00Z --window-id W-1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import compute_ready as cr

SCHEMA = "compute_ready.projection.v1"
BLOCKER_STATES = ("submitted", "admitted", "duplicate", "needs-info", "rejected",
                  "ready", "planned", "granted", "denied", "running", "terminal")
DISPOSITION_STATES = set(BLOCKER_STATES) - {"submitted"}


class DaemonError(RuntimeError):
    """Fail-closed refusal naming the ledger/record that broke reconstruction."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# ledger readers
# ---------------------------------------------------------------------------


def read_ledger(path: Path) -> list[dict]:
    """Read a JSONL of bus messages (or a single JSON message/array)."""
    if not path.exists():
        raise DaemonError(f"ledger missing: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DaemonError(f"ledger unreadable: {path}: {exc}") from exc
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        rows = []
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise DaemonError(f"malformed JSONL at {path}:{number}: {exc}") from exc
        return rows
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise DaemonError(f"{path} must contain message records")
    return value


def rows_of_kind(rows: list[dict], kind: str) -> list[dict]:
    return [row for row in rows if row.get("kind") == kind]


# ---------------------------------------------------------------------------
# mappers: bus wire contracts -> planner fixture rows (pure, deterministic)
# ---------------------------------------------------------------------------


def receipt_hash(receipt: dict) -> str:
    """The envelope hash the forward must reproduce: the accepted receipt's."""
    return cr.object_hash(receipt)


def submission_to_checkpoint(msg: dict) -> dict:
    """compute-blocker `submitted` forward -> compute_ready.checkpoint.v1 row."""
    p = msg.get("payload") or {}
    req = p.get("requirements") or {}
    model = req.get("model") or {}
    return {
        "schema_version": cr.CHECKPOINT_SCHEMA,
        "kind": "compute-blocker",
        "event_id": msg["id"],
        "author": p.get("source_agent") or str(msg.get("from") or "?"),
        "ts": msg.get("ts") or _utcnow(),
        "blocker_id": p["blocker_id"],
        "task_id": p["task_id"],
        "task_text": p["task_text"],
        "spec_ref": p["spec_ref"],
        "checkpoint_ref": p["checkpoint_ref"],
        "checkpoint_sha256": p["checkpoint_sha256"],
        "validated": True,
        "graph_node_id": p["graph_node_id"],
        "priority_class": p.get("priority_class", "background-churn"),
        "must_run": p.get("must_run", False),
        "expires_at": p["expires_at"],
        "evidence_refs": list(p.get("evidence_refs") or []),
        "operator_gates": [],
        "requirements": {
            "compatible_window_grades": list(p.get("compatible_window_grades") or []),
            "required_devices": list(req.get("required_devices") or []),
            "cpu_bandwidth_class": req.get("cpu_bandwidth_class", ""),
            "gpu_vram_bytes": req.get("gpu_vram_bytes", 0),
            "duration_seconds": req.get("duration_seconds", 0),
            "contention_class": req.get("contention_class", "exclusive-contiguous"),
            "pausable": bool(req.get("pausable")),
            "model": {
                "model_id": model.get("model_id", ""),
                "weight_id": model.get("weight_id", ""),
                "size_bytes": model.get("size_bytes", 0),
                "load_seconds": model.get("load_seconds", 0),
            },
        },
    }


def disposition_to_intake(msg: dict) -> dict:
    """compute-blocker disposition event -> compute_ready.intake.v1 row."""
    p = msg.get("payload") or {}
    row = {
        "schema_version": cr.INTAKE_SCHEMA,
        "kind": "intake-disposition",
        "event_id": msg["id"],
        "author": msg.get("from") or "?",
        "ts": msg.get("ts") or _utcnow(),
        "blocker_id": p["blocker_id"],
        "checkpoint_event_id": p["checkpoint_event_id"],
        "prior_event_id": p["prior_event_id"],
        "state": p["state"],
        "reason_code": p["reason_code"],
    }
    for field in ("evidence_refs", "duplicate_of", "window_id", "lease_id",
                  "lease_path", "physical_claim_refs", "outcome"):
        if p.get(field) is not None:
            row[field] = p[field]
    return row


def window_to_planner(msg: dict) -> dict:
    """compute-window event -> compute_ready.window.v1 row.

    The bus payload carries the handoff's field names (`gpu_vram_available` as
    bytes-plus-observation-refs, `resident_model` as an identity object); the
    landed planner schema splits those apart. This is projection, not logic.
    """
    p = msg.get("payload") or {}
    vram = p.get("gpu_vram_available") or {}
    resident = p.get("resident_model") or {}
    return {
        "schema_version": cr.WINDOW_SCHEMA,
        "kind": "compute-window",
        "event_id": msg["id"],
        "window_id": p["window_id"],
        "author": msg.get("from") or "?",
        "ts": msg.get("ts") or _utcnow(),
        "grade": p["grade"],
        "eligible_devices": list(p.get("eligible_devices") or []),
        "eligible_model_ids": list(p.get("eligible_model_ids") or []),
        "cpu_bandwidth_class": p["cpu_bandwidth_class"],
        "gpu_vram_available_bytes": vram.get("bytes", 0),
        "vram_observation_refs": list(vram.get("observation_refs") or []),
        "max_model_bytes": p.get("max_model_bytes", 0),
        "resident_model_id": resident.get("model_id") if p.get("resident_model") else None,
        "resident_weight_id": resident.get("weight_id") if p.get("resident_model") else None,
        "load_allowed": bool(p.get("load_allowed")),
        "starts_at": p["starts_at"],
        "expires_at": p["expires_at"],
        "time_budget_seconds": p["time_budget_seconds"],
        "safe_drain_at": p["safe_drain_at"],
        "observation_refs": list(p.get("observation_refs") or []),
    }


def derive_checkpoints(ledger_rows: list[dict]) -> list[dict]:
    """Accepted receipts + coordinator forwards -> planner checkpoint rows.

    A forward is trusted only when (a) it is `submitted`, (b) it names an
    accepted task-checkpoint receipt in the ledger, (c) its envelope hash is
    exactly that receipt's, and (d) the receipt is a compute-class blocker
    carrying a compute request. A forward without its receipt is not
    reconstructible and fails closed.
    """
    receipts = {
        row["id"]: row
        for row in rows_of_kind(ledger_rows, "task-checkpoint")
        if isinstance(row.get("id"), str) and row["id"]
    }
    out: list[dict] = []
    for row in rows_of_kind(ledger_rows, "compute-blocker"):
        p = row.get("payload") or {}
        if p.get("state") != "submitted":
            continue
        ref = p.get("checkpoint_ref")
        receipt = receipts.get(ref)
        if receipt is None:
            raise DaemonError(
                f"forward {row.get('id')} names unknown accepted receipt {ref!r} — "
                f"the projection is not reconstructible from the accepted-receipt ledger")
        if not isinstance(receipt.get("payload"), dict) or receipt["payload"].get(
                "blocker_class") != "compute":
            raise DaemonError(
                f"forward {row.get('id')} references receipt {ref} which is not a "
                f"compute-class blocker")
        if receipt_hash(receipt) != p.get("checkpoint_sha256"):
            raise DaemonError(
                f"forward {row.get('id')} checkpoint_sha256 does not match accepted "
                f"receipt {ref} — tampered or re-typed forward")
        out.append(submission_to_checkpoint(row))
    return out


def derive_intake(ledger_rows: list[dict]) -> list[dict]:
    rows = [row for row in rows_of_kind(ledger_rows, "compute-blocker")
            if (row.get("payload") or {}).get("state") in DISPOSITION_STATES]
    return [disposition_to_intake(row) for row in rows]


def derive_windows(ledger_rows: list[dict]) -> list[dict]:
    return [window_to_planner(row) for row in rows_of_kind(ledger_rows, "compute-window")]


def default_graph(bus_root: Path) -> Path:
    """Walk upward from the bus root to the repo's pinned graph."""
    root = Path(bus_root).resolve()
    while True:
        candidate = root / "handoffs" / "active" / ".index-graph.json"
        if candidate.exists():
            return candidate
        if root.parent == root:
            raise DaemonError(
                "no handoffs/active/.index-graph.json found above the bus root — pass --graph")
        root = root.parent


def default_output(bus_root: Path) -> Path:
    return Path(bus_root).resolve() / "compute_ready.json"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _select_window(planner_windows: list[dict], window_id: str | None) -> str | None:
    """Window selection is delegated to the planner; the daemon only chooses the
    default (the latest announcement) when no explicit window id is named."""
    if window_id:
        return window_id
    if not planner_windows:
        return None
    latest = max(planner_windows, key=lambda w: (w.get("ts") or "", w.get("expires_at") or ""))
    return latest["window_id"]


# ---------------------------------------------------------------------------
# build / check
# ---------------------------------------------------------------------------


def build(
    bus_root: Path,
    *,
    checkpoints_path: Path | None = None,
    blockers_path: Path | None = None,
    dispositions_path: Path | None = None,
    windows_path: Path | None = None,
    graph: Path | None = None,
    graph_sha256: str | None = None,
    as_of: str | None = None,
    window_id: str | None = None,
    output: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """Rebuild the projection from the bus ledgers via the planner core.

    Returns the projection dict. When ``dry_run`` the projection is computed
    and returned but never written.
    """
    bus = Path(bus_root).resolve()
    checkpoints_path = Path(checkpoints_path or bus / "inbox" / "coordinator-agent.jsonl")
    blockers_path = Path(blockers_path or bus / "outbox" / "coordinator-agent.jsonl")
    dispositions_path = Path(dispositions_path or bus / "outbox" / "inference.jsonl")
    windows_path = Path(windows_path or bus / "outbox" / "inference.jsonl")
    graph_path = Path(graph or default_graph(bus))
    if not graph_path.exists():
        raise DaemonError(f"graph missing: {graph_path} — pass --graph explicitly")

    checkpoints = derive_checkpoints(read_ledger(checkpoints_path)
                                     + read_ledger(blockers_path))
    intake = derive_intake(read_ledger(blockers_path) + read_ledger(dispositions_path))
    windows = derive_windows(read_ledger(windows_path))
    if not windows:
        raise DaemonError(f"no compute-window events in {windows_path}")
    if not checkpoints:
        raise DaemonError(
            f"no compute-class candidate derivable from accepted receipts in "
            f"{checkpoints_path} and forwards in {blockers_path}")

    graph_hash = graph_sha256 or cr.file_hash(graph_path)
    replay_as_of = as_of or _utcnow()
    chosen_window = _select_window(windows, window_id)

    with tempfile.TemporaryDirectory(prefix="compute-ready-") as staging:
        stage = Path(staging)
        cp_path = stage / "checkpoints.jsonl"
        in_path = stage / "intake.jsonl"
        win_path = stage / "windows.jsonl"
        _write_jsonl(cp_path, checkpoints)
        _write_jsonl(in_path, intake)
        _write_jsonl(win_path, windows)
        projection = cr.build_projection(cp_path, in_path, win_path, graph_path,
                                         graph_hash, replay_as_of, chosen_window)

    if not dry_run:
        cr.write_atomic(Path(output or default_output(bus)), projection)
    return projection


def check(bus_root: Path, **kwargs: Any) -> dict:
    """Rebuild and verify the stored projection through the planner's own check.

    Replay uses the stored projection's as_of/window/graph inputs, so a
    byte-identical reconstruction is the only way the check passes.
    """
    bus = Path(bus_root).resolve()
    existing_path = Path(kwargs.pop("output", None) or default_output(bus))
    if not existing_path.exists():
        raise DaemonError(f"no stored projection at {existing_path}")
    try:
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DaemonError(f"stored projection unreadable: {existing_path}: {exc}") from exc
    if not isinstance(existing, dict) or existing.get("schema_version") != SCHEMA:
        raise DaemonError(f"{existing_path} is not a {SCHEMA} projection")
    replay = build(bus, as_of=existing.get("as_of"),
                   window_id=existing.get("window", {}).get("window_id"),
                   graph_sha256=existing.get("inputs", {}).get("graph", {}).get("sha256"),
                   dry_run=True, **kwargs)
    unsigned = dict(existing)
    unsigned.pop("projection_sha256", None)
    if existing.get("projection_sha256") != cr.object_hash(unsigned):
        raise DaemonError(f"{existing_path} stored self-hash is invalid")
    if cr.canonical_bytes(existing) != cr.canonical_bytes(replay):
        raise DaemonError(f"{existing_path} differs from the deterministic replay")
    return replay


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "check"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--bus-root", required=True)
        cmd.add_argument("--checkpoints", type=Path, help="accepted-receipt ledger")
        cmd.add_argument("--blockers", type=Path, help="compute-blocker forward ledger")
        cmd.add_argument("--dispositions", type=Path, help="lifecycle-event ledger")
        cmd.add_argument("--windows", type=Path)
        cmd.add_argument("--graph", type=Path)
        cmd.add_argument("--graph-sha256")
        cmd.add_argument("--as-of")
        cmd.add_argument("--window-id")
        cmd.add_argument("--output", type=Path)
        cmd.add_argument("--dry-run", action="store_true", help="compute but do not write")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "build":
            projection = build(
                args.bus_root, checkpoints_path=args.checkpoints,
                blockers_path=args.blockers, dispositions_path=args.dispositions,
                windows_path=args.windows, graph=args.graph,
                graph_sha256=args.graph_sha256, as_of=args.as_of,
                window_id=args.window_id, output=args.output, dry_run=args.dry_run)
            destination = args.output or default_output(Path(args.bus_root))
            sys.stdout.buffer.write(cr.canonical_bytes(projection))
            print(f"\n# wrote {destination}" if not args.dry_run
                  else f"\n# dry-run: would write {destination}", file=sys.stderr)
            return 0
        replay = check(args.bus_root, checkpoints_path=args.checkpoints,
                       blockers_path=args.blockers, dispositions_path=args.dispositions,
                       windows_path=args.windows, graph=args.graph, output=args.output)
        print(f"OK {replay['projection_sha256']}")
        return 0
    except (DaemonError, cr.ContractError) as exc:
        if isinstance(exc, cr.ContractError):
            print(json.dumps({"error": exc.as_dict()}, sort_keys=True), file=sys.stderr)
        else:
            print(f"compute_ready_daemon: REFUSING — {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
