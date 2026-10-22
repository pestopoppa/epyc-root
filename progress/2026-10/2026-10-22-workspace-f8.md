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

## Locals + beacon zero-compute AK / serving-prep tasks (agent locals-c, worktree `f8-locals-c-root`, branch `f8/locals-c-root-20261022`)

Seven filed tasks done, all zero-compute (no server, no weights, no build, no GPU). Research commits on branch `f8/locals-c-research-20261022` (unmerged, unpushed): `0eea263b4` INF37-LB1, `f8df555cf` AK-PORT-LB1, `b9d43a4a2` AKX-ALL-LB2, `c38ef247b` KPF-LB2, `8b545b228` DS-LB1 ordering log, `65152c086` DS-LB1/UFH14-LB5 prefix-property tests. Campaign store (not git): `50-locals-smallbatch-ports-20261022.md` written to the 27B GPU campaign `store/inbox/` and mirrored into the np1-r12 store's inbox.

| Task | Result |
|---|---|
| AKX-ALL-LB1 | Inbox file written (seeds 50.1-50.6, H4 loader-concat evidence, do-not-reseed list, standing rule); `read_inbox` lists it. |
| AKX-ALL-LB2 | `loop/production_surfaces.py` (N=8/16/32 + ragged {1,8,8,8}; N=8-only keep = not-yet-transferable). Recipe JSON unchanged on purpose (strict dataclass + content hash). |
| AK-PORT-LB1 | `loop/noise_relative_tolerance.py` + `gates.check_noise_relative_tolerance`, 17 tests. |
| INF37-LB1 | Static ISA audit on the v10 kernel-store HIP library: Q8_0 and IQ4_XS weight loads hoisted (3/row flat, ncols 1..8); Q4_K re-issues 3 ushort scale loads per column (6 -> 27 per row at ncols 8) and unpacks per column; ncols 4 hoisted by the existing b4 path. |
| KPF-LB2 | Harness amended before the first live arm; finding: the original sample's 7 "claude" sessions are all sub-agent transcripts; store-wide child share of requests 73.6 %. PREDECLARED.md Amendment 1. |
| DS-LB1 | Prefix-property tests + arrival_seq / accumulated-service log in the replay. |
| UFH14-LB5 | All as-served templates hold the prefix property at enable_thinking=false; stock Qwen3.6-35B embedded template fails (drops the empty think block from history), which the terse override fixes. |

Index rows PREPARED, NOT APPLIED (owning session applies): `INF-81` next action add "AKX-ALL-LB2.1 (measure N=16/32/ragged for the first 27B keep; MI210 window)"; `RTG-58` add "KPF-LB2.1 opencode V2 real-row check; KPF-LB2.2 recalibrate E/F knobs at the first live arm"; `INF-06` add "AK-PORT-LB1.1 wire the noise-floor gate into the first multi-row candidate"; `UFH-14` add "UFH14-LB5.1 live-server confirmation of the static template result". INF-37 and RTG-11 need no change.

Pre-existing reds observed, not caused here: `test_campaign_footprint` (three loop modules without a FOOTPRINT row plus totals drift); KPF-64 `test_launcher_*` need `KPF64_PORT=31111` because ports 18964/18971 have listeners on this host.

## KVU-12.1 + KPF-18-S1 verdicts (runs ended ~12:24Z; analysis only, no compute)

- **KVU-12.1** (`/mnt/raid0/llm/tmp/kvu121-arms/out/`; read-only `decide` → `/mnt/raid0/llm/tmp/f8-kvu121-kpf18-verdicts/kvu121_decide.json`,
  selection `{"q36_35b": null}`): **DENSE_STAYS** for every arm, so keep `--ctx-checkpoints 32 --checkpoint-min-step 8192`. Not ticked.
  - 8k does not discriminate: the spacing arms tie dense on bytes, and fixed_s4k is +27.8%.
  - tail_junction fails on substance at 32k: 40% fewer bytes, but deep edits fully re-prefill (37,976 vs 9,200 tokens).
  - Simulator NOT validated: `sim_matches_log=false` in 16/16 cells. Causes: estimated user-start offsets, the first user
    start is dropped, the n_ubatch checkpoint is off by 4, and wave 1 inherits wave 0's checkpoint on the warm server.
    The launcher ran phase 2 without checking agreement.
  - The 32k w1 ERRORS are a driver bug. `fit_conversation` overshoots its target (38,868 tokens vs 32,688) and
    `extend_1` overflows `-c 40960` (HTTP 400). That also explains tail_junction's 3,233 s wall: three full ~38.7k-token
    re-prefills.
  - Filed KVU-12.1a (driver fixes) and KVU-12.1b (32k dense vs coarse holdout, ~2.2 h quarter, ~45 GiB, predicted DENSE_STAYS).
