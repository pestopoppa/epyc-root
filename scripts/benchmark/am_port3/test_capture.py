import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

import capture


class CaptureTests(unittest.TestCase):
    def fixture(self, root):
        q = np.zeros((1, 4, 2, 2))
        k = np.ones((1, 2, 3, 2))
        v = np.arange(18).reshape(1, 2, 3, 3)
        mask = np.zeros((1, 1, 4, 3))
        mask[0, 0, 0, 2] = -np.inf
        actual = np.zeros((1, 2, 4, 3))
        for head in range(4):
            actual[0, 0, head] = v[0, head // 2, :2].mean(axis=0)
            actual[0, 1, head] = v[0, head // 2].mean(axis=0)
        manifest = {'schema': 'epyc.am.native-layer.v1', 'layer': 3,
                    'attention_scale': 0.5, 'tensors': {}}
        for name, a in dict(Q=q, K=k, V=v, mask=mask, output=actual).items():
            filename = f'layer-3-{name}.f32'
            a.astype('<f4').tofile(root / filename)
            manifest['tensors'][name] = dict(file=filename, ne=list(reversed(a.shape)))
        (root / 'layer-3.json').write_text(json.dumps(manifest))
        (root / 'COMPLETE.json').write_text(json.dumps(dict(schema='epyc.am.native-capture.v1', layers=[3])))
        return manifest

    def test_gqa_mapping_mask_and_output_axes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            result = capture.check(root)['layers'][0]
            self.assertLess(result['native_vs_numpy_max_abs'], 1e-12)
            self.assertEqual(result['query_heads'], 4)
            self.assertEqual(result['kv_heads'], 2)
            self.assertEqual(len(result['sha256']), 7)

    def test_incomplete_and_truncated_capture_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            (root / 'layer-3-Q.f32').write_bytes(b'')
            with self.assertRaisesRegex(ValueError, 'byte count'):
                capture.check(root)
            (root / 'COMPLETE.json').unlink()
            with self.assertRaises(FileNotFoundError):
                capture.check(root)

    def test_manifest_paths_cannot_escape_capture(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = self.fixture(root)
            m['tensors']['Q']['file'] = '../outside.f32'
            (root / 'layer-3.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, 'path'):
                capture.check(root)

    def test_wrong_native_output_and_invalid_mask_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            np.zeros((1, 2, 4, 3), dtype='<f4').tofile(root / 'layer-3-output.f32')
            self.assertGreater(capture.check(root)['layers'][0]['native_vs_numpy_relative_l2'], 0.99)
            np.full((1, 1, 4, 3), -np.inf, dtype='<f4').tofile(root / 'layer-3-mask.f32')
            with self.assertRaisesRegex(ValueError, 'fully masked'):
                capture.check(root)


if __name__ == '__main__':
    unittest.main()
