#!/usr/bin/env python3
"""Compare paired synthetic rollback controls; never assert MTP or CAFE-4 closure."""
import math
import re

HEX = re.compile(r'^[0-9a-f]{64}$')
ROW = re.compile(r'^CAFE4_NEXT_COMPARISON mode=(observe|fault) index=(\d+) finite=1 max_abs=([^ ]+) threshold=1e-5 selected=(\d+) faulted=(\d+)$', re.M)
PARTIAL = re.compile(r'^STRICT_PARTIAL width=(\d+) accepted=(\d+) keep=(\d+) max_abs=([^ ]+)$', re.M)


def compare(observe, fault):
    """Inputs are independently captured records: identities, config, rc and native log.

    Every positive result is a candidate diagnostic observation, not an MTP verdict.
    Capture authenticates these values elsewhere; this projection cannot do so.
    """
    try:
        for k in ('binary_sha256', 'model_sha256', 'patch_sha256'):
            if not HEX.fullmatch(observe[k]) or observe[k] != fault[k]:
                return {'status': 'UNKNOWN', 'reason': f'{k} missing or mismatched'}
        if not isinstance(observe['config'], dict) or not observe['config'] or observe['config'] != fault['config']:
            return {'status': 'UNKNOWN', 'reason': 'config missing or mismatched'}
        if observe['rc'] != 1 or fault['rc'] != 1:
            return {'status': 'UNKNOWN', 'reason': 'unexpected candidate exit status'}
        a = ROW.findall(observe['log']); b = ROW.findall(fault['log'])
        if not a or not b or any(x[0] != 'observe' for x in a) or any(x[0] != 'fault' for x in b):
            return {'status': 'UNKNOWN', 'reason': 'missing or mixed finite comparisons'}
        valid = lambda row: math.isfinite(float(row[2])) and float(row[2]) >= 0 and int(row[3]) > 0 and int(row[4]) <= int(row[3])
        if not all(map(valid, a + b)):
            return {'status': 'UNKNOWN', 'reason': 'invalid comparison or counters'}
        if any(int(x[4]) != 0 or float(x[2]) > 1e-5 for x in a):
            return {'status': 'UNKNOWN', 'reason': 'observe condition failed'}
        partials = PARTIAL.findall(observe['log'])
        if not partials or not all(0 < int(ac) < int(w) and int(k) > 0 and math.isfinite(float(e)) and 0 <= float(e) <= 1e-5 for w, ac, k, e in partials):
            return {'status': 'UNKNOWN', 'reason': 'strict partial rollback absent or invalid'}
        if 'RESULT: UNKNOWN (token consistency observed; recurrent snapshot execution and fault control unproven)' not in observe['log']:
            return {'status': 'UNKNOWN', 'reason': 'observe run did not complete candidate path'}
        # Require the first divergent comparison to have an independently visible
        # state-specific fault counter; nonfinite logits and generic exits are not evidence.
        observe_indices = {x[1] for x in a}
        matches = [x for x in b if x[1] in observe_indices and int(x[4]) > 0 and float(x[2]) > 1e-5]
        if not matches or 'UNKNOWN next-token logits differ from serial oracle' not in fault['log']:
            return {'status': 'UNKNOWN', 'reason': 'finite targeted fault divergence not established'}
        return {'status': 'SYNTHETIC_CONTROL_OBSERVED', 'reason': 'matched finite control divergence with target counters; synthetic draft only', 'limitations': 'No MTP, causal isolation, tolerance calibration, runtime provenance, or CAFE-4 verdict follows.'}
    except (KeyError, TypeError, ValueError, OverflowError):
        return {'status': 'UNKNOWN', 'reason': 'malformed evidence'}
