#!/usr/bin/env python3
"""AK-MECH-WITNESS-1: warn-only MECH-UNWITNESSED rule in ak_row_lint (no compute)."""
import json
import os
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import ak_row_lint as LINT  # noqa: E402

RULE = "keep if candidate tok/s beats baseline by >= 3% outside the AA band; else drop"
WITNESS = {"counter": "inst_per_byte", "direction": "down", "aa_band": 0.02}
JOB_OK = "for arm in ('base', 'cand'):\n    print('RESULT', arm, 'inst_per_byte', 1.0)\n"


def _row(tmp_path, spec, job="x = 1\n", rid="ak-mw-20261125"):
    d = tmp_path / rid
    d.mkdir()
    (d / "job.py").write_text(job)
    (d / "launch.sh").write_text("")
    (d / "spec.json").write_text(json.dumps(dict(spec, id=rid)))
    return d


def _mech(d):
    return [(l, m) for l, c, m in LINT.lint_dir(str(d), selftest=False) if c == "MECH-UNWITNESSED"]


def test_missing_witness_warns(tmp_path):
    r = _mech(_row(tmp_path, {"decision_rule": RULE}))
    assert len(r) == 1 and r[0][0] == "WARN" and "mechanism_witness" in r[0][1]


def test_incomplete_witness_warns(tmp_path):
    r = _mech(_row(tmp_path, {"decision_rule": RULE, "mechanism_witness": {"counter": "inst_per_byte"}}, JOB_OK))
    assert len(r) == 1 and "direction" in r[0][1]


def test_missing_counter_in_result_warns(tmp_path):
    r = _mech(_row(tmp_path, {"decision_rule": RULE, "mechanism_witness": WITNESS}, "print('RESULT', 'tok_s')\n"))
    assert len(r) == 1 and r[0][0] == "WARN" and "inst_per_byte" in r[0][1]


def test_compliant_row_no_warn(tmp_path):
    assert _mech(_row(tmp_path, {"decision_rule": RULE, "mechanism_witness": WITNESS}, JOB_OK)) == []


def test_non_speed_rule_no_warn(tmp_path):
    assert _mech(_row(tmp_path, {"decision_rule": "record the census"})) == []


def test_never_fails(tmp_path):
    for i, spec in enumerate(({"decision_rule": RULE}, {"decision_rule": RULE, "mechanism_witness": WITNESS})):
        d = _row(tmp_path, spec, rid="ak-mw-%d" % i)
        assert all(l == "WARN" for l, m in _mech(d))


def test_keep_candidate_toks_warns(tmp_path):
    r = _mech(_row(tmp_path, {"decision_rule": "KEEP_CANDIDATE iff CI of cand/base tok/s clears the band"}))
    assert len(r) == 1 and r[0][0] == "WARN"


def test_gate_pass_geomean_warns(tmp_path):
    r = _mech(_row(tmp_path, {"decision_rule": "GATE_PASS iff correctness AND geomean(c6/new) >= 1.10"}))
    assert len(r) == 1 and r[0][0] == "WARN"


def test_arms_diagnostic_polar_pass_no_warn(tmp_path):
    rule = "DIAGNOSTIC ONLY (never gates, polar None). Two arms BA; polar PASS is recorded, not a keep"
    assert _mech(_row(tmp_path, {"decision_rule": rule})) == []
    assert _mech(_row(tmp_path, {"decision_rule": "keep the arms terms claims"}, rid="ak-mw-arms")) == []


def test_floor_band_keep_candidate_still_warns(tmp_path):
    rule = "floor band [0.99, 1.01] either way -> KEEP_CANDIDATE (CI above) | LOSS; tok/s ratio"
    assert len(_mech(_row(tmp_path, {"decision_rule": rule}))) == 1
