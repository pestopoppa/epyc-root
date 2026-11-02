import copy
import unittest

from container_backend import Refused, verify_inspection


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.image = 'sha256:' + 'a' * 64
        self.good = {'Image': self.image, 'Config': {'User': '65534:65534'},
                     'HostConfig': {'NetworkMode': 'none', 'Privileged': False,
                                    'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges'],
                                    'PidsLimit': 128, 'Memory': 8589934592,
                                    'NanoCpus': 4000000000},
                     'Mounts': [], 'State': {'Running': True}}

    def test_safe_inspection(self):
        verify_inspection(self.good, self.image)

    def test_refuses_escape_or_missing_limits(self):
        changes = [('Image', 'wrong'), ('Mounts', [{'Source': '/'}]),
                   ('State', {'Running': False})]
        for key, val in changes:
            bad = copy.deepcopy(self.good); bad[key] = val
            with self.subTest(key=key), self.assertRaises(Refused):
                verify_inspection(bad, self.image)
        for key, val in [('NetworkMode', 'host'), ('Privileged', True), ('CapDrop', []),
                         ('CapAdd', ['SYS_ADMIN']), ('SecurityOpt', ['no-new-privileges', 'seccomp=unconfined']),
                         ('Binds', ['/etc:/host']), ('Devices', ['/dev/kfd']), ('PidMode', 'host'),
                         ('IpcMode', 'host'), ('Memory', 0), ('NanoCpus', 0), ('PidsLimit', 0)]:
            bad = copy.deepcopy(self.good); bad['HostConfig'][key] = val
            with self.subTest(key=key), self.assertRaises(Refused):
                verify_inspection(bad, self.image)
        bad = copy.deepcopy(self.good); bad['Config']['User'] = '0:0'
        with self.assertRaises(Refused): verify_inspection(bad, self.image)

class PathTests(unittest.TestCase):
    def test_reject_absolute_traversal_and_nul(self):
        from container_backend import safe_relative_path
        for path in ('', '/', '/etc/passwd', '../etc/passwd', 'x/../../etc', 'x\0z', '.', './src/file.py'):
            with self.subTest(path=path):
                self.assertFalse(safe_relative_path(path))
        for path in ('a', 'src/file.py'):
            with self.subTest(path=path):
                self.assertTrue(safe_relative_path(path))

class BackendTests(unittest.TestCase):
    def test_cleanup_on_error(self):
        from container_backend import run_with_cleanup
        from types import SimpleNamespace
        calls = []
        env = SimpleNamespace(_p5_container=SimpleNamespace(close=lambda: calls.append('closed')))
        def bad(*args):
            raise RuntimeError('trial failed')
        with self.assertRaisesRegex(RuntimeError, 'trial failed'):
            run_with_cleanup(bad, None, env)
        self.assertEqual(calls, ['closed'])

    def test_file_access_refuses_symlink_escape(self):
        import base64
        import os
        import tempfile
        from pathlib import Path
        from sandbox_file import execute
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'testbed'; root.mkdir()
            outside = Path(tmp) / 'outside'; outside.mkdir()
            (outside / 'secret').write_text('private')
            os.symlink(outside, root / 'escape')
            os.symlink(outside / 'secret', root / 'link')
            with self.assertRaises(OSError): execute(str(root), 'read', 'escape/secret')
            with self.assertRaises(OSError): execute(str(root), 'read', 'link')
            with self.assertRaises(OSError): execute(str(root), 'write', 'escape/secret', 'eA==')
            self.assertEqual((outside / 'secret').read_text(), 'private')
            execute(str(root), 'write', 'new/file', base64.b64encode(b'ok').decode())
            self.assertEqual(execute(str(root), 'read', 'new/file'), b'ok')


if __name__ == '__main__':
    unittest.main()
