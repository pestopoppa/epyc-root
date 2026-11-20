"""BUILD-POCKET (pipeline-mgmt 2026-11-20): filler-ak-q38fn-draftfa-window-cpu-20261119 (multi-quarter(3), 28000 s) held
q0-q2 for ~7.8 h and a short build claim found no pocket. A long undeclared q0-q2 row is not booked while a build claim
waits, and a resumable one is granted with a hard end so the pocket reopens; thresholds come from policy data."""
import json, time
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
Q012 = [{"q0", "q1", "q2"}]


def cand(rid, est=28000, resumable=False, whole=False, options=Q012, rank=40, shape="multi-quarter(3)"):
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": rank, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset(o) for o in options], "shape": shape, "since": NOW, "window_s": est + 3600,
            "estimate_s": est, "min_window_s": 1800, "resumable": resumable, "whole_host_need": whole}


FREE = {"q0", "q1", "q2", "q3"}
POL = {"long_hold_s": 7200, "max_hold_s": 7200, "waiter_ttl_s": 7200}


def run(cands, waiting, pol=POL):
    return rf.plan(set(FREE), cands, 900, now=NOW, build_waiting=waiting, build_policy=pol)


class BuildPocket(unittest.TestCase):
    def test_long_row_held_while_build_waits(self):
        out, _, _ = run([cand("long")], True)
        self.assertEqual(out, [])
        self.assertEqual(rf.plan.build_held, ["long"])

    def test_long_row_placed_when_no_waiter(self):
        out, _, _ = run([cand("long")], False)
        self.assertEqual([c["id"] for c, _ in out], ["long"])
        self.assertNotIn("long", rf.plan.hard_end)   # not resumable: never cut

    def test_resumable_long_row_gets_hard_end(self):
        run([cand("long", resumable=True)], False)
        self.assertEqual(rf.plan.hard_end["long"], NOW + 7200)

    def test_whole_host_need_opts_out(self):
        out, _, _ = run([cand("long", resumable=True, whole=True)], True)
        self.assertEqual([c["id"] for c, _ in out], ["long"])
        self.assertNotIn("long", rf.plan.hard_end)

    def test_short_row_unaffected(self):
        out, _, _ = run([cand("short", est=3600)], True)
        self.assertEqual([c["id"] for c, _ in out], ["short"])

    def test_threshold_comes_from_policy(self):
        out, _, _ = run([cand("long")], True, dict(POL, long_hold_s=10 ** 6))
        self.assertEqual([c["id"] for c, _ in out], ["long"])

    def test_quarter_row_unaffected(self):
        out, _, _ = run([cand("q", est=30000, options=[{"q1"}], shape="quarter")], True)
        self.assertEqual([c["id"] for c, _ in out], ["q"])

    def test_policy_file_loads_and_override(self):
        with tempfile.TemporaryDirectory() as fl:
            self.assertEqual(rf.build_pocket_policy(fl)["long_hold_s"], 7200)
            json.dump({"build_pocket": {"long_hold_s": 99}}, open(os.path.join(fl, "allocator.json"), "w"))
            self.assertEqual(rf.build_pocket_policy(fl)["long_hold_s"], 99)

    def test_waiters_from_record_and_ticket(self):
        with tempfile.TemporaryDirectory() as fl, tempfile.TemporaryDirectory() as qd:
            json.dump({"build_pocket": {"queue_dir": qd}}, open(os.path.join(fl, "allocator.json"), "w"))
            self.assertEqual(rf.build_waiters(fl, now=NOW), [])
            rf.record_build_wait(fl, "dtree", now=NOW - 60)
            self.assertEqual(json.load(open(os.path.join(fl, "build-wait", "dtree.json")))["pid"], os.getppid())
            self.assertEqual([w["src"] for w in rf.build_waiters(fl, now=NOW)], ["build-wait"])
            self.assertEqual(rf.build_waiters(fl, now=NOW + 8000), [])   # TTL
            self.assertEqual(rf.build_waiters(fl, now=NOW + 1900), [])   # 30-min cap, well inside waiter_ttl_s
            json.dump({"pid": os.getpid(), "regions": ["q0"], "tag": "dtree-q8mf-build", "created_at": NOW - 10},
                      open(os.path.join(qd, "t1.json"), "w"))
            json.dump({"pid": os.getpid(), "regions": ["q3"], "tag": "x", "created_at": NOW - 10}, open(os.path.join(qd, "t2.json"), "w"))
            json.dump({"pid": os.getpid(), "regions": ["q1"], "tag": "rowid", "created_at": NOW - 10}, open(os.path.join(qd, "t3.json"), "w"))
            ws = rf.build_waiters(fl, now=NOW, rowids={"rowid"})
            self.assertEqual(sorted(w["src"] for w in ws), ["build-wait", "ticket"])

    def test_stale_records_ignored_and_logged(self):
        import subprocess
        dead = subprocess.Popen(["true"]); dead.wait()
        zomb = subprocess.Popen(["true"]); time.sleep(0.3)   # exited, not reaped: a zombie
        with tempfile.TemporaryDirectory() as fl, tempfile.TemporaryDirectory() as qd:
            json.dump({"build_pocket": {"queue_dir": qd}}, open(os.path.join(fl, "allocator.json"), "w"))
            d = os.path.join(fl, "build-wait"); os.makedirs(d)
            for name, pid in (("nullpid", None), ("deadpid", dead.pid), ("zombie", zomb.pid), ("alive", os.getpid())):
                json.dump({"owner": name, "pid": pid, "at_epoch": NOW - 60}, open(os.path.join(d, name + ".json"), "w"))
            logs = []
            ws = rf.build_waiters(fl, now=NOW, log=logs.append)
            zomb.wait()
            self.assertEqual([w["who"] for w in ws], ["alive"])
            self.assertEqual(sorted(l.split()[1].rstrip(":") for l in logs), ["deadpid", "nullpid", "zombie"])
            self.assertTrue(all(l.startswith("BUILD-WAIT-STALE") for l in logs))
            self.assertEqual(len(os.listdir(d)), 4)   # never deleted

    def test_explicit_wait_pid(self):
        with tempfile.TemporaryDirectory() as fl:
            rf.record_build_wait(fl, "o", now=NOW, pid=4242)
            self.assertEqual(json.load(open(os.path.join(fl, "build-wait", "o.json")))["pid"], 4242)


if __name__ == "__main__":
    unittest.main()
