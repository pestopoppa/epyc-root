#!/usr/bin/env python3
"""Owner-run, bounded HELMET archive restore; no inference and no shared data writes."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tarfile
import time
import urllib.request

GIB = 1 << 30
ROOT = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch/helmet-data')
URL = 'https://huggingface.co/datasets/princeton-nlp/HELMET/resolve/bc560a6b8165c696ad4bc3d1612c64b5794ba328/data.tar.gz'
SIZE = 11271916108
SHA = '9d693981aa3c065b8b2ff82ddf946141cdc4ece4524f18bff6f3fbd2a86982d9'
FILES = {'nq-dev-multikilt_1000_k1000_dep6.jsonl', 'nq-train-multikilt_1000_k3_dep6.jsonl',
         'hotpotqa-dev-multikilt_1000_k1000_dep3.jsonl', 'hotpotqa-train-multikilt_1000_k3_dep3.jsonl'}

def free():
    s = os.statvfs(ROOT.parent)
    return s.f_bavail * s.f_frsize

def used():
    return sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())

def main():
    a = argparse.ArgumentParser()
    a.add_argument('--budget-gib', required=True, type=float)
    a.add_argument('--deadline-epoch', required=True, type=int)
    a.add_argument('--dry-run', action='store_true')
    o = a.parse_args()
    if not math.isfinite(o.budget_gib) or o.budget_gib < SIZE / GIB or free() - o.budget_gib * GIB < 150 * GIB:
        raise SystemExit('REFUSED: owner budget too small for archive or violates 150 GiB floor')
    if o.deadline_epoch - time.time() < 300:
        raise SystemExit('REFUSED: insufficient remaining window')
    print(json.dumps({'url': URL, 'archive_bytes': SIZE, 'archive_sha256': SHA, 'files': sorted(FILES),
                      'budget_gib': o.budget_gib, 'free_gib': free()/GIB, 'dry_run': o.dry_run}), flush=True)
    if o.dry_run:
        return
    ROOT.mkdir(exist_ok=True)
    part = ROOT / 'data.tar.gz.part'
    offset = part.stat().st_size if part.exists() else 0
    if offset > SIZE:
        raise SystemExit('REFUSED: partial archive exceeds expected size')
    if offset < SIZE:
        req = urllib.request.Request(URL, headers={'Range': f'bytes={offset}-'} if offset else {})
        with urllib.request.urlopen(req, timeout=60) as response:
            if offset and (response.status != 206 or not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-')):
                raise SystemExit('REFUSED: server did not honor resume range')
            with part.open('ab') as out:
                while True:
                    if time.time() >= o.deadline_epoch - 120:
                        raise SystemExit('REFUSED: deadline, partial archive retained')
                    if free() < 150*GIB + (2 << 20) or used() + (1 << 20) > o.budget_gib*GIB:
                        raise SystemExit('REFUSED: output budget or disk floor, partial retained')
                    block = response.read(1 << 20)
                    if not block:
                        break
                    out.write(block)
    if part.stat().st_size != SIZE:
        raise SystemExit('REFUSED: incomplete archive, partial retained')
    h = hashlib.sha256()
    with part.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    if h.hexdigest() != SHA:
        raise SystemExit('REFUSED: archive digest mismatch, retained')
    selected = {}
    with tarfile.open(part, 'r:gz') as archive:
        for member in archive:
            if time.time() >= o.deadline_epoch - 120:
                raise SystemExit('REFUSED: deadline while inspecting archive')
            name = member.name.lstrip('./')
            if not name.startswith('data/kilt/') or name.rsplit('/', 1)[-1] not in FILES:
                continue
            leaf = name.rsplit('/', 1)[-1]
            if not member.isfile() or leaf in selected:
                raise SystemExit('REFUSED: duplicate or non-regular selected archive entry')
            h = hashlib.sha256(); count = 0
            src = archive.extractfile(member)
            while True:
                if time.time() >= o.deadline_epoch - 120:
                    raise SystemExit('REFUSED: deadline during member inventory')
                block = src.read(1 << 20)
                if not block: break
                h.update(block); count += len(block)
            if count != member.size:
                raise SystemExit('REFUSED: member size mismatch during inventory')
            selected[leaf] = {'size': count, 'sha256': h.hexdigest()}
    if set(selected) != FILES:
        raise SystemExit(f'REFUSED: missing selected archive files {sorted(FILES-set(selected))}')
    target = ROOT / 'data' / 'kilt'
    replaceable = 0
    missing_bytes = 0
    for leaf in FILES:
        dst, temp = target/leaf, target/(leaf + '.part')
        if dst.is_symlink() or temp.is_symlink():
            raise SystemExit('REFUSED: symlink in selected output')
        if dst.exists():
            h = hashlib.sha256()
            with dst.open('rb') as f:
                for block in iter(lambda: f.read(1 << 20), b''): h.update(block)
            if dst.stat().st_size != selected[leaf]['size'] or h.hexdigest() != selected[leaf]['sha256']:
                raise SystemExit(f'REFUSED: existing final differs from archive: {leaf}')
        if dst.exists(): replaceable += dst.stat().st_size
        else:
            missing_bytes += selected[leaf]['size']
            if temp.exists(): replaceable += temp.stat().st_size
    needed = sum(v['size'] for v in selected.values())
    if used() - replaceable + needed > o.budget_gib*GIB or free() - missing_bytes < 150*GIB:
        raise SystemExit('REFUSED: total selected members exceed output budget or floor')
    target.mkdir(parents=True, exist_ok=True)
    seen = set()
    with tarfile.open(part, 'r:gz') as archive:
        for member in archive:
            name = member.name.lstrip('./')
            if not name.startswith('data/kilt/') or name.rsplit('/', 1)[-1] not in FILES:
                continue
            leaf = name.rsplit('/', 1)[-1]
            if not member.isfile() or leaf in seen:
                raise SystemExit('REFUSED: duplicate or non-regular selected archive entry')
            seen.add(leaf)
            dst = target / leaf
            if dst.exists():
                continue
            temp = target / (leaf + '.part')
            src = archive.extractfile(member)
            h = hashlib.sha256(); count = 0
            with temp.open('wb', buffering=0) as out:
                while True:
                    if time.time() >= o.deadline_epoch - 120 or free() < 150*GIB + (2 << 20):
                        raise SystemExit('REFUSED: deadline or floor while extracting; partial retained')
                    block = src.read(1 << 20)
                    if not block:
                        break
                    if used() + len(block) > o.budget_gib*GIB or free() - len(block) < 150*GIB:
                        raise SystemExit('REFUSED: output budget or floor while extracting')
                    out.write(block)
                    h.update(block); count += len(block)
                os.fsync(out.fileno())
            if count != selected[leaf]['size'] or h.hexdigest() != selected[leaf]['sha256']:
                raise SystemExit(f'REFUSED: extracted member mismatch: {leaf}')
            os.replace(temp, dst)
    if seen != FILES:
        raise SystemExit(f'REFUSED: missing selected archive files {sorted(FILES-seen)}')
    receipt = {'archive_sha256': SHA, 'archive_revision': 'bc560a6b8165c696ad4bc3d1612c64b5794ba328',
               'files': {f: selected[f] for f in sorted(FILES)}}
    (ROOT / 'RESTORE_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')

if __name__ == '__main__':
    main()
