#!/usr/bin/env python3
"""Seal a row-owned DFlash2 input packet before requesting a grant."""
import base64
import dataclasses
import json
from pathlib import Path
import shutil
import sys

from capture import canonical, file_sha, sha, stat_id
from pair import CAP, verify_pairs

repo, scratch = map(Path, sys.argv[1:])
archive = repo / 'data/vidya/quality-pack-dspark-dflash-20261118'
existing = repo / 'data/vidya/quality-pack-architect-general-hip-smoke-20261118'
critic = repo / 'data/vidya/quality-pack-architect-critic-20261118'
native = repo / 'scripts/benchmark/m4_cpu_producer/native'
sys.path.insert(0, str(native))
import k35_stack_context_matrix_runner as k35  # noqa: E402


def decode(path):
    envelope = json.loads(path.read_bytes())
    raw = base64.b64decode(envelope['bytes_b64'], validate=True)
    if sha(raw) != envelope['sha256']:
        raise ValueError(f'original-bytes witness changed: {path}')
    return raw


def pin(path):
    path = path.resolve(strict=True)
    before = stat_id(path)
    digest = file_sha(path)
    if stat_id(path) != before:
        raise ValueError(f'asset changed while hashing: {path}')
    return {'path': str(path), 'sha256': digest, 'stat': before}


def write(path, body):
    with path.open('xb') as stream:
        stream.write(body)


def copy_witness(src, dst):
    shutil.copyfile(src, dst)
    return {'snapshot': str(dst), 'receipt_sha256': file_sha(dst)}


plan = json.loads(decode(existing / 'plan.json.original-bytes.json'))
critic_plan = json.loads(decode(critic / 'plan.json.original-bytes.json'))
target = critic_plan['architect_critic_model'].copy()
target_path = Path(target['path'])
if stat_id(target_path) != target['stat']:
    raise ValueError('target differs from verified hash witness')
template = pin(Path(critic_plan['architect_critic_template']['path']))
if template != critic_plan['architect_critic_template']:
    raise ValueError('registered template drift')
draft_path = Path('/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf')
saved_draft = scratch / 'draft-hash-witness.json'
if saved_draft.exists():
    draft = json.loads(saved_draft.read_bytes())
    if draft['path'] != str(draft_path) or draft['stat'] != stat_id(draft_path):
        raise ValueError('pregrant draft hash witness stat drift')
else:
    draft = pin(draft_path)
    write(saved_draft, canonical(draft) + b'\n')
target_witness = copy_witness(critic / 'model-hash-receipt.json.original-bytes.json',
                              scratch / 'target-hash-witness.json')
receipt = json.loads(decode(Path(target_witness['snapshot'])))
if (receipt['model_sha256'] != target['sha256'] or receipt['model_stat'] != target['stat']
        or receipt['model_path'] != target['path']):
    raise ValueError('target hash witness disagrees with original pin')
target.pop('receipt_snapshot')
source_paths = [
    native / 'k35_stack_context_matrix_runner.py',
    repo / 'scripts/benchmark/m4_cpu_ownership/owned.py',
    repo / '.claude/skills/kernel-promotion/scripts/quality_parity.py',
    Path('/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/dflash2_capability_smoke.sh'),
    Path('/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml'),
]
feasibility = scratch.parent / 'dflash-cpu-feasibility.json'
copy_witness(feasibility, scratch / 'cpu-feasibility.json')
source_paths.append(scratch / 'cpu-feasibility.json')
sources = [pin(path) for path in source_paths]
arm_keys = ('production', 'candidate')
plan['arms'] = {}
for name in arm_keys:
    original = critic_plan['arms'][name]
    manifest = pin(Path(original['build_manifest']))
    if manifest['sha256'] != original['build_manifest_sha256']:
        raise ValueError(f'pinned CPU build manifest drift: {name}')
    witnesses = [manifest]
    if 'build_identity' in original:
        identity = pin(Path(original['build_identity']))
        if identity['sha256'] != original['build_identity_sha256']:
            raise ValueError(f'pinned CPU build identity drift: {name}')
        witnesses.append(identity)
    runtime = {path: pin(Path(path)) for path in original['runtime_files']}
    if {path: entry['sha256'] for path, entry in runtime.items()} != original['runtime_files']:
        raise ValueError(f'pinned CPU runtime drift: {name}')
    plan['arms'][name] = {key: original[key] for key in ('binary', 'kernel_commit', 'kernel_tree')}
    plan['arms'][name].update(runtime_files=runtime, build_witnesses=witnesses)
for image in plan['arms'].values():
    candidates = {
        'draft-dflash': next(path for path in image['runtime_files'] if '/libllama-common.so.' in path),
        'speculative.n_max': next(path for path in image['runtime_files'] if path.endswith('/libllama-server-impl.so')),
    }
    for literal, path in candidates.items():
        with Path(path).open('rb') as stream:
            if literal.encode() not in stream.read():
                raise ValueError(f'pinned runtime does not expose {literal}: {path}')
    image['dflash2_support_symbols'] = candidates

