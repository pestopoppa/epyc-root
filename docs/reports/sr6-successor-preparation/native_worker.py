#!/usr/bin/env python3
"""SR-6 native capture building blocks, not an executable inference row.

The caller must first establish real grant admission, window/CPU ownership,
deadlines, source and runtime seals, server readiness and residency. This module
provides deterministic arm arguments and crash-safe exposure/response capture.
It has no CLI and deliberately does not start a server or acquire a resource.
"""
import hashlib
import json
import os
import re
from pathlib import Path

ARMS = {
    'composed3': ('ngram-mod,draft-mtp', 3),
    'composed4': ('ngram-mod,draft-mtp', 4),
    'mtp3': ('draft-mtp', 3),
    'mtp4': ('draft-mtp', 4),
    'mtp4_repeat': ('draft-mtp', 4),
}
SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
HEX = re.compile(r'^[a-f0-9]{64}$')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def arm_flags(arm):
    """Speculation flags only; remaining launch flags need independent pinning."""
    if arm not in ARMS:
        raise ValueError('unknown arm')
    kind, width = ARMS[arm]
    return ['--spec-type', kind, '--spec-draft-n-max', str(width)]


def exclusive_json(path, value):
    """Create and fsync an immutable record; existing paths always fail closed."""
    payload = canonical(value) + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(os.fspath(path.parent), os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return digest(payload)


def capture_request(output, *, window, block, arm, prompt, sampler, server_record_sha256, post):
    """Record exposure before a single completion call; retain raw reply or error.

    `post(payload)` is injected by an admitted caller and returns (HTTP status,
    raw bytes). The caller owns timeouts, cancellation and server teardown. An
    existing exposure forbids retries even if the first request was interrupted.
    Failure records are not successful results or a decision verdict.
    """
    if not isinstance(output, Path) or not output.is_dir():
        raise ValueError('existing output directory required')
    if not isinstance(window, str) or not SAFE_ID.fullmatch(window):
        raise ValueError('invalid window')
    if type(block) is not int or block < 0 or arm not in ARMS:
        raise ValueError('invalid block or arm')
    if not isinstance(prompt, dict) or not isinstance(prompt.get('id'), str) or not SAFE_ID.fullmatch(prompt['id']):
        raise ValueError('invalid prompt identity')
    rendered = prompt.get('rendered')
    if not isinstance(rendered, str) or not rendered or digest(rendered.encode('utf-8')) != prompt.get('rendered_sha256'):
        raise ValueError('rendered prompt does not match plan')
    if type(prompt.get('seed')) is not int or prompt['seed'] < 0:
        raise ValueError('invalid seed')
    if not isinstance(server_record_sha256, str) or not HEX.fullmatch(server_record_sha256):
        raise ValueError('server record identity required')
    if not isinstance(sampler, dict) or not sampler or set(sampler) & {'prompt', 'seed', 'cache_prompt', 'return_tokens'}:
        raise ValueError('invalid sampler')
    payload = dict(sampler, prompt=rendered, seed=prompt['seed'], cache_prompt=False, return_tokens=True)
    # Fail before exposure if request cannot be serialized.
    canonical(payload)
    stem = f'{window}-{block}-{arm}-{prompt["id"]}'
    exposure = output / (stem + '.exposure.json')
    response = output / (stem + '.response.json')
    if response.exists():
        raise FileExistsError('response already exists')
    exposure_sha = exclusive_json(exposure, {'schema': 'sr6.exposure.v1', 'window': window, 'block': block,
        'arm': arm, 'prompt_id': prompt['id'], 'rendered_sha256': prompt['rendered_sha256'],
        'server_record_sha256': server_record_sha256, 'request': payload})
    try:
        status, raw = post(payload)
        if type(status) is not int or not isinstance(raw, bytes):
            raise ValueError('transport returned invalid status or bytes')
        # Preserve raw bytes losslessly irrespective of JSON or HTTP status.
        import base64
        record = {'schema': 'sr6.response.v1', 'state': 'raw', 'exposure_sha256': exposure_sha,
                  'http_status': status, 'raw_base64': base64.b64encode(raw).decode('ascii'),
                  'raw_sha256': digest(raw), 'verdict': None}
    except Exception as exc:
        record = {'schema': 'sr6.response.v1', 'state': 'transport_error', 'exposure_sha256': exposure_sha,
                  'error_type': type(exc).__name__, 'error': str(exc), 'verdict': None}
    exclusive_json(response, record)
    return record
