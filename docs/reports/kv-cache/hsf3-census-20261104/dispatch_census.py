#!/usr/bin/env python3
"""Count dispatch-session coverage without writing session keys or request text."""
import collections
import datetime
import hashlib
import json
import pathlib
import sys

p = pathlib.Path(sys.argv[1])
raw = p.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '2eeb5a5753d098a11a8871fb891f7fa6087b19b7ff46ca8f649ac49970e84b67', 'source differs from recorded census'
c = collections.Counter()
sessions = collections.defaultdict(list)
for line in raw.splitlines():
    try:
        record = json.loads(line)
    except ValueError:
        c['invalid_json'] += 1
        continue
    if record.get('schema') != 'epyc.orchestrator.dispatch.v1':
        c['other_schema'] += 1
        continue
    c['dispatch_records'] += 1
    key = (record.get('session') or {}).get('key')
    client = (record.get('client') or {}).get('class')
    role, start, end = record.get('role'), record.get('ts_arrival'), record.get('ts_end')
    if key:
        c['keyed_records'] += 1
    if key and client:
        c['keyed_classed_records'] += 1
    if key and client and role and start and end:
        try:
            a = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
            b = datetime.datetime.fromisoformat(end.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            c['invalid_times'] += 1
            continue
        sessions[(key, client, role)].append((a, b))
pairs = 0
for calls in sessions.values():
    calls.sort()
    if any(first[1] <= following[0] for first, following in zip(calls, calls[1:])):
        pairs += 1
print(json.dumps({'dispatch_records': c['dispatch_records'], 'keyed_records': c['keyed_records'],
                  'keyed_classed_records': c['keyed_classed_records'],
                  'keyed_classed_role_end_sessions': len(sessions),
                  'sessions_with_nonoverlapping_frontend_arrival_pair': pairs,
                  'invalid_json': c['invalid_json'], 'other_schema': c['other_schema'],
                  'invalid_times': c['invalid_times']}, sort_keys=True))
