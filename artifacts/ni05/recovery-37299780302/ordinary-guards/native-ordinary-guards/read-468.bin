from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import yaml

from scripts.lab import review_queue_report


def _write_jobs_file(path: Path) -> None:
    doc = {
        "version": 1,
        "schema_version": "lab_jobs.v1",
        "policy": {
            "review_queue": "orchestration/lab_review_queue/",
            "direct_repo_writes_allowed": False,
            "default_stage": "shadow",
        },
        "jobs": [
            {
                "job_id": "handoff_freshness_lint",
                "stage": "shadow",
                "enabled": True,
                "risk": "read_only",
                "schedule": {"type": "nightly"},
                "input_spec": {"sources": []},
                "output_contract": {"format": "json", "json_schema": {"type": "object"}},
            },
            {
                "job_id": "active_safe_watch",
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
        ],
    }
    path.write_text(yaml.safe_dump(doc, sort_keys=False))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _args(tmp_path: Path, jobs_file: Path, queue: Path, **overrides) -> Namespace:
    values = {
        "repo_root": str(tmp_path),
        "jobs_file": str(jobs_file),
        "queue_dir": str(queue),
        "task_records_file": str(queue / "task_records.jsonl"),
        "verdicts_file": str(queue / "review_verdicts.jsonl"),
        "max_items": 25,
    }
    values.update(overrides)
    return Namespace(**values)


def test_review_queue_report_surfaces_pending_record_commands(tmp_path: Path) -> None:
    jobs_file = tmp_path / "lab_jobs.yaml"
    queue = tmp_path / "queue"
    _write_jobs_file(jobs_file)
    _write_json(queue / "handoff_freshness_lint" / "run-1" / "output.json", {"ok": True})
    _write_jsonl(
        queue / "task_records.jsonl",
        [
            {
                "schema_version": "lab_task_record.v1",
                "record_type": "task_record",
                "job_id": "handoff_freshness_lint",
                "run_id": "run-1",
                "stage": "shadow",
                "artifacts": {"output": "handoff_freshness_lint/run-1/output.json"},
            }
        ],
    )

    report = review_queue_report.run_from_args(_args(tmp_path, jobs_file, queue))

    assert report["schema_version"] == "lab_review_queue_report.v1"
    assert report["ok"] is True
    assert report["status"] == "attention"
    assert report["summary"]["pending_reviews"] == 1
    assert report["summary"]["pending_review_candidates"] == 1
    item = report["pending_items"][0]
    assert item["record_class"] == "review_candidate"
    assert item["output_exists"] is True
    assert item["next_reviewer"] == "cloud_reference"
    assert "scripts/lab/record_verdict.py" in item["cloud_reference_accept_command"]
    assert "--reference-output '<cloud-reference-output.json>'" in item["cloud_reference_accept_command"]
    assert "--reviewer operator" in item["operator_reject_command"]
    assert report["review_batch_template"] == [
        {
            "schema_version": "lab_review_batch.v1",
            "job_id": "handoff_freshness_lint",
            "run_id": "run-1",
            "verdict": "<accept|reject>",
            "reviewer": "cloud_reference",
            "stage": "shadow",
            "confidence": None,
            "notes": "",
            "local_output": "handoff_freshness_lint/run-1/output.json",
            "reference_output": "<cloud-reference-output.json>",
        }
    ]
    assert '"schema_version": "lab_review_batch.v1"' in report["review_batch_template_jsonl"]


def test_review_queue_report_ignores_already_verdicted_runs(tmp_path: Path) -> None:
    jobs_file = tmp_path / "lab_jobs.yaml"
    queue = tmp_path / "queue"
    _write_jobs_file(jobs_file)
    _write_jsonl(
        queue / "task_records.jsonl",
        [
            {
                "job_id": "handoff_freshness_lint",
                "run_id": "run-1",
                "stage": "shadow",
                "artifacts": {"output": "handoff_freshness_lint/run-1/output.json"},
            }
        ],
    )
    _write_jsonl(
        queue / "review_verdicts.jsonl",
        [
            {
                "schema_version": "lab_review_verdict.v1",
                "job_id": "handoff_freshness_lint",
                "run_id": "run-1",
                "stage": "shadow",
                "verdict": "accept",
                "reviewer": "cloud_reference",
            }
        ],
    )

    report = review_queue_report.run_from_args(_args(tmp_path, jobs_file, queue))

    assert report["status"] == "ok"
    assert report["summary"]["pending_reviews"] == 0
    assert report["pending_items"] == []


def test_review_queue_report_flags_missing_outputs_and_counts_active_safe(
    tmp_path: Path,
) -> None:
    jobs_file = tmp_path / "lab_jobs.yaml"
    queue = tmp_path / "queue"
    _write_jobs_file(jobs_file)
    _write_jsonl(
        queue / "task_records.jsonl",
        [
            {
                "job_id": "active_safe_watch",
                "run_id": "active-1",
                "stage": "shadow",
                "artifacts": {"output": "active_safe_watch/active-1/missing.json"},
            }
        ],
    )

    report = review_queue_report.run_from_args(_args(tmp_path, jobs_file, queue))

    assert report["ok"] is False
    assert report["status"] == "attention"
    assert report["summary"]["pending_active_safe"] == 1
    assert report["pending_items"][0]["next_reviewer"] == "automated"
    assert report["review_batch_template"][0]["reviewer"] == "automated"
    assert report["review_batch_template"][0]["reference_output"] is None
    assert report["review_batch_template"][0]["write_gold_tuple"] is False
    assert report["missing_outputs"] == [
        {
            "job_id": "active_safe_watch",
            "run_id": "active-1",
            "output_path": "active_safe_watch/active-1/missing.json",
        }
    ]


def test_review_queue_report_renders_markdown_packet(tmp_path: Path) -> None:
    jobs_file = tmp_path / "lab_jobs.yaml"
    queue = tmp_path / "queue"
    _write_jobs_file(jobs_file)
    _write_json(queue / "active_safe_watch" / "active-1" / "output.json", {"ok": True})
    _write_jsonl(
        queue / "task_records.jsonl",
        [
            {
                "job_id": "active_safe_watch",
                "run_id": "active-1",
                "stage": "shadow",
                "artifacts": {"output": "active_safe_watch/active-1/output.json"},
            }
        ],
    )

    report = review_queue_report.run_from_args(_args(tmp_path, jobs_file, queue))
    markdown = review_queue_report.render_markdown(report)

    assert "# Lab Review Queue Report" in markdown
    assert "| active_safe_watch | `active-1` | active_safe_deterministic | shadow | automated |" in markdown
    assert "```jsonl" in markdown
    assert '"schema_version": "lab_review_batch.v1"' in markdown
    assert "auto_review_active_safe.py --apply" in markdown
    assert "apply_review_batch.py" in markdown


def test_review_queue_report_cli_writes_markdown_packet(tmp_path: Path, capsys) -> None:
    jobs_file = tmp_path / "lab_jobs.yaml"
    queue = tmp_path / "queue"
    out_md = tmp_path / "review.md"
    _write_jobs_file(jobs_file)
    _write_json(queue / "active_safe_watch" / "active-1" / "output.json", {"ok": True})
    _write_jsonl(
        queue / "task_records.jsonl",
        [
            {
                "job_id": "active_safe_watch",
                "run_id": "active-1",
                "stage": "shadow",
                "artifacts": {"output": "active_safe_watch/active-1/output.json"},
            }
        ],
    )

    rc = review_queue_report.main(
        [
            "--repo-root",
            str(tmp_path),
            "--jobs-file",
            str(jobs_file),
            "--queue-dir",
            str(queue),
            "--markdown",
            "--output-md",
            str(out_md),
        ]
    )

    assert rc == 0
    captured = capsys.readouterr()
    assert "# Lab Review Queue Report" in captured.out
    assert out_md.read_text(encoding="utf-8") == captured.out
