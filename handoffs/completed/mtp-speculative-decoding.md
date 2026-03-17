# MTP-1 Speculative Decoding for Qwen3.5

## Status: CLOSED — NOT VIABLE on hybrid recurrent models. Step 7 confirms 0.56x throughput.

## What Was Done

### Step 0: Architecture Inspection
- MTP layer uses **full attention** (gated Q, 16 heads), NOT Delta Net
- Same MoE: 256 experts, 8 used, identical dimensions to base layers
- Shared `embed_tokens` and `lm_head` (no dedicated MTP embeddings)
- 1 MTP layer = 0.84B params (2.3% of 35.95B total)
- Expert storage: per-expert 2D tensors in HF (fused by converter)
- Model has **40 main layers** (not 28 as in type switch — type falls to UNKNOWN, harmless)

### Step 1: GGUF Conversion (`convert_hf_to_gguf.py`)
- `Qwen3_5MoeTextModel.__init__`: bumps `block_count` by `mtp_num_hidden_layers`
- `set_gguf_parameters`: writes `nextn_predict_layers` to GGUF
- `modify_tensors`: remaps MTP tensors:
  - `mtp.layers.{bid}.*` → `model.layers.{bid + n_main}.*` (layer tensors)
  - `mtp.fc` → `blk.{bid}.nextn.eh_proj` (shared tensors via remapper)
  - Expert merging handled by parent class with corrected `bid`

### Step 2: C++ Model Loading
- `constants.py` + `llama-arch.cpp`: 6 NEXTN tensors added to QWEN35MOE arch
- `llama-model.cpp` hparams: loads `nextn_predict_layers`, marks MTP layers as non-recurrent
- `llama-model.cpp` tensors: loads full attention + MoE + NEXTN tensors for MTP layers
- Type switch uses `n_main_layers` (subtracts MTP) for model size detection

### Step 3: MTP-1 Forward Pass (`qwen35moe.cpp`)
- Main loop iterates `n_main_layers` (excludes MTP)
- Saves initial embedding and last hidden state for MTP
- MTP forward: enorm(embd) + hnorm(hidden) → concat → eh_proj → transformer layer → shared LM head
- MTP attention uses `build_attn_inp_no_cache()` (no KV cache needed)
- MTP logits stored in `res->t_logits_mtp`

### Step 4: Conversion — COMPLETE
- HF checkpoint: `/mnt/raid0/llm/cache/huggingface/models--Qwen--Qwen3.5-35B-A3B/snapshots/ec2d4ece1ffb563322cbee9a48fe0e3fcbce0307`
- All 14 shards downloaded (67GB)
- Converted to Q8_0 (37.8GB, 753 tensors) and Q4_K_M (20.7GB, 4.89 BPW)
- Note: `llama-quantize` cannot requantize from Q8_0; must convert to f16 first, then quantize

### Step 5: Validation — COMPLETE
- Model loads successfully: `nextn_predict_layers = 1`, `block_count = 41`
- Server starts and serves HTTP requests
- Prompt: 69.90 t/s, Generation: 10.95 t/s (Q4_K_M, CPU-only, 192 threads)
- MTP forward pass runs without crash, produces `t_logits_mtp`

### Step 6: Acceptance Rate Measurement — COMPLETE

#### Key Bug: Off-by-one in MTP token alignment

**Root cause found and fixed**: MTP is trained with `embed(token_{n+1}) + hidden_state(n) → predict token_{n+2}`. The initial implementation used `embed(token_n) + hidden_state(n)` (same-step), giving only 5% acceptance.

**Fix**: Cached hidden state approach:
1. After each decode step, cache the pre-norm hidden state to CPU
2. On the NEXT decode step, MTP uses `embed(current_input) + cached_hidden(previous_step)`
3. This correctly provides `embed(token_{n+1}) + hidden_state(n)` since the current input IS the previously sampled token

#### Acceptance Results

