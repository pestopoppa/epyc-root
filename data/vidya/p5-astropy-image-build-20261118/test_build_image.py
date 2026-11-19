"""Exercise grant and receipt custody without invoking Docker builds."""

from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch


def load_runner():
    source = Path(__file__).with_name("build-image.py")
    spec = importlib.util.spec_from_file_location("build_image", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_runner()
IMAGE = "sha256:" + "a" * 64


class BuildCustodyTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.grant = self.root / "grants" / f"{runner.ROW}.grant"
        self.grant.parent.mkdir()
        now = int(time.time())
        self.end = now + 400
        stamp = lambda t: datetime.fromtimestamp(t, timezone.utc).isoformat()
        self.grant.write_text(
            f"regions=7-10 start={stamp(now - 20)} end={stamp(self.end)} "
            f"id={runner.ROW} kind=rowflow-dryrun\n"
        )
        self.result = self.root / "native-attempts/attempt-private/native-result.json"
        self.stop = self.root / "STOP"
        env = {
            "FILLER_ID": runner.ROW,
            "FILLER_NEEDGPU": "0",
            "FILLER_DRYRUN": "1",
            "FILLER_SMOKE": "1",
            "FILLER_DRYRUN_DIR": str(self.root),
            "FILLER_DRYRUN_RESULT_PATH": str(self.result),
            "FILLER_DEADLINE": str(self.end - 90),
            "FILLER_CPUS": "7-10",
            "FILLER_STOPFILE": str(self.stop),
        }
        for name in ("launch.sh", "SOURCE.sha256"):
            (self.root / name).write_text(name + "\n")
        for mock in (
            patch.dict(os.environ, env, clear=True),
            patch.object(runner, "ROOT", self.root),
            patch.object(os, "sched_getaffinity", return_value={7, 8, 9, 10}),
            patch.object(runner.signal, "signal"),
            patch.object(runner, "preflight"),
            patch.object(runner, "image_id", return_value=IMAGE),
            patch.object(runner, "build", side_effect=self.fake_build),
        ):
            mock.start()
            self.addCleanup(mock.stop)

    def fake_build(self, attempt, binding, _deadline):
        self.assertEqual(binding["build_cpus"], "7,8,9,10")
        (attempt / "build.log").write_text("original build output\n")
        (attempt / "image.iid").write_text(IMAGE + "\n")
        return IMAGE

    def test_completed_receipt_rechecks_originals(self):
        self.assertEqual(runner.capture(), 0)
        runner.complete()
        receipt = json.loads(self.result.read_bytes())
        log = Path(receipt["build_log"])
        self.assertEqual((log.parent / "rowflow.grant").read_bytes(), self.grant.read_bytes())
        self.assertFalse((self.root / "official/RESULT.json").exists())
        log.write_text("mutated\n")
        with self.assertRaisesRegex(ValueError, "original build custody"):
            runner.complete()

    def test_copy_of_terminal_is_refused(self):
        self.assertEqual(runner.capture(), 0)
        raw = self.result.read_bytes()
        self.result.unlink()
        self.result.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "original attempt"):
            runner.complete()

    def test_stop_preserves_unknown_and_grant(self):
        self.stop.touch()
        self.assertEqual(runner.capture(), 75)
        self.assertFalse(self.result.exists())
        terminal, = self.result.parent.glob("build-*/terminal.json")
        self.assertEqual(json.loads(terminal.read_bytes())["status"], "UNKNOWN")
        self.assertEqual((terminal.parent / "rowflow.grant").read_bytes(), self.grant.read_bytes())
        runner.build.assert_not_called()

    def test_affinity_mismatch_refuses_build(self):
        os.environ["FILLER_CPUS"] = "8-10"
        self.assertEqual(runner.capture(), 1)
        terminal, = self.result.parent.glob("build-*/terminal.json")
        self.assertIn("CPU placement refused", json.loads(terminal.read_bytes())["error"])
        runner.build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
