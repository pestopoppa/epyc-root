#!/usr/bin/env python3
"""Paired net-regression reading of the Q38-T10.1 serving gate (main's proposed alternative).
Per role: b = regressions (base pass, spec fail), c = gains (base fail, spec pass) over clean prompts.
Net rate = (b - c) / n, 95% CI = Newcombe (1998) method 10 paired-proportion score interval + a seeded bootstrap check.
Exact McNemar = two-sided binomial test of b vs c on b+c discordant pairs (p=0.5); one-sided P(b' >= b) also given.
usage: mcnemar_net.py RESULT.serving_gate.json
"""
import json, math, random, sys
from math import comb, sqrt

def binom_two_sided(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(0, k + 1)) / 2**n
    return min(1.0, 2 * p)

def binom_upper(b, c):   # P(X >= b | n=b+c, p=.5)  (evidence that regressions exceed gains)
    n = b + c
    return sum(comb(n, i) for i in range(b, n + 1)) / 2**n if n else 1.0

def wilson(x, n, z=1.959964):
    if n == 0: return (0.0, 1.0)
    p = x / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)

def newcombe_paired_diff(b, c, n, z=1.959964):
    """CI for p_b - p_c where p_b=b/n (regress), p_c=c/n (gain) share the same n paired subjects (Newcombe method 10)."""
    p1, p2 = b / n, c / n   # marginal: base fail->? use discordant-cell form
    # Newcombe: with a=both pass? use the standard form on marginals p1=(a+b)/n, p2=(a+c)/n; diff=p1-p2=(b-c)/n.
    # Reconstruct from cells: only b,c,n known; the concordant split matters only through phi. Use the table form via marginals:
    return None

def newcombe(a, b, c, d, z=1.959964):
    """2x2 paired table: a=both+, b=base+/spec-, c=base-/spec+, d=both-. diff = P(base+) - P(spec+) = (b-c)/n (= net regression)."""
    n = a + b + c + d
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n); l2, u2 = wilson(a + c, n)
    den = (a + b) * (c + d) * (a + c) * (b + d)
    phi = 0.0 if den == 0 else ((a * d - b * c) / sqrt(den))
    if den == 0 or phi < 0: phi = max(phi, 0.0) if den else 0.0
    d_ = p1 - p2
    lo = d_ - sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2))
    hi = d_ + sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2))
    return d_, lo, hi

def boot(rows, iters=20000, seed=7):
    rnd = random.Random(seed); n = len(rows); v = [1 if r == 'REG' else -1 if r == 'GAIN' else 0 for r in rows]
    s = sorted(sum(rnd.choice(v) for _ in range(n)) / n for _ in range(iters))
    return s[int(0.025 * iters)], s[int(0.975 * iters)], s[int(0.95 * iters)]

def main(path):
    R = json.load(open(path)); out = {}
    for key, role in R.items():
        if not isinstance(role, dict) or 'rows' not in role: continue
        rows = [r for r in role['rows'] if r.get('outcome') != 'EXCLUDED_TRUNCATED']
        n = len(rows); b = sum(r['outcome'] == 'REGRESSION' for r in rows); c = sum(r['outcome'] == 'GAIN' for r in rows)
        a = sum(r['outcome'] == 'SAME_PASS' for r in rows); d = sum(r['outcome'] == 'SAME_FAIL' for r in rows)
        net, lo, hi = newcombe(a, b, c, d)
        bl, bh, b95 = boot(['REG' if r['outcome'] == 'REGRESSION' else 'GAIN' if r['outcome'] == 'GAIN' else '' for r in rows])
        out[key] = {'script_verdict': role.get('verdict'), 'script_regression_upper_95_one_sided': role.get('regression_upper_95_one_sided'),
                    'n_clean': n, 'regressions_b': b, 'gains_c': c, 'both_pass': a, 'both_fail': d,
                    'discordant': b + c, 'net_regressions_minus_gains': b - c, 'net_rate': (b - c) / n if n else None,
                    'net_rate_95ci_newcombe10': [lo, hi], 'net_rate_95ci_bootstrap': [bl, bh], 'net_rate_one_sided95_upper_bootstrap': b95,
                    'mcnemar_exact_two_sided_p': binom_two_sided(b, c), 'binom_one_sided_p_regress_gt_gain': binom_upper(b, c),
                    'token_identical_clean': role.get('token_identical_clean'), 'aa_identical': role.get('aa_identical'),
                    'alt_reading': ('NO_NET_REGRESSION (p>=0.05 and CI upper < 0.05)' if (hi < 0.05 and binom_upper(b, c) >= 0.05)
                                    else 'NET_REGRESSION_SIGNIFICANT' if binom_upper(b, c) < 0.05 else 'INCONCLUSIVE (CI upper >= 0.05)')}
    print(json.dumps(out, indent=1)); return out

if __name__ == '__main__': main(sys.argv[1])
