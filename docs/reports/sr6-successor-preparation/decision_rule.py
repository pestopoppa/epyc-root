#!/usr/bin/env python3
"""Proposed SR-6 within-window bootstrap, for model-free evaluation only.

This consumes paired-analysis output, not native evidence. It cannot establish
admission, complete exposure, provenance, independent windows or sampling validity.
"""
import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ARMS = ('composed3', 'composed4', 'mtp3', 'mtp4', 'mtp4_repeat')
CLASSES = ('code', 'rag', 'prose')
RESAMPLES = 10000
SEED = 20261102
ALPHA_PER_WINDOW = 0.05 / 3
PRACTICAL_LOG_GAIN = math.log(1.05)


def evaluate(doc, expected):
    """Evaluate a candidate signal; never produce an execution or registry verdict."""
    try:
        if doc.get('schema') != 'sr6.paired-analysis-draft.v1' or doc.get('status') != 'DESCRIPTIVE_ONLY' or doc.get('errors'):
            raise ValueError('paired analysis is not complete')
        if not isinstance(expected, dict) or len(expected) != 3:
            raise ValueError('exactly three prespecified windows required')
        groups = doc.get('groups')
        if not isinstance(groups, list):
            raise ValueError('missing groups')
        windows = defaultdict(list)
        seen = set()
        for g in groups:
            window, prompt, cls = g['window'], g['prompt_id'], g['class']
            if window not in expected or cls not in CLASSES or not isinstance(prompt, str) or not prompt or (window, prompt) in seen:
                raise ValueError('unexpected or duplicate prompt')
            seen.add((window, prompt))
            speeds = g['tokens_per_second']
            if set(speeds) != set(ARMS) or any(type(speeds[a]) not in (int, float) or not math.isfinite(speeds[a]) or speeds[a] <= 0 for a in ARMS):
                raise ValueError('invalid throughput')
            windows[window].append((prompt, cls, math.log(speeds['composed3']/speeds['composed4']),
                                    math.log(speeds['mtp3']/speeds['mtp4']),
                                    math.log(speeds['mtp4_repeat']/speeds['mtp4'])))
        for window, ids in expected.items():
            if not isinstance(window, str) or not window or not isinstance(ids, list) or len(ids) != len(set(ids)) or any(not isinstance(x, str) or not x for x in ids):
                raise ValueError('invalid prespecified prompt inventory')
            subset = windows[window]
            if {x[0] for x in subset} != set(ids) or len(subset) < 15:
                raise ValueError('missing or unexpected planned prompts')
            if any(Counter(x[1] for x in subset)[c] < 5 for c in CLASSES):
                raise ValueError('fewer than five prompts per class in a window')
        # Prompt IDs must identify disjoint windows, not merely distinct rows.
        all_ids = [x for ids in expected.values() for x in ids]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError('prompt IDs reused across windows')
        rng = random.Random(SEED)
        results = []
        for window in sorted(expected):
            subset = sorted(windows[window])
            strata = [[x for x in subset if x[1] == c] for c in CLASSES]
            n = len(subset)
            composed = sum(x[2] for x in subset) / n
            control = sum(x[3] for x in subset) / n
            aa = max(abs(x[4]) for x in subset)
            draws = []
            for _ in range(RESAMPLES):
                draws.append(sum(rng.choice(stratum)[2] for stratum in strata for _ in stratum) / n)
            draws.sort()
            # floor is conservative relative to the specified lower percentile.
            lower = draws[math.floor(ALPHA_PER_WINDOW * (RESAMPLES - 1))]
            passes = lower > max(PRACTICAL_LOG_GAIN, aa) and control > 0
            results.append({'window': window, 'prompts': n,
                            'composed_geometric_gain': math.expm1(composed),
                            'control_geometric_gain': math.expm1(control),
                            'lower_simultaneous_gain': math.expm1(lower),
                            'aa_max_absolute_log_ratio': aa, 'candidate_pass': passes})
        return {'status': 'CANDIDATE_SIGNAL_ONLY', 'candidate': 'SIGNAL' if all(r['candidate_pass'] for r in results) else 'INCONCLUSIVE',
                'windows': results, 'verdict': None,
                'limitations': ['External provenance, exposure, residency and independence are unverified.',
                                'Percentile-bootstrap coverage relies on sampling assumptions and is not established by this program.',
                                'This draft is not predeclared until sealed before exposure; no registry authority.']}
    except (ValueError, KeyError, TypeError, OverflowError, ZeroDivisionError) as exc:
        return {'status': 'UNKNOWN', 'candidate': None, 'verdict': None, 'reason': str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paired_analysis', type=Path)
    parser.add_argument('expected_prompt_ids', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        doc = json.loads(args.paired_analysis.read_text())
        expected = json.loads(args.expected_prompt_ids.read_text())
        result = evaluate(doc, expected)
        with args.output.open('x') as out:
            json.dump(result, out, indent=2, sort_keys=True, allow_nan=False)
            out.write('\n')
        return 2 if result['status'] == 'UNKNOWN' else 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f'UNKNOWN: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
