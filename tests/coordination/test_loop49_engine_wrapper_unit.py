"""Focused engine regressions that do not require a compute grant."""
import os
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/coordination'))
import filler_engine14 as engine


class EngineWrapperUnit(unittest.TestCase):
    def args(self, **overrides):
        values = dict(id='row-1', cmd='printf fixture', region_lock='/fixture/region-lock',
                      **{'class': 'cpu'},
                      role='build', claim_cpus='', self_claim=False, no_fold_siblings=False,
                      gpu_quiet='none')
        values.update(overrides)
        return type('Args', (), values)()

    def test_qualification_and_production_wrapper_includes_taskset_and_region_lock(self):
        args = self.args()
        command = shlex.split(engine.wrapped_job_command(args, '2,3', 60))
        self.assertEqual(command[:8], ['/fixture/region-lock', 'run', '--cpu-list', '2,3',
                                       '--role', 'build', '--tag', 'filler-row-1'])
        self.assertIn('--timeout-s', command)
        self.assertEqual(command[-7:], ['--', 'taskset', '-c', '2,3', 'bash', '-c', 'printf fixture'])

    def test_self_claim_still_uses_taskset(self):
        command = shlex.split(engine.wrapped_job_command(self.args(self_claim=True), '4,5', 30))
        self.assertEqual(command, ['taskset', '-c', '4,5', 'bash', '-c', 'printf fixture'])

    def test_production_owner_is_bound_from_verified_manifest(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(engine.bind_production_owner({'owner': 'refactor'}), 'refactor')
            self.assertNotIn('WS58_OWNER', os.environ)
            with self.assertRaisesRegex(engine.Refused, 'manifest-owner-missing'):
                engine.bind_production_owner({'owner': ' '})

    def test_unverified_environment_owner_cannot_enter_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'row-1.ended'
            with patch.dict(os.environ, {'WS58_OWNER': 'attacker'}, clear=True):
                engine.ended(target, 70, 'pre-verification-refusal', phase='production')
            self.assertNotIn('owner=', target.read_text())

    def test_qualification_ended_records_synthetic_grant(self):
        with tempfile.TemporaryDirectory() as tmp:
            ended = Path(tmp) / 'row-1.ended'
            Path(tmp, 'row-1.grant').write_text('synthetic\n')
            with patch.dict(os.environ, {'WS58_QUAL': '1', 'WS58_OWNER': 'must-not-leak'}):
                engine.ended(ended, 0, 'qualification-complete')
            record = ended.read_text()
            self.assertIn('phase=qualification\ngranted=true\n', record)
            self.assertNotIn('owner=', record)
            self.assertNotIn('grant_body_b64=', record)

    def test_production_ended_records_bound_owner_and_grant(self):
        with tempfile.TemporaryDirectory() as tmp:
            ended = Path(tmp) / 'row-1.ended'
            Path(tmp, 'row-1.grant').write_text('regions=q0 start=2026-11-01T00:00Z end=2026-11-01T01:00Z\n')
            with patch.dict(os.environ, {'WS58_OWNER': 'attacker'}, clear=True):
                engine.ended(ended, 0, 'complete', phase='production', owner='refactor')
            record = ended.read_text()
            self.assertIn('phase=production\ngranted=true\n', record)
            self.assertIn('id=row-1\nowner=refactor\n', record)
            self.assertIn('grant_path=' + str(Path(tmp, 'row-1.grant').resolve()) + '\n', record)
            self.assertIn('grant_regions=q0\n', record)
            self.assertIn('grant_sha256=', record)
            self.assertIn('grant_body_b64=', record)

    def test_actual_engine_terminal_is_accepted_by_quota_parser(self):
        import science_quota as sq
        from datetime import datetime, timezone
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            terminal = Path(tmp) / 'row-1.ended'
            grant = terminal.with_suffix('.grant')
            grant.write_text('regions=q0 start=2026-11-01T00:00Z end=2026-11-01T01:00Z\n')
            engine.ended(terminal, 0, 'complete', phase='production', owner='verified-owner')
            record = dict(id='row-1', owner='verified-owner', phase='production', granted=True,
                          outcome='COMPLETE', event_time=datetime.now(timezone.utc).isoformat(),
                          terminal_evidence=dict(ended_path=str(terminal),
                              ended_sha256=hashlib.sha256(terminal.read_bytes()).hexdigest(),
                              grant_path=str(grant), grant_sha256=hashlib.sha256(grant.read_bytes()).hexdigest()))
            self.assertEqual(sq.terminal_proof(record), (True, ''))

    def test_empty_terminal_fails_closed(self):
        import science_quota as sq
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            terminal = Path(tmp) / 'row-1.ended'; terminal.write_bytes(b'')
            record = dict(id='row-1', terminal_evidence=dict(ended_path=str(terminal),
                ended_sha256=hashlib.sha256(b'').hexdigest(), grant_path=str(terminal.with_suffix('.grant'))))
            self.assertEqual(sq.terminal_proof(record), (False, 'terminal-ended-schema-invalid'))


if __name__ == '__main__':
    unittest.main()
