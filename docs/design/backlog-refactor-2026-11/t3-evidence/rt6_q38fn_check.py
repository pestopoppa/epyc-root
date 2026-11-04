#!/usr/bin/env python3
"""CAP-01 RT-6, Q38FN share: bit-exact replay check + DI-081 rule table (zero inference, numpy only).
Stop rule (before computing): re-run the filed, unchanged scripts/benchmark/moe_routing/placement_replay.py (--calib same and --calib cross,
default seed 3, all layers) on the stored RT-1 Q38FN traces; stop when the 'configs' trees of all 3 domains agree with the filed
placement_replay_{same,cross}.json leaf-for-leaf (max abs float diff reported), then tabulate the box's rule per config.
Usage: rt6_q38fn_check.py RECOMPUTED_DIR OUT.json"""
import json, sys
FILED = '/mnt/raid0/llm/epyc-inference-research/data/moe-routing-rt1-q38fn-20261023'
def leaves(x, y, path, st):
    if isinstance(x, dict):
        if set(x) != set(y): st['bad'] += 1; return
        for k in x: leaves(x[k], y[k], path + '/' + k, st)
    elif isinstance(x, list):
        if len(x) != len(y): st['bad'] += 1; return
        for i, (p, q) in enumerate(zip(x, y)): leaves(p, q, f'{path}[{i}]', st)
    else:
        st['n'] += 1
        if isinstance(x, float): st['max'] = max(st['max'], abs(x - y))
        elif x != y: st['bad'] += 1
out = {'schema': 'brf-t3/rt6-q38fn-check/1', 'filed_dir': FILED, 'proxy': 'Qwen3.8-Flash-Next UD-IQ4_XS qwen4exp 48 layers 512 experts top-10 (PROXY for DS41; not DS41)', 'calib': {}}
for calib in ('same', 'cross'):
    a = json.load(open(f'{sys.argv[1]}/rt6-{calib}/placement_replay_{calib}.json')); b = json.load(open(f'{FILED}/placement_replay_{calib}.json'))
    st = {'n': 0, 'bad': 0, 'max': 0.0}
    for x, y in zip(a, b):
        assert x['domain'] == y['domain'] and x['layers'] == y['layers'] == 48
        leaves(x['configs'], y['configs'], x['domain'], st)
    table = {}
    for x in a:
        for k, c in x['configs'].items():
            d = c['decision']; table.setdefault(k, {})[x['domain']] = {'ratio_realizable': round(d['ratio_practical'], 3), 'best_realizable': d['best_practical'], 'ratio_idealized_dispatch': round(d['ratio_idealized_dispatch'], 3), 'ratio_bound': round(d['ratio_bound'], 3), 'best_bound': d['best_bound'], 'contiguous_vs_null_random': [round(c['arms']['contiguous']['max_over_mean'], 3), round(c['arms']['null_random']['max_over_mean'], 3)]}
    rule = {}
    for k, v in table.items():
        rule[k] = {'realizable_ge_1.10_domains': [d for d, r in v.items() if r['ratio_realizable'] >= 1.10], 'bound_ge_1.10_domains': [d for d, r in v.items() if r['ratio_bound'] >= 1.10]}
    out['calib'][calib] = {'leaves_compared': st['n'], 'mismatches': st['bad'], 'max_abs_float_diff': st['max'], 'table': table, 'di081': rule}
# Box rule as written: close negative iff even the oracle/LP BOUND fails >=1.10 on >=2 workloads
fails = {k: [d for d, r in v.items() if r['ratio_bound'] < 1.10] for k, v in out['calib']['same']['table'].items()}
out['box_rule_bound_fails_on_ge2_workloads'] = {k: len(v) >= 2 for k, v in fails.items()}
out['box_rule_closes_negative_on_q38fn'] = any(out['box_rule_bound_fails_on_ge2_workloads'].values())
json.dump(out, open(sys.argv[2], 'w'), indent=1, sort_keys=True)
for c in ('same', 'cross'):
    o = out['calib'][c]; print(c, 'leaves', o['leaves_compared'], 'mismatch', o['mismatches'], 'maxdiff', o['max_abs_float_diff'])
    for k, r in o['di081'].items(): print('  ', k, 'realizable>=1.10:', r['realizable_ge_1.10_domains'], 'bound>=1.10:', r['bound_ge_1.10_domains'])
print('close-negative on Q38FN bound:', out['box_rule_closes_negative_on_q38fn'])
