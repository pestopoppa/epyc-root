# Lightning Attention Port to llama.cpp

**Status**: ACTIVE (newly opened 2026-04-29) — v1 port via existing `GGML_OP_GATED_LINEAR_ATTN`. L1 scoping pending; phases L2-L5 designed.
**Created**: 2026-04-29 (after audit of `llama.cpp-experimental` revealed Lightning Attention is essentially a constant-`g` GLA op)
**Updated**: 2026-04-29 (initial)
**Categories**: ssm_hybrid, context_extension, kv_cache, training_distillation, inference_serving
**Workstream**: Inference Acceleration (architectural research) + CPU Engineering (the actual port)
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**:
- [`log-linear-gated-deltanet-readiness.md`](log-linear-gated-deltanet-readiness.md) — sibling architecture (different lineage: log-linear-state vs fixed-decay-state); both are CPU-friendly intermediate paths
- [`multiscreen-attention-evaluation.md`](multiscreen-attention-evaluation.md) — sub-quadratic attention survey, intake-503 documented under same-day-expansion sub-section
- [`qwen36-27b-cpu-feasibility.md`](qwen36-27b-cpu-feasibility.md) — sizing comparison anchor for Ring-mini
- [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) — sibling architectural-port handoff (DSA / V3.2)
- intake-503 (Ling-Linear-2.0 paper, arxiv:2510.19338)
- [Lightning Attention deep-dive](../../research/deep-dives/ling-linear-lightning-attention-hybrid.md) — full architecture analysis + corrected effort estimate

## Objective

Port Lightning Attention to `llama.cpp-experimental` for Ant Group's Ring-mini-linear-2.0 (16B/957M-active) and Ring-flash-linear-2.0 (104B/6.1B-active) families. **Goal: working `convert_hf_to_gguf.py --arch ling_linear` + `llama-cli` decode on Ring-mini Q4_K_M within 3-5 days of focused work.**

## Why This Is Feasible (the GLA-op finding)

A direct audit of `llama.cpp-experimental` (HEAD `9f6191581` on `master`) finds **the kernel is already implemented**:

| Symbol | Location | Relevance |
|--------|----------|-----------|
| `GGML_OP_GATED_LINEAR_ATTN` (enum) | `ggml/include/ggml.h:561` | The op exists |
| `ggml_gated_linear_attn(ctx, k, v, q, g, state, scale)` | `ggml/include/ggml.h:2589` | API accepts `g` as a tensor — feeding a constant power-law decay tensor IS Lightning Attention |
| `ggml_compute_forward_gla_f32` | `ggml/src/ggml-cpu/ops.cpp:10605` | Full CPU implementation, multi-threaded across heads, head-size × head-size state per head — exactly Lightning Attention's recurrence structure |
| `llm_build_delta_net_base` | `src/models/models.h:23` | Base class for hybrid linear-attention models — Qwen3.5, Qwen3-next, Kimi-linear, Qwen3.5-MoE all derive from it |
| `llm_build_kimi_linear` | `src/models/models.h:369` | Closest existing template — also linear attention, with learned (not fixed) decay |

**Lightning Attention vs Gated Linear Attention difference is exactly one thing**: GLA's `g` is learned per-token; Lightning Attention's decay is fixed power-law per-head. **Implementation = feed `g` as a constant tensor of fixed-decay values to the existing op.** Zero new ggml ops needed for v1.

## Track-Based Phases

### L1 — Scoping confirmation (~1 day)

**Goal**: confirm GLA op semantics fully match Lightning Attention's fixed-decay recurrence; identify any gaps before writing model code.

**Work items**:

| ID | Task | Status |
|----|------|--------|
| L1.1 | Re-read `ggml_compute_forward_gla_f32` line-by-line; document exact recurrence equation | PENDING |
| L1.2 | Read Ring-Linear paper Section 7 (train/infer alignment + BF16 drift) — identify any precision constraints we'd hit | PENDING |
| L1.3 | Read `llm_build_kimi_linear` end-to-end as template for L3 | PENDING |
| L1.4 | Read Ant Group's reference impl (github.com/inclusionAI/Ling-V2 — when accessible — or HF model card for Ring-mini) — find the exact decay coefficient form and chunkwise/recurrent split | PENDING |
| L1.5 | Confirm ARM + CUDA + CPU backend coverage of `GGML_OP_GATED_LINEAR_ATTN` (we only need CPU for v1, but multi-backend matters for upstream contribution) | PENDING |
| L1.6 | **Decision gate**: GO/NO-GO. GO if GLA op semantics match within trivial reshaping. NO-GO triggers re-scope to L5 (dedicated op) as v1 instead. | PENDING |

