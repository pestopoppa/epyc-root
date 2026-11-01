#!/usr/bin/env python3
"""Project request-total usage reported by the orchestrator /chat response.

This is not an inference client and establishes no server identity, grant or
measurement warrant. Counts are whole-request totals, never per-REPL-turn data.
Caller must retain the original response and verify the serving source.
"""
from __future__ import annotations

from typing import Any


def request_usage(response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise TypeError('response must be a JSON object')
    reasons: list[str] = []
    if response.get('real_mode') is not True or response.get('mock_mode') is not False:
        reasons.append('real_nonmock_mode_not_confirmed')
    if response.get('error') or response.get('error_detail'):
        reasons.append('response_error')

    def count(key: str, *, minimum: int = 0) -> int | None:
        value = response.get(key)
        if type(value) is not int or value < minimum:
            reasons.append(f'{key}_missing_or_invalid')
            return None
        return value

    turns = count('turns', minimum=1)
    prompt = count('prompt_tokens')
    output = count('output_tokens_reported')
    status = response.get('output_tokens_status')
    sources = response.get('output_tokens_sources')
    if status != 'reported':
        reasons.append('output_tokens_not_reported')
        output = None
    if not isinstance(sources, list) or not sources or any(not isinstance(s, str) or not s for s in sources):
        reasons.append('output_sources_missing_or_invalid')
        sources = []
        output = None
    return {'scope': 'request_total', 'turns': turns, 'prompt_tokens': prompt,
            'output_tokens': output, 'output_tokens_sources': sources,
            'complete': not reasons, 'incomplete_reasons': reasons,
            'identity_verified': False, 'grant_verified': False}
