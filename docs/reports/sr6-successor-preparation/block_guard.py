#!/usr/bin/env python3
"""Model-free SR-6 block exposure classification; not grant admission.

Callers must supply a complete, authoritative inventory. This component does
not scan storage or establish the provenance of inventory records.
"""

ARMS = frozenset(('composed3', 'composed4', 'mtp3', 'mtp4', 'mtp4_repeat'))


def classify(prompt_ids, attempts):
    """Return FRESH, COMPLETE, or ABANDON; a partial block is never retried."""
    if (not isinstance(prompt_ids, list) or not prompt_ids or
            any(not isinstance(p, str) or not p for p in prompt_ids) or
            len(set(prompt_ids)) != len(prompt_ids) or not isinstance(attempts, list)):
        return 'ABANDON'
    expected = {(p, a) for p in prompt_ids for a in ARMS}
    observed = set()
    for entry in attempts:
        if not isinstance(entry, dict):
            return 'ABANDON'
        key = (entry.get('prompt_id'), entry.get('arm'))
        try:
            if key not in expected or key in observed:
                return 'ABANDON'
            observed.add(key)
        except TypeError:
            return 'ABANDON'
        if entry.get('exposure') is not True or entry.get('response') != 'complete':
            return 'ABANDON'
    if not observed:
        return 'FRESH'
    return 'COMPLETE' if observed == expected else 'ABANDON'
