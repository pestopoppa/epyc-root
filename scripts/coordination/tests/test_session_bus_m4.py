#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""M4 assignment-authority tests for the coordinator-daemon.

M4 is the first code that MUTATES the queue, so these tests are deliberately
paranoid. Every case runs against a throwaway copy of the bus with
`authority: assign`; the real bus is never touched and stays in advisory mode.

Covers: the full assign -> ack -> status -> complete transcription chain, token
relay (including the defect path for an unvalidated request), the stall ladder's
three rungs, idempotency under repeated ticks, and the invariant that advisory
mode still writes only two files.

Usage: scripts/coordination/tests/test_session_bus_m4.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

BUS_SRC = REPO_ROOT / "coordination" / "session-bus"
DAEMON = REPO_ROOT / "scripts" / "coordination" / "session_bus_coordinator.py"

from scripts.coordination.session_bus import fold_queue  # noqa: E402

QV = "session_bus.queue.v1"
MV = "session_bus.msg.v1"


def now_iso(offset_s: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_s)).isoformat(timespec="seconds")


class Bus:
    """A throwaway bus copy with a chosen authority level."""

    def __init__(self, authority: str = "assign"):
        self.base = Path(tempfile.mkdtemp())
        self.root = self.base / "bus"
        shutil.copytree(BUS_SRC, self.root)
        # Start from an empty queue/outbox/inbox so cases are isolated.
        (self.root / "queue.jsonl").write_text("")
        for d in ("inbox", "outbox", "heartbeats", "cursors"):
            for f in (self.root / d).glob("*"):
                f.unlink()
        cfg = self.root / "config.yaml"
        cfg.write_text(cfg.read_text().replace("authority: manual", f"authority: {authority}"))
        self.tokens = self.root / "tokens" / "token-queue.md"

    def add_queue(self, **row) -> None:
        full = {"schema_version": QV, "ts": now_iso(), "epoch": 0, **row}
        with (self.root / "queue.jsonl").open("a") as fh:
            fh.write(json.dumps(full) + "\n")

    def add_outbox(self, agent: str, **msg) -> None:
        n = len((self.root / "outbox" / f"{agent}.jsonl").read_text().splitlines()) + 1 \
            if (self.root / "outbox" / f"{agent}.jsonl").exists() else 1
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        full = {"schema_version": MV, "ts": now_iso(), "from": agent,
                "id": f"msg-{stamp}-{n}-{agent}", "to": "coordinator-daemon", **msg}
        with (self.root / "outbox" / f"{agent}.jsonl").open("a") as fh:
            fh.write(json.dumps(full) + "\n")

    def heartbeat(self, agent: str, state: str = "working", task_id=None) -> None:
        (self.root / "heartbeats" / f"{agent}.json").write_text(json.dumps(
            {"agent": agent, "state": state, "task_id": task_id, "ts": now_iso()}))

    def tick(self, lanes: dict | None = None) -> str:
        """One tick with a DETERMINISTIC lane snapshot.

        Real host probing makes these tests slow (~2s each) and host-dependent;
        a test whose result depends on whether a role happens to be serving is a
        test that will eventually lie. Default: both compute lanes idle.
        """
        import os
        env = {**os.environ, "SESSION_BUS_LANE_SNAPSHOT_JSON": json.dumps(
            lanes or {"cpu_busy": False, "gpu_busy": False, "load_class": "quiet"})}
        r = subprocess.run([str(DAEMON), "--bus-root", str(self.root), "once"],
                           capture_output=True, text=True, env=env)
        return r.stdout + r.stderr

    def status_of(self, tid: str):
        return (fold_queue(self.root).get(tid) or {}).get("status")

    def row(self, tid: str) -> dict:
        return fold_queue(self.root).get(tid) or {}

    def inbox(self, agent: str) -> list[dict]:
        p = self.root / "inbox" / f"{agent}.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

    def cleanup(self) -> None:
        shutil.rmtree(self.base, ignore_errors=True)


RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, why: str) -> None:
    RESULTS.append((bool(ok), why))
    print(f"  {'PASS' if ok else 'FAIL'}  {why}")


