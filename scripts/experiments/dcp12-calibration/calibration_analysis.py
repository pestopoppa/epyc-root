#!/usr/bin/env python3
"""Paired eligibility accounting and exact unconditional McNemar power."""
import argparse
import json
import math
from pathlib import Path


def exact_power(n, p01, p10, alpha=0.05):
    """Two-sided exact conditional binomial test, averaged over discordance."""
    q = p01 + p10
    if not (n > 0 and 0 < alpha < 1 and 0 <= p01 <= 1 and 0 <= p10 <= 1 and q <= 1):
        raise ValueError("invalid power inputs")
    if q == 0:
        return 0.0
    alt = p01 / q
    power = 0.0
    for m in range(1, n + 1):
        # Stable log probabilities for larger planning values.
        logpm = math.lgamma(n+1)-math.lgamma(m+1)-math.lgamma(n-m+1)
        logpm += m*math.log(q) + ((n-m)*math.log1p(-q) if q < 1 else (0 if n == m else -math.inf))
        reject = 0.0
        tails, cumulative = [], 0
        for j in range(m // 2 + 1):
            cumulative += math.comb(m, j)
            tails.append(cumulative / 2**m)
        for k in range(m+1):
            tail = tails[min(k, m-k)]
            if min(1.0, 2*tail) <= alpha + 1e-15:
                if alt in (0, 1):
                    probability = float(k == (m if alt == 1 else 0))
                else:
                    probability = math.exp(math.lgamma(m+1)-math.lgamma(k+1)-math.lgamma(m-k+1)+k*math.log(alt)+(m-k)*math.log1p(-alt))
                reject += probability
        power += math.exp(logpm)*reject
    return min(power, 1.0)


def summarize(schedule, outcomes, rerun=1):
    if rerun not in (1, 2):
        raise ValueError("rerun must be 1 or 2")
    planned = {r['unit']: r for r in schedule}
    if len(planned) != len(schedule):
        raise ValueError('duplicate units')
    observed = {}
    for outcome in outcomes:
        unit = outcome['unit']
        if unit not in planned or unit in observed:
            raise ValueError('unexpected or duplicate outcome')
        row = planned[unit]
        if any(outcome.get(k) != row[k] for k in ('case','arm','seed','repeat','replicate')):
            raise ValueError('outcome configuration differs from schedule')
        observed[unit] = outcome
    pairs = {}
    for unit, row in planned.items():
        replicate = row.get('replicate')
        if type(replicate) is not int or replicate not in (0, 1, 2):
            raise ValueError('invalid replicate')
        group = pairs.setdefault(row['case'], {})
        if replicate in group:
            raise ValueError('duplicate case/replicate')
        group[replicate] = observed.get(unit)
    counts = {'eligible': 0, 'flips': 0, 'missing_grade': 0, 'unknown': 0, 'unattempted': 0, 'NA_pairs': 0, 'missing_first_request': 0, 'first_request_mismatch': 0}
    for pair in pairs.values():
        if set(pair) != {0, 1, 2}:
            raise ValueError('expected baseline and two reruns')
        pair = [pair[0], pair[rerun]]
        if any(r is None for r in pair): counts['unattempted'] += 1; continue
        if any(r['status'] == 'UNKNOWN' for r in pair): counts['unknown'] += 1; continue
        if any(r['status'] == 'grade_unavailable' or type(r.get('correct')) is not bool for r in pair): counts['missing_grade'] += 1; continue
        if any(r['status'] == 'NA' for r in pair): counts['NA_pairs'] += 1
        if any(not r.get('first_request_sha256') for r in pair): counts['missing_first_request'] += 1; continue
        if pair[0]['first_request_sha256'] != pair[1]['first_request_sha256']: counts['first_request_mismatch'] += 1; continue
        counts['eligible'] += 1
        counts['flips'] += pair[0]['correct'] != pair[1]['correct']
    counts['flip_rate'] = counts['flips']/counts['eligible'] if counts['eligible'] else None
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('window', type=Path)
    args = parser.parse_args()
    window = json.loads((args.window / 'WINDOW.json').read_text())
    results = [json.loads(p.read_text()) for p in sorted(args.window.glob('task-*/OUTCOME.json'))]
    # Planning examples, not estimates of a DCP treatment effect or universal floor.
    curve = {str(n): exact_power(n, 0.075, 0.025) for n in (50, 100, 200, 400, 800)}
    print(json.dumps({'paired_primary': summarize(window['schedule'], results), 'paired_second_rerun_descriptive': summarize(window['schedule'], results, rerun=2), 'power': {'alternative_p01': .075, 'alternative_p10': .025, 'difference': .05, 'discordance': .1, 'alpha_two_sided': .05, 'target_power': .8, 'curve': curve}}, indent=2))

if __name__ == '__main__': main()
