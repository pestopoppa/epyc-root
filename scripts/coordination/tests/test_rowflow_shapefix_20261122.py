#!/usr/bin/env python3
"""shapefix 2026-11-22 (r5/r6 any-of q0,q1,q2, 24 threads, granted 2 quarters): the engine's own comments (`-t 48`, `-t 10`)
were scanned as the job's argv, and the spec's declared_threads was ignored."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_rowflow_shape_evidence import Fx  # noqa: E402
import rowflow as rf  # noqa: E402


class ShapeFix(Fx):
    def _job_naming_engine(self, rid):
        """job.py whose docstring names rowflow.py / filler_run15.sh, like r6's chain did."""
        d = os.path.join(self.root, rid)
        os.makedirs(d, exist_ok=True)
        infra = os.path.join(d, "bin", "compute-flags", "bin", "rowflow")
        os.makedirs(infra, exist_ok=True)
        eng = os.path.join(infra, "filler_run15.sh")
        open(eng, "w").write("#!/bin/bash\ntimeout 60 \"$d\" stop -t 10 \"$c\"\n# taskset 0-95 + -t 48\n")
        job = os.path.join(d, "job.py")
        open(job, "w").write(f'"""runs under {eng}"""\nTHREADS = 24\nprint("--threads 24")\n')
        return job

    def test_infra_files_never_thread_evidence(self):
        job = self._job_naming_engine("sf1")
        lp = self.launcher("sf1", cmd=f"/usr/bin/python3 {job} --threads 24")
        o = rf.parse_launcher(lp)
        self.assertEqual(o["threads"], 24, o["threads_evidence"])
        self.assertTrue(rf._is_rowflow_infra("/x/compute-flags/bin/rowflow/rowflow.py"))
        self.assertFalse(rf._is_rowflow_infra("/x/tmp/row/job.py"))

    def test_anyof_24_threads_gets_one_quarter(self):
        job = self._job_naming_engine("sf2")
        lp = self.launcher("sf2", cmd=f"/usr/bin/python3 {job} --threads 24")
        row = rf.publish(self.spec("sf2", lp, regions="any-of q0,q1,q2", shape="quarter", declared_threads=24), self.flags)
        self.assertEqual(row["shape"], "quarter")
        self.assertEqual(row["declared_threads"], 24)

    def test_spec_declared_threads_overrides_wider_scan_and_logs(self):
        lp = self.launcher("sf3", cmd="llama-bench -t 48")
        row = rf.publish(self.spec("sf3", lp, regions="any-of q0,q1,q2", shape="quarter", declared_threads=24), self.flags)
        self.assertEqual(row["declared_threads"], 24)
        self.assertEqual(row["shape"], "quarter")
        self.assertTrue(any("THREADS-SCAN-OVERRIDDEN" in w for w in row["publish_warnings"]))

    def test_ram_widening_is_logged_and_opt_out(self):
        lp = self.launcher("sf4", cmd="llama-bench -t 24")
        row = rf.publish(self.spec("sf4", lp, regions="any-of q0,q1,q2", ram_gib=300,
                                   width_justification="model needs 300 GiB, two NUMA quarters of RAM"), self.flags)
        self.assertEqual(row["shape"], "multi-quarter(2)")
        self.assertTrue(any(w.startswith("SHAPE-WIDENED") and "RAM 300" in w for w in row["publish_warnings"]))
        lp = self.launcher("sf5", cmd="llama-bench -t 24")
        row = rf.publish(self.spec("sf5", lp, regions="any-of q0,q1,q2", ram_gib=300, shape_widen=False), self.flags)
        self.assertEqual(row["shape"], "quarter")
        self.assertFalse(any(w.startswith("SHAPE-WIDENED") for w in row.get("publish_warnings") or []))


if __name__ == "__main__":
    unittest.main()
