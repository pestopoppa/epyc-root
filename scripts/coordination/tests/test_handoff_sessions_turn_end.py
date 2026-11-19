"""Operator rulings 2026-11-02 (ws58): turn-end rules in every prompt, light worker persist, ONE index writer."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import handoff_sessions as hs  # noqa: E402
import index_regen as ir  # noqa: E402

E = {"handoff": "handoffs/active/demo.md", "engine": "claude"}
STOP_INVITES = ("wrap up, end the turn", "END THE TURN", "At a milestone", "index_state.py --check")


class TurnEndPrompts(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()

    def prompts(self):
        endf = os.path.join(self.flags, "x.ended")
        open(endf, "w").write("rc=0\n")
        return {"brief": hs.brief_text("demo", E, self.flags), "continue": hs.continue_prompt("demo", E, self.flags),
                "end": hs.end_prompt("demo", E, self.flags, "row-1", endf), "idle": hs.idle_prompt("demo", E, self.flags)}

    def test_every_prompt_carries_the_three_turn_end_points_and_light_persist(self):
        for name, p in self.prompts().items():
            self.assertIn("(a) a row is published", p, name)
            self.assertIn("(c) the handoff is done", p, name)
            self.assertIn("do it now", p, name)
            self.assertIn("Never run index_state.py", p, name)

    def test_no_wording_invites_stopping(self):
        for name, p in self.prompts().items():
            for bad in STOP_INVITES:
                self.assertNotIn(bad, p, f"{name}: {bad}")


class CentralIndexWriter(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()

    def test_dispatcher_spawns_regen_at_most_every_interval(self):
        calls = []
        self.assertTrue(hs.maybe_regen_index(self.flags, 1000.0, spawn=calls.append))
        self.assertFalse(hs.maybe_regen_index(self.flags, 1000.0 + hs.INDEX_REGEN_INTERVAL_S - 1, spawn=calls.append))
        self.assertTrue(hs.maybe_regen_index(self.flags, 1000.0 + hs.INDEX_REGEN_INTERVAL_S, spawn=calls.append))
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0][2].endswith("index_regen.py"))

    def test_regen_stamp_throttles(self):
        self.assertTrue(ir.due(self.flags, 600))
        ir.touch_stamp(self.flags)
        self.assertFalse(ir.due(self.flags, 600))
        self.assertEqual(ir.main(["--flags", self.flags, "--worktree", "/nonexistent"]), 0)  # not due: no git touched

    def test_regen_commits_only_generated_files(self):
        self.assertEqual(set(ir.GENERATED), {"handoffs/active/.index-state.json", "handoffs/active/.index-graph.json",
                                             "handoffs/active/master-handoff-index.md"})


if __name__ == "__main__":
    unittest.main()
