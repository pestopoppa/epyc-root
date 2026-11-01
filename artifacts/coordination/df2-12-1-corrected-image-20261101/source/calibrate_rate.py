#!/usr/bin/env python3
"""One source-bound production-thread rate sample under keeper pregrant authority."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import time

from qual_fixture import request, rendered_prompt, total_ctx_from_log, kv_mode_from_log, write
from native_first_capture import completion, disposition
from native_token_preflight import capture as capture_token_preflight
from df2_parity import canonical, sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shape', choices=('frontdoor_mtp', 'architect_dflash'), required=True)
    ap.add_argument('--url', required=True)
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--server-log', required=True)
    ap.add_argument('--production-recipe', required=True)
    ap.add_argument('--image-proof', required=True)
    ap.add_argument('--argv-record', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    cpus = '0-95' if args.shape == 'frontdoor_mtp' else '184-191'
    if os.environ.get('FILLER_CPUS') != cpus or not os.environ.get('FILLER_ID'):
        raise RuntimeError('source-bound calibration requires keeper-owned production-thread claim wiring')
    authority_path = os.environ.get('WS58_CALIBRATION_AUTHORITY')
    if not authority_path:
        raise RuntimeError('pregrant calibration authority path absent')
    manifest_path = pathlib.Path(args.manifest)
    rows, token_proof = capture_token_preflight(
        args.url, manifest_path, args.shape, pathlib.Path(args.out).parent / 'TOKEN-PREFLIGHT',
        args.image_proof, args.production_recipe)
    rendered = [row['rendered'] for row in rows]
    tokenized = [row['tokens'] for row in rows]
    longest = max(range(len(tokenized)), key=lambda index: len(tokenized[index]))
    props = request(args.url, '/props')
    slots = request(args.url, '/slots')
    total_ctx = total_ctx_from_log(args.server_log)
    context = 262144 if args.shape == 'frontdoor_mtp' else 393216
    per_slot = 65536 if args.shape == 'frontdoor_mtp' else 262144
    kv_mode = 'split' if args.shape == 'frontdoor_mtp' else 'unified'
    threads = 96 if args.shape == 'frontdoor_mtp' else 8
    spec_type = 'draft-mtp' if args.shape == 'frontdoor_mtp' else 'draft-dflash'
    n_max = 4 if args.shape == 'frontdoor_mtp' else 7
    if total_ctx != context or props.get('total_slots') != 4 or len(slots) != 4 or {s.get('n_ctx') for s in slots} != {per_slot}:
        raise RuntimeError('calibration server is not the saved production np4/context shape')
    if kv_mode_from_log(args.server_log) != kv_mode:
        raise RuntimeError('calibration native KV mode differs from saved production role')
    body = {'prompt': rendered[longest], 'temperature': 0.0, 'top_k': 1,
            'seed': 42, 'n_predict': 96, 'return_tokens': True,
            'stream': False, 'n_probs': 0, 'cache_prompt': False}
    source = {'issued_scope': 'PREGRANT_CALIBRATION_FIRST_REQUEST', 'shape': args.shape,
              'manifest_sha256': sha(manifest_path), 'image_proof_sha256': sha(args.image_proof),
              'argv_record_sha256': sha(args.argv_record),
              'production_recipe_sha256': sha(args.production_recipe),
              'authority_sha256': sha(authority_path), 'authority_path': str(pathlib.Path(authority_path).resolve()),
              'filler_id_local_pidfile_only': os.environ['FILLER_ID'], 'claimed_cpus': cpus,
              'actual_model_path': props.get('model_path'), 'n_ctx_total': total_ctx,
              'n_ctx_per_slot': per_slot, 'kv_cache_mode': kv_mode, 'total_slots': 4,
              'production_threads': threads, 'prompt_index': longest,
              'prompt_tokens': len(tokenized[longest]),
              'prompt_token_ids_sha256': hashlib.sha256(canonical(tokenized[longest])).hexdigest()}
    capture_dir = pathlib.Path(args.out).parent
    try:
        response, wall = completion(args.url, body, capture_dir, source, min_tokens=8)
        generated = response['tokens']
        rate = len(generated) / wall
    except BaseException as exc:
        disposition(capture_dir, 'FAILED_OR_EXPOSURE_UNKNOWN', error=repr(exc))
        raise
    result = {'schema': 'epyc.df2_12_1.calibrated_production_rate.v1',
              'scope': 'calibrated-production', 'shape': args.shape,
              'production_threads': threads, 'measured_tok_s': rate,
              'generated_tokens': len(generated), 'wall_s': wall,
              'prompt_tokens': len(tokenized[longest]), 'prompt_index': longest,
              'native_token_preflight_sha256': sha(pathlib.Path(args.out).parent / 'TOKEN-PREFLIGHT/PREFLIGHT.json'),
              'prompt_token_sha256': hashlib.sha256(json.dumps(tokenized[longest], separators=(',', ':')).encode()).hexdigest(),
              'prompt_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              'production_recipe_sha256': hashlib.sha256(pathlib.Path(args.production_recipe).read_bytes()).hexdigest(),
              'n_ctx_total': total_ctx, 'n_ctx_per_slot': per_slot, 'np': 4,
              'kv_cache_mode': kv_mode,
              'spec_type': spec_type, 'spec_draft_n_max': n_max, 'n_probs': 0,
              'filler_id': os.environ['FILLER_ID'], 'filler_cpus': os.environ['FILLER_CPUS'],
              'calibration_authority_sha256': hashlib.sha256(pathlib.Path(authority_path).read_bytes()).hexdigest(),
              'observed_cpus': sorted(os.sched_getaffinity(0)),
              'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'response_tokens_sha256': hashlib.sha256(json.dumps(generated, separators=(',', ':')).encode()).hexdigest()}
    expected_cpus = list(range(96)) if args.shape == 'frontdoor_mtp' else list(range(184, 192))
    try:
        if result['observed_cpus'] != expected_cpus:
            raise RuntimeError('calibration client affinity differs from role production threads')
        write(args.out, result)
        disposition(capture_dir, 'ACCEPTED', evidence={'rate_result_sha256': sha(args.out),
                    'production_threads': threads, 'measured_tok_s': rate})
    except BaseException as exc:
        disposition(capture_dir, 'FAILED_OR_EXPOSURE_UNKNOWN', error=repr(exc))
        raise
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Any failure after intent is written keeps the exposed request UNKNOWN,
        # including failures while assembling the source-bound rate record.
        if '--out' in os.sys.argv:
            out_index = os.sys.argv.index('--out') + 1
            if out_index < len(os.sys.argv):
                disposition(pathlib.Path(os.sys.argv[out_index]).parent,
                            'FAILED_OR_EXPOSURE_UNKNOWN', error=repr(exc))
        raise
