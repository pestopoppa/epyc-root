import importlib.util
import io
import urllib.error
import urllib.request
from email.message import Message
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('slot_sampler', Path(__file__).with_name('slot_sampler.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Response:
    status = 200
    def __init__(self, content): self.content = content
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size): return self.content[:size]

class SlotSamplerTest(unittest.TestCase):
    def capture(self, content):
        values = iter([100, 120])
        return m.capture_slot_sample('http://127.0.0.1:18436', opener=lambda *a, **k: Response(content),
                                     clock=lambda: next(values), wall=lambda: 900)
    def test_exact_raw_and_bounds(self):
        raw = b'[{"id":0,"is_processing":true}]'
        r = self.capture(raw)
        self.assertEqual(r['raw_utf8'].encode(), raw)
        self.assertEqual((r['start_monotonic_ns'], r['end_monotonic_ns']), (100, 120))
    def test_malformed_or_wrong_shape_refused(self):
        self.assertEqual(self.capture(b'{"id":0}')['status'], 'error')
        self.assertEqual(self.capture(b'not json')['status'], 'error')
    def test_oversized_refused(self):
        self.assertEqual(self.capture(b'x' * (8 * 1024 * 1024 + 1))['status'], 'error')
    def test_nonloopback_and_bad_origin_refused(self):
        for base in ('http://example.com', 'https://localhost', 'http://localhost/path',
                     'http://user@localhost', 'http://localhost?x=1'):
            with self.subTest(base=base), self.assertRaises(ValueError):
                m.capture_slot_sample(base)
    def test_redirect_to_external_refused_without_followup(self):
        calls = []
        class FakeHTTP(urllib.request.BaseHandler):
            handler_order = 100
            def http_open(self, request):
                calls.append(request.full_url)
                headers = Message()
                headers['Location'] = 'http://example.com/elsewhere'
                response = urllib.response.addinfourl(io.BytesIO(b''), headers, request.full_url, 302)
                response.msg = 'Found'
                return response
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), FakeHTTP(), m.RejectRedirect())
        values = iter([10, 20])
        result = m.capture_slot_sample('http://127.0.0.1:1', opener=opener.open,
                                       clock=lambda: next(values), wall=lambda: 7)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(calls, ['http://127.0.0.1:1/slots'])

    def test_default_opener_installs_redirect_refusal_and_disables_proxy(self):
        from unittest.mock import patch
        class Dummy:
            def open(self, *args, **kwargs): return Response(b'[]')
        with patch.object(m.urllib.request, 'build_opener', return_value=Dummy()) as build:
            self.assertEqual(m.capture_slot_sample('http://127.0.0.1:1')['status'], 'ok')
        self.assertIsInstance(build.call_args.args[0], urllib.request.ProxyHandler)
        self.assertEqual(build.call_args.args[0].proxies, {})
        self.assertIsInstance(build.call_args.args[1], m.RejectRedirect)

    def test_io_error_has_observation_window(self):
        def broken(*args, **kwargs): raise OSError('no server')
        values = iter([5, 9])
        r = m.capture_slot_sample('http://localhost:1', opener=broken, clock=lambda: next(values), wall=lambda: 7)
        self.assertEqual((r['status'], r['start_monotonic_ns'], r['end_monotonic_ns']), ('error', 5, 9))

if __name__ == '__main__': unittest.main()
