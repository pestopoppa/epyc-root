#!/usr/bin/env python3
"""Capture one new production response and admit a four-item ingest bank."""
import argparse
import base64
from http.client import HTTPException
import json
import os
from pathlib import Path
import signal

import capture_base as capture
from make_plan import NEW_ITEM, ORIGINAL, ORIGINAL_ITEM, build_plan, load_filing, load_original, read_pinned
import quality_parity as parity

D = Path(__file__).resolve().parent
RECIPE = 'ingest_long_context_slice'


def validate_item(item, row, request, response, recipe):
    record = {key: value for key, value in row.items() if key != 'id'}
    body = item['request_body']
    endpoint = recipe['endpoint']
    _, limit = parity._request(body, endpoint)
    if row['id'] != item['id'] or capture.canonical(body) != request:
        raise ValueError(f"{item['id']}: request identity drift")
    if response != base64.b64decode(record['response_b64'], validate=True):
        raise ValueError(f"{item['id']}: raw response differs from capture record")
    content, reasoning, finish, tokens, count = parity._capture(
        record, capture.sha(request), endpoint, None, limit,
    )
    data = parity._parse(response)
    capture.verify_no_spec_response(data, item, recipe)
    checks = {
        'expected_finish': item['expected_finish'], 'actual_finish': finish,
        'semantic_matches': parity._semantic_matches(item['validator'], content),
        'request_sha256': record['request_sha256'], 'response_sha256': record['response_sha256'],
        'completion_count': count, 'output_token_count': len(tokens),
        'prompt_tokens': data['usage']['prompt_tokens'],
        'cached_prompt_tokens': data['usage']['prompt_tokens_details']['cached_tokens'],
        'content_sha256': capture.sha(content.encode()),
        'reasoning_sha256': None if reasoning is None else capture.sha(reasoning.encode()),
        'problems': [],
    }
    if finish != item['expected_finish']:
        checks['problems'].append('finish_mismatch')
    if not checks['semantic_matches']:
        checks['problems'].append('semantic_validation_failed')
    return checks


def original_production(plan, original, filing):
    folder = ORIGINAL / 'full-capture'
    files = filing['files']

    def filed(name):
        return read_pinned(folder / name, files[name])

    def original_bytes(name):
        filed(name + '.original-bytes.json')
        return read_pinned(folder / (name + '.original-bytes.json'),
                           filing['original_files_sha256'][name], envelope=True)

    old_pin = plan['original_production']['bank_sha256']
    if old_pin != filed('native/banked-capture.sha256').decode().strip():
        raise ValueError('filed production bank sidecar differs')
    bank = parity._parse(original_bytes('native/banked-capture.json'))
    result = parity._parse(original_bytes('RESULT.json'))
    identity = bank['capture_identity']
    recipe = original['recipes'][RECIPE]
    if (
        filing['rc'] != 0 or filing['verdict'] != 'pass'
        or result['status'] != 'capture-complete' or result['bank_sha256'] != old_pin
        or result['capture_identity'] != identity or result['request_count_per_arm'] != 4
        or bank['runtime'] != plan['arms']['production'] or identity['profile'] != plan['profile']
        or identity['model'] != original['ingest_long_context_model']
        or identity['prompt_template_sha256'] != plan['ingest_long_context_template']['sha256']
        or identity['question_pool_sha256'] != original['question_pool_sha256']
        or identity['request_plan_sha256'] != plan['original_production']['plan_sha256']
        or identity['recipe_sha256'] != capture.sha(capture.canonical(recipe))
    ):
        raise ValueError('original production custody differs from pinned identity')
    server_raw = filed('native/production/server.json')
    cleanup_raw = filed('native/production/cleanup.json')
    server = parity._parse(server_raw)
    cleanup = parity._parse(cleanup_raw)
    if (
        server['image'] != bank['runtime'] or server['recipe'] != recipe
        or server['cpus'] != result['cpus'] or len(set(server['cpus'])) != 24
        or server['pid'] != cleanup['pid'] or cleanup['dead'] is not True
        or cleanup['port_closed'] is not True or cleanup != filing['cleanup']['production']
    ):
        raise ValueError('original production server or cleanup differs from its filing')
    found = {row['id']: row for row in bank['items']}
    old_items = {item['id']: item for item in original['items']}
    new_items = {item['id']: item for item in plan['items']}
    if len(found) != len(bank['items']) or found.keys() != old_items.keys():
        raise ValueError('original production request roster differs')
    if new_items.keys() != ((old_items.keys() - {ORIGINAL_ITEM}) | {NEW_ITEM}):
        raise ValueError('new request roster does not replace exactly one item')
    checks = {}
    preserved = {}
    for name, item in old_items.items():
        request = filed(f'native/production/{name}.request.json')
        response = filed(f'native/production/{name}.response.json')
        check = validate_item(item, found[name], request, response, recipe)
        checks[name] = {**check, 'validator': item['validator'], 'output_format': item['output_format'],
                        'capture': 'filed_original'}
        if name == ORIGINAL_ITEM:
            if check['problems'] != ['semantic_validation_failed']:
                raise ValueError('original replacement rationale does not replay')
        else:
            if check['problems'] or item != new_items[name]:
                raise ValueError(f'{name}: original item failed revalidation or was changed')
            preserved[name] = (found[name], request, response)
    return checks, preserved, server_raw, cleanup_raw


