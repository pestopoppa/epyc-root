#!/usr/bin/env python3
"""Independent owner-loss guard for one freshly created M4 cgroup.

The watcher must remain outside the cgroup, poll the returned guardian pidfd,
abort and drain on guardian death, and disarm only after its own drain. The
launcher must keep its region claim until both watcher and guardian exit. This
module does not launch or admit workloads.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import select
import subprocess
import sys
import time

CGROUP_ROOT = Path('/sys/fs/cgroup')


def birth(pid: int) -> int:
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()[19])


def _pin_process(pid: int, expected_birth: int) -> int:
    if pid <= 1 or birth(pid) != expected_birth:
        raise RuntimeError('owner identity mismatch')
    fd = os.pidfd_open(pid)
    try:
        if birth(pid) != expected_birth or select.select([fd], [], [], 0)[0]:
            raise RuntimeError('owner identity changed')
    except BaseException:
        os.close(fd)
        raise
    return fd


def _cgroup(path: Path) -> Path:
    root = CGROUP_ROOT.resolve(strict=True)
    if path.is_symlink():
        raise RuntimeError('cgroup symlink forbidden')
    path = path.resolve(strict=True)
    if path.parent != root or not path.name.startswith('m4-private-'):
        raise RuntimeError('not a fresh M4 cgroup')
    if not (path / 'cgroup.kill').is_file() or not (path / 'cgroup.events').is_file():
        raise RuntimeError('cgroup v2 kill and events required')
    return path


def _empty(path: Path) -> bool:
    if not path.exists():
        return True
    fields = dict(line.split() for line in (path / 'cgroup.events').read_text().splitlines())
    if fields.get('populated') not in ('0', '1'):
        raise RuntimeError('unreadable cgroup population')
    return fields['populated'] == '0'


def drain(path: Path, deadline_s: float = 10) -> None:
    if not path.exists():
        return
    (path / 'cgroup.kill').write_text('1')
    deadline = time.monotonic() + deadline_s
    while not _empty(path):
        if time.monotonic() >= deadline:
            raise RuntimeError('owned cgroup failed to drain')
        time.sleep(0.02)


def guard(cgroup: Path, watcher: int, watcher_birth: int, owner: int, owner_birth: int,
          ready_fd: int, done_fd: int) -> int:
    path = _cgroup(cgroup)
    watcher_fd = _pin_process(watcher, watcher_birth)
    try:
        owner_fd = _pin_process(owner, owner_birth)
    except BaseException:
        os.close(watcher_fd)
        raise
    try:
        os.write(ready_fd, b'R')
        os.close(ready_fd)
        ready_fd = -1
        while True:
            events = select.select([watcher_fd, owner_fd, done_fd], [], [], 0.2)[0]
            if watcher_fd in events or owner_fd in events:
                drain(path)
                return 0
            if done_fd in events:
                # EOF is watcher loss, never a success signal.
                command = os.read(done_fd, 1)
                if command == b'D' and _empty(path):
                    return 0
                drain(path)
                return 0 if command != b'D' else 2
    finally:
        if ready_fd >= 0:
            os.close(ready_fd)
        os.close(done_fd)
        os.close(watcher_fd)
        os.close(owner_fd)


def start(cgroup: Path, owner_pid: int, owner_birth: int) -> tuple[subprocess.Popen, int, int]:
    """Start a separately surviving guard; returns (process, pidfd, done pipe)."""
    ready_r, ready_w = os.pipe2(os.O_CLOEXEC)
    done_r, done_w = os.pipe2(os.O_CLOEXEC)
    proc = None
    try:
        watcher_pid = os.getpid()
        proc = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
            '--cgroup', str(cgroup), '--watcher', str(watcher_pid), '--watcher-birth', str(birth(watcher_pid)),
            '--owner', str(owner_pid), '--owner-birth', str(owner_birth),
            '--ready-fd', str(ready_w), '--done-fd', str(done_r)],
            pass_fds=(ready_w, done_r), start_new_session=True)
        os.close(ready_w); ready_w = -1
        os.close(done_r); done_r = -1
        fd = os.pidfd_open(proc.pid)
        readable = select.select([ready_r, fd], [], [], 5)[0]
        if ready_r not in readable or os.read(ready_r, 1) != b'R':
            os.close(fd)
            raise RuntimeError('guardian did not attest readiness')
        if select.select([fd], [], [], 0)[0]:
            os.close(fd)
            raise RuntimeError('guardian exited before readiness')
        return proc, fd, done_w
    except BaseException:
        if done_w >= 0:
            os.close(done_w); done_w = -1
        if proc is not None:
            proc.wait(timeout=10)
        raise
    finally:
        for fd in (ready_r, ready_w, done_r):
            if fd >= 0:
                os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cgroup', type=Path, required=True)
    for arg in ('watcher', 'watcher-birth', 'owner', 'owner-birth', 'ready-fd', 'done-fd'):
        parser.add_argument('--' + arg, type=int, required=True)
    a = parser.parse_args()
    try:
        return guard(a.cgroup, a.watcher, a.watcher_birth, a.owner, a.owner_birth, a.ready_fd, a.done_fd)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'M4 guardian refused: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
