# CTX-JETLONG-PROTO: design note (CPU-first, non-fused Jet-Long in llama.cpp)

- Branch `llama.cpp-experimental-jetlong-proto-20261006`. Worktree `/mnt/raid0/llm/worktrees/llama-jetlong-proto-20261006`.
- Parent: production v10 `ffc1bac82`. The production tree was left untouched (verified `ffc1bac82`, branch `production-consolidated-v10`).
- Commits: `a2e129fcc` (implementation) and `b216a5deb` (tests, tip).
- Gate CTX-3a PASSED (`../ctx3a/COST.md`, `results_20261006T054613Z.csv`).

Sources. In the anchors below, M = `Jet-Long/jetlm/modeling/jetlong/modeling_qwen3_jetlong.py` @a7a9071 under
`/mnt/raid0/llm/tmp/intake-ctxext-src/`, and B = `jetlm/kernels/cute_jetlong_backend.py`. Intake-1900/1919 dive_corrections
(origin/main) supply w0 = 2048 (Eq. 2), in-window = base RoPE (M:149-151), the batch-max G (M:146) and the uncached cost
(M:546). `../CTX2_KSHIFT.md` showed that K-shift is unsafe at v10 (H1-H3), so nothing here uses `seq_div`/K-shift. The correction
is applied on read, inside the attention graph.

## 1. What is computed (Eq. 1 as the reference implements it)
For a query at position p and a key at position k of the same sequence, with L = (max position of the sequence) + 1:
- **In-window (L <= w):** the plain base-RoPE attention (M:149-151). The prototype builds **nothing**: no extra node, input or
  copy. The stock graph runs, so in-window identity holds by construction, and T1 confirms it.
- **Above native:** G = ceil(L / w) (M:155).
  - **Near** (p - k <= w0): score <q_base(p), k_base(k)>. This is FA window (w0, 0) in prefill (M:469) and the last w0 keys in decode (M:503-504).
  - **Distant** (p - k > w0): score <q_grp(p), k_grp(k)>, where x_grp = rot(x_base, floor(pos/G) - pos) (M:396-399, rotation M:227).
    This is a correction rotation applied to the BASE-roped vectors, as the reference does. It is a pure rotation: freq_scale 1,
    no YaRN, no mscale. That avoids the CTX-2 H1 defect class.
  - **One softmax over the union.** This equals the reference's LSE merge of the near and distant branches (M:617 and the oracle
    `_reference_jetlong_decode`, B:93). It also equals the prefill A+B-C merge in exact arithmetic (M:469-486). The
    `clamp(min=0)`/`1e-6` guards are numerical artefacts of the 3-call form and are not needed here.
- **Window semantics:** "near" is per query, p - k <= w0 inclusive, matching FA `window_size=(w0,0)`. Decode in the reference
  uses the batch max (M:503). For np = 1 the two are identical.

## 2. Where it enters the graph
`llm_graph_context::build_attn(llm_graph_input_attn_kv*, ...)` (`src/llama-graph.cpp:2836-2884`) is the KV-cache attention.
For qwen35moe it serves exactly the 10 full-attention layers. The 30 GDN layers have no RoPE and no KV cache. It also serves the
MTP head's own attention layer (il 40) in the MTP context.
1. `q_rope = q_cur` is captured **before** the K Hadamard (`:2836`). Jet-Long needs Q in the RoPE domain.
2. The K store result `k_store` (`cpy_k`) is captured so the side-cache update depends on this ubatch's write.
3. The stock `build_attn_mha` runs unchanged and gives `out_stock`.
4. Only if `inp->jl_active` (decided per ubatch, see section 4): `llama_jetlong_build_attn(...)` (`src/llama-jetlong.cpp:206`) returns
   the spliced output. The V Hadamard inverse and `wo` follow as in stock.

