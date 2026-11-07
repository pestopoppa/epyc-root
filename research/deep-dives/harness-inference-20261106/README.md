# Harness and inference intake — 2026-11-06

Twelve Stage-2 dives from three submitted sources and nine expansion entries, run in four waves.

| Entry | Source | Verification | Read depth |
|---|---|---|---|
| intake-2650 | T3 Code — provider-agnostic agent harness control surface (server + we | dive-verified | FULL |
| intake-2651 | Foundry Local — embeddable ONNX Runtime on-device inference runtime wi | dive-verified | FULL |
| intake-2652 | HarnessMM: Recursive Self-Improvement for Harness Token Efficiency | dive-verified | FULL |
| intake-2653 | Handoff Debt: The Rediscovery Cost When Coding Agents Take Over Interr | dive-verified | FULL |
| intake-2654 | ACP Registry — machine-readable registry of agents implementing the Ag | dive-verified | PARTIAL |
| intake-2655 | Durable Execution for Agent Runtimes: Workflow Engines, Replay, and Re | dive-verified | PARTIAL |
| intake-2656 | ActionEngine: From Reactive to Programmatic Web Agents via State Machi | dive-verified | FULL |
| intake-2657 | Reuse, Rewrite, or Reject: Evidence-Constrained Trace Reuse for Repeat | dive-verified | FULL |
| intake-2658 | When Valid Tool Calls Change Meaning: Formation-Consistent Dispatch fo | dive-verified | FULL |
| intake-2659 | HARBOR: Automated Harness Optimization | dive-verified | FULL |
| intake-2660 | CORTEX: A Verified Experience Layer for Generalist Agents | dive-verified | FULL |
| intake-2661 | vCache: Verified Semantic Prompt Caching | dive-verified | FULL |

## Cross-cutting finding

Harness-level savings are easy to over-attribute. HarnessMM's headline is mostly context shrink; ActionEngine's 3.2x is a single hosted-API mean with an unstable revision history; HARBOR ties the manual peak inside a corrected noise floor; CORTEX's reuse lowers rule evaluations while raising median latency; vCache bounds the cache, not the skip. The plan therefore spends immediate work on soundness and measurement contracts and gates every inference-spending experiment behind a trigger.


Plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
