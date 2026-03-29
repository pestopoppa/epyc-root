# Leanstral: Architecture & Deployment Analysis

**Intake ID**: intake-235
**Released**: 2026-03-16
**Organization**: Mistral AI
**License**: Apache 2.0

## Architecture — DeepSeek V3-style MoE + MLA

Leanstral is a fine-tune of **Mistral Small 4** (which adopted DeepSeek V3's architecture).

| Parameter | Value |
|-----------|-------|
| Total params | 119B (122.4B from config) |
| Active params/token | ~6.5B |
| Layers | 36 |
| Hidden size | 4096 |
| Attention heads | 32 (MLA, not GQA) |
| MLA q_lora_rank | 1024 |
| MLA kv_lora_rank | 256 |
| MLA qk_rope_head_dim | 64 |
| Routed experts | 128 |
| Shared experts | 1 |
| Active experts/token | 4 |
| Expert FFN size | 2048 |
| Shared FFN size | 12288 |
| Vocab | 131,072 (Tekken tokenizer) |
| Max context | 1,048,576 (1M; 256k recommended) |
| RoPE | YaRN, θ=10000, factor=128, original_max=8192 |
| Vision | Pixtral (1024 hidden, 24 layers, dead weight for proofs) |

**Architecture string in llama.cpp**: `deepseek2` — fully supported.

## FLTEval Benchmark

Based on Fermat's Last Theorem formalization project. Tests repo-scale proof engineering (completing PRs), not function-level verification.

| Model | pass@2 | pass@16 | Cost (pass@2) |
|-------|--------|---------|---------------|
| **Leanstral** | **26.3** | **31.9** | **$36** |
| Claude Sonnet 4.6 | 23.7 | 23.9 | $549 |
| Claude Opus 4.6 | — | — | $1,650 |

## GGUF Availability

Community GGUFs at `jackcloudman/Leanstral-2603-GGUF` (1,723 downloads/month).

| Quantization | Size | Notes |
|-------------|------|-------|
| Q4_K_M | ~68 GB | Best quality/size balance |
| Q8_0 | ~126 GB | Near-lossless |

Reported: ~34 t/s on 2× RTX 4090 (48GB VRAM) + 192GB RAM with Q4_K_M.

## EPYC 9655 CPU Deployment

| Quantization | Memory | Estimated Speed |
|-------------|--------|----------------|
| Q4_K_M | ~67 GB | ~36 t/s |
| Q8_0 | ~126 GB | ~19 t/s |
| Q6_K | ~97 GB | ~24 t/s |

Speed estimate: ~200 GB/s DDR5 bandwidth, ~5.6 GB accessed per token at Q4_K_M (attention + shared expert + 4 routed experts + router).

## REAP Expert Pruning — Ideal Candidate

**95% of total parameters are routed expert weights** (116B of 122B).

| Pruning Level | Experts Kept | Total Params | Q4_K_M Size | Notes |
|---------------|-------------|-------------|-------------|-------|
| None | 128 | 119B | 68 GB | Baseline |
| 75% | 32 | ~35B | ~20 GB | Moderate risk — Lean 4 may cluster on few experts |
| 87.5% | 16 | ~21B | ~12 GB | Higher risk — needs profiling |

**Key hypothesis**: Lean 4 proof engineering is extremely specialized. If expert activation patterns cluster (same 20-30 experts handle most Lean tokens), REAP could prune aggressively with minimal quality loss. Needs profiling with `--moe-expert-stats` on representative workloads.

**REAP-32 + Q4_K_M ≈ 20 GB** → ~40+ t/s on EPYC 9655. Blazing fast.

## Leanstral vs Goedel-Code-Prover-8B

| Dimension | Leanstral | Goedel-CP-8B |
|-----------|-----------|-------------|
| Architecture | 119B MoE (6.5B active) | 8B dense |
| Task focus | Repo-scale proof engineering | Function-level code verification |
| Benchmark | FLTEval (FLT PRs) | Verina/Clever/AlgoVeri (427 tasks) |
| Innovation | MCP tool use (lean-lsp-mcp), agentic | Hierarchical proof search, subgoal decomposition |
| Q4_K_M size | 68 GB (20 GB REAP-pruned) | ~4.5 GB |
| CPU speed | ~36 t/s (full), ~40+ t/s (REAP-32) | ~25-40 t/s |
| License | Apache 2.0 | MIT |

**Different tools for different jobs**: Leanstral is an *agent* (uses lean-lsp-mcp tool, reads repo context). Goedel is a *prover* (takes goal, produces tactic proof). Complementary, not competing.

## Integration Notes

- Chat template requires `[THINK]` reasoning blocks and `reasoning_effort` parameter
- vLLM officially recommended (`--attention-backend FLASH_ATTN_MLA`) but llama.cpp works via community GGUFs
- Multimodal (Pixtral vision encoder) — dead weight for proof tasks, could be stripped
- `deepseek2` architecture fully supported in llama.cpp fork (MLA + MoE routing)
