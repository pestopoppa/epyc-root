"""QUIET-SERIAL-ALL + EXCLUSIVE-CPU-HOLD (AK 2026-11-23 23:43Z): c20-fold-cpu-r4 (q0) and ak-cpu-aa-calibration-q-a3b (q2) ran
together because neither MANIFEST carried requires_quiet_host; both ran in-run quiet guards. QUIET-SERIAL now covers every
quiet-sensitive row class (declared, spec-source, job-code derived); exclusive_cpu is an owner opt-in host CPU hold."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

UTIL = {"q0": 2.0, "q1": 3.0, "q2": 1.0, "q3": 4.0}


def cand(rid, opts, rank=20, shape="quarter", est=None):
    c = {"id": rid, "shape": shape, "rank": rank, "kind": "grant", "options": [frozenset(o) for o in opts]}
    if est:
        c["estimate_s"] = est
    return c


def jobdir(td, name, code):
    d = os.path.join(td, name)
    os.makedirs(d)
    with open(os.path.join(d, "launch.sh"), "w") as f:
        f.write("#!/bin/bash\n")
    with open(os.path.join(d, "job.py"), "w") as f:
        f.write(code)
    return {"launcher": {"path": os.path.join(d, "launch.sh"), "sha256": name}, "workdir": d}


class Derived(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        rf._QUIET_SCAN.clear()

    def test_classes(self):
        self.assertTrue(rf.quiet_sensitive({"quiet_sensitive": True}))
        self.assertTrue(rf.quiet_sensitive(jobdir(self.td, "a", "g = H.quiet_guard(phys, rb, out)\n")))
        self.assertTrue(rf.quiet_sensitive(jobdir(self.td, "b", "PAIRS, QUIET_BUSY_P95 = 24, 15.0\n")))
        self.assertFalse(rf.quiet_sensitive(jobdir(self.td, "c", "print('loud')\n")))
        # explicit owner opt-out wins over the code scan
        self.assertFalse(rf.quiet_sensitive(dict(jobdir(self.td, "d", "H.run_quiet(m)\n"), requires_quiet_host=False)))
        # the library file alone is not a call site
        d = jobdir(self.td, "e", "x = 1\n")
        with open(os.path.join(d["workdir"], "ak_row_harness.py"), "w") as f:
            f.write("def quiet_guard(c):\n    pass\n")
        self.assertFalse(rf.quiet_sensitive(d))
        # spec source says requires_quiet_host though the manifest lost it (stale-publisher drop, c20-fold-cpu-r4)
        sp = os.path.join(self.td, "spec.json")
        with open(sp, "w") as f:
            json.dump({"requires_quiet_host": True}, f)
        self.assertTrue(rf.quiet_sensitive({"published_from": sp}))
        self.assertFalse(rf.quiet_required({"published_from": sp}))   # the foreign-busy gate is not widened

    def test_incident_cross_quarter_co_grant_refused(self):
        rows = {"c20": jobdir(self.td, "c20", "H.quiet_guard(p, r, o)\n"),
                "cal": jobdir(self.td, "cal", "QUIET_BUSY_P95 = 15.0\n"),
                "spec": dict(jobdir(self.td, "spec", "print(1)\n"), requires_quiet_host=False)}
        grants = [{"id": "spec", "holds": {"q1"}}, {"id": "cal", "holds": {"q2"}}]
        kept, waits, lines = rf.quiet_gate([cand("c20", [{"q0"}], rank=5)], rows, grants, UTIL)
        self.assertEqual(kept, [])
        self.assertEqual(lines["c20"], "QUIET-SERIAL c20 waits for running quiet cal")
        # with only the non-quiet specpit row running, c20 is granted (no foreign-busy gate on a derived row)
        kept, _, _ = rf.quiet_gate([cand("c20", [{"q0"}], rank=5)], rows, grants[:1], {"q0": 40.0})
        self.assertEqual([c["id"] for c in kept], ["c20"])

    def test_shortest_first_across_derived_and_declared(self):
        rows = {"a": {"requires_quiet_host": True}, "b": jobdir(self.td, "b", "H.run_quiet(m)\n"), "n": {}}
        cs = [cand("a", [{"q0"}], est=9000), cand("b", [{"q2"}], est=600, rank=60), cand("n", [{"q1"}])]
        kept, _, lines = rf.quiet_gate(cs, rows, [], UTIL)
        self.assertEqual(sorted(c["id"] for c in kept), ["b", "n"])
        self.assertEqual(lines["a"], "QUIET-SERIAL a waits for running quiet b")

    def test_urgent_rank_beats_shortest(self):
        """2026-11-24 deadlock: a shorter non-urgent row won QUIET-SERIAL while QUIET-RESERVE held it for the urgent one."""
        rows = {"u": {"requires_quiet_host": True}, "s": {"requires_quiet_host": True}}
        cs = [cand("u", [{"q0"}], est=20000, rank=5), cand("s", [{"q1"}], est=600, rank=40)]
        kept, _, lines = rf.quiet_gate(cs, rows, [], UTIL)
        self.assertIn("u", [c["id"] for c in kept])
        self.assertEqual(lines["s"], "QUIET-SERIAL s waits for running quiet u")


class ExclusiveCpu(unittest.TestCase):
    def rows(self, **kw):
        return {"x": dict({"requires_quiet_host": True, "priority_rank": 5, "exclusive_cpu": True}, **kw), "n": {}, "g": {"lane": "gpu"}}

    def test_hold_logs_and_spares_gpu(self):
        cs = [cand("n", [{"q1"}]), dict(cand("g", [{"gpu-quiet", "c88"}]), lane="gpu")]
        kept, waits, lines = rf.quiet_gate(cs, self.rows(), [{"id": "x", "holds": {"q0"}}], UTIL)
        self.assertEqual([c["id"] for c in kept], ["g"])
        self.assertTrue(lines["n"].startswith("EXCLUSIVE-CPU-HOLD x"))

    def test_off_by_default_and_rank_gated(self):
        g = [{"id": "x", "holds": {"q0"}}]
        for rows in (self.rows(exclusive_cpu=None), self.rows(priority_rank=11)):
            kept, _, _ = rf.quiet_gate([cand("n", [{"q1"}])], rows, g, UTIL)
            self.assertEqual([c["id"] for c in kept], ["n"])

    def test_not_running_no_hold(self):
        kept, _, _ = rf.quiet_gate([cand("n", [{"q1"}])], self.rows(), [], UTIL)
        self.assertEqual([c["id"] for c in kept], ["n"])


if __name__ == "__main__":
    unittest.main()
