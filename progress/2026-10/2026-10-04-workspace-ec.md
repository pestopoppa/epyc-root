# 2026-10-04 — workspace-ec

Continues `2026-10-03-workspace-ec.md`. Per-task wrap-up for the work completed since root `ab84e579`. A GPU
measurement block is running on :8083 while this is written (Q38-T7 first); nothing below touched it.

## UFH14-B1 F1/F2, orchestrator half: DEPLOYED (complete)

- **Problem.** workspace-89's F1/F2 proposal (derived prefill timeouts, forced-answer turn, compaction) had to land
  model-independently in the orchestrator (UFH14-B1b).
- **Review fixes against the proposal:**
  - `doomed` was overstated ~2.5x. It is now judged against one prefill of the UNCACHED tokens.
  - A sample-cache eviction bug was fixed.
  - The design note's clamp claim was wrong: with any deadline the dispatch clamp returns the remaining budget. So
    under a deadline, F1 can only record `doomed`.
  - The compaction finding was real: `TaskState.context` never reaches a turn prompt. Fixed always-on:
    - a deterministic compaction index;
    - the overflow path no longer force-compacts;
    - a test proves that turn prompts are byte-identical.
  - The passthrough derivation now runs before the gate, and the body stays verbatim.
- **Flags, all OFF (attested):** `derived_prefill_timeout`, `repl_answer_force`, `session_compaction_llm_index`.
  **Always-on:** the deterministic index, the overflow path, the `serving_params` record block, the cache fix.
- **Tests:** 45 new and 921 related tests passed, and the drift check is clean (rc 0 each,
  `/mnt/raid0/llm/tmp/ufh14-b1-ec-review/`). The first run had 5 failures:
  - 4 came from a fake backend `infer` signature in the test;
  - 1 was a real 7-char cap overrun from the separator, fixed in ff92a580.
- **Deploy.** Orch main `ff92a580` (3a326a7c, 1d03d9b4, cd5d7d97, 63855968, ff92a580). API-only reload → PID 3858207;
  `ps` lstart is 02:06:46Z.
- **Live check.** The 02:49–02:51Z :8083 passthrough records carry `serving_params`. All four show
  `prefill_source: unmeasured`, so no long call has been priced yet.
- **opencode user config** (`/home/node/.config/opencode/opencode.jsonc`): `headerTimeout`/`chunkTimeout` =
  14,400,000 ms for `qwen-local` and `qwen-gpu`. Applied with the operator's explicit OK (AskUserQuestion, 10-04);
  backup at `/mnt/raid0/llm/tmp/ufh14-b1-20261003/opencode.jsonc.bak-20261004`. The codex template went to
  workspace-89 for their CODEX_HOME.
- **Not ported**, each now a task with its own flag: the `PROVISIONAL` primitive (B1e) and per-turn thinking-budget
  wiring (B1f).
- **The STACKCHANGE timeout item is HELD** until a window of corrected `doomed` counts exists (B1d).
  - Recommendation: Option A, with comment-only registry changes. Check `ingest_long_context` first: 300 s, which is
    doomed above ~77k tokens on :8083.
  - Option C is rejected.
  - Durable copy: `docs/design/ufh14-b1-timeout-stackchange-item-20261003.md`.

## STACKCHG-HYGIENE-20261003: VALID, awaiting the operator's signature

- Package: `/mnt/raid0/llm/tmp/stack-change-hygiene-20261003/PACKAGE.md`. `--validate-only` reports VALID with 68
  pins (`validate-main.out`), and both patches apply to orch `ff92a580` and research `412e8fc1`.
- What it changes:
  - **KVU-16a:** 38.03 GiB measured replaces 39.15 derived.
  - **SCG-PRIORS-WARM:** scoped to seeding `DEFAULT_ROLES` and `discover_active_roles`. `live_stack` is kept for its
    ~40 consumers.
  - **DRAFT-SEL-2:** the frontdoor and Flash-Next drafters move to DRAFT-SEL-1 form, and the :8074 `spec_overrides` is
    retired. `LEGACY drafter` warnings go 2 → 0.
- Argv identity is 11/11 live servers, so no relaunch is needed. All three items are annotated as packaged; none is
  ticked.
- Signing command (operator terminal): `RATIFY_OPERATOR="<name>" bash
  /mnt/raid0/llm/tmp/stack-change-hygiene-20261003/ratify_stackchg_hygiene_20261003.sh --attest
  RATIFY-STACKCHG-HYGIENE-20261003`.

## :8083 SLOTS_DEBUG window ended (UFH14-DIAG-EC-a, complete)

- The override's TTL expired at 19:44Z on 10-03. Nothing restored it, because the A3/A4-done notice was missed, so
  `declared_env_attestation` sat in its post-expiry ERROR state for ~6 h.
- Restored at 01:58:23Z by a plain `reload architect_critic` → PID 3843823. The record is archived
  (`epyc-orchestrator/logs/env_overrides/architect_critic.history.jsonl`) and `readback --expect-declared` is ok.
