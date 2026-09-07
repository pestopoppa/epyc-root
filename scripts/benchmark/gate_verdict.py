#!/usr/bin/env python3
"""scripts/benchmark/gate_verdict.py — THE ONE GATE VERDICT VOCABULARY.

Implements CJ-8 (three-valued gate verdicts) and CJ-9 (resolved coverage
alongside every verdict) from
``handoffs/active/canonical-judge-suite-revamp.md``.

WHY THIS MODULE EXISTS
----------------------
A two-valued gate — ``pass``/``fail``, ``True``/``False``, ``1.0``/``0.0`` — has
no way to say *"the checker never decided this item"*. So it says ``fail``, and
"no signal" becomes indistinguishable from "failed the check". The two events
have different remedies (fix the harness vs fix the model), and folding them
together makes the common one invisible.

The motivating corpus (`intake-1307#record`, an external observation — NOT a
measurement of this deployment, and never to be quoted as one) is the existence
proof: of 1,403 answer-class observations, **741 were never formalized at all**
and **zero timed out**. The entire bottleneck sat *before* the check ever ran.
A two-valued gate over that corpus reports a catastrophic failure rate and points
every remedy at the wrong subsystem.

The same corpus is why CJ-9 exists: winner accuracy was **0.96** where the
resolved mass dominated and **0.20** where it did not — the same judge, the same
protocol, a 4.8x swing driven only by coverage. A reliability figure quoted
without its coverage regime is unreadable, so this module refuses to emit one.

VOCABULARY REUSE — WHAT IS BORROWED AND WHAT IS NOT
---------------------------------------------------
This project already ratified a three-valued vocabulary for the **dashboard
plane**: ``dashboard/freshness.py`` ("THE ONE CLASSIFIER") and the
``/api/health`` fold in ``dashboard/panels.py`` (``ok`` / ``absent`` /
``degraded``), against ``/health``, which is transport-only. This module reuses
that plane's *structure* wholesale and deliberately does not reuse its *status
words*. The reasoning, stated here so nobody re-derives it:

* **Structure reused, verbatim in intent.**
  - *Three values, one of which means "nobody decided"* — the shape of
    ``ok``/``absent``/``degraded``, where ``absent`` is neither of the other two.
  - *Absence must say what absence MEANS* — ``PanelSource.absence_means`` is
    mandatory, enforced in ``__post_init__``. Here the mandatory cause code on
    ``out-of-coverage`` is the same enforcement at item granularity.
  - *Absent and empty are different values on the wire* — ``panels.envelope()``
    emits ``reporting`` and ``content`` as independent fields so "the producer
    reported nothing" cannot render as "no producer reported". The cause-code
    registry below keeps that split: ``absent`` vs ``empty`` vs ``unparsed`` are
    three causes, never one bucket.
  - *A fold is only a fold over its universe* — ``panels.fold({})`` is not
    ``ok``. Here, an **empty asserted surface suppresses the headline** rather
    than reporting a vacuous 100%.
  - *The verdict names who set it* — ``status_set_by`` vs ``worst``. Here
    ``suppression_reason`` names the coverage and the causes that caused it.

* **Status words NOT reused, and why.** ``ok``/``absent``/``degraded`` classify
  a **producer's liveness** — is this panel's upstream still reporting. A gate
  verdict classifies an **item's decision** — did the checker reach a verdict on
  this assertion. Those are different subjects: a fully live producer emits
  out-of-coverage items, and an absent producer emits none at all. Reusing the
  liveness words would put two subjects under one set of labels, which is the
  ``/health``-vs-``/api/health`` conflation that ``dashboard/README.md`` exists
  to warn about. CJ-8 also *names* its three values in the row text
  (``pass``/``fail``/``out-of-coverage``), and the row is the spec.

  The **cause codes**, by contrast, do reuse the panel words where the state is
  literally the same one: ``absent``, ``empty``, ``unknown``-adjacent, so a
  reader moving between the two planes reads one idiom.

* **No import edge.** ``dashboard/`` is the VIEW plane (``dashboard/README.md``
  → the plane rule). A measurement module must not import it, or a scoring run
  acquires a dependency on the hub. The correspondence is documented above and
  locked by a test, not by an import.

THE OTHER PRIOR ART THIS FOLLOWS (surveyed 2026-09-07; none of it is a second
vocabulary, all of it is the same rule at a different granularity):

* ``scripts/audit/deterministic_rescore_ledger.py:192`` ``classify_row`` — a
  three-valued ``disposition`` with a MANDATORY ``reason`` cause code, and a
  cause catalogue that is very nearly this one already: ``pool_miss``,
  ``method_unrecorded``, ``answer_not_persisted``, ``answer_empty``,
  ``no_stored_verdict``, ``scorer_unavailable``, ``scorer_error``. Its comment
  states the doctrine outright: *"Two different failures wear the same shape
  here and must not share a reason."* The cause codes below are that catalogue
  generalised off the rescore ledger's specific artifacts; a suite already
  emitting those strings maps onto ``CAUSES`` without a re-spelling.
* ``scripts/validate/check_ratification_receipts.py:25`` — ``PASS`` / ``FAIL`` /
  ``COULD-NOT-CHECK`` on exit codes 0/1/2, with the rule *"If the boundary list
  cannot be read, that is COULD-NOT-CHECK and exits non-zero — it is NOT 'no
  violations found'."* ``COULD-NOT-CHECK`` is this module's
  ``out-of-coverage`` at process granularity. CJ-8 names its own three values,
  so the spelling here follows the row; the semantics are identical.
* ``scripts/vidya/gate.py:32`` ``Outcome.ABSTAIN`` — "no such claim at this
  frontier", carried with ``reasons``. Same third value, belief-plane subject.
* ``scripts/coordination/backlog_row_check.py:770`` ``emit_verdict`` — the
  argument for why the third value must ride a channel a wrapper cannot drop.
  Honoured here by putting the cause ON the verdict object rather than in a log
  line beside it.
* ``scripts/benchmark/rustevo2_bench_preflight.py:134`` ``autopilot_state`` —
  ``present``/``absent``/``unobservable`` with a ``detail`` naming the channel
  that failed, and callers required to fail closed on ``unobservable``.

THE CLOSEST-FITTING PRIOR ART, AND THE INTEROP RULE
---------------------------------------------------
``epyc-orchestrator/orchestration/verification_report.schema.json`` is a
RATIFIED, MEASUREMENT-PLANE, three-valued check contract, and it is nearer to
CJ-8 than the dashboard plane is. It already carries every structural rule this
module needs:

* ``check.outcome`` enum ``["pass", "fail", "inconclusive"]``;
* ``inconclusive_reason`` **required** whenever the outcome is inconclusive —
  the mandatory cause code, already ratified;
* two orthogonal axes: ``logical_status`` (``pass``/``fail``/``unknown``/
  ``conflict`` — the epistemic verdict) and ``execution_status``
  (``ok``/``error``/``timeout``/``unavailable`` — the verifier's operational
  health), with the schema's own rule: *"Do not collapse tool failure into
  epistemic uncertainty"* and *"an error/timeout/unavailable is NOT proof of
  failure"*.

**This module does not compete with that schema; it maps onto it.**
``out-of-coverage`` IS ``inconclusive`` under a different name — CJ-8 names its
three values in the row text and the row is the spec, so the spelling here
follows the row while :func:`to_verification_outcome` and
:func:`from_verification_status` make the two losslessly interconvertible. Any
suite that already emits a verification report should keep doing so and convert
at the boundary; a suite emitting neither should adopt this module, whose cause
codes are a REFINEMENT of the schema's two axes rather than a replacement:

    cause              -> (logical_status, execution_status)
    absent                 unknown, unavailable   # nothing was produced
    empty                  unknown, ok            # produced, carried nothing
    unparsed               unknown, ok            # produced, unreadable
    no_reference           unknown, unavailable   # no oracle to decide against
    unsupported            unknown, unavailable   # outside competence
    abstained              unknown, ok            # ran, declined to decide
    checker_error          unknown, error
    timeout                unknown, timeout
    skipped                unknown, unavailable

Every cause maps to ``logical_status="unknown"`` by construction: that is what
``out-of-coverage`` MEANS, and a cause that mapped to ``fail`` would be a
``fail`` and belong on the other verdict.

**Standing recommendation to the operator (not executed here):** two spellings
for one state is a drift risk. Either this module's ``out-of-coverage`` or the
schema's ``inconclusive`` should eventually become the single word. That is a
naming ratification across two repositories, not an executor's call, so the
conversion helpers below are the interim and the divergence is documented rather
than silently introduced.

WHAT THIS MODULE REFUSES
------------------------
1. A verdict outside ``VERDICTS`` — including a bare ``bool`` or ``0``/``1``,
   which is the two-valued idiom this row exists to end.
2. ``out-of-coverage`` with no cause code, or with a cause outside the closed
   registry. A free-text cause is not foldable and would let the taxonomy drift
   back into one "other" bucket.
3. A decided verdict (``pass``/``fail``) that carries a cause code — a cause on
   a decided item means the caller does not know which of the two it emitted.
4. A suite that never declares ``min_resolved_coverage``. It is refused, not
   defaulted: a global default is exactly the "one number for everything" this
   row forbids, and a defaulted threshold is one nobody chose.
5. A headline whose suite fell below its declared threshold. The VALUE is
   removed from the report, not merely flagged — a flagged number still gets
   read.

This module is pure: stdlib only, no I/O, no clock, no network.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

__all__ = [
    "VERDICT_PASS", "VERDICT_FAIL", "VERDICT_OUT_OF_COVERAGE", "VERDICTS",
    "DECIDED_VERDICTS", "CAUSES", "SUITE_LEVEL_CAUSES", "ALL_CAUSES",
    "CAUSE_MEANINGS",
    "GateVerdictError", "NonCompliantVerdictError", "MissingCauseCodeError",
    "SpuriousCauseCodeError", "UndeclaredCoverageThresholdError",
    "DuplicateSuiteContractError",
    "GateVerdict", "SuiteCoverageContract", "SuiteReport",
    "out_of_coverage", "refuse_two_valued", "resolve_suite",
    "register_suite", "get_contract", "registered_suites",
    "to_verification_outcome", "from_verification_status",
    "VERIFICATION_OUTCOME_BY_VERDICT", "VERIFICATION_STATUS_BY_CAUSE",
]


# --------------------------------------------------------------------------- #
# Vocabulary — CJ-8
# --------------------------------------------------------------------------- #
#: The gate reached a decision and the assertion held.
VERDICT_PASS = "pass"
#: The gate reached a decision and the assertion did not hold.
VERDICT_FAIL = "fail"
#: The gate reached NO decision. This is not a negative label. It carries a
#: mandatory cause code naming *why* no decision was reached, because the four
#: reasons below have four different remedies and only the cause code tells them
#: apart.
VERDICT_OUT_OF_COVERAGE = "out-of-coverage"

#: WIRE SPELLING, ratified 2026-09-07 (scripts/operator/ratify_three_valued_verdict_naming_20260907.sh).
#: `inconclusive` -- the spelling already ratified in epyc-orchestrator's
#: orchestration/verification_report.schema.json -- is CANONICAL for anything that crosses a
#: repo or plane boundary or lands in a stored artifact. `out-of-coverage` stays as this
#: module's IN-CODE vocabulary, because at the gate plane the useful thing to say is which
#: items the checker never reached; `to_verification_outcome()` is the MANDATORY translator at
#: the boundary and is not optional politeness. Two spellings for one state is only safe while
#: exactly one of them is on the wire.
VERDICTS = (VERDICT_PASS, VERDICT_FAIL, VERDICT_OUT_OF_COVERAGE)
#: The verdicts that constitute a DECISION. The resolved-coverage numerator.
DECIDED_VERDICTS = frozenset({VERDICT_PASS, VERDICT_FAIL})

# --------------------------------------------------------------------------- #
# Cause codes — closed registry, mandatory on out-of-coverage
# --------------------------------------------------------------------------- #
#: Nothing was produced for this item at all. Mirrors ``panels.REPORTING_ABSENT``
#: paired with ``CONTENT_UNKNOWN``: no producer reported.
CAUSE_ABSENT = "absent"
#: Something was produced and it carried nothing. Mirrors ``reporting=observed,
#: content=empty``: the producer reported, and reported nothing. Kept apart from
#: ``absent`` for the exact reason ``panels.py`` keeps its two fields apart.
CAUSE_EMPTY = "empty"
#: A non-empty response arrived and no answer could be extracted from it. The
#: parse-failure scar: a parse-failure rate read as a quality gap is a SCORING
#: artifact, and it is invisible while parse failures score zero.
CAUSE_UNPARSED = "unparsed"
#: There is no gold/oracle/reference for this item, so nothing could be decided
#: against. Sibling of the ``paired_stats.require_matched_comparison`` provenance
#: gate, which refuses an unmatched pair to ``mismatched_pairs`` rather than
#: silently verdicting it.
CAUSE_NO_REFERENCE = "no_reference"
#: The item's shape is outside this checker's competence — e.g. a live-API tool
#: row handed to an offline deterministic checker. A declared incapacity, not a
#: failure of the subject.
CAUSE_UNSUPPORTED = "unsupported"
#: The checker ran and DECLINED to decide. An abstention is a decision not to
#: decide; it is not a ``fail``.
CAUSE_ABSTAINED = "abstained"
#: The checker itself raised. The item was never decided, and the defect is in
#: the instrument.
CAUSE_CHECKER_ERROR = "checker_error"
#: The checker exceeded its budget before deciding. Kept as its own cause even
#: though the motivating corpus measured ZERO of them — a count you cannot name
#: is a count you cannot know is zero.
CAUSE_TIMEOUT = "timeout"
#: The item was deliberately not run: outside the declared slice, filtered, or
#: gated. Compliant, declared, and still not a decision.
CAUSE_SKIPPED = "skipped"
#: SUITE-LEVEL ONLY. Emitted by :func:`resolve_suite` when the suite's own
#: resolved coverage fell below its declared threshold, so the suite verdict
#: itself is undecided. Never valid on a single item.
CAUSE_INSUFFICIENT_COVERAGE = "insufficient_coverage"

#: Causes valid on a single item's verdict.
CAUSES = (
    CAUSE_ABSENT, CAUSE_EMPTY, CAUSE_UNPARSED, CAUSE_NO_REFERENCE,
    CAUSE_UNSUPPORTED, CAUSE_ABSTAINED, CAUSE_CHECKER_ERROR, CAUSE_TIMEOUT,
    CAUSE_SKIPPED,
)
#: Causes valid only on a suite-level (folded) verdict.
SUITE_LEVEL_CAUSES = (CAUSE_INSUFFICIENT_COVERAGE,)
#: Every cause the vocabulary admits, at any granularity.
ALL_CAUSES = CAUSES + SUITE_LEVEL_CAUSES

#: Cause -> the remedy it points at. The whole point of the taxonomy: a reader
#: who sees the count must be able to tell which subsystem to go fix.
CAUSE_MEANINGS: Mapping[str, str] = {
    CAUSE_ABSENT: "no response/artifact was produced for this item — fix the "
                  "generation or transport path, not the model's quality",
    CAUSE_EMPTY: "a response arrived and carried nothing — fix generation "
                 "(budget, stop tokens, template), not the scorer",
    CAUSE_UNPARSED: "a non-empty response arrived and no answer could be "
                    "extracted — fix the extractor; a parse-failure rate read "
                    "as a quality gap is a scoring artifact",
    CAUSE_NO_REFERENCE: "no gold/oracle exists for this item — fix the corpus "
                        "join, not the subject",
    CAUSE_UNSUPPORTED: "the item is outside this checker's competence — either "
                       "build the substrate or exclude the slice explicitly",
    CAUSE_ABSTAINED: "the checker ran and declined to decide — an abstention, "
                     "not a negative label",
    CAUSE_CHECKER_ERROR: "the checker raised — the instrument is defective",
    CAUSE_TIMEOUT: "the checker exceeded its budget before deciding — raise the "
                   "budget or shrink the item",
    CAUSE_SKIPPED: "deliberately not run (outside the declared slice) — "
                   "compliant, declared, and still not a decision",
    CAUSE_INSUFFICIENT_COVERAGE: "the suite's resolved coverage fell below its "
                                 "declared threshold, so the suite verdict "
                                 "itself is undecided",
}


# --------------------------------------------------------------------------- #
# Refusals
# --------------------------------------------------------------------------- #
class GateVerdictError(ValueError):
    """Base for every refusal in this module. Subclasses ``ValueError`` so a
    caller that already guards ``ValueError`` does not silently swallow a
    compliance refusal as a different class of bug."""


class NonCompliantVerdictError(GateVerdictError):
    """A verdict value outside :data:`VERDICTS` — including a two-valued one."""


class MissingCauseCodeError(GateVerdictError):
    """``out-of-coverage`` with no cause code, or a cause outside the registry."""


class SpuriousCauseCodeError(GateVerdictError):
    """A decided verdict (``pass``/``fail``) carrying a cause code."""


class UndeclaredCoverageThresholdError(GateVerdictError):
    """A suite that never declared ``min_resolved_coverage``. Refused, never
    defaulted — a global default is the "one number for everything" CJ-9
    forbids, and a defaulted threshold is one nobody chose."""


class DuplicateSuiteContractError(GateVerdictError):
    """A second coverage contract registered under one suite name. One suite,
    one declared threshold — a second is a silent re-declaration."""


def refuse_two_valued(vocabulary: Iterable[str], *, suite: str = "<unnamed>") -> tuple:
    """Refuse any verdict vocabulary that is not exactly :data:`VERDICTS`.

    The named refusal for the CJ-8 headline rule: *a two-valued verdict is
    non-compliant*. A suite that declares ``("pass", "fail")`` has no way to
    spell "the checker never decided", so every undecided item lands in one of
    the two buckets it does have — and it will be ``fail``, because that is what
    ``score = 0`` means.
    """
    vocab = tuple(vocabulary)
    if set(vocab) != set(VERDICTS):
        missing = [v for v in VERDICTS if v not in set(vocab)]
        extra = [v for v in vocab if v not in set(VERDICTS)]
        raise NonCompliantVerdictError(
            f"suite {suite!r} declared verdict vocabulary {vocab!r}, which is not "
            f"the three-valued gate vocabulary {VERDICTS!r} "
            f"(missing={missing!r}, extra={extra!r}). A gate that cannot spell "
            f"{VERDICT_OUT_OF_COVERAGE!r} reports every undecided item as "
            f"{VERDICT_FAIL!r}."
        )
    return vocab


def _check_verdict(value: Any) -> str:
    # bool is a subclass of int; catch it FIRST and by name, because
    # ``True``/``False`` is the exact two-valued idiom being outlawed and a
    # generic "not in VERDICTS" message would not tell the caller why.
    if isinstance(value, bool) or value in (0, 1):
        raise NonCompliantVerdictError(
            f"verdict {value!r} is TWO-VALUED (a bool / 0-1 score). A two-valued "
            f"verdict is non-compliant: it has no way to spell "
            f"{VERDICT_OUT_OF_COVERAGE!r}, so an item the checker never decided "
            f"is reported as {VERDICT_FAIL!r}. Use one of {VERDICTS!r}."
        )
    if value not in VERDICTS:
        raise NonCompliantVerdictError(
            f"verdict {value!r} is not one of {VERDICTS!r}."
        )
    return value


# --------------------------------------------------------------------------- #
# The item-level verdict — CJ-8
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GateVerdict:
    """One gate's verdict on one asserted item.

    ``cause`` is MANDATORY on :data:`VERDICT_OUT_OF_COVERAGE` and FORBIDDEN on
    the two decided verdicts. That asymmetry is deliberate and is the same
    enforcement ``dashboard/panels.PanelSource`` applies to ``absence_means``:
    a state that means "nobody decided" must always say why, or its count is a
    number with no remedy attached to it.

    ``decided_proposition`` records WHAT the checker actually decided, which may
    be narrower than the claim the verdict is later cited for. Optional here
    (the belief substrate owns the binding rule), but present so a suite that
    can supply it is not forced to drop it on the floor.

    ``suite_level`` marks a FOLDED verdict — the verdict of a whole suite rather
    than of one asserted item. It widens the admissible cause set by exactly
    :data:`SUITE_LEVEL_CAUSES` and nothing else, so ``insufficient_coverage``
    can never be attached to an individual item (an item is not undecided
    because the *suite* was thin).
    """

    item_id: str
    verdict: str
    cause: Optional[str] = None
    detail: Optional[str] = None
    decided_proposition: Optional[str] = None
    suite_level: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "verdict", _check_verdict(self.verdict))
        admissible = ALL_CAUSES if self.suite_level else CAUSES
        if self.verdict == VERDICT_OUT_OF_COVERAGE:
            if self.cause is None:
                raise MissingCauseCodeError(
                    f"item {self.item_id!r}: {VERDICT_OUT_OF_COVERAGE!r} without a "
                    f"cause code. The cause is MANDATORY — an undecided count with "
                    f"no cause names no remedy, which is the failure this verdict "
                    f"exists to prevent. One of {admissible!r}."
                )
            if self.cause not in admissible:
                extra = (" (that cause is SUITE-LEVEL only and is never valid on a "
                         "single item)"
                         if self.cause in SUITE_LEVEL_CAUSES else "")
                raise MissingCauseCodeError(
                    f"item {self.item_id!r}: cause {self.cause!r} is outside the "
                    f"closed registry {admissible!r}{extra}. A free-text cause is "
                    f"not foldable and collapses the taxonomy into one 'other' "
                    f"bucket."
                )
        elif self.cause is not None:
            raise SpuriousCauseCodeError(
                f"item {self.item_id!r}: verdict {self.verdict!r} is a DECISION and "
                f"must not carry a cause code (got {self.cause!r}). A cause on a "
                f"decided item means the caller does not know which verdict it "
                f"emitted."
            )

    @property
    def decided(self) -> bool:
        """True iff this verdict counts toward the resolved-coverage numerator."""
        return self.verdict in DECIDED_VERDICTS

    def to_dict(self) -> dict:
        d = {"item_id": self.item_id, "verdict": self.verdict}
        if self.cause is not None:
            d["cause"] = self.cause
            d["cause_means"] = CAUSE_MEANINGS[self.cause]
        if self.detail is not None:
            d["detail"] = self.detail
        if self.decided_proposition is not None:
            d["decided_proposition"] = self.decided_proposition
        return d


#: cause -> (logical_status, execution_status) in the ratified
#: ``verification_report.schema.json`` axes. Total over :data:`ALL_CAUSES`.
VERIFICATION_STATUS_BY_CAUSE: Mapping[str, tuple] = {
    CAUSE_ABSENT: ("unknown", "unavailable"),
    CAUSE_EMPTY: ("unknown", "ok"),
    CAUSE_UNPARSED: ("unknown", "ok"),
    CAUSE_NO_REFERENCE: ("unknown", "unavailable"),
    CAUSE_UNSUPPORTED: ("unknown", "unavailable"),
    CAUSE_ABSTAINED: ("unknown", "ok"),
    CAUSE_CHECKER_ERROR: ("unknown", "error"),
    CAUSE_TIMEOUT: ("unknown", "timeout"),
    CAUSE_SKIPPED: ("unknown", "unavailable"),
    CAUSE_INSUFFICIENT_COVERAGE: ("unknown", "ok"),
}

#: ``out-of-coverage`` IS the schema's ``inconclusive``. One state, two spellings.
VERIFICATION_OUTCOME_BY_VERDICT: Mapping[str, str] = {
    VERDICT_PASS: "pass",
    VERDICT_FAIL: "fail",
    VERDICT_OUT_OF_COVERAGE: "inconclusive",
}


def to_verification_outcome(verdict: "GateVerdict") -> dict:
    """Project a gate verdict into ``verification_report.schema.json`` fields.

    Lossless in the direction that matters: the cause code survives as
    ``inconclusive_reason`` (which that schema REQUIRES on an inconclusive) and
    is refined onto the schema's two orthogonal axes. Use this at the boundary
    of any suite that already emits a verification report, rather than carrying
    two vocabularies through one pipeline.
    """
    out = {"outcome": VERIFICATION_OUTCOME_BY_VERDICT[verdict.verdict]}
    if verdict.verdict == VERDICT_OUT_OF_COVERAGE:
        logical, execution = VERIFICATION_STATUS_BY_CAUSE[verdict.cause]
        out["inconclusive_reason"] = verdict.detail or CAUSE_MEANINGS[verdict.cause]
        out["cause"] = verdict.cause
        out["logical_status"] = logical
        out["execution_status"] = execution
    else:
        out["logical_status"] = verdict.verdict
        out["execution_status"] = "ok"
    return out


def from_verification_status(item_id: str, *, logical_status: str,
                             execution_status: str = "ok",
                             inconclusive_reason: Optional[str] = None,
                             suite_level: bool = False) -> GateVerdict:
    """Read a ``verification_report.schema.json`` check back as a gate verdict.

    Honours that schema's own rule — *"an error/timeout/unavailable is NOT proof
    of failure"* — so an operational failure becomes ``out-of-coverage`` with the
    matching cause, never ``fail``.
    """
    by_execution = {"error": CAUSE_CHECKER_ERROR, "timeout": CAUSE_TIMEOUT,
                    "unavailable": CAUSE_UNSUPPORTED}
    if execution_status in by_execution:
        return GateVerdict(item_id, VERDICT_OUT_OF_COVERAGE,
                           cause=by_execution[execution_status],
                           detail=inconclusive_reason, suite_level=suite_level)
    if logical_status in (VERDICT_PASS, VERDICT_FAIL):
        return GateVerdict(item_id, logical_status, suite_level=suite_level)
    # `unknown` and `conflict` are both undecided: a conflict between two sound
    # verifiers is emphatically not a `fail`.
    return GateVerdict(item_id, VERDICT_OUT_OF_COVERAGE, cause=CAUSE_ABSTAINED,
                       detail=inconclusive_reason, suite_level=suite_level)


def out_of_coverage(item_id: str, cause: str, detail: Optional[str] = None,
                    **kw: Any) -> GateVerdict:
    """Construct an ``out-of-coverage`` verdict. ``cause`` is positional on
    purpose: there is no call shape that omits it."""
    return GateVerdict(item_id=item_id, verdict=VERDICT_OUT_OF_COVERAGE,
                       cause=cause, detail=detail, **kw)


# --------------------------------------------------------------------------- #
# The per-suite coverage contract — CJ-9
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SuiteCoverageContract:
    """What a suite must DECLARE before it is allowed to emit a headline.

    ``min_resolved_coverage`` is **per-suite and declared**, never global and
    never inferred. A suite that skips it is refused by
    :class:`UndeclaredCoverageThresholdError` rather than defaulted, because the
    right threshold is a property of the instrument: an execution-verified
    checker over a materialised corpus can honestly demand 0.98, while a
    multi-turn agentic harness with a known-lossy join cannot, and one number
    imposed on both is either vacuous for the first or unmeetable for the second.

    ``asserted_surface`` is mandatory prose in the same way
    ``PanelSource.absence_means`` is: the coverage fraction is unreadable unless
    the denominator says what surface it is a fraction OF.
    """

    suite: str
    #: What the suite asserts over — the DENOMINATOR, in words. Mandatory.
    asserted_surface: str
    #: The declared floor, in [0, 1]. Below it, the headline is suppressed.
    min_resolved_coverage: Optional[float] = None
    #: Why this suite's floor is what it is. Mandatory: a threshold with no
    #: rationale is a number nobody can argue with or revise.
    threshold_rationale: str = ""
    #: The name of the metric this suite would headline.
    headline_metric: str = "pass_rate_resolved"
    #: Declared verdict vocabulary. Validated against CJ-8.
    verdict_vocabulary: tuple = VERDICTS

    def __post_init__(self) -> None:
        if not self.suite:
            raise GateVerdictError("a coverage contract must name its suite.")
        if not self.asserted_surface.strip():
            raise GateVerdictError(
                f"suite {self.suite!r}: 'asserted_surface' is mandatory. A "
                f"coverage fraction is unreadable without a stated denominator — "
                f"same rule as PanelSource.absence_means on the dashboard plane."
            )
        if self.min_resolved_coverage is None:
            raise UndeclaredCoverageThresholdError(
                f"suite {self.suite!r} declared no 'min_resolved_coverage'. It is "
                f"REFUSED, not defaulted: the threshold is per-suite and declared, "
                f"never global and inferred, and a defaulted threshold is one "
                f"nobody chose."
            )
        if not isinstance(self.min_resolved_coverage, (int, float)) or \
                isinstance(self.min_resolved_coverage, bool):
            raise UndeclaredCoverageThresholdError(
                f"suite {self.suite!r}: 'min_resolved_coverage' must be a number in "
                f"[0, 1], got {self.min_resolved_coverage!r}."
            )
        if not 0.0 <= float(self.min_resolved_coverage) <= 1.0:
            raise UndeclaredCoverageThresholdError(
                f"suite {self.suite!r}: 'min_resolved_coverage' must be a FRACTION "
                f"in [0, 1], got {self.min_resolved_coverage!r} (a percentage is "
                f"the classic form of this error)."
            )
        if not self.threshold_rationale.strip():
            raise UndeclaredCoverageThresholdError(
                f"suite {self.suite!r}: 'threshold_rationale' is mandatory. A "
                f"declared threshold with no stated reason cannot be revised by "
                f"anyone but its author, which is how a number hardens."
            )
        object.__setattr__(self, "verdict_vocabulary",
                           refuse_two_valued(self.verdict_vocabulary,
                                             suite=self.suite))


# The registry is intentionally EMPTY at import. Declaring a coverage contract
# for a candidate suite is a measurement-parameter decision that belongs to that
# suite's owner; pre-declaring thresholds for the CJ-1..CJ-7 candidates here
# would presume CJ-GATE, which is an OPERATOR decision (which suites to adopt is
# not the executor's call). Suites register their own contract, or pass one
# directly to resolve_suite().
_CONTRACTS: dict = {}


def register_suite(contract: SuiteCoverageContract) -> SuiteCoverageContract:
    """Register a suite's declared coverage contract. One suite, one contract."""
    if contract.suite in _CONTRACTS:
        raise DuplicateSuiteContractError(
            f"suite {contract.suite!r} already has a registered coverage contract "
            f"(min_resolved_coverage={_CONTRACTS[contract.suite].min_resolved_coverage}). "
            f"A second registration silently re-declares a threshold."
        )
    _CONTRACTS[contract.suite] = contract
    return contract


