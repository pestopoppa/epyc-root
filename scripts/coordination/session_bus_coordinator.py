#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""session_bus_coordinator.py — the coordinator-daemon (M3: read-only advisory).

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md
Contract:       coordination/session-bus/BUS_PROTOCOL.md

WHAT THIS IS. The deterministic, always-on tier of the coordinator. It ticks,
senses lane occupancy, folds the queue, and computes what it *would* assign.
It never analyzes, reviews, or edits work products — queue/routing/watchdog only
("the moment it reviews, it's a second main" — operator).

TWO AUTHORITY LEVELS, one switch between them.

`authority: manual` | `advisory` (M3) — the daemon writes ONLY two files, both
of which it owns:

    heartbeats/coordinator-daemon.json   its own liveness + epoch
    advisory.jsonl                        would-assign / saturation / audit records

It does NOT write queue.jsonl, any inbox, or the token queue, so a running daemon
cannot disturb the M1 manual workflow. This is the property M3 verified.

`authority: assign` (M4) — additionally transcribes agent reports into the queue,
relays token-requests, runs the stall ladder, and makes real assignments. See
`apply_assignment()`. Setting authority back to `advisory` is the documented
rollback and needs no other change.

M4's ordering is deliberate: transcribe first so decisions are made against
current truth rather than a stale queue; relay tokens next so a newly-gated task
is not then assigned in the same tick; run the stall ladder before assigning so a
requeued task is immediately available; assign last. Every write is idempotent —
transcription compares the latest report per task against the queue rather than
tracking consumed messages, so a repeated tick cannot double-apply.

EPOCH FENCING. Each start increments the epoch (read back from the daemon's own
heartbeat). Advisory rows carry it so a stale record from a previous generation
is identifiable rather than silently mixed in.

SAFETY. A flock singleton means a second copy exits immediately. Lane sensing is
fail-safe: a lane counts as idle only when every signal agrees it is, and an
unknown signal means busy.

Run:
    nohup scripts/coordination/session_bus_coordinator.py run > logs/coordinator_daemon.out 2>&1 &
    scripts/coordination/session_bus_coordinator.py once      # single tick, for cron/tests
    scripts/coordination/session_bus_coordinator.py status
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination.session_bus import (  # noqa: E402
    COORDINATOR_DAEMON,
    DEFAULT_BUS_ROOT,
    MSG_SCHEMA_VERSION,
    QUEUE_SCHEMA_VERSION,
    TERMINAL_STATES,
    _append_jsonl,
    _read_jsonl,
    _write_atomic,
    fold_queue,
)

LOCK_PATH = Path("/tmp/session_bus_coordinator.lock")
ADVISORY_SCHEMA = "session_bus.advisory.v1"

# A lane is idle only when every signal agrees; unknown means busy.
_BUSY_LOAD_CLASSES = {"busy"}
_UNKNOWN_IS_BUSY = True


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Per-tick probe cache. Host sensing (pgrep + llama-server HTTP + rocm-smi) costs
# ~2s per call, and a single tick needs the lane snapshot and the co-residency
# context in several places. Probing repeatedly would burn a material slice of a
# 45s tick AND risk two halves of one decision seeing different host states,
# which is the worse problem. Cleared at the top of every tick.
_TICK_CACHE: dict[str, Any] = {}


def _reset_tick_cache() -> None:
    _TICK_CACHE.clear()


def lane_snapshot_cached() -> dict:
    if "lanes" not in _TICK_CACHE:
        _TICK_CACHE["lanes"] = _lane_snapshot()
    return _TICK_CACHE["lanes"]


def co_residency_cached(config: dict) -> dict:
    if "co" not in _TICK_CACHE:
        _TICK_CACHE["co"] = co_residency_context(config)
    return _TICK_CACHE["co"]


