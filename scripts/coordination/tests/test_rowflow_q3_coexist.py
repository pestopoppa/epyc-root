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


def cand(cid, options, rank=50, shape="quarter", coexist=False, busy=None, est=3000, lane="cpu"):
    c = {"id": cid, "kind": "grant", "lane": lane, "rank": rank, "lane_count": 0, "gib": 4, "bench": shape == "quiet-host",
         "options": [frozenset(o) for o in options], "shape": shape, "since": time.time(), "window_s": est,
         "estimate_s": est, "coexist": coexist, "coexist_host": shape == "gpu-q3" or (shape == "quiet-host" and lane == "gpu")}
    if busy is not None:
        c["busy_fraction"] = busy
    return c


class Plan(unittest.TestCase):
    def test_quiet_host_granted_while_two_coexist_rows_hold_q3(self):
        held = cx_opt("72-73") | cx_opt("74-75")
        free = ALL_TOKENS - held - {"q3"}
        npd = cand("npd1", [QH_OPT], rank=40, shape="quiet-host", lane="gpu")
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
        npd = cand("npd1", [QH_OPT], rank=40, shape="quiet-host", lane="gpu")
        gx = cand("gx", [cx_opt("72-73")], rank=55, coexist=True, busy=0.05, est=7200)
        out, _, _ = rf.plan(free, [npd, gx], 1000, now=now, grant_ends=[now + 1800])
        self.assertEqual([c["id"] for c, _ in out], ["gx"])
        self.assertEqual(rf.plan.last_drain[0]["id"], "npd1")
        self.assertEqual(rf.plan.rank_holds, [])

    def test_unmarked_q3_row_still_blocks_and_drains(self):
        now = time.time()
        held = cx_opt("72-73")   # held by a NON-coexist sub-quarter row
        free = ALL_TOKENS - held - {"q3"}
        npd = cand("npd1", [QH_OPT], rank=40, shape="quiet-host", lane="gpu")
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


class EvidenceCoexist(unittest.TestCase):
    """11:00Z live bug: nine unmarked -sq3 rows (busy 0.05, regions inside 72-87) sat grantable beside npd1-step5's
    ACTIVE quiet-host grant (holds gpu-quiet,q0-q3). Evidence-derived coexist admits them on q3 cores only."""
    def row(self, regions, busy=0.05, lane="cpu"):
        return {"id": "x", "lane": lane, "regions": regions, "busy_fraction": busy}

    def test_evidence_rows_are_coexist(self):
        self.assertTrue(rf.is_coexist(self.row("72-73")))
        self.assertTrue(rf.is_coexist(self.row("86-87")))

    def test_gpu_threads_busy_or_wide_rows_are_not(self):
        self.assertFalse(rf.is_coexist(self.row("88-89")))      # pins 184-185
        self.assertFalse(rf.is_coexist(self.row("72-73", busy=0.5)))
        self.assertFalse(rf.is_coexist(self.row("72-73", busy=None)))
        self.assertFalse(rf.is_coexist(self.row("any-cpu-quarter")))
        self.assertFalse(rf.is_coexist(self.row("0-1")))

    def test_active_quiet_host_grant_plus_two_coexist_rows_on_q3(self):
        qh = rf.expand(set(rf.REGIONS))   # npd1-step5: holds=gpu-quiet,q0,q1,q2,q3 (running)
        free = ALL_TOKENS - qh - {f"t{k}" for k in range(184, 192)} | {f"t{k}" for k in range(184, 192)}
        rows = [cand(r["id"], [cx_opt(r["regions"])], rank=55, coexist=rf.is_coexist(r), busy=0.05)
                for r in (dict(self.row("72-73"), id="sq3a"), dict(self.row("84-85"), id="sq3b"))]
        out, _, _ = rf.plan(free, rows, 1000, quiet_held=qh)
        self.assertEqual(sorted(c["id"] for c, _ in out), ["sq3a", "sq3b"])
        gpu_thr = {f"t{k}" for k in range(184, 192)}
        for _, o in out:
            self.assertFalse(o & gpu_thr)
            self.assertFalse(o & (rf.expand({"q0", "q1", "q2"}) | {"gpu-quiet"}))

    def test_gpu_q3_hold_also_admits_coexist(self):
        qh = rf.expand({"q3", "gpu-quiet"}) | {f"t{k}" for k in range(184, 192)}
        free = ALL_TOKENS - qh
        out, _, _ = rf.plan(free, [cand("sq3", [cx_opt("74-75")], coexist=True, busy=0.05)], 1000, quiet_held=qh)
        self.assertEqual([c["id"] for c, _ in out], ["sq3"])


