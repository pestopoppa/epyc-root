#!/usr/bin/env python3
"""Offline contract test against canonical research source and the real A1 log."""
import hashlib
import re
import subprocess
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO = "/mnt/raid0/llm/epyc-inference-research"
COMMIT = "1dae4bac89a4a4d23051cf8cc8b97366f36173c8"
ROOT = "scripts/benchmark/yarn_e1"
A1 = Path("/mnt/raid0/llm/tmp/yarn-e1-20261004/results/A1.server.log")
EXPECTED_A1 = "e9dc5d764371fcdfbcda04e2bc06a1c9ddb2519b264d2c144560ca9d15789806"


def source(path):
    return subprocess.check_output(["git", "-C", REPO, "show", f"{COMMIT}:{ROOT}/{path}"], stderr=subprocess.DEVNULL)


def load(name, path):
    module = types.ModuleType(name)
    module.__file__ = f"/tmp/canonical-yarn-source/{path}"
    sys.modules[name] = module
    exec(compile(source(path), module.__file__, "exec"), module.__dict__)
    return module


class CanonicalProofTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = load("yarn_proof", "yarn_proof.py")
        cls.needle = load("yarn_needle", "yarn_needle.py")
        load("cpu_window_gate", "cpu_leg/cpu_window_gate.py")
        cls.cpu = load("yarn_cpu_leg", "cpu_leg/yarn_cpu_leg.py")

    def test_real_a1_preflight_without_force(self):
        self.assertEqual(hashlib.sha256(A1.read_bytes()).hexdigest(), EXPECTED_A1)
        self.assertEqual(hashlib.sha256(source("tests/fixtures/A1.server.log")).hexdigest(), EXPECTED_A1)
        yn = self.needle
        read_bytes, read_text = Path.read_bytes, Path.read_text
        def mock_bytes(path):
            if str(path) == "/proc/424242/environ": return b"LD_LIBRARY_PATH=/store\0"
            if str(path) == "/proc/424242/cmdline": return b"llama-server\0--rope-scaling\0yarn\0"
            return read_bytes(path)
        def mock_text(path, *args, **kwargs):
            if str(path) == "/proc/424242/maps": return "/store/gpu-20260921-ffc1bac82/libggml-hip.so\n"
            return read_text(path, *args, **kwargs)
        def http(url, **kwargs):
            return (200, [{"n_ctx": 524288}]) if url.endswith("/slots") else (200, {"n_ctx": 524288})
        args = SimpleNamespace(port=18083, arm="A1", server_log=str(A1))
        with patch.object(yn, "port_pid", side_effect=lambda port: None if port == 8083 else 424242), patch.object(yn, "http_json", side_effect=http), patch.object(yn, "kfd_gib", return_value=30.0), patch.object(Path, "read_bytes", mock_bytes), patch.object(Path, "read_text", mock_text):
            result = yn.preflight(args, "http://fixture")
        self.assertEqual(result["problems"], [])
        self.assertTrue(all(result["proof"].values()))

    def test_split_is_local_and_last_launch_only(self):
        pattern = r"Using metadata override \(\s*str\) 'a' = yarn"
        for split in ("0.00.597.049 I ", "\n0.00.597.049 I ", "\n"):
            self.assertTrue(self.proof.check_proof("Using metadata override ( str) 'a' = " + split + "yarn", [pattern], [])["ok"])
        self.assertFalse(self.proof.check_proof("Using metadata override ( str) 'a' =\nunrelated\nyarn", [pattern], [])["ok"])
        self.assertFalse(self.proof.check_proof("=== launch old\nMATCH\n=== launch new\nmissing", ["MATCH"], [])["ok"])

    def test_consumers_and_launch_flags(self):
        self.assertIs(self.needle.check_proof, self.proof.check_proof)
        self.assertIs(self.cpu.check_proof, self.proof.check_proof)
        self.assertEqual(self.proof.PROOF_LOG_FLAGS, ["--verbosity", "4"])
        self.assertIn(b"*PROOF_LOG_FLAGS", source("cpu_leg/yarn_cpu_leg.py"))
        self.assertIn(b'"$D/yarn_proof.py" --log-flags', source("launch_arm.sh"))


if __name__ == "__main__":
    unittest.main()