- Follow-up filed: UFH14-DIAG-EC-b, so that an expiry reaches its owner.

## GPU block started 01:59Z

- It was planned for 18:15Z on 10-03 and was delayed by the same missed notices.
- :8083 was parked through the `gpu_window` CLI, the first live use of parked-role support.
- workspace-89's seed #1 ran ~02:00–02:25Z. That run is theirs; this is a note only.

## KVU-19a-1: gpu_slot.sh PASSED on the store build (complete)

Results: `/mnt/raid0/llm/tmp/fa-maskskip-20261003/slot-20261004T022552Z/`.

| Check | Result |
|---|---|
| exactness, skip off vs on | 64/64 bit-identical |
| exactness, champion vs on | 58/64 bit-identical, worst nmse 3.05e-7 |
| `test-backend-ops` FLASH_ATTN_EXT | 2920/2920, both with the default `MIN_KV` and with `MIN_KV=0` |
| micro-bench nb=1, +114,688 foreign | base ~2003 µs → on ~282 µs (7.1x) |
| micro-bench nb=8, +114,688 foreign | 3808 → 584 µs |
| micro-bench, 0 foreign | 271 vs 275 µs (noise) |
| P3-mini (gemma-3-1b), draft 1, 3×32k idle neighbours | 82 → 169 steps/s (no-neighbour ~182–197) |
| P3-mini (gemma-3-1b), draft 8, 3×32k idle neighbours | 41.8 → 89.5 (no-neighbour ~99.5) |
| batched-bench 4×16k, S_PP | kvu base 13,205 → new 21,017 t/s (no-kvu ~20,000) |
| batched-bench 4×16k, S_TG | kvu base 437 → new 444 vs no-kvu 542/551 |

- **Finding: the skip does NOT help concurrent decodes.** A batched decode's query tile spans all sequences, so its
  live set is their union. Production flushes idle slots (211 organic purges), so concurrent decode is the
  production-relevant case.
- KVU-19a-1 and KVU-19a are ticked. Per-row skipping is filed as KVU-19b (workspace-ec, experimental branch).
- workspace-89's KVU-19 is annotated: its batched-bench expectation already fails at small scale.

## DEPLOY-EC-2 live proofs: lease and credit PASSED (complete for those parts)

Evidence: `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/ec2_lease/`. :8083 ran at production flags
(`slots_debug_env: null`).

- **KVU-15a lease** (`20261004T025039Z`):
  - two concurrent ~24k-token passthrough prompts;
  - the lease was held by 2 different API worker PIDs (3858210, 3858214), never at once;
  - :8083 had at most 1 slot prefilling;
  - B waited 48.9 s for A's prefill.

  The first attempt (`…024825Z`) failed only because the runner's lane B used /v1 client mode without the required
  `x_session_id` (422). It was re-run with two passthrough lanes. The runner fix is filed as DEPLOY-EC-2e.
- **KVU-15c credit** (`…024825Z`): call 2 was credited 18,829 tokens from `fp_history`, against a server `cache_n` of
  22,178 (ratio 0.85). It was sized as a 7,197-token prefill and was not held (5.3 ms wait).
- Ticked: KVU-15a, KVU-15c, DEPLOY-EC-2a and DEPLOY-EC-2b.
- Still open:
  - RI-18c, which needs a completed live `/chat` (2c);
  - a primitives-lane record with `prefix_fp` (2d), since no primitives call ran;
  - primitives-lane `long_prefill`, which is KVU-15d (already filed).

## In progress, not complete

Q38-T7 has been running since 02:52:47Z (`results/q38_t7/20261004T025247Z/`). After it come KVU-16b, B4g, B4i, then
workspace-89's P3 v2 on the mask-skip build.

## Files

| Repo | File | Change |
|---|---|---|
| root | `handoffs/active/agentic-serving-harness-fixes.md` | B1b ticked. B1c annotated. B1d–B1h filed. DEPLOY-EC-2a/2b ticked (2a is the lease, 2b the credit); 2c/2d/2e filed. DIAG-EC-a ticked; DIAG-EC-b filed. |
| root | `handoffs/active/kv-unified-stack-rollout.md` | KVU-15a, KVU-15c, KVU-19a and KVU-19a-1 ticked. KVU-16a annotated. KVU-19b filed. KVU-19 annotated (workspace-89's). |
| root | `handoffs/active/stack-change-governance-pipeline.md` | SCG-PRIORS-WARM and DRAFT-SEL-2 annotated. SCG-PRIORS-WARM-b and DRAFT-SEL-2b filed. |
| root | `handoffs/active/qwen38-27b-replace-qwen36.md` | Q38-T7 annotated as running. |
| root | `docs/design/ufh14-b1-timeout-stackchange-item-20261003.md` | Durable copy of the B1 STACKCHANGE item. |

Prepared index edits (not applied): `/mnt/raid0/llm/tmp/wrapup-ec-b1slot/INDEX_ROWS.md`.
