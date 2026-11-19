#!/usr/bin/env python3
"""Report completion only for a complete diagnostic or a successful native smoke."""
from hashlib import sha256
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
    return False


def wired(result_path, record):
    if record.get('schema') != 'epyc.qwen4exp_cpu_loader_diagnostic.v1':
        return False
    status = record.get('status')
    statuses = {'loader_diagnostic_complete': 0, 'loader_exercised_response_refused': 1}
    if status not in statuses or 'error' in record:
        return False
    directory = result_path.parent
    output = directory / 'planning-context'
    receipt = json.loads((output / 'receipt.json').read_bytes())
    seal_raw = (directory / 'qwen4exp_cpu_loader_diagnostic.json').read_bytes()
    seal = json.loads(seal_raw)
    exact = receipt['reads']['exact']['claim_ids']
    return (
        receipt['schema'] == 'epyc.qwen4exp_cpu_loader_planning_context.v1'
        and receipt['row_id'] == record['row_id']
        and receipt['wiring_status'] == 'passed'
        and receipt['native_status'] == status
        and receipt['native_exit_code'] == statuses[status]
        and receipt['seal_sha256'] == sha256(seal_raw).hexdigest()
        and seal['files']['RESULT.json'] == sha256(result_path.read_bytes()).hexdigest()
        and receipt['ledger_sha256'] == sha256((output / 'ledger.jsonl').read_bytes()).hexdigest()
        and exact == [receipt['claim_id']]
        and receipt['capture_pins'] == record['captures']
        and receipt['grade'] == {'Q': 'Judged', 'T': 'Located'}
    )



if __name__ == '__main__':
    try:
        path = Path(sys.argv[1])
        record = json.loads(path.read_bytes())
        done = complete(record, True) if os.getenv('FILLER_DRYRUN') == '1' else wired(path, record)
    except (OSError, ValueError, AttributeError, TypeError, IndexError, KeyError):
        done = False
    raise SystemExit(0 if done else 1)
