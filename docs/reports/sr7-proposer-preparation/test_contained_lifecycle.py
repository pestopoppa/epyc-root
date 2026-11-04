import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

import contained_lifecycle as life


class LifecycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.admit = MagicMock(spec=life.KeeperAdmission)
        self.admit.return_value = True
        self.admit.deadline = time.time() + 120
        self.admit.stop_path = self.root / 'STOP'
        self.proc = MagicMock(pid=12345)
        self.proc.poll.return_value = None
        self.args = dict(root=self.root, request_id='x', payload={'prompt':'hello', 'cache_prompt':False, 'stream':False, 'n_predict':1},
                         expected_names=['mtp'], port=23456, timeout_s=2, admission=self.admit,
                         argv=['/bin/true'], env={'LD_LIBRARY_PATH':'/tmp'}, cwd='/tmp',
                         verify=lambda p, port: {'identity':'verified'}, trace_path=self.root/'trace')

    def test_revoked_in_flight_and_drained(self):
        def captured(**kw):
            p = kw['launch']()
            try:
                kw['verify'](p, 23456)
                with self.assertRaisesRegex(ValueError, 'cancelled'):
                    kw['post'](23456, {'prompt':'hello'}, 2)
            finally:
                kw['stop'](p)
            return kw['read_trace'](p)
        def transport(*args, **kwargs):
            check = kwargs['continue_check']
            def run(*unused):
                self.assertTrue(check())
                self.admit.stop_path.touch()
                self.assertFalse(check())
                raise ValueError('cancelled')
            return run
        with patch.object(life, 'capture_once', side_effect=captured), \
             patch.object(life, 'spawn_contained_session', return_value=self.proc), \
             patch.object(life, 'drain_contained_session') as drain, \
             patch.object(life, 'process_starttime', return_value=44), \
             patch.object(life, 'verify_owned_loopback_listener'), \
             patch.object(life, 'LoopbackCompletion', side_effect=transport):
            self.assertEqual(life.capture_contained(**self.args), b'')
            drain.assert_called_once_with(self.proc, 5)

    def test_real_capture_drains_on_verifier_failure(self):
        self.args['verify'] = lambda p, port: (_ for _ in ()).throw(ValueError('bad identity'))
        with patch.object(life, 'spawn_contained_session', return_value=self.proc), \
             patch.object(life, 'drain_contained_session') as drain:
            with self.assertRaisesRegex(ValueError, 'bad identity'):
                life.capture_contained(**self.args)
            drain.assert_called_once_with(self.proc, 5)
            self.assertTrue((self.root/'x.start.json').exists())

    def test_no_launch_if_admission_revoked(self):
        self.admit.return_value = False
        with patch.object(life, 'spawn_contained_session') as spawn:
            with self.assertRaisesRegex(ValueError, 'admission'):
                life.capture_contained(**self.args)
            spawn.assert_not_called()

    def test_deadline_guard(self):
        self.admit.deadline = time.time() + 1
        def captured(**kw):
            p = kw['launch']()
            kw['verify'](p, 23456)
            try:
                with self.assertRaisesRegex(ValueError, 'deadline'):
                    kw['post'](23456, {'prompt':'hello'}, 2)
            finally:
                kw['stop'](p)
        with patch.object(life, 'capture_once', side_effect=captured), \
             patch.object(life, 'spawn_contained_session', return_value=self.proc), \
             patch.object(life, 'drain_contained_session'), \
             patch.object(life, 'process_starttime', return_value=44), \
             patch.object(life, 'verify_owned_loopback_listener'):
            life.capture_contained(**self.args)

if __name__ == '__main__':
    unittest.main()
