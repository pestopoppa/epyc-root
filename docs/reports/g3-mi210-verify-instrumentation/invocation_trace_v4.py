#!/usr/bin/env python3
"""Parse timestamped G3 V4 records, retaining V3 attribution rules.

The native time is realtime nanoseconds; callers must independently establish
clock consistency and can only claim bounded, device-wide residency evidence.
"""
import re
from invocation_trace_v2 import _MARKER
from invocation_trace_v3 import classify_invocation_trace_v3


def classify_invocation_trace_v4(text, *, expected_layer_ids):
    if not isinstance(text, str):
        raise ValueError('trace text required')
    records = []
    cleaned = []
    for line in text.splitlines():
        marker = _MARKER.search(line)
        if not marker:
            cleaned.append(line)
            continue
        match = re.search(r' time_ns=([0-9]+)$', line)
        if not match:
            raise ValueError('missing or malformed native timestamp')
        timestamp = int(match.group(1))
        if timestamp <= 0:
            raise ValueError('invalid native timestamp')
        base = line[:match.start()]
        ident = re.search(r'\binvocation=([0-9]+)\b', base)
        if not ident:
            raise ValueError('missing invocation id')
        records.append((marker.group(1), int(ident.group(1)), timestamp))
        cleaned.append(base)
    out = classify_invocation_trace_v3('\n'.join(cleaned), expected_layer_ids=expected_layer_ids)
    times = {}
    for kind, ident, stamp in records:
        if ident == 0:
            continue
        state = times.setdefault(ident, {'begin': None, 'end': None, 'dispatches': []})
        if kind == 'G3_TARGET_BEGIN_V3':
            if state['begin'] is not None: raise ValueError('duplicate begin time')
            state['begin'] = stamp
        elif kind == 'G3_TARGET_END_V3':
            if state['end'] is not None: raise ValueError('duplicate end time')
            state['end'] = stamp
        elif kind == 'G3_FATTN_DISPATCH_V3':
            state['dispatches'].append(stamp)
    for candidate in out['candidates']:
        state = times.get(candidate['invocation'], {})
        begin, end, ds = state.get('begin'), state.get('end'), state.get('dispatches', [])
        if not begin or not end or len(ds) != len(candidate['dispatches']) or any(not begin < t < end for t in ds):
            candidate['status'] = 'UNKNOWN'
            candidate['vec_observed'] = None
            candidate['reasons'].append('missing, inconsistent or non-monotonic native timestamps')
            candidate['native_timing'] = []
        else:
            candidate['native_timing'] = [{'invocation': candidate['invocation'], 'native_begin': begin/1e9,
                                           'native_dispatch': t/1e9, 'native_end': end/1e9} for t in ds]
    if any(c['status'] != 'OBSERVED' for c in out['candidates']): out['status'] = 'UNKNOWN'
    out['limitations'].append('realtime clock stability and residency require independent verification')
    return out
