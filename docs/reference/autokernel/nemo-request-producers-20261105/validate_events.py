#!/usr/bin/env python3
"""Fail-closed structural validation of prospective server events; no attribution."""
import argparse
import json
from pathlib import Path

SIGNATURE = 'NEMO_SERVER_BOUNDARY_V1_C3_SYNCHRONIZED_DIAGNOSTIC'
SCHEMA = 'epyc.nemo.server-boundary.v1'
KINDS = {'decode_begin', 'decode_end', 'decode_incomplete', 'clock_sync', 'token_processed', 'verification_result', 'final_summary', 'request_join'}


def validate(lines):
    begins, ends, markers = {}, {}, {}
    previous = -1
    pid = None
    count = 0
    for lineno, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
            if not isinstance(event, dict) or event.get('schema') != SCHEMA or event.get('instrument') != SIGNATURE or event.get('clock_domain') != 'CLOCK_MONOTONIC':
                raise ValueError('invalid schema, instrument or clock domain')
            kind, ts, p, tid, data = (event.get(k) for k in ('kind', 'observed_ns', 'pid', 'tid', 'data'))
            if kind not in KINDS or not isinstance(data, dict): raise ValueError('unknown kind or invalid data')
            if any(type(n) is not int or n <= 0 for n in (ts, p, tid)): raise ValueError('invalid timestamp or process/thread identity')
            if ts < previous: raise ValueError('timestamps out of order')
            if pid is not None and p != pid: raise ValueError('multiple producer PIDs')
            previous, pid = ts, p
            if kind == 'decode_incomplete': raise ValueError('incomplete decode')
            if kind in ('decode_begin', 'decode_end'):
                i = data.get('decode_id')
                if type(i) is not int or i <= 0: raise ValueError('invalid decode id')
                table = begins if kind == 'decode_begin' else ends
                if i in table: raise ValueError('duplicate decode edge')
                if kind == 'decode_end':
                    if i not in begins or begins[i][1] != tid: raise ValueError('missing begin or mismatched decode thread')
                    start, end = data.get('start_ns'), data.get('completion_ns')
                    if any(type(n) is not int for n in (start, end)) or not begins[i][0] <= start <= end <= ts: raise ValueError('invalid decode interval')
                    if data.get('llama_decode_rc') != 0 or data.get('synchronized') is not True or data.get('completion_semantics') != 'host_after_llama_synchronize_on_success': raise ValueError('unsuccessful or unsynchronized decode')
                table[i] = (ts, tid, data)
            elif kind == 'request_join':
                if not isinstance(data.get('request_id'), str) or not data['request_id'] or type(data.get('task_id')) is not int or data['task_id'] < 0: raise ValueError('invalid native request join')
            elif kind == 'clock_sync':
                label = data.get('marker')
                prefix = SIGNATURE + ':clock_sync:'
                if not isinstance(label, str) or not label.startswith(prefix): raise ValueError('invalid marker')
                fields = label[len(prefix):].split(':')
                if len(fields) != 2 or not fields[0].isdigit() or fields[1] not in ('before', 'after'): raise ValueError('invalid marker identity')
                i, edge = int(fields[0]), fields[1]
                if i <= 0 or (i, edge) in markers: raise ValueError('invalid or duplicate marker')
                before, after = data.get('before_ns'), data.get('after_ns')
                if any(type(n) is not int for n in (before, after)) or not 0 < before <= after <= ts: raise ValueError('invalid marker envelope')
                markers[i, edge] = (before, after, tid)
            count += 1
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            raise ValueError(f'line {lineno}: {e}') from e
    if not begins or begins.keys() != ends.keys(): raise ValueError('no complete decodes or unmatched edges')
    if set(markers) != {(i, edge) for i in begins for edge in ('before', 'after')}: raise ValueError('missing or orphan marker')
    for i, (begin_ts, tid, _) in begins.items():
        before, after = markers[i, 'before'], markers[i, 'after']
        end_ts = ends[i][0]
        if before[2] != tid or after[2] != tid: raise ValueError(f'decode {i}: marker thread mismatch')
        if not begin_ts <= before[0] <= before[1] <= ends[i][2]['start_ns'] <= ends[i][2]['completion_ns'] <= after[0] <= after[1]:
            raise ValueError(f'decode {i}: marker/decode order mismatch')
        if end_ts > after[0]: raise ValueError(f'decode {i}: after marker precedes end record')
    return {'status': 'STRUCTURALLY_VALID', 'events': count, 'decodes': len(begins), 'pid': pid, 'clock_domain': 'CLOCK_MONOTONIC', 'attribution': 'NOT_ASSESSED', 'profiler_clock_alignment': 'NOT_ASSESSED'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('events', type=Path)
    args = parser.parse_args()
    try:
        with args.events.open(encoding='utf-8') as f: result = validate(f)
    except (OSError, ValueError) as e:
        print(json.dumps({'status': 'INVALID', 'error': str(e)}))
        raise SystemExit(1)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__': main()
