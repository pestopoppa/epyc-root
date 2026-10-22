# 2026-10-22 workspace-f8

## Overnight 2026-10-21/22

Results recorded in the handoffs (evidence under `/mnt/raid0/llm/tmp/`):

- **PB-HOL-1 budget-on arms** (`gpu-serving-tie-in-program.md`, ticked): A-on 3593 ms, B-on 83352 ms (23.2x), B-on-nodec 63980 ms vs off arms A 3217.5 / B 70932 (22.05x). The prefill budget does not relieve slot-order HOL (confounded by `-b`/`-ub` 512 -> 2048). M4 ordering fix filed. DI-126 and KVU-16g-2 notes updated.
- **PB-QCOST-1** re-validation: frozen model FAIL (held-out MAPE 12.84% n=1, 26.32% n=4, biased low); refit passes (2.4%, 3.83%). Indicative only: ran beside KVU-12 np8 CPU timing with host threads 184-191 contended. Uncontended confirmation filed.
- **KPF-18 item 3 (G1 repeats, ended rc1=0 rc2=0)**: cumulative over all six item-3 records, fork vs no-fork token-identical 17/21, A/A 20/21, min prefix 43 both. Fork divergences: group 0 at token 43 (once), group 3 at token 161 (3 of 3 passes); A/A divergence: group 0 at token 43 (once). Observation grade; group-3 check filed.
- **KVU-12.4 / 12.5 redo**: np4 L64k ABA NO_DIFFERENCE (PROPOSED-until-ratified; unified -22.78% decode sum against a 12.48% anchor floor, weak). np8 L64k pair CONFOUNDED (unified gpu_busy_frac 0.47 vs split 0.0). s4 hit its 12,000 s cap (rc 125). Bank build and mtp-off np8 done; pool-full step skipped for time.
- Operator decisions of 2026-10-21 recorded: DP-1 = (a), DP-4 = (A) (queue rows removed), VB-AP-SPINUP-AP3-SCOPED added; SEC-SECRETS-1 D9 ack, SEC-ART-3 allowlist, SEC-EXEC-6 revoke (operator task added), AKX-AUTO-6 owner = workspace-f8.

## Morning wrap-up 2026-10-22 (WRAPUP_AGENT_ID=workspace-f8)

### DS41-1017 noise floor: COMPLETE (compare still running)

- Stage-3 baseline from 06:30Z (`gate_1017.py`, `/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/`): floor **2.862%**, unit = process, n = 24 A/A pairs, gates k = 5-pair compares, interval 1.974-5.757%, 7394 s, build `cpu-20261020-dd3d9721c`, `matched_process_v2`. Floor file `aa/floor-store/serving-floor.ds41-1017-mxfp4-cpu-t48-targetonly.requests-e50732d9ce365259d5bb95fe31e36995f98bcd0986dc0e48d489f99390e42f58.matched_process_v2.pairs-5.json`.
- Sensitivity check (`FLOOR_SENSITIVITY.md`): STANDS as decision-grade. Every exclusion variant lowers the floor (2.33-2.55%), tagged launches show no systematic shift, PREDECLARED forbids post-hoc exclusion. Annotation, verbatim: "launch 1 is a cold-start outlier (10.67 tok/s, before any disclosed activity); floor without it is 2.445%; launch 39 (14.85) dips inside a disclosed-activity window; post-hoc exclusion forbidden by PREDECLARED".
- Valid ONLY for build `dd3d9721c` (pre-W5.1a numerics epoch). The post-C2-CAS, post-W5.1a recalibration on the new anchor stays a separate open box (`DS41-W5.1a-floor`, FILLERS row `ds41-1017-ak-floor-postcas`, owner workspace-58).
- The champion-vs-C2 (`49550eda5`) 5-pair compare was still RUNNING at 08:41Z (2 of 10 launches in `cmp/launches-compare.jsonl`; no `RUN_RECORD.json`), so DS41-W5b, CH-20.1 (i) and VB-DS41-1017-BASELINE-WIRE stay open; only the floor sub-box is ticked.
- Disclosure: an f8 subagent ran pytest (49 tests) and `prior_check.py` inside stage-3's quiet baseline (~08:10-08:50Z). Logged in `HOST_ACTIVITY_DISCLOSURES.md`; the sensitivity check cleared it (tagged launches 38-48 within ~1% of untagged on average, no systematic shift).

