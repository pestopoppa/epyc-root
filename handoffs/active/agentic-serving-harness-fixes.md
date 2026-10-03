# Agentic serving harness fixes — demonstrate on the 27B, generalize, then audit

**Status**: active. Phase A: A1 (F12 run) done and graded 2026-10-03; A2 running inside the INF-80 X0 window; A3/A4 implemented and offline-tested, GPU test pending.
**Created**: 2026-10-03, by operator directive in session ak-ds41-main:

> "yes, i want all the harness bugs we identified to be fixed. The fixes shoudl be as general as possible (not limited solely to the 27B model) as I'm sure they would affect the usage of any of the models in the orchestrator stack. A full review/audit of how fixes should holistically be folded into the orchestrator's mgmt shoudl be performed after they are demonstrated on the 27B model."

**Categories**: agent_architecture, inference_serving, context_management, tool_implementation
**Parent index**: [`user-facing-harness-index.md`](user-facing-harness-index.md), row UFH-14.
**Owners**:
- Phase A and the client-side harness pieces: ak-ds41-main.
- Phase B orchestrator and stack pieces: workspace-ec, the stack owner (formerly workspace-8d).
- Phase C: the operator's choice of auditor (Fable, per the auditor convention).

**Related**:
- [`harness-selection-and-integration.md`](harness-selection-and-integration.md) (UFH-01, HS-4: harness features live inside the orchestrator).
- [`harness-improvement-loop.md`](harness-improvement-loop.md) (UFH-08).
- [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md) (INF-77, where the defects were found: DS41-C95).

## Evidence (the defects this handoff fixes)

1. **The 27B harness experiment (DS41-C95)** was graded blind by claude-opus-5-5. P(keep): DeepSeek as-ran 0.75, 27B×codex 0.50, 27B×Hermes 0.33, 27B×opencode 0.25, 27B as-ran 0. Orchestrator arms orv and orsv went 0/4.
   - **Diagnosis:** `/mnt/raid0/llm/tmp/ds41-c95/diagnosis-27b-report.md`. Most 27B failures were harness and serving defects, not model capability. In 6 of 8 no-reply calls, a keep-class candidate already sat in the transcript.
2. **The prefill/decode share analysis** covers 09-24→10-01 and was parsed from llama-server logs: [`docs/reviews/prefill-share-20261003.md`](../../docs/reviews/prefill-share-20261003.md).
   - On :8083, 74% of prefill time was cold ≥8k prefills where no slot held the prefix.
   - 21k s was duplicate concurrent prefill of the same context.
   - There were 929 prompt-cache evictions and 456 "failed to find a memory slot" warnings.
   - Neighbour prefill dropped decode from 28.6 to 7.8 tok/s, costing about 60k s.
3. **Decode-vs-context probe** (solo, production shape): `/mnt/raid0/llm/tmp/ds41-c95/probe-decode-vs-context.md`. On MTP, prefill fell from 850 to 487 tok/s between 2k and 80k, and time to first token at 80k is 165 s.

| # | Defect | Layer | Generic? |
|---|---|---|---|
| D1 | Client stream idle timeout (codex ~300 s) shorter than a long silent prefill. The abandoned request keeps prefilling, which doubles the load. | client harness | yes: any model with long prompts |
| D2 | Compaction requests change the prompt prefix (codex sends `tools=[]`), forcing a full cold re-prefill of 79–94k tokens. | client harness | yes |
| D3 | Compaction drops the task prompt (opencode). | client harness | yes |
| D4 | No answer protocol: the model explores past its budget with a candidate in hand, and the final answer is never emitted. | harness prompt and loop | yes |
| D5 | Parallel arms start at the same moment on the same context, so each prefills cold. No prefix warming. | harness scheduling | yes |
| D6 | The `--kv-unified` pool (`-c 196608` shared by 4 slots) overflows under concurrent long contexts, causing evictions and context-exceeded errors. | server config | yes: per-model sizing |
| D7 | Concurrent long prefills stall decode in the other slots. | server admission | yes |
| D8 | Serving telemetry gaps: no wall-clock time, no record of which role or client sent each request, `prompt_eval_ms`=0, cancels untimed, queue wait unlogged. | orchestrator and stack logging | yes |