def _load_config(bus_root: Path) -> dict:
    try:
        import yaml
    except ImportError:
        return {"_error": "PyYAML unavailable"}
    try:
        data = yaml.safe_load((bus_root / "config.yaml").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — config problems must not kill the daemon
        return {"_error": f"config unreadable: {exc}"}
    return data if isinstance(data, dict) else {"_error": "config malformed"}


# ------------------------------------------------------------------ sensing


def _lane_snapshot() -> dict:
    """Occupancy per lane. Fail-safe: anything unknown counts as busy.

    TEST SEAM. `SESSION_BUS_LANE_SNAPSHOT_JSON` substitutes the whole snapshot.
    This exists because probing real host state makes a test both slow (~2s per
    tick) and flaky by construction — a test whose expected result depends on
    whether a role happens to be serving right now is a test that will lie to you
    eventually. It already did once today, on the drop_caches guard. Production
    never sets this variable.
    """
    override = os.environ.get("SESSION_BUS_LANE_SNAPSHOT_JSON")
    if override:
        try:
            faked = json.loads(override)
            faked.setdefault("ts", _utcnow_iso())
            faked.setdefault("none_busy", False)
            faked["_test_seam"] = True
            return faked
        except json.JSONDecodeError:
            pass   # malformed override -> fall through to a real probe

    snapshot: dict[str, Any] = {"ts": _utcnow_iso()}

    load_class = None
    try:
        from scripts.coordination.inference_load_check import classify_load
        # NB: the key is `state` (quiet | serial_ok | busy), not `class`. Reading
        # the wrong key returns None, which fail-safes to busy — correct in
        # direction but permanently wrong, so the daemon would never advise.
        load_class = (classify_load() or {}).get("state")
    except Exception as exc:  # noqa: BLE001
        snapshot["cpu_error"] = str(exc)

    gpu_busy = None
    try:
        from scripts.coordination.inference_load_check import mi210_state
        gpu = mi210_state() or {}
        gpu_busy = gpu.get("occupied")
        snapshot["gpu_signal"] = gpu
    except Exception as exc:  # noqa: BLE001
        snapshot["gpu_error"] = str(exc)

    snapshot["load_class"] = load_class
    snapshot["cpu_busy"] = (
        _UNKNOWN_IS_BUSY if load_class is None else load_class in _BUSY_LOAD_CLASSES
    )
    snapshot["gpu_busy"] = _UNKNOWN_IS_BUSY if gpu_busy is None else bool(gpu_busy)
    snapshot["none_busy"] = False  # lane:none is always schedulable by definition
    return snapshot


def _agent_states(bus_root: Path, roster: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for entry in roster:
        aid = str(entry.get("id", "")).strip()
        if not aid:
            continue
        hb_path = bus_root / "heartbeats" / f"{aid}.json"
        try:
            hb = json.loads(hb_path.read_text(encoding="utf-8"))
            age = max(0.0, time.time() - hb_path.stat().st_mtime)
        except Exception:  # noqa: BLE001
            hb, age = {}, None
        out[aid] = {"state": hb.get("state"), "task_id": hb.get("task_id"),
                    "age_s": age, "lanes": entry.get("lanes") or [],
                    "role": entry.get("role")}
    return out


# -------------------------------------------------------------- eligibility


def _gates_granted(row: dict, token_text: str) -> bool:
    """A gate is granted when its id appears on a ticked checkbox line."""
    for gate in row.get("operator_gates") or []:
        granted = any(
            gate in line and line.lstrip().startswith("- [x]")
            for line in token_text.splitlines()
        )
        if not granted:
            return False
    return True


def _eligible(row: dict, latest: dict[str, dict], snapshot: dict, token_text: str,
              co_ctx: dict | None = None) -> tuple[bool, str]:
    if row.get("revoking"):
        return False, "lease is being handed back (draining) — not re-assignable while held"
    if row.get("status") != "READY":
        return False, f"status={row.get('status')}"
    for dep in row.get("depends_on") or []:
        dep_row = latest.get(dep)
        if not dep_row or dep_row.get("status") not in {"DONE_PASS", "DONE_MARGINAL_OBS"}:
            return False, f"dependency {dep} not terminal-success"
    if not _gates_granted(row, token_text):
        return False, "operator_gates not GRANTED"
    # R9: a tail-replayable result is obtained by deterministically rescoring
    # banked outputs, so it occupies no lane and needs no claim. Gating it on
    # lane occupancy would queue work that cannot possibly contend.
    if row.get("replay_eligible"):
        return True, "eligible (replay_eligible — no lane, no claim needed)"
    # R3: measured per-role-pair co-residency, not just binary lane occupancy.
    if co_ctx is not None:
        ok, why = _co_residency_verdict(row, co_ctx)
        if not ok:
            return False, why
    lane = row.get("lane")
    if lane in {"cpu", "gpu"} and snapshot.get(f"{lane}_busy"):
        return False, f"lane {lane} busy (load_class={snapshot.get('load_class')})"
    if row.get("contention_class") == "exclusive-contiguous" and snapshot.get("cpu_busy"):
        return False, "exclusive-contiguous needs a quiet host"
    return True, "eligible"


_ORCH_ROOT = Path("/mnt/raid0/llm/epyc-orchestrator")

# R3: the bus REFERENCED the measured contention matrix in config but never
# consulted it — eligibility only asked the binary question "is the lane busy".
# That is strictly weaker than what the orchestrator already knows: the matrix
# records per-role-PAIR measured throughput ratios with allow/borderline/block
# verdicts. A task can be blocked from co-running with a specific live role even
# when the lane is not saturated.
#
# NOTE ON AXES. `contention_class` (exclusive-contiguous | resumable) is a
# PAUSABILITY axis introduced by R5. Co-residency compatibility is a different,
# role-pair axis. The rider text originally conflated them ("promote declared
# classes toward measured ones"); they are orthogonal and are now kept separate.
# `role_affinity` is the field that maps a task onto the matrix's axis.
_TRAFFIC_BY_PRIORITY_CLASS = {
    "production-live": "foreground_interactive",
    "operator-directed": "foreground_specialist",
    "background-churn": "background",
}


def _load_matrix_machinery():
    """Import the orchestrator's matrix API. Never reimplement it (R3)."""
    if str(_ORCH_ROOT) not in sys.path:
        sys.path.insert(0, str(_ORCH_ROOT))
    from src.scheduling.contention import (  # noqa: PLC0415
        MatrixStatus, PairDecision, TrafficClass, load_contention_matrix, matrix_status, pair_policy,
    )
    from src.runtime.cpu_region_lock import active_region_holders  # noqa: PLC0415
    return dict(MatrixStatus=MatrixStatus, PairDecision=PairDecision, TrafficClass=TrafficClass,
                load=load_contention_matrix, status=matrix_status, policy=pair_policy,
                holders=active_region_holders)


def co_residency_context(config: dict) -> dict:
    """Live role holders + matrix health, computed once per tick."""
    co = config.get("co_residency") or {}
    ctx: dict[str, Any] = {"available": False, "live_roles": [], "matrix_status": None,
                           "expected_topology_hash": co.get("expected_topology_hash"),
                           "on_mismatch": co.get("on_topology_mismatch", "refuse")}
    try:
        api = _load_matrix_machinery()
    except Exception as exc:  # noqa: BLE001
        ctx["error"] = f"matrix API unavailable: {exc}"
        return ctx
    try:
        status = api["status"](current_topology_hash=ctx["expected_topology_hash"])
        ctx["matrix_status"] = str(getattr(status, "value", status))
        ctx["live_roles"] = sorted(api["holders"]().keys())
        if ctx["matrix_status"] == "ok":
            ctx["matrix"] = api["load"]()
            ctx["available"] = True
        ctx["api"] = api
    except Exception as exc:  # noqa: BLE001
        ctx["error"] = f"matrix probe failed: {exc}"
    return ctx


def _co_residency_verdict(row: dict, ctx: dict) -> tuple[bool, str]:
    """(ok, reason) for one task against everything currently decoding.

    Fail-closed for tasks that DECLARE a role_affinity when the matrix cannot be
    trusted (fabric axiom 3, and config's on_topology_mismatch: refuse). Tasks
    with no role_affinity are unaffected — there is nothing to look up, so
    refusing them would be a guess dressed as a guard.
    """
    role = row.get("role_affinity")
    if not role:
        return True, "no role_affinity — co-residency not applicable"
    if not ctx.get("available"):
        detail = ctx.get("error") or f"matrix status={ctx.get('matrix_status')}"
        if ctx.get("on_mismatch") == "refuse":
            return False, f"co-residency unverifiable ({detail}) and policy is refuse"
        return True, f"co-residency unverifiable ({detail}) but policy is permit"
    api, matrix = ctx["api"], ctx["matrix"]
    traffic = _TRAFFIC_BY_PRIORITY_CLASS.get(row.get("priority_class"), "background")
    for live in ctx["live_roles"]:
        if live == role:
            continue  # same-role co-residency has its own certification path
        pair = matrix.get_pair(role, live)
        # DELIBERATE DIVERGENCE FROM THE ORCHESTRATOR. pair_policy() returns
        # `allow` for an UNMEASURED pair at foreground traffic — sensible there,
        # where a real request is waiting and starving it on missing data would
        # be worse. The bus carries no SLO: its work is background orchestration
        # with nobody waiting, so fabric axiom 3 governs instead — unverifiable
        # means excluded, not permitted. Admitting an unmeasured pair here is
        # exactly the silently-wrong-policy failure the R3 guard exists to stop,
        # one level down.
        if pair is None:
            return False, (f"co-residency UNMEASURED: no matrix entry for ({role}, live {live}). "
                           f"Axiom 3 — unverifiable is excluded, not permitted. Measure the pair "
                           f"via scripts/server/contention_matrix.py, or drop role_affinity if "
                           f"this task genuinely does not contend.")
        try:
            decision = api["policy"](role, live, traffic, matrix)
        except Exception as exc:  # noqa: BLE001
            return False, f"pair_policy({role},{live}) failed: {exc}"
        value = str(getattr(decision, "value", decision))
        if value in {"block", "queue"}:
            return False, (f"measured co-residency: {role} vs live {live} -> {value}, "
                           f"measured ratio {pair.ratio} (traffic={traffic})")
        if value == "degraded_allow":
            return True, (f"co-residency degraded_allow: {role} vs live {live}, "
                          f"ratio {pair.ratio} (traffic={traffic}) — admitted under SLO override, "
                          f"flag it in the run's attribution")
    return True, "co-residency clear against all live roles"


_PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def _pick(rows: list[dict]) -> Optional[dict]:
    if not rows:
        return None
    return sorted(rows, key=lambda r: (_PRIORITY_RANK.get(r.get("priority"), 9),
                                       str(r.get("task_id"))))[0]


def compute_advice(bus_root: Path, config: dict, epoch: int) -> list[dict]:
    """What the daemon WOULD do this tick. Pure — writes nothing."""
    roster = [r for r in (config.get("roster") or []) if isinstance(r, dict)]
    latest = fold_queue(bus_root)
    snapshot = lane_snapshot_cached()
    co_ctx = co_residency_cached(config)
    agents = _agent_states(bus_root, roster)
    try:
        token_text = (bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        token_text = ""

    busy_owners = {
        r.get("owner") for r in latest.values()
        if r.get("status") in {"ASSIGNED", "CLAIMED", "RUNNING"} and r.get("owner")
    }

    advice: list[dict] = [{
        "schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
        "kind": "saturation", "lanes": {
            "cpu": "busy" if snapshot["cpu_busy"] else "idle",
            "gpu": "busy" if snapshot["gpu_busy"] else "idle",
            "none": "idle",
        },
        "load_class": snapshot.get("load_class"),
        "co_residency": {"matrix_status": co_ctx.get("matrix_status"),
                         "live_roles": co_ctx.get("live_roles"),
                         "available": co_ctx.get("available"),
                         "error": co_ctx.get("error")},
        "queue_depth": len(latest),
        "ready_depth": sum(1 for r in latest.values() if r.get("status") == "READY"),
    }]

    # A task advised to one agent must not be advised to another in the same
    # tick. Harmless while advisory, a double-assignment once M4 has authority —
    # and misleading either way, since the advice is read as a plan.
    claimed_this_tick: set[str] = set()

    for aid, agent in agents.items():
        if agent.get("role") == "coordinator-agent":
            continue  # the judgment tier is not scheduled by the daemon
        if aid in busy_owners:
            advice.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                           "epoch": epoch, "kind": "would-skip", "agent": aid,
                           "reason": "already holds a live ASSIGNED/CLAIMED/RUNNING task"})
            continue
        candidates, rejections = [], []
        for row in latest.values():
            if row.get("task_id") in claimed_this_tick:
                continue
            ok, why = _eligible(row, latest, snapshot, token_text, co_ctx)
            if not ok:
                if row.get("status") == "READY":
                    rejections.append({"task_id": row.get("task_id"), "reason": why})
                continue
            if row.get("lane") not in (agent.get("lanes") or []):
                rejections.append({"task_id": row.get("task_id"),
                                   "reason": f"lane {row.get('lane')} not in {aid} roster lanes"})
                continue
            candidates.append(row)
        pick = _pick(candidates)
        if pick:
            claimed_this_tick.add(str(pick.get("task_id")))
        advice.append({
            "schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
            "kind": "would-assign" if pick else "would-idle",
            "agent": aid,
            "task_id": (pick or {}).get("task_id"),
            "priority": (pick or {}).get("priority"),
            "lane": (pick or {}).get("lane"),
            "routing_annotation": (pick or {}).get("routing_annotation"),
            "considered": len(candidates),
            "rejected": rejections[:8],
        })
    return advice


# ------------------------------------------------------------------- daemon


# =========================================================================== M4
#
# Assignment authority. Everything below WRITES to files the daemon owns
# (queue.jsonl, inbox/*, tokens/token-queue.md) and therefore runs ONLY when
# `coordinator_daemon.authority == "assign"`. In manual/advisory mode the daemon
# still writes exactly two files, which is the property M3 verified — flipping
# authority is the single switch, and setting it back to `advisory` is the
# documented rollback.
#
# ALL OF THIS IS BOOKKEEPING, NOT JUDGMENT. Transcription is derived
# deterministically from what agents reported; the daemon never decides whether
# work was done well. It is also STATELESS AND IDEMPOTENT: rather than tracking
# which outbox messages it has consumed (which would need daemon-owned cursors on
# files it does not own), it compares the latest report per task against the queue
# and appends only when they disagree. Re-running a tick therefore cannot
# double-apply.

_ACK_IMPLIES = {"ASSIGNED": "CLAIMED"}
_STATUS_IMPLIES = {"CLAIMED": "RUNNING", "ASSIGNED": "RUNNING"}


def _outbox_reports(bus_root: Path, roster: list[dict]) -> dict[str, list[dict]]:
    """task_id -> its messages, in file order, across every agent outbox."""
    reports: dict[str, list[dict]] = {}
    for entry in roster:
        aid = str(entry.get("id", "")).strip()
        if not aid:
            continue
        rows, _ = _read_jsonl(bus_root / "outbox" / f"{aid}.jsonl")
        for row in rows:
            tid = row.get("task_id")
            if tid:
                reports.setdefault(tid, []).append(row)
    return reports


def transcribe(latest: dict[str, dict], reports: dict[str, list[dict]], epoch: int) -> list[dict]:
    """Queue rows implied by agent reports but not yet reflected in the queue."""
    out: list[dict] = []
    for tid, msgs in reports.items():
        row = latest.get(tid)
        if not row or row.get("status") in TERMINAL_STATES:
            continue
        status = row.get("status")
        base = {k: row.get(k) for k in ("lane", "gating", "owner", "priority", "priority_class",
                                        "contention_class", "role_affinity", "spec_ref",
                                        "est_wall_clock_h", "operator_gates", "depends_on",
                                        "max_attempts", "attempt", "replay_eligible")
                if row.get(k) is not None}
        kinds = [m.get("kind") for m in msgs]

        if "task-complete" in kinds:
            done = [m for m in msgs if m.get("kind") == "task-complete"][-1]
            outcome = str((done.get("payload") or {}).get("outcome", "")).lower()
            new = {"pass": "DONE_PASS", "marginal": "DONE_MARGINAL_OBS"}.get(outcome, "FAILED")
            if status != new:
                out.append({**base, "schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(),
                            "task_id": tid, "status": new, "epoch": epoch,
                            **({"failure_reason": str((done.get("payload") or {}).get("reason", ""))}
                               if new == "FAILED" and (done.get("payload") or {}).get("reason") else {})})
            continue

        target = status
        if "ack" in kinds:
            target = _ACK_IMPLIES.get(target, target)
        if "status" in kinds:
            target = _STATUS_IMPLIES.get(target, target)
        if target != status:
            out.append({**base, "schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(),
                        "task_id": tid, "status": target, "epoch": epoch,
                        "claim_ts": _utcnow_iso() if target == "CLAIMED" else row.get("claim_ts")})
    return [{k: v for k, v in r.items() if v is not None} for r in out]


def relay_tokens(bus_root: Path, reports: dict[str, list[dict]], latest: dict[str, dict],
                 epoch: int) -> tuple[list[str], list[dict]]:
    """Relay token-request blocks into the token queue, verbatim.

    The daemon relays; the coordinator-agent presents; ONLY the operator flips a
    checkbox. Idempotent on gate_id: a gate already present is never re-appended,
    so a repeated tick cannot duplicate a block. Pre-validation is the requesting
    agent's duty — a request lacking dry-run evidence is a DEFECT, not something
    to quietly relay, because presenting a command that fails is an agent defect
    by policy.
    """
    tq = bus_root / "tokens" / "token-queue.md"
    existing = tq.read_text(encoding="utf-8") if tq.exists() else ""
    blocks: list[str] = []
    rows: list[dict] = []
    defects: list[dict] = []

    for tid, msgs in reports.items():
        for msg in msgs:
            if msg.get("kind") != "token-request":
                continue
            payload = msg.get("payload") or {}
            gate = payload.get("gate_id")
            if not gate:
                continue
            validated = payload.get("validated") or {}
            if not validated.get("cmd") or validated.get("dry_run_exit") is None:
                defects.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                                "epoch": epoch, "kind": "defect", "check": "token-prevalidation",
                                "subject": msg.get("from"),
                                "detail": f"token-request {gate} lacks dry-run evidence; "
                                          f"presenting an unvalidated command is an agent defect"})
                continue
            if gate in existing:
                continue
            blocks.append(
                f"\n### {gate}\n\n"
                f"- [ ] **{gate}** — requested by `{msg.get('from')}` for task `{tid}`\n"
                f"  - block ref: `{payload.get('block_ref', '-')}`\n"
                f"  - command (pre-validated, dry-run exit "
                f"`{validated.get('dry_run_exit')}`):\n"
                f"    ```\n    {validated.get('cmd')}\n    ```\n"
                f"  - dry-run evidence: {validated.get('dry_run_evidence')}\n"
            )
            row = latest.get(tid)
            if row and row.get("status") not in TERMINAL_STATES and row.get("status") != "HELD_OP_GATE":
                rows.append({"schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(),
                             "task_id": tid, "status": "HELD_OP_GATE",
                             "lane": row.get("lane"), "gating": row.get("gating"),
                             "epoch": epoch, "owner": row.get("owner"),
                             "operator_gates": sorted(set((row.get("operator_gates") or []) + [gate]))})
    return blocks, rows + defects


