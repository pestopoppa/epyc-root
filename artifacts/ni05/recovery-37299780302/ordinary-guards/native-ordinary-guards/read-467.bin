from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from scripts.lab import record_verdict


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _seed_queue(tmp_path: Path) -> tuple[Path, str]:
    queue = tmp_path / "queue"
    run_id = "sample-run"
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
    return queue, run_id


def _args(tmp_path: Path, queue: Path, run_id: str, **overrides) -> Namespace:
    values = {
        "job_id": "sample_job",
        "run_id": run_id,
        "verdict": "accept",
        "reviewer": "cloud_reference",
        "repo_root": str(tmp_path),
        "queue_dir": str(queue),
        "task_records_file": str(queue / "task_records.jsonl"),
        "verdicts_file": str(queue / "review_verdicts.jsonl"),
        "stage": None,
        "notes": "looks good",
        "confidence": 0.95,
        "local_output": None,
        "reference_output": str(tmp_path / "reference.json"),
        "cloud_reference_run_id": "cloud-run",
        "allow_duplicate": False,
        "no_gold_tuple": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_records_cloud_reference_verdict_and_gold_tuple(tmp_path: Path) -> None:
    queue, run_id = _seed_queue(tmp_path)
    _write_json(tmp_path / "reference.json", {"summary": "reference"})

    result = record_verdict.run_from_args(_args(tmp_path, queue, run_id))

    tuple_path = Path(result["tuple_path"])
    gold = json.loads(tuple_path.read_text())
    assert gold["schema_version"] == "lab_gold_tuple.v1"
    assert gold["local_output"]["payload"]["summary"] == "local"
    assert gold["reference_output"]["payload"]["summary"] == "reference"
    verdict_row = json.loads((queue / "review_verdicts.jsonl").read_text().splitlines()[-1])
    assert verdict_row["reference_type"] == "cloud_reference"
    assert verdict_row["cloud_reference_run_id"] == "cloud-run"
    assert verdict_row["tuple_path"] == f"gold_tuples/sample_job/{run_id}.json"


def test_cloud_reference_requires_reference_output(tmp_path: Path) -> None:
    queue, run_id = _seed_queue(tmp_path)

    with pytest.raises(record_verdict.VerdictError, match="requires --reference-output"):
        record_verdict.run_from_args(_args(tmp_path, queue, run_id, reference_output=None))


def test_automated_verdict_can_skip_gold_tuple(tmp_path: Path) -> None:
    queue, run_id = _seed_queue(tmp_path)

    result = record_verdict.run_from_args(
        _args(
            tmp_path,
            queue,
            run_id,
            reviewer="automated",
            reference_output=None,
            no_gold_tuple=True,
        )
    )

    assert result["tuple_path"] is None
    artifact = Path(result["verdict_artifact_path"])
    assert artifact.exists()
    assert not (queue / "gold_tuples" / "sample_job" / f"{run_id}.json").exists()
    payload = json.loads(artifact.read_text())
    assert payload["schema_version"] == "lab_verdict_artifact.v1"
    verdict_row = json.loads((queue / "review_verdicts.jsonl").read_text().splitlines()[-1])
    assert verdict_row["reviewer"] == "automated"
    assert verdict_row["evidence_type"] == "deterministic_review"
    assert "tuple_path" not in verdict_row


def test_duplicate_verdict_requires_explicit_override(tmp_path: Path) -> None:
    queue, run_id = _seed_queue(tmp_path)
    _write_json(tmp_path / "reference.json", {"summary": "reference"})

    record_verdict.run_from_args(_args(tmp_path, queue, run_id))
    with pytest.raises(record_verdict.VerdictError, match="verdict already exists"):
        record_verdict.run_from_args(_args(tmp_path, queue, run_id))

    result = record_verdict.run_from_args(_args(tmp_path, queue, run_id, allow_duplicate=True))
    assert Path(result["tuple_path"]).exists()


def test_missing_task_record_is_rejected(tmp_path: Path) -> None:
    queue = tmp_path / "queue"
    _write_jsonl(queue / "task_records.jsonl", [])
    _write_json(tmp_path / "reference.json", {"summary": "reference"})

    with pytest.raises(record_verdict.VerdictError, match="task_record not found"):
        record_verdict.run_from_args(_args(tmp_path, queue, "missing-run"))
