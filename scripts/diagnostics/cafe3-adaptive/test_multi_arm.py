"""Schedule custody and stop controls, with model processes mocked throughout."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import launch_context as context
import multi_arm


class ScheduleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/df2')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        corpus = self.root / 'corpus.jsonl'
        corpus.write_text('{"id":"one","prompt":"Hello"}\n')
        self.corpus = dict(path=str(corpus), sha256=context.sha256(corpus),
                           identity=context.file_identity(str(corpus)))
        self.protocol = dict(schema='epyc.cafe3.protocol.v1', corpus=self.corpus,
                             arms=['static-0', 'adaptive', 'static-1'], repetitions=2,
                             request_settings=dict(n_predict=8, seed=42, timeout_s=10,
                                                   arm_widths={'adaptive': 1, 'static-0': 0, 'static-1': 1}))
        protocol = self.save('protocol.json', self.protocol)
        self.manifests = []
        entries = []
        for arm in self.protocol['arms']:
            manifest = dict(arm=arm, run='run-' + arm, protocol=protocol, corpus=self.corpus,
                            argv=['/bound/server', '--host', '127.0.0.1', '--port', '18099'],
                            journal=str(self.root / (arm + '-rounds.jsonl')),
                            build=dict(path='/bound/build'), prepared=dict(path='/bound/prepared'),
                            grant=dict(path='/bound/grant'), backend='cpu')
            self.manifests.append(manifest)
            entries.append(dict(context=self.save(arm + '.json', manifest),
                                **{key: str(self.root / (arm + '-' + key))
                                   for key in ('log', 'process', 'requests')}))
        self.schedule = dict(schema='epyc.cafe3.schedule.v1', protocol=protocol, launches=entries)
        self.path = self.root / 'schedule.json'
        self.result = str(self.root / 'schedule-capture.jsonl')
        self.addCleanup(patch.stopall)
        self.validate = patch.object(context, 'validate_launch_context', side_effect=self.validated).start()
        self.runner = patch.object(multi_arm.native_runner, 'run', side_effect=self.run_arm).start()
        self.seal()

    def save(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data))
        return dict(path=str(path), sha256=context.sha256(path))

    def seal(self):
        self.path.write_text(json.dumps(self.schedule))
        self.digest = context.sha256(self.path)

    def change_manifest(self, index, **changes):
        self.manifests[index].update(changes)
        entry = self.schedule['launches'][index]
        entry['context'] = self.save(Path(entry['context']['path']).name, self.manifests[index])
        self.seal()

    def validated(self, path, digest, argv):
        manifest = context.bound_json(dict(path=path, sha256=digest))
        return dict(arm=manifest['arm'], protocol=manifest['protocol'], corpus=self.corpus,
                    argv=argv, models={'target': dict(path='/bound/target.gguf'),
                                       'draft': dict(path='/bound/draft.gguf')})

    def run_arm(self, path, digest, argv, log, process, requests):
        manifest = context.bound_json(dict(path=path, sha256=digest))
        record = dict(cutoff='protocol-complete', request_rc=0, child_reaped=True,
                      requester_reaped=True)
        Path(log).write_text('model-free log\n')
        Path(process).write_text(json.dumps(record))
        Path(requests).write_text('{"synthetic":true}\n')
        if manifest['arm'] == 'adaptive':
            Path(manifest['journal']).write_text('{"synthetic":true}\n')
        return record

    def execute(self):
        multi_arm.execute(self.path, self.digest, self.result)

    def records(self):
        return [json.loads(line) for line in Path(self.result).read_text().splitlines()]

    def refused(self, message):
        with self.assertRaisesRegex(ValueError, message):
            self.execute()
        self.runner.assert_not_called()
        self.assertFalse(Path(self.result).exists())

    def test_all_arms_preflight_then_ordered_execution_and_bound_captures(self):
        def run(*args):
            self.assertEqual(self.validate.call_count, 3)
            return self.run_arm(*args)
        self.runner.side_effect = run
        self.execute()
        rows = self.records()
        self.assertEqual([r['event'] for r in rows], ['start'] + ['arm-complete'] * 3 + ['complete'])
        self.assertEqual([r['arm'] for r in rows[1:-1]], self.protocol['arms'])
        self.assertTrue(all(r['status'] == 'UNASSESSED' for r in rows))
        self.assertEqual(rows[0]['ordering'], 'sequential-whole-arm')
        for row in rows[1:-1]:
            for ref in row['captures'].values():
                context.bound_file(ref)
            self.assertEqual('journal' in row['captures'], row['arm'] == 'adaptive')

    def test_tampered_schedule_and_last_context_refused_before_spawn(self):
        self.path.write_text('{}')
        self.refused('digest mismatch')
        self.seal()
        Path(self.schedule['launches'][-1]['context']['path']).write_text('{}')
        self.refused('digest mismatch')

    def test_path_result_from_row_runtime_completes_all_arms(self):
        multi_arm.execute(self.path, self.digest, Path(self.result))
        self.assertEqual(self.runner.call_count, 3)
        self.assertEqual(self.records()[-1]['event'], 'complete')

    def test_path_result_keeps_exclusive_and_canonical_output_guards(self):
        result = Path(self.result)
        for value in (self.corpus['path'], self.schedule['launches'][0]['log']):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'colliding output|outside inputs'):
                    multi_arm.execute(self.path, self.digest, Path(value))
                self.runner.assert_not_called()
        result.symlink_to(self.root / 'missing-target')
        with self.assertRaisesRegex(ValueError, 'new canonical path'):
            multi_arm.execute(self.path, self.digest, result)
        self.runner.assert_not_called()
        result.unlink()
        result.touch()
        with self.assertRaisesRegex(ValueError, 'new canonical path'):
            multi_arm.execute(self.path, self.digest, result)
        self.runner.assert_not_called()

    def test_missing_or_duplicate_static_arm_refused(self):
        for arms in (['adaptive', 'static-0'], ['adaptive', 'static-0', 'static-0']):
            self.protocol['arms'] = arms
            self.schedule['protocol'] = self.save('protocol.json', self.protocol)
            self.seal()
            self.refused('all static widths')

    def test_arm_order_and_run_reuse_refused(self):
        self.change_manifest(2, arm='static-0')
        self.refused('arm/order/protocol')
        self.change_manifest(2, arm='static-1', run=self.manifests[0]['run'])
        self.refused('duplicate run')

    def test_cross_arm_build_model_backend_argv_or_grant_drift_refused(self):
        original = copy.deepcopy(self.manifests[2])
        for key, value in [('backend', 'hip'), ('build', {'path': '/other/build'}),
                           ('prepared', {'path': '/other/models'}), ('argv', ['/different/server']),
                           ('grant', {'path': '/other/grant'})]:
            self.manifests[2] = copy.deepcopy(original)
            self.change_manifest(2, **{key: value})
            self.refused('cross-arm launch context')

    def test_late_context_or_request_validation_failure_prevents_every_spawn(self):
        self.validate.side_effect = [self.validated(**dict(path=e['context']['path'], digest=e['context']['sha256'],
                                                          argv=m['argv']))
                                     for e, m in zip(self.schedule['launches'][:2], self.manifests[:2])] + [ValueError('STOP')]
        self.refused('STOP')
        self.validate.side_effect = self.validated
        self.change_manifest(2, argv=self.manifests[0]['argv'])
        self.protocol['request_settings']['seed'] = True
        self.schedule['protocol'] = self.save('protocol.json', self.protocol)
        for index in range(3):
            self.change_manifest(index, protocol=self.schedule['protocol'])
        self.refused('invalid seed')

    def test_output_collision_existing_file_symlink_and_input_overwrite_refused(self):
        entry = self.schedule['launches'][2]
        original = entry['log']
        for value in (self.result, self.corpus['path'], str(self.root / 'missing' / 'log')):
            entry['log'] = value
            self.seal()
            with self.assertRaises((ValueError, FileNotFoundError)):
                self.execute()
            self.runner.assert_not_called()
        entry['log'] = original
        self.seal()
        Path(original).symlink_to(self.root / 'nonexistent')
        self.refused('new canonical path')
        Path(original).unlink()
        Path(original).touch()
        self.refused('new canonical path')

    def test_incomplete_child_or_requester_stops_without_later_arms(self):
        self.runner.side_effect = None
        self.runner.return_value = dict(cutoff='server-exited', request_rc=0,
                                        child_reaped=True, requester_reaped=True)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.execute()
        self.assertEqual(self.runner.call_count, 1)
        self.assertEqual(self.records()[-1]['event'], 'failed')
        self.assertNotIn('complete', [r['event'] for r in self.records()])

    def test_unreaped_children_refused_even_on_protocol_complete(self):
        self.runner.side_effect = None
        self.runner.return_value = dict(cutoff='protocol-complete', request_rc=0,
                                        child_reaped=False, requester_reaped=True)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.execute()
        self.assertEqual(self.runner.call_count, 1)

    def test_partial_failure_retains_first_arm_and_never_runs_last(self):
        def run(*args):
            if self.runner.call_count == 2:
                raise ValueError('deadline')
            return self.run_arm(*args)
        self.runner.side_effect = run
        with self.assertRaisesRegex(ValueError, 'deadline'):
            self.execute()
        self.assertEqual(self.runner.call_count, 2)
        self.assertEqual([r['event'] for r in self.records()], ['start', 'arm-complete', 'failed'])
        self.assertTrue(Path(self.schedule['launches'][0]['requests']).exists())

    def test_missing_adaptive_journal_refuses_completion_and_rerun(self):
        def run(*args):
            record = self.run_arm(*args)
            if self.runner.call_count == 2:
                Path(self.manifests[1]['journal']).unlink()
            return record
        self.runner.side_effect = run
        with self.assertRaises(FileNotFoundError):
            self.execute()
        self.assertEqual(self.runner.call_count, 2)
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(self.runner.call_count, 2)


if __name__ == '__main__':
    unittest.main()
