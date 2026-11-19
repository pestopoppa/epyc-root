#!/usr/bin/env python3
"""rtg34-r1a-bench-claim-20261111 (2026-11-11): a --self-claim row (regions default any-cpu-quarter) declaring shape host with
-t 96 evidence was resolved multi-quarter(3) and granted q0-q2; its own 0-95 bench claim then waited 600 s on q3.
A row with > 72 threads, or a declared host shape with whole-host evidence, must book all four quarters."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_rowflow_shape_evidence import Fx, rf  # noqa: E402


class SelfClaimHost(Fx):
    def test_selfclaim_96_threads_is_host(self):
        lp = self.launcher("r1a", cmd="llama-bench -t 96", extra="--self-claim --role bench")
        row = rf.publish(self.spec("r1a", lp, shape="host"), self.flags)
        self.assertEqual(row["regions"], "any-cpu-quarter")
        k = rf.contract_of(row, flags=self.flags)
        self.assertEqual(k["shape"], "host")
        self.assertEqual(k["options"], [frozenset(rf.QUARTERS)])

    def test_selfclaim_96_threads_undeclared_is_host(self):
        lp = self.launcher("r1b", cmd="llama-bench -t 96", extra="--self-claim --role bench")
        row = rf.publish(self.spec("r1b", lp), self.flags)
        self.assertEqual(rf.contract_of(row, flags=self.flags)["options"], [frozenset(rf.QUARTERS)])

    def test_48_threads_still_multiquarter(self):
        lp = self.launcher("mq", cmd="bench -t 48", extra="--self-claim")
        row = rf.publish(self.spec("mq", lp, shape="multi-quarter(2)"), self.flags)
        self.assertEqual(rf.contract_of(row, flags=self.flags)["shape"], "multi-quarter(2)")


if __name__ == "__main__":
    unittest.main()
