#!/usr/bin/env python3
"""Capture raw native /slots responses during caller-owned request windows.

This module launches no server or requests by itself. The enclosing producer must
bind the server identity, retain raw request timing, own cleanup and align samples
with decode. Slot totals alone are not a count of unique unified KV cells.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request


class RejectRedirect(urllib.request.HTTPRedirectHandler):
    """Reject redirects before urllib can issue a follow-up request."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", headers, fp)


def loopback_opener():
    # Ignore environment proxies and reject all redirects, including loopback redirects.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), RejectRedirect()).open


def capture_slot_sample(base, timeout_s=5.0, *, opener=None,
                        clock=time.monotonic_ns, wall=time.time_ns):
    parsed = urllib.parse.urlsplit(base)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('base must be a loopback HTTP origin')
    if not (0 < timeout_s <= 30):
        raise ValueError('invalid timeout')
    if opener is None:
        opener = loopback_opener()
    start_ns = clock()
    start_wall_ns = wall()
    end_ns = None
    try:
        with opener(base.rstrip('/') + '/slots', timeout=timeout_s) as response:
            status = response.status
            data = response.read(8 * 1024 * 1024 + 1)
        end_ns = clock()
        if status != 200 or len(data) > 8 * 1024 * 1024:
            return {'status': 'error', 'start_monotonic_ns': start_ns, 'end_monotonic_ns': end_ns,
                    'start_wall_ns': start_wall_ns, 'reason': 'http status or response size'}
        value = json.loads(data)
        if not isinstance(value, list) or any(not isinstance(slot, dict) for slot in value):
            raise ValueError('slots response is not a list of objects')
        return {'status': 'ok', 'start_monotonic_ns': start_ns, 'end_monotonic_ns': end_ns,
                'start_wall_ns': start_wall_ns, 'raw_utf8': data.decode('utf-8')}
    except (OSError, TimeoutError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        return {'status': 'error', 'start_monotonic_ns': start_ns, 'end_monotonic_ns': end_ns if end_ns is not None else clock(),
                'start_wall_ns': start_wall_ns, 'reason': type(exc).__name__}