def process_revocations(config: dict, latest: dict[str, dict], reports: dict[str, list[dict]],
                        epoch: int) -> dict:
    """R4 — lease revocation, always quiesce-and-drain, never forcible.

    A held `flock` cannot be revoked by a third party and axiom 4 forbids
    mid-decode preemption, so revocation is COOPERATIVE: the daemon marks the
    queue row `revoking` and nudges the holder, which stops accepting new work and
    releases at its next boundary. The advisory layer never claims to be the
    liveness truth — the flock remains that.

    Authority is checked against `authority.lease_grant`. An unauthorised sender
    is rejected with a defect rather than obeyed; that check is deterministic, so
    the daemon making it does not stray into judgment.

    A revocation the holder IGNORES surfaces as a defect via the normal stall
    ladder (its lease still expires), never as a silent inconsistency.
    """
    allowed = set((config.get("authority") or {}).get("lease_grant")
                  or ["operator", "coordinator-agent"])
    queue_rows: list[dict] = []
    nudges: list[dict] = []
    advisory: list[dict] = []

    for tid, msgs in reports.items():
        for msg in msgs:
            if msg.get("kind") != "lease-revoke":
                continue
            sender = msg.get("from")
            if sender not in allowed:
                advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                                 "epoch": epoch, "kind": "defect", "check": "lease-authority",
                                 "subject": sender,
                                 "detail": f"{sender!r} requested revocation of {tid} but "
                                           f"lease_grant authority is {sorted(allowed)}"})
                continue
            row = latest.get(tid)
            if not row or row.get("status") not in {"ASSIGNED", "CLAIMED", "RUNNING"}:
                advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                                 "epoch": epoch, "kind": "would-skip", "agent": sender,
                                 "task_id": tid,
                                 "reason": f"revocation ignored: status={row.get('status') if row else 'absent'}"})
                continue
            if row.get("revoking"):
                continue                              # idempotent
            payload = msg.get("payload") or {}
            queue_rows.append({
                "schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(), "task_id": tid,
                "status": row.get("status"), "lane": row.get("lane"), "gating": row.get("gating"),
                "epoch": epoch, "owner": row.get("owner"), "revoking": True,
                "lease_expires_ts": row.get("lease_expires_ts"),
                "attempt": row.get("attempt"), "priority": row.get("priority")})
            nudges.append({"to": row.get("owner"), "kind": "nudge", "task_id": tid,
                           "corr_id": f"revoke-{tid}-{epoch}",
                           "payload": {"reason": "lease-revoke — quiesce and drain",
                                       "detail": payload.get("reason"),
                                       "yield_to": payload.get("yield_to"),
                                       "instruction": ("stop accepting new work for this task, "
                                                       "release at your next boundary, and "
                                                       "continue immediately on lane:none work — "
                                                       "do not idle and do not abort mid-unit")}})
            advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                             "epoch": epoch, "kind": "lease-revoking", "agent": row.get("owner"),
                             "task_id": tid, "detail": payload.get("reason")})
    return {"queue_rows": queue_rows, "nudges": nudges, "advisory": advisory}


