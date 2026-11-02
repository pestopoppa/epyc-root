#!/usr/bin/env python3
"""Read native SR-6 exposure records; this does not prove inventory completeness.

Scan a single caller-supplied directory, refusing malformed, orphaned, or linked
records. A complete response here means a captured HTTP 200 byte stream, not a
scientifically valid response. Callers must establish the authoritative root and
prevent concurrent writers before relying on the resulting snapshot.
"""
import base64
import binascii
import json
from pathlib import Path

from native_worker import ARMS, HEX, SAFE_ID, digest


def inventory(root):
    if not isinstance(root, Path) or root.is_symlink() or not root.is_dir():
        raise ValueError('real inventory directory required')
    records = {}
    for path in root.iterdir():
        if not (path.name.endswith('.exposure.json') or path.name.endswith('.response.json')):
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError('record must be a regular file')
        kind = 'exposure' if path.name.endswith('.exposure.json') else 'response'
        stem = path.name.removesuffix('.' + kind + '.json')
        bucket = records.setdefault(stem, {})
        try:
            raw = path.read_bytes()
            obj = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError('unreadable record') from exc
        if not isinstance(obj, dict):
            raise ValueError('record must be an object')
        bucket[kind] = (obj, raw)
    attempts = []
    for stem, bucket in sorted(records.items()):
        if 'exposure' not in bucket:
            raise ValueError('orphan response')
        exposure, raw = bucket['exposure']
        window, block, arm, prompt = (exposure.get(k) for k in ('window', 'block', 'arm', 'prompt_id'))
        if (exposure.get('schema') != 'sr6.exposure.v1' or not isinstance(window, str)
                or not SAFE_ID.fullmatch(window) or type(block) is not int or block < 0
                or not isinstance(arm, str) or arm not in ARMS or not isinstance(prompt, str) or not SAFE_ID.fullmatch(prompt)
                or stem != f'{window}-{block}-{arm}-{prompt}'
                or not isinstance(exposure.get('rendered_sha256'), str)
                or not HEX.fullmatch(exposure['rendered_sha256'])
                or not isinstance(exposure.get('server_record_sha256'), str)
                or not HEX.fullmatch(exposure['server_record_sha256'])
                or not isinstance(exposure.get('request'), dict)):
            raise ValueError('invalid exposure')
        attempt = {'window': window, 'block': block, 'prompt_id': prompt, 'arm': arm,
                   'exposure': True, 'response': 'missing'}
        if 'response' in bucket:
            response, _ = bucket['response']
            if (response.get('schema') != 'sr6.response.v1'
                    or response.get('exposure_sha256') != digest(raw)):
                raise ValueError('invalid response identity')
            state = response.get('state')
            if state == 'raw':
                try:
                    body = base64.b64decode(response['raw_base64'], validate=True)
                except (KeyError, TypeError, ValueError, binascii.Error) as exc:
                    raise ValueError('invalid raw response') from exc
                if response.get('raw_sha256') != digest(body) or type(response.get('http_status')) is not int:
                    raise ValueError('invalid raw response identity')
                attempt['response'] = 'complete' if response['http_status'] == 200 else 'error'
            elif state == 'transport_error':
                attempt['response'] = 'error'
            else:
                raise ValueError('unknown response state')
        attempts.append(attempt)
    return attempts
