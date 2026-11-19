"""handoff_ref: one canonical key for x.md / handoffs/<state>/x.md / either with :TASK (pipeline audit 2026-11-10 #8)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import handoff_ref as hr  # noqa: E402


class HandoffRefTest(unittest.TestCase):
    def test_all_forms_reduce_to_one_file_and_key(self):
        for ref in ("x.md", "handoffs/active/x.md", "/handoffs/completed/x.md/", " x.md ", "handoffs/blocked/x.md"):
            self.assertEqual(hr.file_of(ref), "x.md", ref)
            self.assertEqual(hr.key(ref), "x.md", ref)
        for ref in ("x.md:ROW-1", "handoffs/active/x.md:ROW-1", "handoffs/archived/x.md: ROW-1 "):
            self.assertEqual(hr.file_of(ref), "x.md", ref)
            self.assertEqual(hr.key(ref), "x.md:ROW-1", ref)

    def test_state_only_when_spelled(self):
        self.assertEqual(hr.parse("handoffs/completed/x.md:T").state, "completed")
        self.assertIsNone(hr.parse("x.md:T").state)
        self.assertIsNone(hr.parse("docs/x.md").state)
        self.assertEqual(hr.parse("x.md:42").task, "42")

    def test_not_a_handoff(self):
        for ref in (None, "", "x.txt", "ROW-1", 7, "handoffs/active/"):
            self.assertIsNone(hr.file_of(ref), ref)
            self.assertIsNone(hr.key(ref), ref)

    def test_repo_path(self):
        self.assertEqual(hr.repo_path("x.md"), "handoffs/active/x.md")
        self.assertEqual(hr.repo_path("x.md:T"), "handoffs/active/x.md")
        self.assertEqual(hr.repo_path("handoffs/completed/x.md"), "handoffs/completed/x.md")
        self.assertEqual(hr.repo_path("docs/notes/x.md"), "docs/notes/x.md")
        self.assertIsNone(hr.repo_path("x.txt"))


if __name__ == "__main__":
    unittest.main()
