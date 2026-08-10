"""R1b — the four retraction routes across a negation boundary.

These tests exist because the 2026-08-09 null result was vacuous: `route_a_incremental` and
`route_b_ground_truth` reduce to the same expression, so their agreement over 5,670 instances
measured nothing. The first test below pins that equivalence explicitly, so the vacuity is a
recorded property rather than a thing someone has to re-derive from two function bodies.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import r1_search as R  # noqa: E402

GRADES = (R.TOP_G, R.MID_G, R.LOW_G)


def _instances():
    for prog in R._programs():
        for values in itertools.product(GRADES, repeat=len(prog.base)):
            base_values = dict(zip(prog.base, values))
            for retract in prog.base:
                yield prog, base_values, retract


def test_reevaluation_route_is_ground_truth_by_construction():
    """Not a result: specializing-then-dropping-BOTTOM IS deletion, so these cannot disagree."""
    for prog, bv, retract in _instances():
        assert R.route_a_incremental(prog, bv, retract) == R.route_b_ground_truth(prog, bv, retract)


def test_circuit_specialization_is_refuted():
    """Minimal counterexample: `p :- a`, `r :- not p`, retract `a`.

    `r` did not fire before the retraction, so the recorded circuit has no node for it; after the
    retraction it should hold. A deletion below a negation is a deletion composed with an
    insertion above, and an expression store records only what was derived.
    """
    prog = R.Program(base=("a", "b"), stratum1=(R.Rule("p", ("a",)),),
                     stratum2=(R.Rule("r", (), ("p",)),))
    bv = {"a": R.TOP_G, "b": R.TOP_G}
    assert "r" not in R.route_a_circuit(prog, bv, "a")
    assert "r" in R.route_b_ground_truth(prog, bv, "a")


def test_dual_tokens_repair_most_but_not_all():
    """Residual failures are intra-stratum chaining off a negation-derived atom."""
    prog = R.Program(
        base=("a", "b"),
        stratum1=(R.Rule("p", ("a",)),),
        stratum2=(R.Rule("r", (), ("p",)), R.Rule("s", ("r",))),
    )
    bv = {"a": R.TOP_G, "b": R.TOP_G}
    dual = R.route_a_circuit_dual(prog, bv, "a")
    truth = R.route_b_ground_truth(prog, bv, "a")
    assert "r" in dual and "s" not in dual
    assert "s" in truth


def test_dual_closed_route_is_exact_over_the_whole_sweep():
    """The bounded positive result: dual tokens + intra-stratum closure, 0 counterexamples."""
    checked = 0
    for prog, bv, retract in _instances():
        checked += 1
        assert R.route_a_circuit_dual_closed(prog, bv, retract) == R.route_b_ground_truth(
            prog, bv, retract
        ), f"counterexample: {prog.label()} retract {retract}"
    assert checked == 5670, "sweep size changed; the recorded bound must be updated with it"


def test_counterexample_counts_are_the_recorded_ones():
    """Pins the measured refutation rates so a silent change to the routes is visible."""
    counts = {"circuit": 0, "dual": 0}
    for prog, bv, retract in _instances():
        truth = R.route_b_ground_truth(prog, bv, retract)
        if R.route_a_circuit(prog, bv, retract) != truth:
            counts["circuit"] += 1
        if R.route_a_circuit_dual(prog, bv, retract) != truth:
            counts["dual"] += 1
    assert counts == {"circuit": 2241, "dual": 270}


# ---------------------------------------- stratum evaluation must not depend on rule order

def test_a_stratum_is_a_fixpoint_not_a_single_pass():
    """`s :- r` listed BEFORE the rule deriving `r` must still derive `s`.

    A single pass made rule order change the meaning of a stratum, which produced 1,836 spurious
    "counterexamples" in the first three-stratum sweep. The evaluator was wrong, not the route —
    caught by suspecting the test method before believing the refutation.
    """
    lower = {"a": R.TOP_G}
    ordered = [R.Rule("s", ("r",)), R.Rule("r", ("a",))]
    reversed_ = [R.Rule("r", ("a",)), R.Rule("s", ("r",))]
    assert R._eval_stratum2(ordered, lower, dict(lower)) == \
        R._eval_stratum2(reversed_, lower, dict(lower))
    assert "s" in R._eval_stratum2(ordered, lower, dict(lower))


# ---------------------------------- R1b RESOLVED: exact at one boundary, refuted across two


def _eval_all(strata, facts):
    cur = {k: v for k, v in R._eval_positive(strata[0], facts).items() if v != R.BOTTOM}
    for rules in strata[1:]:
        cur = {k: v for k, v in R._eval_stratum2(rules, cur, dict(cur)).items() if v != R.BOTTOM}
    return cur


def _dual_closed(strata, base, retract):
    pre = {k: v for k, v in R._eval_positive(strata[0], base).items() if v != R.BOTTOM}
    circuits, cur = [], pre
    for rules in strata[1:]:
        circuits.append(R.stratum2_circuit_dual_closed(rules, cur))
        cur = {k: v for k, v in R._eval_stratum2(rules, cur, dict(cur)).items() if v != R.BOTTOM}
    post = {k: v for k, v in base.items() if k != retract}
    cur = {k: v for k, v in R._eval_positive(strata[0], post).items() if v != R.BOTTOM}
    for c in circuits:
        cur = {k: v for k, v in R._eval_stratum2(c, cur, dict(cur)).items() if v != R.BOTTOM}
    return cur


ADVERSARIAL = [
    [R.Rule("p", ("a",))],          # positive
    [R.Rule("r", (), ("p",))],      # r exists only once `a` is retracted
    [R.Rule("t", ("r",))],          # positive body needing that post-retraction-only atom
]


def test_dual_closed_is_REFUTED_across_two_negation_boundaries():
    """Three rules settle what 40,500 swept instances missed.

    The stratum-3 closure is seeded from the atoms stratum 2 DERIVED before the retraction, so a
    rule whose body needs an atom appearing only AFTER it is never recorded. Constructed by
    reasoning about where the single-boundary argument breaks, not found by searching.
    """
    truth = _eval_all(ADVERSARIAL, {})
    got = _dual_closed(ADVERSARIAL, {"a": R.TOP_G}, "a")
    assert "t" in truth, "ground truth derives t once a is gone"
    assert "t" not in got, "the route misses it — that is the refutation"


def test_seeding_the_closure_with_possible_heads_repairs_it():
    """The repair: seed each closure with heads the stratum below COULD derive, not did."""
    def closure_over(rules, available):
        rules, recorded, avail, changed = list(rules), [], set(available), True
        while changed:
            changed = False
            for r in rules:
                if r not in recorded and all(b in avail for b in r.body):
                    recorded.append(r)
                    avail.add(r.head)
                    changed = True
        return recorded

    pre = {k: v for k, v in R._eval_positive(ADVERSARIAL[0], {"a": R.TOP_G}).items()
           if v != R.BOTTOM}
    circuits, avail = [], set(pre)
    for rules in ADVERSARIAL[1:]:
        circuits.append(closure_over(rules, avail))
        avail = avail | {r.head for r in rules}
    cur = {}
    for c in circuits:
        cur = {k: v for k, v in R._eval_stratum2(c, cur, dict(cur)).items() if v != R.BOTTOM}
    assert "t" in cur, "the repaired closure records the rule and derives t"
