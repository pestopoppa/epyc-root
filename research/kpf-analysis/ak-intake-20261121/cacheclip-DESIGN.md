# CacheClip-style chunk-KV reuse in EPYC llama.cpp: design spec

Agent `cacheclip-port`, 2026-10-21. Design only: zero compute, no builds, no servers, no edits to any llama.cpp tree.
Source read: champion `ak/champion/llama-cpp-ffc1bac82eec` (read-only `git show`). Inputs: dives `dive-dpfw3-{cacheclip,block-attention}`,
`dive-dpfw4-concat-ft-recompute`, KPF handoff, GGUF headers of the live roles.
Line numbers below are the champion's; they differ from the dives (the dives' `server-context.cpp:1292` is L1313 here, `3323-3386` is L3684-3745).

## 0. Summary

- Build a **chunk-KV store + position-shift injection + selective recompute** inside libllama and llama-server. About 3.5k LOC, 8-10 weeks serial.
  Attention-only models come first. Hybrid Gated-DeltaNet (GDN) models follow in P2.
- **Cheapest hybrid step first (P1a):** LMCache's reorder planner turns a reordered request into an exact prefix hit, valid on recurrent state, ~1-2 weeks, opt-in for order-insensitive segments.
- **Hybrid verdict.** The coordinator's affine hypothesis HOLDS for the layer's *state map*, and it is implementable with the existing
  `ggml_gated_delta_net` op (no new kernel). It does NOT remove the whole hybrid problem, for two reasons:
  1. The cached (A,B) of a deep layer was computed from hidden states encoded in isolation. Those drift with context exactly as attention KV does.
     So it is a CacheClip-class approximation, not an exact identity.
  2. Per-token DN outputs of *recomputed* tokens need the state at that token, which a chunk-level (A,B) does not give.
     That forces the selection to be head-window plus anchor-aligned runs, not arbitrary scattered tokens.
  Net: the hard "recurrent cannot be reused" bound becomes "reuse with a measured quality cost". Estimated prefill saving on reused-chunk
  tokens is about 60-70% on the two target hybrids and about 75-80% on pure attention. Today's saving for hybrids is 0%.
- **Correction to the dives.** At the champion, `llama_memory_hybrid::get_can_shift()` returns `mem_attn->get_can_shift()`, which is **true**
  (`llama-memory-hybrid.cpp:133`; recurrent `get_can_shift` is hard-true at `llama-memory-recurrent.cpp:706`). So `--cache-reuse` is **not**
  force-disabled on hybrids (L1313 only disables when `can_shift` is false). The recurrent `seq_add` (L315) only moves the tail cell's `pos`;
  it does not touch state. The server's `seq_rm(head_p, head_c)` on a recurrent tail inside the range returns false unless within `n_rs_seq` rollback
  (L184-205), and the server ignores the return. Whether that is a live silent-wrongness hazard depends on whether production argv sets
  `--cache-reuse` (`common/arg.cpp:4352` sets 256 for some preset). Check it in P0 (static argv grep plus one correctness run). Do not assert it before.

## 1. Mechanism and mapping to existing code

CacheClip = (a) per-chunk independently-encoded KV, (b) RoPE re-position at the new offset, (c) pick ~20% of tokens whose KV is stale,
(d) recompute only those through all layers while attending to the (stale) cached KV of the rest.

| Piece | Existing in champion | Missing | Size |
|---|---|---|---|
| Chunk store keyed by content hash | `server_prompt_cache` (`--cache-ram`, L1447-1455) stores whole-slot states by exact prefix. `llama_state_seq_get/set_data_ext` (llama.h:931-948, flags incl. ON_DEVICE) | New `server_chunk_store`: key = H(model fingerprint, tokenizer, token ids, kv types, rope params). **No predecessor in the key.** Value = attention K/V per layer (isolated encode, positions 0..n-1) plus DN maps (section 2). Budgeted LRU. Export/import of an arbitrary *position range* into a sequence at an offset: a new libllama API `llama_memory_seq_export_range` / `_inject_range(blob, pos_offset)` | libllama ~500 LOC, server store ~600 |
| RoPE shift on placement | `llama_kv_cache::seq_add` (`llama-kv-cache.cpp:570`) plus the K-shift graph `build_rope_shift` in `update()` (L821-870). Handles MROPE/IMROPE via a NEOX fallback (Qwen3.5 hybrids, L577-583). Already used by `--cache-reuse` (server L3695-3745) | Inject must write the chunk cells at *original* positions, then call `seq_add(Δ)` so the existing K-shift graph rotates them. Only the first `n_rot`=64 of 256 head dims are rotated. Keep the chunk store in f16/bf16: shifting a quantized K cache re-quantizes and accumulates error | ~150 LOC plus tests |
| Token selection | None | `chunk_selector`: (i) head window (first W=64 tokens, which also covers the 3-token conv boundary and attention-sink artefacts), (ii) CacheClip's auxiliary-model scoring (0.135-0.5B model, last-layer query-to-key attention; the registry already carries `draft_qwen25` 0.5B, so no new model), (iii) group-contiguous runs (CacheBlend degrades with scattered selection; grouping fixed it, RULER 40.5 to 81.3) | ~300 LOC plus a second tiny `llama_context` on CPU |
| Sparse recompute | A batch with explicit per-token `pos` is already legal. Emulation: `seq_rm` the selected positions, decode only those tokens with their real positions; causal masking is by pos so they attend the stale shifted cells of the unselected. The paper's Triton sparse-query FA kernel is only an optimisation. Appendix C of 2609.09768 says tuned FA2 full attention matches 15% recompute on their setup | Ordering (selected must be decoded in position order), cell hygiene (no duplicate pos), and the per-layer "fresh K/V overwrites stale" semantic, which holds naturally because the selected tokens' own K/V are written by their decode | ~300 LOC in `server-context.cpp` (new branch beside the L3684 cache-reuse block) |
| Slot assembly | `launch_slot_with_task`, LCP, `--cache-reuse` (same-slot only), KPF `find_fork_source` and attention-only share (KPF-11/12/13, done 2026-10-04) | Assemble `[chunk_1 ... chunk_k, suffix]` into a slot's sequence; see section 4 | in §4 |