| Quantization | N tokens | Exact match | Top-5 match |
|-------------|----------|-------------|-------------|
| Q4_K_M | 64 | 82.8% | 98.4% |
| Q4_K_M | 256 | 78.5% | 97.7% |
| Q8_0 | 256 | pending | pending |

#### Implementation (Step 6 files)

| File | Change |
|------|--------|
| `include/llama.h` | Public API: `llama_get_logits_mtp()`, `llama_get_logits_mtp_ith()` |
| `src/llama-graph.h` | `llm_graph_input_mtp_hidden` class, `t_mtp_hidden_out` field, `build_inp_mtp_hidden()` |
| `src/llama-graph.h` | MTP cache fields in `llm_graph_params` and `llm_graph_context` |
| `src/llama-graph.cpp` | `set_input()` for MTP hidden cache, `build_inp_mtp_hidden()` impl |
| `src/llama-context.h` | `logits_mtp` buffer, `mtp_hidden_cache` vector, `mtp_hidden_valid` flag |
| `src/llama-context.cpp` | MTP logits buffer allocation, extraction, hidden state caching, public API |
| `src/models/qwen35moe.cpp` | MTP uses cached hidden + current inpL, exports `t_mtp_hidden_out` |
| `tools/mtp-acceptance/` | New diagnostic tool for measuring acceptance rate |
| `tools/CMakeLists.txt` | Added mtp-acceptance subdirectory |

### Step 7: MTP Speculation Loop — COMPLETE (NOT VIABLE)

#### Implementation

1. **`llama_decode_mtp()` API**: Standalone MTP-only eval that runs the MTP head without a full model forward pass. Added `LLM_GRAPH_TYPE_MTP_EVAL` graph type, `build_mtp_head()` extracted as reusable method in `qwen35moe.cpp`. Cost: ~10ms (5% of full decode), 100% match with in-graph MTP logits.

2. **Speculation loop** (`tools/mtp-speculation/`): MTP draft → 2-token verification batch → accept/reject. After each target decode, `llama_decode_mtp()` produces a draft token. Next step submits `[main_token, draft_token]` as a batch of 2 for verification.

3. **Bug fix — `llm_graph_result::reset()` stale pointers**: `t_logits_mtp` and `t_mtp_hidden_out` pointers survived graph rebuilds, causing use-after-free crashes. Fixed `reset()` to clear all MTP fields.

4. **Bug fix — in-graph MTP guard**: MTP head crashes on `n_outputs > 1` (2-token verification batches have dimension mismatch with the single cached hidden state). Added guard to skip in-graph MTP when `n_outputs > 1`.

#### Timing Results (Qwen3.5-35B-A3B Q4_K_M, 192 threads)

| Operation | Latency |
|-----------|---------|
| Baseline single-token decode | ~220ms (~4.5 t/s) |
| MTP-only eval (`llama_decode_mtp`) | ~10ms |
| 2-token verification batch | 560-816ms (3-4x single decode) |
| Draft acceptance rate | 70.3% |
| **Net speculation throughput** | **0.56x baseline** |

#### Root Cause: Recurrent Layer Batching

Qwen3.5-35B-A3B has 75% Delta Net recurrent layers. These process tokens **sequentially** regardless of batch size — a 2-token batch costs ~2x per recurrent layer. Combined with attention overhead scaling, 2-token batches cost 3-4x single decode. This is the same fundamental limitation that blocked tree speculation (Approach A, C) and attention-only draft.

#### Files Modified (Step 7)

| File | Change |
|------|--------|
| `src/llama-graph.h` | `gtype` field in `llm_graph_context`, `LLM_GRAPH_TYPE_MTP_EVAL` enum |
| `src/llama-graph.cpp` | `gtype` init, `reset()` clears MTP fields |
| `src/models/qwen35moe.cpp` | Extracted `build_mtp_head()`, MTP_EVAL mode, multi-token guard |
| `src/llama-context.h` | `decode_mtp()` method |
| `src/llama-context.cpp` | `decode_mtp()` implementation, `llama_decode_mtp` C API |
| `include/llama.h` | `llama_decode_mtp()` public API |
| `tools/mtp-speculation/` | New speculation benchmark tool |

