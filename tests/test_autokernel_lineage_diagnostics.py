"""Fixture-only tests: never touch a live AutoKernel campaign."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


MODULE = Path(__file__).resolve().parents[1] / "scripts/autokernel/lineage_diagnostics.py"
spec = importlib.util.spec_from_file_location("lineage_diagnostics", MODULE)
lineage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lineage)


def _row(pid, iteration, parent, solution, score, labels=None):
    return {"id": pid, "iteration_found": iteration, "parent_id": parent,
            "solution": solution, "metrics": {"score": score},
            "edit_labels": labels or [],
            "edit_label_source": {"annotator": "fixture", "rubric_revision": "1773db16"}}


def test_line_level_cycle_and_multilabel_yield():
    rows = [
        _row("a", 0, None, "int useful = 1;\nint other = 2;", 10),
        _row("b", 1, "a", "int other = 2;\nint fresh = 3;", 9,
             ["pruning", "hyperparameter_tuning"]),
        _row("c", 2, "b", "int useful = 1;\nint other = 2;\nint fresh = 3;", 8,
             ["bug_fix", "efficiency"]),
    ]
    report = lineage.analyze(rows, direction="lower_better")
    assert report["cycling"]["added_lines"] == 2
    assert report["cycling"]["recycled_added_lines"] == 1
    assert report["cycling"]["rate"] == 0.5
    assert report["taxonomy"]["bug_fix"]["yield"] == 1.0
    assert report["taxonomy"]["pruning"]["frequency"] == 1


def test_refuses_unsupported_or_unproven_labels():
    root = _row("a", 0, None, "int useful = 1;", 1)
    child = _row("b", 1, "a", "int useful = 2;", 2, ["reward_hack"])
    with pytest.raises(ValueError, match="nine-label"):
        lineage.analyze([root, child], direction="higher_better")
    child["edit_labels"] = []
    child.pop("edit_label_source")
    with pytest.raises(ValueError, match="provenance"):
        lineage.analyze([root, child], direction="higher_better")


def test_refuses_missing_parent_and_invalid_direction():
    row = _row("b", 1, "a", "int useful = 1;", 1)
    with pytest.raises(ValueError, match="metric direction"):
        lineage.analyze([row], direction="unknown")
    with pytest.raises(ValueError, match="missing parent"):
        lineage.analyze([row], direction="higher_better")


def test_content_addressed_export_roundtrip(tmp_path):
    source = "int useful = 1;\n"
    digest = hashlib.sha256(source.encode()).hexdigest()
    blob = tmp_path / "blobs" / digest[:2] / f"{digest}.txt"
    blob.parent.mkdir(parents=True)
    blob.write_text(source)
    row = {"id": "attempt-a", "iteration_found": 0, "parent_id": None,
           "solution_sha256": digest, "metrics": {}}
    receipt = {"schema": "epyc.autokernel.lineage_source_capture.v1",
               "capture_id": "attempt-a", "parent_id": None,
               "solution_sha256": digest, "patch_sha256": None}
    receipt_bytes = (json.dumps(receipt) + "\n").encode()
    (tmp_path / "captures").mkdir()
    (tmp_path / "captures" / "attempt-a.json").write_bytes(receipt_bytes)
    row["source_capture"] = {"capture_id": "attempt-a",
                             "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest()}
    (tmp_path / "programs.jsonl").write_text(json.dumps(row) + "\n")
    loaded, export_digest = lineage.load_programs(tmp_path)
    assert loaded[0]["solution"] == source
    assert len(export_digest) == 64
    blob.write_text("tampered")
    with pytest.raises(ValueError, match="digest mismatch"):
        lineage.load_programs(tmp_path)


def test_scored_export_requires_authored_outcome(tmp_path):
    source = b"int useful = 1;\n"
    digest = hashlib.sha256(source).hexdigest()
    blob = tmp_path / "blobs" / digest[:2] / f"{digest}.txt"
    blob.parent.mkdir(parents=True)
    blob.write_bytes(source)
    receipt = {"schema": "epyc.autokernel.lineage_source_capture.v1",
               "capture_id": "attempt-a", "parent_id": None,
               "solution_sha256": digest, "patch_sha256": None}
    raw = (json.dumps(receipt) + "\n").encode()
    (tmp_path / "captures").mkdir()
    (tmp_path / "captures/attempt-a.json").write_bytes(raw)
    row = {"id": "attempt-a", "iteration_found": 0, "parent_id": None,
           "solution_sha256": digest, "metrics": {"score": 1},
           "source_capture": {"capture_id": "attempt-a",
                              "receipt_sha256": hashlib.sha256(raw).hexdigest()}}
    (tmp_path / "programs.jsonl").write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="outcome_capture"):
        lineage.load_programs(tmp_path)


def test_historical_unbound_export_refused(tmp_path):
    row = {"id": "old", "iteration_found": 0, "parent_id": None,
           "solution_sha256": "a" * 64, "source_snapshot_sha256": "b" * 64}
    (tmp_path / "programs.jsonl").write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="historical unbound"):
        lineage.load_programs(tmp_path)
