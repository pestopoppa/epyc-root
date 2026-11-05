#!/usr/bin/env python3
"""COEXIST rule (operator 2026-11-05: "this way if GPU is running a timing run, we can still use spare threads on it to
run gitnexus as needed without impacting independent CPU runs on q0,q1, and q2"). plan() is pure; publish validation
runs check_coexist on fixture launchers under a temp dir. Nothing live is touched.
keeper class fix 2026-11-05: coexist is a lock-set test. A candidate's `coexist` (small non-GPU non-timing CPU row, known
threads <= COEXIST_MAX_THREADS) and `lends` (a GPU-timing gpu-q3 grant's q3 cores 72-87 + siblings) come from
contract_of; the coexist_quiet_host marker, check_coexist, is_coexist and coexist_host are gone. A whole-host
quiet-host grant never lends."""
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
         "estimate_s": est, "coexist": coexist, "lends": rf.COEXIST_Q3 if shape == "gpu-q3" else frozenset()}
    if busy is not None:
        c["busy_fraction"] = busy
    return c


class Plan(unittest.TestCase):
    def test_quiet_host_granted_while_two_coexist_rows_hold_q3(self):
        # keeper class fix: the LENDING row (gpu-q3 GPU timing) is granted over coexist rows on 72-75; a quiet-host is not
        held = cx_opt("72-73") | cx_opt("74-75")
        free = ALL_TOKENS - held - {"q3"}
        g3 = cand("g3", [rf.GPU_Q3_TOKENS], rank=40, shape="gpu-q3", lane="gpu")
        out, _, _ = rf.plan(free, [g3], 1000, coexist_held=held)
        self.assertEqual([c["id"] for c, _ in out], ["g3"])
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
        free = ALL_TOKENS - {rf.GPU}   # gpu-quiet busy until +30 min: the lending gpu-q3 row drains
        g3 = cand("g3", [rf.GPU_Q3_TOKENS], rank=40, shape="gpu-q3", lane="gpu")
        gx = cand("gx", [cx_opt("72-73")], rank=55, coexist=True, busy=0.05, est=7200)
        out, _, _ = rf.plan(free, [g3, gx], 1000, now=now, grant_ends=[now + 1800])
        self.assertEqual([c["id"] for c, _ in out], ["gx"])   # the waiting lender never holds a coexist row back
        self.assertEqual(rf.plan.rank_holds, [])
        plain = dict(gx, id="plain", coexist=False)   # ...while a non-coexist q3 row is held back for it
        out, _, _ = rf.plan(free, [g3, plain], 1000, now=now, grant_ends=[now + 1800])
        self.assertEqual(out, [])

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
    """keeper class fix 2026-11-05: check_coexist (marker / claim-geometry validation at publish) is removed; coexist is
    derived from launcher evidence and the claim geometry is enforced by what a gpu-q3 grant lends (see plan tests)."""
    def fixture(self, gq="none"):
        d = tempfile.mkdtemp()
        lp = os.path.join(d, "launch.sh")
        open(lp, "w").write(f"#!/bin/bash\nexec bash /x/filler_run15.sh --id r --class cpu --role build --gpu-quiet {gq} "
                            f"--min-window 300 --stop {d}/STOP --complete-cmd true --workdir {d} --cmd \"gitnexus analyze --workers 1\"\n")
        return {"lane": "cpu", "launcher": {"path": lp}, "regions": "any-cpu-quarter", "coexist_quiet_host": "other"}, rf.parse_launcher(lp)

    def test_valid_q3_claim_accepted(self):
        spec, o = self.fixture()
        self.assertTrue(rf.contract_of(spec, o)["coexist"])   # the marker value is ignored; --workers 1 is the evidence
        spec, o = self.fixture(gq="exclusive")
        self.assertFalse(rf.contract_of(spec, o)["coexist"])


