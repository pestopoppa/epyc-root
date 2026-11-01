#!/usr/bin/env python3
"""Verify the original local evidence referenced by the retained audit."""
import hashlib
import json
from pathlib import Path

data = json.loads(Path(__file__).with_name('audit.json').read_text())
files = {}
def visit(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
            prior = files.setdefault(value['path'], value['sha256'])
            if prior != value['sha256']:
                raise ValueError('conflicting digest: ' + value['path'])
        for item in value.values():
            visit(item)
    elif isinstance(value, list):
        for item in value:
            visit(item)
visit(data)
for name, expected in files.items():
    observed = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    if observed != expected:
        raise ValueError('missing or changed evidence: ' + name)
if data['overall'] != {'11': {'complete': 25, 'unknown': 0}, '12': {'complete': 25, 'unknown': 0}}:
    raise ValueError('unexpected shard disposition')
print(f'{len(files)} referenced files match; s11 and s12 each have 25 completed pages')
