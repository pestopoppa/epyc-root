# How production engines handle concurrent decode over long, shared contexts, and what our llama.cpp stack can take from them

Survey date: 2026-10-04. Read-only research: no GPU or CPU workloads were run. Saved by the coordinating session from the survey subagent's hand-back; the subagent's tool could not write files.

**Scope.** :8083 serves Qwen3.8-27B Q8_0 (hybrid gated-DeltaNet + full attention) with a DFlash2 drafter (n_max 7) on one MI210 (gfx90a, ROCm 6.2). Launch shape: `-np 4 -c 393216 --kv-unified -ub 2048 -fa on -ctk/ctv q8_0 --cache-ram 65536`, with 32 checkpoints per slot.

**Verification tags.** Every source claim carries one tag:

| Tag | Meaning |
|---|---|
| **[local]** | Read in our frozen tree `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82`, or in our own result files. |
| **[gh]** | Verified with `gh pr view` / `gh pr diff` against `ggml-org/llama.cpp`. |
| **[src]** | A research subagent fetched the primary source (GitHub file, PR, paper or docs). The vLLM hybrid-APC docs were spot-checked directly. |
| **[unverified]** | Search-snippet level only. |

The diff of upstream PR #29510 is saved next to this report as `pr29510.diff`.

---

## 0. Findings up front

1. **KVU-16b's 0.52 tok/s is mainly prefill/decode interference (b), made worse by (a), not steady-state concurrent decode.**
   - The slot timeline (`slots.jsonl`, §1) never had a moment with four slots decoding and no prefill in flight.
   - Every decoding slot advanced exactly one decode/verify step per 2048-token prefill ubatch. Each step took about 8.5 s with one neighbour decoding and about 17.7 s with three.
   - llama-server puts decode tokens first, but then fills the rest of the batch with prompt tokens up to `n_batch`. It has **no separate prefill token budget while slots are decoding** [local: `server-context.cpp` `update_slots()` ~L3193-3215, L3614].
   - vLLM (`long_prefill_token_threshold`, `max_num_batched_tokens`), SGLang (`--chunked-prefill-size`), TensorRT-LLM ("chunked context") and Sarathi-Serve all bound this. It is the cheapest large win available to us.
2. **Prefix KV for concurrent subagents is never shared today, although the machinery for it already exists in our tree.**
   - In unified mode, `llama_kv_cache::seq_cp` adds a seq-id to existing cells with zero copy [local: `llama-kv-cache.cpp:450-491`].
   - `llama_memory_recurrent::seq_cp` shares the recurrent tail cell and copies it on write at the next `find_slot` [local: `llama-memory-recurrent.cpp:246-281`].
   - The server's checkpoints already save and restore the recurrent state alone (`LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY`).
   - The server only uses `seq_cp` for `n>1` child tasks (`copy_state_to`, L735/L3834). Slot selection never looks at **busy** slots (`get_available_slot`, L1601-1700).
   - Result: four subagents with the same 60k-token trunk prefill it four times and hold four copies, about 6 GB of the pool.
   - **This is SGLang's radix-plus-Mamba-snapshot design and vLLM's hybrid prefix caching in align mode, rebuilt with parts we already have.**
3. **Per-sequence KV views are arriving upstream as PR #29510 (`flash_attn_ext_rows`). It does not make KVU-19a/19b redundant for us.** [gh, open, 2026-09-27]
   - The PR effectively adds paged attention with a page size of 1.
   - It runs only on NVIDIA's MMA kernel.
   - It only slices batches that are one token per sequence, an equal split, or a single sequence. Unified KV uses `split_simple` [local: `llama-kv-cache.cpp:716`]. So both our **DFlash2 verify batches** (up to 8 tokens per sequence) and our **mixed prefill+decode ubatches** fall back to the dense mask.
   - It also turns itself off when sequences share cells (`n_sum > n_kv`), which is exactly the prefix-shared case from finding 2.
   - KVU-19b's per-row skip covers all three cases. Keep it.
