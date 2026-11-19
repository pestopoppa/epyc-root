"""Scratch guard for cooperative same-process perf FD use; not kernel attestation.

Pin a duplicate of the FD opened by the source owner and compare fstat and
PERF_EVENT_IOC_ID on the pin and on the session descriptor around operations.
This requires trusted Python code, exclusive FD-table ownership and no concurrent
FD close/reuse. Checks on either side are not an atomic proof for the interval.
"""
import errno
import fcntl
import os
import struct
import threading
from kernel_counter import IOC_ID


def _identity(fd):
    s = os.fstat(fd)
    return (s.st_dev, s.st_ino, s.st_mode, s.st_rdev)


def _event_id(fd, ioctl):
    b = bytearray(8)
    ioctl(fd, IOC_ID, b, True)
    value = struct.unpack('=Q', b)[0]
    if value == 0:
        raise ValueError('zero perf event ID')
    return value


class SameFDGuard:
    def __init__(self, session, *, ioctl=fcntl.ioctl):
        if type(session.fd) is not int or session.fd < 0 or type(session.event_id) is not int or session.event_id <= 0:
            raise ValueError('invalid session identity')
        self.session = session
        self.fd = session.fd
        self.event_id = session.event_id
        self.ioctl = ioctl
        self.lock = threading.Lock()
        self.failed = False
        self.closed = False
        self.pin = os.dup(self.fd)
        try:
            if os.get_inheritable(self.pin):
                raise ValueError('pin is inheritable')
            self.identity = _identity(self.pin)
            self._check(True)
        except BaseException:
            os.close(self.pin)
            self.closed = True
            raise

    def _check(self, check_original):
        if self.closed or self.failed:
            raise ValueError('guard closed or failed')
        if self.session.fd != self.fd or self.session.event_id != self.event_id:
            raise ValueError('session identity mutated')
        if _identity(self.pin) != self.identity or _event_id(self.pin, self.ioctl) != self.event_id:
            raise ValueError('pinned event identity changed')
        if check_original and (_identity(self.fd) != self.identity or _event_id(self.fd, self.ioctl) != self.event_id):
            raise ValueError('session FD no longer matches pinned event')

    def call(self, fn, *, closes_fd=False):
        """Check around a cooperative operation; any fault permanently poisons guard.

        Set closes_fd only for a terminal operation which closes session.fd.
        The pin is checked afterwards; the closed original cannot be checked.
        """
        if type(closes_fd) is not bool or not callable(fn):
            raise ValueError('invalid operation')
        with self.lock:
            try:
                self._check(True)
                result = fn()
                self._check(not closes_fd)
                if closes_fd:
                    try:
                        os.fstat(self.fd)
                    except OSError as exc:
                        if exc.errno != errno.EBADF:
                            raise
                    else:
                        raise ValueError('terminal operation left original FD open or reused')
                    self.close()
                return result
            except BaseException:
                self.failed = True
                raise

    def close(self):
        if not self.closed:
            self.closed = True
            os.close(self.pin)
