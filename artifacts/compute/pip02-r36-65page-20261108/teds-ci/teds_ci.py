#!/usr/bin/env python3
"""PIP-04 page-clustered paired bootstrap of (paddle TEDS - ODL TEDS).
Operator 2026-11-10: 0.20 margin, 10k resamples, seed 20261110. Pure file work."""
import json, sys, os, numpy as np
here = os.path.dirname(os.path.abspath(__file__))
SEED, B, MARGIN = 20261110, 10000, 0.20
o = json.load(open(f"{here}/odl-Lfinal_quick_match_table_per_table_TEDS.json"))
p = json.load(open(f"{here}/paddle-Lfinal_quick_match_table_per_table_TEDS.json"))
assert set(o) == set(p), "table key sets differ"
keys = sorted(o)
pages = {}
for k in keys:
    page = k.rsplit("_[", 1)[0]
    pages.setdefault(page, []).append(p[k]["TEDS"] - o[k]["TEDS"])
names = sorted(pages)
arrs = [np.array(pages[n]) for n in names]
sums = np.array([a.sum() for a in arrs]); cnt = np.array([len(a) for a in arrs])
allv = np.concatenate(arrs)
rng = np.random.default_rng(SEED)
idx = rng.integers(0, len(names), size=(B, len(names)))
means = sums[idx].sum(1) / cnt[idx].sum(1)
lo, hi = np.percentile(means, [2.5, 97.5])
res = dict(seed=SEED, resamples=B, margin=MARGIN, n_tables=len(keys), n_pages=len(names),
  paddle_mean_teds=float(np.mean([p[k]["TEDS"] for k in keys])),
  odl_mean_teds=float(np.mean([o[k]["TEDS"] for k in keys])),
  mean_diff=float(allv.mean()), ci95_lower=float(lo), ci95_upper=float(hi),
  boot_mean=float(means.mean()), frac_tables_paddle_better=float((allv>0).mean()),
  verdict="PADDLE_WINS" if lo > MARGIN else "NOT_ESTABLISHED",
  rule="PaddleOCR-VL wins iff lower 95% CI bound of (paddle TEDS - ODL TEDS) > 0.20; percentile CI, page-clustered resampling, statistic = mean of per-table diffs in resampled pages",
  source_run="pip02-r36-english-run-20261107b")
json.dump(res, open(f"{here}/teds_ci_result.json", "w"), indent=2)
print(json.dumps(res, indent=2))
