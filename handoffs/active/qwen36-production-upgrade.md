# Qwen3.6-35B-A3B — Production Upgrade Evaluation

**Status**: in-progress (quality benchmark ready)
**Created**: 2026-04-17 (via research intake)
**Updated**: 2026-04-17 (NUMA sweeps complete, quality benchmark infrastructure ready)
**Categories**: moe_optimization, ssm_hybrid, inference_serving
**Priority**: HIGH (direct production model successor)
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`log-linear-gated-deltanet-readiness.md`](log-linear-gated-deltanet-readiness.md), [`bulk-inference-campaign.md`](bulk-inference-campaign.md)

## Objective

Evaluate Qwen3.6-35B-A3B as a drop-in replacement for the production Qwen3.5-35B-A3B model. Same hybrid architecture (Gated DeltaNet + Gated Attention + MoE), same parameter counts (35B total, 3B active), but improved benchmarks across the board — particularly agentic coding (+11pp Terminal-Bench, +3.4pp SWE-bench).

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-387 | Qwen3.6-35B-A3B model card | high | new_opportunity |
| intake-391 | Qwen3.6-35B-A3B GGUF (unsloth) | high | new_opportunity |

## Key Upgrade Signals

- **Architecture identical**: 10x(3xGDN->MoE -> 1xAttn->MoE), 256 experts, 8+1 active, 2048 hidden dim, 40 layers
- **GGUF ready**: Q4_K_M = 22.1 GB (vs ~22 GB for Qwen3.5 Q4_K_M). Drop-in file swap.
- **New features**: `preserve_thinking` (retain reasoning context across turns), enhanced tool calling with nested object parsing
- **Benchmark gains**: SWE-bench Verified 73.4 (was 70.0), Terminal-Bench 2.0 51.5 (was 40.5), MMLU-Pro 85.2

## Deep Dive Findings (2026-04-17)

### Architecture Confirmation
- `config.json` declares `"model_type": "qwen3_5_moe"` and `"architectures": ["Qwen3_5MoeForConditionalGeneration"]`
- **Byte-for-byte identical structure** to Qwen3.5-35B-A3B. All improvements are post-training only.
- **No llama.cpp patches needed** beyond existing Qwen3.5 support

### Known llama.cpp Issues (carry over from Qwen3.5)
- Parallel-slot "Chunk not found" crash (issue #20222) with hybrid attention
- seq_add assertion failure (issue #19915) — our IMROPE patch addresses this
- Silent unload under heavy load (issue #20002)
- KV cache: use bf16 or q8_0, NOT f16 (clips dynamic range, PPL degradation)

### preserve_thinking
- **Jinja chat template feature**, not architecture change
- Works with llama.cpp `--jinja` flag: `--chat-template-kwargs '{"preserve_thinking": true}'`
- Retains `<think>` blocks from prior turns instead of stripping — useful for multi-turn agentic sessions

### Independent Benchmarks
- BenchLM provisional: #41/109 overall (64/100), **#14/109 in coding (81/100)**
- Weakest: Knowledge (#38). Model is 2 days old, verified pool still small.

### Benchmark Comparison (Qwen3.5 → Qwen3.6)

| Benchmark | Qwen3.5 | Qwen3.6 | Delta |
|-----------|---------|---------|-------|
| SWE-bench Verified | 70.0 | 73.4 | +3.4 |
| Terminal-Bench 2.0 | 40.5 | 51.5 | **+11.0** |
| NL2Repo | 20.5 | 29.4 | +8.9 |
| QwenWebBench | 978 | 1397 | +419 |
| AIME 2026 | — | 92.7 | — |
| MMLU-Pro | — | 85.2 | — |

No regressions reported.

## Resolved Questions

- [x] **llama.cpp compatibility**: Confirmed — identical model_type, zero patches needed
- [x] **preserve_thinking**: Works via `--jinja` flag with chat template kwargs
- [x] **tok/s on EPYC 9655**: 25.6 baseline, 27.4 with ngram dm=64 (+10.1%). Q8 faster than Q4 (25.6 vs 24.4).
- [ ] **PPL regressions**: Pending — quality benchmark ready to execute
- [ ] **Coding eval**: Pending — quality benchmark ready to execute

## Evaluation Plan

1. [x] Download Q4_K_M GGUF from unsloth/Qwen3.6-35B-A3B-GGUF — COMPLETE (deleted, Q8 faster)
2. [x] Download Q8_0 GGUF — COMPLETE (`/mnt/raid0/llm/models/Qwen3.6-35B-A3B-Q8_0.gguf`)
3. [x] Run throughput benchmark (single-model 192t, NUMA 4-way) — COMPLETE: 25.6 baseline, 27.4 w/ngram, 57.4 quad, 76.8 eight
4. [ ] Run quality eval (full suite battery via run_benchmark) — IN PROGRESS: required `use_chat_api: true`, `reasoning: off`, KV `q8_0/q8_0`. Three failed attempts (think loops, `/think` loops, degenerate repetition) before finding correct config. Current run uses `--reasoning off` server flag.
5. [ ] Run coding eval (SWE-bench subset or equivalent) — validate agentic coding claims
6. [ ] If no regressions: swap into production registry (`model_registry.yaml`)

## GGUF Files

| Quant | Size | File | Status |
|-------|------|------|--------|
| Q4_K_M | 22.1 GB | `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf` | DELETED (Q8 faster) |
| Q8_0 | 36.9 GB | `Qwen3.6-35B-A3B-Q8_0.gguf` | Active |

Target: `/mnt/raid0/llm/models/`

## Notes

Released April 16, 2026. This is a weights-only upgrade — all improvements from post-training focused on agentic coding. The +11pp Terminal-Bench gain is the most compelling signal for our orchestrator use case. Ollama already ships it as `qwen3.6:35b-a3b`.
