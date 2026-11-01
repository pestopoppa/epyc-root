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

    def test_qualification_ended_records_synthetic_grant(self):
        with tempfile.TemporaryDirectory() as tmp:
            ended = Path(tmp) / 'row-1.ended'
            Path(tmp, 'row-1.grant').write_text('synthetic\n')
            with patch.dict(os.environ, {'WS58_QUAL': '1'}):
                engine.ended(ended, 0, 'qualification-complete')
            record = ended.read_text()
            self.assertIn('phase=qualification\ngranted=true\n', record)

    def test_production_ended_records_real_grant(self):
        with tempfile.TemporaryDirectory() as tmp:
            ended = Path(tmp) / 'row-1.ended'
            Path(tmp, 'row-1.grant').write_text('real\n')
            with patch.dict(os.environ, {}, clear=True):
                engine.ended(ended, 0, 'complete')
            self.assertIn('phase=production\ngranted=true\n', ended.read_text())


if __name__ == '__main__':
    unittest.main()
