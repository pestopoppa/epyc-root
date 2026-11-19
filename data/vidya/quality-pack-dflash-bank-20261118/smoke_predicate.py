#!/usr/bin/env python3
"""Require original v10 CPU request, response, and custody from this smoke attempt."""
import json
import os
from pathlib import Path

from capture import D, canonical, sha
from pair import verify_response

result_path = Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
assert result_path.stat().st_mtime >= float(os.environ['FILLER_SMOKE_T0'])
result = json.loads(result_path.read_bytes())
assert (result['target_profile'], result['mode'], result['status']) == (
    'dspark-dflash', 'native-smoke-control', 'capture-complete')
assert result['request_count_per_arm'] == 1 and result['candidate_sha256'] is None
assert len(set(result['cpus'])) == 4

plan_bytes = (D / 'plan.json').read_bytes()
plan = json.loads(plan_bytes)
recipe = plan['recipes']['smoke_control']
runtime = plan['arms']['production']
native = result_path.parent / 'native'
bank = (native / 'banked-capture.json').read_bytes()
assert sha(bank) == result['bank_sha256']
record = json.loads(bank)
identity = result['capture_identity']
assert record['capture_identity'] == identity and record['runtime'] == runtime
assert identity['request_plan_sha256'] == sha(plan_bytes)
assert identity['recipe_sha256'] == sha(canonical(recipe))
row, = record['items']
item, = plan['smoke_items']
assert row['id'] == item['id'] == 'native-smoke'
production = native / 'production'
wire = (production / 'native-smoke.request.json').read_bytes()
raw = (production / 'native-smoke.response.json').read_bytes()
assert sha(wire) == row['request_sha256'] and wire == canonical(item['request_body'])
assert sha(raw) == row['response_sha256']
verify_response(json.loads(raw), item, recipe)
server = json.loads((production / 'server.json').read_bytes())
assert server['image'] == runtime and server['cpus'] == result['cpus']
assert set(server['mapped_libraries']) == set(runtime['runtime_files']) - {runtime['binary']}
cleanup = json.loads((production / 'cleanup.json').read_bytes())
assert cleanup['pid'] == server['pid'] and cleanup['dead'] is True and cleanup['port_closed'] is True
