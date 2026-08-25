"""Tests for scripts/coordination/relay_ledger_adjudicate.py (RTG-52 D2).

Adjudicates the daemon's `relay_state.json` flagged ledger against the bus
files, classifying every flagged [msg_id, handler] pair as handled /
delivered-not-drained / dropped / schema-invalid / unknown, and (--apply-clear)
writing a new ledger keeping only the entries that must stay flagged.

WHAT EACH TEST PROVES, AND WHY IT EARNS A TEST:

* handled -> clearable: the flag's concern (nothing consumed it) is resolved by
  a follow-up disposition on the bus — the ONLY thing the protocol treats as a
  disposition (BUS_PROTOCOL.md: a bare ack is receipt, not action, so the test
  must distinguish substantive from bare-ack references).
* absent -> dropped: a flagged message present nowhere on the bus is a
  candidate drop — the exact "nothing distinguishes handled from dropped" gap
  the handoff filed.
* schema-invalid -> classified: the flag shape that means "never relayed" must
  be its own class, not folded into unknown.
* unknown stays: a message that exists only in the sender's outbox (flagged,
  never delivered, no disposition) must stay flagged under --apply-clear.
* delivered-not-drained stays: delivered but nobody answered it — the flag is
  still live.
* MUTATION: remove the message from the fixture inbox -> classification flips
  to dropped. Without the mutation half, a classifier that never actually
  consults the bus files would pass its own positive tests.
* --apply-clear preserves the `delivered` map verbatim and refuses while a
  daemon is alive.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.coordination import relay_ledger_adjudicate as adj

REPO_ROOT = Path(__file__).resolve().parents[2]
BUS_SRC = REPO_ROOT / "coordination" / "session-bus"


def _row(**kw):
    row = {
        "schema_version": "session_bus.msg.v1",
        "id": kw.get("id", "msg-x"),
        "from": kw.get("from", "mainA"),
        "to": kw.get("to", "coordinator-daemon"),
        "ts": kw.get("ts", "2026-08-12T08:00:00+00:00"),
        "kind": kw.get("kind", "finding"),
        "payload": kw.get("payload") or {},
    }
    row.update(kw)
    return row


def _append(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")


@pytest.fixture
def bus(tmp_path: Path) -> Path:
    """A throwaway bus with the real schema file and empty runtime surfaces."""
    root = tmp_path / "bus"
    (root / "inbox").mkdir(parents=True)
    (root / "outbox").mkdir(parents=True)
    (root / "archive").mkdir()
    shutil.copy2(BUS_SRC / "session_bus.schema.json", root / "session_bus.schema.json")
    return root


def _write_ledger(bus: Path, flagged: list[tuple[str, str]], delivered=None) -> None:
    (bus / "relay_state.json").write_text(json.dumps({
        "schema_version": "session_bus.relay_state.v1",
        "ts": "2026-08-16T12:00:00+00:00",
        "delivered": delivered or {"auditor": ["msg-handled-1"], "inference": []},
        "flagged": [list(p) for p in flagged],
    }, indent=2))


def _class_of(report: dict, msg_id: str, handler: str) -> dict:
    for e in report["entries"]:
        if e["msg_id"] == msg_id and e["handler"] == handler:
            return e
    raise AssertionError(f"{msg_id} [{handler}] not in report")


# --------------------------------------------------------------- fixtures


def test_handled_is_clearable(bus: Path) -> None:
    """A flagged message answered by a substantive disposition -> handled."""
    _write_ledger(bus, [("msg-handled-1", "auditor")])
    # The relayed copy the recipient saw (new id, relayed_src = original).
    _append(bus / "inbox" / "auditor.jsonl", [
        _row(id="msg-relay-copy-1", from_agent="coordinator-daemon", to="auditor",
             relayed_src="msg-handled-1")])
    # The recipient's substantive disposition referencing the COPY it saw.
    _append(bus / "outbox" / "auditor.jsonl", [
        _row(id="msg-verdict-1", from_agent="auditor", to="coordinator-agent",
             kind="finding", corr_id="msg-relay-copy-1",
             payload={"audit_verdict": "accept"})])

    report = adj.adjudicate(bus)
    assert report["counts"]["handled"] == 1
    e = _class_of(report, "msg-handled-1", "auditor")
    assert e["class"] == "handled"
    assert e["clearable"] is True


def test_bare_ack_is_not_handled(bus: Path) -> None:
    """A bare ack is receipt, not action — the flag stays live (BUS_PROTOCOL)."""
    _write_ledger(bus, [("msg-handled-1", "auditor")])
    _append(bus / "inbox" / "auditor.jsonl", [
        _row(id="msg-relay-copy-1", from_agent="coordinator-daemon", to="auditor",
             relayed_src="msg-handled-1")])
    _append(bus / "outbox" / "auditor.jsonl", [
        _row(id="msg-ack-1", from_agent="auditor", to="coordinator-agent",
             kind="ack", corr_id="msg-relay-copy-1")])

    report = adj.adjudicate(bus)
    e = _class_of(report, "msg-handled-1", "auditor")
    assert e["class"] == "delivered-not-drained"
    assert e["clearable"] is False


def test_absent_is_dropped(bus: Path) -> None:
    """A flagged message on no bus surface at all -> dropped (candidate loss)."""
    _write_ledger(bus, [("msg-vanished-1", "handler:intake_proposals")])
    report = adj.adjudicate(bus)
    e = _class_of(report, "msg-vanished-1", "handler:intake_proposals")
    assert e["class"] == "dropped"
    assert report["defect_rows"], "a proven-lost entry must be filed as a defect row"


def test_mutation_inbox_removal_flips_to_dropped(bus: Path) -> None:
    """Removing the message from the fixture inbox flips the classification.

    Without this, a classifier that ignores the bus files passes its own
    positive tests — the mutation is the half that proves the evidence is
    actually read.
    """
    _write_ledger(bus, [("msg-only-in-inbox-1", "inference")])
    inbox = bus / "inbox" / "inference.jsonl"
    _append(inbox, [_row(id="msg-only-in-inbox-1", from_agent="mainB", to="inference")])

    assert _class_of(adj.adjudicate(bus), "msg-only-in-inbox-1",
                     "inference")["class"] == "delivered-not-drained"

    # Mutation: the inbox copy disappears (rotation/truncation/restore).
    inbox.write_text("")
    assert _class_of(adj.adjudicate(bus), "msg-only-in-inbox-1",
                     "inference")["class"] == "dropped"


def test_schema_invalid_is_classified(bus: Path) -> None:
    """The 'never relayed, row failed validation' flag shape -> schema-invalid."""
    _write_ledger(bus, [("msg-invalid-1", "schema-invalid")])
    _append(bus / "outbox" / "mainD.jsonl", [
        _row(id="msg-invalid-1", from_agent="mainD", kind="task-propose",
             payload={"task_text": "x"})])
    report = adj.adjudicate(bus)
    e = _class_of(report, "msg-invalid-1", "schema-invalid")
    assert e["class"] == "schema-invalid"


def test_unknown_stays_flagged(bus: Path) -> None:
    """Exists in the sender outbox only: flagged, never delivered -> unknown."""
    _write_ledger(bus, [("msg-outbox-only-1", "handler:intake_proposals")])
    _append(bus / "outbox" / "mainA.jsonl", [
        _row(id="msg-outbox-only-1", from_agent="mainA", kind="task-propose",
             payload={"task_text": "x"})])
    report = adj.adjudicate(bus)
    e = _class_of(report, "msg-outbox-only-1", "handler:intake_proposals")
    assert e["class"] == "unknown"
    assert e["clearable"] is False


def test_delivered_not_drained_stays(bus: Path) -> None:
    """Delivered to an inbox but no disposition -> stays flagged."""
    _write_ledger(bus, [("msg-delivered-1", "auditor")])
    _append(bus / "inbox" / "auditor.jsonl", [
        _row(id="msg-relay-1", from_agent="coordinator-daemon", to="auditor",
             relayed_src="msg-delivered-1")])
    report = adj.adjudicate(bus)
    e = _class_of(report, "msg-delivered-1", "auditor")
    assert e["class"] == "delivered-not-drained"
    assert e["clearable"] is False


# --------------------------------------------------------------- apply-clear


def test_apply_clear_keeps_only_must_stay(bus: Path, monkeypatch) -> None:
    """--apply-clear removes handled entries and preserves the delivered map."""
    _write_ledger(bus, [
        ("msg-handled-1", "auditor"),
        ("msg-unknown-1", "handler:intake_proposals"),
        ("msg-dropped-1", "inference"),
    ], delivered={"auditor": ["msg-handled-1"], "inference": ["msg-dropped-1"]})
    _append(bus / "inbox" / "auditor.jsonl", [
        _row(id="msg-relay-copy-1", from_agent="coordinator-daemon", to="auditor",
             relayed_src="msg-handled-1")])
    _append(bus / "outbox" / "auditor.jsonl", [
        _row(id="msg-verdict-1", from_agent="auditor", to="coordinator-agent",
             kind="finding", corr_id="msg-relay-copy-1")])
    _append(bus / "outbox" / "mainA.jsonl", [
        _row(id="msg-unknown-1", from_agent="mainA", kind="task-propose",
             payload={"task_text": "x"})])
    monkeypatch.setattr(adj, "_daemon_running", lambda: False)

    report = adj.adjudicate(bus)
    result = adj.apply_clear(bus, report, "relay_state.json.bak-test")
    assert result["before"] == 3
    assert result["cleared"] == 1  # only the handled entry leaves the ledger
    assert result["after"] == 2

    kept = json.loads((bus / "relay_state.json").read_text(encoding="utf-8"))
    assert [tuple(p) for p in kept["flagged"]] == [
        ("msg-dropped-1", "inference"), ("msg-unknown-1", "handler:intake_proposals")]
    # The delivered map is untouched — it is the daemon's delivery idempotency ledger.
    assert kept["delivered"] == {"auditor": ["msg-handled-1"],
                                 "inference": ["msg-dropped-1"]}
    assert (bus / "relay_state.json.bak-test").exists()


def test_apply_clear_refuses_while_daemon_alive(bus: Path, monkeypatch) -> None:
    """A running daemon rewrites the ledger every tick; the clear must refuse."""
    _write_ledger(bus, [("msg-handled-1", "auditor")])
    monkeypatch.setattr(adj, "_daemon_running", lambda: True)
    report = adj.adjudicate(bus)
    with pytest.raises(RuntimeError, match="RUNNING"):
        adj.apply_clear(bus, report, "relay_state.json.bak-test")


def test_apply_clear_refuses_on_ledger_drift(bus: Path, monkeypatch) -> None:
    """The ledger changed between report and apply -> refuse, never clobber."""
    _write_ledger(bus, [("msg-handled-1", "auditor")])
    monkeypatch.setattr(adj, "_daemon_running", lambda: False)
    report = adj.adjudicate(bus)
    # A concurrent writer rewrites the ledger (new ts).
    raw = json.loads((bus / "relay_state.json").read_text(encoding="utf-8"))
    raw["ts"] = "2026-08-16T13:00:00+00:00"
    (bus / "relay_state.json").write_text(json.dumps(raw))
    with pytest.raises(RuntimeError, match="differs from the adjudicated one"):
        adj.apply_clear(bus, report, "relay_state.json.bak-test")
