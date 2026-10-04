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

---

# Wrap-up 2 (since root e4bae1c1): GPU block results, coherence_gate, the KVU-16b root cause, INF-59 rewrite

Per-task wrap-up, run by a subagent in lane `te-book-20260927`. No processes, no inference. Index edits are prepared
only, in `/mnt/raid0/llm/tmp/wrapup-ec-gpublock2/INDEX_ROWS.md`. The GPU-block evidence and the analyses were all in
`/mnt/raid0/llm/tmp`, which is scratch. They are now copied durably to `artifacts/gpu-block-27b-20261004/` (46 files,
~1 MB): `results/`, `runners/` and `analysis/`.

## Q38-T7: DFlash2 at the production shape PASSES (complete)

- **Problem.** Run #1 (`results/q38_t7/20261004T025247Z`) reported "Correctness FAIL, speed INVALID".
- **Root cause.** It was a classifier artifact, not a drafting fault.
  - The v1 `uniq < 0.35` rule is length-biased. Measured on the repo's own corpora with the 27B tokenizer, every
    coherent 1000–1500-token reasoning trace scores SALAD (`analysis/q38t7-rescore/length_bias.json`).
  - `lib_gpublock` also read chat "stop" on 1–8-token answers as EARLY-EOS.
- **Fix.**
  - An offline paired re-score (`RESCORE.md`) gave PASS. Phase A had 0 regressions out of 24; ground truth was 4/5 in
    both arms; phase B/C were 12/12 OK under `inf70-degeneracy.v2`.
  - A paired long-context re-run with full text (`20261004T040110Z`, schema v2) gave PASS.
  - The caller eyeballed a saved 1500-token output.
- **Results:**
  - Production mix: DFlash2 60.02 vs no-draft 31.07 tok/s (1.93×), acceptance 0.53.
  - DFlash2 ≈ MTP at depth: 0.95–1.06×, a cross-shape comparison.
  - 4 × 16k concurrent: 20.84 tok/s aggregate.
  - The 80k needle was an injection-abstain (model behaviour).
- **Handoff.** Q38-T7 is ticked. The organic-traffic acceptance clause was not met (the window was parked), so it is
  split out as Q38-T7a. The needle redesign is Q38-T7b.

## INF-70 classifier audit and replacement (complete for the build; adoption tasks filed)

- **Audit** (`analysis/q38t7-rescore/AUDIT.md`):
  - The classifier was a near no-op in every chat client. They pass fake ids `list(range(n))`, so uniq, top and run
    were vacuous.
  - Recomputing 403 rows files gives 0 SALAD. No production decision flips. The MTP divergences were re-read and are
    fluent alternatives.
- **Replacement:**
  - The `coherence_gate` library is on research main 95157ad7: tiers 0–1, `degeneracy.v2`, refuses fake ids, 55 tests.
  - The judge endpoint `POST /v1/typed/coherence_judge` is on orch main f8c9c0a3, DEPLOYED by an API reload. The
    window guard was verified live.
  - The champion-sidecar native backend, plus the prefill optimisations, is on `feat/judge-champion-backend-ec`
    4359b43c, NOT merged.
- **Rectification** (`analysis/classifier-rectify/RECTIFY.md`):
  - 01 and 02 were applied by workspace-89.
  - 03 is on research main 030daa86.
  - 04, the harness1 fake-id fix, is CLS-RECT-1a.
  - 05, the SC75 census, is VB-SC75-CLS.
  - 06, the wiki correction, waits for the next operator-invoked `/wrap-up` wiki sweep (operator-cadence step).
  - 07, the era rows OC1 + CLS1, is TD-30e plus OP-75.
- **Operator-approved scope:**
  - The judge is orchestrator-hosted.
  - Cloud `codex-luna-low` / `sonnet-low` are allowed only for cloud-hosted callers.
  - Local work targets the CHAMPION, with no promotion now.
- **The memory note** `feedback_coherence_gate_at_production_prompt_length.md` was updated by the caller.

## KVU-16b: the residency runner's PASS is INVALID (not ticked); root cause found

- **The run** (`results/kvu16b/20261004T032520Z`) reported PASS. workspace-89's read-only root cause
  (`analysis/kvu16b-rootcause-REPORT.md`) shows the predicate read a stale `n_decoded`: one request was still
  prefilling, so the true peak was 3 decoding + 1 prefilling. The runner fix is KVU-16b-1.
- **The 0.52 tok/s.** Prefill is interleaved into decode batches: ~2024 prompt tokens per iteration (`n_batch` 2048).
  Without the masked-block skip, each chunk reads every occupied cell, ~17–19 s per chunk at 240–310k. Drafting stayed
  healthy at 2.8–4.2 tokens per step.
