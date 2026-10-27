"""VB-SPEECH-KOPT-1: one fixture per record kind (CS-43.1, CH-18.d, upstream literature statement),
projected into the existing measurement class -- the same class and single ladder as the existing
test-backend-ops source (`autokernel_property.py`) -- and graded only by `claim_tuple.grade()`."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_property, speech_ggml_optest as kopt  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"


def fields(**kw):
    f = {"backend": "ROCm0", "device_arch": "gfx90a", "rocm_version": "6.2.0",
         "ggml_sha": "cc5df49", "ggml_version": "0.19.0", "local_patch_count": 0,
         "suite_case_count": 12, "op": "ARGSORT", "case_columns": [1025, 2047, 2048],
         "hip_graphs": True, "fusion": True, "first_divergence_step": None,
         "divergence_steps_checked": 256, "n_passed": 12, "n_failed": 0, "n_not_supported": 0,
         "tree": {"repo": "qwentts.cpp", "branch": "qwentts.cpp-experimental-cs43-1",
                  "commit": "5916bf7"},
         "binary_sha256": "a" * 64,
         "residency_proof": "verify_ggml_linkage.sh ok; VRAM 1.2 GiB sampled during run"}
    f.update(kw)
    return f


def records():
    cs43 = {"record_kind": "cs43_1_speech_ggml_optest", "fields": fields()}
    graphs = {"record_kind": "cs43_1_speech_ggml_optest",
              "metric": "graphs_fusion_identity_mismatch_cases",
              "fields": fields(op="ALL", case_columns=[], suite_case_count=4, n_passed=4,
                               hip_graphs=False, fusion=False, first_divergence_step=17,
                               divergence_steps_checked=64)}
    ch18 = {"record_kind": "ch18d_v11_gfx90a_optest",
            "fields": fields(op="TOP_K", case_columns=["k=40"], suite_case_count=30, n_passed=29,
                             n_failed=1, n_not_supported=0, ggml_sha="ffc1bac82",
                             local_patch_count=3,
                             tree={"repo": "llama.cpp", "branch": "llama.cpp-experimental-v11",
                                   "commit": "dd3d9721c"})}
    lit = {"record_kind": "upstream_statement",
           "fields": {"pr_ref": "llama.cpp#28957", "url": "https://github.com/ggml-org/llama.cpp/pull/28957",
                      "author": "qwentts maintainer", "published_date": "2026-09-30",
                      "statement": "bitonic argsort for rows wider than one block passes test-backend-ops",
                      "author_run_case_count": 1532}}
    return [cs43, graphs, ch18, lit]


def write_fixture(tmp: Path, recs=None) -> Path:
    res = tmp / "optest_results.json"
    res.write_text("{}")
    return kopt.write_belief_measurements(tmp, run_id="kopt-1", producer="cs43-1-runner",
                                          results_path=res, records=recs or records(),
                                          emitted_at=WHEN)


def test_one_fixture_per_measured_kind_graded_by_the_shared_ladder(tmp_path):
    natives = kopt.native_rows(write_fixture(tmp_path))
    assert {n["row"]["record_kind"] for n in natives} == set(kopt.MEASURED_KINDS) - {"meta_qwen4exp_native"}
    for nat in natives:
        tup = kopt.project(nat)
        assert tup.source_class == "measurement" and tup.metric_direction == "lower_better"
        assert tup.value == nat["row"]["fields"]["n_failed"]
        # P-AK-SEARCH-1 search records are not claims: no admissible protocol -> OBSERVATION
        assert tup.protocol_id == "" and ct.grade(tup)[:2] == ("Judged", "Located")


def test_same_class_and_ladder_as_the_existing_test_backend_ops_source():
    classes = ct.source_classes()
    assert classes[kopt.SOURCE_KIND] == classes["autokernel-property-measurement"] == "measurement"
    assert ct.ladders()["measurement"][1] is ct.grade  # one ladder; nothing new registered
    assert autokernel_property.project.__module__ != kopt.project.__module__
    assert "register_ladder" not in Path(kopt.__file__).read_text()


def test_every_record_carries_the_kopt_fields(tmp_path):
    for nat in kopt.native_rows(write_fixture(tmp_path)):
        f = nat["row"]["fields"]
        for k in ("backend", "device_arch", "rocm_version", "ggml_sha", "ggml_version",
                  "local_patch_count", "suite_case_count", "op", "case_columns", "hip_graphs",
                  "fusion", "first_divergence_step"):
            assert k in f, k


def test_missing_kopt_field_is_refused(tmp_path):
    for key in ("rocm_version", "local_patch_count", "hip_graphs", "fusion",
                "first_divergence_step", "residency_proof"):
        rec = copy.deepcopy(records()[0])
        rec["fields"].pop(key)
        with pytest.raises(kopt.CaptureError):
            write_fixture(tmp_path, [rec])
    rec = copy.deepcopy(records()[0])
    rec["fields"]["n_failed"] = 1
    with pytest.raises(kopt.CaptureError, match="must equal suite_case_count"):
        write_fixture(tmp_path, [rec])
    rec = copy.deepcopy(records()[2])
    rec["fields"]["tree"]["repo"] = "qwentts.cpp"
    with pytest.raises(kopt.CaptureError, match="llama"):
        write_fixture(tmp_path, [rec])


def test_upstream_statement_is_literature_only(tmp_path):
    sc = write_fixture(tmp_path)
    lit = kopt.literature_rows(sc)
    assert len(lit) == 1 and lit[0]["source_class"] == "literature"
    assert lit[0]["fields"]["author_run_case_count"] == 1532
    with pytest.raises(ct.ProjectionError, match="literature-class"):
        kopt.project({"row": lit[0]})


def test_protocol_citation_is_kept_verbatim_but_not_projected(tmp_path):
    rec = copy.deepcopy(records()[0])
    rec["protocol_id"] = "P-AK-SEARCH-1"
    tup = kopt.project(kopt.native_rows(write_fixture(tmp_path, [rec]))[0])
    assert tup.protocol_id == "" and tup.extra["protocol_id_native"] == "P-AK-SEARCH-1"
    assert tup.extra["protocol_status"] == "search_record_not_a_claim"


def test_tamper_voids_and_foreign_is_refused(tmp_path):
    sc = write_fixture(tmp_path)
    lines = sc.read_text().splitlines()
    row = json.loads(lines[0])
    row["fields"]["n_failed"] = 0
    row["value"] = 0
    row["claim"] += " edited"
    lines[0] = json.dumps(row, sort_keys=True)
    sc.write_text("\n".join(lines) + "\n")
    assert kopt.native_rows(sc) == ()
    with pytest.raises(ct.ProjectionError):
        kopt.project({"row": {"schema": "other"}})
    assert kopt.rows_for_run(tmp_path / "nowhere") == ()


def test_frames_emit(tmp_path):
    sc = write_fixture(tmp_path)
    assert len(kopt.frames_for_sidecar(sc, as_of="2026-10-22T11:00:00Z")) == 9


def test_meta_synthetic_host_observation_refuses_bad_residency(tmp_path):
    import hashlib
    import json
    for name in ("stdout", "stderr", "linkage.log"):
        (tmp_path / name).write_text("synthetic control")
    sample = {"pid": 123, "start_ticks": "456", "time_ns": 2, "kfd_gpu_id": 7,
              "pid_in_kfd": True, "vram_bytes": 8}
    samples = tmp_path / "residency.jsonl"
    samples.write_text((json.dumps(sample) + "\n") * 2)
    names = ("stdout", "stderr", "linkage.log", "residency.jsonl")
    raw = {name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() for name in names}
    commit = "520ad4f55d805a544862be88d652ec68fcd194ab"
    result = {"schema": "epyc.model_free_backend_correctness.v1", "source_commit": commit,
              "source_seal_sha256": "b" * 64, "binding_sha256": "c" * 64,
              "pid": 123, "start_ticks": "456", "start_ns": 1, "end_ns": 3,
              "kfd_gpu_id": 7, "reaped": True,
              "gates": {"fixture_process_rc": 0, "meta_moe_nmse": "OK",
                        "positive_device_samples": 2}, "raw_sha256": raw}
    result_path = tmp_path / "results.json"
    result_path.write_text(json.dumps(result))
    f = {"backend": "ROCm0", "device_arch": "gfx90a", "op": "qwen4exp-meta-moe-nmse",
         "binary_sha256": "a" * 64, "source_seal_sha256": "b" * 64,
         "binding_sha256": "c" * 64, "residency_proof": str(samples),
         "positive_device_samples": 2, "suite_case_count": 1, "n_failed": 0,
         "tree": {"commit": commit}}
    def emit():
        return kopt.write_belief_measurements(tmp_path, run_id="synthetic-only", producer="test",
            results_path=result_path, records=[{"record_kind": "meta_qwen4exp_native", "fields": f}],
            emitted_at=WHEN)
    native = kopt.native_rows(emit())[0]
    projected = kopt.project(native)
    assert projected.applicability["backend"] == "gpu"
    assert ct.grade(projected)[:2] == ("Judged", "Located")
    for field, wrong in (("time_ns", 4), ("start_ticks", "other"), ("kfd_gpu_id", 99)):
        bad = dict(sample, **{field: wrong})
        samples.write_text((json.dumps(bad) + "\n") * 2)
        result["raw_sha256"]["residency.jsonl"] = hashlib.sha256(samples.read_bytes()).hexdigest()
        result_path.write_text(json.dumps(result))
        with pytest.raises(ct.ProjectionError):
            kopt.project(kopt.native_rows(emit())[0])
