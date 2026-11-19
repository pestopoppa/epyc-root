#!/usr/bin/env python3
"""Own-child counterexample: a grandchild can outlive parent-death kills."""
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys


def prctl(option, value=0):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(option, value, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'prctl')


def birth(pid):
    try:
        return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])
    except FileNotFoundError:
        return None


def kill_exact(pid, ticks):
    fd = os.pidfd_open(pid)
    try:
        if birth(pid) != ticks:
            raise RuntimeError('captured PID identity changed')
        try:
            signal.pidfd_send_signal(fd, signal.SIGKILL)
        except ProcessLookupError:
            pass
    finally:
        os.close(fd)


def outer(fd):
    parent = os.getpid()
    direct = os.fork()
    if direct:
        signal.pause()
        os._exit(90)
    prctl(1, signal.SIGKILL)  # PR_SET_PDEATHSIG
    if os.getppid() != parent:
        os._exit(91)
    grandchild = os.fork()
    if not grandchild:
        # Linux does not inherit PR_SET_PDEATHSIG over fork.
        os.write(fd, (json.dumps({'direct': os.getppid(), 'grandchild': os.getpid()}) + '\n').encode())
        os.close(fd)
        signal.pause()
        os._exit(92)
    os.close(fd)
    signal.pause()
    os._exit(93)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--outer':
        outer(int(sys.argv[2])); return
    prctl(36, 1)  # PR_SET_CHILD_SUBREAPER
    read_fd, write_fd = os.pipe()
    proc = subprocess.Popen([sys.executable, '-B', __file__, '--outer', str(write_fd)], pass_fds=(write_fd,))
    os.close(write_fd)
    captured = {}
    try:
        with os.fdopen(read_fd) as stream:
            rec = json.loads(stream.readline())
        for pid in (proc.pid, rec['direct'], rec['grandchild']):
            ticks = birth(pid)
            if ticks is None:
                raise RuntimeError('missing captured birth')
            captured[pid] = ticks
        kill_exact(proc.pid, captured[proc.pid])
        proc.wait(timeout=5)
        # Waiting for the direct child proves its PDEATHSIG was delivered.
        got, status = os.waitpid(rec['direct'], 0)
        if got != rec['direct'] or not os.WIFSIGNALED(status):
            raise RuntimeError('direct child did not terminate by signal')
        if birth(rec['grandchild']) != captured[rec['grandchild']]:
            raise RuntimeError('grandchild did not survive as the same process')
        kill_exact(rec['grandchild'], captured[rec['grandchild']])
        got, _ = os.waitpid(rec['grandchild'], 0)
        if got != rec['grandchild'] or birth(rec['grandchild']) is not None:
            raise RuntimeError('grandchild cleanup unverified')
        for pid in captured:
            ps = subprocess.run(['/usr/bin/ps', '-p', str(pid), '-o', 'pid='],
                                capture_output=True, text=True, timeout=3)
            if ps.returncode != 1 or ps.stdout.strip() or birth(pid) is not None:
                raise RuntimeError('captured PID not verified absent')
        print('nested grandchild survived parent-death kill; captured processes reaped')
    finally:
        for pid, ticks in captured.items():
            if birth(pid) == ticks:
                kill_exact(pid, ticks)
        while True:
            try:
                os.waitpid(-1, 0)
            except ChildProcessError:
                break


if __name__ == '__main__':
    main()
