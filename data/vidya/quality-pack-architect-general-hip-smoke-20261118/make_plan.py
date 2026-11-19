#!/usr/bin/env python3
"""Derive a native HIP publisher smoke from the original sealed packet."""
import json
from pathlib import Path
import subprocess

from capture import D, canonical, read_requests, sha, verify_files, write, write_json


BASE = D.parent / 'architect-general-20261118'


def main():
    subprocess.run(['/usr/bin/sha256sum', '--check', '--status', 'SOURCE.sha256'], cwd=BASE, check=True)
    base_path = BASE / 'plan.json'
    original = base_path.read_bytes()
    plan = json.loads(original)
    snapshot = D / 'base-plan.json'
    write(snapshot, original)
    plan['base_plan'] = {'path': snapshot.name, 'source': str(base_path), 'sha256': sha(original)}

    for name in ('chat-template.jinja', 'model-hash-receipt.json', 'profile-source.json',
                 'smoke-model-plan.original-bytes.json', 'frontdoor-full-receipt.json'):
        write(D / name, (BASE / name).read_bytes())
    smoke = plan['smoke_model']
    smoke['receipt_snapshot'] = str(D / Path(smoke['receipt_snapshot']).name)
    mismatch = plan['prior_frontdoor_json_mismatch']
    mismatch['snapshot'] = str(D / Path(mismatch['snapshot']).name)
    model_witness = plan['profile_provenance']['model_hash_witness']
    model_witness['snapshot'] = str(D / Path(model_witness['snapshot']).name)

    full = plan['recipes']['hip_slice']
    smoke_recipe = {key: full[key] for key in ('device', 'gpu_id', 'render_minor', 'kfd_topology_node')}
    smoke_recipe.update({
        'max_vram_bytes': 4 * 2**30, 'offloaded_layers': 29, 'context_tokens': 512,
        'endpoint': '/completion', 'startup_s': 45, 'request_s': 30,
        'args': ['--device', 'ROCm0', '-ngl', '99', '--fit', 'off', '--split-mode', 'none',
                 '--main-gpu', '0', '-ctk', 'f16', '-ctv', 'f16', '-fa', 'on', '--no-warmup',
                 '-np', '1', '-m', smoke['path'], '-c', '512', '--cache-ram', '0',
                 '--no-kv-unified', '--no-context-shift', '--spec-type', 'none'],
    })
    plan['recipes']['smoke_control'] = smoke_recipe
    plan['smoke_runtime'] = plan['arms']['production']

    (D / 'requests').mkdir()
    for item in plan['items']:
        entry = plan['request_files'][item['id']]
        write(D / entry['path'], (BASE / entry['path']).read_bytes())
    smoke_item, = plan['smoke_items']
    smoke_item['request_body'].update(n_predict=256, ignore_eos=True)
    entry = plan['request_files'][smoke_item['id']]
    wire = canonical(smoke_item['request_body'])
    write(D / entry['path'], wire)
    entry['sha256'] = sha(wire)

    verify_files(plan)
    read_requests(plan)
    write_json(D / 'plan.json', plan)


if __name__ == '__main__':
    main()
