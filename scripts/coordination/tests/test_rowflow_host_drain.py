#!/usr/bin/env python3
"""HOST-DRAIN (operator 2026-11-25 "Narrow drain now"): a whole-host row waiting > 30 min keeps worse-ranked rows off its
regions when they would end after its earliest start. Replays the 11-25 ak-pernuma / ak-gpu-cpuload starvation."""
import os
import sys
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
H, HG = "ak-pernuma-contam-cpu-20261124-r2", "ak-gpu-cpuload-contam-20261124-r2"
HOST = frozenset(rf.expand(set(rf.QUARTERS)))


def host(rid=H, rank=20, waited=3600, gpu=False):
    o = HOST | ({rf.GPU} if gpu else set())
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": float(rank), "shape": "host", "options": [frozenset(o)],
            "since": NOW - waited, "book_s": 1800, "window_s": 3600, "gib": 0, "ports": [], "arm_fails": 0, "lane_count": 0}


def quarter(rid, rank=28, book=3600, qs=("q1", "q2")):
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": float(rank), "shape": "quarter",
            "options": [frozenset(rf.expand({q})) for q in qs], "since": NOW, "book_s": book, "window_s": book,
            "gib": 0, "ports": [], "arm_fails": 0, "lane_count": 0}


def ends(q1q2_end, gpu_end=None):
    r = {t: q1q2_end for q in ("q1", "q2") for t in rf.expand({q})}
    if gpu_end:
        r[rf.GPU] = gpu_end
    return r


FREE_Q1Q2_BUSY = set(rf.expand({"q0", "q3"})) | {rf.GPU}


class HostDrain(unittest.TestCase):
    def test_incident_rank28_held_after_30min(self):
        kept, lines = rf.host_drain_filter([host(), quarter("r28a"), quarter("r28b")], FREE_Q1Q2_BUSY, ends(NOW + 900),
                                           [NOW + 900], now=NOW)
        self.assertEqual([c["id"] for c in kept], [H])
        self.assertRegex(lines["r28a"], rf"^HOST-DRAIN {H} rank=20 waited=60min: holding r28a \(would end \d\d:\d\dZ > H start")

    def test_not_held_before_30min(self):
        kept, lines = rf.host_drain_filter([host(waited=1700), quarter("r28a")], FREE_Q1Q2_BUSY, ends(NOW + 900), [NOW + 900], now=NOW)
        self.assertEqual(len(kept), 2); self.assertEqual(lines, {})

    def test_fits_before_start_is_granted(self):
        kept, lines = rf.host_drain_filter([host(), quarter("short", book=600)], FREE_Q1Q2_BUSY, ends(NOW + 900), [NOW + 900], now=NOW)
        self.assertIn("short", {c["id"] for c in kept}); self.assertEqual(lines, {})

    def test_better_ranked_not_held(self):
        kept, lines = rf.host_drain_filter([host(), quarter("r10", rank=10)], FREE_Q1Q2_BUSY, ends(NOW + 900), [NOW + 900], now=NOW)
        self.assertIn("r10", {c["id"] for c in kept}); self.assertEqual(lines, {})

    def test_ungrantable_head_holds_nothing(self):
        blocked = dict(host(gpu=True), options=[frozenset((HOST - {rf.GPU}) | {rf.GPU_BLOCKED})])
        kept, lines = rf.host_drain_filter([blocked, quarter("r28a")], FREE_Q1Q2_BUSY, ends(NOW + 900), [NOW + 900], now=NOW)
        self.assertEqual(lines, {})
        # an H gated out this tick (smoke pending / STOP) is not a candidate at all -> nothing held
        kept, lines = rf.host_drain_filter([quarter("r28a")], FREE_Q1Q2_BUSY, ends(NOW + 900), [NOW + 900], now=NOW)
        self.assertEqual(len(kept), 1); self.assertEqual(lines, {})

    def test_gpu_head_drains_toward_gpu_free(self):
        free = set(rf.expand({"q0", "q3"}))
        # GPU frees in 3 h: a 1 h quarter row ends before H could start -> still granted
        kept, lines = rf.host_drain_filter([host(HG, gpu=True), quarter("r28a")], free, ends(NOW + 900, NOW + 10800),
                                           [NOW + 900, NOW + 10800], now=NOW)
        self.assertIn("r28a", {c["id"] for c in kept})
        # GPU frees in 20 min: the 1 h row would overrun H's start -> held
        kept, lines = rf.host_drain_filter([host(HG, gpu=True), quarter("r28a")], free, ends(NOW + 900, NOW + 1200),
                                           [NOW + 900, NOW + 1200], now=NOW)
        self.assertNotIn("r28a", {c["id"] for c in kept}); self.assertIn("r28a", lines)

    def test_resumable_backfill_held(self):
        # 13:21Z recurrence: rank-33 iqk-q8-decode-r3 (resumable, remaining-estimate booking) took q1 until 15:10Z
        r = dict(quarter("ak-cpu-a3b-iqk-q8-decode-r3", rank=33, book=6540), resumable=True)
        kept, lines = rf.host_drain_filter([host(), r], FREE_Q1Q2_BUSY, ends(NOW + 900), [NOW + 900], now=NOW)
        self.assertNotIn(r["id"], {c["id"] for c in kept}); self.assertIn(r["id"], lines)

    def test_flag_off_restores_old(self):
        old = rf.HOST_DRAIN_ENFORCE
        rf.HOST_DRAIN_ENFORCE = False
        try:
            cs = [host(), quarter("r28a")]
            kept, lines = rf.host_drain_filter(cs, FREE_Q1Q2_BUSY, ends(NOW + 900), [NOW + 900], now=NOW)
            self.assertEqual(kept, cs); self.assertEqual(lines, {})
        finally:
            rf.HOST_DRAIN_ENFORCE = old

    def test_live_1412_quarters_end_host_places(self):
        # 14:12Z: the q1/q2 rows ended, the whole host is free; H must be placed, not another q1/q2 backfill
        free = set(HOST) | {rf.GPU}
        kept, lines = rf.host_drain_filter([quarter("r28c"), host()], free, {}, [], now=NOW)
        self.assertEqual([c["id"] for c in kept], [H])
        assigned, _i, _p = rf.plan(set(free), kept, 512.0, now=NOW)
        self.assertEqual([c["id"] for c, _ in assigned], [H])
        # q1/q2 just ended while q0/q3 run 20 more min: old plan backfills q1/q2 with rank 28; HOST-DRAIN holds it
        free = set(rf.expand({"q1", "q2"})) | {rf.GPU}
        rend = {t: NOW + 1200 for q in ("q0", "q3") for t in rf.expand({q})}
        assigned_old, _i, _p = rf.plan(set(free), [quarter("r28c"), host()], 512.0, now=NOW)
        self.assertIn("r28c", [c["id"] for c, _ in assigned_old])
        kept, lines = rf.host_drain_filter([quarter("r28c"), host()], free, rend, [NOW + 1200], now=NOW)
        self.assertNotIn("r28c", [c["id"] for c in kept]); self.assertIn("r28c", lines)
        assigned, _i, _p = rf.plan(set(free), kept, 512.0, now=NOW)
        self.assertEqual(assigned, [])
        # 20 min later q0/q3 end too: H places
        assigned, _i, _p = rf.plan(set(HOST) | {rf.GPU}, kept, 512.0, now=NOW + 1200)
        self.assertEqual([c["id"] for c, _ in assigned], [H])

if __name__ == "__main__":
    unittest.main()
