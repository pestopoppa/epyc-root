#!/usr/bin/env python3
"""RC-11: `pii_fixture_eval` must report false-accept and false-reject SEPARATELY.

Spec: handoffs/active/reviewer-calibration-accounting.md -> RC-11 (intake-1307).

The validator used to print one aggregate, `passed/total`, over a fixture that mixes 20
must-block rows with 22 must-not-block rows. That merged two errors with opposite costs: a
secret the hook let through (FALSE-ACCEPT) and clean text the hook refused (FALSE-REJECT).
The 39/40 -> 42/42 repair of 2026-08-25 was a pure false-reject repair, but it was reported,
wiki-cited, and used to call the candidate gate green as one improved fraction, from which
nobody could tell which side had moved.

Every positive test below is PAIRED WITH A MUTATION that removes the signal under test, so a
one-sided assertion cannot pass against the merged implementation it is meant to reject.

These are observations about a same-sample fixture (RC-6a / RC-12): they do not gate anything.
"""

import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts" / "validate") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts" / "validate"))

import pii_fixture_eval as pfe  # noqa: E402


def _case(idx, expected_block, actual_block, labels=(), context_type="doc"):
    return pfe.CaseResult(
        index=idx,
        expected_block=expected_block,
        actual_block=actual_block,
        kind=pfe.classify(expected_block, actual_block),
        labels=tuple(labels),
        context_type=context_type,
        text=f"case{idx}",
    )


class ClassifyTests(unittest.TestCase):
    def test_all_four_confusion_cells_are_distinct(self):
        self.assertEqual(pfe.classify(True, True), pfe.TRUE_BLOCK)
        self.assertEqual(pfe.classify(True, False), pfe.FALSE_ACCEPT)
        self.assertEqual(pfe.classify(False, True), pfe.FALSE_REJECT)
        self.assertEqual(pfe.classify(False, False), pfe.TRUE_PASS)

    def test_the_two_error_cells_are_not_the_same_label(self):
        """MUTATION for the test above. A classifier that returned one generic "fail" for both
        errors would still satisfy a test that only checked "an error was detected"."""
        self.assertNotEqual(pfe.classify(True, False), pfe.classify(False, True))


class SeparateSidesTests(unittest.TestCase):
    def test_a_missed_secret_lands_only_on_the_false_accept_side(self):
        s = pfe.summarize([_case(1, True, False, labels=("secret",))])
        self.assertEqual((s.fa_errors, s.fa_denominator), (1, 1))
        self.assertEqual((s.fr_errors, s.fr_denominator), (0, 0))
        self.assertEqual(dict(s.fa_causes), {"secret": 1})
        self.assertEqual(dict(s.fr_causes), {}, "a false-accept was counted as a false-reject")

    def test_an_over_block_lands_only_on_the_false_reject_side(self):
        """MUTATION for the test above: the opposite error must move the OTHER counter. A
        summarizer that incremented one shared error counter would pass either test alone."""
        s = pfe.summarize([_case(1, False, True, context_type="config")])
        self.assertEqual((s.fr_errors, s.fr_denominator), (1, 1))
        self.assertEqual((s.fa_errors, s.fa_denominator), (0, 0))
        self.assertEqual(dict(s.fr_causes), {"config": 1})
        self.assertEqual(dict(s.fa_causes), {}, "a false-reject was counted as a false-accept")

    def test_the_two_sides_have_their_own_denominators(self):
        s = pfe.summarize([
            _case(1, True, True, labels=("secret",)),
            _case(2, True, False, labels=("secret",)),
            _case(3, False, False),
            _case(4, False, False),
            _case(5, False, True, context_type="doc"),
        ])
        self.assertEqual((s.fa_errors, s.fa_denominator), (1, 2))
        self.assertEqual((s.fr_errors, s.fr_denominator), (1, 3))
        self.assertAlmostEqual(s.fa_rate, 0.5)
        self.assertAlmostEqual(s.fr_rate, 1 / 3)

    def test_one_aggregate_cannot_distinguish_what_the_two_sides_do(self):
        """MUTATION for the test above, and the reason RC-11 exists. These two runs have
        IDENTICAL merged accuracy (4/5) and opposite meanings: the first let a secret through,
        the second only over-blocked. Any report that emitted a single number would be unable
        to tell them apart, so this asserts the split numbers DO differ."""
        leaked = pfe.summarize([
            _case(1, True, False, labels=("secret",)),
            _case(2, True, True, labels=("secret",)),
            _case(3, False, False), _case(4, False, False), _case(5, False, False),
        ])
        over_blocked = pfe.summarize([
            _case(1, True, True, labels=("secret",)),
            _case(2, True, True, labels=("secret",)),
            _case(3, False, True), _case(4, False, False), _case(5, False, False),
        ])
        self.assertEqual(leaked.total_errors, over_blocked.total_errors)
        self.assertNotEqual(
            (leaked.fa_errors, leaked.fr_errors),
            (over_blocked.fa_errors, over_blocked.fr_errors),
            "the split is not actually separating the two error kinds",
        )

    def test_no_merged_accuracy_is_exposed(self):
        s = pfe.summarize([_case(1, True, True, labels=("secret",))])
        for banned in ("accuracy", "passed", "pass_rate", "score", "correct"):
            self.assertFalse(
                hasattr(s, banned),
                f"Sides re-exposed a merged aggregate `{banned}`; RC-11 forbids it",
            )


