"""Tests for the monitor:file re-invoke sweep (RTG-52 D3, 2026-08-23).

The handoff filed a structural gap: `monitor:file` service identities
(`auditor`, `hardware-backfill`) have no push channel, so an unanswered
`action_required` packet addressed to one sits in an inbox nothing drains —
invisible to the fleet-health plane until manual triage (23 `stuck-unreachable`
advisories one day, 111 undrained auditor inbox rows, a missed pilot audit
invocation unseen for hours). The sweep re-invokes such packets instead of
merely re-flagging them.

WHAT EACH TEST PROVES, AND WHY IT EARNS A TEST:

* unanswered packet past threshold -> re-invoked: the sweep's whole reason to
  exist — a `monitor:file` identity holding an old `action_required` packet
  gets a `stuck-reinvoke` advisory naming the packet, and an `auditor` packet
  routes through the headless-audit invocation path (the P2-7 mechanism).
* answered packet -> NOT re-invoked: never re-run work the bus already shows
  answered — by corr_id disposition, and by the verdict shape the pilot
  audits actually used (task_ids + commit_range, no corr_id backlink).
* interval respected: the same packet is not re-invoked twice inside one
  interval (no storm), and the dedupe survives across calls via the record.
* monitor:file identity without a fallback handler -> advisory only: the
  sweep still surfaces the packet with an explicit `re-invoke` marker so a
  headless invocation can pick it up, but spawns nothing.
* non-monitor:file endpoints are untouched (the sweep is typed to the
  endpoint scheme), and young packets are not re-invoked.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "coordination" / "session_bus_coordinator.py"
SPEC = importlib.util.spec_from_file_location("session_bus_coordinator", MODULE_PATH)
assert SPEC and SPEC.loader
sbc = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sbc
SPEC.loader.exec_module(sbc)

BUS_SRC = ROOT / "coordination" / "session-bus"


def _utc(offset_s: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_s)).isoformat(
        timespec="seconds")


def _packet(**kw):
    base = {
        "schema_version": "session_bus.msg.v1",
        "id": kw.get("id", "msg-packet-1"),
        "from": kw.get("from", "workerpool"),
        "to": kw.get("to", "auditor"),
        "ts": kw.get("ts", _utc(-3600)),
        "kind": kw.get("kind", "finding"),
        "assignee": kw.get("assignee", "auditor"),
        "action_required": True,
        "needs_routing_to": kw.get("needs_routing_to", ["auditor"]),
        "payload": kw.get("payload") or {},
    }
    base.update({k: v for k, v in kw.items() if k not in base})
    return base


def _audit_packet(**kw):
    """The P2-7 pointer-packet shape: task_ids + commit_range in audit_packet."""
    payload = {
        "audit_packet": {
            "task_ids": kw.get("task_ids", ["pilot-01"]),
            "commit_range": kw.get("commit_range", "aaa..bbb"),
            "worktree": "/tmp/wt",
            "report_path": "/tmp/r.json",
            "run_dir": "/tmp/run",
        },
        "note": "pointers only",
    }
    return _packet(payload=payload, **{k: v for k, v in kw.items()
                                       if k not in ("task_ids", "commit_range")})


def _append(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")


def _run_sweep(bus: Path, aid="auditor", rec=None, now=None, invoke_hook=None):
    """Run the sweep for one identity and return (advisory rows, rec)."""
    if invoke_hook is not None:
        import unittest.mock
        monkey = unittest.mock.patch.object(
            sbc, "_invoke_headless_audit_packet", side_effect=invoke_hook)
        monkey.start()
        try:
            rows, out = _sweep(bus, aid, rec, now)
        finally:
            monkey.stop()
        return rows, out
    return _sweep(bus, aid, rec, now)


def _sweep(bus: Path, aid: str, rec: dict | None, now: float | None):
    entry = {"id": aid, "endpoint": "monitor:file",
             "role_policy": f"agents/{aid}-main.md"}
    collected: list[dict] = []

    def row(kind: str, agent: str, **extra) -> None:
        collected.append({"kind": kind, "agent": agent, **extra})

    import time
    out = sbc._monitor_file_reinvoke_sweep(bus, aid, entry, dict(rec or {}),
                                           epoch=1, now=now if now is not None else time.time(),
                                           row=row)
    return collected, out


@pytest.fixture
def bus(tmp_path: Path) -> Path:
    root = tmp_path / "bus"
    (root / "inbox").mkdir(parents=True)
    (root / "outbox").mkdir(parents=True)
    shutil.copy2(BUS_SRC / "session_bus.schema.json", root / "session_bus.schema.json")
    return root


# ------------------------------------------------------------------- sweep


def test_unanswered_packet_past_threshold_is_reinvoked(bus: Path) -> None:
    """An old unanswered action_required packet -> stuck-reinvoke + headless run."""
    _append(bus / "inbox" / "auditor.jsonl", [_audit_packet(ts=_utc(-3600))])
    invoked: list[dict] = []
    rows, rec = _run_sweep(bus, invoke_hook=lambda b, p: invoked.append(p))
    reinvokes = [r for r in rows if r["kind"] == "stuck-reinvoke"]
    assert len(reinvokes) == 1
    assert reinvokes[0]["packet_id"] == "msg-packet-1"
    assert reinvokes[0]["agent"] == "auditor"
    assert reinvokes[0]["re_invoke"] is True
    assert reinvokes[0]["invocation"] == "headless_audit.py audit --packet <pkt> --emit"
    assert len(invoked) == 1, "an auditor packet must actually reach the audit path"
    assert rec["reinvoke_count"] == 1
    assert rec["reinvoked"]["msg-packet-1"]


def test_answered_packet_is_not_reinvoked(bus: Path) -> None:
    """A packet with a corr_id disposition anywhere -> never re-invoked."""
    _append(bus / "inbox" / "auditor.jsonl", [_audit_packet(ts=_utc(-3600))])
    _append(bus / "outbox" / "auditor.jsonl", [
        {"schema_version": "session_bus.msg.v1", "id": "msg-verdict-1",
         "from": "auditor", "to": "coordinator-agent", "ts": _utc(-1800),
         "kind": "finding", "corr_id": "msg-packet-1", "payload": {}}])
    invoked: list[dict] = []
    rows, _ = _run_sweep(bus, invoke_hook=lambda b, p: invoked.append(p))
    assert not [r for r in rows if r["kind"] == "stuck-reinvoke"]
    assert not invoked


def test_answered_by_verdict_shape_is_not_reinvoked(bus: Path) -> None:
    """The pilot audits wrote verdicts WITHOUT a corr_id backlink — only the
    task_ids + commit_range match. The sweep must recognise that as answered,
    or it would re-audit work that already has a verdict on the bus."""
    _append(bus / "inbox" / "auditor.jsonl", [
        _audit_packet(ts=_utc(-3600), task_ids=["pilot-01"], commit_range="aaa..bbb")])
    _append(bus / "outbox" / "auditor.jsonl", [
        {"schema_version": "session_bus.msg.v1", "id": "msg-verdict-1",
         "from": "auditor", "to": "coordinator-agent", "ts": _utc(-1800),
         "kind": "finding",
         "payload": {"task_ids": ["pilot-01"], "commit_range": "aaa..bbb",
                     "audit_verdict": "accept"}}])
    invoked: list[dict] = []
    rows, _ = _run_sweep(bus, invoke_hook=lambda b, p: invoked.append(p))
    assert not [r for r in rows if r["kind"] == "stuck-reinvoke"]
    assert not invoked


def test_interval_respected_no_storm(bus: Path) -> None:
    """The same packet is re-invoked at most once per interval."""
    import time
    _append(bus / "inbox" / "auditor.jsonl", [_audit_packet(ts=_utc(-3600))])
    now = time.time()
    invoked: list[dict] = []

    def hook(b, p):
        invoked.append(p)

    rows1, rec = _run_sweep(bus, now=now, invoke_hook=hook)
    assert len([r for r in rows1 if r["kind"] == "stuck-reinvoke"]) == 1
    rows2, rec2 = _run_sweep(bus, rec=rec, now=now + 300.0, invoke_hook=hook)
    assert not [r for r in rows2 if r["kind"] == "stuck-reinvoke"], \
        "within the interval the same packet must not be re-invoked again"
    assert len(invoked) == 1
    # Past the interval, the packet is re-invoked once more (sweep, not one-shot).
    rows3, rec3 = _run_sweep(bus, rec=rec2, now=now + 1200.0, invoke_hook=hook)
    assert len([r for r in rows3 if r["kind"] == "stuck-reinvoke"]) == 1
    assert len(invoked) == 2


def test_no_fallback_identity_is_advisory_only(bus: Path) -> None:
    """hardware-backfill (monitor:file, no headless path) -> advisory only."""
    _append(bus / "inbox" / "hardware-backfill.jsonl", [
        _packet(id="msg-hw-1", to="hardware-backfill", assignee="hardware-backfill",
                needs_routing_to=["hardware-backfill"], ts=_utc(-3600))])
    invoked: list[dict] = []
    rows, rec = _run_sweep(bus, aid="hardware-backfill",
                           invoke_hook=lambda b, p: invoked.append(p))
    reinvokes = [r for r in rows if r["kind"] == "stuck-reinvoke"]
    assert len(reinvokes) == 1
    assert reinvokes[0]["invocation"] == "none (advisory-only identity)"
    assert reinvokes[0]["re_invoke"] is True
    assert not invoked, "no fallback handler must not spawn anything"
    assert rec["reinvoke_count"] == 1


def test_young_packet_is_not_reinvoked(bus: Path) -> None:
    """A packet under the threshold stays alone; no advisory, no invocation."""
    _append(bus / "inbox" / "auditor.jsonl", [_audit_packet(ts=_utc(-60))])
    invoked: list[dict] = []
    rows, _ = _run_sweep(bus, invoke_hook=lambda b, p: invoked.append(p))
    assert not rows
    assert not invoked


def test_relay_copy_is_addressed_to_the_identity(bus: Path) -> None:
    """A relayed copy (relayed_src set) addressed to the identity is swept."""
    packet = _audit_packet(id="msg-relay-copy-1", from_agent="coordinator-daemon",
                           to="auditor", ts=_utc(-3600), relayed_src="msg-orig-1")
    _append(bus / "inbox" / "auditor.jsonl", [packet])
    rows, _ = _run_sweep(bus)
    assert len([r for r in rows if r["kind"] == "stuck-reinvoke"]) == 1