def test_transcription_chain() -> None:
    print("\n== assign -> ack -> status -> complete ==")
    b = Bus("assign")
    try:
        b.add_queue(task_id="doc-1", status="READY", lane="none", gating="none", priority="P1")
        b.heartbeat("claude-main", "idle")
        b.tick()
        check(b.status_of("doc-1") == "ASSIGNED", f"assigned (got {b.status_of('doc-1')})")
        owner = b.row("doc-1").get("owner")
        check(owner in {"codex", "claude-main"}, f"owner set ({owner})")
        check(bool(b.row("doc-1").get("lease_expires_ts")), "lease_expires_ts set")
        msgs = b.inbox(owner)
        check(any(m.get("kind") == "task-assign" for m in msgs), "task-assign delivered to inbox")

        b.add_outbox(owner, kind="ack", task_id="doc-1", corr_id="c1")
        b.tick()
        check(b.status_of("doc-1") == "CLAIMED", f"ack -> CLAIMED (got {b.status_of('doc-1')})")

        b.add_outbox(owner, kind="status", task_id="doc-1", corr_id="c1")
        b.tick()
        check(b.status_of("doc-1") == "RUNNING", f"status -> RUNNING (got {b.status_of('doc-1')})")

        b.add_outbox(owner, kind="task-complete", task_id="doc-1", corr_id="c1",
                     payload={"outcome": "pass"})
        b.tick()
        check(b.status_of("doc-1") == "DONE_PASS", f"complete -> DONE_PASS (got {b.status_of('doc-1')})")

        before = len((b.root / "queue.jsonl").read_text().splitlines())
        b.tick(); b.tick()
        after = len((b.root / "queue.jsonl").read_text().splitlines())
        check(before == after, f"idempotent: repeated ticks append nothing ({before} -> {after})")
    finally:
        b.cleanup()


def test_failure_outcome() -> None:
    print("\n== task-complete with outcome=fail ==")
    b = Bus("assign")
    try:
        b.add_queue(task_id="f-1", status="RUNNING", lane="none", gating="none", owner="codex")
        b.add_outbox("codex", kind="task-complete", task_id="f-1",
                     payload={"outcome": "fail", "reason": "scorer mismatch"})
        b.tick()
        check(b.status_of("f-1") == "FAILED", f"fail -> FAILED (got {b.status_of('f-1')})")
        check(b.row("f-1").get("failure_reason") == "scorer mismatch", "failure_reason carried")
    finally:
        b.cleanup()


def test_token_relay() -> None:
    print("\n== token relay ==")
    b = Bus("assign")
    try:
        b.add_queue(task_id="g-1", status="RUNNING", lane="none", gating="none", owner="codex")
        b.add_outbox("codex", kind="token-request", task_id="g-1", payload={
            "gate_id": "OP-TEST-GATE", "block_ref": "tokens/token-queue.md#OP-TEST-GATE",
            "validated": {"cmd": "echo hello", "dry_run_exit": 0, "dry_run_evidence": "ran clean"}})
        b.tick()
        text = b.tokens.read_text()
        check("OP-TEST-GATE" in text, "gate block relayed into token-queue.md")
        check("echo hello" in text, "pre-validated command included verbatim")
        check(b.status_of("g-1") == "HELD_OP_GATE", f"task held (got {b.status_of('g-1')})")

        n_before = text.count("OP-TEST-GATE")
        b.tick()
        check(b.tokens.read_text().count("OP-TEST-GATE") == n_before,
              "idempotent: gate not re-appended on a second tick")

        # unvalidated request -> defect, no block
        b.add_queue(task_id="g-2", status="RUNNING", lane="none", gating="none", owner="codex")
        b.add_outbox("codex", kind="token-request", task_id="g-2",
                     payload={"gate_id": "OP-UNVALIDATED", "block_ref": "x"})
        out = b.tick()
        check("OP-UNVALIDATED" not in b.tokens.read_text(),
              "unvalidated request NOT relayed")
        check("token-prevalidation" in out, "unvalidated request raises a defect")
    finally:
        b.cleanup()


