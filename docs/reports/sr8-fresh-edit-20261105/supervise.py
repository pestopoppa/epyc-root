#!/usr/bin/env python3
"""Run a build command with active STOP and verified descendant draining (Linux)."""
import ctypes
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

requested = False


def request_stop(_signum, _frame):
    global requested
    requested = True


def parent_of(pid):
    try:
        stat = Path(f'/proc/{pid}/stat').read_text()
        return int(stat[stat.rfind(')') + 2:].split()[1])
    except (FileNotFoundError, ProcessLookupError):
        return None


def children_of(parents):
    return {int(p.name) for p in Path('/proc').iterdir()
            if p.name.isdigit() and parent_of(int(p.name)) in parents}


def freeze_tree():
    """Freeze each captured process and rescan, including reparented orphans."""
    captured = {}
    while True:
        pending = children_of({os.getpid()} | set(captured)) - set(captured)
        if not pending:
            return captured
        for pid in pending:
            try:
                fd = os.pidfd_open(pid)
            except ProcessLookupError:
                continue
            # A PID can be recycled after the scan; never signal an unrelated
            # process. The pidfd then pins the checked process identity.
            if parent_of(pid) not in ({os.getpid()} | set(captured)):
                os.close(fd)
                continue
            try:
                signal.pidfd_send_signal(fd, signal.SIGSTOP)
            except ProcessLookupError:
                os.close(fd)
                continue
            captured[pid] = fd


def drain(proc):
    """Kill only captured descendants and require every pidfd to signal exit."""
    captured = freeze_tree()
    try:
        for fd in captured.values():
            try:
                signal.pidfd_send_signal(fd, signal.SIGKILL)
            except ProcessLookupError:
                pass
        poller = select.poll()
        for fd in captured.values():
            poller.register(fd, select.POLLIN)
        remaining = set(captured.values())
        end = time.monotonic() + 5
        while remaining and time.monotonic() < end:
            remaining -= {fd for fd, _ in poller.poll(max(0, int((end - time.monotonic()) * 1000)))}
        if remaining:
            raise RuntimeError('descendant drain timed out')
        if proc is not None:
            proc.wait(timeout=1)
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if not pid:
                raise RuntimeError('unreaped descendant after drain')
        if children_of({os.getpid()}):
            raise RuntimeError('descendant appeared after drain')
    finally:
        for fd in captured.values():
            os.close(fd)


def main(argv):
    global requested
    if len(argv) < 3 or not argv[1].isdigit():
        return 64
    stop, deadline, *command = argv
    # The supervisor owns only its command tree; adopted orphans become ours.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, request_stop)
    def stopped():
        return requested or Path(stop).exists() or time.time() >= int(deadline)
    if stopped():
        return 75
    proc = subprocess.Popen(command)
    while True:
        if stopped():
            drain(proc)
            return 75
        rc = proc.poll()
        if rc is not None:
            # Also handle a STOP arriving at the exit boundary and prevent
            # successful completion while a child has left background work.
            stopped_at_exit = stopped()
            leftovers = bool(children_of({os.getpid()}))
            if leftovers:
                drain(proc)
            if stopped_at_exit:
                return 75
            return 75 if leftovers and rc == 0 else rc
        time.sleep(0.05)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
