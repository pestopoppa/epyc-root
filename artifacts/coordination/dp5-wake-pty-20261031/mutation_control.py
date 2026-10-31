"""Remove only the real helper's wake send; the positive PTY contract must fail."""
import ast
import importlib.util
import inspect
from pathlib import Path
import unittest
D = Path(__file__).parent
ROOT = D.parents[2]
spec = importlib.util.spec_from_file_location('dp5_test', ROOT / 'scripts/coordination/tests/test_dp5_wake_pty.py')
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)
source = inspect.getsource(tests.adapter._press_key_with_wake)
module = ast.parse(source)
removed = 0
for node in ast.walk(module):
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
        call = node.value
        if isinstance(call.func, ast.Name) and call.func.id == '_tmux' and isinstance(call.args[-1], ast.Constant) and call.args[-1].value == ' ':
            node.value = ast.Tuple(elts=[ast.Constant(0), ast.Constant('')], ctx=ast.Load())
            removed += 1
assert removed == 1
ast.fix_missing_locations(module)
exec(compile(module, 'DP5-wake-send-removed', 'exec'), tests.adapter.__dict__)
result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([tests.WakeTests('test_actual_wake_submit_consumes_and_records_exact_space')]))
assert len(result.failures) == 1 and not result.errors, 'wake removal must fail positive PTY contract'
print('EXPECTED MUTATION RED: wake removal fails actual-helper PTY submission assertion')