Total about 3.5k LOC including tests; two cheap decisions (store format, selector) are reversible.

## 2. Hybrid and recurrent models (the hard part)

### 2.1 Live layer mix (from GGUF headers; `full_attention_interval=4`)

| Role (registry) | Arch | main layers | attention | GDN | KV heads x dim | GDN heads (H_v) x S_v | conv ch | notes |
|---|---|---|---|---|---|---|---|---|
| coder_escalation / ingest_long_context / architect_critic (Qwen3.8-27B Q8_0, **GPU champion**) | qwen35 | 64 (65 blocks incl. 1 NextN/MTP) | 16 | **48** (3:1) | 4 x 256 | 48 x 128 | 10240 | tensors confirm: 17 blocks with `attn_k`, 48 with `ssm_a` |
| frontdoor / worker_general / math / summarize / toolrunner (Qwen3.6-35B-A3B-MTP Q8_0) | qwen35moe | 40 (41 incl. NextN) | 10 | **30** | 2 x 256 | 32 x 128 | 8192 | MoE, ~3B active |
| architect_general (Qwen3.8-Flash-Next UD-IQ4_XS) | qwen4exp | 48 (metadata only: shard 1 has no tensors) | 12 | 36 | 2 x 256 | 48 x 128 | n/a | also carries an attention *indexer* (4 heads x 128): sparse-attention keys must be cached too. Unverified until P4 |
| worker_vision / vision_escalation (Qwen3-VL-30B-A3B) | qwen3vlmoe | 48 | 48 | 0 | n/a | n/a | n/a | pure attention, the clean CacheClip target |

Conv1d kernel is 4, so the conv state is the previous 3 columns of the (q,k,v) conv channels. It is small, but it is a 3-token dependence on the predecessor.

### 2.2 The affine hypothesis, checked against `delta-net-base.cpp` and `ggml_gated_delta_net`

- The op takes `g` as a **scalar gate per head per token** (`[1,H_v,n_tokens]`; the KDA vector-gate variant is also affine), `beta` scalar,
  state `[S_v,S_v,H_v]` (128x128 per head), and the chunking path uses CS=64 blocks and the WY identity (`delta-net-base.cpp:61-285`). Its update is
  `S_t = S_{t-1}·α_t(I − β_t k_t k_tᵀ) + β_t v_t k_tᵀ`. **Affine in S: `S_out = S_in·A + B`**, with
  `A = (∏α)·∏(I − β_i k_i k_iᵀ) = γ(I − W Kᵀ)` (rank <= n correction) and `B` = final state from a **zero** start. Confirmed.
- **No new kernel is needed to produce them.** `B` = the state after an isolated encode (it is already the recurrent cell). `A = S_out(S_in=I) − B`:
  run the existing op a second time on the same q/k/v/g/β with the identity as initial state. That is a side-graph on the encode path only
  (one extra DN-op per layer, one-time per chunk). The op takes an arbitrary initial state, so this works for both the fused and chunked paths.
- **Composition is exact given the same layer inputs:** `S_end = S_pred·A_chunk + B_chunk`. Cost: 2·128³ FLOP per head-layer. 27B: 2304 head-layers
  (48x48) is **9.7 GFLOP per placement**; 35B-A3B: 960 head-layers is 4 GFLOP. That is <1 ms on MI210 and <~10 ms on CPU, against tens of GFLOP **per token** of prefill.
- **Catches that bound the claim:**
  1. *Layer inputs drift.* `q,k,v,g,β` at layer l>0 are functions of the hidden state, which depends on context through the attention layers and
     through earlier GDN outputs `o_t = S_t q_t`. Only layer 0 (inputs = embeddings, up to the 3-token conv boundary) is exact. Deeper layers' (A,B) are the same
     class of approximation as CacheClip's stale KV. It is a quality question, answered by the gate in §5, not a proof.
  2. *The gate is input dependent* (`g = ssm_a·softplus(ssm_alpha·x + dt_bias)`), so a chunk's `γ` is data dependent.
  3. *Per-token outputs* `o_t = S_in·(A_{1:t} q_t) + B_{1:t} q_t`. Storing `A_{1:t} q_t` per token costs ~0.6-1.2 MB/token (larger than the whole attention KV), so the chunk-level map alone
     cannot serve the DN output of an arbitrary recomputed token. That token needs `S_t`.
  4. *Decay prunes A for many heads.* Prior from the GGUF (`ssm_a`, `dt_bias`, x=0; the real g is input dependent, so this is indicative only): the median decay horizon τ is ~15 tokens
     (35B-A3B) and ~37 tokens (27B), but the 95th percentile is ~1.1k / ~2.1k tokens. Fraction of heads whose chunk decay stays above 1e-3: over 256 tokens 37% (35B) / 50% (27B), over 1024 tokens 21% / 35%.
     So `A` can be dropped (treated as 0) per head-layer when `‖A‖_F < ε`, and long (>1k) chunks keep it for only ~20-35% of heads. Measure in P0.