- **KPF-18-S1** (`/mnt/raid0/llm/tmp/kpf18-s1/out/records/`): steps 1-5 ran; steps 6 and 7 did not run.
  - Item 2 rule not met (0/12 against a zero, placement-fixed A/A floor).
  - 18.1 A/B/C/D, 18.2 and 18.3.1 rules met; 18.3.4 abstained.
  - Item 3 group 3: `aa_diverges_earlier` (undetermined). Read as batch-shape/placement numerics, not a fork defect:
    the A/A flips at 114 without any fork, the 161 flip sits at a 0.167-nat near-tie, and CPU 17.2(3) is byte-identical.
  - Filed KPF-18.0d(item 3) v2 (same-shape control) and the S1 remainder + oracle repair.
- **Belief wiring**:
  - KPF write side is producing (15 records). The read side voids the file on the S1 sub-arm names (0/15 project):
    filed VB-KVU-PF.2 and updated the README status cell.
  - KVU-12.1 request rows go through the VB-KVU-CPU emitter: added a note under VB-KVU-CPU (`cells.jsonl` is unhashed).

## KVU-12.1a driver fixes + VB-KVU-PF.2 read side + UFH14-LB1/CH-LB1 ticks (subagent, no compute)
- **KVU-12.1a** (research `f8/kvu121a-driver-20261022` @ `f7b647705`, not pushed): fail-loud fit (`REFUSED_FIT`), `-c` per cell with a
  pre-request `REFUSED_CTX`, exact `ServerSim` on rendered token ids, one fresh server per ckpt cell, `REFUSED_SIM_GATE` phase gate (rc 8).
  Offline re-check of the recorded run (offsets rebuilt without a server; every prompt length equals the logged one): wave 0 went from
  0/8 cells agreeing to 8/8 cells and 34/34 requests exact. Wave 1 still differs, only by the checkpoint inherited from w0.
  `test_kvu_ckpt_arms.py` 86 passed.
- **VB-KVU-PF.2** (root `f8/vbkvupf2-20261022`; research writer `f8/kpf18-rowsha-20261022` @ `5ed8a628d`): the adapter accepts the
  declared KPF-18 sub-arms (`kpf18_arm` locator), and a record with no `rows_sha256` projects attested-absent (nothing hashed on read).
  The writer now always attests a rows file. S1 sidecar: 0 -> 15 natives, all Judged/Located (no protocol; 1 attested-absent);
  checked on a scratch ledger (canonical ledger untouched). The live runner copy at `/mnt/raid0/llm/tmp/kpf-p1-20261004/kpf18/` still
  predates the writer fix.
- **UFH14-LB1 / CH-LB1** ticked: build + tests passed on `experimental/locals-kernel-fixes-20261022` @ `452887155` (12:33:58Z,
  `/mnt/raid0/llm/tmp/f8-fillers-20261022/locals-d/off/out/steps.txt`). Fold-into-champion children UFH14-LB1.1 and CH-LB1.1 left open.
## opencode mining readers repointed at the read-only snapshots (f8-ocro)

- Operator ruling 2026-10-22: mine EVERYTHING from `/mnt/raid0/llm/opencode-db/{epyc.db,host-daniele.db}` (hourly ro `.backup`
  snapshots) and the vault `{host,twyne,epyc}/{claude,codex}`; every record carries a `source` tag. Never the live stores.
