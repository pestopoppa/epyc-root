#!/usr/bin/env python3
"""Check producer-recorded batch-row binding shape; not token attribution."""
import argparse
import json
from pathlib import Path
from snapshot_validate import validate


def audit(client_bytes, event_bytes):
    base = validate(client_bytes, event_bytes)
    checked = 0
    for line in event_bytes.decode('utf-8').splitlines():
        event = json.loads(line)
        if event['kind'] != 'decode_begin':
            continue
        data = event['data']
        n = data.get('input_rows')
        bindings = data.get('slot_bindings')
        if type(n) is not int or n < 0 or not isinstance(bindings, list):
            raise ValueError('invalid input_rows or slot_bindings')
        seen_slots = set()
        for binding in bindings:
            if not isinstance(binding, dict): raise ValueError('invalid binding')
            task, slot, rows = (binding.get(k) for k in ('task_id', 'slot_id', 'batch_rows'))
            if type(task) is not int or task < 0 or type(slot) is not int or slot < 0 or slot in seen_slots:
                raise ValueError('invalid or duplicated slot identity')
            seen_slots.add(slot)
            if not isinstance(rows, list) or not rows or any(type(x) is not int or x < 0 or x >= n for x in rows):
                raise ValueError('missing or out-of-range batch row')
            if rows != sorted(set(rows)): raise ValueError('duplicate or unordered batch rows')
            checked += 1
    if not checked: raise ValueError('no slot bindings')
    return {'status': 'BATCH_ROW_SHAPE_CONSISTENT_ONLY', 'bindings_checked': checked,
            'events_sha256': base['events_sha256'], 'client_sha256': base['client_sha256'],
            'row_sequence_identity': 'NOT_ASSESSED', 'token_attribution': 'NOT_ASSESSED',
            'same_run_provenance': 'NOT_ASSESSED', 'profiler_alignment': 'NOT_ASSESSED'}


def main():
    p=argparse.ArgumentParser(); p.add_argument('client', type=Path); p.add_argument('events', type=Path)
    a=p.parse_args()
    try: out=audit(a.client.read_bytes(), a.events.read_bytes())
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as e:
        print(json.dumps({'status':'INVALID','error':str(e)})); raise SystemExit(1)
    print(json.dumps(out, sort_keys=True))

if __name__ == '__main__': main()