### Bugs Fixed During Steps 4-7
1. **NEXTN tensor type**: Was `LLM_TENSOR_LAYER_OUTPUT` (no block id allowed), changed to `LLM_TENSOR_LAYER_REPEATING`
2. **n_mtp_tokens vs n_tokens**: After `inp_out_ids` filtering, MTP tensors have fewer tokens. All reshape/view ops now use `mtp_cur->ne[1]` instead of `n_tokens`
3. **RoPE position mismatch**: `inp_pos` has `n_tokens` entries but MTP Q/K have `n_mtp_tokens`. RoPE now only applied when `n_mtp_tokens == n_tokens` (full prefill). For single-token decode, Q·K^T is scalar so RoPE is identity.
4. **MTP token alignment (Step 6)**: embed(token_n) vs embed(token_{n+1}). Fixed with cached hidden state approach.
5. **Acceptance test off-by-one**: Same-step comparison, not next-step.
6. **`llm_graph_result::reset()` stale MTP pointers (Step 7)**: `t_logits_mtp` and `t_mtp_hidden_out` survived graph rebuilds, causing use-after-free crashes. Fixed by clearing in `reset()`.
7. **In-graph MTP on multi-token batches (Step 7)**: `n_outputs > 1` causes dimension mismatch with single cached hidden state. Added guard to skip MTP head for verification batches.

## GGUF Files

| File | Size | Notes |
|------|------|-------|
| `Qwen3.5-35B-A3B-MTP-Q8_0.gguf` | 37.8 GB | Full precision reference |
| `Qwen3.5-35B-A3B-MTP-Q4_K_M.gguf` | 20.7 GB | Production quantization |

## Files Modified (all in llama.cpp repo)

| File | Change |
|------|--------|
| `gguf-py/gguf/constants.py:1922` | +6 NEXTN tensors to QWEN35MOE |
| `convert_hf_to_gguf.py:4851` | +42 lines: MTP conversion overrides |
| `src/llama-arch.cpp:1078` | +6 NEXTN tensors to QWEN35MOE case |
| `src/llama-arch.cpp:2750` | NEXTN tensors: LLM_TENSOR_LAYER_OUTPUT → LLM_TENSOR_LAYER_REPEATING |
| `src/llama-graph.h` | MTP logits accessor, hidden cache input class, params fields |
| `src/llama-graph.cpp` | MTP hidden cache set_input + build_inp_mtp_hidden |
| `src/llama-model.cpp:2550` | +15 lines: nextn hparams, recurrent fix, type switch |
| `src/llama-model.cpp:7483` | +10 lines: NEXTN tensor loading |
| `src/llama-context.h` | MTP logits buffer, hidden cache fields |
| `src/llama-context.cpp` | MTP logits plumbing, hidden state caching, public API |
| `src/models/qwen35moe.cpp` | MTP forward pass with cached hidden, hidden state export |
| `include/llama.h` | Public API for MTP logits |
| `tools/mtp-acceptance/` | New: diagnostic tool |
| `tools/CMakeLists.txt` | Added mtp-acceptance |

## Conclusion: NOT VIABLE on Hybrid Recurrent Models

MTP-1 speculation is **not viable** on Qwen3.5-35B-A3B due to the same recurrent layer batching limitation that blocked all other speculation approaches (tree speculation Approaches A/C, MoE self-draft, attention-only draft).

**The fundamental problem**: 75% of model layers are Delta Net (recurrent). Recurrent layers process tokens sequentially regardless of batch size. A 2-token verification batch costs 3-4x a single decode (~560-816ms vs ~220ms), destroying any benefit from the 70% draft acceptance rate.

**Where MTP-1 IS viable**: Dense attention-only models (e.g., Llama, Mistral, standard Qwen2.5) where multi-token batches have near-1x cost due to parallel KV processing. The 78.5% acceptance rate and ~5% MTP overhead would yield ~1.7x throughput on such architectures.

