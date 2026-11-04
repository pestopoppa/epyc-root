import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

job = load("isolated_b4k_job", BASE / "job.py")
selector = load("isolated_selector", BASE / "select_run.py")

class SafetyTests(unittest.TestCase):
    def test_help_and_unknown_args_precede_check(self):
        with patch.object(job, "check", side_effect=AssertionError("check side effect")) as check:
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as help_exit:
                    job.main(["--help"])
                self.assertEqual(help_exit.exception.code, 0)
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as unknown_exit:
                    job.main(["--definitely-unknown"])
                self.assertEqual(unknown_exit.exception.code, 2)
            check.assert_not_called()

    def test_exact_complete_and_grant_positive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); runs = root / "out/runs"; run = runs / "20261104T160700Z"
            run.mkdir(parents=True); (run / "calls.jsonl").write_text("{}\n")
            grant = {"id":"job-1", "granted_at":"2026-11-04T16:06:00Z", "ended_at":"2026-11-04T16:08:00Z"}
            complete = {"grant_id":"job-1", "grant_started_at":grant["granted_at"], "run":str(run)}
            gp=root/"grant.json"; cp=root/"COMPLETE"
            gp.write_text(json.dumps(grant)); cp.write_text(json.dumps(complete))
            self.assertEqual(selector.select_run(root, cp, gp), run.resolve())

    def test_rejects_ungranted_or_ambiguous_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); runs=root/"out/runs"; selected=runs/"20261104T160700Z"
            selected.mkdir(parents=True); (selected/"calls.jsonl").write_text("{}\n")
            grant={"id":"job-1", "granted_at":"2026-11-04T16:06:00Z", "ended_at":"2026-11-04T16:08:00Z"}
            complete={"grant_id":"job-1", "grant_started_at":grant["granted_at"], "run":str(selected)}
            gp=root/"grant.json"; cp=root/"COMPLETE"
            gp.write_text(json.dumps(grant)); cp.write_text(json.dumps(complete))
            ungranted=runs/"20261104T160643Z"; ungranted.mkdir(); (ungranted/"calls.jsonl").write_text("{}\n")
            with self.assertRaisesRegex(ValueError, "exactly"):
                selector.select_run(root, cp, gp)
            ungranted.rename(runs/"20261104T160500Z")
            complete["run"] = str(runs/"20261104T160500Z")
            cp.write_text(json.dumps(complete))
            with self.assertRaisesRegex(ValueError, "outside grant window"):
                selector.select_run(root, cp, gp)

if __name__ == "__main__":
    unittest.main()
