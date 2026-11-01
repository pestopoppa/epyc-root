#!/usr/bin/env python3
"""Produce six read-only recipe snapshots; placeholders deliberately unlaunchable."""
import json
from pathlib import Path

from recipe_snapshot import ARCHITECT, FRONTDOOR, make

root = Path(__file__).resolve().parent
for shape, source, port in (
    ('frontdoor_mtp', FRONTDOOR, 19070),
    ('architect_dflash', ARCHITECT, 19083),
):
    for np, spec in ((1, 'on'), (4, 'on'), (4, 'off')):
        path = root / f'{shape.upper()}-NP{np}-{spec.upper()}-STAGED.json'
        record = make(shape, source, '/REPLACE_WITH_ACCEPTED_IMAGE/llama-server', port,
                      str(root / 'slot-saves' / shape), np, spec)
        data = json.dumps(record, indent=2) + '\n'
        if path.exists() and path.read_text() != data:
            raise SystemExit(f'refuse to overwrite a different staged recipe: {path}')
        path.write_text(data)
        print(path.name, record['n_ctx_total'], record['n_ctx_per_slot'], record['backend'])