def preflight(plan):
    original = load_original()
    filing = load_filing()
    if plan != build_plan(original, filing):
        raise ValueError('plan differs from its prospective recipe, request or custody pins')
    capture.verify_files(plan)
    requests = capture.read_requests(plan)
    original_data = original_production(plan, original, filing)
    return requests, original_data


def get_grant():
    deadline = capture.deadline_epoch(os.environ['FILLER_DEADLINE'])
    stop = Path(os.environ['FILLER_STOPFILE'])
    capture.budget(deadline, stop, 1)
    grant = Path(os.environ['FILLER_GRANTS_DIR']) / (os.environ['FILLER_ID'] + '.grant')
    return deadline, stop, grant.read_bytes()


def smoke(plan, requests):
    deadline, stop, grant = get_grant()
    cpus = sorted(os.sched_getaffinity(0))
    if len(cpus) != 4:
        raise ValueError('native smoke requires exactly four granted CPUs')
    path = Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
    out = path.parent / 'native'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    capture.write(out / 'scheduler.grant', grant)
    recipe = plan['recipes']['smoke_control']
    runtime = plan['arms']['production']
    items = plan['smoke_items']
    rows = capture.capture_arm('production', runtime, recipe, items, requests, out, cpus, deadline, stop)
    capture.budget(deadline, stop, 1)
    identity = {'profile': 'smoke-control', 'model': plan['smoke_model'],
                'recipe_sha256': capture.sha(capture.canonical(recipe)),
                'question_pool_sha256': capture.sha(capture.canonical(items)),
                'request_plan_sha256': capture.file_sha(D / 'plan.json'),
                'capture_runner_sha256': capture.file_sha(Path(capture.__file__))}
    bank_pin = capture.write_json(out / 'banked-capture.json', {
        'capture_identity': identity, 'runtime': runtime, 'items': rows,
    })
    capture.write_json(path, {
        'schema': 'epyc.quality_pack_native_slice.v1', 'status': 'capture-complete',
        'mode': 'native-smoke-control', 'target_profile': plan['profile'], 'cpus': cpus,
        'capture_identity': identity, 'bank_sha256': bank_pin, 'candidate_sha256': None,
        'prior_frontdoor_json_mismatch': True, 'broad_pack_status': 'incomplete',
        'quality_transfer_authorized': False, 'promotion_authorized': False,
    })
    return 0