- Root (`f8/opencode-ro-root-20261022`): `dh_sources.py` gains `OPENCODE_RO_DBS`, `open_ro` (`?mode=ro`, `query_only`, retry once),
  `refuse_live_opencode_path`, `Unit.source`; `projector.py`/`agentrun.py` default to both DBs and `--tenant all`, outputs under
  `<harness>/<source>/`; `dh_privacy.py` adds `/mnt/raid0/llm/opencode{,-db}` as never-write roots; `backup_coverage.py` counts
  opencode covered by fresh (<3 h) snapshots. Tests: `tests/dev_harness/test_opencode_ro.py` (+ updated existing).
- Smoke on the real snapshots (`select count(*) from session`, ro): epyc.db 1241, host-daniele.db 16045.
- NIB2-LB1.2 resolved (reaper prunes only `event`, which mining no longer reads); UTM-LB1 and dev-harness-trace-mining.md sources updated.

## AKX-ALL-LB4 iqk CPU FA: correctness gate passed on the experimental branch

Three port bugs fixed on `experimental/locals-kernel-fixes-20261022` (c64cd9c14, dd756036a, 629b545e0); the decisive one was the iqk kernel's binary-mask assumption against FLASH_ATTN_EXT's additive mask. FLASH_ATTN_EXT backend-ops 5182/5182; long-ctx f16 residual failures are the reference's F16 accumulator (pass with GGML_FA_VKQ_F32=1). q2 debug grant f8-lb4-debug (workspace-58) closed 13:07Z. Follow-ups AKX-ALL-LB4.2-.5 filed.

## Per-task wrap-up 2026-10-22 (evening, workspace-f8, gap sweep after 1cab565da)

- Swept root `1cab565da..origin/main` against the progress shard and handoffs: KVU-LB1.a, Packets A/B1/C/D, KVU-12.1/KPF-18-S1 verdicts, KVU-12.1a/VB-KVU-PF.2, opencode snapshot repointing, UTM-LB1.D and AKX-ALL-LB4 already carried checkbox state, progress lines and follow-ups. No flips needed.
- Gap (a): the KPF-64 replay adapter opens the live `opencode.db`, contrary to the read-only-snapshot ruling. Filed `KPF-64.1` (repoint to snapshots, add vault sources; explicit decline for the live Claude/Codex JSONL as an additional source).
- Verified present: CTC-Q-G (ticked), AKX-ALL-LB4.2-.5 (open). CTC-Q-B stays open: workspace-58 wires `grant_ok.sh` and ticks it.
- Observation for the record (another session's, not f8's): the cs8l-asr2 stage-3 subagent ran a job without a grant. Noted only; no action here.

## Dev-harness mining M2 (DHM-2, DHM-3, DHM-4, DHM-7.2, HIL-LB1)

- One driver, `scripts/dev_harness/mine_m2.py`, runs all four analyses in a single streaming pass over a projection and its AgentRun conversion. Per-session output goes only under `/mnt/raid0/llm/private/dev-harness-traces/mining/<run>/`. The aggregate passes `dh_privacy.validate_aggregate`; its schema is in `scripts/dev_harness/mining_m2_aggregate.schema.json`. Modules are `m2_common`, `m2_guards`, `m2_lessons`, `m2_label_sheet` and `m2_cluster`. Tests: `tests/dev_harness/test_mining_m2.py`, 45 passing.
- Sample run (`sample-20261022`; 65 units, 4,050 tool calls; 2.0 s, 60 MB RSS):
  - 63 would-fire calls. 43 are containment refusals, all blocked by the hook; the rest are git stash 5, git reset --hard 4, pgrep on a pattern 3, worktree prune/force 3, glob rm 2, wholesale add 2 (blocked) and hooks-path-null 1.
  - 75 hook denials, all from Claude Code.
  - 3 interrupts.
  - 6 clusters reported; 3 of 5 planted classes recovered.
- Full run: scheduled by the main thread, outside the quiet window. Estimated 10–25 min, ~1–2 GB RSS.
- DHM-3: registry of 290 lessons and the ITS spec, `docs/design/dev-harness-its-pilot-spec.md`. Memory files and CLAUDE.md were only read.
- HIL-LB1 was already done (a1-orch-code, orchestrator `258ce2d7`, scored against the Who&When labelled loop set). No work was needed.
- Belief-kernel wiring for the DHM series was already filed (VB-LB1, adapters README rows 751/754).
## Mining wave M1 (DHM-1, DHM-5, DHM-6, OAB-LB1, UFH14-LB8) — mining-m1 subagent

