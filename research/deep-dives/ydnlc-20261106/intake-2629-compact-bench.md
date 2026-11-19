# intake-2629 — Compact-Bench (arXiv 2610.31710v2)

**Dive date**: 2026-11-06 · **Read depth**: FULL · **Source revision**: 2610.31710v2 (2026-10-28)
**Verdict**: dive-verified; claim 2 narrowed.

## Method

Paired PRE/POST continuations from the *same* repository snapshot: PRE continues with the full history, POST
with only the summary. Task Preservation is judged by the repository's FAIL_TO_PASS tests, so damage is a lost
full-history success, not an aggregate score difference. Corpus: 35 SWE-bench repairs, 146 sessions (143 real +
3 synthesised), 106 production chains, 224 boundaries. Only 24 of 35 repairs enter the comparison; every
headline denominator is 22 validated PRE-pass cases. Selection deliberately biases easy (single test file,
small gold patch, few FAIL_TO_PASS).

## Results

- Across 14 summariser backbones, stable damage ranges **5%–64%** of the 22 full-history successes. Claude Opus
  4.8 preserves the most (1/22 damaged); DeepSeek-Flash the most (14/22). 120/126 first-round damaged pairs
  confirm at K=3.
- LLM summaries retain at most **16.0%** of recurring details vs **79.1%** for mechanical extraction; production
  summaries retain 15.7% at the first boundary.
- Failures recur across methods: one repair is damaged by 13/14 backbones, another by all 5 prompts.

## The correction that matters

The 79.1% mechanical figure is **not a deployable compaction method**. It is the same deterministic extractor
that defines the scoring reference (`A(T)`), emitting at most 40 values per kind, scored by case-sensitive
substring membership. It was never run through Task Preservation; no Table 2/3 cell is a mechanical arm. The
paper's own wording is "the comparison quantifies how much recurring structured information survives extraction
versus generated summarization". Do not cite 79.1% as evidence that mechanical compaction preserves a summary.

All 14 summarisers are hosted API models — none is a local GGUF model. The local implication is inferred.

## Actionables (ledger)

| Action | Owner | Disposition |
|---|---|---|
| Prefer deterministic stubbing + an evidence ledger over free-form prose at the boundary; do not adopt mechanical-extraction-as-summary on the 79.1% number | context-and-token-economy.md (CF-3c) | knowledge-only |
| Fix the inverted reference-miss detector before any retention probe | context-and-token-economy.md | immediate |
| Cheap CPU-only probe: replay stored boundaries, score literal-atom retention of our summary vs a mechanical extractor, on Qwen3.6-35B-A3B and Qwen3.8-27B | context-and-token-economy.md (CF-3c) | probe |
| If retention < 20% at first boundary, escalate to an A7 searchable-log requirement | context-and-token-economy.md | trigger |

## Dive-surfaced sources

None new. Convergent in-lane evidence: intake-274 (masking ≥ summarisation), intake-869 (summarisation
marginal, sign-inconsistent).
