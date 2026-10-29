"""Offline expiry routing and hub-health behavior; only temporary bus files are written."""
from __future__ import annotations

import fcntl
import json
import time

import pytest

from dashboard import panels, server
from scripts.coordination import diagnostic_override_expiry as expiry
from scripts.coordination import session_bus_coordinator as coordinator
from scripts.coordination.session_bus import COORDINATOR_DAEMON, required_writer


@pytest.fixture
def case(tmp_path, monkeypatch):
    records = tmp_path / "records"
    records.mkdir()
    bus = tmp_path / "bus"
    (bus / "inbox").mkdir(parents=True)
    config = {"diagnostic_overrides": {"record_dir": str(records)},
              "roster": [{"id": "window-owner"}]}
    monkeypatch.setattr(server, "_read_bus_config", lambda: config)
    path = records / "architect_critic.json"
    record = {"schema": "epyc.env_override.v1", "component": "architect_critic",
              "owner": "window-owner", "applied_at": "2000-01-01T00:00:00+00:00",
              "expires_at": "2000-01-01T01:00:00+00:00", "pids": {"8083": 123},
              "restore": "orchestrator_stack.py reload architect_critic"}
    path.write_text(json.dumps(record))
    return bus, config, path, record


def test_expiry_nudges_owner_once_and_survives_restart_and_rotation(case):
    bus, config, path, record = case
    original = path.read_bytes()
    coordinator.notify_expired_diagnostic_overrides(bus, config, 1)
    coordinator.notify_expired_diagnostic_overrides(bus, config, 2)
    inbox = bus / "inbox/window-owner.jsonl"
    messages = [json.loads(line) for line in inbox.read_text().splitlines()]
    assert len(messages) == 1
    assert messages[0]["to"] == "window-owner"
    assert messages[0]["from"] == COORDINATOR_DAEMON
    assert messages[0]["kind"] == "nudge"
    assert messages[0]["payload"]["component"] == "architect_critic"
    assert messages[0]["payload"]["restore_command"] == record["restore"]
    assert path.read_bytes() == original  # notification never restores/mutates the override
    inbox.rename(inbox.with_suffix(".archived"))
    coordinator.notify_expired_diagnostic_overrides(bus, config, 3)
    assert not inbox.exists()  # durable state outlives inbox rotation
    assert required_writer(bus, bus / "inbox" / ".diagnostic_override_expiry_state.json") == COORDINATOR_DAEMON


def test_delivery_before_checkpoint_crash_does_not_duplicate(case):
    bus, config, _, _ = case
    coordinator.notify_expired_diagnostic_overrides(bus, config, 1)
    (bus / "inbox" / ".diagnostic_override_expiry_state.json").unlink()
    coordinator.notify_expired_diagnostic_overrides(bus, config, 2)
    assert len((bus / "inbox/window-owner.jsonl").read_text().splitlines()) == 1


def test_malformed_native_inbox_payload_does_not_crash_or_fake_delivery(case):
    bus, config, path, _ = case
    corr_id = expiry.snapshot(path.parent)["expired"][0]["corr_id"]
    inbox = bus / "inbox/window-owner.jsonl"
    inbox.write_text(json.dumps({"kind": "nudge", "corr_id": corr_id,
                                "payload": "malformed-native-payload"}) + "\n")
    coordinator.notify_expired_diagnostic_overrides(bus, config, 1)
    coordinator.notify_expired_diagnostic_overrides(bus, config, 2)
    rows = [json.loads(line) for line in inbox.read_text().splitlines()]
    delivered = [row for row in rows if isinstance(row.get("payload"), dict)]
    assert len(delivered) == 1
    assert delivered[0]["payload"]["reason"] == "diagnostic-override-expired"


