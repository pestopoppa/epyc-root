import unittest
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

if __name__ == '__main__': unittest.main()
