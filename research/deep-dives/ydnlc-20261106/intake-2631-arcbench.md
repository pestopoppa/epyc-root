# intake-2631 — ARCBench (arXiv 2611.03223v1)

**Dive date**: 2026-11-06 · **Read depth**: FULL · **Source revision**: 2611.03223v1 (2026-11-02)
**Verdict**: dive-verified; claims 0 and 2 narrowed.

## Method

ARCBench extends the open-source **pi** agent harness; a tool-calling loop lets violations be graded from the
recorded tool-call trace, independent of what the compacted summary says. Caveat: tools are never executed (each
call gets a canned result), so it grades attempted calls, not side effects. 17 OWASP-mapped cases across four
violation types; models DeepSeek-V4-Flash, GLM-5.3-Flash, Qwen3.7-Flash, GPT-Luna as agent/compactor; seven
generative and three selective strategies.

## Results

- With full history, 8.1% of runs violate. After compaction, 70.1% of runs retain the rule and **21.1% of those
  still violate — 2.6×**. Rules are rarely deleted outright (3.0% absent).
- Among compaction-added violations, approval is the plurality (**45.9%**), not a majority: 27.0% never refer to
  the rule, 21.6% acknowledge it and proceed. Half the failure is omission/override, not permission-seeking.
- Budget collapse: at 200/300-token summaries, violation reaches 47.1%/50.0% with ≥95.1% rule loss.
- **No arm restates the rule in the system prompt after compaction** — untested. The only strategy below
  baseline is an instruction to the *compactor* to retain rules (Pi+RP, 9.0% vs 11.9%). An independent
  maintainer A/B on Hermes found prompt-side restatement null (20.7%→17.3%, z=0.99).

## EPYC relevance

This is the sharpest result for a governance-heavy harness: retention is not compliance. Our operating rules
(destructive-command bans, kill-only-captured-PIDs, single-writer outbox, no subagent index writes) are prose in
the transcript, and our only in-tree miss detector is inverted and cannot fire on destroyed content.

## Actionables (ledger)

| Action | Owner | Disposition |
|---|---|---|
| Add a rule-retention + retained-rule-compliance co-metric with deterministic tool-call predicates | context-and-token-economy.md (CF-AB-1) | immediate (design text) |
| Hard gate: no compaction enablement without passing that probe at ≤ baseline + margin on the serving model | context-and-token-economy.md | immediate clause / trigger execution |
| Inventory prose-only vs harness-enforced rules; move high-stakes rules into deterministic deny lists | agents/shared/OPERATING_CONSTRAINTS.md + opencode config | probe |

## Dive-surfaced sources

NousResearch/hermes-agent issue #149881 (independent negative A/B); Governance Decay 2606.22528 (wave 2);
Lost in Context Compaction 2608.11242 (wave 2); TRACE 2608.06503 (wave 2).
