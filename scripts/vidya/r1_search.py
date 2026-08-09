"""R1b — exhaustive counterexample search for the stratum-boundary conjecture.

Conjecture (research/deep-dives/vidya-r1-r2-stratified-negation.md §2.3): evaluating a stratified
program stratum-by-stratum, freezing each stratum's (presence, absence) pair and re-tokenizing it
for the stratum above, agrees with a from-scratch recomputation -- INCLUDING when a retraction
flips a lower-stratum value and thereby adds facts above.

A proof is hard. A counterexample is cheap, and settles the engineering question permanently, so
this searches for one. Two evaluators are implemented independently and compared on every small
program:

    ROUTE A (incremental)  evaluate stratum 1; specialize by zeroing the retracted token;
                           re-tokenize the resulting pairs; evaluate stratum 2 against them.
    ROUTE B (ground truth) delete the fact from the base set and recompute both strata from
                           scratch. Exact by definition.

Disagreement on any instance refutes the conjecture. Agreement across an exhaustive small-program
sweep is NOT a proof -- it is a bounded verification result, and it is reported as such.

The programs are deliberately tiny and the sweep exhaustive rather than random: the interesting
behaviour is at the stratum boundary, which needs only a couple of rules to exhibit, and an
exhaustive sweep of small cases is worth more than a sample of large ones.
"""

from __future__ import annotations

import itertools
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lattice import BOTTOM, Grade, join, meet, parse_grade  # noqa: E402

__all__ = ["Rule", "Program", "search", "SearchResult"]

TOP_G = parse_grade("Witnessed/Attested")
MID_G = parse_grade("Verified/Anchored")
LOW_G = parse_grade("Judged/Located")


@dataclass(frozen=True)
class Rule:
    """head :- body, not negated.  `negated` may only name stratum-1 atoms (stratification)."""

    head: str
    body: tuple[str, ...] = ()
    negated: tuple[str, ...] = ()


@dataclass(frozen=True)
class Program:
    base: tuple[str, ...]          # base facts (stratum 0)
    stratum1: tuple[Rule, ...]     # positive rules over base
    stratum2: tuple[Rule, ...]     # rules that may negate stratum-1 atoms

    def label(self) -> str:
        def r(rule: Rule) -> str:
            parts = list(rule.body) + [f"not {n}" for n in rule.negated]
            return f"{rule.head} :- {', '.join(parts) or 'true'}"
        return " | ".join(
            [f"base={{{','.join(self.base)}}}"]
            + [r(x) for x in self.stratum1]
            + [r(x) for x in self.stratum2]
        )


def _eval_positive(
    rules: Iterable[Rule], facts: dict[str, Grade], rounds: int = 8
) -> dict[str, Grade]:
    """Least fixpoint of positive rules over graded facts. Meet along a body, join across rules."""
    out = dict(facts)
    for _ in range(rounds):
        changed = False
        for rule in rules:
            if rule.negated:
                raise ValueError("positive evaluation received a negated body")
            if any(b not in out for b in rule.body):
                continue
            value = TOP_G
            for b in rule.body:
                value = meet(value, out[b])
            prior = out.get(rule.head, BOTTOM)
            merged = join(prior, value)
            if merged != prior:
                out[rule.head] = merged
                changed = True
        if not changed:
            break
    return out


def _eval_stratum2(
    rules: Iterable[Rule], lower: dict[str, Grade], carried: dict[str, Grade]
) -> dict[str, Grade]:
    """Evaluate stratum 2. A negated atom contributes its ABSENCE grade.

    Absence is modelled as the dual: an atom absent from the lower stratum contributes TOP (its
    negation is fully warranted by the closed lower stratum); an atom present contributes BOTTOM
    (its negation has no support). This is the two-valued specialization of the dual-indeterminate
    treatment, which is what makes the two routes comparable at all.
    """
    out = dict(carried)
    for rule in rules:
        if any(b not in out and b not in lower for b in rule.body):
            continue
        value = TOP_G
        for b in rule.body:
            value = meet(value, out.get(b, lower.get(b, BOTTOM)))
        for n in rule.negated:
            present = lower.get(n, BOTTOM)
            value = meet(value, BOTTOM if present != BOTTOM else TOP_G)
        if value != BOTTOM:
            out[rule.head] = join(out.get(rule.head, BOTTOM), value)
    return out


