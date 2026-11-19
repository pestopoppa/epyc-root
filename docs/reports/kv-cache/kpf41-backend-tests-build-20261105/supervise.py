#!/usr/bin/env python3
"""Cooperatively stop a build tree while retaining its outer grant process group."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

requested = False

def stop_signal(signum, frame):
    global requested
    requested = True


def parent_of(pid):
    try:
        data = Path(f'/proc/{pid}/stat').read_text()
        return int(data[data.rfind(')') + 2:].split()[1])
    except (OSError, ValueError, IndexError):
        return None


def birth_of(pid):
    try:
        data = Path(f'/proc/{pid}/stat').read_text()
        return int(data[data.rfind(')') + 2:].split()[19])
    except (OSError, ValueError, IndexError):
        return None

def descendants(root, root_birth):
    """Freeze captured descendants, then rescan until their tree is closed."""
    captured = {}
    frontier = {root}
    while frontier:
        parents = {}
        for p in Path('/proc').iterdir():
            if p.name.isdigit():
                pid = int(p.name)
                parents[pid] = parent_of(pid)
        todo = list(frontier)
        frontier = set()
        while todo:
            pid = todo.pop()
            if pid in captured:
                continue
            try:
                expected_parent = os.getpid() if pid == root else parents.get(pid)
                birth = birth_of(pid)
                if birth is None or parent_of(pid) != expected_parent or (pid == root and birth != root_birth):
                    continue
                if pid != root and expected_parent not in captured:
                    continue
                fd = os.pidfd_open(pid)
                if birth_of(pid) != birth or parent_of(pid) != expected_parent:
                    os.close(fd)
                    continue
                signal.pidfd_send_signal(fd, signal.SIGSTOP)
            except ProcessLookupError:
                continue
            captured[pid] = fd
            todo.extend(child for child, parent in parents.items() if parent == pid)
        # All captured processes are stopped, so the next scan discovers any
        # children they forked between the prior scan and SIGSTOP.
        for p in Path('/proc').iterdir():
            if p.name.isdigit():
                pid = int(p.name)
                if pid not in captured and parent_of(pid) in captured:
                    frontier.add(pid)
    return list(captured.values())


def send(fds, sig):
    for fd in reversed(fds):
        try:
            signal.pidfd_send_signal(fd, sig)
        except ProcessLookupError:
            pass


def main():
    global requested
    stop, deadline, *command = sys.argv[1:]
    if not command or not deadline.isdigit():
        return 64
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, stop_signal)
    proc = subprocess.Popen(command)
    root_birth = birth_of(proc.pid)
    if root_birth is None:
        return proc.wait()
    while True:
        try:
            return proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            if not (requested or Path(stop).exists() or time.time() >= int(deadline)):
                continue
        fds = descendants(proc.pid, root_birth)
        send(fds, signal.SIGTERM)
        send(fds, signal.SIGCONT)
        # Hold pidfds through the grace interval and kill survivors.
        end = time.monotonic() + 2
        while time.monotonic() < end:
            time.sleep(0.1)
        send(fds, signal.SIGKILL)
        proc.wait()
        for fd in fds:
            os.close(fd)
        return 75


if __name__ == '__main__':
    sys.exit(main())
