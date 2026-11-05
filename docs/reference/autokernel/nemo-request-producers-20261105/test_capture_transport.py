import base64
import json
import unittest

from capture_client import capture


class Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


class CaptureTransport(unittest.TestCase):
    def test_retains_exact_bodies_and_matching_request_identity(self):
        seen = {}

        def send(request, timeout):
            seen['body'] = request.data
            seen['timeout'] = timeout
            request_body = json.loads(request.data)
            seen['response'] = json.dumps({'nemo_request_id': request_body['nemo_request_id'], 'content': 'ok'}).encode()
            return Response(seen['response'])

        record = capture('http://example.invalid/completion', {'prompt': 'test'}, send)['requests'][0]
        self.assertEqual(base64.b64decode(record['request_body_base64']), seen['body'])
        self.assertEqual(base64.b64decode(record['response_body_base64']), seen['response'])
        self.assertEqual(record['request_id'], record['response_request_id'])
        self.assertEqual(seen['timeout'], 600)

    def test_bad_echo_and_invalid_request_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'identity echo'):
            capture('http://example.invalid/completion', {'prompt': 'test'}, lambda request, timeout: Response(b'{"nemo_request_id":"wrong"}'))
        for payload in ({'prompt': 'x', 'stream': True}, {'prompt': ['x']}, {'prompt': 'x', 'n': 2}, {'prompt': 'x', 'nemo_request_id': 'supplied'}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                capture('http://example.invalid/completion', payload, lambda *a, **k: self.fail('transport called'))


if __name__ == '__main__':
    unittest.main()
