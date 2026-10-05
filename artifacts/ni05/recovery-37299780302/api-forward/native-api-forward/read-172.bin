from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.analysis import collect_offline_reward_pairwise_audit_target_live as live


def _write_manifest(path: Path) -> None:
    payload = {
        "schema_version": "offline_reward_pairwise_collection_window.v1",
        "batch_count": 2,
        "batches": [
            {
                "target": "suite:general:architect_general>frontdoor",
                "command": (
                    "uv run python scripts/benchmark/seed_specialist_routing.py "
                    "--suites general --roles architect_general frontdoor --modes direct "
                    "--sample-size 20 --max-tokens 1024 --strict-modes --dry-run "
                    "--output /tmp/a9/seeding_a9_suite_general_<YYYYMMDDTHHMMSSZ>.json"
                ),
            },
            {
                "target": "suite:hotpotqa:architect_general>frontdoor",
                "command": (
                    "uv run python scripts/benchmark/seed_specialist_routing.py "
                    "--suites hotpotqa --roles architect_general frontdoor --modes direct "
                    "--sample-size 20 --max-tokens 1024 --strict-modes --dry-run "
                    "--output /tmp/a9/seeding_a9_suite_hotpotqa_<YYYYMMDDTHHMMSSZ>.json"
                ),
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_live_batch_commands_removes_dry_run_and_substitutes_timestamp(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "collection_manifest.json"
    _write_manifest(manifest)

    batches = live.build_live_batch_commands(manifest, timestamp="20260628T120000Z")

    assert len(batches) == 2
    assert "--dry-run" not in batches[0][1]
    assert "20260628T120000Z" in batches[0][2].name
    assert "20260628T120000Z" in batches[1][2].name


def test_main_blocked_by_invalid_timestamp(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "collection_manifest.json"
    _write_manifest(manifest)
    monkeypatch.setenv("A9_COLLECTION_TIMESTAMP", "bad")
    monkeypatch.setattr(live, "_active_autopilot_processes", lambda pattern="x": [])

    assert live.main(["--manifest", str(manifest)]) == 64


def test_main_blocks_when_autopilot_is_active(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "collection_manifest.json"
    _write_manifest(manifest)
    monkeypatch.delenv("A9_COLLECTION_TIMESTAMP", raising=False)

    monkeypatch.setattr(
        live,
        "_active_autopilot_processes",
        lambda pattern="x": ["123 python scripts/autopilot/autopilot.py start"],
    )

    assert live.main(["--manifest", str(manifest)]) == 75


def test_main_executes_live_commands_without_dry_run(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "collection_manifest.json"
    _write_manifest(manifest)
    monkeypatch.setenv("A9_COLLECTION_TIMESTAMP", "20260628T120000Z")
    monkeypatch.setattr(
        live,
        "_active_autopilot_processes",
        lambda pattern="x": [],
    )

    calls: list[list[str]] = []

    def fake_run(cmd, *, check=False, cwd=None, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(live.subprocess, "run", fake_run)

    rc = live.main(["--manifest", str(manifest)])

    assert rc == 0
    assert calls == [
        [
            "uv",
            "run",
            "python",
            "scripts/benchmark/seed_specialist_routing.py",
            "--suites",
            "general",
            "--roles",
            "architect_general",
            "frontdoor",
            "--modes",
            "direct",
            "--sample-size",
            "20",
            "--max-tokens",
            "1024",
            "--strict-modes",
            "--output",
            "/tmp/a9/seeding_a9_suite_general_20260628T120000Z.json",
        ],
        [
            "uv",
            "run",
            "python",
            "scripts/benchmark/seed_specialist_routing.py",
            "--suites",
            "hotpotqa",
            "--roles",
            "architect_general",
            "frontdoor",
            "--modes",
            "direct",
            "--sample-size",
            "20",
            "--max-tokens",
            "1024",
            "--strict-modes",
            "--output",
            "/tmp/a9/seeding_a9_suite_hotpotqa_20260628T120000Z.json",
        ],
    ]
