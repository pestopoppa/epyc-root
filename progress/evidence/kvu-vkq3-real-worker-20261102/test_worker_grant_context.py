"""Offline synthetic-grant coverage for the real worker's mode boundary."""
import datetime as dt
import os
from pathlib import Path
import tempfile
import time
import unittest

import worker


def stamp(epoch):
    return dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')


class WorkerGrantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.root = Path(self.tmp.name)
        self.dry = self.root / 'dry'; self.dry.mkdir()
        self.grants = self.dry / 'grants'; self.grants.mkdir()
        self.attempts = self.dry / 'native-attempts'; self.attempts.mkdir()
        self.attempt = Path(tempfile.mkdtemp(prefix='attempt-', dir=self.attempts))
        self.native = self.attempt / 'native-result.json'
        now = time.time()
        end = int(now // 60) * 60 + 600
        self.grant = self.grants / 'vkq3-test.grant'
        self.grant.write_text(f'regions=0-3 start={stamp(now - 60)} end={stamp(end)} holds= '
                              'schema=epyc.rowflow.dryrun-grant.v1 id=vkq3-test kind=rowflow-dryrun\n')
        self.env = {'FILLER_ID': 'vkq3-test', 'FILLER_NEEDGPU': '0', 'FILLER_DRYRUN': '1',
                    'FILLER_GRANTS_DIR': str(self.grants), 'FILLER_DRYRUN_DIR': str(self.dry),
                    'FILLER_DRYRUN_RESULT_PATH': str(self.native),
                    'FILLER_CPUS': '0-3', 'FILLER_END': str(end), 'FILLER_DEADLINE': str(end - 90),
                    'FILLER_STOPFILE': str(self.root / 'stop')}

    def tearDown(self):
        self.tmp.cleanup()

    def test_synthetic_four_cpu_grant_isolated_and_grant_loss_detected(self):
        guard, out, result = worker.grant_context(self.env, {'id': 'vkq3-test'})
        self.assertEqual(guard.mode, 'qualification')
        self.assertEqual(out, self.attempt / 'vkq3-control')
        self.assertEqual(result, self.native)
        self.assertFalse(guard.check())
        self.grant.unlink()
        self.assertTrue(guard.check())

    def test_rejects_result_outside_smoke_and_wrong_cpu_shape(self):
        with self.assertRaises(ValueError):
            worker.grant_context({**self.env, 'FILLER_DRYRUN_RESULT_PATH': str(self.root / 'bad')}, {'id': 'vkq3-test'})
        with self.assertRaises(ValueError):
            worker.grant_context({**self.env, 'FILLER_CPUS': '0-95'}, {'id': 'vkq3-test'})

    def test_native_result_no_overwrite(self):
        target = self.native
        worker.publish_native(self.dry, target, {'kind': 'qualification_control'})
        with self.assertRaises(ValueError):
            worker.publish_native(self.dry, target, {'kind': 'second'})
        self.assertIn('qualification_control', target.read_text())

    def test_rejects_traversal_symlink_and_non_native_paths(self):
        outside=self.root/'outside';outside.mkdir()
        bad=self.attempts/'attempt-link';bad.symlink_to(outside,target_is_directory=True)
        bad_paths=[bad/'native-result.json', self.attempt/'../'/'attempt-link'/'native-result.json',
                   self.attempt/'different.json', self.dry/'result.json']
        for path in bad_paths:
            with self.subTest(path=path), self.assertRaises(ValueError):
                worker.grant_context({**self.env,'FILLER_DRYRUN_RESULT_PATH':str(path)}, {'id':'vkq3-test'})
        self.native.symlink_to(outside/'result.json')
        with self.assertRaises(ValueError):
            worker.grant_context(self.env, {'id':'vkq3-test'})

    def test_prior_failed_attempt_does_not_poison_new_attempt(self):
        (self.attempt/'vkq3-control').mkdir()
        new=Path(tempfile.mkdtemp(prefix='attempt-',dir=self.attempts))
        _,out,result=worker.grant_context({**self.env,'FILLER_DRYRUN_RESULT_PATH':str(new/'native-result.json')}, {'id':'vkq3-test'})
        self.assertEqual(out,new/'vkq3-control')
        self.assertEqual(result,new/'native-result.json')
        self.assertFalse(out.exists())

    def test_rejects_symlinked_ancestor_and_native_attempts(self):
        alias=self.root/'dry-alias';alias.symlink_to(self.dry,target_is_directory=True)
        with self.assertRaises(ValueError):
            worker.open_native_attempt(alias,alias/'native-attempts'/self.attempt.name/'native-result.json')
        other=self.root/'other';other.mkdir()
        (other/'native-attempts').symlink_to(self.attempts,target_is_directory=True)
        with self.assertRaises(ValueError):
            worker.open_native_attempt(other,other/'native-attempts'/self.attempt.name/'native-result.json')


if __name__ == '__main__':
    unittest.main()
