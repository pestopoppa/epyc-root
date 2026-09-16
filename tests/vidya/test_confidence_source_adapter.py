"""VB-EVCONF2: the EV-CONF-2 confidence-source write-side hook and its strict reader.

Pinned here:

* projection only: the grade asserted is whatever ``claim_tuple.grade()`` returns, and an
  observation-grade report projects with an empty protocol, so the shared ladder answers
  Judged/Located;
* speculative-decoding state is resolved, carried and stated in the claim. An arm label that
  contradicts it, or an identity that does not describe the report's sidecars, is refused;
* a pre-hook report (no sidecar) emits zero rows, and a tampered sidecar is void as a whole;
* a decayed attestation is visible on the tuple instead of disappearing.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import confidence_source as reader  # noqa: E402
from adapters import confidence_source_capture as capture  # noqa: E402

KERNEL = {"binary_path": "/mnt/raid0/llm/tmp/build-fold-ef81196d5/bin/llama-server",
          "binary_sha256": "8" * 64}
SHA = "a" * 64


def _sidecar(path: Path, batch: str, n: int) -> None:
    rows = [{"row_type": "batch_start", "eval_batch_id": batch}]
    rows += [{"row_type": "question_result", "eval_batch_id": batch, "ordinal": i,
              "result": {"correct": i % 2 == 0}} for i in range(n)]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def _report(sidecar: Path, *, n: int, placeholders: int, trace: int | None = None) -> dict:
    trace = n if trace is None else trace
    return {
        "schema": capture.REPORT_SCHEMA,
        "claim_grade": "observation",
        "n_scored": n,
        "accuracy": 0.5,
        "ece_binning": "closed_top_bin_stat_tests",
        "reweight_prevalence": 0.7886,
        "bootstrap": {"reps": 1000, "seed": 42, "method": "percentile"},
        "baseline_source": "legacy_confidence",
        "token_trace": {"rows_with_trace": trace, "rows_legacy_no_trace": n - trace,
                        "placeholder_fraction_median": 0.6 if placeholders else 0.0,
                        "placeholder_fraction_max": 0.9 if placeholders else 0.0,
                        "rows_with_any_placeholder": placeholders},
        "sources": {
            "legacy_confidence": {"n": n, "accuracy": 0.5, "auroc": 0.41, "auroc_ci95": [0.33, 0.49],
                                  "ece": 0.21, "ece_reweighted": 0.18, "mean_confidence": 0.9},
            "neg_length": {"n": n, "accuracy": 0.5, "auroc": 0.58, "auroc_ci95": [0.5, 0.66],
                           "ece": None, "ece_note": "not a probability; AUROC only",
                           "paired_vs_baseline": {"n_common": n, "delta_auroc": 0.17,
                                                  "delta_auroc_ci95": [0.05, 0.3]}},
            "answer_span_geomean": {"n": n - 10, "accuracy": 0.5, "auroc": 0.72,
                                    "auroc_ci95": [0.64, 0.8], "ece": 0.12, "ece_reweighted": 0.1,
                                    "paired_vs_baseline": {"n_common": n - 10, "delta_auroc": 0.31,
                                                           "delta_auroc_ci95": [0.2, 0.42]}},
            "high_entropy_top10_prob": {"n": 0},
        },
        "inputs": {"files": [{"path": str(sidecar),
                              "sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest()}],
                   "excluded_unscored": 0, "malformed": 0, "scored_rows": n},
    }


def _identity(path: Path, *, arm: str, batch: str, declared, segments: int = 1) -> None:
    seg = {
        "schema": capture.IDENTITY_SCHEMA, "arm": arm, "eval_batch_id": batch,
        "dataset_sha256": "3" * 64, "sample_sha256": "6" * 64, "orchestrator_head": "f2e9ee07",
        "sampling": {"role": "worker_general", "model_path": "/models/gemma.gguf",
                     "payload": {"temperature": 0.3, "top_k": 40, "top_p": 0.95,
                                 "repeat_penalty": 1.1, "seed": 42}},
        "request": {"top_logprobs": 20, "max_tokens": 2048},
        "serving": {"endpoint": "http://127.0.0.1:18381", "spec_declared": declared,
                    "props": {"model_path": "/models/gemma.gguf", "build_info": "b10125-ef81196d5"}},
    }
    path.write_text(json.dumps({"segments": [seg] * segments}))


def _world(tmp_path: Path, *, arm: str = "A-specoff", placeholders: int = 0, declared=False,
           trace: int | None = None, n: int = 200, id_batch: str | None = None) -> dict:
    batch = f"evconf2-probe-{arm}-66763b0b8f10"
    side = tmp_path / f"question_results.{arm}.jsonl"
    _sidecar(side, batch, n)
    report = tmp_path / f"compare.{arm}.json"
    report.write_text(json.dumps(_report(side, n=n, placeholders=placeholders, trace=trace)))
    ident = tmp_path / f"serving_identity.{arm}.json"
    _identity(ident, arm=arm, batch=id_batch or batch, declared=declared)
    return {"side": side, "report": report, "identity": ident, "arm": arm}


def _write(w: dict, **kw) -> Path:
    return capture.write_belief_measurements(
        w["report"], identity_path=w["identity"], arm=w["arm"], run_id="evconf2-probe-20260916",
        producer="test", kernel=KERNEL, emitted_at="2026-09-16T12:00:00Z", **kw)


def test_spec_off_round_trip_projects_every_computed_metric(tmp_path):
    w = _world(tmp_path)
    out = _write(w)
    assert out == tmp_path / "compare.A-specoff.beliefs.jsonl"
    natives = reader.rows_for_report(w["report"])
    got = {(n["row"]["extra"]["source"], n["row"]["metric"]) for n in natives}
    assert got == {
        ("legacy_confidence", "confidence_auroc"), ("legacy_confidence", "confidence_ece"),
        ("legacy_confidence", "confidence_ece_reweighted"), ("neg_length", "confidence_auroc"),
        ("answer_span_geomean", "confidence_auroc"), ("answer_span_geomean", "confidence_ece"),
        ("answer_span_geomean", "confidence_ece_reweighted"),
    }  # n=0 sources and never-computed ECEs emit nothing
    tuples = {(t.extra["source"], t.metric): t for t in map(reader.project, natives)}
    auc = tuples[("answer_span_geomean", "confidence_auroc")]
    assert auc.value == 0.72 and auc.metric_direction == "higher_better"
    assert auc.extra["ci95"] == [0.64, 0.8] and auc.extra["paired_vs_baseline"]["delta_auroc"] == 0.31
    assert auc.reps == 190 and auc.reps_basis == "scored:questions (10 without this source excluded)"
    assert auc.category == "CANDIDATE"
    assert tuples[("legacy_confidence", "confidence_auroc")].category == "BASELINE"
    ece = tuples[("legacy_confidence", "confidence_ece")]
    assert ece.metric_direction == "lower_better" and ece.unit == "ece_closed_top_bin_10"
    assert tuples[("legacy_confidence", "confidence_ece_reweighted")].extra["reweight_prevalence"] == 0.7886
    assert auc.extra["spec"]["state"] == "off" and auc.extra["confidence_is_real"] is True
    assert "CONTAMINATED" not in auc.claim and "UNVERIFIED" not in auc.claim
    assert auc.extra["served"]["build_info"] == "b10125-ef81196d5"
    assert auc.extra["seed"] == 42 and auc.extra["dataset_sha256"] == "3" * 64
    assert auc.attestation_present is True and auc.attestation_verified is True
    # the shared ladder decides, from the empty protocol of an observation-grade report
    q, t, reasons = ct.grade(auc)
    assert (q, t) == ("Judged", "Located")
    assert any("OBSERVATION" in r for r in reasons)
    assert len({t.measurement_id for t in tuples.values()}) == len(tuples)


def test_mtp_arm_carries_the_contamination_in_the_claim(tmp_path):
    w = _world(tmp_path, arm="B-mtp", placeholders=150, declared=True)
    _write(w)
    tup = reader.project(reader.rows_for_report(w["report"])[0])
    assert tup.extra["spec"]["state"] == "on" and tup.extra["confidence_is_real"] is False
    assert tup.claim.startswith("EV-CONF-2 evconf2-probe-20260916: CONTAMINATED: speculative decoding ON")
    assert tup.extra["spec"]["rows_with_any_placeholder"] == 150
    frames = reader.frames_for_sidecar(capture.sidecar_path(w["report"]), as_of="2026-09-16T12:00:00Z")
    assert frames and any("CONTAMINATED" in json.dumps(f) for f in frames)


@pytest.mark.parametrize("kw,match", [
    # the spec-off arm with placeholders while /slots said false: identity describes another server
    ({"placeholders": 3, "declared": False}, "placeholders observed while /slots declared"),
    # the spec-off arm whose server declared speculation
    ({"declared": True}, "must resolve to spec 'off'"),
    # the spec-off arm with a partial token trace cannot prove it
    ({"declared": None, "trace": 150}, "must resolve to spec 'off', not 'unknown'"),
])
def test_spec_off_arm_contract_refuses(tmp_path, kw, match):
    w = _world(tmp_path, **kw)
    with pytest.raises(capture.CaptureError, match=match):
        _write(w)
    assert not capture.sidecar_path(w["report"]).exists()


def test_mtp_arm_that_never_speculated_is_refused(tmp_path):
    w = _world(tmp_path, arm="B-mtp", placeholders=0, declared=False)
    with pytest.raises(capture.CaptureError, match="must resolve to spec 'on'"):
        _write(w)


def test_unlabelled_arm_with_unknown_spec_says_so(tmp_path):
    w = _world(tmp_path, arm="adhoc", declared=None, trace=0)
    _write(w)
    tup = reader.project(reader.rows_for_report(w["report"])[0])
    assert tup.extra["spec"]["state"] == "unknown"
    assert "UNVERIFIED speculative-decoding state" in tup.claim


def test_identity_from_another_run_is_refused(tmp_path):
    w = _world(tmp_path, id_batch="evconf2-probe-A-specoff-other-run")
    with pytest.raises(capture.CaptureError, match="does not describe the report's sidecars"):
        _write(w)


def test_identity_arm_mismatch_and_drifting_segments_are_refused(tmp_path):
    w = _world(tmp_path)
    with pytest.raises(capture.CaptureError, match="segment arm"):
        capture.write_belief_measurements(w["report"], identity_path=w["identity"], arm="B-mtp",
                                          run_id="r", producer="t", kernel=KERNEL)
    data = json.loads(w["identity"].read_text())
    second = json.loads(json.dumps(data["segments"][0]))
    second["serving"]["props"]["build_info"] = "b10107-67a433bf"
    w["identity"].write_text(json.dumps({"segments": [data["segments"][0], second]}))
    with pytest.raises(capture.CaptureError, match="build_info missing or changed"):
        _write(w)


def test_report_without_inputs_or_with_changed_sidecar_is_refused(tmp_path):
    w = _world(tmp_path)
    rep = json.loads(w["report"].read_text())
    w["side"].write_text(w["side"].read_text() + "\n")
    with pytest.raises(capture.CaptureError, match="changed or vanished"):
        _write(w)
    rep.pop("inputs")
    w["report"].write_text(json.dumps(rep))
    with pytest.raises(capture.CaptureError, match="--out, not stdout"):
        _write(w)


def test_pre_hook_report_emits_zero_rows(tmp_path):
    w = _world(tmp_path)
    assert reader.rows_for_report(w["report"]) == ()  # the E7c / EV-4c class: no sidecar


def test_tampered_sidecar_is_void_and_decay_is_visible(tmp_path):
    w = _world(tmp_path)
    out = _write(w)
    lines = out.read_text().splitlines()
    # decay: the attested input sidecar changes after capture -> still projects, not present
    original = w["side"].read_bytes()
    w["side"].write_bytes(original + b"\n")
    tup = reader.project(reader.native_rows(out)[0])
    assert tup.attestation_present is False and tup.attestation_verified is None
    w["side"].write_bytes(original)
    # tamper: a value change without re-hash voids the file
    row = json.loads(lines[0])
    row["value"] = 0.99
    out.write_text("\n".join([json.dumps(row)] + lines[1:]) + "\n")
    assert reader.native_rows(out) == ()
    # a re-hashed row that claims a protocol for an observation-grade report is still refused
    row = json.loads(lines[0])
    row["protocol_id"] = "P-CAL"
    row["row_sha256"] = capture.row_digest(row)
    assert any("protocol_id must be empty" in p for p in capture.validate_row(row))
    out.write_text("\n".join([json.dumps(row)] + lines[1:]) + "\n")
    assert reader.native_rows(out) == ()
    # a non-JSON line voids the file
    out.write_text("\n".join(lines + ["{not json"]) + "\n")
    assert reader.native_rows(out) == ()


def test_project_refuses_rows_that_bypass_validation(tmp_path):
    with pytest.raises(ct.ProjectionError):
        reader.project({"row": {"schema": capture.CAPTURE_SCHEMA}})
    with pytest.raises(ct.ProjectionError):
        reader.project({"not": "a row"})


def test_identity_is_stable_across_rewrites(tmp_path):
    w = _world(tmp_path)
    first = {n["row"]["measurement_id"] for n in reader.native_rows(_write(w))}
    second = {n["row"]["measurement_id"] for n in reader.native_rows(_write(w))}
    assert first == second


def test_cli_hashes_binary_when_not_given(tmp_path):
    w = _world(tmp_path)
    binary = tmp_path / "llama-server"
    binary.write_bytes(b"elf")
    rc = capture.main(["--report", str(w["report"]), "--identity", str(w["identity"]),
                       "--arm", "A-specoff", "--run-id", "r1", "--binary-path", str(binary)])
    assert rc == 0
    row = reader.native_rows(capture.sidecar_path(w["report"]))[0]["row"]
    assert row["extra"]["kernel"]["binary_sha256"] == hashlib.sha256(b"elf").hexdigest()
    assert row["extra"]["kernel"]["binary_sha256_source"] == "hashed_at_capture"
    assert capture.main(["--report", str(w["report"]), "--identity", str(w["identity"]),
                         "--arm", "B-mtp", "--run-id", "r1", "--binary-path", str(binary)]) == 2