def intake_proposals(bus_root: Path, latest: dict[str, dict], reports: dict[str, list[dict]],
                     epoch: int) -> tuple[list[dict], list[dict]]:
    """Turn `task-propose` messages into READY queue rows (returns rows, advisory).

    This is how work ENTERS the queue. Agents never write `queue.jsonl`; they
    propose from their own outbox and the daemon transcribes — bookkeeping, not
    judgment, so the daemon stays inside its bright line.

    Idempotent on `task_id`: a proposal for a task already in the queue is
    skipped, so re-running intake cannot duplicate or resurrect anything. That
    matters because a completed task must NOT be re-created by an old proposal
    still sitting in an outbox.

    Deliberately NOT part of the tick loop. Intake writes `queue.jsonl`, which
    would break the advisory-mode invariant M3 verified (exactly two files). It is
    a one-shot the operator or an agent invokes: `session_bus_coordinator.py
    intake`. Seeding the queue is a decision, not something a daemon should start
    doing on its own.
    """
    rows: list[dict] = []
    advisory: list[dict] = []
    seen: set[str] = set()
    for tid, msgs in reports.items():
        for msg in msgs:
            if msg.get("kind") != "task-propose":
                continue
            if tid in latest:
                advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                                 "epoch": epoch, "kind": "would-skip", "task_id": tid,
                                 "reason": f"proposal ignored: already in the queue as "
                                           f"{latest[tid].get('status')}"})
                continue
            if tid in seen:
                continue
            seen.add(tid)
            pl = msg.get("payload") or {}
            row = {"schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(), "task_id": tid,
                   "status": "READY", "lane": pl.get("lane"), "gating": pl.get("gating"),
                   "epoch": epoch, "origin": f"proposed-by:{msg.get('from')}",
                   "spec_ref": pl.get("spec_ref")}
            for key in ("priority", "priority_class", "contention_class", "role_affinity",
                        "est_wall_clock_h", "replay_eligible"):
                if pl.get(key) is not None:
                    row[key] = pl[key]
            rows.append(row)
            advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                             "epoch": epoch, "kind": "intake", "task_id": tid,
                             "detail": f"lane={pl.get('lane')} gating={pl.get('gating')} "
                                       f"classification={pl.get('classification', 'unstated')}"})
    return rows, advisory


