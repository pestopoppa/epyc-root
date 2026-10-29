# Handoff: Refactoring — orchestrator, autopilot and AutoKernel (multi-repo debt program)

**Status**: ACTIVE — operator resumed implementation 2026-10-24 after an independent handoff audit; review and finish existing branches before integration
**Created**: 2026-10-07
**Updated**: 2026-10-27
**Priority**: High
**Scope**: epyc-orchestrator (`src/`, `scripts/`, `tests/`, `scripts/autopilot/`, `src/autopilot_core/`);
epyc-inference-research `scripts/kernel_rnd/autokernel/`; epyc-root `scripts/hooks/` (guard bugs found on the way)
**Estimated effort**: 382 findings → 26 packages (12 in wave 1, 14 in wave 2); deletion size is a planning estimate, subject to current per-file reachability and retention contracts
**Scratch**: `/mnt/raid0/llm/tmp/refactor-01a16fc3/` · worktrees: `/mnt/raid0/llm/worktrees/refactor-01a16fc3-*` · root integration: `/mnt/raid0/llm/worktrees/refactor-audit-01a16fc3-root` · wrap checkpoints: `/mnt/raid0/llm/worktrees/wrap-root-20261027`, `/mnt/raid0/llm/worktrees/wrap-root-fresh-20261027`, `/mnt/raid0/llm/worktrees/prep-progress-publish-20261027`

**Current working priority (operator, 2026-10-27)**: support the Claude inference owner by resolving prioritized non-inference blockers, validating source-bound launchers, and handing them over unarmed. Coordinate with the parallel NI Codex session. CI/O8 remains parked; this checkpoint does not claim the full refactor complete. Current evidence and next actions: [campaign checkpoint](../../progress/2026-10/2026-10-27-refactor-campaign-wrap.md).

Each package uses its own branch/worktree and scratch subdirectory. Tests whose safety contracts
require `/tmp` use the manually cleaned exception `/tmp/refactor-01a16fc3/`. The earlier cloud run's
`/workspace/wt/` and expired container scratch paths are historical, not host cleanup targets.

