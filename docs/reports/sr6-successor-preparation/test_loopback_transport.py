import unittest
import socket
import threading
from unittest.mock import patch

from loopback_transport import LoopbackCompletion
from native_worker import canonical
from server_lifecycle import ReadyServer


class Response:
    def __init__(self, status, body): self.status, self.body, self.length = status, body, None
    def read(self, amount): return self.body[:amount]


class Connection:
    def __init__(self, status=200, body=b'{}'):
        self.response = Response(status, body); self.closed = False; self.requests = []
    def request(self, *args, **kwargs): self.requests.append((args, kwargs))
    def getresponse(self): return self.response
    def close(self): self.closed = True


class TestLoopbackCompletion(unittest.TestCase):
    def setUp(self):
        self.server = ReadyServer(42, 'mtp3', {'server_record_sha256':'a'*64})
        self.transport = LoopbackCompletion(12345, 3, 8)

    def test_one_bounded_direct_request(self):
        conn = Connection(302, b'moved')
        with patch('loopback_transport.http.client.HTTPConnection', return_value=conn) as factory:
            self.assertEqual(self.transport(self.server, {'prompt':'hello'}), (302, b'moved'))
        factory.assert_called_once_with('127.0.0.1', 12345, timeout=3)
        self.assertEqual(conn.requests[0][0], ('POST', '/completion'))
        self.assertEqual(conn.requests[0][1]['body'], canonical({'prompt':'hello'}))
        self.assertEqual(len(conn.requests), 1)
        self.assertTrue(conn.closed)

    def test_oversize_and_transport_error_close(self):
        conn = Connection(body=b'123456789')
        with patch('loopback_transport.http.client.HTTPConnection', return_value=conn):
            with self.assertRaises(ValueError): self.transport(self.server, {})
        self.assertTrue(conn.closed)
        conn = Connection(); conn.response.length = 2
        with patch('loopback_transport.http.client.HTTPConnection', return_value=conn):
            with self.assertRaises(ValueError): self.transport(self.server, {})
        self.assertTrue(conn.closed)
        conn = Connection(); conn.getresponse = lambda: (_ for _ in ()).throw(TimeoutError())
        with patch('loopback_transport.http.client.HTTPConnection', return_value=conn):
            with self.assertRaises(TimeoutError): self.transport(self.server, {})
        self.assertTrue(conn.closed)

    def test_invalid_parameters_and_handle_refuse(self):
        for args in ((0, 1, 1), (True, 1, 1), (1, float('nan'), 1), (1, 1, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError): LoopbackCompletion(*args)
        with self.assertRaises(ValueError): self.transport(None, {})

    def test_stop_during_inflight_response_closes_socket(self):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        observed = threading.Event()
        disconnected = threading.Event()
        def serve():
            try:
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(3)
                    conn.recv(4096)
                    observed.set()
                    while conn.recv(4096):
                        pass
                    disconnected.set()
            finally:
                listener.close()
        thread = threading.Thread(target=serve)
        thread.start()
        transport = LoopbackCompletion(listener.getsockname()[1], 3, 1024,
                                       continue_check=lambda: not observed.is_set())
        with self.assertRaisesRegex(ValueError, 'cancelled'):
            transport(self.server, {'prompt': 'exposed'})
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertTrue(disconnected.is_set())

    def test_refuses_before_connect_when_stop_already_set(self):
        transport = LoopbackCompletion(12345, 3, 1024, continue_check=lambda: False)
        with patch('loopback_transport.http.client.HTTPConnection') as factory:
            with self.assertRaisesRegex(ValueError, 'before send'):
                transport(self.server, {})
            factory.return_value.connect.assert_not_called()

    def test_guarded_success_retains_bounded_http_result(self):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        def serve():
            try:
                conn, _ = listener.accept()
                with conn:
                    conn.recv(4096)
                    conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}')
            finally:
                listener.close()
        thread = threading.Thread(target=serve)
        thread.start()
        transport = LoopbackCompletion(port, 3, 8, continue_check=lambda: True)
        real_thread = threading.Thread
        workers = []
        def capture_worker(*args, **kwargs):
            worker = real_thread(*args, **kwargs)
            workers.append(worker)
            return worker
        with patch('loopback_transport.threading.Thread', side_effect=capture_worker):
            self.assertEqual(transport(self.server, {}), (200, b'{}'))
        self.assertEqual(len(workers), 1)
        self.assertFalse(workers[0].is_alive())
        thread.join(3)
        self.assertFalse(thread.is_alive())

if __name__ == '__main__': unittest.main()
