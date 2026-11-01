#!/usr/bin/env python3
"""Pure, fail-closed decision reducer for the prospective C5 candidate replay.

Input is native producer data. This module never starts a process, sends a request,
reads a model, or turns partial observations into measurement warrants.
"""
from __future__ import annotations
import math
from h1_event_model import classify
import device_identity

GIB = 1024 ** 3


def evaluate(expected, requests, samples, evidence):
    """Evaluate strictly bound completed replay. Times are monotonic seconds.

    expected: ordered list of (tag, request-body sha256); requests: ordered dicts
    tag, body_sha256, http_status, completed, nodraft, prompt_n, predicted_n. Samples: ordered
    dicts t, phase (load/warm/t7a), own_vram_b, hip_resident. evidence: dict with
    capture_complete, load_complete, t7a_complete, cleanup_verified, source_bound.
    No percentage, timing, quality, or production registry decision is implied.
    """
    unknown = lambda reason: {'verdict': 'UNKNOWN', 'reason': reason, 'phase_growth_gib': None, 'runtime_term_gib': None}
    if not all(evidence.get(x) is True for x in ('capture_complete','load_complete','t7a_complete','cleanup_verified','source_bound')):
        return unknown('capture, source, phase, or cleanup evidence missing')
    if len(expected) != 48 or len(set(expected)) != 48 or len(requests) != 48:
        return unknown('incomplete or duplicate predeclared traffic')
    for r, (tag, digest) in zip(requests, expected):
        if (r.get('tag'), r.get('body_sha256')) != (tag, digest) or r.get('completed') is not True or r.get('http_status') != 200:
            return unknown('request identity, completion, or HTTP failure')
    try:
        classified = classify(requests)
    except ValueError:
        return unknown('H1 event model lacks valid native timing counters')
    triggers = sum(r['h1_event_model'] for r in classified)
    if triggers < 5:
        return unknown('fewer than five H1 modeled transitions')
    if not samples:
        return unknown('no residency samples')
    binding=evidence.get('device_binding')
    if (not isinstance(binding,dict) or binding.get('bdf') != device_identity.BDF
        or binding.get('unique_id') != device_identity.UNIQUE or binding.get('vendor') != device_identity.VENDOR
        or binding.get('device') != device_identity.DEVICE or type(binding.get('gpu_id')) is not int
        or binding['gpu_id'] <= 0):
        return unknown('validated MI210 device binding missing')
    if any(s.get('gpu_id') != binding['gpu_id'] or s.get('gpu_unique_id') != binding['unique_id']
           or s.get('gpu_bdf') != binding['bdf'] for s in samples):
        return unknown('sample identity does not match captured MI210 binding')
    last = -math.inf
    for s in samples:
        t, v = s.get('t'), s.get('own_vram_b')
        if isinstance(t, bool) or not isinstance(t, (int,float)) or not math.isfinite(t) or t <= last:
            return unknown('invalid or non-monotonic sample time')
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            return unknown('own VRAM sample missing or invalid')
        last = t
    try:
        load_start, load_end = evidence['load_start_t'], evidence['load_end_t']
        phase_start, phase_end = evidence['t7a_start_t'], evidence['t7a_end_t']
        if not all(isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t) for t in (load_start, load_end, phase_start, phase_end)):
            return unknown('invalid phase markers')
        if not load_start < load_end < phase_start < phase_end:
            return unknown('phase marker order invalid')
    except (KeyError, TypeError):
        return unknown('phase markers missing')
    load = [s for s in samples if load_start <= s['t'] <= load_end]
    t7a = [s for s in samples if phase_start <= s['t'] <= phase_end]
    before = [s for s in samples if s['t'] <= phase_start]
    after = [s for s in samples if s['t'] >= phase_end]
    if not before or not after or phase_start - before[-1]['t'] > 2 or after[0]['t'] - phase_end > 2:
        return unknown('T7A interval is not bracketed by adjacent samples')
    baseline = before[-1]

    # Before backend initialization the server legitimately has no HIP/KFD residency.
    # Once positive residency appears, it may not disappear within the load window.
    first_positive = next((i for i, s in enumerate(load) if s.get('hip_resident') is True and s['own_vram_b'] > 0), None)
    if first_positive is None or len(load[first_positive:]) < 2 or len(t7a) < 2:
        return unknown('load or T7A observation window lacks two positive residency samples')
    if any(s.get('hip_resident') is not True or s['own_vram_b'] <= 0 for s in load[first_positive:] + t7a + [baseline, after[0]]):
        return unknown('positive own HIP residency lost after initialization')
    if max(s['t'] for s in load) >= min(s['t'] for s in t7a):
        return unknown('load and T7A windows overlap or are reversed')
    observed = [s for s in samples if load[first_positive]['t'] <= s['t'] <= after[0]['t']]
    if any(b['t']-a['t'] > 2 for a, b in zip(observed, observed[1:])):
        return unknown('GPU sampling gap exceeds two seconds during observed interval')
    if any(s.get('hip_resident') is not True or s['own_vram_b'] <= 0 for s in observed):
        return unknown('positive own HIP residency lost during observed interval')
    load_peak = max(s['own_vram_b'] for s in load)
    all_peak = max(s['own_vram_b'] for s in samples)
    phase_growth = (max(s['own_vram_b'] for s in t7a + [baseline, after[0]]) - baseline['own_vram_b']) / GIB
    runtime = (all_peak - load_peak) / GIB
    return {'verdict': 'HOLDS' if phase_growth <= 0.3 else 'FAILS', 'reason': None,
            'phase_growth_gib': phase_growth, 'runtime_term_gib': runtime,
            'h1_modeled_transition_count': triggers, 'load_peak_bytes': load_peak, 'whole_run_peak_bytes': all_peak}
