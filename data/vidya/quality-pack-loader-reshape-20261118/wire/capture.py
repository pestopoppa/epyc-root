#!/usr/bin/env python3
"""Run the pinned CPU loader diagnostic or its small-model publisher smoke."""

import argparse
import json
from http.client import HTTPException
import os
from pathlib import Path
import signal

import cpu_native as native
from make_plan import PROFILE, ROW, build_plan
import quality_parity as parity
import qwen4exp_cpu_loader_contract as contract
from qwen4exp_cpu_loader_contract import SCHEMA

D = native.D
def preflight(plan):
    if plan != build_plan():
        raise ValueError('CPU loader diagnostic plan drift')
    for name, pin in plan['receipts_sha256'].items():
        if native.file_sha(D / name) != pin:
            raise ValueError(f'pre-grant asset receipt drift: {name}')
    for item in (*plan['items'], *plan['smoke_items']):
        name = item['id']
        wire = (D / 'requests' / f'{name}.json').read_bytes()
        if wire != native.canonical(item['request_body']) or native.sha(wire) != plan['request_files'][name]:
            raise ValueError(f'prospective request bytes changed: {name}')
    verify_models(plan)
    for arm in plan['arms'].values():
        if arm['runtime_files'][arm['binary']] != arm['binary_sha256']:
            raise ValueError('runtime executable differs from its declared digest')
        for key in ('build_manifest', 'build_identity'):
            if key in arm and native.file_sha(Path(arm[key])) != arm[f'{key}_sha256']:
                raise ValueError(f'{key} differs from receipt')
        for filename, pin in arm['runtime_files'].items():
            if native.file_sha(Path(filename)) != pin:
                raise ValueError(f'runtime bytes differ from receipt: {filename}')


