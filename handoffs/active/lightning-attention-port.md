# Lightning Attention Port to llama.cpp

**Status**: ACTIVE — **L1 scoping COMPLETE 2026-04-30 (GO verdict)**, L2/L3 cleared to start, L4 inference-gated.
**Created**: 2026-04-29 (after audit of `llama.cpp-experimental` revealed Lightning Attention is essentially a constant-`g` GLA op)
**Updated**: 2026-04-30 (L1.1-L1.6 all done; template strategy corrected — derive from RWKV6 GLA pattern, NOT delta_net_base; decay formula extracted; architecture confirmed as `BailingMoeLinearV2` with `model_type=bailing_moe_linear`, 20 layers M=4 = 4-linear-1-softmax via `layer_group_size=5`)
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
| L1.1 | Re-read `ggml_compute_forward_gla_f32` line-by-line; document exact recurrence equation | **DONE 2026-04-30** |
| L1.2 | Read Ring-Linear paper Section 7 (train/infer alignment + BF16 drift) — identify any precision constraints we'd hit | **DONE 2026-04-30** (resolved via reference-impl reading; paper PDF not text-extractable) |
| L1.3 | Read `llm_build_kimi_linear` end-to-end as template for L3 | **DONE 2026-04-30** (template strategy revised) |
| L1.4 | Read Ant Group's reference impl (github.com/inclusionAI/Ling-V2 — when accessible — or HF model card for Ring-mini) — find the exact decay coefficient form and chunkwise/recurrent split | **DONE 2026-04-30** |
| L1.5 | Confirm ARM + CUDA + CPU backend coverage of `GGML_OP_GATED_LINEAR_ATTN` (we only need CPU for v1, but multi-backend matters for upstream contribution) | **DONE 2026-04-30** |
| L1.6 | **Decision gate**: GO/NO-GO. GO if GLA op semantics match within trivial reshaping. NO-GO triggers re-scope to L5 (dedicated op) as v1 instead. | **GO — 2026-04-30** |

