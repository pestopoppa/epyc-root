import unittest
import os
import sys
import tempfile
import time
from pathlib import Path
from worker_draft import run_attempt


class WorkerDraftTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def args(self):
        return dict(mode='full', attempt_id='a', root=self.tmp.name, argv=['fake'],
                    input_bytes=b'abc', env={}, deadline_monotonic=20.,
                    cleanup_margin_s=2., grant_valid=lambda: True,
                    stopped=lambda: False, now=lambda: 10.)

    def test_ceiling_mode_and_length_reach_components(self):
        observed = {}
        def supervisor(argv, data, env, **kw):
            observed.update(kw)
            return {'status': 'completed'}
        def writer(root, attempt_id, mode, result, **kw):
            return mode, result, kw
        mode, result, receipt = run_attempt(**self.args(), supervise_fn=supervisor, write_fn=writer)
        self.assertEqual(mode, 'full')
        self.assertEqual(observed['timeout_s'], 8.)
        self.assertEqual(receipt['expected_input_bytes'], 3)
        self.assertEqual(result['status'], 'completed')

    def test_qualification_is_not_promoted(self):
        args = self.args(); args['mode'] = 'qualification'
        result = run_attempt(**args, supervise_fn=lambda *a, **k: {'status': 'completed'},
                             write_fn=lambda root, ident, mode, result, **kw: mode)
        self.assertEqual(result, 'qualification')

    def test_invalid_grant_or_deadline_prevents_launch(self):
        args = self.args(); args['grant_valid'] = lambda: False
        with self.assertRaises(ValueError): run_attempt(**args)
        args = self.args(); args['deadline_monotonic'] = 11.
        with self.assertRaises(ValueError): run_attempt(**args)

    def test_lost_grant_after_exit_cannot_record_success(self):
        args = self.args(); grant = [True]
        args['grant_valid'] = lambda: grant[0]
        def supervisor(*a, **kw):
            grant[0] = False
            self.assertTrue(kw['stopped']())
            return {'status': 'completed'}
        status = run_attempt(**args, supervise_fn=supervisor,
                             write_fn=lambda root, ident, mode, result, **kw: result['status'])
        self.assertEqual(status, 'cancelled')

    def test_bad_custody_refuses_before_child_launch(self):
        args = self.args()
        args['attempt_id'] = '../bad'
        with self.assertRaises(ValueError):
            run_attempt(**args, supervise_fn=lambda *a, **k: self.fail('child launched'))
        args = self.args()
        os.chmod(self.tmp.name, 0o755)
        with self.assertRaises(ValueError):
            run_attempt(**args, supervise_fn=lambda *a, **k: self.fail('child launched'))
        os.chmod(self.tmp.name, 0o700)
        Path(self.tmp.name, 'full-a').mkdir()
        with self.assertRaises(FileExistsError):
            run_attempt(**args, supervise_fn=lambda *a, **k: self.fail('child launched'))

    def test_real_fake_child_writes_native_result(self):
        import json
        args = self.args()
        args.update(argv=[sys.executable, '-c', 'import sys; sys.stdin.buffer.read(); print("[1, 2, 30]")'],
                    env=dict(os.environ), deadline_monotonic=time.monotonic()+10,
                    now=time.monotonic)
        directory = run_attempt(**args)
        data = json.loads((directory / 'result.json').read_text())
        self.assertEqual((data['status'], data['validated_token_count']), ('completed', 3))
        self.assertTrue((directory / 'complete.json').exists())

    def test_default_containment_cancels_and_reaps_child(self):
        import json
        from unittest import mock
        import contained_supervisor_draft
        marker = Path(self.tmp.name, 'child.pid')
        script = ('import os, signal, sys; '
                  'open(sys.argv[1], "w").write(str(os.getpid())); '
                  'signal.pause()')
        args = self.args()
        args.update(argv=[sys.executable, '-c', script, str(marker)],
                    env=dict(os.environ), deadline_monotonic=time.monotonic()+10,
                    now=time.monotonic, stopped=marker.exists)
        with mock.patch.object(contained_supervisor_draft, 'supervise',
                               wraps=contained_supervisor_draft.supervise) as actual:
            directory = run_attempt(**args)
        command = actual.call_args.args[0]
        self.assertEqual(Path(command[1]).name, 'pdeath_exec_draft.py')
        data = json.loads((directory / 'result.json').read_text())
        self.assertEqual((data['status'], data['cleanup']), ('cancelled', True))
        pid = int(marker.read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)


if __name__ == '__main__':
    unittest.main()