### Operator rule 2026-10-22 (relayed by workspace-58)

Every session: (1) keep zero-token watchers on its own end/FAILED flags; (2) on a failure or a >1.5x overrun: why, then fix, then re-queue, unasked; (3) `ram_admit.sh <peak_host_GiB> [ds41]` before any model load (peak host RAM = private + file-mapped weights; DS41-1017 server-class = 739 GiB); (4) a wrap-up at each task boundary. Already canonical in `docs/guides/agent-workflows/compute-fillers.md` (*Owner duties*, *RAM admission*), so no agents/shared edit was made (no clearly fitting new section).

### D4 overrun root cause and KVU-12.5 decline

- Workspace-58's `/mnt/raid0/llm/tmp/d4-why-20261022/REPORT.md`: the driver's estimate model was wrong (128k prefill ~65 tok/s vs 195 modelled; shared-batch decode 0.08-0.12 tok/s per stream), so k5_s4's 12,000 s cap was unreachable. GPU contention refuted.
- Re-runs of s4 and the 128k bank + poolfull were DECLINED by f8: CPU timing of a 35B frontdoor that is moving to GPU, so no live decision needs it. Recorded on the KVU-12.5 tasks in `kv-unified-stack-rollout.md` (original KVU-12.5 box ticked as declined; the `KVU-12.5 re-run` box narrowed to part (a), the np8 L64k pair).
- Estimate model fixed on research `f8/kvu12-arms` `8e532d23f`, re-costed: KVU-12.1 8k ~2.1 h on one quarter / 0.6 h full host; the 32k pair +3.5 h / 0.9 h.

### Other state

- Job 67 launcher went to v5 (RAM-gated at 739 GiB + DS41 single-server check), then job 67 was CANCELLED 08:45Z by operator directive (all DS41-1017 tests except the noise floor disregarded until AutoKernel kernel work); its q0-q2 10:45-14:15Z slot goes to f8 test lanes and fillers.
- Operator decision 2026-10-22: serving noise floors live in the MASTER model registry (not the separate floor-registry store); the floor-registry library is being re-targeted to read/write a per-model `serving_floors` section.
- Shared research clone `/mnt/raid0/llm/epyc-inference-research`: 221 commits behind origin/main, 5 uncommitted tracked files no session claims. Plan agreed by all three sessions: rescue branch, then fast-forward after `7B_AK_ENDED`, with a `/proc` cwd check first. Filed as NIB2-101 in `non-inference-backlog.md`.
- Tools built, tests NOT yet run in a granted window (no box ticked): `prior_check.py` + `validate_fillers.py` (root `f8/prior-check`; 49 tests passed inside the disclosed quiet window), floor registry + AKX-AUTO-6 `champion_reanchor` + `serial_run --new-anchor-epoch` pass-through (research + root `f8/floor-registry`). FILLERS.md column 6 redefined as peak host RAM GiB.

### Checklist sync / derived actionables

- Flips: DS41-W5b-floor (new, ticked), KVU-12.5 s4 re-run (ticked as DECLINED) = 2.
- New `- [ ]` filed: DS41-W5b-compare; register the 2.862% floor in the floor registry once its tests pass (owner f8, today); run the floor-registry / champion_reanchor / serial_run tests in a granted window then land both `f8/floor-registry` branches (AKX-AUTO-6/-11); re-run `f8/prior-check` tests, land, wire `validate_fillers.py` (CTC-Q-A/B); NIB2-101 = 5. `DS41-W5.1a-floor` confirmed (owner workspace-58 added).
- Explicit declines: KVU-12.5 s4 / 128k bank + poolfull (above). No other "we could" conclusions were left unfiled.

