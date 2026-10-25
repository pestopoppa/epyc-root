# Handoff: Refactoring — orchestrator, autopilot and AutoKernel (multi-repo debt program)

**Status**: ACTIVE — operator resumed implementation 2026-10-24 after an independent handoff audit; review and finish existing branches before integration
**Created**: 2026-10-07
**Updated**: 2026-10-25
**Priority**: High
**Scope**: epyc-orchestrator (`src/`, `scripts/`, `tests/`, `scripts/autopilot/`, `src/autopilot_core/`);
epyc-inference-research `scripts/kernel_rnd/autokernel/`; epyc-root `scripts/hooks/` (guard bugs found on the way)
**Estimated effort**: 382 findings → 26 packages (12 in wave 1, 14 in wave 2); deletion size is a planning estimate, subject to current per-file reachability and retention contracts
**Scratch**: `/mnt/raid0/llm/tmp/refactor-01a16fc3/` · worktrees: `/mnt/raid0/llm/worktrees/refactor-01a16fc3-*` · root integration: `/mnt/raid0/llm/worktrees/refactor-audit-01a16fc3-root`

Each package uses its own branch/worktree and scratch subdirectory. Tests whose safety contracts
require `/tmp` use the manually cleaned exception `/tmp/refactor-01a16fc3/`. The earlier cloud run's
`/workspace/wt/` and expired container scratch paths are historical, not host cleanup targets.

