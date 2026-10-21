"""VB-HIL-REPLAY-WRITE -- the replay-flip / spectrum write-side hook and its strict reader.

Pinned: a pre-hook report emits ZERO rows; the ladder is the shared one (OBSERVATION, never gating);
identity re-derives; a tampered sidecar is void as a whole; a mutated report grades DOWN; the committed
synthetic example is refused by the writer and a hand-built sidecar over it is void; a flip alone never
reads back as decisiveness; every score row carries its replay denominator.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import hil_replay as reader  # noqa: E402
from adapters import hil_replay_capture as capture  # noqa: E402

EXAMPLE = ROOT / "artifacts" / "dpf-hil-20261021" / "replay_flip_report.example.json"


def arm(n_pass, n, turn=2, hint=60, err=0):
    return {"restart_turn": turn, "hint_chars": hint, "n_started": n, "n_pass": n_pass, "n_error": err,
            "n_fail": n - n_pass - err, "flip_rate": n_pass / n, "wilson95": [0.0, 1.0]}


def flip_report(decisive=True, label="measurement", drop=None):
    arms = {"targeted": arm(9, 10), "no_hint": arm(1, 10, hint=0), "placebo": arm(8 if not decisive else 1, 10), "wrong_step": arm(1, 10, turn=5)}
    contrasts = {c: {"diff": (arms["targeted"]["flip_rate"] - arms[c]["flip_rate"]), "fisher_one_sided_p": 0.001 if decisive or c != "placebo" else 0.5}
                 for c in ("no_hint", "placebo", "wrong_step")}
    if drop:
        arms.pop(drop); contrasts.pop(drop)
    return {"schema": "replay_flip_report/v1", "label": label, "run_id": "r1", "task_key": "t1", "original_outcome": "fail",
            "restart_turn": 2, "alpha": 0.05, "arms": arms, "contrasts_vs_targeted": contrasts,
            "claim_allowed": drop is None, "decisive": decisive and drop is None,
            "verdict": "x" if decisive else "not distinguished from controls: a flip here is not evidence the step was decisive"}


def spec_report(label="measurement"):
    top = [{"key": ["frontdoor", "TOOL", "error"], "k2": 0.83, "ef": 9, "nf": 1, "ep": 2, "ambiguous": False}]
    return {"schema": "spectrum_report/v1", "label": label, "top_m": 3, "tasks_reported": 1, "tasks_skipped": [{"task_key": "s"}],
            "join": {"replays_started": 40, "with_steps": 38, "without_steps": ["a", "b"], "outcome_unknown": 2},
            "tasks": [{"ranking": {"task_key": "t1", "n_runs": 20, "n_fail": 10, "n_pass": 10, "usable": True, "top": top},
                       "l2_agreement": {"top_m": 3, "n_failed_runs": 10, "unclassified": 4,
                                        "by_category": {"loop": {"failed_runs_flagged": 5, "top_key_at_flagged_step": 3}}},
                       "human_overlap": {"top_m": 3, "human_n": 2, "hits": 1, "hit_keys": []}}],
            "l2_agreement_pooled": {"loop": {"failed_runs_flagged": 5, "top_key_at_flagged_step": 3}}}


def emit(tmp_path, rep, kind, name="r.json"):
    p = tmp_path / name
    p.write_text(json.dumps(rep))
    capture.write_belief_measurements(p, kind=kind, run_id="t1", producer="test", code_ref="abc123", emitted_at="2026-10-21T13:00:00Z")
    return p


def test_pre_hook_report_emits_zero_rows(tmp_path):
    p = tmp_path / "r.json"; p.write_text(json.dumps(flip_report()))
    assert reader.rows_for_report(p) == ()


def test_flip_rows_have_denominators_and_grade_as_observation(tmp_path):
    p = emit(tmp_path, flip_report(), "flip")
    rows = {(n["row"]["locator"], n["row"]["metric"]): n["row"] for n in reader.rows_for_report(p)}
    assert rows[("flip:targeted", "hil_flip_rate")]["reps"] == 10 and rows[("flip:targeted", "hil_flip_rate")]["value"] == 0.9
    assert rows[("flip:targeted-vs-placebo", "hil_flip_contrast_diff")]["extra"]["fisher_one_sided_p"] == 0.001
    assert rows[("flip:decisive", "hil_decisive")]["value"] == 1.0
    for n in reader.rows_for_report(p):
        t = reader.project(n)
        g = ct.grade(t)
        assert t.protocol_id == "" and t.reps >= 1 and g == ct.grade(t)
        assert g[0] == "Judged"            # an OBSERVATION: never decision-gating
    assert reader.frames_for_sidecar(capture.sidecar_path(p), as_of="2026-10-21T14:00:00Z")


def test_flip_alone_does_not_read_back_as_decisive(tmp_path):
    p = emit(tmp_path, flip_report(decisive=False), "flip")
    rows = {(n["row"]["locator"], n["row"]["metric"]): n["row"] for n in reader.rows_for_report(p)}
    assert rows[("flip:targeted", "hil_flip_rate")]["value"] == 0.9          # the flip is recorded ...
    assert rows[("flip:decisive", "hil_decisive")]["value"] == 0.0           # ... decisiveness is not claimed
    assert "not distinguished" in rows[("flip:decisive", "hil_decisive")]["extra"]["verdict"]


def test_missing_control_arm_emits_not_decisive(tmp_path):
    p = emit(tmp_path, flip_report(drop="placebo"), "flip")
    rows = {(n["row"]["locator"], n["row"]["metric"]): n["row"] for n in reader.rows_for_report(p)}
    assert rows[("flip:decisive", "hil_decisive")]["value"] == 0.0 and ("flip:targeted-vs-placebo", "hil_flip_contrast_diff") not in rows


def test_committed_synthetic_example_is_refused_and_never_grades(tmp_path):
    ex = json.loads(EXAMPLE.read_text())
    assert ex["label"] != "measurement" and "NOT a measurement" in ex["label"]
    copy = tmp_path / "ex.json"; copy.write_text(EXAMPLE.read_text())
    with pytest.raises(capture.CaptureError, match="label"):
        capture.write_belief_measurements(copy, kind="flip", run_id="x", producer="t", code_ref="x")
    assert not capture.sidecar_path(copy).exists()
    # a hand-built sidecar over the example is void: every row must declare report_label == 'measurement'
    good = emit(tmp_path, flip_report(), "flip", name="g.json")
    rows = [json.loads(l) for l in capture.sidecar_path(good).read_text().splitlines()]
    forged = []
    for r in rows:
        r["report_path"], r["report_sha256"] = str(copy), capture.file_sha256(copy)
        r["extra"]["report_label"] = ex["label"]
        r["measurement_id"] = capture.measurement_identity(run_id=r["run_id"], kind=r["kind"], locator=r["locator"], metric=r["metric"], report_sha256=r["report_sha256"])
        r["row_sha256"] = capture.row_digest(r)
        forged.append(r)
    side = capture.sidecar_path(copy)
    side.write_text("\n".join(json.dumps(r) for r in forged) + "\n")
    assert reader.native_rows(side) == ()          # zero rows: the synthetic example can never grade as evidence


def test_spectrum_rows_carry_replay_denominators_and_scope(tmp_path):
    p = emit(tmp_path, spec_report(), "spectrum")
    rows = {(n["row"]["locator"], n["row"]["metric"]): n["row"] for n in reader.rows_for_report(p)}
    assert rows[("spectrum:t1", "hil_spectrum_pass_rate")]["reps"] == 20
    top = rows[("spectrum:t1:top1", "hil_spectrum_top_k2")]
    assert top["reps"] == 20 and top["extra"]["ef"] == 9 and "not causation" in top["extra"]["scope"]
    assert rows[("spectrum:t1:loop", "hil_spectrum_l2_agree")]["value"] == pytest.approx(0.6)
    assert rows[("spectrum:t1:loop", "hil_spectrum_l2_agree")]["reps"] == 5
    assert rows[("spectrum:t1:unclassified", "hil_spectrum_unclassified_share")]["value"] == pytest.approx(0.4)
    assert rows[("spectrum:t1:human", "hil_spectrum_human_overlap")]["reps"] == 3
    assert rows[("spectrum:join:steps", "hil_spectrum_join_with_steps")]["reps"] == 40
    assert rows[("spectrum:join:outcome", "hil_spectrum_join_outcome_known")]["value"] == pytest.approx(0.95)
    assert all(ct.grade(reader.project(n))[0] == "Judged" for n in reader.rows_for_report(p))


def test_tampered_sidecar_is_void(tmp_path):
    p = emit(tmp_path, flip_report(), "flip")
    side = capture.sidecar_path(p)
    lines = side.read_text().splitlines()
    row = json.loads(lines[0]); row["value"] = 0.99
    side.write_text("\n".join([json.dumps(row)] + lines[1:]) + "\n")
    assert reader.native_rows(side) == ()


def test_mutated_report_grades_down_not_disappears(tmp_path):
    p = emit(tmp_path, spec_report(), "spectrum")
    before = reader.project(reader.rows_for_report(p)[0])
    p.write_text(json.dumps({**spec_report(), "extra": 1}))
    after = reader.project(reader.rows_for_report(p)[0])
    assert after.attestation_present is False and before.attestation_present is True


def test_writer_refuses_wrong_schema_and_empty(tmp_path):
    p = tmp_path / "w.json"; p.write_text(json.dumps(spec_report()))
    with pytest.raises(capture.CaptureError, match="schema"):
        capture.write_belief_measurements(p, kind="flip", run_id="t", producer="t", code_ref="x")
    e = tmp_path / "e.json"; e.write_text(json.dumps({**spec_report(), "tasks": [], "join": {}, "l2_agreement_pooled": {}}))
    with pytest.raises(capture.CaptureError, match="no reportable"):
        capture.write_belief_measurements(e, kind="spectrum", run_id="t", producer="t", code_ref="x")
