# Routing & Optimization Index — History Through 2026-06-19

Historical ledger only; current routing-domain dispatch lives in `../active/routing-and-optimization-index.md`.

This file records the 2026-06-19 wrap-up pruning of the active routing index. The active index had accreted completed implementation narration and research-intake rollups that duplicated owning handoffs and progress logs, making the dispatch surface harder to scan.

## Pruned From Active Index

| Source section | Disposition | Durable source after pruning |
|----------------|-------------|------------------------------|
| `2026-06-14 Sidecar Notes` | Removed from active index. | Commit history plus `progress/2026-06/2026-06-14.md` and the owning N11/N11a/evidence-plane handoffs. |
| Historical checked-off P0-P5/P8/P10/P11/P15/P17/P18/P19/P20/P21/P22/P23/P24/P25/P26 task narration | Replaced by a compact live dispatch table. | Owning active handoffs for open work; completed/archived handoff ledgers and daily progress logs for closed work. |
| Research intake appendices | Replaced by research-derived backlog rollups pointing at owning handoffs. | `research/intake_index.yaml`, deep-dives, and owning active handoffs. |

## Exact Pre-Prune State

The exact pre-prune routing index content remains recoverable from `epyc-root` commit `d3484cf` and earlier root checkpoints. This archived ledger intentionally preserves the disposition and pointers instead of copying hundreds of lines of duplicate completed narration back into the active tree.

## Open Work Still Active

The pruned active index keeps live queues for evidence-plane readiness, stack-change/model-stack SSoT, X-MAS constrained A/B, routing classifier/canary decisions, dynamic stack/placement measurements, bulk inference windows, delegation/edit harness work, trace/HLE/BSV/URE work, research-derived routing spikes, and web/search/PromptForge tails.
