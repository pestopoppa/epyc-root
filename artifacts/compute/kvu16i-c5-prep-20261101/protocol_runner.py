#!/usr/bin/env python3
"""Workload sequencing component, not a complete producer or keeper launcher.

Injected transport owns no server. All output is append-only metadata; prompts and
response content never enter this stream. The caller must supply stop/abort, a
monotonic deadline, sampled server residency, source pins and own-child cleanup.
"""
import hashlib
import json
import os
import time
from pathlib import Path


def append_event(path, event):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    data = (json.dumps(event, sort_keys=True, allow_nan=False) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        with os.fdopen(fd, 'ab', closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)


def run_sequence(port, warm, warm_expected, t7a, transport, stop, abort, deadline, sink):
    """Return completed T7A rows; record an incomplete sequence on exception.

    The caller is responsible for testing socket and server cleanup even when
    this raises. Tags and body hashes are the sole persisted request identity.
    """
    if len(warm) != 2 or len(warm_expected) != 2 or len(t7a) != 48:
        raise ValueError('expected exactly two warm-up and 48 predeclared T7A requests')
    warm_digests = [hashlib.sha256(json.dumps(body).encode()).hexdigest() for body in warm]
    if warm_digests != list(warm_expected):
        raise ValueError('warm-up requests do not match predeclared hashes')
    expected = [(t, d) for t, _, d in t7a]
    if len(set(expected)) != 48:
        raise ValueError('duplicate T7A request identities')
    rows = []
    try:
        for i, body in enumerate(warm):
            digest = warm_digests[i]
            row = transport(port, f'warm-{i}', body, digest, stop, abort, deadline)
            if row.get('tag') != f'warm-{i}' or row.get('body_sha256') != digest:
                raise RuntimeError('warm-up request identity mismatch')
            if row.get('completed') is not True or row.get('http_status') != 200:
                raise RuntimeError('warm-up did not finish with HTTP 200')
            append_event(sink, {'kind':'warm_complete', **row})
        start = time.monotonic()
        append_event(sink, {'kind':'t7a_started', 't':start})
        for tag, body, digest in t7a:
            row = transport(port, tag, body, digest, stop, abort, deadline)
            if row.get('tag') != tag or row.get('body_sha256') != digest:
                raise RuntimeError('T7A request identity mismatch')
            if row.get('completed') is not True or row.get('http_status') != 200:
                raise RuntimeError('T7A request did not finish with HTTP 200')
            row['nodraft'] = body.get('speculative.n_max') == 0
            rows.append(row)
            append_event(sink, {'kind':'t7a_request_complete', **row})
        end = time.monotonic()
        append_event(sink, {'kind':'t7a_completed', 't':end, 'count':len(rows)})
        return {'start_t':start, 'end_t':end, 'rows':rows}
    except BaseException as exc:
        append_event(sink, {'kind':'protocol_incomplete', 'error_type':type(exc).__name__,
                            'completed_t7a_requests':len(rows), 't':time.monotonic()})
        raise
