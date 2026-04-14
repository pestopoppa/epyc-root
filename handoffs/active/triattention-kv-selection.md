# KV Cache Selection/Eviction (TriAttention / Expected Attention)

**Status**: ACTIVE — Benchmark scaffold ready. KVPress cloned, eval harness written. Awaiting model server for live evaluation.
**Created**: 2026-04-08 (via research intake)
**Updated**: 2026-04-13
**Priority**: MEDIUM
**Categories**: kv_cache, inference_serving, memory_bandwidth

## Current Work — Resume Here

### What's Done (2026-04-08)

Research intake processed 3 papers (intake-284 TriAttention, intake-287 LongFlow, intake-288 Expected Attention). Deep-dive cluster analysis completed (267 lines at `research/deep-dives/triattention-kv-selection-cluster.md`), all assessments validated, priorities reordered:

- **Expected Attention** upgraded to primary candidate (Flash Attention compatible, explicit quantization orthogonality, GQA + per-head adaptive, KVPress library)
- **LongFlow** downgraded (topic-switch failure mode impacts our orchestrator pipeline)
- **TriAttention** remains high-relevance secondary candidate (strongest decode-phase results but no quantization discussion, vLLM-only)

### What's Done (2026-04-13)

- KVPress repo cloned to `data/external/kvpress` (NVIDIA, Apache 2.0)
- Expected Attention scorer reviewed: Gaussian statistical model of future queries + averaged RoPE rotation. Flash-compatible, GQA-aware, per-head adaptive.
- Benchmark scaffold written at `scripts/benchmark/eval_expected_attention.py`: RULER NIAH tasks (synthetic needle retrieval at 4K/8K/16K), LongBench-v2 QA (502 samples). Dry-run validated.
- Awaiting model server (Qwen2.5-7B-Instruct) to run S1 gate evaluation.

### State

**Evaluation gate** — scaffold ready, awaiting model server. S1/S2 below are the decision points.

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
| S1 | KVPress evaluation: benchmark Expected Attention on Qwen2.5-7B at 50%/25% compression. Measure RULER score, PPL, latency. Compare against SnapKV baseline. | HIGH | **BLOCKED** — HF CPU infeasible (see note). Replan as S4-first. | >= 90% RULER at 50% compression |
| S2 | Q/K concentration validation: run TriAttention calibration on Qwen2.5-7B. Verify pre-RoPE clustering (expect R >= 0.95). | HIGH | NOT STARTED | R >= 0.95 (pre-RoPE clustering confirmed) |
| S3 | Selection + quantization stacking: best scorer from S1/S2 combined with `--kv-hadamard -ctk q4_0 -ctv f16`. Measure quality under dual compression. | HIGH | BLOCKED on S1/S2 | Quality-neutral at >= 4x combined compression |
| S4 | llama.cpp port: implement Expected Attention Gaussian scoring in ggml. Use `llama_memory_seq_rm()` for eviction (validated by Memento S1, 2026-04-14). | **HIGH** (promoted) | UNBLOCKED — algorithm spec reviewed, eviction primitive validated | Scorer runs in llama.cpp, eval via llama-server |
| -- | LongFlow monitoring: track for topic-switch weakness fix in paper revisions. | LOW | WATCHING | -- |

**S1 HF CPU infeasibility note (2026-04-14)**: KVPress runs through HuggingFace transformers, not llama.cpp. On our EPYC CPU, even a 0.5B model at 4K-16K context took >5 min per sample with no results. The 7B model consumed 65GB and was projected at hours per sample. Root cause: HF Python inference has no ggml kernel optimizations — ~100x slower than llama.cpp on identical hardware. **New plan**: promote S4 (llama.cpp C++ port) to first priority. The Expected Attention scorer is a per-layer scoring function (mean/cov of pre-RoPE queries + Gaussian future prediction + V-norm weighting), not an architecture change. Eviction uses `llama_memory_seq_rm()` which Memento S1 validated (5/5 tests, 2026-04-14). Once the scorer runs in llama.cpp, S1's RULER benchmark can execute at production speed (88+ t/s on 7B).

S4 is now the **critical path**. S1/S2 evaluation runs through the llama.cpp scorer once S4 is implemented. S3 depends on S1/S2 results. If both S1 and S2 fail their gates, **CONCLUDE** this handoff — quantization alone is sufficient.

