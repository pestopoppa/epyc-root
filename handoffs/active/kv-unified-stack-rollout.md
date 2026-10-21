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
**Depends on**: RTG-19 (single-source stack pipeline, SSU-F3 capacity model), RTG-36 (stack-change governance),
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
- [x] **KVU-1c — add the context-checkpoint read to the serving proof.** ✅ 2026-09-24 — :8083 was reloaded
  with `LLAMA_ARG_LOG_VERBOSITY=4`; its log since the np4/kvu launch holds 26 `created context checkpoint` lines
  (first: slot 3, task 1, `checkpoint 1 of 32`, 150.2 MiB), read-only from
  `epyc-orchestrator/logs/llama-server-8083.log` at 19:54Z. Original task: With `-lv 4`, confirm `created context
  checkpoint` fires on :8083 (audit #8 / T14). This is the only partial-prefix reuse the hybrids get.
- [ ] **KVU-1d — replace the `vram_non_kv_gib` UNVALIDATED line** (still open after bring-up: research
  `75ee1b8e` declares 32.80 as UNVALIDATED, and the package's proof step 2 reading was not written back) with KFD − 6.375 from the M-1 reading. Record the
  reading through SSU-F3's prepared claim tuple (RTG-19).
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

### B — orchestrator
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

#### C2 — Restored task texts (v11 FA path, KVU-16g, KVU-19b, CPU-FA-VKQ)

Restored 2026-10-20. Commit `465954bc0` (2026-10-07) deleted 892 lines of this file in one commit, including every
task below; the ids stayed alive in `routing-and-optimization-index.md` RTG-57, in `dflash2-block-drafter-experimental-build.md`
DF2-9 and in `docs/reference/kernel-manifests/llama-v11-manifest.md` (rows V11-016/049/050/051/085/086), so they dangled.
The texts below are copied verbatim from `git show 465954bc0~1:handoffs/active/kv-unified-stack-rollout.md` (which also
holds the other deleted bodies, KVU-15..KVU-20, if any is wanted back); 2026-10-20 notes are marked. Ids not restored
here: none of the RTG-57 ids remain undefined. The owner named in these texts (workspace-ec) has had no bus heartbeat since
2026-10-08 (manifest at-risk item 2): the next session to claim any of them takes ownership.

- **v11 FA-path audit (2026-10-04, workspace-89; durable copy
  [`artifacts/v11-fa-path-audit-20261004/REPORT.md`](../../artifacts/v11-fa-path-audit-20261004/REPORT.md)).** Upstream
  #26046 deletes rocWMMA FA. On gfx90a, for our D=256 GQA-6 q8_0 shape, v11 then routes 3-32 query rows (4×1 batched
  decode, 1-3-slot DFlash2 verify) to the generic TILE kernel (no matrix cores; the RDNA4 analog #26220 lost ~2×) and
  >32 rows (4-slot verify, prefill) to MMA `<256,256,32,2>`, which spills 314 VGPRs under ROCm 6.2. The DF2-9 all-NaN
  path is the ROCWMMA=OFF route. These tasks gate the v11 rebase and RTG-58's P4 `kv_rows` phase
  ([`kv-prefix-fork-and-paged-attention.md`](kv-prefix-fork-and-paged-attention.md) KPF-40..42), and inform KVU-21.
  Owner of V11-FA-1..4: **workspace-ec** (filed 2026-10-04 at the coordinator's direction). Every build and run below
  takes `region-lock` for its host side.
- [x] **V11-FA-1 — A/B the champion with ROCWMMA=OFF (exact v11 FA routing) against ROCWMMA=ON, plus a third arm with
  #27870 and #28576 cherry-picked.** ✅ 2026-10-04 (filed 2026-10-04, workspace-ec, from the v11 FA-path audit §5) ROCWMMA=OFF
  reproduces upstream's D=256 routing: TILE at ≤32 rows, MMA above. The third arm approximates v11's MMA kernel
  (`b74f590ea` divergent-barrier fix, `bfdc32183` fp32 VKQ). Build in an experimental worktree, never the frozen tree.
  Bands: 4×1 decode, 1-3-slot DFlash2 verify (9-27 rows), 4-slot verify (36 rows), prefill (512 and mixed 512+3×9),
  own cells {4k, 16k, 57k} × foreign {0, 3×~100k}. Instruments: the 19b `perf2` micro-bench, `test-backend-ops` perf
  mode (TFLOPS, comparable to #28576/#28907), batched-bench `-kvu` vs `-no-kvu`, and the P3 harness L0 (v10: drafted
  36.3, no-draft 20.4 tok/s). Gate every arm on the DF2-9 reproducer (V11-FA-2) and on TILE D=256 `ncols2=2`
  run-to-run bit-exactness (those kernels have never been compiled into any of our builds). Done when the per-band
  delta is recorded here and decides one of: carry WMMA (V11-FA-4), retune the TILE/MMA crossover for gfx90a, cap
  ncols (V11-FA-3), or nothing.
  - *(2026-10-04, workspace-ec; prep done, slot not yet run, so not ticked.)* **Arms built, slot ready.** Scratch
    `/mnt/raid0/llm/tmp/v11-fa-ab-20261004/`; durable copy of the docs and runner:
    [`artifacts/v11-fa-ab-20261004/`](../../artifacts/v11-fa-ab-20261004/). Runner `gpu_slot_v11fa.sh` (one MI210 slot,
    budget 80 min, DF2-9 probes on every arm first). Arms: A `gpu-20261004-90c12df42-A` (ROCWMMA ON, champion recipe);
    B `gpu-20261004-90c12df42-B` (ROCWMMA OFF = v11 D=256 routing); C `gpu-20261004-5026470c6-C` (B + #27870 + #28576);
    D `gpu-20261004-fa5ebc0c8-D` (C + the CDNA D=256 MMA tuning of V11-FA-3); M upstream master `11fe02151`.
  - **The picks are neutral on the ROCWMMA-ON route** (`PICKS_ON_ROUTE.md`). Both #27870 and #28576 touch only
    `fattn-mma-f16.cuh`, and the ON champion launches no MMA kernel for any production shape: every cache-backed FA op
    has `K->ne[1] % 256 == 0`, so WMMA takes all > 2-row shapes. So arm A+ (ON + picks) was not built. The picks matter
    only on the OFF / v11 route.
  - **In v11 the drafter's 9-row block moves to MMA.** The DFlash2 drafter (D=128, GQA 4) block of 9 rows runs WMMA on
    the champion and D=128 MMA on v11 (≥ 5 rows), TILE at 3-4 rows. The audit did not list this shape; it belongs in
    the V11-FA-1 bands and the DF2-9 probes.
  - *(2026-10-04 PM, workspace-ec.)* **Ran; decision: carry WMMA (V11-FA-4).**
    - Slots: `slot-20261004T113710Z` (arms A/B/C/D/M/D32/D9; merged summary) and `slot-20261004T150551Z` (A/B/E/C).
      Durable copies: `artifacts/v11-fa-ab-20261004/slot-*/` (`summary.txt`, `perf_table.tsv`).
    - FA µs/op vs A (rocWMMA ON), on the v11 route:
      - 4×1 decode: ×0.60 (faster).
      - 1-3-slot verify, 9-27 rows: ×1.14-1.24 (TILE slower).
      - 36 rows: ×0.5-0.9 (B/C/M faster).
      - prefill-512: master M ×0.84-0.90; C ×1.09-1.16; B ×1.28-1.35.
      - drafter D=128, 9 rows: ×1.64-1.86 slower; 64 rows ×0.55-0.74.
    - Patches D and D9 do not help: D ≡ C at 512 rows, and D9 is ×1.35-1.42 at 9-27 rows.
    - The server DF2-9 arm errored on a busy port (18093) in both slots, so the model probe carries the DF2-9
      verdict (V11-FA-2).
- [x] **V11-FA-2 — root-cause DF2-9: all-NaN target features at ~2k-token prompts with ROCWMMA OFF.** ✅ 2026-10-04 (filed
  2026-10-04, workspace-ec, from the audit §0.4 and §4b) Build a standalone reproducer first: `test-backend-ops` cannot
  catch it, because its random [-1,1] inputs never overflow. Add a new FA case with large magnitudes and long KV
  (|V|~30, kv ≥ 4k) checked against the CPU reference. The length discriminator fits the >32-row MMA route: a short
  prompt's prefill goes to TILE, while ~2k prompts split into 512-row ubatches that go to MMA. Candidates in the
  audit's order: the D=256 MFMA-MMA route (consistent with the `99f3fffd6` unpadded-KV guard); the fp16 VKQ downcast
  (fp32 after #28576); the #27870 barrier. Record: `dflash2-block-drafter-experimental-build.md` DF2-9 and wiki CH-8.
  Done when the reproducer is 12/12 finite on the fixed path, or the faulting kernel and cause are recorded with an
  upstream issue.
  - *(2026-10-04, workspace-ec; reproducers built, GPU run pending.)* **DF2-9 sits on the MMA `<256,256,8,8>` route at
    60-340 tokens**, not `<256,256,32,2>` (see V11-FA-3's correction). Reproducers: `df29/` (op-level nan probe, the
    27B model probe `fa_nan_probe` and the server reproducer `df29_server.sh`, `df29/RECIPE.md`) run on every arm in
    `gpu_slot_v11fa.sh` step (a). **ggml CPU reproduces the fp16-overflow mechanism**: the CPU FA path accumulates VKQ
    in FP16 for F16 V and goes non-finite on diffuse attention over 2048 cells (CPU-FA-VKQ below), the same mechanism
    #28576 fixes for MFMA. Upstream issue text is drafted, never posted:
    `artifacts/v11-fa-ab-20261004/UPSTREAM-ISSUE-DRAFT.md`.
  - *(2026-10-04 PM, workspace-ec.)* **ROOT-CAUSED: the pre-#27870 MMA divergent-barrier race.**
    - Model-level probe (27B, 10 runs per arm):
      - B (ROCWMMA OFF): FAIL, 6/10 runs non-finite; first bad node `FLASH_ATTN_EXT` at layer 3.
      - E (B + #27870 only, `gpu-20261004-e9b3b04df-E`): PASS.
      - C (B + #27870 + #28576): PASS.
      - A (rocWMMA ON): PASS.
    - `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0`: B 598/640; E and C 640/640.
    - Op-level determinism: B 84/228 identical; C, D and E 228/228.
    - So **#27870 is a mandatory v11 carry** (V11-FA-6), and #28576 is not needed for DF2-9.
    - The NaN is not an upstream issue, because #27870 already fixes it. The NaN framing in
      `UPSTREAM-ISSUE-DRAFT.md` is superseded; only a perf-only issue remains (V11-FA-5).
    - The opnan non-finites left on A/C/D/E/M are the synthetic `v=bias1024` diffuse cases (fp16-range stress), and
      they occur on every arm.
  - [ ] **V11-FA-2b — give `df29_server.sh` a free port.** (filed 2026-10-04, workspace-ec) The fixed port 18093 was
    busy in both slots, so the server-level DF2-9 arm produced no verdict. Pick a free port at launch and refuse
    loudly if none is free. Done when a slot records a server verdict for every arm.
- [ ] **V11-FA-3 — MMA `<256,256,32,2>` spills 314 VGPRs on gfx90a under ROCm 6.2; evaluate an ncols cap for D=256
  prefill.** (filed 2026-10-04, workspace-ec, from the audit §0.3 and §3.1) `<256,256,16,2>` has 0 spills (499
  registers including 243 AGPR). The spill is structural: 512 threads means 2 waves per SIMD on gfx90a's unified
  register file. Candidates: cap D=256 at `ncols1=16` on CDNA2, or give `(256,256,64)` 256 threads. Leave the choice to
  AutoKernel. Re-check v11's own code object (these numbers predate #28576) with the register-audit scripts in
  `artifacts/v11-fa-path-audit-20261004/register-audit/`. Done when the prefill A/B (ON vs capped) is recorded, and
  the cap is either carried into the v11 candidate or declined with the numbers.
  - *(2026-10-04, workspace-ec; patch built as arm D, GPU A/B pending.)* **Correction to the audit:** for the 27B (GQA 6)
    CDNA picks `ncols2 = 8` by its generic ladder, so every >32-row shape (4-slot verify, mixed ubatch, 512 prefill)
    runs **`<256,256,8,8>`** (64 columns, 512 threads), not `<256,256,32,2>`; the latter is what a GQA-2 model or RDNA
    would run (`NCOLS_CAP.md`, register numbers from `fa_codeobj_audit.py`). Arm D implements the tuning: ncols2 by
    divisibility plus a 16-column cap (GQA 6 → `<256,256,8,2>`, the only spill-free D=256 MMA config with fp32 VKQ),
    with runtime knobs `GGML_CUDA_FA_CDNA_D256_MAX_COLS` and `GGML_CUDA_FA_CDNA_D256_MMA_MIN_ROWS` (arms D32, D9).
  - *(2026-10-04 PM, workspace-ec; A/B recorded, not ticked.)* **The ncols cap brings no gain.**
    - Arm D (16-column cap) ≡ C on 512-row prefill: ×1.16 / ×1.12 vs A.
    - D9 (MMA from 9 rows) is ×1.35-1.42 at 9-27 rows.
    - For reference, D32 measured ×0.97 / ×0.92 and master M ×0.90 / ×0.84 at 512 rows.
    - Recommendation: decline the cap. Still missing before the tick: the register re-check on v11's own code object
      (master `11fe02151`), which the slots' register tables do not include.
  - *(2026-10-20 restore; manifest V11-051.)* The default-on 16-column cap (`GGML_CUDA_FA_CDNA_D256_MAX_COLS`,
    `..._D256_TUNE=0` to disable) is carried in `experimental/v11-fa-ab-20261004` @ `2e0f9dd06`/`fa5ebc0c8` and is
    GPU-unvalidated; it is NOT in candidate C. Remaining work is unchanged: the register re-check on v11's own code
    object, then carry (`MAX_COLS=16|32` bench at the 27B shapes) or decline with the numbers. This task is the
    owner of manifest row V11-051.
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
  - *(2026-10-04, workspace-ec.)* The bands that decide it now include the drafter's 9-row D=128 block, which v11 moves
    from WMMA to MMA (V11-FA-1 note); arm A vs B/C/D in `gpu_slot_v11fa.sh` is the deciding run.
  - *(2026-10-04 PM, workspace-ec.)* **Justified by V11-FA-1.** On the v11 route:
    - TILE is ×1.14-1.24 slower for 9-27 rows.
    - The drafter's 9-row D=128 block is ×1.7-1.9 slower.

    WMMA therefore stays the arm for 9-32 rows. 4×1 decode (×0.60) and 36 rows are faster on the v11 route, so the
    knob should send only the 9-32-row band to WMMA.
  - *(2026-10-20 restore.)* No manifest row carries this arm yet; the v11 candidate list must either carry it or
    record the decline (kernel-manifests README rule 4). Caution: the A/B behind the 'justified' note above ran on
    the 2026-10-04 builds, not on candidate C.
- [ ] **V11-FA-5 — draft (never post) the upstream perf-only issue: on gfx90a, v11's TILE/MMA is slower than the removed
  rocWMMA FA for 9-32 rows.** (filed 2026-10-04, workspace-ec; WARRANTED under the upstream-report rule.)
  - Scope is perf only: the DF2-9 NaN is already fixed upstream by #27870.
  - Content: the V11-FA-1 numbers (`perf_table.tsv`), the arms and builds, and the drafter's D=128 9-row shape.
  - Done when the draft is in `artifacts/v11-fa-ab-20261004/` and handed to the operator. Posting it is the operator's
    call.
- [ ] **V11-FA-6 — the v11 candidate must carry #27870 (mandatory for DF2-9).** (filed 2026-10-04, workspace-ec)
  - The v11 rebase must contain `b74f590ea` (#27870).
  - Gate the candidate on the DF2-9 model probe (`df29/`, 10 runs, 0 non-finite).
  - Also gate it on `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` at 640/640 on the ROCWMMA-OFF route.
  - Done when the v11 candidate's gate record shows both.
  - *(2026-10-20 restore; manifest V11-049.)* Candidate C `f0c96dc1f` already carries #27870 as `f88127a86`. The
    ROCWMMA-OFF route probe (10/10 on an OFF build) and `test-backend-ops` 640/640 on that route are still owed
    (CH-20 item 3 in `autokernel-champion-aggregate.md`). CH-18 also lists #27870: reconcile at the v11 pull so it is
    not applied twice.
- [ ] **V11-FA-7 — decide upstream #28576 (fp32 VKQ accumulation on MFMA; manifest V11-050): fold into the v11 candidate,
  exclude with reason, or defer explicitly.** (filed 2026-10-20 from the derived-actionables gate; the 2026-10-04
  shard declined a separate #28576 carry task because DF2-9 does not need it and a master-based v11 contains it, but
  manifest row V11-050 is still PEND/'decision open' and README rule 4 requires fold/exclude/defer before the freeze.)
  Branch `experimental/v11-fa-ab-20261004` @ `5026470c6` (pick `bfdc32183`). Bench cell: GPU FA exactness (`test-backend-ops
  -o FLASH_ATTN_EXT -b ROCm0`) plus occupancy (CDNA config 4 to 3) at the 27B shapes, using the V11-FA-1 harness
  (`artifacts/v11-fa-ab-20261004/`). If the v11 pull is taken from master and master already contains #28576, the
  outcome is 'carried by the pull' and the row is closed with that sentence.
- **Other restored tasks cited by RTG-57 / the v11 manifest (parent task bodies remain in git history).**
  - [ ] **KVU-16g-1 — run the row-5c prefill-budget A/B (`gpu_slot.sh`) and score it against the done-when above.**
    (filed 2026-10-04, workspace-ec) Then fold `65d48a7a0` into the champion through the KVU-19 fold route if it
    passes, or record why not.
    - *(2026-10-20 restore; manifest V11-016.)* The A/B ran: GPU run dirs `gpuab-20261004T145622Z` and
      `gpuab-20261004T172118Z` under `/mnt/raid0/llm/tmp/prefill-budget-20261004/` (scratch; durability unverified). The
      fold ledger (candidate W, `autokernel-champion-aggregate.md`) quotes pb512 decode-under-prefill x2.92 with solo
      prefill -4% vs `-b 512` x3.22 / -14%, and the feature is folded in the champion (`7052e26df`, default OFF).
      The original done-when (decode under a neighbour's prefill >= 4x at <= 30% TTFT cost, KVU-16b re-run) is NOT met
      by x2.92 as quoted (unverified: score sheet not read). Closing this task = copy the per-arm table from the run
      dir here and record the score against the done-when; the enable decision is KVU-16g-2.
  - [ ] **KVU-16g-2 — enable `--prefill-budget-decoding` (+ `--prefill-budget-target-ms`) on :8083 in the v11 stack-change package.**
    (filed 2026-10-20 from the derived-actionables gate; manifest V11-016 and the champion aggregate say 'the :8083
    switch lands with v11' but no task enabled it.) Choose the target-ms from the PB-QCOST-1 fit
    (`gpu-serving-tie-in-program.md`); gate: decode-under-prefill >= the KVU-16g x2.92 reading, solo prefill within -4%
    to -14%, off == byte-identical; part of the one v11 stack-change signature (no piecemeal reload).
  - [ ] **KVU-19b-fold-c1-p3 — P3 B on the 27B against the folded champion: `-kvu` batched decode within ~5% of
    `-no-kvu`.** (filed 2026-10-04, workspace-ec, split from fold-c1's done-when) workspace-89's P3 harness
    (`p3_kvu_probe.sh` with a `BIN` override) on `gpu-20261004-1bceceb05`, arms skip on vs the same binary with
    `GGML_CUDA_FA_SEQ_ROWS=0` and `-no-kvu`; no-draft arms on their own server launch (KVU-16h-runner). Run it
    in the coordinated GPU block that also serves KVU-19 (workspace-89). Done when the per-arm table is recorded
    here.
    - *(2026-10-20 restore.)* Define-or-delete: the folded champion has since advanced (`dd3d9721c`); either re-aim this
      P3 B run at the current champion in the next coordinated GPU block, or record 'superseded by the v11 gate' and
      delete the id (the RTG-57 row cites it as `fold-c1-p3`).
  - [ ] **KVU-19b-rework-c2-cal — triage the two slot-3 calibration FAILs, then hand commit 2 v2 to workspace-89.**
    (filed 2026-10-04, workspace-ec)
    - (a) The hs=128 bound: decide whether the bound is mis-set, or the layouts-off path still differs from KVU-19a.
    - (b) Case 152: it fails against the CPU reference on every arm, k19a included, so fix the reference or the
      threshold.
    - Done when both are explained with numbers, and the fold hand-off (or the drop of commit 2) is recorded here.
    - *(2026-10-20 restore; manifest V11-085.)* Commit 2 is currently EXCLUDED from v11: about 14% slower on the aligned
      4x8 verify and breaks skip-on == skip-off exactness (6/119 cases); the rework result was not found. Branches
      `experimental/fa-maskskip-batched-20261004` @ `c7f5ac9ad`, `...-v2-20261004` @ `439b52cc2`. Parent task text
      (`KVU-19b-rework-c2`) is recoverable with `git show 465954bc0~1:handoffs/active/kv-unified-stack-rollout.md`.
      Define-or-delete outcome: if nobody triages the two calibration FAILs, record 'commit 2 dropped' here and in
      manifest V11-085 and delete this id from the RTG-57 row at the next index pass.
  - [ ] **CPU-FA-VKQ-2 — decode A/B of the fix on a CPU role at production threads.** (filed 2026-10-04, workspace-ec)
    The harness shows FA-op parity; serving decode is not yet measured. `llama-bench` tg at depth (e.g. 16k and 64k,
    F16 KV) fix vs `GGML_FA_VKQ_F16=1` in one binary, alternating, under `region-lock run --role bench`, n ≥ 5 per arm.
    Done when the decode delta is recorded with its noise floor; it gates CPU-FA-VKQ-1's promotion, not its fold.
    - *(2026-10-04 PM, workspace-ec.)* PENDING: the end-to-end bench of hybrid v2 is running; no result yet.
    - *(2026-10-20 restore; manifest V11-086.)* The register-resident arm `GGML_FA_VKQ_REG=1` (`5bde1b83d`) was
      local-only at the time (whether `13bdbdc4d`, the branch tip now on `fork`, contains it is unverified). The
      champion port carries the fix without the opt-in arms. Define-or-delete: run the A/B (including the `VKQ_REG`
      arm, if it is to be considered for v11) or record 'excluded, not benched' in V11-086 and delete this id from the
      RTG-57 row.

- [ ] **KVU-RESTORE-1 - audit and restore the task bodies deleted from this handoff by commit `465954bc0` (2026-10-07).** That commit is titled as adding the HYBRID-PREFIX-REUSE task but changed this file 12 insertions / 892 deletions (1234 -> 407 lines), about 50 task bodies (KVU-15..KVU-20 incl. KVU-16a..i and KVU-19a/b, CPU-FA-VKQ-0..4, V11-FA-*), which looks like an overwrite from a stale copy, not a deliberate compaction. The RTG-57 ids were restored under 'C2' on 2026-10-21; recover the rest from `git show 465954bc0~1:handoffs/active/kv-unified-stack-rollout.md` (sibling lineage: `06ce3ce14`, `a3f9206d9`), sort each into restore-as-open, already-done (tick with the original date) or superseded (archive to `handoffs/archived/`), and record the outcome. Done when no task id cited by an index row, manifest row or another handoff is undefined. (filed 2026-10-21 by the 3c4ca599 wrap-up, derived from the restoration of the RTG-57 ids)

### D — measurement follow-ups
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
  - **Reopened 2026-10-20 (operator):** measure the CPU concurrency x context tradeoffs before any frontdoor
    `--kv-unified` stack change, and reuse the matrix for the other models in the stack. Prompted by a vLLM
    deployment of the same 35B-A3B (NVFP4) that serves 8 x 64K from one shared pool, while :8070 caps each request at
    65,536 (`-np 4 -c 262144`, split KV). Matrix: KV {split, unified 512K/1M} x np {1,2,4,8} x L {8k..128k} x prompts
    {independent, shared-prefix}, fixed-length generation, >=3 waves, one deliberate pool-full cell. Spec and driver:
    `epyc-inference-research/artifacts/np_context_kvu_cpu_study_20261020/`. The timing half needs an exclusive
    full-host window.
  - *(2026-10-21.)* Tier-0 window W2 (00:30–04:45Z; epyc-inference-research `artifacts/np_context_kvu_cpu_study_20261020/w2_20261021/` (READOUT.md, capture rows, SHA256SUMS); v10 sha 4483bcfc, Qwen3.6-35B-A3B MTP on, one launch per cell): split np4 L64k decode sum 18.67 / 18.50 tok/s (ABA spread 0.9%, n=2 launches, higher=better), unified np4 L64k 18.22 (−2.0%), prefill −3.0%, TTFT +1.0% (lower=better). NOT like-for-like: the split arm lost its 4th stream to HTTP 400 context-exceeded (65.5k-token turn > 65,536 slot) in every decode wave (3 vs 4 streams), and cache-idle-slots was on for split, off for unified. Unified np8: L32k 26.71, L64k 10.18 tok/s sum (L64k at ~99% pool occupancy; unexplained 2.6× drop). Decision rule undecidable. s4 (np8 P=1M L128k) and the bank block SKIPPED for time (cells ran 1.8× estimate).
  - [ ] **KVU-12.4 — Tier-0 np4 L64k ABA redo with equal streams.** Size the depth-mode document so wave-1 suffix turns fit the 65,536 slot, run --no-cache-idle-slots on both arms, run the 32k anchor at start, middle and end for a floor with its unit (n ≥ 24 where it gates), and predeclare the unified-vs-split threshold in the PLAN before the window. Exclusive window, est ~7,800 s.
  - [ ] **KVU-12.5 — Tier-0 s4 re-run: unified np8 pool 1,048,576 L128k depth live** (skipped 2026-10-21 for time; est 10,639 s at the calibrated 1.795 factor), then the S2/S3 bank block (MTP-off np8 L64k control, occupancy, pool-full) and a split np8 L64k partner so np8 gets a relative claim. Next exclusive full-host window.
  - [ ] **KVU-12.6 — explain the np8 L64k decode collapse** (26.71 → 10.18 tok/s sum, L32k → L64k, pool ~99% occupied): separate pool occupancy from np/L with an np8 L48k cell and an np4 equal-token cell, and account for per-stream resume-depth differences, before any np8 decode figure is quoted.
- [ ] **KVU-12.1 — checkpoint-policy arms in the CPU np x ctx matrix.** On the frontdoor Qwen3.6-35B-A3B and the 27B add four hybrid-checkpoint arms to the KVU-12 matrix: dense (today: --checkpoint-min-step spacing plus n-4 / n-4-n_ubatch; record the positions actually materialized, since a chunk spanning several cadence boundaries materializes only its end), tail plus junction only (<=2 recurrent states per request via checkpoint_at on the fork build), fixed-interval with a cap on checkpoints per request, and a coarser grid whose resume is at most I tokens earlier than dense. Record per arm and per context length L: retained checkpoint count per sequence, bytes per checkpoint, resume prompt_n and cache_n, TTFT, and hit length against checkpoint spacing; baseline is the dense count at the current granularity; cite no external figure. Output sizes --ctx-checkpoints and --checkpoint-min-step and answers HYBRID-PREFIX-REUSE (b). Counts and prompt_n are correctness-class (build-role claim, no quiet host); TTFT and throughput wait for the scheduled exclusive window. Controls: frozen manifest = corpus manifest + bank_manifest sha256 + binary sha256; baseline = the dense arm on the same binary; raw per-request rows through the VB-KVU-CPU emitter; holdout = stride and cap chosen at L=32k and evaluated at 64k and 128k; denominator = every request including pool-full and errors; predeclared rule = an alternate arm replaces dense only if its resume prompt_n is within the dense arm's wave-to-wave spread at every L and its checkpoint bytes per sequence are lower at every L, else dense stays.
- [ ] **KVU-12.2 — MTP-on context bank: port #30574, gate it, fold it into the champion if it passes.** v10 slot save/restore writes ctx_tgt only (the study measured restored acceptance below 0.9x live, PLAN section 9 gate (b)), so MTP-on bank cells stay labelled "restored-draft" and no MTP-on decode tok/s from the bank is quoted as production-representative. Operator 2026-10-20: port upstream #30574 now onto `experimental/slotdraft-30574-20261020` from the champion tip (porting in progress), run gate (a) and gate (b) on that build against the unported champion as control with the study's predeclared rule (restored acceptance >= 0.9x live and restored decode >= 0.95x live, both layouts, both suffixes); if it passes, fold #30574 into the champion through the fold-ledger route (FOLD.md + trial merge onto the champion tip, recorded in autokernel-champion-aggregate.md) and run the MTP-on bank cells on the champion+#30574 binary, labelled with that binary; v10-binary MTP-on cells stay labelled restored-draft; a bank written by a build carrying #26640 is not restorable on v10, so rebuild banks per binary. Correctness class under region-lock; no external figure.
  - *(2026-10-20.)* Port + gate + fold done: `experimental/slotdraft-30574-20261020` (#26004 + #30574 ports) restored/live MTP acceptance 0.98–1.02 and decode 0.99–1.02 on both layouts vs the unported champion's 0.53–0.71 / 0.71–0.85 (`/mnt/raid0/llm/tmp/slotdraft-30574/REPORT.md`); folded as champion `dd3d9721c` (ledger in `autokernel-champion-aggregate.md`). Still open: the MTP-on bank cells on the `dd3d9721c` CPU image. Tonight's Tier-0 window (00:30–06:30Z, `/mnt/raid0/llm/tmp/overnight-20261020/`) runs the v10 production binary with MTP-on cells live.
  - *Dormant (research intake 2026-10-20):* Marconi-style FLOP-aware checkpoint eviction (recency plus alpha times covered tokens; our snapshots are equal-size, junctions are pinned). Trigger: the KVU-12.1 arms show unpinned-checkpoint churn with misses on long prefixes.
- [ ] **HYBRID-PREFIX-REUSE — make multi-turn prefix caching actually hit on hybrid (GDN/recurrent) production models via a prefill-only boundary checkpoint.** (filed 2026-10-07) — Owner: workspace-ec.
  - Finding: on hybrid models llama-server reuses a prefix ONLY via context checkpoints, and v10 creates them only at n-4/n-16 of each request's prompt. So a follow-up request that diverges inside the previous prompt's tail forces a full re-prefill (observed: prompt_n = full, "forcing full prompt re-processing (hybrid/recurrent)").
  - Workaround PROVED on CPU, Qwen3.8-27B: a prefill-only request (n_predict 0) of the shared prefix ending at a turn boundary puts checkpoints at prefix-4/-16. Later questions re-decode only their tail (prompt_n 58 and 74 vs 3556), and slot save/restore plus extension gives prompt_n == the delta with byte-identical output. Evidence: `/mnt/raid0/llm/tmp/jetlong-gpu27b-20261006/SAVE_RESTORE_TEST.md` and `saverestore5/` (copy `SAVE_RESTORE_TEST.md` to `artifacts/hybrid-prefix-reuse-20261007/` and cite the copy).
  - Also note: champion commit `ef81196d5` adds user-message-start checkpoints, which may make this automatic.
  - Plan, as sub-bullets:
    (a) correctness on the production frontdoor :8070 recipe (Qwen3.6-35B-A3B): a multi-turn replay with and without a prefill-only boundary request, and also on the champion (`ef81196d5` user-message checkpoints), measuring prompt_n and cache hit rate per turn, plus greedy identity. This is CORRECTNESS work, under build-role quarter claims.
    (b) if (a) passes, choose the mechanism (orchestrator-side prefill-only boundary request vs the champion's server-side user-message checkpoints) and the `--ctx-checkpoints` / `--cache-ram` settings.
    (c) TIMING: TTFT and throughput A/B in a scheduled window.
    (d) stack-change package for :8070 (and :8083 if applicable).

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
- SSU-F3 structural capacity model (RS, draft KV, compute terms): owned by RTG-19. INF-41 aux VRAM in the gate:
  owned by OP-48 / INF-41.
- Package §10 items that the overflow branch already fixes: the 20,000-char routing threshold (now tokens and
  capacity-fenced), the 32768 compaction fallback, and 400 / "Context size has been exceeded." handling.
- The speech addendum's "priority pause instead of partitioning" alternative: not filed as its own task, because a
  pause cannot act mid-token and no mechanism exists; it survived as option C (KVU-11b; operator chose D).
- Frontdoor-under-partition measurement: not filed; the operator chose D (KVU-11b), and any re-run belongs to
  the operator's STT/TTS plan.
- A Stage-1 intake sweep of the audit's new primary sources (vLLM / SGLang / TGI / TRT-LLM / LMDeploy / LMCache
  docs): no claim here relies on them. Intake runs only when the operator invokes it.

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

## Research intake 2026-10-20 — DeepInfer (research intake entries 2116–2142, see research/intake_index.yaml)

Operator-approved 2026-10-20 via research intake (plan sha256 recorded in the session's stage3_filing).

- [ ] **KVU-21 — Agent-resume recompute probe on :8083 (intake-2131#record).** From existing request logs/timings compute, per resumed agent turn, recompute fraction = prompt tokens processed / prompt tokens, and pool usage from /slots, vs concurrent agents 1..4 plus queued; one bounded 4-agent fan-out replay in a GPU window only if logs lack it. Rule: median recompute fraction >= 0.25 at >= 3 agents while usage >= 0.5 opens the CONCUR-style AIMD admission trigger; below closes it.
  - *(2026-10-20, workspace-f8.)* usage arm NOT JUDGEABLE (/slots pool usage is in no :8083 log); fraction arm on agent-length resumes (prompt>=2000): median recompute 0.065 at >=3 busy slots (n=43), 0.014-0.015 at 1-2, all below 0.25; leans toward closing the CONCUR trigger, not conclusive; evidence /mnt/raid0/llm/tmp/analytics-20261020/KVU-21/REPORT.md.
- [ ] **KVU-12.3 — Decode-boundary checkpoint arm for the KVU-12.1 matrix (intake-2116#record).** Add a fifth hybrid-checkpoint arm that snapshots recurrent (and drafter) state every 128 generated tokens (capped per sequence), run on the frontdoor Qwen3.6-35B-A3B and the 27B with the KVU-12.1 controls; measure turn-2 resume prompt_n after 1k-4k generated tokens vs the dense arm, checkpoint bytes and TTFT. Counts are correctness class; TTFT in a window.

**Dormant triggers (no checkbox, no index next action; materialize a task only when the trigger is observed). 'An' in a row means that intake entry's own dive-ledger row n:**

- DI-016 (intake-2119): monitor: revisit when (a) a second MI210 is attached (CS-12 cascade, kv-unified-stack-rollout.md:331) or (b) an NVMe-resident KV tier becomes the reload source and its read bandwidth, not PCIe, is the measured bottleneck
- DI-018 (intake-2119): monitor: admission-queue wait or TTFT p95 on :8083 rises while pool occupancy stays below its fit limit (that is the signature a pool-fit-only cap misses)
- DI-023 (intake-2120): monitor: llama_perf sampling time (t_sample_ms) exceeds 1% of eval time on a production frontdoor/architect log; otherwise knowledge-only (DeepSelect fp32 sampler claim is CUDA-only and our sampler already single-pass)
- DI-047 (intake-2125): monitor: the dive found Gemma-3n/4 KV-shared tail layers get no prompt-row pruning in prefill (exact skip available), but Gemma-4 was retired and deleted from the lineup on 2026-09-23 (orchestration/model_registry.yaml deprecated_models @ 62ee3ba6), so no consumer exists today. Trigger: any model with n_layer_kv_from_start sharing (Gemma-3n/4 class) re-enters the lineup; then file the exact row-prune with last-row logit parity.
- DI-053 (intake-2126): monitor: the AutoKernel GPU profiler reports MI210 prefill (-ub 2048) as compute-bound on GEMMs with a material attention share of layer time (otherwise nothing to overlap), or a hardware change adds idle matrix capacity (second MI210 / matrix-capable part). Until then knowledge-only.
- DI-060 (intake-2116#record): monitor: revisit only if a llama-server async-scheduling task is filed from the scheduler dive; trigger = any task that overlaps host scheduling of step N+1 with device forward of step N.
- DI-106 (intake-2131): monitor: CONCUR-A1 probe result (KVU-21) shows recompute fraction >= 0.25 at >= 3 agents with usage >= 0.5; then draft task in kv-unified-stack-rollout.md
- DI-126 (intake-2136): monitor: short-request TTFT p95 on a shared server rises while a request longer than 16K tokens is prefilling (join request_keys with the inference tap); until measured there is nothing to fix.
- DI-140 (intake-2140): monitor: a host-pinned KV tier prototype (hipHostRegister mapped region plus a small gather kernel, source-copied MIT from ROCm/mori UMBP and compiled for gfx90a) is the read side of a write-through mirror; trigger = the analytic write-through mirror costing finds the mirror fits the decode budget and removes measurable handover cost. MORI itself does not support gfx90a or ROCm 6.2, so this is a port, priced there.
- DI-142 (intake-2140): monitor: second MI210 installed AND a serving-engine EP consumer exists; then rerun this port map (first step: add gfx90a to _supported_arch_list / MORI_SUPPORTED_ARCHS with MORI_GPU_ARCHS=gfx90a and run only the intranode ep2 test)

**Retained knowledge (no task):**

- DI-008 (intake-2117): knowledge-only: lessons (1) and (3) feed kv-prefix-fork-and-paged-attention.md and v9-kernel-per-request-speculative-params.md as design context; no task.
- DI-011 (intake-2118): knowledge-only: design reference for A2 option (2); no separate task until A2 probe shows the class is open on a live server.
- DI-017 (intake-2119): knowledge-only: design rule for any future mirrored/offloaded KV traffic (see intake-2126-A3): price it against decode-in-flight on the same link and cores before enabling
- DI-019 (intake-2119): knowledge-only: have an equivalent feedback budget; revisit only with the sarathi-serve-cpu-evaluation re-promotion trigger (multi-tenant / prefill-heavy)
- DI-048 (intake-2125): knowledge-only: only Gemma-3n/4 in the lineup share KV across layers; nothing else benefits from YOCO-style prefill skipping.
- DI-049 (intake-2125): knowledge-only: cite YOCO for the exact early-exit argument and the O(N+CL) memory formula; do NOT cite its 71.8x/9.6x/80x figures as achievable on our stack (H100, gRet, 3B).
- DI-051 (intake-2126): knowledge-only: sets the precondition for A1 follow-up: only the non-spec arms (and CPU draft-free roles) could use a lagged batch; revisit if A1 shows a material gap in the no-spec arm
- DI-054 (intake-2126): knowledge-only: one-line regime test for the roofline program and np/batch sweeps; no new task
- DI-064 (intake-2116#record): knowledge-only: retained use is the boundary condition for any future "replay instead of checkpoint" proposal on Qwen3.6/3.8 hybrids (reject for GDN layers; only drafter SWA windows qualify, covered by KPF-13.1).
- DI-065 (intake-2116#record): monitor: next pull of fresh production into llama.cpp-experimental carries PR #30580 (llama.cpp upstream); trigger = KPF-17.4 SWA checkpoint range case runs on the new tip.
- DI-067 (intake-2116#record): knowledge-only: retained use is the comparison point for KPF-18.1 hit-length rows and a candidate hit policy for DS41 only after DS41-CED.1 shows the approximation is acceptable.
- DI-070 (intake-2116#record): knowledge-only: retained use is the Sarathi reopen comparison (sarathi-serve-cpu-evaluation.md:L14) - cite as vendor-reported engine behaviour code-verified @774ce24
- DI-092 (intake-2116#record): knowledge-only: cite the coverage_complete / rule-vs-judge agreement pattern when touching quality-gate summaries; do not import vendor Pass@1 as an EPYC target
- DI-098 (intake-2128): knowledge-only: Gemma-3n/4 are natively trained with KV sharing (not YOCO-style early exit; their upper layers still run for every token); the YOCO++ evidence neither supports nor refutes them, and no layer-skipping prefill on them is implied.
- DI-107 (intake-2131): knowledge-only: retained use = if A2 opens, fold a usage gauge into the same champion patch series rather than polling /slots; HSF-2 (heterogeneous-slot-fabric-residency.md:L276) already owns --metrics launch argv
- DI-108 (intake-2131): knowledge-only: intake-2119 reader_should_conclude should drop CONCUR as the support for the hit-rate figure; the 98.7% stays DualPath own-trace, vendor-reported
- DI-127 (intake-2136): knowledge-only: design input for the HSF demote threshold (0.8 hysteresis and a drain grace as starting hypotheses to be replaced by HSF-1 swap cost data); no separate task.
- DI-143 (intake-2140): knowledge-only: retained as the prior for MORI-A1 tier placement (no placement experiment needed unless A1 proceeds)