- **The fixes:**
  - `-b 512 -ub 512` (KVU-16f, then one stack change with UFH14-B4j);
  - a Sarathi prefill budget (KVU-16g, in flight on experimental, `/mnt/raid0/llm/tmp/prefill-budget-20261004/`);
  - KVU-19a in production (workspace-89's fold);
  - KVU-19b;
  - a cross-slot prefix fork (KVU-20, survey Rec 2).
- **VRAM.** 51.7 GiB at load, then 58.88 → 59.77 GiB while serving: +7.2 GiB, ~2.2 GiB to the 62 GiB gate. The suspect
  is the legacy HIP pool (`NO_VMM=1`). Attribution is KVU-16h (URGENT); the capacity-gate runtime term is KVU-16i.
  KVU-16a/OP-72's 38.03 GiB is right as a load-time figure.
- **The KV-serving survey** (`analysis/kv-serving-survey-REPORT.md`): Recs 1–4 filed (KVU-16g, KVU-20, KVU-19c,
  KVU-21); Rec 5, slot-linger, the vLLM probe and host-tier sizing are declined with reasons in the handoff.

## UFH14-B4i: `--no-cache-idle-slots` OFF wins (complete); B4g inconclusive

- **B4i**, on scratch :18083 with 3 conversations × 6 turns per arm:

  | metric | ON | OFF |
  |---|---|---|
  | turn-2+ TTFT median | 66.4 s | **16.3 s** |
  | turn-2+ TTFT p90 | 81.0 s | **19.2 s** |
  | `hit_tok` | 0.81 | 0.81 |
  | KFD | 51.71 GiB | 51.71 GiB |
  | decode | 18.8 tok/s | 20.8 tok/s |

  ON purged idle slots (9 drops on `/slots`). n=1 rep per arm. Ticked. The stack change is UFH14-B4j, combined with
  KVU-16f.
- **B4g.** Zero `prompt_save` lines on the current shape, even after 4 long calls. The likely cause is launch verbosity
  3: the B4i ON arm also logged no `saving idle slot` lines. The investigation is UFH14-B4g-1, which must come before
  any re-run.

## KVU-19b built CPU-side; GPU validation running

- **Branch** `experimental/fa-maskskip-batched-20261004` (1bceceb05, c7f5ac9ad).
- **Store builds** `kernels/builds/{gpu,cpu}-20261004-c7f5ac9ad`.
- **CPU harness** 141/141 bit-identical.
- `gpu_slot2.sh` was RUNNING while this was written: the exactness arms were done (rc=0), and kernel perf was in
  progress. Annotated as built, not ticked.

## INF-59 RoPE/YaRN: ADAPT (handoff rewritten)

- **Assessment** (`analysis/rope-ctx-ASSESSMENT.md`):
  - The target is Qwen3.8-27B at YaRN factor 2 (524K) as a dedicated np 1 MI210 mode, ≈ 48.9 GiB.
  - Two v10 traps:
    - the unconditional slot clamp, which needs `--override-kv … context_length` plus a mandatory
      `--yarn-orig-ctx 262144`;
    - Flash-Next's fused decode, which ignores YaRN.
  - 1M does not fit one MI210 at q8_0 KV.
- **The operator approved E0 + E1.** In flight:
  - the E0 runner and E1 runbook, plus research on hybrid-recurrent behaviour past 262k and the 1M-fit options
    (`/mnt/raid0/llm/tmp/yarn-e1-20261004/`);
  - DCA design and implementation, plus the Flash-Next fused-decode YaRN fix
    (`/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/`).
- **Handoff.** `yarn-context-extension-research.md` was rewritten (status, owner, `**Scratch**` field, traps, memory
  table). Filed: YARN-E0, E1, E2, DCA, FN-FIX, 1M, FN-0 and WIKI. The old QUEUED box is ticked as reactivated.

## Notes only

- **workspace-89's lineage rework.** ONE champion was kept, per the single-champion invariant. No action here.
- **workspace-89's vLLM/SGLang survey.** Its conclusions feed the KVU filings above (KVU-20, KVU-21 and the
  declines).

## Declines (explicit)

- **Raising Q38-T7's `max_tokens` so gsm8k/gpqa become gradable.** It departs from the recipe WORKLOAD; RESCORE
  leaves it to the plan owner. Not filed.
- **Step 7b scratch cleanup.** Skipped this wrap-up, under the hard rules: writes are limited to the lane worktree
  and the wrapup dir, and no processes. The GPU-block roots also held the only copies of the evidence until today's
  archive. KVU-19b's `gpu_slot2.sh` and the E0/DCA/prefill-budget subagents are still writing in their roots.
- **The KVU and INF-59 declines** are written in their handoffs.

## Files

| Repo | File | Change |
|---|---|---|
| root | `artifacts/gpu-block-27b-20261004/` | NEW. Durable copy of the GPU-block results, runners and analyses. |
| root | `handoffs/active/qwen38-27b-replace-qwen36.md` | Q38-T7 ticked. Q38-T7a and Q38-T7b filed. |
| root | `handoffs/active/kv-unified-stack-rollout.md` | KVU-16b annotated (PASS invalid). KVU-16b-1 and KVU-16f/g/h/i filed. KVU-16a, KVU-19 and KVU-19b annotated. KVU-20, KVU-19c and KVU-21 filed. 8 declines. |
| root | `handoffs/active/agentic-serving-harness-fixes.md` | UFH14-B4i ticked. UFH14-B4j and UFH14-B4g-1 filed. B4g annotated. |
| root | `handoffs/active/typed-decision-plane.md` | New coherence-judge section: TD-30 ticked (deployed). TD-30a–f and TD-31 filed. |
| root | `handoffs/active/cpu-decode-roofline-program.md` | CLS-RECT-1 annotated. CLS-RECT-1a filed (patch 04, workspace-ec). |
| root | `handoffs/active/vidya-belief-substrate-program.md` | VB-COHGATE-1, VB-SC75-CLS and VB-YARN-E1 filed. |
| root | `handoffs/active/yarn-context-extension-research.md` | Rewritten (ADAPT). 8 tasks filed. The QUEUED box is ticked as reactivated. |

# Wrap-up 3: KVU-19b GPU validation scored

## KVU-19b-1: store-build GPU validation scored (complete); fold commit 1 only

- **Run.** `gpu_slot2.sh` on store build `gpu-20261004-c7f5ac9ad` ran 04:44:49Z-05:05:18Z. Linkage PASS, and VRAM was
  the same before and after. A durable copy is in `artifacts/kvu19b-20261004/`; the source dir under
  `/mnt/raid0/llm/tmp` is not durable.
