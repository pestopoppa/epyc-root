#!/usr/bin/env python3
"""publish_row refreshes the hub view (refresh_hub_view.sh) once before reading handoff boxes (2026-11-15).

A stale view missing a box gets it after the refresh; a failing refresh warns and the publish continues;
ROWFLOW_NO_VIEW_REFRESH=1 and a ROWFLOW_REPO that is not the view both skip the refresh."""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402

HANDOFF = "view-refresh-test.md"
BOX = "- [ ] VRT-1 run the view refresh probe"


def git(cwd, *a):
    subprocess.run(["git", "-C", cwd, *a], check=True, capture_output=True, text=True)


class ViewRefresh(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="vr-")
        self.origin = os.path.join(self.d, "origin.git")
        seed, self.view = os.path.join(self.d, "seed"), os.path.join(self.d, "view")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.origin], check=True)
        subprocess.run(["git", "clone", "-q", self.origin, seed], check=True, capture_output=True)
        for k, v in (("user.email", "t@t"), ("user.name", "t")):
            git(seed, "config", k, v)
        os.makedirs(os.path.join(seed, "handoffs", "active"))
        self.md = os.path.join(seed, "handoffs", "active", HANDOFF)
        with open(self.md, "w") as f:
            f.write("# t\n\n- [x] VRT-0 done\n")
        git(seed, "add", "."); git(seed, "commit", "-q", "-m", "seed"); git(seed, "push", "-q", "origin", "HEAD:main")
        subprocess.run(["git", "clone", "-q", self.origin, self.view], check=True, capture_output=True)
        open(os.path.join(self.view, ".epyc-view-readonly"), "w").close()
        with open(self.md, "a") as f:  # the box lands on origin/main AFTER the view was cloned: the view is stale
            f.write(BOX + "\n")
        git(seed, "commit", "-qam", "box"); git(seed, "push", "-q", "origin", "HEAD:main")
        self.env = mock.patch.dict(os.environ, {"ROWFLOW_HUB_VIEW": self.view, "HUB_VIEW_SKIP_REGEN": "1",
                                                "HUB_VIEW_REGEN_GATE": "/nonexistent", "HUB_VIEW_QUIET_HOST": "/nonexistent"})
        self.env.start()
        os.environ.pop("ROWFLOW_NO_VIEW_REFRESH", None)
        os.environ.pop("ROWFLOW_VIEW_REFRESH_SCRIPT", None)

    def tearDown(self):
        self.env.stop()
        subprocess.run(["rm", "-rf", self.d])

    def view_text(self):
        with open(os.path.join(self.view, "handoffs", "active", HANDOFF)) as f:
            return f.read()

    def test_stale_view_gets_box_after_refresh(self):
        self.assertNotIn("VRT-1", self.view_text())
        self.assertTrue(pr.refresh_view(self.view))
        self.assertIn(BOX, self.view_text())

    def test_opt_out_honoured(self):
        os.environ["ROWFLOW_NO_VIEW_REFRESH"] = "1"
        self.assertFalse(pr.refresh_view(self.view))
        self.assertNotIn("VRT-1", self.view_text())

    def test_repo_elsewhere_not_refreshed(self):
        other = os.path.join(self.d, "elsewhere")
        os.makedirs(other)
        self.assertFalse(pr.refresh_view(other))
        self.assertNotIn("VRT-1", self.view_text())

    def _failing(self, body):
        p = os.path.join(self.d, "fail.sh")
        with open(p, "w") as f:
            f.write("#!/bin/bash\n" + body + "\n")
        os.environ["ROWFLOW_VIEW_REFRESH_SCRIPT"] = p

    def test_refresh_failure_warns_and_returns(self):
        self._failing("echo boom-refresh >&2; exit 1")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertFalse(pr.refresh_view(self.view))
        self.assertIn("boom-refresh", err.getvalue())
        self.assertIn("WARN view refresh failed", err.getvalue())

    def test_refresh_timeout_warns(self):
        self._failing("sleep 5")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertFalse(pr.refresh_view(self.view, timeout=1))
        self.assertIn("timed out", err.getvalue())

    def test_refresh_failure_does_not_block_publish(self):
        self._failing("exit 1")
        spec = os.path.join(self.d, "spec.json")
        with open(spec, "w") as f:
            f.write('{"id": "vrt-1", "owner": "t", "estimate_s": 600}')
        reached = []
        with mock.patch.object(pr, "REPO", self.view), \
                mock.patch.object(pr, "check_handoff", side_effect=lambda s: reached.append(s) or (_ for _ in ()).throw(SystemExit(7))), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                pr.main([spec])
        self.assertEqual(len(reached), 1)  # publish went on to the box checks after the failed refresh


if __name__ == "__main__":
    unittest.main()