class EvidenceCoexist(unittest.TestCase):
    """11:00Z live bug: nine unmarked -sq3 rows (busy 0.05, regions inside 72-87) sat grantable beside npd1-step5's
    ACTIVE quiet-host grant (holds gpu-quiet,q0-q3). Evidence-derived coexist admits them on q3 cores only."""
    def row(self, regions, busy=0.05, lane="cpu", threads=1):
        return {"id": "x", "lane": lane, "regions": regions, "busy_fraction": busy, "declared_threads": threads}

    def coexist(self, r):
        return rf.contract_of(r, {"class": "gpu" if r["lane"] == "gpu" else "cpu"})["coexist"]

    def test_evidence_rows_are_coexist(self):
        # keeper class fix: evidence = known threads <= COEXIST_MAX_THREADS on a non-GPU non-timing row
        self.assertTrue(self.coexist(self.row("72-73")))
        self.assertTrue(self.coexist(self.row("86-87")))
        self.assertTrue(self.coexist(self.row("any-cpu-quarter", threads=4)))

    def test_gpu_threads_busy_or_wide_rows_are_not(self):
        # 88-89 is not refused here any more: a coexist row only reaches lent tokens (72-87 + siblings) - see plan tests
        self.assertFalse(self.coexist(self.row("72-73", threads=8)))
        self.assertFalse(self.coexist(self.row("72-73", threads=None)))
        self.assertFalse(self.coexist(self.row("mi210_0,184-185", lane="gpu")))

    def test_active_quiet_host_grant_plus_two_coexist_rows_on_q3(self):
        qh = rf.expand(set(rf.REGIONS))   # npd1-step5: holds=gpu-quiet,q0,q1,q2,q3 (running)
        free = ALL_TOKENS - qh - {f"t{k}" for k in range(184, 192)} | {f"t{k}" for k in range(184, 192)}
        rows = [cand(r["id"], [cx_opt(r["regions"])], rank=55, coexist=self.coexist(r), busy=0.05)
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
    GPU_ROW = {"id": "hsf5p", "lane": "gpu", "shape": "gpu-q3", "regions": "mi210_0,88-95,184-191", "timing": "bench"}
    CPU_QH = {"id": "npd1", "lane": "gpu", "shape": "quiet-host", "regions": "mi210_0,0-95", "declared_threads": 48}
    CX = [{"id": "sq3a", "lane": "cpu", "regions": "72-73", "busy_fraction": 0.05, "declared_threads": 1},
          {"id": "sq3b", "lane": "cpu", "regions": "84-85", "busy_fraction": 0.05, "declared_threads": 1}]

    def _plan(self, host, holds):
        allrows = {r["id"]: r for r in [host] + self.CX}
        cx, qh = rf.coexist_holds([{"id": host["id"], "holds": set(holds)}], allrows)
        free = ALL_TOKENS - set(holds)
        rows = [cand(r["id"], [cx_opt(r["regions"])], rank=55, coexist=rf.contract_of(r)["coexist"], busy=0.05) for r in self.CX]
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
        # keeper class fix: only a GPU-timing gpu-q3 contract lends; the spec shape is advisory
        self.assertEqual(rf.contract_of(self.CPU_QH)["lends"], frozenset())   # npd1-step5: lane gpu but -t 48 CPU serving
        self.assertEqual(rf.contract_of({"lane": "cpu", "shape": "quiet-host", "regions": "0-95"})["lends"], frozenset())
        self.assertEqual(rf.contract_of({"lane": "cpu", "shape": "host", "regions": "0-95"})["lends"], frozenset())
        self.assertEqual(rf.contract_of(dict(self.GPU_ROW, timing=""))["lends"], frozenset())   # non-timing GPU row
        self.assertEqual(rf.contract_of(self.GPU_ROW)["lends"], rf.COEXIST_Q3)

    def test_gpu_q3_claim_never_includes_72_87(self):
        self.assertEqual(rf.gpu_q3_claim_cores("mi210_0,88-95,184-191"), set(range(88, 96)))
        self.assertTrue(rf.gpu_q3_claim_cores("mi210_0,q3,184-191") & set(range(72, 88)))
        self.assertTrue(rf.gpu_q3_claim_cores("mi210_0,168-169") & set(range(72, 88)))   # siblings fold
        self.assertFalse(rf.GPU_HOST_THREADS & set(range(168, 184)))
        self.assertFalse({f"t{k}" for k in range(184, 192)} & rf.COEXIST_Q3)
        self.assertFalse(rf.cpu_tokens("88-95") & rf.COEXIST_Q3)


if __name__ == "__main__":
    unittest.main()
