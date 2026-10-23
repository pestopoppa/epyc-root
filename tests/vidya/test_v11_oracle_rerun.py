"""VB-V11-ORACLE-WRITE: V11-086 FP32-oracle rerun -> OBSERVATION tuples graded by the one shared ladder."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402
from adapters import v11_oracle_rerun as vo  # noqa: E402

WHEN = "2026-10-24T01:00:00Z"
FAIL = ["hsv=256 kv=65536 nb=2", "hsv=256 kv=131072 nb=2"]


def arm(passed, total, fails=()):
    return {"present": True, "passed": passed, "total": total, "rc": 0 if passed == total else 1,
            "ok": passed == total, "fail_keys": list(fails), "max_err_on_fail": 0.0007 if fails else None}


def doc(tmp_path, **over):
    arms = {"std_C": arm(5207, 5207), "std_Bunset": arm(5207, 5207), "std_B1": arm(5207, 5207),
            "std_Bauto": arm(5207, 5207), "long_C": arm(33, 35, FAIL), "long_Bunset": arm(33, 35, FAIL),
            "long_B1": arm(35, 35), "long_Bauto": arm(35, 35)}
    arms.update(over)
    d = {"schema": vo.SOURCE_SCHEMA, "written": "2026-10-24T00:59:00Z", "oracle": "fp32", "c_build": "/b/c", "b_build": "/b/b",
         "arms": arms, "A1_std_100_all_arms": True, "A2_long_100_on_B": True, "A3_long_C_equals_Bunset_failset": True,
         "tbo_fa_100_amended": True, "tbo_fa_100_letter": False, "prediction_met": {"std_all_100": True},
         "champion_long_property": {"C_fail_keys": FAIL, "C_max_err": 0.0007}, "summary": {"std_C": "5207/5207"}}
    p = tmp_path / "ORACLE_RERUN.json"
    p.write_text(json.dumps(d))
    return p


def write(tmp_path, **over):
    return vo.write_belief_measurements(tmp_path, run_id="v11orc-t", producer="t", results_path=doc(tmp_path, **over),
                                        emitted_at=WHEN)


def test_round_trip_one_row_per_arm_graded_by_shared_ladder(tmp_path):
    side = write(tmp_path)
    tuples = {n["row"]["extra"]["arm"]: vo.project(n) for n in vo.native_rows(side)}
    assert set(tuples) == set(vo.ARMS)
    t = tuples["long_C"]
    assert t.value == pytest.approx(33 / 35) and t.reps == 35 and t.category == "BASELINE"
    assert t.extra["fail_keys"] == FAIL and t.extra["clauses"]["tbo_fa_100_amended"] is True
    assert t.extra["clauses"]["tbo_fa_100_letter"] is False  # the strict letter rides beside the amendment, verbatim
    assert tuples["long_B1"].category == "CANDIDATE" and tuples["long_B1"].applicability["knobs"]["GGML_FA_VKQ_REG"] == "1"
    assert tuples["std_Bunset"].applicability["knobs"]["GGML_FA_VKQ_REG"] == "unset"
    for tup in tuples.values():
        assert tup.protocol_id == "" and tup.attestation_present is True
        assert ct.grade(tup)[:2] == ("Judged", "Located")
    assert vo.frames_for_sidecar(side, as_of=WHEN)


def test_unmeasured_arm_yields_no_row(tmp_path):
    side = write(tmp_path, long_Bauto=arm(None, None))
    assert "long_Bauto" not in {n["row"]["extra"]["arm"] for n in vo.native_rows(side)}


def test_value_must_equal_passed_over_total(tmp_path):
    row = json.loads(write(tmp_path).read_text().splitlines()[0])
    row["value"] = 0.5
    assert any("passed / extra.total" in p for p in vo.row_problems(row))


def test_nothing_measured_raises(tmp_path):
    every = {a: arm(None, None) for a in vo.ARMS}
    with pytest.raises(vo.CaptureError, match="no arm was measured"):
        vo.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=doc(tmp_path, **every))


def test_wrong_schema_refused_and_tamper_grades_down(tmp_path):
    bad = tmp_path / "x.json"
    bad.write_text(json.dumps({"schema": "other", "arms": {}}))
    with pytest.raises(vo.CaptureError, match="oracle-rerun.v1"):
        vo.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=bad)
    side = write(tmp_path)
    (tmp_path / "ORACLE_RERUN.json").write_text("{}")
    assert all(vo.project(n).attestation_present is False for n in vo.native_rows(side))


def test_cli_write(tmp_path, capsys):
    p = doc(tmp_path)
    assert vo.main(["write", "--results", str(p), "--out-dir", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["rows"] == 8