**Start here:** the [Pending work](#pending-work) checklist is the queue; §Branches says what each pushed
branch holds and how to merge it; per-finding evidence is in `research/refactor-audit-2026-10/findings-*.md`.

Origin: cloud refactor-audit session (claude.ai/code session_01C4SLLAQhop8AA9rJJusAYj), run in an ephemeral
4-CPU container on fresh clones, never on the host. Evidence, data and tooling:
[`research/refactor-audit-2026-10/`](../../research/refactor-audit-2026-10/README.md). Bug report:
[`BUG-REPORT-autopilot-autokernel.md`](../../research/refactor-audit-2026-10/BUG-REPORT-autopilot-autokernel.md).

> **Review-branch registration:** the resumed owning main applied the prepared thin row as RTG-60 in
> `routing-and-optimization-index.md` on this isolated review branch. Shared/canonical index files remain
> untouched; workspace-58's publication boundary still applies. Source wiring is filed prospectively on
> this branch as VB-REFACTOR-CONFORMANCE, not as an optional applicability decision.

## Pending work

Historical implementation checkboxes below mean committed on the named branch, not reviewed or merged.
New completion records name their validation and integration state explicitly. A finding ID in a commit
subject establishes association only; WIP, skipped, tested, reviewed and merged are distinct states.

### Resumed execution (2026-10-24, session 01a16fc3)

- [x] RESUME-1: audit pushed branches and current upstream state; identify unsafe pruning assumptions, rollback failure-path gap, test isolation prerequisite and integration conflicts. Evidence: [audit checkpoint](../../progress/2026-10/2026-10-24-refactor-audit-01a16fc3.md). ✅ 2026-10-24
- [x] RESUME-2: review hermetic-tests + test-hazards and isolate A6-M1 trace/ledger writes in fixtures. Orchestrator `87540dae`, checkpoint `5e392a3c`, pushed to `refactor/test-isolation-reviewed-01a16fc3`: 189 runtime/trace tests pass + 1 intentional skip; 7 E8 wrapper cases pass; all 3 new regressions fail safely on parent. Original hazard modules reviewed; unmerged. ✅ 2026-10-24
- [x] RESUME-3: finish and review C1-05 rollback error handling and behavioral regressions for nonzero exit, timeout, spawn error, wrong HEAD and successful rollback. Research `62c68ad99`, checkpoint `1b58b115c`, pushed to `refactor/autokernel-rollback-reviewed-01a16fc3`: 13 regressions pass (5 fail on WIP), targeted loop set 401 pass + 23 subtests. Reviewed, unmerged under launch/re-pin hold. ✅ 2026-10-24
- [ ] RESUME-4: review/integrate existing orchestrator branches in a private worktree and validate the combined tree, resolving gate/loop logic, source-pin and modified/deleted-test conflicts deliberately. P1, O4, O6, and three K2 finding fixes are accepted independently; the combined-tree gate remains outstanding.
- [x] RESUME-4a: independently review O3 and integrate the accepted isolation harness into its private branch. Orchestrator `d843eb9c` fixes concurrent registry-load backoff (12 attempts before, 1 after); `07829696` scopes alias stress to its actual guarantee; checkpoint `6558beb7` pushed to `refactor/config-reviewed-01a16fc3`. O3 selection 548 pass/4 skip, alias targets 524 pass, all 7 changed source pins verified. Reviewed, unmerged. ✅ 2026-10-24
- [x] RESUME-4b: independently review O1 stage 1 and fix pre-first-chunk streaming disconnect handling. Orchestrator `a1c69593`, checkpoint `142bb5df`, pushed to `refactor/request-reviewed-01a16fc3`: 1,011 targeted tests pass/3 skip; blocked initial generation fails to observe cancellation on parent and passes after fix. Accepted isolation is included; no changed route lies in ni63's pin closure. Reviewed, unmerged. ✅ 2026-10-24
- [x] RESUME-4c: independently review P2 decision semantics and snapshot migration. Orchestrator `4069b8ee`, checkpoint `db17808e`, pushed to `refactor/autopilot-gate-reviewed-01a16fc3`: 1,018 tests pass/1 skip; 18 snapshot controls pass; B2-02/B2-03 fail on parent. Pre-P2 snapshots refuse bounded authority; a current-format rebuild matches full replay. Review complete; integration held because existing reconstruction is CRITICAL and verified-snapshot replay HIGH. No evaluator-era files changed. ✅ 2026-10-24
- [ ] RESUME-5: repair CI infrastructure early; keep K4's post-prune size ratchet after K3. Reconcile baseline collection/failure identities rather than accepting aggregate counts.
- [ ] RESUME-6: reconcile current INF64 retained-module manifest and live belief-source contracts before each deletion stage; include retained `campaign.py` and dynamic/cross-repo consumers as closure roots.
- [ ] RESUME-7: fix the separate mixed-alias cold-import cycle. Randomized 16 aliases fail when imported concurrently at orchestrator baseline `84f6f6f1` and O3; same-alias 24-thread races and canonical identity tests pass. Original mixed test is at orchestrator `5886e5ae:tests/unit/test_inference_lock_concurrent_import.py`; existing O3 tests do not establish cross-module cold-import safety.
- [x] RESUME-8: repair NI07 capture's declared-output environment contract and replace expired cloud-only package prompts with validated host inputs, CPU claims, isolated baseline trees and explicit cheapest-capable model/effort. Root source `a976770b8`, closeout `8e66dd96b`, integrated here as `152a2991b`; node syntax/smoke and capture regression pass, capture regression fails on parent. ✅ 2026-10-24

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

### Done

- [x] Audit of all three codebases: 17 units, 382 findings, adversarially verified except C4-C6 ✅ 2026-10-07
- [x] Hermetic orchestrator test harness (`refactor/hermetic-tests`): 20,815 tests collect off the host ✅ 2026-10-07
- [x] Containment-scanner bypass fixes + degraded-mode regression fix (`refactor/containment-scanner`) ✅ 2026-10-24
- [x] Operator decisions on evaluator regime, AutoKernel prune, CI and scope recorded ✅ 2026-10-24
- [x] Bug report, findings, metrics and package definitions published (`refactor/refactoring-plan`) ✅ 2026-10-24

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
- [ ] Publish this review branch's RTG-60 registration and VB-REFACTOR-CONFORMANCE filing through the root owner boundary; no shared index file was edited during package work.

### Wave 1: bugs, hazards, ruled deletions

- [x] O1 (part): Inference request path: concurrency, event loop, failure semantics on `refactor/request-path` [A1-02, A2-01, A1-M2, A1-M1, A1-01, A4-M1, A2-04, A2-13, A1-17] ✅ 2026-10-24
- [ ] O1 (rest): [A2-02, A2-M1, A2-M2, A2-03, A2-05, A2-11, A2-16]
- [x] O3: Config / registry / runtime correctness and the stack-priors parse cost on `refactor/config-registry` [A3-01, A1-03, A3-19, A3-02, A3-07, A3-08, A3-09, A3-M1, A3-04, A3-06, A3-15, A3-05, A3-16, A4-08, A3-M2] ✅ 2026-10-24
- [x] O4: REPL / tools: permission bypasses and structured-mode defects [A4-01, A4-02, A4-03, A4-04, A4-14, A4-M3, A4-07, A4-06]; accepted on `refactor/repl-correctness-01a16fc3` at `acfd5f8c`: 557 tests pass; eight parent negative controls fail as expected; strict drift, ruff, compile, diff and frozen-snapshot checks pass. ✅ 2026-10-25
- [ ] O5: Dashboard request-path cost and silent-empty panels [A1-04, A1-08, A1-13, A1-11, A1-21]
- [x] O6 (part): Orchestrator scripts: live bugs and operator-ruled deletions on `refactor/scripts-cleanup` [A5-M1, A5-06, A5-07, A5-04, A5-12, A5-22, A5-M2, A5-01, A6-19, A5-05]; no test report for A5-01, A6-19, A5-05 ✅ 2026-10-24
- [x] O6 (rest): [A5-11, A5-23, A5-18, A5-02, A5-21]; accepted source `6efa56265b68f402af736a1c1a2ee3df447849c1` on `refactor/scripts-cleanup-reviewed-01a16fc3`; 190 launcher + 395 coverage tests pass, four 100% floors pass, five NI63 controls pass with 32/32 blob/SHA proof; exact approved four launcher-byte pins and remaining 28 unchanged. No integration/deployment authorization. ✅ 2026-10-25
- [x] O7 (part): Test-suite hazards and hygiene on `refactor/test-hazards` [A6-01, A6-02, A6-09]; no test report for A6-01, A6-02, A6-09 ✅ 2026-10-24
- [ ] O7 (rest): [A6-M1, A6-03, A6-12, A6-11, A6-17]; A6-13 belongs to O8 only.
- [x] P1 (part): Autopilot main loop: behavioural safety net, then loop bugs on `refactor/autopilot-loop` [B1-03, B5-02, B5-08, B1-15] ✅ 2026-10-24
- [x] P1 (rest): [B1-01, B1-M1, B1-M2, B1-04, B1-08, B1-09, B1-14, B1-13]; accepted source `36e1bc55` on `refactor/autopilot-loop-reviewed-01a16fc3`, hashes unchanged across the full candidate and 19 focused/561 broad tests pass (1 skip). Worker status-file failure was an ordering defect; see resume-state proof. ✅ 2026-10-25
- [x] P2: Autopilot safety gate and autopilot_core on `refactor/autopilot-gate` [B2-02, B2-03, B2-09, B2-11, B2-20, B2-17, B5-01, B5-M1, B5-M2, B5-16, B5-09, B5-13, B5-12] (B2-11 skipped: upstream already split SafetyGate.check; B2-17 no change, per the verifier) ✅ 2026-10-24
- [ ] P3: Autopilot actions, config applicator, controller IO, planner, journal [B3-01, B3-02, B3-03, B3-05, B1-17, B3-06, B3-07, B3-08, B3-12, B3-M1, B3-04, B3-23, B4-01, B3-15, B3-16, B3-M2]
- [ ] P4: Autopilot satellites: one-shot scripts, dead modules, small bugs [B4-03, B4-02, B4-19, B4-20, B4-13, B2-16, B4-16, B4-12, B4-06, B4-08, B4-09, B4-15, B4-M1, B4-M2, B4-04, B4-05]
- [ ] K1: AutoKernel live-loop bugs and red tests [C1-06, C1-14, C1-15, C1-M2, C1-24, C2-06, C5-08, C5-16, C6-05, C6-03, C6-04]; C1-05 tested/reviewed on `refactor/autokernel-rollback-reviewed-01a16fc3`, held unmerged (RESUME-3).
- [ ] K2: AutoKernel evaluator/execution integrity package remains open; C4-05, C4-06, C4-10 remain incomplete.
  - [x] K2 finding C4-08: resolved-path, fail-closed production-tree containment; source commit `208a053e29daf5bd11019e733f768b4173887021`. ✅ 2026-10-25
  - [x] K2 finding C4-16: exact Fraction ceiling independent of Decimal context; source commit `091abbbe7dc9b346bab888569434eb68445ae8e5`. ✅ 2026-10-25
  - [x] K2 finding C3-02: package import avoids shadowing stdlib `resource`; source commit `68724da5ba093cf3cec3909a81491932002dd4ce`. ✅ 2026-10-25

### Wave 2: decision-dependent and structural

- [ ] P5: Autopilot evaluator: ONE batched era event (operator decision 2026-10-24) [B5-03, B2-01, B2-M1, B2-M2, B2-10, B5-06, B5-07, B2-19, B2-04, B2-05, B2-06, B2-07, B2-08, B2-14, B2-15, B2-18, B2-12, B2-13, B5-14, B3-09]
- [ ] K3: AutoKernel prune of the three approved planes, after fresh closure and retained-contract checks [C2-01, C1-04, C2-03, C2-05, C2-08, C2-12, C2-M2, C2-13, C3-03, C3-01, C3-M1, C3-13, C3-14, C3-18, C5-03, C5-15, C6-07, C4-01, C4-02, C4-03, C4-11, C5-13, C5-12, C6-09, C5-06, C6-08, C2-09, C5-07, C2-M1]; C4-01's old deletion advice is superseded by INF64's retained manifest.
- [ ] K4: AutoKernel regrowth guard and CI repair (operator decision 2026-10-24) [C2-04, C5-02, C3-05, C1-02, C1-M3, C5-01, C6-01, C5-14, C6-13, C3-11, C2-02, C6-16]
- [ ] O8: Orchestrator CI, honest gates, and the ni63 pin design (operator decision 2026-10-24) [A6-04, B1-M3, B5-10, B5-17, A6-13]
- [ ] D1: Decompose the autopilot loop (_run_loop_inner) behind the P1 safety net [B1-02, B1-05, B1-12, B1-10, B1-06, B1-07, B1-11, B1-16, B1-18, B1-19]
- [ ] D2: API layer: openai_compat and /chat de-duplication [A1-05, A1-06, A1-15, A1-19, A1-20, A1-12, A1-10, A1-14, A1-16, A1-18, A1-09, A1-07]
- [x] D3 (part): Inference hot path: llama_server lanes, _execute_turn, escalation chain [A2-12] ✅ 2026-10-24
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
| O8 | orchestrator CI (PR + manual only; hermetic suite minus a reviewed host-only list with reasons), honest `make gates` (format-check only changed files; 1,471 files fail a whole-tree check), ni63 pin design (record hashes for provenance instead of asserting a past commit's bytes; the pin is already red on main for `orchestrator_stack.py`) | hermetic-tests merged |
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
