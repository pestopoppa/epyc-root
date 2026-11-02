import datetime as dt
import os
from pathlib import Path
import signal
import tempfile
import unittest

from grant_bridge_draft import run_guarded_attempt

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.grants = self.root / 'grants'; self.grants.mkdir()
        self.now = 1793613600
        self.end = self.now + 3600
        self.path = self.grants / 'sample.grant'
        stamp = lambda n: dt.datetime.fromtimestamp(n, dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        self.path.write_text(f'regions=0-95 start={stamp(self.now-60)} end={stamp(self.end)} holds=\n')
        self.env = {'FILLER_ID':'sample', 'FILLER_NEEDGPU':'0', 'FILLER_CPUS':'0-95',
                    'FILLER_END':str(self.end), 'FILLER_DEADLINE':str(self.end-90),
                    'FILLER_STOPFILE':str(self.root/'stop')}
    def args(self):
        return dict(env=self.env, grant_dir=self.grants, local_stop=self.root/'local-stop',
                    expected_id='sample', attempt_id='x', root=self.root, argv=['fake'],
                    input_bytes=b'abc', child_env={}, now=lambda:10., wall=lambda:self.now)
    def test_binds_real_guard_and_deadline(self):
        def worker(**kw):
            self.assertEqual(kw['mode'],'full')
            self.assertEqual(kw['deadline_monotonic'], 10.+3600-90-30)
            self.assertTrue(kw['grant_valid']())
            self.path.unlink()
            self.assertTrue(kw['stopped']())
            self.assertFalse(kw['grant_valid']())
        run_guarded_attempt(**self.args(),worker=worker)
    def test_invalid_grant_cannot_reach_worker(self):
        self.env['FILLER_CPUS']='0-23'
        with self.assertRaises(ValueError):
            run_guarded_attempt(**self.args(),worker=lambda **kw:self.fail('worker called'))
    def test_dryrun_mode_bound_to_guard(self):
        self.env.update(FILLER_DRYRUN='1', FILLER_CPUS='0-23')
        self.path.write_text(self.path.read_text().replace('regions=0-95','regions=0-23').rstrip() + ' schema=epyc.rowflow.dryrun-grant.v1 id=sample kind=rowflow-dryrun\n')
        self.assertEqual(run_guarded_attempt(**self.args(),worker=lambda **kw:kw['mode']),'qualification')

    def test_signal_cancels_and_restores_handlers_even_on_exception(self):
        old_int = signal.getsignal(signal.SIGINT)
        old_term = signal.getsignal(signal.SIGTERM)
        def worker(**kw):
            os.kill(os.getpid(), signal.SIGTERM)
            self.assertTrue(kw['stopped']())
            self.assertFalse(kw['grant_valid']())
            raise RuntimeError('deliberate failure')
        with self.assertRaisesRegex(RuntimeError, 'deliberate failure'):
            run_guarded_attempt(**self.args(), worker=worker)
        self.assertEqual(signal.getsignal(signal.SIGINT), old_int)
        self.assertEqual(signal.getsignal(signal.SIGTERM), old_term)

if __name__ == '__main__': unittest.main()
