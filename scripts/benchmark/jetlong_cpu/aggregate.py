#!/usr/bin/env python3
"""Offline Jet-Long recall aggregation; no inference or task-completion claim.

A timeout is a failure. Unstarted or uncertain cells never become failures or
vanish from the denominator. Only a complete, terminal 150-pair matrix gets a
recall comparison; gate A and independent throughput still require evidence.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import ledger

SCORER_PATH = Path('/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/niah_scorer.py')
SCORER_SHA256 = 'dcf9085156afaccd1b1e42f8e683f786de8b9749d00e85e7dda4c837992dcd2a'
DEPTHS = (0.1, 0.3, 0.5, 0.7, 0.9)
LENGTHS = (300000, 524288)


def load_scorer():
    if hashlib.sha256(SCORER_PATH.read_bytes()).hexdigest() != SCORER_SHA256:
        raise ValueError('canonical scorer does not match pinned digest')
    spec = importlib.util.spec_from_file_location('canonical_niah_scorer', SCORER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_matrix(plan, scorer):
    expected = {(length, depth, needle, seed) for length in LENGTHS
                for depth in DEPTHS for needle in range(5) for seed in range(3)}
    observed = set()
    for item in plan['items']:
        key = (item['length'], item['depth_fraction'], item['needle_index'], item['seed_index'])
        if (type(item['length']) is not int or type(item['needle_index']) is not int or
                type(item['seed_index']) is not int or key not in expected or key in observed):
            raise ValueError('invalid or duplicate matrix coordinate')
        if not scorer.normalize_lenient(item['expected']):
            raise ValueError('undecidable reference')
        observed.add(key)
    if observed != expected:
        raise ValueError('incomplete preregistered 150-item matrix')


def report(plan_path, ledger_dir):
    scorer = load_scorer()
    # initialize creates no events; require an existing pinned ledger instead.
    plan, pin = ledger.read_plan(plan_path)
    pinned = json.loads((Path(ledger_dir) / 'plan.sha256').read_text())
    if pinned != {'sha256': pin}:
        raise ValueError('ledger plan identity mismatch')
    validate_matrix(plan, scorer)
    inventory = ledger.inventory(ledger_dir, plan, pin)
    states = {cell: state for state, cells in inventory.items() for cell in cells}
    results = []
    for item in plan['items']:
        for arm in ledger.ARMS:
            state = states[(item['id'], arm)]
            row = {'id': item['id'], 'length': item['length'], 'depth_fraction': item['depth_fraction'],
                   'arm': arm, 'state': state, 'strict': None, 'lenient': None}
            if state == 'finished':
                event = json.loads(ledger._cell(ledger_dir, item['id'], arm, 'finished').read_text())
                row['terminal_status'] = event['status']
                score = scorer.score_niah(event['response'] if event['status'] == 'ok' else '', item['expected'])
                if not score['decidable']:
                    raise ValueError('undecidable reference')
                row['strict'], row['lenient'] = score['strict'], score['lenient']
                timing = event.get('timings')
                if event['status'] == 'ok' and isinstance(timing, dict):
                    n, ms = timing.get('predicted_n'), timing.get('predicted_ms')
                    if type(n) is int and n > 0 and type(ms) in (int, float) and 0 < ms < float('inf'):
                        row['decode_tokens'] = n
                        row['decode_ms'] = ms
                        row['decode_tokens_per_s'] = n * 1000 / ms
            results.append(row)
    summaries = []
    comparisons = []
    all_terminal = len(inventory['finished']) == 300
    for length in LENGTHS:
        for arm in ledger.ARMS:
            rows = [r for r in results if r['length'] == length and r['arm'] == arm]
            finished = [r for r in rows if r['state'] == 'finished']
            terminal = len(finished) == 75
            strict = sum(r['strict'] is True for r in finished)
            lenient = sum(r['lenient'] is True for r in finished)
            summaries.append({'length': length, 'arm': arm, 'planned': 75,
                              'finished': len(finished),
                              'unknown': sum(r['state'] == 'unknown' for r in rows),
                              'unstarted': sum(r['state'] == 'unstarted' for r in rows),
                              'timeouts': sum(r.get('terminal_status') == 'timeout' for r in rows),
                              'strict_correct_terminal': strict, 'lenient_correct_terminal': lenient,
                              'strict_accuracy': strict / 75 if terminal else None,
                              'lenient_accuracy': lenient / 75 if terminal else None,
                              'format_gap': (lenient - strict) / 75 if terminal else None})
        j, y = [s for s in summaries if s['length'] == length]
        complete = all_terminal and j['finished'] == y['finished'] == 75
        comparisons.append({'length': length, 'recall_j_ge_y':
                            j['lenient_correct_terminal'] >= y['lenient_correct_terminal'] if complete else None})
    complete = all(s['finished'] == 75 for s in summaries)
    return {'schema': 'jetlong-recall-aggregate-v1', 'plan_sha256': pin,
            'scorer_sha256': SCORER_SHA256, 'metric_direction': 'higher is better',
            'state': 'terminal_recall_only' if complete else 'incomplete',
            'task_complete': False,
            'limits': ['Gate A and separate throughput qualification are not adjudicated here'],
            'summaries': summaries, 'comparisons': comparisons, 'items': results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--ledger', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    result = report(a.plan, a.ledger)
    Path(a.out).write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
