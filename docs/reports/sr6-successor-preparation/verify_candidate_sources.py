#!/usr/bin/env python3
"""Verify SR-6 raw candidate source binding; this is not a publication seal.

Checks exact git blob bytes, declared line ranges and candidate hashes against
provided exclusion inventories. Rendering/tokenization, model identity, history
completeness, near-duplicates and source authorship remain independent gates.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

HEX = re.compile(r'[0-9a-f]{64}\Z')
GIT_ID = re.compile(r'[0-9a-f]{40}\Z')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run_git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def verify(candidate, inventories, repo):
    if candidate.get('schema') != 'sr6.raw-candidate-corpus.v1':
        raise ValueError('unexpected candidate schema')
    excluded = set()
    if len(inventories) < 2:
        raise ValueError('both known exposure inventories required')
    for inventory in inventories:
        values = inventory.get('prompt_sha256')
        if not isinstance(values, list) or any(not isinstance(v, str) or not HEX.fullmatch(v) for v in values):
            raise ValueError('invalid exclusion inventory')
        excluded.update(values)
    rows = candidate.get('prompts')
    if not isinstance(rows, list) or len(rows) != 45:
        raise ValueError('expected exactly 45 candidates')
    ids, seeds, digests = set(), set(), set()
    cells = Counter()
    cached = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('invalid row')
        ident, category, window, seed, prompt = (row.get(k) for k in ('id', 'class', 'window', 'seed', 'prompt'))
        if (not isinstance(ident, str) or not ident or category not in ('code','rag','prose')
                or window not in ('w1','w2','w3') or type(seed) is not int or seed < 0
                or not isinstance(prompt, str) or not prompt):
            raise ValueError('invalid candidate identity')
        digest = sha(prompt.encode('utf-8'))
        if ident in ids or seed in seeds or digest in digests or digest in excluded:
            raise ValueError('duplicate or excluded candidate')
        if row.get('prompt_sha256') != digest:
            raise ValueError('candidate hash mismatch')
        ids.add(ident); seeds.add(seed); digests.add(digest); cells[window, category] += 1
        source = row.get('source')
        if not isinstance(source, dict) or source.get('repository') != 'llama.cpp':
            raise ValueError('invalid source')
        rev, path, blob = (source.get(k) for k in ('revision','path','git_blob'))
        if (not isinstance(rev, str) or not GIT_ID.fullmatch(rev)
                or not isinstance(blob, str) or not GIT_ID.fullmatch(blob)
                or not isinstance(path, str) or not path or path.startswith('/')
                or '..' in Path(path).parts or '\x00' in path):
            raise ValueError('invalid git identity')
        key = (rev, path)
        if key not in cached:
            name = rev + ':' + path
            observed_blob = run_git(repo, 'rev-parse', '--verify', name).decode().strip()
            content = run_git(repo, 'show', name)
            cached[key] = (observed_blob, content)
        observed_blob, content = cached[key]
        if observed_blob != blob or source.get('file_sha256') != sha(content):
            raise ValueError('source blob mismatch')
        start, end = source.get('line_start'), source.get('line_end')
        lines = content.decode('utf-8').splitlines()
        if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
            raise ValueError('invalid source range')
        excerpt = '\n'.join(lines[start-1:end]).strip()
        if not excerpt or excerpt not in prompt:
            raise ValueError('source excerpt mismatch')
    if cells != Counter({(w,c): 5 for w in ('w1','w2','w3') for c in ('code','rag','prose')}):
        raise ValueError('unbalanced window partitions')
    return {'status':'SOURCE_CHECK_ONLY_NOT_PUBLICATION_AUTHORITY', 'candidates':len(rows),
            'windows':3, 'per_window_class':5, 'distinct_source_blobs':len(cached),
            'limitations':['exclusion inventories may be incomplete', 'authorship and semantic overlap unproven',
                           'rendering and tokenization not checked', 'model/runtime/sampler not sealed']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('candidate',type=Path); p.add_argument('--inventory',type=Path,action='append',required=True)
    p.add_argument('--repo',type=Path,required=True)
    a=p.parse_args()
    try:
        raw=a.candidate.read_bytes(); inventories=[x.read_bytes() for x in a.inventory]
        out=verify(json.loads(raw),[json.loads(x) for x in inventories],a.repo)
        out['candidate_sha256']=sha(raw)
        out['inventories']=[{'path':str(path),'sha256':sha(data)} for path,data in zip(a.inventory,inventories)]
        print(json.dumps(out,indent=2)); return 0
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status':'UNKNOWN','reason':str(exc)})); return 1

if __name__=='__main__':
    raise SystemExit(main())
