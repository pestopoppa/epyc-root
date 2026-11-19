#!/usr/bin/env python3
"""Verify real native bytes and request identity from this smoke attempt."""
import hashlib
import json
import os
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


p = Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
result = json.loads(p.read_bytes())
assert result['schema'] == 'epyc.quality_pack_native_slice.v1'
assert result['target_profile'] == 'architect-critic-cpu-mtp'
assert result['capture_identity']['profile'] == 'smoke-control'
assert result['prior_frontdoor_json_mismatch'] is True
assert result['status'] == 'capture-complete' and result['mode'] == 'native-smoke-control'
assert len(result['cpus']) == 4 and len(set(result['cpus'])) == 4
assert result['broad_pack_status'] == 'incomplete' and result['promotion_authorized'] is False
assert p.stat().st_mtime >= float(os.environ['FILLER_SMOKE_T0'])
native = p.parent / 'native'
bank = (native / 'banked-capture.json').read_bytes()
assert sha(bank) == result['bank_sha256']
row = json.loads(bank)['items'][0]
assert row['id'] == 'native-smoke'
raw = (native / 'production/native-smoke.response.json').read_bytes()
assert sha(raw) == row['response_sha256']
assert sha((native / 'production/native-smoke.request.json').read_bytes()) == row['request_sha256']
response = json.loads(raw)
assert isinstance(response['content'], str) and response['content'].strip()
assert response['tokens'] and all(type(token) is int and token >= 0 for token in response['tokens'])
assert response['timings']['predicted_n'] == len(response['tokens'])
cleanup = json.loads((native / 'production/cleanup.json').read_bytes())
assert cleanup['dead'] is True and cleanup['port_closed'] is True
