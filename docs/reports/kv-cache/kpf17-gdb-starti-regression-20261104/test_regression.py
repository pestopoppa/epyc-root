#!/usr/bin/env python3
"""Model-free GDB fork-before-receipt + subreaper cleanup regression."""
import ctypes, os, signal, subprocess, time, unittest
from pathlib import Path
D = Path(__file__).resolve().parent
PR_SET_CHILD_SUBREAPER = 36
PR_GET_CHILD_SUBREAPER = 37
libc = ctypes.CDLL(None, use_errno=True)
def set_subreaper():
    if libc.prctl(ctypes.c_int(PR_SET_CHILD_SUBREAPER), ctypes.c_ulong(1),0,0,0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER')
    value=ctypes.c_int()
    if libc.prctl(ctypes.c_int(PR_GET_CHILD_SUBREAPER), ctypes.byref(value),0,0,0) != 0 or value.value != 1:
        raise RuntimeError('subreaper status not verified')
def birth(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
def direct_children(pid):
    found=set()
    for task in Path(f'/proc/{pid}/task').iterdir():
        try: found.update(int(x) for x in (task/'children').read_text().split())
        except FileNotFoundError: pass
    return found
def wait_until(fn, timeout=5):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        x=fn()
        if x: return x
        time.sleep(.01)
    return None
def signal_captured(pid, ticks, fd, sig):
    if birth(pid) != ticks: raise AssertionError('captured PID birth mismatch')
    signal.pidfd_send_signal(fd, sig)

def kill_gdb_before_receipt(proc, pid, ticks, fd):
    # Hold the supervisor-owned debugger stopped at the test pause, then force
    # the bounded escalation path so the traced child must be adopted or die.
    signal_captured(pid,ticks,fd,signal.SIGSTOP)
    if birth(pid) != ticks: raise AssertionError('GDB PID reused before escalation')
    signal_captured(pid,ticks,fd,signal.SIGKILL)
    proc.wait(timeout=2)
    if Path(f'/proc/{pid}').exists(): raise AssertionError('GDB remains after wait/reap')

def kill_adopted(pid, ticks, fd, timeout=1):
    signal_captured(pid,ticks,fd,signal.SIGTERM)
    try: status=reap_one(pid,timeout)
    except AssertionError:
        if birth(pid) != ticks: raise AssertionError('adopted PID reused before escalation')
        signal_captured(pid,ticks,fd,signal.SIGKILL)
        status=reap_one(pid,2)
    if Path(f'/proc/{pid}').exists(): raise AssertionError('adopted process remains after reap')
    return status
def reap_one(pid, timeout=3):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            got,status=os.waitpid(pid,os.WNOHANG)
            if got==pid:return status
        except ChildProcessError:
            if not Path(f'/proc/{pid}').exists(): return 0
            raise
        time.sleep(.01)
    raise AssertionError('adopted child not reaped by bound')
class StartiCleanup(unittest.TestCase):
    def test_stop_after_fork_before_starti_pid_receipt(self):
        set_subreaper()
        for name in ('STOP','release','receipt.json','held-before-receipt.json','pidfile','COMPLETE','gdb.log'):
            try:(D/name).unlink()
            except FileNotFoundError:pass
        env=dict(os.environ,KPF17_TEST_ROOT=str(D),KPF17_TEST_PIDFILE=str(D/'pidfile'))
        argv=['/usr/bin/gdb','--batch','-nx','-ex','set confirm off',
              '-ex','set startup-with-shell off','-ex',f'source {D}/gdb_hook.py',
              '-ex','starti','-ex','python hold_before_receipt()',
              '-ex','python capture_starti()','-ex','continue','-ex','quit',
              '--args','/usr/bin/sleep','30']
        with (D/'gdb.log').open('wb') as log:
            proc=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
            gdb_pid=proc.pid; gdb_birth=birth(gdb_pid); gdb_fd=os.pidfd_open(gdb_pid)
            child_fd=None
            try:
                self.assertIsNotNone(wait_until(lambda:(D/'held-before-receipt.json').exists()),
                                     'GDB never reached held post-starti/pre-receipt point')
                child=wait_until(lambda: next(iter(direct_children(gdb_pid)),None))
                self.assertIsNotNone(child,'inferior was not visible as GDB child')
                child_birth=birth(child); child_fd=os.pidfd_open(child)
                self.assertFalse((D/'receipt.json').exists())
                self.assertFalse((D/'pidfile').exists())
                # Stop now: GDB has forked/started and stopped the inferior, but has no PID receipt.
                (D/'STOP').write_text('STOP\n')
                kill_gdb_before_receipt(proc,gdb_pid,gdb_birth,gdb_fd)
                adopted=wait_until(lambda: child if child in direct_children(os.getpid()) else None)
                self.assertEqual(adopted,child,'inferior was not adopted by the verified subreaper')
                self.assertEqual(birth(child),child_birth)
                # Capture already owns a pidfd and birth before any signal.
                kill_adopted(child,child_birth,child_fd)
                self.assertFalse((D/'receipt.json').exists(),'no starti receipt may be fabricated')
                self.assertFalse((D/'pidfile').exists(),'no PID receipt may be fabricated')
                self.assertFalse((D/'COMPLETE').exists(),'interrupted GDB startup must not complete')
                self.assertFalse(direct_children(os.getpid()),'subreaper retained an unaccounted child')
            finally:
                if proc.poll() is None:
                    kill_gdb_before_receipt(proc,gdb_pid,gdb_birth,gdb_fd)
                if child_fd is not None:
                    try:
                        if Path(f'/proc/{child}').exists() and birth(child)==child_birth:
                            kill_adopted(child,child_birth,child_fd,timeout=1)
                        else:
                            try: os.waitpid(child,os.WNOHANG)
                            except ChildProcessError: pass
                    finally: os.close(child_fd)
                os.close(gdb_fd)
                (D/'release').touch()
if __name__=='__main__': unittest.main(verbosity=2)