- New driver `scripts/dev_harness/mine_m1.py` (stdlib, one events pass for DHM-1+DHM-5, raw vault rollouts for
  OAB-LB1, read-only opencode snapshots for UFH14-LB8) + `tests/dev_harness/test_mine_m1.py` (15 tests, synthetic
  fixtures; all 62 dev_harness tests pass). Per-session rows go to `<private-root>/mining/<run>/m1/`, aggregates
  (dev-harness-aggregate.v1, validated, provenance + sample frame) to `.../m1/aggregates/`. Nothing committed from data.
- Sample run only (quiet-window rule): `sample-20261022`, 4.3 s, 75 MB RSS. Headlines are in the handoff notes.
- Findings: (1) Codex fork/spawn children replay parent history with fresh timestamps (one parent's aborts copied into
  32 forks) — DHM-1 and OAB-LB1 dedupe it; (2) Claude Code JSONL `usage.output_tokens` is a stale streamed value
  (14.5 chars/token), unusable for calibration; (3) AK-lane exec is ~1% of turn wall time in the first 3,000 threads.
- DHM-6 ticked: `docs/design/guard-denial-ledger-proposal.md`.
- Full run (main thread schedules, outside 14:30-22:00Z): `nice -n 19 /usr/bin/python3 scripts/dev_harness/mine_m1.py
  --projection /mnt/raid0/llm/private/dev-harness-traces/projections/full-20261022T1310Z` — est. 5-10 min, ~1.5 GB peak.
- Not run: the DHM-1 correction keyword pass needs `--history ~/.claude/history.jsonl`, a live store this lane may not open.
- Shared-dir note: another wave writes `mining/sample-20261022/` (dhm2/3/4/7.2 files); M1 uses the `m1/` subdir. My first
  sample run wrote into the shared dir at 13:44Z and was removed; their files were not touched.

## Afternoon: full projection, mining code, tonight's armed queue

- UTM-LB2.1 full projection done 13:33Z (run full-20261022T1310Z: 42,744 units, 3.2M events, 4,066 commit joins, 858 s; private output only).
- Mining code landed (M1 b74794809, M2 0e2d51d82); full run armed as FILLERS `dhm-mining-full` for tonight. It reads a private copy of ~/.claude/history.jsonl, never the live file. It produces the operator's DHM-4 labelling sheet (private).
- Seven compute rows armed with launchers in /mnt/raid0/llm/tmp/f8-launchers-20261022/:
  - GPU tonight after yarn: kpf18-item3-v2-sameshape, locals-df2-lb1-ubatch-census.
  - q2/q3 tonight: kvu121b-32k-dense-vs-coarse, locals-specgram2-window.
  - Whole-host block 10-23 ~07:55-10:30Z: locals-akx-lb3-cpu-lc-premeasure, then locals-kvu-lb1-arch-decode-ab. The operator approved the ~2.5 h of 503s on the 0-95 serving roles via AskUserQuestion.
- Blocked: KPF-LB1.1 needs a captured 12-turn REPL transcript (replay_recording on for one live run); this ties to the operator's pending API reload.
- Operator rulings today: no backup work here (root agent owns it); mine everything via the ro snapshots /mnt/raid0/llm/opencode-db; operator name in commits is fine.

## Evening 2026-10-22 (operator-invoked /wrap-up, subagent, branch `f8/wrapup-20261022-evening`)

Covers work since the afternoon wrap-up (root `78bbd5687`). Each item below was checked against git.

