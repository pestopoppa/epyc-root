#!/usr/bin/env python3
"""DF2-18 Step 2/3 driver: rowexact (batch mode) on the champion HIP build, per width x prefix, with A/A repeats.
Run ONLY inside gpu_hold.sh. One child at a time; residency sampled DURING each run."""
import json, os, sys, time, hashlib
from pathlib import Path
sys.path.insert(0, '/mnt/raid0/llm/tmp/gpu-queue-20261020/lib')
import gpuq

ROOT = Path('/mnt/raid0/llm/tmp/gpu-queue-20261020/df2-18')
B = '/mnt/raid0/llm/kernels/builds/gpu-20261006-4348de400/bin'
BIN = str(ROOT / 'bin/rowexact_margin')
MODEL = '/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'
WIDTHS = [2, 3, 4, 5, 8, 9]
PREFIXES = ['code', 'prose']
PREFIX_TOKENS = 24

def run(label, width, prefix, nocap, extra_env=None, out_sub='runs', extra_args=None):
    d = ROOT / out_sub
    log = d / f'{label}.log'
    if log.exists() and (d / f'{label}.meta.json').exists():
        return json.loads((d / f'{label}.meta.json').read_text())
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = f'{B}:/opt/rocm/lib'
    env.pop('HSA_OVERRIDE_GFX_VERSION', None)
    for k in ('GGML_CUDA_DISABLE_FUSION', 'GGML_CUDA_DISABLE_GRAPHS', 'GGML_CUDA_FA_SEQ_ROWS', 'LLAMA_SPEC_EXACT', 'GGML_FA_SPLIT_KV'):
        env.pop(k, None)
    env.update(extra_env or {})
    argv = ['taskset', '-c', '184-191', BIN, '-m', MODEL, '-t', '8', '-n', str(width), '--prefix', str(PREFIX_TOKENS),
            '--text', str(ROOT / f'prefixes/{prefix}.txt'), '--show', '1000000', '--nocap', str(nocap)] + (extra_args or [])
    t = time.time()
    rc, proof, pid = gpuq.run_logged(argv, env, log, timeout=3000)
    meta = {'label': label, 'width': width, 'prefix': prefix, 'nocap': nocap, 'extra_env': extra_env or {}, 'extra_args': extra_args or [], 'rc': rc, 'pid': pid,
            'wall_s': round(time.time() - t, 1), 'residency': proof, 'argv': argv,
            'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()}
    (d / f'{label}.meta.json').write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: meta[k] for k in ('label', 'rc', 'wall_s')}) + ' vram_peak=' + str(proof.get('vram_peak')), flush=True)
    return meta

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'step2'
    if mode == 'step2':
        for prefix in PREFIXES:
            for w in WIDTHS:
                for nocap in (0, 1):
                    for rep in ('a', 'b'):          # b = the A/A repeat
                        run(f'{prefix}_w{w}_{"nocap" if nocap else "cap"}_{rep}', w, prefix, nocap)
    elif mode == 'step3':
        # knob-off re-runs; spec: json list of {label,width,prefix,env}
        spec = json.loads(Path(sys.argv[2]).read_text())
        for s in spec:
            run(s['label'], s['width'], s['prefix'], s.get('nocap', 0), s['env'], out_sub='step3', extra_args=s.get('args'))
