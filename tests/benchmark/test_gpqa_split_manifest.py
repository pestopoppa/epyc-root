"""Offline regression coverage for the pinned GPQA manifest publication boundary."""
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "artifacts/architect-model-selection-bench/gpqa_split_manifest.py"
spec = importlib.util.spec_from_file_location("gpqa_split_manifest", SOURCE)
splitter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(splitter)


@pytest.fixture
def cohort(tmp_path, monkeypatch):
    questions = [{"id": f"q{i}", "prompt": f"Question {i} — λ"} for i in range(198)]
    manifest = tmp_path / "source.json"
    manifest.write_text(json.dumps({"suites": {splitter.SUITE: questions}}), encoding="utf-8")
    monkeypatch.setattr(splitter, "PIN", hashlib.sha256(manifest.read_bytes()).hexdigest())
    return manifest, tmp_path / "out", questions


def test_complete_split_preserves_order_and_content(cohort):
    manifest, output, questions = cohort
    splitter.prepare_manifest(manifest, output)
    files = sorted(output.iterdir())
    assert len(files) == 198
    assert [json.loads(p.read_text(encoding="utf-8"))["suites"][splitter.SUITE][0] for p in files] == questions
    assert not list(output.parent.glob(".out-*"))


@pytest.mark.parametrize("failure", [OSError("disk full"), KeyboardInterrupt()])
def test_interrupted_write_has_no_partial_output_and_can_retry(cohort, failure):
    manifest, output, _ = cohort
    original = Path.write_text

    def fail_write(path, *args, **kwargs):
        if path.name == "017.json":
            raise failure
        return original(path, *args, **kwargs)

    with patch.object(Path, "write_text", fail_write), pytest.raises(type(failure)):
        splitter.prepare_manifest(manifest, output)
    assert not output.exists()
    assert not list(output.parent.glob(".out-*"))
    splitter.prepare_manifest(manifest, output)
    assert len(list(output.iterdir())) == 198


def test_failed_rename_removes_only_owned_reservation(cohort):
    manifest, output, _ = cohort
    with patch.object(splitter.os, "replace", side_effect=OSError("rename failed")), pytest.raises(OSError):
        splitter.prepare_manifest(manifest, output)
    assert not output.exists()
    assert not list(output.parent.glob(".out-*"))


@pytest.mark.parametrize("populated", [False, True])
def test_existing_destination_is_preserved(cohort, populated):
    manifest, output, _ = cohort
    output.mkdir()
    if populated:
        (output / "sentinel").write_text("keep")
    with pytest.raises(FileExistsError):
        splitter.prepare_manifest(manifest, output)
    assert sorted(p.name for p in output.iterdir()) == (["sentinel"] if populated else [])
    assert not list(output.parent.glob(".out-*"))


def test_digest_mismatch_creates_no_output(cohort):
    manifest, output, _ = cohort
    manifest.write_bytes(manifest.read_bytes() + b" ")
    with pytest.raises(ValueError, match="digest"):
        splitter.prepare_manifest(manifest, output)
    assert not output.exists()


@pytest.mark.parametrize("bad_ids", [["same"] * 198, [str(i) for i in range(197)], [""] + [str(i) for i in range(197)], [None] + [str(i) for i in range(197)]])
def test_invalid_cohort_is_rejected_before_output(cohort, monkeypatch, bad_ids):
    manifest, output, _ = cohort
    manifest.write_text(json.dumps({"suites": {splitter.SUITE: [{"id": i} for i in bad_ids]}}))
    monkeypatch.setattr(splitter, "PIN", hashlib.sha256(manifest.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="198 distinct"):
        splitter.prepare_manifest(manifest, output)
    assert not output.exists()
