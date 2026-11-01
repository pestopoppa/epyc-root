#!/usr/bin/env python3
"""Stage exact role argv from saved production launch/builder records; no launch."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

FRONTDOOR = pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-rte-frontdoor-quarter-20261031/RECIPE.json')
ARCHITECT = pathlib.Path('/mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json')


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def replace_pair(argv, flag, value):
    if argv.count(flag) != 1:
        raise RuntimeError(f'expected exactly one {flag}: {argv.count(flag)}')
    argv[argv.index(flag) + 1] = str(value)


def drop_pair(argv, flag):
    if flag in argv:
        i = argv.index(flag)
        del argv[i:i + 2]


def make(shape, source, binary, port, slot_path, np, spec):
    source_data = json.loads(source.read_text())
    argv = list(source_data['argv'])
    if shape == 'architect_dflash':
        pos = next(i for i, part in enumerate(argv) if part.endswith('/llama-server'))
        prefix, argv = argv[:pos], argv[pos:]
        if '-m' not in argv or '-md' not in argv:
            raise RuntimeError('saved :8083 recipe lacks target/draft')
        if argv[argv.index('-md') + 1] != '/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf':
            raise RuntimeError('unexpected :8083 drafter')
    else:
        prefix = []
        if argv[argv.index('-m') + 1] != '/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf':
            raise RuntimeError('unexpected :8070 model')
    original = list(argv)
    argv[0] = str(binary)
    replace_pair(argv, '--port', port)
    replace_pair(argv, '-np', np)
    replace_pair(argv, '--slot-save-path', slot_path)
    if shape == 'frontdoor_mtp':
        if np == 1:
            # np4 split-KV c262144 is 65536 tokens/slot; preserve that per-slot cap.
            replace_pair(argv, '-c', 65536)
        if '--kv-unified' not in argv and '--no-kv-unified' not in argv:
            argv.append('--no-kv-unified')
    elif '--kv-unified' not in argv:
        raise RuntimeError('saved GPU recipe did not explicitly pin unified KV')
    if spec == 'off':
        drop_pair(argv, '-md')
        drop_pair(argv, '-ngld')
        drop_pair(argv, '--spec-draft-n-max')
        drop_pair(argv, '--device-draft')
        replace_pair(argv, '--spec-type', 'none')
    else:
        want_type = 'draft-dflash' if shape == 'architect_dflash' else 'draft-mtp'
        want_max = '7' if shape == 'architect_dflash' else '4'
        if argv[argv.index('--spec-type') + 1] != want_type or argv[argv.index('--spec-draft-n-max') + 1] != want_max:
            raise RuntimeError('not the required speculative recipe')
    total_ctx = int(argv[argv.index('-c') + 1])
    unified = '--kv-unified' in argv
    return {'shape': shape, 'source_path': str(source), 'source_sha256': sha(source),
            'source_timestamp': source_data.get('launched_at'), 'source_commit': source_data.get('source_commit', source_data.get('stack_commit')),
            'source_port': 8070 if shape == 'frontdoor_mtp' else 8083,
            'source_original_argv': prefix + original,
            'scratch_argv': argv, 'scratch_port': port, 'np': np, 'spec': spec,
            'backend': 'cpu' if shape == 'frontdoor_mtp' else 'gpu',
            'source_affinity': source_data.get('affinity') if shape == 'frontdoor_mtp' else prefix,
            'source_ld_library_path': source_data.get('env', {}).get('LD_LIBRARY_PATH') if shape == 'frontdoor_mtp' else source_data.get('ld_library_path'),
            'scratch_affinity_required': 'whole physical host 0-95 via granted FILLER_CPUS; -t96 unchanged' if shape == 'frontdoor_mtp' else 'mi210_0 and physical 88-95 / SMT184-191; -t8 unchanged',
            'n_ctx_total': total_ctx,
            'n_ctx_per_slot': min(total_ctx, 262144) if unified else total_ctx // np,
            'n_ctx_per_slot_basis': ('Qwen3.8 target n_ctx_train=262144; server caps unified slot context at training context; verify /slots on exact image'
                                     if unified else 'split KV total context divided by np; verify /slots on exact image'),
            'source_live_current': False,
            'note': 'Saved source recipe plus explicit scratch changes; ws58 live-boundary identity required.'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shape', required=True, choices=['frontdoor_mtp', 'architect_dflash'])
    ap.add_argument('--binary', required=True)
    ap.add_argument('--port', type=int, required=True)
    ap.add_argument('--slot-path', required=True)
    ap.add_argument('--np', type=int, choices=[1, 4], required=True)
    ap.add_argument('--spec', choices=['on', 'off'], required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    if not 18000 <= args.port <= 19999:
        raise SystemExit('scratch port must be in 18000-19999')
    source = FRONTDOOR if args.shape == 'frontdoor_mtp' else ARCHITECT
    result = make(args.shape, source, args.binary, args.port, args.slot_path, args.np, args.spec)
    out = pathlib.Path(args.out)
    if out.exists():
        raise SystemExit('refuse to overwrite recipe snapshot')
    out.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
