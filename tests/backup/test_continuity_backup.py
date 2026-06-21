import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "backup"))

import continuity_backup as continuity_backup_module  # noqa: E402
from continuity_backup import check_latest_snapshot, create_snapshot, verify_restore  # noqa: E402


def _write_manifest(manifest: Path, repo: Path, *, paths: list[str] | None = None) -> None:
    manifest.write_text(
        yaml.safe_dump(
            {
                "repos": {"test-repo": str(repo)},
                "tiers": {
                    "T0_irreplaceable": [
                        {
                            "id": "state",
                            "repo": "test-repo",
                            "paths": paths or ["state.json"],
                            "copy_mode": "file",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )


def test_verify_restore_compares_restored_file_to_snapshot_not_live_source(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source_file = repo / "state.json"
    source_file.write_text('{"value": "live-after-snapshot"}\n', encoding="utf-8")

    snapshot = tmp_path / "snapshot"
    snapshot_file = snapshot / "test-repo" / "state.json"
    snapshot_file.parent.mkdir(parents=True)
    snapshot_file.write_text('{"value": "snapshot"}\n', encoding="utf-8")

    manifest = tmp_path / "MANIFEST.yaml"
    _write_manifest(manifest, repo)

    restore_root = tmp_path / "restore"

    exit_code, lines = verify_restore(
        manifest,
        snapshot,
        restore_root=str(restore_root),
        tier_csv="T0_irreplaceable",
    )

    assert exit_code == 0, lines
    assert (restore_root / "test-repo" / "state.json").read_text(encoding="utf-8") == (
        '{"value": "snapshot"}\n'
    )


def test_create_snapshot_refuses_same_device_by_default(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "state.json").write_text('{"value": "live"}\n', encoding="utf-8")
    manifest = tmp_path / "MANIFEST.yaml"
    _write_manifest(manifest, repo)

    exit_code, lines = create_snapshot(
        manifest,
        tmp_path / "target",
        snapshot_name="snap",
    )

    assert exit_code == 1
    assert any("shares storage/backing device" in line for line in lines)
    assert not (tmp_path / "target" / "snap").exists()


def test_create_snapshot_layout_verifies_with_explicit_test_override(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "state.json").write_text('{"value": "snapshot"}\n', encoding="utf-8")
    manifest = tmp_path / "MANIFEST.yaml"
    _write_manifest(manifest, repo)

    target_root = tmp_path / "target"
    exit_code, lines = create_snapshot(
        manifest,
        target_root,
        snapshot_name="snap",
        allow_same_device=True,
    )

    assert exit_code == 0, lines
    snapshot_root = target_root / "snap"
    assert (snapshot_root / "test-repo" / "state.json").read_text(encoding="utf-8") == (
        '{"value": "snapshot"}\n'
    )

    verify_code, verify_lines = verify_restore(
        manifest,
        snapshot_root,
        restore_root=str(tmp_path / "restore"),
    )
    assert verify_code == 0, verify_lines


def test_create_snapshot_cleans_up_partial_staging_on_copy_failure(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "state.json").write_text('{"value": "snapshot"}\n', encoding="utf-8")
    nested = repo / "nested"
    nested.mkdir()
    (nested / "other.json").write_text('{"value": "nested"}\n', encoding="utf-8")

    manifest = tmp_path / "MANIFEST.yaml"
    _write_manifest(manifest, repo, paths=["state.json", "nested/other.json"])

    original_copy = continuity_backup_module._copy_file_to_snapshot
    call_count = {"count": 0}

    def flaky_copy(source, destination):
        call_count["count"] += 1
        if call_count["count"] == 2:
            raise OSError("simulated write failure")
        return original_copy(source, destination)

    monkeypatch.setattr(continuity_backup_module, "_copy_file_to_snapshot", flaky_copy)

    target_root = tmp_path / "target"
    exit_code, lines = create_snapshot(
        manifest,
        target_root,
        snapshot_name="snap",
        allow_same_device=True,
    )

    assert exit_code == 1, lines
    assert not (target_root / "snap").exists()
    assert list(target_root.iterdir()) == []


def test_check_latest_snapshot_verifies_newest_snapshot(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source_file = repo / "state.json"
    source_file.write_text('{"value": "old"}\n', encoding="utf-8")
    manifest = tmp_path / "MANIFEST.yaml"
    _write_manifest(manifest, repo)

    target_root = tmp_path / "target"
    old_code, old_lines = create_snapshot(
        manifest,
        target_root,
        snapshot_name="old",
        allow_same_device=True,
    )
    assert old_code == 0, old_lines

    source_file.write_text('{"value": "new"}\n', encoding="utf-8")
    new_code, new_lines = create_snapshot(
        manifest,
        target_root,
        snapshot_name="new",
        allow_same_device=True,
    )
    assert new_code == 0, new_lines

    old_snapshot = target_root / "old"
    new_snapshot = target_root / "new"
    old_time = new_snapshot.stat().st_mtime - 60
    old_snapshot.touch()
    new_snapshot.touch()
    old_snapshot_stat_time = old_time
    new_snapshot_stat_time = old_time + 60
    import os

    os.utime(old_snapshot, (old_snapshot_stat_time, old_snapshot_stat_time))
    os.utime(new_snapshot, (new_snapshot_stat_time, new_snapshot_stat_time))

    exit_code, lines = check_latest_snapshot(
        manifest,
        target_root,
        restore_root=str(tmp_path / "restore"),
        max_age_days=1,
    )

    assert exit_code == 0, lines
    assert f"latest_snapshot_root={new_snapshot}" in lines
    assert (tmp_path / "restore" / "test-repo" / "state.json").read_text(encoding="utf-8") == (
        '{"value": "new"}\n'
    )


def test_check_latest_snapshot_fails_when_no_snapshots_exist(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    manifest = tmp_path / "MANIFEST.yaml"
    _write_manifest(manifest, repo)

    exit_code, lines = check_latest_snapshot(
        manifest,
        tmp_path / "empty-target",
        max_age_days=1,
    )

    assert exit_code == 1
    assert any("no continuity snapshots found" in line for line in lines)


def test_check_latest_snapshot_enforces_age_gate(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "state.json").write_text('{"value": "snapshot"}\n', encoding="utf-8")
    manifest = tmp_path / "MANIFEST.yaml"
    _write_manifest(manifest, repo)

    target_root = tmp_path / "target"
    create_code, create_lines = create_snapshot(
        manifest,
        target_root,
        snapshot_name="stale",
        allow_same_device=True,
    )
    assert create_code == 0, create_lines

    snapshot = target_root / "stale"
    import os

    stale_time = snapshot.stat().st_mtime - (3 * 24 * 3600)
    os.utime(snapshot, (stale_time, stale_time))

    exit_code, lines = check_latest_snapshot(
        manifest,
        target_root,
        max_age_days=1,
    )

    assert exit_code == 1
    assert any("snapshot exceeds max age" in line for line in lines)
