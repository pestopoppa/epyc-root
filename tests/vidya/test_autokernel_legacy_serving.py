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
    # Two v1 arm claims, one v2 capture claim (P1-B), and one lane-C experiment-row claim: the
    # producer fixture also writes `experiments.db`, which `scoped_ingest` projects through
    # `autokernel_experiments` (P1-C). Four claims, three frames each.
    assert first["receipts_read"] == 1 and first["new_claims"] == 4
    assert first["v2_projected"] == 1 and first["experiments_projected"] == 1
    assert first["frames_appended"] == 12 and ledger.verify() == []
    ids = sorted(r.frame["assertion"]["claim_id"].split(":")[0] for r in ledger.read_all()
                 if r.frame["frame_type"].endswith("claim_proposed/v1"))
    assert ids == ["clm_ak-exp", "clm_legacy-serving", "clm_legacy-serving", "clm_legacy-serving-v2"]
    sources = [r.frame for r in ledger.read_all() if r.frame["frame_type"].endswith("source_observed/v1")]
    legacy = [f for f in sources if "legacy-serving" in json.dumps(f["assertion"].get("claim_id", f["assertion"]))]
    assert len(legacy) == 3
    assert all(f["assertion"]["applicability"]["model_file"] == "/fixture-model" for f in legacy)
    second = ingest_scoped_store(ledger, path.parent.parent, as_of=as_of)
    assert second["receipts_known"] == 1 and second["receipts_read"] == 0
    assert second["new_claims"] == 0 and second["already_present"] >= 1
    assert second["frames_appended"] == 0 and len(ledger) == 12


# --- P1-B: one value-bearing v2 claim per capture, from three REAL captures --------------------
#
# Fixtures: tests/vidya/fixtures/belief_p1/serving/{ds41,q38fn,runtime_ab}, derived from real
# AutoKernel captures by `derive_fixtures.py` (residency bulk trimmed, seal re-derived; every
# number the adapter reads is the original). PROVENANCE.json names each original.

P1_SERVING = ROOT / "tests/vidya/fixtures/belief_p1/serving"


def _p1_receipt(label):
    paths = sorted((P1_SERVING / label / "serving-beliefs").glob("*.json"))
    assert len(paths) == 1, f"derive the P1 fixtures first ({label})"
    return paths[0]


