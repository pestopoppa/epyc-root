#!/usr/bin/env python3 -I
"""KPF-18.4: overlap-depth distribution + sparse checkpoint placement DP, from a llama-server verbose log.

No n_fork_tokens exists in served traffic (slot fork is off), so the overlap depth d of a request is
the longest common prefix with the slot it was routed to: d = sim_best * N (server 'selected slot by LCP
similarity' line; sim = lcp / n_prompt_tokens).  Zero-inference: log read + DP only.
"""
import re, sys, json, collections, bisect, statistics as S
R_SEL = re.compile(r'slot get_availabl: id\s+(\d+) \| task -?\d+ \| selected slot by LCP similarity, sim_best = ([\d.]+)')
R_NEW = re.compile(r'slot\s+operator\(\): id\s+(\d+) \| task (-?\d+) \| new prompt, .* task.n_tokens = (\d+)')
R_C = re.compile(r'slot\s+operator\(\): id\s+(\d+) \| task (-?\d+) \| cached n_tokens = (\d+), memory_seq_rm')
sel = {}; pend = {}; reqs = []
for line in open(sys.argv[1], errors='replace'):
    m = R_SEL.search(line)
    if m: sel[int(m.group(1))] = float(m.group(2)); continue
    m = R_NEW.search(line)
    if m:
        sid = int(m.group(1)); N = int(m.group(3))
        r = dict(N=N, sim=sel.pop(sid, 0.0), K0=None); pend[sid] = r; reqs.append(r); continue
    m = R_C.search(line)
    if m:
        r = pend.pop(int(m.group(1)), None)
        if r is not None: r['K0'] = int(m.group(3))
reqs = [r for r in reqs if r['K0'] is not None]
for r in reqs: r['d'] = int(round(r['sim'] * r['N']))
D = [r['d'] for r in reqs]; n = len(D)
pos = [d for d in D if d > 0]
out = dict(requests=n, with_overlap=len(pos), zero_overlap=n - len(pos))
# histogram in log2 buckets of overlap depth
b = collections.Counter()
for d in D:
    b['0' if d == 0 else '<=%d' % (1 << max(6, (d - 1).bit_length()))] += 1
out['hist'] = dict(sorted(b.items(), key=lambda kv: (kv[0] != '0', int(kv[0][2:]) if kv[0] != '0' else 0)))
out['d_quantiles_pos'] = [int(x) for x in S.quantiles(pos, n=10)]
# spike test: most common 512-token bin and +-5% of the modal value
bins = collections.Counter(d // 512 for d in pos); mb, mc = bins.most_common(1)[0]
out['modal_512bin'] = dict(start=mb * 512, mass_pct=round(100 * mc / len(pos), 1))
ds = sorted(pos)
def recompute(cps):
    cps = sorted(cps); tot = 0
    for d in D:
        i = bisect.bisect_right(cps, d) - 1
        tot += d - (cps[i] if i >= 0 else 0)
    return tot
base = sum(D)
def dp(M):
    xs = sorted(set(pos))
    # best[m][j]: min recompute of d<=xs[j] using m ckpts, last at xs[j]; classic 1D DP on distinct values
    cnt = collections.Counter(pos); w = [cnt[x] for x in xs]; L = len(xs)
    import itertools
    pre_w = [0] + list(itertools.accumulate(w)); pre_wx = [0] + list(itertools.accumulate(wi * x for wi, x in zip(w, xs)))
    def cost(i, j, c):  # points xs[i:j] served by ckpt at c (c<=xs[i])
        return (pre_wx[j] - pre_wx[i]) - c * (pre_w[j] - pre_w[i])
    INF = float('inf')
    f = [[INF] * (L + 1) for _ in range(M + 1)]; arg = [[0] * (L + 1) for _ in range(M + 1)]
    # f[m][j]: first j distinct values covered with m ckpts; first group served by 0 if m==0
    f[0][0] = 0
    for m in range(1, M + 1):
        for j in range(1, L + 1):
            for i in range(0, j):   # group xs[i:j] gets ckpt at xs[i]; prefix xs[:i] already covered
                v = (f[m - 1][i] if m > 1 or i == 0 else (cost(0, i, 0) if i else 0)) + cost(i, j, xs[i])
                if v < f[m][j]: f[m][j] = v; arg[m][j] = i
    # allow m ckpts <= M and uncovered prefix served from 0 for m==1 handled above
    return f[M][L] if L else 0
# simplified exact DP on a thinned grid (<=400 distinct candidate positions) for speed
import math
def dp_grid(M, grid):
    cps_best = None; best = math.inf
    L = len(grid)
    # f[m][k]: min total recompute of all d with the m-th ckpt at grid[k] covering d in [grid[k], next ckpt)
    ds_sorted = sorted(D)
    pw = [0]; 
    def seg(lo, hi, c):  # sum over d in [lo,hi) of d-c
        a = bisect.bisect_left(ds_sorted, lo); z = bisect.bisect_left(ds_sorted, hi)
        return sum(ds_sorted[a:z]) - c * (z - a)
    pre = [0]
    for x in ds_sorted: pre.append(pre[-1] + x)
    def seg2(lo, hi, c):
        a = bisect.bisect_left(ds_sorted, lo); z = bisect.bisect_left(ds_sorted, hi)
        return pre[z] - pre[a] - c * (z - a)
    INF = float('inf'); top = ds_sorted[-1] + 1
    f = [[INF] * L for _ in range(M + 1)]; par = [[-1] * L for _ in range(M + 1)]
    for k in range(L): f[1][k] = seg2(0, grid[k], 0)
    for m in range(2, M + 1):
        for k in range(L):
            for p in range(k):
                v = f[m - 1][p] + seg2(grid[p], grid[k], grid[p])
                if v < f[m][k]: f[m][k] = v; par[m][k] = p
    for k in range(L):
        v = f[M][k] + seg2(grid[k], top, grid[k])
        if v < best: best = v; kk = k
    cps = []; m = M; k = kk
    while m >= 1 and k >= 0: cps.append(grid[k]); k = par[m][k]; m -= 1
    return best, sorted(cps)
cand = sorted(set(pos)); step = max(1, len(cand) // 300); grid = cand[::step]
res = {}
for M in (1, 2, 4, 8):
    c, cps = dp_grid(min(M, len(grid)), grid)
    res['M=%d' % M] = dict(mean_recompute_tok=round(c / n, 1), reduction_vs_none_pct=round(100 * (1 - c / base), 1), ckpts=cps)
res['no_checkpoint(restart from 0)'] = dict(mean_recompute_tok=round(base / n, 1))
for U in (2048, 8192):
    cps = list(range(U, max(D) + 1, U))
    res['dense_every_%d' % U] = dict(mean_recompute_tok=round(recompute(cps) / n, 1), ckpts_per_slot_at_max_depth=len(cps),
        mean_ckpts_needed=round(S.mean(d // U for d in D), 2))
# policy checkpoint_at=[len(trunk)]: one ckpt at the modal depth
modal = mb * 512 + 256
res['single_at_modal_depth'] = dict(at=modal, mean_recompute_tok=round(recompute([modal]) / n, 1))
out['policies'] = res
# actual: what the server restored (first cached n_tokens) vs the true overlap
act = sum(max(0, r['d'] - r['K0']) for r in reqs)
out['actual_server_recompute_beyond_restore'] = dict(mean_tok=round(act / n, 1), frac_requests=round(sum(1 for r in reqs if r['d'] > r['K0'] + 16) / n, 3))
print(json.dumps(out, indent=1))
