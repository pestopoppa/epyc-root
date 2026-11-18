#!/usr/bin/env python3
"""Pin the prospectively chosen dense architect-critic CPU/MTP requests."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import subprocess

import yaml

D = Path(__file__).resolve().parent
LANE = Path('/mnt/raid0/llm/worktrees/mains/h-vidya-belief-substrate')
DATA = LANE / 'data/vidya'
ORCH = Path('/mnt/raid0/llm/epyc-orchestrator')
WORKER_PACKET = DATA / 'quality-pack-worker-general-20261118'
PROFILE = 'architect-critic-cpu-mtp'
ROLE = 'architect_critic'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stat_id(path):
    st = path.stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def model_profile():
    registry_path = ORCH / 'orchestration/model_registry.yaml'
    priors_path = ORCH / 'orchestration/derived/stack_priors.yaml'
    inventory_path = LANE / '.claude/skills/kernel-promotion/scripts/quality_parity.py'
    registry_raw, priors_raw, inventory_raw = (p.read_bytes() for p in (registry_path, priors_path, inventory_path))
    registry, priors = map(yaml.safe_load, (registry_raw, priors_raw))
    inventory_strings = {node.value for node in ast.walk(ast.parse(inventory_raw))
                         if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    model = registry['roles'][ROLE]['model']
    server = registry['server_mode'][ROLE]
    artifact = registry['roles'][server['model_role']]
    mtp = artifact['drafters']['mtp']
    live = priors['roles'][ROLE]['serving']
    launch = live['launch']
    flags = launch['runtime']['flags']
    think = server['chat_template_kwargs']
    if (PROFILE not in inventory_strings or live['server_role'] != ROLE
            or launch['requirements']['model_path'] != model['path']
            or any(artifact['model'][key] != model[key] for key in ('path', 'architecture', 'sha256'))
            or model['architecture'] != 'qwen35' or artifact['model']['mtp_capable'] is not True
            or (mtp['spec_type'], mtp['draft_model'], mtp['draft_max']) != ('draft-mtp', model['path'], 4)
            or (flags['device'], flags['spec']['type'], flags['spec']['draft_max']) != ('ROCm0', 'draft-dflash', 7)
            or launch['requirements']['draft_model_path'] != flags['spec']['draft_model_path']
            or flags['chat_template_file'] != server['chat_template_file']
            or flags['served_template_sha256'] != server['chat_template']['served_template_sha256']
            or think != {'enable_thinking': True, 'reasoning_effort': 'medium'}):
        raise ValueError('architect-critic role, serving configuration or embedded MTP witness drifted')
    context = {
        'registry_commit': subprocess.check_output(['git', '-C', str(ORCH), 'rev-parse', 'HEAD'],
                                                   text=True).strip(),
        'sources_sha256': {str(p): sha(raw) for p, raw in (
            (registry_path, registry_raw), (priors_path, priors_raw), (inventory_path, inventory_raw))},
        'registry_role': ROLE,
        'registry_model': model['name'],
        'registry_model_architecture': model['architecture'],
        'compiled_serving_role': live['server_role'],
        'compiled_serving_endpoint': live['endpoint'],
        'compiled_serving_context_tokens': live['effective_context_tokens'],
        'compiled_serving_slots': live['slots'],
        'compiled_serving_binary': launch['runtime']['binary_path'],
        'compiled_serving_device': flags['device'],
        'compiled_serving_spec': flags['spec'],
        'compiled_serving_chat_template_kwargs': think,
        'isolated_mtp_source': f"orchestration/model_registry.yaml:roles.{server['model_role']}.drafters.mtp",
        'isolated_mtp_witness': mtp,
    }
    return model, flags, think, context


def request_item(name, prompt, format_, expected, think, *, limit=128, finish='stop', shape='short'):
    validator = 'json-object-subset.v1' if format_ == 'json' else 'contains-text.v1'
    return {
        'id': f'architect-critic-{name}', 'fixture': None, 'dflash_pair': None,
        'prompt_shape': shape, 'output_format': format_, 'expected_finish': finish,
        'validator': {'id': validator, 'expected': expected},
        'request_body': {'model': 'architect-critic-native-capture',
                         'messages': [{'role': 'user', 'content': prompt}],
                         'max_tokens': limit, 'seed': 42, 'temperature': 0, 'cache_prompt': False,
                         'stream': False, 'return_tokens': True, 'verbose': True,
                         'chat_template_kwargs': think},
    }


def main():
    model, flags, think, context = model_profile()
    model_path = Path(model['path'])
    template = Path(flags['chat_template_file'])
    template_sha = flags['served_template_sha256']
    model_receipt = D / 'model-hash-receipt.json'
    model_raw = model_receipt.read_bytes()
    model_pin = json.loads(model_raw)
    head_receipt = D / 'model-gguf-head.json'
    head_raw = head_receipt.read_bytes()
    head = json.loads(head_raw)
    if (model_pin['model_path'] != str(model_path) or model_pin['model_sha256'] != model['sha256']
            or model_pin['model_stat'] != stat_id(model_path) or sha(template.read_bytes()) != template_sha
            or head['model_path'] != str(model_path) or head['model_stat'] != model_pin['model_stat']
            or head['architecture'] != 'qwen35' or head['nextn_predict_layers'] != 1
            or 'blk.64.nextn.eh_proj.weight' not in head['nextn_tensors']):
        raise ValueError('model hash, embedded MTP head or serving template differs from its witness')
    context['isolated_mtp_gguf_head_sha256'] = sha(head_raw)
    upstream_plan = WORKER_PACKET / 'plan.json.original-bytes.json'
    upstream_bytes = base64.b64decode(json.loads(upstream_plan.read_bytes())['bytes_b64'], validate=True)
    prior_receipt = json.loads((WORKER_PACKET / 'receipt.json').read_bytes())
    if sha(upstream_bytes) != prior_receipt['files_sha256']['plan.json']:
        raise ValueError('pinned worker plan bytes differ from their receipt')
    prior_plan = json.loads(upstream_bytes)
    smoke_pin = prior_plan['smoke_model']
    frontdoor = prior_plan['prior_frontdoor_json_mismatch']
    for source, target, digest in (
            (WORKER_PACKET / 'smoke-model-plan.original-bytes.json', D / 'smoke-model-plan.original-bytes.json',
             smoke_pin['original_hash_receipt_sha256']),
            (WORKER_PACKET / 'frontdoor-full-receipt.json', D / 'frontdoor-full-receipt.json',
             frontdoor['receipt_sha256'])):
        raw = source.read_bytes()
        if sha(raw) != digest:
            raise ValueError(f'inherited witness changed: {source}')
        with target.open('xb') as out:
            out.write(raw)
    smoke_pin['receipt_snapshot'] = str(D / 'smoke-model-plan.original-bytes.json')
    frontdoor['snapshot'] = str(D / 'frontdoor-full-receipt.json')
    items = [
        request_item('json', 'Critique a deployment plan that migrates the only database before verifying '
                            'its backup. Respond with one JSON object using exactly the keys "verdict" '
                            'and "fatal_flaw". Use verdict "reject".', 'json', {'verdict': 'reject'}, think),
        request_item('code', 'A cutover script ignores whether its rollback backup was verified. Write only '
                            'a Python function named block_unsafe_cutover(backup_verified) that raises '
                            'ValueError on False.', 'code', 'def block_unsafe_cutover(', think),
        request_item('reasoning', 'A deployment must keep at least 4 healthy nodes. Six nodes are healthy. '
                                 'A plan takes 3 nodes down at once. Identify the violated constraint and '
                                 'give the largest safe batch size as a digit.', 'reasoning', '2', think),
        request_item('long-prose', ('Irrelevant appendix: tickets use a weekly triage meeting and green '
                                  'labels denote reviewed work. Inventory reports run monthly. ' * 24) +
                            'Proposed plan: delete the existing storage before the replacement is restored. '
                            'Give a detailed plain-language critique starting with Reject.', 'prose', 'Reject',
                     think, limit=32, finish='length', shape='long'),
    ]
    common = ['--device', 'none', '-ngl', '0', '-ctk', 'q8_0', '-ctv', 'q8_0', '-fa', 'on',
              '--no-warmup', '-np', '1']
    cap = context['isolated_mtp_witness']['draft_max']
    plan = {
        'schema': 'epyc.native_quality_architect_critic_plan.v1',
        'scope': 'isolated bounded architect-critic CPU/MTP slice',
        'profile': PROFILE,
        'profile_provenance': context,
        'prior_frontdoor_json_mismatch': frontdoor,
        'arms': prior_plan['arms'],
        'architect_critic_model': {'path': str(model_path), 'stat': model_pin['model_stat'],
                                   'sha256': model['sha256'], 'original_hash_receipt_sha256': sha(model_raw),
                                   'receipt_snapshot': str(model_receipt)},
        'architect_critic_template': {'path': str(template), 'stat': stat_id(template), 'sha256': template_sha},
        'smoke_model': smoke_pin,
        'recipes': {
            'smoke_control': prior_plan['recipes']['smoke_control'],
            'architect_critic_slice': {
                'endpoint': '/v1/chat/completions', 'startup_s': 240, 'request_s': 105, 'mtp_cap': cap,
                'args': [*common, '-m', str(model_path), '-c', '4096', '-b', '512', '-ub', '512',
                         '--cache-ram', '0', '--jinja', '--chat-template-file', str(template),
                         '--spec-type', 'draft-mtp', '--spec-draft-n-max', str(cap)],
            },
        },
        'smoke_items': prior_plan['smoke_items'],
        'items': items,
        'question_pool_sha256': sha(canonical(items)),
        'broad_pack_status': 'incomplete',
    }
    with (D / 'plan.json').open('x') as out:
        json.dump(plan, out, indent=2, sort_keys=True)
        out.write('\n')


if __name__ == '__main__':
    main()
