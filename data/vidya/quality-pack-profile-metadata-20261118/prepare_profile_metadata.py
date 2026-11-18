#!/usr/bin/env python3
"""Prepare prospective profile pins and proposed requests from sealed plan inputs."""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path

PROFILES = {
    'frontdoor-cpu-moe-mtp': ('native-20261118', 'frontdoor_slice', 'frontdoor_model', 'frontdoor_template'),
    'worker-general-cpu-moe-mtp': ('worker-general-20261118', 'worker_general_slice', 'worker_general_model', 'worker_general_template'),
    'architect-critic-cpu-mtp': ('architect-bank-20261118/successor-r2', 'architect_critic_slice', 'architect_critic_model', 'architect_critic_template'),
    'ingest-long-context-recurrent-no-spec': ('ingest-bank-20261118', 'ingest_long_context_slice', 'ingest_long_context_model', 'ingest_long_context_template'),
    'architect-general-hip': ('architect-general-hip-smoke-20261118', 'hip_slice', 'model_shards', 'template'),
    'worker-vision-hip-mmproj': ('worker-vision-20261118', 'hip_slice', 'model', 'template'),
    'dspark-dflash': ('dspark-dflash-20261118/successor-r3', 'cpu_slice', 'model_shards', 'template'),
}
TEXT_MARKERS = {
    'architect-general-hip-code': 'sorted(set(codes))',
    'architect-general-hip-reasoning': 'Gate B',
    'architect-general-hip-prose': 'Friday',
    'worker-vision-hip-mmproj-prose': 'left of',
    'worker-vision-hip-mmproj-reasoning': 'blue bar',
    'worker-vision-hip-mmproj-code': "shape = 'circle'",
}
DFLASH_VALIDATORS = {
    'json': {'id': 'json-object-subset.v1', 'expected': {'status': 'ready', 'count': 2, 'labels': ['alpha', 'beta']}},
    'code': {'id': 'contains-text.v1', 'expected': '% 2'},
    'reasoning': {'id': 'contains-text.v1', 'expected': '3 minutes'},
    'prose': {'id': 'contains-text.v1', 'expected': 'ledger'},
}


def parity_module(root):
    tool = root / '.claude/skills/kernel-promotion/scripts/quality_parity.py'
    spec = importlib.util.spec_from_file_location('quality_parity', tool)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archived_plan(path):
    envelope = json.loads(path.read_bytes())
    raw = base64.b64decode(envelope['bytes_b64'], validate=True)
    if hashlib.sha256(raw).hexdigest() != envelope['sha256']:
        raise ValueError(f'plan archive SHA-256 mismatch: {path}')
    return json.loads(raw), envelope['sha256']


def prospective_item(item, profile, descriptor):
    name = item['id']
    body = dict(item['request_body'])
    output_format = item['output_format'] if 'output_format' in item else item['format']
    validator = item.get('validator')
    finish = item.get('expected_finish', 'stop')
    fixture = item.get('fixture')
    pair = item.get('dflash_pair')
    if profile == 'dspark-dflash':
        validator = DFLASH_VALIDATORS[output_format]
        if output_format != 'json':
            finish = 'length'  # Proposed for the three unconstrained, fixed-budget continuations.
    elif validator is None:
        validator = ({'id': 'json-object-subset.v1', 'expected': item['reference']}
                     if output_format == 'json' else {'id': 'contains-text.v1', 'expected': TEXT_MARKERS[name]})
        if profile == 'architect-general-hip' and output_format == 'json':
            if descriptor is None:
                raise ValueError('a loader witness is required for the new HIP fixture')
            # New ID and fresh production capture preserve the original custody-only slice.
            name = 'architect-general-hip-loader-reshape-json'
            fixture = 'loader-reshape'
    return {
        'id': name, 'shape': profile, 'request_body': body, 'prompt_shape': item['prompt_shape'],
        'output_format': output_format, 'fixture': fixture, 'expected_finish': finish,
        'validator': validator, 'dflash_pair': pair,
    }


def runtime_pin(arm):
    binary = Path(arm['binary'])
    digest = arm.get('binary_sha256')
    if digest is None:
        digest = arm['runtime_files'][str(binary.resolve(strict=True))]['sha256']
    return {'kernel_commit': arm['kernel_commit'], 'kernel_tree': arm['kernel_tree'], 'binary_sha256': digest}


