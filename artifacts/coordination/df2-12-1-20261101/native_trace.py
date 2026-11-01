#!/usr/bin/env python3
"""Audit exact native DF2 trace markers from an instrumented measurement image."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re

MARKER = re.compile(r'DF2_NATIVE_(BATCH|ROUND|REUSE)_V1\s+(.+)$')
FIELD = re.compile(r'([a-z_]+)=(-?[0-9]+)')
PHASE = re.compile(r'\bphase=(prompt|decode)\b')


def parse(path):
    batches = []
    rounds = []
    reuse = []
    malformed = []
    raw = pathlib.Path(path).read_bytes()
    for lineno, line in enumerate(raw.decode(errors='replace').splitlines(), 1):
        match = MARKER.search(line)
        if not match:
            continue
        fields = {name: int(value) for name, value in FIELD.findall(match.group(2))}
        kind = match.group(1)
        required = ({'slot', 'task', 'cache_prompt', 'n_past', 'old_prompt_tokens',
                     'seq_pos_min', 'checkpoints'} if kind == 'REUSE' else
                    {'batch', 'slot', 'task', 'decoded_subbatch_len',
                     'scheduler_batch_len', 'off'})
        if kind == 'BATCH':
            required.update({'slot_tokens', 'prompt_len', 'prompt_fp'})
        elif kind == 'ROUND':
            required.update({'draft_n', 'accepted', 'rollback'})
        if required - fields.keys():
            malformed.append({'line': lineno, 'missing': sorted(required - fields.keys())})
            continue
        record = {'line': lineno, **fields}
        if kind == 'BATCH':
            phase = PHASE.search(match.group(2))
            if phase is None:
                malformed.append({'line': lineno, 'reason': 'prompt/decode phase absent'})
                continue
            record['phase'] = phase.group(1)
            batches.append(record)
        elif kind == 'ROUND':
            if fields['rollback'] != fields['draft_n'] - fields['accepted']:
                malformed.append({'line': lineno, 'reason': 'rollback arithmetic mismatch'})
            rounds.append(record)
        else:
            reuse.append(record)
    by_batch = {}
    for batch in batches:
        by_batch.setdefault(batch['batch'], []).append(batch)
    for round_ in rounds:
        cohort = by_batch.get(round_['batch'], [])
        if not any(x['slot'] == round_['slot'] and x['task'] == round_['task'] and
                   x['phase'] == 'decode' and x['decoded_subbatch_len'] == round_['decoded_subbatch_len']
                   for x in cohort):
            malformed.append({'line': round_['line'], 'reason': 'round batch or slot marker missing'})
    for cohort in by_batch.values():
        lengths = {(x['decoded_subbatch_len'], x['scheduler_batch_len'], x['off']) for x in cohort}
        if len(lengths) != 1:
            malformed.append({'batch': cohort[0]['batch'], 'reason': 'inconsistent batch lengths'})
        if sum(x['slot_tokens'] for x in cohort) < cohort[0]['decoded_subbatch_len']:
            malformed.append({'batch': cohort[0]['batch'], 'reason': 'unaccounted subbatch tokens'})
    return {'schema': 'epyc.df2_12_1.native_trace.v1', 'source_log': str(path),
            'source_sha256': hashlib.sha256(raw).hexdigest(), 'batch_markers': batches,
            'round_markers': rounds, 'reuse_markers': reuse, 'malformed': malformed,
            'complete': bool(batches and rounds and not malformed)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    result = parse(args.log)
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
