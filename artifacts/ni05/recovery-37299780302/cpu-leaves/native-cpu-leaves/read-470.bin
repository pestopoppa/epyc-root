from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator

from scripts.lab import run_shadow_jobs


def _job(
    job_id: str,
    *,
    enabled: bool = True,
    gated: bool = False,
    active_safe: bool = False,
    risk: str = "read_only",
) -> dict:
    job = {
        "job_id": job_id,
        "stage": "shadow",
        "enabled": enabled,
        "risk": risk,
        "schedule": {"type": "nightly", "cadence": "daily"},
    }
    if gated:
        job["gates"] = ["frontier-f5-intake-injection-hardening"]
    if active_safe:
        job["active_safe"] = True
        job["runtime_class"] = "active_safe_deterministic"
        job["execution"] = {"mode": "deterministic_command", "command": ["true"]}
    return job


def test_select_jobs_defaults_to_enabled_ungated_nightly() -> None:
    jobs_doc = {
        "jobs": [
            _job("enabled_1"),
            _job("disabled", enabled=False),
            _job("gated", gated=True),
            _job("enabled_2"),
        ]
    }

    selected = run_shadow_jobs.select_jobs(
        jobs_doc,
        schedule="nightly",
        job_ids=[],
        include_disabled=False,
        allow_gated=False,
        max_jobs=2,
    )

    assert [job["job_id"] for job in selected] == ["enabled_1", "enabled_2"]


def test_select_jobs_can_include_disabled_and_gated_when_explicit() -> None:
    jobs_doc = {"jobs": [_job("disabled", enabled=False), _job("gated", gated=True)]}

    selected = run_shadow_jobs.select_jobs(
        jobs_doc,
        schedule="nightly",
        job_ids=[],
        include_disabled=True,
        allow_gated=True,
        max_jobs=0,
    )

    assert [job["job_id"] for job in selected] == ["disabled", "gated"]


def test_select_jobs_active_safe_only_requires_read_only_deterministic() -> None:
    jobs_doc = {
        "jobs": [
            _job("model_chat"),
            _job("active_safe", active_safe=True),
            _job("write_reviewed", active_safe=True, risk="write_reviewed"),
        ]
    }

    selected = run_shadow_jobs.select_jobs(
        jobs_doc,
        schedule="nightly",
        job_ids=[],
        include_disabled=False,
        allow_gated=False,
        active_safe_only=True,
        max_jobs=0,
    )

    assert [job["job_id"] for job in selected] == ["active_safe"]


def test_select_jobs_quiet_window_only_excludes_active_safe_jobs() -> None:
    jobs_doc = {
        "jobs": [
            _job("model_chat"),
            _job("active_safe", active_safe=True),
            _job("second_model_chat"),
        ]
    }

    selected = run_shadow_jobs.select_jobs(
        jobs_doc,
        schedule="nightly",
        job_ids=[],
        include_disabled=False,
        allow_gated=False,
        quiet_window_only=True,
        max_jobs=0,
    )

    assert [job["job_id"] for job in selected] == ["model_chat", "second_model_chat"]


def test_select_jobs_rejects_conflicting_runtime_filters() -> None:
    with pytest.raises(run_shadow_jobs.ShadowBatchError, match="at most one"):
        run_shadow_jobs.select_jobs(
            {"jobs": [_job("active_safe", active_safe=True)]},
            schedule="nightly",
            job_ids=[],
            include_disabled=False,
            allow_gated=False,
            active_safe_only=True,
            quiet_window_only=True,
            max_jobs=0,
        )


def test_requested_unrunnable_job_fails() -> None:
    jobs_doc = {"jobs": [_job("disabled", enabled=False)]}

    with pytest.raises(run_shadow_jobs.ShadowBatchError, match="not runnable"):
        run_shadow_jobs.select_jobs(
            jobs_doc,
            schedule="nightly",
            job_ids=["disabled"],
            include_disabled=False,
            allow_gated=False,
            max_jobs=2,
        )


