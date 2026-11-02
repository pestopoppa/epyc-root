import signal
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from session_drain import DrainError, drain_session, spawn_session, _signal_captured


class SessionDrainTest(unittest.TestCase):
    def test_spawn_has_owned_session_no_shell(self):
        with patch('session_drain.subprocess.Popen') as popen:
            spawn_session(['/bin/true'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={}, cwd='/tmp')
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        self.assertNotIn('shell', popen.call_args.kwargs)

    def test_pidfd_revalidates_identity_before_signal(self):
        with patch('session_drain.os.pidfd_open', return_value=9), patch('session_drain.os.close'), \
             patch('session_drain._stat', return_value=('S', 21, 101)), \
             patch('session_drain.signal.pidfd_send_signal') as send:
            _signal_captured(22, 101, 21, signal.SIGTERM)
            send.assert_called_once_with(9, signal.SIGTERM)
            with self.assertRaises(DrainError):
                _signal_captured(22, 100, 21, signal.SIGTERM)
            self.assertEqual(send.call_count, 1)

    def test_escalates_and_refuses_surviving_session(self):
        proc = MagicMock(spec=subprocess.Popen); proc.pid = 21
        # A monotonic sequence advances immediately through each bounded window.
        with patch('session_drain._session_members', return_value={22: 100}), \
             patch('session_drain._signal_captured') as send, \
             patch('session_drain.time.monotonic', side_effect=[0, 2, 3, 5]):
            with self.assertRaises(DrainError):
                drain_session(proc, 1)
        self.assertEqual([x.args[3] for x in send.call_args_list], [signal.SIGTERM, signal.SIGKILL])

    def test_success_verifies_empty_session_and_reaps(self):
        proc = MagicMock(spec=subprocess.Popen); proc.pid = 21
        with patch('session_drain._session_members', side_effect=[{22: 100}, {}]), \
             patch('session_drain._signal_captured') as send:
            drain_session(proc, 1)
        send.assert_called_once_with(22, 100, 21, signal.SIGTERM)
        proc.wait.assert_called_once_with(timeout=0)


class ContainedSessionTest(unittest.TestCase):
    def test_setsid_child_cannot_migrate_and_is_drained(self):
        import os
        import tempfile
        import sys
        from session_drain import spawn_contained_session, drain_contained_session
        code = """import os,time
r,w=os.pipe()
pid=os.fork()
if pid==0:
 os.close(r)
 os.setsid()
 try:
  open('/sys/fs/cgroup/cgroup.procs','w').write(str(os.getpid()))
  result=b'ESCAPED'
 except PermissionError:
  result=b'DENIED'
 import ctypes,signal
 class Args(ctypes.Structure):
  _fields_=[(x,ctypes.c_uint64) for x in ('flags','pidfd','child_tid','parent_tid','exit_signal','stack','stack_size','tls','set_tid','set_tid_size','cgroup')]
 libc=ctypes.CDLL(None,use_errno=True)
 fd=os.open('/sys/fs/cgroup',os.O_RDONLY|os.O_DIRECTORY)
 args=Args();args.flags=0x200000000;args.exit_signal=signal.SIGCHLD;args.cgroup=fd
 child=libc.syscall(435,ctypes.byref(args),ctypes.sizeof(args))
 if child==0: os._exit(0)
 if child>0: os.waitpid(child,0)
 if child!=-1 or ctypes.get_errno()!=38: result=b'CLONE_ESCAPE'
 os.close(fd)
 os.write(1,result+b'\\n')
 os.write(w,b'x')
 time.sleep(60)
else:
 os.close(w)
 os.read(r,1)
"""
        process = None
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                process = spawn_contained_session([sys.executable, '-c', code], stdout=out,
                    stderr=err, env=dict(os.environ), cwd='/tmp')
                process.wait(timeout=5)
                out.seek(0)
                self.assertEqual(out.read().strip(), b'DENIED')
                group = process._sr6_cgroup
                self.assertGreaterEqual(len((group / 'cgroup.procs').read_text().splitlines()), 1)
                drain_contained_session(process, grace_seconds=1)
                self.assertFalse(group.exists())
                process = None
            finally:
                if process is not None:
                    drain_contained_session(process, grace_seconds=1)

    def test_rejects_untrusted_output_descriptor(self):
        from session_drain import spawn_contained_session
        with self.assertRaises(DrainError):
            spawn_contained_session(['/bin/true'], stdout=1, stderr=subprocess.DEVNULL,
                                    env={}, cwd='/tmp')


if __name__ == '__main__':
    unittest.main()
