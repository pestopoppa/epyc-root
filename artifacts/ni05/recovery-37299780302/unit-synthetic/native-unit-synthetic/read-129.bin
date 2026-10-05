"""Tests for the P0.3 AutoPilot blacklist purge helper."""

from __future__ import annotations

import json

import yaml

from scripts.autopilot import blacklist_purge_plan as purge


def _sample_document() -> dict:
    return {
        "blacklist": [
            {
                "pattern": {"type": "structural_experiment", "flags": {"lookup_cache": True}},
                "reason": "hardware crash",
                "severity": "crash",
                "source_trial": -1,
            },
            {
                "pattern": {
                    "type": "structural_experiment",
                    "flags": {"architect_delegation": True},
                },
                "reason": "Auto-blacklisted: 3 consecutive failures ending at trial 655",
                "source_trial": 655,
            },
            {
                "pattern": {
                    "type": "structural_experiment",
                    "flags": {"specialist_routing": True},
                },
                "reason": "Auto-blacklisted: 3 consecutive failures ending at trial 664",
                "source_trial": 664,
            },
            {
                "pattern": {"type": "prompt_mutation", "file": "frontdoor.md"},
                "reason": "MANUAL FREEZE: remove after restart",
                "severity": "corruption",
                "source_trial": -1,
            },
            {
                "pattern": {"type": "gepa_optimize", "file": "frontdoor.md"},
                "reason": "MANUAL FREEZE companion",
                "severity": "corruption",
                "source_trial": -1,
            },
            {
                "pattern": {
                    "type": "structural_experiment",
                    "flags": {"specialist_routing": False},
                },
                "reason": "Auto-blacklisted: 3 consecutive failures ending at trial 864",
                "source_trial": 864,
            },
            {
                "pattern": {"type": "seed_batch", "n_questions": 16},
                "reason": "recent independent failure",
                "source_trial": 1067,
            },
        ]
    }


def test_build_purge_report_targets_only_p0_3_entries() -> None:
    entries = _sample_document()["blacklist"]

    report = purge.build_purge_report(entries)

    assert report["removable_count"] == 5
    assert report["entry_count_after"] == 2
    assert report["unmatched_targets"] == []
    assert {item["source_trial"] for item in report["removable_entries"]} == {
        -1,
        655,
        664,
        864,
    }
    assert report["retryable_count"] == 3
    assert {item["target_key"] for item in report["retryable_entries"]} == {
        "architect_delegation_t655_tool_use_axis_bug",
        "specialist_routing_t664_tool_use_axis_bug",
        "specialist_routing_t864_tool_use_axis_bug",
    }
    assert all(item["source_trial"] != -1 for item in report["retryable_entries"])
    assert "lookup_cache" not in json.dumps(report["removable_entries"])
    assert "seed_batch" not in json.dumps(report["removable_entries"])


def test_apply_purge_preserves_non_target_entries() -> None:
    document = _sample_document()

    next_document, report = purge.apply_purge(document)

    assert report["applied"] is True
    assert report["removable_count"] == 5
    assert next_document["blacklist"] == [
        document["blacklist"][0],
        document["blacklist"][-1],
    ]


def test_main_apply_requires_exact_approval_token(tmp_path, capsys) -> None:
    path = tmp_path / "failure_blacklist.yaml"
    original = yaml.dump(_sample_document(), sort_keys=False)
    path.write_text(original, encoding="utf-8")

    code = purge.main(["--blacklist", str(path), "--apply", "--approval-token", "wrong"])

    assert code == 2
    assert path.read_text(encoding="utf-8") == original
    assert "requires --approval-token" in capsys.readouterr().err


def test_main_apply_writes_backup_and_report(tmp_path) -> None:
    path = tmp_path / "failure_blacklist.yaml"
    path.write_text(yaml.dump(_sample_document(), sort_keys=False), encoding="utf-8")
    report_path = tmp_path / "report.json"

    code = purge.main(
        [
            "--blacklist",
            str(path),
            "--apply",
            "--approval-token",
            purge.APPROVAL_TOKEN,
            "--backup-dir",
            str(tmp_path / "backups"),
            "--report-json",
            str(report_path),
        ]
    )

    assert code == 0
    next_document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert len(next_document["blacklist"]) == 2
    backups = list((tmp_path / "backups").glob("failure_blacklist.yaml.bak-p0_3-*"))
    assert len(backups) == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["applied"] is True
    assert report["backup_path"] == str(backups[0])