- **Storage per chunk (f16; per-chunk, independent of length):**

  | Role | head-layers | B (all) | A (kept ~35% @1k) | attn KV / token (f16) | total @1k-token chunk | total @4k |
  |---|---|---|---|---|---|---|
  | 27B | 2304 | 75.5 MB | ~26 MB | 65.5 KB | ~167 MB (167 KB/tok) | ~364 MB (91 KB/tok) |
  | 35B-A3B | 960 | 31.5 MB | ~7 MB (20%) | 20.5 KB | ~59 MB | ~121 MB |
  | Flash-Next (est.) | 1728 | 56.6 MB | ~20 MB | 24.6 KB | ~101 MB (+indexer) | ~160 MB |

  Low-rank/WY storage `(W,K)` is 2·n·128 values per head vs 128² for dense A: it wins only for chunks <64 tokens, and chunks that short are not worth reusing
  (head window W=64 is already 100% of them). So **dense A plus pruning**, not WY factoring. If f16 `B` hurts, store f32 (2x). Anchors (below) multiply `B` by chunk_len/256.
- **Anchors.** To give recomputed tokens a state, encode each chunk in 256-token ubatches (the cell state is readable between ubatches) and keep the zero-start
  `B_j` (and the pruned `A_j`) at every 256-token boundary. A recomputed run that starts at an anchor takes
  `S = S_in_chunk·A_{1:p} + B_{1:p}` composed from these, exact given inputs. Cost: B per 256 tokens (27B f16: ~19 MB per 256 tokens, i.e. ~330 KB/token with A, which is the storage ceiling). Use only if the P2 gate needs
  runs past the head window; otherwise the plain per-chunk (A,B) suffices.
- **Constraint on selection (the real consequence of the hybrid structure):** a token recomputed through *all* layers needs a DN state at its position.
  So the selected set per chunk is **(1) the head window [0,W), recomputed from the true incoming state (chunk-end `S_pred` plus the actual conv columns), plus (2) 64-block-aligned runs that start at an anchor**.
  Scattered single tokens are not allowed on hybrid layers. Expect to need a somewhat larger recompute budget than attention-only (see savings, r≈0.30 vs 0.22).

### 2.3 Options and estimated prefill saving

Saving = reduction in prefill FLOPs on the *reused-chunk tokens*; request-level saving = ρ x this (ρ from B7). Common model: per-token cost is ~uniform across layers (1/L per layer),
r = recomputed fraction. Compose cost <0.2%, aux-model selection ~0.2 s CPU (overlappable with load).

| Option | How | Exact? | 27B (16A/48D) | 35B-A3B (10A/30D) | Qwen3-VL (pure attn) |
|---|---|---|---|---|---|
| O1 Recompute everything but attention layers' reused KV | Cannot skip a token in DN layers without its layer input. Skipping layers 0..l-1 for a token is not possible, so every token passes all earlier layers | yes | **~0%** (no token can be skipped) | ~0% | n/a |
| O2 Per-chunk recurrent snapshot valid only for the original predecessor | Snapshot = KPF checkpoint | yes | 0% for reordering or new predecessor. 100% only when predecessor is identical, which is plain prefix cache (already KPF) | same | n/a |
| O3 **Affine (A,B) composition plus selective recompute (recommended)** | §2.2. Attention layers: CacheClip. GDN layers: composed state plus head-window/anchor-run recompute | approximate (drift), measured by gate | **~65-70%** (r≈0.30) | **~60-70%** (r≈0.30-0.35) | **~75-80%** (r≈0.20-0.22 plus selector) |
| O4 Cache per-layer hidden states, recompute only the GDN layers | Store h^l per token (27B: 5120x2Bx64 ≈ 650 KB/token) | yes-ish | ≤ ~25% (DN layers are ~75% of FLOPs and must run on all tokens) | ≤ ~25% | n/a |
| O5 Restrict reuse to attention-only models | Qwen3-VL-30B-A3B only (worker_vision, vision_escalation) | approx | n/a | n/a | ~75-80% |

Caveats: these are FLOP-model estimates, not measurements. For MoE (35B-A3B) a 300-token recompute batch still touches most experts, so expert-read amortisation shrinks and the realised saving sits at the low end.
The 27B and 35B numbers are the target numbers P2 must confirm or kill. Flash-Next is unverified (no tensor read; indexer cost unknown).

### 2.4 Payoff against OUR tuned prefill, including load (answering 2609.09768)

The paper's TTFT win disappears against FA2 once SSD load is counted, and at 4k loading is slower than prefill. That comparison used H200-class prefill (~10k+ tok/s). Ours is far slower:

