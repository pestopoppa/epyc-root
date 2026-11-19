#!/usr/bin/env python3
"""Capture and strictly admit the prospective architect-general HIP bank."""

import argparse
import base64
from http.client import HTTPException
import json
import os
from pathlib import Path
import signal

import capture_base as native
from capture_base import D, PROFILE, canonical, sha
from loader_log import loader_log_evidence
from make_plan import ROW, build_plan
import quality_parity as parity

SCHEMA = 'epyc.architect_general_hip_loader_bank.v1'


def preflight(plan):
    if plan != build_plan(D):
        raise ValueError('sealed HIP fixture plan drift')
    native.verify_files(plan)
    native.vram_device(plan['recipes']['hip_slice'])
    return native.read_requests(plan)


def validate_capture(plan, item, row, production):
    recipe = plan['recipes']['hip_slice']
    endpoint = recipe['endpoint']
    name = item['id']
    wire = (production / f'{name}.request.json').read_bytes()
    raw = (production / f'{name}.response.json').read_bytes()
    record = {field: row[field] for field in ('request_sha256', 'response_b64', 'response_sha256')}
    if (row['id'] != name or wire != canonical(item['request_body'])
            or raw != base64.b64decode(record['response_b64'], validate=True)):
        raise ValueError('native request/response bytes differ from the sealed fixture or capture')
    _, limit = parity._request(item['request_body'], endpoint)
    content, _, finish, tokens, count = parity._capture(record, sha(wire), endpoint, None, limit)
    native.verify_no_spec_response(parity._parse(raw), item, recipe)

    server = json.loads((production / 'server.json').read_bytes())
    cleanup = json.loads((production / 'cleanup.json').read_bytes())
    pid = server['pid']
    runtime = plan['arms']['production']
    expected_args = [runtime['binary'], '--host', '127.0.0.1', '--port', str(native.PORT),
                     '--threads', str(len(recipe['cpu_affinity'])), *recipe['args']]
    if (server['image'] != runtime or server['recipe'] != recipe
            or server['cpus'] != recipe['cpu_affinity']
            or server['argv'] != expected_args
            or cleanup['pid'] != pid or any(cleanup[key] is not True for key in (
                'dead', 'port_closed', 'kfd_entry_absent',
            ))):
        raise ValueError('native runtime, trace or captured-PID cleanup witness differs')
    residency = (production / f'{name}.hip-residency.json').read_bytes()
    if sha(residency) != row['hip_residency_sha256']:
        raise ValueError('HIP residency witness differs from capture')
    samples = json.loads(residency)
    if samples['errors'] or len({sample['t_ns'] for sample in samples['samples']}) < 2:
        raise ValueError('fewer than two clean and distinct HIP samples')
    libraries = {
        path: {'device': pin['stat'][0], 'inode': pin['stat'][1], 'sha256': pin['sha256']}
        for path, pin in (runtime['runtime_files'] | runtime['rocm_files']).items()
        if path != runtime['binary']
    }
    if server['mapped_libraries'] != libraries:
        raise ValueError('native mapped libraries differ from the runtime pin')
    for sample in samples['samples']:
        if (not samples['request_sent_ns'] <= sample['t_ns'] <= samples['response_end_ns']
                or sample['pid'] != pid or pid not in sample['kfd_pids']
                or sample['gpu_id'] != recipe['gpu_id']
                or not 0 < sample['process_vram_bytes'] <= recipe['max_vram_bytes']
                or sample['device_vram_bytes'] <= 0 or sample['mapped_libraries'] != libraries):
            raise ValueError('HIP sample lacks in-window same-PID MI210 residency or mapped libraries')
    return {
        'finish': finish, 'expected_finish': item['expected_finish'],
        'semantic_matches': parity._semantic_matches(item['validator'], content),
        'completion_count': count, 'output_token_count': len(tokens),
        'content_sha256': sha(content.encode()),
        'hip_residency_sha256': sha(residency),
        'server_sha256': native.file_sha(production / 'server.json'),
        'cleanup_sha256': native.file_sha(production / 'cleanup.json'),
        'capture': record,
    }


