"""KEEPER-DRAIN-HOLDS-GPU follow-up (pipeline-mgmt 2026-11-18). Scenario from the 2026-11-18 07:11Z keeper log: a
whole-host row (v9-8-hot-stack-api-native-vision) waits on q0 while a SUB-QUARTER grant (cf3c-active-evidence) holds
only c0-c3/t96-t99 until 08:05Z; q1-q3 are free. While the drain is pending, a backfill row on a free quarter is
admitted iff its booked end is at or before the drain row's earliest start (the latest end among the blocking grants);
an unknown blocker end sets no reservation (unchanged behaviour). Token-level caller, as the live keeper is."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
M = 60.0
HELD = {"c0", "c1", "c2", "c3", "t96", "t97", "t98", "t99"}   # cf3c-active-evidence: 8 cores of q0
T_BLOCK = NOW + 50 * M                                       # its grant end (08:05Z in the log)


def free_tokens():
    return (rf.expand(set(rf.QUARTERS)) - HELD) | {"q1", "q2", "q3"}


def host_row():
    return {"id": "v9-8-host", "kind": "grant", "lane": "cpu", "rank": 40, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset(rf.QUARTERS)], "shape": "host", "since": NOW - 2 * 3600, "estimate_s": 3600,
            "window_s": 3600}


def backfill(rid, book, min_window=0):
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": 60, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset({"q2"})], "shape": "quarter", "since": NOW, "book_s": book, "window_s": book,
            "estimate_s": book, "min_window_s": min_window}


def ids(assigned):
    return {c["id"] for c, _ in assigned}


class DrainPartialHoldBackfill(unittest.TestCase):
    def run_plan(self, rows, region_ends, grant_ends):
        return rf.plan(free_tokens(), rows, 1000, now=NOW, grant_ends=grant_ends, region_ends=region_ends)

    def test_a_backfill_ending_before_the_blocker_is_admitted(self):
        a, _, _ = self.run_plan([host_row(), backfill("q2-30m", 30 * M)], {t: T_BLOCK for t in HELD}, [T_BLOCK])
        self.assertEqual(ids(a), {"q2-30m"})
        self.assertEqual(rf.plan.last_drain[0]["id"], "v9-8-host")
        self.assertAlmostEqual(rf.plan.last_drain[1], T_BLOCK)
        self.assertNotIn("q2-30m", rf.plan.hard_end)   # ends before T: no cap needed, drain row not delayed

    def test_b_backfill_ending_after_the_blocker_is_refused(self):
        """2 h booking, 2 h min window: the cap at T (50 min) would starve it, so it waits; the drain target keeps T."""
        a, idle, _ = self.run_plan([host_row(), backfill("q2-2h", 2 * 3600, min_window=2 * 3600)],
                                   {t: T_BLOCK for t in HELD}, [T_BLOCK])
        self.assertEqual(ids(a), set())
        self.assertAlmostEqual(rf.plan.last_drain[1], T_BLOCK)
        self.assertIn("draining for host v9-8-host", idle["q2"])

    def test_c_unknown_blocker_end_sets_no_reservation(self):
        """No known end for the q0 hold and no running grant end: earliest start unknown -> no drain reservation
        (plan.no_reserve), i.e. the pre-existing behaviour: the drain row holds nothing back."""
        a, _, _ = self.run_plan([host_row(), backfill("q2-2h", 2 * 3600, min_window=2 * 3600)], {}, [])
        self.assertIsNone(rf.plan.last_drain)
        self.assertEqual([c["id"] for c, _ in rf.plan.no_reserve], ["v9-8-host"])
        self.assertEqual(ids(a), {"q2-2h"})


if __name__ == "__main__":
    unittest.main()
