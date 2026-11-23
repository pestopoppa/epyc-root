"""PM-ANYOF 2026-11-20: a row declaring `regions: any-of qA,qB` may only ever be granted quarters from that set.
Origin: lsa-cpu-sparse-e2e-bound-20261120-r1 ("any-of q1,q2", threads 24) was granted q0: contract_of emitted every
quarter for the threads-known branches and only the threads-unknown branch read the any-of set."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402


def spec(regions, shape="quarter", **kw):
    d = {"regions": regions, "shape": shape, "declared_shape": shape, "timing": "bench"}
    d.update(kw)
    return d


def quarters(opt):
    return {t for t in opt if t in rf.QUARTERS}


class AnyOfRegions(unittest.TestCase):
    def test_any_of_q1_q2_never_q0(self):
        opts = rf.contract_of(spec("any-of q1,q2"), {"class": "cpu", "gpu_quiet": "shared", "threads": 24})["options"]
        self.assertTrue(opts)
        for o in opts:
            self.assertFalse(quarters(o) - {"q1", "q2"}, sorted(o))
            self.assertTrue(quarters(o))

    def test_default_options_path(self):
        c = rf.contract_of(spec("any-of q1,q2"))
        self.assertEqual({frozenset(quarters(o)) for o in c["options"]}, {frozenset({"q1"}), frozenset({"q2"})})

    def test_single_quarter_of_set_is_fine(self):
        c = rf.contract_of(spec("any-of q2,q3"))
        self.assertEqual({frozenset(quarters(o)) for o in c["options"]}, {frozenset({"q2"}), frozenset({"q3"})})
        c = rf.contract_of(spec("any-of q1"))
        self.assertEqual({frozenset(quarters(o)) for o in c["options"]}, {frozenset({"q1"})})

    def test_multi_quarter_any_of_keeps_count(self):
        c = rf.contract_of(spec("any-of q0,q1,q2", shape="multi-quarter(2)"), {"class": "cpu", "threads": 48})
        self.assertTrue(c["options"])
        for o in c["options"]:
            self.assertEqual(len(quarters(o)), 2, sorted(o))
            self.assertFalse(quarters(o) - {"q0", "q1", "q2"})

    def test_multi_quarter_wider_than_set_stays_inside(self):
        c = rf.contract_of(spec("any-of q1,q2", shape="multi-quarter(3)"), {"class": "cpu", "threads": 72})
        for o in c["options"]:
            self.assertFalse(quarters(o) - {"q1", "q2"}, sorted(o))

    def test_declared_threads_beats_launcher_scan(self):
        # ak-cpu-a3b-nonweight-split-20261123: declared 24, argv scan 48 -> was multi-quarter(2) draining q2
        d = {"regions": "any-of q0,q1,q2", "shape": "quarter", "declared_shape": "quarter", "declared_threads": 24,
             "lane": "cpu", "gib": 64}
        c = rf.contract_of(d, {"class": "cpu", "threads": 48})
        self.assertEqual(c["shape"], "quarter")
        self.assertEqual({frozenset(quarters(o)) for o in c["options"]}, {frozenset({q}) for q in ("q0", "q1", "q2")})

    def test_any_cpu_quarter_unrestricted(self):
        c = rf.contract_of(spec("any-cpu-quarter"))
        self.assertEqual({frozenset(quarters(o)) for o in c["options"]}, {frozenset({q}) for q in rf.QUARTERS})


if __name__ == "__main__":
    unittest.main()
