#!/usr/bin/env python3
"""Continue an AM-PORT-2 checkpoint without replaying completed item/arm units."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path


def checked_jsonl(path, expected_sha):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError('checkpoint digest changed')
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    keys = [(r['item'], r['arm']) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate checkpoint units')
    if any(not r.get('ok') or not r.get('aligned') or r['arm'] not in ('FULL', 'L4', 'EA')
           or not 0 <= r['item'] < 60 for r in rows):
        raise ValueError('invalid checkpoint unit')
    return rows


def complete(path):
    try:
        r = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return False
    v = str(r.get('verdict', ''))
    return bool(r.get('complete') and not r.get('smoke') and
                (v == 'L4_KEEP' or v.startswith('L4_BELOW_EA(') or v.startswith('FUTILITY_')))


def configure(m, root, contract):
    """Keep the tested server/protocol; change only input/output and resume custody."""
    checkpoint = checked_jsonl(contract['checkpoint'], contract['checkpoint_sha256'])
    original_units = m.units
    m.ROW = contract['row']
    m.OUT = str(root / ('out-smoke' if m.SMOKE else 'out'))
    m.LOGS = m.OUT + '/logs'
    m.RES = m.OUT + '/results.jsonl'
    m.RESULT = m.OUT + '/RESULT.json'
    m.STOPF = os.environ.get('FILLER_STOPFILE', str(root / 'STOP'))
    m.units = lambda: checkpoint + original_units()
    # All 60 seeded items and the small smoke item were tokenized before publication.
    m.get_item = lambda i: json.loads((root / 'inputs' / f'{i}.json').read_text())
    m.make_item = lambda i: json.loads((root / 'inputs' / 'smoke.json').read_text())
    m.step_source = lambda: True  # original source/build are retained and content-pinned in contract
    m.step_build = lambda: {'ok': True, 'stage': 'retained', 'proof': contract['build_sha256']}
    return m


def main():
    import sys
    root = Path(sys.argv[1]).resolve()
    if len(sys.argv) > 2 and sys.argv[2] == '--complete':
        raise SystemExit(0 if complete(root / 'out/RESULT.json') else 1)
    contract = json.loads((root / 'inputs/contract.json').read_text())
    for path, expected in contract['files'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError(f'input or binary changed: {path}')
    spec = importlib.util.spec_from_file_location('am_port2_original', contract['job'])
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    configure(m, root, contract).main()


if __name__ == '__main__':
    main()
