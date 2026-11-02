#!/usr/bin/env python3
"""Linux captured-session cleanup for a future SR-6 launcher.

Only PIDs captured from the newly created session are signalled, via pidfds.
This does not establish cgroup containment: a child that changes session before
inspection can escape. A launcher must independently rule out that behavior and
prove grant, identity, deadline and residency before this is a runnable row.
"""
import os
from pathlib import Path
import select
import signal
import subprocess
import time


class DrainError(RuntimeError):
    pass


def _stat(pid):
    raw = Path(f'/proc/{pid}/stat').read_text()
    fields = raw[raw.rindex(')') + 2:].split()
    return fields[0], int(fields[3]), int(fields[19])  # state, session, starttime


def _session_members(session):
    result = {}
    try:
        for path in Path('/proc').iterdir():
            if not path.name.isdigit():
                continue
            pid = int(path.name)
            try:
                state, sid, birth = _stat(pid)
            except FileNotFoundError:
                continue
            if sid == session and state != 'Z':
                result[pid] = birth
    except (OSError, IndexError, ValueError) as exc:
        raise DrainError('cannot inspect process session') from exc
    return result


def _signal_captured(pid, birth, session, sig):
    """Bind an inspected PID to a pidfd and revalidate before signalling."""
    fd = None
    try:
        fd = os.pidfd_open(pid)
        state, sid, actual_birth = _stat(pid)
        if state == 'Z':
            return
        if sid != session or actual_birth != birth:
            raise DrainError('captured process identity changed')
        signal.pidfd_send_signal(fd, sig)
    except ProcessLookupError:
        return
    except (OSError, IndexError, ValueError) as exc:
        raise DrainError('cannot signal captured session member') from exc
    finally:
        if fd is not None:
            os.close(fd)


def spawn_session(argv, *, stdout, stderr, env, cwd):
    """Spawn one owned child as a session leader; never use a shell."""
    if (not isinstance(argv, list) or not argv or
            any(not isinstance(a, str) or not a for a in argv) or
            not isinstance(env, dict) or not isinstance(cwd, str)):
        raise ValueError('explicit argv, environment and cwd required')
    return subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                            env=env, cwd=cwd, start_new_session=True, close_fds=True)


def drain_session(process, grace_seconds=10):
    """TERM then KILL captured session members, and refuse an undrained session.

    process must be the actual Popen from spawn_session, with PID equal to its
    session ID. This scoped proof does not cover processes that escaped session.
    """
    if not isinstance(process, subprocess.Popen) or type(process.pid) is not int or process.pid <= 0:
        raise DrainError('captured child handle required')
    if type(grace_seconds) not in (int, float) or not 0 < grace_seconds <= 60:
        raise DrainError('invalid cleanup timeout')
    session = process.pid
    for sig in (signal.SIGTERM, signal.SIGKILL):
        members = _session_members(session)
        for pid, birth in members.items():
            _signal_captured(pid, birth, session, sig)
        deadline = time.monotonic() + grace_seconds
        while True:
            process.poll()  # reap the owned leader when it exits
            if not _session_members(session):
                process.wait(timeout=0)
                return
            if time.monotonic() >= deadline:
                break
            # A bounded child wait avoids host-wide name-based signalling.
            try:
                process.wait(timeout=min(0.05, max(0.001, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                pass
            else:
                # A reaped leader may have live children; avoid a busy loop.
                select.select([], [], [], min(0.05, max(0, deadline - time.monotonic())))
    raise DrainError('session still contains live processes after KILL')
