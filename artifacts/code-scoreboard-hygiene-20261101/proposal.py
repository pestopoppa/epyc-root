#!/usr/bin/env python3
"""Produce a proposed scoreboard copy; never modifies the input or running process."""
import hashlib
import pathlib
import sys

BASE = 'f7438930a8a0384ceb96120af86524266adcae31dfffebc7977dc7a9eaa4eb0d'
OLD = '                if not ticked_at_base(f, key): tn += 1\n'
NEW = "                if not re.search(r'\\[closure:\\s*hygiene\\]', full, re.I) and not ticked_at_base(f, key): tn += 1\n"

def propose(data):
    if hashlib.sha256(data).hexdigest() != BASE:
        raise ValueError('source SHA-256 differs from reviewed base')
    source = data.decode('utf-8')
    if source.count(OLD) != 1:
        raise ValueError('expected unique daily count line')
    return source.replace(OLD, NEW).encode('utf-8')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: proposal.py SOURCE NEW_OUTPUT (output must not exist)')
    source, output = map(pathlib.Path, sys.argv[1:])
    data = propose(source.read_bytes())
    with output.open('xb') as f:
        f.write(data)
