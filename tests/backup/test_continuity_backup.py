import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "backup"))

from continuity_backup import verify_restore  # noqa: E402


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
    manifest.write_text(
        yaml.safe_dump(
            {
                "repos": {"test-repo": str(repo)},
                "tiers": {
                    "T0_irreplaceable": [
                        {
                            "id": "state",
                            "repo": "test-repo",
                            "paths": ["state.json"],
                            "copy_mode": "file",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

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
