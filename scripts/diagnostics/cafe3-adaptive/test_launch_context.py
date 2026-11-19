"""Model-free launch custody regressions; never launches a native binary."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import launch_context as context


class LaunchContextTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.manifest_path = self.root / 'context.json'
        self.grant = Path('/mnt/raid0/llm/tmp/compute-flags/grants/unit-cafe3.grant')
        self.grant_text = 'regions=2-3 start=2026-11-19T12:00Z end=2026-11-19T13:00Z holds=c2,c3 cpus=2-3\n'
        self.now = 1795089660  # 2026-11-19 12:01 UTC
        self.env = dict(FILLER_ID='unit-cafe3', FILLER_CPUS='2-3', FILLER_THREADS='2',
                        FILLER_DEADLINE=str(self.now + 60), FILLER_STOPFILE=str(self.root / 'STOP'),
                        FILLER_NEEDGPU='0', LD_PRELOAD='/foreign/lib.so', LD_LIBRARY_PATH='/foreign')
        self.exe = self.root / 'llama-server'
        self.exe.write_bytes(b'not executable; tests never launch this')
        prepared = dict(schema='epyc.cafe3.prepared.v1', models={})
        for role in ('target', 'draft', 'corpus'):
            path = self.root / (role + ('.gguf' if role != 'corpus' else '.jsonl'))
            path.write_bytes(role.encode())
            item = dict(path=str(path), sha256=context.sha256(path), identity=context.file_identity(str(path)))
            if role == 'corpus':
                prepared['corpus'] = item
            else:
                prepared['models'][role] = item
        self.prepared = prepared
        protocol = dict(schema='epyc.cafe3.protocol.v1', corpus=prepared['corpus'],
                        arms=['adaptive', 'static-3'], repetitions=5, question='P9?',
                        decision_rule='P9: >=+1% vs best static; identity 100%; absorbing-state test',
                        checkpoints='each pair', stop_on_answer='all declared pairs complete',
                        stop_on_futility='stop on identity failure')
        self.argv = [str(self.exe), '-m', prepared['models']['target']['path'],
                     '--model-draft', prepared['models']['draft']['path'], '-t', '2', '-tb', '2',
                     '-ngl', '0', '--gpu-layers-draft', '0']
        self.manifest = dict(schema='epyc.cafe3.launch-context.v1', run='unit-run-1',
                             argv=self.argv, backend='cpu', build=self.save('build', {}),
                             prepared=self.save('prepared', prepared), corpus=prepared['corpus'],
                             protocol=self.save('protocol', protocol), arm='adaptive', row='unit-cafe3',
                             grant=dict(path=str(self.grant), sha256='a'*64),
                             placement=dict(cpus='2-3', threads=2, regions='2-3', holds='c2,c3'),
                             device_env={}, journal=str(self.root / 'rounds.jsonl'))
        self.builder = Mock(return_value=({'base': 'production-pinned'}, self.exe))
        self.addCleanup(patch.stopall)
        patch.object(context, 'build_receipt', self.builder).start()
        original_bound = context.bound_file
        patch.object(context, 'bound_file', side_effect=lambda ref: self.grant if ref == self.manifest['grant'] else original_bound(ref)).start()
        original_read = Path.read_text
        patch.object(Path, 'read_text', lambda path, *a, **kw: self.grant_text if path == self.grant else original_read(path, *a, **kw)).start()

    def save(self, name, value):
        path = self.root / (name + '.json')
        path.write_text(json.dumps(value))
        return dict(path=str(path), sha256=context.sha256(path))

    def validate(self, **kwargs):
        self.manifest_path.write_text(json.dumps(self.manifest))
        return context.validate_launch_context(str(self.manifest_path), context.sha256(self.manifest_path),
                                               kwargs.pop('argv', self.argv), environ=self.env,
                                               now=self.now, affinity=kwargs.pop('affinity', {2, 3}), **kwargs)

    def test_bound_isolated_plan_and_no_weight_hash(self):
        original = context.sha256
        def no_weights(path):
            self.assertFalse(str(path).endswith('.gguf'), 'weight hashing inside launch')
            return original(path)
        with patch.object(context, 'sha256', side_effect=no_weights):
            plan = self.validate()
        self.builder.assert_called_once_with(self.manifest['build'], 'cpu')
        self.assertEqual(plan['argv'], self.argv)
        self.assertEqual(plan['env']['LLAMA_CAFE3_CONTEXT_SHA256'], context.sha256(self.manifest_path))
        self.assertEqual(plan['env']['LD_LIBRARY_PATH'], str(self.exe.parent))
        self.assertNotIn('LD_PRELOAD', plan['env'])
        self.assertEqual(plan['env']['HIP_VISIBLE_DEVICES'], '-1')

    def test_context_hash_and_duplicate_json_refused(self):
        self.manifest_path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            context.validate_launch_context(str(self.manifest_path), '0'*64, self.argv)
        self.manifest_path.write_text('{"schema":1,"schema":2}')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            context.load(self.manifest_path)

    def test_declared_static_arm_disables_adaptation(self):
        self.manifest['arm'] = 'static-3'
        plan = self.validate()
        self.assertEqual(plan['env']['LLAMA_CAFE3_ADAPTIVE'], '0')
        self.assertEqual(plan['arm'], 'static-3')
        self.assertEqual(plan['corpus'], self.prepared['corpus'])
        for arm in ('static-7', 'foreign', 3):
            self.manifest['arm'] = arm
            with self.assertRaisesRegex(ValueError, 'undeclared protocol arm'):
                self.validate()

    def test_manifest_actual_command_and_models(self):
        with self.assertRaisesRegex(ValueError, 'argv mismatch'):
            self.validate(argv=self.argv + ['--model', '/other'])
        for suffix in (['--model', '/other'], ['-md', '/other'], ['-m', '/other'],
                       ['--model=other'], ['--model-draft-url', 'http://other'], ['-hf', 'other'],
                       ['-t', '4'], ['--threads', '4'], ['--gpu-layers', '99'], ['-ngld', '99']):
            with self.subTest(suffix=suffix):
                self.argv.extend(suffix)
                with self.assertRaises((ValueError, IndexError)):
                    self.validate()
                del self.argv[-len(suffix):]
        self.argv[2] = self.prepared['models']['draft']['path']
        with self.assertRaisesRegex(ValueError, 'model argv'):
            self.validate()

    def test_model_and_corpus_replacements(self):
        for role in ('target', 'draft', 'corpus'):
            with self.subTest(role=role):
                item = self.prepared['corpus'] if role == 'corpus' else self.prepared['models'][role]
                path = Path(item['path'])
                old = path.read_bytes()
                path.write_bytes(old + b'tamper')
                with self.assertRaisesRegex(ValueError, 'prepared input changed'):
                    self.validate()
                path.write_bytes(old)
                item['identity'] = context.file_identity(str(path))
                self.manifest['prepared'] = self.save('prepared', self.prepared)

    def test_protocol_references_and_required_rules(self):
        protocol = context.load(self.manifest['protocol']['path'])
        Path(self.manifest['protocol']['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            self.validate()
        for key, value in [('repetitions', 0), ('repetitions', True), ('stop_on_futility', ''),
                           ('decision_rule', ''), ('corpus', {}), ('arms', ['other'])]:
            with self.subTest(key=key, value=value):
                changed = dict(protocol, **{key: value})
                self.manifest['protocol'] = self.save('protocol', changed)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_row_deadline_stop_and_affinity(self):
        for key, value in [('FILLER_ID', 'foreign'), ('FILLER_DRYRUN', '1'),
                           ('FILLER_DEADLINE', str(self.now - 1)), ('FILLER_DEADLINE', str(self.now + 9999)),
                           ('FILLER_CPUS', '2'), ('FILLER_THREADS', '4'), ('FILLER_NEEDGPU', '1')]:
            with self.subTest(key=key):
                original = dict(self.env)
                self.env[key] = value
                with self.assertRaises(ValueError):
                    self.validate()
                self.env = original
        with self.assertRaisesRegex(ValueError, 'affinity'):
            self.validate(affinity={2})
        Path(self.env['FILLER_STOPFILE']).touch()
        with self.assertRaisesRegex(ValueError, 'STOP'):
            self.validate()

    def test_grant_fields_and_gpu_token(self):
        original = self.grant_text
        for text in [original.replace('cpus=2-3', 'cpus=4-5'), original + 'start=2026-11-19T12:00Z',
                     original.replace('regions=2-3', 'regions=q1'), original.replace('holds=c2,c3', 'holds=foreign'),
                     original.replace('end=2026-11-19T13:00Z', 'end=2026-11-19T12:00Z')]:
            with self.subTest(text=text):
                self.grant_text = text
                with self.assertRaises(ValueError):
                    self.validate()
        self.grant_text = original.replace(' cpus=2-3', '')
        self.validate()  # production omission of redundant cpus= is valid
        self.grant_text = original.replace('holds=c2,c3', 'holds=c2,c3,gpu-quiet')
        self.manifest['placement']['holds'] = 'c2,c3,gpu-quiet'
        with self.assertRaisesRegex(ValueError, 'GPU grant'):
            self.validate()
        self.manifest['backend'] = 'hip'
        self.env.update(FILLER_NEEDGPU='1', HIP_VISIBLE_DEVICES='0', ROCR_VISIBLE_DEVICES='0')
        self.manifest['device_env'] = dict(HIP_VISIBLE_DEVICES='0', ROCR_VISIBLE_DEVICES='0')
        self.argv[-3] = '99'
        self.argv[-1] = '99'
        self.validate()
        self.env['HIP_VISIBLE_DEVICES'] = '1'
        with self.assertRaisesRegex(ValueError, 'device placement'):
            self.validate()

    def test_journal_exclusive_precondition(self):
        Path(self.manifest['journal']).touch()
        with self.assertRaisesRegex(ValueError, 'journal'):
            self.validate()

    def test_ended_grant_and_unofficial_path(self):
        original = Path.exists
        with patch.object(Path, 'exists', lambda path: True if path == self.grant.with_suffix('.ended') else original(path)):
            with self.assertRaisesRegex(ValueError, 'grant already ended'):
                self.validate()
        with patch.object(context, 'bound_file', side_effect=lambda ref: Path('/tmp/copied.grant') if ref == self.manifest['grant'] else
                          (context.canonical(ref['path']) if context.sha256(ref['path']) == ref['sha256'] else None)):
            with self.assertRaisesRegex(ValueError, 'nonofficial grant path'):
                self.validate()


class BuildReceiptTest(unittest.TestCase):
    def test_real_producer_validation_and_mandatory_artifact_binding(self):
        source = Path(context.__file__).parent.parent / 'cafe3-build/driver.py'
        spec = importlib.util.spec_from_file_location('test_context_build', source)
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            run = root / 'runs/one'
            (run / 'build/bin').mkdir(parents=True)
            exe = run / 'build/bin/llama-server'
            exe.write_bytes(b'fixture')
            (run / 'build/CMakeCache.txt').write_text('GGML_HIP:BOOL=OFF\nGGML_BACKEND_DL:BOOL=OFF\n')
            linkage = []
            for name in ('libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so'):
                path = exe.parent / name
                path.write_bytes(name.encode())
                linkage.append(f'{name} => {path} (0x0)')
            (run / 'linkage.log').write_text('\n'.join(linkage))
            record = dict(schema='epyc.cafe3.build.v1', mode='build', run=str(run), base=driver.BASE,
                          inputs={'source': 'fixture'}, files={str(p): context.sha256(p) for p in run.rglob('*') if p.is_file()})
            path = root / 'receipt.json'
            def validate():
                path.write_text(json.dumps(record))
                return context.build_receipt(dict(path=str(path), sha256=context.sha256(path)), 'cpu')
            # Execute the actual producer validator with only source inventory and
            # strings mocked. Real artifact hashing, cache and linkage checks run.
            with patch.object(context.importlib.util, 'module_from_spec', return_value=driver), \
                 patch.object(context.importlib.machinery.SourceFileLoader, 'exec_module'), \
                 patch.object(driver, 'D', root), patch.object(driver, 'inputs', return_value=record['inputs']), \
                 patch.object(driver.subprocess, 'check_output', return_value=b'\n'.join(driver.MARKERS)):
                self.assertEqual(validate()[1], exe)
                for field, value in [('mode', 'smoke'), ('schema', 'foreign'), ('base', 'stale')]:
                    old = record[field]
                    record[field] = value
                    with self.assertRaises(ValueError):
                        validate()
                    record[field] = old
                del record['files'][str(exe)]
                with self.assertRaisesRegex(ValueError, 'unbound build'):
                    validate()
                record['files'][str(exe)] = context.sha256(exe)
                exe.write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError, 'artifact mismatch'):
                    validate()


if __name__ == '__main__':
    unittest.main()
