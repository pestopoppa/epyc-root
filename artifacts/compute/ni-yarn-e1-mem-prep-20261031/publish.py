#!/usr/bin/env python3
"""Publish this diagnostic only after a same-launcher native smoke."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

D = Path(__file__).resolve().parent
RID = 'codex-ni-yarn-e1-mem-phase-r1-20261031'
READY = Path('/mnt/raid0/llm/tmp/compute-flags/ready')
LAUNCH = D / 'launch.sh'
JOB = D / 'run.py'
SMOKE = D / 'out/E1-A0-low/smoke-result.json'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def atomic(p, data):
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(data)
    os.replace(tmp, p)


def main():
    proof = json.loads(SMOKE.read_text())
    assert proof['qualification_only'] and proof['first_request_ok'] and proof['result_writer_ok']
    receipt = json.loads((D / 'SMOKE-RECEIPT.json').read_text())
    assert receipt['rc'] == 0 and receipt['cleanup_verified']
    assert receipt['launcher_sha256'] == digest(LAUNCH)
    when = dt.datetime.fromtimestamp(receipt['ended_at'], dt.timezone.utc)
    assert dt.datetime.now(dt.timezone.utc) - when < dt.timedelta(hours=24)
    log = READY / f'{RID}.smoke.log'
    assert log.is_file()
    launcher_sha = digest(LAUNCH)
    source_sha = digest(D / 'SOURCE.sha256')
    desc = ('Historical E1 memory attribution on unchanged 2026-10-04 E1 and W images: '
            'own-PID KFD VRAM and hipMalloc shim series joined to the original YaRN E1 smoke and '
            '128k/240k/400k/500k native needle stages for A0/A1. Higher VRAM is worse; identify '
            'the first phase with the +15 GiB excess and whether W removes it. Split stage groups '
            'are diagnostic and reset the server between groups; no quality or current champion claim.')
    row = (f'| {RID} | codex-ni | {LAUNCH} | mi210_0,184-191 | 5700 s | 64 | {D}/STOP | '
           f'BACKLOG | block-correctness | 6000 s | 5700 s | n | y | {D}/out/RESULT.json | '
           f'{desc} | n/a (historical memory attribution diagnostic) | gpu | '
           f'requested_window_s=6000; est_output_GiB=2; scratch_root={D}; claimed_cpus=184-191; '
           f'launcher_path={LAUNCH}; job_path={JOB}; launcher_sha256={launcher_sha}; '
           f'source_manifest={D}/SOURCE.sha256; source_manifest_sha256={source_sha}; '
           f'launcher_log_path={D}/ws58-launcher.out; log_consumer={D}/analyze_phase.py; '
           f'no_fold_siblings=1; keep_globs=*.py,*.sh,*.json,*.sha256,*.log,helper/*,out/*/*.json,out/*/native/**; '
           f'raw_globs=out/*/native/**,out/*/server.log,out/*/kfd.jsonl,out/*/hipmalloc.jsonl |\n')
    manifest = {
        'id': RID, 'owner': 'codex-ni', 'priority_rank': 80,
        'priority_rank_basis': 'S-tier covered; M YARN-E1-MEM historical attribution',
        'regions': 'mi210_0,184-191', 'min_window_s': 5700, 'window_s': 6000,
        'requested_window_s': 6000, 'gib': 64, 'class': 'diagnostic',
        'booking_class': 'block-correctness', 'enrollment': 'n/a: historical diagnostic',
        'hold': None, 'launcher': {'path': str(LAUNCH), 'sha256': launcher_sha},
        'job': {'path': str(JOB), 'sha256': digest(JOB)},
        'result_path': str(D / 'out/RESULT.json'), 'scratch_root': str(D),
        'keep': ['*.py','*.sh','*.json','*.sha256','*.log','helper/*','out/*/complete.json',
                 'out/*/runtime-proof.json','out/*/launch.json','out/*/native/**',
                 'out/*/kfd.jsonl','out/*/hipmalloc.jsonl','out/*/server.log','out/*/runner.log'],
        'est_output_GiB': 2, 'log_consumer': str(D / 'analyze_phase.py'),
        'launcher_log_path': str(D / 'ws58-launcher.out'),
        'source_manifest': str(D / 'SOURCE.sha256'), 'source_manifest_sha256': source_sha,
        'decision_rule': desc, 'min_effect': 'n/a (historical memory attribution diagnostic)',
        'gpu_quiet': 'exclusive', 'no_fold_siblings': True,
        'smoke': {'ran_at': when.isoformat(), 'regions': '184-185; exclusive GPU-only R7',
                  'model': 'canonical Qwen3.8-27B-Q8_0, 64MiB edges+size pinned',
                  'first_request_ok': True, 'result_writer_ok': True, 'exit_ok': True,
                  'cleanup_verified': True, 'wall_s': receipt['wall_s'], 'log': str(log),
                  'scope': 'native load, response, writer and cleanup only; no E1 inference measurement'},
        'feasibility': {'original_E1_A0_estimate_min': 35.2, 'original_E1_A1_estimate_min': 85.1,
                        'historical_A1_stage_min': {'128k': 5.5, '240k': 10.6, '400k': 25.5, '500k': 22.1},
                        'split_into': 'low/high per-image groups; high reloads 400k prefix so allow 95min',
                        'min_window_s': 5700, 'window_s': 6000, 'smoke_wall_s': receipt['wall_s']}}
    atomic(READY / f'{RID}.row.md', row)
    atomic(READY / f'{RID}.json', json.dumps(manifest, indent=2) + '\n')
    atomic(D / 'READY-PUBLISHED', when.isoformat() + '\n')


if __name__ == '__main__':
    main()