def test_run_from_args_requires_execution_mode(tmp_path, monkeypatch) -> None:
    jobs_file = tmp_path / "lab_jobs.yaml"
    jobs_file.write_text("jobs: []\n")
    args = Namespace(
        repo_root=str(tmp_path),
        jobs_file=str(jobs_file),
        dry_run_stub=False,
        execute_chat=False,
        execute_command=False,
    )

    with pytest.raises(run_shadow_jobs.ShadowBatchError, match="execute-command"):
        run_shadow_jobs.run_from_args(args)


def test_production_inventory_includes_outcome_progress_active_safe_job() -> None:
    root = Path(__file__).resolve().parents[2]
    jobs_doc = yaml.safe_load((root / "orchestration/lab_jobs.yaml").read_text())
    jobs = {job["job_id"]: job for job in jobs_doc["jobs"]}
    job = jobs["autopilot_outcome_progress_watch"]

    selected = run_shadow_jobs.select_jobs(
        jobs_doc,
        schedule="nightly",
        job_ids=[],
        include_disabled=False,
        allow_gated=False,
        active_safe_only=True,
        max_jobs=0,
    )

    assert job["enabled"] is True
    assert job["risk"] == "read_only"
    assert run_shadow_jobs.is_active_safe_job(job) is True
    assert run_shadow_jobs.execution_mode(job) == "deterministic_command"
    assert "autopilot_outcome_progress_watch" in [item["job_id"] for item in selected]
    assert job["execution"]["command"] == [
        "python3",
        "scripts/autopilot/phase_health_report.py",
        "--json",
        "--require-outcome-progress",
    ]

    schema = job["output_contract"]["json_schema"]
    Draft7Validator.check_schema(schema)
    Draft7Validator(schema).validate(
        {
            "ok": False,
            "status": "outcome_stalled",
            "blockers": ["frontier admission stale"],
            "outcome_progress": {
                "status": "attention",
                "blockers": ["frontier admission stale"],
                "latest_trial_id": 1206,
                "latest_frontier_trial_id": 1005,
                "latest_promotion_trial_id": 969,
                "trials_since_frontier": 201,
                "trials_since_promotion": 237,
                "rates": {
                    "keepable_rate": {"count": 0, "rate": 0.0, "total": 78},
                    "wasted_eval_rate": {"count": 54, "rate": 0.692, "total": 78},
                },
            },
        }
    )


def test_production_inventory_includes_planner_provider_active_safe_job() -> None:
    root = Path(__file__).resolve().parents[2]
    jobs_doc = yaml.safe_load((root / "orchestration/lab_jobs.yaml").read_text())
    jobs = {job["job_id"]: job for job in jobs_doc["jobs"]}
    job = jobs["autopilot_planner_provider_watch"]

    selected = run_shadow_jobs.select_jobs(
        jobs_doc,
        schedule="nightly",
        job_ids=[],
        include_disabled=False,
        allow_gated=False,
        active_safe_only=True,
        max_jobs=0,
    )

    assert job["enabled"] is True
    assert job["risk"] == "read_only"
    assert run_shadow_jobs.is_active_safe_job(job) is True
    assert run_shadow_jobs.execution_mode(job) == "deterministic_command"
    assert "autopilot_planner_provider_watch" in [item["job_id"] for item in selected]
    assert job["execution"]["command"] == [
        "python3",
        "scripts/autopilot/planner_provider_health_report.py",
        "--json",
    ]

    schema = job["output_contract"]["json_schema"]
    Draft7Validator.check_schema(schema)
    Draft7Validator(schema).validate(
        {
            "schema_version": "autopilot_planner_provider_health.v1",
            "ok": True,
            "status": "healthy",
            "blockers": [],
            "providers": {
                "local_frontdoor": {
                    "starts": 1,
                    "ends": 1,
                    "failures": 0,
                }
            },
            "local": {"draft_successes": 1, "critique_successes": 1},
            "critic_decisions": {"approve": 1},
            "draft_actions": {"deep_eval": 1},
            "recent_issues": [],
        }
    )
    Draft7Validator(schema).validate(
        {
            "schema_version": "autopilot_planner_provider_health.v1",
            "ok": True,
            "status": "waiting_for_planner_turn",
            "blockers": [],
            "providers": {},
            "local": {"draft_successes": 0, "critique_successes": 0},
            "critic_decisions": {},
            "draft_actions": {},
            "recent_issues": [],
            "window": {
                "event_count": 0,
                "raw_event_count": 1,
                "phase": "dispatch_action",
                "action_type": "numeric_trial",
                "no_event_reason": "current phase is dispatch_action",
            },
        }
    )


