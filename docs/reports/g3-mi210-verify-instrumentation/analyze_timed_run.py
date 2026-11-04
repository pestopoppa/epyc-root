#!/usr/bin/env python3
"""Fail-closed join of V4 verify trace and in-window GPU residency samples.

This does not prove admission, a clock stable between samples, or per-process
VRAM. Its output is diagnostic evidence only, never a bandwidth verdict.
"""
import math

from invocation_trace_v5 import classify_invocation_trace_v5
from sysfs_residency import correlate as correlate_residency


def clocks_stable(samples, tolerance_s=0.05):
    if not samples:
        return False
    offsets = []
    for item in samples:
        try:
            wall_start, wall_end = item['observation_start'], item['observation_end']
            mono_start, mono_end = item['monotonic_start'], item['monotonic_end']
            if any(type(x) not in (int, float) or not math.isfinite(x) for x in (wall_start, wall_end, mono_start, mono_end)):
                return False
            if wall_end < wall_start or mono_end < mono_start:
                return False
            offsets.extend((wall_start - mono_start, wall_end - mono_end))
        except (KeyError, TypeError):
            return False
    return max(offsets) - min(offsets) <= tolerance_s


def analyze(*, trace, expected_layer_ids, baseline, samples, card, pid, backend, backend_sha256,
            complete, drained, device, pid_birth, topology_stable):
    result = {'status': 'UNKNOWN', 'reasons': [], 'trace': None, 'correlations': [],
              'scope': 'Observed dispatches only; KFD VRAM is per captured PID and card VRAM is device-wide; no bandwidth or performance conclusion.'}
    if complete is not True or drained is not True or topology_stable is not True:
        result['reasons'].append('incomplete capture, unverified drain or changed device topology')
        return result
    if not clocks_stable([baseline, *samples]):
        result['reasons'].append('missing or unstable realtime and monotonic clock samples')
        return result
    try:
        parsed = classify_invocation_trace_v5(trace, expected_layer_ids=expected_layer_ids)
        result['trace'] = parsed
        candidates = parsed['candidates']
        if parsed['status'] != 'OBSERVED' or not candidates:
            result['reasons'].append('no fully attributed native verify trace')
            return result
        calls = [v for c in candidates for v in c['native_timing']]
        joins = correlate_residency(calls=calls, samples=samples, pid=pid, birth=pid_birth, gpu_id=device['gpu_id'])
        result['correlations'] = joins
        if not any(j['status'] == 'BOUNDED_OBSERVATION' for j in joins):
            result['reasons'].append('no in-invocation dispatch overlaps a complete residency observation')
            return result
        # Restrict any VEC observation to calls with at least one matched dispatch;
        # a match for another dispatch in that call is insufficient for a VEC claim.
        matches = {(j['invocation'], j['native_dispatch'])
                   for j in joins if j['status'] == 'BOUNDED_OBSERVATION'}
        observed = []
        for c in candidates:
            for dispatch, timing in zip(c['dispatches'], c['native_timing']):
                if (c['invocation'], timing['native_dispatch']) in matches:
                    observed.append({'invocation': c['invocation'], 'kernel': dispatch['kernel'],
                                     'draft_length': c['draft_length'], 'layer': dispatch['layer']})
        result['status'] = 'SCOPED_DISPATCH_OBSERVED'
        result['observed'] = observed
        result['vec_observed'] = any(x['kernel'] == 100 for x in observed)
        return result
    except (ValueError, KeyError, TypeError, OSError) as exc:
        result['reasons'].append('invalid native trace or residency: ' + str(exc))
        return result
