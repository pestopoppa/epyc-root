#!/usr/bin/env python3
"""Report completion only for a complete diagnostic or a successful native smoke."""
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
            and record.get('target_profile') == 'qwen4exp-cpu-loader-diagnostic'
            and record.get('candidate_sha256') is None
        )
    return (
        record.get('schema') == 'epyc.qwen4exp_cpu_loader_diagnostic.v1'
        and record.get('status') == 'loader_diagnostic_complete'
        and 'error' not in record
        and set(record.get('checks', {})) == {'production', 'candidate'}
        and all(row.get('semantic_matches') is True and row.get('finish') == row.get('expected_finish')
                for row in record['checks'].values())
        and set(record.get('captures', {})) == {'production', 'candidate'}
    )


if __name__ == '__main__':
    try:
        record = json.loads(Path(sys.argv[1]).read_bytes())
        done = complete(record, os.getenv('FILLER_DRYRUN') == '1')
    except (OSError, ValueError, AttributeError, TypeError, IndexError):
        done = False
    raise SystemExit(0 if done else 1)
