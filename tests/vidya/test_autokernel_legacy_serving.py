"""Original direct compare -> archive -> strict reader -> existing ledger, no compute."""
import copy
import dataclasses
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


def test_matched_original_http_archive_reader_and_existing_grade(tmp_path, monkeypatch):
    research = os.environ.get("EPYC_RESEARCH_ROOT")
    if not research:
        pytest.skip("EPYC_RESEARCH_ROOT must select the matching direct-serving producer")
    monkeypatch.syspath_prepend(str(Path(research) / "scripts/kernel_rnd"))
    from autokernel.loop.test_matched_serving import (
        test_actual_http_counterbalanced_requests_archive_and_teardown as execute,
    )
    execute(tmp_path, monkeypatch)
    path, = (tmp_path / "memory/serving-beliefs").glob("*.json")
    items = _native(path)
    tuples = [reader.project(item) for item in items]
    assert [item.value for item in tuples] == [20.0, 24.0]
    assert all(grade(item)[:2] == ("Judged", "Located") for item in tuples)
    assert all(item.protocol_id == "" for item in tuples)
    assert all(item.extra["measurement_plan"]["instrument"] == "matched_process_v2" for item in tuples)
    assert all(item.extra["measurement_plan"]["unit"] == "process" for item in tuples)


def test_actual_runtime_http_archive_reader_preserves_each_recipe(tmp_path, monkeypatch):
    research = os.environ.get("EPYC_RESEARCH_ROOT")
    if not research:
        pytest.skip("EPYC_RESEARCH_ROOT must select the matching direct-serving producer")
    monkeypatch.syspath_prepend(str(Path(research) / "scripts/kernel_rnd"))
    from autokernel.loop.test_runtime_treatment import (
        test_actual_loop_runtime_http_without_author_build_or_source_commit as execute,
    )
    execute(tmp_path)
    path, = (tmp_path / "memory/serving-beliefs").glob("*.json")
    tuples = [reader.project(item) for item in _native(path)]
    assert len(tuples) == 2 and tuples[0].value == tuples[1].value
    assert tuples[0].extra["recipe_hash"] != tuples[1].extra["recipe_hash"]
    assert tuples[0].extra["build_path"] == tuples[1].extra["build_path"]
    assert tuples[0].extra["request_digest"] == tuples[1].extra["request_digest"]
    assert all(grade(item)[:2] == ("Judged", "Located") for item in tuples)


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


# --- VB-LOOP-SCOPE: applicability from the capture's own fields ---------------------------------

def test_scope_comes_from_the_captures_own_recipe_and_resolved_launch(source):
    row, _, _, path = source
    inputs = row["belief_capture"]["inputs"]
    for native in _native(path):
        tup = reader.project(native)
        arm = tup.extra["arm"]
        resolved = inputs["resolved_arms"][arm]
        assert tup.applicability["model_file"] == inputs["recipe"]["model"] == "/fixture-model"
        assert tup.applicability["backend"] == resolved["backend"] == "cpu"
        assert tup.applicability["kernel"] == {"build_path": inputs["build_paths"][arm],
                                               "execution_digest": resolved["execution_digest"]}
        # Not stated by the record, so never declared: the reader then does not compare them.
        assert not {"device", "quant", "context_tokens", "run_id"} & set(tup.applicability)
        assert grade(tup) == grade(dataclasses.replace(tup, applicability={}))


def test_unresolved_capture_declares_model_but_no_backend(tmp_path, monkeypatch):
    research = os.environ.get("EPYC_RESEARCH_ROOT")
    if not research:
        pytest.skip("EPYC_RESEARCH_ROOT must select the matching direct-serving producer")
    monkeypatch.syspath_prepend(str(Path(research) / "scripts/kernel_rnd"))
    from autokernel.loop.test_serving_beliefs import archived
    _, _, _, path = archived(tmp_path, monkeypatch, resolved=False)
    for native in _native(path):
        assert native["applicability"] == {"model_file": "/fixture-model",
                                           "kernel": {"build_path": native["claim"]["extra"]["build_path"]}}


def test_a_capture_contradicting_its_own_model_declares_no_scope():
    row = {"extra": {"arm": "anchor"}}
    source = {"comparison": {"belief_capture": {"inputs": {
        "recipe": {"model": "/m/a.gguf"}, "build_paths": {"anchor": "/b"},
        "resolved_arms": {"anchor": {"backend": "cpu", "model": {"path": "/m/b.gguf"}}}}}}}
    assert reader._applicability(source, row) == {}
    source["comparison"]["belief_capture"]["inputs"]["resolved_arms"]["anchor"]["model"] = {
        "path": "/m/a.gguf"}
    assert reader._applicability(source, row) == {"model_file": "/m/a.gguf", "backend": "cpu",
                                                  "kernel": {"build_path": "/b"}}


def test_producer_time_store_ingest_is_idempotent(source, tmp_path):
    from scoped_ingest import ingest_scoped_store

    _, _, _, path = source
    ledger = Ledger(tmp_path / "scoped-ledger.jsonl")
    as_of = datetime.now(timezone.utc).isoformat()
    first = ingest_scoped_store(ledger, path.parent.parent, as_of=as_of)
    assert first["receipts_read"] == 1 and first["new_claims"] == 2
    assert first["frames_appended"] == 6 and ledger.verify() == []
    sources = [r.frame for r in ledger.read_all() if r.frame["frame_type"].endswith("source_observed/v1")]
    assert all(f["assertion"]["applicability"]["model_file"] == "/fixture-model" for f in sources)
    second = ingest_scoped_store(ledger, path.parent.parent, as_of=as_of)
    assert second["receipts_known"] == 1 and second["receipts_read"] == 0
    assert second["frames_appended"] == 0 and len(ledger) == 6
