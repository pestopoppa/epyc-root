#!/usr/bin/env python3
"""core.bare watcher: logs only false->true transitions, never writes the config."""
import json
import os
import sys
import tempfile
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS))
import watch_git_config as w  # noqa: E402

FALSE = "[core]\n\tbare = false\n"
TRUE = "[core]\n\tbare = true\n"


class Tests(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp(prefix="wgc-")
        self.cfg, self.log = os.path.join(d, "config"), os.path.join(d, "out", "events.log")
        open(self.cfg, "w").write(FALSE)

    def events(self):
        return [json.loads(x) for x in open(self.log)] if os.path.exists(self.log) else []

    def test_is_bare(self):
        for t, want in ((TRUE, True), (FALSE, False), ("[core]\n\tbare\n", True), ("[remote \"o\"]\n\tbare = true\n", False),
                        ("[core]\n\tbare = true\n\tbare = false\n", False), ("[CORE]\n\tBare = YES # x\n", True), ("", False)):
            self.assertEqual(w.is_bare(t), want, t)

    def test_flip_logged_once_with_content_and_config_untouched(self):
        st = {}
        w.scan([self.cfg], st, self.log, first=True)
        self.assertEqual(self.events(), [])
        open(self.cfg, "w").write(TRUE)
        before = os.stat(self.cfg).st_mtime_ns
        w.scan([self.cfg], st, self.log)
        w.scan([self.cfg], st, self.log)
        ev = self.events()
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]["event"], ev[0]["content"], ev[0]["file"]), ("became-true", TRUE, self.cfg))
        self.assertIsInstance(ev[0]["git_processes"], list)
        self.assertEqual(os.stat(self.cfg).st_mtime_ns, before)

    def test_false_then_true_again_refires(self):
        st = {}
        open(self.cfg, "w").write(TRUE)
        w.scan([self.cfg], st, self.log, first=True)
        open(self.cfg, "w").write(FALSE)
        w.scan([self.cfg], st, self.log)
        open(self.cfg, "w").write(TRUE)
        w.scan([self.cfg], st, self.log)
        self.assertEqual([e["event"] for e in self.events()], ["already-true-at-start", "became-true"])

    def test_missing_file_mid_rename_does_not_refire(self):
        st = {}
        open(self.cfg, "w").write(TRUE)
        w.scan([self.cfg], st, self.log, first=True)
        os.remove(self.cfg)
        w.scan([self.cfg], st, self.log)
        open(self.cfg, "w").write(TRUE)
        w.scan([self.cfg], st, self.log)
        self.assertEqual(len(self.events()), 1)

    def test_git_processes_lists_git_only(self):
        d = tempfile.mkdtemp()
        for pid, argv in (("11", b"git\0status\0"), ("12", b"/usr/bin/git-remote-https\0o\0"), ("13", b"python3\0git\0"), ("x", b"")):
            os.makedirs(f"{d}/{pid}")
            open(f"{d}/{pid}/cmdline", "wb").write(argv)
        self.assertEqual(sorted(p["pid"] for p in w.git_processes(d)), [11, 12])

    def test_main_polls(self):
        self.assertEqual(w.main(["--file", self.cfg, "--log", self.log, "--max-passes", "1"]), 0)


if __name__ == "__main__":
    unittest.main()
