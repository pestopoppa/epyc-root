import math
from pathlib import Path
import socket
import sys
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from socket_deadline import SocketDeadline


class DeadlineTests(unittest.TestCase):
    def test_silent_peer_unblocks_without_reader_cooperation(self):
        reader, peer = socket.socketpair()
        with reader, peer:
            start = time.monotonic()
            with SocketDeadline(reader, start + .12) as guard:
                self.assertEqual(reader.recv(1), b'')
                self.assertTrue(guard.expired.is_set())
                with self.assertRaises(TimeoutError):
                    guard.check()
            self.assertLess(time.monotonic() - start, 1.)
            self.assertFalse(guard.thread.is_alive())

    def test_trickle_traffic_cannot_reset_total_deadline(self):
        reader, peer = socket.socketpair()
        done = threading.Event()
        def trickle():
            while not done.wait(.01):
                try:
                    peer.sendall(b'x')
                except OSError:
                    return
        thread = threading.Thread(target=trickle)
        with reader, peer:
            thread.start()
            start = time.monotonic()
            try:
                with SocketDeadline(reader, start + .15) as guard:
                    while reader.recv(1):
                        pass
                    self.assertTrue(guard.expired.is_set())
                self.assertLess(time.monotonic() - start, 1.)
            finally:
                done.set()
                thread.join(timeout=1.)
                self.assertFalse(thread.is_alive())

    def test_clean_exit_does_not_cancel_socket(self):
        reader, peer = socket.socketpair()
        with reader, peer:
            with SocketDeadline(reader, time.monotonic() + 1.) as guard:
                guard.check()
            peer.sendall(b'x')
            self.assertEqual(reader.recv(1), b'x')
            self.assertFalse(guard.thread.is_alive())
            self.assertFalse(guard.expired.is_set())

    def test_invalid_deadlines_refused(self):
        reader, peer = socket.socketpair()
        with reader, peer:
            for value in (math.nan, math.inf, -1.):
                with self.assertRaises(ValueError):
                    SocketDeadline(reader, value)

    def test_connect_elapsed_time_does_not_reset_budget(self):
        reader, peer = socket.socketpair()
        with reader, peer:
            start = time.monotonic()
            deadline = start + .18
            # Simulate finite connect work before arming the watchdog.
            time.sleep(.10)
            with SocketDeadline(reader, deadline) as guard:
                self.assertEqual(reader.recv(1), b'')
                self.assertTrue(guard.expired.is_set())
            self.assertLess(time.monotonic() - start, .25)

    def test_expired_after_connect_refuses_before_request(self):
        reader, peer = socket.socketpair()
        with reader, peer:
            with self.assertRaises(ValueError):
                SocketDeadline(reader, time.monotonic() - .001)


if __name__ == '__main__':
    unittest.main()
