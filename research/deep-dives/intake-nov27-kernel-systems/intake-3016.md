# CoordRoute: Coordinated Multi-Model Routing for Maximum Compute-Budget Utility

[Primary source](https://arxiv.org/abs/2611.34161v1) · intake-3016 · 2026-11-27

Per-request prediction borrows historical scores from neighbors learned to minimize routing regret instead of text similarity. A cost-benefit curve from 128 recent requests values remaining window budget using the queue and forecast arrivals; each route includes future opportunity cost. During generation a cheap token/FLOP check at geometric checkpoints gates stronger inspection (default gamma 4); paid inspection may continue, drop or stop and restart original prompt on a stronger model. In pre-recorded-answer replay of 300 held-out UltraFeedback tasks assigned to Azure and BurstGPT timestamps, 21 budgets, 60 streams, 5-minute non-rollover windows, 3 model candidates, judges DeepSeek-V4.1-Flash and sensitivity GLM-5.3: mean per-arrival satisfaction 0.5672 vs best fixed CARROT 0.4778 (+18.72% relative, 95% CI 15.48–22.26%); +10.89% vs hindsight-paced CARROT. Completion 91.88% vs 80.13% for fixed CARROT; unstarted/dropped/truncated score zero. Figure 14 solver adds 10.88% over fixed-price version. Correction adds mean +3.72% over no correction across these replays; default inspection overhead 4.55% of modeled computation in three analysis scenarios. Solver 0.92 ms of 45.17 ms CPU-thread routing. §5.2 explicitly assumes instantaneous redeployment; no real-service SLO measurement, throughput/resource effects or locality contention. §6.5 varied model FLOP cost multipliers as a sensitivity check, not measured CPU/MI210 timing. Bounded targeted search surfaced primary baselines and restatements but no independent reproduction.

Read design, assumptions and experiments §§4–6, targeted captions and appendix tables/algorithm constraints; results are from HTML. Full related work/theory, appendix derivations and references not read.

## Evidence

- Trace replay uses a fungible FLOP budget and assumes instantaneous GPU redeployment. [§5.2, fixed GPU pools and redeployment (#S5.SS2.SSS0.Px3)](https://arxiv.org/html/2611.34161v1)
- On two replayed traces and 21 modeled budgets, CoordRoute yielded 18.72% higher per-arrival satisfaction than fixed CARROT. [§6.2, end-to-end performance (#S6.SS2)](https://arxiv.org/html/2611.34161v1)

## Scope and local transfer



Use decision-aware routing admission ledger rather than a second occupancy model. Replay a planner-only policy against fixed and paced baselines with replayed arrival/load, queue wait, latency and throughput constraints; price actual worker occupancy, model swaps, prefix reuse/eviction and reserve for priority requests. CPU may spend largely memory bandwidth, with high latency/contended decoding; MI210 model residency and batching drive queue service rates. In-flight restart/drop has wasted work and client/SLO semantics, and suits a separate follow-on only if measured gains justify it.

Per-request limits and offline routing snapshots cannot by themselves compare future contention at equal aggregate service cost. Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals.

## Sources surfaced

- https://arxiv.org/abs/2508.21141 — PILOT (Adaptive LLM Routing under Budget Constraints) is a lighter online-knapsack/pacing baseline; compare its costs on live constraints. Exact ID absent from lane index.