## Phase A — demonstrate on the 27B (production Qwen3.8-27B Q8_0, DFlash2, :8083)

- [x] **UFH14-A1.** ✅ 2026-10-03 — F12 run: the cxf1 arm (F1: solo, 1 h idle timeout, compaction at 150k) and the cxf12 arm (F1 plus F2: JSON-first answer, forced answer at 65% of budget, refine turn, 8k thinking cap). 8 solo calls on C2 and C4, graded blind against all C95 arms. Covers D1 and D4, partly D2.
  - Launcher: `/mnt/raid0/llm/tmp/ds41-c95/f12_launch2.sh`. Log: `logs/f12_launch2.log`.
  - **Result** (blind Opus grades, `/mnt/raid0/llm/tmp/ds41-c95/grading/report.md`; per-call `results/C{2,4}/cxf{1,12}/r{1,2}/result.json`). n = 4 calls per arm, so OBSERVATION grade only:

    | arm | answered | keep exact / partial | P(keep) | mean factual errors | median wall s |
    |---|---|---|---|---|---|
    | DeepSeek as-ran (calibration) | 3/4 + 1 abstain | 3 / 0 | 0.75 | 0.0 | — |
    | cx (unfixed codex inline) | 2/4 | 0 / 2 | 0.50 | 2.0 | 5401 |
    | **cxf1** (F1) | 4/4 | 0 / 2 | 0.50 | 1.75 | 4640 |
    | **cxf12** (F1+F2) | 4/4 | 0 / 3 | 0.75 | 2.25 | 3880 |

  - **What F1 fixed:** no client timeouts, aborts or cold re-prefills; prompt-cache hit rate 90–96% per call. F1 alone still needed salvage (answer rebuilt from the transcript) on 2 of 4 calls.
  - **What F2 fixed:** cxf12 answered within its own turns on all 4 calls, with a ~16% shorter median wall than cxf1. It did not reduce factual errors (2.25 vs 1.75) and found no exact keep.
  - **DFlash2 on agentic traffic:** draft acceptance 29–34% on temperature-1.0 planner traffic, decode 25–30 tok/s at 57–152k context (well below the 91.7 tok/s single-stream short-context figure).
  - **Contamination:** C2/cxf1/r2 browsed the live campaign store (`anchor-gen-007`), so it saw post-anchor state; the grader flagged it. The harness had no filesystem isolation.
  - **Fixed offline (not yet GPU-tested):** a Landlock filesystem sandbox (`/mnt/raid0/llm/tmp/ds41-c95/sandbox3.py`; mount and user namespaces are unavailable in this container, Landlock ABI 6 needs no privilege) plus the A3 and A4 implementations in `run3.py`/`proxy3.py`. They close A3/A4 only after a GPU run.
  - The separate DFlash2 decode probe crashed on fresh slots (`KeyError 'params'`); fixed in `probe_decode.py` and folded into the INF-80 X0 window (A2).
