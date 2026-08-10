from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.vidya import autopilot_settled


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _trial(trial_id: int, *, corrupted: str = "") -> dict:
    row = {
        "trial_id": trial_id,
        "timestamp": "2026-08-10T12:00:00+00:00",
        "action_type": "numeric_trial",
        "quality": 1.5,
        "speed": 10.0,
        "cost": 1.0,
        "reliability": 1.0,
        "config_snapshot": {"n_questions": 10},
        "eval_details": {
            "objective_policy_live": {"policy": "task-rate-v1"},
            "details": {"quality_denominator": 10},
        },
        "metric_schema_version": 1,
        "harness_metrics": {"schema_version": 1},
        "git_tag": "autopilot/trial-test",
        "bug_corrupted_by": corrupted,
    }
    digest = hashlib.sha256(
        json.dumps(row, sort_keys=True, default=str, allow_nan=False).encode()
    ).hexdigest()
    row["measurement"] = {
        "protocol_id": "autopilot/metric-v1+harness-v1+task-rate-v1",
        "reps": 10,
        "reps_basis": "scored:quality_denominator",
        "category": "CANDIDATE",
        "metric_directions": {"quality": "higher_better"},
        "date": "2026-08-10",
        "attestation": {
            "locator": f"autopilot_journal.jsonl#trial-{trial_id}",
            "sha256": digest,
            "git_tag": "autopilot/trial-test",
        },
    }
    return row


def test_resolution_is_sealed_when_measurement_tuple_is_witnessed(tmp_path, monkeypatch):
    orch = tmp_path / "repos" / "epyc-orchestrator"
    journal = orch / "orchestration" / "autopilot_journal.jsonl"
    _write(journal, [_trial(7)])
    resolutions = orch / "orchestration" / "operator_hypothesis_resolutions.jsonl"
    _write(
        resolutions,
        [{"hypothesis_id": "h1", "status": "refuted", "evidence_trial_ids": [7]}],
    )
    monkeypatch.setattr(autopilot_settled, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(autopilot_settled.sys.modules["measurement_record"], "REPO_ROOT", tmp_path)

    payload = autopilot_settled.resolution_standings(
        orch_root=orch, resolutions_path=resolutions
    )

    assert payload["resolutions"][0]["effective_standing"] == "sealed"
    assert payload["resolutions"][0]["trials"][0]["grade"] == {
        "Q": "Witnessed",
        "T": "Attested",
    }


def test_supersession_reopens_resolution_for_review(tmp_path):
    orch = tmp_path / "repos" / "epyc-orchestrator"
    journal = orch / "orchestration" / "autopilot_journal.jsonl"
    _write(
        journal,
        [
            _trial(8),
            {
                "type": "supersession",
                "target_trial_ids": [8],
                "fields": {"bug_corrupted_by": "scorer_bug"},
            },
        ],
    )
    resolutions = orch / "orchestration" / "operator_hypothesis_resolutions.jsonl"
    _write(
        resolutions,
        [{"hypothesis_id": "h2", "status": "confirmed", "evidence_trial_ids": [8]}],
    )

    payload = autopilot_settled.resolution_standings(
        orch_root=orch, resolutions_path=resolutions
    )

    row = payload["resolutions"][0]
    assert row["effective_standing"] == "review_required"
    assert row["trials"][0]["state"] == "invalidated"
    assert "RETRACTION/IDENTITY ALERT" in autopilot_settled.render(payload)


def test_duplicate_trial_ids_fail_explicitly(tmp_path):
    orch = tmp_path / "repos" / "epyc-orchestrator"
    for name in ("autopilot_journal.jsonl", "autopilot_journal_1.jsonl"):
        _write(orch / "orchestration" / name, [_trial(9)])
    resolutions = orch / "orchestration" / "operator_hypothesis_resolutions.jsonl"
    _write(
        resolutions,
        [{"hypothesis_id": "h3", "status": "refuted", "evidence_trial_ids": [9]}],
    )

    payload = autopilot_settled.resolution_standings(
        orch_root=orch, resolutions_path=resolutions
    )

    assert payload["resolutions"][0]["effective_standing"] == "review_required"
    assert payload["resolutions"][0]["trials"][0]["state"] == "ambiguous"
