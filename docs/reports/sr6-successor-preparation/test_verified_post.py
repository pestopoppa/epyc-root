import os
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch

from server_lifecycle import ReadyServer
from verified_post import VerifiedPost, process_starttime, verify_owned_loopback_listener


class VerifiedPostTest(unittest.TestCase):
    def test_real_socket_is_bound_to_captured_pid(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen()
            port = listener.getsockname()[1]
            birth = process_starttime(os.getpid())
            self.assertTrue(verify_owned_loopback_listener(os.getpid(), birth, port))
            with self.assertRaises(ValueError):
                verify_owned_loopback_listener(os.getpid(), birth + 1, port)
            with self.assertRaises(ValueError):
                verify_owned_loopback_listener(os.getpid(), birth, 1)

    def test_checks_admission_stop_deadline_and_port_before_transport(self):
        with tempfile.TemporaryDirectory() as tmp, socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen()
            port = listener.getsockname()[1]
            stop = Path(tmp) / 'STOP'
            ready = ReadyServer(os.getpid(), 'mtp3', {'starttime_ticks': process_starttime(os.getpid())})
            calls = []
            guard = VerifiedPost(port=port, timeout_s=1, max_response_bytes=1024,
                                 deadline=time.time()+30, stop_file=stop, admission_check=lambda: True)
            self.assertTrue(guard.transport.continue_check())
            with patch.object(type(guard.transport), '__call__', lambda _, server, payload: calls.append(payload) or (200, b'ok')):
                self.assertEqual(guard(ready, {'prompt': 'x'}), (200, b'ok'))
                stop.touch()
                self.assertFalse(guard.transport.continue_check())
                with self.assertRaises(ValueError): guard(ready, {})
                stop.unlink()
                guard.admission_check = lambda: False
                guard._next_admission_check = 0.0
                self.assertFalse(guard.transport.continue_check())
                with self.assertRaises(ValueError): guard(ready, {})
                guard.admission_check = lambda: True
                guard.deadline = time.time()
                self.assertFalse(guard.transport.continue_check())
                with self.assertRaises(ValueError): guard(ready, {})
            self.assertEqual(len(calls), 1)

    def test_ownership_check_is_rate_limited_but_stop_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            stop = Path(tmp) / 'STOP'; calls = []
            guard = VerifiedPost(port=12345, timeout_s=1, max_response_bytes=10,
                deadline=time.time()+30, stop_file=stop,
                admission_check=lambda: calls.append(1) or True)
            with patch('verified_post.time.monotonic', side_effect=[10.0, 10.5, 11.0]):
                self.assertTrue(guard.transport.continue_check())
                self.assertTrue(guard.transport.continue_check())
                self.assertEqual(len(calls), 1)
                self.assertTrue(guard.transport.continue_check())
                self.assertEqual(len(calls), 2)
                stop.touch()
                self.assertFalse(guard.transport.continue_check())


if __name__ == '__main__':
    unittest.main()