- [ ] **UFH14-A2.** DFlash2 decode-vs-context probe on the production shape, to compare against the MTP probe and to separate drafter speed from harness effects.
  - 2026-10-03: running inside the INF-80 EXL3-X0 window (`/mnt/raid0/llm/tmp/x0-27b-quants/PLAN.md`) after the `probe_decode.py` fix. Agentic-traffic acceptance from A1 (29–34%) is context for it, not a substitute.
  - *F12 production-traffic numbers, 2026-10-03.* These are not the probe, so the box stays open. Re-derived from `wire_timing` in `/mnt/raid0/llm/tmp/ds41-c95/results/C{2,4}/cxf{1,12}/r{1,2}/result.json`, 8 calls. Server: :8083 PID 3793153, `-np 4 -c 196608 --kv-unified`, `--spec-draft-n-max 8` clamped to 7. This is the pre-KVU-16 shape.
    - DFlash2 draft acceptance: 0.290–0.343.
    - Median decode on turns of ≥1k tokens: 24.6–30.2 tok/s.
    - Prompt-cache hit: 0.882–0.959. Two calls sit below 0.90 (C2/cxf1/r2 0.882 and C4/cxf1/r1 0.896); both contain a compaction (A4).
    - Context: 49.8–56.9k at the first request, 109.5–151.5k at the peak.
  - Read the acceptance against the production prior, not the benchmark one. AngelSpec replayed temperature-1 production traffic and measured a block-8 DFlash-family drafter at a mean accepted length of about 2.5 tokens per step, roughly half its benchmark figure (`intake-1848#01`, `intake-1848#02`). Our 29–34% at n_max 7 is in that range and is not by itself a drafter defect. The unified-KV decode tax is a separate, unmeasured suspect (`intake-1849#02`; KVU-18 in [`kv-unified-stack-rollout.md`](kv-unified-stack-rollout.md)).
- [ ] **UFH14-A3.** Prefix warming plus staggered starts for parallel arms. Issue one warm request for the shared context, then start the arms so they hit the prompt cache. Measure the cold-prefill share and decode stall against an unstaggered A/B. Covers D5.
  - 2026-10-03: implemented in `/mnt/raid0/llm/tmp/ds41-c95/run3.py` + `proxy3.py`, offline-tested only. Close after the GPU A/B.
- [ ] **UFH14-A4.** Compaction that keeps the prefix. Make compaction requests carry the same tools and system prefix, or compact through a separate summarization call that leaves the live prefix intact. Measure re-prefill tokens per compaction. Covers D2. Also cover opencode's task-prompt drop (D3).
  - 2026-10-03: implemented in `run3.py` + `proxy3.py`, offline-tested only. Close after a GPU run measures re-prefill tokens per compaction.
  - *Baseline from F12, 2026-10-03, wire logs.* 5 codex compactions across the 8 calls, each a cold pair at `cache_n` = 0:
    - The `tools=[]` compaction request: 147.6–157.1k tokens, 416.7–461.2 s.
    - The post-compaction request: 38.3–39.7k tokens, 58.1–60.1 s.
    - Total: 2,459 s of prefill, 8.9% of the 27,731 s summed call wall time. This is 3.5× the hybrid re-prefill cost in A7.
