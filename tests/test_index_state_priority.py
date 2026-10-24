#!/usr/bin/env python3
"""Unit tests for index_state.derive_priority (graph node priority ordering)."""

import importlib.util
import json
import tempfile
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


def FDOC(rows, tiers=None, generated="2026-10-24T09:00Z"):
    return {"generated_at": generated, "tiers": tiers or {"1": "T1 unblocked"}, "rows": rows}


class PriorityFileTests(unittest.TestCase):
    """override > file > heuristic, with the source recorded per node."""

    def test_file_score_beats_heuristic_and_is_recorded(self):
        # CAMPAIGN names NEW-1, so the heuristic alone would rank NEW-1 first; the file says otherwise.
        nodes = [N("NEW-1"), N("ZZZ-3")]
        doc = FDOC({"ZZZ-3": {"tier": 1, "rank": 1, "score": 0.9, "basis": "gates C4", "blocker": "", "unblocks": ["A-1"]},
                    "NEW-1": {"tier": 2, "rank": 2, "score": 0.4}})
        index_state.derive_priority(nodes, [], CAMPAIGN, doc, None)
        r = {n["id"]: n for n in nodes}
        self.assertGreater(r["ZZZ-3"]["priority"], r["NEW-1"]["priority"])
        self.assertEqual(r["ZZZ-3"]["priority_rank"], 1)
        pb = r["ZZZ-3"]["priority_basis"]
        self.assertEqual((pb["source"], pb["tier"], pb["tier_name"], pb["basis"]), ("file", 1, "T1 unblocked", "gates C4"))
        self.assertEqual(pb["unblocks_rows"], ["A-1"])
        self.assertEqual(r["NEW-1"]["priority_basis"]["campaign"], 2)       # heuristic fields still present

    def test_override_beats_file(self):
        nodes = [N("A-1"), N("B-1")]
        doc = FDOC({"A-1": {"tier": 1, "score": 0.9}, "B-1": {"tier": 2, "score": 0.5}})
        ovr = {"rows": {"B-1": {"score": 1.0, "note": "operator pin"}}}
        index_state.derive_priority(nodes, [], "", doc, ovr)
        r = {n["id"]: n for n in nodes}
        self.assertEqual(r["B-1"]["priority"], 1.0)
        self.assertEqual(r["B-1"]["priority_rank"], 1)
        self.assertEqual(r["B-1"]["priority_basis"]["source"], "override")
        self.assertEqual(r["B-1"]["priority_basis"]["note"], "operator pin")
        self.assertEqual(r["A-1"]["priority_basis"]["source"], "file")
        self.assertEqual(r["A-1"]["priority_rank"], 2)

    def test_fallback_rows_sit_below_every_file_row_and_keep_heuristic_order(self):
        nodes = [N("F-1"), N("F-2"), N("NEW-1"), N("ZZZ-3")]       # NEW-1 is campaign-named, ZZZ-3 is not
        doc = FDOC({"F-1": {"score": 0.3}, "F-2": {"score": 0.2}})
        index_state.derive_priority(nodes, [], CAMPAIGN, doc, None)
        r = {n["id"]: n for n in nodes}
        self.assertEqual(r["NEW-1"]["priority_basis"]["source"], "heuristic")
        self.assertLess(r["NEW-1"]["priority"], r["F-2"]["priority"])
        self.assertLess(r["ZZZ-3"]["priority"], r["NEW-1"]["priority"])   # heuristic order preserved
        self.assertGreater(r["F-1"]["priority"], r["F-2"]["priority"])

    def test_no_file_is_exactly_the_old_heuristic(self):
        a = [N("NEW-1"), N("OLD-2"), N("ZZZ-3")]
        b = [N("NEW-1"), N("OLD-2"), N("ZZZ-3")]
        index_state.derive_priority(a, [], CAMPAIGN)
        index_state.derive_priority(b, [], CAMPAIGN, {}, {})
        self.assertEqual([(n["priority"], n["priority_rank"]) for n in a], [(n["priority"], n["priority_rank"]) for n in b])
        self.assertTrue(all(n["priority_basis"]["source"] == "heuristic" for n in a))
        self.assertEqual(a[0]["priority"], 1.0)

    def test_file_entry_for_row_without_open_work_or_unknown_row_is_ignored(self):
        nodes = [N("A-1"), N("D-1", open_=0, readiness="no_open")]
        doc = FDOC({"A-1": {"score": 0.5}, "D-1": {"score": 0.99}, "GONE-9": {"score": 0.99}})
        info = index_state.derive_priority(nodes, [], "", doc, None)
        r = {n["id"]: n for n in nodes}
        self.assertEqual(r["D-1"]["priority_basis"]["source"], "heuristic")
        self.assertEqual(r["D-1"]["priority"], 0.0)
        self.assertEqual(r["A-1"]["priority_basis"]["source"], "file")
        self.assertIn("D-1", info["file_rows_unused"])
        self.assertIn("GONE-9", info["file_rows_unused"])

    def test_ties_share_best_rank(self):
        nodes = [N("A-1"), N("B-1"), N("C-1")]
        index_state.derive_priority(nodes, [], "", FDOC({"A-1": {"score": .8}, "B-1": {"score": .8}, "C-1": {"score": .1}}), None)
        self.assertEqual([n["priority_rank"] for n in nodes], [1, 1, 3])

    def test_mutation_dropping_the_file_changes_the_order(self):
        base = [N("NEW-1"), N("ZZZ-3")]
        withf = [N("NEW-1"), N("ZZZ-3")]
        doc = FDOC({"ZZZ-3": {"score": 0.9}, "NEW-1": {"score": 0.2}})
        index_state.derive_priority(base, [], CAMPAIGN)
        index_state.derive_priority(withf, [], CAMPAIGN, doc, None)
        self.assertGreater(base[0]["priority"], base[1]["priority"])
        self.assertLess(withf[0]["priority"], withf[1]["priority"])

    def test_loader_rejects_bad_scores_and_bad_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.json"
            self.assertEqual(index_state.load_priority_file(p), ({}, []))           # absent = fine
            p.write_text("{not json")
            self.assertTrue(index_state.load_priority_file(p)[1])
            p.write_text(json.dumps({"rows": {"A-1": {"score": 1.5}, "B-1": {"score": "x"}, "C-1": {"score": True},
                                              "D-1": {"score": 0.5}}}))
            doc, probs = index_state.load_priority_file(p)
            self.assertEqual(sorted(doc["rows"]), ["D-1"])
            self.assertEqual(len(probs), 3)

    def test_committed_files_are_valid_and_cover_real_rows(self):
        for pf in (index_state.PRIORITY_FILE, index_state.PRIORITY_OVERRIDE):
            doc, probs = index_state.load_priority_file(pf)
            self.assertEqual(probs, [], pf.name)
        doc, _ = index_state.load_priority_file(index_state.PRIORITY_FILE)
        self.assertTrue(doc.get("generated_by") and doc.get("generated_at") and doc.get("method"))
        state = index_state.collect()
        self.assertGreater(len(set(doc["rows"]) & set(state["rows"])), 100)

    def test_build_graph_reports_sources(self):
        g = index_state.build_graph(index_state.collect())
        src = g["priority_basis"]["sources"]
        self.assertEqual(sum(src.values()), len(g["nodes"]))
        self.assertTrue(all(n["priority_basis"].get("source") in ("override", "file", "heuristic") for n in g["nodes"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
