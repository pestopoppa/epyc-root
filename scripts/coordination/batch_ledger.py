#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Consolidated inference-batch ledger (Ledger v2) — batch-infra item B1 / Wave-1 W0a.

An append-only JSONL execution ledger for the consolidated inference-batch system.
Row shape = the ``execution_manifest.jsonl`` v1 fields
(``epyc-orchestrator/data/bulk_inference_2026_05_26/execution_manifest.jsonl``)
extended with the v2 fields required by the D1 spec:
``entry_hash, attestation_ref, era_stamp, gate_results[], wall_clock_s,
failure_reason, operator_batch_ref``.

Design constraints:
  * Append-only: every state transition is a new line. Latest row per ``task_id`` wins.
  * Zero third-party dependencies — stdlib only — so the ledger is importable from
    any interpreter. (The compiler that produces the manifest needs pyyaml/jsonschema
    and therefore targets ``/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python``; this
    module does not.)
  * NO live probing. ``pending()`` / ``reconcile()`` reason purely over the ledger rows
    and the structural shape of the manifest entries — they never inspect host health,
    topology, flags-on-workers, or autopilot state. Those are the executor's job.

Public API
----------
    led = Ledger("coordination/inference-batch/ledger.jsonl")   # or Ledger() for in-memory
    led.append_row({"task_id": "T1", "status": "DONE_PASS", ...})
    led.latest_state("T1")          -> "DONE_PASS" | None
    led.latest_row("T1")            -> dict | None
    led.all_latest()                -> {task_id: row}
    led.reconcile(manifest)         -> {task_id: status}   (live states for manifest tasks)
    led.pending(manifest)           -> [entry, ...]         (structurally eligible entries)

``manifest`` may be a list of entry dicts, a ``{"entries": [...]}`` mapping, or a path to
a compiled ``manifest.yaml`` / ``manifest.json`` (yaml loaded lazily, only if a .yaml path
is passed).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

SCHEMA_VERSION = "batch_ledger.v2"

# ---------------------------------------------------------------------------
# Status vocabulary
# ---------------------------------------------------------------------------
STATUSES = (
    "READY",
    "RUNNING",
    "DONE_PASS",
    "DONE_MARGINAL_OBS",
    "FAILED_REVERTED",
    "INFRA_BLOCKED",
    "HELD_AMBIGUOUS",
    "HELD_OP_GATE",
    "BLOCKED_PRECONDITION",
    "SKIPPED_SUPERSEDED",
    "COORDINATION",
)

#: States that satisfy a downstream ``depends_on`` edge. A dependency must have
#: *succeeded* (pass or marginal-observation) for a dependent to become eligible.
#: SKIPPED_SUPERSEDED deliberately does NOT satisfy a dependency — a task whose input
#: was skipped should block, not silently proceed.
TERMINAL_SUCCESS = frozenset({"DONE_PASS", "DONE_MARGINAL_OBS"})

#: States that mean "will not run again" (terminal, for reporting / reconcile).
TERMINAL_STATES = frozenset(
    {"DONE_PASS", "DONE_MARGINAL_OBS", "FAILED_REVERTED", "SKIPPED_SUPERSEDED"}
)

#: States from which an entry is eligible without consulting retry policy. An entry
#: with no ledger row at all is implicitly READY.
ELIGIBLE_STATES = frozenset({"READY"})

#: States from which an entry may be re-admitted only when its entry-level
#: retry_policy explicitly allows that status. This keeps infra recovery from
#: becoming a permanent wedge without blindly retrying every blocked row.
RETRYABLE_STATES = frozenset({"INFRA_BLOCKED", "BLOCKED_PRECONDITION"})

#: Entries at/above this phase are non-executable COORDINATION cross-references
#: (parallel-session-owned work); pending() never returns them.
COORDINATION_PHASE_FLOOR = 90

