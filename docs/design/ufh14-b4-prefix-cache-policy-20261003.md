# UFH14-B4 — prefix-cache and `--cache-ram` policy per llama-server (design)

2026-10-03 · workspace-ec subagent · handoff `agentic-serving-harness-fixes.md` UFH14-B4 (D5, D6 server side).

> Durable copy (2026-10-03 wrap-up) of `/mnt/raid0/llm/tmp/ufh14-b4-ec/DESIGN.md`. Implementation: orch 61873d75, acb5a816,
> 1c3f8e77, c14a098d, 8f354ac3, integrated on `integ/api-reload-2-ec` 10bc5681 (not deployed at copy time). Remaining work
> is tracked as UFH14-B4a…h in `handoffs/active/agentic-serving-harness-fixes.md`.

**How this was produced.** Read-only. Sources: the frozen v10 tree `/mnt/raid0/llm/llama.cpp` at `ffc1bac82` (clean tracked
state), live argv from `/proc/<pid>/cmdline` via `ss -ltnp`, read-only `GET /props` and `GET /slots`, `/proc/<pid>/numa_maps`,
the per-node meminfo, the server logs under `epyc-orchestrator/logs/`, and the orchestrator at `origin/main@841935ea`
(worktree `/mnt/raid0/llm/worktrees/orch-b4-ec`). No process was started, stopped or reloaded and no inference was sent.

Provenance tags: **[M]** measured (source given) · **[S]** read from source (file:line) · **[D]** derived (arithmetic given).
llama.cpp citations are `tools/server/…` / `common/…` / `src/…` in the frozen tree.

---

## 1. Mechanism — how llama-server v10 decides reuse vs eviction

### 1.1 Two tiers, not one

| tier | where | bounded by | holds |
|---|---|---|---|
| **slot KV** | VRAM (GPU) or anonymous RAM (CPU) — the `-c` pool | `-c` (unified) or `-c/np` per slot (split) | the live prompt of each slot (`slot.prompt.tokens` + checkpoints) |
| **prompt cache** (`--cache-ram`) | **host RAM, heap** (`std::vector<uint8_t>` per entry, `server-task.cpp:1724-1727`) under the process's NUMA policy | `--cache-ram` MiB (`server_prompt_cache(limit_size_mib, n_ctx)`, `server-context.cpp:1416-1424`; default **8192**, `common/common.h:635`; `-1` = no limit, `0` = off) | full serialized sequence states of prompts that left a slot |

`--cache-ram` is **host RAM, not VRAM** [S]. It is allocated on demand, is not mlocked (the CPU servers' `--mlock`
covers the weights), and follows the process memory policy: on :8083 that is **`bind:3`** [M, `/proc/3793153/numa_maps`],
so the 27B's prompt cache competes for **NUMA node 3** only (283 GiB, 47 GiB free + ~107 GiB file pages at sampling) — not for
the host's 1133 GiB.

### 1.2 Slot selection (`get_available_slot`, `server-context.cpp:1601-1708`)

1. **`id_slot` pinned** (`task.id_slot != -1`, parsed at `:4449` from the request body, default −1): that slot is the
   candidate (`:1607-1612`). If it is busy the task is **deferred** (`:2444-2449`) — the server never falls back to another
   free slot. An id ≥ np **wraps around** (`id % np`, `get_slot_by_id`, `:1574-1585`), so a client that assumes the wrong
   `np` still pins — to a slot it did not intend — and the LCP pass then skips every slot (it compares the unwrapped id).
2. **LCP similarity** (`:1615-1659`): among idle slots holding tokens, pick the one maximizing
   `lcp / len(new prompt)` above `--slot-prompt-similarity` (default **0.1**, `common/common.h:692`). If the chosen slot would
   keep < 50% of its own content (`f_keep < 0.5`), set `update_cache`.
3. **LRU** (`:1662-1682`): otherwise the least-recently-used idle slot; **always** sets `update_cache`.
4. **Cache update** (`:1685-1705`, completion tasks only): `prompt_save` the chosen slot's current content into the RAM
   cache, then `prompt_load` the **best cache entry** for the new prompt into that slot; if the load fails, `prompt_clear`
   (cold).

### 1.3 What the RAM cache is: a move-semantics LRU of whole states (`server-task.cpp:1677-1866`)

- **Entry = one complete sequence state**: `llama_state_seq_get_data_ext` of target + draft context, plus the slot's
  context checkpoints (`server_prompt_cache_state::size`, `server-task.h:641-654`). **No prefix sharing**: four arms on the
  same 46k context are four full copies.
- **alloc** (`:1677-1757`): skip if the prompt is already fully contained in an entry; skip if the single entry exceeds the
  limit ("exceeds cache size limit"); **delete every entry that is a full prefix of the new one** ("obsolete"); then evict
  **oldest-first** ("making room for prompt cache entry, removing oldest entry") until it fits. On `bad_alloc` the limit is
  cut to 40% of current size.
- **load** (`:1759-1832`): choose the entry maximizing both `f_keep = lcp/len(entry)` and `sim = lcp/len(new)`; an entry with
  **`f_keep < 0.25` is never used** ("don't trash large prompts", `:1775-1778`). A successful load **moves the entry out of the
  cache** (`states.erase(it_best)`, `:1829`) — it is single-use until re-saved.
- **update** (`:1834-1866`): oldest-first eviction to the byte limit; the token limit (`n_ctx`) is raised dynamically to
  `limit_size / bytes_per_token`, so in practice **only the byte limit binds**.
- Recency = insertion order; a loaded-then-resaved entry goes to the back, so eviction is effectively **LRU by last use**.