def cmd_intake(args: argparse.Namespace) -> int:
    """One-shot: transcribe task proposals into READY queue rows."""
    bus_root = Path(args.bus_root)
    config = _load_config(bus_root)
    roster = [r for r in (config.get("roster") or []) if isinstance(r, dict)]
    reports = _outbox_reports(bus_root, roster)
    latest = fold_queue(bus_root)
    epoch = _read_epoch(bus_root)
    rows, advisory = intake_proposals(bus_root, latest, reports, epoch)

    if args.dry_run:
        print(f"would admit {len(rows)} task(s):")
        for r in rows:
            print(f"  {r['task_id']:<44} lane={r.get('lane'):<5} gating={r.get('gating'):<5} "
                  f"{r.get('priority', '-')}")
        skips = [a for a in advisory if a["kind"] == "would-skip"]
        for s in skips:
            print(f"  skip {s['task_id']:<44} {s['reason']}")
        return 0

    for row in rows:
        _append_jsonl(bus_root / "queue.jsonl", row)
    if advisory:
        _append_advisory(bus_root, advisory)
    print(f"admitted {len(rows)} task(s); "
          f"{len([a for a in advisory if a['kind'] == 'would-skip'])} already present")
    return 0


def _class_precedence(config: dict) -> dict[str, set[str]]:
    """{class: set of classes it yields to} from the priority_classes artifact."""
    out: dict[str, set[str]] = {}
    for entry in config.get("priority_classes") or []:
        if isinstance(entry, dict) and entry.get("name"):
            out[entry["name"]] = set(entry.get("yields_to") or [])
    return out


def auto_yield(config: dict, latest: dict[str, dict], snapshot: dict, token_text: str,
               co_ctx: dict, epoch: int) -> dict:
    """R5 — a higher-priority CLASS arriving preempts a lower one, by drain.

    This is the *deterministic* trigger R4 permits the daemon to pull: precedence
    comes straight from the `priority_classes` artifact, so no discretion is
    exercised. Discretionary revocation remains coordinator-agent's.

    Two guards keep it from thrashing:

      1. The waiting task must be eligible **but for the lane**. Draining a lane
         for a task that is also blocked on an ungranted gate or an unmet
         dependency would be pure churn — the lane would sit idle and the task
         still could not run. We re-test eligibility against a snapshot with that
         lane free; only if it then passes is the yield justified.
      2. At most one revocation per lane per tick, so a burst of high-class work
         cannot drain every holder simultaneously.
    """
    precedence = _class_precedence(config)
    if not precedence:
        return {"queue_rows": [], "nudges": [], "advisory": []}

    queue_rows: list[dict] = []
    nudges: list[dict] = []
    advisory: list[dict] = []
    lanes_yielded: set[str] = set()

    waiting = sorted((r for r in latest.values()
                      if r.get("status") == "READY" and not r.get("revoking")),
                     key=lambda r: (_PRIORITY_RANK.get(r.get("priority"), 9), str(r.get("task_id"))))
    live = [r for r in latest.values()
            if r.get("status") in {"ASSIGNED", "CLAIMED", "RUNNING"} and not r.get("revoking")]

    for want in waiting:
        lane = want.get("lane")
        if lane in {None, "none"} or lane in lanes_yielded:
            continue
        want_class = want.get("priority_class")
        if not want_class:
            continue

        # Guard 1: would it actually run if the lane were free?
        free_snapshot = {**snapshot, f"{lane}_busy": False, "cpu_busy": False}
        ok, why = _eligible(want, latest, free_snapshot, token_text, co_ctx)
        if not ok:
            advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                             "epoch": epoch, "kind": "would-skip",
                             "task_id": want.get("task_id"),
                             "reason": f"no auto-yield: blocked for another reason too ({why})"})
            continue

        for holder in live:
            if holder.get("lane") != lane:
                continue
            holder_class = holder.get("priority_class")
            if not holder_class or want_class not in precedence.get(holder_class, set()):
                continue
            queue_rows.append({
                "schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(),
                "task_id": holder["task_id"], "status": holder.get("status"),
                "lane": lane, "gating": holder.get("gating"), "epoch": epoch,
                "owner": holder.get("owner"), "revoking": True,
                "lease_expires_ts": holder.get("lease_expires_ts"),
                "attempt": holder.get("attempt"), "priority": holder.get("priority")})
            nudges.append({"to": holder.get("owner"), "kind": "nudge",
                           "task_id": holder["task_id"],
                           "corr_id": f"autoyield-{holder['task_id']}-{epoch}",
                           "payload": {"reason": "auto-yield to a higher priority class",
                                       "yield_to": want.get("task_id"),
                                       "detail": f"{holder_class} yields to {want_class}",
                                       "instruction": ("quiesce and release at your next boundary, "
                                                       "then continue on lane:none work — do not "
                                                       "idle and do not abort mid-unit")}})
            advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                             "epoch": epoch, "kind": "auto-yield",
                             "agent": holder.get("owner"), "task_id": holder["task_id"],
                             "detail": f"{holder_class} yields lane {lane} to "
                                       f"{want.get('task_id')} ({want_class})"})
            lanes_yielded.add(lane)
            break
    return {"queue_rows": queue_rows, "nudges": nudges, "advisory": advisory}


