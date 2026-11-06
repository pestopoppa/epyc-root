# Log-Linear Gated DeltaNet — Readiness Tracker

> **Fold destination** (BRF-T7-F17, BRF-T7-1, route 1b, 2026-11-03): renamed from `log-linear-gated-deltanet-readiness.md`; every former handoff of this plan target is a `## Track:` with its own gate marker: `log-linear-gated-deltanet-readiness`, `engram-conditional-memory` (rows INF-13 retired into INF-33). The former `log-linear-gated-deltanet-readiness.md` body is `## Track: log-linear-gated-deltanet-readiness`; tracks those handoffs already had are lifted verbatim after their owner.

**Status**: **GATES FIRED 2026-08-12** — all three activation gates are satisfied; this is no longer a monitoring-only tracker. See [§ Activation Evidence — 2026-08-12](#activation-evidence--2026-08-12).
**Scratch**: `/mnt/raid0/llm/tmp/codex-ni-g16a-build-prep-20261031/` (retain with `KEEP` through G16 greedy A and B and coordinated champion integration) · `/mnt/raid0/llm/tmp/codex-ni-g16a-build-checkpoint-20261031/` (checkpoint patch and notification; clean after commit).
**Created**: 2026-04-14 (via research intake deep dive)
**Updated**: 2026-08-12 (gates re-checked against the live sources; all three fired)
**Categories**: ssm_hybrid, context_extension, inference_serving
**Priority**: MEDIUM — the log-linear GDN port waits for a production-scale model by operator decision (2026-11-02); what remains live is G16/G16b (feeds mi210 G15) and the unfunded Engram Track B bet

## Track: log-linear-gated-deltanet-readiness
<!-- gate: INF-48 -->

> Folded from the body of `handoffs/active/log-linear-gated-deltanet-readiness.md` (row INF-33), from its first `##` section on, @ `3f2a6604f6e1` on 2026-11-03 (BRF-T7-F17, route 1b, operator D1/D5). Headings demoted two levels; every box kept its text and ID.

#### 2026-07-26 Staleness Review

> **SUPERSEDED 2026-08-12** — this review, and the "Status as of 2026-04-21" section below, both report
> "no checkpoint". That was wrong from 2026-02-13 onward; neither review queried HuggingFace. Read
> [§ Activation Evidence — 2026-08-12](#activation-evidence--2026-08-12) instead. Kept for provenance.

The [design-backlog triage](../completed/design-backlog-triage-2026-07-23.md) still
classifies the public path as training-only and requires both a pretrained
checkpoint and an inference reference. Neither implementation gate is recorded
as satisfied, so this remains monitoring-only.

#### 2026-05-28 Audit Reset — Executor Start Here

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

#### Status as of 2026-04-21

Backburner monitoring — no pretrained Log-Linear Gated DeltaNet checkpoint released yet (per HF/arxiv checks). Gate criteria unchanged. Stub retained as reference for rapid activation when upstream ships weights. Cross-ref intake-356 remains authoritative research context.

#### Objective

Track readiness of Log-Linear Gated DeltaNet for deployment on EPYC. 75% of the production stack (Qwen3.5-35B-A3B: 30/40 layers) uses standard Gated DeltaNet. The Log-Linear variant (ICLR 2026, by Songlin Yang + Tri Dao + Yoon Kim) replaces the fixed-size hidden state with a logarithmically growing set of hidden states — O(L log L) complexity with <0.4% parameter overhead. When pretrained models emerge, implement in our llama.cpp fork and benchmark.

#### Why This Matters

- **State size 4-10x reduction** (~2GB → ~200-500MB at 262K context) — enables sequential replay for speculation
- **O(log L) growth** makes 1M+ context feasible on same hardware (vs prohibitive ~6-8GB at 1M with standard GDN)
- **CPU-friendly**: matmul-rich parallel form maps to existing ggml infrastructure — no GPU-centric sparse kernels (unlike NSA/MoBA)
- **Highest strategic priority** in the sub-quadratic attention survey (see multiscreen-attention-evaluation.md)

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-356 | Log-Linear Attention (arxiv:2506.04761) | high | worth_investigating |
| intake-354 | Memory Caching: RNNs with Growing Memory (arxiv:2602.24281) | medium | worth_investigating |

#### Gate Criteria

All must be true to activate implementation:

- [x] Pretrained Log-Linear Gated DeltaNet model checkpoint publicly available (any size) ✅ 2026-08-12 — `hanguo/log-linear-attention`, folder `gdn/`, public since 2026-02-13
- [x] Reference implementation (github.com/HanGuo97/log-linear-attention) includes inference code, not just training ✅ 2026-08-12 — `HGatedDeltaNetForCausalLM(…, GenerationMixin)` + `hattention/recurrent.py`; see the caveat below, it is not runnable as shipped
- [x] Model architecture documented sufficiently for GGUF converter implementation ✅ 2026-08-12 — full `config.json` + 423 named tensors read out of the safetensors header + HF modeling source

##### Gate Criteria — portability addendum (added 2026-08-22, wave-2 Stage-2b)

Two further gates. They apply to **every** candidate on the
[GDN branch map](#the-gdn-branch-map-z--recorded-no-action), this one included, and they exist because
the three gates above **cannot tell apart three cases the wave put side by side**. They do **not**
retract the 2026-08-12 activation: gates 1–3 stand fired, and these two are the portability screen
those three could not express.

- **[declined: ws58 2026-11-03 content-review: readiness criterion, not a task — the operator decided 2026-11-02 to wait for a production-scale log-linear GDN; the criterion stays readable here and research intake is the watch]** **Gate 4 — a device-agnostic (non-Triton) numerical oracle exists.** Not "reference code exists"
      (gate 2) but "reference output can be produced on a CPU, to check a ggml port against".
      Log-linear GDN has the *code* — `hattention/recurrent.py`, pure PyTorch — but it is not wired
      into the model, so the gate is **open for log-linear too**; closing it is the first bullet under
      [Next actions](#next-actions-now-that-the-gates-have-fired). Gated DeltaNet-2 (intake-1281#record)
      is the inverse: a better decode path and **no** non-Triton path at all.
- **[declined: ws58 2026-11-03 content-review: readiness criterion, not a task — same operator decision 2026-11-02; no port is scheduled]** **Gate 5 — a ggml primitive exists for every mixer type in the architecture, or a
      numerically-correct fallback is identified for those that lack one.** MiniCPM-SALA
      (intake-1287#record) fires all three original gates and is still not fully portable — its
      InfLLM-V2 block-sparse selection has no ggml op, and only the *fallback* clause rescues it (the
      vendor's own reference runs those layers dense whenever CUDA is unavailable). Log-linear GDN
      fails this gate today: `ggml_log_linear_state_update()` and `ggml_log_linear_attention()` do not
      exist.
      *(2026-11-04: the MiniCPM-SALA checkpoint (/mnt/raid0/llm/models/MiniCPM-SALA-HF-9180fe1d, 18 GB) was deleted by operator order because adoption was declined 2026-11-03; re-downloadable from HF. Intake citations above are research history.)*

**Why this is not bookkeeping.** Gates 2 and 4 came apart in *opposite directions* on two candidates
in a single wave. A gate list that scores both as "reference implementation available" cannot tell you
which port has something to check its output against — and that is the distinction that decides
whether a port is startable at all.

#### Activation Evidence — 2026-08-12

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

##### Caveat — the reference is NOT runnable as shipped (two concrete blockers)

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

##### Correction — the "state size 4-10x reduction" bullet has no named baseline

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

##### Next actions now that the gates have fired

- [x] Wire `hattention_recurrent()` into `HGatedDeltaNetAttention.forward` behind a `mode='fused_recurrent'`
      branch in a local clone, and confirm it reproduces the chunk path's logits on a short prompt. This is the
      numerical oracle every later ggml step is checked against; without it the port has no reference output.
      **CPU-only, no GPU needed** (pure PyTorch, ≈796 M params f32 ≈ 3.2 GB). [declined: operator 2026-11-03 model-audit: operator 2026-11-02: wait for a production-scale log-linear GDN; 795M research checkpoint not deployable]
- [x] Write the GGUF converter tensor map from the 423-name safetensors header; the only non-GDN names are
      `attn.L`, `attn.l_proj.weight` and the level count, so it is standard-GDN mapping plus two entries. [declined: operator 2026-11-03 model-audit: operator 2026-11-02: wait for a production-scale log-linear GDN; port parked with the oracle]
- **[declined: ws58 2026-11-03 content-review: superseded by the 2026-11-02 operator decision to wait for a production-scale log-linear GDN; the design note stays readable here for when a port is scheduled]** Re-scope plan step 4 below: `ggml_log_linear_state_update()` is the `cascade_weak()` counter machine plus
      the existing delta-rule update; `ggml_log_linear_attention()` is `step_output()` = a λ-weighted contraction
      over the level axis. Neither needs the L×L level LUT.
- **[declined: ws58 2026-11-03 content-review: resolved — operator decided 2026-11-02: wait for a production-scale log-linear GDN (decisions-batch2-4-20261102.json)]** Operator decision, once the oracle above exists: this checkpoint is a **795 M research model at f32 with a
      16K position limit** — it validates the port but is not itself deployable. Decide whether the port is
      justified by the checkpoint alone or should wait for a production-scale log-linear GDN.
  - 2026-11-02 operator decision: Wait for a production-scale log-linear GDN (decisions-batch2-4-20261102.json)

#### Implementation Plan (triggered when gate criteria met)

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

#### Monitoring Targets

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

#### Open Questions

1. Is O(N x L x log L) sequential replay cost low enough for net-positive speculation on CPU?
2. Does O(log L) state set work with q4_K_M weight quantization and q4/q8 KV cache quantization?
3. Context-folding synergy: Log-Linear reduces state via O(log L) growth, Context-Folding reduces context via hierarchical summarization. Complementary?
4. Timeline for pretrained models — no public checkpoints as of 2026-04-14.

#### Cross-References

- **Deep dive**: `research/deep-dives/memory-caching-log-linear-attention.md`
- **Survey**: `handoffs/active/long-context-program.md` (priority ranking, literature survey)
- **Intake**: intake-356 (primary), intake-354 (related MC analysis)
- **Chapters**: 10-advanced-speculative-decoding (Section 13: Delta Net speculation blocked)
- **Handoffs**: routing-intelligence.md (historical Delta Net / reasoning-trace risk notes preserved in the completed ledger linked from the active handoff)
- **Completed**: mtp-speculative-decoding.md, ssm-hybrid-acceleration.md (speculation exhausted on standard GDN)
- **Ref impl**: github.com/HanGuo97/log-linear-attention — 285 stars as of 2026-08-12, **last push 2025-06-06**
  (the repo is dormant, the checkpoint release happened on HF instead). No longer "training-only": it carries
  an HF `ForCausalLM` + a pure-PyTorch recurrence, with the two shipped-state caveats recorded above.
- **Checkpoint**: huggingface.co/hanguo/log-linear-attention — `gdn/` (log-linear GDN, 795.690 M) and
  `mamba-2/` (log-linear Mamba-2, `HAttentionForCausalLM`). Public 2026-02-13, MIT, not gated.

#### Research Intake Update — 2026-04-28

##### New Related Research

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

#### Research Intake Update — 2026-06-12 (from the intake-694 open-weights roundup)

- **NVIDIA Nemotron-3-Ultra-550B-A55B** (hybrid Transformer-**Mamba2** MoE, 55B active) — **CORRECTION to intake-694's "GPU/NVFP4-gated" framing: it has CPU-runnable GGUFs** (unsloth / DevQuasar BF16 + Q4; Q4_K_M ≈ 300 GB RAM, fits our 1.1 TB host; build `-DGGML_CUDA=OFF`). This is **not** Log-Linear Gated DeltaNet and **does NOT fire this readiness gate**, but it is the first in-RAM Mamba2-hybrid MoE available as a concrete artifact to smoke-test the hybrid-SSM CPU decode / state-management path on our fork. **Pre-req:** verify it doesn't hit the Nemotron-Nano `mamba-base.cpp:173 GGML_ASSERT` (ggml-org/llama.cpp#20570) first; MTP is unsupported in GGUF. **P1 follow-up — warrants its own intake entry.** See `research/deep-dives/2026-06-12-open-weights-roundup-followups.md`.

#### Research Intake Update — 2026-08-21 (Stage-2b wave, intake-1271…1279)

Nine sources were ingested and dived. Every row below carries a **compute class**: **Z** zero-compute
(executable now), **G** compute-gated (names the measurement and what result opens the gate), or
**B** blocked-on (names its upstream item). A `G` row without a named opening result is a defect.

##### The GDN branch map (Z — recorded, no action)

Five structurally different answers to GDN's fixed-state forgetting are now indexed — the fifth added
2026-08-22. They are easy to conflate and the distinction is load-bearing:

| Branch | Lever | Entry | Standing |
|---|---|---|---|
| Grow the state | O(L log L) hidden states | intake-356 | gates fired, port not started |
| Segment checkpoints | O(NL) | intake-354 | reference only |
| Bounded exact side-cache | leave the state fixed, bolt on a bounded cache | intake-1272 (LTE), intake-1268 (HOLA) | **LTE opened the branch 8.5 months before HOLA** |
| **Fix the update rule** | diagonal key-Gram preconditioner, state size unchanged | **intake-1273 (PGDN)** | **new fourth branch — no checkpoint, gate 1 CLOSED** |
| **Offload recall to a sparse-attention minority** | 8 of 32 layers do block-sparse **exact** attention at 2 KV heads; the linear state stays lossy and simple | **intake-1287#00 (MiniCPM-SALA)** | **new fifth branch — Apache-2.0 9B checkpoint released; a dense-fallback port needs zero new ggml ops** *(2026-11-04: the MiniCPM-SALA checkpoint (/mnt/raid0/llm/models/MiniCPM-SALA-HF-9180fe1d, 18 GB) was deleted by operator order because adoption was declined 2026-11-03; re-downloadable from HF.)* |

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

##### Tasks

- [x] **G1 (G) — #27442 boundary sweep on our CPU.** ✅ 2026-08-27 — **executed, gate verdict:
      NOT REPRODUCIBLE on our path (neither arm).** Frozen v9 (llama-completion, version 10125
      @ 0db32c06e), frontdoor Qwen3.6-35B-A3B-MTP-Q8_0, at 15,401 / 16,501 / 17,601 / 19,801 /
      23,981 prompt tokens, **greedy (`temp 0`, fixed seed 27442)**, `cache_prompt=false` (no
      `--prompt-cache` → cold prefill every trial; `--no-cache-prompt` is server-only in v9),
      single sequence, no speculation. Two prompt classes (seeded pangram filler + meaningful
      doc ending with a real instruction). **10/10 trials: first sampled token = 248068
      (`<think>`) on BOTH classes at ALL five lengths — a valid EOS was NEVER the first token,
      and no trial ended in EOS (`stop=completed` at the 1-token limit).** The meaningful arm
      ENGAGES the instruction (thinking start, not degenerate EOS); the filler arm behaves
      identically — the empty-completion exposure from #27442 does not reproduce on our frozen
      v9 CPU path at 15.4k-24k cold prefills. Trials + self-hashed manifest:
      `data/g1-27442-20260827T1537Z/`; 10 claims ingested, `Witnessed/Anchored` in the fold.
      **B1 note:** the CPU comparison baseline now exists; the HIP sweep is unblocked but remains
      a choice, not a requirement (the handoff's own "a CPU result does not transfer" caveat
      still holds for the GDN kernel's missing chunked-prefill TODO).
      *(Original spec: greedy temp 0 fixed seed, cache_prompt=false, np 1, no speculation,
      two prompt classes, first-sampled-token-id per trial.)*
      **Why it is not optional:** intake-1279#record established that the upstream reporter's own log refutes
      their diagnosis (`n_prompt_tokens_cache = 0` on all 14 requests — no cache, cold full prefill),
      that their exonerating control cannot detect wrong output at all, and that **nobody has tested
      any backend but Metal**. Our shared hybrid/recurrent code is byte-identical to the reproducing
      build. Exposure is a live *unknown*, not a confirmed risk — and no greedy trial exists anywhere.
- [ ] **B1 (G) — repeat the #27442 boundary sweep on the MI210 HIP path.** G1 (CPU) closed 2026-08-27 NOT REPRODUCIBLE, so the comparison baseline exists. Same design as G1: greedy temp 0 seed 27442, cache_prompt=false, np 1, no speculation, two prompt classes, 5 lengths 15.4k-24k, first-sampled-token id per trial, on the current :8083 GPU build and the 27B Q8 + DFlash2 off. Decision: 10/10 trials engage the instruction -> close (#27442 does not reproduce on our HIP path either); any degenerate-EOS trial -> file a kernel defect against the HIP GDN kernel. One GPU window, <= 1 h.
- **[declined: ws58 2026-11-03 content-review: curiosity with no path to a stack decision — by its own argument the production hybrid's 10 full-attention layers already supply the recall HOLA's cache restores, so a pure-GDN retrofit gain is only an upper bound; it also requires training on third-party 340M/360M checkpoints]** **G5 (G, blocked on G6 in `rocm-verify-profile-backend.md`) — HOLA frozen-backbone retrofit.**
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
- **[declined: ws58 2026-11-03 content-review: depends on G5 (retired above); same reasoning — a retrofit-training experiment on third-party checkpoints with no decision on our served models]** **B4 (B, blocked on G5) — hybrid-transfer A/B.** Repeat the retrofit on
      `m-a-p/340M-20B-GatedDeltaNet-hybrid-3-1`, matched to the pure arm by construction (same corpus,
      same budget, same library). This converts "does a pure-GDN result predict anything for our
      30-GDN + 10-attention production hybrid?" from argument into measurement. A pure-GDN gain is an
      **upper bound** on what our stack would see, because our 10 full-attention layers already supply
      the exact recall HOLA's cache exists to restore.
- [x] **(Z) Record the m-a-p ratio-convention correction before anyone cites their band.** Their ✅ 2026-10-29 (audit: correction already recorded in wiki/ssm-hybrid.md:422 (ratio-convention trap, "4:1" for our 10-of-40), compiled 3b2437034 2026-10-21) [no-belief: audit-reconciliation]
      "N:1" means *one attention layer every N layers* (attention fraction 1/N), **not** the literal
      linear:full count — `hybrid-3-1` is 8 attention layers of 24. Our production 10-of-40 is
      therefore **"4:1" in their convention**, which is *not* one of their five trained arms; it sits
      between 3-1 and 6-1, inside their recommended band under either reading.

##### Verification for the above

`bash scripts/validate/validate_intake.sh` → 0 and `python3 scripts/handoffs/index_state.py --check`
→ 0 before committing. For **G1**, the run is only valid if the *meaningful-prompt* arm is present —
a filler-only sweep reproduces the upstream defect in evidentiary quality and settles nothing.

#### Research Intake Update — 2026-08-22 (Stage-2b wave, intake-1280…1294)

Row ids in this section are **wave-2 plan ids** and do **not** continue the 2026-08-21 section's
numbering — `G16` and `B9` below are unrelated to `G1` / `B1` / `G5` / `B4` above. Compute classes as
before: **Z** zero-compute, **G** compute-gated (names the measurement, the owning handoff, and the
result that opens the gate), **B** blocked-on (names its upstream item).

##### The hybridization-ratio convention: our stack is ρ = 4 (Z — recorded)

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
[tq3-quantization-evaluation.md](quantization-and-low-bit.md#track-tq3-quantization-evaluation), which owns the KV-quantization axis.

##### GDN op-test coverage stops ~8–32× below the reported problem band (Z — recorded, feeds G16)

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

##### Tasks

- [ ] **G16 (G) — numerical fidelity of a chunked GDN kernel at long prompts.** On
      `llama.cpp-experimental` branched from the **current production tip** (never v9):
      `test-backend-ops -o GATED_DELTA_NET -b ROCm0`, **plus new eval cases at `n_seq_tokens`
      2048 / 4096 / 8192 at our H=32 d=128 geometry** — per the coverage gap above, today neither the
      length nor the geometry is asserted, so importing the kernel without them tests nothing. Then a
      greedy A/B, chunked vs recurrent, at 2K / 8K / 16K / 24K on a **semantically meaningful**
      document, comparing first-sampled-token id and full output bytes.
      **Gate:** NMSE under the **unrelaxed** 1e-7 at every shape **or** byte-identical greedy output at
      every length. **A relaxed threshold is not a pass.** The third-party gfx90a validation already
      reports 2.97e-7 / 3.70e-7 against a 2e-7 gate (that was PR #26001 + a third-party patch under the
      relaxed gate, not #24561 — intake-1434#record), and the shape that fails is the **longest** one
      (T=2048) — exactly where reassociation error is expected to grow, since the chunked form is
      algebraically equivalent to the per-token recurrence in exact arithmetic but not in floating
      point (intake-1290#record). Relaxing the threshold deletes the only signal this row carries.
      **Owner:** this handoff. **Named consumers:** `G15` and `B5` in
      [mi210-big-model-and-acceleration-roadmap.md](../completed/mi210-serving-program.md#track-mi210-big-model-and-acceleration-roadmap);
      neither may proceed on a chunked kernel this row has not cleared.
      Both compute planes were held by other sessions through this wave — **filed, not run**.
    - **Greedy diagnostic READY (2026-10-31):** the separate production-recipe-aligned HIP
      `97a82855...` passed fresh original eight-case `1e-7` controls. The original meaningful FA-on
      2048-token two-slot comparison completed with finite/nonconstant output and real chunked dispatch:
      first IDs matched, full UTF8 bytes **FAIL** (slot0 index45:198 vs1049; slot1 index109:2824 vs1326).
      Preserve the counterexample; execution completion is separate from scientific verdict. A128-token
      same-arm prefix replay varied slot0 in both arms, while slot1 matched; no unique GDN causality or
      statistical inference follows. [belief: cc]
      MAIN approved and NI published the full diagnostic manifest
      `/mnt/raid0/llm/tmp/compute-flags/ready/codex-ni-g16-greedy-ab-aligned-r2-20261031.json`
      (SHA256 `60b2785db876652ebd6d232ec3c3ed5dff4522ca8872b40e157eb400d65dbbe5`), published unarmed at07:57Z; keeper recorded ARMED at07:58:46Z.
      The new entry explicitly reuses immutable-pinned original2048 source/input/image/raw provenance and must
      capture8192/16384/24576; all four ledger rows are required. Real8192 compute cutoff returned75/partial
      with drained descendants; current validator/grant_ok actual-PID checks passed. Source/build/raw
      custody has KEEP through greedy and coordinated champion integration. G16/keep/promotion remain
      open, and G16b was not triggered. [Preparation capsule](../../artifacts/compute/codex-ni-g16-greedy-aligned-r2-20261031/README.md).
    - **Greedy comparison (2026-10-31):** Native result reports valid execution and FAIL on the predeclared exact-byte branch: first IDs match at 2K, 8K, 16K and 24K; full UTF8 bytes differ at all four. Dispatch/residency valid for all four; 2K is the pinned original, three longer lengths are new. This alone does not resolve the separate NMSE alternative of the G16 OR gate, nor establish causality, keep or promotion. [Terminal evidence](../../artifacts/compute/codex3-results-filing-1830-20261031/capsule.json). [belief: cc]
- [x] **G16a — make G16 fire the chunked kernel on MI210, or it is vacuous.** The H=32/d=128 long-prompt eval
      cases in `719a8529d` use `n_seqs=1`. That gives 256 blocks, below 3×nsm = 312, so on MI210 they assert the
      RECURRENT kernel against CPU. Fix it either way:
      - add `n_seqs=2` variants of the 2048/4096/8192 cases (512 blocks, which fire unmodified); or
      - run a test build with `-DGGML_CUDA_DELTANET_MIN_BLOCKS_PER_SM=2`. It is a compile-time macro
        (`gated_delta_net.cu:608-610`), so setting it as an env var does nothing.
      Require `GGML_CUDA_DELTANET_CHUNKED_DEBUG=1` stderr showing `[gdn] chunked dispatch` for every long case in the
      run log. A G16 pass without that trace clears nothing. Source: intake-1434#record.
    - **Build prerequisite complete (2026-10-31):** the exact two-file C3 candidate built the full
      `test-backend-ops` target for CPU (152.53 s; 1.32 GB peak whole-tree RSS) and explicit gfx90a HIP
      (743.895 s; 1.30 GB peak). It includes the two-sequence (`n_seqs=2`) T=2048/4096/8192 variants;
      the original eight shapes and unrelaxed `1e-7` NMSE threshold are unchanged. This is build-only:
      native dispatch trace/numerical qualification, greedy comparison, keep and production promotion
      remain open. Evidence: `artifacts/engineering/g16a-build-prep-20261031/`.
    - **Native G16a complete (2026-10-31):** MAIN accepted all eight exact H=32/d=128 F32
      eval cases on MI210/gfx90a at the unchanged `1e-7` source gate (each raw operation `OK`,
      `1/1 tests passed`, rc0). T=2048/4096/8192 at `n_seqs=2` each emitted its own
      `[gdn] chunked dispatch`, 512 blocks against floor 312, `keep_rs=0 K=1`; five one-sequence
      controls also passed. All eight loaded the exact candidate HIP image and retained live
      PID/birth-bound per-process KFD/VRAM samples; none skipped or remained partial. Evidence:
      `artifacts/engineering/g16a-native-20261031/`. [belief: cc]
      This closes G16a only. G16 greedy A/B, keep-rs and champion integration/promotion remain open;
      no dispatch-proven numerical failure occurred, so G16b was not triggered. Raw logs do not
      expose NMSE magnitudes; no numerical value, deterministic replay or measurement warrant is invented.
- [ ] **G16b — diagnostic arm if a dispatch-proven G16 fails 1e-7.** Rerun the failing shapes on a test build that
      forces the chunked kernel's scalar f32 path: `FGDN_TILE_MMA` undefined, with the host arch gate still admitting
      it (`gated_delta_net.cu:252-267, 305-321, 406-416`). This separates f16-operand GEMM error from pure
      chunk-reassociation error, and it must happen BEFORE anyone relaxes the gate or declines the kernel.
      No reference implementation sets a precedent for our gate: FLA validates at RMS-relative 0.005 (≈ NMSE 2.5e-5,
      about 250× looser). The recorded 2.97e-7/3.70e-7 T=2048 miss was PR #26001 plus a patch, not #24561, whose
      longest eval was 520 tokens. Source: intake-1434#record.
- **[declined: ws58 2026-11-03 content-review: tracked-not-scheduled training research (continued pretraining of a GDN-2 layer) with no inference-stack decision; GDN-2 has no non-Triton path, so no port follows]** **B9 (B) — GDN-2 zero-loss retrofit initialization, and the β ∈ [0,2] control the paper
      omitted.** Filed as **tracked-not-scheduled**, in two halves with different upstreams.
      **(a) Retrofit initialization.** Broadcast each head's scalar β and α across channels to recover
      plain GDN exactly inside an `fla.layers.GatedDeltaNet2` layer and confirm logits match at step 0
      to fp tolerance — one layer, PyTorch, CPU-feasible. **Blocked on the ROCm 6.2 / gfx90a
      torch+triton feasibility probe (`G6` in
      [rocm-verify-profile-backend.md](rocm-kernel-authoring.md#track-rocm-verify-profile-backend))**: there is no environment on
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
      [multiscreen-attention-evaluation.md](long-context-program.md#track-multiscreen-attention-evaluation), which could shrink
      that +12.5 % and is zero-compute.

##### Verification for the above

`bash scripts/validate/validate_intake.sh` → 0 and `python3 scripts/handoffs/index_state.py --check`
→ 0 before committing. For **G16**, a run that reports only `test-backend-ops` at the shipped shapes is
**not** this row: the new 2048/4096/8192 cases at H=32 d=128 are the row, and a pass at the shipped
shapes alone is a vacuous verification of the exact kind the coverage gap above describes.

#### Research Intake Update — 2026-09-07

##### SWA-beats-linear (arXiv 2608.28444) is NOT evidence against our ρ = 4 topology — non-applicability record

arXiv 2608.28444 is NOT evidence against our ρ = 4 topology: it **excludes hybrids with full-attention
layers by construction** (Section 4), lists them as future work (Section 5), concedes from-scratch
training is out of scope (abstract), and its only Gated DeltaNet arms sit at **MMLU chance** after a
0.1B-token Alpaca conversion (Table 5). It points the **same** way as arXiv 2606.15378 (full attention
carries long-range retrieval). Its title invites exactly the citation this refutes — the value of the
record is preventing work. `intake-1340#04`.

This record also belongs in `wiki/ssm-hybrid.md` beside the 2026-08-23 wave-2 ρ = 4 addendum; that
edit rides the wiki compilation sweep, not this session.

**Declines recorded with the same one reason** (our instrument cannot apply a prefill mask, so the
correct output is this non-applicability record, not an investigation):

- **1340#6 — reproduce SWA(64,4)**: DECLINED. Frozen v9 evicts only inside the context-shift branch;
  it cannot mask at prefill, so a reproduction would measure a different method.
- **1340#7 — implement a true runtime `n_swa` override**: DECLINED. No runtime override exists
  (`common/arg.cpp:1491/:1501/:1512`); building one is kernel work on a FROZEN production tree and buys
  only the ability to reproduce a result that does not bear on ρ = 4.
- **1340#8 — treat 2608.28444 as evidence for/against the GDN hybrid topology**: DECLINED. It excludes
  full-attention hybrids by construction; see the record above.

- [ ] **GDN-ORACLE-1 — Land a CPU-only fp64 conformance oracle for the chunked GDN graph.** Vendor `linquant/reference.py` and `invariances.py` (MIT, attributed) into a test fixture, map our graph to `chunk_core(family=delta, rho=1, tau=1, eta=0, read_post=False, qz=none)`, and assert 1e-9 against it plus chunked-graph equivalence to the per-token path. Add a dump case beside `tests/test-backend-ops.cpp`; no weights, no GPU. Done when the test runs in the normal CPU suite and fails on a seeded mutation of the WY prep or the state pass. [no-belief: test infrastructure]
- [ ] **GDN-SHARE-1 — Measure the GDN recurrent core's share of prefill and decode wall time at our serving shape.** Profile one DS41/Q38FN-shaped Q8_0 run of the chunked GDN graph on CPU and one on MI210, separating the recurrence core from projections, attention and MLP. Pre-registered: if the core is under 5% of either wall, close the LinQuant implementation line as no-transfer and keep only the invariance taxonomy. Estimate 2 CPU-hours plus 1 GPU-hour. [belief: pending]

## Track: engram-conditional-memory
<!-- gate: none -->

> Folded from `handoffs/active/engram-conditional-memory.md` @ `3f2a6604f6e1` on 2026-11-03 (BRF-T7-F17, route 1b, operator D1/D5; retired row INF-13 → INF-33). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Engram — Conditional Memory via Scalable Lookup

**Status**: active (Track A closed negative; Track B proxy open)
**Created**: 2026-05-24 (via research intake)
**Updated**: 2026-06-12 (stale Track A queue reconciled with decision log)
**Categories**: memory_augmented, hardware_optimization, moe_optimization
**Owner**: TBD

#### Current State & Next Action (TL;DR)

**Where we are**: Track A LongCat-Flash-Lite CPU probe closed negative on 2026-05-25. The model ran at production-relevant CPU rates, but gemma4-MTP dominated it on both decode speed and sentinel quality for `worker_general`; it is not a production replacement candidate on this stack. Track A reporting is complete: `research/deep-dives/longcat-flash-lite-engram-cpu-poc.md` exists and `intake-504` records the contradictory measurement. Track B Phase 0a CPU prep is complete and remains a separate research bet.
**Next action**: Track B Phase 0b GPU proxy only when ready to spend ~$50-150 on cloud/GPU time.
**Owner**: TBD — needs assignment.

If you are an agent landing on this doc and being asked to "make progress on Engram", do not restart Track A. The only open execution path is Track B Phase 0b if a clean GPU budget/window has been explicitly authorized.

#### Objective

Two tracks, **sequenced** (not parallelized at the start):

- **Track A — LongCat-Flash-Lite CPU probe** (low-effort, week-scale, RUN FIRST): get a production-deployed Engram-family architecture running on our EPYC stack as the first measurable Engram-style POC anywhere on CPU. Working GGUFs and a fork already exist; this is mostly download + build + measure.
- **Track B — Frozen-backbone Engram retrofit** (high-effort, month-scale research bet, GATED ON TRACK A + PROXY DERISK): graft a paper-faithful Engram layer onto a frozen Qwen3.6 backbone, train only the n-gram table + projections + conv + gate. The paper provides no direct evidence this works, so derisk on a 1.5B proxy before committing to Qwen3.6 surgery.

Hardware fit is the through-line motivation: EPYC 9655 with 1.1 TB DDR5 and ~460 GB/s aggregate BW makes us, in principle, the **best-provisioned single node on Earth** for an inference architecture where 25–46% of "sparse" parameters live in a deterministic-lookup table that wants ~10 KB/token of memory bandwidth.

#### Sequencing Decision

```
                ┌──────────────────────────────┐
                │  Track A — Phases 0-5        │
                │  (LongCat CPU probe)         │
                │  ~1-2 weeks, no GPU needed   │
                └─────────────┬────────────────┘
                              │
                ┌─────────────▼────────────────┐
                │  Gate A: ≥35 t/s decode +    │
                │  quality ≥ Qwen3-30B-A3B?    │
                └─────────────┬────────────────┘
                              │
              ┌───────────────┴───────────────┐
            FAIL                             PASS
              │                                │
   ┌──────────▼──────────┐    ┌────────────────▼──────────────────┐
   │ Archive Track A,    │    │ START Track B Phase 0 (proxy)     │
   │ document negative.  │    │ IN PARALLEL with Track A Phase 6  │
   │ Reconsider Track B  │    │ deeper eval. Both run for ~1 week.│
   │ ONLY if user wants  │    └────────────────┬──────────────────┘
   │ pure-research bet.  │                     │
   └─────────────────────┘     ┌───────────────▼─────────────────┐
                               │  Gate B0: frozen-Engram         │
                               │  recovers ≥30% of co-trained    │
                               │  Engram gain on 1.5B proxy?     │
                               └───────────────┬─────────────────┘
                                               │
                                ┌──────────────┴───────────────┐
                              FAIL                            PASS
                                │                              │
                     ┌──────────▼──────────┐         ┌─────────▼──────────┐
                     │ Archive Track B,    │         │ Track B Phases 1-4 │
                     │ document negative.  │         │ (Qwen3.6 retrofit) │
                     │ Track A may still   │         │ ~1 month, GPU req. │
                     │ produce a worker    │         └────────────────────┘
                     │ candidate.          │
                     └─────────────────────┘
```

**Why this sequencing:**

1. **Track A is cheap to falsify and binary-informative.** If a production-deployed Engram-family checkpoint can't beat our deployed worker on CPU, that's a strong signal the entire family doesn't pay for itself in our regime — and it's a much stronger signal against Track B than anything the paper provides, because Track A measures *deployed reality* on *our exact hardware*.
2. **Track A success ≠ Track B validation** (the architectures differ — see comparison table below). But Track A success means the *primitive* of n-gram-lookup-augmented MoE inference is viable on CPU, which is a necessary precondition for Track B being worthwhile to pursue.
3. **Track B Phase 0 proxy derisk is independent of Track A's deeper evaluation** — once Gate A passes, the two can run truly concurrently: proxy training on the **local MI210 (gfx90a, 64 GB HBM2e, installed 2026-07-02)** instead of a rented/cloud H100 (the Phase-0 proxy trains only the n-gram table + projection, a small forward/backward that fits comfortably; gfx90a training-viability is [unverified] and must pass a smoke first — but no cloud spend is needed), and a different (or same) contributor on EPYC for the deeper LongCat quality run. They share no compute and no codebase. [was: "rented H100" — stale after the MI210 install; cross-ref `gpu-acceleration-path.md`.]
4. **Track B Phases 1-4 (Qwen3.6 surgery) require both gates passing.** This is the only multi-week-of-engineering commitment in either track; gate it hard.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-599 | Conditional Memory via Scalable Lookup (DeepSeek+PKU, arxiv:2601.07372) | high | new_opportunity |
| intake-600 | Pooling Engram Conditional Memory using CXL (workshop, arxiv:2603.10087) | low | worth_investigating |
| intake-502/504 | LongCat-Flash family (Meituan) — Lite variant ships Engram-style n-gram embeddings in production | medium | active POC candidate |

---

#### What the Deep-Dive Established

##### Architecture (paper-faithful version)

- **Hash:** multiplicative-XOR per-head, `hash = (Σ XOR_k t_k·m_k) mod P_head`. 64-bit ints. **K=8 distinct hash heads** per n-gram order. Per-head moduli are distinct primes just above `engram_vocab_size`. Collisions within a head are not resolved — the K-head ensemble + gating is the entire mitigation.
- **Keys:** 2-gram + 3-gram suffixes of *canonicalized* token IDs. DeepSeek's canonicalization map P collapses ~23% of vocab (NOT publicly released; would need to be rebuilt for any non-DeepSeek tokenizer).
- **Embedding dim:** `d_mem = 1280`. Concatenated across (n, k) heads → 2·8·1280 = 20,480-wide vector, projected by W_K / W_V to d_model.
- **Injection:** 27B is 30 layers; reference config uses layers [2, 15] but ablation reports [2, 6] is *better*. So early-layer insertion is critical — the paper hypothesizes Engram "relieves the backbone's early layers from static reconstruction."
- **Path:** scalar sigmoid gate (`α_t = σ(RMSNorm(h)·RMSNorm(W_K·e)/√d)` with a sqrt-signed-magnitude squash before sigmoid) → gated value → depthwise causal Conv1D (kernel=4, dilation=3, SiLU) → residual add into the stream *before* Attention and MoE at the inserted layer.
- **Zero-init:** Conv weights are zero-initialized so the model = un-augmented backbone at step 0. **NOT in the released demo code — must be added (2 lines).**

##### Architecture (LongCat-Flash-Lite production deviation — IMPORTANT)

LongCat is *not* a paper-faithful reproduction. The differences:

| Aspect | Paper Engram | LongCat-Flash-Lite |
|---|---|---|
| Injection points | Per-layer at [2, 15] or [2, 6] | **Input embedding only** (1-shot) |
| Gate | Scalar sigmoid, content-aware | **None** — pure additive |
| Conv path | Depthwise causal Conv1D, kernel=4 dilation=3 | **None** |
| Normalization | RMSNorm × 2 inside gate | Divide by 13 (= 1 + 4·3) |
| n-gram orders | 2, 3 | **2, 3, 4** |
| Hash heads | 8 per order | **4 per order** (`emb_split_num=4`) |
| Hash function | Multiplicative-XOR | **Polynomial rolling hash** |
| Tokenizer | DeepSeek-V3 (128k vocab, canonicalized) | Custom LongCat (131k vocab, no canonicalization) |
| Slot count | ~280k/head (27B) | `78 × 131072 ≈ 10.2M`/head |
| Active params | 27B/40B research | 2.9–4.5B active / 68.5B total (~31.4B in n-gram tables) |

**Net:** LongCat is a simpler, cheaper, input-only "Engram-Lite." It validates that *some* version of n-gram-keyed memory works in production at MoE-scale, but it does NOT validate the paper's gating-and-conv mid-layer-injection path. Track A is a POC of the *family*, not a reproduction of the *paper*.

##### Bandwidth + RAM math (from CXL follow-up paper)

- ~10 KB/token total at FP8 for paper-config (2 layers × 5 KB) at 70k tok/s → 0.7 GB/s lookup BW. **<0.2% of our DDR5 aggregate.**
- 100B-param embedding table → ~50 GB at FP8, ~100 GB at FP16. We have 1.1 TB headroom.
- LongCat-Flash-Lite at Q4_K_M: 37.4 GB on disk, ~51 GB resident with KV cache and activations. Trivial.

##### Repo state (deepseek-ai/Engram)

- **422 lines** of Python in `engram_demo_v1.py`, plus paper PDF, figures, drawio. Nothing else.
- License: Apache-2.0 (safe to vendor).
- Maintainer dropped after day 3 (no engagement since 2026-01-14). 20 open issues, 0 closed. Open issue #16 "training code" — unanswered. Open issue #9 asking about LR scaling — unanswered.
- The Engram **module itself** is real and reusable (~250 LoC of substantive logic).
- **Missing:** training loop, dataloader, optimizer config, backbone-freeze hooks, zero-init, KV-cache support, PCIe prefetch / CUDA kernels, eval scaffolding. All of these the paper *describes* but did not release.
- Bug noted in open PR #15: `torch.from_numpy(...)` forces CPU-only execution; hash needs torch port for GPU.

##### LongCat-Flash-Lite tooling state

- **Weights:** `meituan-longcat/LongCat-Flash-Lite` (HF, MIT license, BF16, ~138 GB).
- **GGUF:** `InquiringMinds-AI/LongCat-Flash-Lite-GGUF` (Q3_K_L through BF16; Q4_K_M = 37.4 GB recommended). Quality note from publisher: hallucination rate climbs sharply ≤Q3, n-gram tables are quant-sensitive.
- **llama.cpp fork:** `InquiringMinds-AI/llama.cpp` branch `longcat-flash-ngram`, head `56abe857` (2026-04-27). ~903 LoC delta across 15 files. **Cannot be upstreamed** — publisher disclosed it was Claude-Code-generated, which violates llama.cpp's AI-policy. Fine for our local use.
- **Upstream llama.cpp:** PRs #19167 + #19182 stalled draft since Jan, blocked on the base architecture not being landed first.
- **ik_llama.cpp:** zero LongCat code. Skip — use the InquiringMinds mainline fork.
- **vLLM:** issue #33528 open, no resolution. Memory overhead loading the 31.4B n-gram embedding remains a complaint.
- **CPU performance reports anywhere:** **none.** We would be the first.

---

#### Track A — LongCat-Flash-Lite CPU Probe

##### Hypothesis

LongCat-Flash-Lite Q4_K_M runs on EPYC 9655 NPS4 at ≥35 tok/s decode with quality ≥ Qwen3-30B-A3B on MMLU. If yes → file follow-on to evaluate against gemma4-26B-A4B MTP in the worker_general role. If no → publish the negative result, free the slot.

##### Phase plan

**Phase 0 — Confirm freshness** (≤30 min, no compute)
- Check InquiringMinds GGUF repo head + llama.cpp fork branch still at `56abe857`.
- Confirm upstream PRs #19167 / #19182 still draft (no surprise landing that obsoletes the fork path).

**Phase 1 — Fetch** (bandwidth-bound, ~30 min)
- `huggingface-cli download InquiringMinds-AI/LongCat-Flash-Lite-GGUF LongCat-Flash-Lite-Q4_K_M.gguf` → `/mnt/raid0/llm/models/longcat-flash-lite-q4km/`.
- Verify sha256 against the HF README.
- Optionally fetch Q5_K_M (44.7 GB) as a quality reference; defer Q8_0 unless Q4_K_M shows quality concerns.

**Phase 2 — Build the fork** (~30 min)
- Clone `https://github.com/InquiringMinds-AI/llama.cpp` into `/mnt/raid0/llm/llama.cpp-experimental` per `feedback_experimental_repo.md`. Add as remote on the existing experimental tree if cleaner.
- Branch `longcat-flash-ngram`. Verify our existing experimental patches don't conflict (check the rebase log).
- Build with AOCC + AVX-512 + no CUDA + `KMP_BLOCKTIME=10` env. NPS4-native.
- Smoke-build `llama-cli`, `llama-bench`, `llama-server`.

**Phase 3 — Smoke test** (user-launched per `feedback_no_concurrent_inference.md`)
- Prepare (do not run unprompted):
  ```
  llama-cli -m longcat-flash-lite-q4km.gguf -p "What is 2+2?" -n 32 \
    -t 96 --numa distribute -fa 1 --no-display-prompt
  ```
- Sanity-check on user's go: no crash, non-garbage output, BPE pre-tokenizer warning absent (verify hash registered per InquiringMinds commit `e0ae3c14`).

**Phase 4 — Speed verify** (user-launched, `llama-bench` only — per `feedback_speed_verify_via_llama_bench.md`)
- Prepare commands for decode-only (`-n 128`) at 1K/4K/16K context, with full OMP env stack per `feedback_omp_env_stack_required.md`:
  ```
  OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  KMP_BLOCKTIME=10 numactl --interleave=all \
  llama-bench -m … -t 96 -fa 1 -n 128 -p 1024,4096,16384
  ```
- Record decode t/s. Falsification thresholds:
  - **<15 t/s** → n-gram path is broken or serialized; investigate or abandon.
  - **15–35 t/s** → working but not competitive with deployed Qwen3-30B-A3B (49 t/s); document and stop.
  - **≥35 t/s** → proceed to quality gate.
  - **≥60 t/s** → escalate priority, this is genuinely interesting.

**Phase 5 — Quality gate** (user-launched, manual or scripted via existing eval infra)
- 20-question MMLU subset + 5 agentic prompts (matched against an internal task we already use Qwen3-30B-A3B for).
- Compare blind. If LongCat ≥ Qwen3-30B-A3B on average → proceed.
- Watch for the published agentic weak spot (Meituan reports VitaBench = 7.0, very low).

**Phase 6 — Decision**
- Pass-all → file new handoff `longcat-engram-worker-evaluation.md` scoping a vs gemma4-MTP comparison in worker_general.
- Any-fail → write findings to `research/deep-dives/longcat-flash-lite-engram-cpu-poc.md`, update intake-504 contradicting_evidence with the verified measurement, archive this track of the handoff.

##### Open risks for Track A

- **Quant sensitivity of n-gram tables.** Embedding tables typically prefer Q6_K+. Q4_K_M may degrade the lookup quality more than the backbone. If quality fails, retry at Q5_K_M before declaring negative.
- **n-gram cache thread safety.** If the InquiringMinds fork doesn't per-thread-isolate or lock the rolling-hash context, expect output corruption at high thread counts. Spot-check by running -t 12 vs -t 96 with same seed.
- **Zero-experts kernel.** Top-12 routing into 256 routed + 128 zero-experts should emit 0 FLOPs for zero-expert slots. If the kernel naively runs them, expect ~50% wasted decode.
- **Architectural variance.** LongCat is not paper-faithful (see comparison table). A positive result on Track A does **not** validate the paper's Engram for Track B purposes — it only validates the family.

---

#### Track B — Frozen-Backbone Engram Retrofit (Research Bet)

##### Hypothesis

A paper-faithful Engram layer (multiplicative-XOR hash + 8 heads × bigram/trigram + gated value + zero-init depthwise conv + residual add) inserted at the early layers of a *frozen* pretrained backbone can recover a meaningful fraction (≥30% derisk gate; ≥50% target) of the joint-training gain reported in the paper — measured on a small-scale proxy first, then promoted to Qwen3.6 or gemma4 if proxy passes.

##### Why the paper provides only weak support

- **No frozen-backbone ablation in the paper.** The closest is §6.3 post-hoc Engram suppression which shows the *co-trained* backbone has learned to delegate to Engram. The complement — backbone never given the chance to delegate — is unstudied.
- **§6.2 finds Engram works best at early layers** (layer 2 best single-insertion; [2, 6] beats [2, 15]) precisely because it "relieves the backbone's early layers from static reconstruction." Once a pretrained backbone has already done that reconstruction with its dense FFNs, there is structurally less headroom.
- **Zero-init conv is gradient-compatible** with frozen backbone: at step 0 Y = 0 → no perturbation. Gradients flow into Engram parameters cleanly. This is the architectural reason to hope.
- Plausibly some fraction of paper's gain is "more compute at early layers" (which a frozen backbone can't get), and some fraction is "the table contents" (which a frozen backbone *can* learn). Ratio is unknown.

##### Phase plan

**Phase 0 — Proxy derisk** (≤1 week, single H100/A100)
- Backbone: a 1.5B-parameter open model with clean public tokenizer (TinyLlama / SmolLM-1.7B). Freeze entirely.
- Engram: copy the demo's `Engram` module verbatim, add the missing zero-init for `short_conv.conv.weight` and `value_proj.weight`. Replace numpy hash with torch hash (PR #15 reference) so it runs on GPU.
- Insertion: a single Engram layer at depth ~2 (early). Optionally test [2, layer_floor(N/2)] as a second config.
- Data: 5–20 B tokens from FineWeb-Edu or RedPajama-v2. Match the paper's batch/seq if possible.
- Two-group AdamW: backbone (frozen — gradients masked or `requires_grad=False`), Engram (lr=5×backbone-equivalent, wd=0).
- **Reference comparator**: also train a tiny co-trained Engram model on the same data budget (same arch, but backbone unfrozen) so we can compute the frozen-fraction-of-gain ratio.
- **Gate**: frozen-backbone Engram recovers ≥30% of co-trained-backbone gain on held-out PPL and a 2-task eval (MMLU subset + LAMBADA). Below 30% → abandon Track B, document negative.
- Cost: ~24–48 H100-hours total, ~$50–150 cloud.

**Phase 1 — Tokenizer canonicalization** (if Phase 0 passes; ~2 days)
- The paper's vocab-canonicalization map P (~23% reduction) is NOT released. Rebuild for the chosen target tokenizer using lightweight rules: Unicode NFKC + case fold + whitespace normalize + punctuation collapse. Validate that the collapsed-vocab Engram doesn't degrade vs raw-vocab on Phase 0 setup before scaling.
- The repo's `CompressedTokenizer` (built on DeepSeek-V3's tokenizer) is a reusable template — swap the underlying `AutoTokenizer.from_pretrained(...)` and re-run the normalizer chain.

**Phase 2 — Layer-injection selection** (~2 days)
- For Qwen3.6 (64 layers) and gemma4-26B-A4B (target backbones), run a CKA-style alignment probe: which layers' representations most resemble the "shallow Engram-input" layers of the proxy that worked best? Inject there. Hypothesis: layers ~[2, 12] or [2, 32] for Qwen3.6; we'll let CKA decide.

**Phase 3 — Full-scale training** (if Phase 0–2 derisk; ~1–2 weeks single H100 OR ~3–5 days on 2× H100 FSDP)
- Backbone: Qwen3.6 (we have it deployed, tokenizer known, eval baselines established). Alternative: gemma4-26B-A4B (MTP path is well-understood).
- Engram-table sizing: target ~5–10% of backbone params (proxy result will refine this — paper's 25% is for co-training; frozen retrofit likely tolerates less).
- Training budget: ~20–50 B tokens. The Engram table is BW-cheap to train (sparse updates), the cost is dominated by backbone forward passes.

**Phase 4 — Inference deployment** (only if Phase 3 passes)
- Bake the Engram-extended Qwen3.6 to GGUF. This requires the Track A llama.cpp fork *plus* the paper-faithful gating-and-conv path (LongCat fork doesn't have these; we'd add them on top).
- Run on EPYC under our standard NPS4 + 96t + Q4_K_M operating point. The lookup BW is negligible (~0.7 GB/s) so decode speed should be ≈ backbone decode minus a small per-token gate+conv overhead.

##### Required net-new engineering work (Phase 0)

| Component | Source |
|---|---|
| `Engram` module (hash + multi-head embed + gate + value_proj + short_conv) | **vendored from deepseek-ai/Engram** (~250 LoC, clean) |
| Zero-init of conv + value_proj weights | **add 2 lines** (not in repo) |
| GPU hash (replace numpy with torch ops) | **port from open PR #15** (~30 LoC) |
| HF forward-hook to splice Engram into chosen backbone layer | **write new** (~50 LoC) |
| Backbone freeze (`requires_grad=False`) | **write new** (~5 LoC) |
| Two-group AdamW (Engram lr=5×, wd=0) | **write new** (~10 LoC) |
| Dataloader + collator | **write new** (~30 LoC, stock HF) |
| Eval scaffolding (lm-eval-harness wiring) | **write new** (~50 LoC) |
| Logging (W&B or local TB) | **write new** (~20 LoC) |

**Total: ~400 LoC of new glue around ~280 LoC of vendored code. A one-week spike to a first proxy curve, single contributor, single GPU.**

##### Falsification criteria (kill switches)

- Phase 0 proxy frozen-Engram recovers <30% of co-trained-Engram gain → **abandon Track B**, write up negative result.
- Gate α_t collapses to 0 (Engram unused) across most tokens during proxy training → indicates LR too low or gate normalization wrong; tune once, then if still failing → **abandon**.
- Phase 0 passes but Phase 1 tokenizer-canonicalization-rebuilt Engram regresses below raw-vocab baseline → **stay with raw vocab**, accept the larger table size.
- Phase 3 full-scale Engram-extended Qwen3.6 fails to beat baseline Qwen3.6 on held-out PPL → **archive, don't deploy.**

##### Open risks for Track B

- **The paper might be wrong about retrofit feasibility being plausible.** §6.3 result is the strongest counter-signal we have. The proxy derisk in Phase 0 is the load-bearing gate; do not commit further compute without it.
- **Privacy/extraction risk** from deterministic n-gram memorization. Not blocking for self-hosted research, but worth flagging if outputs ever surface externally.
- **Training-data quality.** The paper's 262 B tokens are presumed DCLM-grade. Lower-quality data could starve the table.
- **GPU availability.** Phase 0 needs an actual GPU (rent or borrow). EPYC alone is not viable for the training step.

---

#### Pointers

- Paper: https://arxiv.org/abs/2601.07372 / HTML: https://arxiv.org/html/2601.07372v1
- ar5iv mirror: https://ar5iv.labs.arxiv.org/abs/2601.07372
- CXL follow-up: https://arxiv.org/abs/2603.10087 (where the 5 KB/token/layer + 0.7 GB/s figure comes from)
- Demo repo: https://github.com/deepseek-ai/Engram (Apache-2.0, 422 LoC, abandoned by maintainers)
- LongCat-Flash-Lite weights: https://huggingface.co/meituan-longcat/LongCat-Flash-Lite
- LongCat GGUF: https://huggingface.co/InquiringMinds-AI/LongCat-Flash-Lite-GGUF
- LongCat llama.cpp fork: https://github.com/InquiringMinds-AI/llama.cpp tree `longcat-flash-ngram` head `56abe857`
- Upstream PRs (stalled): https://github.com/ggml-org/llama.cpp/pull/19167 and https://github.com/ggml-org/llama.cpp/pull/19182
- vLLM issue: https://github.com/vllm-project/vllm/issues/33528
- Third-party detailed writeup: https://arxiviq.substack.com/p/conditional-memory-via-scalable-lookup

#### Decision Log

Append a line for each gate outcome. Format: `YYYY-MM-DD | <gate> | <result> | <evidence link> | <decision>`

- `2026-05-24 | Phase 0 freshness (Track A) | PASS | gh API: fork head 56abe85 unchanged, PRs #19167/#19182 still draft | proceed to Phase 2 build`
- `2026-05-24 | Phase 2 build (Track A) | PASS | cmake exit 0 in /mnt/raid0/llm/llama.cpp-longcat-probe (worktree on probe/longcat-build tracking inq/longcat-flash-ngram) | ready for Phase 3 GGUF probe, pending user approval per feedback_no_concurrent_inference.md`
- `2026-05-24 | Phase 0a Track B (identity-at-step-zero invariant) | PASS | 36/36 unit tests pass in 0.36s on CPU; engram-spike commit e3b88f0c in epyc-inference-research; max abs Engram output after identity init = 0 (atol 1e-6) on non-zero hidden states | architectural feasibility of frozen-backbone retrofit confirmed at step 0; proceed to GPU rental for Phase 0 proxy training when ready`
- `2026-05-25 | Phase 3 smoke (Track A) | PASS | LongCat-Flash-Lite Q4_K_M loads via InquiringMinds fork, "What is 2+2?" → "4" via /v1/chat/completions on port 8500 | proceed to bench`
- `2026-05-25 | Phase 4 speed (Track A, llama-bench, 96t -fa 1 -ub default, NPS-interleaved) | MIXED | LongCat-Lite Q4_K_M: pp512 322.65 t/s, pp4096 258.33 t/s, tg128 37.08 t/s. Qwen3.6-35B-A3B Q8 (frontdoor): pp512 439.31 t/s, pp4096 435.51 t/s, tg128 25.17 t/s. gemma4-26B-A4B Q4_K_M no-MTP (worker_general core): pp512 957.82 t/s, pp4096 891.39 t/s, tg128 47.71 t/s. gemma4-MTP production-measured 76.5 t/s (memory project_worker_general_swap_2026_05_08). | speed gate: above abandon threshold (15) but below escalate (60); LongCat decodes +47% vs Qwen3.6 frontdoor, −51% vs gemma4-MTP worker. Proceed to quality gate ON THE WORKER COMPARATOR since the speed gap to gemma4-MTP is the binding constraint.`
- `2026-05-25 | Phase 5 quality (Track A, sentinel_questions.yaml = 39 questions, --max-tokens 2048, --temperature 0) | FAIL vs worker, PASS vs frontdoor (likely) | LongCat-Lite Q4_K_M: 21/39 = 53.8%. gemma4-26B-A4B Q4_K_M MTP: 26/39 = 66.7%. **gemma4 dominates LongCat by +12.9pp.** Suite-level: gemma4 wins +4 on math (4/6 vs 0/6), +1 on instruction (4/4 vs 3/4), +1 on gpqa, +1 on thinking. LongCat wins +2 ONLY on hotpotqa. Both tie at agentic 1/3 = 33% (poor — both struggle on tool-use sentinels). LongCat's math 0/6 confirmed structural (not truncation — at 2048 tokens still 0/6); model generates correct-looking step reasoning but final-answer formatting diverges from expected literal. Qwen3.6 eval skipped — speed numbers + role context already determine the decision. Results: /mnt/raid0/llm/epyc-inference-research/research/engram-spike/eval/longcat-results-2048.json + gemma4-results.json. | LongCat is dominated by gemma4-MTP on BOTH axes (slower decode AND lower sentinel quality). It does NOT pass Gate A as a worker_general candidate.`
- `2026-05-25 | Phase 6 decision (Track A) | TRACK A CLOSED — NEGATIVE | LongCat-Flash-Lite Q4_K_M is not a viable replacement for any current production role on our stack: (a) worker_general — dominated by gemma4-MTP on both speed and sentinel quality; (b) frontdoor (Qwen3.6-35B-A3B Q8 at 25 t/s decode) — LongCat is +47% faster on decode but only 53.8% on sentinel including 33% agentic; for an agentic-routed frontdoor the quality regression isn't worth the speed bump. **Family verdict (not paper-faithful verdict): n-gram-augmented MoE inference on CPU IS technically viable at production-relevant rates (37 t/s decode on Q4_K_M 68B/4.5B-active) — we just happen to have better-tuned alternatives already deployed for our specific stack.** Track A archives without taking down our worker. | Write up findings to research/deep-dives/longcat-flash-lite-engram-cpu-poc.md; update intake-504 contradicting_evidence with the verified accuracy + speed numbers; Track B (frozen-backbone retrofit research bet) is unaffected — it's a different architecture (paper-faithful Engram, not LongCat's simplified input-only variant) and a different optimization (training own model, not adopting an existing checkpoint). Track B decision stays "proceed to Phase 0b GPU proxy when ready".`

#### Anti-Rationalization (for this work specifically)

Recurring failure modes worth pre-empting:

| Tempting shortcut | Why it's wrong |
|---|---|
| "Track A passed speed gate, let's skip the quality gate and start using LongCat in production." | Speed without quality is a regression. Engram's headline benefit is *quality*, not speed; treat MMLU/agentic gate as binding. |
| "The paper says retrofitting should work because zero-init is gradient-compatible, let's skip Phase 0 proxy." | The paper says no such thing — it *omits* the retrofit ablation. Zero-init buys gradient-compatibility, not result-compatibility. The proxy derisk is the only direct evidence we'll have. |
| "Frozen-Engram recovered only 20% of co-trained gain on the proxy, but on a bigger backbone it'll be different." | The proxy is a *necessary* condition; small-scale wins generalize unevenly to large scale, small-scale losses almost always do generalize. <30% on the proxy = abandon. |
| "We can use 4-bit Engram tables on Phase 0 to save time." | Quantization sensitivity of the n-gram table is *unstudied* by both the paper and LongCat. Phase 0 must train + eval at full precision (bf16) to keep the measurement clean. |
| "Let's just try injecting Engram into Qwen3.6 directly — skip the proxy, the LoC is small." | The LoC is small but the *compute cost* of a 64-layer 36B-active forward+backward at scale is 20-40× the proxy. Discovering the experiment is broken at scale wastes those GPU-weeks. |
| "LongCat fork is AI-generated; we shouldn't touch it." | The policy concern is about *upstreaming*, not local research use. The fork is fine for our experiments; we just can't submit our patches back to ggml-org. |
| "We should benchmark LongCat on `run_benchmark.py` since it's already wired up." | See `feedback_speed_verify_via_llama_bench.md` — speed verification is `llama-bench` only, run manually by user. Do not auto-launch. |
| "Track B Phase 0 fits on the EPYC box, we don't need GPUs." | EPYC is BW-bound on FFN backward; you cannot train at any reasonable token-rate on CPU. Rent the GPU. |

#### Operating Constraints That Apply

- **`feedback_no_concurrent_inference.md`** — every speed-verify run on EPYC needs explicit per-run user approval; do not launch llama-cli / llama-bench / llama-server without it.
- **`feedback_speed_verify_via_llama_bench.md`** — Track A Phase 4 uses `llama-bench` only, never `run_benchmark.py`.
- **`feedback_omp_env_stack_required.md`** — OMP env stack + `numactl --interleave=all` + `KMP_BLOCKTIME=10` mandatory for all benches.
- **`feedback_canonical_baseline_protocol.md`** — first speed gate uses canonical `taskset -c 0-95 -t 96 -fa 1` baseline before NPS4 variants.
- **`feedback_experimental_repo.md`** — the InquiringMinds llama.cpp fork must live in `/mnt/raid0/llm/llama.cpp-experimental`, not the production tree.
- **`feedback_gitignore_binaries.md`** — GGUF files and rented-GPU artifacts never get committed; add to `.gitignore` proactively.
- **`feedback_host_throttle_check.md`** + **`feedback_drop_caches_numa_eviction.md`** — verify host throttle state before Track A Phase 4, and re-warm with `numactl --interleave` after any drop_caches.
- **`feedback_sanity_check_before_compute.md`** — Track B Phase 0 proxy must produce DIFFERENT outputs vs the same-arch frozen-Engram-disabled baseline before committing to a full training run. Avoid the TIDE-style 20h wasted compute.

#### Initial Action Queue (for the next agent landing here)

Copy this into a TaskCreate list when starting work:

1. [x] **Track A Phase 0** — `gh pr view 19167/19182 -R ggml-org/llama.cpp` + `gh api repos/InquiringMinds-AI/llama.cpp/branches/longcat-flash-ngram` confirm fork head `56abe85` and upstream PRs unchanged as of 2026-05-24. ✅
2. [x] **Track A Phase 1** — Q4_K_M GGUF present at `/mnt/raid0/llm/models/longcat-flash-lite-q4km/LongCat-Flash-Lite-Q4_K_M.gguf`. ✅
3. [x] **Track A Phase 2** — InquiringMinds fork built in worktree `/mnt/raid0/llm/llama.cpp-longcat-probe` (branch `probe/longcat-build` tracking `inq/longcat-flash-ngram` at `56abe857d`). `llama-cli`, `llama-server`, full toolchain present. ✅
4. [x] **Track A Phase 3** — smoke test passed on 2026-05-25: LongCat Q4_K_M loaded and answered a basic prompt through `/v1/chat/completions`. ✅
5. [x] **Track A Phase 4** — speed gate complete on 2026-05-25: LongCat Q4_K_M `tg128=37.08 t/s`, above abandon threshold but below gemma4-MTP production decode. ✅
6. [x] **Track A Phase 5** — quality gate failed vs worker on 2026-05-25: LongCat 21/39 = 53.8%, gemma4-MTP 26/39 = 66.7%. ✅
7. [x] **Track A Phase 6** — closed negative on 2026-05-25. Reporting complete: `research/deep-dives/longcat-flash-lite-engram-cpu-poc.md` exists and `intake-504` has the 2026-05-25 contradictory measurement. ✅

Track B Phase 0a (non-inference prep — COMPLETE 2026-05-24):
8. [x] Vendor + refactor the demo Engram module into a clean importable package with config dataclasses (no global state). Drop mocked attn/moe stubs. ✅
9. [x] Add the **two missing zero-init lines** (`value_proj.weight`, `value_proj.bias`, `short_conv.conv.weight`) so identity is preserved at step 0. ✅
10. [x] Unit test the identity-at-step-zero invariant on CPU with non-zero hidden states. ✅ **PASS** at atol=1e-6.
11. [x] HF backbone splicing helper (`EngramLayerWrapper`, `splice_engram_into`) with raises on missing/stale input_ids. Tested with mock HF layer. ✅
12. [x] Two-group AdamW factory + freeze utilities + trainable-param helpers. ✅
13. [x] Pure-Python canonicalizer (NFKC + accent strip + lowercase + whitespace collapse) + offline build script for HF tokenizers. ✅

Track B Phase 0b (the actual GPU proxy run, only when ready to spend ~$50–150 cloud):
14. [ ] Rent H100-80GB or borrow A100s. Set up SmolLM-1.7B (preferred) or TinyLlama as backbone.
15. [ ] Run `scripts/build_canonicalizer.py --tokenizer HuggingFaceTB/SmolLM-1.7B --output canonicalizers/smollm-1.7b.json` to materialize the canonicalization map.
16. [ ] Write the training driver — uses `engram.EngramLayerWrapper`, `engram.freeze`, `engram.make_two_group_adamw` against a frozen SmolLM backbone. Add a co-trained reference run with backbone unfrozen on the same data budget.
17. [ ] Train both configs on 5–20 B tokens FineWeb-Edu. Same Engram-table size for both.
18. [ ] Compute recovery ratio on held-out PPL + MMLU subset + LAMBADA. Apply ≥30% gate. Record in Decision Log.

#### Reporting Instructions

After any phase of either track:
1. Update `progress/2026-05/2026-05-24.md` (or the day's progress file when the work happens).
2. Update this handoff's Decision Log + phase checklist; record results inline.
3. If Track A passes its quality gate (Gate A): file `longcat-engram-worker-evaluation.md` and link from `inference-research-index.md`.
4. If Track B proxy derisk passes (Gate B0): file `engram-retrofit-qwen36-spike.md` and link from this handoff.
5. If either track is killed by a falsification gate: write a deep-dive in `research/deep-dives/` documenting the negative measurement, and update intake-599 / intake-504 contradicting_evidence with the verified result.
6. When the handoff reaches a terminal state (both tracks resolved): move to `handoffs/completed/` and update `inference-research-index.md`'s landscape table.

#### Research Intake Update — 2026-07-02

##### New Related Research
- **[intake-758] "Scaling Embeddings Outperforms Scaling Experts in Language Models"** (arXiv 2601.21204, Meituan LongCat Team)
  - **Relevance:** This is the **missing scaling-law / architecture paper behind LongCat-Flash-Lite** (already tracked here as intake-502/504; Track A CPU probe closed negative). The 31.4B N-gram-embedding figure (46% of 68.5B total) matches our records exactly.
  - **Design principles to fold into any Track B frozen-backbone retrofit:** (1) n-gram embedding scaling is a sparsity axis **orthogonal to MoE** with superior Pareto at high sparsity; (2) **width amplifies / depth diminishes** the embedding-scaling advantage; (3) embedding params should be **≤50% of total**; (4) n-gram sub-table vocab must **deviate from integer multiples** of the base vocab (polynomial-rolling-hash collision rule); (5) device-side **N-gram Cache** kernels + **Eagle3 3-step** speculative decoding realize the sparsity as speedup (draft uses a conventional embedding to bypass n-gram lookup).
  - **Delta from current approach:** the architecture is a *pretraining* choice (not retrofittable onto our GGUF production models) and all numbers are GPU-measured (8×H800) — so this is **adopt_patterns** (scaling-law justification for Track B), not a deployable technique. n-gram-embedding-in-host-DRAM remains a fit for our 1.1 TB DDR5 / 460 GB/s node (Track B thesis).
  - **⚠ Contradiction to carry forward:** the paper's chat **MATH500 = 96.8%** is contradicted by our Q4_K_M CPU eval of LongCat-Flash-Lite (**math 0/6 STRUCTURAL**, intake-502/504). Treat the paper's downstream numbers as observations, and re-check whether the gap is quant penalty vs harness/structural (per feedback_verify_test_method_before_calling_it_a_bug).

#### Research Intake Update — 2026-07-29 (retrieval-policy rider: CORE utility-aware retrieval over a ReasoningBank schema)

_Via `/research-intake` Stage-4 (intake-888 CORE, intake-930 ReasoningBank, intake-936 EvoMemBench). **Scope note:** this rider is about **agent-experience memory retrieval**, not the n-gram lookup tables of Tracks A/B above — it was routed here by the approved Stage-3 plan. The store/schema half is co-owned by [`unified-trace-memory-service.md`](memory-program.md#track-unified-trace-memory-service) § "Research Intake Update — 2026-07-29"; keep the two in sync. All external figures are OBSERVATION-grade under MEASUREMENT.md._

- **[declined: ws58 2026-11-03 content-review: duplicate — memory-program.md already carries the CORE/ReasoningBank retrieval design and k-as-measured-parameter (UTM-M5, intake-888/930)]** **Do NOT port cosine-top-1 retrieval. Layer CORE's (intake-888) utility-aware retrieval over ReasoningBank's schema.** Convergent evidence: the k-ablation loses **half the benefit by k=4** (49.7 / 46.0 / 45.5 / 44.4), and the one independent 35B replication **failed specifically at the RETRIEVER** after an embedder swap — exactly the substitution we would make with local BGE. Treat **k as a measured parameter**, with **k=1** and **episodic-only** control arms.
- **[declined: ws58 2026-11-03 content-review: duplicate — memory-program.md UTM-M6 already files the intake-936 128K context-budget-competition finding and its no-memory control arm]** **Rider on the k-parameter above: k must be BUDGET-CONDITIONAL, not fixed.** intake-936 (independent, DeepSeek-V3.2 backbone) finds six of fifteen memory methods scoring **below** the no-memory baseline at a **128K** budget — mechanism is **context-budget competition**, not store growth (do **not** conflate with intake-899). So the retrieval sweep must vary k **as a fraction of remaining window budget**, and include a no-memory control arm, or it will select a k that is optimal only at short context.
- [x] **ReasoningBank ranking correction:** do not carry “best overall” into retrieval design. intake-936 places it last of 13 on Cross-Episode Knowledge (Easy); its schema/store shape, not ranking, is the transferable signal. Historical intake prose remains historical and is not used as retrieval-policy evidence. ✅ 2026-07-29

#### Progress checklist

- [x] Track A LongCat CPU probe closed NEGATIVE (Phases 0-6 complete, deep-dive + intake-504 recorded) ✅
- [x] Track B Phase 0a non-inference prep (vendored module, zero-init, identity test, splicing helper) ✅
- [ ] Track B Phase 0b: rent/allocate GPU (or MI210 smoke) and run frozen-vs-cotrained proxy on SmolLM-1.7B (~$50-150) (re-scoped 2026-11-03 from downstream Qwen3.6 surgery target superseded by Qwen3.8-27B (Qwen3.6-27B deleted); SmolLM-1.7B proxy not on disk)
- [ ] Track B Phase 0b: build canonicalizer, train both configs on 5-20B tokens, compute >=30% recovery-ratio gate
- [ ] If gate B0 passes: file engram-retrofit-qwen36-spike.md and proceed to Phase 1-4 Qwen3.8-27B surgery (re-scoped 2026-11-03 from Qwen3.6-27B surgery target: deleted; now Qwen3.8-27B)

#### 2026-08-03 — intake Stage-2/2b: the memory cluster, and where its value actually is

_Via `/research-intake` on intake-938 (MemHarness, **dive-overturned**) and its Stage-2b expansion
intake-988/989/990. The headline result is that the arm we were about to port is the weakest effect in
its own paper, and a stronger one sits in a cited work that the citing paper never reports._

**intake-938's reconstruct-before-inject arm is KEPT BUT DEMOTED.** It targets a **+2.2 pp** effect at
**z ≈ 1.94** on one seed with no CI — not significant. Its stronger effects (training +6.68 pp z=5.20,
negative transfer +6.25 pp z=4.39) do survive sampling noise, but neither is protected against **seed**
variance, which is unmeasured. Two further corrections carried on the entry: the `n=140/250` we recorded
is **stated nowhere in the paper** (minimum consistent denominators are 455/304/400/336/360/190, so the
cells cannot be single-pass success rates), and its `EvolveR (reproduced) 70.1` baseline **reproduces
nothing published** — EvolveR never evaluates on ALFWorld or WebShop at all.

##### The three items worth acting on, all zero-training

- **[declined: ws58 2026-11-03 content-review: a finding without a task — its action (gradient-free principle distillation + retrieval) is the memory-program's adopted ReasoningBank baseline (intake-988)]** **EvolveR's gradient-free arm — the highest-value lead in the cluster, and it is on our side of the training line.** Its Table 4 shows principle distillation + retrieval with **RL DISABLED scoring 0.357, beating RL-only at 0.325**, and reaching **93.5% of the full system's 0.382** (Qwen2.5-3B). The citing paper presents EvolveR as the exhibit for "memory + RL is harmful"; EvolveR's own ablation shows its memory machinery *without gradients* outperforming pure RL. Same shape as our adopted ReasoningBank baseline (intake-988)
- **[declined: ws58 2026-11-03 content-review: curiosity — by its own text the figure cannot be a same-budget causal estimate and no stack decision depends on a reflection-redundancy ratio]** **RRR — pure log post-processing, computable RETROACTIVELY over traces we already have.** [too-big: eligible ordered reflection traces must first be captured by owner] Reflexion v2 (`intake-989#03`; `dive-989/paper.txt:L380-L446`) defines RRR as post-hoc SequenceMatcher >=0.85 redundancy among reflections after the first, divided by |M|-1; this can avoid inference only when those reflection traces are available. Keep RRR separate from feedback extraction. The source's 15-trial original versus 10-trial mitigation budgets and its §4.4 7/8 versus §5.3 “none within 10” tension mean the reported change is not a same-budget causal estimate.
- [x] **Programmatic feedback extraction** — parse tool output for concrete failure facts instead of asking the model to self-diagnose. Reflexion v2 (`intake-989#03`, `intake-989#02`; `dive-989/paper.txt:L681-L694,L1494-L1547`) describes a trajectory parser that extracts “Nothing happens” responses and repeated identical actions, after which an LLM still explains each failure and writes a new plan. This is parser-plus-LLM, not zero-inference diagnosis replacement. Keep this task distinct from RRR; the 0/121 to 134/156 object-mention result remains paper-specific to selected frozen environments and is not a transferable local rate. ✅ 2026-11-01 — APP `1b988feb006497425417d641a3ecf7816c2f58ae`; hosted source-bound CI run 41280199807, artifact 13072594430 (214 passed, 1 warning); [belief: cc]

##### One threat assessed and dismissed, with its mechanism, so it is not re-raised

- [x] **"Dark Room" reward collapse does NOT threaten this line** ✅ 2026-08-03 (intake-990). The mechanism requires a **dense policy-dependent potential-difference shaping term with persistent within-group variance**; MemHarness has sparse +10/0 plus a **saturating** 0.1× format bonus plus SFT format cold-start, which is Dark Room's own **Proposition-2 SAFE class**. Decisively: **Dark Room's own non-collapsing baseline IS MemHarness's reward shape**, on the same verl-agent framework. What it *does* destabilise is measurement — 32-episode binomial noise floor ≈ **8.8 points**, its own cross-arm comparisons declared "DESCRIPTIVE", and an unexplained 8B (32.8) below 4B (49.5)
- [x] **Independent corroboration located, and scoped precisely** ✅ 2026-08-03 (intake-989). "Honest Lying" independently shows memory injection **can** drive below a no-memory control, via a controlled memory-**wipe** ablation, with no citation in either direction. That is corroboration for **claim A only** — it is **not** corroboration for the state-mismatch *mechanism*, which is write-side (confabulated self-diagnosis under binary feedback) versus read-side. A **fourth distinct mechanism**, not the same one

**Source qualification 2026-10-06 (`intake-989#record`):** the checked 2026-08-03 outcome above remains historical; it does not establish independent-group/author independence or a bilateral no-citation relationship. The source reports a bounded memory-wipe comparison on selected frozen environments with unequal 15-trial original versus 10-trial mitigation budgets and an unresolved original-log versus §5.3 result tension. It proposes write-path confabulation but does not isolate write-side from read-side failure or establish a distinct fourth causal mechanism. This qualification changes the source rationale, not the completed checkbox or operational outcome.

#### Research Intake Update — 2026-10-20 (COUNT n-gram tables: a corpus-statistics memory family, and a Track B arm held behind Phase 0b)

COUNT (intake-1988#record, arXiv 2610.20456; reference code intake-1989#record) is a parameter-free corpus-statistics memory: a frozen host-RAM table maps each n-gram history (orders 1-6, Dolma2 token ids) to its top-32 next tokens with 8-bit scores, and the input embedding adds the score-weighted sum of the model's own unembedding rows. Its measured gains are for models PRETRAINED with COUNT at <=1B; nothing in the source shows the input embedding helping a model not trained with it, and the abstract headline (57%) is not reconciled with the body (46-89% compute-equivalent). It informs Engram as a non-learned alternative to hashed learned tables; it is not a deploy action.

**Track B COUNT arm (monitor, no checkbox).** Trigger: Track B Phase 0b is authorized to start (the two open Phase 0b boxes in the Progress checklist). Then add one arm to the proxy: take the released standard 1B (`IanMagnusson/count-checkpoints-standard-transformer`, `model-ladders/vanilla-1b/1B/step32537`, Dolma2 tokenizer, budget-matched to the COUNT 1B) plus a COUNT table, add the COUNT input behind a zero-init scalar gate (optionally a zero-init projection), train only the gate, and compare the recovered fraction of the COUNT-pretrained gain against the hashed-Engram frozen retrofit at the same >=30% recovery gate. Pairing must be stated exactly: the paper recipe is the COUNT-trained 1B with the 797.5 GB `general-797gb` table; the 17 GB table with the 1B is an off-recipe, cheaper variant and must be labelled as such; the arm needs the CountLookup code (`olmo_core.data.count_table`) and a patched forward. Caveats: the gate-only retrofit effect is an untested design, not a source result; the released examples are OLMo-core CUDA/H200, and an MI210 port is not assessed.

DF2-19 evidence (2026-10-20, `dflash2-block-drafter-experimental-build.md`): the leave-group-out domain table shows +9.0% oracle-gate headroom but -0.04% with a realistic gate. A per-position confidence gate is the missing piece, and this is the re-trigger condition.

### D-LSA research intake — approved 2026-11-03

- [ ] **LSA-MOE-1 — Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot.**
  - Gate + owner 2026-11-06: owned by main-inf22 as step (d) of the D-LSA plan (`long-context-program.md` → D-LSA research intake). It starts only after the 27B LSA-QUALITY-32K reaches KEEP-QUALITY and one 27B fast path (LSA-H12-E2E or LSA-CPU-SPARSE) keeps. A3B runs entirely on CPU or entirely on GPU, with zero graph splits on GPU. Stop-on-futility: if the 27B gate is not met, do not start. Cost (PLAN): 1-2 engineer-weeks capture/PCA + a timed distillation pilot. [no-belief: gate note]