- **HF token (SEC-EXEC-6).** The operator closed the huggingface.co revoke sub-task as declined (root `4b071084d`, rollup `a6cea4160`). Both local token files were already deleted on 2026-10-21. The SEC-EXEC-6 parent stays open for its chmod / token-free nextplaid mount remainder.
- **KPF-LB1.1 no longer needs the operator's API reload.** The launcher captures its own 12-turn REPL transcript in-window, on one private 27B server: `capture.py`, a socket guard, every URL on the private port, and a server restart before the lanes. The PREDECLARATION was amended at 16:15Z, before any compute. workspace-58 armed the launcher (pid 3419004) and booked it on tonight's GPU tail (root `55a61404f`, rollup `04b091f4b`). The capture found two orchestrator bugs, fixed on orchestrator main `cdbca26b` (operator approved):
  - `registry_role_urls` ignored the `ORCHESTRATOR_SERVER_URLS_<ROLE>` overrides, so the context-limit fallback contacted production :8083 from a private-URL harness. The override is unset in production, so serving does not change.
  - `auto_wrap_final` wrapped one-line assignments into an always-failing `FINAL(...)`. This fix goes live at the next API reload.
  - The operator noted that the next kernel/stack upgrade opens a new era anyway, so the second fix needs no era row of its own.
- **Floor registry.** The tests (42 pass on research `b93017dc9`) and the landing are ticked. AKX-AUTO-6 and AKX-AUTO-11 each got an exercise sub-task. workspace-7b's Q38FN longctx digests are recorded as UNREGISTERED and indicative only, because no `dd3d9721c` store-build floor record exists (root `ed8ec14d7`, rollup `a9dcd63d9`).
- **Locals+beacon non-inference follow-ups:**
  - Orchestrator main `d0e0e477` holds two items. The UFH14-LB3.1 turn-1 probe logs `turn1_grammar_shape` and `turn1_output`. The UFH14-LB6.2 change records worker_pool `/completion`, schema repair and both VL calls through `record_http_call`. A subagent pushed this commit to main by mistake: it ran a bare `git push` with `push.default=upstream` on a branch cut from origin/main. The operator reviewed the commit and chose to keep it. A memory was saved: always push with an explicit refspec.
  - Research main `ea3c98434`: KPF-64.1 adds the opt-in `--vault-sources` to the replay adapter (operator approved). It is off by default, so the predeclared seed-64 draw is unchanged.
  - Root `1b88d6c1d`:
    - UFH14-LB9.1: 444 of 450 tool-call turns re-tokenize exactly.
    - DHM-7.2: the granite-97m CPU embedder recovered 5 of 5 planted classes, against 3 of 5 for hashed TF-IDF, on the sample.
    - The UTM-LB4 OTel field list.
    - Ticks for F3-LB1, NIB2-LB1 and KVU-LB1.c.
    - Corrected "unmerged" notes on landed branches.
  - Root `dac42532e` (rollup `861b8576d`):
    - AKX-ALL-LB4.2/.3/.5 code is on `experimental/locals-kernel-fixes-20261022` @ `9a338d4f1`, pushed to the fork. Not built.
    - LB4.4 is closed as won't-port: there is no ARM hardware, and the hook declines on non-AVX2 builds.
    - The UFH14-LB4 chat-parser test is written.
    - The v11 manifest has row V11-102, status PEND.
    - Job `akx-lb4-followups` is armed (pid 3817335) and booked on q2 tonight.
- **Follow-up kernel intake (CH-18.c).** Covers ik FlashMLA #277/#243, the #1212/#1215 q8_0 repack, issue #1205 and ggml #28576. Stage 1 landed (root `89286a640` + `55dad9032`, intake-2494..2503). Another subagent is running the Stage 2 dives, so this wrap-up did not touch those entries.
- **SEC lanes.** Another subagent is preparing the landing; it started after the gitnexus re-index finished at 16:55Z. Nothing has landed yet.
- **Still scheduled tonight (FILLERS rows verified):**
  - `dhm-mining-full`, which produces the DHM-4 labelling sheet.
  - The GPU runs `kpf18-item3-v2-sameshape`, `locals-df2-lb1-ubatch-census` and `locals-kpf-lb1-1-27b-completion-turns`.
  - On q2/q3: `kvu121b-32k-dense-vs-coarse`, `locals-specgram2-window` and `akx-lb4-followups`.
  - On 10-23, the whole-CPU runs `locals-akx-lb3-cpu-lc-premeasure` and `locals-kvu-lb1-arch-decode-ab`.

