"""CJ-8 / CJ-9 — three-valued gate verdicts and resolved coverage.

Locks the contract in ``scripts/benchmark/gate_verdict.py``. The scar it exists
to close, in one sentence: **a two-valued gate reports "the checker never
decided this" as "the check failed"**, so the common case becomes invisible and
every remedy points at the wrong subsystem.

The motivating corpus is external (`intake-1307#record`) and is used here as
MOTIVATION ONLY — never as a measurement of this deployment. In it, of 1,403
observations 741 were never formalized and zero timed out (the bottleneck sat
entirely *before* the check ran), and winner accuracy swung 0.96 -> 0.20 between
high and low resolved coverage with the judge and protocol held fixed.

HOUSE STYLE. Every positive here is PAIRED with a mutation that removes exactly
the signal under test and shows the positive would then pass — because a guard
that would hold with its signal deleted is testing something else. Mutations are
written as the PRE-FIX behaviour reproduced inline (a two-valued scorer, a
defaulted threshold, an inferred denominator) so reverting the fix reproduces
the bite exactly. Each mutation test's docstring states which signal it removes
and what would go undetected without it.

NO I/O, NO PROCESS, NO CLOCK. The module under test is pure.
Run: ``pytest tests/benchmark/test_gate_verdict.py`` from ``/mnt/raid0/llm/epyc-root``.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "gate_verdict.py"
SPEC = importlib.util.spec_from_file_location("gate_verdict", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
gv = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gv
SPEC.loader.exec_module(gv)


def contract(**kw):
    """A compliant, fully-declared suite contract. Overridable per test."""
    kw.setdefault("suite", "demo_suite")
    kw.setdefault("asserted_surface", "198 GPQA-Diamond items, one verdict each")
    kw.setdefault("min_resolved_coverage", 0.90)
    kw.setdefault("threshold_rationale",
                  "deterministic letter-match against a materialised gold set; "
                  "an unextractable answer is an extractor defect, so the floor "
                  "is high")
    return gv.SuiteCoverageContract(**kw)


def decided(n_pass, n_fail, prefix="d"):
    return ([gv.GateVerdict(f"{prefix}p{i}", gv.VERDICT_PASS) for i in range(n_pass)]
            + [gv.GateVerdict(f"{prefix}f{i}", gv.VERDICT_FAIL) for i in range(n_fail)])


def undecided(n, cause=gv.CAUSE_UNPARSED, prefix="u"):
    return [gv.out_of_coverage(f"{prefix}{i}", cause) for i in range(n)]


# --------------------------------------------------------------------------- #
# CJ-8 — three-valued verdicts
# --------------------------------------------------------------------------- #
class TwoValuedVerdictIsRefused(unittest.TestCase):
    """CJ-8's headline rule: a two-valued verdict is NON-COMPLIANT.

    Pre-fix behaviour (the bite): a scorer emitting ``True``/``False`` or
    ``1.0``/``0.0`` has no value meaning "never decided", so an item whose answer
    could not be extracted is emitted as the same ``False`` as an item that was
    read and found wrong.
    """

    def test_bool_verdict_is_refused(self):
        """A bare bool is the two-valued idiom. It must not construct."""
        for value in (True, False):
            with self.subTest(value=value):
                with self.assertRaises(gv.NonCompliantVerdictError) as cm:
                    gv.GateVerdict("item-1", value)
                self.assertIn("TWO-VALUED", str(cm.exception))

    def test_zero_one_score_verdict_is_refused(self):
        """``1``/``0`` is the same defect spelled as a score, and ``bool`` is an
        ``int`` subclass — a guard written only against ``bool`` would let the
        numeric spelling through."""
        for value in (1, 0):
            with self.subTest(value=value):
                with self.assertRaises(gv.NonCompliantVerdictError):
                    gv.GateVerdict("item-1", value)

    def test_verdict_outside_the_vocabulary_is_refused(self):
        """Not only bools: any string outside the three values, including
        near-misses that a case-insensitive or fuzzy check would accept."""
        for value in ("PASS", "Pass", "failed", "skip", "out_of_coverage", ""):
            with self.subTest(value=value):
                with self.assertRaises(gv.NonCompliantVerdictError):
                    gv.GateVerdict("item-1", value)

    def test_two_valued_suite_vocabulary_is_refused(self):
        """A suite may not DECLARE a two-valued vocabulary either. Refusing only
        at item construction would let a suite advertise ``(pass, fail)`` and
        then honestly report every undecided item as ``fail``."""
        with self.assertRaises(gv.NonCompliantVerdictError) as cm:
            contract(verdict_vocabulary=(gv.VERDICT_PASS, gv.VERDICT_FAIL))
        self.assertIn(gv.VERDICT_OUT_OF_COVERAGE, str(cm.exception))

    # -- mutation ---------------------------------------------------------- #
    def test_mutation_two_valued_scorer_silently_reports_no_signal_as_fail(self):
        """MUTATION: removes exactly the third verdict value.

        Reproduces the PRE-FIX scorer — a function returning ``bool`` — over the
        same two inputs the positives use, and shows the two events become ONE
        value. Without the refusals above, nothing in the pipeline distinguishes
        them, and the whole of CJ-8 goes undetected: this is the bite the
        positives are load-bearing against.
        """
        def two_valued_score(extracted, gold):
            return extracted == gold          # extracted=None on a parse failure

        wrong_answer = two_valued_score("B", "A")       # decided, and wrong
        never_extracted = two_valued_score(None, "A")   # never decided at all
        self.assertEqual(wrong_answer, never_extracted)
        self.assertIs(never_extracted, False)

        # The fixed vocabulary keeps them apart, and the difference survives to
        # the wire with a remedy attached.
        wrong = gv.GateVerdict("q1", gv.VERDICT_FAIL)
        missing = gv.out_of_coverage("q2", gv.CAUSE_UNPARSED)
        self.assertNotEqual(wrong.verdict, missing.verdict)
        self.assertTrue(wrong.decided)
        self.assertFalse(missing.decided)
        self.assertIn("extractor", missing.to_dict()["cause_means"])


class CauseCodeIsMandatoryOnOutOfCoverage(unittest.TestCase):
    """``out-of-coverage`` without a cause code is refused.

    An undecided count with no cause names no remedy — which is the failure the
    third verdict exists to prevent, committed one level down.
    """

    def test_out_of_coverage_without_a_cause_is_refused(self):
        with self.assertRaises(gv.MissingCauseCodeError) as cm:
            gv.GateVerdict("item-1", gv.VERDICT_OUT_OF_COVERAGE)
        self.assertIn("MANDATORY", str(cm.exception))

    def test_out_of_coverage_with_an_unregistered_cause_is_refused(self):
        """The registry is CLOSED. A free-text cause is not foldable and lets the
        taxonomy drift back into one 'other' bucket."""
        for bad in ("dunno", "other", "no_signal", "", "ABSENT"):
            with self.subTest(cause=bad):
                with self.assertRaises(gv.MissingCauseCodeError):
                    gv.GateVerdict("item-1", gv.VERDICT_OUT_OF_COVERAGE, cause=bad)

    def test_suite_level_cause_is_refused_on_a_single_item(self):
        """``insufficient_coverage`` describes a SUITE. An item is not undecided
        because the suite it sits in was thin, and allowing the cause here would
        let a harness label individual items with a fact about their aggregate."""
        with self.assertRaises(gv.MissingCauseCodeError) as cm:
            gv.GateVerdict("item-1", gv.VERDICT_OUT_OF_COVERAGE,
                           cause=gv.CAUSE_INSUFFICIENT_COVERAGE)
        self.assertIn("SUITE-LEVEL only", str(cm.exception))

    def test_decided_verdict_may_not_carry_a_cause(self):
        """The asymmetry runs both ways. A cause on ``pass``/``fail`` means the
        caller does not know which verdict it emitted."""
        for verdict in (gv.VERDICT_PASS, gv.VERDICT_FAIL):
            with self.subTest(verdict=verdict):
                with self.assertRaises(gv.SpuriousCauseCodeError):
                    gv.GateVerdict("item-1", verdict, cause=gv.CAUSE_TIMEOUT)

    def test_every_cause_has_a_stated_remedy(self):
        """A cause code whose meaning is unwritten is a label, not a diagnosis.
        Totality over ``ALL_CAUSES`` so adding a cause without its remedy fails
        here rather than shipping as an unexplained bucket."""
        self.assertEqual(set(gv.CAUSE_MEANINGS), set(gv.ALL_CAUSES))
        for cause, meaning in gv.CAUSE_MEANINGS.items():
            self.assertTrue(meaning.strip(), cause)

    def test_absent_and_empty_are_distinct_causes(self):
        """Reuses the dashboard plane's split (``panels.py``: ``reporting`` and
        ``content`` are independent so "the producer reported nothing" cannot
        render as "no producer reported"). Collapsing them here would rebuild
        that scar in the measurement plane."""
        self.assertNotEqual(gv.CAUSE_ABSENT, gv.CAUSE_EMPTY)
        self.assertIn(gv.CAUSE_ABSENT, gv.CAUSES)
        self.assertIn(gv.CAUSE_EMPTY, gv.CAUSES)

    # -- mutation ---------------------------------------------------------- #
    def test_mutation_causeless_undecided_mass_names_no_remedy(self):
        """MUTATION: removes exactly the cause code, holding the three-valued
        verdict in place.

        A gate can be three-valued and still useless: 60 undecided items with no
        causes is one number nobody can act on. With causes, the same 60 split
        into "fix the extractor" and "fix the corpus join" — two different teams.
        Without the mandatory-cause guard, the fold below would carry a single
        anonymous bucket and the distinction would be undetectable.
        """
        mixed = (undecided(40, gv.CAUSE_UNPARSED)
                 + undecided(20, gv.CAUSE_NO_REFERENCE, prefix="n"))
        report = gv.resolve_suite(contract(min_resolved_coverage=0.0),
                                  decided(40, 0) + mixed)
        self.assertEqual(report.out_of_coverage_by_cause,
                         {gv.CAUSE_UNPARSED: 40, gv.CAUSE_NO_REFERENCE: 20})

        # The mutant: one bucket. Same total, no remedy.
        collapsed = {"undecided": sum(report.out_of_coverage_by_cause.values())}
        self.assertEqual(sum(collapsed.values()), report.out_of_coverage_n)
        self.assertEqual(len(collapsed), 1)


# --------------------------------------------------------------------------- #
# CJ-9 — resolved coverage and headline suppression
# --------------------------------------------------------------------------- #
class UndeclaredThresholdIsRefused(unittest.TestCase):
    """A suite that never declares ``min_resolved_coverage`` is REFUSED, not
    defaulted. The threshold is per-suite and declared; a global default is the
    "one number for everything" CJ-9 forbids, and a defaulted threshold is one
    nobody chose.
    """

    def test_suite_with_no_threshold_is_refused(self):
        with self.assertRaises(gv.UndeclaredCoverageThresholdError) as cm:
            contract(min_resolved_coverage=None)
        self.assertIn("REFUSED, not defaulted", str(cm.exception))

    def test_unregistered_suite_has_no_default_threshold(self):
        """Looking a suite up must refuse rather than hand back a fallback —
        the lookup path is where a default would sneak back in."""
        with self.assertRaises(gv.UndeclaredCoverageThresholdError):
            gv.get_contract("a_suite_that_never_declared")

    def test_threshold_must_be_a_fraction(self):
        """A percentage is the classic spelling of this error; ``90`` would
        suppress every headline forever, which reads as a broken suite rather
        than a mis-declared one."""
        for bad in (90, 1.5, -0.1, True, "0.9", float("nan")):
            with self.subTest(value=bad):
                with self.assertRaises(gv.UndeclaredCoverageThresholdError):
                    contract(min_resolved_coverage=bad)

    def test_threshold_without_a_rationale_is_refused(self):
        """A declared number with no stated reason cannot be revised by anyone
        but its author — which is how a threshold hardens into a constant."""
        with self.assertRaises(gv.UndeclaredCoverageThresholdError):
            contract(threshold_rationale="   ")

    def test_asserted_surface_is_mandatory(self):
        """A coverage FRACTION is unreadable without a stated denominator. Same
        rule as ``PanelSource.absence_means`` on the dashboard plane."""
        with self.assertRaises(gv.GateVerdictError):
            contract(asserted_surface="")

    def test_one_suite_one_contract(self):
        """A second registration silently re-declares a threshold."""
        c = contract(suite="uniquely_named_for_this_test")
        gv.register_suite(c)
        try:
            with self.assertRaises(gv.DuplicateSuiteContractError):
                gv.register_suite(contract(suite=c.suite, min_resolved_coverage=0.1))
            self.assertIs(gv.get_contract(c.suite), c)
        finally:
            gv._CONTRACTS.pop(c.suite, None)

    # -- mutation ---------------------------------------------------------- #
    def test_mutation_declaring_the_threshold_is_the_only_thing_that_unblocks(self):
        """MUTATION: restores exactly the omitted field and nothing else.

        Proves the refusal keys on the MISSING THRESHOLD rather than on some
        other unset field of the same construction — a refusal that fires for an
        unrelated reason would still pass the positive above while leaving a
        threshold-less suite constructible by a caller who happened to fill the
        other fields.
        """
        kw = dict(suite="mutation_probe",
                  asserted_surface="the same surface, unchanged",
                  threshold_rationale="the same rationale, unchanged")
        with self.assertRaises(gv.UndeclaredCoverageThresholdError):
            gv.SuiteCoverageContract(**kw)
        restored = gv.SuiteCoverageContract(min_resolved_coverage=0.5, **kw)
        self.assertEqual(restored.min_resolved_coverage, 0.5)


class HeadlineIsSuppressedBelowDeclaredCoverage(unittest.TestCase):
    """A headline is SUPPRESSED when resolved coverage falls below the suite's
    declared floor — and the number is REMOVED from the wire, not flagged.

    The evidence this rests on (external, motivation only): winner accuracy 0.96
    at high resolved coverage vs 0.20 at low, same judge, same protocol. A
    reliability figure quoted without its coverage regime is unreadable.
    """

    def test_headline_absent_from_the_wire_below_threshold(self):
        report = gv.resolve_suite(contract(), decided(5, 0) + undecided(5))
        self.assertEqual(report.resolved_coverage, 0.5)
        self.assertFalse(report.coverage_sufficient)
        self.assertTrue(report.headline_suppressed)
        self.assertIsNone(report.headline)
        wire = report.to_dict()
        self.assertNotIn("headline", wire)

    def test_the_metric_behind_the_headline_is_removed_too(self):
        """Suppression in name only is not suppression. Emitting
        ``pass_rate_resolved`` beside ``headline_suppressed: true`` leaves the
        number right there for any consumer that reads fields rather than
        flags."""
        report = gv.resolve_suite(contract(), decided(5, 0) + undecided(5))
        wire = report.to_dict()
        self.assertNotIn("pass_rate_resolved", wire)
        # The COUNTS stay: recomputing from them is a deliberate act by someone
        # who has seen the coverage; reading a field is not.
        self.assertEqual((wire["pass_n"], wire["fail_n"], wire["decided_n"]),
                         (5, 0, 5))

    def test_suite_verdict_is_out_of_coverage_not_fail(self):
        """CJ-8 applied one level up: a thin suite has not ruled against its
        subject, it has failed to rule. Reporting ``fail`` here would be the
        original defect rebuilt at the aggregate."""
        report = gv.resolve_suite(contract(), decided(5, 0) + undecided(5))
        self.assertEqual(report.gate_verdict.verdict, gv.VERDICT_OUT_OF_COVERAGE)
        self.assertEqual(report.gate_verdict.cause, gv.CAUSE_INSUFFICIENT_COVERAGE)
        self.assertNotEqual(report.gate_verdict.verdict, gv.VERDICT_FAIL)

    def test_suppression_reason_names_coverage_threshold_and_causes(self):
        """A suppressed headline that does not say WHY sends the reader to the
        model when the defect is in the harness."""
        report = gv.resolve_suite(contract(), decided(5, 0) + undecided(5))
        reason = report.suppression_reason
        self.assertIn("0.5000", reason)
        self.assertIn("0.9000", reason)
        self.assertIn(gv.CAUSE_UNPARSED, reason)
        self.assertIn("198 GPQA-Diamond items", reason)

    def test_empty_asserted_surface_suppresses_rather_than_passing_vacuously(self):
        """0/0 is undefined, not 100%. A suite that asserted nothing has not
        passed — it has not run. This is ``panels.fold({}) is not ok`` at suite
        granularity, and the repo's standing vacuous-verification scar."""
        report = gv.resolve_suite(contract(min_resolved_coverage=0.0), [])
        self.assertIsNone(report.resolved_coverage)
        self.assertTrue(report.headline_suppressed)
        self.assertNotIn("headline", report.to_dict())
        self.assertIn("asserted NOTHING", report.suppression_reason)

    def test_unreported_items_stay_in_the_denominator(self):
        """An item the harness never attempted still belongs in the asserted
        surface. Counting it out-of-coverage/``absent`` rather than dropping it
        is the difference between honest coverage and manufactured coverage."""
        report = gv.resolve_suite(contract(), decided(50, 0), asserted_n=100)
        self.assertEqual(report.asserted_n, 100)
        self.assertEqual(report.resolved_coverage, 0.5)
        self.assertEqual(report.out_of_coverage_by_cause, {gv.CAUSE_ABSENT: 50})
        self.assertTrue(report.headline_suppressed)
        self.assertTrue(any("denominator" in n for n in report.notes))

    def test_asserted_surface_smaller_than_the_verdicts_is_refused(self):
        """The surface can never be smaller than the set decided on it; that
        combination is a caller bug that would report coverage above 1.0."""
        with self.assertRaises(gv.GateVerdictError):
            gv.resolve_suite(contract(), decided(10, 0), asserted_n=5)

    def test_raw_scores_cannot_be_folded(self):
        """The fold refuses non-``GateVerdict`` items. A list of floats is the
        two-valued shape wearing a different coat, and it cannot carry a cause."""
        with self.assertRaises(gv.NonCompliantVerdictError):
            gv.resolve_suite(contract(), [1.0, 0.0, 1.0])

    def test_per_suite_threshold_is_not_global(self):
        """The same verdicts pass one suite's declared floor and are suppressed
        by another's. If one number governed everything, these two would agree —
        which is precisely what CJ-9 forbids."""
        verdicts = decided(8, 0) + undecided(2)
        lenient = gv.resolve_suite(contract(suite="agentic", min_resolved_coverage=0.75),
                                   verdicts)
        strict = gv.resolve_suite(contract(suite="deterministic",
                                           min_resolved_coverage=0.95), verdicts)
        self.assertFalse(lenient.headline_suppressed)
        self.assertTrue(strict.headline_suppressed)
        self.assertEqual(lenient.resolved_coverage, strict.resolved_coverage)

    # -- mutation ---------------------------------------------------------- #
    def test_mutation_same_pass_rate_full_coverage_is_not_suppressed(self):
        """MUTATION: removes EXACTLY the coverage shortfall, holding the pass
        rate fixed at 1.0.

        The suppressed case above scores 5/5 = 1.0 on what it decided. So does
        this one. The only difference is that nothing was left undecided. If
        suppression were keyed on the score, the threshold, the suite name or the
        presence of any out-of-coverage item at all, this control would also be
        suppressed and the positive would be proving the wrong thing.
        """
        thin = gv.resolve_suite(contract(), decided(5, 0) + undecided(5))
        full = gv.resolve_suite(contract(), decided(10, 0))
        self.assertEqual(thin.pass_n / thin.decided_n, 1.0)
        self.assertTrue(thin.headline_suppressed)

        self.assertEqual(full.resolved_coverage, 1.0)
        self.assertFalse(full.headline_suppressed)
        self.assertEqual(full.headline, 1.0)
        self.assertIn("headline", full.to_dict())
        self.assertEqual(full.gate_verdict.verdict, gv.VERDICT_PASS)

    def test_mutation_coverage_at_the_floor_is_sufficient(self):
        """MUTATION: moves coverage across the boundary by ONE item.

        Pins the comparison as ``>=`` and proves the suppression is driven by the
        declared floor rather than by "any undecided item at all" — a guard that
        suppressed on the mere presence of an out-of-coverage verdict would make
        every real suite permanently headline-less, and would be turned off.
        """
        c = contract(min_resolved_coverage=0.90)
        at_floor = gv.resolve_suite(c, decided(9, 0) + undecided(1))
        below = gv.resolve_suite(c, decided(89, 0) + undecided(11), asserted_n=100)
        self.assertEqual(at_floor.resolved_coverage, 0.90)
        self.assertFalse(at_floor.headline_suppressed)
        self.assertEqual(below.resolved_coverage, 0.89)
        self.assertTrue(below.headline_suppressed)

    def test_mutation_inferred_denominator_manufactures_coverage(self):
        """MUTATION: removes exactly the explicit ``asserted_n``.

        Reproduces the pre-fix denominator — inferred from the verdicts that
        arrived — over the same 50 decided items out of an asserted 100, and
        shows it reports 100% coverage of the subset the harness happened to
        reach. That is the gate-scope defect (a gate's scope must match the
        measured subset) with the numbers to prove it: 0.5 becomes 1.0 and the
        suppressed headline comes back.
        """
        honest = gv.resolve_suite(contract(), decided(50, 0), asserted_n=100)
        inferred = gv.resolve_suite(contract(), decided(50, 0))
        self.assertEqual(honest.resolved_coverage, 0.5)
        self.assertTrue(honest.headline_suppressed)
        self.assertEqual(inferred.resolved_coverage, 1.0)
        self.assertFalse(inferred.headline_suppressed)


