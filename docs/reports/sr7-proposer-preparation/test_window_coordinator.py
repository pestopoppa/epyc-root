import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import window_coordinator as wc


def fixture():
    prompts = []
    for w in range(3):
        for c in wc.CLASSES:
            for i in range(5):
                raw = f'{w} {c} {i}'
                prompts.append({'window': f'w{w}', 'id': f'{w}_{c}_{i}', 'class': c,
                    'seed': len(prompts), 'prompt': raw, 'prompt_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                    'rendered_prompt': f'render {raw}', 'rendered_token_ids': [1, 2, 3, 4, 5]})
    data = json.dumps({'schema': 'sr7.rendered-candidate.v1', 'prompts': prompts}).encode()
    return data, hashlib.sha256(data).hexdigest()


def config(window, prompt, mode, width):
    return {'payload': {'prompt': prompt['rendered_prompt'], 'seed': prompt['seed'],
                        'cache_prompt': False, 'stream': False, 'n_predict': 10},
            'port': 1234, 'timeout_s': 1, 'argv': ['/bin/true'], 'env': {}, 'cwd': '/', 'verify': lambda *x: {}}


def fake_capture(**kw):
    for suffix in ('.start.json', '.exposure.json', '.response.bin', '.response.json', '.trace.bin', '.parsed.json'):
        (kw['root'] / (kw['request_id'] + suffix)).write_text('evidence')
    return {'proposers': {}}


class CoordinatorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.exp = self.root / 'exposure'; self.exp.mkdir()
        data, digest = fixture()
        self.kw = dict(packet_bytes=data, expected_sha256=digest, authenticate=lambda data, sha: True,
                       window_id='w0', root=self.root, exposure_root=self.exp,
                       config_for_arm=config, admission=None)

    @patch.object(wc, 'capture_contained', side_effect=fake_capture)
    def test_complete_and_no_replay(self, capture):
        result = wc.run_window(**self.kw)
        self.assertEqual((result['state'], result['completed']), ('complete_raw', 90))
        self.assertEqual([x['mode'] + str(x['width']) for x in result['requests'][:6]],
                         ['composed2', 'composed4', 'composed6', 'control2', 'control4', 'control6'])
        self.assertEqual(result['requests'][6]['mode'], 'composed')
        self.assertEqual(result['requests'][6]['width'], 4)
        with self.assertRaises(FileExistsError): wc.run_window(**self.kw)
        self.assertEqual(capture.call_count, 90)

    @patch.object(wc, 'capture_contained', side_effect=RuntimeError('failed'))
    def test_failure_is_unknown_and_reservations_persist(self, capture):
        result = wc.run_window(**self.kw)
        self.assertEqual((result['state'], result['attempted'], result['completed']), ('UNKNOWN', 1, 0))
        self.assertEqual(len(list(self.exp.iterdir())), 15)
        self.assertEqual(capture.call_count, 1)

    @patch.object(wc, 'capture_contained', side_effect=fake_capture)
    def test_cross_packet_exposure_and_auth(self, capture):
        wc.run_window(**self.kw)
        data = json.loads(self.kw['packet_bytes']); data['extra'] = 'different packet'
        raw = json.dumps(data).encode(); self.kw['packet_bytes'] = raw; self.kw['expected_sha256'] = hashlib.sha256(raw).hexdigest()
        result = wc.run_window(**self.kw)
        self.assertEqual((result['state'], result['attempted']), ('UNKNOWN', 0))
        self.kw['authenticate'] = lambda *x: False
        with self.assertRaisesRegex(ValueError, 'authentication'): wc.run_window(**self.kw)
        self.assertEqual(capture.call_count, 90)

if __name__ == '__main__': unittest.main()
