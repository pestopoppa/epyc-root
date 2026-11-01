#!/usr/bin/env python3
"""Produce CPU-only metadata for the exact pinned YARN A1/500k first request."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
TEMPLATE = Path('/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja')
TOKENIZER_MODEL = Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
TOKENIZER_BIN = Path('/mnt/raid0/llm/kernels/builds/gpu-20261004-9a3f1392a/bin/llama-tokenize')
HISTORIC = Path('/mnt/raid0/llm/tmp/yarn-e1-20261004/results/A1/20261004T184217Z/needle_500k.jsonl')
OUT = HERE / 'qualification'


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    import jinja2

    spec = importlib.util.spec_from_file_location('yarn_needle', HERE / 'yarn_needle.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    inputs = module.load_inputs()
    if inputs['bad']:
        raise SystemExit(f'input manifest mismatch: {inputs["bad"]}')
    items = [x for x in inputs['needles'] if x.get('stage') == '500k']
    historical_rows = {json.loads(line)['id']: json.loads(line) for line in HISTORIC.read_text().splitlines()}
    n15_historical = historical_rows['N15']
    exact_source_join = {
        'runner_sha256_matches_task_source': sha(HERE / 'yarn_needle.py') == sha(Path('/mnt/raid0/llm/tmp/codex-ni-next-gpu-prep-20261031/yarn_needle.py')),
        'input_manifest_sha256_matches_task_source': sha(HERE / 'inputs/manifest.json') == sha(Path('/mnt/raid0/llm/tmp/codex-ni-next-gpu-prep-20261031/inputs/manifest.json')),
        'template_sha256': sha(TEMPLATE),
        'historical_prompt_sha256': n15_historical['prompt_sha256'],
        'historical_image': 'v10 gpu-20260921-ffc1bac82; historical result is not current-image calibration',
        'current_recipe_binary': '/mnt/raid0/llm/kernels/builds/gpu-20261004-9a3f1392a/bin/llama-server',
    }
    template = jinja2.Environment(undefined=jinja2.StrictUndefined, autoescape=False).from_string(TEMPLATE.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               LD_LIBRARY_PATH=f'{TOKENIZER_BIN.parent}:/opt/rocm/lib:/usr/lib/llvm-20/lib')
    planned = []
    for item in items:
        messages = module.chain_messages(inputs['segments'], module.stage_chain('500k'), item['question'])
        messages_sha = hashlib.sha256(json.dumps(messages).encode()).hexdigest()
        historic = historical_rows.get(item['needle'])
        if not historic or messages_sha != historic.get('prompt_sha256'):
            raise SystemExit(f'exact request/history join failed for {item["needle"]}')
        rendered = template.render(messages=messages, tools=None, add_generation_prompt=True,
                                   enable_thinking=False, reasoning_effort='none',
                                   tool_call_format='xml', max_tool_arg_chars=0,
                                   max_tool_response_chars=0, bos_token='', eos_token='',
                                   unk_token='', pad_token='')
        prompt_path = OUT / f'a1-500k-{item["needle"].lower()}.rendered.txt'
        prompt_path.write_text(rendered, encoding='utf-8')
        cp = subprocess.run([str(TOKENIZER_BIN), '-m', str(TOKENIZER_MODEL), '-f', str(prompt_path), '--show-count'],
                            check=True, capture_output=True, env=env, timeout=900)
        token_lines = re.findall(r'Total number of tokens:\s*(\d+)',
                                 cp.stdout.decode('ascii', errors='ignore'))
        if not token_lines:
            raise SystemExit(f'llama-tokenize count absent for {item["needle"]}: stderr={cp.stderr[-500:]!r}')
        planned.append({
            'stage': '500k', 'arm': 'A1', 'needle': item['needle'],
            'messages_sha256': messages_sha, 'rendered_sha256': sha(prompt_path),
            'rendered_bytes': len(rendered.encode()), 'token_count': int(token_lines[-1]),
            'historical_prompt_tokens': historic['timings']['prompt_n'] + historic['timings']['cache_n'],
            'request_bytes_match_historical': True,
        })
    max_prompt = max(planned, key=lambda x: (x['token_count'], x['needle']))
    prompt = dict(max_prompt, tokenizer_binary_sha256=sha(TOKENIZER_BIN),
                  model_path=str(TOKENIZER_MODEL))
    historical = historical_rows[prompt['needle']]
    exact_source_join['request_bytes_match_historical'] = all(x['request_bytes_match_historical'] for x in planned)
    exact_source_join['max_request_messages_sha256'] = prompt['messages_sha256']
    exact_source_join['max_request_needle'] = prompt['needle']
    exact_source_join['historical_prompt_tokens'] = historical['timings']['prompt_n'] + historical['timings']['cache_n']
    result = {
        'schema': 'epyc.yarn-e1-request-metadata.v1',
        'kind': 'metadata-only-tokenizer-count',
        'no_inference': True,
        'qualification_claim': False,
        'planned_500k_prompts': planned,
        'prompt': prompt,
        'identity_audit': exact_source_join,
        'historical_image': 'v10 gpu-20260921-ffc1bac82; historical timings are not current-image calibration',
        'historical_count_is_not_assumed': True,
    }
    (OUT / 'REQUEST-METADATA.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'max_prompt': {k: result['prompt'][k] for k in ('needle', 'token_count', 'rendered_sha256')},
                      'all_planned': [{'needle': x['needle'], 'token_count': x['token_count']} for x in planned],
                      'all_messages_match_historical': all(x['request_bytes_match_historical'] for x in planned)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
