#!/usr/bin/env python3
"""Build a CPU loader diagnostic plan from original pre-grant identity receipts."""

import base64
import json

from cpu_native import D, canonical, file_sha, sha

PREDECESSOR = 'handoff-vidya-quality-pack-loader-reshape-cpu-20261118'
ROW = PREDECESSOR + '-r2'
BOX = 'VB-V9-8-QUALITY-PACK-LOADER-DIAG'
PROFILE = 'qwen4exp-cpu-loader-diagnostic'
TENSORS = ('blk.0.hc_attn_norm.weight', 'blk.0.hc_ffn_norm.weight')
ARCHITECT_PIN = '51ca3cdd63fea358a53449151f1174751ac857431663f7745791cd0f317b0e23'


def build_plan():
    if file_sha(D / 'base-plan.json') != ARCHITECT_PIN:
        raise ValueError('predecessor HIP plan bytes changed')
    model_plan = json.loads((D / 'base-plan.json').read_bytes())
    envelope = json.loads((D / 'cpu-plan.original-bytes.json').read_bytes())
    cpu_original = base64.b64decode(envelope['bytes_b64'], validate=True)
    if sha(cpu_original) != envelope['sha256']:
        raise ValueError('CPU runtime receipt original bytes changed')
    cpu_plan = json.loads(cpu_original)
    runtime = cpu_plan['arms']
    for name in ('production', 'candidate'):
        if (runtime[name]['kernel_commit'], runtime[name]['kernel_tree']) != (
            model_plan['arms'][name]['kernel_commit'], model_plan['arms'][name]['kernel_tree']
        ):
            raise ValueError(f'{name} CPU source differs from loader comparison source')
    smoke_model = dict(model_plan['smoke_model'])
    smoke_model['receipt_snapshot'] = 'smoke-model-plan.original-bytes.json'
    request = {
        'model': PROFILE, 'cache_prompt': False, 'seed': 35, 'temperature': 0,
        'stream': False, 'return_tokens': True, 'verbose': True, 'max_tokens': 48,
        'chat_template_kwargs': {'enable_thinking': False},
        'messages': [{
            'role': 'user',
            'content': 'Return only this JSON object, without a code fence: {"loader_probe":"amber","count":2}',
        }],
    }
    item = {
        'id': 'qwen4exp-loader-cpu-json', 'request_body': request,
        'expected_finish': 'stop',
        'validator': {'id': 'json-object-subset.v1', 'expected': {'loader_probe': 'amber', 'count': 2}},
    }
    smoke_item, = cpu_plan['smoke_items']
    model_shards = model_plan['model_shards']
    witness = json.loads((D / 'loader-reshape-witness.json').read_bytes())
    if (
        witness['schema'] != 'epyc.quality_pack_loader_reshape_witness.v1'
        or witness['source_plan_sha256'] != ARCHITECT_PIN
        or witness['model_shard_sha256'] != [shard['sha256'] for shard in model_shards]
        or set(witness['tensors']) != set(TENSORS)
        or witness['gguf_metadata'] != {
            'general.architecture': 'qwen4exp', 'qwen4exp.embedding_length': 2560,
            'qwen4exp.hyper_connection.count': 4,
        }
    ):
        raise ValueError('loader witness differs from the pinned qwen4exp shard set')
    for tensor in witness['tensors'].values():
        if (tensor['disk_shape'], tensor['tensor_type'], tensor['tensor_bytes'], tensor['shard_sha256']) != (
            [10240], 'F32', 40960, model_shards[1]['sha256'],
        ):
            raise ValueError('loader witness has unexpected norm storage dimensions or shard')
    for name, dims in (('production', [10240]), ('candidate', [2560, 4])):
        source = witness['runtime_source'][name]
        if (source['kernel_commit'], source['kernel_tree'], source['loader_shape']) != (
            runtime[name]['kernel_commit'], runtime[name]['kernel_tree'], dims,
        ):
            raise ValueError(f'{name} CPU runtime differs from loader source witness')
        if source['loader_reshape_expected'] is not (name == 'candidate'):
            raise ValueError(f'{name} loader witness has wrong reshape expectation')
    recipe = {
        'args': [
            '--alias', PROFILE, '--device', 'none', '-ngl', '0',
            '-ctk', 'f16', '-ctv', 'f16', '-fa', 'on', '--no-warmup', '-np', '1',
            '-m', model_shards[0]['path'], '-c', '2048', '-b', '256', '-ub', '256',
            '--mmap', '--cache-ram', '0', '--no-kv-unified', '--no-context-shift',
            '--jinja', '--spec-type', 'none', '--verbosity', '5',
        ],
        'external_chat_template': 'chat-template.jinja',
        'endpoint': '/v1/chat/completions', 'startup_s': 460, 'request_s': 240,
    }
    pins = {
        'base-plan.json': ARCHITECT_PIN,
        'cpu-plan.original-bytes.json': file_sha(D / 'cpu-plan.original-bytes.json'),
        'chat-template.jinja': model_plan['template']['sha256'],
        'frontdoor-full-receipt.json': model_plan['prior_frontdoor_json_mismatch']['receipt_sha256'],
        'model-hash-receipt.json': model_plan['profile_provenance']['model_hash_witness']['sha256'],
        smoke_model['receipt_snapshot']: smoke_model['original_hash_receipt_sha256'],
        'loader-reshape-witness.json': file_sha(D / 'loader-reshape-witness.json'),
    }
    return {
        'schema': 'epyc.qwen4exp_cpu_loader_diagnostic_plan.v1',
        'profile': PROFILE, 'arms': runtime, 'model_shards': model_shards,
        'receipts_sha256': pins, 'smoke_model': smoke_model,
        'items': [item], 'smoke_items': [smoke_item],
        'request_files': {
            entry['id']: sha(canonical(entry['request_body'])) for entry in (item, smoke_item)
        },
        'loader_witness': {
            'tensors': list(TENSORS), 'source': 'loader-reshape-witness.json',
            'stored_dims': [10240], 'production_dims': [10240], 'candidate_dims': [2560, 4],
        },
        'recipes': {'diagnostic': recipe, 'smoke_control': cpu_plan['recipes']['smoke_control']},
        'scope': 'CPU loader diagnostic only. Separate from the required architect-general HIP shape and the broad quality pack.',
    }


