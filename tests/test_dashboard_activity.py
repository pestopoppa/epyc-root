"""Tests for the hub's today's-activity counters (dashboard/server.py).

Pure-function tests over ``_parse_activity_log`` — no git or HTTP needed.
Run: ``python3 -m unittest tests.test_dashboard_activity``
"""
import unittest

from dashboard import server


SAMPLE = """\
commit:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
diff --git a/handoffs/active/foo.md b/handoffs/active/foo.md
index 1111111..2222222 100644
--- a/handoffs/active/foo.md
+++ b/handoffs/active/foo.md
@@ -1,4 +1,5 @@
-- [ ] port the kernel
+- [x] port the kernel ✅ 2026-07-05
+- [ ] validate on MI210
 narrative line that mentions [x] inline but is not a task
+Status: converged — prose only, no checkbox here
commit:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
diff --git a/handoffs/active/foo.md b/handoffs/active/foo.md
--- a/handoffs/active/foo.md
+++ b/handoffs/active/foo.md
@@ -10,2 +10,3 @@
+  * [X] nested star task, capital X
diff --git a/handoffs/completed/bar.md b/handoffs/completed/bar.md
--- a/handoffs/completed/bar.md
+++ b/handoffs/completed/bar.md
@@ -1 +1,2 @@
+prose appended to a completed handoff
"""


class ParseActivityLogTest(unittest.TestCase):
    def test_counts_commits_files_and_boxes(self):
        act = server._parse_activity_log(SAMPLE)
        self.assertEqual(act["commits"], 2)
        # foo.md counted once across two commits; bar.md once.
        self.assertEqual(act["handoffs_touched"], 2)
        # +[x] flip and +[X] nested star task; the +++ header and prose lines don't count.
        self.assertEqual(act["boxes_checked"], 2)
        self.assertEqual(act["boxes_added"], 1)

    def test_empty_log_is_all_zero(self):
        self.assertEqual(server._parse_activity_log(""), server._ACT_EMPTY)

    def test_prose_only_day_shows_zero_boxes(self):
        text = (
            "commit:cccccccccccccccccccccccccccccccccccccccc\n"
            "diff --git a/handoffs/active/foo.md b/handoffs/active/foo.md\n"
            "+Update (2026-07-05): W8 paired diagnostics recorded.\n"
        )
        act = server._parse_activity_log(text)
        self.assertEqual(act["commits"], 1)
        self.assertEqual(act["handoffs_touched"], 1)
        self.assertEqual(act["boxes_checked"], 0)
        self.assertEqual(act["boxes_added"], 0)

    def test_activity_today_live_shape(self):
        """Smoke the real git path: keys present, values non-negative ints."""
        act = server._activity_today()
        self.assertEqual(set(act), set(server._ACT_EMPTY))
        for v in act.values():
            self.assertIsInstance(v, int)
            self.assertGreaterEqual(v, 0)


if __name__ == "__main__":
    unittest.main()
