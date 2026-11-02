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
        now = time.time()
        end = int(now // 60) * 60 + 600
        self.grant = self.grants / 'vkq3-test.grant'
        self.grant.write_text(f'regions=0-3 start={stamp(now - 60)} end={stamp(end)} holds= '
                              'schema=epyc.rowflow.dryrun-grant.v1 id=vkq3-test kind=rowflow-dryrun\n')
        self.env = {'FILLER_ID': 'vkq3-test', 'FILLER_NEEDGPU': '0', 'FILLER_DRYRUN': '1',
                    'FILLER_GRANTS_DIR': str(self.grants), 'FILLER_DRYRUN_DIR': str(self.dry),
                    'FILLER_DRYRUN_RESULT_PATH': str(self.dry / 'result.json'),
                    'FILLER_CPUS': '0-3', 'FILLER_END': str(end), 'FILLER_DEADLINE': str(end - 90),
                    'FILLER_STOPFILE': str(self.root / 'stop')}

    def tearDown(self):
        self.tmp.cleanup()

    def test_synthetic_four_cpu_grant_isolated_and_grant_loss_detected(self):
        guard, out, result = worker.grant_context(self.env, {'id': 'vkq3-test'})
        self.assertEqual(guard.mode, 'qualification')
        self.assertEqual(out, self.dry / 'vkq3-control')
        self.assertEqual(result, self.dry / 'result.json')
        self.assertFalse(guard.check())
        self.grant.unlink()
        self.assertTrue(guard.check())

    def test_rejects_result_outside_smoke_and_wrong_cpu_shape(self):
        with self.assertRaises(ValueError):
            worker.grant_context({**self.env, 'FILLER_DRYRUN_RESULT_PATH': str(self.root / 'bad')}, {'id': 'vkq3-test'})
        with self.assertRaises(ValueError):
            worker.grant_context({**self.env, 'FILLER_CPUS': '0-95'}, {'id': 'vkq3-test'})

    def test_native_result_no_overwrite(self):
        target = self.dry / 'result.json'
        worker.atom(target, {'kind': 'qualification_control'})
        with self.assertRaises(FileExistsError):
            worker.atom(target, {'kind': 'second'})
        self.assertIn('qualification_control', target.read_text())


if __name__ == '__main__':
    unittest.main()
