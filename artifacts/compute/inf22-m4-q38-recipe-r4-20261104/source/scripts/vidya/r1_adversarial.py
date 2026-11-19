"""R1b: construct the case the dual-closed route MUST fail, instead of sweeping for it.

Reasoning first, search second.

For a SINGLE boundary the route is provably exact, and the proof is short. Stratum 1 is positive,
so retraction is monotone downward: lower_post ⊆ lower_pre. The recorded set S is the closure of
"rules whose positive body atoms are in lower_pre ∪ heads(S)", and that closure is monotone in its
base set, so the post-retraction closure S' ⊆ S. Every rule that can fire after the retraction is
therefore already in S, and re-evaluating S against the new lower stratum derives exactly what full
re-evaluation derives.

That argument breaks at the SECOND boundary, and it breaks in a specific place. Across a negation
boundary retraction is NOT monotone downward: removing a base fact can make a negated guard true
and ADD an atom at stratum 2. So lower_post(2) ⊄ lower_pre(2). A stratum-3 rule whose positive body
needs an atom that appears ONLY after the retraction was never recorded, because the closure was
computed over lower_pre(2) where that atom was absent.

Concretely:

    stratum 1:  p :- a
    stratum 2:  r :- not p          # r exists only once `a` is retracted
    stratum 3:  t :- r              # positive body, needs the atom that only then exists

Pre-retraction `p` holds, so `r` is absent, so `t :- r` is excluded from the stratum-3 circuit.
Retract `a`: `p` goes, `r` appears, full re-evaluation derives `t` — and the recorded circuit has
no node for it.

If that runs and disagrees, R1b is settled in the refutation direction for composition, and the
40,500-instance null just means the sweep never generated this shape.
"""
import sys

sys.path.insert(0, "scripts/vidya")
from lattice import BOTTOM, parse_grade  # noqa: E402
from r1_search import Rule, _eval_positive, _eval_stratum2  # noqa: E402
from r1_search import stratum2_circuit_dual_closed  # noqa: E402

TOP = parse_grade("Witnessed/Attested")


def eval_all(strata, facts):
    cur = {k: v for k, v in _eval_positive(strata[0], facts).items() if v != BOTTOM}
    for rules in strata[1:]:
        cur = {k: v for k, v in _eval_stratum2(rules, cur, dict(cur)).items() if v != BOTTOM}
    return cur


def dual_closed(strata, base_values, retract):
    pre = {k: v for k, v in _eval_positive(strata[0], base_values).items() if v != BOTTOM}
    circuits, cur = [], pre
    for rules in strata[1:]:
        circuits.append(stratum2_circuit_dual_closed(rules, cur))
        cur = {k: v for k, v in _eval_stratum2(rules, cur, dict(cur)).items() if v != BOTTOM}
    post = {k: v for k, v in base_values.items() if k != retract}
    cur = {k: v for k, v in _eval_positive(strata[0], post).items() if v != BOTTOM}
    for c in circuits:
        cur = {k: v for k, v in _eval_stratum2(c, cur, dict(cur)).items() if v != BOTTOM}
    return cur, circuits


STRATA = [
    [Rule("p", ("a",))],            # stratum 1, positive
    [Rule("r", (), ("p",))],        # stratum 2, r appears only when p is gone
    [Rule("t", ("r",))],            # stratum 3, POSITIVE body needing that atom
]
BASE = {"a": TOP}

print("program:")
for i, s in enumerate(STRATA, 1):
    for r in s:
        neg = f", not {r.negated}" if r.negated else ""
        print(f"  stratum {i}:  {r.head} :- {r.body or '()'}{neg}")
print(f"base: {[f'{k}={v}' for k, v in BASE.items()]}\n")

before = eval_all(STRATA, BASE)
truth = eval_all(STRATA, {k: v for k, v in BASE.items() if k != "a"})
got, circuits = dual_closed(STRATA, BASE, "a")

print("before retraction :", {k: str(v) for k, v in sorted(before.items())})
print("recorded circuits :", [[f'{r.head}:-{r.body or "()"}' for r in c] for c in circuits])
print("GROUND TRUTH      :", {k: str(v) for k, v in sorted(truth.items())})
print("dual-closed route :", {k: str(v) for k, v in sorted(got.items())})

if got != truth:
    missing = sorted(set(truth) - set(got))
    print(f"\n*** COUNTEREXAMPLE. The route misses {missing}. ***")
    print("R1b is REFUTED for composition across two negation boundaries:")
    print("the stratum-3 closure is computed over the PRE-retraction stratum-2 atoms, so a rule")
    print("whose body needs a post-retraction-only atom is never recorded.")
else:
    print("\nno disagreement — the constructed case does not break it; investigate why")
