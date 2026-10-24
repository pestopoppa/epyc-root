# Unified KV stack rollout: completed history through 2026-10-24

Historical ledger only; current work lives in [`../active/kv-unified-stack-rollout.md`](../active/kv-unified-stack-rollout.md).
Moved verbatim from the active handoff by the 2026-10-24 operator-invoked /wrap-up (workspace-f8). Line links inside point at the active file's pre-move numbering.

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

