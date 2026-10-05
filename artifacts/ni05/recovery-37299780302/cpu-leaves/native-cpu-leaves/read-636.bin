from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

from scripts.lab import quiet_window_lab_plan


def _write_jobs_file(path: Path) -> None:
    doc = {
        "version": 1,
        "schema_version": "lab_jobs.v1",
        "policy": {"direct_repo_writes_allowed": False},
        "jobs": [
            {
                "job_id": "quiet_model_job",
                "title": "Quiet model job",
                "stage": "shadow",
                "enabled": True,
                "risk": "read_only",
                "schedule": {"type": "nightly", "cadence": "daily", "max_runtime_s": 900},
                "input_spec": {"context_modes": ["kb_rag", "source_excerpt"]},
                "output_contract": {"format": "json", "json_schema": {"type": "object"}},
            },
            {
                "job_id": "active_safe_watch",
                "title": "Active-safe watch",
                "stage": "shadow",
                "enabled": True,
                "risk": "read_only",
                "runtime_class": "active_safe_deterministic",
                "active_safe": True,
                "schedule": {
                    "type": "manual_or_nightly",
                    "cadence": "daily",
                    "runtime_class": "active_safe_deterministic",
                },
                "execution": {"mode": "deterministic_command", "command": ["true"]},
                "input_spec": {},
                "output_contract": {"format": "json", "json_schema": {"type": "object"}},
            },
        ],
    }
    path.write_text(yaml.safe_dump(doc, sort_keys=False))


def _args(tmp_path: Path, jobs_file: Path) -> Namespace:
    return Namespace(
        repo_root=str(tmp_path),
        jobs_file=str(jobs_file),
        queue_dir=str(tmp_path / "queue"),
        schedule="nightly",
        max_jobs=2,
        api_url="http://127.0.0.1:8000",
        timeout_s=None,
    )


def test_plan_reports_blocked_quiet_window_without_executing(tmp_path: Path, monkeypatch) -> None:
    jobs_file = tmp_path / "lab_jobs.yaml"
    _write_jobs_file(jobs_file)
    monkeypatch.setattr(
        quiet_window_lab_plan.readiness_report,
        "_quiet_window_status",
        lambda: {"ready": False, "blockers": ["active AutoPilot process count: 1"]},
    )

    report = quiet_window_lab_plan.run_from_args(_args(tmp_path, jobs_file))

    assert report["schema_version"] == "quiet_window_lab_plan.v1"
    assert report["status"] == "blocked"
    assert report["blockers"] == ["active AutoPilot process count: 1"]
    assert [row["job_id"] for row in report["selected_jobs"]] == ["quiet_model_job"]
    assert "active_safe_watch" not in [row["job_id"] for row in report["selected_jobs"]]
    assert "--quiet-window-only" in report["commands"]["run_quiet_window_batch"]
    assert "--execute-chat" in report["commands"]["run_quiet_window_batch"]
    assert "--timeout-s 900.0" in report["commands"]["run_quiet_window_batch"]
    assert report["timeout_s"] == 900.0
    assert "apply_review_batch.py" in report["commands"]["apply_reviewed_verdict_batch_template"]


def test_plan_reports_ready_when_quiet_window_is_clear(tmp_path: Path, monkeypatch) -> None:
    jobs_file = tmp_path / "lab_jobs.yaml"
    _write_jobs_file(jobs_file)
    monkeypatch.setattr(
        quiet_window_lab_plan.readiness_report,
        "_quiet_window_status",
        lambda: {"ready": True, "blockers": []},
    )

    report = quiet_window_lab_plan.run_from_args(_args(tmp_path, jobs_file))

    assert report["status"] == "ready"
    assert report["blockers"] == []
    assert report["quiet_window"]["ready"] is True


def test_production_inventory_includes_quiet_window_lab_plan_watch() -> None:
    root = Path(__file__).resolve().parents[2]
    jobs_doc = yaml.safe_load((root / "orchestration/lab_jobs.yaml").read_text())
    jobs = {job["job_id"]: job for job in jobs_doc["jobs"]}
    job = jobs["quiet_window_lab_plan_watch"]

    assert job["enabled"] is True
    assert job["risk"] == "read_only"
    assert job["active_safe"] is True
    assert job["execution"]["command"] == [
        "python3",
        "scripts/lab/quiet_window_lab_plan.py",
        "--json",
    ]
    schema = job["output_contract"]["json_schema"]
    Draft7Validator.check_schema(schema)
    Draft7Validator(schema).validate(
        {
            "schema_version": "quiet_window_lab_plan.v1",
            "ok": True,
            "status": "blocked",
            "blockers": ["active AutoPilot process count: 1"],
            "selected_jobs": [{"job_id": "handoff_freshness_lint"}],
            "commands": {
                "run_quiet_window_batch": "uv run python scripts/lab/run_shadow_jobs.py",
                "review_pending_items": "uv run python scripts/lab/review_queue_report.py",
                "apply_reviewed_verdict_batch_template": "uv run python scripts/lab/apply_review_batch.py",
            },
        }
    )
