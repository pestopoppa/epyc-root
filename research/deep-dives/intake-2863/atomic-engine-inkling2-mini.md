# intake-2863 — Atomic Engine (Inkling 2 Mini) deep dive

Source: github.com/AtomicBot-ai/atomic-engine, branch engine-development @ `fb69fff02101b048a0a165a3b502712dd2ca978f`, read from a local clone 2026-11-24. Lane head `8f49b151a`. Read depth PARTIAL (files listed in the entry's `dive_corrections`).

## Verdicts per claim
| # | Claim | Verdict |
|---|---|---|
| 0 | Memory-budgeted expert streaming from GGUF | CONFIRMED (executor; CPU and MTL0 only) |
| 1 | Loop-aware residency for Inkling core layers | PARTIAL: default is core banks; `inkling-loop-age` is an opt-in experimental policy, no A/B published |
| 2 | 105.71 tok/s with IQ2_M + DSpark on M4 Max | PARTIAL: confounded — stock arm has no drafter; prompt repetitive raw continuation |
| 3 | Device MoE cache with CPU share of misses | CONFIRMED as documented; not measured |
| 4 | TurboQuant lineage | not examined |

## H1 (resolved)
The bench script gives the stock arm no `-md`/`--spec-type`; every Atomic arm runs `draft-dspark`. The prompt is a file doubled without separator, raw `/completion`, `ignore_eos`, 64 tokens; output ids cycle. The ratio is spec-decode + engine on a highly predictable continuation and is an upper bound.

## Correction to our handoff
`INK2-PORT-2c` says no GGUF drafter is published. AtomicChat publishes `dspark-Inkling-2-Mini-Q8_0.gguf` (504 MB) and the fork's graph is a port of upstream PR #32218.

## Derived actionables
- H2 MI210 placement estimate using core-layer residency (non-inference, gated on INK2-MEAS-1 GO).
- H3 refine INK2-PORT-2c onto the published GGUF drafter and #32218.
- H4 add an AD-IQ2_M / AD-IQ3_S quant arm note to INK2-MEAS-1's follow-up.
- H5/H6: trigger prose only.

## Dive-surfaced sources
- llama.cpp PR #31233 (`moe_cache_lru`) — would settle whether a class-LRU device expert cache is upstream; bears on H6. Recommend ingest at a later intake.
- AtomicChat/Inkling-2-Mini-GGUF model card — would settle the AD-* quant recipe; bears on H4.

Artifact audit: clean (clone and JSON under /mnt/raid0/llm/tmp/dive-atomic/).
