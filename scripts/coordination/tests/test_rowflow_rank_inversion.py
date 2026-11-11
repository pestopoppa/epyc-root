"""ws58 2026-11-04 rank inversion: a strictly better-ranked row that is blocked only by busy regions that free soon
reserves the regions it needs; a lower-ranked row may take them only when it ends before they free. A better row
blocked by its OWN constraint (arm failures, held port, RAM) reserves nothing, and the plan names that constraint.

Incident (11:57-11:59Z): m4-gpu-aa-noise (rank 1, 300 s) books gpu-quiet + q3 (its engine snapshot predates GRANT_CPUS,
so its launcher's --claim-cpus 72-95 folds to q3); q3 was held by p12-h2h-np16 (0-95, ends 12:15Z). The keeper logged
`IDLE-WHY gpu-quiet: grant m4-gpu-aa-noise-20261104 needs gpu-quiet,q3: q3 busy` and then granted the idle GPU to
codex-ni-yarn-e1-mem-chain-r2 (rank 80, 4800 s, gpu-quiet + t184-191) until 13:57Z."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_000_000.0
THREADS = {f"t{k}" for k in range(184, 192)}
NOISE_OPT = [frozenset({rf.GPU, "q3"})]
YARN_OPT = [frozenset({rf.GPU} | THREADS)]


def cand(rid, opts, rank, est, lane="gpu", **kw):
    c = {"id": rid, "kind": "grant", "lane": lane, "rank": float(rank), "lane_count": 1, "gib": 64, "bench": True,
         "options": list(opts), "window_s": est * 2, "estimate_s": est, "shape": "gpu"}
    c.update(kw)
    return c


def incident_free():
    # every quarter busy with p12 (0-95); gpu-quiet, the MI210 host threads and the q*-upper siblings free
    return {rf.GPU} | THREADS | {f"t{k}" for r in ((112, 120), (136, 144), (160, 168)) for k in range(*r)}


class RankInversion(unittest.TestCase):
    def setUp(self):
        self.noise = cand("m4-gpu-aa-noise-20261104", NOISE_OPT, 1, 300, ports=[18792])
        self.yarn = cand("codex-ni-yarn-e1-mem-chain-r2-20261104", YARN_OPT, 80, 4800, ports=[18438], min_window_s=1000 * 3600)  # D9 2026-11-11: min_window above the gap, so the cap fails cap_ok and the row stays late

    def test_incident_replay_lower_row_not_granted_the_gpu(self):
        out, _, pend = rf.plan(incident_free(), [self.yarn, self.noise], 1000, now=NOW, grant_ends=[NOW + 1080])
        self.assertEqual(out, [])
        self.assertEqual({c["id"] for c in pend}, {self.noise["id"], self.yarn["id"]})
        self.assertEqual([(lc["id"], hc["id"]) for lc, hc, _ in rf.plan.rank_holds], [(self.yarn["id"], self.noise["id"])])

    def test_better_row_takes_the_gpu_once_q3_frees(self):
        free = incident_free() | rf.expand({"q3"})
        out, _, _ = rf.plan(free, [self.yarn, self.noise], 1000, now=NOW + 1080)
        self.assertEqual([c["id"] for c, _ in out], [self.noise["id"]])

    def test_short_lower_row_still_backfills(self):
        short = cand("short", YARN_OPT, 80, 600)
        out, _, _ = rf.plan(incident_free(), [short, self.noise], 1000, now=NOW, grant_ends=[NOW + 1080])
        self.assertEqual([c["id"] for c, _ in out], ["short"])

    def test_own_constraint_does_not_reserve_and_is_named(self):
        for kw, frag in (({"arm_fails": 2}, "failing to arm"), ({"ports": [18438]}, "port 18438 held")):
            noise = cand("noise", NOISE_OPT, 1, 300, **kw)
            yarn = cand("yarn", YARN_OPT, 80, 4800, ports=[18439])
            out, _, _ = rf.plan(incident_free(), [yarn, noise], 1000, now=NOW, grant_ends=[NOW + 1080],
                                held_ports=[18438])
            self.assertEqual([c["id"] for c, _ in out], ["yarn"])
            self.assertEqual(len(rf.plan.rank_skips), 1)
            self.assertIn(frag, rf.plan.rank_skips[0][2])

    def test_far_or_unknown_free_time_does_not_reserve(self):
        for ends in ([], [NOW + rf.DRAIN_MAX_WAIT_S + 60]):
            out, _, _ = rf.plan(incident_free(), [self.yarn, self.noise], 1000, now=NOW, grant_ends=ends)
            self.assertEqual([c["id"] for c, _ in out], [self.yarn["id"]])
            self.assertIn("busy regions", rf.plan.rank_skips[0][2])


if __name__ == "__main__":
    unittest.main()
