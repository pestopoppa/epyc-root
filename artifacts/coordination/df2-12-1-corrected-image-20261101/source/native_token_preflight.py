#!/usr/bin/env python3
"""Source-bound target-server template/tokenizer check before completion issuance."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib

from df2_parity import render, token_count

ROOT = pathlib.Path(__file__).resolve().parent
MANIFEST_SHA = 'de3096605c354c6346418267ad09efc5cbf6eb7599816301a940e3b93cb8e0e1'


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def candidates(manifest):
    return ([('salt-' + key, text) for key, text in manifest['prompts'].items()] +
            [('reuse_a', manifest['reuse_a']), ('reuse_b', manifest['reuse_b'])] +
            [('low_entropy-' + str(i), text) for i, text in enumerate(manifest['low_entropy'])] +
            [('planted-' + str(i), text) for i, text in enumerate(manifest['planted'])])


def capture(base_url, manifest_path, role, output_dir, image_proof, production_recipe):
    if role not in ('frontdoor_mtp', 'architect_dflash'):
        raise RuntimeError('unknown DF2 role')
    out = pathlib.Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)
    manifest_path = pathlib.Path(manifest_path)
    metadata = ROOT / 'metadata' / role
    metadata_result = metadata / 'RESULT.json'
    metadata_raw = metadata / 'stdout.jsonl'
    intent = {'schema':'epyc.df2_12_1.native_token_preflight.v1',
              'scope':'ACCEPTED_IMAGE_SERVER_API_READ_ONLY_BEFORE_COMPLETION',
              'role':role, 'base_url':base_url, 'manifest_path':str(manifest_path),
              'manifest_sha256':sha(manifest_path), 'image_proof_path':str(image_proof),
              'image_proof_sha256':sha(image_proof),
              'production_recipe_path':str(production_recipe),
              'production_recipe_sha256':sha(production_recipe),
              'metadata_result_sha256':sha(metadata_result),
              'metadata_raw_sha256':sha(metadata_raw),
              'utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    write(out / 'INTENT.json', intent)
    if intent['manifest_sha256'] != MANIFEST_SHA:
        write(out / 'DISPOSITION.json', {'status':'REFUSED_MANIFEST_DRIFT'})
        raise RuntimeError('frozen request manifest changed')
    manifest = json.loads(manifest_path.read_text())
    expected = candidates(manifest)
    metadata_rows = [json.loads(line) for line in metadata_raw.read_text().splitlines()]
    if [row['id'] for row in metadata_rows] != [name for name, _ in expected]:
        write(out / 'DISPOSITION.json', {'status':'REFUSED_METADATA_IDENTITY_DRIFT'})
        raise RuntimeError('metadata row identity differs from frozen manifest')
    rows = []
    try:
        for name, prompt in expected:
            rendered = render(base_url, prompt, out / 'wire' / (name + '.apply-template'))
            tokens = token_count(base_url, rendered, out / 'wire' / (name + '.tokenize'))
            rows.append({'id':name,'rendered':rendered,'tokens':tokens,'count':len(tokens)})
    except BaseException as exc:
        write(out / 'DISPOSITION.json', {'status':'FAILED_OR_UNKNOWN_API_PREFLIGHT',
              'completed_ids':[row['id'] for row in rows], 'error':repr(exc)})
        raise
    raw = out / 'NATIVE-ROWS.jsonl'
    raw.write_text(''.join(json.dumps(row, sort_keys=True, separators=(',',':'))+'\n' for row in rows))
    equal = len({row['count'] for row in rows if row['id'].startswith('salt-')}) == 1
    same = rows == metadata_rows
    counts = {row['id']:row['count'] for row in rows}
    maximum = max(counts.values())
    result = {'schema':'epyc.df2_12_1.native_token_preflight.v1',
              'scope':'ACCEPTED_IMAGE_SERVER_API_READ_ONLY_BEFORE_COMPLETION',
              'role':role, 'manifest_sha256':intent['manifest_sha256'],
              'image_proof_sha256':intent['image_proof_sha256'],
              'production_recipe_sha256':intent['production_recipe_sha256'],
              'metadata_result_sha256':intent['metadata_result_sha256'],
              'metadata_raw_sha256':intent['metadata_raw_sha256'],
              'native_rows_sha256':sha(raw), 'counts':counts,
              'salt_equal_length':equal, 'max_count':maximum,
              'max_ids':[name for name,count in counts.items() if count == maximum],
              'metadata_match':same, 'endpoint_observed':True,
              'utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    write(out / 'PREFLIGHT.json', result)
    write(out / 'DISPOSITION.json', {'status':'ACCEPTED_NATIVE_API_PREFLIGHT' if same and equal else
          'MISMATCH_REVIEW_REQUIRED', 'result_sha256':sha(out / 'PREFLIGHT.json')})
    if not same or not equal:
        raise RuntimeError('accepted-image target API differs from frozen metadata/token equality')
    return rows, result
