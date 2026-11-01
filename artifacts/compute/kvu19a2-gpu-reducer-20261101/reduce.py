#!/usr/bin/env python3
"""Offline reducer for a prospective KVU-19a-2 native evidence bundle.

This is not a launcher or a substitute for capture/attestation. Paths are relative
to the evidence root; one complete, predeclared 10-launch sequence per case is required.
"""
import argparse
import hashlib
import json
from pathlib import Path

ORDER = 'ABBAABBAAB'
CASES = (78, 79, 80)
INPUTS = ('q', 'k', 'v', 'mask')


def read_file(root, name):
    if not isinstance(name, str) or not name:
        raise ValueError('missing file path')
    path = (root / name).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('path escapes evidence root or is not a file')
    return path.read_bytes()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reduce_case(root, rows):
    if len(rows) != 10 or ''.join(str(x.get('arm', '')) for x in rows) != ORDER:
        raise ValueError('expected exact ABBAABBAAB sequence')
    # Native capture must set these only after observing each condition.
    required = ('normal_exit', 'input_capture_complete', 'output_capture_complete',
                'live_vram_and_kfd', 'device_gfx90a', 'mapping_verified', 'cleanup_verified')
    inputs = None
    identity = {}
    outputs = {'A': [], 'B': []}
    nonfinite = {'A': [], 'B': []}
    for row in rows:
        if any(row.get(k) is not True for k in required):
            raise ValueError('missing native completion or custody evidence')
        arm = row['arm']
        ids = tuple(row.get(k) for k in ('executable_sha256', 'mapped_libraries_sha256', 'source_tree_sha256'))
        if any(not isinstance(x, str) or len(x) != 64 or any(c not in '0123456789abcdef' for c in x) for x in ids):
            raise ValueError('missing or malformed binary/source identity')
        if arm in identity and identity[arm] != ids:
            raise ValueError('identity changed within arm')
        identity[arm] = ids
        captured = tuple(read_file(root, row.get('inputs', {}).get(k)) for k in INPUTS)
        if inputs is None:
            inputs = captured
        elif inputs != captured:
            raise ValueError('input bytes differ')
        output = read_file(root, row.get('output'))
        if not output or row.get('output_bytes') != len(output):
            raise ValueError('missing or truncated output')
        if not isinstance(row.get('nonfinite_count'), int) or isinstance(row.get('nonfinite_count'), bool) or row['nonfinite_count'] < 0:
            raise ValueError('nonfinite count missing')
        outputs[arm].append(output)
        nonfinite[arm].append(row['nonfinite_count'])
    return {'status': 'complete', 'input_sha256': {k: digest(v) for k, v in zip(INPUTS, inputs)},
            'arms': {arm: {'verdict': 'NO-DIFFERENCE-OBSERVED' if len(set(outputs[arm])) == 1 else 'OBSERVED-NONDETERMINISM',
                           'n': len(outputs[arm]), 'output_sha256': [digest(x) for x in outputs[arm]],
                           'nonfinite_count': nonfinite[arm], 'identity': identity[arm]} for arm in ('A', 'B')},
            'cross_binary_equal_all': len(set(outputs['A'] + outputs['B'])) == 1}


def reduce(root, manifest):
    root = root.resolve(strict=True)
    result = {}
    for case in CASES:
        rows = [x for x in manifest.get('runs', []) if x.get('case') == case]
        try:
            result[str(case)] = reduce_case(root, rows)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            result[str(case)] = {'status': 'incomplete', 'reason': str(exc)}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    print(json.dumps(reduce(args.root, manifest), indent=2))


if __name__ == '__main__':
    main()
