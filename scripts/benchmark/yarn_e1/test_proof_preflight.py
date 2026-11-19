#!/usr/bin/env python3
"""Boundary tests for the live checker, not a repeat of the matcher tests."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import proof_preflight as checker


class LiveCheckerTests(unittest.TestCase):
    def run_case(self, preflight):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "server.log"
            log.write_text("historical evidence must remain unchanged")
            output = Path(tmp) / "result.json"
            def inspect(args, base):
                self.assertFalse(hasattr(args, "force_preflight"))
                self.assertEqual(base, "http://127.0.0.1:18083")
                return preflight()
            with contextlib.redirect_stdout(io.StringIO()):
                rc = checker.main(["--arm", "A1", "--server-log", str(log),
                                   "--output", str(output)],
                                  loader=lambda repo: SimpleNamespace(preflight=inspect))
            self.assertEqual(log.read_text(), "historical evidence must remain unchanged")
            return rc, json.loads(output.read_text())

    def test_live_problems_refuse_even_with_complete_log_proof(self):
        rc, result = self.run_case(lambda: {"proof": {"metadata": True},
                                           "problems": ["server PID is not a KFD process"]})
        self.assertEqual(rc, 3)
        self.assertFalse(result["ok"])

    def test_full_preflight_pass(self):
        rc, result = self.run_case(lambda: {"proof": {"metadata": True}, "problems": []})
        self.assertEqual(rc, 0)
        self.assertEqual(result["source_commit"], checker.SOURCE_COMMIT)

    def test_unavailable_host_inspection_refuses(self):
        def unavailable():
            raise FileNotFoundError("ss unavailable")
        rc, result = self.run_case(unavailable)
        self.assertEqual(rc, 3)
        self.assertIn("FileNotFoundError", result["error"])

    def test_source_uses_git_object_and_restores_import_state(self):
        prior = SimpleNamespace(marker=True)
        helper = b"def check_proof(): return 'pinned'\n"
        runner = b"from yarn_proof import check_proof\n"
        with patch.dict(sys.modules, {"yarn_proof": prior}):
            with patch.object(checker.subprocess, "check_output", side_effect=[helper, runner]) as call:
                module = checker.load_runner("/example/research")
            self.assertIs(sys.modules["yarn_proof"], prior)
            self.assertEqual(module.check_proof(), "pinned")
            for item in call.call_args_list:
                self.assertIn(checker.SOURCE_COMMIT + ":" + checker.SOURCE_ROOT, item.args[0][-1])

    def test_existing_output_refused_without_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "prior.json"
            output.write_text("keep")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                checker.main(["--arm", "A1", "--server-log", "/unused", "--output", str(output)],
                             loader=lambda repo: self.fail("must refuse before loading"))
            self.assertEqual(output.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
