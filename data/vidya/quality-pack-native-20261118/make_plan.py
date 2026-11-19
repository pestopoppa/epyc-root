#!/usr/bin/env python3
"""Prepare a typed, truthful slice from existing kernel/model provenance."""
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
STORE = Path('/mnt/raid0/llm/kernels')
MODELS = Path('/mnt/raid0/llm/models')
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


def frontdoor_item(name, prompt, output_format, expected, *, limit=96, finish='stop', shape='short'):
    validator = 'json-object-subset.v1' if output_format == 'json' else 'contains-text.v1'
    return {'id': name, 'fixture': None, 'dflash_pair': None, 'prompt_shape': shape,
            'output_format': output_format, 'expected_finish': finish, 'validator': {'id': validator, 'expected': expected},
            'request_body': {'model': 'frontdoor-native-capture', 'messages': [{'role': 'user', 'content': prompt}],
                             'max_tokens': limit, 'seed': 35, 'temperature': 0, 'cache_prompt': False,
                             'stream': False, 'return_tokens': True, 'verbose': True,
                             'chat_template_kwargs': {'enable_thinking': False}}}


def main():
    small = MODELS / 'Qwen_Qwen3-0.6B-Q8_0.gguf'
    small_sha = 'c159d1518f16bc42533d9a09f034eb598b670341adc2b08b9a9751614aea71eb'
    model = MODELS / 'Qwen3.6-35B-A3B-MTP-Q8_0.gguf'
    template_sha = '1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551'
    template = MODELS / f'chat-templates/sha256/{template_sha}.jinja'
    prepared = json.loads(PREP.read_text())
    production = runtime('cpu-20260921-ffc1bac82', 'SHA256SUMS',
                         'ffc1bac82eeca6f9099e1ccd9ba49703c460a115', 'a7c564ffbac0a86ce648ef6f11c1748c81a6560d')
    candidate = runtime('cpu-20261117-bda43aa17-c13', 'SHA256SUMS.c13',
                        'bda43aa17c11b671e0e203e7eb7bf4f1303bc273', 'e6dc8715fa3374406b38de48571e8700bded094f')
    candidate_build = Path(candidate['binary']).parent.parent / 'BUILD-IDENTITY.json'
    build = json.loads(candidate_build.read_text())
    if (build['source_sha'], build['source_tree']) != (candidate['kernel_commit'], candidate['kernel_tree']):
        raise ValueError('C13 build manifest source identity differs')
    candidate['build_identity_sha256'] = sha(candidate_build)
    common = ['--device', 'none', '-ngl', '0', '-ctk', 'q8_0', '-ctv', 'q8_0', '-fa', 'on', '--no-warmup', '-np', '1']
    model_pin = file_pin(model, prepared['model_sha256'])
    if model_pin['stat'] != prepared['model_stat'] or sha(template) != template_sha:
        raise ValueError('prepared model or served template identity changed')
    plan = {
        'schema': 'epyc.native_quality_frontdoor_plan.v1', 'scope': 'isolated bounded frontdoor-model CPU/MTP slice',
        'arms': {'production': production, 'candidate': candidate},
        'frontdoor_model': {**model_pin, 'original_hash_receipt': str(PREP), 'original_hash_receipt_sha256': sha(PREP)},
        'frontdoor_template': file_pin(template, template_sha), 'smoke_model': file_pin(small, small_sha),
        'recipes': {
            'smoke_control': {'endpoint': '/completion', 'startup_s': 45, 'request_s': 30,
                              'args': [*common, '-m', str(small), '-c', '512', '--spec-type', 'none']},
            'frontdoor_slice': {'endpoint': '/v1/chat/completions', 'startup_s': 240, 'request_s': 75,
                                'args': [*common, '-m', str(model), '-c', '4096', '-ub', '512', '--jinja',
                                         '--chat-template-file', str(template), '--reasoning', 'off',
                                         '--spec-type', 'draft-mtp', '--spec-draft-n-max', '4']},
        },
        'smoke_items': [{'id': 'native-smoke', 'request_body': {
            'prompt': 'The first four positive integers are 1, 2, 3,', 'n_predict': 8,
            'seed': 35, 'temperature': 0, 'cache_prompt': False, 'stream': False, 'return_tokens': True}}],
        'items': [
            frontdoor_item('json', 'Reply with only a JSON object containing the key "city" with value "Oslo".', 'json', {'city': 'Oslo'}),
            frontdoor_item('code', 'Write a Python function named parity(n) returning n % 2. Give only Python code.', 'code', 'def parity('),
            frontdoor_item('reasoning', 'What is 13 * 7 + 5? Give the calculation and final result in one sentence.', 'reasoning', '96'),
            frontdoor_item('long-prose', ('The inventory sheet is checked every Monday. The records use stable identifiers. '
                                         'Items are stored on pallets with one record per package. ' * 20)
                           + 'The actual audit location is Helsinki. Start the reply with Helsinki, then write a long inventory story.',
                           'prose', 'Helsinki', limit=16, finish='length', shape='long'),
        ],
        'broad_pack_status': 'incomplete',
    }
    with (D / 'plan.json').open('x') as out:
        json.dump(plan, out, indent=2, sort_keys=True)
        out.write('\n')


if __name__ == '__main__':
    main()
