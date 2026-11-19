#!/usr/bin/env python3
"""Prepare and seal Worker Vision packets before scheduling any model load."""

import base64
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

import yaml

from capture import (D, PROFILE, canonical, file_sha, sha, stat_id, verify_pin,
                     verify_vision_inputs, write, write_json)

ROOT = Path('/mnt/raid0/llm/worktrees/mains/h-vidya-belief-substrate')
HOST = Path('/mnt/raid0/llm')
ORCH = HOST / 'epyc-orchestrator'
SOURCE = ROOT / 'data/vidya/quality-pack-architect-general-20261118'
EXPECTED_SOURCE = ROOT / 'data/mi210/m4-fold-binding-review-20261104/FOLD-PLAN.json'
COMMITS = {'production': 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115',
           'candidate': 'bda43aa17c11b671e0e203e7eb7bf4f1303bc273'}
IMAGE_SIZE = 896
IMAGE_MIN_TOKENS = 1024


def pin(path, expected):
    path = path.resolve(strict=True)
    before = stat_id(path)
    if file_sha(path) != expected or before != stat_id(path):
        raise ValueError(f'published content digest or file identity differs: {path}')
    return {'path': str(path), 'stat': before, 'sha256': expected}


def archived_bytes(path):
    receipt = json.loads(path.read_bytes())
    raw = base64.b64decode(receipt['bytes_b64'], validate=True)
    if sha(raw) != receipt['sha256']:
        raise ValueError(f'original bytes differ from envelope digest: {path}')
    return raw


def vision_runtime(arm, runtime):
    if runtime['kernel_commit'] != COMMITS[arm]:
        raise ValueError(f'unexpected kernel source for {arm}')
    bdir = Path(runtime['binary']).parent
    if arm == 'production' and (HOST / 'kernels/production/gpu').resolve(strict=True) != bdir:
        raise ValueError('frozen production GPU link differs from prepared store')
    for identity in (*runtime['build_witnesses'], *runtime['runtime_files'].values(),
                     *runtime['rocm_files'].values()):
        verify_pin(identity, verify_digest=True)

    manifest = Path(runtime['build_witnesses'][0]['path'])
    records = {name: digest for line in manifest.read_text().splitlines() if line.strip()
               for digest, name in [line.split()]}
    mtmd = (bdir / 'libmtmd.so').resolve(strict=True)
    runtime['mtmd_library'] = pin(mtmd, records[str(mtmd.relative_to(bdir.parent))])
    env = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': runtime['ld_library_path']}
    linkage = HOST / 'epyc-inference-research/scripts/utils/verify_ggml_linkage.sh'
    report = subprocess.check_output([str(linkage), runtime['binary'], str(bdir.parent)], env=env)
    observed = subprocess.check_output(['/usr/bin/ldd', str(bdir / 'libllama-server-impl.so')], env=env, text=True)
    libs = [Path(row.split()[2]).resolve(strict=True) for row in observed.splitlines()
            if row.lstrip().startswith('libmtmd.so') and 'not found' not in row]
    if libs != [mtmd] or 'not found' in observed:
        raise ValueError(f'multimodal linkage differs from prepared store for {arm}')
    write(D / f'{arm}-linkage.txt', report + observed.encode())
    return runtime


