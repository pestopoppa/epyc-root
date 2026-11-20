"""Offline clock/transport controls: no server, model, cohort exposure or sleep."""
import ast
import hashlib
import pathlib
import unittest

from ifbench_capture_budget import can_expose, capture_response, request_seconds
from ifbench_timeout_repair import repair, SOURCE_SHA256


class BudgetTests(unittest.TestCase):
    def test_slow_progress_completes_after_old_timeout(self):
        timeout = request_seconds(4096)
        self.assertEqual(timeout, 8312)
        elapsed = 120 + 4096 / 1.12
        self.assertGreater(elapsed, 1200)
        calls = []

        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return b'{"choices":[{"finish_reason":"stop"}]}'

        def opener(request, *, timeout):
            calls.append((request, timeout))
            if elapsed >= timeout:
                raise TimeoutError('simulated wall timeout')
            return Response()

        with self.assertRaises(TimeoutError):
            capture_response('http://localhost', {'max_tokens': 4096}, 1200, opener=opener)
        status, raw = capture_response('http://localhost', {'max_tokens': 4096}, timeout, opener=opener)
        self.assertEqual(status, 200)
        self.assertIn(b'"stop"', raw)
        self.assertEqual(len(calls), 2)  # one call per explicit invocation
        self.assertEqual(calls[-1][0].method, 'POST')
        self.assertTrue(can_expose(0, timeout + 31, timeout))

    def test_deadline_refuses_exposure_without_full_reserve(self):
        timeout = request_seconds(4096)
        for remaining in (1200, timeout, timeout + 29, timeout + 30):
            self.assertFalse(can_expose(100, 100 + remaining, timeout))
        self.assertTrue(can_expose(100, 100 + timeout + 31, timeout))
        self.assertFalse(can_expose(100, 200, 120))  # smoke also reserves cleanup

    def test_capture_errors_propagate_once(self):
        calls = []
        def opener(*args, **kwargs):
            calls.append(1)
            raise TimeoutError('no progress within declared budget')
        with self.assertRaises(TimeoutError):
            capture_response('http://localhost', {}, request_seconds(4096), opener=opener)
        self.assertEqual(calls, [1])

    def test_invalid_token_cap(self):
        for value in (0, -1, True, 4.5, '4096'):
            with self.assertRaises(ValueError):
                request_seconds(value)

    def test_unreviewed_worker_rejected(self):
        with self.assertRaises(ValueError):
            repair(b'import os\n')

    def test_pinned_worker_integration_offline(self):
        path = pathlib.Path('/mnt/raid0/llm/tmp/canonical-judge-suite-revamp/ifbench-v3-cj6a-20261104/worker.py')
        if not path.exists():
            self.skipTest('pinned external worker unavailable')
        original = path.read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), SOURCE_SHA256)
        changed = repair(original).decode()
        tree = ast.parse(changed)
        nodes = list(ast.walk(tree))
        # Admission precedes the original exposure write; exact same timeout goes to transport.
        self.assertLess(changed.index('not can_expose('), changed.index('   atom(ep,'))
        self.assertIn("request_timeout=request_seconds(decoding['max_tokens'])", changed)
        self.assertIn("'request_timeout_s':request_timeout", changed)
        request = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == 'request')
        state = {}
        def transport(url, payload, timeout):
            self.assertEqual(timeout, 8312)
            return 200, b'complete'
        namespace = dict(state=state, capture_response=transport, url='http://localhost',
                         payload={'max_tokens': 4096}, request_timeout=8312)
        exec(compile(ast.Module(body=[request], type_ignores=[]), '<request>', 'exec'), namespace)
        namespace['request']()
        self.assertEqual(state, {'status': 200, 'raw': b'complete'})
        # All existing UNKNOWN/no-redraw paths remain byte-for-byte in place.
        for line in original.decode().splitlines():
            if 'no redraw' in line or 'without redraw' in line or "if ep.exists():" in line:
                self.assertIn(line, changed)
        self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
