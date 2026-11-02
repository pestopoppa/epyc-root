import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from native_worker import arm_flags, capture_request

class NativeCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.prompt = {'id': 'p1', 'rendered': 'hello', 'rendered_sha256': hashlib.sha256(b'hello').hexdigest(), 'seed': 3}
        self.args = dict(window='w1', block=0, arm='composed3', prompt=self.prompt,
                         sampler={'temperature': 0.6}, server_record_sha256='a'*64)

    def test_arms(self):
        self.assertEqual(arm_flags('composed3'), ['--spec-type', 'ngram-mod,draft-mtp', '--spec-draft-n-max', '3'])
        self.assertEqual(arm_flags('mtp4_repeat'), ['--spec-type', 'draft-mtp', '--spec-draft-n-max', '4'])
        with self.assertRaises(ValueError): arm_flags('unknown')

    def test_exposure_precedes_call_and_raw_bytes_preserved(self):
        def post(payload):
            self.assertEqual(len(list(self.out.glob('*.exposure.json'))), 1)
            self.assertFalse(payload['cache_prompt']); self.assertTrue(payload['return_tokens'])
            return 200, b'\xffraw'
        record = capture_request(self.out, **self.args, post=post)
        self.assertEqual(base64.b64decode(record['raw_base64']), b'\xffraw')
        self.assertEqual(record['raw_sha256'], hashlib.sha256(b'\xffraw').hexdigest())
        self.assertIsNone(record['verdict'])

    def test_failure_is_recorded_and_cannot_retry(self):
        def broken(_): raise TimeoutError('deadline')
        result = capture_request(self.out, **self.args, post=broken)
        self.assertEqual(result['state'], 'transport_error')
        with self.assertRaises(FileExistsError): capture_request(self.out, **self.args, post=broken)

    def test_corrupt_prompt_or_sampler_rejected_before_exposure(self):
        self.prompt['rendered'] = 'different'
        with self.assertRaises(ValueError): capture_request(self.out, **self.args, post=lambda _: (200,b''))
        self.assertEqual(list(self.out.iterdir()), [])
        self.prompt['rendered'] = 'hello'; self.args['sampler'] = {'cache_prompt': True}
        with self.assertRaises(ValueError): capture_request(self.out, **self.args, post=lambda _: (200,b''))
        self.assertEqual(list(self.out.iterdir()), [])

    def test_invalid_http_payload_is_error_not_success(self):
        record = capture_request(self.out, **self.args, post=lambda _: ('200', 'not bytes'))
        self.assertEqual(record['state'], 'transport_error')
        self.assertEqual(json.loads(next(self.out.glob('*.response.json')).read_text())['state'], 'transport_error')

if __name__ == '__main__': unittest.main()
