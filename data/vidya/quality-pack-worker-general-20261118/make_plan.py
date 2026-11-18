#!/usr/bin/env python3
"""Prepare a typed, truthful slice from existing kernel/model provenance."""
import base64
import hashlib
import json
import subprocess

import yaml
from pathlib import Path

D = Path(__file__).resolve().parent
STORE = Path('/mnt/raid0/llm/kernels')
ORCHESTRATOR = Path('/mnt/raid0/llm/epyc-orchestrator')
LANE = Path('/mnt/raid0/llm/worktrees/mains/h-vidya-belief-substrate')
FRONTDOOR = LANE / 'data/vidya/quality-pack-native-20261118'
PROFILE = 'worker-general-cpu-moe-mtp'
ROLE = 'worker_general'
PREP = Path('/mnt/raid0/llm/tmp/v11-promotion-checklist/sealed-calibration/pins.json')


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def file_pin(path, digest):
    st = path.stat()
    return {'path': str(path), 'sha256': digest,
            'stat': [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]}


def runtime(base, manifest_name, commit, tree):
    build = STORE / 'builds' / base
    binary = (build / 'bin/llama-server').resolve(strict=True)
    libs = ('libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libllama.so',
            'libllama-common.so', 'libllama-server-impl.so')
    files = [binary, *((binary.parent / name).resolve(strict=True) for name in libs)]
    manifest = build / manifest_name
    digests = {file.removeprefix('*'): digest for digest, file in
               (line.split(maxsplit=1) for line in manifest.read_text().splitlines())}
    pins = {str(path): digests[str(path.relative_to(build))] for path in files}
    if any(sha(Path(path)) != digest for path, digest in pins.items()):
        raise ValueError(f'{base} content differs from independently recorded runtime manifest')
    return {'binary': str(binary), 'kernel_commit': commit, 'kernel_tree': tree,
            'binary_sha256': pins[str(binary)], 'runtime_files': pins,
            'build_manifest': str(manifest), 'build_manifest_sha256': sha(manifest)}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def worker_item(name, prompt, output_format, expected, *, limit=96, finish='stop', shape='short'):
    validator = 'json-object-subset.v1' if output_format == 'json' else 'contains-text.v1'
    return {'id': f'worker-general-{name}', 'fixture': None, 'dflash_pair': None, 'prompt_shape': shape,
            'output_format': output_format, 'expected_finish': finish,
            'validator': {'id': validator, 'expected': expected},
            'request_body': {'model': 'worker-general-native-capture',
                             'messages': [{'role': 'user', 'content': prompt}],
                             'max_tokens': limit, 'seed': 42, 'temperature': 0, 'cache_prompt': False,
                             'stream': False, 'return_tokens': True, 'verbose': True,
                             'chat_template_kwargs': {'enable_thinking': False}}}


