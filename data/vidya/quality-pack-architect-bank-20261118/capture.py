#!/usr/bin/env python3
"""Capture and strictly admit a prospective architect-critic production bank."""
import argparse
import base64
from http.client import HTTPException
import json
import os
from pathlib import Path
import signal

import capture_base as capture
import quality_parity as parity

D = Path(__file__).resolve().parent


def validate_items(plan, records, production):
    recipe = plan['recipes']['architect_critic_slice']
    expected = {item['id']: item for item in plan['items']}
    actual = {row['id']: row for row in records}
    if len(actual) != len(records) or expected.keys() != actual.keys():
        raise ValueError('bank response inventory differs from the pinned requests')
    audit = {}
    for name, item in expected.items():
        body = item['request_body']
        wire = parity.canonical_json(body)
        record = {key: value for key, value in actual[name].items() if key != 'id'}
        request = (production / f'{name}.request.json').read_bytes()
        response = (production / f'{name}.response.json').read_bytes()
        _, limit = parity._request(body, recipe['endpoint'])
        problems = []
        checks = {}
        try:
            if wire != request or response != base64.b64decode(record['response_b64'], validate=True):
                raise ValueError('raw request or response differs from its capture record')
            content, reasoning, finish, tokens, count = parity._capture(
                record, capture.sha(request), recipe['endpoint'], None, limit,
            )
            checks = {
                'expected_finish': item['expected_finish'], 'actual_finish': finish,
                'semantic_matches': parity._semantic_matches(item['validator'], content),
                'completion_count': count, 'output_token_count': None if tokens is None else len(tokens),
                'content_sha256': capture.sha(content.encode()),
                'reasoning_sha256': None if reasoning is None else capture.sha(reasoning.encode()),
            }
            if finish != item['expected_finish']:
                problems.append('finish_mismatch')
            if not checks['semantic_matches']:
                problems.append('semantic_validation_failed')
            if tokens is None:
                problems.append('missing_output_token_ids')
            if count is None:
                problems.append('missing_completion_count')
            if item['output_format'] == 'json' and item['validator']['id'] != 'json-object-subset.v1':
                problems.append('json_object_validator_required')
        except (ValueError, TypeError, KeyError) as exc:
            problems.append(f'invalid_capture: {exc}')
        audit[name] = {**checks, 'problems': problems}
    return audit


def verify_plan(plan):
    capture.verify_files(plan)
    original = plan['original_architect_critic']
    if capture.file_sha(D / 'original-architect-critic-receipt.json') != original['filing_sha256']:
        raise ValueError('original architect-critic filing changed')
    items = plan['items']
    if capture.sha(parity.canonical_json(items)) != plan['question_pool_sha256']:
        raise ValueError('question pool differs from the prospective pin')
    if len(items) != 4 or len({item['id'] for item in items}) != 4:
        raise ValueError('expected four unique architect-critic requests')
    endpoint = plan['recipes']['architect_critic_slice']['endpoint']
    for item in items:
        parity._request(item['request_body'], endpoint)
        parity._semantic_matches(item['validator'], '')
        if item['fixture'] is not None or item['dflash_pair'] is not None:
            raise ValueError('unsupported fixture or DFlash declaration for this prerequisite')
        if item['expected_finish'] not in parity.FINISHES or item['output_format'] not in parity.FORMATS:
            raise ValueError('unsupported finishes or formats in the prospective plan')


def run(plan, plan_pin):
    result_path = D / 'out/RESULT.json'
    out = result_path.parent / 'native'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    state = {
        'schema': 'epyc.quality_pack_architect_critic_bank.v1',
        'status': 'incomplete',
        'profile': plan['profile'],
        'question_pool_sha256': plan['question_pool_sha256'],
        'request_plan_sha256': plan_pin,
        'validator_source_sha256': parity.VALIDATOR_SOURCE_SHA256,
        'capture_runner_sha256': capture.file_sha(Path(capture.__file__)),
        'bank_gate_sha256': capture.file_sha(Path(__file__)),
        'original_architect_critic': plan['original_architect_critic'],
        'observation_only': True,
        'candidate_collected': False,
        'broad_pack_status': 'incomplete',
        'quality_transfer_authorized': False,
        'promotion_authorized': False,
    }
    phase = 'preflight'
    try:
        verify_plan(plan)
        deadline = capture.deadline_epoch(os.environ['FILLER_DEADLINE'])
        stop = Path(os.environ['FILLER_STOPFILE'])
        capture.budget(deadline, stop, 1)
        grant = Path(os.environ['FILLER_GRANTS_DIR']) / (os.environ['FILLER_ID'] + '.grant')
        capture.write(out / 'scheduler.grant', grant.read_bytes())
        cpus = sorted(os.sched_getaffinity(0))
        if len(cpus) != 24:
            raise ValueError('requires exactly one granted 24-CPU quarter')
        state['cpus'] = cpus
        phase = 'production_capture'
        recipe = plan['recipes']['architect_critic_slice']
        rows = capture.capture_arm(
            'production', plan['arms']['production'], recipe, plan['items'], out, cpus, deadline, stop,
        )
        phase = 'bank_admission'
        capture.budget(deadline, stop, 1)
        verify_plan(plan)
        if capture.file_sha(D / 'plan.json') != plan_pin:
            raise ValueError('prospective plan changed during production capture')
        state['recipe_sha256'] = capture.sha(parity.canonical_json(recipe))
        state['prompt_template_sha256'] = plan['architect_critic_template']['sha256']
        state['model'] = plan['architect_critic_model']
        state['checks'] = validate_items(plan, rows, out / 'production')
        if any(check['problems'] for check in state['checks'].values()):
            state['status'] = 'inadmissible_bank'
        else:
            state['status'] = 'bank_admitted'
        bank = out / 'production-capture.json'
        state['capture_sha256'] = capture.write_json(bank, {
            'identity': state, 'runtime': plan['arms']['production'], 'items': rows,
        })
        capture.write(out / 'production-capture.sha256', (state['capture_sha256'] + '\n').encode())
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
    plan = json.loads(raw)
    if args.preflight:
        verify_plan(plan)
        return 0
    if os.getenv('FILLER_DRYRUN') == '1':
        verify_plan(plan)
        return capture.main()
    signal.signal(signal.SIGTERM, capture.stop_signal)
    return run(plan, capture.sha(raw))


if __name__ == '__main__':
    raise SystemExit(main())
