#!/usr/bin/env python3
"""Apply draft clock and request/row checks to immutable input byte snapshots."""
import argparse
import hashlib
import json
from pathlib import Path
from audit_rows import audit
from clock_correlate import correlate
from validate_events import _unique_object


def validate(client_bytes, event_bytes, marker_bytes):
    if not all(type(v) is bytes for v in (client_bytes,event_bytes,marker_bytes)):
        raise ValueError('inputs must be byte snapshots')
    # Reject ambiguous JSON even where a consumer would otherwise choose one key.
    json.loads(client_bytes, object_pairs_hook=_unique_object)
    profiler = json.loads(marker_bytes, object_pairs_hook=_unique_object)
    event_lines = event_bytes.decode('utf-8').splitlines()
    row_result = audit(client_bytes,event_bytes)
    clock_result = correlate(event_lines, profiler)
    return {'status':'SNAPSHOT_CONSISTENT_ONLY',
            'input_sha256':{'client':hashlib.sha256(client_bytes).hexdigest(),
                            'events':hashlib.sha256(event_bytes).hexdigest(),
                            'markers':hashlib.sha256(marker_bytes).hexdigest()},
            'row_audit':row_result,'clock_constraints':clock_result,
            'source_authenticity':'NOT_ASSESSED','same_run_provenance':'NOT_ASSESSED',
            'token_attribution':'NOT_ASSESSED'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('client',type=Path); p.add_argument('events',type=Path); p.add_argument('markers',type=Path)
    a=p.parse_args()
    try: out=validate(a.client.read_bytes(), a.events.read_bytes(), a.markers.read_bytes())
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'status':'INVALID','error':str(exc)})); raise SystemExit(1)
    print(json.dumps(out,sort_keys=True))

if __name__=='__main__': main()
