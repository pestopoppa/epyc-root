#!/usr/bin/env python3
"""Bounded vocabulary-only template/token count; never a native target request."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
MODELS = {
    'frontdoor_mtp': ('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf',
                      'c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131'),
    'architect_dflash': ('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf',
                          'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348'),
}
TEMPLATE = pathlib.Path('/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja')
TEMPLATE_SHA = '1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551'
MANIFEST_SHA = 'de3096605c354c6346418267ad09efc5cbf6eb7599816301a940e3b93cb8e0e1'


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MODELS:
        raise SystemExit('usage: metadata_run.py frontdoor_mtp|architect_dflash')
    role = sys.argv[1]
    out = ROOT / 'metadata' / role
    out.mkdir(parents=True, exist_ok=False)
    model, model_sha = MODELS[role]
    tool = ROOT / 'metadata/bin/metadata_prompt_count'
    source = ROOT / 'metadata_prompt_count.cpp'
    inputs = ROOT / 'metadata/input.jsonl'
    argv = [str(tool), model, str(TEMPLATE)]
    intent = {'schema': 'epyc.df2_12_1.metadata_token_preflight.v1',
              'scope': 'FROZEN_V10_CPU_VOCAB_ONLY_MINJA_NO_TENSORS_NO_SERVER_REQUEST',
              'role': role, 'argv': argv, 'input_path': str(inputs),
              'planned_manifest_sha256': MANIFEST_SHA, 'model_sha256_expected': model_sha,
              'template_sha256_expected': TEMPLATE_SHA, 'tool_sha256': sha(tool),
              'source_sha256': sha(source), 'input_sha256': sha(inputs),
              'frozen_common_so': '/mnt/raid0/llm/kernels/production/cpu/libllama-common.so.0.0.10303',
              'utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    write(out / 'INTENT.json', intent)
    if (sha(ROOT / 'PROMPTS.json') != MANIFEST_SHA or sha(model) != model_sha or
        sha(TEMPLATE) != TEMPLATE_SHA):
        write(out / 'DISPOSITION.json', {'status': 'REFUSED_SOURCE_DRIFT'})
        return 2
    env = dict(os.environ, LD_LIBRARY_PATH='/mnt/raid0/llm/kernels/production/cpu')
    started = time.monotonic()
    with inputs.open('rb') as inp, (out / 'stdout.jsonl').open('wb') as stdout, (out / 'stderr.log').open('wb') as stderr:
        proc = subprocess.run(argv, stdin=inp, stdout=stdout, stderr=stderr,
                              env=env, timeout=300, check=False)
    if proc.returncode:
        write(out / 'DISPOSITION.json', {'status': 'UNKNOWN', 'returncode': proc.returncode,
              'stdout_sha256': sha(out / 'stdout.jsonl'), 'stderr_sha256': sha(out / 'stderr.log')})
        return 2
    rows = [json.loads(line) for line in (out / 'stdout.jsonl').read_text().splitlines()]
    ids = [row['id'] for row in rows]
    expected = [json.loads(line)['id'] for line in inputs.read_text().splitlines()]
    if ids != expected or any(len(row['tokens']) != row['count'] for row in rows):
        write(out / 'DISPOSITION.json', {'status': 'UNKNOWN', 'reason': 'missing/malformed rows'})
        return 2
    counts = {row['id']: row['count'] for row in rows}
    salt_counts = [counts[f'salt-{salt}'] for salt in 'ABCDE']
    result = {'schema': 'epyc.df2_12_1.metadata_token_preflight.v1',
              'scope': intent['scope'], 'role': role, 'model_sha256': model_sha,
              'template_sha256': TEMPLATE_SHA, 'manifest_sha256': MANIFEST_SHA,
              'tool_sha256': intent['tool_sha256'], 'source_sha256': intent['source_sha256'],
              'counts': counts, 'salt_equal_length': len(set(salt_counts)) == 1,
              'max_count_metadata_only': max(counts.values()),
              'max_ids': [key for key, value in counts.items() if value == max(counts.values())],
              'rendered_and_tokens_sha256': sha(out / 'stdout.jsonl'),
              'stderr_sha256': sha(out / 'stderr.log'),
              'wall_s': time.monotonic() - started,
              'native_same_image_api_crosscheck_required': True,
              'utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    write(out / 'RESULT.json', result)
    write(out / 'DISPOSITION.json', {'status': 'ACCEPTED_METADATA_PREFLIGHT_ONLY',
          'result_sha256': sha(out / 'RESULT.json')})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
