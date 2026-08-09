"""The Q x T grade carrier.

Spec: docs/design/vidya-pilot-spec.md §4 (ratified 2026-08-09).

    Q (warrant quality)  Q0 . Hinted . Judged . Verified . Witnessed
    T (traceability)     T0 . Located . Anchored . Attested

    join = pointwise max (alternative support)
    meet = pointwise min (joint / chained support)
    0    = (Q0, T0)      1 = (Q4, T3)

A product of two finite chains is a bounded distributive lattice, which is the hypothesis class
the pilot's formal results actually require -- absorptive, 0-stable, meet-idempotent, fully
continuous. Every theorem the fold leans on survives the move from the v1 chain unchanged.

The one real cost, and the reason `join_with_witnesses` exists: in a chain, join is a *selection*
operator, so the folded value is always one of the inputs and you can point at the path that
produced it. Here it is not. If path A is (Verified, Located) and path B is (Judged, Anchored),
the join is (Verified, Anchored) -- a grade no single path achieves. The join is still the right
answer to "is anything verified, and is anything anchored?", but it is the WRONG answer to "is one
thing both?", so this module exposes those as two different operations and never lets a caller
get the second by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

__all__ = [
    "Q_LEVELS", "T_LEVELS", "Grade", "BOTTOM", "TOP",
    "join", "meet", "join_all", "meet_all", "join_with_witnesses",
    "meets_floor", "satisfies_conjunctive", "parse_grade",
]

# Ordinals are the storage form; names are for display and policy files. Q4 is deliberately narrow
# -- it means "would be admissible as a decision-gating measurement claim", and the measurement
# constitution is the arbiter of that, not this module.
Q_LEVELS: Sequence[str] = ("Q0", "Hinted", "Judged", "Verified", "Witnessed")
T_LEVELS: Sequence[str] = ("T0", "Located", "Anchored", "Attested")

_Q_INDEX = {name: i for i, name in enumerate(Q_LEVELS)}
_T_INDEX = {name: i for i, name in enumerate(T_LEVELS)}


@dataclass(frozen=True, order=False)
class Grade:
    """A point in the Q x T lattice.

    Ordering is the PARTIAL product order, so `<=` can be False in both directions: (Verified,
    Located) and (Judged, Anchored) are incomparable, which is the whole point of factoring the
    axes. Python's total-ordering helpers are deliberately not used -- a sort needs an explicit
    tiebreak (see `sort_key`), and silently inventing one here is how the v1 chain got its
    indefensible `Corroborated < Traced`.
    """

    q: int
    t: int

    def __post_init__(self) -> None:
        if not (0 <= self.q < len(Q_LEVELS)):
            raise ValueError(f"q out of range: {self.q}")
        if not (0 <= self.t < len(T_LEVELS)):
            raise ValueError(f"t out of range: {self.t}")

    # -- display ---------------------------------------------------------
    @property
    def q_name(self) -> str:
        return Q_LEVELS[self.q]

    @property
    def t_name(self) -> str:
        return T_LEVELS[self.t]

    def __str__(self) -> str:
        return f"{self.q_name}/{self.t_name}"

    def as_dict(self) -> dict:
        return {"Q": self.q_name, "T": self.t_name}

    # -- lattice order ---------------------------------------------------
    def dominates(self, other: "Grade") -> bool:
        """True iff self >= other in the product order (both coordinates)."""
        return self.q >= other.q and self.t >= other.t

    def comparable(self, other: "Grade") -> bool:
        return self.dominates(other) or other.dominates(self)

    def sort_key(self) -> tuple[int, int]:
        """An EXPLICIT total order for display only.

        Never use this to decide support: it imposes a ranking the lattice does not have.
        """
        return (self.q, self.t)


BOTTOM = Grade(0, 0)
TOP = Grade(len(Q_LEVELS) - 1, len(T_LEVELS) - 1)


def parse_grade(value) -> Grade:
    """Accept ``Grade``, ``{"Q": "Verified", "T": "Anchored"}``, or ``"Verified/Anchored"``."""
    if isinstance(value, Grade):
        return value
    if isinstance(value, dict):
        q, t = value.get("Q"), value.get("T")
    elif isinstance(value, str) and "/" in value:
        q, t = value.split("/", 1)
    else:
        raise ValueError(f"cannot parse grade from {value!r}")
    if q not in _Q_INDEX:
        raise ValueError(f"unknown Q level {q!r} (expected one of {list(Q_LEVELS)})")
    if t not in _T_INDEX:
        raise ValueError(f"unknown T level {t!r} (expected one of {list(T_LEVELS)})")
    return Grade(_Q_INDEX[q], _T_INDEX[t])


# -- semiring operations -------------------------------------------------

def join(a: Grade, b: Grade) -> Grade:
    """Alternative support: pointwise max. The semiring's addition."""
    return Grade(max(a.q, b.q), max(a.t, b.t))