- [ ] **UFH14-A6.** Run every later harness experiment under the Landlock sandbox (`sandbox3.py`) and verify isolation on a real call before relying on it: a planted read of the live campaign store must fail, while the call's own workspace, result dir and wire proxy stay reachable. Origin: C2/cxf1/r2 contamination (A1).
- [ ] **UFH14-A5.** Phase A verdict: which fixes measurably change P(keep), wall time and prefill seconds on the 27B. Wire the results to the belief kernel; VB-DS41-C95 already exists, so extend it rather than adding a new ladder.
- [ ] **UFH14-A7 (intake P7). Hybrid re-prefill when the next turn's history diverges inside the previous output.** Code read of frozen v10 `ffc1bac82` plus the F12 wire logs. Report and scripts: `/mnt/raid0/llm/tmp/p6p7-20261003/`.
  - **Mechanism.**
    - Context checkpoints are created at only one call site, in the prompt-processing loop (`tools/server/server-context.cpp:3725`).
    - They are taken at user-message starts and at 4+n_ubatch and 4 tokens before the prompt end (`:3640-3666`, `:3696-3726`).
    - None is taken during or at the end of generation. `--ctx-checkpoints` (default 32) and `--checkpoint-min-step` (default 8192; `common/common.h:633-634`, `common/arg.cpp:1520-1535`) govern prefill only.
    - The intake guess that every turn recomputes the previous output (intake-1827#record notes) is **refuted for the common case**. When the next prompt extends the cached tokens exactly, the live recurrent state is already at the end of the previous output and is used as is. On 179 of 230 follow-on F12 turns, `cache_n` = previous prompt + previous output, with zero re-prefill.
    - The checkpoint matters only when the re-rendered history differs from the generated tokens. The hybrid `pos_min` test (`:3397-3399`, `:3450-3464`; recurrent `seq_rm` rolls back at most `n_rs_seq` tokens, `src/llama-memory-recurrent.cpp:191-200`) then forces a restore, and the newest usable checkpoint is the previous prompt end minus 4.
  - **Measured.**
    - 41 of 230 turns (17.8%) show `cache_n` = previous prompt − 4 exactly, with re-prefill = previous output + 4.
    - Cost: 224,863 tokens and 705 s over 8 calls, 14.8% of all prefill time and 2.5% of wall time.
    - Divergence points come from `selected slot by LCP similarity` in the server-window logs (35 turns). 13 diverge in the first third of the previous output (reasoning), 10 in the middle, and 12 in the last 10% (message or tool-call tail).
    - An end-of-generation checkpoint would save **0** tokens, because every divergence precedes the end.
  - **Next steps, in order.**
    1. *Root cause, no code.* Set `LLAMA_SERVER_SLOTS_DEBUG=1` on the next :8083 relaunch. It prints the old and new tokens at the mismatch (`server-context.cpp:3407-3447`). Then classify each case: template re-render (fix in `epyc-qwen3x-v1-terse.jinja` or the Responses-to-chat conversion) or non-canonical re-tokenization of sampled text. A render-side fix recovers up to the full 705 s per 8 calls.
    2. *Only if the cause cannot be removed: experimental-tree code on `llama.cpp-experimental`.* Add generation-time checkpoints every N generated tokens for RS/hybrid slots, in the decode path beside the existing per-round speculative checkpoint (`server-context.cpp:3146-3184`). Each is about 144 MB of 27B linear state (`intake-1847#01`). Restore then lands at the last checkpoint at or before the divergence point. Replayed savings on the 35 located turns: N=1024 saves 92k tokens and 270 s (38% of the class); N=2048 saves 82k and 237 s; an ideal checkpoint exactly at the divergence point saves 105k and 309 s. No flag change in v10 achieves this.

## Phase B — generalize, model-agnostic

Client and harness side (ak-ds41-main):

- [ ] **UFH14-B1.** Move the demonstrated client fixes (D1–D5) out of the C95 experiment drivers (`/mnt/raid0/llm/tmp/ds41-c95/run2.py`, `proxy2.py`) into shared, model-independent harness settings. Targets:
  - the AutoKernel actor launch (`epyc-inference-research` actors.py);
  - the opencode and codex provider configs used with local models;
  - the orchestrator's own agent-loop compaction (HS-4).

  Each parameter is derived from the serving server's measured prefill rate and slot context, never hardcoded for one model.

Orchestrator and stack side (workspace-ec; items are linked here as they land):

- [x] **UFH14-B2.** ✅ 2026-10-03 (workspace-ec) — orch 2586a7bb on main, API reload: scouts reserve prompt+max_tokens on the token gate; one long prefill (≥16384 est. tokens, env ORCHESTRATOR_KV_POOL_LONG_PREFILL_TOKENS, 0=off) per server, lease ends at first chunk or prompt/250 tok/s; /slots observation holds long requests behind any slot prefilling ≥4096 (covers other uvicorn workers + direct clients like C95); per-request cap = min(slot ctx, model ctx_max). 32 new tests; 4126 related pass. Live alias call via gate ok. Remaining limits: per-worker gate (cross-worker via /slots only), whole-prompt size even when mostly cached; ungated paths documented in /mnt/raid0/llm/tmp/kv-gate-8083-ec/BYPASS.md (action_repair_completer if pointed at :8083; prewarmer only :8074). Was: Token-aware pool gate, keyed per server: one long prefill at a time, with all orchestrator traffic, scouts included, going through it. Covers D7. Operator-approved 2026-10-03; deployed as an API-only change. In progress (workspace-ec): orch branch `feat/kv-pool-gate-8083-ec`; tracked as KVU-15 in `kv-unified-stack-rollout.md`.
- [x] **UFH14-B3.** ✅ 2026-10-03 (workspace-ec) — LIVE: :8083 relaunched 13:14:35Z (PID 4052768) with `-c 393216` unified, per-slot cap 262144 (server log `n_ctx_slot = 262144, kv_unified = 'true'`), draft n-max 7; API reload (PID 4054223) reads per_request 262144 / shared_pool / pool_tokens 393216; load peak 50.78 GiB; alias completion via :8000 correct; pipeline `check --run-promotion-gate` all ok. Receipt RATIFY-STACKCHG-KVPOOL-20261003; research 412e8fc1, orch 09e91e1e + 841935ea, root 64d70d17; evidence `/mnt/raid0/llm/tmp/stack-change-kvpool-20261003/`. Detail is KVU-16 in `kv-unified-stack-rollout.md`. Was: KV-pool sizing as a per-model stack rule: slots × expected context, plus a per-request cap. The :8083 instance is a relaunch with `-c 393216` unified and a 262144 per-request cap (stack change, operator signature). Covers D6.
  - [ ] **Open sub-task: the full-pool concurrent-residency proof.** The 4 × 90k probe held (all 200, zero memory-slot
    lines, KFD peak 51.73 GiB) but peaked at 92,343 cells in flight, under its 300k criterion, so residency is UNPROVEN,
    not disproven. Tracked as KVU-16b (corrected probe) / KVU-16c (cite workspace-89's P3 run).
- [ ] **UFH14-B4.** Prefix-cache and `--cache-ram` policy per server. Covers D5 and D6 on the server side.
  **DESIGNED + API part BUILT 2026-10-03, NOT DEPLOYED, policy not applied** (workspace-ec): design
  `docs/design/ufh14-b4-prefix-cache-policy-20261003.md`; orch commits 61873d75, acb5a816, 1c3f8e77, c14a098d, 8f354ac3
  (integrated on `integ/api-reload-2-ec` 10bc5681). Key fix: router `id_slot` pinning hashed the prompt's first 256
  characters, so every call of a role went to ONE slot and v10 deferred it while other slots were free; pinning is now
  opt-in (`ORCHESTRATOR_PREFIX_ROUTER_PIN_SLOTS=1`). Instrument: `missed_prefill_share` (lower = better) from
  `scripts/analysis/prefix_cache_report.py`. Not ticked until PFX-SEL-1 lands; the sub-tasks below are the remainder.
  - [ ] **UFH14-B4a — PFX-SEL-1 stack-change package, after a metric window.** Design §3.8 / §4.4: master
    `prefix_cache` per model, topology `prefix_cache_selection`, compiler + launcher + drift checker. No launch flag
    changes today (derived values equal today's). Prepare it after ≥ 1 window of ≥ 200 post-deploy calls gives a
    `missed_prefill_share` baseline; one package, operator signature. Raise :8083 `--cache-ram` 65536 → 102400 only if
    §4.3's decision rule fires (> 5% across two windows, with evictions logged).
  - [ ] **UFH14-B4b — A/B: the stable head as a system message (design R2, §4.2 item 1).** Split the prompt at a
    builder-emitted marker into `[system, user]` on the chat lane behind a flag; A/B on the eval tower (quality) and
    `missed_prefill_share` / `hit_tok` for REPL roles. Largest expected win on hybrids.
  - [ ] **UFH14-B4c — A/B: `prefix_stable_order` on in production (design R1, §4.2 item 2).** `src/features.py:236`;
    composes with B4b, same A/B protocol.
  - [ ] **UFH14-B4d — A/B: move CoT prefixes and worker RAG snippets to the tail (design R6, §4.2 item 3).**
    `graph/helpers.py:936-940` (CoT before the system prompt), `corpus_retrieval.py:739-780` (`## Reference Code`
    before `## Task`).
  - [ ] **UFH14-B4e — delete `escalation_prewarmer` (design §4.2 item 5, delete-lens 4).** It warms
    `ARCHITECT_SYSTEM_PREFIX`, a string no real architect request contains (`escalation_prewarmer.py:61-65`); A3's
    client-side warm + stagger is where warming belongs. Review, not A/B: it changes no model input.
  - [ ] **UFH14-B4f — belief-kernel write side for the per-port prefix-cache report.** Add the report's per-port rows as
    a projection under B5's `serving_calls` adapter row in `scripts/vidya/adapters/README.md`. Row text PREPARED for the
    owning session in `/mnt/raid0/llm/tmp/wrapup-ec-kvu16/INDEX_ROWS.md`; read side rides VB-SERVE-TIMING-1.
  - [ ] **UFH14-B4g — re-measure the 27B DFlash2 prompt-cache entry cost (design §4.4).** It was to ride B3's relaunch
    (`-lv 4` lines `prompt_save … total state size … (draft: …)` and `created context checkpoint … size`). If those lines
    are not in the 13:14Z bring-up log, capture them at the post-X0 restore (KVU-16e); feeds PFX-SEL-1's entry cost.
  - [ ] **UFH14-B4i — evaluate `--no-cache-idle-slots` per server (filed 2026-10-03, from workspace-89's P3 code read).**
    v10 defaults `cache_idle_slots` ON: with `--cache-ram` + `--kv-unified`, every idle slot is saved to RAM and cleared
    from the KV pool as soon as any new task starts (server-context.cpp:2469-2483). So on :8083 a paused agent context
    never stays resident in VRAM, and its next turn pays a RAM restore (or a cold prefill after one of the 929 evictions).
    A/B per server, both arms read with `prefix_cache_report.py`: per-turn agent latency, `hit_tok`, `missed_prefill_share`,
    `cache_ram` evictions, and VRAM headroom. Default ON against OFF. OFF keeps idle contexts resident, but the pool then
    fills with idle cells. Whatever wins becomes a PFX-SEL-1 field.
  - [ ] **UFH14-B4h — remove the dead slot-save warming path (delete-lens 2 and 6).** `--slot-save-path` /
    `save_hot_prefixes` / `restore_hot_prefixes` have no production caller and lose hybrid checkpoints;
    `canonicalize_prompt` is dead weight with pinning off. One cleanup commit with an upstream gitnexus impact first.
  - Declined, not filed: adding `cache_prompt` to the direct callers that omit it (`worker_pool.py:855-867`,
    `tools/web/research.py:709-716`, design §4.2 item 6) — the server default is `true`, so the edit changes nothing;
    the design says add it when next touched. Declined: `--cache-reuse` as a generic knob (design §3.6, unsound on
    every model we run).
- [x] **UFH14-B5.** ✅ 2026-10-03 (workspace-ec) — orch c6225e8b/f7fad574/9a0d38e0 on main, API reload 04:59Z: per-call records in `logs/serving_calls/serving_calls.jsonl` (role, request_id, queue wait, llama `timings`, outcome incl. cancelled), chat-stream `prompt_eval_ms` fixed (live :8083 call: 2368 ms), progress rows flushed durably, launch/stop banners + `logs/server_launches/<port>.json` at each server's next stack launch; era ST1 (orch 4e23e553); write-side adapter row in `scripts/vidya/adapters/README.md` (root 999954ca), read side = VB-SERVE-TIMING-1 (open). Was: Serving telemetry: a launch banner with ISO-UTC, pid, role and argv; per-call role, request_id and llama `timings`; `prompt_eval_ms` filled in; cancel summaries; queue wait. Plus the belief-kernel write-side adapter, owned by workspace-ec. Covers D8.
- [ ] **UFH14-B6.** An OpenAI-compatible passthrough on :8000 for a named role (chat/completions and responses, streaming, tools, timings echoed), so harness experiments can go through the gate instead of hitting servers directly. The gap list is pending from workspace-ec. Gap analysis in progress (workspace-ec): `/mnt/raid0/llm/tmp/kv-gate-8083-ec/BYPASS.md`.
  **BUILT 2026-10-03, NOT LIVE** (workspace-ec): orch 3edfdff3 — `POST /v1/passthrough/{role}/chat/completions` and
  `/responses`, `GET …/models`; raw body forwarded, true SSE streamed unbuffered, server `timings` on the wire, behind the
  full admission gate (KV-pool tokens, one long prefill, host-wide lease after KVU-15a, per-request cap → 413), one
  `serving_call.v1` record per call (`caller.source="passthrough"`), localhost only, `ORCHESTRATOR_PASSTHROUGH=0` kill
  switch. Integrated on `integ/api-reload-2-ec` 10bc5681. The purpose (harness experiments go through the gate) needs
  it live on :8000, so not ticked until UFH14-DEPLOY-EC lands and a live call proves it.
  - Declined, not filed: timings on a NON-streamed `/v1/responses` body. llama-server v10 does not emit them
    (`server-task.cpp:558`) and the kernel is frozen; streamed `/responses` and chat/completions carry them.
- [ ] **UFH14-DEPLOY-EC — deploy orch `integ/api-reload-2-ec` (B6, B4 API part, KVU-15a, RI-18c, test fixes).**
  (filed 2026-10-03, workspace-ec) HEAD 10bc5681, worktree `/mnt/raid0/llm/worktrees/orch-integ2-ec`. Gate: the full
  unit run (`/mnt/raid0/llm/tmp/integ2-ec/full_unit3.log`, in progress at wrap-up) ends 0 failed apart from the known
  order-dependent test (SCG-TEST-ORDER). Then merge to orch main and `orchestrator_stack.py reload orchestrator`
  (API only) once :8083 is restored (KVU-16e). Proofs after the reload: one live passthrough streamed call with
  timings (B6); RI-16 reader shows `review_gate`/`review_verdict` null on live `/chat` (RI-18c); a 2-worker replay
  with peak 1 long prefill and a cached-prefix request not held (KVU-15a); serving records carry `prefix_fp` (B4).

## Phase C — holistic audit (starts only after A5)

- [ ] **UFH14-C1.** A full review of how the A and B fixes fold into orchestrator management across every model in the stack: CPU and GPU roles, frontdoor, architect, workers and embedders. Covers routing, admission, compaction, caching, telemetry and per-model parameters.
  - Output: a decision package for the operator (options, tradeoffs, recommendation), plus follow-up tasks filed in their owning handoffs.
  - Delete-lens included: name the fixes that should NOT become generic.

## Notes

- The C95 harness calls :8083 directly through its own proxy, because it needs raw streams with per-request timings on the wire. It runs at concurrency 1, so it cannot exhaust the pool. Once B6 exists, later harness experiments should go through the gate.
- **The 16-token verify block is a copy-workload profile, not an agentic one.** HyperQwen's DFLASH_TOKENS=15 gains come from greedy runs where the model reproduces its own context. Its author puts it about 2:1 behind MTP elsewhere, it costs recurrent-state pages per slot, and the source keeps k=7 for agentic clients (`intake-1827#01`, `intake-1827#06`, `intake-1830#record`). Do not tune temperature-1.0 agentic traffic toward it. Bole prices each extra verify position on Qwen3.8-27B at a ~144 MB recurrent snapshot per sequence (`intake-1847#record`). The production prior for block-8 acceptance at temperature 1 is AngelSpec's ~2.5 tokens per step (`intake-1848#01`).
- Since 2026-09-30 DS41's planner and critic are external models (gpt-6.1-sol, claude-opus-5-5). Whether the 27B returns to the planner seat is an operator decision after A5. It competes for :8083 with the INF-80 X0 window (`/mnt/raid0/llm/tmp/x0-27b-quants/PLAN.md`).
