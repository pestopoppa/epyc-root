# Dive — cachecomp — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2607.15516v1", retrieved: "2026-11-24", sha256: "889b0245df34"}

authors: Yan Song (PayPal Inc.); arXiv v1

## 1. Stage-1 fields
- title: Cache-Aware Prompt Compression: A Two-Tier Cost Model for LLM API Caching. author: Yan Song (PayPal Inc.), arXiv 2607.15516v1.
- categories: context_management, cost_aware_routing, kv_cache. novelty: medium. relevance: medium for the form, low for numbers.
- credibility_score: 1 (not peer-reviewed 0; <=12 months +1; single industry author, no bias flag; no independent corroboration).
- verdict: adopt_patterns.

## 2. Key claims
0. Cost model with measured hit rate and a provider-agnostic crossover rho_cross(r)=(alpha-1/r)/(alpha-beta) - CONFIRMED (anchor 0).
1. Crossover table (0.652/0.797/0.870/0.942 at r=2/3/4/6) vs plateau ~0.89 gives compression > cache-only at r>=6 - CONFIRMED but API-specific (anchor 1). I recomputed (1.25-1/r)/(1.15): r=2 0.652, r=6 0.942. Matches.
2. "Sharp threshold near 3,500 tokens" - PARTIAL: sweep brackets 2k-4k; 3,500 is adopted for modelling (anchors 2,3). Abstract plateau 0.83 vs body plateau 0.89 at 2.4k tokens, N=50.
3. Invalidation cost depends on the mutated fraction of the cached prefix (+40.1% on tau-bench retail; 100% hit rate on the 94k tools-array workload) - CONFIRMED (anchor 4).
4. All numeric values are Sonnet 4.6 May-2026 snapshots - CONFIRMED by authors (anchor 5).

## 3. Reported results
16/16 LongBench-v2 configs CAPC cheapest (mean savings 49%/64%/90% vs cache-only/query-aware/vanilla); tau-bench retail 36/50 = vanilla, query-aware +40.1%; enterprise 94k-token prefix -51.7% at r=3. Anthropic API, total spend $98.96. Not local.

## 4. Performance-principles table (re-expressed in seconds per device)
Local mapping (derived by me, not in source): c_r -> ~0 (slot/prompt-cache reuse), c_w = p_in -> prefill seconds per token t_p(device), so alpha=1, beta~0 and rho_cross(r)=1-1/r (r=2: 0.50; r=3: 0.667; r=6: 0.833). rho -> p*/T, with p* the longest common prefix with a resident slot. The model lacks a term for decode attention over a shorter context (saving s_d(ctx) per generated token), which locally can favour compression even at rho above the threshold.
| Principle | MI210 gfx90a | Zen 5 EPYC | Reason |
|---|---|---|---|
| Crossover on reuse fraction | YES | YES | Seconds form: cache-and-keep beats compress-and-re-prefill when t_p*(T-p*) + decode(ctx) < t_p*(T/r) + decode(ctx/r)-style; needs measured prefill s/token and ms/token-vs-context slope per device |
| Prefix-strict invalidation, token-level | YES | YES | llama-server slot reuse is exact-prefix; any edit before the end re-prefills from p* |
| Hybrid/GDN cannot shift KV | YES (applies) | YES (applies) | recurrent state cannot be position-shifted (can_shift false, kv-cache-program.md:L644 @ f74b175), so a mutated middle region forces re-prefill from p* or the last checkpoint; strictly worse than API pricing suggests |
| Two tiers by prefix size (3,500 tokens) | NO | NO | provider cache architecture; llama.cpp slots have no size tier (checkpoint spacing is the nearest local analogue, uncited) |
| Mutated-fraction principle | YES | YES | compactions that rewrite only the tail keep p* high |

## 5. In-house state
KV-EVICT-COST-1 (kv-cache-program.md:L644 @ f74b175, unticked) already specifies predicted re-prefilled tokens T'-p* and a seconds model a + b x cells per device; this paper's rho is p*/T in that probe and its crossover is the break-even the probe's table is meant to emit. dmc5 ledger row 1 asks to extend that table with a DMC-5 row. No llama.cpp source touched.

## 6. Derived-actionables ledger
1. refines dmc5 row 1: Draft: "In the KV-EVICT-COST-1 break-even table add the column rho_cross(r) = 1 - 1/r in local seconds (t_p per device from existing prefill rows, ms/token-vs-context slope from existing context-slope rows) and mark each compaction design by its mutated-prefix fraction (tail-only vs middle rewrite)." Owner: kv-cache-program.md (KV-EVICT-COST-1 box; it is unticked, not frozen). Code/doc-only first (arithmetic over retained rows). Decision rule: report r* above which compress-and-re-prefill beats keep-and-reuse for each device at the roles' trajectory lengths; if the decode-slope saving alone exceeds the re-prefill seconds at the role's context, record 'compress wins regardless of rho'. Stop-on-answer when the table has both devices.
2. Decline: tier-preserving ratio bound r_max=floor(P/3500) or any 3,500-token threshold; reason: provider cache tier, no local analogue.
3. Decline: implementing CAPC-style cache_control; reason specific to entry: we have no per-token billing or cache_control API; exact-prefix slot reuse is already the behaviour.

## 7. Dive-surfaced sources
None. (graphify/capc_graphify_profiler.py is code for API workloads; would not change row 1.)

## 8. Contradiction / adversarial pass
Hit-rate step function rests on four prefix sizes; the abstract and body disagree on the plateau (0.83 vs 0.89); the implicit tools-cache finding contradicts the paper's own Section 3.1 (authors flag it); single provider and snapshot; restatement of API prices, not independent corroboration.

9. read_depth: PARTIAL. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.
10. artifact audit: clean (6 anchors verified).
