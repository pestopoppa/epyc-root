#!/usr/bin/env python3
"""Cheap custody check of a snapshot fully verified before the compute grant.

Root is trusted. This is not protection against privileged writers. Preparation
removes write bits recursively only after manifest verification; the root-owned
run directory protects snapshot and provenance directory entries.
"""
import json
from pathlib import Path
import sys
from prepare import COMMIT, ARCHIVE_SHA, MANIFEST_SHA


def protected(path):
    info = path.lstat()
    if path.is_symlink() or info.st_uid != 0 or info.st_mode & 0o222:
        raise ValueError(f'unprotected custody path: {path}')
    return info


def check(run):
    run = Path(run)
    if run.resolve(strict=True) != run:
        raise ValueError('noncanonical run')
    protected(run.parent)
    protected(run)
    for name in ('source.tar', 'tree-manifest.json', 'source-provenance.json'):
        protected(run/name)
    info = protected(run/'src')
    p = json.loads((run / 'source-provenance.json').read_text())
    if p != dict(source_commit=COMMIT, archive_sha256=ARCHIVE_SHA,
                 manifest_sha256=MANIFEST_SHA, method='git archive from pinned commit',
                 source_dir=str(run / 'src'), run_dir=str(run),
                 source_device=info.st_dev, source_inode=info.st_ino,
                 protection='root-owned tree; all write bits removed after verification'):
        raise ValueError('source provenance mismatch')


if __name__ == '__main__':
    check(sys.argv[1])
