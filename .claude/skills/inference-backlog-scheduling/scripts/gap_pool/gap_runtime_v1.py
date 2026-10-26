#!/usr/bin/env python3
"""PROPOSED v1, no installation or live authorization. Pure callbacks in fixtures only.

The owner must serialize ALL HOLD/row/grant mutations under the SAME existing
region/publication lease. A boolean from this process cannot establish that lease.
No callback from this module executes the operational canonical validator CLI.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
import gap_policy
# Native validator stays canonical in the tracked root; private fixture bundles
# retain a pinned sibling copy solely for isolated model-free tests.
import importlib.util
_validator_path = Path(__file__).resolve().parents[5] / "scripts/coordination/validate_fillers.py"
if not _validator_path.is_file():
    _validator_path = Path(__file__).with_name("validate_fillers.py")
_validator_spec = importlib.util.spec_from_file_location("gap_native_validator", _validator_path)
validator = importlib.util.module_from_spec(_validator_spec)
_validator_spec.loader.exec_module(validator)

NIGHT_IDS = frozenset(('akx-lb3-2-cv2-pair-20261026', 'v11-086-cpu', 'kvu12-5-np8', 'ch27-q38fn-floors'))
NIGHT = 'HOLD_GPU_FOR_QUIET_NIGHT_20261026'
LEGACY = Path('/mnt/raid0/llm/tmp/HOLD_GPU_FOR_QUIET_20261024')

class Refuse(Exception):
    pass

def utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def read_record(path):
    """Stable regular nonsymlink bytes; metadata+bytes detect replacement and edit."""
    path = Path(path)
    first = path.lstat()
    if not stat.S_ISREG(first.st_mode):
        raise Refuse('nonregular-input:' + str(path))
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        data = stream.read()
        closed = os.fstat(stream.fileno())
    last = path.lstat()
    def identity(s):
        return s.st_dev, s.st_ino, s.st_mtime_ns, s.st_ctime_ns, s.st_size, s.st_mode
    if len({identity(s) for s in (first, opened, closed, last)}) != 1:
        raise Refuse('unstable-input:' + str(path))
    return identity(last), data

def exists(path):
    return os.path.lexists(path)

def holds_snapshot(flags, legacy=LEGACY):
    paths = sorted(Path(flags).glob('HOLD_*'))
    answer = {str(p): read_record(p) for p in paths}
    if exists(legacy):
        answer[str(legacy)] = read_record(legacy)
    if paths != sorted(Path(flags).glob('HOLD_*')):
        raise Refuse('hold-set-race')
    return answer

def capture(flags, row_id, grant_bytes=None, legacy=LEGACY):
    flags = Path(flags)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', row_id):
        raise Refuse('unsafe-row-id')
    rows = read_record(flags / 'FILLERS.md')
    grant_path = flags / 'grants' / (row_id + '.grant')
    grant = read_record(grant_path) if grant_bytes is None else (None, grant_bytes)
    return rows, grant, holds_snapshot(flags, legacy)

def parse_grant(data):
    try:
        tokens = data.decode('utf-8').split()
        pairs = [x.split('=', 1) for x in tokens]
        if len(pairs) != 3 or any(len(x) != 2 for x in pairs):
            raise ValueError()
        result = dict(pairs)
        if set(result) != {'regions', 'start', 'end'} or len(result) != len(pairs):
            raise ValueError()
        gap_policy.epoch(result['start']); gap_policy.epoch(result['end'])
        return result
    except (UnicodeError, ValueError):
        raise Refuse('malformed-canonical-grant')

def row_from_snapshot(record, row_id):
    try:
        col, rows, _ = validator.parse_table(record[1].decode('utf-8'))
        matches = [c for _, c in rows if c and c[0] == row_id]
        if len(matches) != 1 or len(matches[0]) != 18:
            raise Refuse('canonical-row-count-or-schema')
        cells = matches[0]
        # Native validator's structural rules and derived class, never an invented enum.
        # Liveness is retained in normal grant_ok, not counterfeited here.
        errors = validator.check_row(cells, col, set(), pid_alive=lambda *_: True)
        if errors:
            raise Refuse('canonical-row-invalid:' + ';'.join(errors))
        return {k: cells[v] for k, v in col.items()}, validator.derive_booking_class(cells, col)
    except (UnicodeError, validator.Malformed, IndexError) as error:
        raise Refuse('canonical-row-parse:' + str(error))

def fold_cpus(spec):
    result = set()
    for token in spec.split(','):
        if not re.fullmatch(r'\d+(?:-\d+)?', token):
            raise Refuse('malformed-affinity')
        values = [int(x) for x in token.split('-')]
        a, b = values[0], values[-1]
        if not 0 <= a <= b <= 191:
            raise Refuse('invalid-affinity')
        result.update(c % 96 for c in range(a, b + 1))
    return result

def night_allowed(holds, row_id, grant, now):
    if row_id not in NIGHT_IDS or len(holds) != 1:
        return False
    name, record = next(iter(holds.items()))
    if Path(name).name != NIGHT:
        return False
    tokens = record[1].decode('utf-8').split()
    by = [t for t in tokens if t.startswith('by=')]
    ids = [t for t in tokens if t.startswith('grant=')]
    # Existing per-grant night rule; never admits any pool or other ordinary row.
    return (by == ['by=workspace-58'] and ids == ['grant=' + row_id]
            and gap_policy.epoch(now) < gap_policy.epoch(grant['end']) - 90)

def evaluate(snapshot, row_id, *, adopted=False, now=None, cpus=None,
             expected_start=None, expected_end=None, expected_regions=None,
             writer=False):
    now = now or utc()
    rows, grant_record, holds = snapshot
    grant = parse_grant(grant_record[1])
    row, derived = row_from_snapshot(rows, row_id)
    for key, value in (('start', expected_start), ('end', expected_end), ('regions', expected_regions)):
        if value is not None and grant[key] != value:
            raise Refuse('exported-' + key + '-mismatch')
    s, e, n = [gap_policy.epoch(x) for x in (grant['start'], grant['end'], now)]
    if not s <= n < e:
        raise Refuse('outside-live-grant')
    if not holds:
        return 'no-hold; normal-guards-required'
    if night_allowed(holds, row_id, grant, now):
        return 'exact-existing-night; normal-guards-required'
    # The external legacy HOLD never gains quiet metadata semantics.
    if any(Path(name).parent != Path(next(iter(holds))).parent for name in holds):
        raise Refuse('external-legacy-hold')
    if str(LEGACY) in holds:
        raise Refuse('external-legacy-hold')
    if derived != 'block-correctness':
        raise Refuse('derived-not-correctness')
    quarter = gap_policy.canonical_quarter(grant['regions'])
    if quarter is None or gap_policy.canonical_quarter(row['resources']) != quarter:
        raise Refuse('row-grant-quarter-mismatch')
    if not writer:
        if cpus is None:
            raise Refuse('missing-actual-affinity')
        lo = int(quarter[1:]) * 24
        if fold_cpus(cpus) != set(range(lo, lo + 24)):
            raise Refuse('actual-affinity-not-exact-quarter')
    ok, reason = gap_policy.admit(notes=row['notes'], booking_class=row['class'],
        substrate=row['substrate'], regions=grant['regions'], start=grant['start'],
        end=grant['end'], now=now, holds={Path(k).name: v[1].decode('utf-8') for k, v in holds.items()},
        adopted=adopted)
    if not ok:
        raise Refuse(reason)
    return reason

def checked(flags, row_id, *, legacy=LEGACY, **options):
    before = capture(flags, row_id, legacy=legacy)
    reason = evaluate(before, row_id, **options)
    if before != capture(flags, row_id, legacy=legacy):
        raise Refuse('admission-snapshot-race')
    return reason

def publish_under_owner_lease(flags, row_id, grant_bytes, normal_admission,
                              *, lease, adopted=False, now=None, legacy=LEGACY,
                              before_compare=lambda: None):
    """Owner passes its ALREADY HELD lease object; no new lock namespace here.

    All row/HOLD/grant writers MUST share lease; otherwise not activation-ready.
    The fake lease is fixture-only. Normal admission may invoke preconditions;
    therefore it is called only after first read-only HOLD admission.
    """
    lease.assert_held()
    flags = Path(flags)
    target = flags / 'grants' / (row_id + '.grant')
    absolute_end = gap_policy.epoch(parse_grant(grant_bytes)["end"])
    inherited_end = os.environ.get("FILLER_END")
    if inherited_end is not None:
        absolute_end = min(absolute_end, int(inherited_end))
    def admission_deadline():
        if time.time() >= absolute_end:
            raise Refuse("admission-deadline-expired")
    admission_deadline()
    if exists(target):
        raise Refuse('existing-grant')
    before = capture(flags, row_id, grant_bytes, legacy)
    admission_deadline()
    evaluate(before, row_id, adopted=adopted, now=now, writer=True)
    admission_deadline()
    normal_admission()
    admission_deadline()
    before_compare()
    admission_deadline()
    lease.assert_held()
    if exists(target) or before != capture(flags, row_id, grant_bytes, legacy):
        raise Refuse('publication-snapshot-race')
    evaluate(before, row_id, adopted=adopted, now=now, writer=True)
    fd, temp = tempfile.mkstemp(prefix='.' + row_id + '.', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(grant_bytes); stream.flush()
            admission_deadline()
            os.fsync(stream.fileno())
        admission_deadline()
        # Still under owner lease: include temp creation delay in final checks.
        if exists(target) or before != capture(flags, row_id, grant_bytes, legacy):
            raise Refuse('publication-snapshot-race')
        evaluate(before, row_id, adopted=adopted, now=now, writer=True)
        lease.assert_held()
        admission_deadline()
        os.replace(temp, target)
    finally:
        if exists(temp):
            os.unlink(temp)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--flags', required=True); p.add_argument('--id', required=True)
    p.add_argument('--cpus'); p.add_argument('--start'); p.add_argument('--end'); p.add_argument('--regions')
    p.add_argument('--startup', action='store_true')
    p.add_argument("--actual-affinity", action="store_true")
    # No env override or command-line adoption flag. Owner changes versioned constant.
    a = p.parse_args()
    if a.startup:
        if holds_snapshot(a.flags):
            raise Refuse('hold-before-startup-completion-callback')
        return
    if a.actual_affinity:
        a.cpus = ",".join(str(c) for c in sorted(os.sched_getaffinity(0)))
    print(checked(a.flags, a.id, adopted=OWNER_ADOPTED, cpus=a.cpus,
        expected_start=a.start, expected_end=a.end, expected_regions=a.regions))

OWNER_ADOPTED = False
if __name__ == '__main__':
    try:
        main()
    except (Refuse, OSError, ValueError, UnicodeError) as error:
        print('refuse: ' + str(error), file=sys.stderr)
        sys.exit(6)
