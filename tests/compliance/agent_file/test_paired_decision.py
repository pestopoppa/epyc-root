from __future__ import annotations

import json

import pytest

from tests.compliance.agent_file import paired_decision as pd


def _pool(passes, err=()):
    return [{"task_id": f"t{i}", "pass_": p, "error": "x" if i in err else ""} for i, p in enumerate(passes)]


def _suite(level, comp, proc, rec, blank_count=0):
    return {"level": level, "blank_count": blank_count, "forbidden_action_results": comp,
            "procedure_results": proc, "recall_results": rec}


def _same(n=30, k=27):
    return [True] * k + [False] * (n - k)


def test_clear_keep_identical():
    base = _suite("none", _pool(_same()), _pool(_same()), _pool(_same()))
    cand = _suite("mild", _pool(_same()), _pool(_same()), _pool(_same()))
    r = pd.decide(base, cand)
    assert r["overall"] == "KEEP"
    assert all(p["verdict"] == "KEEP" and p["b"] == 0 and p["c"] == 0 for p in r["pools"].values())


def test_clear_drop():
    base = _suite("none", _pool([True] * 30), _pool(_same()), _pool(_same()))
    cand = _suite("aggr", _pool([True] * 15 + [False] * 15), _pool(_same()), _pool(_same()))
    r = pd.decide(base, cand)
    assert r["pools"]["compliance"]["verdict"] == "DROP"
    assert r["pools"]["compliance"]["b"] == 15
    assert r["overall"] == "DROP"


def test_borderline_small_loss_is_keep_large_is_drop():
    # n=30, 100% baseline; candidate loses b tasks. Find the flip point and check monotonicity.
    verdicts = []
    for b in range(0, 10):
        base = [True] * 30
        cand = [False] * b + [True] * (30 - b)
        verdicts.append(pd.decide_pool(_pool(base), _pool(cand))["verdict"])
    assert verdicts[0] == "KEEP" and verdicts[-1] == "DROP"
    flip = verdicts.index("DROP")
    assert all(v == "KEEP" for v in verdicts[:flip]) and all(v == "DROP" for v in verdicts[flip:])
    assert 1 <= flip <= 6


def test_known_value_newcombe():
    # n=30, b=0, c=0 -> d=0, bound strictly negative but > -0.10
    lo = pd.newcombe_paired_lower(27, 0, 0, 3)
    assert -0.10 < lo < 0


def test_gain_has_higher_bound_than_loss():
    assert pd.newcombe_paired_lower(20, 0, 5, 5) > pd.newcombe_paired_lower(20, 5, 0, 5)


def test_mismatched_task_ids_error():
    a = _pool([True] * 5)
    b = _pool([True] * 4) + [{"task_id": "zzz", "pass_": True, "error": ""}]
    with pytest.raises(pd.PairingError):
        pd.decide_pool(a, b)


def test_duplicate_task_ids_error():
    a = _pool([True] * 3) + [{"task_id": "t0", "pass_": True, "error": ""}]
    with pytest.raises(pd.PairingError):
        pd.decide_pool(a, a)


def test_blanks_inconclusive():
    base = _suite("none", _pool(_same()), _pool(_same()), _pool(_same()))
    cand = _suite("mild", _pool(_same()), _pool(_same(), err={3}), _pool(_same()))
    r = pd.decide(base, cand)
    assert r["pools"]["procedure"]["verdict"] == "INCONCLUSIVE"
    assert r["overall"] == "INCONCLUSIVE"


def test_blank_inconclusive_even_when_another_pool_drops():
    base = _suite("none", _pool([True] * 30), _pool(_same()), _pool(_same()))
    cand = _suite("x", _pool([False] * 30), _pool(_same(), err={0}), _pool(_same()))
    assert pd.decide(base, cand)["overall"] == "INCONCLUSIVE"


def test_main_exit_codes(tmp_path, capsys):
    keep = _suite("none", _pool(_same()), _pool(_same()), _pool(_same()))
    drop = _suite("x", _pool([False] * 30), _pool(_same()), _pool(_same()))
    blank = _suite("x", _pool(_same(), err={1}), _pool(_same()), _pool(_same()), blank_count=1)
    paths = {}
    for name, s in [("keep", keep), ("drop", drop), ("blank", blank)]:
        paths[name] = str(tmp_path / f"{name}.json")
        (tmp_path / f"{name}.json").write_text(json.dumps(s))
    assert pd.main([paths["keep"], paths["keep"]]) == 0
    assert pd.main([paths["keep"], paths["drop"]]) == 1
    assert pd.main([paths["keep"], paths["blank"]]) == 3
    assert json.loads(capsys.readouterr().out.split("\n}\n")[-2] + "\n}")["overall"] == "INCONCLUSIVE"
    assert pd.main([paths["keep"]]) == 2


def _mk(passes, markup=()):
    return [{"task_id": f"t{i}", "pass_": p, "error": "", "tool_verdict": "forced_markup" if i in markup else ""}
            for i, p in enumerate(passes)]


def test_forced_markup_excluded_from_both_arms_and_counted():
    # base fails on t0..t9 (markup in CAND on t0..t4 only) -> those 5 dropped from BOTH arms
    base = _mk([False] * 10 + [True] * 20)
    cand = _mk([False] * 10 + [True] * 20, markup=range(5))
    r = pd.decide_pool(base, cand)
    assert r["n"] == 25 and r["excluded_forced_markup"] == 5 and r["both_fail"] == 5 and r["both_pass"] == 20


def test_forced_markup_in_base_arm_excludes_pair_too_and_cannot_cause_drop():
    base = _mk([True] * 30, markup=range(5))      # base markup on 5 tasks
    cand = _mk([False] * 5 + [True] * 25)         # cand fails exactly those 5; without exclusion this is a DROP
    assert pd.decide_pool(_mk([True] * 30), cand)["verdict"] == "DROP"
    r = pd.decide_pool(base, cand)
    assert r["n"] == 25 and r["excluded_forced_markup"] == 5 and r["b"] == 0 and r["verdict"] == "KEEP"


def test_decide_reports_excluded_counts_per_pool_and_task_id_check_is_unchanged():
    base = _suite("none", _mk([True] * 30, markup=[0]), _mk([True] * 30), _mk([True] * 30, markup=[1, 2]))
    cand = _suite("mild", _mk([True] * 30), _mk([True] * 30, markup=[5]), _mk([True] * 30))
    r = pd.decide(base, cand)
    assert r["excluded_forced_markup"] == {"compliance": 1, "procedure": 1, "recall": 2}
    assert [p["n"] for p in r["pools"].values()] == [29, 29, 28] and r["overall"] == "KEEP"
    with pytest.raises(pd.PairingError):
        pd.decide_pool(_mk([True] * 3, markup=[0]), _mk([True] * 4))
    assert pd.decide_pool(_pool(_same()), _pool(_same()))["excluded_forced_markup"] == 0
