# NI05-51 — OBS-10 current-consumer audit (2026-10-05)

Completed a read-only audit of OBS-10, “Two E8 operator ratifiers gate on an argv
pattern.” The finding is historical operator-artifact scope; no active autonomous or
in-process non-inference consumer remains to repair.

The direct authority is [`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json): it retires the E8 chain and re-anchors quality-baseline obligations to applying or publishing a baseline, invalidating an in-flight baseline, or promotion. The current campaign restatement in [`CURRENT-CAMPAIGN.md`](../../handoffs/active/CURRENT-CAMPAIGN.md) likewise says the former blanket E8 gate is retired and gates bind at promotion, not discovery.

The two ratifier files still contain the noted process-pattern checks:
`artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh:23-25` and
`artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.sh:26-28`. The related
retired E8 rearm script also retains checks at
`artifacts/operator/rearm_e8_autopilot_20260726.sh:40-41`. These are historical human-only
operator transactions, not running observers or current in-process gates. The newer
`artifacts/operator/ratify_v9_cpu_bench_era_advance_20260811.sh:47-53` uses the autopilot
lock instead of a process-pattern probe.

The [`operator_ratifier_autopilot_gates` registry entry](../../scripts/coordination/observer_registry.json)
already marks the ratifiers `exempt` as one-shot human-reviewed artifacts and records
the same sibling relationship. The main session dispositioned OBS-10 as closed for
active-consumer scope under OP-19 while retaining that historical finding and registry
entry.

This audit made no runtime or process probe, pane observation, operator-artifact
mutation, or new ratification. It does not assert any live process or session state.
