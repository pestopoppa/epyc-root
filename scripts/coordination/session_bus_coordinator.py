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
import subprocess
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
    validate_row,
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


# C18 (2026-07-29). How long a recipient's heartbeat may be silent before a routed
# message to it is worth warning about. NOT a liveness SLA — a main can legitimately
# idle for hours — which is why it is far above the stall-ladder grace and why a live
# window suppresses the warning entirely.
_RECIPIENT_LOOKS_DEAD_S = 4 * 3600.0


def _live_window_names(config: dict) -> tuple[set[str] | None, str]:
    """Window names in `tmux.live_session`, or (None, why) if untellable.

    None means UNKNOWN, never "no windows". Callers must not read an unreadable
    tmux as proof that everyone is dead — the C14 polarity lesson applied here.
    """
    live = str((config.get("tmux") or {}).get("live_session") or "").strip()
    if not live:
        # No declared session: do NOT fall back to a default and probe the real
        # tmux. A caller that did not supply config (every unit test) must not
        # reach the live `agent` session and read whichever windows happen to be
        # up — that is a test reaching into production state, and it would make
        # the result depend on who is logged in.
        return None, "no tmux.live_session declared"
    try:
        proc = subprocess.run(["tmux", "list-windows", "-t", live, "-F", "#{window_name}"],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"tmux unreadable: {exc}"
    if proc.returncode != 0:
        return None, f"tmux could not list session {live!r}: {(proc.stderr or '').strip()}"
    return {w.strip() for w in (proc.stdout or "").split() if w.strip()}, live


def _looks_dead(aid: str, entry: dict, states: dict[str, dict],
                windows: set[str] | None, windows_why: str) -> str | None:
    """Reason a rostered recipient looks dead, or None if it looks alive.

    C18 (2026-07-29): REACHABILITY IS OBSERVED, NOT DECLARED. The first version of
    this check asked the roster whether a recipient was `retired` — a field a human
    must remember to maintain — so `codex-bus-tests` stayed "reachable" for 16.7 h
    after its session ended, and a message routed to it was dropped in silence.
    A roster row is a durable IDENTITY; a session is not, and only the session can
    read an inbox. Same lesson as C14: derive state from what is observable.

    Two signals, and the window is decisive:
      * a live window in `tmux.live_session` means alive, full stop — heartbeats go
        stale on a healthy session mid-generation (observed 2026-07-27), so window
        presence must be able to SUPPRESS a stale-heartbeat warning;
      * otherwise a heartbeat silent past _RECIPIENT_LOOKS_DEAD_S is the evidence.

    If tmux is unreadable the window signal is unavailable, and this still warns on
    a stale heartbeat rather than going quiet: the advisory is deduped per
    (msg, recipient), so the cost of a false warning is one visible line, while the
    cost of false silence is the defect this exists to close.
    """
    endpoint = str(entry.get("endpoint") or "")
    candidates = {aid}
    if endpoint.startswith("tmux:"):
        parts = endpoint.split(":")
        if len(parts) >= 3 and parts[2].strip():
            candidates.add(parts[2].strip().split(".", 1)[0])
    if windows is not None and (candidates & windows):
        return None
    age = (states.get(aid) or {}).get("age_s")
    if age is None:
        detail = "has no readable heartbeat"
    elif age > _RECIPIENT_LOOKS_DEAD_S:
        detail = f"heartbeat is {age / 3600.0:.1f}h stale"
    else:
        return None
    where = "no live window" if windows is not None else f"window state unknown ({windows_why})"
    return f"{detail} and {where}"


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
        "capabilities": capability_status(config),
        "capability_blockers": capability_blockers(config),
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

    C27 (2026-07-29): THE TWO OUTPUTS ARE INDEPENDENTLY IDEMPOTENT. Until this
    change `gate in existing` short-circuited the whole iteration, so the block and
    the HELD_OP_GATE row shared one guard. That was harmless only while this ran
    exactly once per tick. It no longer does: the BLOCK is now relayed from the
    always-on tier (`relay_token_blocks`) because transporting "a human signature
    is needed" is transport, while HOLDING a task on that gate is a scheduling
    decision and stays assign-only. With the old guard the always-on write would
    have consumed the gate and the assign-tier pass would then have emitted no
    queue row at all — the fix would have silently broken gating. The block guard
    now suppresses only the block; the row keeps its own (`status != HELD_OP_GATE`).

    `seen` additionally dedupes WITHIN one pass. `existing` is read once, so two
    requests carrying the same gate_id in one sweep used to append it twice.
    """
    tq = bus_root / "tokens" / "token-queue.md"
    existing = tq.read_text(encoding="utf-8") if tq.exists() else ""
    blocks: list[str] = []
    rows: list[dict] = []
    defects: list[dict] = []
    seen: set[str] = set()

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
                                # C33: carried as a FIELD, not only inside the prose, so the
                                # notice built from this row does not have to parse `detail`.
                                "gate_id": gate, "msg_id": msg.get("id"),
                                "detail": f"token-request {gate} lacks dry-run evidence; "
                                          f"presenting an unvalidated command is an agent defect"})
                continue
            if gate in existing or gate in seen:
                self_block = None            # already presented; the hold below still applies
            else:
                seen.add(gate)
                self_block = (
                    f"\n### {gate}\n\n"
                    f"- [ ] **{gate}** — requested by `{msg.get('from')}` for task `{tid}`\n"
                    f"  - block ref: `{payload.get('block_ref', '-')}`\n"
                    f"  - command (pre-validated, dry-run exit "
                    f"`{validated.get('dry_run_exit')}`):\n"
                    f"    ```\n    {validated.get('cmd')}\n    ```\n"
                    f"  - dry-run evidence: {validated.get('dry_run_evidence')}\n"
                )
            if self_block is not None:
                blocks.append(self_block)
            row = latest.get(tid)
            if row and row.get("status") not in TERMINAL_STATES and row.get("status") != "HELD_OP_GATE":
                rows.append({"schema_version": QUEUE_SCHEMA_VERSION, "ts": _utcnow_iso(),
                             "task_id": tid, "status": "HELD_OP_GATE",
                             "lane": row.get("lane"), "gating": row.get("gating"),
                             "epoch": epoch, "owner": row.get("owner"),
                             "operator_gates": sorted(set((row.get("operator_gates") or []) + [gate]))})
    return blocks, rows + defects


def relay_token_blocks(bus_root: Path, config: dict, epoch: int) -> list[dict]:
    """C27 (2026-07-29): present operator gates at EVERY authority, not just `assign`.

    THE DEFECT THIS CLOSES. `relay_tokens` is the only writer of `token-queue.md`
    gate blocks, and it was reachable only from `apply_assignment`, which runs under
    `authority: assign`. The live config is `manual`. `token-request` was
    simultaneously listed in `_NO_RELAY_KINDS` *because* `relay_tokens` was its
    handler-of-record — so the exclusion was justified by a handler that the
    configured authority never reached, and the message went nowhere at all. Two
    real operator signature requests
    (`RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729`, `RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729`,
    filed 2026-07-29 10:18Z and 11:16Z) were lost this way; `token-queue.md` read
    "Pending token requests: (none)" the whole time, so a coordinator following the
    documented cold-start procedure exactly would conclude no gates were waiting.
    Worse than a dropped message: a dropped *signature request*.

    WHY THIS IS TRANSPORT AND NOT JUDGMENT — the test every always-on tier member
    must pass. Relaying a token-request GRANTS NOTHING. It writes an unchecked
    `- [ ]` into a file the operator reads, and the operator still signs. It expands
    no authority and touches no trust boundary, exactly as argued in-code for C2,
    C19 and C20. HOLDING the requesting task on that gate is the opposite — that is
    a scheduling decision — so the `HELD_OP_GATE` queue rows stay assign-only and
    are deliberately not emitted here (`latest={}` yields none). The daemon's bright
    line is unmoved: at `manual` it still writes no queue rows.

    Cheap and idempotent: `relay_tokens` dedupes on `gate_id` against the file, so
    the assign-tier call later in the same tick re-reads it, finds the gate present,
    and appends nothing — while still emitting its own hold row.
    """
    roster = [r for r in (config.get("roster") or []) if isinstance(r, dict)]
    ids = [str(e.get("id", "")).strip() for e in roster if str(e.get("id", "")).strip()]
    reports = _outbox_reports(bus_root, roster)
    blocks, extra = relay_tokens(bus_root, reports, {}, epoch)
    advisory: list[dict] = [item for item in extra if item.get("kind") == "defect"]

    # C33 (2026-07-29): A REFUSED GATE MUST REACH A READER.
    #
    # `relay_tokens` refuses to present a token-request without dry-run evidence —
    # correct, presenting an unvalidated command is an agent defect by policy. But the
    # refusal was reported ONLY as an advisory row, and advisory.jsonl is delivered to
    # nobody; `status` prints the last five on demand. So a gate could be filed, be
    # schema-valid, be silently never presented, AND the notice about it be a second
    # durable-but-unread sink one level up. That is C18's second half exactly, and the
    # same repair applies: push it into coordinator-agent's inbox, which IS drained at
    # every task boundary, because coordinator-agent is the party that can get the
    # requester to re-file.
    #
    # Live instance at authorship: mainA filed `E5-THROTTLE-SCOPE-ERA-ROW-20260729` at
    # 2026-07-29 15:18Z with `action_required: true`, carrying `apply_command` and a
    # top-level `dry_run_evidence` rather than the `validated: {cmd, dry_run_exit}`
    # object this reads. The SCHEMA accepts that shape; the relay does not. So the
    # request was genuinely pre-validated and still stranded, with nobody told.
    # Aligning the schema with the relay contract — so `append` refuses at authoring
    # time, which is the right place — is a CONTRACT change and is escalated
    # separately, not decided here.
    seen_notice: set[str] = set()
    if COORDINATOR_AGENT in ids:
        _ca_rows, _ = _read_jsonl(bus_root / "inbox" / f"{COORDINATOR_AGENT}.jsonl")
        seen_notice = {str((r.get("payload") or {}).get("gate_id")) for r in _ca_rows
                       if (r.get("payload") or {}).get("event") == "token-request-not-presented"}
        for item in advisory:
            gate = str(item.get("gate_id") or "")
            if not gate or gate in seen_notice:
                continue
            _append_inbox(bus_root, [{
                "to": COORDINATOR_AGENT, "kind": "defect",
                "payload": {"event": "token-request-not-presented", "gate_id": gate,
                            "from_agent": item.get("subject"),
                            "detail": item.get("detail"),
                            "action": f"{gate} is NOT in token-queue.md and the operator has not "
                                      f"been asked. Have {item.get('subject')!r} re-file it with "
                                      f"payload.validated = {{cmd, dry_run_exit, dry_run_evidence}}"}}],
                          epoch)
            seen_notice.add(gate)

    if blocks:
        tq = bus_root / "tokens" / "token-queue.md"
        tq.parent.mkdir(parents=True, exist_ok=True)
        with tq.open("a", encoding="utf-8") as fh:
            fh.writelines(blocks)
        advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                         "kind": "tokens-relayed", "count": len(blocks),
                         "tier": "always-on"})
    return advisory


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
    roster = [entry for entry in (_load_config(bus_root).get("roster") or [])
              if isinstance(entry, dict) and str(entry.get("id", "")).strip()]
    for entry in roster:
        owner = str(entry["id"]).strip()
        path = bus_root / "outbox" / f"{owner}.jsonl"
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


def capability_status(config: dict) -> dict[str, dict]:
    """Which M5 capabilities are authorised, capped, and actually implemented.

    WHY THIS EXISTS. `flags` and `caps` sat in config.yaml with NOTHING reading
    them — declared safeguards that enforced nothing. A cap that is not enforced is
    worse than no cap, because it reads as protection. This makes them real, and
    reports the third axis that matters: whether the code exists at all. Granting a
    gate for an unimplemented capability would otherwise leave the config asserting
    `on` while nothing could act on it.

    `implemented` is a fact about this file, not a policy — so a granted flag can
    never make an absent adapter look present.
    """
    flags = config.get("flags") or {}
    caps = config.get("caps") or {}

    def state(flag_val) -> bool:
        return str(flag_val).strip().lower() in {"1", "true", "yes", "on"}

    return {
        "codex_sendkeys": {
            "authorised": state(flags.get("codex_sendkeys")),
            # C9 (2026-07-28): concurrency, not a daily action count. The old
            # max_spawns_per_day is NOT read as a fallback — it authorised a
            # different measurement — so an unset cap reports 0 and spawn refuses.
            "cap": int(caps.get("max_concurrent_mains") or 0),
            "cap_name": "max_concurrent_mains",
            "implemented": True,       # scripts/coordination/tmux_adapter.py (M5, 2026-07-27)
            "gate": "OP-SENDKEYS-CODEX",
        },
        "triage": {
            "authorised": state(flags.get("triage")),
            "cap": int(caps.get("triage_calls_per_day") or 0),
            "cap_name": "triage_calls_per_day",
            "implemented": False,      # no one-shot triage hook exists yet
            "gate": "triage",
        },
        "headless_workers": {
            "authorised": int(caps.get("max_headless_workers") or 0) > 0,
            "cap": int(caps.get("max_headless_workers") or 0),
            "cap_name": "max_headless_workers",
            "implemented": False,      # no headless launcher wiring exists yet
            "gate": "headless-worker",
        },
    }


def capability_blockers(config: dict) -> list[str]:
    """Human-readable reasons each M5 capability cannot run right now."""
    out: list[str] = []
    for name, s in capability_status(config).items():
        reasons = []
        if not s["implemented"]:
            reasons.append("NOT IMPLEMENTED")
        if not s["authorised"]:
            reasons.append(f"gate {s['gate']} not granted")
        if s["cap"] <= 0:
            reasons.append(f"{s['cap_name']}=0")
        if reasons:
            out.append(f"{name}: " + ", ".join(reasons))
    return out


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


COORDINATOR_AGENT = "coordinator-agent"
_BOUNDARY_STATE = "boundary_state.json"


def detect_task_boundaries(bus_root: Path, roster: list[dict], epoch: int) -> list[dict]:
    """Deliver task-boundary notices to coordinator-agent's inbox, durably.

    Defect C8 (2026-07-28): boundary surfacing lived in a coordinator SESSION as a
    background poller, so it died with the session — and a `monitor:file` endpoint
    has no push, so an idle agent was unreachable and its finished work sat
    unnoticed. Detection therefore belongs in the daemon: it is the always-on tier
    (kept alive by bus_supervisor.sh), it already owns every inbox, and a notice
    written to coordinator-agent's inbox is picked up by ANY coordinator session's
    next drain — including a fresh one started hours later. That is what makes
    boundary surfacing survive a session restart.

    Prior state is persisted in a daemon-owned file so a DAEMON restart does not
    replay every agent as a fresh boundary. Only transitions INTO idle are
    reported: an agent going idle is the boundary that needs new work. Ordinary
    working->working churn is noise and is deliberately not delivered.
    """
    state_path = bus_root / _BOUNDARY_STATE
    try:
        prev = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - absent or corrupt reads as "no history"
        prev = {}

    now = _agent_states(bus_root, roster)
    notices, snapshot = [], {}
    for aid, st in now.items():
        if (st.get("role") or "") == "coordinator-agent":
            continue  # don't notify the coordinator about its own idleness
        cur = f"{st.get('state')}|{st.get('task_id')}"
        snapshot[aid] = cur
        was = prev.get(aid)
        if was is None or was == cur:
            continue
        if str(st.get("state") or "").strip() == "idle":
            notice = {
                "to": COORDINATOR_AGENT, "kind": "status",
                "payload": {"event": "task-boundary", "agent": aid,
                            "transition": f"{was} -> {cur}",
                            "detail": f"{aid} reached a task boundary and is IDLE "
                                      f"(was {was}). It has no running task; "
                                      f"assign work or stand it down.",
                            "state": "idle"}}
            # An agent that has retired its task_id has None here, and the msg
            # schema types task_id as a string — so omit rather than emit null.
            if st.get("task_id"):
                notice["task_id"] = st["task_id"]
            notices.append(notice)

    if notices:
        _append_inbox(bus_root, notices, epoch)
    if snapshot != prev:
        _write_atomic(state_path, snapshot)
    return [{"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
             "kind": "task-boundary", "agent": n["payload"]["agent"],
             "transition": n["payload"]["transition"]} for n in notices]


# --------------------------------------------------------- stuck-agent rescue
#
# C19 (2026-07-29). An agent that goes IDLE before draining its inbox stays that
# way forever: the work is delivered, unread, and nothing wakes it. Observed
# repeatedly, most recently `claude-gpu-lane` sitting idle on 14 unread messages
# until a human noticed. The coordinator-agent's 7-minute prompt loop is not a
# fix — it depends on a session's attention, misses windows, and dies with the
# session. Detection belongs here for the same reason C8's boundary surfacing
# does: the daemon ticks every 45s, already reads heartbeats and cursors, is kept
# alive by bus_supervisor.sh, and outlives every coordinator session.
#
# WHAT THIS DOES NOT DO. It does not send keys. It calls tmux_adapter.py, which
# owns the grant (OP-SENDKEYS-CODEX / flags.codex_sendkeys) and every guard
# (quiet-check, heartbeat state, rate limit, submission verification). An adapter
# refusal is a LEGITIMATE outcome recorded as an advisory and retried on a later
# tick — never routed around. A daemon that learns to bypass its own guards is a
# far worse failure mode than a stuck agent.
_STUCK_STATE = "stuck_state.json"
# Heartbeat silence that, combined with unread mail, counts as stuck even without
# an explicit `idle`. Above the stall-ladder grace: a main may legitimately be
# quiet for a long while, and the adapter's own heartbeat guards decide the rest.
_STUCK_HEARTBEAT_STALE_S = 3600.0
# Never nudge one agent more often than this. Matches tmux_adapter's own default
# --min-interval-s, and is passed THROUGH to the adapter so the adapter enforces
# it independently of this file's bookkeeping.
_STUCK_MIN_NUDGE_INTERVAL_S = 600.0
# An agent that was nudged and whose (unread, cursor) is unchanged is refusing to
# drain — a different problem from being asleep, and nudging it forever is noise.
# Escalating advisories are emitted no more often than this.
_STUCK_ESCALATION_INTERVAL_S = 1800.0
# A guard refusal is retried, but not on every 45s tick: an endpoint the adapter
# structurally cannot resolve (`tmux:agent` with no matching window) would
# otherwise spawn a subprocess and write an advisory row every tick, forever.
_STUCK_REFUSAL_RETRY_S = 300.0
_STUCK_NUDGE_MESSAGE = (
    "Bus: you have {unread} unread inbox message(s) and are idle. Run "
    "scripts/coordination/session_bus.py drain --agent {agent} now, act on what it "
    "delivers, and refresh your heartbeat."
)


def _tmux_nudge(agent: str, message: str, min_interval_s: float) -> tuple[int, str]:
    """Shell out to the adapter. Isolated so tests can substitute it wholesale."""
    script = Path(__file__).resolve().parent / "tmux_adapter.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "nudge", "--agent", agent,
             "--message", message, "--min-interval-s", str(min_interval_s)],
            capture_output=True, text=True, timeout=120,
        )
    except Exception as exc:  # noqa: BLE001 — an unrunnable adapter is a refusal
        return 3, f"adapter invocation failed: {exc}"
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


# C21 (2026-07-29). The stuck predicate is ENTIRELY heartbeat-derived, and agents
# let heartbeats go stale in BOTH directions — an agent mid-generation left
# `state: idle` behind. Observed live: fable-auditor was flagged stuck 4x while
# its pane was plainly generating; the adapter's own quiet-check refused, so no
# agent was wrongly interrupted, but `stuck-detected` stopped being a usable
# signal. The pane is the more trustworthy witness, so cross-check it before
# spending a detection or a nudge.
#
# `esc to interrupt` is the marker, deliberately NOT tmux_adapter.probe's
# window_activity quiet-check: the quiet-check is defeated by cosmetic TUI
# redraw (an idle pane that re-renders reads as busy), so it cannot answer "is
# it working". The literal marker is rendered by both TUIs only while a turn is
# in flight and has held up all day.
_PANE_BUSY_MARKER = "esc to interrupt"


def _pane_generating(agent: str, roster: list[dict]) -> tuple[Optional[bool], str]:
    """(True | False | None, detail). None = the pane could not be read.

    Read-only: `tmux capture-pane -p`. Target resolution is delegated to
    tmux_adapter.resolve_target(), which already verifies that an endpoint's
    window component resolves to the window it names (tmux silently falls back
    to the session's current window on a miss) — reimplementing endpoint parsing
    here is exactly how the wrong pane gets read.
    """
    try:
        from scripts.coordination import tmux_adapter  # lazy: keeps import cheap/safe
        target, reason = tmux_adapter.resolve_target({"roster": roster}, agent)
    except Exception as exc:  # noqa: BLE001 — an unusable adapter is "unreadable"
        return None, f"could not resolve a tmux target: {exc}"
    if not target:
        return None, f"could not resolve a tmux target: {reason}"
    try:
        proc = subprocess.run(["tmux", "capture-pane", "-p", "-t", target],
                              capture_output=True, text=True, timeout=15)
    except Exception as exc:  # noqa: BLE001
        return None, f"capture-pane on {target} failed: {exc}"
    if proc.returncode != 0:
        return None, f"capture-pane on {target} exited {proc.returncode}: " \
                     f"{(proc.stderr or proc.stdout or '').strip()[:200]}"
    if _PANE_BUSY_MARKER in (proc.stdout or "").lower():
        return True, f"pane {target} shows {_PANE_BUSY_MARKER!r}"
    return False, f"pane {target} shows no generation marker"


def _unread_state_rows(bus_root: Path, aid: str) -> tuple[list[dict], int]:
    """(unread_rows, cursor_offset). Raises if it cannot be computed.

    FAIL CLOSED. A missing inbox, a missing/unreadable cursor or malformed JSONL
    must NOT read as "zero unread" — every prior defect in this module (C3, C6,
    C8) was a fail-open, and "no unread" is precisely the answer that makes a
    stuck agent invisible. The caller skips the agent and says so in an advisory.
    """
    cursor_path = bus_root / "cursors" / f"{aid}.json"
    raw = json.loads(cursor_path.read_text(encoding="utf-8"))
    offset = int(raw["offset"])
    inbox = bus_root / "inbox" / f"{aid}.jsonl"
    if not inbox.exists():
        raise FileNotFoundError(f"{inbox} does not exist")
    rows, _ = _read_jsonl(inbox, offset)   # raises BusError on malformed JSONL
    return rows, offset


def _unread_state(bus_root: Path, aid: str) -> tuple[int, int]:
    """(unread_count, cursor_offset), same fail-closed contract."""
    rows, offset = _unread_state_rows(bus_root, aid)
    return len(rows), offset


def resolve_stuck_agents(bus_root: Path, roster: list[dict], epoch: int,
                         *, nudge_fn=None, pane_fn=None,
                         now: float | None = None) -> list[dict]:
    """Detect agents idle on unread mail and nudge them to drain.

    Predicate: `unread > 0` AND (heartbeat state is `idle` OR the heartbeat is
    unreadable/absent OR its age exceeds _STUCK_HEARTBEAT_STALE_S). An agent
    reporting `working`/`draining` with a fresh heartbeat is NOT stuck — it will
    drain at its next boundary, which is the protocol.

    C21: because that predicate is purely heartbeat-derived and heartbeats go
    stale in both directions, a tmux agent's pane is cross-checked before any
    detection or nudge. A pane that is generating — or that cannot be read —
    suppresses the nudge with a `stuck-suppressed-pane-active` advisory.

    De-duplication is durable, in a daemon-owned state file, so a daemon restart
    does not re-nudge everybody: per agent we keep the last nudge timestamp and
    the (unread, cursor) pair it was sent against.
    """
    nudge = nudge_fn or _tmux_nudge
    pane = pane_fn or _pane_generating
    now = time.time() if now is None else now
    state_path = bus_root / _STUCK_STATE
    try:
        prev = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(prev, dict):
            prev = {}
    except Exception:  # noqa: BLE001 — absent or corrupt reads as "no history"
        prev = {}

    states = _agent_states(bus_root, roster)
    advisory: list[dict] = []
    new_state = dict(prev)

    def row(kind: str, aid: str, **extra) -> None:
        advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                         "epoch": epoch, "kind": kind, "check": "stuck-agent",
                         "agent": aid, **extra})

    for entry in roster:
        aid = str(entry.get("id", "")).strip()
        if not aid or aid == COORDINATOR_DAEMON:
            continue
        endpoint = str(entry.get("endpoint") or "").strip()
        rec = dict(prev.get(aid) or {})

        try:
            unread, offset = _unread_state(bus_root, aid)
        except Exception as exc:  # noqa: BLE001
            # NOT zero. Skipped, loudly, and deduped so a permanently missing
            # file does not write a row every 45s.
            sig = f"unreadable:{exc.__class__.__name__}"
            if rec.get("last_detect_sig") != sig:
                row("stuck-state-unreadable", aid, detail=str(exc),
                    action="skipped — unread not computable, NOT treated as zero")
            rec["last_detect_sig"] = sig
            new_state[aid] = rec
            continue

        st = states.get(aid) or {}
        hb_state = str(st.get("state") or "").strip()
        hb_age = st.get("age_s")
        stale = hb_age is None or hb_age > _STUCK_HEARTBEAT_STALE_S
        stuck = unread > 0 and (hb_state == "idle" or not hb_state or stale)

        if not stuck:
            rec["last_detect_sig"] = f"clear:{unread}:{offset}"
            new_state[aid] = rec
            continue

        # C21 pane cross-check. Every path into `stuck` above is heartbeat-derived,
        # so the pane always gets the deciding vote before we spend a detection.
        #
        # FAIL CLOSED = SUPPRESS. An unreadable pane (tmux down, session/window
        # gone, capture failed) resolves to "do not nudge", NOT "nudge anyway":
        #   - if the window is genuinely gone the adapter refuses the nudge
        #     anyway, so suppressing costs one advisory row and nothing else;
        #   - nudging a busy agent is precisely the harm being removed here, and
        #     an unreadable pane cannot rule that out.
        # Suppression is never silent and never permanent: the advisory is
        # emitted, and the next tick re-reads the pane, so a transient tmux
        # failure self-heals while a truly idle agent is nudged one tick later.
        if endpoint.startswith("tmux:"):
            active, detail = pane(aid, roster)
            if active is not False:
                psig = f"pane-suppressed:{unread}:{offset}"
                if rec.get("last_detect_sig") != psig:
                    row("stuck-suppressed-pane-active", aid, unread=unread,
                        cursor_offset=offset, heartbeat_state=hb_state or None,
                        heartbeat_age_s=hb_age, endpoint=endpoint,
                        pane_active=active, detail=detail,
                        action=("pane is generating — heartbeat is stale, not the agent"
                                if active else
                                "pane unreadable — failing closed to suppression, "
                                "re-checked next tick"))
                rec["last_detect_sig"] = psig
                new_state[aid] = rec
                continue

        sig = f"stuck:{unread}:{offset}"
        if rec.get("last_detect_sig") != sig:
            row("stuck-detected", aid, unread=unread, cursor_offset=offset,
                heartbeat_state=hb_state or None, heartbeat_age_s=hb_age,
                endpoint=endpoint)
        rec["last_detect_sig"] = sig

        # (6) A monitor:file endpoint has no push channel — there is nothing to
        # send keys to. Surfacing it is the whole remedy available; attempting a
        # nudge would only manufacture a guaranteed adapter refusal.
        if not endpoint.startswith("tmux:"):
            last = rec.get("last_unreachable_ts")
            if last is None or now - float(last) >= _STUCK_ESCALATION_INTERVAL_S:
                row("stuck-unreachable", aid, unread=unread, endpoint=endpoint or None,
                    detail="stuck on unread mail but the endpoint is not tmux, so it "
                           "cannot be nudged (defect C8's shape)",
                    action="operator/coordinator-agent must reach it out of band")
                rec["last_unreachable_ts"] = now
            new_state[aid] = rec
            continue

        # (4) Refusing to drain: we nudged, and neither the unread count nor the
        # cursor moved. Nudging again would not help — this is a different defect
        # and it escalates rather than repeating.
        nudged_sig = rec.get("last_nudge_sig")
        if nudged_sig == f"{unread}:{offset}":
            last_esc = rec.get("last_escalation_ts")
            if last_esc is None or now - float(last_esc) >= _STUCK_ESCALATION_INTERVAL_S:
                rec["escalations"] = int(rec.get("escalations") or 0) + 1
                row("stuck-refusing-drain", aid, unread=unread, cursor_offset=offset,
                    escalation=rec["escalations"],
                    detail=f"nudged {int(rec.get('nudges') or 0)} time(s); unread and cursor "
                           f"unchanged since. The agent is not asleep — it is not draining.",
                    action="coordinator-agent/operator intervention")
                rec["last_escalation_ts"] = now
            new_state[aid] = rec
            continue

        last_nudge_ts = rec.get("last_nudge_ts")
        if last_nudge_ts is not None and now - float(last_nudge_ts) < _STUCK_MIN_NUDGE_INTERVAL_S:
            new_state[aid] = rec          # rate limited; retried on a later tick
            continue

        last_refusal = rec.get("last_refusal_ts")
        if last_refusal is not None and now - float(last_refusal) < _STUCK_REFUSAL_RETRY_S:
            new_state[aid] = rec       # backing off a refused attempt; retried later
            continue

        message = _STUCK_NUDGE_MESSAGE.format(unread=unread, agent=aid)
        rc, out = nudge(aid, message, _STUCK_MIN_NUDGE_INTERVAL_S)
        if rc == 0:
            rec["last_nudge_ts"] = now
            rec["last_nudge_sig"] = f"{unread}:{offset}"
            rec["nudges"] = int(rec.get("nudges") or 0) + 1
            row("stuck-nudged", aid, unread=unread, cursor_offset=offset,
                nudges=rec["nudges"], detail=out[-500:])
        else:
            # A guard said no. That is the system working; record the divergence
            # between "detected stuck" and "resolved" and try again later.
            rec["last_refusal_ts"] = now
            row("stuck-nudge-refused", aid, unread=unread, exit_code=rc,
                detail=out[-500:] or "adapter refused with no output",
                action="guard refusal respected; retried on a later tick")
        new_state[aid] = rec

    if new_state != prev:
        _write_atomic(state_path, new_state)
    return advisory


# ------------------------------------------------- the last hop: bus -> operator
#
# C20 (2026-07-29). The delivery plane is mechanical; the LAST HOP is not. Seven
# documented failures share one shape: an operator-decision item existed durably
# and NO machine was responsible for a human seeing it within a bounded time.
# Twice a ratification command was printed into a pane and never filed as a
# token-request, so the coordinator's drain was legitimately empty and the
# OPERATOR found it by reading tmux. Once, 33 messages sat unread — including
# "Human amendment required. No further inference permitted".
#
# The load-bearing idea is (c): the coordinator-agent is in the loop for
# JUDGEMENT, and that must not make it a single point of failure for TRANSPORT
# of "a human signature is needed". So after a second, longer deadline the daemon
# writes the notice straight into tokens/token-queue.md — a file the operator
# already reads — as a clearly marked daemon escalation. It NEVER writes or
# alters a checkbox: relaying blocks is the daemon's existing role under rule 1,
# flipping a box is the operator's and only the operator's.
_OPERATOR_STATE = "operator_escalation_state.json"
# Kinds that mean a human is waiting. Deliberately narrow: a normalised warning
# is the failure mode this whole mechanism exists to avoid.
_OPERATOR_ITEM_KINDS = {"token-request", "defect"}
_OPERATOR_NUDGE_DEADLINE_S = 1800.0      # 30 min unread -> nudge the coordinator
_OPERATOR_BYPASS_DEADLINE_S = 5400.0     # 90 min unread -> bypass to the operator
_OPERATOR_NUDGE_RETRY_S = 900.0
_OPERATOR_ESCALATION_MARKER = "DAEMON-ESCALATION"
# (a) THE RECEIPT CONVENTION, and why it is inert today.
#
# A prior attempt to join operator scripts against the token queue flagged 11 of
# 25 as "unrun". That was not a scanner bug — it was missing ground truth:
# superseded and repaired scripts never receive receipts, and string-matching
# --validate-only output guesses at each script's vocabulary. A high-false-
# positive signal here would be worse than none, because normalised warnings are
# precisely how the seven failures happened.
#
# So the join is defined against an EXPLICIT convention and scans nothing that
# has not opted in:
#   * a script declares its gate with a header line `# BUS-GATE: <gate-id>`;
#   * a successful apply writes `<script-name>.receipt.json` beside it;
#   * a superseded script gets `<script-name>.superseded`, minted when its
#     successor is generated.
# No script in artifacts/operator/ declares BUS-GATE today, so this emits
# nothing until the convention is adopted — which is an operator decision, not
# one the daemon makes for them. Documented in BUS_PROTOCOL.md.
_BUS_GATE_DECLARATION = "# BUS-GATE:"
_OPERATOR_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "operator"


def _msg_age_s(row: dict, now: float) -> float | None:
    try:
        ts = datetime.fromisoformat(str(row.get("ts")))
    except (TypeError, ValueError):
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return now - ts.timestamp()


def _is_operator_item(row: dict) -> bool:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    if row.get("kind") in _OPERATOR_ITEM_KINDS:
        return True
    for key in ("severity", "priority"):
        if str(payload.get(key) or row.get(key) or "").strip().upper() == "CRITICAL":
            return True
    return False


def unevidenced_operator_outbox(bus_root: Path, roster: list[dict]) -> list[dict]:
    """C27c: operator items sitting in OUTBOXES with no evidence anyone consumed them.

    WHY THE INBOX SCAN IS NOT ENOUGH. `pending_operator_actions` is the last-hop net
    for "a human signature is needed", and it read exactly one set: the coordinator's
    unread INBOX rows. But a message only reaches that inbox if the relay put it
    there — and `_NO_RELAY_KINDS` guaranteed a `token-request` never could. The net
    was searching a set that structurally cannot contain the thing it looks for.
    Both 2026-07-29 gates were invisible to it for that reason, for hours, while the
    mechanism built to catch precisely this reported nothing.

    A last-hop net that depends on the hop before it having worked is not a net. So
    this reads the SENDERS' own files, which is the earliest durable evidence that
    exists and the one thing no delivery bug can erase.

    EVIDENCE, not delivery — an item is considered handled when ANY of these hold,
    because each means something downstream actually saw it:
      * it was relayed (some inbox carries `relayed_src == id`) — the inbox path
        owns it from there, and this also stops the two paths double-escalating;
      * it is a token-request whose `gate_id` is already in `token-queue.md` — the
        operator can see it, which is the entire objective;
      * some outbox carries `corr_id == id` — somebody answered it.

    Deliberately NOT evidence: the coordinator having read it. Read-and-dropped is
    the failure this catches, and the read cursor cannot tell the two apart.

    Measured against the live bus at authorship: 24 operator-kind outbox rows, 3
    unevidenced — two of them the lost gates, one a routed defect. The narrowness is
    the point; a high-false-positive signal here would be worse than none.
    """
    ids = [str(e.get("id", "")).strip() for e in roster
           if isinstance(e, dict) and str(e.get("id", "")).strip()]
    relayed: set[str] = set()
    answered: set[str] = set()
    for aid in ids:
        for row in _read_jsonl(bus_root / "inbox" / f"{aid}.jsonl")[0]:
            if row.get("relayed_src"):
                relayed.add(str(row["relayed_src"]))
        for row in _read_jsonl(bus_root / "outbox" / f"{aid}.jsonl")[0]:
            if row.get("corr_id"):
                answered.add(str(row["corr_id"]))
    try:
        presented = (bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")
    except OSError:
        presented = ""

    out: list[dict] = []
    for aid in ids:
        for row in _read_jsonl(bus_root / "outbox" / f"{aid}.jsonl")[0]:
            mid = str(row.get("id") or "")
            if not mid or not _is_operator_item(row):
                continue
            if mid in relayed or mid in answered:
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            gate = payload.get("gate_id")
            if gate and str(gate) in presented:
                continue
            out.append(row)
    return out


def scan_operator_receipts(bus_root: Path, roster: list[dict], epoch: int,
                           *, artifact_dir: Path | None = None) -> list[dict]:
    """(a) Operator scripts that declare a gate nobody ever asked the operator for.

    The obligation being enforced is EMISSION: the producing agent should have
    filed a `token-request`. Printing a ratification command into a pane is the
    defect; detecting it afterwards is the consolation prize. Exempt: a script
    with a receipt (applied), a `.superseded` marker (replaced), or whose gate is
    already in the token queue or in some outbox token-request.
    """
    directory = artifact_dir or _OPERATOR_ARTIFACT_DIR
    advisory: list[dict] = []
    if not directory.is_dir():
        return advisory
    try:
        token_text = (bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — fail closed: no queue, no exemptions to check
        return [{"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                 "kind": "operator-receipt-scan-skipped", "check": "operator-receipt",
                 "detail": f"token-queue.md unreadable: {exc}"}]

    requested: set[str] = set()
    producer_of: dict[str, str] = {}
    for entry in roster:
        aid = str(entry.get("id", "")).strip()
        if not aid:
            continue
        try:
            rows, _ = _read_jsonl(bus_root / "outbox" / f"{aid}.jsonl")
        except Exception:  # noqa: BLE001 — an unreadable outbox proves no request
            continue
        for row in rows:
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            if row.get("kind") == "token-request" and payload.get("gate_id"):
                requested.add(str(payload["gate_id"]))
            for name in ("script", "artifact", "path", "cmd"):
                val = payload.get(name)
                if isinstance(val, str) and val.endswith(".sh"):
                    producer_of.setdefault(Path(val).name, aid)

    notices: list[dict] = []
    seen_notices = set()
    try:
        inbox_rows, _ = _read_jsonl(bus_root / "inbox" / f"{COORDINATOR_AGENT}.jsonl")
        seen_notices = {str((r.get("payload") or {}).get("gate_id")) for r in inbox_rows
                        if (r.get("payload") or {}).get("event") == "unrequested-operator-gate"}
    except Exception:  # noqa: BLE001
        seen_notices = set()

    for script in sorted(directory.glob("*.sh")):
        try:
            text = script.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                             "epoch": epoch, "kind": "operator-receipt-unreadable",
                             "check": "operator-receipt", "script": script.name,
                             "detail": str(exc)})
            continue
        gate = ""
        for line in text.splitlines():
            if line.strip().startswith(_BUS_GATE_DECLARATION):
                gate = line.split(":", 1)[1].strip()
                break
        if not gate:
            continue  # has not opted into the convention; nothing is known, so nothing is claimed
        if script.with_suffix(".sh.receipt.json").exists() or (
                script.parent / f"{script.name}.receipt.json").exists():
            continue
        if (script.parent / f"{script.name}.superseded").exists():
            continue
        if gate in token_text or gate in requested:
            continue
        subject = producer_of.get(script.name, "unattributed (all sessions share one git identity)")
        advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                         "kind": "defect", "check": "operator-receipt", "subject": subject,
                         "script": script.name, "gate_id": gate,
                         "detail": f"{script.name} declares gate {gate}, which appears in neither "
                                   f"the token queue nor any outbox token-request, and it has no "
                                   f"receipt or superseded marker. The producing agent owed a "
                                   f"token-request."})
        if gate not in seen_notices:
            notices.append({"to": COORDINATOR_AGENT, "kind": "defect",
                            "payload": {"event": "unrequested-operator-gate", "gate_id": gate,
                                        "script": str(script), "producer": subject,
                                        "detail": "an operator script declares a gate that was "
                                                  "never presented to the operator"}})
            seen_notices.add(gate)
    if notices:
        _append_inbox(bus_root, notices, epoch)
    return advisory


def pending_operator_actions(bus_root: Path, roster: list[dict], epoch: int,
                             *, nudge_fn=None, now: float | None = None,
                             artifact_dir: Path | None = None) -> list[dict]:
    """(b) + (c): unread operator-decision items age into a nudge, then a bypass."""
    nudge = nudge_fn or _tmux_nudge
    now = time.time() if now is None else now
    advisory: list[dict] = []
    advisory += scan_operator_receipts(bus_root, roster, epoch, artifact_dir=artifact_dir)

    state_path = bus_root / _OPERATOR_STATE
    try:
        prev = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(prev, dict):
            prev = {}
    except Exception:  # noqa: BLE001
        prev = {}
    state = dict(prev)

    # FAIL CLOSED. If the coordinator's unread set cannot be computed we do NOT
    # read that as "nothing is waiting" — that is exactly the shape of the
    # failure this exists to catch.
    try:
        unread, _ = _unread_state_rows(bus_root, COORDINATOR_AGENT)
    except Exception as exc:  # noqa: BLE001
        advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                         "kind": "operator-backlog-unreadable", "check": "pending-operator-action",
                         "agent": COORDINATOR_AGENT, "detail": str(exc),
                         "action": "skipped — unread not computable, NOT treated as empty"})
        return advisory

    # C27c: the second input. Failures of the hop BEFORE this one are invisible to
    # `unread`, so the net also reads the senders' own outboxes. Tagged, because a
    # reader must be able to tell "the coordinator sat on it" from "it never got
    # there" — those have different repairs.
    try:
        stranded = unevidenced_operator_outbox(bus_root, roster)
    except Exception as exc:  # noqa: BLE001 — FAIL CLOSED, same as the unread read above
        advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                         "kind": "operator-outbox-unreadable", "check": "pending-operator-action",
                         "detail": str(exc),
                         "action": "outbox scan skipped — NOT treated as empty"})
        stranded = []

    overdue, bypass_due = [], []
    for row in stranded:
        age = _msg_age_s(row, now)
        if age is not None and age >= _OPERATOR_BYPASS_DEADLINE_S:
            bypass_due.append((dict(row, _c27_undelivered=True), age))
    for row in unread:
        if not _is_operator_item(row):
            continue
        age = _msg_age_s(row, now)
        if age is None:
            advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                             "epoch": epoch, "kind": "operator-item-undatable",
                             "check": "pending-operator-action", "msg_id": row.get("id"),
                             "detail": "unread operator item has no parseable ts; "
                                       "escalating on the next readable pass"})
            continue
        if age >= _OPERATOR_BYPASS_DEADLINE_S:
            bypass_due.append((row, age))
        if age >= _OPERATOR_NUDGE_DEADLINE_S:
            overdue.append((row, age))

    # (c) step 1 — nudge the coordinator. Its endpoint is `monitor:file` today, so
    # the adapter WILL refuse; that refusal is recorded rather than worked around,
    # and it is defect C8's shape: an unreachable agent holding operator-critical
    # mail. The bypass below is what makes that survivable.
    if overdue:
        last = state.get("__nudge__", {}).get("ts")
        if last is None or now - float(last) >= _OPERATOR_NUDGE_RETRY_S:
            rc, out = nudge(COORDINATOR_AGENT,
                            f"Bus: {len(overdue)} operator-decision item(s) have been unread in "
                            f"your inbox past the deadline. Drain and present them now.",
                            _OPERATOR_NUDGE_RETRY_S)
            state["__nudge__"] = {"ts": now, "rc": rc}
            advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                             "epoch": epoch,
                             "kind": "operator-backlog-nudged" if rc == 0
                                     else "operator-backlog-unreachable",
                             "check": "pending-operator-action", "agent": COORDINATOR_AGENT,
                             "overdue": len(overdue), "exit_code": rc, "detail": out[-500:]})

    # (c) step 2 — bypass. Append a clearly marked, checkbox-free notice block to
    # a file the operator already checks. Idempotent on the message id, exactly as
    # relay_tokens is idempotent on gate_id, so repeated ticks cannot spam it.
    tq = bus_root / "tokens" / "token-queue.md"
    try:
        existing = tq.read_text(encoding="utf-8") if tq.exists() else ""
    except Exception as exc:  # noqa: BLE001
        advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                         "kind": "operator-bypass-unavailable", "check": "pending-operator-action",
                         "detail": f"token-queue.md unreadable: {exc}"})
        if state != prev:
            _write_atomic(state_path, state)
        return advisory

    blocks: list[str] = []
    for row, age in bypass_due:
        mid = str(row.get("id") or "")
        marker = f"{_OPERATOR_ESCALATION_MARKER} {mid}"
        if not mid or marker in existing:
            continue
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        detail = str(payload.get("detail") or payload.get("event") or row.get("kind"))
        if row.get("_c27_undelivered"):
            where = (f"**never reached `coordinator-agent`'s inbox at all** and shows no sign of "
                     f"having been consumed anywhere. It has sat in `outbox/{row.get('from')}"
                     f".jsonl` for {age / 3600.0:.1f}h. This is a DELIVERY failure, not a triage "
                     f"backlog — repairing the coordinator's attention will not clear it")
        else:
            where = (f"has sat unread in `coordinator-agent`'s inbox for {age / 3600.0:.1f}h, past "
                     f"the bypass deadline. The coordinator is in the loop for judgement; it must "
                     f"not be a single point of failure for transporting *a human signature is "
                     f"needed*")
        blocks.append(
            f"\n### {marker}\n\n"
            f"**Daemon escalation — not a gate, no checkbox.** An operator-decision item {where}.\n\n"
            f"- message: `{mid}` (`{row.get('kind')}`) from `{row.get('from')}`\n"
            f"- task: `{row.get('task_id') or '-'}`\n"
            f"- detail: {detail}\n"
        )
        state.setdefault("escalated", {})[mid] = now
        advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(), "epoch": epoch,
                         "kind": "operator-bypass-escalated", "check": "pending-operator-action",
                         "msg_id": mid, "msg_kind": row.get("kind"), "age_s": age})
    if blocks:
        with tq.open("a", encoding="utf-8") as fh:
            fh.writelines(blocks)
    if state != prev:
        _write_atomic(state_path, state)
    return advisory


# C27 (2026-07-29): kind -> (handler-of-record, is that handler REACHABLE here?).
#
# This was a bare set — `_NO_RELAY_KINDS = {"token-request", "task-propose",
# "task-complete"}` — of kinds the relay skipped "because the daemon already
# consumes them through another path". It was right about which handler owned each
# kind and NEVER CHECKED THAT ANY OF THEM RUNS:
#   * token-request -> relay_tokens, then reachable only from apply_assignment
#     (assign-only) while the live config is `manual`;
#   * task-complete -> transcribe, likewise inside apply_assignment;
#   * task-propose  -> intake_proposals, reachable ONLY from the manual `intake`
#     CLI. `tick` has never called it at any authority.
# So a declaration was used to justify removing a kind from the general path, and
# the declaration's own premise was never tested against the CONFIGURED authority.
# Two operator signature requests were lost this way on 2026-07-29 (see
# relay_token_blocks); C27a fixed token-request's handler, this fixes the class.
#
# THE RULE, and why it is not a bare skip: when the handler is unreachable the
# message is RELAYED NORMALLY and a defect is emitted. Delivery is transport, so
# duplicating a message into an inbox costs a read; dropping it costs a gate. The
# asymmetry is the whole argument. This also restores the C18 discipline stated
# twenty lines below — "an unreachable recipient is a defect advisory, never a
# silent drop" — which the old bare `continue` contradicted, including for
# `needs_routing_to`, whose fan-out sits AFTER the skip and was therefore inert for
# exactly the three kinds that most needed it.
#
# ADDING A KIND HERE IS A CLAIM YOU MUST BE ABLE TO DEFEND: name the function that
# consumes it and state the authorities at which that function actually runs.
_RELAY_HANDLERS: dict[str, tuple[str, str]] = {
    # kind: (handler-of-record, authority at which it runs; "*" = every authority)
    "token-request": ("relay_token_blocks", "*"),
    "task-complete": ("transcribe", "assign"),
    "task-propose": ("intake_proposals", "never — `intake` CLI only, never from tick"),
}
# Retained as the derived view, so `validate` and any external reader that asks
# "which kinds does relay skip?" get an answer that depends on the live authority
# instead of a constant that was wrong for two of its three members.
def no_relay_kinds(authority: str) -> set[str]:
    return {kind for kind, (_h, at) in _RELAY_HANDLERS.items()
            if at == "*" or at == authority}
_ACK_REDELIVERY_REASON = "ack-deadline elapsed"


def redeliver_unacked_messages(bus_root: Path, roster: list[dict], epoch: int) -> list[dict]:
    """Rule 3: nudge recipients whose delivered ACK-required messages expired.

    The recipient's outbox is the authoritative ACK source: it is the only file
    that recipient may write.  A ``corr_id`` is considered acknowledged when an
    ``ack`` row in that outbox carries the same value.

    Bound: emit at most one ACK-deadline nudge per unacknowledged ``corr_id``.
    The nudge remains durable in the recipient inbox, so re-running every tick
    cannot grow the inbox without bound.  Its daemon-assigned message id is new,
    while ``corr_id`` preserves the protocol's correlation identity.
    """
    ids = [str(entry.get("id", "")).strip() for entry in roster
           if str(entry.get("id", "")).strip()]
    advisory: list[dict] = []
    now = datetime.now(timezone.utc)

    for recipient in ids:
        inbox, _ = _read_jsonl(bus_root / "inbox" / f"{recipient}.jsonl")
        outbox, _ = _read_jsonl(bus_root / "outbox" / f"{recipient}.jsonl")
        acked = {str(row.get("corr_id")) for row in outbox
                 if row.get("kind") == "ack" and row.get("corr_id")}
        nudged = {
            str(row.get("corr_id")) for row in inbox
            if row.get("kind") == "nudge" and row.get("corr_id")
            and (row.get("payload") or {}).get("reason") == _ACK_REDELIVERY_REASON
        }

        for row in inbox:
            corr_id = row.get("corr_id")
            deadline_s = row.get("ack_deadline_s")
            if not row.get("requires_ack") or not corr_id or deadline_s is None:
                continue
            corr_id = str(corr_id)
            if corr_id in acked or corr_id in nudged:
                continue
            try:
                delivered_at = datetime.fromisoformat(str(row.get("ts")))
                if delivered_at.tzinfo is None:
                    delivered_at = delivered_at.replace(tzinfo=timezone.utc)
                overdue = now >= delivered_at + timedelta(seconds=float(deadline_s))
            except (TypeError, ValueError, OverflowError):
                continue  # malformed source is not a safe basis for a deadline action
            if not overdue:
                continue
            _append_inbox(bus_root, [{
                "to": recipient,
                "kind": "nudge",
                "corr_id": corr_id,
                "task_id": row.get("task_id"),
                "payload": {
                    "reason": _ACK_REDELIVERY_REASON,
                    "original_msg_id": row.get("id"),
                    "instruction": "ack the correlated message from your own outbox",
                },
            }], epoch)
            nudged.add(corr_id)
            advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                             "epoch": epoch, "kind": "ack-redelivered",
                             "agent": recipient, "corr_id": corr_id,
                             "task_id": row.get("task_id")})
    return advisory


def relay_outbox_messages(bus_root: Path, roster: list[dict], epoch: int,
                          config: dict | None = None) -> list[dict]:
    """Deliver agent-authored, explicitly-addressed outbox messages to inboxes.

    Defect C2 (2026-07-28): _append_inbox was only ever called with messages the
    daemon generated itself, so agent -> agent messages were written and silently
    dropped. That made coordinator-agent's duties 4 and 6 (lease-revoke, re-read
    nudges) unexecutable, and BUS_PROTOCOL rule 3's ack redelivery could never fire
    because delivery never happened. Note _outbox_reports keys by task_id and drops
    rows without one, so relay reads the outboxes directly rather than reusing it.

    Idempotent: each delivered row carries `relayed_src` (the source msg id), and a
    recipient's inbox is scanned for those before delivering.
    """
    ids = [str(e.get("id", "")).strip() for e in roster if str(e.get("id", "")).strip()]
    authority = _authority(config or {})
    skip_kinds = no_relay_kinds(authority)
    roles = {str(e.get("id", "")).strip(): str(e.get("role") or "").strip()
             for e in roster if isinstance(e, dict) and str(e.get("id", "")).strip()}
    roster_by_id = {str(e.get("id", "")).strip(): e for e in roster
                    if isinstance(e, dict) and str(e.get("id", "")).strip()}
    # C18 code half: liveness inputs, read ONCE per relay pass rather than per message.
    states = _agent_states(bus_root, roster)
    live_windows, live_windows_why = _live_window_names(config or {})
    # C18 second half: which (msg, dead-recipient) pairs coordinator-agent has already
    # been told about, read from its inbox — the notice's own durable trace.
    _ca_rows, _ = _read_jsonl(bus_root / "inbox" / f"{COORDINATOR_AGENT}.jsonl")
    notified = {(str(r.get("relayed_src")), str((r.get("payload") or {}).get("unreachable")))
                for r in _ca_rows
                if r.get("kind") == "defect" and (r.get("payload") or {}).get("unreachable")}
    delivered_src: dict[str, set[str]] = {}
    for aid in ids:
        rows, _ = _read_jsonl(bus_root / "inbox" / f"{aid}.jsonl")
        delivered_src[aid] = {r["relayed_src"] for r in rows if r.get("relayed_src")}

    # C18 dedupe: an unreachable routing recipient is flagged ONCE per (msg, rid),
    # not once per tick — the pair is looked up in the durable advisory ledger the
    # tick loop writes, so a restart does not re-flood it either.
    already_flagged: set[tuple[str, str]] = set()
    try:
        advisory_rows, _ = _read_jsonl(bus_root / "advisory.jsonl")
        already_flagged = {(str(r.get("relayed_src")), str(r.get("unreachable")))
                          for r in advisory_rows if r.get("unreachable")}
    except Exception:  # noqa: BLE001 — a torn ledger must not stop delivery
        pass

    advisory: list[dict] = []
    for sender in ids:
        rows, _ = _read_jsonl(bus_root / "outbox" / f"{sender}.jsonl")
        for row in rows:
            to, kind = row.get("to"), row.get("kind")
            src = row.get("id")
            if not to or not src:
                continue
            if kind in skip_kinds:
                continue          # its handler runs at this authority; relaying would double-count
            # C27: declared handler, but NOT reachable here. Relay it (below) AND say so
            # once per message — a silent `continue` is how the two 2026-07-29 gates
            # vanished. Flagged against the sender because the row is theirs to see.
            stranded = _RELAY_HANDLERS.get(str(kind))
            targets = [a for a in ids if a != sender] if to == "*" else (
                [to] if to in ids and to != sender else [])
            # Never propagate an invalid row. Relay is a fan-out, so delivering a
            # malformed message multiplies one bad row into N and leaves `validate`
            # permanently red — a validator nobody can get to green stops being read.
            # The source row is left untouched in the sender's outbox (single writer);
            # the defect is surfaced for its author to fix.
            try:
                validate_row(bus_root, row, "msg")
            except Exception as exc:  # noqa: BLE001
                advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                                 "epoch": epoch, "kind": "defect", "agent": sender,
                                 "detail": f"outbox msg {src} is schema-invalid and was NOT "
                                           f"relayed: {exc}"})
                continue
            if stranded is not None:
                handler, runs_at = stranded
                flag_key = (str(src), f"handler:{handler}")
                if flag_key not in already_flagged:
                    advisory.append({
                        "schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                        "epoch": epoch, "kind": "defect", "agent": sender,
                        "relayed_src": src, "unreachable": f"handler:{handler}",
                        "check": "relay-handler-reachability",
                        "detail": f"outbox msg {src} is a {kind!r}, whose handler-of-record "
                                  f"{handler!r} runs at authority {runs_at!r} but this daemon is "
                                  f"at {authority!r}. Nothing would have consumed it, so it was "
                                  f"RELAYED to its addressees instead of skipped. Fix the "
                                  f"handler's reachability or the authority — do not silence "
                                  f"this by re-excluding the kind."})
                    already_flagged.add(flag_key)
            # C18 (2026-07-29): needs_routing_to DELIVERS. Until this change the
            # relay fanned out on `to` alone, so a message routed to codex but
            # addressed to coordinator-agent reached codex NEVER — the field read
            # like delivery and was only a hint, which is the shape that misleads.
            # Fan-out is IN ADDITION to `to`, never instead: the coordinator stays
            # in the loop by design. An unreachable recipient (roster row gone, or
            # role retired) is a defect advisory, never a silent drop — a routing
            # field that silently discards is worse than none.
            for rid in (row.get("needs_routing_to") or []):
                rid = str(rid)
                if rid == sender or rid in targets:
                    continue
                if rid not in ids or roles.get(rid) == "retired":
                    reason = ("not a roster id" if rid not in ids
                              else "roster role is 'retired'")
                    if (src, rid) not in already_flagged:
                        advisory.append({
                            "schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                            "epoch": epoch, "kind": "defect", "agent": sender,
                            "relayed_src": src, "unreachable": rid,
                            "detail": f"outbox msg {src} routes to unreachable recipient "
                                      f"{rid!r} ({reason}) and was NOT delivered to it. Fix "
                                      f"needs_routing_to or the roster row; the message DID "
                                      f"still go to its addressable recipients."})
                        already_flagged.add((src, rid))
                    continue
                # C18 code half (2026-07-29): the row exists and is not retired, but
                # DOES ANYONE ANSWER TO IT? Delivery still happens — an inbox row is
                # durable and a merely-offline agent drains it on return, so refusing
                # here would convert transient offline into message loss, the
                # opposite-polarity error (fable-auditor's caution). The sender is
                # warned instead, once per (msg, recipient).
                dead_why = _looks_dead(rid, roster_by_id.get(rid) or {}, states,
                                       live_windows, live_windows_why)
                if dead_why and (src, rid) not in already_flagged:
                    detail = (f"outbox msg {src} routes to {rid!r}, which LOOKS DEAD "
                              f"({dead_why}). It WAS delivered to that inbox and will be "
                              f"read if the session returns, but nothing is draining it "
                              f"now — do not assume this reached a reader. Retire the "
                              f"roster row or route to a live agent.")
                    advisory.append({
                        "schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                        "epoch": epoch, "kind": "defect", "agent": sender,
                        "relayed_src": src, "unreachable": rid, "detail": detail})
                    # C18 second half (2026-07-29): the WARNING needed a reader too.
                    # Advisory rows land in advisory.jsonl and are delivered to nobody —
                    # `status` prints the last five on demand. So the message was a
                    # durable-but-unread sink AND the notice about it was another one,
                    # one level up. Push it into coordinator-agent's inbox, which IS
                    # drained at every task boundary, because coordinator-agent is the
                    # party that can retire the roster row or re-route the work.
                    # Deduped by the same (src, rid) ledger key as the advisory, so a
                    # daemon restart cannot re-deliver it either.
                    # Idempotency is keyed on the NOTICE'S OWN durable evidence — a row
                    # already in coordinator-agent's inbox — not on the advisory ledger.
                    # The ledger is written by the tick loop, so a caller that only calls
                    # relay (every unit test, and any future direct caller) would re-notify
                    # on every pass. Derive the dedupe from what the delivery itself leaves
                    # behind: the same rule this module applies to liveness.
                    if COORDINATOR_AGENT in ids and (src, rid) not in notified:
                        _append_inbox(bus_root, [{
                            "to": COORDINATOR_AGENT, "kind": "defect",
                            "relayed_src": src,
                            "payload": {"unreachable": rid, "from_agent": sender,
                                        "detail": detail,
                                        "action": f"retire {rid!r}'s roster row, or re-route "
                                                  f"the work to a live agent"}}], epoch)
                        notified.add((src, rid))
                    already_flagged.add((src, rid))
                targets.append(rid)
            for target in targets:
                if src in delivered_src.get(target, set()):
                    continue
                # Preserve the original author and payload; only the envelope is new.
                msg = {k: v for k, v in row.items() if k not in ("id", "ts")}
                msg["to"] = target
                msg["relayed_src"] = src
                _append_inbox(bus_root, [msg], epoch)
                delivered_src.setdefault(target, set()).add(src)
                advisory.append({"schema_version": ADVISORY_SCHEMA, "ts": _utcnow_iso(),
                                 "epoch": epoch, "kind": "relayed", "from": sender,
                                 "to": target, "relayed_src": src, "msg_kind": kind})
    return advisory


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

    # C2 relay. Runs at EVERY authority, including manual, because delivering an
    # explicitly-addressed message is transport, not judgment — and gating it on
    # `assign` would leave coordinator-agent's outbound channel dead until M4,
    # which is exactly the defect being fixed.
    #
    # INVARIANT CHANGE, stated rather than slipped in: the daemon now writes
    # inbox/* at manual authority, so it no longer writes "exactly two files" in
    # manual/advisory mode. That file-count was M3's PROXY for "the daemon makes
    # no decisions"; the underlying property still holds (relay chooses nothing —
    # recipient, kind and payload all come from the sender), but M3's acceptance
    # evidence must be restated against the decision property, not the file count.
    if not dry_run:
        roster = [r for r in (config.get("roster") or []) if isinstance(r, dict)]
        advice += relay_outbox_messages(bus_root, roster, epoch, config)
        # C8: boundary surfacing must outlive any single coordinator session, so
        # it runs here (the always-on tier) rather than in a session-local poller.
        advice += detect_task_boundaries(bus_root, roster, epoch)
        advice += redeliver_unacked_messages(bus_root, roster, epoch)
        # C19: an agent idle on unread mail is stuck forever unless something
        # wakes it. Runs at EVERY authority — waking an agent to read its own
        # inbox is transport, not a scheduling decision — and delegates the
        # actual send-keys, with all its guards, to tmux_adapter.py.
        advice += resolve_stuck_agents(bus_root, roster, epoch)
        # C27: the FIRST hop of that same path, and the one that was missing.
        # `pending_operator_actions` below is the net for an operator item the
        # coordinator failed to present; this is the presentation itself. It ran
        # only under `assign` authority until 2026-07-29, which is why two real
        # signature requests were never presented at all — see relay_token_blocks.
        advice += relay_token_blocks(bus_root, config, epoch)
        # C20: the last hop, bus -> operator. Runs at every authority for the same
        # reason relay does — transporting "a human signature is needed" is not a
        # scheduling decision, and its absence is what every one of the seven
        # documented last-hop failures had in common.
        advice += pending_operator_actions(bus_root, roster, epoch)

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


def daemon_liveness(hb: dict) -> tuple[bool | None, str]:
    """Is the pid in the daemon heartbeat actually alive? ``None`` => unknowable.

    P1b (2026-07-29): `cmd_status` printed `state` straight from the heartbeat JSON
    and there was NO pid check anywhere in this module. `cmd_run` writes "idle" only
    on a CLEAN exit, so any crash, `kill -9`, or host reboot leaves `state: working`
    on disk forever. Observed during the 2026-07-29 post-reboot cold start: the
    record read `epoch=11 pid=1928027 age=2157s`, naming a PID that did not exist,
    and `status` reported the dead daemon as `working` — which nearly had the cold
    start conclude the bus was being serviced when nothing was running. The pid was
    already in the record; it just was not read.

    `os.kill(pid, 0)` sends no signal and only asks whether the process exists.
    ``PermissionError`` means it exists under another uid — alive, not absent. An
    unusable or missing pid returns None: "I cannot tell" is reported as such, never
    silently rendered as either alive or dead.
    """
    pid = hb.get("pid")
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None, "heartbeat carries no usable pid"
    if pid <= 0:
        return None, f"heartbeat pid {pid!r} is not a process id"
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False, f"pid {pid} does not exist"
    except PermissionError:
        return True, f"pid {pid} exists (owned by another user)"
    except OSError as exc:
        return None, f"pid {pid} liveness unknown: {exc}"
    return True, f"pid {pid} is alive"


def boot_time(proc: Path = Path("/proc/uptime")) -> float | None:
    """Unix time the host booted, or None where that is not knowable."""
    try:
        return time.time() - float(proc.read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        return None


def heartbeat_predates_boot(mtime: float, *, slack_s: float = 60.0) -> bool | None:
    """Was this heartbeat last written BEFORE the host booted? None => unknowable.

    C26's second check, and it closes what `daemon_liveness` cannot. A pid check
    answers "does a process with that number exist", not "is it MY process" — and
    across a reboot pid numbering restarts, so the recorded pid can be recycled onto
    something entirely unrelated and report alive. That is not hypothetical here:
    C26 was raised from a post-reboot cold start reading `pid=1928027`, and the only
    reason it read as dead is that the number happened not to be re-issued.

    A heartbeat written before boot cannot describe a running process, whatever the
    pid says. `slack_s` absorbs clock adjustment around boot rather than pretending
    the two clocks are exact.
    """
    boot = boot_time()
    if boot is None:
        return None
    return mtime < boot - slack_s


def cmd_status(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    hb_path = _heartbeat_path(bus_root)
    try:
        hb = json.loads(hb_path.read_text(encoding="utf-8"))
        mtime = hb_path.stat().st_mtime
        age = time.time() - mtime
        alive, why = daemon_liveness(hb)
        if heartbeat_predates_boot(mtime) and alive is not False:
            # The pid check is OVERRIDDEN, not merely supplemented: it is the check
            # that is wrong in this case, because it is answering about a recycled
            # number rather than about this daemon.
            alive, why = False, (f"{why}, but the heartbeat was last written BEFORE this host "
                                 f"booted — the pid is recycled, not this daemon")
        state = str(hb.get("state"))
        # The heartbeat's own claim is never overwritten — it is EVIDENCE, and the
        # record of what the last daemon believed is worth keeping. It is annotated.
        if alive is False:
            state = f"{state} (STALE — DAEMON IS NOT RUNNING: {why})"
        elif alive is None:
            state = f"{state} (unverified: {why})"
        print(f"state={state} epoch={hb.get('epoch')} pid={hb.get('pid')} "
              f"age={age:.0f}s note={hb.get('note')!r}")
    except Exception:  # noqa: BLE001
        print("no coordinator-daemon heartbeat")
    blockers = capability_blockers(_load_config(bus_root))
    print("M5 capabilities:")
    for b in blockers:
        print(f"  BLOCKED  {b}")
    if not blockers:
        print("  all authorised, capped and implemented")
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
