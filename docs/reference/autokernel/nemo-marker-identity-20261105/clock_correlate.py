#!/usr/bin/env python3
"""Intersect prospective same-clock offset constraints; not GPU attribution."""
import argparse
import json
from pathlib import Path
from validate_events import validate as validate_events, _unique_object


def correlate(lines, profiler):
    lines = list(lines)
    structural = validate_events(lines)
    if not isinstance(profiler, dict) or profiler.get('schema') != 'epyc.nemo.profiler-markers.v1':
        raise ValueError('invalid profiler marker schema')
    if not isinstance(profiler.get('clock_domain'), str) or not profiler['clock_domain']:
        raise ValueError('missing profiler clock domain')
    events = [json.loads(line, object_pairs_hook=_unique_object) for line in lines]
    host = {e['data']['marker']: (e['data']['before_ns'], e['data']['after_ns'])
            for e in events if e['kind'] == 'clock_sync'}
    records = profiler.get('markers')
    if not isinstance(records, list):
        raise ValueError('missing profiler markers')
    found = {}
    for record in records:
        if not isinstance(record, dict): raise ValueError('invalid profiler marker')
        label, ts = record.get('marker'), record.get('timestamp_ns')
        if not isinstance(label, str) or label not in host or label in found:
            raise ValueError('orphan or duplicate profiler marker')
        if type(ts) is not int or ts <= 0:
            raise ValueError('invalid profiler timestamp')
        found[label] = ts
    if found.keys() != host.keys(): raise ValueError('missing profiler markers')
    lower = max(host[label][0] - ts for label, ts in found.items())
    upper = min(host[label][1] - ts for label, ts in found.items())
    if lower > upper: raise ValueError('marker envelopes have no common clock offset')
    return {'status':'OFFSET_CONSTRAINTS_CONSISTENT_ONLY', 'markers':len(found),
            'host_clock_domain':'CLOCK_MONOTONIC', 'profiler_clock_domain':profiler['clock_domain'],
            'host_minus_profiler_offset_ns':[lower, upper], 'offset_uncertainty_width_ns':upper-lower,
            'drift_and_same_run_provenance':'NOT_ASSESSED', 'kernel_attribution':'NOT_ASSESSED',
            'structural':structural}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('events', type=Path); parser.add_argument('markers', type=Path)
    args = parser.parse_args()
    try:
        result = correlate(args.events.read_text().splitlines(), json.loads(args.markers.read_text(), object_pairs_hook=_unique_object))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(json.dumps({'status':'INVALID','error':str(exc)})); raise SystemExit(1)
    print(json.dumps(result, sort_keys=True))

if __name__ == '__main__': main()
