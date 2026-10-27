#!/usr/bin/env python3
"""Read-only preflight for reviewed KPF18 paths; never moves or deletes data."""
import hashlib
import json
import os
from pathlib import Path
import sys

EXPECTED = 'f4c7f90d69661011026c52adf5c3bb0c61ecbf42f56d967770487b6e34783291'


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: kpf18_batch_prepare.py REVIEW-MANIFEST.tsv')
    path = Path(sys.argv[1]); raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise SystemExit('REFUSED: source manifest hash differs from reviewed list')
    result = []
    for line in raw.decode().splitlines():
        _, name = line.split('\t', 1); p = Path(name)
        if p.is_symlink() or not p.is_dir() or str(p.resolve(strict=True)) != name:
            raise SystemExit('REFUSED: missing, symlinked or aliased path: ' + name)
        st = p.stat(); result.append({'source': name, 'device': st.st_dev, 'inode': st.st_ino})
    print(json.dumps({'source_manifest_sha256': EXPECTED, 'entries': result}, indent=2))


if __name__ == '__main__': main()