- **Correctness.** `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` passed 2978/2978, plus 110/110 on the unified cases
  with `MIN_KV=0` and 110/110 with `SEQ_ROWS=0`. All arms were within the CPU reference on 119 cases (worst nmse 9e-5,
  tolerance 5e-4). seqoff == alloff == k19a bit-identical.
- **Commit 1 (`1bceceb05`, vec routing for one row per sequence) is a WIN.** At 4 seqs × 81920 own (n_kv 327680) it
  takes 5.53 ms, against 9.23 ms for 19a, 8.77 ms for base and 5.26 ms for the per-sequence streams reference.
  Batched-bench `-kvu` S_TG is 522.4, against 434.6 for 19a and 529.3 for base `-no-kvu`. p3batch at draft=1
  (round 3) gives 449 tok/s, against 396 for 19a and 518 for no-kvu, so a gap remains.
- **Commit 2 (`c7f5ac9ad`, WMMA sequence tiles) is MIXED.**
  - Aligned 4×8: 11.86 vs 10.36 ms, 14% slower.
  - Uneven [1,8,8,8]: 11.90 vs 13.64 ms, 13% faster.
  - It breaks the design's bit-identity claim: skip on vs off differs on 6 cases (110/111/118/119/126/127; ndiff 384,
    nmse ≤ 8.3e-10).
  - Its p3batch draft=8 rows are within noise.
- **Actions.**
  - Recommendation sent to workspace-89: fold commit 1 only.
  - Rework of commit 2 dispatched: root-cause the exactness break, plan tiles only where they straddle sequences, add
    a separate `GGML_CUDA_FA_SEQ_TILES` knob, and write `gpu_slot3.sh`.
- **Handoff.**
  - KVU-19b-1 ticked.
  - Filed KVU-19b-fold-c1 (workspace-89), KVU-19b-rework-c2 and KVU-19b-gap.
  - KVU-19 annotated.
  - The parent KVU-19b stays open until the commit-2 rework is folded or dropped.

## Process lesson: unlocked CPU work inside a peer's held window (incident)

- **What happened.** workspace-89 held `cpu-window2-20261004` (q0-q3, 04:40-05:00Z). Inside it, three workspace-ec
  workloads ran without a region claim:
  - a dev llama-server pinned to 160-183, the SMT siblings of 64-87;
  - a `cmake -j24`;
  - the KVU-19b slot's own host side, on `taskset -c 160-183`.
- **Impact.** The window's preflight measured about 2,400% CPU and refused steps 2-4, so the MXFP4/EXL3/Q38FN
  measurements were lost.
- **Remedy.** Every subagent brief requires
  `region-lock run --cpu-list 0-95 --role build --tag <t> -- <cmd>` for builds, servers and tests.
- **The rule was only partly written.**
  - `OPERATING_CONSTRAINTS.md:124` covers self-launched inference only.
  - The fan-out section's brief requirements say nothing about a CPU lock.
  - The SMT-sibling point is stated nowhere.
  - PREPARED, not applied:
    - `/mnt/raid0/llm/tmp/wrapup-ec-kvu19b/oc-region-lock.patch`, 6 lines in § Parallel Subagent Fan-Out
      (`git apply --check` rc=0);
    - `/mnt/raid0/llm/tmp/wrapup-ec-kvu19b/incident-draft.md`, INC-20261004-subagent-unlocked-cpu-in-held-window, to
      append at the end of `docs/reference/agent-config/INCIDENT_LOG.md`.
- **A lock-layer gap was found and filed.** `instance_topology.parse_cpu_list` drops CPUs 96-191. So
  `region-lock --cpu-list 160-183` maps to no region and could not have conflicted with the window anyway. Filed as
  REGION-SIBLING-1 in `shape-keyed-contention-gating.md`.
- **Caveat on the slot2 numbers.** They were taken on that contended host, so this caveat now rides KVU-19b-1 and
  KVU-19b-gap.

## v11 FA-path audit actionables filed (coordinator addendum)

- **Source.** workspace-89's read-only audit, `/mnt/raid0/llm/tmp/v11-fa-path-audit-20261004/REPORT.md`. The durable
  copy is in `artifacts/v11-fa-path-audit-20261004/`, together with the register-audit scripts and the v10 FA register
  table (1704 kernels), which existed only in a session `/tmp` scratchpad.
- **The core finding.** Upstream #26046 removes rocWMMA FA. On gfx90a at D=256 / GQA 6:
  - 3-32 rows go to TILE, which uses no matrix cores. That covers 4×1 batched decode and 1-3-slot DFlash2 verify.
  - Above 32 rows, work goes to MMA `<256,256,32,2>`, which spills 314 VGPRs under ROCm 6.2.
  - The DF2-9 all-NaN record is the ROCWMMA=OFF path.
  - It agrees with KVU-19b-1: fold 19a plus 19b commit 1 now, and hold commit 2.
- **Filed in `kv-unified-stack-rollout.md` section C, after KVU-21 (owner workspace-ec):**
  - V11-FA-1: ROCWMMA OFF/ON A/B plus an arm with #27870 and #28576, gated on DF2-9;
  - V11-FA-2: the DF2-9 root cause, a standalone reproducer, and a large-magnitude FA case;
  - V11-FA-3: an ncols cap for D=256 prefill;
  - V11-FA-4: carry rocWMMA as an in-binary arm, keeping the `99f3fffd6` guard.