# Fields carried from execution_manifest.jsonl v1 (defaults applied on append).
_V1_DEFAULTS: Dict[str, Any] = {
    "run_id": None,
    "required_topology_hash": None,
    "status": None,
    "allowed_concurrency_mode": None,
    "matrix_status": None,
    "flags": {},
    "needs_approval": False,
    "command": None,
    "output_path": None,
    "journal_quarantine_rule": None,
    "pass_fail_gate": None,
    "next_action": None,
    "findings": [],
    "artifacts": [],
}

# v2 additions.
_V2_DEFAULTS: Dict[str, Any] = {
    "entry_hash": None,
    "attestation_ref": None,
    "era_stamp": None,
    "gate_results": [],
    "wall_clock_s": None,
    "failure_reason": None,
    "operator_batch_ref": None,
}


class LedgerError(ValueError):
    """Raised on malformed ledger operations (bad status, missing task_id)."""


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _retry_policy(entry: dict) -> dict:
    execution = entry.get("execution") or {}
    policy = execution.get("retry_policy") or {}
    return policy if isinstance(policy, dict) else {}


def _retry_on(entry: dict) -> set[str]:
    policy = _retry_policy(entry)
    return {str(item) for item in (policy.get("retry_on") or [])}


def _stale_running_after_s(entry: dict) -> Optional[float]:
    policy = _retry_policy(entry)
    value = policy.get("stale_running_after_s")
    if value is None:
        value = (entry.get("execution") or {}).get("timeout_s")
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    return seconds if seconds > 0 else None


def is_retry_pickable(
    entry: dict,
    latest_row: Optional[dict],
    *,
    now: Optional[datetime] = None,
) -> bool:
    """Return whether a non-READY latest row may be picked again.

    The ledger remains append-only: retrying still happens by executing the entry
    and appending a new row. This helper only controls structural pickability.
    """
    if not latest_row:
        return True
    status = str(latest_row.get("status") or "")
    if status in ELIGIBLE_STATES:
        return True
    retry_on = _retry_on(entry)
    if status in RETRYABLE_STATES:
        return status in retry_on
    if status == "RUNNING":
        stale_after = _stale_running_after_s(entry)
        if stale_after is None:
            return False
        started = _parse_utc_ts(latest_row.get("ts"))
        if started is None:
            return False
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        age_s = (current.astimezone(timezone.utc) - started).total_seconds()
        return age_s > stale_after and bool(retry_on)
    return False


def canonical_hash(obj: Any) -> str:
    """Stable sha256 over a JSON-serialisable object (sorted keys, no whitespace).

    Used for ``entry_hash`` so the ledger can bind a row to the exact entry that was
    executed and detect drift (hash-bound invalidation)."""
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _normalise_entries(manifest: Union[str, Path, dict, list]) -> List[dict]:
    """Coerce a manifest (path / mapping / list) into a list of entry dicts."""
    if isinstance(manifest, (str, Path)):
        p = Path(manifest)
        text = p.read_text(encoding="utf-8")
        if p.suffix in (".yaml", ".yml"):
            import yaml  # lazy: only needed when a yaml path is passed

            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
        return _normalise_entries(data)
    if isinstance(manifest, dict):
        return list(manifest.get("entries", []))
    if isinstance(manifest, list):
        return list(manifest)
    raise LedgerError(f"cannot interpret manifest of type {type(manifest)!r}")


