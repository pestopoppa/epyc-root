import json
import unittest
from unittest.mock import patch

from native_transport import MAX_REPLY, post_completion


class FakeResponse:
    status = 200
    def __init__(self, body=b'{"timings":{}}'):
        self.body = body
        self.length = 0
    def read(self, limit):
        return self.body[:limit]


class FakeConnection:
    def __init__(self, host, port, timeout):
        self.address = (host, port, timeout)
        self.closed = False
        self.response = FakeResponse()
        self.requested = []
    def request(self, *args, **kwargs):
        self.requested.append((args, kwargs))
    def getresponse(self):
        return self.response
    def close(self):
        self.closed = True


class NativeTransportTest(unittest.TestCase):
    def setUp(self):
        self.payload = {'prompt': 'x', 'cache_prompt': False, 'stream': False, 'n_predict': 12}
    def test_one_native_post_and_raw_response(self):
        with patch('native_transport.http.client.HTTPConnection', side_effect=FakeConnection) as factory:
            status, raw = post_completion(17777, self.payload, 3)
        self.assertEqual((status, raw), (200, b'{"timings":{}}'))
        factory.assert_called_once_with('127.0.0.1', 17777, timeout=3)
    def test_fails_before_connection_on_invalid_request(self):
        for key, value in [('cache_prompt', True), ('stream', True), ('n_predict', True), ('prompt', '')]:
            payload = dict(self.payload, **{key: value})
            with self.subTest(key=key), patch('native_transport.http.client.HTTPConnection') as factory:
                with self.assertRaises(ValueError): post_completion(10000, payload, 1)
                factory.assert_not_called()
    def test_oversized_reply_closes_connection(self):
        conn = FakeConnection('127.0.0.1', 10000, 1)
        conn.response = FakeResponse(b'x' * (MAX_REPLY + 1))
        with patch('native_transport.http.client.HTTPConnection', return_value=conn):
            with self.assertRaises(ValueError): post_completion(10000, self.payload, 1)
        self.assertTrue(conn.closed)
        self.assertEqual(len(conn.requested), 1)
        args, kwargs = conn.requested[0]
        self.assertEqual(args, ('POST', '/completion'))
        self.assertEqual(json.loads(kwargs['body']), self.payload)

    def test_truncated_reply_closes_connection(self):
        conn = FakeConnection('127.0.0.1', 10000, 1)
        conn.response.length = 5
        with patch('native_transport.http.client.HTTPConnection', return_value=conn):
            with self.assertRaisesRegex(ValueError, 'declared content length'):
                post_completion(10000, self.payload, 1)
        self.assertTrue(conn.closed)


if __name__ == '__main__': unittest.main()