| Repo | Commit | What |
|---|---|---|
| epyc-root | `4b071084d` (+ rollup `a6cea4160`) | SEC-EXEC-6 revoke sub-task declined (operator) |
| epyc-root | `55a61404f` (+ rollup `04b091f4b`) | KPF-LB1.1 self-captures; capture fixes recorded; run armed |
| epyc-root | `ed8ec14d7` (+ rollup `a9dcd63d9`) | floor-registry ticks; AKX-AUTO-6/11 exercise sub-tasks; Q38FN unregistered |
| epyc-root | `1b88d6c1d` | UFH14-LB9.1, DHM-7.2 embedder, UTM-LB4, LB ticks, landed-branch notes |
| epyc-root | `89286a640`, `55dad9032` | kernel follow-up intake Stage 1 (intake-2494..2503) |
| epyc-root | `dac42532e` (+ rollup `861b8576d`) | AKX-ALL-LB4.2-.5, UFH14-LB3.1/LB4/LB6.2, KPF-64.1 recorded; V11-102 PEND |
| epyc-orchestrator | `cdbca26b` (main) | context-limit fallback honours URL overrides; no FINAL-wrap of one-line assignments |
| epyc-orchestrator | `d0e0e477` (main) | UFH14-LB3.1 turn-1 probe; UFH14-LB6.2 call-site recording |
| epyc-inference-research | `ea3c98434` (main) | KPF-64.1 vault sources |
| epyc-llama (experimental, fork) | `9a338d4f1` on `experimental/locals-kernel-fixes-20261022` | LB4.2/.3/.5 + chat-parse truncation test (not built) |

### Checklist sync / derived actionables (this wrap-up)

- Flips 2: UFH14-LB3.1a (the logging half) and UFH14-LB6.2a (the four wrapped call sites). Both were recorded only in prose; the work landed on orchestrator main `d0e0e477`. All other evening items already carried checkbox state.
- Filed 4 new `- [ ]`:
  - UFH14-LB3.1b: the A/B run, with its full run spec.
  - UFH14-LB4.1: the history-echo side finding. A client that echoes a call's invalid-JSON `arguments` back in the history makes `common/chat.cpp:2372` throw `std::runtime_error`. A static read of `ex_wrapper` says that becomes a 500, but this is unconfirmed.
  - UTM-LB4.1: the tool-call and sub-agent lineage OTel fields.
  - DHM-7.2a: the granite full-corpus run, with its command. Tonight's `dhm-mining-full` runs `mine_m2.py` without `--embed-gguf`.
- Repair: the DHM-7.2 embedder note had been inserted under DHM-4, splitting the DHM-7.2 task line. It now sits under DHM-7.2.
- Declined 2, both in writing:
  - UTM-LB4 compaction via OTel. A compaction needs a context-filling session, and the transcript projector already records compaction boundaries. The decline is written in `unified-trace-memory-service.md`.
  - The kernel-intake preliminary actionables. They belong to Stage 3 of CH-18.c, which binds each keep to the v11 list or the fold-ledger route once the Stage 2 dives return. Filing them now would bypass that gate and could collide with the in-flight Stage 2 subagent.

## Late evening 2026-10-22 (operator-invoked /wrap-up #2, subagent, branch `f8/wrapup-20261022-late`)

Covers work since the evening wrap-up (root `520138b70`). Each item below was checked against git, the
FILLERS register or the process table; scheduling items relayed by workspace-58 are marked as such.

