"""Preparation only: bind an ancestor's current official GPU writer lock.

No lock acquisition, scheduler mutation, or inference. Caller must retain this
witness through cleanup and call recheck at every native boundary.
"""
import hashlib
import os
from pathlib import Path
import sys

ORCHESTRATOR = Path('/mnt/raid0/llm/epyc-orchestrator')
LOCK = Path('/mnt/raid0/llm/tmp/gpu_quiet.lock')
SOURCES = ('src/runtime/gpu_quiet_lock.py', 'src/runtime/cpu_region_lock.py',
           'src/runtime/lock_queue.py', 'src/runtime/region_lock_cli.py', 'scripts/region-lock')


def identity(pid):
    root = Path('/proc') / str(pid)
    fields = (root / 'stat').read_text().rsplit(') ', 1)[1].split()
    if fields[0] == 'Z':
        raise ValueError('zombie provider')
    return (root.stat().st_uid, int(fields[19]))


def ancestors():
    found = []
    pid = os.getppid()
    while pid > 1:
        if pid in found:
            raise ValueError('ancestor cycle')
        found.append(pid)
        pid = int((Path('/proc') / str(pid) / 'stat').read_text().rsplit(') ', 1)[1].split()[1])
    return found


def source_digests():
    return {name: hashlib.sha256((ORCHESTRATOR / name).read_bytes()).hexdigest() for name in SOURCES}


def provider():
    # A redirected namespace could prove a private fixture while the hardware
    # lock remains free. Do not accept it as live admission.
    for key in ('ORCHESTRATOR_TMP_DIR', 'ORCHESTRATOR_PATHS_TMP_DIR'):
        if os.environ.get(key) and Path(os.environ[key]) != LOCK.parent:
            raise ValueError('redirected official lock namespace')
    sys.path.insert(0, str(ORCHESTRATOR))
    from src.runtime import gpu_quiet_lock as module
    if Path(module.__file__).resolve() != ORCHESTRATOR / 'src/runtime/gpu_quiet_lock.py':
        raise ValueError('wrong provider module')
    if module.gpu_quiet_lock_path() != LOCK:
        raise ValueError('wrong provider lock path')
    return module


def validate(status, owners, lineage, identities, uid, tag):
    """Refuse fallback/unattributed/shared/foreign/nonancestor observations."""
    if not tag or status.get('path') != str(LOCK) or status.get('held') is not True or status.get('mode') != 'exclusive':
        raise ValueError('exclusive canonical GPU lock absent')
    if not isinstance(owners, dict) or len(owners) != 1 or set(owners.values()) != {'exclusive'}:
        raise ValueError('kernel writer ownership unavailable or ambiguous')
    owner = next(iter(owners))
    if owner not in lineage or owner not in identities or identities[owner][0] != uid:
        raise ValueError('provider is not same-UID captured ancestor')
    rows = status.get('holders')
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError('missing or ambiguous provider attribution')
    row = rows[0]
    if (row.get('schema') != 'epyc.orchestrator.gpu_quiet_holder.v1' or
            row.get('verified') is False or row.get('pid') != owner or
            row.get('start_ticks') != identities[owner][1] or row.get('role') != 'bench' or
            row.get('mode') != 'exclusive' or row.get('lock_path') != str(LOCK) or
            row.get('request_tag') != 'filler-' + tag):
        raise ValueError('provider identity/row binding mismatch')
    return owner, identities[owner]


def capture(row_id, expected_sources):
    if source_digests() != expected_sources:
        raise ValueError('current provider source seal changed')
    module = provider()
    before = LOCK.stat()
    lineage = ancestors()
    ids = {pid: identity(pid) for pid in lineage}
    result = validate(module.holders(), module.lock_owners(LOCK), lineage, ids, os.getuid(), row_id)
    after = LOCK.stat()
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        raise ValueError('lock file replaced during witness')
    if identity(result[0]) != result[1] or source_digests() != expected_sources:
        raise ValueError('provider changed during witness')
    return {'owner': result[0], 'identity': list(result[1]), 'device': after.st_dev,
            'inode': after.st_ino, 'row_id': row_id, 'sources': expected_sources}


def recheck(witness):
    current = capture(witness['row_id'], witness['sources'])
    if current != witness:
        raise ValueError('captured provider writer no longer retained')
    return True