- **Folded in rather than filed separately.** The audit's other actionables went into those four tasks:
  - the large-|V| test case and TILE `ncols2=2` run-to-run exactness;
  - the gfx90a TILE/MMA crossover retune;
  - the `99f3fffd6` guard;
  - the `GGML_CUDA_FA_PREFER_WMMA` knob shape.
- **Cross-references.** The prefix-fork handoff (RTG-58, `kv-prefix-fork-and-paged-attention.md`, landed on main as
  `4aab28c8` during this wrap-up) gates its P4 `kv_rows` phase on this audit. KPF-40 is annotated with the durable
  path, and the V11-FA block cites KPF-40..42 and KVU-21.

## Declines (explicit, wrap-up 3)

- **The higher no-kvu S_TG on the 19b binary (552.7 vs 529.3/529.6 for base and 19a).** It is a single sample. With
  `kv_unified=false` the hint is 0, so the code path is the 19a path: this is noise, not a finding. Not filed.
- **The S_PP jump at kvu (base 13216 → about 20600 on every patched arm).** This is KVU-19a's skip on prompt-chunk
  tiles, which KVU-19a and its fold already cover. Not filed again.
- **The vec routing excludes bf16 KV and head dims other than 128/256.** Production GPU KV is q8_0, and gemma-3-1b /
  the 27B are D=256. Not filed until a GPU-served unified-KV model falls outside the routed set.
- **Updating `CURRENT-CAMPAIGN.md`'s stale KVU-19a lines.** That is the coordinator's posture file, not a wrap-up
  surface. The suggested text is in the prepared INDEX_ROWS.md.

## Files (wrap-up 3)

| Repo | File | Change |
|---|---|---|
| root | `artifacts/kvu19b-20261004/` | NEW. Durable copy of FOLD/DESIGN, `gpu_slot2.sh` and the slot2 results, plus a README. |
| root | `handoffs/active/kv-unified-stack-rollout.md` | KVU-19b-1 ticked; KVU-19b-fold-c1, -rework-c2 and -gap filed; KVU-19b and KVU-19 annotated; V11-FA-1..4 filed in section C. |
| root | `handoffs/active/vidya-belief-substrate-program.md` | VB-FA-MASKSKIP-b filed (write side for the slot2 records). |
| root | `handoffs/active/shape-keyed-contention-gating.md` | REGION-SIBLING-1 filed. |
| root | `artifacts/v11-fa-path-audit-20261004/` | NEW. Durable copy of the v11 FA-path audit, register-audit scripts and the v10 table, plus a README. |
| root | `handoffs/active/kv-prefix-fork-and-paged-attention.md` | KPF-40 annotated (audit complete; durable path; V11-FA ids). |
| root | `progress/2026-10/2026-10-04-workspace-ec.md` | This entry. |

Prepared, not applied (`/mnt/raid0/llm/tmp/wrapup-ec-kvu19b/`): `INDEX_ROWS.md` (RTG-57 cell, adapter source-table
row), `oc-region-lock.patch` and `incident-draft.md`.

# Wrap-up 4 (07:00-08:05Z): champion fold LIVE, KVU-16h attributed, CPU FA fp16 VKQ fixed, V11-FA prep

## Champion fold: KVU-19a + KVU-19b commit 1 are in the ONE champion (complete; receipt pending)

- **Ref move.** `ak/champion/llama-cpp-ffc1bac82eec` advanced `90c12df42` → `1bceceb05`, locally and on `fork`, by the
  guarded compare-and-swap in `advance_ref.sh`. It is a fast-forward (`ac97e305a`, `a0d0ae238`, `1bceceb05`, with the
  original shas kept, so the builds are the commits the evidence was made on). `ak-loop-tree` was refreshed clean, and
  the frozen tree stayed on `production-consolidated-v10`. Commit 2 (`c7f5ac9ad`) is out: `plan_seq_tiles` is absent
  from strings and `nm`. Builds: `kernels/builds/{gpu,cpu}-20261004-1bceceb05` (build 10311, champion recipes, linkage
  PASS).
- **Gates.** G0 feature preservation passed on source, GPU and CPU with 0 losses; G0 is vacuous for HIP kernels.
  - CPU: harness v1 86/86 and v2 141/141 bit-identical; `test-backend-ops -b CPU` 5178/5178.
  - **GPU slot `slot-20261004T073429Z`: VERDICT PASS.**
    - Exactness E1-E8 all pass; the worst nmse against the CPU reference is 8.97e-05.
    - 27B DFlash2 smoke: champion, candidate skip-off and candidate skip-on outputs are byte-identical. All three
      decoded 74 tokens at 36.054% acceptance.
    - `test-backend-ops` ROCm0: 2949/2949, plus 81/81 × 3.
    - perf2: 4×1 kvu took 1084 vs 1733 µs at 16k own and 5514 vs 9168 µs at 80k own. Single-sequence decode with
      +114,688 foreign cells took 284 vs 2335 µs. The 0-foreign rows are within noise.
- **Standing receipt: PENDING.** `standing_receipt.sh` runs a single arm, per the operator ruling. The baseline is the
  FOLD-2 G5 `ef81196d5` samples from 2026-09-08 (median 31.301 tok/s), unpaired, with the BIOS-change caveat. It started
  ~07:59Z and was still waiting on the q0-q3 region lock at 08:07Z. Nothing is published yet. Tracked as
  KVU-19b-fold-c1-receipt.
- **Durable copy:** `artifacts/champion-fold-kvu19-20261004/` holds `FOLD-CANDIDATE.md`, the slot summary and
  per-check files, the G0 JSONs, CPU exactness, linkage/strings, all scripts and `SOURCES.sha256`. The two ~1 MB
  `test-backend-ops` logs are kept as verdict tails plus hashes.
