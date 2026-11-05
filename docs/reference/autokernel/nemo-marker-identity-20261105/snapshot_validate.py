#!/usr/bin/env python3
"""Apply the two prospective capture checks to the same immutable byte snapshot."""
import argparse, hashlib, json
from pathlib import Path
from validate_events import validate as validate_events
from validate_request_join import validate as validate_join


def validate(client_bytes, event_bytes):
    client = json.loads(client_bytes)
    lines = event_bytes.decode('utf-8').splitlines()
    events = [json.loads(line) for line in lines]
    structural = validate_events(lines)
    join = validate_join(client, events)
    return {'status': 'CONSISTENT_NOT_ATTRIBUTED',
            'client_sha256': hashlib.sha256(client_bytes).hexdigest(),
            'events_sha256': hashlib.sha256(event_bytes).hexdigest(),
            'structural': structural, 'join': join,
            'event_scope': 'non-decode/non-marker events checked for envelope only, except request_join fields',
            'same_run_provenance': 'NOT_ASSESSED'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('client', type=Path)
    p.add_argument('events', type=Path)
    args = p.parse_args()
    try:
        result = validate(args.client.read_bytes(), args.events.read_bytes())
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(json.dumps({'status': 'INVALID', 'error': str(exc)}))
        raise SystemExit(1)
    print(json.dumps(result, sort_keys=True))

if __name__ == '__main__':
    main()
