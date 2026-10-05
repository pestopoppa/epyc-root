"""Synthetic native score custody and shared-grade fixtures for NI38.

The app source checkout is explicitly supplied by CI; fixture inputs and dataset bytes are
synthetic. Nothing acquires ContextBench data or runs a discovery arm.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
sys.path.insert(0, str(ROOT / "scripts" / "harness"))
import cli  # noqa: E402
from adapters import contextbench_score as adapter  # noqa: E402
from claim_tuple import grade  # noqa: E402
import contextbench_score_capture as producer  # noqa: E402
from contextbench_score_capture import capture_score  # noqa: E402

AS_OF = "2026-10-05T00:00:00Z"


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _reseal_receipt(receipt: Path, record: dict) -> None:
    record.pop("receipt_sha256", None)
    record["receipt_sha256"] = hashlib.sha256(_canonical(record)).hexdigest()
    receipt.chmod(0o600)
    receipt.write_bytes(_canonical(record) + b"\n")
    receipt.chmod(0o400)


def _app_root() -> Path:
    value = os.environ.get("NI38_APP_SOURCE_ROOT")
    if not value:
        pytest.skip(
            "dedicated NI38 off-host CI binds NI38_APP_SOURCE_ROOT to the exact reviewed clean app checkout"
        )
    root = Path(value).resolve(strict=True)
    if not (root / "src" / "contextbench_score.py").is_file():
        raise AssertionError("NI38_APP_SOURCE_ROOT lacks the reviewed scorer source")
    return root


def _fixture(tmp_path: Path, *, malformed: bool = False):
    task_rows = tmp_path / "tasks.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    dispositions = tmp_path / "dispositions.json"
    dataset = tmp_path / "synthetic.parquet"
    task = {"instance_id": "fixture-1", "gold_context": [
        {"file": ".hidden/a.py", "start_line": 1, "end_line": 2},
    ]}
    if malformed:
        task = {"instance_id": "fixture-1", "gold_context": "{broken"}
    task_rows.write_text(json.dumps(task, separators=(",", ":")) + "\n")
    candidate = {"path": ".hidden/a.py", "priority": 1.0, "cost_full": 100,
        "cost_slices": 20, "cost_codemap": 5, "desired_mode": "full",
        "line_ranges": [[1, 2]], "total_lines": 2}
    prediction = {"task_id": "fixture-1", "arm": "synthetic-arm", "status": "ok",
        "pred_files": [".hidden/a.py"],
        "pred_spans": [{"path": ".hidden/a.py", "start_line": 1, "end_line": 2}],
        "pack_candidates": [candidate]}
    predictions.write_text(json.dumps(prediction, separators=(",", ":")) + "\n")
    dispositions.write_text(json.dumps({"schema": "epyc.contextbench_dispositions.v1",
        "tasks": [{"task_id": "fixture-1", "disposition": "include", "evidence_paths": []}]},
        separators=(",", ":")))
    dataset.write_bytes(b"synthetic ContextBench data placeholder\n")
    return dataset, task_rows, predictions, dispositions


def _capture(tmp_path: Path, *, malformed: bool = False) -> Path:
    dataset, task_rows, predictions, dispositions = _fixture(tmp_path, malformed=malformed)
    out = tmp_path / "owned-private-run"
    out.mkdir(mode=0o700)
    out.chmod(0o700)
    receipt = capture_score(dataset=dataset, task_rows=task_rows, predictions=predictions,
        dispositions=dispositions, app_root=_app_root(), output=out,
        dataset_label="synthetic-contextbench-fixture-v1", applicability="synthetic_fixture",
        arms=["synthetic-arm"], capture=True)
    return receipt


def test_synthetic_native_score_projects_descriptive_shared_grade_and_cli_row(tmp_path, capsys):
    meta_path_before = tuple(sys.meta_path)
    receipt = _capture(tmp_path)
    assert tuple(sys.meta_path) == meta_path_before
    record, digest = adapter.read_receipt(receipt)
    assert record["status"] == "scored"
    assert "src-package-source.bin" in record["artifacts"]
    native = adapter.native_rows(receipt)
    assert len(native) == 1
    row = native[0]
    assert row["integrity_result"] is True
    assert row["applicability"] == "synthetic_fixture"
    assert "arm" not in row and "task_id" not in row
    projected = adapter.project(row)
    assert projected.value is True
    assert projected.metric == "contextbench_score_report_integrity"
    assert projected.metric_direction == "higher_better"
    assert projected.protocol_id == ""
    assert projected.attestation_sha256 == digest
    assert projected.attestation_locator == "contextbench-score:" + row["capture_id"]
    assert projected.attestation_locator != str(receipt)
    assert adapter.public_locator(receipt) == projected.attestation_locator
    assert not any(key in projected.extra for key in ("arm", "task_id", "receipt_path"))
    assert grade(projected)[:2] == ("Judged", "Located")

    report_path = tmp_path / "vidya-ledger.jsonl"
    rc = cli.main(["--ledger", str(report_path), "--json", "ingest",
                   "contextbench-discovery-score", "--path", str(receipt.parent),
                   "--as-of", AS_OF, "--dry-run"])
    rendered_report = capsys.readouterr().out
    assert str(receipt.parent) not in rendered_report
    report = json.loads(rendered_report)
    assert rc == 0
    assert report["units_matched"] == report["units_projected"] == 1
    assert report["rows_projected"] == 1
    assert report["declined"] == [] and report["refused"] == []
    assert not report_path.exists() or report_path.stat().st_size == 0


def test_malformed_capture_is_private_diagnostic_and_projects_zero_rows(tmp_path):
    receipt = _capture(tmp_path, malformed=True)
    record, _ = adapter.read_receipt(receipt)
    assert record["status"] == "diagnostic"
    assert record["scorer_import_started"] is True
    assert adapter.native_rows(receipt) == ()


def test_capture_refuses_unsafe_output_root_without_normalizing_it(tmp_path):
    unsafe = tmp_path / "group-readable-output-root"
    unsafe.mkdir(mode=0o755)
    unsafe.chmod(0o755)
    with pytest.raises(ValueError, match="owned private directory"):
        producer._private_run_dir(unsafe, uuid.uuid4().hex)
    assert unsafe.stat().st_mode & 0o777 == 0o755


def test_stale_scorer_module_cache_is_diagnostic_without_execution(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "src", object())
    receipt = _capture(tmp_path)
    record, _ = adapter.read_receipt(receipt)
    assert record["status"] == "diagnostic"
    assert record["scorer_import_started"] is False
    assert record["diagnostic_code"] == "ValueError"
    assert adapter.native_rows(receipt) == ()


def test_moved_capture_directory_is_refused_and_report_locator_stays_private(tmp_path):
    receipt = _capture(tmp_path)
    run_dir = receipt.parent
    moved = run_dir.parent / "renamed-capture"
    os.rename(run_dir, moved)
    try:
        with pytest.raises(adapter.ProjectionError, match="custody refused"):
            adapter.native_rows(moved / "receipt.json")
        assert adapter.public_locator(moved / "receipt.json") == "contextbench-score:unresolved"
    finally:
        os.rename(moved, run_dir)


def test_changed_original_score_bytes_are_refused(tmp_path):
    receipt = _capture(tmp_path)
    output = receipt.parent / "scored-output.json"
    output.chmod(0o600)
    output.write_bytes(output.read_bytes() + b" ")
    output.chmod(0o400)
    with pytest.raises(adapter.ProjectionError, match="original digest"):
        adapter.native_rows(receipt)


def test_resealed_metric_that_contradicts_per_task_rows_is_refused(tmp_path):
    receipt = _capture(tmp_path)
    output = receipt.parent / "scored-output.json"
    score = json.loads(output.read_bytes())
    scope = next(item for item in score["arms"][0]["scopes"]
                 if item["scope"] == "discovery")
    scope["metrics"]["line_recall"]["value"] = 0.125
    output_bytes = _canonical(score) + b"\n"
    output.chmod(0o600)
    output.write_bytes(output_bytes)
    output.chmod(0o400)
    record = json.loads(receipt.read_bytes())
    record["scored_output"]["sha256"] = hashlib.sha256(output_bytes).hexdigest()
    record["scored_output"]["size"] = len(output_bytes)
    _reseal_receipt(receipt, record)
    with pytest.raises(adapter.ProjectionError, match="aggregate metric differs"):
        adapter.native_rows(receipt)


def test_resealed_integrity_proposition_that_contradicts_request_is_refused(tmp_path):
    receipt = _capture(tmp_path)
    record = json.loads(receipt.read_bytes())
    record["integrity_proposition"] = "A resealed, invented proposition."
    _reseal_receipt(receipt, record)
    with pytest.raises(adapter.ProjectionError, match="integrity result or proposition differs"):
        adapter.native_rows(receipt)


def test_cli_and_ingest_sources_enroll_exact_named_adapter():
    from ingest_sources import SOURCES

    assert "contextbench-discovery-score" in SOURCES
    assert "contextbench-discovery-score" in cli._FILE_SOURCES
    assert SOURCES["contextbench-discovery-score"].module == "contextbench_score"
    assert SOURCES["contextbench-discovery-score"].report_path == "public_locator"
