"""VB-HILLB1-WRITE: HIL-LB1 loop-detector scores -> OBSERVATION tuples graded by the shared ladder."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402
from adapters import hil_lb1_loop_score as hl  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"
TOK = "b" * 64
REF = "258ce2d7b0f35ad22bdd8485662f19b2d3a1a871"


def cell(tp, fp, fn, tn):
    c = {"n": tp + fp + fn + tn, "n_pos": tp + fn, "n_neg": fp + tn, "tp": tp, "fp": fp, "fn": fn,
         "tn": tn}
    for f in ("precision", "recall", "f1", "fp_rate_on_negatives"):
        c[f] = hl.derive(c, f)
    return c


def result_doc(**kw):
    d = {"source": "Locals@0d39e161", "tokenizer": {"kind": "/t/tokenizer.json", "sha256": TOK},
         "profiles": {"tools": {"grace": None, "reps": 3}},
         "whowhen_pro": {"scope": "injected behaviour, not natural frequency; positives = mode A.4",
                         "loop_N": 53,
                         "populations": {"all": {
                             "prevalence_baseline (flag all)": cell(53, 6204, 0, 0),
                             "l2_loop_existing": cell(33, 92, 20, 6112),
                             "token_period_stream_exempt": cell(0, 0, 53, 6204),
                             "repeated_call_2395_ge2_exempt (descriptive sweep)": cell(53, 254, 0, 5950)}}},
         "inference_tap": {"counts": {"all": {"n": 3576}}}}
    d.update(kw)
    return d


def write(tmp_path, doc=None, **kw):
    p = tmp_path / "hil_lb1_loop_score.json"
    p.write_text(json.dumps(doc or result_doc()))
    return hl.write_belief_measurements(tmp_path, run_id="lb1-t", producer="hil_lb1_loop_score",
                                        results_path=p, emitted_at=WHEN, **kw)


def rewrite(side, fn):
    rows = [json.loads(x) for x in side.read_text().splitlines()]
    fn(rows[0])
    side.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_round_trip_observation_graded_by_shared_ladder(tmp_path):
    side = write(tmp_path)
    natives = hl.native_rows(side)
    assert natives
    for n in natives:
        tup = hl.project(n)
        assert tup.protocol_id == ""
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ("Judged", "Located")
        assert any("no protocol citation" in r and "OBSERVATION" in r for r in reasons)
    assert hl.frames_for_sidecar(side, as_of=WHEN)


def test_none_rates_emit_nothing_and_counts_bind(tmp_path):
    rows = [n["row"] for n in hl.native_rows(write(tmp_path))]
    # token_period_stream_exempt: tp+fp == 0 so precision is None at source -> no precision row
    assert not [r for r in rows if r["extra"]["detector"] == "token_period_stream_exempt"
                and r["metric"] == "hil_lb1_precision"]
    rec = [r for r in rows if r["extra"]["detector"] == "l2_loop_existing"
           and r["metric"] == "hil_lb1_recall"][0]
    assert rec["reps"] == 53 and rec["value"] == round(33 / 53, 4)
    fpr = [r for r in rows if r["metric"] == "hil_lb1_fp_rate_on_negatives"][0]
    assert fpr["metric_direction"] == "lower_better"
    cats = {r["extra"]["detector"]: r["category"] for r in rows}
    assert cats["l2_loop_existing"] == "BASELINE" and cats["token_period_stream_exempt"] == "CANDIDATE"
    assert any(r["extra"]["descriptive_sweep"] for r in rows)


def test_absent_identity_recorded_not_invented(tmp_path):
    r = hl.native_rows(write(tmp_path))[0]["row"]
    assert r["extra"]["absent_at_source"] == ["code_ref", "labelled_set_sha256"]
    lab = tmp_path / "text.jsonl"
    lab.write_text("{}\n")
    (tmp_path / "o").mkdir()
    r2 = hl.native_rows(write(tmp_path / "o", labelled_set_path=lab, code_ref=REF))[0]["row"]
    assert r2["extra"]["absent_at_source"] == [] and r2["extra"]["code_ref"] == REF
    assert r2["extra"]["labelled_set_sha256"] == ns.file_sha256(lab)


def test_value_that_does_not_rederive_is_refused(tmp_path):
    d = result_doc()
    d["whowhen_pro"]["populations"]["all"]["l2_loop_existing"]["f1"] = 0.9
    with pytest.raises(hl.CaptureError, match="re-derive"):
        write(tmp_path, d)


def test_missing_label_tokenizer_refused(tmp_path):
    d = result_doc()
    del d["whowhen_pro"]
    with pytest.raises(hl.CaptureError, match="populations"):
        write(tmp_path, d)
    with pytest.raises(hl.CaptureError, match="tokenizer"):
        write(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path,
              result_doc(tokenizer={"kind": "regex", "sha256": None}))


def test_tamper_and_protocol_smuggling_void_sidecar(tmp_path):
    side = write(tmp_path)
    rewrite(side, lambda r: r.update(value=0.99))
    assert hl.native_rows(side) == ()
    side = write(tmp_path)

    def mut(r):
        r["protocol_id"] = "observation:none"
        ns.seal(r)
    rewrite(side, mut)
    assert hl.native_rows(side) == ()


def test_no_ladder_registered_here(tmp_path):
    assert not hasattr(hl, "grade")
