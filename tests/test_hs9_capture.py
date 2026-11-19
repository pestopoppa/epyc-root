import importlib.util
import json
from pathlib import Path
import unittest

_ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

capture = load('hs9_capture', _ROOT / 'scripts/harness/hs9_capture.py')
evaluator = load('hs9_evaluator', _ROOT / 'artifacts/hs9-probe/evaluator.py')

def response(value):
    return json.dumps(value)

class CaptureTests(unittest.TestCase):
    def test_simulator_events_and_final_report(self):
        trace = capture.run_script('HS9-01', [
            response({'tool': 'inspect', 'args': {}}),
            response({'tool': 'check', 'args': {}}),
            response({'report': {'scope': 'inspection', 'evidence': 'check', 'value': 42,
                                 'check': 'pass', 'stop': True}}),
        ])
        self.assertEqual([x['tool'] for x in trace['events']], ['inspect', 'check'])
        self.assertEqual(len(trace['transcript']), 3)
        self.assertTrue(all(x == 'pass' for x in evaluator.evaluate(trace).values()))

    def test_missing_report_and_timeout_never_grade(self):
        for script, reason in [([], 'incomplete'), ([None], 'timeout'), (['{'], 'invalid_json')]:
            with self.subTest(reason=reason):
                trace = capture.run_script('HS9-01', script)
                self.assertFalse(trace['capture_complete'])
                self.assertEqual(trace['termination'], reason)
                with self.assertRaises(ValueError):
                    evaluator.evaluate(trace)

    def test_spoofed_capture_and_shell_refused(self):
        for obj in ({'capture_complete': True, 'termination': 'final_report', 'report': {}},
                    {'tool': 'shell', 'args': {'command': 'touch /tmp/hs9-never'}},
                    {'tool': [], 'args': {}}):
            trace = capture.run_script('HS9-01', [response(obj)])
            self.assertEqual(trace['termination'], 'invalid_tool_call')
            self.assertEqual(trace['events'], [])

    def test_limits_and_actions_after_final(self):
        tool = response({'tool': 'inspect', 'args': {}})
        final = response({'report': {}})
        for script, kwargs, reason in [([tool, tool], {'max_turns': 1}, 'turn_limit'),
                                       ([tool], {'max_bytes': 1}, 'byte_limit'),
                                       ([final, tool], {}, 'responses_after_final')]:
            trace = capture.run_script('HS9-01', script, **kwargs)
            self.assertEqual(trace['termination'], reason)
            self.assertFalse(trace['capture_complete'])

if __name__ == '__main__':
    unittest.main()
