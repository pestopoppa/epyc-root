#!/usr/bin/env python3
"""RESERVATION (operator 2026-11-24 "start the reservation scheduler now") + CLAIM QUEUE: the urgent head drains at once with T
from its own regions, a quiet head reserves host quietness against loud backfills, rank_reservation uses the better row's own
earliest start, gate-dropped / smoke-pending urgent rows stay in the plan as hold / phantom candidates, the persisted head
refuses (enforce) or only logs (shadow) a claim that would delay it, and claim requests are queued, ranked and withdrawn."""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
Q012N = frozenset({"q0", "q1", "q2"} | set(rf.Q3_NARROW))


def cand(rid, rank, opts, est=3600, **kw):
    c = {"id": rid, "kind": "grant", "lane": "cpu", "rank": float(rank), "lane_count": 0, "gib": 8, "bench": False,
         "options": [frozenset(o) for o in opts], "shape": kw.pop("shape", "quarter"), "window_s": est + 900,
         "estimate_s": est, "min_window_s": 600, "since": NOW - 60, "ports": [], "arm_fails": 0}
    c.update(kw)
    return c


def allfree():
    return set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)


class Plan(unittest.TestCase):
    def test_off_unchanged_on_reserve_false(self):
        """reserve=False: an urgent host row that waited < DRAIN_AFTER_S forms no drain (today's behaviour)."""
        free = allfree() - rf.expand({"q0"})
        head = cand("c21", 9, [Q012N], shape="host")
        low = cand("low", 40, [{q} for q in rf.QUARTERS], est=8 * 3600)
        rf.plan(free, [head, low], 900, now=NOW, grant_ends=[NOW + 3 * 3600], region_ends={t: NOW + 600 for t in rf.expand({"q0"})})
        self.assertIsNone(rf.plan.last_drain)

    def test_urgent_head_drains_at_once_T_from_own_regions(self):
        """Root causes C + D: the head is the drain at once; T = the end of q0 (its own region), not the GPU grant's 3 h."""
        free = allfree() - rf.expand({"q0"})
        ends = {t: NOW + 600 for t in rf.expand({"q0"})}
        head = cand("c21", 9, [Q012N], shape="host")
        low = cand("low", 40, [{"q1"}, {"q2"}], est=8 * 3600)
        out, _, _ = rf.plan(free, [head, low], 900, now=NOW, grant_ends=[NOW + 600, NOW + 3 * 3600], region_ends=ends, reserve=True)
        self.assertEqual(rf.plan.last_drain[0]["id"], "c21")
        self.assertAlmostEqual(rf.plan.last_drain[1], NOW + 600)
        self.assertNotIn("low", [c["id"] for c, _ in out])

    def test_short_row_backfills_head_regions(self):
        free = allfree() - rf.expand({"q0"})
        ends = {t: NOW + 3600 for t in rf.expand({"q0"})}
        head = cand("c21", 9, [Q012N], shape="host")
        short = cand("short", 40, [{"q1"}], est=600)
        out, _, _ = rf.plan(free, [head, short], 900, now=NOW, grant_ends=[NOW + 3600], region_ends=ends, reserve=True)
        self.assertIn("short", [c["id"] for c, _ in out])
        self.assertTrue(any(c["id"] == "short" for c, _e, _T, _t in rf.plan.backfills))

    def test_quiet_head_refuses_loud_backfill_anywhere(self):
        """A quiet head reserves host quietness: a loud row on q3 (disjoint) that ends after T is refused; a non-loud one is not."""
        free = allfree() - rf.expand({"q0"})
        ends = {t: NOW + 600 for t in rf.expand({"q0"})}
        head = cand("c21", 9, [{"q0", "q1"}], shape="multi-quarter(2)", quiet=True)
        loud = cand("loud", 40, [{"q3"}], est=8 * 3600, loud=True)
        calm = cand("calm", 41, [{"q2"}], est=8 * 3600)
        out, _, _ = rf.plan(free, [head, loud, calm], 900, now=NOW, grant_ends=[NOW + 600], region_ends=ends, reserve=True)
        ids = [c["id"] for c, _ in out]
        self.assertNotIn("loud", ids)
        self.assertIn("calm", ids)

    def test_hold_token_holds_from_now(self):
        """Root cause B: a gate-held head (hold token, unknown end) holds its free regions from now."""
        tok = rf.HOLD_PREFIX + "c21"
        head = cand("c21", 9, [set(Q012N) | {tok}], shape="host", quiet=True, hold="WAIT foreign busy")
        low = cand("low", 40, [{"q0"}, {"q1"}, {"q2"}], est=3600, loud=True)
        out, _, _ = rf.plan(allfree(), [head, low], 900, now=NOW, region_ends={tok: NOW + rf.RESERVE_TICK_S}, reserve=True)
        self.assertEqual([c["id"] for c, _ in out], [])
        self.assertEqual(rf.plan.last_drain[0]["id"], "c21")

    def test_rank_reservation_uses_own_earliest_start(self):
        """Root cause C on a non-head better row: T = its own regions' end (600 s), not max(all grant ends) (3 h)."""
        free = allfree() - rf.expand({"q0"})
        ends = {t: NOW + 600 for t in rf.expand({"q0"})}
        better = cand("better", 20, [{"q0", "q1"}], shape="multi-quarter(2)")
        low = cand("low", 40, [{"q1"}], est=8 * 3600)
        rf.plan.caps = []
        res, holds, skips = rf.rank_reservation(low, [better, low], free, 900, False, set(), NOW, [NOW + 600, NOW + 3 * 3600],
                                                None, region_ends=ends, reserve=True)
        self.assertIn("q1", res)
        res0, _h0, skips0 = rf.rank_reservation(low, [better, low], free, 900, False, set(), NOW, [NOW + 600, NOW + 3 * 3600], None)
        self.assertNotIn("q1", res0)   # today's behaviour: skipped on the GPU grant's end
        self.assertTrue(skips0)

    def test_reservation_start_unknown_end_holds_from_now(self):
        c = {"options": [frozenset({"q0", "c80"})]}
        free = allfree() - {"q0", "c80"}
        self.assertEqual(rf.reservation_start(c, free, NOW, {"q0": NOW + 900}), NOW + 900)
        self.assertEqual(rf.reservation_start(c, free, NOW, {}), NOW + rf.RESERVE_TICK_S)