Graph composition (`src/llama-jetlong.cpp`). All ops are stock ggml ops and no kernel was written:
- **Side-cache rows** (`:240-268`). The rows are written or moved cells, or all cells at an epoch change.
  - `get_rows` dequantizes the K-cache rows to **f32** (`:246`).
  - For quantized K, the Hadamard is undone on the rotary dims only: `rope(k)[0:n_rot] = H[0:n_rot,:] * Kc` (`:256`).
  - `rope_multi` applies the per-row delta (`:195` `jl_rope`).
  - `set_rows` writes the rows into the f32 side cache (`:267`).
- **Queries.**
  - Stock q gives the near scores.
  - `q_rope * pass_mask`, Hadamard-transformed when K is quantized, scores the 192 pass-through dims directly against the
    cache (`:290`). No per-key work is needed for those dims.
  - `rope_multi(q_rope[0:64], delta_q)` gives the grouped rotary query (`:297`).
- **Scores** (`:304-316`): `s_near = K.q`; `s_dist = K.q_pass + Kgrp64.q_g`; `kq = s_near*m_near + s_dist*m_dist`.
  The 0/1 masks come from the host. Then `soft_max_ext` uses the stock KQ mask (`:319`).
- **V:** cast to f32, transposed, mat-mul.
- **Splice** (`:338-339`): `get_rows(concat(out_stock, out_jl), sel)`. Rows of in-window sequences come from `out_stock` by pure copy.
  An in-window sequence co-batched with an above-native one is therefore bit-identical to stock (T1c). This is a deliberate
  deviation from the reference, which would group every sample in a batch with the batch-max G (M:146).

## 3. q8_0 K and the Hadamard (production :8070 runs `-ctk q8_0 -ctv q8_0`)
- `attn_rot_k` is on for quantized K, so the cache holds `q8_0(H256 . rope(k))`. The correction is applied **after dequant, in
  f32, in the RoPE domain**. Only the n_rot = 64 rotary dims ever need rotating. The pass-through 192 dims are invariant under
  the correction. They are scored against the quantized cache with `H . [0, q_pass]`, which equals the stock q8_0 x q8_0 dot product.
- Side-cache precision is f32: 512 B per cell per layer (64 x 2 heads x 4 B). That is about 5.0 GiB for 10 layers at 1M cells
  (+0.5 GiB for the MTP layer). An f16 side cache would halve it (CTX-3a C1). That is a follow-on; it does not change the
  cached == uncached property.
- Measured consequence: in the q8_0 configuration the residual vs an exact f32 reference (1.5e-3) is the q8_0 quantization of Q
  in the two q8_0 dot products. The stock path has the same 9.5e-4 on the same rows. Against a Q-quantization-aware reference the
  Jet-Long residual is 1.8e-4 (L = 1124) and 1.3e-6 (L = 300001). See TESTS.md.

## 4. Epochs, the per-G-epoch cache and what is stored
- **Plan per ubatch** (`llama_jetlong_plan_ubatch`, `src/llama-jetlong.cpp:13`):
  - For each sequence, L_s = max position in the ubatch + 1.
  - Active iff some L_s > w.
  - G = ceil(max over active sequences of L_s / w): one G per ubatch, the batch max, as M:146.
  - `tok_ext[i]` marks the tokens of above-native sequences.
- **Side cache** (`llama_kv_cache::jetlong_init`, `src/llama-kv-cache.cpp:1849`): an F32 tensor `[n_rot*n_head_kv, kv_size, n_stream]` per
  attention layer in a CPU buffer. Each cell stores `rot(k_base[0:n_rot], floor(p/G) - p)` for the (p, G) recorded in
  `llama_jetlong_cell_state` (`pos`, `grp`).
- **Rows recomputed per ubatch** (`llama_jetlong_cell_state::collect`, `:50`):
  - cells written by this ubatch (always);
  - every visible non-empty cell whose recorded G differs from the ubatch G (**epoch change**: all cells once per w tokens);
  - cells whose position changed.
  - `clear`, `state_read` (slot restore/prompt cache) and `update` (K-shift or stream copy) invalidate everything
    (`:370, :825, :2300`).
  - `seq_rm` does not invalidate. A removed cell's content only comes back through a ubatch store, which is always recomputed.
    This keeps MTP draft rejection (seq_rm every step) on the cheap path.