smoke_model = plan['smoke_model']
smoke_model.update(copy_witness(existing / 'smoke-model-plan.original-bytes.json.original-bytes.json',
                                    scratch / 'smoke-model-hash-witness.json'))
smoke_model.pop('receipt_snapshot')
mismatch = plan['prior_frontdoor_json_mismatch']
mismatch.update(copy_witness(archive.parent / 'quality-pack-native-20261118/full-capture/receipt.json',
                             scratch / 'frontdoor-full-receipt.json'))
definitions = [
    ('json', 'short', 'Write a compact JSON object with keys status, count, and labels. Set status to ready, count to 2, and labels to alpha and beta. The JSON object is:\n'),
    ('code', 'short', 'Below is a Python function with a docstring. Complete the body with input validation, a loop, and a return statement. The function returns the even integers from a list.\ndef only_even(values):\n    """Collect even integers in order."""\n'),
    ('reasoning', 'long', 'A commuter walks north for 8 minutes, waits at the crossing for 5 minutes, then walks east for 6 minutes. A second route goes east for 6 minutes and walks north for 8 minutes, with a 2 minute wait. ' * 32
     + '\nReason step by step about the elapsed difference and whether the final displacement changes. Explain the result in complete sentences.\nSolution:'),
    ('prose', 'long', 'In the archive, the morning shift labels boxes by month, the evening shift labels boxes by shelf, and every moving cart must leave an entry in a physical ledger. ' * 32
     + '\nWrite the next paragraph of a short story about a new archivist reconciling the two systems without losing an inventory item.\nThe new archivist'),
]
scenario = dataclasses.replace(
    k35.scenario_by_name('v9_dsv4_q8_dspark_request_nmax0'),
    name='qwen38_27b_dflash2_request_pair', model=target_path, draft_model=draft_path,
    spec_type='draft-dflash', device='none', n_gpu_layers=0,
    spec_draft_device='none', spec_draft_ngl=0, spec_draft_n_max=CAP,
)
items = []
for name, shape, prompt in definitions:
    for cap in (0, CAP):
        body = k35.build_chat_request_body(dataclasses.replace(scenario, request_spec_n_max=cap),
                                          prompt, max_tokens=128)
        items.append({'id': f'dflash2-{name}-cap{cap}', 'request_body': body,
                      'dflash_pair': f'dflash2-{name}', 'prompt_shape': shape, 'output_format': name})
verify_pairs(items)

full = {'args': ['--alias', 'quality-dflash2', '--device', 'none', '-ngl', '0',
                 '-ctk', 'f16', '-ctv', 'f16', '-fa', 'on', '--no-warmup', '-np', '1', '-m', str(target_path),
                 '-c', '4096', '-b', '512', '-ub', '512', '--cache-ram', '0', '--no-kv-unified',
                 '--no-context-shift', '--spec-type', 'draft-dflash', '-md', str(draft_path),
                 '--spec-draft-device', 'none', '--spec-draft-ngl', '0', '--spec-draft-n-min', '0',
                 '--spec-draft-n-max', str(CAP)],
        'endpoint': '/completion', 'batch': 512, 'context_tokens': 4096, 'slots': 1,
        'speculation': 'draft-dflash', 'startup_s': 240, 'request_s': 90}
smoke = critic_plan['recipes']['smoke_control']
smoke.update({'smoke': True, 'slots': 1, 'speculation': 'none', 'context_tokens': 512})
plan['recipes'] = {'cpu_slice': full, 'smoke_control': smoke}
plan['smoke_items'] = critic_plan['smoke_items']
plan.pop('base_plan', None)
plan.pop('profile_provenance', None)
plan.update({'schema': 'epyc.quality_pack_dflash2_source_plan.v1', 'profile': 'dspark-dflash',
             'validated_cap': CAP, 'model_shards': [target], 'draft_model': draft, 'template': template,
             'model_hash_witness': target_witness, 'source_witnesses': sources,
             'scope': 'Isolated source inputs on Qwen3.8 DFlash2. Native raw prompts bypass the registered chat template. Historical DeepSeek 0731 DSpark remains retired. No broad pack comparison or qualification.',
             'items': items, 'question_pool_sha256': sha(canonical(items)), 'request_files': {}})
plan['smoke_runtime'] = plan['arms']['production']
(scratch / 'requests').mkdir()
for item in [*items, *plan['smoke_items']]:
    rel = f"requests/{item['id']}.json"
    raw = canonical(item['request_body'])
    write(scratch / rel, raw)
    plan['request_files'][item['id']] = {'path': rel, 'sha256': sha(raw)}
write(scratch / 'plan.json', canonical(plan) + b'\n')
