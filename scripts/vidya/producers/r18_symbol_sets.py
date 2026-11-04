#!/usr/bin/env python3
"""Capture prospective R18 comparison sets; never changes the comparator verdict.

Invoke during the producer's full-run finalization with its exact comparator, libraries,
output and return code. Failure produces no output directory. Existing runs must not be
replayed through this hook to manufacture producer-time evidence.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def capture(comparator, result, rc, anchor_cpu, candidate_cpu, anchor_hip, candidate_hip, out):
    comparator, result, out = map(Path, (comparator, result, out))
    paths = [Path(p) for p in (anchor_cpu, candidate_cpu, anchor_hip, candidate_hip)]
    if rc not in (0, 1) or out.exists():
        raise ValueError('requires complete comparator return code and new output directory')
    comparator_sha, result_sha = sha(comparator), sha(result)
    native = json.loads(result.read_text())
    if native.get('schema') != 'r18a.independent_symbol_identity.v1' or 'error' in native:
        raise ValueError('comparator result is incomplete')
    spec = importlib.util.spec_from_file_location('r18_unchanged_comparator', comparator)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = [sha(p) for p in paths]
    ac, cc, ah, ch = paths
    sets = {
        'cpu': (module.symbols(ac, 'anchor/cpu'), module.symbols(cc, 'candidate/cpu')),
        'hip_host': (module.symbols(ah, 'anchor/hip_host'), module.symbols(ch, 'candidate/hip_host')),
    }
    ad, an = module.device_symbols(ah, 'anchor')
    cd, cn = module.device_symbols(ch, 'candidate')
    sets['hip_device'] = (ad, cd)
    rows = native.get('comparisons', {})
    if (set(rows) != set(sets) or before != [sha(p) for p in paths]
            or sha(comparator) != comparator_sha or sha(result) != result_sha):
        raise ValueError('comparison surfaces or input hashes changed')
    for kind, (anchor, candidate) in sets.items():
        row = rows[kind]
        if (row.get('anchor_count') != len(anchor) or row.get('candidate_count') != len(candidate)
                or row.get('added') != sorted(candidate - anchor)
                or row.get('removed') != sorted(anchor - candidate)):
            raise ValueError(f'{kind} sets disagree with native comparator')
    for kind, offset in (('cpu', 0), ('hip_host', 2)):
        if (rows[kind].get('anchor_sha256') != before[offset]
                or rows[kind].get('candidate_sha256') != before[offset + 1]):
            raise ValueError(f'{kind} library identity differs')
    if rows['hip_device'].get('anchor_code_objects') != an or rows['hip_device'].get('candidate_code_objects') != cn:
        raise ValueError('device object count differs')
    verdict = all(not row['added'] and not row['removed'] for row in rows.values())
    if native.get('symbol_identity_pass') is not verdict or rc != (0 if verdict else 1):
        raise ValueError('native verdict and return code disagree')
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='.r18-symbol-sets-', dir=out.parent))
    try:
        artifacts = {}
        for kind, pair in sets.items():
            for role, values in zip(('anchor', 'candidate'), pair):
                path = tmp / f'{kind}-{role}.json'
                path.write_text(json.dumps(sorted(values), ensure_ascii=True, separators=(',', ':')) + '\n')
                artifacts[path.name] = sha(path)
        manifest = {'schema': 'r18a.symbol_sets.v1', 'comparator': str(comparator.resolve()),
                    'comparator_sha256': comparator_sha, 'native_result': str(result.resolve()),
                    'native_result_sha256': result_sha, 'native_rc': rc,
                    'inputs': [{'path': str(p.resolve()), 'sha256': d} for p, d in zip(paths, before)],
                    'artifacts_sha256': artifacts}
        (tmp / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
        os.rename(tmp, out)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)
    return manifest


def main():
    p = argparse.ArgumentParser()
    for key in ('comparator', 'result', 'anchor-cpu', 'candidate-cpu', 'anchor-hip', 'candidate-hip', 'out'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--rc', type=int, required=True)
    a = p.parse_args()
    capture(a.comparator, a.result, a.rc, a.anchor_cpu, a.candidate_cpu, a.anchor_hip, a.candidate_hip, a.out)


if __name__ == '__main__':
    main()
