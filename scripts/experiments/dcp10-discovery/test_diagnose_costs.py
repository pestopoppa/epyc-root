"""Controls for the slice-provenance distinctions in the retained replay."""
import unittest

from diagnose_costs import explain_slice


class ExplainSliceTests(unittest.TestCase):
    def test_missing_hit_ranges(self):
        self.assertEqual(explain_slice("a.py", "x = 1\n", [], [], True),
                         {"reason": "missing_hit_ranges"})

    def test_non_python(self):
        self.assertEqual(explain_slice("a.c", "int x;\n", [[1, 1]], [], True),
                         {"reason": "non_python"})

    def test_invalid_python(self):
        self.assertEqual(explain_slice("a.py", "def\n", [[1, 1]], [], True),
                         {"reason": "ast_parse_failure", "error_type": "SyntaxError", "error_line": 1})

    def test_parsed_window_with_uncovered_lines(self):
        self.assertEqual(explain_slice("a.py", "# header\n\nx = 1\n", [[1, 3]], [], True),
                         {"reason": "unresolved_ast_hit_lines", "hit_lines_without_ast_statement": [1, 2]})

    def test_window_outside_source(self):
        self.assertEqual(explain_slice("a.py", "x = 1\n", [[1, 2]], [], True),
                         {"reason": "hit_range_out_of_bounds"})

    def test_covered_decorator_is_distinct_from_blank_line(self):
        source = "@decorate\ndef f():\n    pass\n\n"
        self.assertEqual(explain_slice("a.py", source, [[1, 4]], [], True),
                         {"reason": "unresolved_ast_hit_lines", "hit_lines_without_ast_statement": [4]})

    def test_materialized_span_and_equal_estimate_are_distinct(self):
        source = "x = 1\ny = 2\n"
        self.assertEqual(explain_slice("a.py", source, [[1, 2]], [[1, 2]], False),
                         {"reason": "whole_file_ast_span"})
        self.assertEqual(explain_slice("a.py", source, [[1, 1]], [[1, 1]], True),
                         {"reason": "ast_slice_equal_estimate"})
        self.assertEqual(explain_slice("a.py", source, [[1, 1]], [[1, 1]], False),
                         {"reason": "ast_slice_distinct_estimate"})


if __name__ == "__main__":
    unittest.main()
