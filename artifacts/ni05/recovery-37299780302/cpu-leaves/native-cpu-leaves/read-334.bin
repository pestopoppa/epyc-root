"""Behavioral pin on eval_tower.py's EvalTower._aggregate ECE binning semantics.

PURPOSE (audit TEST-3 / EV-11b): this test pins the Expected-Calibration-Error
binning definition that ``EvalTower._aggregate`` uses, and holds it FROZEN until
the next *intentional*, era-labeled migration (EV-11c rebaseline). It exists so
that ANY change to the inline ECE semantics — accidental "helpful" consolidation,
refactor drift, or a parallel agent's edit — fails CI loudly instead of silently
shifting a decision-gating calibration number by 0.15-0.40 on binary-confidence
cohorts.

Operator decision (2026-07-20, audit TEST-3/EV-11b) fixed the migration path: the
``_aggregate`` ECE definition changes ONLY at an era-labeled rebaseline. Whoever
intentionally lands EV-11c (or any successor era) MUST update this test IN THE
SAME COMMIT and bump the era note below.

CURRENT STATE PINNED (verified against the tree, do not assume from history):
    ``_aggregate`` no longer contains the old *divergent half-open* inline binning
    loop (``mask = [lo <= c < hi ...]``, top bin ``c < hi`` so confidence == 1.0
    fell out of every bin and yielded ECE 0.0 on all-confident cohorts). That
    inline loop and its "Do NOT 'helpfully' swap it" tripwire were removed in
    commit 8f24679a ("Harden eval tower scoring denominators", 2026-07-20), which
    migrated ``_aggregate`` to the canonical CLOSED-top-bin definition
    ``src.llm_primitives.stat_tests.expected_calibration_error`` (final bin closed
    on the right, ``<=``, so confidence == 1.0 lands in it). The result is
    era-labeled in EvalResult.details as:
        ece_binning        == "closed_top_bin_stat_tests"
        ece_instrument_era == "ev11b_closed_bin_2026_07_20"

    This pin therefore locks the CLOSED-top-bin behavior now live in production and
    guards against a *regression back* to the old half-open loop (or any other
    silent redefinition), which the discriminating cohort below would surface as a
    0.3 -> 0.0 swing.

IF THIS TEST FAILS, it means either:
    (a) ACCIDENTAL ECE semantics drift — e.g. someone reintroduced the half-open
        top bin, re-inlined a hand-rolled binning loop, or otherwise changed the
        definition ``_aggregate`` delegates to. This is a scoring-semantics
        regression across a CRITICAL-blast-radius path: REVERT it. -- or --
    (b) the EV-11c (or later) era migration LANDING deliberately. In that case the
        person landing it updates the pinned values + the era constants below in
        the SAME commit, with an era note, so pre/post numbers are never mixed.

The pin executes the real production code path: synthetic QuestionResult cohorts
are fed through ``EvalTower._aggregate`` and we assert on the ECE it emits — NOT a
re-implementation of the formula. ``expected_calibration_error`` is also called
directly, but only to document the closed-bin reference value the tower delegates
to.

RESILIENCE: eval_tower.py is edited concurrently by other sessions. A transiently
broken tree (import-time failure) SKIPS loudly rather than hard-failing this pin;
but a SUCCESSFUL import whose ECE behavior has changed FAILS — that is the pin
firing, exactly as intended.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# eval_tower uses bare intra-package imports (``from safety_gate import ...``), so
# scripts/autopilot must be on sys.path -- same setup as the other eval_tower
# unit tests (see tests/unit/test_eval_tower_ev11_stats.py).
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))
sys.path.insert(0, str(REPO_ROOT))

# Guarded import: a concurrently-edited / transiently-broken eval_tower.py must
# SKIP (loudly, naming the error) instead of erroring this pin out of existence.
# A *successful* import with changed ECE behavior still runs the assertions below
# and fails -- that is the pin doing its job.
_IMPORT_ERROR: str | None = None
try:
    from eval_tower import EvalTower, QuestionResult  # type: ignore[import-not-found]
    from src.llm_primitives.stat_tests import expected_calibration_error
except Exception as exc:  # noqa: BLE001 -- deliberately broad: any import breakage -> skip
    _IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

# ── Pinned era identity (bump these ONLY when landing an intentional migration) ──
EXPECTED_ECE_BINNING = "closed_top_bin_stat_tests"
EXPECTED_ECE_INSTRUMENT_ERA = "ev11b_closed_bin_2026_07_20"

# Closed-top-bin ECE for the discriminating cohort: 10 rows, all confidence 1.0,
# 7 correct + 3 wrong -> single top bin, |acc 0.7 - conf 1.0| = 0.3. The OLD
# half-open loop dropped every confidence==1.0 row and returned 0.0 instead.
DISCRIMINATING_CLOSED_BIN_ECE = 0.3
OLD_HALF_OPEN_ECE_FOR_DISCRIMINATING_COHORT = 0.0
# Mixed cohort where half-open and closed-bin AGREE (no confidence == 1.0):
# 5 rows @0.95 (4 correct/1 wrong) + 5 rows @0.65 (2 correct/3 wrong)
#   top bin  [0.9,1.0): |acc 0.8 - conf 0.95| = 0.15, weight 0.5 -> 0.075
#   bin      [0.6,0.7): |acc 0.4 - conf 0.65| = 0.25, weight 0.5 -> 0.125
#   ECE = 0.20
MIXED_COHORT_ECE = 0.20

_skip_if_broken = pytest.mark.skipif(
    _IMPORT_ERROR is not None,
    reason=(
        "PIN SKIPPED (not passed): eval_tower / stat_tests import failed -- tree is "
        f"transiently broken (concurrent edit?): {_IMPORT_ERROR}. Re-run once the "
        "tree is coherent; a successful import with changed ECE will FAIL, not skip."
    ),
)


def _make_result(confidence: float, correct: bool, idx: int) -> "QuestionResult":
    """Minimal scored (non-error) QuestionResult carrying only ECE-relevant fields.

    ``_aggregate`` collects (confidence, correctness) from every ``not r.error``
    row; the remaining fields are inert defaults. route_used="" keeps the AP-16
    instruction accounting a no-op and irrelevant to ECE.
    """
    return QuestionResult(
        question_id=f"q{idx}",
        suite="pin_suite",
        prompt="p",
        expected="e",
        correct=correct,
        confidence=confidence,
    )


def _aggregate_ece(results: list["QuestionResult"]):
    """Invoke the REAL production path: EvalTower._aggregate.

    ``_aggregate`` reads no instance state except ``self._count_instruction_tokens``
    (which itself touches only module-level imports + a staticmethod, and returns 0
    when src.* prompt builders are unavailable). Building the instance via
    ``__new__`` -- with NO attributes set -- is therefore sufficient to exercise the
    ECE code path in isolation, with no heavy EvalTower construction.
    """
    tower = EvalTower.__new__(EvalTower)
    return tower._aggregate(results, tier=1)


@_skip_if_broken
def test_aggregate_ece_pins_closed_top_bin_on_discriminating_binary_cohort() -> None:
    """PIN: all-confident binary cohort -> closed-top-bin ECE 0.3, NOT half-open 0.0.

    This cohort is the discriminator between the two ECE definitions: under the
    live closed-top-bin definition every confidence==1.0 row lands in the final
    bin and ECE == 0.3; under the removed half-open loop those rows fell out of
    every bin and ECE == 0.0. A revert to half-open (or any silent redefinition)
    flips 0.3 -> 0.0 here and fails the pin.
    """
    confidences = [1.0] * 10
    correctness = [True] * 7 + [False] * 3
    results = [_make_result(c, ok, i) for i, (c, ok) in enumerate(zip(confidences, correctness))]

    agg = _aggregate_ece(results)

    # (a) THE PIN: production ECE == closed-top-bin value on this cohort.
    assert agg.ece == pytest.approx(DISCRIMINATING_CLOSED_BIN_ECE, abs=1e-9), (
        "eval_tower _aggregate ECE drifted off the pinned closed-top-bin value "
        f"({DISCRIMINATING_CLOSED_BIN_ECE}); got {agg.ece}. See module docstring: "
        "revert accidental drift, or update the pin if landing EV-11c."
    )
    # (b) Explicit guard against reverting to the OLD half-open loop, which
    #     returned 0.0 on this all-confident cohort.
    assert agg.ece != pytest.approx(OLD_HALF_OPEN_ECE_FOR_DISCRIMINATING_COHORT, abs=1e-9), (
        "eval_tower _aggregate ECE collapsed to 0.0 on an all-confidence-1.0 "
        "cohort -- the divergent HALF-OPEN top bin was reintroduced. Revert it."
    )
    # (c) Pin the delegation: _aggregate uses the stat_tests closed-bin definition.
    closed_bin_ref = expected_calibration_error(
        [float(c) for c in confidences],
        [float(ok) for ok in correctness],
        n_bins=10,
    )
    assert closed_bin_ref == pytest.approx(DISCRIMINATING_CLOSED_BIN_ECE, abs=1e-9), (
        "stat_tests closed-bin reference itself moved off 0.3 on this cohort; "
        f"got {closed_bin_ref}. The measurement-trust boundary changed -- investigate."
    )
    assert agg.ece == pytest.approx(closed_bin_ref, abs=1e-12), (
        "eval_tower _aggregate ECE no longer equals stat_tests closed-bin ECE on "
        "identical vectors -- the tower stopped delegating to the canonical "
        "definition. Revert, or era-relabel if intentional."
    )
    # (d) Pin the era stamp so a definition change can't ship without relabeling.
    assert agg.details.get("ece_binning") == EXPECTED_ECE_BINNING, (
        f"ece_binning label changed to {agg.details.get('ece_binning')!r}; "
        f"expected {EXPECTED_ECE_BINNING!r}. Update the pin only for a deliberate era migration."
    )
    assert agg.details.get("ece_instrument_era") == EXPECTED_ECE_INSTRUMENT_ERA, (
        f"ece_instrument_era changed to {agg.details.get('ece_instrument_era')!r}; "
        f"expected {EXPECTED_ECE_INSTRUMENT_ERA!r}. Bump this pin in the same commit as the era migration."
    )


@_skip_if_broken
def test_aggregate_ece_matches_closed_bin_on_mixed_agreeing_cohort() -> None:
    """PIN: mixed cohort where half-open and closed-bin agree -> shared ECE 0.20.

    No confidence equals 1.0 here, so the two ECE definitions coincide; the pin
    locks the shared non-degenerate value and re-asserts _aggregate == stat_tests.
    """
    confidences = [0.95] * 5 + [0.65] * 5
    correctness = [True] * 4 + [False] * 1 + [True] * 2 + [False] * 3
    results = [_make_result(c, ok, i) for i, (c, ok) in enumerate(zip(confidences, correctness))]

    agg = _aggregate_ece(results)

    assert agg.ece == pytest.approx(MIXED_COHORT_ECE, abs=1e-9), (
        f"eval_tower _aggregate ECE drifted off the pinned mixed-cohort value "
        f"({MIXED_COHORT_ECE}); got {agg.ece}."
    )
    closed_bin_ref = expected_calibration_error(
        [float(c) for c in confidences],
        [float(ok) for ok in correctness],
        n_bins=10,
    )
    assert agg.ece == pytest.approx(closed_bin_ref, abs=1e-12), (
        "eval_tower _aggregate ECE diverged from stat_tests closed-bin ECE on a "
        "mixed cohort -- the tower stopped delegating to the canonical definition."
    )
    assert agg.details.get("ece_instrument_era") == EXPECTED_ECE_INSTRUMENT_ERA
