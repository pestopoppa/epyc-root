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