**All speculation approaches exhausted for hybrid recurrent models**:
- Tree speculation (Approaches 0, A, C): NOT VIABLE (recurrent state costs)
- MoE self-draft: NOT VIABLE (low acceptance)
- Attention-only draft: NOT VIABLE (incoherent output)
- MTP-1 speculation: NOT VIABLE (verification batch cost)
- Remaining: Approach B (linearized Delta Net) — ~40% viability, approximate, deferred

## Key Design Decisions

1. **Cached hidden state for MTP**: MTP(hidden_n, embed_{n+1}) requires the PREVIOUS step's hidden state. Cache pre-norm hidden to CPU after each decode, feed as graph input on next step. First decode has no cache → MTP skipped.

2. **No KV cache for MTP**: `build_attn_inp_no_cache()`. For single-token generation, attention degenerates to identity-on-V (with gate). For prefill, dense attention.

3. **RoPE skipped for filtered MTP**: Only applied when `n_mtp_tokens == n_tokens` (prefill). For single-token decode (Q·K^T is scalar), RoPE has no effect.

4. **MTP layer marked non-recurrent**: `recurrent_layer_arr[mtp_idx] = false` → loads full-attention tensors (wq/wk/wv/wo) not Delta Net.

5. **Backward compatible**: `nextn_predict_layers` defaults to 0. Existing GGUFs unchanged.

## Risks

| Risk | Severity | Status |
|------|----------|--------|
| MTP attention shape mismatch | HIGH | ✅ Verified: matches base full-attn layers |
| Expert merging for MTP layer | MEDIUM | ✅ Verified: bid correctly remapped |
| n_layer / block_count mismatch | MEDIUM | ✅ Handled: type switch uses n_main_layers |
| NEXTN tensor type (output vs repeating) | MEDIUM | ✅ Fixed: changed to LAYER_REPEATING |
| n_tokens vs n_mtp_tokens after filtering | MEDIUM | ✅ Fixed: use mtp_cur->ne[1] |
| RoPE with filtered positions | MEDIUM | ✅ Fixed: skip when mismatched |
| MTP token alignment (embed offset) | HIGH | ✅ Fixed: cached hidden state approach |
| MTP acceptance too low (<40%) | LOW | ✅ Measured: 78.5% exact, 97.7% top-5 |
| Verification batch cost on hybrid model | HIGH | ❌ Confirmed: 3-4x single decode, 0.56x net |

## Research Intake Update — 2026-03-17

### New Related Research
- **[intake-158] "DFlash: Block Diffusion for Flash Speculative Decoding"** (arxiv:2602.06036)
  - Relevance: Targets the EXACT same model (Qwen3.5-35B-A3B) with a fundamentally different drafting approach — block diffusion instead of MTP heads
  - Key technique: Lightweight block diffusion model drafts multiple tokens in parallel via denoising, conditioned on target model context features
  - Reported results: 2.4-2.8x speedup on B200 GPU (Math500, HumanEval, GSM8K, MBPP); claims 6.1x over AR and 2.5x over EAGLE-3
  - Delta from current approach: DFlash requires SGLang/vLLM (GPU-only, no llama.cpp/GGUF). Our MTP-1 approach works natively in llama.cpp with 78.5% acceptance. DFlash validates that Qwen3.5-35B-A3B cooperates well with speculative decoding — both approaches confirm the model is a good spec-decode target. If GPU serving is added, DFlash becomes an alternative to MTP speculation.

- **[intake-159] "DART: Diffusion-Inspired Speculative Decoding"** (arxiv:2601.19278)
  - Relevance: Another diffusion-based parallel drafter, ~30% faster than EAGLE-3
  - Key technique: Parallel masked position prediction + N-gram-enforced tree pruning
  - Reported results: 2.03x-3.44x wall-clock speedup
  - Delta: No Qwen3.5 weights published; same GPU-only limitation. Less directly relevant than DFlash.