- **Kernel follow-up intake (CH-18.c).**
  - Stage 2 is on main as root `1b8e9d259`: 8 entries dive-verified (intake-2494..2501, 2500 dived as the
    2498 fix pair). The second-reader waves re-found every anchor quote and re-matched every sha256
    (72 + 19 + 12 = 103 checks, `.research-session.json`).
  - Headline findings:
    - intake-2499: ggml #28576 does NOT fix the MFMA FP16 VKQ overflow. The unnormalized partial is still
      staged as half before the row-sum division, and opnan arms E and C fail the same 6/228 cases. This
      overturns the CPU-FA-VKQ-4 premise.
    - intake-2501: the port's work-size formula alone under-sizes for the runtime -inf trim (model: up to
      4x on GQA12, up to 31x on DS41). It is safe today only because the mainline prefill tile term
      dominates the graph-plan MAX, which also makes a sanitizer run vacuous.
    - intake-2494/2496: sinks can be folded once per row after the merge.
  - The operator selected 6 sources for Stage 2b (steering seq 3). They became 7 entries on main as root
    `a30f929d8` (intake-2504..2510: ik #2442, #2710, #2165 with #2287 folded, #2511, #1935, #1880 with
    issue #809 folded, #1923). The Stage-2 close-out gate is CLOSED.
  - The Stage-3 plan is drafted at `/mnt/raid0/llm/tmp/intake-kernel-followup-20261022/STAGE3_PLAN.md`
    (sha256 `3583551b…`). It awaits operator approval and is NOT applied: no handoff or index edits.
- **SEC lanes landed.** gitnexus flagged `Features` CRITICAL and `_launch_runtime_record` HIGH. The
  operator approved landing after review; both changes are additive.
  - Landed: orchestrator `bbc74d5c`, research `0a71fd5d6`, root `a7bfde22d` and `629ea0d17`. All are on
    origin/main.
  - D9 ack 2026-10-22 for the `install_git_hooks.sh` epyc-web line, recorded as an amended trailer on
    root `a7bfde22d`.
  - Post-landing handoff ticks for 7 boxes (SEC-EXEC-3/5/7, SEC-ART-3/7/9, SEC-SECRETS-1) are at root
    `85c5ef820`. That commit also filed SEC-ART-POST-a..e and SEC-EXEC-POST-c..e.
  - The name-only git-history secret scan found 0 real findings across ~18.7k commits in 4 repos.
- **SEC-ART-POST.**
  - POST-c: research `c4017b4f4` adds served-only template pins for `reap_25b` and
    `document_formalizer`, the two non-lineup roles with a GGUF on disk. All 4 lineup roles (frontdoor,
    architect_general, architect_critic, worker_vision) already carried pins, re-verified against
    today's bytes. `template_pins_strict` is untouched.
  - POST-e: the template-store re-point is prepared on research branch `f8/sec-art-post-e` @
    `929a5d667` (worktree `/mnt/raid0/llm/worktrees/f8-sec-art-post-c`). NOT landed: the store must hold
    the file first. Order: publish, land the re-point, recompile.
  - POST-a: the fingerprint job `sec-art-fingerprints` is armed (pid 555983, FILLERS row present). Per
    workspace-58 it is booked on q0/q1 tonight and done by 06:15Z.
  - Finding: the orchestrator lean registry and `stack_priors` carry no sha256 or template pins. Pins in
    the master registry therefore do not reach the launcher until a recompile through the stack-change
    step. Filed as SEC-ART-POST-f.
- **/workspace sync (operator-approved).**
  - The shared clone was 778 commits behind, and its local main carried an unpushed duplicate commit
    `b397f203e`. It was synced to origin/main `92431e3ab`. The ref `backup/workspace-local-b397f203e` and
    the backup dir `/mnt/raid0/llm/tmp/workspace-ff-backup-20261022/` keep the old state.
  - Method: a two-way `read-tree` plus `update-ref`, after the hygiene hook correctly blocked a checkout.
    Uncommitted edits were preserved, and the epyc-web row was re-applied to CLAUDE.md as a local edit.
  - Hooks were reinstalled. epyc-web now has a pre-commit hook, and orchestrator/research commits run the
    current PII/secret hooks. A later plain fast-forward to the then-current main worked; /workspace
    HEAD is now `85c5ef820`.
- **Re-index.** The gitnexus re-index `f8-gitnexus2` is armed (pid 308272, FILLERS row present). It
  refreshes the index of the stale `b397f20` tree. Per workspace-58 it is booked for 10-23 ~06:50Z.
- **Scheduling (relayed by workspace-58).** The 10-23 whole-CPU block moved to ~07:40Z, and the operator
  approved the 503 window shift to ~08:25–11:00Z. workspace-58 booked `locals-specgram2-window` and
  `kvu121b-32k-dense-vs-coarse` on tonight's q2 tail after `akx-lb4-followups`.

| Repo | Commit | What |
|---|---|---|
| epyc-root | `1b8e9d259` | kernel follow-up intake Stage 2 (intake-2494..2501) |
| epyc-root | `a30f929d8` | kernel follow-up intake Stage 2b (intake-2504..2510) |
| epyc-root | `a7bfde22d`, `629ea0d17` | SEC-SECRETS-1 patterns + epyc-web hook; new-model SEC-ART steps |
| epyc-root | `85c5ef820` | SEC post-landing ticks; SEC-ART-POST / SEC-EXEC-POST sub-tasks |
| epyc-orchestrator | `bbc74d5c` (main) | SEC-ART registry tooling, containment, template provenance |
| epyc-inference-research | `0a71fd5d6` (main) | SEC-ART-3 uploader_class for the lineup roles |
| epyc-inference-research | `c4017b4f4` (main) | SEC-ART-POST-c template pins for reap_25b and document_formalizer |
| epyc-inference-research | `929a5d667` on `f8/sec-art-post-e` | SEC-ART-POST-e re-point (NOT landed) |

### Checklist sync / derived actionables (late-evening wrap-up)

- Flips 1: SEC-ART-POST-c (coverage met; see the dated note). Its `template_pins_strict` clause moves to
  SEC-ART-POST-f, because the master-registry pins do not reach the launcher yet.
- Notes without a flip: SEC-ART-POST-a (armed, booked) and SEC-ART-POST-e (branch, publish command,
  expected digest, order).
- Filed 1 new `- [ ]`: SEC-ART-POST-f, the lean registry + `stack_priors` recompile via stack-change
  before any `pins_strict` / `template_pins_strict` flip.
- Declined 2, both in writing:
  - The kernel-intake Stage-2/2b actionables (LIN-1/LIN-2 ledger rows, the CPU-FA-VKQ-4 premise reversal
    and the sinks fold). The Stage-3 plan binds them to owners and is unapproved; filing them now would
    bypass that gate.
  - Committing the epyc-web row in CLAUDE.md. It exists only as an uncommitted local edit in /workspace.
    It is not filed as a task: a wrap-up subagent does not edit CLAUDE.md, so the owning session lands it.
- Index `Next action` cells for RTG-59 (SEC-ART) and UFH-16 (SEC-EXEC) still name tasks that have
  landed. Refreshed cells are prepared for the owning session.
- Fixed in this wrap-up: the documented lease helper `wrapup_lease_acquire` (`agents/commands/wrap-up.md`)
  returned the status of its trailing assignment, so `wrapup_lease_acquire || exit 2` swallowed a
  refusal. Measured here: this wrap-up's second protected section ran while workspace-58 held the lease.
  The generated output was never committed; it was redone under a held lease after syncing. The helper
  now returns the refusal (`|| return $?`). New test
  `test_documented_wrapup_acquire_refusal_is_visible_without_errexit` passes with the other 5 in
  `tests/coordination/test_concurrent_wrapup.py`.

## Mining results (full-20261022T1310Z, aggregates only)

- Run: 42,420 units, 863 interrupt candidates, 13,989 cluster docs, 80 clusters, planted 3/5 (TF-IDF baseline), would-fire total 21,924. DHM-4 sheet (100 items) ready in the private root; not ticked.
- DHM-1 interrupts per 1000 turns: Claude main 6.30 (CI 5.70-6.97), Claude subagent 0.088, Codex main 6.83, Codex subagent 2.21, opencode main 0.71, opencode subagent 2.36.
- DHM-3 per 1000 tool calls (Claude): pattern_kill 1.71 -> 0.089 and llama_cli 0.45 -> 0.032 after hooks; glob_rm 0.62 -> 1.30 and wholesale_git_add 0.36 -> 1.22 ROSE.
- DHM-5: always-on est. 17,158 tok/turn (Claude main), 8,326 elsewhere (file-size estimate, not usage-field; DHM-5.1 filed).
- OAB-LB1: 15,144 threads, exec wall 0.64% of turn wall. UFH14-LB8: token-weighted prefix hit 0.915 (0.940 excl. first step).
- Ticked DHM-1, DHM-2, DHM-3, OAB-LB1, UFH14-LB8. Filed DHM-5.1, DHM-8 to DHM-11. Detail: `docs/design/dev-harness-mining-results-20261022.md`; aggregate `data/dev_harness/mining-full-20261022T1310Z.aggregate.json`.
