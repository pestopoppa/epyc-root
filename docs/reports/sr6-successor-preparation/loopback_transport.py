#!/usr/bin/env python3
"""Bounded SR-6 completion transport for the block-controller seam.

This binds transport only. The caller must independently establish that the
loopback port belongs to the verified child, and enforce grant and deadline.
"""
import http.client
import math

from native_worker import canonical
from server_lifecycle import ReadyServer


class LoopbackCompletion:
    """One POST per call, with no proxy, redirect, retry, or unbounded body."""
    def __init__(self, port, timeout_s, max_response_bytes):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('invalid port')
        if (type(timeout_s) not in (int, float) or not math.isfinite(timeout_s)
                or not 0 < timeout_s <= 3600):
            raise ValueError('invalid timeout')
        if type(max_response_bytes) is not int or not 1 <= max_response_bytes <= 64 * 1024 * 1024:
            raise ValueError('invalid response bound')
        self.port = port
        self.timeout_s = timeout_s
        self.max_response_bytes = max_response_bytes

    def __call__(self, server, payload):
        if not isinstance(server, ReadyServer) or type(server.pid) is not int or server.pid <= 0:
            raise ValueError('verified server handle required')
        if not isinstance(payload, dict):
            raise ValueError('request object required')
        request_bytes = canonical(payload)
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