def profile():
    registry_path = ORCH / 'orchestration/model_registry.yaml'
    priors_path = ORCH / 'orchestration/derived/stack_priors.yaml'
    inventory = ROOT / '.claude/skills/kernel-promotion/scripts/quality_parity.py'
    registry_raw, priors_raw = registry_path.read_bytes(), priors_path.read_bytes()
    registry = yaml.safe_load(registry_raw)
    registered = registry['roles']['worker_vision']
    role_model = registered['model']
    mode = registry['server_mode']['worker_vision']
    deployed = yaml.safe_load(priors_raw)['roles']['worker_vision']['serving']
    runtime = deployed['launch']['runtime']
    launch_artifacts = deployed['launch']['requirements']
    if (f'"{PROFILE}"' not in inventory.read_text()
            or role_model['architecture'] != 'qwen3vlmoe' or role_model['quant'] != 'Q4_K_M'
            or any(role_model[key] != mode['model'][key] for key in ('path', 'mmproj_path', 'architecture', 'quant'))
            or launch_artifacts['model_path'] != role_model['path']
            or launch_artifacts['mmproj_path'] != role_model['mmproj_path']
            or runtime['flags']['device'] != 'none' or runtime['flags']['spec']['enabled'] is not False
            or '/cpu-' not in runtime['binary_path'] or runtime['flags']['image_min_tokens'] != IMAGE_MIN_TOKENS):
        raise ValueError('registry and compiled deployment differ from the declared Worker Vision source')

    witness_path = D / 'model-hash-receipt.json'
    witness = json.loads(witness_path.read_bytes())
    expected_source_raw = EXPECTED_SOURCE.read_bytes()
    expected_digests = json.loads(expected_source_raw)['models']
    weights, projector = witness['files']
    if (witness['schema'] != 'epyc.native_quality_pregrant_model_hash.v1'
            or witness['expected_source_sha256'] != sha(expected_source_raw)
            or weights['path'] != role_model['path'] or projector['path'] != role_model['mmproj_path']
            or weights['sha256'] != role_model['sha256']
            or any(expected_digests[pin['path']] != pin['sha256'] for pin in (weights, projector))):
        raise ValueError('pregrant hash receipt does not match the model registry and fold content pins')
    verify_pin(weights)
    verify_pin(projector)

    sys.path.insert(0, str(ORCH))
    from src.registry.artifact_integrity import read_gguf_chat_template

    expected = mode['chat_template']['served_template_sha256']
    content = read_gguf_chat_template(weights['path'])
    if (not content or sha(content) != expected or runtime['flags']['served_template_sha256'] != expected
            or runtime['flags']['chat_template_file'] is not None):
        raise ValueError('embedded template differs from the registered served bytes')
    verify_pin(weights)
    write(D / 'chat-template.jinja', content)
    provenance = {'inventory_path': str(inventory), 'inventory_sha256': file_sha(inventory),
                  'registry_path': str(registry_path), 'registry_sha256': sha(registry_raw),
                  'compiled_priors_path': str(priors_path), 'compiled_priors_sha256': sha(priors_raw),
                  'registered_role': registered, 'observed_server_mode': mode,
                  'compiled_deployed_serving': deployed,
                  'template_source': {'gguf': weights['path'], 'key': 'tokenizer.chat_template'}}
    provenance_pin = write_json(D / 'profile-source.json', json.loads(json.dumps(provenance, default=str)))
    return weights, projector, pin(D / 'chat-template.jinja', expected), provenance_pin


def png(paint):
    pixels = bytearray(bytes((247, 247, 240)) * IMAGE_SIZE * IMAGE_SIZE)

    def rectangle(left, top, right, bottom, color):
        row = bytes(color) * (right - left)
        for y in range(top, bottom):
            pixels[(y * IMAGE_SIZE + left) * 3:(y * IMAGE_SIZE + right) * 3] = row

    def circle(x, y, radius, color):
        for dy in range(-radius, radius + 1):
            half_width = int((radius * radius - dy * dy) ** 0.5)
            rectangle(x - half_width, y + dy, x + half_width + 1, y + dy + 1, color)

    paint(rectangle, circle)
    step = IMAGE_SIZE * 3
    raster = b''.join(b'\0' + pixels[i:i + step] for i in range(0, len(pixels), step))

    def chunk(kind, content):
        return struct.pack('>I', len(content)) + kind + content + struct.pack('>I', zlib.crc32(kind + content))

    header = struct.pack('>IIBBBBB', IMAGE_SIZE, IMAGE_SIZE, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(raster, 9)) + chunk(b'IEND', b'')


def vision_items():
    red, blue, green = (218, 45, 37), (36, 82, 207), (30, 139, 76)

    def circles(_rectangle, circle):
        for x, y in [(212, 215), (680, 236), (450, 680)]:
            circle(x, y, 110, red)

    def positions(rectangle, _circle):
        rectangle(92, 330, 348, 586, blue)
        rectangle(542, 330, 798, 586, green)

    def taller(rectangle, _circle):
        rectangle(130, 300, 370, 720, blue)
        rectangle(522, 520, 762, 720, red)
        rectangle(90, 720, 804, 730, (38, 38, 38))

    def shape(rectangle, circle):
        rectangle(140, 190, 355, 706, green)
        circle(650, 448, 135, red)

    fixtures = [
        ('json', circles, 'Count the red circles. Return only a JSON object with the only key red_circles and its integer count.',
         {'red_circles': 3}),
        ('prose', positions, 'In one short sentence, describe where the blue square is relative to the green square.',
         'The blue square is to the left of the green square.'),
        ('reasoning', taller, 'Which colored bar is taller? Give the color and one reason using how high its top is.',
         'The blue bar is taller because its top is higher than the red bar’s top.'),
        ('code', shape, 'Is the red shape a circle or a rectangle? Return only a valid Python assignment to shape with the lowercase name in quotes.',
         "shape = 'circle'"),
    ]
    items = []
    for output_format, paint, question, reference in fixtures:
        name = f'{PROFILE}-{output_format}'
        raw = png(paint)
        write(D / 'images' / f'{name}.png', raw)
        url = 'data:image/png;base64,' + base64.b64encode(raw).decode('ascii')
        items.append({'id': name, 'format': output_format, 'reference': reference,
                      'image_sha256': sha(raw), 'prompt_shape': 'short',
                      'request_body': {'model': PROFILE, 'stream': False,
                                       'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': question},
                                                                                 {'type': 'image_url', 'image_url': {'url': url}}]}],
                                       'temperature': 0, 'seed': 35, 'max_tokens': 80, 'cache_prompt': False,
                                       'return_tokens': True, 'verbose': True}})
    return items


