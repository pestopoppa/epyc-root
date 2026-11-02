import signal
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from session_drain import DrainError, drain_session, spawn_session, _signal_captured


class SessionDrainTest(unittest.TestCase):
    def test_spawn_has_owned_session_no_shell(self):
        with patch('session_drain.subprocess.Popen') as popen:
            spawn_session(['/bin/true'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={}, cwd='/tmp')
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        self.assertNotIn('shell', popen.call_args.kwargs)

    def test_pidfd_revalidates_identity_before_signal(self):
        with patch('session_drain.os.pidfd_open', return_value=9), patch('session_drain.os.close'), \
             patch('session_drain._stat', return_value=('S', 21, 101)), \
             patch('session_drain.signal.pidfd_send_signal') as send:
            _signal_captured(22, 101, 21, signal.SIGTERM)
            send.assert_called_once_with(9, signal.SIGTERM)
            with self.assertRaises(DrainError):
                _signal_captured(22, 100, 21, signal.SIGTERM)
            self.assertEqual(send.call_count, 1)

    def test_escalates_and_refuses_surviving_session(self):
        proc = MagicMock(spec=subprocess.Popen); proc.pid = 21
        # A monotonic sequence advances immediately through each bounded window.
        with patch('session_drain._session_members', return_value={22: 100}), \
             patch('session_drain._signal_captured') as send, \
             patch('session_drain.time.monotonic', side_effect=[0, 2, 3, 5]):
            with self.assertRaises(DrainError):
                drain_session(proc, 1)
        self.assertEqual([x.args[3] for x in send.call_args_list], [signal.SIGTERM, signal.SIGKILL])

    def test_success_verifies_empty_session_and_reaps(self):
        proc = MagicMock(spec=subprocess.Popen); proc.pid = 21
        with patch('session_drain._session_members', side_effect=[{22: 100}, {}]), \
             patch('session_drain._signal_captured') as send:
            drain_session(proc, 1)
        send.assert_called_once_with(22, 100, 21, signal.SIGTERM)
        proc.wait.assert_called_once_with(timeout=0)


if __name__ == '__main__':
    unittest.main()
