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


@pytest.mark.parametrize("kind", sorted(coordinator._NO_RELAY_KINDS))
def test_c2_no_relay_kinds_are_not_fanned_out(bus_root: Path, kind: str) -> None:
    """C2: messages consumed by a dedicated path cannot be duplicated by relay."""
    _provision(bus_root, *AGENTS)
    row = _message("alice", "bob", kind, seq=1, task_id="task-1")
    _append(bus_root / "outbox" / "alice.jsonl", row)
    roster = json.loads((bus_root / "config.yaml").read_text())["roster"]
    assert coordinator.relay_outbox_messages(bus_root, roster, epoch=1) == []
    assert _read_jsonl(bus_root / "inbox" / "bob.jsonl") == []


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
