#!/usr/bin/env python3
"""Source-based checks for candidate selection, gold exclusion and tamper refusal."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import candidate_manifest as cm

DATASET = Path("/mnt/raid0/llm/epyc-inference-research/artifacts/architect-code-eval-20260724/swebench_verified.json")
SCRIPT = Path(cm.__file__).resolve()


class CandidateTests(unittest.TestCase):
    def test_source_selection_and_prompt_allowlist(self):
        artifacts = cm.artifacts(DATASET)
        self.assertEqual(artifacts, cm.artifacts(DATASET))
        rows = json.loads(DATASET.read_bytes())
        # Independently spell out the registered selection, without using rank().
        expected = sorted((hashlib.sha256(("epyc-p5-candidate-swe-verified-40-v1\x00" + r["instance_id"]).encode()).hexdigest(), r["instance_id"]) for r in rows)[:40]
        questions = json.loads(artifacts["questions.json"])
        manifest = json.loads(artifacts["manifest.eval-only.json"])
        self.assertEqual([i for _, i in expected], [q["id"] for q in questions])
        source = {r["instance_id"]: r for r in rows}
        for q, case in zip(questions, manifest["cases"]):
            self.assertEqual(set(q), {"id", "repo", "base_commit", "prompt"})
            self.assertEqual(q["prompt"], source[q["id"]]["problem_statement"])
            self.assertEqual(case["FAIL_TO_PASS"], cm.test_names(source[q["id"]]["FAIL_TO_PASS"]))
            self.assertEqual(case["PASS_TO_PASS"], cm.test_names(source[q["id"]]["PASS_TO_PASS"]))
        self.assertEqual(manifest["status"], "CANDIDATE_NOT_APPROVED")

    def test_changed_dataset_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "changed.json"
            path.write_bytes(b"[]\n")
            with self.assertRaisesRegex(ValueError, "pinned source"):
                cm.artifacts(path)

    def test_cli_roundtrip_overwrite_and_tamper_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "candidate"
            def run(command):
                return subprocess.run([sys.executable, str(SCRIPT), command, "--dataset", str(DATASET), "--directory", str(output)], capture_output=True, text=True)
            self.assertEqual(run("freeze").returncode, 0)
            self.assertEqual(run("verify").returncode, 0)
            self.assertNotEqual(run("freeze").returncode, 0)
            q = output / "questions.json"
            q.chmod(0o644)
            q.write_bytes(q.read_bytes() + b"\n")
            self.assertNotEqual(run("verify").returncode, 0)


if __name__ == "__main__":
    unittest.main()
