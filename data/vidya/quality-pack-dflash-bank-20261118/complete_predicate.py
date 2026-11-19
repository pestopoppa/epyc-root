#!/usr/bin/env python3
"""Accept only the admitted production bank or completed publisher smoke."""
import json
from pathlib import Path
import sys

from capture import CAP, PROFILE, file_sha


def complete(result_path, smoke):
    result = json.loads(result_path.read_bytes())
    expected = (
        ('native-smoke-control', 'capture-complete', 1)
        if smoke else ('strict-production-bank', 'bank_admitted', 8)
    )
    mode, status, count = expected
    if (result.get('mode'), result.get('status'), result.get('request_count_per_arm')) != expected:
        return False
    if (result['target_profile'] != PROFILE or result['candidate_collected'] is not False
            or result['candidate_sha256'] is not None):
        return False
    native = result_path.parent / 'native'
    bank_path = native / 'banked-capture.json'
    bank_pin = result['bank_sha256']
    if file_sha(bank_path) != bank_pin or (native / 'banked-capture.sha256').read_text() != f'{bank_pin}\n':
        return False
    bank = json.loads(bank_path.read_bytes())
    if bank['capture_identity'] != result['capture_identity'] or len(bank['items']) != count:
        return False
    if smoke:
        return True
    checks = result['checks']
    return (bank['checks'] == checks and len(checks) == count
            and len(bank['pack_items']) == count and bank['shape']['validated_cap'] == CAP
            and all(not check['problems'] for check in checks.values()))


if __name__ == '__main__':
    try:
        ok = complete(Path(sys.argv[1]), sys.argv[2] == 'smoke')
    except (OSError, ValueError, TypeError, AttributeError, KeyError, IndexError):
        ok = False
    sys.exit(0 if ok else 1)
