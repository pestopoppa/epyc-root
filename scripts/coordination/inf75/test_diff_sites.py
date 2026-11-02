import unittest

from diff_sites import DiffError, extract_changed_lines


PATCH = """diff --git a/a.c b/a.c
index 0000000..1111111 100644
--- a/a.c
+++ b/a.c
@@ -2,2 +2,3 @@
-old1
-old2
+new1
+new2
+new3
@@ -5,0 +7 @@
+added
"""


class DiffSitesTests(unittest.TestCase):
    def test_positions_and_insert_only_side(self):
        got = extract_changed_lines(PATCH)
        self.assertEqual(got["status"], "PARTIAL_UNVERIFIED")
        self.assertEqual(got["files"]["a.c"], {
            "anchor_lines": [2, 3], "candidate_lines": [2, 3, 4, 7]})

    def test_malformed_headers_and_hunks_refuse(self):
        for patch in (PATCH.replace("--- a/a.c", "--- a/other.c"),
                      PATCH.replace("--- a/a.c\n", ""),
                      PATCH.replace("@@ -5,0 +7 @@", "@@ -2,0 +4 @@"),
                      PATCH.replace("@@ -5,0 +7 @@\n+added", "@@ -5,0 +6,0 @@")):
            with self.subTest(patch=patch), self.assertRaises(DiffError):
                extract_changed_lines(patch)

    def test_lf_only_line_splitting(self):
        patch = PATCH.replace("-old1", "-old\v+still-old")
        self.assertEqual(extract_changed_lines(patch)["files"]["a.c"]["anchor_lines"], [2, 3])

    def test_unknown_or_truncated_input_refused(self):
        for patch in (PATCH.replace("+added\n", ""),
                      PATCH.replace("b/a.c", "b/renamed.c", 1),
                      PATCH.replace("-old1", " old1"),
                      "diff --git a/a b/a\nBinary files differ\n"):
            with self.subTest(patch=patch), self.assertRaises(DiffError):
                extract_changed_lines(patch)


if __name__ == "__main__":
    unittest.main()
