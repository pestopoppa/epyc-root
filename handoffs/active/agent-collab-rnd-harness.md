# Agent-Collaboration Harness for Kernel/Orchestration R&D

> **Fold destination** (BRF-T1-F12, BRF-T1-1, route 1a, 2026-11-02): absorbs 1 handoff(s) as `## Track:` sections at the end of this file (`autokernel-restart-and-strip.md`). The body above the first track is the former `agent-collab-rnd-harness.md`.

**Status**: ACTIVE/PARTIAL — C6 scoring-integrity guard landed 2026-07-22; Phase 2/C4 remain open.
**Scratch**: `/mnt/raid0/llm/tmp/agent-collab-rnd-harness/` · worktrees: `/mnt/raid0/llm/worktrees/agent-collab-rnd-harness-*`
**Created**: 2026-07-11 (via research intake, operator-directed: apply collab model to kernel R&D + autopilot harness)
**Categories**: swarm_techniques, autonomous_research, agent_architecture, hardware_optimization

## Objective

Evaluate adopting the HF **agent-collabs** collaboration model (persistent shared workspace + backend-mediated central store + leaderboard + taskforces + layered quality gates + human dashboard) as the *mechanism* for running our **experimental-kernel R&D campaigns** (the v6→v7 optimization work that today runs as ad-hoc dispatched agents with no persistent shared workspace or leaderboard). The Gemma Challenge (intake-798) is structurally almost identical to our own work: a swarm optimizing inference-kernel throughput under a downstream-quality gate. Secondary target: the same substrate could host autopilot's harness-optimization loop as a population rather than a single daemon.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-798 | The Gemma Challenge and the Case for Agent Collabs | high | adopt_patterns |

Related existing work (do NOT duplicate — this stub is about the *collaboration mechanism*, those are the current mechanisms):
- [`meta-harness-optimization.md`](../completed/meta-harness-optimization.md) — single-daemon harness optimization (the autopilot-harness target).
- [`autopilot-continuous-optimization.md`](autopilot-program.md) — live autopilot loop.
- [`kernel-reconciliation-audit.md`](../completed/kernel-reconciliation-audit.md) / [`v6-iqk-promotion.md`](../completed/v6-iqk-promotion.md) — current experimental-kernel (v7-candidate) workflow.
- [`swarm-dataset-distillation.md`](../completed/swarm-dataset-distillation.md) — the other swarm handoff (dataset generation, different objective).
- [`halo-trace-loop-spike.md`](../completed/halo-trace-loop-spike.md) — trace sharing / attribution overlap.

## Open Questions

- Do we run our kernel R&D as isolated agent sessions today, or is there already a shared leaderboard/workspace? (If the latter, this is a smaller delta than it looks.) The collab's central value is the **persistent shared workspace + leaderboard + failed-trace reuse** — worth it only if our campaigns currently repeat dead ends across sessions.
- The Challenge ran on GPU-hosted E4B with challenge-defined gates. Our kernel R&D is CPU-first with `production-kernel immutability` + MEASUREMENT.md gating and a strict "experimental kernels only, never touch production" rule. Does a leaderboard-driven swarm respect those governance rails, or does it invite the exact metric-gaming the Challenge saw (their PPL gate was gamed until MMLU-Pro/GPQA layered on)?
- **Agent Collapse** is the headline risk: agents converged onto a narrow set of axes and *avoided custom quantization, large kernels, and engine changes* — which is precisely where our hardest CPU-kernel wins live. Any swarm we run must incentivize exploration of exactly the avenues their swarm skipped.
- Infra fit: could this reuse the existing handoff-dashboard hub (:8100) + a bucket/artifact store, or does it require the HF Buckets/Spaces/Jobs stack? (`opensource_only` / self-hosted constraint applies — the github.com/huggingface/agent-collabs template is a starting point, not a hosted dependency.)

## Notes

- Concrete transferable patterns from intake-798: layered/rotating quality gates (defeat metric-gaming), taskforces+channels (defeat collapse + message-flood), trace sharing (defeat repeated dead-ends), HITL dashboard to steer agents out of hopeless loops.
- All intake-798 numbers are OBSERVATION-grade (challenge-internal, self-reported); this stub is about the *organizational mechanism*, which does not depend on those numbers.
- Template referenced by the source: `github.com/huggingface/agent-collabs` (external, operator-review only — do not clone/run without approval).


