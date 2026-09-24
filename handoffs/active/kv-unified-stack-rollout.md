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
