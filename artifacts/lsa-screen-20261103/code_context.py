#!/usr/bin/env python3
"""Bounded LSA code-revision context from explicitly supplied CI verifier receipts."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters import ci_conformance
from claim_tuple import ProjectionError, grade


def collect(receipts, *, repo_label, commit, case):
    """Reopen original receipts; return only verified exact revision/case observations."""
    if not repo_label or not re.fullmatch(r'[0-9a-f]{40}', commit) or not case.startswith('lsa-'):
        raise ValueError('nonempty repo label, full lowercase commit and LSA case required')
    visible, refused, omitted = [], [], []
    for path in receipts:
        try:
            rows = ci_conformance.native_rows(Path(path))
            if not rows:
                omitted.append({'receipt': str(path), 'reason': 'no decided verifier claim'})
            for native in rows:
                record = native['record']
                if record['repositories'].get(repo_label) != commit:
                    omitted.append({'receipt': str(path), 'reason': 'repository label or revision mismatch'})
                    continue
                if case not in record['selections'] or not any(
                    row.get('name') == case and row.get('classname') == 'lsa_native_unit'
                    for row in record['summary']['cases']
                ):
                    omitted.append({'receipt': str(path), 'reason': 'named LSA case mismatch'})
                    continue
                if not any(item.get('role') == 'declared_read' for item in record['readset']):
                    omitted.append({'receipt': str(path), 'reason': 'missing declared readset'})
                    continue
                claim = ci_conformance.project_ci_conformance(native)
                if claim.source_class != 'verifier' or not claim.decided_proposition:
                    omitted.append({'receipt': str(path), 'reason': 'no bounded verifier proposition'})
                    continue
                level, detail, reasons = grade(claim)
                if level in ('Refused', 'Invalid') or detail in ('Refused', 'Invalid'):
                    omitted.append({'receipt': str(path), 'reason': 'shared grade refused'})
                    continue
                visible.append({'claim_id': 'clm_' + claim.measurement_id,
                    'grade': [level, detail], 'grade_reasons': reasons,
                    'native_locator': native['receipt_path'], 'case': case,
                    'value': claim.value, 'decided_proposition': claim.decided_proposition,
                    'basis': 'bounded command exit for producer-declared repository label and source revision'})
        except (ProjectionError, OSError, ValueError, KeyError, TypeError) as exc:
            refused.append({'receipt': str(path), 'reason': str(exc)})
    return {'scope': 'code_revision', 'repo_label': repo_label, 'commit': commit,
            'case': case, 'claims': visible, 'omitted': omitted, 'refused': refused}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-label', required=True)
    rev = parser.add_mutually_exclusive_group(required=True)
    rev.add_argument('--commit')
    rev.add_argument('--checkout', help='use current checkout HEAD; makes no historical path claim')
    parser.add_argument('--case', required=True)
    parser.add_argument('--receipt', required=True, action='append')
    args = parser.parse_args()
    commit = args.commit
    if args.checkout:
        commit = subprocess.check_output(['git', '-C', args.checkout, 'rev-parse', 'HEAD'], text=True).strip()
    answer = collect(args.receipt, repo_label=args.repo_label, commit=commit, case=args.case)
    if args.checkout:
        answer['requester_current_checkout'] = str(Path(args.checkout).resolve())
    print(json.dumps(answer, indent=2))
    return 1 if answer['refused'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
