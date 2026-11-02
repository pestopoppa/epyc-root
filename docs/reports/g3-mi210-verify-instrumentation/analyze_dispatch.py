#!/usr/bin/env python3
"""Classify explicitly correlated G3 diagnostic records; not a run validator.

Input records are a proposed interchange contract, not evidence that an
instrumented binary exists. Caller independently proves source/binary identity,
HIP residency and complete backend event delivery. Unknown is never a no-VEC.
"""
from collections import Counter


def classify(records, *, expected_attention_layers):
    if type(expected_attention_layers) is not int or expected_attention_layers <= 0:
        raise ValueError('positive expected layer count required')
    if not isinstance(records, list):
        raise ValueError('record list required')
    calls = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('invalid record')
        kind, ident = record.get('kind'), record.get('invocation')
        if not isinstance(ident, str) or not ident:
            raise ValueError('missing invocation identity')
        if kind == 'begin':
            if ident in calls:
                raise ValueError('duplicate invocation')
            calls[ident] = {'begin': record, 'dispatch': [], 'ended': False}
        elif kind == 'dispatch':
            if ident not in calls or calls[ident]['ended']:
                raise ValueError('unmatched or late dispatch')
            calls[ident]['dispatch'].append(record)
        elif kind == 'end':
            if ident not in calls or calls[ident]['ended']:
                raise ValueError('unmatched or duplicate end')
            calls[ident]['ended'] = True
            calls[ident]['end'] = record
        else:
            raise ValueError('unknown record kind')
    verified, unknown = [], []
    for ident, call in calls.items():
        b = call['begin']
        length, tokens, indices = b.get('draft_length'), b.get('view_tokens'), b.get('spec_indices')
        rc = call.get('end', {}).get('rc')
        valid = (call['ended'] and type(rc) is int and rc == 0 and
                 b.get('mode') == 'parallel' and type(length) is int and length > 0 and
                 type(tokens) is int and tokens == length + 1 and isinstance(indices, list) and
                 len(indices) == tokens and all(type(i) is int for i in indices) and
                 sorted(indices) == list(range(tokens)))
        events = call['dispatch']
        layers = [e.get('layer') for e in events]
        valid = (valid and len(events) == expected_attention_layers and
                 all(type(x) is int and x >= 0 for x in layers) and
                 len(set(layers)) == expected_attention_layers and
                 all(e.get('kernel') in ('VEC', 'TILE', 'MMA_F16', 'WMMA_F16') and
                     type(e.get('q_len')) is int and e['q_len'] > 0 and
                     e.get('kv_type') in ('Q8_0', 'Q4_0') for e in events))
        if not valid:
            unknown.append(ident)
            continue
        counts = Counter(e['kernel'] for e in events)
        verified.append({'invocation': ident, 'draft_length': length,
                         'dispatch_counts': dict(counts),
                         'q_lengths': sorted({e['q_len'] for e in events}),
                         'kv_types': sorted({e['kv_type'] for e in events}),
                         'vec_observed': counts['VEC'] > 0})
    return {'verify_calls': verified, 'unknown_invocations': unknown,
            'limitations': ['source and loaded binary identity unverified',
                            'HIP residency and complete delivery unverified',
                            'kernel selection does not establish bandwidth or performance']}
