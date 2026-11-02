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
            with patch.object(type(guard.transport), '__call__', lambda _, server, payload: calls.append(payload) or (200, b'ok')):
                self.assertEqual(guard(ready, {'prompt': 'x'}), (200, b'ok'))
                stop.touch()
                with self.assertRaises(ValueError): guard(ready, {})
                stop.unlink()
                guard.admission_check = lambda: False
                with self.assertRaises(ValueError): guard(ready, {})
                guard.admission_check = lambda: True
                guard.deadline = time.time()
                with self.assertRaises(ValueError): guard(ready, {})
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