def prepare_profile_metadata(root, witness_path):
    parity = parity_module(root)
    witness = parity._parse(witness_path.read_bytes())
    output = {}
    for profile, (archive, recipe_key, model_key, template_key) in PROFILES.items():
        plan_path = root / 'data/vidya' / f'quality-pack-{archive}' / 'plan.json.original-bytes.json'
        plan, plan_pin = archived_plan(plan_path)
        if plan.get('profile', 'frontdoor-cpu-moe-mtp') != profile:
            raise ValueError(f'archive profile differs: {plan_path}')
        recipe = plan['recipes'][recipe_key]
        endpoint = recipe['endpoint']
        raw_completion = endpoint == '/completion'
        template_pin = plan[template_key]['sha256']
        runtime = {arm: runtime_pin(pin) for arm, pin in plan['arms'].items()}
        model = plan[model_key]
        weights = [value['sha256'] for value in model] if isinstance(model, list) else [model['sha256']]
        assets = {'weights': weights}
        for role in ('draft_model', 'mmproj'):
            if role in plan:
                assets[role] = plan[role]['sha256']
        fixture_witness = None
        if profile == 'architect-general-hip':
            if (witness['profile'] != profile or witness['source_plan_sha256'] != plan_pin
                    or witness['model_shard_sha256'] != weights
                    or any(runtime[arm]['kernel_commit'] != source['kernel_commit']
                           or runtime[arm]['kernel_tree'] != source['kernel_tree']
                           for arm, source in witness['runtime_source'].items())
                    or witness['runtime_source']['candidate']['loader_reshape_expected'] is not True):
                raise ValueError('loader witness differs from pinned HIP plan model/runtime')
            fixture_witness = hashlib.sha256(witness_path.read_bytes()).hexdigest()
        items = [prospective_item(item, profile, fixture_witness) for item in plan['items']]
        for item in items:
            parity._request(item['request_body'], endpoint)
            parity._semantic_matches(item['validator'], '')
        question_pool = [{'id': item['id'], 'request_body': item['request_body'],
                          'prompt_shape': item['prompt_shape'], 'output_format': item['output_format'],
                          'fixture': item['fixture']} for item in items]
        scoring = [{'id': item['id'], 'expected_finish': item['expected_finish'],
                    'validator': item['validator']} for item in items]
        sampling = [{'id': item['id'], 'parameters': {key: value for key, value in item['request_body'].items()
                                                    if key not in ('messages', 'prompt', 'model')}} for item in items]
        endpoint_semantics = {'endpoint': endpoint, 'raw_prompt': raw_completion, 'streams': False,
                              'model_output_token_ids_required': True, 'native_completion_count_required': True,
                              'mmproj_image_decode_required': 'mmproj' in assets}
        generation = {'recipe_sha256': parity._json_hash(recipe), 'endpoint': endpoint,
                      'model_assets': assets, 'template_applied_by_server': not raw_completion,
                      'loader_reshape_witness_sha256': fixture_witness}
        shape = {
            'id': profile, 'profile': profile, 'endpoint': endpoint,
            'model_sha256': weights[0] if len(assets) == 1 and len(weights) == 1 else parity._json_hash(assets),
            'recipe_sha256': parity._json_hash(recipe),
            'prompt_template_sha256': template_pin if not raw_completion else parity._json_hash({
                'server_template_applied': False, 'registered_template_sha256': template_pin}),
            'sampling_sha256': parity._json_hash(sampling),
            'scorer_sha256': parity._json_hash({'source_sha256': parity.VALIDATOR_SOURCE_SHA256, 'items': scoring}),
            'question_pool_sha256': parity._json_hash(question_pool),
            'endpoint_semantics_sha256': parity._json_hash(endpoint_semantics),
            'generation_path_sha256': parity._json_hash(generation),
        }
        if raw_completion:
            shape['validated_cap'] = plan['validated_cap']
        output[profile] = {
            'archived_plan': str(plan_path.relative_to(root)), 'archived_plan_sha256': plan_pin,
            'shape': shape, 'runtime': runtime, 'items': items, 'model_assets': assets,
            'recipe': recipe, 'endpoint_semantics': endpoint_semantics, 'generation': generation,
            'registered_template_sha256': template_pin,
            'scoring': scoring, 'sampling': sampling,
            'requires_fresh_production_capture': profile in (
                'architect-general-hip', 'worker-vision-hip-mmproj', 'dspark-dflash'),
        }
    parity._shapes([row['shape'] for row in output.values()])
    return {
        'schema': 'epyc.quality_pack_prospective_metadata.v1', 'profiles': output,
        'comparator_sha256': parity.VALIDATOR_SOURCE_SHA256,
        'scope': 'Prospective recipe and request declaration. Contains no production responses or candidate captures.',
        'capture_source_status': 'requires a committed production/candidate capture protocol before sealing',
    }


