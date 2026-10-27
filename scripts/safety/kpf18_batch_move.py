#!/usr/bin/env python3
"""Exact KPF18 trash staging. Default is dry-run; --apply requires owner receipt."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from approved_batch_sweep import APPROVED_SOURCE_SHA256, WORKTREE_REFS, verify_worktree_clean

TRASH = Path('/mnt/raid0/llm/.trash')
GUARD = Path(__file__).with_name('guarded_rm.sh')
RESEARCH = '/mnt/raid0/llm/epyc-inference-research'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if len(sys.argv) not in (4, 6) or (len(sys.argv) == 6 and sys.argv[4] != '--apply'):
        raise SystemExit('usage: kpf18_batch_move.py MANIFEST SNAPSHOT BATCH [--apply OPERATOR-RECEIPT]')
    manifest, snapshot, batch = map(Path, sys.argv[1:4]); applying = len(sys.argv) == 6
    snap = json.loads(snapshot.read_text())
    if sha(manifest) != APPROVED_SOURCE_SHA256 or snap.get('source_manifest_sha256') != APPROVED_SOURCE_SHA256:
        raise SystemExit('REFUSED: manifest identity mismatch')
    sources = [line.split('\t', 1)[1] for line in manifest.read_text().splitlines()]
    entries = snap['entries']
    if set(snap) != {'source_manifest_sha256', 'entries'} or any(set(e) != {'source', 'device', 'inode'} for e in entries):
        raise SystemExit('REFUSED: unknown snapshot metadata')
    if [e['source'] for e in entries] != sources or len(set(sources)) != len(sources):
        raise SystemExit('REFUSED: snapshot differs from manifest')
    if batch.parent.resolve(strict=True) != TRASH.resolve(strict=True) or not batch.name.startswith('kpf18-approved-') or batch.exists() or batch.is_symlink():
        raise SystemExit('REFUSED: batch must be a new isolated trash child')
    for e in entries:
        p = Path(e['source'])
        if p.is_symlink() or not p.is_dir() or str(p.resolve(strict=True)) != e['source']:
            raise SystemExit('REFUSED: source path changed')
        st = p.stat()
        if (st.st_dev, st.st_ino) != (e['device'], e['inode']):
            raise SystemExit('REFUSED: source inode changed')
        if e['source'] in WORKTREE_REFS:
            verify_worktree_clean(p, e['source'])
            name, commit = WORKTREE_REFS[e['source']]
            got = subprocess.check_output(['git', '-C', RESEARCH, 'rev-parse', '--verify', 'refs/heads/' + name], text=True).strip()
            if got != commit: raise SystemExit('REFUSED: branch custody changed')
    if not applying:
        print('DRY RUN: validated %d sources; no moves performed' % len(entries)); return
    receipt = json.loads(Path(sys.argv[5]).read_text())
    if set(receipt) != {'operator_approved', 'early_hold_override', 'keep_override', 'action_checks_passed', 'approval_reference', 'source_manifest_sha256', 'snapshot_sha256', 'batch'}:
        raise SystemExit('REFUSED: unknown or missing receipt metadata')
    if (receipt.get('operator_approved') is not True or receipt.get('early_hold_override') is not True
        or receipt.get('keep_override') is not True or receipt.get('action_checks_passed') is not True
        or not isinstance(receipt.get('approval_reference'), str) or not receipt.get('approval_reference') or receipt.get('source_manifest_sha256') != APPROVED_SOURCE_SHA256
        or receipt.get('snapshot_sha256') != sha(snapshot) or receipt.get('batch') != str(batch)):
        raise SystemExit('REFUSED: operator receipt or action-boundary checks missing')
    batch.mkdir(mode=0o700)
    journal = Path(str(batch) + '.journal.jsonl')
    def record_event(event):
        with journal.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event) + '\n'); stream.flush(); os.fsync(stream.fileno())
    mapped = []
    for index, e in enumerate(entries):
        source = Path(e['source']); st = source.stat()
        if source.is_symlink() or (st.st_dev, st.st_ino) != (e['device'], e['inode']):
            raise SystemExit('REFUSED: source changed; partial batch retained')
        container = batch / ('item-%02d' % index); container.mkdir(mode=0o700)
        record = dict(e, trash_name=container.name)
        record_event({'event': 'move-intent', **record})
        if e['source'] in WORKTREE_REFS:
            name, commit = WORKTREE_REFS[e['source']]; payload = container / 'worktree'
            verify_worktree_clean(source, e['source'])
            subprocess.run(['git', '-C', RESEARCH, 'worktree', 'move', str(source), str(payload)], check=True)
            record['branch'] = {'repository': RESEARCH, 'ref': 'refs/heads/' + name, 'commit': commit}
        else:
            subprocess.run(['bash', str(GUARD), str(source)], env={**os.environ, 'TRASH_ROOT': str(container)}, check=True)
            children = list(container.iterdir())
            if len(children) != 1: raise SystemExit('REFUSED: unexpected trash entries; partial batch retained')
            payload = children[0]
        st = payload.lstat()
        if payload.is_symlink() or (st.st_dev, st.st_ino) != (e['device'], e['inode']):
            raise SystemExit('REFUSED: moved identity mismatch; partial batch retained')
        record['payload_name'] = payload.name; mapped.append(record)
        record_event({'event': 'move-complete', **record})
    mapping = Path(str(batch) + '.mapping.json')
    mapping.write_text(json.dumps({'entries': mapped}, indent=2) + '\n')
    derived = Path(str(batch) + '.receipt.json')
    derived.write_text(json.dumps({**receipt, 'mapping_sha256': sha(mapping)}, indent=2) + '\n')
    print('TRASHED ONLY; no purge. mapping=%s receipt=%s' % (mapping, derived))


if __name__ == '__main__': main()
