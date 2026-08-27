# AutoKernel — restart-loop fix, v28 launch, and the dead-weight strip

**Owner:** operator audit session (2026-08-27), which now holds GPU compute.
**Code branch:** `lane/autokernel-restructure-20260827` in **epyc-inference-research**
(the code fixes live there; this rider lives in epyc-root with the rest of `handoffs/`).
**Trigger:** operator audit — v27 crash-looped ≥9× in 48h, 0 scientific attempts across every
campaign v3→v27, GPU held with nothing to show.

This is a rider on [`autokernel-research-loop.md`](autokernel-research-loop.md); it does not
re-open that handoff's backlog. Owning index row: **INF-06** in
[`inference-research-index.md`](inference-research-index.md).

## LAUNCHED — v28 live under audit-session GPU ownership (2026-08-27T14:23Z)

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

## Fixed this session (all committed + unit-tested; suite fully green, 779/779)

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

## Open

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
- [ ] **Strip the 19 verified-dead modules** (10,500 LOC + 19 test files ~4,870 LOC +
  `c5_rocm_oracle.json`). Deletion MUST regenerate `FOOTPRINT.md` in the same commit
  (`python -m …controller.test_campaign_footprint --refresh`) — it is asserted by
  `test_campaign_footprint` / `test_readme`. Do NOT touch the HOLD sets (arena/hip/loop/
  least-commitment producers wired into vidya adapters + dashboard; `campaign.py` importees;
  `scripts/benchmark/` runners).
  Confirmed unreferenced by a two-pass AST audit across research, `/workspace`, and
  `epyc-orchestrator` — the earlier "40K LOC dead" figure was WRONG (the static grep missed
  `campaign.py`'s parenthesized import and the `scripts/benchmark/` runners; 51 of 82 candidates
  are live): `c5_rocm_oracle` · `controller/completed_campaign_adapter` ·
  `controller/gpu_hot_residency_runner` · `controller/reward_monitor` · `evaluator/baseline_honesty` ·
  `evaluator/c3_apex_runner` · `evaluator/c3_epyc_capture_provider` · `evaluator/c3_epyc_compiler` ·
  `evaluator/c3_epyc_suite` · `evaluator/c3_epyc_tensor_capture` · `evidence_path_rehearsal` ·
  `heldout_bound_pipeline` · `least_commitment_archive_builder` · `least_commitment_receipts` ·
  `offline_least_commitment` · `placement_context` · `prepare_iqk_matched_pair` · `substrate` ·
  `turn_productivity`.
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

## The deeper finding (for the operator — a design question, not a task)

The loop is ~15-40 lines of real measurement (`microbench.parse_llama_bench_json` → compare) inside
~278K LOC of custody scaffolding: "receipt" appears 2,735× in non-test source, "authority" 824×,
"seal" 753×. The month's commit stream is ~49:1 governance-to-science, and the last 15 commits were
all one subsystem (build-supervisor authority/crash-recovery) rewriting itself. The manual method
that produced the §22 occupancy-cliff finding was two `llama-bench` invocations + a markdown table.
The constitution requires the custody at CLAIM time (P-GPU-1), not at EXPERIMENT time — a screening
run that is wrong just gets refused later. Long-term the discovery loop should be re-scoped so the
sealed apparatus wraps the *promotion* boundary and the *screening* loop is thin. Filing that as a
task would be premature: it needs an operator design session, not an implementer.
