"""Tests for orchestrator stack checkpoint helpers."""

from __future__ import annotations

import json


from scripts.server.stack_checkpoint import (
    checkpoint_create,
    checkpoint_delete,
    checkpoint_list,
    checkpoint_restore,
)
from scripts.server.stack_state import ProcessInfo, save_state_file


def _seed_state(state_file, role: str = "orchestrator", port: int = 8000) -> ProcessInfo:
    process = ProcessInfo(
        role=role,
        pid=123,
        port=port,
        started_at="now",
        model_path="api",
        log_file="api.log",
    )
    save_state_file(state_file, {role: process})
    return process


def test_create_and_list_roundtrip(tmp_path) -> None:
    cp_dir = tmp_path / "checkpoints"
    state_file = tmp_path / "state.json"
    _seed_state(state_file)

    result = checkpoint_create("phase1_baseline", cp_dir, state_file)
    assert "checkpoint_id" in result
    assert result["checkpoint_id"].startswith("phase1_baseline_")

    listed = checkpoint_list(cp_dir)
    assert len(listed) == 1
    assert listed[0]["id"] == result["checkpoint_id"]
    assert listed[0]["name"] == "phase1_baseline"


def test_create_includes_state_when_requested(tmp_path) -> None:
    cp_dir = tmp_path / "cp"
    state_file = tmp_path / "state.json"
    _seed_state(state_file, role="worker", port=8071)

    result = checkpoint_create("with_state", cp_dir, state_file, include_state=True)
    cp_path = cp_dir / f"{result['checkpoint_id']}.json"
    data = json.loads(cp_path.read_text())
    assert "worker" in data["state"]
    assert data["state"]["worker"]["port"] == 8071


def test_create_skips_state_when_disabled(tmp_path) -> None:
    cp_dir = tmp_path / "cp"
    state_file = tmp_path / "state.json"
    _seed_state(state_file)

    result = checkpoint_create("no_state", cp_dir, state_file, include_state=False)
    cp_path = cp_dir / f"{result['checkpoint_id']}.json"
    data = json.loads(cp_path.read_text())
    assert data["state"] == {}


def test_restore_returns_error_when_missing(tmp_path) -> None:
    cp_dir = tmp_path / "cp"
    state_file = tmp_path / "state.json"
    result = checkpoint_restore("nonexistent_ckpt", cp_dir, state_file)
    assert result == {"success": False, "error": "Checkpoint not found: nonexistent_ckpt"}


def test_restore_repopulates_state_file(tmp_path) -> None:
    cp_dir = tmp_path / "cp"
    state_file = tmp_path / "state.json"
    original = _seed_state(state_file, role="frontdoor", port=8070)

    created = checkpoint_create("snap", cp_dir, state_file)

    # Wipe state file, then restore
    state_file.unlink()
    restore_result = checkpoint_restore(created["checkpoint_id"], cp_dir, state_file)
    assert restore_result["success"] is True

    # Verify state was rewritten
    restored = json.loads(state_file.read_text())
    assert restored["frontdoor"]["port"] == original.port


def test_delete_removes_file_and_returns_true(tmp_path) -> None:
    cp_dir = tmp_path / "cp"
    state_file = tmp_path / "state.json"
    _seed_state(state_file)
    created = checkpoint_create("doomed", cp_dir, state_file)

    assert checkpoint_delete(created["checkpoint_id"], cp_dir) is True
    assert not (cp_dir / f"{created['checkpoint_id']}.json").exists()


def test_delete_returns_false_when_missing(tmp_path) -> None:
    cp_dir = tmp_path / "cp"
    cp_dir.mkdir()
    assert checkpoint_delete("never_existed", cp_dir) is False


def test_list_empty_dir_returns_empty_list(tmp_path) -> None:
    cp_dir = tmp_path / "no_such_dir"
    assert checkpoint_list(cp_dir) == []


def test_list_skips_malformed_files(tmp_path) -> None:
    cp_dir = tmp_path / "cp"
    cp_dir.mkdir()
    (cp_dir / "broken.json").write_text("not valid json {{{")
    state_file = tmp_path / "state.json"
    _seed_state(state_file)
    valid = checkpoint_create("ok", cp_dir, state_file)

    listed = checkpoint_list(cp_dir)
    ids = [cp["id"] for cp in listed]
    assert valid["checkpoint_id"] in ids
    assert "broken" not in ids


def test_list_honors_limit_and_newest_first(tmp_path) -> None:
    cp_dir = tmp_path / "cp"
    cp_dir.mkdir()
    # Manually create 3 files with controlled lexical order
    for i, name in enumerate(["aaa.json", "mmm.json", "zzz.json"]):
        (cp_dir / name).write_text(json.dumps({"id": name[:3], "name": name[:3], "created_at": "t"}))

    listed = checkpoint_list(cp_dir, limit=2)
    assert [cp["id"] for cp in listed] == ["zzz", "mmm"]
