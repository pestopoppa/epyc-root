#!/usr/bin/env python3
"""Operator D9 2026-11-11 "Hold smokes (Recommended)": the keeper does not START a GPU-SMOKE-BATCH while a quiet-host row
is the next drain/placement candidate and could start within ~600 s; smokes still run in gaps they finish before that
row could start. Origin: 14:20Z, AutoKernel smokes took the GPU lock, the inf85 quiet-host row waited, 4 quarters idle."""
import os
import sys
import tempfile
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
QH_TOKENS = frozenset(set(rf.QUARTERS) | {rf.GPU})
ALL_FREE = set(rf.QUARTERS) | {rf.GPU}
RAM = 1000.0


def qh(rid="inf85", rank=5.0, **kw):
    c = {"id": rid, "kind": "grant", "lane": "cpu", "rank": rank, "lane_count": 0, "gib": 50, "bench": False,
         "options": [QH_TOKENS], "shape": "quiet-host", "window_s": 7200, "estimate_s": 3600, "min_window_s": 600,
         "ports": [], "arm_fails": 0}
    c.update(kw)
    return c


def hold(cands, free=ALL_FREE, batch_s=900, **kw):
    return rf.quiet_host_smoke_hold(cands, set(free), RAM, NOW, batch_s, **kw)


class SmokeHoldPure(unittest.TestCase):
    def test_quiet_host_fits_now_holds_the_batch(self):
        h = hold([qh()])
        self.assertIsNotNone(h)
        self.assertEqual(h[0]["id"], "inf85")
        self.assertEqual(h[1], NOW)

    def test_no_quiet_host_row_no_hold(self):
        self.assertIsNone(hold([qh(shape="quarter")]))
        self.assertIsNone(hold([]))

    def test_starts_within_horizon_holds(self):
        free = {rf.GPU, "q0", "q1", "q2"}
        ends = {t: NOW + 300 for t in rf.expand({"q3"})}
        h = hold([qh()], free=free, grant_ends=[NOW + 300], region_ends=ends)
        self.assertIsNotNone(h)
        self.assertEqual(h[1], NOW + 300)

    def test_short_batch_that_finishes_first_still_runs(self):
        free = {rf.GPU, "q0", "q1", "q2"}
        ends = {t: NOW + 500 for t in rf.expand({"q3"})}
        self.assertIsNone(hold([qh()], free=free, batch_s=300, grant_ends=[NOW + 500], region_ends=ends))

    def test_start_beyond_horizon_smokes_run(self):
        free = {rf.GPU, "q0", "q1", "q2"}
        ends = {t: NOW + 1800 for t in rf.expand({"q3"})}
        self.assertIsNone(hold([qh()], free=free, grant_ends=[NOW + 1800], region_ends=ends))

    def test_unknown_start_no_hold(self):
        free = {rf.GPU, "q0", "q1", "q2"}
        self.assertIsNone(hold([qh()], free=free, grant_ends=[], region_ends={}))

    def test_quiet_hours_off_or_row_blocked_no_hold(self):
        self.assertIsNone(hold([qh()], quiet_ok=False))
        self.assertIsNone(hold([qh(arm_fails=2)]))
        self.assertIsNone(hold([qh(gib=RAM)]))
        self.assertIsNone(hold([qh(ports=[8080])], held_ports={8080}))

    def test_better_placeable_row_on_its_regions_is_next_not_the_quiet_host(self):
        better = {"id": "q0row", "kind": "grant", "lane": "cpu", "rank": 1.0, "lane_count": 0, "gib": 10, "bench": False,
                  "options": [frozenset({"q0"})], "shape": "quarter", "window_s": 3600, "ports": [], "arm_fails": 0}
        self.assertIsNone(hold([qh(rank=5.0), better]))

    def test_no_queued_batch_no_hold(self):
        self.assertIsNone(hold([qh()], batch_s=0))


class SmokeHoldState(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()

    def test_batch_s_sums_markers(self):
        for rid, s in (("a", 900), ("b", None)):
            os.makedirs(rf.dry_dir(self.flags, rid), exist_ok=True)
            rf.atomic_json(os.path.join(rf.dry_dir(self.flags, rid), "GPU-SMOKE-QUEUED.json"),
                           {"id": rid, **({"smoke_s": s} if s else {})})
        self.assertEqual(rf.queued_gpu_batch_s(self.flags), 900 + rf.QUEUED_SMOKE_DEFAULT_S)

    def test_hold_lapses_after_max_and_clears(self):
        h = (qh(), NOW)
        self.assertFalse(rf.smoke_hold_lapsed(self.flags, h, now=NOW))
        self.assertFalse(rf.smoke_hold_lapsed(self.flags, h, now=NOW + rf.QH_SMOKE_HOLD_MAX_S - 1))
        self.assertTrue(rf.smoke_hold_lapsed(self.flags, h, now=NOW + rf.QH_SMOKE_HOLD_MAX_S + 1))
        self.assertFalse(rf.smoke_hold_lapsed(self.flags, None, now=NOW + 5000))
        self.assertFalse(rf.smoke_hold_lapsed(self.flags, h, now=NOW + 5000))   # a new hold restarts the clock

    def test_new_row_restarts_clock(self):
        self.assertFalse(rf.smoke_hold_lapsed(self.flags, (qh("a"), NOW), now=NOW))
        self.assertFalse(rf.smoke_hold_lapsed(self.flags, (qh("b"), NOW), now=NOW + 10 * rf.QH_SMOKE_HOLD_MAX_S))


if __name__ == "__main__":
    unittest.main()
