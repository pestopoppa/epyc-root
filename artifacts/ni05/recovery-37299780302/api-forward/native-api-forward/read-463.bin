from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from scripts.lab import apply_review_batch


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _seed_queue(tmp_path: Path) -> tuple[Path, Path, str]:
    queue = tmp_path / "queue"
    run_id = "run-1"
    output_path = queue / "sample_job" / run_id / "output.json"
    _write_json(output_path, {"job_id": "sample_job", "run_id": run_id, "summary": "local"})
    _write_jsonl(
        queue / "task_records.jsonl",
        [
            {
                "schema_version": "lab_task_record.v1",
                "record_type": "task_record",
                "job_id": "sample_job",
                "run_id": run_id,
                "stage": "shadow",
                "artifacts": {"output": f"sample_job/{run_id}/output.json"},
            }
        ],
    )
    reference = tmp_path / "reference.json"
    _write_json(reference, {"summary": "reference"})
    return queue, reference, run_id


def _args(tmp_path: Path, queue: Path, batch: Path, **overrides) -> Namespace:
    values = {
        "batch_file": str(batch),
        "repo_root": str(tmp_path),
        "queue_dir": str(queue),
        "task_records_file": str(queue / "task_records.jsonl"),
        "verdicts_file": str(queue / "review_verdicts.jsonl"),
        "allow_duplicates": False,
        "dry_run": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_apply_review_batch_records_gold_tuple(tmp_path: Path) -> None:
    queue, reference, run_id = _seed_queue(tmp_path)
    batch = tmp_path / "batch.jsonl"
    _write_jsonl(
        batch,
        [
            {
                "schema_version": "lab_review_batch.v1",
                "job_id": "sample_job",
                "run_id": run_id,
                "verdict": "accept",
                "reviewer": "cloud_reference",
                "reference_output": str(reference),
                "cloud_reference_run_id": "cloud-run-1",
                "confidence": 0.95,
                "notes": "matches reference",
            }
        ],
    )

    report = apply_review_batch.run_from_args(_args(tmp_path, queue, batch))

    assert report["ok"] is True
    assert report["rows"] == 1
    assert report["applied"][0]["tuple_path"].endswith("gold_tuples/sample_job/run-1.json")
    verdict_row = json.loads((queue / "review_verdicts.jsonl").read_text().splitlines()[0])
    assert verdict_row["reviewer"] == "cloud_reference"
    gold = json.loads((queue / "gold_tuples" / "sample_job" / "run-1.json").read_text())
    assert gold["reference_output"]["payload"]["summary"] == "reference"


def test_apply_review_batch_dry_run_does_not_mutate_queue(tmp_path: Path) -> None:
    queue, reference, run_id = _seed_queue(tmp_path)
    batch = tmp_path / "batch.jsonl"
    _write_jsonl(
        batch,
        [
            {
                "job_id": "sample_job",
                "run_id": run_id,
                "verdict": "accept",
                "reviewer": "cloud_reference",
                "reference_output": str(reference),
            }
        ],
    )

    report = apply_review_batch.run_from_args(_args(tmp_path, queue, batch, dry_run=True))

    assert report["ok"] is True
    assert report["dry_run"] is True
    assert report["planned"][0]["job_id"] == "sample_job"
    assert not (queue / "review_verdicts.jsonl").exists()


def test_apply_review_batch_can_record_non_gold_verdict_artifact(tmp_path: Path) -> None:
    queue, _reference, run_id = _seed_queue(tmp_path)
    batch = tmp_path / "batch.jsonl"
    _write_jsonl(
        batch,
        [
            {
                "job_id": "sample_job",
                "run_id": run_id,
                "verdict": "accept",
                "reviewer": "automated",
                "write_gold_tuple": False,
            }
        ],
    )

    report = apply_review_batch.run_from_args(_args(tmp_path, queue, batch))

    assert report["ok"] is True
    assert report["applied"][0]["tuple_path"] is None
    assert report["applied"][0]["verdict_artifact_path"].endswith(
        "verdict_artifacts/sample_job/run-1.json"
    )
    assert not (queue / "gold_tuples").exists()


def test_apply_review_batch_reports_row_errors_without_partial_abort(tmp_path: Path) -> None:
    queue, reference, run_id = _seed_queue(tmp_path)
    batch = tmp_path / "batch.jsonl"
    _write_jsonl(
        batch,
        [
            {
                "job_id": "sample_job",
                "run_id": run_id,
                "verdict": "accept",
                "reviewer": "cloud_reference",
                "reference_output": str(reference),
            },
            {
                "job_id": "sample_job",
                "run_id": "missing",
                "verdict": "accept",
                "reviewer": "operator",
            },
        ],
    )

    report = apply_review_batch.run_from_args(_args(tmp_path, queue, batch))

    assert report["ok"] is False
    assert report["status"] == "attention"
    assert len(report["applied"]) == 1
    assert report["errors"] == [{"row": 2, "error": "task_record not found for sample_job/missing"}]
