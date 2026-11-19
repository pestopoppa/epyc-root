import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from capture import reference
import compact_check
import run_driver
from convert import convert
from fit import digest
import test_convert


class CompactTests(unittest.TestCase):
    def fixture(self, root):
        # Original rows are permuted, suffix values are deliberately extreme.
        native, provenance, _ = test_convert.ConvertTests().fixture(root)
        converted = root / 'converted'
        record = convert(native, provenance, converted, 2)
        # inputs() uses the driver's canonical location.
        if Path(provenance) != native.parent / 'PROVENANCE.json':
            (native.parent / 'PROVENANCE.json').write_bytes(Path(provenance).read_bytes())
        # Conversion binds provenance bytes; preserve the exact original record.
        out = root / 'reload'
        (out / 'native').mkdir(parents=True)
        rows = [-1, 9, 10, 0, -1]
        for layer in (3, 7):
            q = np.arange(8, dtype=np.float32).reshape(1, 4, 1, 2) / 8
            k = np.zeros((1, 2, 5, 2), dtype=np.float32)
            v = np.zeros((1, 2, 5, 3), dtype=np.float32)
            mask = np.full((1, 4, 4, 5), -np.inf, dtype=np.float32)
            for head in range(2):
                fit = converted / f'layer-{layer}-head-{head}-fit' / 'carrier.npz'
                with np.load(fit) as z:
                    # Deliberately scatter original-position order [0,9] into [3,1].
                    v[0, head, [3, 1]] = z['C2'].astype(np.float16).astype(np.float32)
                    mask[0, head*2:head*2+2, 0, 3] = np.float16(z['beta'][0])
                    mask[0, head*2:head*2+2, 0, 1] = np.float16(z['beta'][1])
                v[0, head, 2] = [3, 2, 1]
                mask[0, head*2:head*2+2, 0, 2] = 0
            m = dict(schema='epyc.am.native-layer.v1', layer=layer, attention_scale=0.5, tensors={})
            tensors = dict(Q=q, K=k, V=v, mask=mask, output=np.zeros((1, 1, 4, 3), dtype=np.float32))
            tensors['output'][0] = reference(m, tensors)
            for name, a in tensors.items():
                filename = f'layer-{layer}-{name}.f32'
                a.astype('<f4').tofile(out / 'native' / filename)
                m['tensors'][name] = dict(file=filename, ne=list(reversed(a.shape)))
            (out / 'native' / f'layer-{layer}.json').write_text(json.dumps(m))
        complete = out / 'native' / 'COMPLETE.json'
        complete.write_text(json.dumps(dict(schema='epyc.am.native-capture.v1', layers=[3, 7])))
        p = {k: record['provenance'][k] for k in ('source_commit', 'model_identity', 'capture_id')}
        p.update(schema='epyc.am.compact-provenance.v1', cache_row_positions=rows, query_positions=[10],
                 conversion_sha256=digest(converted / 'CONVERT.json'), complete_sha256=digest(complete))
        (out / 'COMPACT.json').write_text(json.dumps(p))
        return native, converted, out

    def test_native_integrity_and_frozen_prefix_quality_are_separate(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self.fixture(Path(td))
            result = compact_check.check(*paths)
            for layer in result['layers']:
                self.assertLess(layer['native_vs_compact_oracle']['relative_l2'], 1e-7)
                self.assertGreater(layer['frozen_prefix_quality_on_reload_queries']['cosine_min'], 0.999999)
            out = paths[2] / 'native' / 'layer-3-output.f32'
            np.zeros((1, 1, 4, 3), dtype='<f4').tofile(out)
            bad = compact_check.check(*paths)['layers'][0]
            self.assertAlmostEqual(bad['native_vs_compact_oracle']['relative_l2'], 1)
            self.assertGreater(bad['frozen_prefix_quality_on_reload_queries']['cosine_min'], 0.999999)

    def test_loaded_values_beta_keys_and_padding_refused(self):
        for name, index, value in [('V', (0, 0, 3, 0), 99), ('K', (0, 0, 1, 0), 1),
                                   ('mask', (0, 3, 0, 1), -3), ('mask', (0, 0, 0, 4), 0)]:
            with self.subTest(name=name, index=index), tempfile.TemporaryDirectory() as td:
                paths = self.fixture(Path(td))
                file = paths[2] / 'native' / f'layer-3-{name}.f32'
                shapes = {'V': (1, 2, 5, 3), 'K': (1, 2, 5, 2), 'mask': (1, 4, 4, 5)}
                a = np.fromfile(file, dtype='<f4').reshape(shapes[name])
                a[index] = value
                a.tofile(file)
                with self.assertRaisesRegex(ValueError, 'native K/C2/beta'):
                    compact_check.check(*paths)

    def test_identity_row_map_original_and_fit_tampering_refused(self):
        for defect in ('identity', 'row', 'original', 'fit'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as td:
                paths = self.fixture(Path(td))
                if defect in ('identity', 'row'):
                    path = paths[2] / 'COMPACT.json'
                    p = json.loads(path.read_text())
                    if defect == 'identity':
                        p['capture_id'] = 'another-capture'
                    else:
                        p['cache_row_positions'][0] = 0
                    path.write_text(json.dumps(p))
                else:
                    path = (paths[0] / 'layer-3-K.f32' if defect == 'original' else
                            paths[1] / 'layer-3-head-0-fit' / 'carrier.npz')
                    with path.open('ab') as f:
                        f.write(b'!')
                with self.assertRaises(ValueError):
                    compact_check.check(*paths)

    def test_wrapper_requires_original_then_seals_checked_reload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, converted, out = self.fixture(root)
            cp = out / 'COMPACT.json'
            raw = json.loads(cp.read_text())
            cp.unlink()
            (out / 'COMPACT.raw.json').write_text(json.dumps(raw))
            (out / 'RESULT.json').write_text(json.dumps(dict(
                schema='epyc.am.native-driver.v1', mode='reload', decoded_tokens=1, captured_reload=True)))
            config = {k: raw[k] for k in ('source_commit', 'model_identity', 'capture_id')}
            config.update(mode='reload', out=str(out), prefix_state=str(root / 'prefix.state'),
                          carrier=str(converted / 'carrier.bin'), prefix_tokens=[1]*10,
                          capture_reload=True, decode_steps=1)
            cfg = root / 'config.json'
            cfg.write_text(json.dumps(config))
            with patch('run_driver.PIN', raw['source_commit']), patch('run_driver.subprocess.run') as native:
                with self.assertRaisesRegex(ValueError, 'requires original'):
                    run_driver.run('/unused', cfg, converted)
                native.assert_not_called()
                run_driver.run('/unused', cfg, converted, original)
                native.assert_called_once()
            self.assertTrue(cp.is_file())
            result = json.loads((out / 'CHECK.json').read_text())
            self.assertEqual(len(result['layers']), 2)

    def test_zero_norm_quality_is_undefined(self):
        m = compact_check.metrics(np.zeros((2, 3)), np.ones((2, 3)))
        self.assertEqual(m['undefined_cosines'], 2)
        self.assertIsNone(m['cosine_min'])


if __name__ == '__main__':
    unittest.main()
