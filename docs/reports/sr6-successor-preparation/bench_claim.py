#!/usr/bin/env python3
"""Verify a live full-host bench claim using pinned guard primitives.

This proves only the sampled lock state, not grant authorization, residency,
or continuous ownership. Seal this source, the guard digest and interpreter;
recheck at every boundary. Never use it as a keeper or grant writer.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import types

_GUARD = Path(__file__).resolve().parents[3] / 'scripts' / 'gitnexus-guard.py'
_HEX = re.compile(r'[0-9a-f]{64}\Z')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*\Z')
_QUADS = ('q0', 'q1', 'q2', 'q3')


def _payload(raw, owner, quadrant, row_id):
    try:
        data = json.loads(raw.decode('utf-8'))
    except (UnicodeError, ValueError) as exc:
        raise ValueError('invalid attribution') from exc
    if not isinstance(data, dict):
        raise ValueError('invalid attribution')
    started = data.get('started_at')
    if (type(data.get('schema_version')) is not int or data['schema_version'] != 1 or
            type(data.get('pid')) is not int or data['pid'] != owner or
            data.get('role') != 'bench' or data.get('region') != quadrant or
            data.get('regions') != list(_QUADS) or data.get('request_tag') != 'filler-' + row_id or
            type(started) not in (int, float) or not math.isfinite(started) or
            not 0 < started <= time.time() + 60):
        raise ValueError('bench attribution mismatch')


def _admit(g, row_id):
    # safe_root and open_identity are the pinned production guard primitives;
    # they fix the canonical root and reject symlinks, hard links and swaps.
    g.EXPECTED_ROOT = g.safe_root()
    if os.environ.get('ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT', '').strip().lower() not in {'1', 'true', 'yes', 'on'}:
        raise ValueError('cross-role locks not enabled')
    anc, kernel = g.ancestors(), g.proc_lock_owners()
    identities = []
    paths = [(f'cpu_region.{role}.{q}.lock', role, q) for role in ('GLOBAL', 'bench') for q in _QUADS]
    paths.append(('gpu_quiet.lock', 'quiet', None))
    for name, role, q in paths:
        path = os.path.join(g.LOCK_ROOT, name)
        identity, data = g.open_identity(path)
        candidates = kernel.get(g.dev_inode(identity), set()).intersection(anc)
        if len(candidates) != 1:
            raise ValueError('lock lacks one ancestor write flock')
        owner = next(iter(candidates))
        if owner == os.getpid() or anc[owner][1] != os.getuid():
            raise ValueError('invalid claim owner')
        if role == 'bench':
            _payload(data, owner, q, row_id)
        identities.append((path, identity, owner, anc[owner][0], role, q))
    if len({i[1] for i in identities}) != 9 or len({i[2] for i in identities}) != 1:
        raise ValueError('claim owner or lock inode mismatch')
    owner = identities[0][2]
    proc, anc2, kernel2 = g.proc_stat(owner), g.ancestors(), g.proc_lock_owners()
    if owner not in anc2 or anc2[owner] != anc[owner] or proc[1] != anc[owner][0] or proc[2] != os.getuid():
        raise ValueError('claim owner changed')
    for path, prior, expected, _start, role, q in identities:
        current, data = g.open_identity(path)
        if current != prior or expected not in kernel2.get(g.dev_inode(current), set()):
            raise ValueError('lock changed or released')
        if role == 'bench':
            _payload(data, owner, q, row_id)
    return True


class FullHostBenchClaim:
    """Recheck q0-q3 GLOBAL+bench and exclusive gpu-quiet ancestor flocks."""
    def __init__(self, row_id, guard_sha256):
        if not isinstance(row_id, str) or not _ID.fullmatch(row_id) or not isinstance(guard_sha256, str) or not _HEX.fullmatch(guard_sha256):
            raise ValueError('row id and sealed guard digest required')
        self.row_id, self.guard_sha256 = row_id, guard_sha256

    def __call__(self):
        try:
            fd = os.open(_GUARD, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            with os.fdopen(fd, 'rb') as stream:
                raw = stream.read(131073)
            if len(raw) > 131072 or hashlib.sha256(raw).hexdigest() != self.guard_sha256:
                return False
            guard = types.ModuleType('sealed_gitnexus_guard')
            exec(compile(raw, '<sealed-guard>', 'exec'), guard.__dict__)
            return _admit(guard, self.row_id) is True
        except Exception:
            return False
