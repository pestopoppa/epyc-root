#!/usr/bin/env python3
"""Bounded SR-6 completion transport for the block-controller seam.

This binds transport only. The caller must independently establish that the
loopback port belongs to the verified child, and enforce grant and deadline.
"""
import http.client
import math
import socket
import threading
import time

from native_worker import canonical
from server_lifecycle import ReadyServer


class LoopbackCompletion:
    """One POST per call, with no proxy, redirect, retry, or unbounded body."""
    def __init__(self, port, timeout_s, max_response_bytes, *, continue_check=None):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('invalid port')
        if (type(timeout_s) not in (int, float) or not math.isfinite(timeout_s)
                or not 0 < timeout_s <= 3600):
            raise ValueError('invalid timeout')
        if type(max_response_bytes) is not int or not 1 <= max_response_bytes <= 64 * 1024 * 1024:
            raise ValueError('invalid response bound')
        if continue_check is not None and not callable(continue_check):
            raise ValueError('invalid continuation check')
        self.port = port
        self.timeout_s = timeout_s
        self.max_response_bytes = max_response_bytes
        self.continue_check = continue_check

    def __call__(self, server, payload):
        if not isinstance(server, ReadyServer) or type(server.pid) is not int or server.pid <= 0:
            raise ValueError('verified server handle required')
        if not isinstance(payload, dict):
            raise ValueError('request object required')
        request_bytes = canonical(payload)
        if self.continue_check is not None:
            return self._cancellable(request_bytes)
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=self.timeout_s)
        try:
            conn.request('POST', '/completion', body=request_bytes,
                         headers={'Content-Type': 'application/json', 'Connection': 'close'})
            response = conn.getresponse()
            raw = response.read(self.max_response_bytes + 1)
            if len(raw) > self.max_response_bytes:
                raise ValueError('response exceeds declared bound')
            if response.length is not None and response.length != 0:
                raise ValueError('response ended before declared content length')
            # 3xx and 4xx/5xx are preserved as raw failures by capture_request.
            return response.status, raw
        finally:
            conn.close()

    def _cancellable(self, request_bytes):
        """Abort the socket on lost admission, STOP, or the request deadline.

        The caller's predicate must be bounded and include all three checks.
        Aborted requests must be treated as exposed and never retried.
        """
        done = threading.Event()
        abort = threading.Event()
        shared = {}
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=min(self.timeout_s, 1.0))

        def exchange():
            try:
                conn.connect()
                shared['socket'] = conn.sock
                if abort.is_set():
                    raise ValueError('request cancelled before send')
                conn.sock.settimeout(self.timeout_s)
                conn.request('POST', '/completion', body=request_bytes,
                             headers={'Content-Type': 'application/json', 'Connection': 'close'})
                response = conn.getresponse()
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise ValueError('response exceeds declared bound')
                if response.length is not None and response.length != 0:
                    raise ValueError('response ended before declared content length')
                shared['result'] = (response.status, raw)
            except Exception as exc:
                shared['error'] = exc
            finally:
                conn.close()
                done.set()

        def allowed():
            try:
                return self.continue_check() is True
            except Exception:
                return False

        if not allowed():
            raise ValueError('request cancelled before send')
        worker = threading.Thread(target=exchange, daemon=True)
        deadline = time.monotonic() + self.timeout_s
        worker.start()
        cancelled = False
        while not done.wait(0.05):
            if time.monotonic() >= deadline or not allowed():
                cancelled = True
                abort.set()
                sock = shared.get('socket')
                if sock is not None:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                # Connect itself has a one-second bound, so no reader is left
                # operating on this request when this function returns.
                if not done.wait(2.0):
                    raise RuntimeError('cancelled transport did not drain')
                break
        worker.join(2.0)
        if worker.is_alive():
            raise RuntimeError('transport thread did not exit')
        if cancelled or not allowed() or time.monotonic() >= deadline:
            raise ValueError('request cancelled in flight')
        if 'error' in shared:
            raise shared['error']
        return shared['result']
