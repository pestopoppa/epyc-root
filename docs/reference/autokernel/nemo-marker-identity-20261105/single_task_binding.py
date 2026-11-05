#!/usr/bin/env python3
"""Check producer-reported single-task batch bindings, not token attribution."""
import argparse
import json
from pathlib import Path
from clock_snapshot import validate as validate_snapshot
from validate_events import _unique_object


def check(client_bytes, event_bytes, marker_bytes):
    result = validate_snapshot(client_bytes, event_bytes, marker_bytes)
    client = json.loads(client_bytes, object_pairs_hook=_unique_object)
    if len(client['requests']) != 1:
        raise ValueError('single-task check requires exactly one request')
    rid = client['requests'][0]['request_id']
    records = [json.loads(line, object_pairs_hook=_unique_object)
               for line in event_bytes.decode('utf-8').splitlines()]
    joins = [(i, e['data']) for i,e in enumerate(records) if e['kind'] == 'request_join']
    if len(joins) != 1 or joins[0][1]['request_id'] != rid:
        raise ValueError('expected exactly one matching native join')
    join_index, data = joins[0]; task = data['task_id']; checked = 0
    for i,event in enumerate(records):
        if event['kind'] != 'decode_begin': continue
        data = event['data']; bindings = data['slot_bindings']; n = data['input_rows']
        if i <= join_index:
            raise ValueError('decode precedes request join')
        if type(n) is not int or n <= 0 or len(bindings) != 1:
            raise ValueError('decode is empty or not isolated to one binding')
        binding = bindings[0]
        if binding['task_id'] != task or binding['batch_rows'] != list(range(n)):
            raise ValueError('task identity or complete input row coverage mismatch')
        checked += 1
    if not checked: raise ValueError('no matched decode')
    return {'status':'SINGLE_TASK_BINDING_SHAPE_CONSISTENT_ONLY',
            'checked_decodes':checked, 'joined_task_id':task, 'input_sha256':result['input_sha256'],
            'clock_constraints':result['clock_constraints'],
            'producer_truth':'NOT_ASSESSED', 'row_sequence_identity':'NOT_ASSESSED',
            'same_run_provenance':'NOT_ASSESSED', 'token_attribution':'NOT_ASSESSED'}


def main():
    p=argparse.ArgumentParser(); p.add_argument('client',type=Path); p.add_argument('events',type=Path); p.add_argument('markers',type=Path)
    a=p.parse_args()
    try: result=check(a.client.read_bytes(),a.events.read_bytes(),a.markers.read_bytes())
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'status':'INVALID','error':str(exc)})); raise SystemExit(1)
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__': main()