def run(plan, plan_pin):
    result_path = D / 'out/RESULT.json'
    out = result_path.parent / 'native'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    state = {
        'schema': 'epyc.quality_pack_ingest_reconciliation_bank.v1', 'status': 'incomplete',
        'profile': plan['profile'], 'question_pool_sha256': plan['question_pool_sha256'],
        'request_plan_sha256': plan_pin, 'source_manifest_sha256': capture.file_sha(D / 'SOURCE.sha256'),
        'validator_source_sha256': parity.VALIDATOR_SOURCE_SHA256,
        'capture_runner_sha256': capture.file_sha(Path(capture.__file__)),
        'bank_gate_sha256': capture.file_sha(Path(__file__)),
        'model': plan['ingest_long_context_model'],
        'prompt_template_sha256': plan['ingest_long_context_template']['sha256'],
        'prior_frontdoor_receipt_sha256': plan['prior_frontdoor_json_mismatch']['receipt_sha256'],
        'original_production': plan['original_production'],
        'candidate_collected': False, 'broad_pack_status': 'incomplete',
        'quality_transfer_authorized': False, 'promotion_authorized': False,
    }
    phase = 'preflight'
    try:
        requests, (prior_checks, preserved, server, cleanup) = preflight(plan)
        state['original_checks'] = prior_checks
        deadline, stop, grant = get_grant()
        capture.write(out / 'scheduler.grant', grant)
        cpus = sorted(os.sched_getaffinity(0))
        if len(cpus) != 24:
            raise ValueError('requires exactly one granted 24-CPU quarter')
        state['cpus'] = cpus
        phase = 'production_capture'
        recipe = plan['recipes'][RECIPE]
        state['recipe_sha256'] = capture.sha(capture.canonical(recipe))
        target, = [item for item in plan['items'] if item['id'] == NEW_ITEM]
        runtime = plan['arms']['production']
        replacement, = capture.capture_arm(
            'production', runtime, recipe, [target], requests, out, cpus, deadline, stop,
        )
        phase = 'bank_admission'
        capture.budget(deadline, stop, 1)
        preflight(plan)
        if capture.file_sha(D / 'plan.json') != plan_pin:
            raise ValueError('prospective plan changed during capture')
        new_folder = out / 'production'
        new_check = validate_item(target, replacement,
                                  (new_folder / f'{NEW_ITEM}.request.json').read_bytes(),
                                  (new_folder / f'{NEW_ITEM}.response.json').read_bytes(), recipe)
        new_check.update({'capture': 'prospective_replacement', 'validator': target['validator']})
        state['checks'] = {name: prior_checks[name] for name in preserved} | {NEW_ITEM: new_check}
        prior_folder = out / 'prior-production'
        prior_folder.mkdir()
        capture.write(prior_folder / 'server.json', server)
        capture.write(prior_folder / 'cleanup.json', cleanup)
        for name, (_, request, response) in preserved.items():
            capture.write(prior_folder / f'{name}.request.json', request)
            capture.write(prior_folder / f'{name}.response.json', response)
        if new_check['problems']:
            state['status'] = 'inadmissible_bank'
        else:
            state['status'] = 'bank_admitted'
        rows = {name: record for name, (record, _, _) in preserved.items()} | {NEW_ITEM: replacement}
        capture.budget(deadline, stop, 1)
        seal = {'identity': state, 'runtime': runtime, 'items': [rows[item['id']] for item in plan['items']]}
        digest = capture.write_json(out / 'production-capture.json', seal)
        capture.write(out / 'production-capture.sha256', (digest + '\n').encode())
        state['capture_sha256'] = digest
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, HTTPException) as exc:
        state['status'] = 'incomplete'
        state['error'] = {'phase': phase, 'type': type(exc).__name__, 'message': str(exc)}
        capture.write_json(result_path, state)
        return 75 if isinstance(exc, InterruptedError) else 1
    capture.write_json(result_path, state)
    return 0 if state['status'] == 'bank_admitted' else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    raw = (D / 'plan.json').read_bytes()
    plan = parity._parse(raw)
    if args.preflight:
        preflight(plan)
        return 0
    signal.signal(signal.SIGTERM, capture.stop_signal)
    if os.getenv('FILLER_DRYRUN') == '1':
        requests, _ = preflight(plan)
        return smoke(plan, requests)
    return run(plan, capture.sha(raw))


if __name__ == '__main__':
    raise SystemExit(main())
