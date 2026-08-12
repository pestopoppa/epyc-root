# Log-Linear Gated DeltaNet — Readiness Tracker

**Status**: **GATES FIRED 2026-08-12** — all three activation gates are satisfied; this is no longer a monitoring-only tracker. See [§ Activation Evidence — 2026-08-12](#activation-evidence--2026-08-12).
**Created**: 2026-04-14 (via research intake deep dive)
**Updated**: 2026-08-12 (gates re-checked against the live sources; all three fired)
**Categories**: ssm_hybrid, context_extension, inference_serving
**Priority**: HIGH (strategic) — activates when gate criteria met

## 2026-07-26 Staleness Review

> **SUPERSEDED 2026-08-12** — this review, and the "Status as of 2026-04-21" section below, both report
> "no checkpoint". That was wrong from 2026-02-13 onward; neither review queried HuggingFace. Read
> [§ Activation Evidence — 2026-08-12](#activation-evidence--2026-08-12) instead. Kept for provenance.

The [design-backlog triage](design-backlog-triage-2026-07-23.md) still
classifies the public path as training-only and requires both a pretrained
checkpoint and an inference reference. Neither implementation gate is recorded
as satisfied, so this remains monitoring-only.

## 2026-05-28 Audit Reset — Executor Start Here

This is not an implementation queue yet. The highest-value action is a disciplined readiness check; starting a GGML port before the gate fires will create speculative code without a model to validate.

| Gate state | Action |
|---|---|
| No checkpoint, no inference reference | Keep monitoring only. Update the status date when checked. |
| Reference code appears but no pretrained checkpoint | Read the inference path and update expected GGML/state-management design, but do not implement. |
| Checkpoint appears but docs/reference are incomplete | Run a transformers-library smoke only if the model card exposes enough tensor names; otherwise hold for docs. |
| Checkpoint + inference code + architecture docs available | Activate the implementation plan below and open a concrete port branch. |

Minimum activation evidence to paste into this handoff:

```text
Checkpoint:
Reference inference entry point:
Tensor/name mapping source:
License:
Expected first model size:
Why this is Log-Linear Gated DeltaNet and not standard GDN:
```

Dependency and mitigation notes:

- `delta-mem-reproduction.md` may produce delta-rule GGML scaffolding first. If so, reuse that primitive instead of creating a parallel op family.
- `lightning-attention-port.md` is not a template for this implementation beyond "start from existing recurrence ops where possible"; Lightning's fixed-decay GLA path does not solve Log-Linear GDN's indexed state set.
- If upstream publishes only training code for another month, keep this active but do not claim an implementation slot.

## Status as of 2026-04-21

Backburner monitoring — no pretrained Log-Linear Gated DeltaNet checkpoint released yet (per HF/arxiv checks). Gate criteria unchanged. Stub retained as reference for rapid activation when upstream ships weights. Cross-ref intake-356 remains authoritative research context.

## Objective

Track readiness of Log-Linear Gated DeltaNet for deployment on EPYC. 75% of the production stack (Qwen3.5-35B-A3B: 30/40 layers) uses standard Gated DeltaNet. The Log-Linear variant (ICLR 2026, by Songlin Yang + Tri Dao + Yoon Kim) replaces the fixed-size hidden state with a logarithmically growing set of hidden states — O(L log L) complexity with <0.4% parameter overhead. When pretrained models emerge, implement in our llama.cpp fork and benchmark.

## Why This Matters

- **State size 4-10x reduction** (~2GB → ~200-500MB at 262K context) — enables sequential replay for speculation
- **O(log L) growth** makes 1M+ context feasible on same hardware (vs prohibitive ~6-8GB at 1M with standard GDN)
- **CPU-friendly**: matmul-rich parallel form maps to existing ggml infrastructure — no GPU-centric sparse kernels (unlike NSA/MoBA)
- **Highest strategic priority** in the sub-quadratic attention survey (see multiscreen-attention-evaluation.md)

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-356 | Log-Linear Attention (arxiv:2506.04761) | high | worth_investigating |
| intake-354 | Memory Caching: RNNs with Growing Memory (arxiv:2602.24281) | medium | worth_investigating |

## Gate Criteria

All must be true to activate implementation:

- [x] Pretrained Log-Linear Gated DeltaNet model checkpoint publicly available (any size) ✅ 2026-08-12 — `hanguo/log-linear-attention`, folder `gdn/`, public since 2026-02-13
- [x] Reference implementation (github.com/HanGuo97/log-linear-attention) includes inference code, not just training ✅ 2026-08-12 — `HGatedDeltaNetForCausalLM(…, GenerationMixin)` + `hattention/recurrent.py`; see the caveat below, it is not runnable as shipped
- [x] Model architecture documented sufficiently for GGUF converter implementation ✅ 2026-08-12 — full `config.json` + 423 named tensors read out of the safetensors header + HF modeling source

## Activation Evidence — 2026-08-12

Filed in the format the [2026-05-28 Audit Reset](#2026-05-28-audit-reset--executor-start-here) asks for.
Every line below was read from the live artifact on 2026-08-12, not from a model card or the paper.

```text
Checkpoint:                      hanguo/log-linear-attention  (HF, public, not gated, lastModified 2026-02-13)
                                 subfolder gdn/  → model.safetensors, config.json, generation_config.json,
                                 tokenizer.json, LICENSE
                                 subfolder mamba-2/ → the log-linear Mamba-2 sibling (model_type "hattention")
Reference inference entry point: hattention/modeling_h_gated_deltanet.py
                                 HGatedDeltaNetForCausalLM(HGatedDeltaNetPreTrainedModel, GenerationMixin)
                                 .generate() + .prepare_inputs_for_generation() + past_key_values.update(
                                     recurrent_state=…, conv_state=(q,k,v), offset=…)
                                 hattention/recurrent.py — HState / step_state() / step_output() /
                                 hattention_recurrent(): the O(log L) recurrence in PURE PyTorch, no Triton
Tensor/name mapping source:      safetensors header of gdn/model.safetensors — 423 tensors, 795.690 M params, F32
License:                         MIT (gdn/LICENSE, "Copyright (c) 2023-2025 Songlin Yang, Yu Zhang" — the FLA
                                 licence, shipped inside the model folder). NOTE: the GitHub reference repo
                                 itself carries NO top-level LICENSE file (GitHub API reports license: null).
Expected first model size:       795.690 M params · hidden 1536 · 21 layers · 6 heads · head_dim 192 ·
                                 expand_v 2 (v head dim 384) · conv_size 4 · vocab 32000 ·
                                 max_position_embeddings 16384 · f32 → ≈3.2 GB on disk
Why this is Log-Linear GDN and not standard GDN:
                                 config model_type = "h_gated_deltanet" (the baseline variant in the same repo
                                 is model_type "gated_deltanet" — configs/flame/{h_,}gated_deltanet_mid.json are
                                 otherwise byte-identical), _name_or_path = ".../h_deltanet_mid.json", and the
                                 checkpoint carries the two tensors the baseline does not have:
                                   model.layers.N.attn.L       [6, 15]      per-head level weights (λ)
                                   model.layers.N.attn.l_proj  [90, 1536]   90 = 6 heads × 15 levels
                                 15 levels = ceil(log2 16384) + 1, i.e. the log-linear level set itself.
```

**How long this was available**: the checkpoint has been public since **2026-02-13**, i.e. it already existed
at the 2026-07-26 gate review and at the 2026-05-28 audit reset. The gate did not fire late because upstream
was slow; it fired late because the monitoring row was never actually executed against HF. The
[Monitoring Targets](#monitoring-targets) table names HF at *monthly* cadence — that cadence was not met.

### Caveat — the reference is NOT runnable as shipped (two concrete blockers)

Gate 2 is satisfied *as code*, but an executor who clones the repo and calls `.generate()` will not get output:

1. **The only wired compute path is Triton/GPU.** `HGatedDeltaNetAttention.forward` dispatches
   `if mode == 'chunk': chunk_h_gated_delta_rule(...)` and `else: raise NotImplementedError`. There is no
   `fused_recurrent` mode wired into the model, so `hattention/recurrent.py` — the pure-PyTorch, device-agnostic
   form — is **reachable only by editing the model**. It is nonetheless the right port reference (see below).
2. **An unshipped absolute path.** `hattention/base.py` holds
   `CACHED_LEVELS_MATRICES[(16384, 2, HType.WEAK, -1)] = "/export/share/experiments/20250202/llut/llut.length-16384.base-2.pth"`,
   an author-cluster path that is not in the repo. `make_levels_matrix()` defaults to `cached_length=16384`,
   so every chunkwise/parallel kernel call (`chunkwise_hgdn.py:630`, `chunkwise.py:1174`, `parallel.py:899`)
   hits that key and `torch.load`s a file nobody outside the authors' cluster has. Removing the dict entry makes
   the function fall through to its own `get_level_index()` computation — correct, but an O(L²) Python double
   loop at L=16384 (≈2.7·10⁸ iterations), so it wants doing once and caching via the function's `file_name=` arg.

**Consequence for our port**: port from `hattention/recurrent.py`, not from the chunkwise kernels. The recurrent
form needs **no** level lookup table at all — `HState.cascade_weak()` derives the level from per-level counters
(`counts[level] == base**level` → carry into `level+1`), which is a ggml-friendly integer state machine. The L×L
LUT exists only to materialise the mask for the parallel/chunk forms. This changes step 4 of the plan below.

### Correction — the "state size 4-10x reduction" bullet has no named baseline

[Why This Matters](#why-this-matters) claims *"State size 4-10x reduction (~2GB → ~200-500MB at 262K context)"*
directly under a paragraph framing this as the replacement for the **standard GDN** in 75% of the production
stack. Measured on the released checkpoint, that reading is **backwards**: log-linear GDN's recurrent state is
the standard GDN state replicated across the level set, so per layer

| | recurrent state (this checkpoint's dims) | 21 layers, f32 |
|---|---|---|
| standard GDN | 6 heads × 192 (d_k) × 384 (d_v) | ≈37 MB |
| log-linear GDN | 6 × 192 × 384 × **15 levels** | ≈557 MB |

— a **15× increase** versus standard GDN, not a reduction. The reduction is real but is against **softmax
attention's KV cache**, which grows linearly in L while both GDN forms are constant in L. State the baseline
whenever this number is quoted. Two further facts the bullet elides: the released architecture's level count is
a **fixed 15** (tensor `L [6, 15]`) with `max_position_embeddings` 16384 — a 262K-context claim needs 19 levels
and therefore a different checkpoint — and the level set is constant in L, so "at 262K context" does not qualify
the log-linear number at all.

### Next actions now that the gates have fired

- [ ] Wire `hattention_recurrent()` into `HGatedDeltaNetAttention.forward` behind a `mode='fused_recurrent'`
      branch in a local clone, and confirm it reproduces the chunk path's logits on a short prompt. This is the
      numerical oracle every later ggml step is checked against; without it the port has no reference output.
      **CPU-only, no GPU needed** (pure PyTorch, ≈796 M params f32 ≈ 3.2 GB).
- [ ] Write the GGUF converter tensor map from the 423-name safetensors header; the only non-GDN names are
      `attn.L`, `attn.l_proj.weight` and the level count, so it is standard-GDN mapping plus two entries.
- [ ] Re-scope plan step 4 below: `ggml_log_linear_state_update()` is the `cascade_weak()` counter machine plus
      the existing delta-rule update; `ggml_log_linear_attention()` is `step_output()` = a λ-weighted contraction
      over the level axis. Neither needs the L×L level LUT.
- [ ] Operator decision, once the oracle above exists: this checkpoint is a **795 M research model at f32 with a
      16K position limit** — it validates the port but is not itself deployable. Decide whether the port is
      justified by the checkpoint alone or should wait for a production-scale log-linear GDN.

## Implementation Plan (triggered when gate criteria met)

1. Clone reference impl, verify architecture matches paper description
2. Implement GGUF converter for log-linear variant tensors
3. New model variant `llm_build_log_linear_delta_net` in `src/models/`
4. New ggml operators: `ggml_log_linear_state_update()`, `ggml_log_linear_attention()`
5. GGUF metadata extensions: `architecture = "log_linear_gated_delta_net"`, state index tensors
6. State management: O(log L) indices per-sequence in `llama-memory-recurrent.cpp`
7. Benchmark: perplexity, throughput, memory at 8K / 32K / 262K / 1M context lengths
8. If speculation replay viable: prototype sequential replay on O(log L) state

Estimated effort: 2-3 weeks from gate activation.

## Monitoring Targets

| Target | Signal | Cadence |
|--------|--------|---------|
| github.com/HanGuo97/log-linear-attention | New releases, model checkpoints | Weekly |
| github.com/NVlabs/GatedDeltaNet | Log-linear variant merge | Weekly |
| HuggingFace | Models tagged log-linear or using log-linear GDN | Monthly |
| llama.cpp upstream (ggml-org) | PRs for log-linear layer support | Monthly |
| arxiv.org | Qwen4 or next-gen models adopting log-linear GDN | Monthly |

## Open Questions

1. Is O(N x L x log L) sequential replay cost low enough for net-positive speculation on CPU?
2. Does O(log L) state set work with q4_K_M weight quantization and q4/q8 KV cache quantization?
3. Context-folding synergy: Log-Linear reduces state via O(log L) growth, Context-Folding reduces context via hierarchical summarization. Complementary?
4. Timeline for pretrained models — no public checkpoints as of 2026-04-14.

## Cross-References

- **Deep dive**: `research/deep-dives/memory-caching-log-linear-attention.md`
- **Survey**: `handoffs/active/multiscreen-attention-evaluation.md` (priority ranking, literature survey)
- **Intake**: intake-356 (primary), intake-354 (related MC analysis)
- **Chapters**: 10-advanced-speculative-decoding (Section 13: Delta Net speculation blocked)
- **Handoffs**: routing-intelligence.md (historical Delta Net / reasoning-trace risk notes preserved in the completed ledger linked from the active handoff)
- **Completed**: mtp-speculative-decoding.md, ssm-hybrid-acceleration.md (speculation exhausted on standard GDN)
- **Ref impl**: github.com/HanGuo97/log-linear-attention — 285 stars as of 2026-08-12, **last push 2025-06-06**
  (the repo is dormant, the checkpoint release happened on HF instead). No longer "training-only": it carries
  an HF `ForCausalLM` + a pure-PyTorch recurrence, with the two shipped-state caveats recorded above.
- **Checkpoint**: huggingface.co/hanguo/log-linear-attention — `gdn/` (log-linear GDN, 795.690 M) and
  `mamba-2/` (log-linear Mamba-2, `HAttentionForCausalLM`). Public 2026-02-13, MIT, not gated.

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-488] "Speculative Decoding with Mamba"** (github.com/itsdaniele/speculative_mamba; arxiv:2408.15237) — Pure-Mamba target+draft spec-dec; CUDA-only; no Delta-Net coverage. Verdict: not_applicable.

- **[intake-489] "SpecMamba: Accelerating Mamba Inference on FPGA with Speculative Decoding"** (arxiv:2509.19873)
  - Relevance: Memory-aware hybrid backtracking strategy directly addresses the SSM hidden-state rollback problem that has blocked spec-dec on hybrid SSMs (chapter 10 §13). FPGA hardware-bound but algorithmic frame is reusable.
  - Reported results: 2.27× over GPU, 2.85× over prior FPGA Mamba.
  - Delta: FPGA-only — no CPU port path. Catalog as algorithmic reference for if/when Delta-Net spec-dec is reopened with proper rollback semantics.

- **[intake-490] "Hybrid Models Meet SGLang: More than Full Attention"** (pytorch.org blog, Dec 2025) — verdict: **adopt_patterns**
  - Relevance: SGLang's resolution of in-place SSM state updates (MambaRadixCache + HybridReqToTokenPool + EAGLE/MTP rollback over SSM state) demonstrates that "spec-dec dead on hybrid SSM" is solvable in principle on the architecture side. Direct counter-evidence for the chapter-10 §13 blocker if/when CPU-side rollback semantics are implemented in llama.cpp.
  - Reported results: 324.57 tok/s, accept length 4.231 on Qwen3-Next-80B-A3B-FP8 (H200) with EAGLE/MTP.
  - Delta: CUDA/H200/FP8 only — does not run on EPYC, but four named primitives (HybridReqToTokenPool, HybridLinearKVPool, MambaRadixCache, Elastic Memory Pool) form the reference design that GDN serving on llama.cpp would need to mirror.

- **[intake-491] "Mamba Drafters for Speculative Decoding"** (arxiv:2506.01206; Findings of EMNLP 2025)
  - Relevance: External SSM drafter is the inverse direction of GDN serving — uses an SSM as the cheap drafter rather than the expensive target. MAB-optimized tree-shape selector applies orthogonally.
  - Reported results: At 8k context, Mamba 52GB total memory vs EAGLE 72GB; throughput preserved while Transformer drafters degrade.
  - Delta: principle generalizes to GDN drafters once a small Delta-Net or hybrid is available. Track alongside readiness for log-linear GDN target inference.

## Research Intake Update — 2026-06-12 (from the intake-694 open-weights roundup)

- **NVIDIA Nemotron-3-Ultra-550B-A55B** (hybrid Transformer-**Mamba2** MoE, 55B active) — **CORRECTION to intake-694's "GPU/NVFP4-gated" framing: it has CPU-runnable GGUFs** (unsloth / DevQuasar BF16 + Q4; Q4_K_M ≈ 300 GB RAM, fits our 1.1 TB host; build `-DGGML_CUDA=OFF`). This is **not** Log-Linear Gated DeltaNet and **does NOT fire this readiness gate**, but it is the first in-RAM Mamba2-hybrid MoE available as a concrete artifact to smoke-test the hybrid-SSM CPU decode / state-management path on our fork. **Pre-req:** verify it doesn't hit the Nemotron-Nano `mamba-base.cpp:173 GGML_ASSERT` (ggml-org/llama.cpp#20570) first; MTP is unsupported in GGUF. **P1 follow-up — warrants its own intake entry.** See `research/deep-dives/2026-06-12-open-weights-roundup-followups.md`.
