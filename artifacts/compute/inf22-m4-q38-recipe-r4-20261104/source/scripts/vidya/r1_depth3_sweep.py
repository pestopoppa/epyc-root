"""Detection power for the depth-3 sweep: does it catch a route already known to be wrong?

A null across 40,500 instances is worth nothing unless the same harness can see a wrong answer at
this depth. Plain circuit specialization was refuted at depth 2 (2,241 of 5,670), so running it
here is the control: if depth 3 reports 0 for it too, the sweep is blind and the null means nothing.
"""
import itertools
import sys

sys.path.insert(0, "scripts/vidya")
from lattice import BOTTOM, parse_grade  # noqa: E402
from r1_search import Rule, _eval_positive, _eval_stratum2  # noqa: E402
from r1_search import stratum2_circuit, stratum2_circuit_dual_closed  # noqa: E402

TOP_G = parse_grade("Witnessed/Attested")
MID_G = parse_grade("Verified/Anchored")
LOW_G = parse_grade("Judged/Located")


def eval_all(strata, facts):
    cur = {k: v for k, v in _eval_positive(strata[0], facts).items() if v != BOTTOM}
    for rules in strata[1:]:
        cur = {k: v for k, v in _eval_stratum2(rules, cur, dict(cur)).items() if v != BOTTOM}
    return cur


def route(strata, base_values, retract, circuit_fn):
    pre = {k: v for k, v in _eval_positive(strata[0], base_values).items() if v != BOTTOM}
    circuits, cur = [], pre
    for rules in strata[1:]:
        circuits.append(circuit_fn(rules, cur))
        cur = {k: v for k, v in _eval_stratum2(rules, cur, dict(cur)).items() if v != BOTTOM}
    specialized = {k: v for k, v in base_values.items() if k != retract}
    cur = {k: v for k, v in _eval_positive(strata[0], specialized).items() if v != BOTTOM}
    for c in circuits:
        cur = {k: v for k, v in _eval_stratum2(c, cur, dict(cur)).items() if v != BOTTOM}
    return cur


S1 = [Rule("p", ("a",)), Rule("p", ("b",)), Rule("q", ("b",)), Rule("q", ("a", "b"))]
S2 = [Rule("r", (), ("p",)), Rule("r", ("b",), ("p",)), Rule("s", (), ("q",)),
      Rule("s", ("r",)), Rule("r", ("a",), ("q",))]
S3 = [Rule("t", (), ("r",)), Rule("t", ("a",), ("s",)), Rule("u", (), ("s",)),
      Rule("u", ("t",)), Rule("t", ("q",), ("s",))]

grades = (TOP_G, MID_G, LOW_G)
counts = {"dual_closed": 0, "plain_circuit": 0}
checked = 0
for n1 in (1, 2):
    for s1 in itertools.combinations(S1, n1):
        for n2 in (1, 2):
            for s2 in itertools.combinations(S2, n2):
                for n3 in (1, 2):
                    for s3 in itertools.combinations(S3, n3):
                        strata = [list(s1), list(s2), list(s3)]
                        for values in itertools.product(grades, repeat=2):
                            bv = dict(zip(("a", "b"), values))
                            for retract in ("a", "b"):
                                checked += 1
                                truth = eval_all(
                                    strata, {k: v for k, v in bv.items() if k != retract})
                                if route(strata, bv, retract,
                                         stratum2_circuit_dual_closed) != truth:
                                    counts["dual_closed"] += 1
                                if route(strata, bv, retract, stratum2_circuit) != truth:
                                    counts["plain_circuit"] += 1

print(f"three-stratum instances: {checked}")
print(f"  dual-closed route counterexamples:   {counts['dual_closed']}")
print(f"  plain-circuit route counterexamples: {counts['plain_circuit']}  <- detection control")
if counts["plain_circuit"] == 0:
    print("\nWARNING: the sweep is BLIND at this depth. The null means nothing.")
