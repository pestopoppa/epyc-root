# Unified KV (`--kv-unified`) stack rollout and shared-pool serving

**Status**: ACTIVE. The GPU-residency package (OP-54) is **applied and serving-proven** (2026-09-24 ~18:45–18:55Z,
orch `0a564a1f`, research `75ee1b8e`): :8083 runs `-np 4 -c 196608 --kv-unified --spec-draft-n-max 4 -ub 2048
--cache-ram 65536`, STT/TTS run on CPU cores 0-23 / 24-39. The overflow branch and the gate fix are merged. What is
left: the depth-4 production confirmation (KVU-1b / M-3b),
the opencode limit (KVU-1a, operator), and the follow-ups below.
**Created**: 2026-09-24 (main-ak-seat, stack-configuration window)
**Priority**: HIGH. :8083 caps every request at 98,304 tokens today, and that ceiling emptied DS41 run 8's planner reply.
**Categories**: inference_serving, kv_cache, orchestration, stack_lifecycle
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md) (row RTG-57)
**Depends on**: RTG-19 (single-source stack pipeline; its SSU-F3 capacity accounting is done, 2026-09-23), RTG-36 (stack-change governance),
INF-41 (speech VRAM in the capacity gate, OP-48). Downstream, not a dependency: INF-77 DS41-C25 (run 9) waits
on KVU-1.
**Related**: [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md) DS41-C25,
[`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) KV-3 (native LCP slot pick),
[`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) SW-9,
[`autokernel-orchestrator-actor-backend.md`](autokernel-orchestrator-actor-backend.md) OAB-4a,
[`multimodal-pipeline.md`](multimodal-pipeline.md) S-11a

## Why this exists: production was never unified

The registry said "KV IS UNIFIED ON THIS SERVER" for :8083, but no production launch ever ran unified KV.
- The frozen v10 server auto-enables `kv_unified` only when `-np` is absent. In that case `n_parallel = -1` becomes
  4 slots plus unified KV (`tools/server/server.cpp:145-150`, `common/arg.cpp:1216`). Otherwise the default is
  `false` (`common/common.h:580`).
- The orchestrator always passes `-np <slots>`, and no orchestrator file mentions kv-unified. Every live
  llama-server logs `kv_unified = 'false'`.
- The "unified" evidence came from bench launches that had no `-np`, or that passed `--kv-unified` by hand.
- Under split KV each slot gets `-c / -np`. :8083 runs `-np 2 -c 196608`, so each request is capped at 98,304
  tokens.

Rule for every agent: the rule and the output-divergence caveat are in
`agents/shared/OPERATING_CONSTRAINTS.md` → *Inference and Benchmarks*, and in `wiki/kv-cache.md`.

## Evidence (all 2026-09-24)

