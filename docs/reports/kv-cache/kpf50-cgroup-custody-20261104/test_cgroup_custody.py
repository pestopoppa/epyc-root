import ctypes
import os
import select
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cgroup_custody import birth, captured_members


class CgroupCustody(unittest.TestCase):
    def test_owned_fork_membership(self):
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(36, 1, 0, 0, 0):
            self.skipTest('subreaper unavailable')
        try:
            group = Path(tempfile.mkdtemp(prefix='kpf50-test-', dir='/sys/fs/cgroup'))
        except OSError as exc:
            self.skipTest('private cgroup unavailable: ' + str(exc))
        read_fd, write_fd = os.pipe()
        script = '''import os,sys
group,gate=sys.argv[1],int(sys.argv[2])
open(group+"/cgroup.procs","w").write(str(os.getpid()))
child=os.fork()
if child==0:
 os.read(gate,1); os._exit(0)
print(child,flush=True)
os.read(gate,1)
os.waitpid(child,0)
'''
        proc = None
        captured = {}
        try:
            proc = subprocess.Popen([sys.executable, '-c', script, str(group), str(read_fd)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=(read_fd,))
            os.close(read_fd); read_fd = -1
            ready, _, _ = select.select([proc.stdout], [], [], 3)
            self.assertTrue(ready, 'owned child did not report')
            child = int(proc.stdout.readline())
            captured = captured_members(group)
            self.assertEqual(set(captured), {proc.pid, child})
            self.assertTrue(all(birth(pid) == entry[0] for pid, entry in captured.items()))
            os.close(write_fd); write_fd = -1
            self.assertEqual(proc.wait(timeout=3), 0)
            self.assertEqual((group / 'cgroup.procs').read_text().strip(), '')
        finally:
            if write_fd != -1: os.close(write_fd)
            if read_fd != -1: os.close(read_fd)
            if proc is not None:
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Signal only the owned PID whose pidfd and birth were captured.
                    if proc.pid in captured and birth(proc.pid) == captured[proc.pid][0]:
                        import signal
                        signal.pidfd_send_signal(captured[proc.pid][1], signal.SIGKILL)
                        proc.wait(timeout=3)
                proc.stdout.close()
                proc.stderr.close()
            for _, fd in captured.values(): os.close(fd)
            os.rmdir(group)


if __name__ == '__main__': unittest.main()
