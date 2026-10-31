"""LOOP-27: actual helper/watch entry points, isolated due/FILED and native bus schema."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "filing_alarm", ROOT / "scripts/coordination/filing_takeover_alarm.py"
)
alarm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alarm)
NOW = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)


@pytest.fixture
def fixture(tmp_path):
    flags = tmp_path / "flags"
    flags.mkdir()
    (flags / "filing-done").mkdir()
    (flags / "filing-due.jsonl").touch()
    bus = tmp_path / "bus"
    bus.mkdir()
    shutil.copyfile(
        ROOT / "coordination/session-bus/session_bus.schema.json",
        bus / "session_bus.schema.json",
    )
    (bus / "config.yaml").write_text(
        json.dumps(
            {
                "roster": [
                    {"id": "filing-watch", "role": "service", "lanes": ["none"]},
                    {
                        "id": "coordinator-agent",
                        "role": "coordinator-agent",
                        "lanes": ["none"],
                    },
                ]
            }
        )
    )
    assert bus.resolve() != Path("/workspace/coordination/session-bus").resolve()
    return flags, bus


def due(flags, run_id="native-result-1", *, age=7200):
    with (flags / "filing-due.jsonl").open("a") as out:
        out.write(
            json.dumps(
                {"id": run_id, "seen_at": (NOW - timedelta(seconds=age)).isoformat()}
            )
            + "\n"
        )


def messages(bus):
    p = bus / "outbox/filing-watch.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def test_one_stale_run_nudges_once_over_repeated_scans_and_duplicate_rows(fixture):
    flags, bus = fixture
    due(flags)
    due(flags)
    assert alarm.scan_once(flags, bus, now=NOW)["nudged"] == ["native-result-1"]
    assert alarm.scan_once(flags, bus, now=NOW)["nudged"] == []
    rows = messages(bus)
    assert len(rows) == 1
    assert rows[0]["kind"] == "nudge" and rows[0]["from"] == "filing-watch"
    assert (
        rows[0]["to"] == rows[0]["assignee"] == "coordinator-agent"
        and rows[0]["action_required"] is True
    )
    assert rows[0]["payload"]["alarm"] == "LOOP-27"
    assert not (flags / "filing-done/native-result-1.FILED").exists()


@pytest.mark.parametrize("age", [0, 1800, 3600, -30])
def test_not_more_than_one_hour_does_not_nudge(fixture, age):
    flags, bus = fixture
    due(flags, age=age)
    assert alarm.scan_once(flags, bus, now=NOW)["nudged"] == [] and messages(bus) == []


def test_filed_run_never_nudges(fixture):
    flags, bus = fixture
    due(flags)
    (flags / "filing-done/native-result-1.FILED").write_text("existing filing commit\n")
    assert alarm.scan_once(flags, bus, now=NOW)["nudged"] == [] and messages(bus) == []


@pytest.mark.parametrize(
    "bad",
    [
        {},
        [],
        {"id": "../../outside", "seen_at": NOW.isoformat()},
        {"id": "a", "seen_at": "bad"},
        {"id": "a", "seen_at": "2026-10-31T00:00:00"},
    ],
)
def test_invalid_observation_is_unknown_not_permission_to_nudge(fixture, bad):
    flags, bus = fixture
    (flags / "filing-due.jsonl").write_text(json.dumps(bad) + "\n")
    row = alarm.scan_once(flags, bus, now=NOW)
    assert (
        len(row["unknown"]) == 1
        and row["nudged"] == []
        and messages(bus) == []
        and alerts(flags) == []
    )


def test_checkpoint_survives_outbox_rotation(fixture):
    flags, bus = fixture
    due(flags)
    alarm.scan_once(flags, bus, now=NOW)
    (bus / "outbox/filing-watch.jsonl").rename(bus / "outbox/filing-watch.archived")
    assert alarm.scan_once(flags, bus, now=NOW)["nudged"] == [] and messages(bus) == []


def test_interrupted_checkpoint_reconciles_own_outbox_without_duplicate(
    fixture, monkeypatch
):
    flags, bus = fixture
    due(flags)
    real = alarm.bus._write_atomic

    def fail_bus_checkpoint(path, value):
        if path.name == "filing-alarm.sent.json":
            raise OSError("bus checkpoint interruption")
        return real(path, value)

    monkeypatch.setattr(alarm.bus, "_write_atomic", fail_bus_checkpoint)
    report = alarm.scan_once(flags, bus, now=NOW)
    assert report["bus_status"] == "unknown"
    assert len(messages(bus)) == len(alerts(flags)) == 1
    monkeypatch.setattr(alarm.bus, "_write_atomic", real)
    report = alarm.scan_once(flags, bus, now=NOW)
    assert report["nudged"] == [] and report["alerted"] == []
    assert len(messages(bus)) == len(alerts(flags)) == 1


def test_malformed_outbox_refuses_instead_of_guessing_delivery(fixture):
    flags, bus = fixture
    due(flags)
    (bus / "outbox").mkdir()
    path = bus / "outbox/filing-watch.jsonl"
    path.write_text("{bad\n")
    for _ in range(2):
        report = alarm.scan_once(flags, bus, now=NOW)
        assert report["bus_status"] == "unknown" and report["unknown"]
    assert path.read_text() == "{bad\n" and len(alerts(flags)) == 1


def test_actual_watcher_once_calls_alarm_and_keeps_existing_producer(fixture):
    flags, bus = fixture
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    (flags / "filing-due.jsonl").write_text(
        json.dumps({"id": "old-real-run", "seen_at": old.isoformat()}) + "\n"
    )
    (flags / "grants").mkdir()
    (flags / "grants/new-real-run.ended").write_text("rc=0\n")
    env = {
        **os.environ,
        "FILING_WATCH_FLAGS_ROOT": str(flags),
        "FILING_WATCH_BUS_ROOT": str(bus),
        "PATH": str(Path(sys.executable).parent) + ":" + os.environ["PATH"],
    }
    argv = ["/bin/bash", str(ROOT / "scripts/coordination/filing_watch.sh"), "--once"]
    for _ in range(2):
        p = subprocess.run(argv, env=env, capture_output=True, text=True, check=False)
        assert p.returncode == 0, p.stdout + p.stderr
    assert (
        len(messages(bus)) == 1
        and messages(bus)[0]["payload"]["run_id"] == "old-real-run"
    )
    records = [
        json.loads(x) for x in (flags / "filing-due.jsonl").read_text().splitlines()
    ]
    assert [r["id"] for r in records].count("new-real-run") == 1
    assert not (flags / "filing-done/old-real-run.FILED").exists()
    assert not list(bus.glob("inbox/*")) and not (bus / "queue.jsonl").exists()
    assert [r["id"] for r in alerts(flags)] == ["old-real-run"]


@pytest.mark.parametrize(
    "raw", ["{", '{"id":"partial","seen_at":"2026-10-30T00:00:00Z"}', "{bad}\n"]
)
def test_malformed_or_unterminated_due_row_never_nudges(fixture, raw):
    flags, bus = fixture
    (flags / "filing-due.jsonl").write_text(raw)
    result = alarm.scan_once(flags, bus, now=NOW)
    assert len(result["unknown"]) == 1
    assert result["nudged"] == [] and messages(bus) == [] and alerts(flags) == []


def test_missing_runtime_service_roster_refuses_without_outbox(fixture):
    flags, bus = fixture
    config = json.loads((bus / "config.yaml").read_text())
    config["roster"] = [r for r in config["roster"] if r["id"] != "filing-watch"]
    (bus / "config.yaml").write_text(json.dumps(config))
    due(flags)
    for _ in range(2):
        report = alarm.scan_once(flags, bus, now=NOW)
        assert (
            report["bus_status"] == "unknown"
            and "not a roster id" in report["unknown"][0]["reason"]
        )
    assert messages(bus) == [] and len(alerts(flags)) == 1


def test_actual_dispatcher_relays_service_outbox_once(fixture):
    from scripts.coordination import session_bus_coordinator as coordinator

    flags, bus = fixture
    due(flags)
    alarm.scan_once(flags, bus, now=NOW)
    original = (bus / "outbox/filing-watch.jsonl").read_bytes()
    config = coordinator._load_config(bus)
    assert any(
        r["id"] == "filing-watch" and r["role"] == "service" for r in config["roster"]
    )
    for epoch in (1, 2):
        coordinator.relay_outbox_messages(bus, config["roster"], epoch, config)
    inbox, _ = alarm.bus._read_jsonl(bus / "inbox/coordinator-agent.jsonl")
    relayed = [
        row
        for row in inbox
        if row.get("kind") == "nudge" and row.get("from") == "filing-watch"
    ]
    assert len(relayed) == 1 and relayed[0]["payload"]["alarm"] == "LOOP-27"
    assert (bus / "outbox/filing-watch.jsonl").read_bytes() == original
    assert not list((bus / "outbox").glob("coordinator*"))
    assert not (bus / "queue.jsonl").exists()


def test_watcher_missing_yaml_is_fail_visible_without_bus_append(fixture, tmp_path):
    flags, bus = fixture
    (flags / "grants").mkdir()
    due(flags)
    blocked = tmp_path / "missing-dependency"
    blocked.mkdir()
    (blocked / "yaml.py").write_text(
        "raise ModuleNotFoundError('yaml dependency intentionally unavailable')\n"
    )
    env = {
        **os.environ,
        "FILING_WATCH_FLAGS_ROOT": str(flags),
        "FILING_WATCH_BUS_ROOT": str(bus),
        "PATH": str(Path(sys.executable).parent) + ":" + os.environ["PATH"],
        "PYTHONPATH": str(blocked),
    }
    p = subprocess.run(
        ["/bin/bash", str(ROOT / "scripts/coordination/filing_watch.sh"), "--once"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert p.returncode != 0
    assert "yaml dependency intentionally unavailable" in p.stdout + p.stderr
    assert len(alerts(flags)) == 1
    assert "filing-alarm unknown rc=" in (flags / "filing-watch.log").read_text()
    assert messages(bus) == []
    assert not list(bus.glob("inbox/*")) and not (bus / "queue.jsonl").exists()


def alerts(flags):
    path = flags / "filing-alarm.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def test_own_alert_stream_once_across_duplicate_rows_and_restart(fixture):
    flags, bus = fixture
    due(flags)
    due(flags)
    first = alarm.scan_once(flags, bus, now=NOW)
    assert first["alerted"] == ["native-result-1"]
    spec = importlib.util.spec_from_file_location(
        "alarm_restarted", ROOT / "scripts/coordination/filing_takeover_alarm.py"
    )
    restarted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(restarted)
    second = restarted.scan_once(flags, bus, now=NOW)
    assert second["alerted"] == [] and second["nudged"] == []
    assert len(messages(bus)) == len(alerts(flags)) == 1
    row = alerts(flags)[0]
    assert row["id"] == "native-result-1" and row["action"] == "filing-takeover"
    assert row["bus_recipient"] == "coordinator-agent"


@pytest.mark.parametrize(
    "raw",
    [
        "{",
        '{"schema_version":"epyc.filing-alarm.v1","kind":"filing-overdue","id":"native-result-1"}',
        "{}\n",
        "[]\n",
    ],
)
def test_bad_or_partial_own_alert_stream_is_preserved_and_refuses(fixture, raw):
    flags, bus = fixture
    due(flags)
    path = flags / "filing-alarm.jsonl"
    path.write_text(raw)
    with pytest.raises(ValueError):
        alarm.scan_once(flags, bus, now=NOW)
    assert path.read_text() == raw and messages(bus) == []


def test_bus_checkpoint_interruption_backfills_one_alert_without_second_nudge(
    fixture, monkeypatch
):
    flags, bus = fixture
    due(flags)
    real = alarm.bus._write_atomic

    def fail_bus_checkpoint(path, value):
        if path.name == "filing-alarm.sent.json":
            raise OSError("bus checkpoint interruption")
        return real(path, value)

    monkeypatch.setattr(alarm.bus, "_write_atomic", fail_bus_checkpoint)
    report = alarm.scan_once(flags, bus, now=NOW)
    assert report["bus_status"] == "unknown"
    assert len(messages(bus)) == len(alerts(flags)) == 1
    monkeypatch.setattr(alarm.bus, "_write_atomic", real)
    report = alarm.scan_once(flags, bus, now=NOW)
    assert report["nudged"] == [] and report["alerted"] == []
    assert len(messages(bus)) == len(alerts(flags)) == 1


def test_alert_append_interruption_recovers_from_stream_without_duplicate(
    fixture, monkeypatch
):
    flags, bus = fixture
    due(flags)
    real = alarm.os.fsync
    monkeypatch.setattr(
        alarm.os,
        "fsync",
        lambda *args: (_ for _ in ()).throw(OSError("alert flush interruption")),
    )
    with pytest.raises(OSError):
        alarm.scan_once(flags, bus, now=NOW)
    assert messages(bus) == [] and len(alerts(flags)) == 1
    monkeypatch.setattr(alarm.os, "fsync", real)
    assert alarm.scan_once(flags, bus, now=NOW)["alerted"] == []
    assert len(messages(bus)) == len(alerts(flags)) == 1


@pytest.mark.parametrize(
    "failure",
    ["missing-config", "malformed-config", "bad-sent-state", "append-refused"],
)
def test_bus_failure_does_not_blind_owner_alert(fixture, monkeypatch, failure):
    flags, bus = fixture
    due(flags)
    if failure == "missing-config":
        (bus / "config.yaml").unlink()
    elif failure == "malformed-config":
        (bus / "config.yaml").write_text("[unterminated")
    elif failure == "bad-sent-state":
        (flags / "filing-alarm.sent.json").write_text("{bad")
    else:
        monkeypatch.setattr(alarm.bus, "main", lambda *args: 2)
    for _ in range(2):
        result = alarm.scan_once(flags, bus, now=NOW)
        assert result["bus_status"] == "unknown" and result["unknown"]
    assert len(alerts(flags)) == 1 and messages(bus) == []


def test_failed_bus_append_recovers_later_without_repeating_owner_alert(
    fixture, monkeypatch
):
    flags, bus = fixture
    due(flags)
    real = alarm.bus.main
    monkeypatch.setattr(alarm.bus, "main", lambda *args: 2)
    first = alarm.scan_once(flags, bus, now=NOW)
    assert first["alerted"] == ["native-result-1"] and first["bus_status"] == "unknown"
    monkeypatch.setattr(alarm.bus, "main", real)
    later = alarm.scan_once(flags, bus, now=NOW)
    assert later["alerted"] == [] and later["nudged"] == ["native-result-1"]
    assert len(alerts(flags)) == len(messages(bus)) == 1


@pytest.mark.parametrize(
    "failure", ["missing-roster", "malformed-config", "malformed-outbox"]
)
def test_actual_watcher_bus_unavailable_keeps_one_owner_alert(fixture, failure):
    flags, bus = fixture
    (flags / "grants").mkdir()
    due(flags)
    if failure == "missing-roster":
        config = json.loads((bus / "config.yaml").read_text())
        config["roster"] = [
            row for row in config["roster"] if row["id"] != "filing-watch"
        ]
        (bus / "config.yaml").write_text(json.dumps(config))
    elif failure == "malformed-config":
        (bus / "config.yaml").write_text("[bad")
    else:
        (bus / "outbox").mkdir()
        (bus / "outbox/filing-watch.jsonl").write_text("{partial")
    env = {
        **os.environ,
        "FILING_WATCH_FLAGS_ROOT": str(flags),
        "FILING_WATCH_BUS_ROOT": str(bus),
        "PATH": str(Path(sys.executable).parent) + ":" + os.environ["PATH"],
    }
    for _ in range(2):
        p = subprocess.run(
            ["/bin/bash", str(ROOT / "scripts/coordination/filing_watch.sh"), "--once"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert p.returncode != 0
        report = json.loads(p.stdout)
        assert report["status"] == "unknown" and report["bus_status"] == "unknown"
    assert len(alerts(flags)) == 1
    if failure == "malformed-outbox":
        assert (bus / "outbox/filing-watch.jsonl").read_text() == "{partial"
    else:
        assert messages(bus) == []
    assert not list(bus.glob("inbox/*")) and not (bus / "queue.jsonl").exists()
