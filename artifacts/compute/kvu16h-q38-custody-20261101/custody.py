"""Draft process custody primitive; no server recipe, transport, or rowflow entry.

The caller must supply an approved command, verify executable/library identity, and
handle STOP. A failed readiness check drains the captured child before raising.
"""
from __future__ import annotations

import os
import errno
import signal
import subprocess
from dataclasses import dataclass
from typing import Callable


class CustodyError(RuntimeError):
    pass


def birth(pid: int) -> str:
    # The comm field may contain spaces or parentheses; starttime is field 22.
    data = open(f'/proc/{pid}/stat', encoding='utf-8').read()
    end = data.rfind(')')
    if end < 0:
        raise CustodyError('invalid process stat')
    return data[end + 2:].split()[19]


@dataclass
class Handle:
    process: object
    birth: str
    pidfd: int


class Custodian:
    def __init__(self, popen: Callable = subprocess.Popen, birth_reader: Callable = birth,
                 pidfd_open: Callable = os.pidfd_open, pidfd_signal: Callable = signal.pidfd_send_signal,
                 close: Callable = os.close,
                 reserve_fd: Callable = lambda: os.open(os.devnull, os.O_RDONLY | os.O_CLOEXEC)):
        self._popen = popen
        self._birth = birth_reader
        self._pidfd_open = pidfd_open
        self._pidfd_signal = pidfd_signal
        self._close = close
        self._reserve_fd = reserve_fd

    def start(self, argv: list[str], ready: Callable[[Handle], None], **kwargs) -> Handle:
        if not argv or any(not isinstance(x, str) or not x for x in argv):
            raise CustodyError('nonempty argv required')
        # Caller controls descriptors and environment; never use a shell or a group kill.
        if 'shell' in kwargs or 'preexec_fn' in kwargs:
            raise CustodyError('shell and preexec hooks forbidden')
        # Reserve one descriptor before spawning: EMFILE during pidfd_open can
        # then be retried without resorting to a PID-only signal.
        reserve = self._reserve_fd()
        try:
            proc = self._popen(argv, shell=False, **kwargs)
        except BaseException:
            self._close(reserve)
            raise
        handle = None
        fd = None
        try:
            interrupted = 0
            while True:
                try:
                    fd = self._pidfd_open(proc.pid)
                    break
                except OSError as error:
                    if error.errno == errno.EINTR and interrupted < 3:
                        interrupted += 1
                        continue
                    if error.errno == errno.EMFILE and reserve is not None:
                        self._close(reserve)
                        reserve = None
                        continue
                    raise
            handle = Handle(proc, self._birth(proc.pid), fd)
            if proc.poll() is not None:
                raise CustodyError('child exited during launch')
            ready(handle)
            if proc.poll() is not None or self._birth(proc.pid) != handle.birth:
                raise CustodyError('child identity lost during readiness')
            return handle
        except BaseException as exc:
            # An unreturned child is still ours. Popen's captured PID identifies the
            # child; while poll() is None the PID cannot have been reused as a child.
            try:
                if handle is None:
                    if fd is None:
                        raise CustodyError("pidfd capture failed; cleanup unverified")
                    self._drain_unreturned(proc, fd)
                else:
                    try:
                        cleaned = self.stop(handle)
                    finally:
                        fd = None  # stop always closes its pidfd
                    if not cleaned:
                        raise CustodyError('failed to verify startup cleanup')
            except Exception as cleanup:
                raise CustodyError(f'start failed; cleanup unverified: {cleanup}') from exc
            finally:
                if fd is not None:
                    self._close(fd)
            raise
        finally:
            if reserve is not None:
                self._close(reserve)

    def _drain_unreturned(self, proc: object, fd: int) -> None:
        if proc.poll() is None:
            self._pidfd_signal(fd, signal.SIGTERM)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._pidfd_signal(fd, signal.SIGKILL)
                proc.wait(timeout=2)
        if proc.poll() is None:
            raise CustodyError('child still running')

    def stop(self, handle: Handle) -> bool:
        proc = handle.process
        try:
            if proc.poll() is not None:
                return True
            try:
                if self._birth(proc.pid) != handle.birth:
                    return False
            except (OSError, IndexError, CustodyError):
                return False
            self._drain_unreturned(proc, handle.pidfd)
            return proc.poll() is not None
        finally:
            self._close(handle.pidfd)