| What | Where |
|---|---|
| Stack-change package (patches, capacity table, bring-up, serving proof, rollback) | [`artifacts/operator/stack-change-kvu-20260924/PACKAGE.md`](../../artifacts/operator/stack-change-kvu-20260924/PACKAGE.md). The scratch original is `/mnt/raid0/llm/tmp/stack-change-kvu-20260924/`, which also holds the scratch clones |
| Stack-wide `-kvu` inventory: every live server, and the ranked candidates | [`artifacts/operator/kvu-stack-inventory-20260924.md`](../../artifacts/operator/kvu-stack-inventory-20260924.md) |
| Serving-engine technique audit (vLLM / SGLang / TGI / TRT-LLM), with the steal list T1–T14 | [`artifacts/operator/serving-engine-technique-audit-20260924.md`](../../artifacts/operator/serving-engine-technique-audit-20260924.md) |
| GPU np × ctx study: 27B split vs unified, O-2, pool-full repro, MTP depth; 35B-A3B matrix; load-only footprints; M-3; M-4 | research `artifacts/np_context_kvu_study_20260924/` (README §1–§9 + SHA256SUMS): first commit `21cf444c`; the 35B-A3B matrix, 27B load-only, M-3 (`m3_depth_production.md`) and M-4 (`m4_np4_concurrent_live.json`) in `07060eaa`. The study README cites the package at its scratch path; the committed copy is the root path in the first row |
| Signed GPU-residency package (revision 3, the one OP-54 applied) | [`artifacts/operator/stack-change-kvu-20260924/revision-3/PACKAGE.md`](../../artifacts/operator/stack-change-kvu-20260924/revision-3/PACKAGE.md) with `patches/` (copied 2026-09-24 from the scratch `v2/` + `patches/v2/`; the files at the directory's top level are revision 1) |
| CPU STT/TTS real-time study | research `artifacts/speech_cpu_realtime_20260924/README.md`: 17:14Z snapshot `21cf444c`; option C (`smtC`) `07060eaa`; addendum 3 (the live production layout under CPU LLM load) `6afc7eed` |
| Durable reference: CPU speech vs CPU LLM contention, speech options, and the GPU constraints voice work depends on | [`docs/reference/speech/cpu-speech-contention-20260924.md`](../../docs/reference/speech/cpu-speech-contention-20260924.md) |
| Live working view (database-backed page) | https://claude.ai/artifact/Lr4Xd1jBwUW3ToDCQJCEjm |
| Orchestrator: context-overflow handling | `feat/context-overflow-handling-20260924` @ `8bbe2a3c` (80 tests), plus `5ca21957` route-by-live-limit; **merged as orch main `8a0c0944`** |
| Orchestrator: promotion-gate fix | `fix/promotion-gate-red-20260924` @ `d7ab368e`, **merged as orch main `ff67bbec`**. Strict is green via option A: `9692c7f9` was merged on the operator's direction |

**Measured on the 27B (Qwen3.8-27B Q8_0, v10 GPU binary, MTP draft).** Each cell is one sample, and the workload
is olympiad-style reasoning.
- Per-request decode, unified vs split, across np 1/2/4 × L 2k/8k/32k:
  - np1: equal within 1.1%, with byte-identical outputs (unified is −1.1% at 8k and −0.4% at 32k).
  - np2 and np4: unified is +0.3% to +5.7%.
- Aggregate np4 is lower under unified (−8% at 8k, −16% at 32k). At np2/np4 the two arms generated different
  answers, so this difference is not attributed to KV mode (see KVU-8).
- A 124,174-token prompt is accepted under unified (399.9 tok/s prefill). Split returns HTTP 400 at 98,304 tokens.
- O-2 (`-ctkd/-ctvd q8_0`) costs no per-request speed. Its 0.35 GiB saving, like the +0.75 GiB kvu mask, comes
  from the package's buffer model at `-c 196608`, not from these runs.
- MTP draft depth 4 vs 8:
  - acceptance 0.63–0.66 vs 0.37–0.46 (all depth-8 cells);
  - per-request decode +7.8% (np2 2k), −2.4% (np2 8k), +2.4% (np4 8k);
  - 1014 MiB less at production shape (whole-device VRAM, load-only: 64,582 vs 63,568 MiB).
- np 8 does not fit in either arm. At L2048 it was skipped with 63 GB in use; at 8k and 32k it fails to load
  (out of memory on KV, compute or `rs cache` buffers).
- With a full pool, unified fails one request with `speculative batch index 8 is not inside the current sub-batch
  [0, 8)` in 4 of 4 runs. Split never errors: it silently truncates at the slot.
- Unified and split produce different outputs at the same seed at np2/np4. The outputs are identical at np1.

## Start here

0. **2026-09-24 ~19:50Z:** OP-54 applied and serving-proven (KVU-1). CPU speech is not real time while a `-t 96` CPU
   LLM role generates, and the collision is two-sided (KVU-11b). Operator decision 2026-09-24: **D, no change**,
   superseded by the operator's forthcoming STT/TTS integration plan.
   Everything below this line is the history of how the package got signed.
1. OP-54 (package signature) gates KVU-1. **Operator rulings 2026-09-24 ~17:50-18:10Z:** OP-55 decided — ALL recommended (reroute only `ingest_long_context`; route by the LIVE per-request limit instead of the ~5k threshold; cache_ram 65536 :8083 / 32768 :8070 / 16-32k :8074 / 0 :8086 via the package; opencode bypass = live /slots + retry, /v1 routing later under HS-4). OP-56 decided — move whisper STT to CPU ("move it back to CPU"); cores from the option-C (SMT siblings) result; it is what makes :8083 `-np 4` fit. OP-52 (CPU window for the MTP-probs fix) granted and validated by the TD-21 session. Revised package in preparation (np4 + kvu + O-2 + depth 4 + whisper→CPU). Work everything else
   meanwhile.
2. Before applying any patch, re-run `git apply --check` on each one. The package was cut against orchestrator
   `71be6ed3` and research `21ca61b0`, and both mains have moved since.
3. Reload ownership. Whoever owns the inference owns the reload. The N-4 timing premise in the package (a DS41
   run-8 planner boundary) no longer holds, because run 8 was stopped 15:32Z. The reload must still land before
   DS41 run 9 starts, and it must not overlap a live GPU sweep.

## Tasks

### Done this session
- [x] **KVU-0a — root cause: production was never unified** (see above). ✅ 2026-09-24
- [x] **KVU-0b — stack-change package for :8083** (patches 1–3 default, O-2 optional, capacity table, serving
  proof, rollback). ✅ 2026-09-24
- [x] **KVU-0c — stack-wide `-kvu` inventory**, with the ranked candidates. ✅ 2026-09-24
- [x] **KVU-0d — serving-engine technique audit.** T2, T3, T5, T6 and T7 went onto the overflow branch. ✅ 2026-09-24
- [x] **KVU-0e — overflow branch built.** `fca70439` detects both overflow kinds on all four transports, resolves
  the limit from `/props`, admits by FCFS token reservation, and recovers by retry → reroute → typed 413/503.
  `8bbe2a3c` adds live `/slots` occupancy, the adaptive decode reservation, a bounded queue that returns 503,
  the `max_tokens` clamp, `context_length` on `/v1/models`, classifies the MTP sub-batch error as
  `pool_exhausted`, and classifies split truncation as `context_limit`. 80 tests. ✅ 2026-09-24
- [x] **KVU-0f — 27B GPU matrix, split vs unified**, with O-2, the pool-full 3× repro and MTP depth 4/6/8.
  ✅ 2026-09-24
- [x] **KVU-0g — CPU STT/TTS real-time study (C1).** ✅ 2026-09-24
- [x] **KVU-0i — bare-`OK` final answer dropped on the /v1 REPL path** (found post-reload during the KVU-1
  serving proof; pre-existing). `FINAL(OK)` with an unquoted identifier raised `NameError` and returned empty
  content; `rescue_bare_name_final` now rescues it. Orch `41ecf9fc`, merged `3a61c153`; API reloaded, repro
  fixed. ✅ 2026-09-24
- [x] **KVU-0h — promotion gate reduced from 14 errors to 4** on `fix/promotion-gate-red-20260924` (stale tests
  re-fixtured to the 2026-09-22 lineup, sources pinned repo-relative, derived artifacts recompiled). Strict went
  green at `d7ab368e` via option A (KVU-4). ✅ 2026-09-24

### A — :8083 bring-up
- [x] **KVU-1 — apply the signed `-kvu` package and prove it serves** (OP-54). ✅ 2026-09-24 — applied as the
  revised revision-3 package (not the np2 funding below): `-np 4 -c 196608 --kv-unified --spec-draft-n-max 4 -ub
  2048 --cache-ram 65536`, O-2 **dropped** (a q8_0 draft cache adds a 768 MiB FA conversion buffer), STT → CPU
  0-23, TTS → CPU 24-39 via the `nprocs` shim. Orch `0a564a1f` (plus the contention-matrix re-bench, topology
  `4893e37e`), research `75ee1b8e`. Serving proof: :8083 pid 2009477 logs `n_slots = 4, n_ctx_slot = 196608,
  kv_unified = 'true'`; a 124k-token request served; jfk.wav RTF 0.20; TTS first packet 97 ms; both speech
  services 0 VRAM; `orchestrator_stack.py status` shows no attestation warnings; promotion gate green. The text
  below is the pre-revision plan, kept for the record.
  - Defaults: patches 1–3. Recommended funding: `-np 2 + -kvu + O-2`.
  - O-2 measured neutral: per-request 39.4 vs 37.1 tok/s at 2k and 41.0 vs 41.3 at 8k, acceptance 0.428/0.420 vs
    0.403/0.448. The package's buffer model says it frees 0.35 GiB, which raises card headroom from 0.18 to
    0.53 GiB.
  - Optional: MTP depth 8 → 4, measured neutral. Acceptance is 0.63–0.66 vs 0.40–0.46; per-request 40.0 vs 37.1
    (np2 2k), 40.3 vs 41.3 (np2 8k), 29.7 vs 29.0 (np4 8k), i.e. within ±2.5% except the +7.8% cell. It uses
    1014 MiB less whole-device VRAM at `-np 2 -c 196608 -kvu` (load-only).
    That workload was olympiad-style, so **confirm on production traffic** (KVU-1b) before the recipe changes.
  - Run package §5 phases 7–8 and all seven §6 serving proofs. Report what each proof returned; `healthy` is not
    proof.
- [ ] **KVU-1a — opencode `limit` (N-3).** Apply `patches/opencode-OPERATOR-ACK-limit.patch` (operator, outside
  containment) together with the reload, then restart opencode. Retire this manual step once the overflow branch's
  `/v1/models` `context_length` (T7) is live and opencode reads it.
- [ ] **KVU-1b — production-traffic confirmation of MTP depth 4** before changing `--spec-draft-n-max`. Compare
  `mean len` and t/s on real planner traffic at equal prompt length, with the §6 rollback thresholds.
  - **2026-09-24 M-3 (log-only): NOT confirmed.** Depth 4 went live with OP-54 before this check. Depth-8
    production arm n=240 (median context 63.5k, mean accepted 4.86, acceptance 0.483, 38.2 tok/s); depth-4 arm
    0 organic requests (its 22 are probes or M-4). A truncation projection from the depth-8 log — a model, not a
    measurement — puts depth 4 at 0.93× depth 8 for the median request and 1.01× aggregate; positions 5–8 carry
    27.5% of accepted tokens on production traffic. Research
    `artifacts/np_context_kvu_study_20260924/m3_depth_production.md` (`07060eaa`).
  - [ ] **M-3b — resolve depth 4 vs 8 at production context.** Let organic depth-4 traffic accrue to ~175
    requests (resolves an effect of ~8%), re-run the M-3 log read, and if the difference is inside 8% run a
    same-window A/B (depth 8 vs 4 alternating on :8083) for the ~2.5% effect. If depth 4 loses by more than the
    §6 rollback threshold, revert `draft_max` to 8 through a stack-change reload.
  - **SUPERSEDED 2026-10-03 (KVU-1b and M-3b):** :8083 no longer runs MTP. Since `RATIFY-STACKCHG-DFLASH2-20261003`
    it serves DFlash2 (`--spec-type draft-dflash --spec-draft-n-max 8`, clamped to 7; PID 3793153), so MTP depth 4
    vs 8 has no production arm left. The DFlash2 depth question (n-max 7 vs 8) is KVU-16; the production-shape
    speed/correctness check is `qwen38-27b-replace-qwen36.md` Q38-T7. Boxes left for their owner to close.
- [x] **KVU-1c — add the context-checkpoint read to the serving proof.** ✅ 2026-09-24 — :8083 was reloaded
  with `LLAMA_ARG_LOG_VERBOSITY=4`; its log since the np4/kvu launch holds 26 `created context checkpoint` lines
  (first: slot 3, task 1, `checkpoint 1 of 32`, 150.2 MiB), read-only from
  `epyc-orchestrator/logs/llama-server-8083.log` at 19:54Z. Original task: With `-lv 4`, confirm `created context
  checkpoint` fires on :8083 (audit #8 / T14). This is the only partial-prefix reuse the hybrids get.
- [ ] **KVU-1d — replace the `vram_non_kv_gib` UNVALIDATED line** (still open after bring-up: research
  `75ee1b8e` declares 32.80 as UNVALIDATED, and the package's proof step 2 reading was not written back) with KFD − 6.375 from the M-1 reading. Record the
  reading through SSU-F3's prepared claim tuple (RTG-19; SSU-F3 itself is done).
  - 2026-10-03: the master figure is now `vram_non_kv_gib: 37.92` MEASURED for DFlash2 (research `be2cc414`, KFD on
    PID 3737649 minus 6.38 GiB KV, `vram_non_kv_drafter: dflash2`); the load-time peak was sampled at bring-up
    (43.49 GiB card-total, `qwen38-27b-replace-qwen36.md` Q38-T8). The 32.80 UNVALIDATED line is gone. Still open
    here: recording the reading through SSU-F3's claim tuple.
- [x] **KVU-1e — M-4: np4 aggregate under concurrent load, live.** ✅ 2026-09-24 — live :8083 (np4, kvu, depth
  4), fixed-length 1024-token generations (`ignore_eos`), 2 waves per level: aggregate 40.2 / 39.9 tok/s at
  concurrency 1, 71.4 / 67.8 at 2, 95.3 / 93.1 at 4; per-request median 40.5 / 40.2, 36.4 / 34.9, 27.6 / 26.1.
  Research `m4_np4_concurrent_live.json` (`07060eaa`). Feeds KVU-8.
- [x] **KVU-2 — size `serving_shape.cache_ram` per server** ✅ 2026-09-24 — applied with OP-54: live argv
  `--cache-ram 65536` on :8083, `32768` on :8070 and :8074 (and the frontdoor halves), `0` on :8086 (read from
  `/proc/<pid>/cmdline`). (audit #4 / T8; OP-55). Today every server runs the
  8192 MiB default, and one full-pool 27B prompt (~9.2 GiB, inferred) does not fit.
  - Recommendations: 65536 MiB on :8083 (floor 24576), 32768 on :8070, 16384–32768 on :8074, 0 on :8086.
  - The value compiles to `-cram` already. Land it at the same :8083 reload if the operator agrees; a second
    reload costs a planner transient.
- [x] **KVU-15a — close step 1's two known gate limits** ✅ 2026-10-04 (filed 2026-10-03, workspace-ec, from the KVU-15 landing,
  orch 2586a7bb). **BUILT 2026-10-03, NOT DEPLOYED:** orch cdf0f9b4 (host-wide `fcntl.flock` lease per server,
  `ORCHESTRATOR_KV_POOL_CROSS_PROCESS_LEASE=0` reverts; new-token sizing from the longest prefix an IDLE slot holds,
  margin `ORCHESTRATOR_KV_POOL_CACHE_CREDIT_MARGIN_TOKENS`), integrated on orch `integ/api-reload-2-ec` 10bc5681; not
  ticked until deployed and the done-when replay below has run (deploy = UFH14-DEPLOY-EC in
  `agentic-serving-harness-fixes.md`). (1) The long-prefill lease is per uvicorn worker; across the 6 workers it relies on `/slots`, which sees a
  long prefill only after ~4096 processed tokens plus a 1.5 s cache, so two workers can start long prefills seconds apart:
  move the lease to a cross-process primitive (flock or the region-lock layer). (2) Size is judged on the whole prompt, so a
  mostly-cached long prompt still waits: subtract the matching slot's cached prefix (`cache_n` from the serving records)
  when estimating new tokens. Done when a 2-worker replay shows peak 1 long prefill and a cached-prefix request is not held.
  - **DEPLOYED 2026-10-03 ~14:50Z, pending live verification** (UFH14-DEPLOY-EC: merged to orch main 10bc5681, now
    aa1d6894; API-only reload → PID 1628390; full `tests/unit` 15979 passed / 0 failed). The flock lease half is live.
    The 2-worker replay waits for the :8083 restore (KVU-16e). The cached-prefix half **cannot pass in production as
    built**: the credit is inert, see the finding and KVU-15c below. Not ticked.
  - **Post-restore, 2026-10-03 ~15:40Z (workspace-ec): nothing new proven for the lease.** The only dispatched
    calls since the :8083 restore are three short passthrough calls (15:39Z, `serving_calls.jsonl`), far below the
    16384-token long-prefill threshold, so neither the flock lease nor the credit was exercised. The 2-worker replay
    is still the proof. Since 15:43:08Z :8083 runs a `LLAMA_SERVER_SLOTS_DEBUG` window (UFH14-DIAG-EC-a, experiment
    id `UFH14-A7`), where the credit goes live only because debug exposes slot text: the replay's lease half may run
    there, but its cached-prefix half must not be read from that window.
  - **PASSED LIVE 2026-10-04 02:48–02:52Z (workspace-ec), production flags** (SLOTS_DEBUG off, `slots_debug_env:
    null`), evidence `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/ec2_lease/`:
    - Lease half (run `20261004T025039Z`): two concurrent ~24k-token passthrough prompts; the flock lease was held by
      2 different API worker PIDs (3858210, 3858214), never at once (max holders 1, 1042 samples); :8083 max 1 slot
      prefilling; B waited 48.9 s for A's prefill. Peak 1 long prefill across workers.
    - Cached-prefix half (run `20261004T024825Z`): call 2 extended call 1, was credited 18,829 tokens (KVU-15c
      `fp_history`), sized as a 7,197-token prefill (`long_prefill: false`) and admitted after 5.3 ms, i.e. not held.
    - Both halves of the done-when hold, so ticked. The credit run was sequential rather than inside the 2-worker
      replay; the lease run had no cached prefix (both `cache_n` 0). UFH14-DEPLOY-EC-2a/2b record the same proofs.
  - **Finding, 2026-10-03 (workspace-ec): the cached-prefix credit is inert in production.** It reads the prompt
    text an idle slot holds from `/slots`. v10 returns slot prompt text only under `LLAMA_SERVER_SLOTS_DEBUG`
    (`tools/server/server-context.cpp` `to_json` :699-730; `slot.to_json(slots_debug == 0)` at :2541, prompt only under `!only_metrics` at :726). With debug off, a
    busy slot reports `n_prompt_tokens` / `_processed` / `_cache` but no `prompt`. Live check on :8074: an idle slot
    reports only `id`, `is_processing`, `n_ctx` and `speculative`. So the credit always falls back to whole-prompt
    sizing. That is safe, but the credit is never applied. Step 1's `/slots` prefill observation is unaffected,
    because it reads token counts, not text.
  - [x] **KVU-15c — re-base the cached-prefix credit on orchestrator-side prefix history, not `/slots` text.** ✅ 2026-10-04 (filed
    2026-10-03, workspace-ec, from the finding above)
    - Keep a per-port history of recent `prefix_fp` fingerprints and the server-reported `cache_n` from the UFH14-B4
      serving records. Credit a request with the longest prefix that history says a slot or `--cache-ram` holds,
      less the margin.
    - Until it lands, make the fallback visible: count and record `cache_credit_unavailable` (reason
      `slots_no_prompt`) on every serving record where the credit could not be computed, so an inert credit no
      longer looks like zero hits.
    - Do not read the KVU-15a credit from a `LLAMA_SERVER_SLOTS_DEBUG` window (UFH14-DIAG-EC-a): the credit goes
      live there only because debug exposes the text.
    - Done when the 2-worker replay shows a cached-prefix request admitted with a non-zero credit on a
      production-flag server, and the KVU-15a done-when passes.
    - **BUILT and DEPLOYED 2026-10-03 (workspace-ec); live proof pending, so not ticked.** orch 0f0bfa19 on main,
      API-only reload.
      - `src/scheduling/prefix_history.py` is a per-server LRU of served prompts, keyed by the UFH14-B4 `prefix_fp`
        ladder, with server-measured tokens (`timings.prompt_n + cache_n`). It is kept in-process plus a host-wide
        JSON file under flock, so a follow-up turn on another uvicorn worker is credited too. An entry survives only
        within the `--cache-ram` volume, an 1800 s window and the same server launch.
      - `kv_pool_admission` credits the longest matched prefix; `/slots` text stays a second source.
      - Serving records carry a `kv_admission` block: `cache_credit_source` (`fp_history` | `slots_text` | none),
        `cache_credited_tokens`, and `cache_credit_unavailable` per source. That also covers the "make the fallback
        visible" bullet above.
      - Tests: `tests/unit/test_kv_prefix_history.py`, plus passthrough wiring in `test_passthrough_route.py`.
      - Live proof: the GPU-block runner's `deploy_ec2_lease.py` (step 1 of
        `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/RUNBOOK.md`, :8083 serving and not parked, SLOTS_DEBUG off). PASS
        means call 2's record has `cache_credit_source == "fp_history"`, `cache_credited_tokens > 0` and
        credited / `timings.cache_n` within 0.5-1.5. It runs in the coordinated GPU block after ~18:15Z.
    - **PASSED LIVE 2026-10-04 ~02:49-02:50Z (workspace-ec)**, :8083 at production flags (`slots_debug_env: null`):
      call 2 `kv_admission.cache_credit_source == "fp_history"`, `cache_credited_tokens` 18,829 vs server
      `timings.cache_n` 22,178 (ratio 0.849); call 1 recorded `cache_credit_unavailable` `{fp_history: no_match,
      slots_text: slots_no_prompt}`, so the fallback is visible. The KVU-15a done-when also passes (above). Evidence
      `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/ec2_lease/20261004T024825Z/report.json`. This opens the
      KVU-15b count (≥ 200 credited calls).
  - [ ] **KVU-15d — primitives-lane serving records must say whether the call held the long-prefill lease.** (filed
    2026-10-03, workspace-ec, found while preparing the GPU-block runner) Passthrough records carry
    `passthrough.long_prefill`, but primitives-lane `serving_call.v1` records have no `long_prefill` field, only
    `queue.pre_dispatch_wait_ms`, which mixes lock, placement and lease wait. So the KVU-15a lease cannot be read
    from organic primitives traffic. Add `long_prefill` (and the lease wait in ms) to the primitives record through
    the same staging path that sets `kv_admission`, with a test. Done when a primitives record for a long prompt
    carries `long_prefill: true` and its lease wait.
  - [ ] **KVU-15b — measure cache-credit misses on the serving records.** (filed 2026-10-03, workspace-ec; owner's
    decision was keep the credit and measure) On unified-KV servers the credit assumes the matched prefix survives in
    `--cache-ram`; a miss costs one extra concurrent long prefill. After KVU-15a is live, count calls admitted with
    `cache_credited` whose server-reported `cached_prompt_tokens` (`timings.cache_n`) fell short of the credited
    prefix, over ≥ 200 calls on :8083 (two windows, two-sample persistence). Today `cache_credited` is an admission
    counter and a passthrough-record field; put it on every `serving_call.v1` record first if it is missing there.
    Remove or narrow the credit if misses persist above ~5% of credited calls.
    - **Moot until KVU-15c (2026-10-03).** In production the credit never fires (finding above), so there is nothing
      to miss. Re-scope against KVU-15c's history-based credit once it lands. Records from a SLOTS_DEBUG window do
      not count.
    - 2026-10-03 (workspace-ec): the field half is done. Since orch 0f0bfa19, every serving record carries
      `kv_admission.cache_credited_tokens` and `cache_credit_source`, on the primitives and passthrough lanes. The
      count still waits for KVU-15c's live proof and then ≥ 200 credited calls.
- [x] **KVU-16 — :8083 KV-pool step 2: one stack change for `-c 393216`, a 262144 per-request cap, n-max 7** ✅ 2026-10-03 (workspace-ec) — LIVE. SIGNED 2026-10-03T11:50:52Z, RATIFY-STACKCHG-KVPOOL-20261003; research 412e8fc1, orch 09e91e1e + 841935ea, archive root 64d70d17 (`artifacts/operator/stack-change-kvpool-20261003/`; live evidence in `/mnt/raid0/llm/tmp/stack-change-kvpool-20261003/{apply,evidence}/`). Bring-up after workspace-89's "F12 done": `reload architect_critic` → PID 4052768 at 13:14:35Z, argv `-c 393216 … --spec-draft-n-max 7` (`evidence/argv_8083_live_post_relaunch.txt`); server log "slot context (393216) exceeds the training context (262144) - capping", `n_slots = 4, n_ctx_slot = 262144, kv_unified = 'true'`, no clamp-to-7 warning. Load-peak VRAM 50.78 GiB (`evidence/vram_during_reload.log`). API reload → PID 4054223; `context_limits` per_request 262144, kv_unified True, shared_pool True, pool_tokens 393216. Alias completion via :8000 `coder_escalation` correct with draft acceptance logged (`apply/completion.json`). `stack_change_pipeline check --run-promotion-gate` all ok incl. runtime_attestation (`apply/check-final.out`). The 4 × 90k concurrency probe is NOT a pass — see KVU-16b/16c; full-pool concurrent residency is UNPROVEN, not disproven. :8083 has been stopped for the INF-80 X0 window since 13:55Z (KVU-16e restores it).
  - Original scope:
  (operator-approved 2026-10-03, IN PACKAGING; decision package
  `/mnt/raid0/llm/tmp/kv-sizing-8083-20261003/DECISION.md` §4 step 2). One :8083 relaunch carrying: `-c` 196608 →
  393216 unified at np 4 (+4.86 GiB → ~51.4 GiB, 12.5 GiB free; four concurrent p90 prompts fit); an orchestrator
  per-request cap of 262144 (= `n_ctx_train`; `context_limits.py` `per_request_n_ctx` must take
  `min(n_ctx, n_ctx_train)` once `-c` exceeds it); `--spec-draft-n-max` 8 → 7 (the kernel already clamps to 7; the
  GDN ring is sized from the unclamped value, so 7 should save ~0.58 GiB); re-derive `vram_non_kv_gib` for the new
  depth (DRAFT-SEL-1's `check_lean` refuses a selection whose VRAM was not re-derived). Bring-up with `-lv 4`:
  read the `llama_kv_cache` / `memory_recurrent` / `sched_reserve` lines and KFD at load (expect ~51.4 GiB), then
  one synthetic 4 × 90k concurrent replay: zero "failed to find a memory slot", KFD peak ≤ 62 GiB. Before
  packaging, run DECISION §4 measurement 1 (zero compute: regress per-slot decode vs pool high-water on the
  existing log); if decode with neighbours is >15% slower at 300k+ fill than at 100k, take option (c) split
  4 × 163840 instead. Fix the "3 GiB" comment at `stack_manifest.py:1690` (code uses 2.0) in the same package.
  - [ ] **KVU-16a — replace the derived `vram_non_kv_gib` with the measured one.** (filed 2026-10-03, workspace-ec,
    from the KVU-16 bring-up) The package carries a derived 39.15 GiB; the bring-up measured 50.78 GiB load peak −
    12.75 GiB KV pool ≈ 38.03 GiB (`evidence/vram_during_reload.log`). Land the measured value in the research master
    with its evidence pointer through the stack-change pipeline (registry value, DRAFT-SEL-1 `check_lean` reads it),
    and recompile. Done when `check` passes and the lean carries 38.03 with an evidence path.
    - *(Annotation, workspace-ec, 2026-10-04.)* **PACKAGED, VALID, awaiting the operator's signature** in
      STACKCHG-HYGIENE-20261003 (`/mnt/raid0/llm/tmp/stack-change-hygiene-20261003/PACKAGE.md`; `--validate-only`
      VALID, 68 pins; `validate-main.out`): 39.15 derived → 38.03 measured (50.7822 GiB load peak − 12.75 GiB KV pool;
      evidence copied to `evidence/vram_during_reload_8083_20261003.log`). Argv identity 11/11 live servers, so no
      relaunch. Not ticked until signed, applied and `check` passes.
    - *(Annotation, workspace-ec, 2026-10-04.)* 38.03 GiB is right as a LOAD-time figure, and OP-72 can be signed
      as packaged. However, :8083 grows +7.2 GiB while serving (KVU-16h), so the load-time figure understates the
      runtime peak. The runtime term is KVU-16i; it does not change this item.
  - [ ] **KVU-16b — a corrected concurrent-residency proof for the 393216 pool.** NOTE (2026-10-03, workspace-89 P3 code read): production runs `cache_idle_slots` ON, so idle slots are flushed to RAM at each task launch and the pool can only fill with ACTIVELY GENERATING sequences. The proof must hold 4 long contexts DECODING at once (long `n_predict`), not parked. P3 part A1 uses `--no-cache-idle-slots`: cite it only as a mechanism result, NOT as a production residency proof. (filed 2026-10-03, workspace-ec)
    - **Correction (2026-10-03, workspace-ec, from the P3 report):** the idle-purge claim above is a CODE READ, not a
      measurement. P3 arm A0 ran at the exact production flags and did NOT reproduce the purge: its neighbour slot held
      0 tokens before the probe task, so the purge path was never exercised (inconclusive). "Production always purges
      idle slots" is therefore NOT proven. The design rule stands anyway: holding 4 contexts DECODING at once is valid
      whether or not idle slots are purged. Measuring whether the purge happens is folded into UFH14-B4i's A/B.
    - **Second correction (2026-10-03, workspace-ec, read-only log read while preparing the GPU-block runner): the
      purge IS real on organic traffic.** `logs/llama-server-8083.log` holds **211 idle-slot purges of non-empty
      slots** between log lines 35430 and 130878. Each is a `saving idle slot to prompt cache` line followed by
      `clearing prompt with N tokens` with N > 0, 11.5 M tokens in all. The latest is line 130621, `id 2 | clearing
      prompt with 84951 tokens`. All are at the previous kv-unified shape (np 4, `n_ctx_slot` 196608), before the
      393216 relaunch. So "not reproduced" described P3 A0 only, not production. At the current shape it is still to
      be shown; `kvu16b_residency.py` records it with an optional 1-token purge probe.
    - Runner prepared, dry-run OK: `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/kvu16b_residency.py` (RUNBOOK step 4,
      :8083 serving with its roles parked). It holds 4 long contexts decoding at once and samples `/slots` and KFD
      during the run. Exit 0 = PASS against the done-when above. It runs in the coordinated GPU block after ~18:15Z.
    The probe (`evidence/concurrency-probe-20261003T135133Z.json`) failed its own criterion: max cells in flight 92,343
    vs ≥ 300k. What held: 4 × 89,921-token requests all 200, zero "failed to find a memory slot", zero "Context size
    has been exceeded", 4 slots processing at once, KFD peak 51.73 GiB (≤ 62). Why it failed: the server prefilled
    largely serially (done at 263 / 682 / 1328 / 2166 s) and `n_predict 64` freed each request's cells right after its
    prefill. Re-run with long generations (`ignore_eos`, n_predict large enough to outlast the slowest neighbour's
    prefill) so all four contexts are resident at once; sample `/slots` cells and KFD during, not after. Done when
    peak resident cells ≥ 300k with zero memory-slot lines and KFD ≤ 62 GiB. Closed instead by KVU-16c if that
    evidence exists. Needs a :8083 window, so it runs after the X0 hand-back (KVU-16e).
    - **2026-10-04 (workspace-ec): RAN; the runner said PASS, but the PASS is INVALID, so this box stays open.**
      The run is `results/kvu16b/20261004T032520Z/`, with a durable copy in
      [`artifacts/gpu-block-27b-20261004/results/kvu16b/`](../../artifacts/gpu-block-27b-20261004/results/kvu16b/).
      workspace-89's read-only root cause is `artifacts/gpu-block-27b-20261004/analysis/kvu16b-rootcause-REPORT.md`
      (original at `/mnt/raid0/llm/tmp/kvu16b-rootcause-20261004/REPORT.md`).
      - **Why the PASS is invalid:** the predicate `proc and n_dec > 0` reads a stale `n_decoded`, which resets only
        at prompt end. Request i=3 (server slot 0) was still prefilling (60.7k of 79.8k) at the PASS sample, so the
        true peak was 3 decoding + 1 prefilling.
      - **What held:** ~310k cells resident, zero "failed to find a memory slot" lines, KFD 58.88 GiB (≤ 62).
      - **Decode collapsed to 0.52 tok/s summed** (≥ 90% confidence). Prefill shares every server batch with decode:
        each iteration is the 8-row verify for every decoding slot plus ~2024 prompt tokens (`n_batch` 2048). So each
        decoding slot advances one verify step per prefill chunk. Without the masked-block skip, a chunk's attention
        reads every occupied cell, at T ≈ 2.6 s + 0.052 s per 1k cells: **17–19 s per chunk at 240–310k**. Drafting
        stayed healthy at 2.8–4.2 tokens per step; only the step rate collapsed. TTFT climbs for the same reason
        (prefill 440 → 232 → 146 → 115 tok/s for i=0..3). Context checkpoints, the drafter, `--cache-ram` and an FA
        fallback are ruled out.
      - **VRAM grew while serving:** 51.69 GiB at load, then 58.88, then 59.77 GiB during Q38-T7 #2 and still
        rising. That is +7.2 GiB, and only ~2.2 GiB of margin to the 62 GiB gate. See KVU-16h.
      - Fixes, cheapest first: KVU-16f (`-b 512`), KVU-16g (a prefill budget while slots decode), KVU-19a in
        production (workspace-89's fold, KVU-19; ~3.5× alone, ~10× with KVU-16f), KVU-19b, and KVU-20.
    - [ ] **KVU-16b-1 — fix the residency runner's decoding predicate, then re-run KVU-16b.** (filed 2026-10-04,
      workspace-ec) In `kvu16b_residency.py:203,260` (durable copy
      `artifacts/gpu-block-27b-20261004/runners/`), count a slot as decoding only when `n_proc >= prompt_tokens` or a
      first token has been observed for its request. Key the report by request index, not by server slot (request
      i=3 ran on server slot 0). Treat `/slots` poll timeouts as samples missed during an iteration, not as slot
      errors. Re-run after KVU-16f or KVU-16g lands; otherwise the run measures the interleave again. Done when the
      runner's PASS requires 4 slots past prompt end at once, and a re-run meets the done-when above.
  - [ ] **KVU-16f — A/B `-b 512 -ub 512` on :8083, then one stack change.** (filed 2026-10-04, workspace-ec, from the
    KVU-16b root cause, fix 1) `-ub` alone does nothing: the server packs `n_batch` prompt tokens per iteration. At 512,
    the root cause predicts an iteration of ~4.7 s at 300k (~4× faster decode while a prefill runs) and a KQ mask
    1536 → 384 MiB (−1.1 GiB). The registry's mask term must then be re-derived. The cost is a possible 10–20% lower
    solo prefill at shallow depth. Measure in a coordinated :8083 window: the KVU-16b runner (s per chunk and decode
    while prefilling, after KVU-16b-1), plus Q38-T7 phase B at 80k (prefill rate, paired correctness). Then ship it as
    ONE stack change together with UFH14-B4j (`--no-cache-idle-slots`). Done when the A/B is recorded here and the
    combined package is signed and serving.
  - [ ] **KVU-16g — decode-aware prefill budget on llama-server (Sarathi-style), experimental tree.** (filed 2026-10-04,
    workspace-ec; KVU-16b root cause fix 1e, KV-serving survey Rec 1) In `update_slots()`, cap the prompt tokens added
    per iteration while any slot generates (`--prefill-budget-decoding N`, or sized from a per-step time target), and
    keep `-ub 2048` for solo prefill. This shields decode without shrinking solo prefill batches, so it is the better
    form of KVU-16f. **In flight 2026-10-04:** a subagent is building it on `llama.cpp-experimental`
    (`/mnt/raid0/llm/tmp/prefill-budget-20261004/`). Risks to check: more checkpoint-creation points, and DFlash2
    verify-row indexing in `post_decode` (cf. KVU-7). Done when the KVU-16b re-run shows decode under a neighbour's
    prefill ≥ 4× better at ≤ 30% TTFT cost on the prefilling request, with `test-backend-ops` and a paired correctness
    check green. Ships with the next kernel version (four-step workflow), not as a flag on v10.
  - [ ] **KVU-16h — URGENT: attribute :8083's +7.2 GiB VRAM growth while serving.** (filed 2026-10-04, workspace-ec)
    KFD for pid 1703677 was 51.69 GiB right after load, 58.88 after Q38-T7 #1's concurrent prefill+decode traffic, and
    59.77 after Q38-T7 #2, still rising. That leaves ~2.2 GiB to the 62 GiB gate. The growth follows request shape,
    not KV occupancy: KVU-16b at 310k cells added nothing. Candidates: the ggml-cuda legacy pool (`NO_VMM=1` →
    `ggml_cuda_pool_leg`, which never frees), compute-buffer reallocation beyond the `n_seqs = n_seq_max` reserve,
    and rocBLAS/hipBLASLt workspaces. In a GPU window, relaunch :8083's argv on a scratch port at `-lv 4`, replay the
    Q38-T7 phases one at a time with phase markers, and sample KFD at 1 Hz. Done when the growth is attributed to a
    named allocator with a per-phase table, and either bounded by a flag or carried as a runtime term in KVU-16i.
  - [ ] **KVU-16i — the capacity gate must carry the RUNTIME peak, not only the load-time `vram_non_kv_gib`.** (filed
    2026-10-04, workspace-ec) The registry's non-KV figure is load-derived: 39.15 GiB derived, and 38.03 GiB measured in
    KVU-16a / OP-72, from the load peak. The runtime peak runs +7.2 GiB above that (KVU-16h). The capacity gate in
    `stack_manifest.py:1604-1626` therefore passes lineups whose serving peak is within ~2 GiB of the card limit. Add
    a measured `vram_runtime_growth_gib` term (or a runtime-peak field with an evidence path) per GPU server, and have
    `check_lean` / the capacity gate sum it. Done when the master carries the term for :8083 with KVU-16h's evidence,
    and the gate's arithmetic for :8083 reproduces the measured ~59.8 GiB peak.
  - [x] **KVU-16c — or cite workspace-89's P3 parked-neighbour run as the residency proof.** (filed 2026-10-03)
    ✅ 2026-10-03 — resolved: **NOT citable**, so KVU-16b runs. P3 A1 (`/mnt/raid0/llm/tmp/x0-27b-quants/results/p3/report.md`)
    had zero slot-failure lines, but it ran with `--no-cache-idle-slots` (not the production flag), and its ≈355k fill
    rests on the slot-restore replies: `/slots` showed only 156,971 resident tokens, because restored slots do not
    report `n_tokens` there. VRAM peak was 51.96 GiB (within ≤ 62 GiB). It is a mechanism result only.
    Workspace-89's X0 window carries the P3 probe (llama.cpp #28495, intake-1849#record: unified-KV flash-attention
    decode cost as the pool fills). If its parked-neighbour arm reports peak resident cells ≥ 300k with zero
    memory-slot lines, cite it here and close KVU-16b; otherwise run KVU-16b.
  - [x] **KVU-16d — act on the P3 decode-cost verdict: unified vs split per-slot.** (filed 2026-10-03, workspace-ec)
    ✅ 2026-10-03 — **DECIDED: keep the shared 393216 pool** (operator, 2026-10-03, this session's AskUserQuestion
    answer: "Keep shared 393k for now"). No split-per-slot stack change. Mitigation: rely on the one-long-prefill gate
    (KVU-15 / KVU-15a) and fix the kernel. The masked-block skip is KVU-19, implemented directly as KVU-19a.
    - 2026-10-03: P3 trigger MET (KVU-18 A1: −59.5% no-draft at ≈355k nominal fill, three parked neighbours; batched-bench
      kvu vs no-kvu −15.2% TG). workspace-ec is preparing the option (c) package. *(Superseded by the decision above;
      no package was prepared.)*
    - **Decision record, the options considered (VRAM at load, approximate):**

      | Option | Shape | VRAM at load | Effect |
      |---|---|---|---|
      | split 2 × 262144 | np 2, per-slot | ~52-55 GiB | full per-request context, but only 2 concurrent requests |
      | split 3 × 196608 | np 3, per-slot | ~57 GiB | per-request cap 196608, 3 concurrent requests |
      | split 4 × 163840 | np 4, per-slot (DECISION.md §4 option c) | ~59 GiB | per-request cap falls below 262144 |
      | **keep shared 393216** | np 4, unified | 50.78 GiB (measured) | **CHOSEN**: decode tax with resident neighbours remains until KVU-19 lands |

    - Reopen trigger: KVU-19a fails its validation, or the fold into the champion stalls, while organic traffic shows
      the neighbour decode tax (serving records, KVU-17).
    If P3 shows ≥ 15% decode loss at 300k+ pool fill vs ~100k, prepare the option (c) split stack change (4 × 163840,
    DECISION.md §4) for operator signature; if < 15%, record the verdict here and keep unified. Trigger: workspace-89's
    P3 result.
  - [x] **KVU-16e — restore :8083 after workspace-89's "X0 done" (ETA ~16:30Z 2026-10-03; extended, see below).** ✅ 2026-10-03 (filed 2026-10-03,
    workspace-ec) `orchestrator_stack.py reload architect_critic`; verify the live argv equals
    `evidence/argv_8083_live_post_relaunch.txt`, `context_limits` (262144 / unified / pool 393216) and one alias
    completion via :8000. :8083 is down from 13:55Z (stop verified: PID dead, VRAM 0.01 GiB; X0 argv record
    `/mnt/raid0/llm/tmp/ds41-c95/X0_ARGV_8083.txt`).
    - 2026-10-03, ~15:00Z: the X0 window was extended (granted) to a ~17:15Z hand-back. Order: X0 serving + KLD,
      then P3 (KVU-18, llama.cpp #28495), then LB1 (rocprof low-bit kernel roofline, operator-approved), then a
      speech stop plus EXL3 correctness. Whisper/TTS will be stopped for ~30 min near the end. The restore also
      unblocks the UFH14-DEPLOY-EC-2 live proofs (B6, RI-18c, KVU-15a, B4).
    - **DONE 2026-10-03 ~15:35Z (workspace-ec).** workspace-89 sent "speech back + X0 done" at 15:31Z: all its scratch
      PIDs dead, KFD list empty, VRAM 13 MB. `reload architect_critic` → PID 1064570 at 15:35:49Z, `/health` ok. The
      launch banner argv (`logs/server_launches/launches.jsonl`) equals `evidence/argv_8083_live_post_relaunch.txt`
      token for token, `argv_sha256` b865820d… (same as the 13:14Z launch). Completions via :8000 to :8083 correct at
      15:39Z (UFH14-B6 proof). `context_limits` was not re-read here. `reload whisper tts` → PIDs 1064878 / 1065102,
      health ok, TTS smoke 57,644 bytes. Production outage: :8083 13:55Z → ~15:35Z; speech ~15:00Z → ~15:35Z.
    - Later the same day, 15:43:08Z: :8083 relaunched (PID 1083497) with the UFH14-DIAG-EC-a SLOTS_DEBUG override
      (experiment id `UFH14-A7`, TTL 14400 s). Same argv; a plain `reload architect_critic` restores it.
  - Finding, not filed as a task: 4 concurrent ~90k prompts take ~36 min for the last one (2166 s). That is the
    neighbour-prefill serialisation the one-long-prefill gate (KVU-15) makes explicit by design; it is a capacity
    fact, not a defect. Declined as a separate task: the actionable part, unified vs split, is KVU-16d.

### B — orchestrator
- [x] **KVU-15 — :8083 KV-pool step 1: close the admission bypasses** ✅ 2026-10-03 (workspace-ec) — orch 2586a7bb on main, API reload: scouts reserve prompt+max_tokens on the token gate; one long prefill (≥16384 est. tokens, env ORCHESTRATOR_KV_POOL_LONG_PREFILL_TOKENS, 0=off) per server, lease ends at first chunk or prompt/250 tok/s; /slots observation holds long requests behind any slot prefilling ≥4096 (covers other uvicorn workers + direct clients like C95); per-request cap = min(slot ctx, model ctx_max). 32 new tests; 4126 related pass. Live alias call via gate ok. Remaining limits: per-worker gate (cross-worker via /slots only), whole-prompt size even when mostly cached; ungated paths documented in /mnt/raid0/llm/tmp/kv-gate-8083-ec/BYPASS.md (action_repair_completer if pointed at :8083; prewarmer only :8074). Was: (operator-approved 2026-10-03, IN PROGRESS;
  `/mnt/raid0/llm/tmp/kv-sizing-8083-20261003/DECISION.md` §3(d), §4 step 1). All 17 pool-exhaustion episodes in
  the 8083 log were four ~45-55k contexts filling the 196k pool, and `logs/orchestrator.log` holds zero
  `SharedKVPoolAdmission` queue lines: the load never passed through the gate. No relaunch, API reload only:
  - route :8083 traffic through the token gate — scouts reserve TOKENS, not slots (`scout_stage.py:39-50`,
    `:250-266`, `:726-753`);
  - one long prefill (≥ 8k tokens) at a time per URL, which targets the 28.6 → 7.8 tok/s neighbour-prefill decode
    collapse (`kv_pool_admission.py`);
  - re-point remaining direct :8083 clients (AutoKernel/DS41 harnesses, opencode, codex, Hermes, C95) at :8000.
  Done when a replay of concurrent long prompts through :8000 queues FIFO with zero "failed to find a memory slot".
- [x] **KVU-17 — serving telemetry: record per-call server timings, including streamed chat** ✅ 2026-10-03 —
  LANDED orch c6225e8b/f7fad574/9a0d38e0 on main, API reload 04:59Z; a live :8083 call logged prompt_eval_ms 2368 ms,
  queue wait 113 ms, role/request_id/orch_commit (logs/serving_calls/serving_calls.jsonl). Was (IN PROGRESS
  2026-10-03; scratch `/mnt/raid0/llm/tmp/serving-timing-ec/`, new `src/backends/serving_calls` module, 44 tests
  pass on the candidate `llama_server.py`). The chat-stream path ignored the `timings` object llama-server
  attaches to the last chunk and hard-coded `prompt_eval_ms = 0.0`, so every streamed completion logged zero
  prefill time and no draft acceptance. The change records `prompt_ms`, `predicted_ms`, `cache_n`, `draft_n` and
  `draft_n_accepted` per call (`infer`, `infer_stream_text`, `/completion`, `/v1/chat/completions`). It is the
  instrument for KVU-15/16 (decode vs pool fill) and Q38-T7 (DFlash2 acceptance on organic traffic). Land on orch
  main, `reload orchestrator`, prove one streamed completion logs non-zero `prompt_eval_ms`, and wire the records
  as a belief-kernel source (VB-SERVING-DF2).
- [x] **KVU-3 — land `feat/context-overflow-handling-20260924` @ `8bbe2a3c`** once OP-55 decides: ✅ 2026-09-24 —
  OP-55 decided "all recommended"; `5ca21957` added route-by-live-limit; merged as orch `8a0c0944` (351 targeted
  tests pass on the merge), shared clone fast-forwarded, API reloaded (orchestrator only); `/v1/models` shows the
  live per-request context. Original decision list:
  - reroute roles (add `architect_critic` at 262144?);
  - the long-context threshold (tokens, ~5k now);
  - `cache_ram` sizes (KVU-2);
  - an unbounded-generation cap;
  - an opencode bypass.

  Then merge, and the owner runs the API reload (`orchestrator_stack.py reload orchestrator`, API only).
- [ ] **KVU-3a — detect truncation of streamed chat.** The branch cannot see it today, because the stream carries
  no token counts. Request usage in the stream (`stream_options.include_usage`), or count streamed tokens against
  the live limit, and mark `completion_reason=context_limit`.
- [x] **KVU-4 — promotion gate: clear the 4 strict known-gap errors.** ✅ 2026-09-24 The operator chose option A:
  `option/critic-general-suite-evidence-20260924` @ `9692c7f9` was merged into the fix branch as `d7ab368e`.
  Strict now counts `general_suite_quality` as per-axis evidence, never as `overall`. The role-purpose critic-suite
  gap remains open as RTG-19 SSU-F16.
- [x] **KVU-4a — clear the gate's only remaining failure: runtime attestation.** ✅ 2026-09-24 — :8180, :8080,
  :8074, :8070 reloaded on `-ub 2048` (18:16–18:18Z, healthy, frontdoor completion ok); the branch merged as orch
  `ff67bbec`; the promotion gate is green. :8083 followed with KVU-1. :8070, :8074, :8080 and :8180 run
  with `-ub 8192` live, but K4 declares 2048. The change is inert, because effective ubatch was already 2048 by
  clamp. :8083 rides KVU-1.
  - The owning session reloads those four after the running speech test, then merges
    `fix/promotion-gate-red-20260924` @ `d7ab368e` and re-runs the gate in the shared clone.
  - Do not merge while the shared orchestrator clone holds another session's uncommitted edits.
  - Acceptance: `stack_change_pipeline.py check --numa-mode both --run-promotion-gate` is green.
- [ ] **KVU-5 — preemption on the orchestrator side** (audit #6 / T4a). When the pool is short, cancel the youngest
  or lowest-priority in-flight request, optionally after `POST /slots/{id}?action=save`, and requeue it idempotently
  with the same request id.
  - Needs a cancellable in-flight registry per URL and a request priority field, and it must preserve the FCFS
    no-starvation invariant.
  - This is the only way to turn the server's abort-all into one recompute without touching the kernel.
- [ ] **KVU-6 — cache-aware ordering on kvu servers** (audit #7 / T9).
  - Stop pinning `id_slot` on unified servers: the server clears idle slots anyway, and the RAM tier is what
    keeps the prefix.
  - Add a bounded longest-prefix-match bypass to the admission queue (at most one skip per waiter).
  - Coordinate with INF-05 KV-3, which is the same lever (native LCP slot pick). Move this task there if INF-05
    takes it.
- [ ] **KVU-13a — ambient `LLAMA_ARG_*` env is invisible to the cmdline attestation.** `-kvu` on argv wins, but an
  ambient `LLAMA_ARG_N_PARALLEL` would not be seen. Extend `_live_kv_unified()` (patch 3) to read
  `/proc/<pid>/environ`, or scrub `LLAMA_ARG_*` from the launch env. Same class (package revision 3 §9): an
  ambient `LD_PRELOAD` / `SHIM_NPROCS` in the launcher's parent env would reach every aux service, because
  `build_service_env` starts from `os.environ`; scrub both unless the service entry declares them.
- [ ] **KVU-13b — the stack-change skill's DERIVATION source list omits the files a new launch flag needs**
  (`src/registry/stack_priors.py`, `scripts/server/stack_commands.py`, `scripts/server/orchestrator_stack.py`, and
  per package revision 3 §9 also `scripts/server/stack_manifest.py` and `scripts/voice/`).
  Also, `preflight.sh`, `capacity.sh` and `topology_check.py` hardcode the real ORCH path, so they cannot run
  against a scratch clone. Fix both in `.claude/skills/stack-change/`.
- [ ] **KVU-13c — the capacity gate runs at import of `stack_manifest`.** A lineup that fails capacity makes the
  launcher and the pipeline un-importable, so the tool you would use to fix the lineup cannot load (hit in the
  package scratch, revision 3 §9). Move the gate to an explicit call (pipeline `check` / launcher pre-start) and
  keep import side-effect-free; test: a failing lineup still imports and `check` reports the failure.
- [ ] **KVU-14 — session-keyed admission hold on shared-pool servers (DESIGN; opens only if dynamic-stack-concurrency.md G5 finds cross-session eviction).** ThunderAgent's contract (intake-1816#1, intake-1816#4, intake-1816#6): a session is REASONING while a request is in flight and ACTING from response completion; capacity = the unified KV pool plus `--cache-ram`; under pressure, hold the NEXT turn of the smallest idle (ACTING) sessions at admission — never mid-decode — and resume shortest-first with hysteresis and a forced-resume timeout (HSF-3 p99). Optionally back the hold with `POST /slots/{id}?action=save` to RAM (the verb KVU-5 uses). Reads the ONE session table (heterogeneous-slot-fabric-residency.md tracked-session index; identity from harness-selection-and-integration.md HS-16); shares the admission queue with KVU-5/KVU-6; no second occupancy notion. Upstream ThunderAgent and Dynamo's plugin are not deployable here (vLLM/SGLang backends only; Dynamo frontend only).

### C — kernel candidate (v11, guarded)
- [ ] **KVU-19 (intake P5) — masked-block skip for unified-KV flash attention on `llama.cpp-experimental`.
  Trigger: KVU-18 measures a decode loss of 5% or more.** Upstream trims only the fully masked *tail* of the KV
  range, and the launch gate never fires for unified-KV decode (`n_stream` == 1). So a decode or verify step
  attends over every block that other slots' sequences occupy (`intake-1849#00`). Skip masked blocks anywhere in
  the range, not just at the tail, for the decode and verify shapes, HIP/gfx90a first. No upstream fix exists:
  the WMMA-only PR #28943 closed unmerged (`intake-1849#03`). Four-step workflow; validate on the KVU-18 cells
  and on the DF2 verify shape (n_max 7). Not triggered means no kernel work.
  - **TRIGGERED 2026-10-03** by KVU-18 (no-draft decode −32.6% with one ~99k parked neighbour, −59.5% with three).
    Validate on the KVU-18 A1 cells (same P, 0/1/2/3 neighbours) plus the DF2 verify shape. Whether the split stack
    change (KVU-16d) lands first changes the production stake, not the kernel case: any unified-KV deployment
    with parked neighbours pays this tax.
  - *(Annotation, workspace-ec, 2026-10-03; this item stays workspace-89's.)* KVU-16d is decided **keep shared
    393k**, so production keeps paying the tax until this lands. The operator asked for the skip to be implemented
    DIRECTLY, without waiting on AutoKernel, and folded into the champion. The implementation is KVU-19a (workspace-ec);
    the champion fold and the full-scale P3 re-measurement stay here with workspace-89.
  - *(Annotation, workspace-ec, 2026-10-03 ~17:15Z; this item stays workspace-89's.)* KVU-19a is built: fold record
    [`docs/design/fa-masked-block-skip-20261003-fold.md`](../../docs/design/fa-masked-block-skip-20261003-fold.md)
    (cherry-pick ac97e305a + a0d0ae238; both clean onto b3e0b0902). The P3 re-run needs a `BIN` override in
    `p3_kvu_probe.sh` and `x0_common.py`, and arms new build vs the same binary with `GGML_CUDA_FA_MASK_SKIP=0`.
    workspace-89 was asked to run it on its harness in the coordinated GPU block after ~18:15Z. Falsifiable
    expectations: at L3, drafted ≥ ~33 tok/s (was 15.4) and no-draft ≥ ~19 (was 8.3); batched-bench `-kvu` S_TG within
    ~5% of `-no-kvu` (was −15.2%); L0 unchanged within noise. Its records project under VB-KVU-P3.
  - *(Annotation, workspace-ec, 2026-10-04; this item stays workspace-89's.)* KVU-19a-1 passed on the store build
    (02:25-02:47Z), but the batched-bench expectation above already FAILS at small scale: 4×16k `-kvu` S_TG 444 vs
    `-no-kvu` 542/551 t/s (base 437). The skip is per tile, and a batched decode tile spans all sequences. Single-
    sequence decode/verify behind idle neighbours is fixed (P3-mini 82 → 169 steps/s). Per-row skipping is KVU-19b.
  - *(Annotation, workspace-ec, 2026-10-04 later; this item stays workspace-89's.)* The KVU-16b root cause raises
    the production stake. On :8083's mixed prefill+decode iterations, the skip is estimated at ~3.5× decode on its
    own and ~10× with KVU-16f's `-b 512`: the i=3 prefill attends ~40k own cells against ~275k occupied. The fold's
    P3 v2 can use the KVU-16b replay (after KVU-16b-1) as its full-scale cell. KVU-19b's store build
    `gpu-20261004-c7f5ac9ad` carries the KVU-19a arm too (`GGML_CUDA_FA_SEQ_ROWS=0`).
  - *(Annotation, workspace-ec, 2026-10-04 05:05Z; this item stays workspace-89's.)* KVU-19b-1 scored the KVU-19b store
    build: fold **commit 1 only** (`1bceceb05`, batched-decode vec routing: 5.5 vs 9.2 ms at 4×80k; batched-bench
    `-kvu` 522 vs `-no-kvu` 529 t/s). Commit 2 (`c7f5ac9ad`) is out until KVU-19b-rework-c2 lands. Filed as
    KVU-19b-fold-c1.
  - [x] **KVU-19a — implement masked-block skip directly; fold via workspace-89.** ✅ 2026-10-04 (filed 2026-10-03, workspace-ec;
    operator instruction 2026-10-03, implements KVU-19) IN PROGRESS: an Opus subagent on a new `llama.cpp-experimental`
    branch from the global champion 90c12df42 (`ak/champion/llama-cpp-ffc1bac82eec`).
    - Scope: the HIP (gfx90a) and CPU flash-attention kernels skip fully masked KV blocks anywhere in the range, not
      just the tail, for the decode and verify (n_max 7) shapes.
    - Correctness: `test-backend-ops` cases with multi-sequence masks.
    - Speed: a small-model micro-bench, with 0/1/3 resident neighbours.
    - Build into a new `kernels/builds/` dir; a feature commit plus `FOLD.md`, with a trial merge onto the DS41
      accumulator b3e0b0902.
    - Hand-off: workspace-89 folds it into the champion with DS41's promoted keeps and runs the full-scale P3
      re-measurement window (KVU-19). Never touches the frozen production tree.
    - Done when `test-backend-ops` passes with the new masks, the micro-bench shows the neighbour tax reduced, and
      `FOLD.md` plus the trial-merge result are handed to workspace-89.
    - **BUILT 2026-10-03 (workspace-ec); GPU validation on the store build pending, so not ticked.** Fold record:
      [`docs/design/fa-masked-block-skip-20261003-fold.md`](../../docs/design/fa-masked-block-skip-20261003-fold.md)
      (durable copy of `/mnt/raid0/llm/tmp/fa-maskskip-20261003/FOLD.md`).
      - Branch `experimental/fa-maskskip-20261003` from champion 90c12df42, pushed to `fork`: ac97e305a (GPU plus
        `test_flash_attn_ext_unified`, 52 cases) and a0d0ae238 (CPU). Store builds
        `kernels/builds/gpu-20261003-a0d0ae238` and `cpu-20261003-a0d0ae238` (build 10310); linkage PASS.
      - Kernels: all 4 HIP FA kernels, the CDNA2 fused-combine vec path and the CPU path. A new scan kernel marks
        live/dead 256-cell blocks per query tile. On gfx90a, plain decode uses vec, and verify/batched/prefill use
        WMMA after a q8_0→f16 conversion that now skips dead blocks too. Knobs: `GGML_CUDA_FA_MASK_SKIP=0` (one
        binary is its own control) and `GGML_CUDA_FA_MASK_SKIP_MIN_KV` (default 4096).
      - Correctness, on the dev build before the final q8_0 converter change: `test-backend-ops -o FLASH_ATTN_EXT -b
        ROCm0` 2920/2920 including the 52 new cases. The 64-case harness is bit-identical with the skip on vs off.
        Against the unpatched champion, 58/64 are bit-identical and 6 differ at nmse ≤ 3e-7 from codegen. CPU 86/86
        bit-identical.
      - Kernel micro-bench (dev build, contended GPU, indicative only), 27B attention shape: decode (vec) 2446 →
        401 µs at +112k foreign cells; drafted verify (WMMA) 4443 → 788 µs, a +18% residual against +590% unpatched;
        0 foreign +4-5%, within noise, to be re-measured.
      - Upstream: #28495 still open. The maintainer-requested approach builds on `flash_attn_mask_to_KV_max`; PR
        #28943 closed, #29510 is a draft. Drop ac97e305a for the upstream design when it lands.
      - Fold: trial merge and cherry-pick onto DS41 accumulator b3e0b0902 are both clean. workspace-89 does the
        champion fold (KVU-19).
    - [x] **KVU-19a-1 — validate the STORE build on the GPU (`gpu_slot.sh`).** ✅ 2026-10-04 (filed 2026-10-03, workspace-ec) The
      correctness and micro-bench numbers above come from the dev build. Run
      `/mnt/raid0/llm/tmp/fa-maskskip-20261003/gpu_slot.sh` (~20-25 min, < 2 GiB) in a coordinated GPU slot, never
      during another session's GPU measurement window (INC-20261003-subagent-gpu-tests-in-peer-window). It covers
      store-build exactness, the micro-bench with 3 alternating rounds, P3-mini on gemma-3-1b, batched-bench `-kvu`
      vs `-no-kvu`, and `test-backend-ops` with `GGML_CUDA_FA_MASK_SKIP_MIN_KV` default and 0. Done when
      `test-backend-ops` passes on the store build, skip on/off is bit-identical, and the 0-foreign micro-bench row is
      within noise of the champion. Then tick KVU-19a. Scheduled for the coordinated GPU block after ~18:15Z.
      - **PASSED 2026-10-04 02:25-02:47Z (workspace-ec)** on the store build, results
        `/mnt/raid0/llm/tmp/fa-maskskip-20261003/slot-20261004T022552Z/` (VRAM before/after equal).
        - Exactness (`exact.txt`): skip off vs on 64/64 bit-identical; base (champion) vs on 58/64, worst nmse 3.05e-7.
          `test-backend-ops -o FLASH_ATTN_EXT` 2920/2920 twice (`MIN_KV` default and 0).
        - Kernel micro-bench, 3 alternating rounds (`perf_results.txt`): nb=1 at +114,688 foreign cells base ~2003 µs
          vs on ~282 µs (7.1x); nb=8 at +114,688 3808 vs 584 µs; 0 foreign 271 vs 275 µs (noise).
        - P3-mini, gemma-3-1b, 8k own, 3×32k idle neighbours (`p3mini_results.txt`): draft 1 base 82 → on 169 steps/s
          (no-neighbour ~182-197); draft 8 41.8 → 89.5 (no-neighbour ~99.5).
        - Batched-bench, 4 concurrent 16k sequences (`bb_*.jsonl`): S_PP kvu base 13,205 → new 21,017 t/s (no-kvu
          ~20,000); S_TG kvu base 437 → new 444 vs no-kvu 542/551.
        - **FINDING: the skip does NOT help concurrent decodes.** A batched decode's query tile spans every sequence,
          so its live-block set is their union and nothing is dead. Production flushes idle slots (211 organic
          purges, KVU-16b), so concurrent decode is the production-relevant case. Filed as KVU-19b.
        - KVU-19a's done-when holds (tests pass, neighbour tax reduced for single-sequence decode/verify, fold record
          handed to workspace-89, whose P3 v2 on this build is queued), so KVU-19a is ticked.
    - [ ] **KVU-19a-2 — report or investigate the latent D=512/576 tile-kernel nondeterminism upstream.** (filed
      2026-10-03, workspace-ec, from the KVU-19a build) A no-op branch inside the KV loop of the D=512/576 GQA tile
      FA kernel made its output run-to-run nondeterministic on gfx90a (~1e-4 nmse), even with the skip disabled.
      That is pre-existing upstream code, codegen-sensitive, and it affects Gemma-4 D=512 layers on HIP. KVU-19a
      avoids triggering it by advancing the loop index instead. Reduce it to a standalone `test-backend-ops` repro
      on an experimental branch, then file an upstream llama.cpp issue with the repro. Detail: the fold record's
      *Not done / follow-ups*. Done when an upstream issue link is recorded here, or the repro shows it is not
      reproducible on the unpatched kernel.
    - [ ] **KVU-19b — per-sequence (per-query-row) block skipping inside a multi-sequence FA tile.** (filed
      2026-10-04, workspace-ec, owner workspace-ec, from KVU-19a-1's batched-bench finding) KVU-19a marks a KV block
      dead only if it is dead for EVERY query row in the tile, so a batched decode over 4 sequences sees the union
      and skips nothing: S_TG kvu 444 vs no-kvu 542/551 t/s. Skip per query row (or regroup query rows by sequence)
      inside the tile, on `llama.cpp-experimental` from the current champion, HIP/gfx90a first, keeping the 64-case
      exactness harness and `test-backend-ops` green. Done when batched-bench `-kvu` S_TG at 4×16k is within ~5% of
      `-no-kvu` and single-sequence results do not regress.
      - **2026-10-04 (workspace-ec): BUILT CPU-side; GPU validation in progress, so not ticked.** Fold record:
        `/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/FOLD.md` (design in `DESIGN.md` beside it).
        - Branch `experimental/fa-maskskip-batched-20261004` on base a0d0ae238 (KVU-19a), pushed to `fork`:
          - `1bceceb05` routes "every row a different sequence" batches to the vec kernel, one row per block, using a
            new `ggml_flash_attn_ext_{set,get}_n_seq` hint that `llama-graph.cpp` sets from `ubatch.n_seqs_unq`;
          - `c7f5ac9ad` cuts WMMA query tiles at sequence boundaries with a device planner.
        - Knob: `GGML_CUDA_FA_SEQ_ROWS=0` turns both off, which is the same as KVU-19a. So one binary carries the
          three arms 19b, 19a, and 19a with the skip off.
        - Store builds `kernels/builds/{gpu,cpu}-20261004-c7f5ac9ad` (build 10312); linkage PASS.
        - CPU FA harness v2: 141/141 bit-identical to the KVU-19a CPU store build. The llama-side hint checks out on
          gemma-3-1b (4 in every multi-sequence kvu step graph, 0 for single-sequence and for `kv_unified=false`).
        - `gpu_slot2.sh` ran 04:44-05:05Z (`slot2-20261004T044448Z/`); scored in KVU-19b-1 below.
      - **2026-10-04 05:05Z (workspace-ec): GPU validation SCORED; parent stays open.** Durable evidence:
        [`artifacts/kvu19b-20261004/`](../../artifacts/kvu19b-20261004/) (`slot2-20261004T044448Z/summary.txt`,
        `FOLD.md`, `DESIGN.md`, runner `gpu_slot2.sh`). The batched-bench done-when holds for commit 1 (`-kvu` S_TG
        522.4 vs 529.3 base `-no-kvu`, -1.3%; -5.5% vs the same binary `-no-kvu`, 552.7; 19a was 434.6) and single-
        sequence rows are unchanged vs 19a. KVU-19b is NOT ticked because commit 2 broke the design's bit-identity
        claim and is being reworked (KVU-19b-rework-c2), and p3batch draft=1 still trails no-kvu (KVU-19b-gap). Tick
        it when the rework is folded or dropped.
      - [x] **KVU-19b-1 — validate the KVU-19b STORE build on the GPU (`gpu_slot2.sh`).** ✅ 2026-10-04 (workspace-ec;
        store build `gpu-20261004-c7f5ac9ad`, linkage PASS, VRAM before/after equal)
        - Correctness: `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` 2978/2978, plus the unified cases 110/110 with
          `MIN_KV=0` and 110/110 with `SEQ_ROWS=0`. Every arm (on / seqoff / k19a) is within the CPU reference on all
          119 harness cases (worst nmse 8.97e-05 at a 5e-4 tolerance). seqoff == alloff == k19a bit-identical (119/119).
        - **Commit 1 (`1bceceb05`, vec routing, one row per sequence) WINS.** Kernel at 4 seqs × 81920 own, n_kv 327680:
          5.53 ms vs 9.23 ms (19a) vs 8.77 ms (base); per-sequence streams reference 5.26 ms. At 4 × 16384: 1.08 vs
          1.78 ms. p3batch gemma-3-1b 4×16k draft=1: 440 / 430 / 449 tok/s (on) vs 377 / 373 / 396 (19a) vs 491 / 523 /
          518 (no-kvu), three rounds.
        - **Commit 2 (`c7f5ac9ad`, WMMA sequence tiles) is MIXED and breaks exactness.** Aligned 4×8 verify: 11.86 vs
          10.36 ms (seqoff), 14% slower. Uneven [1,8,8,8]: 11.90 vs 13.64 ms, 13% faster. Skip on vs off is NOT
          bit-identical on 6 cases (110/111/118/119/126/127, all hint=4 nb≥25 multi-row tiles, f16/q8_0/bf16):
          ndiff 384, nmse ≤ 8.3e-10. DESIGN.md claimed bit-identity for the tile layout under skip on/off. p3batch
          draft=8 rows are within run-to-run noise (±10%), so the end-to-end effect is unresolved.
        - Recommendation sent to workspace-89 (fold owner): fold commit 1 only.
        - **Contention caveat.** The slot ran its host side unlocked on `taskset -c 160-183` (the SMT siblings of
          64-87) while workspace-89 held `cpu-window2-20261004` and two dev servers and a build were also running
          (INC-20261004-subagent-unlocked-cpu-in-held-window). Arms alternate within each round, so the comparisons
          stand, but host-bound absolute numbers (p3batch on a 1B model, ~100 steps/s) are noisier than a quiet
          host would give. `gpu_slot3.sh` takes `region-lock` for its host side.
      - [ ] **KVU-19b-fold-c1 — fold KVU-19b commit 1 (`1bceceb05`) into the champion; leave commit 2 out.** (filed
        2026-10-04, workspace-ec, owner **workspace-ec** (reassigned 2026-10-04 by workspace-89; operator "proceed in coordination"), from KVU-19b-1) Cherry-pick order: `ac97e305a a0d0ae238`
        (KVU-19a, if not folded yet), then `1bceceb05` only. Commit 1 also touches `ggml.h/ggml.c` (the
        `ggml_flash_attn_ext_{set,get}_n_seq` hint) and `src/llama-graph.cpp`. Gates on the folded candidate, from
        `artifacts/kvu19b-20261004/FOLD.md`: house recipes; `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` (also with
        `GGML_CUDA_FA_MASK_SKIP_MIN_KV=0`); harness exactness; P3 B on the 27B. Done when the champion carries commit 1
        and its P3 B shows `-kvu` batched decode within ~5% of `-no-kvu`.
      - [ ] **KVU-19b-rework-c2 — make WMMA sequence tiles exact, straddle-only, and separately switchable; then
        `gpu_slot3.sh`.** (filed 2026-10-04, workspace-ec, owner workspace-ec, from KVU-19b-1; rework dispatched)
        (1) Root-cause the skip on/off difference on cases 110/111/118/119/126/127 (384 elements differ in each). The
        design says the planner and tiles never depend on `GGML_CUDA_FA_MASK_SKIP`, so something does. (2) Plan
        sequence tiles only when a default tile straddles sequences, so the aligned 4×8 verify keeps the 19a layout
        (it is 14% slower today). (3) Split the knob: `GGML_CUDA_FA_SEQ_TILES` for the tiles, `GGML_CUDA_FA_SEQ_ROWS`
        for the vec routing only. (4) Write and run `gpu_slot3.sh` with more p3batch rounds for draft 8 and [1,8,8,8].
        Done when skip on/off is bit-identical on all cases, aligned 4×8 is within noise of seqoff, uneven keeps its
        gain, and the result is handed to workspace-89 as a separate fold item (or commit 2 is dropped with the
        reason recorded here).
      - [ ] **KVU-19b-gap — commit 1 still trails no-kvu at draft=1 in p3batch; find out why.** (filed 2026-10-04,
        workspace-ec, from KVU-19b-1) p3batch gemma-3-1b 4×16k draft=1: 449 vs 518 tok/s (round 3; medians 440 vs
        518, about 15% short), while the kernel micro-bench is at the streams reference (5.53 vs 5.26 ms) and
        batched-bench is within 1.3%. So the remainder is likely outside the FA op: mask construction over
        n_kv = 4 × own, the KVU-19a scan, KV copy/view ops on a single stream, or graph shape. Profile one
        p3batch step `-kvu` vs `-no-kvu` (rocprof per-kernel, GPU slot) and attribute the gap per op. Done when the gap
        is attributed with a fix filed, or shown to be inherent to a single KV stream. Re-measure the gap
        under `region-lock` first: slot2 ran on a contended host (KVU-19b-1 caveat), and host overhead hits the
        1B model hardest.
- [ ] **KVU-20 — cross-slot prefix fork anchored on recurrent checkpoints, plus trunk-first dispatch.** (filed
  2026-10-04, workspace-ec, from the KV-serving survey Rec 2,
  `artifacts/gpu-block-27b-20261004/analysis/kv-serving-survey-REPORT.md` §4.)
  - **The gap.** Four subagents sharing a 60k trunk prefill it four times and hold four copies (~6 GB of the pool).
    Slot selection never looks at busy slots (`get_available_slot`), and `seq_cp` is used only for `n>1` children.
  - **Server side (experimental tree).** For a new task, compute the LCP against all slots and their checkpoint
    lists. Fork attention KV zero-copy with `mem_attn->seq_cp(S, dst, 0, p)` at the largest checkpoint ≤ LCP.
    Restore the recurrent state (and the drafter's) from that checkpoint with `llama_state_seq_set_data_ext(...,
    PARTIAL_ONLY)`; `llama_memory_hybrid::seq_cp` shares S's *current* tail, so do not rely on it. Add a request field
    that marks the end of the shared prefix so a checkpoint lands exactly at the parent→subagent junction.
  - **Orchestrator side.** Issue the trunk first, then the children; order and pin slots by the KVU-15c prefix
    history; have the KV-pool gate count unique cells.
  - **Gate.** A logits-equivalence test, fork vs fresh prefill (top-1 on ≥ 24 prompts), with the drafter state
    included.
  - **Done when** a 4-child fan-out over a ≥ 30k trunk prefills the trunk once, the child TTFT is the suffix time,
    and the gate passes.
- [ ] **KVU-19c — measure the live-block fraction per row on organic traffic before building sequence-affine cell
  allocation.** (filed 2026-10-04, workspace-ec, survey Rec 3) `find_slot` allocates first-fit, so concurrent decode
  interleaves the sequences' new tokens in shared 256-cell blocks. A block holding generated tokens is then live for
  every decoding sequence, and even KVU-19b cannot skip it. Have KVU-19a's scan kernel, or a debug counter, report
  the per-row live-block fraction on an organic :8083 replay. Build the allocator (~100–200 LOC in
  `llama-kv-cache.cpp`, per-sequence 256-cell chunks) only if mixed blocks are a material share. Done when the
  fraction is recorded here, with a build/no-build verdict.
- [ ] **KVU-21 — at the v11 rebase, carry upstream #29510 (`flash_attn_ext_rows`) as an A/B arm against KVU-19b.**
  (filed 2026-10-04, workspace-ec, survey Rec 4; trigger: the v11 rebase starts) #29510 is NVIDIA-MMA-only. It cannot
  slice DFlash2 verify batches or mixed ubatches (unified KV uses `split_simple`), and it falls back to dense when
  sequences share cells (`n_sum > n_kv`). So it complements KVU-19b rather than replacing it. If it has merged by
  then, port the `kv_rows` path to the HIP vec kernel and the CDNA MMA path. A/B it on the KVU-18 cells and the 4×80k
  shape, and drop whichever loses. Done when the A/B verdict is recorded.
- **v11 FA-path audit (2026-10-04, workspace-89; durable copy
  [`artifacts/v11-fa-path-audit-20261004/REPORT.md`](../../artifacts/v11-fa-path-audit-20261004/REPORT.md)).** Upstream
  #26046 deletes rocWMMA FA. On gfx90a, for our D=256 GQA-6 q8_0 shape, v11 then routes 3-32 query rows (4×1 batched
  decode, 1-3-slot DFlash2 verify) to the generic TILE kernel (no matrix cores; the RDNA4 analog #26220 lost ~2×) and
  >32 rows (4-slot verify, prefill) to MMA `<256,256,32,2>`, which spills 314 VGPRs under ROCm 6.2. The DF2-9 all-NaN
  path is the ROCWMMA=OFF route. These tasks gate the v11 rebase and RTG-58's P4 `kv_rows` phase
  ([`kv-prefix-fork-and-paged-attention.md`](kv-prefix-fork-and-paged-attention.md) KPF-40..42), and inform KVU-21.
  Owner of V11-FA-1..4: **workspace-ec** (filed 2026-10-04 at the coordinator's direction). Every build and run below
  takes `region-lock` for its host side.
- [ ] **V11-FA-1 — A/B the champion with ROCWMMA=OFF (exact v11 FA routing) against ROCWMMA=ON, plus a third arm with
  #27870 and #28576 cherry-picked.** (filed 2026-10-04, workspace-ec, from the v11 FA-path audit §5) ROCWMMA=OFF
  reproduces upstream's D=256 routing: TILE at ≤32 rows, MMA above. The third arm approximates v11's MMA kernel
  (`b74f590ea` divergent-barrier fix, `bfdc32183` fp32 VKQ). Build in an experimental worktree, never the frozen tree.
  Bands: 4×1 decode, 1-3-slot DFlash2 verify (9-27 rows), 4-slot verify (36 rows), prefill (512 and mixed 512+3×9),
  own cells {4k, 16k, 57k} × foreign {0, 3×~100k}. Instruments: the 19b `perf2` micro-bench, `test-backend-ops` perf
  mode (TFLOPS, comparable to #28576/#28907), batched-bench `-kvu` vs `-no-kvu`, and the P3 harness L0 (v10: drafted
  36.3, no-draft 20.4 tok/s). Gate every arm on the DF2-9 reproducer (V11-FA-2) and on TILE D=256 `ncols2=2`
  run-to-run bit-exactness (those kernels have never been compiled into any of our builds). Done when the per-band
  delta is recorded here and decides one of: carry WMMA (V11-FA-4), retune the TILE/MMA crossover for gfx90a, cap
  ncols (V11-FA-3), or nothing.
- [ ] **V11-FA-2 — root-cause DF2-9: all-NaN target features at ~2k-token prompts with ROCWMMA OFF.** (filed
  2026-10-04, workspace-ec, from the audit §0.4 and §4b) Build a standalone reproducer first: `test-backend-ops` cannot
  catch it, because its random [-1,1] inputs never overflow. Add a new FA case with large magnitudes and long KV
  (|V|~30, kv ≥ 4k) checked against the CPU reference. The length discriminator fits the >32-row MMA route: a short
  prompt's prefill goes to TILE, while ~2k prompts split into 512-row ubatches that go to MMA. Candidates in the
  audit's order: the D=256 MFMA-MMA route (consistent with the `99f3fffd6` unpadded-KV guard); the fp16 VKQ downcast
  (fp32 after #28576); the #27870 barrier. Record: `dflash2-block-drafter-experimental-build.md` DF2-9 and wiki CH-8.
  Done when the reproducer is 12/12 finite on the fixed path, or the faulting kernel and cause are recorded with an
  upstream issue.
- [ ] **V11-FA-3 — MMA `<256,256,32,2>` spills 314 VGPRs on gfx90a under ROCm 6.2; evaluate an ncols cap for D=256
  prefill.** (filed 2026-10-04, workspace-ec, from the audit §0.3 and §3.1) `<256,256,16,2>` has 0 spills (499
  registers including 243 AGPR). The spill is structural: 512 threads means 2 waves per SIMD on gfx90a's unified
  register file. Candidates: cap D=256 at `ncols1=16` on CDNA2, or give `(256,256,64)` 256 threads. Leave the choice to
  AutoKernel. Re-check v11's own code object (these numbers predate #28576) with the register-audit scripts in
  `artifacts/v11-fa-path-audit-20261004/register-audit/`. Done when the prefill A/B (ON vs capped) is recorded, and
  the cap is either carried into the v11 candidate or declined with the numbers.
- [ ] **V11-FA-4 — in v11, carry rocWMMA FA as an in-binary arm until TILE/MMA is at least as fast on every band.**
  (filed 2026-10-04, workspace-ec, from the audit §4 "Can rocWMMA FA be carried in v11? Yes" and §5.3)
  - Restore `fattn-wmma-f16.{cu,cuh}`, the dispatch branch and the CMake/`hip.h` flags.
  - Keep the tile skip-list out, so the same binary carries TILE for the A/B.
  - Adapt to v11's `fattn_kernel_t`/`launch_fattn` signatures.
  - Re-apply `db18f3937` and KVU-19a's WMMA hunk.
  - Keep the `99f3fffd6` D=256 unpadded-KV → TILE guard until v11 `test-backend-ops` on ROCm0 proves MMA D=256
    unpadded is correct.
  - Expose it as a runtime knob (e.g. `GGML_CUDA_FA_PREFER_WMMA`), so the ONE candidate carries its own control.
  - Cost: ~1-2 days plus a recurring conflict tax. It pins rocWMMA 1.x; ROCm 7 brings back #16221/#19461.
  - Drop-when: TILE/MMA ≥ WMMA on every V11-FA-1 band, and DF2-9 is clean without WMMA.
  - Done when the v11 candidate carries the arm, or V11-FA-1 shows it is not needed.
- [ ] **KVU-7 — the MTP pool-full exception is a v11 experimental-kernel candidate.** v10 `ffc1bac82` with
  `-np 2 -c 4096 --kv-unified` and two 2048-token generations fails exactly one request with
  `speculative batch index 8 is not inside the current sub-batch [0, 8)`, instead of the clean
  `Context size has been exceeded.`
  - Reproduced 4/4. Evidence: research `artifacts/np_context_kvu_study_20260924/q38_27b_q8/unified/np2_L2048/server.stderr`
    and `q38_27b_q8_h/unified_poolfull_r{1,2,3}/np2_L2048/server.stderr`. The split controls
    `split_poolfull_r{1,2,3}` never error.
  - Locate it in the frozen source (read-only). File it on a `llama.cpp-experimental` branch together with the
    upstream "evict one slot" TODO (`server-context.cpp:3760`, audit T4b).
  - **Guarded:** the standing rule is no kernel research until the champion is consolidated, and the operator
    reopens it. The orchestrator already classifies the error (KVU-0e).

### D — measurement follow-ups
- [x] **KVU-18 (intake P3) — unified-KV decode cost on :8083's shape. Running in the 2026-10-03 INF-80 X0
  window** (`/mnt/raid0/llm/tmp/x0-27b-quants/PLAN.md`). Measure one slot's decode and verify tok/s at a fixed
  context while 0, 1 and 3 other slots hold parked long contexts, unified vs split, same binary. Include a cell
  near the F12 range: 50–150k own context, 15–60k neighbours. The source reports -6.6% S_TG on gfx1201 and
  "a 15.6k conversation with three others parked generates at the speed of a 62k one" on V100
  (`intake-1849#02`). Those are other GPUs and are not MI210 expectations. The loss, if any, is independent of
  drafter acceptance, so it must be measured before 25–30 tok/s agentic decode is blamed on DFlash2 (UFH14-A2
  in [`agentic-serving-harness-fixes.md`](agentic-serving-harness-fixes.md)). A loss of 5% or more triggers
  KVU-19. Carry the belief-kernel write-side hook from the first cell.
  - ✅ 2026-10-03 — **both triggers MET.** Report `/mnt/raid0/llm/tmp/x0-27b-quants/results/p3/report.md`; native records `a1.json`, `a0.json`, `b.json`,
    `p3_result.json`. MI210, v10 `ffc1bac82` kernel store, Qwen3.8-27B Q8_0 + DFlash2, :8083 production argv (pool 393216).
    - *A1, mechanism* (`--no-cache-idle-slots`, so parked neighbours stay resident): slot 0 holds P = 57,082 tokens and
      decodes 512 tokens; neighbours are one ~99.4k prefill plus two slot restores of it. No-draft decode (isolates
      attention): base 20.39 tok/s → **−32.6% / −49.5% / −59.5%** with 1 / 2 / 3 neighbours; drafted 36.28 tok/s →
      −29.6% / −47.2% / −57.6%. Acceptance unchanged (0.393–0.397). ABA drift −0.61% (L0 before vs after). Zero
      slot-failure, purge or restore-failure log lines. Nominal fill at L3 ≈ 57k + 3 × 99.4k ≈ 355k (0.90 of the pool).
    - *Caveat on the fill figure:* `/slots` reported only 156,971 resident tokens (0.399) at L1–L3, because the two
      restored slots never show `n_tokens` there; the restore replies report 99,378 tokens each, and the monotone L1→L3
      loss says the restored cells are attended. The ≥300k condition rests on the restore records, not on `/slots`.
    - *A0, production flags* (`cache_idle_slots` default on): **inconclusive** — the neighbour slot held 0 tokens before
      the probe task, so the "new task purges an idle neighbour" path was never exercised. Not re-filed as a task: the
      production default parks neighbours in RAM, and A1 already answers the decode-cost question the triggers ask.
    - *B, `llama-batched-bench`* (no drafter, pl 4, 4 × 16k, n_kv 65,792): kvu vs no-kvu S_TG 47.17 vs 55.64 t/s
      (**−15.2%**), S_PP 587.4 vs 823.3 t/s (**−28.6%**).
    - Consequences: KVU-19 is triggered (≥5%). KVU-16d's ≥15%-at-≥300k condition is met — workspace-ec is preparing the
      split-per-slot stack-change package there (their item). Belief-kernel wiring: VB-KVU-P3 in
      [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md).
    - *(Annotation, workspace-ec, 2026-10-03.)* The operator decided KVU-16d as keep shared 393k, so no split package
      is being prepared. The skip is implemented directly as KVU-19a. A0 being inconclusive leaves the production
      idle-purge claim a code read (see the KVU-16b correction).
- [x] **KVU-8 — confirm the throughput verdict with fixed-length or multi-wave generation.** ✅ 2026-09-24 —
  confirmed, with one named substitution. (1) 35B-A3B, both arms, fixed-length L 2048 cells: unified within 2% of
  split in all 4 (per-request −0.6..−1.7%, aggregate −0.7..−1.1%); at 8k/32k the per-request spread is −5.3..+5.6%
  with no consistent sign because the arms' completions differ even at np 1. (2) 27B L 2048 cells, where every
  request in both arms ran to the cap: unified aggregate +5.1% at np 4. (3) M-4 (KVU-1e): the live np4 kvu shape
  at fixed length, 2 waves, gives 95.3 / 93.1 tok/s aggregate at concurrency 4, in line with the study's split
  np4 cells (92.9–102.0). So the single-wave −8% / −16% "aggregate loss" was the answer-length artifact. The
  substitution: no fixed-length **split** arm was re-run on the 27B; the claim rests on (1)–(3), n ≤ 2 per cell.
  Original task: Every cell is n=1, and
  the np4 aggregate gap tracks divergent completions. Rerun the np 2/4 cells with fixed-length generation
  (`ignore_eos` + `n_predict`) or at least 3 waves, both arms on the same binary. Carry the write-side hook
  (VB-KVU-1) from the first run.
- [x] **KVU-9 — finish, commit and read the Qwen3.6-35B-A3B-MTP Q8_0 GPU matrix.** ✅ 2026-09-24 — 24 cells,
  0 errors, np 8 fits at every L (44–45 GiB at 32k); committed research `07060eaa` (README §7, SHA256SUMS). Read
  in KVU-8. :8083 and :8086 were restored (18:30Z) and :8083 then came up on the OP-54 shape. The 35B ran at
  depth 4. Original task: Research
  `artifacts/np_context_kvu_study_20260924/q36_35b_a3b_q8_h/` was running from ~17:12Z with driver pid 1224153.
  - After the driver exits: verify it, add the run to the study README and SHA256SUMS, and commit it to research
    main.
  - Then restore :8083 and :8086 (`orchestrator_stack.py start --only …`; the owning session does this).
- [ ] **KVU-10 — roll `-kvu` to other roles, in the inventory's order.**
  - Embedders first (:8090–8095). Per-slot context is 256, below bge-large's 512 window, and every launch WARNs.
    The alternative is `-c 2048 -np 4`.
  - :8070 only if long jobs are routed there.
  - :8086 only if its `-np` rises.
  - Never :8080, :8180 or :8074 (`-np 1`, nothing to gain).
- [ ] **KVU-12 — np × ctx on CPU (TB-6 successor, Flash-Next) only if needed.** The operator skipped C2 at 17:25Z
  because the GPU matrix showed no unified-KV throughput cost. Reopen only if a CPU role shows qualitatively
  different relative behaviour.

### E — speech residency
- [x] **KVU-11a — commit the speech study's follow-up run.** ✅ 2026-09-24 — option C (`smtC`) committed in
  research `07060eaa` (README addendum, SHA256SUMS regenerated); the shared clone's untracked copies were moved
  aside and the clone fast-forwarded (it is at `6afc7eed`, ≥ `34373dd8`). Option C failed: TTS 20–37× slower than
  real time with the frontdoor generating. Original task: After 17:14Z the study kept writing to the shared
  research clone: an `smtC` SMT-sibling run, an edited `speech_cpu_bench.py`, and a grown
  `raw/whisper_bench_encoder_matrix.txt`. Once it finishes:
  - commit the delta onto research main (`artifacts/speech_cpu_realtime_20260924/`, SHA256SUMS regenerated);
  - update the README's option C;
  - after a checksum match, remove the shared clone's untracked copies, so DS41-C10a's fast-forward is not blocked.
- [x] **KVU-11 — decide where STT/TTS live** (OP-56). ✅ 2026-09-24 — operator: STT **and** TTS to CPU (STT
  24@0-23, TTS 16@24-39); applied with OP-54 (KVU-1). Voice turns route their reasoning step to
  architect_general (:8083), a requirement for the voice-pipeline handoff the operator is drafting. The
  follow-up measurement showed this layout collides with the CPU LLM roles (KVU-11b). Original options: Research `artifacts/speech_cpu_realtime_20260924/README.md`.
  - (A) Stay on GPU. Recommended: whisper costs ~2.2 GB VRAM, plus TTS when it runs.
  - (B) Give speech its own cores. Shrink the `-t 96` frontdoor and :8074 to free 24–40 physical cores. The
    frontdoor cost is unmeasured and needs a frontdoor relaunch.
  - (C) Run speech on SMT siblings 96–175. This was untested in the committed snapshot; an `smtC` run was in
    progress at 17:53Z (KVU-11a).
  - Either CPU option must use a measured core layout: whisper hangs on some layouts (e.g. 32@0-31). TTS also
    needs the `get_nprocs` shim to control its thread count.
  - Couples with OP-48 (capacity gate sees speech VRAM) and package N-5 (TTS does not fit next to kvu today).
  - The operator is drafting a separate conversation-stack handoff (STT → frontdoor → TTS). Do not file the
    omni/Moshi intake here.
- [x] **KVU-11b — CPU speech is not real time while a CPU LLM role generates: decided.** ✅ 2026-09-24
  **Operator decision 2026-09-24 ~20:00Z (first-hand to main-ak-seat): option D, no change to the layout.** The
  operator is drafting a larger STT/TTS integration plan that supersedes options A-C; the measurements below are its
  input, collected in [`docs/reference/speech/cpu-speech-contention-20260924.md`](../../docs/reference/speech/cpu-speech-contention-20260924.md).
  Do not re-propose partitioning or a throttle as standalone work.
  Measured 2026-09-24 19:19–19:43Z against the live layout (research
  `artifacts/speech_cpu_realtime_20260924/README.md` addendum 3, `6afc7eed`; harness `live_llm_contention.py`):
  - With :8074 or :8070 generating (`-t 96` on 0-95): STT RTF ≥ 58 (one 11 s clip took ~10.7 min), TTS first
    packet 13.4–13.6 s and then stalls. The collision is two-sided: :8074 falls 31.2 → 0.59 tok/s and :8070
    36.8 → 1.05 tok/s, because speech threads sit inside the LLMs' core masks and their barriers wait on them.
  - Partition test (a TEST Flash-Next instance, `-t 56` on 40-95): STT back to quiet levels (RTF 0.22–0.44), TTS
    marginal (first packet 0.24–1.0 s, RTF 0.93–1.40 vs 0.55–0.63 quiet), LLM decode −22..26% (23.0 / 24.5 vs
    31.1 / 31.3 tok/s). The frontdoor under the same partition was not measured (inferred similar).
  - No priority-pause mechanism exists today.
  - Options presented: **(A, was recommended)** partition the CPU LLM roles to 40-95 **and** move TTS back to the GPU
    (0.92 GB of weights; re-check VRAM headroom against the np4 :8083 + VL resident set first); (B) partition
    only (TTS stays marginal); (C) keep the layout and build a decode throttle that pauses LLM decode while TTS
    streams; (D) do nothing (any speech request during a `-t 96` generation wrecks both).
  - Acceptance that would have applied to A/B (keep for the operator's plan): the live-contention harness re-run against the new layout gives STT RTF < 0.5 and TTS
    first packet < 1 s with a CPU LLM generating, and the LLM decode loss is recorded.
  - The voice-pipeline handoff the operator's parallel agent is drafting must carry this contention as a
    requirement; that handoff did not exist at 2026-09-24 ~19:50Z, so no cross-reference was written.
  - Cross-reference (added 2026-09-24, later): the operator's plan landed as
    [`conversation-stack.md`](conversation-stack.md) (INF-79). This contention and the acceptance above are carried
    there as CS-11 (partition measurement) and CS-12 (cascade onto the second MI210). KVU-11c stays here.
  - Layout hygiene seen in the same run: `megasync` (unpinned) ran at 60–100% on core 16, inside whisper's 0-23
    mask — a possible straggler source (quiet STT RTF spread 0.22–0.39). Pin it outside 0-39 as part of whichever
    option lands.
- [ ] **KVU-11c — replace the TTS `nprocs` shim with a real thread flag.** The shim (`LD_PRELOAD` interposer on
  `get_nprocs()`, orch `scripts/voice/`) is the accepted stopgap (package revision 3 §4.2). Add a thread-count
  flag to qwentts.cpp on an `experimental` branch and promote it as the next speech kernel version; then drop the
  shim and `SHIM_NPROCS` from the launch manifest.

## Not filed here (explicit)
- SSU-F3 structural capacity model (RS, draft KV, compute terms): RTG-19's SSU-F3 is done (2026-09-23,
  `artifacts/operator/vram-gap-27b-20260923.md`); the open follow-on is SSU-F10 (per-buffer VRAM logging on every GPU
  role). INF-41 aux VRAM in the gate:
  owned by OP-48 / INF-41.
- Package §10 items that the overflow branch already fixes: the 20,000-char routing threshold (now tokens and
  capacity-fenced), the 32768 compaction fallback, and 400 / "Context size has been exceeded." handling.
- The speech addendum's "priority pause instead of partitioning" alternative: not filed as its own task, because a
  pause cannot act mid-token and no mechanism exists; it survived as option C (KVU-11b; operator chose D).
- Frontdoor-under-partition measurement: not filed; the operator chose D (KVU-11b), and any re-run belongs to
  the operator's STT/TTS plan.
- A Stage-1 intake sweep of the audit's new primary sources (vLLM / SGLang / TGI / TRT-LLM / LMDeploy / LMCache
  docs): no claim here relies on them. Intake runs only when the operator invokes it.
- Declined 2026-10-04 (workspace-ec), from the KVU-16b root cause and the KV-serving survey:
  - `--no-kv-unified` (root cause fix 1c). It caps a slot at 98k and defeats KVU-16. KVU-16d already decided to keep
    the shared 393k pool, and its reopen trigger stands.
  - The admission rule "no ≥ 32k prefill while ≥ 2 slots decode" (fix 1d). KVU-16f/16g bound the same interference
    inside the server without starving long ingest, and KVU-15's one-long-prefill lease is the coarse version.
    Reopen it if KVU-16g fails its done-when.
  - `--ctx-checkpoints`, `--cache-ram` and `-cd` as fixes (fix 1b). Ruled out by source and log evidence.
  - Cascade/Hydragen shared-trunk attention (survey Rec 5). It pays only after KVU-20 forks trunks, and only if a
    rocprof profile shows shared-prefix attention dominating after KVU-16g, KVU-19b and KVU-20. Not filed until then.
  - Cherry-picking upstream #28532 `--slot-linger-ms`. The orchestrator's opt-in `id_slot` pinning gives the same
    binding (UFH14-B4).
  - A time-boxed vLLM/SGLang reference probe on the MI210 (survey §5). gfx90a is a degraded tier (ROCm ≥ 6.3 needed,
    no AITER, an open MI210 crash for this family), and it is not a production path. The survey offers it to the
    operator as an optional reference number; not filed unless the operator asks for it.
  - More checkpoints per slot for trunk-heavy roles (survey host-tier note). It is only meaningful once KVU-20 makes
    checkpoints into fork anchors, so it rides KVU-20.
  - A per-buffer VRAM logging task for KVU-16h. SSU-F10 already owns per-buffer VRAM logging on every GPU role, and
    KVU-16h uses `-lv 4` for its one-off attribution.

## Key files
- Orchestrator: `src/scheduling/kv_pool_admission.py`, `src/backends/context_limits.py`,
  `src/backends/context_overflow.py`, `src/llm_primitives/context_recovery.py`, `src/llm_primitives/inference.py`,
  `src/api/routes/openai_compat.py`, `scripts/server/orchestrator_stack.py`, `scripts/server/stack_commands.py`,
  `src/registry/stack_priors.py`
- Research: `orchestration/model_registry.yaml` (`serving_shape.kv_unified`, `vram_non_kv_gib`, `draft_kv_quant`,
  `cache_ram`)
- Frozen tree (read-only): `tools/server/server.cpp:145-150`, `tools/server/server-context.cpp:3303-3310, 3759-3801,
  1716-1735, 2468-2482`, `src/llama-context.cpp:289-302`

## Reporting
Flip the box here, update RTG-57's `Next action`, and append to `progress/YYYY-MM/`. Operator decisions go through
the master index: OP-54, OP-55 and OP-56 are decided and applied; the CPU speech contention (KVU-11b) was decided D (no change) by
the operator directly, with no queue row. The gate's known-gap choice was decided before filing: option A.
