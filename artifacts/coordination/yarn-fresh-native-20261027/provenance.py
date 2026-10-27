#!/usr/bin/env python3
"""Write or verify full-content serving identity before each window's first load."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch')
MODEL = Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
TEMPLATE = Path('/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja')
BUILD = Path('/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin')
RESEARCH = Path('/mnt/raid0/llm/worktrees/yarn-native-gate-runner-20261022')

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()

def build(out):
    if Path('/mnt/raid0/llm/kernels/production/gpu').resolve() != BUILD:
        raise ValueError('store build mismatch')
    head = subprocess.check_output(['git', '-C', str(RESEARCH), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(RESEARCH), 'status', '--porcelain'], text=True)
    if head != '7e7d5ef7f28f0c0ec45c16b7a90a51750006671f' or dirty:
        raise ValueError('research source differs or dirty')
    dsos = sorted({p.resolve() for p in BUILD.glob('*.so*')})
    if not dsos or not all(p.parent == BUILD for p in dsos): raise ValueError('invalid DSO set')
    inherited = {k: v for k, v in os.environ.items() if k.startswith(('GGML_', 'LLAMA_', 'HSA_', 'ROCR_', 'HIP_', 'OMP_'))}
    for k in ('LLAMA_SERVER_SLOTS_DEBUG', 'GGML_CUDA_GDN_STATE_BF16', 'GGML_CUDA_FA_MASK_SKIP', 'HSA_OVERRIDE_GFX_VERSION'):
        inherited.pop(k, None)
    inherited.update({'GGML_IQK': '1', 'HIP_PATH': '/opt/rocm', 'ROCM_PATH': '/opt/rocm',
                      'OMP_PROC_BIND': 'spread', 'OMP_PLACES': 'cores', 'OMP_WAIT_POLICY': 'active',
                      'OMP_DYNAMIC': 'false', 'LD_LIBRARY_PATH': str(BUILD)+':/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib',
                      'FILLER_CPUS': os.environ.get('FILLER_CPUS', '')})
    return {'schema': 'yarn-fresh-serving-identity-v1', 'model': sha(MODEL),
            'binary': sha(BUILD/'llama-server'), 'dsos': {str(p): sha(p) for p in dsos},
            'template': sha(TEMPLATE), 'source_commit': head,
            'source_manifest': sha(ROOT/'fresh/SOURCES.sha256'),
            'recipe_A0': sha(out/'A0.recipe'), 'recipe_A1': sha(out/'A1.recipe'),
            'frozen_plan': sha(out/'plan/plan.json'), 'frozen_items': sha(out/'plan/items.jsonl'),
            'server_environment': inherited}

def main():
    out = Path(sys.argv[1]); record = out/'provenance.json'
    current = build(out)
    if record.exists():
        if json.loads(record.read_text()) != current: raise SystemExit('REFUSED: serving provenance changed')
    else:
        tmp = out/'provenance.json.tmp'
        with tmp.open('x') as f:
            json.dump(current, f, sort_keys=True, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, record)
    print('serving provenance complete and matched', flush=True)

if __name__ == '__main__': main()
