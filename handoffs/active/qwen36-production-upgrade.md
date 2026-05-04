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

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-455] "Qwen3.6-27B Spec-Decoding on RTX 4090 with 1.7B Same-Family Draft (community note)"** (`inline:qwen36-27b-spec-decoding-rtx4090-2026-04-24`)
  - **Model mismatch caveat**: this note targets the freshly-released **Qwen3.6-27B dense** (released 2026-04-22, Apache-2.0, 262K ctx extensible to 1M), which is **distinct** from this handoff's **Qwen3.6-35B-A3B hybrid-MoE**. The 5.9× GPU speedup numbers do **not** transfer — MoE + hybrid-SSM verification-wall is documented in `wiki/speculative-decoding.md`, and thc1006's 19-config sweep on Qwen3.6-35B-A3B + 0.8B draft on RTX 3090 (2026-04-19) found **no net speedup** post-PR-#19493.
  - Relevance to this handoff: signals that Qwen3.6 family now has a **dense 27B variant** — a potential new worker/coder model candidate. Worth a separate CPU-feasibility probe (BW-bound decode on EPYC 9655 for a 27B dense in Q4_K_M).
  - Action: **flag for model-intake** — evaluate Qwen3.6-27B-Q4_K_M as a CPU candidate for the coder/worker slot. Do not conflate with the 35B-A3B upgrade tracked here. If promoted, spawn a sibling handoff.

## Research Intake Update — 2026-05-04

### Qwen-Scope SAE Suite Includes Qwen3.5-35B-A3B (predecessor architecture)

- **[intake-521] "Qwen-Scope: Turning Sparse Features into Development Tools for LLMs"** (Qwen Team, 2026-04-30, OSS PDF)
  - Direct relevance: Qwen-Scope releases SAEs for **Qwen3.5-35B-A3B-Base** — the production predecessor of the 35B-A3B-hybrid model this handoff is upgrading from. Two widths: W32K-L0_50 and W128K-L0_100, all 40 layers, expansion factors 16x and 64x. There are NO published SAEs for Qwen3.6-35B-A3B (released 2026-04-16, ~2 weeks before Qwen-Scope), so the upgrade target itself remains uncovered.
  - Practical implication: the Qwen3.5 SAEs can serve as a **diagnostic baseline** for the upgrade evaluation — feature activations on identical prompt sets between the predecessor (with SAEs) and the upgrade (without yet) reveal whether the post-training shift in Qwen3.6 has moved the model away from the SAE-discovered feature basis. If it has, that argues against transferring any future Qwen-Scope-derived intervention without re-training SAEs.
  - Specific application: the three documented failure modes in this handoff's task 4 — "think loops, /think loops, degenerate repetition" while running the quality eval — match exactly the **endless-repetition feature mechanism** documented in Qwen-Scope Section 8. The SAE-Res-Qwen3.5-35B-A3B-Base-W32K-L0_50 release would let us inspect whether those repetition failures activate the same repetition features identified on Qwen3-30B-A3B (which also has a Section 8 result). If the pattern transfers, the Section 8 RL recipe (SAE-guided rare-negative augmentation in DAPO) becomes a candidate post-training intervention for Qwen3.6-35B-A3B once SAEs are trained on it.
  - Architecture caveat: Qwen3.5 -> Qwen3.6 keeps the 256-expert / 8+1-active / 40-layer structure but the post-training is different. Feature transferability between predecessor and successor SAEs in MoE+hybrid-SSM architectures is not characterized in the Qwen-Scope paper; the only same-architecture longitudinal comparison the paper makes is Qwen3 vs Qwen3.5.
  - Action: defer; mentioned in `qwen-scope-sae-toolkit.md` (stub 2026-05-04). Do NOT block the production-upgrade quality eval on SAE inspection. If quality regressions concentrate on think-loop or repetition-style failures (matching task-4 history), fall back to the SAE diagnostic path. Otherwise the SAEs remain a future-research asset for the predecessor model only.
  - Caveats (Tier 2b): Qwen-Scope's Section 7 SASFT shows non-trivial general-capability regressions on Qwen3-8B (HellaSwag -2.88pp, MMLU -2.06pp); applying SASFT-style suppression to a production candidate would need diversity-collapse + general-capability gates beyond what this handoff's current eval suite measures.
