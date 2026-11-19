#!/usr/bin/env python3
"""Pin fresh DFlash requests against archived r3 capture and comparator metadata."""
import argparse
import base64
import copy
from pathlib import Path

import quality_parity as parity
from capture import D, PROFILE, canonical, file_sha, sha, write, write_json, validate_plan


def original_bytes(path):
    envelope = parity._parse(path.read_bytes())
    raw = base64.b64decode(envelope['bytes_b64'], validate=True)
    if sha(raw) != envelope['sha256']:
        raise ValueError(f'original-byte envelope differs: {path}')
    return raw


def prepare(repo):
    archive_root = repo / 'data/vidya'
    r3 = archive_root / 'quality-pack-dspark-dflash-20261118'
    metadata_root = archive_root / 'quality-pack-profile-metadata-20261118'
    plan_raw = original_bytes(r3 / 'successor-r3/plan.json.original-bytes.json')
    plan = parity._parse(plan_raw)
    receipt_path = r3 / 'full-capture-r3/receipt.json'
    receipt = parity._parse(receipt_path.read_bytes())
    audit_raw = original_bytes(metadata_root / 'dflash-original-admission.json.original-bytes.json')
    audit = parity._parse(audit_raw)
    metadata_raw = original_bytes(metadata_root / 'prospective-metadata.json.original-bytes.json')
    metadata = parity._parse(metadata_raw)
    prior = metadata['profiles'][PROFILE]
    if (plan['profile'] != PROFILE or receipt['rc'] != 0 or receipt['verdict'] != 'pass'
            or receipt['capture_identity']['request_plan_sha256'] != sha(plan_raw)
            or prior['archived_plan_sha256'] != sha(plan_raw) or audit['plan_sha256'] != sha(plan_raw)
            or audit['bank_sha256'] != receipt['bank_sha256'] or audit['candidate_read'] is not False
            or metadata['comparator_sha256'] != parity.VALIDATOR_SOURCE_SHA256):
        raise ValueError('original r3 plan, custody receipt or comparator source differs')
    write(D / 'dflash-original-admission.json', audit_raw)
    write(D / 'r3-owner-receipt.json', receipt_path.read_bytes())
    plan['prior_dflash'] = {
        'row': receipt['row'], 'plan_sha256': sha(plan_raw), 'native_bank_sha256': audit['bank_sha256'],
        'admission_sha256': sha(audit_raw), 'filing_sha256': file_sha(receipt_path),
        'scoring_sha256': prior['shape']['scorer_sha256'], 'prospective_metadata_sha256': sha(metadata_raw),
        'disposition': 'custody_only_no_prospective_admission',
    }
    for witness in (plan['smoke_model'], plan['model_hash_witness'], plan['prior_frontdoor_json_mismatch']):
        target = D / Path(witness['snapshot']).name
        raw = Path(witness['snapshot']).read_bytes()
        if sha(raw) != witness['receipt_sha256']:
            raise ValueError(f'original r3 witness changed: {target.name}')
        write(target, raw)
        witness['snapshot'] = str(target)
    for witness in plan['source_witnesses']:
        path = Path(witness['path'])
        if path.name != 'cpu-feasibility.json':
            continue
        raw = path.read_bytes()
        if sha(raw) != witness['sha256']:
            raise ValueError('original feasibility witness changed')
        target = D / path.name
        write(target, raw)
        witness['path'] = str(target)

    original = parity._named_rows(plan['items'], 'r3 plan items')
    plan['items'] = copy.deepcopy(prior['items'])
    for item in plan['items']:
        name = item['id']
        body = item['request_body']
        old = original[name]
        original_check = audit['items'][name]
        if (body != old['request_body'] or item['dflash_pair'] != old['dflash_pair']
                or item['expected_finish'] != original_check['proposed_finish']
                or item['validator'] != original_check['proposed_validator']):
            raise ValueError(f'{name}: archived metadata drift')
        if item['output_format'] == 'json':
            body['prompt'] = (
                'Return a single compact JSON object on one line. Use exactly these keys and types: '
                'status is the string "ready"; count is the integer 2; labels is an ordered array '
                'of two strings, "alpha" followed by "beta". Write the raw object followed by a '
                'newline. Omit markdown fences, headings, and commentary.\nThe JSON object is:\n'
            )
            body['stop'] = ['\n']
        elif item['output_format'] == 'reasoning':
            context, marker, _ = body['prompt'].partition('\nReason step by step')
            if not marker:
                raise ValueError('original long reasoning context missing')
            body['prompt'] = (
                context + '\nGive the conclusion before the explanation. In one sentence, state by '
                'how many minutes the second route is faster and whether final displacement changes. '
                'Then explain the elapsed-time arithmetic and the equal net displacement.\n'
                'The second route is'
            )
    production = plan['arms']['production']
    plan['arms'] = {'production': production}
    plan['smoke_runtime'] = production
    plan['schema'] = 'epyc.quality_pack_dflash_bank_plan.v1'
    plan['scope'] = (
        'Prospective isolated v10 CPU DFlash2 production admission. The registered template is '
        'recorded as provenance; native /completion uses raw prompts. Historical DeepSeek 0731 '
        'DSpark remains retired. Candidate collection requires the sealed seven-profile pack.'
    )
    plan['question_pool_sha256'] = sha(canonical(plan['items']))
    plan['validator_source_sha256'] = parity.VALIDATOR_SOURCE_SHA256
    plan['shape'] = prior['shape'].copy()
    pool = [{key: item[key] for key in ('id', 'request_body', 'prompt_shape', 'output_format', 'fixture')}
            for item in plan['items']]
    sampling = [{'id': item['id'], 'parameters': {
        key: value for key, value in item['request_body'].items() if key not in ('messages', 'prompt', 'model')
    }} for item in plan['items']]
    plan['shape']['question_pool_sha256'] = parity._json_hash(pool)
    plan['shape']['sampling_sha256'] = parity._json_hash(sampling)

    (D / 'requests').mkdir()
    plan['request_files'] = {}
    for item in plan['items'] + plan['smoke_items']:
        rel = f"requests/{item['id']}.json"
        wire = canonical(item['request_body'])
        write(D / rel, wire)
        plan['request_files'][item['id']] = {'path': rel, 'sha256': sha(wire)}
    validate_plan(plan)
    write_json(D / 'plan.json', plan)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('repo', type=Path)
    prepare(parser.parse_args().repo.resolve())