### SPEC-RNG.1.1 and SPEC-GRAM.1(1) results (2026-10-22)

- SPEC-RNG.1.1 (`experimental/spec-rng-argv-20261022` e3bf8dac8): argv/request switch landed, unit and kill-switch tests pass; np1==np4 and depth0==depth3 identity failed (7/8, 6/8 differ). Cause is CPU batch-shape logit drift, not the RNG (stateful control drifts identically). poskey matters only on the DFlash2 rejection path. Acceptance amended (np4 serial == np1 8/8; divergences low-margin via n_probs); SPEC-RNG.1.2 filed.
- SPEC-GRAM.1(1): frontdoor schema-eager B1 7.07% of a 25 ms step (tail-driven, 4.5% full-vocab fallbacks) -> OPENS_DI110; DI-110 materialized as XGRAMMAR-A2. Sensitivity: <5% if step > 35.3 ms. Part (2) unrun.
- Checklist sync: flips 1 (SPEC-GRAM.1(1) added ticked); new `- [ ]` 2 (SPEC-RNG.1.2, XGRAMMAR-A2).

## Per-task wrap-up 2026-10-22 (afternoon, workspace-f8)

| Item | Result | Recorded in |
|---|---|---|
| SPEC-RNG.1.1 retest (`f5cc4269f`/`5450617c5`, final test commit `261db6c7e`) | PASSES the amended rule: same-shape np4 serial == np1 8/8; all divergences (7/8 np1 vs concurrent np4, 6/8 depth 0 vs 3) drift at or before the first divergent token, 0 misaligned. Extra live-candidate check 1/13 exception (tail token p=0.043/0.023, top_p/min_p cut drift), downgraded to a report. SPEC-RNG.1.2 stays open. | `speculative-decoding-mtp-refresh.md` |
| KVU-12.2 MTP-on bank cells | PASSED: candidate `dd3d9721c` 4/4 cells, acceptance 0.98-1.02, decode 0.98-1.01, tokens identical; unported control 4/4 fail (0.53-0.71 / 0.77-0.82). `/mnt/raid0/llm/tmp/f8-fillers-20261022/kvu122/VERDICT.json` | `kv-unified-stack-rollout.md` |
| UFH14-LB10 `%llguidance` guard | Orchestrator main `1e707b8d` (`reject_unsafe_grammar`, 14 tests). API NOT reloaded (pending operator): reload task filed. Direct role-port clients bypass it. | `agentic-serving-harness-fixes.md` |
| KPF-13 fork | Fork cleared (`kpf13-repro`): no-fork cache hit == A1, no-1-token-ubatch prefill == B1. v11 property: fork ≡ cache hit with the same remainder. KPF-13.1 control text corrected; v2 tokens clean, acceptance needs rules v3 (drafter run-to-run spread), filed. | `kv-prefix-fork-and-paged-attention.md` |
| KPF-17.2 | Closed on prior queue results (jobs 20, 27, 29, 30). | same |
| AK-RX-1 / AK-RX-1.1 | NULL: real-archive repair-chain replay (research `a13a267d2`), no arm beats the fixed policy. | `autokernel-research-loop.md` |
| DS41-1017 floor | In the master registry, research `d077d6c55` (`serving_floors`, 2.862%). | `deepseek-v41-flash-evaluation.md` |
| Pipefail early-exit lint | Landed root `6b2c351ad`; cleanup of ~150 live hits + hook wiring filed. | `non-inference-backlog.md` |
| Locals + agent-beacon intake | Landed on main (`12206f57b`): intake-2386..2460 (renumbered +40, Bark took 2346..2385), 19 handoffs plus stub `dev-harness-trace-mining.md` (EVL-52). Operator: P4 reads the existing vault `/mnt/raid0/llm/cloud-llm-vault` (no new snapshot); claude-code-proxy declined; follow-up kernel intake approved, not run (CH-18.c filed). | `autokernel-champion-aggregate.md` |

