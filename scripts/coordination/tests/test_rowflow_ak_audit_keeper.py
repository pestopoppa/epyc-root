#!/usr/bin/env python3
"""AK failure audit 2026-11-23, keeper items: one unit test class per item (B1 and B3 have their own files)."""
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "rowflow"))
sys.path.insert(0, os.path.join(HERE, "..", "churn"))
import rowflow as rf  # noqa: E402
import filing  # noqa: E402


class Flags(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = self.tmp.name
        self.G = os.path.join(self.f, "grants")
        os.makedirs(self.G)
        os.makedirs(os.path.join(self.f, "ready"))
        self.logs = []
        self.addCleanup(self.tmp.cleanup)


class B2HoldOrphan(Flags):
    def setUp(self):
        super().setUp()
        rf.write_grant(self.f, "gpu-a", "mi210_0,184-191", {rf.GPU} | {f"t{k}" for k in range(184, 192)}, 7200)
        rf.atomic_json(rf.ready_path(self.f, "gpu-a"), {"id": "gpu-a", "owner": "autokernel", "workdir": "/mnt/raid0/llm/tmp/gpu-a-workdir"})
        os.makedirs(rf.dry_dir(self.f, "gpu-a"), exist_ok=True)
        with open(os.path.join(rf.dry_dir(self.f, "gpu-a"), "poller.out"), "w") as fh:   # the engine logged START: a started grant
            fh.write("START regions=mi210_0,184-191\n")
        os.utime(os.path.join(self.G, "gpu-a.grant"), (time.time() - 60, time.time() - 60))
        self.alerts = []
        for name, fn in (("own_pids", lambda *a, **k: set()), ("proc_alive", lambda p: False)):
            p = mock.patch.object(rf, name, side_effect=fn)
            p.start(); self.addCleanup(p.stop)

    def run_at(self, t, ps):
        g = [x for x in rf.open_grants(self.f) if x["id"] == "gpu-a"]
        with mock.patch.object(rf, "ps_listing", return_value=None):   # ps=None -> unanswerable (never the real host ps)
            return rf.hold_orphans(self.f, g, self.logs.append, now=t, ps=ps, emit=lambda *a, **k: self.alerts.append(a[1]))

    def test_released_after_5_min_of_absence_only(self):
        t0 = 1_800_000_000.0
        self.assertEqual(self.run_at(t0, []), [])
        self.assertEqual(self.run_at(t0 + 299, []), [])
        self.assertEqual(self.run_at(t0 + 301, []), ["gpu-a"])
        self.assertIn("rc=75", open(os.path.join(self.G, "gpu-a.ended")).read())
        self.assertIn("reason=hold-orphan", open(os.path.join(self.G, "gpu-a.ended")).read())
        self.assertTrue(os.path.exists(os.path.join(self.G, "gpu-a.grant.hold-orphan")))
        self.assertTrue(any("HOLD-ORPHAN gpu-a" in l for l in self.logs))
        self.assertEqual(self.alerts, ["hold-orphan"])

    def test_fail_closed_any_live_attribution(self):
        t0 = 1_800_000_000.0
        for ps in ([(77, 77, "S", "python3 /x/gpu-a/job.py")],                       # argv names the row id
                   [(78, 78, "S", "python3 /mnt/raid0/llm/tmp/gpu-a-workdir/job.py")],  # argv names the workdir
                   None):                                                           # ps unanswerable
            self.setUp()
            self.run_at(t0, ps)
            self.assertEqual(self.run_at(t0 + 900, ps), [], ps)
            self.assertFalse(os.path.exists(os.path.join(self.G, "gpu-a.ended")))

    def test_unstarted_grant_is_not_an_orphan(self):
        with open(os.path.join(rf.dry_dir(self.f, "gpu-a"), "poller.out"), "w") as fh:
            fh.write("armed, waiting\n")   # no START line: heal_grants' business, not an orphan
        t0 = 1_800_000_000.0
        self.run_at(t0, [])
        self.assertEqual(self.run_at(t0 + 900, []), [])

    def test_zombie_does_not_count_and_recorded_pgid_does(self):
        t0 = 1_800_000_000.0
        self.assertEqual(self.run_at(t0, [(5, 5, "Z", "gpu-a defunct")]), [])
        self.assertEqual(self.run_at(t0 + 400, [(5, 5, "Z+", "gpu-a defunct")]), ["gpu-a"])
        self.setUp()
        rf.atomic_json(rf.hold_orphan_state_path(self.f), {"gpu-a": {"pgids": [999], "dead_since": t0 - 5000}})
        self.assertEqual(self.run_at(t0, [(1000, 999, "S", "sleep 1")]), [])   # a member of a pgid it once had


class B4Gap(unittest.TestCase):
    def test_gap_rows_cap_the_grant_end(self):
        now = 1_800_000_000.0
        c = {"id": "g", "kind": "grant", "lane": "gpu", "rank": 100, "lane_count": 1, "gib": 8, "bench": False, "shape": "gpu",
             "options": [frozenset({rf.GPU} | {f"t{k}" for k in range(184, 192)})], "window_s": 7200, "estimate_s": 300,
             "min_window_s": 600, "book_s": 600}
        free = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
        assigned, _, _ = rf.plan(free, [c], 900.0, now=now, gap_rows={"g": now + 1800})
        self.assertEqual([a[0]["id"] for a in assigned], ["g"])
        self.assertEqual(rf.plan.hard_end.get("g"), now + 1800)


class B8StopRequeue(Flags):
    RID = "res-row-1"

    def setUp(self):
        super().setUp()
        d = os.path.join(self.f, "job")
        os.makedirs(d)
        self.lp = os.path.join(d, "launch.sh")
        open(self.lp, "w").write("#!/bin/bash\n")
        self.stop = os.path.join(d, "STOP")
        rf.atomic_json(rf.ready_path(self.f, self.RID), {"id": self.RID, "owner": "autokernel", "resumable": True, "stop_file": self.stop,
                       "workdir": d, "launcher": {"path": self.lp}})
        os.makedirs(os.path.dirname(rf.pass_path(self.f, self.RID)))
        rf.atomic_json(rf.pass_path(self.f, self.RID), {"launcher_sha256": rf.sha256(self.lp)})
        open(self.stop, "w").write("owner stop\n")
        with open(os.path.join(self.G, self.RID + ".ended"), "w") as fh:
            fh.write("rc=75 time=2026-11-23T10:00:00Z reason=stopped\n")

    def test_owner_stop_requeues_and_clears_stop(self):
        self.assertEqual(rf.autorequeue_decision(self.f, self.RID)[0], "requeue")
        self.assertEqual(rf.autorequeue(self.f, log=self.logs.append, emit=lambda *a, **k: None), [self.RID])
        self.assertFalse(os.path.exists(self.stop))
        self.assertFalse(os.path.exists(os.path.join(self.G, self.RID + ".ended")))

    def test_final_markers_and_keeper_stop_do_not_requeue(self):
        for marker in ("STOP-FINAL", "WITHDRAW"):
            m = os.path.join(os.path.dirname(self.stop), marker)
            open(m, "w").close()
            self.assertEqual(rf.autorequeue_decision(self.f, self.RID)[0], "stop", marker)
            os.remove(m)
        open(self.stop, "w").write('{"by": "rowflow idle-after-crash", "reason": "idle-after-crash"}\n')
        self.assertEqual(rf.autorequeue_decision(self.f, self.RID)[0], "stop")
        open(self.stop, "w").write("STOP-FINAL: done\n")
        self.assertEqual(rf.autorequeue_decision(self.f, self.RID)[0], "stop")

    def test_non_resumable_stop_is_not_requeued(self):
        d = rf.load_json(rf.ready_path(self.f, self.RID))
        d["resumable"] = False
        rf.atomic_json(rf.ready_path(self.f, self.RID), d)
        self.assertEqual(rf.autorequeue_decision(self.f, self.RID)[0], None)


class B12Ws58Cpus(unittest.TestCase):
    def test_digit_only_comma_list(self):
        for regions, want in (("mi210_0,88-95,184-191", "88-95,184-191"), ("mi210_0, 88-95 ,88-95,gpu-quiet,q3", "88-95"),
                              ("any-cpu-quarter", ""), ("0-95", "0-95"), ("q1,72-87", "72-87")):
            self.assertEqual(rf.ws58_cpu_list(regions), want)
            self.assertRegex(want, r"^$|^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$")

    def test_env_exports_both_and_scrubs_inherited_garbage(self):
        env = rf.ws58_cpus_env({"WS58_CPUS": "mi210_0,88-95", "WS58_REGIONS": "x"}, "mi210_0,88-95,184-191")
        self.assertEqual((env["WS58_CPUS"], env["WS58_REGIONS"]), ("88-95,184-191", "88-95,184-191"))
        env = rf.ws58_cpus_env({"WS58_CPUS": "mi210_0,88-95"}, "any-cpu-quarter")
        self.assertNotIn("WS58_CPUS", env)
        self.assertNotIn("WS58_REGIONS", env)

    def test_filler_claim_regex_accepts_the_export(self):
        import re
        v = rf.ws58_cpu_list("mi210_0,88-95,184-191")
        self.assertTrue(re.match(r"^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$", v))   # filler_run15.sh:93 (unedited)


class B13RotateLauncherOut(Flags):
    def test_rotates_per_attempt_and_never_clobbers(self):
        dd = rf.dry_dir(self.f, "r1")
        os.makedirs(dd)
        for i in range(3):
            open(os.path.join(dd, "launcher.out"), "w").write(f"attempt {i}\n")
            self.assertTrue(rf.rotate_launcher_out(self.f, "r1", f"A{i}").endswith(f"launcher.out.A{i}"))
            self.assertFalse(os.path.exists(os.path.join(dd, "launcher.out")))
        open(os.path.join(dd, "launcher.out"), "w").write("again\n")
        self.assertTrue(rf.rotate_launcher_out(self.f, "r1", "A0").endswith("A0-1"))
        self.assertEqual(open(os.path.join(dd, "launcher.out.A1")).read(), "attempt 1\n")
        self.assertIsNone(rf.rotate_launcher_out(self.f, "r1"))   # nothing to rotate

    def test_live_smoke_is_never_rotated(self):
        dd = rf.dry_dir(self.f, "r2")
        os.makedirs(dd)
        open(os.path.join(dd, "launcher.out"), "w").write("x\n")
        rf.atomic_json(rf.running_path(self.f, "r2"), {"pid": os.getpid()})
        self.assertIsNone(rf.rotate_launcher_out(self.f, "r2"))


class B14IdleViolationX6(Flags):
    def setUp(self):
        super().setUp()
        self.allrows = {"nxt": {"id": "nxt", "owner": "autokernel"}, "run": {"id": "run", "owner": "autokernel"},
                        "other": {"id": "other", "owner": "someone"}}
        self.cands = [{"id": "nxt", "shape": "gpu-q3"}, {"id": "other", "shape": "gpu-q3"}, {"id": "flag", "shape": "gpu-q3"}]
        self.alerts = []
        p = mock.patch.object(rf, "contract_of", side_effect=lambda d, o=None, flags=None: {"shape": "gpu-q3"})
        p.start(); self.addCleanup(p.stop)
        p = mock.patch.object(rf.notify, "_bus_send", return_value="skipped:test")
        p.start(); self.addCleanup(p.stop)

    def six(self):
        hit = []
        for _ in range(rf.IDLE_VIOLATION_ROW_TICKS):
            hit = rf.idle_violation_rows(self.f, [{"id": "nxt", "shape": "gpu-q3"}], self.allrows, self.logs.append)
        return hit

    def test_sixth_tick_logs_alerts_and_holds_until_ack(self):
        for _ in range(rf.IDLE_VIOLATION_ROW_TICKS - 1):
            self.assertEqual(rf.idle_violation_rows(self.f, [{"id": "nxt", "shape": "gpu-q3"}], self.allrows, self.logs.append), [])
        self.assertEqual(rf.idle_violation_rows(self.f, [{"id": "nxt", "shape": "gpu-q3"}], self.allrows, self.logs.append), ["nxt"])
        self.assertTrue(any("IDLE-VIOLATION-X6 nxt" in l for l in self.logs))
        rec = [json.loads(l) for l in open(os.path.join(self.f, "rowflow-alerts.jsonl"))]
        self.assertEqual(rec[0]["kind"], "idle-violation-x6")
        self.assertEqual(rec[0]["row_owner"], "autokernel")
        running = [{"id": "run", "holds": {"q3"}}]
        self.allrows["flag"] = {"id": "flag", "owner": "autokernel"}
        kept = rf.idle_violation_hold(self.f, self.cands, running, self.allrows, self.logs.append)
        self.assertIn("other", [c["id"] for c in kept])           # another owner is untouched
        self.assertNotIn("flag", [c["id"] for c in kept])         # the owner's next same-shape row is not stacked on the running one
        self.assertIn("nxt", [c["id"] for c in kept])             # the flagged row itself is not blocked
        self.assertEqual([c["id"] for c in rf.idle_violation_hold(self.f, self.cands, [], self.allrows, self.logs.append)],
                         ["nxt", "other", "flag"])                # nothing running of that shape: nothing held
        rf.notify.ack(self.f, rec[0]["key"], by="autokernel")
        self.assertEqual(len(rf.idle_violation_hold(self.f, self.cands, running, self.allrows, self.logs.append)), 3)   # acked: lifted

    def test_a_gap_resets_the_count(self):
        for _ in range(3):
            rf.idle_violation_rows(self.f, [{"id": "nxt", "shape": "gpu-q3"}], self.allrows, self.logs.append)
        rf.idle_violation_rows(self.f, [], self.allrows, self.logs.append)
        for _ in range(5):
            self.assertEqual(rf.idle_violation_rows(self.f, [{"id": "nxt", "shape": "gpu-q3"}], self.allrows, self.logs.append), [])


class ArmLauncherExit(Flags):
    def test_launcher_exit_rc_and_tail_in_fail_reason(self):
        lp = os.path.join(self.f, "launch.sh")
        open(lp, "w").write("#!/bin/bash\necho line-one\necho 'sha256sum: SOURCE.sha256: no properly formatted checksum lines' >&2\nexit 3\n")
        d = {"id": "arm-x", "owner": "autokernel", "estimate_s": 60, "gib": 1, "window_s": 600, "regions": "q0",
             "launcher": {"path": lp}, "engine": {"path": os.path.join(self.f, "engine.sh")}}
        seen = []
        with mock.patch.object(rf, "snapshot_engine", side_effect=OSError("no snap")), \
                mock.patch.object(rf, "record_arm_fail", side_effect=lambda fl, rid, dd, kind, why, log: seen.append(why) or 1):
            t0 = time.time()
            pid, msg = rf.arm_one(self.f, "arm-x", d, "q0", log=lambda m: None)
        self.assertIsNone(pid)
        self.assertLess(time.time() - t0, 20, "must not wait out the 30 s window once the launcher has exited")
        self.assertIn("launcher exited rc=3", seen[0])
        self.assertIn("no properly formatted checksum", seen[0])
        self.assertIn("launcher exited rc=3", msg)


if __name__ == "__main__":
    unittest.main()