def route_b_ground_truth(prog: Program, base_values: dict[str, Grade], retract: str) -> dict:
    """Delete the fact and recompute everything. Exact by definition."""
    facts = {k: v for k, v in base_values.items() if k != retract}
    lower = _eval_positive(prog.stratum1, facts)
    lower = {k: v for k, v in lower.items() if v != BOTTOM}
    return _eval_stratum2(prog.stratum2, lower, dict(lower))


def route_a_incremental(prog: Program, base_values: dict[str, Grade], retract: str) -> dict:
    """Specialize stratum 1 by zeroing the token, re-tokenize the pairs, evaluate stratum 2.

    The re-tokenization is the step the conjecture is about: stratum 1's (presence, absence) pairs
    are frozen and handed to stratum 2 as if they were fresh base facts.
    """
    specialized = {k: (BOTTOM if k == retract else v) for k, v in base_values.items()}
    specialized = {k: v for k, v in specialized.items() if v != BOTTOM}
    lower = _eval_positive(prog.stratum1, specialized)
    frozen = {k: v for k, v in lower.items() if v != BOTTOM}
    return _eval_stratum2(prog.stratum2, frozen, dict(frozen))


@dataclass
class SearchResult:
    checked: int
    counterexamples: list[dict]
    boundary_growth_max: int

    def as_dict(self) -> dict:
        return {
            "programs_checked": self.checked,
            "counterexamples": self.counterexamples,
            "counterexample_count": len(self.counterexamples),
            "max_boundary_growth": self.boundary_growth_max,
            "interpretation": (
                "Agreement across an exhaustive small-program sweep is a BOUNDED VERIFICATION "
                "RESULT, not a proof. It rules out the conjecture failing for a simple structural "
                "reason at this size, and nothing more."
                if not self.counterexamples
                else "REFUTED: stratum-wise specialization disagrees with from-scratch "
                     "recomputation on the instance(s) below."
            ),
        }


def _programs() -> Iterable[Program]:
    """Exhaustive sweep of small two-stratum shapes, including the growth-inducing ones."""
    atoms1, atoms2 = ("p", "q"), ("r", "s")
    bases = ("a", "b")
    s1_candidates = [
        Rule("p", ("a",)), Rule("p", ("b",)), Rule("q", ("b",)),
        Rule("q", ("a", "b")), Rule("p", ("a", "b")),
    ]
    s2_candidates = [
        # The load-bearing shapes: a negated lower atom, so deleting a base fact can ADD a
        # higher-stratum fact rather than only remove one.
        Rule("r", (), ("p",)), Rule("r", ("b",), ("p",)), Rule("s", (), ("q",)),
        Rule("s", ("a",), ("p",)), Rule("r", ("a",), ("q",)),
        Rule("s", ("r",)),                      # stratum-2 chaining off a negation-derived atom
    ]
    for n1 in (1, 2):
        for s1 in itertools.combinations(s1_candidates, n1):
            for n2 in (1, 2):
                for s2 in itertools.combinations(s2_candidates, n2):
                    yield Program(base=bases, stratum1=s1, stratum2=s2)


def search(verbose: bool = False) -> SearchResult:
    grades = (TOP_G, MID_G, LOW_G)
    counterexamples: list[dict] = []
    checked = 0
    growth = 0

    for prog in _programs():
        for values in itertools.product(grades, repeat=len(prog.base)):
            base_values = dict(zip(prog.base, values))
            for retract in prog.base:
                checked += 1
                a = route_a_incremental(prog, base_values, retract)
                b = route_b_ground_truth(prog, base_values, retract)

                before = _eval_stratum2(
                    prog.stratum2,
                    {k: v for k, v in _eval_positive(prog.stratum1, base_values).items()
                     if v != BOTTOM},
                    {k: v for k, v in _eval_positive(prog.stratum1, base_values).items()
                     if v != BOTTOM},
                )
                added = set(b) - set(before)
                growth = max(growth, len(added))

                if a != b:
                    counterexamples.append({
                        "program": prog.label(),
                        "base_values": {k: str(v) for k, v in base_values.items()},
                        "retracted": retract,
                        "route_a_incremental": {k: str(v) for k, v in sorted(a.items())},
                        "route_b_ground_truth": {k: str(v) for k, v in sorted(b.items())},
                        "facts_added_by_the_retraction": sorted(added),
                    })
                    if verbose:
                        print("COUNTEREXAMPLE:", prog.label(), "retract", retract)

    return SearchResult(checked=checked, counterexamples=counterexamples,
                        boundary_growth_max=growth)


if __name__ == "__main__":
    import json

    print(json.dumps(search().as_dict(), indent=2)[:4000])