GPU_THR = {f"t{k}" for k in range(184, 192)}


class Coexist2(unittest.TestCase):
    """coexist2 (2026-11-05): coexist only beside GPU-timing holds; a whole-host CPU quiet-host grant keeps q3."""
    GPU_ROW = {"id": "hsf5p", "lane": "gpu", "shape": "gpu-q3", "regions": "mi210_0,88-95,184-191"}
    CPU_QH = {"id": "npd1", "lane": "gpu", "shape": "quiet-host", "regions": "mi210_0,0-95", "declared_threads": 48}
    CX = [{"id": "sq3a", "lane": "cpu", "regions": "72-73", "busy_fraction": 0.05},
          {"id": "sq3b", "lane": "cpu", "regions": "84-85", "busy_fraction": 0.05}]

    def _plan(self, host, holds):
        allrows = {r["id"]: r for r in [host] + self.CX}
        cx, qh = rf.coexist_holds([{"id": host["id"], "holds": set(holds)}], allrows)
        free = ALL_TOKENS - set(holds)
        rows = [cand(r["id"], [cx_opt(r["regions"])], rank=55, coexist=rf.is_coexist(r), busy=0.05) for r in self.CX]
        return rf.plan(free, rows, 1000, coexist_held=cx, quiet_held=qh)[0]

    def test_coexist_beside_gpu_q3_grant_and_locks_succeed(self):
        holds = rf.expand(set(rf.GPU_Q3_TOKENS))
        out = self._plan(self.GPU_ROW, holds)
        self.assertEqual(sorted(c["id"] for c, _ in out), ["sq3a", "sq3b"])
        for _, o in out:
            self.assertFalse(o & GPU_THR)
            self.assertFalse(o & rf.cpu_tokens("88-95"))
        # simulate the region-lock tree: GPU row = SH GLOBAL.q3 + EX cores 88-95 (+ gpu-quiet EX); coexist rows = SH
        # GLOBAL.q3 + SH build.q3 + EX per core. Every coexist lock must be grantable while the GPU row holds its locks.
        held = {("GLOBAL.q3", "SH"), ("bench.q3", "SH"), ("gpu-quiet", "EX")} | {(f"core.{c}", "EX") for c in rf.gpu_q3_claim_cores(self.GPU_ROW["regions"])}
        for r in self.CX:
            a, _, b = r["regions"].partition("-")
            want = {("GLOBAL.q3", "SH"), ("build.q3", "SH")} | {(f"core.{c}", "EX") for c in range(int(a), int(b or a) + 1)}
            for lk, mode in want:
                clash = [m for (l2, m) in held if l2 == lk and "EX" in (m, mode)]
                self.assertFalse(clash, f"{r['id']} blocks on {lk} {mode}")
            held |= want

    def test_coexist_not_beside_whole_host_cpu_quiet_host(self):
        holds = rf.expand(set(rf.REGIONS))
        self.assertEqual(self._plan(self.CPU_QH, holds), [])
        self.assertFalse(rf.coexist_host(self.CPU_QH))   # npd1-step5: lane gpu but -t 48 CPU serving
        self.assertFalse(rf.coexist_host({"lane": "cpu", "shape": "quiet-host"}))
        self.assertFalse(rf.coexist_host({"lane": "cpu", "shape": "host"}))
        self.assertTrue(rf.coexist_host({"lane": "gpu", "shape": "quiet-host", "declared_threads": 1}))
        self.assertTrue(rf.coexist_host(self.GPU_ROW))

    def test_gpu_q3_claim_never_includes_72_87(self):
        self.assertEqual(rf.gpu_q3_claim_cores("mi210_0,88-95,184-191"), set(range(88, 96)))
        self.assertTrue(rf.gpu_q3_claim_cores("mi210_0,q3,184-191") & set(range(72, 88)))
        self.assertTrue(rf.gpu_q3_claim_cores("mi210_0,168-169") & set(range(72, 88)))   # siblings fold
        self.assertFalse(rf.GPU_HOST_THREADS & set(range(168, 184)))
        self.assertFalse({f"t{k}" for k in range(184, 192)} & rf.COEXIST_Q3)
        self.assertFalse(rf.cpu_tokens("88-95") & rf.COEXIST_Q3)


if __name__ == "__main__":
    unittest.main()