**Start here:** the [Pending work](#pending-work) checklist is the queue; §Branches says what each pushed
branch holds and how to merge it; per-finding evidence is in `research/refactor-audit-2026-10/findings-*.md`.

**Owner review boundary (2026-10-26):** root `bb6410b1fa76553ab8d2d26dad5ee9816fb1ee5d` was
privately published, but was not accepted or merged by workspace-58. Owner review at 12:45/13:25
requires per-line checkbox evidence, removal of this branch's generated index artifacts/counts,
and confirmation of one index owner. The correction below does not claim owner acceptance.
The owner verified those fixes in private `d3cba7b6` at 16:40, but still withheld merge: this
branch must withdraw its wiki page/manifest contribution and retain the runbook's live executor
offender until the cleanup source merges. Findings stay in the research record for the next sweep.

**Current next action (2026-10-26):** repair CI report compatibility and runtime isolation, then rerun baseline.
CI already contains integration in local merge `753e0287a1ae6b06f2a5c91269899ff8cc8452b5`.
P3 is accepted and published at `fb5db1a0a24b92172643bb670c77a4343a508c96` on its private
`codex/*` branch. Run the separate root wrap-up checks in an official q1 grant.

Origin: cloud refactor-audit session (claude.ai/code session_01C4SLLAQhop8AA9rJJusAYj), run in an ephemeral
4-CPU container on fresh clones, never on the host. Evidence, data and tooling:
[`research/refactor-audit-2026-10/`](../../research/refactor-audit-2026-10/README.md). Bug report:
[`BUG-REPORT-autopilot-autokernel.md`](../../research/refactor-audit-2026-10/BUG-REPORT-autopilot-autokernel.md).

> **Review-branch registration:** owning main corrected this handoff's row to **RTG-61** in
> `routing-and-optimization-index.md`. Native review of current main `a876d3c9` found RTG-60 already
> reserved for `loop-state-offraid-backup.md`; that canonical row must remain intact at merge. The old
> private RTG-60 refactoring row was a collision, not canonical ownership. Shared/canonical files remain
> untouched; workspace-58's publication boundary still applies. Source wiring is filed prospectively on
> this branch as VB-REFACTOR-CONFORMANCE, not as an optional applicability decision.

### Current package state (2026-10-26)

- **Integration:** reviewed and published private candidate `851955112b8ba8c2911a7684469551afa1541623`
  on `refactor/orchestrator-integration-01a16fc3`, validated relative to immutable base `84f6f6f1`.
  The expanded union passed 2,897/2,905 (8 skipped), four coverage floors are 100%, 32 NI63 pins
  and four P5 preservation proofs pass. The formatter correction establishes zero introduced
  failures within accepted scope. RESUME-4 records this private candidate only; no main promotion.
- **O8 CI:** B1-tested pre-fixture local-only merge `753e0287a1ae6b06f2a5c91269899ff8cc8452b5` has parents
  `713edf671614e69f67028100c08cc8f08b02d52f` and integration `851955112b8ba8c2911a7684469551afa1541623`.
  The focused check passed 13 tests. Official q1 B1 attempt 1 failed before collection because
  custody hashing followed public-carrier directory symlinks; no tests ran in that attempt.
  The helper's corrected symlink metadata proof passed. B1 attempt 2 actually collected 20,646
  baseline tests plus an error for an unregistered `slow` marker; candidate collection did not run.
  After the external harness correction, strict collection passed: baseline 20,658 total/20,645
  selected, candidate 20,666 total/20,653 selected; 0 removed and 8 intended additions, with the
  same 13 exclusions on both sides. This is collection parity, not a full-suite result.
  Full baseline comparison, native capture and coverage remain incomplete; O8 stays unchecked.
  B2 baseline then completed at 13:13:11 UTC with 31 failed, 20,517 passed, 85 skipped, 19 xfailed
  and 6 passed subtest events in 2,146.45 s. Its 20,643 parent cases plus 9 module-skip case nodes
  give 20,652 JUnit testcase nodes; header 20,658 also counts the 6 subtest events. Native
  conformance is NULL on an unnamed collection-skip case; shared grading failed without JSON.
  Sixteen ignored runtime paths leaked in the baseline checkout, while tracked custody for all
  three repositories and the source harness matched. No candidate full run occurred and no
  accepted known-failure set is established. Original log/JUnit/native receipts remain at
  `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/b2-baseline-first-native/`.
- **P3:** reviewed private source `fb5db1a0a24b92172643bb670c77a4343a508c96` is published on
  `codex/refactor-autopilot-actions-01a16fc3`, remote-exact verified with a clean worktree. It combines
  checkpoint `bbccaaef` and integration `851955112`. The original 34-file run was 817 passed, 1 skipped,
  3 failed; the expanded 90-file run was 1,917 passed, 2 skipped, 11 failed (600 s).
  Targeted legacy-adapter/double repairs then passed the final 12-file selection: 402 passed,
  1 skipped in 39.49 s, with compile, P5/W3e preservation, diff/hash and no-new-Ruff proofs.
  Raw Ruff exit 1 is preserved: 16 inherited E701 findings in `tests/unit/test_mutation_diagnostics.py`.
  The official q1 closure at 12:04:57–12:05:05 UTC returned 0: all three formatter targets have equal
  ASTs before/after, format-check 3 passed, non-target bytes are unchanged, and no-new-Ruff,
  protected-file, diff and source-custody proofs pass. The owning main accepted P3 for this private
  branch only. These successive selections do not establish a current all-1,930-pass aggregate.
- **Next:** repair CI report compatibility and runtime isolation, then rerun baseline under a new
  reviewed calendar admission. The root metadata correction needs no compute row per the owner's
  12:45 instruction; it remains subject to owning-main review before commit/push.

The native read observed the 1.35 GB `question_pool.jsonl`; its exact consumer is unproven. No fixture patch was
applied, and an EvalTower-constructor causal claim is not supported. The CI host audit established
that a dashboard restart test polls live slots and creates host logs. A reviewed owned-dashboard
test fixture was applied after B1 (+26/−10); its validation is pending, with production application
logic unchanged. The source evidence chronology is in
the [Oct 26 checkpoint](../../progress/2026-10/2026-10-26-refactor-next-packages-checkpoint-01a16fc3.md).

Evidence and the formatter-scope adjudication are recorded in
[`integration-validation-review-2026-10-26.md`](../../research/refactor-audit-2026-10/integration-validation-review-2026-10-26.md).
Root attempts `829152` and `831298` ended before admission. The later bare queued wrapper `881101`
and its exact region child `881104` were cancelled for calendar integration and both verified dead;
its actual terminal exit 143 is preserved, with no gates run. The root row is not armed. All new
checks require the calendar owner's live grant and official filler launcher on literal q1 CPUs
24–47, 8 GiB, with affinity proof; a bare region claim is insufficient. The separate root request
is 600 s, minimum useful 300 s. Future pushes target `codex/*` only; this root's publication
destination is `codex/refactor-handoff-audit-01a16fc3`, leaving its old review remote unchanged.

## Pending work

Historical implementation checkboxes below mean committed on the named branch, not reviewed or merged.
New completion records name their validation and integration state explicitly. A finding ID in a commit
subject establishes association only; WIP, skipped, tested, reviewed and merged are distinct states.

### Resumed execution (2026-10-24, session 01a16fc3)

- [x] RESUME-1: audit pushed branches and current upstream state; identify unsafe pruning assumptions, rollback failure-path gap, test isolation prerequisite and integration conflicts. Evidence: [audit checkpoint](../../progress/2026-10/2026-10-24-refactor-audit-01a16fc3.md). ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-audit-01a16fc3.md`. [belief: cc]
- [x] RESUME-2: review hermetic-tests + test-hazards and isolate A6-M1 trace/ledger writes in fixtures. Orchestrator `87540dae`, checkpoint `5e392a3c`, pushed to `refactor/test-isolation-reviewed-01a16fc3`: 189 runtime/trace tests pass + 1 intentional skip; 7 E8 wrapper cases pass; all 3 new regressions fail safely on parent. Original hazard modules reviewed; unmerged. ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc]
- [x] RESUME-3: finish and review C1-05 rollback error handling and behavioral regressions for nonzero exit, timeout, spawn error, wrong HEAD and successful rollback. Research `62c68ad99`, checkpoint `1b58b115c`, pushed to `refactor/autokernel-rollback-reviewed-01a16fc3`: 13 regressions pass (5 fail on WIP), targeted loop set 401 pass + 23 subtests. Reviewed, unmerged under launch/re-pin hold. ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc]
- [x] RESUME-4: review and validate the combined orchestrator candidate in a private worktree against immutable base `84f6f6f15f713d21098dbad2b153d32f8cc13624`. Candidate `851955112b8ba8c2911a7684469551afa1541623` on `refactor/orchestrator-integration-01a16fc3` passed reviewed AST, focused tests, Ruff/format scope, compile/diff, 32 NI63 pin, and four-file P5 preservation proofs; expanded union: 2,897 passed, 8 skipped, 0 failed/2,905, all four coverage floors 100%. Formatter correction proves zero introduced failures within accepted scope. Private candidate only; no main promotion/deployment. [belief: cc] Evidence: [`integration-validation-review-2026-10-26.md`](../../research/refactor-audit-2026-10/integration-validation-review-2026-10-26.md). ✅ 2026-10-26 Review record: root `bb6410b1:research/refactor-audit-2026-10/integration-validation-review-2026-10-26.md`.
- [x] RESUME-4a: independently review O3 and integrate the accepted isolation harness into its private branch. Orchestrator `d843eb9c` fixes concurrent registry-load backoff (12 attempts before, 1 after); `07829696` scopes alias stress to its actual guarantee; checkpoint `6558beb7` pushed to `refactor/config-reviewed-01a16fc3`. O3 selection 548 pass/4 skip, alias targets 524 pass, all 7 changed source pins verified. Reviewed, unmerged. ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc]
- [x] RESUME-4b: independently review O1 stage 1 and fix pre-first-chunk streaming disconnect handling. Orchestrator `a1c69593`, checkpoint `142bb5df`, pushed to `refactor/request-reviewed-01a16fc3`: 1,011 targeted tests pass/3 skip; blocked initial generation fails to observe cancellation on parent and passes after fix. Accepted isolation is included; no changed route lies in ni63's pin closure. Reviewed, unmerged. ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc]
- [x] RESUME-4c: independently review P2 decision semantics and snapshot migration. Orchestrator `4069b8ee`, checkpoint `db17808e`, pushed to `refactor/autopilot-gate-reviewed-01a16fc3`: 1,018 tests pass/1 skip; 18 snapshot controls pass; B2-02/B2-03 fail on parent. Pre-P2 snapshots refuse bounded authority; a current-format rebuild matches full replay. Review complete; integration held because existing reconstruction is CRITICAL and verified-snapshot replay HIGH. No evaluator-era files changed. ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc]
- [ ] RESUME-5: repair CI infrastructure early; keep K4's post-prune size ratchet after K3. Reconcile baseline collection/failure identities rather than accepting aggregate counts.
  - [x] **B2-PRODUCER-E-NEXT-01a16fc3:** prepared and delivered the q2 candidate/baseline comparison packet; source-bound two-core preflight passed, NEXT receipt `f7e9e236-f6d5-4034-a609-7bf03f181ee1`. No official comparison was run; compare the known baseline failures individually. Parent work remains open. ✅ 2026-10-27 [no-belief: packet preparation]
  - *(2026-10-27 21:35Z, ws58 results filing, B2 producer E.)* `refactor-b2-producer-e-q2-20261027` ended rc1 at 19:04:07Z by design of its comparison: candidate `411 passed, 4 warnings in 49.03s` (candidate-research.status 0, cleanup-integrity 0, model-free violation count 0); baseline `2 failed, 394 passed` (baseline-research.status 1; the two known historical failures, a containment case and `test_python_hook_flags_out_of_root_writes_and_not_in_root_ones` on EXDEV `os.rename` to `/var/tmp`). Terminal rc1 is the baseline's, comparison only, no zero-failure claim. Results `/mnt/raid0/llm/tmp/refactor-01a16fc3/b2-cpu-ready-1728/results/run-20261027T190217308687691/`. Not a merge; B2 producer E stays open. [no-belief: model-free test comparison, no measurement]
  - *(2026-10-28, scoped re-derivation.)* A private fail-closed comparator matched all 396 baseline test identities to passing candidate cases and found 15 additional passing candidate cases. The baseline has 394 passes and the same two historical containment/EXDEV failures; the original row named those categories, while their exact test identities and signatures were established from the prior and current logs. Fixtures reject missing/duplicate tests, changed failure signatures, candidate failures and custody/guard changes. This is a scoped comparison, not a clean baseline, full B2 result or merge. Evidence: `/mnt/raid0/llm/tmp/refactor-01a16fc3/b2-producer-e-comparison-20261028/actual-comparison.log`. [belief: cc]
- [ ] RESUME-6: reconcile current INF64 retained-module manifest and live belief-source contracts before each deletion stage; include retained `campaign.py` and dynamic/cross-repo consumers as closure roots.
- [ ] RESUME-7: fix the separate mixed-alias cold-import cycle. Randomized 16 aliases fail when imported concurrently at orchestrator baseline `84f6f6f1` and O3; same-alias 24-thread races and canonical identity tests pass. Original mixed test is at orchestrator `5886e5ae:tests/unit/test_inference_lock_concurrent_import.py`; existing O3 tests do not establish cross-module cold-import safety.
- [x] RESUME-8: repair NI07 capture's declared-output environment contract and replace expired cloud-only package prompts with validated host inputs, CPU claims, isolated baseline trees and explicit cheapest-capable model/effort. Root source `a976770b8`, closeout `8e66dd96b`, integrated here as `152a2991b`; node syntax/smoke and capture regression pass, capture regression fails on parent. ✅ 2026-10-24 Evidence: root `e031c422f:progress/2026-10/2026-10-24-root-integration-01a16fc3.md`. [belief: cc]

At resumption, the independent audit found 55/382 findings with associated commits (including two WIP findings),
327 without commits, and 52 unverified C4–C6 findings. These are inventory counts, not accepted fixes.
The explicit AutoKernel launch hold, deliberate owner-controlled re-pinning, operator-timed P5 merge,
containment-scanner operator review and production-kernel freezes remain in force. Execution stays
near two concurrent agents, using the cheapest capable available model/effort per dispatch.

### Resumed execution checkpoint (2026-10-25)

The operator approved isolated candidate work for the exact A5-18 protected-launcher cleanup and
for O4 HIGH/CRITICAL REPL findings A4-03/A4-04/A4-06/A4-07. These approvals cover candidate
patches only; they do not authorize a main push, merge, deployment, or production activation.

P1 is accepted and pushed at source `36e1bc55aa40f35965a941e81fdc593a22abd520` on
`refactor/autopilot-loop-reviewed-01a16fc3`. The aggregate and all nine focused file hashes match the run-start, run-end,
and checkpoint snapshots; 19 focused and 561 broad tests passed (one skip), with ruff and diff checks
passing. The worker's original `validation.status` says `FAIL` because its hash-comparison ordering
was wrong; the independent unchanged-file proof is the acceptance evidence. No test was rerun for this
root checkpoint. The P1(rest) item is complete; RESUME-4 combined-tree validation is still separate.

O6 rest (A5-11, A5-23, A5-18, A5-02, A5-21) is accepted and pushed at `6efa56265b68f402af736a1c1a2ee3df447849c1` on `refactor/scripts-cleanup-reviewed-01a16fc3`. The 190 launcher tests and 395 coverage tests pass, including all four 100% floors (331/331, 151/151, 508/508, 579/579); five NI63 controls pass with 32/32 blob and SHA proof. The three scorer failures were a test-fixture `sys.modules` patch/restore leak, fixed without a production-code defect. Four source-pin changes match the exact approved launcher bytes; baseline 5 passes, HEAD `094cbc5b` and main `84` match, and the other 28 pins are unchanged. The original seeding worktree is unchanged. O6 candidate acceptance does not authorize integration, deployment, or activation. O4 candidate patches and caller audit are frozen and accepted:
557 tests passed, eight parent regression negative controls failed as expected, and strict offline
drift, ruff, compile, diff and frozen-snapshot checks passed. Its source-only closeout is pushed as
`acfd5f8ca3837c568fc3c944ffb242b29823f3fa` on reviewed branch `refactor/repl-correctness-01a16fc3`; this does not
authorize main integration or deployment. K2 fixes C4-08, C4-16, and C3-02 are accepted and pushed on `refactor/autokernel-k2-guards-01a16fc3` at `68724da5ba093cf3cec3909a81491932002dd4ce`; C4-05, C4-06, and C4-10 remain incomplete, so K2 stays open. Detailed state and evidence paths are in
`research/refactor-audit-2026-10/resume-state-01a16fc3.json`.

### Superseded package checkpoint (2026-10-25)

This entire section is an as-of-2026-10-25 snapshot. Its integration and runner statuses were
superseded by the Oct 26 state above; do not use its captured PIDs as current.

Everything in this dated snapshot is historical; for current integration, O8, P3 and runner states,
use the Oct 26 package state above.

The private integration candidate at `3ee8eea2ab514e8fac4c15c839d4ad1644e0ba38` completed an expanded 111-file union: 2,897 passed, 8 skipped, 0 failed of 2,905 collected; all four source coverage floors are 100%, with no checkout-write warnings. The initial 93-file failure was traced to fixture bytes changing during `_run_loop_inner`; two regression tests now preserve the historical W3e fixture while also detecting future overwrites. The 18-case initial rerun and both added regression tests pass. New-file/changed-hunk style fixes are applied, but final AST, style, focused-suite, 32-pin and P5 frozen-file proof is still running as captured PID 2010953. Its durable evidence is under `/mnt/raid0/llm/tmp/refactor-01a16fc3/orchestrator-integration/` (`final-proof.pid`, `final-proof-runner.log`, `final-proof.sh`; terminal status/done artifacts are not present yet). Until that proof completes and is reviewed, integration is not accepted or pushed. Known baseline debt is 18 Ruff findings and 133 formatter paths; the first integration attempt's checkout-write warnings were eliminated by private pre-import environments for the tool-audit/seen-host file and Ruff cache.

O8 is a frozen, uncommitted draft in `/mnt/raid0/llm/worktrees/refactor-01a16fc3-ci`, branch `refactor/orchestrator-ci-01a16fc3`, based on `3ee8eea2`. It prepares PR/manual CI, the shared native carrier and grade, exact nonsecret context/output/JUnit custody, a single test entrypoint, baseline comparators, strict pytest/server-marker handling, NI63's 32-source current-provenance closure, and pip/UV dev-dependency parity. Original preparation PID 2085542 was cancelled by its owner before the comparator fix and verified dead. Replacement PID 2093707 is the current single detached preparation request, waiting behind the q0–q3 build claim; authoritative pointers are `precheck-run2.pid`, `precheck-run2.process-check.txt`, and `region-lock-run2.log` under `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/`. No tests, lint, lock/sync, native receipt or CI validation are accepted, and no source commit or push exists. The checkpoint snapshot is `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/checkpoint/`; its manifest prose still describes the original PID, so use the run2 PID/status pointers for live state.

P3 is a frozen, uncommitted draft in `/mnt/raid0/llm/worktrees/refactor-01a16fc3-autopilot-actions`, branch `refactor/autopilot-actions-01a16fc3`, based on `3ee8eea2`. The prepared changes cover managed-stack PID/environment access without `pgrep`, finite validators, refusal-before-side-effects, journal context/events and supersession/caching, provider IO/lifecycle, dead-resume/API cleanup, shard reading, and a neutral core baseline-pin helper. Successor `/root/autopilot_actions_finish` completed the authorized B3-04 optional loaded-journal injection with separate all-era ceiling semantics and added invariance/reset/teardown tests, then froze the draft. W3e fixture bytes match base and `git diff --check` passes. No tests have run; P3 remains unvalidated and uncommitted, with no approval missing. The refreshed 34-file suite is queued in phase `queued-source-frozen`; its stable authoritative manifest is `/mnt/raid0/llm/tmp/refactor-01a16fc3/autopilot-actions/current-run.json`, which points to the source/test snapshot, runner, PID file, log, status and completion flag. Use that manifest for current liveness and runner details; prior wrapper PID 2077838 and child PID 2077840 remain cancelled-before-admission history in `focused-p3-20261025/cancelled-before-admission.txt`. Observed 2026-10-25 08:53:07 UTC. Graph coverage is unknown after the index error. No source acceptance, commit or push exists.

The current next action is to finish and review the integration proof, then validate O8 CI and P3 against the accepted integration SHA. The O8, P3, and RESUME-4 completion boxes remain unchecked; no per-finding completion is claimed. Existing AutoKernel launch/main-merge holds, the P5 single-era boundary and protected serving/kernel rules remain in force. P3 is frozen with a 34-file suite queued; its stable current-run manifest is `/mnt/raid0/llm/tmp/refactor-01a16fc3/autopilot-actions/current-run.json`, observed 2026-10-25 08:53:07 UTC. No tests have run and no source is accepted. The earlier P3 wrapper PID 2077838 and child PID 2077840 are cancelled history, as recorded in `focused-p3-20261025/cancelled-before-admission.txt`. My root-gates wrapper PID 2096522 and child PID 2096526 were cancelled before region admission and verified dead at 2026-10-25 08:52:45 UTC; no token was acquired. Root documentation gates remain pending; use `/mnt/raid0/llm/tmp/refactor-01a16fc3/next-packages-checkpoint/root-gates.pid` and `root-gates.status` as the stable runner-state pointers. The captured state is recorded in `research/refactor-audit-2026-10/resume-state-01a16fc3.json`.

### Done

- [x] Audit inventory and artifacts filed for 17 units/382 findings; C4-C6 remained unverified in the historical audit. This records artifact filing, not completion of the findings. Evidence: root `83419070d:research/refactor-audit-2026-10/README.md`. [no-belief: not-a-result] ✅ 2026-10-24
- [ ] Hermetic orchestrator harness: the historical plan reported 20,815 off-host collections on `refactor/hermetic-tests`; no independently reviewed raw receipt for that historical count is cited here. Current isolation review is RESUME-2; branch association alone does not complete this item.
- [ ] Containment-scanner bypass/degraded-mode fixes on `refactor/containment-scanner`: historical implementation association only; owner safety review remains open below, so this item is not complete.
- [x] Operator decisions on evaluator regime, AutoKernel prune, CI and scope recorded. Evidence: root `83419070d:research/refactor-audit-2026-10/OPERATOR-DECISIONS.md`. [no-belief: not-a-result] ✅ 2026-10-24
- [x] Bug report, findings, metrics and package definitions filed; no implementation completion follows from publication. Evidence: root `83419070d:research/refactor-audit-2026-10/README.md`. [no-belief: not-a-result] ✅ 2026-10-24

### Review and merge what is already pushed

- [ ] Operator review of `refactor/containment-scanner` (safety boundary for INC-20260823); read `scripts/hooks/CONTAINMENT-SCANNER-CHANGES-FOR-REVIEW.md` on the branch, then merge or reject
- [ ] Merge `refactor/hermetic-tests` into epyc-orchestrator main (every orchestrator branch contains it)
- [ ] Adversarial review, then merge, of `refactor/config-registry` (O3)
- [ ] Adversarial review, then merge, of `refactor/request-path` (O1 stage 1)
- [ ] Adversarial review, then merge, of `refactor/test-hazards` (O7 partial; its 3 commits have no test report: run the suites first)
- [ ] Adversarial review, then merge, of `refactor/autopilot-gate` (P2; B2-03 changes what is admitted to learning: review as a decision-semantics change)
- [ ] Adversarial review, then merge, of `refactor/autopilot-loop` (P1 stage 1, test harness)
- [ ] Adversarial review, then merge, of `refactor/scripts-cleanup` (O6; finish the A5-11 WIP commit and run the suites for the A5-01/A6-19/A5-05 deletions first)
- [ ] Merge `refactor/autokernel-loop-bugs` only after the AutoKernel launch hold lifts, with a deliberate re-pin (workspace-58); finish the C1-05 WIP first (regression test + loop suite)
- [ ] Delete the superseded `claude/vigilant-thompson-shpyh0` branches in epyc-root and epyc-orchestrator (operator)
- [x] Publish this review branch's RTG-60 registration and VB-REFACTOR-CONFORMANCE filing through the root owner boundary; no shared index file was edited during package work. ✅ 2026-10-29 (audit: RTG-61 row exists in routing-and-optimization-index.md:65 (owning main corrected RTG-60->RTG-61, d3cba7b64) and VB-REFACTOR-CONFORMANCE row filed at vidya-belief-substrate-program.md:82) [no-belief: audit-reconciliation]

### Wave 1: bugs, hazards, ruled deletions

- [x] O1 (part): reviewed private stage-1 request-path candidate, including the initial-stream cancellation repair, at orchestrator `a1c69593`/`142bb5df`; 1,011 targeted checks pass/3 skip, with parent regression negative control. This is candidate review, not main integration or a blanket completion of associated findings. Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc] ✅ 2026-10-24
- [ ] O1 (rest): [A2-02, A2-M1, A2-M2, A2-03, A2-05, A2-11, A2-16]
- [x] O3: reviewed private config/registry candidate at orchestrator `d843eb9c`/`07829696`/`6558beb7`; 548 targeted checks pass/4 skip, 524 alias-target checks pass and all 7 changed source pins match. Scope is this reviewed candidate; mixed-alias safety remains RESUME-7. Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc] ✅ 2026-10-24
- [x] O4 (reviewed scope): A4-03/A4-04/A4-06/A4-07 only, accepted private source `acfd5f8ca3837c568fc3c944ffb242b29823f3fa`; 557 checks pass, eight parent negative controls fail as expected, strict drift/Ruff/compile/diff/frozen proof passes. Evidence: root `09d3c70b5:progress/2026-10/2026-10-25-repl-validation-01a16fc3.md`. [belief: cc] ✅ 2026-10-25
- [ ] O4 (historical associations): A4-01/A4-02/A4-14/A4-M3 were listed against `refactor/repl-correctness`; this line has no reviewed per-finding closure receipt and remains open rather than inheriting the four-item review above.
- [ ] O5: Dashboard request-path cost and silent-empty panels [A1-04, A1-08, A1-13, A1-11, A1-21]
- [ ] O6 (part): historical source associations on `refactor/scripts-cleanup` [A5-M1, A5-06, A5-07, A5-04, A5-12, A5-22, A5-M2, A5-01, A6-19, A5-05]; no reviewed closure receipt for the entire listed scope, and no test report for A5-01/A6-19/A5-05. Association is not completion.
- [x] O6 (rest): [A5-11, A5-23, A5-18, A5-02, A5-21]; accepted source `6efa56265b68f402af736a1c1a2ee3df447849c1` on `refactor/scripts-cleanup-reviewed-01a16fc3`; 190 launcher + 395 coverage tests pass, four 100% floors pass, five NI63 controls pass with 32/32 blob/SHA proof; exact approved four launcher-byte pins and remaining 28 unchanged. No integration/deployment authorization. ✅ 2026-10-25 Evidence: root `e8748d8ec:progress/2026-10/2026-10-25-cleanup-validation-01a16fc3.md`. [belief: cc]
- [ ] O7 (part): historical hazards/hygiene associations on `refactor/test-hazards` [A6-01, A6-02, A6-09]; no reviewed test report for these three findings. RESUME-2's narrower isolation review does not supply their missing closure.
- [ ] O7 (rest): [A6-M1, A6-03, A6-12, A6-11, A6-17]; A6-13 belongs to O8 only.
- [ ] P1 (part): historical main-loop associations on `refactor/autopilot-loop` [B1-03, B5-02, B5-08, B1-15]; this row lacks its own reviewed per-finding closure receipt and does not inherit P1(rest)'s narrower result.
- [x] P1 (rest): [B1-01, B1-M1, B1-M2, B1-04, B1-08, B1-09, B1-14, B1-13]; accepted source `36e1bc55` on `refactor/autopilot-loop-reviewed-01a16fc3`, hashes unchanged across the full candidate and 19 focused/561 broad tests pass (1 skip). Worker status-file failure was an ordering defect; see resume-state proof. ✅ 2026-10-25 Evidence: root `09d3c70b5:progress/2026-10/2026-10-25-loop-acceptance-closeout.md`. [belief: cc]
- [x] P2: Autopilot safety gate and autopilot_core on `refactor/autopilot-gate` [B2-02, B2-03, B2-09, B2-11, B2-20, B2-17, B5-01, B5-M1, B5-M2, B5-16, B5-09, B5-13, B5-12] (B2-11 skipped: upstream already split SafetyGate.check; B2-17 no change, per the verifier) ✅ 2026-10-24 Reviewed private candidate only; evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`, orchestrator `4069b8ee`/`db17808e`. [belief: cc]
- [x] P3: Autopilot actions, config applicator, controller IO, planner, journal [B3-01, B3-02, B3-03, B3-05, B1-17, B3-06, B3-07, B3-08, B3-12, B3-M1, B3-04, B3-23, B4-01, B3-15, B3-16, B3-M2]; reviewed private source `fb5db1a0a24b92172643bb670c77a4343a508c96` published and remote-verified on `codex/refactor-autopilot-actions-01a16fc3`, clean worktree. Final 12-file functional selection 402 passed/1 skipped in 39.49 s; official three-file formatter closure passed AST equality, format/compile, non-target bytes, no-new-Ruff, P5/W3e, diff and source custody. Earlier 34/90-file failures retained; no current all-1,930-pass claim or main/deployment acceptance. [belief: cc] Evidence: [Oct 26 source/proof record](../../progress/2026-10/2026-10-26-refactor-next-packages-checkpoint-01a16fc3.md). ✅ 2026-10-26 Source warrant: orchestrator `fb5db1a0:docs/refactoring/2026-10-26-p3-reviewed-checkpoint.md`.
- [ ] P4: Autopilot satellites: one-shot scripts, dead modules, small bugs [B4-03, B4-02, B4-19, B4-20, B4-13, B2-16, B4-16, B4-12, B4-06, B4-08, B4-09, B4-15, B4-M1, B4-M2, B4-04, B4-05]
- [ ] K1: AutoKernel live-loop bugs and red tests [C1-06, C1-14, C1-15, C1-M2, C1-24, C2-06, C5-08, C5-16, C6-05, C6-03, C6-04]; C1-05 tested/reviewed on `refactor/autokernel-rollback-reviewed-01a16fc3`, held unmerged (RESUME-3).
- [ ] K2: AutoKernel evaluator/execution integrity package remains open; C4-05, C4-06, C4-10 remain incomplete.
  - [x] K2 finding C4-08: resolved-path, fail-closed production-tree containment; source commit `208a053e29daf5bd11019e733f768b4173887021`. ✅ 2026-10-25 Evidence: root `e8748d8ec:progress/2026-10/2026-10-25-k2-guards-01a16fc3.md`. [belief: cc]
  - [x] K2 finding C4-16: exact Fraction ceiling independent of Decimal context; source commit `091abbbe7dc9b346bab888569434eb68445ae8e5`. ✅ 2026-10-25 Evidence: root `e8748d8ec:progress/2026-10/2026-10-25-k2-guards-01a16fc3.md`. [belief: cc]
  - [x] K2 finding C3-02: package import avoids shadowing stdlib `resource`; source commit `68724da5ba093cf3cec3909a81491932002dd4ce`. ✅ 2026-10-25 Evidence: root `e8748d8ec:progress/2026-10/2026-10-25-k2-guards-01a16fc3.md`. [belief: cc]

### Wave 2: decision-dependent and structural

- [ ] P5: Autopilot evaluator: ONE batched era event (operator decision 2026-10-24) [B5-03, B2-01, B2-M1, B2-M2, B2-10, B5-06, B5-07, B2-19, B2-04, B2-05, B2-06, B2-07, B2-08, B2-14, B2-15, B2-18, B2-12, B2-13, B5-14, B3-09]
- [ ] K3: AutoKernel prune of the three approved planes, after fresh closure and retained-contract checks [C2-01, C1-04, C2-03, C2-05, C2-08, C2-12, C2-M2, C2-13, C3-03, C3-01, C3-M1, C3-13, C3-14, C3-18, C5-03, C5-15, C6-07, C4-01, C4-02, C4-03, C4-11, C5-13, C5-12, C6-09, C5-06, C6-08, C2-09, C5-07, C2-M1]; C4-01's old deletion advice is superseded by INF64's retained manifest.
- [ ] K4: AutoKernel regrowth guard and CI repair (operator decision 2026-10-24) [C2-04, C5-02, C3-05, C1-02, C1-M3, C5-01, C6-01, C5-14, C6-13, C3-11, C2-02, C6-16]
- [ ] O8: Orchestrator CI, honest gates, and the ni63 pin design (operator decision 2026-10-24) [A6-04, B1-M3, B5-10, B5-17, A6-13]
- [ ] D1: Decompose the autopilot loop (_run_loop_inner) behind the P1 safety net [B1-02, B1-05, B1-12, B1-10, B1-06, B1-07, B1-11, B1-16, B1-18, B1-19]
- [ ] D2: API layer: openai_compat and /chat de-duplication [A1-05, A1-06, A1-15, A1-19, A1-20, A1-12, A1-10, A1-14, A1-16, A1-18, A1-09, A1-07]
- [ ] D3 (part): historical inference-hot-path association [A2-12]; no reviewed closure receipt is cited here, so it remains open.
- [ ] D3 (rest): [A2-22, A2-06, A2-09, A2-07, A2-08, A2-10, A2-14, A2-15, A2-17, A2-18, A2-19, A2-20, A2-21]
- [ ] D4: AutoKernel run.main decomposition [C1-03, C1-M1, C1-01, C1-08, C1-10, C1-11, C1-12, C1-13, C1-16, C1-17, C1-18, C1-19, C1-20, C1-21, C1-23, C1-09, C1-07, C2-14, C2-15, C2-16]
- [ ] D5: Config / registry / runtime consolidation [A3-03, A3-10, A3-11, A3-12, A3-13, A3-14, A3-17, A3-18, A3-20, A3-21, A3-22, A3-23, A3-24, A3-25]
- [ ] D6: REPL / tools consolidation [A4-09, A4-12, A4-10, A4-17, A4-05, A4-11, A4-13, A4-15, A4-16, A4-18, A4-19, A4-20, A4-21, A4-22, A4-23, A4-M2]
- [ ] D7: Orchestrator scripts structure (src<->scripts layering, sys.path, duplicated helpers) [A5-03, A5-08, A5-09, A5-13, A5-14, A5-15, A5-20, A5-24, A5-25, A5-M3]
- [ ] D8: Orchestrator test-suite consolidation [A6-10, A6-05, A6-06, A6-07, A6-08, A6-14, A6-15, A6-16, A6-20, B5-18]
- [ ] D9: Autopilot remaining structure (actions, planner, journal, reports) [B3-10, B3-11, B3-13, B3-14, B3-17, B3-18, B3-19, B3-20, B3-21, B3-22, B3-24, B3-25, B4-07, B4-10, B4-11, B4-14, B4-17, B4-18, B5-04, B5-05, B5-11, B5-15]
- [ ] D10: AutoKernel remaining structure (controller, evaluator, execution, schemas, tests) [C3-04, C3-06, C3-07, C3-08, C3-09, C3-10, C3-12, C3-15, C3-16, C3-17, C3-19, C3-20, C3-21, C3-22, C3-M2, C4-04, C4-07, C4-09, C4-12, C4-13, C4-14, C4-15, C4-17, C4-18, C5-04, C5-09, C5-10, C5-11, C6-02, C6-06, C6-10, C6-11, C6-12, C6-14, C6-15, C6-18, C2-07, C2-10, C2-11]

### Deferred, each with its blocker

- [ ] A5-10, A5-16, A5-17, A5-19: restructure `scripts/server/orchestrator_stack.py`. Blocked: a live path on the host (workspace-58, 2026-10-24); run when that file is quiet
- [ ] C5-05: delete the `campaign.py` CLI cluster (~20k LOC). Blocked: needs an operator decision (it is a fourth plane, not among the three approved)
- [ ] C6-17: Arena retirement is outside the approved three-plane prune; preserve its existing belief-source producer/consumer contracts unless the operator authorizes a separate retirement package. Continue other packages meanwhile.
- [ ] Re-enable the AutoKernel guards workflow in GitHub after K4 lands (operator click)

### Follow-ups found during the audit (not tied to a single package)

- [ ] Reconcile C4-01 against `artifacts/ni08/inf64-source-reachability-review-20261007/completed-manifest.md`: current strip guidance already retains all 19 candidates. Do not follow the old proposal to delete Apex/compiler modules or preserve only three evaluator modules.
- [ ] Re-pin `scripts/server/orchestrator_stack.py` in the ni63 `SOURCE_PINS`: stale on orchestrator main, 4 tests red there (fixed properly by O8's record-not-assert design)
- [ ] Refresh `scripts/harness/strategy_projection_report_capture.py` `TRUSTED_APP_SOURCES`: 6 of 11 pins already stale at base (incl. `tier_specs.py`), so the tool refuses (found by O3)
- [ ] Move `process_pattern_kill_scan.py`, `operator_apply_copy_scan.py` and `pytest_worker_scan.py` to `shell_scan.lex()`: they still use the old strip functions and share the escape/heredoc blind spots the containment scanner had
- [ ] Containment scanner coverage for `restic restore --target`, `borg extract/delete/prune`, `rclone copyto/moveto/mkdir` (changes `--dump-rules`; regenerate the opencode config in the same change)
- [ ] `.claude/skills/project-wiki/scripts/check_readme_freshness.py` hard-codes `/mnt/raid0/llm/<repo>`: off the host it reports all three READMEs as missing. Resolve repos relative to its own checkout or accept `--root`
- [ ] `scripts/vidya/adapters/README.md` cites `test_vb_ap53_reproposal_rate.py (12)`; the file had 14 tests at base (found by P1). Owner: vidya-belief-substrate-program
- [ ] VB-REFACTOR-CONFORMANCE: implement prospective native capture/projector wiring for controlled regression verdicts. Source row and task are filed on this review branch; manual source audits remain dependency findings and past diagnostic runs are not backfilled.


## Problem

The operator asked for a review of the heavily built codebases for best practice, documentation,
modularity, compute performance, ease of resolving bugs, clean and effective tests, and code-size bloat.
The trees grew at roughly 10:1 insertions to deletions. epyc-orchestrator is ~862k lines of Python (src 201k, scripts 274k,
tests 358k) and grew another ~90k in the 17 days from 2026-10-07 to 2026-10-24. AutoKernel is ~490k lines
(282k source, 209k tests): it was rebuilt to a 3,450-LOC loop budget and regrew +278k net in August and +185k in
September, and its own regrowth guard sits 37x over budget (95,260 code lines vs 2,560). The worst hotspots are
single functions of 2,902 lines (`autopilot.py` `_run_loop_inner`, cyclomatic complexity 324), 5,518
(`loop/run.py` `main`, complexity 1,166) and 1,006 (`openai_chat_completions`). Neither repo had working CI:
the orchestrator has none, and the AutoKernel guards workflow was disabled by hand on 2026-09-10 after 168
red runs (its test steps never ran even before that).

## Test baselines and coverage

| Suite | Where | Result | Notes |
|---|---|---|---|
| epyc-orchestrator, full | container, origin/main + `refactor/hermetic-tests`, 2026-10-24 | 20,815 collected; **20,496 passed, 127 failed, 21 errors** (63 min, `-n 2`) | Before `refactor/hermetic-tests` the conftest could not even be imported off the production host. Failing ids: `data/orch_baseline_failing_ids.txt` |
| AutoKernel, full | container, 2026-10-07 | **10,576 passed, 476 failed, 87 errors** (23 min, `-n 3`) | ~58% host-dependent (root uid, CPUs < 32/64, /mnt/raid0); the rest is real rot nobody saw because CI was off. `release/test_t3*` cannot be collected at any standard checkout path |
| epyc-root `scripts/hooks/tests` | container | 313 passed with the scanner fixes (296 at base); same 11 failed / 25 errors on both sides | |
| CI | GitHub | orchestrator: none; AutoKernel: `disabled_manually` since 2026-09-10 | |

Per-file coverage is not mapped here: the suite is too large for a source-to-test table. Coverage gaps that
block a refactor are named inside each package (e.g. B1-03/B5-02: only 9 tests drove the real autopilot
loop; 11+ tests pinned its source TEXT; 28 AutoKernel test files grep `run.py` source).

## Operator decisions (2026-10-24, [`OPERATOR-DECISIONS.md`](../../research/refactor-audit-2026-10/OPERATOR-DECISIONS.md))

1. **Evaluator regime**: batch every change to `eval_tower.py`, `rubric_scoring.py`,
   `src/autopilot_core/tier_specs.py` and `orchestration/eval_registry.yaml` into ONE era event (package P5),
   together with an AST-normalized evaluator fingerprint, so later comment, format and pure-refactor edits stop
   splitting the AP-55 regime. Merging P5 is the single regime break; the operator picks the time.
2. **AutoKernel prune**: delete all three unreachable planes (the unified/standalone control plane rejected on
   2026-09-09; the `discovery_*`/`gpu_source_*` stack; `release/`), staying current with main and re-proving
   reachability from the live entry points at the current origin/main HEAD before every stage.
3. **CI**: add orchestrator CI (pull_request + workflow_dispatch only) and repair the AutoKernel workflow
   (the operator re-enables it in GitHub).
4. **Scope**: full program, paced at about 2 concurrent agents. The account has no extra-usage credits, so the
   work spans several 5-hour usage windows.

Standing inputs: hermetic tests approved (2026-10-07); keep an eye on bloat (2026-10-07); kernel (llama.cpp)
defects go to the champion fold as CH-xx recommendations, never as production patches (relayed operator rule,
2026-10-24); workspace-58's live-path and file boundaries (§Coordination).

## Branches (all pushed 2026-10-24; rebased on origin/main unless noted; NONE reviewed by a second agent yet)

| Repo | Branch | Commits | Contents | Merge notes |
|---|---|---|---|---|
| epyc-root | `refactor/containment-scanner` | 3 | scanner bypass fixes; degraded-mode regression fix (main since 84b0de13 lets `sudo mount` through with no scanner); behaviour-change note | **Operator review required** (safety boundary for INC-20260823); see `scripts/hooks/CONTAINMENT-SCANNER-CHANGES-FOR-REVIEW.md` on the branch |
| epyc-root | `refactor/refactoring-plan` | this | this handoff, the bug report, all evidence | docs only |
| epyc-orchestrator | `refactor/hermetic-tests` | 1 | conftest stub kernel store + host-RAM fallback (no-ops on the host), `ORCHESTRATOR_PATHS_KERNEL_ROOT`, ni63 pin refresh | **merge first**; every orchestrator branch below contains it |
| epyc-orchestrator | `refactor/request-path` | 9 | O1 stage 1: per-request state on the shared LLMPrimitives (A1-02/A2-01/A1-M2), model/REPL calls off the event loop (A1-01), per-request cancellation (A1-M1), no_web context (A4-M1), shared backend build (A2-04), region-lock release (A2-13), skill ids (A1-17) | production request path: review carefully; stage 2 (A2-02…A2-16) not started |
| epyc-orchestrator | `refactor/config-registry` | 14 | O3: stack-priors parse cache (A3-01/A1-03), fail-closed compile (A3-02), Settings factories (A3-07), topology-cache poison (A3-08), shadow thread (A3-09), env-override and crash fixes (A3-M1, A3-04, A3-06), OCR timeout (A3-15), registry-cache lock (A3-05), shim race (A3-16/A4-08), env.sh root (A3-M2), registry backoff (A3-19) | rebased with ni63 pin conflicts resolved (upstream fixture kept; pins of files this branch changes refreshed) |
| epyc-orchestrator | `refactor/scripts-cleanup-reviewed-01a16fc3` | accepted candidate | O6 rest source `6efa56265b68f402af736a1c1a2ee3df447849c1`; 190 launcher + 395 coverage pass, all four 100% floors and five NI63 controls pass; 32/32 blob/SHA proof; approved four pin changes exact, other 28 unchanged | Accepted source only; combined-tree validation remains under RESUME-4; no merge/deploy |
| epyc-orchestrator | `refactor/test-hazards` | 4 | O7: fence tests no longer aim destructive payloads at the REAL wiki (A6-01), checkout-write leak guard (A6-02), tmp_path not fixed /mnt/raid0 dirs (A6-09) | no test report (interrupted) |
| epyc-orchestrator | `refactor/test-isolation-reviewed-01a16fc3` | reviewed | Includes hermetic/test-hazards plus fixture-only A6-M1 trace/ledger isolation | Pushed `5e392a3c`; 189 runtime/trace tests + 7 E8 wrappers pass, 1 intentional skip; reviewed, unmerged |
| epyc-orchestrator | `refactor/config-reviewed-01a16fc3` | reviewed | Includes O3 + accepted isolation, concurrent registry-backoff fix and scoped alias-import stress | Pushed `6558beb7`; 548 O3 tests + 524 alias targets pass, 4 skips; mixed-alias cycle is RESUME-7 |
| epyc-orchestrator | `refactor/request-reviewed-01a16fc3` | reviewed | Includes O1 stage 1 + accepted isolation and cancellation during initial streaming generation | Pushed `142bb5df`; 1,011 tests pass, 3 skips; reviewed, unmerged |
| epyc-orchestrator | `refactor/autopilot-gate-reviewed-01a16fc3` | reviewed | Includes P2 + accepted isolation and real-fixture pre-P2 snapshot migration controls/runbook | Pushed `db17808e`; 1,018 tests pass/1 skip; HIGH/CRITICAL integration review and owner-boundary snapshot rebuild required |
| epyc-orchestrator | `refactor/autopilot-loop` | 6 | P1 stage 1 (safety net): the real loop driven by a harness instead of source-text slicing (B1-03/B5-02), shared frontier-admission predicate (B5-08), hook containment (B1-15) | Initial P1 stage-1 branch; reviewed rest is on `refactor/autopilot-loop-reviewed-01a16fc3` |
| epyc-orchestrator | `refactor/autopilot-loop-reviewed-01a16fc3` | reviewed | P1 rest B1-01/B1-M1/B1-M2/B1-04/B1-08/B1-09/B1-14/B1-13; source `36e1bc55aa40f35965a941e81fdc593a22abd520` | Accepted, unmerged; RESUME-4 combined validation remains |
| epyc-orchestrator | `refactor/autopilot-gate` | 15 | P2: safety-gate seq upgrade (B2-02), one-sided MAD (B2-03, **changes what is admitted to learning**), refusal codes (B2-09), validator/replay (B2-20), hypervolume memo + fold + off-loop dashboard (B5-01), bounded snapshot replay (B5-M1), cluster identity (B5-M2), era guard (B5-16), dead modules (B5-09), `__init__` (B5-13), drop counts (B5-12) | B2-03 is a decision-semantics change: review it as such |
| epyc-inference-research | `refactor/autokernel-loop-bugs` | 1 | **WIP**: `run._git` checks git's exit status; failed rollback aborts the run (C1-05) | **do not merge to main**: AutoKernel launches are under an operator hold; workspace-58 merges it with a deliberate re-pin when the hold lifts |
| epyc-inference-research | `refactor/autokernel-rollback-reviewed-01a16fc3` | 3 | Completes C1-05: includes WIP, catches rollback timeout/spawn errors, behavioral regressions and checkpoint | Reviewed; 401 targeted loop tests + 23 subtests pass. Pushed at `1b58b115c`; hold/re-pin applies, no launch or merge |
| epyc-orchestrator | `refactor/orchestrator-integration-01a16fc3` | reviewed private candidate | Combined orchestrator candidate | `851955112b8ba8c2911a7684469551afa1541623`; validated relative to immutable base `84f6f6f1`; no main promotion/deployment |
| epyc-orchestrator | `refactor/orchestrator-ci-01a16fc3` | B1-tested pre-fixture local merge | O8 CI, central pytest gates and NI63 provenance closure | `753e0287` contains `713edf671` + `851955112`; focused 13 pass; strict collection baseline 20,658/20,645 selected vs candidate 20,666/20,653, 0 removed/8 added/13 identical exclusions; post-B1 owned fixture validation pending; full suite/native/coverage open; future `codex/*` only |
| epyc-orchestrator | `codex/refactor-autopilot-actions-01a16fc3` | reviewed private candidate, published | P3: actions, config applicator, controller IO, planner, journal and baseline-pin helper | `fb5db1a0a24b92172643bb670c77a4343a508c96`, remote-exact verified, clean worktree; final 12-file 402 pass/1 skip and three-file formatting/protected/source-custody closure pass; prior failures retained, no main/deploy |
| all three | `claude/vigilant-thompson-shpyh0` | — | superseded by the `refactor/*` branches above | ignore / delete |

Merge order (orchestrator): reviewed hermetic harness + test-hazards/A6-M1 isolation →
`refactor/config-registry` → `refactor/request-path` → `refactor/autopilot-gate` →
`refactor/autopilot-loop` → completed `refactor/scripts-cleanup`.
The branches carry patch-equivalent copies of the hermetic commit, not one shared commit identity.
Known integration conflicts: gate/loop `autopilot.py` (retain cluster identity and the admission helper),
config/cleanup ni63 registry-loader pin, and hazards/cleanup conftest plus the deleted E8 test.
Each branch rebased cleanly on origin/main on 2026-10-24; later upstream commits may need another rebase. Nothing
merged to orchestrator main is served until the shared clone is synced (operator approval).

## Issue inventory (summary; every finding with evidence, verifier notes and proposal is in the findings files)

| Unit | Findings | Sev ≥ 4 | Bloat est. (LOC) | Biggest problems |
|---|---|---|---|---|
| A1 API layer | 23 | 6 | 1,100 | blocking model/REPL calls on the uvicorn loop; shared per-request state; 1,006-line openai handler, 2 near-identical /chat/stream impls; per-request YAML and ps parsing in the dashboard |
| A2 inference hot path | 24 | 6 | 2,300 | per-request state on a shared LLMPrimitives reroutes requests under concurrency; read-timeout truncation reported as success; quadratic early-stop; 4 drifted llama_server lanes; 12 copies of the escalation chain |
| A3 config/registry/runtime | 27 | 3 | 2,700 | config declared 4 times; fail-open stack-priors compile; reset_config cannot refresh; poisoned caches |
| A4 REPL/tools/top level | 26 | 1 | 3,000 | production read_file swapped for an unchecked builtin; REPL web tools bypass role permissions and no_web; 4 parallel tool stacks |
| A5 orchestrator scripts | 28 | 2 | 45,000 | the retired E8 chain (32.6k incl. tests); a forked scripts/lib; 71 src→scripts imports; 196 sys.path hacks; name-pattern kills |
| A6 orchestrator tests | 20 | 2 | 5,200 | not hermetic; destructive payloads aimed at the real wiki; no CI; 89 assertion-free tests; ~50 source-text tests |
| B1 autopilot loop | 22 | 3 | 300 (+~9k movable) | 2,902-line `_run_loop_inner`; plain `save_state()` clobbers an operator pause (H4 class); 8 copies of the halt latch |
| B2 eval + safety gate | 22 | 1 | 1,250 | parse-failure telemetry zeroed on every T1/T2 trial; two-sided MAD admits regressions as improvements; per-question registry re-parse |
| B3 actions/planner/journal | 27 | 0 | 1,500 | pgrep name-pattern process picks; NaN passes bounds checks; journal deep-copied per trial |
| B4 satellites | 22 | 0 | 7,400 | applied one-shot ratifiers and era-pinned collectors still in tree; vendored judges unprotected |
| B5 autopilot_core + tests | 20 | 3 | 1,450 | exponential hypervolume per replayed trial (3.6-5.7 s, twice per trial); evaluator fingerprint hashes raw bytes |
| C1 AK loop core | 27 | 5 | 26,600 | 5,518-line `run.main`; `_git` ignores exit status; CI off |
| C2 AK loop periphery | 18 | 2 | 72,000 | the rejected unified/standalone plane (~61k incl. tests) still imported through 5 thin bridges |
| C3 AK controller | 24 | 1 | 37,000 | unreachable discovery_*/gpu_source_* stack; v9 digests pinned for "v10"; stdlib `resource` shadowed |
| C4 AK evaluator/execution (UNVERIFIED) | 18 | 3 | 5,700 | non-inferiority e-value labelled IMPROVEMENT; attestation never hashes the libggml DSOs |
| C5 AK release + top level (UNVERIFIED) | 16 | 7 | 65,000 | dormant release/ plane; guard counts only loop/; journal validator turns ImportError into "invalid payload" |
| C6 AK tests (UNVERIFIED) | 18 | 5 | 9,400 | CI cannot reach its test steps; 38 tests broken by a helper change; jobs=32 fixture vs CPU count |

(Bloat estimates overlap between C units; the approved three-plane prune is ~150k LOC including tests.)

## Wave 1: bugs, hazards, ruled deletions (packages in [`packages/wave1.json`](../../research/refactor-audit-2026-10/packages/wave1.json))

| Pkg | Theme | State 2026-10-24 |
|---|---|---|
| O1 | request path: concurrency, event loop, failure semantics | stage 1 done (9/9, on `refactor/request-path`); stage 2 (A2-02, A2-M1, A2-M2, A2-03, A2-05, A2-11, A2-16) not started |
| O3 | config/registry/runtime correctness + stack-priors cache | done (`refactor/config-registry`) |
| O4 | REPL/tools permission bypasses and structured-mode defects | accepted on `refactor/repl-correctness-01a16fc3` at `acfd5f8c`; 557 tests pass and eight parent negative controls fail as expected; offline drift, ruff, compile, diff and snapshot gates pass |
| O5 | dashboard request-path cost | not started |
| O6 | scripts bugs + ruled deletions | rest accepted at `6efa56265b68f402af736a1c1a2ee3df447849c1`; launcher/coverage suites and four floors pass; integration remains separate |
| O7 | test-suite hazards | A6-01, A6-02, A6-09 committed; A6-M1, A6-03, A6-12, A6-13, A6-11, A6-17 not started |
| P1 | autopilot loop: safety net, then loop bugs | stage 1 and P1 rest accepted at `36e1bc55aa40f35965a941e81fdc593a22abd520`; combined-tree validation remains separate |
| P2 | safety gate + autopilot_core | done (B2-11 skipped: upstream already split `check()`; B2-17 no change per verifier) |
| P3 | actions, config applicator, controller IO, planner, journal (B3-01 pgrep) | not started |
| P4 | autopilot satellites bloat (one-shot ratifiers, era-pinned family, dead modules) | not started |
| K1 | AutoKernel live-loop bugs and red tests | C1-05 WIP only |
| K2 | AutoKernel evaluator/execution integrity (C4-05, C4-06, C4-10 remain) | C4-08/C4-16/C3-02 accepted at `68724da5ba093cf3cec3909a81491932002dd4ce`; package incomplete |

## Wave 2: decision-dependent and structural ([`packages/wave2.json`](../../research/refactor-audit-2026-10/packages/wave2.json))

| Pkg | Theme | Depends on |
|---|---|---|
| P5 | **evaluator: ONE batched era event**: B5-03 fingerprint normalization FIRST, then B2-01, B2-M1, B2-M2, B2-10, B5-06, B5-07, B2-19, perf B2-04/05/06, refactors B2-07/08/14/15/18/12/13, B5-14, B3-09; commit subjects prefixed `evaluator-era:` | P2 merged |
| K3 | **AutoKernel three-plane prune**, staged by approved plane; rebase on origin/main and re-prove closure before EVERY stage, including retained campaign CLI and dynamic/cross-repo roots; honor INF64's per-file retention manifest and live belief-source contracts; Arena is excluded | K1; operator hold lifted for merge |
| K4 | Repair CI infrastructure early (independent steps, yaml dependency, honest collection floors); set the all-package size ratchet only after the approved prune | ratchet depends on K3; infrastructure does not |
| O8 | orchestrator CI (PR + manual only; hermetic suite minus a reviewed host-only list with reasons), honest `make gates` (format-check only changed files; 1,471 files fail a whole-tree check), ni63 pin design (record hashes for provenance instead of asserting a past commit's bytes; the pin is already red on main for `orchestrator_stack.py`) | merge reviewed integration candidate `851955112` into `refactor/orchestrator-ci-01a16fc3`, then validate package |
| D1 | autopilot `_run_loop_inner` decomposition (B1-02 staged seams) | P1 merged |
| D2 | API: openai_compat and /chat de-duplication | O1 merged |
| D3 | inference hot path: llama_server lanes, `_execute_turn`, escalation chain | O1 merged |
| D4 | AutoKernel `run.main` decomposition (behavioural tests first; evidence identities hash whole files: C1-M1) | K1, K3 merged |
| D5 | config/registry/runtime consolidation (region-lock: bug fixes only) | O3 merged |
| D6 | REPL/tools consolidation | O4 merged |
| D7 | orchestrator scripts structure (no `orchestrator_stack.py` restructuring) | O6 merged |
| D8 | orchestrator test-suite consolidation | last |
| D9 | autopilot remaining structure | P1, P3, P4 merged |
| D10 | AutoKernel remaining structure | K1, K2, K3 merged |

Deferred, not in any package ([`packages/deferred.json`](../../research/refactor-audit-2026-10/packages/deferred.json)):
A5-10, A5-16, A5-17, A5-19 restructure `scripts/server/orchestrator_stack.py`, a live path on the host (workspace-58,
2026-10-24); their proposals in `findings-orchestrator-core.md` are ready to run when that file is quiet.
C5-05 (delete the `campaign.py` CLI cluster, ~20k LOC) is a fourth plane the operator did not approve.
C1-22 disappears with the unified plane.

## How to resume

1. `python3 research/refactor-audit-2026-10/packages/mkpkg.py research/refactor-audit-2026-10/packages/wave1.json <scratch>/pkg`
   regenerates the per-package briefs (same for `wave2.json`).
2. `research/refactor-audit-2026-10/packages/impl_workflow_w2.js` is the implementer/reviewer prompt contract
   (one worktree per package, re-verify at HEAD, failing test first for bugs, one commit per finding, adversarial
   review of the diff). Point its paths at the new scratch dir.
3. Start each package from its pushed `refactor/*` branch (or from origin/main for unstarted packages), rebased on
   origin/main. Commit subjects identify related work; inspect explicit WIP/skip/test/review/merge state before
   treating a finding as complete. Status per finding:
   `research/refactor-audit-2026-10/data/finding-status.json`.
4. Every package needs its adversarial review before merge; none has had one.

## Coordination (workspace-58, 2026-10-24)

- Push only `refactor/<topic>` branches with an explicit refspec, rebased on origin/main; never main.
- Live paths on the host: no structural refactor of `scripts/server/orchestrator_stack.py`, `scripts/region-lock`,
  `src/runtime/*region_lock*`, `scripts/gitnexus-analyze.sh` (bug fixes only), and those keep their paths and
  CLIs. Never the llama.cpp trees. `scripts/benchmark/` and `scripts/kernel_rnd/autokernel/` are pinned by SHA by
  running jobs: merge with a deliberate re-pin.
- Do not hand-edit the index files, `.index-state.json`/`.index-graph.json`, `backlog-priority.json`,
  `wiki/source_manifest.json`, `progress/*-workspace-58.md`, `INCIDENT_LOG.md`, or the handoffs workspace-58 listed.

## Success criteria

1. Every finding is either implemented with a regression or characterization test, or recorded as skipped with
   a reason (already fixed, does not reproduce, unsafe).
2. The orchestrator suite collects and runs off the host, and no package adds a failure to the baseline set
   (`data/orch_baseline_failing_ids.txt`).
3. AutoKernel source shrinks by roughly the approved ~150k LOC, the live-loop and decision-arithmetic suites stay
   green, and the regrowth guard is a satisfiable ratchet that CI runs.
4. Orchestrator CI runs on pull requests; the AutoKernel workflow can go green when re-enabled.
5. No function in the touched hotspots stays above ~300 lines without a recorded reason.

## Notes

- **The evaluator files are booby-trapped**: any byte change to the four fingerprinted files splits the AP-55
  regime (B5-03). Until P5 lands, do not reformat or edit them, including blanket `ruff format`.
- **ni63 source pins**: `tests/fixtures/ni63_capacity_child/source_clone.py` byte-pins ~30 production files to
  a past commit. Any change to a pinned file must refresh its (blob sha1, sha256). The pin for
  `scripts/server/orchestrator_stack.py` is already stale on main, so those 4 tests fail there too. O8 fixes the design.
- **Guards found broken on the way** (epyc-root, `refactor/containment-scanner`): the filesystem-containment
  scanner allowed writes outside the roots when a redirect followed the destination (`cp secret /outside
  2>/dev/null`), checked the branch instead of the path in `git worktree add`, and missed shell structure; and
  since 84b0de13 its degraded mode allows `sudo mount`. Also: `scripts/harness/strategy_projection_report_capture.py`
  `TRUSTED_APP_SOURCES` has 6 of 11 pins stale at base (reported by O3).
- **Unverified units**: C4, C5, C6 findings were never adversarially verified; the packages re-verify them first.
- **Not filed (explicit decline)**: `scripts/hooks/tests/test_harness_guard_parity.py::test_generator_check_exits_zero`
  fails identically on main in the container; it compares against the host's generated opencode config, so it
  says nothing about this work.
- **Usage pacing**: 6 concurrent agents exhausted a 5-hour window in about 55 minutes on 2026-10-24 (extra usage
  rejected: `out_of_credits`); 2 concurrent agents is the sustainable rate.

### Native packet preparation checkpoint — 2026-10-27 22:55 UTC

- [x] **HIL-CHECKPOINT-NATIVE-PREP** — source-bound one-unit/three-slot canary and separate20-unit pilot prepared with immutable slot evidence, runtime-receipt resume refusal and captured detached-child cleanup. Full fake-server entries and all six quarter alternatives passed scoped26–27 PF, normal admission and validator0/0. Old pilot excluded; no model execution, band or quality claim. See [packet record](../../progress/2026-10/2026-10-27-native-repair-packets-2255.md). ✅ 2026-10-27 [no-belief: preparation and synthetic fixtures only]
- [x] **M4-HOL-V2-NATIVE-PREP** — fix harness prematurely stopping its own long-prefill server; full fakeHTTP phaseA/B fixture, STOP/failure/deadline/cleanup, source-bound PF and normal admission passed0/0. Claude armed GPUv2 PID1707428; native rerun outcome pending, parentM4 open. ✅ 2026-10-27 [no-belief: preparation and synthetic fixtures only]
- [x] **M4-OFF-NATIVE-READOUT** — reviewed all7 prompt hashes and21 native responses, exact content+reasoning identity against both C5 controls,0mismatch/0nondeterminism/0incomplete. Native run complete in~146s; correctness observation only. Preserve original protocol/co-tenant limits; no wholeM4, speed or promotion claim. ✅ 2026-10-27 [belief: cc]

### Dispatch checkpoint — 2026-10-27

- [x] **M4-CURRENT-C5-OFF-PAIR-PREP** — four-load current-C5/M4 OFF packet prepared against the ratified paired0.9–1.1 rule; full fakeHTTP/lifecycle/guard fixtures, source-bound PF/admit/validator0/0 passed. GPU7800/min6000s, source e56b292276b33a93b450bb0e82bf7d7e2eaa36d362676eaf0e8a3480efa64023; no actual C2 result or parent completion. Existing family extension and OPEN reader/canary task filed. ✅ 2026-10-27 [no-belief: preparation and synthetic fixtures only]
- [x] **ATT-CANARY-V2-PREP** — repaired bundled libpciaccess loader path, live grant/STOP/HOLD/deadline guard and captured process-group cleanup. Actual CPU-only loader controls plus model-free lifecycle fixtures and current source-bound PF/admit/validator0/0 passed; GPU900/min600s. No GPU trace, MFMA count or efficiency claim. ✅ 2026-10-27 [no-belief: preparation and synthetic fixtures only]
- [x] **HSF5P-RESTORE-R11-DIAGNOSTIC** — the repaired-C5 scheduled run completed `rc0`; three save/erase/restore/continuation checks each reported matching 4,116-token counts and equal saved/read byte counts (740,054,204; 938,916,368; 938,916,368). The own server was reaped and an independent native-output/cleanup reader passed. This is one diagnostic run, with no timing, quality or promotion verdict. Evidence: `/mnt/raid0/llm/tmp/hsf5p-r11-repair-20261028/runs-official/` and the keeper launcher log. ✅ 2026-10-28 [belief: cc]
- [x] **ATT-INSTRUCTION-STREAM-DIAGNOSTIC** — a bounded real gfx90a probe produced raw SE0/SE4 ATT data and its native kernel exited `rc0`; the wrapper refused `rc1` at strict decoding. Offline GPU-denied decoding of the two streams from that single run found 32 ordered repetitions of the eight static MFMA instructions. Both decoders reported zero waves, so per-wave completeness and trace loss remain unknown. This narrow instruction-stream observation is not the decoded-wave canary, an efficiency claim or a READY result. Evidence: `/mnt/raid0/llm/tmp/att-decoded-r5-prep-20261028/checked-se0.log` and `checked-se4.log` in the same directory. ✅ 2026-10-28 [belief: cc]
- [x] **HIL-HEAVY-PILOT-PREP** — full20-task/60-slot cohort prepared at24threads with3600/min1800s and four mutually exclusive quarter placements. Native two-unit/six-slot fixture, resume/no-redraw and detached-child cleanup, all scopedPF/admit/validator0/0 passed; one task rather than four independent studies. Existing HIL producer family, no quality/band result. ✅ 2026-10-27 [no-belief: preparation and synthetic fixtures only]
- [x] **LB49-SCOPED-AUTHORIZATION-RECORDED** — operator approved the exact pinned experimental port, including shared parser CRITICAL43 and all six pinned input hunks; private experimental source/build/tests only. Production/deployment/promotion remain excluded. Expanded actual graph qualification and build preparation continue under owner compute; this is not a risk downgrade or completed port. ✅ 2026-10-27 [no-belief: operator authorization, no measurement]

### CPU layout source enrollment checkpoint — 2026-10-28

- [x] **CPU-LAYOUT-SOURCE-ENROLLMENT** — register the YaRN CPU shard and CL3 quarter profile layouts with open strict-reader/planning tasks, and record the repaired M4 v2 producer scope. This is source enrollment and failure documentation, not validated launcher readiness. YaRN s2 was granted before this extension publication; its timing is disclosed without retrospective warrant. See [checkpoint](../../progress/2026-10/2026-10-28-launcher-repair-and-enrollment.md). ✅ 2026-10-28 [no-belief: source enrollment and maintenance only]
- [x] **RUN13-M4-NATIVE-REPAIR** — repaired deadline descendant cleanup; actual engine failure fixtures, actual same-entry host preflight, stable engine seal and fresh source-bound M4 row are complete and handed to Claude; owner armed row PID 2427508 at 01:13. The parent M4/C2 native result remains pending; preserve the old false COMPLETE and all native partial evidence. ✅ 2026-10-28 [no-belief: launcher implementation, synthetic controls, and no-model preflight; no native M4 result]

### Validated run13 engine and HIL discovery enrollment — 2026-10-28

- [x] **RUN13-ENGINE-REPAIR-VALIDATED** — versioned engine passes actual complete-job PASS/FAIL, load failures, STOP/HOLD, watcher/engine deadlines, stale marker and zero-incomplete fixtures; child-exit and between-load TERM regressions pass and owned descendants drain. Engine SHA256 `fbcf07ca57b4c6d938151e2c3269191edb19241a35a0d2057bf7e8b0d85a171a`, exact logs in [checkpoint](../../progress/2026-10/2026-10-28-launcher-repair-and-enrollment.md). Per-consumer real-entry PF/admission remain mandatory; this does not complete M4. ✅ 2026-10-28 [no-belief: launcher implementation and synthetic failure controls]
- [x] **HIL15-DISCOVERY-SOURCE-ENROLLED** — register the fixed 60-task discovery assessment and OPEN strict-reader/planning task before new measurement. Gold/novelty/no-redraw/native fake-entry/selection controls pass; actual host prerequisites pass without model load. Four distinct 15-case shard rows now have nine validated placement variants; seven alternative placements remain unvalidated. The validated variant receipts are recorded separately; the cohort outcome remains open. ✅ 2026-10-28 [no-belief: prospective enrollment and synthetic controls]


### Qualified launcher preparation and HIL shard delivery — 2026-10-28

- [x] **UFH14-SERVING-TRACE-QUALIFICATION** — source-qualified serving-call integrity LB6 launcher preparation is complete on orchestrator main `6b25fe9acf1bc8b8a9c2908c4d918483f5811c14`. The 106-case suite plus six fake-entry cases passed; source-bound PF used nonce `ae1b7fc54bb7a9d71ac789f97670c9800a47008f5036d868`, followed by normal admission and validator 0/0. PF was scoped to CPUs 26–27 while the row claims 0–23; normal placement remains a live-entry check. Packet: `/mnt/raid0/llm/tmp/refactor-01a16fc3/ufh14-serving-calls-ready/`; 106-case test log `prep/20261028T005856Z-2374852/command.log`, six fake-entry test log `prep/20261028T010837Z-2427965/command.log`, PF receipt `dryrun/ae1b7fc54bb7a9d71ac789f97670c9800a47008f5036d868/pass.json`, and final admission/validator log `prep/20261028T011823Z-2481749/command.log`. Preparation only; no actual model/server result is claimed. ✅ 2026-10-28 [no-belief: source implementation and model-free validation only]
- [x] **HIL15-DISCOVERY-SHARD-DELIVERY** — four distinct 15-case shard rows passed source-bound PF/admission/validator checks, with nine validated placement variants and seven alternatives unvalidated. Shards s0/s1/s2 were delivered to Claude and armed; s3 is held at the M4 SMT-sibling timing boundary. The native-readiness placement record is `/mnt/raid0/llm/tmp/refactor-01a16fc3/hil15-decision-cohort-ready/PLACEMENT-CHECKPOINT.json`. This records preparation and owner handoff only: no shard outcomes or HIL cohort result. ✅ 2026-10-28 [no-belief: packet preparation and delivery; no HIL result]

- [x] **HIL15-SHARED-VENV-INCIDENT-ATTRIBUTION** — root cause attribution is filed: the authorized M4 CPU scope helper capture at `scope-check/20261028T015457Z-2658028/` ran `scope.sh --backend cpu`; its `command.log` reports building `epyc-orchestrator`, uninstalling one package, and installing one package into the shared editable environment. Helper PID `2658028` is not an installer PID. HIL s1 retains six completed slots, with 39 unstarted; replay 02-2 overlap effect remains undetermined. Preserve original evidence; no redraw and no no-impact claim. The owner has prohibited further shared orchestrator-venv writes and requires private environments; private-runtime v5 continuation was separately preflighted/armed. See [incident checkpoint](../../progress/2026-10/2026-10-28-codex-ni-01a16d6b-hil-venv-incident.md) and [publication audit correction](../../progress/2026-10/2026-10-28-codex-refactor-01a16fc3-hil-venv-publication-audit.md). ✅ 2026-10-28 [no-belief: incident attribution and runtime repair only; no HIL outcome]

- [x] **M4-C1-NATIVE-READOUT** — file the reviewed HOL-v2 mechanism PASS (512 B/A0.9990076596;2048 B/A0.9975592176;12 valid collision rows) with original source/rule hash checks and the full unobserved NI co-tenancy disclosure. The earlier harness-truncated attempt is superseded; current-C5 OFF paired C2 and the parent M4 gate remain separate. See [checkpoint](../../progress/2026-10/2026-10-28-launcher-repair-and-enrollment.md). ✅ 2026-10-28 [belief: cc]

- [x] **M4-GPU-QUALITY-SOURCE-ENROLLMENT** — enroll the prospective role-paired GPU quality source and open its strict-reader/planning task. Native GPU quality and the parent fold gate remain unmeasured; source enrollment does not make the launcher ready. ✅ 2026-10-28 [no-belief: prospective source enrollment only]

- [x] **M4-GPU-QUALITY-R12-RESULT** — the paired architect Qwen3.8-27B GPU quality gate completed `rc=0` on 2026-10-28 with both arms using concurrency four. MMLU-Pro: 118/200 versus 118/200; GPQA: 117/195 versus 115/195. Both candidate scores meet the predeclared baseline-minus-five-percentage-point tolerance; all 790 rows have zero recorded errors and truncations. Actual GPU residency, four concurrent slots per cell, matching prompt identities and captured-server cleanup were independently checked. Native artifacts and comparisons: `/mnt/raid0/llm/tmp/codex-m4-gpu-quality-r12-native/output/`. Embedded measurement and attestation hashes verify; ledger ingestion is not claimed. This is the quality gate only, not a parent-fold, speed or promotion result. ✅ 2026-10-28 [belief: cc]

- [x] **M4-RECUT-C3-DIAGNOSTIC-RESULT** — the source-bound run13 r2 diagnostic completed `rc=0` at 19:07 UTC with native verdict **FAIL**. All seven champion identities were deterministic; the candidate matched both passes on five identities but differed on pass 2 for both pair4k identities. Independent checks validated all 28 successful 96-token records and recomputed their token/text hashes; the two requested-slot client intervals overlapped in both passes and arms. This proves client overlap, not simultaneous server-slot residency; C1/C2 and promotion were outside this diagnostic. The original run12 attempt failed `rc6` before model load and is superseded for this result. Evidence: `/mnt/raid0/llm/tmp/codex-m4-c3-original-r2-20261028/attempts/run-20261028T185919367038969/`. ✅ 2026-10-28 [belief: cc]
- **Diagnostic-instruction violation:** r2's inherited `make-record.py` created `PRELOAD_WARRANT.json` in the completed diagnostic attempt despite the operator's prohibition on diagnostic receipts/seals. Preserve the file as evidence, do not treat it as a diagnostic receipt or rely on it for the finding; the follow-up removes this writer.
- [x] **M4-RECUT-C3-PAIR-DIVERGENCE** — investigate the two pair4k pass-2 divergences and measure both server admission orders on both images. The controlled-order diagnostic completed `rc=0` on 2026-10-28: within each order, all three repetitions matched between images, while 0→2 and 2→0 differed starting at token index 2 for both slots on both images. Independent audit verified all 24 raw completions and hashes, all 12 client overlaps, native server admission ordering, GPU residency and server teardown. This is an order-associated observation in this run, not a proven mechanism or a promotion decision. Evidence: `/mnt/raid0/llm/tmp/codex-m4-order-diag-20261028/attempts/run-20261028T192253258894951/ORDER-DIAGNOSTIC.json`. ✅ 2026-10-28 [belief: cc]
- [x] **M4-C3-ORDER-CONTROLLED-DIAGNOSTIC** — the controlled successor completed rc0 under the MI210 grant. Its C3 condition passed: all seven champion identities were deterministic across both passes and both candidate-off passes matched; pair4k logs recorded 0→2 admission in each pass of each arm with overlapping client request intervals. Overall native verdict is INCOMPLETE because C1/C2 were not measured. Client overlap and observed admission order do not prove simultaneous server-slot residency, and this does not authorize a full M4 or production/fold gate. The original C3 failure remains preserved above. Evidence: `/mnt/raid0/llm/tmp/codex-m4-c3-order-controlled-20261028/COMPLETE` points to the retained `VERDICT.json` (SHA-256 `784cca3dd1ba7701cc418bbb62f183ed1df960d49594698307757c9226506f2c`); controlled amendment `PREDECLARATION.md` SHA-256 `fb939843ebb42d9eeb7b7bd7af0dcd9033354a36a09a83ceee5e169bff88b213`. The completed manifest names an older scratch log reader; retain that reader and the byte-identical copy in this run directory. ✅ 2026-10-29 [no-belief: diagnostic source enrollment is prospective; no measurement tuple]
- [ ] **M4-RECUT-ORDER-ROOT-CAUSE** — trace the observed admission-order sensitivity in the SRPF-off path and determine what further controlled evidence is needed to explain it; preserve the two-image result and avoid attributing a kernel cause without proof.
- [x] **M4-ORDER-SPEC-CONTRAST** — the C5 diagnostic completed `rc=0` at 19:53 UTC. Across three repetitions per condition, both requested slots changed with 0→2 versus 2→0 when DFlash was on; with DFlash off, slot 0 stayed identical and slot 2 still changed. The two configurations also differed beyond speculative decoding, including draft memory. A separate raw-record check verified all 24 responses, hashes, 12 client overlaps, recorded server admission orders, GPU residency and cleanup. This shows the order-associated difference can appear without DFlash for slot 2; it is not a causal mechanism, general performance or promotion claim. Evidence: `/mnt/raid0/llm/tmp/codex-m4-order-spec-diag-20261028/attempts/run-20261028T194522838332151/ORDER-DIAGNOSTIC.json`. ✅ 2026-10-28 [belief: cc]
- [x] **M4-ORDER-DIAGNOSTIC-READY** — prepare the controlled-arrival-order follow-up across C5 and M4-off. The final same-launcher real GPU smoke ran 146 seconds, completed four ordered 0→2 pairs, and verified GPU residency and cleanup; a separate cutoff returned `rc75` with verified cleanup. The keeper queued it at 19:17 UTC with zero refusals. Manifest: `/mnt/raid0/llm/tmp/compute-flags/ready/armed/codex-m4-order-diag-20261028.json`. The scheduled reverse-order and paired-image comparison remain unmeasured. ✅ 2026-10-28 [no-belief: diagnostic smoke and launcher preparation only]

- [x] **LB49-DIAGNOSTIC-PUBLISH-GATE** — remove the self-imposed requirement that the already-pushed diagnostic source registration be an ancestor of `origin/main`. The replacement publisher verifies the actual remote branch, registration commit and exact source/task contents while retaining real-smoke, model, retention and collision checks. Its bounded watcher is running; LB49 itself still requires a real free-quarter smoke and has not been published READY. ✅ 2026-10-28 [no-belief: publisher repair only; no measurement]
- [x] **LB49-DS41-PAIRED-DIAGNOSTIC** — the repaired launcher completed `rc0` on 2026-10-28 under a real q0 grant. Both matched private CPU build arms loaded canonical DS41 after separate 739 GiB admissions and returned successfully to the same short prompt. Both answered Paris, but their raw output text differed; no parity conclusion follows. Independent checks matched both log hashes and the final result hash, verified both child PIDs had exited, and confirmed the result is non-partial and diagnostic-only. This is a narrow operational observation, not an attention-sink, route-coverage, quality, performance or promotion result. Native output is referenced by `/mnt/raid0/llm/tmp/lb49-r11-source-draft-20261028/COMPLETE.json`. ✅ 2026-10-28 [belief: cc]

- [x] **M4-CPU-CALIBRATION-SOURCE-ENROLLMENT** — enroll prospective architect CPU load and warmup memory samples and open their strict-reader/planning task. This is preparation only; no model execution or resource peak claim. ✅ 2026-10-28 [no-belief: prospective source enrollment only]

- [x] **M4-WORKER-CALIBRATION-SOURCE-ENROLLMENT** — enroll prospective worker/frontdoor CPU load and warmup samples and open their strict-reader/planning task. Preparation only; no model execution or peak claim. ✅ 2026-10-28 [no-belief: prospective source enrollment only]

- [x] **M4-VISION-CALIBRATION-SOURCE-ENROLLMENT** — enroll prospective vision CPU load and warmup samples and open their strict-reader/planning task. Preparation only; no model execution or peak claim. ✅ 2026-10-28 [no-belief: prospective source enrollment only]