class Ledger:
    """Append-only JSONL ledger; latest row per task_id wins.

    Pass a filesystem ``path`` for a persistent ledger, or ``None`` for an in-memory
    ledger (used by ``--simulate`` and by tests; never touches disk)."""

    def __init__(self, path: Optional[Union[str, Path]] = None):
        self.path: Optional[Path] = Path(path) if path is not None else None
        self._mem: List[dict] = []  # backing store when in-memory (path is None)

    # -- row construction ---------------------------------------------------
    @staticmethod
    def new_row(task_id: str, status: str, **fields: Any) -> dict:
        """Build a fully-defaulted v2 row. ``fields`` override any default."""
        if not task_id:
            raise LedgerError("task_id is required")
        if status not in STATUSES:
            raise LedgerError(
                f"unknown status {status!r}; valid: {', '.join(STATUSES)}"
            )
        row: Dict[str, Any] = {"schema_version": SCHEMA_VERSION, "task_id": task_id}
        row.update(_V1_DEFAULTS)
        row.update(_V2_DEFAULTS)
        row.update(fields)
        row["task_id"] = task_id
        row["status"] = status
        row["ts"] = fields.get("ts") or _utcnow_iso()
        return row

    # -- append -------------------------------------------------------------
    def append_row(self, row: dict) -> dict:
        """Validate and append a row. Returns the fully-defaulted stored row.

        Accepts a partial dict (``task_id`` + ``status`` required); missing v1/v2
        fields are filled with defaults so the JSONL is uniform."""
        task_id = row.get("task_id")
        status = row.get("status")
        if not task_id:
            raise LedgerError("append_row: 'task_id' is required")
        if status not in STATUSES:
            raise LedgerError(
                f"append_row: unknown status {status!r}; valid: {', '.join(STATUSES)}"
            )
        extra = {k: v for k, v in row.items() if k not in ("task_id", "status")}
        full = self.new_row(task_id, status, **extra)
        if self.path is None:
            self._mem.append(full)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(full, sort_keys=True) + "\n")
        return full

    # -- reads --------------------------------------------------------------
    def rows(self) -> List[dict]:
        """All rows in append order (oldest first)."""
        if self.path is None:
            return list(self._mem)
        if not self.path.exists():
            return []
        out: List[dict] = []
        with self.path.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                    raise LedgerError(
                        f"{self.path}:{lineno}: malformed JSONL row: {exc}"
                    ) from exc
        return out

    def all_latest(self) -> Dict[str, dict]:
        """Latest row per task_id (last-appended wins)."""
        latest: Dict[str, dict] = {}
        for row in self.rows():
            tid = row.get("task_id")
            if tid is not None:
                latest[tid] = row  # later rows overwrite earlier ones
        return latest

    def latest_row(self, task_id: str) -> Optional[dict]:
        return self.all_latest().get(task_id)

    def latest_state(self, task_id: str) -> Optional[str]:
        row = self.latest_row(task_id)
        return row.get("status") if row else None

    # -- manifest reconciliation -------------------------------------------
    def reconcile(self, manifest: Union[str, Path, dict, list]) -> Dict[str, str]:
        """Live state per task_id for every entry in the manifest.

        Entries with no ledger row default to ``READY``. Ledger rows for task_ids that
        are NOT in the manifest are orphans and are excluded (see :meth:`orphans`)."""
        entries = _normalise_entries(manifest)
        latest = self.all_latest()
        states: Dict[str, str] = {}
        for entry in entries:
            tid = entry.get("task_id")
            if tid is None:
                continue
            row = latest.get(tid)
            states[tid] = row["status"] if row else "READY"
        return states

    def orphans(self, manifest: Union[str, Path, dict, list]) -> List[str]:
        """task_ids present in the ledger but absent from the manifest."""
        entries = _normalise_entries(manifest)
        manifest_ids = {e.get("task_id") for e in entries}
        return sorted(tid for tid in self.all_latest() if tid not in manifest_ids)

    # -- eligibility --------------------------------------------------------
    def pending(self, manifest: Union[str, Path, dict, list]) -> List[dict]:
        """Entries eligible to be picked next, in deterministic execution order.

        An entry is eligible iff ALL of:
          * its live ledger state is READY, absent, or explicitly retry-pickable
            by the entry's retry_policy, AND
          * its preconditions are *structurally* satisfiable (deps reference known
            task_ids; flags_required and flags_forbidden do not contradict), AND
          * every ``depends_on`` task is in a terminal-success state
            (DONE_PASS or DONE_MARGINAL_OBS).

        This is STRUCTURAL only — no host-health / topology / flag-on-worker / autopilot
        probing, and operator_gates are NOT evaluated here (they are resolved live by
        the executor). Returned list is sorted by (phase, priority, task_id)."""
        entries = _normalise_entries(manifest)
        by_id = {e.get("task_id"): e for e in entries}
        latest = self.all_latest()
        states = self.reconcile(entries)

        eligible: List[dict] = []
        for entry in entries:
            tid = entry.get("task_id")
            if tid is None:
                continue
            # Phase >= COORDINATION_PHASE_FLOOR (90) are non-executable cross-reference
            # rows for parallel-session-owned work; the loop never picks them. Their
            # ledger state should also be seeded COORDINATION, but this guard makes the
            # skip robust even if the seed step is missed.
            if int(entry.get("phase", 0)) >= COORDINATION_PHASE_FLOOR:
                continue
            if not is_retry_pickable(entry, latest.get(tid)):
                continue
            if not _structurally_satisfiable(entry, by_id):
                continue
            deps = _deps_of(entry)
            if all(states.get(d) in TERMINAL_SUCCESS for d in deps):
                eligible.append(entry)
        eligible.sort(key=sort_key)
        return eligible


