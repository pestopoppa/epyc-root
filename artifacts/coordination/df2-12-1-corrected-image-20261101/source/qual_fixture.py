#!/usr/bin/env python3
"""Canonical engine v14 fixture contract. Model-free mode tests mechanics only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import time
import urllib.request

from df2_parity import canonical, sha
from native_first_capture import completion, disposition
from native_token_preflight import capture as capture_token_preflight


def write(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    digest = write(temporary, obj)
    os.replace(temporary, path)
    return digest


def request(url, route, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url.rstrip('/') + route, data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as response:
        return json.loads(response.read())


def total_ctx_from_log(path):
    data = pathlib.Path(path).read_text(errors='replace')
    values = [int(x) for x in re.findall(r'llama_context: n_ctx\s+=\s+(\d+)', data)]
    if not values or len(set(values)) != 1:
        raise RuntimeError(f'actual target n_ctx absent or inconsistent in startup log: {values}')
    return values[0]


def kv_mode_from_log(path):
    text = pathlib.Path(path).read_text(errors='replace')
    values = re.findall(r"kv_unified = '(true|false)'", text)
    if not values or len(set(values)) != 1:
        raise RuntimeError(f'actual native KV mode missing/inconsistent: {values}')
    return 'unified' if values[0] == 'true' else 'split'


def rendered_prompt(url, prompt):
    data = request(url, '/apply-template', {
        'messages': [{'role': 'user', 'content': prompt}],
        'chat_template_kwargs': {'enable_thinking': False}})
    result = data.get('prompt')
    if not isinstance(result, str):
        raise RuntimeError('qualification template endpoint omitted prompt')
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['model-free', 'target'], required=True)
    ap.add_argument('--url')
    ap.add_argument('--n-ctx-required', type=int, default=32768)
    ap.add_argument('--n-ctx-per-slot-required', type=int)
    ap.add_argument('--server-log')
    ap.add_argument('--manifest')
    ap.add_argument('--production-recipe')
    ap.add_argument('--image-proof')
    ap.add_argument('--argv-record')
    args = ap.parse_args()
    phase = os.environ.get('FILLER_QUAL_PHASE', 'normal')
    common = {'id': os.environ.get('FILLER_ID', os.environ.get('WS58_ROW_ID', 'df2-12.1-fixture')),
              'nonce': os.environ.get('WS58_QUAL_NONCE', 'model-free-fixture'),
              'phase': phase, 'observed_cpus': sorted(os.sched_getaffinity(0))}
    results = pathlib.Path(os.environ['FILLER_RESULTS_DIR'])
    proof_path = pathlib.Path(os.environ['WS58_QUAL_PROOF'])
    results.mkdir(parents=True, exist_ok=True)
    if phase == 'cutoff' and args.mode == 'model-free':
        deadline = os.environ.get('FILLER_DEADLINE')
        reached = deadline is not None and time.time() >= float(deadline)
        if args.mode == 'target' and not reached:
            raise RuntimeError('production cutoff probe did not observe the forced deadline')
        write(results / 'PARTIAL.json', {'partial': True, 'phase': phase})
        write(proof_path, {**common, 'partial': True,
                           **({'deadline_reached': reached} if deadline is not None else {})})
        return 75
    if phase not in ('normal', 'cutoff'):
        raise RuntimeError(f'unknown qualification phase {phase}')
    started = time.monotonic()
    if args.mode == 'model-free':
        first = {'ok': True, 'n_ctx_total': args.n_ctx_required,
                 'n_ctx_per_slot': args.n_ctx_per_slot_required or args.n_ctx_required,
                 'prompt_tokens': 16,
                 'wall_s': 0.001, 'measured_tok_s': 1000.0,
                 'scope': 'MODEL_FREE_ENGINE_MECHANICS_ONLY'}
        response = {'tokens': [1], 'content': 'fixture', 'timings': {'draft_n': 0}}
    else:
        if not all((args.url, args.server_log, args.manifest, args.production_recipe,
                    args.image_proof, args.argv_record,
                    args.n_ctx_per_slot_required)):
            raise RuntimeError('target qualification needs URL, startup log, frozen manifest, and per-slot context')
        slots = request(args.url, '/slots')
        props = request(args.url, '/props')
        if not isinstance(slots, list) or len(slots) != 4 or props.get('total_slots') != 4:
            raise RuntimeError('server omitted /slots n_ctx')
        per_slot = {int(slot['n_ctx']) for slot in slots}
        if per_slot != {args.n_ctx_per_slot_required}:
            raise RuntimeError(f'actual per-slot context mismatch: {per_slot}')
        n_ctx_total = total_ctx_from_log(args.server_log)
        if n_ctx_total != args.n_ctx_required:
            raise RuntimeError(f'actual total context mismatch: {n_ctx_total}')
        rows, token_proof = capture_token_preflight(
            args.url, args.manifest,
            'frontdoor_mtp' if args.n_ctx_required == 262144 else 'architect_dflash',
            results / 'TOKEN-PREFLIGHT', args.image_proof, args.production_recipe)
        rendered = [row['rendered'] for row in rows]
        tokenized = [row['tokens'] for row in rows]
        max_index = max(range(len(tokenized)), key=lambda index: len(tokenized[index]))
        prompt = rendered[max_index]
        tokens = tokenized[max_index]
        request_body = {
            'prompt': prompt, 'temperature': 0.0, 'top_k': 1, 'seed': 42,
            'n_predict': 96, 'return_tokens': True, 'stream': False, 'n_probs': 0,
            'cache_prompt': False}
        actual_kv_mode = kv_mode_from_log(args.server_log)
        source = {'issued_scope': 'KEEPER_HARD_QUAL_FIRST_REQUEST', 'id': common['id'],
                  'nonce': common['nonce'], 'phase': phase, 'manifest_sha256': sha(args.manifest),
                  'image_proof_sha256': sha(args.image_proof), 'argv_record_sha256': sha(args.argv_record),
                  'production_recipe_sha256': sha(args.production_recipe),
                  'actual_model_path': props.get('model_path'),
                  'n_ctx_total': n_ctx_total, 'n_ctx_per_slot': args.n_ctx_per_slot_required,
                  'total_slots': 4, 'kv_cache_mode': actual_kv_mode,
                  'prompt_index': max_index, 'prompt_tokens': len(tokens),
                  'prompt_token_ids_sha256': hashlib.sha256(canonical(tokens)).hexdigest(),
                  'observed_cpus': common['observed_cpus']}
        response, wall = completion(args.url, request_body, results, source)
        generated = response['tokens']
        first = {'ok': True, 'n_ctx_total': n_ctx_total,
                 'n_ctx_per_slot': args.n_ctx_per_slot_required,
                 'total_slots': 4, 'prompt_tokens': len(tokens),
                 'kv_cache_mode': actual_kv_mode,
                 'production_recipe_sha256': sha(args.production_recipe),
                 'wall_s': wall, 'measured_tok_s': len(generated) / wall,
                 'scope': 'TARGET_SCRATCH_SERVER',
                 'manifest_sha256': hashlib.sha256(pathlib.Path(args.manifest).read_bytes()).hexdigest()}
    result_path = results / 'QUAL-RESULT.json'
    result_sha = write(result_path, {'first_request': first, 'raw_response': response})
    if phase == 'cutoff':
        event_path = pathlib.Path(os.environ['WS58_QUAL_CUTOFF_EVENT'])
        stopfile = pathlib.Path(os.environ['FILLER_STOPFILE'])
        native_pid = int(os.environ['DF2_NATIVE_PID'])
        native_birth = int(os.environ['DF2_NATIVE_BIRTH'])
        stat = pathlib.Path(f'/proc/{native_pid}/stat').read_text().rsplit(') ', 1)[1].split()
        if int(stat[19]) != native_birth or os.getpgid(native_pid) != os.getpgrp():
            raise RuntimeError('native server was not live in owned qualification PGID at first event')
        atomic_write(event_path, {**common, 'native_first_event': True,
                                  'native_pid': native_pid, 'native_birth_ticks': native_birth,
                                  'first_request': first})
        limit = time.monotonic() + 90
        while not stopfile.exists() and time.monotonic() < limit:
            if not pathlib.Path(f'/proc/{native_pid}').exists():
                raise RuntimeError('native server died before cutoff STOP')
            time.sleep(.05)
        if not stopfile.exists():
            raise RuntimeError('canonical qualifier did not issue active STOP')
        write(results / 'PARTIAL.json', {'partial': True, 'unknown_disposition': 'UNKNOWN',
                                         'stop_observed': True, 'first_request': first})
        atomic_write(proof_path, {**common, 'first_request': first, 'partial': True,
                                  'stop_observed': True, 'unknown_disposition': 'UNKNOWN'})
        disposition(results, 'PARTIAL_UNKNOWN', evidence={'proof_sha256': sha(proof_path),
                    'first_request': first})
        return 75
    proof = {**common, 'first_request': first, 'result_writer': {'ok': True, 'result_path': str(result_path),
             'sha256': result_sha}, 'disk': {'job_floor_gib': 150}}
    write(proof_path, proof)
    if args.mode == 'target':
        disposition(results, 'ACCEPTED', evidence={'proof_sha256': sha(proof_path),
                    'result_sha256': result_sha})
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        if os.environ.get('FILLER_RESULTS_DIR'):
            disposition(pathlib.Path(os.environ['FILLER_RESULTS_DIR']),
                        'FAILED_OR_EXPOSURE_UNKNOWN', error=repr(exc))
        raise
