#!/usr/bin/env python3
"""2026-11-08 inf75-c7r-w3-halfb: a grant's lock= list must cover every cpu the grant holds, t<N> SMT tokens included."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow"))
import rowflow as rf  # noqa: E402


def cpus(s):
    out = set()
    for p in s.split(","):
        a, _, b = p.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return out


class LockTokens(unittest.TestCase):
    def test_quarters_plus_smt_tokens_cover_the_whole_grant(self):
        opt = {"gpu-quiet", "q2", "q3"} | {f"t{i}" for i in [*range(160, 168), *range(184, 192)]}
        self.assertEqual(cpus(rf.lock_cpus(opt)), set(range(48, 96)) | set(range(144, 192)))

    def test_core_tokens_keep_their_output(self):
        self.assertEqual(rf.tokens_cpus({"c88", "c89"}), "88,89,184,185")

    def test_token_already_covered_by_its_core_is_not_repeated(self):
        self.assertEqual(rf.tokens_cpus({"c88", "t184", "t185"}), "88,184,185")


if __name__ == "__main__":
    unittest.main()
