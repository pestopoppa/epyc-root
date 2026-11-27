# Adaptive LLM Routing under Budget Constraints

[Primary source](https://arxiv.org/abs/2508.21141v2) · intake-3023 · 2026-11-27

PILOT combines a preference-prior LinUCB (pretrained projections and model embeddings from ChatArena pairwise preferences, fit to selected-arm feedback) with a separate online multi-choice knapsack allocator. The allocator observes scores and estimated token cost, gates on minimum value/cost rising with spent-budget fraction, and selects the highest-scoring admissible model. It divides a known Q-request horizon into count-based bins with unused funds carried forward. Appendix C.2 falls back to free budget per remaining query if no arm clears the threshold; it terminates if no arm fits. Output token cost uses a fixed mean per model from tuning samples. Experiments replay RouterBench across 11 candidate LLMs, with 1000 tuning samples and a 10:1 learning/deployment split. Learning is unbudgeted, and the same allocator wraps all learned scorers for Figure 3. Full PILOT achieves 93% of GPT-4 performance at 25% of its cost on the multitask benchmark, and 86% at 27% on MMLU. The allocator-only Table 2 wins 3/4 budgets against retrospectively tuned price P−λC (at $1.00 PILOT 0.7240 vs 0.7265). Routing time Table 3 gives 65 ms on Instructor-XL and 239 ms on OpenAI embedding versus 2.5s GPT-4; adjacent prose reverses which latency yields ~38× vs ~10× speed ratios. No actual arrival-time queue, occupancy, redeployment, SLO or client runtime correction measured. CoordRoute’s Appendix F reports a minimum 11.04% advantage over a same-score knapsack threshold across 21 replay budgets, but uses training percentile bounds and expected-arrivals fallback, not the full preference-prior PILOT pipeline.

Read §§2–5 including Tables 2–3 and Figures 3–4 captions, Limitations, and Appendix C.2 allocation algorithm and D.1 comparator notes. Remaining mathematical proofs, adjacent supplementary results and full references not read.

## Evidence

- The paper divides a fixed-length sequence into budget bins and carries unused budget forward. [§2.2.3 online cost policy (#S2.SS2.SSS3)](https://arxiv.org/html/2508.21141v2)
- The allocator consumes scores from a separate ranker, allowing an allocator-only comparison with shared scores. [§3.2 deployment cost estimate (#S3.SS2)](https://arxiv.org/html/2508.21141v2)

## Scope and local transfer



Include allocator-only PILOT threshold with shared EPYC score and resource accounting inputs as a low-complexity control beside fixed price, dual pacing and CoordRoute lookahead. Record if using native known-count bins or CoordRoute’s forecast-count adaptation. CPU modeling prices active DDR/NUMA/slot time; MI210 modeling prices warm residency, batching and contention. Keep bandit updates as a different decision requiring an actual chosen-arm reward stream.

Per-request limits and offline routing snapshots cannot by themselves compare future contention at equal aggregate service cost. Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals.

## Sources surfaced

No additional decision-changing source identified.