class VocabularyReuseIsLockedNotAsserted(unittest.TestCase):
    """The module's docstring claims it reuses the dashboard plane's structure
    without importing it. Both halves are checked here rather than trusted."""

    def test_no_import_edge_to_the_view_plane(self):
        """``dashboard/`` is the VIEW plane (``dashboard/README.md`` plane rule).
        A scoring module that imports it acquires a dependency on the hub, and a
        benchmark run would then break when a page changes."""
        source = MODULE_PATH.read_text(encoding="utf-8")
        code = "\n".join(line for line in source.splitlines()
                         if not line.lstrip().startswith("#"))
        body = code.split('"""', 2)[-1]   # drop the module docstring
        self.assertNotIn("import dashboard", body)
        self.assertNotIn("from dashboard", body)

    def test_cause_words_match_the_panel_words_they_borrow(self):
        """Where the state is literally the same one, the spelling is the same
        one — so a reader moving between the two planes reads one idiom rather
        than two synonyms. Checked against ``dashboard/panels.py`` as text (no
        import), so a rename there surfaces here."""
        panels_src = (ROOT / "dashboard" / "panels.py").read_text(encoding="utf-8")
        self.assertIn('REPORTING_ABSENT = "absent"', panels_src)
        self.assertIn('CONTENT_EMPTY = "empty"', panels_src)
        self.assertEqual(gv.CAUSE_ABSENT, "absent")
        self.assertEqual(gv.CAUSE_EMPTY, "empty")

    def test_gate_verdicts_are_not_the_panel_status_words(self):
        """Deliberate NON-reuse: ``ok``/``absent``/``degraded`` classify a
        producer's liveness, these classify an item's decision. One label set
        over two subjects is the ``/health`` vs ``/api/health`` conflation the
        dashboard README exists to warn about."""
        self.assertEqual(set(gv.VERDICTS),
                         {"pass", "fail", "out-of-coverage"})
        self.assertNotIn("ok", gv.VERDICTS)
        self.assertNotIn("degraded", gv.VERDICTS)


