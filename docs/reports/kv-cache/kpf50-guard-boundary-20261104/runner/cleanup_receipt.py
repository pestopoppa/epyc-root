"""Prospective same-process KPF-50 cleanup proof; not wired to the runner.

Create Guard in an isolated single-threaded subreaper before spawning anything.
Register each adopted direct child before reaping it through Guard.reap().
No conclusion about scientific validity or a different process follows.
"""
import ctypes
import errno
import json
import os
from pathlib import Path
import re
import stat
import threading
import uuid

SAFE = re.compile(r'[A-Za-z0-9_.-]{1,128}\Z')
ORDER = ('full-a', 'mask-a', 'mask-b', 'full-b')


def birth(pid):
    try:
        return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])
    except FileNotFoundError:
        return None


def children():
    return {int(x) for x in Path(f'/proc/self/task/{os.getpid()}/children').read_text().split()}


def is_subreaper():
    value = ctypes.c_int()
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(37, ctypes.byref(value), 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_GET_CHILD_SUBREAPER')
    return value.value == 1


def one_thread():
    if len(list(Path('/proc/self/task').iterdir())) != 1 or threading.current_thread() is not threading.main_thread():
        raise RuntimeError('cleanup supervisor must be single threaded')


class Guard:
    def __init__(self):
        one_thread()
        if not is_subreaper() or children():
            raise RuntimeError('must begin as a child-free subreaper before spawn')
        self.owner = os.getpid()
        self.owner_birth = birth(self.owner)
        self.captured = {}
        self.closed = False

    def _owner(self):
        one_thread()
        if self.closed or os.getpid() != self.owner or birth(self.owner) != self.owner_birth or not is_subreaper():
            raise RuntimeError('supervisor identity or subreaper changed')

    def capture(self, pid, expected_birth):
        self._owner()
        if type(pid) is not int or pid <= 0 or type(expected_birth) is not int or expected_birth <= 0:
            raise ValueError('invalid captured identity')
        if pid in self.captured or pid not in children() or birth(pid) != expected_birth:
            raise ValueError('child absent, duplicated or birth changed')
        self.captured[pid] = {'pid': pid, 'birth_ticks': expected_birth, 'reaped': False}

    def reap(self, pid):
        self._owner()
        item = self.captured.get(pid)
        if item is None or item['reaped'] or birth(pid) != item['birth_ticks']:
            raise ValueError('child was not captured or its identity changed')
        try:
            got, status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError as exc:
            raise RuntimeError('captured child was reaped outside supervisor') from exc
        if got != pid:
            raise RuntimeError('captured child has not exited')
        if birth(pid) is not None:
            raise RuntimeError('captured PID remains present or was reused')
        item['reaped'] = True
        item['wait_status'] = status

    def publish(self, directory, window, run_id):
        self._owner()
        if window not in ORDER or not isinstance(run_id, str) or not SAFE.fullmatch(run_id) or run_id in ('.', '..'):
            raise ValueError('invalid window or lineage')
        if not self.captured or any(not v['reaped'] or birth(pid) is not None for pid, v in self.captured.items()):
            raise RuntimeError('captured children are incomplete or PID reused')
        if children():
            raise RuntimeError('unregistered or surviving child exists')
        try:
            os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            pass
        else:
            raise RuntimeError('ECHILD not established')
        # Direct ECHILD + child-free verified subreaper is the survivor check;
        # captured PID/births bind the actual children we reaped. These facts
        # cannot establish GPU residency or semantic/scientific correctness.
        payload = {'schema': 'kpf50.cleanup.v1', 'window': window, 'run_id': run_id,
                   'verified_dead': True, 'remaining_children': 0,
                   'supervisor': {'pid': self.owner, 'birth_ticks': self.owner_birth, 'subreaper': True},
                   'captured': list(self.captured.values()), 'echild': True}
        dfd = os.open(Path(directory), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        name = f'{window}.cleanup.json'
        temp = '.cleanup-' + uuid.uuid4().hex
        made = False
        try:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
            made = True
            try:
                data = memoryview((json.dumps(payload, sort_keys=True) + '\n').encode())
                while data:
                    n = os.write(fd, data)
                    if n <= 0:
                        raise OSError('short write')
                    data = data[n:]
                os.fsync(fd)
            finally:
                os.close(fd)
            os.link(temp, name, src_dir_fd=dfd, dst_dir_fd=dfd, follow_symlinks=False)
            os.fsync(dfd)
            self.closed = True
            return payload
        finally:
            if made:
                try:
                    os.unlink(temp, dir_fd=dfd)
                    os.fsync(dfd)
                except FileNotFoundError:
                    pass
            os.close(dfd)
