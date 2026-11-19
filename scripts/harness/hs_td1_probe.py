#!/usr/bin/env python3
"""HS-TD-1 shadow risk/intent feasibility screen; never an action gate.

Authored references are diagnostic controls, not observed harness decisions.
Real-session agreement remains a separate acceptance requirement.
"""
from __future__ import annotations

import json
import math
import sys

import hs_td2_probe as runner

RISKS = ('low', 'medium', 'high')
INTENTS = ('read', 'edit', 'execute', 'external')


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate JSON key')
        value[key] = item
    return value


def decision(response):
    choice = response['choices'][0]
    if choice['finish_reason'] != 'stop':
        raise ValueError('unfinished classification')
    value = json.loads(choice['message']['content'], object_pairs_hook=unique)
    if not isinstance(value, dict) or set(value) != {'risk', 'intent', 'confidence'}:
        raise ValueError('classification schema')
    if value['risk'] not in RISKS or value['intent'] not in INTENTS:
        raise ValueError('classification outside closed set')
    confidence = value['confidence']
    if type(confidence) not in (float, int) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError('invalid confidence')
    return value


def proposed_decision(value):
    """Diagnostic mapping only: no permission system reads this answer."""
    return 'restrictive' if value['risk'] == 'high' or value['intent'] == 'external' else 'permissive'


def case_payload(case):
    # Exclude reference labels/decisions/rationale from model input.
    return {'request': case['request'], 'context': case['context']}


def reference_fields(case):
    return {'reference': {k: case[k] for k in ('risk', 'intent', 'decision', 'rationale')},
            'reference_kind': 'authored diagnostic; not an observed harness decision'}


def summarize(records, expected):
    full = [r for r in records if r['phase'] == 'full']
    keys = [(r['case_id'], r['repetition']) for r in full]
    if len(keys) != len(set(keys)) or len(full) > expected:
        raise ValueError('duplicate or excess observations')
    valid = [r for r in full if r['status'] == 'ok']
    agreements = {k: sum(r['judgment'][k] == r['reference'][k] for r in valid)
                  for k in ('risk', 'intent')}
    agreements['decision'] = sum(proposed_decision(r['judgment']) == r['reference']['decision'] for r in valid)
    disagreements = [r['record_path'] for r in valid
                     if any(r['judgment'][k] != r['reference'][k] for k in ('risk', 'intent'))
                     or proposed_decision(r['judgment']) != r['reference']['decision']]
    return {'complete': len(full) == expected, 'expected': expected, 'observed': len(full),
            'valid': len(valid), 'unknown': expected - len(valid), 'agreement_counts': agreements,
            'mean_confidence_valid': sum(r['judgment']['confidence'] for r in valid) / len(valid) if valid else None,
            'confidence_by_record': [{'record_path': r['record_path'], 'confidence': r['judgment']['confidence']} for r in valid],
            'disagreements': disagreements, 'all_attempt_call_s': sum(r['elapsed_s'] for r in full),
            'gate': False, 'scope': 'authored offline CPU feasibility screen; no real-session acceptance or permission efficacy claim'}


def main():
    return runner.main(decision_fn=decision, summarize_fn=summarize, case_payload=case_payload,
                       reference_fields=reference_fields, runtime_path=__file__)


if __name__ == '__main__':
    sys.exit(main())