class NonComputableSideTests(unittest.TestCase):
    def test_a_side_with_no_denominator_reports_none_not_zero(self):
        s = pfe.summarize([_case(1, False, False)])
        self.assertIsNone(s.fa_rate, "0/0 was reported as a rate; that is a fabricated 0%")
        self.assertIsNotNone(s.fr_rate)

    def test_a_side_with_a_denominator_does_report_a_rate(self):
        """MUTATION for the test above: `fa_rate` must not be None merely because it is always
        None. Without this, a property hard-coded to return None would pass."""
        s = pfe.summarize([_case(1, True, True, labels=("secret",))])
        self.assertEqual(s.fa_rate, 0.0)

    def test_report_states_the_non_computable_side_even_when_both_sides_are_clean(self):
        results = [_case(1, True, True, labels=("secret",)), _case(2, False, False)]
        text = "\n".join(pfe.report(pfe.summarize(results), results))
        self.assertIn("NOT COMPUTABLE", text)
        self.assertIn("false-accept", text)
        self.assertIn("false-reject", text)
        self.assertIn("negative-side label coverage", text)

    def test_report_names_both_sides_when_only_one_side_has_an_error(self):
        """MUTATION for the test above: the omitted side must be stated, not dropped. A report
        that only printed a side when it had errors would pass a both-clean test but silently
        omit `false-accept: 0/20` on a run whose only errors were over-blocks -- which is
        exactly the 2026-08-25 reporting failure."""
        results = [_case(1, True, True, labels=("secret",)), _case(2, False, True)]
        text = "\n".join(pfe.report(pfe.summarize(results), results))
        self.assertIn("false-accept", text)
        self.assertIn("0/1 must-block rows", text)


class NegativeCoverageTests(unittest.TestCase):
    def test_coverage_histogram_shows_which_label_kinds_have_a_clean_row(self):
        s = pfe.summarize([
            _case(1, True, True, labels=("account_number",)),
            _case(2, False, False, labels=("secret",)),
            _case(3, False, False),
        ])
        self.assertEqual(
            dict(s.negative_label_coverage), {"secret": 1, "<no-pii-span>": 1}
        )
        self.assertNotIn(
            "account_number", s.negative_label_coverage,
            "a label with no must-not-block row must be visibly ABSENT from coverage",
        )

    def test_coverage_counts_a_negative_row_when_one_exists(self):
        """MUTATION for the test above: absence must mean absence. A histogram that never
        recorded any label would also lack `account_number` and pass the assertion above."""
        s = pfe.summarize([_case(1, False, False, labels=("account_number",))])
        self.assertEqual(dict(s.negative_label_coverage), {"account_number": 1})

    def test_coverage_is_built_from_negative_rows_only(self):
        """A must-block row must never contribute to the untested-direction diagnostic --
        including a must-block row the hook GOT WRONG. Both branches are covered here because
        a leak on only the false-accept branch is the easy version of this bug to write."""
        s = pfe.summarize([
            _case(1, True, True, labels=("secret",)),
            _case(2, True, False, labels=("account_number",)),
        ])
        self.assertEqual(dict(s.negative_label_coverage), {})
        self.assertEqual(dict(s.fa_causes), {"account_number": 1},
                         "the false-accept cause histogram stopped recording")


class RealFixtureTests(unittest.TestCase):
    """Observations on the shipped fixture. These assert the SHAPE of the accounting, never a
    quality bar -- the fixture is same-sample with the hook it certifies (RC-12)."""

    def setUp(self):
        self.rows = pfe.load_rows(pfe.DEFAULT_FIXTURE)

    def test_fixture_has_both_sides_so_neither_rate_is_vacuous(self):
        pos = [r for r in self.rows if bool(r["expected_match"])]
        neg = [r for r in self.rows if not bool(r["expected_match"])]
        self.assertGreater(len(pos), 0, "no must-block rows: the false-accept rate would be 0/0")
        self.assertGreater(len(neg), 0, "no must-not-block rows: the false-reject rate would be 0/0")

    def test_row_labels_reads_the_span_annotations(self):
        labelled = [r for r in self.rows if pfe.row_labels(r)]
        self.assertGreater(len(labelled), 0, "row_labels never extracted a label kind")
        self.assertIn("secret", {lab for r in self.rows for lab in pfe.row_labels(r)})


if __name__ == "__main__":
    unittest.main()