- Docs: `docs/guides/agent-workflows/benchmark-analyst.md` gained *Identity checks across batch shapes* (KPF-13 + SPEC-RNG.1.1 instances) and the region-lock `python3` = venv 3.11 trap. Placed there, not in `agents/shared/MEASUREMENT_POLICY.md`, because that file is inside the human-amendment-only measurement trust boundary.
- Engine hazard: `filler_run2.sh` stale pollers take re-written grants and a sibling's bogus `refused:own-port` `.ended` deletes the live grant; fix filed as CTC-Q-G (`autokernel-concurrent-target-coordination.md`).
- CH-19 parked: already recorded (CH-19.3 ✅ 2026-10-21 PARKED); no change.
- Checklist sync: flips 7 (SPEC-RNG.1.1, KVU-12.2, UFH14-LB10, KPF-17.2, AK-RX-1, AK-RX-1.1, DS41 floor-in-registry) plus 1 new ticked line (LINT-PIPEFAIL-EARLY-EXIT). New `- [ ]`: 5 (UFH14-LB10 API reload, KPF-13.1 rules v3, CH-18.c follow-up kernel intake, LINT-PIPEFAIL-EARLY-EXIT cleanup, CTC-Q-G). Declines: none. Index: Next-action cells refreshed for INF-50, INF-65, RTG-58, UFH-14 (no rows added, deleted or re-pointed).
- Gate fix: `index_state.py --check` and `cite-check` failed on three overturned entry-level citations filed by today's Locals+beacon Stage 4 (intake-2435 in KPF-LB2, intake-2411 in HSF-LB1, intake-2434 in UTM-LB2). They are provenance tags on filed tasks, so they were narrowed to `#record`. Both validators now exit 0.

## Operator-invoked /wrap-up 2026-10-22 (subagent, branch `f8/wrapup-full-20261022`)

- Gap filled: the FILLERS queue validator ("queued means ready", 2026-10-22 ruling) landed on main as `03a4b109d` + `a367d1df0` with operator D9 acks for `scripts/coordination/**` (ready=y needs ARMED + live launcher pid; ready=n rows are BACKLOG with blocker+owner; REGISTERED/ready=n is an error; terminal rows skip field checks; `min_effect` accepts `n/a (<reason>)`). Recorded in `autokernel-concurrent-target-coordination.md` under CTC-Q-B: the land sub-task and the queue-semantics line ticked; the open remainder split out as "wire `validate_fillers.py --for-grant` into the grant writer" (no caller exists on main yet). CTC-Q-A/B stay open until that wiring lands.
- Locals+beacon intake Stage 4 (`12206f57b`) was already recorded above; its four implementation packets (`f8/locals-{a,b1,c,d}-*`) are in flight and were not touched.
- Index pruning: the generated prune signal had 0 candidates (182 handoffs: 176 open-tasks, 2 no-checkboxes stubs, 2 open-section, 1 open-assertion, 1 standing checklist RTG-18), so no handoff moved to `completed/`. Two DECIDED operator-queue rows pruned from `master-handoff-index.md`: OP-TOC-RD-1A (choice 1B, recorded in `tool-output-compression.md` TOC-RD-1a) and OP-80 (recorded in `autokernel-all-devices-all-dimensions.md` AKX-ALL-11); an archival note was added under the queue.
- Wiki: workspace-58's sweep 7 (`1dec6c3c1`, `5a0253370`) landed while this wrap-up was compiling the same delta, so this wrap-up's parallel sweep-7 draft (18 pages, three subagents) was discarded unapplied (kept at `/mnt/raid0/llm/tmp/f8-wrapup-full-20261022/my-wiki-sweep7.patch` until scratch cleanup) and a **sweep 8** compiled only the 16-source remainder: four pages got a "wrap-up sweep 8" section with the findings sweep 7 lacked — benchmark-methodology (identity checks across batch shapes), kv-cache (KVU-12.2 MTP-on bank 4/4 pass vs control 4/4 fail), hardware-optimization (AK-RX-1 bounded null; V11-086 re-port, no measurement), inference-serving (queue validator on main, not yet wired). The other remainder sources carried nothing sweep 7 had not covered. Bare `--touch`.
- README freshness: pass. Checklist sync: 2 flips + 1 new `- [ ]` (grant-writer wiring). Declines: none.

