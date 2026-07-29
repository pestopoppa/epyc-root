"""Protocol-anchored regression coverage for the session bus.

Every fixture uses an isolated ``tmp_path`` bus root.  These tests must never
point at the live coordination/session-bus directory: a coordinator daemon and
working agent sessions read that directory concurrently.
"""

from __future__ import annotations

import json
import os
import shutil
import time
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

    assert "DAEMON IS NOT RUNNING" in out
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