def get_contract(suite: str) -> SuiteCoverageContract:
    """Return a suite's contract, or refuse. A missing contract is never a
    default — it is a suite that has not declared, and it may not headline."""
    try:
        return _CONTRACTS[suite]
    except KeyError:
        raise UndeclaredCoverageThresholdError(
            f"suite {suite!r} has no registered coverage contract, so it has no "
            f"declared 'min_resolved_coverage'. It is refused, not defaulted."
        ) from None


def registered_suites() -> tuple:
    return tuple(sorted(_CONTRACTS))


# --------------------------------------------------------------------------- #
# The fold — CJ-9
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SuiteReport:
    """The wire form of a suite's result. Every field a consumer needs to tell a
    low score from a thin one — and no headline value when coverage is short."""

    suite: str
    asserted_n: int
    pass_n: int
    fail_n: int
    out_of_coverage_n: int
    resolved_coverage: Optional[float]
    min_resolved_coverage: float
    coverage_sufficient: bool
    pass_rate_resolved: Optional[float]
    headline_metric: str
    headline: Optional[float]
    headline_suppressed: bool
    suppression_reason: Optional[str]
    out_of_coverage_by_cause: Mapping[str, int]
    asserted_surface: str
    gate_verdict: GateVerdict
    notes: tuple = field(default_factory=tuple)

    @property
    def decided_n(self) -> int:
        return self.pass_n + self.fail_n

    def to_dict(self) -> dict:
        d = {
            "suite": self.suite,
            "asserted_surface": self.asserted_surface,
            "asserted_n": self.asserted_n,
            "decided_n": self.decided_n,
            "pass_n": self.pass_n,
            "fail_n": self.fail_n,
            "out_of_coverage_n": self.out_of_coverage_n,
            "out_of_coverage_by_cause": dict(self.out_of_coverage_by_cause),
            "resolved_coverage": self.resolved_coverage,
            "min_resolved_coverage": self.min_resolved_coverage,
            "coverage_sufficient": self.coverage_sufficient,
            "headline_metric": self.headline_metric,
            "headline_suppressed": self.headline_suppressed,
            "suppression_reason": self.suppression_reason,
            "gate_verdict": self.gate_verdict.to_dict(),
            "notes": list(self.notes),
        }
        # The headline KEY — and the metric it is computed FROM — are present
        # only when a headline exists. A suppressed headline is ABSENT from the
        # wire, not null-and-flagged: a null still gets read as a value by a
        # consumer doing `.get(k, 0)`, and a flagged number still gets quoted.
        # Emitting `pass_rate_resolved` beside `headline_suppressed: true` would
        # be suppression in name only — the number is right there.
        #
        # The COUNTS stay. Recomputing the rate from pass_n/decided_n is a
        # deliberate act by someone who has seen the coverage; reading a field is
        # not.
        if not self.headline_suppressed:
            d["headline"] = self.headline
            d["pass_rate_resolved"] = self.pass_rate_resolved
        return d


