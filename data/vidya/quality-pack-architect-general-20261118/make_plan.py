#!/usr/bin/env python3
"""Pin the isolated qwen4exp HIP recipe, witnesses and exact request bytes before booking."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from capture import D, PROFILE, canonical, file_sha, sha, stat_id, write, write_json

ROOT = Path('/mnt/raid0/llm/worktrees/mains/h-vidya-belief-substrate')
HOST = Path('/mnt/raid0/llm')
ORCH = HOST / 'epyc-orchestrator'
INGEST = ROOT / 'data/vidya/quality-pack-ingest-long-context-20261118'
NPD1 = ROOT / 'data/vidya/mi210-paired-wire-20261117/npd1-deployment.json'
KERNELS = HOST / 'kernels'
COMMITS = {'production': 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115',
           'candidate': 'bda43aa17c11b671e0e203e7eb7bf4f1303bc273'}
BUILDS = {'production': 'gpu-20260921-ffc1bac82',
          'candidate': 'gpu-20261117-bda43aa17-c13'}
ROCM = Path('/opt/rocm/lib').resolve(strict=True)
ROCM_DSOS = ('libamdhip64', 'libhipblas', 'librocblas', 'libhsa-runtime64')
SELECTED_LAYERS = 24
CONTEXT = 4096


def pin(path, expected=None):
    path = Path(path).resolve(strict=True)
    before = stat_id(path)
    digest = file_sha(path)
    if before != stat_id(path) or (expected is not None and digest != expected):
        raise ValueError(f'published content digest or file identity differs: {path}')
    return {'path': str(path), 'stat': before, 'sha256': digest}


def runtime(name, rocm):
    build = KERNELS / 'builds' / BUILDS[name]
    binpath = build / 'bin'
    candidate = name == 'candidate'
    inputs = ('SHA256SUMS.c13', 'BUILD-IDENTITY.json', 'BUILD-OK.json') if candidate else ('SHA256SUMS', 'PROVENANCE.md')
    manifest = dict((parts[1], parts[0]) for line in (build / inputs[0]).read_text().splitlines()
                    if (parts := line.split()))
    if candidate:
        for source in inputs[1:]:
            identity = json.loads((build / source).read_bytes())
            if identity['source_sha'] != COMMITS[name] or identity['kind'] != 'gpu':
                raise ValueError(f'candidate build identity differs: {source}')
        tree = json.loads((build / 'BUILD-IDENTITY.json').read_bytes())['source_tree']
    else:
        if (KERNELS / 'production/gpu').resolve(strict=True) != binpath:
            raise ValueError('frozen GPU store target differs')
        if COMMITS[name][:9] not in (build / 'PROVENANCE.md').read_text():
            raise ValueError('frozen GPU provenance commit differs')
        tree = subprocess.check_output(['git', '-C', str(HOST / 'llama.cpp'), 'rev-parse',
                                        COMMITS[name] + '^{tree}'], text=True).strip()
    basenames = ('llama-server', 'libllama.so', 'libllama-common.so', 'libllama-server-impl.so',
                 'libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libggml-hip.so')
    files = {}
    for basename in basenames:
        real = (binpath / basename).resolve(strict=True)
        identity = pin(real, manifest[str(real.relative_to(build))])
        files[str(real)] = identity
    binary = str(binpath / 'llama-server')
    ld_env = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': f'{binpath}:{ROCM}'}
    linkage = {}
    for target in (Path(binary), binpath / 'libllama-server-impl.so', binpath / 'libggml-hip.so'):
        raw = subprocess.check_output(['/usr/bin/ldd', str(target)], env=ld_env, text=True)
        if 'not found' in raw:
            raise ValueError(f'unresolved dependencies: {target}')
        for line in raw.splitlines():
            fields = line.split()
            if len(fields) > 2 and fields[1] == '=>':
                resolved = str(Path(fields[2]).resolve(strict=True))
                if fields[0].startswith(('libggml', 'libllama')) and resolved not in files:
                    raise ValueError(f'cross-store dependency: {line}')
                if fields[0].startswith(ROCM_DSOS):
                    if resolved not in rocm:
                        raise ValueError(f'unpinned ROCm dependency: {line}')
                    linkage[fields[0]] = resolved
    if set(linkage.values()) != set(rocm):
        raise ValueError('ROCm linkage differs from prepared pins')
    return {'kernel_commit': COMMITS[name], 'kernel_tree': tree, 'binary': binary,
            'runtime_files': files, 'rocm_files': rocm, 'rocm_linkage': linkage,
            'ld_library_path': ld_env['LD_LIBRARY_PATH'],
            'build_witnesses': [pin(build / source) for source in inputs]}


def profile():
    source = D.parent / 'quality-profile-next-inputs.json'
    source_raw = source.read_bytes()
    original = json.loads(source_raw)
    registry_path = Path(original['registry_path'])
    priors_path = ORCH / 'orchestration/derived/stack_priors.yaml'
    inventory = ROOT / '.claude/skills/kernel-promotion/scripts/quality_parity.py'
    registry_raw = registry_path.read_bytes()
    priors_raw = priors_path.read_bytes()
    registry = yaml.safe_load(registry_raw)
    deployed = yaml.safe_load(priors_raw)['roles']['architect_general']['serving']
    deployed_runtime = deployed['launch']['runtime']
    source_model = registry['roles']['architect_general']['model']
    mode = registry['server_mode']['architect_general']
    role_model = registry['roles'][mode['model_role']]['model']
    if (PROFILE not in inventory.read_text() or original['required_profile'] != PROFILE
            or original['registry_sha256'] != sha(registry_raw)
            or original['model'] != source_model or original['observed_server_mode'] != json.loads(json.dumps(mode, default=str))
            or any(source_model[key] != role_model[key] for key in ('path', 'sha256', 'architecture'))
            or (source_model['architecture'], source_model['split_count'], source_model['block_count']) != ('qwen4exp', 3, 48)
            or deployed['launch']['requirements']['model_path'] != source_model['path']
            or deployed_runtime['flags']['device'] is not None
            or '/cpu-' not in deployed_runtime['binary_path']
            or deployed_runtime['flags']['chat_template_file'] is not None
            or deployed_runtime['flags']['spec']['type'] != 'draft-mtp'
            or deployed_runtime['flags']['spec']['draft_max'] != 4):
        raise ValueError('registry and compiled CPU/MTP identity differ from the prepared source view')

    npd_raw = NPD1.read_bytes()
    by_path = {entry['path']: entry for entry in json.loads(npd_raw)['model_prepared_identities']}
    first = Path(source_model['path'])
    names = {first.name: source_model['sha256'], **source_model['shard_sha256']}
    model = []
    for name, digest in sorted(names.items()):
        path = first.parent / name
        witness = by_path[str(path)]
        values = [witness['prepared_stat'][k] for k in ('device', 'inode', 'size_bytes', 'mtime_ns', 'ctime_ns')]
        if (witness['error'] is not None or witness['sha256'] != digest
                or stat_id(path) != values or path.resolve(strict=True) != path):
            raise ValueError(f'shard differs from original content witness: {path}')
        model.append({'path': str(path), 'stat': values, 'sha256': digest})
    if len(model) != 3 or model[0]['path'] != str(first):
        raise ValueError('split roster drift')

    sys.path.insert(0, str(ORCH))
    from src.registry.artifact_integrity import read_gguf_chat_template

    template_raw = read_gguf_chat_template(first)
    expected = mode['chat_template']['served_template_sha256']
    if (not template_raw or sha(template_raw) != expected or stat_id(first) != model[0]['stat']
            or deployed_runtime['flags']['served_template_sha256'] != expected):
        raise ValueError('embedded GGUF template differs from the serve registry')
    template_path = D / 'chat-template.jinja'
    write(template_path, template_raw)
    write(D / 'model-hash-receipt.json', npd_raw)
    write(D / 'profile-source.json', source_raw)
    return model, pin(template_path, expected), {
        'profile_source_snapshot_sha256': sha(source_raw),
        'inventory_sha256': file_sha(inventory),
        'registry_sha256': sha(registry_raw),
        'compiled_priors_sha256': sha(priors_raw),
        'template_source': {'gguf': str(first), 'key': 'tokenizer.chat_template'},
        'model_hash_witness': {'snapshot': str(D / 'model-hash-receipt.json'), 'sha256': sha(npd_raw)},
        'compiled_deployed_serving': deployed,
    }


def item(name, prompt, output_format, reference):
    return {'id': f'architect-general-hip-{name}', 'format': output_format, 'reference': reference,
            'prompt_shape': 'short',
            'request_body': {'model': 'architect-general-hip', 'stream': False,
                             'messages': [{'role': 'user', 'content': prompt}],
                             'chat_template_kwargs': {'enable_thinking': False},
                             'temperature': 0, 'seed': 35, 'max_tokens': 80,
                             'cache_prompt': False, 'return_tokens': True, 'verbose': True}}


def main():
    model, template, sources = profile()
    smoke_plan_envelope = json.loads((INGEST / 'plan.json.original-bytes.json').read_bytes())
    import base64
    smoke_plan = json.loads(base64.b64decode(smoke_plan_envelope['bytes_b64'], validate=True))
    if smoke_plan['profile'] != 'ingest-long-context-recurrent-no-spec':
        raise ValueError('unexpected smoke source plan')
    smoke_model = smoke_plan['smoke_model']
    witness = INGEST / 'smoke-model-plan.original-bytes.json'
    if file_sha(witness) != smoke_model['original_hash_receipt_sha256'] or stat_id(Path(smoke_model['path'])) != smoke_model['stat']:
        raise ValueError('CPU smoke model witness differs')
    shutil.copyfile(witness, D / witness.name)
    smoke_model['receipt_snapshot'] = str(D / witness.name)
    frontdoor = smoke_plan['prior_frontdoor_json_mismatch']
    mismatch = INGEST / 'frontdoor-full-receipt.json'
    if file_sha(mismatch) != frontdoor['receipt_sha256']:
        raise ValueError('frontdoor mismatch witness differs')
    shutil.copyfile(mismatch, D / mismatch.name)
    frontdoor['snapshot'] = str(D / mismatch.name)

    rocm = {}
    for name in ROCM_DSOS:
        identity = pin(ROCM / f'{name}.so')
        rocm[identity['path']] = identity
    (D / 'requests').mkdir()
    items = [
        item('json', 'Return only a JSON object with keys route, enabled and replicas. Use the values "amber", true, and 3 respectively.',
             'json', {'route': 'amber', 'enabled': True, 'replicas': 3}),
        item('code', 'Return only a Python expression that takes the sorted unique values from a list called "codes".',
             'code', 'sorted(set(codes))'),
        item('reasoning', 'Only Gate A permits northbound buses and Gate B permits northbound and southbound cars. The vehicle is a southbound car. Explain in one sentence which gate it may use.',
             'reasoning', 'Gate B'),
        item('prose', 'Summarize this note in two short sentences: Iris reviewed the migration at noon. The migration was delayed until Friday because a backup check was outstanding. Rowan owns that check.',
             'prose', 'Migration delayed until Friday pending the backup check. Rowan owns the check.'),
    ]
    request_files = {}
    for entry in items + smoke_plan['smoke_items']:
        path = f"requests/{entry['id']}.json"
        body = canonical(entry['request_body'])
        write(D / path, body)
        request_files[entry['id']] = {'path': path, 'sha256': sha(body)}

    recipe = {'device': 'ROCm0', 'gpu_id': 25466, 'render_minor': 128, 'kfd_topology_node': 4,
              'max_vram_bytes': 60 * 2**30, 'cpu_affinity': list(range(184, 192)),
              'offloaded_layers': SELECTED_LAYERS, 'speculation': 'none', 'slots': 1,
              'context_tokens': CONTEXT, 'kv_type_k': 'f16', 'kv_type_v': 'f16',
              'kv_unified': False, 'batch': 256, 'ubatch': 256, 'mmap': True,
              'endpoint': '/v1/chat/completions', 'startup_s': 330, 'request_s': 160,
              'args': ['--alias', PROFILE, '--device', 'ROCm0', '-ngl', str(SELECTED_LAYERS), '--fit', 'off',
                       '--split-mode', 'none', '--main-gpu', '0', '-ctk', 'f16', '-ctv', 'f16',
                       '-fa', 'on', '--no-warmup', '-np', '1', '-m', model[0]['path'],
                       '-c', str(CONTEXT), '-b', '256', '-ub', '256', '--cache-ram', '0',
                       '--mmap', '--no-kv-unified', '--no-context-shift', '--jinja',
                       '--chat-template-file', template['path'], '--spec-type', 'none']}
    write_json(D / 'plan.json', {
        'schema': 'epyc.native_quality_architect_general_hip_plan.v1',
        'scope': 'One-MI210 isolated text-only hybrid HIP offload, no speculation, four fixed requests per arm.',
        'profile': PROFILE, 'profile_provenance': sources, 'model_shards': model, 'template': template,
        'arms': {name: runtime(name, rocm) for name in COMMITS}, 'smoke_runtime': smoke_plan['arms']['production'],
        'smoke_model': smoke_model, 'prior_frontdoor_json_mismatch': frontdoor,
        'recipes': {'smoke_control': smoke_plan['recipes']['smoke_control'], 'hip_slice': recipe},
        'smoke_items': smoke_plan['smoke_items'], 'items': items,
        'request_files': request_files, 'question_pool_sha256': sha(canonical(items)),
    })


if __name__ == '__main__':
    main()
