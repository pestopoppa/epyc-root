"""Prospective fixture only: no hardware execution or historical warrant."""
import hashlib
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from autokernel import census_capture as capture
from adapters import autokernel_census as adapter
from claim_tuple import ProjectionError, grade


class CensusCaptureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = {}
        for name in ('binary', 'model', 'recipe', 'binding', 'producer', 'driver',
                     'capture_module', 'residency', 'workload_contract', 'libggml-hip.so'):
            p = self.root / name
            p.write_text(name)
            self.paths[name] = str(p)
        grant_file = self.root / 'grant'
        grant_file.write_text('regions=mi210_0,184-191 start=1970-01-01T00:00Z end=1970-01-01T00:02Z\n')
        self.paths['grant'] = str(grant_file)
        workload = {'id': 'fixture', 'model': self.paths['model'], 'expected_ops': ['ADD']}
        Path(self.paths['recipe']).write_text(json.dumps({'kernel_commit': 'a' * 40, 'workloads': [workload]}))
        Path(self.paths['binding']).write_text(json.dumps({'recipes_sha256': capture.file_sha256(Path(self.paths['recipe']))}))
        for name, content in {
            'build_receipt_binding': str(self.root),
            'build_complete': f"BUILD_COMPLETE source={'a' * 40} kind=hip end=1970-01-01T00:00:00Z no-model-runs=true\n",
            'build_log': f"source={'a' * 40} cpus=0-1 jobs=2 start=fixture\n",
            'build_job': 'fixture build script',
            'build_sources': f"{capture.file_sha256(Path(self.paths['producer']))}  {self.paths['producer']}\n",
            'elf_manifest': ''.join(f"{capture.file_sha256(Path(self.paths[n]))}  {self.paths[n]}\n"
                                    for n in ('binary', 'libggml-hip.so')),
        }.items():
            p = self.root / name
            p.write_text(content)
            self.paths[name] = str(p)
        self.shape = {'phase': 'prefill', 'n_tokens': 32, 'n_seq': 1}
        self.argv = [self.paths['binary'], '-m', self.paths['model'], '-p', '32', '-n', '0']
        self.log = self.root / 'raw.log'
        self.log.write_text('Device 0: MI210\n' + ''.join(f'node # {i} (ADD): output [GPU0]\n' for i in range(1001)))
        self.journal = self.root / 'attempt.jsonl'
        self.sidecar = self.root / 'record.belief.jsonl'
        self.record = self.root / 'record.json'
        inputs = {k: self.paths[k] for k in ('binary', 'model', 'recipe', 'binding', 'producer', 'driver', 'grant',
                    'capture_module', 'residency', 'workload_contract',
                    'build_receipt_binding', 'build_complete', 'build_log', 'elf_manifest', 'build_job', 'build_sources')}
        capture.begin(self.journal, attempt_id='a1', started_ns=1_000_000_000, argv=self.argv,
                      env={'PATH': '/fixture', 'FILLER_CPUS': '184-191', 'GGML_SCHED_DEBUG':'2'}, shape=self.shape,
                      grant=grant_file.read_text(), deadline='30',
                      kernel_commit='a' * 40, inputs=inputs)
        dso = self.paths['libggml-hip.so']
        def sample(t):
            return {'utc_ns': t, 'pid': 123, 'own_vram_bytes': 2 << 30, 'global_vram_bytes': 2 << 30,
                    'kfd_processes': 1, 'task_affinity': {'1': '184-191'}, 'loaded_ggml': [dso]}
        capture.finish(self.journal, attempt_id='a1', ended_ns=4_000_000_000, rc=0, error='',
                       samples=[sample(2_000_000_000), sample(3_000_000_000)], log=str(self.log),
                       loaded_dsos={'hip': dso}, spawned_ns=1_500_000_000,
                       loaded_before={dso: capture.file_identity(Path(dso))})
        identity = {'workload_id': 'fixture', 'kernel': {'commit': 'a' * 40,
                    'binary_sha256': capture.file_sha256(Path(self.paths['binary']))},
                    'model': {'path': self.paths['model'],
                    'sha256': capture.file_sha256(Path(self.paths['model']))},
                    'recipe': workload, 'env': {'FILLER_CPUS': '184-191'}}
        row = {'shape': self.shape, 'argv': self.argv, 'rc': 0, 'state': 'OBSERVED',
               'nodes_total': 1001, 'op_backend': {'ADD': {'GPU0': 1001}}, 'device_seen': True}
        record = {'schema': 'epyc.autokernel.workload_census.v1', 'identity': identity,
                  'validity': {'freshness_key': hashlib.sha256(capture.canonical(identity)).hexdigest(),
                               'state': 'OBSERVED', 'observed': True},
                  'graph': {'shape_envelope': [self.shape], 'per_shape': [row]}}
        self.record.write_text(json.dumps(record))
        capture.seal_record(self.sidecar, record=self.record, journals=[self.journal])

    def test_projection_and_grade(self):
        rows = adapter.native_rows(self.sidecar)
        self.assertEqual(len(rows), 1)
        claim = adapter.project(rows[0])
        self.assertEqual(claim.metric, 'census_shape_observed')
        self.assertEqual(claim.value, 1)
        self.assertEqual(claim.extra['nodes_total'], 1001)
        self.assertEqual(claim.protocol_id, '')
        self.assertIn('Judged', str(grade(claim)))
        self.assertTrue(adapter.frames_for_record(self.sidecar, as_of='2026-10-27T00:00:00Z'))

    def test_larger_graph_does_not_rank_higher(self):
        first = adapter.project(adapter.native_rows(self.sidecar)[0])
        self.log.write_text(self.log.read_text() + 'node # 1001 (ADD): output [GPU0]\n')
        record = json.loads(self.record.read_text())
        record['graph']['per_shape'][0]['nodes_total'] = 1002
        record['graph']['per_shape'][0]['op_backend']['ADD']['GPU0'] = 1002
        self.record.write_text(json.dumps(record))
        events = [json.loads(line) for line in self.journal.read_text().splitlines()]
        start, end = (dict(event) for event in events)
        for event in (start, end):
            for key in ('content_sha256', 'schema', 'previous_sha256'):
                event.pop(key)
        end['log']['sha256'] = capture.file_sha256(self.log)
        self.journal.unlink()
        capture.append_event(self.journal, start)
        capture.append_event(self.journal, end)
        self.sidecar.unlink()
        capture.seal_record(self.sidecar, record=self.record, journals=[self.journal])
        second = adapter.project(adapter.native_rows(self.sidecar)[0])
        self.assertEqual((first.metric, first.value), (second.metric, second.value))
        self.assertEqual(second.extra['nodes_total'], 1002)

    def test_batch_frames_hash_the_model_once(self):
        original = adapter._read
        seen = []
        def counted(ref, **kw):
            if ref.get('path') == self.paths['model']:
                seen.append(ref['path'])
            return original(ref, **kw)
        with mock.patch.object(adapter, '_read', side_effect=counted):
            adapter.frames_for_record(self.sidecar, as_of='2026-10-27T00:00:00Z')
        self.assertEqual(len(seen), 1)

    def test_private_fixture_planning_context_canary(self):
        import loop_beliefs
        from ledger import Ledger
        from autokernel.loop import actors
        class Fresh:
            def status(self, ledger, index):
                return {'fresh': True}
        ledger = self.root / 'ledger.jsonl'
        for frame in adapter.frames_for_record(self.sidecar, as_of='2026-10-27T00:00:00Z'):
            Ledger(ledger).append(frame)
        history_file = self.root / 'history.json'
        history_file.write_text(json.dumps([{'mechanism_id': 'fixture-do-not-repeat',
                                             'status': 'measured_null'}]))
        answer = loop_beliefs.prepare('autokernel.fixture',
            {'model_file': self.paths['model'], 'backend': 'gpu', 'device': 'mi210'},
            ledger=ledger, index_path=self.root / 'index', as_of='2026-10-28T00:00:00Z',
            sync_module=Fresh(), known_good=self.root / 'known-good.json',
            alarm_state=self.root / 'alarm.json', alarm_config=self.root / 'alarm.yaml',
            read_log=self.root / 'reads.jsonl')
        self.assertEqual(answer['status'], 'ready')
        context = actors.render_context({'prior_experiments': json.loads(history_file.read_text())},
                                       belief_section=answer['evidence']['section'])
        self.assertIn('1001', context)
        self.assertIn('fixture-do-not-repeat', context)

    def test_changed_log_or_source_refused(self):
        self.log.write_text('changed')
        with self.assertRaises(ProjectionError):
            adapter.native_rows(self.sidecar)
        self.log.unlink()
        with self.assertRaises(ProjectionError):
            adapter.native_rows(self.sidecar)

    def test_cleanup_or_mutation_of_original_small_evidence_keeps_projection(self):
        start = json.loads(self.journal.read_text().splitlines()[0])
        for key, ref in start['inputs'].items():
            if key not in ('binary', 'model'):
                Path(ref['origin_path']).unlink()
        self.assertEqual(adapter.project(adapter.native_rows(self.sidecar)[0]).value, 1)

    def test_mutated_original_small_evidence_keeps_projection(self):
        start = json.loads(self.journal.read_text().splitlines()[0])
        for key, ref in start['inputs'].items():
            if key not in ('binary', 'model'):
                Path(ref['origin_path']).write_text('post-run change')
        self.assertEqual(adapter.project(adapter.native_rows(self.sidecar)[0]).value, 1)

    def test_altered_retained_evidence_refuses(self):
        start = json.loads(self.journal.read_text().splitlines()[0])
        Path(start['inputs']['grant']['path']).write_text('altered retained grant')
        with self.assertRaises(ProjectionError):
            adapter.native_rows(self.sidecar)

    def test_altered_retained_manifest_source_refuses(self):
        start = json.loads(self.journal.read_text().splitlines()[0])
        source = next(iter(start['manifest_sources']['build_sources'].values()))
        Path(source['path']).write_text('altered retained source')
        with self.assertRaises(ProjectionError):
            adapter.native_rows(self.sidecar)

    def test_missing_grant_at_capture_refuses(self):
        start = json.loads(self.journal.read_text().splitlines()[0])
        inputs = {key: ref.get('origin_path', ref['path']) for key, ref in start['inputs'].items()}
        Path(inputs['grant']).unlink()
        failed = self.root / 'missing-grant.jsonl'
        with self.assertRaises(OSError):
            capture.begin(failed, attempt_id='missing', started_ns=start['started_ns'],
                          argv=start['argv'], env=start['env'], shape=start['shape'],
                          grant=start['grant'], deadline=start['deadline'],
                          kernel_commit=start['kernel_commit'], inputs=inputs)
        self.assertEqual(json.loads(failed.read_text())['kind'], 'refusal')

    def test_stale_manifest_source_at_capture_refuses(self):
        start = json.loads(self.journal.read_text().splitlines()[0])
        inputs = {key: ref.get('origin_path', ref['path']) for key, ref in start['inputs'].items()}
        Path(inputs['producer']).write_text('changed before capture')
        failed = self.root / 'stale-source.jsonl'
        with self.assertRaises(ValueError):
            capture.begin(failed, attempt_id='stale', started_ns=start['started_ns'],
                          argv=start['argv'], env=start['env'], shape=start['shape'],
                          grant=start['grant'], deadline=start['deadline'],
                          kernel_commit=start['kernel_commit'], inputs=inputs)
        self.assertEqual(json.loads(failed.read_text())['kind'], 'refusal')

    def test_changed_record_and_journal_refused(self):
        self.record.write_text('{}')
        with self.assertRaises(ProjectionError):
            adapter.native_rows(self.sidecar)

    def test_failure_and_missing_samples_refused_even_if_resealed(self):
        events = [json.loads(line) for line in self.journal.read_text().splitlines()]
        for update in ({'rc': 1}, {'samples': []}, {'error': 'timeout'}):
            start = dict(events[0])
            end = dict(events[1])
            for key in ('content_sha256', 'schema', 'previous_sha256'):
                start.pop(key)
                end.pop(key)
            end.update(update)
            self.journal.unlink()
            capture.append_event(self.journal, start)
            capture.append_event(self.journal, end)
            self.sidecar.unlink()
            capture.seal_record(self.sidecar, record=self.record, journals=[self.journal])
            with self.assertRaises(ProjectionError):
                adapter.native_rows(self.sidecar)

    def test_record_shape_mismatch_refused_even_if_resealed(self):
        record = json.loads(self.record.read_text())
        record['graph']['per_shape'][0]['nodes_total'] = 1002
        self.record.write_text(json.dumps(record))
        self.sidecar.unlink()
        capture.seal_record(self.sidecar, record=self.record, journals=[self.journal])
        with self.assertRaises(ProjectionError):
            adapter.native_rows(self.sidecar)
        self.journal.write_text('{}\n')
        with self.assertRaises(ProjectionError):
            adapter.native_rows(self.sidecar)
