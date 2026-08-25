#!/usr/bin/env python3
"""rtg51_rollout.py — the RTG-51 rollout gates (off | shadow | enforce) and the
shadow-mode receipt validator.

Owning handoff: handoffs/active/wrap-up-division-of-labor-policy.md, "Rollout
and rollback": start `off`, then `shadow`, then `enforce`. Shadow mode records
and validates the new receipts while legacy behavior remains available; it
NEVER rejects legacy behavior. Every validation result is written as a
`finding`-shaped observation on the bus.

WHAT THIS MODULE IS
-------------------
A tiny policy loader plus ONE fail-closed structural validator for the new
typed receipts/events (task-checkpoint, compute-blocker, compute-window). The
validator's job is bounded on purpose: full git reachability, path ownership
and commit-content admission are the coordinator-daemon's — this is the
canary layer that measures whether the new wire contracts are being honored
without changing any live behavior.

The loader reads `coordination/session-bus/rtg51_rollout.yaml`. The file is a
handful of scalar lines by design, so the loader parses exactly that subset
with the standard library (no PyYAML dependency under /usr/bin/python3) and
REFUSES anything else: a config that cannot be parsed must not silently mean
`off`.

`RTG51_SHADOW_MODE=1` forces every gate to its shadow/observe value — the
canary escape hatch for tests and staged runs, mirroring how
`role_rollout.audit_completion` selects `shadow` from config.yaml.

MODE SEMANTICS (per gate):
    off     record nothing, validate nothing, never raise.
    shadow  validate; every result becomes a finding-shaped observation on the
            validating agent's own outbox; NEVER raise.
    enforce validate; a defect raises ReceiptRefusal.

THE FINDING SHAPE
-----------------
kind=finding, authored by the validating agent into its OWN outbox (single
writer, invariant 1). payload carries the surface, the receipt/event id, the
mode, and the result. It is a finding, not a defect: in shadow mode nothing
changed behavior and nobody must act.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "rtg51_rollout.v1"
VALID_MODES = {"off", "shadow", "enforce", "observe"}

DEFAULT_GATES = {
    "worker_checkpoint_receipts": "off",
    "auditor_full_wrap": "off",
    "compute_window_plan": "off",
}
# The shadow-grade of each gate when RTG51_SHADOW_MODE=1 forces a canary run.
SHADOW_GRADE = {
    "worker_checkpoint_receipts": "shadow",
    "auditor_full_wrap": "shadow",
    "compute_window_plan": "observe",
}

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
BOUNDARY_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


class RolloutError(RuntimeError):
    """The rollout config is unreadable or malformed — fail closed, never `off`."""


class ReceiptRefusal(RuntimeError):
    """Enforce-mode refusal of a defective receipt/event."""


def default_bus_root() -> Path:
    return Path(__file__).resolve().parents[2] / "coordination" / "session-bus"


def _parse_scalar_yaml(text: str) -> dict[str, str]:
    """Parse the fixed-shape scalar config; refuse anything else."""
    out: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip() if "#" in raw else raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep or not key.strip() or not value.strip():
            raise RolloutError(f"rtg51_rollout.yaml:{number}: expected 'key: value'")
        if key.strip() != "schema_version" and not out.get("schema_version"):
            raise RolloutError(
                f"rtg51_rollout.yaml:{number}: schema_version must be the first key"
            )
        if key.strip() in out:
            raise RolloutError(f"rtg51_rollout.yaml:{number}: duplicate key {key.strip()!r}")
        out[key.strip()] = value.strip()
    return out


def load_rollout(bus_root: Path | str | None = None,
                 env: dict[str, str] | None = None,
                 path: Path | str | None = None) -> dict[str, str]:
    """Effective per-gate modes: file, overridden by RTG51_SHADOW_MODE=1.

    A missing file reads as all-`off` (rollout starts off; the plan changes no
    live behavior merely by existing). A present-but-malformed file REFUSES —
    a config that cannot be parsed must not silently mean `off`. `path` names
    the config file directly (the heavy-wrap executor's --rollout-file).
    """
    env = dict(os.environ if env is None else env)
    if path is not None:
        config_path = Path(path)
    else:
        config_path = Path(bus_root or default_bus_root()) / "rtg51_rollout.yaml"
    if not config_path.exists():
        gates: dict[str, str] = dict(DEFAULT_GATES)
    else:
        parsed = _parse_scalar_yaml(config_path.read_text(encoding="utf-8"))
        if parsed.get("schema_version") != SCHEMA:
            raise RolloutError(
                f"{config_path}: schema_version must be {SCHEMA!r}, got {parsed.get('schema_version')!r}"
            )
        gates = dict(DEFAULT_GATES)
        unknown = sorted(set(parsed) - {"schema_version"} - set(DEFAULT_GATES))
        if unknown:
            raise RolloutError(f"{config_path}: unknown gate key(s) {unknown}")
        for key in DEFAULT_GATES:
            value = parsed.get(key, DEFAULT_GATES[key])
            if value not in VALID_MODES:
                raise RolloutError(f"{config_path}: gate {key} has invalid mode {value!r}")
            gates[key] = value
    if env.get("RTG51_SHADOW_MODE") in {"1", "true", "yes"}:
        gates = {key: SHADOW_GRADE[key] for key in gates}
    return gates


def mode_of(gates: dict[str, str], name: str) -> str:
    return gates.get(name, "off")


@dataclass(frozen=True)
class ValidationResult:
    surface: str
    ref: str
    result: str          # "valid" | "defect"
    reasons: tuple[str, ...]
    mode: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "ref": self.ref,
            "result": self.result,
            "reasons": list(self.reasons),
            "mode": self.mode,
        }


# ---------------------------------------------------------------------------
# structural receipt validation (bounded; git-level admission is the daemon's)
# ---------------------------------------------------------------------------

_CHECKPOINT_REQUIRED = (
    "boundary_id", "outcome", "boundary_reason", "task_id", "task_text", "spec_ref",
    "agent", "branch", "commit_sha", "pushed_ref", "progress_path", "handoff_paths",
    "validation", "next_context", "major_checkpoint", "completed_at",
)
_CHECKPOINT_OUTCOMES = {"completed", "blocked", "partial"}
_BLOCKER_CLASSES = {"dependency", "operator-decision", "external-event", "compute"}


def _checkpoint_defects(payload: Any) -> list[str]:
    defects: list[str] = []
    if not isinstance(payload, dict):
        return ["payload is not an object"]
    for field in _CHECKPOINT_REQUIRED:
        if field not in payload:
            defects.append(f"missing payload.{field}")
    if defects:
        return defects
    if not isinstance(payload["boundary_id"], str) or not BOUNDARY_RE.fullmatch(
            payload["boundary_id"]):
        defects.append("payload.boundary_id must be a stable boundary token")
    if payload["outcome"] not in _CHECKPOINT_OUTCOMES:
        defects.append(f"payload.outcome must be one of {sorted(_CHECKPOINT_OUTCOMES)}")
    if not isinstance(payload["commit_sha"], str) or not SHA40_RE.fullmatch(payload["commit_sha"]):
        defects.append("payload.commit_sha must be a 40-hex SHA")
    if not isinstance(payload["branch"], str) or not payload["branch"].startswith("lane/"):
        defects.append("payload.branch must be lane/<agent>")
    if not isinstance(payload["pushed_ref"], str) or not payload["pushed_ref"].startswith(
            "refs/remotes/origin/lane/"):
        defects.append("payload.pushed_ref must be refs/remotes/origin/lane/<agent>")
    if payload["outcome"] in {"blocked", "partial"}:
        for field in ("blocker_class", "blocked_on", "blocking_owner_or_event",
                      "evidence_refs", "alternatives_exhausted", "resume_action"):
            if not payload.get(field):
                defects.append(f"blocked/partial receipt requires payload.{field}")
        if payload.get("blocker_class") not in _BLOCKER_CLASSES:
            defects.append(f"payload.blocker_class must be one of {sorted(_BLOCKER_CLASSES)}")
    if payload["outcome"] == "partial" and payload.get("boundary_reason") != "pre-reboot":
        defects.append("partial receipts require boundary_reason=pre-reboot")
    if not isinstance(payload.get("validation"), list) or not payload["validation"]:
        defects.append("payload.validation must be a non-empty command-evidence array")
    return defects


def _blocker_defects(payload: Any) -> list[str]:
    defects: list[str] = []
    if not isinstance(payload, dict):
        return ["payload is not an object"]
    for field in ("blocker_id", "state", "checkpoint_ref", "requirements", "expires_at"):
        if field not in payload:
            defects.append(f"missing payload.{field}")
    if defects:
        return defects
    if not isinstance(payload["blocker_id"], str) or not payload["blocker_id"]:
        defects.append("payload.blocker_id must be non-empty")
    state = payload["state"]
    lifecycle = ("submitted", "admitted", "duplicate", "needs-info", "rejected",
                 "ready", "planned", "granted", "denied", "running", "terminal")
    if state not in lifecycle:
        defects.append(f"payload.state must be one of {lifecycle}")
    req = payload["requirements"]
    if not isinstance(req, dict):
        defects.append("payload.requirements must be an object")
    else:
        for field in ("required_devices", "cpu_bandwidth_class", "gpu_vram_bytes",
                      "duration_seconds", "contention_class", "pausable", "model"):
            if field not in req:
                defects.append(f"missing payload.requirements.{field}")
    if not isinstance(payload.get("checkpoint_sha256"), str) or len(
            payload["checkpoint_sha256"]) != 64:
        defects.append("payload.checkpoint_sha256 must be a 64-hex SHA-256")
    return defects


def _window_defects(payload: Any) -> list[str]:
    defects: list[str] = []
    if not isinstance(payload, dict):
        return ["payload is not an object"]
    for field in ("grade", "eligible_devices", "cpu_bandwidth_class", "load_allowed",
                  "starts_at", "expires_at", "time_budget_seconds", "safe_drain_at",
                  "observation_refs", "gpu_vram_available", "resident_model"):
        if field not in payload:
            defects.append(f"missing payload.{field}")
    if defects:
        return defects
    if payload["grade"] not in {"small-model-only", "load-then-keep-hot", "full-idle"}:
        defects.append("payload.grade must be a known window grade")
    if not isinstance(payload.get("eligible_devices"), list) or not payload["eligible_devices"]:
        defects.append("payload.eligible_devices must be a non-empty list")
    if not isinstance(payload.get("load_allowed"), bool):
        defects.append("payload.load_allowed must be boolean")
    return defects


_SURFACE_VALIDATORS = {
    "task-checkpoint": _checkpoint_defects,
    "compute-blocker": _blocker_defects,
    "compute-window": _window_defects,
}


def validate_event(row: dict, *, surface: str, gates: dict[str, str],
                   bus_root: Path | str | None = None,
                   emit_agent: str | None = None,
                   emit: bool = True) -> list[ValidationResult]:
    """The one shadow/enforce validator. Returns findings; raises only in enforce.

    `surface` selects the structural validator; the row is a bus message
    envelope. The mode is taken from the gate that governs the surface:

        task-checkpoint -> worker_checkpoint_receipts
        compute-blocker/compute-window -> compute_window_plan

    off      -> no findings, never raise.
    shadow   -> findings are emitted as finding-shaped observations (unless
                `emit=False`), never raise.
    enforce  -> a defect raises ReceiptRefusal; a valid row yields one
                "valid" finding for the record.
    """
    gate = {"task-checkpoint": "worker_checkpoint_receipts",
            "compute-blocker": "compute_window_plan",
            "compute-window": "compute_window_plan"}[surface]
    mode = mode_of(gates, gate)
    if mode == "off":
        return []
    validator = _SURFACE_VALIDATORS[surface]
    defects = validator(row.get("payload") if isinstance(row, dict) else None)
    if not isinstance(row, dict) or row.get("kind") != {
        "task-checkpoint": "task-checkpoint",
        "compute-blocker": "compute-blocker",
        "compute-window": "compute-window",
    }[surface]:
        defects.insert(0, f"row.kind must be {surface}")
    result = ValidationResult(
        surface=surface,
        ref=str((row.get("payload") or {}).get("boundary_id")
                or (row.get("payload") or {}).get("blocker_id")
                or (row.get("payload") or {}).get("window_id")
                or row.get("id") or "?"),
        result="valid" if not defects else "defect",
        reasons=tuple(defects),
        mode=mode,
    )
    if mode == "enforce" and defects:
        raise ReceiptRefusal(f"{surface} {result.ref}: " + "; ".join(defects))
    if emit and bus_root is not None and emit_agent is not None:
        emit_finding(Path(bus_root), emit_agent, result.as_dict())
    return [result]


# ---------------------------------------------------------------------------
# the finding-shaped observation
# ---------------------------------------------------------------------------


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_ROSTER_ROW_RE = re.compile(r"^\s*-\s*(?:\{[^}]*\bid:\s*([A-Za-z0-9_.-]+)|id:\s*([A-Za-z0-9_.-]+))",
                            re.MULTILINE)


def _require_roster_id(bus_root: Path, agent: str) -> None:
    """Fail-closed roster check; falls back to the inline-dict subset when the
    interpreter has no yaml module (the pytest venv), never weakening the check."""
    try:
        from scripts.coordination import session_bus
        session_bus._require_roster_id(bus_root, agent)
        return
    except Exception as exc:  # noqa: BLE001 — either missing-yaml or genuine refusal
        message = str(exc)
        if "yaml" not in message and "No module named" not in message:
            raise
    try:
        ids = {m.group(1) or m.group(2) for m in
               _ROSTER_ROW_RE.finditer((bus_root / "config.yaml").read_text(encoding="utf-8"))}
    except OSError as exc:
        raise RolloutError(f"could not read config.yaml roster: {exc}") from exc
    if not ids:
        raise RolloutError("config.yaml roster is missing or malformed; refusing an unverified writer")
    if agent not in ids:
        raise RolloutError(
            f"{agent!r} is not a roster id in config.yaml (have: {', '.join(sorted(ids))})")


def emit_finding(bus_root: Path, agent: str, finding: dict) -> dict:
    """Append a kind=finding observation to the agent's OWN outbox (single writer)."""
    from scripts.coordination import session_bus  # local import: session_bus is heavy

    path = bus_root / "outbox" / f"{agent}.jsonl"
    writer = session_bus.required_writer(bus_root, path)
    if writer != agent:
        raise RolloutError(f"single-writer violation: {agent!r} may not write {path}")
    _require_roster_id(bus_root, agent)
    existing, _ = session_bus._read_jsonl(path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    row = {
        "schema_version": session_bus.MSG_SCHEMA_VERSION,
        "id": f"msg-{stamp}-{len(existing) + 1}-{agent}",
        "ts": _utcnow_iso(),
        "from": agent,
        "to": "coordinator-agent",
        "kind": "finding",
        "task_id": str(finding.get("ref") or "?"),
        "payload": {
            "rtg51_validation": finding,
            "source": "rtg51-shadow",
            "note": "shadow-mode validation record; no behavior changed and no action is owed",
        },
    }
    session_bus.validate_row(bus_root, row, "msg")
    session_bus._append_jsonl(path, row)
    return row


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--bus-root", default=str(default_bus_root()))
    parser.add_argument("--json", action="store_true", help="print gates as JSON")
    args = parser.parse_args(argv)
    try:
        gates = load_rollout(args.bus_root)
    except RolloutError as exc:
        print(f"rtg51_rollout: REFUSING — {exc}", file=__import__("sys").stderr)
        return 2
    if args.json:
        print(json.dumps(gates, sort_keys=True))
    else:
        for key in ("worker_checkpoint_receipts", "auditor_full_wrap", "compute_window_plan"):
            print(f"{key}: {gates[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
