#!/usr/bin/env python3
"""Tests for REG-ENF-2: check_inference_region_claim.sh + inference_claim_scan.py.

Cases live in inference_region_claim_cases.json (not literals here) so this file's own
text never trips the hook it tests — the lesson of test_live_holder_interference.py.

Run: python3 -m pytest -q scripts/hooks/tests/test_inference_region_claim.py
"""
from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = HERE.parent / "check_inference_region_claim.sh"
CASES = json.loads((HERE / "inference_region_claim_cases.json").read_text())


def run(command, tool="Bash", env_extra=None, hook=HOOK, raw=None):
    env = {k: v for k, v in os.environ.items() if k != "EPYC_ALLOW_UNCLAIMED_INFERENCE"}
    env.update(env_extra or {})
    payload = raw if raw is not None else json.dumps(
        {"tool_name": tool, "tool_input": {"command": command}, "cwd": "/tmp"})
    return subprocess.run(["bash", str(hook)], input=payload, text=True,
                          capture_output=True, env=env, timeout=20)


class Cases(unittest.TestCase):
    def test_fixture_cases(self):
        self.assertGreaterEqual(len(CASES), 15)
        for c in CASES:
            with self.subTest(c["name"]):
                r = run(c["command"])
                want = 2 if c["expect"] == "block" else 0
                self.assertEqual(r.returncode, want, f"{c['name']}: rc={r.returncode} {r.stderr}")
                if want == 2:
                    self.assertIn("region claim", r.stderr)


class Posture(unittest.TestCase):
    BLOCK = next(c["command"] for c in CASES if c["expect"] == "block")

    def test_override_allows(self):
        self.assertEqual(run(self.BLOCK, env_extra={"EPYC_ALLOW_UNCLAIMED_INFERENCE": "1"}).returncode, 0)

    def test_other_tools_pass(self):
        self.assertEqual(run(self.BLOCK, tool="Write").returncode, 0)

    def test_unparsable_input_fails_open(self):
        self.assertEqual(run(None, raw="not json").returncode, 0)

    def test_scanner_missing_fails_closed_on_unambiguous_form(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            h = Path(d) / HOOK.name
            shutil.copy(HOOK, h)                      # no scanner beside it
            self.assertEqual(run(self.BLOCK, hook=h).returncode, 2)
            claimed = next(c["command"] for c in CASES if c["name"] == "flock cpu region wraps")
            self.assertEqual(run(claimed, hook=h).returncode, 0)
            self.assertEqual(run("ls -la", hook=h).returncode, 0)


if __name__ == "__main__":
    unittest.main()
