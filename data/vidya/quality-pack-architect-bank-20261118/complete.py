#!/usr/bin/env python3
"""Report completion only for an admitted bank or a successful native smoke."""
import json
import os
from pathlib import Path
import sys


def complete(record, smoke):
    if smoke:
        return (
            record.get('schema') == 'epyc.quality_pack_native_slice.v1'
            and record.get('status') == 'capture-complete'
            and record.get('mode') == 'native-smoke-control'
            and record.get('target_profile') == 'architect-critic-cpu-mtp'
            and record.get('candidate_sha256') is None
        )
    return (
        record.get('schema') == 'epyc.quality_pack_architect_critic_bank.v1'
        and record.get('status') == 'bank_admitted'
        and record.get('candidate_collected') is False
        and 'error' not in record
        and len(record.get('checks', {})) == 4
        and all(not row.get('problems') for row in record['checks'].values())
        and isinstance(record.get('capture_sha256'), str)
    )


if __name__ == '__main__':
    try:
        record = json.loads(Path(sys.argv[1]).read_bytes())
        done = complete(record, os.getenv('FILLER_DRYRUN') == '1')
    except (OSError, ValueError, AttributeError, TypeError, IndexError):
        done = False
    raise SystemExit(0 if done else 1)
