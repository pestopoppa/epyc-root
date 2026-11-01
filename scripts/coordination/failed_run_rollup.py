#!/usr/bin/env python3
"""Structured filer outcomes; failed validation never erases native completion.

Input is JSONL with explicit forensic family A..I (no guessing from rc). Output
is retained JSONL or a Markdown rollup. Science quota scores are emitted only
by science_quota.py after retained evidence verification. --validate-only replays a validator on
retained outputs without launching the native job.
"""
from __future__ import annotations
import argparse
from collections import Counter
from enum import Enum
import json
from pathlib import Path
import re
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
    # Classification is forensic metadata, never evidence-backed quota authority.
    # Strip caller-supplied score fields too: copying them would retain the bypass.
    result.pop('qualified_science_run', None)
    result.pop('science_score', None)
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
    identity_file = Path(identity_path)
    identity = json.loads(identity_file.read_text())
    row_id = identity.get('id')
    if not isinstance(row_id, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', row_id) is None:
        raise ValueError('invalid-launcher-id')
    phase = identity.get('phase')
    if phase not in ('qualification', 'production'):
        raise ValueError('invalid-launcher-phase')
    grants_dir = identity.get('grants_dir')
    if not isinstance(grants_dir, str) or not Path(grants_dir).is_absolute():
        raise ValueError('invalid-launcher-grants-dir')
    grants_root = Path(grants_dir)
    try:
        if grants_root.is_symlink() or grants_root.resolve(strict=True) != grants_root or not grants_root.is_dir():
            raise ValueError('unsafe-launcher-grants-dir')
    except OSError as exc:
        raise ValueError('unsafe-launcher-grants-dir') from exc

    ended_target = Path(ended_path)
    if (not ended_target.is_absolute() or ended_target.name != row_id + '.ended'
            or ended_target.parent != grants_root or ended_target.is_symlink()):
        raise ValueError('ended-path-identity-mismatch')
    if (not identity_file.is_absolute() or identity_file.name != row_id + '.launcher.json'
            or identity_file.parent != grants_root or identity_file.is_symlink()):
        raise ValueError('identity-path-mismatch')
    try:
        pid = identity['pid']
        birth = identity['birth']
    except KeyError as exc:
        raise ValueError('invalid-launcher-identity') from exc
    if type(pid) is not int or pid <= 0 or not isinstance(birth, str) or not birth.isdigit():
        raise ValueError('invalid-launcher-identity')
    if not launcher_dead(pid, birth):
        raise ValueError('launcher-still-alive')
    owner = None
    if phase == 'production':
        owner = identity.get('owner')
        verifier_fields = ('manifest_path', 'nonce_store', 'allowlist_path', 'policy_path', 'flags_dir')
        if not isinstance(owner, str) or not owner.strip() or any(
                not isinstance(identity.get(key), str) or not identity[key]
                for key in verifier_fields):
            raise ValueError('production-launcher-owner-proof-missing')
        try:
            from types import SimpleNamespace
            import qualify_launcher
            manifest = qualify_launcher.load(identity['manifest_path'])
            if manifest.get('id') != row_id or manifest.get('owner') != owner:
                raise ValueError('production-launcher-owner-binding-mismatch')
            verified = qualify_launcher.verify(manifest, SimpleNamespace(
                allowlist=identity['allowlist_path'], nonce_store=identity['nonce_store'],
                policy=identity['policy_path'], fingerprint_now=False,
                flags_dir=identity['flags_dir']))
            if verified.get('id') != row_id or verified.get('id') != manifest.get('id'):
                raise ValueError('production-launcher-receipt-binding-mismatch')
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('production-launcher-owner-proof-invalid') from exc
    ended(ended_target, 70, 'launcher-dead:pid=%s:birth=%s' % (pid, birth), phase=phase, owner=owner)
