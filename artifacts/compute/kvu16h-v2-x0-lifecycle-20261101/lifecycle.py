"""Prospective P3 v2 / X0 isolated-arm coordinator; no production adapter.

Runtime methods must start and stop captured servers and enforce binary/process identity.
This module intentionally has no real HTTP or subprocess adapter and is not a launcher.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


class InvalidRun(RuntimeError):
    pass


def payload_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _validate_payload(payload: dict[str, Any]) -> None:
    # Request-level speculative overrides would mask a drafted server identity error.
    if any(str(k).startswith('speculative') for k in payload):
        raise InvalidRun('request-level speculative override forbidden')


def run_arm(runtime: Any, variant: str, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run one arm on its own server; caller owns exposure and durable partial records.

    Runtime.start must clean up a child if it raises before returning a handle. stop
    must return exactly True only after verified captured-child termination.
    False, None, or an exception prevents any paired result or subsequent arm.
    """
    if variant not in ('drafted', 'nodraft') or not cases:
        raise InvalidRun('invalid arm or empty cases')
    for case in cases:
        _validate_payload(case['warm'])
        _validate_payload(case['measure'])
        if case['minimum_cache_tokens'] <= 0:
            raise InvalidRun('cache threshold must be positive')
    handle = runtime.start(variant)
    try:
        if runtime.identity(handle) != variant:
            raise InvalidRun('server identity differs from arm')
        rows = []
        for case in cases:
            # P3 adapter must independently reconstruct neighbor occupancy per arm.
            occupancy = runtime.prepare_occupancy(handle, case)
            if not occupancy.get('verified', False):
                raise InvalidRun('occupancy is unverified')
            warm = copy.deepcopy(case['warm'])
            measure = copy.deepcopy(case['measure'])
            warm_result = runtime.request(handle, warm)
            result = runtime.request(handle, measure)
            cache_n = (result.get('timings') or {}).get('cache_n')
            if type(cache_n) is not int or cache_n < case['minimum_cache_tokens']:
                raise InvalidRun('measured request lacks required cache hit')
            rows.append({'id': case['id'], 'variant': variant, 'warm_sha256': payload_sha(warm),
                         'measure_sha256': payload_sha(measure), 'occupancy': occupancy,
                         'warm_result': warm_result, 'result': result})
        return rows
    finally:
        if runtime.stop(handle) is not True:
            raise InvalidRun('captured server cleanup unverified')


def run_pair(runtime: Any, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Separate sequential servers; missing/invalid arms raise and yield no pair."""
    cases = copy.deepcopy(cases)
    drafted = run_arm(runtime, 'drafted', cases)
    nodraft = run_arm(runtime, 'nodraft', cases)
    for a, b in zip(drafted, nodraft, strict=True):
        if (a['id'], a['warm_sha256'], a['measure_sha256']) != (b['id'], b['warm_sha256'], b['measure_sha256']):
            raise InvalidRun('arm payloads differ')
    return drafted + nodraft
