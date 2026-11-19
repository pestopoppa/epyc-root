"""Model-free exit-boundary controls; process execution and draining are mocked."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('cafe3_supervise', Path(__file__).with_name('supervise.py'))
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


class ExitTest(unittest.TestCase):
    def exercise(self, reasons, child_rc=0, children=(), drain_error=None):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / 'exit.json'
            proc = Mock()
            proc.poll.return_value = child_rc
            def drain(_proc):
                # Evidence must be durable even if termination itself fails.
                self.assertEqual(json.loads(report.read_text())['drain'], 'pending')
                if drain_error:
                    raise RuntimeError(drain_error)
            with patch.object(s, 'stop_reason', side_effect=reasons), patch.object(s.subprocess, 'Popen', return_value=proc) as spawn, patch.object(s, 'children_of', return_value=set(children)), patch.object(s, 'drain', side_effect=drain) as drained:
                if drain_error:
                    with self.assertRaisesRegex(RuntimeError, drain_error):
                        s.supervise(['compiler'], 'STOP', 999, report)
                    rc = None
                else:
                    rc = s.supervise(['compiler'], 'STOP', 999, report)
                return rc, json.loads(report.read_text()), spawn.call_count, drained.call_count

    def test_clean_and_failed_command(self):
        for code in (0, 1, 75, -9):
            with self.subTest(code=code):
                rc, r, _, calls = self.exercise([None, None, None], code)
                self.assertEqual(rc, code)
                self.assertEqual(r['reason'], 'command-exit')
                self.assertEqual(r['child_rc'], code)
                self.assertEqual(calls, 0)

    def test_prelaunch_refusals_do_not_spawn(self):
        for cause in ('signal', 'stop-file', 'deadline'):
            rc, r, calls, _ = self.exercise([cause])
            self.assertEqual((rc, r['reason'], calls), (75, cause, 0))

    def test_stop_during_command_and_at_exit(self):
        for causes in ([None, 'stop-file'], [None, None, 'deadline']):
            rc, r, _, calls = self.exercise(causes, children=(123,))
            self.assertEqual(rc, 75)
            self.assertEqual(r['reason'], causes[-1])
            self.assertEqual((r['drain'], calls), ('complete', 1))

    def test_leftovers_fail_even_after_successful_link(self):
        rc, r, _, calls = self.exercise([None, None, None], children=(123, 124))
        self.assertEqual((rc, r['child_rc'], r['reason']), (75, 0, 'leftover-descendants'))
        self.assertEqual(r['captured_children'], [123, 124])
        self.assertEqual((r['drain'], calls), ('complete', 1))

    def test_drain_failure_keeps_attribution(self):
        _, r, _, _ = self.exercise([None, None, None], children=(123,), drain_error='timeout')
        self.assertEqual((r['reason'], r['drain'], r['error']), ('leftover-descendants', 'failed', 'timeout'))

    def test_real_stop_reason_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            stop = Path(tmp) / 'STOP'
            with patch.object(s, 'requested', False), patch.object(s.time, 'time', return_value=10):
                self.assertEqual(s.stop_reason(stop, 9), 'deadline')
                self.assertIsNone(s.stop_reason(stop, 11))
                stop.touch()
                self.assertEqual(s.stop_reason(stop, 11), 'stop-file')
                with patch.object(s, 'requested', True):
                    self.assertEqual(s.stop_reason(stop, 11), 'signal')


if __name__ == '__main__':
    unittest.main()