def settle_drained(latest: dict[str, dict], agents: dict[str, dict], epoch: int) -> list[dict]:
    """A revoking task whose holder now reports `draining` has released its lease.

    Returns it to READY with the owner cleared, so the ordinary priority-ordered
    assignment pass re-grants it when it is next eligible. That IS R4's
    "deterministic re-grant trigger" — no separate mechanism is needed, and the
    daemon exercises no discretion in choosing when.
    """
    out: list[dict] = []
    for tid, row in latest.items():
        if not row.get("revoking") or row.get("status") in TERMINAL_STATES:
            continue
        holder = row.get("owner")
        state = (agents.get(holder) or {}).get("state")
        if state != "draining":
            continue
        out.append({"schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(), "task_id": tid,
                    "status": "READY", "lane": row.get("lane"), "gating": row.get("gating"),
                    "epoch": epoch, "owner": None, "revoking": False,
                    "priority": row.get("priority"), "attempt": row.get("attempt"),
                    "failure_reason": "lease released on revocation (drained at boundary)"})
    return out


def stall_ladder(bus_root: Path, latest: dict[str, dict], agents: dict[str, dict],
                 reports: dict[str, list[dict]], config: dict, epoch: int) -> dict:
    """soft-stall -> nudge; hard-stall (lease expired) -> requeue + defect; give-up -> alert.

    Grace is lane-tuned: silence on a bench lane is not a stall, so a cpu/gpu
    task's grace derives from `est_wall_clock_h * bench_grace_margin` while
    `lane: none` uses the flat `none_lane_grace_s`.
    """
    leases = config.get("leases") or {}
    none_grace = float(leases.get("none_lane_grace_s", 900))
    margin = float(leases.get("bench_grace_margin", 1.5))
    now = datetime.now(timezone.utc)

    nudges: list[dict] = []
    queue_rows: list[dict] = []
    advisory: list[dict] = []
    alerts: list[str] = []

    for tid, row in latest.items():
        if row.get("status") not in {"ASSIGNED", "CLAIMED", "RUNNING"}:
            continue
        owner = row.get("owner")
        if not owner:
            continue
        agent = agents.get(owner) or {}

        expired = False
        exp = row.get("lease_expires_ts")
        if exp:
            try:
                expired = datetime.fromisoformat(str(exp)) < now
            except ValueError:
                expired = False

        if row.get("lane") in {"cpu", "gpu"} and row.get("est_wall_clock_h"):
            grace = float(row["est_wall_clock_h"]) * 3600.0 * margin
        else:
            grace = float(row.get("heartbeat_grace_s") or none_grace)
        hb_age = agent.get("age_s")
        hb_stale = hb_age is None or hb_age > grace
        # Recent outbox traffic disproves a stall regardless of heartbeat age.
        talking = bool(reports.get(tid))

        if expired:
            attempt = int(row.get("attempt") or 0) + 1
            max_attempts = int(row.get("max_attempts") or 3)
            if attempt > max_attempts:
                alerts.append(
                    f"\n- [ ] **GIVE-UP {tid}** — lease expired after {attempt - 1} attempt(s), "
                    f"owner `{owner}`. The coordinator-daemon does not decide what happens next; "
                    f"this is an operator/coordinator-agent call.\n")
                queue_rows.append({"schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(),
                                   "task_id": tid, "status": "INFRA_BLOCKED",
                                   "lane": row.get("lane"), "gating": row.get("gating"),
                                   "epoch": epoch, "attempt": attempt,
                                   "failure_reason": "attempts exhausted after lease expiry"})
            else:
                queue_rows.append({"schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(),
                                   "task_id": tid, "status": "STALE_REQUEUED",
                                   "lane": row.get("lane"), "gating": row.get("gating"),
                                   "epoch": epoch, "owner": None, "attempt": attempt,
                                   "failure_reason": "lease expired"})
                advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                                 "epoch": epoch, "kind": "defect", "check": "hard-stall",
                                 "subject": owner,
                                 "detail": f"task {tid} lease expired; requeued as attempt "
                                           f"{attempt}/{max_attempts}"})
        elif hb_stale and not talking:
            nudges.append({"to": owner, "kind": "nudge", "task_id": tid,
                           "corr_id": f"nudge-{tid}-{epoch}",
                           "payload": {"reason": "soft-stall",
                                       "heartbeat_age_s": hb_age,
                                       "grace_s": grace}})
    return {"nudges": nudges, "queue_rows": queue_rows, "advisory": advisory, "alerts": alerts}


