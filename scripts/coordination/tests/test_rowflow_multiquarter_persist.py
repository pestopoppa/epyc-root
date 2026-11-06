#!/usr/bin/env python3
"""Emergency fix 2026-11-06: an accepted multi-quarter shape (shape_override OR width_justification) is persisted in the
manifest and booked by the keeper - a 2-quarter row is granted 2 quarters or waits, never 1 (r4-pca was granted q1 only)."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_rowflow_shape_evidence import Fx, rf, ALL_TOKENS  # noqa: E402

OVR = "operator: pestopoppa 2026-11-06: widen to 2 quarters (longest arm); operator ruling: more than one quarter when justified"
WJ = "width-agnostic 32k CPU prefill; dense compute scales with threads"


def cand(row_manifest, flags):
    k = rf.contract_of(row_manifest, flags=flags)
    return {"id": row_manifest["id"], "kind": "grant", "lane": "cpu", "rank": 20, "lane_count": 0, "gib": 48, "bench": False,
            "options": k["options"], "shape": k["shape"], "since": time.time(), "window_s": 3600, "estimate_s": 3600,
            "coexist": False, "lends": frozenset()}


class MultiQuarter(Fx):
    def publish(self, rid, **kw):
        lp = self.launcher(rid)   # no thread knob: width-agnostic
        return rf.publish(self.spec(rid, lp, regions="any-cpu-quarter", shape="multi-quarter(2)", **kw), self.flags)

    def check(self, row):
        self.assertEqual(row["shape"], "multi-quarter(2)")
        k = rf.contract_of(row, flags=self.flags)
        self.assertEqual(k["shape"], "multi-quarter(2)")
        self.assertTrue(all(len([q for q in o if q in rf.QUARTERS]) == 2 for o in k["options"]))
        # preference: q0-q2 combinations before any holding q3
        firsts = [("q3" in o) for o in k["options"]]
        self.assertEqual(firsts, sorted(firsts))
        free = ALL_TOKENS
        out, _, _ = rf.plan(free, [cand(row, self.flags)], 1000)
        self.assertEqual(len(out), 1)
        self.assertEqual(len({q for q in out[0][1] if q in rf.QUARTERS}), 2)
        self.assertNotIn("q3", out[0][1])
        self.assertEqual(len(rf.grant_regions(row, out[0][1]).split(",")), 2)
        # replay: only q1 and q3 free -> never one quarter. The row waits unless q3 is placeable under its own rules.
        for free in (ALL_TOKENS - {"q0", "q2"}, ALL_TOKENS - {"q0", "q1", "q3"}):
            out, _, _ = rf.plan(free, [cand(row, self.flags)], 1000)
            for _, o in out:
                self.assertEqual(len({q for q in o if q in rf.QUARTERS}), 2)
        out, _, _ = rf.plan(ALL_TOKENS - {"q0", "q2", "q3"}, [cand(row, self.flags)], 1000)
        self.assertEqual(out, [])   # one free quarter: waits

    def test_shape_override_persists_and_books_two(self):
        self.check(self.publish("ovr", shape_override=OVR))

    def test_width_justification_persists_and_books_two(self):
        self.check(self.publish("wj2", width_justification=WJ))

    def test_negative_control_old_behaviour_grants_one(self):
        row = self.publish("neg", shape_override=OVR)
        old = dict(row)
        old.pop("shape_override")          # the pre-fix contract ignored the override: threads unknown -> one quarter
        old.pop("declared_shape", None)
        old["shape"] = "quarter"
        k = rf.contract_of(old, flags=self.flags)
        self.assertEqual(k["shape"], "quarter")
        out, _, _ = rf.plan(ALL_TOKENS - {"q0", "q2", "q3"}, [cand(old, self.flags)], 1000)
        self.assertEqual(len(out), 1)
        self.assertEqual(len({q for q in out[0][1] if q in rf.QUARTERS}), 1)


class GpuWidth(Fx):
    """operator 2026-11-06 ("Allow, q0-q2 only"): a justified GPU row may add whole q0-q2 quarters beside its GPU grant."""
    def gpu_row(self, rid, regions, **kw):
        lp = self.launcher(rid, cmd="python3 ref.py", cls="gpu", extra="--no-fold-siblings --gpu-quiet shared")
        return rf.publish(self.spec(rid, lp, lane="gpu", regions=regions, **kw), self.flags)

    def test_justified_gpu_row_plus_q0_granted_unjustified_refused(self):
        row = self.gpu_row("gj", "mi210_0,0-23,184-191", width_justification=WJ)
        k = rf.contract_of(row, flags=self.flags)
        self.assertEqual(len(k["options"]), 1)
        opt = k["options"][0]
        self.assertIn("q0", opt)
        self.assertNotIn("q3", opt)
        self.assertFalse({"c72", "c80", "c87"} & rf.expand(opt))      # q3 72-87 never added
        out, _, _ = rf.plan(ALL_TOKENS, [cand(row, self.flags) | {"lane": "gpu"}], 1000)
        self.assertEqual(len(out), 1)
        self.assertEqual(rf.grant_regions(row, out[0][1]), "mi210_0,0-23,184-191")
        with self.assertRaises(rf.Refused):   # no justification: the q0 declaration is refused
            self.gpu_row("gu", "mi210_0,0-23,184-191")

    def test_justified_gpu_row_never_gets_q3_or_whole_host(self):
        row = self.gpu_row("gq", "mi210_0,0-23,72-87,184-191", width_justification=WJ)
        opt = rf.contract_of(row, flags=self.flags)["options"][0]
        self.assertNotIn("q3", opt)
        self.assertEqual(rf.grant_regions(row, opt), "mi210_0,0-23,184-191")
        row = self.gpu_row("gh", "mi210_0,0-95,184-191", width_justification=WJ)
        k = rf.contract_of(row, flags=self.flags)
        self.assertNotIn("q3", k["options"][0])
        self.assertNotIn(k["shape"], ("host", "quiet-host"))


if __name__ == "__main__":
    unittest.main()
