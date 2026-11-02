#!/usr/bin/env python3
"""Prepare the acceptance-gated EffiBench-X subset from a dataset JSON export."""
import argparse
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
EXCLUDED = {'leetcode_3264_maximum-points-after-enemy-battles',
            'leetcode_3451_string-compression-iii'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path, help='JSON array exported from test split')
    parser.add_argument('output', type=Path, help='new, non-existing dataset directory')
    args = parser.parse_args()
    expected = set(json.loads((HERE / 'dated-308.json').read_text()))
    rows = json.loads(args.dataset.read_text())
    if not isinstance(rows, list):
        parser.error('dataset must be a JSON array')
    selected = {}
    for row in rows:
        if row.get('release_timestamp') is None:
            continue
        name = f"{row['source']}_{row['id']}_{row['title_slug']}"
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in selected:
            raise ValueError(f'invalid or duplicate problem name: {name!r}')
        selected[name] = row
    if len(expected) != 308 or len(selected) != 308 or set(selected) != expected:
        raise ValueError(f'DATED cohort mismatch: missing={sorted(expected-set(selected))}, extra={sorted(set(selected)-expected)}')
    if not EXCLUDED <= expected:
        raise ValueError('exclusions absent from cohort')
    args.output.mkdir(parents=True, exist_ok=False)
    for name in sorted(expected - EXCLUDED):
        (args.output / f'{name}.json').write_text(json.dumps(selected[name], indent=2) + '\n')
    print(f'Wrote {len(expected - EXCLUDED)} problems; excluded {sorted(EXCLUDED)}')


if __name__ == '__main__':
    main()
