#!/usr/bin/env python3
"""Validate prospective request-to-server-task join evidence, not token semantics.

Requires a future native request_join event that the current source patch does not
emit. Synthetic fixtures exercise the contract; they are never capture evidence.
"""
import argparse
import base64
import binascii
import json
from pathlib import Path
from validate_events import SCHEMA, SIGNATURE


def validate(client, events):
    if not isinstance(client, dict) or client.get('schema') != 'epyc.nemo.client-capture.v1':
        raise ValueError('invalid client-capture schema')
    requests = client.get('requests')
    if not isinstance(requests, list) or not requests:
        raise ValueError('no client requests')
    identities = {}
    for r in requests:
        if not isinstance(r, dict): raise ValueError('invalid request')
        rid = r.get('request_id')
        if not isinstance(rid, str) or not rid or rid in identities: raise ValueError('missing or duplicate request_id')
        # The future transport producer must record these fields from the actual
        # request and response, rather than infer identity from temporal adjacency.
        if r.get('sent_request_id') != rid or r.get('response_request_id') != rid:
            raise ValueError('missing request/response ID echo')
        try:
            sent = json.loads(base64.b64decode(r['request_body_base64'], validate=True))
            received = json.loads(base64.b64decode(r['response_body_base64'], validate=True))
            if not isinstance(sent, dict) or not isinstance(received, dict) or sent.get('nemo_request_id') != rid or received.get('nemo_request_id') != rid:
                raise ValueError('raw request/response IDs differ')
        except (KeyError, TypeError, binascii.Error, UnicodeError) as e:
            raise ValueError('missing or malformed raw request/response body') from e
        if type(r.get('response_status')) is not int or not 200 <= r['response_status'] < 300:
            raise ValueError('request was not successfully completed')
        identities[rid] = None
    tasks = {}
    for event in events:
        if not isinstance(event, dict) or event.get('schema') != SCHEMA or event.get('instrument') != SIGNATURE:
            raise ValueError('invalid native event envelope')
        if event.get('kind') != 'request_join': continue
        d = event.get('data')
        if not isinstance(d, dict): raise ValueError('malformed native join')
        rid, task = d.get('request_id'), d.get('task_id')
        if rid not in identities or identities[rid] is not None: raise ValueError('orphan or duplicate native join')
        if type(task) is not int or task < 0 or task in tasks: raise ValueError('invalid or reused server task id')
        identities[rid] = task
        tasks[task] = rid
    if any(task is None for task in identities.values()): raise ValueError('missing native request_join')
    return {'status': 'JOIN_RECORDS_CONSISTENT', 'requests': len(identities), 'mapping': identities,
            'native_event_authenticity': 'NOT_ASSESSED', 'emitted_token_reconciliation': 'NOT_ASSESSED',
            'profiler_attribution': 'NOT_ASSESSED'}


def main():
    p = argparse.ArgumentParser(); p.add_argument('client', type=Path); p.add_argument('server_jsonl', type=Path)
    args = p.parse_args()
    try:
        client = json.loads(args.client.read_text())
        with args.server_jsonl.open() as f: events = [json.loads(line) for line in f]
        out = validate(client, events)
    except (ValueError, OSError, TypeError) as e:
        print(json.dumps({'status':'INVALID', 'error':str(e)})); raise SystemExit(1)
    print(json.dumps(out, sort_keys=True))

if __name__ == '__main__': main()
