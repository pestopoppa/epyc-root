import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import unittest

from contained_supervisor_draft import contained_supervise

HERE = Path(__file__).resolve().parent


class ContainmentTests(unittest.TestCase):
    def test_normal_supervision_uses_same_child_and_reaps(self):
        result = contained_supervise([sys.executable, '-c', 'import sys; sys.stdin.buffer.read(); print("[1]")'],
                                     b'abc', dict(os.environ), stopped=lambda: False, timeout_s=5)
        self.assertEqual((result['status'], result['cleanup'], result['stdout']), ('completed', True, b'[1]\n'))

    def test_relative_executable_refused(self):
        with self.assertRaises(ValueError):
            contained_supervise(['python'], b'', dict(os.environ), stopped=lambda: False, timeout_s=5)

    @unittest.skipUnless(hasattr(os, 'pidfd_open'), 'requires Linux pidfd_open')
    def test_direct_child_dies_when_captured_parent_is_killed(self):
        # Capture the parent's Popen and child's pidfd; never signal a discovered PID.
        parent_code = '''import os, subprocess, sys\nwrapper, python = sys.argv[1:]\ncode = "import os,signal; print('READY', flush=True); signal.pause()"\nc = subprocess.Popen([python, wrapper, str(os.getpid()), python, '-c', code], stdout=subprocess.PIPE, text=True)\nprint(c.pid, flush=True)\nprint(c.stdout.readline().strip(), flush=True)\nc.wait()\n'''
        parent = subprocess.Popen([sys.executable, '-c', parent_code, str(HERE / 'pdeath_exec_draft.py'), sys.executable],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pidfd = None
        try:
            child_pid = int(parent.stdout.readline().strip())
            self.assertEqual(parent.stdout.readline().strip(), 'READY')
            pidfd = os.pidfd_open(child_pid)
            parent.kill()
            parent.wait(timeout=5)
            self.assertTrue(select.select([pidfd], [], [], 5)[0], 'captured child did not exit on parent death')
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=5)
            if pidfd is not None:
                os.close(pidfd)
            parent.stdout.close()
            parent.stderr.close()


if __name__ == '__main__':
    unittest.main()