def verify_models(plan):
    for entry in (*plan['model_shards'], plan['smoke_model']):
        file = Path(entry['path'])
        # The original hash witness predates inference. No model weights are read here.
        if file.resolve(strict=True) != file or native.stat_id(file) != entry['stat']:
            raise ValueError(f'model changed since pre-grant hash witness: {file}')


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    plan_path = D / 'plan.json'
    plan_bytes = plan_path.read_bytes()
    plan_pin = native.sha(plan_bytes)
    plan = json.loads(plan_bytes)
    if args.preflight:
        preflight(plan)
        return 0

    signal.signal(signal.SIGTERM, native.stop_signal)
    smoke = os.getenv('FILLER_DRYRUN') == '1'
    result = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D / 'out' / 'RESULT.json'
    result.parent.mkdir(parents=True, exist_ok=True)
    out = result.parent / 'native'
    started_at = contract.utc_now()
    phase = 'preflight'
    state = {
        'schema': SCHEMA, 'status': 'incomplete', 'profile': PROFILE, 'row_id': ROW,
        'scope': plan['scope'], 'request_plan_sha256': plan_pin,
        'source_manifest_sha256': native.file_sha(D / 'SOURCE.sha256'),
        'validator_source_sha256': parity.VALIDATOR_SOURCE_SHA256,
        'loader_witness_sha256': plan['receipts_sha256']['loader-reshape-witness.json'],
        'prior_frontdoor_receipt_sha256': plan['receipts_sha256']['frontdoor-full-receipt.json'],
        'broad_pack_status': 'incomplete', 'broad_pack_input': False,
        'quality_transfer_authorized': False, 'promotion_authorized': False,
    }
    try:
        preflight(plan)
        deadline = native.deadline_epoch(os.environ['FILLER_DEADLINE'])
        stop = Path(os.environ['FILLER_STOPFILE'])
        native.budget(deadline, stop, 1)
        grant = Path(os.environ['FILLER_GRANTS_DIR']) / (os.environ['FILLER_ID'] + '.grant')
        cpus = sorted(os.sched_getaffinity(0))
        if len(cpus) != (4 if smoke else 24):
            raise ValueError('CPU affinity does not match granted smoke or quarter shape')
        out.mkdir()
        state['cpus'] = cpus
        grant_bytes = grant.read_bytes()
        native.write(out / 'scheduler.grant', grant_bytes)
        state['grant_sha256'] = native.sha(grant_bytes)
        recipe = plan['recipes']['smoke_control' if smoke else 'diagnostic']
        item, = plan['smoke_items' if smoke else 'items']
        state['checks'] = {}
        state['captures'] = {}
        for arm in ('production',) if smoke else ('production', 'candidate'):
            phase = arm
            native.budget(deadline, stop, 1)
            verify_models(plan)
            runtime = plan['arms'][arm]
            bank = out / 'banked-capture.json'
            if arm == 'candidate' and native.file_sha(bank) != state['captures']['production']:
                raise ValueError('production diagnostic capture changed before C13 launch')
            row, = native.capture_arm(arm, runtime, recipe, [item], out, cpus, deadline, stop)
            if native.file_sha(plan_path) != plan_pin:
                raise ValueError('plan changed during capture')
            verify_models(plan)
            target = out / arm
            evidence = None
            if not smoke:
                evidence = contract.loader_log_evidence((target / 'server.log').read_bytes(), plan, arm)
                name = item['id']
                state['checks'][arm] = contract.check_response(
                    item, row, (target / f'{name}.request.json').read_bytes(),
                    (target / f'{name}.response.json').read_bytes(), recipe['endpoint'], parity,
                )
            identity = {
                'profile': 'smoke-control' if smoke else PROFILE,
                'model': plan['smoke_model'] if smoke else plan['model_shards'],
                'recipe_sha256': native.sha(native.canonical(recipe)),
                'request_plan_sha256': plan_pin, 'grant_sha256': state['grant_sha256'],
                'loader_witness_sha256': None if smoke else state['loader_witness_sha256'],
                'capture_runner_sha256': native.file_sha(Path(__file__)),
                'cleanup_sha256': native.file_sha(target / 'cleanup.json'),
                'server_sha256': native.file_sha(target / 'server.json'),
            }
            capture_name = 'banked-capture' if arm == 'production' else 'candidate-diagnostic-capture'
            path = out / f'{capture_name}.json'
            record = {'capture_identity': identity, 'runtime': runtime, 'items': [row]}
            if evidence:
                record['loader_log_evidence'] = evidence
            if arm == 'candidate':
                record['production_diagnostic_capture_sha256'] = state['captures']['production']
            digest = native.write_json(path, record)
            native.write(out / f'{capture_name}.sha256', (digest + '\n').encode())
            state['captures'][arm] = digest
            if native.file_sha(bank) != state['captures']['production']:
                raise ValueError('production diagnostic capture changed')
            if smoke:
                native.write_json(result, {
                    'schema': 'epyc.quality_pack_native_slice.v1', 'status': 'capture-complete',
                    'mode': 'native-smoke-control', 'target_profile': PROFILE, 'cpus': cpus,
                    'capture_identity': identity, 'bank_sha256': digest, 'candidate_sha256': None,
                    'prior_frontdoor_json_mismatch': True, 'broad_pack_status': 'incomplete',
                    'quality_transfer_authorized': False, 'promotion_authorized': False,
                })
                return 0
        phase = 'decision'
        native.budget(deadline, stop, 1)
        state['status'] = (
            'loader_diagnostic_complete'
            if all(check['semantic_matches'] and check['finish'] == check['expected_finish']
                   for check in state['checks'].values())
            else 'loader_exercised_response_refused'
        )
        prod, cand = (state['checks'][arm] for arm in ('production', 'candidate'))
        state['comparison'] = {key + '_equal': prod[key] == cand[key] for key in
                               ('finish', 'token_ids', 'content_sha256', 'reasoning_sha256')}
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, HTTPException) as exc:
        state['error'] = {'phase': phase, 'type': type(exc).__name__, 'message': str(exc)}
        native.write_json(result, state)
        if not smoke:
            contract.write_seal(D, result, started_at)
        return 75 if isinstance(exc, InterruptedError) else 1
    native.write_json(result, state)
    contract.write_seal(D, result, started_at)
    return 0 if state['status'] == 'loader_diagnostic_complete' else 1


if __name__ == '__main__':
    raise SystemExit(run())
