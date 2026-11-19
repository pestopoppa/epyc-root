#!/usr/bin/env python3
"""Check the production-only bank's native result and immutable capture pin."""
import hashlib
import json
import os
from pathlib import Path
import sys


def complete(path):
    record = json.loads(path.read_bytes())
    if os.getenv('FILLER_DRYRUN') == '1':
        return (
            record.get('schema') == 'epyc.quality_pack_native_slice.v1'
            and record.get('status') == 'capture-complete'
            and record.get('mode') == 'native-smoke-control'
            and record.get('target_profile') == 'ingest-long-context-recurrent-no-spec'
            and record.get('candidate_sha256') is None
        )
    if (
        record.get('schema') != 'epyc.quality_pack_ingest_reconciliation_bank.v1'
        or record.get('status') != 'bank_admitted'
        or record.get('candidate_collected') is not False
        or 'error' in record
        or len(record['checks']) != 4
        or any(row['problems'] for row in record['checks'].values())
    ):
        return False
    native = path.parent / 'native'
    digest = hashlib.sha256((native / 'production-capture.json').read_bytes()).hexdigest()
    return digest == record['capture_sha256'] == (native / 'production-capture.sha256').read_text().strip()


if __name__ == '__main__':
    try:
        done = complete(Path(sys.argv[1]))
    except (OSError, ValueError, AttributeError, TypeError, KeyError, IndexError):
        done = False
    raise SystemExit(0 if done else 1)
