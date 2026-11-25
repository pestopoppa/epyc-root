#!/usr/bin/env python3
"""QUIET-YIELD (pipeline-mgmt 2026-11-25): a low-rank quiet-host row yields to a better-ranked bandwidth-heavy row it would
block under the beside-quiet rule; capped at 2 h. Replays the rka r5 (rank 60) vs conv-state / iqk (rank 30) inversion."""
import os
import sys
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
RKA, CONV, IQK = "rka-a3b-d-remeasure-q-20261123-r5", "ak-cpu-conv-state-fwd-20261124-r4", "ak-cpu-a3b-iqk-q8-decode-20261125"
QS = ["q0", "q1", "q2"]


def cand(rid, rank, qs=QS):
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": float(rank), "shape": "quarter",
            "options": [frozenset(rf.expand({q})) for q in qs]}


ROWS = {RKA: {"id": RKA, "requires_quiet_host": True, "shape": "quarter"},
        CONV: {"id": CONV, "bandwidth_heavy": True, "shape": "quarter"},
        IQK: {"id": IQK, "bandwidth_heavy": True, "shape": "quarter"},
        "plain": {"id": "plain", "bandwidth_heavy": False, "shape": "quarter"}}


class QuietYield(unittest.TestCase):
    def test_incident_replay_quiet_yields(self):
        kept, lines, st = rf.quiet_yield_filter([cand(RKA, 60), cand(CONV, 30), cand(IQK, 30)], ROWS, {}, NOW)
        self.assertEqual({c["id"] for c in kept}, {CONV, IQK})
        self.assertIn(f"QUIET-YIELD {RKA} to higher-rank ", lines[RKA])
        self.assertEqual(st, {RKA: NOW})

    def test_cap_grants_quiet(self):
        st = {RKA: NOW - rf.QUIET_YIELD_CAP_S - 1}
        kept, lines, new = rf.quiet_yield_filter([cand(RKA, 60), cand(CONV, 30)], ROWS, st, NOW)
        self.assertIn(RKA, {c["id"] for c in kept})
        self.assertEqual(lines, {})
        kept, _, new = rf.quiet_yield_filter([cand(RKA, 60), cand(CONV, 30)], ROWS, {RKA: NOW - 3600}, NOW)
        self.assertNotIn(RKA, {c["id"] for c in kept})
        self.assertEqual(new[RKA], NOW - 3600)

    def test_no_competitor_granted(self):
        for cs in ([cand(RKA, 60)], [cand(RKA, 60), cand("plain", 10)], [cand(RKA, 20), cand(CONV, 30)]):
            kept, lines, _ = rf.quiet_yield_filter(cs, ROWS, {}, NOW)
            self.assertIn(RKA, {c["id"] for c in kept})
            self.assertEqual(lines, {})

    def test_running_quiet_still_blocks_heavy(self):
        g = [{"id": RKA, "holds": sorted(rf.expand({"q1"}))}]
        kept, waits, lines = rf.quiet_gate([cand(CONV, 30, ["q0"])], ROWS, g, {q: 0.0 for q in rf.QUARTERS}, None)
        self.assertEqual(kept, [])
        self.assertIn("bandwidth-heavy row not placed beside the running quiet-host row", lines[CONV])


if __name__ == "__main__":
    unittest.main()
