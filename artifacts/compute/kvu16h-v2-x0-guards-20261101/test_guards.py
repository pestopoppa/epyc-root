#!/usr/bin/env python3
"""Offline structural tests of the fail-closed drafts; no server or inference."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def function(name, symbol):
    tree = ast.parse((ROOT / name).read_text())
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == symbol)

def code(node):
    return ast.unparse(node)

class GuardTests(unittest.TestCase):
    def test_p3_direct_paths_refuse_first(self):
        for symbol in ('phase_a1', 'measure_level'):
            self.assertIsInstance(function('p3_kvu_probe_v2.py', symbol).body[0], ast.Raise)

    def test_p3_cli_refuses_before_side_effects(self):
        body = function('p3_kvu_probe_v2.py', 'main').body
        texts = list(map(code, body))
        parse = next(i for i, s in enumerate(texts) if 'ap.parse_args()' in s)
        self.assertIn("a.phase in ('all', 'a1')", texts[parse + 1])
        self.assertIn('ap.error', texts[parse + 1])
        self.assertGreater(next(i for i,s in enumerate(texts) if 'a.dry_run' in s), parse + 1)

    def test_x0_probe_refuses_and_direct_request_guarded(self):
        body = function('probe_decode_x0.py', 'main').body
        texts = list(map(code, body))
        parse = next(i for i,s in enumerate(texts) if 'ap.parse_args()' in s)
        self.assertIn('ap.error', texts[parse + 1])
        guard = code(function('probe_decode_x0.py', 'stream_chat').body[0])
        self.assertIn("body.get('speculative.n_max') == 0", guard)
        self.assertIn('raise RuntimeError', guard)

    def test_outer_guard_before_reading_or_launch(self):
        body = function('x0_shape_b.py', 'main').body
        texts = list(map(code, body))
        parse = next(i for i,s in enumerate(texts) if 'ap.parse_args()' in s)
        self.assertIn('a.with_probe', texts[parse + 1])
        self.assertIn('ap.error', texts[parse + 1])
        self.assertIn('src_path', texts[parse + 2])

if __name__ == '__main__':
    unittest.main()