### 1.4 Unified KV turns the RAM cache into THE prefix store (`--cache-idle-slots`, default ON)

`common/common.h:632`, `server-context.cpp:1485-1500` and `:2469-2484`: **after every task launch**, every idle slot is
saved to the RAM cache, and **under `--kv-unified` it is also cleared from the pool** (`[TAG_IDLE_SLOT_CLEAR]`). Without
unified KV the idle slot keeps its KV and only a RAM *copy* is published.

Consequences on :8083 (unified, np 4):
- An idle conversation survives **only** in the RAM cache once any other task starts. Slot affinity (`id_slot`, LCP) cannot
  keep it in VRAM — every return trip is a cache load.
- Every launch publishes up to np−1 copies → high insertion rate → the 1985 "removing oldest entry" lines in the 8083 log
  (929 inside the 09-24→10-01 window of the prefill-share review).

### 1.5 Hybrid / recurrent models: prefix reuse is quantized to checkpoints

Every LLM server in the live stack is a **hybrid attention + Gated-DeltaNet** model [M, GGUF metadata]:
Qwen3.8-27B (`qwen35`, 16/64 attention layers), Qwen3.6-35B-A3B (`qwen35moe`, `full_attention_interval 4`),
Qwen3.8-Flash-Next (`qwen4exp`, `full_attention_interval 4`). The recurrent state holds only the **last** position, so it
cannot be truncated to an arbitrary common prefix:

- `server-context.cpp:3404-3480`: when the reusable prefix ends **before** the end of the held/loaded prompt
  (`pos_min >= pos_min_thold`), the server restores the newest **context checkpoint** at or before the divergence; if none
  qualifies it logs **"forcing full prompt re-processing due to lack of cache data (likely due to SWA or hybrid/recurrent
  memory)"** and restarts from token 0. [M] 8083 log: 251 checkpoint restores, 32 forced full re-processes.
- **Where checkpoints exist** (`:3562-3726`, `create_checkpoint` `:2365-2416`): only for completion tasks; at the start of
  user messages **when the request carries `message_delimiters`** — which only the OpenAI chat conversion sets
  (`server-common.cpp:1116`), **not raw `/completion`**; no closer than `--checkpoint-min-step` (default **8192**,
  `common.h:634`) except the last user message; and at **4 + n_ubatch** and **4** tokens before the prompt end. At most
  `--ctx-checkpoints` (default **32**) per slot, oldest erased first.