if __name__ == "__main__":
    unittest.main()


class InteropWithTheRatifiedVerificationSchema(unittest.TestCase):
    """``orchestration/verification_report.schema.json`` is a ratified,
    measurement-plane, three-valued check contract with a MANDATORY
    ``inconclusive_reason``. ``out-of-coverage`` IS its ``inconclusive`` — one
    state, two spellings — so the two must be interconvertible rather than
    parallel. These lock the mapping so a drift becomes a test failure."""

    def test_the_mapping_is_total_over_every_cause(self):
        """A cause with no schema projection is a cause that cannot cross the
        boundary, which is how a second vocabulary starts."""
        self.assertEqual(set(gv.VERIFICATION_STATUS_BY_CAUSE), set(gv.ALL_CAUSES))
        self.assertEqual(set(gv.VERIFICATION_OUTCOME_BY_VERDICT), set(gv.VERDICTS))

    def test_every_cause_is_logically_unknown_never_fail(self):
        """CATCHES the conflation at the boundary. If any cause projected to
        ``logical_status: fail`` it would arrive downstream as a real negative
        finding — the exact defect, re-committed in the adapter."""
        for cause, (logical, _) in gv.VERIFICATION_STATUS_BY_CAUSE.items():
            self.assertEqual(logical, "unknown", cause)

    def test_out_of_coverage_projects_to_inconclusive_with_a_reason(self):
        v = gv.out_of_coverage("q1", gv.CAUSE_TIMEOUT, detail="budget exceeded")
        out = gv.to_verification_outcome(v)
        self.assertEqual(out["outcome"], "inconclusive")
        self.assertEqual(out["execution_status"], "timeout")
        self.assertEqual(out["logical_status"], "unknown")
        self.assertTrue(out["inconclusive_reason"])

    def test_an_operational_failure_reads_back_as_undecided_not_failed(self):
        """The schema's own rule: 'an error/timeout/unavailable is NOT proof of
        failure'. Reading a crashed verifier back as ``fail`` would import the
        defect from the other direction."""
        for execution, cause in (("error", gv.CAUSE_CHECKER_ERROR),
                                 ("timeout", gv.CAUSE_TIMEOUT),
                                 ("unavailable", gv.CAUSE_UNSUPPORTED)):
            with self.subTest(execution=execution):
                v = gv.from_verification_status("q1", logical_status="fail",
                                                execution_status=execution)
                self.assertEqual(v.verdict, gv.VERDICT_OUT_OF_COVERAGE)
                self.assertEqual(v.cause, cause)

    def test_a_conflict_between_sound_verifiers_is_not_a_fail(self):
        """``conflict`` is the schema's fourth logical value and is undecided,
        not negative — two sound verifiers disagreeing means nobody decided."""
        v = gv.from_verification_status("q1", logical_status="conflict")
        self.assertEqual(v.verdict, gv.VERDICT_OUT_OF_COVERAGE)

    def test_mutation_a_healthy_run_round_trips_to_the_decided_verdicts(self):
        """MUTATION: removes exactly the operational failure, holding
        ``logical_status`` fixed.

        Proves the reads above are driven by ``execution_status`` and not by a
        converter that returns ``out-of-coverage`` for everything — which would
        satisfy every positive in this class while destroying all real verdicts.
        """
        for logical in (gv.VERDICT_PASS, gv.VERDICT_FAIL):
            with self.subTest(logical=logical):
                v = gv.from_verification_status("q1", logical_status=logical,
                                                execution_status="ok")
                self.assertEqual(v.verdict, logical)
                self.assertIsNone(v.cause)
                self.assertEqual(gv.to_verification_outcome(v)["outcome"], logical)
