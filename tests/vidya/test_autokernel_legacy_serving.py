"""Original direct compare -> archive -> strict reader -> existing ledger, no compute."""
import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))

from adapters import autokernel_corpus as corpus
from adapters import autokernel_legacy_serving as reader
from claim_tuple import ProjectionError, grade
from ledger import Ledger


@pytest.fixture
def source(tmp_path, monkeypatch):
    research = os.environ.get("EPYC_RESEARCH_ROOT")
    if not research:
        pytest.skip("EPYC_RESEARCH_ROOT must select the matching direct-serving producer")
    monkeypatch.syspath_prepend(str(Path(research) / "scripts/kernel_rnd"))
    from autokernel.loop.test_serving_beliefs import archived
    row, calls, attempt, path = archived(tmp_path, monkeypatch)
    return row, calls, attempt, path


def _native(path):
    raw = path.read_bytes()
    return reader.native_rows(json.loads(raw), receipt_locator=f"autokernel:{path}",
                              receipt_sha256=hashlib.sha256(raw).hexdigest())


def test_actual_producer_archive_reader_and_existing_corpus_ledger(source, tmp_path):
    row, calls, attempt, path = source
    tuples = [reader.project(item) for item in _native(path)]
    assert [item.value for item in tuples] == [11.0, 19.0]
    assert all(grade(item)[:2] == ("Judged", "Located") for item in tuples)
    assert [item.reps for item in tuples] == [2, 2]
    assert all(item.extra["build_path"] == row["belief_capture"]["inputs"]["build_paths"][item.extra["arm"]]
               and item.extra["model_path"] == "/fixture-model" for item in tuples)
    assert len(calls) == 4
    ledger = Ledger(tmp_path / "belief-ledger.jsonl")
    as_of = datetime.now(timezone.utc).isoformat()
    report = corpus.ingest_corpus(ledger, root=path.parent, as_of=as_of)
    assert report["rows_projected"] == 2 and report["refused"] == 0
    assert len(ledger) == 6 and ledger.verify() == []
    assert row["anchor_residency"][0]["cpu_lifecycle"]["status"] == "unavailable"
    assert attempt["status"] == "measured_null"  # adapter did not reinterpret the loop verdict
    first = [record.frame for record in ledger.read_all()]
    corpus.ingest_corpus(ledger, root=path.parent, as_of=as_of)
    assert [record.frame for record in ledger.read_all()][-6:] == first


def test_absent_pre_hook_rows_are_not_reconstructed():
    assert reader.native_rows({"schema": "epyc.autokernel.serving_ab.v1"},
                              receipt_locator="autokernel:/no/source", receipt_sha256="") == []


@pytest.mark.parametrize("change", ["moved", "changed", "symlink"])
def test_missing_or_changed_original_native_source_is_refused(source, change):
    _, _, _, path = source
    reference = json.loads(path.read_text())["native_reference"]
    original = path.parent / reference["path"]
    moved = original.with_suffix(".moved")
    if change == "changed":
        original.write_bytes(original.read_bytes() + b" ")
    else:
        original.rename(moved)
        if change == "symlink":
            original.symlink_to(moved)
    with pytest.raises(ProjectionError, match="source"):
        _native(path)


def test_mutated_projected_rows_and_rehashed_unearned_protocol_are_refused(source):
    _, _, _, path = source
    native = _native(path)[0]
    mutated = copy.deepcopy(native)
    mutated["claim"]["protocol_id"] = "invented-protocol"
    with pytest.raises(ProjectionError, match="projected row differs"):
        reader.project(mutated)
    receipt = json.loads(path.read_text())
    original = path.parent / receipt["native_reference"]["path"]
    body = json.loads(original.read_text())
    capture = body["comparison"]["belief_capture"]
    capture["belief_measurements"][0]["protocol_id"] = "invented-protocol"
    capture["capture_sha256"] = reader._digest({k: v for k, v in capture.items() if k != "capture_sha256"})
    raw = json.dumps(body, indent=2, sort_keys=True).encode()
    original.write_bytes(raw)
    receipt["native_reference"].update(sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))
    receipt["capture_sha256"] = capture["capture_sha256"]
    path.write_text(json.dumps(receipt))
    with pytest.raises(ProjectionError, match="belief rows differ"):
        _native(path)
