#!/usr/bin/env python3
"""Report typed CMake cache differences for P1c build recipe review.

This is a byte-value comparison, not recipe parity or build provenance. Paths,
flags, internal entries and toolchain values are included; nothing is ignored.
The caller must independently bind the caches to their source and builds.
"""
import argparse
import json
import re
from pathlib import Path

_ENTRY = re.compile(r'([^:#=][^:=]*):([^=]+)=(.*)\Z')


def parse_cache(text):
    if not isinstance(text, str):
        raise ValueError('cache must be text')
    entries = {}
    for line in text.split('\n'):
        if not line or line.startswith(('#', '//')):
            continue
        match = _ENTRY.fullmatch(line)
        if not match:
            raise ValueError('unsupported cache entry')
        name, kind, value = match.groups()
        if not name or not kind or name in entries:
            raise ValueError('duplicate or invalid cache entry')
        entries[name] = {'type': kind, 'value': value}
    if not entries:
        raise ValueError('empty cache')
    return entries


def compare_caches(base, candidate):
    before, after = parse_cache(base), parse_cache(candidate)
    return {'status': 'UNVERIFIED_COMPARISON', 'differences': [
        {'key': key, 'base': before.get(key), 'candidate': after.get(key)}
        for key in sorted(before.keys() | after.keys()) if before.get(key) != after.get(key)
    ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compare_caches(args.base.read_text(), args.candidate.read_text()), sort_keys=True))
    except (OSError, UnicodeError, ValueError) as exc:
        parser.exit(1, f'REFUSED: {exc}\n')


if __name__ == '__main__':
    main()
