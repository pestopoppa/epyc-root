# KV Cache Selection/Eviction (TriAttention / Expected Attention)

**Status**: ACTIVE — Research evaluation phase. No code written; benchmarking KVPress + validating Q/K concentration.
**Created**: 2026-04-08 (via research intake)
**Updated**: 2026-04-08
**Priority**: MEDIUM
**Categories**: kv_cache, inference_serving, memory_bandwidth

## Current Work — Resume Here

### What's Done (2026-04-08)

Research intake processed 3 papers (intake-284 TriAttention, intake-287 LongFlow, intake-288 Expected Attention). Deep-dive cluster analysis completed (267 lines at `research/deep-dives/triattention-kv-selection-cluster.md`), all assessments validated, priorities reordered:

- **Expected Attention** upgraded to primary candidate (Flash Attention compatible, explicit quantization orthogonality, GQA + per-head adaptive, KVPress library)
- **LongFlow** downgraded (topic-switch failure mode impacts our orchestrator pipeline)
- **TriAttention** remains high-relevance secondary candidate (strongest decode-phase results but no quantization discussion, vLLM-only)

### State

**Evaluation gate** — determining whether KV selection is worth pursuing alongside our deployed quantization (`--kv-hadamard -ctk q4_0 -ctv f16`). No code written, no benchmarks run. S1/S2 below are the decision points.

## Objective

Evaluate TriAttention's pre-RoPE trigonometric KV scoring as an orthogonal complement to our Hadamard KV quantization. If viable, stacking selection (keep fewer tokens) + quantization (compress survivors) could yield multiplicative memory savings beyond either approach alone.

## Why This Matters for EPYC

KV cache quantization (our deployed Hadamard + q4_0) compresses HOW each token's KV is stored. KV cache selection compresses WHICH tokens are kept. These are orthogonal dimensions — combined theoretical ceiling: 10.7x (selection) x 2x (quantization) = **~21x KV memory reduction**.

At 256K+ context, KV cache dominates memory. Our production coder (Qwen2.5-Coder-32B, pure attention) at 256K context uses ~64 GB KV at f16. With Hadamard q4_0: ~16 GB. With 10x selection on top: ~1.6 GB. The difference between "can't serve" and "trivial."

See `kv-cache-quantization.md` → Why This Matters for EPYC for full hardware specs (EPYC 9655, 1.13 TB DDR5, ~355 GB free for KV).

**Caveat**: Quality cliff under dual compression is unknown — that is exactly what S3 tests.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-284 | TriAttention: Efficient Long Reasoning with Trigonometric KV Compression | high | new_opportunity |
| intake-287 | LongFlow: Efficient KV Cache Compression for Reasoning Models | medium (↓) | worth_investigating |
| intake-288 | Expected Attention: KV Cache Compression by Estimating Attention from Future Queries Distribution | high (↑) | worth_investigating |

## Work Items

| Stage | Task | Priority | Status | Decision Gate |
|-------|------|----------|--------|---------------|
| S1 | KVPress evaluation: benchmark Expected Attention on Qwen2.5-7B at 50%/25% compression. Measure RULER score, PPL, latency. Compare against SnapKV baseline. | HIGH | NOT STARTED | >= 90% RULER at 50% compression |
| S2 | Q/K concentration validation: run TriAttention calibration on Qwen2.5-7B. Verify pre-RoPE clustering (expect R >= 0.95). | HIGH | NOT STARTED | R >= 0.95 (pre-RoPE clustering confirmed) |
| S3 | Selection + quantization stacking: best scorer from S1/S2 combined with `--kv-hadamard -ctk q4_0 -ctv f16`. Measure quality under dual compression. | HIGH | BLOCKED on S1/S2 | Quality-neutral at >= 4x combined compression |
| S4 | llama.cpp portability: assess Expected Attention Gaussian scoring for C++ port. Document changes needed to llama.cpp KV cache infrastructure. | MEDIUM | BLOCKED on S1 | Feasible C++ port path identified |
| -- | LongFlow monitoring: track for topic-switch weakness fix in paper revisions. | LOW | WATCHING | -- |