- 27B on MI210: pp512 ≈ **727 tok/s** (v9 era row in handoffs; ≈1.4 ms/token). Chunk load from RAM over PCIe (~20 GB/s): 167 KB/token ≈ **8 µs/token** (0.6% of prefill). From NVMe (~3 GB/s): ≈56 µs/token (4%), still a win. Fixed per-request cost (aux model 0.24 s CPU, overlapped, compose ≈1 ms, launch) ≈ 0.1-0.25 s.
- 35B-A3B on CPU: prefill rate **not measured here** (repo notes say 200-500 tok/s class for CPU prefill; assume ~5 ms/token). Load is a RAM memcpy (≥20 GB/s): ≈3 µs/token for attention KV plus tens of ms fixed for the DN maps.
- **Crossover (reused tokens needed in a request for net win), saving ≈ 0.65 x t_prefill/token x n vs fixed cost:** 27B GPU **≈ 150-300 tokens**; 35B CPU **≈ 50-150 tokens**. Per-chunk minimum worth reusing: **≥ 256 tokens** (head window W=64 is otherwise ≥25% of the chunk). From NVMe, the 27B crossover rises to ~300-400 tokens. P0 must measure real pp rates per role and the real inject/compose latency, then freeze these crossovers; they are estimates.
- Memory is the real constraint, not speed: host RAM 1133 GB with ~708 GB page cache. A 64-128 GB store holds ~400-750 chunks of 1k tokens (27B) or ~1-2k chunks (35B). That is far below the >200-chunks-per-request quality cliff, so the cliff, not the store, bounds request shape.

### 2.5 Refinements from the vLLM/SGLang/LMCache survey (`kv-reuse-survey-20261021/REPORT.md`)

The survey confirms nobody composes recurrent state across reordered chunks (LMCache refuses blend on GDN, `recipes/qwen3_5.rst:123`; vLLM/SGLang snapshots are prefix-only). The affine map is unclaimed, so it is our own research risk. Folded in:

