#!/usr/bin/env python3
"""Capture one diagnostic native /completion request and response; no inference on import."""
import argparse
import base64
import json
import os
import tempfile
import urllib.request
import uuid
from pathlib import Path


def capture(url, payload, send=urllib.request.urlopen):
    if not isinstance(payload, dict) or not isinstance(payload.get('prompt'), str): raise ValueError('one string prompt is required')
    if payload.get('stream', False) is not False or payload.get('n', 1) != 1 or 'nemo_request_id' in payload:
        raise ValueError('one non-stream completion and no caller-supplied identity required')
    rid = uuid.uuid4().hex
    request_data = dict(payload, nemo_request_id=rid, stream=False)
    body = json.dumps(request_data, separators=(',', ':')).encode()
    req = urllib.request.Request(url, body, {'Content-Type':'application/json'}, method='POST')
    with send(req, timeout=600) as response:
        raw = response.read(); status = response.status
    result = json.loads(raw)
    if not isinstance(result, dict) or result.get('nemo_request_id') != rid or status != 200:
        raise ValueError('native response identity echo missing or unsuccessful')
    return {'schema':'epyc.nemo.client-capture.v1', 'requests':[{'request_id':rid,
        'sent_request_id':request_data['nemo_request_id'], 'response_request_id':result['nemo_request_id'],
        'response_status':status,'request_body_base64':base64.b64encode(body).decode(),
        'response_body_base64':base64.b64encode(raw).decode(), 'url':url}]}


def publish_capture(output, producer):
    """Publish only a complete capture; never overwrite an existing destination."""
    output = Path(output)
    # Avoid issuing a request when the caller's evidence path is already taken.
    # os.link below remains the race-safe no-replace publication primitive.
    if output.exists():
        raise FileExistsError(output)
    # A sibling temporary file lets link() publish atomically without replacement.
    fd, tmp = tempfile.mkstemp(prefix='.' + output.name + '.pending-', dir=output.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            record = producer()
            json.dump(record, out, indent=2, sort_keys=True)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.link(tmp, output)
        dirfd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        os.unlink(tmp)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--url',required=True); p.add_argument('--payload',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    payload=json.loads(a.payload.read_text())
    publish_capture(a.output, lambda: capture(a.url,payload))

if __name__=='__main__': main()