**Expected Attention algorithm (for S4 port)**:
1. After prefill, extract pre-RoPE Q statistics: `mu = mean(Q_preRoPE)`, `cov = (Q-mu)^T(Q-mu)/n` per head
2. Compute averaged RoPE rotation matrix R over `[q_len, q_len+512)` future positions
3. Apply: `mu = mu @ R^T`, `cov = R @ cov @ R^T`
4. Score each KV entry: `score = K @ mu^T / sqrt(d) + 0.5 * K @ cov @ K^T / d`, then softmax, then `*= ||V||_2`
5. Protect sink tokens (first 4), evict lowest-scoring via `llama_memory_seq_rm()`

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
- **Overall**: IF S1 AND S2 both fail gates THEN **CONCLUDE as NOT VIABLE** for token selection. However, Attention Matching compaction ([attention-matching-kv-compaction.md](attention-matching-kv-compaction.md)) provides 10-50x compression via latent-space construction rather than token selection. AM outperforms all selection baselines at 20x+; at 5-10x the gap narrows. AM is a viable replacement path, not just a complement — evaluate AM independently of S1/S2 outcomes.

## Composability: Triple-Stack KV Compression (intake-289, 2026-04-09)

Memento (intake-289) introduces a third orthogonal KV compression dimension — block masking removes entire reasoning blocks, retaining only summary KV states. Combined theoretical ceiling:

| Layer | Method | Compression | Status |
|-------|--------|-------------|--------|
| Selection (this handoff) | TriAttention / Expected Attention | 2-10x | S1/S2 evaluating |
| Quantization | Hadamard + q4_0 | 2x | **Production** (`b51c905`) |
| Block masking | Memento | 2-3x | Research (memento-block-reasoning-compression.md) |

S3 (selection + quantization stacking) should also consider eventual triple-stack with block masking. Quality cliff under triple compression is the key unknown.

See: [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md), deep-dive at `research/deep-dives/memento-iterative-reasoning-cluster.md`.

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

## Research Intake Update — 2026-04-13

### New Related Research
- **[intake-350] "Latent Briefing: KV Cache Compaction for Multi-Agent Systems"** (github:CuriousCaliBoi/latent-briefing)
  - Relevance: Implements attention-score-driven KV compaction with MAD thresholding + PGD reweighting for cross-model agent transfer (Claude orchestrator → Qwen3-14B worker). Uses same RMS attention scoring family as TriAttention/Expected Attention for position selection, but adds learned per-position β weights and Ridge regression value correction.
  - Key technique: AMCompactor — three-stage pipeline: RMS scoring → MAD threshold selection → PGD β + Ridge C2
  - Reported results: No published benchmarks in repo. VentureBeat coverage claims 42-57% worker token reduction, 21-31% total token reduction, +3pp accuracy at optimal thresholds.
  - Delta from current approach: This is KV *compaction* (construct new compact representations), not selection (keep/evict original tokens). Orthogonal paradigm to TriAttention/Expected Attention. Targets GPU (DGX Spark), not CPU.

- **[intake-351] "Fast KV Compaction via Attention Matching"** (arxiv:2602.16284)
  - Relevance: Formalizes KV compaction as attention matching with closed-form solutions. 50x compression on QuALITY benchmark, Pareto-dominant over all token-selection baselines (H2O, SnapKV, PyramidKV, KVzip). **This is the academic formalization of the compaction paradigm that Latent Briefing implements.**
  - Key technique: Attention Matching — NNLS for bias β, OLS for values, OMP or RMS-heuristic for key selection
  - Reported results: 50x compression, ~71% QuALITY accuracy, 100-200x faster than Cartridges
  - Delta from current approach: Token selection (this handoff) keeps original KV entries. Compaction constructs *new* compact KV representations in latent space. AM outperforms all selection baselines at high compression (20-100x). See new handoff: [attention-matching-kv-compaction.md](attention-matching-kv-compaction.md).
  - **llama.cpp status**: Issue #20037 open — blocked on ggml pseudoinverse support. Reference implementation: github.com/adamzweiger/compaction

- **[intake-352] "KVCOMM: Online Cross-context KV-cache Communication"** (arxiv:2510.12872)
  - Relevance: Training-free multi-agent KV cache reuse across agents with diverging prefixes. 70%+ reuse rate, 7.8x prefill speedup. NeurIPS'25.
  - Delta from current approach: Addresses multi-agent KV sharing (relevant to orchestrator stack), not KV compression.

## References

- TriAttention: https://arxiv.org/abs/2604.04921 | https://github.com/WeianMao/triattention (Apache 2.0)
- LongFlow: https://arxiv.org/abs/2603.11504
- Expected Attention: https://arxiv.org/abs/2510.00636 | KVPress: https://github.com/NVIDIA/kvpress

## Notes

Complementarity with our stack: `--kv-hadamard` reduces per-token KV size. Selection reduces token count. Combined: 10.7x (selection) x 2x (q8/q4 quant) = ~21x potential KV memory reduction. Needs empirical validation — quality cliff may hit earlier when both are active.
