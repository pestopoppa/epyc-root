import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from apply_integration import PIN
import controls
from fit import digest


class ControlTests(unittest.TestCase):
    def config(self, root):
        return dict(mode='control', model='/prepared/model.gguf', model_identity='prepared-sha256',
                    source_commit=PIN, prefix_tokens=[1, 2], warmup_tokens=[3], probe_tokens=[4, 5],
                    n_ctx=8, threads=1, n_gpu_layers=0, out=str(root))

    def raw(self, root, libraries=(), logits=None, times=(1., 1.)):
        root.mkdir()
        logits = np.array([[1, 0], [2, 0]], dtype='<f4') if logits is None else np.asarray(logits, dtype='<f4')
        logits.tofile(root / 'logits.f32')
        result = dict(schema='epyc.am.default-off-control.v1', mode='control',
                      model_identity='prepared-sha256', source_commit=PIN, n_vocab=logits.shape[1],
                      probe_steps=2, decode_seconds=list(times), mapped_libraries=list(libraries), trace='logits.f32')
        (root / 'RESULT.json').write_text(json.dumps(result))

    def fixture(self, root, **kwargs):
        self.raw(root, **kwargs)
        c = self.config(root)
        s = dict(schema='epyc.am.default-off-seal.v1', settings=controls.validate(c),
                 control_source_sha256='same-source', artifacts_sha256={'binary': 'a'},
                 mapped_libraries_sha256={'lib': 'b'}, environment={}, affinity=[0],
                 result_sha256=digest(root / 'RESULT.json'), trace_sha256=digest(root / 'logits.f32'))
        (root / 'SEAL.json').write_text(json.dumps(s))
        return s

    def test_kl_against_independent_two_outcome_oracle(self):
        a = np.array([[math.log(0.8), math.log(0.2)]], dtype=np.float64)
        b = np.array([[math.log(0.4), math.log(0.6)]], dtype=np.float64)
        r = controls.logit_metrics(a, b)
        want = 0.8 * math.log(2) + 0.2 * math.log(1/3)
        self.assertAlmostEqual(r['kld_mean'], want, places=14)
        self.assertFalse(r['greedy_tokens_equal'])
        self.assertFalse(r['logits_byte_equal'])
        self.assertGreater(r['max_abs_logit_error'], 1)

    def test_shift_invariance_does_not_mask_logit_change(self):
        a = np.array([[10000, 10001], [-10000, -9998]], dtype=np.float32)
        r = controls.logit_metrics(a, a + 100)
        self.assertAlmostEqual(r['kld_max'], 0)
        self.assertEqual(r['max_abs_logit_error'], 100)
        self.assertTrue(r['greedy_tokens_equal'])
        self.assertFalse(r['logits_byte_equal'])
        self.assertTrue(controls.logit_metrics(a, a)['logits_byte_equal'])

    def test_prepared_input_bounds_and_types(self):
        cases = [('prefix_tokens', [1]), ('warmup_tokens', []), ('probe_tokens', [True]),
                 ('probe_tokens', [-1]), ('probe_tokens', [1] * 257), ('n_ctx', 3),
                 ('n_ctx', 36865), ('threads', True), ('n_gpu_layers', -1), ('source_commit', 'old')]
        for key, value in cases:
            with self.subTest(key=key, value=str(value)[:20]):
                with self.assertRaises(ValueError):
                    controls.validate(dict(self.config(Path('/unused')), **{key: value}))

    def test_runtime_seal_binds_actual_mapped_libraries_and_disables_beta(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            binary = root / 'am-control'; binary.write_bytes(b'executable')
            libs = root / 'bin'; libs.mkdir()
            for name in ('libllama.so.0', 'libggml-base.so.0', 'libggml-cpu.so.0'):
                (libs / name).write_bytes(name.encode())
            paths = sorted(str(p) for p in libs.iterdir())
            config = root / 'config.json'; config.write_text(json.dumps(self.config(root / 'run')))

            def invoke(cmd, env, check):
                self.assertEqual(cmd, [str(binary), str(config)])
                self.assertEqual(env['LD_LIBRARY_PATH'], str(libs))
                self.assertNotIn('LLAMA_KV_AM_BETA', env)
                self.assertTrue(check)
                self.raw(root / 'run', libraries=paths)

            with patch.dict(controls.os.environ, {'LLAMA_KV_AM_BETA': '1'}):
                with patch.object(controls.subprocess, 'run', side_effect=invoke):
                    seal = controls.run(binary, config, libs)
            self.assertEqual(seal['mapped_libraries_sha256'], {p: digest(p) for p in paths})
            self.assertEqual(seal['artifacts_sha256'][str(binary)], digest(binary))
            self.assertTrue((root / 'run' / 'SEAL.json').is_file())

    def test_stale_or_foreign_libraries_refuse_completion_seal(self):
        for defect in ('foreign', 'mutated', 'no-llama', 'bad-trace'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as td:
                root = Path(td); libs = root / 'bin'; libs.mkdir()
                for name in ('libllama.so', 'libggml-base.so'):
                    (libs / name).write_bytes(b'original')
                binary = root / 'am-control'; binary.write_bytes(b'executable')
                foreign = root / 'libggml-hip.so'; foreign.write_bytes(b'foreign')
                config = root / 'config.json'; config.write_text(json.dumps(self.config(root / 'run')))

                def invoke(*args, **kwargs):
                    mapped = [str(p) for p in libs.iterdir()]
                    if defect == 'foreign':
                        mapped.append(str(foreign))
                    elif defect == 'no-llama':
                        mapped = [str(libs / 'libggml-base.so')]
                    self.raw(root / 'run', libraries=mapped)
                    if defect == 'mutated':
                        (libs / 'libllama.so').write_bytes(b'changed')
                    elif defect == 'bad-trace':
                        (root / 'run' / 'logits.f32').write_bytes(b'bad')

                with patch.object(controls.subprocess, 'run', side_effect=invoke):
                    with self.assertRaises(ValueError):
                        controls.run(binary, config, libs)
                self.assertFalse((root / 'run' / 'SEAL.json').exists())

    def test_trace_tamper_size_nonfinite_times_and_geometry_refused(self):
        for defect in ('hash', 'size', 'nan', 'time', 'vocab', 'identity'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as td:
                root = Path(td) / 'run'; s = self.fixture(root)
                trace, result = root / 'logits.f32', root / 'RESULT.json'
                if defect in ('hash', 'size', 'nan'):
                    if defect == 'nan':
                        np.array([[np.nan, 0], [1, 0]], dtype='<f4').tofile(trace)
                    else:
                        trace.write_bytes(b'bad')
                    if defect != 'hash':
                        s['trace_sha256'] = digest(trace)
                else:
                    r = json.loads(result.read_text())
                    if defect == 'time': r['decode_seconds'][0] = 0
                    if defect == 'vocab': r['n_vocab'] = 10**9
                    if defect == 'identity': r['model_identity'] = 'wrong-model'
                    result.write_text(json.dumps(r)); s['result_sha256'] = digest(result)
                with self.assertRaises(ValueError):
                    controls.read_trace(root, s)

    def groups(self, root):
        baseline, patched = [], []
        for label, group, times in [('b', baseline, [1., 2., 1.]), ('p', patched, [2., 4., 2.])]:
            for i, duration in enumerate(times):
                d = root / f'{label}-{i}'; self.fixture(d, times=[duration, duration]); group.append(d)
        return baseline, patched

    def test_fixed_replicates_throughput_direction_and_exact_logits(self):
        with tempfile.TemporaryDirectory() as td:
            b, p = self.groups(Path(td))
            r = controls.compare(b, p, 0.95)
            self.assertEqual(r['median_throughput_ratio'], 0.5)
            self.assertFalse(r['throughput_threshold_pass'])
            self.assertTrue(r['exact_logits_pass'])
            r = controls.compare(p, b, 0.95)
            self.assertEqual(r['median_throughput_ratio'], 2)
            self.assertTrue(r['throughput_threshold_pass'])

    def test_baseline_nondeterminism_and_patched_logit_shift_fail_exact_gate(self):
        for which in (0, 1):
            with tempfile.TemporaryDirectory() as td:
                b, p = self.groups(Path(td))
                d = (b, p)[which][1]; t = d / 'logits.f32'
                (np.fromfile(t, dtype='<f4') + 1).tofile(t)
                s = json.loads((d / 'SEAL.json').read_text()); s['trace_sha256'] = digest(t)
                (d / 'SEAL.json').write_text(json.dumps(s))
                r = controls.compare(b, p, 0.95)
                self.assertFalse(r['exact_logits_pass'])
                self.assertTrue(all(m['kld_max'] == 0 for m in r['logit_metrics']))

    def test_mismatched_protocol_and_variant_artifacts_refused(self):
        for key in ('settings', 'control_source_sha256', 'environment', 'affinity', 'artifacts_sha256'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as td:
                b, p = self.groups(Path(td)); path = p[1] / 'SEAL.json'
                s = json.loads(path.read_text())
                if key == 'settings': s[key]['probe_tokens'][0] = 9
                else: s[key] = {'different': 'value'} if key != 'affinity' else [1]
                path.write_text(json.dumps(s))
                with self.assertRaises(ValueError): controls.compare(b, p, 0.95)

    def test_no_single_sample_or_duplicated_run_gate(self):
        with tempfile.TemporaryDirectory() as td:
            b, p = self.groups(Path(td))
            for left, right, threshold in [(b[:1], p[:1], .95), (b, p[:2], .95),
                                            ([b[0]] * 3, p, .95), (b, p, float('nan')),
                                            (b, p, 0), (b, p, 1.01)]:
                with self.assertRaises(ValueError): controls.compare(left, right, threshold)


if __name__ == '__main__':
    unittest.main()
