"""Unit checks for control-only LOOP-49 qualification (no grants or inference)."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
import time
from datetime import datetime, timezone
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/coordination'))
import qualify_launcher as q
import filler_engine14 as engine


class NativeDiagnosticProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixture = self.root / 'fixture'
        self.fixture.write_text('pinned fixture\n')
        self.model = self.root / 'model'
        self.model.write_text('model identity fixture\n')
        self.qroot = self.root / 'qual' / ('a' * 32)
        self.result_dir = self.qroot / 'results'
        self.result_dir.mkdir(parents=True)
        self.grants = self.qroot / 'grants'
        self.grants.mkdir()
        (self.grants / 'diag.grant').write_text('synthetic grant evidence\n')
        self.partial_ended = self.grants / 'diag.deadline.ended'
        self.partial_ended.write_text('rc=75 time=2026-11-01T00:00:00Z reason=fixture-exit\npartial=true\nnative_complete=false\nphase=qualification\ngranted=true\n')
        self.terminal_ended = self.grants / 'diag.ended'
        self.terminal_ended.write_text('rc=0 time=2026-11-01T00:00:00Z reason=qualification-complete\npartial=false\nnative_complete=false\nphase=qualification\ngranted=true\n')
        self.result = self.result_dir / 'result.json'
        self.result.write_text('{"diagnostic":true}\n')
        partial_dir = self.qroot / 'partial-results'
        partial_dir.mkdir(parents=True)
        partial = partial_dir / 'partial.json'
        partial.write_text('{"partial":true}\n')
        self.partial = partial
        self.policy = self.root / 'policy.json'
        self.policy.write_text(json.dumps({'interim_until_utc': '2000-01-01T00:00Z',
                                           'interim_floor_gib': 1, 'normal_floor_gib': 1}))
        predicate = 'test -f result.json'
        self.manifest = {
            'id': 'diag', 'qualification_profile': 'native-diagnostic',
            'qual_complete_cmd_sha256': hashlib.sha256(predicate.encode()).hexdigest(),
            'qual_fixture_items': 2, 'qual_forced_deadline_s': 1,
            'scratch_root': str(self.root), 'requires_tools': [],
            'qual_fixture': str(self.fixture),
            'qualification_model': {'id': 'fixture-model', 'path': str(self.model), 'sha256': q.sha(self.model)},
            'n_ctx_required': 999999, 'tokens_per_item': 999999, 'items': 999999,
        }
        self.evidence = {
            'nonce': 'a' * 32, 'qualification_profile': 'native-diagnostic',
            'qualification_root': str(self.qroot), 'children_drained': True,
            'admission': {'rc': 0, 'affinity_ok': True},
            'completion': {'complete_cmd_present': True, 'is_complete_rc': 0,
                           'predicate_sha256': self.manifest['qual_complete_cmd_sha256']},
            'rc75': {'exit_code': 75, 'partial_flag': True,
                     'ended_path': str(self.partial_ended), 'ended_line_sha256': q.sha(self.partial_ended),
                     'partial_path': str(partial), 'partial_sha256': q.sha(partial)},
            'disk': {'job_floor_gib': 1, 'policy_floor_gib': 1,
                     'diagnostic_control': {'kind': 'epyc.qual.diagnostic-disk-control.v1',
                                            'policy_sha256': q.sha(self.policy), 'floor_gib': 1}},
            'fixture': {'path': str(self.fixture.resolve()), 'sha256': q.sha(self.fixture), 'items': 2},
            'result_writer': {'ok': True, 'result_path': str(self.result), 'sha256': q.sha(self.result)},
            'launcher_terminal': {'path': str(self.terminal_ended), 'sha256': q.sha(self.terminal_ended)},
            'exec_namespace': {'tools': {}},
        }

    def test_native_diagnostic_needs_no_fabricated_inference_metrics(self):
        q.evidence_check(self.manifest, self.evidence, self.policy)

    def test_native_diagnostic_manifest_requires_pinned_static_fields(self):
        for field, reason in (('qual_complete_cmd_sha256', 'missing-pinned-completion-predicate'),
                              ('qual_fixture_items', 'missing-or-invalid-qual-fixture-items'),
                              ('qual_forced_deadline_s', 'invalid-native-diagnostic-deadline')):
            manifest = dict(self.manifest)
            manifest.pop(field)
            with self.subTest(field=field), self.assertRaisesRegex(q.Refused, reason):
                q.native_diagnostic_manifest_check(manifest)

    def test_static_native_diagnostic_accepts_28_work_units_without_inference_fields(self):
        manifest = dict(self.manifest, launcher=str(self.root / 'launcher'),
                        engine=str(q.HERE / 'filler_run14.sh'), job=str(self.root / 'job'),
                        source_manifest=str(self.root / 'source'), row=str(self.root / 'row'),
                        requires_tools=[], ports=[], shared_state=[], exclusive_class=None,
                        regions='any-cpu-quarter', claimed_cpus='any-cpu-quarter',
                        window_s=600, min_window_s=60, items=28, est_output_GiB=0,
                        gib=8, process_limit_GiB=8, scratch_root=str(self.root))
        manifest.pop('tokens_per_item')
        manifest.pop('n_ctx_required')
        for name in ('launcher', 'job', 'source_manifest', 'row'):
            Path(manifest[name]).write_text('fixture file\n')
        allow = self.root / 'allow.json'
        q.create(allow, {'kind': 'epyc.engine-allowlist.v1',
                         'engines': [q.sha(manifest['engine'])]})
        with patch.object(q, 'check_row_binding', return_value={}), \
             patch.object(q, 'checked_manifest', return_value='fixture'), \
             patch.dict('os.environ', {'WS58_ROOT': str(ROOT)}):
            self.assertEqual(q.static_check(manifest, allow), manifest)
        inference_manifest = dict(manifest, qualification_profile='inference',
                                  tokens_per_item=1, n_ctx_required=1)
        binding = q.hashes(inference_manifest, self.policy)
        self.assertEqual(binding['qualification_model_path'], str(self.model.resolve()))
        self.assertEqual(binding['qualification_model_sha256'], q.sha(self.model))

    def test_inference_static_check_rejects_model_byte_drift(self):
        manifest = dict(self.manifest, qualification_profile='inference',
                        tokens_per_item=1, n_ctx_required=1)
        manifest['qualification_model'] = dict(self.manifest['qualification_model'], sha256='0' * 64)
        with self.assertRaisesRegex(q.Refused, 'qualification-model-hash-mismatch'):
            q.static_check(manifest, self.root / 'unused-allowlist')

    def test_ended_markers_bind_partial_and_final_launcher_states(self):
        q.evidence_check(self.manifest, self.evidence, self.policy)
        self.terminal_ended.write_text(self.terminal_ended.read_text().replace('rc=0 ', 'rc=1 '))
        self.evidence['launcher_terminal']['sha256'] = q.sha(self.terminal_ended)
        with self.assertRaisesRegex(q.Refused, 'launcher-terminal-marker-invalid'):
            q.evidence_check(self.manifest, self.evidence, self.policy)

    def test_inference_profile_rejects_rc75_marker_with_wrong_phase(self):
        self.partial_ended.write_text(self.partial_ended.read_text().replace(
            'phase=qualification', 'phase=production'))
        self.evidence['rc75']['ended_line_sha256'] = q.sha(self.partial_ended)
        manifest = dict(self.manifest, qualification_profile='inference',
                        tokens_per_item=1, n_ctx_required=1)
        with self.assertRaisesRegex(q.Refused, 'rc75-ended-marker-invalid'):
            q.evidence_check(manifest, self.evidence, self.policy)

    def test_launcher_dead_malformed_proc_record_refuses(self):
        with patch.object(engine.Path, 'read_text', return_value='truncated'):
            with self.assertRaisesRegex(q.Refused, 'proc-birth-malformed'):
                engine.launcher_dead(123, '456')
        with patch.object(engine.Path, 'read_text', side_effect=FileNotFoundError):
            self.assertTrue(engine.launcher_dead(123, '456'))

    def test_schema_keeps_tokens_and_context_inference_only(self):
        schema = json.loads((ROOT / 'scripts/coordination/ready_manifest.schema.json').read_text())
        self.assertNotIn('tokens_per_item', schema['required'])
        self.assertNotIn('n_ctx_required', schema['required'])
        branches = schema['allOf'][0]
        self.assertIn('tokens_per_item', branches['else']['required'])
        self.assertIn('n_ctx_required', branches['else']['required'])
        self.assertIn('qual_fixture_items', branches['then']['required'])

    def test_end_to_end_diagnostic_fixtures_emit_control_only_pass_evidence(self):
        qroot = self.root / 'e2e' / 'qual' / ('b' * 32)
        results = qroot / 'results'
        fixture = self.root / 'fixture.py'
        fixture.write_text("import os, pathlib, sys\nphase=os.environ['FILLER_QUAL_PHASE']\nout=pathlib.Path(os.environ['FILLER_RESULTS_DIR'])\nif phase == 'complete':\n (out/'result.json').write_text('{\\\"ok\\\":true}\\n')\n raise SystemExit(0)\n(out/'partial.json').write_text('{\\\"partial\\\":true}\\n')\nraise SystemExit(75)\n")
        manifest = dict(self.manifest, qual_fixture=str(fixture),
                        claimed_cpus='any-cpu-quarter', regions='any-cpu-quarter',
                        ports=[], exclusive_class=None, shared_state=[], est_output_GiB=0)
        complete_cmd = 'test -f "$FILLER_RESULTS_DIR/result.json"'
        manifest['qual_complete_cmd_sha256'] = hashlib.sha256(complete_cmd.encode()).hexdigest()
        env = {'FILLER_GRANTS_DIR': str(self.root / 'grants'), 'WS58_REGIONS': '0-1',
               'FILLERS_MD': str(self.root / 'row'), 'WS58_QUAL_RESULTS': str(results),
               'WS58_QUAL_ROOT': str(qroot), 'WS58_QUAL_MANIFEST': str(self.root / 'manifest.json'),
               'WS58_QUAL_NONCE': 'b' * 32}
        Path(env['FILLER_GRANTS_DIR']).mkdir()
        qroot.mkdir(parents=True)
        (qroot / 'grants').mkdir()
        (qroot / 'grants' / 'diag.grant').write_text('synthetic grant evidence\n')
        (Path(env['FILLER_GRANTS_DIR']) / 'diag.grant').write_text('fixture grant\n')
        Path(env['FILLERS_MD']).write_text('fixture row\n')
        (self.root / 'manifest.json').write_text(json.dumps(manifest))
        args = type('Args', (), dict(id='diag', min_window=60, region_lock='region-lock',
              workdir=str(self.root), cmd='true', complete_cmd=complete_cmd,
              stop='STOP', self_claim=True, claim_cpus='', role='build', gpu_quiet='none',
              no_fold_siblings=False, requires_tool=[], **{'class': 'cpu'}))()
        allowed = {0, 1}
        now = time.time()
        original_run = subprocess.run
        def run_mock(command, *a, **kw):
            if command and command[0] == 'bash' and command[1] == '-c':
                return original_run(command, *a, **kw)
            return subprocess.CompletedProcess(command, 0, stdout='', stderr='')
        def fixture_run(_args, jobenv, _deadline, _log, _policy):
            Path(jobenv['FILLER_RESULTS_DIR']).mkdir(parents=True, exist_ok=True)
            done = original_run([sys.executable, str(fixture)], env=jobenv, cwd=self.root,
                                capture_output=True, text=True)
            return done.returncode, 'exited'
        with patch.object(engine, 'parse_grant', return_value=('0-1',
                     datetime.fromtimestamp(now - 1, timezone.utc),
                     datetime.fromtimestamp(now + 60, timezone.utc))), \
             patch.object(engine, 'grant_cpus', return_value=allowed), \
             patch.object(engine.subprocess, 'run', side_effect=run_mock), \
             patch.object(engine.os, 'sched_getaffinity', return_value=allowed), \
             patch.object(engine.os, 'sched_setaffinity'), \
             patch.dict(os.environ, {'WS58_QUAL': '1', 'WS58_QUAL_ROOT': '/wrong-global-root',
                                     'WS58_QUAL_MANIFEST': '/wrong-global-manifest',
                                     'WS58_QUAL_NONCE': 'c' * 32}), \
             patch.object(engine, 'run_job', side_effect=fixture_run):
            self.assertEqual(engine.qualify(args, dict(os.environ, **env), self.policy), 0)
        receipt = q.load(qroot / 'receipt-partial.json')
        self.assertEqual(receipt['nonce'], env['WS58_QUAL_NONCE'])
        self.assertEqual(receipt['qualification_root'], str(qroot.resolve()))
        self.assertNotIn('first_request', receipt)
        self.assertNotIn('measured_tok_s', receipt)
        terminal_path = qroot / 'grants' / 'diag.ended'
        engine.ended(terminal_path, 0, 'qualification-complete', False, phase='qualification')
        receipt['launcher_terminal'] = {'path': str(terminal_path), 'sha256': q.sha(terminal_path)}
        q.evidence_check(manifest, receipt, self.policy)
        valid_receipt = json.loads(json.dumps(receipt))
        receipt['completion']['predicate_sha256'] = '0' * 64
        with self.assertRaisesRegex(q.Refused, 'completion-predicate-unbound'):
            q.evidence_check(manifest, receipt, self.policy)
        for case, mutate, reason in (
            ('result hash', lambda p: p['result_writer'].__setitem__('sha256', '0' * 64), 'result-writer'),
            ('partial return code', lambda p: p['rc75'].__setitem__('exit_code', 0), 'rc75'),
            ('partial marker hash', lambda p: p['rc75'].__setitem__('partial_sha256', '0' * 64), 'rc75-partial-binding'),
            ('fixture item binding', lambda p: p['fixture'].__setitem__('items', 3), 'fixture-binding'),
        ):
            bad = json.loads(json.dumps(valid_receipt))
            mutate(bad)
            with self.subTest(case=case), self.assertRaisesRegex(q.Refused, reason):
                q.evidence_check(manifest, bad, self.policy)

    def test_native_diagnostic_rejects_inference_metrics(self):
        self.evidence['first_request'] = {'measured_tok_s': 123456, 'fixture_only': True}
        with self.assertRaisesRegex(q.Refused, 'native-diagnostic-inference-metrics-present'):
            q.evidence_check(self.manifest, self.evidence, self.policy)

    def test_native_diagnostic_rejects_unpinned_completion_predicate(self):
        self.evidence['completion']['predicate_sha256'] = '0' * 64
        with self.assertRaisesRegex(q.Refused, 'completion-predicate-unbound'):
            q.evidence_check(self.manifest, self.evidence, self.policy)

    def test_native_diagnostic_requires_retained_rc75_partial(self):
        self.partial.write_text('{"partial":false}\n')
        with self.assertRaisesRegex(q.Refused, 'rc75-partial-binding'):
            q.evidence_check(self.manifest, self.evidence, self.policy)

    def test_inference_profile_rejects_fixture_only_rate(self):
        manifest = dict(self.manifest, qualification_profile='inference')
        evidence = dict(self.evidence, qualification_profile='inference',
                        first_request={'ok': True, 'n_ctx': 999999,
                                       'prompt_tokens': 999999, 'measured_tok_s': 999999,
                                       'fixture_only': True})
        with self.assertRaisesRegex(q.Refused, 'first-request-is-fixture-only'):
            q.evidence_check(manifest, evidence, self.policy)

    def test_inference_profile_rejects_unmarked_unbound_synthetic_rate(self):
        manifest = dict(self.manifest, qualification_profile='inference')
        evidence = dict(self.evidence, qualification_profile='inference',
                        first_request={'ok': True, 'n_ctx': 999999,
                                       'prompt_tokens': 999999, 'measured_tok_s': 999999})
        with self.assertRaises(q.Refused):
            q.evidence_check(manifest, evidence, self.policy)


if __name__ == '__main__':
    unittest.main()