def build_spec():
    return {
        'id': ROW, 'owner': 'handoff-vidya-belief-substrate', 'supersedes': PREDECESSOR,
        'handoff_task': f'handoffs/active/vidya-belief-substrate-program.md:{BOX}',
        'lane': 'cpu', 'shape': 'quarter', 'kind': 'compute', 'regions': 'any-cpu-quarter',
        'estimate_s': 1300, 'min_window_s': 1650, 'max_window_s': 1950,
        'ram_gib': 112, 'first_progress_s': 120, 'priority_rank': 38,
        'launcher': str(D / 'row-launch.sh'), 'scratch_root': str(D),
        'result_path': str(D / 'out' / 'RESULT.json'), 'result_format': 'json',
        'dryrun_native_result': True,
        'smoke_predicate': f'/usr/bin/python3 -B {D}/smoke_predicate.py',
        'decision_rule': (
            'Does the pinned C13 CPU loader accept the same flat F32 qwen4exp norm tensors '
            'that v10 loads flat, and can both serve the fixed JSON request? One diagnostic request '
            'per runtime, with pinned source and GGUF metadata, native debug logs for the witnessed '
            'tensors within the unique mapped load phase, exact HTTP bytes, CPU/process/library '
            'evidence and verified cleanup. Seal the '
            'v10 arm before C13 starts. Stop after two captures or at STOP/deadline or the first '
            'identity/load/response/cleanup failure. Four-CPU smoke runs the pinned v10 no-spec '
            'small-model completion. CPU diagnostic scope excludes the required HIP profile and '
            'supplies no broad-pack input or promotion authority.'
        ),
        'keep': ['out/**', 'requests/**', '*.py', '*.json', '*.jinja', '*.md', '*.sh', 'SOURCE.sha256'],
        'verdict_by': 'agent',
    }


if __name__ == '__main__':
    plan = build_plan()
    (D / 'plan.json').write_bytes(canonical(plan) + b'\n')
    (D / 'row.spec.json').write_bytes(canonical(build_spec()) + b'\n')
    for item in (*plan['items'], *plan['smoke_items']):
        (D / 'requests' / f"{item['id']}.json").write_bytes(canonical(item['request_body']))
