# DESIGN-DCA: Dual Chunk Attention in llama.cpp

Branch `experimental/dca-20261004` (on champion `90c12df42`), worktree
`/mnt/raid0/llm/llama.cpp-experimental-dca-20261004`. Status: **v1 implemented (CPU-verified, generic ops), v2/v3 planned.**

## 0. Sources and prior art

- **Paper.** An et al. 2024, *Training-Free Long-Context Scaling of Large Language Models* (arXiv 2402.17463). Reference code: HKUNLP/ChunkLlama `chunkllama_attn_replace.py`.
- **Production use.** Qwen2.5-7B/14B-Instruct-1M run it through vLLM:
  - `vllm/model_executor/layers/rotary_embedding/dual_chunk_rope.py` (`DualChunkRotaryEmbedding`, still on vLLM main);
  - `vllm/attention/backends/dual_chunk_flash_attn.py` (removed from main; present at v0.10.0 and on QwenLM/vllm `dev/dual-chunk-attn`).
- **Upstream llama.cpp:** no issue, PR or discussion implements or proposes DCA. A search for "dual chunk", "dual_chunk", "ChunkLlama", "Qwen2.5-1M" and "DCA" found none. Qwen2.5-1M GGUFs therefore run as plain qwen2 with full causal attention.
- Verbatim excerpts and URLs: `upstream-and-vllm-dca-notes.md`. Raw sources: `ref-sources/`.
- **The vLLM implementation is a usable reference.** Its position formulas match ChunkLlama exactly. Its LSE merge is the exact softmax over the union of key sets. Its MInference sparse prefill is optional and only affects performance. `tests/dca_reference.py` reimplements both formulations and checks that they agree.

## 1. The algorithm (what has to be reproduced)

**Notation.** `c = chunk_len = chunk_size - local_size`, `p` is the absolute position, chunk(p) = `p / c`.

| Role | Rotary position |
|---|---|
| Every **key** | `p mod c`. Keys are chunk-periodic and roped once. |
| Query to keys in the **same chunk** (intra, causal) | `p mod c` |
| Query to keys in the **previous chunk** (succ, all of it) | `min(p mod c + c, chunk_size)` |
| Query to keys in **any earlier chunk** (inter) | `min(2c - 1, chunk_size)`, a constant: ChunkLlama `qc_t[c-1]`, vLLM `cos_sin_qc_cache[chunk_len-1]`. Equals `chunk_size` unless `local ≥ c`. |