4. **"Run vLLM/SGLang on the MI210 for this role" is not a production option today.**
   - gfx90a is a degraded tier: AITER does not build for it.
   - vLLM has an open MI210 crash for the Qwen3-Next family (#25030).
   - CDNA2 has no FP8, and there is no vLLM GGUF path for this hybrid model. bf16 weights (about 54 GB) leave room for only about 90k tokens of KV.
   - vLLM's hybrid prefix caching is documented as experimental.
   - It is worth one time-boxed reference measurement at most (§5).

---

## 1. Our failure, re-read against the data

### 1.1 KVU-16b timeline

Source: `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/kvu16b/20261004T032520Z/slots.jsonl`, derived by differencing `/slots` samples [local].

| Phase | Occupied cells | Prefilling slot: rate | Decoding slots: rate each | Implied step time |
|---|---|---|---|---|
| Slot 1 prefills alone, 0→80k | 12k→80k | 589→325 tok/s (own-length attention) | – | 3.5-6.3 s per 2048 ubatch |
| Slot 2 prefills, slot 1 decodes | 92k→151k | 243→202 tok/s | 0.40-0.50 tok/s | ~8.5-10 s; ~3.7 tok per step (DFlash accepts) |
| Slot 3 prefills, slots 1-2 decode | 166k→225k | 165→141 tok/s | 0.19-0.45 tok/s | ~12.5-14.5 s |
| Slot 0 prefills, slots 1-3 decode | 247k→298k | 122→111 tok/s | 0.10-0.33 tok/s | ~17-18 s; ~2.2 tok per step |

What the timeline shows:

- **Decode is paced by the prefill ubatch.** Each `update_slots` iteration runs one batch: decode/verify tokens plus up to 2048 prompt tokens with `-b` at its default 2048 = `-ub`. The decoders therefore get one step per prefill chunk.
- **The prefill chunk itself slows as foreign cells accumulate**: 243 → 165 → 122 tok/s at the same own-context range. That is failure (a) acting on prefill. Without KVU-19a, a prefill tile attends over all occupied cells. KVU-19a-1's batched-bench S_PP rose from 13,205 to 21,017 t/s at 4×16k, which confirms that the skip recovers this for single-sequence prefill tiles.
- **The rising TTFT (181 s → 525 s → 1,070 s → never) is mostly serialized, slowed prefill of four distinct 80k prompts.** In the real fan-out workload, most of those tokens would be a shared trunk (finding 2).

### 1.2 P3 and KVU-19a

- P3 A1 measured single-sequence decode losing −32.6/−49.5/−59.5% (no-draft) with 1/2/3 parked neighbours.
- KVU-19a fixes the single-sequence case: the micro-bench went from about 2003 to 282 µs per layer call at +114,688 foreign cells, and P3-mini from 82 to 169 steps/s.
- KVU-19a does not help batched decode, because the tile's live set is the union of all sequences (filed as KVU-19b).
- Derived from the fold-record micro-bench (an inference): a foreign cell costs about 15 ns per layer on the vec/WMMA paths. That is roughly 10× above the HBM byte cost of a q8_0 cell (~2.2 KB per layer). **Attention on gfx90a here is compute/latency-bound, not bandwidth-bound.** This matters in §4 rec 5: methods that raise arithmetic intensity, such as Hydragen or cascade attention, pay off more than their bandwidth argument alone suggests.

### 1.3 VRAM arithmetic

These numbers are used in (e) and in the recommendations.

**Attention KV:**
- 16 full-attention layers × 4 KV heads × 256 dim × 2 (K, V) × 1.0625 B (q8_0) = **34.8 KB per token**.
- The 393,216-cell pool is therefore 12.75 GiB, which matches the measured value.
- An 80k-token context holds about 2.8 GB of KV.

**Recurrent state:**
- About **150 MiB per sequence**, per the server log `created context checkpoint … size = 150.2 MiB`. That is the gated-DeltaNet state, target plus drafter.
- So one recurrent snapshot costs as much as about 4.4k tokens of KV. Snapshotting on a fixed 2k grid would cost more than the KV itself. Snapshots have to be **sparse and placed at branch points**, which is exactly where vLLM and SGLang ended up (§2).

**Budget:**
- Measured load peak is 50.78 GiB with the 393k pool. KFD peak in KVU-16b was 58.9 GiB.
- That leaves roughly 5-11 GiB of headroom on 64 GiB, about 150-330k more cells.
- Deduplicating a 60k trunk across 4 subagents frees about 180k cells. **Sharing prefixes buys more capacity than resizing the pool.**

---

## 2. Mechanisms in the production engines

### 2.1 vLLM (V1 engine)

**PagedAttention / block tables.** [src]
- KV is split into fixed blocks (default 16 tokens). Each request owns a row of a block table, so attention reads only that request's blocks.
- Paper: Kwon et al., SOSP'23, arXiv:2309.06180.
- V1 code: `vllm/v1/worker/block_table.py` → `BlockTable` (`append_row`, `compute_slot_mapping` as a Triton kernel, `commit_block_table`), plus `map_to_kernel_blocks()` when the allocator block size differs from the kernel block size.
- Backends consume it through `FlashAttentionMetadataBuilder.build()` in `vllm/v1/attention/backends/flash_attn.py`.
- **Relevance:** this solves (a) structurally, because cost scales with the sequence's own length.

**Automatic prefix caching (APC).** [src]
- Block hashing: `vllm/v1/core/kv_cache_utils.py::hash_block_tokens(parent_hash, token_ids, extra_keys)` builds a chained hash. `extra_keys` folds in LoRA, multimodal hashes and cache salt.
- LRU free list: `FreeKVCacheBlockQueue`, an intrusive doubly-linked list.
- `vllm/v1/core/block_pool.py::BlockPool`:
  - `get_cached_block` looks blocks up;
  - `cache_full_blocks` registers blocks, and only **full** blocks are cached;
  - `touch` increments the ref count on a hit;
  - `free_blocks` decrements it; a freed cached block becomes evictable.
- Entry point: `KVCacheManager.get_computed_blocks()` → `coordinator.find_longest_cache_hit()`.
- Because only full, immutable blocks are shared, ordinary models need no copy-on-write.
- Copy-on-write was added recently, and only for the fine-grained partial-block hit path for hybrid models (`take_pending_cow_copies`, PR #46384).
- **Relevance:** fixes (c) for both prefill compute and KV memory.

**Chunked prefill and the V1 scheduler.** [src]
- `vllm/v1/core/sched/scheduler.py::Scheduler.schedule()` schedules **RUNNING requests first**, then WAITING ones, against a per-step `token_budget = max_num_scheduled_tokens`.
- `long_prefill_token_threshold` caps one long prompt's chunk per step, "to stop a long prefill from starving other requests".
- `max_num_partial_prefills` and `max_long_partial_prefills` limit concurrent partial prefills.
- Caveat: PRs #49075 and #57427 suggest these limits were not always enforced in V1, so check the pinned version.
- **Relevance:** this is exactly failure (b).

**Cascade attention.** [src]
- `flash_attn.py::use_cascade_attention(common_prefix_len, query_lens, …)` enables it when:
  - the common prefix is at least 256 tokens;
  - there are at least 8 queries;
  - there is no ALiBi, sliding window or local attention;
  - and a cost model favours it over FlashDecoding.
- The common prefix length comes from `KVCacheManager.get_num_common_prefix_blocks`: blocks whose `ref_cnt` equals the number of running requests. That is, the prefix shared by **all** requests in the batch.
- The prefix pass treats the whole batch as one virtual query set over the shared blocks. The suffix pass is per request. `merge_attn_states()` combines them with log-sum-exp (LSE).
- **Relevance:** (a) and decode bandwidth/compute when sharing is heavy. It only applies to a prefix common to the whole batch.

**Hybrid / Mamba models.** [src; docs spot-checked]
- `vllm/v1/core/kv_cache_coordinator.py::HybridKVCacheCoordinator` groups layers by `KVCacheSpec`.
- `find_longest_cache_hit` runs a fixed-point shrink across groups. Full attention goes first because its hits are downward-closed; EAGLE/MTP groups get one extra unit of slack.
- `vllm/v1/core/single_type_kv_cache_manager.py::MambaManager` manages recurrent state as pages in the same allocator.
- Page-size mismatch is handled by growing the attention block size until it matches the Mamba page (e.g. 672-token blocks for Nemotron-Nano-12B-v2) [PyTorch blog "Hybrid Models as First-Class Citizens in vLLM", 2025-11-05].
- Prefix reuse:
  - `--mamba-cache-mode align` stores state only on the block grid, so a hit "can resume only at a block boundary".
  - `--prefix-match-unit N` gives sub-block key granularity (PRs #45939, #46384).
  - `--enable-mamba-shared-prefix-checkpoint` "stores a checkpoint at the shared-prefix junction, the point where an earlier request with the same prefix stopped". It requires align mode plus EAGLE/MTP, among other conditions.
- Known defects:
  - #45238: the hit rate silently drops to 0% when the align checkpoint lands in request-unique tokens.
  - #47861: MTP and Mamba prefix-cache correctness, fixed.
  - #53504: MTP first-repeat miss, open.
- Officially "experimental".
- **Relevance:** (d). The lesson is that **snapshots go at branch points, not on a dense grid**, because the state is large. This matches our 150 MiB vs 34.8 KB per token arithmetic.

### 2.2 SGLang and FlashInfer

**RadixAttention.** [src]
- `python/sglang/srt/mem_cache/radix_cache.py::RadixCache`:
  - `match_prefix` is page-aligned and splits nodes;
  - `insert`;
  - `evict` takes a heap over evictable leaves and cascades upward;
  - `inc_lock_ref` / `dec_lock_ref` protect nodes in use.
- Pools are in `memory_pool.py` (`ReqToTokenPool`, `MHATokenToKVPool`).
- Every finished or in-flight sequence's KV is a tree path, so a new request reuses the longest matching path **even while the owner is still decoding**. This is the gap in llama-server.
- Paper: arXiv:2312.07104.

**Cache-aware scheduling.** [src]
- `managers/schedule_policy.py`:
  - **LPM** sorts the queue by `-num_matched_prefix_tokens`;
  - **DFS_WEIGHT** orders requests by a radix-tree DFS so siblings that share branches run together;
  - it falls back to FCFS when the queue is longer than 128.
- `PrefillAdder` truncates a chunk to `chunk_tokens_limit` and re-queues the rest.
- Flags: `--chunked-prefill-size`, `--enable-mixed-chunk`.

**Hybrid / linear attention.** [src via PR diffs; direct file fetch 404'd]
- `mem_cache/mamba_radix_cache.py::MambaRadixCache`. A tree node is a valid hit only where `node.mamba_value` holds a snapshot.
- `HybridReqToTokenPool` + `MambaPool`.
- `--mamba-radix-cache-strategy`:
  - `no_buffer` (default);
  - `extra_buffer`: overlap scheduling plus "branching point caching", recommended with `--page-size 64`.
- Spec decode for Qwen3-Next uses the built-in MTP as NEXTN/EAGLE.
- Correctness fault lines are still open in 2026: #24221 (snapshot race with chunked prefill) and #39342 (`--enable-mixed-chunk` corrupts Mamba checkpoints on GDN models).
- **Relevance (d):** it is the same "snapshot at branch points" answer as vLLM. The bugs warn that **mixing chunked prefill with recurrent snapshots is where correctness breaks**. Our server already checkpoints mid-prefill (#24176 checkpoints at user-message boundaries), so any fork feature must be tested against that.

**FlashInfer cascade.** [src]
- `flashinfer/cascade.py`:
  - `merge_state` / `merge_state_in_place` / `merge_states` (LSE merge);
  - `MultiLevelCascadeAttentionWrapper` (N levels over paged KV, `plan()`/`run()`);
  - `BatchDecodeWithSharedPrefixPagedKVCacheWrapper`.
- The 2024-02-02 blog reports up to 31× over vLLM PagedAttention and 26× over non-cascade FlashInfer, on H100 with long shared prefixes and short suffixes.
- FlashInfer paper: arXiv:2501.01005. Its block-sparse / composable formats use variable-length page tables (`kv_indptr`, `kv_indices`, `kv_last_page_len`) and a load-balanced `plan`/`run` split.
- **ROCm:** FlashInfer's ROCm port (`AMD-Ecosystem/flashinfer`) targets gfx942/gfx950 only, **not gfx90a**.

### 2.3 Others

| System | Mechanism | Numbers (their conditions) | Applicable to us? |
|---|---|---|---|
| TensorRT-LLM [src] | Radix-tree block reuse in `kvCacheManager.cpp` (`enable_block_reuse`, 32-token blocks, priority LRU, copy-on-write for partial blocks); in-flight batching; chunked context. Hybrid Mamba reuse via the V2 Python KV manager with `mamba_state_config` (periodic or explicit boundaries), still crashy (#18849). | – | Design reference only; NVIDIA-only. |
| Sarathi-Serve (arXiv:2403.02310, OSDI'24) [src] | Chunked prefill plus **stall-free** scheduling: decodes always proceed; prefill fills a per-step token budget sized from a TBT (time-between-tokens) target. | Up to 2.6× SLO-constrained throughput (Mistral-7B, A100) | **Yes: rec 1.** |
| Hydragen (arXiv:2402.05099) [src] | Split attention into shared prefix and per-sequence suffix; batch every sequence's queries against the prefix as one matmul; LSE merge. | Up to 32× end-to-end (CodeLlama-13B, large batch); <15% loss going 1k→16k prefix | Kernel idea for rec 5. |
| ChunkAttention (arXiv:2402.15220) [src] | Prefix tree of KV chunks plus a two-phase partition kernel. | 3.2-4.8× self-attention kernel, 1-4k system prompts | Same idea as Hydragen. |
| RelayAttention, DeFT, BatchLLM, POD-Attention [src] | Read the shared prefix once per batch; tree attention; global prefix identification plus co-scheduling; fused prefill+decode kernel. | POD: up to 59% attention speedup | Rec 5 / background. |
| LMCache + CacheBlend (arXiv:2405.16444) [src] | KV tiers (CPU/disk/remote); **non-prefix** chunk reuse with 5-18% selective recompute. | – | **No for this model.** The recurrent state depends on every earlier token, so a reused middle chunk cannot be blended. Only relevant for pure-attention models. Our `--cache-ram` already is the host tier. |
| Mooncake (arXiv:2407.00079), DistServe (2401.09670) [src] | KV-centric prefill/decode disaggregation across nodes; a shared DRAM/SSD KV pool. | Mooncake +75% requests in production | **No.** We have one GPU. The disaggregation lesson reduces to rec 1: isolate decode from prefill in time, since we cannot separate them in space. |

### 2.4 llama.cpp upstream, as of 2026-10-04

**Paged KV: nothing merged.** [gh/src]
- #14070 (closed), #17579 (closed 2026-07-11) and #22569 (open draft: `--kv-paged`, 16-token blocks, admission/eviction/swap scheduler) all exist but none landed.
- #22569 shows parity at equal concurrency and its gain is capacity: 247 vs 25 sequences on an A10G.

**Per-sequence views: PR #29510 `flash_attn_ext_rows`, by am17an.** [gh, open, updated 2026-10-03]
- **Design:**
  - A new `ggml_flash_attn_ext_rows(q,k,v,mask,kv_rows,…)` op, where `kv_rows[n_kv, n_slices]` is an I32 indirection.
  - Each query slice attends only to its own compact cell list. The author describes it as "rows are pages of size 1 at the moment, but that can change". That is the start of upstream paged attention.
- **Author's numbers** on Qwen3.8-27B Q8_0, 4×100k, RTX Pro 6000: S_PP 1106 → 2778 t/s, S_TG 90 → 102 t/s.
- **Maintainers:** ggerganov calls it "a good direction" but wants no Metal regression, so it is undecided.
- **Limits that matter to us** (from the diff, `pr29510.diff`):
  - Dispatch is gated `GGML_CUDA_CC_IS_NVIDIA(cc) && turing_mma_available(cc)`. Only the MMA kernel reads `kv_rows`; vec and tile ignore it. On HIP it would fall back.
  - `get_n_kv_slices()` returns 0 unless the ubatch is one sequence, an equal split, or one token per sequence. Unified KV uses `split_simple`, so **DFlash2 verify (≤8 tokens per sequence) and mixed prefill+decode ubatches get no slicing**.
  - `get_n_kv_rows()` returns 0 when `n_sum > n_kv`, i.e. when cells are shared across sequences. **Prefix sharing disables it.**
  - Rows are padded to the longest sequence in the ubatch (`n_max`).
- Related: closed #28943 (WMMA interior skip), open #28495 (the issue our KVU-19 cites), and a community branch (ynankani, commit 2e0685368) with compact views and masked-block skip.

**Prefix caching.** [local/gh]
- `--cache-reuse` (#9866) works by KV shifting and is **disabled for our model**: `llama_memory_can_shift()` is false for recurrent memory, so the server zeroes `n_cache_reuse` [local L1291-1301]. Our handoff's "declined `--cache-reuse`" is correct.
- The host-RAM prompt cache `--cache-ram` (#16391) restores **by copy** into an idle slot (best LCP).
- Context checkpoints `--ctx-checkpoints` are hybrid- and SWA-aware and store the recurrent state with `PARTIAL_ONLY`. They are created at user-message boundaries (#24176) and near the end of the prompt.
- Cross-slot sharing is not merged. Related open PRs:
  - #26204 `/slots action=clone_to` copies KV between slots. On Metal, a 7.4k trunk with 4 branches gave 2.12× wall time; it did not cover hybrid models.
  - #29578 pinned prefix preload.
  - #27451 share checkpoint state.
- The recurrent/hybrid checkpoint-reuse PRs are a long contested tail (#24035, #25592 and #24785 open; #24899 and #26191 closed).
- No radix-tree proposal exists.

**Scheduling.** [gh]
- #10718 "server : chunked prefill support" has been open since 2024-12. ggerganov's concern: "total wait time over all requests is longer".
- #28532 `--slot-linger-ms` prefers resuming the session that holds a slot. Open.
- Nothing merged caps prefill per step.

**HIP FA.** [src/local]
- Upstream removed the rocWMMA FA (#26046, 2026-07-24). CDNA now goes through the MMA kernel on MFMA.
- **Our v10 tree still builds `GGML_HIP_ROCWMMA_FATTN=ON`**, and the fold record shows verify/batched/prefill running on WMMA.
- The v11 rebase will therefore move our verify and prefill path onto MMA. That changes where KVU-19a/19b must live and is the path #29510 extends.

**Our own prior asset.** [local]
- v5 shipped a **CPU** paged attention: `src/llama-kv-block.h` (ref-counted blocks, `enable_cow`, block pool and stats), `GGML_OP_FLASH_ATTN_EXT_PAGED`, and `tests/test-kv-block.cpp`.
- It was forward-ported in `0e485a91b` and reverted in `a4e2b4f86` (2026-06-24).
- The block accounting is reusable scaffolding. There is no GPU kernel.

### 2.5 ROCm on gfx90a [src]

**vLLM:**
- The install docs still list gfx90a, but require **ROCm ≥ 6.3** (our host has 6.2; a container's userspace may work, unverified).
- AITER backends do not cover gfx90a (`VLLM_USE_AITER=0`), leaving TRITON_ATTN or ROCM_ATTN.
- The 2026-02 ROCm attention-backend blog covers only MI300/MI355.
- Qwen3-Next family on MI210: **#25030 is open** (unified-attention Triton "arange's range must be a power of 2", under tensor parallelism).
- The FLA GDN fused kernels were gated `is_cuda()`; #51406 relaxes this, merge status unconfirmed.
- DFlash is supported in vLLM via Speculators v0.5.0 (2026-05), unverified on ROCm.

**AITER:** gfx942/gfx950 only. Building for gfx90a fails (aiter#179).

**SGLang:**
- Its AMD docs mention only MI300X (and MI250 for one quantization path).
- The ROCm release notes' supported list excludes gfx90a.
- Sources conflict, so treat it as **unsupported**.

**CK flash-attention:** `ROCm/flash-attention` does build for gfx90a (fp16/bf16, head dim ≤ 256). That covers prefill; paged decode would be Triton.

---

## 3. Mapping mechanisms onto our failure modes

Legend: ●● solves it · ● partly solves it · – no effect.

| Mechanism | (a) cost ∝ total occupancy | (b) prefill starves decode | (c) duplicate prefix KV | (d) hybrid recurrent prefix reuse | (e) VRAM planning |
|---|---|---|---|---|---|
| Block tables / PagedAttention (vLLM); `kv_rows` (#29510) | ●● structurally | ● (prefill tiles stop scanning foreign cells) | – by itself | – | ● (no per-slot reservation) |
| KVU-19a (masked block skip, ours) | ●● single-sequence decode/verify and prefill tiles; ✗ batched decode | ● (prefill rate with neighbours) | – | – | – |
| KVU-19b (per-row skip, ours) | ●● batched decode/verify, including mixed ubatches | ● | works with shared cells | – | – |
| Sequence-affine cell allocation (our gap) | ● (makes 19a/19b skip effective for generated tokens) | – | – | – | – |
| Chunked prefill + decode-first token budget (vLLM / Sarathi / SGLang / TRT) | – | ●● | – | must checkpoint at chunk ends (SGLang #39342 warning) | – |
| APC hash blocks / radix tree (vLLM, SGLang, TRT) | ● (less occupancy) | ● (less prefill) | ●● | needs state snapshots | ●● (dedup) |
| Hybrid prefix snapshots at junctions (vLLM shared-prefix checkpoint, SGLang `mamba_value` / extra_buffer, TRT `mamba_state_config`) | – | – | – | ●● | ● (state is 150 MiB each, keep sparse) |
| Cache-aware ordering: LPM / DFS-weight (SGLang); trunk-first fan-out | – | ● | ●● (maximizes hits) | ● | ● |
| Cascade / Hydragen / ChunkAttention / FlashInfer shared-prefix | ●● on the shared part | – | requires sharing | – | – |
| Host KV tier (LMCache; our `--cache-ram`) | – | – | ● (TTFT only, copies) | ● (checkpoints included) | ● |
| CacheBlend (non-prefix reuse) | – | – | ● | ✗ impossible with recurrent state | – |
| Prefill/decode disaggregation (Mooncake, DistServe) | – | ●● (needs ≥ 2 devices) | – | – | – |

---

## 4. Recommendations, ranked by ROI for us

### Rec 1 — Prefill token budget while slots are decoding (stall-free chunked prefill)

**Area:** llama-server, experimental tree. **Effort: S.** **Impact: high on (b).**

**What to change.** In `update_slots()`, after decode/verify tokens are added, cap the prompt tokens added this iteration:
- `n_prefill_max = any_slot_generating ? B_mixed : n_batch`, with `B_mixed` ≈ 256-512 behind a new flag such as `--prefill-budget-decoding N`.
- Better, the Sarathi form: size `B_mixed` from a per-step time target using the measured prompt rate (e.g. a target step time of about 1 s).
- Keep `-ub 2048` for solo prefill so throughput with no neighbours is unchanged.
- This is about 30-80 LOC near L3205-3215 and L3614 of `server-context.cpp`, plus a CLI arg. It is close in spirit to upstream #10718.

**Expected gain** (estimate, to be measured with the KVU-16b harness):
- Step time scales roughly with chunk size while prefill is compute-bound.
- A 512-token chunk should cut the 8.5-17.7 s steps to about 2-4.5 s, so decode under a neighbour's prefill improves about **4×** (0.1-0.5 → ~0.5-2 tok/s per slot).
- 256 gives about 6-8× but costs more prefill efficiency.
- TTFT of the prefilling request rises an estimated 10-30%. Sweep `B_mixed` ∈ {256, 512, 1024} with `llama-bench -ub` and the KVU-16b runner.

**Risks:**
- Smaller mixed ubatches add more checkpoint-creation points (they are created during prompt processing). Verify the checkpoint count and RAM.
- DFlash2 verify rows ride in the same ubatch. Re-check `post_decode` sub-batch indexing (cf. KVU-7's "speculative batch index" assert).

**Interactions:**
- Complements the orchestrator's one-long-prefill gate (KVU-15), the coarse analogue of vLLM's `max_long_partial_prefills=1`.
- Orthogonal to KVU-19.

### Rec 2 — Cross-slot prefix forking anchored on recurrent checkpoints, plus cache-aware dispatch

**Area:** llama-server, experimental tree, plus the orchestrator. **Effort: M** (server ~300-500 LOC + tests; orchestrator S-M). **Impact: very high on (c), (d) and (e); indirect on (a) and (b).**

This rebuilds RadixAttention plus Mamba branch-point snapshots from parts llama.cpp already has.

**Server side:**
1. **Find the source.** For a new task, compute the LCP against **all** slots, busy ones included, and against each slot's checkpoint list. Pick slot S and fork position `p` = the largest S checkpoint position ≤ LCP (or S's exact prompt end, if S is waiting there).
2. **Share the attention KV:** `mem_attn->seq_cp(S, dst, 0, p)`. This is zero-copy in unified mode.
3. **Restore the recurrent state:** load S's checkpoint at `p` into `dst` with `llama_state_seq_set_data_ext(..., PARTIAL_ONLY)`. Do the same for the drafter context. Do **not** rely on `llama_memory_hybrid::seq_cp` for the recurrent half: `p1` is ignored and S's *current* tail is shared [local L152-154, L246-281].
4. **Prefill from `p`.** Positions are unchanged, so no shift is needed.

**Explicit trunk checkpoint:** add a request field, e.g. `"checkpoint_at": <token pos>` or "mark end of shared prefix". The orchestrator then guarantees a snapshot exactly at the parent→subagent junction. This is vLLM's `--enable-mamba-shared-prefix-checkpoint` and SGLang's branching-point caching.

**Orchestrator side:**
- **Trunk-first fan-out:** issue the shared trunk once, then the N children, rather than N full prompts at once. This is the cold-start case #26204 measured: built-in reuse found 0 cached tokens.
- **LPM-style ordering and slot pinning** (`id_slot`) driven by the KVU-15c prefix history.
- The KV-pool gate should count **unique** cells.
- The prompt-determinism plan becomes load-bearing: system prompt, repo files and parent transcript must be byte-stable and in stable order.

**Expected gain:**
- For N subagents with a T-token trunk, prefill drops from N·T to T + N·suffix.
- With 4 × 60k trunk at about 120-300 tok/s, that removes roughly **10-30 min of GPU prefill per fan-out**. Child TTFT goes from minutes to the suffix time (seconds to tens of seconds).
- Pool use drops by (N−1)·T cells, about 180k at N=4, T=60k, freeing about 6 GB.
- Lower occupancy then also shrinks (a) and the prefill slowdown in §1.1.

**Risks:**
- Correctness of hybrid state restore across slots, plus the drafter's state. Gate with a logits-equivalence test: fork vs fresh prefill, as #26204 did (top-1 match on 24/24 prompts).
- Checkpoints created mid-prefill vs chunked prefill (SGLang #39342 class bug).
- `cache_idle_slots` save/clear on shared cells must remove only that slot's seq bit; the code supports this, but it needs a test.
- #29510's `n_sum > n_kv` fallback conflicts with sharing (see Rec 4).

### Rec 3 — Finish KVU-19b and add sequence-affine cell allocation

**Area:** experimental kernel plus KV cache. **Effort: M** (19b, in flight) + **S-M** (allocator). **Impact: high on (a) for concurrent decode/verify.**

**KVU-19b** (per-row skip, or regrouping query rows by sequence inside the tile):
- It is the HIP-native equivalent of per-sequence block tables for our actual batch shapes: DFlash verify with ≤8 tokens per sequence, and mixed prefill+decode ubatches.
- Per-sequence block tables would not make it moot: #29510's indirection cannot slice exactly those shapes (§2.4).
- **Keep it.**

**Sequence-affine allocation (new).**
- `find_slot` allocates first-fit from `head` per ubatch [local L1004-1075].
- During concurrent decode, each step's 4-32 new tokens from different sequences land in adjacent cells. Every 256-cell block holding generated tokens is then live for **every** decoding sequence, so even a per-row block skip cannot skip it.
- Multi-turn agent sessions keep those interleaved generated cells as cached prefix.
- Proposal: reserve per-sequence 256-cell chunks (allocate a sequence's new tokens inside its current chunk, and a new chunk when it is full).
- This is about 100-200 LOC in `llama-kv-cache.cpp`, with no kernel change.
- **Measure first.** Have KVU-19a's scan kernel, or a debug counter, report the live-block fraction per row on organic traffic. Only build the allocator if mixed blocks are a material share.

**Expected:** 19b's done-when has batched-bench `-kvu` S_TG within about 5% of `-no-kvu` (444 → ~540 t/s at 4×16k). At 4×80k the gap is larger, so the gain is larger.

**Risk:** the deterministic-codegen hazards already seen in the D=512/576 tile kernel (KVU-19a-2).

### Rec 4 — Treat upstream #29510 (`kv_rows`) as the v11 direction, and port it as an A/B arm, not a replacement

**Area:** v11 rebase. **Effort: M-L for HIP. Impact: medium (overlaps Rec 3).**

**Port work:**
- Enable the MMA kernel's `kv_rows` path on CDNA. Upstream moved CDNA to MMA/MFMA; our tree is still on rocWMMA.
- Add `kv_rows` reads to the vec kernel for plain decode.
- Make the q8_0 → f16 conversion gather only the referenced rows, extending KVU-19a's dead-block conversion skip.

**What it would make redundant:** KVU-19b for one-token-per-sequence decode batches and single-sequence prefill only.

**What it would not cover:**
- DFlash verify and mixed ubatches, unless we also move unified KV to equal splits per sequence.
- Prefix-shared batches, because of its `n_sum > n_kv` fallback. With Rec 2 deployed, that fallback should become a hybrid: indirection for each sequence's private rows plus one pass over shared rows. That is cascade attention, i.e. Rec 5.

**Recommendation:**
- Ship 19a + 19b now.
- At the v11 rebase, carry #29510 if it has merged, A/B it against 19b on the KVU-18 cells and the 4×80k shape, and drop whichever loses.
- Watch the PR: ggerganov's Metal objection could reshape the API.

### Rec 5 — Shared-prefix (cascade / Hydragen) attention for the forked trunk

**Area:** experimental kernel. **Effort: L.** **Impact: medium-high on (a), only after Rec 2.**

**Why it helps:**
- Once N sequences share a T-token trunk, each still reads the trunk separately in every decode/verify step.
- A cascade pass computes trunk attention once for all N × (≤8) query rows, as one matmul-shaped FA call over the shared cells. It then does per-sequence suffix passes and merges with LSE.
- On gfx90a, where our measured per-cell cost is compute/latency-bound (§1.2), the batched-query trunk pass also raises arithmetic intensity.

**Expected:**
- The trunk part of attention cost drops by up to N×.
- End to end at 4 × 80k with a 60k trunk, perhaps 1.3-2× decode. That is a rough estimate that depends on attention's share of the step, which should be measured first with rocprof.

**What is needed:**
- An FA variant that emits LSE (or uses the existing `dst_meta` partials) plus a merge op.
- Graph construction that identifies trunk cells. Cells whose seq-set includes all decoding sequences in the ubatch are exactly vLLM's `get_num_common_prefix_blocks`.

**Risk:** high kernel complexity on two FA paths (vec and WMMA/MMA). Do it only if, after Recs 1-3, a profile shows attention over shared prefixes dominating.

### Non-recommendations and smaller items

- **`--cache-reuse` / CacheBlend:** impossible on this hybrid model. The recurrent state cannot be shifted or blended.
- **Disaggregation (Mooncake, DistServe):** needs a second device. Rec 1 is the single-GPU form of the same lesson.
- **Per-slot split KV (KVU-16d option c):** it fixes (a) by construction but caps per-request context. With Rec 3 plus 19b it should not be needed. Keep it as the reopen trigger already written in KVU-16d.
- **Host-tier sizing:** with Rec 2, `--cache-ram` holds checkpoints that are now cross-slot fork anchors. 32 × 150 MiB × 4 slots ≈ 19 GiB of host RAM per server is affordable. Consider more checkpoints for trunk-heavy roles.
- **#28532 `--slot-linger-ms`:** cheap to cherry-pick for agent loops with fast tool calls (the slot stays bound to the session). Low effort, modest gain. Our orchestrator can get the same effect with `id_slot` pinning.

---

## 5. Option: run vLLM (or SGLang) on the MI210 for this role

| Factor | Status | Verdict |
|---|---|---|
| Architecture support | vLLM lists gfx90a but needs ROCm ≥ 6.3 (host has 6.2). No AITER, so Triton/ROCM_ATTN only. SGLang is effectively unsupported on gfx90a. FlashInfer ROCm port is gfx942/950 only. | Degraded tier |
| Model | Qwen3-Next-family GDN on vLLM ROCm: an MI210 crash is open (#25030). FLA kernel gating on ROCm (#51406) merge status unknown. Hybrid prefix caching is documented "experimental", with open MTP interaction issues. | High risk |
| Weights / VRAM | CDNA2 has no FP8. No vLLM GGUF path is known for this hybrid model. bf16 ≈ 54 GB leaves about 5-8 GB of KV, roughly 80-120k tokens at bf16 KV (69.6 KB per token). INT8 W8A16 via Triton is plausible but unmeasured on gfx90a. | Kills the 262k-context role unless INT8 works |
| Drafter | DFlash is supported in vLLM via Speculators v0.5.0 (CUDA-validated). Our DFlash2 GGUF would need an HF-format drafter. | Unknown on ROCm |
| What we would gain | Chunked prefill with a token budget, paged KV, APC, a hybrid shared-prefix checkpoint, and cascade, all out of the box on paper. | Rec 1 and Rec 2 deliver the main gains on our own stack |

**Recommendation.** Not a production path for this role. If the operator wants the reference point (the wiki already lists "a vLLM-on-gfx90a MI210 number is still un-measured"), run one time-boxed probe (≤ 1 day, in a coordinated GPU window):
- the official ROCm vLLM container;
- Qwen3.8-27B in INT8 or bf16 at a reduced context;
- `--enable-prefix-caching --mamba-cache-mode align`;
- 4 concurrent requests sharing a 30k trunk.

Its value is a target number for Recs 1-2, not a migration.

---

## 6. Effort and impact summary

| Rank | Item | Where | Effort | Expected impact | Fixes |
|---|---|---|---|---|---|
| 1 | Decode-aware prefill budget (Sarathi-style) | server | S (days) | ~4× decode TPOT under concurrent prefill; +10-30% TTFT on the long prompt | (b) |
| 2 | Cross-slot prefix fork with checkpoint-anchored recurrent state + trunk-first/LPM dispatch | server + orchestrator | M (1-2 wk) | Fan-out child TTFT minutes → seconds; −(N−1)·T cells (~6 GB at 4×60k) | (c), (d), (e), relieves (a)/(b) |
| 3 | KVU-19b + sequence-affine cell allocation | kernel + KV cache | M + S-M | Batched decode/verify at `-no-kvu` parity (≥ +20% at 4×16k, more at 4×80k) | (a) |
| 4 | Port upstream #29510 `kv_rows` at v11 as an A/B arm | v11 rebase | M-L (HIP MMA + vec) | Overlaps 19b for plain decode; no help for verify, mixed or shared batches as written | (a) |
| 5 | Cascade/Hydragen shared-trunk attention | kernel | L | Trunk attention ÷N; maybe 1.3-2× decode at 4×80k with a 60k trunk | (a) with sharing |
| – | vLLM on MI210 | probe only | ≤ 1 day | Reference number; not a production path | – |

---

## 7. Sources

**Local** (read in our tree and results):
- `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82`:
  - `tools/server/server-context.cpp` (`get_available_slot` L1601; `copy_state_to` L735; `update_slots` batch fill L3193-3215, L3614; cache-reuse gating L1285-1301, L3315-3340; checkpoint policy L3562-3575);
  - `src/llama-kv-cache.cpp` (`seq_cp` L450; `find_slot` L901-1075; `split_simple` for unified L716);
  - `src/llama-memory-recurrent.cpp` (`seq_cp` L246);
  - `src/llama-memory-hybrid.cpp` (L152);
  - git `0e485a91b` / `a4e2b4f86` (CPU paged attention).
- KVU-16b: `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/kvu16b/20261004T032520Z/{report.md,slots.jsonl,requests.jsonl}`
- P3: `/mnt/raid0/llm/tmp/x0-27b-quants/results/p3/report.md`
- Handoffs: `handoffs/active/kv-unified-stack-rollout.md` (KVU-15/16/19), `agentic-serving-harness-fixes.md`
- Fold record: `docs/design/fa-masked-block-skip-20261003-fold.md`

**llama.cpp upstream:**
- Verified with gh: #29510, #28495, #22569, #26204, #29578, #10718, #28532.
- Subagent-fetched [src]: #14070, #17579, #18747, #28943, #26046, #16391, #9866, #24176, #24035, #25592, #24899, #26191, #27451.
- https://github.com/ggml-org/llama.cpp/pull/29510 · https://github.com/ggml-org/llama.cpp/issues/28495 · https://github.com/ggml-org/llama.cpp/pull/22569 · https://github.com/ggml-org/llama.cpp/pull/26204 · https://github.com/ggml-org/llama.cpp/pull/10718

**vLLM:**
- Source files: https://github.com/vllm-project/vllm/blob/main/vllm/v1/worker/block_table.py · `vllm/v1/core/{kv_cache_utils.py,block_pool.py,kv_cache_manager.py,kv_cache_coordinator.py,single_type_kv_cache_manager.py,sched/scheduler.py}` · `vllm/v1/attention/backends/flash_attn.py`
- Docs: https://docs.vllm.ai/en/latest/design/prefix_caching.html · https://docs.vllm.ai/en/latest/features/automatic_prefix_caching.html
- Blogs: https://pytorch.org/blog/hybrid-models-as-first-class-citizens-in-vllm/ · https://vllm.ai/blog/2026-02-27-rocm-attention-backend · https://vllm.ai/blog/2026-05-28-speculators-v050
- PRs/issues: #46384, #45939, #47861, #45238, #53504, #49075, #57427, #55652, #25030, #51406, #59151
- Paper: arXiv:2309.06180

**SGLang and FlashInfer:**
- https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/mem_cache/radix_cache.py · `memory_pool.py` · `managers/schedule_policy.py` · PRs #32732 and #36022 (`mamba_radix_cache.py`) · issues #24221 and #39342
- Docs: https://docs.sglang.io/platforms/amd_gpu.html · https://lmsysorg.mintlify.app/cookbook/autoregressive/Qwen/Qwen3-Next
- Paper: arXiv:2312.07104
- FlashInfer: https://github.com/flashinfer-ai/flashinfer/blob/main/flashinfer/cascade.py · https://flashinfer.ai/2024/02/02/cascade-inference.html · arXiv:2501.01005 · https://github.com/AMD-Ecosystem/flashinfer

**Others:**
- TensorRT-LLM: https://nvidia.github.io/TensorRT-LLM/latest/features/kvcache.html (issue #18849)
- Papers: Sarathi-Serve arXiv:2403.02310 · Hydragen arXiv:2402.05099 · ChunkAttention arXiv:2402.15220 · RelayAttention arXiv:2402.14808 · DeFT arXiv:2404.00242 · BatchLLM arXiv:2412.03594 · POD-Attention arXiv:2410.18038 · CacheBlend arXiv:2405.16444 · Mooncake arXiv:2407.00079 · DistServe arXiv:2401.09670
- LMCache: https://github.com/LMCache/LMCache (issue #3238)

**ROCm:**
- https://docs.vllm.ai/en/latest/getting_started/installation/gpu/ · https://github.com/ROCm/aiter (issue #179) · https://github.com/ROCm/flash-attention · https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html

**Caveats:**
- The vLLM, SGLang, TRT and ROCm details are subagent fetches of primary sources. Two were partial: the `gpu_model_runner.py` cascade-prefix function body (file truncated) and the `mamba_radix_cache.py` method list (404; confirmed via PR diffs).
- The SGLang gfx90a status conflicts between sources; reported as unsupported.
- All expected-gain figures in §4 are estimates derived from our measured rates, not measurements.
- **Belief-kernel note:** this survey makes no new measurements. If Rec 1 or Rec 2 is prototyped, wire its records under VB-KVU-* per CLAUDE.md.
