"""Exercise the actual disabled integrated driver's cell under model-free fakes."""
import ast
import hashlib
from pathlib import Path
from unittest.mock import patch
import test_patched_driver_cell as base

SOURCE = Path(__file__).resolve().parent / 'driver.py'
PIN = '48af88fa8e293efde5fbe1b2bf3112500d85f1c25bfab9ac03420d86ddb7b741'


def integrated_cell(namespace):
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN:
        raise ValueError('integrated driver drift')
    tree = ast.parse(raw)
    item = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'item3')
    cell = next(n for n in item.body if isinstance(n, ast.FunctionDef) and n.name == 'cell')
    exec(compile(ast.Module(body=[cell], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['cell']


class IntegratedActualCell(base.ActualCell):
    def test_stop_refusal_aborts_and_records(self):
        self.assertIsNone(super().test_stop_refusal_aborts_and_records())

    def setUp(self):
        self.override = patch.object(base, 'patched_cell', integrated_cell)
        self.override.start()
        self.addCleanup(self.override.stop)

if __name__ == '__main__':
    import unittest
    unittest.main()