S1 and S2 can run **in parallel**. S3 depends on S1/S2 results. S4 depends on S1. If both S1 and S2 fail their gates, **CONCLUDE** this handoff — quantization alone is sufficient.

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | Q/K clustering doesn't hold on Qwen2.5/DeepSeek | Medium | High — TriAttention unusable | S2 validates early; Expected Attention (Gaussian) needs no clustering assumption |
| R2 | Dual compression (selection + quantization) hits quality cliff | Medium | High — stacking not viable | S3 tests explicitly; may need to choose one or the other |
| R3 | KVPress library incompatible with our model formats | Low | Medium — delays S1 | KVPress uses HuggingFace models; eval on f16 HF weights, port winner later |
| R4 | Hadamard rotation breaks trigonometric scoring (q4_0 norm error) | Medium | Medium — limits stacking | Hadamard preserves norms (orthogonal); q4_0 degrades. Test both in S3 |

## Decision Framework

- **Gate 1 (after S1)**: IF Expected Attention >= 90% RULER at 50% compression on Qwen2.5-7B THEN proceed to S3 stacking test. ELSE evaluate TriAttention via S2 before concluding.
- **Gate 2 (after S2)**: IF Q/K concentration validates (R >= 0.95) THEN TriAttention remains a candidate. ELSE drop TriAttention, rely solely on Expected Attention.
- **Gate 3 (after S3)**: IF selection + quantization stacking is quality-neutral at >= 4x combined compression THEN promote to implementation phase. ELSE **CONCLUDE** — KV quantization alone sufficient.
- **Overall**: IF S1 AND S2 both fail gates THEN **CONCLUDE as NOT VIABLE**.

## Open Questions

- Can TriAttention's pre-RoPE Q/K concentration assumption be validated for our models (Qwen2.5, DeepSeek-R1-Distill)?
- Is the trigonometric scoring portable to llama.cpp's KV cache architecture, or is it fundamentally tied to vLLM's PagedAttention?
- What is the interaction between token eviction and our Hadamard smoothing? (Hadamard operates on all tokens — does selective eviction break the rotation properties?)
- At what KV budget does TriAttention's quality degrade? Their 2048-token budget is aggressive — our models may need different budgets.
- Does trigonometric scoring work on Hadamard-rotated, q4_0-quantized K vectors? Hadamard preserves norms (orthogonal transform), but q4_0 introduces norm error. Net effect unknown.
- Expected Attention may be MORE practical than TriAttention for our stack — Flash Attention compatible, explicit quantization orthogonality, GQA support. Should we prioritize it? (Deep-dive says yes.)

## Deep-Dive Findings (2026-04-08)

See `research/deep-dives/triattention-kv-selection-cluster.md` for full analysis (5 papers, 267 lines).

- **TriAttention**: "Matches Full Attention" is at throughput-parity only. At fixed 2048 budget: AIME25 32.9% (−7.9pp), MATH500 68.4% (−1.2pp). Still best eviction method vs SnapKV/R-KV. Validated on 5 architectures including MLA-940heads. Credibility 4 (Song Han MIT/NVIDIA).
- **Expected Attention**: Flash Attention compatible (SnapKV/H2O are NOT), explicitly discusses quantization stacking, GQA with per-head adaptive compression. RULER 4K: 94.7% at 50% vs SnapKV 55.7%. Credibility 4 (KVPress library, 6 models tested). **Primary candidate.**
- **LongFlow**: Downgraded — topic-switch failure mode impacts orchestrator. 11.8x headline is system-level vs vanilla (not accuracy-matched like TriAttention's 2.5x).

## Key Files

| Path | Purpose |
|------|---------|
| `research/deep-dives/triattention-kv-selection-cluster.md` | Full cluster analysis (5 papers, 267 lines) |
| `handoffs/active/kv-cache-quantization.md` | Parent quantization handoff (Hadamard Phase 1 deployed) |
| `research/intake_index.yaml` (intake-284, 287, 288) | Source intake entries with full metadata |

## References

- TriAttention: https://arxiv.org/abs/2604.04921 | https://github.com/WeianMao/triattention (Apache 2.0)
- LongFlow: https://arxiv.org/abs/2603.11504
- Expected Attention: https://arxiv.org/abs/2510.00636 | KVPress: https://github.com/NVIDIA/kvpress

## Notes

Complementarity with our stack: `--kv-hadamard` reduces per-token KV size. Selection reduces token count. Combined: 10.7x (selection) x 2x (q8/q4 quant) = ~21x potential KV memory reduction. Needs empirical validation — quality cliff may hit earlier when both are active.