def audit(bus_root: Path, epoch: int) -> list[dict]:
    """R7 defect attribution — the daemon auditing the agent tier.

    Emits ONLY mechanically checkable findings. Anything requiring judgment
    belongs to a human, not here: the daemon that starts interpreting work is a
    second main.

    A note on what is deliberately NOT a defect. Two of R7's candidate checks —
    "commit without a preceding fetch" and "wholesale `git add`" — are not
    reliably decidable after the fact, and a commit touching a human-only path
    cannot be attributed to agent-vs-operator at all, because every session
    commits under one git identity. Those are emitted as `observation`, not
    `defect`, so a clean audit is never mistaken for full coverage. Preventing
    them belongs in a pre-commit hook, where the actor is still known.
    """
    findings: list[dict] = []

    def add(kind: str, check: str, subject: str, detail: str) -> None:
        findings.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                         "kind": kind, "check": check, "subject": subject, "detail": detail})

    # --- hard, mechanical: trust-boundary pin -------------------------------
    try:
        from scripts.coordination.session_bus import check_trust_boundary_pin
        for problem in check_trust_boundary_pin(bus_root):
            add("defect", "trust-boundary-pin", "coordinator-agent", problem)
    except Exception as exc:  # noqa: BLE001
        add("observation", "trust-boundary-pin", "coordinator-daemon",
            f"pin check unavailable: {exc}")

    # --- hard, mechanical: single-writer ownership --------------------------
    for path in sorted((bus_root / "outbox").glob("*.jsonl")):
        owner = path.stem
        rows, _ = _read_jsonl(path)
        for i, row in enumerate(rows, 1):
            if row.get("from") != owner:
                add("defect", "single-writer", owner,
                    f"outbox/{path.name}:{i} carries from={row.get('from')!r} but this file's "
                    f"only writer is {owner!r}")

    # --- observation: human-only paths touched by recent commits ------------
    try:
        import subprocess
        gate = bus_root / "human_only_paths.yaml"
        globs = []
        if gate.exists():
            for line in gate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("glob:"):
                    globs.append(line.split(":", 1)[1].strip().strip('"'))
        if globs:
            changed = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "log", "--name-only", "--pretty=format:", "-20"],
                capture_output=True, text=True, timeout=15,
            ).stdout.split()
            hits = sorted({g for g in globs for c in changed if c == g})
            for hit in hits:
                add("observation", "human-only-path-touched", hit,
                    "a commit in the last 20 touched a human-only path. NOT a defect: all "
                    "sessions share one git identity, so this cannot be attributed to an agent "
                    "rather than the operator. Confirm it was an operator/ratify-script apply.")
    except Exception as exc:  # noqa: BLE001
        add("observation", "human-only-path-touched", "-", f"git inspection unavailable: {exc}")

    return findings


def _heartbeat_path(bus_root: Path) -> Path:
    return bus_root / "heartbeats" / f"{COORDINATOR_DAEMON}.json"


def _read_epoch(bus_root: Path) -> int:
    try:
        return int(json.loads(_heartbeat_path(bus_root).read_text(encoding="utf-8")).get("epoch", 0))
    except Exception:  # noqa: BLE001
        return 0


def _write_heartbeat(bus_root: Path, epoch: int, state: str, note: str = "") -> None:
    _write_atomic(_heartbeat_path(bus_root), {
        "agent": COORDINATOR_DAEMON, "state": state, "task_id": None,
        "ts": _utcnow_iso(), "epoch": epoch, "note": note, "pid": os.getpid(),
    })


def _append_advisory(bus_root: Path, rows: list[dict]) -> None:
    path = bus_root / "advisory.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _authority(config: dict) -> str:
    return str((config.get("coordinator_daemon") or {}).get("authority", "manual")).strip()


def _append_inbox(bus_root: Path, msgs: list[dict], epoch: int) -> list[dict]:
    """Deliver messages to recipient inboxes (daemon-owned). Returns what it wrote."""
    written = []
    for msg in msgs:
        to = msg.get("to")
        if not to:
            continue
        path = bus_root / "inbox" / f"{to}.jsonl"
        existing, _ = _read_jsonl(path)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        full = {"schema_version": MSG_SCHEMA_VERSION, "ts": _utcnow_iso(),
                "from": COORDINATOR_DAEMON,
                "id": f"msg-{stamp}-{len(existing) + 1}-{COORDINATOR_DAEMON}", **msg}
        _append_jsonl(path, full)
        written.append(full)
    return written


def apply_assignment(bus_root: Path, config: dict, epoch: int) -> list[dict]:
    """M4 write path. Runs ONLY under authority: assign.

    Order matters and is deliberate: transcribe what agents already reported
    BEFORE deciding anything, so decisions are made against current truth rather
    than a stale queue; relay tokens next so a newly-gated task is not then
    assigned; run the stall ladder before assigning so a requeued task is
    immediately available; assign last.
    """
    emitted: list[dict] = []
    roster = [r for r in (config.get("roster") or []) if isinstance(r, dict)]
    reports = _outbox_reports(bus_root, roster)

    # 1. transcribe agent reports into the queue (bookkeeping, no judgment)
    latest = fold_queue(bus_root)
    for row in transcribe(latest, reports, epoch):
        _append_jsonl(bus_root / "queue.jsonl", row)
        emitted.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                        "kind": "transcribed", "task_id": row["task_id"], "status": row["status"]})

    # 1b. R4 revocation: mark revoking + nudge the holder to drain, and settle any
    # task whose holder has since reported `draining` back to READY.
    latest = fold_queue(bus_root)
    agents_now = _agent_states(bus_root, roster)

    # R5 auto-yield: a higher priority CLASS waiting on a lane a lower class
    # holds triggers a drain, by deterministic rule from the priority artifact.
    try:
        tok = (bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        tok = ""
    ay = auto_yield(config, latest, lane_snapshot_cached(), tok, co_residency_cached(config), epoch)
    for row in ay["queue_rows"]:
        _append_jsonl(bus_root / "queue.jsonl", row)
    if ay["nudges"]:
        _append_inbox(bus_root, ay["nudges"], epoch)
    emitted.extend(ay["advisory"])

    latest = fold_queue(bus_root)
    rev = process_revocations(config, latest, reports, epoch)
    for row in rev["queue_rows"]:
        _append_jsonl(bus_root / "queue.jsonl", row)
    if rev["nudges"]:
        _append_inbox(bus_root, rev["nudges"], epoch)
    emitted.extend(rev["advisory"])

    latest = fold_queue(bus_root)
    # Tasks released by revocation THIS tick are excluded from this tick's
    # assignment pass. Without that, the task returns to READY and the very next
    # step hands it straight back to the same holder — making the revocation a
    # no-op and the drain pure churn. Skipping one tick lets whatever the lease
    # was yielded TO claim the lane first; if nothing higher-priority
    # materialises, ordinary priority ordering resumes the task next tick, so
    # there is no lasting penalty.
    released_this_tick: set[str] = set()
    for row in settle_drained(latest, agents_now, epoch):
        _append_jsonl(bus_root / "queue.jsonl", row)
        released_this_tick.add(row["task_id"])
        emitted.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                        "kind": "lease-released", "task_id": row["task_id"],
                        "detail": "excluded from this tick's assignment so the yield can land"})

    # 2. relay token-requests; a newly gated task must not be assigned this tick
    latest = fold_queue(bus_root)
    blocks, extra = relay_tokens(bus_root, reports, latest, epoch)
    if blocks:
        tq = bus_root / "tokens" / "token-queue.md"
        with tq.open("a", encoding="utf-8") as fh:
            fh.writelines(blocks)
        emitted.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                        "kind": "tokens-relayed", "count": len(blocks)})
    for item in extra:
        if item.get("kind") == "defect":
            emitted.append(item)
        else:
            _append_jsonl(bus_root / "queue.jsonl", item)
            emitted.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                            "kind": "held-on-gate", "task_id": item["task_id"]})

    # 3. stall ladder
    latest = fold_queue(bus_root)
    agents = _agent_states(bus_root, roster)
    ladder = stall_ladder(bus_root, latest, agents, reports, config, epoch)
    for row in ladder["queue_rows"]:
        _append_jsonl(bus_root / "queue.jsonl", row)
    if ladder["nudges"]:
        _append_inbox(bus_root, ladder["nudges"], epoch)
    if ladder["alerts"]:
        with (bus_root / "tokens" / "token-queue.md").open("a", encoding="utf-8") as fh:
            fh.writelines(ladder["alerts"])
    emitted.extend(ladder["advisory"])

    # 4. real assignment, using the same eligibility the advisory path uses
    latest = fold_queue(bus_root)
    for rec in compute_advice(bus_root, config, epoch):
        if rec.get("kind") != "would-assign" or not rec.get("task_id"):
            continue
        tid, agent = rec["task_id"], rec["agent"]
        if tid in released_this_tick:
            continue
        row = latest.get(tid) or {}
        if row.get("status") != "READY":
            continue
        hold = float((config.get("leases") or {}).get("max_hold_s", 1800))
        expires = datetime.now(timezone.utc) + timedelta(seconds=hold)
        _append_jsonl(bus_root / "queue.jsonl", {
            "schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(), "task_id": tid,
            "status": "ASSIGNED", "lane": row.get("lane"), "gating": row.get("gating"),
            "epoch": epoch, "owner": agent, "priority": row.get("priority"),
            "lease_expires_ts": expires.isoformat(timespec="seconds"),
            "attempt": int(row.get("attempt") or 0)})
        _append_inbox(bus_root, [{"to": agent, "kind": "task-assign", "task_id": tid,
                                  "requires_ack": True, "ack_deadline_s": 600,
                                  "payload": {"lane": row.get("lane"), "epoch": epoch,
                                              "lease_expires_ts": expires.isoformat(timespec="seconds"),
                                              **({"spec_ref": row["spec_ref"]} if row.get("spec_ref") else {})}}],
                      epoch)
        emitted.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                        "kind": "assigned", "agent": agent, "task_id": tid})
        latest = fold_queue(bus_root)
    return emitted