- **One softmax per query.** It runs over all causal keys, each key scored with the query variant that its chunk distance selects. This equals vLLM's merge of the three partial attentions by their log-sum-exps.
- **Bound on relative positions.** Every query-to-key relative position lies in `[0, chunk_size]`. Pick `chunk_size <= trained context` and the model never sees an unseen rotation. This holds at any total length; the self-check verifies the bound.
- **Logit temperature.** vLLM applies it when `original_max_position_embeddings > 0`: `s = max(1, 0.1*ln(n/orig) + 1)`, a YaRN-style mscale only. vLLM uses n = prompt length at prefill and cache length at decode. llama.cpp v1 uses n = p+1 per token. That is identical at decode, and at prefill it is causal (vLLM's prefill value depends on the future prompt length).
- **Qwen2.5-7B-Instruct-1M** `dual_chunk_attention_config` = `{chunk_size: 262144, local_size: 8192, original_max_position_embeddings: 262144}`, so c = 253952. Its `rope_scaling` is null.
- **For contexts up to c, DCA is exactly plain RoPE attention.**

## 2. Mapping onto llama.cpp

### 2.1 Graph (v1, implemented)

**`llm_graph_context::build_attn_dca`** (`src/llama-graph.cpp`, after `build_attn(llm_graph_input_attn_kv*)`). It takes the **unroped** q and k. A model opts in by calling it when `cparams.dca_chunk_size > 0` (qwen2, qwen35, qwen35moe). Steps:

1. **Rope** k once and q three times from one I32 input `dca_pos` that holds three position slices: [k = q_intra, q_succ, q_inter]. The slices are 1D views, so `ggml_rope_ext` (NEOX, qwen2) and `ggml_rope_multi` (IMROPE, qwen35) both work unchanged.
   - For M-RoPE text tokens, the three temporal/1D sections are remapped and the 4th section (0) is kept.
   - All rope parameters (freq_base, freq_scale, YaRN ext/attn/beta, n_ctx_orig) are the graph's, so YaRN composes mechanically (§4).
   - With `dca_orig_ctx > 0`, the three q tensors are multiplied by an F32 input `dca_qscale` [1,1,n_tokens].
2. **Store** the roped k (chunk-local) and v in the cache through the normal `cpy_k`/`cpy_v`. The cache is unchanged in layout and size.
3. **Score** with `kq_v = mul_mat(K, q_v)` for v in {intra, succ, inter}, then combine `kq = Σ_v kq_v ⊙ sel_v`.
   - `sel` is one F32 input [n_kv, n_tps, n_stream, 3] of 0/1. Each slice is viewed as [n_kv, n_tps, 1, n_stream] and broadcast over heads.
   - It is filled by `llama_kv_cache::set_input_dca_sel` (`src/llama-kv-cache.cpp`) from the cell positions, with the same stream and sequence logic as the KQ mask.
4. **Normalise and apply V.** `soft_max_ext(kq, kq_mask, kq_scale)` is the ordinary causal/sequence mask; then `kqv = V·kq`.
   - This is the exact one-softmax formulation.
   - It uses generic ops only (rope, mul_mat, mul, add, soft_max, cpy), so it runs on CPU and HIP alike. It ignores `-fa`.

**Wiring (file:line on the branch):**
- `include/llama.h:398` (`dca_chunk_size`, `dca_local_size`, `dca_orig_ctx`);
- `src/llama-cparams.h:29`;
- `src/llama-context.cpp:138-156` (validation, arch allow-list qwen2/qwen35/qwen35moe, MTP-context refusal);
- `common/arg.cpp:2180` (`--dca-chunk-size`, `--dca-local-size`, `--dca-orig-ctx`, env `LLAMA_ARG_DCA_*`);
- `src/llama-graph.h:349-355` (inputs plus `set_input_dca`), `:1169` (builder);
- `src/llama-graph.cpp`:
  - `:490` (input fill);
  - `:1100` (also called by the hybrid memory input, which sets the attention inputs itself; missing this produced NaN on qwen35 in the first test run);
  - `:2832` (input creation);
  - `:2934-3045` (builder);
- `src/models/qwen2.cpp:88`, `qwen35.cpp:323`, `qwen35moe.cpp:347` (opt-in);
- `src/llama-kv-cache.cpp:866` (K-shift refused under DCA), `:1799` (selector fill).
- `llm_graph_input_pos::set_input` now skips an unallocated position tensor. DCA leaves the model's own `inp_pos` unread.

### 2.2 Unified KV cache, multiple sequences, streams

- **Selection is per (query token, cell)** and is computed from each cell's own position and sequence. Unified pools, `-kvu` with many sequences, and per-sequence streams work the same way the KQ mask does.
- **Positions are per sequence.** Chunking is by each sequence's own positions, so two sequences in a unified pool chunk independently.
- **Cells are not required to be in position order.** Nothing assumes contiguity.
- **The K cache is chunk-periodic.** A cell stores `R(p mod c)·k`, which has three consequences:
  - **K-shift is refused under DCA** (`GGML_ABORT`, `llama-kv-cache.cpp:864`). A shift by δ needs `R((p+δ) mod c - p mod c)`, which is not a uniform rotation across chunk boundaries. A DCA-aware shift is possible later: store p, re-rope from scratch.
  - **A slot or cache saved under DCA is only valid under the same `(chunk_size, local_size)`.** The same stale-geometry hazard as YaRN (intake-1347#record): give a DCA instance its own `--slot-save-path` and `--cache-ram`.
  - **Prefix-cache reuse within one DCA instance is exact.** A cell's stored value depends only on its own position.

### 2.3 Hybrid models (Qwen3.5/3.6/3.8 `qwen35`, `qwen35moe`; Flash-Next `qwen4exp`)

- **Only the attention layers change** (every 4th layer: 16 of 64 in the 27B, 10 of 40 in the 35B-A3B). The GDN/linear-attention layers carry no position signal and are untouched. DCA is wired inside `build_layer_attn`, so the recurrent path and the hybrid memory are unchanged.
- **Only the rotated dims are affected.** These models rotate 64 of 256 dims per head (partial rotary). The 192 NoPE dims score identically under all three query variants, so in those dims DCA reduces to plain attention. Only the 64 rotary dims see the remapped geometry.
- **The capacity question YaRN leaves open stays open.** DCA keeps the attention geometry in-distribution. It does nothing for the GDN state's own length generalisation past 262K; only a needle or RULER run settles that.
- **The MTP / nextn layer ropes plainly.** A DCA main context with an MTP draft would verify drafts whose MTP attention sees out-of-distribution positions. v1 refuses an MTP context; a DCA mode should run no-draft (DFlash2 likewise).
- **qwen4exp (Flash-Next) is not wired.** Its QSA sparse attention has an indexer whose pooled block keys are roped at block positions (`qwen4exp.cpp:760`), and its fused decode path is separate. Doing it properly needs:
  1. the indexer keys roped chunk-locally and the indexer query in three variants (top-k selection under DCA);
  2. `build_attn_qsa` given the three-variant scores;
  3. the fused decode taught the same.

  Defer it until Flash-Next's native 262K is validated, as the assessment recommends.

### 2.4 FA kernels: v2 and v3, not yet implemented

v1's non-FA path materialises three [n_kv, n_tps, H] f32 score tensors. That is fine for decode and short prefill, and prohibitive for long prefill (§5). Two routes to FlashAttention:

**v2: FA with LSE output plus a merge** (the vLLM structure).
- Add an `op_params` flag to `GGML_OP_FLASH_ATTN_EXT` that also writes each row's log-sum-exp.
- CPU: `ggml_compute_forward_flash_attn_ext_f16_one_chunk` already holds `M` (running max) and `S` (sum), `ggml/src/ggml-cpu/ops.cpp:9117-9152`. LSE = `M + log(S)` is one extra store. `ggml_flash_attn_ext_reduce_partials` (`:9457`) already merges split-KV partials by (M, S).
- HIP: `flash_attn_combine_results` (`ggml/src/ggml-cuda/fattn-common.cuh:916-966`) and the stream-K fixups (`:723`, `:807`) already carry `meta = (KQ_max, rowsum)`, so emitting LSE is local to them.
- Three FA calls (q_intra/q_succ/q_inter with three −inf masks), then `out = Σ softmax(lse)_v · out_v` in generic ops.
- With KVU-19a's masked-tile skip, the intra and succ calls touch only about 2c of keys, so K bandwidth is close to 1× plus 2c.

**v3: single-pass DCA FA** (the best).
- Pass the three q variants stacked as Q [D, n_q, H, 3] plus a per-(query, key) selector: an I8 tensor, or chunk ids of query and cell.
- Per KV tile, the kernel picks the query row variant by chunk distance. When `c` is a multiple of the KV tile (chunk_len 253952 = 2^13·31 is), the choice is uniform per tile, so the inner loop is unchanged: three Q fragments in registers or LDS, one selected per tile.
- Exact, one pass, K read once, no LSE.
- CPU insertion point: `ggml_compute_forward_flash_attn_ext_f16_one_chunk` (`ops.cpp:8929`), which picks the converted Q row per `ic` from the cell's chunk.
- HIP: `fattn-tile`/`fattn-wmma` Q-load per KV tile.
- Cost: about 3× Q registers and the selector input. This is the recommended production path; v2 is the stepping stone if v3's kernel work is gated.

## 3. Correctness tests (implemented)

1. **`tests/dca_reference.py` (numpy).**
   - Checks:
     - concat formulation vs vLLM LSE-merge formulation agree (|d| < 1e-12);
     - chunk_len > context equals plain RoPE attention;
     - a small chunk differs from plain;
     - max relative position ≤ chunk_size over 200 positions.
   - Synthetic config: T 80, 4 q heads / 2 kv heads (GQA), D 32, chunk 24, local 8, orig 40.
2. **`tests/test-dca.cpp` (ctest, CPU).** Synthetic models from the test-llama-archs fixture.
   - **Numeric (qwen2, NEOX).**
     - Setup: chunk 24, local 8 (c 16) over 96 tokens (6 chunks); prefill 60 in ubatches of 13 that straddle chunks, then 36 single-token decodes. Captures layer 0's unroped q/k/v and the attention output via `cb_eval`.
     - Pass criteria: a float64 reference must match within 1e-5 relative, and a plain-RoPE reference must miss by >1e-2 (the discrimination guard).
     - Runs with and without the temperature (orig 40).
   - **Equivalence (qwen2, qwen35, qwen35moe).** DCA with chunk_len > n_ctx must give logits bit-identical to the non-DCA run (non-FA). This covers the IMROPE and hybrid wiring.
   - **Smoke (same archs).** DCA with chunk 24 gives finite logits that differ from plain.

## 4. Interaction with YaRN

- **Qwen2.5-1M did not combine them.** `rope_scaling` is null; only the `s` temperature, with the formula of YaRN's mscale.
- **DCA makes YaRN's interpolation unnecessary.** No relative position exceeds `chunk_size ≤ trained ctx`.
- **Combining them is mechanically supported but not recommended.** `build_attn_dca` uses the graph's rope parameters, so `--rope-scaling yarn` plus `--dca-*` composes. YaRN would then *compress* the in-distribution positions DCA produces, and the vendor already warns that static YaRN costs short-context quality.
- **The fair A/B for a 524K or 1M mode on the 27B:**
  - arm A: YaRN f2/f4 (vendor-documented);
  - arm B: DCA, chunk 262144, local 8192 or 16384, orig 262144, no YaRN;
  - arm C, optional: DCA plus YaRN, which is what "Qwen2.5-1M combined both" would mean if one reads the temperature as YaRN.
- **The server clamp (`server-context.cpp:1316-1322`) applies to DCA too.** Pass `--override-kv qwen35.context_length=int:<N>`. Since DCA does not use `n_ctx_orig_yarn`, the YaRN-orig trap does not apply.

## 5. Memory and compute

**KV memory** is unchanged by DCA: same cells, same bytes. For the 27B at q8_0 that is 34,816 B/token (16 attention layers), so 1M ≈ 34 GiB of KV, the assessment's figure. **DCA does not make 1M fit one MI210 any better than YaRN.**

**Extra inputs per ubatch:**
- `sel`: 3·n_kv·n_tokens·4 B (f32). At n_kv 1M and ub 512 that is 6 GiB, so v1 needs a small ubatch at long context.
- `dca_pos`: 3·n_tokens·n_pos·4 B.

**v1 non-FA:**

| Item | Size or cost |
|---|---|
| Score tensors | Three [n_kv, n_tps, H] f32 plus their combination. At n_kv 262144, ub 512, H 24: 12 GiB **each**. |
| Prefill, consequence | Long prefill must drop the ubatch to about 32 (0.75 GiB each). |
| Prefill FLOPs | QKᵀ ×3, PV ×1: about 2× plain attention. |
| Decode, per attention layer | Reads K three times plus V once, versus once each: about 2× attention bandwidth. |
| 27B decode at 1M, q8_0 | ≈ 4 × 1.04 GiB × 16 layers ≈ 67 GiB per token of attention traffic, versus ≈ 33 GiB plain. Attention dominates at 1M. |
| V transpose | With `-fa on` the V cache is not transposed, and v1 transposes it per layer per ubatch. Run v1 with `-fa off`. |

**v2:** FLOPs ≈ plain plus 2 small FA calls. K bandwidth ≈ 1× plus 2c per query with tile skip. Memory ≈ plain FA plus 3 output tensors plus LSE.

**v3:** ≈ plain FA. Q registers 3×, one selector read per tile.

**What DCA does not change:**
- the GDN layers (60–75% of layers);
- weight bandwidth;
- the recurrent state.

At 1M on the 27B, decode is dominated by KV traffic (§ assessment §4). v3 keeps DCA at plain-FA cost there; v1 doubles it.

## 6. Plan and status

| Step | Status |
|---|---|
| v1 graph path: qwen2/qwen35/qwen35moe, params, CLI, guards | **done**. CPU tests pass: qwen2 numeric rel err 8.2e-7 / 8.3e-7 (orig 0 / 40) vs the float64 ref and vs numpy LSE merge, plain-rope ref misses by 0.80; equivalence bit-exact on qwen2/qwen35/qwen35moe; smoke differs by 0.11–0.67 of max logit |
| numpy reference plus ctest | **done** |
| GPU validation of v1 (generic ops on HIP) | `gpu_slot_dca.sh`, waiting for the GPU |
| Real-model CPU check: Qwen2.5-0.5B (32K trained), PPL at 64K, plain vs YaRN f2 vs DCA(32768, 4096) | `real_model_ppl_cpu.sh`, region-locked |
| v2: FA LSE output (CPU then HIP) plus merge | planned, insertion points in §2.4 |
| v3: single-pass DCA FA kernel | planned, recommended production path |
| qwen4exp (QSA indexer, fused decode) | deferred |
| DCA-aware K-shift (re-rope from stored positions) | deferred |
| 27B long-context mode A/B (YaRN vs DCA), needle/RULER above 262K | needs a parked-:8083 GPU window and v2/v3 for prefill memory |
