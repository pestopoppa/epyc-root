# Stack Change Governance Pipeline

**Status**: IN PROGRESS - canonical stack-change command, generated
stack-prior contract, guard/scanner ownership, runtime attestation, launch and
preflight gates, promotion-gate execution, and representative swap-CI witnesses
are live. Remaining work is high-risk consumer migration and waiver hygiene;
completed governance history through 2026-06-19 is compacted under
`Completed Scope`.
**Created**: 2026-06-13
**Updated**: 2026-07-26
**Priority**: HIGH — prevents silent stale model constants after stack changes; no inference required for W1-W4
**Related**: [standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md), [model-capability-descriptors.md](model-capability-descriptors.md), [routing-truth-restoration.md](../completed/routing-truth-restoration.md), [dynamic-stack-concurrency.md](dynamic-stack-concurrency.md), [bulk-inference-campaign.md](bulk-inference-campaign.md), [MEASUREMENT.md](../../MEASUREMENT.md)

> **2026-06-13 finalization bridge**: [standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md) consolidates the older audits into the main workflow pickup plan. Use that file for the next implementation pass; continue recording commit-level progress and guard counts here.

## 2026-07-26 Staleness Review

W4 remains active in the [routing and optimization
index](routing-and-optimization-index.md) and
[design-backlog triage](design-backlog-triage-2026-07-23.md). The v8
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
- [ ] **W4 - Consumer migration**: continue migrating remaining stack-sensitive consumers to generated stack priors or explicit degraded fallbacks. Use the N11/N11a handoffs and `stack_change_surface_manifest.yaml` for prioritization.
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
- [ ] **SCG-TEST-LOGDIR — tests must never write to the live `/workspace/logs/progress/`.** (filed 2026-10-03,
  workspace-ec) An API test falls back to that directory when run from a worktree with no `logs/`; on 2026-10-03 it
  wrote 2 synthetic `contention_denied` rows into the live 2026-10-03 progress file (deleted with operator OK).
  Point the fallback at a tmp dir under pytest (conftest fixture) and add a test that the live dir is untouched.
- [ ] **SCG-PRIORS-WARM — `stack_priors` must not classify WARM-tier roles as `live_stack`.** (filed 2026-10-03,
  workspace-ec, found fixing 19 stale test fixtures on orch `fix/main-test-failures-ec` d97004f6 / 9d40c30b) After
  STACKCHG-DFLASH2 moved `worker_vision` (:8086) to cold CPU, WARM tier, the compiled `stack_priors` still lists the
  vision roles as `live_stack`, so seeding's DEFAULT_ROLES include :8086, which a default `start` no longer launches.
  Fix the compiler classification (launch tier HOT only, or an explicit `warm` class), recompile, and add a test that
  a WARM role never lands in DEFAULT_ROLES. Derived output changes, so it ships as a stack-change package.
- [ ] **SCG-TEST-ORDER — fix the order-dependent `test_safety_gate_baseline_eligibility` failure.** (filed 2026-10-03,
  workspace-ec) `test_reproduced_promotion_uses_representative_median…` fails or passes depending on test order, on
  origin/main as well as the integration branch. Find the leaked state (module global, env, or monkeypatch order),
  isolate it in a fixture, and prove it with `pytest -p no:randomly` in both orders plus the full `tests/unit` run.
  - 2026-10-03: the full `tests/unit` run on `integ/api-reload-2-ec` passed it, 15979 passed / 0 failed
    (`/mnt/raid0/llm/tmp/integ2-ec/full_unit3.log`). That is one order, not a fix: the leaked state is unfound, so
    the task stays open.
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
- [ ] **SCG-ENVOVR-EXPIRED — an expired embedder override of an UNDECLARED key is silent in env attestation.**
  (filed 2026-10-03, workspace-ec, found building the diagnostic override, orch aa1d6894) In
  `scripts/server/env_attestation.py` (~:200-207) the loop over keys the embedder record overrides but the stack does
  not declare (e.g. `KMP_LIBRARY`) appends EXPECTED when the record covers the live value and does nothing otherwise.
  So an expired record, or one naming another pid, leaves a live undeclared key unreported. The same case on the new
  diagnostic path is an ERROR (`:208-224`). Add the missing branch: an ERROR with the EXPIRED/restore hint, matching
  the diagnostic path. Test it with an expired record plus a live `KMP_LIBRARY`. Done when attestation reports that
  case as an error and the existing embedder tests stay green.
- [ ] **SCG-GITNEXUS-ORCH — re-index the stale orchestrator GitNexus index.** (filed 2026-10-03, workspace-ec) A
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
- [ ] **SCG-FASTPATH — the stack-change skill offers the fast path first for an urgent production fix**
  (filed 2026-10-03, from `INC-20261003-urgent-fix-slowed-by-bundling`). When live serving is wrong and the
  operator wants it fixed now, phase 0 presents (a) an operator-terminal relaunch with the target argv, then (b)
  the permanent package behind it — instead of only (b). It also refuses to bundle an unrelated lineup move into
  an urgent package without the operator choosing that. Edit `.claude/skills/stack-change/SKILL.md` phase 0.
- [ ] **SCG-RULING-TO-FIELD — an operator recipe ruling must land as a registry field plus a compile check, or a
  task that does so** (filed 2026-10-03, same incident). Add to the stack-change skill's intake: any operator
  ruling that names a launch recipe ("use X for model Y") is a stack-change intent, not handoff prose; the
  handoff carries only a pointer to the package or to an open `- [ ]` task.

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
