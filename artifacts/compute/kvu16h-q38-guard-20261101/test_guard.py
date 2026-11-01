#!/usr/bin/env python3
"""Offline structural and isolated behavior checks; never starts inference."""
import argparse
import ast
import copy
from pathlib import Path
import unittest

PATH = Path(__file__).with_name('q38_t7.guarded.py')
TREE = ast.parse(PATH.read_text())


class GuardTest(unittest.TestCase):
    def test_direct_phase_calls_refuse_before_work(self):
        for name, args in [('phase_a', [None, None]), ('phase_b', [None] * 6)]:
            fn = copy.deepcopy(next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == name))
            self.assertIsInstance(fn.body[0], ast.Raise)
            fn.returns = None
            for arg in fn.args.args:
                arg.annotation = None
            mod = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
            ns = {}
            exec(compile(mod, str(PATH), 'exec'), ns)
            with self.assertRaisesRegex(RuntimeError, 'KVU-16h'):
                ns[name](*args)

    def test_cli_guard_is_early_and_precise(self):
        main = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        idx = next(i for i, n in enumerate(main.body) if isinstance(n, ast.If) and 'phases &' in ast.unparse(n.test))
        self.assertEqual(ast.unparse(main.body[idx - 1].targets[0]), 'phases')
        guard = ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(main.body[idx])], type_ignores=[]))
        code = compile(guard, str(PATH), 'exec')
        for phases in ({'A'}, {'B'}, {'A', 'C'}, {'B', 'C'}):
            with self.assertRaises(SystemExit):
                exec(code, {'phases': phases, 'ap': argparse.ArgumentParser()})
        for phases in ({'C'}, set()):
            exec(code, {'phases': phases, 'ap': argparse.ArgumentParser()})

if __name__ == '__main__':
    unittest.main()
