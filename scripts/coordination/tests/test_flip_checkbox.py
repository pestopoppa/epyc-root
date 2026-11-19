#!/usr/bin/env python3
"""Tests for B8 flip_checkbox — uniqueness (0/1/many) + dry-run-no-write.

Uses tmp fixture files only; never touches a real handoff. Stdlib unittest.
"""
import sys
import tempfile
import unittest
from pathlib import Path

_COORD = Path(__file__).resolve().parents[1]
if str(_COORD) not in sys.path:
    sys.path.insert(0, str(_COORD))

import flip_checkbox as fc  # noqa: E402


HANDOFF = """# Some Handoff

## Work Items
- [ ] **B5** verdict wiring for the batch loop
- [ ] **B8** checkbox flip helper
- [x] **B1** manifest compiler ✅ 2026-07-16 (landed)
- [ ] **B9** status reporter

## Nested
  - [ ] **N1** a nested item
"""


class TestFlipUniqueness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "handoff.md"
        self.path.write_text(HANDOFF)

    def tearDown(self):
        self.tmp.cleanup()

    def test_flip_one_dry_run_default_no_write(self):
        before = self.path.read_text()
        diff = fc.flip(self.path, "B5", "2026-07-17", "tests green")
        self.assertIn("- [x] **B5**", diff)
        self.assertIn("✅ 2026-07-17 [no-belief: unrecorded] tests green", diff)
        # default dry_run=True => file unchanged.
        self.assertEqual(self.path.read_text(), before)

    def test_flip_writes_when_dry_run_false(self):
        fc.flip(self.path, "B5", "2026-07-17", "tests green", dry_run=False)
        text = self.path.read_text()
        self.assertIn("- [x] **B5** verdict wiring for the batch loop ✅ 2026-07-17 [no-belief: unrecorded] tests green", text)
        # every OTHER line is byte-identical.
        self.assertIn("- [ ] **B8** checkbox flip helper", text)
        self.assertIn("- [ ] **B9** status reporter", text)

    def test_zero_anchor_raises(self):
        with self.assertRaises(fc.CheckboxFlipError):
            fc.flip(self.path, "NOPE", "2026-07-17", "x")

    def test_already_flipped_raises(self):
        # B1 is already [x]; the unchecked anchor is absent -> 0 matches.
        with self.assertRaises(fc.CheckboxFlipError):
            fc.flip(self.path, "B1", "2026-07-17", "x")

    def test_ambiguous_many_anchors_raises(self):
        dup = HANDOFF + "\n- [ ] **B5** a duplicate token line\n"
        self.path.write_text(dup)
        with self.assertRaises(fc.CheckboxFlipError):
            fc.flip(self.path, "B5", "2026-07-17", "x")

    def test_token_boundary_no_prefix_collision(self):
        # token 'B' must NOT match '- [ ] **B5'/'**B8'/'**B9'.
        with self.assertRaises(fc.CheckboxFlipError):
            fc.flip(self.path, "B", "2026-07-17", "x")

    def test_nested_indented_anchor(self):
        diff = fc.flip(self.path, "N1", "2026-07-17", "nested ok")
        self.assertIn("  - [x] **N1**", diff)

    def test_empty_note_omits_parens(self):
        diff = fc.flip(self.path, "B9", "2026-07-17", "")
        self.assertIn("✅ 2026-07-17", diff)
        self.assertNotIn("()", diff)

    def test_idempotent_re_run_after_write_raises(self):
        fc.flip(self.path, "B5", "2026-07-17", "note", dry_run=False)
        with self.assertRaises(fc.CheckboxFlipError):
            fc.flip(self.path, "B5", "2026-07-17", "note", dry_run=False)


