"""operator 2026-11-05 "Warn now; auto-end in rowflow2": a grant IDLE-HELD continuously for >= IDLE_WARN_AFTER_S (300 s,
< IDLE_PCT busy) sends ONE [warning] to the row owner through notify.emit (the smoke-fail path), then at most one repeat
per IDLE_WARN_REPEAT_S (900 s) per grant; a busy grant never warns; the keeper never kills, ends or changes a grant.
Origin: rock-aiter-tests-r3-20261105 held gpu-quiet at 0% for ~20 min (21:20-21:41Z) while 7 GPU rows queued and the
keeper logged IDLE-HELD every tick to nobody. Temp flags dirs only; notify's bus is never live here."""
import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402
from test_rowflow_arming_park import QUIET_OPT, Fixture  # noqa: E402

GPU_IDLE = {"q0": 50.0, "q1": 3.0, "q2": 0.0, "q3": 0.0, "gpu": {"busy": 0, "vram_pct": 0.0, "vram_gib": 0.0, "card": "card2"}}
GPU_BUSY = dict(GPU_IDLE, gpu={"busy": 97, "vram_pct": 60.0, "vram_gib": 38.0, "card": "card2"})
TICK = 120


def alerts(flags):
    p = os.path.join(flags, "rowflow-alerts.jsonl")
    return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


