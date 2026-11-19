import unittest
from gcov_sites import CaptureError, extract_sites

REPORT = """        -:    0:Source:/src/ggml-cpu.c
       12:   10:if (x) {
branch  0 taken 9 (fallthrough)
branch  1 taken 3
    #####:   11:body();
        -:   12:}
"""
SITES = {"branch": {"line": 10, "predicate": True}, "body": {"line": 11, "predicate": False}}


class GcovTests(unittest.TestCase):
    def test_count_form_is_partial_only(self):
        result = extract_sites(REPORT, expected_source="/src/ggml-cpu.c", sites=SITES)
        self.assertEqual(result["status"], "PARTIAL_UNVERIFIED")
        self.assertEqual(result["sites"]["branch"]["branches"], [9, 3])
        self.assertEqual(result["sites"]["body"]["line_count"], 0)

    def test_missing_ambiguous_and_percentages_refuse(self):
        for report, source, sites in (
            (REPORT, "/wrong", SITES),
            (REPORT.replace("branch  1 taken 3\n", ""), "/src/ggml-cpu.c", SITES),
            (REPORT.replace("taken 9", "taken 75%"), "/src/ggml-cpu.c", SITES),
            (REPORT, "/src/ggml-cpu.c", {"missing": {"line": 12, "predicate": False}}),
        ):
            with self.subTest(report=report, sites=sites), self.assertRaises(CaptureError):
                extract_sites(report, expected_source=source, sites=sites)
