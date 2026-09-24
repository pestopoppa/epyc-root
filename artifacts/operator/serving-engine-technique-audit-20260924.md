# Serving-engine technique audit — what vLLM / SGLang (and TGI, TensorRT-LLM, LMDeploy) do with a shared KV pool, and what we should steal

**Date**: 2026-09-24 · **Requested by**: operator · **Mode**: READ-ONLY research + drafting (no repo edits, no process, no inference).
**Context**: :8083 (Qwen3.8-27B Q8_0, `-np 2 -c 196608`, MTP draft 8, MI210) is about to flip to `--kv-unified`
(package: `/mnt/raid0/llm/tmp/stack-change-kvu-20260924/PACKAGE.md`). Under a unified pool the frozen v10 server admits
each request against `slot.n_ctx` only and, when `llama_decode` finds no free cells, purges idle slots, halves `n_batch`
to 1 and then **fails every in-flight request** (`tools/server/server-context.cpp:3759-3790`, `:1716-1735`). The
orchestrator branch `feat/context-overflow-handling-20260924` @ `fca70439` (worktree
`/mnt/raid0/llm/tmp/orch-ctx-overflow-20260924`) is the admission/queue/recovery design already built against that.

All llama.cpp citations are against the frozen production tree `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82` (v10).
Anything marked **(inferred)** was not read from a source line or a log.

---

## 0. Executive summary

The production engines are robust under a shared KV pool because of four things, in this order of importance:

1. **They never let the engine hit the wall blind.** Admission is a *token* budget (prompt + reserved decode tokens)
   against the actual free pool, not a request count. (vLLM `allocate_slots`/`token_budget`; SGLang `PrefillAdder`
   `rem_total_tokens` + `new_token_ratio`; TGI `--max-batch-total-tokens`.)
2. **When they do hit the wall, they evict ONE victim and requeue it — never all.** vLLM preempts `running[-1]` (or the
   lowest priority) and re-prefills it; SGLang "retracts" the request with the least decode progress; TRT-LLM's
   MAX_UTILIZATION "pauses and restarts" some requests. llama-server's equivalent is a `// TODO` at
   `server-context.cpp:3760` ("try to terminate only the largest active slot/sequence and continue with the rest").
3. **Prefix reuse is a first-class tier, not a slot side-effect.** Hash-block APC (vLLM), radix tree with LRU leaf
   eviction + longest-prefix-match scheduling (SGLang), prioritized-LRU block reuse with host offload (TRT-LLM).
   llama-server has a per-slot LCP match (`--slot-prompt-similarity`), a RAM prompt cache (`--cache-ram`, FIFO
   eviction) and disk slot files (`--slot-save-path`) — the parts exist, the policy is thin.
4. **Rejection is explicit and arithmetic.** vLLM 400s on `prompt + max_tokens > max_model_len` with the numbers in
   the message; TGI validates in the router before the model sees it; llama-server 400s on `n_prompt >= n_ctx` only
   and otherwise stops generation silently at `n_ctx - 1` (`finish_reason: length`, `truncated = true`).

The overflow branch already implements (1) as an orchestrator-side FCFS token reservation, and the client contract of
(4). The **steal list (§5)** is therefore mostly about closing (1) against *real* server occupancy, adding SGLang's
adaptive decode reservation so (1) is not pessimistic, doing (2) on the orchestrator side (client-side preemption by
cancel-and-requeue, since the kernel is frozen), and sizing the (3) tiers we already ship.

Nothing here requires touching `production-consolidated-v10`. One item (a kernel-side "evict one slot" patch) is
flagged as a v11 experimental-branch candidate and is explicitly **not** recommended now (standing rule: no kernel
research until the champion is consolidated).

---

## 1. Scheduling under KV pressure

### 1.1 What the engines do

