#!/usr/bin/env python3
"""Structured filer outcomes; failed validation never erases native completion.

Input is JSONL with explicit forensic family A..I (no guessing from rc). Output
is retained JSONL or a Markdown rollup. --validate-only replays a validator on
retained outputs without launching the native job.
"""
from __future__ import annotations
import argparse
from collections import Counter
from enum import Enum
import json
from pathlib import Path
import subprocess
import sys

class Family(str, Enum):
    ENVIRONMENT = 'A'
    VALIDATOR = 'B'
    ADMISSION = 'C'
    PLACEMENT = 'D'
    DEADLINE = 'E'
    DISK = 'F'
    IDENTITY = 'G'
    WITHDRAWN = 'H'
    DIAGNOSTIC = 'I'

class Outcome(str, Enum):
    COMPLETE = 'COMPLETE'
    PARTIAL = 'PARTIAL'
    FAILED = 'FAILED-RUN'
    WITHDRAWN = 'WITHDRAWN'
    VALIDATOR = 'VALIDATOR-FAILED'
    DIAGNOSTIC = 'DIAGNOSTIC-RESULT'
    WAIT_DISK = 'READY-WAIT-DISK'
    QUALIFIED = 'QUALIFIED'
    QUAL_FAILED = 'QUALIFICATION-FAILED'
    REFUSED = 'REFUSED-PRE-GRANT'

def classify(record):
    result = dict(record)
    family = Family(record['root_cause_family'])
    if record.get('state') == Outcome.WAIT_DISK:
        outcome = Outcome.WAIT_DISK
        if record.get('compute_burned') or record.get('granted'):
            raise ValueError('WAIT-DISK cannot have a grant or compute')
    elif family == Family.WITHDRAWN or record.get('reason') in ('owner-retired', 'stop-file-before-start'):
        outcome = Outcome.WITHDRAWN
    elif record.get('native_complete') is True and record.get('validator_rc', 0) != 0:
        outcome = Outcome.VALIDATOR
    elif family == Family.DIAGNOSTIC and record.get('diagnostic_result') is True:
        outcome = Outcome.DIAGNOSTIC
    elif record.get('phase') == 'qualification':
        outcome = Outcome.QUALIFIED if record['rc'] == 0 else Outcome.QUAL_FAILED
    elif record.get('granted') is False:
        outcome = Outcome.REFUSED
    elif record['rc'] == 0:
        outcome = Outcome.COMPLETE
    elif record['rc'] == 75 and record.get('partial') is True:
        outcome = Outcome.PARTIAL
    else:
        outcome = Outcome.FAILED
    result['outcome'] = outcome.value
    result['root_cause_family'] = family.value
    # Operator D2: failed grants subtract; republishing and disk waits never score.
    result['qualified_science_run'] = bool(record.get('phase') == 'production' and record.get('qualified') is True and record.get('granted') is True
        and outcome in (Outcome.COMPLETE, Outcome.PARTIAL) and record.get('verdict'))
    result['science_score'] = 1 if result['qualified_science_run'] else -1 if outcome == Outcome.FAILED and record.get('phase') == 'production' and record.get('granted') else 0
    result['retain_native_output'] = outcome == Outcome.VALIDATOR
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', nargs='?')
    p.add_argument('--validate-only', nargs=argparse.REMAINDER)
    p.add_argument('--workdir')
    args = p.parse_args()
    if args.validate_only is not None:
        if not args.validate_only or not args.workdir:
            p.error('--validate-only requires --workdir and an argv command')
        return subprocess.run(args.validate_only, cwd=args.workdir).returncode
    counts = Counter()
    for line in Path(args.input).read_text().splitlines():
        if line.strip():
            record = classify(json.loads(line))
            counts[(record['root_cause_family'], record['outcome'])] += 1
            print(json.dumps(record, sort_keys=True))
    print(json.dumps({'counts': {'%s/%s' % k: v for k, v in sorted(counts.items())}}, sort_keys=True), file=sys.stderr)
    return 0

if __name__ == '__main__':
    sys.exit(main())


def record_launcher_dead(identity_path, ended_path):
    """Keeper fallback for SIGKILL: birth-bound death, immutable, no signalling.

    The engine remains sole writer while alive. A SIGKILL cannot execute EXIT
    cleanup; this separate recovery path is required before filing that attempt.
    """
    from filler_engine14 import launcher_dead, ended
    identity = json.loads(Path(identity_path).read_text())
    if not launcher_dead(int(identity['pid']), identity['birth']):
        raise ValueError('launcher-still-alive')
    ended(Path(ended_path), 70, 'launcher-dead:pid=%s:birth=%s' % (identity['pid'], identity['birth']))