## KVU-LB1 upstream post (operator-approved)

Posted our CPU FP16 V-accumulator evidence on llama.cpp PR #29810 after operator review: https://github.com/ggml-org/llama.cpp/pull/29810#issuecomment-6340235109. Draft and sources: /mnt/raid0/llm/tmp/kvu-lb1-upstream-draft/ (DRAFT.md §c maps every number to its log). KVU-LB1.a ticked; .b (architect decode A/B) and .c (dense-MTP >64k check priority) remain open.
## Locals intake packet D: experimental llama.cpp code for UFH14-LB1, CH-LB1, AKX-ALL-LB4 (f8 locals-d subagent)

Branch `experimental/locals-kernel-fixes-20261022` (worktree `/mnt/raid0/llm/worktrees/llama-locals-kernel-fixes-20261022`), cut from the champion `ak/champion/llama-cpp-ffc1bac82eec` = `dd3d9721c`; local only, not pushed, NOT built (a build needs a calendar grant). Production tree untouched (`production-consolidated-v10` @ `ffc1bac82`).

| Task | Commit | State |
|---|---|---|
| CH-LB1 BF16 GDN state guard | `5f1eee195` | CPU supports_op refuses a non-F32 state, compute aborts with a named message, load-time warning; `test-gdn-state-guard` (ctest) + opt-in `gdn_bf16_state` test-backend-ops set. Launcher audit: no CPU launcher sets `GGML_CUDA_GDN_STATE_BF16`. |
| UFH14-LB1 `%llguidance` abort | `0daa3ca8d` | throw instead of GGML_ABORT, server answers 400 and keeps serving; server pytest added. Role ports all bind 127.0.0.1 (local clients only bypass the orchestrator guard). |
| AKX-ALL-LB4 iqk CPU FA, step 1 | `8f0fa64ca` | fa/ vendored + build wiring behind `GGML_IQK_FLASH_ATTENTION` (OFF), FLASH_ATTN_EXT hook + work size, opt-in `fa_cpu_long_ctx` set + `test-fa-rowexact`. Configure-only checked ON/OFF. Remaining: compile fixes, gates, row-exact decision, argv switch. |

Build+test specs are under each task in its handoff. Boxes stay unticked until build+tests pass. Default test-backend-ops corpus unchanged (new cases are opt-in via `TEST_BACKEND_OPS_EXTRA_CASES`) so AK per-op case counts do not move.
## Locals + agent-beacon non-inference tasks (locals-a, 2026-10-22)

Orchestrator branch `f8/locals-a-orch-20261022` (6 commits on origin/main `1e707b8da`, unmerged, not pushed); root branch `f8/locals-a-root-20261022` (handoff ticks and this entry).

