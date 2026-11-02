#!/usr/bin/env python3
"""Classify native V3 target records; not a binary, HIP or delivery validator."""
import re
from invocation_trace_v2 import (parse_invocation_trace_v2, _fields, _int, _MARKER,
                                 _BEGIN, _END, _DISPATCH, MAX_TRACE_BYTES, MAX_TRACE_LINES)


def classify_invocation_trace_v3(text, *, expected_layer_ids):
    if (not isinstance(expected_layer_ids, (list, tuple)) or not expected_layer_ids
            or any(type(i) is not int or i < 0 for i in expected_layer_ids)
            or len(set(expected_layer_ids)) != len(expected_layer_ids)):
        raise ValueError('unique expected layer IDs required')
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_TRACE_BYTES or len(text.splitlines()) > MAX_TRACE_LINES:
        raise ValueError('invalid or oversized trace')
    rewritten, indices, layer_events, raw_events = [], {}, [], []
    for line in text.splitlines():
        marker = _MARKER.search(line)
        if not marker:
            rewritten.append(line)
            continue
        kind = marker.group(1)
        required = {'G3_TARGET_BEGIN_V3': _BEGIN | {'indices'}, 'G3_TARGET_END_V3': _END,
                    'G3_FATTN_DISPATCH_V3': _DISPATCH | {'layer'}}.get(kind)
        if required is None:
            raise ValueError('unsupported trace marker')
        fields = _fields(line[marker.end():].strip(), required)
        raw_events.append({'kind': kind, 'fields': dict(fields)})
        if kind == 'G3_TARGET_BEGIN_V3':
            raw = fields.pop('indices')
            if raw == 'none':
                parsed = []
            elif re.fullmatch(r'[0-9]+(?:,[0-9]+)*', raw):
                parsed = [int(i) for i in raw.split(',')]
            else:
                raise ValueError('invalid indices')
            indices[int(fields['invocation'])] = parsed
        elif kind == 'G3_FATTN_DISPATCH_V3':
            layer_events.append(_int(fields.pop('layer')))
        rewritten.append(kind.replace('_V3', '_V2') + ' ' + ' '.join(f'{k}={v}' for k, v in fields.items()))
    parsed = parse_invocation_trace_v2('\n'.join(rewritten))
    dispatch_iter = iter(layer_events)
    # Preserve event ordering, including worker-thread events, while attaching layers.
    by_call = {c['invocation']: c for c in parsed['calls']}
    positions = {c['invocation']: 0 for c in parsed['calls']}
    for event in raw_events:
        if event['kind'] != 'G3_FATTN_DISPATCH_V3':
            continue
        layer = next(dispatch_iter)
        f = event['fields']
        if f['correlation'] == 'host_scope':
            ident = int(f['invocation'])
            pos = positions[ident]
            by_call[ident]['dispatches'][pos]['layer'] = layer
            positions[ident] += 1
    candidates, controls = [], []
    for call in parsed['calls']:
        if call['class'] != 'parallel_verify_candidate':
            controls.append(call)
            continue
        reasons = []
        if call['status'] != 'CORRELATED_CANDIDATE' or call['drafts'] <= 0:
            reasons.append('incomplete or unsuccessful candidate')
        if call['tokens'] != call['drafts'] + 1:
            reasons.append('candidate token count does not match draft length')
        if indices[call['invocation']] != list(range(call['off'], call['off'] + call['tokens'])):
            reasons.append('speculative indices do not match complete verify batch')
        events = call['dispatches']
        if any(e['q'][1] != call['tokens'] for e in events):
            reasons.append('attention query length does not match complete verify batch')
        layers = [e['layer'] for e in events]
        if len(layers) != len(expected_layer_ids) or set(layers) != set(expected_layer_ids):
            reasons.append('incomplete or ambiguous layer coverage')
        keys = [(e['device'], int(e['tensor'], 16)) for e in events]
        if any(ptr == 0 for _, ptr in keys) or len(keys) != len(set(keys)):
            reasons.append('ambiguous dispatch tensor identity')
        if any(e['kernel'] not in (100, 200, 300, 400) or e['k_type'].upper() not in ('Q8_0', 'Q4_0')
               or e['k_type'].upper() != e['v_type'].upper() for e in events):
            reasons.append('unsupported kernel or KV type')
        if parsed['uncorrelated_dispatch_counts']:
            reasons.append('uncorrelated dispatch in capture')
        candidates.append({'invocation': call['invocation'], 'draft_length': call['drafts'],
                           'indices': indices[call['invocation']], 'dispatches': events,
                           'status': 'UNKNOWN' if reasons else 'OBSERVED', 'reasons': reasons,
                           'vec_observed': None if reasons else any(e['kernel'] == 100 for e in events)})
    return {'status': 'OBSERVED' if candidates and all(c['status'] == 'OBSERVED' for c in candidates) else 'UNKNOWN',
            'candidates': candidates, 'unclassified_controls': controls, 'raw_events': raw_events,
            'uncorrelated_dispatch_counts': parsed['uncorrelated_dispatch_counts'],
            'limitations': ['source and loaded binary identity, complete delivery, HIP residency and correctness unverified',
                            'selection is scoped to observed calls and establishes no performance claim']}
