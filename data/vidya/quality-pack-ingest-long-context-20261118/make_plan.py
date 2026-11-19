#!/usr/bin/env python3
"""Materialize fixed paired ingest requests and bind their source identities."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import subprocess

import yaml

D = Path(__file__).resolve().parent
LANE = Path('/mnt/raid0/llm/worktrees/mains/h-vidya-belief-substrate')
ARCHIVE = LANE / 'data/vidya/quality-pack-architect-critic-20261118'
ORCH = Path('/mnt/raid0/llm/epyc-orchestrator')
KERNEL = Path('/mnt/raid0/llm/llama.cpp')
PROFILE = 'ingest-long-context-recurrent-no-spec'
ROLE = 'ingest_long_context'
HOST = 'architect_critic'
CONTEXT = 16384
COMMITS = {
    'production': 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115',
    'candidate': 'bda43aa17c11b671e0e203e7eb7bf4f1303bc273',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stat_id(path):
    st = path.stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def write(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)


def inherited_bytes(name, receipt, *, envelope=False):
    relative = name + '.original-bytes.json' if envelope else name
    raw = (ARCHIVE / relative).read_bytes()
    if envelope:
        raw = base64.b64decode(json.loads(raw)['bytes_b64'], validate=True)
    if sha(raw) != receipt['files_sha256'][name]:
        raise ValueError(f'architect packet receipt drift: {name}')
    return raw


def model_profile(architect_plan):
    registry_path = ORCH / 'orchestration/model_registry.yaml'
    priors_path = ORCH / 'orchestration/derived/stack_priors.yaml'
    inventory_path = LANE / '.claude/skills/kernel-promotion/scripts/quality_parity.py'
    sources = {path: path.read_bytes() for path in (registry_path, priors_path, inventory_path)}
    registry = yaml.safe_load(sources[registry_path])
    priors = yaml.safe_load(sources[priors_path])
    inventory_strings = {node.value for node in ast.walk(ast.parse(sources[inventory_path]))
                         if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    model = registry['roles'][ROLE]['model']
    alias = registry['server_mode'][ROLE]
    host = registry['server_mode'][HOST]
    artifact = registry['roles'][alias['model_role']]['model']
    alias_serving = priors['roles'][ROLE]['serving']
    host_serving = priors['roles'][HOST]['serving']
    alias_runtime = alias_serving['launch']['runtime']
    host_runtime = host_serving['launch']['runtime']
    alias_flags, host_flags = alias_runtime['flags'], host_runtime['flags']
    spec = host_flags['spec']
    role_spec = registry['roles'][ROLE]['acceleration']
    cache = host_runtime['cache']
    serving_key = lambda view: (view['server_role'], view['endpoint'],
                                view['effective_context_tokens'], view['slots'])
    if (PROFILE not in inventory_strings or alias['alias_of'] != HOST
            or alias['model_role'] != host['model_role']
            or serving_key(alias_serving) != (HOST, 'http://localhost:8083', 393216, 4)
            or serving_key(host_serving) != serving_key(alias_serving)
            or alias_runtime['cache'] != cache or alias_runtime['binary_path'] != host_runtime['binary_path']
            or (cache['context_tokens'], cache['slots'], cache['kv_type_k'],
                cache['kv_type_v'], cache['kv_unified']) != (393216, 4, 'q8_0', 'q8_0', True)
            or alias_flags['device'] != 'ROCm0' or host_flags['device'] != 'ROCm0'
            or alias['kv_quant'] != {'k': 'q8_0', 'v': 'q8_0'}
            or model['architecture'] != 'qwen35' or model['ctx_max'] != 262144
            or any(model[key] != artifact[key] for key in ('path', 'sha256', 'architecture'))
            or host_serving['launch']['requirements']['model_path'] != model['path']
            or alias_serving['launch']['requirements']['model_path'] != model['path']
            or alias_flags['spec']['enabled'] is not False or alias_flags['spec']['type'] is not None
            or alias_serving['launch']['requirements']['draft_model_path'] != spec['draft_model_path']
            or (spec['enabled'], spec['type'], spec['draft_max'], spec['n_gpu_layers_draft']) !=
                (True, 'draft-dflash', 7, 99)
            or any((entry['inherits_spec_from'], entry['spec_type'], entry['draft_model'], entry['draft_max']) !=
                   (HOST, 'draft-dflash', spec['draft_model_path'], 7)
                   for entry in (role_spec, alias['acceleration']))
            or alias_flags['served_template_sha256'] != host_flags['served_template_sha256']
            or host_flags['served_template_sha256'] != host['chat_template']['served_template_sha256']
            or alias_flags['chat_template_file'] != host['chat_template_file']
            or host_flags['chat_template_file'] != host['chat_template_file']
            or alias['chat_template_kwargs'] != {'enable_thinking': True, 'reasoning_effort': 'medium'}):
        raise ValueError('ingest registry role, alias, host serving recipe, or profile inventory drifted')
    if {name: arm['kernel_commit'] for name, arm in architect_plan['arms'].items()} != COMMITS:
        raise ValueError('architect runtime pin differs from paired v10/C13 commits')

    source = 'src/models/qwen35.cpp'
    gdn = {}
    for name, commit in COMMITS.items():
        raw = subprocess.check_output(['git', '-C', str(KERNEL), 'show', f'{commit}:{source}'])
        if b'linear attention (gated delta net)' not in raw or b'build_recurrent_attn' not in raw:
            raise ValueError(f'{name} lacks the qwen35 gated-delta recurrent path')
        gdn[name] = {'commit': commit, 'path': source, 'sha256': sha(raw)}
    context = {
        'registry_commit': subprocess.check_output(['git', '-C', str(ORCH), 'rev-parse', 'HEAD'],
                                                   text=True).strip(),
        'sources_sha256': {str(path): sha(raw) for path, raw in sources.items()},
        'registry_role': ROLE,
        'registry_model': model['name'],
        'registry_model_architecture': model['architecture'],
        'registry_acceleration': role_spec,
        'qwen35_gdn_source': gdn,
        'compiled_serving_role': HOST,
        'compiled_serving_endpoint': host_serving['endpoint'],
        'compiled_serving_context_tokens': cache['context_tokens'],
        'compiled_serving_slots': cache['slots'],
        'compiled_serving_binary': host_runtime['binary_path'],
        'compiled_serving_device': host_flags['device'],
        'compiled_serving_cache': cache,
        'compiled_host_spec': spec,
        'compiled_alias_spec': alias_flags['spec'],
        'compiled_alias_launch_requirements': alias_serving['launch']['requirements'],
        'compiled_serving_per_request_limit': model['ctx_max'],
        'registry_ingest_chat_template_kwargs': alias['chat_template_kwargs'],
        'serving_interpretation': 'Ingest shares the architect_critic :8083 host with DFlash2 cap 7. '
                                  'The compiled alias view reports speculation disabled while its '
                                  'launch requirements and registry preserve the inherited sidecar.',
    }
    return model, host_flags, context


def request_item(name, prompt, output, expected, *, fixture=None, long=False, limit=80):
    return {
        'id': f'ingest-{name}', 'fixture': fixture, 'dflash_pair': None,
        'prompt_shape': 'long' if long else 'short', 'output_format': output, 'expected_finish': 'stop',
        'validator': {'id': 'json-object-subset.v1' if output == 'json' else 'contains-text.v1',
                      'expected': expected},
        'request_body': {
            'model': 'ingest-long-context-native-capture',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': limit, 'seed': 42, 'temperature': 0, 'cache_prompt': False,
            'stream': False, 'return_tokens': True, 'verbose': True,
            'chat_template_kwargs': {'enable_thinking': False},
        },
    }


def questions():
    paperwork = '\n'.join(
        f'Record {i:03d}. The records desk filed the delivery note with the weekly inventory. '
        'The archive copy has a routine signature and no routing exception.'
        for i in range(1, 148)
    )
    returns = '\n'.join(
        f'Batch {i:03d}. General stock returns were received at the east dock and verified '
        'against the manifest. The clerk returned all samples to standard storage.'
        for i in range(1, 151)
    )
    inspections = '\n'.join(
        f'Inspection {i:03d}. Staff cleared the loading area, counted the empty containers, '
        'checked the labels, and stored the routine checklist with the district notes.'
        for i in range(1, 159)
    )
    return [
        request_item('short-summary',
                     'Summarize this brief in one sentence and name the confirmed cause. '
                     'At 09:10 a dispatch started late. At 09:45 the supervisor ruled out weather. '
                     'The final entry confirms a faulty gate sensor blocked the first departure.',
                     'prose', 'gate sensor', limit=56),
        request_item('early-lookup',
                     'Read the entire archive and answer the final query. '
                     'Master routing record: ARCHIVE BLUEBELL uses depot SANDSTONE.\n' + paperwork +
                     '\nQuery: Which depot does ARCHIVE BLUEBELL use? Reply with the depot name alone.',
                     'prose', 'SANDSTONE', long=True, limit=32),
        request_item('recurrent-state',
                     'Reconcile the chronological file using the latest signed directive for each shipment. '
                     '07:10 signed directive: parcel RAVEN is HOLD.\n' + returns[:returns.index('Batch 076.')] +
                     '\n12:45 signed directive: parcel RAVEN is RELEASE.\n' + returns[returns.index('Batch 076.'):] +
                     '\n17:30 unsigned proposal: parcel RAVEN is HOLD. '
                     'Return a JSON object with shipment and status, using uppercase values.',
                     'json', {'shipment': 'RAVEN', 'status': 'RELEASE'}, fixture='recurrent-state', long=True),
        request_item('document-reconciliation',
                     'Read this inspection register. Only signed exception notices change the ledger. '
                     'A signed exception puts equipment LARK in the NORTH annex.\n' + inspections +
                     '\nAn unsigned worksheet moves LARK to WEST. A signed correction moves LARK to SOUTH. '
                     'Explain in one or two sentences which annex currently holds LARK and why.',
                     'reasoning', 'SOUTH', long=True),
    ]


def main():
    receipt_path = ARCHIVE / 'receipt.json'
    receipt_raw = receipt_path.read_bytes()
    receipt = json.loads(receipt_raw)
    architect_raw = inherited_bytes('plan.json', receipt, envelope=True)
    architect_plan = json.loads(architect_raw)
    model, flags, context = model_profile(architect_plan)
    model_raw = inherited_bytes('model-hash-receipt.json', receipt, envelope=True)
    model_pin = json.loads(model_raw)
    model_path = Path(model['path'])
    template = Path(flags['chat_template_file'])
    template_sha = flags['served_template_sha256']
    if (model_pin['model_path'] != str(model_path) or model_pin['model_sha256'] != model['sha256']
            or model_pin['model_stat'] != stat_id(model_path) or sha(template.read_bytes()) != template_sha
            or architect_plan['architect_critic_model']['original_hash_receipt_sha256'] != sha(model_raw)):
        raise ValueError('model hash receipt, filesystem identity or serving template differs')
    context['architect_packet_receipt'] = {
        'path': str(receipt_path), 'sha256': sha(receipt_raw), 'plan_sha256': sha(architect_raw),
    }
    context['isolated_chat_template_kwargs'] = {'enable_thinking': False}
    smoke_pin = architect_plan['smoke_model']
    frontdoor = architect_plan['prior_frontdoor_json_mismatch']
    for name, expected in (
            ('smoke-model-plan.original-bytes.json', smoke_pin['original_hash_receipt_sha256']),
            ('frontdoor-full-receipt.json', frontdoor['receipt_sha256'])):
        raw = inherited_bytes(name, receipt)
        if sha(raw) != expected:
            raise ValueError(f'inherited witness changed: {name}')
        write(D / name, raw)
    write(D / 'model-hash-receipt.json', model_raw)
    smoke_pin['receipt_snapshot'] = str(D / 'smoke-model-plan.original-bytes.json')
    frontdoor['snapshot'] = str(D / 'frontdoor-full-receipt.json')
    items = questions()
    request_files = {}
    (D / 'requests').mkdir()
    for item in [*items, *architect_plan['smoke_items']]:
        body = canonical(item['request_body'])
        path = f"requests/{item['id']}.json"
        write(D / path, body)
        request_files[item['id']] = {'path': path, 'sha256': sha(body)}
    recipe = {
        'endpoint': '/v1/chat/completions', 'startup_s': 240, 'request_s': 360,
        'speculation': 'none', 'context_tokens': CONTEXT, 'slots': 1,
        'minimum_long_prompt_tokens': 4096, 'kv_type_k': 'q8_0', 'kv_type_v': 'q8_0',
        'kv_unified': False,
        'args': ['--device', 'none', '-ngl', '0', '-ctk', 'q8_0', '-ctv', 'q8_0',
                 '-fa', 'on', '--no-warmup', '-np', '1', '-m', str(model_path), '-c', str(CONTEXT),
                 '-b', '512', '-ub', '512', '--cache-ram', '0', '--no-kv-unified',
                 '--no-context-shift', '--jinja', '--chat-template-file', str(template),
                 '--spec-type', 'none'],
    }
    plan = {
        'schema': 'epyc.native_quality_ingest_long_context_plan.v1',
        'scope': 'isolated bounded ingest input slice with hybrid recurrent state and no speculation',
        'profile': PROFILE,
        'profile_provenance': context,
        'prior_frontdoor_json_mismatch': frontdoor,
        'arms': architect_plan['arms'],
        'ingest_long_context_model': {'path': str(model_path), 'stat': model_pin['model_stat'],
                                      'sha256': model['sha256'], 'original_hash_receipt_sha256': sha(model_raw),
                                      'receipt_snapshot': str(D / 'model-hash-receipt.json')},
        'ingest_long_context_template': {'path': str(template), 'stat': stat_id(template), 'sha256': template_sha},
        'smoke_model': smoke_pin,
        'recipes': {'smoke_control': architect_plan['recipes']['smoke_control'], 'ingest_long_context_slice': recipe},
        'smoke_items': architect_plan['smoke_items'],
        'items': items,
        'request_files': request_files,
        'question_pool_sha256': sha(canonical(items)),
        'broad_pack_status': 'incomplete',
    }
    write(D / 'plan.json', (json.dumps(plan, indent=2, sort_keys=True) + '\n').encode())


if __name__ == '__main__':
    main()
