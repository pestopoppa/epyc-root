"""Isolated subreaper owns every PID signaled in this synthetic fixture."""
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
libc = ctypes.CDLL(None, use_errno=True)
if libc.prctl(36, 1, 0, 0, 0):
    raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER')

def alarm(_sig, _frame):
    raise TimeoutError('subprocess containment did not complete')

signal.signal(signal.SIGALRM, alarm)
signal.alarm(8)
owned = set()
try:
    with tempfile.TemporaryDirectory() as directory:
        proc = subprocess.Popen([sys.executable, '-B', str(HERE / 'outer.py')],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        owned.add(proc.pid)
        config = {'argv': [sys.executable, '-c', 'import time; time.sleep(30)'],
                  'directory': directory, 'window': 'full-a', 'run_id': 'pdeath',
                  'timeout_s': 30}
        proc.stdin.write(json.dumps(config) + '\n'); proc.stdin.flush()
        outer = json.loads(proc.stdout.readline())
        inner = json.loads(proc.stdout.readline())
        if outer.get('event') != 'supervisor-started' or inner.get('event') != 'started':
            raise RuntimeError('missing owned process receipt')
        child_pids = {outer['pid'], inner['pid']}
        owned.update(child_pids)
        os.kill(proc.pid, signal.SIGKILL)
        if proc.wait() != -signal.SIGKILL:
            raise RuntimeError('outer not terminated by requested signal')
        owned.remove(proc.pid)
        reaped = set()
        while len(reaped) < len(child_pids):
            pid, status = os.waitpid(-1, 0)
            if pid not in child_pids or not os.WIFSIGNALED(status):
                raise RuntimeError('unexpected adopted child or status')
            reaped.add(pid); owned.remove(pid)
        if reaped != child_pids:
            raise RuntimeError('captured PIDs not reaped')
        print('captured children reaped')
finally:
    signal.alarm(0)
    for pid in owned:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
    for pid in owned:
        try: os.waitpid(pid, 0)
        except ChildProcessError: pass
