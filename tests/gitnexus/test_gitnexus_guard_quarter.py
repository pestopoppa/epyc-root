"""Operator decision 2026-11-05: `--workers 1` analyze admits on ONE quarter.

Policy fixtures with patched /proc and lock seams (pattern of APP
tests/unit/test_gitnexus_quarter.py); they do not prove a live grant.
"""
import importlib.util
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
spec = importlib.util.spec_from_file_location("gitnexus_guard", SCRIPTS / "gitnexus-guard.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
UID = os.getuid()
OWNER = 41234
ONE = ["--skip-agents-md", "--workers", "1", "--force"]


def payload(q, regions, pid=OWNER):
    return json.dumps({"schema_version": 1, "pid": pid, "role": "build", "region": q,
                       "regions": list(regions), "request_tag": "filler-case",
                       "started_at": time.time() - 1}).encode()


class Base(unittest.TestCase):
    held = {("GLOBAL", "q2"), ("build", "q2")}
    regions = None  # None -> single held quarter

    def setUp(self):
        self.held = set(type(self).held)
        self.owner_of = {}
        self.payload_regions = None

        def identity(path):
            role, q = Path(path).name.split(".")[1:3]
            inode = 100 + (0 if role == "GLOBAL" else 4) + int(q[1])
            regions = self.payload_regions or ((q,) if len({x[1] for x in self.held}) == 1 else G.QUADRANTS)
            return (os.makedev(1, 2), inode), payload(q, regions)

        def owners():
            return {(1, 2, 100 + (0 if role == "GLOBAL" else 4) + int(q[1])): {self.owner_of.get((role, q), OWNER)}
                    for role, q in self.held}

        for item in [
            patch.object(G, "safe_root", return_value=(1, 2)),
            patch.object(G, "ancestors", return_value={OWNER: (100, UID), 41235: (100, UID)}),
            patch.object(G, "proc_stat", return_value=(1, 100, UID)),
            patch.object(G, "proc_lock_owners", side_effect=owners),
            patch.object(G, "open_identity", side_effect=identity),
            patch.dict(os.environ, {"ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT": "1"}),
        ]:
            item.start()
            self.addCleanup(item.stop)
        os.environ.pop("GITNEXUS_WORKER_POOL_SIZE", None)


class OneQuarter(Base):
    def test_one_quarter_admitted_with_workers_1(self):
        self.assertEqual(G.admit(ONE), OWNER)

    def test_one_quarter_admitted_with_equals_spelling(self):
        self.assertEqual(G.admit(["--workers=1"]), OWNER)

    def test_one_quarter_denied_without_workers(self):
        with self.assertRaises(G.Refusal):
            G.admit(["--force"])

    def test_one_quarter_denied_bare_guard(self):
        with self.assertRaises(G.Refusal):
            G.admit()

    def test_one_quarter_denied_workers_2(self):
        with self.assertRaises(G.Refusal):
            G.admit(["--workers", "2"])

    def test_repeated_workers_denied(self):
        with self.assertRaises(G.Refusal):
            G.admit(["--workers", "1", "--workers", "1"])

    def test_malformed_workers_denied(self):
        for args in (["--workers"], ["--workers", "01"], ["--workers", "1", "--"], ["--workers-max", "1", "--workers", "1"]):
            with self.subTest(args=args), self.assertRaises(G.Refusal):
                G.admit(args)

    def test_env_pool_disagreeing_denied(self):
        os.environ["GITNEXUS_WORKER_POOL_SIZE"] = "4"
        self.addCleanup(os.environ.pop, "GITNEXUS_WORKER_POOL_SIZE", None)
        with self.assertRaises(G.Refusal):
            G.admit(ONE)

    def test_payload_must_name_held_quarter_only(self):
        self.payload_regions = G.QUADRANTS
        with self.assertRaises(G.Refusal):
            G.admit(ONE)

    def test_different_owners_denied(self):
        self.owner_of[("build", "q2")] = 41235
        with self.assertRaises(G.Refusal):
            G.admit(ONE)

    def test_placement_disabled_denied(self):
        os.environ["ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT"] = "0"
        with self.assertRaises(G.Refusal):
            G.admit(ONE)


class Mismatched(Base):
    held = {("GLOBAL", "q1"), ("build", "q2")}

    def test_mismatched_quarters_denied(self):
        with self.assertRaises(G.Refusal):
            G.admit(ONE)


class GlobalOnly(Base):
    held = {("GLOBAL", "q1")}

    def test_global_without_build_denied(self):
        with self.assertRaises(G.Refusal):
            G.admit(ONE)


class TwoQuarters(Base):
    held = {("GLOBAL", "q1"), ("build", "q1"), ("GLOBAL", "q2"), ("build", "q2")}

    def test_two_partial_quarters_denied(self):
        with self.assertRaises(G.Refusal):
            G.admit(ONE)


class WholeHost(Base):
    held = {(r, q) for r in ("GLOBAL", "build") for q in G.QUADRANTS}

    def test_whole_host_still_admits_default(self):
        self.assertEqual(G.admit(), OWNER)

    def test_whole_host_admits_workers_1(self):
        self.assertEqual(G.admit(ONE), OWNER)

    def test_whole_host_admits_multiworker(self):
        self.assertEqual(G.admit(["--workers", "8"]), OWNER)


class Main(unittest.TestCase):
    def test_usage_rejects_extra_without_separator(self):
        with patch.object(G.sys, "argv", ["g", "--repo", "app", "--workers", "1"]):
            self.assertEqual(G.main(), G.DENIED)


if __name__ == "__main__":
    unittest.main()
