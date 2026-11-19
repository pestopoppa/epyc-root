#!/usr/bin/env python3
"""Strict complete-native-token comparator for public Voxtral fixture traces.

This reports token agreement only. It does not establish transcription accuracy,
runtime residency, provenance, or validation eligibility.
"""
import argparse
import json
from pathlib import Path
import re


def parse_voxtral_tokens(log):
    """Read exactly one complete, nonempty native witness, without trimming IDs."""
    state = 'before'
    declared = None
    tokens = []
    for line in log.splitlines():
        if not line.startswith('CS8_VOXTRAL_'):
            continue
        header = re.fullmatch(r'CS8_VOXTRAL_TOKENS ([0-9]+)', line)
        token = re.fullmatch(r'CS8_VOXTRAL_TOKEN ([0-9]+) ([0-9]+)', line)
        if header and state == 'before':
            declared = int(header[1])
            state = 'tokens'
        elif token and state == 'tokens':
            if int(token[1]) != len(tokens):
                raise ValueError('native token index gap or duplicate')
            tokens.append(int(token[2]))
            if len(tokens) > declared:
                raise ValueError('native token count overflow')
        elif line == 'CS8_VOXTRAL_TOKENS_END' and state == 'tokens':
            if not tokens or len(tokens) != declared:
                raise ValueError('empty or incomplete native witness')
            state = 'after'
        else:
            raise ValueError('malformed, duplicate or out-of-order native witness')
    if state != 'after':
        raise ValueError('missing or truncated native witness')
    return tokens


def compare(candidate, reference):
    actual = parse_voxtral_tokens(candidate)
    expected = parse_voxtral_tokens(reference)
    first = next((i for i, (a, b) in enumerate(zip(actual, expected)) if a != b), None)
    if first is None and len(actual) != len(expected):
        first = min(len(actual), len(expected))
    return {'schema': 'stt5-voxtral-token-agreement/v1',
            'verdict': 'PASS' if actual == expected else 'FAIL',
            'candidate_count': len(actual), 'reference_count': len(expected),
            'first_difference': first, 'candidate_ids': actual, 'reference_ids': expected}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('candidate', type=Path)
    ap.add_argument('reference', type=Path)
    args = ap.parse_args()
    try:
        result = compare(args.candidate.read_text(), args.reference.read_text())
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({'verdict': 'INCONCLUSIVE', 'error': str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