## Research-intake integration — 2026-07-22 (R&D-harness patterns from orx / HyRA / OpenHyra)
_Via /research-intake Stage-2 (intake-882#record + intake-883#record orx, intake-884#record HyRA, intake-885#record OpenHyra). NOTE: the HyRA/OpenHyra R&D-harness descriptor + scoring items were routed here rather than to the meta-harness completed ledger, which forbids new task checkboxes (the active compatibility pointer was retired 2026-08-23)._
- [x] Compare OpenHyra's all-outcomes Experience Bank + LLM Context-Agent cross-round memory (`eb.py`, `context_agent.py`) against StructuralLab / agent-collab archive design ✅ 2026-07-22
- [x] Adopt a uniform per-task descriptor {seed/baseline solution, run script -> solution.json, fixed objective scorer, always-valid fallback} for the R&D harness (HyRA cross-domain contract) ✅ 2026-07-22
- [x] Feature-mine OpenHyra's trusted-evaluator-outside-sandbox + anti-TOCTOU immutable-snapshot scoring (`sandbox.py:80-134,255`) as a reusable scoring-integrity pattern (general R&D-harness version of the C6 kernel-loop item in [rocm-verify-profile-backend.md](rocm-verify-profile-backend.md)) ✅ 2026-07-22 (research `2d5b1f6e`; `kernel_rnd/c6_reward_integrity.py` and task descriptor)
- [ ] (Optional spike, gate on operator interest) Point orx at EPYC's llama.cpp via OpenCode as a DISPOSABLE test vehicle (`--backend local`, custom OpenAI provider in `~/.config/opencode/opencode.json`) to validate the loop end-to-end. NOT a harness commitment — mining orx's patterns is unconditional and re-targeting to our eventual chosen harness is ~1 `impl Harness` file (`src/local/harness/mod.rs:1135`). Gate any long-term harness choice on [harness-selection-and-integration.md](harness-selection-and-integration.md) **Constraint if ever authorized:** SINGLE-USER only on this shared host (orx's own README states the dashboard binds loopback with no application-level authentication, so other host users can reach it), and built from source (channel development) so telemetry is compile-time disabled. Strip overleaf_live / browser_cookies at import (intake-883#record).
- [ ] (Optional spike) Add a 3rd OpenHyra llm_backend adapter (~30-60 LOC) targeting a local OpenAI-compatible coding agent -> llama.cpp; needs `OPENHYRA_ALLOW_UNSANDBOXED=1` + an external container (sandbox is macOS-only)
- [x] **S3-ACH-01 — spike a PreToolUse read-only allowlist gate for planner/critic actors.** An actor may inspect evidence freely but cannot launch a build or benchmark until authorized. Classification is allowlist-only (unknown ⇒ gated), with a test asserting every allowlisted verb names a real command. Gates the ACTION, not the outcome: both our loops gate at promotion, so a misfiring planner can spend GPU-hours before a human sees a decision. Pattern: orx plan_gate, intake-883#record @3a8b0286. ROOT source `9414032c93e3a9ea0247bcab9f5158877ca6724a` (published main through `00ceac9c331a9b085f1b9169cbe24083e245b81f`); Git tests `scripts/hooks/tests/test_planner_readonly_gate.py` (6 passed), evidence `artifacts/codex3/s3ach01-20261031/`. ✅ 2026-10-31 [no-belief: source prototype and regression controls]
  - Default-off opt-in prototype with fixed trusted `planner` / `critic` CLI seats; strict Read/Glob/Grep schemas and Bash only for literal absolute `/usr/bin/cat`, with unknown requests asking for approval. Six focused tests passed against native JSON and controlled cat; host crash/missing/timeout/invalid-JSON behavior is simulated, not a live Claude session. Enablement still requires Claude Code ≥2.1.295, host-protected hook/settings/interpreter, and interactive approval. No live host enablement or blanket sandbox/security claim.

## Fan-out A/B design constraints — 2026-08-13 (research-intake Stage 3, source round intake-1105…intake-1127)
- [ ] **Hard design constraints on any first-party fan-out A/B, fixed before one is built.** (a) Matched cost axis on the same plot; result shape is a Pareto frontier, not a bar — intake-1120 (arXiv:2407.01502v1, dive-verified), whose trivial warming baseline matched the best agent architecture at >50x less cost than the most expensive arm. (b) A simple-baseline CONTROL ARM (retry-to-N, warming) at equal spend, or the fan-out arm is unfalsified. (c) PAIRED within-task design with task as a random effect — intake-1122#01 (arXiv:2604.22750v2, dive-overturned) shows cross-problem token variance dwarfs cross-run variance, so an unpaired design measures task sampling rather than fan-out. (d) Our cost axis is not dollars: define GPU-seconds + total tokens + wall-clock and always record tokens so the axis stays re-derivable. Note on (c): that source's "up to 30x" is a TOKEN tail, typical ratio ~2x, and it prescribes no minimum n — do not cite it as a variance gate.

## Research-intake update — 2026-09-07 (execution-alignment failure triage)
- [x] **Adopt the five execution-alignment symptoms as our agent-run failure triage label set** — contract/format, tool/recovery, evidence/grounding, artifact commitment, state/continuation (intake-1332#03, dive-verified). Cross-link **MHS-5** in [promptforge-mutation-safety-contract.md](autopilot-sequential-allocation.md#track-promptforge-mutation-safety-contract): the meta-harness stub trains harness edits from exactly this kind of failure trajectory. The **label set** is the durable part and is independent of every defect the dive found in that source's published rates. Zero compute.

## Research Intake Update — 2026-09-17 (CORAL / SwarmResearch harness mechanisms, intake-1439…1455)

_Via /research-intake Stage 4 (operator-approved plan 2026-09-17). Sources dive-verified; external numbers motivate, never gate._

- [ ] **AC-CORAL — pin CORAL v0.7.20 (`bbae4f72`) and spike the shared-state design against orchestrator `/v1`.** Install via pinned tag; point opencode/codex runtimes at `/v1` (baseURL or embedded LiteLLM gateway); evaluate `.coral/public` shared state (attempts/notes/skills + heartbeat reflect-1/consolidate-10/pivot-5) as the persistent-workspace mechanism for kernel R&D against the current ad-hoc dispatch baseline (equal-spend control per the fan-out A/B constraints above). Sources: intake-1449, intake-1455.
- [ ] **AC-branch-per-agent — draft the SwarmResearch-pattern search-harness spec.** Branch+worktree per search agent, fresh-context explorers, lineage findings.md, shepherd global context, width/depth adaptation with explicit spawn telemetry; reuse the released repro harness (intake-1450) as trial substrate where useful. Sources: intake-1439, intake-1450, intake-1444.

### Proposed operational follow-through — 2026-10-04 earlier-intake retrospective

**Implementation boundary:** at most three eligible, existing configurations on the same actor/model/backend. Reuse completed-batch continuation (`serial_run.py`), actor-call capture and native journals. Give each configuration its own experimental worktree/store/continuation; pooled lanes sharing one advancing champion are not independent trajectories. Bind exact argv/effective configuration, prefix-visible score, cumulative cost, continuation reference and alive/pruned state. No arbitrary mid-call checkpoint system. OAB-9b forbids an unchanged inline-versus-variable rerun; DS41-C20 already covers plain-versus-bounded. Do not disguise either as a new portfolio. Use supported recorded trajectories or configurations with an actual changed eligibility condition; if fewer than two eligible comparable arms exist, return unsupported rather than launch a new campaign. An actor-seat change is not a stable-resume exclusion: maintain separate continuations instead of assuming it can be switched in place.

- [ ] **AC-CHECKPOINT-ALLOC — Implement and screen prefix-visible checkpoint-pruned allocation over a small frozen R&D harness pool.** PROPOSED, not execution/activation approval. The September 17 mapping assigned this outcome to AC-branch-per-agent, but a collaboration spec does not compare allocations. At the existing candidate/run-record and selector-replay seams, compare the pruned pool with matched incumbent repetition, unpruned diversity and simple repeated sampling on one nonpromotable workload. Freeze only presently supported actor/selector/context configurations, current evaluator/model/policy revisions and paired run/input identities; change allocation, not each arm's internal policy. Decisions may inspect only checkpoint-prefix progress. Use complete recorded continuations where available; missing or scheduler-dependent counterfactual continuations remain unsupported, never inferred from a selected parent's outcome. If the recorded pool cannot support the comparison, report the exact missing native fields and capture the smallest prospective paired pool through the existing isolated run harness rather than creating a new framework or fabricating a replay. Bind matched model-call, token, evaluator and wall budgets; charge failures, invalids, abstentions and pruning overhead. Retain per-run raw outputs and all dispatched outcomes; separate endpoint quality from anytime frontier. Choose checkpoints/pruning on a calibration prefix and freeze an untouched later seed/run holdout before scoring. Predeclare the stopping rule: no follow-on without correctness-preserving held-out improvement beyond local uncertainty at matched cost; incomplete support returns unavailable. Implement against fixtures first; any prospective inference/hardware run requires the normal campaign/resource authorization and VB-RI-OPS-WIRE's write-side capture. A positive screen warrants a separately reviewed bounded follow-on, not live allocation or kernel promotion. [Evidence and counter-coverage](../../docs/reviews/research-intake-earlier-applications-20261004.md); record discussion: intake-1444#record.

## Research Intake Update — 2026-09-25 (ALE private evaluation)

**ACH-ALE-1 trigger record — private grader for a selected ALE-style campaign.** Activate only when the shared `SEQ-SHINKA-1` / `AP-DGM-SEL` replay beats matched simple controls, or a live long-horizon engineering campaign requires ALE-style evaluation. Then run private grading in a separate process or service with inaccessible instances, seeds, and standings, immutable one-shot receipts, and a non-resettable private-call budget. The search process may consume only the returned verdict; it may not inspect or tune against hidden cases. Until the trigger fires this record creates no active grader service or campaign. Sources: intake-1597#record, intake-1598#record, intake-1599#record.

✅ 2026-10-06 MAIN adopted the [closed triage metadata contract](../../docs/reference/agent-run-failure-triage.md), explicit unknown and non-exclusive semantics, with MHS-5 cross-link. Documentation only; no rates, classifier, score or runtime ErrorCategory changes.

## Track: autokernel-restart-and-strip
<!-- gate: none -->

> Folded from `handoffs/active/autokernel-restart-and-strip.md` @ `052ae9dd8748` on 2026-11-02 (BRF-T1-F12, route 1a, operator D1/D5; retired row INF-64 → INF-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### AutoKernel — restart-loop fix, v28 launch, and the dead-weight strip

> **NI08 source-only start here — 2026-10-07:** the [completed per-file manifest](../../artifacts/ni08/inf64-source-reachability-review-20261007/completed-manifest.md) retains all19 candidate/test units. The next bounded source gate is `VB-INF64-REACHABILITY-CONFORMANCE` in the [belief program](vidya-belief-substrate-program.md); it grants no runtime reachability or deletion authority. The dated launch and benchmark history below does not establish current live campaign state. Campaign execution remains with its owner.

**Owner:** operator audit session (2026-08-27), which now holds GPU compute.
**Code branch:** `lane/autokernel-restructure-20260827` in **epyc-inference-research**
(the code fixes live there; this rider lives in epyc-root with the rest of `handoffs/`).
**Trigger:** operator audit — v27 crash-looped ≥9× in 48h, 0 scientific attempts across every
campaign v3→v27, GPU held with nothing to show.

This is a rider on [`autokernel-research-loop.md`](autokernel-research-loop.md); it does not
re-open that handoff's backlog. Owning index row: **INF-06** in
[`inference-research-index.md`](inference-research-index.md).

#### LAUNCHED — v28 live under audit-session GPU ownership (2026-08-27T14:23Z)

Operator granted GPU compute to this session and directed latching autokernel. **v28 is running
the fixed code**, latched (`--max-restarts 1000`, supervisor auto-restarts + resumes from durable
state). Deployment `gpu-discovery-quant-ladder-occupancy-v28`, config `659e356d`, tmux session
`ak-fb097bfd6ee7a8e58c108430` (socket `epyc-autokernel-supervisors`), supervisor pid 1698290,
execution closure `89de3a8a…` (verified to contain the sampler `owner_root_pid` fix and the
lifted restart clamp). First iteration reached `planner_started` on `akh-v2-q5-type-specific-dequant`
within seconds — clean, no crash.

- Monitor: `/mnt/raid0/llm/autokernel/monitor-v28-audit.sh` → `…/v28/monitor-audit.log`
- Graceful stop: `discovery_supervisor stop --runtime-root …/v28/state`. Never `pkill`.
- **The MI210 is owned by this campaign** — it takes the `gpu_device.mi210_0` flock per screen.

#### Fixed this session (all committed + unit-tested; suite fully green, 779/779)

- [x] **Planner backoff** — consecutive `PlannerProviderTransient`s back off exponentially
  (30s → 1800s), checkpoint-before-wait, streak surfaced as `operator_attention` (non-terminal),
  cleared on first success. Kills the 284-failures-in-23-min spin (codex 401, 08-26). ✅ 2026-08-27
- [x] **Actor timeout** — `codex_container_actor.run_actor(timeout=1800)` bounds one invocation
  (v27 had none, so a hung container held the turn forever). ✅ 2026-08-27
- [x] **Transport→transient** — docker/timeout/staging failures reclassified as
  `PlannerProviderTransient` instead of escaping as terminal controller faults. ✅ 2026-08-27
- [x] **Restart clamp lifted** — removed `max_restarts==0` for `kind==deployment` (commit
  `f13434e3`) that made every crash a permanent exit and the OPERATOR the restart loop. The
  controller already resumes from durable state, so a supervised restart IS a resume. ✅ 2026-08-27
- [x] **KFD sampler self-flagging + no wait-out** (caused 4 of 11 v27 crashes). `_belongs` only
  accepted descendants of the *sampled leg*, so the controller's OWN sibling (crash #10, pid
  964901) was "foreign"; sampler now takes `owner_root_pid`. Added `wait_until_clear()` wired as
  `SubprocessCommandExecutor(preflight_clear=…)` so a timed leg never opens on a contended GPU —
  foreign work is waited out, then a clean `GpuContentionTimeout` leg-refusal. ✅ 2026-08-27
- [x] **Worktree name collision on crash-orphaned branch** (crash #6). `create_campaign_worktree(
  prune_orphan_branch=True)` deletes the DEAD orphan ref only — guarded by
  `GitRepo.checked_out_branches()` and `SafeBranch`. ✅ 2026-08-27
- [x] **Rotted Claude critic pin** (discovered at launch; blocked EVERY new deployment).
  `_SITE_CRITIC_WRAPPER` pinned `claude/versions/2.1.231`, orphaned by Claude auto-updates
  (2.1.238/240/241 installed) — every bundle init died with `FileNotFoundError`, and it was also
  the cause of the 3 "pre-existing" test failures. Now resolves the stable launcher. ✅ 2026-08-27
- [x] **Stopped v27 and reclaimed disk** — supervisor/factory/build/watcher/kfd-watchdog
  terminated by captured PID and verified dead; 144/146 worktrees removed (2 handoff-referenced
  kept), dirty state backed up to `/mnt/raid0/llm/autokernel/reclaim-20260827/`. Free space
  371 G → 589 G. ✅ 2026-08-27

#### Open

- [x] **v28 reached a real screen disposition — `scientific_attempts: 1` at 15:19Z.** The milestone
  no campaign v3→v27 ever reached, achieved ~56 min after launch. ✅ 2026-08-27
  - turn 1 `authoring_refused` — critic caught a diff deriving undeclared file-scope symbols in
    `vecdotq.cuh` (a legitimate gate, costs no science budget).
  - turn 2 `inconclusive` on `akh-v2-q5-type-specific-dequant`: exact attribution
    **+0.129 %**, target runtime **−0.015 %** → conjunctive rule (either ≤ 0 → inconclusive).
    A null result, recorded with evidence. Receipt `34f836cc…`, sealed at
    `operations/941c8fde…/screen-result.json`.
  - Both arms proved real GPU residency: anchor KFD pid 3623562, candidate 3623486, both exit 0,
    through admission → correctness → attribution → graphs-off measurement → graphs-on runtime.
  - **Zero crashes** (1 `child_started` = the initial launch), no transient streak, no
    operator-attention flag. Loop advanced to turn 3 by itself.
  - This is the end-to-end on-real-hardware confirmation the GPU-path fixes needed: two arms ran
    back-to-back with distinct KFD pids and neither was misflagged as "foreign" — the exact
    condition that caused 4 of the 11 v27 crashes.
- [ ] **Let the campaign run to its disposition budget** (`max_iterations: 100`, ~35 min/iteration
  ⇒ multi-day). Monitor wakes the owning session on a science increase, a crash, or a genuine
  stall. No action needed unless it wakes.
- [x] **Re-screen the 19 historically proposed deletion modules individually and strip only proven-safe files** (10,500 LOC + 19 test files ~4,870 LOC +
  `c5_rocm_oracle.json`). Deletion MUST regenerate `FOOTPRINT.md` in the same commit
  (`python -m …controller.test_campaign_footprint --refresh`) — it is asserted by
  `test_campaign_footprint` / `test_readme`. Do NOT touch the HOLD sets (arena/hip/loop/
  least-commitment producers wired into vidya adapters + dashboard; `campaign.py` importees;
  `scripts/benchmark/` runners).
  Historical 2026-08-27 audit claimed unreferenced status across research, `/workspace`, and
  `epyc-orchestrator` — the earlier "40K LOC dead" figure was WRONG (the static grep missed
  `campaign.py`'s parenthesized import and the `scripts/benchmark/` runners; 51 of 82 candidates
  are live): `c5_rocm_oracle` · `controller/completed_campaign_adapter` ·
  `controller/gpu_hot_residency_runner` · `controller/reward_monitor` · `evaluator/baseline_honesty` ·
  `evaluator/c3_apex_runner` · `evaluator/c3_epyc_capture_provider` · `evaluator/c3_epyc_compiler` ·
  `evaluator/c3_epyc_suite` · `evaluator/c3_epyc_tensor_capture` · `evidence_path_rehearsal` ·
  `heldout_bound_pipeline` · `least_commitment_archive_builder` · `least_commitment_receipts` ·
  `offline_least_commitment` · `placement_context` · `prepare_iqk_matched_pair` · `substrate` ·
  `turn_productivity`.
  ✅ 2026-10-25 — current-pin individual re-screen complete: 19 retained, 12 positive-edge, 7 intentional off-path with runtime invocation unestablished, 0 proven obsolete, 0 deletions proposed. See [docs/reference/cme7t-inf64-accepted-findings-20261025.md](../../docs/reference/cme7t-inf64-accepted-findings-20261025.md). [no-belief: committed conclusion prepared; register capture not yet applied]
  - 2026-11-02: the HOLD note above on the least-commitment producers and `campaign.py` importees is moot: research `753639bd1` deleted that cluster (C5-05, operator decision 2026-11-02). [no-belief: tooling]
  - 2026-10-25 (Codex NI T1; canonical ROOT 249855e78 / research e8d57acd / orchestrator 49c1f749): all 19 source blobs match the accepted matrix. 12 retained for positive source/CLI/consumer edges; 7 retained as intentional off-path contracts with current runtime invocation unestablished. Zero proven obsolete and zero deletion candidates. Detailed module matrix and source/test/data hashes: [docs/reference/cme7t-inf64-accepted-findings-20261025.md](../../docs/reference/cme7t-inf64-accepted-findings-20261025.md) and task-local INF-64-REPORT.md SHA-256 94ad54ced756508606eb508a48dec964e2b1e480154870a400973a6efee2073c. No inference, GNX deletion clearance, native-control pass, runtime absence, or deletion-safety claim.
- [ ] **Add build/runtime disk expiry.** `deployments/*/builds/` (14 G) + `runtime/` (4.4 G) are
  pinned by `materialization.json` digests; `storage.expire_artifact` has zero callers. Also run
  `_recover_incomplete_attempt` at controller start for ALL incomplete attempts, not only on
  re-proposal (that is why 6 orphan worktrees survived). Not a crash — disk growth.
- [x] **Merged `lane/autokernel-restructure-20260827` to research `main`** — future launches now get
  the fixes by default. Promoted via the isolated-worktree pattern (never the shared clone, which had
  1,212 dirty files from other sessions); research `origin/main` = `01f1d2be`, with `owner_root_pid`
  verified present in the sampler on main. ✅ 2026-08-27
- [x] **Reconciled the epyc-root divergence** (operator-directed). Local `main` 17 ahead / 11 behind
  `origin/main` had been blocking EVERY session's wrap-up push all day, not just this one. Merged in
  an isolated worktree; the single conflict was the **generated** master-index rollup, resolved by
  regenerating from the merged tree (yielding a third value, `52 | 472` — proof that regeneration,
  not side-picking, was correct). Superset-verified, then 18 commits published to `origin/main` under
  the push lock; never forced. ✅ 2026-08-27
  - Residual, benign: the shared clone cannot fast-forward while a peer's uncommitted
    `wiki/knowledge-management.md` is also changed upstream (git aborts atomically; peer work
    untouched). It is `ahead=0`, so nothing is unpublished. Until that file's owner commits or
    discards it, sessions committing to `main` there will re-diverge; the working pattern is a
    detached worktree at `origin/main` → commit → serialized push.

Not live at HEAD (closures already refactored these away — do not re-add): preauthored-provenance
raise, C6-admission path-embedded identity, C6-policy-refusal-as-crash. If they reappear:
provenance drift → log+continue; admission identity → hash CONTENT not the closure path; a C6
policy verdict is a SCREEN DISPOSITION (falsified/refused row), never an exception.

#### The deeper finding (for the operator — a design question, not a task)

The loop is ~15-40 lines of real measurement (`microbench.parse_llama_bench_json` → compare) inside
~278K LOC of custody scaffolding: "receipt" appears 2,735× in non-test source, "authority" 824×,
"seal" 753×. The month's commit stream is ~49:1 governance-to-science, and the last 15 commits were
all one subsystem (build-supervisor authority/crash-recovery) rewriting itself. The manual method
that produced the §22 occupancy-cliff finding was two `llama-bench` invocations + a markdown table.
The constitution requires the custody at CLAIM time (P-GPU-1), not at EXPERIMENT time — a screening
run that is wrong just gets refused later. Long-term the discovery loop should be re-scoped so the
sealed apparatus wraps the *promotion* boundary and the *screening* loop is thin. Filing that as a
task would be premature: it needs an operator design session, not an implementer.


#### 2026-08-28 — the planner was never told why its diffs were refused

Investigating why v33 hit the identical authoring refusal on two consecutive turns.
Root cause found, fixed and merged (research `9516ac05`); two follow-ups filed below.

**The defect.** `prior_authoring_refusals` — the channel that tells the planner why its
previous diff was rejected — filtered on `status == "planner_refused"`. The status actually
written for a rejected diff is `authoring_refused`. Real tally across campaigns v28–v34:

| status | occurrences |
|---|---:|
| `authoring_refused` | **22** |
| `planner_refused` | 1 |

So for **22 of 23** authoring failures the planner got no feedback and re-derived rejected work
blind. The field's own name said `authoring_refusals` while its predicate excluded the status of
that name.

**Measured consequence (v33, `akh-v2-q5-type-specific-dequant`):** turns 2 and 3 produced two
*different* diffs (distinct `operation_key`s) with a byte-identical refusal — `committed diff in
'ggml/src/ggml-cuda/vecdotq.cuh' derives undeclared symbols ['<file-scope>']`. Those strikes hit
the 3-strike `bounded_authoring_skip`, retiring the hypothesis for the campaign **without ever
testing it**. v34 reproduced it: `authoring_refused` on turn 1. Fixed and relaunched as **v35**.

**What the investigation CLEARED.** My initial suspicion — that the do-not-repeat ledger was
failing to suppress re-proposals — was **wrong**. The ledger and the bounded-skip are correct:
`portfolio_authoring_failures` reached 3, the hypothesis was skipped with
`scientific_terminal: false` (campaign-scoped, not permanent), and provider transients are
explicitly excluded from the count, as they should be. The ledger was fine; the planner was blind.

- [x] **AK-VIS-1 — authoring refusals rendered as NOTHING on the command band.** ✅ 2026-08-28
      (epyc-root `2cc984a7`). **My first diagnosis of this was wrong and is corrected here.** I
      filed it as a telemetry-event gap; the real mechanism is the status→label map in the live
      payload. `refusal.detected` is `refusal_type is not None`, and `authoring_refused` was absent
      from that map — so the whole refusal block (type, stage **and** the `detail` carrying the
      guard's message) was skipped. The map did contain
      `planner_contract_refused -> "authoring_refused"`, emitting the LABEL while never matching
      the status of that name, which is why it survived review.
      Added `authoring_refused` plus `authorization_refused`,
      `candidate_semantic_repeat_refused` and `portfolio_dnr_refused`; `kernel.html` now renders
      `refusal.detail`, so the card shows *why* ("derives undeclared symbols in vecdotq.cuh")
      rather than a bare "refused". The server already computed it.
      **A secret boundary was nearly weakened and was not:** the first attempt also surfaced the
      raw iteration `reason`, which `test_v2_planner_refusal_is_typed_secret_free_and_advances`
      correctly failed — a `planner_refused` reason can carry raw actor stdout, which is why that
      path ships only a digest. The change was reverted rather than the test weakened.
      Regression test drives the real payload path; its first version was vacuous twice over (a
      local copy of the map, and a source grep matching unrelated lines) and was rewritten until
      the mutation actually fails. Failure SETS diffed against origin/main: 0 newly broken.
- [x] **AK-VIS-2 — `critic_revise` consumed an authoring-failure strike.** ✅ 2026-08-28
      (research `26f587a9`). A critic asking for a revision is the mechanism by which a proposal
      improves; charging it to the same 3-strike budget as a malformed diff retires hypotheses for
      being reviewed. It supplied v33's third strike, skipping
      `akh-v2-q5-type-specific-dequant` without it ever being tested. Revisions now have their own
      larger budget (`CRITIC_REVISION_BUDGET` 6 vs `AUTHORING_FAILURE_BUDGET` 3) and their own
      disposition `bounded_critic_revision_skip`, so the two are distinguishable in state; both
      stay `scientific_terminal: false`. A critic **reject** deliberately still counts — the
      proposal was judged unsound, not merely improvable. Tests replay v33's exact sequence and
      are mutation-tested.


#### 2026-08-28 — v36 died at preflight: the champion-as-instrument ruling was refused in code

The dashboard reported `stalled`; it was not a stall. Campaign **v36 was dead** — supervisor gone,
4 turns, **0 scientific attempts** — and the real cause was in the live payload the whole time:

```
RuntimeError: shared source-discovery reward requires the exact sealed 81bf32f11
timed-output instrument
```

A hard preflight refusal on **every** attempt, not a slow stage.

**CH-3 and the runner were in direct contradiction, and the runner won silently.** CH-3 made the
aggregate champion the campaign's instrument so gains compound. But two gates in
`run_autokernel_gpu_discovery.py` compared the anchor arm's source commit for **equality** against
`READY_CONTINUE_INSTRUMENT_COMMIT` (`5bbcc5498`, the original reviewed instrument). A
champion-instrumented campaign can never satisfy equality, so every campaign since the re-pin was
refused before it could do any science. This is the mechanism behind v33–v36 all ending at 0.

**Fixed by accepting the instrument LINEAGE** (research `23e9be47`). What the gate protects is that
the timed-output oracle carries the reviewed measurement apparatus, and a descendant does: the
champion is built ON the instrument (its own review receipt enforces the delta) and
`tests/test-autokernel-ready-continue-contract.py` is **byte-identical** between `5bbcc5498` and
champion `270b48ed6` — which `READY_CONTINUE_CONTRACT_SHA256` pins independently. Ancestry plus
that unchanged contract blob is the same guarantee equality gave; equality merely also forbade the
champion. **The gate keeps its teeth**: frozen production v9 predates the instrument and is still
refused, asserted rather than assumed.

- [x] **AK-INST-1 — the timed-output gates must accept a champion instrument.** ✅ 2026-08-28
      (research `23e9be47`). Mutation-tested: collapsing the helper back to equality fails
      `test_a_champion_built_on_the_instrument_is_accepted`. Suite 56 passed, including the
      pre-existing assertion that the guard still raises for a non-instrument anchor. The git tree
      is resolved from `--anchor-build` (the path `build_identity` already runs `git -C` in);
      a first attempt used a non-existent `--instrument-path` argument and would have thrown.
- [x] **AK-MSG-1 — make the authoring-refusal message actionable.** ✅ 2026-08-28 (research
      `4d2fa807`). The journal line read `derives undeclared symbols ['<file-scope>']` — naming a
      "symbol" that exists nowhere in the source, omitting what the proposal DID declare. Three
      audiences read it and none can ask a follow-up: the planner (fed back since `9516ac05`), the
      dashboard command band, and a human. It now states what changed, what was declared, and that
      `<file-scope>` means a hunk outside any function body.
- [x] **AK-INST-2 — audit for OTHER hardcoded instrument pins.** ✅ 2026-09-23 — audited every 40-hex / `*_COMMIT` comparison in the discovery plane: no other champion-drift pin (the rest are exact freeze/seal/vendor/replay identities or already ancestry checks). It surfaced a DIFFERENT v10 defect, fixed in research `714777e4`: with `MEASUREMENT_COMMIT == PRODUCTION_COMMIT` the "instrument parents == (production,)" rule was unsatisfiable in `live_controls` preflight AND `candidate_record.build_candidate_record` — shared `worktree.instrument_lineage_ok` now accepts the folded identity. The review-pin at `discovery_deployment_factory.py:1516` stays EXACT by design (re-pinned per freeze). `READY_CONTINUE_INSTRUMENT_COMMIT`
      was found only because it killed a campaign. Any other equality comparison against a fixed
      instrument/production commit will fail the same way the next time the champion advances.
      Grep the discovery plane for 40-hex constants compared with `==` and convert the ones that
      mean "descends from the reviewed instrument".

#### 2026-08-28 — dashboard deployment gap (the reason four fixes were invisible)

At the time, landed dashboard code never reached the served tree: the hub served `${EPYC_ROOT}` directly and
that tree sat **35 commits behind** origin/main. The current hub instead serves the read-only full-tree view described under AK-DEPLOY-2. Separately, `cmd_loop` called neither the sync nor
the pre-existing `check_hub_stale_source` — both ran only in `cmd_once`, the cron-style one-shot
nobody invokes. The staleness watchdog was correct and simply unreachable on the path in use.

- [x] **AK-DEPLOY-1 — the supervisor deploys landed dashboard code and restarts the hub.** ✅
      2026-08-28 (epyc-root `2dbf5dc1`, `7adc4127`, `fc9502ab`). Proven live: the served file was
      reverted by hand and the supervisor repaired it unattended, then restarted the hub. Three
      safety rules, each mutation-tested — never writes the git index, never overwrites work in
      progress, never moves the branch or pushes; scope is `dashboard/` only.
      **The predicate took three attempts and the first two failed by looking like success**:
      comparing to local HEAD calls every correctly-deployed file a hand edit, because the served
      tree deliberately lags. It now judges by PROVENANCE — a blob this project has published for
      that path is a deployment; one that never existed on origin/main is someone's work.
- [x] **AK-DEPLOY-2 — reconcile served-tree drift outside `dashboard/`.** ✅ 2026-10-27 — The operator-approved dedicated read-only view advances the entire served tree to origin/main, including handoffs, scripts and progress. `refresh_hub_view.sh` requires a marked standalone view and refreshes generated handoff artifacts; the shared working tree is not its deployment target. The former dashboard-only scope remains the fallback for a non-view tree.

      Live verification at 19:31 UTC: hub PID 1899355 served `/mnt/raid0/llm/views/epyc-root-main`; its detached HEAD and origin/main were `b3ef3eb2a011e0edd9cc06a3a5690d63d0b88a73`, with clean porcelain. The historical stale champion handoff matched published blob `07c828776d18566814a3ada697371d7e0af50f98`. The supervisor log recorded a successful refresh to that commit at 19:22:24 UTC with regeneration, and an unchanged successful refresh at 19:30:02. `/api/handoff_board` returned 200 and included this handoff; `/api/health` reported the board fresh, observed and populated. The hub started 2026-10-24 08:50:27 UTC after the served `dashboard/server.py` mtime 08:50:03; its source derives handoff paths from the served module tree. This closes the full-tree drift issue, not unrelated producer health findings. [no-belief: operational liveness and deployment observation]

      **Historical evidence (2026-08-28):**

      **Measured 2026-08-28, and it is worse than "lagging".** The served tree's local `main` stood
      **45 behind / 1 ahead** of origin/main, and carried
      `handoffs/active/kernel-champion-and-promotion.md` as an **untracked 144-line file where
      origin/main has 465 lines** — a superseded draft occupying the authoritative path. It read as
      untracked only because local `main` predates the commit that added it. Every substantive
      passage was verified present in origin/main's version before the stale copy was displaced
      (backup: `/mnt/raid0/llm/tmp/champ_aggregate_stale_worktree_20260828.md`). The one commit
      ahead was another session's completed-but-unpushed work.
      So the failure mode is not just staleness: **a stale untracked file is indistinguishable from
      live uncommitted work**, and the dashboard reads handoffs. Whatever is decided, it must
      distinguish those two cases — the AK-DEPLOY-1 provenance predicate is the existing pattern.
- [ ] **AK-INST-3 (new, 2026-08-28) — AK-INST-1 is fixed in code but UNPROVEN end-to-end.** The
      lineage helper is unit- and mutation-tested, but no campaign has yet ridden it to a
      scientific attempt. v37 reached `sci=0` and was stopped deliberately (champion work had to
      finalize first, per the operator's standing sequencing rule), so the whole point of the
      fix — a champion-instrumented campaign passing preflight and spending screen budget — has
      never been observed. Relaunch against the finalized champion and watch to `sci >= 1`;
      **do not record AK-INST-1 as validated until a campaign banks a real screen.**
      - 2026-11-01 audit: current C5 descends from the reviewed instrument and retains its contract hash, but the latest witness remains `sci=0`. The champion launch hold permits only CH-27; AK-INST-3 needs a separately authorized campaign and a real screen. [Audit](../../artifacts/coordination/ni-post-a2-wrap-20261101/AK-INST-3-AUDIT.md). [no-belief: read-only source and scheduling audit]

#### 2026-10-07 current-source deletion-premise correction

MAIN independently reopens Research01d36835 and confirms three noncandidate loop imports of `evaluator/c3_epyc_tensor_capture.py`, the compiler's dynamic Apex entry, and the documented least-commitment producer family. ROOT also carries a cross-repo expected-inventory consumer. The historical19-dead assertion is superseded; paired tests being proposed for deletion do not prove their dependency dead. [Exact path/blob/importer matrix](../../artifacts/ni08/inf64-source-reachability-review-20261007/importer-path-entrypoint-matrix.md) identifies retained modules and the remaining dynamic/path/HOLD/entrypoint checks. No deletion, frozen-kernel edit, live campaign interference or native reachability proof occurred.

- [x] **INF64-REACHABILITY-MANIFEST — complete the per-file source reachability/disposition manifest before any deletion proposal.** Bind exact19 candidate paths, adjacent data and paired tests; resolve non-Python/dynamic entrypoints, string/CLI/config references, cross-repo capture inventories, FOOTPRINT/HOLD ownership and outgoing edges. Retain actual loop/compiler/least-commitment consumers; only prepare removal of individually proven-safe files together with their explicit dependent tests/data and regenerated footprint guards. Existing campaign owner applies any source change at its boundary.


✅ 2026-10-07 INF64-REACHABILITY-MANIFEST: [MAIN completed19-row conservative source audit](../../artifacts/ni08/inf64-source-reachability-review-20261007/completed-manifest.md),64unique source blobs/145exact incoming refs plus outgoing imports/path/CLI edges. All19retain; none cleared for deletion. Existing strip/owner boundaries and prospective native controls remain separate.
