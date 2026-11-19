# Measurement sufficiency audit — 2026-11-02

The operator requested an audit of active handoffs for opportunities to make decisions without running measurements longer than necessary. This is a targeted sample, not an exhaustive inventory or authorization to change existing gates. The reusable operational procedure is [measurement sufficiency](../../../docs/guides/agent-workflows/measurement-sufficiency.md); MEASUREMENT.md and applicable protocols remain authoritative.

| Example | Opportunity and limit |
| --- | --- |
| [RTG-58 KPF-64](../../../handoffs/active/kv-prefix-fork-and-paged-attention.md) | FB72 was stopped by the operator after 49 records. Its paired comparison is informative but selected, observational and mixes changes to RAM and idle-slot caching. F72 tests whether cache behavior holds under the larger allocation using a bounded exploratory monitor. Neither partial result silently completes a fixed gate. |
| [INF-12 Gate 2](../../../handoffs/active/delta-mem-reproduction.md) | The 7,342-record two-arm workload has a measured example of about 98 seconds per question. Preplan paired strata and decision-relevant looks or futility where the governing protocol permits; a partial base-only score is not the full gate. |
| [HIL-18](../../../handoffs/active/harness-improvement-loop.md) | Repeated task replays can be staged by task and a prespecified futility rule, while leaving unobserved task coverage open and preserving the required final test. |
| [CS-8.LEX2](../../../handoffs/active/conversation-stack.md) | Stage parameter exploration and reserve held-out evaluation; a promising or futile dev cell does not replace the final comparison. |
| [DS41-W5b](../../../handoffs/active/deepseek-v41-flash-evaluation.md) | Fixed A/A and paired requirements cannot be silently reduced after inspecting results. An early operational stop remains incomplete unless an authorized prospective protocol permits otherwise. |
| [PF1](../../../handoffs/active/mi210-big-model-and-acceleration-roadmap.md) | A small 8K pilot can inform whether to expand, but the full crossover gate requires its stated matrix, five repetitions, confidence intervals and later reversed-order replicate. A pilot failure is not a verdict for all shapes. |

## Feedback for the backlog-refactor proposal v5

Reference: `/mnt/raid0/llm/tmp/ws58-csh/backlog-refactor-proposal-20261102.md`, snapshot at `3ac825873dfb`; RTG-58 advanced subsequently. Recommendations for the owning session:

- Reconcile task identities and counts with current state before migration. The 927 are structurally executable candidates, not proof that each is still needed and launch-ready. The 761 inference count is over the 2,808 open tasks, not necessarily a subset of those 927.
- Assign EXP-01's executable KT gates to [INF-26](../../../handoffs/active/iqk-iquant-enablement.md), with tq3 as consumer; tq3 records that transfer.
- Give each pilot a decision, appropriate unit, coverage, interim looks, uncertainty and stop/continue/inconclusive rule. In particular, EXP-04's three-run 8K pilot is a screen, not the full PF1 gate. EXP-01's 95% is the relevant throughput ratio, not a quality pass rate. Preserve protocol-mandated counts and distinguish pilot decisions from full acceptance.
- CAP-04 should generate at each budget unless equivalence of reused lower-budget completed generations is demonstrated for that comparison; retain truncation and metadata. Resume by identity must not silently conflate budgets.
- Clarify that provisional package status does not stop independent authorized evidence reuse, adjudication or preparation. Refresh the KEEP inventory wording to reflect markers since created; the two journal paths have a shared parent marker, whose treatment should be checked against the particular cleaner.

No proposal, KEEP marker, private evidence or trust-boundary document was edited in this audit.
