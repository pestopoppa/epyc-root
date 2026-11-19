#!/usr/bin/env python3
"""Run a build command with active STOP and verified descendant draining (Linux)."""
import ctypes
import json
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


def stop_reason(stop, deadline):
    if requested:
        return 'signal'
    if Path(stop).exists():
        return 'stop-file'
    if time.time() >= deadline:
        return 'deadline'
    return None


def supervise(command, stop, deadline, report):
    """Record the refusal cause before draining; never turn leftovers into success."""
    def finish(reason, rc, child_rc=None, leftovers=()):
        record = dict(schema='epyc.cafe3.supervisor.v1', reason=reason, rc=rc,
                      child_rc=child_rc, captured_children=sorted(leftovers),
                      command=command, deadline=deadline, at=time.time(),
                      drain='pending' if leftovers else 'not-required')
        def save():
            with report.open('w') as stream:
                json.dump(record, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
        save()
        if leftovers:
            try:
                drain(proc)
            except Exception as error:
                record.update(drain='failed', error=str(error))
                save()
                raise
            record['drain'] = 'complete'
            save()
        print('CAFE3 SUPERVISOR: ' + json.dumps(record), flush=True)
        return rc

    reason = stop_reason(stop, deadline)
    if reason:
        return finish(reason, 75)
    proc = subprocess.Popen(command)
    while True:
        reason = stop_reason(stop, deadline)
        if reason:
            return finish(reason, 75, proc.poll(), children_of({os.getpid()}))
        rc = proc.poll()
        if rc is not None:
            reason = stop_reason(stop, deadline)
            leftovers = children_of({os.getpid()})
            return finish(reason or ('leftover-descendants' if leftovers else 'command-exit'),
                          75 if reason or (leftovers and rc == 0) else rc,
                          rc, leftovers)
        time.sleep(0.05)


def main(argv):
    global requested
    requested = False
    if len(argv) < 4 or not argv[1].isdigit():
        return 64
    stop, deadline, report, *command = argv
    if not command:
        return 64
    # The supervisor owns only its command tree; adopted orphans become ours.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, request_stop)
    return supervise(command, stop, int(deadline), Path(report))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