| Engine | Continuous batching | Admission unit | Preemption on KV exhaustion | Chunked prefill / long-prefill fairness | Priority |
|---|---|---|---|---|---|
| **vLLM v1** | yes; "batches all pending decode requests before scheduling any prefill" ([optimization docs](https://docs.vllm.ai/en/stable/configuration/optimization/)) | `token_budget = max_num_scheduled_tokens`, `max_num_seqs`, and `kv_cache_manager.allocate_slots(request, num_new_tokens, num_lookahead_tokens)` returns `None` when blocks are short ([scheduler.py](https://github.com/vllm-project/vllm/blob/main/vllm/v1/core/sched/scheduler.py) l.740-810) | **Recompute by default in V1** ("recomputation has lower overhead in the V1 architecture"); victim = `self.running[-1]` (FCFS) or `max(running, key=(priority, arrival_time))` (priority policy); `_preempt_request` frees blocks, sets `num_computed_tokens = 0`, `waiting.prepend_request` — the victim re-prefills from scratch (l.1539-1565). `--swap-space` (CPU swap) is the V0-era alternative; PagedAttention paper §4.5: "recomputation is more efficient when the block size is small, while swapping is more efficient when the block size is large" | Enabled by default in V1; `long_prefill_token_threshold` caps a single long prompt's tokens per step *only when there is someone to starve* ("When it is the only request there is nobody to starve, so let it use the whole budget", scheduler.py l.606-623; adaptive floor `max(threshold, input_budget // num_eligible_reqs)`) | `--scheduling-policy priority` (lower value first, ties by arrival) |
| **SGLang** | yes | `PrefillAdder`: `rem_total_tokens` (free KV incl. evictable tree), `rem_input_tokens`, `rem_chunk_tokens`; each admitted request reserves `extend_input_len + max_new_tokens × new_token_ratio + page_size` ([schedule_policy.py](https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/managers/schedule_policy.py)) | **Retraction** (`ScheduleBatch.retract_decode`, [schedule_batch.py](https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/managers/schedule_batch.py) l.3264-3348): while `check_decode_mem()` fails, pop the least-preferred request; order key `(len(output_ids), -len(origin_input_ids))` so the request with the **least decode progress (ties: longest prompt) is retracted first**; "Always keep at least one request"; the retracted request's KV is released (not inserted into the tree "because we need the space instantly"), `reset_for_retract()` and it re-prefills; in PD-decode mode the KV is first backed up to host (`release_req … backup_kv_cache`). Log line: `KV cache pool is full. Retract requests. #retracted_reqs: 1, #new_token_ratio: 0.9998 -> 1.0000` ([tuning doc](https://docs.sglang.io/advanced_features/hyperparameter_tuning.html)) | `--chunked-prefill-size` ("-1 disables"); `--max-prefill-tokens` | `--enable-priority-scheduling`, `--priority-scheduling-preemption-threshold` ("Minimum difference in priorities for an incoming request to have to preempt running request(s)"); `retraction_policy == "priority"` sorts victims by priority first |
| **SGLang `new_token_ratio`** | — | The decode reservation is `max_new_tokens × new_token_ratio`, starting at `init_new_token_ratio`, decaying per step toward `min_new_token_ratio`, and **bumped back up after every retraction** (`NewTokenRatioTracker.estimate_new_token_ratio_after_retract`, scheduler.py l.4174-4232). `--schedule-conservativeness` scales it: "Decrease to ~0.3 if token usage < 0.9 and #queue-req > 0; increase to ~1.3 if frequent KV cache full warnings" | | | |
| **TGI** | yes | `--max-batch-total-tokens` ("For max_batch_total_tokens=1000, you could fit 10 queries of total_tokens=100 or a single query of 1000 tokens"); `--max-total-tokens` per request = prompt + `max_new_tokens` ("the memory budget of running clients requests") ([launcher ref](https://huggingface.co/docs/text-generation-inference/en/reference/launcher)) | No preemption: admission is conservative, a request admitted runs to completion | `--waiting-served-ratio` (0.3) and `--max-waiting-tokens` (20) decide when to pause decodes for a prefill | `--max-concurrent-requests` (128) "will refuse clients requests instead of having them wait" |
| **TensorRT-LLM** | in-flight batching | `max_num_tokens` (8192 default), `max_batch_size`, `free_gpu_memory_fraction` (0.9) | `CapacitySchedulerPolicy::MAX_UTILIZATION` "might require that some requests be paused and restarted depending on peak KV cache memory availability"; `GUARANTEED_NO_EVICT` "guaranteeing that a request, once started, will run to completion without eviction"; `STATIC_BATCH` ([executor/types.h](https://github.com/NVIDIA/TensorRT-LLM/blob/main/cpp/include/tensorrt_llm/executor/types.h) l.216-231) | chunked context: "NVIDIA recommends that you always enable it" ([IFB doc](https://nvidia.github.io/TensorRT-LLM/features/paged-attention-ifb-scheduler.html)) | priority is on KV *blocks*, not requests (§2) |
| **LMDeploy** | yes | `cache_max_entry_count` (fraction of free GPU memory for KV, 0.8), `max_batch_size` | (not documented in the page read) | `max_prefill_token_num` (not in page read) | — |

Two things the engines have in common that llama-server lacks: (a) the decode reservation is explicit and (b) the
victim of exhaustion is one request, chosen by a policy, and it is *requeued*, not failed.

### 1.2 What we have

| Capability | llama-server v10 | Orchestrator (branch `fca70439`) |
|---|---|---|
| Continuous batching | yes — `update_slots` batches all slots' tokens into one `llama_batch`; prompt chunks are bounded by `n_batch`/`n_ubatch` (2048 effective on :8083), so decode of the other slot rides in the same batch as prefill chunks | n/a |
| Admission by KV budget | **no** — `slot.task->n_tokens() >= slot.n_ctx` only (`server-context.cpp:3303-3310`), i.e. prompt vs per-slot ctx; nothing checks pool occupancy or `max_tokens` | **yes (new)** — `SharedKVPoolAdmission.acquire(url, tokens, pool_tokens)` FCFS token reservations, `tokens = estimate_tokens_conservative(prompt) + generation` (`src/llm_primitives/inference.py:110-115`, `:940-960`); a lone request is always admitted; wait bounded by the request deadline else `ORCHESTRATOR_KV_POOL_WAIT_S` (1800 s) |
| Preemption | **abort-all** (`:3759-3790`), preceded by idle-slot purge (`try_clear_idle_slots`, unified only, "clear slots one by one", first idle slot with tokens — not LRU, source TODO says so at `:1712-1715`) and `n_batch /= 2` down to 1 | none in-engine; **recovery** = bounded backoff retry (2×, 2 s→15 s) when the request "fits alone", then one reroute to `ORCHESTRATOR_CONTEXT_OVERFLOW_ROLES` (default `ingest_long_context`), then typed error → API 413 / 503 + `Retry-After` (`context_recovery.py`, `openai_compat.py:955-1003`) |
| Chunked prefill | implicit via `n_batch` | nothing to do |
| Long-prefill fairness | none beyond `n_batch` | the FCFS reservation serialises long jobs by tokens, which is coarser than vLLM's per-step cap but is the only lever available |
| Priority | none (`queue_tasks` is FIFO with `defer`) | per-server request semaphores (`src/api/admission.py`) sized from registry `-np`; no priority class |

### 1.3 Gap

* The branch's reservation is **pessimistic**: it reserves the full generation budget. A thinking-mode planner call
  with `max_tokens: 32768` on a 120k prompt reserves 152k of 196k; a second 60k request queues even though the first
  will very likely finish thinking well below 32k. SGLang's `new_token_ratio` exists for exactly this.
* The branch is **blind to load it did not admit** (its own comment: opencode straight to :8083). `/slots` exposes
  `n_prompt_tokens` (= `prompt.tokens.size()`, which includes generated tokens as they are appended), `n_decoded`,
  `n_remain`, `is_processing` per slot (`server-context.cpp:699-722`), so real occupancy — including idle slots holding
  purgeable warm prefixes — is readable.
* There is **no victim policy**. When the pool is exhausted the server kills both; the orchestrator can only retry.

---

## 2. KV memory management

### 2.1 What the engines do

| Topic | vLLM | SGLang | TensorRT-LLM | LMCache / offload tiers |
|---|---|---|---|---|
| Layout | paged blocks (PagedAttention paper: prior systems used "only 20.4% - 38.2% of the KV cache memory … to store the actual token states"; "vLLM improves the LLM serving throughput by 2-4×") | paged pool + radix tree over token sequences ("A radix tree … space-efficient alternative to a classical trie") | paged blocks (default 128 tokens) | chunks of 256 tokens (`LMCACHE_CHUNK_SIZE`) |
| Prefix cache | APC: "hash each kv-cache block by the tokens in the block and the tokens in the prefix before the block", parent hash + extra keys (LoRA, image hash); SHA256 default since v0.11; only **full** blocks cached ([design doc](https://docs.vllm.ai/en/latest/design/prefix_caching.html)) | RadixAttention: KV tensors on tree edges; "Each node maintains a reference counter indicating how many running requests are using it"; "a node is evictable if its reference counter is zero" (paper §3) | "KV cache state only becomes reusable after the request that computed the state terminates"; "Only full blocks can be shared" ([kv-cache-reuse](https://nvidia.github.io/TensorRT-LLM/advanced/kv-cache-reuse.html)) | prefix hits served from CPU: "LMCache hit tokens: 30, need to load: 14" ([quickstart](https://docs.lmcache.ai/getting_started/quickstart/offload_kv_cache.html)) |
| Eviction | free-block queue, LRU from the head; evicted block loses its hash | "A simple LRU eviction policy evicts the least recently used leaf first" | "prioritized LRU. All blocks are assigned a priority between 0 and 100"; `KvCacheRetentionConfig` sets priority "for a given range of tokens", reverting "to the default of 35 after … duration_ms" ([kvcache](https://nvidia.github.io/TensorRT-LLM/features/kvcache.html)) | — |
| Cache-aware scheduling | in-batch: `_get_local_prefix_cache_hit` at admission | `--schedule-policy lpm` ("longest prefix match … reorders requests to encourage more cache hits"); paper theorem: optimal hit rate "by visiting the radix tree of the requests in the depth-first search order"; in-batch dedup: "If … all those requests share the same prefix, we prefer to schedule only one of them" (`IN_BATCH_PREFIX_CACHING_*_THRESHOLD` = 32) | "launching new requests take priority over possible reuse" | — |
| CPU/disk offload | `--swap-space` (V0 swap preemption), `--cpu-offload-gb` (weights, not KV), `KVTransferConfig(kv_connector="LMCacheConnectorV1")` | HiCache (GPU→host→storage; doc page did not render, not quoted) ; PD-decode retraction backs KV up to host (`backup_kv_cache`) | "Before a block is evicted from GPU memory, it can optionally be offloaded to host (CPU) memory" (`host_cache_size`, default 0; `secondary_offload_min_priority`) | `LMCACHE_LOCAL_CPU=True`, `LMCACHE_MAX_LOCAL_CPU_SIZE` (GB); "Speedup (first run / second run): 7.43x" on repeated prefixes |

### 2.2 What we have

| Capability | llama-server v10 | Orchestrator |
|---|---|---|
| Layout | one contiguous cell array per stream; unified = `n_stream 1`, `split_simple` (`src/llama-kv-cache.cpp:85, 716`). **No paging.** Fragmentation is handled by `llama_memory` defrag, not by blocks | — |
| Prefix reuse inside a slot | `cache_prompt` → `get_common_prefix` (`:3320`); `--cache-reuse N` reuses non-prefix chunks by KV shifting (help: "min chunk size to attempt reusing from the cache via KV shifting", default 0) — **disabled when `!llama_memory_can_shift`** (`:1292-1300`), which is the case for the recurrent/hybrid contexts (**inferred**: GDN hybrids cannot shift; the WARN "cache_reuse is not supported by this context" would appear in the launch block) | `PrefixRouter` pins `id_slot` per prefix hash with a private LRU (`src/inference/prefix_cache.py:135-330`), one router per physical URL since KV-0b (2026-08-20) |
| Cross-slot / cross-request reuse | `--slot-prompt-similarity` (default 0.10): pick the idle slot with the best LCP (`get_available_slot`, `:1601-1655`) — the engine's own "cache-aware slot pick" | `PrefixRouter` overrides it by sending `id_slot`; `_should_bypass_slot_routing` exists for the frontdoor REPL |
| RAM tier | `--cache-ram` (default **8192 MiB**, `common.h:635`; `-1` unlimited, `0` off) holds whole-prompt states (`server_prompt_cache`), loaded by LCP on a new task (`:1686-1702`); `--cache-idle-slots` (default on) saves idle slots on every new task and, **under unified KV, clears them** (`:2468-2482`, `TAG_IDLE_SLOT_CLEAR`). **Eviction is FIFO** ("removing oldest entry", `states.pop_front()`, `server-task.cpp:1834-1850`), not LRU, and the token limit is `n_ctx` with a dynamic bump when bytes allow | registry `cache_ram: null` on every launch record (`orchestration/derived/stack_priors.yaml`), so every server runs the 8192 MiB default; the compiler already plumbs `cache_ram` (`stack_priors.py:1510-1512, :2334`) |
| Disk tier | `--slot-save-path` + `POST /slots/{id}?action=save|restore|erase` (on argv for :8070 and :8083) | `concurrency_aware.py:148,177` uses it for KV **migration**; `CachingBackend.save_hot_prefixes/restore_hot_prefixes` (`prefix_cache.py:508-640`) — filename bug fixed 2026-08-20 (KV-0a), integration never proven live (`attention-matching-kv-compaction.md:277-311`) |
| Context checkpoints | `--ctx-checkpoints` (default 32, `--checkpoint-min-step`), PR 15293: checkpoints of SWA/recurrent state so a prompt can be resumed from a checkpoint instead of re-prefilling; also used by speculative decoding (`:1332`, `:2365-2410`) | nothing reads them; they are how the hybrids get *any* partial-prefix reuse |
| Eviction/purge policy | `try_clear_idle_slots`: first idle slot with tokens, no LRU (source TODO) | — |
| KV compaction (local) | `server_task_result_slot_compact` (`expected_attention` scorer, `reclaim_mode position_compaction|evict_only_gapped`, `server-task.cpp:1610-1619`) — the attention-matching KV compaction patch is in the v10 tree | owned by `handoffs/active/attention-matching-kv-compaction.md` |

### 2.3 Gap

* We already ship a three-tier cache (VRAM/RAM slot state → `--cache-ram` → `--slot-save-path`) but nobody sized it.
  8192 MiB on :8083 holds ~1.25 full-pool prompts (attention KV at 196 608 cells q8_0 = 6528 MiB, + 2693 MiB recurrent
  state per saved prompt — so **one** unified-pool prompt is ~9.2 GiB and does not fit in the default cache at all
  (**inferred** from the :8083 buffer lines; the prompt-cache entry stores the sequence's KV + RS; whether RS is
  included per entry is not verified here). The idle-slot save under kvu (§4.4 of the package) is therefore likely a
  no-op for long prompts until `cache_ram` is raised.
* The engine's own LCP slot pick and the orchestrator's `PrefixRouter` compete; under kvu the server clears idle slots
  anyway, so pinning `id_slot` buys nothing on :8083 and the RAM tier is what actually preserves the prefix.
* No LRU anywhere on the eviction side (FIFO prompt cache, first-idle purge). Not fixable on the frozen kernel; can
  be partially compensated by cache size and by the orchestrator saving hot prefixes to disk.

---

## 3. Long-context handling

| Engine | Global limit | Per-request check | Reject vs truncate | What the client sees |
|---|---|---|---|---|
| vLLM | `--max-model-len` ("Model context length (prompt and output)") | `token_num >= max_model_len` **and** `token_num + max_tokens > max_model_len` (`serving_engine.py` v0.10.2 l.674-688) | reject; opt-in `truncate_prompt_tokens` extra param; Responses-API `truncation: "auto"` was a 400 not a truncate (issue #38132) | HTTP 400: "This model's maximum context length is N tokens. However, your request has M input tokens…" / "'max_tokens' … is too large: X. This model's maximum context length is N tokens and your request has M input tokens (X > N - M)". Queue overflow → **503** (`max_num_queued_reqs`: "new requests are rejected with HTTP 503 so the client can retry on another instance", `config/scheduler.py` l.93-97) |
| SGLang | `--context-length` | in `PrefillAdder` against `rem_total_tokens` | reject (auto-truncate is an opt-in flag; not on the page read) | retraction → transparent re-prefill; "Out of memory even after retracting all other requests … Aborting the last request" → HTTP 500 |
| TGI | `--max-total-tokens` (prompt + `max_new_tokens`), `--max-input-tokens` | router-side validation with tokenizer workers (`--validation-workers`) | reject | 422 validation error (**inferred** from TGI router behaviour; not quoted from the launcher page) |
| llama-server v10 | `-c` (pool) / `-c ÷ -np` per slot; **`--kv-unified` makes per-slot = `-c`** | `n_prompt >= slot.n_ctx` → 400 `exceed_context_size_error` (`:3303-3310`); **`max_tokens` is not checked** — with `ctx_shift` off (default, `common.h:578`) generation stops at `n_ctx - 1` with `truncated = true` (`:1929-1931`) | reject prompt / **silently truncate generation** | 400 body `{"code":400,"message":"request (N tokens) exceeds the available context size (C tokens), try increasing it","type":"exceed_context_size_error"}`; pool exhaustion → per-request error "Context size has been exceeded." (`:3759-3763`) on **every** in-flight request |
| Orchestrator branch | `ContextLimitResolver` reads `/props` (`default_generation_settings.n_ctx`, `total_slots`; `kv_unified` is **not** exposed by v10, inferred from registry) | `ContextLimit.fits(prompt, max_new) = prompt + max_new < n_ctx` (`context_limits.py`) — stricter than the server, matches vLLM | reject/reroute, never truncate ("Nothing here truncates a prompt") | 413 (too large for the role) or 503 + `Retry-After` (pool stayed exhausted); typed SSE error event when streaming |

Gap: the orchestrator knows the arithmetic but does not yet **clamp `max_tokens`** to `n_ctx - prompt` before
dispatch, so a request that fits the prompt but not the generation is dispatched and comes back `finish_reason:
length` (DS41 run 8's failure shape under split KV). vLLM refuses that request; TGI's `max_total_tokens` budget refuses
it; we should at minimum clamp-and-annotate.

---

## 4. Technique matrix — have / how / benefit / cost

Workloads referenced: **P** = agentic long-context planner calls on :8083 (DS41 autokernel planner, opencode direct);
**A** = many aliased roles on :8070 (frontdoor + 5 workers, `-np 4`, 65 536/slot); **S** = shared :8083 (architect_general
+ coder_escalation + ingest_long_context, about to become one 196 608 pool).

| # | Technique (origin) | Have? | How to get it | Benefit | Cost |
|---|---|---|---|---|---|
| T1 | Token-budget admission against the pool (vLLM `allocate_slots`, SGLang `rem_total_tokens`, TGI `max_batch_total_tokens`) | **orchestrator: yes (branch)** — own reservations only | keep; extend with T2/T3 | S: no more abort-all from orchestrator-admitted traffic | done |
| T2 | Admit against **actual** occupancy (all engines: they own the pool) | no — branch counts only its own tickets | `ContextLimitResolver`/`SharedKVPoolAdmission._fits`: subtract `Σ n_prompt_tokens` over `is_processing` slots from `GET /slots` (idle slots' tokens are purgeable, count them as free); cache 1–2 s; on `/slots` failure fall back to own tickets | P/S: covers opencode→:8083 and any bypassing client; turns the "estimate error" fallback into a measured input | one `/slots` GET per admission under contention (server-side `/slots` walks slots under the task queue lock — cheap) |
| T3 | Adaptive decode reservation (`new_token_ratio`, `--schedule-conservativeness`) | no — branch reserves full `max_tokens` | `kv_pool_admission`: `reserve = prompt_est + ceil(max_new × ratio)`; ratio starts 1.0, decays toward a floor (e.g. 0.3) per admission without incident, resets to 1.0 on any `POOL_EXHAUSTED`; env override `ORCHESTRATOR_KV_POOL_NEW_TOKEN_RATIO` | P/S: thinking calls with `max_tokens 32768` stop blocking a second 60k job on the 196k pool; queue wait falls without raising the abort risk beyond what the retry path already absorbs | small; a wrong ratio surfaces as `POOL_EXHAUSTED` events, which already have telemetry |
| T4 | Evict **one** victim and requeue (vLLM `running[-1]`, SGLang least-progress-first, TRT MAX_UTILIZATION) | **no** — kernel aborts all; source TODO at `server-context.cpp:3760` | (a) orchestrator-side: when a request is queued behind a pool that a *lower-priority / younger* in-flight request holds, cancel that request (close the stream — `SERVER_TASK_TYPE_CANCEL` releases the slot) and requeue it at the head; (b) kernel-side: implement the TODO on an experimental branch for v11 — **not now** | P: a planner call is never lost to a background ingest job; S: turns abort-all into one recompute | (a) needs a cancellable in-flight registry keyed by URL, idempotent requeue with the same request id, and a priority field on requests; recompute cost = victim's prefill (RAM tier makes it a restore if `cache_ram` holds it). (b) is kernel research — barred by standing rule until champion consolidation |
| T5 | Bounded queue → fast 503 (vLLM `max_num_queued_reqs`, TGI `max_concurrent_requests`, SGLang `--max-queued-requests`) | partial — wait bounded by deadline / 1800 s, depth unbounded | `SharedKVPoolAdmission.acquire`: `ORCHESTRATOR_KV_POOL_MAX_QUEUED` per URL; over the cap → immediate 503 + `Retry-After` (the API path already emits it) | S: opencode and agents get a retryable answer in ms instead of a 30-minute silent wait | trivial |
| T6 | Clamp / reject `max_tokens` against `n_ctx - prompt` (vLLM `_validate_input`, TGI `max_total_tokens`) | partial — `fits()` exists, not enforced pre-dispatch | `inference.py` before dispatch: if `prompt + max_new >= n_ctx` and the request is not reroutable, set `max_tokens = n_ctx - prompt - margin`, annotate `completion_reason=context_limit` (already a field) | P: no more surprise `finish_reason: length` on planner calls; makes the `-kvu` "advertise 196608 to opencode" step safe | trivial |
| T7 | Advertise the limit to clients (vLLM `/v1/models` `max_model_len`) | no — N-3 in the package hand-edits opencode's `limit.context` | `openai_compat.py` `/v1/models`: add `context_length`/`max_model_len` from `ContextLimitResolver` per role | P: opencode compacts against the live value; removes the manual N-3 step and its rollback | trivial; opencode still reads config only at start (its limitation) |
| T8 | Size the host KV tier deliberately (TRT `host_cache_size`, LMCache `MAX_LOCAL_CPU_SIZE`, vLLM `swap_space`) | have the mechanism (`--cache-ram` 8192 MiB default, `--cache-idle-slots` on), never sized | registry `serving_shape.cache_ram` per role → `-cram` (already compiled by `stack_priors.py:2334`); :8083 → ≥ 24 576 MiB (two full-pool prompts + RS); :8070 → sized for 4–6 warm alias prefixes; host budget is 1069 GiB with 233 GiB required (package §4.1) | S: the kvu idle-slot clear becomes a *restore from RAM* instead of a re-prefill; A: six aliases stop evicting each other's prefixes through the FIFO cache | RAM only; FIFO eviction means size is the only knob |
| T9 | Cache-aware ordering / in-batch prefix dedup (SGLang LPM + `IN_BATCH_PREFIX_CACHING_*`) | server: LCP slot pick (`--slot-prompt-similarity 0.1`); orchestrator: `PrefixRouter` pins slots | On kvu servers stop pinning `id_slot` (let the server's LCP pick + RAM cache do the work); in the admission queue, when >1 waiter, prefer the waiter whose prefix hash matches an in-flight/idle slot's prompt (FCFS with a bounded LPM bypass, e.g. at most one skip per waiter to preserve the no-starvation property) | A: fewer re-prefills across the six :8070 aliases; S: back-to-back planner turns hit the warm prefix | modest; the fairness bound must be kept (the branch's FCFS invariant is load-bearing) |
| T10 | Long-prefill fairness (`long_prefill_token_threshold`, TGI `waiting_served_ratio`) | server: `n_batch` chunking only | not feasible per-slot on the frozen kernel; orchestrator can only serialise (T1) | low for P (single planner); some for A | — |
| T11 | Paged KV / block sharing (PagedAttention) | **no**, not feasible on llama-server (single cell array per stream) | — | — | — |
| T12 | Swap-preemption to CPU (vLLM V0 `--swap-space`, SGLang decode backup) | closest analog: `/slots/{id}?action=save` (disk) — a **pre**-emption tool, not an in-batch one; migration only (`concurrency_aware.py`) | for T4(a), save the victim's slot to `--slot-save-path` before cancelling so requeue restores instead of re-prefilling | P/S: recompute cost → file restore | save of a 120k-token slot on the 27B ≈ 9 GiB write (**inferred** from buffer sizes); only worth it above a prefix-length threshold |
| T13 | Prioritized block retention (TRT `KvCacheRetentionConfig`) | no; nearest is the orchestrator choosing which prefixes to `save_hot_prefixes` | keep as a policy input to T8/T9 (which prefixes get pinned to disk) | A | not feasible in-engine |
| T14 | Recurrent-state checkpoints for partial reuse (llama.cpp-specific, PR 15293) | **yes** (`--ctx-checkpoints 32` default) | verify at kvu bring-up that checkpoints are created on :8083 (`-lv 4` prints "created context checkpoint"); tune `--checkpoint-min-step` if the 32-checkpoint window is spent on speculative rounds | P: partial-prefix reuse on the hybrids where `cache_reuse` is disabled | none |

---

## 5. Ranked steal list

Landing spots are in the orchestrator unless stated; "branch" = `feat/context-overflow-handling-20260924`.

1. **T2 — Admit against real `/slots` occupancy, not just own tickets.** `src/scheduling/kv_pool_admission.py`
   (`_fits`) + `src/backends/context_limits.py` (a `pool_occupancy(url)` reader with a 1–2 s TTL). **Branch** — it is
   the branch's own stated blind spot (opencode → :8083 direct) and the kvu bring-up proof 6 ("a concurrent planner
   call could exhaust the pool") is exactly this case.
2. **T3 — Adaptive decode reservation (`new_token_ratio`).** `kv_pool_admission.py` (ratio state per URL, reset on
   `POOL_EXHAUSTED` reported from `context_recovery.py`). **Branch** — without it the FCFS queue over-serialises the
   thinking-mode planner on S.
3. **T6 + T7 — Clamp `max_tokens` pre-dispatch and advertise `context_length` on `/v1/models`.**
   `src/llm_primitives/inference.py` (clamp, annotate `completion_reason=context_limit`) and
   `src/api/routes/openai_compat.py` (models endpoint). **Branch** — both are arithmetic the branch already computes;
   T7 retires package step N-3.
4. **T8 — Size `cache_ram` per server in the registry.** `epyc-inference-research/orchestration/model_registry.yaml`
   `serving_shape.cache_ram` for architect_general (≥ 24 576 MiB) and frontdoor (sized for the alias set) → compiled
   by `stack_priors.py:2334` → `-cram`. **New stack-change task** (it changes launch argv; do not fold into the signed
   kvu package — but land it at the same :8083 reload boundary if the operator agrees, since a second reload costs a
   planner transient).
5. **T5 — Bounded per-server queue with fast 503.** `kv_pool_admission.py` (`ORCHESTRATOR_KV_POOL_MAX_QUEUED`).
   **Branch**, one-line semantics, already has the 503 + `Retry-After` path.
6. **T4(a) — Orchestrator-side preemption: cancel the youngest/lowest-priority in-flight request and requeue it, optionally
   after a `/slots/{id}?action=save`.** New module `src/scheduling/kv_pool_preemption.py` + a priority field threaded
   from the API/graph layer + cancel hooks in `src/backends/llama_server.py`. **New task** (needs a cancellable in-flight
   registry and idempotent requeue; must be designed against the FCFS no-starvation invariant). This is the only item
   that turns "abort-all" into "one recompute" without touching the kernel.
7. **T9 — Cache-aware ordering: stop pinning `id_slot` on kvu servers; bounded LPM bypass in the admission queue.**
   `src/inference/prefix_cache.py` (`_should_bypass_slot_routing` gains a per-URL `kv_unified` condition from
   `ContextLimitResolver`) and `kv_pool_admission.py`. **New task**, and it belongs under the existing prefix-cache
   ownership row (`handoffs/active/attention-matching-kv-compaction.md` KV-1..), not under overflow.
8. **T14 — Verify context checkpoints are live on :8083 at kvu bring-up** (log line `created context checkpoint`, `-lv 4`).
   No code; add to the package's §6 serving proof as a read. **Fold into the kvu bring-up checklist.**

**Explicitly not stolen now**: T11 paged KV (not feasible on llama-server); T4(b) kernel-side single-slot eviction
(the upstream TODO — a v11 experimental-branch candidate, blocked by the standing "no kernel research until champion
consolidation" rule; the operator decides when that reopens); T10 per-step long-prefill caps (no lever on the frozen
kernel); T13 in-engine priority retention.

---

## 6. Prior intake (do not re-ingest)

Cited with `#record` because this report discusses the entries and asserts nothing from them:

* intake-033#record — PagedAttention paper (block layout, swap vs recompute, FCFS all-or-nothing eviction).
* intake-041#record — SGLang paper (RadixAttention, LRU leaf eviction, LPM/DFS scheduling).
* intake-461#record, intake-462#record, intake-463#record — SGLang, vLLM, TensorRT-LLM repos (2026-04-26 GPU-curriculum
  batch; recorded as "DGX-Spark-prep references; none are actionable on current CPU stack" — this audit is the first
  time their *scheduling* patterns are read against the orchestrator rather than the kernel).
* intake-469#record — Sarathi (chunked prefill piggybacking decodes).
* intake-490#record — SGLang hybrid Mamba+attention slot promotion (why hybrids pay GDN rows per slot; consistent with
  the package's per-slot RS cost).
* intake-1182#record — Unified Radix Cache for hybrid-model prefix caching (relevant to T14: partial prefix reuse on
  GDN models is checkpoint-shaped, not block-shaped).
* intake-1196#record (KVFlow, dive-overturned) and intake-1207#record (SGLang Rust tree-core cluster) — already
  evaluated for the orchestrator prefix-cache path (`attention-matching-kv-compaction.md:277-311`), verdict
  `adopt_patterns`; T9 is the surviving actionable piece.
* intake-656#record — vLLM v0.22.0 release notes (multi-tier KV offloading).

New primary sources read for this audit (not in the index; candidates for a Stage-1 sweep if the operator wants
them recorded): vLLM v1 `scheduler.py` and `config/scheduler.py` (main), vLLM prefix-caching design doc, vLLM
optimization doc, SGLang `schedule_batch.py` / `schedule_policy.py` / `scheduler.py` (main), SGLang server-args and
hyperparameter-tuning docs, TGI launcher reference, TensorRT-LLM `executor/types.h` and kvcache/kv-cache-reuse docs,
LMDeploy TurboMind config doc, LMCache offload quickstart.

**Belief-kernel note**: this audit produces no measurements. The kvu bring-up readings (M-1/M-2 in the package) are
the measurements; their claim tuple is already prepared by SSU-F3.

---

## 7. Source index

* Frozen tree `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82`: `tools/server/server-context.cpp` (`:1292-1300` shift/reuse
  disable, `:1416-1434` prompt cache + checkpoints init, `:1485-1495` idle-slot policy, `:1601-1655` LCP slot pick,
  `:1686-1702` cache load, `:1712-1735` `try_clear_idle_slots`, `:1929-1931` truncation, `:2365-2410` checkpoints,
  `:2468-2482` idle-slot save/clear, `:3303-3310` admission 400, `:3320` common prefix, `:3759-3801` abort-all + batch
  halving, `:699-722` `/slots` JSON, `:4878-4895` `/props`); `tools/server/server-task.cpp:1834-1860` FIFO eviction,
  `:1610-1619` slot compact; `common/arg.cpp:1516-1560, 3345-3360, 3550-3555, 1562-1567`; `common/common.h:578, 630-635, 692`.
* Orchestrator worktree `/mnt/raid0/llm/tmp/orch-ctx-overflow-20260924` @ `fca70439`: `src/scheduling/kv_pool_admission.py`,
  `src/backends/context_limits.py`, `src/backends/context_overflow.py`, `src/llm_primitives/context_recovery.py`,
  `src/llm_primitives/inference.py:110-115, 931-960, 1321-1324`, `src/api/routes/openai_compat.py:955-1003, 1372-1381`.
* Live: `/proc/3343847/cmdline` (:8083), `/proc/2020119/cmdline` (:8070); `orchestration/derived/stack_priors.yaml`
  (`cache_ram: null` ×13).
* vLLM: https://docs.vllm.ai/en/latest/design/prefix_caching.html · https://docs.vllm.ai/en/stable/configuration/optimization/ ·
  https://docs.vllm.ai/en/latest/configuration/engine_args.html · https://github.com/vllm-project/vllm/blob/main/vllm/v1/core/sched/scheduler.py ·
  https://github.com/vllm-project/vllm/blob/main/vllm/config/scheduler.py · https://github.com/vllm-project/vllm/blob/v0.10.2/vllm/entrypoints/openai/serving_engine.py ·
  https://arxiv.org/abs/2309.06180 (via ar5iv) · https://github.com/vllm-project/vllm/issues/38132
* SGLang: https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/managers/schedule_batch.py ·
  https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/managers/schedule_policy.py ·
  https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/managers/scheduler.py ·
  https://docs.sglang.io/advanced_features/hyperparameter_tuning.html · https://docs.sglang.io/advanced_features/server_arguments.html ·
  https://arxiv.org/abs/2312.07104 (via ar5iv)
* TGI: https://huggingface.co/docs/text-generation-inference/en/reference/launcher
* TensorRT-LLM: https://github.com/NVIDIA/TensorRT-LLM/blob/main/cpp/include/tensorrt_llm/executor/types.h ·
  https://nvidia.github.io/TensorRT-LLM/features/kvcache.html · https://nvidia.github.io/TensorRT-LLM/advanced/kv-cache-reuse.html ·
  https://nvidia.github.io/TensorRT-LLM/features/paged-attention-ifb-scheduler.html
* LMDeploy: https://lmdeploy.readthedocs.io/en/latest/inference/turbomind_config.html
* LMCache: https://docs.lmcache.ai/getting_started/quickstart/offload_kv_cache.html