class IdleHeldWarn(Fixture):
    def setUp(self):
        super().setUp()
        os.environ.pop("ROWFLOW_BUS_ROOT", None)   # temp flags tree: notify._bus_send is "skipped", nothing reaches a bus
        self.t0 = time.time() - 3600

    def grant(self, rid, holds, age_s):
        p = os.path.join(self.flags, "grants", rid + ".grant")
        with open(p, "w") as f:
            f.write(f"regions=mi210_0,184-191 start=2026-11-05T21:19Z end=2026-11-05T23:48Z holds={holds}\n")
        os.utime(p, (self.t0 - age_s, self.t0 - age_s))
        return p

    def run_ticks(self, rid, holders, utils):
        """One idle_held + idle_held_notify pair per tick, TICK s apart, starting at self.t0. Returns the warned-rids per tick."""
        out = []
        for i, u in enumerate(utils):
            now = self.t0 + i * TICK
            idle = rf.idle_held(self.flags, rf.open_grants(self.flags), holders, u, self.lines.append, set(), now=now)
            out.append(rf.idle_held_notify(self.flags, idle, rf.open_grants(self.flags), self.lines.append, now=now))
        return out

    def test_idle_grant_warns_once_after_300s_and_never_before(self):
        rid = "rock-aiter-tests-r3-20261105"
        self.row(rid, 10, QUIET_OPT, "gpu", lane="gpu", regions="mi210_0,184-191")
        gp = self.grant(rid, "gpu-quiet,c88,t184", age_s=64)
        warned = self.run_ticks(rid, {"gpu-quiet": rid}, [GPU_IDLE] * 4)   # t=0,120,240,360 -> idle_since=t0
        self.assertEqual(warned, [[], [], [], [rid]], "exactly one warning, at the first tick >= 300 s idle")
        a = alerts(self.flags)
        self.assertEqual(len(a), 1)
        self.assertEqual((a[0]["kind"], a[0]["severity"], a[0]["row_id"], a[0]["row_owner"]), ("idle-held", "warning", rid, "t"))
        self.assertEqual(a[0]["detail"]["warning_n"], 1)
        self.assertGreaterEqual(a[0]["detail"]["idle_s"], rf.IDLE_WARN_AFTER_S)
        self.assertIn("gpu-quiet", a[0]["detail"]["regions"])
        self.assertTrue([l for l in self.lines if l.startswith(f"IDLE-HELD-WARN gpu-quiet {rid}:")])
        self.assertTrue(os.path.exists(gp), "the keeper never ends or changes the grant")
        self.assertTrue(os.path.exists(os.path.join(self.flags, "ws58-keeper-state", "allocator", "idle_held_warn.json")))
        # the inference mailbox got the same alert (the smoke-fail path)
        inbox = os.path.join(self.flags, "notify", "inbox", "inference.jsonl")
        self.assertTrue(os.path.exists(inbox) and json.loads(open(inbox).readline())["key"] == a[0]["key"])

    def test_busy_grant_never_warns(self):
        rid = "busy-gpu"
        self.row(rid, 10, QUIET_OPT, "gpu", lane="gpu", regions="mi210_0,184-191")
        self.grant(rid, "gpu-quiet", age_s=600)
        warned = self.run_ticks(rid, {"gpu-quiet": rid}, [GPU_BUSY] * 6)
        self.assertEqual(warned, [[]] * 6)
        self.assertEqual(alerts(self.flags), [])
        self.assertEqual(rf.load_json(rf.idle_warn_state_path(self.flags)), {})

    def test_repeat_at_most_once_per_15_min_and_dedupe_survives_restarts(self):
        rid = "idle-gpu"
        self.row(rid, 10, QUIET_OPT, "gpu", lane="gpu", regions="mi210_0,184-191")
        self.grant(rid, "gpu-quiet", age_s=600)
        n = 14                                    # t = 0 .. 1560 s
        warned = self.run_ticks(rid, {"gpu-quiet": rid}, [GPU_IDLE] * n)
        ticks = [i for i, w in enumerate(warned) if w]
        self.assertEqual(ticks, [3, 11], "first at 360 s idle, repeat at the first tick >= 900 s after it (1320 s)")
        a = alerts(self.flags)
        self.assertEqual([x["detail"]["warning_n"] for x in a], [1, 2])
        self.assertNotEqual(a[0]["key"], a[1]["key"])
        st = rf.load_json(rf.idle_warn_state_path(self.flags))
        self.assertEqual(st[rid]["warn_n"], 2)
        self.assertEqual(int(st[rid]["idle_since"]), int(self.t0))

    def test_cpu_quarter_grant_is_covered_and_a_busy_tick_resets_the_clock(self):
        rid = "cpu-q1"
        self.row(rid, 10, QUIET_OPT, "quiet-host")
        self.grant(rid, "q1", age_s=600)
        idle_q1 = dict(GPU_BUSY, q1=2.0)
        busy_q1 = dict(GPU_BUSY, q1=40.0)
        warned = self.run_ticks(rid, {"q1": rid}, [idle_q1, idle_q1, busy_q1, idle_q1, idle_q1, idle_q1, idle_q1])
        # idle at 0,120 -> busy at 240 resets -> idle again from 360: first warning at the first tick >= 660 s = tick 6 (720 s)
        self.assertEqual([i for i, w in enumerate(warned) if w], [6])
        self.assertEqual(alerts(self.flags)[0]["detail"]["regions"], "q1")

    def test_notify_failure_is_logged_and_never_raises(self):
        rid = "idle-gpu-2"
        self.row(rid, 10, QUIET_OPT, "gpu", lane="gpu", regions="mi210_0,184-191")
        self.grant(rid, "gpu-quiet", age_s=600)

        def boom(*a, **k):
            raise OSError("bus down")
        idle = [("gpu-quiet", rid, 0.0)]
        for i in range(4):
            rf.idle_held_notify(self.flags, idle, rf.open_grants(self.flags), self.lines.append, now=self.t0 + i * TICK, emit=boom)
        self.assertTrue([l for l in self.lines if "notify failed: OSError: bus down" in l])
        self.assertEqual(alerts(self.flags), [])

    def test_allocate_tick_wires_the_warning(self):
        """End to end through allocate(): a gpu-quiet grant measured 0% busy for > 300 s warns once over 4 ticks."""
        rid = "e2e-gpu"
        self.row(rid, 10, QUIET_OPT, "gpu", lane="gpu", regions="mi210_0,184-191")
        self.grant(rid, "gpu-quiet", age_s=600)
        os.utime(os.path.join(self.flags, "grants", rid + ".grant"), (time.time() - 600, time.time() - 600))
        rf.measure_util = lambda *a, **k: GPU_IDLE
        rf.underused = self.saved["underused"]
        saved_time = rf.time.time
        try:
            for i in range(4):
                now = time.time() + i * TICK
                rf.time.time = lambda now=now: now
                rf.allocate(self.flags, log=self.lines.append)
        finally:
            rf.time.time = saved_time
        self.assertEqual(len(alerts(self.flags)), 1)
        self.assertEqual(alerts(self.flags)[0]["kind"], "idle-held")
        self.assertTrue(os.path.exists(os.path.join(self.flags, "grants", rid + ".grant")))


if __name__ == "__main__":
    unittest.main()
