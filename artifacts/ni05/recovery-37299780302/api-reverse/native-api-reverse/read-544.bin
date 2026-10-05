from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router import offline_reward_pairwise_collection_status as mod


def _write_manifest(path: Path) -> None:
    payload = {
        "schema_version": "offline_reward_pairwise_collection_window.v1",
        "source_plan_decision": {"status": "expansion_plan_ready"},
        "requires_active_autopilot_absent": True,
        "autopilot_guard": {
            "process_pattern": "scripts/autopilot/autopilot.py start",
            "refusal_exit_code": 75,
        },
        "batch_count": 1,
        "batches": [
            {
                "target": "suite:general:architect_general>frontdoor",
                "command": (
                    "uv run python scripts/benchmark/seed_specialist_routing.py "
                    "--suites general --roles architect_general frontdoor "
                    "--modes direct --sample-size 20 --max-tokens 1024 "
                    "--strict-modes --dry-run "
                    "--output /tmp/a9_<YYYYMMDDTHHMMSSZ>.json"
                ),
                "durable_source_path": "/tmp/a9_<YYYYMMDDTHHMMSSZ>.json",
                "durable_source_path_template": "/tmp/a9_<YYYYMMDDTHHMMSSZ>.json",
            }
        ],
        "post_collection_pipeline": ["uv run python scripts/graph_router/rebuild.py"],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_a9_collection_status_ready_when_manifest_valid_and_no_autopilot(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    monkeypatch.setattr(mod, "_active_processes", lambda pattern: [])

    status = mod.build_status(manifest)

    assert status["ready"] is True
    assert status["status"] == "ready"
    assert status["batch_count"] == 1
    assert status["post_collection_step_count"] == 1
    assert status["blockers"] == []


def test_a9_collection_status_blocks_on_active_autopilot(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    monkeypatch.setattr(
        mod,
        "_active_processes",
        lambda pattern: ["123 python scripts/autopilot/autopilot.py start"],
    )

    status = mod.build_status(manifest)

    assert status["ready"] is False
    assert status["status"] == "blocked"
    assert status["autopilot_guard"]["refusal_exit_code"] == 75
    assert status["blockers"] == [
        "active AutoPilot process(es): 123 python scripts/autopilot/autopilot.py start"
    ]


def test_a9_collection_status_invalidates_missing_dry_run(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["batches"][0]["command"] = payload["batches"][0]["command"].replace(
        " --dry-run", ""
    )
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(mod, "_active_processes", lambda pattern: [])

    status = mod.build_status(manifest)

    assert status["ready"] is False
    assert status["status"] == "invalid"
    assert status["blockers"] == [
        "suite:general:architect_general>frontdoor: command is missing --dry-run"
    ]


def test_a9_collection_status_reports_no_runnable_batches(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["batch_count"] = 0
    payload["batches"] = []
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(mod, "_active_processes", lambda pattern: [])

    status = mod.build_status(manifest)

    assert status["ready"] is False
    assert status["status"] == "no_runnable_batches"
    assert status["blockers"] == []
    assert status["warnings"] == ["manifest has no runnable collection batches"]


def test_a9_collection_status_no_runnable_batches_overrides_active_autopilot(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["batch_count"] = 0
    payload["batches"] = []
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        mod,
        "_active_processes",
        lambda pattern: ["123 python scripts/autopilot/autopilot.py start"],
    )

    status = mod.build_status(manifest)

    assert status["ready"] is False
    assert status["status"] == "no_runnable_batches"
    assert status["blockers"] == []
    assert status["autopilot_guard"]["active_processes"] == [
        "123 python scripts/autopilot/autopilot.py start"
    ]


def test_a9_collection_status_main_uses_guard_exit_code(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    monkeypatch.setattr(
        mod,
        "_active_processes",
        lambda pattern: ["123 python scripts/autopilot/autopilot.py start"],
    )

    assert mod.main(["--manifest", str(manifest)]) == 75
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "blocked"
