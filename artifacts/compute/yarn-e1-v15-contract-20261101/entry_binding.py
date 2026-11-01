#!/usr/bin/env python3
"""Offline content-binding verifier for a proposed E1-MEM v15 packet.

A passing check is not authority to launch: lifecycle, booking, resource and
same-entry native tests remain necessary. This module neither invokes a job nor
writes a READY row.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

STEPS = [["E1", "A0", "low"], ["W", "A0", "low"], ["E1", "A1", "low"],
         ["W", "A1", "low"], ["E1", "A1", "high"], ["W", "A1", "high"]]

class BindingError(ValueError):
    pass

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def require(test, message):
    if not test:
        raise BindingError(message)

def pinned(entry, expected_path=None):
    require(isinstance(entry, dict), 'pin missing')
    path = Path(entry.get('path', ''))
    require(path.is_file(), f'missing file: {path}')
    if expected_path is not None:
        require(path.resolve() == Path(expected_path).resolve(), f'wrong path: {path}')
    require(entry.get('sha256') == digest(path), f'digest mismatch: {path}')
    return path

def validate(root, row_id, expected_request_sha, approved_builds):
    root = Path(root).resolve()
    request_path = root/'qualification/request_manifest.json'
    require(request_path.is_file(), 'request absent')
    require(digest(request_path) == expected_request_sha, 'request digest mismatch')
    request = json.loads(request_path.read_text())
    require(request.get('schema') == 'epyc.yarn-e1-request-manifest.v1', 'request schema')
    require(request.get('id') == row_id and row_id != 'codex-ni-yarn-e1-mem-phase-r2-20261101', 'wrong or retired row ID')
    require(request.get('science_cells') == STEPS and request.get('science_cells_mutated') is False, 'science cells altered')
    pinned(request.get('runner'), root/'yarn_needle.py')
    require((root/'yarn_proof.py').is_file(), 'proof helper absent')
    # The helper must be independently covered by the source seal, not inferred
    # from the runner's hash. Seal semantics are raw sha256sum path records.
    source_path = root/'SOURCE.sha256'
    records = {}
    for line in source_path.read_text().splitlines():
        value, name = line.split('  ', 1)
        require(name not in records, f'duplicate source pin: {name}')
        records[name] = value
    for file in (root/'yarn_needle.py', root/'yarn_proof.py', root/'run.py', root/'launch.sh',
                 root/'qualification/qual_fixture.json'):
        key = str(file.resolve())
        require(key in records and records[key] == digest(file), f'source seal mismatch: {key}')
    pinned(request.get('input_manifest'))
    recipe_path = pinned(request.get('production_recipe'), root/'qualification/production_recipe.json')
    recipe = json.loads(recipe_path.read_text())
    require(recipe.get('schema') == 'epyc.yarn-e1-production-recipe.v1', 'recipe schema')
    require(set(recipe.get('images', {})) == {'E1', 'W'}, 'missing images')
    for name, commit in [('E1', '9a3f1392a'), ('W', 'b0ba1d427')]:
        image = recipe['images'][name]
        require(image.get('source_commit') == commit, f'{name} commit mismatch')
        # The caller must supply independently accepted manifest and version
        # digests; recipe-provided source labels cannot attest their own build.
        approved = approved_builds.get(name, {})
        require(approved.get('source_commit') == commit, f'{name} no approved build binding')
        manifest = pinned(approved.get('manifest'))
        version = pinned(approved.get('version'))
        require(commit in version.read_text(), f'{name} version lacks commit')
        contents = {}
        for line in manifest.read_text().splitlines():
            value, filename = line.split(None, 1)
            filename = filename.strip().lstrip('*')
            require(filename not in contents, f'{name} duplicate build entry')
            contents[filename] = value
        binary = pinned(image.get('binary'))
        require(contents.get('./'+binary.name) == digest(binary), f'{name} binary not bound by build manifest')
        dsos = image.get('ggml_dsos', [])
        require(len(dsos) == 4 and len({str(Path(d.get('path', '')).resolve()) for d in dsos}) == 4,
                f'{name} missing or duplicate ggml DSOs')
        for dso in dsos:
            file = pinned(dso)
            require(contents.get('./'+file.name) == digest(file), f'{name} DSO not bound by build manifest')
    pinned(recipe.get('template'))
    backend = recipe.get('backend', {})
    pinned({'path': backend.get('shim', ''), 'sha256': backend.get('shim_sha256')}, root/'helper/libhipmalloc_trace.so')
    fixture_path = root/'qualification/qual_fixture.json'
    fixture = json.loads(fixture_path.read_text())
    require(fixture.get('schema') == 'epyc.yarn-e1-qual-fixture.v1', 'fixture schema')
    require(fixture.get('science_cells') == STEPS, 'fixture cells changed')
    freq = fixture.get('request', {})
    require(freq.get('request_manifest_sha256') == expected_request_sha, 'fixture request pin mismatch')
    require(freq.get('production_recipe_sha256') == digest(recipe_path), 'fixture recipe pin mismatch')
    q = request.get('request_max', {})
    for key in ('needle', 'messages_sha256', 'rendered_sha256', 'prompt_tokens_required'):
        require(q.get(key) == freq.get(key), f'fixture {key} mismatch')
    return {'status': 'PASS_OFFLINE_BINDINGS_ONLY', 'row_id': row_id,
            'request_sha256': expected_request_sha, 'recipe_sha256': digest(recipe_path)}
