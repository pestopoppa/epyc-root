#!/usr/bin/env python3
"""Q3-POCKET BUILD (AK 2026-11-21): `claim --build --cpus 72-87` books cores 72-87 + siblings 168-183 only - never 88-95 /
184-191 / gpu-quiet - and coexists with GPU grants (incl. timing ones, as subquarter q3 rows do under gpu-q3 NARROW)."""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

ALL = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
GPU_HOLD = set(rf.GPU_Q3_TOKENS)
HOST = {f"c{n}" for n in range(88, 96)} | {f"t{n}" for n in range(184, 192)} | {rf.GPU}
GPUG = {"id": "gpu-timing-1", "regions": "mi210_0,88-95,184-191", "pid": None, "dryrun": False, "started": True, "path": "x",
        "holds": set(GPU_HOLD)}


def free_of(grants, extra_busy=()):
    busy = set()
    for g in grants:
        busy |= rf.expand(set(g["holds"]))
    busy |= set(extra_busy)
    busy |= {q for q in rf.QUARTERS if rf.expand({q}) & busy}
    return ALL - busy


class Q3PocketBuild(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="q3b-")
        os.makedirs(os.path.join(self.flags, "grants"))

    def claim(self, cpus, grants, free=None, bench_ids=()):
        free = free_of(grants) if free is None else free
        with mock.patch.object(rf, "contract_of", side_effect=lambda d, flags=None: {"bench": d["id"] in bench_ids}):
            return rf.claim_build(self.flags, "akagg", cpus, 30, log=lambda m: None, grants=grants,
                                  allrows={g["id"]: {"id": g["id"]} for g in grants}, free=free)

    def held(self, gid):
        return [x for x in rf.open_grants(self.flags) if x["id"] == gid][0]["holds"]

    def test_explicit_pocket_never_holds_host_threads(self):
        gid, line = self.claim("72-87", [GPUG], bench_ids={GPUG["id"]})   # beside a live GPU TIMING grant
        h = self.held(gid)
        self.assertEqual(h, {f"c{n}" for n in range(72, 88)} | {f"t{n}" for n in range(168, 184)})
        self.assertFalse(h & HOST); self.assertNotIn("q3", h); self.assertNotIn(rf.GPU, h)
        self.assertNotIn("88", line)

    def test_gpu_row_grantable_while_pocket_build_live(self):
        gid, _ = self.claim("72-87", [])
        build = {"id": gid, "holds": self.held(gid), "regions": "x"}
        free = free_of([build])
        self.assertTrue(rf.GPU_Q3_TOKENS <= free | {"q3"} and not (rf.GPU_Q3_TOKENS & rf.expand(build["holds"])))
        c = {"id": "gpu1", "kind": "grant", "lane": "gpu", "rank": 50, "lane_count": 0, "gib": 4, "bench": True,
             "options": [frozenset(rf.GPU_Q3_TOKENS)], "shape": "gpu-q3", "since": time.time(), "window_s": 3000, "estimate_s": 3000}
        out, _, _ = rf.plan(free, [c], 1000)
        self.assertEqual([x["id"] for x, _ in out], ["gpu1"])

    def test_count_claim_falls_to_pocket_when_q0_q2_full_never_88_95(self):
        full = [{"id": f"h{q}", "holds": {q}, "regions": q} for q in ("q0", "q1", "q2")]
        gid, _ = self.claim("12", full + [GPUG])
        h = self.held(gid)
        cores = {t for t in h if t.startswith("c")}
        self.assertEqual(len(cores), 12)
        self.assertTrue(h <= rf.COEXIST_Q3 and not h & HOST)

    def test_count_prefers_q0_q2_over_pocket(self):
        gid, line = self.claim("12", [GPUG])
        self.assertIn("q0", line)

    def test_count_over_pocket_width_refused_when_q0_q2_full(self):
        full = [{"id": f"h{q}", "holds": {q}, "regions": q} for q in ("q0", "q1", "q2")]
        with self.assertRaises(rf.Refused):
            self.claim("20", full + [GPUG])

    def test_explicit_host_threads_refused(self):
        for c in ("88-95", "184-191", "72-95", "80-95", "168-191"):
            with self.assertRaises(rf.Refused, msg=c) as e:
                self.claim(c, [])
            self.assertIn("88-95", str(e.exception).replace("88-95 / 184-191", "88-95"))
        self.assertEqual([f for f in os.listdir(os.path.join(self.flags, "grants")) if f.endswith(".grant")], [])

    def test_pocket_held_by_other_cpu_row_refused(self):
        other = {"id": "r", "holds": {f"c{n}" for n in range(80, 88)} | {f"t{n}" for n in range(176, 184)}, "regions": "80-87"}
        with self.assertRaises(rf.Refused):
            self.claim("72-87", [other, GPUG])

    def test_whole_q3_free_still_never_booked_whole(self):
        gid, _ = self.claim("72-87", [])
        self.assertNotIn("q3", self.held(gid))
        self.assertFalse(self.held(gid) & HOST)


if __name__ == "__main__":
    unittest.main()