def test_a_new_override_window_gets_its_own_nudge(case):
    bus, config, path, record = case
    coordinator.notify_expired_diagnostic_overrides(bus, config, 1)
    record["applied_at"] = "2000-01-02T00:00:00+00:00"
    record["expires_at"] = "2000-01-02T01:00:00+00:00"
    path.write_text(json.dumps(record))
    coordinator.notify_expired_diagnostic_overrides(bus, config, 2)
    assert len((bus / "inbox/window-owner.jsonl").read_text().splitlines()) == 2


@pytest.mark.parametrize("owner", [None, "unregistered-owner"])
def test_unroutable_owner_is_not_guessed_or_marked_sent_and_can_recover(case, owner):
    bus, config, path, record = case
    record["owner"] = owner
    path.write_text(json.dumps(record))
    advice = coordinator.notify_expired_diagnostic_overrides(bus, config, 1)
    assert "no routable owner" in advice[0]["detail"]
    assert coordinator.notify_expired_diagnostic_overrides(bus, config, 2) == []
    assert list((bus / "inbox").glob("*.jsonl")) == []
    assert server.diagnostic_overrides_health()[0] == 503
    state = json.loads((bus / "inbox" / ".diagnostic_override_expiry_state.json").read_text())
    assert state["seen"] == {}
    if owner is None:
        record["owner"] = "window-owner"
        path.write_text(json.dumps(record))
        owner = "window-owner"
    else:
        config["roster"].append({"id": owner})
    coordinator.notify_expired_diagnostic_overrides(bus, config, 3)
    assert len((bus / "inbox" / f"{owner}.jsonl").read_text().splitlines()) == 1


def test_overlapping_poller_yields_without_blocking_or_sending(case):
    bus, config, _, _ = case
    with (bus / "inbox" / ".diagnostic_override_expiry_state.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert coordinator.notify_expired_diagnostic_overrides(bus, config, 1) == []
        assert list((bus / "inbox").glob("*.jsonl")) == []
    coordinator.notify_expired_diagnostic_overrides(bus, config, 2)
    assert len((bus / "inbox/window-owner.jsonl").read_text().splitlines()) == 1


def test_expired_fresh_record_reaches_global_health_and_clear_recovers(case, monkeypatch):
    _, _, path, record = case
    baseline = {name: panels.envelope(source, panels.Observation(
        artifact_present=True, timestamp=time.time(), populated=True))
        for name, source in panels.PANELS.items()}

    def envelopes():
        return {**baseline, "diagnostic_overrides":
                server.diagnostic_overrides_payload()["_freshness"]}

    monkeypatch.setattr(server, "panel_envelopes", envelopes)
    monkeypatch.setattr(server, "_read_kernel_progression", lambda: {})
    payload = server.health_payload()
    assert payload["status"] == "degraded"
    assert payload["status_set_by"]["panel"] == "diagnostic_overrides"
    assert record["restore"] in payload["status_set_by"]["why"]
    assert payload["panels"]["diagnostic_overrides"]["staleness_class"] == "fresh"
    assert server.diagnostic_overrides_health()[0] == 503
    path.unlink()
    assert server.health_payload()["status"] == "ok"
    assert server.diagnostic_overrides_health()[0] == 200
    assert all(not value for value in panels.registry_gaps(server).values())


@pytest.mark.parametrize("contents", ["{", '{"schema":"unknown"}',
                                      '{"schema":"epyc.env_override.v1","component":"architect_critic","expires_at":5}'])
def test_unreadable_records_are_unhealthy_not_empty(case, contents):
    _, _, path, _ = case
    path.write_text(contents)
    result = expiry.snapshot(path.parent)
    assert result["status"] == "degraded" and result["errors"]


def test_unexpired_record_does_not_nudge_or_degrade(case):
    bus, config, path, record = case
    record["expires_at"] = "3000-01-01T00:00:00+00:00"
    path.write_text(json.dumps(record))
    assert coordinator.notify_expired_diagnostic_overrides(bus, config, 1) == []
    assert list((bus / "inbox").glob("*.jsonl")) == []
    assert server.diagnostic_overrides_health()[0] == 200
