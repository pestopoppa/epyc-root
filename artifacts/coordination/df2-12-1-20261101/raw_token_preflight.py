#!/usr/bin/env python3
"""Vocab-only raw-prompt token counts; rendered chat prompts still need exact server preflight."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess


ROOT = pathlib.Path(__file__).resolve().parent
BIN = pathlib.Path('/mnt/raid0/llm/kernels/production/cpu/llama-tokenize')
LIB = BIN.parent
MODELS = {
    'frontdoor_mtp': pathlib.Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'),
    'architect_dflash': pathlib.Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'),
}


def main():
    manifest_path = ROOT / 'PROMPTS.json'
    manifest = json.loads(manifest_path.read_text())
    all_counts = {}
    for shape, model in MODELS.items():
        counts = {}
        for key, prompt in manifest['prompts'].items():
            proc = subprocess.run([str(BIN), '-m', str(model), '-p', prompt, '--show-count'],
                                  env={**os.environ, 'LD_LIBRARY_PATH': str(LIB)},
                                  text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=120, check=True)
            matches = re.findall(r'Total number of tokens: (\d+)', proc.stdout)
            if len(matches) != 1:
                raise RuntimeError(f'token count absent for {shape}/{key}')
            counts[key] = int(matches[0])
        all_counts[shape] = counts
    result = {'schema': 'epyc.df2_12_1.raw_vocab_preflight.v1',
              'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              'tokenizer_binary_sha256': hashlib.sha256(BIN.read_bytes()).hexdigest(),
              'mode': 'vocab-only raw prompts; no rendered chat template or model inference',
              'counts': all_counts, 'equal_raw_salted': {shape: len(set(counts.values())) == 1
                                                     for shape, counts in all_counts.items()}}
    (ROOT / 'RAW-TOKEN-PREFLIGHT.json').write_text(json.dumps(result, indent=2) + '\n')
    if not all(result['equal_raw_salted'].values()):
        raise SystemExit('raw salted prompts differ in token length; revise frozen manifest before target exposure')
    print(json.dumps(result['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
