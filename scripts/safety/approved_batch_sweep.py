#!/usr/bin/env python3
"""Opt-in exact-batch early sweep; receipt records operator authorization.

A receipt is an attestation, not a cryptographic signature. Caller must verify it
was issued by the operator. No caller may supply the production trash root.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

TRASH = Path('/mnt/raid0/llm/.trash')
AUDIT = Path('/workspace/logs/safety_audit.log')
APPROVED_SOURCE_SHA256 = 'f4c7f90d69661011026c52adf5c3bb0c61ecbf42f56d967770487b6e34783291'
WORKTREE_REFS = {
    '/mnt/raid0/llm/tmp/batch-20261024/wt-research-d': ('docs-batch-20261024-research-d', 'b57ab3154e8ecce2a2c21e044669964a015d1434'),
    '/mnt/raid0/llm/tmp/batch-20261024/wt-epyc-inference-research-c': ('docs-batch-20261024-epyc-inference-research-c', '464ed0aaf2c1832fa233de1e4337cd513d648a6f'),
}
RESEARCH = '/mnt/raid0/llm/epyc-inference-research'
WORKTREE_IGNORED = {
    '/mnt/raid0/llm/tmp/batch-20261024/wt-research-d': {
        '!! scripts/voice/turn_taking/__pycache__/',
        '!! scripts/voice/turn_taking/tests/__pycache__/',
    },
    '/mnt/raid0/llm/tmp/batch-20261024/wt-epyc-inference-research-c': set(),
}


def verify_worktree_clean(path, source):
    output = subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain=v1', '--ignored=matching', '--untracked-files=all'], text=True)
    if not set(output.splitlines()).issubset(WORKTREE_IGNORED[source]):
        raise ValueError('worktree contains unexpected tracked, untracked or ignored data')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sweep(batch, source_manifest, mapping_path, receipt_path, trash_root=TRASH, audit=AUDIT,
          expected_source_sha256=APPROVED_SOURCE_SHA256):
    batch = Path(batch)
    root = Path(trash_root).resolve(strict=True)
    if batch.is_symlink() or batch.parent.resolve(strict=True) != root or not batch.name.startswith('kpf18-approved-'):
        raise ValueError('batch must be a direct non-symlink kpf18-approved child of trash')
    if batch.resolve(strict=True) != root / batch.name or not batch.is_dir():
        raise ValueError('invalid batch directory')
    source_manifest, mapping_path, receipt_path = map(Path, (source_manifest, mapping_path, receipt_path))
    if any(p.is_symlink() or not p.is_file() for p in (source_manifest, mapping_path, receipt_path)):
        raise ValueError('manifest and receipt must be regular non-symlink files')
    receipt = json.loads(receipt_path.read_text())
    mapping = json.loads(mapping_path.read_text())
    receipt_keys = {'operator_approved', 'early_hold_override', 'keep_override', 'action_checks_passed',
                    'approval_reference', 'source_manifest_sha256', 'snapshot_sha256', 'mapping_sha256', 'batch'}
    if set(receipt) != receipt_keys or set(mapping) != {'entries'}:
        raise ValueError('unknown receipt or mapping metadata')
    source_sha, mapping_sha = digest(source_manifest), digest(mapping_path)
    if source_sha != expected_source_sha256:
        raise ValueError('source manifest is not the reviewed KPF18 manifest')
    if (receipt.get('operator_approved') is not True or receipt.get('early_hold_override') is not True
            or receipt.get('keep_override') is not True or receipt.get('action_checks_passed') is not True
            or not isinstance(receipt.get('approval_reference'), str) or not receipt.get('approval_reference')
            or receipt.get('source_manifest_sha256') != source_sha
            or receipt.get('mapping_sha256') != mapping_sha or receipt.get('batch') != str(batch)
            or not isinstance(receipt.get('snapshot_sha256'), str) or len(receipt['snapshot_sha256']) != 64):
        raise ValueError('explicit operator receipt does not bind this batch and both manifests')
    lines = source_manifest.read_text().splitlines()
    sources = [line.split('\t', 1)[1] for line in lines]
    entries = mapping['entries']
    if not sources or len(sources) != len(set(sources)) or len(entries) != len(sources):
        raise ValueError('duplicate source or wrong count')
    if {e['source'] for e in entries} != set(sources):
        raise ValueError('mapping differs from approved source manifest')
    names = [e['trash_name'] for e in entries]
    if len(set(names)) != len(names) or any(not n or n in ('.', '..') or '/' in n for n in names):
        raise ValueError('invalid or duplicate trash name')
    if set(os.listdir(batch)) != set(names):
        raise ValueError('batch contains missing or extra entries')
    # All validation before the first deletion. Recheck each inode immediately
    # before deletion; partial completion is recorded if a later recheck fails.
    for e in entries:
        if set(e) - {'source', 'trash_name', 'payload_name', 'device', 'inode', 'branch'}:
            raise ValueError('unknown entry metadata')
        if 'branch' in e and e['source'] not in WORKTREE_REFS:
            raise ValueError('unexpected branch metadata')
        if e['source'] in WORKTREE_REFS:
            name, commit = WORKTREE_REFS[e['source']]
            expected = {'repository': RESEARCH,
                        'ref': 'refs/heads/' + name, 'commit': commit}
            if e.get('branch') != expected:
                raise ValueError('worktree branch custody missing or changed')
        container = batch / e['trash_name']
        payload_name = e['payload_name']
        if (container.is_symlink() or not container.is_dir() or not payload_name
                or payload_name in ('.', '..') or '/' in payload_name
                or set(os.listdir(container)) != {payload_name}):
            raise ValueError('invalid isolated trash container')
        payload = container / payload_name
        st = payload.lstat()
        if payload.is_symlink() or (st.st_dev, st.st_ino) != (e['device'], e['inode']):
            raise ValueError('entry symlink or identity mismatch')
        if 'branch' in e:
            verify_worktree_clean(payload, e['source'])
            branch = e['branch']
            got = subprocess.check_output(['git', '-C', branch['repository'], 'rev-parse', '--verify', branch['ref']], text=True).strip()
            if got != branch['commit']:
                raise ValueError('worktree branch is not preserved')
    fd = os.open(batch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for e in entries:
            container = batch / e['trash_name']
            payload = container / e['payload_name']
            st = payload.lstat()
            if (st.st_dev, st.st_ino) != (e['device'], e['inode']):
                raise ValueError('entry identity changed during sweep')
            event = {'cat': 'TRASH_SWEEP_APPROVED_BATCH', 'source': e['source'], 'batch': str(batch),
                     'entry': e['trash_name'], 'approval_reference': receipt['approval_reference'],
                     'source_manifest_sha256': source_sha, 'mapping_sha256': mapping_sha}
            with open(audit, 'a', encoding='utf-8') as log:
                log.write(json.dumps({**event, 'event': 'purge-intent'}) + '\n'); log.flush(); os.fsync(log.fileno())
            if 'branch' in e:
                verify_worktree_clean(payload, e['source'])
                branch = e['branch']
                got = subprocess.check_output(['git', '-C', branch['repository'], 'rev-parse', '--verify', branch['ref']], text=True).strip()
                if got != branch['commit']:
                    raise ValueError('worktree branch changed during sweep')
                subprocess.run(['git', '-C', e['branch']['repository'], 'worktree', 'remove', '--force', str(payload)], check=True)
                os.rmdir(e['trash_name'], dir_fd=fd)
            else:
                shutil.rmtree(e['trash_name'], dir_fd=fd)
            with open(audit, 'a', encoding='utf-8') as log:
                log.write(json.dumps({**event, 'event': 'purge-complete'}) + '\n'); log.flush(); os.fsync(log.fileno())
    finally:
        os.close(fd)


def main():
    if len(sys.argv) != 5:
        raise SystemExit('usage: trash-sweep.sh --approved-batch BATCH SOURCE-MANIFEST MAPPING RECEIPT')
    try:
        sweep(*sys.argv[1:])
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as e:
        print('REFUSED:', e, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
