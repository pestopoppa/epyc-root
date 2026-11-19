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
assert result['target_profile'] == 'worker-vision-hip-mmproj'
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
arm = native / 'production'
raw = (arm / 'native-smoke.response.json').read_bytes()
assert sha(raw) == row['response_sha256']
request = (arm / 'native-smoke.request.json').read_bytes()
assert sha(request) == row['request_sha256']
assert request == (Path(__file__).resolve().parent / 'requests/native-smoke.json').read_bytes()
response = json.loads(raw)
assert isinstance(response['content'], str) and response['content'].strip()
assert response['tokens'] and all(type(token) is int and token >= 0 for token in response['tokens'])
assert response['timings']['predicted_n'] == len(response['tokens']) == json.loads(request)['n_predict']
assert all(type(response['timings'].get(key, 0)) is int and response['timings'].get(key, 0) == 0
           for key in ('draft_n', 'draft_n_accepted'))
assert set(response['generation_settings']['speculative.types'].split(',')) == {'none'}
server = json.loads((arm / 'server.json').read_bytes())
assert server['recipe']['device'] == 'ROCm0' and server['cpus'] == result['cpus']
assert server['image']['kernel_commit'] == 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
cleanup = json.loads((arm / 'cleanup.json').read_bytes())
assert cleanup['pid'] == server['pid']
assert all(cleanup[key] is True for key in ('dead', 'port_closed', 'kfd_entry_absent'))
raw_residency = (arm / 'native-smoke.hip-residency.json').read_bytes()
assert sha(raw_residency) == row['hip_residency_sha256']
residency = json.loads(raw_residency)
assert not residency['errors'] and len({sample['t_ns'] for sample in residency['samples']}) >= 2
for sample in residency['samples']:
    assert residency['request_sent_ns'] <= sample['t_ns'] <= residency['response_end_ns']
    assert sample['pid'] == server['pid'] and sample['pid'] in sample['kfd_pids']
    assert sample['gpu_id'] == server['recipe']['gpu_id'] and sample['process_vram_bytes'] >= 64 << 20
    assert any(Path(lib).name.startswith('libggml-hip.so') for lib in sample['mapped_libraries'])
assert result['candidate_sha256'] is None and result['request_count_per_arm'] == 1
