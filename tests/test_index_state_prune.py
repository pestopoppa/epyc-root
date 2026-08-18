#!/usr/bin/env python3
"""Unit tests for index_state.prune_signal — the `open == 0` disambiguation.

Stdlib ``unittest`` only (no pytest dependency) so it runs anywhere with
``python3 tests/test_index_state_prune.py``; pytest also discovers it.

WHY THIS FILE EXISTS. `open == 0` was being read as "complete, prunable". Measured
2026-08-18: of 15 handoffs reporting `open == 0`, the first four inspected were all false
positives — a compatibility pointer, a handoff whose open work was stated in prose, a prompt
that never had tasks, and a notes-only reference. Pruning on that signal would have archived
live work. Each case below is one of those real handoffs, reduced to its status region.

Every blocker case is paired with a MUTATION case proving the guard is what rejects it: strip
the disqualifying phrase and the same handoff becomes a candidate. Without that pairing a test
can pass because the fixture is inert rather than because the guard fires.
"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "index_state", _REPO / "scripts" / "handoffs" / "index_state.py")
index_state = importlib.util.module_from_spec(_SPEC)
sys.modules["index_state"] = index_state
_SPEC.loader.exec_module(index_state)

ALL_CLOSED = {"open": 0, "closed": 3, "guarded": 0, "blocked": 0, "total": 3}


def _write(tmp: Path, name: str, text: str) -> Path:
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return p


class PruneSignalTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # ---- the four measured false positives -------------------------------

    def test_compatibility_pointer_is_not_prunable(self):
        """meta-harness-optimization.md — archiving it breaks the routing it exists to provide."""
        p = _write(self.tmp, "pointer.md",
                   "# Meta-Harness Optimization — Compatibility Pointer\n"
                   "**Status**: RETAINED COMPATIBILITY POINTER — no standalone implementation queue.\n"
                   "- [x] done\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "pointer")
        self.assertIn("POINTER", sig["evidence"].upper())

    def test_prose_open_work_is_not_prunable(self):
        """benchmark-results-dashboard.md — live work stated in prose, never checkboxed."""
        p = _write(self.tmp, "prose.md",
                   "# Benchmark Results Dashboard\n"
                   "**Status**: active — registry inventory landed 2026-07-29; "
                   "artifact ingestion and UI remain open\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "prose-open")

    def test_prompt_not_a_task_list_is_not_prunable(self):
        """fable5-architecture-review-2.md — nothing to complete, so 0 open is meaningless."""
        p = _write(self.tmp, "prompt.md",
                   "# Fable 5 Architectural Review — window 2 (a prompt, not a task list)\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "not-a-task-list")

    def test_notes_only_reference_is_not_prunable(self):
        """orchestrator-nps4-48x4-notes.md — never an implementation queue."""
        p = _write(self.tmp, "notes.md",
                   "# Orchestrator Rework Notes\n"
                   "**Status**: REFRESHED 2026-05-28 — notes-only topology reference; "
                   "not an implementation queue\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "not-a-task-list")

    # ---- mutation tests: the guard, not the fixture, is what rejects ------

    def test_mutation_removing_pointer_phrase_makes_it_a_candidate(self):
        p = _write(self.tmp, "mutated_pointer.md",
                   "# Meta-Harness Optimization\n"
                   "**Status**: active — everything landed.\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertTrue(sig["candidate"], "guard did not fire on the phrase; test was vacuous")
        self.assertIsNone(sig["blocker"])

    def test_mutation_removing_prose_open_phrase_makes_it_a_candidate(self):
        p = _write(self.tmp, "mutated_prose.md",
                   "# Benchmark Results Dashboard\n"
                   "**Status**: active — registry inventory landed 2026-07-29.\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertTrue(sig["candidate"], "guard did not fire on the phrase; test was vacuous")

    # ---- structural cases ------------------------------------------------

    def test_no_checkboxes_is_not_prunable(self):
        """0 of 0 boxes: `open == 0` was never a completion signal here."""
        p = _write(self.tmp, "empty.md", "# Some dossier\n\nProse only.\n")
        sig = index_state.prune_signal(
            p, {"open": 0, "closed": 0, "guarded": 0, "blocked": 0, "total": 0})
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "no-checkboxes")

    def test_undispatchable_boxes_block_and_are_named(self):
        """0 open but guarded/blocked boxes remain — unresolved, and the reason must be named."""
        p = _write(self.tmp, "guarded.md", "# Thing\n**Status**: active\n")
        sig = index_state.prune_signal(
            p, {"open": 0, "closed": 1, "guarded": 2, "blocked": 1, "total": 4})
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "undispatchable-tasks")
        self.assertIsNotNone(sig["evidence"], "a non-candidate must never report blocker=None")

    def test_open_tasks_block(self):
        p = _write(self.tmp, "open.md", "# Thing\n**Status**: active\n")
        sig = index_state.prune_signal(
            p, {"open": 2, "closed": 1, "guarded": 0, "blocked": 0, "total": 3})
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "open-tasks")

    def test_genuinely_complete_handoff_is_a_candidate(self):
        """The signal must still be USEFUL — a real all-done handoff has to surface."""
        p = _write(self.tmp, "done.md",
                   "# Tree draft forward port plan\n"
                   "**Status**: all phases landed and validated.\n"
                   "- [x] a\n- [x] b\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertTrue(sig["candidate"])
        self.assertIsNone(sig["blocker"])

    # ---- structural open-work assertions outside the status region -------
    #
    # Measured 2026-08-18, SECOND PASS: four handoffs passed the status-region screen above and
    # were still live. Every one announced it structurally — in a heading, or in a line-leading
    # bold run — rather than in its status line. These are those four, reduced.

    def test_open_section_heading_blocks(self):
        """moe-aggregate-deployment-wins-brief.md — `## Still open (GPU-kernel, our side)`."""
        p = _write(self.tmp, "still_open.md",
                   "# Brief\n**Status**: MEASURED role->config recommendations.\n\n"
                   "## Win 1\ntext\n\n## Still open (GPU-kernel, our side)\n- a thing\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "open-section")
        self.assertIn("Still open", sig["evidence"])

    def test_open_questions_heading_blocks(self):
        """granite-97m-r2-bench-plan.md — a live question under `## Open Questions`."""
        p = _write(self.tmp, "open_q.md",
                   "# Bench plan\n**Status**: phases landed.\n\n## Open Questions\n\n"
                   "- Is the K2 chunker scoped to ship before this bench wants to run?\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "open-section")

    def test_line_leading_bold_assertion_blocks(self):
        """fable5-window2-findings-05b — `**Still OPEN (not measured-dead):** the Q8 kernel`."""
        p = _write(self.tmp, "bold_open.md",
                   "# Findings\n**Status**: findings supplement.\n\n"
                   "**Still OPEN (not measured-dead):** the Q8 dequant-GEMV kernel.\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "open-assertion")

    def test_mostly_done_status_blocks(self):
        """gpu-candidates-surface-qwen38-update.md — "MOSTLY DONE ... parked on a restart"."""
        p = _write(self.tmp, "mostly.md",
                   "# GPU candidates surface\n"
                   "**Status**: MOSTLY DONE — the agentic re-run is parked on a devcontainer restart.\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertFalse(sig["candidate"])
        self.assertEqual(sig["blocker"], "prose-open")

    # ---- the screen must not become vacuous ------------------------------

    def test_bold_run_without_an_open_marker_does_not_block(self):
        """Bold is everywhere in these documents; only an OPEN MARKER inside it may block."""
        p = _write(self.tmp, "bold_ok.md",
                   "# Thing\n**Status**: complete.\n\n"
                   "**Bottom line up front:** everything landed and was validated.\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertTrue(sig["candidate"],
                        "an ordinary bold lead-in blocked; the screen is over-matching")

    def test_task_line_mentioning_remaining_does_not_block(self):
        """A closed task whose TEXT says 'remaining' is not an open-work assertion."""
        p = _write(self.tmp, "task_text.md",
                   "# Thing\n**Status**: complete.\n\n"
                   "- [x] Fold the remaining rows into the table\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertTrue(sig["candidate"],
                        "a closed task line blocked; the screen is over-matching")

    # ---- scope: the body must not disqualify the handoff -----------------

    def test_body_text_does_not_leak_into_the_status_region(self):
        """A task line containing 'pending' must not disqualify an otherwise-complete handoff."""
        body = "\n".join(f"- [x] task {i} — nothing pending here" for i in range(60))
        p = _write(self.tmp, "body.md", f"# Thing\n**Status**: complete.\n\n{body}\n")
        sig = index_state.prune_signal(p, ALL_CLOSED)
        self.assertTrue(sig["candidate"],
                        "body text leaked into the status region; scan is not bounded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
