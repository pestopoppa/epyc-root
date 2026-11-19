#!/usr/bin/env python3
"""Emergency 2026-11-06 (operator "Yes, both"): a CPU multi-quarter booking uses q0-q2 ONLY and waits when they are not
free. Origin: lsa-quality-32k-20261106-r5-pca was granted q1+q3; its q3 lock covered cores 88-95 (physical cores behind the
MI210 host threads 184-191) and c7-q38-ppl-bisect-20261106-r5 waited 600 s on q3, rc75, MI210 idle ~40 min.
NEGATIVE CONTROL: the engine of 15804eaf5 (the pre-fix commit) is loaded from git and DOES grant q1+q3 here."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_rowflow_shape_evidence import Fx, rf, ALL_TOKENS  # noqa: E402

OVR = "operator: pestopoppa 2026-11-06: widen to multiple quarters; operator ruling: more than one quarter when justified"
PRE_FIX = "15804eaf5"


def cand(mod, row, flags):
    k = mod.contract_of(row, flags=flags)
    return {"id": row["id"], "kind": "grant", "lane": "cpu", "rank": 20, "lane_count": 0, "gib": 48, "bench": False,
            "options": k["options"], "shape": k["shape"], "since": time.time(), "window_s": 3600, "estimate_s": 3600,
            "coexist": False, "lends": frozenset()}


def free_only(mod, quarters):
    """Every token except the quarters (and their cores/threads) that are busy."""
    busy = set()
    for q in set(mod.QUARTERS) - set(quarters):
        busy |= mod.expand({q})
    return {t for t in ALL_TOKENS if t not in busy}


def prefix_engine():
    d = tempfile.mkdtemp(prefix="rf-prefix-")
    repo = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True,
                          cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
    tar = subprocess.run(["git", "-C", repo, "archive", PRE_FIX, "scripts/coordination/rowflow"], capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", d], input=tar.stdout, check=True)
    path = os.path.join(d, "scripts/coordination/rowflow")
    sys.path.insert(0, path)
    try:
        spec = importlib.util.spec_from_file_location("rowflow_prefix", os.path.join(path, "rowflow.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(path)
    return mod


class NoQ3MultiQuarter(Fx):
    def publish(self, rid, n=2, **kw):
        lp = self.launcher(rid)
        return rf.publish(self.spec(rid, lp, regions="any-cpu-quarter", shape=f"multi-quarter({n})",
                                    shape_override=OVR, **kw), self.flags)

    def test_options_never_hold_q3(self):
        for n in (2, 3):
            row = self.publish(f"nq3-{n}", n=n)
            k = rf.contract_of(row, flags=self.flags)
            self.assertEqual(k["shape"], f"multi-quarter({n})")
            self.assertTrue(k["options"])
            self.assertTrue(all("q3" not in o for o in k["options"]), k["options"])
            self.assertTrue(all(len({q for q in o if q in rf.QUARTERS}) == n for o in k["options"]))

    def test_waits_when_only_q3_plus_one_is_free(self):
        row = self.publish("nq3-wait")
        free = free_only(rf, {"q1", "q3"})
        out, _, _ = rf.plan(free, [cand(rf, row, self.flags)], 1000)
        self.assertEqual(out, [], "granted a multi-quarter row with only q1+q3 free")

    def test_grants_q0_q2_pair_when_free(self):
        row = self.publish("nq3-ok")
        out, _, _ = rf.plan(free_only(rf, {"q1", "q2", "q3"}), [cand(rf, row, self.flags)], 1000)
        self.assertEqual(len(out), 1)
        self.assertEqual({q for q in out[0][1] if q in rf.QUARTERS}, {"q1", "q2"})

    def test_gpu_row_q3_rules_unchanged(self):
        # gpu-q3 NARROW: a GPU timing row still holds 88-95 (q3 cores) with its host threads; the shape is untouched
        self.assertIn("gpu-q3", rf.SHAPES)
        self.assertEqual(rf.GPU_Q3_ALLOWED_CPUS, frozenset(range(72, 96)) | frozenset(range(168, 192)))

    def test_negative_control_prefix_engine_grants_q1_q3(self):
        old = prefix_engine()
        row = self.publish("nq3-neg")
        out, _, _ = old.plan(free_only(old, {"q1", "q3"}), [cand(old, row, self.flags)], 1000)
        self.assertEqual(len(out), 1, "control: the pre-fix engine no longer grants q1+q3 - the test proves nothing")
        self.assertEqual({q for q in out[0][1] if q in old.QUARTERS}, {"q1", "q3"})


if __name__ == "__main__":
    unittest.main()
