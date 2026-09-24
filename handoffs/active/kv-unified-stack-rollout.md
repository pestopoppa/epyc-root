# Unified KV (`--kv-unified`) stack rollout and shared-pool serving

**Status**: ACTIVE. Diagnosis, package, inventory, audit, orchestrator branches and the 27B GPU measurements are
done (2026-09-24). What is left is operator signatures, bring-up, and the follow-ups below.
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
| GPU np × ctx study: 27B split vs unified, O-2, pool-full repro, MTP depth | research `artifacts/np_context_kvu_study_20260924/` on research main `21cf444c` (README + SHA256SUMS; the 35B-A3B run `q36_35b_a3b_q8_h/` is not committed yet). The study README cites the package at its scratch path; the committed copy is the root path in the first row |
| CPU STT/TTS real-time study | research `artifacts/speech_cpu_realtime_20260924/README.md`. Research `21cf444c` holds the 17:14Z snapshot. An SMT-sibling (`smtC`) run was still writing to the shared clone at 17:53Z and is not committed (KVU-11a) |
| Live working view (database-backed page) | https://claude.ai/artifact/Lr4Xd1jBwUW3ToDCQJCEjm |
| Orchestrator: context-overflow handling | `feat/context-overflow-handling-20260924` @ `8bbe2a3c` (pushed; 80 tests; worktree `/mnt/raid0/llm/tmp/orch-ctx-overflow-20260924`) |
| Orchestrator: promotion-gate fix | `fix/promotion-gate-red-20260924` @ `d7ab368e` (pushed). Strict is green via option A: `9692c7f9` was merged on the operator's direction |

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
- [x] **KVU-0h — promotion gate reduced from 14 errors to 4** on `fix/promotion-gate-red-20260924` (stale tests
  re-fixtured to the 2026-09-22 lineup, sources pinned repo-relative, derived artifacts recompiled). Strict went
  green at `d7ab368e` via option A (KVU-4). ✅ 2026-09-24

### A — :8083 bring-up
- [ ] **KVU-1 — apply the signed `-kvu` package and prove it serves** (OP-54).
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
- [ ] **KVU-1c — add the context-checkpoint read to the serving proof.** With `-lv 4`, confirm `created context
  checkpoint` fires on :8083 (audit #8 / T14). This is the only partial-prefix reuse the hybrids get.
- [ ] **KVU-1d — replace the `vram_non_kv_gib` UNVALIDATED line** with KFD − 6.375 from the M-1 reading. Record the
  reading through SSU-F3's prepared claim tuple (RTG-19).
- [ ] **KVU-2 — size `serving_shape.cache_ram` per server** (audit #4 / T8; OP-55). Today every server runs the
  8192 MiB default, and one full-pool 27B prompt (~9.2 GiB, inferred) does not fit.
  - Recommendations: 65536 MiB on :8083 (floor 24576), 32768 on :8070, 16384–32768 on :8074, 0 on :8086.
  - The value compiles to `-cram` already. Land it at the same :8083 reload if the operator agrees; a second
    reload costs a planner transient.

### B — orchestrator
- [ ] **KVU-3 — land `feat/context-overflow-handling-20260924` @ `8bbe2a3c`** once OP-55 decides:
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
- [ ] **KVU-4a — clear the gate's only remaining failure: runtime attestation.** :8070, :8074, :8080 and :8180 run
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
  `/proc/<pid>/environ`, or scrub `LLAMA_ARG_*` from the launch env.
- [ ] **KVU-13b — the stack-change skill's DERIVATION source list omits the files a new launch flag needs**
  (`src/registry/stack_priors.py`, `scripts/server/stack_commands.py`, `scripts/server/orchestrator_stack.py`).
  Also, `preflight.sh`, `capacity.sh` and `topology_check.py` hardcode the real ORCH path, so they cannot run
  against a scratch clone. Fix both in `.claude/skills/stack-change/`.

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
- [ ] **KVU-8 — confirm the throughput verdict with fixed-length or multi-wave generation.** Every cell is n=1, and
  the np4 aggregate gap tracks divergent completions. Rerun the np 2/4 cells with fixed-length generation
  (`ignore_eos` + `n_predict`) or at least 3 waves, both arms on the same binary. Carry the write-side hook
  (VB-KVU-1) from the first run.
- [ ] **KVU-9 — finish, commit and read the Qwen3.6-35B-A3B-MTP Q8_0 GPU matrix.** Research
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
- [ ] **KVU-11a — commit the speech study's follow-up run.** After 17:14Z the study kept writing to the shared
  research clone: an `smtC` SMT-sibling run, an edited `speech_cpu_bench.py`, and a grown
  `raw/whisper_bench_encoder_matrix.txt`. Once it finishes:
  - commit the delta onto research main (`artifacts/speech_cpu_realtime_20260924/`, SHA256SUMS regenerated);
  - update the README's option C;
  - after a checksum match, remove the shared clone's untracked copies, so DS41-C10a's fast-forward is not blocked.
- [ ] **KVU-11 — decide where STT/TTS live** (OP-56). Research `artifacts/speech_cpu_realtime_20260924/README.md`.
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

## Not filed here (explicit)
- SSU-F3 structural capacity model (RS, draft KV, compute terms): owned by RTG-19. INF-41 aux VRAM in the gate:
  owned by OP-48 / INF-41.
- Package §10 items that the overflow branch already fixes: the 20,000-char routing threshold (now tokens and
  capacity-fenced), the 32768 compaction fallback, and 400 / "Context size has been exceeded." handling.
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
OP-54, OP-55 and OP-56 in the master index. The gate's known-gap choice was decided before filing: option A.
