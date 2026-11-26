#!/usr/bin/env python3
"""Validate an intermediate, token-aligned trace JSONL without running a model.

This is an interchange validator, not a llama-perplexity mask writer.
"""
import argparse
import hashlib
import json
from pathlib import Path


def validate(path):
    raw = Path(path).read_bytes()
    sessions = set()
    counts = {}
    for line_no, line in enumerate(raw.splitlines(), 1):
        try:
            row = json.loads(line)
            session, split = row['session_id'], row['split']
            tokens, mask = row['token_ids'], row['model_written']
            assert isinstance(session, str) and session
            assert split in ('calibration', 'heldout')
            assert isinstance(tokens, list) and tokens
            assert isinstance(mask, list) and len(tokens) == len(mask)
            assert all(type(t) is int and t >= 0 for t in tokens)
            assert all(type(m) is int and m in (0, 1) for m in mask)
            assert any(mask)
            assert session not in sessions
        except (ValueError, TypeError, KeyError, AssertionError) as exc:
            raise ValueError(f'invalid trace at line {line_no}') from exc
        sessions.add(session)
        totals = counts.setdefault(split, {'sessions': 0, 'tokens': 0, 'model_written': 0})
        totals['sessions'] += 1
        totals['tokens'] += len(tokens)
        totals['model_written'] += sum(mask)
    if set(counts) != {'calibration', 'heldout'}:
        raise ValueError('both calibration and heldout sessions are required')
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'splits': counts}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jsonl')
    args = parser.parse_args()
    print(json.dumps(validate(args.jsonl), indent=2, sort_keys=True))