- **Ledger:** ak-ds41-main (workspace-89's lane) ledgered the fold and updated the champion header in
  `autokernel-champion-aggregate.md` (root `3cef9579`, landed during this wrap-up). The P3 B 27B re-measurement is
  split out as KVU-19b-fold-c1-p3.
- **Found at wrap-up:** KPF-17a's shared-trunk FA test patch was not applied at the fold, and it does not apply to
  `1bceceb05` (`test-backend-ops.cpp:8584`; it was cut against the commit-2 branch). KPF-17a is annotated to re-cut
  the patch and apply it at the next fold.

## KVU-16h: :8083 VRAM growth attributed (attribution complete; fix built, GPU confirm pending)

- **Replay** (`kvu16h-vram-20261004/results/20261004T063830Z`): +1.42 GiB, then a plateau. The largest share is the
  legacy pool (0.58 target + 0.50 draft GiB, cuBLAS F16 dequant buffers). `-ub 512` grew +0.79 GiB.
- **Mechanism.** The HIP-graph `mmvq_q8_1_graph_cache` is a LOCAL AutoKernel keep (`dd161d519`, `c0d42d81c`,
  `8a3049beb`). It holds legacy-pool buffers across graph captures. Per-request `speculative.n_max: 0` traffic
  alternates graph shapes, so every event allocates a fresh set of dequant buffers. 0.29 GiB per event fits all four
  datasets.
- **Latent hazard:** a use-after-free across graph captures (the pool can free a buffer a captured graph still
  references).
- **Fix:** `experimental/mmvq-graph-cache-pool-20261004` @ `656c9a66b`, a private per-context arena on the folded
  champion. Store build `gpu-20261004-656c9a66b`.
- **Filed:** KVU-16h-a (attribution, ticked), KVU-16h-confirm (row 4c), KVU-16h-fold, and KVU-16h-runner (no-draft
  arms get their own server launch; workspace-89's suggestion). The +8.08 GiB KVU-16i term stays until row 4c
  confirms.
- **Durable copy:** `artifacts/kvu16h-vram-20261004/`.

## CPU FA fp16 VKQ overflow (fix built; fold and A/B filed)

- **Defect.** `ggml-cpu/ops.cpp` `..._one_chunk` accumulates VKQ in FP16 for F16 V. Diffuse attention over 2048 cells
  with a same-sign channel of 32 overflows FP16.
- **Production is not at risk today:** architect :8074 `acc_peak` ≤ 238, bounded by the 2048-cell indexer. The dense
  F16 MTP draft head could lose acceptance at very long context.
- **Fix:** `experimental/cpu-fa-fp32-vkq-20261004` @ `2ad8bff36` uses a fused FP32 accumulation.
  - Harness: 84/84 with the fix vs 71/84 at base (10 non-finite, 3 mismatch).
  - FA-op cost is at parity.
  - The branch was only local; it was **pushed to `fork` at this wrap-up**. A trial merge onto `1bceceb05` is clean.
- **Upstream** is unfixed for ggml-cpu (#28576 fixed only the MFMA analog).
- **Filed** in the V11-FA section: CPU-FA-VKQ-0 (ticked), -1 (fold into champion/v11), -2 (decode A/B), -3 (optional
  MTP acceptance at >64k on the architect) and -4 (upstream report).
- **Durable copy:** `artifacts/cpu-fa-fp32-vkq-20261004/`.

## V11-FA prep (complete; slot not yet run)

- **Arms built.** Five arms are built in `/mnt/raid0/llm/tmp/v11-fa-ab-20261004/`: A (ON), B (OFF), C (+#27870
  +#28576), D (CDNA D=256 tuning) and M (upstream master). `gpu_slot_v11fa.sh` is ready.
- **Findings.**
  - The picks are neutral on the ROCWMMA-ON route: the ON champion launches no MMA kernel for production shapes.
  - DF2-9 sits on MMA `<256,256,8,8>` at 60-340 tokens; the audit's `<256,256,32,2>` is corrected in V11-FA-3.
  - ggml CPU reproduces the fp16-overflow mechanism.
  - The drafter's 9-row D=128 block moves from WMMA to MMA in v11.
- **Handoff updates.** V11-FA-1..4 are annotated.
- **Durable copy:** `artifacts/v11-fa-ab-20261004/`.

## Other advances

- **KVU-19b-rework-c2 v2** (`experimental/fa-maskskip-batched-v2-20261004` @ `54df2c030`): steps 1-3 are done and
  step 4 is pending.
  - The exactness root cause is a compiler rounding difference between WMMA tile columns (`v_mul_f32` +
    `v_cvt_f16_f32` vs `v_fma_mixlo_f16`). Fixed by keeping rows in their plain tile column.
  - Aligned-verify gate: added.
  - Knob split: `GGML_CUDA_FA_SEQ_VEC` / `GGML_CUDA_FA_SEQ_TILES`.
  - CPU v2 harness: 141/141.
  - `gpu_slot3.sh` is ready.
- **KVU-16g prefill budget.** Rebased onto the fold as `65d48a7a0` (`experimental/prefill-budget-on-fold-20261004`),
  with store builds `{gpu,cpu}-20261004-65d48a7a0`. `gpu_slot.sh` is ready for row 5c; KVU-16g-1 is filed.
- **:8083 batch package `STACKCHG-8083BATCH-20261004`** (`-b 512 -ub 512` + `--no-cache-idle-slots`): VALID and
  greenlit by workspace-ec. It awaits the operator's terminal signature and applies at the :8083 restore after YaRN
  E1. KVU-16f and UFH14-B4j are annotated.
- **RTG-58.** P1's handoff edit is on main (`b22ff171`). P2 branch B got Fable ACK-with-fixes (D1-D6); the v2
  re-review is in progress. KPF-27b-ack is annotated.
- **REGION-SIBLING-1.** The fix is on epyc-orchestrator `fix/region-lock-smt-siblings-ec` @ `4ae008a8` (CLI folds SMT
  siblings, library default unchanged, 816 tests). Merge and deploy AWAIT OPERATOR APPROVAL, because the classifier
  blocked the merge.
  - The task was already filed on origin/main (`shape-keyed-contention-gating.md`). The "missing" reading came from
    the stale shared clone. It is annotated, not re-filed.
- **Promotion process gap.** kernel-promotion SKILL step 9 now carries the champion's standing forward as the
  production baseline (`8c0fe68e`, on main). workspace-89 is implementing `production-baseline.<sha>.json` in
  `production.py`.

## Process lessons (incident recurrence)

INC-20261004-subagent-unlocked-cpu-in-held-window gained a "Recurrence, same day" paragraph. workspace-ec subagents
preempted CPU windows three more times: a KPF smoke run, a DCA perplexity run and a `gitnexus` re-index. Lessons:
- Quadrant claims must be pinned and no wider than the quadrant's threads.
- Inference takes `--role bench`.
- The region lock is non-FIFO, so waiters can starve.
- Lock-free tooling is load too.

## Declines (explicit, wrap-up 4)

- **A handoff task for `production-baseline.<sha>.json`.** workspace-89 is implementing it now in its own lane (the
  production writer is research `production.py`), and the skill text is already on main. Filing it would create a
  second owner. Not filed.
- **Editing the fold-table ledger in `autokernel-champion-aggregate.md`.** That file is workspace-89's surface, and
  ak-ds41-main ledgered the fold there itself (`3cef9579`) while this wrap-up ran. Nothing is left to hand over.
- **Folding #27870/#28576 into the champion now.** `PICKS_ON_ROUTE.md` shows the change is behaviour-neutral on the
  ON route. Doing it would only pre-stage v11 code, and V11-FA-1's C arm already measures the picks where they
  matter. Not filed separately.
- **A separate task to merge REGION-SIBLING-1.** The only unblock is the operator's approval. That goes in the
  operator decision queue (prepared row), and the handoff task already carries the done-when.

## Files (wrap-up 4)

| Repo | File | Change |
|---|---|---|
| root | `artifacts/champion-fold-kvu19-20261004/` | NEW. Fold record, GPU slot results, G0, CPU exactness, scripts, hashes. |
| root | `artifacts/kvu16h-vram-20261004/` | NEW. Replay summary, runner and analysis scripts, fix commit text. |
| root | `artifacts/cpu-fa-fp32-vkq-20261004/` | NEW. CPU FA harness outputs, model probe, fix commit text. |
| root | `artifacts/v11-fa-ab-20261004/` | NEW. `PICKS_ON_ROUTE.md`, `NCOLS_CAP.md`, upstream draft, slot runner, DF2-9 recipe. |
| root | `handoffs/active/kv-unified-stack-rollout.md` | Ticked KVU-19b-fold-c1, KVU-16h-a and CPU-FA-VKQ-0. Filed fold-c1-p3, fold-c1-receipt, KVU-16h-confirm/-fold/-runner, KVU-16g-1 and CPU-FA-VKQ-1..4. Annotated KVU-19, KVU-16f/g/h/i, rework-c2 and V11-FA-1..4. |
| root | `handoffs/active/kv-prefix-fork-and-paged-attention.md` | KPF-17a (patch does not apply to the folded champion) and KPF-27b-ack annotated. |
| root | `handoffs/active/agentic-serving-harness-fixes.md` | UFH14-B4j annotated (package awaiting signature). |
| root | `handoffs/active/shape-keyed-contention-gating.md` | REGION-SIBLING-1 annotated (fix branch, awaits operator). |
| root | `handoffs/active/vidya-belief-substrate-program.md` | VB-FA-MASKSKIP-c, VB-KVU16H and VB-CPU-FA-VKQ filed. |
| root | `docs/reference/agent-config/INCIDENT_LOG.md` | Recurrence paragraph. |
| llama.cpp fork | `experimental/cpu-fa-fp32-vkq-20261004` | Pushed (`2ad8bff36`); it was local-only. |

Prepared, not applied (`/mnt/raid0/llm/tmp/wrapup-ec-fold/INDEX_ROWS.md`):
- the RTG-57 and RTG-58 Next-action cells;
- two operator-queue rows (STACKCHG-8083BATCH signature, REGION-SIBLING-1 merge);
- three adapter source-table rows.

# Wrap-up 5 (~10:30-16:00Z): KVU-16h confirmed and folded, champion Y, DF2-9 root-caused, v11 FA decided

Per-task wrap-up, run by a subagent for workspace-ec. No index pruning and no wiki sweep (operator cadence). Index
rows and operator-queue rows are PREPARED in `/mnt/raid0/llm/tmp/wrapup-ec-pm/INDEX_ROWS.md`; none were applied.

## KVU-16h: confirmed and fixed (complete)

- Run `fuc-20261004T110509Z`, durable copy `artifacts/kvu16h-vram-20261004/results/fuc-20261004T110509Z/`.
- Arm A (v10): +5.83 GiB over 21 `n_max: 0` → prefill events (0.28 GiB per event); control +0.06.
- Arm B (HIP graphs off): +0.05 GiB, but no-draft decode −5.6%.
- Arm C (arena fix `656c9a66b`): +0.057 GiB; decode +1.0% no-draft, +4.9% drafted.
- The fix is in champion Y (`61bdb185c`).
- Ticked: KVU-16h, KVU-16h-confirm, KVU-16h-fold.
- KVU-16i: the term drops to the bounded ~1.42 GiB once a v11 carrying `656c9a66b` is promoted (KVU-16i-v11 filed).
  Until then v10 production keeps +8.08 GiB, under the rule "no per-request `n_max: 0` against :8083".

## Champion standing

- Paired v10 vs `1bceceb05` receipt: 14 launches, tg +0.61% [−0.20, +1.41], pp −0.21%, identity equal. Ingested as
  the v10 `serving_probe` baseline; KVU-19b-fold-c1-receipt ticked.
- The raw run dir was lost to a subagent's glob `rm` (INC-20261004-glob-rm-deleted-receipt-evidence, recorded).
  Surviving evidence: `artifacts/champion-fold-kvu19-20261004/paired-receipt-20261004T094057Z/`.
- Candidate X `cf23279ae`, paired: tg −0.23% [−0.57, +0.23]; FA `test-backend-ops` 2949/2949.
- Operator chose Y `61bdb185c`: DS41 serving-gated keeps + `656c9a66b`, no IQ4_NL allowlist.
  - Y champion-only receipt: tg +0.35%; pp +18.2% is flagged as unpaired drift.
- workspace-89 advanced the champion `1bceceb05` → `61bdb185c`.
- Next fold: Yfa `9a3f1392a` (+ CPU FA hybrid v2), gates passed.
- X and Y run dirs copied durably to `artifacts/champion-fold-kvu19-20261004/receipt-ab/`, with `SOURCES.sha256`.

## v11 FA A/B (V11-FA-1/2 complete; -3 and -4 updated)

Slots: `slot-20261004T113710Z` (merged) and `slot-20261004T150551Z`. Durable copies are in
`artifacts/v11-fa-ab-20261004/slot-*/` (`summary.txt`, `perf_table.tsv`, `det/`, `tbo/`, probe summaries; the 5.7 MB
`*.nodes.tsv` dumps were left in scratch).

**DF2-9 is root-caused: the pre-#27870 MMA divergent-barrier race.**

| arm | model probe | `test-backend-ops` FA |
|---|---|---|
| B (ROCWMMA OFF) | FAIL, 6/10 runs (first bad `FLASH_ATTN_EXT` at layer 3) | 598/640 |
| E (B + #27870) | PASS | 640/640 |
| C | PASS | 640/640 |
| A | PASS | — |

- #27870 is a mandatory v11 carry (V11-FA-6 filed). #28576 is not needed for DF2-9.
- Perf on the v11 route, against rocWMMA:

  | band | ratio vs rocWMMA |
  |---|---|
  | 4×1 decode | ×0.60 |
  | 9-27 rows | ×1.14-1.24 (TILE slower) |
  | 36 rows | ×0.5-0.9 |
  | prefill-512, master | ×0.84-0.90 |
  | prefill-512, C | ×1.09-1.16 |
  | drafter 9-row D=128 | ×1.7-1.9 slower |

- Patches D and D9 do not help, and the ncols cap gives no gain (V11-FA-3 updated, left open for the register
  re-check on master's code object).
- V11-FA-4 (carry rocWMMA for 9-32 rows) is justified.
- The upstream issue is perf-only and WARRANTED by rule, as a draft only (V11-FA-5 filed). The NaN is not an
  upstream issue, since #27870 already fixes it.

## KVU-19b rework v2 (`54df2c030`), slot3-20261004T115000Z

- All five bit-identity criteria PASS.
- Perf: 4×9 ×0.708; uneven ×0.88-0.90; aligned ×0.98.
- `test-backend-ops` 118/118 ×2.
- Two calibration FAILs are under triage: the hs=128 bound (22 cases at nmse 7.79e-08), and case 152 vs the CPU
  reference, which fails on every arm, k19a included. Filed as KVU-19b-rework-c2-cal; the parent stays open.
- Durable copy: `artifacts/fa-maskskip-batched-20261004/slot3-20261004T115000Z/`.

## FA-INT64-OFFSET GPU slot (`gpu-slot-20261004T145625Z`): PASS

- Fixed build: 4/4 `mask_ne0` cases. Champion: 1/4 (3 FAIL, ERR 0.03-0.59).
- Full `FLASH_ATTN_EXT` suite on the fixed build: 2872/2872. 119/119 bit-identical to the champion on existing cases.
- YARN-FA-INT64 added as done; the fold and an upstream draft are filed.

## DCA

Perplexity on Qwen2.5-0.5B at 32K-64K (lower is better):

| arm | GPU | CPU |
|---|---|---|
| plain 64K | 14.39 | 13.63 |
| YaRN | — | 12.63 |
| DCA | 13.07 | 12.46 |
| DCA + T | 12.96 | — |

- DCA beats raw extrapolation on both devices; DCA vs YaRN is within the one-window spread.
- The GPU-vs-CPU offset is unexplained (YARN-DCA-XDEV filed). YARN-DCA-E1 (the needle A/B on the 27B) is filed.

## Other advances

- **CPU FA fp16-VKQ:** hybrid v2 `a99e5330a` is folded into Yfa. The end-to-end bench is running, so it is marked
  PENDING (CPU-FA-VKQ-1 and -2 annotated).
- **YARN-FN-FIX ticked:** `5bfdcd18c` plus `6c126e975`, with the fused-rope test green. YARN-FN-FIX-fold filed.
- **Flash-Next fused decode:** the divergence and double-free repro is committed (`45d8f2937`). Filed as FD-DIV-1 in
  `cpu-fused-decoder-blocks.md`, owner TBD (the Flash-Next owner). Keep `GGML_FUSED_DECODE_OFF=1`.
- **G1 round-2 review:**
  - Manual windows: ACK-with-fixes. AK-requested windows: NACK (F4/F5/F6).
  - orch `4b871cc5` is in the shared checkout (operator-approved). Device-busy `6ce26fc9` is not (operator approval
    needed; OP row prepared).
  - The watchdog is not armed yet: it needs host cron after today's restore (AKX-ALL-15a, OP row prepared).
  - AKX-ALL-15b and -15c filed.
- **gpu-quiet lock live** (orch `c5dc4ae5`). Three lessons went to the incident log as a same-day recurrence, and to a
  PREPARED OPERATING_CONSTRAINTS patch: `artifacts/operator/oc-gpu-quiet-lessons-20261004.patch`
  (`git apply --check` clean).
- **Prefill budget (KVU-16g):** rebased on Y as `98c0ce12a`. The slot refusal was a `pipefail` false alarm, now fixed.
  The GPU A/B is next in the queue.
- **Operator decisions today:**
  - (a) restore :8083 only after YaRN E1;
  - (b) champion = Y;
  - (c) measure v10 once on DFlash2 (done, paired);
  - (d) keep the shared checkout at `c5dc4ae5` and approve `4b871cc5`;
  - (e) the AK GPU lane's first job is multi-row dequant-GEMV (AKX-ALL-15c).
- **Belief kernel:** the KVU-16h adapter row status was refreshed. New source rows: the v11 FA A/B slot, the DF2-9
  model probe, and the DCA / FA-INT64 slots. Tasks VB-V11FA and VB-LONGCTX-KERNEL filed.

## Checkbox ledger (wrap-up 5)

- **Flipped or added as done (8):** KVU-16h, KVU-16h-confirm, KVU-16h-fold, KVU-19b-fold-c1-receipt, V11-FA-1,
  V11-FA-2, YARN-FN-FIX, YARN-FA-INT64.
- **Filed (16):** KVU-16i-v11, KVU-19b-rework-c2-cal, V11-FA-2b, V11-FA-5, V11-FA-6, YARN-DCA-E1, YARN-DCA-XDEV,
  YARN-FA-INT64-fold, YARN-FA-INT64-up, YARN-FN-FIX-fold, FD-DIV-1, AKX-ALL-15a, AKX-ALL-15b, AKX-ALL-15c, VB-V11FA,
  VB-LONGCTX-KERNEL.

## Declines (explicit, wrap-up 5)

- **Re-running the lost paired receipt.** The verdict stands on the ingested loop-memory records. The champion has
  since moved to Y, with its own receipts, so a re-run would spend a GPU window without informing any decision.
- **An upstream issue for the DF2-9 NaN.** #27870 already fixes it upstream.
- **A separate #28576 carry task.** DF2-9 does not need it, and a master-based v11 contains it anyway.
- **A separate ncols-cap decline task.** It stays inside V11-FA-3, which closes on the register re-check.
- **Re-running the CPU `dca_t` arm.** The GPU slot measured DCA+T, and cross-device comparison waits on YARN-DCA-XDEV.
- **A new task for the "no `n_max: 0` against :8083" rule.** The existing KVU-16h-runner enforces it for runners,
  and KVU-16i records it.
- **A handoff task for the `6ce26fc9` checkout update.** It is an operator decision, so it goes to the operator queue
  (prepared row).

## Files (wrap-up 5)

| Repo | File | Change |
|---|---|---|
| root | `handoffs/active/kv-unified-stack-rollout.md` | KVU-16h ×3, fold-c1-receipt, V11-FA-1/2 ticked; -3/-4, KVU-16g/16i, rework-c2, CPU-FA-VKQ-1/2 annotated; 6 tasks filed |
| root | `handoffs/active/yarn-context-extension-research.md` | YARN-FN-FIX ticked; YARN-FA-INT64 added as done; DCA results; 5 tasks filed |
| root | `handoffs/active/cpu-fused-decoder-blocks.md` | FD-DIV-1 filed |
| root | `handoffs/active/autokernel-all-devices-all-dimensions.md` | AKX-ALL-15 G1 review state; -15a/b/c filed |
| root | `handoffs/active/dflash2-block-drafter-experimental-build.md` | DF2-9 root cause noted |
| root | `handoffs/active/vidya-belief-substrate-program.md` | VB-V11FA, VB-LONGCTX-KERNEL filed; VB-KVU16H note |
| root | `scripts/vidya/adapters/README.md` | 3 source rows added; KVU-16h row status |
| root | `docs/reference/agent-config/INCIDENT_LOG.md` | INC-20261004-glob-rm-deleted-receipt-evidence; second same-day recurrence (gpu-quiet) |
| root | `artifacts/operator/oc-gpu-quiet-lessons-20261004.patch` | NEW, PREPARED OPERATING_CONSTRAINTS patch (not applied) |
| root | `artifacts/champion-fold-kvu19-20261004/receipt-ab/` | NEW: X and Y run dirs + `SOURCES.sha256` |
| root | `artifacts/v11-fa-ab-20261004/slot-20261004T{113710,150551}Z/` | NEW: slot summaries, perf tables, probes |
| root | `artifacts/kvu16h-vram-20261004/results/fuc-20261004T110509Z/` | NEW: row-4c result |
| root | `artifacts/fa-maskskip-batched-20261004/` | NEW: KVU-19b slot3 |
| root | `artifacts/dca-yarn-kernel-20261004/` | NEW: NOTES, DCA slot, FA-INT64 slot, fused repro log |
