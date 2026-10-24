#!/usr/bin/env python3
"""Unit tests for index_state.derive_priority (graph node priority ordering)."""

import importlib.util
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("index_state", _REPO / "scripts/handoffs/index_state.py")
index_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(index_state)

CAMPAIGN = (
    "# C\n\n> **2026-10-22 ~08:15Z - newest.** work on NEW-1 and old-handoff-b.\n\n"
    "> **2026-10-21 ~20:22Z - older.** mentions OLD-2 only.\n"
)


def N(rid, open_=3, handoff=None, readiness="ready"):
    return {"id": rid, "open": open_, "handoff": handoff, "readiness": readiness}


def run(nodes, edges=(), text=CAMPAIGN):
    index_state.derive_priority(nodes, list(edges), text)
    return {n["id"]: n for n in nodes}


class PriorityTests(unittest.TestCase):
    def test_campaign_newest_beats_older_beats_none(self):
        r = run([N("NEW-1"), N("OLD-2"), N("ZZZ-3"), N("ZZZ-4", handoff="old-handoff-b.md")])
        self.assertEqual(r["NEW-1"]["priority_basis"]["campaign"], 2)
        self.assertEqual(r["ZZZ-4"]["priority_basis"]["campaign"], 2)   # by handoff stem
        self.assertEqual(r["OLD-2"]["priority_basis"]["campaign"], 1)
        self.assertEqual(r["ZZZ-3"]["priority_basis"]["campaign"], 0)
        self.assertGreater(r["NEW-1"]["priority"], r["OLD-2"]["priority"])
        self.assertGreater(r["OLD-2"]["priority"], r["ZZZ-3"]["priority"])
        self.assertEqual(r["NEW-1"]["priority"] , r["ZZZ-4"]["priority"])  # tie shares a value

    def test_mutation_removing_campaign_text_flattens(self):
        r = run([N("NEW-1"), N("ZZZ-3")], text="")
        self.assertEqual(r["NEW-1"]["priority"], r["ZZZ-3"]["priority"])

    def test_unblocks_is_transitive_and_counts_only_open_dependents(self):
        # C blocked on B blocked on A; D (no open) blocked on A.
        nodes = [N("A-1"), N("B-1", readiness="blocked"), N("C-1", readiness="blocked"),
                 N("D-1", open_=0, readiness="no_open")]
        edges = [{"from": "B-1", "to": "A-1", "kind": "dep"},
                 {"from": "C-1", "to": "B-1", "kind": "dep"},
                 {"from": "D-1", "to": "A-1", "kind": "dep"},
                 {"from": "A-1", "to": "C-1", "kind": "ref"}]      # ref edges ignored
        r = run(nodes, edges, text="")
        self.assertEqual(r["A-1"]["priority_basis"]["unblocks"], 2)   # B, C (not D)
        self.assertEqual(r["B-1"]["priority_basis"]["unblocks"], 1)
        self.assertGreater(r["A-1"]["priority"], r["B-1"]["priority"])

    def test_no_open_is_lowest_and_cycles_terminate(self):
        nodes = [N("X-1"), N("Y-1", readiness="blocked"), N("Z-1", open_=0, readiness="no_open")]
        edges = [{"from": "X-1", "to": "Y-1", "kind": "dep"},
                 {"from": "Y-1", "to": "X-1", "kind": "dep"}]
        r = run(nodes, edges, text="NEW-1 Z-1")
        self.assertEqual(r["Z-1"]["priority"], 0.0)
        self.assertEqual(r["Z-1"]["priority_rank"], 3)

    def test_rank_and_range(self):
        r = run([N("NEW-1"), N("OLD-2"), N("ZZZ-3")])
        self.assertEqual(r["NEW-1"]["priority"], 1.0)
        self.assertEqual(r["NEW-1"]["priority_rank"], 1)
        self.assertTrue(all(0.0 <= n["priority"] <= 1.0 for n in r.values()))

    def test_build_graph_exposes_priority_contract(self):
        g = index_state.build_graph(index_state.collect())
        self.assertIn("priority_basis", g)
        self.assertTrue(all("priority" in n and "priority_rank" in n for n in g["nodes"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
