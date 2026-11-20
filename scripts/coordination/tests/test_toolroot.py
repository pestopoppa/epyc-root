#!/usr/bin/env python3
"""F5 (AK audit B5/C5): toolroot prints tool-commit, warns from a checkout > 50 commits behind origin/main, resolves
config from the hub view first; the churn tools call it at startup with no other behaviour change."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
_COORD = os.path.dirname(_TESTS)
sys.path.insert(0, _COORD)
import toolroot  # noqa: E402

GENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def git(cwd, *a):
    return subprocess.run(["git", "-C", cwd, *a], check=True, capture_output=True, env=GENV).stdout.decode().strip()


class ToolRoot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="toolroot-")
        up = os.path.join(cls.tmp, "up")
        os.makedirs(up)
        git(up, "init", "-q", "-b", "main")
        os.makedirs(os.path.join(up, "scripts"))
        open(os.path.join(up, "scripts", "tool.py"), "w").write("# tool\n")
        git(up, "add", ".")
        git(up, "commit", "-q", "-m", "c0")
        cls.first = git(up, "rev-parse", "HEAD")
        for i in range(60):
            git(up, "commit", "-q", "--allow-empty", "-m", f"c{i + 1}")
        cls.clone = os.path.join(cls.tmp, "clone")
        subprocess.run(["git", "clone", "-q", up, cls.clone], check=True, capture_output=True, env=GENV)
        git(cls.clone, "checkout", "-q", "--detach", cls.first)   # fixture clone only: pinned 60 commits behind
        cls.tool = os.path.join(cls.clone, "scripts", "tool.py")

    def setUp(self):
        self.cache = tempfile.mkdtemp(prefix="trcache-")
        self.hub = tempfile.mkdtemp(prefix="trhub-")
        self.p = [mock.patch.object(toolroot, "CACHE_DIR", self.cache), mock.patch.object(toolroot, "HUB", self.hub)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()

    def test_stale_checkout_warns_with_commit(self):
        err = io.StringIO()
        lines = toolroot.banner(self.tool, out=err)
        self.assertTrue(lines[0].startswith(f"tool-commit {self.first[:12]}"), lines)
        self.assertIn("WARN: checkout 60 commits behind origin/main; tools/config read from " + self.hub, err.getvalue())

    def test_behind_cached_per_hour(self):
        toolroot.banner(self.tool, out=io.StringIO())
        with mock.patch.object(toolroot, "_git", wraps=toolroot._git) as g:
            toolroot.behind(toolroot.checkout_root(self.tool))
        self.assertFalse(any("rev-list" in c.args for c in g.call_args_list))

    def test_fresh_checkout_no_warn(self):
        with mock.patch.object(toolroot, "behind", return_value=3):
            self.assertEqual(len(toolroot.banner(self.tool, out=io.StringIO())), 1)

    def test_deployed_json_wins(self):
        b = os.path.join(self.tmp, "flags", "bin")
        os.makedirs(os.path.join(b, "rowflow"), exist_ok=True)
        os.makedirs(os.path.join(b, "churn"), exist_ok=True)
        json.dump({"sha": "abcdef1234567890"}, open(os.path.join(b, "rowflow", "DEPLOYED.json"), "w"))
        for f in (os.path.join(b, "rowflow", "publish_row.py"), os.path.join(b, "churn", "file_result.py")):
            self.assertEqual(toolroot.tool_commit(f), ("abcdef1234567890", os.path.join(b, "rowflow", "DEPLOYED.json")))
            self.assertIn("deployed", toolroot.banner(f, out=io.StringIO())[0])

    def test_resolve_hub_first(self):
        rel = "coordination/session-bus/config.yaml"
        self.assertEqual(toolroot.resolve(rel, self.tool), os.path.join(self.clone, rel))
        os.makedirs(os.path.dirname(os.path.join(self.hub, rel)))
        open(os.path.join(self.hub, rel), "w").write("x")
        self.assertEqual(toolroot.resolve(rel, self.tool), os.path.join(self.hub, rel))

    def test_never_raises(self):
        with mock.patch.object(toolroot, "tool_commit", side_effect=RuntimeError("x")):
            self.assertEqual(toolroot.banner(self.tool, out=io.StringIO()), [])

    def test_file_result_and_session_bus_print_banner(self):
        sys.path.insert(0, os.path.join(_COORD, "churn"))
        import file_result
        import session_bus
        for fn, argv in ((file_result.main, ["no-such-row", "--flags", self.cache]),
                         (session_bus.main, ["--print-root"])):
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                fn(argv)
            self.assertIn("tool-commit ", err.getvalue())


if __name__ == "__main__":
    unittest.main()