# ---------------------------------------------------------------------------
# Ordering + structural helpers (module-level so the compiler can reuse them)
# ---------------------------------------------------------------------------
_PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def priority_rank(priority: Optional[str]) -> int:
    return _PRIORITY_RANK.get(priority or "P4", 99)


def sort_key(entry: dict):
    """Deterministic execution ordering: phase asc, priority asc, task_id asc."""
    return (
        int(entry.get("phase", 0)),
        priority_rank(entry.get("priority")),
        str(entry.get("task_id", "")),
    )


def _deps_of(entry: dict) -> List[str]:
    return list(entry.get("preconditions", {}).get("depends_on", []) or [])


def _structurally_satisfiable(entry: dict, by_id: Dict[str, dict]) -> bool:
    """True if the entry has no internal / cross-entry structural contradiction.

    Structural checks only (no liveness):
      * every depends_on target exists in the manifest, and
      * no flag is simultaneously required and forbidden.
    """
    for dep in _deps_of(entry):
        if dep not in by_id:
            return False
    pre = entry.get("preconditions", {})
    required = set((pre.get("flags_required") or {}).keys())
    forbidden = set(pre.get("flags_forbidden") or [])
    if required & forbidden:
        return False
    return True


def simulate(
    manifest: Union[str, Path, dict, list],
    ledger: Optional[Ledger] = None,
) -> Dict[str, Any]:
    """Walk pick-next over a (by default empty, in-memory) ledger — pure dry logic.

    Repeatedly takes ``ledger.pending(manifest)``, picks the first entry in
    deterministic order, and records a synthetic DONE_PASS row in the (in-memory)
    ledger, until no entry is eligible. Proves the phase/priority/dependency ordering
    WITHOUT executing anything.

    Returns::

        {
          "order":     [ {task_id, phase, priority, depends_on}, ... ],  # scheduled
          "unscheduled": [task_id, ...],   # never eligible (unsatisfiable deps / cycle)
        }
    """
    entries = _normalise_entries(manifest)
    led = ledger if ledger is not None else Ledger()  # in-memory
    all_ids = {e.get("task_id") for e in entries if e.get("task_id") is not None}

    order: List[dict] = []
    scheduled: set = set()
    # Bound the walk to guarantee termination even on a malformed cyclic manifest.
    for _ in range(len(entries) + 1):
        ready = led.pending(entries)
        ready = [e for e in ready if e.get("task_id") not in scheduled]
        if not ready:
            break
        pick = ready[0]
        tid = pick["task_id"]
        order.append(
            {
                "task_id": tid,
                "phase": pick.get("phase"),
                "priority": pick.get("priority"),
                "depends_on": _deps_of(pick),
            }
        )
        scheduled.add(tid)
        led.append_row(
            led.new_row(tid, "DONE_PASS", next_action="simulated pick-next")
        )

    unscheduled = sorted(all_ids - scheduled)
    return {"order": order, "unscheduled": unscheduled}


__all__ = [
    "Ledger",
    "LedgerError",
    "STATUSES",
    "TERMINAL_SUCCESS",
    "TERMINAL_STATES",
    "SCHEMA_VERSION",
    "canonical_hash",
    "simulate",
    "sort_key",
    "priority_rank",
]
