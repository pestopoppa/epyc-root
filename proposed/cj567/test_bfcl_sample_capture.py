"""Original-source supported-frame capture controls; no model inference."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bfcl_sample import prepare
from bfcl_sample_capture import BoundSample, materialize
from bfcl_capture_run import capture_case
from bfcl_native import OfficialV3


class SupportedCaptureControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checkout = os.environ['BFCL_CHECKOUT']
        cls.manifest = prepare(cls.checkout, 20, 20261120)
        cls.bundle = materialize(cls.checkout, cls.manifest)
        cls.bridge = OfficialV3(cls.checkout)
        cls.identity = {'model': 'control', **{k: 'a' * 64 for k in (
            'model_sha256', 'server_binary_sha256', 'build_manifest_sha256', 'runtime_manifest_sha256')}}

    def binding(self, tmp, bundle=None):
        raw = json.dumps(bundle or self.bundle).encode()
        path = Path(tmp) / 'sample.json'
        path.write_bytes(raw)
        return BoundSample(path, hashlib.sha256(raw).hexdigest())

    def test_all_120_selected_inputs_reach_native_capture_and_official_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            binding = self.binding(tmp)
            for row in binding.rows():
                out = Path(tmp) / row['case']['id']
                seen = []
                def query(payload):
                    seen.append(payload)
                    events = [json.loads(line)['event'] for line in out.read_text().splitlines()]
                    self.assertEqual(events[-1], {'kind': 'exposure', 'request': payload})
                    self.assertEqual(events[0]['supported_sample']['prepared_sample_sha256'], binding.sha256)
                    self.assertNotIn('gold', payload)
                    return {'choices': []}
                with self.subTest(qid=row['case']['id']):
                    verdict = capture_case(self.bridge, row, 'control', self.identity, None,
                        out, query, software_control=True, sample_binding=binding)
                    self.assertIsNone(verdict['valid'])
                    self.assertEqual(len(seen), 1)
                    self.assertEqual(seen[0], self.bridge.request(row['case'], row['category'], 'control')[0])

    def test_row_mutation_refuses_before_exposure_and_binding_is_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            binding = self.binding(tmp)
            for field in ('case', 'gold', 'category'):
                row = binding.rows()[0]
                if field == 'category':
                    row[field] = 'sql'
                else:
                    row[field]['tampered'] = True
                out = Path(tmp) / field
                with self.assertRaises(ValueError):
                    capture_case(self.bridge, row, 'control', self.identity, None, out,
                        lambda _: self.fail('exposure'), software_control=True, sample_binding=binding)
                self.assertFalse(out.exists())
            self.assertNotIn('tampered', binding.rows()[0]['case'])

    def test_prepared_file_digest_and_order_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            binding = self.binding(tmp)
            path = Path(tmp) / 'sample.json'
            path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'digest'):
                BoundSample(path, binding.sha256)
            for damage in ('order', 'gold_id', 'source', 'upstream'):
                bundle = copy.deepcopy(self.bundle)
                if damage == 'order':
                    bundle['cases'].reverse()
                elif damage == 'gold_id':
                    bundle['cases'][0]['gold']['id'] = 'wrong'
                elif damage == 'source':
                    next(iter(bundle['sample']['sources'].values()))['sha256'] = '0' * 64
                else:
                    bundle['sample']['upstream_commit'] = '0' * 40
                with self.subTest(damage=damage), self.assertRaises(ValueError):
                    self.binding(tmp, bundle)

    def test_fleet_supported_frame_passes_binding_and_stops_on_unknown(self):
        import time
        from unittest.mock import Mock
        from bfcl_fleet_run import run
        from bfcl_residency import fingerprint
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = json.dumps(self.bundle).encode()
            (root / 'SELECTION.json').write_bytes(raw)
            model = root / 'weight'; model.write_bytes(b'fixture')
            (root / 'MODEL.json').write_text(json.dumps({'path': str(model),
                'stat': fingerprint(model.stat()), 'sha256': 'a' * 64}))
            (root / 'CONFIG.json').write_text(json.dumps({'model': 'control',
                'server': '/fixture', 'server_binary_sha256': 'b' * 64,
                'library_path': '/fixture', 'checker': self.checkout, 'catalog': '',
                'cohort': 'supported-frame', 'selection_sha256': hashlib.sha256(raw).hexdigest()}))
            (root / 'BUILD.json').write_text('{}')
            grants = root / 'grants'; grants.mkdir(); (grants / 'fixture.grant').write_text('grant')
            process = Mock(pid=123, returncode=-15); process.poll.return_value = None
            health = Mock(); health.__enter__ = Mock(return_value=Mock(status=200))
            health.__exit__ = Mock(return_value=False)
            opener = Mock(); opener.open.return_value = health
            with patch.dict(os.environ, {'FILLER_SMOKE': '0', 'FILLER_ID': 'fixture',
                    'FILLER_GRANTS_DIR': str(grants), 'FILLER_DEADLINE': str(time.time() + 10000)}), \
                 patch('bfcl_fleet_run.subprocess.Popen', return_value=process), \
                 patch('bfcl_fleet_run.build_opener', return_value=opener), \
                 patch('bfcl_fleet_run.LocalNativeTransport'), \
                 patch('bfcl_fleet_run.stop_server'), \
                 patch('bfcl_fleet_run.OfficialV3', return_value=self.bridge), \
                 patch('bfcl_fleet_run.capture_case', return_value={'valid': None}) as capture:
                run(root)
            capture.assert_called_once()
            self.assertIsInstance(capture.call_args.kwargs['sample_binding'], BoundSample)
            result = json.loads((root / 'run/RESULT.json').read_bytes())
            self.assertEqual(result['benchmark'], 'bfcl_v3_native_supported_frame_local')
            self.assertEqual(result['status'], 'partial')
            self.assertEqual((result['completed'], result['total'], result['unknown']), (1, 120, 1))
            self.assertIsNone(result['score'])
            self.assertEqual(sum(v['completed'] for v in result['strata'].values()), 1)

    def test_materialize_reconstructs_selection_and_source_identity(self):
        for damage in ('id', 'source', 'seed'):
            manifest = copy.deepcopy(self.manifest)
            if damage == 'id':
                manifest['strata']['simple']['ids'][0] = 'simple_99999'
            elif damage == 'source':
                next(iter(manifest['sources'].values()))['blob'] = '0' * 40
            else:
                manifest['seed'] += 1
            with self.subTest(damage=damage), self.assertRaisesRegex(ValueError, 'reconstruction'):
                materialize(self.checkout, manifest)
        with patch.dict(os.environ, {'FILLER_ID': 'control'}), self.assertRaises(ValueError):
            materialize(self.checkout, self.manifest)


if __name__ == '__main__':
    unittest.main()
