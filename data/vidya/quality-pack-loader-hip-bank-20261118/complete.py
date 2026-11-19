#!/usr/bin/env python3
"""Permit row completion only after strict fixture admission or native smoke."""

import json
import os
from pathlib import Path
import sys

from capture import SCHEMA
from capture_base import PROFILE, file_sha
from make_plan import ITEM


def complete(result_path, smoke):
    record = json.loads(result_path.read_bytes())
    out = result_path.parent / 'native'
    if smoke:
        return (record.get('schema') == 'epyc.quality_pack_native_slice.v1'
                and record.get('status') == 'capture-complete'
                and record.get('mode') == 'native-smoke-control'
                and record.get('target_profile') == PROFILE
                and record.get('candidate_sha256') is None
                and file_sha(out / 'banked-capture.json') == record.get('bank_sha256'))
    checks = record.get('checks', {})
    return (
        record.get('schema') == SCHEMA and record.get('status') == 'bank_admitted'
        and record.get('candidate_collected') is False and 'error' not in record
        and len(checks) == 4 and ITEM in checks and 'loader_log_evidence' in record
        and all(check.get('semantic_matches') is True and check.get('finish') == check.get('expected_finish')
                for check in checks.values())
        and file_sha(out / 'production-fixture-capture.json') == record.get('capture_sha256')
    )


if __name__ == '__main__':
    try:
        done = complete(Path(sys.argv[1]), os.environ.get('FILLER_DRYRUN') == '1')
    except (OSError, ValueError, AttributeError, TypeError, IndexError):
        done = False
    raise SystemExit(0 if done else 1)
