from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import yaml

from scripts.lab import auto_review_active_safe
from scripts.lab import review_queue_report


def _write_jobs(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "schema_version": "lab_jobs.v1",
                "jobs": [
                    {
                        "job_id": "active_watch",
                        "stage": "shadow",
                        "enabled": True,
                        "risk": "read_only",
                        "runtime_class": "active_safe_deterministic",
                        "active_safe": True,
                        "schedule": {"type": "manual_or_nightly"},
                        "execution": {"mode": "deterministic_command", "command": ["true"]},
                        "input_spec": {"sources": []},
                        "output_contract": {"format": "json", "json_schema": {"type": "object"}},
                    },
                    {
                        "job_id": "model_job",
                        "stage": "shadow",
                        "enabled": True,
                        "risk": "read_only",
                        "schedule": {"type": "nightly"},
                        "input_spec": {"sources": []},
                        "output_contract": {"format": "json", "json_schema": {"type": "object"}},
                    },
                ],
            },
            sort_keys=False,
        )
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _seed_queue(tmp_path: Path) -> tuple[Path, Path]:
    jobs = tmp_path / "lab_jobs.yaml"
    queue = tmp_path / "queue"
    _write_jobs(jobs)
    _write_json(queue / "active_watch" / "active-1" / "output.json", {"ok": True})
    _write_json(queue / "model_job" / "model-1" / "output.json", {"ok": True})
    _write_jsonl(
        queue / "task_records.jsonl",
        [
            {
                "job_id": "active_watch",
                "run_id": "active-1",
                "stage": "shadow",
                "artifacts": {"output": "active_watch/active-1/output.json"},
            },
            {
                "job_id": "model_job",
                "run_id": "model-1",
                "stage": "shadow",
                "artifacts": {"output": "model_job/model-1/output.json"},
            },
        ],
    )
    return jobs, queue


def _args(tmp_path: Path, jobs: Path, queue: Path, *, apply: bool) -> Namespace:
    return Namespace(
        repo_root=str(tmp_path),
        jobs_file=str(jobs),
        queue_dir=str(queue),
        task_records_file=str(queue / "task_records.jsonl"),
        verdicts_file=str(queue / "review_verdicts.jsonl"),
        max_items=100,
        apply=apply,
    )


def test_auto_review_active_safe_dry_run_does_not_mutate(tmp_path: Path) -> None:
    jobs, queue = _seed_queue(tmp_path)

    report = auto_review_active_safe.run_from_args(_args(tmp_path, jobs, queue, apply=False))

    assert report["ok"] is True
    assert report["summary"]["planned"] == 1
    assert report["planned"][0]["job_id"] == "active_watch"
    assert report["planned"][0]["write_gold_tuple"] is False
    assert not (queue / "review_verdicts.jsonl").exists()


def test_auto_review_active_safe_applies_without_gold_tuple(tmp_path: Path) -> None:
    jobs, queue = _seed_queue(tmp_path)

    report = auto_review_active_safe.run_from_args(_args(tmp_path, jobs, queue, apply=True))

    assert report["ok"] is True
    assert report["summary"]["applied"] == 1
    verdict = json.loads((queue / "review_verdicts.jsonl").read_text().splitlines()[0])
    assert verdict["job_id"] == "active_watch"
    assert verdict["reviewer"] == "automated"
    assert verdict["evidence_type"] == "deterministic_review"
    assert "tuple_path" not in verdict
    assert (queue / "verdict_artifacts" / "active_watch" / "active-1.json").exists()
    assert not (queue / "gold_tuples").exists()

    pending = review_queue_report.run_from_args(
        Namespace(
            repo_root=str(tmp_path),
            jobs_file=str(jobs),
            queue_dir=str(queue),
            task_records_file=str(queue / "task_records.jsonl"),
            verdicts_file=str(queue / "review_verdicts.jsonl"),
            max_items=25,
        )
    )
    assert pending["summary"]["pending_active_safe"] == 0
    assert pending["summary"]["pending_review_candidates"] == 1
