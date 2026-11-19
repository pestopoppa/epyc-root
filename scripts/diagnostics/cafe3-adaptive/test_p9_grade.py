"""Real sealed file graphs; fake models/process captures, never native inference."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import launch_context as context
import p9_grade as grader


class GradeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/df2')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        corpus = self.root / 'corpus.jsonl'
        corpus.write_text('{"id":"one","prompt":"Hello"}\n')
        self.corpus = dict(path=str(corpus), identity=context.file_identity(str(corpus)), sha256=context.sha256(corpus))
        prepared = dict(schema='epyc.cafe3.prepared.v1', corpus=self.corpus, models={})
        for role in ('target', 'draft'):
            path = self.root / (role + '.gguf')
            path.write_bytes(b'fake model; never executed')
            prepared['models'][role] = dict(path=str(path), identity=context.file_identity(str(path)), sha256=context.sha256(path))
        prepared_ref = self.save('prepared', prepared)
        self.arms = ['static-0', 'adaptive', 'static-1']
        self.protocol = dict(schema='epyc.cafe3.protocol.v1', corpus=self.corpus, arms=self.arms, repetitions=1,
                             p9_policy=copy.deepcopy(grader.POLICY), request_settings=dict(n_predict=8, seed=42,
                             timeout_s=10, arm_widths={'static-0': 0, 'adaptive': 1, 'static-1': 1}))
        self.protocol_ref = self.save('protocol', self.protocol)
        self.exe = self.root / 'llama-server'
        self.exe.touch()
        lib = self.root / 'libggml.so'
        lib.write_bytes(b'fake library')
        self.build = dict(base='ffc1bac82eeca6f9099e1ccd9ba49703c460a115', files={str(lib): context.sha256(lib)})
        self.manifests, self.requests, self.processes, self.entries = [], [], [], []
        self.grant = self.root / 'grant'
        self.grant.write_text('start=2026-11-19T12:00Z end=2026-11-19T13:00Z regions=2-3 holds=c2,c3')
        self.grant_ref = dict(path='/mnt/raid0/llm/tmp/compute-flags/grants/unit-cafe3-grade.grant', sha256=context.sha256(self.grant))
        self.t = 1795089660
        for i, arm in enumerate(self.arms):
            m = dict(schema='epyc.cafe3.launch-context.v1', arm=arm, run='run-' + arm,
                     backend='cpu', row='unit-cafe3-grade', build=self.save('build', self.build), prepared=prepared_ref,
                     protocol=self.protocol_ref, corpus=self.corpus, grant=self.grant_ref,
                     placement=dict(regions='2-3', holds='c2,c3', cpus='2-3', threads=2), device_env={},
                     argv=[str(self.exe), '--host', '127.0.0.1', '--port', '18099',
                           '-m', prepared['models']['target']['path'], '--model-draft', prepared['models']['draft']['path'],
                           '-t', '2', '-tb', '2', '-ngl', '0', '--gpu-layers-draft', '0'],
                     journal=str(self.root / (arm + '.rounds')))
            entry = dict(context={}, **{k: str(self.root / (arm + '.' + k)) for k in ('log', 'process', 'requests')})
            start = self.t + i * 10
            req = dict(schema='epyc.cafe3.request-capture.v1', status='UNASSESSED', protocol=self.protocol_ref,
                       arm=arm, repetition=0, prompt_id='one', context_sha256='',
                       payload=dict(prompt='Hello', n_predict=8, seed=42, temperature=0, stream=False,
                                    return_tokens=True, cache_prompt=False, **{'speculative.n_max': 1 if arm != 'static-0' else 0}),
                       elapsed_ns=1000000000 if arm == 'adaptive' else 1020000000,
                       unix_started_ns=(start + 1)*10**9, unix_ended_ns=(start+3)*10**9,
                       response=dict(stop=True, truncated=False, tokens=[1,2,3,4,5], timings={}))
            proc = dict(schema='epyc.cafe3.process-capture.v1', status='UNASSESSED', context_sha256='',
                        argv=m['argv'], cutoff='protocol-complete', request_rc=0, child_reaped=True,
                        requester_reaped=True, started=start, ended=start+4, log=entry['log'], requests_path=entry['requests'],
                        env=dict(LLAMA_CAFE3_RUN=m['run'], LLAMA_CAFE3_CONTEXT_SHA256='', LLAMA_CAFE3_JOURNAL=m['journal'],
                                 LLAMA_CAFE3_ADAPTIVE='1' if arm == 'adaptive' else '0', LD_LIBRARY_PATH=str(self.exe.parent)),
                        mapping_samples=[dict(at=start+2, maps='000-fff r-xp 0 0 0 ' + str(lib))])
            proc['env'].update(OMP_NUM_THREADS='2', GGML_IQK='1', HIP_VISIBLE_DEVICES='-1',
                               ROCR_VISIBLE_DEVICES='-1', CUDA_VISIBLE_DEVICES='-1')
            self.manifests.append(m)
            self.requests.append([req])
            self.processes.append(proc)
            self.entries.append(entry)
        self.rounds = []
        for ordinal, (width, probe) in enumerate([(0, True),(1, True),(0, False),(1, True)],1):
            self.rounds.append(dict(schema='epyc.cafe3.round.v1', run='run-adaptive', context_sha256='',
                                   ordinal=ordinal, unix_ns=(self.t+11)*10**9+ordinal*1000, request=123,
                                   request_epoch=1, sequence=0, round=ordinal, ticket=ordinal,
                                   implementation='mtp', selected_width=width, actual_width=width, accepted=0,
                                   position_zero_probability=0.2, elapsed_us=50, probe=probe))
        self.addCleanup(patch.stopall)
        self.builder = patch.object(context, 'build_receipt', return_value=(self.build, self.exe)).start()
        original_bound = context.bound_file
        patch.object(context, 'bound_file', side_effect=lambda ref: Path(self.grant_ref['path']) if ref == self.grant_ref else original_bound(ref)).start()
        original_read = Path.read_text
        patch.object(Path, 'read_text', lambda path, *a, **kw: original_read(self.grant)
                     if str(path) == self.grant_ref['path'] else original_read(path, *a, **kw)).start()
        self.seal()

    def save(self, name, data):
        path = self.root / (name + '.json')
        path.write_text(json.dumps(data))
        return dict(path=str(path), sha256=context.sha256(path))

    def lines(self, path, rows):
        Path(path).write_text(''.join(json.dumps(r)+'\n' for r in rows))
        return dict(path=str(path), sha256=context.sha256(path))

    def seal(self):
        self.protocol_ref = self.save('protocol', self.protocol)
        records = []
        for arm, m, entry, requests, proc in zip(self.arms, self.manifests, self.entries, self.requests, self.processes):
            m['protocol'] = self.protocol_ref
            entry['context'] = self.save(arm, m)
            digest = entry['context']['sha256']
            proc['context_sha256'] = proc['env']['LLAMA_CAFE3_CONTEXT_SHA256'] = digest
            for r in requests:
                r['context_sha256'], r['protocol'] = digest, self.protocol_ref
                r['unix_ended_ns'] = r['unix_started_ns'] + r['elapsed_ns']
            Path(entry['log']).write_text('fake model log\n')
            refs = dict(log=dict(path=entry['log'], sha256=context.sha256(entry['log'])),
                        process=self.save(arm+'.process', proc), requests=self.lines(entry['requests'], requests))
            # save() uses .json; the scheduled output path must be identical.
            Path(entry['process']).write_text(Path(refs['process']['path']).read_text())
            refs['process'] = dict(path=entry['process'], sha256=context.sha256(entry['process']))
            if arm == 'adaptive':
                for r in self.rounds:
                    r['context_sha256'] = digest
                refs['journal'] = self.lines(m['journal'], self.rounds)
            records.append(dict(event='arm-complete', status='UNASSESSED', arm=arm, context=entry['context'], captures=refs))
        schedule = dict(schema='epyc.cafe3.schedule.v1', protocol=self.protocol_ref, launches=self.entries)
        self.schedule_ref = self.save('schedule', schedule)
        self.records = [dict(schema='epyc.cafe3.schedule-capture.v1', status='UNASSESSED', event='start',
                             schedule=self.schedule_ref, protocol=self.protocol_ref, arms=self.arms,
                             ordering='sequential-whole-arm'), *records, dict(event='complete', status='UNASSESSED', arms=3)]
        self.capture_ref = self.lines(self.root / 'capture.jsonl', self.records)

    def assess(self):
        return grader.assess(self.schedule_ref, self.capture_ref)

    def test_complete_software_fixture_passes_and_best_static_used(self):
        result = self.assess()
        self.assertEqual(result['verdict'], 'pass')
        self.assertEqual(result['identity_percent'], 100)
        self.assertEqual(result['recovery_requests'], 1)
        self.assertAlmostEqual(result['gain_percent'], 2)
        self.builder.assert_called_once()

    def test_best_static_not_target_only(self):
        self.requests[0][0]['elapsed_ns'] = 2000000000
        self.requests[2][0]['elapsed_ns'] = 990000000
        self.seal()
        self.assertEqual(self.assess()['verdict'], 'fail')
        self.assertEqual(self.assess()['best_static'], 'static-1')

    def test_exact_one_percent_inclusive_boundary(self):
        self.requests[0][0]['elapsed_ns'] = self.requests[2][0]['elapsed_ns'] = 1010000000
        self.seal()
        self.assertEqual(self.assess()['verdict'], 'pass')
        self.requests[2][0]['elapsed_ns'] -= 1
        self.seal()
        self.assertEqual(self.assess()['verdict'], 'fail')

    def test_identity_checks_every_arm(self):
        for i in range(3):
            self.requests[i][0]['response']['tokens'][0] = 99
            self.seal()
            self.assertEqual(self.assess()['verdict'], 'fail')
            self.requests[i][0]['response']['tokens'][0] = 1

    def test_startup_exploration_not_recovery(self):
        self.rounds = self.rounds[:2]
        self.seal()
        self.assertEqual(self.assess()['verdict'], 'inconclusive')

    def test_missing_policy_or_static_coverage_refused(self):
        del self.protocol['p9_policy']
        self.seal()
        with self.assertRaisesRegex(ValueError, 'policy'):
            self.assess()
        self.protocol['p9_policy'] = copy.deepcopy(grader.POLICY)
        self.protocol['request_settings']['arm_widths']['adaptive'] = 2
        self.seal()
        with self.assertRaisesRegex(ValueError, 'static coverage'):
            self.assess()

    def test_incomplete_duplicate_reordered_or_failed_requests_refused(self):
        original = copy.deepcopy(self.requests[1])
        for change in ('missing', 'duplicate', 'wrong-id', 'failed', 'wrong-width', 'bool-token'):
            self.requests[1] = copy.deepcopy(original)
            r = self.requests[1][0]
            if change == 'missing': self.requests[1] = []
            if change == 'duplicate': self.requests[1].append(copy.deepcopy(r))
            if change == 'wrong-id': r['prompt_id'] = 'other'
            if change == 'failed': r['response']['stop'] = False
            if change == 'wrong-width': r['payload']['speculative.n_max'] = 0
            if change == 'bool-token': r['response']['tokens'] = [True]
            self.seal()
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.assess()

    def test_cutoff_unreaped_env_mapping_or_window_refused(self):
        original = copy.deepcopy(self.processes[1])
        for key, value in [('cutoff','server-exited'),('child_reaped',False),('requester_reaped',False),
                           ('request_rc',True),('mapping_samples',[]),('ended',self.t+10000)]:
            self.processes[1] = copy.deepcopy(original)
            self.processes[1][key] = value
            self.seal()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.assess()
        self.processes[1] = original
        self.processes[1]['env']['LD_PRELOAD'] = '/foreign.so'
        self.seal()
        with self.assertRaises(ValueError): self.assess()

    def test_round_corruption_and_unbound_request_windows_refused(self):
        original = copy.deepcopy(self.rounds)
        for key, value in [('ordinal',5),('ticket',0),('round',False),('actual_width',5),
                           ('unix_ns',1),('accepted',2),('elapsed_us',float('inf')),
                           ('request',999),('position_zero_probability',2)]:
            self.rounds = copy.deepcopy(original)
            self.rounds[1][key] = value
            self.seal()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.assess()

    def test_tampered_digest_partial_tail_and_schedule_failure_refused(self):
        Path(self.entries[1]['requests']).write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'): self.assess()
        self.seal()
        self.records.pop()
        self.capture_ref = self.lines(self.root / 'capture.jsonl', self.records)
        with self.assertRaisesRegex(ValueError, 'partial schedule'): self.assess()
        self.seal()
        path = Path(self.manifests[1]['journal'])
        path.write_bytes(path.read_bytes().rstrip(b'\n'))
        self.records[2]['captures']['journal']['sha256'] = context.sha256(path)
        self.capture_ref = self.lines(self.root / 'capture.jsonl', self.records)
        with self.assertRaisesRegex(ValueError, 'partial journal tail'): self.assess()

    def test_cross_arm_drift_and_reused_run_refused(self):
        self.manifests[2]['backend'] = 'hip'
        self.seal()
        with self.assertRaisesRegex(ValueError, 'cross-arm'): self.assess()
        self.manifests[2]['backend'] = 'cpu'
        self.manifests[2]['run'] = self.manifests[1]['run']
        self.seal()
        with self.assertRaisesRegex(ValueError, 'duplicate run'): self.assess()

    def test_recovery_after_bound_fails(self):
        zero = copy.deepcopy(self.rounds[2])
        self.rounds = self.rounds[:3]
        for index in range(4, 133):
            row = copy.deepcopy(zero)
            row.update(ordinal=index, round=index, ticket=index,
                       unix_ns=(self.t+11)*10**9+index*1000)
            self.rounds.append(row)
        final = copy.deepcopy(self.rounds[-1])
        final.update(ordinal=133, round=133, ticket=133, selected_width=1, actual_width=1,
                     probe=True, unix_ns=(self.t+11)*10**9+133000)
        self.rounds.append(final)
        self.seal()
        self.assertEqual(self.assess()['verdict'], 'fail')

    def test_multiple_repetitions_match_native_requests_without_cross_request_recovery(self):
        self.protocol['repetitions'] = 2
        first_rounds = copy.deepcopy(self.rounds)
        for index, requests in enumerate(self.requests):
            requests[0]['elapsed_ns'] = 90000000 if index == 1 else 100000000
            second = copy.deepcopy(requests[0])
            second.update(repetition=1, unix_started_ns=requests[0]['unix_started_ns']+500000000)
            requests.append(second)
        for r in first_rounds:
            new = copy.deepcopy(r)
            new.update(ordinal=r['ordinal']+4, request=124, unix_ns=r['unix_ns']+500000000)
            self.rounds.append(new)
        self.seal()
        self.assertEqual(self.assess()['recovery_requests'], 2)
        # Each request must recover on its own. End one at zero; the next
        # request's startup positive probe cannot close that zero episode.
        self.rounds = first_rounds[:3]
        for index, width in enumerate([0,1], 1):
            r = copy.deepcopy(first_rounds[index-1])
            r.update(ordinal=3+index, request=124, selected_width=width, actual_width=width,
                     unix_ns=(self.t+11)*10**9+500000000+index*1000)
            self.rounds.append(r)
        self.seal()
        self.assertEqual(self.assess()['verdict'], 'inconclusive')
        self.rounds[-1]['request'] = 123
        self.rounds[-2]['request'] = 123
        self.seal()
        with self.assertRaisesRegex(ValueError, 'reused native request'):
            self.assess()

    def test_request_clock_regression_and_missing_boundary_refused(self):
        self.seal()
        ref = self.records[2]['captures']['requests']
        request = copy.deepcopy(self.requests[1][0])
        request['unix_ended_ns'] += 100000000
        self.records[2]['captures']['requests'] = self.lines(ref['path'], [request])
        self.capture_ref = self.lines(self.root / 'capture.jsonl', self.records)
        with self.assertRaisesRegex(ValueError, 'clock disagreement'):
            self.assess()
        del request['unix_started_ns']
        self.records[2]['captures']['requests'] = self.lines(ref['path'], [request])
        self.capture_ref = self.lines(self.root / 'capture.jsonl', self.records)
        with self.assertRaises(KeyError): self.assess()

    def test_model_thread_and_environment_custody(self):
        self.manifests[2]['argv'] = list(self.manifests[2]['argv'])
        self.manifests[2]['argv'][self.manifests[2]['argv'].index('-m')+1] = '/other/model.gguf'
        self.seal()
        with self.assertRaises(ValueError): self.assess()
        self.manifests[2]['argv'] = list(self.manifests[0]['argv'])
        self.processes[1]['env']['OMP_NUM_THREADS'] = '99'
        self.seal()
        with self.assertRaisesRegex(ValueError, 'environment mismatch'): self.assess()

    def make_hip(self):
        self.grant.write_text(self.grant.read_text().replace('holds=c2,c3', 'holds=c2,c3,gpu-quiet'))
        self.grant_ref['sha256'] = context.sha256(self.grant)
        for m, proc in zip(self.manifests, self.processes):
            m['backend'] = 'hip'
            m['placement']['holds'] += ',gpu-quiet'
            m['device_env'] = dict(HIP_VISIBLE_DEVICES='0', ROCR_VISIBLE_DEVICES='0')
            for flag in ('-ngl', '--gpu-layers-draft'):
                m['argv'][m['argv'].index(flag)+1] = '99'
            proc['env'].update(m['device_env'])
            del proc['env']['CUDA_VISIBLE_DEVICES']
        self.seal()

    def test_hip_requires_residency_and_retains_known_identity_failure(self):
        self.make_hip()
        self.assertEqual(self.assess()['verdict'], 'inconclusive')
        self.requests[1][0]['response']['tokens'][0] = 9
        self.seal()
        self.assertEqual(self.assess()['verdict'], 'fail')

    def add_residency(self):
        for proc, requests in zip(self.processes, self.requests):
            proc['pid'] = 123
            start = requests[0]['unix_started_ns'] / 1e9
            proc['residency_samples'] = [dict(pid=123, kfd_registered=True,
                devices={'vram_7': 4096}, vram_bytes=4096,
                libraries=list(self.build['files']), at=start+offset) for offset in (.1, .4)]

    def test_hip_pass_requires_residency_for_every_arm_request(self):
        self.make_hip()
        self.add_residency()
        self.seal()
        result = self.assess()
        self.assertEqual(result['verdict'], 'pass')
        self.assertIs(result['hip_request_residency'], True)

    def test_missing_wrong_pid_zero_vram_foreign_libraries_and_stale_samples(self):
        self.make_hip()
        import copy
        for mutation in ('missing', 'pid', 'bool-pid', 'kfd', 'zero', 'negative', 'sum',
                         'foreign', 'missing-lib', 'late', 'early', 'duplicate', 'nan', 'malformed'):
            with self.subTest(mutation=mutation):
                self.add_residency()
                proc = self.processes[2]  # Even a static arm must prove residency.
                samples = proc['residency_samples']
                if mutation == 'missing': samples.pop()
                elif mutation == 'pid': samples[0]['pid'] = 124
                elif mutation == 'bool-pid': samples[0]['pid'] = True
                elif mutation == 'kfd': samples[0]['kfd_registered'] = False
                elif mutation == 'zero': samples[0].update(vram_bytes=0, devices={'vram_7': 0})
                elif mutation == 'negative': samples[0]['devices']['vram_8'] = -1
                elif mutation == 'sum': samples[0]['vram_bytes'] = 8192
                elif mutation == 'foreign': samples[0]['libraries'].append('/foreign/libggml.so')
                elif mutation == 'missing-lib': samples[0]['libraries'] = []
                elif mutation == 'late': samples[0]['at'] = proc['ended'] + 1
                elif mutation == 'early': samples[0]['at'] = proc['started'] + .1
                elif mutation == 'duplicate': samples[0] = copy.deepcopy(samples[1])
                elif mutation == 'nan': samples[0]['at'] = float('nan')
                elif mutation == 'malformed': samples[0] = None
                self.seal()
                if mutation == 'nan':
                    with self.assertRaisesRegex(ValueError, 'nonfinite JSON'):
                        self.assess()
                    continue
                result = self.assess()
                self.assertEqual(result['verdict'], 'inconclusive')
                self.assertIs(result['hip_request_residency'], False)

    def test_residency_from_another_request_does_not_cover_this_one(self):
        self.add_residency()
        proc = self.processes[0]
        request = dict(self.requests[0][0])
        request['unix_started_ns'] += 2*10**9
        request['unix_ended_ns'] += 2*10**9
        self.assertFalse(grader.request_resident(proc, request, set(self.build['files'])))

    def test_duplicate_json_keys_refused(self):
        path = self.root / 'capture.jsonl'
        path.write_text('{"event":"start","event":"complete"}\n')
        self.capture_ref['sha256'] = context.sha256(path)
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'): self.assess()

    def test_no_grant_time_model_hashing(self):
        original = context.sha256
        def guarded(path):
            self.assertFalse(str(path).endswith('.gguf'))
            return original(path)
        with patch.object(context, 'sha256', side_effect=guarded):
            self.assertEqual(self.assess()['verdict'], 'pass')


if __name__ == '__main__':
    unittest.main()
