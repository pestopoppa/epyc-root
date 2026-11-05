#!/usr/bin/env python3
"""Recount the retained matched census; never turn unsupported into a pass."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

EXPECTED = 'f7b7c095394c2b10987f4cc49e8746ec614777ba30d5688ced64af02093ac48f'

def params(value):
    # Extract scalar fields only: dimensions such as bs=[2,3] contain commas.
    fields = {}
    for part in value.split(','):
        if '=' in part:
            key, val = part.split('=', 1)
            fields[key] = val
    return fields

def classify(data):
    if data.get('status') != 'COMPLETE' or data.get('mode') != 'grant':
        raise ValueError('census is not a complete granted capture')
    summary = {}
    for op in ('MUL_MAT', 'FLASH_ATTN_EXT'):
        rows = [r for r in data['rows'] if r['op'] == op]
        if len(rows) != 2 or {r['arm'] for r in rows} != {'baseline', 'corrected'}:
            raise ValueError('expected one matched row per arm')
        images = {}
        for r in rows:
            identities = Counter((c['op'], c['params']) for c in r['cases'])
            counts = Counter(c['status'] for c in r['cases'])
            if sum(counts.values()) != r['case_count'] or not r['cleanup']:
                raise ValueError('incomplete cases or child cleanup')
            images[r['arm']] = (identities, counts, r)
        if images['baseline'][0] != images['corrected'][0]:
            raise ValueError('case identities differ')
        transitions = []
        for key in sorted(images['corrected'][0]):
            statuses = []
            for arm in ('baseline', 'corrected'):
                statuses.append(Counter(c['status'] for c in images[arm][2]['cases'] if (c['op'], c['params']) == key))
            if statuses[0] != statuses[1]:
                transitions.append({'op': key[0], 'params': key[1], 'baseline': dict(statuses[0]), 'corrected': dict(statuses[1])})
        unsupported = [params(c['params']) for c in images['corrected'][2]['cases'] if c['status'] == 'not_supported']
        entry = {'cases': len(images['corrected'][2]['cases']), 'identities': len(images['corrected'][0]),
                 'baseline_statuses': dict(sorted(images['baseline'][1].items())),
                 'corrected_statuses': dict(sorted(images['corrected'][1].items())), 'changed_status_distributions': transitions}
        if op == 'MUL_MAT':
            entry['unsupported_types'] = dict(sorted(Counter(f"{p['type_a']}/{p['type_b']}" for p in unsupported).items()))
            entry['rhs_f16_non_f16_lhs'] = sum(p['type_b'] == 'f16' and p['type_a'] != 'f16' for p in unsupported)
        else:
            entry['unsupported_k_types'] = dict(sorted(Counter(p['type_K'] for p in unsupported).items()))
            entry['unsupported_head_pairs'] = dict(sorted(Counter(f"{p['hsk']}/{p['hsv']}" for p in unsupported).items()))
            entry['unsupported_kv_types_when_all_quants_off'] = sum(p['type_K'] in {'q4_1', 'q5_0', 'q5_1', 'iq4_nl'} or p['type_V'] in {'q4_1', 'q5_0', 'q5_1', 'iq4_nl'} for p in unsupported)
        summary[op] = entry
    return summary

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    args = parser.parse_args()
    raw = args.result.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED:
        raise SystemExit(f'refusing unexpected census SHA-256: {digest}')
    print(json.dumps(classify(json.loads(raw)), indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