def audit_dflash(root, bank_directory):
    """Review the original production-only bytes against prompt-derived prospective semantics."""
    parity = parity_module(root)
    plan_path = root / 'data/vidya/quality-pack-dspark-dflash-20261118/successor-r3/plan.json.original-bytes.json'
    plan, plan_pin = archived_plan(plan_path)
    def original_bytes(name):
        envelope = parity._parse((bank_directory / (name + '.original-bytes.json')).read_bytes())
        data = base64.b64decode(envelope['bytes_b64'], validate=True)
        if parity._sha256(data) != envelope['sha256']:
            raise ValueError(f'original byte seal differs: {name}')
        return data

    raw = original_bytes('banked-capture.json')
    bank_pin = parity._sha256(raw)
    if bank_pin != original_bytes('banked-capture.sha256').decode().strip():
        raise ValueError('bank digest sidecar disagrees with raw bytes')
    bank = parity._parse(raw)
    if bank['capture_identity']['request_plan_sha256'] != plan_pin or bank['runtime'] != plan['arms']['production']:
        raise ValueError('DFlash bank does not bind to original plan and runtime')
    inventory = parity._named_rows(bank['items'], 'banked item')
    plan_items = parity._named_rows(plan['items'], 'DFlash plan item')
    if inventory.keys() != plan_items.keys():
        raise ValueError('DFlash bank item inventory differs from archived plan')
    checks = {}
    pairs = {}
    for name, item in plan_items.items():
        request = original_bytes(f'production/{name}.request.json')
        response = original_bytes(f'production/{name}.response.json')
        row = inventory[name]
        capture_fields = parity.CAPTURE_FIELDS | parity.DFLASH_FIELDS
        parity._fields(row, capture_fields | {'id', 'dflash_pair', 'draft_counters', 'request_custody_sha256'}, name)
        capture = {key: row[key] for key in capture_fields}
        custody = original_bytes(f'production/{name}.request-custody.json')
        if (row['dflash_pair'] != item['dflash_pair']
                or parity._sha256(custody) != row['request_custody_sha256']):
            raise ValueError(f'{name}: DFlash pair or custody record drifted')
        body = item['request_body']
        if request != parity.canonical_json(body) or response != base64.b64decode(capture['response_b64'], validate=True):
            raise ValueError(f'{name}: archived request/response bytes differ from original seal')
        _, limit = parity._request(body, '/completion')
        cap = body[parity.CAP_KEY]
        content, _, finish, tokens, count = parity._capture(capture, parity._sha256(request), '/completion', cap, limit)
        proposed = prospective_item(item, plan['profile'], None)
        validator = proposed['validator']
        semantic = parity._semantic_matches(validator, content)
        problems = []
        if finish != proposed['expected_finish']:
            problems.append('finish_mismatch')
        if not semantic:
            problems.append('semantic_validation_failed')
        if count is None or tokens is None:
            problems.append('missing_native_completion_count_or_token_ids')
        checks[name] = {
            'original_expected_finish': item.get('expected_finish'), 'original_validator': item.get('validator'),
            'observed_finish': finish, 'completion_count': count, 'token_id_count': None if tokens is None else len(tokens),
            'proposed_finish': proposed['expected_finish'], 'proposed_validator': validator,
            'proposed_validator_matches_original': semantic, 'problems_under_proposed_checks': problems,
            'request_sha256': parity._sha256(request), 'response_sha256': parity._sha256(response),
        }
        pairs.setdefault(item['dflash_pair'], []).append(parity._pair_row(proposed, capture, cap))
    parity._pair_check(pairs, 'production')
    return {'schema': 'epyc.quality_pack_dflash_original_admission_audit.v1', 'plan_sha256': plan_pin,
            'bank_sha256': bank_pin, 'candidate_read': False,
            'status': 'custody_slice_only_no_prospective_admission', 'items': checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('witness', type=Path)
    parser.add_argument('--audit-dflash-bank', type=Path)
    args = parser.parse_args()
    result = (audit_dflash(args.repo, args.audit_dflash_bank) if args.audit_dflash_bank
              else prepare_profile_metadata(args.repo, args.witness))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
