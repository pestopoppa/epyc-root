#!/usr/bin/env python3
"""Scratch-server request transport for the prospective candidate diagnostic.

The owner supplies exact prevalidated bodies. This unit does not own the server,
write prompts, infer trigger transitions, or decide whether work may be scheduled.
"""
import hashlib
import http.client
import json
import socket
import threading
import time

class RequestInterrupted(RuntimeError):
    pass


def execute(port, tag, body, expected_sha, stop, abort, deadline, *, timeout=600, connection_factory=http.client.HTTPConnection):
    raw = json.dumps(body).encode()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha:
        raise ValueError('request body differs from predeclared identity')
    if stop.is_set() or abort.is_set() or time.monotonic() >= deadline:
        raise RequestInterrupted('request not started due to stop, safety or deadline')
    conn = connection_factory('127.0.0.1', port, timeout=timeout)
    done = threading.Event()
    caught = []
    result = []
    started = time.monotonic()
    def work():
        try:
            conn.request('POST', '/v1/chat/completions', body=raw,
                         headers={'Content-Type':'application/json'})
            response = conn.getresponse()
            content = response.read()
            try:
                payload = json.loads(content)
            except (ValueError, UnicodeDecodeError):
                payload = None
            timings = payload.get('timings') if isinstance(payload, dict) else None
            if not isinstance(timings, dict):
                timings = {}
            # Native fields only: missing or invalid counters remain unknown.
            counters = {}
            for key in ('prompt_n', 'predicted_n', 'cache_n', 'draft_n', 'draft_n_accepted'):
                value = timings.get(key)
                counters[key] = value if type(value) is int and value >= 0 else None
            result.append((response.status, len(content), hashlib.sha256(content).hexdigest(), counters))
        except BaseException as exc:
            caught.append(exc)
        finally:
            conn.close()
            done.set()
    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    reason = None
    while not done.wait(.1):
        if stop.is_set() or abort.is_set() or time.monotonic() >= deadline:
            reason = 'stop, safety, or deadline during request'
            # Shutdown wakes a blocking read on a captured socket; never touch a PID.
            sock = getattr(conn, 'sock', None)
            if sock is not None:
                try: sock.shutdown(socket.SHUT_RDWR)
                except OSError: pass
            conn.close()
            break
    thread.join(timeout=10)
    if thread.is_alive():
        raise RequestInterrupted('HTTP thread failed to drain; server cleanup required')
    if reason is not None:
        raise RequestInterrupted(reason)
    if caught:
        raise RuntimeError(f'HTTP request failed: {type(caught[0]).__name__}') from caught[0]
    if not result:
        raise RuntimeError('HTTP request ended without response')
    status, size, response_hash, counters = result[0]
    return {'tag':tag, 'body_sha256':actual, 'http_status':status, 'completed':True,
            'response_bytes':size, 'response_sha256':response_hash,
            'start_t':started, 'end_t':time.monotonic(), 'trigger_observed':None, **counters}
