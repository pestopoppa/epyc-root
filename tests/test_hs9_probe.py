import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock
import subprocess

spec = importlib.util.spec_from_file_location('hs9_probe', Path(__file__).resolve().parents[1] / 'scripts/harness/hs9_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def test_stale_prepared_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input'
            path.write_text('fixed')
            st = path.stat()
            record = dict(path=str(path), size=st.st_size, mtime_ns=st.st_mtime_ns,
                          inode=st.st_ino, device=st.st_dev)
            probe.verify_inputs([record])
            path.write_text('modified')
            with self.assertRaises(ValueError):
                probe.verify_inputs([record])

    def test_incomplete_trace_is_unknown_never_pass(self):
        evaluator = MagicMock()
        evaluator.evaluate.side_effect = ValueError('incomplete')
        score = probe.grade(evaluator, {'case': 'HS9-01'})
        self.assertEqual(score['verdict'], 'not_demonstrated')
        self.assertEqual(score['unknown'], 7)
        self.assertEqual(score['pass'], 0)

    def test_one_failed_requirement_prevents_feasibility(self):
        evaluator = MagicMock()
        evaluator.evaluate.return_value = {'order': 'pass', 'boundary': 'fail'}
        score = probe.grade(evaluator, {})
        self.assertEqual(score['verdict'], 'not_demonstrated')
        self.assertEqual(score['fail'], 1)

    def test_only_captured_child_is_killed_and_reaped(self):
        child = MagicMock()
        child.poll.side_effect = [None, -9]
        child.wait.side_effect = [subprocess.TimeoutExpired('own-child', 10), -9]
        probe.stop_child(child)
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
        self.assertEqual(child.wait.call_count, 2)


class RequirementSchemaTests(unittest.TestCase):
    def test_incomplete_denominators_match_independent_evaluator(self):
        evaluator = probe.load('hs9_evaluator_schema', Path(__file__).resolve().parents[1] / 'artifacts/hs9-probe/evaluator.py')
        for case, names in probe.REQUIREMENTS.items():
            with self.subTest(case=case):
                complete = dict(case=case, events=[], report={}, capture_complete=True, termination='final_report')
                self.assertEqual(set(evaluator.evaluate(complete)), set(names))
                incomplete = dict(complete, capture_complete=False)
                result = probe.grade(evaluator, incomplete)
                self.assertEqual(result['unknown'], len(names))
                self.assertEqual(set(result['checks'].values()), {'unknown'})
