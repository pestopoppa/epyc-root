import ctypes
import signal
import os
import subprocess
import sys
import unittest
from unittest.mock import patch
import parent_death


class Tests(unittest.TestCase):
    def test_kernel_accepts_parent_death_setting(self):
        code = "import ctypes,os,signal,parent_death; parent_death.contain(os.getppid()); v=ctypes.c_int(); assert ctypes.CDLL(None).prctl(2,ctypes.byref(v),0,0,0)==0 and v.value==signal.SIGKILL"
        subprocess.run([sys.executable, '-B', '-c', code], check=True, timeout=5)

    def test_wrapper_executes_benign_child_in_place(self):
        p = subprocess.run([sys.executable, '-B', 'pdeath_exec.py', str(os.getpid()), sys.executable, '-B', '-c', 'print("child-ok")'], capture_output=True, text=True, timeout=5, check=True)
        self.assertEqual(p.stdout.strip(), 'child-ok')

    def test_wrapper_refuses_wrong_parent(self):
        p = subprocess.run([sys.executable, '-B', 'pdeath_exec.py', '1', sys.executable, '-B', '-c', 'print("must-not-run")'], capture_output=True, text=True, timeout=5)
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn('must-not-run', p.stdout)

    def test_installs_kernel_guard(self):
        with patch.object(ctypes, 'CDLL') as lib, patch.object(parent_death.os, 'getppid', return_value=9):
            lib.return_value.prctl.return_value = 0
            parent_death.contain(9)
            lib.return_value.prctl.assert_called_once_with(parent_death.PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0)

    def test_refuses_missing_parent(self):
        with patch.object(ctypes, 'CDLL') as lib, patch.object(parent_death.os, 'getppid', return_value=1):
            lib.return_value.prctl.return_value = 0
            with self.assertRaises(RuntimeError):
                parent_death.contain(9)

    def test_refuses_prctl_failure(self):
        with patch.object(ctypes, 'CDLL') as lib:
            lib.return_value.prctl.return_value = -1
            with self.assertRaises(OSError):
                parent_death.contain(9)

if __name__ == '__main__':
    unittest.main()