def _v2(path):
    raw = path.read_bytes()
    return reader.native_rows_v2(json.loads(raw), receipt_locator=f"autokernel:{path}",
                                 receipt_sha256=hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize("label", ["ds41", "q38fn", "runtime_ab", "matched_runtime"])
def test_v2_projects_one_value_bearing_claim_per_real_capture(label):
    path = _p1_receipt(label)
    v1 = [reader.project(n) for n in _native(path)]
    (native,) = _v2(path)
    tup = reader.project_v2(native)
    source = json.loads((path.parent / "sources" / path.name).read_text())
    comparison = source["comparison"]
    arms = {t.extra["arm"]: t for t in v1}
    assert tup.measurement_id == f"legacy-serving-v2:{path.stem}"
    assert tup.source_kind == "autokernel-legacy-serving-v2" and tup.category == "CANDIDATE"
    assert tup.value == comparison["candidate_tok_s"] == arms["candidate"].value
    assert tup.observation["anchor_value"] == comparison["anchor_tok_s"] == arms["anchor"].value
    assert tup.observation["n_pairs"] == tup.reps == comparison["pairs"]
    assert tup.observation["effect_rel"] == comparison["effect"]
    assert tup.observation["mechanism"] == {"id": source["mechanism_id"]}
    assert "retrofit" not in tup.observation  # a producer capture, not a retrofit
    # Same receipt, same locator: the reader's v1/v2 dedup key (§7.4).
    assert {t.attestation_locator for t in v1} == {tup.attestation_locator}
    assert tup.attestation_sha256 == arms["anchor"].attestation_sha256
    assert grade(tup)[:2] == ("Judged", "Located") == grade(arms["candidate"])[:2]
    assert tup.applicability["model_file"] == arms["candidate"].applicability["model_file"]
    assert tup.applicability["epoch"] == source["epoch"]
    assert tup.applicability["recipe"] == comparison["recipe"]
    assert tup.applicability["np"] == comparison["np"]
    assert tup.applicability["scope_basis"] == "native"
    assert f"{comparison['candidate_tok_s']:.2f} t/s" in tup.claim


def test_v2_decisive_capture_states_its_floor_and_signed_outcome():
    (native,) = _v2(_p1_receipt("ds41"))
    obs = reader.project_v2(native).observation
    assert obs["decisive"] is True
    assert obs["outcome"] == ("improved" if obs["effect_rel"] > 0 else "regressed")
    assert 0 < obs["noise_floor_rel"] < 1


def test_v2_runtime_capture_without_a_floor_states_no_outcome():
    (native,) = _v2(_p1_receipt("runtime_ab"))
    obs = reader.project_v2(native).observation
    assert "noise_floor_rel" not in obs and "decisive" not in obs and "outcome" not in obs


@pytest.mark.parametrize("label", ["ds41", "q38fn", "runtime_ab", "matched_runtime"])
def test_v2_frames_carry_the_numbers_and_ids_are_byte_stable(label):
    from claim_tuple import to_frames

    (native,) = _v2(_p1_receipt(label))
    first = to_frames(reader.project_v2(native), as_of="t", adapter_id=reader.ADAPTER_ID_V2)
    again = to_frames(reader.project_v2(_v2(_p1_receipt(label))[0]), as_of="t",
                      adapter_id=reader.ADAPTER_ID_V2)
    assert [f["frame_id"] for f in first] == [f["frame_id"] for f in again]
    evidence = first[2]["assertion"]
    assert evidence["metric"] == "aggregate_tok_s" and evidence["unit"] == "t/s"
    assert float(evidence["value"]) == pytest.approx(native["claim"]["value"], rel=1e-11)
    assert first[2]["frame_type"].endswith("evidence_supports_claim/v1")


# --- keep-grade declared runtime arm under the matched instrument (AK proof r4, 2026-11-10) -------
#
# The producer writes a v3 capture that ALSO carries the runtime pair; the reader refused it with
# "legacy serving inputs imply unsupported authority", so planner serving feedback went dark.


def test_matched_keep_grade_runtime_capture_projects_both_arms_and_its_floor():
    path = _p1_receipt("matched_runtime")
    v1 = [reader.project(n) for n in _native(path)]
    assert [t.extra["arm"] for t in v1] == ["anchor", "candidate"]
    assert v1[0].extra["recipe_hash"] != v1[1].extra["recipe_hash"]  # runtime: per-arm recipe
    assert all(t.extra["measurement_plan"]["instrument"] == "matched_process_v2" for t in v1)
    assert all(grade(t)[:2] == ("Judged", "Located") for t in v1)
    (native,) = _v2(path)
    obs = reader.project_v2(native).observation
    assert obs["decisive"] is False and obs["outcome"] == "null"
    assert obs["noise_floor_rel"] == pytest.approx(0.04146)


def _derive():
    import importlib.util
    here = ROOT / "tests/vidya/fixtures/belief_p1/derive_fixtures.py"
    spec = importlib.util.spec_from_file_location("belief_p1_derive", here)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resealed_matched_runtime(tmp_path, mutate):
    """The real matched-runtime capture with one field changed and every seal re-derived, so only
    the reader's admission rule (not a digest check) can refuse it."""
    src = _p1_receipt("matched_runtime")
    body = json.loads((src.parent / "sources" / src.name).read_text())
    mutate(body["comparison"])
    body, receipt, raw = _derive()._reseal(body)
    dest = tmp_path / "serving-beliefs"
    (dest / "sources").mkdir(parents=True)
    (dest / "sources" / f"{receipt['capture_id']}.json").write_bytes(raw)
    path = dest / f"{receipt['capture_id']}.json"
    path.write_text(json.dumps(receipt))
    return path


def test_matched_runtime_reseal_without_mutation_still_projects(tmp_path):
    assert len(_native(_resealed_matched_runtime(tmp_path, lambda c: None))) == 2


@pytest.mark.parametrize("mutate", [
    lambda c: c.update(admission="observation_only_original_strict_evidence_unavailable"),
    lambda c: c.update(admission="keep_grade_strict_frame"),
    lambda c: c.update(decisive=None),
    lambda c: c.update(noise_floor_pct=None),
    lambda c: c.update(floor_sha256=None),
    lambda c: c["belief_capture"]["inputs"].pop("runtime_pair"),
    lambda c: c["belief_capture"]["inputs"].pop("measurement_plan"),
], ids=["observation-admission", "unknown-admission", "no-decision", "no-floor",
        "no-floor-identity", "inputs-drop-runtime-pair", "inputs-drop-plan"])
def test_matched_runtime_capture_claiming_other_authority_is_refused(tmp_path, mutate):
    with pytest.raises(ProjectionError):
        _native(_resealed_matched_runtime(tmp_path, mutate))


def test_v2_mutated_native_row_is_refused():
    (native,) = _v2(_p1_receipt("q38fn"))
    mutated = copy.deepcopy(native)
    mutated["observation"]["anchor_value"] = 1.0
    with pytest.raises(ProjectionError, match="v2 projected row differs"):
        reader.project_v2(mutated)


def test_v2_ignores_non_receipts():
    assert reader.native_rows_v2({"schema": "epyc.autokernel.serving_ab.v1"},
                                 receipt_locator="autokernel:/x", receipt_sha256="") == []


def test_v2_capture_whose_arms_disagree_on_the_model_declares_no_scope():
    rows = [{"extra": {"arm": "anchor", "execution_digest": None}, "measurement_id": "a",
             "date": "2026-10-01T00:00:00+00:00", "reps_basis": "r"},
            {"extra": {"arm": "candidate", "execution_digest": None}, "measurement_id": "c",
             "date": "2026-10-01T00:00:01+00:00", "reps_basis": "r"}]
    source = {"epoch": "e", "mechanism_id": "akm-x", "comparison": {
        "schema": "epyc.autokernel.serving_ab.v2", "recipe": "r", "metric": "aggregate_tok_s",
        "anchor_tok_s": 10.0, "candidate_tok_s": 11.0, "effect": 0.1, "noise_floor_pct": 3.0,
        "decisive": True, "recipe_hash": "h", "belief_capture": {
            "capture_id": "c" * 64, "native_sha256": "n" * 64, "inputs": {
                "pairs": 2, "recipe": {"model": "/m/a.gguf", "np": 1},
                "build_paths": {"anchor": "/a", "candidate": "/c"},
                "resolved_arms": {"anchor": {"backend": "cpu", "model": {"path": "/m/b.gguf"}},
                                  "candidate": {"backend": "cpu"}}}}}}
    claim, scope, obs = reader._v2_row(source, rows)
    assert scope == {} and obs["outcome"] == "improved" and claim["value"] == 11.0


# --- VB-SL2-STEPS: estimated target steps/s, labelled by its estimator --------------------------

def _steps_block(estimators=("predicted_n_minus_draft_n_accepted",)):
    def side(median):
        return {"metric": reader.STEPS_METRIC, "n": 3, "status": "ok", "estimators": list(estimators),
                "median": median, "samples": [median] * 3}
    return {"schema": reader.STEPS_SCHEMA, "metric": reader.STEPS_METRIC,
            "role": "reporting_only_not_gate", "anchor": side(7.5), "candidate": side(9.5),
            "effect": 9.5 / 7.5 - 1}


def _resealed(tmp_path, block):
    """Copy a real P1 capture, inject the block into the native body, and re-seal every digest the
    strict reader checks (native_sha256 binds the block, so a mere edit would be refused)."""
    import shutil
    src = _p1_receipt("q38fn")
    dest = tmp_path / "serving-beliefs"
    shutil.copytree(src.parent, dest)
    receipt = json.loads((dest / src.name).read_text())
    old_id = receipt["capture_id"]
    body = json.loads((dest / "sources" / src.name).read_text())
    comparison = body["comparison"]
    old_native = comparison["belief_capture"]["native_sha256"]
    if block is not None:
        comparison["target_sample_steps_est"] = block
    capture = comparison["belief_capture"]
    native = {k: v for k, v in comparison.items() if k not in {"belief_capture", "surface", "baseline_scope"}}
    new_native = reader._digest(native)
    new_id = reader._digest({"native_sha256": new_native, "inputs": capture["inputs"]})
    text = json.dumps(capture).replace(old_native, new_native).replace(old_id, new_id)
    capture = json.loads(text)
    capture["capture_sha256"] = reader._digest({k: v for k, v in capture.items() if k != "capture_sha256"})
    comparison["belief_capture"] = capture
    raw = json.dumps(body, indent=2, sort_keys=True).encode()
    (dest / "sources" / src.name).unlink()
    (dest / "sources" / f"{new_id}.json").write_bytes(raw)
    (dest / src.name).unlink()
    receipt.update(capture_id=new_id, capture_sha256=capture["capture_sha256"],
                   native_reference={"path": f"sources/{new_id}.json",
                                     "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)})
    path = dest / f"{new_id}.json"
    path.write_text(json.dumps(receipt))
    return path


def _steps(path):
    raw = path.read_bytes()
    return reader.native_rows_steps(json.loads(raw), receipt_locator=f"autokernel:{path}",
                                    receipt_sha256=hashlib.sha256(raw).hexdigest())


def test_serving_ab_projects_target_steps_with_its_estimator_label(tmp_path):
    path = _resealed(tmp_path, _steps_block())
    assert len(_native(path)) == 2  # the tok/s rows still replay under the re-sealed body
    tuples = [reader.project_steps(n) for n in _steps(path)]
    assert [t.value for t in tuples] == [7.5, 9.5]
    assert [t.extra["arm"] for t in tuples] == ["anchor", "candidate"]
    for t in tuples:
        assert t.metric == "aggregate_target_sample_steps_s_est" and t.unit == "steps/s"
        assert t.extra["estimator"] == "predicted_n_minus_draft_n_accepted"
        assert t.extra["estimator_label"] == "estimate:predicted_n_minus_draft_n_accepted"
        assert "ESTIMATE via predicted_n_minus_draft_n_accepted" in t.claim
        assert "not the server's n_draft_verif_steps" in t.claim
        assert t.measurement_id.startswith("legacy-serving-steps:")
        assert grade(t)[:2] == ("Judged", "Located")


def test_target_steps_block_without_estimator_string_is_refused(tmp_path):
    for bad in ([], None, [""], ["made_up_estimator"]):
        block = _steps_block()
        block["candidate"]["estimators"] = bad
        if bad is None:
            del block["candidate"]["estimators"]
        with pytest.raises(ProjectionError, match="estimator string missing or unknown"):
            _steps(_resealed(tmp_path / str(len(str(bad))) / str(bad), block))


def test_capture_without_a_block_projects_no_steps_rows(tmp_path):
    assert _steps(_resealed(tmp_path, None)) == []


def _ingest(store, tmp_path):
    from scoped_ingest import ingest_scoped_store

    ledger = Ledger(tmp_path / "ledger.jsonl")
    report = ingest_scoped_store(ledger, store, as_of=datetime.now(timezone.utc).isoformat())
    return ledger, report


def _source_ids(ledger):
    return sorted(r.frame["assertion"]["source_id"] for r in ledger.read_all()
                  if r.frame["frame_type"].endswith("source_observed/v1"))


def test_scoped_ingest_adds_steps_rows_beside_the_existing_rows(tmp_path):
    _resealed(tmp_path / "with", _steps_block())
    _resealed(tmp_path / "without", None)
    with_ledger, with_report = _ingest(tmp_path / "with", tmp_path / "w")
    base_ledger, base_report = _ingest(tmp_path / "without", tmp_path / "b")
    assert with_report["steps_projected"] == 2 and with_report["refusals"] == []
    assert with_report["v2_projected"] == 1 and with_report["rows_projected"] == 2
    steps = [s for s in _source_ids(with_ledger) if s.startswith("src_legacy-serving-steps:")]
    assert len(steps) == 2 and with_ledger.verify() == []
    # A capture without the block ingests exactly as before: no steps rows, same row counts.
    assert base_report["steps_projected"] == 0 and base_report["refusals"] == []
    assert not [s for s in _source_ids(base_ledger) if "serving-steps" in s]
    assert len(base_ledger) == len(with_ledger) - 2 * 3
    assert base_report["rows_projected"] == with_report["rows_projected"]
    assert base_report["v2_projected"] == with_report["v2_projected"]


def test_scoped_ingest_refuses_unlabelled_steps_but_keeps_the_other_rows(tmp_path):
    block = _steps_block()
    block["anchor"]["estimators"] = []
    _resealed(tmp_path / "s", block)
    ledger, report = _ingest(tmp_path / "s", tmp_path / "l")
    assert report["steps_projected"] == 0
    assert any("estimator string missing" in r["reason"] for r in report["refusals"])
    assert report["rows_projected"] == 2 and report["v2_projected"] == 1
    assert not [s for s in _source_ids(ledger) if "serving-steps" in s]
