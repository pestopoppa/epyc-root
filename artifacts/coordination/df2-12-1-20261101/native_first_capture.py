#!/usr/bin/env python3
"""Producer-authored first-request intent and raw HTTP capture for qual/calibration."""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

from df2_parity import canonical, http, sha, write_json


def files(out):
    out = pathlib.Path(out)
    prefix = out / 'FIRST-COMPLETION'
    return out / 'FIRST-REQUEST-INTENT.json', out / 'FIRST-REQUEST-ATTEMPT.json', prefix


def wire_hashes(prefix):
    return {kind: sha(str(prefix) + suffix) if pathlib.Path(str(prefix) + suffix).exists() else None
            for kind, suffix in (('request_sha256', '.request.bin'),
                                 ('response_sha256', '.response.bin'),
                                 ('wire_status_sha256', '.wire.json'))}


def completion(base, body, out, source, min_tokens=1):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    intent_path, attempt_path, prefix = files(out)
    if intent_path.exists() or attempt_path.exists() or any(out.glob('FIRST-COMPLETION.*')):
        raise RuntimeError('refuse to overwrite first native request warrant')
    intent = {'schema': 'epyc.df2_12_1.first_request_intent.v1',
              'issued_scope': source['issued_scope'], 'source': source,
              'request_body': body, 'request_body_sha256': hashlib.sha256(canonical(body)).hexdigest(),
              'written_epoch': time.time(), 'unknown_until_response': True}
    write_json(intent_path, intent)
    start = time.monotonic()
    try:
        response = http(base, '/completion', body, timeout=300, wire_prefix=prefix)
        elapsed = max(time.monotonic() - start, 1e-6)
        tokens = response.get('tokens') if isinstance(response, dict) else None
        if not isinstance(tokens, list) or len(tokens) < min_tokens or not all(type(token) is int for token in tokens):
            raise RuntimeError('native completion omitted adequate integer token IDs')
        write_json(attempt_path, {'schema': 'epyc.df2_12_1.first_request_attempt.v1',
                   'status': 'RESPONSE_VALID_UNSEALED', 'unknown_disposition': 'UNKNOWN',
                   'intent_sha256': sha(intent_path), 'wire': wire_hashes(prefix),
                   'elapsed_s': elapsed, 'token_count': len(tokens),
                   'tokens_sha256': hashlib.sha256(canonical(tokens)).hexdigest(),
                   'written_epoch': time.time()})
        return response, elapsed
    except BaseException as exc:
        write_json(attempt_path, {'schema': 'epyc.df2_12_1.first_request_attempt.v1',
                   'status': 'FAILED_OR_EXPOSURE_UNKNOWN', 'unknown_disposition': 'UNKNOWN',
                   'intent_sha256': sha(intent_path), 'wire': wire_hashes(prefix),
                   'elapsed_s': time.monotonic() - start, 'error': repr(exc),
                   'written_epoch': time.time()})
        raise


def disposition(out, status, evidence=None, error=None):
    intent_path, attempt_path, prefix = files(out)
    if not intent_path.exists():
        return
    write_json(pathlib.Path(out) / 'FIRST-REQUEST-DISPOSITION.json', {
        'schema': 'epyc.df2_12_1.first_request_disposition.v1', 'status': status,
        'unknown_disposition': 'UNKNOWN' if status != 'ACCEPTED' else None,
        'intent_sha256': sha(intent_path),
        'attempt_sha256': sha(attempt_path) if attempt_path.exists() else None,
        'wire': wire_hashes(prefix), 'evidence': evidence, 'error': error,
        'written_epoch': time.time()})
