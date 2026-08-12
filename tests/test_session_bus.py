"""Protocol-anchored regression coverage for the session bus.

Every fixture uses an isolated ``tmp_path`` bus root.  These tests must never
point at the live coordination/session-bus directory: a coordinator daemon and
working agent sessions read that directory concurrently.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.coordination import session_bus as bus
from scripts.coordination import session_bus_coordinator as coordinator


REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_BUS_ROOT = REPO_ROOT / "coordination" / "session-bus"
AGENTS = ("alice", "bob", "coordinator-agent")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _heartbeat(root: Path, agent: str, state: str, *, task_id: str | None = None) -> None:
    """Write an isolated agent heartbeat for direct coordinator unit tests."""
    row: dict[str, str] = {
        "agent": agent,
        "state": state,
        "ts": "2026-07-28T00:00:00+00:00",
    }
    if task_id is not None:
        row["task_id"] = task_id
    path = root / "heartbeats" / f"{agent}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row), encoding="utf-8")


def _message(sender: str, recipient: str, kind: str = "finding", *, seq: int = 1,
             **extra: object) -> dict:
    """A schema-valid bus message unless a test deliberately mutates it."""
    row: dict[str, object] = {
        "schema_version": bus.MSG_SCHEMA_VERSION,
        "id": f"msg-20260728T000000Z-{seq}-{sender}",
        "ts": "2026-07-28T00:00:00+00:00",
        "from": sender,
        "to": recipient,
        "kind": kind,
    }
    row.update(extra)
    return row


def _queue(task_id: str = "task-1", *, status: str = "READY", lane: str = "none",
           gating: str = "none", epoch: int = 1, **extra: object) -> dict:
    row: dict[str, object] = {
        "schema_version": bus.QUEUE_SCHEMA_VERSION,
        "ts": "2026-07-28T00:00:00+00:00",
        "task_id": task_id,
        "status": status,
        "lane": lane,
        "gating": gating,
        "epoch": epoch,
    }
    row.update(extra)
    return row


@pytest.fixture
def bus_root(tmp_path: Path) -> Path:
    """A complete, deliberately small bus that is never the live bus root."""
    root = tmp_path / "session-bus"
    root.mkdir()
    assert root.resolve() != LIVE_BUS_ROOT.resolve()
    shutil.copy2(LIVE_BUS_ROOT / "session_bus.schema.json", root / "session_bus.schema.json")
    config = {
        "roster": [
            {"id": "alice", "role": "main", "lanes": ["none"]},
            {"id": "bob", "role": "main", "lanes": ["none"]},
            {"id": "coordinator-agent", "role": "coordinator-agent", "lanes": ["none"]},
        ],
        "authority": {"lease_grant": ["coordinator-agent"]},
        "coordinator_daemon": {"authority": "manual"},
        "leases": {"none_lane_grace_s": 900, "max_hold_s": 1800},
        "priority_classes": [],
    }
    # JSON is valid YAML and avoids a test dependency on PyYAML's emitter.
    (root / "config.yaml").write_text(json.dumps(config), encoding="utf-8")
    (root / "tokens").mkdir()
    (root / "tokens" / "token-queue.md").write_text("# operator tokens\n", encoding="utf-8")
    return root


def _provision(root: Path, *agents: str) -> None:
    for agent in agents:
        assert bus.main(["--bus-root", str(root), "provision", "--agent", agent]) == 0


def _quiet_tick_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep coordinator unit tests off host probes and all resource lanes."""
    monkeypatch.setattr(coordinator, "_lane_snapshot", lambda: {
        "ts": "2026-07-28T00:00:00+00:00", "cpu_busy": False,
        "gpu_busy": False, "none_busy": False, "load_class": "quiet",
    })
    monkeypatch.setattr(coordinator, "co_residency_context", lambda _cfg: {
        "available": False, "live_roles": [], "matrix_status": None,
    })


def test_c1_provision_creates_exactly_four_routes_idempotently_and_rejects_unknown(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """C1 / bootstrap: every roster member gets exactly inbox/outbox/hb/cursor."""
    expected = {
        "inbox/alice.jsonl", "outbox/alice.jsonl", "heartbeats/alice.json", "cursors/alice.json",
    }
    assert bus.main(["--bus-root", str(bus_root), "provision", "--agent", "alice"]) == 0
    actual = {str(path.relative_to(bus_root)) for path in bus_root.rglob("alice.*")}
    assert actual == expected
    first = {rel: (bus_root / rel).read_bytes() for rel in expected}
    assert bus.main(["--bus-root", str(bus_root), "provision", "--agent", "alice"]) == 0
    assert {rel: (bus_root / rel).read_bytes() for rel in expected} == first

    assert bus.main(["--bus-root", str(bus_root), "provision", "--agent", "not-rostered"]) == 2
    assert "not a roster id" in capsys.readouterr().err


def test_c2_relay_preserves_author_fans_out_and_is_idempotent(bus_root: Path) -> None:
    """C2: outbox transport retains ``from`` and dedupes by ``relayed_src``."""
    _provision(bus_root, *AGENTS)
    direct = _message("alice", "bob", seq=1, task_id="direct")
    wildcard = _message("alice", "*", seq=2, task_id="all")
    _append(bus_root / "outbox" / "alice.jsonl", direct)
    _append(bus_root / "outbox" / "alice.jsonl", wildcard)
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]

    first = coordinator.relay_outbox_messages(bus_root, roster, epoch=7)
    assert len([row for row in first if row["kind"] == "relayed"]) == 3
    bob_rows = _read_jsonl(bus_root / "inbox" / "bob.jsonl")
    assert {(row["relayed_src"], row["from"], row["to"]) for row in bob_rows} == {
        (direct["id"], "alice", "bob"), (wildcard["id"], "alice", "bob"),
    }
    coordinator_rows = _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
    assert [(row["relayed_src"], row["from"], row["to"]) for row in coordinator_rows] == [
        (wildcard["id"], "alice", "coordinator-agent")
    ]
    assert coordinator.relay_outbox_messages(bus_root, roster, epoch=7) == []
    assert len(_read_jsonl(bus_root / "inbox" / "bob.jsonl")) == 2


@pytest.mark.parametrize("kind", sorted(coordinator.no_relay_kinds("manual")))
def test_c2_kinds_with_a_reachable_handler_are_not_fanned_out(bus_root: Path, kind: str) -> None:
    """C2: messages consumed by a dedicated path cannot be duplicated by relay.

    C27 (2026-07-29) narrowed this. It used to parametrize over a CONSTANT set and so
    asserted the silent drop of `task-complete` and `task-propose` at manual
    authority as correct behaviour — the test encoded the defect. The skip set is now
    derived from the authority, and this covers only kinds whose handler really runs.
    """
    _provision(bus_root, *AGENTS)
    row = _message("alice", "bob", kind, seq=1, task_id="task-1")
    _append(bus_root / "outbox" / "alice.jsonl", row)
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]
    assert coordinator.relay_outbox_messages(bus_root, roster, epoch=1) == []
    assert _read_jsonl(bus_root / "inbox" / "bob.jsonl") == []


_PROPOSE_PAYLOAD = {"lane": "none", "gating": "none", "spec_ref": "handoffs/active/x.md",
                    "summary": "a proposed unit of work"}


@pytest.mark.parametrize("kind", ["task-complete", "task-propose"])
def test_c27_kind_whose_handler_cannot_run_here_is_relayed_and_flagged(
        bus_root: Path, kind: str) -> None:
    """C27: an unreachable handler must never produce a bare silent `continue`.

    `transcribe` runs only under `assign`; `intake_proposals` only from the manual
    `intake` CLI, never from `tick`. At the live `manual` authority neither consumes
    anything, so excluding these kinds dropped them outright. Duplicating a message
    into an inbox costs a read; dropping one costs a gate.
    """
    _provision(bus_root, *AGENTS)
    row = _message("alice", "bob", kind, seq=1, task_id="task-1",
                   **({"payload": _PROPOSE_PAYLOAD} if kind == "task-propose" else {}))
    _append(bus_root / "outbox" / "alice.jsonl", row)
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]

    advisory = coordinator.relay_outbox_messages(bus_root, roster, epoch=1)

    assert [r["relayed_src"] for r in _read_jsonl(bus_root / "inbox" / "bob.jsonl")] == [row["id"]]
    defects = [r for r in advisory if r.get("check") == "relay-handler-reachability"]
    assert len(defects) == 1
    assert defects[0]["relayed_src"] == row["id"]
    assert "manual" in defects[0]["detail"]


def test_c27_task_complete_is_skipped_again_once_its_handler_runs(bus_root: Path) -> None:
    """The map is authority-derived, not a second constant: at `assign`, transcribe
    consumes task-complete, so relaying it too WOULD double-count."""
    _provision(bus_root, *AGENTS)
    row = _message("alice", "bob", "task-complete", seq=1, task_id="task-1")
    _append(bus_root / "outbox" / "alice.jsonl", row)
    config = json.loads((bus_root / "config.yaml").read_text())
    config["coordinator_daemon"]["authority"] = "assign"

    advisory = coordinator.relay_outbox_messages(bus_root, config["roster"], epoch=1,
                                                 config=config)

    assert advisory == []
    assert _read_jsonl(bus_root / "inbox" / "bob.jsonl") == []
    assert coordinator.no_relay_kinds("assign") == {"token-request", "task-complete"}
    assert coordinator.no_relay_kinds("manual") == {"token-request"}


def test_c27_handler_defect_is_flagged_once_not_every_tick(bus_root: Path) -> None:
    """45s ticks must not flood advisory.jsonl with the same reachability defect."""
    _provision(bus_root, *AGENTS)
    row = _message("alice", "bob", "task-propose", seq=1, task_id="task-1",
                   payload=_PROPOSE_PAYLOAD)
    _append(bus_root / "outbox" / "alice.jsonl", row)
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]

    first = coordinator.relay_outbox_messages(bus_root, roster, epoch=1)
    for entry in first:
        _append(bus_root / "advisory.jsonl", entry)     # what the tick loop does
    second = coordinator.relay_outbox_messages(bus_root, roster, epoch=1)

    assert [r.get("check") for r in first].count("relay-handler-reachability") == 1
    assert [r.get("check") for r in second].count("relay-handler-reachability") == 0


def test_c27_needs_routing_to_now_delivers_for_a_stranded_kind(bus_root: Path) -> None:
    """The C18 fan-out sits AFTER the skip, so it was inert for exactly the three
    kinds that most needed it — including every `action_required` token-request."""
    _provision(bus_root, *AGENTS)
    row = _message("alice", "bob", "task-complete", seq=1, task_id="task-1",
                   needs_routing_to=["coordinator-agent"], action_required=True)
    _append(bus_root / "outbox" / "alice.jsonl", row)
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]

    coordinator.relay_outbox_messages(bus_root, roster, epoch=1)

    routed = _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
    assert [r["relayed_src"] for r in routed if r.get("relayed_src")] == [row["id"]]


def test_c2_invalid_outbox_row_is_defect_not_delivery(bus_root: Path) -> None:
    """C2: malformed source data is isolated instead of being propagated."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl", {
        "id": "malformed-source", "to": "bob", "kind": "finding",
    })
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]
    advisory = coordinator.relay_outbox_messages(bus_root, roster, epoch=3)
    assert len(advisory) == 1
    assert advisory[0]["kind"] == "defect"
    assert "schema-invalid" in advisory[0]["detail"]
    assert _read_jsonl(bus_root / "inbox" / "bob.jsonl") == []


def test_c3_drain_missing_inbox_fails_closed_but_empty_inbox_succeeds(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """C3: an unprovisioned route must not look like an empty route."""
    assert bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"]) == 2
    assert "no inbox" in capsys.readouterr().err
    _provision(bus_root, "alice")
    assert bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"]) == 0
    assert "no new messages" in capsys.readouterr().out


def test_rule_1_single_writer_refuses_cross_queue_and_inbox_and_lints_forgery(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Rule 1: target ownership is structural; content ownership is linted."""
    _provision(bus_root, *AGENTS)
    queue_row = json.dumps(_queue())
    assert bus.main(["--bus-root", str(bus_root), "append", "--agent", "alice",
                     "--target", "queue", "--json", queue_row]) == 1
    assert bus.main(["--bus-root", str(bus_root), "append", "--agent", "alice",
                     "--target", "inbox", "--to", "bob", "--json",
                     json.dumps(_message("alice", "bob"))]) == 1
    assert "single-writer violation" in capsys.readouterr().err

    # Outbox and heartbeat routes derive their filename from --agent, making a
    # cross-target append syntactically inexpressible; assert that mapping too.
    assert bus.required_writer(bus_root, bus_root / "outbox" / "bob.jsonl") == "bob"
    assert bus.required_writer(bus_root, bus_root / "heartbeats" / "bob.json") == "bob"
    forged = _message("bob", "coordinator-agent", seq=9)
    _append(bus_root / "outbox" / "alice.jsonl", forged)
    assert bus.main(["--bus-root", str(bus_root), "validate"]) == 1
    assert "from='bob'" in capsys.readouterr().out