| Task | Outcome | Evidence |
|---|---|---|
| UFH14-LB2 | persist half done (`365b20c6`): `parse_events.v1` with finish_reason/n_tokens/max_tokens/site; the 14-day classification is child LB2.1 (needs merge + API reload + 14 days) | 13 tests |
| UFH14-LB3 | PROPOSAL (`658513a4`): `ORCHESTRATOR_TURN1_GRAMMAR=legacy|call|off`, default unchanged; no raw turn text retained; 4/81 enforced rows called a tool | 3 tests; recommendation: `off`, pending A/B (LB3.1) |
| UFH14-LB6 | extension done (finish_reason, stream_gaps with raw list, p99.9 sample flag); restore NOT proven: 75 records, 0 `infer`, vs 4,739 `llama POST start` lines; recorder now counts and logs drops (`health()`); 8 unrecorded call sites listed (LB6.1, LB6.2) | 6 tests |
| UFH14-LB9 | done (`3bbb443c`): 2/87 text-only replies (2.3%) re-tokenize one token shorter than generated; tool-call turns not measurable (LB9.1) | 2 tests |
| KPF-LB1 | tabulated (`80bdae83`): 27B chat path 20-25% of turn 2-3 steps below 10% cache; /completion x turn not measurable from logs; child KPF-LB1.1 carries the needs-compute spec | 2 tests |
| HSF-LB1 | done (`28ed886f`): correction note under HSF-4, dispatch.v1 `preceding_tool` / `turn_trigger` / `finish_reason` | 3 tests + 107 suite |
| RTE-PFX-LB1 | done (`567b43c0`): all three local roles are recurrent hybrids (frontdoor `qwen35moe`); `junction-ckpt` arm added to the A/B spec | 2 tests |
| TOC-SP-LB1 | done (`640e7a37`): consecutive-identical rate 0.03% local, 0.04% deepseek, 0.24% Claude vault, 0.39% Codex vault; decision: wire neither now | 5 tests |

- Reads were read-only and bounded: `opencode.db` opened `mode=ro` with `PRAGMA query_only`, `nice -n 19`, LIMITed sessions; the vault was read, never written. No server, model load, build or background process.
- Checklist sync: flips 4 (UFH14-LB9, HSF-LB1, RTE-PFX-LB1, TOC-SP-LB1); new `- [ ]` 7 (UFH14-LB2.1, LB3.1, LB6.1, LB6.2, LB9.1, KPF-LB1.1; LB2/LB3/LB6/KPF-LB1 parents stay open).
- Lesson: a recorder that swallows every exception cannot be told apart from a recorder that was never reached; a 19-record census over 17 days was the only signal. Fail-open writers need a per-process drop counter.
## Locals B1 — dev-harness trace substrate (subagent, branches `f8/locals-b1-{root,orch}-20261022`)

- UTM-LB1: existing backup verified read-only with new `scripts/system/backup_coverage.py` (job live, STATUS OK 02:16Z
  and 11:43Z). Covered: Claude transcripts+subagents, Claude memory, Codex rollouts (vault + tarball). Partial: opencode.db
  (one-off `.db.zst` from a root run at 11:28Z). Not covered: history.jsonl, Codex state sqlite, agent_audit + orchestrator
  logs, serving_calls, planner_archive. Anomalies: 6/14 tarballs present, 62-day log gap 08-03..10-03. Decision package
  filed as UTM-LB1.D; nothing copied, no backup built.
- UTM-LB2 projector + F3-LB1.1 privacy gate + DHM-7.1 AgentRun converter in `scripts/dev_harness/`; private root
  `/mnt/raid0/llm/private/dev-harness-traces`. The PII hook `[transcript]` scan (F3-LB1.2) is prepared but uncommitted:
  D9 refuses a hooks change without an operator `D9-ack:`. Sample `sample-20261022`
  (20 main sessions / 66 units): projector 2.2 s, converter 1.4 s, nice 19. 17 committed tests + 10 hook tests (uncommitted) + 92 PII hook tests pass.
- UTM-LB3: orchestrator `08670ddd`, agent_audit ingester reads the per-agent shard directory.
- VB-LB1: four aggregate-only source rows in `scripts/vidya/adapters/README.md`; adapter follow-up VB-LB1.1.
- NIB2-LB1.1: `backup_coverage.py precondition` plus the rule in `cleanup-reference-check.md`; wiring it into the opencode
  event reaper (NIB2-LB1.2) waits on UTM-LB1.D (the extract fallback would be a copy job, which the ruling forbids).
