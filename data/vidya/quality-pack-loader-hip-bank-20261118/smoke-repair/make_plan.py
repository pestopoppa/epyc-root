#!/usr/bin/env python3
"""Pin a four-request production HIP bank with a loader fixture."""

import json

from capture_base import D, PROFILE, canonical, file_sha, sha
from quality_parity import VALIDATOR_SOURCE_SHA256

ROW = 'handoff-vidya-quality-pack-architect-general-hip-loader-bank-20261118'
ITEM = 'architect-general-hip-loader-reshape-json'
PINS = {
    'production-runtime-stat-refresh.json': '8d8126dae927f90d9b2b5dc07555edc08d36e6744857c9f2d09614f1a9314f26',
    'hip-scoring-from-prospective-metadata.json': '7089409366c9a50bd8dbe962c2cc7a641abe93d33ac412e52e36d02c66200ef8',
    'hip-plan.original.json': '51ca3cdd63fea358a53449151f1174751ac857431663f7745791cd0f317b0e23',
    'loader-reshape-witness.json': 'eb1a7ab49b75440793223b4d8bf7982577dda1c0fe37ac76d956362337b9f0e3',
    'cpu-diagnostic-result.original.json': 'dee8f89c8d199e9232441251b48f714d2ea738992cb435ba2ae5bb2591bbf7a5',
}
TENSORS = ('blk.0.hc_attn_norm.weight', 'blk.0.hc_ffn_norm.weight')


def build_plan(root=D):
    for name, pin in PINS.items():
        if file_sha(root / name) != pin:
            raise ValueError(f'original receipt drift: {name}')
    original = json.loads((root / 'hip-plan.original.json').read_bytes())
    witness = json.loads((root / 'loader-reshape-witness.json').read_bytes())
    if (witness['source_plan_sha256'] != PINS['hip-plan.original.json']
            or witness['profile'] != PROFILE or original['profile'] != PROFILE
            or witness['model_shard_sha256'] != [entry['sha256'] for entry in original['model_shards']]
            or set(witness['tensors']) != set(TENSORS)):
        raise ValueError('loader witness does not bind the HIP shape and pregrant shard pins')
    if witness['gguf_metadata'] != {'general.architecture': 'qwen4exp',
                                    'qwen4exp.embedding_length': 2560,
                                    'qwen4exp.hyper_connection.count': 4}:
        raise ValueError('unexpected loader architecture or dimensions')
    for name in TENSORS:
        tensor = witness['tensors'][name]
        if (tensor['disk_shape'], tensor['tensor_type'], tensor['tensor_bytes'], tensor['shard_sha256']) != (
            [10240], 'F32', 40960, original['model_shards'][1]['sha256'],
        ):
            raise ValueError(f'wrong source shard or tensor header: {name}')
    for arm, dims in (('production', [10240]), ('candidate', [2560, 4])):
        source = witness['runtime_source'][arm]
        identity = original['arms'][arm]
        if (source['kernel_commit'], source['kernel_tree'], source['loader_shape'],
            source['loader_reshape_expected']) != (
            identity['kernel_commit'], identity['kernel_tree'], dims, arm == 'candidate',
        ):
            raise ValueError(f'loader source witness differs from prepared HIP runtime: {arm}')
    prior, = [item for item in original['items'] if item['id'] == 'architect-general-hip-json']
    expected = {'route': 'amber', 'enabled': True, 'replicas': 3}
    if prior['reference'] != expected:
        raise ValueError('original HIP JSON semantic expectations drifted')
    body = {
        **prior['request_body'],
        'messages': [{
            'role': 'user',
            'content': (
                'The route is amber, it is enabled, and there are three replicas. '
                'Reply with one JSON object. Set route to the string "amber", enabled to '
                'the boolean true, and replicas to the integer 3. End after the closing brace.'
            ),
        }],
    }
    item = {
        'id': ITEM, 'shape': PROFILE, 'request_body': body, 'prompt_shape': 'short',
        'output_format': 'json', 'fixture': 'loader-reshape', 'expected_finish': 'stop',
        'validator': {'id': 'json-object-subset.v1', 'expected': expected}, 'dflash_pair': None,
    }
    policy = json.loads((root / 'hip-scoring-from-prospective-metadata.json').read_bytes())
    scoring = {entry['id']: entry for entry in policy['scoring']}
    fixture_policy = scoring[ITEM]
    if any(item[key] != fixture_policy[key] for key in ('validator', 'expected_finish')):
        raise ValueError('prospective HIP fixture scoring differs from the original declaration')
    items = [item]
    for entry in original['items']:
        name = entry['id']
        if name == prior['id']:
            continue
        items.append({
            'id': name, 'shape': PROFILE, 'request_body': entry['request_body'],
            'prompt_shape': entry['prompt_shape'], 'output_format': entry['format'],
            'fixture': None, 'dflash_pair': None,
            'validator': scoring[name]['validator'], 'expected_finish': scoring[name]['expected_finish'],
        })
    production = original['arms']['production']
    runtime_refresh = json.loads((root / 'production-runtime-stat-refresh.json').read_bytes())
    runtime_files = {
        entry['path']: entry
        for entry in (*production['build_witnesses'], *production['runtime_files'].values(),
                      *production['rocm_files'].values())
    }
    for path, receipt in runtime_refresh.items():
        entry = runtime_files[path]
        if (receipt['old_stat'] != entry['stat'] or receipt['sha256'] != entry['sha256']
                or len(receipt['new_stat']) != 5 or receipt['new_stat'][:4] != entry['stat'][:4]):
            raise ValueError(f'production runtime refresh does not preserve the source identity: {path}')
        entry['stat'] = receipt['new_stat']

    recipe = dict(original['recipes']['hip_slice'])
    recipe['args'] = list(recipe['args']) + ['--verbosity', '5']
    recipe['args'][recipe['args'].index('--chat-template-file') + 1] = str(root / 'chat-template.jinja')
    question_pool = [{key: entry[key] for key in (
        'id', 'request_body', 'prompt_shape', 'output_format', 'fixture',
    )} for entry in items]
    sampling = [{
        'id': entry['id'], 'parameters': {key: value for key, value in entry['request_body'].items()
                                          if key not in ('messages', 'prompt', 'model')},
    } for entry in items]
    scoring_roster = [{key: entry[key] for key in ('id', 'expected_finish', 'validator')} for entry in items]
    scorer_pin = sha(canonical({'source_sha256': VALIDATOR_SOURCE_SHA256, 'items': scoring_roster}))
    if scorer_pin != policy['shape']['scorer_sha256']:
        raise ValueError('current shared comparator or scoring policy differs from the pinned declaration')
    recipe_pin = sha(canonical(recipe))
    generation = {**policy['generation'], 'recipe_sha256': recipe_pin}
    shape = {
        **policy['shape'], 'recipe_sha256': recipe_pin,
        'question_pool_sha256': sha(canonical(question_pool)),
        'sampling_sha256': sha(canonical(sampling)),
        'generation_path_sha256': sha(canonical(generation)),
    }
    return {
        **original, 'schema': 'epyc.architect_general_hip_loader_bank_plan.v1',
        'arms': {'production': production}, 'smoke_runtime': production, 'items': items,
        'recipes': {**original['recipes'], 'hip_slice': recipe},
        'pack_shape': shape, 'pack_generation': generation,
        'pack_endpoint_semantics': policy['endpoint_semantics'],
        'question_pool_sha256': sha(canonical(items)),
        'request_files': {
            entry['id']: {'path': f"requests/{entry['id']}.json",
                          'sha256': sha(canonical(entry['request_body']))}
            for entry in (*items, *original['smoke_items'])
        },
        'source_receipts_sha256': PINS,
        'loader_witness': {'tensors': list(TENSORS), 'stored_dims': [10240],
                           'production_dims': [10240], 'candidate_dims_from_source': [2560, 4]},
        'scope': 'Four strict v10 production items on one traced architect-general HIP recipe. C13 requires fresh post-seal candidate capture.',
    }


