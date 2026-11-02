"""ws58 2026-11-02 sub-quarter packing: rows whose claim covers < 24 cores of a quarter share that quarter."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

ALL = set(rf.REGIONS) | set(rf.CORES)


def shape(claim=None, cls="cpu", regions="any-cpu-quarter", nofold=False, gq=""):
    o = {"class": cls}
    if claim:
        o["claim_cpus"] = claim
    if nofold:
        o["nofold"] = True
    if gq:
        o["gpu_quiet"] = gq
    with mock.patch.object(rf, "parse_launcher", return_value=o):
        return rf.row_shape({"regions": regions, "launcher": {"path": "x"}})[0]


def cand(rid, opts, rank=1):
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": rank, "lane_count": 0, "gib": 0, "bench": False,
            "options": opts, "window_s": 600}


class SubQuarter(unittest.TestCase):
    def test_small_claim_holds_only_its_cores(self):
        (o,) = shape("0-3")
        self.assertEqual(o, frozenset({"c0", "c1", "c2", "c3"}))
        self.assertEqual(rf.grant_regions({"regions": "any-cpu-quarter"}, o), "0,1,2,3,96,97,98,99")

    def test_gpu_row_holds_host_threads_not_q3(self):
        (o,) = shape(cls="gpu", regions="mi210_0,184-187")
        self.assertEqual(o, frozenset({rf.GPU, "c88", "c89", "c90", "c91"}))
        self.assertNotIn("q3", o)

    def test_whole_quarter_row_unchanged(self):
        opts = shape()
        self.assertEqual(len(opts), 4)
        self.assertTrue(all(len([t for t in o if t in rf.QUARTERS]) == 1 and len(o) == 1 for o in opts))

    def test_two_small_rows_share_a_quarter_and_block_whole_quarter(self):
        free = {"q0"}   # only q0 free (legacy region-only free set)
        a, b = cand("a", shape("0-3")), cand("b", shape("4-11"))
        w = cand("w", shape(), rank=0)
        out, _, pend = rf.plan(free, [w, a, b], 1000)
        placed = {c["id"] for c, _ in out}
        self.assertEqual(placed, {"w"})   # whole q0 free -> top-ranked whole row takes it
        out, _, pend = rf.plan(free, [dict(a, rank=0), dict(b, rank=0), dict(w, rank=5)], 1000)
        self.assertEqual({c["id"] for c, _ in out}, {"a", "b"})   # sub rows pack; q0 is no longer free for w
        self.assertEqual([c["id"] for c in pend], ["w"])

    def test_overlapping_small_rows_do_not_share(self):
        out, _, pend = rf.plan(ALL, [cand("a", shape("0-3")), cand("b", shape("2-5"))], 1000)
        self.assertEqual(len(out), 1)

    def test_cpu_tokens_folds_siblings_and_caps_at_24_cores(self):
        self.assertEqual(rf.cpu_tokens("0-23,96-119"), {"q0"})
        self.assertEqual(rf.cpu_tokens("96-99"), {"c0", "c1", "c2", "c3"})
        self.assertEqual(rf.compress(rf.expand({"q2"}) | {"c1"}), ["c1", "q2"])


class FarDrain(unittest.TestCase):
    def test_far_T_still_drains_and_backfills(self):
        now = 1_000_000.0
        host = dict(cand("h", [frozenset(rf.REGIONS)], rank=0), shape="quiet-host")
        short = dict(cand("s", [frozenset({q}) for q in rf.QUARTERS]), window_s=3600)
        longr = dict(cand("l", [frozenset({q}) for q in rf.QUARTERS]), window_s=5 * 3600)
        out, idle, _ = rf.plan({"q3"}, [host, longr, short], 1000, now=now, grant_ends=[now + 3 * 3600])
        self.assertIsNotNone(rf.plan.last_drain)
        self.assertEqual([(c["id"], sorted(o)) for c, o in out], [("s", ["q3"])])


if __name__ == "__main__":
    unittest.main()