def meet(a: Grade, b: Grade) -> Grade:
    """Joint / chained support: pointwise min. The semiring's multiplication.

    A derivation is only as strong as its weakest required step, on each axis independently.
    """
    return Grade(min(a.q, b.q), min(a.t, b.t))


def join_all(grades: Iterable[Grade]) -> Grade:
    result = BOTTOM
    for g in grades:
        result = join(result, g)
    return result


def meet_all(grades: Iterable[Grade]) -> Grade:
    result = TOP
    for g in grades:
        result = meet(result, g)
    return result


def join_with_witnesses(
    paths: Sequence[tuple[str, Grade]],
) -> tuple[Grade, list[str]]:
    """Join a set of labelled support paths, returning the join AND a minimal witness set.

    The witness set is the smallest set of paths that jointly achieve the join -- at most two for
    a two-axis lattice, one per coordinate. This is what keeps a synthetic join honest: "Verified
    by path A; anchored by path B" says more than the v1 chain's single number ever could, and it
    makes it obvious when no single path achieved the reported grade.

    Returns ``(BOTTOM, [])`` for an empty input.
    """
    if not paths:
        return BOTTOM, []

    result = join_all(g for _, g in paths)

    # Prefer a single path that achieves the join outright -- when one exists, the join is a
    # selection after all and the witness set should say so.
    for label, g in paths:
        if g == result:
            return result, [label]

    witnesses: list[str] = []
    best_q = max(paths, key=lambda p: (p[1].q, p[1].t))
    witnesses.append(best_q[0])
    best_t = max(paths, key=lambda p: (p[1].t, p[1].q))
    if best_t[0] not in witnesses:
        witnesses.append(best_t[0])
    return result, witnesses


# -- policy predicates ---------------------------------------------------

def meets_floor(grade: Grade, floor: Grade) -> bool:
    """Upward-closed threshold test: does `grade` clear both per-axis floors?

    A conjunction of per-axis floors is upward-closed, which is what the lattice requires of a
    policy threshold. Non-rectangular policies must be written as an explicit set of minimal
    accepted pairs (see `satisfies_any_floor`), never as an inequality.
    """
    return grade.dominates(floor)


def satisfies_any_floor(grade: Grade, floors: Iterable[Grade]) -> bool:
    """Accept if the grade clears ANY of a set of minimal accepted pairs.

    This is how a non-rectangular upward-closed policy is expressed -- e.g. accept
    (Witnessed, Located) or (Judged, Attested) but nothing strictly between them.
    """
    return any(grade.dominates(f) for f in floors)


def satisfies_conjunctive(
    paths: Sequence[tuple[str, Grade]], floor: Grade
) -> tuple[bool, list[str]]:
    """Does at least ONE path clear both floors by itself?

    This is the reading authoritative policies default to, and it is deliberately a different
    function from `join_with_witnesses` -- reading the join would answer a strictly weaker
    question ("some path is verified, some path is anchored") while looking like an answer to this
    one. Returns the satisfying paths so a certificate can name them.
    """
    satisfying = [label for label, g in paths if g.dominates(floor)]
    return bool(satisfying), satisfying