def main():
    previous = json.loads(archived_bytes(SOURCE / 'plan.json.original-bytes.json'))
    if previous['profile'] != 'architect-general-hip':
        raise ValueError('unexpected shared runtime source plan')
    smoke = previous['smoke_model']
    mismatch = previous['prior_frontdoor_json_mismatch']
    for witness, path_key, sha_key in ((smoke, 'receipt_snapshot', 'original_hash_receipt_sha256'),
                                       (mismatch, 'snapshot', 'receipt_sha256')):
        name = Path(witness[path_key]).name
        raw = archived_bytes(SOURCE / f'{name}.original-bytes.json')
        if sha(raw) != witness[sha_key]:
            raise ValueError(f'prior original bytes differ: {name}')
        write(D / name, raw)
        witness[path_key] = str(D / name)

    weights, projector, template, provenance_pin = profile()
    arms = {arm: vision_runtime(arm, previous['arms'][arm]) for arm in COMMITS}
    witness_path = D / 'model-hash-receipt.json'
    (D / 'requests').mkdir()
    (D / 'images').mkdir()
    items = vision_items()
    smoke_items = [{'id': 'native-smoke',
                    'request_body': {**previous['smoke_items'][0]['request_body'],
                                     'n_predict': 256, 'ignore_eos': True}}]
    request_files = {}
    for entry in [*items, *smoke_items]:
        path = f"requests/{entry['id']}.json"
        body = canonical(entry['request_body'])
        write(D / path, body)
        request_files[entry['id']] = {'path': path, 'sha256': sha(body)}

    recipe = {'device': 'ROCm0', 'gpu_id': 25466, 'render_minor': 128, 'kfd_topology_node': 4,
              'max_vram_bytes': 60 * 2**30, 'cpu_affinity': list(range(184, 192)),
              'offload': 'all', 'speculation': 'none', 'slots': 1, 'context_tokens': 4096,
              'kv_type_k': 'f16', 'kv_type_v': 'f16', 'kv_unified': False, 'batch': 1024, 'ubatch': 1024,
              'mmap': True, 'mmproj_path': projector['path'], 'image_min_tokens': IMAGE_MIN_TOKENS,
              'image_size': [IMAGE_SIZE, IMAGE_SIZE], 'startup_s': 330, 'request_s': 140,
              'endpoint': '/v1/chat/completions',
              'args': ['--alias', PROFILE, '--device', 'ROCm0', '-ngl', '99', '--fit', 'off',
                       '--split-mode', 'none', '--main-gpu', '0', '-ctk', 'f16', '-ctv', 'f16',
                       '-fa', 'on', '--no-warmup', '-np', '1', '-m', weights['path'],
                       '--mmproj', projector['path'], '--mmproj-offload', '--image-min-tokens', str(IMAGE_MIN_TOKENS),
                       '-c', '4096', '-b', '1024', '-ub', '1024', '--cache-ram', '0', '--mmap',
                       '--no-kv-unified', '--no-context-shift', '--jinja',
                       '--chat-template-file', template['path'], '--spec-type', 'none']}
    smoke_recipe = {key: recipe[key] for key in ('device', 'gpu_id', 'render_minor', 'kfd_topology_node')}
    smoke_recipe.update({
        'max_vram_bytes': 4 * 2**30, 'offloaded_layers': 29, 'context_tokens': 512,
        'endpoint': '/completion', 'startup_s': 45, 'request_s': 30,
        'args': ['--device', 'ROCm0', '-ngl', '99', '--fit', 'off', '--split-mode', 'none',
                 '--main-gpu', '0', '-ctk', 'f16', '-ctv', 'f16', '-fa', 'on', '--no-warmup',
                 '-np', '1', '-m', smoke['path'], '-c', '512', '--cache-ram', '0',
                 '--no-kv-unified', '--no-context-shift', '--spec-type', 'none'],
    })
    plan = {'schema': 'epyc.native_quality_worker_vision_hip_plan.v1', 'profile': PROFILE,
            'scope': 'Isolated one-MI210 image+text paired capture with pinned HIP projector and no speculation.',
            'shared_capture_sha256': file_sha(D / 'capture_base.py'),
            'profile_provenance_sha256': provenance_pin,
            'model': weights, 'mmproj': projector, 'template': template, 'arms': arms,
            'model_hash_witness': {'snapshot': str(witness_path), 'sha256': file_sha(witness_path)},
            'smoke_model': smoke,
            'prior_frontdoor_json_mismatch': mismatch,
            'recipes': {'smoke_control': smoke_recipe, 'hip_slice': recipe},
            'smoke_items': smoke_items, 'items': items, 'request_files': request_files,
            'question_pool_sha256': sha(canonical(items))}
    verify_vision_inputs(plan)
    write_json(D / 'plan.json', plan)


if __name__ == '__main__':
    main()