1. **Cost A: "A is larger than a snapshot".** For our models `d_k = d_v = 128`, so a dense A is the same size as B and (A,B) is **2x** a snapshot, not an order more (the survey's d_k·d_k + d_k·d_v is 2·16384 per head). Three levers, all gated by G2/G3:
   - *A-mode tiers per head-layer per chunk:* `none` (A≈0 when `‖A‖_F<ε`, typical for fast-decay heads), `scalar` (A≈γ·I, drops the projection term), `dense`. The tier is chosen at encode from measured `‖A‖` and recorded; the compose op branches on it.
   - *SGLang-style int8 per-(head, k-channel) scaling* of cached A and B (`mamba_checkpoint_pool.py`), rounded once on store, never re-entering recurrence: ~2x smaller than f16, ~4x smaller than f32. With pruning, 27B @1k chunk is ~35 MB (B int8) + ~13 MB (A) ≈ 50 MB of DN maps instead of ~100 MB f16 (plus the 65 MB attention KV).
   - *WY factoring* is only worthwhile for chunks <64 tokens, which are not reused anyway. Rejected.
2. **Cost B: conv1d breaks affinity at chunk edges.** The depthwise causal conv (kernel 4) is linear, but the following SiLU is not, so the first 3 tokens of a chunk produce different q/k/v when the predecessor differs. Fix by construction: **the cached (A,B) cover tokens `[W,n)` only**, where `W` is the head window (`W ≥ 3` is mandatory; the default `W = 64` also handles sink artefacts and fast-decay heads). Tokens `[0,W)` are always recomputed with the true incoming state and true conv columns, then `S ← S·A + B` composes the rest. The encode keeps the chunk's last 3 pre-conv columns (they are the conv cell) so the *next* chunk's head window has them. Then no affine-breaking token enters a cached map. Store also `S_iso(W)`, the isolated state after the window, for the deviation signal below.
3. **Cost C: no K-deviation signal for recurrent layers.** Three signals, usable together (selector interface in P1, DN versions in P2):
   - *(S-A) Aux-model scoring* (CacheClip's own selector; layer-agnostic, one small CPU model). It is independent of the main model's layer types and works on hybrids unchanged.
   - *(S-B) CacheBlend/LMCache check-layer K deviation, extended to GDN.* GDN layers have `k_t` too (q,k are projections of the layer input). Run every chunk token through layers `0..ℓc` (in the hybrids, layers 0-2 are GDN and layer 3 is the first attention layer), score `‖k_fresh − k_cached‖²` per token at the layers, keep top-`ratio·N` (LMCache `blender.py` ~L86-105), aggregate per 64-block for runs. Cost: `(ℓc+1)/L` of a full prefill on all chunk tokens: 27B 4/64 = 6%, 35B-A3B 4/40 = 10%. It is exact on layer 0 (deviation only at the conv edge), which doubles as a sanity probe. The GDN layers in the check prefix are the one place we pay a sequential pass.
   - *(S-C) State-deviation budget.* From the head window we already recompute, `Δ_l = ‖S_W^true − S_iso(W)‖_F / ‖S_iso(W)‖_F` per head-layer. This is a per-chunk drift measure (not per-token): small Δ across layers lowers `r` for that chunk, large Δ raises it (adaptive recompute budget). An *output deviation at a check token* is the same signal in o-space: `‖o_t^true − o_t^iso‖` at the last window token.
   Quality is judged only by G3; the signals only allocate budget. Replace S-B with S-A when check-layer cost exceeds the gain (short chunks).
4. **Position-free keys and a fingerprint index** (LMCache `token_database.py:452-560`, `blend_index.py`, `matcher.py`): chunk key = content hash alone (no parent); keep a separate chained hash for prefix/KPF. `kv_chunks_mode:"auto"` finds cached chunks at any offset by a rolling polynomial hash over token windows, verified token-exact (P3).
5. **K-only RoPE re-rotation with a self-check** (`positional_encoding.py:52-150`): V is position-free and untouched; llama.cpp already rotates K via K-shift. Add the startup self-test (rotate +Δ then −Δ, require NMSE ≤ 1e-6 for the actual rope type incl. IMROPE dim sections and partial `n_rot`=64) as part of G1. Skip the shift when Δ=0.
6. **SGLang hybrid discipline for the chunk store:** a *grid* (anchor spacing 256 tokens, a multiple of the kernel's 64-block, mirrors SGLang's lcm grid); *tombstone on evict* in this order: anchors first (selection falls back to head-window only), then A (falls back to `scalar`/`none`), then B+KV (chunk gone); *copy-on-write on hit* (the injected state is a private copy; KPF-13 already does this for checkpoints); int8 snapshots per item 1.
7. **Reorder planner (LMCache `blend/reorder.py`) as the cheap hybrid route, Phase P1a.** It rebuilds a *cached prompt's exact prefix* out of pieces of the incoming prompt (min run LMIN=16, glue 3, last LMIN tokens pinned last). The reordered request is then a **plain prefix hit**, exact, no blending, and valid for recurrent state because the state is the true state for that history.
   - *Evaluation.* Saving on the reordered portion is **100% of the matched prefix**, exact (bit-identical to full recompute **of the reordered prompt**), on every role including 27B and 35B-A3B. Limits: (a) it changes the prompt, so it is valid only for order-insensitive segments (retrieved docs; opt-in `kv_chunks_reorder:true`, never default); (b) it needs a cached prompt whose chunk boundaries have KPF `checkpoint_at` junction checkpoints (KPF-15) so a hybrid prefix can be resumed at a chunk end; (c) the match is a single chain: a request whose chunk *set* differs from the cached chain gets only the prefix up to the first missing chunk, so the realised share depends on how popular chunks are placed first; (d) the quality reference changes: exactness is vs full recompute of the reordered prompt, and a separate task A/B measures reordering itself (lost-in-the-middle sensitivity).
   - *Size:* S-M, ~1-2 weeks (planner ~300 LOC ported from `reorder.py` semantics, KPF find_fork_source integration, tests). It needs no libllama change, no RoPE shift, no store. It also gives the cheapest early read of B7's value on hybrids.
   - It does not replace O3: it only helps when a cached prompt exists whose chunk chain covers the new set. O3 covers arbitrary subsets/orders.

## 3. SWA models

No live role has sliding-window layers (Qwen3.x full attention; Flash-Next uses an indexer, not SWA). Required for Gemma-class workers and for future lineups:

- `llama_kv_cache_iswa` keeps the SWA cache with only the last `n_swa` positions per layer. The chunk-encode context must run with **`swa_full=true`** (server already has the knob, L1325-1332) so the chunk's whole range is resident when exported; `LLAMA_STATE_SEQ_FLAGS_SWA_ONLY` (llama.h:920) lets the SWA half be exported/injected separately.
- RoPE shift applies to both halves (`seq_add` is implemented for the base cache; confirm the iswa wrapper forwards to both, a P4 unit test).
- SWA gives a free structural guarantee: a token deeper than `n_swa` into a chunk has an SWA-layer *window* entirely inside the chunk, so the **head window W := max(64, n_swa)** is exactly the set of tokens whose SWA attention sees the predecessor. Only these need recompute for correctness in SWA layers; global layers still drift and use the selector.
- Consumer side: after injection the next suffix's window reaches back into the chunk tail, which is present. If the target slot is itself SWA-pruned (`swa_full=false`), injection of a chunk with length > `n_swa` only needs the last `n_swa` positions in the SWA half. Truncate on inject to save memory.
- Hybrid + SWA (`llama_memory_hybrid_iswa`) composes the two rules above.

## 4. Server integration

**API.** New request field alongside `checkpoint_at` (KPF-15):
`"kv_chunks": [{"offset": <token pos in prompt>, "n_tokens": N, "key": "<optional client hash>", "pin": false}]`.
Server verifies `key` (or computes it from the token ids) and ignores unknown or mismatched chunks (fail-safe to normal prefill). Segments not listed are the suffix. Optional `"kv_chunks_mode": "auto"` makes the server hash fixed block boundaries; default off. The orchestrator (B7 candidate: `build_corpus_context`, `chunk_id`+`content_hash` in `kb_rag.py`) maps `content_hash` to chunk boundaries. Response `timings`: `n_chunk_hit`, `n_chunk_recomputed`, `chunk_store_hit_bytes`, `chunk_gate_failed`.

**Flow in `launch_slot_with_task`** (new branch, before the L3684 cache-reuse block, mutually exclusive with it):
1. KPF `find_fork_source` and LCP give the true common prefix; chunks must start at or after `n_past`.
2. For each declared chunk: store lookup; a miss encodes it in isolation (a prefill at pos 0 in a scratch sequence with `swa_full`, ubatches of 256 for anchors, DN (A,B) side graph) and inserts it. A miss is a normal prefill cost plus one-time encode; the encode may run as a prefill-only request (`max_tokens:0`, mirrors KPF-21 trunk-first).
3. Inject: write cells at original positions (copy; **never share cells across sequences with different Δ**, because a shifted K differs per placement. KPF's zero-copy share applies only to identical-offset trunks), `seq_add(Δ)`, then compose DN state chunk by chunk in order (state advance `S ← S·A + B`; conv columns fixed by the head-window recompute).
4. Recompute selected tokens (head windows plus runs) in position order as ordinary batches (`pre_decode` already supports `checkpoint_at`-style boundary cutting), then prefill the suffix.
5. Record the checkpoint as normal. A slot built from reused chunks is **marked approximate** (`prompt.tokens` stays correct, but `prompt.approx=true`): it must not be used as a KPF fork source or `--cache-ram` entry for exact-prefix reuse unless the request opts in (otherwise an approximate state would silently seed exact prefixes).

**Eviction.** Cost-aware LRU, budget `--chunk-store-mib` (separate from `--cache-ram`; `0` = feature off = champion behaviour). Score = hits x tokens saved / bytes. Pinned entries via `"pin":true` (RAG corpora, tool schemas). Optional disk spill reusing the slot save-file format (only worth it if NVMe load meets the §2.4 crossover). Keys include the model fingerprint so a stack reload cannot serve a stale blob; the fingerprint must include the mtime/sha of the GGUF and the kernel version (CLAUDE.md stale-artifact rule).

**Interactions.** Prompt cache and checkpoints are unchanged when no `kv_chunks` field is sent. KPF fork: chunk assembly is orthogonal; a chunked prompt that also has a plain shared prefix forks the prefix first (KPF-12/13), then injects chunks after it. Speculative/MTP drafter contexts (`ctx_dft`, the L3700 `seq_add` pair) need the same inject on their own KV; DFlash/MTP drafters for the 27B ("27B ALWAYS DFlash2") must be covered or the drafter sees the wrong history. Multimodal (`mtmd`) chunks are excluded in v1.

## 5. Correctness gate (predeclared; frozen in P0 before any data is looked at)

Reference = full recompute of the identical token sequence on the same binary and argv. Never compare to a different build.

1. **Plumbing exactness (G0).** `r = 100%` (everything recomputed, store bypassed) is bit-identical to the champion path, and with `--chunk-store-mib 0` or no `kv_chunks` field the outputs are bit-identical to the champion tip on the KPF-18 corpus. Any difference stops the phase.
2. **Shift exactness (G1, attention-only).** A chunk encoded at offset 0, injected at Δ with no recompute, versus encoded in place at Δ with the same isolated context (single chunk, no predecessor), has K/V NMSE ≤ 1e-6 (f32 K) and logits NMSE ≤ 1e-5. This isolates the RoPE-shift plumbing from the approximation.
3. **Composition exactness (G2, hybrid).** Layer 0 DN: `S_pred·A + B` equals the sequentially computed state with NMSE ≤ 1e-6 (f32 A,B) given identical inputs; f16 A,B storage ≤ 1e-3.
4. **Approximation gate (G3, the CacheClip-class loss).** On a frozen mix of ≥ 200 requests with 2-16 chunks at ≥ 2 different offsets/predecessors each, lengths 1k-32k, per target role:
   - mean per-position KL(full ‖ reuse) at all continuation positions ≤ **0.05 nats**, p95 ≤ **0.25**;
   - top-1 agreement ≥ **0.95**; logits NMSE median ≤ 0.02, p95 ≤ 0.10;
   - downstream task retention ≥ **0.95 of full recompute** on the actual B7-derived tasks. CacheClip's own published retention is 85-91% of full attention at 20% recompute, so 0.95 is a deliberately higher bar for a production flag; if a role only reaches 0.85-0.95 it ships as **opt-in per request**, never default;
   - must beat the naive baseline (shift with r=0) on KL by ≥ 5x, or the selector is not earning its keep.
   All thresholds are a pre-registration: P0 commits them to git with the corpus manifest before P1 produces any number; any change after is a recorded amendment.
5. **Native-window rule (YaRN-style hard gate).** Everything above is run at every length inside the native window (up to 262144 tokens, YaRN/extension off). No regression is allowed there: when the feature is enabled but a request carries no chunk or the store misses, the output equals the non-chunk path bit-for-bit (G0), and G3 must hold at the short end (1k-4k) as well as at the long end. A length bucket that fails excludes that bucket from the feature (a min-prompt-tokens floor), not the whole feature.
6. **Hybrid-specific tripwires.** Per-layer relative error of composed vs sequential state at every GDN layer, reported as a curve over depth (expected to rise with depth; the curve decides the selector's recompute depth). Conv-boundary check: first 3 tokens of every chunk are in the head window.
   **Amendment 2026-11-21 (KPF-62-DRIFT-PRIORS; adds arms, a sweep, a prior and a localiser to the item 6 drift-curve gate; no threshold in section 4 changes).** Scoring is the section 4 scoring unchanged: per-position KL(full || reuse) at the G3 continuation positions (mean and p95, nats), top-1 agreement, logits NMSE, on the same frozen corpus and roles; the per-layer curve in item 6 stays reported-not-gated. Gate class: futility-only at interim looks.
   - **(a) Arms.** The hybrid drift-curve gate compares three state arms on 27B and 35B-A3B, all with the same selector and r: (i) *affine (A,B)* (O3, the recommended arm: `S_end = S_pred*A + B` over `[W,n)` plus head-window recompute), (ii) *naive* (shift/addition with r=0, no state repair; the section 4 baseline), and (iii) NEW *single-source* (one cached state only: the last chunk's end-state `B_last` injected as the state of the new position, no transition matrix, no A; LinearKV's one-state shortcut, intake-2773#record). The single-source arm is the cheapest hybrid design (about half the DN bytes of (A,B)); it is kept only if it is within the section 4 gates, otherwise it is the recorded lower bound. Ranking rule: report all three on KL and top-1; (A,B) must beat single-source by a margin that pays for its 2x state, else drop A (fallback ladder P2 (b)).
   - **(b) Head-window sweep.** w in {4, 8, 16, 32, 64} against the W=64 default (W >= 3 is mandatory, so w=4 is the smallest legal value; the SWA rule W := max(64, n_swa) applies when SWA layers are present, and the sweep then reports w only below that floor on non-SWA roles). Each w is scored on KL and top-1 under arms (i) and (iii), with r held fixed so only w varies, and the recomputed-token cost (k-1)*w per request is reported next to it. HyPIC's own sweep (4-128, best w=8, w=128 costs +11.4% TTFT, task-score scale, intake-2774#record) is the comparison, not a substitute for our KLD scoring.
   - **(c) Expected magnitude (prior, not a gate).** HyPIC reports exact composition at layer 0 (rel L2 1.55e-15, FP64) and 8.92% relative L2 / 5.11 degrees mean drift at depth on Qwen3.5-35B-A3B (Table 4; full-attention layers disabled for the probe), intake-2774#record. LinearKV reports 14-25% task-score loss at 20% recompute for composition-style PIC on Qwen3.6-27B (Mamba-2 models collapse harder), intake-2773#record. The repo dive gives no layer-by-layer numbers: only the two scalar figures above exist, there is no depth curve in the dives, and Qwen3.6/3.8 were not tested by HyPIC (intake-2783#record). Therefore: a measured composed-vs-sequential relative error far below about 9% at the same depth on our models would be better than the published prior; far above it falls outside it and triggers the fallback ladder. Do not read the prior as a threshold.
   - **(d) First-divergent-layer localisation.** Modelled on HyPIC `examples/pic/diag_layer_divergence.py` (pinned SHA 98147c01909004e66d98bcb18b886927d41b0ee5; it dumps one record per decoder layer for baseline and PIC runs, then flags the first layer where relative norm error > 1e-4 or cosine of the head slice < 0.999, intake-2783#record). Our version runs on the `ggml_gated_delta_net` path with the llama.cpp eval callback (the `cb_eval` hook in `examples/eval-callback`, `ask`/`get` two-phase). For each (model, chunk, predecessor) pair: Run A = baseline, the full sequence decoded in one pass; Run B = the arm under test (composed-state injection, or single-source, at the same positions, same binary, same argv, same device). For every decoder layer, hook the layer-output residual (the `l_out-<il>` tensor, the same per-layer name set in `src/models/qwen35.cpp` and `qwen35moe.cpp`) and the GDN state tensors; copy through `ggml_backend_tensor_get` into f32; write one JSONL record per layer: `{layer, kind: gdn|attn, norm, head8, rel_fro_vs_baseline, cos_vs_baseline}` at the last prompt token and over the seam-window tokens, plus the composed-vs-sequential state relative error for GDN layers. The reported localisation is the FIRST layer where rel_fro > 1e-4 or cos < 0.999 (HyPIC's thresholds), run once per arm and once per w, plus the whole per-layer curve. The first-divergent layer separates seam/conv-boundary defects (layer 0 or the first GDN layer: a bug, the conv-boundary check of item 6 applies) from depth drift (monotone rise: expected) and from attention-layer cross-segment error (jump at the first attention layer). Controls: A vs A rerun bit-identical; arm at r=100% reproduces A (G0). Instrument is CPU-only correctness, no timing window; it reuses the P0 `chunk-drift` hook plan (`p0_timing_plan.md` section 4) and ships as the drift-gate's localiser.
   - **(e) Dependency.** KPF-62-P3-SKELETON (kv-cache-program.md) must reference this amendment: the skeleton's hybrid affine-state phase decision is taken from these three arms, the w sweep and the localiser.
7. **Timing** (separate from correctness): alternating windows, same binary, `--chunk-store-mib 0` as the control, GPU residency proven by `verify_ggml_linkage.sh` plus VRAM sampled during the run, per the host rules. Report TTFT including store load, against the tuned prefill, with crossover length per role.

## 6. Phased build plan (workflow per CLAUDE.md)

Branches `experimental/chunk-kv-reuse-<phase>` in worktrees under `/mnt/raid0/llm/worktrees/`, cut from the champion tip **resolved live**
(currently `ffc1bac82`, v10). Production is frozen. Nothing merges to production; the work folds into the champion only and ships in the next big production bundle (release manifest kept). The candidate is the FULL build (fresh champion plus all features) validated as a whole; no cherry-picks at promotion. Each phase rebases onto the then-current champion tip before its gate. Correctness work needs no quiet host (shard and build-role claims); only timing needs a window; CPU builds/tests under `region-lock run --cpu-list 0-95`; no GPU overlap.

| Phase | Content | Size | Gate to exit |
|---|---|---|---|
| **P0 Setup and measurement** | Worktree, GitNexus index of it (`scripts/gitnexus-analyze.sh <worktree>`; `llama_state_seq_set_data_ext` and the `update_slots` area are HIGH impact so proceed methodically); freeze gate thresholds and corpus manifest; static check of production `--cache-reuse` on hybrids (§0); measure pp rate per role, load/inject latency, DN decay statistics and (A,B) norms from a real run; layer-input drift study (isolated vs in-context q/k/v/g/β per layer) on 27B and 35B | S, 4-6 days (plus one timing window) | thresholds committed; drift curve and crossover table in the handoff |
| **P1a Reorder planner (hybrid-safe, exact)** | Port the `reorder.py` planner into server; opt-in `kv_chunks_reorder`; rely on KPF fork plus `checkpoint_at` junctions; telemetry for matched-prefix share | S-M, 1-2 weeks | reordered request bit-identical to full recompute of the reordered prompt on 27B and 35B (G0-style); permutation task A/B; reports B7's extra metric (prefix-reconstructible share) |
| **P1 Attention-only core** | `server_chunk_store`, libllama export/inject-range, RoPE shift on inject, selector v1 (head window plus S-A aux-model scoring and S-B check-layer K deviation, group-contiguous runs), position-free chunk key plus chained key, K-shift self-check, sparse recompute by explicit-pos batches; test model Qwen3-VL-30B-A3B text path plus a small attention-only model for CI | M-L, 2-3 weeks | G0, G1, G3 on pure attention; speed vs tuned prefill |
| **P2 Hybrid GDN** | (A,B) side-graph encode over tokens `[W,n)`, A-mode tiers and int8 per-(head,k-channel) storage, 256-token anchors with tombstone order, compose op (CPU path plus ROCm graph), conv-edge handling via head window, selectors S-B (check-layer K deviation extended to GDN) and S-C (state-deviation budget), hybrid selector constraint (head window plus anchor-aligned runs), `ctx_dft`/MTP/DFlash2 coverage | L, 3-4 weeks, **research risk** | G2, G3 on 27B and 35B-A3B. Fallback ladder if G3 fails: (a) larger r or f32 maps, (b) head-window-only selection, (c) hybrids opt-out and the feature ships attention-only (O5) with the finding recorded |
| **P3 Server productisation** | `kv_chunks` API, eviction/pin, telemetry, `/props` flag, approximate-slot marking, KPF coexistence tests, pytest, orchestrator hook (B7 consumer) | M, 1-2 weeks | G0 under KPF-18-style corpus; off = champion bit-identical |
| **P4 SWA, indexer, VL** | iswa export/inject, Flash-Next indexer cache, mtmd exclusion rule | S-M, 1-2 weeks | G1/G3 per role |
| **P5 Fold** | Fold into the CHAMPIONS candidate; promotion checklist (agent-file overlay baked in); full-candidate bench | M, with the next bundle | candidate-level gates; operator ratification via the kernel-promotion skill |
| (optional) P6 sparse-query kernel | Only if P1/P2 profiling shows the emulation dominates | L | profiler evidence |

Critical path ≈ P0 → P1 → P2 → P3, about 8-10 weeks serial; P3 skeleton and P4 can overlap P2. Work that does not depend on a phase's answer (P3 API/store skeleton, P0 measurements) starts immediately.
Subagent fan-out is natural for P1: store/API, selector, tests/gate harness, as independent file-scoped lanes.

## 7. Payoff dependence on B7

B7 (offline, zero-inference): for each request, the chunk_id/content_hash set, order, token share, and the fraction of chunk tokens whose chunk appeared before **at a different offset or predecessor**.
Ask B7 to split ρ into (i) same-predecessor repeats (already served by prefix cache and KPF; not ours), (ii) different-offset or different-predecessor repeats (this design), and to report per-request distinct-chunk count and chunk lengths (D3: quality drops past ~200 chunks, small chunks below ~2k are poor; close if median chunks >~50 or median chunk <~2k).

Also ask B7 for the *prefix-reconstructible share*: the fraction of chunk tokens that a reorder planner could place into a cached prompt's exact prefix (decides P1a's value on hybrids, independent of O3).

Request-level saving = ρ(ii) x S where S ≈ 0.65-0.8 (§2.3). Priority, not whether we build:

| B7 result | Priority | Plan |
|---|---|---|
| ρ(ii) < ~10%, or retrieval is turn-0 only with a stable preface | Lowest tier | Build P0, P1a (cheap, exact) and P1 only (attention-only plus the plumbing), keep the design; run behind KPF P2/P3 and the champion work. P2/P4 wait |
| ρ(ii) 10-30%, chunks ≥ 1-2k tokens, median chunk count < 50 | Medium | P0-P3 in sequence, P2 as a time-boxed research phase |
| ρ(ii) > 30% and chunk library is small and long | High | Start P0 immediately, run P1 and P2 in parallel lanes, aim to fold in the next champion bundle |
| B7 shows repetition only as exact prefix | None for this design | KPF already captures it; P1 shrinks to the shared plumbing that KPF can reuse |

The decision in every row is the *order and depth* of the build. Building P0-P1 is unconditional.

## 8. Risks and open items

- The deepest unknown is the layer-input drift in GDN layers (P0 measures it before P2 is committed to).
- f16 storage of B/A may cost accuracy; gate decides f16 vs f32 (doubling the numbers in §2.2).
- Flash-Next facts are metadata-only; its indexer may need a separate cache and shift rule.
- Approximate slots must never feed exact-prefix reuse (§4 step 5).
- Latent `--cache-reuse` on hybrid issue (§0): verify before anything else touches that code path.
- Belief-kernel wiring: P1 produces measurements; add the source-table row in `scripts/vidya/adapters/README.md` and a task in `handoffs/active/vidya-belief-substrate-program.md` when P0 starts (owning session applies, not a subagent).
