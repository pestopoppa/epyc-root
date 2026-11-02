import json
import tempfile
import unittest
from pathlib import Path
from exposure_inventory import inventory
from native_worker import capture_request, digest


class TestExposureInventory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prompt = {'id': 'p1', 'rendered': 'hello', 'rendered_sha256': digest(b'hello'), 'seed': 1}
    def tearDown(self):
        self.temp.cleanup()
    def capture(self, post):
        return capture_request(self.root, window='w1', block=0, arm='mtp3', prompt=self.prompt,
                               sampler={'n_predict': 1}, server_record_sha256='a' * 64, post=post)
    def test_empty_and_completed(self):
        self.assertEqual(inventory(self.root), [])
        self.capture(lambda _: (200, b'{"content":"x"}'))
        self.assertEqual(inventory(self.root)[0]['response'], 'complete')
        self.assertEqual(inventory(self.root)[0]['rendered_sha256'], digest(b'hello'))
    def test_interrupted_and_http_failure(self):
        self.capture(lambda _: (503, b'busy'))
        response = next(self.root.glob('*.response.json'))
        self.assertEqual(inventory(self.root)[0]['response'], 'error')
        response.unlink()
        self.assertEqual(inventory(self.root)[0]['response'], 'missing')
    def test_orphan_and_tampering_refused(self):
        self.capture(lambda _: (200, b'ok'))
        exposure = next(self.root.glob('*.exposure.json'))
        exposure.write_bytes(exposure.read_bytes() + b' ')
        with self.assertRaises(ValueError): inventory(self.root)
        exposure.unlink()
        with self.assertRaises(ValueError): inventory(self.root)
    def test_exposure_hash_must_match_request_even_without_response(self):
        self.capture(lambda _: (200, b'ok'))
        next(self.root.glob('*.response.json')).unlink()
        exposure = next(self.root.glob('*.exposure.json'))
        record = json.loads(exposure.read_text())
        record['request']['prompt'] = 'tampered'
        exposure.write_text(json.dumps(record))
        with self.assertRaises(ValueError): inventory(self.root)
    def test_link_refused(self):
        (self.root / 'x.exposure.json').symlink_to('/dev/null')
        with self.assertRaises(ValueError): inventory(self.root)
    def test_bad_json_refused(self):
        (self.root / 'x.exposure.json').write_text('{')
        with self.assertRaises(ValueError): inventory(self.root)

if __name__ == '__main__': unittest.main()