class TestFlipMany(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "handoff.md"
        self.path.write_text(HANDOFF)

    def tearDown(self):
        self.tmp.cleanup()

    def test_flip_many_dry_run_no_write(self):
        before = self.path.read_text()
        diffs = fc.flip_many(
            [
                {"checkbox_token": "B5", "evidence_note": "a"},
                {"checkbox_token": "B8", "evidence_note": "b"},
            ],
            handoff_path=self.path,
            date="2026-07-17",
        )
        self.assertEqual(self.path.read_text(), before)  # no write
        key = str(self.path)
        self.assertIn("- [x] **B5**", diffs[key])
        self.assertIn("- [x] **B8**", diffs[key])

    def test_flip_many_writes_both(self):
        fc.flip_many(
            [
                fc.FlipSpec("B5", "2026-07-17", "a"),
                fc.FlipSpec("B9", "2026-07-17", "c"),
            ],
            handoff_path=self.path,
            dry_run=False,
        )
        text = self.path.read_text()
        self.assertIn("- [x] **B5** verdict wiring for the batch loop ✅ 2026-07-17 [no-belief: unrecorded] a", text)
        self.assertIn("- [x] **B9** status reporter ✅ 2026-07-17 [no-belief: unrecorded] c", text)

    def test_flip_many_all_or_nothing_on_failure(self):
        before = self.path.read_text()
        with self.assertRaises(fc.CheckboxFlipError):
            fc.flip_many(
                [
                    {"checkbox_token": "B5", "evidence_note": "a"},
                    {"checkbox_token": "NOPE", "evidence_note": "b"},
                ],
                handoff_path=self.path,
                date="2026-07-17",
                dry_run=False,
            )
        # first flip must NOT have been written (all-or-nothing).
        self.assertEqual(self.path.read_text(), before)


if __name__ == "__main__":
    unittest.main()


class TestUnifiedTickSuffix(unittest.TestCase):
    """Handoff standard decision 1: ONE suffix `✅ date [belief|no-belief] verdict`; readers accept legacy forms."""

    def test_flip_line_unified(self):
        self.assertEqual(fc.flip_line("  - [ ] **A-1** do x", "2026-11-19", "clm_ab1", "PASS 3/3"),
                         "  - [x] **A-1** do x ✅ 2026-11-19 [belief: clm_ab1] PASS 3/3")
        self.assertEqual(fc.flip_line("- [ ] y", "2026-11-19", "no-belief: tooling"),
                         "- [x] y ✅ 2026-11-19 [no-belief: tooling]")

    def test_flip_line_refuses(self):
        for bad in (("- [x] done", "2026-11-19", "cc"), ("- [ ] y", "2026-11-19", "maybe"), ("- [ ] y", "11/19", "cc")):
            with self.assertRaises(fc.CheckboxFlipError):
                fc.flip_line(*bad)

    def test_flip_with_belief(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "h.md"
            p.write_text(HANDOFF)
            fc.flip(p, "B5", "2026-07-17", "KEEP +4%", dry_run=False, belief="cc")
            self.assertIn("loop ✅ 2026-07-17 [belief: cc] KEEP +4%", p.read_text())

    def test_parse_tick_unified_and_legacy(self):
        P = fc.parse_tick
        self.assertEqual(P("- [x] a ✅ 2026-11-19 [belief: clm_x] KEEP +3%"),
                         {"date": "2026-11-19", "belief": "clm_x", "verdict": "KEEP +3%", "form": "unified"})
        self.assertEqual(P("- [x] a ✅ 2026-11-19 [no-belief: build only] landed")["belief"], "no-belief: build only")
        self.assertEqual(P("- [x] a ✅ 2026-10-30 [belief: cc]")["form"], "belief-only")
        self.assertEqual(P("- [x] a ✅ 2026-07-16 (landed)")["form"], "note")
        self.assertEqual(P("- [x] a ✅ 2026-07-16 (landed)")["verdict"], "landed")
        self.assertEqual(P("- [x] a ✅ 2026-08-13 <!-- worker-checkpoint:wcp-1 -->")["form"], "marker")
        self.assertEqual(P("- [x] a ✅ 2026-08-13")["form"], "bare")
        self.assertIsNone(P("- [ ] open box"))
        # the LAST tick on the line wins (earlier ✅ dates are history quoted in the text)
        self.assertEqual(P("- [x] a (was ✅ 2026-01-01) ✅ 2026-11-19 [belief: cc] PASS")["date"], "2026-11-19")

