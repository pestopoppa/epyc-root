#!/usr/bin/env python3
"""Check single-task request/clock snapshots and marker producer PID/TID identity."""
import argparse
import json
from pathlib import Path
from single_task_binding import check as check_single_task
from validate_events import _unique_object


def check(client_bytes, events_bytes, markers_bytes):
    result = check_single_task(client_bytes, events_bytes, markers_bytes)
    events = [json.loads(line, object_pairs_hook=_unique_object)
              for line in events_bytes.decode('utf-8').splitlines()]
    profiler = json.loads(markers_bytes, object_pairs_hook=_unique_object)
    host = {event['data']['marker']: (event['pid'], event['tid'])
            for event in events if event['kind'] == 'clock_sync'}
    # check_single_task already rejects missing, duplicate, and orphan labels.
    for record in profiler['markers']:
        label = record['marker']
        pid, tid = record.get('pid'), record.get('tid')
        if type(pid) is not int or pid <= 0 or type(tid) is not int or tid <= 0:
            raise ValueError('profiler marker PID/TID required as positive integers')
        if (pid, tid) != host[label]:
            raise ValueError(f'profiler marker PID/TID mismatch: {label}')
    return {'status': 'MARKER_IDENTITY_CONSISTENT_ONLY',
            'input_sha256': result['input_sha256'],
            'matched_markers': len(host), 'checked_decodes': result['checked_decodes'],
            'joined_task_id': result['joined_task_id'], 'clock_constraints': result['clock_constraints'],
            'producer_authenticity': 'NOT_ASSESSED', 'same_run_provenance': 'NOT_ASSESSED',
            'profiler_normalization_and_clock_semantics': 'NOT_ASSESSED',
            'token_attribution': 'NOT_ASSESSED'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('client', type=Path); p.add_argument('events', type=Path); p.add_argument('markers', type=Path)
    a = p.parse_args()
    try:
        out = check(a.client.read_bytes(), a.events.read_bytes(), a.markers.read_bytes())
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'status': 'INVALID', 'error': str(exc)})); raise SystemExit(1)
    print(json.dumps(out, sort_keys=True))


if __name__ == '__main__': main()
