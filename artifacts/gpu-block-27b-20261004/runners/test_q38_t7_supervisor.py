"""Real captured-child tests with synthetic Python processes, never inference."""

import hashlib
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import unittest
from unittest import mock

import q38_t7_runtime as runtime
import q38_t7_supervisor as supervisor


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SupervisorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        script = root / 'fake_server.py'
        script.write_text('import time\ntime.sleep(60)\n')
        model, draft = root / 'model', root / 'draft'
        model.write_bytes(b'fake model'); draft.write_bytes(b'fake draft')
        shape = {'common_argv': [str(script), '-m', str(model)],
                 'binary_sha256': digest(sys.executable), 'model_sha256': digest(model),
                 'env': {'PATH': os.environ.get('PATH', '/usr/bin:/bin')}}
        base = {'binary': sys.executable, 'model': str(model), 'shape': shape}
        self.recipes = {
            'drafted': dict(base, draft_model=str(draft),
                            draft_options={'type': 'draft-dflash', 'n_max': 7,
                                           'draft_sha256': digest(draft)}),
            'nodraft': dict(base, draft_model=None, draft_options={}),
        }
        self.drained = True
        self.sup = supervisor.Supervisor(
            lambda h, arm, recipe: h.process.poll() is None,
            lambda h: self.drained and h.process.poll() is not None,
            log_path=str(root / 'fake.log'), stop_timeout=2)
        self.handles = []

    def tearDown(self):
        for handle in self.handles:
            if handle.process.poll() is None:
                handle.process.kill()
                handle.process.wait(timeout=2)
            if not handle.closed:
                os.close(handle.pidfd)
        self.temp.cleanup()

    def test_exact_sequential_children_and_mode_argv(self):
        for arm in ('drafted', 'nodraft'):
            handle = self.sup.spawn(arm, self.recipes[arm])
            self.handles.append(handle)
            self.assertTrue(self.sup.verify(handle, arm, self.recipes[arm]))
            with mock.patch.object(supervisor, '_sha256', side_effect=AssertionError('rehash during request')):
                self.assertTrue(self.sup.verify(handle, arm, self.recipes[arm]))
            self.assertEqual('-md' in handle.argv, arm == 'drafted')
            self.assertEqual('--spec-type' in handle.argv, arm == 'drafted')
            self.assertTrue(self.sup.stop_and_drain(handle))
            self.assertIsNotNone(handle.process.poll())
        self.assertNotEqual(self.handles[0].process.pid, self.handles[1].process.pid)

    def test_unverified_descendant_drain_refuses_next_arm(self):
        self.drained = False
        rt = runtime.Runtime(self.sup, object(), object(), lambda: False)
        server = rt.start('drafted', self.recipes['drafted'])
        self.handles.append(server.handle)
        rt.verify(server, 'drafted', self.recipes['drafted'])
        self.assertFalse(rt.stop(server))
        self.assertTrue(rt.cleanup_unverified)
        self.assertIs(rt.active, server)
        with self.assertRaises(runtime.RuntimeFailure):
            rt.start('nodraft', self.recipes['nodraft'])
        self.drained = True
        self.assertTrue(rt.stop(server))
        with self.assertRaises(runtime.RuntimeFailure):
            rt.start('nodraft', self.recipes['nodraft'])

    def test_recipe_rejects_draft_in_common_and_ambient_env(self):
        import copy
        bad = copy.deepcopy(self.recipes['nodraft'])
        bad['shape']['common_argv'] += ['--model-draft=/tmp/draft']
        with self.assertRaisesRegex(ValueError, 'draft options'):
            supervisor.command_for('nodraft', bad)
        bad = copy.deepcopy(self.recipes['nodraft'])
        bad['shape']['env']['LLAMA_ARG_MODEL_DRAFT'] = '/tmp/draft'
        with self.assertRaisesRegex(ValueError, 'environment'):
            supervisor.command_for('nodraft', bad)
        bad = copy.deepcopy(self.recipes['nodraft'])
        bad['shape']['common_argv'] += ['--model=/other']
        with self.assertRaisesRegex(ValueError, 'ambiguous model'):
            supervisor.command_for('nodraft', bad)

    def test_wrong_model_or_identity_refuses(self):
        import copy
        bad = copy.deepcopy(self.recipes['nodraft'])
        bad['shape']['model_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            supervisor.command_for('nodraft', bad)
        handle = self.sup.spawn('nodraft', self.recipes['nodraft'])
        self.handles.append(handle)
        self.sup.identity_verifier = lambda *_: False
        self.assertFalse(self.sup.verify(handle, 'nodraft', self.recipes['nodraft']))
        self.assertTrue(self.sup.stop_and_drain(handle))

    def test_exact_child_escalates_when_sigterm_is_ignored(self):
        script = Path(self.recipes['nodraft']['shape']['common_argv'][0])
        sentinel = script.parent / 'ready'
        script.write_text('import signal, time\n'
                          'from pathlib import Path\n'
                          'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                          f'Path({str(sentinel)!r}).touch()\n'
                          'time.sleep(60)\n')
        self.sup.stop_timeout = .05
        handle = self.sup.spawn('nodraft', self.recipes['nodraft'])
        self.handles.append(handle)
        deadline = time.monotonic() + 3
        while not sentinel.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(sentinel.exists())
        self.assertTrue(self.sup.stop_and_drain(handle))
        self.assertEqual(handle.process.returncode, -9)

    def test_cleanup_leaves_unrelated_captured_test_process_alive(self):
        peer = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        try:
            handle = self.sup.spawn('nodraft', self.recipes['nodraft'])
            self.handles.append(handle)
            self.assertTrue(self.sup.stop_and_drain(handle))
            self.assertIsNone(peer.poll())
        finally:
            if peer.poll() is None:
                peer.terminate()
                peer.wait(timeout=2)


if __name__ == '__main__':
    unittest.main()
