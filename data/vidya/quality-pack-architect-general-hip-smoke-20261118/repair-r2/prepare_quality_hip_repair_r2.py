#!/usr/bin/env python3
"""Seal an isolated HIP repair from the digest-pinned predecessor packet."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity(path):
    st = path.stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def repin(pin, path=None):
    original_path = Path(pin['path'])
    path = original_path if path is None else path
    if path.resolve(strict=True) != path:
        raise ValueError(f'expected a canonical file path: {path}')
    before = identity(path)
    if path != original_path or before != pin['stat']:
        if digest(path) != pin['sha256'] or before != identity(path):
            raise ValueError(f'prepared content differs: {path}')
        change = {'old': dict(pin), 'new': {**pin, 'path': str(path), 'stat': before}}
        pin.update(change['new'])
        return change
    return None


def write_json(path, document):
    path.write_text(json.dumps(document, sort_keys=True, indent=2) + '\n')


def prepare(source, failed_smoke):
    plan_path = source / 'plan.json'
    plan = json.loads(plan_path.read_bytes())
    spec = json.loads((source / 'row.spec.json').read_bytes())
    manifest = {}
    for line in (source / 'SOURCE.sha256').read_text().splitlines():
        sha, name = line.split('  ', 1)
        manifest[name] = sha
        if digest(source / name) != sha:
            raise ValueError(f'predecessor packet file differs: {name}')

    dest = Path(tempfile.mkdtemp(prefix=source.name + '-repair-r2.', dir=source.parent))
    names = sorted(manifest.keys() - {'make_plan.py'})
    for name in names:
        path = dest / name
        path.parent.mkdir(exist_ok=True, parents=True)
        shutil.copyfile(source / name, path)
    if json.loads(failed_smoke.read_bytes())['id'] != spec['id']:
        raise ValueError('failure receipt does not name the repaired row')

    changes = []
    for runtime in plan['arms'].values():
        pins = [*runtime['build_witnesses'], *runtime['runtime_files'].values(), *runtime['rocm_files'].values()]
        if 'mtmd_library' in runtime:
            pins.append(runtime['mtmd_library'])
        for pin in pins:
            change = repin(pin)
            if change:
                changes.append(change)
    if 'smoke_runtime' in plan:
        plan['smoke_runtime'] = plan['arms']['production']
    for witness in (plan.get('model_hash_witness') or plan['profile_provenance']['model_hash_witness'],
                    plan['prior_frontdoor_json_mismatch']):
        original = Path(witness['snapshot'])
        witness['snapshot'] = str(dest / original.name)
    plan['smoke_model']['receipt_snapshot'] = str(dest / Path(plan['smoke_model']['receipt_snapshot']).name)

    old_template = plan['template']['path']
    changes.append(repin(plan['template'], dest / 'chat-template.jinja'))
    full_args = plan['recipes']['hip_slice']['args']
    template_index = full_args.index('--chat-template-file') + 1
    if full_args[template_index] != old_template:
        raise ValueError('full recipe template path differs from the prepared pin')
    full_args[template_index] = plan['template']['path']

    for recipe in plan['recipes'].values():
        if any(arg in ('-v', '--verbose', '--log-verbose', '-lv', '--verbosity', '--log-verbosity')
               for arg in recipe['args']):
            raise ValueError('predecessor recipe already set server verbosity')
        recipe['args'] += ['--verbosity', '4']

    for key in ('launcher', 'scratch_root', 'result_path', 'smoke_predicate'):
        if str(source) not in spec[key]:
            raise ValueError(f'expected predecessor path in {key}')
        spec[key] = spec[key].replace(str(source), str(dest), 1)
    launcher = (dest / 'row-launch.sh').read_text()
    if str(source) not in launcher:
        raise ValueError('expected predecessor path in row launcher')
    (dest / 'row-launch.sh').write_text(launcher.replace(str(source), str(dest), 1))
    (dest / 'row-launch.sh').chmod(0o755)

    write_json(dest / 'plan.json', plan)
    write_json(dest / 'row.spec.json', spec)
    write_json(dest / 'repair-receipt.json', {
        'schema': 'epyc.quality_hip_smoke_repair.v1',
        'row_id': spec['id'],
        'predecessor_source_manifest_sha256': digest(source / 'SOURCE.sha256'),
        'predecessor_plan_sha256': digest(plan_path),
        'failed_smoke_sha256': digest(failed_smoke),
        'fresh_identity_pins': changes,
        'server_verbosity': 4,
        'recipe_path_delta': {'old_template': old_template, 'new_template': plan['template']['path']},
        'request_sha256': {name: pin['sha256'] for name, pin in plan['request_files'].items()},
    })
    names.append('repair-receipt.json')
    (dest / 'SOURCE.sha256').write_text(''.join(f'{digest(dest / name)}  {name}\n' for name in sorted(names)))
    return dest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('failed_smoke', type=Path)
    args = parser.parse_args()
    print(prepare(args.source.resolve(strict=True), args.failed_smoke))
