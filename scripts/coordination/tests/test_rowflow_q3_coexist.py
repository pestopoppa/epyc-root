#!/usr/bin/env python3
"""COEXIST rule (operator 2026-11-05: "this way if GPU is running a timing run, we can still use spare threads on it to
run gitnexus as needed without impacting independent CPU runs on q0,q1, and q2"). plan() is pure; publish validation
runs check_coexist on fixture launchers under a temp dir. Nothing live is touched."""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow"))
import rowflow as rf  # noqa: E402

ALL_TOKENS = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
QH_OPT = frozenset(rf.compress(rf.expand(set(rf.REGIONS))))


def cx_opt(cpus):
    return frozenset(rf.cpu_tokens(cpus))


def cand(cid, options, rank=50, shape="quarter", coexist=False, busy=None, est=3000):
    c = {"id": cid, "kind": "grant", "lane": "cpu", "rank": rank, "lane_count": 0, "gib": 4, "bench": shape == "quiet-host",
         "options": [frozenset(o) for o in options], "shape": shape, "since": time.time(), "window_s": est,
         "estimate_s": est, "coexist": coexist}
    if busy is not None:
        c["busy_fraction"] = busy
    return c


class Plan(unittest.TestCase):
    def test_quiet_host_granted_while_two_coexist_rows_hold_q3(self):
        held = cx_opt("72-73") | cx_opt("74-75")
        free = ALL_TOKENS - held - {"q3"}
        npd = cand("npd1", [QH_OPT], rank=40, shape="quiet-host")
        out, _, _ = rf.plan(free, [npd], 1000, coexist_held=held)
        self.assertEqual([c["id"] for c, _ in out], ["npd1"])
        self.assertIsNone(rf.plan.last_drain)

    def test_coexist_granted_during_active_quiet_host_grant(self):
        qh = rf.expand(set(rf.REGIONS))
        free = ALL_TOKENS - qh - {f"t{k}" for k in range(184, 192)}
        rows = [cand("gx1", [cx_opt("72-73")], rank=55, coexist=True, busy=0.05),
                cand("gx2", [cx_opt("74-75")], rank=55, coexist=True, busy=0.05)]
        out, _, _ = rf.plan(free, rows, 1000, quiet_held=qh)
        self.assertEqual(sorted(c["id"] for c, _ in out), ["gx1", "gx2"])
        for _, o in out:
            self.assertFalse(o & {f"t{k}" for k in range(184, 192)})

    def test_coexist_never_shares_cores_with_another_coexist_row(self):
        qh = rf.expand(set(rf.REGIONS))
        held = cx_opt("72-73")
        free = ALL_TOKENS - qh - held
        out, _, _ = rf.plan(free, [cand("gx", [cx_opt("72-73")], coexist=True, busy=0.05)], 1000,
                            quiet_held=qh, coexist_held=held)
        self.assertEqual(out, [])

    def test_coexist_not_held_back_by_quiet_host_drain(self):
        now = time.time()
        free = ALL_TOKENS - rf.expand({"q0"})   # q0 busy until +2h: the quiet-host row drains
        npd = cand("npd1", [QH_OPT], rank=40, shape="quiet-host")
        gx = cand("gx", [cx_opt("72-73")], rank=55, coexist=True, busy=0.05, est=7200)
        out, _, _ = rf.plan(free, [npd, gx], 1000, now=now, grant_ends=[now + 1800])
        self.assertEqual([c["id"] for c, _ in out], ["gx"])
        self.assertEqual(rf.plan.last_drain[0]["id"], "npd1")
        self.assertEqual(rf.plan.rank_holds, [])

    def test_unmarked_q3_row_still_blocks_and_drains(self):
        now = time.time()
        held = cx_opt("72-73")   # held by a NON-coexist sub-quarter row
        free = ALL_TOKENS - held - {"q3"}
        npd = cand("npd1", [QH_OPT], rank=40, shape="quiet-host")
        out, _, _ = rf.plan(free, [npd], 1000, now=now, grant_ends=[now + 1800])
        self.assertEqual(out, [])
        self.assertEqual(rf.plan.last_drain[0]["id"], "npd1")
        # an unmarked low-busy q3 row is still held back by the drain
        gx = cand("plain", [cx_opt("74-75")], rank=55, busy=0.05, est=7200)
        out, _, _ = rf.plan(free, [npd, gx], 1000, now=now, grant_ends=[now + 1800])
        self.assertEqual(out, [])


class Publish(unittest.TestCase):
    def fixture(self, guard=True):
        d = tempfile.mkdtemp()
        if guard:
            open(os.path.join(d, "gitnexus-guard.py"), "w").write("def admit_subquarter_q3(): pass\n")
        open(os.path.join(d, "job.py"), "w").write("run(['--workers','1'])\n")
        lp = os.path.join(d, "launch.sh")
        open(lp, "w").write(f"#!/bin/bash\nexec bash /x/filler_run15.sh --id r --class cpu --role build --gpu-quiet none --min-window 300 "
                            f"--stop {d}/STOP --complete-cmd true --workdir {d} --cmd \"python3 {d}/job.py\"\n")
        return {"lane": "cpu", "launcher": lp, "busy_fraction": 0.05, "coexist_quiet_host": "gitnexus-q3"}, rf.parse_launcher(lp)

    def test_valid_q3_claim_accepted(self):
        spec, o = self.fixture()
        rf.check_coexist(spec, o, "72-73")

    def test_claim_touching_gpu_threads_refused(self):
        spec, o = self.fixture()
        for regions in ("88-89", "184-185", "72-73,186", "94-95"):
            with self.assertRaises(rf.Refused, msg=regions):
                rf.check_coexist(spec, o, regions)

    def test_claim_outside_q3_refused(self):
        spec, o = self.fixture()
        for regions in ("0-1", "48-49", "any-cpu-quarter", "q3"):
            with self.assertRaises(rf.Refused, msg=regions):
                rf.check_coexist(spec, o, regions)

    def test_busy_and_marker_refused(self):
        spec, o = self.fixture()
        with self.assertRaises(rf.Refused):
            rf.check_coexist(dict(spec, busy_fraction=0.2), o, "72-73")
        with self.assertRaises(rf.Refused):
            rf.check_coexist(dict(spec, coexist_quiet_host="other"), o, "72-73")
        spec2, o2 = self.fixture(guard=False)
        with self.assertRaises(rf.Refused):
            rf.check_coexist(spec2, o2, "72-73")


if __name__ == "__main__":
    unittest.main()
