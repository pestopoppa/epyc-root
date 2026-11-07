# ActionEngine: From Reactive to Programmatic Web Agents via State Machine Memory

**Intake**: intake-2656 · **Verification**: dive-verified · **Read depth**: FULL · **Source**: https://arxiv.org/abs/2602.20502

## What the dive found

2026-11-06 Stage-2 dive (read_depth FULL; arXiv 2602.20502v2, 19 pages plus v1 read for the revision delta). Claim 1 confirmed with a model-call qualifier (1.5-3.5 calls/task remain), claim 2 narrowed to a design claim (the Patcher is disabled in every evaluation run), claim 3 narrowed on both ratios. The transferable quantities are calls/task (14.7 -> 2.9) and input tokens (390k -> 29k), not the 3.2x wall-clock, which is a single-attempt mean against a hosted API; v1 reports the same Reddit tasks at 2x not 6.6x. Cost decomposes as 2.5x architecture x 3.2x prefix caching (Table 2b), so most of the '8x' is a price-list effect our own prefix cache already supplies. Authoring is amortised only over 39-101 tasks per application, with warm-up and engineering excluded, and Table 2(a) and Appendix C.1 disagree on the GitLab crawl cost by ~6x ($5 vs $29.5). The self-healing half has no measurement at all: no drift event, no repair-success rate, no rollback. Second-reader pass (2026-11-06): the 7.49x/7.67x cost ratios are dive arithmetic from the printed endpoints, not a quoted figure; the 3.2x prefix-caching factor is anchored at section 5.3 Table 2(b).

## Claims and corrections

- claim 0: **narrowed** — Confirmed, with a qualifier on 'no further planning calls': true of the planner, not of the model. 1.5-3.5 calls/task remain (task-weighted 2.9) from an in-program LLM helper and a state-filter call that fires above 300 operations. Parameter binding is deterministic against the execution context, not a model call.

- claim 1: **narrowed** — Write-back is real, but the condition is never tested: the Patcher is disabled for all 655 evaluation tasks, the only write-back is a warm-up over incomplete (not changed) memory, and there is no drift, rollback or poisoning experiment. Treat as a design claim, not a measured capability.

- claim 2: **narrowed** — 3.20x latency is exact (87s -> 27s, task-weighted mean of ONE attempt per task, no p50/p95, no repeats, no host description). Cost is 7.49x task-weighted / 7.67x on the paper's rounded endpoints, not 8x, and Table 2(b) decomposes it as 2.5x architecture x 3.2x layered prefix caching. v1 of the same paper reports the same 106 Reddit tasks at 2x, so wall-clock is the unstable number while quality is stable (95.0% in both revisions).


## Anchors

intake-2656 carries 9 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
