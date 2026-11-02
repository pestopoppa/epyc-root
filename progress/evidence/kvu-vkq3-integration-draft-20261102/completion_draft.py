"""Offline predicate draft for VKQ3 receipt units; not a rowflow launcher."""
import json
import os
from pathlib import Path
import sys

FAILURES = {'nonzero_exit', 'timeout', 'cancelled', 'output_overflow',
            'input_incomplete', 'invalid_completion', 'invalid_output'}


def complete_diagnostic(mode, attempt_id, directory):
    """Require matching durable unit, marker, mode and direct-child cleanup.

    Qualification requires a completed native output; full bounded failures
    are terminal but inconclusive. This does not prove process-tree cleanup,
    grant validity, identity, or that the receipt writer itself is trusted.
    """
    if mode not in ('qualification', 'full') or not isinstance(attempt_id, str):
        return False
    try:
        root = Path(directory)
        result = json.loads((root / 'result.json').read_text())
        unit_raw = (root / 'unit.jsonl').read_text()
        if not unit_raw.endswith('\n') or len(unit_raw.splitlines()) != 1:
            return False
        unit = json.loads(unit_raw)
        marker = json.loads((root / 'complete.json').read_text())
        if not isinstance(result, dict) or result != unit or marker != {'attempt_id': attempt_id, 'mode': mode}:
            return False
        if (result.get('schema') != 'vkq3-receipt-draft-v1' or result.get('attempt_id') != attempt_id
                or result.get('mode') != mode or result.get('cleanup') is not True):
            return False
        status, verdict = result.get('status'), result.get('verdict')
        count = result.get('validated_token_count')
        if status == 'completed':
            valid = (type(result.get('returncode')) is int and result.get('returncode') == 0
                     and type(count) is int and (count > 0 if mode == 'qualification' else count >= 0)
                     and type(result.get('expected_input_bytes')) is int
                     and result.get('input_bytes_written') == result['expected_input_bytes'])
            return valid and verdict == ('excluded_qualification' if mode == 'qualification' else 'synthetic_input_completed')
        return mode == 'full' and status in FAILURES and verdict == 'inconclusive' and count is None
    except (OSError, ValueError, TypeError):
        return False


def publish_unit(mode, attempt_id, directory, destination):
    """Publish one JSON/JSONL-compatible unit only after a complete receipt.

    Destination must be a new file in an existing private directory. A native
    dry-run result path accepts the same single JSON object as the full JSONL
    path. This helper assumes the receipt directory is owned by the worker and
    is not being modified concurrently; it is not a launcher or grant check.
    """
    dest = Path(destination)
    if not dest.is_absolute():
        raise ValueError('result path must be absolute')
    if not complete_diagnostic(mode, attempt_id, directory):
        raise ValueError('receipt is not complete')
    payload = (Path(directory) / 'unit.jsonl').read_bytes()
    tmp = dest.parent / ('.' + dest.name + '.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.link(tmp, dest, follow_symlinks=False)
        os.unlink(tmp)
        dfd = os.open(dest.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except BaseException:
        # Preserve a partial as interruption evidence and prohibit retry in place.
        raise


if __name__ == '__main__':
    sys.exit(0 if len(sys.argv) == 4 and complete_diagnostic(*sys.argv[1:]) else 1)
