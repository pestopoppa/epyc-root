"""Keeper audit 2026-11-10 fix 2: a backfill passes a drain target T by its ESTIMATE + margin, not its booked window,
and its grant end is capped at T so the engine's hard-end kill frees the drain row's regions at T even on an overrun.
Origin: 04:33-06:38Z 2026-11-10 the MI210 idled because race-eqv-gpu-r3 (window 21600 s) could not pass a drain; it ran
7 minutes."""
import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0   # a whole minute
H = 3600.0


def cand(rid, options, rank=50, shape="quarter", since=NOW, est=600, window=21600, minwin=300):
    return {"id": rid, "kind": "grant", "lane": "gpu", "rank": rank, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset(o) for o in options], "shape": shape, "since": since, "window_s": window,
            "estimate_s": est, "min_window_s": minwin}


def wide():
    return cand("drain-host", [set(rf.QUARTERS) | {rf.GPU}], rank=40, shape="quiet-host", since=NOW - 4 * H, est=H, window=2 * H)


def ends(t):
    return {r: t for r in rf.expand({"q0", "q1"})}


FREE = {"q2", "q3", rf.GPU}
T = NOW + 2 * H


class DrainByEstimate(unittest.TestCase):
    def run_plan(self, rows):
        return rf.plan(FREE, rows, 1000, now=NOW, grant_ends=[T], region_ends=ends(T))

    def test_short_estimate_long_window_is_admitted_and_capped_at_T(self):
        a, _, _ = self.run_plan([wide(), cand("race-eqv-gpu-r3", [{rf.GPU}])])
        self.assertEqual({c["id"] for c, _ in a}, {"race-eqv-gpu-r3"})
        self.assertEqual(rf.plan.last_drain[1], T)
        self.assertEqual(rf.plan.hard_end, {"race-eqv-gpu-r3": T})

    def test_book_s_past_T_waits(self):
        # audit 2026-11-10 #3: book_s = 0.75 * 2.8 h = 2.1 h > 2 h to T (1.8 h now books 1.35 h and is admitted, capped)
        a, _, _ = self.run_plan([wide(), cand("long", [{rf.GPU}], est=2.8 * H)])
        self.assertEqual(a, [])
        a, _, _ = self.run_plan([wide(), cand("was-long", [{rf.GPU}], est=1.8 * H)])
        self.assertEqual({c["id"] for c, _ in a}, {"was-long"})
        self.assertEqual(rf.plan.hard_end, {"was-long": T})

    def test_margin_has_a_floor(self):
        # est 1h30m + 22.5m <= T; est 60 s + the 300 s floor > 300 s to T
        a, _, _ = self.run_plan([wide(), cand("ok", [{rf.GPU}], est=1.5 * H)])
        self.assertEqual({c["id"] for c, _ in a}, {"ok"})
        a, _, _ = rf.plan(FREE, [wide(), cand("tight", [{rf.GPU}], est=60)], 1000, now=NOW, grant_ends=[NOW + 300],
                          region_ends=ends(NOW + 300))
        self.assertEqual(a, [])   # 60 s + 300 s floor > 300 s to T

    def test_cap_below_min_window_falls_back_to_window_rule(self):
        a, _, _ = self.run_plan([wide(), cand("minwin", [{rf.GPU}], est=600, minwin=2 * H)])
        self.assertEqual(a, [])

    def test_row_whose_window_ends_by_T_is_not_capped(self):
        a, _, _ = self.run_plan([wide(), cand("fits", [{rf.GPU}], est=600, window=H)])
        self.assertEqual({c["id"] for c, _ in a}, {"fits"})
        self.assertEqual(rf.plan.hard_end, {})

    def test_row_off_the_drain_regions_is_never_capped(self):
        wide_q = cand("drain-q", [{"q0", "q1", "q2"}], rank=40, shape="multi-quarter(3)", since=NOW - 4 * H, est=H)
        a, _, _ = self.run_plan([wide_q, cand("gpu-long", [{rf.GPU}], est=600)])
        self.assertEqual({c["id"] for c, _ in a}, {"gpu-long"})
        self.assertEqual(rf.plan.hard_end, {})


class OverrunSafety(unittest.TestCase):
    """The overrunner's grant end is at or before T, so the engine kills it (reason=hard-end) by T and the next tick
    sees the drain row's regions free and places the drain row first."""

    def test_capped_window_and_grant_end_never_pass_T(self):
        for off in (0, 17, 59, 61, 3599):
            now = NOW + off
            Tc = now + 2 * H + 37
            w = rf.capped_window(21600, Tc, now=now)
            end = rf.grant_start(now).timestamp() + w
            self.assertLessEqual(end, Tc)
            self.assertGreater(w, 0)
            self.assertEqual(rf.capped_window(21600, None, now=now), 21600)

    def test_write_grant_end_is_capped(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "grants"))
            Tc = dt.datetime.now(dt.timezone.utc).timestamp() + 2 * H + 30
            line = rf.write_grant(d, "r", "mi210_0,184-191", {rf.GPU}, 21600, end_cap=Tc)
            end = dt.datetime.strptime(dict(x.split("=", 1) for x in line.split())["end"], "%Y-%m-%dT%H:%MZ")
            self.assertLessEqual(end.replace(tzinfo=dt.timezone.utc).timestamp(), Tc)

    def test_overrunner_killed_at_T_then_drain_row_starts(self):
        a, _, _ = rf.plan(FREE, [wide(), cand("over", [{rf.GPU}])], 1000, now=NOW, grant_ends=[T], region_ends=ends(T))
        self.assertEqual(rf.plan.hard_end["over"], T)
        # at T: q0/q1's grants ended; the overrunner (estimate 600 s, still running) hit its capped end and was killed
        # by the engine's hard-end, so the GPU is free too. The drain row is placed first.
        a, _, _ = rf.plan(FREE | {"q0", "q1"}, [wide(), cand("other", [{rf.GPU}])], 1000, now=T, grant_ends=[],
                          drain_prev={"drain-host": T}, region_ends={})
        self.assertEqual([c["id"] for c, _ in a], ["drain-host"])

    def test_engine_kills_at_grant_end(self):
        src = open(os.path.join(os.path.dirname(rf.__file__), "filler_run15.sh")).read()
        self.assertIn('-ge "$e" ]; then reason=hard-end; kill_job', src)


class RankHoldByEstimate(unittest.TestCase):
    def test_lower_row_takes_held_regions_by_estimate_and_is_capped(self):
        better = cand("better", [{"q0", "q2"}], rank=10, shape="multi-quarter(2)", window=H)
        lower = cand("lower", [{"q2"}], rank=60, est=600)
        a, _, _ = rf.plan({"q2", "q3"}, [better, lower], 1000, now=NOW, grant_ends=[NOW + H])
        self.assertEqual({c["id"] for c, _ in a}, {"lower"})
        self.assertEqual(rf.plan.hard_end.get("lower"), NOW + H)


if __name__ == "__main__":
    unittest.main()
