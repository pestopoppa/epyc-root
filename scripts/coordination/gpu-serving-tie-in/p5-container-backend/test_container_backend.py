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
                                    'NanoCpus': 4000000000, 'AutoRemove': True},
                     'Mounts': [], 'State': {'Running': True}}

    def test_safe_inspection(self):
        verify_inspection(self.good, self.image)

    def test_row_cpu_binding_is_required_when_requested(self):
        self.good['HostConfig']['CpusetCpus'] = '0-3'
        verify_inspection(self.good, self.image, '0-3')
        with self.assertRaises(Refused):
            verify_inspection(self.good, self.image, '4-7')

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
                         ('IpcMode', 'host'), ('Memory', 0), ('NanoCpus', 0), ('PidsLimit', 0),
                         ('AutoRemove', False)]:
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
    def test_git_reset_diff_and_add_use_direct_sandbox_entry(self):
        from container_backend import contained_env
        from types import SimpleNamespace
        from unittest.mock import patch

        class DockerEnv:
            def __init__(self, container, docker_bin='docker'):
                pass
        harness = SimpleNamespace(DockerEnv=DockerEnv, TIMEOUT_EXIT=124, _timeout_msg=lambda t: 'timeout')
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        with patch('container_backend.subprocess.run', side_effect=run):
            env = contained_env(harness, 'c' * 64, 'docker')
            self.assertEqual(env.reset_testbed('a' * 40), (True, ''))
            env._exec('git -C /testbed diff', 5)
            env._exec("git -C /testbed add -N -- 'src/file.py'", 5)
            env._exec('git status; echo model-command', 5)
        self.assertEqual([x[x.index('--git') + 1:] for x in calls[:4]], [
            ['reset', '--hard', 'a' * 40], ['clean', '-fd'],
            ['-C', '/testbed', 'diff'], ['-C', '/testbed', 'add', '-N', '--', 'src/file.py']])
        self.assertNotIn('--git', calls[4])
        self.assertIn('git status; echo model-command', calls[4][-1])

    def test_git_reset_reports_stderr_and_refuses_bad_commit(self):
        from container_backend import contained_env
        from types import SimpleNamespace
        from unittest.mock import patch
        class DockerEnv:
            def __init__(self, container, docker_bin='docker'):
                pass
        harness = SimpleNamespace(DockerEnv=DockerEnv, TIMEOUT_EXIT=124, _timeout_msg=lambda t: 'timeout')
        with patch('container_backend.subprocess.run', return_value=SimpleNamespace(returncode=128, stdout='', stderr='fatal: unsafe repository')):
            env = contained_env(harness, 'c' * 64, 'docker')
            self.assertEqual(env.reset_testbed('bad'), (False, 'invalid base commit'))
            self.assertEqual(env.reset_testbed('a' * 40), (False, 'fatal: unsafe repository'))

    def test_direct_git_entry_scopes_trust_without_disabling_containment(self):
        import os
        import runpy
        import sys
        from types import ModuleType, SimpleNamespace
        from unittest.mock import patch
        class ExecCalled(BaseException):
            pass
        seen = {}
        def wrap(command, policy):
            seen['command'] = command
            seen['policy'] = policy
            return ['/shim', *command], {}
        policy = object()
        fake_sandbox = SimpleNamespace(wrap=wrap, Policy=lambda: policy)
        pkg = ModuleType('src.repl_environment'); pkg.exec_sandbox = fake_sandbox
        src = ModuleType('src'); src.repl_environment = pkg
        def execvpe(file, argv, env):
            seen['env'] = env
            raise ExecCalled()
        entry = str(__import__('pathlib').Path(__file__).with_name('sandbox_entry.py'))
        with patch.dict(sys.modules, {'src': src, 'src.repl_environment': pkg}), \
             patch.object(sys, 'argv', [entry, '--git', 'reset', '--hard', 'a' * 40]), \
             patch('shutil.which', return_value='/usr/bin/git'), \
             patch.object(os, 'execvpe', side_effect=execvpe), patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ExecCalled):
                runpy.run_path(entry, run_name='__main__')
        self.assertEqual(seen['command'], ['/usr/bin/git', 'reset', '--hard', 'a' * 40])
        self.assertIs(seen['policy'], policy)
        self.assertEqual(seen['env']['GIT_CONFIG_VALUE_0'], '/testbed')
        self.assertEqual(seen['env']['GIT_CONFIG_KEY_0'], 'safe.directory')
        self.assertEqual(seen['env']['GIT_CONFIG_COUNT'], '1')

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