def test_stall_ladder() -> None:
    print("\n== stall ladder ==")
    b = Bus("assign")
    try:
        # hard stall: lease expired, attempts remain -> requeue
        b.add_queue(task_id="s-1", status="RUNNING", lane="none", gating="none", owner="codex",
                    lease_expires_ts=now_iso(-60), attempt=0, max_attempts=3)
        out = b.tick()
        check(b.status_of("s-1") == "STALE_REQUEUED", f"expired lease -> STALE_REQUEUED (got {b.status_of('s-1')})")
        check(b.row("s-1").get("attempt") == 1, "attempt incremented")
        check(b.row("s-1").get("owner") is None, "owner cleared for any capable main")
        check("hard-stall" in out, "defect row emitted for the hard stall")

        # give-up: attempts exhausted
        b2 = Bus("assign")
        try:
            b2.add_queue(task_id="s-2", status="RUNNING", lane="none", gating="none", owner="codex",
                         lease_expires_ts=now_iso(-60), attempt=3, max_attempts=3)
            b2.tick()
            check(b2.status_of("s-2") == "INFRA_BLOCKED",
                  f"attempts exhausted -> INFRA_BLOCKED (got {b2.status_of('s-2')})")
            check("GIVE-UP" in b2.tokens.read_text(), "give-up alert raised in the token queue")
        finally:
            b2.cleanup()

        # soft stall: stale heartbeat, live lease, no outbox traffic -> nudge
        b3 = Bus("assign")
        try:
            b3.add_queue(task_id="s-3", status="RUNNING", lane="none", gating="none",
                         owner="codex", lease_expires_ts=now_iso(3600), heartbeat_grace_s=1)
            b3.heartbeat("codex", "working", "s-3")
            import os, time as _t
            hb = b3.root / "heartbeats" / "codex.json"
            os.utime(hb, (_t.time() - 600, _t.time() - 600))
            b3.tick()
            nudges = [m for m in b3.inbox("codex") if m.get("kind") == "nudge"]
            check(bool(nudges), "soft stall -> nudge delivered")
            check(b3.status_of("s-3") == "RUNNING", "soft stall does not change status")
        finally:
            b3.cleanup()
    finally:
        b.cleanup()


def test_lane_gating_and_pausability() -> None:
    print("\n== lane gating + exclusive-contiguous (deterministic via the seam) ==")
    b = Bus("assign")
    try:
        b.add_queue(task_id="cpu-1", status="READY", lane="cpu", gating="cpu", priority="P0")
        b.tick(lanes={"cpu_busy": True, "gpu_busy": False, "load_class": "busy"})
        check(b.status_of("cpu-1") == "READY", "cpu task NOT assigned while the cpu lane is busy")

        b.tick(lanes={"cpu_busy": False, "gpu_busy": False, "load_class": "quiet"})
        check(b.status_of("cpu-1") == "ASSIGNED", "same task assigned once the lane frees")
    finally:
        b.cleanup()

    b2 = Bus("assign")
    try:
        b2.add_queue(task_id="bench-1", status="READY", lane="cpu", gating="cpu", priority="P0",
                     contention_class="exclusive-contiguous")
        b2.tick(lanes={"cpu_busy": True, "gpu_busy": False, "load_class": "serial_ok"})
        check(b2.status_of("bench-1") == "READY",
              "exclusive-contiguous run NOT assigned on a non-quiet host")
        b2.tick(lanes={"cpu_busy": False, "gpu_busy": False, "load_class": "quiet"})
        check(b2.status_of("bench-1") == "ASSIGNED",
              "exclusive-contiguous run assigned on a quiet host")
    finally:
        b2.cleanup()

    b3 = Bus("assign")
    try:
        b3.add_queue(task_id="replay-1", status="READY", lane="cpu", gating="cpu", priority="P1",
                     replay_eligible=True)
        b3.tick(lanes={"cpu_busy": True, "gpu_busy": False, "load_class": "busy"})
        check(b3.status_of("replay-1") == "ASSIGNED",
              "R9: replay_eligible assigned despite a busy cpu lane")
    finally:
        b3.cleanup()


