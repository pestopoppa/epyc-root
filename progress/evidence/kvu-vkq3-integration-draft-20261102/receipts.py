"""Offline receipt draft; no grant, launcher, or tokenizer integration.

Input is a bounded supervisor result already held by the caller. This module
never saves raw stdout/stderr. The token stream follows the frozen v10 source --ids output: a bracketed,
comma-separated list of nonnegative ASCII decimal integers. The actual tokenizer
binary must still be bound to the approved source before use.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z')
_TOKENS = re.compile(rb'\[(?:[0-9]+(?:, [0-9]+)*)?\]\n\Z')
_FAILURES = {'nonzero_exit', 'timeout', 'cancelled', 'output_overflow', 'input_incomplete'}


def _durable_file(directory, name, data):
    """Publish one new private file and sync its content and directory entry."""
    tmp = directory / ('.' + name + '.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(tmp, directory / name, follow_symlinks=False)
        os.unlink(tmp)
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except BaseException:
        # Retain a partial temporary file as interruption evidence.
        raise


def _json(obj):
    return (json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')


def write_attempt(root, attempt_id, mode, result, *, expected_input_bytes, ceiling_s):
    """Write an isolated, private attempt; marker is always written last.

    root must be an existing caller-owned private directory. Returns its new
    attempt directory. Any error leaves partial evidence without a completion marker.
    """
    if not _ID.fullmatch(attempt_id) or mode not in ('qualification', 'full'):
        raise ValueError('invalid attempt identity or mode')
    if not isinstance(expected_input_bytes, int) or expected_input_bytes < 0 or ceiling_s <= 0:
        raise ValueError('invalid input length or ceiling')
    root = Path(root)
    st = root.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) & 0o077:
        raise ValueError('root must be a private owned directory')
    status = result['status']
    if status not in _FAILURES | {'completed'}:
        raise ValueError('unsupported supervisor status')
    cleanup = result['cleanup'] is True
    if not cleanup:
        status = 'failed_cleanup'
    output = result['stdout']
    if not isinstance(output, bytes):
        raise ValueError('stdout must be bytes')
    count = None
    if status == 'completed':
        if result['returncode'] != 0 or result['input_bytes_written'] != expected_input_bytes:
            status = 'invalid_completion'
        elif not _TOKENS.fullmatch(output):
            status = 'invalid_output'
        else:
            count = 0 if output == b'[]\n' else output.count(b', ') + 1
    verdict = ('synthetic_input_completed' if status == 'completed' else 'inconclusive') if mode == 'full' else 'excluded_qualification'
    record = {'schema': 'vkq3-receipt-draft-v1', 'attempt_id': attempt_id, 'mode': mode,
              'status': status, 'verdict': verdict, 'cleanup': cleanup,
              'returncode': result['returncode'], 'input_bytes_written': result['input_bytes_written'],
              'expected_input_bytes': expected_input_bytes, 'ceiling_s': ceiling_s,
              'tokenizer_process_total_wall_s': result['elapsed_s'],
              'stdout_bytes': len(output), 'stdout_sha256': hashlib.sha256(output).hexdigest(),
              'validated_token_count': count}
    encoded = _json(record)  # validate serializability before creating anything
    directory = root / (mode + '-' + attempt_id)
    directory.mkdir(mode=0o700)  # exclusive: no reuse/reset
    rootfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(rootfd)
    finally:
        os.close(rootfd)
    _durable_file(directory, 'result.json', encoded)
    _durable_file(directory, 'unit.jsonl', encoded)
    _durable_file(directory, 'complete.json', _json({'attempt_id': attempt_id, 'mode': mode}))
    return directory
