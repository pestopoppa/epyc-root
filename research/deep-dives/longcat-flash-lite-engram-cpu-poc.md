# LongCat-Flash-Lite Engram-Family CPU POC

**Date**: 2026-05-25
**Status**: Negative Track A result, reporting closed 2026-06-12
**Linked handoff**: `handoffs/active/engram-conditional-memory.md`
**Full artifacts**: `/mnt/raid0/llm/epyc-inference-research/research/engram-spike/eval/`

## Bottom Line

LongCat-Flash-Lite Q4_K_M validates that n-gram-augmented MoE inference can run on EPYC CPU at production-relevant rates, but it does not displace any current production role on this stack.

Measured on EPYC 9655:

| Comparator | Decode | Sentinel Quality | Decision |
|---|---:|---:|---|
| LongCat-Flash-Lite Q4_K_M | 37.08 t/s | 21/39 = 53.8% | viable family, not deployable here |
| gemma4-26B-A4B Q4_K_M MTP (`worker_general`) | ~76.5 t/s | 26/39 = 66.7% | dominates LongCat on both axes |
| Qwen3.6-35B-A3B Q8 (`frontdoor`) | 25.17 t/s | not rerun in this gate | LongCat faster, but too weak for agentic frontdoor duties |

Track A is therefore closed negative. Do not restart the LongCat CPU probe unless the goal is a new hypothesis, such as a higher-precision LongCat quant, altered chat template, or a dedicated literal-retrieval role.

## What Was Tested

The evaluated model was Meituan LongCat-Flash-Lite, 68.5B total parameters with 2.9-4.5B active parameters and 31.4B parameters in n-gram embedding tables. The local GGUF was:

`/mnt/raid0/llm/models/longcat-flash-lite-q4km/LongCat-Flash-Lite-Q4_K_M.gguf`

It was served with the InquiringMinds llama.cpp fork:

`/mnt/raid0/llm/llama.cpp-longcat-probe`

That fork is sufficient for local research, but it is not an upstreamable production path because the publisher disclosed AI-generated implementation work that conflicts with upstream llama.cpp policy.

## Architectural Scope

This is a negative result for LongCat-Flash-Lite as a production checkpoint on our stack, not a negative result for paper-faithful Engram.

LongCat is an Engram-family architecture, but it is simpler than the DeepSeek/Peking University Engram paper:

- input-embedding injection only, not per-layer mid-stream injection
- no scalar gate
- no depthwise causal convolution
- polynomial rolling hash, not multiplicative-XOR
- 4 hash heads per order, not 8
- n-gram orders `{2,3,4}`, not paper `{2,3}`
- custom 131k tokenizer with no released canonicalization map

Track B in the handoff remains a separate research bet: frozen-backbone retrofit of a paper-faithful Engram module, gated by a GPU proxy run.

## Speed Result

`llama-bench` ran with the tuned EPYC stack: 96 threads, flash attention on, interleaved NUMA allocation, active wait policy, and `KMP_BLOCKTIME=10`.

| Test | LongCat Q4_K_M | gemma4 no-MTP | gemma4 MTP production | Qwen3.6 Q8 |
|---|---:|---:|---:|---:|
| pp512 | 322.65 | 957.82 | not isolated | 439.31 |
| pp4096 | 258.33 | 891.39 | not isolated | 435.51 |
| tg128 | 37.08 | 47.71 | ~76.5 | 25.17 |

LongCat passed the Track A speed limb in isolation because it exceeded the 35 t/s proceed threshold. It still lost the relevant worker comparator badly: roughly half of deployed gemma4-MTP decode speed.

## Quality Result

The quality gate used the 39-question sentinel suite with `temperature=0`, `max_tokens=2048`, and identical scoring by each question's `scoring_method`.

| Suite | LongCat | gemma4-MTP | Result |
|---|---:|---:|---|
| agentic | 1/3 | 1/3 | tie, both weak |
| coder | 3/3 | 3/3 | tie |
| general | 4/4 | 4/4 | tie |
| gpqa | 1/4 | 2/4 | gemma4 +1 |
| hotpotqa | 3/4 | 1/4 | LongCat +2 |
| instruction_precision | 3/4 | 4/4 | gemma4 +1 |
| long_context | 1/1 | 1/1 | tie |
| math | 0/6 | 4/6 | gemma4 +4 |
| mode_advantage_hard | 2/3 | 2/3 | tie |
| simpleqa | 1/3 | 1/3 | tie |
| thinking | 2/4 | 3/4 | gemma4 +1 |
| **Total** | **21/39** | **26/39** | **gemma4 +12.9pp** |

The math failure was structural, not a token-budget artifact. LongCat scored 0/6 at both 512 and 2048 token budgets, and observed traces included arithmetic errors inside otherwise plausible step-by-step reasoning.

The one real positive signal was HotpotQA: LongCat won 3/4 vs 1/4. That is consistent with the n-gram table helping literal-string multi-hop retrieval, but the single-suite win is not enough to offset worker-general speed and quality losses.

## Decision

Do not deploy LongCat-Flash-Lite for:

- `worker_general`: dominated by gemma4-MTP on speed and sentinel quality.
- `frontdoor`: faster than Qwen3.6 decode, but too weak on agentic duties.
- `ingest_long_context` or `architect_general`: wrong role scale and no supporting quality evidence.

Keep the result as positive evidence for the family:

- The 31.4B-parameter n-gram table fits comfortably in host DDR5.
- Lookup bandwidth was not the bottleneck on EPYC.
- A novel n-gram-augmented MoE checkpoint can run locally through a llama.cpp fork.

## References

- Root handoff: `handoffs/active/engram-conditional-memory.md`
- Intake index: `research/intake_index.yaml` (`intake-504`, `intake-599`, `intake-600`)
- Full research report copy: `/mnt/raid0/llm/epyc-inference-research/research/deep-dives/longcat-flash-lite-engram-cpu-poc.md`
- Eval JSON: `/mnt/raid0/llm/epyc-inference-research/research/engram-spike/eval/longcat-results-2048.json`
- Comparator JSON: `/mnt/raid0/llm/epyc-inference-research/research/engram-spike/eval/gemma4-results.json`
