"""Actual local fake HTTP/SSE transport; no model or inference."""

import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from threading import Thread
import unittest

import q38_t7_transport as transport


class FakeHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        timings = {'cache_n': 5, 'predicted_n': 3, 'predicted_per_second': 10}
        if body.get('stream'):
            event = {'choices': [{'index': 0, 'delta': {'content': 'answer', 'reasoning_content': 'reason'},
                                  'finish_reason': 'stop'}], 'timings': timings}
            raw = ('data: ' + json.dumps(event) + '\n\ndata: [DONE]\n\n').encode()
        else:
            raw = json.dumps({'choices': [{'message': {'content': 'answer'}, 'finish_reason': 'stop'}],
                              'timings': timings}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(raw)


class TransportTest(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(('127.0.0.1', 0), FakeHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown(); self.thread.join(timeout=3); self.server.server_close()

    @staticmethod
    def proof(_handle, text):
        ids = [1, 2, 3]
        return {'token_ids': ids, 'method': 'retokenized_text',
                'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'tokenizer_sha256': 'a' * 64,
                'token_ids_sha256': hashlib.sha256(b'[1,2,3]').hexdigest()}

    def test_actual_stream_retains_events_and_exact_text_attestation(self):
        client = transport.HttpTransport(lambda _: self.base, self.proof)
        result = client.send(None, {'messages': [{'role': 'user', 'content': 'x'}], 'stream': True})
        self.assertTrue(result['stream_complete'])
        self.assertEqual(result['content'], 'answer')
        self.assertEqual(result['reasoning'], 'reason')
        self.assertEqual(result['tokenizer_provenance']['text_sha256'],
                         hashlib.sha256(b'reason\nanswer').hexdigest())
        self.assertEqual(result['raw_stream_sha256'], hashlib.sha256(result['raw_stream'].encode()).hexdigest())
        self.assertIsNotNone(result['ttft_s'])

    def test_actual_nonstream_retains_raw_and_tokenizer_proof(self):
        client = transport.HttpTransport(lambda _: self.base, self.proof)
        result = client.send(None, {'messages': [{'role': 'user', 'content': 'x'}]})
        self.assertEqual(result['body'], json.loads(result['raw_body']))
        self.assertEqual(result['raw_body_sha256'], hashlib.sha256(result['raw_body'].encode()).hexdigest())
        self.assertEqual(result['tokenizer_provenance']['text_sha256'], hashlib.sha256(b'answer').hexdigest())

    def test_incomplete_or_malformed_sse_refuses(self):
        for raw in (b'data: {}\n\n', b'data: broken\n\ndata: [DONE]\n\n',
                    b'data: [DONE]\n\ndata: {}\n\n'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                transport.parse_sse(raw)

    def test_spoofed_loopback_url_refuses(self):
        client = transport.HttpTransport(lambda _: 'http://127.0.0.1:80@example.com')
        with self.assertRaises(ValueError):
            client.send(None, {})


if __name__ == '__main__':
    unittest.main()
