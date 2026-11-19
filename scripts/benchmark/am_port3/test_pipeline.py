import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pipeline as p


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.model = self.root / 'prepared-model'
        self.model.write_bytes(b'fixture; not model weights')
        self.tokens = self.root / 'tokens.json'
        self.tokens.write_text(json.dumps(dict(prefix_tokens=list(range(10)),
                              calibration_tokens=[1, 2, 3, 4], warmup_tokens=[1], probe_tokens=[2, 3])))
        self.plan = dict(schema='epyc.am.pipeline-plan.v1', source_commit=p.PIN,
                         model=str(self.model), model_identity='a'*64, model_stat=p.model_stat(self.model),
                         tokens=str(self.tokens), tokens_sha256=p.digest(self.tokens), expected_layers=list(range(16)),
                         threads=1, control_pairs=3, phase_timeout_s=60, n_gpu_layers=999,
                         min_throughput_ratio=.98, native_relative_l2_limit=.001,
                         device_vram_path='/sys/class/drm/card0/device/mem_info_vram_used', builds={})
        for key in p.KINDS:
            path = self.root / key / 'BUILD.json'
            path.parent.mkdir()
            path.write_text(key)
            self.plan['builds'][key] = str(path)
        self.events = []
        self.control_pass = True

        def verify(path):
            variant, backend = Path(path).parent.name.split('_')
            return dict(variant=variant, backend=backend, architecture='gfx90a' if backend == 'hip' else None)
        self.patch(p.build, 'verify', verify)

    def patch(self, obj, name, value):
        patcher = patch.object(obj, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def check():
        return dict(schema='epyc.am.compact-check.v1', layers=[dict(layer=i,
                    frozen_prefix_quality_on_reload_queries=dict(cosine_min=.96, undefined_cosines=0),
                    native_vs_compact_oracle=dict(relative_l2=.0001)) for i in range(16)])

    def fake_execution(self):
        outer = self
        class Executor:
            def __init__(self, root, bindir, **settings):
                self.root = Path(root)
                outer.events.append(('executor', self.root.name, settings))
            def __call__(self, argv, **kwargs):
                self.root.mkdir(parents=True)
                (self.root / 'EXECUTION.json').write_text('{"test_fixture":true}')
        self.patch(p, 'Executor', Executor)

        def control(driver, config, bindir, execute):
            c = json.loads(Path(config).read_text())
            self.events.append(('control', Path(c['out']).name, c))
            Path(c['out']).mkdir()
            execute([str(driver), str(config)], env={}, check=True)
        self.patch(p.controls, 'run', control)
        self.patch(p.controls, 'compare', lambda *args: dict(exact_logits_pass=self.control_pass,
                         throughput_threshold_pass=True, median_throughput_ratio=1.01))

        def driver(binary, config, converted=None, original=None, execute=None):
            c = json.loads(Path(config).read_text())
            root = Path(c['out'])
            root.mkdir()
            self.events.append((c['mode'], c, converted, original))
            execute([str(binary), str(config)], check=True)
            if c['mode'] == 'capture':
                (root / 'native').mkdir()
                (root / 'prefix.state').write_bytes(b'fixture state')
                (root / 'PROVENANCE.json').write_text('{}')
                (root / 'RESULT.json').write_text('{"prefix_greedy_token":42}')
            else:
                p.save(root / 'RESULT.json', dict(decoded_tokens=c['decode_steps'], captured_reload=c['capture_reload']))
                p.save(root / 'CHECK.json', self.check())
        self.patch(p.run_driver, 'run', driver)

        def convert(native, provenance, out, keep):
            self.events.append(('convert', native, provenance, keep))
            out.mkdir()
            (out / 'carrier.bin').write_bytes(b'fixture carrier')
        self.patch(p, 'convert', convert)

    def run_plan(self):
        config = self.root / 'plan.json'
        p.save(config, self.plan)
        return p.run(config, self.root / 'out')

    def test_full_orchestration_uses_native_original_and_32k(self):
        self.fake_execution()
        result = self.run_plan()
        self.assertEqual(result['stopped_at'], 'complete')
        self.assertEqual(result['decoded_tokens'], 32768)
        self.assertEqual(len(result['quality']['layers_at_cosine_095']), 16)
        control = [e for e in self.events if e[0] == 'control']
        self.assertEqual([e[1] for e in control[:6]], ['control-cpu-0-baseline', 'control-cpu-0-patched',
                         'control-cpu-1-patched', 'control-cpu-1-baseline', 'control-cpu-2-baseline', 'control-cpu-2-patched'])
        self.assertEqual(len(control), 12)
        reload = next(e for e in self.events if e[0] == 'reload')
        self.assertEqual(reload[3], self.root / 'out/capture/native')
        self.assertEqual(reload[1]['first_decode_token'], 42)
        self.assertTrue(reload[1]['capture_reload'])
        self.assertEqual(reload[1]['decode_steps'], 1)
        stability = [e for e in self.events if e[0] == 'reload'][1]
        self.assertEqual(stability[1]['decode_steps'], 32768)
        self.assertFalse(stability[1]['capture_reload'])
        self.assertIsNone(stability[3])
        self.assertEqual(next(e for e in self.events if e[0] == 'convert')[3], 2)
        self.assertEqual(len(result['execution_sha256']), 15)

    def test_quality_failure_stops_before_32k(self):
        self.fake_execution()
        original = self.check()
        for row in original['layers']:
            row['frozen_prefix_quality_on_reload_queries']['cosine_min'] = .5
        self.patch(self, 'check', lambda: original)
        result = self.run_plan()
        self.assertEqual(result['stopped_at'], 'compact-quality')
        self.assertEqual(result['decoded_tokens'], 1)
        self.assertEqual(len([e for e in self.events if e[0] == 'reload']), 1)
        self.assertFalse((self.root / 'out/stability').exists())

    def test_default_off_failure_stops_before_fitting(self):
        self.fake_execution()
        self.control_pass = False
        result = self.run_plan()
        self.assertEqual(result['stopped_at'], 'default-off-cpu')
        self.assertFalse(any(e[0] in ('capture', 'reload', 'convert') for e in self.events))
        self.assertNotIn('decoded_tokens', result)

    def test_model_or_tokens_changed_refused(self):
        self.model.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'model file'):
            p.validate(self.plan)
        self.plan['model_stat'] = p.model_stat(self.model)
        self.tokens.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'token content'):
            p.validate(self.plan)

    def test_invalid_inputs_before_model_execution(self):
        for key, value in [('control_pairs', 2), ('threads', 0), ('n_gpu_layers', 0),
                           ('phase_timeout_s', 0), ('min_throughput_ratio', float('nan')),
                           ('native_relative_l2_limit', .1), ('model_identity', 'unpinned'),
                           ('device_vram_path', '/tmp/fake-vram'), ('expected_layers', [0]*16)]:
            plan = dict(self.plan, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                p.validate(plan)

    def test_fractional_compression_and_bool_tokens_refused(self):
        for prefix in ([1]*11, [True]*10):
            t = json.loads(self.tokens.read_text())
            t['prefix_tokens'] = prefix
            self.tokens.write_text(json.dumps(t))
            self.plan['tokens_sha256'] = p.digest(self.tokens)
            with self.assertRaises(ValueError):
                p.validate(self.plan)

    def test_wrong_build_backend_refused(self):
        self.plan['builds']['baseline_cpu'] = self.plan['builds']['baseline_hip']
        with self.assertRaisesRegex(ValueError, 'variant/backend'):
            p.validate(self.plan)

    def test_layer_verdict_uses_minimum_cosine_and_fourteen_layers(self):
        check = self.check()
        for i in range(2):
            check['layers'][i]['frozen_prefix_quality_on_reload_queries']['cosine_min'] = .94
        q = p.quality(check, list(range(16)), .001)
        self.assertTrue(q['prefix_quality_screen_pass'])
        check['layers'][2]['frozen_prefix_quality_on_reload_queries']['undefined_cosines'] = 1
        self.assertFalse(p.quality(check, list(range(16)), .001)['prefix_quality_screen_pass'])
        check['layers'][3]['native_vs_compact_oracle']['relative_l2'] = .01
        self.assertFalse(p.quality(check, list(range(16)), .001)['native_integrity_screen_pass'])

    def test_missing_duplicate_nonfinite_layer_refused(self):
        for defect in ('missing', 'duplicate', 'nan'):
            check = self.check()
            if defect == 'missing':
                check['layers'].pop()
            elif defect == 'duplicate':
                check['layers'][0]['layer'] = 1
            else:
                check['layers'][0]['native_vs_compact_oracle']['relative_l2'] = float('nan')
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                p.quality(check, list(range(16)), .001)

    def test_failed_phase_never_writes_result(self):
        self.fake_execution()
        def fail(*args, **kwargs):
            raise RuntimeError('native child failed')
        self.patch(p.controls, 'run', fail)
        with self.assertRaisesRegex(RuntimeError, 'child failed'):
            self.run_plan()
        self.assertFalse((self.root / 'out/RESULT.json').exists())

    def test_changed_build_receipt_during_phase_refused(self):
        self.fake_execution()
        def mutate(driver, config, bindir, execute):
            Path(self.plan['builds']['patched_hip']).write_text('substituted')
            execute([str(driver), str(config)], check=True)
        self.patch(p.controls, 'run', mutate)
        with self.assertRaisesRegex(ValueError, 'receipts changed'):
            self.run_plan()
        self.assertFalse((self.root / 'out/RESULT.json').exists())


if __name__ == '__main__':
    unittest.main()
