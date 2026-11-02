"""Single-request capture seam for SR-7; not a grant-ready launcher.

Injected adapters must prove admission, fresh server/port identity, deadline,
process-tree drain and authoritative cross-run prompt inventory. This module
cannot verify those properties. A failure after exposure is never retried here.
"""
import hashlib
import json
import os
from pathlib import Path
import re

from native_transport import post_completion
from proposer_stats import parse_proposer_stats

SAFE_ID = re.compile(r'^[A-Za-z0-9_]+$')


def _write_once(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())


def _json(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()


def capture_once(*, root, request_id, payload, expected_names, port, timeout_s,
                 admit, launch, verify, stop, read_trace, post=post_completion):
    """Capture one request and reconcile its counters after the owned child stops.

    The request ID's exclusive start record prevents retry in this directory;
    callers must provide an authoritative disjoint prompt inventory and exclude
    concurrent use of a prompt under a different ID. launch must clean up if it
    spawns a child and then raises. stop must fail if the captured child was not
    reaped; descendant drain must be independently verified by the adapter.
    """
    if (not isinstance(root, Path) or root.is_symlink() or not root.is_dir()
            or not isinstance(request_id, str) or not SAFE_ID.fullmatch(request_id)):
        raise ValueError('real root and safe request ID required')
    if not all(callable(x) for x in (admit, launch, verify, stop, read_trace, post)):
        raise ValueError('missing adapter')
    if not isinstance(payload, dict):
        raise ValueError('payload required')
    request_bytes = _json(payload)
    if admit() is not True:
        raise ValueError('admission unverified')
    prefix = root / request_id
    _write_once(prefix.with_suffix('.start.json'), _json({'request_sha256': hashlib.sha256(request_bytes).hexdigest()}))
    process = launch()
    if process is None:
        raise ValueError('owned child required')
    try:
        evidence = verify(process, port)
        if not isinstance(evidence, dict) or not evidence:
            raise ValueError('server identity unverified')
        _write_once(prefix.with_suffix('.exposure.json'), _json({'request': payload, 'server': evidence}))
        try:
            status, raw = post(port, payload, timeout_s)
            if type(status) is not int or not isinstance(raw, bytes):
                raise ValueError('invalid transport capture')
            _write_once(prefix.with_suffix('.response.bin'), raw)
            _write_once(prefix.with_suffix('.response.json'), _json({'status': status, 'sha256': hashlib.sha256(raw).hexdigest()}))
        except Exception as exc:
            _write_once(prefix.with_suffix('.error.json'), _json({'type': type(exc).__name__}))
            raise
    finally:
        stop(process)
    trace = read_trace(process)
    if not isinstance(trace, bytes):
        raise ValueError('trace bytes required')
    _write_once(prefix.with_suffix('.trace.bin'), trace)
    if status != 200:
        raise ValueError('non-200 response retained')
    try:
        response = json.loads(raw)
        timings = response['timings']
        parsed = parse_proposer_stats(trace.decode('utf-8'), expected_names,
                                      timings['draft_n'], timings['draft_n_accepted'])
    except (KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('native response or trace invalid') from exc
    _write_once(prefix.with_suffix('.parsed.json'), _json(parsed))
    return parsed