def test_lease_revocation() -> None:
    print("\n== R4: lease revocation is quiesce-and-drain, never forcible ==")
    b = Bus("assign")
    try:
        b.add_queue(task_id="rv-1", status="RUNNING", lane="cpu", gating="cpu", owner="codex",
                    lease_expires_ts=now_iso(3600), priority="P2")
        b.heartbeat("codex", "working", "rv-1")
        # authorised: coordinator-agent holds lease_grant authority
        b.add_outbox("coordinator-agent", kind="lease-revoke", task_id="rv-1",
                     payload={"reason": "production-live needs the cpu lane",
                              "yield_to": "production-live"})
        b.tick()
        check(b.row("rv-1").get("revoking") is True, "row marked revoking")
        check(b.status_of("rv-1") == "RUNNING",
              "status unchanged — it IS still running (axiom 4: no forcible stop)")
        nudges = [m for m in b.inbox("codex") if m.get("kind") == "nudge"]
        check(bool(nudges), "holder nudged to drain")
        instr = (nudges[-1].get("payload") or {}).get("instruction", "") if nudges else ""
        check("lane:none" in instr, "nudge tells the holder to keep working on lane:none, not idle")

        n_before = len([m for m in b.inbox("codex") if m.get("kind") == "nudge"])
        b.tick()
        check(len([m for m in b.inbox("codex") if m.get("kind") == "nudge"]) == n_before,
              "idempotent: no repeat nudge on the next tick")

        # holder drains at its boundary -> lease released, task re-assignable
        b.heartbeat("codex", "draining", "rv-1")
        b.tick()
        check(b.status_of("rv-1") == "READY", f"drained -> READY (got {b.status_of('rv-1')})")
        check(b.row("rv-1").get("owner") is None, "owner cleared on release")
        check(b.row("rv-1").get("revoking") is False, "revoking flag cleared")

        # The one-tick exclusion must carry NO lasting penalty: with nothing
        # higher-priority waiting, ordinary priority ordering resumes the task.
        b.tick()
        check(b.status_of("rv-1") == "ASSIGNED",
              f"resumes on the NEXT tick when nothing outranks it (got {b.status_of('rv-1')})")
    finally:
        b.cleanup()

    b2 = Bus("assign")
    try:
        b2.add_queue(task_id="rv-2", status="RUNNING", lane="cpu", gating="cpu", owner="codex",
                     lease_expires_ts=now_iso(3600))
        b2.heartbeat("codex", "working", "rv-2")
        # UNauthorised: a main cannot revoke another main's lease
        b2.add_outbox("claude-main", kind="lease-revoke", task_id="rv-2",
                      payload={"reason": "I want the lane"})
        out = b2.tick()
        check(not b2.row("rv-2").get("revoking"), "unauthorised revocation NOT applied")
        check("lease-authority" in out, "unauthorised revocation raises a defect")
    finally:
        b2.cleanup()

    b3 = Bus("assign")
    try:
        # a revoking task must not be handed to anyone else while still held
        b3.add_queue(task_id="rv-3", status="READY", lane="none", gating="none", priority="P0",
                     revoking=True)
        b3.tick()
        check(b3.status_of("rv-3") == "READY",
              "revoking task not assigned even when READY and top priority")
    finally:
        b3.cleanup()

    b4 = Bus("assign")
    try:
        # the yield actually lands: the freed lane goes to the higher-priority task
        b4.add_queue(task_id="yield-victim", status="RUNNING", lane="cpu", gating="cpu",
                     owner="codex", lease_expires_ts=now_iso(3600), priority="P3")
        b4.add_queue(task_id="yield-target", status="READY", lane="cpu", gating="cpu",
                     priority="P0", priority_class="production-live")
        b4.heartbeat("codex", "working", "yield-victim")
        b4.add_outbox("coordinator-agent", kind="lease-revoke", task_id="yield-victim",
                      payload={"reason": "yield to production-live", "yield_to": "yield-target"})
        b4.tick(lanes={"cpu_busy": False, "gpu_busy": False, "load_class": "quiet"})
        b4.heartbeat("codex", "draining", "yield-victim")
        b4.tick(lanes={"cpu_busy": False, "gpu_busy": False, "load_class": "quiet"})
        check(b4.status_of("yield-target") == "ASSIGNED",
              f"higher-priority task claims the freed lane (got {b4.status_of('yield-target')})")
        check(b4.status_of("yield-victim") == "READY",
              f"yielded task waits its turn (got {b4.status_of('yield-victim')})")
    finally:
        b4.cleanup()


def test_advisory_writes_only_two_files() -> None:
    print("\n== advisory mode still writes only two files (M3 invariant) ==")
    b = Bus("advisory")
    try:
        b.add_queue(task_id="adv-1", status="READY", lane="none", gating="none", priority="P1")
        before = {p: p.stat().st_mtime_ns for p in b.root.rglob("*") if p.is_file()}
        b.tick()
        after = {p: p.stat().st_mtime_ns for p in b.root.rglob("*") if p.is_file()}
        changed = {p.name for p in set(after) if before.get(p) != after[p]}
        allowed = {"advisory.jsonl", "coordinator-daemon.json"}
        check(changed <= allowed, f"only {allowed} touched; changed={changed or '{}'}")
        check(b.status_of("adv-1") == "READY", "advisory mode did NOT assign")
    finally:
        b.cleanup()


def main() -> int:
    test_transcription_chain()
    test_failure_outcome()
    test_token_relay()
    test_stall_ladder()
    test_lane_gating_and_pausability()
    test_lease_revocation()
    test_advisory_writes_only_two_files()
    failed = [w for ok, w in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        for w in failed:
            print(f"  FAILED: {w}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
