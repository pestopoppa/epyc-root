"""The publish rehearsal is static and uses the real launcher inputs."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rowflow"))
import publish_row as pr


class PublishRehearsal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.engine = self.root / "filler_run15.sh"
        self.engine.write_text("#!/bin/sh\n")
        self.server = self.root / "llama-server"
        self.server.write_text("#!/bin/sh\n")
        self.server.chmod(0o755)
        self.model = self.root / "missing.gguf"
        self.job = self.root / "job.py"
        self.job.write_text(f"SERVER_ARGV = {[str(self.server), '--model', str(self.model)]!r}\n")
        self.launch = self.root / "launch.sh"
        self.launch.write_text(
            f'#!/bin/bash\nexec bash {self.engine} --id fixture --class cpu '
            f'--min-window 300 --stop {self.root}/STOP --workdir {self.root} '
            f'--complete-cmd "true" --cmd "python3 {self.job}"\n')
        self.spec = {"id": "fixture", "launcher": str(self.launch), "owner": "fixture"}
        self.flags = str(self.root / "flags")

    def test_enforced_missing_model_refuses_publish_before_smoke(self):
        specfile = self.root / "spec.json"
        specfile.write_text(json.dumps(self.spec))
        with mock.patch.object(pr, "PUBLISH_REHEARSAL", "enforce"), \
             mock.patch.object(pr, "_toolroot_banner"), \
             mock.patch.object(pr, "route_rerank", return_value=False), \
             mock.patch.object(pr, "check_operator_gate"), \
             mock.patch.object(pr, "check_owner_roster"), \
             mock.patch.object(pr, "refresh_view"), \
             mock.patch.object(pr, "check_handoff"), \
             mock.patch.object(pr, "check_task_lint"), \
             mock.patch.object(pr, "lint", return_value=[]), \
             mock.patch.object(pr, "check_supersedes"), \
             mock.patch.object(pr, "publish_smoked") as publish, \
             mock.patch.object(pr.subprocess, "Popen", side_effect=AssertionError("must not launch")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            rc = pr.main([str(specfile), "--flags", self.flags])
        self.assertEqual(rc, 2)
        self.assertIn("publish-rehearsal", output.getvalue())
        self.assertIn("missing.gguf", output.getvalue())
        publish.assert_not_called()

    def test_warn_records_missing_model_and_enforce_accepts_valid_inputs(self):
        with mock.patch.object(pr, "PUBLISH_REHEARSAL", "warn"), contextlib.redirect_stdout(io.StringIO()):
            pr.publish_rehearsal(self.spec, self.flags)
        self.assertTrue(any("missing.gguf" in w for w in self.spec["publish_warnings"]))
        self.model.write_bytes(b"fixture")
        with mock.patch.object(pr, "PUBLISH_REHEARSAL", "enforce"):
            pr.publish_rehearsal(self.spec, self.flags)

    def test_checksum_env_and_argv_defects_are_reported(self):
        self.model.write_bytes(b"fixture")
        self.launch.write_text(self.launch.read_text() + '\n: "${REHEARSAL_REQUIRED:?required}"\n')
        self.job.write_text(f"SERVER_ARGV = {[str(self.server), '--model']!r}\n")
        (self.root / "SOURCE.sha256").write_text(hashlib.sha256(b"old").hexdigest() + "  job.py\n")
        with mock.patch.object(pr, "PUBLISH_REHEARSAL", "warn"), contextlib.redirect_stdout(io.StringIO()):
            pr.publish_rehearsal(self.spec, self.flags)
        warnings = "\n".join(self.spec["publish_warnings"])
        self.assertIn("SOURCE.sha256 mismatch", warnings)
        self.assertIn("REHEARSAL_REQUIRED", warnings)
        self.assertIn("missing value", warnings)


if __name__ == "__main__":
    unittest.main()
