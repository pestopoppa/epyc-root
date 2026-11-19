import json
import math
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import keep_tail as kt  # noqa: E402

REGION = {"warm_up": "3 discarded", "timed_loop": "20 iters", "compile_import_check": "excluded"}


def samples(p_pct, n=21):
    xs = [100.0] * n
    xs[-1] = 100.0 * (1 + p_pct / 100) * 1.0
    # p95 index = 19 of 0..20 -> make the top two carry the tail
    xs[-2] = xs[-1]
    return xs


def test_floor_formula_matches_handoff_example():
    assert abs(kt.widened_floor_pct(3.90) - 5.515) < 0.01
    assert kt.widened_floor_pct(0.5) == 2.00


def test_p95_known_value_and_guards():
    assert abs(kt.p95_inflation_pct(samples(4.0)) - 4.0) < 1e-9
    for bad in ([1, 2, 3], [1, 2, 3, 4, float("nan")], [1, 2, 3, 4, -1]):
        try:
            kt.p95_inflation_pct(bad)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_scope_is_future_rows_only_and_excludes_c7r():
    s = kt.load_scope()
    for yes in ("H8b-r2-a", "H8B-E2E-1", "FA-r5", "C8-inc3"):
        assert kt.applies(yes, s)
    for no in ("C7r-gate", "C7r", "FA-r4", "H8b-r1"):
        assert not kt.applies(no, s)


def test_enforced_row_inside_tail_is_refused_and_journalled():
    j = Path(tempfile.mkdtemp()) / "j.jsonl"
    r = kt.verdict("C8-inc1", 3.0, samples(3.9), samples(3.9), region=REGION, journal=j)
    assert r["refused"] and r["F_pct"] > 5.5 and "inside the reported tail" in r["reason"]
    assert json.loads(j.read_text().splitlines()[0])["row_id"] == "C8-inc1"


def test_enforced_row_clearing_floor_is_kept_and_undeclared_region_refused():
    j = Path(tempfile.mkdtemp()) / "j.jsonl"
    assert not kt.verdict("C8-inc1", 8.0, samples(3.9), samples(3.9), region=REGION, journal=j)["refused"]
    assert kt.verdict("C8-inc1", 8.0, samples(3.9), samples(3.9), region=None, journal=j)["refused"]


def test_out_of_scope_row_reports_but_never_refuses_or_journals():
    j = Path(tempfile.mkdtemp()) / "j.jsonl"
    r = kt.verdict("C7r-gate", 1.0, samples(3.9), samples(3.9), journal=j)
    assert not r["refused"] and r["effect_inside_tail"] and r["F_pct"] > 5.5 and not r["enforced"]
    assert not j.exists()


def test_scope_matches_real_row_ids_case_insensitively():
    for rid in ("ak-asm-h8b-e2e-20261106", "ak-asm-h8b-gate-r2-20261106", "fa-ck-hd256-gate-r5-20261106",
                "H8B-E2E-x", "c8-incr-1", "FA-r5-x"):
        assert kt.applies(rid), rid


def test_scope_token_anchoring_and_c7r_exclusion():
    for rid in ("c80-thing", "fa-ck-hd256-gate-20261106", "unrelated-row", "h8bx-e2e"):
        assert not kt.applies(rid), rid
    for rid in ("c7r-fa-r5-gate", "C7R-C8-x", "ak-c7r-h8b-e2e-20261106", "c7r2-c8-x"):
        assert not kt.applies(rid), rid
