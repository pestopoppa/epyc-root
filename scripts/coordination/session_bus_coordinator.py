#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""session_bus_coordinator.py — the coordinator-daemon (M3: read-only advisory).

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md
Contract:       coordination/session-bus/BUS_PROTOCOL.md

WHAT THIS IS. The deterministic, always-on tier of the coordinator. It ticks,
senses lane occupancy, folds the queue, and computes what it *would* assign.
It never analyzes, reviews, or edits work products — queue/routing/watchdog only
("the moment it reviews, it's a second main" — operator).

M3 IS ADVISORY. With `coordinator_daemon.authority` set to `manual` or
`advisory` the daemon writes ONLY two files, both of which it owns:

    heartbeats/coordinator-daemon.json   its own liveness + epoch
    advisory.jsonl                        would-assign / saturation records

It does NOT write queue.jsonl or any inbox in advisory mode, so a running daemon
cannot disturb the M1 manual workflow. Real assignment is M4 and requires
`authority: assign`; until then the daemon refuses to take it even if asked.

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination.session_bus import (  # noqa: E402
    COORDINATOR_DAEMON,
    DEFAULT_BUS_ROOT,
    TERMINAL_STATES,
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
    """Occupancy per lane. Fail-safe: anything unknown counts as busy."""
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


def _eligible(row: dict, latest: dict[str, dict], snapshot: dict, token_text: str) -> tuple[bool, str]:
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
    lane = row.get("lane")
    if lane in {"cpu", "gpu"} and snapshot.get(f"{lane}_busy"):
        return False, f"lane {lane} busy (load_class={snapshot.get('load_class')})"
    if row.get("contention_class") == "exclusive-contiguous" and snapshot.get("cpu_busy"):
        return False, "exclusive-contiguous needs a quiet host"
    return True, "eligible"


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
    snapshot = _lane_snapshot()
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
            ok, why = _eligible(row, latest, snapshot, token_text)
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


def tick(bus_root: Path, epoch: int, *, dry_run: bool = False) -> list[dict]:
    config = _load_config(bus_root)
    authority = _authority(config)
    if authority == "assign":
        # M4 is not built. Refusing is the safe failure: an unbuilt assign path
        # must never be silently approximated by the advisory one.
        raise SystemExit(
            "coordinator_daemon.authority='assign' but assignment (M4) is not implemented. "
            "Set authority to 'advisory' or build M4 first."
        )
    advice = compute_advice(bus_root, config, epoch) + audit(bus_root, epoch)
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
