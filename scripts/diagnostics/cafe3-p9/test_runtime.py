"""Row-boundary refusal controls, without launching models or a native process."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('p9_runtime', Path(__file__).with_name('runtime.py'))
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
context = runtime.context


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patcher = patch.object(runtime, 'ROOT', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        corpus = self.root / 'corpus.jsonl'
        corpus.write_text('{"id":"a","prompt":"Write a loop."}\n')
        self.prepared = dict(schema='epyc.cafe3.prepared.v1', models={})
        for role in ('target', 'draft', 'corpus'):
            path = corpus if role == 'corpus' else self.root / (role + '.gguf')
            if role != 'corpus':
                path.write_text(role)
            item = dict(path=str(path), sha256=context.sha256(path), identity=context.file_identity(str(path)))
            if role == 'corpus':
                self.prepared['corpus'] = item
            else:
                self.prepared['models'][role] = item
        self.protocol = dict(schema='epyc.cafe3.protocol.v1', corpus=self.prepared['corpus'],
                             p9_policy=runtime.p9_grade.POLICY, repetitions=2,
                             arms=['static-0', 'static-1', 'adaptive'],
                             request_settings=dict(n_predict=256, seed=42, timeout_s=600,
                                                   arm_widths={'static-0': 0, 'static-1': 1, 'adaptive': 1}))
        self.inventory = dict(schema='epyc.cafe3.p9-inputs.v1', runtime={}, row='test-row', port=18792,
                              prepared=runtime.write(self.root / 'prepared.json', self.prepared),
                              protocol=runtime.write(self.root / 'protocol.json', self.protocol), build={'fixture': True})
        self.digest = runtime.write(self.root / 'inputs.json', self.inventory)['sha256']
        self.builder = patch.object(context, 'build_receipt', return_value=({}, self.root / 'llama-server')).start()
        self.addCleanup(patch.stopall)

    def test_inputs_never_hash_weights(self):
        original = context.sha256
        def no_weights(path):
            self.assertFalse(str(path).endswith('.gguf'), 'grant-time weight hash')
            return original(path)
        with patch.object(context, 'sha256', side_effect=no_weights):
            runtime.inputs(self.digest)

    def test_model_mutation_refuses_before_build(self):
        Path(self.prepared['models']['draft']['path']).write_text('modified')
        with self.assertRaisesRegex(ValueError, 'prepared input drift'):
            runtime.inputs(self.digest)
        self.builder.assert_not_called()

    def test_incomplete_static_coverage_refuses(self):
        self.protocol['arms'].remove('static-1')
        Path(self.inventory['protocol']['path']).unlink()
        self.inventory['protocol'] = runtime.write(self.root / 'protocol.json', self.protocol)
        (self.root / 'inputs.json').unlink()
        digest = runtime.write(self.root / 'inputs.json', self.inventory)['sha256']
        with self.assertRaisesRegex(ValueError, 'complete bounded'):
            runtime.inputs(digest)

    def test_smoke_cannot_seal_native_grant(self):
        with patch.dict(os.environ, FILLER_ID='test-row', FILLER_DRYRUN='1'):
            with self.assertRaisesRegex(ValueError, 'matching scheduled row'):
                runtime.seal_schedule(self.inventory, self.prepared, self.protocol, self.root / 'exe', self.root)

    def test_schedule_binds_grant_and_identical_argv(self):
        grant = self.root / 'grant'
        grant.write_text('regions=2-3 holds=cpu cpus=2-3')
        original = runtime.reference
        def local_grant(path):
            if str(path).startswith('/mnt/raid0/llm/tmp/compute-flags/grants/'):
                return original(grant)
            return original(path)
        original_read = Path.read_text
        def read_grant(path, *args, **kwargs):
            if str(path).startswith('/mnt/raid0/llm/tmp/compute-flags/grants/'):
                return original_read(grant)
            return original_read(path, *args, **kwargs)
        with patch.dict(os.environ, FILLER_ID='test-row', FILLER_DRYRUN='0', FILLER_CPUS='2-3', FILLER_THREADS='2'), \
                patch.object(runtime, 'reference', side_effect=local_grant), patch.object(Path, 'read_text', read_grant):
            ref = runtime.seal_schedule(self.inventory, self.prepared, self.protocol, self.root / 'exe', self.root)
        schedule = context.bound_json(ref)
        contexts = [context.bound_json(entry['context']) for entry in schedule['launches']]
        self.assertEqual([c['arm'] for c in contexts], self.protocol['arms'])
        self.assertTrue(all(c['argv'] == contexts[0]['argv'] for c in contexts))
        self.assertTrue(all(c['grant'] == original(grant) for c in contexts))
        self.assertEqual(len({c['journal'] for c in contexts}), 3)

    def test_negative_assessment_is_completed_but_tampering_refuses(self):
        schedule = runtime.write(self.root / 'schedule.json', {})
        capture = runtime.write(self.root / 'capture.jsonl', {})
        assessment = runtime.write(self.root / 'assessment.json', dict(schema='epyc.cafe3.p9-assessment.v1',
                                   verdict='fail', schedule=schedule, capture=capture))
        runtime.write(self.root / 'RESULT.json', dict(schema='epyc.cafe3.p9-result.v1', inventory_sha256=self.digest,
                      assessment=assessment, verdict='fail', schedule=schedule, capture=capture))
        runtime.check(self.digest)
        (self.root / 'capture.jsonl').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            runtime.check(self.digest)


if __name__ == '__main__':
    unittest.main()
