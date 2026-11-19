import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent

class Integration(unittest.TestCase):
    def test_real_subreaper_nested_child_and_unfinished_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            code = r'''
import ctypes, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from cleanup_receipt import Guard, birth
root = Path(sys.argv[2]); libc = ctypes.CDLL(None)
assert libc.prctl(36,1,0,0,0) == 0
g = Guard()
rd, wr = os.pipe(); ready_r, ready_w = os.pipe()
pid = os.fork()
if pid == 0:
    os.close(ready_r)
    grandchild = os.fork()
    if grandchild == 0:
        os.close(wr); os.write(ready_w, str(os.getpid()).encode()+b'\n'); os.close(ready_w)
        os.read(rd, 1); os._exit(0)
    os.close(ready_w); os._exit(0)
os.close(ready_w); os.close(rd)
grandchild = int(os.read(ready_r, 128)); os.close(ready_r)
g.capture(pid, birth(pid))
os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
g.reap(pid)
g.capture(grandchild, birth(grandchild))
try:
    g.publish(root, 'full-a', 'lin1')
    raise AssertionError('live adopted child accepted')
except RuntimeError:
    assert not (root/'full-a.cleanup.json').exists()
os.write(wr,b'x'); os.close(wr)
os.waitid(os.P_PID, grandchild, os.WEXITED | os.WNOWAIT)
g.reap(grandchild)
result = g.publish(root, 'full-a', 'lin1')
assert result['echild'] and result['remaining_children'] == 0 and len(result['captured']) == 2
assert all(x['reaped'] and x['birth_ticks'] > 0 for x in result['captured'])
'''
            p = subprocess.run([sys.executable, '-B', '-c', code, str(HERE), d], capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 0, p.stderr)

    def test_refuses_non_subreaper_in_separate_process(self):
        code = 'import sys;sys.path.insert(0,sys.argv[1]);from cleanup_receipt import Guard;Guard()'
        p = subprocess.run([sys.executable, '-B', '-c', code, str(HERE)], capture_output=True, text=True, timeout=10)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('subreaper', p.stderr)

if __name__ == '__main__': unittest.main()
