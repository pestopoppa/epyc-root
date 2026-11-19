"""Captured debugger teardown: real child exits and bounded refusal controls."""
import signal
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

import cleanup
from gdb_job import stop_debugger


class DebuggerStopTests(unittest.TestCase):
    def child(self, ignore_term=False):
        code = (
            'import signal\n'
            + ('signal.signal(signal.SIGTERM, signal.SIG_IGN)\n' if ignore_term else '')
            + 'print("ready", flush=True)\nsignal.pause()\n'
        )
        proc = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE,
                                text=True, start_new_session=True)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(lambda: stop_debugger(proc, timeout_s=1))
        self.assertEqual(proc.stdout.readline(), 'ready\n')
        return proc

    def test_term_reaps_only_captured_child(self):
        proc = self.child()
        with patch('os.killpg', side_effect=AssertionError('group signal forbidden')):
            stop_debugger(proc, timeout_s=1)
        self.assertEqual(proc.returncode, -signal.SIGTERM)
        self.assertTrue(cleanup.absent(proc.pid))

    def test_term_ignoring_child_is_killed_and_reaped(self):
        proc = self.child(ignore_term=True)
        with patch('os.killpg', side_effect=AssertionError('group signal forbidden')):
            stop_debugger(proc, timeout_s=.2)
        self.assertEqual(proc.returncode, -signal.SIGKILL)
        self.assertTrue(cleanup.absent(proc.pid))

    def test_reaped_child_is_never_signalled_again(self):
        proc = self.child()
        stop_debugger(proc, timeout_s=1)
        with patch.object(proc, 'terminate', side_effect=AssertionError('already reaped')):
            with patch.object(proc, 'kill', side_effect=AssertionError('already reaped')):
                stop_debugger(proc)

    def test_failed_absence_proof_refuses_completion(self):
        proc = self.child()
        with self.assertRaisesRegex(RuntimeError, 'death not verified'):
            stop_debugger(proc, timeout_s=1, verify_absent=lambda pid: False)
        self.assertTrue(cleanup.absent(proc.pid))

    def test_kill_timeout_is_bounded_and_propagates(self):
        proc = Mock(pid=123)
        proc.poll.return_value = None
        proc.wait.side_effect = subprocess.TimeoutExpired('captured-debugger', .2)
        verify = Mock()
        with self.assertRaises(subprocess.TimeoutExpired):
            stop_debugger(proc, timeout_s=.2, verify_absent=verify)
        self.assertEqual(proc.wait.call_count, 2)
        for call in proc.wait.call_args_list:
            self.assertEqual(call.kwargs, {'timeout': .2})
        proc.terminate.assert_called_once_with()
        proc.kill.assert_called_once_with()
        verify.assert_not_called()


if __name__ == '__main__':
    unittest.main()