def build_spec(root=D):
    return {
        'id': ROW, 'owner': 'handoff-vidya-belief-substrate',
        'handoff_task': 'handoffs/active/vidya-belief-substrate-program.md:VB-V9-8-QUALITY-PACK-LOADER-HIP-BANK',
        'lane': 'gpu', 'regions': 'mi210_0,184-191', 'shape': 'gpu', 'kind': 'compute',
        'estimate_s': 980, 'min_window_s': 1200, 'max_window_s': 1500, 'ram_gib': 112,
        'first_progress_s': 120, 'launcher': str(root / 'row-launch.sh'), 'scratch_root': str(root),
        'result_path': str(root / 'out/RESULT.json'), 'result_format': 'json', 'dryrun_native_result': True,
        'smoke_predicate': f'/usr/bin/python3 -B {root}/smoke_predicate.py',
        'decision_rule': (
            'Admit four v10 architect-general HIP production items after all replies pass their '
            'pinned semantics, clean stops and token checks and each proves two in-window '
            'same-PID MI210 samples. The unique mapped serving phase must prove both pinned '
            'loader fixture tensor load lines. Preserve source, header, model, grant, raw '
            'request and response, process and mapped-library evidence and verified cleanup. '
            'Stop after four captures and cleanup or at STOP/deadline or first custody, transport or '
            'fixture failure. Publisher smoke runs one genuine v10 HIP small-model completion '
            'on the MI210 and four CPUs. Candidate capture waits for the complete bank seal.'
        ),
        'verdict_by': 'agent', 'priority_rank': 40,
        'keep': ['out/**', 'requests/**', '*.py', '*.json', '*.jinja', '*.sh', '*.md', '*.txt', 'SOURCE.sha256'],
    }


if __name__ == '__main__':
    plan = build_plan()
    (D / 'plan.json').write_bytes(canonical(plan) + b'\n')
    (D / 'row.spec.json').write_bytes(canonical(build_spec()) + b'\n')
    for item in (*plan['items'], *plan['smoke_items']):
        (D / plan['request_files'][item['id']]['path']).write_bytes(canonical(item['request_body']))
