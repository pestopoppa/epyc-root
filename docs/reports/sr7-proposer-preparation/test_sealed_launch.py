import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sealed_launch import launch_sealed


class SealedLaunchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.server = root / 'server'
        self.lib = root / 'libggml.so'
        self.server.write_bytes(b'server')
        self.server.chmod(0o700)
        self.lib.write_bytes(b'library')
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.seal = {'server': str(self.server), 'library_dir': str(root),
                     'files': {str(self.server): digest(self.server), str(self.lib): digest(self.lib)}}
        self.args = dict(seal=self.seal, argv=[str(self.server)], env={'LD_LIBRARY_PATH': str(root)},
                         trace_path=root / 'trace', admission=lambda: True)

    def test_checks_then_launches(self):
        with patch('sealed_launch.launch_owned', return_value='owned') as launch:
            self.assertEqual(launch_sealed(**self.args), 'owned')
        launch.assert_called_once()

    def test_changed_bytes_denial_and_revocation_never_launch(self):
        self.lib.write_bytes(b'changed')
        with patch('sealed_launch.launch_owned') as launch:
            with self.assertRaises(ValueError): launch_sealed(**self.args)
            launch.assert_not_called()
        self.lib.write_bytes(b'library')
        for checker in (lambda: False, iter([True, False]).__next__):
            self.args['admission'] = checker
            with patch('sealed_launch.launch_owned') as launch:
                with self.assertRaises(ValueError): launch_sealed(**self.args)
                launch.assert_not_called()

    def test_rejects_weights_and_unpinned_library_path(self):
        self.seal['files'][str(Path(self.tmp.name) / 'weights.gguf')] = 'a' * 64
        with self.assertRaises(ValueError): launch_sealed(**self.args)
        del self.seal['files'][str(Path(self.tmp.name) / 'weights.gguf')]
        self.args['env']['LD_LIBRARY_PATH'] += ':/foreign'
        with self.assertRaises(ValueError): launch_sealed(**self.args)


if __name__ == '__main__': unittest.main()
