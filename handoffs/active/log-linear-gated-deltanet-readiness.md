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

### Gate Criteria — portability addendum (added 2026-08-22, wave-2 Stage-2b)

Two further gates. They apply to **every** candidate on the
[GDN branch map](#the-gdn-branch-map-z--recorded-no-action), this one included, and they exist because
the three gates above **cannot tell apart three cases the wave put side by side**. They do **not**
retract the 2026-08-12 activation: gates 1–3 stand fired, and these two are the portability screen
those three could not express.

- [ ] **Gate 4 — a device-agnostic (non-Triton) numerical oracle exists.** Not "reference code exists"
      (gate 2) but "reference output can be produced on a CPU, to check a ggml port against".
      Log-linear GDN has the *code* — `hattention/recurrent.py`, pure PyTorch — but it is not wired
      into the model, so the gate is **open for log-linear too**; closing it is the first bullet under
      [Next actions](#next-actions-now-that-the-gates-have-fired). Gated DeltaNet-2 (intake-1281#record)
      is the inverse: a better decode path and **no** non-Triton path at all.
- [ ] **Gate 5 — a ggml primitive exists for every mixer type in the architecture, or a
      numerically-correct fallback is identified for those that lack one.** MiniCPM-SALA
      (intake-1287#record) fires all three original gates and is still not fully portable — its
      InfLLM-V2 block-sparse selection has no ggml op, and only the *fallback* clause rescues it (the
      vendor's own reference runs those layers dense whenever CUDA is unavailable). Log-linear GDN
      fails this gate today: `ggml_log_linear_state_update()` and `ggml_log_linear_attention()` do not
      exist.

**Why this is not bookkeeping.** Gates 2 and 4 came apart in *opposite directions* on two candidates
in a single wave. A gate list that scores both as "reference implementation available" cannot tell you
which port has something to check its output against — and that is the distinction that decides
whether a port is startable at all.

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

**A second reference point on the same axis — Gated DeltaNet-2 at 1.0× state (intake-1281#record).**
The table above has one data point on the state-size axis and it is an outlier (15×). GDN-2 is the
other end: it replaces GDN's scalar delta gate with a channel-wise erase gate on the key axis and a
channel-wise write gate on the value axis, and its recurrent state is **byte-identical in size** to
GDN's and KDA's — Appendix E.1 matches all three at `H · d_k · d_v` = 16 · 128 · 128 = 262,144 floats
per layer per batch element. It changes *how the state is edited*, not how large it is. The cost moves
somewhere else entirely: two full-rank per-layer projections (`d_model → H·d_k` and `d_model → H_v·d_v`)
that no pretrained GDN checkpoint contains, ≈ **+375.5 M always-active dense parameters** on our
architecture, ≈ **+12.5 %** active parameters for **zero** state saving. **Quote the state-size axis
and the active-parameter axis together or the comparison is meaningless** — log-linear buys context
scaling with 15× state; GDN-2 buys update expressiveness with +12.5 % active weights; PGDN buys it
with ~0.8 %. That is the shape of the branch, and no row of it is free.

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
2. **Add tensor entries to the existing converter package** — not "write a converter". At
   `0db32c06e3e5` the converter is a **package**: `convert_hf_to_gguf.py` is a 296-line CLI shim with
   **zero** `ModelBase.register` calls, and every architecture is registered under `conversion/`
   (`conversion/qwen.py:271` `@ModelBase.register("Qwen3NextForCausalLM")`; `:623` and `:628`
   `Qwen3_5ForCausalLM` / `Qwen3_5MoeForCausalLM` → `MODEL_ARCH.QWEN35` / `QWEN35MOE`;
   `conversion/kimi_linear.py:15` `KimiLinearModel`). **A literal grep of `convert_hf_to_gguf.py`
   returns zero registrations for EVERY architecture in the tree**, so that probe cannot distinguish a
   supported arch from an unsupported one — a textbook *PROBE outside the tool* vacuous negative
   (`feedback_vacuous_verification_empty_input`). The GDN family **is** supported; the work here is the
   two extra tensor names (`attn.L`, `attn.l_proj.weight`) plus the level count, added to the existing
   package. Verified read-only against the frozen tree 2026-08-23.
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
| `fla-org/flash-linear-attention` → `fla.models` | `GatedDeltaNet2ForCausalLM` appearing (today `fla.layers` + `fla.ops` carry GDN-2, `fla.models` does not) — the adoption signal that would reopen the declined GDN-2 port | Weekly, **pin the checked revision** (last checked `bc3b101dcb713d`) |
| llama.cpp upstream PR #27018 — `LLM_ARCH_MINIMAX_01` | **Already merged 2026-08-14**, four days after the v9 freeze point `0db32c06e3e5` (committed 2026-08-10T21:54:03Z), so it is post-v9 and absent from our tree — which carries `LLM_ARCH_MINIMAX_M2` but not `_01`. Lightning-attention decay slopes on hybrid recurrent memory: the closest existing template for any constant-decay-GLA linear half. Watch for follow-ups and fixes | On any v10 candidate, else monthly |

**Pin the revision every time you check a row in this table.** Not a style preference: the HuggingFace
row above is *monthly* and was not executed, which is the sole reason the log-linear gate fired six
months after the checkpoint went public (see [How long this was
available](#activation-evidence--2026-08-12)). A row whose last-checked state is unrecorded cannot be
distinguished from a row that was never checked.

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

## Research Intake Update — 2026-08-21 (Stage-2b wave, intake-1271…1279)

Nine sources were ingested and dived. Every row below carries a **compute class**: **Z** zero-compute
(executable now), **G** compute-gated (names the measurement and what result opens the gate), or
**B** blocked-on (names its upstream item). A `G` row without a named opening result is a defect.

### The GDN branch map (Z — recorded, no action)

Five structurally different answers to GDN's fixed-state forgetting are now indexed — the fifth added
2026-08-22. They are easy to conflate and the distinction is load-bearing:

| Branch | Lever | Entry | Standing |
|---|---|---|---|
| Grow the state | O(L log L) hidden states | intake-356 | gates fired, port not started |
| Segment checkpoints | O(NL) | intake-354 | reference only |
| Bounded exact side-cache | leave the state fixed, bolt on a bounded cache | intake-1272 (LTE), intake-1268 (HOLA) | **LTE opened the branch 8.5 months before HOLA** |
| **Fix the update rule** | diagonal key-Gram preconditioner, state size unchanged | **intake-1273 (PGDN)** | **new fourth branch — no checkpoint, gate 1 CLOSED** |
| **Offload recall to a sparse-attention minority** | 8 of 32 layers do block-sparse **exact** attention at 2 KV heads; the linear state stays lossy and simple | **intake-1287 (MiniCPM-SALA)** | **new fifth branch — Apache-2.0 9B checkpoint released; a dense-fallback port needs zero new ggml ops** |

**Two things about the fifth row that a one-line summary will get wrong, and both are load-bearing.**
(a) **SALA's linear primitive is constant-decay Simple GLA, not Gated DeltaNet.** The paper says
"Lightning Attention" throughout; the released code calls `fla.ops.simple_gla`
(`chunk_simple_gla` / `fused_recurrent_simple_gla`) with `g_gamma` from `_build_slope_tensor()` — the
parameter-free ALiBi power-of-2 slope schedule, no delta rule, no data-dependent gate. Three
independent implementers read it the same way. So SALA does **not** sit on the GDN branch and bears on
the log-linear port only by analogy. (b) **Its memory is O(N) at 8 KiB/token, not O(1).** Its 8 sparse
layers keep the **full** KV cache — the paper names this "sparse computation, dense storage" and does
not solve it, it shrinks it (8 layers × 2 KV heads × 128 head_dim × 2 (K+V) × 2 B = 8,192 B/token, so
8 GiB at 1M, plus a constant ~48 MiB fp32 recurrent state). It must therefore **not** be filed under
"bounded exact side-cache" alongside LTE and HOLA, whose whole claim is a *bounded* cache. Both facts
are from the released artifact rather than the prose (intake-1287#record).

**PGDN is the only one in the cluster with a near-zero state cost** — one d_k vector per head against
the existing d_k×d_v matrix (~0.8 %), versus the log-linear branch's measured ~557 MB vs ~37 MB
(15× *increase*). It is also the smallest llama.cpp delta of the four. Gate 1 is nonetheless shut:
it adds weight tensors no pretrained GDN checkpoint contains, and no PGDN checkpoint exists anywhere.

**Do not cite LTE as evidence the bounded-cache branch works.** Its own Table 2 shows plain GDN
beating it 88.9 → 83.1 on RULER S-NIAH at 1.4B, the advantage *inverts* across its single scaling
step, nothing is measured beyond its 4096 training length, and it was withdrawn from ICLR 2026.

### Tasks

- [ ] **G1 (G) — #27442 boundary sweep on our CPU.** Frozen v9, frontdoor GGUF Q8_0, at 15,401 /
      16,501 / 17,601 / 19,801 / 23,981 prompt tokens. **Greedy (`temp 0`, fixed seed)**,
      `cache_prompt=false`, `-np 1`, no speculation. **Two prompt classes**: repeated-pangram filler
      *and* a semantically meaningful document carrying a real instruction. Record the **first sampled
      token id** per trial.
      **Gate:** valid EOS as first token on the *meaningful* prompt → real exposure, escalate. Only on
      filler → model behaviour on degenerate input, close it. Neither → not reproducible on our path.
      **Why it is not optional:** intake-1279 established that the upstream reporter's own log refutes
      their diagnosis (`n_prompt_tokens_cache = 0` on all 14 requests — no cache, cold full prefill),
      that their exonerating control cannot detect wrong output at all, and that **nobody has tested
      any backend but Metal**. Our shared hybrid/recurrent code is byte-identical to the reproducing
      build. Exposure is a live *unknown*, not a confirmed risk — and no greedy trial exists anywhere.
- [ ] **B1 (B, blocked on G1) — repeat the sweep on MI210 HIP.** Our HIP GDN kernel is a distinct
      implementation still carrying a TODO for a chunked prefill kernel, so a CPU result does not
      transfer; and running HIP first leaves nothing to compare against.
- [ ] **G5 (G, blocked on G6 in `rocm-verify-profile-backend.md`) — HOLA frozen-backbone retrofit.**
      Run it as a *within-checkpoint delta*: measure ppl with `use_gdn_swa` false, freeze, fit the
      12,480 trainable scalars, measure again. **Needs neither a corpus nor a layer-count match to
      HOLA**, so run it on **both** substrates (`m-a-p/340M-20B-GatedDeltaNet-pure-baseline` and
      `puigde/gated-deltanet-360M-15B-slimpajama`) to control for substrate idiosyncrasy.
      **Gate:** a measurable ppl improvement from 12,480 frozen-backbone scalars.
      **Two prerequisites, both Z:** HOLA ships **no freeze entrypoint** (~10 lines of `requires_grad`
      logic to write), and the m-a-p checkpoint needs a state-dict adapter — drop 24 legacy
      `attn.D` tensors and decide `tie_word_embeddings` (the checkpoint is untied, HOLA's config
      expects tied). `load_state_dict(strict=True)` fails until then. **Assert
      `ShortConvolution.backward` is never invoked before trusting any ROCm number** (see fla #1156).
- [ ] **B4 (B, blocked on G5) — hybrid-transfer A/B.** Repeat the retrofit on
      `m-a-p/340M-20B-GatedDeltaNet-hybrid-3-1`, matched to the pure arm by construction (same corpus,
      same budget, same library). This converts "does a pure-GDN result predict anything for our
      30-GDN + 10-attention production hybrid?" from argument into measurement. A pure-GDN gain is an
      **upper bound** on what our stack would see, because our 10 full-attention layers already supply
      the exact recall HOLA's cache exists to restore.
- [ ] **(Z) Record the m-a-p ratio-convention correction before anyone cites their band.** Their
      "N:1" means *one attention layer every N layers* (attention fraction 1/N), **not** the literal
      linear:full count — `hybrid-3-1` is 8 attention layers of 24. Our production 10-of-40 is
      therefore **"4:1" in their convention**, which is *not* one of their five trained arms; it sits
      between 3-1 and 6-1, inside their recommended band under either reading.

### Verification for the above

`bash scripts/validate/validate_intake.sh` → 0 and `python3 scripts/handoffs/index_state.py --check`
→ 0 before committing. For **G1**, the run is only valid if the *meaningful-prompt* arm is present —
a filler-only sweep reproduces the upstream defect in evidentiary quality and settles nothing.

## Research Intake Update — 2026-08-22 (Stage-2b wave, intake-1280…1294)

Row ids in this section are **wave-2 plan ids** and do **not** continue the 2026-08-21 section's
numbering — `G16` and `B9` below are unrelated to `G1` / `B1` / `G5` / `B4` above. Compute classes as
before: **Z** zero-compute, **G** compute-gated (names the measurement, the owning handoff, and the
result that opens the gate), **B** blocked-on (names its upstream item).

### The hybridization-ratio convention: our stack is ρ = 4 (Z — recorded)

`arXiv:2608.12149` (intake-1280#record) defines it in §2 Preliminaries, p.3, verbatim:

> Letting L_FA = |I_FA|, we define the hybridization ratio as rho = L/L_FA; thus, a rho:1
> configuration contains one full attention layer per rho sequence-mixing layers. Larger rho
> corresponds to sparser full attention, whereas rho = 1 recovers a full attention model.

Table 4 confirms the reading (Hybrid-3:1 = 16 linear + 8 full of 24). **Production Qwen3.6-35B-A3B is
10 full-attention layers of 40, therefore ρ = 4** — corroborated from our own code rather than only
from the paper: `src/models/qwen35moe.cpp:25-30` defaults `full_attn_interval = 4` and marks layer *i*
recurrent iff `(i+1) % 4 != 0`, putting attention at layers {3, 7, …, 39}; `:33-36` switches n_layer
40 / 48 / 60 to 35B_A3B / 122B_A10B / 397B_A17B.

**Cite §2 and Table 4. Never cite Appendix C.1.** The paper contradicts itself there: Appendix C.1
calls Qwen3.5 "a fixed 3:1 pattern" while stating *in the same sentence* that it has 40 layers with 10
full attention. That is the informal literal "three GDN layers then one attention layer" sense, not
the ρ its own §2 defines. Two consequences follow, and both bite: anyone citing "Qwen3.5 is one of
their 3:1 arms" is wrong twice — Qwen3.5 is not an M-A-P arm at all (it is a separately evaluated open
checkpoint), and by the paper's own ρ it sits at **4**, *between* the 3:1 and 6:1 arms.

This **corroborates and does not replace** the m-a-p ratio-convention row already filed in the
2026-08-21 section above: two papers, two conventions, one answer for us (ρ = 4, attention fraction
1/4). Do not open a second row for it. The MA-exposure consequence of ρ = 4 is recorded in
[tq3-quantization-evaluation.md](tq3-quantization-evaluation.md), which owns the KV-quantization axis.

### GDN op-test coverage stops ~8–32× below the reported problem band (Z — recorded, feeds G16)

Read from the frozen tree at `0db32c06e3e5` on 2026-08-23, read-only:

- `tests/test-backend-ops.cpp` holds **50** `test_gated_delta_net` **eval** cases — the ones that
  assert numerics. The largest `n_seq_tokens` among them is **256**
  (`test_gated_delta_net(GGML_TYPE_F32, 4, 64, 256, 1)`).
- The 512 and 1024 shapes exist **only** in `make_test_cases_perf()` (`32, 128, 512, 1` and
  `32, 128, 1024, 1`, plus a 4-head pair). **Perf cases assert nothing.** Anyone grepping this file
  for "1024" will conclude we have coverage there. We do not.
- Sharper than a length count, and it is what shapes G16: every eval case that reaches 64–256 tokens
  runs at `head_count=4, head_size=64`. **Our production geometry — H=32, d=128 — appears in the eval
  set only at `n_seq_tokens = 1`.** Long-token coverage and production-geometry coverage are disjoint
  sets, so neither one implies the other.

Chunked-GDN numerical problems are reported in the 2048–8192-token band (intake-1290#record), i.e.
**~8–32× above where our assertions stop**. This is the gap G16 exists to close, and it is why G16's
first deliverable is *new eval cases*, not a benchmark.

(The bare 256-token ceiling is already noted in the completed K28 correction landed by `89049772`.
What is new here, and what determines what G16 must actually add, is the 50-case count, the
**perf-only** status of the 512/1024 shapes, and the length/geometry disjointness.)

### Tasks

- [ ] **G16 (G) — numerical fidelity of a chunked GDN kernel at long prompts.** On
      `llama.cpp-experimental` branched from the **current production tip** (never v9):
      `test-backend-ops -o GATED_DELTA_NET -b ROCm0`, **plus new eval cases at `n_seq_tokens`
      2048 / 4096 / 8192 at our H=32 d=128 geometry** — per the coverage gap above, today neither the
      length nor the geometry is asserted, so importing the kernel without them tests nothing. Then a
      greedy A/B, chunked vs recurrent, at 2K / 8K / 16K / 24K on a **semantically meaningful**
      document, comparing first-sampled-token id and full output bytes.
      **Gate:** NMSE under the **unrelaxed** 1e-7 at every shape **or** byte-identical greedy output at
      every length. **A relaxed threshold is not a pass.** The third-party gfx90a validation already
      reports 2.97e-7 / 3.70e-7 against a 2e-7 gate, and the shape that fails is the **longest** one
      (T=2048) — exactly where reassociation error is expected to grow, since the chunked form is
      algebraically equivalent to the per-token recurrence in exact arithmetic but not in floating
      point (intake-1290#record). Relaxing the threshold deletes the only signal this row carries.
      **Owner:** this handoff. **Named consumers:** `G15` and `B5` in
      [mi210-big-model-and-acceleration-roadmap.md](mi210-big-model-and-acceleration-roadmap.md);
      neither may proceed on a chunked kernel this row has not cleared.
      Both compute planes were held by other sessions through this wave — **filed, not run**.
      **MEASURED 2026-08-24 — PASS.** 57/57 eval cases on ROCm0 vs CPU reference, unrelaxed 1e-7:
      H=32/d=128 recurrent 0.0 (1/64/256 tokens), chunked 8e-10 (keep_rs K=4/512), 4e-10 (K=12/520),
      **8.80e-8 / 9.04e-8 / 9.30e-8 at n_seq_tokens 2048/4096/8192** — below 1e-7 at every shape
      including the longest; PR H=48 geometry ≤ 9.07e-8. Chunked dispatch proven at every H=32
      ≥512-token case (blocks=256 ≥ floor 208). New H=32/d=128 eval cases (64/256/2048/4096/8192 +
      keep_rs) added on branch `ak/g15-chunked-gdn-20260823` @ 7abbd9afb and retained as permanent
      regression coverage. G15/B5 may proceed on the kernel's numerics; B5's stacking constraint
      stands (do not stack chunked on `GGML_CUDA_GDN_STATE_BF16`).
- [ ] **B9 (B) — GDN-2 zero-loss retrofit initialization, and the β ∈ [0,2] control the paper
      omitted.** Filed as **tracked-not-scheduled**, in two halves with different upstreams.
      **(a) Retrofit initialization.** Broadcast each head's scalar β and α across channels to recover
      plain GDN exactly inside an `fla.layers.GatedDeltaNet2` layer and confirm logits match at step 0
      to fp tolerance — one layer, PyTorch, CPU-feasible. **Blocked on the ROCm 6.2 / gfx90a
      torch+triton feasibility probe (`G6` in
      [rocm-verify-profile-backend.md](rocm-verify-profile-backend.md))**: there is no environment on
      this host in which that layer can currently be instantiated, and the fla floor is `>=0.5.2` —
      falling back to 0.4.2 is forbidden. If the equivalence holds, continued-pretraining retrofit is
      mathematically free of a cold start, which is the only route by which GDN-2 reaches our stack
      without a from-scratch run.
      **(b) β ∈ [0,2] on the plain Gated DeltaNet baseline.** The control the paper never ran: it
      tested the Grazzi negative-eigenvalue variant *on GDN-2* and found "no consistent gain at this
      scale" (Table 5), and never ran the converse on its own baseline. **Blocked on an external
      event**, named explicitly so this does not read as ours to schedule — a matched training run at
      ≥ 350 M, far outside our envelope. The realistic disposition is to watch someone else run it, via
      the `fla.models` monitoring row added above and via arXiv 2607.07953 (ETH/CSCS, the only
      independent GDN-2 evaluation in existence — hop-4, **not ingested**, recommended for a wave 3).
      Porting GDN-2 to ggml is a standing **decline on evidence**, not a compute block: 4/4 independent
      losses to plain GDN, the untested baseline control above, and +12.5 % active parameters for zero
      state saving (intake-1281#record). See also the static-analysis question `Z12` filed in
      [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md), which could shrink
      that +12.5 % and is zero-compute.

### Verification for the above

`bash scripts/validate/validate_intake.sh` → 0 and `python3 scripts/handoffs/index_state.py --check`
→ 0 before committing. For **G16**, a run that reports only `test-backend-ops` at the shipped shapes is
**not** this row: the new 2048/4096/8192 cases at H=32 d=128 are the row, and a pass at the shipped
shapes alone is a vacuous verification of the exact kind the coverage gap above describes.
