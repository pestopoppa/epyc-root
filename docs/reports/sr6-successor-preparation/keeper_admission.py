#!/usr/bin/env python3
"""Check filler_run15 window/STOP invariants; this is not proof of a held region lock.

The caller must supply an independently implemented ownership check and seal the
expected paths and row identity in the launcher. Environment variables and a grant
file alone are not authority: either can be fabricated. Recheck before each unit.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import time

ROW_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*\Z')
EPOCH = re.compile(r'[0-9]+\Z')


def _epoch(value):
    if not isinstance(value, str) or not EPOCH.fullmatch(value):
        raise ValueError('invalid epoch')
    return int(value)


def _grant_time(value):
    try:
        return int(datetime.strptime(value, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp())
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('invalid grant time') from exc


def _fields(raw):
    try:
        text = raw.decode('ascii')
        pairs = [item.split('=', 1) for item in text.split()]
    except UnicodeDecodeError as exc:
        raise ValueError('invalid grant encoding') from exc
    if not pairs or any(len(p) != 2 or not p[0] or not p[1] for p in pairs):
        raise ValueError('invalid grant fields')
    keys = [p[0] for p in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate grant fields')
    fields = dict(pairs)
    if not all(fields.get(k) for k in ('regions', 'holds', 'start', 'end')):
        raise ValueError('grant fields missing')
    return fields


class KeeperAdmission:
    """Repeated, fail-closed check of a caller-bound filler_run15 grant window.

    `ownership_check` must independently prove the live region claim; it must
    return literal True. These checks do not verify server identity, residency,
    descendant cleanup or stop a request already in flight.
    """
    def __init__(self, *, env, row_id, grant_path, stop_path, ownership_check):
        if not isinstance(row_id, str) or not ROW_ID.fullmatch(row_id):
            raise ValueError('invalid row id')
        if (not isinstance(env, dict) or env.get('FILLER_ID') != row_id or
                not isinstance(grant_path, Path) or not grant_path.is_absolute() or
                grant_path.name != row_id + '.grant' or not isinstance(stop_path, Path) or
                not stop_path.is_absolute() or env.get('FILLER_STOPFILE') != str(stop_path) or
                not callable(ownership_check)):
            raise ValueError('unbound keeper context')
        self.deadline = _epoch(env.get('FILLER_DEADLINE'))
        self.end = _epoch(env.get('FILLER_END'))
        if self.deadline != self.end - 90:
            raise ValueError('filler deadline mismatch')
        self.row_id, self.grant_path, self.stop_path = row_id, grant_path, stop_path
        self.ownership_check = ownership_check
        try:
            if grant_path.is_symlink() or not grant_path.is_file():
                raise ValueError('grant must be a regular file')
            self.grant_bytes = grant_path.read_bytes()
        except OSError as exc:
            raise ValueError('grant unavailable') from exc
        fields = _fields(self.grant_bytes)
        self.start = _grant_time(fields['start'])
        if _grant_time(fields['end']) != self.end or self.start >= self.end:
            raise ValueError('grant window mismatch')
        if 'id' in fields and fields['id'] != row_id:
            raise ValueError('grant row mismatch')

    def __call__(self):
        try:
            now = time.time()
            return (self.start <= now < self.deadline and
                    not os.path.lexists(self.stop_path) and
                    not self.grant_path.is_symlink() and self.grant_path.is_file() and
                    self.grant_path.read_bytes() == self.grant_bytes and
                    self.ownership_check() is True)
        except (OSError, ValueError, RuntimeError):
            return False
