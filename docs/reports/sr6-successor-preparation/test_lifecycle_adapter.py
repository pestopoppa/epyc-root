import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from lifecycle_adapter import LifecycleAdapters
from native_worker import ARMS

class AdapterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.admission = Mock(return_value=True)
        self.adapter = LifecycleAdapters(argv_by_arm={a: ['/bin/server', a] for a in ARMS},
            env={'LD_LIBRARY_PATH': '/kernel'}, cwd='/', library_dir='/kernel',
            build_root=Path('/kernel'), port=1234, admission_check=self.admission,
            evidence_dir=Path(self.tmp.name), startup_timeout_s=1)

    @patch('lifecycle_adapter.verify_ready_server', return_value={'witness': 'ok'})
    @patch('lifecycle_adapter.spawn_contained_session')
    def test_bound_process_and_arm(self, spawn, verify):
        process = spawn.return_value
        process.poll.return_value = None
        self.assertIs(self.adapter.spawn('mtp3'), process)
        self.assertEqual(spawn.call_args.args[0], ['/bin/server', 'mtp3'])
        self.assertEqual(self.adapter.verify_ready_and_identity(process, 'mtp3'), {'witness': 'ok'})
        self.assertEqual(verify.call_args.kwargs['expected_argv'], ['/bin/server', 'mtp3'])
        with self.assertRaises(ValueError):
            self.adapter.verify_ready_and_identity(process, 'mtp3')

    @patch('lifecycle_adapter.verify_ready_server', return_value={'witness': 'ok'})
    @patch('lifecycle_adapter.spawn_contained_session')
    def test_approved_numactl_exec_replaces_prefix(self, spawn, verify):
        adapter = LifecycleAdapters(
            argv_by_arm={a: ['/usr/bin/numactl', '--interleave=all', '/bin/server', a] for a in ARMS},
            env={'LD_LIBRARY_PATH': '/kernel'}, cwd='/', library_dir='/kernel',
            build_root=Path('/kernel'), port=1234, admission_check=self.admission,
            evidence_dir=Path(self.tmp.name), startup_timeout_s=1800)
        process = adapter.spawn('mtp3')
        process.poll.return_value = None
        self.assertEqual(spawn.call_args.args[0], ['/usr/bin/numactl', '--interleave=all', '/bin/server', 'mtp3'])
        adapter.verify_ready_and_identity(process, 'mtp3')
        self.assertEqual(verify.call_args.kwargs['expected_argv'], ['/bin/server', 'mtp3'])

    @patch('lifecycle_adapter.spawn_contained_session')
    def test_revocation_before_verification(self, spawn):
        process = spawn.return_value
        process.poll.return_value = None
        self.adapter.spawn('mtp3')
        self.admission.return_value = False
        with patch('lifecycle_adapter.verify_ready_server') as verify, self.assertRaises(ValueError):
            self.adapter.verify_ready_and_identity(process, 'mtp3')
        verify.assert_not_called()

    @patch('lifecycle_adapter.drain_contained_session')
    @patch('lifecycle_adapter.spawn_contained_session')
    def test_drain_requires_owned_child_and_retires_it(self, spawn, drain):
        child = self.adapter.spawn('mtp3')
        with self.assertRaises(ValueError):
            self.adapter.drain(Mock(), 2)
        self.adapter.drain(child, 2)
        drain.assert_called_once_with(child, 2)
        with self.assertRaises(ValueError):
            self.adapter.drain(child, 2)

    @patch('lifecycle_adapter.spawn_contained_session')
    def test_refuses_swapped_arm(self, spawn):
        process = spawn.return_value
        self.adapter.spawn('mtp3')
        with self.assertRaises(ValueError):
            self.adapter.verify_ready_and_identity(process, 'mtp4')

if __name__ == '__main__':
    unittest.main()
