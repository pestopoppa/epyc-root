# Agentic serving harness fixes — demonstrate on the 27B, generalize, then audit

**Status**: active. Phase A is in flight: the F12 run on DFlash2 started 2026-10-03.
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

- [ ] **UFH14-A1.** F12 run: the cxf1 arm (F1: solo, 1 h idle timeout, compaction at 150k) and the cxf12 arm (F1 plus F2: JSON-first answer, forced answer at 65% of budget, refine turn, 8k thinking cap). 8 solo calls on C2 and C4, graded blind against all C95 arms. Covers D1 and D4, partly D2.
  - Launcher: `/mnt/raid0/llm/tmp/ds41-c95/f12_launch2.sh`. Log: `logs/f12_launch2.log`.
- [ ] **UFH14-A2.** DFlash2 decode-vs-context probe on the production shape, to compare against the MTP probe and to separate drafter speed from harness effects.
- [ ] **UFH14-A3.** Prefix warming plus staggered starts for parallel arms. Issue one warm request for the shared context, then start the arms so they hit the prompt cache. Measure the cold-prefill share and decode stall against an unstaggered A/B. Covers D5.
- [ ] **UFH14-A4.** Compaction that keeps the prefix. Make compaction requests carry the same tools and system prefix, or compact through a separate summarization call that leaves the live prefix intact. Measure re-prefill tokens per compaction. Covers D2. Also cover opencode's task-prompt drop (D3).
- [ ] **UFH14-A5.** Phase A verdict: which fixes measurably change P(keep), wall time and prefill seconds on the 27B. Wire the results to the belief kernel; VB-DS41-C95 already exists, so extend it rather than adding a new ladder.

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
- Since 2026-09-30 DS41's planner and critic are external models (gpt-6.1-sol, claude-opus-5-5). Whether the 27B returns to the planner seat is an operator decision after A5. It competes for :8083 with the INF-80 X0 window (`/mnt/raid0/llm/tmp/x0-27b-quants/PLAN.md`).
