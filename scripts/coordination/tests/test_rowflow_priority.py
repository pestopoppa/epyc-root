"""ws58 2026-11-02 allocator priority: an operator rank < URGENT_RANK beats lane starvation, and no drain (or drain-row
promotion) is set for a row while a better-ranked row that wants the same regions is runnable.

Incident: at 21:25Z the operator had raised brf-exp09-pilot / brf-exp01-trellis-build (and two GPU smokes) to rank 1,
yet the allocator granted handoff-kvu-vkq3-mtp-bound (rank 30, whole host) for 5 h: the aged host row was promoted to
the front as a drain row, and the starved GPU lane sorted ahead of rank."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_000_000.0
QUARTER_OPTS = [frozenset({q}) for q in sorted(rf.QUARTERS)]
HOST_OPT = [frozenset(rf.QUARTERS)]
GPU_OPT = [frozenset({rf.GPU, "q3"})]   # a GPU row whose reviewed legacy engine books q3 + the MI210


def cand(rid, opts, rank, lane="cpu", lane_count=0, **kw):
    c = {"id": rid, "kind": "grant", "lane": lane, "rank": float(rank), "lane_count": lane_count, "gib": 0,
         "bench": False, "options": list(opts), "window_s": 3000}
    c.update(kw)
    return c


def ids(out):
    return [c["id"] for c, _ in out]


class UrgentBeatsStarvation(unittest.TestCase):
    def test_rank1_cpu_row_beats_starved_gpu_lane(self):
        # q3 + the MI210 free; the starved GPU lane's rank-100 row would take q3 + gpu and leave the pilot nothing
        pilot = cand("brf-exp09-pilot", QUARTER_OPTS, 1, lane_count=27)
        gpu = cand("gpu-row", GPU_OPT, 100, lane="gpu", lane_count=10)
        out, _, pend = rf.plan({"q3", rf.GPU}, [gpu, pilot], 1000, now=NOW)
        self.assertEqual(ids(out)[0], "brf-exp09-pilot")
        self.assertEqual([sorted(o) for c, o in out if c["id"] == "brf-exp09-pilot"], [["q3"]])
        self.assertIn("gpu-row", [c["id"] for c in pend])

    def test_old_order_would_have_lost(self):
        # control: with a non-urgent rank the starved lane still goes first (fairness kept for ordinary ranks)
        pilot = cand("p", QUARTER_OPTS, 20, lane_count=27)
        gpu = cand("gpu-row", GPU_OPT, 100, lane="gpu", lane_count=10)
        out, _, _ = rf.plan({"q3", rf.GPU}, [gpu, pilot], 1000, now=NOW)
        self.assertEqual(ids(out), ["gpu-row"])

    def test_equal_urgent_rank_keeps_starvation_fairness(self):
        a = cand("cpu-a", QUARTER_OPTS, 1, lane_count=27)
        b = cand("gpu-b", GPU_OPT, 1, lane="gpu", lane_count=10)
        self.assertLess(rf.plan_order(b), rf.plan_order(a))
        out, _, _ = rf.plan({"q3", rf.GPU}, [a, b], 1000, now=NOW)
        self.assertEqual(ids(out), ["gpu-b"])

    def test_urgent_rows_ordered_by_rank_then_lane(self):
        r2 = cand("r2", QUARTER_OPTS, 2, lane_count=0)
        r1 = cand("r1", QUARTER_OPTS, 1, lane_count=50)
        r9 = cand("r9", QUARTER_OPTS, 9.5, lane_count=0)
        r10 = cand("r10", QUARTER_OPTS, 10, lane_count=0)   # 10 is not urgent: back to lane-first ordering
        order = [c["id"] for c in sorted([r10, r9, r2, r1], key=rf.plan_order)]
        self.assertEqual(order, ["r1", "r2", "r9", "r10"])


class DrainYieldsToRank(unittest.TestCase):
    def test_incident_replay_host_row_not_promoted_over_rank1_pilots(self):
        host = cand("handoff-kvu-vkq3-mtp-bound", HOST_OPT, 30, shape="host", since=NOW - 7200, window_s=17580)
        exp09 = cand("brf-exp09-pilot", QUARTER_OPTS, 1)
        exp01 = cand("brf-exp01-trellis-build", QUARTER_OPTS, 1)
        out, _, pend = rf.plan(set(rf.QUARTERS) | {rf.GPU}, [host, exp09, exp01], 1000, now=NOW)
        self.assertEqual(sorted(ids(out)), ["brf-exp01-trellis-build", "brf-exp09-pilot"])
        self.assertIn("handoff-kvu-vkq3-mtp-bound", [c["id"] for c in pend])
        self.assertIsNone(rf.plan.last_drain)
        self.assertEqual([(h["id"], b["id"]) for h, b in rf.plan.drain_held],
                         [("handoff-kvu-vkq3-mtp-bound", "brf-exp01-trellis-build")])

    def test_no_drain_while_better_ranked_overlapping_row_is_grantable(self):
        # q1-q3 busy, q0 free: a drain would reserve q0-q3 for the rank-30 host row at T; a rank-20 quarter row that
        # fits q0 now wants them
        host = cand("host", HOST_OPT, 30, shape="host", since=NOW - 7200)
        better = cand("better", QUARTER_OPTS, 20)
        rf.plan({"q0"}, [host, better], 1000, now=NOW, grant_ends=[NOW + 1800])
        self.assertIsNone(rf.plan.last_drain)
        self.assertEqual([h["id"] for h, _ in rf.plan.drain_held], ["host"])
        # quiet-host rows obey the same rule
        quiet = cand("quiet", [frozenset(rf.REGIONS)], 30, shape="quiet-host")
        rf.plan({"q0"}, [quiet, better], 1000, now=NOW, grant_ends=[NOW + 1800])
        self.assertIsNone(rf.plan.last_drain)

    def test_unplaceable_better_row_does_not_hold_the_drain(self):
        # ws58 2026-11-03: nothing free -> the better-ranked row cannot be placed this tick, so it holds nothing; at T
        # (everything free) it is placeable again and wins by rank before the drain row is promoted
        host = cand("host", HOST_OPT, 30, shape="host", since=NOW - 7200)
        better = cand("better", QUARTER_OPTS, 20)
        rf.plan(set(), [host, better], 1000, now=NOW, grant_ends=[NOW + 1800])
        self.assertEqual(rf.plan.last_drain[0]["id"], "host")
        self.assertEqual(rf.plan.drain_held, [])
        out, _, _ = rf.plan(set(rf.QUARTERS), [host, better], 1000, now=NOW + 1800)
        self.assertEqual(ids(out), ["better"])

    def test_arm_failing_better_row_does_not_hold_the_drain(self):
        # the yarn-e1-a2 deadlock: a rank-7 GPU row that keeps failing to arm held every quiet-host row on an idle host
        quiet = cand("quiet", [frozenset(rf.REGIONS)], 30, shape="quiet-host")
        yarn = cand("yarn", [frozenset({rf.GPU})], 7, lane="gpu", arm_fails=1)
        out, _, _ = rf.plan(set(rf.REGIONS), [quiet, yarn], 1000, now=NOW)
        self.assertEqual(rf.plan.drain_held, [])
        self.assertEqual(ids(out), ["quiet"])
        yarn["arm_fails"] = 0   # control: a healthy better-ranked GPU row still holds it
        out, _, _ = rf.plan(set(rf.REGIONS), [quiet, yarn], 1000, now=NOW)
        self.assertEqual([(h["id"], b["id"]) for h, b in rf.plan.drain_held], [("quiet", "yarn")])
        self.assertEqual(ids(out), ["yarn"])

    def test_port_blocked_better_row_does_not_hold_the_drain(self):
        quiet = cand("quiet", [frozenset(rf.REGIONS)], 30, shape="quiet-host")
        gpu = cand("gpu", [frozenset({rf.GPU})], 7, lane="gpu", ports=[18083])
        rf.plan(set(rf.REGIONS), [quiet, gpu], 1000, now=NOW, held_ports=[18083])
        self.assertEqual(rf.plan.drain_held, [])

    def test_drain_still_set_when_better_row_wants_other_regions(self):
        host = cand("host", HOST_OPT, 30, shape="host", since=NOW - 7200)
        gpu_only = cand("gpu-only", [frozenset({rf.GPU})], 1, lane="gpu")
        rf.plan(set(), [host, gpu_only], 1000, now=NOW, grant_ends=[NOW + 1800])
        self.assertIsNotNone(rf.plan.last_drain)
        self.assertEqual(rf.plan.last_drain[0]["id"], "host")

    def test_drain_still_set_over_equal_and_worse_ranked_rows(self):
        host = cand("host", HOST_OPT, 30, shape="host", since=NOW - 7200)
        same = cand("same", QUARTER_OPTS, 30)
        worse = cand("worse", QUARTER_OPTS, 100)
        rf.plan(set(), [host, same, worse], 1000, now=NOW, grant_ends=[NOW + 1800])
        self.assertEqual(rf.plan.last_drain[0]["id"], "host")
        self.assertEqual(rf.plan.drain_held, [])

    def test_next_eligible_big_row_drains_when_first_is_held(self):
        # a held rank-30 host row does not stop a better-ranked (rank-5) host row behind it from draining
        held = cand("held", HOST_OPT, 30, shape="host", since=NOW - 7200)
        better = cand("better", [frozenset({"q0"})], 20)
        top = cand("top", HOST_OPT, 5, shape="host", since=NOW - 7200)
        rf.plan(set(), [held, better, top], 1000, now=NOW, grant_ends=[NOW + 1800])
        self.assertEqual(rf.plan.last_drain[0]["id"], "top")


class RowRank(unittest.TestCase):
    def test_explicit_zero_is_not_default(self):
        self.assertEqual(rf.row_rank({"priority_rank": 0}), 0.0)
        self.assertEqual(rf.row_rank({"priority_rank": 1}), 1.0)
        self.assertEqual(rf.row_rank({}), 100.0)
        self.assertEqual(rf.row_rank({"priority_rank": None}), 100.0)
        self.assertEqual(rf.row_rank({"priority_rank": "x"}), 100.0)


if __name__ == "__main__":
    unittest.main()
