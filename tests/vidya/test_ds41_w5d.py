"""VB-DS41-W5D-WRITE: DS41-W5d analyzer RESULT -> OBSERVATION tuples graded by the one shared ladder."""
import json
import math
import statistics
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import ds41_w5d as dw  # noqa: E402

WHEN = "2026-10-24T11:30:00Z"
PP = [101.0, 102.0, 100.5, 101.5, 100.0, 102.5]
TG = [20.0, 20.2, 19.9, 20.1, 20.0, 20.3]
RR = [1.08, 1.07, 1.09, 1.08, 1.06, 1.10]


def _stats(xs):
    return {"n": 6, "values": xs, "mean": statistics.mean(xs), "median": statistics.median(xs), "sd": statistics.stdev(xs),
            "cv_pct": 100 * statistics.stdev(xs) / statistics.mean(xs), "ci95": [min(xs), max(xs)],
            "ci95_halfwidth_pct": 1.0, "noisy_runs_within_cv": []}


def result(tmp_path, a_verdict="BASELINE_VALID", b_verdict="PREMISE_STANDS", ratios=None, tweak=None):
    gm = math.exp(statistics.mean(math.log(x) for x in RR))
    d = {"task": "DS41-W5d", "predeclared_sha256": "ab" * 32,
         "a_baseline_1017_llama_bench": {"verdict": a_verdict, "metrics": {"pp512": _stats(PP), "tg128": _stats(TG)}},
         "b_mmid_pp512_premise": {
             "verdict": b_verdict, "served_mxfp4_arm": "B", "repack_na": False, "premise_verdict_if_valid": b_verdict,
             "constants": {"tol_pct": 3.0, "primary_n": 512},
             "ratio_served_over_Q4K_iqk": ratios if ratios is not None else {
                 "512": {"per_round": RR, "gm": gm, "ci95": [1.05, 1.11], "all_rounds_gt_1": True},
                 "1024": {"per_round": RR, "gm": gm, "ci95": [1.05, 1.11], "all_rounds_gt_1": True}},
             "s5_ceiling": {"s5_ceiling_pct_of_pp512_wall": 4.2, "mmid_share_pct_of_pp512_wall": 31.0}},
         "constants": {"reps": 3}}
    if tweak:
        tweak(d)
    p = tmp_path / "RESULT.json"
    p.write_text(json.dumps(d))
    return p


def write(tmp_path, **kw):
    return dw.write_belief_measurements(tmp_path, run_id="w5d-t", producer="t", results_path=result(tmp_path, **kw),
                                        emitted_at=WHEN)


def test_round_trip_all_halves(tmp_path):
    side = write(tmp_path)
    natives = dw.native_rows(side)
    metrics = [n["row"]["metric"] for n in natives]
    assert metrics.count(dw.M_RATIO) == 2 and dw.M_CEIL in metrics and "ds41_w5d_1017_pp512_ts" in metrics
    by = {(t.metric, t.extra.get("n_rows")): t for t in map(dw.project, natives)}
    pp = by[("ds41_w5d_1017_pp512_ts", None)]
    assert pp.value == pytest.approx(statistics.mean(PP)) and pp.reps == 6 and pp.observation["outcome_native"] == "BASELINE_VALID"
    assert pp.observation["noise_floor_rel"] == pytest.approx(pp.extra["cv_pct"] / 100)
    r512 = by[(dw.M_RATIO, 512)]
    assert r512.metric_direction == "lower_better" and r512.observation["anchor_value"] == 1.0
    assert r512.observation["decisive"] is True and r512.observation["noise_floor_rel"] == pytest.approx(0.03)
    assert "decisive" not in by[(dw.M_RATIO, 1024)].observation  # only the primary N carries the premise verdict
    for t in by.values():
        assert t.protocol_id == "" and t.attestation_present is True
        assert ct.grade(t)[:2] == ("Judged", "Located")
    assert dw.frames_for_sidecar(side, as_of=WHEN)


def test_void_or_incomplete_halves_project_nothing(tmp_path):
    def void(d):
        d["a_baseline_1017_llama_bench"] = {"verdict": "VOID", "reason": "protocol-mismatch"}
        d["b_mmid_pp512_premise"] = {"verdict": "INCOMPLETE", "reason": "30 of 36"}
    with pytest.raises(dw.CaptureError, match="no valid statistic"):
        dw.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=result(tmp_path, tweak=void))


def test_one_valid_half_projects_without_the_other(tmp_path):
    def half(d):
        d["b_mmid_pp512_premise"] = {"verdict": "INCOMPLETE", "reason": "30 of 36"}
    side = dw.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=result(tmp_path, tweak=half),
                                        emitted_at=WHEN)
    assert {n["row"]["metric"] for n in dw.native_rows(side)} == set(dw.M_BENCH.values())


def test_statistics_must_rederive_from_the_recorded_values(tmp_path):
    side = write(tmp_path)
    rows = [json.loads(x) for x in side.read_text().splitlines()]
    pp = next(r for r in rows if r["metric"] == "ds41_w5d_1017_pp512_ts")
    assert dw.row_problems(pp) == []
    assert any("mean of extra.values" in p for p in dw.row_problems(dict(pp, value=pp["value"] + 1)))
    ratio = next(r for r in rows if r["metric"] == dw.M_RATIO)
    assert any("geometric mean" in p for p in dw.row_problems(dict(ratio, value=2.0)))


def test_noisy_verdict_is_carried_not_rewritten(tmp_path):
    side = write(tmp_path, a_verdict="INVALID_NOISY", b_verdict="INVALID_NOISY")
    t = dw.project(next(n for n in dw.native_rows(side) if n["row"]["metric"] == "ds41_w5d_1017_pp512_ts"))
    assert t.observation["outcome_native"] == "INVALID_NOISY" and t.extra["verdict"] == "INVALID_NOISY"


def test_wrong_task_refused_and_cli(tmp_path, capsys):
    bad = tmp_path / "x.json"
    bad.write_text(json.dumps({"task": "other"}))
    with pytest.raises(dw.CaptureError, match="DS41-W5d"):
        dw.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=bad)
    assert dw.main(["write", "--results", str(result(tmp_path)), "--out-dir", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["rows"] == 5