def test_rule_4_drain_peek_does_not_advance_but_drain_does(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Rule 4: consumers own monotonically advancing inbox cursors."""
    _provision(bus_root, "alice")
    _append(bus_root / "inbox" / "alice.jsonl", _message("bob", "alice"))
    cursor = bus_root / "cursors" / "alice.json"
    assert bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice", "--peek"]) == 0
    assert json.loads(cursor.read_text())["offset"] == 0
    capsys.readouterr()
    assert bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"]) == 0
    assert json.loads(cursor.read_text())["offset"] == (bus_root / "inbox" / "alice.jsonl").stat().st_size


def test_rule_4_cursor_only_advances(bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Rule 4 regression: a consumer cannot move its cursor backwards."""
    _provision(bus_root, "alice")
    assert bus.main(["--bus-root", str(bus_root), "cursor", "--agent", "alice", "--set", "20"]) == 0
    assert bus.main(["--bus-root", str(bus_root), "cursor", "--agent", "alice", "--set", "20"]) == 0
    assert bus.main(["--bus-root", str(bus_root), "cursor", "--agent", "alice", "--set", "21"]) == 0
    assert bus.main(["--bus-root", str(bus_root), "cursor", "--agent", "alice", "--set", "10"]) != 0
    assert "cannot rewind" in capsys.readouterr().err
    assert json.loads((bus_root / "cursors" / "alice.json").read_text())["offset"] == 21


def test_rule_8_authorized_revoke_drains_releases_and_skips_same_tick_assignment(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Rule 8: revocation is cooperative, preserves status, then excludes regrant."""
    _provision(bus_root, *AGENTS)
    _quiet_tick_seams(monkeypatch)
    config = json.loads((bus_root / "config.yaml").read_text())
    config["coordinator_daemon"]["authority"] = "assign"
    (bus_root / "config.yaml").write_text(json.dumps(config), encoding="utf-8")
    _append(bus_root / "queue.jsonl", _queue("revoked", status="RUNNING", owner="bob",
                                              priority="P1", lease_expires_ts="2999-01-01T00:00:00+00:00"))
    _append(bus_root / "outbox" / "coordinator-agent.jsonl", _message(
        "coordinator-agent", "bob", "lease-revoke", task_id="revoked",
        payload={"reason": "higher priority work"},
    ))
    (bus_root / "heartbeats" / "bob.json").write_text(json.dumps({
        "agent": "bob", "state": "working", "ts": "2026-07-28T00:00:00+00:00",
    }), encoding="utf-8")

    coordinator.apply_assignment(bus_root, config, epoch=11)
    marked = bus.fold_queue(bus_root)["revoked"]
    assert marked["status"] == "RUNNING"
    assert marked["revoking"] is True

    (bus_root / "heartbeats" / "bob.json").write_text(json.dumps({
        "agent": "bob", "state": "draining", "ts": "2026-07-28T00:00:01+00:00",
    }), encoding="utf-8")
    emitted = coordinator.apply_assignment(bus_root, config, epoch=11)
    released = bus.fold_queue(bus_root)["revoked"]
    assert released["status"] == "READY"
    assert released["owner"] is None
    assert released["revoking"] is False
    assert any(row["kind"] == "lease-released" for row in emitted)
    assert not any(row["kind"] == "assigned" and row["task_id"] == "revoked" for row in emitted)


def test_rule_8_unauthorized_revoke_is_defect_and_leaves_lease_untouched(bus_root: Path) -> None:
    """Rule 8: only lease-grant authority can begin quiesce-and-drain."""
    _provision(bus_root, *AGENTS)
    config = json.loads((bus_root / "config.yaml").read_text())
    initial = _queue("protected", status="ASSIGNED", owner="bob", priority="P1")
    outcome = coordinator.process_revocations(config, {"protected": initial}, {
        "protected": [_message("alice", "bob", "lease-revoke", task_id="protected",
                                payload={"reason": "not authorised"})]
    }, epoch=5)
    assert outcome["queue_rows"] == []
    assert outcome["advisory"][0]["kind"] == "defect"
    assert outcome["advisory"][0]["check"] == "lease-authority"


def test_rule_9_rebuild_is_identical_from_bus_files_after_restart(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Rule 9: no coordinator-agent authority is supplied from process memory."""
    _provision(bus_root, "alice")
    _append(bus_root / "queue.jsonl", _queue("live", status="RUNNING", owner="alice"))
    (bus_root / "tokens" / "token-queue.md").write_text("- [ ] OP-ONE\n- [x] OP-TWO\n")
    _append(bus_root / "inbox" / "alice.jsonl", _message("bob", "alice"))
    assert bus.main(["--bus-root", str(bus_root), "cursor", "--agent", "alice", "--set", "0"]) == 0
    capsys.readouterr()  # Provision/cursor progress is not part of rebuild's JSON result.

    assert bus.main(["--bus-root", str(bus_root), "rebuild", "--json"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert bus.main(["--bus-root", str(bus_root), "rebuild", "--json"]) == 0
    second = json.loads(capsys.readouterr().out)
    first.pop("rebuilt_at")
    second.pop("rebuilt_at")
    assert second == first
    assert first["queue"]["live"]["live"]["owner"] == "alice"
    assert first["agents"]["alice"]["inbox_unread"] == 1


def test_rule_10_queue_row_without_gating_is_hard_validation_failure(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Rule 10: gating classification is mandatory, never a soft warning."""
    ungated = _queue()
    ungated.pop("gating")
    _append(bus_root / "queue.jsonl", ungated)
    assert bus.main(["--bus-root", str(bus_root), "validate"]) == 1
    assert "gating" in capsys.readouterr().out


def test_epoch_fencing_stamps_new_advisory_rows_and_exposes_stale_epoch(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Epoch fencing: current advice is labelled and old-generation rows differ."""
    _provision(bus_root, *AGENTS)
    _quiet_tick_seams(monkeypatch)
    _append(bus_root / "advisory.jsonl", {
        "schema_version": coordinator.ADVISORY_SCHEMA, "ts": "2026-07-27T00:00:00+00:00",
        "epoch": 6, "kind": "saturation",
    })
    coordinator.tick(bus_root, epoch=7)
    rows = _read_jsonl(bus_root / "advisory.jsonl")
    current = [row for row in rows if row["epoch"] == 7]
    stale = [row for row in rows if row["epoch"] != 7]
    assert current and all(row["epoch"] == 7 for row in current)
    assert [row["epoch"] for row in stale] == [6]


def test_c7_nonroster_writer_files_are_refused_ignored_and_preserved(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """C7: task-shaped writer ids neither create routes nor become agents."""
    _provision(bus_root, *AGENTS)
    ghost = "task-shaped-writer"
    assert bus.main(["--bus-root", str(bus_root), "append", "--agent", ghost,
                     "--target", "heartbeat", "--json", '{"state":"working"}']) == 1
    assert bus.main(["--bus-root", str(bus_root), "append", "--agent", ghost,
                     "--target", "outbox", "--json", json.dumps(_message(ghost, "alice"))]) == 1
    assert "not a roster id" in capsys.readouterr().err
    assert not (bus_root / "heartbeats" / f"{ghost}.json").exists()
    assert not (bus_root / "outbox" / f"{ghost}.jsonl").exists()

    # Existing evidence is surfaced but never deleted or adopted as an agent.
    ghost_hb = bus_root / "heartbeats" / f"{ghost}.json"
    ghost_outbox = bus_root / "outbox" / f"{ghost}.jsonl"
    ghost_hb.write_text(json.dumps({"agent": ghost, "state": "working", "task_id": ghost}),
                        encoding="utf-8")
    _append(ghost_outbox, _message(ghost, "alice"))
    before = {path: path.read_bytes() for path in (ghost_hb, ghost_outbox)}
    for name in ("human_only_paths.yaml", "human_only_paths.sha256"):
        shutil.copy2(LIVE_BUS_ROOT / name, bus_root / name)

    assert bus.main(["--bus-root", str(bus_root), "validate"]) == 0
    validation = capsys.readouterr().out
    assert f"WARN heartbeats/{ghost}.json" in validation
    assert f"WARN outbox/{ghost}.jsonl" in validation
    assert {path: path.read_bytes() for path in (ghost_hb, ghost_outbox)} == before

    assert bus.main(["--bus-root", str(bus_root), "rebuild", "--json"]) == 0
    rebuilt = json.loads(capsys.readouterr().out)
    assert set(rebuilt["agents"]) == set(AGENTS)
    assert ghost not in rebuilt["agents"]
    _quiet_tick_seams(monkeypatch)
    config = json.loads((bus_root / "config.yaml").read_text())
    assert ghost not in coordinator._agent_states(bus_root, config["roster"])
    assert not [row for row in coordinator.audit(bus_root, epoch=1)
                if row.get("subject") == ghost]
    advice = coordinator.tick(bus_root, epoch=1, dry_run=True)
    assert not [row for row in advice if row.get("agent") == ghost or row.get("subject") == ghost]
    assert {path: path.read_bytes() for path in (ghost_hb, ghost_outbox)} == before


def test_c4_unacked_message_redelivers_one_same_corr_id_nudge(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """C4 / Rule 3: one overdue ACK produces one dedupeable nudge on later ticks.

    The explicit bound is one durable nudge per unacknowledged correlation id.
    """
    _provision(bus_root, *AGENTS)
    _quiet_tick_seams(monkeypatch)
    assignment = _message(
        "coordinator-daemon", "bob", "task-assign", task_id="needs-ack", corr_id="corr-ack",
        requires_ack=True, ack_deadline_s=1,
        payload={"lane": "none", "epoch": 1, "lease_expires_ts": "2000-01-01T00:00:00+00:00"},
    )
    _append(bus_root / "inbox" / "bob.jsonl", assignment)
    # A normal nudge is not an ACK-deadline redelivery and must not suppress one.
    _append(bus_root / "inbox" / "bob.jsonl", _message(
        "alice", "bob", "nudge", seq=4, corr_id="corr-ack", payload={"reason": "other event"},
    ))
    acknowledged = _message(
        "coordinator-daemon", "bob", "task-assign", task_id="already-acked", corr_id="corr-acked",
        seq=2, requires_ack=True, ack_deadline_s=1,
        payload={"lane": "none", "epoch": 1, "lease_expires_ts": "2000-01-01T00:00:00+00:00"},
    )
    _append(bus_root / "inbox" / "bob.jsonl", acknowledged)
    _append(bus_root / "outbox" / "bob.jsonl", _message(
        "bob", "coordinator-agent", "ack", seq=3, corr_id="corr-acked",
    ))
    foreign_ack = _message(
        "coordinator-daemon", "bob", "task-assign", task_id="foreign-ack", corr_id="corr-foreign",
        seq=5, requires_ack=True, ack_deadline_s=1,
        payload={"lane": "none", "epoch": 1, "lease_expires_ts": "2000-01-01T00:00:00+00:00"},
    )
    _append(bus_root / "inbox" / "bob.jsonl", foreign_ack)
    _append(bus_root / "outbox" / "alice.jsonl", _message(
        "alice", "coordinator-agent", "ack", seq=6, corr_id="corr-foreign",
    ))
    coordinator.tick(bus_root, epoch=1)
    coordinator.tick(bus_root, epoch=1)
    inbox = _read_jsonl(bus_root / "inbox" / "bob.jsonl")
    nudges = [row for row in inbox if row["kind"] == "nudge" and row.get("corr_id") == "corr-ack"
              and (row.get("payload") or {}).get("reason") == coordinator._ACK_REDELIVERY_REASON]
    assert len(nudges) == 1
    assert len({row["id"] for row in nudges}) == 1
    assert nudges[0]["id"] != assignment["id"]
    assert not [row for row in inbox if row["kind"] == "nudge" and row.get("corr_id") == "corr-acked"]
    assert [row for row in inbox if row["kind"] == "nudge" and row.get("corr_id") == "corr-foreign"
            and (row.get("payload") or {}).get("reason") == coordinator._ACK_REDELIVERY_REASON]
    assert bus.main(["--bus-root", str(bus_root), "drain", "--agent", "bob", "--peek"]) == 0
    assert capsys.readouterr().out.count(nudges[0]["id"]) == 1


@pytest.mark.parametrize("state", ("idle", "working", "draining"))
def test_c8_first_seen_heartbeat_never_replays_a_task_boundary(
        bus_root: Path, state: str) -> None:
    """C8: daemon startup snapshots agents rather than flooding the coordinator."""
    roster = json.loads((bus_root / "config.yaml").read_text(encoding="utf-8"))["roster"]
    _heartbeat(bus_root, "alice", state, task_id="t1")

    assert coordinator.detect_task_boundaries(bus_root, roster, epoch=7) == []
    assert _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl") == []
    assert json.loads((bus_root / "boundary_state.json").read_text(encoding="utf-8")) == {
        "alice": f"{state}|t1", "bob": "None|None",
    }


def test_c8_working_churn_is_not_a_task_boundary(bus_root: Path) -> None:
    """C8: only a transition into idle is useful coordinator work."""
    roster = json.loads((bus_root / "config.yaml").read_text(encoding="utf-8"))["roster"]
    _heartbeat(bus_root, "alice", "working", task_id="t1")
    assert coordinator.detect_task_boundaries(bus_root, roster, epoch=7) == []

    # Neither a redundant heartbeat nor replacing one active task with another
    # should look like an available-worker boundary.
    _heartbeat(bus_root, "alice", "working", task_id="t1")
    assert coordinator.detect_task_boundaries(bus_root, roster, epoch=7) == []
    _heartbeat(bus_root, "alice", "working", task_id="t2")
    assert coordinator.detect_task_boundaries(bus_root, roster, epoch=7) == []
    assert _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl") == []


def test_c8_idle_boundary_is_durable_idempotent_and_schema_valid(bus_root: Path) -> None:
    """C8: a retired task produces one valid, restart-safe coordinator notice."""
    roster = json.loads((bus_root / "config.yaml").read_text(encoding="utf-8"))["roster"]
    _heartbeat(bus_root, "alice", "working", task_id="t1")
    assert coordinator.detect_task_boundaries(bus_root, roster, epoch=7) == []

    # Retiring task_id is the escaped live bug: schema requires strings, so the
    # delivered message must omit it instead of serializing task_id: null.
    _heartbeat(bus_root, "alice", "idle")
    advisory = coordinator.detect_task_boundaries(bus_root, roster, epoch=7)
    assert len(advisory) == 1
    assert advisory[0]["kind"] == "task-boundary"
    assert advisory[0]["transition"] == "working|t1 -> idle|None"
    delivered = _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
    assert len(delivered) == 1
    notice = delivered[0]
    bus.validate_row(bus_root, notice, "msg")
    assert notice["kind"] == "status"
    assert notice["payload"]["event"] == "task-boundary"
    assert notice["payload"]["transition"] == "working|t1 -> idle|None"
    assert "task_id" not in notice

    # An unchanged tick is idempotent, including after a daemon process restart:
    # the persisted snapshot alone supplies all history the fresh call needs.
    persisted = json.loads((bus_root / "boundary_state.json").read_text(encoding="utf-8"))
    assert persisted["alice"] == "idle|None"
    assert coordinator.detect_task_boundaries(bus_root, roster, epoch=8) == []
    assert _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl") == delivered


def test_c8_coordinator_agent_idle_is_excluded_from_boundary_notices(bus_root: Path) -> None:
    """C8: the coordinator must not enqueue a notice to itself."""
    roster = [{"id": "coordinator-agent", "role": "coordinator-agent", "lanes": ["none"]}]
    _heartbeat(bus_root, "coordinator-agent", "idle")

    assert coordinator.detect_task_boundaries(bus_root, roster, epoch=7) == []
    assert not (bus_root / "inbox" / "coordinator-agent.jsonl").exists()
    assert not (bus_root / "boundary_state.json").exists()


def test_c8_endpoint_lint_warns_for_unreachable_roster_rows_only(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """C8: non-tmux endpoints surface their unread work without failing validation."""
    config = json.loads((bus_root / "config.yaml").read_text(encoding="utf-8"))
    for entry in config["roster"]:
        entry["endpoint"] = "tmux:bus-tests"
    next(entry for entry in config["roster"] if entry["id"] == "alice")["endpoint"] = "monitor:file"
    (bus_root / "config.yaml").write_text(json.dumps(config), encoding="utf-8")
    _provision(bus_root, "alice")
    _append(bus_root / "inbox" / "alice.jsonl", _message("bob", "alice"))
    for name in ("human_only_paths.yaml", "human_only_paths.sha256"):
        shutil.copy2(LIVE_BUS_ROOT / name, bus_root / name)

    assert bus.main(["--bus-root", str(bus_root), "validate"]) == 0
    output = capsys.readouterr().out
    assert "WARN roster/alice" in output
    assert "currently 1" in output

    next(entry for entry in config["roster"] if entry["id"] == "alice")["endpoint"] = "tmux:bus-tests"
    (bus_root / "config.yaml").write_text(json.dumps(config), encoding="utf-8")
    assert bus.main(["--bus-root", str(bus_root), "validate"]) == 0
    assert "WARN roster/alice" not in capsys.readouterr().out


def test_c8_endpoint_lint_malformed_config_warns_without_raising(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """C8: endpoint lint is advisory even when the roster cannot be parsed."""
    (bus_root / "config.yaml").write_text("roster: [unterminated", encoding="utf-8")

    assert bus.main(["--bus-root", str(bus_root), "validate"]) == 1
    output = capsys.readouterr().out
    assert "WARN roster endpoint check skipped:" in output
    assert "FAIL could not read config.yaml roster:" in output


def test_c8_endpoint_lint_absent_config_warns_without_raising(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """C8: a missing config degrades the endpoint lint to a warning."""
    (bus_root / "config.yaml").unlink()

    assert bus.main(["--bus-root", str(bus_root), "validate"]) == 1
    assert "WARN roster endpoint check skipped:" in capsys.readouterr().out


def test_c8_boundary_state_is_daemon_owned(bus_root: Path) -> None:
    """C8: persisted boundary history has the same single writer as inboxes."""
    assert bus.required_writer(bus_root, bus_root / "boundary_state.json") == bus.COORDINATOR_DAEMON


# --------------------------------------------------------------------------
# C18 code half — reachability is OBSERVED, not declared.
# --------------------------------------------------------------------------

def test_c18_routed_to_a_dead_but_rostered_agent_warns_and_still_delivers(
        bus_root: Path) -> None:
    """The exact 2026-07-29 miss: a roster row outlives its session.

    `codex-bus-tests` was still `role: main` with no window and a 16.7 h stale
    heartbeat, so the roster-metadata test called it reachable and the routed
    message went to an inbox nobody drains, in silence. Reachability now comes
    from what is observable.

    Delivery still happens: an inbox row is durable and a merely-offline agent
    drains it on return, so refusing would turn transient offline into message
    loss — the opposite-polarity error. The sender is WARNED instead.
    """
    _provision(bus_root, *AGENTS)
    row = _message("alice", "coordinator-agent", seq=1, task_id="t",
                   needs_routing_to=["bob"], action_required=True)
    _append(bus_root / "outbox" / "alice.jsonl", row)
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]
    # bob is rostered and NOT retired — the case the roster-metadata test missed.
    assert {r["id"]: r.get("role") for r in roster}.get("bob") != "retired"
    hb = bus_root / "heartbeats" / "bob.json"
    old = time.time() - 17 * 3600
    os.utime(hb, (old, old))

    advisory = coordinator.relay_outbox_messages(bus_root, roster, epoch=1)

    dead = [a for a in advisory if a.get("unreachable") == "bob"]
    assert len(dead) == 1, "a dead-but-rostered recipient must be flagged exactly once"
    assert "LOOKS DEAD" in dead[0]["detail"] and "stale" in dead[0]["detail"]
    # ...and the message is still on bob's inbox, recoverable if bob returns.
    assert [r["relayed_src"] for r in _read_jsonl(bus_root / "inbox" / "bob.jsonl")] == [row["id"]]

    # Deduped per (msg, recipient) against the DURABLE ledger, which the tick loop
    # writes — so persist it as the daemon would before asserting no re-flood.
    # (Without this the second pass legitimately re-flags: the dedupe key lives on
    # disk precisely so a daemon restart cannot re-flood either.)
    with (bus_root / "advisory.jsonl").open("a", encoding="utf-8") as fh:
        for entry in advisory:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    assert coordinator.relay_outbox_messages(bus_root, roster, epoch=1) == []


def test_c18_a_fresh_heartbeat_is_not_flagged(bus_root: Path) -> None:
    """The warning must not fire on a live agent — that would train people to ignore it."""
    _provision(bus_root, *AGENTS)
    row = _message("alice", "coordinator-agent", seq=2, task_id="t",
                   needs_routing_to=["bob"])
    _append(bus_root / "outbox" / "alice.jsonl", row)
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]
    advisory = coordinator.relay_outbox_messages(bus_root, roster, epoch=1)
    assert [a for a in advisory if a.get("unreachable")] == []
    assert len(_read_jsonl(bus_root / "inbox" / "bob.jsonl")) == 1


def test_c18_a_live_window_suppresses_a_stale_heartbeat_warning() -> None:
    """Window presence beats heartbeat age: a healthy session goes quiet mid-generation.

    Observed 2026-07-27 — a live main's heartbeat was 2 h stale while it was
    working. If staleness alone could flag, the warning would fire on healthy
    agents and stop being read.
    """
    entry = {"id": "codex", "endpoint": "tmux:agent:codex-inference"}
    states = {"codex": {"age_s": 99 * 3600}}
    assert coordinator._looks_dead("codex", entry, states, {"codex-inference"}, "agent") is None
    # Same agent, same staleness, no window -> flagged.
    why = coordinator._looks_dead("codex", entry, states, {"htop"}, "agent")
    assert why and "stale" in why and "no live window" in why


def test_c18_unknown_window_state_still_warns_rather_than_going_quiet() -> None:
    """If tmux cannot be read the window signal is unavailable — warn anyway.

    The advisory is deduped per (msg, recipient), so a false warning costs one
    visible line while false silence costs the defect this exists to close.
    """
    why = coordinator._looks_dead("gone", {"id": "gone"}, {"gone": {"age_s": 99 * 3600}},
                                  None, "tmux unreadable: boom")
    assert why and "window state unknown" in why


def test_c18_no_tmux_config_never_probes_the_real_session() -> None:
    """A caller without config must not read whichever windows happen to be up."""
    windows, why = coordinator._live_window_names({})
    assert windows is None and "no tmux.live_session declared" in why


def test_c18_the_warning_itself_reaches_a_drained_channel(bus_root: Path) -> None:
    """C18 second half: a warning nobody reads is another silent sink.

    The advisory row lands in advisory.jsonl, which is delivered to no one and
    printed only by `status` on demand. So the original defect had two layers: a
    message in an inbox nobody drains, and a notice about it in a ledger nobody
    reads. coordinator-agent is the party that can retire the roster row or
    re-route, and it drains its inbox at every boundary — so the notice goes there.

    Delivery to the dead recipient is UNCHANGED. This adds a reader; it does not
    refuse, bounce, or withhold anything (fable-auditor's polarity note).
    """
    _provision(bus_root, *AGENTS)
    row = _message("alice", "coordinator-agent", seq=9, task_id="t",
                   needs_routing_to=["bob"], action_required=True)
    _append(bus_root / "outbox" / "alice.jsonl", row)
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]
    hb = bus_root / "heartbeats" / "bob.json"
    old = time.time() - 17 * 3600
    os.utime(hb, (old, old))

    coordinator.relay_outbox_messages(bus_root, roster, epoch=1)

    notices = [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
               if r.get("kind") == "defect" and (r.get("payload") or {}).get("unreachable")]
    assert len(notices) == 1, "coordinator-agent must be told, in a channel it drains"
    assert notices[0]["payload"]["unreachable"] == "bob"
    assert notices[0]["payload"]["from_agent"] == "alice"
    assert "retire" in notices[0]["payload"]["action"]
    # The mail still went to bob: warn, never withhold.
    assert [r["relayed_src"] for r in _read_jsonl(bus_root / "inbox" / "bob.jsonl")] == [row["id"]]


def test_c18_the_notice_is_not_re_sent_on_every_tick(bus_root: Path) -> None:
    """Idempotent against its OWN evidence, not against a ledger someone else writes.

    Keying this on advisory.jsonl would re-notify on every pass for any caller that
    does not persist advisories — which is every direct caller, including the tests.
    """
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl",
            _message("alice", "coordinator-agent", seq=10, task_id="t",
                     needs_routing_to=["bob"]))
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]
    old = time.time() - 17 * 3600
    os.utime(bus_root / "heartbeats" / "bob.json", (old, old))

    for _ in range(3):
        coordinator.relay_outbox_messages(bus_root, roster, epoch=1)

    notices = [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
               if r.get("kind") == "defect" and (r.get("payload") or {}).get("unreachable")]
    assert len(notices) == 1, f"one notice per (msg, recipient), got {len(notices)}"


# --------------------------------------------------------- C19 stuck-agent rescue


def _stuck_roster(*, endpoint: str = "tmux:agent:alice") -> list[dict]:
    return [
        {"id": "alice", "role": "main", "lanes": ["none"], "endpoint": endpoint},
        {"id": "coordinator-agent", "role": "coordinator-agent", "lanes": ["none"],
         "endpoint": "monitor:file"},
    ]


class _RecordingNudge:
    """Stand-in for tmux_adapter.py. NO test may reach a real tmux window."""

    def __init__(self, rc: int = 0, out: str = "nudged") -> None:
        self.rc, self.out, self.calls = rc, out, []

    def __call__(self, agent: str, message: str, min_interval_s: float) -> tuple[int, str]:
        self.calls.append((agent, message, min_interval_s))
        return self.rc, self.out


@pytest.fixture(autouse=True)
def _never_touch_real_tmux(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may run `tmux capture-pane`. Default stub: pane idle (not generating)."""
    monkeypatch.setattr(coordinator, "_pane_generating",
                        lambda agent, roster: (False, "stubbed idle pane"))


class _RecordingPane:
    """Stand-in for the C21 pane cross-check. ``active`` may be True/False/None."""

    def __init__(self, active: bool | None) -> None:
        self.active, self.calls = active, []

    def __call__(self, agent: str, roster: list[dict]) -> tuple[bool | None, str]:
        self.calls.append(agent)
        return self.active, f"stubbed pane for {agent}"


def _unread(root: Path, agent: str, n: int) -> None:
    for i in range(n):
        _append(root / "inbox" / f"{agent}.jsonl",
                _message("coordinator-daemon", agent, seq=100 + i))


def _kinds(rows: list[dict], agent: str = "alice") -> list[str]:
    return [r["kind"] for r in rows if r.get("agent") == agent]


def test_c19_idle_agent_with_unread_is_detected_and_nudged(bus_root: Path) -> None:
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "alice", 3)
    _heartbeat(bus_root, "alice", "idle")
    nudge = _RecordingNudge()

    rows = coordinator.resolve_stuck_agents(bus_root, _stuck_roster(), epoch=1,
                                            nudge_fn=nudge, now=1000.0)

    assert [c[0] for c in nudge.calls] == ["alice"]
    assert "drain --agent alice" in nudge.calls[0][1]
    assert nudge.calls[0][2] == coordinator._STUCK_MIN_NUDGE_INTERVAL_S
    assert _kinds(rows) == ["stuck-detected", "stuck-nudged"]
    assert (bus_root / "stuck_state.json").exists()


def test_c21_active_pane_suppresses_the_nudge(bus_root: Path) -> None:
    """The live false positive: heartbeat says idle, the pane is generating."""
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "alice", 1)
    _heartbeat(bus_root, "alice", "idle")
    nudge, pane = _RecordingNudge(), _RecordingPane(True)

    rows = coordinator.resolve_stuck_agents(bus_root, _stuck_roster(), epoch=1,
                                            nudge_fn=nudge, pane_fn=pane, now=1000.0)

    assert nudge.calls == []
    assert pane.calls == ["alice"]
    assert _kinds(rows) == ["stuck-suppressed-pane-active"]
    assert rows[0]["pane_active"] is True
    # Deduped: the same (unread, cursor) does not write a row every 45s tick.
    again = coordinator.resolve_stuck_agents(bus_root, _stuck_roster(), epoch=1,
                                             nudge_fn=nudge, pane_fn=pane, now=1045.0)
    assert _kinds(again) == []


def test_c21_idle_pane_still_nudges(bus_root: Path) -> None:
    """The genuine path must not be weakened."""
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "alice", 2)
    _heartbeat(bus_root, "alice", "idle")
    nudge, pane = _RecordingNudge(), _RecordingPane(False)

    rows = coordinator.resolve_stuck_agents(bus_root, _stuck_roster(), epoch=1,
                                            nudge_fn=nudge, pane_fn=pane, now=1000.0)

    assert [c[0] for c in nudge.calls] == ["alice"]
    assert _kinds(rows) == ["stuck-detected", "stuck-nudged"]


def test_c21_unreadable_pane_fails_closed_to_suppression(bus_root: Path) -> None:
    """Unreadable pane => suppress, visibly, and re-check on the next tick."""
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "alice", 1)
    _heartbeat(bus_root, "alice", "idle")
    nudge, pane = _RecordingNudge(), _RecordingPane(None)

    rows = coordinator.resolve_stuck_agents(bus_root, _stuck_roster(), epoch=1,
                                            nudge_fn=nudge, pane_fn=pane, now=1000.0)

    assert nudge.calls == []
    assert _kinds(rows) == ["stuck-suppressed-pane-active"]
    assert rows[0]["pane_active"] is None

    # Not permanent: once the pane is readable and idle, the nudge happens.
    rows = coordinator.resolve_stuck_agents(bus_root, _stuck_roster(), epoch=1,
                                            nudge_fn=nudge, pane_fn=_RecordingPane(False),
                                            now=1045.0)
    assert [c[0] for c in nudge.calls] == ["alice"]
    assert _kinds(rows) == ["stuck-detected", "stuck-nudged"]


def test_c19_working_agent_is_not_stuck(bus_root: Path) -> None:
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "alice", 5)
    _heartbeat(bus_root, "alice", "working", task_id="t-1")
    nudge = _RecordingNudge()

    rows = coordinator.resolve_stuck_agents(bus_root, _stuck_roster(), epoch=1,
                                            nudge_fn=nudge, now=1000.0)

    assert nudge.calls == []
    assert _kinds(rows) == []


def test_c19_idle_agent_with_no_unread_is_not_stuck(bus_root: Path) -> None:
    _provision(bus_root, "alice", "coordinator-agent")
    _heartbeat(bus_root, "alice", "idle")
    nudge = _RecordingNudge()

    rows = coordinator.resolve_stuck_agents(bus_root, _stuck_roster(), epoch=1,
                                            nudge_fn=nudge, now=1000.0)

    assert nudge.calls == []
    assert _kinds(rows) == []


def test_c19_stale_heartbeat_with_unread_counts_as_stuck(bus_root: Path) -> None:
    """Silence is not proof of health when mail is sitting unread."""
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "alice", 1)
    _heartbeat(bus_root, "alice", "working", task_id="t-1")
    old = time.time() - (coordinator._STUCK_HEARTBEAT_STALE_S + 600)
    os.utime(bus_root / "heartbeats" / "alice.json", (old, old))
    nudge = _RecordingNudge()

    rows = coordinator.resolve_stuck_agents(bus_root, _stuck_roster(), epoch=1,
                                            nudge_fn=nudge, now=1000.0)

    assert [c[0] for c in nudge.calls] == ["alice"]
    assert "stuck-nudged" in _kinds(rows)


def test_c19_rate_limit_suppresses_a_second_nudge(bus_root: Path) -> None:
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "alice", 2)
    _heartbeat(bus_root, "alice", "idle")
    nudge = _RecordingNudge()
    roster = _stuck_roster()

    coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=nudge, now=1000.0)
    # New mail arrives (so this is not the refusing-to-drain path), immediately.
    _unread(bus_root, "alice", 1)
    rows = coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=nudge, now=1100.0)

    assert len(nudge.calls) == 1, "rate limit must hold within min-interval"
    assert "stuck-nudged" not in _kinds(rows)

    # Past the interval, with the state still divergent, it nudges again.
    rows = coordinator.resolve_stuck_agents(
        bus_root, roster, epoch=1, nudge_fn=nudge,
        now=1000.0 + coordinator._STUCK_MIN_NUDGE_INTERVAL_S + 1)
    assert len(nudge.calls) == 2
    assert "stuck-nudged" in _kinds(rows)


def test_c19_agent_that_will_not_drain_escalates_instead_of_nudging_forever(
        bus_root: Path) -> None:
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "alice", 2)
    _heartbeat(bus_root, "alice", "idle")
    nudge = _RecordingNudge()
    roster = _stuck_roster()

    coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=nudge, now=1000.0)
    # Nothing changed: unread identical, cursor unmoved.
    later = 1000.0 + coordinator._STUCK_ESCALATION_INTERVAL_S + 1
    rows = coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=nudge, now=later)

    assert len(nudge.calls) == 1, "a refusing agent is escalated, not re-nudged"
    esc = [r for r in rows if r["kind"] == "stuck-refusing-drain"]
    assert len(esc) == 1 and esc[0]["escalation"] == 1

    # And the escalation itself is rate-limited, not emitted every 45s tick.
    rows = coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=nudge,
                                            now=later + 60)
    assert [r for r in rows if r["kind"] == "stuck-refusing-drain"] == []


def test_c19_unreadable_state_is_skipped_never_read_as_zero_unread(bus_root: Path) -> None:
    """Fail closed: the whole defect class here is 'no unread' hiding a stuck agent."""
    _provision(bus_root, "alice", "coordinator-agent")
    _heartbeat(bus_root, "alice", "idle")
    (bus_root / "inbox" / "alice.jsonl").write_text("{not json\n", encoding="utf-8")
    nudge = _RecordingNudge()
    roster = _stuck_roster()

    rows = coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=nudge, now=1000.0)
    assert nudge.calls == []
    assert _kinds(rows) == ["stuck-state-unreadable"]

    # A missing cursor is equally unreadable, and equally not zero.
    (bus_root / "inbox" / "alice.jsonl").write_text("", encoding="utf-8")
    _unread(bus_root, "alice", 4)
    (bus_root / "cursors" / "alice.json").unlink()
    rows = coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=nudge, now=2000.0)
    assert nudge.calls == []
    assert _kinds(rows) == ["stuck-state-unreadable"]


def test_c19_non_tmux_endpoint_is_surfaced_unreachable_not_nudged(bus_root: Path) -> None:
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "coordinator-agent", 2)
    _heartbeat(bus_root, "coordinator-agent", "idle")
    nudge = _RecordingNudge()

    rows = coordinator.resolve_stuck_agents(bus_root, _stuck_roster(), epoch=1,
                                            nudge_fn=nudge, now=1000.0)

    assert nudge.calls == [], "monitor:file has no push channel — never send keys at it"
    assert _kinds(rows, "coordinator-agent") == ["stuck-detected", "stuck-unreachable"]


def test_c19_adapter_refusal_is_recorded_and_retried_never_bypassed(bus_root: Path) -> None:
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "alice", 2)
    _heartbeat(bus_root, "alice", "idle")
    refusing = _RecordingNudge(rc=2, out="REFUSING to nudge: window produced output 3s ago")
    roster = _stuck_roster()

    rows = coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=refusing,
                                            now=1000.0)
    assert [r["kind"] for r in rows if r["kind"] == "stuck-nudge-refused"]
    state = json.loads((bus_root / "stuck_state.json").read_text())
    assert "last_nudge_ts" not in state["alice"], "a refusal is not a nudge"

    # A refusal backs off (an unresolvable endpoint must not spawn a subprocess
    # every 45s tick) but is genuinely retried afterwards — never bypassed.
    coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=refusing, now=1045.0)
    assert len(refusing.calls) == 1
    coordinator.resolve_stuck_agents(
        bus_root, roster, epoch=1, nudge_fn=refusing,
        now=1000.0 + coordinator._STUCK_REFUSAL_RETRY_S + 1)
    assert len(refusing.calls) == 2


def test_c19_detection_advisory_is_deduped_across_ticks(bus_root: Path) -> None:
    _provision(bus_root, "alice", "coordinator-agent")
    _unread(bus_root, "alice", 2)
    _heartbeat(bus_root, "alice", "idle")
    nudge = _RecordingNudge()
    roster = _stuck_roster()

    first = coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=nudge, now=1000.0)
    second = coordinator.resolve_stuck_agents(bus_root, roster, epoch=1, nudge_fn=nudge, now=1045.0)

    assert "stuck-detected" in _kinds(first)
    assert "stuck-detected" not in _kinds(second), "45s ticks must not flood advisory.jsonl"


# ------------------------------------------- C20 last hop: bus -> operator


def _op_msg(kind: str, *, mid: str, ts: str, **payload) -> dict:
    row = _message("alice", "coordinator-agent", kind, seq=1)
    row["id"] = mid
    row["ts"] = ts
    row["payload"] = payload or {"detail": "human signature required"}
    return row


_T0 = 1_800_000_000.0


def _iso(offset_s: float) -> str:
    from datetime import datetime, timezone as _tz
    return datetime.fromtimestamp(_T0 - offset_s, _tz.utc).isoformat(timespec="seconds")


def test_c20_fresh_operator_item_is_not_escalated(bus_root: Path) -> None:
    _provision(bus_root, *AGENTS)
    _append(bus_root / "inbox" / "coordinator-agent.jsonl",
            _op_msg("token-request", mid="m-1", ts=_iso(60)))
    nudge = _RecordingNudge()

    rows = coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=nudge, now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    assert nudge.calls == []
    assert rows == []
    assert coordinator._OPERATOR_ESCALATION_MARKER not in \
        (bus_root / "tokens" / "token-queue.md").read_text()


def test_c20_overdue_item_nudges_the_coordinator_and_records_unreachable(
        bus_root: Path) -> None:
    """monitor:file has no push, so the adapter refuses — that IS defect C8's shape."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "inbox" / "coordinator-agent.jsonl",
            _op_msg("token-request", mid="m-1", ts=_iso(3600)))
    refusing = _RecordingNudge(rc=2, out="REFUSING: endpoint is not tmux")

    rows = coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=refusing, now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    assert [c[0] for c in refusing.calls] == ["coordinator-agent"]
    assert [r["kind"] for r in rows] == ["operator-backlog-unreachable"]
    # Not yet past the bypass deadline: the token queue is untouched.
    assert coordinator._OPERATOR_ESCALATION_MARKER not in \
        (bus_root / "tokens" / "token-queue.md").read_text()


def test_c20_bypass_appends_a_checkboxless_block_and_is_idempotent(bus_root: Path) -> None:
    _provision(bus_root, *AGENTS)
    _append(bus_root / "inbox" / "coordinator-agent.jsonl",
            _op_msg("defect", mid="m-42", ts=_iso(4 * 3600),
                    detail="Human amendment required. No further inference permitted"))
    nudge = _RecordingNudge(rc=2, out="refused")
    tq = bus_root / "tokens" / "token-queue.md"

    for _ in range(3):
        rows = coordinator.pending_operator_actions(
            bus_root, _stuck_roster(), epoch=1, nudge_fn=nudge, now=_T0,
            artifact_dir=bus_root / "no-such-dir")
    text = tq.read_text(encoding="utf-8")

    assert text.count(f"{coordinator._OPERATOR_ESCALATION_MARKER} m-42") == 1
    assert "Human amendment required" in text
    # NEVER a checkbox: the daemon relays, only the operator signs.
    assert "- [ ]" not in text.split(coordinator._OPERATOR_ESCALATION_MARKER, 1)[1]
    assert "- [x]" not in text.split(coordinator._OPERATOR_ESCALATION_MARKER, 1)[1]


def test_c20_read_items_are_never_escalated(bus_root: Path) -> None:
    _provision(bus_root, *AGENTS)
    inbox = bus_root / "inbox" / "coordinator-agent.jsonl"
    _append(inbox, _op_msg("token-request", mid="m-1", ts=_iso(9 * 3600)))
    (bus_root / "cursors" / "coordinator-agent.json").write_text(
        json.dumps({"agent": "coordinator-agent", "offset": inbox.stat().st_size}),
        encoding="utf-8")
    nudge = _RecordingNudge()

    rows = coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=nudge, now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    assert rows == [] and nudge.calls == []


def test_c20_non_operator_traffic_does_not_escalate(bus_root: Path) -> None:
    _provision(bus_root, *AGENTS)
    _append(bus_root / "inbox" / "coordinator-agent.jsonl",
            _op_msg("status", mid="m-9", ts=_iso(9 * 3600), detail="fyi"))
    nudge = _RecordingNudge()

    rows = coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=nudge, now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    assert rows == [] and nudge.calls == []


def test_c20_unreadable_backlog_is_skipped_not_read_as_empty(bus_root: Path) -> None:
    _provision(bus_root, *AGENTS)
    (bus_root / "inbox" / "coordinator-agent.jsonl").write_text("{oops\n", encoding="utf-8")
    nudge = _RecordingNudge()

    rows = coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=nudge, now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    assert [r["kind"] for r in rows] == ["operator-backlog-unreadable"]
    assert nudge.calls == []


def test_c20_receipt_scan_is_inert_without_the_declaration(bus_root: Path, tmp_path: Path) -> None:
    """No false positives: a script that has not opted in tells us nothing."""
    art = tmp_path / "operator"
    art.mkdir()
    (art / "ratify_thing.sh").write_text("#!/bin/bash\necho hi\n", encoding="utf-8")
    _provision(bus_root, *AGENTS)

    rows = coordinator.scan_operator_receipts(bus_root, _stuck_roster(), epoch=1,
                                              artifact_dir=art)
    assert rows == []


def test_c20_declared_gate_never_presented_is_a_defect_against_the_producer(
        bus_root: Path, tmp_path: Path) -> None:
    art = tmp_path / "operator"
    art.mkdir()
    (art / "ratify_thing.sh").write_text(
        "#!/bin/bash\n# BUS-GATE: OP-THING-2026\necho hi\n", encoding="utf-8")
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl",
            _message("alice", "coordinator-agent", "status", seq=3,
                     payload={"script": str(art / "ratify_thing.sh")}))
    roster = [{"id": "alice", "role": "main", "endpoint": "tmux:agent:alice"},
              {"id": "coordinator-agent", "role": "coordinator-agent", "endpoint": "monitor:file"}]

    rows = coordinator.scan_operator_receipts(bus_root, roster, epoch=1, artifact_dir=art)

    assert [r["kind"] for r in rows] == ["defect"]
    assert rows[0]["subject"] == "alice" and rows[0]["gate_id"] == "OP-THING-2026"
    notices = [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
               if (r.get("payload") or {}).get("event") == "unrequested-operator-gate"]
    assert len(notices) == 1

    # Idempotent: the coordinator is notified once per gate, not every 45s.
    coordinator.scan_operator_receipts(bus_root, roster, epoch=1, artifact_dir=art)
    notices = [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
               if (r.get("payload") or {}).get("event") == "unrequested-operator-gate"]
    assert len(notices) == 1


def test_c20_receipt_superseded_and_token_queue_all_exempt(bus_root: Path, tmp_path: Path) -> None:
    art = tmp_path / "operator"
    art.mkdir()
    for name, gate in (("a.sh", "OP-A"), ("b.sh", "OP-B"), ("c.sh", "OP-C")):
        (art / name).write_text(f"#!/bin/bash\n# BUS-GATE: {gate}\n", encoding="utf-8")
    (art / "a.sh.receipt.json").write_text("{}", encoding="utf-8")
    (art / "b.sh.superseded").write_text("replaced by c.sh\n", encoding="utf-8")
    _provision(bus_root, *AGENTS)
    tq = bus_root / "tokens" / "token-queue.md"
    tq.write_text(tq.read_text(encoding="utf-8") + "\n- [ ] **OP-C** pending\n", encoding="utf-8")

    rows = coordinator.scan_operator_receipts(bus_root, _stuck_roster(), epoch=1, artifact_dir=art)
    assert rows == []


# ------------------------------------------- C27 first hop: outbox -> token-queue.md


def _token_request(sender: str = "alice", *, gate: str, task_id: str = "task-1",
                   seq: int = 1, validated: bool = True) -> dict:
    """The exact shape of the two 2026-07-29 requests that were never presented."""
    payload: dict[str, object] = {"gate_id": gate, "block_ref": "handoffs/active/x.md#L1"}
    if validated:
        payload["validated"] = {"cmd": "bash artifacts/operator/ratify.sh",
                                "dry_run_exit": 0,
                                "dry_run_evidence": "artifacts/operator/ratify.dryrun.log"}
    return _message(sender, "coordinator-agent", "token-request", seq=seq,
                    task_id=task_id, needs_routing_to=["coordinator-agent"],
                    action_required=True, payload=payload)


def test_c27_token_request_is_presented_at_manual_authority(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """C27: the live config is `manual`; a gate filed there MUST still reach the operator.

    Regression for the 2026-07-29 loss of RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729 and
    RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729 — both well-formed, both routed to
    coordinator-agent, both action_required, neither ever written to token-queue.md.
    """
    _provision(bus_root, *AGENTS)
    _quiet_tick_seams(monkeypatch)
    assert coordinator._authority(coordinator._load_config(bus_root)) == "manual"
    _append(bus_root / "outbox" / "alice.jsonl", _token_request(gate="RATIFY-THING-20260729"))

    coordinator.tick(bus_root, epoch=1)

    assert "RATIFY-THING-20260729" in (bus_root / "tokens" / "token-queue.md").read_text(
        encoding="utf-8")


def test_c27_presentation_writes_no_queue_row_at_manual_authority(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Transport, not judgment. Presenting a gate must not HOLD the task."""
    _provision(bus_root, *AGENTS)
    _quiet_tick_seams(monkeypatch)
    _append(bus_root / "queue.jsonl", _queue("task-1", status="RUNNING", owner="alice"))
    _append(bus_root / "outbox" / "alice.jsonl", _token_request(gate="RATIFY-HOLD-20260729"))
    before = _read_jsonl(bus_root / "queue.jsonl")

    coordinator.tick(bus_root, epoch=1)

    assert "RATIFY-HOLD-20260729" in (bus_root / "tokens" / "token-queue.md").read_text(
        encoding="utf-8")
    assert _read_jsonl(bus_root / "queue.jsonl") == before, \
        "at manual authority the daemon presents the gate but decides nothing"


def test_c27_presentation_is_idempotent_across_ticks(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _provision(bus_root, *AGENTS)
    _quiet_tick_seams(monkeypatch)
    _append(bus_root / "outbox" / "alice.jsonl", _token_request(gate="RATIFY-ONCE-20260729"))

    for _ in range(3):
        coordinator.tick(bus_root, epoch=1)

    text = (bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")
    assert text.count("### RATIFY-ONCE-20260729") == 1


def test_c27_two_requests_sharing_a_gate_id_append_one_block(bus_root: Path) -> None:
    """`existing` is read once per pass, so in-pass dedupe needs its own guard."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl", _token_request(gate="RATIFY-DUP-20260729"))
    _append(bus_root / "outbox" / "bob.jsonl",
            _token_request("bob", gate="RATIFY-DUP-20260729", task_id="task-2", seq=2))
    config = json.loads((bus_root / "config.yaml").read_text(encoding="utf-8"))

    coordinator.relay_token_blocks(bus_root, config, epoch=1)

    text = (bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")
    assert text.count("### RATIFY-DUP-20260729") == 1


def test_c27_always_on_presentation_does_not_swallow_the_hold_row(bus_root: Path) -> None:
    """The regression the C27 restructure exists to prevent.

    `relay_tokens` used to guard block AND queue row behind one `gate in existing`
    check. Once the always-on tier writes the block first, the assign-tier pass would
    then find the gate present and emit NO HELD_OP_GATE row — silently converting a
    presented gate into an unheld task. Block and row are now independently idempotent.
    """
    _provision(bus_root, *AGENTS)
    _append(bus_root / "queue.jsonl", _queue("task-1", status="RUNNING", owner="alice"))
    _append(bus_root / "outbox" / "alice.jsonl", _token_request(gate="RATIFY-BOTH-20260729"))
    config = json.loads((bus_root / "config.yaml").read_text(encoding="utf-8"))
    roster = [r for r in config["roster"]]

    coordinator.relay_token_blocks(bus_root, config, epoch=1)          # always-on tier
    reports = coordinator._outbox_reports(bus_root, roster)
    blocks, extra = coordinator.relay_tokens(                          # assign tier, same tick
        bus_root, reports, coordinator.fold_queue(bus_root), epoch=1)

    assert blocks == [], "the block was already presented; do not duplicate it"
    holds = [r for r in extra if r.get("status") == "HELD_OP_GATE"]
    assert [h["task_id"] for h in holds] == ["task-1"]
    assert holds[0]["operator_gates"] == ["RATIFY-BOTH-20260729"]


def test_c27_unvalidated_request_is_a_defect_at_manual_authority_too(bus_root: Path) -> None:
    """A defect that only fires under `assign` is a defect nobody sees."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl",
            _token_request(gate="RATIFY-BARE-20260729", validated=False))
    config = json.loads((bus_root / "config.yaml").read_text(encoding="utf-8"))

    rows = coordinator.relay_token_blocks(bus_root, config, epoch=1)

    assert [r["check"] for r in rows] == ["token-prevalidation"]
    assert "RATIFY-BARE-20260729" not in (
        bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")


# ------------------------------------------- C27c: the net reads outboxes too


def test_c27c_undelivered_token_request_escalates_from_the_outbox(bus_root: Path) -> None:
    """C27c: the last-hop net must not depend on the hop before it having worked.

    Regression for the exact 2026-07-29 shape: a well-formed token-request that never
    reached the coordinator's inbox, so the mechanism built to catch "a human
    signature went unseen" reported nothing for hours.
    """
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl",
            _op_msg("token-request", mid="m-lost", ts=_iso(6 * 3600),
                    gate_id="RATIFY-LOST-20260729"))
    nudge = _RecordingNudge()

    rows = coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=nudge, now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    text = (bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")
    assert f"{coordinator._OPERATOR_ESCALATION_MARKER} m-lost" in text
    assert "never reached" in text and "DELIVERY failure" in text
    assert [r["kind"] for r in rows] == ["operator-bypass-escalated"]
    # NEVER a checkbox: the daemon relays, only the operator signs.
    assert "- [ ]" not in text.split(coordinator._OPERATOR_ESCALATION_MARKER, 1)[1]


def test_c27c_relayed_item_is_not_escalated_twice(bus_root: Path) -> None:
    """Evidence, not delivery. A relayed message belongs to the inbox path."""
    _provision(bus_root, *AGENTS)
    src = _op_msg("token-request", mid="m-relayed", ts=_iso(6 * 3600))
    _append(bus_root / "outbox" / "alice.jsonl", src)
    relayed = _op_msg("token-request", mid="m-inbox-copy", ts=_iso(6 * 3600))
    relayed["relayed_src"] = "m-relayed"
    _append(bus_root / "inbox" / "coordinator-agent.jsonl", relayed)
    nudge = _RecordingNudge()

    coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=nudge, now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    text = (bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")
    assert f"{coordinator._OPERATOR_ESCALATION_MARKER} m-relayed" not in text
    assert text.count(coordinator._OPERATOR_ESCALATION_MARKER) == 1


def test_c27c_presented_gate_is_evidence_enough(bus_root: Path) -> None:
    """A gate the operator can already see needs no escalation — that IS the goal."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl",
            _op_msg("token-request", mid="m-shown", ts=_iso(9 * 3600),
                    gate_id="RATIFY-SHOWN-20260729"))
    tq = bus_root / "tokens" / "token-queue.md"
    tq.write_text(tq.read_text(encoding="utf-8") + "\n### RATIFY-SHOWN-20260729\n", encoding="utf-8")

    rows = coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=_RecordingNudge(), now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    assert rows == []
    assert coordinator._OPERATOR_ESCALATION_MARKER not in tq.read_text(encoding="utf-8")


def test_c27c_answered_item_is_evidence_enough(bus_root: Path) -> None:
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl",
            _op_msg("defect", mid="m-answered", ts=_iso(9 * 3600)))
    # The answerer must itself be on the roster passed in — evidence is gathered
    # from roster members' files, exactly as every other scan in this module is.
    _append(bus_root / "outbox" / "coordinator-agent.jsonl",
            _message("coordinator-agent", "alice", "ack", seq=9, corr_id="m-answered"))

    rows = coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=_RecordingNudge(), now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    assert rows == []


def test_c27c_fresh_and_non_operator_outbox_traffic_stay_quiet(bus_root: Path) -> None:
    """The narrowness is the point: a noisy net gets normalised, which is the
    original failure mode."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl",
            _op_msg("token-request", mid="m-fresh", ts=_iso(60)))
    _append(bus_root / "outbox" / "alice.jsonl",
            _op_msg("status", mid="m-chatter", ts=_iso(9 * 3600), detail="fyi"))

    rows = coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=_RecordingNudge(), now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    assert rows == []
    assert coordinator._OPERATOR_ESCALATION_MARKER not in (
        bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")


def test_c27c_outbox_escalation_is_idempotent(bus_root: Path) -> None:
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl",
            _op_msg("token-request", mid="m-once", ts=_iso(9 * 3600)))

    for _ in range(3):
        coordinator.pending_operator_actions(
            bus_root, _stuck_roster(), epoch=1, nudge_fn=_RecordingNudge(), now=_T0,
            artifact_dir=bus_root / "no-such-dir")

    text = (bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")
    assert text.count(f"{coordinator._OPERATOR_ESCALATION_MARKER} m-once") == 1


def test_c27c_unreadable_outbox_is_skipped_not_read_as_empty(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FAIL CLOSED: 'I could not scan' is never 'nothing is waiting'."""
    _provision(bus_root, *AGENTS)

    def boom(*_a, **_k):
        raise RuntimeError("outbox unreadable")

    monkeypatch.setattr(coordinator, "unevidenced_operator_outbox", boom)
    rows = coordinator.pending_operator_actions(
        bus_root, _stuck_roster(), epoch=1, nudge_fn=_RecordingNudge(), now=_T0,
        artifact_dir=bus_root / "no-such-dir")

    assert [r["kind"] for r in rows] == ["operator-outbox-unreadable"]


# ------------------------------------------- P1b: a dead daemon must not read `working`


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True
    return True


def test_p1b_status_marks_a_dead_daemon_stale_not_working(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """P1b: cmd_run writes "idle" only on a CLEAN exit, so a crash or a reboot leaves
    `state: working` on disk forever. The 2026-07-29 cold start read exactly that —
    epoch=11 pid=1928027 age=2157s naming a PID that did not exist — and nearly
    concluded the bus was being serviced while nothing was running."""
    # Do not ASSUME a high pid is free — pid_max is 4194304 on this host, so a
    # hardcoded constant is a coin flip that fails on a busy machine. Probe for one
    # that genuinely does not exist, and fail loudly if none does.
    dead = next((p for p in range(4_194_303, 4_190_000, -1)
                 if not _pid_exists(p)), None)
    assert dead is not None, "no free pid to test with"
    coordinator._write_atomic(coordinator._heartbeat_path(bus_root), {
        "agent": coordinator.COORDINATOR_DAEMON, "state": "working", "task_id": None,
        "ts": "2026-07-29T12:00:00+00:00", "epoch": 11, "note": "advisory", "pid": dead})

    assert coordinator.main(["--bus-root", str(bus_root), "status"]) == 0
    out = capsys.readouterr().out

    # C37 changed the rendering: the verdict now LEADS in one word instead of
    # being a parenthetical spliced into `state=`. The contract this test guards
    # — a dead daemon must not read as working — is unchanged.
    assert out.splitlines()[0] == "coordinator-daemon: DEAD"
    assert f"pid {dead} does not exist" in out
    assert f"pid={dead}" in out, "the evidence itself is preserved, only annotated"


def test_p1b_status_leaves_a_live_daemon_unannotated(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    coordinator._write_heartbeat(bus_root, epoch=12, state="working", note="advisory")

    assert coordinator.main(["--bus-root", str(bus_root), "status"]) == 0
    out = capsys.readouterr().out

    assert "state=working" in out
    assert "STALE" not in out and "unverified" not in out


@pytest.mark.parametrize("pid", [None, "", "not-a-pid", 0, -1])
def test_p1b_unusable_pid_is_reported_unknown_never_guessed(pid: object) -> None:
    """'I cannot tell' is reported as such. Rendering it as either alive or dead is
    the fail-open/fail-closed guess this whole module exists to refuse."""
    alive, why = coordinator.daemon_liveness({"state": "working", "pid": pid})
    assert alive is None and why


def test_p1b_liveness_recognises_a_process_owned_by_someone_else(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """PermissionError means the process EXISTS under another uid — alive, not absent.
    Reading it as absent would report a healthy daemon as dead."""
    def denied(_pid: int, _sig: int) -> None:
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(coordinator.os, "kill", denied)
    alive, why = coordinator.daemon_liveness({"pid": 12345})
    assert alive is True and "another user" in why


def test_c26_a_prboot_heartbeat_is_stale_even_when_its_pid_is_alive(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """C26's second check. A pid check answers "does a process with that number
    exist", not "is it MY process" — and pid numbering restarts at boot, so a
    recorded pid can be recycled onto something unrelated and report alive. The
    heartbeat is written before boot, so it cannot describe a running process.
    """
    hb_path = coordinator._heartbeat_path(bus_root)
    coordinator._write_atomic(hb_path, {
        "agent": coordinator.COORDINATOR_DAEMON, "state": "working", "task_id": None,
        "ts": "2026-07-29T12:00:00+00:00", "epoch": 11, "note": "advisory",
        "pid": os.getpid()})                          # a genuinely LIVE pid
    boot = coordinator.boot_time()
    assert boot is not None, "this host exposes /proc/uptime"
    os.utime(hb_path, (boot - 3600, boot - 3600))

    assert coordinator.main(["--bus-root", str(bus_root), "status"]) == 0
    out = capsys.readouterr().out

    assert out.splitlines()[0] == "coordinator-daemon: DEAD"
    assert "recycled" in out


def test_c26_boot_check_is_unknowable_not_false_without_proc_uptime(tmp_path: Path) -> None:
    """Where boot time cannot be read the answer is None, and cmd_status then leaves
    the pid verdict alone — 'I cannot tell' never becomes 'it is fine'."""
    assert coordinator.boot_time(tmp_path / "no-such-uptime") is None


def test_c26_a_post_boot_heartbeat_is_not_flagged(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    # This test is about the BOOT check, so the C37 identity check is isolated out:
    # the heartbeat here is written by pytest, not by a daemon, so its cmdline
    # legitimately does not name session_bus_coordinator. Verified separately
    # against the live daemon, which reports "is the coordinator-daemon".
    monkeypatch.setattr(coordinator, "process_cmdline",
                        lambda _p: "python session_bus_coordinator.py run")
    coordinator._write_heartbeat(bus_root, epoch=13, state="working", note="advisory")

    assert coordinator.main(["--bus-root", str(bus_root), "status"]) == 0
    out = capsys.readouterr().out

    assert "state=working" in out and "recycled" not in out
    assert out.splitlines()[0] == "coordinator-daemon: HEALTHY"


# ------------------------------------------- C33: a refused gate must reach a reader


def test_c33_unpresentable_gate_notifies_the_coordinator(bus_root: Path) -> None:
    """C33: `relay_tokens` correctly refuses to present an unvalidated command, but the
    refusal was reported ONLY to advisory.jsonl, which is delivered to nobody. So a gate
    could be filed, be schema-valid, be silently never presented, and the notice about
    that be a second unread sink one level up. Live instance: mainA's
    E5-THROTTLE-SCOPE-ERA-ROW-20260729, filed 2026-07-29 15:18Z with `action_required`,
    carrying `apply_command` + top-level `dry_run_evidence` instead of `validated`.
    """
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl",
            _token_request(gate="RATIFY-NOEVID-20260729", validated=False))
    config = json.loads((bus_root / "config.yaml").read_text(encoding="utf-8"))

    rows = coordinator.relay_token_blocks(bus_root, config, epoch=1)

    assert [r["check"] for r in rows] == ["token-prevalidation"]
    assert rows[0]["gate_id"] == "RATIFY-NOEVID-20260729"
    notices = [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
               if (r.get("payload") or {}).get("event") == "token-request-not-presented"]
    assert len(notices) == 1
    assert notices[0]["payload"]["gate_id"] == "RATIFY-NOEVID-20260729"
    assert notices[0]["payload"]["from_agent"] == "alice"
    assert "re-file" in notices[0]["payload"]["action"]


def test_c33_notice_is_sent_once_per_gate_not_every_tick(bus_root: Path) -> None:
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl",
            _token_request(gate="RATIFY-NOEVID-20260729", validated=False))
    config = json.loads((bus_root / "config.yaml").read_text(encoding="utf-8"))

    for _ in range(3):
        coordinator.relay_token_blocks(bus_root, config, epoch=1)

    notices = [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
               if (r.get("payload") or {}).get("event") == "token-request-not-presented"]
    assert len(notices) == 1, "45s ticks must not flood the coordinator's inbox"


def test_c33_a_presentable_gate_produces_no_notice(bus_root: Path) -> None:
    """The notice means 'this gate is NOT in front of the operator'. A presented gate
    must not produce one, or the signal stops meaning anything."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl", _token_request(gate="RATIFY-FINE-20260729"))
    config = json.loads((bus_root / "config.yaml").read_text(encoding="utf-8"))

    coordinator.relay_token_blocks(bus_root, config, epoch=1)

    assert not [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
                if (r.get("payload") or {}).get("event") == "token-request-not-presented"]
    assert "RATIFY-FINE-20260729" in (
        bus_root / "tokens" / "token-queue.md").read_text(encoding="utf-8")


# ------------------------------------------- C29: identity checks, consistently


@pytest.mark.parametrize("argv", [
    ["drain", "--agent", "ghost"],
    ["drain", "--agent", "ghost", "--triage"],
    ["triage", "--agent", "ghost"],
    ["cursor", "--agent", "ghost", "--set", "5"],
    ["cursor", "--agent", "ghost"],
])
def test_c29_identity_taking_verbs_refuse_a_non_roster_id(
        bus_root: Path, capsys: pytest.CaptureFixture[str], argv: list[str]) -> None:
    """C29: the two halves of this CLI disagreed about whether an identity must EXIST.

    `append --agent ghost` failed CLOSED with the valid id list; drain, triage and
    cursor took an identity and never validated it. Now they all use the same helper
    and say the same thing.
    """
    assert bus.main(["--bus-root", str(bus_root), *argv]) == 1
    err = capsys.readouterr().err
    assert "not a roster id" in err
    assert "alice" in err, "the refusal must list the valid ids, as append's does"


def test_c29_drain_on_a_ghost_inbox_refuses_and_advances_nothing(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The reachable production shape: C28 relay RECREATES old-id inboxes, so the
    file-exists check passed for exactly the ids that no longer exist. A session still
    using its pre-rename id drained a ghost inbox cleanly, saw "no new messages", and
    concluded it was up to date — the precise C3 failure, one identity check short.

    Refusing rather than warning is the point: a warning leaves the CURSOR ADVANCE in
    place, which silently consumes another agent's mail. The read is the damage.
    """
    _provision(bus_root, *AGENTS)
    ghost_inbox = bus_root / "inbox" / "ghost.jsonl"
    _append(ghost_inbox, _message("alice", "bob", "finding", seq=1, task_id="not-yours"))

    assert bus.main(["--bus-root", str(bus_root), "drain", "--agent", "ghost"]) == 1
    out = capsys.readouterr()

    assert "not a roster id" in out.err
    assert "not-yours" not in out.out, "a ghost id must not be shown another agent's mail"
    assert not (bus_root / "cursors" / "ghost.json").exists(), \
        "and must not leave a cursor behind"
    assert ghost_inbox.exists(), "existing evidence is surfaced, never deleted (C7)"


def test_c29_triage_no_longer_answers_a_ghost_with_an_all_clear(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The worse half. `routed_view` filters on membership, so an unknown id matched
    nothing and got `(triage: no routed messages awaiting <id>)` — exit 0,
    indistinguishable from "you are clear". Triage is designed to be the LOUDEST signal
    on this bus, the one that survives a broken delivery path; a stale or typo'd id
    turned it into a silent all-clear."""
    _provision(bus_root, *AGENTS)

    assert bus.main(["--bus-root", str(bus_root), "triage", "--agent", "ghost"]) == 1
    out = capsys.readouterr()

    assert "no routed messages awaiting" not in out.out
    assert "not a roster id" in out.err


def test_c29_rostered_ids_are_entirely_unaffected(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The positive control: fail-closed must not become fail-shut."""
    _provision(bus_root, *AGENTS)

    assert bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"]) == 0
    assert bus.main(["--bus-root", str(bus_root), "triage", "--agent", "alice"]) == 0
    assert bus.main(["--bus-root", str(bus_root), "cursor", "--agent", "alice"]) == 0
    assert bus.main(["--bus-root", str(bus_root), "cursor", "--agent", "alice", "--set", "0"]) == 0
    capsys.readouterr()


def test_c29_an_unprovisioned_rostered_id_still_gets_the_C3_bootstrap_message(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The identity check must run BEFORE the file check but must not replace it — the
    two failures have different repairs, and telling someone to `provision` an id that
    is not on the roster sends them to a command that also refuses."""
    assert bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"]) == 2
    err = capsys.readouterr().err
    assert "no inbox for 'alice'" in err and "provision" in err
    assert "not a roster id" not in err


# ------------------------------------------- C34: the two sides ran different validators


def test_c34_schema_invalid_defect_is_flagged_once_not_every_tick(bus_root: Path) -> None:
    """C34: this was the ONE defect path in relay that appended unconditionally.

    An outbox row is never repaired by the daemon (single writer), so an invalid row is
    invalid forever and re-reporting it every 45s says nothing new. Measured: the roster
    rename added `_renamed_from` to 217 rows, which the schema forbids, so 249 distinct
    shapes were re-emitted every tick — ~20,000 advisory rows/hour into a 38.5 MiB file
    that `already_flagged` re-reads IN FULL every tick, on the daemon's hot path.
    """
    _provision(bus_root, *AGENTS)
    _append(bus_root / "outbox" / "alice.jsonl", {
        "id": "malformed-source", "to": "bob", "kind": "finding"})
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]

    first = coordinator.relay_outbox_messages(bus_root, roster, epoch=1)
    for entry in first:
        _append(bus_root / "advisory.jsonl", entry)      # what the tick loop does
    second = coordinator.relay_outbox_messages(bus_root, roster, epoch=1)

    assert [r.get("check") for r in first] == ["outbox-schema"]
    assert first[0]["relayed_src"] == "malformed-source"
    assert second == [], "45s ticks must not re-report a row that cannot change"
    assert _read_jsonl(bus_root / "inbox" / "bob.jsonl") == [], "and it is still not relayed"


def test_c34_partial_validation_warns_on_the_SUCCESS_path_too(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """C34: without jsonschema, `validate_row` checked 6 keys and returned SILENTLY, so
    "validated" and "checked six keys exist" were indistinguishable to the caller.

    That distinction is the whole ballgame: agents author with `python3 ...` (no
    jsonschema — the 6-key check) while the daemon runs under the orchestrator venv
    (full schema). A message can pass authoring and be refused at relay, and nobody is
    told. 217 of 341 live outbox rows were in exactly that state.

    2026-08-11: the DEGRADE ITSELF is now reachable only when the schema grows a
    construct the vendored validator refuses (`_validator` no longer returns None
    merely because jsonschema is missing). This test keeps guarding that last
    resort — it must still announce itself rather than pass silently.
    """
    monkeypatch.setattr(bus, "_validator", lambda *_a: None)
    row = _message("alice", "bob", "finding", seq=1)
    row["_renamed_from"] = "someone-else"        # full schema forbids extra properties

    bus.validate_row(bus_root, row, "msg")       # must NOT raise — it is a degradation

    err = capsys.readouterr().err
    assert "no validator could be built" in err
    assert "required keys ONLY" in err
    assert "coordinator-daemon DOES validate in full" in err


def test_c34_partial_validation_still_raises_on_a_missing_required_key(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """The warning must not replace the check it warns about."""
    monkeypatch.setattr(bus, "_validator", lambda *_a: None)

    with pytest.raises(bus.BusError, match="missing required field"):
        bus.validate_row(bus_root, {"schema_version": "x", "id": "y"}, "msg")
    assert "no validator could be built" in capsys.readouterr().err


def test_c34_full_validation_stays_silent(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The positive control: when validation is real, it must not cry wolf — a warning
    on every valid row is a warning nobody reads."""
    pytest.importorskip("jsonschema")
    bus.validate_row(bus_root, _message("alice", "bob", "finding", seq=1), "msg")
    assert capsys.readouterr().err == ""


# ------------------------------------------- claim: row ownership the FS enforces


def test_claim_is_exclusive_and_the_loser_is_told_who_holds_it(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Observed 2026-07-29: mainD claimed TOP-40 #5 at 16:00:07 and finished at
    16:03:51 while mainC was independently building the same row; mainC found the
    flipped checkbox at 16:05:05 and threw its implementation away. Two mains, one
    row, five minutes apart, inside the first ten minutes of three mains on a shared
    queue.

    The collision map partitions FILES, not rows, and claiming was an outbox message —
    which only helps if the other main DRAINS between the claim and starting work.
    O_EXCL has no window between checking and taking, because there is no check.
    """
    row = "Run focused unit tests for stack priors, guard, enum sync"
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice", "--row", row]) == 0
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "bob", "--row", row]) == 2
    out = capsys.readouterr()
    assert "claimed by alice" in out.out
    assert "REFUSING" in out.err and "'alice'" in out.err


def test_claim_keys_on_task_text_not_line_number(bus_root: Path) -> None:
    """The queue's own rule: line numbers are a hint, task text is the identity —
    mains close rows live and every anchor below a closure shifts. Two mains reading
    the same row at different offsets must still collide."""
    a = "  Port the ~50-line   Hermes SQLite reader\t"
    b = "Port the ~50-LINE Hermes SQLite reader"
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice", "--row", a]) == 0
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "bob", "--row", b]) == 2


def test_claim_is_idempotent_for_its_own_holder(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A main that restarts mid-task must not be locked out of work it already holds."""
    row = "Guard or delete the legacy path"
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice", "--row", row]) == 0
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice", "--row", row]) == 0
    assert "already yours" in capsys.readouterr().out


def test_claim_release_only_releases_your_own(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Releasing someone else's claim would reintroduce the race, silently."""
    row = "Enumerate models on the system from both registries"
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice", "--row", row]) == 0

    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "bob",
                     "--row", row, "--release"]) == 1
    assert "may not release" in capsys.readouterr().err

    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice",
                     "--row", row, "--release"]) == 0
    # released -> the row is takeable again, which is the whole point of releasing
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "bob", "--row", row]) == 0


def test_claim_refuses_a_non_roster_id(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """C29 consistency: every identity-taking verb uses the same rule."""
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "ghost",
                     "--row", "anything"]) == 1
    assert "not a roster id" in capsys.readouterr().err
    assert not (bus_root / "claims").exists()


def test_claim_list_shows_holders_and_release_is_a_noop_when_unclaimed(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice", "--list"]) == 0
    assert "no rows claimed" in capsys.readouterr().out

    bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice", "--row", "row one"])
    bus.main(["--bus-root", str(bus_root), "claim", "--agent", "bob", "--row", "row two"])
    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice", "--list"]) == 0
    listing = capsys.readouterr().out
    assert "alice" in listing and "bob" in listing and "row one" in listing

    assert bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice",
                     "--row", "never claimed", "--release"]) == 0
    assert "not claimed" in capsys.readouterr().out


def test_claim_does_not_disturb_the_single_writer_lint(bus_root: Path) -> None:
    """`claims/` is a new area. `validate` must not start failing because of it —
    a validator nobody can get to green stops being read (the C2 rule)."""
    _provision(bus_root, *AGENTS)
    for name in ("human_only_paths.yaml", "human_only_paths.sha256"):
        shutil.copy2(LIVE_BUS_ROOT / name, bus_root / name)
    bus.main(["--bus-root", str(bus_root), "claim", "--agent", "alice", "--row", "a row"])

    assert bus.main(["--bus-root", str(bus_root), "validate"]) == 0


# --------------------------------------------------------------------- C34
#
# C34: agents author under /usr/bin/python3 (no jsonschema) and the daemon
# relays under the orchestrator venv (jsonschema 4.26), so for as long as
# `_validator` returned None without jsonschema the two sides applied DIFFERENT
# rules — 368 of 1137 live outbox rows passed authoring and were refused at
# relay. `session_bus` now falls back to a vendored draft-7 subset. These tests
# exist to prove the fallback is not a second, subtly different rulebook: what
# it accepts and rejects must match jsonschema exactly, or C34 has merely moved.

SCHEMA_DEFINITIONS = ("msg", "queue_row")


def _live_schema() -> dict:
    return json.loads((LIVE_BUS_ROOT / "session_bus.schema.json").read_text(encoding="utf-8"))


def _sub_schema(schema: dict, definition: str) -> dict:
    return {"$schema": schema["$schema"], "definitions": schema["definitions"],
            "$ref": f"#/definitions/{definition}"}


def _error_set(validator, row: dict) -> set:
    """(path, failing keyword) pairs — comparable across implementations, unlike
    the human-facing message text."""
    return {("/".join(str(p) for p in e.path), e.validator) for e in validator.iter_errors(row)}


def _reference_validator(definition: str):
    jsonschema = pytest.importorskip("jsonschema", reason="reference validator not installed")
    return jsonschema.Draft7Validator(_sub_schema(_live_schema(), definition))


def _vendored(definition: str) -> bus._MiniDraft7Validator:
    return bus._MiniDraft7Validator(_sub_schema(_live_schema(), definition))


VALID_MSG = {
    "schema_version": "session_bus.msg.v1",
    "id": "msg-20260811T090000Z-1-mainD",
    "ts": "2026-08-11T09:00:00+00:00",
    "from": "mainD",
    "to": "coordinator-agent",
    "kind": "status",
}

VALID_QUEUE_ROW = {
    "schema_version": "session_bus.queue.v1",
    "ts": "2026-08-11T09:00:00+00:00",
    "task_id": "c-own-round-4",
    "status": "READY",
    "lane": "none",
    "gating": "none",
    "epoch": 14,
}


def _mutants() -> list[tuple[str, str, dict]]:
    """A battery aimed at every assertion keyword the live schema uses, plus the
    real per-kind `allOf`/`if`/`then` payload rules."""
    cases: list[tuple[str, str, dict]] = [("msg", "pristine", dict(VALID_MSG)),
                                          ("queue_row", "pristine", dict(VALID_QUEUE_ROW))]
    for definition, base in (("msg", VALID_MSG), ("queue_row", VALID_QUEUE_ROW)):
        for key in base:
            cases.append((definition, f"drop:{key}", {k: v for k, v in base.items() if k != key}))
            cases.append((definition, f"nulled:{key}", {**base, key: None}))
            cases.append((definition, f"numbered:{key}", {**base, key: 7}))
            cases.append((definition, f"listed:{key}", {**base, key: []}))
            cases.append((definition, f"emptied:{key}", {**base, key: ""}))
    cases += [
        # additionalProperties — the 217-row `_renamed_from` class, and friends.
        ("msg", "extra:_renamed_from", {**VALID_MSG, "_renamed_from": "claude-main"}),
        ("msg", "extra:several", {**VALID_MSG, "summary": "s", "status": "done", "next": "x"}),
        ("queue_row", "extra:one", {**VALID_QUEUE_ROW, "note": "hi"}),
        # enum
        ("msg", "kind:blocker", {**VALID_MSG, "kind": "blocker"}),
        ("msg", "kind:decision", {**VALID_MSG, "kind": "decision"}),
        ("queue_row", "lane:tpu", {**VALID_QUEUE_ROW, "lane": "tpu"}),
        ("queue_row", "status:bogus", {**VALID_QUEUE_ROW, "status": "PARTIALLY_DONE"}),
        # const
        ("msg", "schema_version:v2", {**VALID_MSG, "schema_version": "session_bus.msg.v2"}),
        # pattern
        ("msg", "id:malformed", {**VALID_MSG, "id": "msg-2026-08-11-1-mainD"}),
        ("msg", "id:ok", {**VALID_MSG, "id": "msg-20260811T090000Z-42-coordinator-agent"}),
        ("msg", "priority:P9", {**VALID_MSG, "priority": "P9"}),
        ("msg", "priority:P0", {**VALID_MSG, "priority": "P0"}),
        ("queue_row", "task_id:leading-dot", {**VALID_QUEUE_ROW, "task_id": ".hidden"}),
        # boolean / number types
        ("msg", "requires_ack:string", {**VALID_MSG, "requires_ack": "yes"}),
        ("msg", "requires_ack:true", {**VALID_MSG, "requires_ack": True}),
        ("msg", "action_required:one", {**VALID_MSG, "action_required": 1}),
        # exclusiveMinimum / minimum / integer
        ("msg", "ack_deadline:zero", {**VALID_MSG, "ack_deadline_s": 0}),
        ("msg", "ack_deadline:positive", {**VALID_MSG, "ack_deadline_s": 30}),
        ("queue_row", "epoch:negative", {**VALID_QUEUE_ROW, "epoch": -1}),
        ("queue_row", "epoch:float", {**VALID_QUEUE_ROW, "epoch": 2.5}),
        ("queue_row", "epoch:whole-float", {**VALID_QUEUE_ROW, "epoch": 2.0}),
        ("queue_row", "epoch:bool", {**VALID_QUEUE_ROW, "epoch": True}),
        ("queue_row", "max_attempts:zero", {**VALID_QUEUE_ROW, "max_attempts": 0}),
        # nullable union type
        ("queue_row", "owner:null", {**VALID_QUEUE_ROW, "owner": None}),
        ("queue_row", "owner:number", {**VALID_QUEUE_ROW, "owner": 3}),
        # array: items / minItems / uniqueItems
        ("msg", "routing:empty", {**VALID_MSG, "needs_routing_to": []}),
        ("msg", "routing:dupes", {**VALID_MSG, "needs_routing_to": ["mainA", "mainA"]}),
        ("msg", "routing:blank", {**VALID_MSG, "needs_routing_to": [""]}),
        ("msg", "routing:number", {**VALID_MSG, "needs_routing_to": [1]}),
        ("msg", "routing:ok", {**VALID_MSG, "needs_routing_to": ["mainA", "auditor"]}),
        ("queue_row", "depends_on:mixed", {**VALID_QUEUE_ROW, "depends_on": ["a", 2]}),
        # per-kind allOf/if/then payload rules
        ("msg", "assign:no-payload", {**VALID_MSG, "kind": "task-assign", "task_id": "t"}),
        ("msg", "assign:payload-thin",
         {**VALID_MSG, "kind": "task-assign", "task_id": "t", "payload": {"lane": "none"}}),
        ("msg", "assign:payload-full",
         {**VALID_MSG, "kind": "task-assign", "task_id": "t",
          "payload": {"lane": "none", "lease_expires_ts": "2026-08-11T10:00:00+00:00",
                      "epoch": 14}}),
        ("msg", "assign:lane-bogus",
         {**VALID_MSG, "kind": "task-assign", "task_id": "t",
          "payload": {"lane": "quantum", "lease_expires_ts": "x", "epoch": 14}}),
        ("msg", "assign:no-task_id",
         {**VALID_MSG, "kind": "task-assign",
          "payload": {"lane": "none", "lease_expires_ts": "x", "epoch": 14}}),
        ("msg", "token:no-validated",
         {**VALID_MSG, "kind": "token-request",
          "payload": {"gate_id": "g", "block_ref": "b"}}),
        ("msg", "token:validated-thin",
         {**VALID_MSG, "kind": "token-request",
          "payload": {"gate_id": "g", "block_ref": "b", "validated": {"cmd": "true"}}}),
        ("msg", "token:full",
         {**VALID_MSG, "kind": "token-request",
          "payload": {"gate_id": "g", "block_ref": "b",
                      "validated": {"cmd": "true", "dry_run_exit": 0,
                                    "dry_run_evidence": "ok"}}}),
        ("msg", "reprioritize:thin",
         {**VALID_MSG, "kind": "reprioritize", "payload": {"task_id": "t"}}),
        ("msg", "reprioritize:bad-scope",
         {**VALID_MSG, "kind": "reprioritize",
          "payload": {"task_id": "t", "new_priority": "P1", "scope": "everywhere"}}),
        ("msg", "revoke:no-reason",
         {**VALID_MSG, "kind": "lease-revoke", "task_id": "t", "payload": {}}),
        ("msg", "propose:thin",
         {**VALID_MSG, "kind": "task-propose", "task_id": "t", "payload": {"lane": "none"}}),
        ("msg", "propose:full",
         {**VALID_MSG, "kind": "task-propose", "task_id": "t",
          "payload": {"lane": "none", "gating": "none", "spec_ref": "h.md#a",
                      "summary": "s"}}),
        ("msg", "propose:est-negative",
         {**VALID_MSG, "kind": "task-propose", "task_id": "t",
          "payload": {"lane": "none", "gating": "none", "spec_ref": "h.md#a",
                      "summary": "s", "est_wall_clock_h": -1}}),
        # payload must be an object at all
        ("msg", "payload:string", {**VALID_MSG, "payload": "not an object"}),
        # non-object instances entirely
        ("msg", "instance:list", []),
        ("msg", "instance:string", "nope"),
    ]
    return cases


@pytest.mark.parametrize("definition,label,row", [(d, l, r) for d, l, r in _mutants()],
                         ids=[f"{d}-{l}" for d, l, _ in _mutants()])
def test_vendored_validator_matches_jsonschema_on_a_mutant_battery(
        definition: str, label: str, row) -> None:
    """Verdict AND error set must agree. Verdict alone would pass a fallback that
    rejects for the wrong reason, and the reason is what the author reads."""
    reference, vendored = _reference_validator(definition), _vendored(definition)
    assert vendored.is_valid(row) == reference.is_valid(row), (
        f"{definition}/{label}: vendored says valid={vendored.is_valid(row)}, "
        f"jsonschema says valid={reference.is_valid(row)}")
    assert _error_set(vendored, row) == _error_set(reference, row), f"{definition}/{label}"


def test_vendored_validator_matches_jsonschema_on_the_whole_live_bus() -> None:
    """The corpus that mattered: every row actually on the bus. Read-only.

    A synthetic battery can only test the failure modes its author imagined;
    12 days of real agent output is the sample that found `_renamed_from`.
    """
    rows: list[tuple[str, str, dict]] = []
    for area, definition in (("outbox", "msg"), ("inbox", "msg"), ("queue.jsonl", "queue_row")):
        paths = ([LIVE_BUS_ROOT / area] if area.endswith(".jsonl")
                 else sorted((LIVE_BUS_ROOT / area).glob("*.jsonl")))
        for path in paths:
            if not path.exists():
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    rows.append((f"{path.name}:{lineno}", definition, json.loads(line)))
                except json.JSONDecodeError:
                    continue
    # WAS `assert len(rows) > 500` — a proxy for "this comparison is not vacuous",
    # and it encoded the corpus size at authoring time. On 2026-08-12 the bus runtime
    # was wiped and the corpus fell to ~100 rows, so the guard fired TRULY: it refused
    # to validate a truncated corpus and call it agreement. But the corpus did not
    # regrow — it kept shrinking — so a fixed floor would have stayed red forever,
    # which trains readers to ignore it. Lowering the number would have been face 1
    # committed in reverse.
    #
    # So assert the PROPERTY the number was proxying: THE READER SAW EVERYTHING THAT
    # IS THERE. That is scale-free, survives a wipe, and is strictly stronger — it is
    # face 14 (the reader dropped part of the input and said nothing) turned on this
    # test's own reader. Counted independently, by a different method than the loop
    # above, so a bug in that loop cannot satisfy its own check.
    on_disk = 0
    for area in ("outbox", "inbox", "queue.jsonl"):
        target = LIVE_BUS_ROOT / area
        for path in ([target] if area.endswith(".jsonl") else sorted(target.glob("*.jsonl"))):
            if path.exists():
                on_disk += sum(1 for ln in path.read_bytes().split(b"\n") if ln.strip())
    unparsable = on_disk - len(rows)
    assert rows, "live bus corpus is EMPTY — agreement over nothing is not agreement"
    assert unparsable == 0, (
        f"reader dropped {unparsable} of {on_disk} non-empty lines — every line on the "
        f"bus must be validated or the agreement is over a corpus this test narrowed itself")

    validators = {d: (_reference_validator(d), _vendored(d)) for d in SCHEMA_DEFINITIONS}
    disagreements = []
    for where, definition, row in rows:
        reference, vendored = validators[definition]
        if _error_set(vendored, row) != _error_set(reference, row):
            disagreements.append((where, sorted(_error_set(vendored, row)),
                                  sorted(_error_set(reference, row))))
    assert not disagreements, f"{len(disagreements)} disagreements, first: {disagreements[0]}"


def test_vendored_validator_refuses_a_schema_it_would_only_partly_enforce() -> None:
    """The fail-open this whole fix exists to close, one level up: a validator
    that ignores the keyword it does not know reports PASS on a row that
    violates it. Construction must refuse instead."""
    schema = _live_schema()
    schema["definitions"]["msg"]["properties"]["ts"]["format"] = "date-time"
    with pytest.raises(bus._UnsupportedSchema, match="format"):
        bus._MiniDraft7Validator(_sub_schema(schema, "msg"))

    schema = _live_schema()
    schema["definitions"]["msg"]["properties"]["from"]["$ref"] = "https://example.com/x.json"
    with pytest.raises(bus._UnsupportedSchema, match=r"\$ref"):
        bus._MiniDraft7Validator(_sub_schema(schema, "msg"))


@pytest.fixture()
def no_jsonschema(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reproduce the authoring interpreter: `import jsonschema` raises."""
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    with pytest.raises(ImportError):
        import jsonschema  # noqa: F401


def test_authoring_without_jsonschema_still_applies_the_full_schema(
        bus_root: Path, no_jsonschema: None) -> None:
    """C34 itself. Before the fix this row appended cleanly under
    /usr/bin/python3 and was then refused at relay, forever, silently."""
    _provision(bus_root, *AGENTS)
    assert bus._validator(_live_schema(), "msg").__class__ is bus._MiniDraft7Validator

    with pytest.raises(bus.BusError, match="Additional properties"):
        bus.validate_row(LIVE_BUS_ROOT, {**VALID_MSG, "summary": "routing intent as prose"}, "msg")
    with pytest.raises(bus.BusError, match="not one of"):
        bus.validate_row(LIVE_BUS_ROOT, {**VALID_MSG, "kind": "blocker"}, "msg")
    with pytest.raises(bus.BusError, match="required property"):
        bus.validate_row(LIVE_BUS_ROOT, {**VALID_MSG, "kind": "task-assign", "task_id": "t",
                                         "payload": {"lane": "none"}}, "msg")


def test_authoring_without_jsonschema_still_accepts_a_compliant_row(
        bus_root: Path, no_jsonschema: None, capsys: pytest.CaptureFixture[str]) -> None:
    """The other direction, and the one that takes the fleet down if it is wrong:
    a guard that forbids its own idiom passes review and breaks production. The
    documented `append` command must keep working, silently, with no jsonschema.
    """
    _provision(bus_root, *AGENTS)
    capsys.readouterr()

    assert bus.main(["--bus-root", str(bus_root), "append", "--agent", "alice",
                     "--target", "outbox", "--json",
                     json.dumps({"to": "bob", "kind": "status",
                                 "payload": {"summary": "still here"}})]) == 0
    captured = capsys.readouterr()
    assert "WARNING" not in captured.err, captured.err

    written = _read_jsonl(bus_root / "outbox" / "alice.jsonl")
    assert len(written) == 1 and written[0]["kind"] == "status"
    # And the daemon's own full-schema check agrees, which is the whole point.
    bus.validate_row(bus_root, written[0], "msg")


def test_append_refuses_an_unrelayable_row_at_the_author(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Failing at the author is the correct place: the rows this refuses were
    never being delivered anyway, they were just being written."""
    _provision(bus_root, *AGENTS)

    assert bus.main(["--bus-root", str(bus_root), "append", "--agent", "alice",
                     "--target", "outbox", "--json",
                     json.dumps({"to": "bob", "kind": "blocker"})]) != 0
    assert not _read_jsonl(bus_root / "outbox" / "alice.jsonl")


def test_renamed_from_is_accepted_so_the_migrated_rows_can_be_delivered() -> None:
    """C34 second half. The 2026-07-29 roster rename wrote `_renamed_from` onto
    the 217 rows it rewrote; `additionalProperties: false` forbade it, so relay
    refused every one of them — five operator token-requests among them, stranded
    two weeks. Stripping the field was the alternative and is not available: an
    outbox has exactly one writer and it is not the daemon. So the schema accepts
    the provenance, and this test is what stops a future tidy-up from re-breaking
    delivery by deleting the property as 'unused'.
    """
    for definition in ("msg",):
        vendored = _vendored(definition)
        assert vendored.is_valid({**VALID_MSG, "_renamed_from": "claude-main"})
        # Still typed, not a hole: it is a non-empty string or nothing.
        assert not vendored.is_valid({**VALID_MSG, "_renamed_from": ""})
        assert not vendored.is_valid({**VALID_MSG, "_renamed_from": 7})
    # Unrelated stray keys stay refused — this widened the schema by one field,
    # not into a bag of anything.
    assert not _vendored("msg").is_valid({**VALID_MSG, "_renamed_to": "x"})
    assert not _vendored("queue_row").is_valid({**VALID_QUEUE_ROW, "_renamed_from": "codex"})


def test_no_live_outbox_row_is_still_blocked_by_renamed_from() -> None:
    """The measurement that justified the change, kept as a regression: every one
    of the 217 rows must now pass, and this fails loudly if the property is
    narrowed later in a way the real corpus does not satisfy."""
    validator = _vendored("msg")
    blocked = []
    for path in sorted((LIVE_BUS_ROOT / "outbox").glob("*.jsonl")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "_renamed_from" not in row:
                continue
            reasons = {e.validator for e in validator.iter_errors(row)}
            if reasons:
                blocked.append((f"{path.name}:{lineno}", sorted(reasons)))
    assert not blocked, f"{len(blocked)} migrated rows still unrelayable, first: {blocked[0]}"


# --------------------------------------------------------------- C37 / C38
#
# The coordinator-daemon was dead from 2026-08-01T05:42:54Z to 2026-08-11T08:48:02Z
# — 243.1h, measured as the gap in advisory.jsonl — and nothing noticed. P1b had
# already added a pid check, so the interesting question was why that was not
# enough. Two independent holes, both reproduced against the real module before
# either was touched:
#   * `os.kill(pid, 0)` proves a process EXISTS, not that it is this daemon. The
#     boot check closes that only across a reboot; within one boot the number can
#     be re-issued to anything. A heartbeat naming pid 1 (/sbin/init) reported
#     `state=working`.
#   * heartbeat age was printed and never judged, so `age=876736s` and `age=19s`
#     produced the same verdict: none.

def _hb_file(root: Path, pid: int, *, age_s: float, state: str = "working") -> Path:
    path = root / "heartbeats" / "coordinator-daemon.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"agent": "coordinator-daemon", "epoch": 13, "pid": pid,
                                "state": state, "note": "advisory", "task_id": None}),
                    encoding="utf-8")
    stamp = time.time() - age_s
    os.utime(path, (stamp, stamp))
    return path


def test_daemon_liveness_rejects_a_recycled_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    """The C37 hole. Existence is not identity."""
    monkeypatch.setattr(coordinator, "process_cmdline", lambda pid: "/sbin/init splash")
    alive, why = coordinator.daemon_liveness({"pid": os.getpid()})
    assert alive is False
    assert "recycled" in why and "/sbin/init" in why


def test_daemon_liveness_accepts_the_real_daemon(monkeypatch: pytest.MonkeyPatch) -> None:
    """The compliant path. A guard that cannot recognise its own process would
    report every healthy daemon dead and send someone to restart a singleton."""
    monkeypatch.setattr(coordinator, "process_cmdline",
                        lambda pid: "/venv/bin/python /repo/scripts/coordination/"
                                    "session_bus_coordinator.py run")
    alive, why = coordinator.daemon_liveness({"pid": os.getpid()})
    assert alive is True and "coordinator-daemon" in why


def test_daemon_liveness_states_doubt_when_identity_is_unverifiable(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """No /proc is a portability fact, not evidence of death — but the doubt is
    reported rather than dropped."""
    monkeypatch.setattr(coordinator, "process_cmdline", lambda pid: None)
    alive, why = coordinator.daemon_liveness({"pid": os.getpid()})
    assert alive is True and "identity unverifiable" in why


def test_process_cmdline_reads_this_process_and_survives_a_dead_pid(tmp_path: Path) -> None:
    mine = coordinator.process_cmdline(os.getpid())
    if mine is not None:                       # skip where /proc is absent
        assert "python" in mine.lower() or "pytest" in mine.lower()
    assert coordinator.process_cmdline(999_999_999, proc_root=tmp_path) is None


@pytest.mark.parametrize("age_s,tick_s,expected", [
    (0, 45, True), (45, 45, True), (449, 45, True), (451, 45, False),
    (876_736, 45, False),                      # the ten-day heartbeat, judged
    (119, 1, True), (121, 1, False),           # 120s floor, so a fast tick is not jumpy
])
def test_heartbeat_freshness_is_a_verdict_not_a_number(
        age_s: float, tick_s: float, expected: bool) -> None:
    fresh, why = coordinator.heartbeat_freshness(age_s, tick_s)
    assert fresh is expected
    assert f"{age_s:.0f}s old" in why


def test_daemon_verdict_worst_signal_wins(bus_root: Path,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coordinator, "heartbeat_predates_boot", lambda *_a, **_k: False)

    def verdict(pid: int, age_s: float, cmdline: str | None) -> str:
        monkeypatch.setattr(coordinator, "process_cmdline", lambda _p: cmdline)
        path = _hb_file(bus_root, pid, age_s=age_s)
        hb = json.loads(path.read_text(encoding="utf-8"))
        return coordinator.daemon_verdict(hb, path.stat().st_mtime, 45.0)[0]

    daemon = "python session_bus_coordinator.py run"
    assert verdict(os.getpid(), 10, daemon) == "HEALTHY"
    # Alive, correct process, but has not ticked in ten days: wedged is not healthy.
    assert verdict(os.getpid(), 876_736, daemon) == "STALE"
    # Alive, but it is something else entirely.
    assert verdict(os.getpid(), 10, "/sbin/init splash") == "DEAD"
    # Dead pid outranks everything.
    assert verdict(999_999_999, 10, None) == "DEAD"
    # Unusable pid is reported as unknown, never rendered as either.
    monkeypatch.setattr(coordinator, "process_cmdline", lambda _p: daemon)
    path = _hb_file(bus_root, 0, age_s=10)
    hb = json.loads(path.read_text(encoding="utf-8"))
    hb["pid"] = None
    assert coordinator.daemon_verdict(hb, path.stat().st_mtime, 45.0)[0] == "UNKNOWN"


def test_status_leads_with_the_verdict_in_one_word(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """The rendering defect, not just the logic one: the old output differed
    between healthy and ten-days-dead only by a parenthetical several fields into
    a dense line, and for ten days nobody read the difference."""
    _provision(bus_root, *AGENTS)
    monkeypatch.setattr(coordinator, "heartbeat_predates_boot", lambda *_a, **_k: False)
    monkeypatch.setattr(coordinator, "process_cmdline", lambda _p: "/sbin/init splash")
    _hb_file(bus_root, os.getpid(), age_s=876_736)
    (bus_root / "advisory.jsonl").write_text("", encoding="utf-8")
    capsys.readouterr()                        # drop the _provision chatter

    args = coordinator.build_parser().parse_args(
        ["--bus-root", str(bus_root), "status", "--exit-nonzero-if-unhealthy"])
    assert coordinator.cmd_status(args) == 1
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "coordinator-daemon: DEAD"
    assert "recycled" in out and "876736s old" in out
    # Evidence is annotated, never overwritten.
    assert "heartbeat says: state=working" in out


def test_status_reports_healthy_and_exits_zero_for_a_live_daemon(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """The other direction, and the one that matters operationally: a false DEAD
    sends someone to restart a running singleton."""
    _provision(bus_root, *AGENTS)
    monkeypatch.setattr(coordinator, "heartbeat_predates_boot", lambda *_a, **_k: False)
    monkeypatch.setattr(coordinator, "process_cmdline",
                        lambda _p: "python session_bus_coordinator.py run")
    _hb_file(bus_root, os.getpid(), age_s=12)
    (bus_root / "advisory.jsonl").write_text("", encoding="utf-8")
    capsys.readouterr()                        # drop the _provision chatter

    args = coordinator.build_parser().parse_args(
        ["--bus-root", str(bus_root), "status", "--exit-nonzero-if-unhealthy"])
    assert coordinator.cmd_status(args) == 0
    assert capsys.readouterr().out.splitlines()[0] == "coordinator-daemon: HEALTHY"


def test_status_default_exit_code_is_unchanged_for_existing_readers(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Without the flag, status stays exit 0 even when DEAD — the coordinator-agent
    reads it by eye and nothing should start failing because of a new verdict."""
    _provision(bus_root, *AGENTS)
    monkeypatch.setattr(coordinator, "heartbeat_predates_boot", lambda *_a, **_k: False)
    monkeypatch.setattr(coordinator, "process_cmdline", lambda _p: None)
    _hb_file(bus_root, 999_999_999, age_s=876_736)
    (bus_root / "advisory.jsonl").write_text("", encoding="utf-8")
    capsys.readouterr()                        # drop the _provision chatter

    args = coordinator.build_parser().parse_args(["--bus-root", str(bus_root), "status"])
    assert coordinator.cmd_status(args) == 0
    assert capsys.readouterr().out.splitlines()[0] == "coordinator-daemon: DEAD"


def test_status_says_dead_when_there_is_no_heartbeat_at_all(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing heartbeat used to print 'no coordinator-daemon heartbeat' through
    a bare `except Exception`, which also swallowed every other failure."""
    _provision(bus_root, *AGENTS)
    (bus_root / "advisory.jsonl").write_text("", encoding="utf-8")
    capsys.readouterr()                        # drop the _provision chatter
    args = coordinator.build_parser().parse_args(["--bus-root", str(bus_root), "status"])
    assert coordinator.cmd_status(args) == 0
    assert capsys.readouterr().out.splitlines()[0] == "coordinator-daemon: DEAD"


@pytest.mark.parametrize("body,n,expected_total,expected_tail", [
    ("", 5, 0, []),
    ("a\n", 5, 1, ["a"]),
    ("a\nb\nc\n", 2, 3, ["b", "c"]),
    ("a\nb\nc", 2, 2, ["b", "c"]),              # no trailing newline
    ("a\n\n\nb\n", 5, 4, ["a", "b"]),           # blank lines skipped in the tail
])
def test_count_and_tail_matches_a_naive_read(tmp_path: Path, body: str, n: int,
                                             expected_total: int,
                                             expected_tail: list[str]) -> None:
    """C38: status parsed a 1,028 MiB / 2,986,358-row advisory.jsonl into ~6.6 GiB
    of dicts to print five lines. Cheap is only worth having if it is identical."""
    path = tmp_path / "advisory.jsonl"
    path.write_text(body, encoding="utf-8")
    total, tail = _count_and_tail_probe(path, n)
    assert (total, tail) == (expected_total, expected_tail)


def _count_and_tail_probe(path: Path, n: int) -> tuple[int, list[str]]:
    # Exercised at a small block size too, so the backwards walk is actually
    # multi-block in the test rather than always fitting in one read.
    big = coordinator._count_and_tail(path, n)
    small = coordinator._count_and_tail(path, n, block=2)
    assert big == small, f"block size changed the answer: {big} vs {small}"
    return big


def test_count_and_tail_is_bounded_on_a_large_file(tmp_path: Path) -> None:
    path = tmp_path / "advisory.jsonl"
    path.write_text("".join(f'{{"i": {i}}}\n' for i in range(50_000)), encoding="utf-8")
    total, tail = coordinator._count_and_tail(path, 3)
    assert total == 50_000
    assert tail == ['{"i": 49997}', '{"i": 49998}', '{"i": 49999}']
    assert coordinator._count_and_tail(tmp_path / "absent.jsonl", 3) == (0, [])


# ----------------------------------------------------------------------- C39
#
# `relay_tokens` deduped only on "is the gate string already in token-queue.md" and
# had no notion of a gate being SPENT. Both C27 gates sat presented as unchecked
# pending requests while carrying `status: ratified` receipts from 2026-07-29, so
# the operator was being asked to sign what they had already signed — and for the
# E8 gate, whose ratified work then aborted, a re-signature would have read as
# authorisation for a cross-era re-run. Deleting the rows does not stick: the next
# tick re-presents them.

def _c39_token_request(gate: str, sender: str = "alice", tid: str = "t1") -> dict:
    return {"schema_version": bus.MSG_SCHEMA_VERSION, "id": f"msg-20260811T100000Z-1-{sender}",
            "ts": "2026-08-11T10:00:00+00:00", "from": sender, "to": "coordinator-agent",
            "kind": "token-request", "task_id": tid,
            "payload": {"gate_id": gate, "block_ref": "h.md#a",
                        "validated": {"cmd": "true", "dry_run_exit": 0,
                                      "dry_run_evidence": "ok"}}}


def _write_receipt(directory: Path, gate: str, status: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{gate}.json"
    path.write_text(json.dumps({"gate_id": gate, "status": status}), encoding="utf-8")
    return path


def test_spent_receipt_is_found_only_for_a_status_that_means_signed(tmp_path: Path) -> None:
    for status in ("ratified", "spent", "applied", "attested", "granted", "RATIFIED"):
        _write_receipt(tmp_path, "G", status)
        assert coordinator.spent_receipt_for("G", tmp_path) is not None, status
    for status in ("pending", "draft", "requested", "", "revoked"):
        _write_receipt(tmp_path, "G", status)
        assert coordinator.spent_receipt_for("G", tmp_path) is None, status
    assert coordinator.spent_receipt_for("NEVER-FILED", tmp_path) is None
    (tmp_path / "TORN.json").write_text("{not json", encoding="utf-8")
    assert coordinator.spent_receipt_for("TORN", tmp_path) is None


def test_a_spent_gate_is_ANNOTATED_and_never_suppressed(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The load-bearing direction. A relay that silently withholds a gate because it
    believes the gate is spent is the C3/C6/C8 fail-open family aimed at the operator
    path — and a withheld signature request is precisely what C27 was. The block must
    still be presented; the receipt is named beside it and the human decides.
    """
    receipts = tmp_path / "receipts"
    _write_receipt(receipts, "RATIFY-X-20260729", "ratified")
    monkeypatch.setattr(coordinator, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(coordinator, "REPO_ROOT", tmp_path)

    blocks, _ = coordinator.relay_tokens(
        bus_root, {"t1": [_c39_token_request("RATIFY-X-20260729")]}, {}, 14)

    assert len(blocks) == 1, "the gate is still PRESENTED — suppression would re-create C27"
    body = blocks[0]
    assert "- [ ] **RATIFY-X-20260729**" in body, "still an unchecked box the operator can sign"
    assert "already exists" in body and "status: ratified" in body
    assert "receipts/RATIFY-X-20260729.json" in body, "names WHERE, so the claim is checkable"


def test_an_unspent_gate_is_presented_with_no_annotation(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The compliant path. Every ordinary gate must be untouched by this — an
    annotation on a gate that is genuinely pending would train the operator to
    ignore the warning, which is how a real one gets signed twice anyway."""
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    monkeypatch.setattr(coordinator, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(coordinator, "REPO_ROOT", tmp_path)

    blocks, _ = coordinator.relay_tokens(
        bus_root, {"t1": [_c39_token_request("RATIFY-FRESH-20260811")]}, {}, 14)

    assert len(blocks) == 1
    assert "already exists" not in blocks[0] and "⚠" not in blocks[0]


def test_a_gate_already_in_the_queue_gets_a_notice_because_the_block_is_never_rewritten(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both live C27 gates are in this state: presented BEFORE their receipt existed.
    The daemon does not edit token-queue.md, so the annotation can never reach them —
    it has to be said on the bus instead."""
    receipts = tmp_path / "receipts"
    _write_receipt(receipts, "RATIFY-OLD-20260729", "ratified")
    monkeypatch.setattr(coordinator, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(coordinator, "REPO_ROOT", tmp_path)
    tq = bus_root / "tokens" / "token-queue.md"
    tq.parent.mkdir(parents=True, exist_ok=True)
    tq.write_text("### RATIFY-OLD-20260729\n\n- [ ] **RATIFY-OLD-20260729** — old\n",
                  encoding="utf-8")

    blocks, extra = coordinator.relay_tokens(
        bus_root, {"t1": [_c39_token_request("RATIFY-OLD-20260729")]}, {}, 14)

    assert blocks == [], "already presented — the daemon must not duplicate or rewrite it"
    spent = [r for r in extra if r.get("check") == "token-gate-looks-spent"]
    assert len(spent) == 1, extra
    assert spent[0]["gate_id"] == "RATIFY-OLD-20260729"
    assert "SURFACE IT TO THE OPERATOR" in spent[0]["detail"]


def test_backfill_indexes_only_spent_receipts_for_known_gates(
        bus_root: Path, tmp_path: Path) -> None:
    """The one-shot exists so the 55-file / 55.7 MB scan is paid ONCE. Doing it on the
    45s tick would be a fresh instance of C38, which this same module already carries."""
    _provision(bus_root, "alice")
    _append(bus_root / "outbox" / "alice.jsonl", _c39_token_request("RATIFY-REAL-20260729"))
    source, receipts = tmp_path / "operator", tmp_path / "receipts"
    source.mkdir()
    (source / "ratify_real_odd_name.json").write_text(
        json.dumps({"protocol_id": "p", "status": "ratified",
                    "human_attestation": "RATIFY-REAL-20260729"}), encoding="utf-8")
    (source / "still_pending.json").write_text(
        json.dumps({"status": "pending", "gate": "RATIFY-REAL-20260729"}), encoding="utf-8")
    (source / "unrelated.json").write_text(
        json.dumps({"status": "ratified", "about": "SOMETHING-ELSE"}), encoding="utf-8")

    dry = coordinator.backfill_receipts(bus_root, source, receipts, dry_run=True)
    assert [g for g, _, _ in dry] == ["RATIFY-REAL-20260729"]
    assert not receipts.exists(), "--dry-run must write nothing"

    coordinator.backfill_receipts(bus_root, source, receipts)
    found = coordinator.spent_receipt_for("RATIFY-REAL-20260729", receipts)
    assert found is not None and found[1] == "ratified"
    indexed = json.loads((receipts / "RATIFY-REAL-20260729.json").read_text())
    assert indexed["receipt"].endswith("ratify_real_odd_name.json"), \
        "a POINTER, not a copy — an operator signature must not get a second source of truth"


def test_a_spent_gate_notice_is_not_mislabelled_as_never_presented(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The regression C39 could easily have introduced. The inbox-notice loop used to
    consume EVERY advisory row carrying a gate_id and label it
    `token-request-not-presented` — true while `token-prevalidation` was the only such
    row. A "looks already signed" row rendered as "was never presented" would send the
    coordinator to chase a gate that is sitting in the queue, unchecked, right now.
    """
    receipts = tmp_path / "receipts"
    _write_receipt(receipts, "RATIFY-OLD-20260729", "ratified")
    monkeypatch.setattr(coordinator, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(coordinator, "REPO_ROOT", tmp_path)
    _provision(bus_root, "alice", "coordinator-agent")
    _append(bus_root / "outbox" / "alice.jsonl", _c39_token_request("RATIFY-OLD-20260729"))
    # ...and an unvalidated request, which IS the C33 "never presented" case.
    unvalidated = _c39_token_request("RATIFY-UNVALIDATED-20260811")
    unvalidated["payload"]["validated"] = {}
    _append(bus_root / "outbox" / "alice.jsonl", unvalidated)
    tq = bus_root / "tokens" / "token-queue.md"
    tq.parent.mkdir(parents=True, exist_ok=True)
    tq.write_text("- [ ] **RATIFY-OLD-20260729** — presented earlier\n", encoding="utf-8")

    coordinator.relay_token_blocks(bus_root, _load_bus_config(bus_root), 14)

    notices = {(r.get("payload") or {}).get("event"): (r.get("payload") or {})
               for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
               if (r.get("payload") or {}).get("event")}
    assert notices["token-gate-looks-spent"]["gate_id"] == "RATIFY-OLD-20260729"
    assert "IS in token-queue.md" in notices["token-gate-looks-spent"]["action"]
    assert notices["token-request-not-presented"]["gate_id"] == "RATIFY-UNVALIDATED-20260811"
    assert "is NOT in token-queue.md" in notices["token-request-not-presented"]["action"]


def _load_bus_config(bus_root: Path) -> dict:
    return coordinator._load_config(bus_root)


def test_backfill_check_catches_a_signed_gate_with_no_keyed_receipt(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """C39's write side is a CONVENTION, not a mechanism. Measured 2026-08-11: 2 of 24
    `ratify_*.sh` scripts write `receipts/<GATE_ID>.json` at `--attest` time. The other
    22 are each one forgotten copy-paste from re-creating C39 for their gate, and
    nothing would say so — the relay would simply present a signed gate as pending
    again. `--check` catches that whichever script signed it, so the guarantee stops
    depending on the next author remembering 14 lines.
    """
    _provision(bus_root, "alice")
    _append(bus_root / "outbox" / "alice.jsonl", _c39_token_request("RATIFY-SIGNED-20260811"))
    # cmd_backfill_receipts derives its source from REPO_ROOT/artifacts/operator,
    # so the fixture has to sit where the command will actually look.
    source = tmp_path / "artifacts" / "operator"
    receipts = source / "receipts"
    source.mkdir(parents=True)
    (source / "ratify_signed.json").write_text(
        json.dumps({"status": "ratified", "human_attestation": "RATIFY-SIGNED-20260811"}),
        encoding="utf-8")
    monkeypatch.setattr(coordinator, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(coordinator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(coordinator, "_read_epoch", lambda *_a, **_k: 14)

    args = coordinator.build_parser().parse_args(
        ["--bus-root", str(bus_root), "backfill-receipts", "--check"])
    capsys.readouterr()
    assert coordinator.cmd_backfill_receipts(args) == 1, "drift must FAIL, not merely report"
    out = capsys.readouterr().out
    assert "RATIFY-SIGNED-20260811" in out and "no keyed receipt" in out
    assert not receipts.exists(), "--check must not silently repair what it is checking for"

    # Indexed -> clean, exit 0. Without this the check passes by always failing.
    coordinator.backfill_receipts(bus_root, source, receipts)
    capsys.readouterr()
    assert coordinator.cmd_backfill_receipts(args) == 0
    clean = capsys.readouterr().out
    assert "index is current" in clean
    # The success line must state its SCOPE. This check derives its gate set from
    # token-requests in the bus outboxes, so it cannot see a receipt for a gate the
    # bus never carried — `auditor` measured three such gates on 2026-08-11 while
    # this printed a clean verdict. A pass that reads as an all-clear for something
    # it never examined is the fail-open shape C39 itself was.
    assert "gates the bus has seen" in clean
    assert "check_ratifier_receipt_contract.sh" in clean, \
        "name the check that covers the other half, or the gap is invisible again"


# ----------------------------------------------------------------------- C40
#
# When the daemon came back from its 243h outage it relayed 703 messages in one
# burst. mainA and mainB, spawned minutes earlier, drained that backlog and BOTH
# self-assigned `p2-5l-stack-numa-doc-debt` — work auditor had completed on
# 2026-07-29 as ae40ee8b. Nothing was delivered wrongly (that is C28's subject);
# the delivery was correct and the AGE was invisible. `ts` sits inside each JSON
# body and nowhere else, so a session with no history cannot tell this minute's
# assignment from twelve-day-old mail, and both read as instructions.

def _aged_msg(hours: float, *, task: str, sender: str = "bob") -> dict:
    stamp = datetime.now(timezone.utc) - timedelta(hours=hours)
    # A schema-VALID task-assign: the C34 validator refuses a thin one, and a fixture
    # that could not survive `validate_row` would not prove anything about drained rows.
    return {"schema_version": bus.MSG_SCHEMA_VERSION,
            "id": f"msg-20260811T100000Z-{int(hours)}-{sender}", "ts": stamp.isoformat(),
            "from": sender, "to": "alice", "kind": "task-assign", "task_id": task,
            "payload": {"lane": "none", "lease_expires_ts": stamp.isoformat(), "epoch": 14}}


def test_drain_flags_a_stale_relayed_backlog_on_stderr(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The incident, reproduced. The old assignment must be called out; the fresh
    one must not, or the warning is noise and stops being read."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "inbox" / "alice.jsonl",
            _aged_msg(24 * 12 + 3, task="p2-5l-stack-numa-doc-debt", sender="auditor"))
    _append(bus_root / "inbox" / "alice.jsonl", _aged_msg(0, task="live-work"))
    capsys.readouterr()

    assert bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"]) == 0
    err = capsys.readouterr().err

    assert "1 of 2 message(s) are OLDER THAN 24h" in err
    assert "p2-5l-stack-numa-doc-debt" in err and "12.1d old" in err
    assert "live-work" not in err, "a current message must not be flagged"


def test_drain_keeps_stdout_as_clean_jsonl(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The constraint that decided WHERE the signal goes. Stdout is JSONL and
    consumers parse it; the msg schema sets additionalProperties: false, so
    decorating the rows would make anything that re-validates a drained row start
    failing — the exact class of defect C34 was."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "inbox" / "alice.jsonl", _aged_msg(24 * 30, task="ancient"))
    capsys.readouterr()

    bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"])
    out = capsys.readouterr().out

    rows = [json.loads(line) for line in out.splitlines() if line.strip()]
    assert len(rows) == 1
    for row in rows:
        bus.validate_row(bus_root, row, "msg")      # still schema-valid, undecorated


def test_drain_says_nothing_when_everything_is_current(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The compliant path. A banner on every drain trains the reader to skip it,
    which is how the real one gets missed."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "inbox" / "alice.jsonl", _aged_msg(1, task="recent"))
    capsys.readouterr()

    bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"])
    assert "OLDER THAN" not in capsys.readouterr().err


def test_stale_threshold_is_tunable_and_a_broken_ts_is_never_a_verdict(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _provision(bus_root, *AGENTS)
    _append(bus_root / "inbox" / "alice.jsonl", _aged_msg(2, task="two-hours-old"))
    torn = _aged_msg(99, task="unparseable")
    torn["ts"] = "not a timestamp"
    _append(bus_root / "inbox" / "alice.jsonl", torn)
    capsys.readouterr()

    bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice",
              "--stale-after-h", "1"])
    err = capsys.readouterr().err
    assert "two-hours-old" in err
    # A ts it cannot read is reported as neither fresh nor stale — inventing an age
    # would be a claim the record does not support.
    assert "unparseable" not in err
    assert bus.message_age_h({"ts": "not a timestamp"}) is None


def test_triage_marks_a_stale_item_without_touching_the_fence_digest(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The age goes on the `via:` line, NOT inside `body`. The fence's byte count and
    sha256 are computed over `body` so a downstream truncation is provable; decorating
    the body would force the digest to cover text the sender never wrote."""
    _provision(bus_root, *AGENTS)
    old = _aged_msg(24 * 12, task="stale-routed")
    old["needs_routing_to"] = ["alice"]
    old["action_required"] = True
    _append(bus_root / "outbox" / "bob.jsonl", old)
    capsys.readouterr()

    bus.print_triage(bus_root, "alice")
    out = capsys.readouterr().out

    assert "DAYS OLD" in out
    fenced = out.split("--- BEGIN", 1)[1]
    body = fenced.split("\n{", 1)[1]
    body = "{" + body.split("\n--- END", 1)[0]
    assert "DAYS OLD" not in body, "the integrity-covered body must be the sender's bytes"
    assert json.loads(body)["task_id"] == "stale-routed"


# ----------------------------------------------------------------------- C23
#
# Clearing triage took one `corr_id` per item, so a session holding ONE answer for
# N routed items had no compliant way to send it once. BUS_PROTOCOL.md told authors
# to "write it once and reference it" while no mechanism to reference it existed —
# the rule was not performable. Measured 2026-07-29 from a careful main: 3
# byte-identical payloads at 17:41Z, 6 more at 17:44Z differing only in `corr_id`.
# Nine in ten minutes, hours after the discipline rule was codified. Two failures
# in ten minutes is the rule being the defect, not the sender.

def _routed(msg_id: str, task: str, sender: str = "bob") -> dict:
    return {"schema_version": bus.MSG_SCHEMA_VERSION, "id": msg_id,
            "ts": "2026-08-11T10:00:00+00:00", "from": sender, "to": "alice",
            "kind": "finding", "task_id": task,
            "needs_routing_to": ["alice"], "action_required": True}


def test_one_row_can_disposition_many_routed_items(bus_root: Path) -> None:
    """The fix. One answer, one row, N ids cleared."""
    _provision(bus_root, *AGENTS)
    ids = [f"msg-20260811T10000{i}Z-{i}-bob" for i in range(3)]
    for i, mid in enumerate(ids):
        _append(bus_root / "inbox" / "alice.jsonl", _routed(mid, f"task-{i}"))
    assert len(bus.routed_view(bus_root, "alice")["pending"]) == 3

    _append(bus_root / "outbox" / "alice.jsonl", {
        "schema_version": bus.MSG_SCHEMA_VERSION, "id": "msg-20260811T110000Z-9-alice",
        "ts": "2026-08-11T11:00:00+00:00", "from": "alice", "to": "bob", "kind": "ack",
        "corr_ids": ids, "payload": {"disposition": "done", "note": "all three superseded"}})

    view = bus.routed_view(bus_root, "alice")
    assert view["pending"] == [] and view["acked_awaiting_action"] == []


def test_the_scalar_corr_id_still_works_unchanged(bus_root: Path) -> None:
    """Backward compatibility, and the compliant path. This is purely additive: the
    scalar is still right for a genuinely per-item answer, and every row already on
    the bus uses it."""
    _provision(bus_root, *AGENTS)
    _append(bus_root / "inbox" / "alice.jsonl", _routed("msg-20260811T100000Z-1-bob", "t1"))
    _append(bus_root / "inbox" / "alice.jsonl", _routed("msg-20260811T100001Z-2-bob", "t2"))

    _append(bus_root / "outbox" / "alice.jsonl", {
        "schema_version": bus.MSG_SCHEMA_VERSION, "id": "msg-20260811T110000Z-9-alice",
        "ts": "2026-08-11T11:00:00+00:00", "from": "alice", "to": "bob", "kind": "ack",
        "corr_id": "msg-20260811T100000Z-1-bob", "payload": {"disposition": "done"}})

    pending = bus.routed_view(bus_root, "alice")["pending"]
    assert [bus.logical_id(e["row"]) for e in pending] == ["msg-20260811T100001Z-2-bob"], \
        "one scalar disposition must clear exactly one item — no wider, no narrower"


def test_corr_ids_clears_only_what_it_lists(bus_root: Path) -> None:
    """The direction that would make this dangerous. 'Bulk' must not mean 'all'."""
    _provision(bus_root, *AGENTS)
    ids = [f"msg-20260811T10000{i}Z-{i}-bob" for i in range(3)]
    for i, mid in enumerate(ids):
        _append(bus_root / "inbox" / "alice.jsonl", _routed(mid, f"task-{i}"))

    _append(bus_root / "outbox" / "alice.jsonl", {
        "schema_version": bus.MSG_SCHEMA_VERSION, "id": "msg-20260811T110000Z-9-alice",
        "ts": "2026-08-11T11:00:00+00:00", "from": "alice", "to": "bob", "kind": "ack",
        "corr_ids": ids[:2], "payload": {"disposition": "done"}})

    pending = bus.routed_view(bus_root, "alice")["pending"]
    assert [bus.logical_id(e["row"]) for e in pending] == [ids[2]]


def test_a_bare_bulk_ack_is_receipt_not_action(bus_root: Path) -> None:
    """The bulk form must not become a loophole around the rule it sits inside: an
    `action_required` message KEEPS APPEARING after a bare ack, because
    acknowledgement is receipt, not action. Bulk changes the arity, not the semantics.
    """
    _provision(bus_root, *AGENTS)
    ids = [f"msg-20260811T10000{i}Z-{i}-bob" for i in range(2)]
    for i, mid in enumerate(ids):
        _append(bus_root / "inbox" / "alice.jsonl", _routed(mid, f"task-{i}"))

    _append(bus_root / "outbox" / "alice.jsonl", {
        "schema_version": bus.MSG_SCHEMA_VERSION, "id": "msg-20260811T110000Z-9-alice",
        "ts": "2026-08-11T11:00:00+00:00", "from": "alice", "to": "bob", "kind": "ack",
        "corr_ids": ids, "payload": {"seen": True}})          # no disposition

    view = bus.routed_view(bus_root, "alice")
    assert view["pending"] == []
    assert len(view["acked_awaiting_action"]) == 2, "bare acks are receipt, in bulk too"


def test_corr_ids_is_schema_valid_and_typed(bus_root: Path) -> None:
    base = {"schema_version": bus.MSG_SCHEMA_VERSION, "id": "msg-20260811T110000Z-1-alice",
            "ts": "2026-08-11T11:00:00+00:00", "from": "alice", "to": "bob", "kind": "ack"}
    bus.validate_row(LIVE_BUS_ROOT, {**base, "corr_ids": ["a", "b"]}, "msg")
    for bad in ([], ["a", "a"], [""], [1], "not-a-list"):
        with pytest.raises(bus.BusError):
            bus.validate_row(LIVE_BUS_ROOT, {**base, "corr_ids": bad}, "msg")


def test_the_triage_trailer_advertises_the_bulk_form_when_it_is_needed(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The previous instruction implied one row per item was the only way, which is
    how someone following it correctly sent nine identical payloads in ten minutes."""
    _provision(bus_root, *AGENTS)
    for i in range(2):
        _append(bus_root / "inbox" / "alice.jsonl",
                _routed(f"msg-20260811T10000{i}Z-{i}-bob", f"task-{i}"))
    capsys.readouterr()
    bus.print_triage(bus_root, "alice")
    assert "corr_ids:" in capsys.readouterr().out

    # ...and stays quiet for a single item, where the bulk form is just noise.
    _provision(bus_root, "coordinator-agent")
    _append(bus_root / "inbox" / "coordinator-agent.jsonl",
            {**_routed("msg-20260811T100009Z-9-bob", "solo"), "to": "coordinator-agent",
             "needs_routing_to": ["coordinator-agent"]})
    capsys.readouterr()
    bus.print_triage(bus_root, "coordinator-agent")
    out = capsys.readouterr().out
    assert "1 item(s)" in out and "corr_ids:" not in out


# ----------------------------------------------------------------- C28 / C38
#
# Two defects that turned out to be one defect: both asked "what has this daemon
# already done" and both answered by re-reading the thing it had acted on.
#   C28 — relay idempotency was `relayed_src` checked against the RECIPIENT'S
#     INBOX, so an absent or truncated destination read as "never relayed". The
#     2026-07-29 roster rename (`git mv inbox/<old> inbox/<new>`) made the running
#     daemon re-deliver its entire relay history into recreated old-id inboxes.
#     Generally: any operation that moves, truncates, rotates or restores an inbox.
#   C38 — `already_flagged` re-read advisory.jsonl in full every 45s. Measured:
#     1,028 MiB / 3,001,866 rows parsed per tick to rebuild a set of 637 pairs.

def _relayed_into(root: Path, agent: str, src: str) -> None:
    _append(root / "inbox" / f"{agent}.jsonl", {
        "schema_version": bus.MSG_SCHEMA_VERSION, "id": f"msg-20260811T120000Z-9-{agent}",
        "ts": "2026-08-11T12:00:00+00:00", "from": "bob", "to": agent, "kind": "status",
        "relayed_src": src})


def test_moving_an_inbox_no_longer_re_floods_it(bus_root: Path) -> None:
    """C28's exact trigger, reproduced. The rename is not the only one — this is
    every move, truncate, rotate or restore."""
    _provision(bus_root, "alice")
    _relayed_into(bus_root, "alice", "msg-20260728T090000Z-1-bob")
    (bus_root / "advisory.jsonl").write_text("", encoding="utf-8")

    state = coordinator.load_relay_state(bus_root, ["alice"])
    assert state["bootstrapped"] is True
    assert state["delivered"]["alice"] == {"msg-20260728T090000Z-1-bob"}
    coordinator.save_relay_state(bus_root, state)

    # The destructive operation: the inbox is moved away and recreated empty.
    (bus_root / "inbox" / "alice.jsonl").write_text("", encoding="utf-8")

    after = coordinator.load_relay_state(bus_root, ["alice"])
    assert after["bootstrapped"] is False
    assert after["delivered"]["alice"] == {"msg-20260728T090000Z-1-bob"}, \
        "the ledger, not the destination file, is what remembers the delivery"


def test_a_missing_ledger_degrades_to_the_old_behaviour_not_to_a_re_flood(
        bus_root: Path) -> None:
    """The fail-safe direction, and the reason bootstrap reads the inboxes. A lost
    or corrupt ledger must fall back to reading what is ACTUALLY THERE — today's
    semantics — rather than to an empty set, which would re-deliver everything."""
    _provision(bus_root, "alice")
    _relayed_into(bus_root, "alice", "msg-20260728T090000Z-1-bob")
    (bus_root / "advisory.jsonl").write_text("", encoding="utf-8")

    for corrupt in ("", "{not json", json.dumps({"schema_version": "session_bus.relay_state.v99"})):
        (bus_root / "relay_state.json").write_text(corrupt, encoding="utf-8")
        state = coordinator.load_relay_state(bus_root, ["alice"])
        assert state["bootstrapped"] is True, corrupt[:20]
        assert state["delivered"]["alice"] == {"msg-20260728T090000Z-1-bob"}, \
            "a torn ledger must never read as 'nothing was ever delivered'"


def test_flagged_pairs_survive_without_re_reading_the_advisory(bus_root: Path) -> None:
    """C38. Once the ledger exists the advisory is not read at all — which is the
    whole point, since it is 1,028 MiB and the answer is 637 pairs."""
    _provision(bus_root, "alice")
    _append(bus_root / "advisory.jsonl",
            {"relayed_src": "msg-1", "unreachable": "schema-invalid"})
    _append(bus_root / "advisory.jsonl",
            {"relayed_src": "msg-2", "unreachable": "handler:relay_tokens"})

    state = coordinator.load_relay_state(bus_root, ["alice"])
    assert state["flagged"] == {("msg-1", "schema-invalid"), ("msg-2", "handler:relay_tokens")}
    coordinator.save_relay_state(bus_root, state)

    # Truncating the advisory must not resurrect the flags — they are the daemon's
    # own record now, in a place a rotation cannot erase.
    (bus_root / "advisory.jsonl").write_text("", encoding="utf-8")
    after = coordinator.load_relay_state(bus_root, ["alice"])
    assert after["flagged"] == state["flagged"]
    assert after["bootstrapped"] is False


def test_relay_persists_the_ledger_and_stays_idempotent_across_ticks(
        bus_root: Path) -> None:
    """End to end, and the compliant path: a second tick over the same outbox must
    deliver NOTHING new — that is the property C28 exists to protect, and 'never
    re-flood' is trivially satisfied by never delivering at all."""
    _provision(bus_root, "alice", "bob", "coordinator-agent")
    _append(bus_root / "outbox" / "bob.jsonl", {
        "schema_version": bus.MSG_SCHEMA_VERSION, "id": "msg-20260811T120000Z-1-bob",
        "ts": "2026-08-11T12:00:00+00:00", "from": "bob", "to": "alice", "kind": "status",
        "payload": {"detail": "hello"}})
    config = coordinator._load_config(bus_root)
    roster = [r for r in (config.get("roster") or []) if isinstance(r, dict)]

    coordinator.relay_outbox_messages(bus_root, roster, 14, config)
    first = _read_jsonl(bus_root / "inbox" / "alice.jsonl")
    assert len(first) == 1 and first[0]["relayed_src"] == "msg-20260811T120000Z-1-bob", \
        "the message must actually be delivered — this is the direction that matters"
    assert (bus_root / "relay_state.json").exists()

    coordinator.relay_outbox_messages(bus_root, roster, 14, config)
    assert _read_jsonl(bus_root / "inbox" / "alice.jsonl") == first, "second tick must be a no-op"


def _daemon_hb(root: Path, pid: int, age_s: float) -> None:
    path = root / "heartbeats" / f"{bus.COORDINATOR_DAEMON}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"agent": bus.COORDINATOR_DAEMON, "pid": pid,
                                "state": "working", "epoch": 14}), encoding="utf-8")
    stamp = time.time() - age_s
    os.utime(path, (stamp, stamp))


def test_drain_warns_every_agent_when_the_daemon_is_not_serving(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """C37's second half. The identity and freshness checks fixed the REPORT, but the
    report was pull-only and for 243 hours nobody pulled — and the supervisor that
    would have noticed was dead too. Every agent runs `drain` at every task boundary,
    so the check runs there: the outage becomes visible within ONE boundary.
    """
    _provision(bus_root, *AGENTS)
    _daemon_hb(bus_root, 999_999_999, age_s=10)          # dead pid
    capsys.readouterr()

    bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"])
    err = capsys.readouterr().err
    assert "COORDINATOR-DAEMON IS NOT SERVING" in err
    assert "does not exist" in err


def test_the_warning_fires_on_an_EMPTY_drain_too(
        bus_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The case that matters most, and the one an early return would have missed:
    '(no new messages)' is exactly what a dead relay looks like from inside an
    agent — an all-clear that is really a silence."""
    _provision(bus_root, *AGENTS)
    _daemon_hb(bus_root, 999_999_999, age_s=10)
    capsys.readouterr()

    bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"])
    captured = capsys.readouterr()
    assert "(no new messages for alice)" in captured.out
    assert "COORDINATOR-DAEMON IS NOT SERVING" in captured.err


def test_a_wedged_daemon_holding_its_pid_is_not_serving(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Alive is not the same as serving. A wedged daemon keeps its pid and stops
    ticking, which is indistinguishable from healthy if you only check the pid."""
    _provision(bus_root, *AGENTS)
    monkeypatch.setattr(bus, "daemon_argv", lambda _p: "python session_bus_coordinator.py run")
    _daemon_hb(bus_root, os.getpid(), age_s=876_736)     # ten days
    ok, why = bus.daemon_is_serving(bus_root)
    assert ok is False and "WEDGED" in why


def test_a_healthy_daemon_is_silent(bus_root: Path, monkeypatch: pytest.MonkeyPatch,
                                    capsys: pytest.CaptureFixture[str]) -> None:
    """The compliant path, and the one that decides whether the warning gets read at
    all: a banner on every drain trains the fleet to skip it."""
    _provision(bus_root, *AGENTS)
    monkeypatch.setattr(bus, "daemon_argv", lambda _p: "python session_bus_coordinator.py run")
    _daemon_hb(bus_root, os.getpid(), age_s=12)
    capsys.readouterr()

    bus.main(["--bus-root", str(bus_root), "drain", "--agent", "alice"])
    assert "NOT SERVING" not in capsys.readouterr().err
    ok, _ = bus.daemon_is_serving(bus_root)
    assert ok is True


def test_a_recycled_pid_is_not_a_serving_daemon(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent-side copy must carry the identity check too, or it reports every
    recycled pid as a healthy bus."""
    _provision(bus_root, *AGENTS)
    _daemon_hb(bus_root, 1, age_s=10)                    # pid 1 is /sbin/init
    ok, why = bus.daemon_is_serving(bus_root)
    if Path("/proc/1/cmdline").exists():
        assert ok is False and "recycled" in why


def test_an_always_refused_nudge_eventually_escalates(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R1's second half, and the fail-open that hid the first. `last_nudge_ts` and
    `last_nudge_sig` are written ONLY on rc == 0, and the stuck-refusing-drain
    escalation is gated on `last_nudge_sig` — so an agent whose nudges are ALWAYS
    refused could never escalate, however long it stayed unreachable. The one path
    that reported it was an advisory row, and advisory.jsonl has no reader. Measured
    2026-08-11: 1,903 refusals accumulated while the whole fleet sat unreachable and
    nothing escalated. That is the C3/C6/C8 shape inside the escalation path itself.
    """
    _provision(bus_root, "alice", "coordinator-agent")
    _append(bus_root / "inbox" / "alice.jsonl", {
        "schema_version": bus.MSG_SCHEMA_VERSION, "id": "msg-20260811T120000Z-1-bob",
        "ts": "2026-08-11T12:00:00+00:00", "from": "bob", "to": "alice", "kind": "status",
        "payload": {"x": 1}})
    _heartbeat(bus_root, "alice", "idle")
    roster = [{"id": "alice", "role": "main", "endpoint": "tmux:agent:alice"},
              {"id": "coordinator-agent", "role": "coordinator",
               "endpoint": "tmux:agent:coordinator-agent"}]
    monkeypatch.setattr(coordinator, "_STUCK_ESCALATION_INTERVAL_S", 1.0)
    monkeypatch.setattr(coordinator, "_STUCK_REFUSAL_RETRY_S", 0.0)

    refused = lambda *_a, **_k: (2, "REFUSING: heartbeat is 40000s stale (> 900s)")
    # pane_fn -> (active, detail); False means "not generating", so proceed.
    alive = lambda *_a, **_k: (False, "pane quiet 1200s, settled at its prompt")

    # The clock must ADVANCE between ticks: escalation is gated on how long the
    # agent has been unreachable, which is the property under test.
    base = time.time() + 7200
    seen = []
    for tick in range(3):
        seen += coordinator.resolve_stuck_agents(
            bus_root, roster, 14, nudge_fn=refused, pane_fn=alive,
            now=base + tick * 60)

    kinds = [r.get("kind") for r in seen]
    assert "stuck-nudge-refused" in kinds, "the refusal itself is still recorded"
    assert "stuck-unreachable" in kinds, \
        "a guard refusing forever must ESCALATE — refusal is not the system working"

    notice = [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
              if (r.get("payload") or {}).get("event") == "stuck-unreachable"]
    assert notice, "advisory.jsonl has no reader — the escalation must reach an inbox"
    assert notice[0]["payload"]["agent"] == "alice"
    assert "R1 deadlock" in notice[0]["payload"]["action"]


def test_a_successful_nudge_does_not_escalate(
        bus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The compliant path. Escalating on a nudge that worked would train the
    coordinator to ignore the notice, which is how the real one gets missed."""
    _provision(bus_root, "alice", "coordinator-agent")
    _append(bus_root / "inbox" / "alice.jsonl", {
        "schema_version": bus.MSG_SCHEMA_VERSION, "id": "msg-20260811T120000Z-1-bob",
        "ts": "2026-08-11T12:00:00+00:00", "from": "bob", "to": "alice", "kind": "status",
        "payload": {"x": 1}})
    _heartbeat(bus_root, "alice", "idle")
    roster = [{"id": "alice", "role": "main", "endpoint": "tmux:agent:alice"},
              {"id": "coordinator-agent", "role": "coordinator",
               "endpoint": "tmux:agent:coordinator-agent"}]

    seen = coordinator.resolve_stuck_agents(
        bus_root, roster, 14, nudge_fn=lambda *_a, **_k: (0, "sent"),
        pane_fn=lambda *_a, **_k: (False, "pane quiet, settled at its prompt"),
        now=time.time() + 7200)

    assert "stuck-nudged" in [r.get("kind") for r in seen]
    assert "stuck-unreachable" not in [r.get("kind") for r in seen]
    assert not [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
                if (r.get("payload") or {}).get("event") == "stuck-unreachable"]


# ------------------------------------------------------------------------- R2
#
# F1: a day of commits with nothing written to progress/<YYYY-MM>/<today>.md is
# invisible to the operator — the dashboard counts checkbox state, so
# committed-but-unlogged work reads as a day where nothing happened. Measured
# 2026-08-11: open went 1283 -> 1293 while done went 2274 -> 2294 and the board
# looked flat. The report specifying this flagged it as the proposal MOST at risk
# of fail-open, with three silent-pass paths, and said build it fail-closed or not
# at all. These tests are that requirement.

def _git_repo(tmp_path: Path, commit_iso: str) -> Path:
    import subprocess as sp
    root = tmp_path / "repo"
    (root / "progress").mkdir(parents=True)
    sp.run(["git", "init", "-q", str(root)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        sp.run(["git", "-C", str(root), "config", k, v], check=True)
    (root / "f.txt").write_text("x", encoding="utf-8")
    sp.run(["git", "-C", str(root), "add", "f.txt"], check=True)
    sp.run(["git", "-C", str(root), "commit", "-q", "-m", "c"], check=True,
           env={**os.environ, "GIT_AUTHOR_DATE": commit_iso, "GIT_COMMITTER_DATE": commit_iso})
    return root


def test_r2_fails_closed_when_git_cannot_be_read(bus_root: Path, tmp_path: Path) -> None:
    """Silent-pass path 1. An unreadable git is NOT 'no commits' — reporting it as
    clean is precisely the fail-open this was built to avoid."""
    rows = coordinator.progress_log_currency(bus_root, 14, repo_root=tmp_path / "not-a-repo")
    assert len(rows) == 1
    assert rows[0]["check"] == "progress-log-check-skipped"
    assert rows[0]["kind"] == "defect", "must be a defect kind — that is what reaches the operator"
    assert "not a clean one" in rows[0]["detail"]


def test_r2_fails_closed_when_the_progress_directory_is_missing(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Silent-pass path 2. A missing directory is a LOUDER defect than a stale file,
    not a quieter one."""
    now = time.time()
    root = _git_repo(tmp_path, datetime.fromtimestamp(now, timezone.utc).isoformat())
    monkeypatch.setattr(coordinator, "_PROGRESS_DIR", tmp_path / "absent")
    rows = coordinator.progress_log_currency(bus_root, 14, now=now, repo_root=root)
    assert len(rows) == 1 and rows[0]["check"] == "progress-log-stale"
    assert "does not exist" in rows[0]["detail"]


def test_r2_fails_closed_when_todays_file_is_missing(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Silent-pass path 3, and the one most likely to be written wrong: an absent
    file is the DEFECT, never 'nothing due'."""
    now = time.time()
    root = _git_repo(tmp_path, datetime.fromtimestamp(now, timezone.utc).isoformat())
    monkeypatch.setattr(coordinator, "_PROGRESS_DIR", root / "progress")
    rows = coordinator.progress_log_currency(bus_root, 14, now=now, repo_root=root)
    assert len(rows) == 1 and rows[0]["check"] == "progress-log-stale"
    assert "does not exist" in rows[0]["detail"] and "not\n" not in rows[0]["detail"]


def test_r2_flags_commits_that_landed_after_the_last_entry(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The defect itself: work landing while the log stands still."""
    now = time.time()
    root = _git_repo(tmp_path, datetime.fromtimestamp(now, timezone.utc).isoformat())
    monkeypatch.setattr(coordinator, "_PROGRESS_DIR", root / "progress")
    stamp = datetime.fromtimestamp(now, timezone.utc)
    entry = root / "progress" / f"{stamp:%Y-%m}" / f"{stamp:%Y-%m-%d}.md"
    entry.parent.mkdir(parents=True)
    entry.write_text("# today\n", encoding="utf-8")
    old = now - 6 * 3600
    os.utime(entry, (old, old))

    rows = coordinator.progress_log_currency(bus_root, 14, now=now, repo_root=root)
    assert len(rows) == 1 and rows[0]["check"] == "progress-log-stale"
    assert rows[0]["stale_h"] >= 4.0
    assert "reads to the operator as a day where nothing happened" in rows[0]["detail"]


def test_r2_is_silent_when_the_log_is_current(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The compliant path. A check that fires on a well-run day trains the reader to
    ignore it, which is how the real one gets missed."""
    now = time.time()
    root = _git_repo(tmp_path, datetime.fromtimestamp(now - 3600, timezone.utc).isoformat())
    monkeypatch.setattr(coordinator, "_PROGRESS_DIR", root / "progress")
    stamp = datetime.fromtimestamp(now, timezone.utc)
    entry = root / "progress" / f"{stamp:%Y-%m}" / f"{stamp:%Y-%m-%d}.md"
    entry.parent.mkdir(parents=True)
    entry.write_text("# today\n", encoding="utf-8")     # written now, after the commit

    assert coordinator.progress_log_currency(bus_root, 14, now=now, repo_root=root) == []


def test_r2_is_silent_on_a_day_with_no_commits(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The ONE clean exit, and it is keyed on POSITIVE evidence — a commit timestamp
    older than today — never on something being unreadable. Nothing is owed for a day
    nobody worked."""
    now = time.time()
    root = _git_repo(tmp_path, datetime.fromtimestamp(now - 4 * 86400, timezone.utc).isoformat())
    monkeypatch.setattr(coordinator, "_PROGRESS_DIR", root / "progress")
    assert coordinator.progress_log_currency(bus_root, 14, now=now, repo_root=root) == []


def test_r2_never_writes_the_thing_it_checks(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A checker that fixes what it checks for cannot be trusted to report — the rule
    --audit-guards and backfill-receipts --check already follow."""
    now = time.time()
    root = _git_repo(tmp_path, datetime.fromtimestamp(now, timezone.utc).isoformat())
    monkeypatch.setattr(coordinator, "_PROGRESS_DIR", root / "progress")
    before = sorted(p.name for p in (root / "progress").rglob("*"))
    coordinator.progress_log_currency(bus_root, 14, now=now, repo_root=root)
    assert sorted(p.name for p in (root / "progress").rglob("*")) == before


def test_r2_defect_kind_reaches_the_operator_path_without_new_code() -> None:
    """The reason this is a `defect` and not a bespoke kind: `defect` is already in
    _OPERATOR_ITEM_KINDS, so an unpresented one reaches token-queue.md on the C20
    timer with no new escalation code."""
    assert "defect" in coordinator._OPERATOR_ITEM_KINDS


def test_r2_delivers_into_an_inbox_not_only_advisory(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R2 CORRECTION, same day, caught by the operator. This first shipped emitting
    the advisory row only, reasoning that `defect` is in _OPERATOR_ITEM_KINDS and
    would reach token-queue.md on the C20 timer for free. Wrong: `_is_operator_item`
    is applied to OUTBOX and INBOX rows, never advisory rows — so the notice went to
    advisory.jsonl and stopped. That is the C33 shape, quoted twice the same day
    while building this.
    """
    _provision(bus_root, "alice", "coordinator-agent")
    now = time.time()
    root = _git_repo(tmp_path, datetime.fromtimestamp(now, timezone.utc).isoformat())
    monkeypatch.setattr(coordinator, "_PROGRESS_DIR", root / "progress")

    rows = coordinator.progress_log_currency(bus_root, 14, now=now, repo_root=root)
    assert rows and rows[0]["check"] == "progress-log-stale"

    notices = [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
               if (r.get("payload") or {}).get("event") == "progress-log-stale"]
    assert notices, "the defect must reach a queue somebody drains"
    assert "invisible to the operator" in notices[0]["payload"]["action"]


def test_r2_does_not_re_deliver_the_same_day_every_tick(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 45s tick must not turn a true finding into the advisory flood C34 measured.
    Deduped against the coordinator's own inbox — the notice's durable trace."""
    _provision(bus_root, "alice", "coordinator-agent")
    now = time.time()
    root = _git_repo(tmp_path, datetime.fromtimestamp(now, timezone.utc).isoformat())
    monkeypatch.setattr(coordinator, "_PROGRESS_DIR", root / "progress")

    for _ in range(5):
        coordinator.progress_log_currency(bus_root, 14, now=now, repo_root=root)

    notices = [r for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
               if (r.get("payload") or {}).get("event") == "progress-log-stale"]
    assert len(notices) == 1, f"one notice per day, got {len(notices)}"


def test_r2_delivery_failure_never_breaks_the_tick(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reporting must not be able to take the daemon down. A check that can break the
    tick is worse than a missed notice."""
    now = time.time()
    root = _git_repo(tmp_path, datetime.fromtimestamp(now, timezone.utc).isoformat())
    monkeypatch.setattr(coordinator, "_PROGRESS_DIR", root / "progress")
    monkeypatch.setattr(coordinator, "_append_inbox",
                        lambda *_a, **_k: (_ for _ in ()).throw(OSError("disk full")))

    rows = coordinator.progress_log_currency(bus_root, 14, now=now, repo_root=root)
    assert rows and rows[0]["check"] == "progress-log-stale", \
        "the advisory row still comes back even when delivery fails"


def test_advisory_rotates_once_it_passes_the_bound(bus_root: Path) -> None:
    """advisory.jsonl reached 1,041 MiB / 3,003,126 rows with nothing rotating it."""
    live = bus_root / "advisory.jsonl"
    live.write_text("x" * 2048, encoding="utf-8")

    assert coordinator.rotate_advisory(bus_root, 14, max_bytes=10_000) == [], \
        "under the bound is a no-op"

    rows = coordinator.rotate_advisory(bus_root, 14, max_bytes=1024)
    assert rows and rows[0]["kind"] == "advisory-rotated"
    assert (bus_root / "advisory_1.jsonl").exists(), "renamed, never truncated"
    assert live.exists() and live.stat().st_size == 0, "a fresh live file takes over"

    (bus_root / "advisory.jsonl").write_text("y" * 2048, encoding="utf-8")
    coordinator.rotate_advisory(bus_root, 14, max_bytes=1024)
    assert (bus_root / "advisory_2.jsonl").exists(), "shards number upward"


def test_bootstrap_reads_every_shard_or_rotation_re_floods(bus_root: Path) -> None:
    """The hazard rotation introduces, and the reason C28 had to land first. A
    bootstrap that read only the live file would lose every flag raised before the
    last rotation and re-flag all of them — turning housekeeping into the C34 flood
    it was meant to prevent."""
    _provision(bus_root, "alice")
    _append(bus_root / "advisory.jsonl", {"relayed_src": "old-1", "unreachable": "schema-invalid"})
    coordinator.rotate_advisory(bus_root, 14, max_bytes=1)
    _append(bus_root / "advisory.jsonl", {"relayed_src": "new-1", "unreachable": "schema-invalid"})

    state = coordinator.load_relay_state(bus_root, ["alice"])
    assert state["bootstrapped"] is True
    assert ("old-1", "schema-invalid") in state["flagged"], \
        "a flag in a ROTATED shard must survive — otherwise it is re-flagged forever"
    assert ("new-1", "schema-invalid") in state["flagged"]


def test_rotation_failure_never_stops_the_tick(bus_root: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    """Housekeeping must not be able to take delivery down."""
    (bus_root / "advisory.jsonl").write_text("x" * 4096, encoding="utf-8")
    monkeypatch.setattr(Path, "rename",
                        lambda *_a, **_k: (_ for _ in ()).throw(OSError("read-only fs")))
    rows = coordinator.rotate_advisory(bus_root, 14, max_bytes=1024)
    assert rows and rows[0]["kind"] == "advisory-rotation-failed"


def test_c39_advice_never_instructs_an_agent_across_the_trust_boundary(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """C39-advice, 2026-08-11, raised by `coordinator-agent` against my own tooling.

    The notice used to say "verify the receipt, then tick or remove the block
    yourself". That instructs the ONE action the coordinator is specifically
    forbidden to take: token-queue.md's header reserves the checkbox to the operator
    ("Nobody but the operator touches a checkbox") and agents/coordinator-agent.md
    says "Never tick a checkbox". A coordinator following its own tooling would have
    breached the human-only boundary — and the advice is persuasive precisely
    because it comes from the delivery plane. Tooling that contradicts the trust
    boundary is worse than tooling with a wrong number in it.

    Removing is not the safe alternative either: the block plus its unticked box is
    the only in-file record that a gate was PRESENTED; the receipt records only the
    signing.

    Asserted against the PRODUCED NOTICE, not the module source: the source
    legitimately quotes the old wording to explain the defect, and a guard that
    forbids its own documentation is the guard-forbids-its-own-idiom trap.
    """
    _provision(bus_root, "alice", "coordinator-agent")
    receipts = tmp_path / "receipts"
    _write_receipt(receipts, "RATIFY-OLD-20260729", "ratified")
    monkeypatch.setattr(coordinator, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(coordinator, "REPO_ROOT", tmp_path)
    tq = bus_root / "tokens" / "token-queue.md"
    tq.parent.mkdir(parents=True, exist_ok=True)
    tq.write_text("- [ ] **RATIFY-OLD-20260729** — presented earlier\n", encoding="utf-8")
    _append(bus_root / "outbox" / "alice.jsonl", _c39_token_request("RATIFY-OLD-20260729"))

    _, extra = coordinator.relay_tokens(
        bus_root, {"t1": [_c39_token_request("RATIFY-OLD-20260729")]}, {}, 14)
    coordinator.relay_token_blocks(bus_root, coordinator._load_config(bus_root), 14)

    texts = [str(r.get("detail", "")) for r in extra if r.get("check") == "token-gate-looks-spent"]
    texts += [str((r.get("payload") or {}).get("action", ""))
              for r in _read_jsonl(bus_root / "inbox" / "coordinator-agent.jsonl")
              if (r.get("payload") or {}).get("event") == "token-gate-looks-spent"]
    assert texts, "the notice must exist at all"
    for text in texts:
        low = text.lower()
        # POLARITY, not substring. The corrected text legitimately says "do NOT tick
        # or remove", so a bare substring check fails on the fix itself — the same
        # trap as a guard forbidding its own documentation. What must hold is that
        # every mention of ticking is a prohibition.
        if "tick" in low:
            assert "do not tick" in low, f"mentions ticking without forbidding it: {text[:140]}"
        assert "yourself" not in low, f"reads as an instruction to act: {text[:140]}"
        # ...and it must still name the action that IS permitted. "Do not tick" with
        # no alternative is how a real signal gets ignored.
        assert "surface it to the operator" in low, f"no permitted action named: {text[:120]}"


# ------------------------------------------------------- C39 deferred half
#
# The C39 notice reached coordinator-agent's inbox, which is right, but left the
# OPERATOR-FACING file misleading on its own terms: six of seven unchecked gates in
# token-queue.md carried `status: ratified` receipts and nothing in the file said
# so. A reader of that file alone sees six pending signature requests that are not
# pending.

def _queue_with(root: Path, *gates: str) -> Path:
    tq = root / "tokens" / "token-queue.md"
    tq.parent.mkdir(parents=True, exist_ok=True)
    tq.write_text("# Operator token queue\n\n" +
                  "".join(f"### {g}\n\n- [ ] **{g}** — requested\n\n" for g in gates),
                  encoding="utf-8")
    return tq


def test_spent_gate_notice_names_signed_gates_without_touching_a_checkbox(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """APPEND-ONLY, deliberately narrower than what was proposed. Annotating each
    block in place means the daemon editing operator-facing content it wrote
    earlier, right next to checkboxes only the operator may touch. Appending
    achieves the same thing for a reader and cannot corrupt an existing block."""
    receipts = tmp_path / "receipts"
    _write_receipt(receipts, "RATIFY-SIGNED-1", "ratified")
    monkeypatch.setattr(coordinator, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(coordinator, "REPO_ROOT", tmp_path)
    tq = _queue_with(bus_root, "RATIFY-SIGNED-1", "RATIFY-GENUINELY-PENDING")
    before = tq.read_text(encoding="utf-8")

    rows = coordinator.note_spent_gates_in_queue(bus_root, 14)

    assert rows and rows[0]["kind"] == "spent-gate-notice"
    assert rows[0]["gates"] == ["RATIFY-SIGNED-1"]
    after = tq.read_text(encoding="utf-8")
    assert after.startswith(before), "append-only: existing content is byte-identical"
    assert "RATIFY-SIGNED-1" in after.replace(before, "")
    assert "RATIFY-GENUINELY-PENDING" not in after.replace(before, ""), \
        "an unsigned gate must not be named as signed"
    # The whole point: it states evidence, it never decides.
    assert "- [x]" not in after, "the daemon must never write a ticked box"
    assert after.count("- [ ] **RATIFY-SIGNED-1**") == 1, "no checkbox was altered"


def test_spent_gate_notice_does_not_repeat_every_tick(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 45s tick appending the same notice forever is the advisory flood C34
    measured, aimed at the operator's own file."""
    receipts = tmp_path / "receipts"
    _write_receipt(receipts, "RATIFY-SIGNED-1", "ratified")
    monkeypatch.setattr(coordinator, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(coordinator, "REPO_ROOT", tmp_path)
    tq = _queue_with(bus_root, "RATIFY-SIGNED-1")

    first = coordinator.note_spent_gates_in_queue(bus_root, 14)
    for _ in range(4):
        assert coordinator.note_spent_gates_in_queue(bus_root, 14) == []
    assert first and tq.read_text(encoding="utf-8").count("Daemon notice") == 1


def test_a_newly_spent_gate_gets_a_fresh_corrected_notice(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dedupe is on the gate SET, not on 'a notice exists'. Keying on mere presence
    would leave a later-signed gate silently unmentioned — quiet is not the same as
    correct."""
    receipts = tmp_path / "receipts"
    _write_receipt(receipts, "RATIFY-SIGNED-1", "ratified")
    monkeypatch.setattr(coordinator, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(coordinator, "REPO_ROOT", tmp_path)
    tq = _queue_with(bus_root, "RATIFY-SIGNED-1", "RATIFY-SIGNED-2")
    coordinator.note_spent_gates_in_queue(bus_root, 14)

    _write_receipt(receipts, "RATIFY-SIGNED-2", "ratified")     # signed later
    rows = coordinator.note_spent_gates_in_queue(bus_root, 14)
    assert rows and rows[0]["gates"] == ["RATIFY-SIGNED-1", "RATIFY-SIGNED-2"]
    assert tq.read_text(encoding="utf-8").count("Daemon notice") == 2


def test_no_notice_when_nothing_is_spent(
        bus_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The compliant path. A file that gains a daemon block on an ordinary day
    trains the operator to skim past it."""
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    monkeypatch.setattr(coordinator, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(coordinator, "REPO_ROOT", tmp_path)
    tq = _queue_with(bus_root, "RATIFY-GENUINELY-PENDING")
    before = tq.read_text(encoding="utf-8")

    assert coordinator.note_spent_gates_in_queue(bus_root, 14) == []
    assert tq.read_text(encoding="utf-8") == before


# --- C44: the token relay is withdrawal-blind (mainD, 2026-08-12) -------------
# Sibling of C39's receipt-blindness, found the same way: an escalation chasing
# the operator about a gate that was not live. Helper name kept distinct from
# _queue_with / _routed / _aged_msg — an appended helper that shadows an existing
# one silently breaks unrelated passing tests.

def _outbox_msgs(root: Path, agent: str, *msgs: dict) -> None:
    ob = root / "outbox"
    ob.mkdir(parents=True, exist_ok=True)
    with (ob / f"{agent}.jsonl").open("a", encoding="utf-8") as fh:
        for m in msgs:
            fh.write(json.dumps(m) + "\n")


def _request(gate: str, task: str, ts: str, agent: str = "mainD") -> dict:
    return {"id": f"req-{gate}", "from": agent, "kind": "token-request", "task_id": task,
            "ts": ts, "payload": {"gate_id": gate}}


def _complete(task: str, ts: str, agent: str = "mainD") -> dict:
    return {"id": f"done-{task}-{ts}", "from": agent, "kind": "task-complete",
            "task_id": task, "ts": ts, "payload": {"disposition": "done"}}


def test_an_explicitly_withdrawn_gate_is_named_authoritatively(bus_root: Path) -> None:
    """Tier 1: the requester said so, keyed to the gate id."""
    tq = _queue_with(bus_root, "GATE-A")
    _outbox_msgs(bus_root, "mainD",
                 _request("GATE-A", "t1", "2026-08-12T01:00:00+00:00"),
                 {"id": "w1", "from": "mainD", "kind": "status", "task_id": "t1",
                  "ts": "2026-08-12T01:30:00+00:00", "payload": {"withdraws_gate": "GATE-A"}})
    hits = coordinator.withdrawn_or_stale_gates(bus_root, tq.read_text(encoding="utf-8"))
    assert [(g, v) for g, v, _ in hits] == [("GATE-A", "WITHDRAWN")]


def test_a_requester_who_moved_on_is_a_DISCREPANCY_not_a_withdrawal(bus_root: Path) -> None:
    """Tier 2, and the verdict must NOT claim withdrawal.

    The real case carried no gate_id — it was a task-complete on the request's own
    task_id — so a gate_id-keyed matcher would have detected nothing and passed
    vacuously. The wording matters: too broad a signal SUPPRESSES a live operator ask.
    """
    tq = _queue_with(bus_root, "GATE-B")
    _outbox_msgs(bus_root, "mainD",
                 _request("GATE-B", "t2", "2026-08-12T01:21:10+00:00"),
                 _complete("t2", "2026-08-12T01:41:39+00:00"))
    hits = coordinator.withdrawn_or_stale_gates(bus_root, tq.read_text(encoding="utf-8"))
    assert [(g, v) for g, v, _ in hits] == [("GATE-B", "REQUESTER-MOVED-ON")]


def test_a_live_gate_is_left_alone(bus_root: Path) -> None:
    """Mutation: no later task-complete, no signal. Suppressing a live ask is this
    defect inverted, and worse."""
    tq = _queue_with(bus_root, "GATE-C")
    _outbox_msgs(bus_root, "mainD", _request("GATE-C", "t3", "2026-08-12T01:00:00+00:00"))
    assert coordinator.withdrawn_or_stale_gates(bus_root, tq.read_text(encoding="utf-8")) == []


def test_a_task_complete_BEFORE_the_request_does_not_flag(bus_root: Path) -> None:
    """Ordering is load-bearing: re-requesting after finishing a prior round is normal."""
    tq = _queue_with(bus_root, "GATE-D")
    _outbox_msgs(bus_root, "mainD",
                 _complete("t4", "2026-08-12T00:30:00+00:00"),
                 _request("GATE-D", "t4", "2026-08-12T01:00:00+00:00"))
    assert coordinator.withdrawn_or_stale_gates(bus_root, tq.read_text(encoding="utf-8")) == []


def test_another_agents_task_complete_does_not_withdraw_your_gate(bus_root: Path) -> None:
    """Author identity is load-bearing too."""
    tq = _queue_with(bus_root, "GATE-E")
    _outbox_msgs(bus_root, "mainD", _request("GATE-E", "t5", "2026-08-12T01:00:00+00:00"))
    _outbox_msgs(bus_root, "mainA", _complete("t5", "2026-08-12T02:00:00+00:00", agent="mainA"))
    assert coordinator.withdrawn_or_stale_gates(bus_root, tq.read_text(encoding="utf-8")) == []


def test_the_notice_never_ticks_a_checkbox_and_does_not_repeat(bus_root: Path) -> None:
    tq = _queue_with(bus_root, "GATE-F")
    _outbox_msgs(bus_root, "mainD",
                 _request("GATE-F", "t6", "2026-08-12T01:00:00+00:00"),
                 _complete("t6", "2026-08-12T01:30:00+00:00"))
    first = coordinator.note_withdrawn_gates_in_queue(bus_root, epoch=1)
    body = tq.read_text(encoding="utf-8")
    assert first and first[0]["kind"] == "withdrawn-gate-notice"
    assert "- [ ] **GATE-F**" in body and "- [x]" not in body   # never ticks
    assert "REQUESTER-MOVED-ON" in body
    assert coordinator.note_withdrawn_gates_in_queue(bus_root, epoch=2) == []   # deduped


def test_an_unreadable_cursor_degrades_to_replay_rather_than_crashing(tmp_path: Path) -> None:
    """Three states, not two (`mainB`, 2026-08-12).

    A cursor can be MISSING, CORRUPT, or PRESENT-BUT-UNREADABLE. The first two
    already defaulted to 0 (replay). The third raised OSError out of the drain, so
    the agent neither replayed nor skipped — it crashed, and presented as a stuck
    agent. Only the first two were covered.
    """
    cursors = tmp_path / "cursors"
    cursors.mkdir(parents=True)
    cur = cursors / "ghost.json"

    cur.write_text('{"offset": 42}', encoding="utf-8")
    assert bus._cursor_get(tmp_path, "ghost") == 42

    os.chmod(cur, 0o000)
    try:
        assert bus._cursor_get(tmp_path, "ghost") == 0, "unreadable must degrade to replay"
    finally:
        os.chmod(cur, 0o644)

    cur.write_text("not json", encoding="utf-8")
    assert bus._cursor_get(tmp_path, "ghost") == 0
    cur.unlink()
    assert bus._cursor_get(tmp_path, "ghost") == 0


def test_cursor_read_survives_the_file_vanishing_after_the_exists_check(tmp_path: Path) -> None:
    """TOCTOU the `exists()` check opens: on a bus whose runtime is wiped mid-flight
    the file can disappear between the check and the read. FileNotFoundError is an
    OSError, so the same fix closes it — 0 (replay), never a crash."""
    cursors = tmp_path / "cursors"
    cursors.mkdir(parents=True)
    cur = cursors / "vanish.json"
    cur.write_text('{"offset": 7}', encoding="utf-8")

    real_read = Path.read_text

    def vanishing(self, *a, **k):
        if self == cur:
            cur.unlink(missing_ok=True)
            raise FileNotFoundError(2, "No such file or directory", str(cur))
        return real_read(self, *a, **k)

    try:
        Path.read_text = vanishing            # type: ignore[method-assign]
        assert bus._cursor_get(tmp_path, "vanish") == 0
    finally:
        Path.read_text = real_read            # type: ignore[method-assign]


def test_a_closed_spec_ref_box_is_refused_at_pick_time(tmp_path: Path) -> None:
    """C50: the queue was a snapshot nothing reconciled.

    `_eligible` checked status/deps/gates/lane/load — all from the QUEUE ROW — and
    never opened `spec_ref`. A row whose checkbox closed on 2026-07-29 stayed READY
    forever. Measured by `mainB`: 811 records resolving to NINE distinct rows, 86%
    naming a row already closed or rotted when picked.
    """
    h = tmp_path / "h.md"
    h.write_text("intro\n- [x] done thing\n- [ ] open thing\nprose line\n", encoding="utf-8")
    assert coordinator.spec_ref_state("h.md#L2", tmp_path)[0] == "closed"
    assert coordinator.spec_ref_state("h.md#L3", tmp_path)[0] == "open"


def test_anchor_rot_is_UNRESOLVED_not_closed_so_it_still_dispatches(tmp_path: Path) -> None:
    """Fail toward dispatchable on a bad pointer — refusing real work is costlier.

    The live instance: `opendataloader-pipeline-integration--013-L534` pointed at a
    PROSE bullet, and its two id halves disagreed (box #13 is at line 59). Rot must
    be reported, not silently treated as done.
    """
    h = tmp_path / "h.md"
    h.write_text("intro\n- [x] done\nprose, not a checkbox\n", encoding="utf-8")
    state, detail = coordinator.spec_ref_state("h.md#L3", tmp_path)
    assert state == "unresolved" and "anchor rot" in detail
    assert coordinator.spec_ref_state("h.md#L99", tmp_path)[0] == "unresolved"
    assert coordinator.spec_ref_state("missing.md#L1", tmp_path)[0] == "unresolved"
    assert coordinator.spec_ref_state("", tmp_path)[0] == "unresolved"
