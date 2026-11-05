"""Operator 2026-11-05 ("approve sub-quarters on q3 for gitnexus!"): `--workers 1` analyze admits on a q3
sub-quarter region-lock claim (LOCK_SH GLOBAL.q3 + build.q3, LOCK_EX cpu_core.N) whose cores contain this
process's whole affinity. Policy fixtures with patched /proc and lock seams; they do not prove a live grant.
"""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
spec = importlib.util.spec_from_file_location("gitnexus_guard_sq", SCRIPTS / "gitnexus-guard.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
UID = os.getuid()
OWNER = 51234
ONE = ["--skip-agents-md", "--workers", "1", "--force"]


def inode_of(name):
    parts = name.split(".")
    if parts[0] == "cpu_core":
        return 1000 + int(parts[1])
    role, q = parts[1], parts[2]
    return 100 + (0 if role == "GLOBAL" else 4) + int(q[1])


class Sub(unittest.TestCase):
    q = "q3"
    cores = (72, 73)
    affinity = {72, 73, 168, 169}

    def setUp(self):
        self.read = {("GLOBAL", self.q), ("build", self.q)}
        self.cores_held = set(self.cores)
        self.write_extra = set()
        self.aff = set(self.affinity)

        def identity(path):
            return (os.makedev(1, 2), inode_of(Path(path).name)), b""

        def owners(mode="WRITE"):
            if mode == "READ":
                return {(1, 2, 100 + (0 if r == "GLOBAL" else 4) + int(q[1])): {OWNER} for r, q in self.read}
            out = {(1, 2, 1000 + c): {OWNER} for c in self.cores_held}
            out.update({(1, 2, 100 + (0 if r == "GLOBAL" else 4) + int(q[1])): {OWNER} for r, q in self.write_extra})
            return out

        for item in [
            patch.object(G, "safe_root", return_value=(1, 2)),
            patch.object(G, "ancestors", return_value={OWNER: (100, UID), 51235: (100, UID)}),
            patch.object(G, "proc_stat", return_value=(1, 100, UID)),
            patch.object(G, "proc_lock_owners", side_effect=owners),
            patch.object(G, "open_identity", side_effect=identity),
            patch.object(G, "own_affinity", side_effect=lambda: set(self.aff)),
            patch.dict(os.environ, {"ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT": "1"}),
        ]:
            item.start()
            self.addCleanup(item.stop)
        os.environ.pop("GITNEXUS_WORKER_POOL_SIZE", None)

    def test_subquarter_q3_admitted(self):
        self.assertEqual(G.admit(ONE), OWNER)

    def test_workers_2_refused(self):
        with self.assertRaises(G.Refusal):
            G.admit(["--workers", "2"])

    def test_bare_guard_refused(self):
        with self.assertRaises(G.Refusal):
            G.admit()

    def test_pool_size_env_refused(self):
        os.environ["GITNEXUS_WORKER_POOL_SIZE"] = "2"
        self.addCleanup(os.environ.pop, "GITNEXUS_WORKER_POOL_SIZE", None)
        with self.assertRaises(G.Refusal):
            G.admit(ONE)

    def test_affinity_outside_claim_refused(self):
        self.aff = {72, 73, 74}
        with self.assertRaises(G.Refusal):
            G.admit(ONE)

    def test_affinity_on_gpu_thread_outside_claim_refused(self):
        self.aff = {72, 73, 184}
        with self.assertRaises(G.Refusal):
            G.admit(ONE)

    def test_no_claim_refused(self):
        self.read, self.cores_held = set(), set()
        with self.assertRaises(G.Refusal):
            G.admit(ONE)

    def test_core_locks_without_quarter_share_refused(self):
        self.read = {("GLOBAL", "q3")}
        with self.assertRaises(G.Refusal):
            G.admit(ONE)

    def test_owner_also_holding_core_outside_q3_refused(self):
        self.cores_held |= {5}
        with self.assertRaises(G.Refusal):
            G.admit(ONE)

    def test_placement_disabled_refused(self):
        os.environ["ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT"] = "0"
        with self.assertRaises(G.Refusal):
            G.admit(ONE)

    def test_cpus_allowed_parser(self):
        self.assertEqual(G.parse_cpu_list("72-73,168-169"), {72, 73, 168, 169})
        for bad in ("", "a", "3-1", "1-"):
            with self.subTest(bad=bad), self.assertRaises(G.Refusal):
                G.parse_cpu_list(bad)


class SubQ0(Sub):
    q, cores, affinity = "q0", (0, 1), {0, 1, 96, 97}

    def test_subquarter_q3_admitted(self):
        with self.assertRaises(G.Refusal):
            G.admit(ONE)


class SubQ1(SubQ0):
    q, cores, affinity = "q1", (24, 25), {24, 25}


class SubQ2(SubQ0):
    q, cores, affinity = "q2", (48, 49), {48, 49, 144, 145}


if __name__ == "__main__":
    unittest.main()