- **Steady state:** n_tokens rows per step. **Epoch change:** all cells (T3: 64 vs 1025 rows; T2-long: 300000/600000 at the first
  above-native step, then 1).
- `--jetlong-uncached` recomputes every row every ubatch. It is the control for T3 and the reference cost.
- Graph reuse:
  - An active ubatch carries per-step update lists and is never reused.
  - An in-window graph is reused only for another in-window ubatch (`can_reuse`, `src/llama-graph.cpp:498-509`).
  - In-window reuse behaviour is unchanged.

## 5. Flag and plumbing
- `--jetlong-window N`: w0, the local window. **Default 0 = off = stock**, with no side cache allocated.
- `--jetlong-native N`: w, default `n_ctx_orig` (262144 for Qwen3.6).
- `--jetlong-uncached`.
- Path: `common_params` -> `llama_context_params.jetlong_*` -> `cparams` (`src/llama-context.cpp:274-285`) -> `create_memory` attaches the
  side cache to the plain or hybrid attention KV cache (`src/llama-model.cpp:2100`).
- Disabled with a warning:
  - when RoPE is not NeoX-paired (NEOX/MROPE/IMROPE);
  - when YaRN/linear scaling is on (`freq_scale != 1` or `ext_factor != 0`);
  - on caches that share cells with another context.
- IMRoPE note: for text tokens t = h = w = p, and with sections [11,11,10,0] every rotary pair uses theta_t/h/w and never e.
  The rotation is therefore exactly NeoX over 64 dims. The correction uses `rope_multi` with the same delta on all axes.
- Knob compiled in: `strings libllama.so | grep -ci jetlong` = 167; `libllama-common.so` contains `--jetlong-window`.

## 6. Known limits of the prototype (not blockers for the gate; they set the window request)
- **Non-fused cost above native.**
  - Each layer and ubatch builds 3 score tensors of n_kv x n_ub x 16 x 4 B, plus an f32 transposed copy of V, plus the stock FA
    (computed and discarded for the above-native rows).
  - Long prefills need `-ub 32`. 1M takes hours (LONGCTX_PLAN.md B).
  - The fused CPU/HIP kernel is the trigger-gated follow-on (STAGE3 section 2).
- **Untested code paths.** The `kv_unified = false` multi-stream path (`-np 4` without unified KV) and the transposed-V (FA off)
  path are coded but not covered by the synthetic tests. Above-native runs use `-np 1`.
- The side-cache bookkeeping is committed when the graph is built. A compute aborted by the abort callback would leave rows marked
  valid that were never written. Clearing or invalidating the cache after an abort is a hardening item.
- **fp32 RoPE angle floor at depth.** With exact (double) angles as the reference, f16 errors grow from 4.4e-5 to 1.6e-4 at 300K
  and to 6.8e-4 at 600K. Against fp32-mirrored angles they stay at 4-6e-5. This is llama.cpp's fp32 rope, which the stock base RoPE
  shares. At 1M expect ~1e-3 (intake-1922 trigger: fp32/f64 rope A/B).
- **G is per ubatch (batch max).** An above-native sequence co-batched with a longer one uses the larger G, as the reference does.
  A verify batch that straddles k*w shares one G.

## 7. MTP implications
- **In-window:** the MTP context builds nothing extra, so drafts, verification and acceptance are unchanged by construction. The
  model-level check is LONGCTX_PLAN gate A.
- **Above native:**
  - The MTP context gets the same flag through `common_context_params_to_llama`. Its attention layer then has its own side
    cache and the same G rule, so draft and target use the same position grouping.
  - Draft rejection (`seq_rm`) does not trigger rebuilds.
  - A verify batch crossing an epoch boundary uses one G for all its tokens, whereas sequential decode would not. Expect an
    acceptance blip once per w tokens, which needs measuring.
  - Graph reuse is disabled while active, so there is an extra graph build per step.
- The MTP/DFlash2 mirroring trigger in STAGE3 section 2 stays open. DFlash2 drafters (other architectures, shared cells) are out
  of scope: the side cache is disabled on cell-sharing caches.
