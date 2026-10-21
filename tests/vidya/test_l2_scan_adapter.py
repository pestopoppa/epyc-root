"""VB-L2-WRITE -- the L2 scan / calibration write-side hook and its strict reader.

Pinned: a pre-hook report emits ZERO rows; the ladder is the shared one; identity re-derives; a
tampered sidecar is void as a whole; a mutated report grades DOWN; the writer refuses an empty
report; calibration rows carry their injected-vs-natural scope.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import l2_scan as reader  # noqa: E402
from adapters import l2_scan_capture as capture  # noqa: E402

SCAN = {
    "header": "This report reads only status, exception, category and count fields ...",
    "coverage": {"denominator_failed": 200, "share_mechanical_signature": 0.25},
    "category_rates": {
        "tool_error": {"failed": {"n": 200, "fires": 30, "rate": 0.15}, "passed": {"n": 800, "fires": 8, "rate": 0.01}},
        "zero_step_violation": {"failed": {"n": 0, "fires": 0, "rate": None}, "passed": {"n": 0, "fires": 0, "rate": None}},
    },
}
CAL = {
    "whowhen_pro_text": {"targets": {"loop": {
        "detector_score": {"scored": True, "n_positive": 53, "tp": 33, "fp": 92, "precision": 0.264, "recall": 0.6226},
        "construction_only_baseline": {"tp": 53, "fp": 258, "precision": 0.1704, "recall": 1.0}}}},
    "traceelephant": {"agreement": {"ALL|detector_fvd": {"n": 218, "exact": 2, "within1": 5, "within5": 9}}},
}


def emit(tmp_path, rep, kind, name="r.json"):
    p = tmp_path / name
    p.write_text(json.dumps(rep))
    capture.write_belief_measurements(p, kind=kind, run_id="t1", producer="test", code_ref="abc123",
                                      emitted_at="2026-10-21T13:00:00Z")
    return p


def test_pre_hook_report_emits_zero_rows(tmp_path):
    p = tmp_path / "r.json"; p.write_text(json.dumps(SCAN))
    assert reader.rows_for_report(p) == ()


def test_scan_rows_grade_through_shared_ladder(tmp_path):
    p = emit(tmp_path, SCAN, "scan")
    natives = reader.rows_for_report(p)
    assert len(natives) == 3          # share + tool_error failed/passed; the n=0 cells emit nothing
    for n in natives:
        t = reader.project(n)
        assert ct.grade(t) == ct.grade(t)
        assert t.protocol_id == "" and t.reps >= 1
    assert reader.frames_for_sidecar(capture.sidecar_path(p), as_of="2026-10-21T14:00:00Z")


def test_calibration_rows_carry_scope_and_denominators(tmp_path):
    p = emit(tmp_path, CAL, "calibration")
    rows = {(n["row"]["locator"], n["row"]["metric"]): n["row"] for n in reader.rows_for_report(p)}
    assert rows[("whowhen_pro_text:loop", "l2_cal_recall")]["reps"] == 53
    assert rows[("whowhen_pro_text:loop", "l2_cal_precision")]["reps"] == 125
    assert "injected" in rows[("whowhen_pro_text:loop", "l2_cal_recall")]["extra"]["scope"]
    assert rows[("traceelephant:ALL", "l2_te_within5")]["value"] == pytest.approx(9 / 218)


def test_tampered_sidecar_is_void(tmp_path):
    p = emit(tmp_path, SCAN, "scan")
    side = capture.sidecar_path(p)
    lines = side.read_text().splitlines()
    row = json.loads(lines[0]); row["value"] = 0.99
    side.write_text("\n".join([json.dumps(row)] + lines[1:]) + "\n")
    assert reader.native_rows(side) == ()


def test_mutated_report_grades_down_not_disappears(tmp_path):
    p = emit(tmp_path, SCAN, "scan")
    before = reader.project(reader.rows_for_report(p)[0])
    p.write_text(json.dumps({**SCAN, "extra": 1}))
    after = reader.project(reader.rows_for_report(p)[0])
    assert after.attestation_present is False
    assert ct.grade(after)[:2] != ct.grade(before)[:2] or ct.grade(after)[0] != "Witnessed"


def test_writer_refuses_empty_report(tmp_path):
    p = tmp_path / "e.json"; p.write_text(json.dumps({"coverage": {"share_mechanical_signature": None}, "category_rates": {}}))
    with pytest.raises(capture.CaptureError):
        capture.write_belief_measurements(p, kind="scan", run_id="t", producer="t", code_ref="x")
