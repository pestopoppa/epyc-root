#!/usr/bin/env python3
"""Build a reviewable DF2 v14 production manifest only from native sealed inputs."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import sys

from df2_launcher import ENGINE, ENGINE_SHA, FLAGS, ROLES, ROOT, need, pinned, sha

PROMPT_SHA = 'de3096605c354c6346418267ad09efc5cbf6eb7599816301a940e3b93cb8e0e1'
RECIPES = {
    'cpu': ('/mnt/raid0/llm/tmp/codex-ni-rte-frontdoor-quarter-20261031/RECIPE.json',
            '6fc8303cfa58f9e1443cf2af44a03de13ccc244232d0ac8f64b8d2d08631dd05'),
    'gpu': ('/mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json',
            '612323d93632856a923b2d163b7486b9e48e87645f41b16e0602260667c33149'),
}
MODELS = {
    'cpu': [('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf',
             'c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131')],
    'gpu': [('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf',
             'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348'),
            ('/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf',
             '7f1c9a31a6ed40044c69f6508b50fd63b87abd8e1fb7fe4290303df549153751')],
}
TEMPLATE = ('/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja',
            '1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551')


def ceiling_minute(seconds):
    return int(math.ceil(seconds / 60) * 60)


def phase_budget(rate_tok_s, observed_fixed_s, bound_fixed_s, reserve_s):
    need(type(rate_tok_s) in (int,float) and math.isfinite(rate_tok_s) and rate_tok_s > 0,
         'production token rate absent')
    need(type(observed_fixed_s) in (int,float) and math.isfinite(observed_fixed_s) and observed_fixed_s >= 0,
         'observed server load/preflight/drain overhead absent')
    need(type(bound_fixed_s) in (int,float) and math.isfinite(bound_fixed_s) and
         bound_fixed_s >= observed_fixed_s, 'declared phase overhead bound below observation')
    need(type(reserve_s) in (int,float) and math.isfinite(reserve_s) and reserve_s >= 300,
         'at least 300 seconds explicit reserve required')
    needed = 53 * bound_fixed_s + 152 * 96 / rate_tok_s
    minimum = ceiling_minute(needed)
    window = max(minimum + 300, ceiling_minute(needed + reserve_s))
    return needed, minimum, window


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--role', choices=tuple(ROLES), required=True)
    ap.add_argument('--native-token-proof', type=pathlib.Path, required=True)
    ap.add_argument('--rate-evidence', type=pathlib.Path, required=True)
    ap.add_argument('--owner-calibration-receipt', type=pathlib.Path, required=True)
    ap.add_argument('--phase-overhead-bound-s', type=float, required=True)
    ap.add_argument('--reserve-s', type=float, required=True)
    ap.add_argument('--output-reserve-gib', type=float, required=True)
    args = ap.parse_args()
    role, spec = args.role, ROLES[args.role]
    out = ROOT / 'finalization-ready-draft' / role
    manifest_path = out / 'FINAL-MANIFEST.json'
    source_manifest = out / 'SOURCE-MANIFEST.txt'
    need(out.is_dir() and not manifest_path.exists() and not source_manifest.exists(),
         'fresh staged launcher directory required; refuse overwrite')
    need(sha(ROOT / 'PROMPTS.json') == PROMPT_SHA, 'frozen 304-request manifest drift')
    need(ENGINE.is_file() and sha(ENGINE) == ENGINE_SHA, 'canonical installed v14 engine absent/changed')
    allow = FLAGS / 'engine-allowlist.json'
    need(allow.is_file() and json.loads(allow.read_text()).get('engine') ==
         {'path':str(ENGINE),'sha256':ENGINE_SHA}, 'canonical engine allowlist absent/changed')
    shape = spec['shape']
    recipe = pathlib.Path(RECIPES[role][0])
    need(sha(recipe) == RECIPES[role][1], 'role production recipe drift')
    image = ROOT / 'corrected-proof' / shape / 'IMAGE-PREFLIGHT.json'
    rollback = ROOT / 'corrected-proof' / shape / 'ROLLBACK-TEST.json'
    image_data, rollback_data = json.loads(image.read_text()), json.loads(rollback.read_text())
    need(image_data.get('pass') is True and rollback_data.get('pass') is True and
         rollback_data.get('identity_sha256') == sha(image), 'same-image corrected native gate absent')
    token_path = args.native_token_proof.resolve(strict=True)
    token = json.loads(token_path.read_text())
    metadata = ROOT / 'metadata' / shape / 'RESULT.json'
    need(token.get('endpoint_observed') is True and token.get('metadata_match') is True and
         token.get('salt_equal_length') is True and token.get('role') == shape and
         token.get('manifest_sha256') == PROMPT_SHA and
         token.get('image_proof_sha256') == sha(image) and
         token.get('production_recipe_sha256') == sha(recipe) and
         token.get('metadata_result_sha256') == sha(metadata) and
         token.get('max_count') == 274 and
         set(token.get('counts', {})) == {'salt-A','salt-B','salt-C','salt-D','salt-E',
              'reuse_a','reuse_b','low_entropy-0','low_entropy-1','planted-0','planted-1'},
         'accepted-image native token max/equal salt/source proof absent')
    rate_path = args.rate_evidence.resolve(strict=True)
    rate = json.loads(rate_path.read_text())
    need(rate.get('scope') == 'calibrated-production' and rate.get('shape') == shape and
         rate.get('production_threads') == spec['threads'] and
         rate.get('production_recipe_sha256') == sha(recipe) and
         rate.get('prompt_manifest_sha256') == PROMPT_SHA and
         rate.get('native_token_preflight_sha256') == sha(token_path) and
         rate.get('prompt_tokens') == token['max_count'] and
         rate.get('n_ctx_total') == spec['n_ctx'] and rate.get('n_ctx_per_slot') == spec['per_slot'] and
         rate.get('np') == 4 and rate.get('kv_cache_mode') == spec['kv'] and
         rate.get('server_phase_timing_sha256') == sha(rate_path.parent / 'SERVER-PHASE-TIMING.json') and
         type(rate.get('phase_fixed_overhead_s')) in (int,float),
         'production rate/phase timing not bound to accepted role/image')
    owner_path = args.owner_calibration_receipt.resolve(strict=True)
    owner = json.loads(owner_path.read_text())
    need(owner.get('purpose') == 'calibrate' and owner.get('role') == role and
         owner.get('returncode') == 0 and owner.get('failure') is None and
         owner.get('owned_group_drained') is True and owner.get('result_sha256') == sha(rate_path),
         'owner resource/exit custody not bound to sealed rate')
    needed, minimum, window = phase_budget(rate['measured_tok_s'], rate['phase_fixed_overhead_s'],
                                            args.phase_overhead_bound_s, args.reserve_s)
    need(math.isfinite(args.output_reserve_gib) and args.output_reserve_gib >= 1,
         'at least 1 GiB explicit output reserve required')
    launcher = out / ('launcher-' + shape + '.sh')
    job = out / ('job-' + shape + '.sh')
    need(launcher.is_file() and job.is_file() and sha(ROOT / 'df2_launcher.py') and
         sha(ROOT / 'complete_df2.py'), 'fixed launcher/job/source absent')
    files = [ROOT / name for name in ('PROMPTS.json','run_role.py','complete_df2.py','df2_launcher.py',
             'df2_parity.py','native_trace.py','qual_fixture.py','calibrate_rate.py',
             'native_token_preflight.py','native_first_capture.py','recipe_snapshot.py',
             'image_preflight.py','metadata_prompt_count.cpp')]
    files += [launcher, job, ENGINE, recipe, image, rollback, token_path, rate_path,
              owner_path, metadata, ROOT / 'metadata' / shape / 'stdout.jsonl',
              token_path.parent / 'NATIVE-ROWS.jsonl',
              ROOT / 'frontend-instrument-corrected' / role / 'CORRECTED-BUILD-RECEIPT.json',
              ROOT / 'dirty-diagnostic/test-oracle-fix-minimal.cpp',
              ROOT / 'dirty-diagnostic/TEST-ORACLE-FIX.patch',
              rate_path.parent / 'SERVER-PHASE-TIMING.json',
              pathlib.Path(TEMPLATE[0])]
    files += [pathlib.Path(path) for path in image_data['artifacts']]
    files += [pathlib.Path(path) for path, _checksum in MODELS[role]]
    lines = []
    for path in sorted(set(files)):
        expected = dict(MODELS[role]).get(str(path), TEMPLATE[1] if str(path) == TEMPLATE[0] else None)
        actual = sha(path)
        need(expected is None or actual == expected, 'model/template source drift: ' + str(path))
        lines.append(actual + '  ' + str(path))
    source_manifest.write_text('\n'.join(lines) + '\n')
    (ROOT / 'qualification').mkdir(exist_ok=True)
    manifest = {'schema':'epyc.ready.v2','production':True,'workload_kind':'llm',
                'id':spec['id'],'owner':'codex-ni','regions':spec['regions'],
                'window_s':window,'min_window_s':minimum,'gib':120,
                'scratch_root':str(ROOT),'launcher':{'path':str(launcher),'sha256':sha(launcher)},
                'engine':{'path':str(ENGINE),'sha256':ENGINE_SHA},
                'job':{'path':str(job),'sha256':sha(job)},
                'qual_fixture':{'path':str(ROOT/'qual_fixture.py'),'sha256':sha(ROOT/'qual_fixture.py'),'items':2},
                'production_recipe':{'path':str(recipe),'sha256':sha(recipe)},
                'source_manifest':str(source_manifest),
                'source_manifest_sha256':sha(source_manifest),
                'request_manifest_sha256':PROMPT_SHA,
                'native_token_proof':{'path':str(token_path),'sha256':sha(token_path)},
                'requires_tools':['bash','python3','numactl','taskset'],
                'ports':[spec['port']],'exclusive_class':'df2-12.1-'+role,
                'shared_state':[],'n_ctx_required':spec['n_ctx'],
                'per_slot_n_ctx_required':spec['per_slot'],'n_parallel_required':4,
                'prompt_tokens_required':token['max_count'],'kv_cache_mode':spec['kv'],
                'items':152,'tokens_per_item':96,'est_output_GiB':args.output_reserve_gib,
                'job_floor_gib':150,'qual_timeout_s':600,
                'rate_basis':{'scope':'calibrated-production','production_threads':spec['threads'],
                              'rate_tok_s':rate['measured_tok_s'],
                              'evidence':{'path':str(rate_path),'sha256':sha(rate_path)}},
                'qualification':{'receipt':str(ROOT/'qualification'/('QUAL-'+spec['id']+'.json'))},
                'window_basis':{'phase_count':53,'items':152,
                     'phase_fixed_overhead_observed_s':rate['phase_fixed_overhead_s'],
                     'phase_overhead_bound_s':args.phase_overhead_bound_s,
                     'rate_evidence_sha256':sha(rate_path),
                     'reserve_s':args.reserve_s,'needed_s':needed,
                     'method':'53*explicit_phase_overhead_bound + 152*96/measured_tok_s; minute ceiling',
                     'owner_calibration_receipt_sha256':sha(owner_path)},
                'generated_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'staged_manifest':str(manifest_path),'sha256':sha(manifest_path),
                      'source_manifest_sha256':sha(source_manifest),'window_s':window,
                      'min_window_s':minimum,'native_prompt_tokens':token['max_count']}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError,OSError,KeyError,ValueError,TypeError) as exc:
        print(str(exc) if str(exc).startswith('UNREADY:') else 'UNREADY: '+str(exc),file=sys.stderr)
        raise SystemExit(70)
