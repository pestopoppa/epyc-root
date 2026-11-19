import copy
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import convert
import run_driver
from fit import digest


class ConvertTests(unittest.TestCase):
    def fixture(self, root):
        native = root / 'native'
        native.mkdir()
        # The physical cache is deliberately NOT in original-position order.
        rows = [9, 2, 5, 0, 11, -1, 7, 1, 10, 4, 6, 3, 8, -1, -1, -1]
        for layer in (3, 7):
            q = np.arange(16, dtype=np.float32).reshape(1, 4, 2, 2) / 16
            k = np.zeros((1, 2, 16, 2), dtype=np.float32)
            v = np.zeros((1, 2, 16, 3), dtype=np.float32)
            for head in range(2):
                for row, pos in enumerate(rows):
                    v[0, head, row] = (np.arange(3) + layer + head*3 + 1
                                       if 0 <= pos < 10 else 1000)
            mask = np.full((1, 1, 4, 16), -np.inf, dtype=np.float32)
            for query in range(2):
                for row, pos in enumerate(rows):
                    if 0 <= pos <= query + 10:
                        mask[0, 0, query, row] = 0
            output = np.ones((1, 2, 4, 3), dtype=np.float32)
            m = dict(schema='epyc.am.native-layer.v1', layer=layer, attention_scale=0.5, tensors={})
            for name, array in dict(Q=q, K=k, V=v, mask=mask, output=output).items():
                namefile = f'layer-{layer}-{name}.f32'
                array.astype('<f4').tofile(native / namefile)
                m['tensors'][name] = dict(file=namefile, ne=list(reversed(array.shape)))
            (native / f'layer-{layer}.json').write_text(json.dumps(m))
        (native / 'COMPLETE.json').write_text(json.dumps(dict(schema='epyc.am.native-capture.v1', layers=[3, 7])))
        (root / 'prefix.state').write_bytes(b'model-free-prefix-state')
        p = dict(schema='epyc.am.calibration-provenance.v1', sequence=0, source_commit='a'*40,
                 model_identity='fixture-model', capture_id='fixture', prefix_tokens=10,
                 cache_row_positions=rows, query_positions=[10, 11], fit_positions=[10], eval_positions=[11],
                 layers=[3, 7])
        (root / 'PROVENANCE.raw.json').write_text(json.dumps(p))
        (root / 'RESULT.json').write_text(json.dumps(dict(schema='epyc.am.native-driver.v1', mode='capture')))
        path = convert.seal_provenance(root)
        return native, path, json.loads(path.read_text())

    def run_fixture(self, root):
        native, path, p = self.fixture(root)
        return convert.convert(native, path, root / 'fits', 2), p

    def test_5x_shared_gqa_fit_and_binary_axes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result, _ = self.run_fixture(root)
            self.assertEqual(result['positions'], [0, 9])
            self.assertEqual(len(result['layers']), 4)
            for fitted in result['layers']:
                self.assertGreater(fitted['heldout']['cosine_min'], 0.999999)
                self.assertLess(fitted['heldout']['relative_l2'], 1e-6)
            for layer in (3, 7):
                for head in range(2):
                    with np.load(root / 'fits' / f'layer-{layer}-head-{head}.npz') as z:
                        self.assertEqual(z['K'].shape, (10, 2))
                        np.testing.assert_array_equal(z['V'], np.tile(np.arange(3)+layer+head*3+1, (10, 1)))
                        self.assertEqual(len(z['fit_ids']), 2)
                        self.assertFalse(set(z['fit_ids']) & set(z['eval_ids']))
                        self.assertTrue(all('pos=11' in x for x in z['eval_ids']))
            raw = (root / 'fits' / 'carrier.bin').read_bytes()
            self.assertEqual(raw[:8], b'EPYCAM03')
            self.assertEqual(struct.unpack_from('<IIqqIII', raw, 8), (2, 2, 0, 9, 3, 2, 3))
            self.assertEqual(result['carrier_sha256'], digest(root / 'fits' / 'carrier.bin'))

    def test_row_mapping_and_gqa_query_axes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            native, _, p = self.fixture(root)
            meta, t, _ = convert.load_layer(native, 3)
            for row, pos in enumerate(p['cache_row_positions']):
                t['K'][0, 1, row] = pos
            z = convert.shard(t, meta, p, 1, np.array([0, 9]))
            np.testing.assert_array_equal(z['K'][:, 0], np.arange(10))
            np.testing.assert_array_equal(z['Q_fit'], t['Q'][0, 2:4, 0])
            np.testing.assert_array_equal(z['Q_eval'], t['Q'][0, 2:4, 1])

    def test_provenance_refuses_leakage_mapping_and_identity_defects(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            native, path, p = self.fixture(root)
            for key, bad in [('fit_positions', [10, 11]), ('eval_positions', [10]),
                             ('query_positions', [9, 11]), ('cache_row_positions', [0]*16),
                             ('complete_sha256', '0'*64), ('layers', [3]),
                             ('source_commit', 'unbound'), ('prefix_state_sha256', 'unbound'),
                             ('sequence', 1)]:
                with self.subTest(key=key):
                    mutation = copy.deepcopy(p); mutation[key] = bad
                    path.write_text(json.dumps(mutation))
                    with self.assertRaises(ValueError):
                        convert.provenance(path, native)

    def test_masks_and_geometry_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            native, _, p = self.fixture(root)
            meta, t, _ = convert.load_layer(native, 3)
            for bad in (-np.inf, 0.1):
                t['mask'][0, 0, 0, 0] = bad
                with self.assertRaisesRegex(ValueError, 'zero bias'):
                    convert.shard(t, meta, p, 0, np.array([0, 9]))
            t['mask'][0, 0, 0, 0] = 0
            t['Q'] = t['Q'][:, :, :1]
            with self.assertRaisesRegex(ValueError, 'geometry'):
                convert.shard(t, meta, p, 0, np.array([0, 9]))

    def test_selection_endpoints_and_sizes(self):
        for n in range(2, 36):
            for keep in range(2, n + 1):
                ix = convert.uniform_selection(n, keep)
                self.assertEqual(len(set(ix)), keep)
                self.assertEqual((ix[0], ix[-1]), (0, n-1))
        for keep in (0, 1, 11, True, 2.0):
            with self.assertRaises(ValueError):
                convert.uniform_selection(10, keep)

    def test_reload_refuses_wrong_snapshot_carrier_and_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, p = self.run_fixture(root)
            cfg = {key: p[key] for key in ('source_commit', 'model_identity', 'capture_id')}
            cfg.update(mode='reload', prefix_tokens=[1]*10, carrier=str(root/'fits'/'carrier.bin'),
                       prefix_state=str(root/'prefix.state'))
            convert.verify_reload(cfg, root/'fits')
            for key, value in [('model_identity', 'other'), ('source_commit', 'b'*40),
                               ('capture_id', 'other'), ('prefix_tokens', [1]*9)]:
                with self.assertRaisesRegex(ValueError, 'binding'):
                    convert.verify_reload({**cfg, key: value}, root/'fits')
            (root/'prefix.state').write_bytes(b'other snapshot')
            with self.assertRaisesRegex(ValueError, 'binding'):
                convert.verify_reload(cfg, root/'fits')
            (root/'prefix.state').write_bytes(b'model-free-prefix-state')
            with (root/'fits'/'carrier.bin').open('ab') as out:
                out.write(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'binding'):
                convert.verify_reload(cfg, root/'fits')

    def test_driver_wrapper_refuses_before_native_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root/'config.json'
            for cfg in (dict(source_commit='wrong', mode='capture'),
                        dict(source_commit=run_driver.PIN, mode='reload'),
                        dict(source_commit=run_driver.PIN, mode='unknown')):
                path.write_text(json.dumps(cfg))
                with patch('run_driver.subprocess.run') as native:
                    with self.assertRaises(ValueError):
                        run_driver.run('/unused', path)
                    native.assert_not_called()

    @unittest.skipUnless(os.environ.get('AM_BUNDLE_TEST'), 'set AM_BUNDLE_TEST to compiled native reader test')
    def test_native_reader_and_malformed_bundle_refusals(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_fixture(root)
            good = (root/'fits'/'carrier.bin').read_bytes()
            exe = os.environ['AM_BUNDLE_TEST']
            result = subprocess.run([exe, str(root/'fits'/'carrier.bin')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            print(result.stdout.strip())
            for bad in (b'badmagic' + good[8:], good[:4], good[:-1], good + b'x',
                        good[:8]+struct.pack('<I', 257)+good[12:],
                        good[:32]+struct.pack('<III', 3, 256, 512)+good[44:],
                        good[:44]+struct.pack('<f', float('nan'))+good[48:],
                        good[:24]+struct.pack('<q', 0)+good[32:],
                        good[:108]+struct.pack('<I', 3)+good[112:]):
                path = root / 'bad.bin'; path.write_bytes(bad)
                refused = subprocess.run([exe, str(path)], capture_output=True, text=True)
                self.assertNotEqual(refused.returncode, 0, 'native reader accepted malformed carrier')


if __name__ == '__main__':
    unittest.main()
