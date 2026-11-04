"""Real process and synthetic cgroup checks, with no model inference."""

from dataclasses import replace
import hashlib
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest
from unittest import mock

import q38_t7_native_verify as native
import q38_t7_supervisor as supervisor


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class NativeVerificationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        model, script = root / 'model', root / 'fake.py'
        model.write_bytes(b'fake')
        script.write_text('import socket, sys, time\n'
                          'p=int(sys.argv[sys.argv.index("--port")+1])\n'
                          's=socket.socket(); s.bind(("127.0.0.1",p)); s.listen()\n'
                          'time.sleep(60)\n')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        shape = {'common_argv': [str(script), '-m', str(model), '--port', str(self.port)],
                 'binary_sha256': sha(sys.executable), 'model_sha256': sha(model), 'env': {}}
        self.recipe = {'binary': sys.executable, 'model': str(model), 'shape': shape,
                       'draft_model': None, 'draft_options': {}}
        self.sup = supervisor.Supervisor(lambda *_: True, lambda *_: True,
                                         log_path=str(root / 'log'))
        self.handle = self.sup.spawn('nodraft', self.recipe)
        libc = next(p for p in native._mapped_paths(os.getpid()) if Path(p).name.startswith('libc.so'))
        self.libs = {libc: sha(libc)}
        self.verify = native.NativeIdentityVerifier('127.0.0.1', self.port, self.libs,
                                                    lambda _: True, lambda *_: True,
                                                    require_ggml=False)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not self.verify(self.handle, 'nodraft', self.recipe):
            time.sleep(.01)

    def tearDown(self):
        if not self.handle.closed:
            self.sup.stop_and_drain(self.handle)
        self.tmp.cleanup()

    def test_real_child_argv_executable_mapped_library_and_socket(self):
        self.assertTrue(self.verify(self.handle, 'nodraft', self.recipe))
        self.assertEqual(len(native._owned_listeners(self.handle.process.pid, '127.0.0.1', self.port)), 1)
        self.assertEqual(native._owned_listeners(os.getpid(), '127.0.0.1', self.port), set())
        self.assertFalse(self.verify(replace(self.handle, birth='0'), 'nodraft', self.recipe))
        self.assertFalse(self.verify(replace(self.handle, argv=['wrong']), 'nodraft', self.recipe))
        other_port = native.NativeIdentityVerifier('127.0.0.1', self.port % 65535 + 1, self.libs,
                                                  lambda _: True, lambda *_: True,
                                                  require_ggml=False)
        self.assertFalse(other_port(self.handle, 'nodraft', self.recipe))
        wrong = native.NativeIdentityVerifier('127.0.0.1', self.port,
                                               {next(iter(self.libs)): '0' * 64},
                                               lambda _: True, lambda *_: True,
                                               require_ggml=False)
        self.assertFalse(wrong(self.handle, 'nodraft', self.recipe))
        with mock.patch.object(native, '_file_identity', return_value=(0, 0, 0)):
            self.assertFalse(self.verify(self.handle, 'nodraft', self.recipe))

    def test_missing_mode_or_membership_or_ggml_proof_refuses(self):
        self.verify.membership_verifier = lambda _: False
        self.assertFalse(self.verify(self.handle, 'nodraft', self.recipe))
        self.verify.membership_verifier = lambda _: True
        self.verify.mode_verifier = lambda *_: False
        self.assertFalse(self.verify(self.handle, 'nodraft', self.recipe))
        self.verify.mode_verifier = lambda *_: True
        self.verify.require_ggml = True
        self.assertFalse(self.verify(self.handle, 'nodraft', self.recipe))

    def test_cgroup_requires_exclusivity_and_empty_subtree(self):
        root = Path(self.tmp.name) / 'cgroup'
        leaf = root / 'owned'
        leaf.mkdir(parents=True)
        (leaf / 'cgroup.procs').write_text('')
        (leaf / 'cgroup.events').write_text('populated 0\nfrozen 0\n')
        check = native.ExclusiveCgroupDrainVerifier('owned', lambda *_: True, root=str(root))
        self.assertFalse(check(self.handle))  # captured child remains alive
        self.assertTrue(self.sup.stop_and_drain(self.handle))
        self.assertTrue(check(self.handle))
        (leaf / 'cgroup.events').write_text('populated 1\nfrozen 0\n')
        self.assertFalse(check(self.handle))
        (leaf / 'cgroup.events').write_text('populated 0\nfrozen 0\n')
        (leaf / 'cgroup.procs').write_text('42\n')
        self.assertFalse(check(self.handle))
        (leaf / 'cgroup.procs').write_text('')
        check.ownership_verifier = lambda *_: False
        self.assertFalse(check(self.handle))
        with self.assertRaises(ValueError):
            native.ExclusiveCgroupDrainVerifier('../escape', lambda *_: True, root=str(root))


if __name__ == '__main__':
    unittest.main()