**Decision rule**: NO-GO if GLA's state update doesn't accept a constant `g` (e.g., if shape mismatch forces broadcast that the kernel doesn't support). This is unlikely given the kernel's generic structure but must be verified.

#### L1.1 finding — GLA op recurrence (verified 2026-04-30 against `production-consolidated-v5` HEAD `23bcd6aaf`)

**API** (`ggml/include/ggml.h:2507-2514`, `ggml/src/ggml.c:5773-5811`):
```c
ggml_gated_linear_attn(ctx, k, v, q, g, state, scale)
  // shape requirements (S = head_size, H = n_heads, T = n_tokens, n_seqs from state.ne[1]):
  //   k, v, q, g  : [S, H, T]   (all four identical layout)
  //   state       : [S*S*H*n_seqs] (per-head SxS state matrix, persistent across recurrence)
  //   scale       : float (Q-scaling)
  //   output      : [S*H, T + S*n_seqs] (concat of token output + new state)
```

**Kernel** (`ggml/src/ggml-cpu/ops.cpp:10524-10702`, two arms — vectorized AVX/AVX-512/SVE/NEON + scalar fallback). Per-token, per-head loop:

```
for t in [0, T):
  state_prev = (t == seq_start) ? state_input[h] : state_cur[h]
  for h in [h_start, h_end):       # threads partition heads
    for i in [0, head_size):       # outer i = key-dim
      k_val = k[t,h,i]
      q_val = q[t,h,i] * scale
      g_val = g[t,h,i]
      for j in [0, head_size):     # inner j = value-dim, vectorized
        kv             = v[t,h,j] * k_val
        state_cur[h,i,j] = state_prev[h,i,j] * g_val + kv
        dst[t,h,j]      += state_cur[h,i,j] * q_val
```

Equivalent recurrence (per head, dropping h subscript):
```
S_t[i,j] = g_t[i] * S_{t-1}[i,j] + k_t[i] * v_t[j]      # state update
y_t[j]   = sum_i (scale * q_t[i]) * S_t[i,j]            # output
```

This is the **per-(t,h,i)** GLA recurrence. The decay `g` has full per-token, per-head, per-key-dim resolution.

**Match to Lightning Attention** (Qin et al. 2024, fixed power-law decay per head, NOT per-token, NOT per-key-dim):

The Lightning Attention recurrence is `S_t = γ_h * S_{t-1} + k_t v_t^T` where `γ_h ∈ ℝ` is a single per-head fixed scalar. To express this through `ggml_gated_linear_attn`, we set:

```
g[t,h,i] = γ_h     for all t, all i
```

i.e., a tensor of shape `[S, H, T]` filled with the per-head decay constant `γ_h` broadcast across both the S axis and the T axis. **No shape mismatch, no kernel modification needed for v1.**

**Precision**: kernel runs **F32 throughout** — state, accumulators, all reads/writes are F32. The BF16-drift concern from paper Section 7 (state recurrence accumulates error in BF16 training) does NOT apply at inference time when state is F32. ✓ (L1.2 will confirm.)

**Memory cost of redundant g**: For Ring-mini (~32 heads × 128 head_dim × 8K tokens = 33 MB per layer per forward pass), this is acceptable. L5 (dedicated op) would eliminate the redundant storage.

**Threading**: heads are partitioned across threads (`h_start = HEADS*ith/nth`, `h_end = HEADS*(ith+1)/nth`). For Ring-mini at H=32, EPYC 96-thread bind would have only 32 of 96 threads doing work per call → underutilization. **Flag for L4 throughput analysis.**

**Edge case**: `state_prev` switches between `state_cur` (mid-sequence) and `dst->src[4]->data` (sequence start, position `t % (T/n_seqs) == 0`). For greedy single-stream decode (n_seqs=1), this means state is read from input on the very first token of a fresh state, and from in-place state thereafter. Standard GLA persistence; nothing special needed.

**Conclusion for L1.6 (preliminary, pending L1.2-L1.5)**: GO. The op accepts `g` as a tensor of the right shape; constant fill is a degenerate case the kernel handles correctly.

#### L1.3 finding — template strategy revised (2026-04-30)

**The original handoff's recommendation to derive `llm_build_ring_linear` from `llm_build_delta_net_base` is WRONG.** The base class methods all dispatch to `ggml_gated_delta_net` (GDN), not `ggml_gated_linear_attn` (GLA). GDN and GLA are different recurrences:

| Op | Recurrence | Used by |
|----|-----------|---------|
| `ggml_gated_delta_net` (GDN) | `S_t = S_{t-1}(g_t I − β_t k_t k_t^T) + β_t k_t v_t^T` | kimi-linear, qwen3.5, qwen3-next, qwen3.5-moe |
| `ggml_gated_linear_attn` (GLA) | `S_t = g_t · S_{t-1} + k_t v_t^T` (element-wise per-(t,h,i)) | RWKV-6 (qrwkv mode only) |

Lightning Attention's recurrence `S_t = γ_h · S_{t-1} + k_t v_t^T` (fixed per-head scalar) is mathematically a degenerate-`g` GLA, NOT a GDN special case. Therefore the L3 template must mirror **`llm_build_rwkv6_base::build_rwkv6_time_mix`** (the only existing GLA consumer in tree), not `llm_build_kimi_linear`.

**Reference call site** (`src/models/rwkv6-base.cpp:137` in qrwkv branch):
```cpp
wkv_output = ggml_gated_linear_attn(ctx0, k, v, r, w, wkv_state,
                                    pow(head_size, -0.5f));
// Output split (lines 141-147):
cur       = ggml_view_1d(ctx0, wkv_output, n_embd * n_tokens, 0);
wkv_state = ggml_view_1d(ctx0, wkv_output, n_embd * head_size * n_seqs,
                         n_embd * n_tokens * sizeof(float));
ggml_cpy(ctx0, wkv_state, mctx_cur->get_s_l(il) view);
```

**For Lightning Attention** (Ring-mini), we'd:
1. Skip RWKV's time-shift / lerp / receptance machinery (RWKV-specific, not applicable).
2. Compute Q/K/V via the standard 3-projection pattern (`ggml_mul_mat(layer.wq, cur)` etc.), since Ring-mini does **not** use RWKV-style x_prev mixing.
3. Build `g` as a **constant** tensor of shape `[S, H, T]` filled with the per-head decay constant `γ_h` (broadcast across S and T axes). Construction options: (i) `ggml_repeat([1,H,1] decay → [S,H,T])`, (ii) `ggml_new_tensor_3d` + manual fill at model load. Option (i) is graph-friendly.
4. Call `ggml_gated_linear_attn(ctx0, K, V, Q, g_const, state, scale)`.
5. Split output + persist state — identical pattern to RWKV6 above.

**Recommended L3 inheritance**: derive `llm_build_ring_linear` directly from `llm_graph_context` (NOT `llm_build_delta_net_base`, NOT `llm_build_rwkv6_base`). Inline the GLA call following RWKV6's pattern but stripped of RWKV-specifics. Estimated ~150 LOC unchanged from prior estimate.

**Hybrid handling**: Ring-mini uses M=4 (4 linear : 1 softmax). Periodic softmax layers reuse the standard `build_attn` path — no new code needed. The `if (hparams.is_recurrent(il)) { GLA path } else { build_attn path }` pattern from kimi-linear (line 120, 206) IS reusable structurally even though we don't inherit from `delta_net_base`.

**State allocation**: per-head SxS = head_dim² × n_head × n_seqs. For Ring-mini at head_dim=128, n_head=32 (assumed; verify in L1.4), 1 seq → 2 MB per recurrent layer. With ~30 recurrent layers in a ~32-layer M=4 model → ~60 MB total recurrent state. Trivial.

**State plumbing**: re-use `llama_memory_recurrent_context::get_s_l(il)` per kimi-linear / RWKV6 pattern.

#### L1.5 finding — backend coverage of `GGML_OP_GATED_LINEAR_ATTN` (verified 2026-04-30 via grep)

| Backend | Status | Source location |
|---------|--------|-----------------|
| CPU (AVX/AVX-512/SVE/NEON + scalar) | ✅ supported | `ggml/src/ggml-cpu/ops.cpp:10524-10702` (`ggml_compute_forward_gla_f32`) |
| CUDA | ✅ supported | `ggml/src/ggml-cuda/gla.cu` (93 LOC) |
| HIP (AMD ROCm) | ✅ inherits | `ggml/src/ggml-hip/CMakeLists.txt` globs `../ggml-cuda/*.cu` |
| MUSA (Moore Threads) | ✅ inherits | `ggml/src/ggml-musa/CMakeLists.txt` globs `../ggml-cuda/*.cu` |
| SYCL (Intel) | ✅ supported | `ggml/src/ggml-sycl/gla.cpp` (106 LOC) + `gla.hpp` |
| CANN (Huawei Ascend) | ✅ supported | `ggml/src/ggml-cann/aclnn_ops.cpp` |
| BLAS / zDNN / zenDNN | ✅ falls back to CPU | (op not implemented; backend dispatcher routes unsupported ops to CPU) |
| Metal | ❌ missing | (would need shader port; pre-existing gap from RWKV-6) |
| Vulkan | ❌ missing | (pre-existing gap) |
| OpenCL | ❌ missing | (pre-existing gap) |
| WebGPU | ❌ missing | (pre-existing gap) |
| OpenVINO | ❌ missing | (pre-existing gap) |
| Hexagon | ❌ missing | (pre-existing gap) |

**For v1 port (CPU-only target on EPYC)**: ✅ fully covered, no kernel work needed.

**For upstream contribution**: the Metal/Vulkan/OpenCL/WebGPU gaps are pre-existing — same gaps RWKV-6 has. Adding Lightning Attention to the existing GLA consumer set does NOT introduce a new backend hole. A v1 PR upstream would ship with the same backend matrix as RWKV-6 already has; Metal/Vulkan ports would be follow-on work for both.

**No L1.5 blocker for L1.6 GO decision.**

#### L1.4 finding — Ring-mini-linear-2.0 architecture + decay coefficient (verified 2026-04-30)

Source: `https://huggingface.co/inclusionAI/Ring-mini-linear-2.0/raw/main/{config.json,modeling_bailing_moe_linear_v2.py,configuration_bailing_moe_linear_v2.py}`.

**Architecture identifiers**:
- `model_type: "bailing_moe_linear"` (NOT "ling_linear" as the deep-dive earlier guessed)
- `architectures: ["BailingMoeLinearV2ForCausalLM"]`
- Linear-attn class: `BailingMoeV2LinearAttention`
- Reference kernel: `fla.chunk_simple_gla` (chunk path) + `fla.fused_recurrent_simple_gla` (recurrent path) from `flash-linear-attention v0.3.2`. **FLA's "simple GLA" = scalar per-head decay GLA = exactly what `ggml_gated_linear_attn` implements.**

**Confirmed dimensions** (from `config.json`):
| Field | Value |
|-------|-------|
| `num_hidden_layers` | **20** |
| `hidden_size` | 2048 |
| `head_dim` | **128** |
| `num_attention_heads` (Q heads) | **16** |
| `num_key_value_heads` (KV heads, GQA) | **4** |
| `layer_group_size` | **5** |
| `group_norm_size` | 4 |
| `first_k_dense_replace` | 1 (first dense FFN replaces MoE) |
| `num_experts` | 256 |
| `num_experts_per_tok` | 8 |
| `num_shared_experts` | 1 |
| `partial_rotary_factor` | 0.5 (used on softmax layers only) |
| `max_position_embeddings` | 131072 |

**M=4 layer pattern** (from `modeling_bailing_moe_linear_v2.py` decoder-layer init):
```python
self.attention_layer_type = "attention" if (layer_idx + 1) % config.layer_group_size == 0 or \
    layer_idx >= config.num_hidden_layers // config.layer_group_size * config.layer_group_size else "linear_attention"
```
With `layer_group_size = 5` and `num_hidden_layers = 20`: every 5th layer (indices 4, 9, 14, 19) is softmax attention; the other 16 are linear (Lightning Attention). **M=4 = "4 linear : 1 softmax", confirmed.** No tail trimming since 20 is divisible by 5.

**Decay coefficient — exact form** (`BailingMoeV2LinearAttention.build_slope_tensor`):
```python
def get_slopes_power_of_2(n):
    start = 2 ** (-(2 ** -(math.log2(n) - 3)))   # ALiBi-style slope base
    ratio = start
    return [start * ratio ** i for i in range(n)]
slopes = build_slope_tensor(num_heads)             # ALiBi positive slopes
# Per-layer scaling and sign flip:
slope = -slopes * (1 - (layer_idx - 1) / (num_hidden_layers - 1) + 1e-5)
self.register_buffer('slope', slope, persistent=False)
```

For Ring-mini (`num_heads = 16`): `start = 2^(-2^(-(log2(16)-3))) = 2^(-2^(-1)) = 2^(-0.5) ≈ 0.7071`. Slopes = `[0.7071^1, 0.7071^2, ..., 0.7071^16]` ≈ `[0.7071, 0.5000, 0.3536, 0.2500, 0.1768, ..., 5.96e-3]`.

**Per-layer scaling**: linear depth-decay `1 - (layer_idx-1)/(n_layers-1) + 1e-5` ramps from ~1.053 (layer 0) down to ~0.105 (layer 18). Final `slope` is **negative** with magnitude ranging from full ALiBi at shallow layers to ~10× weaker at deep layers.

**FLA call site** in `BailingMoeV2LinearAttention.forward`:
```python
o, recurrent_state = self.lightning_attn_ops[mode](
    q=query_states, k=key_states, v=value_states,
    g=self.slope[None, None, :].expand(bsz, q_len, self.num_heads),
    initial_state=recurrent_state,
    output_final_state=use_cache,
)
```
The `g` is `[bsz, q_len, n_heads]` — broadcast of per-head scalar across all tokens. **No per-token, no per-key-dim variation.**

**FLA semantics** (per FLA source for `simple_gla`): `g` is treated as a **log-decay**; the kernel computes `S_t = exp(g_t) * S_{t-1} + k_t v_t^T` (multiplicative decay = exp of log-decay). With `g = -|slope|`, the multiplier is `exp(-|slope|) ∈ (0, 1)` — a contractive decay, as required.

**Mode dispatch** (chunk vs recurrent):
```python
mode = 'fused_recurrent' if hidden_states.shape[1] <= 64 else self.mode  # default 'chunk'
```
i.e., **prefill of ≤64 tokens uses fused_recurrent; longer uses chunkwise** (FLA default chunk size 64). For our v1 (CPU only), the existing `ggml_compute_forward_gla_f32` is a single recurrent loop covering both regimes correctly — **no chunkwise speed-up but bit-identical output**. L5 (dedicated op) would be the place to add the chunked-prefill speedup.

#### L1.2 finding — BF16 KV-state drift, FP32-accumulation strategy (resolved via reference impl, paper PDF not extractable)

Reference-impl reading (`modeling_bailing_moe_linear_v2.py`) tells us what we need:
1. **Inference accumulation**: the FLA kernel's internal accumulator dtype is the call site's responsibility. With our `ggml_compute_forward_gla_f32`, **state is F32, k/v/q/g/dst are F32, all FMA chains are F32**. The BF16-drift problem the paper discusses (training-time drift) is **not a concern at our F32 inference path**.
2. **Post-output rescaling**: Ring-mini applies a `BailingMoeV2GroupRMSNorm` (FP32-cast inside) immediately after the linear-attention output, then a sigmoid gate from a separate projection (`g_proj`), then the output projection. Our llama.cpp port must mirror this **exactly** (FP32-cast in g_norm + sigmoid gate from g_proj) — but that's standard `build_norm` + `ggml_sigmoid` + `ggml_mul`, no novel kernel work.
3. **No per-step FP32 conversion needed inside the recurrence** since our state is already F32. (We'd lose this benefit if we ever quantized the recurrent state — out of scope for v1.)

**Implication**: BF16-drift handling is a non-issue for our v1 port. The only constraint is matching the post-output norm + sigmoid gate structure precisely, which is straightforward graph-building.

**Section 7 paper read deferred**: PDF compressed-stream extraction failed via WebFetch; the actionable content (FP32 accumulation, layer-scaled slopes) was already recoverable from the reference impl. If a future drift-debugging issue surfaces, re-attempt the paper read via `arxiv-vanity` or local PDF tools.

#### Implementation notes derived from L1.4 (for L2/L3 work)

**GGUF tensor layout** (proposal — to be confirmed during L2 converter work):

Per linear-attention layer (16 of 20 layers in Ring-mini):
- `attn_q.weight`        `[hidden, n_head*head_dim]` = `[2048, 16*128=2048]`  (Q proj)
- `attn_k.weight`        `[hidden, n_kv_head*head_dim]` = `[2048, 4*128=512]`  (K proj, GQA)
- `attn_v.weight`        `[hidden, n_kv_head*head_dim]` = `[2048, 512]`        (V proj, GQA)
- `attn_output.weight`   `[n_head*head_dim, hidden]`                          (output proj `dense`)
- `attn_g.weight`        `[hidden, n_head*head_dim]` = `[2048, 2048]`         (sigmoid gate `g_proj`)
- `attn_g_norm.weight`   `[head_dim]`                                         (post-attn GroupRMSNorm)
- `attn_decay`           `[1, n_head, 1]` or just `[n_head]` — **the precomputed `exp(slope_per_layer_per_head)` decay constants** (NEW, distinct from any existing tensor)
- `attn_norm.weight`     `[hidden]`                                           (pre-attn RMSNorm)

Per softmax-attention layer (4 of 20):
- standard Qwen-style q/k/v/o projections + partial RoPE (factor 0.5)
- `attn_q_norm`, `attn_k_norm` (use_qk_norm=True)
- `attn_norm`

Per-layer FFN/MoE (all 20 except layer 0 which is dense):
- 256 experts + 1 shared expert + sigmoid gating (`score_function: "sigmoid"`)

**GQA handling**: K/V projections produce `n_kv_head=4` heads but the GLA op needs `n_head=16`. Use the same `ggml_repeat` pattern as `rwkv6-base.cpp:110-117` to broadcast K/V/decay from 4 heads up to 16 before the GLA call. State is then 16 heads × head_dim × head_dim.

**State allocation**: per linear layer per seq = `n_head * head_dim * head_dim * 4 bytes` = `16 * 128 * 128 * 4 = 1,048,576 bytes = 1 MiB`. Total: 16 linear layers × 1 MiB = 16 MiB recurrent state per seq. Well within `n_embd_s` budgeting.

**Decay tensor construction at graph time**: load `attn_decay[n_head]` as a fixed buffer per linear layer; broadcast to `[head_dim, n_head, n_tokens]` via `ggml_repeat`. Since the values are layer-constant, `attn_decay` is a model weight, not recomputed.

**Decay value computation at convert time** (`convert_hf_to_gguf.py`): replicate the Python `build_slope_tensor` + per-layer scaling, then `exp(slope)` to convert from FLA's log-decay to our op's multiplicative decay. Single-line port.

#### L1.6 verdict — GO (2026-04-30)

**All five gates passed:**

| Sub-task | Verdict | Why |
|----------|---------|-----|
| L1.1 — GLA op semantics | ✅ matches | `ggml_compute_forward_gla_f32` implements `S_t[i,j] = g[t,h,i] * S_{t-1}[i,j] + k[t,h,i]*v[t,h,j]`; setting `g[t,h,i] = exp(slope_h)` ∀(t,i) gives Lightning Attention exactly |
| L1.2 — BF16 drift | ✅ N/A for our path | F32 throughout in `ggml_compute_forward_gla_f32`; the post-output GroupRMSNorm-FP32 cast is a standard `build_norm` step |
| L1.3 — Template strategy | ✅ revised | Mirror `llm_build_rwkv6_base::build_rwkv6_time_mix` (qrwkv branch, GLA call site at line 137) — NOT `llm_build_delta_net_base` (which uses GDN op, wrong recurrence) |
| L1.4 — Decay form | ✅ extracted | ALiBi-style `slopes[h] = (2^-0.5)^h` for n_heads=16, scaled per layer by `1 - (l-1)/(L-1) + 1e-5`, sign-flipped, exp'd at convert time |
| L1.5 — Backend coverage | ✅ CPU + CUDA + HIP + MUSA + SYCL + CANN | Metal/Vulkan/OpenCL/WebGPU gaps pre-existing from RWKV-6 status |

**No gaps blocking L2 (converter) or L3 (model variant). No new ggml ops required.** The constant-`g` formulation is a degenerate but correct case of the existing GLA op; redundant per-(t,i) storage of the same scalar is the only inefficiency, and it is acceptable for v1 (16 MiB per layer per forward pass for Ring-mini at 8K context — see L1.3 finding).

**One open question deferred to L2** (not a blocker): exact GGUF tensor naming convention for `attn_decay` (per-layer per-head precomputed `exp(slope)`). Pick during converter work; suggested name `<arch>.attn_decay` analogous to existing `attn_norm` / `attn_q.weight` patterns.

**Lower-bound estimate of L2+L3 effort revised**: ~3 days (was 3-5). The decay-precompute single-line port + GQA handling reuse + RWKV6-template borrowing have all been pre-validated.

**Risks reaffirmed**:
1. M=4 layer pattern (every 5th layer is softmax) means CPU thread underutilization on linear layers when only 16 of 96 threads do useful work per layer — flag for L4 throughput characterization.
2. `partial_rotary_factor: 0.5` on softmax layers — the standard Qwen-style partial-RoPE plumbing is already in tree (kimi-linear and qwen3.6 both use it); reuse without modification.
3. `score_function: "sigmoid"` MoE gating — supported in tree per kimi-linear's `expert_gating_func`.

**Cleared to begin L2 (converter extension) immediately upon user approval.** L2 + L3 are pure code work with no inference gates. Only L4 (smoke decode + quality spot-check) hits the inference gate.

---

## L2 Phase — Converter Extension (DONE 2026-04-30)

Branch: `feature/lightning-attention-port` off `production-consolidated-v5` HEAD `23bcd6aaf` in `/mnt/raid0/llm/llama.cpp-experimental`. All edits working-tree only (no commits yet).

### Files modified

| File | Lines | Purpose |
|------|-------|---------|
| `src/llama-arch.h` | +1 | `LLM_ARCH_BAILINGMOE_LINEAR` enum |
| `src/llama-arch.cpp` | +1 | arch name string `"bailingmoe-linear"` |
| `gguf-py/gguf/constants.py` | +26 | `MODEL_ARCH.BAILINGMOE_LINEAR` enum + 22-tensor list (TOKEN_EMBD, OUTPUT*, ATTN_NORM/QKV/OUT/Q_NORM/K_NORM/GATE/OUT_NORM, FFN family for hybrid dense+MoE, no NextN since `num_nextn_predict_layers=0`) |
| `gguf-py/gguf/tensor_mapping.py` | +2 | `attention.g_proj` → ATTN_GATE, `attention.g_norm` → ATTN_OUT_NORM patterns |
| `convert_hf_to_gguf.py` | +21 | `BailingMoeLinearV2Model(BailingMoeV2Model)` class, emits `full_attention_interval` + `group_norm_groups` KVs |

### Smoke test (passed without inference)

```python
import sys; sys.path.insert(0, 'gguf-py')
from gguf import constants as C
from gguf.tensor_mapping import TensorNameMap
nm = TensorNameMap(C.MODEL_ARCH.BAILINGMOE_LINEAR, 20)
# All 17 expected tensor paths resolve correctly:
#   model.embed_tokens.weight                   -> token_embd.weight
#   model.layers.0.input_layernorm.weight       -> blk.0.attn_norm.weight
#   model.layers.0.attention.query_key_value... -> blk.0.attn_qkv.weight
#   model.layers.0.attention.dense.weight       -> blk.0.attn_output.weight
#   model.layers.0.attention.g_proj.weight      -> blk.0.attn_gate.weight       (linear-attn only)
#   model.layers.0.attention.g_norm.weight      -> blk.0.attn_output_norm.weight (linear-attn only)
#   ...
```

`python3 -m py_compile convert_hf_to_gguf.py` → exit 0.

---

## L3 Phase — C++ Loader + Graph Builder (IN PROGRESS — L3.1-L3.4 DONE, L3.5-L3.7 PENDING compile-window approval)

### L3.2 done — `llm_arch_is_hybrid` + `llm_arch_supports_sm_tensor`

`LLM_ARCH_BAILINGMOE_LINEAR` added to both classifier helpers in `src/llama-arch.cpp`. Mirrors KIMI_LINEAR (hybrid=true, supports_sm_tensor=false).

### L3.3 done — `llm_load_hparams` case

Added to `src/llama-model.cpp` after BAILINGMOE2. Reads:
- Bailing expert KVs (`n_layer_dense_lead`, `n_ff_exp`, `n_ff_shexp`, `n_expert_shared`, `expert_weights_scale/norm`, `expert_gating_func`)
- `LLM_KV_ATTENTION_GROUPNORM_GROUPS` → `hparams.n_norm_groups`
- `LLM_KV_FULL_ATTENTION_INTERVAL` (default 5) → `recurrent_layer_arr[il] = ((il+1) % full_attn_interval != 0)` for all layers
- `LLM_TYPE` dispatch: 20 → 16B_A1B (Ring-mini), 30 → 100B_A6B (tentative for Ring-flash)

### L3.4 done — `llm_load_tensors` case

Added to `src/llama-model.cpp` after BAILINGMOE2. Per-layer dispatch on `hparams.is_recurrent(il)`:

| Tensor | Linear layer | Softmax layer |
|--------|-------------|---------------|
| `wqkv` | `[n_embd, n_embd + 2*n_embd_head_k*n_head]` (MHA-shaped K/V) | `[n_embd, n_embd + 2*n_embd_gqa]` (GQA-shaped K/V) |
| `wo` | `[n_embd_head_k*n_head, n_embd]` | same |
| `attn_q_norm` / `attn_k_norm` | `[n_embd_head_k]` | same |
| `wqkv_gate` (g_proj) | `[n_embd, n_embd_head_k*n_head]` | NOT ALLOCATED |
| `attn_out_norm` (g_norm) | `[n_embd_head_k*n_head]` | NOT ALLOCATED |

Plus standard FFN/MoE tensors (Bailing pattern: `first_k_dense_replace=1`, dense FFN at layer 0, MoE at 1..19 with 256 experts + 1 shared).

**Field reuse note**: `wqkv_gate` field on `llama_layer` already exists and is used by AFMOE/qwen3.5/step3.5 for ATTN_GATE-mapped tensors. Reusing it for Lightning Attention's `g_proj` is consistent with prior arches.

### L3.5 DONE — `src/models/ring-linear.cpp` graph builder

NEW FILE, ~205 LOC. Mirrors `BailingMoeV2LinearAttention.forward()` exactly. Per-layer dispatch on `hparams.is_recurrent(il)`:

**Linear path**:
1. `build_qkv(layer, cur, head_dim, n_head, /*n_head_kv=*/n_head, il)` — passes n_head_kv=n_head since linear layers are MHA
2. Q/K norm via `build_norm(LLM_NORM_RMS)` with use_qk_norm
3. Partial NeoX RoPE on Q and K (`ggml_rope_ext` with `n_rot < head_dim`)
4. `ggml_cont` on Q/K/V to satisfy GLA op contiguity asserts
5. Decay tensor `g` constructed at graph build via ggml ops:
   - `h_idx = ggml_arange(0, n_head, 1)`
   - `slope_h = ggml_exp(ggml_scale(h_idx, ln(slope_base)))` = `slope_base^h`
   - `decay_per_h = ggml_exp(ggml_scale(slope_h, -slope_base * layer_factor))` = `exp(-slope_base^(h+1) * layer_factor)`
   - `ggml_repeat` to broadcast `[1, n_head, 1]` → `[head_dim, n_head, n_tokens]`
6. `ggml_gated_linear_attn(K, V, Q, g, state, kq_scale)` — scale = 1/sqrt(head_dim)
7. Split output: token output `[0, n_embd*n_tokens)` + new state `[n_embd*n_tokens, +n_embd*head_dim*n_seqs)`
8. `ggml_cpy` new state into `mctx_rs->get_s_l(il)` at `kv_head` offset
9. `ggml_group_norm` with `group_norm_size=4` then per-channel `ggml_mul` against `layer.attn_out_norm`
10. Sigmoid gate from `g_proj(input_hidden_states)`, NOT attention output
11. `gate * o_normed`, then output projection via `layer.wo`

**Softmax path**:
1. `build_qkv(layer, cur, head_dim, n_head, n_head_kv, il)` — GQA with n_head_kv=4 from hparams
2. Same Q/K norm + partial RoPE
3. Standard `build_attn(inp->get_attn(), wo, ...)` — full softmax via the existing kernel
4. Returns `cur` directly (no post-attention gate on softmax layers)

**Both paths**: residual + FFN dispatch (dense for `il < n_layer_dense_lead`, MoE via `build_moe_ffn` otherwise) + residual + cvec + final norm + lm_head.

### L3.6 DONE — wiring

- `src/models/models.h`: `struct llm_build_ring_linear : public llm_graph_context` forward decl after `llm_build_kimi_linear`
- `src/llama-model.cpp` build_graph dispatch: `case LLM_ARCH_BAILINGMOE_LINEAR: llm = std::make_unique<llm_build_ring_linear>(*this, params)` after KIMI_LINEAR
- `src/llama-model.cpp` RoPE type dispatch: `LLM_ARCH_BAILINGMOE_LINEAR` added to NEOX group with BAILINGMOE2
- CMakeLists: no edit needed (auto-globbed via `file(GLOB LLAMA_MODELS_SOURCES "models/*.cpp")` in `src/CMakeLists.txt:9`)

### L3.7 DONE — compile gate PASSED

Fresh `cmake -B build_lightning -DGGML_CUDA=OFF -DGGML_NATIVE=ON -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF` configure clean. `cmake --build build_lightning -j 4` (low parallelism to leave EPYC headroom for parallel inference benchmarks) produced:
- `libllama.so`, `libggml*.so`, `libmtmd.so` linked clean
- 66 binaries built including `llama-bench`, `llama-perplexity`, `llama-batched`, etc.
- `ring-linear.cpp.o` size 21,120 bytes
- `nm -D libllama.so` confirms `llm_build_ring_linear::llm_build_ring_linear(...)` symbol at offset `0x263400`

**One compile error found and fixed during the gate**: `hparams.n_embd_head_k` → `hparams.n_embd_head_k()` (it's a method, not a field). All other code compiled clean on first attempt.

**Build did NOT touch any other build directories** — used `build_lightning/` exclusively.

---

## Summary of L1+L2+L3 completion (2026-04-30)

Branch: `feature/lightning-attention-port` off `production-consolidated-v5` HEAD `23bcd6aaf` in `/mnt/raid0/llm/llama.cpp-experimental`. Working-tree only — **no commits yet**.

| File | Type | Lines |
|------|------|-------|
| `convert_hf_to_gguf.py` | modify | +21 (BailingMoeLinearV2Model class) |
| `gguf-py/gguf/constants.py` | modify | +26 (BAILINGMOE_LINEAR enum + 22-tensor list) |
| `gguf-py/gguf/tensor_mapping.py` | modify | +2 (g_proj, g_norm patterns) |
| `src/llama-arch.h` | modify | +1 (LLM_ARCH_BAILINGMOE_LINEAR enum) |
| `src/llama-arch.cpp` | modify | +3 (arch name + 2 classifiers) |
| `src/llama-model.cpp` | modify | +100 (load_hparams + load_tensors + build_graph dispatch + RoPE type) |
| `src/models/models.h` | modify | +8 (forward decl) |
| `src/models/ring-linear.cpp` | NEW | ~205 |
| **TOTAL** | | **~366 LOC** |

Compile gate passed: `libllama.so` + 66 tools build clean with the new arch fully wired in. Lightning Attention port v1 ready for L4 (smoke decode + quality spot-check), gated on user inference approval per `feedback_no_concurrent_inference.md`.

**No L4 inference launched. No models loaded.**

**Verified forward path** (from `BailingMoeV2LinearAttention.forward()` reference impl):

```
hidden_states  →  cur = build_norm(input, attn_norm)
                  ↓
   Linear-attention path (when is_recurrent(il)):
                  ↓
   qkv = build_lora_mm(layer.wqkv, cur)                  // [bsz, q_len, 3*n_head*head_dim]
   qkv = reshape_4d(head_dim, 3*n_head, n_seq_tokens, n_seqs)
   Q = view(qkv, 0..n_head)            ; K = view(qkv, n_head..2*n_head)
   V = view(qkv, 2*n_head..3*n_head)
                  ↓
   if use_qk_norm:
     Q = build_norm(Q, attn_q_norm, RMS, head_dim eps)
     K = build_norm(K, attn_k_norm, RMS, head_dim eps)
                  ↓
   Q,K = ggml_rope_ext(..., n_rot=head_dim*partial_rotary_factor, NEOX, ...)
         (partial RoPE on first n_rot of head_dim — RoPE IS applied on linear path
          per the reference impl, even though Lightning Attention is position-implicit)
                  ↓
   state = build_rs(inp_rs, ssm_state_il, n_embd_s, n_seqs)
   state = reshape_4d(head_dim, head_dim, n_head, n_seqs)
                  ↓
   // Decay tensor `g`: per-head fixed scalar broadcast across all (t,i).
   //   slope[h] = -((2^-0.5)^(h+1)) * (1 - (il-1)/(L-1) + 1e-5)   // ALiBi + per-layer
   //   g_value[h] = exp(slope[h])
   // Construction: bake `g_per_head[n_head]` as a model weight at LOAD time
   //   (compute in load_tensors using formula; store in layer.attn_decay or equivalent).
   //   Then at graph time: ggml_repeat into [head_dim, n_head, n_seq_tokens, n_seqs].
   // Alternative: bake per-(layer,head) precomputed value into a GGUF tensor.
   //   Cleanest: model-load-time bake using formula, no GGUF tensor needed.
                  ↓
   gla_out = ggml_gated_linear_attn(ctx0, K, V, Q, g_4d, state, kq_scale=1/sqrt(head_dim))
   o      = view_1d(gla_out, n_embd*n_tokens, 0)
   new_s  = view_1d(gla_out, n_embd*head_dim*n_seqs, n_embd*n_tokens*element_size)
   build_forward_expand(ggml_cpy(new_s, ssm_state_il view at kv_head))
                  ↓
   // Post-attention: GroupRMSNorm(o) with group_norm_size=4 over n_head*head_dim
   o = ggml_group_norm(o, n_norm_groups, eps)            // existing ggml op
   o = ggml_mul(o, layer.attn_out_norm.weight broadcast)
                  ↓
   // Sigmoid gate computed from input hidden_states (NOT attention output)
   g_proj = build_lora_mm(layer.wqkv_gate, cur)
   gate   = ggml_sigmoid(g_proj)
   gated  = ggml_mul(o, gate)
                  ↓
   cur = build_lora_mm(layer.wo, gated)
                  ↓
   Softmax-attention path (when !is_recurrent(il)):  use existing build_attn() + GQA-4 + partial RoPE
                  ↓
   Residual + FFN/MoE (mirror BAILINGMOE2 build_moe_ffn pattern with 256 experts + 1 shared expert)
```

### Open questions to resolve in L3.5

1. **Decay tensor storage decision**: bake `g_per_head[n_head]` at load_tensors time (compute the slope formula in C++, store as a per-layer F32 buffer) — cleanest, no GGUF tensor needed.
   - Alternative: have the converter precompute and store `attn_decay[n_head]` as a GGUF tensor — keeps the slope formula in Python (single source of truth) but adds 16×4=64 bytes/layer to the GGUF.
   - Recommendation: **converter-side bake** (Python is the reference). Add `MODEL_TENSOR.ATTN_DECAY` enum + `blk.{bid}.attn_decay` template + load alloc.

2. **`ggml_group_norm` interface**: confirm signature `ggml_group_norm(ctx, src, n_groups, eps)` returns normalized-only tensor (no learnable weight applied). Need `ggml_mul(result, layer.attn_out_norm.weight)` for the per-channel weight after.

3. **`recurrent_layer_arr` set BEFORE `n_embd_s()` is queried**: confirm ordering in `llm_load_hparams` so `recurrent_layer_arr[il]` returns true for linear layers when state allocator queries it.

4. **Recurrent state shape per layer**: per-layer `n_embd_s = head_dim * head_dim * n_head` for linear layers, 0 for softmax layers. The hparams API for per-layer `n_embd_s` needs verification.

5. **Softmax-attention path RoPE**: standard partial RoPE on Q/K via `ggml_rope_ext(n_rot, NEOX, ...)`. Use BAILINGMOE2's pattern.

6. **State persistence vs recurrent_state initialization**: `build_rs(inp_rs, ssm_state_il, n_embd_s, n_seqs)` returns the state-input tensor; the GLA op consumes it as `src[4]` and emits new state appended to output; we then `ggml_cpy` the new state into the persistent `ssm_state_il` buffer at the right `kv_head` slot. Mirror RWKV-6's pattern (lines 144-147 of `rwkv6-base.cpp`).

### L3.6 PENDING — wiring

Forward declare `llm_build_ring_linear` in `src/models/models.h` after `llm_build_kimi_linear`. Add case to build_graph dispatcher in `llama-model.cpp` after `LLM_ARCH_KIMI_LINEAR`. Add `ring-linear.cpp` to `src/models/CMakeLists.txt`.

### L3.7 PENDING — compile gate

Fresh `cmake -B build_lightning -DGGML_CUDA=OFF -DGGML_NATIVE=ON .` then `cmake --build build_lightning`. **NOT YET RUN** because compile competes for EPYC CPU with the parallel agent's inference benchmarks. Wait for window.

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
