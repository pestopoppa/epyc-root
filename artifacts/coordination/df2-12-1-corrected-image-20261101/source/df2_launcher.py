#!/usr/bin/env python3
"""Fail-closed DF2 v14 launcher binder; keeper owns nonce and grant."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
FLAGS = pathlib.Path('/mnt/raid0/llm/tmp/compute-flags')
ENGINE = FLAGS / 'bin/qual-v1/filler_run14.sh'
ENGINE_SHA = '6fe168333738d15e5988d5af42e2b4c348194d722bac11c32368183ae89cd3ef'
ROLES = {
    'cpu': {'shape':'frontdoor_mtp', 'id':'codex-ni-df2-12-1-frontdoor-v1',
            'port':19070,'regions':'0-95','n_ctx':262144,'per_slot':65536,
            'kv':'split','threads':96,'class':'cpu'},
    'gpu': {'shape':'architect_dflash', 'id':'codex-ni-df2-12-1-architect-v1',
            'port':19083,'regions':'mi210_0,184-191','n_ctx':393216,'per_slot':262144,
            'kv':'unified','threads':8,'class':'gpu'},
}


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def need(ok, reason):
    if not ok:
        raise RuntimeError('UNREADY: ' + reason)


def pinned(item, reason):
    need(isinstance(item, dict) and isinstance(item.get('path'), str) and
         re.fullmatch('[0-9a-f]{64}', str(item.get('sha256', ''))), reason + ' pin absent')
    path = pathlib.Path(item['path'])
    need(path.is_absolute() and path.is_file() and sha(path) == item['sha256'], reason + ' changed/missing')
    return path


def validate(manifest, role):
    spec = ROLES[role]
    m = json.loads(manifest.read_text())
    need(m.get('schema') == 'epyc.ready.v2' and m.get('production') is True and
         m.get('workload_kind') == 'llm', 'production manifest absent')
    need(m.get('id') == spec['id'] and m.get('owner') == 'codex-ni' and
         m.get('regions') == spec['regions'], 'row id/owner/regions changed')
    need(m.get('scratch_root') == str(ROOT) and m.get('ports') == [spec['port']],
         'scratch root/port changed')
    need(m.get('n_ctx_required') == spec['n_ctx'] and
         m.get('per_slot_n_ctx_required') == spec['per_slot'] and
         m.get('n_parallel_required') == 4 and m.get('kv_cache_mode') == spec['kv'],
         'production shape changed')
    need(m.get('items') == 152 and m.get('tokens_per_item') == 96 and
         m.get('request_manifest_sha256') == sha(ROOT / 'PROMPTS.json'),
         'frozen 152-request role manifest changed')
    need(type(m.get('prompt_tokens_required')) is int and m['prompt_tokens_required'] > 0,
         'native prompt count missing')
    need(type(m.get('window_s')) is int and type(m.get('min_window_s')) is int and
         m['window_s'] >= m['min_window_s'] + 300, 'window budget absent')
    need(m.get('job_floor_gib') == 150 and m.get('gib') == 120,
         'disk/RAM reservation changed')
    for key in ('engine','launcher','job','qual_fixture','production_recipe'):
        pinned(m.get(key), key)
    need(m['engine']['path'] == str(ENGINE) and m['engine']['sha256'] == ENGINE_SHA,
         'canonical engine path/SHA changed')
    need(m['launcher']['path'] == str(manifest.parent / ('launcher-' + spec['shape'] + '.sh')),
         'launcher path changed')
    need(m['job']['path'] == str(manifest.parent / ('job-' + spec['shape'] + '.sh')),
         'job path changed')
    need(m['qual_fixture']['path'] == str(ROOT / 'qual_fixture.py'), 'qual fixture changed')
    basis = m.get('rate_basis', {})
    need(basis.get('scope') == 'calibrated-production' and
         basis.get('production_threads') == spec['threads'] and
         type(basis.get('rate_tok_s')) in (int, float) and basis['rate_tok_s'] > 0,
         'matching production rate absent')
    rate_path = pinned(basis.get('evidence'), 'rate evidence')
    rate = json.loads(rate_path.read_text())
    need(rate.get('production_threads') == spec['threads'] and
         rate.get('measured_tok_s') == basis['rate_tok_s'] and
         rate.get('production_recipe_sha256') == m['production_recipe']['sha256'],
         'rate evidence not matching role recipe/threads')
    token_path = pinned(m.get('native_token_proof'), 'native token proof')
    token = json.loads(token_path.read_text())
    need(token.get('endpoint_observed') is True and token.get('metadata_match') is True and
         token.get('salt_equal_length') is True and
         token.get('max_count') == m['prompt_tokens_required'] and
         token.get('manifest_sha256') == m['request_manifest_sha256'] and
         token.get('production_recipe_sha256') == m['production_recipe']['sha256'] and
         token.get('image_proof_sha256') == sha(ROOT / 'corrected-proof' / spec['shape'] / 'IMAGE-PREFLIGHT.json') and
         rate.get('native_token_preflight_sha256') == m['native_token_proof']['sha256'],
         'native endpoint token proof not bound to calibration/image')
    window = m.get('window_basis', {})
    need(window.get('phase_count') == 53 and window.get('items') == 152 and
         window.get('rate_evidence_sha256') == basis['evidence']['sha256'] and
         window.get('phase_fixed_overhead_observed_s') == rate.get('phase_fixed_overhead_s') and
         type(window.get('phase_overhead_bound_s')) in (int,float) and
         window['phase_overhead_bound_s'] >= rate['phase_fixed_overhead_s'] and
         type(window.get('reserve_s')) in (int,float) and window['reserve_s'] >= 300 and
         window.get('needed_s') == 53*window['phase_overhead_bound_s'] + 152*96/basis['rate_tok_s'] and
         m['min_window_s'] >= window['needed_s'] and
         m['window_s'] >= window['needed_s'] + window['reserve_s'],
         '53-load full-role window forecast missing')
    source_manifest = pathlib.Path(m['source_manifest'])
    need(source_manifest.is_file() and source_manifest.is_absolute() and
         sha(source_manifest) == m.get('source_manifest_sha256'), 'source manifest absent/changed')
    for line in source_manifest.read_text().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (/mnt/raid0/llm/[^\n]+)', line)
        need(match is not None and pathlib.Path(match.group(2)).is_file() and
             sha(match.group(2)) == match.group(1), 'source manifest dependency changed')
    allow = FLAGS / 'engine-allowlist.json'
    need(allow.is_file() and json.loads(allow.read_text()).get('engine') == m['engine'],
         'canonical allowlist missing/mismatched')
    return m, spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--role', choices=tuple(ROLES), required=True)
    ap.add_argument('--manifest', type=pathlib.Path, required=True)
    args = ap.parse_args()
    manifest = args.manifest.resolve()
    try:
        m, spec = validate(manifest, args.role)
    except (OSError, KeyError, ValueError, TypeError, RuntimeError) as exc:
        print(str(exc) if str(exc).startswith('UNREADY:') else 'UNREADY: ' + str(exc), file=sys.stderr)
        return 70
    job = m['job']['path']
    complete = (f'/usr/bin/python3 {ROOT / "complete_df2.py"} --shape {spec["shape"]} '
                f'--out {ROOT / "science" / spec["shape"]} --manifest {ROOT / "PROMPTS.json"}')
    argv = [str(ENGINE), '--id', m['id'], '--class', spec['class'],
            '--cmd', 'bash ' + job, '--min-window', str(m['min_window_s']),
            '--stop', str(ROOT / 'stop' / (m['id'] + '.stop')),
            '--complete-cmd', complete, '--port', str(spec['port']), '--workdir', str(ROOT)]
    for tool in ('bash', 'python3', 'numactl', 'taskset'):
        argv += ['--requires-tool', tool]
    if args.role == 'gpu':
        argv += ['--gpu-quiet', 'exclusive', '--no-fold-siblings', '--gpu-threads', '184-191']
    os.execv(str(ENGINE), argv)


if __name__ == '__main__':
    raise SystemExit(main())