def resolve_suite(contract: SuiteCoverageContract,
                  verdicts: Iterable[GateVerdict],
                  *,
                  asserted_n: Optional[int] = None,
                  headline_bar: Optional[float] = None) -> SuiteReport:
    """Fold item verdicts into a suite report carrying resolved coverage.

    ``resolved_coverage = decided / asserted``, where ``decided`` is
    ``pass + fail`` and ``asserted`` is the whole surface the suite claims to
    cover. Pass ``asserted_n`` explicitly when the surface is larger than the
    verdict list — an item the harness never even attempted still belongs in the
    denominator, and inferring the denominator from the verdicts that arrived is
    how a suite reports 100% coverage of the subset it happened to reach.

    Suppression, in order:

    1. **Empty asserted surface** — coverage is undefined (0/0), so the headline
       is suppressed. A suite that asserted nothing has not passed; it has not
       run. This is the ``fold({}) is not ok`` rule at suite granularity.
    2. **Coverage below the declared floor** — the headline VALUE is removed and
       the suite's own gate verdict becomes ``out-of-coverage`` with cause
       ``insufficient_coverage``.

    Otherwise the suite's gate verdict is ``pass``/``fail`` against
    ``headline_bar`` when one is supplied, and ``pass`` (coverage satisfied,
    nothing further asserted) when it is not.
    """
    items = list(verdicts)
    for v in items:
        if not isinstance(v, GateVerdict):
            raise NonCompliantVerdictError(
                f"suite {contract.suite!r}: {v!r} is not a GateVerdict. Raw "
                f"bools/floats cannot carry a cause code and are the two-valued "
                f"shape CJ-8 outlaws."
            )

    pass_n = sum(1 for v in items if v.verdict == VERDICT_PASS)
    fail_n = sum(1 for v in items if v.verdict == VERDICT_FAIL)
    ooc = [v for v in items if v.verdict == VERDICT_OUT_OF_COVERAGE]

    by_cause: dict = {}
    for v in ooc:
        by_cause[v.cause] = by_cause.get(v.cause, 0) + 1
    by_cause = dict(sorted(by_cause.items(), key=lambda kv: (-kv[1], kv[0])))

    decided_n = pass_n + fail_n
    surface = len(items) if asserted_n is None else int(asserted_n)
    notes: list = []
    if asserted_n is not None and asserted_n < len(items):
        raise GateVerdictError(
            f"suite {contract.suite!r}: asserted_n={asserted_n} is smaller than "
            f"the {len(items)} verdicts supplied. The asserted surface can never "
            f"be smaller than the set that was decided on it."
        )
    unreported = surface - len(items)
    ooc_n = len(ooc) + unreported
    if unreported:
        # Items in the asserted surface that produced no verdict object at all
        # are out-of-coverage with cause `absent` — never subtracted from the
        # denominator, which is the exact way a suite manufactures coverage.
        by_cause[CAUSE_ABSENT] = by_cause.get(CAUSE_ABSENT, 0) + unreported
        by_cause = dict(sorted(by_cause.items(), key=lambda kv: (-kv[1], kv[0])))
        notes.append(
            f"{unreported} asserted item(s) produced no verdict at all; counted "
            f"{VERDICT_OUT_OF_COVERAGE!r}/{CAUSE_ABSENT!r} rather than dropped "
            f"from the denominator."
        )

    threshold = float(contract.min_resolved_coverage)

    if surface == 0:
        coverage = None
        sufficient = False
        pass_rate = None
        reason = (
            f"suite {contract.suite!r} asserted NOTHING (asserted_n=0), so "
            f"resolved coverage is undefined (0/0) and no headline exists. A "
            f"suite that asserted nothing has not passed — it has not run. "
            f"Asserted surface: {contract.asserted_surface}"
        )
    else:
        coverage = decided_n / surface
        sufficient = coverage >= threshold
        pass_rate = (pass_n / decided_n) if decided_n else None
        reason = None
        if not sufficient:
            top = ", ".join(f"{c}={n}" for c, n in list(by_cause.items())[:4]) or "none"
            reason = (
                f"resolved coverage {coverage:.4f} ({decided_n}/{surface}) is below "
                f"suite {contract.suite!r}'s DECLARED floor {threshold:.4f}, so the "
                f"'{contract.headline_metric}' headline is SUPPRESSED. "
                f"{ooc_n} of {surface} asserted items were never decided "
                f"(by cause: {top}). A reliability figure quoted without its "
                f"coverage regime is unreadable. "
                f"Asserted surface: {contract.asserted_surface}"
            )

    headline_value = pass_rate

    if not sufficient:
        # The suite's OWN verdict is undecided — not `fail`. A thin suite has not
        # ruled against its subject; it has failed to rule. That distinction is
        # the whole of CJ-8 applied one level up.
        gate = GateVerdict(
            item_id=f"suite:{contract.suite}",
            verdict=VERDICT_OUT_OF_COVERAGE,
            cause=CAUSE_INSUFFICIENT_COVERAGE,
            detail=reason,
            suite_level=True,
        )
        # Both the headline AND the metric it is computed from are dropped. See
        # SuiteReport.to_dict: emitting the rate beside `headline_suppressed`
        # would be suppression in name only.
        headline_value = None
        pass_rate = None
    elif headline_bar is None:
        gate = GateVerdict(item_id=f"suite:{contract.suite}",
                           verdict=VERDICT_PASS, suite_level=True)
    else:
        gate = GateVerdict(
            item_id=f"suite:{contract.suite}",
            verdict=VERDICT_PASS if (pass_rate is not None and pass_rate >= headline_bar)
            else VERDICT_FAIL,
            suite_level=True,
        )

    return SuiteReport(
        suite=contract.suite,
        asserted_n=surface,
        pass_n=pass_n,
        fail_n=fail_n,
        out_of_coverage_n=ooc_n,
        resolved_coverage=coverage,
        min_resolved_coverage=threshold,
        coverage_sufficient=sufficient,
        pass_rate_resolved=pass_rate,
        headline_metric=contract.headline_metric,
        headline=headline_value,
        headline_suppressed=not sufficient,
        suppression_reason=reason,
        out_of_coverage_by_cause=by_cause,
        asserted_surface=contract.asserted_surface,
        gate_verdict=gate,
        notes=tuple(notes),
    )