def tick(bus_root: Path, epoch: int, *, dry_run: bool = False) -> list[dict]:
    _reset_tick_cache()   # one consistent host view per tick, probed once
    config = _load_config(bus_root)
    authority = _authority(config)
    advice = compute_advice(bus_root, config, epoch) + audit(bus_root, epoch)
    if authority == "assign" and not dry_run:
        # M4. In manual/advisory mode this branch never runs, so the daemon keeps
        # writing exactly two files — the property M3 verified.
        advice += apply_assignment(bus_root, config, epoch)
    if not dry_run:
        _append_advisory(bus_root, advice)
    return advice


def cmd_once(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    epoch = _read_epoch(bus_root)
    advice = tick(bus_root, epoch, dry_run=args.dry_run)
    for row in advice:
        print(json.dumps(row, sort_keys=True))
    if not args.dry_run:
        _write_heartbeat(bus_root, epoch, "idle", "single tick")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    lock_fh = LOCK_PATH.open("a+b")
    try:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("coordinator-daemon: another instance holds the lock; exiting.", file=sys.stderr)
        return 0

    config = _load_config(bus_root)
    tick_s = float((config.get("coordinator_daemon") or {}).get("tick_s", 45))
    epoch = _read_epoch(bus_root) + 1  # epoch fencing: a restart is a new generation
    _write_heartbeat(bus_root, epoch, "working", f"advisory tick loop, {tick_s}s")
    print(f"coordinator-daemon: epoch={epoch} authority={_authority(config)} tick={tick_s}s",
          file=sys.stderr)

    stopping = {"now": False}

    def _stop(signum, _frame):
        stopping["now"] = True
        print(f"coordinator-daemon: signal {signum}, draining", file=sys.stderr)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while not stopping["now"]:
        started = time.time()
        try:
            tick(bus_root, epoch)
            _write_heartbeat(bus_root, epoch, "working", "advisory")
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001 — a bad tick must not kill the loop
            print(f"coordinator-daemon: tick error: {exc}", file=sys.stderr)
            _write_heartbeat(bus_root, epoch, "working", f"tick error: {exc}")
        slept = 0.0
        while slept < max(1.0, tick_s - (time.time() - started)) and not stopping["now"]:
            time.sleep(0.5)
            slept += 0.5

    _write_heartbeat(bus_root, epoch, "idle", "stopped cleanly")
    print("coordinator-daemon: stopped", file=sys.stderr)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    hb_path = _heartbeat_path(bus_root)
    try:
        hb = json.loads(hb_path.read_text(encoding="utf-8"))
        age = time.time() - hb_path.stat().st_mtime
        print(f"state={hb.get('state')} epoch={hb.get('epoch')} pid={hb.get('pid')} "
              f"age={age:.0f}s note={hb.get('note')!r}")
    except Exception:  # noqa: BLE001
        print("no coordinator-daemon heartbeat")
    rows, _ = _read_jsonl(bus_root / "advisory.jsonl")
    print(f"advisory records: {len(rows)}")
    for row in rows[-5:]:
        print("  " + json.dumps(row, sort_keys=True)[:160])
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="session_bus_coordinator.py",
                                description="Coordinator-daemon (M3: read-only advisory).")
    p.add_argument("--bus-root", default=str(DEFAULT_BUS_ROOT))
    sub = p.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("once", help="run a single tick")
    o.add_argument("--dry-run", action="store_true", help="compute advice, write nothing")
    o.set_defaults(func=cmd_once)

    r = sub.add_parser("run", help="tick loop (flock singleton)")
    r.set_defaults(func=cmd_run)

    s = sub.add_parser("status", help="daemon liveness + recent advice")
    s.set_defaults(func=cmd_status)

    a = sub.add_parser("audit", help="R7 integrity audit only (defects + observations)")
    a.set_defaults(func=cmd_audit)

    i = sub.add_parser("intake", help="one-shot: transcribe task-propose messages into READY rows")
    i.add_argument("--dry-run", action="store_true", help="show what would be admitted")
    i.set_defaults(func=cmd_intake)
    return p


def cmd_audit(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    findings = audit(bus_root, _read_epoch(bus_root))
    defects = [f for f in findings if f["kind"] == "defect"]
    for f in findings:
        marker = "DEFECT " if f["kind"] == "defect" else "observe"
        print(f"  {marker} [{f['check']}] {f['subject']}: {f['detail']}")
    if not findings:
        print("  clean — no mechanical violations")
    print(f"\n{len(defects)} defect(s), {len(findings) - len(defects)} observation(s)")
    return 1 if defects else 0


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
