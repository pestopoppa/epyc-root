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
