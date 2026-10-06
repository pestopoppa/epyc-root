"""Synthetic native dependency controls; execute only in reviewed GitHub CI.

No real docker, host cron, supervisor, production source/store or kernel is invoked.
The outer CI observation uses the existing NI07 carrier; these native rows stay ungraded.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import host_supervision_activation as host

_TICK_SPEC = importlib.util.spec_from_file_location("activation_hook_hygiene",
                                                ROOT / "scripts/system/host_hygiene_tick.py")
tick_module = importlib.util.module_from_spec(_TICK_SPEC)
sys.modules[_TICK_SPEC.name] = tick_module
_TICK_SPEC.loader.exec_module(tick_module)

PIN = "a" * 40
INSTALL_ID = "a0000000-0000-4000-8000-000000000001"
INSTALLED = "2026-10-06T11:00:00+00:00"
MARKER = "2026-10-06T12:00:00+00:00"
HEARTBEAT = "2026-10-06T12:01:00+00:00"


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromisoformat(MARKER).astimezone(tz)
    monkeypatch.setattr(host.dt, "datetime", Clock)
    root = tmp_path / "root"
    installer = root / "scripts/operator/install_supervision_cron_20260916.sh"
    installer.parent.mkdir(parents=True)
    installer.write_bytes(b"#!/bin/bash\n# inert synthetic installer bytes\n")
    registry = root / "scripts/coordination/observer_registry.json"
    registry.parent.mkdir()
    registry.write_text(json.dumps({"observers": [
        {"id": "host_hygiene_tick", "fixture": True},
        {"id": "opencode_event_reaper", "fixture": True}]}))
    backup = root / "logs/backup"
    backup.parent.mkdir()
    backup.write_bytes(b"0 3 * * * /usr/bin/true # inert backup\n")
    kwargs = dict(root=root, install_id=INSTALL_ID, supervisor_pin=PIN,
                  installer_path=installer, registry_path=registry, backup_path=backup,
                  selected_cron_entries=[
                      f"*/2 * * * * /fixture/hub-supervisor/{PIN}/scripts/dashboard/hub_supervisor.sh once # epyc-op9-hub-supervisor",
                      "*/5 * * * * /fixture/inert # epyc-fw3-fleet-watch"],
                  installer_sha256=hashlib.sha256(installer.read_bytes()).hexdigest(),
                  installed_at=INSTALLED)
    return root, kwargs


def paths(root):
    base = root / "logs/hygiene/host-supervision-activation"
    return base, base / "pending" / f"{INSTALL_ID}.json"


def heartbeat(root, value=HEARTBEAT):
    path = root / "logs/state.json"
    path.write_text(json.dumps({"heartbeat_at": value, "fixture": True}))
    return host.capture_pending_heartbeat(root, path, value)


def reseal(path, updates):
    row = json.loads(path.read_bytes())
    row.update(updates)
    row.pop("evidence_sha256")
    path.write_bytes(json.dumps(host._self_hash(row)).encode())


def test_dependency_boundary_and_exact_input_bytes(fixture):
    root, kwargs = fixture
    receipt = host.capture_install(**kwargs)
    row = json.loads(receipt.read_bytes())
    classification = host.classify_receipt(row)
    assert classification["classification"] == "dependency_evidence_only"
    for key in ("performance_measurement", "corroborating_witness", "belief_measurement_emitted",
                "claim_tuple_emitted", "support_frame_emitted"):
        assert classification[key] is False
    assert row["installer_sha256"] == hashlib.sha256(kwargs["installer_path"].read_bytes()).hexdigest()
    assert row["registry_bytes_sha256"] == hashlib.sha256(kwargs["registry_path"].read_bytes()).hexdigest()
    assert row["crontab_backup_sha256"] == hashlib.sha256(kwargs["backup_path"].read_bytes()).hexdigest()
    assert row["registry_scope"] == "canonical_snapshot_only_not_deployment_proof"
    assert row["registry_projection_sha256"] == host._registry_projection(kwargs["registry_path"].read_bytes())
    assert row["selected_cron_sha256"] == host._sha(host._canonical(kwargs["selected_cron_entries"]))


def test_second_tick_and_repeat_capture_keep_original(fixture):
    root, kwargs = fixture
    receipt = host.capture_install(**kwargs)
    install_bytes = receipt.read_bytes()
    base, marker = paths(root)
    marker_bytes = marker.read_bytes()
    result = heartbeat(root)
    assert len(result) == 1
    first_bytes = result[0].read_bytes()
    assert not marker.exists()
    assert (base / "consumed" / marker.name).read_bytes() == marker_bytes
    assert heartbeat(root, "2026-10-06T12:02:00+00:00") == []
    assert host.capture_install(**kwargs) == receipt
    assert receipt.read_bytes() == install_bytes and result[0].read_bytes() == first_bytes
    assert list((base / "pending").glob("*.json")) == []
    row = json.loads(first_bytes)
    assert row["marker_created_at"] == MARKER and row["heartbeat_at"] == HEARTBEAT
    assert row["state_bytes_sha256"] == hashlib.sha256(
        json.dumps({"heartbeat_at": HEARTBEAT, "fixture": True}).encode()).hexdigest()


@pytest.mark.parametrize("value", [INSTALLED, "2026-10-06T11:59:59+00:00", MARKER])
def test_noneligible_state_preserves_pending(fixture, value):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    base, marker = paths(root)
    before = marker.read_bytes()
    assert heartbeat(root, value) == []
    assert marker.read_bytes() == before
    assert not (base / f"heartbeat-{INSTALL_ID}.json").exists()
    assert len(heartbeat(root)) == 1


@pytest.mark.parametrize("updates", [
    {"classification": "measurement"}, {"support_scope": "other"},
    {"installed_at": "2026-10-06T10:00:00+00:00"},
    {"marker_created_at": "2026-10-06T10:00:00+00:00"},
    {"installation_path": "logs/../outside.json"},
    {"installation_evidence_sha256": "b" * 64}, {"extra": True},
    {"install_id": "a0000000-0000-4000-8000-000000000002"},
])
def test_resealed_marker_mismatch_refuses_preserving_marker(fixture, updates):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    _, marker = paths(root)
    reseal(marker, updates)
    before = marker.read_bytes()
    with pytest.raises(host.ReceiptError):
        heartbeat(root)
    assert marker.read_bytes() == before


def test_duplicate_json_and_tamper_refused(fixture):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    _, marker = paths(root)
    original = marker.read_bytes()
    marker.write_bytes(original.replace(b'"schema":', b'"schema":"duplicate","schema":', 1))
    with pytest.raises(host.ReceiptError, match="duplicate"):
        heartbeat(root)
    marker.write_bytes(original.replace(b"dependency_evidence_only", b"dependency_evidence_evil"))
    with pytest.raises(host.ReceiptError, match="^evidence_sha256 does not bind native row$"):
        heartbeat(root)


@pytest.mark.parametrize("recovery", ["receipt_only", "receipt_and_consumed", "install_only"])
def test_interrupted_publication_recovery(fixture, recovery):
    root, kwargs = fixture
    install = host.capture_install(**kwargs)
    base, marker = paths(root)
    marker_bytes = marker.read_bytes()
    if recovery == "install_only":
        marker.unlink()
        assert host.capture_install(**kwargs) == install
        assert len(heartbeat(root)) == 1
    else:
        first = heartbeat(root)[0]
        first_bytes = first.read_bytes()
        marker.write_bytes(marker_bytes)
        consumed = base / "consumed" / marker.name
        if recovery == "receipt_only":
            consumed.unlink()
        assert heartbeat(root, "2026-10-06T12:02:00+00:00") == [first]
        assert first.read_bytes() == first_bytes
        assert consumed.read_bytes() == marker_bytes and not marker.exists()


def test_conflicting_consumed_preserves_pending(fixture):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    base, marker = paths(root)
    result = heartbeat(root)[0]
    consumed = base / "consumed" / marker.name
    marker.write_bytes(consumed.read_bytes())
    consumed.write_bytes(b"different")
    before = marker.read_bytes()
    with pytest.raises(host.ReceiptError, match="differs"):
        heartbeat(root)
    assert marker.read_bytes() == before and result.exists()


@pytest.mark.parametrize("kind", ["parent", "outside", "symlink"])
def test_input_path_escape_refused(fixture, kind):
    root, kwargs = fixture
    if kind == "parent":
        kwargs["backup_path"] = root / "logs/../../escape"
    elif kind == "outside":
        kwargs["backup_path"] = root.parent / "escape"
    else:
        link = root / "logs/link"
        link.symlink_to(kwargs["backup_path"])
        kwargs["backup_path"] = link
    with pytest.raises(host.ReceiptError):
        host.capture_install(**kwargs)
    assert not paths(root)[0].exists()


@pytest.mark.parametrize("kind", ["source", "duplicate_observer", "duplicate_key", "wrong_cron", "changed_receipt"])
def test_source_or_input_identity_refused(fixture, kind):
    root, kwargs = fixture
    if kind == "source":
        kwargs["installer_path"].write_bytes(b"changed")
    elif kind == "duplicate_observer":
        registry = json.loads(kwargs["registry_path"].read_bytes())
        registry["observers"].append(registry["observers"][0])
        kwargs["registry_path"].write_text(json.dumps(registry))
    elif kind == "duplicate_key":
        kwargs["registry_path"].write_bytes(b'{"observers":[],"observers":[]}')
    elif kind == "wrong_cron":
        kwargs["selected_cron_entries"][0] = "bogus " + PIN + " # epyc-op9-hub-supervisor"
    else:
        receipt = host.capture_install(**kwargs)
        before = receipt.read_bytes()
        kwargs["backup_path"].write_bytes(b"changed")
    with pytest.raises(host.ReceiptError):
        host.capture_install(**kwargs)
    if kind == "changed_receipt":
        assert receipt.read_bytes() == before


def test_readonly_preflight(fixture):
    root, kwargs = fixture
    result = host.preflight_capture(root, kwargs["installer_path"], kwargs["registry_path"],
                                    kwargs["backup_path"].parent, kwargs["installer_sha256"])
    assert host._uuid(result["install_id"]) == result["install_id"]
    assert not paths(root)[0].exists()
    with pytest.raises(host.ReceiptError):
        host.preflight_capture(root, kwargs["installer_path"], kwargs["registry_path"],
                               root / "absent", kwargs["installer_sha256"])
    with pytest.raises(host.ReceiptError):
        host.preflight_capture(root, kwargs["installer_path"], kwargs["registry_path"],
                               kwargs["backup_path"].parent, "b" * 64)


@pytest.fixture
def installer_fixture(tmp_path):
    """Every external docker operation is an inert response or owned fixture I/O."""
    root = tmp_path / "root"
    installer = root / "scripts/operator/install_supervision_cron_20260916.sh"
    installer.parent.mkdir(parents=True)
    # Literal root substitution is explicitly synthetic; runtime structure is unchanged.
    source = (ROOT / "scripts/operator/install_supervision_cron_20260916.sh").read_text()
    installer.write_text(source.replace('ROOT="/mnt/raid0/llm/epyc-root"', f'ROOT="{root}"'))
    adapter = root / "scripts/vidya/adapters/host_supervision_activation.py"
    adapter.parent.mkdir(parents=True)
    adapter.write_bytes((ROOT / "scripts/vidya/adapters/host_supervision_activation.py").read_bytes())
    registry = root / "scripts/coordination/observer_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"observers": [{"id": name} for name in sorted(host.EXPECTED_OBSERVERS)]}))
    (root / "logs").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls.jsonl"
    cron = tmp_path / "cron"
    cron.write_text("0 3 * * * /fixture/inert # original\n")
    docker = bin_dir / "docker"
    docker.write_text('''#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys
args = sys.argv[1:]
with open(os.environ["FIXTURE_CALLS"], "a") as stream:
    stream.write(json.dumps(args) + "\\n")
if args[0] == "inspect":
    print("true"); sys.exit(0)
assert args.pop(0) == "exec"
assert args[:2] == ["-u", "node"]
del args[:3]  # -u node container
if args[0] == "test":
    sys.exit(1 if args[1] == "-d" else 0)
if args[0] == "git":
    operation = args[3]
    assert operation in {"fetch", "rev-parse", "cat-file", "grep"}
    if operation == "rev-parse": print("a" * 40)
    sys.exit(0)
if args[0] == "python3":
    assert pathlib.Path(args[1]) == pathlib.Path(os.environ["FIXTURE_ADAPTER"])
    assert args[2] in {"preflight", "capture-install"}
    sys.exit(subprocess.run([sys.executable, *args[1:]], check=False).returncode)
if args[:2] == ["bash", "-c"]:
    if "set -o noclobber" in args[2]:
        assert len(args) == 6 and pathlib.Path(args[4]).parent == pathlib.Path(os.environ["FIXTURE_ROOT"]) / "logs"
        with open(args[4], "x") as stream: stream.write(args[5] + "\\n")
    else:
        # Admit only the reviewed complete pin helper and its exact arguments.
        # Return an inert success; never execute its shell/archive/supervisor code.
        assert hashlib.sha256(args[2].encode()).hexdigest() == "03356d06881896c0fdd0f9650bf66dd9837fa151805b7f1e9793ff21dacca855"
        pin_base = "/mnt/raid0/llm/ops/hub-supervisor"
        assert args[3:] == [
            "_", os.environ["FIXTURE_ROOT"], "a" * 40, pin_base + "/" + "a" * 40, pin_base,
            "scripts/dashboard/hub_supervisor.sh", "scripts/dashboard/hub_launch_spec.py",
            "scripts/dashboard/refresh_hub_view.sh", "scripts/coordination/daemon_provenance.sh",
        ]
    sys.exit(0)
raise AssertionError("unexpected child: " + repr(args))
''')
    docker.chmod(0o700)
    crontab = bin_dir / "crontab"
    crontab.write_text('''#!/usr/bin/env python3
import os, pathlib, sys
path = pathlib.Path(os.environ["FIXTURE_CRON"])
if sys.argv[1:] == ["-l"]: print(path.read_text(), end="")
elif sys.argv[1:] == ["-"]: path.write_text(sys.stdin.read())
else: raise AssertionError("unexpected cron command")
''')
    crontab.chmod(0o700)
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
               SUPERVISION_CRON_ALLOW_CONTAINER="1", FIXTURE_ROOT=str(root),
               FIXTURE_CALLS=str(calls), FIXTURE_CRON=str(cron), FIXTURE_ADAPTER=str(adapter))
    return root, installer, registry, adapter, calls, cron, env


def run_installer(fx, args, *, substitution=False, outside=False):
    _, installer, _, _, _, _, env = fx
    if outside:
        copy = installer.parents[3] / "outside.sh"
        copy.write_bytes(installer.read_bytes())
        installer = copy
    if substitution:
        command = ["bash", "-c", 'bash <(cat "$1") "${@:2}"', "fixture", str(installer), *args]
    else:
        command = ["bash", str(installer), *args]
    return subprocess.run(command, env=env, capture_output=True, text=True, timeout=15, check=False)


@pytest.mark.parametrize("mode", ["default", "process_substitution", "outside", "dry_capture", "fw"])
def test_legacy_callers_and_dry_run_never_capture(installer_fixture, mode):
    fx = installer_fixture
    root, _, _, adapter, calls, cron, _ = fx
    adapter.unlink()  # Legacy behavior must work even without a capture module.
    original = cron.read_bytes()
    args = ["--fleet-watch-only"] if mode == "fw" else ["--all"]
    if mode == "dry_capture":
        args += ["--capture-activation", "--dry-run"]
    result = run_installer(fx, args, substitution=mode == "process_substitution", outside=mode == "outside")
    assert result.returncode == 0, result.stderr
    assert not paths(root)[0].exists()
    invoked = [json.loads(line) for line in calls.read_text().splitlines()]
    assert all("python3" not in row for row in invoked)
    if mode == "dry_capture":
        assert cron.read_bytes() == original and not list((root / "logs").iterdir())
    else:
        assert len(list((root / "logs").glob("crontab.bak-*"))) == 1
        assert cron.read_text().count("# epyc-fw3-fleet-watch") == 1


@pytest.mark.parametrize("failure", ["module_missing", "registry_duplicate", "outside", "process_substitution", "backup_outside"])
def test_capture_preflight_refuses_before_mutation(installer_fixture, failure):
    fx = installer_fixture
    root, _, registry, adapter, calls, cron, env = fx
    if failure == "module_missing":
        adapter.unlink()
    elif failure == "registry_duplicate":
        registry.write_text('{"observers":[],"observers":[]}')
    elif failure == "backup_outside":
        env["SUPERVISION_CRON_BACKUP_DIR"] = str(root.parent)
    original = cron.read_bytes()
    result = run_installer(fx, ["--all", "--capture-activation"],
                           substitution=failure == "process_substitution", outside=failure == "outside")
    assert result.returncode == 3
    assert cron.read_bytes() == original and not list((root / "logs").iterdir())
    invoked = [json.loads(line) for line in calls.read_text().splitlines()]
    assert all("fetch" not in row and "bash" not in row for row in invoked)
    assert not paths(root)[0].exists()


def test_optin_capture_is_node_writer_and_exact_synthetic_source(installer_fixture):
    fx = installer_fixture
    root, installer, registry, _, calls, cron, _ = fx
    result = run_installer(fx, ["--all", "--capture-activation"])
    assert result.returncode == 0, result.stderr
    base, _ = paths(root)
    receipts = list(base.glob("install-*.json"))
    assert len(receipts) == 1 and len(list((base / "pending").glob("*.json"))) == 1
    row = json.loads(receipts[0].read_bytes())
    assert row["installer_sha256"] == hashlib.sha256(installer.read_bytes()).hexdigest()
    assert row["registry_bytes_sha256"] == hashlib.sha256(registry.read_bytes()).hexdigest()
    assert set(row["selected_cron_entries"]) == set(line for line in cron.read_text().splitlines() if "# epyc-" in line)
    invoked = [json.loads(line) for line in calls.read_text().splitlines()]
    capture_calls = [row for row in invoked if "python3" in row]
    assert len(capture_calls) == 2
    assert all(row[:4] == ["exec", "-u", "node", "epyc-root"] for row in capture_calls)
    assert "preflight" in capture_calls[0] and "capture-install" in capture_calls[1]
    assert all(not ("hub_supervisor.sh" in row and "once" in row) for row in invoked)


@pytest.mark.parametrize("child", ["pending", "consumed", ".activation.lock"])
def test_preflight_symlink_state_refused(fixture, child):
    root, kwargs = fixture
    base, _ = paths(root)
    base.mkdir(parents=True)
    (base / child).symlink_to(root / "logs")
    with pytest.raises(host.ReceiptError, match="symlink"):
        host.preflight_capture(root, kwargs["installer_path"], kwargs["registry_path"],
                               kwargs["backup_path"].parent, kwargs["installer_sha256"])


def test_heartbeat_state_timestamp_mismatch_refused(fixture):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    path = root / "logs/state.json"
    path.write_text(json.dumps({"heartbeat_at": MARKER}))
    before = paths(root)[1].read_bytes()
    with pytest.raises(host.ReceiptError, match="does not match"):
        host.capture_pending_heartbeat(root, path, HEARTBEAT)
    assert paths(root)[1].read_bytes() == before


def test_resealed_heartbeat_chronology_refused(fixture):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    first = heartbeat(root)[0]
    reseal(first, {"heartbeat_at": MARKER})
    with pytest.raises(host.ReceiptError, match="strictly later"):
        host.classify_receipt(json.loads(first.read_bytes()))


def test_non_string_pin_refused(fixture):
    _, kwargs = fixture
    receipt = host.capture_install(**kwargs)
    reseal(receipt, {"supervisor_pin": 1})
    with pytest.raises(host.ReceiptError, match="supervisor_pin"):
        host.classify_receipt(json.loads(receipt.read_bytes()))


def test_unrelated_malformed_observer_is_not_selected(fixture):
    _, kwargs = fixture
    registry = json.loads(kwargs["registry_path"].read_bytes())
    registry["observers"].append({"id": ["unrelated"]})
    kwargs["registry_path"].write_text(json.dumps(registry))
    receipt = host.capture_install(**kwargs)
    assert host.classify_receipt(json.loads(receipt.read_bytes()))["classification"] == "dependency_evidence_only"


@pytest.mark.parametrize("failure", ["state_read", "state_file_fsync", "state_directory_fsync"])
def test_state_read_or_sync_failure_preserves_pending(fixture, monkeypatch, failure):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    base, marker = paths(root)
    before = marker.read_bytes()
    state_path = root / "logs/state.json"
    state_path.write_text(json.dumps({"heartbeat_at": HEARTBEAT}))
    state_inode = state_path.stat().st_ino
    directory_inode = state_path.parent.stat().st_ino
    original_read, original_fsync = os.read, os.fsync

    def read(fd, size):
        if failure == "state_read" and os.fstat(fd).st_ino == state_inode:
            raise OSError("fixture state read refused")
        return original_read(fd, size)

    def sync(fd):
        inode = os.fstat(fd).st_ino
        if (failure == "state_file_fsync" and inode == state_inode) or (
                failure == "state_directory_fsync" and inode == directory_inode):
            raise OSError("fixture state sync refused")
        return original_fsync(fd)

    monkeypatch.setattr(os, "read", read)
    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(OSError, match="fixture state"):
        host.capture_pending_heartbeat(root, state_path, HEARTBEAT)
    assert marker.read_bytes() == before
    assert not (base / f"heartbeat-{INSTALL_ID}.json").exists()
    assert not (base / "consumed").exists()


def test_exact_state_fd_and_directory_synced_before_publication(fixture, monkeypatch):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    state_path = root / "logs/state.json"
    state_path.write_text(json.dumps({"heartbeat_at": HEARTBEAT}))
    state_inode = state_path.stat().st_ino
    directory_inode = state_path.parent.stat().st_ino
    original_read, original_fsync, original_write = os.read, os.fsync, host._write_once
    events = []

    def read(fd, size):
        if os.fstat(fd).st_ino == state_inode:
            events.append(("read_state", fd))
        return original_read(fd, size)

    def sync(fd):
        inode = os.fstat(fd).st_ino
        if inode == state_inode:
            events.append(("sync_state", fd))
        elif inode == directory_inode:
            events.append(("sync_directory", fd))
        return original_fsync(fd)

    def write(root_arg, path, value):
        if value["event"] == "first_heartbeat":
            assert [event[0] for event in events] == ["read_state", "read_state", "sync_state", "sync_directory"]
            assert events[0][1] == events[1][1] == events[2][1]
            events.append(("publish_receipt", None))
        return original_write(root_arg, path, value)

    monkeypatch.setattr(os, "read", read)
    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(host, "_write_once", write)
    assert len(host.capture_pending_heartbeat(root, state_path, HEARTBEAT)) == 1
    assert events[-1][0] == "publish_receipt"


@pytest.mark.parametrize("empty_directory", [False, True])
def test_no_marker_does_not_open_or_sync_state(fixture, monkeypatch, empty_directory):
    root, _ = fixture
    base, marker = paths(root)
    if empty_directory:
        marker.parent.mkdir(parents=True)

    def refuse(*args, **kwargs):
        raise AssertionError("no marker must mean no state/lock I/O")

    monkeypatch.setattr(host, "_read_bytes", refuse)
    monkeypatch.setattr(host, "_lock", refuse)
    assert host.capture_pending_heartbeat(root, root / "absent-state.json", HEARTBEAT) == []
    assert not (base / ".activation.lock").exists()


def hook_tick(root, monkeypatch, dry_run=False):
    monkeypatch.setattr(tick_module, "ROOT", root)
    monkeypatch.setattr(tick_module, "now_iso", lambda: HEARTBEAT)
    return tick_module.Tick(dry_run=dry_run, state_dir=root / "logs/hygiene")


@pytest.mark.parametrize("marker_kind", ["absent", "empty", "nonjson", "symlink"])
def test_tick_hook_no_real_marker_has_zero_adapter_import(fixture, monkeypatch, marker_kind):
    root, _ = fixture
    base, marker = paths(root)
    if marker_kind != "absent":
        marker.parent.mkdir(parents=True)
    if marker_kind == "nonjson":
        marker.with_suffix(".txt").write_text("not a pending marker")
    elif marker_kind == "symlink":
        target = root / "irrelevant.json"
        target.write_text("{}")
        marker.symlink_to(target)
    monkeypatch.setattr(tick_module.importlib.util, "spec_from_file_location",
                        lambda *a: pytest.fail("default hook imported adapter"))
    tick = hook_tick(root, monkeypatch)
    tick.flush()
    assert json.loads(tick.state_path.read_text())["heartbeat_at"] == HEARTBEAT
    assert not list(base.glob("heartbeat-*.json"))
    assert not (base / ".activation.lock").exists()


def test_tick_hook_dry_run_preserves_real_pending_without_import(fixture, monkeypatch):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    marker = paths(root)[1]
    before = marker.read_bytes()
    monkeypatch.setattr(tick_module.importlib.util, "spec_from_file_location",
                        lambda *a: pytest.fail("dry run imported adapter"))
    hook_tick(root, monkeypatch, dry_run=True).flush()
    assert marker.read_bytes() == before
    assert not list(paths(root)[0].glob("heartbeat-*.json"))


def test_tick_hook_after_durable_state_uses_published_code_and_canonical_root(fixture, monkeypatch):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    wrong_adapter = root / "scripts/vidya/adapters/host_supervision_activation.py"
    wrong_adapter.parent.mkdir(parents=True)
    wrong_adapter.write_text("raise AssertionError('canonical working source must not be imported')\n")
    monkeypatch.setattr(tick_module, "CODE_ROOT", ROOT)
    tick = hook_tick(root, monkeypatch)
    tick.flush()
    base, marker = paths(root)
    native = json.loads((base / f"heartbeat-{INSTALL_ID}.json").read_text())
    assert native["state_bytes_sha256"] == hashlib.sha256(tick.state_path.read_bytes()).hexdigest()
    assert native["heartbeat_at"] == json.loads(tick.state_path.read_text())["heartbeat_at"] == HEARTBEAT
    assert native["state_path"] == "logs/hygiene/state.json"
    assert not marker.exists() and (base / "consumed" / marker.name).exists()
    assert host.classify_receipt(native)["classification"] == "dependency_evidence_only"


def test_tick_hook_error_preserves_marker_and_tick_heartbeat(fixture, monkeypatch):
    root, _ = fixture
    base, marker = paths(root)
    marker.parent.mkdir(parents=True)
    marker.write_text('{"invalid":"preserve"}')
    before = marker.read_bytes()
    tick = hook_tick(root, monkeypatch)
    tick.flush()
    assert marker.read_bytes() == before
    assert not list(base.glob("heartbeat-*.json"))
    assert json.loads(tick.state_path.read_text())["heartbeat_at"] == HEARTBEAT
    assert any("capture failed; preserve pending marker" in line for line in tick.lines)


def test_tick_hook_state_write_failure_prevents_capture(fixture, monkeypatch):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    marker = paths(root)[1]
    before = marker.read_bytes()
    tick = hook_tick(root, monkeypatch)
    def deny(path, state):
        raise OSError("synthetic state publication failure")
    monkeypatch.setattr(tick_module, "write_json", deny)
    monkeypatch.setattr(tick_module.importlib.util, "spec_from_file_location",
                        lambda *a: pytest.fail("hook preceded durable state"))
    with pytest.raises(OSError):
        tick.flush()
    assert marker.read_bytes() == before
    assert not list(paths(root)[0].glob("heartbeat-*.json"))


def test_tick_hook_missing_published_adapter_preserves_marker(fixture, monkeypatch):
    root, kwargs = fixture
    host.capture_install(**kwargs)
    marker = paths(root)[1]
    before = marker.read_bytes()
    monkeypatch.setattr(tick_module, "CODE_ROOT", root / "missing-published-code")
    tick = hook_tick(root, monkeypatch)
    tick.flush()
    assert marker.read_bytes() == before
    assert any("capture failed" in line for line in tick.lines)
