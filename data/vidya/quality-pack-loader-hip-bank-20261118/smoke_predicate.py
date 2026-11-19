#!/usr/bin/env python3
"""Require native completion and same-PID MI210 custody for this smoke attempt."""
import json
import os
from pathlib import Path

from capture import D, canonical, sha


p = Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
assert p.stat().st_mtime >= float(os.environ['FILLER_SMOKE_T0'])
result = json.loads(p.read_bytes())
assert result['schema'] == 'epyc.quality_pack_native_slice.v1'
assert result['target_profile'] == 'architect-general-hip'
assert result['status'] == 'capture-complete' and result['mode'] == 'native-smoke-control'
assert result['candidate_sha256'] is None and result['request_count_per_arm'] == 1
assert len(result['cpus']) == 4 and len(set(result['cpus'])) == 4
assert result['prior_frontdoor_json_mismatch'] is True
assert result['broad_pack_status'] == 'incomplete' and result['promotion_authorized'] is False

plan_bytes = (D / 'plan.json').read_bytes()
plan = json.loads(plan_bytes)
recipe = plan['recipes']['smoke_control']
runtime = plan['arms']['production']
identity = result['capture_identity']
assert identity['profile'] == 'smoke-control'
assert identity['request_plan_sha256'] == sha(plan_bytes)
assert identity['recipe_sha256'] == sha(canonical(recipe))
assert identity['model'] == plan['smoke_model']

native = p.parent / 'native'
bank = (native / 'banked-capture.json').read_bytes()
assert sha(bank) == result['bank_sha256']
bank_record = json.loads(bank)
assert bank_record['capture_identity'] == identity and bank_record['runtime'] == runtime
row, = bank_record['items']
assert row['id'] == 'native-smoke'

production = native / 'production'
request = (production / 'native-smoke.request.json').read_bytes()
assert sha(request) == row['request_sha256'] == plan['request_files'][row['id']]['sha256']
raw = (production / 'native-smoke.response.json').read_bytes()
assert sha(raw) == row['response_sha256']
response = json.loads(raw)
settings = response['generation_settings']
timings = response['timings']
assert isinstance(response['content'], str) and response['content'].strip()
tokens = response['tokens']
assert tokens and all(type(token) is int and token >= 0 for token in tokens)
assert timings['predicted_n'] == len(tokens) == json.loads(request)['n_predict']
assert set(settings['speculative.types'].split(',')) == {'none'}
assert all(type(timings.get(key, 0)) is int and timings.get(key, 0) == 0
           for key in ('draft_n', 'draft_n_accepted'))

server = json.loads((production / 'server.json').read_bytes())
assert server['image'] == runtime and server['recipe'] == recipe and server['cpus'] == result['cpus']
pid = server['pid']
libraries = {path: pin for path, pin in (runtime['runtime_files'] | runtime['rocm_files']).items()
             if path != runtime['binary']}
mapped = {path: {'device': pin['stat'][0], 'inode': pin['stat'][1], 'sha256': pin['sha256']}
          for path, pin in libraries.items()}
assert server['mapped_libraries'] == mapped

residency = (production / 'native-smoke.hip-residency.json').read_bytes()
assert sha(residency) == row['hip_residency_sha256']
evidence = json.loads(residency)
assert not evidence['errors']
assert len({sample['t_ns'] for sample in evidence['samples']}) >= 2
for sample in evidence['samples']:
    assert evidence['request_sent_ns'] <= sample['t_ns'] <= evidence['response_end_ns']
    assert sample['pid'] == pid and pid in sample['kfd_pids'] and sample['gpu_id'] == recipe['gpu_id']
    assert (64 << 20) <= sample['process_vram_bytes'] <= recipe['max_vram_bytes']
    assert sample['device_vram_bytes'] > 0 and sample['mapped_libraries'] == mapped

cleanup = json.loads((production / 'cleanup.json').read_bytes())
assert cleanup['pid'] == pid and cleanup['dead'] is True
assert cleanup['port_closed'] is True and cleanup['kfd_entry_absent'] is True