- Checkpoint size = one partial (recurrent-only) state: **~150 MiB on the 27B** [M, "created context checkpoint … size =
  150.2–152.3 MiB"], ~2× the per-state figure below for the others [D].

So on these models: **append-only growth reuses everything; any edit before the tail costs a re-prefill back to the
previous checkpoint, and on raw `/completion` that is usually token 0.**

### 1.6 Entry cost — measured on :8083 (MTP era, same GGUF and K/V types)

[M] 489 `prompt_save` lines (`saving prompt with length L, total state size = X MiB (draft: Y MiB)`), exact linear fit, max
error 0.0 MiB:

```
state(L)  = 149.6 MiB  +  38,960 B × L        (target 34,816 B/tok q8_0 KV + MTP draft 4,120 B/tok + ~24 B cell meta)
entry(L)  = state(L)  +  k(L) × ~152 MiB      (k = checkpoints carried)
```

[M] 6538 cache-state lines (`- prompt …: N tokens, checkpoints: k, S MiB`), np 4 unified launch: mean k ≈ 1.3 (<2k tok),
4.0 (2–16k), 4.5 (16–49k), 6.3 (49–98k), 11.3 (≥98k); median entry 2.4 GiB at 16–49k, 4.7 GiB at 49–98k, 8.8 GiB above.
**Effective cost ≈ 70–80 MiB per 1k cached tokens** for agentic-length prompts — about **2×** the raw KV rate, because the
recurrent state and checkpoints are carried per entry. At 65536 MiB the cache held **14–18 entries** in steady state.

Small prompts are dominated by the fixed part: a 120-token prompt with one checkpoint costs **304 MiB** [M]. That is why
the CPU frontdoor's 32 GiB cache churns (1526 evictions on :8070, median evicted entry 261 MiB) while holding almost
nothing that is expensive to recompute.

### 1.7 State-restore failures — what they are

[M] All 5 in the 8083 log have the same shape (line 44333; 198881; 199123; 199851; 202211):

```
get_availabl: id 0 | selected slot by LRU …
load: - found better prompt with f_keep = 0.991, sim = 1.000
state_read_meta: failed to find 28622 available cells in kv cache
state_seq_set_data: error loading state: failed to restore kv cache
load: failed to restore state with size 1154085244
prompt_load: failed to load prompt from cache   → prompt_clear → cold prefill
```

Mechanism [S]: `prompt_load` runs inside `get_available_slot`, **before** the launch that clears idle slots
(`:2469-2484`) and without calling `try_clear_idle_slots()` (`:1710-1735`). Restoring a cached state needs that many **free
cells in the unified pool now** (`state_read_meta` → find_slot). In the first case slot 1 had just released 168,953 tokens and
still held them, so 196,608 − 168,953 = 27,655 < 28,622 cells were free. The entry stays in the cache (it is only erased on
success, `:1829`), but this request pays a full cold prefill **of a prompt that was 99% cached**. It is a pool-occupancy
problem at the moment of selection, fixed by pool headroom (B3: `-c` 393216) and not by `--cache-ram`.

### 1.8 `cache_prompt`, `--cache-reuse`, slot save/restore

- **`cache_prompt`**: per-request bool, default = server `--cache-prompt` = **true** (`server-task.h:55`,
  `server-schema.cpp:31,519`, `common.h:631`). False forces `n_past = 0` (`:3388-3391`) — a full re-prefill and no reuse.
- **`--cache-reuse N` / `n_cache_reuse`** (KV-shift chunk reuse, `:3323-3386`, default 0, `common.h:630`): enabled only
  when `llama_memory_can_shift` and no multimodal (`:1286-1302`, `:3325-3327`). The hybrid memory reports
  `can_shift = mem_attn->get_can_shift()` (`src/llama-memory-hybrid.cpp:133-136`), i.e. **true** — the server would accept it
  on our hybrids. But the recurrent state is not recomputed for shifted chunks: after a shift the checkpoint logic either
  rolls `n_past` back to a checkpoint (voiding the reuse) or, when the shifted tail ends past the old end, continues on a
  recurrent state that summarizes **different** tokens. **On hybrid/recurrent models `--cache-reuse` must stay 0.**
  It is safe and useful only for pure-attention, non-SWA, text-only models — none are in the live LLM stack.
- **Slot save/restore** (`--slot-save-path`, `POST /slots/{id}?action=save|restore`, `:2600-2660`, `:5444-5500`):
  `llama_state_seq_save_file` of one slot to disk (tokens + state, **no checkpoints**). Restore needs free pool cells
  (same failure as §1.7) and is deferred while the slot is busy. Every live LLM server has a `--slot-save-path`, and every
  directory under `/mnt/raid0/llm/cache/kv_slots/` is empty or 4–16 KiB [M] — **nothing uses it today**. Its only value over
  the RAM cache is surviving a relaunch. Note: :8070, :8080 and :8180 share one directory (`kv_slots/frontdoor`), so a save
  from one instance can be restored into another; that is harmless only because all three serve the same GGUF.

---

## 2. Per-server settings today and what the evidence says they cost

Live argv [M, `/proc/<pid>/cmdline`, 2026-10-03 ~12:10Z]; all binaries `kernels/builds/{cpu,gpu}-20260921-ffc1bac82` (b10303).
Eviction/restore counts are over each server's **whole current log** [M]; the 09-24→10-01 window figures are from the
prefill-share review.

| port | role(s) | model (memory) | np × ctx | KV | `--cache-ram` | NUMA (heap) | cache events [M] |
|---|---|---|---|---|---|---|---|
| **:8083** | architect_critic (+coder_escalation, ingest_long_context) | Qwen3.8-27B Q8_0 (hybrid), DFlash2 d8 | 4, **unified** 196608 (B3 → 393216 pending relaunch) | q8_0 | **65536** | **bind:3** | 1985 evictions (929 in window; median evicted entry 629 MiB, p90 3.6 GiB, max 17.2 GiB); **5 restore failures**; 32 forced full re-prefills; 251 checkpoint restores; 465 "failed to find a memory slot" |
| :8070 | frontdoor (full) | Qwen3.6-35B-A3B Q8_0 (hybrid), MTP d4 | 4, split 4×65536 | q8_0 | 32768 | interleave 0-3 | 1526 evictions, median 261 MiB; 2170 LCP vs 832 LRU selections; 0 restore failures |
| :8080 / :8180 | frontdoor halves | same GGUF | 1 × 262144 | q8_0 | 32768 | interleave 0-1 / 2-3 | 828 / 608 evictions, median 137 MiB |
| :8074 | architect_general | Qwen3.8-Flash-Next UD-IQ4_XS (hybrid), MTP d4 | 1 × 262144 | f16 | 32768 | interleave 0-3 | 1703 evictions, median 233 MiB (4 "exceeds cache size limit" in an older 8192-default launch) |
| :8090-8095 | embedders | bge-large f16 (encoder) | 4 × 512 | — | unset (8192 default) | — | none; RSS ~700 MiB |

All LLM servers also carry `--slot-save-path` (unused, §1.8). None carries `--cache-reuse`, `--ctx-checkpoints`,
`--checkpoint-min-step` or `--slot-prompt-similarity`, so v10 defaults apply (0, 32, 8192, 0.1).

**What it costs, by mechanism** (8083 is the only server where prefix misses are expensive):

| cause | evidence | cost | lever |
|---|---|---|---|
| concurrent duplicates: same context prefilled by parallel arms before anything is cached | 96 near-duplicate prefills, **20.9k s** (review §2) | the cache cannot help — nothing exists yet | **A3** warm + stagger (client), and B2's one-long-prefill rule |
| restore failure: entry cached but pool full at selection time | 5 events, entries 1.1–3.2 GB (28k–82k tokens) | ~5 × 60–250 s cold prefill [D at 325–470 tok/s] | **B3** pool headroom; nothing in `--cache-ram` |
| evicted before reuse | 929 evictions in window; logged lookups found an entry only **61 / 273** times | **not separable** from "never seen" in the server log | `--cache-ram` sizing — **unproven as the binding constraint** |
| prefix edited before the tail (compaction with `tools=[]`, volatile-first prompts) | D2 (79–94k re-prefills per compaction); 32 forced full re-prefills | per compaction ≈ full context at 300–500 tok/s | **A4** + assembly rules §3.4 |
| `f_keep < 0.25` refusal: a long cached conversation is not used for a new session that shares only its head | [S] `server-task.cpp:1775-1778` | shared system/tools heads re-prefilled per new session | §3.5 (a dedicated short prefix entry, re-warmed) |

**The honest reading:** the review's "larger `--cache-ram`" is a hypothesis, not a finding. The measured costs are
dominated by duplicates (D5), pool-occupancy restore failures (D6) and prefix edits (D2), none of which a bigger RAM cache
fixes. The log cannot say how much of the remaining cold LRU time was eviction. §4.3 adds the instrument that can.

---

## 3. A model-agnostic policy

### 3.1 `--cache-ram` per server — the derivation

Implemented as a pure function: `src/registry/prefix_cache_policy.py` (branch, §4.1).

```
entry(L)  = fixed + per_token × L + k(L) × checkpoint        k(L) = min(ctx_checkpoints, 1.5 + L/12000)   (hybrid/SWA; 0 for attention)
entries   = warm_sessions + shared_prefixes + (np if split KV and anything resumes, else 0)
need      = entries × entry(p90 prompt tokens) × 1.25
cap       = server's share of its NUMA domain = (domain_total × 0.85 − resident) / prompt-cache tenants of that domain
cache_ram = clamp(round_up_4GiB(need), 8192, cap)
verdict   = keep if current ∈ [need, max(cap, 2·need)]  ·  raise if current < need  ·  lower if far above
```

- **Model fact** (`entry`): measured once per GGUF × K/V type × drafter from the server's own `prompt_save` / cache-state
  lines (they are TRC/INFO; the bring-up of any relaunch with `-lv 4` yields them). Today only the 27B MTP shape is
  measured; the others are [D] from GGUF metadata and checked against median eviction sizes (35B-A3B ≈ 63 + 63 MiB fixed ≈
  the 128 MiB p10 evicted on :8080; Flash-Next ≈ 115 + 115 ≈ the 233 MiB median on :8074).
- **Workload fact** (`warm_sessions`, `p90`): how many conversations must survive between turns. p90 comes from
  `serving_calls.jsonl` (`cache_n + prompt_n`) once B5 has a week of data; until then from the review.
- **Why the split-KV term**: with `--cache-idle-slots` (default) split servers publish a RAM *copy* of every idle slot after
  each launch, so the copies occupy cache whether or not they are ever used.
- **Why a NUMA cap, not a host cap**: the heap follows the process policy. :8083 is `bind:3`; node 3 has 283 GiB with ~111 GiB
  resident outside the 27B's own cache → cap ≈ **130 GiB** [D]. The interleaved CPU servers share ~728 GiB → ≈ 182 GiB each [D].

**Per-server result** (module output, inputs in the table):

| server | entry cost [M/D] | workload | entries | entry@p90 | need | cap | verdict |
|---|---|---|---|---|---|---|---|
| :8083 (DFlash2) | 190 MiB + 34,840 B/tok + 152 MiB/ckpt [D from M] | unified np4, 8 sessions + 2 shared, p90 86,988 | 10 | 4.31 GiB | 53.8 GiB | 130 GiB | **keep 65536** |
| :8083 under DS41-like load | same | 16 sessions + 2 shared | 18 | 4.31 GiB | 96.9 GiB | 130 GiB | raise → 102400 |
| :8074 | 115 MiB + 29.7 KB/tok + 115 MiB/ckpt [D] | np1, 3 sessions, p90 159,354 | 4 | 6.18 GiB | 30.9 GiB | 182 GiB | **keep 32768** |
| :8070 | 63 MiB + 12.0 KB/tok + 63 MiB/ckpt [D] | split np4, 16 sessions, p90 1,013 | 20 | 0.17 GiB | 4.3 GiB | 182 GiB | **keep 32768** (over-provisioned, harmless) |
| :8080 / :8180 | same | np1, 4 sessions | 5 | 0.17 GiB | 1.1 GiB | 182 GiB | **keep 32768** |
| embedders | — | encoder, no resumption | — | — | — | — | out of scope (no change) |

**So the policy changes no `--cache-ram` value today.** It turns the three operator-approved literals (2026-09-24) into a
derived, re-checkable rule, and it says when to raise :8083: when the B4 metric (§4.3) shows `missed_prefill_share` above
~5% on :8083 with `concurrent_dupes` excluded, or when the planner seat returns to the 27B with ≥ 12 warm sessions.

### 3.2 Slot pinning (`id_slot`) — do NOT pin per conversation

- **Unified servers**: an idle slot is cleared after every launch (§1.4), so a pinned conversation finds an empty slot and
  goes through the same cache load as LRU. Pinning buys nothing.
- **Split servers**: the server's own LCP selection (§1.2, token-level, threshold 0.1) already returns a conversation to the
  slot that holds its prefix. Pinning can only add head-of-line blocking: a pinned task whose slot is busy is **deferred
  inside the server** (`:2444-2449`) while other slots are free.
- **Interaction with the token pool gate** (`kv_pool_admission.py`): the gate admits by tokens and FCFS and holds the
  reservation until release. A pinned request deferred inside the server holds its reservation and, if long, the
  per-server **long-prefill lease** (`:356-357`) without prefilling; the lease then expires on the rate floor
  (`tokens / 250 tok/s`, `:420-424`) rather than at first chunk, and the gate's `/slots` observation sees no prefilling
  slot. Pinning would make B2's one-long-prefill rule lie.
- **What the code did**: `CachingBackend` pinned every `/completion` call via a 256-character prefix hash
  (`src/inference/prefix_cache.py`), with one process-wide `num_slots` (default 2, `src/config/__init__.py:490`). Every
  root-LM prompt starts with the same 576-byte system prompt, so a role's calls all mapped to **one slot**. The chat lane
  never sent it (the slot was computed and dropped, yet recorded as `request.slot_id`). **Fixed on the branch**: pinning is
  opt-in (`ORCHESTRATOR_PREFIX_ROUTER_PIN_SLOTS=1`), the record says whether a slot was actually sent (`slot_id_sent`)
  and which slot the server used (`notes.server_slot`).
- **The one legitimate pin** stays: an explicit caller `slot_id` (e.g. `typed_decisions/native.py` `pin_slots`, KV
  migration in `concurrency_aware.py`) is passed through untouched.

### 3.3 `cache_prompt`

Always `true` on the wire, every lane, unless the caller overrides it. The server default is already true; sending it
explicitly removes the dependence on a launch flag (`--no-cache-prompt` would silently disable reuse) and makes the
existing `ChatRequest.cache_prompt` override work on the chat lanes, where it was dropped. **Fixed on the branch**
(`_cache_prompt()` in `llama_server.py`). Callers outside the backend layer (`worker_pool.py:855-867`,
`tools/web/research.py:709-716`) omit it and get the server default — acceptable, listed in §4.2.

### 3.4 Prefix-stable assembly — rules

Hybrid models make these rules sharper than for pure attention: any edit before the tail costs a re-prefill back to the
nearest checkpoint, and checkpoints sit only at **message boundaries** (chat lane) and at the previous prompt's tail.

| # | rule | why (mechanism) | today | action |
|---|---|---|---|---|
| R1 | Static content first, volatile last: system → tools → rules → task → state/turn → last output. | LCP is a prefix; anything volatile early invalidates everything after it. | Root-LM default puts `## Current State` ("Turn N", REPL state) **before** `## Task` (`builder.py:237`); `prefix_stable_order` exists but is off in prod (`src/features.py:236`). | API-only flag flip, but it changes model input → A/B on the eval tower first (§4.2). |
| R2 | Put the stable head in its **own message** (system), the volatile part in the user message. | Chat-lane checkpoints are created at user-message starts (`server-context.cpp:3641-3648`); a split at the stable/volatile boundary gives the server a restore point exactly there. The orchestrator sends ONE user message (`llama_server.py:728`), so the only boundary is at token ~0 and the previous prompt's tail checkpoint lies *after* any mid-prompt edit → full re-prefill on hybrids. | not done | API-only, behind a flag, with an A/B (§4.2). Largest expected win for REPL roles on all hybrids. |
| R3 | Prefer `/v1/chat/completions` for multi-turn traffic on hybrid models. | Raw `/completion` carries no `message_delimiters` (`server-common.cpp:1116` sets them only on the chat conversion), so it gets no message-boundary checkpoints. | most roles already on the chat lane | keep; note it in the role-lane SoT. |
| R4 | Tool lists: one canonical order per role, identical across turns **and** across compaction. | Tools render into the system block; reorder or `tools=[]` rewrites the head (D2). | registry insertion order (`tool_registry.py:693-720`), stable within a process; client mode forwards caller order. | A4 (client) owns compaction; orchestrator side is already stable. |
| R5 | Nothing time- or id-dependent in the head. | — | none found in system prompts (grep across prompt builders) | keep; enforced by the fingerprint metric (a head that changes every call shows as zero `c2048` repeats). |
| R6 | Never put per-query material (RAG snippets, scout blocks, CoT prefixes) before the stable head. | — | `cot_prefix + prompt` puts the CoT prefix **before** the system prompt (`graph/helpers.py:936-940`); worker RAG puts `## Reference Code` before `## Task` (`corpus_retrieval.py:739-780`). | API-only fix (move to tail) with an A/B; listed in §4.2. |
| R7 | Escalation prompts and LLMLingua compression rewrite the whole prompt — accept that they are cold. | `EscalationPrompt.to_string` starts with volatile lines (`types.py:154-169`); WS3B compression rewrites >16K-char prompts. | as is | do not generalize; escalations are rare and one-shot. |

### 3.5 Prefix warming (A3) — what v10 actually allows

- A warm request (`n_predict` 0/1, the shared context only) leaves a **short entry** S in the cache once another task
  launches. A new session whose prompt starts with S loads it with `f_keep = 1.0`.
- The load **moves** S into the slot (`states.erase`, `server-task.cpp:1829`); when that slot is later saved, S is a full
  prefix of the new entry and is deleted as **obsolete** (`:1714-1724`). **A warm entry serves one session.** Later sessions
  can still load the grown entry if `|S| / |entry| ≥ 0.25`, after which the loader truncates back to S on hybrids only if a
  checkpoint sits at S (R2 again).
- Therefore the A3 recipe that works on v10: warm S once, start arm 1, then start arms 2…N **staggered** so that each loads
  a still-short sibling (f_keep ≥ 0.25) — or re-warm S per arm. The orchestrator's `escalation_prewarmer` warms a prefix
  (`ARCHITECT_SYSTEM_PREFIX`) that no real request uses (§4.2), so it buys nothing.

### 3.6 `--cache-reuse`

**0 on every server in the stack.** All LLM servers are hybrid (§1.5): KV shifting leaves the recurrent state describing
other tokens, so it is either voided by the checkpoint rollback or wrong. The policy sets a non-zero value (256) only for a
pure-attention, non-SWA, text-only model (`cache_reuse_for()`); none is deployed. No launcher change is needed today —
the flag is never emitted, and the policy makes that a rule instead of an accident.

### 3.7 Companion knobs (declared, defaults kept)

- `--cache-idle-slots`: must stay **on** for any unified multi-slot server (it is the only way idle conversations survive).
- `--ctx-checkpoints` 32 / `--checkpoint-min-step` 8192: keep. Checkpoints are what make partial reuse possible on hybrids;
  they cost ~150 MiB each on the 27B and roughly double the per-token cache cost (§1.6). Revisit only if the metric shows
  capacity misses, by lowering `ctx_checkpoints` before raising `cache_ram`.
- `--slot-prompt-similarity` 0.1: keep.
- `--slot-save-path`: keep as is; do not build on it (delete-lens §5).

### 3.8 The stack rule — PFX-SEL-1 (proposed), shaped like DRAFT-SEL-1

One fact per **model** in the master, one selection per **server** in the topology, one writer (the compiler),
hand-carried copies refused.

**Master registry** (`epyc-inference-research/orchestration/model_registry.yaml`, `roles.<model_role>`):

```diff
   qwen38_27b_q8_local:
     ...
+    # PFX-SEL-1 (proposed 2026-10-03, UFH14-B4): what ONE llama-server prompt-cache entry costs for this
+    # model, keyed by K/V type + drafter. entry(L) = fixed + per_token*L + k(L)*checkpoint. Measured from
+    # the server's prompt_save / cache-state lines; the selection lives in stack_topology prefix_cache_selection.
+    prefix_cache:
+      memory_kind: hybrid          # GGUF qwen35: full_attention_interval 4, ssm.* -> recurrent state per entry
+      entry_cost:
+        q8_0+mtp:     {fixed_mib: 149.6, per_token_bytes: 38960, checkpoint_mib: 152,
+                       evidence: "epyc-orchestrator logs/llama-server-8083.log prompt_save fit, 489 lines, max err 0.0 MiB"}
+        q8_0+dflash2: {fixed_mib: 190, per_token_bytes: 34840, checkpoint_mib: 152, UNVALIDATED: true,
+                       evidence: "derived: target 34,816 B/tok q8_0 + DFlash SWA-2048 draft state; measure at next -lv 4 bring-up"}
   qwen36_35b_a3b_mtp_q8_local:   # frontdoor :8070/:8080/:8180
+    prefix_cache:
+      memory_kind: hybrid
+      entry_cost:
+        q8_0+mtp: {fixed_mib: 63, per_token_bytes: 11968, checkpoint_mib: 63, UNVALIDATED: true,
+                   evidence: "derived from GGUF (10 attn layers x 2 kv heads x 256, q8_0; 30 GDN layers); matches 8080 p10 evicted entry 127 MiB"}
   qwen38_flash_next_ud_iq4xs_local:   # architect_general :8074
+    prefix_cache:
+      memory_kind: hybrid
+      entry_cost:
+        f16+mtp: {fixed_mib: 115, per_token_bytes: 29700, checkpoint_mib: 115, UNVALIDATED: true,
+                  evidence: "derived from GGUF (12 attn layers f16 + indexer keys; 36 GDN layers); matches 8074 median evicted entry 233 MiB"}
```

**Orchestrator topology** (`orchestration/stack_topology.yaml`):

```diff
+# =============================================================================
+# PREFIX-CACHE SELECTION (PFX-SEL-1, proposed 2026-10-03, UFH14-B4)
+# =============================================================================
+# Which prompt-cache workload each LAUNCHING server is sized for. The compiler derives
+# runtime.flags.cache_ram (and cache_reuse, only for memory_kind: attention) from the master's
+# roles.<model>.prefix_cache.entry_cost[<kv>+<drafter>] and this selection
+# (src/registry/prefix_cache_policy.py::recommend). A selected server may NOT hand-carry cache_ram.
+# Keys are server_mode keys, never aliases. No default: an unselected server keeps its hand-carried value.
+prefix_cache_profiles:
+  agentic_long:      {headroom: 1.25}   # resumed multi-turn sessions, long contexts
+  interactive_short: {headroom: 1.25}   # short prompts; cache mostly holds fixed recurrent state
+  none:              {cache_ram: 0}     # nothing is ever resumed (embedders, one-shot vision)
+numa_memory:
+  node_total_gib: 283
+  reserve_fraction: 0.15
+prefix_cache_selection:
+  architect_critic:  {profile: agentic_long,      warm_sessions: 8,  shared_prefixes: 2, p90_prompt_tokens: 86988}
+  architect_general: {profile: agentic_long,      warm_sessions: 3,  p90_prompt_tokens: 159354}
+  frontdoor:         {profile: interactive_short, warm_sessions: 16, p90_prompt_tokens: 1013}
+  worker_vision:     {profile: none}
```

**Lean registry stamp** (compiled, like `drafter_selection`):

```yaml
prefix_cache_selection: {server: architect_critic, model_role: qwen38_27b_q8_local, cost_key: q8_0+dflash2,
                         profile: agentic_long, entries: 10, need_mib: 55091, cap_mib: 132659, verdict: keep,
                         cache_ram: 65536, cache_reuse: 0, source: stack_topology.prefix_cache_selection}
```

**Compiler/launcher code** (lands with the stack change, not before): `src/registry/prefix_cache_selection.py`
(load + resolve + project + `check_lean`, mirroring `drafter_selection.py`), a call next to `resolve_drafters` in
`registry_compiler.py:324-334`, a `("cache_reuse", "--cache-reuse", False, False)` row in
`orchestrator_stack.py:_RUNTIME_SERVING_FLAG_ARGS` (`:509-514`; emitted only when > 0), and the drift checker row in
`stack_commands.py:598`. The `frontdoor` row needs per-instance flags only if the halves are ever sized differently; today
the derivation keeps all three at 32768, so the existing role-level scalar stays valid.

---

## 4. Implementation split

### 4.1 API-only, implemented on the branch (no stack change; takes effect at `orchestrator_stack.py reload orchestrator`)

Branch `feat/ufh14-b4-prefix-cache-ec`, worktree `/mnt/raid0/llm/worktrees/orch-b4-ec`, base `origin/main@841935ea`.
Not pushed, not merged.

Commits: `61873d75` router pinning opt-in · `acb5a816` serving-record fields + chat-lane `cache_prompt` ·
`1c3f8e77` policy derivation · `c14a098d` metric report · `8f354ac3` payload byte-identity test updated for `cache_prompt`.

| change | files | behaviour change in production |
|---|---|---|
| Router slot pinning opt-in (`ORCHESTRATOR_PREFIX_ROUTER_PIN_SLOTS`, default off); explicit caller `slot_id` preserved | `src/inference/prefix_cache.py` | `/completion`-lane calls stop sending a 256-char-hash `id_slot`; the server picks the slot (LCP + cache). Chat lane: none (it never sent it). |
| `cache_prompt` on the chat lanes, honouring the per-request override | `src/backends/llama_server.py` (`_cache_prompt`, both chat payloads) | none at server defaults (already true); the `ChatRequest.cache_prompt=False` override now works on the chat lane. |
| Serving record: `result.cached_prompt_tokens` falls back to `timings.cache_n`; `request.slot_id_sent`; `notes.server_slot` (from the response `id_slot`); `request.prefix_fp` (sha256/16 of the wire prompt's first 2k/8k/32k/128k/512k characters) | `src/backends/serving_calls.py`, `src/backends/llama_server.py` | telemetry only; never affects inference (all failures swallowed, pure functions). |
| Policy derivation (pure, not wired) | `src/registry/prefix_cache_policy.py` | none until PFX-SEL-1 is compiled in. |
| Metric report | `scripts/analysis/prefix_cache_report.py` | offline. |

Tests: `tests/unit/test_prefix_cache_policy.py` (22), `test_prefix_cache_report.py` (9), `test_serving_calls_prefix_fp.py`
(17), `test_chat_lane_cache_prompt.py` (7), `test_prefix_cache.py::TestSlotPinningDefaultOff` (14 incl. parametrized).
Existing suites that exercise the pinning mode (`test_prefix_cache.py::TestCachingBackend`,
`tests/integration/test_cache_hits.py::TestPrefixRouterIntegration`, `tests/integration/test_cache_integration.py`) opt in
to `PIN_SLOTS=1` via fixtures; nothing was loosened. Related suites (every test file that touches `CachingBackend`,
`PrefixRouter`, `serving_calls`, `slot_id`, `LlamaServerBackend`, `kv_pool`): **1001 passed, 6 skipped**. Full `tests/unit` (8 workers, 180 s per-test timeout): **16,000 passed, 20 failed**;
1 was the payload byte-identity guard (updated in `8f354ac3`, now passing) and the other **18 fail identically on the base
commit `841935ea`** (`test_autokernel_enrollment.py` ×15, `test_gpu_shadow_lane_preflight`, `test_seeding_types_state`,
`test_quarter_stack_smoke` — pre-existing, unrelated to this branch); the 20th, `test_contention_device_model.py::
test_live_topology_device_map_is_consistent`, asserts `worker_vision` is a live GPU role and fails in isolation too —
it reads live topology, not code this branch touches.

### 4.2 API-only, proposed (each changes model input or admission → needs its own A/B or review before deploy)

1. **R2 stable head as a system message** on the chat lane (`_infer_chat_completions` / `_infer_stream_text_chat_completions`):
   split `request.prompt` at a builder-emitted marker (end of `## Rules`) into `[system, user]`. Gate behind a flag;
   A/B on the eval tower (quality) and on the B4 metric (`hit_tok` for REPL roles on :8070). Expected: per-turn re-prefill
   drops from the whole prompt to the volatile tail on every hybrid.
2. **R1 `prefix_stable_order` on in production** (`src/features.py:236`): same A/B; it composes with (1).
3. **R6** move `cot_prefix` (`graph/helpers.py:936-940`) and worker RAG snippets (`corpus_retrieval.py:739-780`) to the tail.
4. **Gate cache awareness** (`kv_pool_admission.py:64-66` known limit): classify "long prefill" by **expected new tokens**
   (`prompt − expected cached`) instead of whole-prompt chars/3, where expected cached comes from the deepest
   `prefix_fp` depth seen on that server within the window. Keep the token *reservation* on the whole prompt (the pool
   must hold it). Risk: a wrong guess lets two long prefills overlap — bound it by requiring the match to be on the same
   server within 10 min and capping the credit at 75%.
5. **`escalation_prewarmer`**: it warms `ARCHITECT_SYSTEM_PREFIX`, a string no real architect request contains
   (`escalation_prewarmer.py:61-65`). Either warm the real root-LM head through the chat template the role uses, or
   delete it (delete-lens, §5). Recommendation: **delete**; A3's client-side warm+stagger is the place for warming.
6. Direct callers that omit `cache_prompt` (`worker_pool.py:855-867`, `tools/web/research.py:709-716`): add it when next
   touched; they get the server default (true) meanwhile.

### 4.3 The measurement that proves it

Source: `logs/serving_calls/serving_calls.jsonl` (B5, era ST1; plus rotated shards). Instrument:
`python3 scripts/analysis/prefix_cache_report.py --split-at <deploy ISO-UTC> [--port 8083] --json <out>`.

| metric | definition | direction | role |
|---|---|---|---|
| `missed_prefill_share` | prefill seconds on calls whose prompt shared ≥ D leading chars with an earlier call to the same port within 60 min yet reused < ½·D/3 tokens, weighted by the missed fraction, ÷ all prefill seconds | **lower** | **B4 headline** (a lower bound on avoidable prefill) |
| `hit_tok` | Σ`cache_n` / Σ(`cache_n` + `prompt_n`) | higher | secondary |
| `cold_large_share` | prefill seconds of calls with `prompt_n` ≥ 8192 and `cache_n` < 1024 ÷ all prefill seconds | lower | continuity with the review (74% on :8083) |
| `concurrent_dupes` | calls whose deepest shared prefix was still in flight on the same port | lower | D5/A3 attribution — subtracted when judging `--cache-ram` |
| guard | decode tok/s (`predicted_per_second`) and `outcome` error rate per port | no regression | |

**Before/after protocol.** Before = records since B5 (2026-10-03 05:00Z) up to the API reload of this branch; after = an
equal-length window of comparable traffic. The branch adds `prefix_fp`, so `missed_prefill_share` is only defined on the
"after" side the first time: run the first comparison on `hit_tok` and `cold_large_share` per (port, role), and use
`missed_prefill_share` as the baseline for every later step (R2/R1 A/B, any `--cache-ram` change, B3's relaunch).
**Decision rule for `--cache-ram`:** raise :8083 only if `missed_prefill_share` (with `concurrent_dupes` removed) stays
> 5% across two windows of ≥ 200 calls (two-sample persistence, INVARIANTS), and the server log shows evictions in the
same window. Belief kernel: the report's per-port rows are new measurements; the write-side row belongs with B5's
`serving_calls` adapter (`scripts/vidya/adapters/README.md`) as an additional projection — flagged for the owning session.

### 4.4 Stack-change items (proposal only; one package with the operator's signature)

| item | surfaces | relaunch? |
|---|---|---|
| PFX-SEL-1 master `prefix_cache` per model (§3.8 diff) | research `orchestration/model_registry.yaml` (`roles.qwen38_27b_q8_local`, `roles.qwen36_35b_a3b_mtp_q8_local`, `roles.qwen38_flash_next_ud_iq4xs_local`) | no (values derive to today's flags) |
| PFX-SEL-1 topology `prefix_cache_selection` + profiles + `numa_memory` (§3.8 diff) | orch `orchestration/stack_topology.yaml` | no |
| Compiler + launcher + drift checker (`prefix_cache_selection.py`, `registry_compiler.py:324-334`, `orchestrator_stack.py:509-514`, `stack_commands.py:598`) | orchestrator | no — derived `cache_ram` equals today's values; `--cache-reuse` stays unemitted |
| Re-measure the 27B DFlash2 entry cost at B3's relaunch (`-lv 4` bring-up lines: `prompt_save … total state size … (draft: …)`, `created context checkpoint … size`) | B3 package bring-up step | rides on B3's relaunch |
| (only if §4.3's decision rule fires) :8083 `--cache-ram` 65536 → 102400 | `server_mode.architect_critic.cache_ram` (research registry ~`:1405`) | yes, :8083 |

**Per-server proposal diffs (today):** none change a launch flag. :8083 `cache_ram: 65536` (keep, now derived),
:8074 `32768` (keep), :8070/:8080/:8180 `32768` (keep), embedders unchanged. The diff is the rule, not the numbers.

---

## 5. Risks, and the delete-lens

**Risks**
- *Unpinning changes slot placement on the `/completion` lane.* Mitigated: the server's LCP selection is token-level and
  strictly better informed; the old pin could only coincide with it or defer behind a busy slot. Rollback is one env var.
- *Fingerprints are character-, not token-level, at fixed depths.* They under-count misses (lower bound) and can't see a
  shared prefix that diverges between two depths; `CHARS_PER_TOKEN = 3` is approximate. Acceptable for a before/after delta
  on the same traffic; not a per-call verdict.
- *Fingerprint cost.* sha256 of up to 512k characters per call (~1 ms); never on the inference path's failure path.
- *Entry costs for the CPU models and DFlash2 are [D].* The derivation's verdicts there are insensitive to ±50% error
  (need ≪ current), but :8083's "raise" threshold is not — hence the bring-up re-measure.
- *NUMA cap is a snapshot.* Page cache on node 3 is reclaimable but :8083's bind means a too-large cache can force
  reclaim or `bad_alloc` (the server then cuts its limit to 40% — `server-task.cpp:1729-1739`). The cap includes a 15%
  reserve; recompute it when node-3 tenants change.
- *Restore failures are not a `--cache-ram` problem.* If B3 is deferred, they continue regardless of this policy.

**Delete-lens — what should NOT become generic**
1. **Slot pinning (`PrefixRouter` → `id_slot`)**: delete from the generic path (done: opt-in). Keep only explicit,
   purpose-built pins (KV migration, typed-decision workers).
2. **`--slot-save-path` / `save_hot_prefixes` / `restore_hot_prefixes`**: no production caller, every directory empty,
   restores hit the same pool-occupancy failure, and they lose checkpoints (so a restored hybrid prefix cannot be
   partially reused). Do not build warming on it. Candidate for removal from the launcher in a later cleanup.
3. **`--cache-reuse`**: must not be generic — unsound on every model we run.
4. **`escalation_prewarmer`**: model-specific, warms a prefix nobody sends. Delete rather than generalize.
5. **Raising `--cache-ram` by default**: not generic. It is host-RAM on one NUMA node for the GPU lane, and the evidence does
   not show capacity as the binding cause. The rule raises it only on measured misses.
6. **`canonicalize_prompt`** (timestamp/UUID normalization for the router key): only meaningful for a client-side router;
   with pinning off it is dead weight. Do not reuse it as a prompt-stability tool (the server sees raw bytes).
7. **Embedders and `worker_vision`**: out of the policy (`none`); per-request content never repeats.