def model_profile():
    registry_path = ORCHESTRATOR / 'orchestration/model_registry.yaml'
    priors_path = ORCHESTRATOR / 'orchestration/derived/stack_priors.yaml'
    gates_path = LANE / '.claude/skills/kernel-promotion/promotion_gates.yaml'
    registry_bytes, priors_bytes, gates_bytes = (p.read_bytes() for p in (registry_path, priors_path, gates_path))
    registry, priors, gates = (yaml.safe_load(raw) for raw in (registry_bytes, priors_bytes, gates_bytes))
    worker = registry['roles'][ROLE]
    shared = registry['server_mode']['frontdoor']
    live = priors['roles'][ROLE]['serving']
    flags = live['launch']['runtime']['flags']
    model = worker['model']
    acceleration = worker['acceleration']
    if (ROLE not in gates['gates']['quality']['roles'] or ROLE not in shared['shared_with']
            or live['server_role'] != 'frontdoor' or live['launch']['requirements']['model_path'] != model['path']
            or model['architecture'] != 'qwen35moe' or model['mtp_capable'] is not True
            or (acceleration['spec_type'], acceleration['draft_max']) != ('draft-mtp', 4)
            or model['kv_cache'] != {'type_k': 'q8_0', 'type_v': 'q8_0'}
            or flags['reasoning'] != 'off' or flags['flash_attn'] is not True
            or flags['jinja'] is not True or shared['chat_template_kwargs'] != {'enable_thinking': False}):
        raise ValueError('pinned worker-general role/model or recipe inputs drifted')
    if model['path'] != shared['model_path'] or flags['chat_template_file'] != shared['chat_template_file']:
        raise ValueError('worker-general and shared template/model binding disagrees')
    context = {
        'registry_commit': subprocess.check_output(['git', '-C', str(ORCHESTRATOR), 'rev-parse', 'HEAD'],
                                                   text=True).strip(),
        'sources_sha256': {str(p): hashlib.sha256(raw).hexdigest()
                            for p, raw in ((registry_path, registry_bytes), (priors_path, priors_bytes),
                                           (gates_path, gates_bytes))},
        'registry_role': ROLE,
        'registry_model': model['name'],
        'registry_model_architecture': model['architecture'],
        'registry_worker_acceleration': {'spec_type': acceleration['spec_type'], 'draft_max': acceleration['draft_max']},
        'compiled_serving_role': live['server_role'],
        'compiled_serving_context_tokens': live['effective_context_tokens'],
        'compiled_serving_slots': live['slots'],
        'compiled_serving_spec': flags['spec'],
        'gate_model_lineage': 'Promotion gates retain pre-lineup Gemma4 v10 worker-general history. '
                              'Current worker-general registry and compiled priors resolve to Qwen3.6 MoE.',
    }
    return model, flags, context


