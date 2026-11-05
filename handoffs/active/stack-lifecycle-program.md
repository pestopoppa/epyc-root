# Stack Change Governance Pipeline

> **Fold destination** (BRF-T1-F4, BRF-T1-1, route 1a, 2026-11-02): renamed from `stack-change-governance-pipeline.md`; absorbs 7 handoff(s) as `## Track:` sections at the end of this file (`capability-registry-and-promotion.md`, `model-artifact-integrity.md`, `model-exec-containment.md`, `model-stack-single-source-update-pipeline.md`, `model-stack-update-pipeline-audit.md`, `standardized-stack-update-pipeline-finalization.md`, `wp12-fleet-layer-design.md`). The body above the first track is the former `stack-change-governance-pipeline.md`.

**Scratch**: `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/scg-logdir-private-recipe-20261007` · `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/scg-logdir-multipart-child-20261007` · `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/scg-logdir-multipart-original-run-37602092844-20261007` (KEEP original custody).

Accepted source is APP `b87998e3`, with durable [source and original acceptance](../../artifacts/ni08/scg-test-logdir-success-acceptance-20261007/README.md); the completed task no longer depends on its throwaway checkout.

**Status**: IN PROGRESS - canonical stack-change command, generated
stack-prior contract, guard/scanner ownership, runtime attestation, launch and
preflight gates, promotion-gate execution, and representative swap-CI witnesses
are live. Remaining work is high-risk consumer migration and waiver hygiene;
completed governance history through 2026-06-19 is compacted under
`Completed Scope`.
**Created**: 2026-06-13
**Updated**: 2026-07-26
**Priority**: HIGH — prevents silent stale model constants after stack changes; no inference required for W1-W4
**Related**: [standardized-stack-update-pipeline-finalization.md](stack-lifecycle-program.md#track-standardized-stack-update-pipeline-finalization), [model-capability-descriptors.md](routing-program.md#track-model-capability-descriptors), [routing-truth-restoration.md](../completed/routing-truth-restoration.md), [dynamic-stack-concurrency.md](numa-placement-and-contention.md#track-dynamic-stack-concurrency), [bulk-inference-campaign.md](eval-tower-program.md#track-bulk-inference-campaign), [MEASUREMENT.md](../../MEASUREMENT.md)

> **2026-06-13 finalization bridge**: [standardized-stack-update-pipeline-finalization.md](stack-lifecycle-program.md#track-standardized-stack-update-pipeline-finalization) consolidates the older audits into the main workflow pickup plan. Use that file for the next implementation pass; continue recording commit-level progress and guard counts here.

## NI18 source-correlated fixture route — 2026-10-05

- [ ] **SCG-NI18-FIXTURES** — Review the six stack-change/:8083 modules against exact registry/prior/backend/receipt inputs and owner-approved disposable fixture boundaries. Keep synthetic fixtures distinct from operator/runtime evidence; no peer source edits, API traffic, reload or operator receipt is authorized by classification. Modules: `test_stack_change_guard.py`, `test_stack_change_pipeline.py`, `test_stack_change_pipeline_simulated_fixtures.py`, `test_stackchg_8083_batch.py`, `test_stackchg_8083_idle_slots.py`, `test_sync_procedure_role_enums.py`. Done when each of the six modules either asserts against the generated registry/prior artifact or carries a docstring naming its fixtures synthetic, and none reads an operator receipt.

## 2026-07-26 Staleness Review

W4 remains active in the [routing and optimization
index](routing-and-optimization-index.md) and
[design-backlog triage](../completed/design-backlog-triage-2026-07-23.md). The v8
registration repair (`epyc-orchestrator` `e923a40b`) is current evidence that
generated priors and consumer probes must stay aligned; it does not complete
the remaining high-risk consumer migration or waiver-hygiene work.

## Why

The orchestration stack has outgrown manual update discipline. A single model or
serving-topology change now has to update registry records, descriptors,
launch args, q_scorer priors, planner signatures, seeder eval config, process
layout, tests, docs, and runtime attestation. The 2026-06-13 q_scorer fix found
severe drift: `architect_coding` was retired but still present in fallback
priors, `architect_general` and `ingest_long_context` were marked HOT in
`server_mode` while older role/process-layout metadata still implied WARM, and
`coder_escalation` shares the frontdoor model/server but old cost comments
treated it as separate memory pressure.

The target state is a fail-closed stack-change pipeline: edit model/serving
truth once, compile generated descriptors/derived priors, validate every
consumer, and refuse launch or CI if any model-specific quantity remains stale.

## Current Baseline

- Canonical check: `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` in `epyc-orchestrator`.
- Generated descriptors and stack priors are compiled with empty stack-prior
  `known_gaps` for live roles.
- Guard ownership is machine-readable through
  `orchestration/stack_change_surface_manifest.yaml`; hardcoded-surface rule
  inventory and compact summary output are available for operator review.
- Runtime attestation checks model/mmproj paths, known-stack listeners, state
  gaps, concrete launch flags, context/KV/spec flags, binary path, and related
  llama-server runtime evidence.
- Promotion-gate execution includes the simulated stack-change fixtures and
  launch-parity witnesses; swap-CI has representative q_scorer/operator
  summary/system-card/health/dashboard/routing/API/long-context/vision coverage.
- Completed details are in the dated ledgers listed below and in daily
  `progress/` logs, not in this active handoff.

## Completed Scope

| Through | Historical ledger |
|---------|-------------------|
| 2026-06-15 | [standardized-stack-update-pipeline-finalization-history-2026-06-15.md](../archived/standardized-stack-update-pipeline-finalization-history-2026-06-15.md) and related active-handoff histories |
| 2026-06-19 | [stack-change-governance-pipeline-history-through-2026-06-19.md](../archived/stack-change-governance-pipeline-history-through-2026-06-19.md) |

## Waypoints

- [x] **W1 - Stack truth precedence spec**: live serving facts have documented precedence, shared-runtime alias handling, retired-role handling, and generated-consumer source evidence.
- [x] **W2 - Derived stack-priors generator**: descriptors compile the machine-readable stack-prior artifact consumed by validators and migrated consumers.
- [x] **W3 - Stack drift validator foundation**: freshness, structural contract, scanner ownership, exception metadata, runtime witness, surface summary, and promotion-gate reporting are live. Strict/future hardening continues through owned consumer surfaces rather than a new guard system.
- [ ] **W4 - Consumer migration: make the remaining set queryable first.** The manifest `stack_change_surface_manifest.yaml` records no migration state, so "remaining consumers" cannot be listed. Add a `migration_state` field (`migrated` / `degraded_fallback` / `pending`) to each of the 13 `consumer_surfaces` entries, populate it from the code (implementation_refs), and add a check that fails on an entry without it. Then migrate only `pending` entries that restate a live model/role/serving fact. Done when the field exists on all 13 entries and the pending list is printed by one command.
  **2026-08-11 (`mainB`) — sized, and the reason it has stayed open is structural: THE MANIFEST
  RECORDS NO MIGRATION STATE.** `consumer_surfaces` carries 13 entries whose fields are
  `classification / consumer_scope / source_of_truth / promotion_blocker / review_cadence /
  drift_response / implementation_refs / owner / validation_command` — and **no** migration or
  status field. So "remaining consumers" is not a queryable set; every session that picks this row
  up must re-derive it from scratch, which is why it never closes.
  A mechanical screen over `implementation_refs` (does the file read generated priors / does it
  contain port literals) gives **5 clean, 8 mixed, 0 with no priors read at all**. **That is a
  SCREEN, not a verdict, and must not be quoted as "8 remaining"**: W4's own wording permits
  *"or explicit degraded fallbacks"*, and a regex cannot distinguish a **declared** fallback
  (compliant) from a **hardcoded copy** (not). Reporting the screen as a count would be the same
  category error as comparing a joint verdict to a single-axis threshold — see SEQ-A.
  **The unblocking step is therefore not migration work, it is a `migration_status` field on each
  `consumer_surfaces` entry** (`migrated` | `explicit_fallback` | `unmigrated`, with the evidence
  ref), so the set becomes queryable and the promotion gate can assert on it. That is a schema
  change to a governance artifact owned by `stack-change-governance`, so it is **proposed, not
  applied** — not something to land unattended overnight against a file with a promotion-blocker
  contract.
  Screen output for whoever takes it: clean = `routing_prior_consumers`, `admission_policy`,
  `lock_tap_policy`, `procedure_role_enums`, `generated_stack_docs`; needs a human read =
  `q_scorer_priors`, `seeding_reward_priors`, `config_model_catalog`, `health_preflight_probes`,
  `launch_maps`, `dashboard_status_system_cards`, `planner_prompt_guidance`, `runtime_attestation`.
- [x] **W5 - Simulated model-swap CI gate**: representative data-only stack swaps execute in the promotion gate and cover generated artifacts plus selected consumers.
- [x] **W6 - Stack-change runbook and launch hook**: production launch, AutoPilot preflight, and benchmark preflight use the canonical gate; bypasses are explicit diagnostics only.
- [x] **SCG-DRYRUN — `orchestrator_stack.py start --dry-run` without `--migrate-to` launched the production stack.** ✅ 2026-10-03
  (orch `99e3e5fe`). Only the `--migrate-to` path reads `--dry-run`. On its own, argparse accepted it and `main()`
  dispatched to `cmd_start`. On 2026-10-03 workspace-ec ran it on a freshly rebooted host and the whole stack came up.
  That was benign, because a start was intended next anyway. It now returns 2 with a pointer to `--validate-only`. The
  tests drive `main()` with `cmd_start` booby-trapped, plus a negative control
  (`tests/unit/test_orchestrator_stack_validate_only.py`). Same class as the 2026-08-12 inert `--validate-only`
  (orch `2c421c1c`). Incident: `INC-20261003-start-dry-run-launched-stack`.
- [x] **SCG-TEST-LOGDIR — tests must never write to the live `/workspace/logs/progress/`.** (filed 2026-10-03, ✅ 2026-10-07 — [MAIN source/original4/4 acceptance](../../artifacts/ni08/scg-test-logdir-success-acceptance-20261007/README.md), APPb87998e3; actual root bootstrap/real during-test logger, constructor override/default/sentinel/teardown and authenticated temporary JSONL copies. Original NULL/setup evidence unchanged; no shared-host tests/logs or runtime warrant.
  workspace-ec) An API test falls back to that directory when run from a worktree with no `logs/`; on 2026-10-03 it
  wrote 2 synthetic `contention_denied` rows into the live 2026-10-03 progress file (deleted with operator OK).
  Point the fallback at a tmp dir under pytest (conftest fixture) and add a test that the live dir is untouched.
- [ ] **SCG-PRIORS-WARM — `stack_priors` must not classify WARM-tier roles as `live_stack`.** (filed 2026-10-03,
  workspace-ec, found fixing 19 stale test fixtures on orch `fix/main-test-failures-ec` d97004f6 / 9d40c30b) After
  STACKCHG-DFLASH2 moved `worker_vision` (:8086) to cold CPU, WARM tier, the compiled `stack_priors` still lists the
  vision roles as `live_stack`, so seeding's DEFAULT_ROLES include :8086, which a default `start` no longer launches.
  Fix the compiler classification (launch tier HOT only, or an explicit `warm` class), recompile, and add a test that
  a WARM role never lands in DEFAULT_ROLES. Derived output changes, so it ships as a stack-change package.
  - *(Annotation, workspace-ec, 2026-10-04.)* **PACKAGED, VALID, awaiting the operator's signature** in
    STACKCHG-HYGIENE-20261003 (`/mnt/raid0/llm/tmp/stack-change-hygiene-20261003/PACKAGE.md` §1b; `--validate-only`
    VALID, 68 pins). Scoped to seeding: the compiler stamps `serving.default_launch`; `DEFAULT_ROLES` and
    `discover_active_roles` drop `worker_vision` / `vision_escalation` (:8086). `live_stack` is KEPT, because ~40
    declared consumers need it (`live_stack_role_records` is CRITICAL in impact analysis); two helpers sit beside it.
    7 new tests plus a negative control. Argv identity 11/11, no relaunch. Not ticked until signed and applied.
  - 2026-11-01: an isolated source proposal rebased on Orchestrator `2e45e6a` preserves `live_stack` and adds default-launch filtering; four focused tests passed. It is unmerged and the derived stack change remains unsigned. [Proposal](../../artifacts/coordination/ni-post-a2-wrap-20261101/RTG36-PROPOSED.md). [no-belief: source proposal only]
- [ ] **SCG-PRIORS-WARM-b — switch the default-start readers to `live_stack_default_launch_role_records()`.** (filed
  2026-10-04, workspace-ec, from STACKCHG-HYGIENE PACKAGE §8 A-3; after SCG-PRIORS-WARM is applied) The RESIDENT
  consumers that mean "expected up after a default start" still read `live_stack`: `/health` core probes (a missing
  :8086 reports `not_realized` → `degraded`), `cli_orch` status, `stack_commands status`, `autopilot/preflight_audit`,
  the `host_health` rewarm list, `corpus_quality_gate`, `kv_compress` compress-all and autopilot `/slots` polling.
  Needs an API + autopilot reload. Done when `/health` is not `degraded` with :8086 down by design, with tests.
- [ ] **SCG-TEST-ORDER — fix the order-dependent `test_safety_gate_baseline_eligibility` failure.** [too-big: source fixes landed; both-order and full-unit acceptance remain with handoff owner] (filed 2026-10-03,
  workspace-ec) `test_reproduced_promotion_uses_representative_median…` fails or passes depending on test order, on
  origin/main as well as the integration branch. Find the leaked state (module global, env, or monkeypatch order),
  isolate it in a fixture, and prove it with `pytest -p no:randomly` in both orders plus the full `tests/unit` run.
  - 2026-10-03: the full `tests/unit` run on `integ/api-reload-2-ec` passed it, 15979 passed / 0 failed
    (`/mnt/raid0/llm/tmp/integ2-ec/full_unit3.log`). That is one order, not a fix: the leaked state is unfound, so
    the task stays open.
  - 2026-10-31 partial source repair: APP `2f5c05013ccc80d549635878f260bddf0c172452` isolates the incoming promotion provider and warning state with private `MonkeyPatch.context()`. Original predecessor pair failed 2.95 != 2.8; both orders, root-conftest pairs and both modules (71 PASS) now pass; provider identity/warnings and gates preserved. Full unit acceptance remains open: 19,818 collected; early stop at 374 PASS / 8 skipped / 1 AP54 missing-headers failure. C3 subsequently repaired that fixture at `1fc5eb1ac21aa400bdc6425a06e4cf8dbc0d6806` with 12 controls; broader full suite has not been rerun or established green. Evidence: `artifacts/ni/source-acceptance-20261031/README.md`. No new checkbox/quota or deployment claim. [no-belief: source correctness controls; full-suite acceptance incomplete]
- [x] **SCG-STALE-FIXTURES — fix the 19 orch `tests/unit` failures on main.** ✅ 2026-10-03 (workspace-ec) All 19 were
  stale fixtures from STACKCHG-DFLASH2 5265e09d, not production defects: orch `fix/main-test-failures-ec` d97004f6
  (enrollment compiles a master view of the lean, DRAFT-SEL-1) and 9d40c30b (vision expectations: VL-30B on cold CPU,
  WARM tier). Merged through `integ/api-reload-2-ec` (10bc5681) to orch main. Full `tests/unit`: 15979 passed,
  0 failed, 57 skipped. Residual found while fixing them: SCG-PRIORS-WARM above.
- [x] **SCG-LEASE-FIXTURE — the KVU-15a autouse lease fixture reordered monkeypatch teardown.** ✅ 2026-10-03
  (orch ac33e623) `_hermetic_long_prefill_lease` requested the function-scoped `monkeypatch`, so it tore down after
  `_reset_config_between_tests`, and a patched `get_config` lambda was still in place at `cache_clear()`. That caused
  9 teardown errors (`test_safe_pickle` ×2, `test_typed_decisions_tool_args_integration` ×7). The fixture now uses a
  private `MonkeyPatch.context()`.
- [x] **SCG-ENVOVR-EXPIRED — an expired embedder override of an UNDECLARED key is silent in env attestation.** ✅ 2026-10-07 — [MAIN original97/97 acceptance](../../artifacts/ni08/registry-banner-override-source-20261007/README.md).
  (filed 2026-10-03, workspace-ec, found building the diagnostic override, orch aa1d6894) In
  `scripts/server/env_attestation.py` (~:200-207) the loop over keys the embedder record overrides but the stack does
  not declare (e.g. `KMP_LIBRARY`) appends EXPECTED when the record covers the live value and does nothing otherwise.
  So an expired record, or one naming another pid, leaves a live undeclared key unreported. The same case on the new
  diagnostic path is an ERROR (`:208-224`). Add the missing branch: an ERROR with the EXPIRED/restore hint, matching
  the diagnostic path. Test it with an expired record plus a live `KMP_LIBRARY`. Done when attestation reports that
  case as an error and the existing embedder tests stay green.
- [x] **SCG-GITNEXUS-ORCH — re-index the stale orchestrator GitNexus index.** (filed 2026-10-03, workspace-ec) A ✅ 2026-10-29 (audit: /mnt/raid0/llm/epyc-orchestrator/.gitnexus/meta.json indexedAt 2026-10-24T21:20Z lastCommit 84f6f6f15, 25 commits behind origin/main (was ~844 behind 2026-10-03)) [no-belief: audit-reconciliation]
  subagent saw it ~844 commits behind, which makes every `gitnexus impact` blast radius on orch code untrustworthy.
  Run `scripts/gitnexus-analyze.sh` (never bare `gitnexus analyze`) for epyc-orchestrator in a CPU-quiet window (it
  must not overlap an AutoKernel CPU measurement window); exit 75 means another analyze holds the lock, retry later.
- [ ] **SCG-INERT-FLAGS — sweep `orchestrator_stack.py` for other parsed-but-unread flags.** (filed 2026-10-03, from
  SCG-DRYRUN) The same defect has now shipped twice (`--validate-only` 2026-08-12, `--dry-run` 2026-10-03), and each
  was found by accident. Each fix covered only its own flag. Add one structural test: for every subcommand, every
  parsed option is either read on the path `main()` dispatches to or rejected with a non-zero exit. Drive `main()`
  with the launch functions booby-trapped, as `99e3e5fe` does. Fix whatever it finds.
- [x] **STACKCHG-DFLASH2-20261003 — :8083 on DFlash2, Qwen3-VL-30B to cold CPU.** ✅ 2026-10-03 — signed at the
  terminal 2026-10-03T04:39:55Z; research `be2cc414`, orch `d3233170` (source) + `5265e09d` (derived), root
  `ceae5967` (receipt, package archive, change-topology `device: none` is CPU). Bring-up: `reload architect_critic`
  → :8083 PID 3793153, stack-launched with the DFlash2 argv; `reload orchestrator` → API PID 3794270 with
  `ORCHESTRATOR_VISION_VL_BACKEND=server`; `check --run-promotion-gate`: runtime_attestation, serving_shape_capacity
  and promotion_gate ok. Package: [`artifacts/operator/stack-change-dflash2-20261003/PACKAGE.md`](../../artifacts/operator/stack-change-dflash2-20261003/PACKAGE.md).
  Root cause: `INC-20261003-dflash2-ruling-never-compiled`.
- [x] **DRAFT-SEL-1 — drafter selection is a compile input, not a hand-carried field.** ✅ 2026-10-03 (orch
  `d3233170`, research `be2cc414`). The master lists every acceptable drafter per model
  (`roles.<model_role>.drafters`); `stack_topology.yaml` `drafter_selection:` picks one per launching server;
  `src/registry/drafter_selection.py` projects it into host, role and alias rows with a provenance stamp. Compile
  FAILS on an unlisted or alias-keyed selection, on a hand-carried drafter field, and on a model with >1 drafter
  and no selection (deliberately no default — a default is how :8083 re-inherited MTP); the lean validator at
  every `start` fails a stale or hand-edited projection. `stack_priors` now enables spec for `draft-dflash` /
  `draft-simple` / `draft-eagle3` (it used to enable only `draft-mtp`, so a hand edit launched with no
  speculation), the launcher emits `-ngld`, and runtime attestation checks it. The global
  `production_recipe: draft-mtp` became `default_spec_type`, scoped to n-gram composition (operator-signed A-1).
- [x] **SCG-CAPACITY-FRESH — `update` was green over a lean that fails the import-time VRAM gate.** ✅ 2026-10-03
  (orch `d3233170`). The pipeline imported `stack_manifest` before rewriting the lean, so the import-time capacity
  gate ran against the OLD lean. Measured during packaging: with the VL still on the card, `update` was all-green
  while a fresh import raised `ROCm0 OVERSUBSCRIBED by 3.16 GiB`. New step `serving_shape_capacity` re-runs the gate
  in a fresh interpreter on the lean the run just wrote (tests: capacity step ×3).
- [x] **SCG-LEAN-BOOTSTRAP — a tier flip could never compile.** ✅ 2026-10-03 (orch `d3233170`). `stack_manifest`
  validates launcher↔lean parity at import, so a field both sides declare (here the vision `tier`) could not be
  flipped: the lean that fixes the parity cannot compile, because compiling needs the import. During `update`
  only, the lean step now derives the active set from `launch_manifest.yaml` + master `shared_with` (mirroring
  `_build_role_launch_meta`; a test pins equality with `ROLE_LAUNCH_META`), compiles, and re-imports. `check`
  never takes this path. It also covers the reverse flip on rollback.
- [ ] **DRAFT-SEL-2 — audit the roles that still carry legacy drafter fields** (filed 2026-10-03, from the
  drafter-compile handback `/mnt/raid0/llm/tmp/drafter-compile-20261001/REPORT_handback.txt` and DESIGN §7).
  DRAFT-SEL-1 migrated only Qwen3.8-27B; every other row compiles with a `LEGACY drafter` warning. Close each:
  - **Qwen3.6-27B (rollback anchor, not served):** its DFlash drafter lives in a third shape, its own role row
    `dflash_qwen36_27b_f16_local` (below floor at the v9 freeze). A rollback would re-open the same drift. Migrate
    it to `drafters:` with no DFlash selection until its gate passes.
  - **`architect_general` (:8074, Flash-Next):** topology `spec_overrides: {draft_max: 4}` is a second argv writer
    after compile, and its comment still describes the pre-ARCHSWAP critic. Fold it into `drafters.mtp.draft_max`
    and retire `spec_overrides` (or add the rule: `spec_overrides.draft_max` must equal the selected recipe).
  - **frontdoor + worker/toolrunner aliases (35B-A3B MTP):** no DFlash drafter exists, so no functional drift;
    migrate to a one-entry `drafters:` list so the LEGACY path can be deleted.
  - **Top-level `dflash_drafters:`** (Qwen3-8B, Qwen3-Coder-30B-A3B): a fourth drafter shape; fold onto target
    rows if ever rostered, else delete.
  - **MTP baseline mismatch:** the untracked research recipe `qwen3.8-27b-q8-gpu-mtp.json` measures MTP with the
    SIDECAR `mtp-Qwen3.8-27B-Q8_0.gguf`, while production MTP self-drafts from the model file — so AK's MTP
    denominator is not the production argv. List the sidecar as `drafters.mtp_sidecar` or fix the recipe.
  Done when no served or rollback-anchor model compiles with a `LEGACY drafter` warning.
  - *(Annotation, workspace-ec, 2026-10-04.)* **PACKAGED, VALID, awaiting the operator's signature** in
    STACKCHG-HYGIENE-20261003 (`/mnt/raid0/llm/tmp/stack-change-hygiene-20261003/PACKAGE.md`; `--validate-only`
    VALID, 68 pins): frontdoor + aliases (35B-A3B MTP) and `architect_general` (Flash-Next MTP) move to DRAFT-SEL-1
    `roles.<model>.drafters` form; the :8074 `spec_overrides` is retired; the Qwen3.6-27B rollback anchor gets
    `drafters` (MTP only, DFlash stays gated). `LEGACY drafter` warnings 2 → 0; argv identity 11/11 live servers, so
    no relaunch. Not ticked until signed and applied. The residuals the package leaves (A-5) are DRAFT-SEL-2b.
- [ ] **DRAFT-SEL-2b — the drafter residuals STACKCHG-HYGIENE left (PACKAGE §8 A-5).** (filed 2026-10-04,
  workspace-ec) None produces a `LEGACY drafter` warning today, so DRAFT-SEL-2's done-when does not cover them:
  the top-level `dflash_drafters:` (Qwen3-8B, Qwen3-Coder-30B-A3B; fold onto target rows if rostered, else delete);
  the untracked `qwen3.8-27b-q8-gpu-mtp.json` sidecar-MTP recipe mismatch (list `drafters.mtp_sidecar` or fix the
  recipe); the alias `server_mode.worker.draft_model` that no check reads; and the gemma rows the package names.
  Ships as one stack-change package. Done when each is folded, deleted or explicitly declined in that package.
- [ ] **SCG-FASTPATH — the stack-change skill offers the fast path first for an urgent production fix**
  (filed 2026-10-03, from `INC-20261003-urgent-fix-slowed-by-bundling`). When live serving is wrong and the
  operator wants it fixed now, phase 0 presents (a) an operator-terminal relaunch with the target argv, then (b)
  the permanent package behind it — instead of only (b). It also refuses to bundle an unrelated lineup move into
  an urgent package without the operator choosing that. Edit `.claude/skills/stack-change/SKILL.md` phase 0. Same edit absorbs SCG-RULING-TO-FIELD: the skill's intake treats any operator ruling that names a launch recipe ("use X for model Y") as a stack-change intent that lands as a registry field plus a compile check; the handoff carries only a pointer.
- **[declined: ws58 2026-11-03 content-review: merged into SCG-FASTPATH (one edit of the same skill file)]** **SCG-RULING-TO-FIELD — an operator recipe ruling must land as a registry field plus a compile check, or a
  task that does so** (filed 2026-10-03, same incident). Add to the stack-change skill's intake: any operator
  ruling that names a launch recipe ("use X for model Y") is a stack-change intent, not handoff prose; the
  handoff carries only a pointer to the package or to an open `- [ ]` task.
- [ ] **SCG-SPEECH-OMP-PASSIVE — give the speech servers a passive OMP wait policy.** (filed 2026-10-03,
  workspace-ec) After the 15:35Z speech restore, tts-server burned **32 CPU-minutes in 21 minutes** while idle:
  its OpenMP team busy-waits between requests. That spin lands on cores 24-39, inside the frontdoor's `-t 96` set.
  - Cause to confirm first: the whisper and tts entries in `orchestration/launch_manifest.yaml` declare no
    `OMP_WAIT_POLICY` / `KMP_BLOCKTIME`, and `stack_env.build_service_env` starts from the parent env. So the policy
    is either the OpenMP runtime default or an ambient `active` inherited from the launcher. Read
    `/proc/<pid>/environ` of the next speech launch to tell which.
  - Fix: declare `OMP_WAIT_POLICY: passive` (plus `KMP_BLOCKTIME: "0"` if the binary links LLVM libomp) in both
    service `env` blocks. The embedder precedent is `repl-embedding-retrieval.md` A3. This is a launch-env change on
    the stack surface, so it goes through the stack-change pipeline with operator signature. Pair it with one TTS RTF
    and one STT RTF check, so the passive wake-up latency does not cost real-time.
  - Done when an idle speech server shows < 1 CPU-minute per 10 minutes (sampled during the idle period, not after)
    and the TTS/STT RTFs stay within their recorded real-time figures.
  - Speech is DOWN from ~16:4xZ 2026-10-03 on operator instruction. The package can be prepared now; its live
    proof waits for the next speech start, which the operator asks for.

- [ ] **REG-KVFA-COMMENT — apply the registry KV-FA warning comment.** Apply registry KV-FA warning comment (`/mnt/raid0/llm/tmp/registry-kv-fa-comment-20261105.patch`, epyc-orchestrator `orchestration/model_registry.yaml`) after next full-stack bring-up regenerates contention matrix; commit must pass pre-commit (no --no-verify). [no-belief: pending-stack]

## Dependency Graph

- W1 blocks W2/W3 because consumers need a declared precedence model.
- W2 blocks W4/W5 because consumers need one artifact/API to consume.
- W3 can proceed after W1 and should run before each W4 migration.
- W4 and W5 are parallel after W2/W3.
- W6 depended on W2-W5 because launch hooks needed to enforce the generated
  contract. The production launch hook and runbook are now live; future
  consumer migrations should extend the same promotion gate instead of adding
  separate launch checks.

## Cross-Cutting Concerns

- **Model descriptors**: this handoff is the governance shell around
  `model-capability-descriptors.md` W3/W4. Descriptor compilation stays the
  model-agnostic interface; this handoff ensures downstream consumers cannot
  bypass it with stale constants.
- **Routing and q_scorer**: q_scorer must not keep role/model/memory defaults
  as hidden policy. Its fallbacks are degraded-mode only and must be tested as
  such.
- **Launch truth**: `orchestrator_stack.py`, `server_mode`, and runtime
  attestation must agree. If launch args are special-cased by role name
  (`_NO_SPEC_DECODE`, ik binary paths, MTP knobs), the generated artifact must
  either own that mapping or mark it unresolved.
- **Benchmark provenance**: MEASUREMENT.md claim grammar still applies. Derived
  TPS/quality values must carry source evidence, date, protocol, and stale/gap
  markers.
- **Docs and tests**: stale docs/tests can reintroduce bad constants. The drift
  validator should scan docs/tests for retired live-role claims separately from
  production-code blockers.

## Key File Locations

- `epyc-orchestrator/orchestration/model_registry.yaml`
- `epyc-orchestrator/orchestration/model_descriptors.yaml`
- `epyc-orchestrator/scripts/registry/compile_descriptors.py`
- `epyc-orchestrator/scripts/registry/compile_stack_priors.py`
- `epyc-orchestrator/scripts/registry/sync_procedure_role_enums.py`
- `epyc-orchestrator/src/registry/model_descriptors.py`
- `epyc-orchestrator/src/registry/stack_priors.py`
- `epyc-orchestrator/docs/reference/stack-truth-precedence.md`
- `epyc-orchestrator/orchestration/derived/stack_priors.yaml`
- `epyc-orchestrator/orchestration/procedure.schema.json`
- `epyc-orchestrator/orchestration/procedures/add_model_to_registry.yaml`
- `epyc-orchestrator/scripts/validate/stack_change_guard.py`
- `epyc-orchestrator/src/api/admission.py`
- `epyc-orchestrator/src/scheduling/contention.py`
- `epyc-orchestrator/src/runtime/inference_lock.py`
- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py`
- `epyc-orchestrator/scripts/benchmark/seeding_types.py`
- `epyc-orchestrator/scripts/benchmark/seeding_rewards.py`
- `epyc-orchestrator/orchestration/repl_memory/bilinear_scorer.py`
- `epyc-orchestrator/scripts/autopilot/state_store.py`
- `epyc-orchestrator/scripts/server/orchestrator_stack.py`
- `epyc-orchestrator/scripts/server/stack_commands.py`
- `epyc-orchestrator/scripts/server/stack_processes.py`
- `epyc-orchestrator/orchestration/model_quality_signatures.yaml`
- `epyc-orchestrator/tests/unit/test_scheduling_contention.py`
- `epyc-orchestrator/tests/unit/test_scheduling_contention_gate.py`
- `epyc-orchestrator/tests/unit/test_admit_set.py`
- `epyc-orchestrator/tests/unit/test_q_scorer.py`
- `epyc-orchestrator/tests/unit/test_inference_lock.py`
- `epyc-orchestrator/tests/unit/test_model_descriptor_compiler.py`
- `epyc-orchestrator/tests/unit/test_model_descriptors_schema.py`

## Proposed Validation Commands

Run after any stack/model change and before an AutoPilot restart:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python3 -m py_compile src/registry/stack_priors.py scripts/registry/compile_stack_priors.py scripts/registry/sync_procedure_role_enums.py scripts/validate/stack_change_guard.py orchestration/repl_memory/q_scorer.py scripts/registry/compile_descriptors.py src/registry/model_descriptors.py
uv run python scripts/registry/compile_descriptors.py --dry-run --allow-incomplete
uv run python scripts/registry/compile_stack_priors.py --allow-incomplete
python3 scripts/registry/sync_procedure_role_enums.py --check
uv run python scripts/validate/stack_change_guard.py
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run --with pytest pytest -q tests/unit/test_stack_priors_compiler.py tests/unit/test_stack_change_guard.py tests/unit/test_sync_procedure_role_enums.py tests/unit/test_model_descriptors_schema.py tests/unit/test_model_descriptor_compiler.py tests/unit/test_q_scorer.py
uv run --with ruff ruff check src/registry/stack_priors.py scripts/registry/compile_stack_priors.py scripts/registry/sync_procedure_role_enums.py scripts/validate/stack_change_guard.py orchestration/repl_memory/q_scorer.py scripts/registry/compile_descriptors.py src/registry/model_descriptors.py
git diff --check
```

Future W3/W6 should replace this with a single strict command after descriptor
gaps close, e.g. `uv run python scripts/validate/stack_change_guard.py --strict`.

## Acceptance Criteria

- A stack/model change can update role -> model/serving facts in one source and
  regenerate all model-specific consumer quantities without hand-editing
  q_scorer, planner signatures, seeder config, bilinear features, or launch args.
- Retired roles such as `architect_coding` cannot remain in live priors,
  generated signatures, launch manifests, or active routing chains unless
  explicitly marked legacy/test-only.
- Shared-mmap roles such as `frontdoor` and `coder_escalation` carry one model
  identity and do not double-count memory cost.
- HOT roles such as `architect_general` and `ingest_long_context` do not receive
  WARM memory penalties because older role/process-layout fields lagged.
- CI or launch fails closed on stale generated artifacts, missing descriptor
  evidence, or contradictory live serving facts.

## Reporting

After each waypoint:

- Update this handoff with commit hashes, validator output, and any unresolved
  source-of-truth contradictions.
- Update `model-capability-descriptors.md` only when W3/W4 consumer ownership
  changes; GitNexus currently marks it HIGH blast radius.
- Update `routing-and-optimization-index.md` and `master-handoff-index.md` only
  in a deliberate doc-sync pass; GitNexus currently marks them CRITICAL/HIGH.
- Add a progress entry with exact commands and whether AutoPilot was paused or
  running.


2026-10-07 MAIN source boundary: reviewed APP0a40117c missing undeclared-override branch reports expired/wrong-PID deviations with restore hints, preserving the original diagnostic coverage path. VB-SW-SCG-SOURCE-CONFORMANCE prospectively binds full compiler/environment/diagnostic/embedder modules before hosted capture. SCG-ENVOVR-EXPIRED remains unchecked pending source integration and original compatibility proof; no live /proc read or reload occurred.


2026-10-07 MAIN acceptance: [normally published source and original97/97](../../artifacts/ni08/registry-banner-override-source-20261007/README.md) close SW-6, SCG-ENVOVR-EXPIRED and the prospective verifier. SW-5 keeps its wider active editing-reference documentation sweep open. Full source/result custody verified; original capacity collection NULL retained; no shared-host test, runtime reload or measurement warrant.

## Track: capability-registry-and-promotion
<!-- gate: none -->

> Folded from `handoffs/active/capability-registry-and-promotion.md` @ `05e2b812a086` on 2026-11-02 (BRF-T1-F4, route 1a, operator D1/D5; retired row RTG-06 → RTG-36). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Capability Registry, Safe Role-Restart Applicator & Promotion Workflow

**Status**: IN PROGRESS — revalidated 2026-08-05. W0 traffic-class interface, TaskIR/task-record capture, and live `request_context` workload-class tagging are closed; W1 seed rows landed; W2 generated Action-Availability + index A-by surfaces landed/adopted 2026-06-27; W3 implementation primitives remain present, but its live shadow-restart attestation is still absent; W4 has not run and every registry row remains `promotion_state: placeholder`.
**Created**: 2026-06-12
**Priority**: READY FOR W3 ATTESTATION — the implementation prerequisites survived the 2026-08-05 code audit, but promotion remains fail-closed until a shadowed live restart supplies the required attestation. W4 remains downstream of that evidence; this audit does not promote any row.
**Spec**: [fable5-findings-04-impl-plan.md](../completed/fable5-findings-04-impl-plan.md) §C + §D — read before claiming any waypoint
**Related**: [fable5-findings-04-northstar-portfolio-indices.md](../completed/fable5-findings-04-northstar-portfolio-indices.md) (why backlog→actionable must be a state transition); [multi-file-coding-completion-capability.md](benchmark-suites.md#track-multi-file-coding-completion-capability) (edit-transaction = first-cohort member); [moe-spec-cpu-spec-dec-integration.md](kernel-champion-and-promotion.md#track-moe-spec-cpu-spec-dec-integration) (`moe_spec_budget` evidence source)

#### Why

Every measured speed lever that needs a restart is currently operator-only,
and the planner's action surface is a hand-maintained denylist in program.md
that nobody promotes against. The spec turns "what can the autopilot touch"
into data: one YAML row per lever (kind/surface/applicator/range/evidence/
risk/actionable_by), one missing applicator (safe role restart), and one
standing monthly promotion pass. §D's workload model is the smallest
interface with the biggest definitional payoff and rides along as W0.

#### Waypoints

- [x] **W0 — workload model** (1 day, ungated): `orchestration/workload_model.yaml` per spec §D — traffic classes `{interactive, eval_batch, campaign}` with per-class volume share (seed from the 2026-06-11 tally), latency/throughput SLO, serving class, contention priority; extend `request_context` tagging to workload class. Acceptance: routing/placement/autopilot consumers named in §D can read it; eval traffic self-labels `eval_batch`. **Interface branch-ready 2026-06-13**: `feat/workload-traffic-classes` commit `b62946d` extends the F1 workload model with `traffic_classes:` and `traffic_class_tagging:`, adds read-only `src/workload_model.py` loader/inference helpers, and validates the three required traffic classes. **Capture lane landed 2026-06-19**: orchestrator `02370da` adds `capture_workload_class()`, persists `workload_class` through TaskIR canonicalization and progress task records, and keeps legacy inference for older records. **Live request context closed 2026-06-28**: orchestrator `f895282d` adds explicit `ChatRequest.workload_class`, request-local `LLMPrimitives` workload-class state, backend request metadata propagation, delegated specialist preservation, and scheduler-policy wrapping without changing admission priority or promoting any capability row.
- [x] **W1 — registry schema + seed rows** (~1 day): `orchestration/capability_registry.yaml` per §C.1 schema; seed with the first-cohort levers (W4 list) plus existing operator-only rows. Acceptance: schema-validates; every row names applicator, range, evidence with protocol id, risk, `actionable_by`.
- [x] **W2 — compilation targets** (~1 day): compile registry → planner Action-Availability section (generated allow/deny + reasons, replacing program.md's hand-maintained denylist) and → master-index `A-by` column (script per §E.4, not hand-edit). Acceptance: both outputs regenerate from the YAML; a row edit propagates to both.
- [ ] **W3 — safe role-restart applicator** (~2–3 days): `config_applicator.restart_role(role, env_overrides, registry_overrides)` per §C.2 — pause autopilot dispatch via existing contention/queue path → `orchestrator_stack.py reload <role>` → health gate (`wait_for_health` + one canned smoke completion) → rollback to prior config on fail → journal `exogenous_role_restart` boundary (spanning trials auto-excluded). Batched restart-class trial protocol (one restart, several trials, restore) enforced by the dispatch gate, declared in the capability row; strict callers must pass explicit affected roles and a smoke hook, not infer restart scope. Acceptance: shadowed restart of one role passes attestation; a deliberately failed health gate rolls back.
  - [x] **W3-a — the "deliberately failed health gate rolls back" acceptance half is now covered by an
        induced-failure unit test ✅ 2026-08-12.** Measured before writing anything: `coverage run
        --rcfile=/dev/null --include='*config_applicator.py' -m pytest tests/unit/test_config_applicator.py`
        showed the entire `role == "orchestrator"` branch of `restart_role()` — the ONLY place the API
        health gate is consulted — as never executed (lines 2221-2223, 2228-2230, 2232, 2246-2248), because
        all 44 existing tests pass a MODEL role and evaluate that branch False. The rollback tests that did
        exist induce a *reload* failure or a *smoke* failure; both reach the same rollback block from a
        different source, so a health-gate regression was invisible. Also uncovered: the empty-role guard
        (2144) and the registry-restore-exception path (2292-2293). Five tests added; `restart_role()` now
        has zero missing statements. Five mutations, each caught by exactly the intended test with the suite
        still reporting 49 collected: health gate forced green, health failure swallowed, empty-role guard
        removed, registry-restore failure laundered to `ok`, smoke run despite a failed health gate.
  - [ ] **W3-b — BLOCKED on a reload window owned by the inference session.** The remaining acceptance half
        is a LIVE shadowed role restart, and reload ownership belongs to whichever session owns the
        inference — running one around it caused INC-20260728-reload-preemption. Everything reachable
        without executing a reload is now done; this row needs a reload window, not more code. Stated in
        blocker grammar deliberately, so `backlog_row_check.py` refuses to dispatch W3 to a session that
        cannot finish it — the 2026-08-12 dispatch that produced W3-a screened DISPATCHABLE with no blocker.
- [ ] **W4 — promotion workflow + first cohort** (recurring, ~half day/month): monthly pass per §C.3 — promote operator→autopilot when descriptor/applicator wired + range validated + kill condition written + one shadowed trial passes attestation. First cohort: `moe_spec_budget`, per-role `enable_thinking`, EA compaction profiles (S8/S9), draft_max/p_split where spec-dec is on, and `edit_transaction_auto_routing` (A2 rollout contract prepared in [`multi-file-coding-completion-capability.md`](benchmark-suites.md#track-multi-file-coding-completion-capability)). Acceptance: first pass executed and logged; promoted rows flip `actionable_by`.

##### First-cohort note: edit transaction auto-routing

`edit_transaction_auto_routing` is the proven protocol fix for routine coding edits, but it is not yet an
autopilot lever. Seed its future registry row as `actionable_by=operator` until the A2 contract's clean-window
A/B, scoped-root attestation, and kill conditions exist. The current production-safe surface is explicit
`force_mode="edit"` only; missing `ORCHESTRATOR_EDIT_TRANSACTION=1` or scoped `ORCHESTRATOR_EDIT_ROOT`
must continue to fail closed rather than falling back to REPL.

2026-06-19 checkpoint: Orchestrator `3f6692b` made the first-cohort A2 row executable as a guarded
placeholder: the id now matches this handoff (`edit_transaction_auto_routing`), `actionable_by=operator`
is explicit, the A2 kill condition is recorded in the row, and the registry loader rejects any promoted row
without a `kill_condition`. Orchestrator `63bbc8b` tightened the loader further: `actionable_by` must be
`operator`, `autopilot`, or `gated:<condition>`, and `promotion_state=promoted` rows must be
autopilot-actionable with a non-empty string kill condition. W2/W3/W4 remain gated; no autopilot action
surface was enabled.

2026-06-27 checkpoint: Orchestrator `d9fe32eb` adds the W2 compiler foundation. `src/registry/capability_registry.py`
now compiles capability rows into generated planner Action-Availability text and a generated index A-by table;
`scripts/registry/compile_capability_registry.py` exposes both outputs as CLI targets. AutoPilot appends the
generated capability section to the existing `### Action Availability` prompt/critic surface, so the planner now
sees all first-cohort levers as registry-derived blocked/operator-only rows. No capability was promoted and no
dispatch/applicator path was enabled; the generated index table exists, but live master-index column replacement
still needs a deliberate adoption pass.

2026-06-27 follow-up: the generated `index-a-by` table was adopted into
`master-handoff-index.md` under "Generated Capability A-by Table" with the exact compiler command. This closes W2
without changing any row's `actionable_by` or `promotion_state`: all restart-class levers remain gated on
`evidence-plane-ledger.md Phase 1`, and `edit_transaction_auto_routing` remains operator-only.

2026-06-27 W2 guard + W3 first primitive: Orchestrator `7b47671e` added `--replace-block` and `--check-block`
to the capability compiler so the generated master-index A-by table can be mechanically checked. Root `82904490`
wrapped that table in capability-registry markers and recorded the check command. Orchestrator W3 follow-up adds a
dormant `restart_role(role, env_overrides, registry_overrides)` primitive with mocked success and rollback coverage
for env-backed role restarts. Registry overrides still fail closed until a rollback record exists, and W3 remains
open for dispatch pause, smoke completion, exogenous restart journaling, and shadow attestation.

2026-06-27 W3 boundary journal slice: Orchestrator adds an append-only `role_restart_boundary` journal event and
optionally attaches it from `restart_role(..., journal=...)`. The event uses `boundary_trial_id` rather than
reserved `trial_id`, round-trips without counting as a trial, and is ignored by archive reconstruction. This closes
the W3 journal-record primitive only; W3 remains open for dispatch pause, smoke completion, co-hosted-role
resolution, registry override rollback semantics, and a shadowed live restart attestation.

2026-06-28 W3 dispatch-pause slice: Orchestrator `config_applicator.restart_role()` now accepts
`pause_dispatch=True` plus an optional AutoPilot state path and grace period. When requested, it sets
`paused=True` in the AutoPilot state file before invoking `orchestrator_stack.py reload <role>`, fails closed before
reload if the state file cannot be paused, and restores `paused=False` only if the applicator changed it from false.
The pause result is attached to the restart payload and is restored on both successful reloads and rollback paths.
This closes the W3 dispatch-pause primitive without promoting any capability row or touching the live AutoPilot run.

2026-06-28 W3 registry-rollback slice: Orchestrator `config_applicator.restart_role()` now applies
`registry_overrides` as dotted YAML paths against an explicit registry file, records the exact prior leaf values, and
atomically restores that rollback record before the rollback reload when reload or smoke gating fails. Missing parents
fail closed before any reload, and restart-boundary events now include the registry override keys. This closes the W3
registry override rollback primitive without promoting any capability row or touching the live stack. W3 remains open
only for a shadowed live restart attestation once the evidence plane allows restart-class experiments.

2026-07-03 W3/W4 protocol hardening: Orchestrator now requires every `role_restart` / `stack_restart` capability row to
declare a structured `trial_protocol` mapping (`class: batched_restart`, `min_trials >= 1`,
`restore_after_batch: true`, and non-empty `boundary_event`). The first restart-class rows (`moe_spec_budget`,
`ea_compaction_profiles`, and `draft_max_p_split`) now carry the shared `role_restart_boundary` / 5-trial restore
contract. This does not promote any row or enable live restarts; it makes the C.2 batched restart protocol a validated
data contract before future W4 promotion work.

2026-07-04 W3 strict-scope hardening: Orchestrator `config_applicator.restart_role()` now has strict opt-in gates for
future promoted callers: `require_explicit_affected_roles=True` fails before dispatch pause, registry edits, or reload
unless the caller supplied the exact restart surface; `require_smoke_check=True` likewise fails before reload unless a
role smoke hook is present. The capability registry restart protocol now requires `smoke_check: canned_completion` and
`require_explicit_affected_roles: true` on every `role_restart` / `stack_restart` row. This keeps the existing manual
helper compatible while ensuring future AutoPilot promotion cannot rely on stack-prior inference or skip the smoke
gate. W3 still waits for a shadowed live restart attestation.

#### Gates & pitfalls

- Hard gate: W1–W4 wait for `evidence-plane-ledger.md` (findings-01 Phase 1) — same gate as the index rewrite's A15 row. Do not hand the optimizer restart-class levers on an uncertified instrument.
- Lifecycle ONLY via `orchestrator_stack.py` (`feedback_use_orchestrator_stack_for_lifecycle`) — the applicator must never kill PIDs directly.
- The registry is the rollback record — restart with overrides not recorded in it and rollback is undefined.
- Same-GGUF roles share one server process (`feedback_same_model_roles_share_server`): a "role restart" can bounce sibling roles — the promoted path must pass an explicit affected-role set and journal the boundary for ALL roles on that process.
- A-by column and Action-Availability must only ever be generated (W2); one hand edit and the two sources of truth diverge permanently.

#### Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; any number cited follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar.

#### Checkpoints

- [x] **2026-08-05 staleness audit:** re-read the live orchestrator implementation and registry rather than refreshing this file cosmetically. `config_applicator.restart_role()` and its boundary/trial-protocol gates remain present; the registry still contains only `promotion_state: placeholder` rows, and focused tests explicitly preserve the no-live/no-promoted invariant. No live shadow-restart attestation was found. Therefore W3 stays open on its acceptance test and W4 stays open with zero promotions; the obsolete blanket “evidence plane Phase 1” priority wording above is replaced by the narrower, current gate. ✅ 2026-08-05

- 2026-06-13 W0 interface branch-ready: `feat/workload-traffic-classes` commit `b62946d`, based on F1 `feat/task-record-harvester` `40bde0d`. GitNexus re-indexed the worktree first (48,880 nodes, 83,890 edges, 300 flows). Formal graph impact could not resolve `orchestration/workload_model.yaml` (`UNKNOWN`); manual `rg` found only the F1 harvester reading it. Separate GitNexus impact on live `LLMPrimitives.request_context` was HIGH, so this pass avoided live request tagging. Validation: `python3 -m py_compile src/workload_model.py tests/unit/test_workload_model.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_workload_model.py tests/unit/test_task_harvester.py` -> 6 passed, 1 pytest config warning; `uv run --with ruff ruff check src/workload_model.py tests/unit/test_workload_model.py` passed; `git diff --cached --check` passed.
- 2026-06-19 A2 first-cohort row tightened on active: Orchestrator `3f6692b` (`Canonicalize edit transaction capability row`) updated `orchestration/capability_registry.yaml`, `src/registry/capability_registry.py`, and `tests/unit/test_capability_registry.py`. Validation: `python3 -m py_compile src/registry/capability_registry.py tests/unit/test_capability_registry.py`; `uv run pytest -q tests/unit/test_capability_registry.py` -> 47 passed; `uv run ruff check ...`; `git diff --check`.
- 2026-06-19 W0/A2 hardening on active: Orchestrator `02370da` persists explicit `workload_class` on TaskIR/task records while keeping legacy inference (`uv run pytest -q tests/unit/test_workload_model.py tests/unit/test_task_ir.py tests/unit/test_progress_logger_task_record.py tests/unit/test_task_harvester.py` -> 17 passed). Orchestrator `63bbc8b` fail-closes promoted capability rows unless they are autopilot-actionable and carry a non-empty string kill condition (`tests/unit/test_capability_registry.py` included in the 122-test focused gate). Live edit auto-routing remains deferred/gated.
- 2026-06-28 W0 live request-context closure: Orchestrator `f895282d` wires workload class through the live request context. `ChatRequest.workload_class` is constrained to `interactive|eval_batch|campaign`; unset requests infer from existing metadata, so background/batched calls attribute as `eval_batch` while preserving existing admission priority behavior. `LLMPrimitives.request_context()` now stores request-local workload class in diagnostics, forwards it to backend request metadata, and delegated specialist contexts preserve it. `SchedulerPolicy` mirrors the field for interaction-lifecycle wrappers. GitNexus impact on the exact `LLMPrimitives.request_context` method was LOW (`impactedCount=3`; the earlier HIGH concern is no longer present on the current graph). Validation: `python3 -m py_compile` on touched modules/tests; `uv run ruff check ...`; `uv run pytest -q tests/unit/test_llm_primitives.py tests/unit/test_inference_mixin.py tests/unit/test_interaction_lifecycle.py tests/unit/test_workload_model.py tests/unit/test_task_ir.py` -> `70 passed`; `git diff --check`.
- 2026-06-27 W2 compiler foundation: Orchestrator `d9fe32eb` wires generated capability-registry availability into AutoPilot planning and adds `compile_capability_registry.py --target action-availability|index-a-by`. Validation: `python3 -m py_compile src/registry/capability_registry.py scripts/registry/compile_capability_registry.py scripts/autopilot/autopilot.py tests/unit/test_capability_registry.py tests/unit/test_autopilot_creativity.py`; `uv run pytest -q tests/unit/test_capability_registry.py tests/unit/test_autopilot_creativity.py` -> 70 passed; `uv run ruff check ...`; both compiler targets emitted expected generated output. No live capability promotion.
- 2026-06-27 W2 index adoption: Root docs adopted the generated `index-a-by` table in `master-handoff-index.md`. Validation: reran `uv run python scripts/registry/compile_capability_registry.py --target index-a-by`; GitNexus impact was HIGH for both root docs because they are coordination surfaces, so the edit stayed in the main thread. No runtime files or capability promotion states changed.
- 2026-06-27 W2 drift guard + W3 primitive: Orchestrator `7b47671e` added marked-block replace/check support to `compile_capability_registry.py`; Root `82904490` adopted the marked block. Orchestrator W3 primitive adds `restart_role()` env rollback support but does not wire planner/AutoPilot calls. Validation: `uv run pytest -q tests/unit/test_capability_registry.py` -> 55 passed; `uv run python scripts/registry/compile_capability_registry.py --target index-a-by --check-block /mnt/raid0/llm/epyc-root/handoffs/active/master-handoff-index.md` passed; `python3 -m py_compile scripts/autopilot/config_applicator.py tests/unit/test_config_applicator.py`; `uv run pytest -q tests/unit/test_config_applicator.py` -> 10 passed; `uv run ruff check scripts/autopilot/config_applicator.py tests/unit/test_config_applicator.py`.
- 2026-06-27 W3 boundary journal slice: Orchestrator added `role_restart_boundary` append-only events plus optional `restart_role(..., journal=...)` attachment. Validation: `python3 -m py_compile scripts/autopilot/experiment_journal.py scripts/autopilot/config_applicator.py tests/unit/test_journal_supersession_events.py tests/unit/test_config_applicator.py`; `uv run pytest -q tests/unit/test_journal_supersession_events.py tests/unit/test_config_applicator.py` -> 22 passed; `uv run ruff check ...`; `git diff --check`.
- 2026-07-03 W3/W4 protocol hardening: Orchestrator validates structured restart-class `trial_protocol` rows and populates the first-cohort restart rows with the batched-restart/restore/boundary contract. Validation: `uv run pytest -q tests/unit/test_capability_registry.py` -> 58 passed; `python3 -m py_compile`; `uv run ruff check src/registry/capability_registry.py tests/unit/test_capability_registry.py`; both capability compiler targets; and generated block drift check against the root master index.
- 2026-07-04 W3 strict-scope hardening: Orchestrator added strict-mode `restart_role()` gates for explicit affected roles and required smoke hooks, and the registry validator now rejects restart-class rows without `smoke_check` plus `require_explicit_affected_roles: true`. Validation: GitNexus impact was LOW for `_validate_entry` (`impactedCount=8`) and `restart_role` (`impactedCount=0`); `uv run pytest tests/unit/test_config_applicator.py tests/unit/test_capability_registry.py -q` -> 81 passed; `uv run ruff check scripts/autopilot/config_applicator.py src/registry/capability_registry.py tests/unit/test_config_applicator.py tests/unit/test_capability_registry.py`; both capability compiler targets rendered.
- 2026-08-12 W3 health-gate acceptance (W3-a): the backlog row that dispatched this reads "build `config_applicator.restart_role()` … the ONE missing applicator", and that premise is **false** — the applicator has existed since the 2026-06-27…07-04 slices and the 2026-08-05 audit re-confirmed it. What was actually missing was the row's own second acceptance clause. Coverage-measured first, not assumed: `restart_role()`'s `role == "orchestrator"` branch (the only consult of `health_check`) had **zero** executed statements across all 44 existing tests, so "a deliberately failed health gate rolls back" was untested; the empty-role guard and the registry-restore-exception path were likewise dead. Orchestrator `tests/unit/test_config_applicator.py` adds five induced-failure tests (health gate fails → env+registry rollback, boundary journaled, smoke never invoked; health ok + smoke fails → rollback; both green → one reload, no rollback; empty role fails closed before any reload; registry-restore exception is recorded and does not swallow the env rollback). Validation: `.venv/bin/python -m pytest -q tests/unit/test_config_applicator.py` -> **49 passed** (was 44, so the five are counted by the reporter); `coverage` re-run shows **zero** missing statements in `restart_role()` (2112-2329); five mutations run against an out-of-tree mutated copy of the module (never writing the shared file) each failed exactly one intended test — `health_gate_always_ok`, `health_failure_not_recorded`, `no_empty_role_guard`, `registry_restore_laundered`, `smoke_runs_despite_health`; `ruff check` clean; `git diff --check` clean. **No reload was executed** — `subprocess.run` is stubbed in every test, and reload ownership belongs to the inference-owning session (INC-20260728-reload-preemption). Call-site check: `restart_role()` does have a production caller chain (`apply_role_restart_params` → `restart_role`, `config_applicator.py:1556`, reached from `apply_params`), fail-closed behind `AUTOPILOT_AP3_ROLE_RESTART_ENABLE` and zero promoted registry rows — so it is wired, not orphaned.

## Track: model-artifact-integrity
<!-- gate: none -->

> Folded from `handoffs/active/model-artifact-integrity.md` @ `05e2b812a086` on 2026-11-02 (BRF-T1-F4, route 1a, operator D1/D5; retired row RTG-59 → RTG-36). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Model artifact integrity — pinned, verified and reviewed weights and templates

**Status**: stub
**Created**: 2026-10-21 (via research intake, operator-approved 2026-10-21 plan intake-backdoor-cvec-20261020)
**Scratch**: `/mnt/raid0/llm/tmp/model-artifact-integrity/`
**Categories**: local_inference, agent_architecture, tool_implementation
**Related**: [model-exec-containment.md](stack-lifecycle-program.md#track-model-exec-containment) (runtime side) · [qwen-chat-template-evaluation.md](harness-program.md#track-qwen-chat-template-evaluation) (template CHOICE and CT-12; this handoff owns template INTEGRITY) · [model-stack-update-pipeline-audit.md](stack-lifecycle-program.md#track-model-stack-update-pipeline-audit) (registry consistency)

#### Objective

Make every GGUF, drafter and chat template we serve traceable to a pinned upstream revision and a
recorded hash, checked at download, at launch and at re-pull, and give community fine-tunes a review
gate before they reach a tool-bearing role. A backdoor can live in weights (intake-2191#record) or in a
chat template with no weight change (intake-2200#record), and community relays can repackage trusted
weights with extra sidecar files under misleading labels (intake-2197#record).

#### Current state (verified 2026-10-21)

- `scripts/utils/safe_download.py` only cleans up partial files; it records no revision or sha256.
- The model registry carries free-text provenance for a few roles; `validate_model_registry.py` checks
  no sha256 or revision fields; no GGUF hash is verified at llama-server launch.
- `served_template_sha256_12` exists for three roles and is read only by an offline certification
  check; the launcher does not compare the served template with a pin. Template override files are
  owned by the service user.
- No production `--lora` or `--control-vector` is loaded.

#### Tasks

- [x] **SEC-ART-1 — Revision and sha256 pinning at download.** scripts/utils/safe_download.py records the resolved HF commit sha and per-file sha256 (LFS oid) into a download ledger; new-model Step 0 passes --revision; add hf_repo / hf_revision / sha256 fields to the model registry schema, check them in validate_model_registry.py and backfill the serving lineup. ✅ 2026-10-24
  - 2026-10-21 (workspace-f8): IMPLEMENTED, NOT ticked. Root `a9fccdc21`: `safe_download.py` `--hf-repo/--revision/--no-resolve/--provenance-ledger` (resolves commit sha, forces `hf download --revision <sha>`, appends per-file LFS sha256 to `data/provenance/model_downloads.jsonl`); new-model Step 0 passes `--revision`. Orchestrator `a9a3365a`: `registry_validator.py` checks `roles.<role>.model.{hf_repo,hf_revision,sha256}` (missing = WARN; malformed = error; `REGISTRY_ARTIFACT_PINS_STRICT=1` / `--strict-artifact-pins` makes missing fatal) and `scripts/validate/backfill_registry_artifact_pins.py` (plan only, size-match to HF LFS oid, no GGUF hashing). Pending: lineup backfill into the master registry and the strict flip (SEC-ART-1.1).
  - 2026-10-24 (f8 sweep): lineup backfill done and strict flipped (SEC-ART-1.1 note); SEC-ART-1 closes when the owning session merges research `7b157602` then orchestrator `26d0d033`.
- [x] SEC-ART-1.1 — run the registry backfill (HF tree API read-only; network go-ahead given 2026-10-21 by workspace-f8 for metadata reads only) then flip strict mode ✅ 2026-10-24
  - 2026-10-24 (f8 sweep): backfill APPLIED and strict FLIPPED on branches, box left open until they merge. Research `f8/sec-art-11-20261024` @ `7b157602` pins the last 2 unpinned lineup roles, `draft_qwen25` (QuantFactory/Qwen2.5-0.5B-GGUF @ 808e8756) and `draft_qwen3_coder_0_75b` (jukofyork/Qwen3-Coder-Instruct-DRAFT-0.75B-GGUF @ 07e59a56), both size-matched to the HF LFS entry, `uploader_class: community`, not tool-bearing. All 16 lineup roles are now pinned (14 were pinned by research `4691a43f2`), 0 exempt; 5 sequential HF metadata reads, no downloads. It also fixes a duplicate `baseline_tps`/`optimized_tps` key that broke strict YAML loading (loaded value unchanged). Orchestrator `f8/sec-art-11-20261024` @ `26d0d033`: validator + stack-change pipeline treat a missing lineup pin as an ERROR by default (opt-out `REGISTRY_ARTIFACT_PINS_STRICT=0`); backfill script resolves relative paths against the model base and spaces requests (`--request-interval`, default 1 s); lean registry regenerated (only diff: the 2 pins); `--strict-artifact-pins` OK; 130/130 touched-module tests pass (6 wider-sweep failures pre-exist on origin/main). Runtime `artifact_integrity.pins_strict` stays false on purpose: it gates the launcher fingerprint ledger, which does not exist until the SEC-ART-2 registration run. MERGE ORDER: research `7b157602` first, then orchestrator `26d0d033` (else `start` recompiles without the drafter pins and the strict default refuses). Tick on merge.
  - 2026-10-24 (f8, main): LANDED. Reviewed (pins re-verified against HF tree API + full sha256 of both on-disk GGUFs; blast radius LOW: only `stack_commands.cmd_start` -> `validate_or_raise`; `reload` unaffected). Research `7b157602` merged to main, the shared research clone fast-forwarded (ff-only, operator-approved) to `99301fa14` so `start` reads the pinned master, then orchestrator `26d0d033` merged (main `1eff8145`). All 16 lineup roles pinned, missing pin = FATAL at `start` (opt-out `REGISTRY_ARTIFACT_PINS_STRICT=0`). The launcher-side `pins_strict` stays false until the SEC-ART-2 fingerprint ledger exists. The shared orchestrator clone picks this up at its next ff (nib2-gnx1-reindex-2) or pull.
- [ ] **SEC-ART-2 — Launch-time GGUF fingerprint check.** Hash each lineup GGUF in full at registration; at launch compare a stat fingerprint (size, mtime, inode) and re-hash only on change; the launcher refuses a role whose GGUF does not match its pin; a test uses a touched copy.
  - 2026-10-22: code + tests LANDED, box left OPEN — orchestrator `bbc74d5c` (origin/main) `6dbc4e27` (`artifact_integrity.py`: `register_gguf`, `verify_gguf_for_launch`, launcher wiring in `orchestrator_stack.build_server_command` / `stack_commands`; `test_artifact_integrity.py`, `test_launcher_artifact_integrity.py`), `bbc74d5c` (`register_gguf_fingerprints.py`). MISSING: the registration run itself (acceptance: "hash each lineup GGUF in full at registration"); the fingerprint ledger `/mnt/raid0/llm/cache/artifact_fingerprints.json` does not exist yet and `runtime_defaults.artifact_integrity.pins_strict` is false, so the launcher only WARNS today. Tick after SEC-ART-POST-a and a proven launch refusal on a touched copy.
- [x] **SEC-ART-3 — Uploader class and review record for tool-bearing roles.** Add an uploader_class field (first-party / allowlisted re-quantizer / community) to the registry; a stack-change gate refuses to give a community fine-tune tool access without a recorded review covering provenance, a base-model diff where a base exists, and a label-vs-function check of every launch flag that changes generation (intake-2191#07, intake-2199#03, intake-2197#record).
  - ✅ 2026-10-22 — orchestrator `bbc74d5c` (origin/main) `9769590d` (`src/registry/artifact_review.py` community-review gate wired into `scripts/registry/stack_change_pipeline.py`; `test_artifact_review_gate.py`); research `0a71fd5d6` (master registry `uploader_class: allowlisted_requantizer` on the 14 unsloth/lmstudio-community lineup roles, one-time frontdoor/worker GGUF review `qwen36-35b-a3b-mtp-q8-frontdoor-20261022.md`).
  - *(2026-10-21, operator.)* Allowlist decided (option B): `unsloth` and `lmstudio-community` are allowlisted re-quantizers; a one-time review of the frontdoor and worker GGUFs comes first, before the field is populated for them.
- [ ] **SEC-ART-4 — Enforce served-template pins at launch.** Add a 64-hex served_template_sha256 for every lineup role; before llama-server starts, the launcher hashes the effective template (GGUF tokenizer.chat_template or the --chat-template-file bytes) and refuses on mismatch; a test uses a one-byte-modified template copy (today the 12-hex pin is read only by an offline certification check; intake-2200#05).
  - 2026-10-22: code + tests LANDED, box left OPEN — orchestrator `bbc74d5c` (origin/main) `6dbc4e27` (launch-time template hash check, `TemplatePinError`, refuses before Popen) and `9769590d` (validator `_check_template_pins`); research `4691a43f2` backfilled 64-hex `served_template_sha256` on 4 server_mode roles (frontdoor, worker_vision, architect_critic, architect_general). MISSING: acceptance says "every lineup role"; GGUF-embedded-template roles such as `qwen25_coder_32b_q4km`, `reap_25b`, `architect_coding` carry no pin (confirm which are lineup, then run `backfill_template_pins.py`), and `template_pins_strict` is false (WARN only). Plus a live launch proof (SEC-ART-POST-d).
- [x] **SEC-ART-5 — Upstream template diff at onboarding.** new-model records upstream_template_sha256, served_template_sha256 and a reviewed diff path for every GGUF; validate_model_registry.py requires them for lineup roles. [belief: cc]
  - 2026-10-22: tooling LANDED, box left OPEN — orchestrator `bbc74d5c` (origin/main) `bbc74d5c` (`template_provenance.py`, `apply_registry_integrity_pins.py`); research `4691a43f2` (upstream/served digests + `data/template_reviews/*.diff` for the 4 template roles; `validate_model_registry.py` Check 6 requires them, `test_validate_model_registry_templates.py`). MISSING: every one of the 4 `template_diff_reviewed` entries still reads "human review sign-off pending" (SEC-ART-POST-b), and the same lineup-coverage gap as SEC-ART-4.
  - 2026-10-31 partial source checkpoint: APP `afb87d5d4b056232cc804c6333fd8e0420988a9c` (verified main `4408254125460317a262c3774fa1850890cb41fd`) fixes byte-inaccurate review rendering: distinct invalid UTF-8 templates can no longer produce a false “identical” diff; valid UTF-8 stays readable and unterminated lines are delimited. Actual-lane 19 focused controls, mandatory `make gates`, Ruff and staged privacy pass; the pinned formatter changed only test whitespace with identical AST. [Git evidence](../../artifacts/engineering/sec-art5-byte-review-20261031/EVIDENCE.json). Signing/admission/schema and production remain unchanged. The checkbox stays OPEN: new-role onboarding still needs a valid staging order because Step1.5 requires `server_mode.<role>` before Step4 creates only `roles.<role>`; POST-b/c already closed the old lineup signoff/coverage gaps. [no-belief: source conformance only; no measurement-grade claim tuple]
  - 2026-11-01: `/new-model` now stages the confirmed role before applying pins, calls for human diff review before recording sign-off, and preserves master-registry comments. A synthetic staged entry accepted all template fields through the existing pin helper. The research validator enforces their presence once a role is deployable; candidates are checked directly at onboarding. [no-belief: source conformance only; no measurement-grade claim tuple]
- [x] **SEC-ART-6 — Read-only template store.** Serve template override files from a location agent sessions cannot rewrite (or a content-addressed path named by sha256), referenced from the registry, so the launch check is not the only barrier.
  - ✅ 2026-10-22 — acceptance met: module + published content-addressed store + registry re-point (SEC-ART-POST-e, research `95f90f04f`). REMAINING (not part of this box): the lean-registry recompile so the launcher sees the pins (SEC-ART-POST-f), and the operator-side root ownership / `chattr +i` decision (files are still same-uid-writable).
  - 2026-10-22: module LANDED, box left OPEN — orchestrator `bbc74d5c` (origin/main) `94de63e9` (`src/registry/template_store.py`: `<64hex>.jinja` 0444 in a 0555 dir, `check_template_path`, `verify_store`, `publish`; `test_template_store.py`). MISSING: the store directory `/mnt/raid0/llm/models/chat-templates/sha256` does not exist, the registry `chat_template_file` entries still point at the plain override files (e.g. `epyc-qwen3x-v1-terse.jinja`), and the files stay same-uid-writable (module docstring: root-owned + `chattr +i` is an operator action). Tick after publish + registry re-point via stack-change (SEC-ART-POST-e).
- [x] **SEC-ART-7 — Re-pull drift check.** safe_download refuses to overwrite or upgrade a registered artifact when the repo commit sha or any file LFS oid differs from the registry pin, unless a review record is passed; a test uses a mocked HF tree-API response.
  - ✅ 2026-10-22 — root `0c8acc08f`: `scripts/utils/model_pin_guard.py` wired into `safe_download.py` (drift gate runs BEFORE the download; refuses on commit or LFS-oid drift, missing oid, tree-API failure and `--no-resolve` on a registered repo; `--review-record` lifts exactly the reviewed drift and is ledgered); `tests/test_model_pin_guard.py` (mocked tree API). Registry pins now exist (research `4691a43f2`), so the guard is live for the lineup.
- [x] **SEC-ART-9 — Relay and sidecar check.** When a repo presents itself as a copy of an upstream, compare every LFS oid with the claimed upstream through the HF tree API and list every file the upstream lacks (intake-2197#00 found a byte-identical relay plus one refusal-direction sidecar); record the result in the SEC-ART-3 review.
  - ✅ 2026-10-22 — root `24e9adec4`: relay/sidecar check against the claimed upstream via the HF tree API; `tests/test_relay_sidecar_check.py`.

#### Post-landing steps (2026-10-22, workspace-f8)

- [x] **SEC-ART-POST-a — Register GGUF fingerprints (IO-heavy; scheduled window; do NOT run ad hoc).** `register_gguf_fingerprints.py register` full-hashes every lineup GGUF (30-90 GB each) once. Launcher plan, to be cut by the owning session as a CPU-queue job (IO task, not a timing window; never during a timing run; one hasher at a time; `nice -n 19 ionice -c3`; the ledger update is flock-protected and does not touch running servers): `cd /workspace/repos/epyc-orchestrator && nice -n 19 ionice -c3 /usr/bin/python3 scripts/validate/register_gguf_fingerprints.py register --registry /workspace/repos/epyc-inference-research/orchestration/model_registry.yaml > /mnt/raid0/llm/tmp/model-artifact-integrity/register-$(date +%Y%m%dT%H%M%S).log 2>&1`, then `... check` (stat only). A digest differing from a registry pin records nothing and fails loudly: treat it as a SEC-ART finding, not noise. Unpinned files are skipped unless `--adopt-unpinned` (proposal only; an adopted hash verifies nothing upstream). Exit when the ledger exists and `check` is clean; then flip `pins_strict` via stack-change. ✅ 2026-10-23
  - 2026-10-22: armed, booked. Job `sec-art-fingerprints` (FILLERS row; launcher `/mnt/raid0/llm/tmp/f8-launchers-20261022/sec-art-fingerprints/launch.sh`, pid 555983) is booked by workspace-58 on q0/q1 tonight, done by 06:15Z. Tick when the ledger exists and `check` is clean.
  - *(2026-10-23.)* Job `sec-art-fingerprints` PASSED 2026-10-23T00:04Z: 6/6 lineup GGUF rows registered and `check` rc 0, not_ok empty; ledger `/mnt/raid0/llm/cache/artifact_fingerprints.json` sha256 37e9c439…675d (code orch bbc74d5cc, registry research 0a71fd5d6). SEC-ART-2 stays open until SEC-ART-POST-f puts the pins in the lean registry the launcher reads.
- [x] **SEC-ART-POST-b — Human sign-off of each `template_diff_reviewed` entry (operator action).** Four registry entries (frontdoor, worker_vision, architect_critic, architect_general) read "human review sign-off pending". Read `data/template_reviews/{frontdoor,worker_vision,architect_critic,architect_general}.diff` in epyc-inference-research and replace each entry with a signed review line. The measurement/trust boundary is human-amendment-only: an agent does not write this sign-off. [no-belief: operator-action]
  - *(2026-10-23 15:05Z, operator decision.)* The operator chose a digest plus ONE ratify command for the four `template_diff_reviewed` sign-offs; a subagent is preparing it. Not ticked until the operator runs the ratify command.
  - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up.)* **Digest and ratify script prepared, NOT landed.** Root branch `f8/sec-art-post-b-ratify` @ `8093e1ad1` adds `scripts/operator/ratify_sec_art_post_b_20261023.sh`; the main session lands it.
    - Modes: `--dry-run` (default), `--verify`, and `--apply --attest RATIFY-SEC-ART-POST-B-20261023 --digest-sha256 <sha>`.
    - It is pinned to the four diff sha256s at research `62c2e09da` and to the sha256 of the PRIVATE review digest (`/mnt/raid0/llm/private/sec-art-post-b/`, never committed).
    - **One CONCERN** from the review for the operator: a template-authored "SYSTEM WARNING" injection into tool results on frontdoor and architect_critic. The operator decision is pending; not ticked.
  - *(2026-10-23 ~15:40Z, workspace-f8: OPERATOR DECISION.)* Option chosen: **sign all 4 now, then strip the injection in a v2 template.** The signature attests the served bytes as reviewed, warning text included; the CONCERN (frontdoor.diff:444-471 / architect_critic.diff:453-480, template-authored `⚠️ SYSTEM WARNING` appended inside `<tool_response>` on error keywords) is removed by SEC-ART-POST-b.1 below. Digest: private `/mnt/raid0/llm/private/sec-art-post-b/TEMPLATE_REVIEW_DIGEST.md`, sha256 `50c357749c54064da46aa8f9a0e49f9fd0d63f4cb08924469d8a6767b29e2516`. The operator runs (the script commits itself + receipt to root and the 4 signed lines to research `orchestration/model_registry.yaml`, each under the push lock): `RATIFY_OPERATOR='<name>' bash /mnt/raid0/llm/worktrees/f8-sec-art-post-b/scripts/operator/ratify_sec_art_post_b_20261023.sh --apply --attest RATIFY-SEC-ART-POST-B-20261023 --digest-sha256 50c357749c54064da46aa8f9a0e49f9fd0d63f4cb08924469d8a6767b29e2516` (then `--verify`). Note: `validate_model_registry.py` Check 6 does not read the signed-line format; only the script's `--verify` does.
  - [ ] **SEC-ART-POST-b.1 — `epyc-qwen3x-v2` chat template without the tool-result SYSTEM WARNING injection.** Drop the keyword scan and the appended warning (served froggeric-v22.3 file, frontdoor.diff 445-457 + 467-471); publish via `template_store publish`, new diff vs upstream, digest and operator sign-off; roll out to frontdoor + architect_critic at the next stack change (with SEC-ART-POST-f). Done when both roles serve v2 with a signed review and a render test proves no template-authored text appears in a tool result. Filed 2026-10-23 (workspace-f8, operator decision).
    - *(2026-10-23 16:30Z, workspace-f8 subagent.)* v2 PREPARED, not published, not bound. Research branch `f8/sec-art-post-b1-v2-template` @ `6df1516a6` (pushed, not merged): `data/chat_templates/epyc-qwen3x-v2.jinja` sha256 `925def46621a41f233403e5199be4b8a596ea5cecd747586ff256d7032da0c91` (23458 bytes), a minimal edit of the served v1 `1443ea9a…` (copy beside it): the 13-line keyword scan, the 5-line warning block, the `consecutive_failures` counter (namespace field + per-user-turn reset) removed, `template_version` -> `epyc-qwen3x-v2-froggeric-v22.3`, nothing else. New review diffs `data/template_reviews/{frontdoor,architect_critic}.v2.diff` written by `template_provenance.build_row` (the same call regenerates the committed v1 diffs byte-identically). Render test `scripts/test_epyc_qwen3x_v2_template.py` (jinja2, 29 fixtures x 8 kwarg sets = 232 renders): 128 byte-identical v1/v2, 104 differ, all on the 13 scan-triggering fixtures and only by the injected warning; v2 `<tool_response>` bodies equal the tool content on every render. Remaining for the box: (1) `cd /workspace/repos/epyc-orchestrator && /usr/bin/python3 -m src.registry.template_store publish /mnt/raid0/llm/worktrees/f8-sec-art-post-b1-research/data/chat_templates/epyc-qwen3x-v2.jinja` then `... template_store verify`; (2) operator sign-off of the v2 diffs; (3) at the next stack change, re-point frontdoor + architect_critic `chat_template_file` to `sha256/925def46….jinja` and update `served_template_sha256`/`_12`/`_bytes`, `template_diff` -> `*.v2.diff`, `template_version`/`provenance` (with SEC-ART-POST-f).
  - ✅ 2026-10-24 (operator ran `ratify_sec_art_post_b_20261023.sh --apply`, signer Daniele): all four `template_diff_reviewed` entries signed. Root receipt commit `522f7fd33` (13:58:53Z; `artifacts/operator/ratify_sec_art_post_b_20261023.json`, `artifacts/operator/receipts/RATIFY-SEC-ART-POST-B-20261023.json`); research `5baae2367f88` carries the signed lines. SEC-ART-POST-b.1 (v2 template roll-out) stays open for the next stack change.
- [x] **SEC-ART-POST-c — Lineup coverage of template pins.** Run `backfill_template_pins.py` (header-only read) for the remaining launched-GGUF roles, apply with `apply_registry_integrity_pins.py --template-plan`, then flip `template_pins_strict` via stack-change. Closes the SEC-ART-4/5 coverage gap.
  - ✅ 2026-10-22 — coverage met. All 4 lineup roles (frontdoor, architect_general, architect_critic, worker_vision) already carried 64-hex `served_template_sha256` pins, re-verified against today's bytes. Research `c4017b4f4` adds served-only pins for the two non-lineup roles with a GGUF on disk (`reap_25b`, `document_formalizer`). `qwen25_coder_32b_q4km` and `architect_coding` have no GGUF on disk. The `template_pins_strict` flip moves to SEC-ART-POST-f: the pins do not reach the launcher yet.
- [ ] **SEC-ART-POST-d — Live launch proof.** On the next real role launch after `pins_strict` is on, capture the launcher banner showing pin verified (GGUF fingerprint + served-template digest) and one refusal on a touched copy outside production (fixture or scratch copy, never the served file).
- [x] **SEC-ART-POST-e — Publish templates to the content-addressed store and re-point the registry (stack-change, operator signature).** `python -m src.registry.template_store publish` for the override files, `verify`, point `server_mode.<role>.chat_template_file` at the `sha256/<64hex>.jinja` path; optional root-owner + `chattr +i` is an operator decision.
  - ✅ 2026-10-22 (operator decision (c)): published `/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja` (0444, dir 0555; `verify`: 1 entry, 0 problems); original override file left in place; research main `95f90f04f` re-points frontdoor + architect_critic. Recompile is SEC-ART-POST-f.
  - 2026-10-22: re-point prepared on research branch `f8/sec-art-post-e` @ `929a5d667` (frontdoor + architect_critic `chat_template_file` → store path). NOT landed: the store must hold the file first. Order: (1) `python -m src.registry.template_store publish /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja` (expected digest `1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551`), (2) land the re-point, (3) recompile (SEC-ART-POST-f).
- [ ] **SEC-ART-POST-f — Recompile the orchestrator lean registry + stack_priors from the master registry (stack-change step) so sha256 / template pins reach the launcher; only then consider pins_strict / template_pins_strict.** Found 2026-10-22: the lean registry and `stack_priors` carry no sha256 or template pins, so master-registry pins are not enforced at launch until this recompile.
- [x] **SEC-ART-POST-g — Operator decision: root-own the template store and `chattr +i` its files?** (filed 2026-10-22 by the night wrap-up; named as remaining in the SEC-ART-6 and SEC-ART-POST-e notes but never filed.) The store `/mnt/raid0/llm/models/chat-templates/sha256/` is 0444 files in a 0555 dir, still owned by the agent uid, so any session can chmod it back and rewrite a template. Options: (a) root-own the dir and `chattr +i` each published file (operator runs it with sudo; every later `template_store publish` then needs the operator too); (b) keep same-uid ownership and rely on the launch-time digest check once SEC-ART-POST-f and `template_pins_strict` are on. Recommendation: (b) now and (a) after POST-f lands. With pins enforced at launch, the immutable bit is defense in depth, and it would add an operator step to every publish before the launcher even reads the pins. Tick when the operator records a choice here.
  - ✅ 2026-10-23 15:05Z — DECIDED (operator): option (b), same-uid ownership plus the launch-time digest pins once SEC-ART-POST-f lands. No `chattr`, no root-owning the store. Until POST-f lands the only protection is the 0444 files / 0555 dir modes, which is adequate under the honest-author threat model and not a defense against a hostile same-uid process. Option (a) stays available as defense in depth later if the threat model changes.

#### Monitors (trigger prose, no checkbox)

- Trigger (no checkbox): a public implementation of the arXiv 2602.03085 backdoor scanner appears (linked from the paper or Microsoft AIRT), or a community fine-tune enters a SEC-ART-3 review for a tool-bearing role. Then file a bounded probe: scanner steps 1-2 on that artifact plus one clean lineup GGUF of the same family, wall time and motif clusters recorded, advisory only, never an admission gate (intake-2209#record).

#### Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-2191#record | ProjectDiscovery: QLoRA trigger-phrase backdoor in an open tool-calling model | high | adopt_patterns | dive-verified |
| intake-2200 | Inference-time backdoors via chat templates | high | new_opportunity | dive-verified |
| intake-2197 | Community relay of GSQ-RCO quants plus a refusal-direction sidecar | medium | worth_investigating | dive-verified |
| intake-2208 | ProjectDiscovery: leaked write tokens and the model supply chain | high | adopt_patterns | dive-verified |
| intake-2209 | Trigger in the Haystack: backdoor-trigger extraction scanner | medium | worth_investigating | dive-verified |

#### Open Questions

- ~~Which uploaders count as allowlisted re-quantizers for SEC-ART-3?~~ Answered 2026-10-21 (operator): `unsloth` and `lmstudio-community`.
- Full re-hash cost at registration for the largest lineup GGUFs (SEC-ART-2 measures it once; launch uses a stat fingerprint).

#### Notes

- Prompt-level defences and rendered-sentinel hashes are not template-backdoor protection (intake-2200#record); the defence is hashing the template bytes that will be served.
- The 2602.03085 scanner is advisory at most (no code release; untested on GGUF, MoE, tool-call targets or >14B).

#### SEC-ART-4 design (design only; no code landed)

**Gap.** `served_template_sha256_12` is read only by `scripts/validate/reasoning_effort_certifications.py`
(`_bound_template_sha`, which truncates any sha to 12 hex). `orchestrator_stack.py:_append_runtime_serving_flags`
only checks that a `chat_template_file` path EXISTS before emitting `--chat-template-file`; nothing compares bytes,
and a role with no `chat_template_file` silently serves the GGUF-embedded `tokenizer.chat_template`.

**Registry field.** `roles.<role>.chat_template.served_template_sha256` = 64 lowercase hex (sha256 of the exact
effective template bytes). The existing `served_template_sha256_12` stays and must equal its first 12 chars
(validator error otherwise), so the certification reader keeps working unchanged. Compiled through
`registry_compiler.compile_lean` as-is (roles pass through); `registry_validator.py` gains
`_check_template_pins(registry, strict)`: shape check always an error, missing is WARN until the lineup is
backfilled, then flipped by `REGISTRY_TEMPLATE_PINS_STRICT=1` (same switch design as SEC-ART-1).

**New module `src/registry/template_pin.py`** (pure, no llama-server import):
- `read_gguf_chat_template(gguf_path) -> bytes | None` - reads ONLY the GGUF header metadata (magic, version,
  n_tensors, n_kv, then the KV records; stop at key `tokenizer.chat_template`, type STRING = 8; length-prefixed
  uint64 + raw bytes). Never touches tensor data, so it is a few KB of I/O even on a 40 GB file. Returns None if
  the key is absent. Handles GGUF v2/v3 only; any other version raises `TemplatePinError`.
- `effective_template_bytes(chat_template_file: str | None, gguf_path: str) -> tuple[bytes, str]` - mirrors
  llama-server precedence: `--chat-template-file` bytes if the flag is emitted, else the GGUF template. The second
  value is the source label (`file:<path>` / `gguf:<path>`). A command carrying `--chat-template` (inline) is
  refused outright (cannot be pinned by path; the launcher never emits it today).
- `template_sha256(data: bytes) -> str` (64 hex), `check_template_pin(role, effective, pinned) -> None` raising
  `TemplatePinError(role, source, expected, actual)`; the message carries both full digests and the source path.

**Launcher wiring.** In `scripts/server/orchestrator_stack.py` add `_verify_served_template(role_name, cmd, flags)`
and call it from `build_server_command` after the per-mode builder returns `cmd` (so it sees the FINAL argv, not
the registry's intent) and before `start_server` reaches either `subprocess.Popen` (lines ~1907/1980). It parses
`--chat-template-file` and `-m/--model` out of `cmd`, calls `effective_template_bytes`, and compares with the
role's pin from `_stack_prior_launch(role_name)` (extend that tuple's `flags` with `served_template_sha256`).
On mismatch it raises `TemplatePinError`; `start_server` converts it to the same refuse-and-return-None path the
missing-path ValueError takes, prints `REFUSED <role>: template sha256 <actual> != pinned <expected> (<source>)`
and writes a `kind: template_pin_refusal` line to the stack-change ledger. Embedders and aux services without a
chat template (`embedding_mode`) skip the check; a role with a template-bearing model and NO pin is a WARN in
non-strict mode and a refusal under `REGISTRY_TEMPLATE_PINS_STRICT=1`. The check also runs in `cmd_start`'s
validate-only path (`stack_commands.cmd_start` -> `validate_or_raise` neighbourhood) so `--validate-only`
reports pin failures without starting anything. No `--jinja` flag handling changes.

**TOCTOU.** The hash is of bytes read by the launcher, llama-server re-reads the file microseconds later. For
file templates, close the window by launching with a content-addressed copy: SEC-ART-6 serves overrides from
`.../chat-templates/sha256/<64hex>.jinja` (read-only), so the path itself names the pinned digest and the launch
check becomes a belt-and-braces recheck. Until SEC-ART-6, the launcher re-hashes after `Popen` has logged the
banner (cheap) and `stack_log_banner.write_launch_banner` records the digest so a post-launch swap is visible.

**Test plan** (foreground, orchestrator venv, fixtures only, no server):
1. `tests/unit/test_template_pin.py`: build a minimal GGUF in `tmp_path` (struct-packed header, two KVs, one with
   `tokenizer.chat_template`, zero tensors) - assert `read_gguf_chat_template` returns the exact bytes; a GGUF
   without the key returns None; a truncated header and a v1 magic raise `TemplatePinError`; a 1 GiB sparse file
   with the same header proves no full-file read (assert `os.read` total < 1 MB via monkeypatched open).
2. File precedence: `effective_template_bytes(file, gguf)` returns the file bytes and `file:` label; with
   `None` returns the GGUF bytes and `gguf:` label.
3. One-byte mutation: copy the template, flip one byte -> `check_template_pin` raises with both digests; the
   unmodified copy passes. Same for the GGUF-embedded path (mutate one byte inside the KV value).
4. `tests/unit/test_orchestrator_stack_template_pin.py`: with `subprocess.Popen` patched to raise if reached,
   `start_server` on a registry fixture whose pin mismatches returns None/raises and Popen is NEVER called;
   matching pin reaches Popen. Inline `--chat-template` argv is refused.
5. Validator: 64-hex shape errors, 12-char prefix consistency error, WARN-vs-strict switch (mirrors
   `tests/unit/test_registry_artifact_pins.py`).
6. Live-registry backfill check (read-only): for each lineup role with `chat_template_file`, the hash of the
   file equals the existing `served_template_sha256_12` prefix (expected `1443ea9ab4bb` for the terse template,
   25808 bytes); roles that use a GGUF-embedded template are listed for the header-read backfill.

## Track: model-exec-containment
<!-- gate: none -->

> Folded from `handoffs/active/model-exec-containment.md` @ `05e2b812a086` on 2026-11-02 (BRF-T1-F4, route 1a, operator D1/D5; retired row UFH-16 → RTG-36). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Model-exec containment — what an open-weight model's tool calls can reach

**Status**: stub
**Created**: 2026-10-21 (via research intake, operator-approved 2026-10-21 plan intake-backdoor-cvec-20261020)
**Scratch**: `/mnt/raid0/llm/tmp/model-exec-containment/`
**Categories**: agent_architecture, tool_implementation, local_inference
**Related**: [model-artifact-integrity.md](stack-lifecycle-program.md#track-model-artifact-integrity) (artifact side) · [qwen-chat-template-evaluation.md](harness-program.md#track-qwen-chat-template-evaluation) (CT-12: special-token injection, the input-side sibling — not duplicated here) · [agentic-serving-harness-fixes.md](harness-program.md#track-agentic-serving-harness-fixes) (UFH14-A6: Landlock for harness experiments, not production) · [repl-session-memory-maturity.md](memory-program.md#track-repl-session-memory-maturity) (D-RI-CONTAIN: the opt-in contained CPython lane for REPL *cells*, no network/secrets; this handoff owns the tool-subprocess path, credential reach and the audit log, and its env/no-network helpers are offered to D-RI-CONTAIN rather than built twice)

#### Objective

Assume any open-weight model we serve may carry a trigger-conditioned backdoor that rewrites a tool call
(intake-2191#record demonstrates it for a QLoRA-poisoned tool-calling model; intake-2199#record shows
the class survives clean fine-tuning and evades guardrail screening). Contain what a model-issued
command can reach — environment secrets, credential files, the network — and keep a durable record of
every call, so that a backdoor that fires has nothing to steal and leaves a trace.

#### Current state (verified 2026-10-21, orchestrator @ 50f7ffbd)

- `run_shell` allowlists `python`/`python3` (external_access.py:128-152), so its curl/wget block does
  not stop network access; `find`/`awk`/`sed` exec forms are refused only under a task_root scope.
- `run_shell` and `run_python_code` children inherit the full API environment, fenced or not
  (knowledge_fence.py:733/765 build the fenced env from `os.environ`).
- No egress control on any model-exec path; the eval Landlock fence is filesystem-only and eval-only.
- Tool-call logging is the in-memory ExplorationLog; refused, timed-out and errored calls are not recorded.
- The API sets `HF_HOME` to the shared cache (orchestrator_stack.py:2466), which holds an HF token file;
  same-uid credential files (git, gh, agent CLIs) are readable by children.
- Already in place and kept: credential redaction of REPL output before it reaches model context; the
  CT-12.3a control-token neutraliser (input side).
- Already planned elsewhere: D-RI-CONTAIN (repl-session-memory-maturity.md) contains REPL cell execution in an
  opt-in killable child with no network/secrets; it does not cover the run_shell/run_python_code subprocesses,
  the default production path, credential files or tool-call logging.

#### Tasks

- [x] **SEC-EXEC-1 — Minimal allowlisted env for model-exec children.** One helper builds the child env (PATH, LANG, TMPDIR and fence variables only) for run_shell and run_python_code, fenced and unfenced: today both pass the full parent environment (external_access.py:227/323/332 and knowledge_fence.py:733/765 @ 50f7ffbd); a unit test plants a fake API key and HF_HOME in the parent and proves both are absent in the child (intake-2191#07). ✅ 2026-10-21 — epyc-orchestrator 644c6530 + 65fbdce3: `child_env` allowlist (PATH, LANG*, LC_*, TZ, TMPDIR/TEMP/TMP, PYTHONIOENCODING/UTF8 + explicit fence vars) in `exec_containment.py`, fenced and unfenced; HOME = per-task scratch dir (+XDG cache/config under it), real home never the child HOME; PYTHONPATH/VIRTUAL_ENV not needed (python3 resolved via PATH, nothing in src relies on them); tests in `test_sec_exec_containment.py`.
- [x] **SEC-EXEC-2 — Close the interpreter hole in run_shell.** Drop python/python3 from the run_shell allowlist (external_access.py:128-152 @ 50f7ffbd; run_python_code is the sanctioned Python path) and apply the task_root command-execution refusals (find/awk/sed exec forms, task_root.py:285-337) unscoped in production; one test per refusal plus a test that `python3 -c` through run_shell is refused. ✅ 2026-10-21 — same commits: python/python3 dropped from the run_shell allowlist; `task_root.check_shell_exec` applies the find/awk/sed exec-form refusals unscoped ("EXEC CONTAINMENT"); one test per refusal plus `python3 -c` via run_shell.
- [x] **SEC-EXEC-3 — No network for model-exec children.** Probe host support first (unprivileged network namespace or Landlock network rules), then run run_shell and run_python_code children without network; web_fetch stays the only network tool and gains a private-range and link-local deny; tests show a child connect() fails while web_fetch to a public URL works (deny-by-default, because a trusted-domain allowlist can host the payload: intake-2191#07).
  - Probe 2026-10-21 (agent sandbox, user node, kernel 6.14.0-37): `unshare -rn true` fails EPERM (uid_map write; AppArmor userns restriction likely) so no netns; Landlock ABI 6, so Landlock net rules (TCP bind/connect only) are available. Re-probe as the actual service user before choosing. Still OPEN: the child no-network enforcement and the web_fetch private-range/link-local deny (web_fetch currently has none; only audit logging was added).
  - ✅ 2026-10-22 (landed, flag-gated, DEFAULT OFF) — orchestrator `bbc74d5c` (origin/main, 8 commits on `d0e0e477`): `fe0244af` Landlock (ABI 6, TCP connect/bind deny) + seccomp shim for run_shell/run_python_code children (`exec_sandbox.py`, `_fence_kernel_shim.py`; refuses visibly when the host cannot enforce, never runs the command unrestricted), `e29ebadf` `web_guard.py` private-range/link-local deny for web_fetch/fetch_docs (redirect, DNS-rebinding, non-canonical-IP safe), flags in `bdb9b858` (`exec_containment`, `web_fetch_guard`). Tests: `test_sec_exec3_5_sandbox.py::test_child_has_no_network_but_the_control_does`, `test_sec_exec3_web_guard.py`. Acceptance (tests: child connect() fails, public web_fetch works) is met by the code; it is NOT in force until the flags are turned on (task SEC-EXEC-POST-e below).
- [x] **SEC-EXEC-4 — Durable tool-call audit log.** Append-only rotated JSONL with one record per run_shell / run_python_code / web_fetch call INCLUDING refused, timed-out and errored calls (tool, argv or code text plus sha256, cwd, exit, duration, refusal reason, role, request id); today ExplorationLog is in-memory and run_shell records only successful calls; a test shows a refused call is recorded. ✅ 2026-10-21 — same commits: `<log_dir>/tool_call_audit.jsonl` (override ORCHESTRATOR_TOOL_AUDIT_LOG), RotatingFileHandler 20MB x 10, one redacted record per run_shell / run_python_code / web_fetch call incl. refused, timed-out and errored; refused-call test passes. Gate: 10 REPL/fence/task_root suites 367 passed, 1 skipped.
- [x] **SEC-EXEC-5 — No credential-file reach from model-exec children.** Children run under a separate uid or a production Landlock read-deny covering $HF_HOME/token, $HF_HOME/stored_tokens, ~/.git-credentials, ~/.config/gh and the agent-CLI auth directories, and get a token-free HF_HOME (the API sets HF_HOME to the shared cache at orchestrator_stack.py:2466 @ 50f7ffbd); a test shows open() of each path fails in a child while ordinary tool calls work (intake-2208#record).
  - ✅ 2026-10-22 (landed, flag-gated, DEFAULT OFF) — `fe0244af`: production Landlock read-deny over the credential path set ($HF_HOME token files, ~/.git-credentials, ~/.config/gh, agent-CLI auth dirs; operator extra-deny honoured; rules deny paths that do not exist yet) plus token-free HF_HOME for contained children (`test_child_env_has_a_token_free_hf_home_only_when_contained`); `1b971951` /proc environ bypass test. Tests: `test_credential_files_are_unreadable_to_the_child_and_ordinary_files_are_not`, `test_credential_path_set_covers_the_handoff_list`. In force only once `exec_containment` is on (SEC-EXEC-POST-e).
- [x] **SEC-EXEC-6 — HF token hygiene (operator decision package).** Options: (a) revoke the token under /mnt/raid0/llm/cache/huggingface if no gated-model pull needs it; (b) keep a read-only fine-grained token, mode 0600, in a path only the download wrapper reads (recommended if gated pulls exist). Then chmod, give the nextplaid containers a token-free cache mount, and record the decision; token values are never printed.
  - *(2026-10-21, operator.)* Decided option (a): revoke and delete. The local token files are deleted by the owning session; the revoke on huggingface.co can only be done by the operator.
  - *(2026-10-22, status.)* Code side landed: `1b971951` points nextplaid-code/docs at `{cache_dir}/huggingface/hub` only (`orchestration/launch_manifest.yaml`, token files no longer visible to the containers) and adds an HF-token-reappearance warning. LEFT OPEN: the running containers still hold the old root mount until recreated (SEC-EXEC-POST-c); tick this box after the recreate is verified.
  - [x] **DECLINED by operator (2026-10-22):** revoke HF token on huggingface.co. Closed as declined via AskUserQuestion: the token lived only on this host, was never committed, and both local files (`token`, `stored_tokens`) were deleted 2026-10-21; nothing depends on the revoke. Residual risk accepted: a host process could have copied it while `stored_tokens` was 0664. ✅ 2026-10-22
  - ✅ 2026-10-22 — acceptance met: token files deleted (2026-10-21), option (a) decided, nextplaid containers recreated with the token-free `huggingface/hub`-only mount and verified with `docker inspect` (SEC-EXEC-POST-c).
- [x] **SEC-EXEC-7 — First-seen destination and out-of-root write flags.** Depends on SEC-EXEC-4: each audit record carries first_seen_host and write_outside_root booleans, and a zero-token daily summary lists flagged calls for review.
  - ✅ 2026-10-22 (landed, flag `exec_write_flags` DEFAULT OFF) — `bdb9b858` + `fe0244af`: `write_audit.py` adds `first_seen_host` / `write_outside_root` to each audit record, `scripts/security/tool_audit_summary.py` is the zero-token daily summary; tests `test_sec_exec7_audit_flags.py`. Live proof of the new fields on a real API process is still owed (SEC-EXEC-POST-d).
- [x] **SEC-SECRETS-1 — HF and W&B key patterns plus a name-only history scan.** Add hf_ and W&B key patterns with fixtures to scripts/hooks/pii_precommit.sh, install the hook in epyc-web, run a one-off history scan of the epyc-* repos that reports path and commit only (never the value), record the result and rotate anything found (intake-2208#07).
  - *(2026-10-21, operator.)* D9 ack approved: commit with trailer `D9-ack: operator 2026-10-21 (SEC-SECRETS-1 hook patterns)` after its tests pass.
  - ✅ 2026-10-22 — patterns: root `a7bfde22d` (hf_/W&B in `scripts/hooks/pii_precommit.sh`, fixtures `research/fixtures/pii_secret_tokens_hf_wandb.jsonl`; D9-ack 2026-10-21); epyc-web in the hook installer (operator ack 2026-10-22; `install_git_hooks.sh` run, all repos ok); scan tool `scripts/audit/secret_history_scan.py` (`3508bd4aa`, name-only by construction, test proves the planted value is absent from all output). History scan run 2026-10-22 over every ref of epyc-root, epyc-orchestrator, epyc-inference-research, epyc-web, HF + W&B families, `nice -n 19`, read-only: real findings 0 / 0 / 0 / 0 (commits scanned 8430 / 3990 / 6299 / 9). Only hits: 10 allowlisted, all in the documented fake-token fixture `research/fixtures/pii_secret_tokens_hf_wandb.jsonl` (root commits `d008394c5`, `3508bd4aa`). Nothing to rotate; nothing rewritten. Re-run when the pattern set widens (`--all-families` is the broad, noisy mode and was not run).

#### Post-landing steps (2026-10-22, workspace-f8)

- [x] **SEC-EXEC-POST-c — Recreate the nextplaid-code and nextplaid-docs containers (owning session runs this; NOT run by f8).** The manifest now mounts only `{cache_dir}/huggingface/hub`; the running containers still hold the old cache-root mount (token files already deleted 2026-10-21, but the mount shape must change so a token reappearing is not exposed). `start_docker_container` does `docker rm -f <name>` then `docker run` from `orchestration/launch_manifest.yaml`, and the aux reload path kills listeners on the port first. Command, one container at a time, from `/workspace/repos/epyc-orchestrator`: `python3 scripts/server/orchestrator_stack.py reload nextplaid-code`, wait for health on :8088 (`/health`), then `python3 scripts/server/orchestrator_stack.py reload nextplaid-docs`, wait for :8089. Prove: `docker inspect nextplaid-code nextplaid-docs --format '{{.Name}} {{range .Mounts}}{{.Source}} {{end}}'` shows only `.../huggingface/hub`, and a code/docs search still returns results. (Retrieval briefly unavailable per container; do not do it mid-eval.) Then tick SEC-EXEC-6.
  - ✅ 2026-10-22 (main session, ~21:33Z, operator decision (b)) — recreated ONLY the two containers, one at a time: `orchestrator_stack.py reload nextplaid-code` then `nextplaid-docs`; both healthy, models loaded, docs index served; mounts now `{cache_dir}/huggingface/hub -> /root/.cache/huggingface/hub`, verified with `docker inspect`; shared orch clone fast-forwarded to `074e9148` first.
- [ ] **SEC-EXEC-POST-d — Live proofs after the operator's API reload** (`orchestrator_stack.py reload orchestrator` only; never the whole stack, autopilot stays up). With the new code live and flags still off, then each flag on a canary: (1) a fresh `tool_call_audit.jsonl` record carries `first_seen_host` and `write_outside_root` (needs `exec_write_flags` on); (2) a `fetch_docs` call appears in the audit log (SEC-EXEC-4 covers web_fetch; confirm fetch_docs specifically); (3) the `seen_hosts` file is created and a repeat host is not flagged first-seen; (4) `scripts/security/tool_audit_summary.py` renders the flagged calls. Record file names and counts only, never call arguments.
  - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up.)* The operator's API-only reload happened at 14:59:25Z (pid 3932317, orchestrator main `f3ab78b2`), so proofs (1)-(4) can run now. Proof (1) waits on a post-reload tool call.
  - *(2026-10-24 08:50Z, workspace-f8 sweep; read-only.)* **Still waiting on a post-reload tool call, and the production model stack is down.**
    - Nothing is listening on :8070/:8080/:8083.
    - The API was restarted again at 16:19:44Z 10-23 (pid 3663075, orch main `fd1a8941`). Its env carries `EXEC_WRITE_FLAGS=1`, `WEB_FETCH_GUARD=0` and `EXEC_CONTAINMENT=0`. Since then it has served only `/health`.
    - `logs/tool_call_audit.jsonl` has 6 records, all written before the reload, with `write_outside_root` null. No `seen_hosts` file exists.
    - Proof (4)'s script runs on that log (`tool_audit_summary.py --since-hours 1000`: 6 run_shell, 2 ok, 4 refused, 0 first-seen hosts), but there are no flagged calls to render yet.
    - Trigger: the production stack serving plus the first tool-calling request through the API. Proofs (1)-(4) then take one read-only pass.
- [x] **SEC-EXEC-POST-e — Decision package: turn on `exec_containment` and `web_fetch_guard`?** Operator decision (see the package below); `exec_write_flags` is observe-only and can precede both. Recommendation and tradeoffs are in the package; nothing is enabled by f8.
  - ✅ 2026-10-22 DECIDED (operator, AskUserQuestion): Option A, staged. Order: `exec_write_flags`, then `web_fetch_guard`, then `exec_containment`; each step = one API reload (operator runs it manually) + live proof.
  - [ ] **SEC-EXEC-POST-e1 — Step 1: `exec_write_flags` ON.** Orch branch `f8/exec-guards-step1` @ `a73af3cc` (one line in `PRODUCTION_FEATURE_WAVE_OVERRIDES`, `scripts/server/orchestrator_stack.py`); land to orch main, then apply at the operator's API reload + live proof (`write_outside_root` in `tool_call_audit.jsonl`).
    - *(2026-10-22, f8.)* Landed on orchestrator main `a73af3cc` (staged by the operator). It goes live at the operator's next API reload (`orchestrator_stack.py reload orchestrator` only). Not ticked: the live proof (`write_outside_root` in `tool_call_audit.jsonl`) is still owed.
    - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up; read-only.)* **Applied.** The 14:59:25Z API-only reload (pid 3932317) runs `a73af3cc`. Its environment carries `ORCHESTRATOR_FEATURE_EXEC_WRITE_FLAGS=1`, with `WEB_FETCH_GUARD=0` and `EXEC_CONTAINMENT=0`. The live proof is still owed: `logs/tool_call_audit.jsonl` holds 6 records, all written before the reload, each with `write_outside_root` null. Tick on the first post-reload record that carries the field.
  - [ ] **SEC-EXEC-POST-e2 — Step 2: `web_fetch_guard` ON.** Same one-line override, apply at the operator's next API reload + live proof (private/link-local/metadata fetch refused, public fetch OK).
  - [ ] **SEC-EXEC-POST-e3 — Step 3: `exec_containment` ON.** Same one-line override, apply at the operator's next API reload + live proof (child has no network, scratch HOME, credential read denied); run the REPL/tool suites on the canary first.
    - *(2026-10-24, workspace-f8 sweep.)* The flag is still applied on the current API pid 3663075 (restarted 16:19:44Z 10-23). The live proof waits on the same trigger as SEC-EXEC-POST-d: no post-reload tool call has happened, because the stack is down.

##### SEC-EXEC-POST-e decision package

- Question: enable `exec_containment` (Landlock+seccomp child sandbox: no network, credential read-deny, token-free HF_HOME) and `web_fetch_guard` (private-range/link-local deny) in production, and when.
- Option A, recommended: enable `exec_write_flags` first (observe only), then `web_fetch_guard` (narrow: blocks only private/link-local/non-canonical destinations), then `exec_containment`, each after one API reload and one live-proof pass (POST-d), spaced so a regression is attributable. Tradeoff: slower, three reloads; each step reversible by flag.
- Option B: enable all three in one reload after POST-c and POST-d. Faster; a failure cannot be attributed to a single flag. `exec_containment` refuses visibly when the host cannot enforce, so a bad host shows as refused tool calls, not silent exposure.
- Option C: leave all off until a model with tool access that is community-origin enters a SEC-ART-3 review. Zero risk of tool regressions; leaves the documented backdoor-reach gap open on the default path, against the handoff objective.
- Known cost to weigh: contained children lose network (an `exec` that pip-installs or curls will fail), and `HOME` is a per-task scratch dir (SEC-EXEC-1). Verify the REPL/tool suites on the canary before the broad flip.

#### Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-2191#record | ProjectDiscovery: QLoRA trigger-phrase backdoor in an open tool-calling model | high | adopt_patterns | dive-verified |
| intake-2199#record | Malice in Agentland: backdoors in the AI agent supply chain | high | adopt_patterns | dive-verified |
| intake-2208 | ProjectDiscovery: pwning AI labs through employees' leaked tokens | high | adopt_patterns | dive-verified |
| intake-2210 | Poisoning attacks need a near-constant number of samples | medium | worth_investigating | dive-verified |

#### Open Questions

- Does the host kernel allow unprivileged network namespaces or Landlock network rules for the service user (SEC-EXEC-3 probes this first)?
- Separate uid or Landlock read-deny for credential paths (SEC-EXEC-5): which composes better with the existing eval fence?

#### Notes

- Egress denial alone is not enough: a network-restricted backdoored agent can switch to local destructive actions (intake-2199#record), so SEC-EXEC-2 and SEC-EXEC-4 stay in scope alongside SEC-EXEC-3.
- Do not adopt guardrail models or weight-diff monitors as the backdoor defence for tool-bearing roles; they failed in intake-2199#record.

## Track: model-stack-single-source-update-pipeline
<!-- gate: none -->

> Folded from `handoffs/active/model-stack-single-source-update-pipeline.md` @ `05e2b812a086` on 2026-11-02 (BRF-T1-F4, route 1a, operator D1/D5; retired row RTG-19 → RTG-36). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Model Stack Single-Source Update Pipeline

**Status**: ACTIVE — the single-source contract, runtime attestation, launch/AutoPilot/benchmark gates and swap-CI are live (history: § Completed Scope). Open work is the 2026-09-22 cutover follow-ups (SSU-F*) below; the seven boxes in § Outstanding Work are standing rules, never tasks. SSU-F17 waits on UFH-13's verdict.
**Created**: 2026-06-13
**Priority**: HIGH - stale model-specific quantities can silently corrupt
routing, scoring, launch, planner prompts, replay analysis, and operator docs
after a stack change.
**History**:
[model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md)
and
[model-stack-single-source-update-pipeline-history-through-2026-06-19.md](../archived/model-stack-single-source-update-pipeline-history-through-2026-06-19.md)
preserve completed chronology compacted out of this active handoff.
**Related**:
[standardized-stack-update-pipeline-finalization.md](stack-lifecycle-program.md#track-standardized-stack-update-pipeline-finalization),
[model-stack-update-pipeline-audit.md](stack-lifecycle-program.md#track-model-stack-update-pipeline-audit),
[model-stack-change-standardization-audit.md](../completed/model-stack-change-standardization-audit.md),
[stack-change-governance-pipeline.md](stack-lifecycle-program.md),
[model-capability-descriptors.md](routing-program.md#track-model-capability-descriptors)

#### Start here

- **Next:** SSU-F8 remains with its owning session for confirmation.
- **Waiting:** SSU-F17 on UFH-13's verdict; the SSU-F1 weight deletion on the operator (its deprecation half can be
  done now); SSU-F16 on an inference window.
- SSU-F4 and SSU-F11 overlap SSU-F17.
- Also open: SSU-F8 (mostly landed in orch `b14ed228`; the owner confirms and ticks), and SSU-F10 under
  § Validation.
- The seven open boxes in § Outstanding Work are standing rules. Never dispatch or tick them.

#### Objective

Make orchestration-stack changes reliable by ensuring model-specific facts are
updated once, then projected everywhere:

1. edit structured truth;
2. compile generated contracts;
3. validate all consumers and docs;
4. refuse launch, AutoPilot resume, or benchmark interpretation when generated
   truth and live/runtime facts disagree.

The concrete trigger remains the stale-quantity class of bug: shared models,
retired roles, HOT/WARM status, memory footprints, context windows, launch
ports, q_scorer costs, and prompt/operator labels must not be duplicated in
unowned local constants.

#### Current Baseline

- Generated model descriptors plus `orchestration/derived/stack_priors.yaml` are the source contract for live model,
  role, serving, launch, quality and memory facts. Consumers keep generated priors primary, with explicitly owned
  degraded fallbacks.
- Live checks: descriptor/stack-prior freshness, stack-manifest registry drift, q_scorer provenance, runtime
  attestation, production launch, AutoPilot preflight, direct benchmark preflight, the DS-7 template/prior parity
  guard, the launch-manifest serving-alignment validator, and (since 2026-09-23) the derived-surface checks in
  `scripts/validate/check_shared_with_derivations.py`.
- The surface manifest `orchestration/stack_change_surface_manifest.yaml` owns the hardcoded-surface inventory:
  `consumer_surface_count=13`, `rule_count=27`.
- Do not churn these re-audited surfaces unless a concrete duplicated fact reappears: `scripts.autopilot.preflight_audit`,
  `config_model_catalog` (`ServerURLsConfig` / `TimeoutsConfig` / `LLMConfig`) and the `src.config.models`
  compatibility aliases.
- X-MAS v2 (`incumbent_constrained_cheapfirst_v2`) is `promote_candidate` from the 2026-07-03 quiet-window A/B;
  production enforce stays default-off until an operator enablement decision.
- New migration work starts only from a concrete new duplicated model/role/port fact, or from a newly migrated
  consumer that deserves swap-CI coverage. The detailed baseline chronology is in the [completed sibling](../completed/model-stack-single-source-update-pipeline-completed-through-2026-09-27.md).

#### Completed Scope

| Through | Historical ledger |
|---------|-------------------|
| 2026-06-15 | [model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md) |
| 2026-06-19 | [model-stack-single-source-update-pipeline-history-through-2026-06-19.md](../archived/model-stack-single-source-update-pipeline-history-through-2026-06-19.md) |
| 2026-09-27 | [model-stack-single-source-update-pipeline-completed-through-2026-09-27.md](../completed/model-stack-single-source-update-pipeline-completed-through-2026-09-27.md): superseded status line, detailed Current Baseline snapshot, SSU-F2/F3/F5/F9a/F9b/F9d/F9e/F12/F14/F15 and the F2/F5/F9 outcome sections |

#### Required Contract

Any future stack update should be accepted only when these hold:

- generated descriptors, stack priors, procedure enums, and operator summaries
  are fresh;
- model-specific consumer surfaces are either generated from stack priors or
  explicitly owned degraded fallbacks;
- q_scorer/reward/routing/admission/launch/status/prompt consumers do not hide
  stale local model facts;
- live runtime flags, model paths, mmproj paths, context/KV/spec flags, and
  known-stack listeners agree with generated launch truth;
- scanner rules and consumer surfaces have manifest ownership metadata.

#### Outstanding Work

> **⚠ THESE SEVEN BOXES ARE STANDING CONSTRAINTS, NOT TASKS — DO NOT DISPATCH OR FLIP THEM.**
> Every open box in this section is a rule with no completion state: *"Preserve … **whenever**
> migrating"*, *"Continue … **only where**"*, *"Treat … **as** re-audited surfaces … **do not churn
> unless**"*, *"Keep production routing default-off **until** an explicit operator decision"*,
> *"Keep … **under review**"*, *"Keep completed logs out of active indices"*, *"Broaden …
> **opportunistically as** consumers create new surfaces"*. Checking one asserts that an ongoing
> constraint has been permanently satisfied, after which the constraint stops being applied.
>
> **Count corrected SIX → SEVEN, 2026-08-11 (`mainC`).** The *"Treat … as re-audited surfaces"* rule
> was a standing constraint the enumeration never counted, and it had been flipped `[x]` — the exact
> false-permit C41 predicts, *"a guard that trusts an enumeration is passed by not being
> enumerated."* The banner is the scope, so an undercount silently un-guards a real rule; the repair
> belongs here rather than in a widened predicate.
>
> Noted 2026-07-29 by `auditor`. **The heading gives no warning** — "Outstanding Work" reads like a
> task list, and three of these rows (`:320`, and the two now at `:353`/`:355`) are offered as
> dispatchable in `BACKLOG-DISPATCH-QUEUE.md`'s runner-up bench. The reliable tell is the BOX TEXT
> — a continuous imperative plus a standing condition — not the section title.

- **[declined: ws58 2026-11-03 content-review: standing rule with no completion state, not a task; stays readable here]** Preserve env override precedence and explicit degraded fallbacks whenever
  migrating config, runtime, benchmark, or prompt consumers.
- **[declined: ws58 2026-11-03 content-review: duplicate of W4 consumer migration (Waypoints), which now carries the queryable-set step]** Continue migrating remaining high-risk P2 consumers only where a concrete
  duplicated model/role/serving fact or duplicated stack-prior traversal still
  exists; avoid broad renderer rewrites unless there is a narrow helper seam.
- [x] Re-audit `scripts.benchmark.seeding_rewards`, `scripts.benchmark.corpus_quality_gate`
  and `scripts.autopilot.kv_compress` for duplicated live facts ✅ 2026-07-29 — each imports
  generated stack-prior helpers for normal operation; each fallback remains explicitly marked
  degraded and derives from the manifest rather than copied live model/endpoint facts.
- **[declined: ws58 2026-11-03 content-review: standing constraint with no completion state (its own text says so); stays readable here]** **STANDING — do not churn `seeding_rewards`, `corpus_quality_gate` or `kv_compress`**
  unless a concrete duplicated live fact reappears. They are re-audited surfaces that keep
  generated stack priors primary with an explicit degraded fallback.
  *(SPLIT 2026-08-11 by `mainC`, adopting `auditor`'s synthesis over my own first fix. One box
  was carrying two different things: a re-audit that genuinely COMPLETED, and a rule with no
  completion state. I had restored the whole box to `- [ ]`, which hid the finished audit; it had
  previously been `- [x]`, which retired the live rule — the same loss-mode as the consumed GEAK
  pickup box. Splitting is the only form that keeps both true. Consequence for consumers: any
  queue row marking this a CLOSED task is wrong, and the dated result now lives on its own
  checked line where a completion record belongs.)*
- **[declined: ws58 2026-11-03 content-review: merged into the Finish-W4-swap-CI box; "opportunistically" is unbounded]** Broaden W4 swap-CI opportunistically as migrated consumers create new
  witness surfaces; do not add abstract fixture coverage without a migrated
  consumer to prove. Latest re-audits: the simulated vision swap already covers
  the migrated vision serving consumers (`stack_prior_vl_ports`,
  `_vl_port_for_role`, `_vl_url_for_role`, and `_vl_url_for_port`) against the
  generated stack-prior artifact, and the simulated worker swap now covers
  WorkerPool primary-port/model-path consumption plus factual-risk role-tier
  consumption after a generated worker swap. The simulated vision and
  long-context swaps also prove factual-risk role-tier consumption for their
  role classes.
  - 2026-11-01 codex3 bounded expansion: APP `a643cb331b1389eda0b414eb54bdac9bf90fe04b` adds the migrated SSU-F11 recipe readers as an actual witness surface. The temporary master→lean compiler step, stale-check refusal, approved update and in-process recipe/env/thread readers pass in the affected 17/17 suite. [Source-bound proof](https://github.com/pestopoppa/epyc-orchestrator/blob/a643cb331b1389eda0b414eb54bdac9bf90fe04b/artifacts/engineering/w4-recipe-swap-20261101/README.md) retains earlier sparse-input failures and their baseline reproduction. No model/server/full promotion-gate execution. This standing expansion item remains OPEN; no completion tick for this bounded addition. [no-belief: synthetic source conformance only]

- [x] Fix promotion-gate test regressions: `_role_result` fixture missing
  `tool_chains` attribute (orchestrator `91cb03bf`), and stale ingest
  topology fixture expectation (`083e2736`). Full promotion-gate `181 passed`,
  pipeline `summary: ok`. ✅ 2026-07-07
- [x] Deploy/reload the repaired X-MAS constrained policy and rerun the
  held-out quiet-window A/B with required policy
  `incumbent_constrained_cheapfirst_v2`; the 2026-07-03 artifact is
  `promote_candidate` with no blockers.
- **[declined: ws58 2026-11-03 content-review: standing constraint, not a task; the enablement decision is owned by routing-program.md]** Keep production routing default-off until an explicit operator
  enablement/reload/attestation decision accepts the repaired-policy evidence.
- **[declined: ws58 2026-11-03 content-review: bookkeeping with no behaviour change]** Keep `scripts/autopilot/short_term_memory.md` under review as live run
  state; do not prune it during active AutoPilot execution.
- **[declined: ws58 2026-11-03 content-review: bookkeeping with no behaviour change; the wrap-up routine already owns it]** Keep completed implementation logs out of active indices; record future
  closures in `progress/` and compact/archive at wrap-up.

#### Validation

Default no-inference acceptance:

```bash
uv run python scripts/registry/stack_change_pipeline.py check
```

Promotion/launch-boundary acceptance:

```bash
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```

Surface inventory checks:

```bash
uv run python scripts/validate/stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --list-hardcoded-surface-rules --surface-inventory-format json > /tmp/stack-change-inventory.json
```

Moved-lineup regression (from SSU-F5): the pytest plugin `/mnt/raid0/llm/tmp/ssuf5/moved_lineup.py`
relocates the worker lane a second time, onto `architect_critic`. Against `tests/unit/test_stack_priors_compiler.py`
it gives 34 of 35 passing; the one failure is the deliberate pin. It lives only in tmp, beside its fixtures
(`launch_manifest.yaml`, `model_registry.yaml`, `moved/`).

- [x] **SSU-F18 — commit the moved-lineup plugin to the orchestrator tests** before a disk reclaim removes
  `/mnt/raid0/llm/tmp/ssuf5/`. Bring its fixtures with it, run it against `tests/unit/test_stack_priors_compiler.py`,
  and keep the 34/35 result, with the deliberate pin failing, as a standing regression against the next lineup change.
  Zero inference. **Blocker: none.**
  - ✅ 2026-10-28 — reviewed source `833a2f4e870b9c12ffabe7ac1bbc3efa4b594baf` integrated as orchestrator main `bc1cf9780905d65e5088aedcf240d20a9643caa3`, no deployment. Original tmp bytes were lost; committed overlays preserve the documented move. Current 44-case suite: baseline 44 pass, moved 43 pass plus the exact deliberate `startswith("full:")` assertion failure; automatic identity/counter/isolation regression makes combined 45 pass. Historical 34/35 is not asserted for current source. Details and grant-timing disclosure: [periodic checkpoint](../../progress/2026-10/2026-10-28-codex-ni-periodic-wrap.md). [belief: cc]

---

#### Follow-ups from the 2026-09-22 v10 promotion + lineup cutover

The cutover is live and serving; these are what it left owed. Each names its own
blocker rather than sitting in prose.

Closed and moved to the [completed sibling](../completed/model-stack-single-source-update-pipeline-completed-through-2026-09-27.md): SSU-F2, F3, F5, F9a, F9b, F9d, F9e, F12, F14, F15, and the F2/F5/F9 outcome sections. SSU-F9 is ticked below.

- [x] **SSU-F1 — deprecate the seven `*_local` catalogue rows for the retired models, THEN delete ~544 GiB of weights.** ✅ 2026-10-29 (audit: epyc-inference-research 41fd9c498 (2026-09-23): seven *_local rows deprecated:true (verified in model_registry.yaml) AND deletion recorded in deprecated_models graveyard (deleted: 2026-09-23); 122B/gemma4/Next-80B GGU...) [no-belief: audit-reconciliation]
  The lineup change deprecated the role-holding rows and never touched the
  exact-artifact rows beneath them, so `qwen35_122b_iq2m`,
  `qwen3_next_80b_a3b_instruct_iq2m_local`, `gemma4_26b_a4b_orig_q8_local`,
  `gemma4_26b_a4b_q4km_current_local`, `gemma4_26b_a4b_orig_bf16_local`,
  `gemma4_26b_a4b_ud_iq4xs_local` and `draft_gemma4_26b_a4b_assistant_v6_f16_local`
  are all still live and non-deprecated. Three of them ALREADY point at absent
  files. Deleting before deprecating leaves seven rows naming missing artifacts.
  Clean checks already pass: no process maps them (`/proc/*/maps`), no live
  serving role references them. Use the `retire-model` skill — this is exactly
  what it refuses on. **Blocker: deletion is an operator action (destructive,
  irreversible); the deprecation half can be done now.**

- [ ] **SSU-F4 — make the stack-change surfaces derive instead of restate.**
  The audit's structural finding (`artifacts/operator/session-friction-audit-20260922.md` §2):
  `port_map`, `role_launch_meta`, `numa_config`, the procedure enums and
  `roles.*` each independently restate `shared_with`, and nothing recomputes.
  The `stack-change` skill now enforces the discipline by hand; the durable fix
  is to derive them. **Blocker: none — design work, sizeable.**

- [x] **SSU-F8 — `src/config/models.py::_LEGACY_SERVER_URL_FALLBACKS` still names the retired `:8072` ✅ 2026-10-29 (audit: epyc-orchestrator src/config/models.py:303-312 comment "row corrected 2026-09-23, SSU-F8": worker_general/math/toolrunner now point at :8070 not :8072 (checked 2026-10-29)) [no-belief: audit-reconciliation]
  worker fleet, and eleven neighbouring tests assert the same dead ports.** Found by SSU-F5 while
  reading, reported rather than fixed because it is outside one test file.
  Three rows — `worker_general`, `worker_math`, `toolrunner` — carry
  `full:http://localhost:8072,http://localhost:8082,http://localhost:8182`. Those ports have not
  existed since 2026-09-22; all three roles are aliases on frontdoor `:8070`. `_server_url_default()`
  ends in a bare subscript of this dict, so in **exactly the degraded mode the table exists to serve**
  (priors unreadable, no runtime facts, fresh checkout, bootstrap) these three roles resolve to a fleet
  with nothing listening. It reads correct today only because live runtime facts win.
  `worker_summarize` and `coder_escalation` were updated at their cutovers; the worker lane was not.
  **Do not just update the three rows.** Add `_LEGACY_SERVER_URL_FALLBACKS` as a **sixth surface** in
  `scripts/validate/check_shared_with_derivations.py` — an alias's fallback must equal its host's,
  recomputed and diffed. It is the shape that file already handles, and its absence is the whole reason
  this rotted silently while the five wired surfaces did not.
  Then clear the eleven pre-existing failures in the neighbouring suites (verified present without
  SSU-F5's change; none of them import the file it edited):
  `test_config.py` ×2 (the consumer-side twin of the defect above), `test_config_lineup_liveness.py` ×1
  (`KeyError: 'worker_general'`), `test_stack_numa_reader_agreement.py` ×2, `test_stack_numa.py` ×1,
  `test_stack_manifest_imports.py` ×4, `test_stack_change_guard.py` ×1.
  **Two of those deserve attention beyond "stale literal".** `test_stack_numa_reader_agreement`
  (`assert [8080] == [8080, 8180]`) is a reader *disagreeing about half-instance ports* — the only
  failure whose cause is not obviously a copied constant, and worth looking at independently of tests.
  And two of the four `test_stack_manifest_imports` failures are a **stale parity exception still live
  in `launch_manifest.yaml`**, whose own text says it no longer applies; while it sits there it
  pre-excuses the next real divergence. One line, a live surface, owned by whoever owns that file.
  **Blocker: none.**
  *Progress 2026-09-23 (orch `b14ed228`, an ancestor of origin/main):* `_LEGACY_SERVER_URL_FALLBACKS` is now the sixth derived surface in `check_shared_with_derivations.py`, wired into `stack_change_pipeline` before the lean compile. On its first run it found four stale rows, not three (`ingest_long_context` also named a retired fleet). The six neighbouring suites went from 11 failed / 288 passed to 299 passed. The commit judged the reader-agreement failure not a production defect, and found that the "stale parity exception" did not exist (`exceptions: []` since 2026-08-02; the parity tests had gone vacuous). Left open for the owner to confirm against this box's full scope and tick.

- [x] **SSU-F9 — a correctly-acquired push lock does not satisfy the pre-push guard, and the failure
  mode is silent.** Measured 2026-09-23: four consecutive failed pushes of one reviewed commit.
  Two independent defects compose, and each one alone is enough to block a push while reporting success:
  **(a) the lock directories disagree.** `serialized_push.py` with no `--lock-dir` derives ONE canonical
  directory from the git common dir (correct, and deliberate — it is what makes all five lane worktrees
  contend for one lease). The pre-push hook looks in `<repo>/coordination/push-locks/`. So `--acquire`
  reports `acquired push lock for .` and the hook then reports `the push serialization lock is NOT HELD
  — no lock file at /workspace/coordination/push-locks/push-<key>.json`. Both are telling the truth
  about different directories.
  **(b) the wrapper's own `--push` cannot satisfy its own guard across two tool calls.** The guard
  accepts a push whose process is a *descendant of the lock holder*, but `--acquire` and `--push` run as
  separate processes, so the holder pid is not an ancestor and the check falls through to
  `EPYC_PUSH_LOCK_HOLDER`/`AGENT_ID` — neither of which the wrapper exports. The push fails.
  **The silence is the real defect**: `--push` prints its full publish manifest and then
  `PUSHING as '<agent>' under the push lock ...` as its LAST line, while git's `error: failed to push
  some refs` goes to stderr and surfaces *before* the manifest. A caller reading the tail sees a
  clean-looking manifest ending in `PUSHING`, and `--release` afterwards says `(no push lock held)`,
  which reads like a normal post-push release. Nothing in that sequence says the push did not happen.
  Only `git cherry origin/main main` does — which is why the wrap-up contract requires it.
  Fix: make the guard and the wrapper agree on one lock directory; have `--push` exit non-zero and say
  `PUSH FAILED` on the last line; and have the wrapper export its own identity so its push satisfies its
  own guard. **Blocker: none.**
  ✅ 2026-09-23 — fixed in root `0f9a4ef1` (verified an ancestor of origin/main 2026-09-27): guard and wrapper share one lock resolver, the wrapper declares `EPYC_PUSH_LOCK_HOLDER` for its own push, and `--push` verifies with `git cherry` and ends on `PUSH VERIFIED` / `PUSH FAILED` (exit 4). The D9 ack is in the commit (SSU-F9a). Outcome, SSU-F9a and SSU-F9b: [completed sibling](../completed/model-stack-single-source-update-pipeline-completed-through-2026-09-27.md).

- [x] **SSU-F9c — `promote_lane.py:519` has the same defect one lease over.** It defaults
  `--lock-dir` to `serialized_push.DEFAULT_LOCK_DIR`, the `__file__`-relative fallback, which in a
  lane worktree is that lane's **private** directory — so the *promote* lease serializes nothing
  across lanes, exactly the 2026-09-01 incident that the push lease's git-common-dir derivation was
  introduced to fix. ✅ 2026-10-05: default promotion lease now uses the target's git common
  directory via `serialized_push.default_lock_dir`; environment/CLI overrides remain explicit.
  Accepted CI run [37273697465](https://github.com/pestopoppa/epyc-root/actions/runs/37273697465),
  combined source `23298f00096f24b5d665a478467692f2085c09a0`: three focused fixtures passed,
  including two real worktree leases contending for one lock. No actual promotion was executed.

- [ ] **SSU-F10 — every GPU role on this host is un-auditable for VRAM between reloads, by
  default.** The per-buffer breakdown (`load_tensors:`, `llama_kv_cache:`,
  `llama_memory_recurrent:`, `sched_reserve:`) is suppressed at the launcher's default log
  verbosity, which is why SSU-F3 had to be answered by subtraction in the first place — and why the
  subtraction was wrong by 0.277 GiB. The 2026-09-23 reload settled `:8083` only, and only until it
  next restarts. Raise the model-load log verbosity permanently in the launcher so the decomposition
  is in the log of every GPU role from the moment it starts. A capacity model that cannot be checked
  against the kernel's own numbers is a model nobody can falsify. **Blocker: none.**

- [x] ✅ 2026-11-01 — APP `2c4350972645856fc20c356d0d4659da20edd57f`, Research `5e3cf5355bc701f6c055ce83836fcdabfca8cfcd`; [test/artifact](https://github.com/pestopoppa/epyc-orchestrator/blob/2c4350972645856fc20c356d0d4659da20edd57f/artifacts/ssuf11-20261101/README.md). [no-belief: source launch/attestation conformance only] **SSU-F11 — the registry's `recipe:` block is DECORATIVE: nothing reads it, and the served
  process runs a hardcoded parallel configuration.** Root-caused 2026-09-23 while chasing SSU-F7's
  two missing env knobs on `:8074`. The knobs are only the visible edge.

  **The measurement.** `architect_critic` declares, in `model_registry.yaml` under
  `recipe: {recipe_id: qwen38-flash-next-cpu-mtp}`: `threads: 48`, `cpu_shape: NUMA_FULL_T48`, and
  `env: {GGML_NOHUGEPAGE_PROCESS: '1', GGML_FA_SPLIT_KV: '0'}`. The live process (pid 2021760) runs
  `-t 96`, and its `/proc/<pid>/environ` contains `GGML_IQK=1` and the four OMP vars and **none of
  the declared knobs**. `no_mmap`, `-ctk/-ctv f16` and `--spec-draft-n-max 4` do match — but they
  match because the *launcher* and the `acceleration:` block independently say so, not because
  anything consulted `recipe:`.

  **Why: there is no reader.** `grep` for any consumer of `recipe.env` across `scripts/` and `src/`
  returns **zero hits**. `build_launch_env()` (`scripts/server/stack_env.py:258`) composes its env
  from a base copy, a canonical OMP block, and `_role_env_overrides()` — which reads
  `_ROLE_ENV_BLOCKS`, a **hardcoded dict in that file**. For `architect_critic` that dict holds
  exactly `{'GGML_NUMA_REPACK_INTERLEAVE': '0'}`, and not one of the eight role blocks mentions any
  of the three recipe knobs. `GGML_IQK=1` is live because it is a launcher default, not because the
  recipe asked for it — which is precisely why this looked like it was working.
  `cpu_shape: NUMA_FULL_T48` has no definition in `stack_numa.py`, which is why the thread count
  falls through to 96.

  **Why it matters beyond hygiene.** `GGML_NOHUGEPAGE_PROCESS=1` is **CHAMP-2, ADOPTED 2026-09-08 by
  operator ruling** (`model_registry_full.yaml:1758` says so in its own comment), it is a
  SESSION-unit knob that must be exported AT LAUNCH, and it is not being exported. An adopted,
  operator-ruled optimisation is not reaching production and nothing detects that.
  **State direction only, never a magnitude**: `qwen38_flash_next_recipe.py` sets
  `THP_SHIM["magnitude_claimed"] = False` deliberately, and the 86.4% figure in that module's tests
  is about conflating the two THP knobs discarding most of the CHAMPION, not about this shim's own
  effect. Do not quote it as the shim's value.

  **Fix shape** — the same one SSU-F8 used, and for the same reason: derive, then make disagreement
  detectable. Have `build_launch_env()` read `recipe.env` from the registry, with `_ROLE_ENV_BLOCKS`
  either removed or reduced to a documented override layer; resolve `cpu_shape` against
  `stack_numa.py` and FAIL on an undefined shape rather than silently falling through to a default;
  and add "the served process's env and thread count equal its declared recipe" as a surface in
  `scripts/validate/check_shared_with_derivations.py`, which is now the established home for exactly
  this check. A declared recipe that nothing reads is not a source of truth, it is a comment.

  **Carry this into any claim measured on `:8074`.** The architect CPU quality gate runs against
  this process, so its rows are `instrument_class: serving` AND the served configuration is not the
  recipe's — `-t 96` where the recipe measured `-t 48`, without the THP shim. The recipe's recorded
  43.281 t/s decode was measured at `t=48` WITH the shim on the champion build, so it cannot be
  expected to describe this process, and the two must never be quoted against each other.
  **2026-09-27 — the `threads: 48` / `NUMA_FULL_T48` claim is SUPERSEDED by measurement.** DAR-LAT-3h's signed G1
  (v10, served shape) chose **T96**: 48 threads failed parity (wall 1.0385×, TTFT 1.055× vs 96) and the THP shim gave
  no gain (1.009×). So the 2026-09-22 C3 ruling's premise ("48 is the served decode optimum") no longer holds, live
  `-t 96` is the right shape, and nothing was applied. The recipe text still says 48 because the correcting research
  lane was not merged either; when this task makes `recipe:` load-bearing, it must derive 96, not 48. Evidence:
  `artifacts/operator/stack-change-dar-lat-3h-20260926/RESULT.md`.
  **Blocker: none.**

  - 2026-11-01 implementation: recipe environment values now reach launch environment construction and survive ambient-GGML sanitization, before the documented role override layer. Undefined shapes, declared-thread mismatch and actual-instance shape disagreement refuse. The explicit `--recipe-process ROLE=PID` checker compares declared effective environment and thread count with stable process starttime/UID and repeated argv/environment reads. 83 launcher controls plus 31 derivation-checker controls pass; a no-process native canary compiles the corrected Research master and calls the real default command builder: architect_general, port 8074, T96, split-KV 0 and no THP shim. The original model/port mapping survives the historical role rename. No live process was checked or restarted, no model ran, and no performance or deployment claim follows. Research native hooks pass with optional PII capture unavailable; the ordinary exact-diff PII scan passed, and no native PII finding receipt is claimed. The exceptional sparse worktree was removed through the gate. Future live-finding custody is tracked as VB-SSU-F11-PROCESS-WRITE.

- [x] **SSU-F13 — 10 more unit tests still encode the pre-cutover topology.** ✅ 2026-10-05 Fail on clean origin/main
  (2026-09-24, after `8d7633d0`): `tests/unit/test_default_template_topology_parity.py` (9 — e.g.
  `ingest_long_context` now alias-only, `worker_general` has no `NUMA_CONFIG` instance) and
  `tests/unit/test_stack_templates_v2.py::test_default_yaml_loads_and_validates`. Per test: decide stale
  fixture (derive from the source of truth, as SSU-F5) vs. a real template defect; do not re-pin constants.
  - *2026-09-24 confirmation:* the `worker_general` / `NUMA_CONFIG` `KeyError` reproduces read-only in the
    SHARED clone (`/mnt/raid0/llm/epyc-orchestrator`, `main`, unrelated dirty files in `src/services/image_*`)
    via `.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/test_fleet_layer_dispatch.py` — same
    `KeyError: 'worker_general'` at collection. This is **real pre-cutover drift, not a worktree-only config
    gap.**
  - [x] ✅ 2026-10-05 A wider `tests/unit` sweep reported by an agent this session found **~96 failures / 38 errors**,
    which is far more than the 10 named above — re-run the full `tests/unit` suite, bucket every new failure
    by root cause (same topology-parity class vs. genuinely new), and fold the ones that match this item's
    scope in; file any that don't as their own row.
- [ ] **SSU-F16 — build the architect_critic CRITIC-SUITE instrument and run it on Qwen3.8-Flash-Next.**
  Operator chose option A on 2026-09-24 (orch `9692c7f9`, merged in `d7ab368e` on
  `fix/promotion-gate-red-20260924`). Strict now counts `performance.general_suite_quality`
  (mmlu_pro 0.7550 / gpqa 0.6513) as per-axis evidence, never as `overall`, so the gate no longer blocks
  on it. The role-purpose gap that research `58b115ed` deliberately left open is **still open**:
  `quality_score` means the adversarial-critique suite on this role, it stays null, and no critic-suite
  instrument exists anywhere. Build one (plan-critique items, DELETE-lens scoring, truncation audit per
  `promotion_gates.yaml`), run it on live :8074 at a CPU-quiet boundary, and record the result in
  `roles.architect_critic.performance.quality_score`. Blocker: none (buildable); the run needs an
  inference window. Emit producer-authored belief rows from the first run, as the SSU-F2 CPU bench does
  (root `CLAUDE.md` → *Belief Kernel*).

- [ ] **SSU-F17 — key servers by model instance and bind every role to a server id.** **Sequenced after UFH-13
  (operator 2026-09-27)**: approved in chat (session https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ) to run
  AFTER the thesis experiment (`thesis-experiment-orchestrator-vs-strongest-model.md`), not before or during it.
  - **The limit today.** `server_mode.<key>` is both a role name and a process declaration, so a server has no name
    except its owning role's. An alias binds role → role through `server_mode.<host role>.shared_with`, and
    `alias_of` is documentation only. When a role label moves between processes, every alias must be re-pointed by
    hand across about 8 restated surfaces. ARCHSWAP-20260927 had to do exactly that.
  - **The change.**
    - Add a server namespace keyed by model instance (e.g. `servers.qwen38_27b_q8_gpu0 {port, model, shape, ...}`).
    - Every role, host or alias, binds to a server id.
    - Retire the role → role binding through `server_mode.<host role>.shared_with` and the documentation-only
      `alias_of`, with their validators and derived restatements (`shared_with_first_n`, the alias `server_mode`
      rows that must equal the host's port).
    - Roles stay distinct prompt and tier profiles: `orchestration/prompts/roles/{role}.md` and per-role
      `chat_template_kwargs` stay per role.
  - **Done when** a role swap like ARCHSWAP is a two-line change to two roles' server ids and no alias moves.
  - **Evidence.** ARCHSWAP PACKAGE §4a,
    `/mnt/raid0/llm/tmp/archswap-20260927/root/artifacts/operator/stack-change-archswap-20260927/PACKAGE.md` (root
    `lane/archswap-20260927`). Code refs (orch `280059cc`): `src/registry/stack_priors.py:900-907`
    (`_server_for_role`), `src/registry/registry_compiler.py:117-119`, `src/registry/model_descriptors.py:1285-1300`,
    `scripts/validate/check_shared_with_derivations.py:400-442` (`check_alias_of_coherence`).
  - Overlaps SSU-F4 (derive instead of restate): once roles bind to server ids, the `shared_with` alias lists that
    SSU-F4 would derive no longer exist.
  - Also fold in ARCHSWAP acknowledgement **A-5**, a pre-existing defect the swap did not cause:
    `ingest_long_context` is in `serial_roles`, but its host server is not. Once roles bind to server ids,
    serial-ness belongs to the server. Derive it there, so an alias can no longer disagree with its host. (Folded here
    2026-09-27 rather than filed separately: a stand-alone fix would re-edit a surface this task deletes.)
  - It changes the registry schema, so it runs as a `stack-change` package with one operator signature.
  - Not folded here (2026-09-28): `coder_escalation`'s dead `enable_thinking: False` (it inherits its host's
    thinking-on lane) is reconciled under `routing-intelligence.md` RI-23a, because it is needed before TE-reopen.
    RI-23a was applied 2026-09-29 (receipt `RATIFY-RI23A-20260929`): the role is thinking-on in the registry and the
    priors.
  - Blocker: sequencing only (UFH-13's verdict, TE-6).

2026-10-05 NI18 fullscan checkpoint accepted: all895 tracked unit modules have independently reopened original native receipts and deterministic selection/source/hash accounting across32 shards. Outcomes826TRUE57FALSE12NULL;16,227 collected/15,719 passed/258 failures/68 errors/182 skipped. This is capture/accounting acceptance, never whole-suite conformance. Originals remain unchanged in CI37327810408 and owned custody; [derivative inventory](../../artifacts/ni05/unit-sweep-37327810408/README.md) records the distinction. A prospective nine-module fixture rerun prepares only missing owned0700 runner scratch; parentNI18/SSU-F13 remains open for classification/repairs. Running tally **35/38**.

- [x] **SSU-FIXTURE-KVSLOTS (NI05-39)** ✅ 2026-10-05 — original fullscan modules `test_build_server_command_helpers.py` (8 failures of74) and `test_k4_ubatch_not_inert.py` (3 failures of11) fail at mkdir of `/mnt/raid0/llm/cache/kv_slots/{role}` on ephemeral CI. Main source review confirms argv-building fixtures with existing process/health stubs. Prepare/attest only the runner-owned0700 cache fixture and run the two unchanged modules independently through existing native CI custody. No serving, kernel-store simulation, host/peer/live KV writes or source policy change. Scope and exact prospective recipe receive main review; preserve original FALSE receipts.

NI18 scratch-fixture phase independently accepted from original CI37331885023: all nine unchanged test modules reopen TRUE Judged/Located;312 collected282passed30skipped0fail/error, separate ordinary guard1/1. Runner-only owned0700 scratch preparation resolves the observed path failures while preserving fence assertions. Earlier895-module FALSE/NULL originals are unchanged; this is no whole-suite pass. NI39 cache-fixture follow-on is newly filed; tally **35/39**, NI18/37/38/39 continue.

- [x] **SSU-FIXTURE-REPL-SPILL (NI05-40)** ✅ 2026-10-05 — nine original failures in `test_repl_spill_output.py` use `/mnt/raid0/llm/tmp/repl_spill_test_<uuid>` and cannot create spill files on the runner. Source confirms execute retains raw stdout/error after the directory OSError. Prepare the previously reviewed owned0700 scratch fixture and capture this unchanged module separately; retain original failures, no LLM calls or source policy change.
- [x] **SSU-SCORING-EXTRA (NI05-41) ✅ 2026-10-05** — `test_ev_conf2_confidence_probe.py`, `test_eval_tower_ev11_stats.py`, and `test_eval_verifier_mode.py` need the real optional `math_verify` parser/verifier, absent from dev/uv.lock. Prepare a pinned optional scoring extra and off-host lock generation, review the exact generated lock, then capture the tiny offline fixtures plus intentional missing-package refusals. Keep hard-fail semantics and default serving dependencies; no inference or actual model-evaluation claim.
- [x] **SSU-GRAPH-FIXTURES (NI05-42)** ✅ 2026-10-05 — select temporary-DB-only graph modules whose first sweep skipped at `pytest.importorskip("kuzu")`, using the existing locked `graph` extra (`kuzu==0.11.3`). Review the exact selection and no-inference boundary before independent captures. No host graph access, fabricated data or blanket skip removal.

NI39 accepted 2026-10-05: main reopened all three original CI37334324990 receipts through the trusted reader/shared verifier grade. The two unchanged command-construction modules pass74/74 and11/11 with zero skips/failures/errors; the distinct ordinary expected capacity refusal passes1/1. Both original source hashes match the fullscan; runner contexts attest an absent-before-setup, empty, owned0700 cache fixture without override or live KV data. Original fullscan outcomes remain unchanged. Source-only follow-ons NI40 scratch-dependent spill output, NI41 optional scorer dependency and NI42 temporary-DB graph fixtures are filed for concrete review. Published tally **36/42**; NI18 stays open.


- [x] **SSU-FIXTURE-REPL-FILESYSTEM (NI05-43) ✅ 2026-10-05: named offline REPL filesystem modules with disposable owned roots** — the two original NULL modules skip under CI/mock flags. Source proves only module-local/builtin fixtures and mocked patch subprocesses; run exact optional child captures with those flags unset and `--noconftest`, disclosing excluded 100-GiB/model memory guard. Use fresh owned0700 runner scratch and disposable checkout logs/patches, three absent binary overrides and postchecks; preserve default guards and originals. No inference, capacity claim, host filesystem changes or blanket skip removal.

NI40/NI42 accepted 2026-10-05: main independently reopened original CI37339651393 (13/13 spill cases) and CI37339553198 (five graph modules,65/65 cases), all TRUE Judged/Located with zero skips/failures/errors. Declared source snapshots match pinned appdb38737d and exact workflow/producer originals. Independent postchecks prove all three binary targets absent/non-symlink; graph uses temporary databases and mocked embeddings. Spill scratch ownership/emptiness is attested before execution only, with no separate original post-run scratch check. Original fullscan failures/skips and first graph diagnostic NULL records remain unchanged. Public originals are preserved at artifacts/ni05/repl-spill-37339651393 and artifacts/ni05/graph-fixtures-37339553198. Accepted tally **39/44**; NI18/38/41/43/44 continue.

#### NI18 source-correlated offline follow-ons — 2026-10-05

Original CI37327810408 FALSE receipts remain unchanged. Source comparison at appdb38737d and prior6714c72 confirms these distinct scopes; hypotheses become product findings only after exact source/fixture review. Existing CI conformance producer/shared verifier carrier covers prospective selected commands; no new grader or historical warrant.

- [x] **SSU-STRATEGY-PROJECTION-FLAG (NI05-45)** ✅ 2026-10-05 — Repair the explicit strategy-report CLI fallback flag at its leaf while preserving owned-store degraded-vector refusal and default semantic requirements. Original test_strategy_projection_report has4/5passed; empty JSON stdout follows RuntimeError/rc2. Review sanctioned opt-in plumbing and mock all embedding paths; never bypass ownership guards or write a live strategy store.

- [x] **SSU-EXECUTOR-MOCKED-VALIDATION (NI05-54)** ✅ 2026-10-05 — Original executor modules pass4/5 and23/26. Four constructors validate unavailable binaries before mocked subprocess paths. Set the existing explicit validation option only for those fixtures; retain missing-binary refusal controls, original outcomes and prospective whole-module receipts. Production executor and launch validation stay unchanged.

- [x] **SSU-CLAIM-API-FIXTURES (NI05-55)** ✅ 2026-10-05 — Original claim API module passes11/14. Two mocked spawn cases declare cores0–95 without the existing host-core seam; the quiet OCR case names a missing directory where its assertion expects a CLI leaf. Repair only fixture topology and explicit absent executable argv, preserving placement assertions and no-launch mocks.

- [x] **SSU-TYPED-LIVE-SENTINEL (NI05-56)** ✅ 2026-10-05 — Original typed replay module passes23/24. The live-path refusal case reaches correct missing-path validation offhost. Use an existing temporary sentinel as the monkeypatched live-path identity, trap database reads and assert the actual LIVE refusal; change no resolver behavior and touch no live DB.

- [x] **SSU-ROUTING-POOL-FIXTURE (NI05-57)** ✅ 2026-10-05 — Original specialist routing module passes71/72. The empty lookup test patches a same-named module while production deliberately resolves research by path. Use the existing `_bind_research_pool` seam with an empty synthetic pool, retaining the stale bare-import trap and SystemExit1. No production loader change or actual corpus access.

- [x] **SSU-PROMPT-FORGE-VOCAB-FIXTURE (NI05-58)** ✅ 2026-10-05 — Original mutation extraction module passes8/9. Its happy path reaches the data-sourced leakage vocabulary omitted from the app-only runner. Inject a tiny synthetic `EvalIdVocabulary` through the existing constructor seam and keep real leakage checks/mocked generation; do not disable the checker or read the host research pool.

- [x] **SSU-REPL-SCORER-SCRATCH (NI05-59)** — Original REPL environment and debug code-execution modules pass139/140 and5/11. Prepare fresh owned0700 runner scratch through declared existing seams, then capture exact unchanged modules with finite child bounds and local/mock execution only. Preserve original failures; any remaining assertion becomes an individually attributed source finding, never a blanket pass. ✅ 2026-10-05 — 140+12 cases; source and custody complete.

- [x] **SSU-LOCAL-EMBEDDING-FIXTURES (NI05-60)** ✅ 2026-10-05 — Original creativity/strategy seed modules pass52/53 and4/5. Use existing embedder injection with temporary SQLite/FAISS stores and deterministic vectors. Retain actual store assertions and default semantic/degraded ownership guards; no live store, endpoint or model access. Review exact source/test scope before any capture.

- [x] **SSU-VL-REPAIR-TEMP-CACHE (NI05-46) ✅ 2026-10-05** — Make test_td21_19_vl_structured_repair use a pytest-owned cache directory. Original2/8passed; hardcoded VISION_CACHE_DIR prevents mocked HTTP requests and produces secondary missing-structured errors. Preserve actual vision/runtime code, mocked responses and terminal-repair assertions.

- [x] **SSU-QUIESCENCE-TEMP-HOLDS (NI05-47) ✅ 2026-10-05** — Replace the OAB3 fixture hardcoded /mnt hold directory with pytest-owned temporary storage via the existing HOLD_DIR_ENV seam. Original6/10passed. Preserve quiescence/scoring guards, witness semantics and meaningful local-process fixtures; no host holds or live scorer.

- [x] **SSU-OPENAI-REPL-SCOPE-DESCRIPTION (NI05-48) ✅ 2026-10-05** — Reconcile the x_disable_repl public description with actual vision/client route branches. Original47/48schema cases passed; one description-scope assertion fails. Confirm current request rejection semantics and add only accurate description clauses; no route behavior or serving reload.

- [x] **SSU-PAIRWISE-PROMPT-FIXTURES (NI05-49) ✅ 2026-10-05** — Make two offline pairwise planner fixtures use an explicit temporary instruction_precision prompt-source mapping with tiny synthetic YAML prompts. Original11/13passed; configured production prompt source is absent offhost. Preserve planner/reference-source policy and assert deterministic counts; no real corpus acquisition or collection.

- [x] **SSU-PARKED-ROLE-HERMETIC-PROBES (NI05-50) ✅ 2026-10-05** — Complete the parked-role fake StackOps fixture with deterministic kfd_pids and gpu_quiet_exclusive injection. Original21/22passed; restore refuses real offhost KFD observation. Preserve all production safety probes and final restore guards; no GPU query, stack action or live process.

- [x] **SSU-OFFHOST-CODE-INDEX (NI05-52)** — refresh the stale GitNexus analysis against an exact clean app snapshot on an isolated runner using the tracked analyze wrapper and pinned verified tool artifact, embeddings/LLM disabled. Preserve all agent/skill files and shared canonical indices; record original source/tool identities, bounded analyze/status/impact outputs and metadata/clean-state checks for main review. This is code-intelligence dependency evidence, not a performance/quality/scientific tuple or a shared-index deployment. Current stale925-commit results are warnings, not current blast-radius proof. ✅ 2026-10-05 — main accepted originalCI37358369281; historical c885 scope, exact LOW targets and clean-state proofs, no host-index deployment.

2026-10-05 accepted boundary: NI43 retryCI37347669248 passes24/24 exploration plus19/19 mutation cases on unchanged appdb387; main independently verifies both TRUE Judged/Located receipts, every declared source byte, private checkout/empty fixture roots and scratch, and absent binary postchecks. First failed mutation original remains unchanged. NI44 CI37348970500 passes36/36 offline observer cases; main verifies TRUE Judged/Located, pinned source/recipe bytes and isolated bus absence, then integrates exact five source/test files as d4999a170. Qualified authoritative probe evidence replaces marker-derived leaf idle authority; uninstrumented Claude remains UNKNOWN and live processes are not restarted. Public originals: artifacts/ni05/repl-filesystem-37347669248 and artifacts/ni05/observer-leaf-37348970500. NI51 closes only retired E8 active-consumer scope under existing OP-19. Tally **43/52**; NI18/41/45–50/52 remain open, with no inference or live-stack change.

2026-10-05 NI41 accepted: originalCI37351080596 passes68/68 cases (18confidence-probe/9EV11stats/41verifier-mode), zero skips/failures/errors; allfive named positive/missing-package hard-fail controls pass. Main independently reopens allthree TRUE Judged/Located receipts and verifies exact source/dependency/context bytes, installed versions, frozen additive lock and absent binary postchecks. Rawresolver unrelated changes are preserved but rejected for promotion; all214original nonproject lock records/top-level fields remain unchanged. Only the optional extra and its three-package closure are published to appmain65599ff2b02fcf10a9631376e143e507717469b6. Original public custody: artifacts/ni05/eval-scoring-37351080596. SSU-SCORING-EXTRA and VB-CI-OPTIONAL-SCORING-LOCK close; tally **44/52**, NI18/45–50/52 continue. No inference, scientific quality, capacity, default-serving change or runtime reload claim.

2026-10-05 NI46–50 accepted: originalCI37352568892 passes101/101 whole-module cases (8vision/10quiescence/48requestschema/13pairwiseplanner/22parkedrole), zero skips/failures/errors. Main independently reopens allfive TRUE Judged/Located receipts, verifies31Git-boundsource snapshots+4context/install originals per capture and five absent-path/unchanged-lock postchecks. Exact four fixture files and one schema-description file are published to appmain64843e13642930895bb2e52694cd444de5892903; runtime policies and original FALSE sweep outcomes remain unchanged. NI45 still requires fresh source analysis and prospective evidence. NI53 newly filed before execution for active strategy-report original boolean integrity custody, with descriptive counts and no new ladder/method/quality claim. Tally **49/53**; NI18/45/52/53 continue. No inference, liveKFD/GPU/hold/store access or API reload.


- [x] **SSU-ONNX-THREAD-CONTRACT (NI05-61)** ✅ 2026-10-05 — Resolve topology-dependent thread defaults against actual source/configuration, then bind deterministic small-host and production-shaped fixture controls; do not change expected values solely to pass.

- [x] **SSU-KV-PURE-ARITHMETIC (NI05-62)** — Review a pure KV formula boundary for the two modules refused by import-time capacity validation. Require fresh impact/manual callers before production refactoring; keep actual serving-capacity refusal and avoid synthetic RAM. ✅ 2026-10-06 — original18/18; scoped native evidence reviewed and published.

- [x] **SSU-ARGV-CAPACITY-CHILD (NI05-63)** — Investigate the two foreign-interpreter argv-import cases with an owned temporary topology that genuinely fits actual runner RAM. Preserve the import-time capacity guard and original traceback; no fake RAM or source-guard move. ✅ 2026-10-05 — four owned child controls, actual capacity refusal; source published.

- [x] **SSU-ARCHIVE-INTERRUPTED-ATTRIBUTION (NI05-64)** — Prospectively capture test_design_archive with finite verbose node attribution and immediate original-prefix retention; preserve the original missing-JUnit NULL and diagnose the exact interrupted node. ✅ 2026-10-05 — prospective16/16 complete; historical NULL/root-cause boundary retained.

- [x] **SSU-QSCORER-INTERRUPTED-ATTRIBUTION (NI05-65)** — Prospectively capture test_q_scorer with finite verbose node attribution and immediate original-prefix retention. Preserve censored nodes and original NULL; mock or local code paths only, no inference service. ✅ 2026-10-05 — prospective79/79 complete; historical NULL/root-cause boundary retained.

- [x] **SSU-IMPORT-LOCK-INTERRUPTED-ATTRIBUTION (NI05-66)** — Prospectively capture test_inference_lock_concurrent_import with finite child/node bounds and private fixture state. Preserve original NULL, shared host locks and peer processes; review actual child behavior before execution. ✅ 2026-10-05 — prospective2/2 complete; historical NULL/root-cause boundary retained.

- [x] **SSU-JUNIT-COUNT-ATTRIBUTION (NI05-67)** — Inspect the six-pass command versus twelve-test/six-node JUnit inconsistency in test_makefile_gate_contract, then capture fresh native originals. Retain strict count refusal and never rewrite or reseal the historical XML. ✅ 2026-10-05 — source exporter traced; strict NULL12/6 and separate TRUE4/4 control.

- [x] **SSU-SYSTEM-CARD-PATH-FIXTURES (NI05-68)** — Review the two pure missing-priors fallback cases in test_autopilot_system_card and bind explicit owned path fixtures before capture. Preserve renderer/fallback assertions; no real launch or kernel-store claim. ✅ 2026-10-06 — original13/13; scoped native evidence reviewed and published.

- [x] **SSU-EXTERNAL-DRAFTER-ARGV-FIXTURES (NI05-69)** — Review five failed external-drafter command/compiler cases for exact resolver seams and no-execution proof, then capture synthetic argv fixtures. Separate any genuine runtime assertion; no external drafter/server launch. ✅ 2026-10-06 — original12/12; scoped native evidence reviewed and published.

- [x] **SSU-STACK-PRIORS-COMPILER-FIXTURES (NI05-70)** — Review sixteen failed stack-priors compiler cases and bind owned registry/backend path fixtures only for pure compilation. Preserve source-policy assertions and separate real binary/linkage evidence. ✅ 2026-10-06 — original44/44; scoped native evidence reviewed and published.

- [x] **SSU-NUMA-READER-PATH-FIXTURES (NI05-71)** — Resolve six failed NUMA reader-agreement cases as path metadata versus actual kernel evidence, then capture only the proven pure fixture scope. Never substitute a fake production store or imply residency. ✅ 2026-10-06 — original7/7; scoped native evidence reviewed and published.

- [x] **SSU-SPEECH-ENV-COMPOSITION (NI05-72)** — Split seven speech environment/path composition failures from two actual ggml loader cases. Use declared temporary paths only for composition, retain the frozen-service loader requirement and each service-specific library policy. ✅ 2026-10-06 — original7/7; scoped native evidence reviewed and published.

- [x] **SSU-LCB-SYNTHETIC-ORACLE (NI05-73)** — Separate nine scratch failures and three synthetic-oracle assertions in test_livecodebench_oracle from the cached-JSONL helper/skips. Review finite offline fixtures and preserve dataset boundaries; no upstream dataset read or acquisition. ✅ 2026-10-05 — synthetic13/13, source-pinned native TRUE.

- [x] **SSU-E8-T2-ALGORITHM-FIXTURE (NI05-74)** — Separate local T2 question-vector/refusal logic from the omitted research full-pool property in test_e8_quality_baseline_reseed. Review a tiny source-bound synthetic fixture only for algorithm behavior; preserve actual corpus and human-authorization requirements. ✅ 2026-10-05 — synthetic6/6, source-pinned native TRUE.

- [x] **SSU-EXECUTOR-REGISTRY-FALLBACK (NI05-75)** — Trace and repair the early registry-unavailable fallback in scripts/lib/executor.py:get_binary_paths, which returns an in-tree build/bin literal before the delegated kernel-store override. Review fresh impact and exact existing loader-patch callers first; retain explicit binary overrides and missing-store refusal. Test with unavailable registry and an owned absent override, never launch or modify a kernel. ✅ 2026-10-06

- [x] **SSU-DOC-STORE-DEFAULTS (NI05-79)** — align `.env.example`, `docs/SETUP.md` and `README.md` with kernel-store defaults and frozen production; leave binary-path overrides unset by default, retain diagnostic overrides, use CPU-region admission and the experimental build's own library path in build/version examples, and link current records instead of stale counts. ✅ 2026-10-06 — APP source `07b352d0` accepted and promoted to APP main `4a11e974`; three approved documentation/template files only. See [`2026-10-06 NI final wrap`](../../progress/2026-10/2026-10-06-codex-ni-final-wrap.md).

- [x] **SSU-CODE-INDEX-COMPUTE-CLAIM (NI05-76)** — Host index refresh must enforce the existing compute claim before mutating the index or globally installed tooling. Review ROOT and APP wrappers, exact inherited region-claim proof, and a verified isolated off-host boundary; do not accept CI=true alone as host isolation. Validate unclaimed refusal before mutation, claim inheritance, and approved off-host execution in disposable CI. Canonical-host index recovery remains a separate review against a known baseline, with no deletion or unclaimed rebuild. ✅ 2026-10-06 — original native evidence reviewed and published.

2026-10-05 NI54–56 completed: main independently verified all 284 original files from CI37361602330 and reopened four TRUE Judged/Located receipts. The selected whole modules pass 69/69 cases (5 executor, 26 additional executor, 14 claim API, 24 typed replay), with zero failures, errors or skips and five named refusal controls preserved. Each receipt binds 56 Git-backed source inputs plus original runner context. Python 3.11.14, uv 0.8.15, frozen lock and four absent-path/lock postchecks are verified. The exact three commits are published to APP main6bb8d860d410217895efb7806e9ef907a62a4350; four fixture files change, with production behavior intact. Public originals: `artifacts/ni05/fixture-matrix-37361602330`. Original fullscan outcomes stay unchanged. Completed tally **53/75**; NI18 classification, NI45/53 strategy work and NI57–75 continue. No inference, live database, kernel availability, capacity or whole-suite claim.

NI75 impact checkpoint: main verifies all 76 retained files from original CI37361379823. The exact executor wrapper target is HIGH, with 10 impacted nodes, one direct caller and three modules; only the risk validator is nonzero. Source work is stopped and NI75 remains open. Public originals: `artifacts/ni05/executor-impact-37361379823`. This is ordinary offline dependency evidence with no new belief grading rule or host-index deployment.

2026-10-05 incident checkpoint: a delegated fixture worker ran the host GitNexus refresh without a CPU-region claim despite the off-host-only brief. Its captured session was interrupted and returned exit130; ignored index changes and a WAL were reported, so the canonical index is untrusted. Exact execution timestamps and parallel-measurement impact are unknown. No cleanup/recovery or peer process management was performed. See [INC-20261005-unclaimed-host-code-index](../../docs/reference/agent-config/INCIDENT_LOG.md#inc-20261005-unclaimed-host-code-index). NI05-76 files structural wrapper enforcement before implementation. Published completions remain53; newly identified total76.

2026-10-05 NI18 completed in its bounded topology/classification scope. Main independently reopened the original topology modules: 35 default-template cases, nine fleet-dispatch cases and 17 stack-template cases, all TRUE Judged/Located with zero failures/errors/skips and current-source parity. The complete original sweep accounted for all895 tracked modules:826TRUE/57FALSE/12NULL. Main reviewed all69 exception routes against the immutable source-correlated action map, preserved every original outcome and bound current APP6bb8 source bytes (61 unchanged modules/eight reviewed fixture deltas). [Main routing review](../../artifacts/ni05/unit-sweep-37327810408/main-routing-review.json) records31 reviewed child scopes,23 independent queued tasks and15 program-owner/live/historical boundaries. Three missing program routes are now explicit GPU-NI18-FIXTURES, OAB-NI18-FIXTURES and SCG-NI18-FIXTURES checkboxes in their existing canonical handoffs. Parent completion means the original topology verification and wider-sweep classification/routing are done; it does not mean the895-module suite passes or all child repairs are complete. The named NI45/53/57–76 work continues. Completed tally54/76.

2026-10-05 NI05-57 completed: the path-bound routing fixture preserves its stale-module trap and SystemExit1 refusal; the complete module passes72/72 with zero skips, failures or errors. Main independently verifies78 extracted originals,62 Git-backed source inputs plus three context/install inputs, native TRUE Judged/Located and19 postchecks from CI37369215336 attempt1. Only the routing test delta is promoted to APP main198ee59d54750d23b211e80856b913d07357bfbe. Public originals and derivative review: `artifacts/ni05/routing-pool-37369215336`. NI05-58 prompt validation remains open; its original unacquired runner produced no fixture outcome. Existing CI belief carrier applies without a new grading rule. Published scoped completion tally55/76,21 open; the full unit suite remains mixed.

2026-10-05 NI05-61 completed: reviewed topology fixtures enforce the existing8/16 ONNX intra-op defaults and inter_op1, retain positive explicit overrides/refusals, and cover visibleCPU1/8/16/192. Original CI37369039306 attempt2 passes47 ColBERT+13 encoder cases, zero skips/failures/errors; main reopens both TRUE Judged/Located receipts,21 Git-backed+19 context/install inputs each,17 postchecks each and190 ZIP-member comparisons. Two test files are published to APP main33d9de564e3090516780a8889f4ca4e77a779bb7. Public originals: `artifacts/ni05/onnx-fixtures-37369039306`. Earlier setup/acquisition failures remain unchanged, with no invented result. Scoped completion tally56/76,20 open; no live ONNX model, inference, performance or full-suite claim.

2026-10-05 NI05-60 completed: deterministic normalized1024-D embeddings use existing injection seams and temporary SQLite/FAISS stores; real persistence assertions, semantic/degraded ownership guards and default-embedder traps remain. Original CI37372187218 attempt1 passes53 creativity+5 seed cases with zero skips/failures/errors. Main independently reopens both TRUE Judged/Located receipts,22 Git-backed+3 context/install inputs each and17 postchecks each; verifies21 private original metadata and76 downloaded original files. Two test files are published to APP mainec711a7c100a26e183c8e9341e4a3122d21907df. Public originals: `artifacts/ni05/local-embedding-fixtures-37372187218`. Scoped completion tally57/76,19 open; no live store, model inference, semantic quality or full-suite claim.

2026-10-05 NI05-58 completed: the prompt happy-path fixture injects a tiny synthetic EvalIdVocabulary through the existing seam, preserving real leakage validation and mocked generation. The prompt-only retry in original CI37369215336 attempt2 passes9/9, zero skips/failures/errors; routing remains its original successful attempt1 job and was not rerun. Main independently verifies93 private custody files,78 ZIP-member comparisons,62 Git-backed+3 context/install inputs, native TRUE Judged/Located,19 postchecks and three refusal controls. Only the prompt test is published to APP main392afbfc9ce72b4521daa21f6075ccc0ac4b256f. Public originals: `artifacts/ni05/prompt-forge-fixtures-37369215336`. Scoped completion tally58/76,18 open; original unexecuted prompt metadata remains unchanged. No corpus, inference, semantic-quality, capacity or whole-suite claim.

2026-10-05 review checkpoint (completion tally unchanged58/77,19 open): Original NI59 CI37374639638 passes140 REPL+12 scorer cases with native exit0, but both evidence postchecks refuse an installer-created mode0777 uv lock inside the captured temporary directory. Original files remain unchanged; the reviewed next recipe separates installer temporary files into the already isolated cache while preserving strict native-original mode checks. Original NI53 impact CI37376429724 captures exact upstream LOW results for _validate_inputs (6 nodes) and read_receipt (4), then fails on missing runner rg. Main verifies all499 retained custody files and9 source-readset files against native Git43d9100; the one-line Path(shard).name repair is published only on candidateb2955bb, awaiting fresh fixture evidence and promotion. Original NI62 CI37375358644 captures LOW pure-helper impacts but validate_serving_shape_capacity has exact HIGH105-node impact; no production refactor is authorized or applied. NI76 attempt1 acquired no runner and produced no source outcome; one unchanged-workflow rerun succeeds, with JS main/resolveAnalyzeJs exact LOW1/2-node results. Empty Bash File impacts remain UNASSESSED for callable coverage. Source guard implementation remains under review; canonical host index remains untrusted and untouched. No inference, peer reload, kernel modification or full-suite claim.

2026-10-05 NI05-45 completed: original CI37378870278 attempt1 passes11/11 strategy CLI cases, zero skips/failures/errors, native TRUE Judged/Located and all11 postchecks. Main verifies148 private custody files,88 ZIP-member comparisons,19 Git-backed+6 context/install inputs and integration source parity. Explicit write/fallback permission is scoped and restored across constructor/sync/close errors; default semantic/owned-store guards remain and report permission does not identify the actual embedding method. Exact two source/test files are published to APP mainf884406e76d12a98254372a819e1fa6248c9223c. Public originals: `artifacts/ni05/strategy-cli-fixtures-37378870278`. The separate NI53 ROOT job remains original FALSE8/10 and open; no full-run/full-suite, live-store, model-quality or inference claim. Published scoped completion tally59/77,18 open.

2026-10-05 NI05-64 completed: unchanged design-archive whole-module fixtures pass16/16, zero skips/failures/errors, in original CI37381716978 attempt1. Main verifies1,747 private custody files and1,731 ZIP-member comparisons, strictly reopens native TRUE Judged/Located, matches570 Git-backed+5 context/install inputs and20 true postchecks, and proves current APP mainf884 source parity. Finite verbose prospective attribution is complete; the historical missing-JUnit NULL remains unchanged and cannot establish the original interrupted node/root cause. Public untouched metadata/log subset and derivative review: `artifacts/ni05/design-archive-37381716978`; full source/context snapshots remain private, so the public prefix is explicitly not independently reopenable. No source change, inference, kernel/capacity, host-lock, quality or whole-suite claim. Published scoped completion tally60/77,17 open.

2026-10-05 NI05-65 completed: unchanged q-scorer whole-module fixtures pass79/79, zero skips/failures/errors, in original CI37381716978 attempt1. Main verifies1,747 private custody files and1,731 ZIP-member comparisons, strictly reopens native TRUE Judged/Located, matches570 Git-backed+5 context/install inputs and20 true postchecks, and proves current APP mainf884 source parity. Finite verbose prospective attribution is complete; the historical missing-JUnit NULL remains unchanged and cannot establish the original interrupted node/root cause. Public untouched metadata/log subset and derivative review: `artifacts/ni05/q-scorer-37381716978`; full source/context snapshots remain private, so the public prefix is explicitly not independently reopenable. No source change, inference, kernel/capacity, host-lock, quality or whole-suite claim. Published scoped completion tally61/77,16 open.

2026-10-05 NI05-66 completed: unchanged inference-lock whole-module fixtures pass2/2, zero skips/failures/errors, in original CI37381716978 attempt1. Main verifies1,747 private custody files and1,731 ZIP-member comparisons, strictly reopens native TRUE Judged/Located, matches519 Git-backed+5 context/install inputs and20 true postchecks, and proves reviewed APP mainf884 source parity. Finite verbose prospective attribution is complete; the historical missing-JUnit NULL remains unchanged and cannot establish the original interrupted node/root cause. Public untouched metadata/log subset and derivative review: `artifacts/ni05/inference-lock-37381716978`; full source/context snapshots remain private, so the public prefix is explicitly not independently reopenable. No source change, inference, kernel/capacity, host-lock, quality or whole-suite claim. Published scoped completion tally62/77,15 open.

2026-10-05 NI05-59 completed: reviewed owned0700 scratch fixtures pass140 REPL+12 code-execution cases in original CI37383742953 attempt1, zero skips/failures/errors. Main verifies191 private original files and180 ZIP-member comparisons, strictly reopens both TRUE Judged/Located receipts, matches62 Git-backed+10 context/install inputs each and22 true postchecks each. Real spill-file assertions, missing-scratch refusal before Popen and bounded child-cleanup controls remain. Only two test files are published to APP mainad477541dbc2e6da4cfe4176d5f85045f64c6069; runtime behavior is unchanged. The runner custody gate admits only owned direct pytest *current links targeting captured same-parent private0700 directories; all other links/native-prefix links refuse. Prior FALSE/setup originals remain unchanged. Public original metadata/log subset: artifacts/ni05/runner-scratch-37383742953; excluded private source/context/meminfo snapshots are explicitly hashed, and the public prefix cannot independently reopen. Published completion tally63/77,14 open; no inference, live store/kernel, capacity, quality or whole-suite claim.

2026-10-05 NI05-67 completed as a bounded attribution audit: pinned pytest9.0.3 emits successful subTest reports under their parent node IDs, incrementing suite statistics while retaining six parent testcase nodes. Main source review traces this in exact upstream commit a7d58d7a21b78581e636bbbdea13c66ad1657c1e. Fresh original CI37384625409 reproduces command exit0 with suite12/nodes6 and strict native NULL/no rows; the separate four-method control passes4/4 TRUE Judged/Located with zero skips/errors/failures. Main verifies six API-digest ZIPs and182 original-member byte comparisons,13 Git-backed+7 context/install inputs each and all four named postchecks per phase. Source/test and native count grammar remain unchanged; historical XML is never rewritten. Complete public native prefixes: artifacts/ni05/junit-count-attribution-37384625409. This closes attribution, not whole-six conformance. NI78 is newly filed from the actual precommit advisory before its guard repair; total78, published scoped tally65/78,13 open.

2026-10-05 NI05-63 completed: four source-pinned child probes pass4/4 with zero skips/failures/errors in original CI37385650047. Main verifies623 custody files and616 ZIP-member byte comparisons, strictly reopens TRUE Judged/Located, matches592 Git-backed+5 context/install inputs and21 true postchecks. Real foreign /usr/bin/python3.12 children retain hostile-argv, process survival and explicit entry-point reexec assertions. The fitting and oversized owned lineup fixtures use actual unchanged MemTotal/MemAvailable; the oversized control proves the unchanged capacity guard refuses. Complete canonical registry dependency closure is pinned, including loader/descriptors and compatibility shim. Six test/fixture files only are integrated to APP mainb27e5543199ba4f7a8c3fec87c263f35fb5bcbf1; all30 pinned source dependencies match current bytes. Initial checkout failure and subsequent missing-registry FALSE remain unchanged. Public untouched metadata/log subset: artifacts/ni05/argv-capacity-child-37385650047; private source/context originals are explicitly hashed, so the public prefix cannot independently reopen. No production launch/capacity measurement, memory override, kernel, inference or whole-suite claim. Published scoped tally67/78,11 open.

2026-10-05 NI05-73 completed: original CI37389045961 passes13/13, zero failures/errors/skips, strict native TRUE Judged/Located. Main independently verifies six API-digest ZIPs and468 byte-identical original members across both phases, and this phase binds85 Git-backed+7 external context/install inputs with all original postchecks true. Tested APP sourcefe29834d3bc0e203845effc699abddf0f2e3e2f0 remains the receipt identity; only the reviewed test file is integrated to APP maind31ac2e1f6595e126627ab177cb9449ee2e181a2, with selected production source bytes unchanged. Thirteen selected synthetic oracle/scorer and missing-manifest controls retain real bounded local Python scoring children in owned0700 scratch; exact argv/kwargs and child termination are asserted, and teardown leaves scratch empty. The missing-manifest case uses a finite in-memory row rather than the cached-JSONL helper. Dataset acquisition, full cached JSONL and model quality remain outside this scope. Public untouched metadata/log subset: artifacts/ni05/synthetic-oracle-37389045961; all excluded private input/context files are explicitly hashed, so this public prefix cannot independently reopen. Existing native CI carrier/shared grader only; no new grading rule, production kernel, inference or whole-suite claim. Published scoped tally68/78,10 open.

2026-10-05 NI05-74 completed: original CI37389045961 passes6/6, zero failures/errors/skips, strict native TRUE Judged/Located. Main independently verifies six API-digest ZIPs and468 byte-identical original members across both phases, and this phase binds85 Git-backed+7 external context/install inputs with all original postchecks true. Tested APP sourcefe29834d3bc0e203845effc699abddf0f2e3e2f0 remains the receipt identity; only the reviewed test file is integrated to APP main9d553e863ff8ef7954803cb83d415eeda7940aab, with selected production source bytes unchanged. Six tiny seeded T1/T2 question-vector selection and refusal controls exercise local algorithm behavior. The full-corpus property remains unchanged and unselected, with its existing human-authorization requirement preserved; no corpus access, model quality or live quality-baseline warrant. Public untouched metadata/log subset: artifacts/ni05/synthetic-vectors-37389045961; all excluded private input/context files are explicitly hashed, so this public prefix cannot independently reopen. Existing native CI carrier/shared grader only; no new grading rule, production kernel, inference or whole-suite claim. Published scoped tally69/78,9 open.

2026-10-05 NI05-53 completed: prospective private original Strategy Projection Report custody and strict reader/CLI enrollment are published to ROOT main 7c782a266b2551127aff1dd93f29a9e597321117. Original CI37390356985 passes 10/10 selected cases with zero failures, errors or skips; main independently reopens TRUE Judged/Located, compares all 50 original members in three API-digest ZIPs, verifies 30 Git-backed plus six external context/install inputs, and checks all ten true postchecks. The earlier six failures came from a stale exact producer digest; the reviewed correction updates that digest without relaxing equality. Every prior FALSE/NULL/setup original remains unchanged. The capture retains original CLI status, stdout/stderr, JSON/Markdown and prebound source/input/policy identities; the adapter projects only report.ok integrity through the existing verifier carrier/shared grade. Counts are descriptive, and fallback permission does not identify an actual embedding method. Synthetic owned-store controls cover positive/false reports, original exception/NULL disposition, input drift, resealed boolean mismatch, duplicate/member identity, symlinks/private-directory refusal and source enrollment. No live store, model, inference, embedding quality, transitive completeness or historical warrant. Five integrated source files match tested candidate 69c368204e8e582a10ed163574c8c08583eef7cd byte for byte; the new test module retains its entire original AST plus a refusing direct-entry guard, verified separately by the existing AST-only collectability checker (zero blocking/advisory). This ordinary file-integrity supplement is not another CI execution. Public original metadata/log subset: artifacts/ni05/strategy-report-custody-37390356985; private source/context exclusions are explicitly hashed, so the public prefix cannot independently reopen. Published completion tally 70/78; eight tasks remain open.

2026-10-06 NI05-68 completed: original CI37391662467 passes13/13 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Both missing-priors fallback assertions retain their original renderer/compiler bodies. Owned empty backend directories allow metadata compilation; only the exact read-only Git provenance child contract is admitted and its real successful exit is required. The earlier two failures remain preserved; their exact internally caught exception was not observed. Only the reviewed test fixture is published to APP main94d34949e16ce3a0b7827dcbcfa6d7fca0b6c171; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-system-card-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-69 completed: original CI37391662467 passes12/12 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Original external-drafter argv, compile-refusal and runtime-field assertions are unchanged. Owned empty backend directory metadata replaces production-store discovery; Popen refuses every child, so this is not a drafter launch. Only the reviewed test fixture is published to APP main7f36af77dcb90651067398474372536b9db271e2; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-external-drafter-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-70 completed: original CI37391662467 passes44/44 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. All original compiler/policy assertion bodies remain unchanged. Fixtures declare absent binary paths and admit only the exact read-only Git provenance child contract. Nine named compiler consumers must capture a successful provenance read; direct helper consumers may make no Git call. Only the reviewed test fixture is published to APP main75688b0523093b67af99bc87fb34b629ff2a3d20; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-priors-compiler-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-71 completed: original CI37391662467 passes7/7 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Original full/quarter/both NUMA reader-agreement assertions remain unchanged. Owned empty backend path metadata is bound and every child launch is refused. This proves metadata agreement, not host placement or residency. Only the reviewed test fixture is published to APP mainee4b60d253e382b60ceb8f930cae99f2a8617275; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-numa-readers-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-72 completed: original CI37391662467 passes7/7 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Seven original speech environment-composition cases use owned empty STT/TTS paths and refuse all child launches. Real library-path/vendor policy is unchanged. The two actual frozen-service loader cases remain unchanged and unselected. Only the reviewed test fixture is published to APP maincb0a6eb57eca58830b076d4e2e1eb8057ac97031; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-speech-composition-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-76 checkpoint (task remains open): main independently verifies original failed CI37391222859 API ZIP712625349bytes/600 members and strict native FALSE1/1. The actual wrapper timed out after600 seconds with85 recorded expected control statuses and no complete marker; its deeper time cost is not exclusively attributed. Prospective streaming result custody retains full snapshot windows. Separate source review finds a real distinct-grant attribution gap: GLOBAL q0–q3 names hardlinked to one held inode can satisfy repeated checks, with five distinct CPU FLOCKs, or four if aliased to build.q0. This proves incorrect grant attribution, not unsafe concurrent overlap. New proposal015a9253bf7398bb71593b85401dbcadc4558c50c6b346fa4a488e6aab74d91d adds single-link and eight-distinct-identity checks, two real hardlink refusal controls and future transport compression6 preserving inner original bytes. Native denominator stays one testcase; descriptive denominator becomes103. No new source promotion or test run is counted here; no host code-index recovery or execution. Prospective native source wiring is recorded before that capture.

2026-10-06 NI05-62 completed: original CI37392512279 passes18/18 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. The original per-token module passes10 cases and quant-width module passes8. Fixed arithmetic inputs/assertions, production helper source and the eager capacity guard are unchanged. The proposed HIGH-impact pure-module extraction remains unauthorized and is unnecessary for this bounded validation; no architectural extraction was performed. No APP source edit was needed; the existing original test modules ran unchanged. Recipea291322bfc9cdb678aa2081ca786a16c057f41f3 is published on its owned validation branch. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-kv-arithmetic-37392512279; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-76 completed: original CI37396700409 at recipe591bd02d148bba94ee1ecc271183337493665c85 passes ONE native pytest testcase with103 actual descriptive controls, including CPU GLOBAL shared-inode and GLOBAL/build-alias refusals. Main independently verifies the complete API ZIP seal, every original member,103 exclusive sidecars equal to aggregate records, original statuses and denial snapshots, the exact50-input readset (15 ROOT Git,16 APP Git,7 approved fixture,12 context), pre-execution bindings and postchecks. Strict native TRUE1/1 projects through the existing shared grader as Judged/Located; no second ladder or retrofit. ROOT4 and APP3 guard-related implementation files are published; APP main405a5e7c162480c6cbc5919ecfa626850c08c7e0. All seven native CLI closure files remain byte-identical to tested APPb27e5543199ba4f7a8c3fec87c263f35fb5bcbf1; peer FIFO/runtime changes are preserved, without a new whole-current-main validation claim. CPU admission requires eight distinct single-link files, four GLOBAL plus four build, with actual write flocks attributed to one live same-UID ancestor. Refusal64 occurs before downstream index/global-tool mutation; nontruncating writer-lock contention returns75 and its FD is carried across child/exec. CI=true grants no exemption. Validation bypasses API preflight only on the disposable runner while real CPU claims remain mandatory. This is point-in-time admission, not continuous CPU-owner supervision, host-index execution/recovery, runtime deployment, or inference-noninterference evidence. The canonical host index remains untrusted after the recorded incident. Earlier ordinary audit negatives, native600s/85-record failure, prior101-control TRUE slice and failed103/16-record FIFO-message run remain private and unchanged; the original race assertion was preserved. New single-link diagnostics are separate from the original regular-file message. Public metadata/log originals are at artifacts/ni05/code-index-admission-37396700409; excluded private inputs/control snapshots are explicitly hashed, so the public prefix cannot independently reopen. GitNexus impact for new helpers remains UNASSESSED with manual caller review; no host graph query or rebuild was run.

2026-10-06 NI75 approval checkpoint: operator explicitly approved the reviewed HIGH-impact executor fallback repair. Exact dependency scope remains10 affected nodes/one direct caller/three modules; the prior negative query is retained. Reviewed APP candidatefa1eb43a2c4431d695e5c4339373ecbf3b96aed6 changes only the registry-failure branch and adds six no-launch unit cases. Single prospective recipe45660107ffa880c2b97f08f5c775a5cf4aeb943c uses unchanged ROOT producer2dff56e6c9263fe982b12b91eab0552e50610635. Main verified exact diffs and source AST scope; publication/capture is authorized only after this prospective wiring is pushed. No validation outcome or completion is claimed; tally77/78 remains. Main owns original review, integration and per-task wrap-up.

2026-10-06 NI75 corrected-capture checkpoint: main independently verifies all three API ZIP digests and 5,564 original members from CI37406127191, plus exact2,757 readset inputs (2,129 APP Git,617 producer Git,1 recipe and10 context). Strict native result is NULL, exit4, no JUnit/summary and zero projected rows: eager PathsConfig resolution refused the absent CPU store before test collection. All seven independent postchecks pass. Original receipt FILEcb6726d07d366bf0e0f8d18a6a12834b02e33e948c6821a431f0b64d30b1f5e3/selfeafd884c0d25216fa668feab22692d32820ecb3c09571ab13ab87f24d0ad5fbb remain unchanged. Main reviews exact one-workflow correctione1c234b527900c8096032122eaa3c844fd837356, sole child45660107, binding three private nonexistent import-only paths and before/after absence checks. APPfa1eb43a and all six test assertions, capacity guards, source pins and time limits remain unchanged. Test fixtures explicitly clear/set the CPU override before exercising fallback policy. Prospective wiring now points to the corrected recipe before its single new capture. No fallback outcome, tuple or task completion is inferred from the earlier NULL; tally remains77/78.

2026-10-06 NI05-75 completed after MAIN review and publication: original CI37406900511 at recipee1c234b527900c8096032122eaa3c844fd837356 passes all six focused executor fallback cases with no skips/failures/errors. APPfa1eb43a2c4431d695e5c4339373ecbf3b96aed6 changes only get_binary_paths registry-load failure handling: one patchable load attempt, unchanged legacy names, stripped explicit override precedence, otherwise CPU kernel-store resolution with KernelPathError propagated before any Popen. Successful registry delegation/custom names remain unchanged. Original native TRUE6/6 is captured prospectively through unchanged producer2dff56e6 and existing shared grader; MAIN independently reopens all original ZIP/readset/context/fixture/postcheck evidence before acceptance. Three private nonexistent ambient overrides permit eager configuration imports; each fallback test explicitly clears/sets the CPU override and no kernel/model process is launched or store directory materialized. Prior original CI37406127191 remains NULL/exit4/noJUnit before collection, with zero projected rows; original HIGH-impact negative query CI37361379823 remains unchanged ordinary evidence, and the operator approved its10-node/one-direct/three-module repair scope. No production capacity, binary linkage, deployment, inference noninterference or whole-suite pass is claimed. Scoped published completion tally78/78; larger parent programs and standing rules remain open.


2026-10-06 reconciliation: the NI05-75 approval and corrected-capture paragraphs above are historical checkpoints, superseded by the accepted final outcome in the immediately preceding completion record and the linked final wrap. NI05-75 is complete; no operator approval or capture remains pending.

#### W4 real-gate follow-on — 2026-10-07

- [x] **W4-REAL-GATE-SOURCE — make the swap verifier execute its original six target suites from any temporary world using the invoking interpreter.** Source proposal APP`3512707441fd77d8b8ab942c1e2ad614251585a8` replaces relative `uv run` resolution with absolute targets, explicit project configuration and `sys.executable`; new outer controls run actual frontdoor/worker/vision/ingest swaps and preserve corrupted-output refusal. VB-W4-STACK-CHANGE-GATE owns exact hosted proof. No runtime deployment or broad standing W4-growth acceptance. ✅ 2026-10-07 — [MAIN exact original acceptance](../../artifacts/ni08/w4-real-gate-success-acceptance-20261007/README.md).

2026-10-07 final W4 gate source acceptance supersedes the proposed APP351270 source pin above: exact APP9cff6583 source is published in mainfd1869b1cc020c21402f85799eb28259212928f4. Original2/2 outer controls execute all202 cases in each of4 actual synthetic swap worlds with no skips and preserve invalid-world refusal. Six empty-directory ZIP omissions remain explicit in the acceptance packet; source conformance never closes standing migration/runtime readiness requirements.

## Track: model-stack-update-pipeline-audit
<!-- gate: none -->

> Folded from `handoffs/active/model-stack-update-pipeline-audit.md` @ `05e2b812a086` on 2026-11-02 (BRF-T1-F4, route 1a, operator D1/D5; retired row RTG-20 → RTG-36). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Model Stack Update Pipeline Audit

**Status**: IN PROGRESS 2026-06-14 - W1/W2 stack-prior consumer migration active; this audit is now historical-detail support for the concise pickup contract in `model-stack-single-source-update-pipeline.md`. Core pipeline/gate work is live through q_scorer provenance gating, runtime attestation, launch/AutoPilot promotion wiring, scanner-rule ownership, consumer-surface inventory, generated summaries, and N11a cleanup through `epyc-orchestrator` `5f0f248` (`rule_count=27`, `consumer_surface_count=13`, promotion gate 163 passed, warning buckets unchanged: `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`, `waived_legacy_test=9`). Remaining work is residual classified docs/tests, direct benchmark runtime enforcement only if promotion-gate coverage proves insufficient, and other high-risk consumer migrations after focused GitNexus impact checks.
**Priority**: HIGH - stale model constants can silently misroute, mis-score, launch the wrong stack, or corrupt AutoPilot/replay data after a model change
**Scope**: Audit and implementation handoff. No inference, AutoPilot, orchestrator code, research code, or index files were changed by this pass.
**Related**: [stack-change-governance-pipeline.md](stack-lifecycle-program.md), [model-capability-descriptors.md](routing-program.md#track-model-capability-descriptors), [routing-truth-restoration.md](../completed/routing-truth-restoration.md), [running-state-attestation.md](../completed/running-state-attestation.md), [MEASUREMENT.md](../../MEASUREMENT.md)

> **📎 2026-07-18 stale-open audit note.** This doc self-demotes to "historical-detail support" for the SSoT, but it still holds **2 orphan-live boxes tracked in _neither_ authoritative doc** — the `ctx_model_max` contract extension and the tap / policy-hint projection. Kept **LIVE** (deliberately *not* superseded) until those migrate to [`model-stack-single-source-update-pipeline.md`](stack-lifecycle-program.md#track-model-stack-single-source-update-pipeline); its other 2 boxes are covered/deferred. See [`stale-open-audit-2026-07-18.md`](frontier-lab-automation.md#track-stale-open-audit-2026-07-18) finding #5.

#### Objective

Turn the existing stack-prior work into a robust, repeatable, fail-closed pipeline for changing orchestration-stack models and all model-specific quantities:

- role -> model binding
- role -> serving endpoint, ports, slots, shared-server binding, and hot/warm state
- q_scorer and seeding reward cost/TPS/quality priors
- routing priors, role budgets, role enums, admission limits, lock/tap classifications, and launch requirements
- generated operator docs/runbooks and runtime attestation

The audit conclusion is clear: the project has the right foundation and the canonical no-inference stack-change gate is now executable. The next step is not another manual q_scorer-style patch; it is to keep shrinking the remaining live consumer surfaces until each model fact comes from `stack_priors.yaml`, generated descriptors, or an explicit degraded-mode fallback.

#### Existing Pipeline Artifacts

These are the real standardized-pipeline artifacts found in the current root/orchestrator trees:

- `/mnt/raid0/llm/epyc-orchestrator/docs/reference/stack-truth-precedence.md`
  - Defines precedence: live serving topology first, descriptors second, role metadata third, historical records last.
  - Explicitly states that `server_mode.*.tier` overrides stale `roles.*.memory.residency`, shared mmap roles must not double-count memory, and retired roles such as `architect_coding` must not appear in active live priors.
- `/mnt/raid0/llm/epyc-orchestrator/src/registry/stack_priors.py`
  - Compiles role records from lean registry, model descriptors, and stack manifest.
  - Current output includes contract v3 plus serving endpoint/ports/slots/tier, effective launch context, launch-entry witness records, launch requirements for worker/VL model paths, priors for throughput/quality/memory, acceleration metadata, model identity, source evidence, and known gaps (`69057f3`, `7917535`, `a001017`).
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/compile_stack_priors.py`
  - Writes `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`.
- `/mnt/raid0/llm/epyc-orchestrator/scripts/validate/stack_change_guard.py`
  - Validates generated artifact contract shape, freshness, live-role gaps, retired-role leakage, generated procedure enums, and curated hardcoded surfaces.
  - `--all-hardcoded-surfaces` currently reports production blockers, legacy tests, and historical docs separately; `--surface-exceptions` reads documented, expiring exceptions (`e162c7c`).
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/sync_procedure_role_enums.py`
  - Syncs `add_model_to_registry.yaml` role choices and `procedure.schema.json` executor roles from stack priors.
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_descriptors.yaml`
  - Physical model identity/evidence layer. Descriptors are keyed by model, not role.
- `/mnt/raid0/llm/epyc-root/handoffs/active/stack-lifecycle-program.md`
  - Current concise pickup contract for post-Fable5 stack single-source work.
- `/mnt/raid0/llm/epyc-root/handoffs/active/stack-lifecycle-program.md`
  - Historical implementation track and detailed commit log; use it for provenance, not as the shortest pickup path.

GitNexus note before this handoff edit: root was refreshed via `scripts/gitnexus-analyze.sh` to `24,180 nodes | 26,206 edges | 43 flows`. `gitnexus impact --repo epyc-root handoffs/active/stack-lifecycle-program.md --direction upstream` returned target not found, `UNKNOWN` risk, `impactedCount=0`, which is expected for this doc path.

#### Sidecar Hardening Review

The 2026-06-13 sidecar audit in `handoffs/completed/model-stack-update-pipeline-hardening-sidecar.md` found no reason to invent a parallel registry or process. It confirmed that the current descriptor -> stack-prior -> guard -> consumer-migration path is the right foundation, with three immediate hardening priorities:

1. **Descriptor check output is now actionable for shared-runtime aliases.** PARTIAL RESOLUTION in `epyc-orchestrator` `d5cb80a`: check mode reports changed model IDs, changed field paths, generated removals/additions, and top-level drift before stale-artifact errors. SAFETY EXTENSION in `4ca702d`: `check` and `update` fail closed when generated descriptors contain role/server conflict gaps. RESOLUTION in `a7b72a9`: `worker_math` and `toolrunner` now compile as virtual aliases of the live Gemma worker runtime instead of standalone live Qwen descriptors; `stack_change_pipeline.py check --allow-known-gaps` now passes with expected known-gap warnings.
2. **q_scorer fallback provenance is now visible.** RESOLVED in `epyc-orchestrator` `d6912e7`: `QScorerPriors` and default `ScoringConfig` now expose per-role source maps for TPS, quality, and memory priors plus an optional degraded reason. Degraded fallback tables remain available for offline/replay, but live/default scoring can now distinguish generated stack-prior values from fallback-filled values.
3. **Generated semantics remain incomplete but launch witness is stronger.** EXTENDED in `epyc-orchestrator` `dc14196`: stack priors now project exact per-role launch port sets from computed `HOT_SERVERS`/`WARM_SERVERS`, and the guard rejects both missing launch ports and extra non-launch ports. EXTENDED in `7917535`: contract v2 requires `serving.launch.entries` and the guard compares launch mode, alias status, primary role, and NUMA/worker/vision instance metadata against the computed manifest. EXTENDED in `a7b72a9`: shared-runtime aliases are represented as alias bindings on the primary runtime descriptor with non-live role metadata recorded as known gaps. EXTENDED in `a001017`: contract v3 requires `serving.effective_context_tokens` and `serving.launch.requirements`, projecting Gemma worker model/draft paths and VL model/mmproj paths into guarded generated priors. EXTENDED in `33c81ff`: contract v4 requires `serving.launch.runtime`, adds launcher/path/runtime source hashes, and guards effective binary family/path, runtime requirements, cache/KV settings, slot-save policy, and launch flags/spec state against computed launch truth. EXTENDED in `fb0fd6d`: simulated data-only workflow fixtures prove shared-runtime swaps, retired-role cleanup, runtime-requirement drift, and context/KV/acceleration drift are caught without production-code edits. EXTENDED in `837829f`: architect quality evidence is structured and projected into descriptors/stack priors. EXTENDED in `03ed49f`: the temporary retired-architect production waiver is gone because the enum member now aliases live `architect_general` and legacy strings normalize to the live role. Remaining work is consumer migration plus residual classified hardcoded-surface cleanup.
4. **Operator acceptance output is now explicit and compact.** EXTENDED in
   `epyc-orchestrator` `079ff30`: `stack_change_pipeline.py check` prints a
   concise `acceptance:` line and a `promotion_gate:` line. Passing checks point
   at the simulated data-only fixture pytest target; failed checks report the
   blocker count and prevent launch/AutoPilot promotion until strict errors are
   resolved or intentionally classified. EXTENDED in `2baaee5`: the two
   intentional retired-role production surfaces are classified in
   `stack_change_guard_exceptions.yaml`, so default check passes while waived
   warnings remain visible. EXTENDED in `a7927c2`: the command footer
   de-duplicates warnings and summarizes waived production-blocker, legacy-test,
   and historical-doc categories.
5. **Consumer fallback residue is shrinking.** EXTENDED in `epyc-orchestrator`
   `2e31055`: seeding role discovery now prefers generated stack priors,
   restoring live `worker_vision` and `vision_escalation` eval coverage while
   excluding shared non-default aliases and preserving registry fallback.
   EXTENDED in `9ed177d`: q_scorer stack-prior alias propagation now carries
   quality to `worker_explore` the same way TPS and memory already flowed from
   live `worker_general`, eliminating that degraded fallback residue.
6. **Launcher parity is now asserted from generated priors in tests.**
   EXTENDED in `epyc-orchestrator` `b026f7d`: the `worker_general` MTP and VL
   launch-command witnesses in `tests/unit/test_build_server_command_helpers.py`
   now derive expected launch requirements from
   `orchestration/derived/stack_priors.yaml`. This is a test-only guardrail for
   generated launch metadata parity, not a launcher/startup behavior change.
   Validation: focused launcher-helper pytest -> 37 passed; simulated
   stack-change fixtures -> 6 passed; `stack_change_pipeline.py check` summary
   ok / no-inference checks passed with the same warning buckets; `py_compile`;
   `git diff --check`.
7. **Promotion output now advertises launch parity.** EXTENDED in
   `epyc-orchestrator` `ebd929b`: `scripts/registry/stack_change_pipeline.py`
   now includes `tests/unit/test_build_server_command_helpers.py` beside the
   simulated data-only fixture target in the printed `promotion_gate:` command,
   with `tests/unit/test_stack_change_pipeline.py` covering the output.
   Validation: py_compile for the pipeline and test; focused pipeline +
   simulated-fixture + launcher-helper pytest -> 53 passed; default check
   summary ok with both targets printed; `git diff --check`.
8. **Promotion output can now execute its targets.** EXTENDED in
   `epyc-orchestrator` `3a20efd`: `check --run-promotion-gate` runs the
   no-inference promotion pytest targets only after the descriptor, stack-prior,
   procedure, guard, and strict checks pass. The default remains a reference
   step. Tests now select simulated fixture steps by name. Validation:
   py_compile for the pipeline and relevant tests; focused pipeline pytest -> 11
   passed; executable promotion gate -> summary ok, promotion_gate ok, nested
   pytest 43 passed; `git diff --check`.

#### Current Drift Examples

The following examples are evidence-backed reasons this work should stay high ROI and should not be handled as one-off cleanup.

1. `scripts/benchmark/seeding_rewards.py` previously owned a stale TPS table.
   - RESOLVED in `epyc-orchestrator` `7ecf847`: `compute_comparative_rewards()` now reads live role throughput from `orchestration/derived/stack_priors.yaml`; missing priors fail closed to the existing no-TPS `0.3` branch unless a caller explicitly provides override/degraded data.
   - EXTENDED in `epyc-orchestrator` `5773777`: active 3-way benchmark evaluation now enumerates live non-VL architect roles from stack priors, the legacy seeder derives slow roles from `ARCHITECT_ROLES`, and the corpus quality gate loads live model/port/name data from stack priors instead of the stale pre-consolidation model table.
   - Validation dropped the live guard from 73 to 62 warnings in `7ecf847`, then from 62 to 56 warnings in `5773777`; `--all-hardcoded-surfaces` now reports 161 warnings after the benchmark cleanup.

2. API routing and delegation still contain retired live-role constants.
   - First cleanup landed in `epyc-orchestrator` `b1402a2`: `src/api/routes/chat_delegation_decision.py` no longer keeps `architect_coding` budget defaults, and the live guard warning count dropped from 85 to 83.
   - Second cleanup landed in `epyc-orchestrator` `481516c`: `src/api/routes/chat_pipeline/delegation_stage.py` and `src/api/routes/chat_pipeline/proactive_stage.py` no longer treat retired `architect_coding` as an architect entrypoint, and the live guard warning count dropped from 83 to 81.
   - Third cleanup landed in `epyc-orchestrator` `519f710`: `_role_to_task_type()` no longer contains the redundant retired-role check, and the live guard warning count dropped from 81 to 80.
   - Fourth cleanup landed in `epyc-orchestrator` `d9c053c`: `/v1/models` now derives live model IDs from `stack_priors.yaml` plus compatibility aliases, and the live guard warning count dropped from 80 to 79.
   - Fifth cleanup landed in `epyc-orchestrator` `1b9db81`: `dashboard_snapshot.py` no longer carries a retired in-flight age override, and the live guard warning count dropped from 79 to 78.
   - Sixth cleanup landed in `epyc-orchestrator` `6bc1f51`: runtime inference lock/tap heavy-role classifications no longer include retired `architect_coding`, and the live guard warning count dropped from 78 to 76.
   - Sixth helper follow-up landed in `epyc-orchestrator` `dfcd280`: inference lock/tap keep the same fallback constants but no longer duplicate stack-prior YAML parsing; both consume shared `live_stack_role_records` / `stack_prior_serving` helpers.
   - Seventh helper follow-up landed in `epyc-orchestrator` `91c7cba`: API health and chat-vision probe URL readers now consume shared `live_stack_role_records`, `stack_prior_serving`, and `stack_prior_serving_ports` helpers instead of parsing stack-prior YAML inside route modules.
   - Seventh cleanup landed in `epyc-orchestrator` `e6e10d8`: approval-gate high-cost role classification no longer includes retired `architect_coding`, and the live guard warning count dropped from 76 to 75.
   - Eighth cleanup landed in `epyc-orchestrator` `eb4dac5`: `_heuristic_role_priors()` now filters its default candidate roles through live `stack_priors.yaml` roles and uses a non-retired degraded fallback; live guard warning count dropped from 75 to 74.
   - Ninth cleanup landed in `epyc-orchestrator` `b5bf5eb`: `analyze_routing_policy.py` now derives specialist-utilization roles from live `stack_priors.yaml` roles with a non-retired fallback; live guard warning count dropped from 74 to 73.
   - Tenth cleanup landed in `epyc-orchestrator` `7ecf847`: `seeding_rewards.py` derives reward throughput and architect grouping from stack priors; live guard warning count dropped from 73 to 62.
   - Eleventh cleanup landed in `epyc-orchestrator` `5773777`: `seeding_eval.py`, `seeding_scoring.py`, `seeding_legacy.py`, and `corpus_quality_gate.py` no longer contain live benchmark retired-role/model assumptions; live guard warning count dropped from 62 to 56.
   - Twelfth cleanup landed in `epyc-orchestrator` `f24eab7`: active config URL/timeout maps no longer publish retired `architect_coding` endpoints or role timeouts; live guard warning count dropped from 56 to 46 and `--all-hardcoded-surfaces` dropped from 161 to 146.
   - Thirteenth cleanup landed in `epyc-orchestrator` `2967526`: the production launcher no longer force-enables `ORCHESTRATOR_LANGGRAPH_ARCHITECT_CODING`; this removed a live startup hazard that the current lowercase hardcoded-surface scan did not count.
   - Fourteenth cleanup landed in `epyc-orchestrator` `c2b4437`: retired `architect_coding` no longer has an active parsing-mode entry and the llm-cache target comment no longer lists it; live guard warning count dropped from 46 to 44 and `--all-hardcoded-surfaces` dropped from 146 to 143.
   - Fifteenth cleanup landed in `epyc-orchestrator` `03ed49f`: `Role.ARCHITECT_CODING` is now an enum alias of live `Role.ARCHITECT_GENERAL`; legacy `"architect_coding"` strings still normalize to `architect_general`; and active prompt fallback / graph node map / prewarm special-cases no longer treat coding architect as a distinct live role.
   - Sixteenth cleanup landed in `epyc-orchestrator` `e7fab9d`: KV adaptive compression and legacy `ToolRegistry` permissions now normalize stale role runtime surfaces. `coder_escalation` and `worker_summarize` share the frontdoor layer-count fallback, retired `architect_coding` is removed from active KV layer tables, production port helpers use live role names, and compatibility `"architect_coding"` permission strings inherit `architect_general` semantics through `Role.from_string()`.
   - Seventeenth cleanup landed in `epyc-orchestrator` `53f12e0`: proactive `/think` / `/ultrathink`-style deep-reasoning triggers now route to live `architect_general` instead of the removed dedicated thinking role. Stale comments were updated, a unit regression covers the routing behavior, and active proactive stale thinking-role strings were not found by `rg`.
   - Eighteenth cleanup landed in `epyc-orchestrator` `822482b`: runtime
     inference lock role classes now derive from generated live stack priors when
     available. Live `worker_pool` and `worker_vision` use shared locks, retired
     `worker_fast` no longer appears in live derived `LIGHT_ROLES`, unknown roles
     fail closed/exclusive, and explicit `shared=` override behavior is unchanged.
   - Nineteenth cleanup landed in `epyc-orchestrator` `eed215d`:
     scheduling/contention role classes are pinned to the current real stack
     matrix. The code no longer carries an unused fallback heavy-role constant or
     stale same-role vision comment; tests assert current n-way light/heavy role
     classes, `worker_fast` absence from matrix light roles, and same-role
     `vision_escalation` ALLOW behavior.
   - Twentieth cleanup landed in `epyc-orchestrator` `3e4ba7c`:
     legacy/model-generated ingress labels now normalize before config lookup.
     `/chat` and OpenAI-compatible paths map `coder` to `coder_escalation` and
     `worker_fast` / `worker_coder` / `worker_code` to `worker_general`; chat
     delegation parsing keeps live valid targets while compatibility aliases
     normalize legacy labels; and REPL `delegate` / `my_role` no longer
     advertise retired `worker_fast`, `worker_coder`, or `worker_explore` as
     live targets while still resolving them to live roles.
   - Twenty-first cleanup landed in `epyc-orchestrator` `6ec2686`:
     compact specialist delegation report prompts now canonicalize through
     `_normalize_delegate_role`. Direct preamble sets are reduced to live
     `coder_escalation` and `worker_general`, while legacy `worker_coder`,
     `worker_explore`, and `worker_fast` aliases still resolve to live-role
     prompt text without advertising retired labels.
   - Twenty-second cleanup landed in `epyc-orchestrator` `09948db`:
     architect investigation prompts now advertise only live delegation roles.
     The active template, fallback constant, and architect system example use
     `coder_escalation` for implementation/file-split delegation and
     `worker_general` for investigation/search; the valid role list no longer
     includes `worker_coder`, `worker_explore`, or `worker_fast`.
   - Twenty-third cleanup landed in `epyc-orchestrator` `4bf8061`:
     `_formalize_output` in `src/api/routes/chat_utils.py` now calls live
     `worker_general` instead of the retired/legacy `worker_explore` label.
     Its docstring no longer embeds stale model speed or port assumptions, and
     coverage asserts `llm_call` receives `worker_general`.
   - Twenty-fourth cleanup landed in `epyc-orchestrator` `a9424a9`:
     user-modeling preference extraction now calls live `worker_general`
     instead of the retired/legacy `worker_explore` label. User-modeling docs
     were updated, and `tests/unit/test_user_modeling.py` asserts the LLM-call
     role is `worker_general`.
   - Twenty-fifth cleanup landed in `epyc-orchestrator` `a7c9ac0`:
     post-hoc model grading now defaults to live `worker_general`; the three
     `orchestration/grading_specs/*.yaml` specs explicitly set
     `judge_role: worker_general`; and `tests/unit/test_model_grader.py`
     verifies fallback/default and explicit override behavior.
   - Twenty-sixth cleanup landed in `epyc-orchestrator` `4f9123f`:
     debugger prompt documentation for `model_graded_evals` now names
     `worker_general`, matching the model-grader default/spec migration.
   - Twenty-seventh cleanup landed in `epyc-orchestrator` `c2daef44`:
     approval-gate high-cost roles now derive from generated live stack-prior
     model memory with `architect_general` only as explicit degraded fallback.
     Tests prove generated priors can move the high-cost gate to a different
     live role and that a valid empty high-cost set does not fall back.
   - Twenty-eighth cleanup landed in `epyc-orchestrator` `80ed046e`:
     chat delegation architect decision/compute budgets now derive the live
     `architect_*` role set from generated stack priors, while compatibility
     imports still expose dynamic budget maps. Tests cover generated live
     architect additions and valid empty live-architect sets.
   - Twenty-ninth cleanup landed in `epyc-orchestrator` `a91c8860`:
     live MemRL/q_scorer initialization now fails closed when required live
     q_scorer priors would come from degraded fallback sources. The runtime
     helper reuses the existing promotion validator before Q-scoring components
     are constructed.
   - Remaining risk: legacy tests and historical docs can still preserve old names unless classified or rewritten; they are no longer production blocker waivers.

3. Config models no longer preserve dead URLs/timeouts as active live maps.
   - RESOLVED in `epyc-orchestrator` `f24eab7`: `src/config/models.py` and `src/config/__init__.py` no longer expose `architect_coding` through `ServerURLsConfig.as_dict()`, `TimeoutsConfig.role_timeouts_dict()`, or env-backed active settings.
   - `TimeoutsConfig.for_role("architect_coding")` now falls through to the default request timeout instead of advertising a retired-role-specific value.
   - Remaining risk: compatibility aliases or legacy tests can still mention dead ports, but they should stay explicit degraded/legacy surfaces rather than active stack truth.

4. Raw launch maps can disagree with generated serving truth.
   - RESOLVED for shared aliases in `epyc-orchestrator` `d4acf24`: `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py` now maps `coder_escalation` and `worker_summarize` to `8070`, and `toolrunner` to `8072`, matching computed launch roles.
   - Current stack priors now keep exact per-role launch ports instead of broad shared-server NUMA port unions: for example `coder_escalation` and `worker_summarize` project only `8070`, `worker_math` and `toolrunner` project `8072/8082`, and `ingest_long_context` projects `8085/8185/8285/8385/8485`.
   - EXTENDED in `epyc-orchestrator` `40d46ea`: `validate_against_registry()` now also checks `server_mode` rows that cover launch roles through `model_role` or `shared_with`, so a stale shared worker port warns before launch.
   - EXTENDED in `epyc-orchestrator` `312b28e`: `stack_change_guard.py` now validates live stack-prior `serving.endpoint`, primary `serving.ports`, and `serving.tier` against the current computed launch manifest, catching launch-manifest changes that registry/descriptor source hashes cannot see.
   - EXTENDED in `epyc-orchestrator` `a6d1200`: generated stack priors now hash `scripts/server/stack_manifest.py` and `scripts/server/stack_numa.py`, and `stack_change_guard.py` requires those source artifacts. A launch topology/tier edit now forces stack-prior regeneration even if registry/descriptors did not change.
   - EXTENDED in `epyc-orchestrator` `dc14196`: the stack-prior compiler now treats computed launch-port sets as authoritative per role, while preserving server `slots`; `stack_change_guard.py` rejects missing launch ports and extra non-launch ports.
   - EXTENDED in `epyc-orchestrator` `7917535`: `serving.launch.entries` records each computed launch entry's port, primary role, mode, alias status, and optional NUMA instance, worker type, or vision type; `stack_change_guard.py` now compares that witness against computed `HOT_SERVERS`/`WARM_SERVERS`.
   - EXTENDED in `epyc-orchestrator` `a001017`: `serving.effective_context_tokens` and `serving.launch.requirements` now project worker model/draft paths and VL model/mmproj paths, with guard comparisons against stack-manifest launch truth.
   - EXTENDED in `epyc-orchestrator` `33c81ff`: contract v4 now adds an effective launch runtime witness under `serving.launch.runtime`, including launcher/path/runtime source hashes and guard comparison.
   - Remaining risk: descriptor-native model context/measurement gaps and hardcoded-surface cleanup still need closure; guards now catch future `PORT_MAP`, shared `server_mode` alias-port drift, generated serving endpoint/tier drift, exact serving port-set drift, launch-entry witness drift, effective-context drift, worker/VL model-path drift, effective runtime/binary/KV/flag drift, and simulated data-only workflow drift.

5. The generated contract now has explicit shape validation but remains semantically incomplete.
   - `epyc-orchestrator` `69057f3` embeds a versioned `epyc.stack_priors` contract and makes `stack_change_guard.py` reject artifacts missing required role/serving/prior fields.
   - `epyc-orchestrator` `7917535` bumps the contract to v2 and requires a structured `serving.launch` section so launch-mode witness data is no longer an optional side effect.
   - GUARDED in `epyc-orchestrator` `4ca702d`: the canonical `stack_change_pipeline.py` refuses descriptor updates when generated descriptors contain role/server conflicts, preventing a stale manual descriptor artifact from being replaced by output that misattributes alias roles to the shared runtime model.
   - RESOLVED in `epyc-orchestrator` `a7b72a9`: shared-runtime aliases with stale role-level model metadata now merge into the primary runtime descriptor instead of emitting standalone live Qwen descriptors.
   - EXTENDED in `epyc-orchestrator` `a001017`: contract v3 requires effective context plus launch requirements; candidate/non-live records still carry complete empty launch structure so consumers can validate before live-role filtering.
   - `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml:1` is still compiled with gaps.
   - RESOLVED for architect quality in `epyc-orchestrator` `837829f`: `roles.architect_general.performance.quality_score: "2.57/3"` now compiles into regenerated `model_descriptors.yaml` and `derived/stack_priors.yaml`, projecting `quality_overall: 0.8567` for both `architect_general` and `qwen35_122b_q4km`.
   - `architect_general` / `qwen35_122b_q4km` known gaps narrowed from quality+ctx to structured ctx only.
   - `frontdoor` and `coder_escalation` record shared serving truth and memory cost correctly at lines 78-205, but still have `ctx_max` and quarter-TPS gaps.
   - `worker_general` has ik-llama launch metadata, MTP metadata, and alias bindings for `worker_math` and `toolrunner`; descriptors record ignored non-live Qwen alias metadata as known gaps rather than role/server conflicts.
   - Risk: consumers need to preserve gaps and fail closed where decision-grade priors are required.

6. The validator is finding the right problems, and the former retired-role waiver is no longer a strict-mode blocker.
   - After `03ed49f`, default `stack_change_guard.py` and `stack_change_guard.py --strict` are clean.
   - After `e7fab9d`, `uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces` still reports only legacy-test and historical-doc classes after split-string test literals; no production runtime surface remains in this cleanup class.
   - This is good machinery; it now needs continued consumer migration and generated-summary replacement so current operator guidance cannot drift.

7. q_scorer live priors now consume the generated stack-prior contract.
   - RESOLVED in `epyc-orchestrator` `e3d967a`: `orchestration/repl_memory/q_scorer.py` loads live TPS, quality, and memory priors from `orchestration/derived/stack_priors.yaml` before falling back to degraded local tables.
   - `frontdoor` and `coder_escalation` now share generated TPS/memory truth; `worker_explore` inherits worker-server TPS/memory from the live `worker_general` stack-prior record; `architect_coding` remains absent from live scorer priors.
   - EXTENDED in `epyc-orchestrator` `a91c8860`: `QScorerPriorSourceError`
     and `require_live_q_scorer_stack_priors()` now let selected live callers
     reject degraded fallback sources for required live roles. API MemRL
     initialization uses this path before constructing Q-scoring components.
   - Remaining risk: fallback tables are still intentionally present for
     degraded/offline mode; additional offline/runner callers can opt into the
     strict helper if they become live production paths.

8. GraphRouter offline consumers no longer own stale live action/model rosters.
   - RESOLVED for GAT training in `epyc-orchestrator` `8cf0310`: `train_graph_router.py` loads live `LLMRole` nodes from `stack_priors.yaml` and skips benchmark/candidate roles.
   - RESOLVED for classifier/verifier extraction in `epyc-orchestrator` `1f16759`: `scripts/graph_router/action_space.py` derives live action labels from stack priors, remaps legacy replay labels into current live roles, and verifier extraction infers `n_actions` from classifier artifacts instead of a fixed `8`.
   - Remaining risk: other historical replay/offline scripts may still need explicit era labels, but the main GraphRouter extraction path no longer leaks retired live roles into new artifacts.

9. Vision ReAct serving-port routing now consumes generated serving truth.
   - RESOLVED in `epyc-orchestrator` `06ff53c`: `src/api/routes/chat_pipeline/vision_stage.py` now reads `worker_vision` and `vision_escalation` ports from `orchestration/derived/stack_priors.yaml` for multimodal ReAct calls.
   - Fallback ports remain explicitly degraded-mode only; the helper reloads the generated artifact on each call rather than caching stale ports in a long-lived API process.
   - CENTRALIZED in `epyc-orchestrator` `d0960b0`: this consumer now reaches the artifact through shared `src/registry/stack_priors.py` serving/port helpers instead of maintaining local stack-prior parsing.
   - EXTENDED in `epyc-orchestrator` `ee784f9`: `src/api/routes/chat_vision.py` now resolves direct and ReAct VL backend URLs from live generated stack-prior `serving.endpoint` / `serving.ports` for `worker_vision` and `vision_escalation`, excludes candidate ports, and normalizes `full:` URL prefixes to concrete endpoints before `httpx` calls.
   - Fallback URL selection remains explicit degraded/config mode with role fallback coverage.
   - Remaining risk: live validation of the end-to-end vision path still belongs to the multimodal handoff; the URL/port source now follows generated stack truth.

10. AutoPilot preflight no longer owns a stale model-server health table.
   - RESOLVED in `epyc-orchestrator` `a5aaafb`: `scripts/autopilot/preflight_audit.py` now derives live model-server health targets from generated stack-prior serving endpoints and groups shared roles by health URL.
   - Fallback targets are current degraded mode only: no retired `architect_coding`, no dead `8071`, and both VL servers included.
   - Remaining risk: broader AutoPilot/system-card/operator summaries should keep moving to generated stack-prior summaries instead of manual tables.

11. API health no longer owns a stale backend probe pair.
   - RESOLVED in `epyc-orchestrator` `3dc21c5`: `src/api/routes/health.py` now derives live backend probe targets from generated stack-prior `serving.endpoint` / `serving.ports` records with `deployment_status: live_stack`.
   - Shared endpoints are grouped under slash-joined role labels and probed once, so shared frontdoor/coder-style servers do not create duplicate live health checks.
   - CENTRALIZED in `epyc-orchestrator` `91c7cba`: `src/api/routes/health.py` now reaches those records through shared `src/registry/stack_priors.py` helper APIs instead of maintaining a route-local YAML parser.
   - Missing or malformed stack priors retain the old degraded fallback to `frontdoor` plus `architect_general` config URLs.
   - Focused tests cover live endpoint grouping, port fallback, and one-probe-per-shared-endpoint behavior.

12. Chat summarization no longer probes a retired worker.
   - RESOLVED in `epyc-orchestrator` `5b4f683`: `src/api/routes/chat_summarization.py` selects the chunk-digest worker from generated stack priors instead of probing retired `worker_fast` at port 8102.
   - Selection prefers live `worker_summarize`, then other live worker roles, with degraded fallback to `worker_summarize` when stack priors are unavailable.
   - The batch-failure fallback now retries sequentially through the selected live worker instead of forcing `worker_explore`.
   - `tests/unit/test_chat_summarization.py` covers stack-prior worker selection and expects role history to use `worker_summarize`.

13. Parallel step execution no longer assumes a retired warm worker.
   - RESOLVED in `epyc-orchestrator` `cc401c0`: `src/parallel_step_executor.py` derives burst worker roles from generated stack priors instead of hardcoding `worker_fast` / port 8102.
   - Burst eligibility requires `deployment_status: live_stack`, a `worker_` role name, and `serving.tier: warm`; the current live stack has no warm worker burst role, so same-wave execution fails closed to sequential HOT execution.
   - Unknown burst execution and exception reporting now defaults to `worker_general` rather than retired `worker_fast`.
   - CENTRALIZED in `epyc-orchestrator` `d0960b0`: burst worker selection now reuses shared live-role and warm-worker slot helpers from `src/registry/stack_priors.py`.
   - `tests/unit/test_parallel_step_executor.py` covers stack-prior burst-role derivation, missing-artifact fail-closed behavior, and injects an explicit burst role only for the concurrency behavior test.

14. Runtime worker concurrency caps no longer assume fixed small-worker roles.
   - RESOLVED in `epyc-orchestrator` `f41f956`: `src/runtime/concurrency.py` derives concurrent worker caps from generated stack priors instead of hardcoding `worker_fast`, `worker_explore`, or related small-worker role names.
   - Eligibility requires `deployment_status: live_stack`, a role name starting with `worker_`, and `serving.tier: warm`; caps come from `serving.slots` and default to 1 when missing.
   - Missing or malformed stack priors fail closed to no concurrent worker caps. Because the current live stack has HOT workers only, REPL parallel delegation and primitive role semaphores remain single-lane until a future generated stack explicitly promotes a live warm worker.
   - CENTRALIZED in `epyc-orchestrator` `d0960b0`: worker cap derivation now uses shared live warm-worker slot helpers from `src/registry/stack_priors.py`.
   - `tests/unit/test_runtime_concurrency.py` covers stack-prior concurrency derivation, malformed/missing prior fail-closed behavior, and slot defaulting.

15. AutoPilot human program guidance no longer carries dead endpoint examples.
   - RESOLVED in `epyc-orchestrator` `60733c7`: `scripts/autopilot/program.md` now tells autonomous operator sessions to derive compaction endpoints from `orchestration/derived/stack_priors.yaml` instead of copying a static target-port table.
   - Removed the stale coder `8071`, retired coding-architect `8084`, and obsolete fixed-RAM tier-demotion wording from the program prompt.
   - GUARDED in `epyc-orchestrator` `cf73ac1`: `stack_change_guard.py --all-hardcoded-surfaces` now scans `scripts/autopilot/program.md` for stale static target-port, retired-role, and fixed-RAM tier guidance, with unit fixtures proving both the stale and stack-prior-derived cases.
   - Remaining risk: generated system-card/runtime summaries are healthier, but active operator docs and historical chapters still need generated current-stack summaries or explicit historical labels.

16. Production launcher summaries no longer duplicate stale stack inventory.
   - RESOLVED in `epyc-orchestrator` `53f452c`: `scripts/server/launch_production.sh` keeps launch behavior unchanged while deriving its displayed component inventory from `scripts/server/stack_manifest.py`.
   - `--full` prints HOT launch groups from `HOT_SERVERS`; `--with-burst` prints HOT plus WARM launch groups; `--minimal` is now labelled as a legacy HOT-tier alias rather than claiming architects are excluded.
   - Help text points operators at `stack_manifest.py` and `--status` for current inventory/residency instead of carrying hardcoded RAM/model breakdowns.
   - GUARDED in `epyc-orchestrator` `b8a1abc`: `stack_change_guard.py --all-hardcoded-surfaces` now treats stale launch-wrapper static inventory in `scripts/server/*.sh` as a production blocker, including removed `architect_coding`/`8084`, old `Qwen3-Coder-480B`, fixed RAM totals, and old HOT/core wording.
   - Validation: `bash -n scripts/server/launch_production.sh`; launcher `--help`; embedded summary Python compile; stale literal search for removed role/model/RAM strings; focused `test_cli_orch.py` + `test_stack_change_guard.py` -> 25 passed; strict guard OK; all-surface guard shows no production launcher warning.

17. AutoPilot controller-facing stack summary now reads generated stack priors.
   - RESOLVED in `epyc-orchestrator` `603ad6b`: `scripts/autopilot/gen_system_card.py` renders the active `live_stack` role table from `orchestration/derived/stack_priors.yaml` first, including shared aliases and launch port sets.
   - Raw registry role rows are degraded fallback only when stack priors are missing or unreadable; generated `system_card.md` labels the source as stack priors and warns that the retired architect role is not active in stack priors.
   - Tests fixture stale registry entries plus stack-prior data so raw stale registry/candidate rows cannot leak into the controller prompt.
   - Validation: GitNexus impacts LOW for `generate_system_card` and `_render_system_card`; py_compile; `uv run pytest tests/unit/test_autopilot_system_card.py` -> 4 passed; `python3 scripts/autopilot/gen_system_card.py --check`; `stack_change_pipeline.py check --allow-known-gaps` reported descriptors/stack_priors/procedure_enums/guard/strict OK and all-surface warnings classified as legacy-test/historical-doc only.

#### Model-Specific Quantity Audit Matrix

| Quantity | Current state | Canonical source | Required projection / guard |
|---|---|---|---|
| q_scorer TPS, quality, memory priors | DONE in `e3d967a`: live defaults read `stack_priors.yaml`; fallback tables remain for degraded/offline mode. EXTENDED in `9ed177d`: `worker_explore` now inherits stack-prior quality from live `worker_general` aliases instead of falling back only for quality. | `stack_priors.yaml` role `priors` with descriptor evidence and measurement status. | Keep explicit provenance plumbing for live vs degraded fallback scoring; alias quality/TPS/memory should travel together. |
| Seeding reward TPS/cost assumptions | DONE in `7ecf847`: `seeding_rewards.py` reads live `priors.throughput_tps`, keeps explicit override/degraded fallback for replay/tests, and no longer exports the stale baseline table. | Same stack-prior `priors.throughput_tps` plus per-role memory/admission costs. | Keep guard coverage so any future live seeding cost table or retired-role default fails. |
| Seeding scoring/architect assumptions | DONE in `5773777`: active `seeding_eval.py` enumerates live non-VL architect roles from stack priors; `seeding_scoring.py` no longer documents the retired architect split; `seeding_legacy.py` derives slow roles from current `ARCHITECT_ROLES`. EXTENDED in `2e31055`: per-role seeding discovery restores live `worker_vision` and `vision_escalation` coverage from generated stack priors while excluding shared non-default aliases. | Live roles from stack priors; historical benchmark-only comparisons from research registry with non-live status. | Remaining historical/deprecated fixtures should stay explicit legacy/test-only; live benchmark defaults should keep reading stack priors. |
| Memory/admission costs | `src/api/admission.py` derives limits from stack-prior ports/slots with fallback; q_scorer memory now reads stack-prior memory cost first. | `server_mode.*.tier`, `slots`, shared mmap binding compiled into stack priors. | Add tests that frontdoor/coder_escalation share memory and admission truth; fail on role-level WARM overrides for live HOT roles. |
| Hot/warm deployment status | `server_mode` is current truth; older research docs and role metadata still mention WARM `architect_coding`/`ingest_long_context`. | Orchestrator lean registry `server_mode.*`; research registry is comprehensive evidence/candidate history only. | Compiler must preserve conflict notes and prevent non-live research rows from satisfying live deployment. |
| Context size / ctx limits | Effective launch context is now guarded in stack priors (`a001017`): frontdoor 32768, worker aliases 16384, worker_vision 8192, vision_escalation 16384, architect_general 16384, and ingest_long_context 32768. Model-native `ctx_max` remains incomplete in descriptors. | Physical descriptor `model.ctx_max` from research/lean registry, plus launch `-c` effective context from stack manifest. | Extend descriptor contract with `ctx_model_max`; strict mode blocks live consumers that need model-native context limits while null. |
| TPS, latency, reward baselines | TPS partly structured; latency/admission history lives in comments/docs; reward baselines are split across q_scorer, seeding, eval tower, and AutoPilot artifacts. | Measurement-attested descriptor evidence and stack-prior priors; historical benchmark artifacts remain provenance only. | Add provenance status fields: decision-grade, observation, gap, stale. Decision gates must require protocol/date/ref per `MEASUREMENT.md`. |
| Routing priors / role priors | `_heuristic_role_priors()` now filters through live stack priors; `3e4ba7c` keeps chat delegation live valid targets while normalizing legacy/model-generated alias labels before config lookup; learned-routing handoffs/docs still contain `architect_coding` training labels. | Live role set from stack priors; learned/replay datasets must carry era labels. | Add simulated retired-role fixture proving `architect_coding` is ignored in live priors but preserved in historical replay with era metadata; keep compatibility aliases explicit and non-advertised as live targets. |
| OpenAI-compatible model listing | `/v1/models` now derives live model IDs from stack priors plus compatibility aliases; `3e4ba7c` also normalizes OpenAI-compatible ingress aliases such as `coder` -> `coder_escalation` and retired/generated worker labels -> `worker_general` before config lookup. | Stack-prior live roles. | Keep compatibility aliases separate from live role IDs; guard any static live model list. |
| Dashboard/runtime classification | Dashboard age overrides and inference lock/tap had recent cleanup; worker concurrency caps now derive live warm worker slots from stack priors in `f41f956` and reuse shared warm-slot helpers in `d0960b0`; inference lock role classes derive live shared/exclusive classes from stack priors in `822482b`, with unknown roles failing closed to exclusive and explicit `shared=` overrides unchanged, and `dfcd280` moves lock/tap parsing onto shared `stack_priors.py` helpers while preserving fallback constants; API health/chat-vision probe URL readers reuse the same helper layer as of `91c7cba`; scheduling/contention current-role tests are pinned to the real stack matrix in `eed215d` and assert retired `worker_fast` absence from matrix light roles plus same-role `vision_escalation` ALLOW behavior; tap stream roles and some approval-gate high-cost classifications are still local policy tables. | Stack-prior tier/slots/model class plus explicit runtime policy hints. | Compile remaining tap/high-cost/contention policy hints or a generated runtime classification projection; local tables must be fallback/override only. |
| Launch ports and shared servers | DONE for shared aliases in `d4acf24`; active VL ReAct ports now read stack-prior serving records in `06ff53c`; shared `server_mode` alias-port drift is guarded in `40d46ea`; AutoPilot preflight health probes read stack-prior serving endpoints in `a5aaafb`; API health backend probes read grouped live stack-prior serving endpoints in `3dc21c5`; chat summarization chunk-digest worker selection reads live stack-prior workers in `5b4f683`; parallel step executor burst-worker eligibility reads live warm worker records from stack priors in `cc401c0`; AutoPilot human program guidance now derives compaction endpoints from stack priors in `60733c7`; production launcher summaries derive HOT/WARM groups from `stack_manifest.py` in `53f452c`; KV compression `PRODUCTION_PORTS` now uses live role names in `e7fab9d`; stack-prior endpoint/primary-port/tier drift from the computed launch manifest is guarded in `312b28e`; stack priors now hash `stack_manifest.py`/`stack_numa.py` in `a6d1200`; exact per-role launch port sets are projected and guarded in `dc14196`; contract v2 launch-entry witness is projected and guarded in `7917535`; contract v3 effective-context and worker/VL model-path requirements are projected and guarded in `a001017`; test-only `worker_general` MTP and VL command parity witnesses derive expected requirements from stack priors in `b026f7d`; degraded CLI and AutoPilot preflight target/exclusion derivation is current through `3b5a682` and `5f0f248`. | `server_mode` plus generated stack priors should outrank raw port maps. | Guard direct `PORT_MAP` consumers; launch/health probes and operator guidance should consume generated serving records or verified launch metadata. |
| Registry/derived YAML drift | `stack_priors.yaml` has a contract and freshness hash; default `stack_change_pipeline.py check` now reports pass/block state and warning-category summaries after freshness, enum, guard, and strict checks; `ebd929b` makes the printed `promotion_gate:` command include both simulated stack-change fixtures and launcher-helper parity tests; `3a20efd` adds `--run-promotion-gate` to execute those targets after earlier checks pass. | Lean registry + descriptors generated from research evidence. | One workflow command must compile descriptors/priors, sync procedure enums, run strict guard, emit the promotion gate, optionally run it, summarize warning categories, and fail on stale generated hashes or unclassified strict blockers. |

#### Proposed Source-Of-Truth Design

Adopt this rule for every stack/model change:

1. **Edit structured truth only.**
   - Physical model identity and measured evidence: `orchestration/model_descriptors.yaml`.
   - Live serving topology, ports, slots, tiers, shared bindings, and deployment intent: `orchestration/model_registry.yaml` `server_mode.*`.
   - Comprehensive benchmark/candidate history: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`; values imported from here must remain non-live until projected through orchestrator descriptors/stack priors with measurement status.
   - Temporary launch witness until fully generated: `scripts/server/stack_manifest.py` `ROLE_LAUNCH_META`.

2. **Compile exactly one consumer contract.**
   - `orchestration/derived/stack_priors.yaml` is the generated contract for model-specific consumers.
   - It must include role, model id, endpoint/ports/slots, tier/memory cost, TPS/quality/latency/reward priors with measurement provenance, model max context, effective launch context, launch binary, draft/MTP/spec settings, KV settings, modality, shared mmap group, source hashes, and known gaps.

3. **Consume through a typed API, not ad hoc YAML parsing.**
   - Add or extend a small loader, for example `src/registry/stack_priors.py` runtime helpers, so production code can ask for:
     - live roles
     - retired roles
     - role serving record
     - role scorer priors
     - role budget/policy hints
     - launch requirements
     - high-cost/lock/tap classifications
   - Tests and scripts may read YAML directly only when imports would create a cycle; they must still preserve degraded-mode warnings.

4. **Make fallback tables explicit degraded mode.**
   - Fallback constants should be named `DEGRADED_*` or `FALLBACK_*`, must exclude retired live roles unless testing legacy behavior, and must emit or return provenance that says "not live stack truth".
   - Production validators should fail if a live consumer silently accepts fallback values while stack priors are present.

5. **Require data-only simulated swaps.**
   - A model swap is not complete until fixture-based tests prove that changing registry/descriptors regenerates consumer outputs without code edits.
   - Include a retired-role fixture where `architect_coding` is removed from live stack truth and a shared-server fixture where `frontdoor`/`coder_escalation` keep one model identity, one memory owner, and distinct role IDs.

#### Work Packages

##### W1 - Harden the stack-prior contract and guard

Goal: make `stack_priors.yaml` complete enough to be the only model-specific consumer contract.

Tasks:

- DONE foundation in `69057f3`: add an explicit versioned contract plus structural validation for stack priors.
- Extend compiled records with missing consumer fields:
  - context window / effective max context
  - decision-grade TPS and quality status
  - launch binary path/family and runtime incompatibilities
  - draft/MTP/spec decode knobs
  - KV/cache settings
  - shared mmap group id and memory-accounting owner
  - role policy hints needed by API budgets/routing if those remain role-specific
- DONE for launch topology in `a6d1200`: stack priors now include source hashes for `scripts/server/stack_manifest.py` and `scripts/server/stack_numa.py`, and the guard requires those artifacts.
- DONE for exact launch-port projection in `dc14196`: stack priors now use computed launch role ports as the serving port set for live roles, preserve server slot metadata, and reject missing/extra port drift against the launch manifest.
- DONE for launch-entry witness in `7917535`: stack-prior contract v2 requires `serving.launch.entries`, and the guard compares generated launch mode/alias/primary-role/NUMA witness data against the computed launch manifest.
- DONE for launch-context/path witness in `a001017`: stack-prior contract v3 requires
  `serving.effective_context_tokens` and `serving.launch.requirements`; worker
  model/draft paths and VL model/mmproj paths are now generated and guarded.
- DONE for launch-runtime witness in `33c81ff`: stack-prior contract v4
  requires `serving.launch.runtime`; generated priors now witness effective
  launcher binary family/path, runtime requirements, cache/KV settings, slot
  save policy, and launch flags/spec state, and the guard compares them against
  computed launch truth.
- DONE for test-only launcher parity witnesses in `b026f7d`: launcher-helper
  tests derive `worker_general` MTP and VL expected command requirements from
  generated stack priors, proving parity with current generated launch metadata
  without changing startup behavior.
- Add source metadata for research-registry/benchmark evidence where descriptors depend on research artifacts, not just the lean orchestrator registry and launch topology.
- DONE foundation in `e162c7c`: add an external exception allowlist for `stack_change_guard.py` with owner, category, rationale, expiry/review date, and whether the exception is live, degraded fallback, legacy test, or historical doc.
- PARTIAL in `e162c7c`: strict mode now keeps valid waived hardcoded-surface findings visible as warnings instead of promoting them to errors; unresolved descriptor/global-gap policy still needs final strict-mode tightening.

Acceptance:

- `uv run python scripts/registry/compile_stack_priors.py --allow-incomplete` preserves known gaps.
- strict mode can distinguish "blocked live consumer" from "documented fallback" without hiding either.
- changing stack manifest/NUMA launch metadata makes generated stack priors stale until regenerated.
- Adding a retired live role to a production consumer fails the guard.

##### W2 - Migrate highest-risk live consumers

Goal: eliminate model-specific hardcoding from live scoring/routing/config behavior.

Priority order:

1. `scripts/benchmark/seeding_rewards.py`
   - DONE in `7ecf847`: replaced the stale TPS table with stack-prior-derived live throughput.
   - DONE in `7ecf847`: kept explicit override/degraded fallback paths for replay/offline tests without silent live fallback.
   - Treat this as a separate blast-radius pass because `compute_comparative_rewards` was previously marked CRITICAL.
   - Follow-up: wire provenance metadata if downstream injection needs to record live-prior vs override/degraded cost source.
2. `src/api/routes/chat_delegation_decision.py`
   - DONE first cleanup in `b1402a2`: removed `architect_coding` from live budget defaults.
   - DONE follow-up in `80ed046e`: architect/delegation budget maps derive
     live `architect_*` roles from generated stack priors instead of a local
     static table, preserving dynamic compatibility map imports.
3. `src/api/routes/chat_pipeline/delegation_stage.py` and `src/api/routes/chat_pipeline/proactive_stage.py`
   - DONE cleanup in `481516c`: retired `architect_coding` no longer triggers delegated/proactive architect branch behavior.
   - DONE follow-up in `53f12e0`: proactive deep-reasoning triggers such as `/think` and `/ultrathink` now delegate to live `architect_general` instead of the removed dedicated thinking role; `tests/unit/test_proactive_delegator.py` covers the regression.
   - DONE ingress-alias follow-up in `3e4ba7c`: chat delegation parsing keeps
     live valid targets while compatibility aliases normalize legacy labels
     before config lookup.
4. `src/api/routes/chat_routing.py`
   - PARTIAL cleanup in `519f710`: removed the redundant retired-role check from `_role_to_task_type()` and added live-role mapping coverage.
   - DONE HIGH-impact follow-up in `eb4dac5`: `_heuristic_role_priors()` now reads live stack-prior role status before seeding candidate priors, with a non-retired degraded fallback.
5. `src/api/routes/openai_compat.py` and `src/api/routes/dashboard_snapshot.py`
   - DONE cleanup in `d9c053c`: OpenAI-compatible `/v1/models` now reads deployed roles from stack priors and keeps only non-retired degraded fallback roles plus aliases.
   - DONE ingress-alias follow-up in `3e4ba7c`: OpenAI-compatible request
     routing normalizes `coder` to `coder_escalation` and
     `worker_fast` / `worker_coder` / `worker_code` to `worker_general`
     before config lookup while preserving compatibility alias behavior.
   - DONE cleanup in `1b9db81`: dashboard in-flight task age overrides no longer include retired `architect_coding`.
6. `src/config/__init__.py` and `src/config/models.py`
   - DONE in `f24eab7`: removed retired `architect_coding` from active server URL maps, role timeout maps, env-backed settings, and API import expectations.
   - Follow-up: prefer stack-prior endpoints/timeouts where possible for generated config projections, rather than maintaining parallel role maps indefinitely.
7. `src/runtime/inference_lock.py`, `src/runtime/inference_tap.py`, and `src/graph/**`
   - PARTIAL cleanup in `6bc1f51`: removed retired `architect_coding` from inference lock/tap heavy-role classifications.
   - HELPER cleanup in `dfcd280`: lock/tap role and serving lookups now use shared stack-prior helpers instead of duplicate YAML parsing; legacy fallback constants remain unchanged.
   - PARTIAL cleanup in `e6e10d8`: removed retired `architect_coding` from approval-gate high-cost classification.
   - PARTIAL cleanup in `2967526`: `scripts/server/orchestrator_stack.py` now enables only live LangGraph Phase 3 node env vars and no longer sets the retired `ORCHESTRATOR_LANGGRAPH_ARCHITECT_CODING` launch flag.
   - PARTIAL cleanup in `c2b4437`: `src/parsing_config.py` no longer assigns an active parsing strategy to retired `architect_coding`, and `src/inference/llm_cache.py` no longer recommends it as a cache target.
   - DONE in `03ed49f`: `Role.ARCHITECT_CODING` now aliases live `Role.ARCHITECT_GENERAL`; legacy string routing is preserved through `_missing_` / `_LEGACY_ROLE_ALIASES`; active prompt fallback, graph node map, and prewarm special-cases no longer treat coding architect as a separate live role.
   - DONE in `e7fab9d`: legacy tool permission lookup now canonicalizes string roles through live `Role` semantics, so compatibility `"architect_coding"` requests inherit `architect_general` permissions instead of a separate permission row.
   - DONE in `822482b`: runtime inference lock role classes now derive from
     generated live stack priors when available. Live `worker_pool` and
     `worker_vision` use shared locks, retired `worker_fast` is absent from live
     derived `LIGHT_ROLES`, missing/unknown roles fail closed to exclusive locks,
     and explicit `shared=` overrides remain authoritative.
   - DONE in `eed215d`: scheduling/contention role classes are pinned to the
     current real stack matrix. The unused fallback heavy-role constant and
     stale same-role vision comment are gone; tests assert current n-way
     light/heavy role classes, retired `worker_fast` absence from matrix light
     roles, and same-role `vision_escalation` ALLOW behavior.
   - DONE in `c2daef44`: approval-gate high-cost classification now derives
     from stack-prior model memory, with `architect_general` only as degraded
     fallback.
   - Remaining follow-up: tap/streaming classifications are stack-prior-derived
     in runtime code; keep any residual work limited to guard/doc classification
     unless a new live static table is found.
   - Remaining LangGraph retired-role mentions should be legacy-test or historical-doc cleanup only.
8. `scripts/benchmark/seeding_eval.py`, `scripts/benchmark/seeding_scoring.py`, `scripts/benchmark/analyze_routing_policy.py`, and `scripts/benchmark/corpus_quality_gate.py`
   - DONE in `5773777`: live seeding/eval behavior now derives non-VL architect candidates from stack priors, legacy slow-role logic derives from `ARCHITECT_ROLES`, and the corpus quality gate loads current model configs from stack priors.
   - Architect comparisons enumerate live architect-like roles from stack priors and treat removed roles as legacy benchmark fixtures only.
   - DONE in `2e31055`: `scripts/benchmark/seeding_types.py` active-role discovery now prefers generated stack priors, includes live VL roles (`worker_vision`, `vision_escalation`) for eval coverage, excludes shared non-default aliases, and keeps registry fallback for degraded operation.
   - DONE for `analyze_routing_policy.py` in `b5bf5eb`: specialist-utilization summary reads live stack-prior roles and the fallback excludes retired `architect_coding`.
9. `src/parallel_step_executor.py`
   - DONE in `cc401c0`: same-wave burst concurrency now derives live warm `worker_*` roles from stack priors instead of hardcoding retired `worker_fast` / port 8102.
   - Missing or malformed stack priors fail closed to no burst roles; tests inject a burst role explicitly only where parallel behavior itself is under test.
10. `src/runtime/concurrency.py`
   - DONE in `f41f956`: runtime worker concurrency caps now derive live warm `worker_*` records and `serving.slots` from stack priors instead of fixed small-worker role tables.
   - Missing or malformed stack priors fail closed to no concurrent workers; the current HOT-only live worker stack therefore keeps REPL delegation and primitive role semaphores single-lane until generated stack truth changes.
11. REPL delegate/my-role ingress surfaces
   - DONE in `3e4ba7c`: REPL `delegate` and `my_role` no longer advertise
     retired `worker_fast`, `worker_coder`, or `worker_explore` as live
     targets, but legacy labels still resolve to current live roles for
     persisted/generated compatibility.
12. Chat delegation report prompt preambles
   - DONE in `6ec2686`: compact specialist report preambles now canonicalize
     through `_normalize_delegate_role`. Direct preamble role sets advertise
     only live `coder_escalation` and `worker_general`; legacy `worker_coder`,
     `worker_explore`, and `worker_fast` aliases remain accepted but render
     live-role prompt text rather than retired labels.
13. Architect investigation prompt templates
   - DONE in `09948db`: the active architect investigation prompt template,
     fallback constant, and architect system example now name live roles only:
     `coder_escalation` for implementation/file-split delegation and
     `worker_general` for investigation/search. Prompt-builder tests assert the
     resolved architect investigate prompt contains those live roles and omits
     retired `worker_coder`, `worker_explore`, and `worker_fast`.
14. Output formalizer worker routing
   - DONE in `4bf8061`: `_formalize_output` now sends final formatting work to
     live `worker_general` instead of the retired/legacy `worker_explore`
     label. The helper docstring dropped stale model speed/port assumptions and
     coverage asserts the role passed to `llm_call` is `worker_general`.

DONE in `d6912e7`: q_scorer now exposes live/degraded provenance metadata. Follow-up, if strict promotion needs a harder failure mode, is to make selected production callers reject `PRIOR_SOURCE_DEGRADED_FALLBACK` for required live roles instead of only inspecting metadata.

Acceptance:

- `stack_change_guard.py --all-hardcoded-surfaces` production-blocker count drops materially after each pass.
- q_scorer, seeding reward costs, routing priors, admission limits, procedure role enums, and API examples all agree on the same live roles.
- `architect_coding` remains only in historical docs, retired compatibility tests, or explicit legacy fixtures.

##### W3 - Build the repeatable stack-change workflow

Goal: one command sequence for safe model changes, usable by the main agent or a human operator.

Tasks:

- Add a no-inference stack-change workflow script or documented command target that runs:
  - descriptor compile/check
  - stack-prior compile/check
  - procedure enum sync check
  - stack-change guard strict mode
  - consumer snapshot tests
  - simulated model-swap tests
  - source/derived artifact freshness checks
- DONE in `d5cb80a`: descriptor freshness checks now show exact changed model IDs/field paths, generated add/remove model IDs, and top-level drift before the stale-artifact error.
- DONE in `4ca702d`: descriptor update/check paths now fail closed on generated role/server conflict gaps instead of suggesting or performing an unsafe artifact update.
- DONE in `a7b72a9`: `src/registry/model_descriptors.py` now treats `server_mode.shared_with` aliases with different role-level models as virtual aliases served by the primary runtime descriptor. The generated artifacts intentionally remove standalone live Qwen math/toolrunner descriptors while preserving alias coverage and known-gap notes. GitNexus marked `compile_model_descriptors` and `_descriptor_for_role` HIGH through the launch-adjacent stack command path, so the fix landed with focused descriptor, stack-prior, pipeline, schema, q_scorer, routing, vision, preflight, and CLI tests.
- DONE in `fb0fd6d`: add fixture-based simulated swaps:
  - shared-mmap role swap, e.g. frontdoor/coder_escalation same-GGUF group
  - worker-family swap with launch requirements, e.g. gemma4 worker MTP/ik binary
  - retired-role removal, e.g. `architect_coding`
- DONE in `837829f`: project architect quality from structured registry evidence
  into descriptors and stack priors; `architect_general` and
  `qwen35_122b_q4km` now carry `quality_overall: 0.8567` and no longer have a
  quality known gap.
- DONE in `03ed49f`: close the temporary retired-role enum production-waiver path by normalizing `Role.ARCHITECT_CODING` to live `architect_general`, preserving legacy string compatibility, and removing distinct-live-role prompt/graph/prewarm surfaces.
- DONE in `e7fab9d`: normalize stale role runtime surfaces in KV adaptive compression and legacy tool permissions. KV layer fallbacks now use current shared frontdoor evidence for `coder_escalation`/`worker_summarize`, retired architect layer entries are inactive, roles without current layer evidence fall back to uniform compression, and `ToolRegistry` compatibility strings canonicalize through `Role.from_string()`.
- Add pre-launch and post-launch gates:
  - pre-launch: strict stack-change guard must pass or require an explicit diagnostic override
  - launch: launcher consumes generated launch requirements where available
  - post-launch: running-state attestation compares live PIDs/ports/flags/binary paths against stack priors
- DONE in `0573e02`: `orchestrator_stack.py status` performs read-only live cmdline attestation for concrete GGUF model paths and warns on `model-drift`.
- DONE in `3bdd506`: stack status now loads generated stack-prior launch requirements for VL projector paths and extends live cmdline attestation to expected `--mmproj` arguments, warning with `mmproj-drift` on missing or mismatched projectors.
- DONE in `8bad5e9`: stack status now uses the same generated launch-contract path as the runtime attestation gate, so `orchestrator_stack.py status` surfaces runtime flag/cache/spec drift such as stale context size, `--flash-attn`, or speculative-draft flags instead of only model/mmproj drift.
- DONE in `3e8121d`: `role.model.mmproj_path` now compiles into descriptor
  `serving.requirements.mmproj_path`, so Qwen2.5-VL and Qwen3-VL projector
  dependencies are descriptor-native before stack-prior regeneration.
- DONE in `d59029a`: `_scan_known_ports()` unions `PORT_MAP.values()` instead
  of hardcoding native auxiliary ports, and unit coverage verifies
  manifest-only auxiliary ports are included in status scanning.
- Generate or refresh operator-facing stack summaries from stack priors so manual docs do not become source truth.
- DONE in `53f452c` for one production wrapper: `launch_production.sh` derives its mode summary from `stack_manifest.py` instead of carrying stale model/RAM/retired-role text.
- DONE in `b8a1abc`: `stack_change_guard.py --all-hardcoded-surfaces` now blocks reintroducing stale launch-wrapper static inventory in `scripts/server/*.sh`.
- DONE in `603ad6b` for the AutoPilot controller prompt: `gen_system_card.py` renders active live-stack rows from stack priors first and keeps raw registry role rows as degraded fallback only.
- DONE in `6cfb2c7`: the generated AutoPilot system card now includes compact launch requirements from stack priors, surfacing VL `mmproj` and MTP/draft dependencies without requiring the planner/controller to parse raw YAML.
- DONE in `5b4f683`: chat summarization chunk-digest selection now reads live
  worker roles from stack priors instead of probing retired `worker_fast` at
  port 8102, and sequential retry fallback stays on the selected live worker.
- DONE in `ee39cbe7` (2026-07-23): `src/graph/session_log.py` session-summary /
  scratchpad extraction was the MISSED sibling of the `5b4f683`/`cc401c0`
  class — raw-keyed `role="worker_fast"` bypassed alias normalization to dead
  8102 (autopilot checkpoints showed the lane returning 0 tokens). Now selects
  from live stack priors (worker_summarize-first) and `[ERROR`-prefixed
  responses fall back to the deterministic summary. Found by the 2026-07-23
  stack-lineup archaeology ([stack-lineup-dossier-2026-07-23.md](../archived/stack-lineup-dossier-2026-07-23.md) §3).
- DONE in `cc401c0`: parallel step executor same-wave burst eligibility now
  reads live warm `worker_*` roles from stack priors, defaults unknown role
  reporting to `worker_general`, and fails closed to sequential execution when
  the generated live stack has no warm worker burst role.

Acceptance:

- A model assignment can be changed in structured inputs, generated artifacts update, and no live consumer requires hand-editing.
- Launch refuses stale generated priors unless an explicit diagnostic override is present.
- Runtime attestation detects stale running processes after config/code changes.
- Repeating the 2026-06 `architect_coding` retirement or q_scorer-cost drift pattern is impossible without a failing guard: retired roles are absent from live priors, shared mmap roles do not double-count cost, and live cost/TPS/context consumers either read the generated contract or declare degraded fallback.

#### Validation Strategy

No inference is required for W1-W3 until a later benchmark gate explicitly requests it.

```bash
cd /mnt/raid0/llm/epyc-orchestrator

python3 -m py_compile \
  src/registry/stack_priors.py \
  scripts/registry/compile_stack_priors.py \
  scripts/registry/sync_procedure_role_enums.py \
  scripts/validate/stack_change_guard.py \
  scripts/registry/compile_descriptors.py \
  src/registry/model_descriptors.py \
  orchestration/repl_memory/q_scorer.py \
  scripts/benchmark/seeding_rewards.py

uv run python scripts/registry/compile_descriptors.py --dry-run --allow-incomplete
uv run python scripts/registry/compile_stack_priors.py --allow-incomplete
python3 scripts/registry/sync_procedure_role_enums.py --check
uv run python scripts/validate/stack_change_guard.py
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --strict

uv run --with pytest pytest -q \
  tests/unit/test_stack_priors_compiler.py \
  tests/unit/test_stack_change_guard.py \
  tests/unit/test_sync_procedure_role_enums.py \
  tests/unit/test_model_descriptors_schema.py \
  tests/unit/test_model_descriptor_compiler.py \
  tests/unit/test_q_scorer.py \
  tests/unit/test_admission.py

git diff --check
```

Use focused extra tests for each W2 consumer pass. Do not run AutoPilot or llama inference while implementing this handoff unless a later explicit benchmark/attestation step requires it.

#### Non-Goals

- Do not restart AutoPilot or run inference as part of this audit handoff.
- Do not design a second registry. The point is to make descriptors, lean registry `server_mode`, stack manifest launch metadata, and generated stack priors cohere.
- Do not rewrite all historical docs. Historical references should be labeled or generated separately; production launch should not depend on them.
- Do not suppress guard findings without owner/rationale/expiry metadata.
- Do not reopen learned-routing expansion work. Routing-truth restoration remains frozen until the measured gates in the routing handoffs justify expansion.
- Do not edit master or sub-index files during implementation except in a deliberate doc-sync pass.

#### Reporting Instructions

- Update this handoff when an audited failure mode is closed, reclassified, or assigned an explicit exception.
- Update `stack-change-governance-pipeline.md` only for waypoint progress and validation results.
- Keep `master-handoff-index.md`, `routing-and-optimization-index.md`, and `model-capability-descriptors.md` out of incidental edits; those have broader blast radius and should be synchronized deliberately.
- Progress notes should include exact commands, guard warning counts before/after, and whether AutoPilot/inference was paused.

#### Progress checklist

- [x] W1 stack-prior contract + guard hardening (contract v4, launch/runtime witnesses, source hashes) ✅
- [x] W2 high-risk consumer migrations (q_scorer, seeding, routing, config, health, autopilot - ~29 cleanups) ✅
- [x] Residual classified docs/tests cleanup (legacy_test=72, historical_doc=25 warning buckets) ✅ 2026-07-22
- [x] Descriptor ctx_model_max contract extension (native ctx_max still incomplete) ✅ 2026-07-22
- [ ] **Is promotion-gate coverage insufficient?** (the actual open question behind the conditional "direct benchmark runtime enforcement" row, mainB 2026-08-12). Enumerate every benchmark runtime entry point (bench_canonical, llama-bench wrappers, autopilot preflight, direct launches in scripts/) and record for each whether it passes through the canonical gate. Decision: any bypass that can produce a ratification-bearing number -> file the enforcement task with that path named; none -> close this row. Read-only, one session.
  **2026-08-12 (`mainB`) — screened and NOT actionable as written: the row is CONDITIONAL and its
  condition has never been assessed.** "Only if promotion-gate coverage proves insufficient" is a
  gate, not a task; nobody has established insufficiency, so the work it authorises is not yet
  authorised. Whoever picks it up should first answer *is promotion-gate coverage insufficient?* —
  that is the actual open question, and it is a different (and cheaper) piece of work.
- [x] Remaining tap/high-cost/contention policy-hint projection into generated stack priors ✅ 2026-07-22

- [ ] (620 follow-up — deferred, operator-gated) Wire a compile-blocking strict known-gap for null `ctx_model_max` in `_descriptor_gaps`. Deliberately NOT done in `13112f77` (the field extension) because it would flip the strict promotion gate to error for every not-yet-populated model on the launcher path (CRITICAL blast radius). Populate native `ctx_max` first, then enable.
- [x] **scripts.server circular-import fail-open flake** (filed 2026-07-24): `runtime_facts_manifest`/`stack_paths`/`stack_manifest` raise partially-initialized ImportErrors under several entry orders (visible as `runtime-facts selected-servers read failed (ImportError: cannot import name ...)` WARNs in orchestrator_stack/dashboard/eval output; made `expected_stack_services()` fall open to the unfiltered list inside pytest — documented in-test in `test_dashboard_helpers.py::test_expected_stack_services_are_numa_mode_filtered`). Untangle the import cycle so stack-truth readers import cleanly from any entry point; the fail-open then stops masking filter behavior. ✅ 2026-10-29 (audit: box note "Closed 2026-09-07 on independently re-run evidence": imports clean, degraded paths warn, orchestrator 48a685f0 with 6 tests) [no-belief: audit-reconciliation]
  **2026-08-12 (`mainB`) — the CYCLE IS ALREADY GONE; the fail-open it justified was not.** Re-derived:
  3 bare imports and 4 package-order imports of `runtime_facts_manifest` / `stack_paths` /
  `stack_manifest` / `orchestrator_stack` all import cleanly, so the row's stated cause no longer
  reproduces (the `scripts/server/` → `src/config/` move is the likely fix). What remained was the
  residue: `expected_stack_services()` logged BOTH degraded paths at `logger.debug` —
  filter-failure → unfiltered list (other modes' ports render as "expected"), manifest-unavailable →
  `[]` (renders as a healthy empty stack). Silence is what made them masks. Both now warn, naming the
  substitution and the cause; the fail-open is KEPT because dropping the panel is worse than
  over-reporting it. orchestrator `48a685f0`, 6 tests incl. a negative control that the healthy
  path stays silent and a pin that the cycle stays fixed.
  **Left open deliberately:** the literal ask is "untangle the import cycle", which I did not do — I
  found it already untangled. Owner closes on the evidence, not on my say-so.
  ✅ Closed 2026-09-07 on independently re-run evidence: `stack_manifest`, `stack_paths`,
  `runtime_facts_manifest` and `orchestrator_stack` all import cleanly from a fresh interpreter
  (cycle confirmed gone, matching the 2026-08-12 re-derivation); the residue — both degraded paths
  now warn, naming the substitution and the cause — landed in `48a685f0` with 6 tests including the
  negative control. Row's literal ask (untangle) satisfied by prior state; fail-open retained
  deliberately because dropping the panel is worse than over-reporting.

## Track: standardized-stack-update-pipeline-finalization
<!-- gate: none -->

> Folded from `handoffs/active/standardized-stack-update-pipeline-finalization.md` @ `05e2b812a086` on 2026-11-02 (BRF-T1-F4, route 1a, operator D1/D5; retired row RTG-38 → RTG-36). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Standardized Stack Update Pipeline Finalization

**Status**: PARTIAL IMPLEMENTATION LANDED - canonical stack-change command and
promotion gates are live. Generated-contract and guard checks are clean.
Runtime-attestation checks can still stop during intentionally isolated
clean-window measurements that bind stack ports; the latest frontdoor G11
measurement window caused such a stop while active, then exited without a
claim-grade aggregate. A rerun after that exit returned `summary: ok`.
Remaining work is high-risk consumer migrations and opportunistic W4 swap-CI.
**Lifecycle**: superseded — consolidated into the authoritative pair [`model-stack-single-source-update-pipeline.md`](stack-lifecycle-program.md#track-model-stack-single-source-update-pipeline) (consumer-SSoT) + [`stack-change-governance-pipeline.md`](stack-lifecycle-program.md) (command/gates). Remaining work (W4 swap-CI, high-risk consumer migrations) is co-tracked there — no unique one-time work here. Per [`stale-open-audit-2026-07-18.md`](frontier-lab-automation.md#track-stale-open-audit-2026-07-18) finding #5. Hard-archive to `completed/` pending operator OK.
**Created**: 2026-06-13
**Priority**: HIGH - stale model-specific constants can corrupt scoring,
routing, launch, planner context, and benchmark interpretation after stack
changes.
**History**:
[standardized-stack-update-pipeline-finalization-history-2026-06-15.md](../archived/standardized-stack-update-pipeline-finalization-history-2026-06-15.md)
preserves the completed chronology compacted out of this active handoff.
**Related**:
[model-stack-single-source-update-pipeline.md](stack-lifecycle-program.md#track-model-stack-single-source-update-pipeline),
[stack-change-governance-pipeline.md](stack-lifecycle-program.md),
[model-stack-update-pipeline-audit.md](stack-lifecycle-program.md#track-model-stack-update-pipeline-audit),
[model-stack-change-standardization-audit.md](../completed/model-stack-change-standardization-audit.md),
[model-capability-descriptors.md](routing-program.md#track-model-capability-descriptors),
[routing-truth-restoration.md](../completed/routing-truth-restoration.md),
[fable5-findings-01-measurement-and-integrity.md](../completed/fable5-findings-01-measurement-and-integrity.md)

#### Purpose

Finish the standardized pipeline that makes orchestration model/serving changes
safe:

1. structured stack truth changes first;
2. generated descriptors, stack priors, and operator summaries refreshed from
   that truth;
3. all known model-specific consumers validated;
4. production launch, AutoPilot resume, and benchmark preflight blocked when
   live model facts drift from generated truth.

Do not create a second registry or guard system. Extend the current
descriptor -> stack-prior -> guard -> consumer-migration path.

#### Current Baseline

- Canonical command:
  `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate`
  in `epyc-orchestrator`.
- Default check after Orchestrator `9dcfbf5` was green:
  `stack_manifest_registry: ok`, `runtime_attestation: ok`,
  `q_scorer_priors: ok`, and descriptors/stack priors fresh. The 2026-06-20
  N11a migration checks that failed runtime attestation did so only while the
  isolated K-MEM Tulving listener owned port `8080`; that listener is now gone,
  so future full-pipeline checks should expect runtime attestation to run again.
- Generated descriptors and stack priors are `status: compiled`; stack-prior
  role `known_gaps` are empty.
- Current all-surface warning baseline: clean. Orchestrator `d459f46` labeled
  the last retired-role launch test as intentional legacy coverage, and
  `stack_change_pipeline.py check --run-promotion-gate` now reports
  `guard_all_surfaces: ok`.
- 2026-06-21 A9 follow-up `3693f6c7` restored that clean baseline after the
  offline reward verifier tests intentionally added historical
  `architect_coding:delegated` remap fixtures. The fixtures now carry exact
  `stack-change-guard: allow` markers, `guard_all_surfaces: ok` is restored,
  `stack_change_pipeline.py check --run-promotion-gate` passed, and the
  executable promotion gate reported `174 passed`.
- 2026-06-28 currentness recheck: `stack_change_guard.py
  --all-hardcoded-surfaces` returned OK; `stack_change_pipeline.py check`
  returned `summary: ok` with `guard_all_surfaces: ok`, `guard_strict: ok`,
  `runtime_attestation: ok`, and `acceptance: no-inference checks passed`;
  surface inventory remained `consumer_surface_count=13`, `rule_count=27`;
  `orchestration/stack_change_guard_exceptions.yaml` remained
  `exceptions: []`; and the no-inference promotion gate passed `176` tests.
  This found no live N11 consumer-migration gap to patch while AutoPilot is
  accruing W6 evidence.
- 2026-07-04 currentness repair: `stack_change_guard.py
  --all-hardcoded-surfaces` caught stale generated stack-prior source metadata
  for `scripts/server/orchestrator_stack.py` (`source_artifacts` expected the
  previous launcher hash). Regenerating through the canonical
  `stack_change_pipeline.py update` path refreshed descriptors, stack priors,
  procedure enums, and the generated operator summary without semantic role
  diffs. The follow-up `stack_change_pipeline.py check --run-promotion-gate`
  returned `summary: ok` and the promotion gate passed `181` tests.
- 2026-07-05 source-fingerprint repair: after Orchestrator `01d14301`
  changed the launcher NUMA default, `stack_change_guard.py
  --all-hardcoded-surfaces` again caught stale `source_artifacts` metadata for
  `scripts/server/orchestrator_stack.py`. Orchestrator `a0377110` regenerated
  descriptors, stack priors, and the generated operator summary through the
  canonical pipeline. The diff was metadata-only: compiled timestamps, source
  commits, source hashes, and summary fingerprints; no role rows, ports, tiers,
  launch requirements, or procedure enums changed. The follow-up
  `stack_change_pipeline.py check --run-promotion-gate` returned `summary: ok`,
  `guard_all_surfaces: ok`, `guard_strict: ok`, `runtime_attestation: ok`, and
  promotion gate `181` tests passed.
- 2026-06-19 descriptor drift from the research registry hash was repaired
  through the canonical `stack_change_pipeline.py update` path. The generated
  diff was limited to `model_descriptors.yaml` / `stack_priors.yaml`
  source-artifact metadata and `check --run-promotion-gate` returned
  `summary: ok` with 172 tests passing.
- 2026-06-19 recheck after the X-MAS reporting and KB-RAG manifest-prune
  commits again returned `summary: ok`: descriptor/stack-prior/procedure/operator
  artifacts fresh, `guard_all_surfaces: ok`, `runtime_attestation: ok`, and the
  executable promotion gate passed 172 no-inference tests. No pipeline code
  changes were needed for N11 in this pass.
- 2026-06-19 high-risk N11a consumer migration landed in Orchestrator `911b880`:
  stack-prior primary-port selection is centralized in
  `stack_prior_primary_port()` and direct endpoint-first fallback consumers
  (`orch status`, corpus gate model discovery, GraphRouter fleet discovery, and
  AutoPilot preflight target grouping) now share that helper. Consumers with
  intentionally different precedence, such as worker-pool port-first binding and
  stack-summary rendering, were left unchanged.
- 2026-06-19 W4 swap-CI expansion landed in Orchestrator `6c9ac6b`: the
  simulated worker swap fixture now proves the text-side primary-port consumers
  migrated in `911b880` (`orch status`, corpus quality gate discovery,
  GraphRouter fleet loading, and AutoPilot preflight health grouping) all read
  the same generated `stack_priors.yaml` primary port after a data-only stack
  change.
- 2026-06-19 follow-up migrations after `6c9ac6b` removed or constrained
  several remaining stack-prior consumers: OpenAI `/v1/models` helper ordering,
  chat-completions degraded fallback role order, stack-monitoring and
  slot-query consumers, dashboard service hints, and seeding reward descriptor
  fallback. A read-only `health_preflight_probes` audit found no further
  duplicate role/port table to migrate in AutoPilot preflight.
- 2026-06-20 WorkerPool follow-through landed in Orchestrator `1a8cb729` and
  `b0150e1c`: runtime worker-pool config now uses shared stack-prior
  primary-port selection and generated launch requirements for worker model
  paths. The stack-prior compiler and guard both honor explicit
  `server_mode` launch-path overrides on top of stack-manifest defaults, and
  the simulated worker swap fixture proves a data-only worker model/port swap
  reaches WorkerPool. `stack_change_pipeline.py check` returned `summary: ok`
  and the executable promotion target passed 174 no-inference tests.
- 2026-06-19 W4 swap-CI follow-up landed in Orchestrator `7a90924`: the
  simulated worker swap fixture now also proves seeding reward degraded
  fallback reads swapped model descriptor throughput before the legacy static
  table.
- 2026-06-19 high-risk generated-stack-docs cleanup landed in Orchestrator
  `95a23aa`: the final raw-registry degraded fallback in
  `render_stack_summary.py:registry_role_rows` now emits only canonical current
  roles or generic chain aliases resolved to canonical roles, and skips retired
  serialized aliases or arbitrary auxiliary server names.
- 2026-06-19 AutoPilot system-card fail-closed cleanup landed in Orchestrator
  `523cb02`: `_render_system_card()` no longer falls back to checked-in
  `system_card.md` when live generation breaks. The degraded card blocks stale
  planner/operator stack truth by explicitly marking live role, port, tier,
  throughput, baseline, and trust-boundary facts unavailable until
  `gen_system_card.py --check` passes again.
- 2026-06-19 admission degraded-fallback cleanup landed in Orchestrator
  `3007610`: `src.api.admission` still uses generated stack-prior slot limits
  as primary truth, but empty/bad priors now fall back to computed stack-manifest
  launch records at controller construction time instead of an import-time
  static URL table. Embedding services are skipped so they do not become
  request-admission gates.
- 2026-06-19 benchmark seeding topology fallback cleanup landed in Orchestrator
  `93722b1`: `scripts.benchmark.seeding_types` still uses generated stack
  priors for default roles, role ports, heavy ports, and model ports, but the
  degraded fallback now derives topology from lean-registry `server_mode`
  records instead of preserving a separate static current-stack role/port table.
- 2026-06-20 high-risk vision-serving consumer migration landed in Orchestrator
  `c9d499f`: `src.api.routes.vision_serving` now derives the live vision role
  set from generated stack-prior launch metadata, and `chat_vision` plus
  `chat_pipeline.vision_stage` consume that helper for VL endpoint/role
  resolution. Legacy `VISION_ROLES`/VL port constants remain degraded fallback
  compatibility only; valid generated priors with no vision launch roles do not
  silently re-enable legacy vision roles.
- Guard inventory currently reports `consumer_surface_count=13` and
  `rule_count=27`.
- Active operator topology docs were refreshed in `8221971`, `d94954a` marked
  remaining retired-role doc mentions as historical notes, and `7ad5965` moved
  legacy seed fixtures to exact inline allowances.
- W4 promotion-gate execution/failure coverage landed in Orchestrator
  `d9fd1eb`; system-card swap visibility landed in `4aed83d`;
  health/dashboard stack-prior witnesses landed in `8beaf79`; representative
  routing/API role-surface witnesses landed in `edd20f7`; stack-manifest vs
  registry drift gating landed in `3c18a17`; swap-CI can still be broadened as
  new high-risk consumers are migrated. Long-context ingest swap-CI coverage
  landed in `63b8612`, proving generated descriptors, stack priors, operator
  summary, system card, health/dashboard endpoint hints, q_scorer priors, and
  promotion-gate execution move together for `ingest_long_context`. Orchestrator
  `cacd8c44` broadens the same simulated swap fixture to factual-risk role
  capability tiers, proving worker, vision, and long-context swaps update
  `src.classifiers.factual_risk` through regenerated stack priors instead of
  static degraded role defaults.
- 2026-07-06 consumer-tail integration: Orchestrator `4bf414d6` folds the
  parked factual-risk degraded fallback cleanup back into the main stack SSoT
  line. The live/generated role-tier path remains primary; the explicit degraded
  role-tier compatibility table is now isolated behind `_degraded_role_tier()`
  rather than a module-level mapping that can be mistaken for live stack truth.
  Validation passed with `test_factual_risk.py` (`51 passed`), focused
  `py_compile`/`ruff`, and the canonical `stack_change_pipeline.py check
  --run-promotion-gate` (`summary: ok`, promotion gate `181 passed`).
- 2026-07-06 DS-7 guard integration: Orchestrator `464aca54` makes
  `stack_templates/default.yaml` fail validation when deployable role ports
  drift from generated live stack-prior serving ports. Logical aliases remain
  valid only when the alias target serves the generated alias ports; experimental
  templates are not forced to mirror production priors. Validation passed with
  `test_dynamic_stack.py` + `test_stack_templates_v2.py` (`47 passed`),
  `orchestrator_stack.py start --stack-profile default --validate-only`,
  `stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces`, and
  `stack_change_pipeline.py check --run-promotion-gate` (`181 passed`).

#### Outstanding Work

- [x] **SS-BENCH-GATE — a stack reload must check for a running CPU bench, not just autopilot.** ✅ 2026-10-29 (audit: all children [x]: -a orchestrator 237f16f0 (guard_against_running_bench live at orchestrator_stack.py:3298), -b bench_core_claim.py 2026-08-23, -c worker_pool _start_worker 2026-08-23, residuals + test fix) [no-belief: audit-reconciliation]
      **Incident 2026-07-27**: an operator-authorized `orchestrator_stack.py reload orchestrator`
      killed the Laguna Q4 CPU bench **1h09m into a decision-gating run**. The reload spawned an
      accelerated sidecar (PID `1202069`, 15:51:42) on cores the bench had pinned, and the bench's
      *campaign continuity gate* invalidated the run:
      `campaign continuity gate failed: production stack continuity invalid: accelerated sidecar
      1202069 overlaps CPU bench cores: [0, 1, 2, ...]`.
      The precondition that was checked — "autopilot is down" — is **not the relevant gate**; the
      gate keys on **core overlap** with a pinned bench. Two things to land:
  - [x] SS-BENCH-GATE-a — **LANDED** ✅ 2026-07-27 (orchestrator `237f16f0`).
        `orchestrator_stack.py` start/stop/reload now call `guard_against_running_bench()`, which
        detects a live bench driver (`*_bench_runner.py`, `v7_quality_gate_runner.py`, `llama-bench`,
        `run_e8_quality_baseline_reseed.py`), prints the incident context, and exits 2 unless
        `--allow-during-bench` is passed. `earlyoom` is excluded — it merely names `llama-bench` in
        its arguments. **Verified live on first run**: it caught the E8 quality baseline reseed
        (PID 1485364) and the v7 quality gate.
  - [x] SS-BENCH-GATE-b — Pin the orchestrator fleet (including transient sidecars) off the CPU
        bench core range so a reload cannot trip the gate at all. This is the durable fix; (a) is the
        guard rail. ✅ 2026-08-23 — `scripts/server/bench_core_claim.py`: the launcher reads the live
        bench driver's ACTUAL thread core sets from /proc (fail-closed on malformed/unstable;
        unobservable = busy), and every spawn (start/reload/aux/sidecar, 6 Popen sites + 5 wrappers)
        is either pinned off the claim (`host_cores − claim`, e.g. bench 0-95 → sidecar `96-191`)
        or refused (exit 2) unless `--allow-during-bench`; default-affinity spawns (the incident's
        sidecar shape) are pinned rather than refused so the stack stays functional during a bench.
        60 new tests + 95 reload/stack tests + 489 stack suite green.
  - [x] SS-BENCH-GATE-c — Extend the same guard to the API's OWN runtime spawn layer (llama-servers
        spawned by the running API with default affinity, not through the CLI launcher). ✅ 2026-08-23 —
        spawn-site map produced; the ONE API-runtime spawn site is `src/services/worker_pool.py:392
        _start_worker` (WARM-expansion/on-demand, `numactl --interleave=all` — the incident's
        default-affinity shape). `bench_core_claim.py` gains `api_enforce_placement()` +
        `ORCHESTRATOR_ALLOW_DURING_BENCH` env knob (evaluated at spawn time; bypasses refusals only,
        pinning still applies; WARNING-logged); `_start_worker` now uses a bench-guarded prefix
        (pins to `host_cores − claim` when a bench is live, refuses otherwise). Quiet path
        byte-identical (proven by tests). 69 bench-claim + 179 worker-pool/backends + 70 model-server
        tests green; ruff clean. The incident's sidecar class is now covered at BOTH layers (CLI -b,
        API -c).
  - [x] SS-BENCH-GATE-c residuals — `src/inference/model_server.py` `LlamaCppBackend` (legacy
        per-inference llama-completion, `numactl --interleave=all`, CLI-only today) and
        `src/services/lightonocr_llama_server.py` per-request llama-mtmd-cli spawns (separate
        launcher-owned service) are the same incident class but not API-runtime-reachable; guard
        them IF either path re-wires into the API. Filed 2026-08-23. ✅ **DONE 2026-08-23** — both
        guarded anyway (cheap insurance, same `api_enforce_placement` pattern): `LlamaCppBackend`
        replaces the numactl default-affinity prefix with `taskset -c <host_cores − claim>` when a
        bench is live (refuses fail-closed on unobservable/refusal); `LlamaOCRWorker` prepends the
        same pin to the asyncio exec (503 on refusal). Quiet paths byte-identical (tests). 14 -c
        tests + 103 worker/model-server tests green.
  - [x] Fix the pre-existing `test_runtime_flag_spec.py` failures (3, `prefix_stable_order` spec
        parity drift) discovered 2026-08-23 while running the stack suite — imports only
        `src/runtime_flag_spec` + `src/features`, untouched by the -b change; predates it.
        ✅ 2026-08-23 — `prefix_stable_order` is the RTE-Prefix flag (default-off, `src/features.py:204`);
        spec re-synced via the sanctioned `runtime_flags_drift.py --sync-spec` (spec header forbids
        hand-editing names) — one `baseline` line added in sorted position; 22/22 spec tests green;
        drift proof clean. The 38 live-file drift findings (10 undeclared_override on
        architect_delegation/plan_review/skillbank…) are pre-existing and remain the stack-owning
        session's triage — unchanged by this fix.


- [x] Keep the `waived_production_blocker` mechanism empty by default and
  fail-closed: any future waiver must be intentional, owned, expiring, and
  removed as soon as compatibility no longer needs it. Current guard state has
  no active waivers (`orchestration/stack_change_guard_exceptions.yaml`
  contains `exceptions: []`) and `stack_change_pipeline.py check` reports
  `guard_strict: ok`. Orchestrator `5bfab0a7` hardens this from convention to
  enforcement: documented `production_blocker` surface waivers now fail closed
  unless `stack_change_guard.py` / `stack_change_pipeline.py` is run with
  `--allow-production-blocker-waivers`, leaving any accepted emergency waiver
  visible as `hardcoded_surface.waived.production_blocker`.
- **[declined: ws58 2026-11-03 content-review: standing constraint, explicitly "not a dispatchable task"; stays readable here]** *(STANDING CONSTRAINT — not a dispatchable task; do not flip. `auditor` 2026-07-29.)*
      Continue high-risk consumer migrations only after focused GitNexus impact
  checks. Use the stack-change surface manifest to pick the next consumer.
  Latest completed slices: Orchestrator `95a23aa` canonicalized the
  generated-stack-docs raw-registry degraded fallback, `523cb02` made AutoPilot
  system-card generation fail closed instead of reusing checked-in stale
  guidance, and `3007610` moved admission degraded fallback URL/slot limits to
  computed stack-manifest truth; `93722b1` moved seeding degraded benchmark
  topology fallback to registry-derived truth. Remaining slices should continue
  to distinguish de-duplication from deliberate precedence changes. As of the
  2026-06-28 currentness recheck, this is opportunistic-on-new-finding rather
  than an already-identified open code migration.
- [ ] Finish W4 swap-CI so representative stack changes prove generated
  descriptors, stack priors, q_scorer priors, operator summary, promotion-gate
  execution, and selected consumer witnesses move together. The simulated
  frontdoor swap fixture now also exercises promotion-gate execution in the
  same swapped state, and representative worker, vision, and long-context ingest
  swaps now cover distinct live role classes. The worker swap also covers the
  migrated text-side primary-port consumers after `6c9ac6b`, the seeding
  descriptor degraded fallback after `7a90924`, and factual-risk role-tier
  consumption after `cacd8c44`; `4bf414d6` keeps that factual-risk degraded
  fallback compatibility explicit. The remaining gap is opportunistic expansion
  as new high-risk consumers are migrated rather than a missing end-to-end
  happy-path proof. Absorbs the "broaden swap-CI opportunistically" row: new witness surfaces are added only when a migrated consumer creates one. Done when every role class in the live lineup (frontdoor, architect, critic, worker, vision, speech, long-context ingest) has one simulated swap fixture that proves descriptors, priors, q_scorer priors, summary and gate execution move together.
- [x] Fix promotion-gate test failures: `test_seed_specialist_routing_main_and_retry.py`
  had 4 failures — `_role_result` fixture missing `tool_chains` attribute that
  `seed_specialist_routing.py:447` / `seed_specialist_routing_v2.py:423` access.
  Orchestrator `91cb03bf` adds `tool_chains=[]` to the fixture. Combined with
  the prior `083e2736` (stale ingest topology fixture expectation), full
  promotion-gate is now `181 passed`, pipeline `summary: ok`. ✅ 2026-07-07
- **[declined: ws58 2026-11-03 content-review: standing constraint, explicitly "not a dispatchable task"; stays readable here]** *(STANDING CONSTRAINT — not a dispatchable task; do not flip. `auditor` 2026-07-29.)*
      Keep direct benchmark, production launch, and AutoPilot preflight wired to
  the canonical gate; no new bypasses.

#### Operating Rules

- Before editing root or orchestrator files, run `gitnexus status`; re-index
  through the repo wrapper if stale.
- Before code or high-impact doc changes, run `gitnexus impact ... --direction
  upstream` and keep the patch scoped to the blast radius.
- Active indices should stay dispatch-oriented. Completed chronology belongs in
  `progress/`, completed/archived handoffs, and commit history.
- No inference is required for this handoff unless a future consumer migration
  explicitly needs live runtime validation.

#### Validation

For no-inference stack-change work in `epyc-orchestrator`:

```bash
uv run python scripts/validate/stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces
uv run pytest -q tests/unit/test_stack_change_guard.py
uv run python scripts/registry/stack_change_pipeline.py check
```

For promotion-gate or launch-boundary changes:

```bash
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```

#### Newly found SMT placement source gap — 2026-10-07

**Scratch**: `/mnt/raid0/llm/tmp/ni08-ss-bench-smt-proposal-20261007/`; MAIN custody `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/`.

MAIN current-source review at APP `92cb0197e8e8e0b491909f669ed4b0c43c16f850` finds the launcher guard excludes only logical IDs. Its historical 0–95 → 96–191 example does not establish physical-core isolation when those ranges are SMT siblings. All three existing children and historical receipts are retained; the parent stays open. Existing REGION-SIBLING-1 toolkit is already present, but its logical→primary/lenient-parser contract loses the complete symmetric-group information needed by this guard. No running process, topology probe or kernel was changed.

- [x] **SSBENCH-SMT-SOURCE — exclude the full physical SMT closure of a live CPU-bench claim in the shared CLI/API launch guard.** Use the existing strict CPU-list parser, complete symmetric sysfs groups, injected synthetic topology, and fail-closed missing/malformed/asymmetric/candidate-map controls. Preserve no-claim quiet path and existing force authority. Cover both direct and actual API spawn layers with fake boundaries; source publication is separate from runtime-owner activation and real isolation evidence.

✅ 2026-10-07 SSBENCH-SMT-SOURCE: [MAIN original81/81 custody and exact source publication](../../artifacts/ni08/ssbench-smt-success-acceptance-20261007/README.md). Source conformance only; runtime-owner activation and real isolation evidence remain independent.

- [x] **STACK-STOP-STALE-PID** [non-inference] `orchestrator_stack.py stop <role>` signals the PID recorded in the stack state file without checking that it is still that server (`stack_commands.py` ~2187 → `stack_processes.kill_process_tree`: no cmdline/port/start-time identity check). 2026-11-05: `stop architect_critic` acted on PID 2055785, recorded 10-27 and already stopped then; pid_max is 4194304, so a reused PID would receive SIGTERM and SIGKILL (this time nothing was alive under it: no stop banner, no SIGTERM alerts). Fix: verify the PID's port listener or cmdline (and start time ≥ `started_at`) before signalling; otherwise drop the state entry and report STALE. Done when a unit test covers a reused PID and stop leaves it alive. ✅ 2026-11-05 — fixed in orchestrator `7b03a196` (`verify_state_pid`, stop + reload-embedders paths; 209 tests), operator-ratified. [no-belief: bug fix, no measurement]

## Track: wp12-fleet-layer-design
<!-- gate: none -->

> Folded from `handoffs/active/wp12-fleet-layer-design.md` @ `05e2b812a086` on 2026-11-02 (BRF-T1-F4, route 1a, operator D1/D5; retired row RTG-43 → RTG-36). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

---
title: WP-12 — Server-fleet layer (derive backends from the physical fleet, not per-role URL copies)
status: design (implementation deferred — operator-gated to post-measurement-chain)
created: 2026-07-22
owner: within-role-placement-state-machine (WP-12 line item)
kind: design-only  # NO implementation, NO src edits in this handoff
operator_authorization: op-bundle ESC-8 (2026-07-22) — "WP-12 sequencing (a): design doc now, implementation after the measurement chain completes"
constitution: operator-endorsed 2026-07-22 (quoted verbatim below)
predecessors:
  - handoffs/active/numa-placement-and-contention.md      # WP-8..WP-14, mode-exclusivity contract, DISPATCH-A/A2/A3
  - handoffs/archived/wp9-wp10-lineup-event-prep.md               # fleet-shape recert cascade (WP-9/WP-10)
supersedes_on_land:
  - WP-13 (stack_priors alias-ports inheritance) — durable fix + interim Fix-A field delegations + parity drift-guard test
  - WP-14 (runtime-facts phantom-lineup writer) — subsumed by fleet-from-registry (reader hardening still useful standalone)
---

> **CONSTITUTION (operator-endorsed 2026-07-22 — governs every decision below):**
> *"Roles as a remappable logical layer over servers is sound design."*
> Roles keep their per-role SLAs/timeouts, prompts, sampling, priority, and **remappability**
> (worker_math's historical Qwen2.5-Math binding is the canonical ghost — a role that can be
> re-pointed at a different model/server without touching the physical layer). The **physical
> fleet is defined ONCE and referenced**; roles never carry private copies of the wiring.

---

#### Executive summary (10 lines)

1. Today each orchestrator role carries an **independent COPY** of its server wiring: a URL-string field in `ServerURLsConfig` (`src/config/models.py`), an independent `ConcurrencyAwareBackend` (CAB) built per-role in `_init_caching_backends` (`src/llm_primitives/backend.py`), and — through those copies — a fragmented view of the same physical endpoints' health, topology idxs, and region-lock identity.
2. Roles that share ONE physical server (registry `server_mode.worker.shared_with:[worker_math,toolrunner]`; frontdoor↔coder_escalation↔worker_summarize) therefore get **N descriptions of one fleet** that silently drift apart.
3. Shipped failures from that drift: worker_math's stale 2-endpoint copy **serialized its EV-11c arm (~4h)**; same-fleet `forced_role_fallback` churned **~90x** (role A's object trips while role B's object for the same server stays "healthy"); WP-10's worker_math has **no region locks at all**; ESC-8's env producer can **clobber the truth** and wire every role to dead full ports.
4. **Design:** split into a **Fleet layer** (defined once from the registry `server_mode` SoT: endpoints + quarter/full shapes + topology idxs + **ONE** health/breaker state per physical endpoint + **ONE** region-lock identity + demotion/alignment machinery) and a **Role layer** (role → fleet reference + per-role policy: SLA/timeout, prompt/template, sampling, priority, optional capacity cap, placement_policy override).
5. **One endpoint's health is one fact:** the breaker/circuit and the region-lock identity live on the fleet's endpoint, not on any role's copy — every role bound to that fleet reads and writes the same circuit and the same lock.
6. **Fallback becomes fleet-aware:** same-fleet fallback (worker_math→worker_general) collapses to a **no-op** (identical physical backend + identical breaker → nothing to retry); cross-fleet fallback (architect_general→coder_escalation, ingest_long_context→architect_general) stays **real**. This kills the `forced_role_fallback` noise class at the root.
7. **Construction flow:** registry `server_mode` → normalize to Fleet objects (one per physical server group, keyed by primary role + `shared_with`) → build **one CAB per fleet** → roles resolve to `(fleet_ref, RolePolicy)`; the logical role is threaded per-call so tap/timeout/prompt/sampling stay role-specific while the physical dispatch state is shared.
8. **Deletes:** the `_LEGACY_SERVER_URL_FALLBACKS` literals, the per-role URL copies + Fix-A field delegations in `ServerURLsConfig`, the per-role CAB instances for shared fleets, and (on land) WP-13's alias-ports fix + its interim parity drift-guard test. **Keeps:** the role fields — now as references — and every legitimate role-layer bit (remappability, SLAs, sampling, capacity policy).
9. **Rollout:** behind `ORCHESTRATOR_FLEET_LAYER=1` (default off), deployed **after** the EV-11c measurement chain completes, sequenced at the same terminal boundary as WP-13's regeneration + the ESC-8 package; WP-12 landing **removes** WP-13's interim, not layers on top of it.
10. **Riskiest decision:** collapse the N per-role CABs into **one CAB per fleet** (vs. keep per-role CABs sharing only a fleet descriptor). Recommendation below: **collapse** — a shared descriptor still leaves N objects with divergent per-instance dispatch state (the exact fragmentation being fixed); thread the logical role per-call to preserve role identity.

---

#### 1. Current architecture (the problem, concretely)

##### 1.1 Three URL producers feed per-role string copies

`ServerURLsConfig` (`src/config/models.py:597-663`) declares ~20 role fields, each defaulting to `_server_url_default(<name>)`. `_server_url_default` → `_stack_prior_server_urls()` (`models.py:429-452`), which merges, in precedence order:

1. **env/runtime-facts producer** — `_selected_server_url_values(_runtime_or_env_selected_servers())` (`models.py:316-399`). Driven by `ORCHESTRATOR_STACK_NUMA_MODE` or the runtime-facts manifest. **This is the ESC-8 landmine**: when its import path succeeds it lands FIRST and, via `urls.update(...)` before the `setdefault` from stack_priors, clobbers the truth — wiring every hot role to the dead full ports under `STACK_NUMA_MODE=full` on a quarters-only deployment.
2. **stack_priors producer** — `live_stack_serving_url_values(stack_priors.yaml)` (`src/registry/stack_priors.py:439-446`), the intended SoT (`urls.setdefault(...)` — only fills gaps the env producer left).
3. **manifest + hardcoded literal** — `_stack_manifest_server_urls()` (`models.py:402-426`) then, as the last-resort default, `_LEGACY_SERVER_URL_FALLBACKS` (`models.py:265-294`) — a frozen dict of literal `full:...` tuples per role.

Each role field is an independent string. Shared-fleet roles are wired by **delegating the default to the primary** (the interim WP-13 "Fix A"): `worker_math`, `toolrunner`, `worker_summarize`, `coder`, `coder_escalation` all call `_server_url_default("worker_general")` or `_server_url_default("frontdoor")` (`models.py:616-640`). That is a *convention enforced field-by-field in comments* — nothing structural prevents the next drift.

##### 1.2 One ConcurrencyAwareBackend built per role — even for shared fleets

`_init_caching_backends` (`src/llm_primitives/backend.py:46-222`) iterates `server_urls` and builds a backend **per role key**. For every `full:`-prefixed multi-instance role it constructs an independent `ConcurrencyAwareBackend`, and independently re-derives, per role:

- `topology_role` via `_infer_topology_role_for_urls` (`backend.py:17-40`) — a **URL-tuple string match** against the set of topology roles. Robust only while every role's copy is byte-identical.
- the full/quarter split, `_port_of`, and the **DISPATCH-A2 demotion** (`backend.py:135-199`): resolve each endpoint's true topology idx by port against `NUMA_CONFIG`; demote a quarter mis-wired as `full:` into the quarters pool. This decision is recomputed per role and can differ across copies of the same fleet.
- per-instance dispatch state inside the CAB: `_session_quarter` affinity, migration counters, `_full_slot_aligned`, `_quarter_topology_idx`. **None of this is shared** between two roles pointed at the same physical fleet.

##### 1.3 The breaker is per-endpoint — but reached through divergent copies

`BackendHealthTracker` (`src/api/health_tracker.py`) keys circuits by `backend_url` and is a **shared singleton** on app state (`state.health_tracker`). So at the URL layer, breaker state is *already* per-endpoint. The fragmentation is upstream of it:

- Two roles can disagree on **which endpoints exist** (worker_math's stale copy had 2 of 5 ports) → they exercise different circuits for the same fleet, and the "healthy" subset masks the "open" one.
- The `_FALLBACK_MAP` (`src/roles.py:395-402`) treats same-fleet roles as independent fallback targets: `WORKER_MATH → [WORKER_GENERAL]`, `CODER_ESCALATION → [FRONTDOOR]`. When the shared fleet is loaded/timing-out, `inference.py:401-416` retries the *same physical endpoints under a different role name* — physically a no-op, but it churns (the ~90x). `classify_failure` + the fallback loop have no notion that both roles are one fleet.
- The **region-lock identity** is the `topology_role`; cross-process CPU region locks are keyed by it (`src/runtime/cpu_region_lock.py`). Because `topology_role` is *inferred per role from URL strings*, a drifted copy can land a role on the wrong lock namespace — or, per DISPATCH-A/A2, let a quarter wired as `full:` grab idx-0's ALL-region lock and head-of-line-block the machine.

##### 1.4 Net: N descriptions of one fact

For the worker fleet (gemma4, ports 8072 full + 8082/8182/8282/8382 quarters) there are today up to **four** role objects (worker_general, worker_math, toolrunner, worker_summarize is on the frontdoor fleet; coder/coder_escalation/worker_summarize sit on frontdoor's) each independently describing the same servers, each with its own topology resolution, its own CAB dispatch state, its own path to the breaker, and — for worker_math — **no NUMA_CONFIG entry and thus no region locks** (WP-10). The registry already carries the normalized truth (`server_mode` + `shared_with`); nothing consumes it as a single source.

---

#### 2. Target architecture — two layers

##### 2.1 Fleet layer (defined ONCE, registry `server_mode` is SoT)

A **`ServerFleet`** is the single description of one physical llama-server deployment. One fleet per distinct physical server group. Fields:

| Field | Meaning | Source |
|-------|---------|--------|
| `fleet_id` | Stable identity == the physical topology role (e.g. `worker_general`, `frontdoor`) | registry `server_mode` primary role |
| `endpoints[]` | `(port, topology_idx, cpu_regions, shape, is_full)` per live instance | stack_priors serving ports resolved against `NUMA_CONFIG` by port |
| `full_instance_idx` / `full_port` | The 1×96t/half instance, or **None** when quarters-only | `NUMA_CONFIG[fleet].full_instance_idx`, cross-checked against live endpoints |
| `mode` | `full` \| `quarter` \| `mixed` — the realized serving mode, not the static default | live endpoint set (kills the WP-14 phantom-lineup class) |
| `topology_role` | The **one** region-lock identity for every endpoint in the fleet | `fleet_id` (no per-role inference) |
| `circuits{port→BackendCircuit}` | **ONE** health/breaker state per physical endpoint | shared `BackendHealthTracker`, keyed by the fleet's own endpoint URLs |
| `placement_policy` | `full_disabled` \| `burst_prefer_quarters` \| `solo_prefer_full` \| `queue_only` | `NUMA_CONFIG[fleet].placement_policy` |
| `demotion/alignment` | DISPATCH-A2 misaligned-full demotion + `_full_slot_aligned`, computed **once** at fleet build | port↔`NUMA_CONFIG` resolution |

The fleet owns exactly one `ConcurrencyAwareBackend` (see §7 riskiest decision). The demotion/alignment machinery, the port→topology-idx resolution, and the region-lock identity are computed once per fleet and are therefore impossible to disagree with themselves.

**Construction:** `build_fleets(registry, numa_config, stack_priors) -> dict[fleet_id, ServerFleet]`. Enumerate `server_mode` rows; each row + its `shared_with` collapses to one fleet; resolve live endpoints from stack_priors (the SoT) with `NUMA_CONFIG` supplying shapes/idxs/policy. The env/runtime-facts producer is **not** consulted for fleet identity (this makes the ESC-8 precedence inversion structural rather than a setdefault-ordering accident).

##### 2.2 Role layer (reference + policy)

A **`RoleBinding`** is what a role *is* once the physical layer is factored out:

| Field | Meaning | Today's home (preserved) |
|-------|---------|--------------------------|
| `fleet_ref` | Which `ServerFleet` serves this role | replaces the URL-string field |
| `model_binding` | The logical model the role currently maps to (**remappable** — worker_math↔Qwen2.5-Math ghost) | registry `model_role` |
| `timeout` / SLA | Per-role request deadline | `TimeoutsConfig.for_role` (`models.py:666-790`) — unchanged |
| `prompt` / `template` / `use_chat_completions` | Role prompt + `/v1/chat/completions` vs `/completion` | `chat_completions_roles()`, persona/prompt loaders — unchanged |
| `sampling` | temp/seed/top_p/enable_thinking | registry `chat_template_kwargs`, sampling config — unchanged |
| `priority` | Admission/queue priority | request-priority path — unchanged |
| `capacity_cap` (optional) | e.g. `max_quarters_for_this_role` — cap a role's share of a shared fleet | **new**, role-layer only |
| `placement_policy_override` (optional) | Role-scoped override of the fleet default | **new**, role-layer only |

The role's logical identity is threaded into dispatch per-call. `_tap_dispatch_metadata` (`concurrency_aware.py:982-1006`) already emits BOTH `role` (logical) and `topology_role`/`lock_role` (physical) — the design generalizes that: the fleet backend is physical, the call carries the role, so tap/timeout/prompt/sampling remain role-specific over shared physical state.

---

#### 3. Breaker-state sharing semantics — "one endpoint's health is one fact"

- **One circuit per (fleet, endpoint port).** The fleet's endpoints are the *only* set of URLs any of its roles ever present to `health_tracker.is_available` / `record_failure` / `record_success`. Because all roles on the fleet resolve to the identical endpoint tuple (structurally, not by convention), the existing URL-keyed singleton becomes authoritative with no ambiguity.
- **A failure observed by any role trips the circuit for all roles on the fleet.** worker_math and worker_general no longer maintain independent "health opinions" about port 8082.
- **Half-open probing is fleet-global.** One probe per endpoint per cooldown, regardless of how many logical roles ride the fleet — no N-fold probe amplification (a contributor to the 90x).
- **The region lock is the same fact in a different dimension:** one `topology_role` per fleet means the cross-process CPU region locks are the physical truth; a role can never acquire a lock namespace that disagrees with its fleet's endpoints. DISPATCH-A2 demotion happens once at fleet build, so the "quarter-impersonating-full holds all-region lock" hazard cannot be re-created per-copy.

Invariant to assert at build + runtime: **for every fleet, `{endpoints seen by each bound role} == fleet.endpoints`** and **`{topology_role of each bound role} == fleet.fleet_id`**. Fail closed on mismatch (this is the structural replacement for WP-13's parity drift-guard *test*).

---

#### 4. force_role / fallback interaction

`force_role` selects a **role** (logical); the role resolves to its fleet. Nothing about forcing a role changes — the role still carries its own prompt/timeout/sampling. What changes is fallback:

- **Same-fleet fallback → no-op (elided).** `get_fallback_roles` becomes fleet-aware: a candidate whose `fleet_ref` equals the failing role's `fleet_ref` is dropped, because retrying it hits the identical physical backend and the identical (already-open) circuit. `WORKER_MATH → WORKER_GENERAL` and `CODER_ESCALATION → FRONTDOOR` both collapse to no-ops (worker_math shares worker_general's gemma4 fleet; coder_escalation shares frontdoor's Qwen fleet). **This is the fix for the `forced_role_fallback` noise class** — the ~90x churn was same-fleet fallback masquerading as failover.
- **Cross-fleet fallback → real, unchanged.** `ARCHITECT_GENERAL → CODER_ESCALATION` (122B fleet → frontdoor fleet) and `INGEST_LONG_CONTEXT → ARCHITECT_GENERAL` cross physical fleets → genuine failover, kept. When the *fleet* circuit is open (all endpoints down), cross-fleet fallback is the only fallback that can succeed, and now it's the only one attempted.
- **Rule:** fallback is meaningful **iff** it changes the physical fleet. The fallback map is re-expressed as fleet-adjacency; same-fleet edges are compiled out at load.

---

#### 5. Migration path — what gets deleted, what survives

**Deleted (the per-role copy machinery):**

- `_LEGACY_SERVER_URL_FALLBACKS` literal dict (`models.py:265-294`) — fleets come from stack_priors/registry; a literal per-role frozen tuple is exactly the drift vector being removed. (A single degraded-mode literal *per fleet* may survive as the fleet layer's own last resort — see risks.)
- The per-role URL-string fields' **independent defaults** + the Fix-A field delegations in `ServerURLsConfig` (`models.py:616-640`, the `_server_url_default("worker_general")`/`("frontdoor")` chains). Roles stop owning URL strings.
- The **per-role CAB instances for shared fleets** — the N-objects-per-fleet build in `_init_caching_backends`. One CAB per fleet replaces them.
- `_infer_topology_role_for_urls` URL-tuple string matching (`backend.py:17-40`) — topology role is now `fleet_id`, not inferred.
- **On land, WP-13 in full:** the durable `_stack_manifest_info` alias-ports inheritance fix (`stack_priors.py:836-853`, which today gives an alias only its own single port), *and* its interim Fix-A field delegations, *and* the interim parity drift-guard test. WP-12's fleet identity makes alias-port inheritance moot (aliases are role bindings that reference the primary's fleet). **WP-12 landing removes WP-13's interim, it does not stack on it.**
- **On land, most of WP-14:** the runtime-facts phantom-lineup writer's authority over role wiring — the fleet's `mode` is the realized serving mode from live endpoints, not the static full-mode default the writer records. (The two *reader* hardenings in WP-14 — `dashboard_topology.py` and `eval_tower.py` fail-closed type checks — remain worth landing independently as defense-in-depth.)

**Survives (the legitimate role layer):**

- Every role field — **reclassified from a URL copy to a `fleet_ref` + `RolePolicy`**. The role names, `Role` enum, routing, and MCP/`list_roles` surface are unchanged.
- **Remappability** — a role can be re-pointed at a different fleet/model without touching the physical layer (worker_math's Qwen2.5-Math ghost; toolrunner as a logical alias over the gemma4 fleet).
- Per-role **SLAs/timeouts** (`TimeoutsConfig`), **prompts/templates** (`chat_completions_roles`, persona loaders), **sampling** (registry `chat_template_kwargs`), **priority**, and the new optional **capacity cap** / **placement_policy override**.
- The **contention matrix / topology_hash** machinery and the WP-9/WP-10 recert cascade — fleets change *how wiring is described*, not the measured topology. (WP-12 does not itself change any cpuset, so it does not trigger the §H recert cascade; it should land in a window where the topology_hash is already settled.)
- The shared `BackendHealthTracker` singleton — now reached unambiguously.

**Ordering with the in-flight fixes:** ESC-8's precedence inversion (Fix 2) and WP-13's regeneration are the *interim* that make the current per-copy world safe until WP-12 lands. WP-12 is the durable replacement. Sequence: land ESC-8 + WP-13 interim at the EV-11c boundary (already granted); build+gate WP-12 behind its flag; flip WP-12 on and delete the interim in the same change once its acceptance gate passes.

---

#### 6. Test / acceptance plan (incident-derived cases first)

Unit + integration, all runnable without live inference (mock backends, synthetic `NUMA_CONFIG`/stack_priors) except the two live gates flagged. **A live eval is running — no API calls from this design work.**

1. **Fleet collapse / parity** — `build_fleets` over the real registry yields one fleet for `{worker_general, worker_math, toolrunner}` and one for `{frontdoor, coder, coder_escalation, worker_summarize}`; assert every bound role resolves to the **identical** endpoint tuple + `topology_role`. (Replaces WP-13's drift-guard test with a structural invariant.)
2. **worker_math 4-wide** (mode-exclusivity contract, WP-8/WP-10) — 4 concurrent worker_math requests land on **4 disjoint busy quarters** of the shared gemma4 fleet, full idle; worker_math now holds real region locks (fixes WP-10). Mirror case: 4 concurrent frontdoor → 4 quarters, half0 idle.
3. **No phantom-full** — a fleet whose live endpoints are quarters-only with the first port mis-marked `full:` demotes that endpoint into the quarters pool **once** at fleet build (DISPATCH-A2), serves no full, and no role acquires idx-0's all-region lock. Assert region locks == physical cores.
4. **Single breaker state** — inject failures on port 8082 via worker_math's dispatch; assert the *fleet* circuit for 8082 opens and worker_general + toolrunner immediately observe `is_available(8082) == False` (one fact). Assert exactly one half-open probe per cooldown across all bound roles.
5. **Same-fleet fallback is a no-op** — force worker_math with the fleet circuit open; assert `get_fallback_roles` yields **no** same-fleet candidate (no worker_general retry), the request fails fast (or waits on the fleet, not on a role-name retry), and the fallback-churn counter stays ~0 (regression bound for the 90x).
6. **Cross-fleet fallback still real** — architect_general with its fleet circuit open falls back to coder_escalation's (distinct) fleet and succeeds.
7. **Mode-exclusivity contract cases** — `burst_prefer_quarters` fleet abandons full the moment a self-role holder exists; `full_disabled` never emits full; `solo_prefer_full` keeps full first at concurrency 1. Reuse the existing `test_concurrency_aware_migration_sm.py` / placement-SM suites against the one-CAB-per-fleet object.
8. **Remappability** — re-point worker_math's `RoleBinding.fleet_ref`/`model_binding` at a synthetic second fleet; assert only worker_math moves, worker_general/toolrunner stay, and no URL literal edit was needed.
9. **ESC-8 non-clobber** — with `ORCHESTRATOR_STACK_NUMA_MODE=full` set but a quarters-only stack_priors, `build_fleets` produces the quarters fleet (env cannot override fleet identity). Regression for the armed-outage class.
10. **Live gate (operator-approved window only):** single-worker API, `ORCHESTRATOR_FLEET_LAYER=1`; replay the ROUTE-A3 J2/J3 migration probe + a worker_math 4-wide burst; confirm committed migrations, 4 busy quarters, one circuit per endpoint, zero same-fleet fallback events.

---

#### 7. Riskiest design decision + recommendation

**Decision: one `ConcurrencyAwareBackend` per FLEET (collapse the N per-role CABs) vs. keep N per-role CABs that merely share a read-only fleet *descriptor*.**

- *Shared-descriptor (lighter):* keep today's per-role CAB objects, but have them all read fleet identity/endpoints/policy from one `ServerFleet`. Smaller diff, preserves per-role object identity for tap/session state.
  - **Fatal flaw:** the fragmentation being fixed is *per-instance dispatch state*, not just wiring — `_session_quarter`, migration counters, `_full_slot_aligned`, and (critically) the live region-lock acquisitions live *inside the CAB object*. N CABs sharing a descriptor still hold N independent session-affinity maps and can still race each other for the same physical quarter under two role names. It reduces wiring drift but **not** the runtime-state fragmentation or the lock races.
- *One-CAB-per-fleet (heavier):* the fleet owns a single CAB; roles dispatch through it, threading their logical role per-call. Session affinity, migration state, and lock acquisition become one authoritative object per physical fleet — which is precisely "one endpoint's health/placement is one fact."
  - **Cost:** dispatch must carry the logical role through a physical backend. Mitigated because the plumbing already exists: `_tap_dispatch_metadata` emits logical `role` + physical `topology_role` separately, and timeout/prompt/sampling are already looked up by role name upstream of the backend, not inside it. Session-affinity keys stay per-`session_id` (already role-agnostic in `_session_quarter`).

**Recommendation: collapse to one CAB per fleet.** It is the only option that actually closes the runtime-state and region-lock fragmentation (the shared-descriptor variant leaves the lock races and divergent session state intact, so it would not have prevented the worker_math serialization or the 90x churn). Thread the logical role as a per-call parameter and keep role-specific timeout/prompt/sampling/priority resolution in the role layer above the backend. Gate the whole thing behind `ORCHESTRATOR_FLEET_LAYER=1` so the legacy per-role build remains the instant rollback until the acceptance gate (§6) passes.

---

#### 8. Risks

- **Degraded-mode bootstrap:** deleting `_LEGACY_SERVER_URL_FALLBACKS` removes the last-resort wiring when stack_priors is absent (fresh clone, pre-launch API). *Mitigation:* keep exactly one literal fallback **per fleet** inside the fleet layer (not per role), so the degraded path still resolves without re-introducing per-role copies.
- **Per-call role threading regressions:** collapsing CABs means a bug in role-threading could cross a role's prompt/timeout onto another role on the same fleet. *Mitigation:* acceptance cases 2/7/8; keep the flag default-off until green.
- **Hidden per-role divergence that was load-bearing:** some role may today rely on a *deliberately* different endpoint subset (e.g. a capacity carve-out). *Mitigation:* that is exactly what `capacity_cap` in the role layer expresses — audit each shared-fleet role for an intended cap before collapsing; default cap = full fleet.
- **Sequencing collision with the interim fixes:** landing WP-12 without first removing ESC-8/WP-13 interim risks two systems describing wiring. *Mitigation:* the flip and the interim-deletion are one change (§5 ordering).
- **Topology_hash confusion:** WP-12 changes descriptions, not cpusets — but reviewers may expect a recert. *Mitigation:* document explicitly that WP-12 does **not** touch `NUMA_CONFIG` cpusets and does **not** trigger the §H cascade (unlike WP-9/WP-10).

#### 9. Explicit non-goals

- **Not** a NUMA/cpuset change — no new topology fingerprint, no contention-matrix re-measure, no §H recert cascade (that is WP-9/WP-10).
- **Not** a change to the placement state machine, KV migration, or the mode-exclusivity contract — WP-12 consumes DISPATCH-A/A2/A3 behavior, it does not redefine it.
- **Not** a change to routing, the `Role` enum, role prompts/sampling/SLAs, or the MCP role surface — those are the *role layer* and are preserved verbatim.
- **Not** cross-server KV sharing or slot multiplexing (KVCOMM / dynamic-stack-concurrency scope).
- **Not** a registry schema change — `server_mode` + `shared_with` already carry the normalized truth; WP-12 *consumes* it, it does not extend it.
- **Not** the ESC-8 env-alignment stack-script change (Fix 1) — WP-12 makes the env non-authoritative for fleet identity, but the launch-site env hygiene is a separate stack-script task.

#### 10. Reporting

##### Implementation status (2026-07-23, chartered worktree session — NOT landed; flip boundary pending)

Implementation branch: `wp12-fleet-layer-impl` (epyc-orchestrator, worktree
`/mnt/raid0/llm/worktrees/wp12-fleet-layer`, rebased onto
`origin/spec-dec-mtp-refresh-2026-06-22` @ `97ce58b8` — two-test
reconciliation + solo-goes-full seam fix absorbed), head `3c0b4ce4`, pushed;
84-test targeted regression green post-rebase. The live-lock-coupling finding
this session filed was confirmed by the main session, fixed in `97ce58b8`, and
generalized to a filed three-seam-hermeticity task for the whole file
(`5adf81aa`).
Flag `ORCHESTRATOR_FLEET_LAYER` default OFF everywhere; no env wiring into launch
scripts; flag-off behavior verified byte-identical (existing placement/migration/
demotion suites: 130 passed; the 2 failures — frontdoor drift-guard vacuity check +
vision quarter-preference — pre-exist at the base commit, verified by stash-run).

- [x] §2.1 `ServerFleet` build from registry `server_mode` SoT (`src/fleet.py`; env/runtime-facts producers structurally not consulted; port-resolved `is_full`; per-FLEET degraded literal) ✅ 2026-07-23
- [x] §2.2 `RoleBinding` policy layer (fleet_ref + model_binding; `capacity_cap`/`placement_policy_override` carried as data, enforcement deliberately deferred) ✅ 2026-07-23
- [x] §3 one breaker/lock identity per fleet endpoint (CAB `health_tracker` injection, per-dispatched-endpoint recording, circuit-aware SM candidates, all-open fail-fast; §3 parity invariant fails the build closed) ✅ 2026-07-23
- [x] §7 one-CAB-per-fleet collapse (flag-gated `_init_fleet_backends`; logical role threaded per-call; use_chat_completions fleet-consensus-or-fail-closed) ✅ 2026-07-23
- [x] §4 same-fleet fallback compiled to no-ops (`compiled_fleet_fallback_map` + flag-gated `get_fallback_roles`) ✅ 2026-07-23
- [x] §6 acceptance cases 1–9 as offline/mocked tests (33 tests: `test_fleet_layer_build.py` 1/3/8/9+parity+degraded, `test_fleet_layer_dispatch.py` 2/7+flag-off identity, `test_fleet_layer_breaker.py` 4+5-fail-fast, `test_fleet_layer_fallback.py` 5/6) ✅ 2026-07-23
- Explicit decline (2026-07-23): per-request `use_chat_completions` threading through a shared fleet backend is NOT filed as a task — the fleet-consensus-or-fail-closed rule covers every real fleet (all shared-fleet roles agree in the live config, verified offline), and a future disagreement fails loudly to the legacy build rather than mis-routing; revisit only if that CRITICAL log ever fires.

##### FLIP BOUNDARY EXECUTED 2026-07-23 (operator-directed; this session held the con; main session stood down per one-deploy-authority)

- [x] Merge `wp12-fleet-layer-impl` (3c0b4ce4) → `spec-dec-mtp-refresh-2026-06-22` = merge commit `4ca6859a` ✅ 2026-07-23
- [x] Acceptance cases 1–9 re-run on the MERGED tree: 33/33 + targeted regression 53/53 ✅ 2026-07-23
- [x] Launch-env wiring: `ORCHESTRATOR_FLEET_LAYER=1` durable `env.setdefault` (`a172d2dd`); rollback = reload with `ORCHESTRATOR_FLEET_LAYER=0` in the shell env ✅ 2026-07-23
- [x] Pre-reload preflight: fleet build from LIVE registry+priors+NUMA = 4 fleets (frontdoor + worker_general quarters-shared, architect single, ingest quarters), §3 parity green, 8 bindings, none degraded ✅ 2026-07-23
- [x] One API-only reload (new PID 3051676) + no-inference attestation: `ORCHESTRATOR_FLEET_LAYER=1` in worker env (attest_orchestrator_workers), API healthy, /health backend probes now group the shared fleet (`coder_escalation/frontdoor/worker_summarize` as one probe) ✅ 2026-07-23
- [x] Both boundary commits pushed to origin ✅ 2026-07-23
- **DELIBERATE SCOPE DEVIATION (flagged in `a172d2dd`)**: the §5 WP-13 interim deletion did NOT execute at this boundary. Reasoning chain: instant-rollback requirement ⇒ the legacy per-role build stays ⇒ Fix-A delegations + generator alias-ports inheritance are its substrate (deleting them breaks rollback after any priors regeneration: toolrunner KeyError degraded, worker_math single-quarter re-serialization) ⇒ their guard tests stay with the code they guard. Fleet-wins-at-runtime resolves the two-descriptions concern the §5 atomicity clause guarded against. The permission classifier independently blocked live-tree test deletion, converging on the same outcome.
- [ ] **Post-soak §5 cleanup (code + tests as ONE change)**: retire the legacy per-role build path — ServerURLsConfig URL ownership, Fix-A delegations, `_LEGACY_SERVER_URL_FALLBACKS`, generator alias-ports inheritance, and their guard tests (4 in `test_full_slot_demotion.py` + convergence test in `test_stack_priors_compiler.py`) — once the fleet layer survives its soak and the operator retires the flag-off rollback Trigger: ask the operator ONCE, in a decision package carrying the soak evidence (days with the fleet-layer flag on, incidents attributed), to retire the flag-off rollback; if approved, run this cleanup as one change; if declined, retire this row.
  **2026-08-11 (`mainB`) — PRECONDITION CHECKED AND IT DOES NOT HOLD. Do not start this row.**
  The gate on this row is *"the operator retires the flag-off rollback"*. Verified against the tree,
  three ways, all negative:
  1. **The flag still exists and still defaults OFF.** `src/fleet.py:40` defines
     `FLEET_LAYER_ENV = "ORCHESTRATOR_FLEET_LAYER"`; `src/fleet.py:23` states the module is *"inert
     unless `ORCHESTRATOR_FLEET_LAYER=1`"*; `src/llm_primitives/backend.py:177` still branches on
     `os.environ.get("ORCHESTRATOR_FLEET_LAYER") == "1"`, default off.
  2. **No operator receipt retires it** — nothing under `artifacts/operator/` mentions
     `FLEET_LAYER`, and the runtime-flags store carries no fleet entry at all.
  3. **The rollback substrate is intact and still referenced** — `_LEGACY_SERVER_URL_FALLBACKS`
     lives at `src/config/models.py:282` with live referents (e.g.
     `src/api/routes/vision_serving.py:25`).
  So deleting the interim now would remove the rollback path for a flag that is **still default-off**
  — the precise reasoning chain the 2026-07-23 scope deviation (`a172d2dd`) recorded when it
  declined the same deletion. **The condition has not moved in the 19 days since.** That is a
  recurrence, not a fresh finding: the row is gated on an operator action nobody has taken, so it
  will keep being picked up and re-declined until the operator either retires the rollback or the
  gate is rewritten. Surfaced to `coordinator-agent` as an operator item rather than re-declined
  silently a third time.

  **Residual `wp12-realized-first-reader` — FILED OUT OF SCOPE WITH A REASON, not left silently**
  (2026-08-11, `mainB`; the brief required one or the other). `stack_templates._active_numa_mode()`
  does still delegate to `env_stack_numa_mode()` — re-derived, the code is at
  `src/config/stack_templates.py:256-259` (the file moved `scripts/server/` → `src/config/` since
  the residual was filed, so its old path citation reads dead while the line numbers still match).
  **It is not an oversight and must not be deleted.** WP-14's residual note
  (`within-role-placement-state-machine.md`, ✅ 2026-07-29, orchestrator `608cc54c`) records this as
  the *intended* shared validated reader: *"No further WP-12 deletion is needed."*
  One precision worth having, because the two defaults differ and it is easy to misread as a hazard:
  `env_stack_numa_mode()` defaults to **`full`** (`DEFAULT_STACK_NUMA_MODE = "full"`), while the port
  helper `_role_instance_ports()` defaults to **`both`**. An ambient `full` would be the ESC-8 kill
  chain A4 shape *if it governed* — it does not. The consumer at `stack_templates.py:325+` computes
  `_matching_numa_mode_for_ports(role, prior_ports)` and prefers the **realized** mode per role, and
  the function is a *validator* (returns `errors, warnings`), not a priors writer. The actual priors
  writer is separately hardened: `stack_priors.py:1041` `_realized_compile_numa_mode` **refuses to
  compile** when nothing is listening rather than defaulting to `full`.
  So: out of scope for §5, resolved by decision, and the reader stays.
- [x] §6 case 10 live gate — **PASS** ✅ 2026-07-23 (operator inference grant same day; evidence bundle `coordination/inference-batch/bundles/WP12-case10-live-gate/` + terminal ledger row `WP12-case10-live-gate`): worker_math 4-wide burst → **4 disjoint busy quarters** (8082/8182/8282/8382, all four simultaneously decoding, peak /slots sample all-busy), fleet identity on every dispatch (tap `topology_role=worker_general`), zero same-fleet fallback, zero phantom-full, migration counters 0→0. J2/J3 replay executed faithfully (identical params, `--workers 1` API-only reload, 12/12 OK, n_aborted=0) — verdict INCONCLUSIVE is **structurally correct**: both fleets are quarters-only (no full endpoint), so the full↔quarter migration surface is dormant (C10-F2). Two findings, neither a fleet-layer defect:
  - **C10-F1**: `live_warm_worker_slots()` returns `{}` (filters `tier=="warm"`; every live role is `hot`) → `get_role_max_concurrency()==1` for ALL roles → `_acquire_role` `Semaphore(1)` per role **per API worker process**. Within-role concurrency in production exists ONLY via the 6 uvicorn processes (cross-process disjointness from region flocks). On a `--workers 1` API every role serializes fully — the first burst attempt landed 4/4 on port 8082 back-to-back (staircase 19.7/34.9/49.6/64.1s). Also reinterprets the 2026-07-21 J2/J3 pass: its committed migrations (forward=6/reverse=4) are consistent with fully serial traffic (full-idle KV handovers), not overlap-driven displacement.
  - **C10-F2** (wording corrected 2026-07-23 per [stack-lineup-dossier-2026-07-23.md](../archived/stack-lineup-dossier-2026-07-23.md) §5.1): WP-3/WP-4 migration surface dormant in the quarters-only **realized/launched** lineup — the full/half instances remain **declared-dormant** in NUMA_CONFIG (worker full 8072 `placement_policy: full_disabled` by DISPATCH-A `99dd6c92`; frontdoor 8070 / ingest 8085 halves undisabled-but-unlaunched since the v7 quarter-mode cutover `ff4b3766`). SM stays unit-verified; the live surface returns only if the operator redeploys a big instance.
  - **C10-F2 CLOSED same day — lineup restored, J2/J3 PASS on it** ✅ 2026-07-23: the operator ruled the launch-contract drop an accidental regression and directed restoration; 8070/8072/8085 redeployed via the new additive `--numa-mode both` promotion path (orchestrator `95dffc88`; three-gates green: pipeline ok + 183-test suite, additive starts with quarters preserved, live affinity verified, solo dispatch → big instances on all three fleets). The J2/J3 replay then ran on the restored lineup under the fleet layer and **PASSED**: forward=6, reverse=1, n_committed=7, n_aborted=0 (`probeD_stdout.json` / `j2j3_restored_lineup_probeD.jsonl` in the case-10 bundle). Case-10 is now complete in its full original sense — committed migrations confirmed live.
- [x] **C10-F1 follow-up — fleet-derived role concurrency LANDED flag-off** ✅ 2026-07-23 (orchestrator `94ab796f`): `ORCHESTRATOR_FLEET_ROLE_CONCURRENCY=1` derives `get_role_max_concurrency` from the role's realized fleet (disjoint-quarter capacity; big instance never adds capacity since it overlaps; fail-open to legacy on fleet unavailability, never wider). **Default OFF — enabling is a deploy decision** (raises in-process within-role concurrency; placement SM + region locks own disjointness; recommend enabling alongside a WP-8-style eval-fanout validation window). Until enabled, eval fan-out concurrency remains 6-process spread × per-process `Semaphore(1)`.
  - **ENABLE TIMING DECIDED (operator, 2026-07-23): Option C — after E5.** Flag stays OFF through E5 W0/Stage-B so every E5 comparison + the banked R3 denominator (27.55 min/eval) describe the exact live lane; enable + validate (case-10-style burst probe + one R3 re-measure) in the post-E5 provisioning window, where R4's per-instance `-np` recommendations likely change lane config anyway — one re-baseline covers both changes.

On implementation (post-measurement-chain, per operator sequencing):
1. Flip the WP-12 checkbox in `within-role-placement-state-machine.md` → `- [x] … ✅ <date>`; note the interim (WP-13 Fix-A + drift-guard test) deletion in the same edit.
2. Update `progress/2026-07/2026-07-DD.md`.
3. Cross-reference op-bundle ESC-8 (shared restart surface) and the WP-9/WP-10 lineup event.

> **2026-07-23**: the fleet layer's heterogeneous extension is governed by the OPERATOR-RATIFIED fabric contract (core guiding principle banner in [heterogeneous-slot-fabric-residency.md](kv-cache-program.md#track-heterogeneous-slot-fabric-residency)): policy-data-never-code, the four robustness axioms, the bounded/reversible/measurable/gated conversion rule.
