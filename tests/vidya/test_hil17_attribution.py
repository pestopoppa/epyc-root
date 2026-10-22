"""VB-HIL17-WRITE: HIL-17 attribution-ladder tables -> OBSERVATION tuples graded by the shared ladder."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402
from adapters import hil17_attribution as ha  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"
SHA = "a" * 64
REF = "258ce2d7b0f35ad22bdd8485662f19b2d3a1a871"


def rung(name, n=40, ran=40, exact=0.25, calls=80):
    r = _rung(name, n, ran, exact, calls)
    if n == 0:
        r.update(within1=None, hit=None, abstain=None, agent_acc=None, agent_N=0,
                 tokens_per_case_all=0.0, calls=0)
    return r


def _rung(name, n, ran, exact, calls):
    return {"rung": name, "N": n, "ran_on": ran, "ran_share": 1.0, "exact": exact, "within1": 0.4,
            "hit": 0.6, "abstain": 0.1, "agent_acc": 0.5, "agent_N": 30, "calls": calls,
            "prompt_tokens": 1000, "completion_tokens": 100, "total_tokens": 1100,
            "calls_without_usage": 0, "tokens_per_case_ran": 27.5, "tokens_per_case_all": 27.5}


def report(**kw):
    r = {"set": "whowhen_pro_text", "mock": False, "policy": "calibrate", "with_reference": False,
         "code_ref": REF, "scope": {"set": "whowhen_pro_text", "path": "/x/text.jsonl", "sha256": SHA,
                                    "skipped": {}, "slice": {"per_framework": 10, "seed": 0}},
         "judges": [{"name": "jA", "family": "qwen", "quantised": False},
                    {"name": "jB", "family": "gemma", "quantised": True}],
         "ladder_judge": "jA", "n_cases": 40, "n_labelled": 40,
         "rungs": [rung("rung0_l2", calls=0), rung("rung1_whole"), rung("rung2_bisect", n=0, ran=0, exact=None),
                   rung("ladder_final")],
         "aggregate": {"N": 40, "k_per_family": 5, "temperature": 0.7,
                       "ksample_exp": 0.5, "ksample_exp_N": 40, "ksample_linear": 0.55,
                       "ksample_linear_N": 40, "temp0_exp": 0.4, "temp0_exp_N": 40,
                       "temp0_linear": None, "temp0_linear_N": 0, "random_expected_exp": 0.3,
                       "random_expected_exp_N": 40, "random_mc_exp": 0.31, "random_mc_exp_N": 40,
                       "per_family": {}, "tokens_ksample_per_case": 900.0, "tokens_temp0_per_case": 90.0}}
    r.update(kw)
    return r


def result(tmp_path, **kw):
    p = tmp_path / "ladder_report.json"
    p.write_text(json.dumps(report(**kw)))
    return p


def write(tmp_path, **kw):
    return ha.write_belief_measurements(tmp_path, run_id="hil17-t", producer="attribution_ladder",
                                        results_path=result(tmp_path, **kw), emitted_at=WHEN)


def rewrite(side, fn):
    rows = [json.loads(x) for x in side.read_text().splitlines()]
    fn(rows[0])
    side.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_round_trip_observation_graded_by_shared_ladder(tmp_path):
    side = write(tmp_path)
    natives = ha.native_rows(side)
    assert natives
    metrics = {n["row"]["metric"] for n in natives}
    assert "hil17_exact" in metrics and "hil17_ndcg5_ksample_exp" in metrics
    for n in natives:
        tup = ha.project(n)
        assert tup.protocol_id == ""  # never "observation:none"
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ("Judged", "Located")
        assert any("no protocol citation" in r and "OBSERVATION" in r for r in reasons)
    assert ha.frames_for_sidecar(side, as_of=WHEN)


def test_empty_rungs_and_none_rates_emit_nothing(tmp_path):
    rows = [n["row"] for n in ha.native_rows(write(tmp_path))]
    assert not [r for r in rows if r["extra"].get("cell", {}).get("rung") == "rung2_bisect"]
    assert not [r for r in rows if r["metric"] == "hil17_ndcg5_temp0_linear"]
    # rung0 makes no model call: no vacuous tokens row
    assert not [r for r in rows if r["metric"] == "hil17_tokens_per_case_all"
                and r["extra"]["cell"]["rung"] == "rung0_l2"]
    cats = {r["extra"]["cell"]["rung"]: r["category"] for r in rows if r["extra"]["part"] == "rung"}
    assert cats["rung0_l2"] == "BASELINE" and cats["rung1_whole"] == "CANDIDATE"
    tok = [r for r in rows if r["metric"] == "hil17_tokens_per_case_all"][0]
    assert tok["reps"] == 40 and tok["metric_direction"] == "lower_better"


def test_mock_unlabelled_undigested_and_fake_judge_refused(tmp_path):
    for kw, msg in (({"mock": True}, "mock"), ({"n_labelled": 0}, "no labelled"),
                    ({"scope": {"path": "x"}}, "sha256"), ({"code_ref": "abc"}, "code_ref"),
                    ({"judges": [{"name": "jA", "family": "fake", "quantised": None}]}, "fake")):
        with pytest.raises(ha.CaptureError, match=msg):
            ha.write_belief_measurements(tmp_path, run_id="r", producer="p",
                                         results_path=result(tmp_path, **kw))
    d = report()
    del d["mock"]
    p = tmp_path / "nomock.json"
    p.write_text(json.dumps(d))
    with pytest.raises(ha.CaptureError, match="mock"):
        ha.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=p)


def test_tamper_and_protocol_smuggling_void_sidecar(tmp_path):
    side = write(tmp_path)
    rewrite(side, lambda r: r.update(value=0.99))
    assert ha.native_rows(side) == ()
    side = write(tmp_path)

    def mut(r):
        r["protocol_id"] = "observation:none"
        ns.seal(r)
    rewrite(side, mut)
    assert ha.native_rows(side) == ()


def test_judge_identity_is_part_of_the_claim(tmp_path):
    a = {n["row"]["measurement_id"] for n in ha.native_rows(write(tmp_path))}
    (tmp_path / "other").mkdir()
    b = {n["row"]["measurement_id"] for n in ha.native_rows(write(
        tmp_path / "other", judges=[{"name": "jA", "family": "qwen", "quantised": True},
                                     {"name": "jB", "family": "gemma", "quantised": True}]))}
    assert not (a & b)


def test_project_refuses_invalid_and_no_ladder(tmp_path):
    row = dict(ha.native_rows(write(tmp_path))[0]["row"], value=0.123)
    with pytest.raises(ct.ProjectionError):
        ha.project({"row": row})
    assert not hasattr(ha, "grade")
