#!/usr/bin/env python3
"""Model-free supervision tests with only own harmless child processes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import supervise

SUPERVISOR=Path(supervise.__file__)
FORK='''import os, signal
p=os.fork()
if not p:
 q=os.fork()
 if not q: print("READY",flush=True)
 signal.pause()
signal.pause()
'''
class TestSupervisor(unittest.TestCase):
    def launch(self,root,deadline,code=FORK):
        p=subprocess.Popen([sys.executable,str(SUPERVISOR),str(root/'STOP'),str(deadline),sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.assertEqual(p.stdout.readline().strip(),'READY')
        return p
    def finish(self,p,expected):
        try:
            p.wait(timeout=8)
            self.assertEqual(p.returncode,expected,p.stderr.read())
        finally:
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=12)
            p.stdout.close();p.stderr.close()
    def test_stop_drains_nested_children(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=self.launch(root,int(time.time())+30)
            (root/'STOP').touch();self.finish(p,75)
    def test_deadline_drains_nested_children(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=self.launch(root,int(time.time())+2)
            self.finish(p,75)
    def test_normal_parent_with_survivor_is_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            code='''import os,signal
p=os.fork()
if not p:
 print("READY",flush=True)
 signal.pause()
'''
            p=self.launch(Path(td),int(time.time())+30,code)
            self.finish(p,1)
    def test_stale_birth_never_signalled(self):
        with patch.object(supervise,'children',return_value=[123]),patch.object(supervise,'birth',return_value=88),patch.object(supervise.os,'kill') as kill:
            with self.assertRaisesRegex(RuntimeError,'identity changed'):supervise.kill_owned(123,99)
            kill.assert_not_called()
    def test_pidfd_failure_owned_child_fallback(self):
        supervise.enable_subreaper()
        self.assertEqual(supervise.children(),[])
        p=subprocess.Popen(['/usr/bin/sleep','30']); b=supervise.birth(p.pid)
        try:
            with patch.object(supervise.os,'pidfd_open',side_effect=OSError(24,'injected')):
                self.assertTrue(supervise.drain(p,b))
            self.assertIsNone(supervise.birth(p.pid))
            self.assertEqual(supervise.children(),[])
        finally:
            if p.poll() is None:
                supervise.kill_owned(p.pid,b);p.wait(timeout=5)

if __name__=='__main__':unittest.main()