def main():
    model_entry, flags, context = model_profile()
    model = Path(model_entry['path'])
    template = Path(flags['chat_template_file'])
    template_sha = flags['served_template_sha256']
    prepared_raw = PREP.read_bytes()
    prepared = json.loads(prepared_raw)
    small_plan = FRONTDOOR / 'plan.json.original-bytes.json'
    small_receipt = json.loads((FRONTDOOR / 'receipt.json').read_bytes())
    small_envelope_raw = small_plan.read_bytes()
    small_envelope = json.loads(small_envelope_raw)
    small_raw = base64.b64decode(small_envelope['bytes_b64'], validate=True)
    if hashlib.sha256(small_raw).hexdigest() != small_receipt['files_sha256']['plan.json']:
        raise ValueError('frontdoor original plan differs from its receipt')
    small_pin = json.loads(small_raw)['smoke_model']
    if small_pin['stat'] != file_pin(Path(small_pin['path']), small_pin['sha256'])['stat']:
        raise ValueError('inherited smoke model stat drifted')

    production = runtime('cpu-20260921-ffc1bac82', 'SHA256SUMS',
                         'ffc1bac82eeca6f9099e1ccd9ba49703c460a115', 'a7c564ffbac0a86ce648ef6f11c1748c81a6560d')
    candidate = runtime('cpu-20261117-bda43aa17-c13', 'SHA256SUMS.c13',
                        'bda43aa17c11b671e0e203e7eb7bf4f1303bc273', 'e6dc8715fa3374406b38de48571e8700bded094f')
    candidate_build = Path(candidate['binary']).parent.parent / 'BUILD-IDENTITY.json'
    build = json.loads(candidate_build.read_text())
    if (build['source_sha'], build['source_tree']) != (candidate['kernel_commit'], candidate['kernel_tree']):
        raise ValueError('C13 build manifest source identity differs')
    candidate['build_identity'] = str(candidate_build)
    candidate['build_identity_sha256'] = sha(candidate_build)
    model_pin = file_pin(model, prepared['model_sha256'])
    if (model_pin['stat'] != prepared['model_stat'] or model_pin['sha256'] != model_entry['sha256']
            or sha(template) != template_sha):
        raise ValueError('prepared model or recorded template identity changed')
    frontdoor_receipt_path = FRONTDOOR / 'full-capture/receipt.json'
    frontdoor_raw = frontdoor_receipt_path.read_bytes()
    frontdoor = json.loads(frontdoor_raw)
    prior_json = next(row for row in frontdoor['raw_derived_comparisons'] if row['id'] == 'json')
    if prior_json['content_equal'] is not False or prior_json['token_ids_equal'] is not False:
        raise ValueError('frontdoor mismatch receipt drifted')
    for name, raw in (('worker-model-hash-receipt.json', prepared_raw),
                      ('smoke-model-plan.original-bytes.json', small_envelope_raw),
                      ('frontdoor-full-receipt.json', frontdoor_raw)):
        with (D / name).open('xb') as stream:
            stream.write(raw)
    common = ['--device', 'none', '-ngl', '0', '-ctk', 'q8_0', '-ctv', 'q8_0', '-fa', 'on', '--no-warmup', '-np', '1']
    items = [
        worker_item('json', 'Extract the issue number and state as one JSON object with keys "issue" and "state". '
                            'Source: issue 47 moved from review to closed. Return only the JSON object.',
                    'json', {'issue': 47, 'state': 'closed'}),
        worker_item('code', 'Write one Python function named normalize_status(value). It strips surrounding whitespace '
                            'and lowercases the supplied string. Output only Python code.', 'code', 'def normalize_status('),
        worker_item('reasoning', 'A worker resolved 8 of 19 tickets on Monday and 6 more on Tuesday. Explain the subtraction '
                                 'and state how many tickets remain in one sentence.', 'reasoning', '5'),
        worker_item('long-prose', ('Repeated boilerplate: support rotations change on Fridays; checklists are stored '
                                  'in the shared folder; unresolved tickets remain in the weekly queue. ' * 20) +
                    'Actual incident: the queue is now unblocked because the service credential was rotated. '
                    'Write a long incident handoff note starting with the word Unblocked.', 'prose', 'Unblocked',
                    limit=16, finish='length', shape='long'),
    ]
    plan = {
        'schema': 'epyc.native_quality_worker_general_plan.v1',
        'scope': 'isolated bounded worker-general CPU/MTP slice',
        'profile': PROFILE,
        'profile_provenance': context,
        'prior_frontdoor_json_mismatch': {'receipt': str(frontdoor_receipt_path),
                                         'receipt_sha256': hashlib.sha256(frontdoor_raw).hexdigest(),
                                         'comparison': prior_json, 'snapshot': str(D / 'frontdoor-full-receipt.json')},
        'arms': {'production': production, 'candidate': candidate},
        'worker_general_model': {**model_pin, 'original_hash_receipt': str(PREP),
                                 'original_hash_receipt_sha256': hashlib.sha256(prepared_raw).hexdigest(),
                                 'receipt_snapshot': str(D / 'worker-model-hash-receipt.json')},
        'worker_general_template': file_pin(template, template_sha),
        'smoke_model': {**small_pin, 'original_hash_receipt': str(small_plan),
                        'original_hash_receipt_sha256': hashlib.sha256(small_envelope_raw).hexdigest(),
                        'receipt_snapshot': str(D / 'smoke-model-plan.original-bytes.json')},
        'recipes': {
            'smoke_control': {'endpoint': '/completion', 'startup_s': 45, 'request_s': 30,
                              'args': [*common, '-m', small_pin['path'], '-c', '512', '--spec-type', 'none']},
            'worker_general_slice': {'endpoint': '/v1/chat/completions', 'startup_s': 240, 'request_s': 75,
                                     'args': [*common, '-m', str(model), '-c', '4096', '-ub', '512', '--jinja',
                                              '--chat-template-file', str(template), '--reasoning', 'off',
                                              '--spec-type', 'draft-mtp', '--spec-draft-n-max', '4']},
        },
        'smoke_items': [{'id': 'native-smoke', 'request_body': {
            'prompt': 'The first four positive integers are 1, 2, 3,', 'n_predict': 8,
            'seed': 35, 'temperature': 0, 'cache_prompt': False, 'stream': False, 'return_tokens': True}}],
        'items': items,
        'question_pool_sha256': hashlib.sha256(canonical(items)).hexdigest(),
        'broad_pack_status': 'incomplete',
    }
    with (D / 'plan.json').open('x') as out:
        json.dump(plan, out, indent=2, sort_keys=True)
        out.write('\n')


if __name__ == '__main__':
    main()
