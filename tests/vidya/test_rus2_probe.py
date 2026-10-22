"""VB-RUS2-PROBE-WIRE: RUS-2 probe cells -> OBSERVATION tuples, graded by the one shared ladder."""

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402
from adapters import rus2_probe as rp  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"


def cell(role="frontdoor", mode="direct", suite="hotpotqa", **kw):
    c = {"role": role, "mode": mode, "suite": suite, "questions": 253, "samples": 253,
         "correct": 179, "cap_proxy_excluded": 0, "cap_value": None,
         "between_auroc_tokens": 0.2116, "between_pairs": 13246, "between_ci95": [0.1434, 0.2888],
         "within_questions_mixed": 0, "within_pairs": 0, "within_pooled_auroc": None,
         "within_ci95": None, "within_share_correct_shorter": None,
         "review_ratio_samples": 169, "review_ratio_auroc": 0.2785}
    c.update(kw)
    return c


def result(tmp_path, rows=None, **kw):
    r = {"files_scanned": 62, "drops": {"no_tokens_generated": 462},
         "temperature_field": {"not_recorded": 6565},
         "fields_absent": ["finish_reason", "per-sample temperature (unless temperature_field."
                           "recorded>0)", "reasoning trace text (answer only)"],
         "rows": rows if rows is not None else [
             cell(), cell("architect_coding", "delegated", "agentic", questions=42, samples=42),
             cell("coder", "direct", "math", questions=5, samples=7,
                  within_questions_mixed=1, within_pairs=3, within_pooled_auroc=0.33)]}
    r.update(kw)
    p = tmp_path / "rus2_result.json"
    p.write_text(json.dumps(r))
    return p


def write(tmp_path, **kw):
    return rp.write_belief_measurements(tmp_path, run_id="rus2-t", producer="rus2-probe",
                                        results_path=result(tmp_path), emitted_at=WHEN, **kw)


def rewrite(side, fn):
    rows = [json.loads(x) for x in side.read_text().splitlines()]
    fn(rows[0])
    side.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_round_trip_observation_graded_by_shared_ladder(tmp_path):
    side = write(tmp_path)
    natives = rp.native_rows(side)
    # frontdoor + agentic between rows, coder within row (coder between: 5 < 20 questions)
    assert [n["row"]["metric"] for n in natives].count("rus2_between_auroc_tokens") == 2
    assert [n["row"]["metric"] for n in natives].count("rus2_within_pooled_auroc") == 1
    for n in natives:
        tup = rp.project(n)
        assert tup.protocol_id == ""
        assert tup.extra["absent_protocol_fields"] == ["finish_reason", "temperature"]
        q, t, reasons = ct.grade(tup)
        # grade() is the only decider: no protocol -> OBSERVATION, never gating, never Witnessed
        assert (q, t) == ("Judged", "Located")
        assert any("no protocol citation" in r and "OBSERVATION" in r for r in reasons)
    frames = rp.frames_for_sidecar(side, as_of=WHEN)
    assert frames


def test_within_arm_carries_its_tiny_sample(tmp_path):
    n = [x for x in rp.native_rows(write(tmp_path)) if x["row"]["metric"].endswith("within_pooled_auroc")][0]
    assert n["row"]["reps"] == 3 and n["row"]["extra"]["cell"]["within_questions_mixed"] == 1


def test_values_come_from_file_and_hash_binds_it(tmp_path):
    side = write(tmp_path)
    n = rp.native_rows(side)[0]
    assert n["attestation_present"] is True
    (tmp_path / "rus2_result.json").write_text("{}")
    assert rp.native_rows(side)[0]["attestation_present"] is False  # decayed attestation, not void
    assert rp.project(rp.native_rows(side)[0]).attestation_present is False


def test_tampered_row_voids_whole_sidecar(tmp_path):
    side = write(tmp_path)
    rewrite(side, lambda r: r.update(value=0.9))
    assert rp.native_rows(side) == ()


def test_protocol_cannot_be_smuggled_in(tmp_path):
    side = write(tmp_path)
    def mut(r):
        r["protocol_id"] = "P-QUAL-T1"
        ns.seal(r)
    rewrite(side, mut)
    assert rp.native_rows(side) == ()


def test_dropping_absent_fields_is_refused(tmp_path):
    side = write(tmp_path)
    def mut(r):
        r["extra"]["absent_protocol_fields"] = []
        ns.seal(r)
    rewrite(side, mut)
    assert rp.native_rows(side) == ()


def test_project_refuses_invalid_native(tmp_path):
    row = rp.native_rows(write(tmp_path))[0]["row"]
    row = dict(row, value=0.1)
    with pytest.raises(ct.ProjectionError):
        rp.project({"row": row})
    with pytest.raises(ct.ProjectionError):
        rp.project({})


def test_writer_refuses_missing_producer_fields(tmp_path):
    p = result(tmp_path)
    d = json.loads(p.read_text())
    del d["temperature_field"]
    p.write_text(json.dumps(d))
    with pytest.raises(rp.CaptureError, match="temperature_field"):
        rp.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=p)


def test_writer_refuses_when_source_does_not_declare_absence(tmp_path):
    p = result(tmp_path, temperature_field={"recorded": 10}, fields_absent=["reasoning trace text"])
    with pytest.raises(rp.CaptureError, match="declares neither"):
        rp.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=p)


def test_writer_refuses_malformed_cell_and_missing_file(tmp_path):
    bad = result(tmp_path, rows=[{"role": "x"}])
    with pytest.raises(rp.CaptureError, match="malformed"):
        rp.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=bad)
    with pytest.raises(rp.CaptureError, match="unreadable"):
        rp.write_belief_measurements(tmp_path, run_id="r", producer="p",
                                     results_path=tmp_path / "nope.json")


def test_no_ladder_registered_here():
    assert not hasattr(rp, "grade")
