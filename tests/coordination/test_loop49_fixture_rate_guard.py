"""Synthetic launcher probes must not be accepted as measured qualification."""
import unittest
import os
import secrets
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/coordination'))
import qualify_launcher as q


class FixtureRateGuard(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            'id': 'fixture-rate-guard',
            'items': 1,
            'tokens_per_item': 1,
            'n_ctx_required': 32,
            'window_s': 60,
            'requires_tools': ['bash'],
            'source_manifest': str(ROOT / 'scripts/coordination/qualify_launcher.py'),
            'qualification_model': {
                'id': 'fixture-model',
                'path': str(ROOT / 'scripts/coordination/qualify_launcher.py'),
                'sha256': 'a' * 64,
            },
        }
        self.qroot = Path(os.environ['LOOP49_TEST_ARTIFACTS']) / secrets.token_hex(8) / 'qual' / ('a' * 32)
        grants = self.qroot / 'grants'
        grants.mkdir(parents=True)
        deadline = grants / (self.manifest['id'] + '.deadline.ended')
        terminal = grants / (self.manifest['id'] + '.ended')
        deadline.write_text('rc=75 time=2026-11-01T00:00:00Z reason=fixture-deadline\npartial=true\nnative_complete=false\nphase=qualification\ngranted=true\n')
        terminal.write_text('rc=0 time=2026-11-01T00:00:00Z reason=qualification-complete\npartial=false\nnative_complete=false\nphase=qualification\ngranted=true\n')
        self.marker_hashes = {str(path.resolve()): q.sha(path) for path in (deadline, terminal)}
        result_path = str((self.qroot / 'results' / 'result.json').resolve())
        record_path = str((self.qroot / 'results' / 'first-request.json').resolve())
        self.receipt = {
            'admission': {'rc': 0, 'affinity_ok': True},
            'completion': {'complete_cmd_present': True, 'is_complete_rc': 0},
            'rc75': {'exit_code': 75, 'partial_flag': True,
                     'ended_path': str(deadline), 'ended_line_sha256': q.sha(deadline)},
            'launcher_terminal': {'path': str(terminal), 'sha256': q.sha(terminal)},
            'nonce': self.qroot.name,
            'disk': {'job_floor_gib': 150, 'policy_floor_gib': 150},
            'children_drained': True,
            'first_request': {
                'ok': True,
                'n_ctx': 32,
                'prompt_tokens': 1,
                'measured_tok_s': 40.0,
                'native_record': {
                    'record_kind': 'epyc.qual.native-first-request.v1',
                    'provenance': 'native-runtime',
                    'source_manifest_sha256': 'sourcehash',
                    'model_id': 'fixture-model',
                    'model_sha256': 'a' * 64,
                    'result_path': result_path,
                    'result_sha256': 'resultdigest',
                },
            },
            'first_request_record': {
                'record_kind': 'epyc.qual.native-first-request.v1',
                'path': record_path,
                'sha256': 'recorddigest',
            },
            'qualification_root': str(self.qroot),
            'result_writer': {'ok': True, 'result_path': result_path, 'sha256': 'resultdigest'},
            'exec_namespace': {'tools': {'bash': '/usr/bin/bash'}},
        }

    def check(self):
        paths = {
            **self.marker_hashes,
            str(Path(self.manifest['source_manifest']).resolve()): 'sourcehash',
            self.receipt['result_writer']['result_path']: 'resultdigest',
            self.receipt['first_request_record']['path']: 'recorddigest',
        }
        with (
            patch.object(q, 'sha', side_effect=lambda path: paths.get(str(Path(path).resolve()), 'digest')),
            patch.object(q, 'load', return_value=self.receipt['first_request']),
            patch.object(q, 'floor_gib', return_value=150),
            patch.object(Path, 'is_file', return_value=True),
        ):
            q.evidence_check(self.manifest, self.receipt, 'unused-policy')

    def test_model_free_fixture_cannot_be_measured_first_request(self):
        self.receipt['first_request']['fixture_only'] = True
        with self.assertRaisesRegex(q.Refused, 'first-request-is-fixture-only'):
            self.check()

    def test_fixture_scope_cannot_be_measured_first_request(self):
        self.receipt['first_request']['scope'] = 'model-free launcher qualification fixture'
        with self.assertRaisesRegex(q.Refused, 'first-request-is-fixture-only'):
            self.check()

    def test_real_request_evidence_still_passes(self):
        self.check()

    def test_unmarked_synthetic_rate_without_native_record_is_refused(self):
        self.receipt['first_request'].pop('native_record')
        with self.assertRaisesRegex(q.Refused, 'native-first-request-record-missing'):
            self.check()


if __name__ == '__main__':
    unittest.main()
