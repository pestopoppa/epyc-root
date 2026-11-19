#!/usr/bin/env python3
"""Fail-closed V4 trace classification scoped to non-overlapping target calls.

The V4 source labels backend dispatches outside a target scope as unknown; that
includes initialization and draft work. We retain them and refuse any such
event during a target invocation. This does not infer ownership of any event.
"""
import re
from invocation_trace_v2 import _MARKER
from invocation_trace_v4 import classify_invocation_trace_v4


def classify_invocation_trace_v5(text, *, expected_layer_ids):
    active = None
    previous_ns = 0
    outside_unknown = 0
    seen = set()
    for line in text.splitlines():
        m = _MARKER.search(line)
        if not m:
            continue
        kind = m.group(1)
        ti = re.search(r' time_ns=([0-9]+)$', line)
        ident = re.search(r'\binvocation=([0-9]+)\b', line)
        if not ti or not ident:
            raise ValueError('missing timestamp or invocation')
        timestamp, call = int(ti.group(1)), int(ident.group(1))
        if timestamp <= 0 or timestamp < previous_ns:
            raise ValueError('invalid or decreasing native timestamp')
        previous_ns = timestamp
        if kind == 'G3_TARGET_BEGIN_V3':
            if call == 0 or active is not None or call in seen:
                raise ValueError('overlapping or duplicate invocation')
            active = call
            seen.add(call)
        elif kind == 'G3_TARGET_END_V3':
            if call == 0 or call != active:
                raise ValueError('unmatched invocation end')
            active = None
        elif kind == 'G3_FATTN_DISPATCH_V3':
            if call == 0:
                if active is not None:
                    raise ValueError('uncorrelated dispatch within target invocation')
                outside_unknown += 1
            elif call != active:
                raise ValueError('dispatch outside its active target invocation')
        else:
            raise ValueError('unsupported native event')
    if active is not None:
        raise ValueError('incomplete final target invocation')
    parsed = classify_invocation_trace_v4(text, expected_layer_ids=expected_layer_ids)
    for candidate in parsed['candidates']:
        candidate['reasons'] = [r for r in candidate['reasons'] if r != 'uncorrelated dispatch in capture']
        if candidate['reasons']:
            candidate['status'], candidate['vec_observed'] = 'UNKNOWN', None
        else:
            candidate['status'] = 'OBSERVED'
            candidate['vec_observed'] = any(d['kernel'] == 100 for d in candidate['dispatches'])
    parsed['status'] = ('OBSERVED' if parsed['candidates'] and all(c['status'] == 'OBSERVED' for c in parsed['candidates'])
                        else 'UNKNOWN')
    parsed['outside_target_unknown_dispatches'] = outside_unknown
    parsed['limitations'].append('Outside-target dispatches remain unattributed; scope requires ordered, non-overlapping host trace and independently stable clock.')
    return parsed
