# Unified-KV (`-kvu`) stack-wide inventory — 2026-09-24

READ-ONLY inventory. Nothing edited, no process touched. Live facts sampled 2026-09-24 ~14:00 local
(`ps`, `/proc/<pid>/cmdline`, `GET /props`, the stack's own log files). Source citations are against the
frozen production tree `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`
(`production-consolidated-v10`, binary `b10303-ffc1bac82` as every live `/props.build_info` reports),
which IS the tree behind every running binary (`kernels/builds/{cpu,gpu}-20260921-ffc1bac82`).
Anything marked **(inferred)** was not read from a log or a source line.

Registry paths: **M** = master `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`;
**L** = lean/compiled `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`;
**T** = `/mnt/raid0/llm/epyc-orchestrator/orchestration/stack_topology.yaml`;
**LM** = `/mnt/raid0/llm/epyc-orchestrator/orchestration/launch_manifest.yaml`;
**P** = `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`;
**D** = `/mnt/raid0/llm/epyc-orchestrator/stack_templates/default.yaml`.

---

## 0. The one-line answer

**Every llama-server in the live stack runs `kv_unified = 'false'`, and nothing in the orchestrator has
ever asked for anything else.** The frozen server auto-enables unified KV only when `-np` is *absent*
(`common/arg.cpp:1216` sets `n_parallel = -1` for the server example; `tools/server/server.cpp:146-151`
turns `-1` into `n_parallel = 4, kv_unified = true`). The launcher always passes `-np` explicitly
(`scripts/server/orchestrator_stack.py:826-832`), and no file in the orchestrator mentions `kvu`,
`kv-unified` or `kv_unified` at all (grep over `*.py`/`*.yaml`/`*.sh`: zero hits), so the flag never
reaches the binary and the default `common/common.h:580` (`bool kv_unified = false`) stands. The registry's
"KV IS UNIFIED" text is measurement provenance copied from a *research* launch that passed `--kv-unified`
by hand (§4) — it was never a launcher fact.

---

## 1. Live facts — every running llama-server

Log lines are the `srv load_model: initializing, n_slots = N, n_ctx_slot = C, kv_unified = 'X'` line
(`tools/server/server-context.cpp:1341-1342`) from the *last* launch block in each log. Only :8083 was
restarted at `-lv 4` (SSU-F3), so only its log also carries the `llama_context:` / `llama_kv_cache:` /
`llama_memory_recurrent:` block; the others run at verbosity 3 (e.g. `logs/llama-server-8070.log:1`) and
do not print buffer sizes.

| Port | PID (start) | Role(s) (registry binding) | Model / arch | Device | `-np` | `-c` | `/props` total_slots / n_ctx per slot | `-kvu` passed | `kv_unified` (log) |
|---|---|---|---|---|---|---|---|---|---|
| 8070 | 2020119 (09-22 14:49) | frontdoor + shared_with worker_summarize/worker_general/worker_explore/worker_math/toolrunner/worker (M:900, M:961; L:1674, L:1698-1704; LM:62-73) | Qwen3.6-35B-A3B-MTP-Q8_0, `qwen35moe` (hybrid GDN, `src/llama-arch.cpp:1053`) | CPU, NUMA_FULL, -t 96 | 4 | 262144 | 4 / **65536** | no | `'false'` — `logs/llama-server-8070.log:18400` |
| 8080 | 2020769 (09-22 14:50) | frontdoor NUMA_HALF_A instance (M:995-996; T:125) | same | CPU, -t 48 | 1 | 262144 | 1 / 262144 | no | `'false'` — `logs/llama-server-8080.log:23850` |
| 8180 | 2021240 (09-22 14:50) | frontdoor NUMA_HALF_B instance (T:126) | same | CPU, -t 48 | 1 | 262144 | 1 / 262144 | no | `'false'` — `logs/llama-server-8180.log:20093` |
| 8074 | 2021760 (09-22 14:50) | architect_critic (M:1610; L:1860; LM:85) | Qwen3.8-Flash-Next UD-IQ4_XS + MTP draft `-md`, `qwen4exp` (hybrid, `llama-arch.cpp:1054`) | CPU, NUMA_FULL, -t 96 | 1 | 262144 | 1 / 262144 | no | `'false'` — `logs/llama-server-8074.log:1001` |
| 8086 | 2022349 (09-22 14:51) | worker_vision + vision_escalation (M:1189, M:1234; L:1781, L:1792) | Qwen3-VL-30B-A3B Q4_K_M + mmproj, `qwen3vlmoe` (pure attention) | ROCm0 | 1 | 65536 | 1 / 65536 | no | `'false'` — `logs/vision-worker-8086.log:3046` |
| 8090-8095 | 2022735…2023882 (09-22 14:51) | embedder, embedder_1..5 (LM:89-94, LM:249-254) | bge-large-en-v1.5 f16, embeddings | CPU, -t 4 | 4 | 512 | 4 / **256** (`n_ctx` rounded down to 1024 — `logs/embedder-8090.log:194426`, rule `src/llama-context.cpp:299-301`) | no | `'false'` — `logs/embedder-8090.log:194428` |
| **8083** | 3343847 (09-23 07:44) | architect_general + aliases coder_escalation, ingest_long_context (M:1323, M:1499; L:1811, L:1838-1840; LM:68,80,87) | Qwen3.8-27B-Q8_0, `qwen35` (hybrid GDN, `llama-arch.cpp:1052`), MTP draft, `--spec-draft-n-max 8` | ROCm0 | 2 | 196608 | 2 / **98304** | no | `'false'` — `logs/llama-server-8083.log:21685`; `llama_context: kv_unified = false` at :21620 (target) and :21658 (draft ctx) |
| 18641 | 3537867 (09-24 13:48) | not a stack role — an experimental DeepSeek-V4.1-Flash run from `llama.cpp-experimental-deepseek41-20260923/build-cpu`, logs to /dev/null | DeepSeek-V4.1-Flash-Q4 + DSpark draft | CPU | 1 | 8192 | `/props` not served (no reply) | **`--no-kv-unified` passed explicitly** | n/a (no log). `draft-dspark` refuses `-np != 1` — `tools/server/server.cpp:153-160` |

The :8083 log block (`logs/llama-server-8083.log:21613-21700`) is the only place the buffer arithmetic is
read rather than derived; it is the calibration for §5:

- target `llama_context`: `n_seq_max = 2` (:21614), `n_ctx = 196608` (:21615), `n_ctx_seq = 98304` (:21616), `n_batch = n_ubatch = 2048` (:21617-21618 — the `-ub 8192` on the cmdline is clamped by `src/llama-context.cpp:265` because no `-b` is passed), `kv_unified = false` (:21620)
- attention KV: `6528.00 MiB (98304 cells, 16 layers, 2/2 seqs)`, q8_0 (:21628)
- recurrent state: `2693.25 MiB (2 cells, 64 layers, 2 seqs 8 rs_seq)` (:21632-21633)
- target compute buffer 1472.33 MiB ROCm0 (:21643); draft MTP KV `768.00 MiB (98304 cells, 1 layers, 2/2 seqs)` f16 (:21666-21667); draft compute 656.06 MiB (:21679)
- slots: `new slot, n_ctx = 98304` ×2 (:21698-21699)

---

## 2. Declared facts and every declared-vs-live mismatch

No `kv_unified`/`kvu` **setting** exists for any role in M, L, T, LM, P or D. The phrase appears in M only,
only for architect_general, only as comments/provenance, and the compiler drops all of it (L: 0 hits). The
launch-arg chain per DERIVATION.md (`/workspace/.claude/skills/stack-change/DERIVATION.md:11-16, 21-24,
37-40`): master `server_mode.<role>.slots` + `serving_shape.slots_by_shape` → `stack_manifest.resolve_slots()`
→ `-np` (rule LM:24, LM:431-437); `serving_shape.n_ctx` → `-c` (LM:460-472); `serving_shape.kv_quant` →
`-ctk/-ctv` (LM:484-493); joined per instance in P `launch.entries` / `runtime.cache` (e.g. P:114-145 for :8074);
emitted by `orchestrator_stack.py:826-832` (default), `:880-885` (vision), `:915-939` (embedding). The
master's `command_templates.server_start` (M:11820-11838, `-c {context_length}`, no `-np`) is legacy, not the
production path.

| Port | Declared n_ctx | Declared slots | Declared kv text | Declared shape | Live | Verdict |
|---|---|---|---|---|---|---|
| 8070 | 262144 (M:916, L:1680) | 4 (M:914; `slots_by_shape {full:4, half:1}` M:917) | none | NUMA_FULL (T:124; D:88-90) | -np 4 -c 262144, 65536/slot | **match** (per-slot 65536 is nowhere declared — M declares only the total) |
| 8080/8180 | 262144 (M:916) | 1 (`half:1` M:917; P:751-759) | none | HALF_A/B interleave 0,1 / 2,3 (T:125-126, T:133-135) | -np 1 -c 262144 | match |
| 8074 | 262144 (M:1621, L:1866) | 1 (M:1619, M:1626) | none; kv f16 forced by recipe (M:1627-1632) | recipe says `threads: 48, cpu_shape: NUMA_FULL_T48` (M:1734, M:1737; L:1900) but T:215 launches `NUMA_FULL` and D:151-153 = 96 threads | -t 96 | **mismatch (threads/shape)** — recipe 48t vs launched 96t. Also T:222 `spec_overrides {draft_max: 4, p_split: 0}` — live has `--spec-draft-n-max 4`, consistent |
| 8086 | 65536 (M:1200, L:1786) | 1 (M:1194; LM:448) | none | GPU_HOST_LANE membind=3 (T:272, T:283) | -np 1 -c 65536 | match |
| 8090-95 | 512 (LM:343) | 4 (LM:345, LM:451) | none | no NUMA (D:187; LM:249) | -np 4 -c 512 → per-slot 256, n_ctx rounded to 1024 | **mismatch (silent)**: a 512-token embedder ctx split 4 ways gives 256 per slot; `llama_context: n_ctx is not divisible by n_seq_max - rounding down to 1024` is a WARN on every launch (`embedder-8090.log:194426`). bge-large's 512 window is not reachable per slot |
| 8083 | 196608 (M:1411, L:1817) | 2 (M:1332, L:1815; P:282, 296). Alias compat scalar for coder_escalation says `slots: 1` (M:1038, L:1730); ingest_long_context says 2 (M:1872) | M:1330-1331 "KV is UNIFIED on this server, so slot count does not scale KV; -c does. 65536/2 = 32768 per slot"; M:1404-1405 "⚠ KV IS UNIFIED ON THIS SERVER…"; M:1520 `vram_gib: 36.70 # … 262144 ctx, n_slots=4, kv_unified=true (MI210, 2026-07-31)`; same provenance at M:3033, M:11081, M:11196 | GPU_HOST_LANE membind=3 (T:238, T:242), ROCm0 (M:1575) | -np 2 -c 196608 → **98304/slot**, `kv_unified='false'` | **mismatch ×3**: (a) unified claim false (server :21620); (b) "32768 per slot" stale (now 98304); (c) coder_escalation `slots: 1` vs host 2. `serving_shape` has no `np`/`batch`/`ubatch`/`spec` key (vram-gap §3.5, `/workspace/artifacts/operator/vram-gap-27b-20260923.md:210-212`) so the capacity model cannot express either -kvu or the draft depth |

A fourth, cross-cutting mismatch: the registry declares only the **total** `-c`, never the per-slot number,
and per §3 no consumer computes `-c / -np`. So the declared "context" of every multi-slot role
(8070, 8083, 8090-95) overstates what any single request can use by exactly `-np`×.

---

## 3. Consumers of per-request context — what the orchestrator actually reads

Finding: **no code in `src/` reads llama-server `/props`, `default_generation_settings.n_ctx`, `total_slots`
or `kv_unified`.** Nothing routes, admits or truncates on a token count vs a role's context. The orchestrator
is blind to the per-slot cap either way, which is why `-kvu` changes *serving* capacity without changing any
orchestrator decision until a consumer is taught to read it. All paths under `/mnt/raid0/llm/epyc-orchestrator`.

| Concern | file:line | What it reads |
|---|---|---|
| Long-context alias routing | `src/api/routes/chat_pipeline/routing_decision.py:195-207` | `len(prompt)+len(context) > threshold_chars` (default **20 000 chars**, `src/config/models.py:1296`; env override `src/config/__init__.py:261,586`) → `ingest_long_context`. Characters, not tokens; never consults the target's n_ctx |
| Alias target | `src/config/models.py:339-344` | `ingest_long_context` → `http://localhost:8083` (architect_general's server) |
| Skip cheap-first for long ctx | `src/api/routes/chat.py:420-432` | role name only |
| Triviality guard off ingest | `routing_decision.py:305-360` (flag `src/features.py:116`) | hardcoded 2000/4000/400 chars |
| REPL exploration switch | `src/api/routes/chat_pipeline/repl_executor.py:592-604` | same 20 000-char threshold |
| Launch `-c` | `src/registry/stack_priors.py:2211-2240` | `serving_shape.n_ctx` (total), fallbacks `effective_context_tokens` / `DEFAULT_EFFECTIVE_CONTEXT_TOKENS` / `model.max_context`; GPU lane `lane_shape.context_tokens = np_slots × slot_ctx` |
| Compaction trigger | `src/graph/compaction.py:50-61, 122-130` | `get_role_config(role).n_ctx` — but `scripts/lib/registry.py:104` returns a dict, `RoleConfig` has no `n_ctx`, exception swallowed → **effectively always 32768** (0.75× = 24 576 tokens or >12 000 chars) **(inferred from code shape, not executed)** |
| Hardcoded context defaults | `src/backends/server_lifecycle.py:84,195` (32768), `src/inference/model_server.py:98` (8192), `src/registry/registry_loader.py:166,464,722` (8192, unused by routing) | constants |
| Truncation | `src/graph/helpers.py:257-266` (>16 000 chars → 0.5 compression), `src/prompt_builders/types.py:29`/`builder.py:474` (4000 chars), `src/context_manager.py:72,83` (100 000), `src/config/models.py:1292` (`stage1_context_limit` 20 000) | chars, hardcoded |
| "exceeds context size" error handling | none found in `src/` | the llama-server 400 propagates as a generic failure |
| Admission (per server) | `src/api/admission.py:60-100,128` | one `Semaphore` per server URL sized from `live_stack_serving_slot_limits` → `stack_priors.py:499-590` reads `runtime.cache.slots_by_port` in P (registry `-np`, not live `/props`); fallback `admission.py:64-73` hardcoded 1/2/4 |
| Admission (per role) | `src/llm_primitives/primitives.py:302-306,650-660` → `src/runtime/concurrency.py:17,72-83` → `stack_priors.py:641-651` (`serving.slots`, warm roles only, default 1) | comment `concurrency.py:43-44`: on the all-hot stack every role ends at Semaphore(1) |
| Worker pool | `src/services/worker_pool.py:312-313` | `config.slots × 2` |
| KV migration | `src/backends/concurrency_aware.py:148,177` | `/slots/{id}?action=save|restore` — moves KV, not an admission check |

Consequence for `-kvu`: today a >98 304-token request to `ingest_long_context` fails at the server with no
orchestrator-side detection; after `-kvu` it succeeds on an idle server but the orchestrator still cannot
tell *which* size will fit (it depends on what the other slot holds — unified capacity is shared, so
"fits" becomes a runtime question the server alone can answer, via `/slots` or the 400).

---

## 4. Why it flipped — the source rule and the launch history

**Rule (frozen tree):**
- `common/common.h:580` — `bool kv_unified = false;` (library default).
- `common/arg.cpp:1215-1216` — server example only: `params.n_parallel = -1; // auto by default`.
- `common/arg.cpp:1545-1552` — `-kvu/--kv-unified` and `-no-kvu/--no-kv-unified` set it explicitly; help text: *"default: enabled if number of slots is auto"*; env `LLAMA_ARG_KV_UNIFIED`.
- `tools/server/server.cpp:146-151` — `if (params.n_parallel < 0) { n_parallel = 4; kv_unified = true; }`. **Any explicit `-np` — including `-np 4` — leaves `kv_unified` at its `false` default.**
- `src/llama-context.cpp:289-303` — unified: `n_ctx_seq = n_ctx`; else `n_ctx_seq = n_ctx / n_seq_max` padded to 256 and `n_ctx` rounded down to `n_ctx_seq × n_seq_max` (the embedder WARN).
- `src/llama-kv-cache.cpp:85` — `n_stream = unified ? 1 : n_seq_max`; K/V tensors are `[n_embd_gqa, kv_size, n_stream]` (:234-235), so total KV bytes are identical either way; only the *partition* changes.
- `src/llama-kv-cache.cpp:716` — unified (`n_stream == 1`) uses `split_simple`, non-unified `split_equal` — batching of concurrent sequences differs **(throughput effect inferred, unmeasured)**.
- `src/llama-graph.cpp:33-38` — KQ mask is `[n_kv, n_tokens/n_stream, 1, n_stream]` with `n_stream = kv_unified ? 1 : n_seqs_unq`; unified makes `n_kv` the whole cache, so the mask doubles at `-np 2` (384 → 768 MiB per context at n_ubatch 2048 on the 27B; vram-gap :205-209).
- Unified-only server behaviours: `tools/server/server-context.cpp:1719` (`try_clear_idle_slots` returns false unless unified), called from `:3798` when a batch cannot find KV room — under unified an **idle slot's prompt is purged** to make room (`:1728-1729` WARN "purging slot"); `:2479-2481` clears idle slots after saving them to the prompt cache when `--cache-idle-slots` is on (needs `--cache-ram`, `:1485-1491`).

**History (which launches were `'true'`):**
- The registry's `vram_gib: 36.70 … kv_unified=true` (M:1520) traces to a **research** run that passed `--kv-unified` by hand: `/mnt/raid0/llm/epyc-inference-research/artifacts/architect-bench-gpu-20260814/q38_vram_shape_20260820/server_command.txt:1` (`-np 4 -c 262144 --kv-unified`), log `server.stderr:23` = `n_slots = 4, n_ctx_slot = 262144, kv_unified = 'true'` (2026-08-20). Sibling runs `swebench_oracle_recapture*_20260819/server_command.txt:1` likewise pass `--kv-unified`. Build not recorded in those dirs; `README.md:46` and `dflash2_np1_20260820/binary-version.stderr:1` point at `10131` (`2046c64e9`) **(inferred, not proven)**.
- Older 4-slot research logs with `'true'` and no cmdline saved: same dir `server.log:8`, `agentic*/server.log:8` (2026-08-15/16); `/workspace/artifacts/typed_decisions/run_20260917/server-27b.log:23`, `server-lfm.log:8`, `server-worker.log:8`; `run_20260918/server-embed.log:12`. Note `run_20260918/launch_server.sh:21-30` passes `--parallel 4 --ctx-size 131072` with no `-kvu`, which under the frozen rule would yield `'false'` — so either those logs came from a different build/launch than the script, or that build's rule differed **(unresolved; inferred)**. `server-worker-np8.log:8` (`-np 8`) is `'false'`, consistent with the rule.
- Orchestrator logs, 2026-04-15/17, build `b8761-4babc8fe3`: `logs/llama-server-8081.log:9,147,293` (and `-8181`, `-8281`, `-8381`) — *"tree speculation: auto-enabling --kv-unified for multi-path verification"* (Qwen2.5-Coder-32B). That auto-enable path no longer exists in the frozen tree (grep: no such string). Later b8957 logs show the opposite: `logs/llama-server-8071.log:191`, `-8073.log:196`, `-8184.log:316`, `vision-escalation-8075.log:216`, `vision-worker-8186.log:203` — *"--cache-idle-slots requires --kv-unified, disabling"*.
- Explicit opt-out on record: `/workspace/artifacts/m12/run_20260918/reader-argv.txt:1` (35B-A3B `-np 4 -c 786432 … --no-kv-unified`).
- A `--kv-unified` A/B came back **negative** as a root-cause hypothesis for a DFlash2 acceptance question: `/workspace/progress/2026-08/2026-08-28-operator-audit-20260827.md:24`.

So: nothing "flipped" in the production launcher — it never passed `-kvu`. The claim entered the master as
provenance of a hand-launched measurement and was then generalised into an invariant (M:1330, M:1404).

---

## 5. Per role — would unified KV help, and what it costs

Cost model (all from the frozen tree; the 27B numbers are read from `logs/llama-server-8083.log:21613-21700`):

- **Attention KV**: total bytes unchanged (`llama-kv-cache.cpp:234-235`); only the per-sequence ceiling changes from `-c/-np` to `-c`.
- **KQ mask**: doubles at `-np 2`, ×`-np` in general (`llama-graph.cpp:33-38`). 27B at n_ubatch 2048: +384 MiB target + +384 MiB draft context = **+0.75 GiB VRAM**. CPU roles pay it in RAM.
- **Recurrent (GDN) state**: rows = `n_seq_max × (1 + n_rs_seq)` (`src/llama-memory-recurrent.cpp:101`, `mem_size = max(1, n_seq_max)` at `src/llama-model.cpp:2278`), `n_rs_seq = draft.n_max` for MTP/EAGLE3/DFlash/DSpark drafts (`common/common.h:390-396`), supported for `qwen35/qwen35moe/qwen4exp` (`llama-arch.cpp:1076-1082`). **Independent of `kv_unified`** — the unified flag is passed to the hybrid memory (`llama-model.cpp:2281`) but sizes the attention half only. 27B: 2693 MiB / 18 rows = **~150 MiB per row → +1.35 GiB per extra slot at draft 8, +0.75 GiB at draft 4, +0.15 GiB at draft 0.** So "higher `-np` is cheap under unified KV" is true only for pure-attention models (8086, 8090-95); for the three hybrids each slot costs GDN rows before it costs a single KV cell.
- **MTP draft context**: a second `llama_context` with the same `n_seq_max`, `n_ctx`, and unified flag (:21651-21667); its KV total is also unchanged; its mask also doubles.
- **Prompt-cache semantics**: under unified an idle slot can be purged mid-run to make room (`server-context.cpp:1719-1729, 3798`); on shared servers (8070 with six roles, 8083 with three) a long request can evict another role's warm prefix — a re-prefill cost that does not exist today **(behavioural inference from source, unmeasured)**.
- **Batching**: `split_simple` vs `split_equal` (`llama-kv-cache.cpp:716`) — unified lets one ubatch mix sequences freely; **(throughput effect unmeasured)**.

| Port / role | Would it help? | Benefit | Cost | Verdict |
|---|---|---|---|---|
| **8083** architect_general / coder_escalation / ingest_long_context (`-np 2`, hybrid, draft 8, GPU) | **Yes — this is the only role whose alias is *defined* by long context** (`ingest_long_context` → :8083, `models.py:339-344`) and whose slot cap (98 304) is below the model's 262 144 train ctx (:21625) | a lone request can use 196 608; two concurrent requests share it dynamically instead of 98 304 hard each | +0.75 GiB VRAM (two masks) against **0.86 GiB free** (vram-gap §4, :215); the SSU-F3 levers `-ctkd/-ctvd q8_0` (−0.35 GiB, :278) and/or draft 8→4 (−1.3 GiB, handoff `model-stack-single-source-update-pipeline.md:432`) are the funding. Idle-slot purge across three aliases. | candidate #1 (in flight) — **must be paired with a VRAM lever or it will not fit (inferred from the mask formula; a `-lv 4` restart proves it)** |
| **8070** frontdoor + 5 worker aliases (`-np 4`, hybrid, draft 4, CPU RAM) | Partly. Per-slot cap 65 536 vs `-c` 262 144; any worker request >65 536 tokens fails today with no orchestrator handling (§3). But long requests are routed *away* to 8083 at 20 000 chars, so 8070 sees them only via non-chat paths | one big worker/summarize job could use up to 262 144 | mask ×4 in RAM (256 MiB → 1 GiB at n_ubatch 2048, **inferred**); idle-slot purge across six roles on the busiest server; RS unchanged | candidate #2 — only if a consumer is taught to send long jobs here; otherwise no request can exploit it |
| 8080/8180 frontdoor halves (`-np 1`) | No — `-np 1` means per-slot = `-c` already (`/props` 262144) | none | none | skip |
| 8074 architect_critic (`-np 1`, hybrid, draft 4) | No — same; and going to `-np 2` costs GDN rows (Flash-Next row size unknown; log at verbosity 3) | none unless `-np` rises | RS growth per slot; the recipe was measured at 8192 ctx (M:1770) | skip |
| 8086 worker_vision / vision_escalation (`-np 1`, pure attention, GPU) | Not at `-np 1`. If `-np` ever rises, this is the one model where unified `-np` IS cheap (no RS, no draft) | free dynamic sharing between vision and escalation | mask ×`-np`; 0.80 GiB residual today (vram-gap :90-92) | candidate #3 if vision concurrency is wanted |
| 8090-95 embedder (`-np 4 -c 512`, embeddings) | **Yes, and for a different reason**: per-slot is 256, below bge-large's 512 window, and the launch WARNs every time (`embedder-8090.log:194426`). Unified makes each slot able to take 512 | correct embedding window; no more silent truncation at 256 | none material (mask 512×512) — but embeddings must fit one ubatch (`server.cpp:139-144`); alternatively `-c 2048 -np 4` fixes it without `-kvu` | candidate #2-bis (cheapest, GDN-free) — or simply raise `-c` |
| 18641 experimental DeepSeek (not a stack role) | out of scope; passes `--no-kv-unified` and DSpark forbids `-np != 1` (`server.cpp:153-160`) | — | — | ignore |

---

## 6. Ranked candidates after the 27B proves it

1. **:8083 (in flight).** Benefit: `ingest_long_context` finally has a 196 608-token slot instead of 98 304; 27B can approach its 262 144 train window only via this route. Cost: +0.75 GiB VRAM (needs `-ctkd/-ctvd q8_0` or draft 8→4 to fit in 0.86 GiB free), idle-slot purge across architect_general/coder_escalation/ingest_long_context. Consumers to change: `routing_decision.py:195-207` (char threshold → token estimate against the *live* per-slot n_ctx from `/props`), `compaction.py:50-61` (fix `get_role_config` so 32 768 is not the silent default), add handling for the server's "exceeds context size" 400, and give `serving_shape` an `np`/`kv_unified`/`spec` key (vram-gap :210-212) so the capacity model can price it. Also fix M:1330-1331 and M:1404-1405 wording and the coder_escalation `slots: 1` scalar (M:1038).
2. **:8090-95 embedder.** Benefit: restores the 512-token window per slot (today 256, WARN on every launch). Cost: nil. Consumers: none (or replace `-kvu` with `-c 2048`, which needs only LM:343). Pure-attention → no RS cost.
3. **:8070 frontdoor/workers.** Benefit: a lone 262 144-token worker job. Cost: 4× mask in RAM, purge semantics across six roles. Consumers: nothing routes long work here today; `routing_decision.py:195-207` sends it to 8083. Only worth it if the operator wants CPU-side long-context as an overflow for 8083 — then admission (`admission.py:60-100`) must learn that unified capacity is shared, not `slots × per-slot`.
4. **:8086 vision** — only if `-np` rises; the one hybrid-free GPU role where unified `-np` is cheap.
5. **Not candidates**: 8080/8180/8074 (`-np 1`, nothing to gain); 18641 (experimental, DSpark forbids it).

Stack-wide principle the operator asked for: under unified KV, **KV capacity is per server, not per slot**,
so the registry's "context" of a role should be stated as `(-c, -np, kv_unified)` and every consumer that
reasons about "fits" must read the server (`/props`, `/slots`) — the registry's scalar cannot express a
shared pool. For the three hybrids (27B, 35B-A3B, Flash-Next) the second lever — more slots — is paid in
GDN rows × (1 + draft depth) regardless of `-kvu`, so it stays expensive; only the vision and embedder
servers get "free" slots.

---

## Appendix — commands used (all read-only)

- Process census: iterate `/proc/*/cmdline` for `llama-server`; `ps -o lstart= -p <pid>`; `readlink /proc/<pid>/fd/{1,2}` → log paths.
- `curl -s http://127.0.0.1:<port>/props` → `total_slots`, `default_generation_settings.n_ctx`, `build_info`.
- `grep -n "kv_unified" logs/*.log`; last `load_model: initializing` block per log.
- `git -C /mnt/raid0/llm/llama.cpp rev-parse HEAD` = `ffc1bac82…`; `grep -n kv_unified` over `common/`, `src/`, `tools/server/`.
- GGUF arch: `head -c 4M <gguf> | strings | grep general.architecture` → `qwen35moe`, `qwen35`, `qwen4exp`, `qwen3vlmoe`.