def run(plan, plan_pin, result, smoke, threads):
    out = result.parent / 'native'
    phase = 'preflight'
    state = {
        'schema': SCHEMA, 'status': 'incomplete', 'row_id': ROW, 'profile': PROFILE,
        'request_plan_sha256': plan_pin, 'validator_source_sha256': parity.VALIDATOR_SOURCE_SHA256,
        'source_manifest_sha256': native.file_sha(D / 'SOURCE.sha256'),
        'source_receipts_sha256': plan['source_receipts_sha256'],
        'scope': plan['scope'], 'candidate_collected': False, 'broad_pack_status': 'incomplete',
        'quality_transfer_authorized': False, 'promotion_authorized': False,
    }
    result.parent.mkdir(parents=True, exist_ok=True)
    try:
        requests = preflight(plan)
        deadline = native.deadline_epoch(os.environ['FILLER_DEADLINE'])
        stop = Path(os.environ['FILLER_STOPFILE'])
        native.budget(deadline, stop, 1)
        grant = Path(os.environ['FILLER_GRANTS_DIR']) / (os.environ['FILLER_ID'] + '.grant')
        cpus = sorted(os.sched_getaffinity(0))
        recipe = plan['recipes']['smoke_control' if smoke else 'hip_slice']
        if os.environ.get('FILLER_NEEDGPU') != '1' or os.environ.get('FILLER_GPU_FENCE') == '1':
            raise ValueError('native capture requires an unfenced MI210 grant')
        if len(cpus) != (4 if smoke else threads) or (not smoke and cpus != recipe['cpu_affinity']):
            raise ValueError('CPU affinity differs from the granted smoke or the pinned HIP profile')

        out.mkdir()
        native.write(out / 'scheduler.grant', grant.read_bytes())
        state['grant_sha256'] = native.file_sha(out / 'scheduler.grant')
        state['cpus'] = cpus
        items = plan['smoke_items' if smoke else 'items']
        runtime = plan['arms']['production']
        phase = 'native_capture'
        rows = native.capture_arm('production', runtime, recipe, items, requests, out, cpus, deadline, stop)
        phase = 'admission'
        native.budget(deadline, stop, 1)
        if native.file_sha(D / 'plan.json') != plan_pin or preflight(plan) != requests:
            raise ValueError('plan or prospective request files changed during capture')
        identity = {
            'profile': 'smoke-control' if smoke else PROFILE,
            'model': plan['smoke_model'] if smoke else plan['model_shards'],
            'recipe_sha256': sha(canonical(recipe)), 'request_plan_sha256': plan_pin,
            'question_pool_sha256': sha(canonical(items)),
            'grant_sha256': state['grant_sha256'],
        }
        if smoke:
            digest = native.write_json(out / 'banked-capture.json', {
                'capture_identity': identity, 'runtime': runtime, 'items': rows,
            })
            native.write_json(result, {
                **state, 'schema': 'epyc.quality_pack_native_slice.v1', 'status': 'capture-complete',
                'mode': 'native-smoke-control', 'target_profile': PROFILE, 'capture_identity': identity,
                'candidate_sha256': None, 'request_count_per_arm': 1, 'bank_sha256': digest,
                'prior_frontdoor_json_mismatch': True,
            })
            return 0

        if len(rows) != 4 or [row['id'] for row in rows] != [item['id'] for item in items]:
            raise ValueError('native production bank request roster differs from the four pinned items')
        production = out / 'production'
        state['checks'] = {
            item['id']: validate_capture(plan, item, row, production)
            for item, row in zip(items, rows, strict=True)
        }
        state['loader_log_evidence'] = loader_log_evidence(production / 'server.log', plan, 'production')
        admitted = all(check['semantic_matches'] and check['finish'] == check['expected_finish']
                       for check in state['checks'].values())
        state['status'] = 'bank_admitted' if admitted else 'inadmissible_bank'
        state['capture_identity'] = identity
        state['pack_shape'] = plan['pack_shape']
        bank = out / 'production-fixture-capture.json'
        state['capture_sha256'] = native.write_json(bank, {
            'identity': state, 'runtime': runtime, 'items': items, 'native_rows': rows,
        })
        native.write(out / 'production-fixture-capture.sha256', (state['capture_sha256'] + '\n').encode())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, HTTPException) as exc:
        state['status'] = 'incomplete'
        state['error'] = {'phase': phase, 'type': type(exc).__name__, 'message': str(exc)}
        native.write_json(result, state)
        return 75 if isinstance(exc, InterruptedError) else 1
    native.write_json(result, state)
    return 0 if state['status'] == 'bank_admitted' else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads', type=int, default=8)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    raw = (D / 'plan.json').read_bytes()
    plan = json.loads(raw)
    if args.preflight:
        preflight(plan)
        return 0
    signal.signal(signal.SIGTERM, native.stop_signal)
    smoke = os.environ.get('FILLER_DRYRUN') == '1'
    result = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D / 'out' / 'RESULT.json'
    return run(plan, sha(raw), result, smoke, args.threads)


if __name__ == '__main__':
    raise SystemExit(main())
