"""ws58 2026-11-02 sub-quarter packing: rows whose claim covers < 24 cores of a quarter share that quarter."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

ALL = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
T = lambda *n: {f"t{k}" for k in n}  # noqa: E731


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
        self.assertEqual(o, frozenset({"c0", "c1", "c2", "c3"} | T(96, 97, 98, 99)))
        self.assertEqual(rf.grant_regions({"regions": "any-cpu-quarter"}, o), "0,1,2,3,96,97,98,99")

    def test_gpu_row_holds_host_threads_not_q3(self):
        (o,) = shape(cls="gpu", regions="mi210_0,184-187")
        self.assertEqual(o, frozenset({rf.GPU} | T(184, 185, 186, 187)))
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
        self.assertEqual(rf.cpu_tokens("96-99"), {"c0", "c1", "c2", "c3"} | T(96, 97, 98, 99))
        self.assertEqual(rf.compress(rf.expand({"q2"}) | {"c1"}), ["c1", "q2"])



def gshape(regions="mi210_0,184-191", claim="", gq="exclusive", engine_text=None, nofold=False):
    import tempfile
    o = {"class": "gpu", "gpu_quiet": gq, "claim_cpus": claim, "nofold": nofold, "engine": "/nonexistent/filler_run15.sh"}
    if engine_text is not None:
        f = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False)
        f.write(engine_text); f.close(); o["engine"] = f.name
    with mock.patch.object(rf, "parse_launcher", return_value=o):
        return rf.row_shape({"regions": regions, "launcher": {"path": "x"}})[0]


class GpuHostThreads(unittest.TestCase):
    """ws58 2026-11-02 18:21Z: inf22-m4-aa-np4-r6 (mi210_0,184-191, --claim-cpus 72-95) waited on q3 behind a host row."""

    def test_grant_cpus_engine_books_only_declared_host_threads(self):
        (o,) = gshape(claim="72-95", engine_text="# GRANT_CPUS\n")
        self.assertEqual(o, frozenset({rf.GPU} | T(*range(184, 192))))
        self.assertFalse(o & set(rf.QUARTERS) or o & set(rf.CORES))

    def test_legacy_engine_keeps_its_claim(self):
        (o,) = gshape(claim="72-95")   # the snapshot engine still region-locks 72-95: booking must match it
        self.assertEqual(o, frozenset({rf.GPU, "q3"}))
        (o,) = gshape(claim="", gq="exclusive")   # legacy exclusive default claim = 0-95
        self.assertTrue(set(rf.QUARTERS) <= o)

    def test_nofold_or_claimless_legacy_row_locks_no_cpu(self):
        (o,) = gshape(nofold=True)
        self.assertEqual(o, frozenset({rf.GPU} | T(*range(184, 192))))
        (o,) = gshape(gq="shared")
        self.assertEqual(o, frozenset({rf.GPU} | T(*range(184, 192))))

    def test_explicit_cpu_region_claims_cpus(self):
        (o,) = gshape(regions="mi210_0,0-23,184-191", claim="0-23,184-191", engine_text="GRANT_CPUS")
        self.assertEqual(o, frozenset({rf.GPU, "q0"} | T(*range(184, 192))))

    def test_gpu_row_runs_beside_whole_host_row(self):
        host_busy = rf.expand(set(rf.QUARTERS))
        free = ALL - host_busy
        (g,) = gshape(engine_text="GRANT_CPUS")
        c = dict(cand("gpu", [g]), lane="gpu")
        out, idle, _ = rf.plan(free, [c], 1000)
        self.assertEqual([x["id"] for x, _ in out], ["gpu"])
        self.assertNotIn(rf.GPU, idle)

    def test_whole_quarter_row_beside_gpu_host_threads(self):
        (g,) = gshape(engine_text="GRANT_CPUS")
        free = ALL - set(g)   # GPU grant open on t184-191
        out, _, _ = rf.plan(free, [cand("w", [frozenset({"q3"})])], 1000)
        self.assertEqual([sorted(o) for _, o in out], [["q3"]])

    def test_quarter_with_a_busy_core_is_not_whole_free(self):
        free = ALL - {"c88", "t184"}   # a sub-quarter row holds core 88 (+ its sibling)
        out, _, pend = rf.plan(free, [cand("w", [frozenset({"q3"})])], 1000)
        self.assertEqual(out, [])
        out, _, _ = rf.plan(free, [cand("s", shape("72-75"))], 1000)
        self.assertEqual(len(out), 1)

    def test_grant_records_exact_cpu_list(self):
        self.assertEqual(rf.grant_cpus("q1"), "24-47,120-135")
        self.assertEqual(rf.grant_cpus("mi210_0,184-191"), "184-191")
        self.assertEqual(rf.grant_cpus("0,1,96,97"), "0,1,96,97")
        import tempfile
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "grants"))
        line = rf.write_grant(d, "r", "mi210_0,184-191", {rf.GPU} | T(184), 600)
        self.assertTrue(line.endswith("cpus=184-191"), line)
        self.assertIn("holds=gpu-quiet,t184", line)

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