class Claims(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="res-")
        os.makedirs(os.path.join(self.flags, "grants"))

    def head(self, T, tokens, quiet=True, ts=None):
        rf.atomic_json(os.path.join(rf.state_dir(self.flags), rf.RESERVATION_STATE),
                       {"mode": "enforce", "ts": ts or time.time(), "id": "c21", "rank": 9, "T": T,
                        "T_iso": "2026-11-24T14:25Z", "tokens": sorted(tokens), "quiet": quiet})

    def test_refusal_shape(self):
        now = time.time()
        self.head(now + 600, rf.compress(rf.expand({"q0"}) | set(rf.Q3_NARROW)))
        light = {f"c{k}" for k in range(84, 88)}
        self.assertEqual(rf.reservation_refusal(self.flags, light, now + 900, light=True, now=now), "RESERVED-FOR c21 until 2026-11-24T14:25Z")
        self.assertIsNone(rf.reservation_refusal(self.flags, light, now + 300, light=True, now=now))   # ends by T
        self.assertIsNone(rf.reservation_refusal(self.flags, {"c50"}, now + 900, light=True, now=now))   # disjoint, light
        self.assertIsNotNone(rf.reservation_refusal(self.flags, {"q2"}, now + 900, light=False, now=now))   # loud, quiet head

    def test_stale_head_ignored(self):
        now = time.time()
        self.head(now + 600, ["q0"], ts=now - rf.RESERVATION_FRESH_S - 5)
        self.assertIsNone(rf.reservation_refusal(self.flags, {"q0"}, now + 900, now=now))

    def test_shadow_logs_enforce_refuses(self):
        now = time.time()
        self.head(now + 600, ["q0"])
        with mock.patch.object(rf, "RESERVATION_MODE", "shadow"):
            rf.claim_reservation_check(self.flags, {"q0"}, 15, False, "ak", "0-23", now=now)
        log = open(os.path.join(self.flags, "ws58-calendar-keeper.log")).read()
        self.assertIn("CLAIM-SHADOW ak cpus=0-23 15 min would wait for 2026-11-24T14:25Z behind c21", log)
        with mock.patch.object(rf, "RESERVATION_MODE", "enforce"):
            with self.assertRaises(rf.Refused) as e:
                rf.claim_reservation_check(self.flags, {"q0"}, 15, False, "ak", "0-23", now=now)
        self.assertTrue(str(e.exception).startswith("RESERVED-FOR c21 until"))

    def test_request_queue_roundtrip(self):
        rid = rf.request_claim(self.flags, "pm", "84-87", 10, light=True, pid=os.getpid())
        reqs = rf.claim_requests(self.flags)
        self.assertEqual([r["id"] for r in reqs], [rid])
        c = rf.request_cand(reqs[0])
        self.assertEqual(c["kind"], "claim")
        self.assertFalse(c["loud"])
        self.assertEqual(c["options"], [frozenset({f"c{k}" for k in range(84, 88)} | {f"t{k}" for k in range(180, 184)})])
        self.assertEqual(rf.claim_queue_position(self.flags, rid)[0], 1)
        self.assertEqual(rf.withdraw_request(self.flags, rid, "pm"), ("WITHDRAWN", None))
        self.assertEqual(rf.claim_requests(self.flags), [])

    def test_request_dead_pid_pruned_and_count_options(self):
        rf.request_claim(self.flags, "pm", "16", 30, pid=2 ** 22 + 12345)
        self.assertEqual(rf.claim_requests(self.flags, prune=True), [])
        opts = rf.request_options({"cpus": "16"})
        self.assertIn(frozenset({"q0"}), opts)
        self.assertEqual(len(opts), 4)

    def test_wait_timeout(self):
        with mock.patch.object(rf, "CLAIM_POLL_S", 0.01):
            with self.assertRaises(rf.Refused) as e:
                rf.claim_wait(self.flags, "pm", "84-87", 5, light=True, wait_s=0)
        self.assertTrue(str(e.exception).startswith("QUEUED-TIMEOUT position 1 behind"))
        self.assertEqual(rf.claim_requests(self.flags), [])