**Decision rule**: NO-GO if GLA's state update doesn't accept a constant `g` (e.g., if shape mismatch forces broadcast that the kernel doesn't support). This is unlikely given the kernel's generic structure but must be verified.

### L2 — GGUF converter extension (~1 day, ~50 LOC)

**Goal**: `convert_hf_to_gguf.py --arch ling_linear` produces a valid GGUF from Ring-mini-linear-2.0 HF weights.

**Work items**:

| ID | Task | Status |
|----|------|--------|
| L2.1 | Map Ant Group's PyTorch tensor names to our GGUF tensor naming convention | PENDING |
| L2.2 | Add `LingLinearForCausalLM` config support to converter (architecture detection, hyperparameter extraction: chunk size, decay coefficient form, M ratio, layer count, head count) | PENDING |
| L2.3 | Add explicit handling for the fixed power-law decay coefficient — store as a per-head constant tensor in GGUF rather than as a learned weight | PENDING |
| L2.4 | Validate on a small test: convert Ring-mini-linear-2.0 BF16, sanity-check tensor shapes via `gguf_dump.py` | PENDING |

**Reference**: existing `convert_hf_to_gguf.py` patterns for Qwen3.5/3.6 (which already includes `delta_net` handling) — the ling-linear converter is an analogous extension.

### L3 — Model variant (~1-2 days, ~150 LOC)

**Goal**: `llm_build_ring_linear` derived from `llm_build_delta_net_base` in `src/models/`; loadable end-to-end.

**Work items**:

| ID | Task | Status |
|----|------|--------|
| L3.1 | Create `src/models/ring-linear.cpp`. Derive `llm_build_ring_linear` from `llm_build_delta_net_base`; mirror `llm_build_kimi_linear` structure | PENDING |
| L3.2 | In layer-build loop, call `ggml_gated_linear_attn` with `g` set to the per-head constant fixed-decay tensor loaded from GGUF | PENDING |
| L3.3 | Wire hyperparameters via `LLAMA_HPARAMS_*` (chunk size, M-ratio, fixed decay coefficient) | PENDING |
| L3.4 | Add architecture string `"ling_linear"` (or upstream-blessed name) to `src/llama-arch.cpp` enum + dispatcher | PENDING |
| L3.5 | Compile clean across our build matrix (no AVX-512 specific failures, no missing symbol errors) | PENDING |
| L3.6 | Load Ring-mini-linear-2.0 GGUF in `llama-cli` without crashing — does NOT require text generation; just verify tensors map correctly | PENDING |

### L4 — Test path (~1 day) [GATED]

**Goal**: validate decode quality matches paper's claimed numbers within tolerance.

**Inference gate**: REQUIRED per `feedback_no_concurrent_inference.md`. Every step in L4 needs explicit user approval.

**Work items**:

| ID | Task | Status | Notes |
|----|------|--------|-------|
| L4.1 | Smoke decode: `llama-cli -m ring-mini-linear-2.0.Q4_K_M.gguf -p "Hello, world!" -n 50` → coherent text | **GATED** | First sanity check |
| L4.2 | Reasoning quality spot-check: AIME-25 subset (5-10 problems) | **GATED** | Paper claims 73.65% Ring-mini AIME-25; 5-problem sample is signal-only, not statistical |
| L4.3 | GPQA-Diamond spot-check: 10 problems | **GATED** | Paper claims 65.69% Ring-mini GPQA-D |
| L4.4 | Throughput baseline: t/s at 8K context, single-instance EPYC | **GATED** | Use canonical `taskset -c 0-95 -t 96 -fa 1 --mmap 0 numactl --interleave=all` |
| L4.5 | Decision gate: do quality + throughput numbers warrant proceeding to L5 (dedicated op) or stopping at v1? | PENDING | Driven by L4.1-L4.4 results |

**Test path options to confirm with user before L4 starts**:
- (a) Pre-existing Ring-mini Q4_K_M from HF community quants (preferred if available)
- (b) Convert from Ant Group's BF16 release ourselves via L2 converter (~10 min one-time cost)

### L5 — Optional v2 dedicated `GGML_OP_LIGHTNING_ATTN` (~1 week)

**Goal**: write a specialized op that exploits constant `g` for prefill speedup.

**Trigger**: only if L4 results show prefill bottleneck attributable to repeated per-token `g` lookup vs precomputable `g^t` powers.

**Work items**:

| ID | Task | Status |
|----|------|--------|
| L5.1 | Profile L3 v1 with `GGML_PERF=1` at 8K / 32K prefill — identify if `g` lookup is the hotspot | PENDING |
| L5.2 | Design `GGML_OP_LIGHTNING_ATTN` with chunked precomputed `g^t` powers for chunkwise-parallel prefill | PENDING |
| L5.3 | Implement CPU path (mirror existing GLA structure but with chunked recurrence) | PENDING |
| L5.4 | Implement CUDA path (optional; depends on whether we want upstream contribution) | PENDING |
| L5.5 | Correctness gate: PPL bit-exact vs L3 v1 baseline | PENDING |
| L5.6 | Throughput improvement gate: ≥10% at 8K prefill, ≥20% at 32K prefill | PENDING |

## Decision Gates Summary

| Gate | Trigger | Action |
|------|---------|--------|
| **L1 GO** | GLA op semantics match Lightning Attention's recurrence | Proceed to L2 |
| **L1 NO-GO** | Shape mismatch / unsupported broadcast | Re-scope: L5 (dedicated op) becomes v1 |
| **L4 GO** | Smoke decode coherent + quality within ±5pp of paper | Hand to drafter eval (separate handoff) |
| **L4 NO-GO** | Quality collapse | Triage: precision drift? converter bug? Re-iterate L1-L3 |
| **L5 START** | L4 prefill profile shows `g`-lookup hotspot | Begin L5 |
| **L5 SKIP** | L4 prefill is already adequate, OR profile shows different bottleneck | Stop at v1; document |

## Risks / Caveats

1. **BF16 KV-state precision drift** (paper Section 7) — the recurrence accumulates error. Authors solve with FP32 accumulation in the linear path. Our current `ggml_compute_forward_gla_f32` uses F32 throughout, so this should be fine for v1; flag for L1.2 verification.
2. **Train/inference alignment requirement** — paper notes performance highly sensitive to decay coefficient (power-law vs linear swing 0.04 in training loss). Our llama.cpp port must match upstream numerics exactly. Bit-identical replication is the safer assumption; defer numeric optimizations to L5.
3. **FP8 LingHe kernels are GPU-only** — even when Lightning Attention lands in our llama.cpp, the FP8 efficiency claims don't transfer to CPU. Our v1 will be F16/F32 throughout. This is fine for correctness; just sets expectations on absolute throughput.
4. **Fixed power-law decay** (not learned per-token like GDN) means less expressivity per linear layer. Paper compensates with M=4 / M=7 ratios. Our port respects the architectural choice; we don't try to "fix" this.
5. **Hadamard q4_0 KV interaction unknown** — our deployed Hadamard KV path was tuned for standard attention, not linear-attention recurrence. If we ever try to combine Hadamard quant with Ring-mini, expect extra precision-drift issues. Out of scope for v1; flag for follow-on.
6. **Ant Group reference implementation may not be publicly fully accessible** — earlier WebFetch attempts to `inclusionAI/Ling-V2/inference/lightning_attn.py` returned 404. May need to extract the recurrence equation from paper Section 2 + Section 7 directly.

## Why This Matters (Activation Value)

Ring-mini-linear-2.0 is **957M active params, 16B total** — well inside our drafter / Q-scorer territory. A working port unlocks:

1. **A new candidate small drafter for spec-dec experiments**. Architecture mismatch with Qwen target (Ring uses Lightning; Qwen uses GDN) is a research question, not a default-yes. But the size + reasoning quality (86.51% AIME-25 on Ring-flash) is unusual.
2. **Reasoning capability at ~957M active params**, comfortably fitting in 1.1 TB RAM with massive headroom for parallel instances or long context.
3. **Validation data point** for the M-sweep finding (M=4 for 16B vs M=7 for 104B) on our own measurement infrastructure — independently informative for Qwen3.5/3.6 hybrid analysis (Qwen3.5-35B uses 30/40 = M=3 effective).
4. **Continuation of the "intermediate path" thesis** alongside `log-linear-gated-deltanet-readiness.md` — both architectures aim for sub-quadratic compute with matmul-rich CPU-friendly forms.

## Cross-References

- intake-503 (parent paper) — full architecture details + paper-claim numbers
- `/workspace/research/deep-dives/ling-linear-lightning-attention-hybrid.md` — corrected effort estimate + audit findings
- `ggml/src/ggml-cpu/ops.cpp:10605` — `ggml_compute_forward_gla_f32` implementation
- `src/models/models.h:23` — `llm_build_delta_net_base` (parent class)
- `src/models/kimi-linear.cpp` — closest existing template
- `convert_hf_to_gguf.py` — converter to extend in L2
- arxiv:2401.04658 (Lightning Attention parent paper, Qin et al. 2024)
- arxiv:2501.08313 (Minimax-01, predecessor at 7:1 hybrid)

## Notes

The original "defer indefinitely / multi-week port" framing was wrong. Lesson recorded: **before claiming an implementation is multi-week, audit the existing op space.** A 30-second `grep -nE "(GGML_OP_GATED_LINEAR_ATTN|llm_build_delta_net_base)"` against `llama.cpp-experimental` revealed the kernel + base class were already in place.

Per `feedback_no_concurrent_inference.md`: every step in L4 (and L5) requires explicit user approval before execution. Steps L1-L3 are pure code/audit and don't need inference; L1-L3 can proceed without inference gates.
