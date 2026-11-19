"""Independent monotonic deadline for a captured, caller-owned HTTP socket.

Only shuts down the supplied socket; never closes a recycled descriptor and
never sends another request. This bounds transport waits, not native release.
"""
import math
import socket
import threading
import time


class SocketDeadline:
    def __init__(self, owned_socket, deadline):
        if not math.isfinite(deadline) or deadline <= time.monotonic():
            raise ValueError('transport deadline must be finite and future')
        if not isinstance(owned_socket, socket.socket) or owned_socket.fileno() < 0:
            raise ValueError('live caller-owned socket required')
        self.socket = owned_socket
        self.deadline = deadline
        self.done = threading.Event()
        self.expired = threading.Event()
        self.thread = threading.Thread(target=self._watch, daemon=True)

    def _watch(self):
        if self.done.wait(max(0., self.deadline - time.monotonic())):
            return
        self.expired.set()
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            # Already closed by normal/exceptional transport cleanup.
            pass

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.done.set()
        self.thread.join(timeout=1.)
        if self.thread.is_alive():
            raise RuntimeError('transport watchdog failed to join')

    def check(self):
        if self.expired.is_set() or time.monotonic() >= self.deadline:
            raise TimeoutError('independent seed transport deadline expired')
