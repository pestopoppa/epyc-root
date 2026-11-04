"""Own-child, private-cgroup membership escape control; no shared-group writes."""
import os
from pathlib import Path
import select
import subprocess
import sys
import unittest
import uuid

ROOT = Path('/sys/fs/cgroup')
CHILD = r'''
import os, sys
from pathlib import Path
src,dst=sys.argv[1:]
Path(src, 'cgroup.procs').write_text(str(os.getpid()))
print('READY',flush=True)
if sys.stdin.readline() != 'MOVE\n': raise SystemExit(2)
Path(dst, 'cgroup.procs').write_text(str(os.getpid()))
print('MOVED',flush=True)
if sys.stdin.readline() != 'EXIT\n': raise SystemExit(3)
'''

class PrivateEscape(unittest.TestCase):
    def line(self, proc):
        ready,_,_=select.select([proc.stdout],[],[],5)
        self.assertTrue(ready, 'owned child did not reply')
        return proc.stdout.readline().strip()

    def test_owned_child_moves_between_private_siblings(self):
        group=ROOT/('kpf50-test-escape-'+uuid.uuid4().hex)
        left=group/'left'; right=group/'right'; proc=None
        try:
            group.mkdir(); left.mkdir(); right.mkdir()
            proc=subprocess.Popen([sys.executable,'-c',CHILD,str(left),str(right)],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertEqual(self.line(proc),'READY')
            self.assertIn(str(proc.pid),(left/'cgroup.procs').read_text().split())
            proc.stdin.write('MOVE\n');proc.stdin.flush()
            self.assertEqual(self.line(proc),'MOVED')
            self.assertNotIn(str(proc.pid),(left/'cgroup.procs').read_text().split())
            self.assertIn(str(proc.pid),(right/'cgroup.procs').read_text().split())
            proc.stdin.write('EXIT\n');proc.stdin.flush()
            self.assertEqual(proc.wait(timeout=5),0)
        finally:
            if proc is not None:
                if proc.poll() is None:
                    proc.kill();proc.wait(timeout=5)
                for stream in (proc.stdin,proc.stdout,proc.stderr):
                    if stream:stream.close()
            for p in (right,left,group):
                if p.exists():p.rmdir()

if __name__=='__main__': unittest.main()
