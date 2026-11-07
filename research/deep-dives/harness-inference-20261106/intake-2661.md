# vCache: Verified Semantic Prompt Caching

**Intake**: intake-2661 · **Verification**: dive-verified · **Read depth**: FULL · **Source**: https://arxiv.org/abs/2502.03771

## What the dive found

2026-11-06 Stage-2 dive (read_depth FULL; arXiv 2502.03771v5, ICLR 2026, 28 pages). Claim 1 confirmed; claim 2 OVERTURNED (the budget is on the cache's aggregate output, not on the skip - the guarantee is bought by exploring, i.e. by sometimes NOT skipping, so per-hit error is roughly delta/hit-rate: about 2.2% at delta=0.01 in their own table); claim 3 OVERTURNED as a joint attribution (12.5x is SemCacheCombo, 26x is SemCacheLMArena, and section 5 merges them while F.2 contradicts it); claim 4 narrowed (a marginal bound conditional on the observed prompt set, with an implementation that uses a 1-D band with gamma pinned and a flat-prior credible interval presented as confidence). The guarantee is label-hungry: the best-labelled entries had 42 and 33 observations after 60,000 prompts, and at n->0 the method explores and caches nothing. Applicability to EPYC: exact prefix caching satisfies the guarantee trivially and needs none of this; prompt-semantic caching is the applicable case; action omission cannot inherit it because an omitted call has no counterfactual label.

## Claims and corrections

- claim 0: **unaffected** — Confirmed at mechanism level: a per-cached-entry sigmoid fit by online MLE, versus static thresholds that carry no guarantee (Table 3 labels only LD3/vCache as providing guarantees). Precision: the guarantee is produced by the threshold PLUS a randomized exploration draw, so 'learned threshold' is necessary but not sufficient.

- claim 1: **overturned** — The error budget attaches to the CACHE, not to the skip. Definition 4.1 bounds the marginal probability that the cache returns a correct answer and pays for it by exploring (running the full call with probability tau); no per-skip false-positive bound exists. The paper's own Table 2 arithmetic (delta=0.01, 18.1% hit, 0.4% total error) implies about 2.2% of cache-served answers were wrong, i.e. per-hit error is roughly delta/hit-rate.

- claim 2: **overturned** — Numbers are verbatim but the joint attribution is wrong: 12.5x is SemCacheCombo (F.2) and 26x is SemCacheLMArena (F.3); section 5 merges both onto LMArena, contradicting F.2, and they are different points on a Pareto frontier. No single configuration delivers both. Weaker reported operating points: 18.1-40.2% hit at 0.4-1.4% error, and vCache is more conservative than baselines below a 1.5% bound.

- claim 3: **narrowed** — The guarantee is a per-prompt marginal expected-correctness bound conditional on the observed prompt set, not a per-skip false-positive rate and not a high-probability statement over the data distribution. Assumptions: i.i.d. prompts and a correctly specified sigmoid family. The implementation does not meet the proof's own premise: Lemma C.2 needs a joint band on (t, gamma) but only t gets a band and gamma is plugged in at its point estimate, and the band is a flat-prior credible interval presented as a confidence interval. Calibration is label-starved: the best-labelled entries had 42 and 33 observations after 60,000 prompts.


## Anchors

intake-2661 carries 11 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