def test_production_inventory_includes_quiet_window_queue_active_safe_job() -> None:
    root = Path(__file__).resolve().parents[2]
    jobs_doc = yaml.safe_load((root / "orchestration/lab_jobs.yaml").read_text())
    jobs = {job["job_id"]: job for job in jobs_doc["jobs"]}
    job = jobs["quiet_window_queue_watch"]

    selected = run_shadow_jobs.select_jobs(
        jobs_doc,
        schedule="nightly",
        job_ids=[],
        include_disabled=False,
        allow_gated=False,
        active_safe_only=True,
        max_jobs=0,
    )

    assert job["enabled"] is True
    assert job["risk"] == "read_only"
    assert run_shadow_jobs.is_active_safe_job(job) is True
    assert run_shadow_jobs.execution_mode(job) == "deterministic_command"
    assert "quiet_window_queue_watch" in [item["job_id"] for item in selected]
    assert job["execution"]["command"] == [
        "python3",
        "scripts/lab/quiet_window_queue_report.py",
        "--json",
    ]

    schema = job["output_contract"]["json_schema"]
    Draft7Validator.check_schema(schema)
    Draft7Validator(schema).validate(
        {
            "schema_version": "quiet_window_queue_report.v1",
            "ok": True,
            "status": "ok",
            "blockers": [],
            "findings": [],
            "checked_files": ["handoffs/active/master-handoff-index.md"],
        }
    )


def test_production_inventory_includes_lab_review_queue_active_safe_job() -> None:
    root = Path(__file__).resolve().parents[2]
    jobs_doc = yaml.safe_load((root / "orchestration/lab_jobs.yaml").read_text())
    jobs = {job["job_id"]: job for job in jobs_doc["jobs"]}
    job = jobs["lab_review_queue_watch"]

    selected = run_shadow_jobs.select_jobs(
        jobs_doc,
        schedule="nightly",
        job_ids=[],
        include_disabled=False,
        allow_gated=False,
        active_safe_only=True,
        max_jobs=0,
    )

    assert job["enabled"] is True
    assert job["risk"] == "read_only"
    assert run_shadow_jobs.is_active_safe_job(job) is True
    assert run_shadow_jobs.execution_mode(job) == "deterministic_command"
    assert "lab_review_queue_watch" in [item["job_id"] for item in selected]
    assert job["execution"]["command"] == [
        "python3",
        "scripts/lab/review_queue_report.py",
        "--json",
    ]

    schema = job["output_contract"]["json_schema"]
    Draft7Validator.check_schema(schema)
    Draft7Validator(schema).validate(
        {
            "schema_version": "lab_review_queue_report.v1",
            "ok": True,
            "status": "attention",
            "blockers": [],
            "summary": {
                "task_records": 2,
                "verdicts": 1,
                "pending_reviews": 1,
                "pending_reviews_by_class": {"review_candidate": 1},
                "pending_review_candidates": 1,
                "pending_active_safe": 0,
            },
            "pending_items": [],
            "review_batch_template": [],
            "review_batch_template_jsonl": "",
        }
    )
