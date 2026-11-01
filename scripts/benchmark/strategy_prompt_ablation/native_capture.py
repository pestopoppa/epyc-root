#!/usr/bin/env python3
"""Persist caller-supplied per-turn strategy observations; never grants authority.

Digests establish byte integrity only. A runner must independently verify the
plan, origin, source, reset receipt, token counters and scorer before analysis.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

SCHEMA = 'epyc.strategy_prompt_ablation.capture.v2'
ARMS = ('baseline', 'strategy_short', 'strategy_long')
ORIGINS = ('synthetic', 'live_claimed')


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _optional_number(value: object, label: str, *, integer: bool = False) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{label} must be null or finite and nonnegative')
    if integer and not isinstance(value, int):
        raise ValueError(f'{label} must be an integer or null')


def write_observation(output: Path, *, plan_sha256: str, question_id: str, arm: str,
                      prompt_sha256: str, source_identity: str, slot_reset_receipt: str,
                      origin: str, status: str, turns: list[dict],
                      correct: bool | None, error: str | None = None) -> Path:
    """Write a private, exclusive task capture; all provenance remains asserted.

    Each turn requires request bytes; response may be null on failure. Counters
    and time are nullable, never imputed. Incomplete artifacts lack record.json
    and must be discarded or handled as incomplete after a failed write.
    """
    for value, name in ((plan_sha256, 'plan_sha256'), (prompt_sha256, 'prompt_sha256')):
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError(f'{name} must be a lowercase SHA-256')
    if arm not in ARMS or not isinstance(question_id, str) or not question_id.strip():
        raise ValueError('invalid arm or question_id')
    if origin not in ORIGINS or status not in ('complete', 'incomplete'):
        raise ValueError('explicit origin and valid status are required')
    for value, name in ((source_identity, 'source_identity'), (slot_reset_receipt, 'slot_reset_receipt')):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{name} is required')
    if correct is not None and not isinstance(correct, bool):
        raise ValueError('correct must be boolean or null')
    if error is not None and (not isinstance(error, str) or not error.strip()):
        raise ValueError('error must be a nonempty string or null')
    if status == 'incomplete' and correct is not None:
        raise ValueError('incomplete tasks cannot carry a final score')
    if status == 'complete' and error is not None:
        raise ValueError('complete task cannot carry an error')
    if not isinstance(turns, list) or not turns:
        raise ValueError('turns must be a nonempty list')
    entries, files = [], []
    required = {'request', 'response', 'prompt_tokens', 'output_tokens', 'elapsed_s', 'error'}
    for idx, turn in enumerate(turns, 1):
        if not isinstance(turn, dict) or set(turn) != required:
            raise ValueError('each turn needs exactly the required fields')
        req, resp = turn['request'], turn['response']
        if not isinstance(req, bytes) or not req or (resp is not None and (not isinstance(resp, bytes) or not resp)):
            raise ValueError('request must be nonempty bytes and response nonempty bytes or null')
        if status == 'complete' and resp is None:
            raise ValueError('complete task requires every response')
        for k in ('prompt_tokens', 'output_tokens'):
            _optional_number(turn[k], k, integer=True)
        _optional_number(turn['elapsed_s'], 'elapsed_s')
        err = turn['error']
        if err is not None and (not isinstance(err, str) or not err.strip()):
            raise ValueError('turn error must be a nonempty string or null')
        if status == 'complete' and err is not None:
            raise ValueError('complete task cannot contain a turn error')
        reqname = f'turn-{idx:04d}-request.bin'
        respname = f'turn-{idx:04d}-response.bin' if resp is not None else None
        files.append((reqname, req))
        if resp is not None:
            files.append((respname, resp))
        entries.append({'turn': idx, 'request_file': reqname, 'request_sha256': _sha(req),
                        'response_file': respname, 'response_sha256': _sha(resp) if resp is not None else None,
                        'prompt_tokens': turn['prompt_tokens'], 'output_tokens': turn['output_tokens'],
                        'elapsed_s': turn['elapsed_s'], 'error': err})
    record = {'schema': SCHEMA, 'plan_sha256': plan_sha256, 'question_id': question_id,
              'arm': arm, 'prompt_sha256': prompt_sha256, 'source_identity': source_identity,
              'slot_reset_receipt': slot_reset_receipt, 'origin': origin, 'status': status,
              'correct': correct, 'error': error, 'turns': entries}
    files.append(('record.json', (json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()))
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, data in files:
        fd = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    directory_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return output / 'record.json'