class Cands(unittest.TestCase):
    def test_gate_dropped_urgent_row_comes_back_holding(self):
        flags = tempfile.mkdtemp(prefix="res-c-")
        os.makedirs(os.path.join(flags, "grants"))
        head = cand("c21", 9, [Q012N], shape="host")
        low = cand("low", 40, [{"q1"}])
        with mock.patch.object(rf, "urgent_quiet_pending", return_value=[]):
            out, ends, seen = rf.reservation_cands(flags, [head, low], [low], [], {"c21": {"requires_quiet_host": True}},
                                                   {"c21": "WAIT c21: foreign busy 31% on q3"}, now=NOW)
        h = next(c for c in out if c["id"] == "c21")
        self.assertTrue(h["quiet"] and h["hold"].startswith("WAIT c21"))
        self.assertIn(rf.HOLD_PREFIX + "c21", h["options"][0])
        self.assertEqual(ends[rf.HOLD_PREFIX + "c21"], NOW + rf.RESERVE_TICK_S)
        self.assertEqual(seen, {"c21": NOW})
        with mock.patch.object(rf, "urgent_quiet_pending", return_value=[]):   # anti-starvation bound
            out2, _, _ = rf.reservation_cands(flags, [head, low], [low], [], {"c21": {"requires_quiet_host": True}},
                                              now=NOW, hold_since={"c21": NOW - rf.RESERVE_HOLD_MAX_S - 1})
        self.assertNotIn("c21", [c["id"] for c in out2])


if __name__ == "__main__":
    unittest.main()
