# AutoKernel Unified-Surface Program — one champion, one accumulator, one runbook for CPU + GPU kernel work

**Status**: SCOPED UNIFIED-LOOP IMPLEMENTATION COMPLETE · opened 2026-09-07 · original campaign owners `ak-rebuild-20260828` (loop)
and `inf70-audit` / `workspace-1c` (CPU); both research sessions closed. Current implementation owner:
`autokernel-unified-20260908` · rider on [`autokernel-rebuild-program.md`](autokernel-rebuild-program.md)
(R23 series) and [`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md) (FOLD series)
**Index row**: `inference-research-index.md` → this file. **Domain**: inference research.

> **Operator correction, 2026-09-09:** extend the working loop; do not replace it with
> a prerequisite-heavy framework. Prioritize an actual five-loop experimental GLM CPU
> run, fix observed failures and retry. Unpublished diagnostic/retention expansion is
> set aside, not a launch dependency. Preserve existing GPU behavior, original
> measurement reuse, bounded anchor pruning, resource ownership and production freezes.
> The new standalone route is incomplete (no source/build dispatch; ordinary runtime
> settlement defaults to invalid) and is not an accepted replacement. The original
> feature scope remains CPU/GPU/candidate targeting and reliable autonomous operation.

**2026-09-10 checkpoint:** the existing GLM CPU trial completed all five measured
iterations and exited 0 after 248.2 minutes. Each used five original A/B pairs;
all were `measured_null` below the unchanged 7.801% floor. No keep or qualified gain.
Separately, the serial target wrapper is published and hermetically tested; it has
not run a live CPU/GPU rotation. See the [operating CLI](../../docs/guides/agent-workflows/agent-loop-design.md#operating-the-existing-loop-across-targets).
The five-iteration **pre-serial existing-loop** trial is complete. The final installed
all-eight-target dry run, separate original GPU hardware iteration, required-target LOO
code path, fresh CPU instrument selection and live dashboard capability verification are
also complete as of 2026-09-10. They do not prove one final-code serial owner rotated live
CPU and GPU work: the GLM run predates those hooks and used the legacy 7.801% floor. Full
acceptance therefore remains open until the final owner runs the required hardware path.

**2026-09-11 scoped completion:** the final owner ran that hardware path. The installed
serial loop completed six alternating target batches in one process across the selected
GLM-5.3-Flash CPU target and production GPU serving target. State closed with
`next_batch=6`, `active=null`, no failed targets, no outstanding issued selections and ten
accounted held-resource receipts. Four GLM batches in this campaign plus the valid earlier
v4 GLM batch complete the requested five-loop GLM trial. Three reached measurement:
`+0.186%`, `-3.360%` and `-2.152%`; all were measured nulls under their applicable matched
floor. The remaining two GLM attempts were refused during hypothesis formation. GPU batches
also settled cleanly (`refused_at_formation`, then `planner_transient`) without a fabricated
measurement. There was no keep, promotion or production-kernel mutation.

The only execution defect exposed by the run was corrected at research commit `3aa79c89`:
resumed champion-of-record verification now forwards the explicit unverified-anchor policy,
and a known pre-claim identity failure settles its issued scheduler selection. The exact v6
dry run and hardware run are retained at
`/mnt/raid0/llm/tmp/aku-final-glm-gpu-20260911-v6-dry-run.log` (SHA-256
`731a45f7b8c350a01820ebe5a6d2461cbbdb0ed58d60c778dae51dccc5e615f1`) and
`/mnt/raid0/llm/tmp/aku-final-glm-gpu-20260911-v6.log` (SHA-256
`1a820aa9c433f79be32d80ae06223b3aa3c92a6195d03377091df451753f99eb`).
The live dashboard was reloaded against that v6 store and verified to report
`selected_producer=serial_router`, `serial_state=complete`, both retained targets and the
attributed DFlash2/Qwen4Next capabilities. ROOT commit `2e1dd002` fixes terminal serial
campaign classification. Broader replacement-architecture tasks retained below are not
launch dependencies and are outside this scoped extension of the working loop.

- [x] **Required-target validation aggregate follows the current shared tip**: ✅ 2026-09-10.
  Serial state now retains an exact aggregate over every production target and every
  target that authored a keep still present in the ordered lineage. The latest author
  alone is the intended-gain target; other rows remain non-regression checks. Missing
  or stale evidence clears/pends the aggregate rather than preserving an old pass.
  Main27 serial checks passed11.98s. This observation does not yet enforce LOO,
  rebaseline or COR advancement; those remain the next execution seam.

- [x] **Targets author against the shared source tip, retaining their own baseline/history**: ✅ 2026-09-10.
  Cross-target validation builds the target recipe and records original provenance;
  subsequent authoring uses the source receipt's actual checkout/branch and that
  validated build. Target continuation identity remains separate. Same-target
  cross-checkout resume reuses its exact retained current build. No branch reset,
  cherry-pick or copy is used to switch targets. Main31 serial/outcome/validation
  checks passed23.95s, including A keep→B validation/descendant keep→A real
  validation/source iteration and B self-resume startup. Aggregate required-target
  LOO/rebaseline/COR integration remains separate unfinished work.

- [x] **Original GPU positive/historical control supplier is connected**: ✅ 2026-09-10.
  Research e019bd52/main981d64ac retains native benchmark means and original held
  CPU/GPU contexts through existing calibration and T0–T2 evaluators. Failed setup
  retains raw observations; same-owner recovery reuses completed arms. The exact
  historical paired-effect range is an engineering replay tolerance, not a new
  gain threshold or confidence interval. Original governed adapter captures these
  observations with empty protocol; no hardware qualification is inferred.
  Main55 research checks plus8 subtests passed15.23s; ROOT27 passed0.38s without
  skips. Actual GPU control replay and mixed hardware acceptance remain unverified.

- [x] **Completed serial campaigns retain selectable target details**: ✅ 2026-09-10.
  The existing dashboard follows bounded original last-result references, verifies
  exact terminal target status, and lets the operator select each retained batch.
  Canonical champion/history remain separate and visible. Missing or superseded
  target reports show an unavailable reason; no current activity or cumulative
  totals are invented. Main36 reader/page/terminal checks passed2.52s, including
  CPU keep and GPU null fixtures. This does not establish a live mixed hardware run.

- [x] **Last completed outcome retains an optional original-evidence pointer**: ✅ 2026-09-10.
  Serial continuation carries at most 12KiB of reference metadata to the existing
  serving receipt/runtime result, not duplicated measurements or a second ledger.
  Explicit diagnostics use original readers; continuation loading never invokes
  that expensive read, and missing optional evidence does not block restart.
  Main28 outcome/serial checks passed23.78s. No scheduler weights, scientific
  eligibility, thresholds or hardware results change in this slice.

- [x] **Distinct common-Git worktrees receive target-recipe source validation**: ✅ 2026-09-10.
  Preserve target A; prove the source checkout's exact shared-Git commit/tree and
  clean state again under the held build claim; build target-specific B and run
  original correctness/serving comparison. Build failure records debt without
  rebinding a nonexistent binary. Immutable old validation references reopen after
  source HEAD advances. Legacy source keys migrate by original references/ancestry;
  subsequent direct lookup avoids whole-history scanning. Divergent keeps cannot
  replace the forward shared pointer. Main28 serial/validation/matched checks
  passed13.08s. No hardware or canonical promotion. This does not yet route every
  target's source authoring onto one shared tip or execute required-target LOO.

- [x] **Aggregate serving gates feed the original archive and belief consumer**: ✅ 2026-09-10.
  Both promotion and nonpromotion archive the original whole-bundle comparison with
  COR/tip, keep membership and trigger before existing state advancement. Existing
  divergence recall fields remain; a successful aggregate observation is not another
  source keep. The original export callback reaches the observation-only ROOT reader
  and planner. Main21 checks passed1.23s; worker37 passed1.21s. Actual PROMOTE and
  DIVERGED fixtures verify duplicate ingestion/restart preserve receipt bytes and do
  not repeat measurement. Numerical verdicts, cadence and serving source are unchanged.

- [x] **Original GPU runtime path uses both held contexts and numeric device observations**: ✅ 2026-09-10.
  Planner, runtime fast path, ROCm0 correctness, calibration/window capture and
  recovery now retain the original CPU-host and GPU contexts separately. Device
  observations cover request endpoints and interior gaps under existing limits.
  Missing GPU control suppliers refuse setup before calibration, including explicit
  --calibrate-runtime; observation-only comparison/source research remain available.
  No CPU control band, policy, threshold or qualified keep is invented. Main26
  GPU/original-GPU checks passed3.66s; worker43 composed GPU/matched-CPU checks
  passed19.45s. Nine primary files match the frozen packet. Synthetic HTTP/device
  fixtures establish execution wiring, not hardware qualification. Actual positive/
  historical GPU control suppliers and qualified GPU runtime admission remain open.

- [x] **Fresh unified CPU source measurements use matched process-pair calibration**: ✅ 2026-09-10.
  Fresh CPU enrollment selects matched_process_v2 and pins that choice before the
  first child. Original v1 floors/continuations and direct CLI/GPU defaults remain
  unchanged. New calibration uses24 independent A/A pairs (48 launches), randomized
  balanced AB/BA, and the existing ratio-of-arm-medians reducer at the comparison's
  pair count. Separate versioned floors bind workload/placement; source-treatment
  reuse remains allowed. The descriptive interval does not replace the scalar gate.
  All four source comparison paths, cross-target validation, archive/belief capture
  and exact CPU profile source pin are connected. Reused original validation does
  not rerun calibration/A-B. Main25 matched checks passed16.60s; worker62 producer
  and29 ROOT checks passed. Existing GLM results are not regraded or rerun. This is
  source measurement, not full strict runtime qualification or hardware transfer.

- [x] **Shared-worktree source changes receive original-owner cross-target validation**: ✅ 2026-09-10.
  Retained original keep receipts identify the whole source, original target baseline,
  request and recipe. Validation is an explicit charged scheduler stage, not a hidden
  priority filter. Pending retries require intervening ordinary research; missing
  evidence remains pending, not a regression or pass. Exact single-keep observations
  are reused without another calibration/A-B; changed assembled candidates remeasure.
  Existing serving/FOLD-2 rules decide, and fresh rows use the existing archive/belief
  export. Reuse preserves original timestamps/bytes. Unused promotion scaffolding was
  removed. Main70 combined checks,29 boundary follow-ups and35 archive/belief checks
  passed; all8 primary files match acceptance. Distinct CPU/GPU worktree validation,
  required-target final aggregation and canonical promotion are NOT completed here.

- [x] **Serial selection learns bounded cost forecasts from original held receipts**: ✅ 2026-09-10.
  Completed matching measured-search batches supply a last8/p75 duration estimate;
  exact recipe/request/source/runtime/scope/accounting identities prevent unrelated
  reuse. Failed/invalid attempts remain charged but do not train successful duration.
  Original selection, coverage, seed opportunity and stage limits remain unchanged.
  Main60 combined cost/serial/control/scheduling tests passed11.93s, including real
  private-flock child, changed next estimate and restart with no repeated settlement.
  Scientific-outcome adaptive reward weights remain incomplete; no new grader added.

- [x] **Existing dashboard operates the original serial controls**: ✅ 2026-09-10.
  Pause/resume/drain buttons use the authenticated serial listener and exact owner,
  revision, batch and target. Tokens remain in tab memory. Lost acknowledgements retry
  the original ID; a new owner detaches the old uncertainty without replaying it or
  disabling new commands. Malformed optional controls disable only their own card,
  not the valid child/measurement/history display. Main137 reader/browser/producer
  integration tests passed4.80s against published research8c723082. No live command
  issued; listener configuration remains an explicit next-start option.

- [x] **Original serial owner accepts authenticated pause/resume/drain**: ✅ 2026-09-10.
  Optional loopback listener reuses the existing authenticated HTTP transport. Commands
  bind owner/configuration/revision/batch/target; the serial execution thread persists
  acknowledgements. Pause finishes the batch and accounting, resume permits selection,
  and drain uses the captured child's original STOP/SIGTERM path. Failed cleanup never
  earns a completed drain. Persisted pause requires a resume channel or explicit STOP.
  Main33 controls/serial/runtime-recovery/progress tests passed74.75s; exact two-child
  receipt accounting remains6 seconds despite acknowledgement retry. No hardware run
  or live listener started. Dashboard integration is recorded in the following checkpoint above.

- [x] **Original-owner runtime interruption recovery**: ✅ 2026-09-10.
  Serial retries only a typed recoverable runtime interruption after original child
  termination and held-resource accounting; unrelated failed targets remain excluded.
  Fresh ownership resumes the original pending pair/allocation in a new window, with
  completed control/results reused and old samples kept separate. Unknown child cleanup
  aborts before any fallback measurement. Historical completed results reopen even when
  the caller lost its result reference. Main combined43 checks pass plus the corrected
  old cleanup-exception fixture1pass; original real-child recovery tests are included.
  Synthetic measurement edges only; no claim that arbitrary orphan cleanup is automatic.

- [x] **Existing dashboard shows dated runtime preparation and selected recipe**: ✅ 2026-09-10.
  Original checkpoint callbacks supply phase/counts/pending state; heartbeat cannot
  refresh the observation timestamp. Existing page renders the human-readable recipe
  with digests/caveats collapsed. Diagnostics cannot change admission or checkpoint
  success. Main45 writer/reader/page checks pass; separate producer44 checks passed
  before recovery composition. Authenticated serial controls remain separate work.

- [x] **Fresh selected CPU/GPU targets prepare their missing source floor automatically**: ✅ 2026-09-10.
  The existing startup calibration now covers full targets as well as reduced screens.
  Only an absent exact recipe/request floor triggers automatic preparation, using the
  existing serving pair count (minimum2); an explicit calibration count still overrides.
  Existing GLM7.801 is reused, and malformed/mismatched records still refuse unchanged.
  Actual full8 dry run exits0: seven fresh production targets schedule5 launches each,
  GLM schedules none. Original calibration/estimator/claim ownership is unchanged.
  This is startup/execution wiring, not new hardware calibration or improved precision.

- [x] **Shared-source target switching and all-eight-target serial startup**: ✅ 2026-09-10.
  Targets can serialize one exact experimental worktree/branch while retaining their own
  request/history. Digest-bound latest-source continuation rebinds the existing build;
  a target's older personal continuation does not force an obsolete source anchor.
  Main118 tests pass, including actual-owner synthetic A keep -> B keep -> A startup.
  Full seven-production-plus-GLM serial dry run exits0 from primary; original GLM floor
  remains7.801, new production floors remain absent, and the retained GPU build's existing
  unattested warning remains explicit. No inference/build/state directory created.
  Log: `/mnt/raid0/llm/tmp/aku-full-roster-dryrun-inputs-20260910/shared-source-primary-dry-run.log`,
  SHA256 b704dc907b9021f267c80e9be5552825581e856df3db2e14f2b3673c712c605a.
  Shared candidate folding and runtime-recipe transport remain separate active work;
  neither is implied by this source-continuation checkpoint.

- [x] **Automatic CPU screening connects selection to same-build full confirmation**: ✅ 2026-09-10.
  The existing serial loop selects quarter/half/full scope from qualitative mechanism
  history before resource selection; both arms share the selected geometry and its own
  floor. Reduced positives retain the original patch and executable as `keep_candidate`,
  not champion promotion. Full confirmation reuses that candidate and original requests;
  only an ordinary full keep promotes. Pending confirmation protects source/build aliases
  and remains explicit scope debt if unaffordable. Real production frontier IDs now reach
  the existing coverage policy. Main113 integration checks pass; actual scheduler-selected
  GLM quarter dry run exits0 with CPU0-23 and no borrowed full-size floor. These checks
  establish startup and fixture execution, not live transfer or CPU/GPU coexistence.

- [x] **Inherited CPU recipes use explicitly declared campaign affinity**: ✅ 2026-09-10.
  Actual worker_fast production input omitted taskset and was rejected. The original
  run now makes its inherited affinity explicit from enrolled resources, preserving
  command, artifacts, environment and original snapshot provenance. Standalone inputs
  without declared resources still require affinity. Main70 tests pass; all seven
  production workloads plus GLM pass individual original-owner preflight. Full-roster
  serial shared-source handling is proven by the later all-eight-target checkpoint above.

- [x] **Existing serial CPU+GPU owned-roster dry run passes**: ✅ 2026-09-10.
  Actual GLM c463 CPU and canonical ef811 GPU inputs resolve and both original owner
  dry runs exit0 (0.44s), with sol-medium actors and derived scheduler. Fixed production
  draft-mtp/self_draft import mismatch and the scheduled-child topology import. Main75
  joined tests pass. Original GLM floor7.801 retained; new GPU requests correctly have no
  floor and retained hand-built anchor remains explicitly unattested. No inference,
  state directory or GPU memory store created. Evidence dry-run.log SHA130ba42ffe18405efe4824c3be5de2458189986a3ac88633e1c9f821e098d493
  under `/mnt/raid0/llm/tmp/aku-cpu-gpu-dryrun-inputs-20260910`. This is not live rotation proof.

- [x] **Build rebinding follows actual ELF loader names across version changes**: ✅ 2026-09-10.
  Actual frozen10125 -> champion10301 dry-run preparation exposed full-version DSO
  filename assumptions. Existing exact paths remain unchanged; missing versions resolve
  through the original SONAME to a contained candidate with matching SONAME. External
  libraries remain fixed. Main42 checks passed; real16-DSO GPU rebinding matches the
  independently pinned retained build. No kernel rebuild or inference was needed.

- [x] **Actual production command grammar resolves all seven exported targets**: ✅ 2026-09-10.
  Preserve emitted draft probability/thread/logging flags and frozen v9's omitted
  ubatch default512; conflicting aliases and invalid values still refuse. Main112
  research checks and32 original profile producer/reader checks passed. Profile source
  pin updated additively; historical captures retain their original accepted identities.
  Seven actual production recipes resolve with supplemental pinned ROCm DSOs. Original
  export artifact verification passed; the supplemental export explicitly did not repeat
  full artifact verification. No hardware launch or mixed-target performance claim.

- [x] **Existing serial owner selects and accounts original held resources**: ✅ 2026-09-10.
  Owned rosters derive scheduler inputs without an extra manifest. One iteration per
  stage; fresh proposal identities support repeated passes, failed targets are excluded,
  and terminal restart accounts once before new selection. Original claim open/close
  intervals charge CPU/GPU components; no child-wall-time substitute. Main 101 tests
  passed and actual GLM auto-scheduled dry run exited0. Continuous defaults stop at
  1000 attempts, declared budget or STOP; this is not live mixed-target proof.

- [x] **Split-model import preserves the launch entry shard**: ✅ 2026-09-10.
  Singular campaign/launch model slots now select the shard named by argv rather
  than silently retaining the last shard. The original export retains every pin.
  Main 21 enrollment tests passed, including split-model launch resolution.

- [x] **Completed dashboard runs no longer look like stalled measurements**: ✅ 2026-09-10.
  Final reports retain original timestamps/raw steps but display a terminal step and
  FINAL REPORT/FAILED REPORT badge. Running producers retain heartbeat expiry; future
  timestamps remain malformed. Main 35 producer/reader/browser tests passed, including
  a running router with a completed child. Actual GLM artifact reads complete at 5/5.

- [x] **Shared historical mechanisms reach the existing planner automatically**: ✅ 2026-09-10.
  Owned-target rosters supply canonical and sibling stores to read-only recall.
  Bounded selection retains useful keeps/nulls despite transient floods and rotates
  across one-iteration child restarts. Original scope/caveats remain separate from
  local applicability and gains. Main 104 tests passed; actual canonical-store read
  returned one keep, three measured nulls and one refusal without errors.
  This is historical suggestion recall, not demonstrated transfer or runtime admission.

- [x] **Production enrollment includes every split-GGUF shard**: ✅ 2026-09-10.
  The existing exporter expands exact numbered model/drafter families and requires
  each supplied artifact pin; missing siblings leave the target waiting. No directory
  discovery, model mutation or implicit hashing was added. Main 20 enrollment tests
  passed. This closes artifact association, not the broader mixed-target acceptance gate.

- [x] **Five actual GLM CPU research iterations completed unattended**: ✅ 2026-09-10.
  Original controller PID1380863 / exec21102 exited 0; five source/build/correctness/A-B
  iterations, no keeps. Effects: +0.950164%, +1.454288%, +1.181050%, +1.248272%,
  +0.332447%; every comparison retains five samples per arm. Original result:
  `/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-output-continuation/loop-run.json`, SHA256
  `a489ee01fa6807e202ec69c44d2d59c2ae2c3be28fa766c48ea90d3b099ce408`.
  Parent and all ten final-iteration server PIDs are absent; floor SHA479db985… unchanged.
  Final rejected source remains in its owned worker lane and archive, not promoted.
  This controller predates newer continuation/telemetry/feedback/scheduler hooks;
  their absence from its output is not evidence those newer paths were exercised.
  Observation-grade workflow result only; AKU-12b's broader integration gates remain open.

- [x] **Serial dashboard accepts the restart producer's process identity**: ✅ 2026-09-10.
  Corrected the closed reader contract after the restart producer added original
  PID/start/boot identity. Old payloads remain supported; optional identity must match
  the child PID and exact shape. Batch/target joining is unchanged. Main 26 tests passed,
  including actual serial producer through reader and browser rendering with history intact.

- [x] **Interrupted source survives the existing lane reset**: ✅ 2026-09-10.
  STOP-before-gate and reused dirty lanes now retain original HEAD plus an immutable
  hash-qualified patch before reset. Tracked recipe/docs changes remain included;
  newly captured untracked files are bounded kernel-source text only. Archive failure
  prevents reset. Main 56 tests passed, including actual Git round-trip recovery.
  Build pruning is unchanged; this does not resume unfinished measurements automatically.

- [x] **Serial restart reuses a completed child without replay**: ✅ 2026-09-10.
  Startup reopens the exact retained batch/target/arguments result and checks the
  original child's kernel identity before advancing once. Live or unreadable children
  refuse without signals or adoption; STOP persists. Missing/mismatched results retain
  original state and logs. Main 26 real-child/serial tests passed in 10.27s. This fixes
  the crash between child completion and router checkpoint, not unfinished-work recovery.

- [x] **Existing-loop CPU factual noise and bounded original-arm recovery**: ✅ 2026-09-10.
  Research `64923e9f` / main `591616c0` records load/swap/PSI and bounded non-target
  CPU activity without turning ordinary builds/pressure into blockers. Original
  PID/start substitution or two affinity-violation samples for the same TID/start
  produce durable `measurement_invalid`, not a null. The existing tail archives
  before one budgeted retry of the same failed server launch, retaining valid arms,
  hypothesis/patch/build and exact requests. STOP, budget exhaustion, repeated
  invalidity and unresolved cleanup prevent retry. Main: 39 joined tests and 41 ROOT
  profile/corpus tests passed; historical source pins remain supported. Hermetic
  checks only, no live reload or hardware change. In-memory continuation is not
  restart recovery, and competing-inference classification remains unproven.

- [x] **Existing-loop same-binary runtime observation and readers**: ✅ 2026-09-10.
  Typed CPU runtime treatments skip source authoring, diff review, build and source
  promotion; existing tail ownership, correctness and serving A/B remain the owners.
  Each arm retains its actual recipe with identical executable and frozen requests.
  `runtime_observed` is measured, not a keep or scientific null; the existing belief
  reader accepts its original per-arm identities without claiming qualified evidence.
  Main checks: 72 research tests and 10 ROOT reader/render tests passed. HTTP fixtures,
  not a hardware runtime experiment. The current live controller was not reloaded.
- [x] **Prevalidated runtime options bypass routine critics**: ✅ 2026-09-10.
  Research `64923e9f` retains deterministic current-anchor/option checks and tail
  ownership/correctness gates; source changes retain review. Main 42 focused tests passed.
- [x] **Same-owner runtime admission and serial recipe transport**: ✅ 2026-09-10.
  Original evaluator/calibration/control owners consume the direct loop's retained
  HTTP evidence. Runtime keeps select a recipe without source promotion; subsequent
  source comparisons use a recipe-bound floor. Existing bounded pruning protects
  only the selected admission's original build in addition to COR/current anchors.
  Serial resumes target-local selection with separate latest-source rebinding.
  Main54 admission/control checks pass; a fixture-only continuation assertion was
  corrected separately. Full8 actual dry run exits0 with GLM floor7.801 unchanged;
  32 profile-reader checks pass. No hardware runtime gain or interrupted-owner
  recovery is claimed by this checkpoint.
- [ ] **Complete runtime fast-path admission and continuation**: finish interrupted-owner recovery; use original applicable calibration/evidence and
  retain/select/resume an accepted runtime recipe without a source promotion. Runtime
  observations alone do not complete AK-AUTO-07 or the runtime champion requirement.

- [x] **Existing-loop CPU profile observation reaches actor and belief readers**: ✅ 2026-09-10.
  The current CPU launch and original frozen request feed the existing owned perf capture
  in a separate observational server run at startup and after a keep, never after a null.
  Actor prompts receive sampled symbol periods/fractions, original record identity or an
  unavailable reason; acceptance pairs/floors are unchanged. ROOT uses the existing profile
  measurement projector/corpus, without a direct integrity or `PROFILE_VERIFIED` row.
  Focused checks: 114 research and 40 ROOT passed, no skips. Tiny HTTP/synthetic perf only;
  no hardware profiling, production mutation, qualified gain or live process reload.

- [x] **First actual CPU source-to-measurement iteration and automatic continuation**:
  ✅ 2026-09-10. On research `2059e30e`, `akm-q4k-avx512-paired-y` passed through
  source authoring, build, the existing MUL_MAT correctness gate and five serving pairs.
  The original loop durably recorded `measured_null`: effect fraction
  `0.009501638190257289` (+0.95016%) did not clear the 7.801% floor. No keep or qualified
  gain. Runtime PID1380863 automatically entered iteration 2; this checkpoint is one
  completed/measured iteration, not completion of the five-iteration test.

- [x] **Dashboard restart configuration and observed false benchmark detection**:
  ✅ 2026-09-09. Existing watchdog replaced the configured hub without inheriting its
  store setting. Re-adopted that same watchdog with explicit primary `EPYC_ROOT` and
  `AUTOKERNEL_LOOP_STORE_ROOT`; its real replacement hub retained trial/history split.
  Guard mistook Codex prompt text for benchmark identity: orchestrator `5e3a9ec7`
  (main `03ddb449`) checks executable/script operands instead. Main 61 focused tests
  passed; real benchmark identities and placement rules remain enforced.

- [x] **Actual CPU actor-template failure repaired**: ✅ 2026-09-09.
  The first live attempts proved target metadata was dropped and CUDA paths forced;
  actors returned no valid target/empty paths. `ee76b37b` (research main `2059e30e`)
  delivers original CPU target context and corrects planner/author/critic wording.
  Main 33 actor checks passed. Stopped the failed run cleanly after two failures and
  one stopped formation; preserved all five calibration samples/floor for reuse.

- [x] **Separate live trial from retained champion/history readers**: ✅ 2026-09-09.
  Corrected the store-selection regression: live GLM status no longer relocates canonical
  measurements or the 2,397-row historical experiment database. Canonical capability
  fallback reopens five original evidence entries with historical attribution and
  verified lineage; no new measurement or inferred production ratio is manufactured.
  Main focused combined checks:19 passed. Experimental CPU status now has explicit scope
  (`51abc7a3`, research main `e2a01699`); the already-running trial is not restarted.

- [x] **Live CPU trial dashboard selection**: ✅ 2026-09-09. Orchestrator
  `59782734` → main `0ad401dd` selects the dedicated GLM store through the existing
  dashboard environment. Dashboard-only reload verified PID1339228; `/api/loop/health`
  reports fresh CPU evidence. Trial PID1329820 remained live. This is current-trial
  visibility, not completion of automatic multi-campaign dashboard selection.

- [x] **Existing-loop CPU serving and request-bound calibration**: ✅ 2026-09-09.
  Published serving forwarding `1799ade6` → main `12bfe8a3` and existing-loop CPU
  entry route `2f066e53` → main `fbecc61c`. CPU candidates reuse the existing
  source/build/measurement/keep owners; optional resolved launches and exact frozen
  requests reach both serving arms. Request-bound floors cannot borrow a legacy floor;
  uncalibrated measurements remain non-decisive. Main actual child/HTTP checks:4 passed;
  existing focused serving checks:95 passed plus11 subtests. Legacy GPU defaults retained.
- [x] **Original experimental CPU anchor identity and unwaived dry run**: ✅ 2026-09-09.
  Published `863128c1` → main `2032e5be`: the existing CPU entry route verifies the
  original experimental build identity against source/head and inventory, without
  inventing promotion provenance or using the unverified-anchor waiver. Main focused
  identity checks:27 passed plus4 subtests; startup worker's unwaived dry run exited0.
  This proves startup wiring only, not a qualified result or five-loop completion.
  Main subsequently verified live PID1329820 at original-request CPU calibration,
  iterations0/5; observe that existing loop and fix actual failures, not a replacement.
- [x] **CPU-specific actor instructions and workload-scoped evidence epoch**: ✅ 2026-09-09.
  Published `3dddec73` → main `99f91479`; main 3 focused tests passed. CPU actors receive
  explicit selected-target instructions rather than GPU profiling directives; CPU launch
  and frozen-prompt digests join the evidence epoch. No fabricated CPU hotspots or GPU
  timing reuse, and no change to ordinary GPU instructions/epochs.

- [x] **Compatibility repair — fresh legacy stores and anchor pruning**: ✅ 2026-09-09.
  Fresh-store initialization restored without resetting populated/corrupt history
  (`009ef659`, main `cdd13df5`; main 31 focused tests). Legacy keep path again uses
  bounded existing pruning with current/COR protection (`457f5e37`, main `602bdf16`;
  actual keep-path regression passes with deletion intercepted). No live deletion.
- [x] **GLM request transport and original topology order**: ✅ 2026-09-09.
  Original token-array/cache/seed42 requests and explicit CPU launch flags use existing
  serving code (`002fc0d0`, main `bfb86301`); retained taskset/numactl order supported
  (`20b9621c`, main `5038e406`). Main focused combined check:50 passed. No hardware
  performance or five-loop completion claim.

> **Implementation authorization, 2026-09-08:** the operator has now directed implementation of this
> handoff, using **GPT-5.6-sol medium** workers for bounded work and the main thread for coordination,
> review and integration. This supersedes the earlier documentation-only scope, not protected production
> freezes, measurement ratification, live-research relaunch or OP-41's explicit ownership/sequencing gate.
> [§9](#implementation-ledger-20260908) is the current execution ledger. The notebook remains the design
> contract; old campaign checkboxes are not proof of present implementation or inherited ownership.

> **2026-09-08 planning update — documentation only.** The operator is iterating on a VERY detailed
> autonomy plan, including IMPLEMENTATION details; this session is explicitly **not implementing it**.
> [§8 — autonomy design notebook](#autonomy-design-20260908) captures accepted preferences, dated audit
> findings, proposed interfaces/algorithms, migration, tests, and provisional numerical defaults.
> It is not an approved implementation specification or permission to launch research. Consolidation
> ownership and the no-relaunch directive below remain in force. P1 records the fold at `ef81196d5`;
> earlier pending-fold/running-run-30 descriptions are historical, not live-process observations.
> **Final-close-out audit:** [§8.16](#final-closeout-audit-20260908) reconciles both completed sessions,
> ratified measurement rules, measured-versus-delivery identity, per-surface recipes, and implementation
> refinements. It supersedes conflicting earlier design assumptions, not the operator's sequencing gates.
> **Fresh implementation-contract review:** [§8.17](#implementation-contract-review-20260908) resolves
> search-phase policy, the already-ruled four-keep cadence, validation transactions, bounded scheduling,
> scoped evidence use, restart fencing and control/status consistency. Details remain proposals except
> where explicitly identified as existing ratified policy; no campaign restart or implementation follows.

## Operator directive (2026-09-07, verbatim intent)

> "Shouldn't both CPU and GPU kernel work be subsumed by the autokernel loop (which would then be
> responsible for coordinating when heavy CPU is used for building kernels) and its accumulated keep +
> champion promotion runbook, and potentially have a single session monitoring autokernel's runs?"
>
> Ruling: **"unify the champion, the accumulator and the promotion runbook now, so CPU levers land on the
> same branch, get bundled toward the same serving gate, and inherit the durable bundle and the
> leave-one-out arm"** — relayed to the CPU session 2026-09-07 with the request to start immediately.
> Then, as the design step: a config-arm type and per-surface budgets; subsume INF-70's *measurement*
> into the loop first, its *authoring* only once the config arm exists; one session monitors both surfaces.

**Operator context added 2026-09-07 (north star for every phase):** *"autokernel, when running, should
own both GPU and CPU resources, and maximally use them to advance kernel research on all fronts. That's
what the loop needs to be built up to handle."* So U4 is not a courtesy scheduler: the loop is the OWNER of
both resources and their saturation is a KPI — idle-while-claimed is reported per resource, the CPU surface
is a co-equal search frontier (not a fold target), and while a GPU arm runs the CPU should be running CPU
arms or builds subject to the contention bounds in §3.4. The manual CPU campaign is transitional.

**Operator directive 2026-09-08 (verbatim; supersedes the cadence above until consolidation completes):**

> "I want no more pure kernel inference research until we have a FULLY consolidated champion collecting
> all GPU AND CPU performance progress."

> "WE CANNOT AFFORD to lose performance progress on either the GPU or the CPU inference work. WE MUST
> FOCUS on consolidating all kept performance levers and persisting them."

NO research relaunch after the fold window; consolidation only; relaunch is a separate operator go.
The CPU session (INF-70 / `workspace-1c`) received this directly and has parked all lever campaigns.

## Start here (implementation)

1. Read §8.1 for accepted preferences and authority, §8.16 for final-session findings, and §8.17 for
   implementable contracts. Then use §8.13 to locate each proposal's existing owner/task mapping.
2. **Current execution is §9**, in dependency order, with tested bounded slices. §1–7 retain the original
   campaign design/history and other owners' checkboxes. Re-resolve their state by task text before any
   future dispatch. The fold/run-30 process descriptions are historical; neither closed session is revived.
3. Ratified measurement rules and operator directives outrank every proposal. Within proposed design,
   §8.17 refines §8.16/§8.3–15 and explicitly identifies replacements for §3 pseudocode. It does not
   silently replace current runtime behavior or waive a protocol, release gate, or operator decision.
4. Research relaunch remains a separate operator go. OP-41 implementation remains operator-owned,
   after champion finalisation → production promotion → host reboot. The new instruction authorizes
   application implementation; its relation to OP-41's narrower broker-code restriction was explicitly
   asked, not assumed. Work not dependent on that answer continues.

## 1. The problem in one paragraph

Two campaigns optimise the same production kernel tree on the same host with two lineages, two ledgers,
two measurement disciplines and no shared scheduler. The single-champion invariant (ratified 2026-08-31,
`OPERATING_CONSTRAINTS.md` 35c1a6d1: one champion aggregates ALL work between promotions) is therefore
violated by construction — the exact fork `INC-20260831-champion-lineage-fork` ended once — and the two
campaigns corrupt each other's measurements because **no CPU on this host is free of the other's work**
(§2.3). The loop already owns the discipline the unified program needs (calibrated floors, paired
alternating A/B, drift detection, refusal ledger, durable bundle, anchor guard); what it lacks is a
*surface* dimension, a *runtime-config* arm, and a *resource broker*.

## 2. Evidence this design rests on (all measured 2026-09-07 unless noted)

### 2.1 The accumulator never confirmed anything — R23-51
The bundle was rebuilt from the anchor at every startup, so each restart reset the keeps AND advanced the
champion of record to the accumulated tip. **No `epyc.autokernel.serving_ab.v1` record exists on disk; the
R23-44 serving gate has never fired.** Bundle peaked at +6.13% (5 keeps) vs an +8.84% threshold. Fixed
(durable `Bundle`, `load_bundle()` refuses state the tree no longer contains; research `706e6894`); the true
cor must be re-seeded with a MEASURED tip-vs-cor bench at the next launch (R23-51a). A unified bundle
inherits this fix for free; a hand-kept CPU ledger cannot.

### 2.2 Numbers from a contended instrument are not banked value — R23-50, INF-70 HARNESS-1
Same day, same mechanism (`akm-q4k-q8-sum-sidecar`): +6.723/+2.978/+2.374/+1.952/+1.595% and four nulls,
against a 0.668% floor — a 6.6 pp spread; ~80 re-measurements since are null-to-negative. INF-70's cold-arm
A/A: ~5% clean, **pair_p95 19.89% contended**, one arm carrying 3218% foreign CPU. Their +4.50% champion
headline (supersedes the +4.27% quoted earlier that day; 1.5149× vs pristine on 0 s-eviction rounds) is at or below its instrument's floor (sign survives on 60/60 paired wins; magnitude does not).
Historical arms cannot be retro-screened: the sampler read `184-191` as disjoint until today, so labels are
wrong, not missing. Three of our 31 `kept` rows never reached the champion (tagged
`ak/orphan-keeps-quantize-20260829`), and the pass they touch is ≤3.6% of tg128, so their +12.5% was noise.
**Consequence for design: measurement must be one system with one contention model, or every magnitude
either side quotes is provisional.**

### 2.3 Placement alone cannot isolate the historical full-host recipe — R23-49 / OP-41
Kernel-read `thread_siblings_list`: logical `c` and `c+96` share a physical core, exhaustively. Our
`jobs=64` builds on `96-183` cover 88 of INF-70's 96 bench cores (9×`cc1plus`@100% measured live); our
bench host threads on `184-191` cover the other 8; our `llama-server` was unpinned (now pinnable,
`Recipe.cpu_list`, default off until the floor is re-calibrated under a pin). **"Fence tooling out of 0-95"
has nowhere to fence to. The only real options are SERIALIZE, SCHEDULE, or ACCEPT-AND-REGRESS**, and only
a single owner can serialize builds, CPU arms and GPU arms coherently. INF-70's own builds
(`build3.sh`, `-j40`, unpinned, unlocked) have the same defect.
**Placement is not even sufficient**: both sides were correctly pinned on 2026-09-08 and still poisoned
each other through DRAM bandwidth — see the admission-control bullet at the top of §3.4.

### 2.4 What already exists and must be reused, not rebuilt
| capability | where | status |
|---|---|---|
| calibrated per-surface floors (tg128 0.638% @20 pairs; dec-b4; serving 3.536%) | `loop-memory/calibration/`, `serving-floor.*.json` | GPU surfaces only |
| paired alternating A/B + residency + drift | `loop/bench.py`, `loop/residency.py` | GPU |
| **build-recipe arm (cmake defines as a champion arm)** | D3, shipped 2026-08-30 | exists — **runtime-config arm does not** |
| durable bundle + validated reload | `loop/accumulate.py` (2026-09-07) | single-surface |
| anchor guard by OBJECT digest + incremental build | `controller/anchor_integrity.py`, `loop/anchor.py` | GPU objects; works for CPU objects unchanged |
| leave-one-out per accumulated keep on PROMOTE | R23-48 | designed, not built |
| CPU region lock (`cpu_region.{role}.{region}.lock`) | `epyc-orchestrator/src/runtime/cpu_region_lock.py` | orchestrator-owned; loop does not take it |
| sibling-expanded live foreign-load sampler | `/mnt/raid0/llm/tmp/inf70/agents/sync19-20/foreign.py` (protected) | INF-70; `/proc/<pid>/stat` deltas, not `ps %CPU` |
| fold plan + two default-ON blockers | FOLD-0..3, `docs/design/inf70-cpu-fold-into-champion-20260907.md` | specified |
| promotion runbook | `docs/reference/kernel-freeze-runbook.md` (shipped v7/v8/v9) | single candidate build, never cherry-picks |
| **rescued kernel work not yet in the champion** | [`docs/design/champion-consolidation-audit-20260908.md`](../../docs/design/champion-consolidation-audit-20260908.md) | audited 2026-09-08: 23 superseded/archive, 2 candidates + 1 decline (P1b), 2 REFUTED, 1 must-not-fold, 4 single-copy refs pushed |

**Audit note (2026-09-08).** The reuse question "is this lever already in the champion?" cannot be answered by
patch-id: v9 was rebuilt from fresh upstream, so `git cherry` calls semantically-present levers unmerged. The audit
above used `git cherry` **plus** a content grep against the champion tip `bff30cebe`. The converse hazard is sharper —
**folding a superseded decision back in is a failure class ancestry checks cannot see and cherry-equivalence waves
through** (see the MUST-NOT-FOLD entry in P1b).

## 3. Design

### 3.0 The unified iteration — pseudocode first (rule: agent loops get pseudocode before the plan)

**Historical starting design.** §8 proposes the runtime fast path, phase-specific evidence handling and
separate accumulated/validated pointers; §8.17 makes those replacements explicit. The two universal
critic passes and any-surface `cor` advancement below are not the current implementation specification.

```
STATE (durable, in loop-memory):
  champion        = one branch, ak/champion/llama-cpp-<prod-sha>, anchor == tip (object digest)
  bundle[surface] = {champion_of_record, tip, keeps[], compounded_bench_pct (MEASURED vs cor)}
                    surfaces = {gpu.tg128, cpu.<recipe-name>, ...}; ONE cor shared, per-surface gain
  floors[surface] = calibrated A/A floor per (surface, n_pairs, host-state hash)
  budgets[surface]= max iterations in flight, max arm seconds, max concurrent builds

each iteration (lane picks a surface by budget share, not round-robin):
  hypothesis  ← planner(surface, context[surface])         # context = profile+ledger+inbox for THAT surface
  kind        ← SOURCE | BUILD_RECIPE | RUNTIME_CONFIG       # RUNTIME_CONFIG is new (§3.3)
  critic pass 1 → accept | reason back to planner
  patch/recipe/config ← author(kind)
  critic pass 2 → accept | reason back
  BROKER.acquire(build_slot)                                 # §3.4: builds are heavy CPU, scheduled
     build (incremental, object digest)   [skipped for RUNTIME_CONFIG: same binary, new launch args]
  BROKER.release(build_slot)
  BROKER.acquire(surface.arm_resource)                       # gpu claim | cpu region lock role=bench
     correctness oracle(surface)
     A/B paired alternating, n from floors[surface], residency + FOREIGN-LOAD sampled during the run
  BROKER.release
  keep? → commit onto champion (SOURCE/BUILD_RECIPE) or onto codified recipe (RUNTIME_CONFIG)
        → anchor guard → bundle[surface].add_keep(MEASURED tip-vs-cor) → bundle.save()
  if any bundle[surface] clears fire_multiple × floors[surface.serving]:
        serving gate for THAT surface (its own recipe, its own llama-server)
        PROMOTE surface → cor advances (shared)
                        → RE-BASELINE: every OTHER surface re-measures tip-vs-NEW-cor on its OWN harness before
                          any compounded_bench_pct is quoted again — never carried, never rescaled ("a baseline's
                          value is a property of the tip it was taken at", INF-70 review 2026-09-07)
                        → LOO: one reverted arm per accumulated keep, ALL surfaces, as a HARD GATE on the
                          promotion record (no LOO receipt → promotion refused: LOO skipped once is
                          indistinguishable from LOO never built). Cost n_keeps × n_surfaces arms — budgeted §3.4.
                          (a CPU keep can change a GPU number: shared ggml graph code — measure, don't assume)
        DIVERGE → hold, journal, planner evidence
promotion to production: ONE full candidate build of the champion tip, all surfaces' gates demonstrated,
                         kernel-freeze-runbook, freeze-aware agent overlay baked in
```

### 3.1 Track U1 — unify champion, bundle, runbook (NOW; no loop code needed)
- CPU levers are commits on `ak/champion/llama-cpp-0db32c06e3e5`, staged on a lane branch off its tip,
  folded at a loop boundary by the reconcile precedent (`a27287015`: merge-tree disjointness, zero
  conflicts, pre-fold tags). **Never mid-run**: the anchor guard proves anchor == tip by object digest, and
  a CPU commit changes library objects.
- Both default-ON blockers opt-in first (FOLD-0): `GGML_OP_MOE_TOPK_NORM`, INF-64 fused decoder.
- CPU keeps recorded in the same durable schema (`epyc.autokernel.accumulator_bundle.v1`) with measured
  compounded gain vs cor, so the fold merges one bundle, not two ledgers.
- LOO on PROMOTE applies to the whole stack (R23-48) — CPU keeps included.
- Promotion = one candidate build (runbook), never cherry-picks.

### 3.2 Track U2 — surface dimension on the bundle and the gates
`Bundle` gains `surface`; the store keeps one file per surface; the cor is shared. Each surface has its
own screen floor, confirm rung, serving recipe and serving floor — **and each floor carries its measurement
conditions (harness, n, contention model, host-state hash), not just a number**: ours is 3.452% p95 at n=20
tg128 pairs, INF-70's is ~5% clean / 19.89% contended on a 24-prompt served harness, and the same
`compounded_bench_pct` would otherwise mean two different things in one bundle (CPU: `Recipe` with `device=CPU`,
`cpu_list`, `numa`, threads — the CPU session's canonical recipe becomes the codified artifact). The
serving gate fires per surface. The headline card shows per-surface gain over the shared cor, never a
sum or product across surfaces.

**A floor must carry its UNIT (measured 2026-09-08, INF-70 RETEST-1) — this is the field whose absence
costs three orders of magnitude.** The conditions list above (harness, n, contention model, host-state hash)
was incomplete: add **`unit` ∈ {arm, session, process}**, the scope at which the knob under test varies.
Within-session (**arm**) sd is **0.501%**; between-session (**process launch**) sd is **2.793%** — a
process-scoped knob faces a floor **~13× coarser** than an arm-scoped one. Worked consequence: INF-70's
**0.171% arm** floor says CHAMP-2 THP needs **4 sessions/side**; the correct **session-unit** answer is
**4,780** — a **1200-fold** error, and it would have been spent as real host hours. So: every floor record
states its unit, and **a gate comparing an effect to a floor of a different unit REFUSES** rather than warns.
Mirror task: `autokernel-rebuild-program.md` **R23-55** (write `unit` into `loop-memory/serving-floor.*.json`
and the bench-floor records).

**And the champion arm itself is not stable across launches (measured 2026-09-08, INF-70) — so HEADLINE
ADMISSIBILITY is a U2 property, not a reporting style.** An **identical** champion configuration measured
**24.4 → 27.4 tok/s** plain across four of that day's sessions (~**12%** spread: gate 25.6-25.9, THP-OFF
24.4-25.3, FIX-1 controls 27.3-27.4, characterisation 27.3-27.4) while the **pristine control reproduced**
(12.637 vs 12.366 standing, **+2.2%**). Champion 27.383 vs standing ~21.21 is **+29.1%**, and the
champion/pristine ratio reads **2.167×** today against **1.7151×** standing. A hot-vs-cold harness offset
(**+4.36%**) would move *both* arms; only the champion moved, so the harness does not explain it. **The
mechanism is UNEXPLAINED.** Two rules follow for this track:

- **A headline is admissible only from ≥N independent launches with a session-unit CI.** One tight session
  is not a headline whatever its internal spread, because the arm-unit floor is the wrong instrument for a
  quantity that varies at process-launch scope. N is sized from the between-session sd (**2.793%**), never
  the arm sd (0.501%).
- **Investigate the source of the between-launch variance on the champion** — page-cache / NUMA placement,
  THP state, HIP graph capture, allocator — before any final champion number is published. Until it is
  explained, a **"cannot tell"** verdict (CHAMP-2 THP) is as consistent with this instability as with a weak
  effect. Mirror task: `autokernel-rebuild-program.md` **R23-57**.

**Re-baselining rule (INF-70 review, 2026-09-07).** The cor is SHARED, so when any surface's promotion
advances it, every other surface's `compounded_bench_pct` is momentarily stated against a baseline its own
harness never measured. That number is INVALID until that surface re-measures tip-vs-new-cor on its own
harness: the bundle marks every non-promoting surface `stale_baseline` at PROMOTE and clears the flag only on
that measurement; a quote while flagged is refused. Carrying or rescaling it forward is the same laundering
class as pre-hook seeding. Per-surface cor was considered and rejected — it recreates two lineages inside one
branch; if the re-baseline arm ever proves too expensive, revisit that choice explicitly rather than skip the arm.

### 3.3 Track U3 — RUNTIME_CONFIG arm type
D3 gave us build-recipe arms (cmake defines). Most CPU wins are *runtime*: placement, NUMA mode, thread
topology, env knobs, launch flags. A RUNTIME_CONFIG hypothesis mutates a **codified recipe**, needs no
build, and is measured by the same paired A/B (two launches of one binary). A keep commits the recipe
change (recipes are code, in git) and the recipe hash becomes part of the epoch. Guard: a knob whose
`switch` covers more than its name (INF-70's `GGML_TINY_SOLO_CLAMP` fall-through gated 10 ops) is a
correctness-oracle failure, not a tolerance — the oracle must diff op coverage, not just outputs.

**SEED CASE — the first RUNTIME_CONFIG arm already exists, measured, from outside the loop (2026-09-08).**
CHAMP-2's THP shim (`GGML_NOHUGEPAGE_PROCESS=1`) *is* a RUNTIME_CONFIG arm by this section's own
definition: no build, one binary, two launch configurations, paired, session-unit. INF-70 ran it to a
verdict (6/6 ON-faster, α = 0.0430, direction only) before the arm type exists in the loop. Specify U3
against this instance rather than in the abstract — it arrives with a validated measurement design, a
knob whose scope is known, and a recipe that a keep would mutate. Two properties of it that the arm type
must therefore support, neither of which a SOURCE arm needs:
- **The unit is the SESSION and cannot be otherwise.** A launch-time knob cannot be switched between arms
  inside a live process, so a per-arm number for it is meaningless by construction (R23-55).
- **The effect was a compressed downside TAIL, not a shifted mean** (sd 2.510% OFF vs 0.481% ON, 25.3x).
  A comparator that only tests means can return "no effect" on a real one. U3's compare step must report
  spread alongside the point estimate, and the keep grammar must be able to accept "reduces variance".

**Cross-surface transfer — the programme's thesis, demonstrated (2026-09-08).** This is the FIRST result
either campaign has produced that pays on the *other* surface: a knob found on the CPU decode path is a
candidate fix for the GPU **serving floor** (4.581% p95 n=10), which is the binding constraint on every
GPU keep (R23-58). Everything before it was surface-local or a constraint. Record it as evidence for the
unified surface, against the standing cost of the same design (serialisation throughput, coordination
overhead) — this is the first entry on the other side of that ledger.

**Status precision (do not over-record):** the *verdict* is settled (LIKELY IMPROVEMENT, keep, session
unit, direction only, no fold). The *recipe change* is INF-70's recommendation to their operator and is
**not yet adopted**; the champion default remains OFF until it is.

> **CORRECTION OF RECORD, 2026-09-08 — THE TRANSFER WAS TESTED AND IT DID NOT TRANSFER.** The paragraph
> above was written while R23-58 was still a *candidate*. R23-58 has since **run to its registered stop
> rule and returned a BOUNDED NULL** on the GPU serving path (T0/D0; 48 launches / 24 couples; `p95_dev`
> ratio OFF/ON **0.713**, p = 0.3159; the ON arm slightly *wider*), with the mechanism proven to have fired
> (ON-arm AnonHugePages 0.0% on every launch, `THP_enabled` correct 48/48). Verdict and evidence:
> `autokernel-rebuild-program.md` → R23-58.
>
> **So the ledger entry changes sign, and the honest version is the more useful one.** What the unified
> surface demonstrated is **not** "a CPU finding fixed the GPU floor" — it is that the unified surface let
> a CPU finding be **cheaply and decisively falsified on the GPU surface in ~27 minutes**, which is itself
> the argument for the design. A cross-surface *candidate* is only worth the coordination cost if the
> transfer test is cheap; here it was, and it said no. Record the transfer as **TESTED, NEGATIVE, BOUNDED**
> — never as "demonstrated". The CPU adoption stands on its own CPU evidence and is now **ADOPTED there**
> (operator ruling); the GPU recipe does **not** take the knob.
>
> **Also now settled: the recipe is PER-SURFACE.** One champion, one commit, **two different launch
> recipes**. That is a second worked instance of R23-59 / U3 — `champion.py`/`Bundle` carrying a single
> recipe per champion is under-specified by construction.

- [ ] **U3-SEED — specify the RUNTIME_CONFIG arm type against the THP instance**: session-unit paired
      launches, spread reported with the point estimate, a variance-reduction keep grammar, and the recipe
      hash in the epoch. Blocked on nothing; do it before authoring any RUNTIME_CONFIG hypothesis.
- [x] **U3-DEFAULTS — RESOLVED 2026-09-08: NOT APPLICABLE. R23-58 did NOT confirm the shim on the GPU
      serving path, so it does NOT go into the loop's recipe defaults.** ✅ 2026-09-08. The conditional this
      task was written under evaluated **false**: bounded null, T0/D0, registered action "do not adopt".
      **Do not add `GGML_NOHUGEPAGE_PROCESS` to any loop-launched `llama-server` on the GPU surface** — the
      premise that the loop "pays the OFF variance today" is refuted for that surface (OFF p95_dev 6.657%
      vs ON 9.334%; the ON arm was wider). Closing this as *resolved-negative* rather than deleting it, so a
      later reader does not re-derive the same candidate and re-spend the 27 minutes.
> ### THE RECIPE FORMAT — NOT THE KERNELS — IS THE BINDING CONSTRAINT ON WHAT THIS CAMPAIGN CAN ASK
>
> **Three expressiveness gaps in the recipe schema were found and fixed on ONE DAY, 2026-09-08.** Each one
> surfaced only when somebody asked a slightly new question, and each one made a measurement **impossible**
> rather than merely slow:
>
> | # | research commit | what the recipe could not carry | how it surfaced |
> |---|---|---|---|
> | 1 | `b5f58b74` | **an env var** — so a RUNTIME_CONFIG arm (the THP shim) had nowhere to live, and serving compare reported only the mean | CHAMP-2 needed a launch-time knob and a *spread* comparison |
> | 2 | `4952e95e` | **its own identity hash** — so a floor was keyed by recipe NAME and a gate could be fed a floor calibrated under a different recipe | R23-58 needed floors that could not be silently swapped |
> | 3 | `c3e362a1` | **a self-drafting model** — `Recipe.server_argv` required `spec_decode["drafter"]` unconditionally, so an MTP model raised `KeyError` and **could not be expressed at all** | the Qwen3.6-35B-A3B sweep |
>
> Gap 3 is the sharpest statement of the pattern. MTP carries its draft head *inside the model weights*
> (`blk.N.nextn.*`), so there is no drafter file to name. Absence of `drafter` is now itself the declaration
> that the model self-drafts: `-md`/`-ngld` are omitted and `--spec-type` is still passed. Tests cover both
> shapes and spec=none, **and carry a control proving the negative assertion can fail** (suite 587 → 592).
>
> **The generalisation, and it is a U3 statement:** every one of these was found by *tripping over it*, at the
> moment a measurement was wanted. The schema is the interface between "a question we can ask" and "a question
> we cannot", and it has now failed that test three times in a day. **Do not wait for the fourth question to
> expose the fourth gap** — U3-EXPRESS below is a deliberate pass over the schema instead of a reactive one.
>
> Gap 3 also had an immediate consequence beyond its own sweep: it means the **dense Qwen3.8-27B is now
> expressible as an MTP recipe too** (it carries `blk.64.nextn.*` and `nextn_predict_layers = 1`), which is
> exactly the configuration frozen production supports for that model — the missing PROD-BASE-1 denominator.
> Tracked as **MTP-27B-1** in `autokernel-champion-aggregate.md`.

- [x] **U3-EXPRESS-3 — a self-drafting model is expressible as a recipe** ✅ 2026-09-08
      (research `c3e362a1`: `spec_decode.drafter` optional, `-md`/`-ngld` omitted when absent, `--spec-type`
      still passed; `test_selfdraft_recipe.py` covers both shapes, spec=none, and a fail-control; suite
      587 → 592). Third of the three gaps above; the first two landed the same day as `b5f58b74` and
      `4952e95e`.
- [ ] **U3-EXPRESS — run a DELIBERATE expressiveness pass over the recipe schema instead of waiting for the
      next question to expose the next gap.** Three gaps in one day (env var, identity hash, self-draft), each
      found by tripping over it mid-measurement, each blocking a measurement outright. Enumerate what a
      `Recipe` must be able to express for the surfaces this campaign already runs — multi-GPU / split modes,
      tensor-split and per-device `ngl`, LoRA and control vectors, RPC/distributed serving, per-arm env sets
      (not just one), draft models with their own recipe fields (`draft_p_min`, `draft_n_min`), grammar and
      sampler variants, `--no-kv-offload`/`--cache-type` combinations, and the *absence* semantics that gap 3
      showed can be load-bearing — then write a failing test per gap before fixing any of them. Belongs with
      **U3 (RUNTIME_CONFIG arm type)**: a RUNTIME_CONFIG arm mutates a codified recipe, so the arm type is
      bounded by exactly what the recipe can say. Blocked on nothing.

- [ ] **U3-DEFAULTS-b — carry a PER-SURFACE recipe on the champion record.** R23-58 makes the champion
      `ef81196d5` + *CPU* recipe (shim ON) + *GPU* recipe (shim NOT set). `champion.py`/`Bundle` can express
      one recipe per champion, which is now demonstrably under-specified. Extend the record to key the
      recipe by surface, and make the gate refuse a measurement whose (surface, recipe_hash) pair does not
      match. Ties to R23-59 and R23-55 (`unit`). Blocked on nothing.

### 3.4 Track U4 — resource broker and per-surface budgets

- **Admission control, not screening (measured 2026-09-08, both directions):** during the fold window the
  GPU and CPU surfaces each measured the other as a confound, **with both sides correctly pinned and
  INF-70 holding the CPU region lock correctly**.

  | direction | victim instrument | confound | quiet reference | contaminated | ratio |
  |---|---|---|---|---|---|
  | 1 (INF-70 MEAS-6) | their hot-harness A/A (`llama-bench`, one process at a time, tg128, 20 alternating pairs, host threads `taskset -c 184-191`) | my bundle-seed bench, straddled deliberately | pair p95 0.80% drain-era; quiet-host subset re-measured **0.509%, sd 0.279%** | **7.223%** (n=5, sd 3.268%); restated **2.151%** on their adjacent subset | **~4.2×** |
  | 2 | my pinned serving-floor recalibration (10:05-10:08Z) | their RETEST-1 `llama-server` pid 1167737, `-t 48`, 242 threads, 4800% CPU across 0-95, launched 09:53:47Z by `session2.sh RA_AA`, holding q0-q3 as `retest1-campaign3` correctly | unpinned quiet-host floor **3.536%** (n=8, cv 1.572%) | **10.255%** p95 (cv 5.977%; 155.02/168.48/152.81/144.17/143.22 tok/s) | **~2.9×** |

  Direction 1 put the detectable effect at n=8/side at **4.575%**, i.e. 1-3% CPU levers are unmeasurable
  under concurrency, and their pre-registered gate halted before any lever arm ran. Direction 2 cost a
  quarantined floor file and an aborted n=10 run.

  **The channel is DRAM bandwidth, not cores.** INF-70's contention screen (foreign %CPU,
  sibling-expanded) PASSED every contaminated arm: prefill flat (±2%) while decode fell 7%, NUMA
  placement and AnonHugePages constant. **No CPU-occupancy screen on either side can see it.**

  **Halt semantics are part of the broker, not a courtesy.** Both sides had a "halt" that did not stop
  queued successors: my loop's drain let a lane start a `jobs=64` build at 09:31Z (killed at the build
  stage); INF-70's `chain2.sh` (launched 09:41:41Z) ran a `-j 48` build 09:48:11-09:49:17Z on its own
  after campaign 1 halted, and their agent re-ran a campaign at 09:53:41Z, reading "STOP and report" as
  "diagnose and re-run". Structural, not carelessness.

  **Rules this fixes into U4:** (a) the broker **admits ONE surface at a time** — time-slicing, with a
  quiet-host A/A at each switch; (b) the broker owns process **LIFECYCLE**, not just locks: *nothing
  queued may fire across a halt*; (c) CPU-occupancy screens stay **necessary for diagnosis but
  insufficient for admission**. Cost of the alternative (INF-70, arms at 80% power): detecting +1.0%
  needs 2 arms/side quiet, 10 concurrent, 168 during an excursion — serialising is worth **5×-84×**;
  CHAMP-2's pooled +0.16% needs ~48 sessions/side ≈ **10 h exclusive**, not resolvable on this host
  under any realistic booking.

The loop becomes the single scheduler for: build slots (pinned, `jobs` bounded, **locked**), GPU arms (the
`mi210_0` flock, as today), CPU arms (the orchestrator `cpu_region_lock`, role `bench`), and the
foreign-load sampler (sibling-expanded, `/proc/<pid>/stat` deltas — reuse `foreign.py`, do not rebuild).
A CPU arm and a build never overlap; a GPU arm and a build may (GPU-bound, host threads pinned) only if
the sampled foreign load on the GPU host threads' siblings stays under a declared bound. Budgets: a CPU
arm costs ~10× a GPU arm (reload + eviction), so surface share is by *arm-seconds*, not iterations, and the
CPU surface gets fewer, larger windows. This is the structural resolution of OP-41 (option A, built in).
**LOO budget, stated so it cannot be quietly skipped:** per promotion, `n_keeps × n_surfaces` arms plus one
re-baseline arm per non-promoting surface — at 5 keeps and two surfaces, 5 GPU arms (minutes) plus 5 CPU
arms (~30 min of arm time before builds) plus re-baselines. The broker reserves that window when the fire
decision is made; the promotion record carries LOO and re-baseline receipts as REQUIRED fields and a
promotion without them is refused, not warned.
**Precondition for P4 (INF-70 review):** `foreign.py` lives in scratch (`/mnt/raid0/llm/tmp/inf70/agents/
sync19-20/`) under a retention note, and a retention note is not a home — promote it into
`epyc-inference-research` (beside the recipe module PROD-1 is producing) with a test BEFORE the broker depends
on it. Owner `ak-rebuild-20260828` unless INF-70 takes it.
**§3.3 oracle, sharpened by the review:** INF-70's fall-through knob passed 18/18 output identity precisely
BECAUSE outputs were bit-identical — an output-diffing oracle cannot see the class; op-coverage diffing is
necessary, not nice-to-have.

**Region lock blind spot (measured 2026-09-08):** `cpu_region_lock` models regions as logical-CPU
ranges; a build pinned to 96-183 is OUTSIDE 0-95 yet occupies the siblings of 0-87, so the lock would
grant a bench arm during the compile. The broker must reserve by PHYSICAL core (sibling-expanded, via
`foreign_load.bench_logical_cpus`) — a build slot on 96-183 and a bench arm on 0-95 are the same resource.

**Third-party disturbance is PRICED, and serialisation is not the binding constraint (INF-70, 2026-09-08).**
Across the RETEST-1 Q2 arms the disturbance hit rate was **1 in 6 ≈ a 17% tax in arms** — and it is the
expensive kind, *paid on work identified as garbage only after running it*. Serialisation between the two
sessions **held**: both sides honoured the region lock and it still did not protect the instrument, because
> *"Region-lock serialises those who call it; nothing constrains those who don't."*

That sentence is the whole case for **admission control over cooperative locking**: the broker must gate
**entry to the host**, not participation in a protocol. Foreign, unattributed load (a python process at
**800% CPU**, `Cpus_allowed` 0-191, plus `opencode`) cost one Q2 arm outright. Host-state change for the
record: at **12:05Z** the operator stopped the orchestrator API (uvicorn :8000 + 6 workers, pid **3961116**,
up since 2026-08-26) via `orchestrator_stack.py stop orchestrator`; hub :8100, OCR :9001, sd_server :8190 and
the docker containers remain — a **candidate, unproven** source of that 800% python.

- **Gate guards (2026-09-08):** a gate cannot PASS on zero cases or an unobserved graph; verify process
  death by `/proc/<pid>` existence, not `ps` exit codes.

- **OP-41 RULED (operator, 2026-09-08) — the operator owns this design, and it lands LAST.** The admission-control
  broker is **the operator's own design**, refined through this handoff (INF-73 §3.4); it will be **implemented by
  the operator**, and only **AFTER**, in order: **(1)** the champion is finalised, **(2)** the champion is promoted to
  production, **(3)** the host is rebooted. **No action now** — no broker code, no scheduler, no admission daemon,
  and no session may start building one. Until then the standing behaviour is unchanged: cooperative region-lock
  plus INF-70's bounded-hold requests, with the measured 4.2×/2.9× mutual degradation and the ~17% third-party arm
  tax accepted and labelled, not engineered around.
  - [ ] **U4-SEQ — hold admission control until the operator's three gates clear**, then hand this section's
        evidence (both degradation directions, the 1-in-6 disturbance tax, *"region-lock serialises those who call
        it; nothing constrains those who don't"*) to the operator as the design input. Gates: champion finalised →
        promoted to production → host reboot. Nothing in U4 is buildable before that, and this row exists to record
        the sequencing, not to authorise work.

- **OP-40 IS NOW PART OF OP-41 — ONE item, owned by `ak-rebuild-20260828` (transferred 2026-09-08).**
  INF-70 closed today and, on an **operator ruling**, transferred its **OP-40** (unfenced tooling inside the
  measured region) to this session, where it **folds into OP-41**. They are **one item from here on**, so
  co-tenancy is not tracked twice; INF-70's own record stays readable at
  [`cpu-decode-roofline-program.md`](cpu-decode-roofline-program.md) -> **MEAS-6**.
  - **Both directions, both sides correctly pinned, no rule broken by either.** Their CPU A/A degraded
    **0.80% -> 7.223%** under **our** pinned GPU bench chain; **our** serving floor degraded
    **3.536% -> 10.255%** under **their** lock-holding CPU session.
  - **Attribution caveat — this must never be dropped when either number is quoted, and must not be
    paraphrased away.** The split between *"the chain costs ~6.4 pp"* and *"the drain-era floor was
    optimistic"* is **NOT separable** from those two points; the **CONJUNCTION is what is established**,
    never either limb on its own. **Later evidence favours us**: their quiet floor came back at **0.509%**
    on the adjacent subset — *tighter* than the 0.80% reference — so **their baseline was conservative
    rather than self-flattering**.
  - **The ~17% third-party tax: serialisation is necessary and demonstrably NOT sufficient.** With both
    campaigns serialised on an **operator-mandated exclusive host**, an 8-core `python` plus `opencode`
    (`Cpus_allowed_list=0-191`, belonging to **neither** campaign) still cost an arm at a **1-in-6** rate.
    **Serialising the two campaigns against each other is necessary and demonstrably NOT sufficient.**
  - **The channel is DRAM bandwidth, not cores** — prefill flat within **+/-2%** while decode fell **7%**.
    **No CPU-occupancy screen on either side can see it.** That is precisely why the remedy is **admission
    control rather than a better screen**, and it is the **strongest argument for the U4 broker owning
    process LIFECYCLE on both surfaces**, not merely holding locks.
  - [x] **OP-40 transferred from INF-70 (operator ruling) and folded into OP-41; this session owns the
        single resulting item, and no duplicate row is carried** ✅ 2026-09-08

### 3.5 Track U5 — one monitoring session; authoring roles
One roster session monitors both surfaces (status, keeps, gates, errors — what `ak-rebuild-20260828`
does today). The CPU session's role becomes **diagnosis and hypothesis authoring into the inbox**
(sibling-expansion bug, fall-through knob: reading work the loop cannot do), and the loop measures.
Authoring of RUNTIME_CONFIG hypotheses by the loop's planner comes only after U3 exists (operator
sequencing: measurement first, authoring later).

## 4. Phases, exit criteria, tasks

### P0 — directive relayed, handoff filed ✅ 2026-09-07
- [x] Directive sent to `workspace-1c` with concrete instructions (rebase onto champion tip, opt-in the two
      blockers, record keeps in the bundle schema, LOO per promotion, fold at a loop boundary) ✅ 2026-09-07
- [x] This handoff + index row ✅ 2026-09-07

### P1 — the fold at run 30's next boundary (U1)  · exit: ONE champion tip carrying both lineages, GPU floors unchanged
- [x] **UD-0**: operator confirmed the fold DIRECTLY to `workspace-1c` ✅ 2026-09-07 — gate 1 (their windows clear) is theirs to signal; gate 2 (run 30 boundary) is ours
- [x] **FOLD-2 additions (UD-4)** ✅ 2026-09-08: on candidate `ef81196d5` — `test-backend-ops -o SSM_SCAN -b ROCm0` **7/7 OK**
      incl. the K=4 / K=3 rollback cases; `verify_ggml_linkage.sh` **PASS** before the serving gate; dispatch **observed**
      (`llama-bench -v` + `GGML_SCHED_DEBUG=2`: 27,516 nodes, SSM_SCAN=0, SSM_CONV 576 + GATED_DELTA_NET 576 all on ROCm0,
      CPU holds only 12 GET_ROWS); tg128 vs anchor-gen-021 **+0.052%** (20 pairs, floor 0.638%, not decisive, no drift).
      **UD-4 closed on observation.** Result file `/mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json`
- [x] Champion branch + orphan tag pushed to the GitHub fork ✅ 2026-09-08 (`ak-loop-tree` was swept from scratch mid-fold; `champ2` was one sweep from the same)
- [ ] INF-70 **RETEST-1 turn in progress** (A/A first, then RETEST-1 in priority order); **next fold = their keeps off `ef81196d5`** — they stage
      levers on a lane branch off that tip, prove merge-tree disjointness, and fold the same way
- [ ] FOLD-0 (`inf70-audit`): fold-ready commit with both blockers opt-in; bit-identity + `test-backend-ops -b CPU`.
      **FOLD-0 as written targets `6f032c48d`, two CPU champions old — re-base onto the CPU champion at the
      boundary (today `inf70/champion3` @ `9c4f73e29`, build 10241, `experimental-inf70-champion3` on the `fork`
      remote: +4.50% vs champion-1 on 117/120 per-prompt wins, 1.5149× vs pristine, bit-identical over 16
      arm-pairs, α 0.8209 unchanged) or the fold ships a superseded kernel and discards the +4.50%**
- [ ] Do not schedule the boundary under INF-70's live chains (SYNC-19/20 window 1 ~21:30Z + a second window,
      HARNESS-1 Phase B behind it) — rebasing under in-flight pre-registered arms invalidates them; clears in hours
- [x] FOLD-1..3 (champion owner) per `autokernel-champion-aggregate.md` ✅ 2026-09-08: fold executed, all FOLD-2 gates
      PASSED (G1 7/7, G2 1140/1140, G3 39/39, G4 dispatch observed, G5 +0.052% inside the 0.638% floor), then
      `ak/champion/llama-cpp-0db32c06e3e5` fast-forwarded `bff30cebe` → **`ef81196d5`** (`--ff-only`, tip == candidate) at
      11:16:49Z, lineage verified (`bff30cebe`, `445e93a8`, `9c4f73e29`, production `0db32c06e` all ancestors), worktree
      clean, pushed to fork `pestopoppa/llama.cpp`; pre-fold GPU tip tagged `ak/pre-fold-gpu-tip-20260908` (pushed).
      **Production branch untouched.** NO relaunch (operator directive stands)
- [x] **R23-51a in the same window** ✅ 2026-09-08: cor `445e93a8` seeded with a **MEASURED** tip-vs-cor tg128 bench,
      **+5.958%** (20 pairs, decisive, not drifting). The serving gate then ran on it: n=5 −5.19% (decisive, `diverged`),
      re-run n=10 **−2.18% NOT decisive** → disposition **UNCONFIRMED (not refuted)**; **cor HOLDS at `445e93a8`** and the six
      keeps stay on the tip as provisional and re-gateable. An **11-point proxy-vs-truth gap** the bench alone could never show
- [x] **R23-49 pin + re-calibration in the same window** ✅ 2026-09-08: `cpu_list` pinned `184-191` on the GPU serving recipe
      and the serving floor re-calibrated under the pin — **4.581% p95** (n=10, cv 3.136%, median 161.08 tok/s) on a
      verified-quiet host; the first attempt was CONTAMINATED (10.255%, INF-70's server live) and was quarantined. The pin
      costs ~1 pp of floor width vs the 3.536% unpinned quiet floor
- [ ] CPU keeps present in the fold recorded as `accumulator-bundle.cpu.<recipe>.json` (schema v1) — **with their
      magnitude flagged `provisional` and the contention label `pre-hook`**: every INF-70 arm before 2026-09-07
      carries a WRONG contention label (sampler read `184-191` as disjoint), and +4.50% is at or below its
      instrument's floor (sign solid, magnitude not). A bundle must never launder a non-claim into a settled number.
      **Further caveats (INF-70, 2026-09-07 ~20:20Z):** (i) SYNC-19/20 independently corroborates the ~5% floor — seven
      identical A arms, sd 1.79%, range 4.91%; (ii) **a harness-wide statistical defect**: 20 prompts inside one arm are ONE
      observation, and a sign test over pairings double-counts the shared treatment arm, so every INF-70 significance
      computed the old way is inflated — the corrected statistic is an arm-level permutation test; any magnitude the
      bundle ingests must carry which statistic produced it; (iii) linear within-block drift is ruled out (slope
      +0.03%/slot, R² 0.004), so CPU-surface scatter is contention (OP-40), not drift.
- [ ] NO relaunch by default (operator 2026-09-08). **Consolidation exit ACHIEVED for the GPU side ✅ 2026-09-08**: one tip
      carrying both lineages (**`ef81196d5`** = GPU tip + CPU champion3 `9c4f73e29`); **FOLD-2 passed**; the durable bundle
      **seeded MEASURED** (+5.958% tip-vs-cor) **and the serving gate run on it → UNCONFIRMED** (−2.18%, n=10, not decisive;
      cor holds `445e93a8`); **tip on the fork**. Consolidation is **complete for the GPU side pending INF-70's keeps**, which
      fold onto `ef81196d5` next. Phase-2 candidates below still to be gated or declined. Then ASK before any run 31.

### P1b — consolidation phase 2: rescued-ref candidates (each behind its own gate; measurement that serves consolidation is allowed)

Source of truth for the classification of all 31 `fork/rescued-*` refs:
[`docs/design/champion-consolidation-audit-20260908.md`](../../docs/design/champion-consolidation-audit-20260908.md).

- [ ] **Chunked GDN — `rescued-ak-g15-chunked-gdn-20260823` @ `719a8529d`** (upstream PR #24561 unified-MMA port;
      `ggml/src/ggml-cuda/gated_delta_net.cu` +527, `tests/test-backend-ops.cpp` +34). Surface: GPU PREFILL on GDN
      models (qwen35 / qwen35moe / qwen3next); the champion still carries `//TODO: Add chunked kernel for even faster
      pre-fill`. **Largest unrecovered GPU lever.** Gate: GPU prefill A/B on a GDN model **plus** `test-backend-ops`.
- [ ] **Quantize reciprocal — `rescued-ak-discovery-7e8da8ea-attempt1` @ `9f85ba2fb`** (`ggml/src/ggml-cuda/quantize.cu`
      +4/−1: reciprocal-multiply + `__shfl_sync` broadcast replacing per-lane `roundf(xi/d)`; the champion still does
      `roundf(xi / d)`). Gate: tg128, 20 pairs vs anchor.
- [ ] **Q5_0 `vecdotq.cuh` variants — `f9d74a2a3`, `d4b0a04e4`, `580e8d090`, `5d22a5463`: DECLINE.** Q5_0 is not a
      production quant and the work is re-derivable. Revisit only if a Q5_0 target appears on the fleet.
- [x] Single-copy refs pushed to the fork ✅ 2026-09-08 (`ak/orphan-keeps-quantize-20260829`,
      `ak/pre-anchor-fix-full-history` `b04fad244`, `ak/run14-01893a36-cumulative` `01893a36c`,
      `ak/admission/remove-funsafe-math-20260831` `3161d2dcf` — the last is already applied on the champion as
      `b861c32fa` (CH-7, 2026-08-31); pushed for durability only, nothing to fold)

**REFUTED — do not fold. A measured refutation is not a keep, and re-measuring a refuted lever is new research
(stopped by the operator).** Both read as candidates on the audit's first pass because absence from the champion is
exactly what a refuted lever looks like; corrected from the record by INF-70 2026-09-08:
- `rescued-inf10-gemv-fusion` `ea8ca0609` — measured and refuted 2026-08-27: gate+up **−2.11%**, QKV **+0.25%**, both
  **−0.57%** (verified window **−1.33%**) at tg128, region-locked q0-q3, canonical env, 5×4 rotated; correctness clean
  (PPL 5.5410 identical 4/4 arms). Closed `[x]` in `cpu-shape-specialized-gemv-decode.md`; evidence
  `epyc-inference-research/data/gemv-fusion-2026-08-25/` + `SHA256SUMS`. *"No further barrier-fusion work is justified
  on this target."*
- `rescued-cpu-opt-q8-8x8-avx512bw` `1f8868307` + `af6701d00` — the SIMD ukernel plan is an explicitly CLOSED appendix
  (8×8 GEMM body E3-gated, owned by `batched-decode-measurement.md`); the one measured angle `0467a5c17` (RMS_NORM
  intra-op parallel reduction) was **−8.8%** (4.41 → 4.02 t/s at 96t, Qwen3.6-27B Q8_0), kept env-gated
  `GGML_RMS_NORM_PARALLEL=1` default OFF as scaffolding. The 22% in `ggml_barrier` is barrier-COUNT-bound; the Q8 axis
  closed with *"the 4.4 t/s ceiling is genuinely architecture-bound."*

**MUST NOT FOLD `de447119f`** (`rescued-feature-tree-draft-v6`, "route Q8_0 `ne11<=1` MTP-verify to MMQ, +17.4%") — the
champion's `mmvq.cu` carries the LATER contradicting decision `akm-cdna2-q8-b4-mmvq-route` (Q8_0 `ne11<=4` through
MMVQ, `ne11>=5` on MMQ — "the July crossover"), reversal documented in-source. Folding it would REGRESS the champion.
Its other GPU commits (nwarps=4, async prefetch, GDN bf16 +21.5%, `GGML_CUDA_GDN_STATE_BF16` in 9 files) are already in.

### P2 — surface dimension (U2)  · exit: two bundle files, two floors, a CPU serving A/B record on disk
- [ ] `Bundle.surface`; per-surface store filenames; `load_bundle()` per surface; shared cor invariant test
- [ ] `serving.Recipe` CPU variant (device, cpu_list, numa, threads) — the CPU session's canonical recipe codified
- [ ] CPU A/A calibration: screen floor + serving floor, unit and host-state hash recorded; gating-floor calibration n≥24 with interval (FLOOR-UNIT-1 supersedes the earlier n=20 proposal)
- [ ] **Every floor record carries `unit` (arm | session | process)** alongside harness, n, contention model
      and host-state hash; a gate comparing an effect to a floor of a different unit REFUSES (INF-70 RETEST-1,
      2026-09-08: arm sd 0.501% vs process-launch sd 2.793%; the 1200-fold THP sizing error). See R23-55.
- [ ] **Headline admissibility: ≥N independent launches with a session-unit CI**, N sized from the
      between-session sd (2.793%), not the arm sd; a single-session headline is refused (R23-57)
- [ ] **Investigate the source of between-launch variance on the champion** (page-cache/NUMA placement, THP
      state, HIP graph capture, allocator) — ~12% spread on an identical config, pristine control stable (R23-57)
- [ ] Per-surface fire decision; dashboard accumulator card per surface (product-of-solos labelled ESTIMATE)
- [ ] **Re-baseline on cor advance**: `stale_baseline` set on every non-promoting surface at PROMOTE, cleared only by
      a tip-vs-new-cor measurement on that surface's own harness; test that a quote while flagged is refused
- [ ] First CPU serving gate produces an `epyc.autokernel.serving_ab.v1` record

### P3 — RUNTIME_CONFIG arm (U3)  · exit: a config keep committed to a codified recipe and re-measurable from a fresh checkout
- [ ] Hypothesis kind enum; author path that edits a recipe file, no build
- [ ] A/B of one binary under two recipes; recipe hash in the epoch
- [ ] Oracle extension: op-coverage diff for env-gated knobs (fall-through class)
- [ ] Known-good and known-null config patches classify correctly

### P4 — broker + budgets (U4)  · exit: 10 consecutive iterations mixing surfaces with zero unlocked builds and foreign load under bound on every arm
- [ ] Build slot: pinned + `jobs` bounded + region lock role `build`; per-lane concurrency cap
- [ ] CPU arm: acquire `cpu_region_lock` role `bench`; GPU arm: existing flock
- [x] **P4-0 precondition** ✅ 2026-09-07 (INF-70 took it): `scripts/utils/foreign_load.py` + `test_foreign_load.py` on
      research `main` `de51899c` (branch `inf70/foreign-load-sampler` `e441de78`, merged by `ak-rebuild-20260828`: merge-tree 0
      conflicts, 7 tests green). Importable `sample_once()` / `bench_logical_cpus()`; `--out`/`--bench-cpus`; fails CLOSED on
      unreadable sysfs; foreignness by `cpus_allowed` intersection (permissive by design, `on_bench_core` per row for the strict
      reading); the sibling test is mutation-isolated. Scratch copy stays until SYNC-19/20 + HARNESS-1 finish in-flight arms.
- [ ] **P4-0a (filed 2026-09-07, derived from the P4-0 merge)** — the shared, un-lane-owned research clone
      `/mnt/raid0/llm/epyc-inference-research` is **187 commits behind `origin/main` with 9 dirty tracked
      files** left by other sessions (a merge there failed on `ort`). Surfaced merging P4-0 in; no owner,
      so nobody syncs it. Do NOT `checkout`/`reset` it (destroys other sessions' uncommitted work) — needs
      an operator-assigned owner or a scheduled sweep session before it grows further.
- [ ] Foreign-load sampler wired into residency (reuse `foreign.py`; sibling-expanded; live deltas)
- [x] LOO + re-baseline receipts are REQUIRED fields before shared-source advancement; the
      serial controller refuses to treat required-target validation as complete until every
      enrolled production surface and every keep-author surface has an exact current-tip row,
      then schedules one real `source_loo.execute_surface` treatment per retained keep plus the
      required re-baseline under the original held CPU/GPU claims. Continuations bind the target,
      assembled commit, candidate execution digest, instrument, request digest, pair count and
      immutable result hashes. Missing or inconclusive rows remain pending; an inconclusive LOO
      becomes retry-eligible only after one ordinary search opportunity, while failed rows remain
      failed. No LOO result grants deletion or promotion authority. ✅ 2026-09-10 — research
      `ee0ee378`; combined existing CPU/GPU/serving/screen/serial/LOO suite 109 passed in 33.22s.
- [ ] Budgets by arm-seconds; utilisation (held vs idle-while-claimed) on every row
- [ ] Retire the bilateral hold protocol with INF-70 (OP-41) — the broker replaces it

### P5 — single monitoring session (U5)  · exit: one roster entry monitors both surfaces; CPU session files hypotheses, measures nothing by hand
- [ ] Roster/ownership update; inbox is the CPU session's output surface
- [ ] Wiki: "measure the stack" + "one owner schedules" compiled from this program's results

## 5. Operator decisions (package, non-blocking)

| ID | Decision | Recommendation |
|---|---|---|
| **UD-4 — SSM_SCAN `K` port rides with the fold: measure, don't split (2026-09-08)** | INF-70 found the CPU lineage changes `ggml_backend_cuda_device_supports_op` for `GGML_OP_SSM_SCAN` (`K > 1` → decline on CUDA → CPU fallback), an UPSTREAM port (`4595b1bca` = ggml `1692f9e50`, recurrent-state rollback), with all 5 CPU levers committed ON TOP of it (27 commits after). Splitting = cherry-picking 27 commits = exactly what the runbook forbids and how keeps get dropped. Their operator: *"make sure the gpu-focused autokernel session is aware… reserve a quiet GPU window to verify impact on GPU performance… just make sure we don't lose any performance keeps."* | **Recommendation: take the whole `champion3` as ONE candidate; in the window run test-backend-ops SSM_SCAN with an explicit `K > 1` case, `verify_ggml_linkage.sh`, and OBSERVE the 27B's SSM_SCAN dispatch on ROCm0 (it is a hybrid; SSM_SCAN runs every token); hold K out only on measured evidence.** |
| **UD-0 — RESOLVED ✅ 2026-09-07 (~20:20Z)**: operator ruled DIRECTLY to `workspace-1c`: *"yes, fold onto the champion once the measurement windows clear."* Two gates remain, neither side controls both: (1) INF-70's windows clear (SYNC-19/20 w1 MTP block → w2 `AP` controls + 3 F1 arms → HARNESS-1 Phase B + hot session) — **they message us; do not schedule on an estimate**; (2) run 30's next boundary — ours. | The CPU session (`workspace-1c`) holds a DIRECT operator instruction from earlier this session — *"we're not folding into autokernel champion just yet. make sure we don't forget the canonical recipe."* — and correctly refuses to rebase on a relayed directive. **The operator must confirm the fold directly to that session**; a peer relay cannot override a direct instruction, and should not. | confirm directly; until then P1 proceeds only on the loop-side items (R23-51a seed, R23-49 recal) |
| **OP-41 — RULED ✅ 2026-09-08** | serialize / schedule / regress on CPU co-tenancy | **Operator owns the admission-control design**, refined through this handoff (§3.4), and implements it himself **after** champion finalised → promotion to production → host reboot. **No action now**; until then accept INF-70's bounded-hold requests and label contended arms. |

**OP-41 headline evidence (2026-09-08):** two campaigns, both pinned, lock respected → **4.2× / 2.9×**
mutual degradation via DRAM bandwidth; see §3.4. (Master-index row update owed to its owning session.)

**OP-41 second evidence bullet (2026-09-08, RETEST-1 close-out):** cooperative serialisation **worked and was
still insufficient** — third-party disturbance ran at a **1-in-6 hit rate ≈ 17% tax in arms**, paid only after
the arm was run. *"Region-lock serialises those who call it; nothing constrains those who don't."* This is
evidence for the **admission-control broker** (option A) over any further tightening of the lock protocol;
see §3.4.

| ID | Decision | Recommendation |
|---|---|---|
| UD-1 | CPU serving recipe = the gate for the CPU surface | the CPU session's canonical served recipe (Qwen3.8-Flash-Next), codified as `Recipe`; not a bench proxy |
| UD-2 | promotion granularity | one production candidate carries BOTH surfaces; a surface without a demonstrated gate does not block the other's keeps landing on the champion, but does block promotion |
| UD-3 | who authors CPU hypotheses after U3 | loop planner for RUNTIME_CONFIG/SOURCE on the CPU surface; CPU session keeps diagnosis; revisit after 10 CPU iterations |

## 5b. INF-70's unowned residue — PARKED, explicitly NOT adopted (2026-09-08)

**Why this list lives here and not in the rebuild program.** The rebuild program
(`autokernel-rebuild-program.md`) carries only work **this campaign will execute** — its R23 rows are the
loop's own queue. This handoff is where the **cross-campaign relationship with INF-70** is recorded (§3.4,
OP-41, the OP-40 fold above), so the inventory of what INF-70 left behind belongs beside it. Putting it in
the rebuild program would put unowned items inside an execution queue, which is exactly how silence gets
read as ownership.

**Status of everything below: recorded for DISCOVERABILITY, and NOT OWNED.** This session is **parking**
these, not adopting them. There is **no owner**. Nothing here is scheduled, and no row in any index claims
it. If someone needs one of these done, it needs an owner first.

| item | what it is | pointer |
|---|---|---|
| **PROD-1** | canonical recipe as **importable constants** (not prose). It must now also carry the **THP knob with its unit** and its **distinctness from `GGML_NOHUGEPAGE`** — the two are not the same knob and a recipe that conflates them is wrong. Draft promoted to git | `data/inf70-prod1-recipe-draft-2026-09-08/` (`epyc-inference-research`, commit `1780fa7b`) |
| **MEAS-2** | adopt `build_locked.sh` as the standing build idiom and promote it out of scratch — **19 of 21 build scripts are still unlocked** | `cpu-decode-roofline-program.md` -> MEAS-2 |
| **MEAS-3** | retention row: the `sync16` scratch directory is a **cross-campaign dependency**, not spent scratch | `cpu-decode-roofline-program.md` -> MEAS-3 |
| **MEAS-4** | the instrument **reserves 96 cores to run 48 threads**, and blocks a second agent while doing it | `cpu-decode-roofline-program.md` -> MEAS-4 |
| **MEAS-5** | the **MTP (serving) block is ~2.8x more precise** than the plain block, i.e. **~8x fewer arms** for the same precision — an unclaimed instrument upgrade | `cpu-decode-roofline-program.md` -> MEAS-5 |
| **SYNC-21** | prove or kill the profiler-overhead hypothesis for SYNC-16's null; also tests whether the per-node census systematically overprices cheap single-threaded nodes | `cpu-decode-roofline-program.md` -> SYNC-21 |
| **METH-2** | the back-to-back A/A registration rule **and its own correction** (bracketing is worse than pooling when there is no trend) — a methodology rule with no home outside INF-70's file | `cpu-decode-roofline-program.md` -> METH-2 |
| **NOFOLD-1** | `feature/tree-draft-v6` **MUST NOT FOLD**; the constraint existed nowhere in `handoffs/active/` until INF-70 recorded it | `cpu-decode-roofline-program.md` -> NOFOLD-1 |
| **HYG-2b** | the commit-hygiene hook **still misparses compound shell commands** (and blocks its own idiom) | `cpu-decode-roofline-program.md` -> HYG-2b |
| **G2-CONC** | blocking promotion gate — **must run on the PROMOTION CANDIDATE binary, never inherited from an ancestor** | `cpu-decode-roofline-program.md` -> G2-CONC |
| **UP-1 / UP-2** | **four upstream ggml contributions**, patches **ready and UNSUBMITTED**. Promoted to git so they survive a scratch sweep; submission has no owner | `data/inf70-upstream-patches-2026-09-08/` (`epyc-inference-research`, commit `1780fa7b`) |

Two items from INF-70 were **transferred and ARE owned here** and are deliberately absent from the table
above: **OP-40** (folded into OP-41, §3.4) and the **champion divergence** (filed as **R23-62** in
`autokernel-rebuild-program.md`).

## 6. Risks
- **Cross-surface interaction**: shared ggml graph/scheduler code means a CPU keep can move a GPU number. LOO across all surfaces on PROMOTE is the control; until P2, re-measure the GPU headline after every fold.
- **CPU arm cost** starves the loop if budgeted by iteration count — budget by arm-seconds (P4).
- **Two default-ON blockers** silently change GPU defaults if folded un-neutralised — FOLD-0 is a hard precondition.
- **Recipe drift**: RUNTIME_CONFIG keeps must land in codified recipes in git, never in a session's shell history (lesson: `gguf_swap_ple.py` lived in scratch; the pruner lived in scratch).

## 7. Dependencies
FOLD-0..3 (`autokernel-champion-aggregate.md`) · R23-48 LOO, R23-49 pin/recal, R23-50a/b recovery,
R23-51/51a durable bundle + seed (`autokernel-rebuild-program.md`) · OP-41 · INF-70 MEAS-1 / HARNESS-1 /
CHAMP-2 (`cpu-decode-roofline-program.md`) · `cpu_region_lock.py` · `sync19-20/foreign.py` ·
`docs/reference/kernel-freeze-runbook.md`.

## Key files
`scripts/kernel_rnd/autokernel/loop/{accumulate,run,serving,bench,anchor,pipeline}.py` ·
`controller/anchor_integrity.py` · `/mnt/raid0/llm/tmp/champ2` (champion tree) ·
`/mnt/raid0/llm/autokernel/loop-memory/` (store) · `docs/design/inf70-cpu-fold-into-champion-20260907.md`.

<a id="autonomy-design-20260908"></a>

## 8. Autonomy design notebook — 2026-09-08, evolving and documentation-only

### 8.1 Purpose, authority, and accepted decisions

**Session purpose:** collect and refine the plan in this handoff across multiple operator iterations,
including implementation details. Do not implement, deploy, launch experiments, modify production,
or alter running campaigns as a consequence of this section. The operator explicitly clarified:
"by details, I also mean IMPLEMENTATION details" and "We won't actually be implementing the plan
in this session." Retaining concrete designs does not make those designs approved.

The eventual outcome is one standalone AutoKernel service: the operator supplies its resource envelope
and targets, then follows the dashboard. CPU/GPU research, compilation, measurement scheduling, routine
recovery and evidence handling should no longer require two manually coordinated agent sessions.

**Vocabulary:** accepted = explicitly selected/agreed by the operator; observed = dated finding with
source; proposed = engineering design for later discussion; provisional default = suggested number or
policy, not ratified and not a measured performance result. Existing operational policy remains
authoritative until deliberately changed in a later session.

**Binding close-out updates:** `MEASUREMENT.md` INSTRUMENT-CLASS-1, FLOOR-UNIT-1 and BOUNDED-NULL-1
were operator-ratified after the first notebook draft; they are requirements, not provisional defaults.
OP-41 (§3.4) reserves admission-broker implementation to the operator **after champion finalisation →
production promotion → host reboot**. R23-64/65 wait for the operator's BIOS/reboot boundary. The architecture
below is a dependency design, not permission to move those gates earlier. No implementation is authorized
by this audit. Current evidence and corrections are consolidated in §8.16.

| Topic | Accepted direction / preference |
|---|---|
| Compute | Declare CPU, GPU, or both; explore production workloads applicable to those interfaces. |
| Prospective models | Seed a model outside the lineup; preserve production/candidate distinction. |
| Scheduling | **Adaptive, seed prioritized**: initial exploration window, then adaptation with continuing production coverage. |
| CPU experiment size | Smallest informative allocation for the mechanism; no full-host reservation by default for discovery. |
| Transfer | Mechanism-specific applicability; a small-allocation result is not automatically a full-serving gain. |
| Beliefs | Deeper integration for memory, applicability, transfer, invalidation and experiment selection. |
| Friction | Automatic capture, cached routes, asynchronous projection; no extra routine approval/review layers. |
| Runtime fast path | **Deterministic checks** for prevalidated recipe options, without the two critic rounds. New options and code retain review. |
| Dashboard | **Minimal controls**: pause/drain/resume and model/hypothesis seeding; advanced configuration stays in CLI/manifest. |
| This session | Documentation and iterative design only; no implementation authorization. |

Documentation checklist (only these boxes describe this session's work):

- [x] **PLAN-DOC-1** — capture audit, accepted choices, implementation proposals, tests and provisional defaults in the owning handoff. ✅ 2026-09-08
- [x] **PLAN-DOC-2** — iterate §8 with the operator before converting proposals into an implementation queue. ✅ 2026-09-08: operator authorized implementation; §9 records execution and retained boundaries. No production or live-research authorization inferred.
- [x] **PLAN-DOC-3** — audit both final September 8 close-outs and refine the notebook with evidence-scoped implementation contracts and tests (§8.16). ✅ 2026-09-08
- [x] **PLAN-DOC-4** — fresh independent audit; reconcile protocol/cadence contradictions and delineate scheduler, evidence, validation and lifecycle implementation contracts (§8.17). ✅ 2026-09-08

### 8.2 Dated audit findings and corrections

The audit covered August 25–September 8 reports and inspected the newer research lane
`/mnt/raid0/llm/worktrees/mains/ak-rebuild-research` (`bdfab023`) and research `origin/main` (`624adbdd`)
during that pass. The shared research checkout was behind those refs. Code-present, merged and loaded
in a process are separate statements. Resolve symbols at the recorded revision and current code before
implementation. This planning session ran no new benchmarks and re-certifies no historical percentages.

| Finding | Evidence / correction | Design consequence |
|---|---|---|
| Builds contaminated CPU arms | [Sept 7 co-tenancy audit](../../progress/2026-09/2026-09-07-ak-rebuild-20260828.md): build `96–183` shares cores with bench `0–95`; some manual builds were also unpinned/unlocked. | Broker all build paths; do not attribute all contamination to one session. |
| Seven workers did not mean seven concurrent builds | `loop/pipeline.py::SerializedTail.session` serializes build → oracle → A/B → commit; `run.py::gate_for` documents its `jobs=64`. | Preserve ancestry protection; process-local serialization does not protect external CPU experiments. |
| Threads are not physical allocation | [CPU roofline handoff](cpu-decode-roofline-program.md), C5/B2/MEAS-4: `-t 48` in a 96-core reservation, OMP spread, interleaved memory. | Fewer threads spread over the host do not prove a NUMA-local quarter equivalent. |
| Disjoint cores still share bandwidth/fabric | CPU roofline C0 concurrent node-local streams; this handoff §3.4 later DRAM contention. | Core locks alone cannot certify measurement coexistence; compare against quiet controls. |
| Wrong screening workloads | [Sept 1 transfer study](../../progress/2026-09/2026-09-01-ak-rebuild-20260828.md), [Sept 3 retargeting](../../progress/2026-09/2026-09-03-ak-rebuild-20260828.md): quantization, dimensions and speculative verify changed dispatched kernels. | Preserve shapes/dispatch; same quant label or a smaller model is insufficient transfer evidence. |
| NUMA/stale builds/dead controls masqueraded as kernel behavior | [Sept 2 audit](../../progress/2026-09/2026-09-02-inf70-audit.md), [Sept 5 audit](../../progress/2026-09/2026-09-05-inf70-audit.md). | Bind actual build/library, placement and effective path, not just source or requested env. |
| Transfer depends on mechanism and composition | CPU roofline SYNC-17 and final plain→MTP correction: tiny parallel work may lose to serial; universal transfer divisor retracted; later keeps change prior benefits. | No timeless class multiplier; small-only nulls cannot retire scale-sensitive ideas. |
| Persistence fix retained unsafe recovery in inspected code | `loop/accumulate.py::save/load_bundle`: direct write; missing/corrupt/lineage-invalid state sets cor=anchor; advanced tip retains old gain. | Replayable state; no implicit confirmation; invalidate affected values. Reinspect before fixing. |
| Serving metric/statistics differed from labels | `loop/serving.py`: sums per-request rates; always A then B; calibration uses individual-run deviations. | Separate metric identities, counterbalance, calibrate the actual estimator; incompatible floors cannot transfer. |
| Source fixes were not deployed-contract proof | [Sept 8 report](../../progress/2026-09/2026-09-08-ak-rebuild-20260828.md); ~09:47 UTC snapshot: running, age 879 s, budget 1800 s, no step/actor_health, health ok. | Snapshot does not prove a stalled process; new producer contract was not exposed then. Show loaded version and independent health axes. |
| New heartbeat had lifecycle/progress gaps | Inspected `run.py`: heartbeat always writes running, stop event not set/joined, claim/profile failures outside failed handler. Hub `panels.py` shares silence/progress budget; `loop_status.py` watermark omits stage. | Single status writer, terminal ordering, separate heartbeat/stage/science clocks. |
| Belief wiring largely covered older producers | Current loop reads local archive; legacy execution has capture. `ClaimTuple.to_frames` omits value/unit/extra; `UsePolicy` lacks workload matching. | Current-loop prospective capture + typed applicability; grade alone cannot establish transfer. |
| Resource plumbing requires reconciliation | `instance_topology.py::parse_cpu_list` drops IDs >95; cross-role global locks already exist. Ratified daemon authority differs from inspected inference-only/disabled-GPU config. | Fix normalization and existing provider path; no self-grants or second build-lock authority. |
| Serving contention allowance is not experimental equivalence | Existing contention provider allows bounded serving degradation. | Separate research coexistence use; do not turn serving allow into measurement-isolation proof. |

**Later consolidation supersedes early state:** P1 records fold `ef81196d5`, a real serving gate,
pin/recalibration and **UNCONFIRMED** bundle with cor held at `445e93a8`. Thus "gate never fired",
"pin not activated", "fold pending" and "run 30 live" are historical. Do not undo that work or seed
a new lineage. Remaining source findings require current-code reinspection, not an assumption that
another session has not fixed them. Root handoff snapshot at capture: `e5d1846d`.

### 8.3 Proposed architecture and loop

One service owns campaign state; coordination policy owns grants; broker suballocates within them using
existing physical providers. Actors own hypotheses/changes; adapters own execution/validity; journal owns
durable transitions; Vidya owns evidence/relationships; dashboard projects state and submits typed commands.

```text
START
  resolve manifest + registry snapshot + candidate seeds
  recover journal, desired state, candidate and validated evidence
  request authority and physical claims through existing policy
WHILE active
  apply controls at boundaries
  scheduler chooses target using coverage, cost, seed priority and scoped evidence
  if prevalidated runtime combination:
    deterministic recipe/compatibility checks; no critic calls
  else:
    planner reads current profile + scoped history + cached beliefs + inbox
    forms hypothesis and mechanism annotation
    existing critic pass 1: objection -> exact reason to planner
    author source/build/novel-recipe change
    existing critic pass 2: objection -> exact reason to author
  choose cheapest informative route; unknown transfer permits scoped exploration
  resolve phase/protocol/category/use and freeze its ExperimentPlan
  broker admits build if needed, correctness, load/place/warm/profile, comparison
  compile/correctness failure -> tool reason to author, separate bounded retry budget
  classify interference under phase/protocol -> retain noise or invalidate/checkpoint as authorized
    ordinary foreign load is recorded noise, not a search-admission veto (P-AK-SEARCH-1-A2)
  unavailable actor/resource -> other eligible work, or release claims and wait visibly
  stale parent -> superseded, preserve idea, rebase/retest; not refutation
  discovery completed -> advisory nomination only; schedule separate strict confirmation if selected
  completed valid comparison -> typed scoped conclusion for planner
    inconclusive / direction_only / estimated_effect / bounded_null / regression
    purported null missing power record or fired-mechanism control -> untested, no negative warrant
    valid measured contrast with inadequate resolution -> inconclusive; preserve data/uncertainty
  strict-confirmed eligible experimental keep -> integration lock, parent check, intent, commit, completion
  due validation batch -> assembled candidate + serving + required LOO; evidence matrix
  advance validated record only after applicable production-serving rows pass at exact identities
    bench/non-production BASELINE rows remain research/addenda, not production vetoes
BACKGROUND
  native journal -> local memory/status -> async Vidya/index projection
  supervisor -> bounded recovery; broker-aware storage maintenance
```

Retain existing independent hypothesis/patch review budgets. No additional reviewer or per-attempt
protocol-writing step. Runtime fast-path approval is the accepted exception. Tool failures return to
the author without another critic ceremony. Retiring an attempt does not retire its idea. Build and
measurement are expensive brokered stages; correctness/validation follow where they need produced output.
Brokered probes replace uncontrolled actor host compute, without requiring an operator for each probe.

### 8.4 Proposed campaign and target interfaces

Proposed supported commands, not installed by this update:

```text
autokernel start --manifest campaign.yaml
autokernel status --campaign ID [--json]
autokernel pause --campaign ID
autokernel drain --campaign ID
autokernel resume --campaign ID
autokernel seed --campaign ID --file seed.yaml
```

Manifest declares campaign/consumer, requested CPU regions/affinity and GPUs, build job/memory/disk
limits, duration/budget or continuous mode, production selectors and seeds, configured actors/explicit
fallbacks, recipes/objectives/acceptance-policy refs, scheduling/validation and control-access settings.
Resolve an immutable launch snapshot of registry/model/recipe/topology/policy/instrument/controller
identities. Dry-run before admission; no silent active-campaign change when registry or checkout moves.
Report requested, granted, physically held and actively used resources separately.

Target records bind model/hash, architecture/tensor census, backend/kernel tree, context/concurrency,
speculation/drafter, environment, metric/direction, correctness and regression requirements, route and
calibration refs. Key recipes by target/surface/operating mode, not one global recipe or backend alone.
Deduplicate roles only on complete workload-signature equality. A seed creates its own
candidate target without changing production or inheriting another calibration. If production cannot
load it, use the first compatible experimental build as exploration baseline, never a fabricated
production delta. Missing artifact blocks only that target; others continue.

**Proposed v1 scope:** llama.cpp CPU/GPU first, retaining per-kernel-tree identity for future speech;
local artifacts and registered references first. Remote downloads, requantization and lineup edits
are outside this proposed v1, subject to operator iteration. Do not silently dismiss a source/model as
inapplicable. Candidate rows are advisory unless explicitly included in the required validation set.

### 8.5 Proposed durable event model and migration compatibility

Reuse `scripts/kernel_rnd/autokernel/journal.py`: fsynced append, validation, torn-tail recovery and
durable cursors. Extend narrow current-loop kinds; do not restore the old deployment factory or create
another WAL/outbox. Current-loop records must not manufacture legacy `evaluation_event.v5` receipts.

| Record group | Automatically captured fields |
|---|---|
| Identity | campaign/hypothesis/attempt/execution, actual measured source/build/object digests, intended delivery candidate, compiled defaults and effective runtime state, recipe-map entry, target/model, instrument/protocol. |
| Scope | backend/architecture, quant/dispatch/op shapes, serving recipe, threads, physical cores/siblings/NUMA, placement, grant, neighbor envelope. |
| Measurement | instrument_class (bench/serving), category (OPTIMUM/BASELINE/CANDIDATE), phase/protocol_ref and record_class, metric/direction/physical unit/value, comparison_kind and changed factors, raw artifacts/hashes, estimator version, order/block and stopping plan, independent experimental unit/IDs, attempted/completed/valid/scored counts, window timestamps. |
| Validity | correctness/effective path, loaded-library/residency, contamination/drift/refusal; invalid timing never becomes a null. |
| Annotation | planner mechanism class and uncertainty, explicitly not measured fact. |
| Conclusion | estimand (level/dispersion/etc.), conclusion type, permitted claim strength, interval/power and effect-size bounds, both-direction fired-mechanism control refs; lack of significance alone is not a bounded null. |
| Relationships | reduced->target transfer, quiet->overlap, individual->assembled benefit, supersession/retraction, original evidence IDs. |

Mint attempt ID before execution; retries have separate execution IDs. Related arms retain their
shared support/independence grouping. Keep large data in references, not copied into each projection.
Capture facts from launchers/instruments rather than asking an actor to author evidence paperwork.

Journal is authoritative; SQLite history, Bundle JSON, Markdown memory, status and belief index are
projections. Integration: record `keep_intent` (attempt/parent/tree) -> integration lock/current-parent
check -> commit with attempt trailer -> `keep_committed` -> projections. Replay reconciles exactly once.
An unexpected tree advance preserves code but clears affected measurements; it cannot silently confirm.

Derived files use temp/write/fsync/rename/directory fsync. Missing/corrupt Bundle replays journal;
insufficient evidence means last provable validated head or `validation_required`, never cor=anchor.
Local journal failure stops new irreversible transitions and drains; downstream Vidya/dashboard failure
does not. Preserve legacy records as history; do not infer missing write-side provenance on read.

### 8.6 Proposed broker and resource foundation

**Sequencing constraint:** the operator owns admission-control implementation and its post-promotion,
post-reboot gate (§3.4). These interfaces are retained as design input only. Until that gate clears,
existing cooperative locks and bounded-hold coordination remain; this plan creates no scheduler/daemon.

```text
acquire(StageRequest) -> AllocationReceipt
launch(AllocationReceipt, ExecutableRequest) -> OwnedProcess
release(AllocationReceipt, outcome)
drain(reason) / resume() / recover()
```

Requests bind stage, CPU affinity/GPU set, memory/build limits, workload signature, bounded duration and
coexistence profile. Reuse lease/provider open/close fields. Reconcile inspected config with ratified
D4 and verify the actual grant/activate/renew/release path; never impersonate inference or self-grant.

Normalize CPUs using discovered sibling topology, not dropping 96+ or assuming historical NUMA labels.
Proposed v1 keeps four existing region claims: a microtest can use fewer cores while reserving its
containing region. No second fine-grained lock authority. Reuse cross-role global exclusion; build is
attribution, not a private nonconflicting namespace.

Broker ALL compute: candidate/anchor/validation/recovery builds, correctness/profiling, load/place/warm,
calibration/bench/serving/ablation. Enforce limits on descendants and bound/account actor local work.
Multi-resource acquisition uses deterministic order and releases partial claims on failure. External
grants cover useful batches, not a bus transaction per hypothesis/compiler. Internal admission uses one
broker lock. Preserve current tail serialization until immutable-base stages and integration locking
can reject/rebase/retest superseded candidates safely.

Check control/grant validity at every expensive stage, including queued work. No new bounded stage
past expiry without acknowledged renewal. Follow existing grant drain semantics, invalidate incomplete
evidence and manage only owned PID-start/process-group/cgroup identities. Never name-pattern kill or
delete locks. Release claims during no-runnable-work outages and reacquire through policy on recovery.

### 8.7 Proposed partition routes and coexistence profiles

Correctness transfer, reduction of local work, and end-to-end speedup transfer are separate claims.
Fewer threads across the host are not a smaller physical allocation: cache/CCD distribution, memory
placement, per-thread shape, clock and dispatch can change. More production threads are not inherently
better; final validation targets the best intended serving recipe, not all cores by definition.
The final MEAS-4 correction establishes that t48 was a measured optimum in earlier recipes, spread over
all 12 CCDs/four NUMA nodes—not an arbitrary half-instance or a contiguous unused half. That optimum need
not survive changed dispatch costs or BIOS settings. R23-64 owns the gated re-sweep; topology-shaped
partition discovery remains a separate experiment from simply lowering `-t`.

| Family | Proposed cheapest informative route | Transfer limitation |
|---|---|---|
| Local SIMD/arithmetic/redundant work/dispatch | Op test in one quarter preserving production shapes/quant/path; then target model on reduced allocation. | Benefit may disappear when serving becomes bandwidth-bound; never assume same percentage. |
| Copies/traffic reduction | Small allocation retaining relevant memory level and representation. | Cache vs DRAM and preprocessing cost change the claim. |
| Blocking/prefetch/layout/repack | Match working set, cache, placement and dispatch. | Same quant label is insufficient; cache route only under matching dependencies. |
| Barriers/scheduling/partitioning/NUMA/scaling | Representative thread/topology geometry. | Small-only null cannot retire a scale-sensitive idea. |
| Unknown/mixed | Safe exclusive exploration, uncertainty recorded. | Missing transfer/classification is not a blocker to all experimentation. |

Prefer actual target on fewer cores over a tiny model that changes the kernel under study. Intermediate
sizes are optional tests of a specific scaling uncertainty. Periodically sample rejected small-screen
candidates to detect false negatives; rate/selection remain proposed design choices.

**Transfer and coexistence are independent:** predictive partitions may still be contaminated by a
compiler, and isolated tests may still mispredict serving. Research profiles bind workload+neighbor,
allocation/pressure bounds, topology/runtime dependencies and quiet-versus-overlap evidence. Store them
through the existing contention provider, separately from serving-throughput allowances.

No profile means serialize incompatible **owned** work under its applicable admission policy, not seek
operator approval or veto search for ordinary foreign load (§8.17A). Cache validated routes and
profiles until relevant dependency/declared expiry/drift changes. Telemetry alone is not absence proof
for fabric/DRAM interference: certify against quiet controls and monitor the envelope DURING arms,
including placement/warmup/residency. Apply the protocol's predefined disposition: recorded search noise
can widen reported uncertainty, not an acceptance threshold; invalidate/repeat only on that protocol's
actual invalidity conditions. No selective favorable samples. Indexing/hashing/cleanup/actor CPU are
neighbors too. Quiet/overlap profiling is a separate planned experiment, not an ad hoc quiet-host demand.

### 8.8 Proposed adaptive scheduling and independent budgets

Adaptive seed priority and production coverage are accepted; algorithm/numbers below are provisional:

- Weighted deficit scheduling by held physical-region and GPU-device time, including GPU stages' CPU
  claims; retain the resource vector and charge load/warmup/build/validation, not just timed inference.
- New target weight 2 until three valid comparisons **or** a finite charged-time/attempt cap; normal
  weight 1; one boosted seed/backend, FIFO. Duplicates earn no new boost (§8.17D).
- Thereafter weights bounded 1–3, revisited every ten valid comparisons using target-scale confirmed
  outcomes, not screen gains alone. Exact update formula remains open for iteration.
- Bounded production-coverage rounds and reservations supplement weights; §8.17D defines the service
  bound and eligibility/outage assumptions. Bound the ready queue to limit obsolete work.
- Calibration and validation are explicit budgeted work, not unbounded priority. Invalid arms/outages
  cost operational budget but are not scientific nulls. No runnable backlog -> release and wait visibly.
- Count informative bounded transfer negatives and precision improvements as research outcomes, with
  their scope/power retained; do not reward only positive mean-throughput keeps. Forecast measurement
  cost from completed independent units under the current recipe, not a retired recipe's spread.

Separate provider retry, hypothesis review, patch repair, contamination retry, calibration, serving/LOO
and campaign budgets. Learn cost from observed stage durations. Report exclusion, resource waiting,
actor waiting and no-eligible-work separately. Optimize valid research per budget; contaminated hardware
saturation is not productivity. §8.17D supplies the proposed deterministic algorithm; numerical budgets
and adaptive coefficients remain for iteration, not unstated runtime defaults.

### 8.9 Proposed runtime fast path and measurement repairs

Versioned recipe option sets declare supported model/backend, argv/env mapping, compatibility and
effective-path witness. In-contract combinations are deterministic, reuse binary, skip critic calls,
and use ordinary correctness/measurement. New options/arbitrary env/build/source changes retain review.
Flag acceptance is insufficient: detect absent compiled knobs, no-op controls, unexpected fall-through
or op coverage. Runtime recipe hashes are part of experiment and champion identity.

Serving instrument proposals:

- Version common-window completed-token throughput separately from sum-of-slot decode rates.
  Exclude declared startup/warmup from the metric but charge scheduling; retain production concurrency
  and speculation. Report request latency, and TTFT via suitable streaming capture if adopted.
- Counterbalance AB/BA and use identical declared estimator for A/A calibration and comparisons.
  Calibrate its actual distribution at the independent arm/block count, not individual-run deviation.
- Floors bind model/resolved recipe/metric/estimator/instrument/placement/coexistence and independent
  `unit ∈ {arm, session, process}`. A gating-floor calibration requires **n≥24 and an interval**, not
  just a point; missing/cross-unit floors refuse. This minimum is for calibration, not every experiment.
  Preserve historical dispositions; older floors acquire rederivation debt, not retroactive re-verdicts.
- Register fixed N **or a complete sequential look/stopping plan** before execution using reusable
  protocol templates; no outcome-chosen extension. The CPU two-look sign test is a worked example,
  not a reason to ban registered early stopping. Direction-only evidence cannot mint a magnitude.
- Replay stored samples through the declared estimator/version once per immutable calibration and
  applicable policy identity; cache the validated result for routine arms. Require reproducibility
  before gate use. A differing quantile convention/normalization is not rounding to accept
  silently. Changes cannot inherit an incompatible floor; n≥24 alone does not guarantee useful precision.
- Preserve attempted/completed/valid/scored counts; prompts within one arm and reuse of the same
  treatment arm do not manufacture independent samples. Pairing alone does not prove contamination cancels.
- Preserve correctness/library/dispatch/residency evidence; search cannot edit its measurement policy.
- Dispatch comparator by **estimand**, not only experiment type: same-binary env arms can test level
  and/or dispersion without rebuilding. Emit separate conclusions; a nonsignificant level contrast does
  not answer a tail-compression hypothesis. A null needs power/bounds and both-direction mechanism controls.

Exact per-target objective/window, estimator, calibration design, non-regression/equivalence margins
and legacy metric migration remain explicit discussion items, not accepted thresholds. Reinspect source
and run controls before implementing a repair; do not widen policy to fit observed noise.

### 8.10 Proposed champion evidence matrix and validation cadence

Distinguish accumulated source+recipe candidate, last globally validated candidate+recipe record, and
current frozen-production comparator. Matrix rows bind actual measured build and proposed candidate,
model/backend/operating mode/resolved recipe/metric/
instrument, correctness, validity and effect. CPU pass cannot certify GPU; runtime keep changes identity
even with unchanged source SHA. A new candidate cannot reuse earlier combined-candidate rows for its own
manifest; those rows remain valid for their original immutable batch, as do per-change historical findings.

Proposed global validated advancement waits for required **production-optimal serving** rows at identical candidate
identities. §8.17C explicitly replaces §3.0's proposed any-surface/shared-cor transition with an immutable
validation batch and one atomic advancement; existing policy remains until adoption. Preserve required
re-baseline/LOO rules. Missing resources hold their
validation rows while scoped research continues. Candidate models are advisory unless explicitly required.
Absolute headlines require serving-class evidence with its registered recipe and protocol status visible;
bench relative comparisons remain on their own surface, never cross-class ratios or conversion factors.
Non-production BASELINE and bench cells that cannot exercise the registered recipe are addenda, not
production promotion vetoes (MEASUREMENT.md §5). Products of solo gains remain estimates.

Retain compound-then-gate and the **already-ruled four-keep cadence**, OR the configured gain trigger
(R23-54; research `56195d3e`, `SERVING_GATE_EVERY_KEEPS=4`). The durable counter resets on every completed
gate run regardless of outcome; trigger reason is threshold/cadence/both. No calibrated floor means no
serving spend under the existing guard. A proposed additional 24-hour due signal is for iteration, not a
replacement for four keeps and never weaker acceptance. §8.17C separates that counter from outstanding
validation debt. Budget required LOO at validated advancement over assembled
candidate/required surfaces. Neutral/inconclusive removal evidence does not automatically justify deletion.
Record drops with evidence; resulting new candidate needs applicable validation. Do not globally discard
dormant quant-specific improvements based on another target's null, or seed from production mid-cycle.

### 8.11 Proposed low-friction Vidya integration

Reuse the already-filed **VB-INF70-ARMS / SC75** source/task for CPU arm capture; do not recreate it.
At future implementation start, register any distinct current-loop capture source in
[`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md) and link its task in
[`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md). This documentation update
creates no measurement producer and claims no new hook. Adapter verifies original artifact identities,
projects into `ClaimTuple`, and delegates to existing `grade()`; no new ladder. Invalid attempts stay
operational records. Typed versioned applicability projection links value/unit/scope/dependencies to
event/claim/evidence IDs without dumping arbitrary extra into legacy frames or changing their IDs.

```text
retrieve(target_scope, mechanism?, intended_use, limit=40)
  -> exact | supported_transfer | hypothesis_only | incompatible
     findings, scoped nulls, transfer links, conflicts/staleness,
     missing-evidence suggestions, snapshot frontier and reasons
```

Quality and applicability filter independently. Supported transfer requires recorded source/target
comparisons; class labels are priors. Unknown historical scope cannot certify overlap/exact transfer.
Apply warrant/epoch rules by record class and intended use (§8.17A/E). Cross-epoch P-AK search history
can supply attempted mechanisms/conclusions, **not comparable numerical values** (A3). Separately, the
operator permits pre/post-BIOS absolute serving observations: show those rates under their actual
authority, while simultaneous changes limit causal attribution and changed dispersion requires new floors.

Async consumer tails journal at a durable cursor, ingests deterministic IDs, advances on acknowledgment,
quarantines malformed events individually and publishes an atomic local index. Planner reads once per
proposal batch plus unprojected local attempts to avoid immediate repeats. No network query per arm,
compiler or scheduler tick, no corpus rescan per iteration, and no additional LLM call for classification.
Use existing journal as outbox, not another delivery ledger.

Vidya outage permits fresh local measurements and established safe exploration; new overlap requiring
missing evidence falls back to serialization. A validation decision waits on its own evidence, not all
research. Recovery catches up idempotently. Invalidate topology/neighbor->coexistence, recipe/instrument
->calibration, model/shape->matching, relevant code/dispatch->transfer, candidate->combined validation.
Age alone is not universal invalidation. Retain scoped history and supersession/retraction reasons.

Provisional targets: query p95 ≤100 ms on 100k events; normal lag ≤30 s outside quiet windows; batch
≤100 events or five seconds; added bookkeeping <1% of campaign wall time with denominator reported.
Append at lifecycle boundaries, not tokens; never weaken fsync for a target. Hash immutable verified
artifacts once and cache; broker/suspend heavy projection/hashing/cleanup around quiet windows. Accepted
nonnumeric constraint: zero added routine operator interactions or critic calls for established sweeps.

### 8.12 Proposed standalone lifecycle, dashboard and storage

Small research-owned supervisor wraps existing engine, independent of tmux/monitoring agents/orchestrator
API. Coordination grant service remains necessary for new authority. Avoid old controller custody machinery.
Persist desired state separately from observed worker state. Proposed states: starting, recovering,
running, waiting_resource, waiting_actor, paused, draining, drained, validation_required, failed, complete.

- Pause closes new admissions, completes safe active work and releases compute when quiescent; service remains.
- Drain closes admissions, completes or invalidates bounded work, stops workers and releases claims.
- Resume reconciles identities and reacquires authority/claims; paused state survives restart.
- Actor outages honor reset/retry hints, otherwise bounded exponential backoff; repeated identical
  failure becomes visible cooldown, not spin. No silent model/provider changes outside explicit fallback list.
- Recover owned children using PID-start/process-group/cgroup identity, not names/stale JSON. Respect
  valid long-running measurement drain boundaries and make partial invalidation visible.

CLI/UI share typed idempotent commands, requested -> applied/refused(reason); daemon is sole writer.
UI says pending until acknowledgment. Duplicate clicks/reconnect/concurrent requests cannot duplicate
seeds. Keep /loop in existing hub, registered health/freshness. Proposed **research-producer-owned**
gateway uses owner-only Unix
socket plus token-paired browser session, token+trusted origin for writes, no credentials in URL, no
arbitrary shell/executable request. Current GET/CORS is not authentication. Token lifecycle/storage and
gateway detail remain design choices; minimal controls are accepted. Browser contacts the producer
directly; the hub owns page/nav/registry and does not proxy commands or acquire broker authority
([plane rule](../../dashboard/README.md)). Advanced configuration stays in CLI.

Display loaded producer/schema/instance, heartbeat, stage/activity/deadline, last valid scientific result,
actor last success/retry/reset, requested/granted/held/used resources, target/seed coverage, refusal/
contamination/supersession, accumulation vs validation, evidence age/projection lag and exact prerequisites.
Fold actor/evidence availability into health; HTTP reachability is separate. Proposed heartbeat 30 s and
missing-producer deadline 180 s do not define stage progress. Single synchronized writer stops/joins
the worker's status publisher before terminal publish and covers startup claim/profile and shutdown
errors; the retained supervisor heartbeat remains live (§8.17G). Verify loaded
version, not just source commit, when claiming deployment.
Scientific cards also expose instrument class, actual measured artifact, resolved recipe, independent
unit, n/interval, protocol/calibration status, and supported conclusion strength. Separate single-user
rate, highest **measured** aggregate point and selected operating point; never label a sweep endpoint
as an established ceiling. Preserve historical sum-of-slot-rate identity until a versioned metric migration.

Reserve space before builds; protect active, validated and in-flight/referenced generations (absolute
RUNPATH means copied builds need original paths). Reclaim only explicitly unreferenced disposable
artifacts through recoverable operations, never age-only guesses. Keep source/recipes/journal/results
durable; rotate logs and bound campaign-owned actor storage. Maintenance is brokered; disk pressure
pauses storage-heavy admissions while reporting/control remain. Do not prune unrelated users' databases.

### 8.13 Proposed work packages and existing-task mapping

**NOT A DISPATCH QUEUE.** IDs retain implementation detail for iteration; no new implementation
checkboxes are created. PLAN-DOC-2 owns review. P1/P1b consolidation remains its owners' operational work.

| Proposal | Deliverable | Dependencies | Acceptance / existing mapping |
|---|---|---|---|
| AK-AUTO-01 | Reconcile code/fold state and dated findings | — | No stale live claims; final aggregate anchors future launch; preserve P1/P1b. |
| AK-AUTO-02 | Native current-loop journal and safe recovery | 01 | Keep replay once; corrupt bundle cannot certify; expands R23-51. |
| AK-AUTO-03 | Topology and policy/claim-provider path | 01; OP-41 operator gate | Sibling affinity conflicts; standalone activate/renew/release; design dependency does not move broker implementation ahead of promotion/reboot. |
| AK-AUTO-04 | Manifest/target enrollment | 01 | CPU/GPU/both/candidate resolve without lineup mutation; P2 expansion. |
| AK-AUTO-05 | Broker all compute/build paths | 02,03,04; OP-41 operator gate | Operator-owned implementation after finalisation/promotion/reboot; no unlocked build paths or queued-stage expiry gaps in eventual acceptance. |
| AK-AUTO-06 | CPU adapter and serving repairs | 04,05 | Explicit metric/calibration/units and witnesses; recheck fixes; P2. |
| AK-AUTO-07 | Runtime fast path and mechanism routes | 05,06 | No extra critic calls; scale-sensitive null not globally retired; P3. |
| AK-AUTO-08 | Prospective Vidya and scoped local retrieval | 02,04 | Typed scope, idempotence/outage recovery, unchanged grader; reuse SC75 and register only distinct current-loop sources. |
| AK-AUTO-09 | Certified coexistence/adaptive scheduling | 05,06,07,08 | Cache reuse, uncertified incompatible owned work serialized under policy, seeds advance and production not starved; P4. |
| AK-AUTO-10 | Evidence matrix/batched serving/LOO | 02,06,08 | One surface cannot certify others; assembled evidence; P2/R23-48. |
| AK-AUTO-11 | Supervisor/minimal authenticated controls | 02,04,05 | Persistent idempotent lifecycle, honest health, bounded recovery; proposed replacement for P5 endpoint. |
| AK-AUTO-12 | Migration/bounded live run/unattended acceptance | 07–11 | Tests below, no monitoring agent required for routine recovery. |

Retain one INF-73 row; future implementation reuses existing task text/owners instead of duplicating
P2–P5/R23/FOLD checkboxes. Update normative loop description only when adopted. Do not rewrite measurement
constitution or compute-authority policy as a side effect of this documentation update.

### 8.14 Proposed tests, migration and completion criteria

| Area | Test scenarios |
|---|---|
| Recovery | Crashes around intent/commit/completion/checkpoint; corrupt/missing bundle, torn tail, replay/cursor, disk full, missing artifact, branch movement; exactly one keep and no false validation. |
| Candidate concurrency | Two racing keeps -> one integrates, one superseded/retested; runtime change cannot reuse source-only evidence. |
| Claims | Sibling-only affinity, cross-role conflicts, partial acquisition rollback, denied/disabled provider, renewal/expiry, queued build after pause, orphan recovery; no lock deletion. |
| Coexistence | Serving allow not research proof; unvalidated shared DRAM serialized; stale topology invalidates; quiet controls detect bias even when occupancy looks clean. |
| Statistics | Instrument-class separation; unit and n≥24/interval floor admission; replay equality; registered sequential looks; level vs dispersion; complete screened units only; power plus both-direction controls for bounded nulls. |
| Transfer | Same threads/different topology, same quant/different shape/dispatch, absent/supported/refuted transfer, scaling null not global rejection, composition-dependent invalidation. |
| Beliefs | Legacy frame IDs/grader unchanged; scope retained, epochs not pooled, quarantine, replay equivalence, outage safe exploration and idempotent catch-up. |
| Controls | Duplicates/concurrent CLI/UI, paused/draining restart, unauthorized writes, browser disconnect, no silent actor fallback, orchestrator-API outage. |
| Health | Long healthy stage vs stalled child, quota/auth/malformed output, producer death with live hub, hub restart, terminal overwrite prevented, loaded-version proof. |
| Storage/overhead | Referenced RUNPATH generation protected; maintenance obeys quiet windows; projection/retrieval and campaign overhead measured; no routine extra review/operator steps. |

Proposed migration: isolated pinned runtime -> inventory final champion/bundles/recipes/evidence -> import
legacy observations without retrofitted warrant -> preserve rollback stores -> authorized owner boundary
-> initially serialized broker -> partition routes -> only certified overlaps -> adaptive scheduling/
controls after bounded checks. This does not authorize a stop/relaunch now; cutover remains separate.
The broker step is additionally held behind the operator's finalise → promote → reboot sequence;
R23-64/65 and new post-BIOS calibration dependencies remain explicit rather than inferred completed.

Proposed acceptance: bounded mixed run, then **48-hour** unattended soak with production CPU, production
GPU and seeded local candidate. Source/build and prevalidated runtime routes; **ten valid comparisons
per active backend**, target-scale confirmation (valid null acceptable), useful overlap under one certified
profile; actor/worker/dashboard/Vidya faults and pause/drain/resume. Duration/counts are provisional.

Eventual completion: no routine manual relaunch/monitoring agent; no unlocked builds, protocol-invalid
units accepted as evidence, implicit confirmation, false full-scale transfer, or eligible-production starvation; seed progress;
no extra critic calls for established sweeps; visible bounded overhead; durable reproducible candidate
and truthful dashboard. Positive kernel gains are not required to prove the service works.

### 8.15 Provisional defaults and next discussion

Accepted directions are in §8.1; the operator did not approve every number/detail in the previous draft.

| Proposed detail | Open refinement |
|---|---|
| Local artifacts / llama.cpp-first v1 | Remote enrollment and speech-adapter scope. |
| Four claim regions, sub-quarter execution | Discovered topology and actual concurrency; region is not assumed to be NUMA node. |
| Seed 2×/three comparisons; weights 1–3/ten-result update | Exact formula, normalization, starvation and repeated-null/futility policy. |
| Sample small-screen rejects | Rate and selection avoiding expensive universal confirmation. |
| Existing gain trigger + **ruled four-keep cadence**; proposed 24-hour addition | Only the time trigger/new multi-surface budgeting remain provisional; preserve R23-54. |
| Global validation before shared cor advance | §8.17C specifies the replacement transition and LOO semantics; not yet adopted/implemented. |
| Common-window throughput / counterbalanced comparison | Objective, estimator/calibration, margins and legacy migration. |
| 30 s lag; 100 events/5 s; query 100 ms at 100k; overhead <1% | Feasibility, denominators, quiet-window behavior, invalidation dependencies. |
| Heartbeat 30 s / missing 180 s | Independent stage/activity and retry deadlines. |
| Socket + token-paired browser controls | Token lifecycle and gateway security without per-command ceremonies. |
| 48-hour / ten comparisons per backend soak | Workload/cost and fault schedule; positive gains unnecessary. |

**Next action here:** iterate these implementation details with the operator and update this notebook.
Do not run proposed work packages or turn defaults into new approval friction. The broker enforces
allocations; belief-backed mechanism awareness should make choices cheaper and less conservative while
preserving the distinction between permission to explore and evidence sufficient for production claims.

<a id="final-closeout-audit-20260908"></a>

### 8.16 Final-close-out audit — refinements to implement later, not a new execution queue

**Audit basis:** root `2a710cab`, both final September 8 progress records, the committed CPU close-out
packet, GPU sweep and R23-58 receipts, and targeted source inspection. Research shared checkout inspected
at `6ab403ed`; self-draft support separately inspected at `c3e362a1`. No benchmarks, servers, builds,
reboots, policy amendments or deployment changes were performed. This section refines the implementation
notebook; it does not adopt §5b's unowned residue or reopen either closed research session.

#### A. Evidence that changes the plan

| Final finding | What follows for unified AutoKernel |
|---|---|
| CPU process-THP recipe adoption, but GPU R23-58 ends T0/D0 bounded null after 48 launches; controls fired in both directions. | One source champion needs a target/surface recipe map. CPU adoption must not set GPU defaults; GPU non-transfer must not retract CPU evidence. R23-58's coarse simulated power was ~0.97 for a 3× dispersion effect and ~0.69 for 2×; this is not proof of no smaller effect. |
| CPU final characterisation uses instrument `bin-r1`/build 10303, with champion-control state explicitly set; THP fold record identifies source `2516c9807`, not clean `ef81196d5`. | Store actual measurement identity separately from intended delivery. The instrument adds knob-page/dispatch controls and is explicitly NOT TO FOLD. Reports' champion label is not a binary identity witness. |
| Pristine contains neither THP knob; CPU final contrast changes source and adopted recipe. | Preserve `recipe_to_recipe` scope; it is not a source-only or THP-only attribution. The asymmetric champion divergence remains R23-62, not explained away by adoption. |
| Late MEAS-4 correction: t48 was previously measured, with spread placement over all CCDs/NUMA nodes. | “Unused cores” is not unused cache/memory capacity. Encode placement geometry and test partition recipes; do not infer an available contiguous half. R23-64/65 own the post-BIOS revisit. |
| Same-build runtime and dispersion questions needed a separate runner; env, recipe hash and self-draft support were added during the campaign. | Reuse those fixes at verified revisions. Generalize experiment plans/estimands and run a recipe expressiveness matrix, rather than creating another ad hoc runner for each knob. |
| Stored/recomputed floor values differ; n=10 tail floors are unstable; new n≥24/interval/unit rules are ratified. | Version and replay the estimator, retain raw sample membership, check calibration applicability. Never treat an estimator change or different build/window as proof of changed host variance. |
| Partial MTP arm looked ~7% faster because its prompt/token mix was incomplete. | Completion and screening are scientific admission conditions, not UI formatting. An in-flight fast arm cannot enter means, spread, beliefs or scheduling scores. |
| GPU curves differ by model, and v9 has no measured matching DFlash2 production baseline. | Optimize an operating frontier under an explicit objective; distinguish highest measured point from ceiling and capability gain from an unmeasured speed ratio. |

Sources: [final CPU report](../../docs/design/inf70-close-out-20260908/CHAMPION-FINAL.md),
[THP fold record](../../docs/design/inf70-close-out-20260908/FOLD-RECORD-THP.md),
[CPU final progress](../../progress/2026-09/2026-09-08-inf70-audit.md),
[AutoKernel final progress](../../progress/2026-09/2026-09-08-ak-rebuild-20260828.md),
[GPU sweep](../../docs/design/champion-max-performance-20260908.md), and R23-58/61/62/64/65 in
[the rebuild handoff](autokernel-rebuild-program.md). Raw CPU `PREREG-FINAL.md` and GPU
`VERDICT.json` are in research `data/inf70-retest1-2026-09-08/` and
`data/ak-r2358-shim-serving-2026-09-08/`; original evidence commits are recorded in the final progress.

#### B. Recipe identity and expressiveness — one resolution path, no hand transcription

Proposed contracts refine AK-AUTO-04/06/07/10 and existing U3-EXPRESS/U3-SEED/U3-DEFAULTS-b:

```text
resolve_recipe(template, target, surface, operating_point, build, environment_policy)
  -> ResolvedRecipe + CapabilityReport
ResolvedRecipe:
  template_id/version/hash; model and optional drafter identities
  speculation_kind: none | self_draft | external_draft
  resolved argv; measurement-relevant env; explicit_unsets
  declared defaults; requested overrides; dependency/master-off semantics
  controls[]: {set_at: process_launch | runtime_arm, scope_definition, state_witness}
  effective_state_witnesses; normalized_execution_digest
ChampionRecord:
  intended_source; build_manifest
  recipes[(target_id, backend, operating_mode)] -> normalized_execution_digest
EvidenceBinding:
  actual_measured_source/build/object_digests; runtime_state_snapshot
  intended_delivery_id; typed_equivalence_receipts[permitted_uses] | validation_required
```

Resolve/load once per immutable generation and reuse it for launcher, calibration, comparisons, report
and dashboard. Keep template/module-source hashes as provenance, distinct from resolved execution identity.
Normalize launch to process only when each sample is an independent process; preserve the policy's
arm/session/process distinctions with explicit unit definitions and IDs. The comparison unit belongs to
ExperimentPlan, while activation scope belongs to each control—a recipe can contain launch and runtime
controls together. No new LLM call or per-run approval is needed for this resolution.

**Source-confirmed holes to design out, not fixes made by this audit:**

- `Recipe.with_env(KNOB=None)` at `c3e362a1` removes only the declared recipe override, while
  `server_env()` starts from inherited environment. A parent `KNOB=1` can survive an intended unset;
  the declared recipe hash does not expose that difference. Model **unset / set / permitted inherit**
  separately; apply explicit unsets after constructing the inherited environment. Hash/record only the
  allowlisted measurement-relevant resolved environment; never dump credentials into evidence.
  R23-58's THP readback would catch this mismatch, so this finding does **not** invalidate that run;
  generic recipes with no readback do not have that protection.
- The rescued CPU draft declares `CHAMPION_PIN_RESOLVED=False`, but its `preflight()` does not test
  the flag and its digest function checks old champion3 objects. A declarative flag/test of the flag
  is not an enforced refusal. Final-candidate admission must execute the unresolved-pin check; a
  diagnostic `--skip-digests` path must never emit verified final-candidate evidence. The existing draft
  is a starting point, not a proven final-candidate launcher.
- THP `prctl` and model-buffer `madvise` are separate controls. Record master-off dependency and verify
  `THP_enabled` in the launched process; time-dependent AnonHugePages alone is not a general switch
  witness. Diagnostic knob-page defaults differ from champion state: capture each arm's effective state,
  not just the process environment or source defaults.

Expressiveness fixtures should cover existing admitted targets first: CPU/GPU placement, none/self/external
speculation, drafter-specific flags, per-arm and per-launch state, unset/master-off, cache/batch/context
and concurrency. Unsupported combinations return structured capability reasons. Future multi-GPU/RPC,
LoRA and sampler extensions remain scoped capability entries, not a demand to implement every backend
before first use. Existing `c3e362a1` absence semantics map to explicit self-draft in the proposed schema;
do not break existing JSON recipes silently. Recipe validation/plan creation must be useful without compute.

Sources: research `loop/serving.py::{Recipe.with_env,Recipe.server_env,Recipe.recipe_hash}` at the inspected
revisions; [CPU recipe draft](../../docs/design/inf70-close-out-20260908/qwen38_flash_next_recipe.py.draft),
[pin caveat](../../docs/design/inf70-close-out-20260908/README.md), and research `PREREG-FINAL.md`.

#### C. One typed comparison plan and admissible-unit pipeline

Proposed `ExperimentPlan` carries `instrument_class`, `category`, `phase`, `protocol_ref`, `record_class`,
`intended_use`, `comparison_kind`, `estimand`, changed factors,
metric/estimator identities, required unit/control/completeness predicates, pairing/order, fixed-N or
registered sequential stopping rule, power model/margins, calibration reference and permitted conclusions.
`comparison_kind` distinguishes controlled mechanism attribution, assembled candidate comparison and
best-supported-recipe product comparison. `estimand` distinguishes level, dispersion and separately
registered objectives; a variance effect cannot be inferred from a mean test or vice versa.

Use reusable deterministic templates, populated from the resolved recipe and existing policy, then
freeze/hash once before execution. One shared validator feeds comparison, journal publication, planner,
dashboard and Vidya projection; it validates existing warrants and delegates grading to `ClaimTuple.grade()`.
It is not another grading ladder or critic review. Missing formal serving-protocol registration
(RATIFY-MEAS-2) stays visible: exploration/evidence collection can proceed within authority, but a template
cannot invent an approved protocol ID or auto-ratify a gating claim. Apply-time human boundaries stay intact.

```text
native samples -> complete independent unit -> predefined screen disposition
  -> immutable admissible-unit view -> exact estimator + registered stopping rule
  -> typed conclusion + claim eligibility -> journal / planner / dashboard / belief projection
```

Completeness includes expected prompt IDs/counts, workload/token-mix identity, terminal marker and required
witnesses. Preserve `flagged_but_retained(reason)` separately from CLEAN and rejected, following the declared
policy. All consumers use the **same unit set**; a dropped arm cannot reappear in floor estimation or CI.
Repeated prompts inside one process do not multiply independent launch N. Control assertions must witness
the execution path in both directions—not merely a profiler's task-plan counter that execution ignores
(SYNC-18's exact failure). Zero/insufficient observations return invalid rather than an empty PASS.

Typed results keep `inconclusive`, `direction_only`, `estimated_effect`, `bounded_null` and `regression`
distinct. A purported null missing its power record or fired-knob control is `untested` under
BOUNDED-NULL-1; retain the raw measurements and missing-warrant reason. This is different from a valid
measured contrast whose documented power/resolution is inadequate: that is `inconclusive`, with its
effect/uncertainty preserved. Do not encode the
CPU six-pair direction-only THP keep as a validated +5.23% magnitude, or the joint FIX-1+FIX-3 regression
as two separately significant component effects. Save the original registered action separately from
today's claim eligibility; policy upgrades do not silently rewrite historical decisions.

Sources: [FIX1 result](../../docs/design/inf70-close-out-20260908/FIX1-RESULT.md),
[final-arm completeness](../../docs/design/inf70-close-out-20260908/CHAMPION-FINAL.md),
[ratified rules](../../MEASUREMENT.md), and final CPU progress §§6/10.

#### D. Calibration, precision economics and host changes

A proposed `CalibrationReceipt` contains exact model/build/resolved recipe, metric and estimator version,
quantile/normalization convention, independent-unit definition and IDs, raw sample digest, n, interval,
window/host/neighbor envelope, sampler version and protocol. Deserialize → replay → compare **once per
immutable calibration, estimator and applicable policy identity**, then cache validation for routine
arms; invalidate the cache when those dependencies change. No raw-sample replay per arm.
The 4.581/4.494 and 6.657/6.596 discrepancies are **unreconciled estimator/provenance observations**, not
permission to choose a convenient value or assume rounding. A changed estimator creates a new identity.

Maintain reference precision and observed per-treatment precision separately. The CPU shim's paired test
and later six-launch characterisation support examining precision as a resource-saving lever, not a
universal fixed noise multiplier. Estimates from a few launches remain uncertain. Forecast cost under the
current recipe with that uncertainty; a cheap low-power “null” is not cheaper useful science. Select the
cheapest instrument that exercises the mechanism **and** matches intended use; MTP's better precision in
one CPU block does not license applying its floor to plain decode or another target.

For BIOS/reboot, retain pre/post absolute serving rates when metric/workload semantics match; classify
the difference as unattributed if several conditions changed. Do not hide improved capability behind an
era label or attribute it solely to a kernel. Re-resolve topology/host settings and recalibrate gating
floors because dispersion may change. No assumption that C8's prepared BIOS proposal equals the operator's
actual changes. R23-61a's pre/post choice and gated R23-64/65 remain the existing route, not duplicate tasks.

#### E. Selection, transfer memory and honest dashboard objectives

Seed the mechanism/transfer fixture with CPU-THP adopted / GPU-THP bounded non-transfer. Store source and
target scopes, actual mechanism controls, bounds, effect statistic, dependencies and registered disposition.
Unknown transfer permits scoped exploration; negative evidence suppresses **the same tested claim** until
relevant dependencies or the effect-size question change. It must neither retire all small possible
effects nor propagate CPU defaults to GPU. Cheap bounded disproof is useful progress, not a failed campaign.

For each target, retain the tested concurrency/placement frontier, objective and SLO, not only one scalar
best. `single_user`, `aggregate_capacity` and a selected responsiveness/throughput operating point are
different objectives. Choose under an explicit workload/resource envelope and policy; missing SLO does
not authorize inventing one. Publish sweep bounds and operator stop reason. The dense np=8 result is the
highest tested point with diminishing returns, **not a measured turnover/global ceiling**; the MoE np=16
endpoint likewise leaves its ceiling unknown. Small-n spread is descriptive, not a certified floor.

For kernel attribution hold a compatible recipe fixed. For product improvement compare each build at its
own best **supported** recipe under the same workload/objective/resources, with the changed factors visible.
Production lacking the experimental drafter is `unsupported_capability`, not a zero denominator;
`baseline_not_measured` emits no ratio. A candidate model outside production still gets a baseline in a
compatible experimental build. Cross-model architecture comparisons are not kernel gains. Preserve the
historical aggregate metric's exact definition; migrating to common-window throughput needs a new metric
identity and calibration, not a relabeled card.

#### F. Lifecycle coverage, durable closure and cross-campaign reuse

One campaign sampler should cover allocation/setup/eviction/load/placement/warmup, **between-arm gaps**,
request phases and teardown, with timestamp coverage attached to each unit. Otherwise foreign work can
change cache/placement before timed sampling begins. Recovery/re-admission uses the existing declared
quiescence/reset conditions; this notebook invents no magic cooldown duration. Retain ownership and
samples rather than guessing a culprit: the API stop was subsequently observed as a non-event in the
sampled CPU window, superseding the earlier suspected attribution, not proving global noninterference.

Reuse SC75's prospective CPU arm wiring. Its pre-September-7 erroneous sibling-isolation labels must not
be upgraded into clean measurements; keep historical records discoverable but emit no eligible measurement
claims from that known-bad set under the existing adapter policy. A corrected sampler version invalidates
dependent **warrant**, not the fact that a run occurred. New GPU residency capture R23-60 is already landed;
reuse its raw readbacks and inspect the loaded revision rather than restating it as missing.

Before releasing a campaign, derive a retention manifest from all evidence/candidate/recipe references,
including non-branch refs and absolute RUNPATH dependencies. Verify the backup actually covers the named
ref/object/artifact closure, not merely that a bundle command succeeded. Commit compact receipts/checksums
and explicit large-artifact provenance; never silently promote a hedge copy into the evidence record.
Drafts remain drafts, no-fold refs remain exclusions, and a closed researcher does not transfer ownership
of unadopted tasks. This is automated bookkeeping and validation, not an additional sign-off ceremony.

#### G. Acceptance fixtures and integration into the existing plan

| Fixture | Required behavior | Existing design/task mapping |
|---|---|---|
| Parent env sets treatment, control requests unset | Resolved control really unsets; digest distinguishes relevant state; THP readback still catches mismatch | AK-AUTO-04/07; U3-EXPRESS |
| Unresolved champion pin with old digests matching | Actual admission refuses; diagnostic bypass cannot claim final validation | AK-AUTO-01/04/10; PROD-1 context only |
| Instrument build in champion-control state | Preserve measured identity; no automatic clean-candidate timing/correctness inheritance | AK-AUTO-10; G2-CONC requirement |
| CPU adoption plus GPU bounded null | Two recipe entries; independent dispositions and power bounds; no cross-surface default leak | AK-AUTO-08/10; U3-DEFAULTS-b |
| Partial fast arm / dropped arm / zero evidence | Exclude consistently until complete/valid; never a gain or vacuous PASS | AK-AUTO-02/06 |
| Direction-only / component non-claim / dispersion-only effect | Claim serializer and all projections preserve conclusion strength | AK-AUTO-06/08 |
| Floor wrong unit, missing interval, n<24, or replay mismatch | Refuse new gate use with exact reason; queue scoped recalibration; keep historical record | AK-AUTO-06; R23-55/61/65 |
| Hypothesis control only changes profiler counters | No executed-path warrant; record untested and diagnose before spending measurement budget | AK-AUTO-07; SYNC-18 fixture |
| Production cannot load candidate recipe | Capability status, no invented speed ratio; optional own-best supported baseline | AK-AUTO-04/10; PROD-BASE-1 |
| BIOS change / superseded sampler | Absolute rate remains visible; attribution and calibration/coexistence eligibility updated separately | AK-AUTO-03/08; R23-64/65 |
| Operator stops sweep at highest measured point | Record endpoint/stop reason; do not claim saturation or resume without authority | AK-AUTO-11 |
| Scratch cleanup or session retirement | Referenced evidence/refs/build dependencies survive; unresolved ownership remains explicit | AK-AUTO-02/11 |

**No duplicate execution queue:** these are refinements to §8.13's proposals and PLAN-DOC-2, not newly
authorized implementation tasks. Declined to create separate dispatch rows because this session's scope
is iterative design and existing U3/R23/SC75 rows already route applicable work. Before implementation,
re-resolve their actual state and ownership. OP-41 stays operator-owned and sequenced last as recorded.

**Audit cautions retained rather than copied into formulas:** some summaries call the final +5.958% bench
versus −2.18% serving contrast an “11-point” gap (arithmetic is 8.138 points, and cross-class subtraction is
not a performance claim); the listed sd values 2.793/0.501 do not themselves imply a 13× ratio; and one GPU
discussion compares unlike concurrency points as though they establish better per-user responsiveness.
Do not import those shorthands as evidence or thresholds. The ratified rules remain unchanged; this audit
does not edit protected policy or re-verdict historical experiments. Exact estimators and original
receipts, not persuasive prose, must drive future automated decisions.

<a id="implementation-contract-review-20260908"></a>

### 8.17 Fresh review — deterministic implementation boundaries

**Basis:** three independent read-only reviews of root `452bee84`, followed by reconciliation against
the ratified protocols, R23-54 and research `loop/accumulate.py` at `6ab403ed`. These are design refinements,
not implementation, new measurements, retroactive verdicts or adoption of unowned tasks. A–B identify
existing authority; the concrete interfaces/algorithms below are proposed ways to enforce it cheaply.

#### A. Phase-specific admission and evidence-use authority

The earlier blanket contamination/refusal wording conflicted with **ratified P-AK-SEARCH-1-A2**.
Ordinary foreign builds, agents, filesystem activity and host load are recorded noise for AutoKernel
search, not reasons to wait/refuse/abort or request quiet. This applies to search, not merely its cheapest
screen. The sole environmental-interference blocker is witnessed competing model inference overlapping
the held claim. Correctness, identity, power/frequency envelope and claim-witness gates remain mandatory.
The planner may reduce overlap among its **own** queued jobs under authorized resource policy, but cannot
turn that scheduling choice into a foreign-load veto, a signal to foreign processes, or a quiet-host demand.

| Phase / authority | Execution and reuse | Permitted consequence |
|---|---|---|
| A2 discovery, category CANDIDATE | Exactly three anchor invocations create an immutable baseline bank; exactly three candidate-only invocations per screen, zero new anchors while the full common frame matches. No strict T1 floor prerequisite. | Advisory nomination only; no banking, champion entry, readiness or headline claim. |
| Original P-AK confirmation, narrowed by its amendments | Fully paired, randomized, calibrated selection/confirmation; frozen ordering/stopping/control requirements. Never pool discovery samples into confirmation. | Strict evidence can satisfy the protocol's experimental banking/composition prerequisites; remains a search record, not a release claim. |
| Serving observation or owning release protocol | Execute the identified instrument and registered recipe; apply that protocol's validity/isolation requirements, not a search default. Missing RATIFY-MEAS-2 is observation-only where applicable. | Only the actual registered authority can supply a production gate/headline. A serving-class label alone grants nothing. |

Bank identity includes the full runtime/environment frame, not just a build hash. A2 runtime screens
require exactly one unequal runtime field and identical sealed executable/DSOs; no build/worktree.
Source-changing screens retain identical runtime semantics. No-op or multi-factor screens are invalid;
broader recipe combinations/product comparisons need their appropriate plan, not a fabricated A2 attestation.
Ordinary noise may widen **uncertainty** or reduce nomination priority, never the acceptance threshold.
Complete identity-matching phases survive restart and changes in ordinary load. Identity drift closes a
baseline bank; no relabeling it to the new frame. No retrospective application to pre-ratification records.

Proposed shared interface, evaluated from templates and cached receipts rather than actor paperwork:

```text
eligibility(record, intended_use, policy_snapshot)
  -> permitted | refused(reason, missing_dependencies)
inputs: record_class = discovery_screen | strict_search | observation | registered_claim
        category = OPTIMUM | BASELINE | CANDIDATE
        phase, protocol_ref/status, instrument_class, actual scope/identities, warrant refs
uses: explore | nominate | rank | bank | certify_transfer | certify_overlap | validate | headline
```

This is a **use/applicability check**, not a second grading ladder: `ClaimTuple.grade()` remains the
existing warrant grader. Persist the original authority/disposition; derive present use eligibility
without rewriting history. BASELINE diagnostics cannot veto or justify production promotion; required
rows concern the production-optimal serving recipe and its candidate counterpart. A3 permits same-epoch
search ranking, but cross-epoch search retrieval exposes attempted mechanisms/conclusions with staleness,
not comparable magnitudes. The separately authorized absolute pre/post-BIOS serving observations in
§8.16D do not repeal that search restriction.

Sources: [Annex K A2/A3](../../measurement/protocols/kernel-research.md),
[category and instrument rules](../../MEASUREMENT.md), and R23-54 in the
[rebuild handoff](autokernel-rebuild-program.md). These restrictions already exist; no policy amendment here.

#### B. Calibration applicability and measured-to-delivery identity

Separate **exact provenance** (`CalibrationReceipt` in §8.16D) from **applicability to a comparison**:

```text
calibration_applicability(receipt, complete_ExperimentPlan, registered_rule_version)
  -> applicable | recalibration_required(reason) | policy_undefined(reason)
```

The rule considers both actual arm identities, declared changed factor(s), resolved recipes, estimator,
experimental unit, planned count/stopping scheme, metric and host/coexistence envelope. It specifies
which intended source/build differences can share calibration and which runtime/placement/instrument
changes require a new one. Exact build provenance does not mean every source patch automatically needs
a wholly new floor; conversely, matching a model name or n does not establish applicability. A runtime
intervention affecting variance needs the registered treatment-aware comparison/calibration method;
do not transplant a control-only noise estimate or assume equal arm variances.

Resolve the gate's scalar floor and its use from the **existing registered estimator/policy**, retain
the calibration interval alongside it, and apply any registered precision requirement. Do not silently
substitute an interval endpoint, increase a multiplier, or reinterpret a percentile. If that mapping or
allowed transfer is undefined, mark only the dependent gate `policy_undefined`/`recalibration_required`;
discovery continues under A2. A new gate floor still needs n≥24 at the declared unit and an interval.
Cache applicability by receipt + complete plan dependencies + rule version; a cheap key check suffices
before each admitted stage. Neither every-arm raw replay nor an actor-selected calibration is required.

Equivalence receipts have explicit assertion/use types: output correctness, local-work/path equivalence,
or timing under a named workload/envelope. Correctness equivalence cannot certify timing. No receipt
overrides an exact-candidate requirement: **G2-CONC uses the promotion candidate binary**. A measured
instrument in champion-control state remains evidence about that instrument, not clean-delivery timing.
Historical measurements stay discoverable even when current validation requires a different build.

#### C. One accumulated candidate, one validation transaction, one frozen production reference

Proposed durable pointers—not separate per-surface champions:

```text
production_ref       # frozen kernel set and ratified serving recipe identities; never mutated by loop
integration_tip      # one assembled source/build/recipe-map manifest; experimental keeps may accumulate
validated_candidate  # one immutable manifest + complete required validation batch; may lag integration
ValidationBatch:
  id; candidate_manifest; comparator_manifest; required_row_set_version
  exact per-row target/recipe/instrument/protocol/objective identities
  required LOO treatments; receipts; outstanding debt; terminal disposition
```

Freeze a due batch at a specific integration manifest; newer keeps do not retarget its running arms.
Reserve budget to finish it, so perpetual integration cannot postpone validation forever. A passing
batch advances `validated_candidate` once through a journaled compare-and-swap on its expected predecessor;
it never claims a newer integration tip is validated. Per-row recipe hashes may differ across targets,
but all rows must belong to the **same manifest and required-set version**. CPU pass/GPU missing leaves
the batch pending; a newer recipe cannot inherit old rows. Missing capabilities/resources have explicit
row status, not zero denominators, fictitious pass values, or a veto from an unrelated optional model.

**Proposed replacement for §3.0/U2:** `cor` denotes this validated candidate, not the most recently passing
surface. Any-surface pass fills a row; it no longer advances shared `cor`. After a full batch advances,
mark all outstanding tip-versus-old-cor summaries stale and remeasure under each applicable harness
before quoting against the new baseline. Never rescale old percentages or copy a gain across surfaces.
Production promotion remains a separate runbook/operator action requiring its owning gates. Until this
design is adopted, preserve current behavior and annotate its limitations rather than silently migrating it.

Integration must survive source and recipe changes in **different repositories**: under the integration
lock verify parent, persist intent, create retained immutable source/recipe refs, then journal one
content-addressed manifest and atomically publish its pointer. Git commits across repositories are not
one atomic transaction. Recovery reconciles intent/trailers/refs; orphan refs remain retained until
resolved, and no half-published manifest becomes a champion. Workers never advance these pointers.

Each keep records source/build/runtime delta, parent manifest, affected scopes and dependencies. LOO
constructs a derived candidate with that treatment absent, not a blind commit revert on the live tip.
Runtime-only ablations reuse the same binary with a distinct recipe. Dependent source changes or two
keeps overwriting the same knob require an identifiable registered treatment; if impossible, record
`nonidentifiable`/`unsupported`/`build_failed`, not a neutral measurement or a satisfied required gate.
Evaluate required applicable production surfaces; preserve dormant-quant findings as scoped history.
Neutral/inconclusive LOO is not automatic deletion authority. Removing a keep creates another candidate
manifest requiring its own applicable validation; nothing rebases or rewrites frozen production.

Preserve R23-54's **four keeps OR gain trigger**, durable count and reset on every completed gate run,
including inconclusive outcomes. Refusal before a gate starts is not a completed run. Proposed unified
cadence counts each integrated keep once, not once per affected surface, and schedules a frozen validation
batch; retain per-surface receipts. Maintain separate `validation_debt` until required rows pass: resetting
the cadence counter cannot erase unresolved rows or falsely validate. Calibration absence exposes debt
and schedules its authorized prerequisite instead of spinning. The additional 24-hour trigger is still
proposed; it creates a due reservation, not permission to violate grants, policies or serving budgets.

#### D. Enrollment, accounting and bounded coverage without scheduler ceremony

```text
enroll(request_id, seed_spec) -> immutable TargetRevision + enrolled_event
  status: baseline_pending | ready | artifact_missing | unsupported_capability
Proposal:
  versioned_claim_key; target_revision; immutable parent/control/intervention identities
  mechanism/estimand/effect-bound question; route; required witnesses
  estimated stage resource vector/deadline; evidence snapshot + dependency generations
```

Keep the launch snapshot; later seeds append target revisions rather than mutate it. Resolve registered
references and pin the intended compatible baseline at enrollment (or the first capability-resolving
transition before execution), using actual model/build/recipe identities. Retries cannot silently follow
a moved reference. An artifact appearing later creates an explicit resolution event. Deduplicate aliases
by full workload signature, retain the union of production obligations/candidate roles, and grant no new
boost for a duplicate. Missing/unsupported targets report a precise prerequisite while other work proceeds;
this is not a decision to dismiss that model or permission to download/convert it outside v1 scope.

Proposed deterministic scheduler, implemented within one admission owner:

1. Charge each stage the time integral of its **held claims**: physical-region fraction, GPU-device
   seconds and any separately limiting memory reservation. A quarter claimed for four executing cores
   costs the quarter; GPU stages also pay their CPU claims. Include setup/load/warmup/build/teardown,
   invalid attempts and held idle time. Record estimated versus actual service; attribute shared builds
   once by a recorded apportionment rule, not once per beneficiary or to nobody.
2. At a coverage-round boundary freeze the continuously eligible production-frontier set and `K`/`D`.
   Give each member one bounded stage opportunity; arrivals/seeds cannot reset the round. Count **every**
   admitted expensive stage, including prerequisites/calibration/validation/reject audits/maintenance,
   exactly once against either its frontier's coverage slot or the `K` noncoverage slots. No uncounted
   priority queue may bypass this bound. With `N` members and maximum stage-plus-teardown `D`,
   conservative serial completion is bounded by `(N + K) * D`, plus explicitly recorded authority/resource
   outages and any already-running bounded stage. This bounds **service opportunities**, not valid results
   under unbounded noise/failures. Oversized jobs need a declared larger bound or scientific-safe chunking;
   never interrupt arbitrary samples to make a scheduling theorem look true. Reserve at least one
   noncoverage seed opportunity per round when an eligible seed and budget exist (`K>=1` then); otherwise
   “at most K” would allow zero forever. Use oldest eligible FIFO seed, skipping temporarily ineligible
   entries without resetting their history/budget. Dry-run refuses conflicting reserved-slot totals;
   new eligibility joins the next round rather than silently changing the current bound.
3. In noncoverage slots use weighted deficit over actual charged resource service. A normalized dominant
   share supplies a scalar ordering while the vector remains visible; grant changes start an accounting
   epoch without forgiving prior service. Normal weight 1; seed weight 2 ends after three valid comparisons
   **or its finite attempt/charged-time cap**, whichever first. One boosted seed/backend, FIFO; campaign
   budget bounds seed admission. Invalid-only seeds cannot monopolize a boost or block later seeds forever.
4. Adapt weights in the proposed 1–3 range at batch boundaries using same-epoch target-confirmation and
   informative bounded negatives/precision results per charged cost, plus uncertainty. No screen-only gain
   jackpot or cross-epoch numerical search ranking. Keep coefficients/reward normalization versioned and
   provisional; weights never override coverage, budget or evidence eligibility.
5. Reserve calibration, target-scale reject audits and due validation explicitly. Full-region reservations
   stop new incompatible backfill early enough to finish current bounded work; certified backfill cannot
   extend the reservation. Record budget exhaustion, infeasible stage demands and external outages
   separately. Resume existing rounds/debts after recovery instead of awarding a fresh startup boost.

Finite manifest defaults for stage limits, `K`, seed caps and reserve shares must be selected before
eventual deployment; dry-run reports the resulting bound/cost. This is configuration, not a new review
for each experiment. The coverage test uses fake time/claims; real service can promise no hard wall-time
bound while its external authority is unavailable. Initial admission stays serialized under §3.4;
certified overlap is an eventual policy revision within OP-41's sequence, not a per-profile operator task.

#### E. Transfer, coexistence and retrieval contracts

The versioned claim key covers target scope, intervention/control, mechanism, estimand, effect-size
question and dependency identities. A planner annotation is a hypothesis, never a path witness. Transfer
edges are **directed and nontransitive**, separately typed `correctness`, `local_work`, `serving_effect`:
A→B and B→C do not establish A→C, nor does CPU→GPU follow from a shared mechanism name. A bounded null
suppresses only its tested effect-size question under matching dependencies; changing a bound defines
a new question, not positive evidence or automatic renewed priority.

Routes declare preserved dimensions, required executed-path witnesses, covered targets and disposition
authority: `exploration_only` or `may_screen_out(scope, effect_bound)`. Matching a mechanism class alone
does not certify rejection transfer. Audit a configured fraction of rejects via a stable hash of claim
key + route revision, stratified by mechanism/allocation; record selection probability and charge a
separate bounded target-confirmation budget. Restart keeps the same sample. A successful target-scale
audit of a rejected candidate revokes the route's negative-screen authority in the affected scope, not
its true local result or unrelated correctness evidence. Audit-budget exhaustion stays visible.

Coexistence receipts bind measured workload, **complete neighbor multiset or certified pressure envelope**,
physical claims, all lifecycle phases, dependencies, registered equivalence margins, estimands and
uncertainty. No significant difference is not equivalence. A+B and A+C do not certify A+B+C; B tolerating
A does not certify A tolerating B. Certify each victim direction, including setup and burst exposure;
average pressure alone cannot cover untested bursts. Missing evidence/margins leaves owned incompatible
admission serialized, subject to A's explicit search/foreign-noise distinction. A serving-throughput
allowance is never a research equivalence receipt.

```text
retrieve(scope, claim_key, intended_use, limit=40)
  -> ranked_findings[<=limit] + mandatory_applicable_conflict/retraction_status
     dependency_generations + snapshot_frontier + complete_for_intended_use
admit_cached(proposal, local_generations) -> eligible | stale(affected_dependencies)
```

Indexed conflict/retraction checks occur **before top-k truncation**; a relevant refutation cannot hide
in position 41. Preserve raw grade separately from applicability. Maintain a reverse dependency index
and local invalidation generations; compare cached generations immediately before expensive admission.
A local retraction/recipe/topology change takes effect even while asynchronous Vidya projection lags.
Malformed invalidation events are quarantined with affected eligibility marked incomplete, not silently
clean. If dependencies cannot be identified, withhold certificate-dependent uses at the uncertain
frontier; fresh exploration remains available. Unrelated changes preserve cache reuse. No corpus scan,
network request, raw-calibration replay or LLM classification is added to the per-arm fast path.

#### F. Supervisor fencing, controls, grant expiry and scientific restart

One campaign-scoped exclusive supervisor/writer lock plus a monotonic **supervisor incarnation** fences
workers and command application. Use the host's service-manager restart facility with bounded backoff
and an explicit failed state; tmux or a monitoring agent is not the recovery mechanism. Separate process
incarnation from immutable campaign/config generation: an unchanged restart preserves campaign evidence.
Relevant topology/recipe/policy changes resolve a new generation and scoped invalidation before admission,
not a silent snapshot mutation or automatic research relaunch beyond the operator's authority.

Persist `launch_intent` with allocation/worker generation and a preassigned owned process-container ID
**before spawn**. On crash, reconcile that container and PID-start identities before replacement. This
closes the spawn-before-PID-receipt gap; recovery cannot assume absence because its JSON lacks a PID.
Workers return results tagged with campaign/config generation, supervisor incarnation and worker/allocation
identity, never write journal/pointers directly. Reject stale responses;
retain their raw artifacts as history. Another supervisor cannot steal a live lock or act on an old grant.

Commands contain campaign/generation, request ID, payload digest and expected control revision. Persist
acceptance before acknowledgment and linearize it with admissions. Duplicate ID/payload returns prior
result; same ID/different payload refuses; stale expected revision returns current state. CLI and browser
use the same contract. Show **accepted** separately from **completed**, with reason/deadline.

| Command | Admission boundary | Completion |
|---|---|---|
| pause | Close new expensive-stage admission. Already admitted bounded stage may finish within its grant/deadline; its queued successor needs fresh admission. | Quiescent, compute released, supervisor/control live; desired pause survives restart. |
| drain | Close admissions, finish only permitted bounded active stage or invalidate/tear it down at its declared boundary. | Owned workers/descendants gone, final state durable, claims released; no implicit restart. |
| resume | Reconcile retained work, config dependencies, control revision and authority; fresh admission only after checks. | Running or explicit waiting/prerequisite state; cannot erase a later accepted drain. |

An interrupted independent unit is invalid. Reuse completed units only if the frozen plan explicitly
permits continuation with unchanged identities, unit membership, ordering and stopping rules; otherwise
new comparison execution ID, old observations retained. Drain midway through a pair cannot create an
unpaired winner or an outcome-dependent extension. Reuse sealed completed phases per A2 instead of
restarting the entire campaign. Record reused-phase IDs in the new execution's lineage.

Each allocation receipt binds grant identity/deadline and ownership generation. Admission must fit the
bounded stage **plus teardown** within the remaining authorization or the provider's existing explicit
drain allowance; admission one second before expiry is not enough. A renewal watchdog blocks successors
on renewal failure; an already authorized stage may finish within its current deadline/drain allowance.
Distinguish failed future renewal from current revocation, and start bounded owned teardown in time to
meet the applicable provider deadline. Verify the affected allocation's owned descendants exited before
releasing its claims or admitting replacements. Uncertain ownership stops affected replacement, not a broad name-pattern
kill. The provider remains grant authority; this proposed consumer contract does not implement OP-41 early.

#### G. Coherent dashboard snapshots and lifecycle-aware health

Publish one versioned snapshot from the journal projection: campaign/config generation, supervisor
incarnation, journal cursor, projection sequence, generated time, producer/loaded schema/build identity,
desired/observed state, applied command revision and worker stage/deadline. Assign a durable monotonic
`stream_epoch` at producer incarnation/config-generation changes, plus a sequence increasing within that
epoch; compare `(stream_epoch, sequence)` within a campaign, never order content hashes lexically. Worker
telemetry carries its worker/allocation incarnation so delayed old telemetry cannot enter a new snapshot.
Health-only refreshes advance sequence without pretending the scientific journal advanced. Consumers
reject older stream keys; after an epoch change request a full snapshot, not a partial old/new merge.
Capture journal cursor, command revision and derived state atomically from one projection revision;
attach heartbeat/resource observations with their own sample timestamps and matching worker incarnation.
A stale cached page may display history but cannot acknowledge commands or claim live progress.

Separate supervisor heartbeat, worker stage/activity and last scientific result clocks. Paused/drained
campaigns intentionally have no active worker; that is not failed-worker health. A retained service keeps
its own heartbeat while its campaign is terminal; if the service exits, the terminal record is historical,
not live. Stop/join the **worker's** status publisher before terminal publication so it cannot resurrect
`running`. An actor/evidence outage degrades the dependent capability, not transport. Use existing `/health`
versus `/api/health` semantics and freshness envelopes; do not invent a second hub health definition.
Commands go directly to the authenticated producer gateway; hub pages remain non-proxy projections.

#### H. Code seams, versioning and acceptance fixtures

Keep changes in the existing ownership boundaries. The names below describe proposed seams, not installed
APIs; no monolithic second controller, second WAL, new evidence grader or new grant authority is intended.

| Existing home | Proposed extension / test seam |
|---|---|
| Research `autokernel/journal.py::Journal` | Typed phase/control/integration/validation events, replay and schema migration; crash/torn-tail fixtures. |
| Research `loop/run.py` and `loop/pipeline.py::SerializedTail` | Extract small campaign-service/admission interfaces around current engine; fake actors/workers/clock/claim provider. Preserve serial tail until immutable parent checks exist. |
| Research `loop/accumulate.py` | Immutable candidate manifests, validation batches/debt and cadence; CAS/restart/LOO fixtures. |
| Research `loop/serving.py`, `loop/bench.py`, `loop/residency.py` | Shared resolved recipe and ExperimentPlan/use validator, applicable calibration, unit view and lifecycle witnesses; no duplicated estimator per consumer. |
| Existing orchestrator claim/contention providers | Eventual operator-owned grant/region/coexistence contract; research supplies an adapter, not a competing policy daemon. |
| Root Vidya adapters and existing retrieval/projection | Prospective source registration at implementation, existing grader, scoped use/transfer and invalidation index; reuse SC75. |
| Research status/control producer; root dashboard hub | Producer-side command/snapshot schema and gateway; hub rendering/registry/freshness/health probes. |

Version event and manifest schemas; defaults for absent provenance are `unknown`, never clean/validated.
Keep legacy records readable as history; unsupported schema versions cannot grant evidence eligibility.
Migration writes a replayable versioned snapshot without rewriting the original journal. Rollback must
refuse unsupported newer state rather than fall back to `cor=anchor`; preserve the last compatible
read-only view and require a compatible engine for further admissions. New fields need adapter fixtures
and producer/consumer compatibility tests, not silent deserialization defaults that change authority.

| Deterministic fixture | Required result |
|---|---|
| Ordinary foreign build during A2; overlapping foreign model inference | First remains recorded noise; second follows witnessed checkpoint/resource rule; no foreign signalling. |
| A2 nominee/serving-class search record presented for banking/headline | Intended-use refusal; strict confirmation and owning release authority remain separate. |
| Wrong calibration unit/estimator, runtime variance intervention, output-equivalent delivery build | No incompatible floor or timing inheritance; exact-candidate gate stays exact. |
| Fourth keep, restart at count 3, inconclusive completed gate | Cadence fires/persists/resets as ruled; unresolved validation debt remains. |
| CPU row passes, GPU missing; recipe changes; crash during cross-repo integration | Accumulation preserved; no partial validation or half-published manifest. |
| Dependent source keeps, overwritten runtime knob, unsupported ablation | Identifiable LOO or explicit missing gate; failed revert never counts as measured neutral. |
| Duplicate seeds, moving refs, invalid-only seed, larger region than affinity, GPU host CPU | Stable enrollment/baseline; finite boost; exact charged claims and persisted coverage round. |
| Full-host validation waits while short jobs arrive; grant outage | Reservation prevents backfill starvation; opportunity bound excludes explicitly recorded outage only. |
| A→B/B→C, correctness-only transfer, rejected small-scale scale-sensitive idea | No transitive/timing inference; reproducible reject audit and scoped authority revocation. |
| Pairwise-safe but triple-contended work; asymmetric/bursty overlap | No composed or symmetric certificate; lifecycle/neighbor envelope enforced. |
| Refutation ranks 41st; retraction after proposal; malformed invalidation; projection outage | Mandatory status survives top-k; cheap local fence invalidates dependent use; fresh exploration survives. |
| Crash after spawn before PID receipt; two simultaneous supervisors | Reconcile preassigned owned container; one writer, no duplicate worker/claim use. |
| Duplicate/stale pause-resume-drain commands; restart mid-pair; grant expiry | Ordered durable controls, no successor leak, exact unit membership, teardown before release. |
| Delayed old snapshot after resume; hub restart while paused | No false running/command completion; intentional worker absence not producer failure. |

Run these with fixtures/fake time before any hardware spend; later real lifecycle/contention and unattended
acceptance remain §8.14, after their existing authorization gates. Integrate under AK-AUTO-02/04/06–11;
no new dispatch rows. The remaining numerical/objective choices in §8.15 are still iterative design,
but these failure modes now have explicit data, transition and test contracts. **Friction budget remains
zero additional routine operator decisions or critic calls for established runtime sweeps.**

<a id="implementation-ledger-20260908"></a>

## 9. Implementation ledger — started 2026-09-08

**Owner:** `autokernel-unified-20260908`. Root lane starts at `088427b0`; research lane starts at
`1d9733f1`. Shared checkouts, frozen kernel trees and research artifacts are not modified by lane setup.
Subagent output is proposed until main-thread review and targeted/integration tests accept it. Source
completion, main-branch publication, deployment and live measurement acceptance remain distinct.

**Current-code reconciliation:** `loop/run.py` still uses one GPU claim and `ExperimentStore` history;
the reviewed implementation now journals accumulator snapshots before publishing derived JSON.
Existing Journal, recipes, claim primitives and dashboard are reused, not mistaken for a unified
service. The four-keep cadence is present and survives recovery. Broad
historical P1/P1b/§5b tasks remain with their recorded owners unless explicitly adopted as a §9 slice.

### Executable slices and acceptance

- [ ] **AKU-01 — immutable campaign/target enrollment** (AK-AUTO-01/04): versioned CPU/GPU/both request,
  immutable registry/recipe/model identities, local candidate seeds, idempotent aliases/requests,
  per-target missing/unsupported state, pinned baseline and no silent reference movement. Pure resolver
  and dry-run fixtures first; no resource authority inferred from a manifest.
  - [x] **AKU-01a — explicit-snapshot enrollment and offline CLI**: immutable typed CPU/GPU targets,
    exact artifact/source identities, alias/obligation union, idempotent requests, finite seed marker,
    pinned explicit/implicit baselines and per-target prerequisite states. ✅ 2026-09-09 — main-reviewed
    `campaign.py` plus `campaign_cli.py`, 52 focused tests. Optional local file verification reports
    failures separately without rewriting pins; every output says `admission_ready: false`.
    `docs/autokernel-unified-campaign.md` contains the tested CLI/schema example. The real production
    registry selector/adapter, enrollment events and service consumer remain required for AKU-01.
  - [x] **AKU-01b — canonical production exporter and local-model seed enrollment consumer**:
    automatic CPU/GPU production roster, pinned source/launch context, alias/obligation union,
    explicit local TargetSpec/artifact seeds and per-target unsupported/missing dispositions.
    ✅ 2026-09-09 — main's **118 research tests** and **128 orchestrator/cross-repository tests** pass.
    Export validates loaded launcher tables against pinned inputs and refuses stale compiled priors;
    it cannot accept an injected stale registry. Explicit `--out` seals create-only/fsynced per-target
    recipe sidecars; stdout export and research resolution remain noncreating. Full/quarter recipes
    have distinct actual byte hashes; true aliases still merge. A sealed recipe cannot erase a source
    unsupported/waiting status, including missing DSO prerequisites. Production dry-resolution v2 keeps
    speech/unknown/unsupported rows visible; v1 ordinary manifests remain supported. Local seed refs
    cannot replace production pins or reuse an opposite-backend production recipe/build. Model launch
    compatibility and current byte verification are separate from declared enrollment; no downloads,
    live registry recompilation, worker launch, enrollment Journal event or grant is added here.
- [ ] **AKU-02 — resolved runtime recipes and no-build arms** (AK-AUTO-06/07): explicit unsets,
  effective environment/dispatch witnesses, option compatibility, same-binary arms and canonical CPU
  adapter; established runtime combinations skip critic calls. Hardware execution follows its gate.
  - [x] **AKU-02a — explicit environment-unset semantics**: inherited treatment is absent in the
    control; immutable unset state roundtrips/hashes; legacy no-unset identities remain unchanged.
    ✅ 2026-09-09 — reviewed `Recipe.explicit_unsets`, real `server_env()` consumer and bidirectional
    readback fixtures; 89 focused tests and 611 loop tests / 59 subtests pass. This does not yet freeze
    the full inherited environment or supply the new CPU runtime-arm adapter.
  - [x] **AKU-02b — frozen launch resolution and CPU serving consumer**: explicit artifact identities,
    allowlisted effective environment and absences, derived backend/speculation capability, frozen
    argv/workload/readback expectations, and the optional real `_measure_once()` consumer.
    ✅ 2026-09-09 — 31 main-run focused tests. Exact snapshot integrity is separate from normalized
    execution identity: relocation/port/recipe label do not change execution, while model/DSO load-name
    content, runtime semantics and environment do. CPU uses explicit `device=none, ngl=0`; zero VRAM
    is not a GPU veto, but placement/contention remain unproven. Multi-device/mixed-draft, overriding
    extension flags and unknown capabilities refuse before launch. Runtime-set/master-off samplers,
    CPU lifecycle witnesses, planned no-build arms and policy consumers remain required. Legacy recipe
    hashes are unchanged; the inherited HSA override is actually removed and floor writes now use the
    hardened JSON publisher. Metric prose now accurately describes the unchanged sum-of-slot-rates.
  - [x] **AKU-02c — canonical CPU/GPU launcher recipe adapter and existing serving conformance**:
    closed explicit canonical recipe schema, full semantic/argv rederivation, NUMA prefix grammar,
    immutable launch environment and exact artifact/source provenance.
    ✅ 2026-09-09 — the AKU-01b acceptance includes the real sealed production export → Campaign CLI →
    canonical recipe → existing `_measure_once()` path with fake CPU/GPU processes. Conflicting flag
    aliases, unknown NUMA policies, rehashed semantic mismatches and credential-bearing environment
    refuse; source/recipe identity cannot substitute for witnessed placement or execution. Production
    command construction defaults are unchanged; its opt-in dry seam only skips runtime-directory
    creation. Actual whole-arm observers, runtime sweeps, worker containment and registered policy
    consumers remain separate required work.
- [ ] **AKU-03 — native journal and recovery** (AK-AUTO-02): current-loop event schemas, phase boundaries,
  integration intent/completion, original provenance and replayed projections. Missing/corrupt/stale
  bundle never silently certifies anchor; interrupted units and schema rollback follow §8.17.
  - [x] **AKU-03a — durable derived JSON publication**: file fsync, atomic replace and directory fsync;
    injected pre/post-rename failures preserve the right artifact and never report durable success.
    ✅ 2026-09-09 — real `status.write_json()` caller hardened; 28 focused tests pass, including
    descriptor cleanup and post-rename durability failure. This alone is not journal recovery.
  - [x] **AKU-03b — journal-backed bundle recovery**: snapshot before projection; replay, explicitly
    labelled legacy import, fail-closed missing/unsupported/corrupt state and ancestry; preserve cadence
    while invalidating stale compounded gain after an external tip change.
    ✅ 2026-09-09 — `LOOP_BUNDLE_SAVED` is operational state, not a claim. v1 imports preserve original
    snapshots and default to `unknown_legacy`; current v2 requires validity and makes old readers refuse
    unsupported state. Journal replay repairs missing/corrupt projections, never invents COR. Tip
    advance retains historical magnitude but disables its threshold authority. Main run and manual
    `serving_gate --tip` consume recovery; dry manual inspection opens only an existing read lock and
    never imports or rewrites. Corrupt history requires restoration, not blind reseeding. Native phase,
    integration/control events and candidate transactions remain AKU-03 work.
  - [x] **AKU-03c — serialized prospective arm-capture consumer**: native
    `PLANNED_SERVING_ARM_CAPTURED` events, current campaign/config/supervisor/worker-result fences,
    byte-verified immutable artifacts, exact-payload retry index and restart/uncertainty handling.
    ✅ 2026-09-09 — actual planned-serving→store→controller→journal→restart→independent Vidya reader
    integration passes; main acceptance **278 tests and 15 subtests**. Both comparison identities,
    process/prompt/request/witness links, selected launch values and aggregate are rederived from
    frozen/native inputs. Closed unsupported/malformed inputs refuse; genuine unsupported-unit and
    continuation carriers remain diagnostic. Scoped same-thread/lifetime callbacks serialize lookup,
    append/fsync and projection under the controller mutex; ambiguous append/index failure poisons
    that incarnation. Historical retries return the original event without recreating current worker
    authority. The real lifecycle owner must supply the trusted result fence; none is inferred from
    JSON, and this slice adds no workers, grants, grading, candidate advancement or scientific clock.
- [ ] **AKU-04 — shared ExperimentPlan and evidence-use validator** (AK-AUTO-06/07): phase/category/
  protocol/use, independent-unit view, immutable stopping plan and applicability checks; A2 discovery
  never becomes a keep/release claim; calibration provenance, replay and n/unit/interval requirements.
  - [x] **AKU-04a — immutable structural plan/unit view and calibration applicability API**: strict
    record-class/phase identity, declared fixed-N membership/pairing/order, complete prompt/terminal/
    witness binding, one immutable admissible view, and offline CLI using the real validator.
    ✅ 2026-09-09 — 72 main-run focused tests. Directly constructed objects and supplied view digests
    are revalidated; zero/incomplete or invalid paired units cannot become a complete result. Observation
    cannot become a claim; discovery cannot bank/release; strict-search cannot headline. A2 nomination
    and claim-bearing uses lack their registered verifier/grader integrations and fail closed. Calibration
    requires declared unit, n≥24/interval, exact registered-estimator replay and a registered applicability
    rule; raw replay and plan applicability have separate caches, and transient callback failures are not
    cached. This is structural validation, not verified independence or a second grading ladder. Actual
    instrument consumers, native phase/unit events, A2 semantic attestation, power/bounded-null handling
    and shared ClaimTuple projection remain required for AKU-04.
  - [x] **AKU-04b — frozen planned-serving launcher consumer**: distinct resolved recipes, exact
    canonical prompt bytes, fixed unit order/membership, retained native observations and one shared
    admissible-unit view. ✅ 2026-09-09 — main's 117 tests and 3 subtests pass, including legacy serving,
    resolved recipe and ExperimentPlan coverage. Missing/nonfinite/boolean timing fields cannot become
    zero measurements; warmup/measurement slot failures are retained, raw observations are sunk before
    provider completion, and witness states are not inferred from references. Failed units stop the
    sequence. Continuation prevalidates an exact completed prefix and prior lineage before any admission.
    The trusted provider must enclose the worker with owned-descendant and stage-plus-teardown bounds;
    these are injected consumer contracts, not a local process-tree enforcement implementation. Native
    journal/ClaimTuple hook, real lifecycle samplers, registered inference protocol and worker/provider
    integration remain required. All resulting use status remains `policy_undefined` in this slice.
  - [x] **AKU-04c — prospective sealed arm producer and shared immutable store**: actual planned
    serving emits raw observations before its sealed arm carrier, binding the complete frozen plan,
    exact request bytes, process membership, worker/source identities, timestamps and canonical unit
    view. ✅ 2026-09-09 — main's integrated capture/candidate/Journal suite passes 382 tests and 15
    subtests. Supported scalar is serving/process/level/median with units `t/s`; independent n counts
    scored process launches. Unknown placement/contention or absent GPU residency remains diagnostic,
    not a widened threshold. Store publication uses owned private paths, nested thread/process exclusion,
    no-overwrite content addressing, fsync and exact-inode crash recovery; noncreating verification
    cannot recreate a lost published dependency. Controller-native journal wiring is the next consumer.
    Loaded evaluator identity, real lifecycle witnesses and registered policy remain required; no
    measurement, historical backfill or execution authority is claimed by fixture success.
  - [x] **AKU-04d — generic fixed-member A2 runtime discovery consumer**: exact same-artifact
    runtime frames produce a sealed three-anchor bank and three candidate-only invocations;
    cached-bank reuse adds no fresh anchors. ✅ 2026-09-09 — main's clean nine-file release passes
    **1,512 tests and 83 subtests**; the final focused observation/screen/plan/serving run passes
    **143 tests and 3 subtests**, with Ruff clean. Full frame identity includes target/prompt,
    estimator/estimand, required witnesses, policy, evaluator, power/frequency, resource claim and
    host epoch. Invalid completed units are durably terminal, never silently rerun; uncertain intent
    requires reconciliation. Serialized replay grants no bank/nomination authority without the exact
    live verifier. Registered nomination permits only the completed candidate-only advisory view;
    keep, validation, release and grading remain unavailable. A3 hides stale-epoch magnitudes and
    refuses mixed current frames. Ordinary load remains recorded noise, not an automatic A2 veto.
    Source `04d73260`, main `d75bc9ec`; actual controller/native phase adapters and shared Vidya
    projection remain active work under AKU-04/08 and VB-AK-UNIFIED-DISCOVERY.
  - [x] **AKU-04e — controller-owned A2 phase persistence and cached-bank replay**: exact
    fixed-plan INTENT/TERMINAL/SEALED records use the native Journal and one startup-built bounded
    index; ambiguous append poisons that lifetime and exact retry preserves original bytes.
    ✅ 2026-09-09 — main's clean composition with published standalone controls passes **1,831
    loop/Journal/storage tests plus 165 subtests**, including the independent cached-bank probe;
    Ruff/diff checks pass. Candidate-only reuse references its original seven anchor event/Journal
    identities and sealed bank, adds no synthetic anchors, and reopens after restart. Foreign,
    missing, forged or stale-frame sources refuse. Fourteen actual phase events and at most one
    separate bank reference remain the bound. Source `6b5d5fda`, main `c36411a7`; no actual native
    invocation, semantic grading or real comparison is established by this persistence slice.
  - [ ] **AKU-04f — native per-unit A2 execution and first-issue reservation**: select one
    digest-covered contiguous unit range from the unchanged full ExperimentPlan; parent validation
    rederives membership. Bind each launch to its fsynced unit INTENT and an opaque current-owner
    first-issue permit. Replayed unknown is not absence proof; terminal recovery and durable
    not-acquired retries must preserve exact identity. No hidden three-unit launch or one-unit
    plan rehash. Coordinate this bridge with AKU-07i's actual observation/lifecycle owner.
    Native durable event/permit semantics require OP-AKU-A2 approval: the transition validator
    has HIGH17 upstream impact, including Journal validation and replay. Changing its helper
    language is the same authority change, not an exemption. Independent selected-range
    transport may proceed but cannot enable discovery or complete this task by itself.
  - [x] **AKU-04i — transport one original native plan unit through the owned worker**:
    ✅ 2026-09-09. Additive Prepared v4 and result/run/artifact v3 bind the unchanged full
    native-v2 plan, exact absolute unit range and attempt lineage. Both parent and child refuse
    unselected units; direct multi-unit admission is rejected. Reopening rederives original
    unit/process/arm/prompt/order and full-plan completeness; operational range completion
    cannot imply scientific completion. Exact loaded source/default pins reject non-Python
    callable substitution. Main independently passed **46 tests including explicit factory
    startup**; worker composition passed **238 tests, one existing strict HELD xfail, no skips**.
    All eight primary file hashes match final packet
    `fb5cb9e3ba5bdd7e10c6eeaca721e4778b6949e5c1ab7e8bf62e65968f48c495`.
    Real child/receipt/restart tests use labelled synthetic measurements/provider/procfs;
    missing witnesses remain unknown and captures diagnostic. This adds no A2 event/permit,
    scheduler discovery kind or standalone activation; AKU-04f remains open under OP-AKU-A2.
    Contract: research `docs/autokernel-selected-unit-transport.md`.
  - [x] **AKU-04j — refuse discovery misrouting through ordinary comparisons**:
    ✅ 2026-09-09. Inline pinned driver guards exclude canonical discovery phase, record class
    or A2 protocol declarations before catalog issuance, retaining other eligible work and one
    precise unavailable reason. Historical misclassified intents remain readable but refuse
    materialization before binding or worker acquisition. No new discovery permit/event or
    activation is supplied. Main final **18 tests passed**; worker compatibility **122 passed,
    one existing strict HELD xfailed, no skips**. Exact two-file packet
    `9abb2115347b8d4af796bc6157c6845addc3aafab4544c9fc9e27cfe6ecc2c21` matches primary.
    Prior published transport main `0114da9b` independently passed the complete loop/Journal
    suite: **2,490 passed, two strict xfailed, 83 subtests, no skips in 309.68s**.
    That full run predates this guard; final guard coverage is the focused/compatibility scope.
  - [x] **AKU-04h — align native startup fixture with prospective sample admission**:
    ✅ 2026-09-09. The full published suite exposed one fixture declaring 64 samples for
    32 seconds at 10ms cadence (requires 3,209). The test now derives its count before
    sealing instrument identity and asserts exact prepared-plan admission. Timing, cadence,
    gap, byte limits and production admission are unchanged; main's 80 adjacent tests pass.
    Repaired research main `b9cc11af` then passed the full loop/Journal suite: **2,436 passed,
    two strict expected failures, 83 subtests**, no skips (299.83s). Expected failures remain
    OP-AKU-BIND and OP-AKU-HELD, not successful native resource binding or interrupted recovery.
  - [x] **AKU-04g — installed raw serving-calibration preparation**: ✅ 2026-09-09.
    Startup v4 prospectively derives bounded A/A and neutral-copy process pairs and retries;
    the actual driver/controller/native worker collects immutable original chunks. Only exact
    durable settlements admit chunks to the existing numeric solver; fresh settled restart
    preserves identities and accounting. Neutral physical snapshots stay retained without fake
    runtime dimensions. Main independently passed 144 tests with one strict held-recovery xfail;
    the prior-base full suite passed 2,398 with two strict xfails and 83 subtests. Research source
    `097c5be8`, main `ebb5e9fa`. Fixture providers and observations are explicit, not hardware proof.
    All solves remain diagnostic/unqualified: original qualified controls/window and phase/cell
    scope are still required. OP-AKU-BIND and OP-AKU-HELD remain open; interrupted pre-settlement
    restart refuses rather than recollecting. This does not complete AKU-04 or AKU-12a/b.
- [ ] **AKU-05 — candidate manifests and validation batches** (AK-AUTO-01/10): actual measured versus
  delivery identity, one integration tip and validated pointer, required production rows, frozen batches,
  identifiable LOO, four-keep cadence/debt and cross-repository intent recovery. No frozen-tree writes.
  - [x] **AKU-05a — private-index accepted source commits**: the real `archive.keep()` consumer commits
    only accepted literal paths from captured HEAD, preserves peer index bytes, honors commit hooks and
    advances the selected ref with expected-parent CAS. ✅ 2026-09-09 — 83 main-run adjacent tests and
    7 subtests pass, including 26 focused private-index cases. Wrong repository/branch, path expansion,
    hook-added peer staging and concurrent ref advance refuse; notification failure after a landed
    commit does not report a nonexistent commit failure. HEAD binding is rechecked immediately before
    ref CAS, not claimed as an atomic branch-binding transaction; the owning integration lock remains
    necessary. This supplies source safety, not a measured candidate or cross-repository transaction.
  - [x] **AKU-05b — immutable candidate/validation contract and offline CLI**: explicit Git object
    format, one source set with per-target exact CPU/HIP build selection, candidate/control recipe and
    workload identities, declared keep deltas, separate integration/validated pointers and frozen rows.
    ✅ 2026-09-09 — main reviewed 28 focused tests within 159 passing adjacent tests. Required production
    target/backend obligations and complete keep-set LOO are checked at batch start and advancement;
    loaded state cannot bypass them. Trusted bound row/LOO verifiers are mandatory, and callback errors
    refuse. Completing an older gate preserves newer keeps and monotonic gain-trigger generations;
    cadence reset does not clear validation debt. Exact start retries are idempotent, conflicting batch
    payloads refuse, and optional seed rows may remain pending without being counted as passed or blocking
    required-row completion. Output-correctness equivalence does not grant timing. The offline CLI always
    denies execution/promotion authority. Actual registered verifiers, durable candidate transactions,
    native validation events and retention consumers remain required; this is not a measured candidate.
  - [x] **AKU-05c — durable candidate transactions and recovery consumer**: native journaled
    INTENT → PREPARED → COMMITTED phases, immutable manifest objects, owned experimental refs, exact
    idempotence and expected-state CAS. ✅ 2026-09-09 — main's 382-test integration includes six
    adversarial candidate/cache probes. Old-request retries return the original result without replacing
    the newest projection. Controller capabilities are lifetime/thread fenced; retained public views
    cannot mutate authoritative state. Startup rebuilds indexes once; ordinary operations use bounded
    cached state and the requested transaction, not whole-history Git/JSON replay. Source preparation
    across repositories is recoverable, not atomic. All three frozen kernel paths and both production
    branch families refuse. Historical validated state restores provenance without restoring verifier
    authority; new validation still requires registered live callbacks. Offline CLI has no execution or
    promotion authority. Retention, registered row/LOO verifiers and live validation remain required.
  - [x] **AKU-05d — shared frozen-kernel mutation guard in legacy and candidate paths**:
    canonical llama/speech worktrees and both protected branch families refuse before mutation;
    archive rechecks root/branch binding before its ref CAS, and candidate refs reuse the same guard.
    ✅ 2026-09-09 — main's combined guard/transport acceptance passed **198 tests and 4 subtests**.
    Symlink aliases and detached canonical roots refuse; experimental linked worktrees sharing the
    production object database remain allowed. Existing private-index, hook and peer-staging behavior
    is preserved. Tests use temporary repositories only; no production tree or ref was changed.
  - [x] **AKU-05e — native validation consumer and replayable exact batch wiring**: due state
    freezes candidate/comparator/required rows and cadence generations; every submission rejoins
    the current transaction projection before artifact I/O. Both native arms require one frozen
    plan/lineage/comparison and exact executable plus full loader-name/content DSO closure.
    ✅ 2026-09-09 — main's independent clean three-file release passes **246 adjacent/edge tests**
    and **1,762 loop/Journal/storage tests plus 165 subtests**, with Ruff clean. The sealed row
    binds batch, row, both manifests and row-set identities; reopen verifies original carrier/raw
    artifacts, calibration, complete-measurement status and structural eligibility without history
    scans. CPU success cannot satisfy a required GPU row; optional seed debt stays separate.
    Source `1ac8393e`, main `deab8f40`. V1's loaded-instrument identity remains unknown for real
    validation authority; fixture-only transaction tests do not certify a candidate. The assigned
    semantic consumer must connect native-v2 instrument evidence, canonical ClaimTuple grading,
    the owning production-validation objective and exact row/LOO verification. No inference,
    production mutation, new grading rule or promotion authority is added by this slice.
- [ ] **AKU-06 — bounded scheduler and mechanism routes** (AK-AUTO-07/09): pure accounting/coverage model,
  bounded seed boost/opportunity, reservations and rejection audits; directed transfer and noncomposable
  coexistence evidence. Live admission/coexistence waits for AKU-11, not a fake-provider pass.
  - [x] **AKU-06a — indexed scheduler/accounting and resolved-campaign inspection consumer**:
    frozen coverage rounds, finite FIFO seed boost, required reservations, held-resource charging,
    exact issued-selection/receipt/outcome binding and explicit unavailable-frontier debt.
    ✅ 2026-09-09 — main's **138 tests** pass, including nine independent regression probes.
    Full resolved-campaign identity and grouped workload aliases prevent stale-state/seed-budget reuse;
    non-ready targets require separately typed prerequisite work. Unused optional slots and unavailable
    frontiers cannot indefinitely stall ready production work. Full-region reservations skip only
    unreserved backfill, preserving earlier required seed/other slots. Actual physical-region, GPU
    host, device and memory held time is charged; overruns retain cost and fence successors. Startup
    builds receipt/seed indices once; hot-path updates avoid historical scans. V1 explicitly uses fixed
    weights and no compatibility authority. CLI selections grant no execution. Journal transitions,
    native provider receipts, registered adaptation, planner/routes and live admission remain required.
  - [x] **AKU-06b — mechanism-scoped planner and prepared runtime-recipe consumer**: production
    CPU/GPU profiles, exact scoped evidence, runtime dimensions and persistent scheduler selection
    bind a prospective dispatch intent to the actual target, proposal, claim key and final plan.
    ✅ 2026-09-09 — main's **228 tests** pass across planner, scheduling, evidence, enrollment, recipes
    and plans. Each unique export/policy is validated once when preparing immutable anchors; repeated
    planning performs no export/filesystem reads. Anchors bind the complete resolved campaign, not
    only its requested manifest. Thread/placement/NUMA/batch/ubatch and allowlisted environment
    set/unset arms retain exact model/executable/DSO provenance and rederive canonical launch semantics.
    Runtime dispatch requires a matching complete ExperimentPlan; source/build proposals remain typed
    final-plan preparation, never permission from a claimed plan hash. Mandatory conflicts survive
    prompt truncation; Q4_K findings do not rank Q8_0 work and cross-epoch values do not rank fresh work.
    Stops do not consume undispatched scheduler slots. This is a nonexecuting planner boundary;
    standalone driver, preselected actor preparation, local-seed runtime/profile adapter, native intent
    persistence and worker/receipt/evidence integration remain required. Source `26171408`, main
    `1e5b766a`; the AKU-06 parent remains open.
  - [x] **AKU-06c — durable controller-owned unified driver and compact accounting projection**:
    native fsynced issuance/settlement, exact catalog/selection/arm binding, idempotent replay and
    immutable runtime materialization feed the actual campaign controller. ✅ 2026-09-09
    Accepted together with AKU-07c: the clean 17-file release passed **1,444 tests and 83 subtests**,
    plus **20 independent boundary probes**. Preview failures preserve committed receipts and seed
    queues; old intents cannot rematerialize under a new supervisor. Slow provider/verifier I/O runs
    outside the controller mutex and rechecks lifetime. Operational projections use indexed totals
    and a rolling seed commitment, not per-tick historical scans. V3 START fences actual old readers;
    the closed snapshot connects scheduler/targets and reports other consumers as not connected.
    Source `61a63c42`, main `8cbcce9f`. One outstanding selection and a management-only default do not
    constitute concurrent CPU/GPU execution. The end-to-end execution/receipt consumer, prepared
    actors, native evidence feedback and real authority remain required under AKU-06/07/08.
  - [ ] **AKU-06d — connect actual selected actor/profile preparation**: finish the real
    UnifiedCampaignDriver-issued sequence using the actor/profile owner published in AKU-06f,
    public producer registration/reservation, contained fixture execution, exact held cost/stdout,
    native finish/profile publication and restart. Replace private projection/receipt seeding in
    acceptance tests; independently test durable budget drift with a valid current producer receipt.
    Connect proposed advice to the existing private source/build preparation consumer, not dispatch
    or publication authority. Require selected-work admission before profiler execution and bind
    profile publication to the registered producer, exact current terminal, held receipt and
    controller-authenticated stdout; schema-valid caller events are not verified profiles.
    Nonzero/malformed profile output still settles spent cost without PROFILE_VERIFIED. The actual
    driver E2E currently refuses mismatched provider proposal/backend/class (AKU-07k); a permissive
    settlement-validator lambda or private receipt seeding cannot satisfy acceptance.
    Source/build input consumption is published as AKU-06g, not a complete authoring pipeline.
    Finish separately contained patch authoring with a fresh attempt/reservation, immutable source
    context and owner-assigned scope; authenticated bounded output constructs the native manifest.
    Persist advice → authored patch → source commit → real build identity through native ownership,
    then refresh planner prerequisites from verified results. Never reuse a finished advice grant,
    invent patch bytes from prose or treat a forwarded build-runner return as verified build identity.
  - [x] **AKU-06e — public exact selected-profile materialization**: immutable SelectedProfileWork
    and UnifiedCampaignDriver.materialize_profile bind catalog, transition, selected proposal,
    profile request, preparation-plan digest and current controller identity through the public
    controller callback. ✅ 2026-09-09 — source `c3303474`, main `1accc7f2`; main reproduced
    24 focused tests and **1,834 tests plus 165 subtests** in the clean combined acceptance tree.
    The record is deeply immutable advice with execution_authorized=False, not a grant or launch
    capability. Actor execution, provider metadata and source/build consumption remain AKU-06d/07k.
    The same checkpoint makes the disk-floor boundary test deterministic without changing storage
    policy: fixed 4 GiB free is OK at equality and pressured below a 5 GiB floor.
  - [x] **AKU-06f — contained actor/profile producer and durable preparation state**:
    public controller reservation, exact owned terminal/cost/stdout joins, native
    INTENT/FINISH/PROFILE_VERIFIED replay and independent preparation budgets are implemented.
    Cancellation atomically precedes provider admission or refuses; exact owner-local tombstones
    prevent later admission without pretending to be durable restart authority. Executable reads
    are bounded/nonblocking, configuration limits finite, and profile receipts deeply immutable
    with detached canonical serialization. ✅ 2026-09-09 — research source `a9ce9d88`, main
    `da7dd5bc`; main reproduced **1,839 passed, one strict xfailed, 83 subtests passed**.
    The strict failure is still the real selected-profile scheduler accounting mismatch (AKU-07k),
    not waived acceptance. Proposed advice to private source/build preparation remains AKU-06d;
    prospective measured-profile projection remains VB-AK-UNIFIED-PROFILE. No live actors,
    inference, builds, provider grants or full campaign acceptance are claimed.
  - [x] **AKU-06g — bind selected advice to guarded source/build preparation**: public immutable
    SelectedActorWork and materialize_actor re-open the exact issued catalog/selection; consuming
    adapters revalidate that actual request before using immutable authored manifests or explicit
    BuildPlans. Guarded private source application yields actual commit/tree/diff-policy evidence;
    build delegation preserves the owning runner's arguments/results and enforces configured
    affinity/jobs/deadlines without creating a grant. ✅ 2026-09-09 — research `de4396ca`, main
    `ba0644e7`; main combined gate **2,061 passed, one strict xfailed, 83 subtests in 47.29s**,
    Ruff and diff checks clean. Tests apply/commit only a disposable tiny source fixture; no CMake
    or inference. Actual contained authoring, build ownership and planner feedback remain AKU-06d.
    Prospective source-policy findings are registered under VB-AK-UNIFIED-PREPARATION before live use.
  - [x] **AKU-06h — connect installed profile preparation to settled planner feedback**:
    exact typed mechanism bindings now select the owned profiling child; original authenticated
    PROFILE_VERIFIED publication joins original issuance, receipt and successful prerequisite
    settlement before planner feedback. Same-boot replay preserves original validity without
    restoring live held authority or appending reconstructed evidence. Malformed output closes
    the original reservation and retains incurred cost. Exact source/default closure and complete
    retry identities refuse substitution. ✅ 2026-09-09 — final nine-file packet SHA-256
    `623cbf63587b772747ef9e45cb9e75bf43c94cb79afdf5dc6f4b6ccf30577792`;
    independent combined acceptance **85 passed, two existing strict xfailed**, no skips;
    exact primary application hashes match and focused rerun **37 passed in 3.46s**.
    Successful settlement tests use an explicitly synthetic provider authoring correct original
    metadata; native BIND/HELD refusals remain. No hardware or scientific qualification claimed.
    Contract: research `docs/autokernel-installed-profile-preparation.md`. Published source
    `54eb195d`, main `81b87368`; final main full loop/Journal acceptance: **2,473 passed,
    two strict xfailed, 83 subtests, no skips in 298.45s**. The expected failures are still
    OP-AKU-BIND and OP-AKU-HELD; this is software acceptance, not hardware qualification.
  - [ ] **AKU-06i — automatically renew installed profiles with bounded request generations**:
    derive requests before selection from the installed template, exact settled predecessor and
    campaign attempt cap; durably reuse the original selected request on restart. Preserve original
    validity, cost accounting and fairness across targets. Test older-profile/new-failed-attempt
    attribution together, expiry/restart and exhausted budget. The current connector reports
    per-target `profile_refresh_unavailable:original_request_consumed:fresh_predeclared_request_required`
    while allowing unrelated eligible work; this safe fixed-request limitation is not completed
    autonomous refresh and must not become a recurring operator request. Existing actor projection
    refuses a second distinct PROFILE_VERIFIED for the same target, so generating fresh request IDs
    alone is insufficient. Explicit versioned successor/predecessor semantics require shared
    `actor_preparation_state.validate_event` changes (HIGH16, Journal publication/replay);
    OP-AKU-REFRESH approval was requested. Do not conceal new authority in a nested v1 contract.
  - [x] **AKU-06q — project original CPU profile evidence through the durable feed**:
    ✅ 2026-09-09. ROOT closure-v3 registers measurement and receipt-integrity projections;
    original accepted terminal and PROFILE_VERIFIED join precedes compact artifact verification.
    Pair projection/associations persist before ACK; restart and capacity-one retraction retain
    both carriers. Failed settlement and consumed quarantined/conflicting profiles release only
    their exact terminal, while forged joins cannot discard pending evidence. Unsampled pinned
    TIDs are valid without invented samples. Main combined current-tree acceptance:89 research
    tests in24.94s and65 ROOT adapter/dashboard tests in3.21s, no skips. Existing dashboard cache
    hooks survive composition. No new grading rule, production-validation claim or hardware run.
  - [x] **AKU-06r — correct feed integration regressions without narrowing coverage**:
    ✅ 2026-09-09. Restore original operational diagnostics for unrelated lifecycle/settlement
    events; profile-specific bookkeeping no longer silently consumes their classification.
    Real service test signals only after its publisher observes evidence. Explicit v2/v3 feed
    fixtures use independent source cursors and preserve all native-final/restart assertions;
    scientific-receipt fixtures pin their separately owned seven-file v2 contract.
    Main110 affected integration tests passed in118.63s, no skips; all four applied file hashes
    match the tested tree, Ruff clean. The preceding full run had5 failures and15 setup errors
    (2583 passed,2 strict xfails,83 subtests); a fresh full-suite result is still required.
  - [ ] **AKU-06j — install the concrete owned CPU profiling producer for GLM discovery**:
    Concrete full-request producer is implemented and tested under AKU-06o below; this task
    remains open for exact GLM prompt/configuration and
    real deployment conformance. Do not relabel independent full-request v1 as cached decode.
    emit existing target_profile_output.v1 through the installed ProfileMechanism, retaining
    bounded original perf-script/counter/request-window artifacts and source/tool/model/recipe
    identities. Reuse the preliminary GLM capture semantics, not its independent launcher/lock;
    server and profiler must be owned descendants. Use supported perf-script per-TID/period
    parsing (the historical helper's perf report -F tid was invalid). Historical token prompts,
    seed42 and returned-token handling do not bypass OP-AKU-PROMPT. CPU samples are not wall-time
    share, recoverable spin time, bandwidth saturation or measured gains. Add real configuration
    and registered write-side projection; test offline without presenting fixture profiles as
    fresh hardware evidence. Existing GPU/C4 profilers remain separate selected mechanisms.
  - [x] **AKU-06p — retain exact expected GLM shard inventory without unscheduled model reads**:
    ✅ 2026-09-09. ROOT `artifacts/autokernel/glm53-expected-inventory-20260909/` contains
    the existing model_identity.v1 expected manifest, six original download metadata files,
    lossless encoded source tree, expected-only provenance, task-local author and tests.
    Manifest SHA256 `a9984ae6a18f7b25dd27086abd32b74056264a9cc64ba074067e8a8bb90be626`;
    normalized expected inventory `21d760be3bd473865b31f3b3d9ca28b30a2f7bd12b71660e64191ff02ff11fcc`.
    Main relocated tests:31 passed, no skips. Local model bytes were not read or verified;
    actual six-shard verification remains resource-accounted preparation under AKU-06j/12.
    Preserve explicit prospective GLM microbatch512 (pinned kernel default), not the projection's
    omitted-value2048; omitted -ub currently refuses final resolution. Original token/cache/MTP
    prompt and explicit logging/UI/speculation flags still require their owning recipe work.
  - [x] **AKU-06o — implement and verify owned full-request CPU profile capture**:
    ✅ 2026-09-09. Research `cpu_profile.py`, installed benchmark entry and the optional
    concrete serving hook retain original request/model/source/process/DSO identities,
    bounded sample/counter artifacts, warmup/request windows and deterministic raw replay.
    Reader-only waitid proof fixes exited-child readback races without invented argv/exe.
    Exact six-file packet SHA256 `8fc48b84bf78cc41567239b714cd6b9cc4b84dd8a54f98c49ff70d7e3db0731c`;
    main composed acceptance: 205 passed, 14 subtests, 36.22s, no skips. Tiny HTTP/perf fixtures
    cover installed publication/settlement/planner/restart, bounded failures and cleanup.
    Full published research3762a517 acceptance: 2577 passed, 2 strict expected BIND/HELD
    failures, 83 subtests, 332.81s, no skips (original handle20212, terminal0).
    No real perf events, GLM run or production change. Contract: research
    `docs/autokernel-owned-cpu-profile.md`. Sampled periods are attribution, not gains;
    receipt integrity is not production validation. AKU-06j and all parent tasks remain open.
  - [x] **AKU-06k — connect actual actor preparation to owned native build enrollment**:
    ✅ 2026-09-09. Concrete SourceBuildExecutionOwner consumes the real ActorPreparationConsumer,
    binds exact selected advice/source/BuildPlan, executes the controller-owned build and reopens
    original stdout/log/process/source/binary evidence before immutable enrollment. The candidate
    path requires the original identity-keyed materialized-source capability; copies, parsed bytes,
    foreign owners and changed source refuse. Startup now accepts actual build_recipe identity while
    retaining legacy build without relabelling. Explicit log limits bound parent verification;
    Python safe-path launch prevents candidate-cwd package shadowing before verification.
    Exact eight-file packet `1f55a3b42cb126870f42e1043a9d60aefa920056776e19d417fb5904a574cb5b`;
    all primary hashes match. Main current-base **60 tests passed in 4.57s**; worker **62 passed
    in 5.32s**, prior source/profile/actor/startup composition129 passed. Genuine profile settlement,
    selected build advice, two actor children, actual tiny CMake build and verified enrollment pass,
    including a committed malicious shadow package. No kernel/hardware or production build.
    Contract: research `docs/autokernel-source-build-execution.md`. This does not settle the selected
    scheduler transition, install standalone source/build dispatch, or activate expiry authority.
  - [x] **AKU-06m — full software regression checkpoint after owned build integration**:
    ✅ 2026-09-09. Published research `1f38aefb122b73bd6001ba2b54ea11d66546fa3d`,
    main terminal run: **2,513 passed, two strict expected failures, 83 subtests passed**
    in307.84s, no skips. Scope is the entire loop test directory plus test_journal.py,
    using the exact primary factory tree and ROOT checkout. Expected BIND/HELD failures
    remain explicit. This does not validate subsequent worker edits, real-host export,
    hardware measurements, five-loop GLM acceptance or production promotion.
  - [ ] **AKU-06l — install source/build dispatch and original outcome settlement**:
    implement the [proposed multi-child accounting contract](../../docs/design/autokernel-source-build-accounting-v2-proposal.md)
    only after the existing BIND/HELD high-impact approvals. Original child receipts remain separate;
    terminal no-launch cancellation is explicit, not a synthetic zero-cost receipt. Preserve
    exactly-once attempt accounting, ordered admission retries and every durable crash boundary.
    Connect the published owner to startup/standalone work-kind dispatch; retain exact selected
    request, original actor/build terminal and held-cost references through retries/restart.
    Complete owning scheduler settlement and candidate feedback without synthesizing composite
    receipts or treating enrollment as execution completion. Bind actual source authoring output
    to its original guarded manifest before build; no caller-authored mapping becomes authority.
    Preserve OP-AKU-BIND/HELD and ENROLL approval boundaries and existing native refusals. Prove
    actual startup→profile→actor/source/build→settlement through the same installed entrypoint.
  - [x] **AKU-06n — specify original multi-child accounting and denial recovery**:
    ✅ 2026-09-09. Reviewed current scheduler/lifecycle/actor APIs and retained the implementation
    decision package linked in AKU-06l. It delineates original held-proof/child/settlement append
    order, empty and charged-prefix admission denials, atomic one-attempt settlement, legitimate
    partition concurrency, cross-role receipt refusal and occupancy versus elapsed-time budgets.
    This closes the design audit only; Journal/provider/scheduler changes are not implemented or
    approved, and AKU-06l plus all parent tasks remain open.
- [ ] **AKU-07 — standalone campaign lifecycle** (AK-AUTO-11): fenced single writer, durable controls,
  launch intent before spawn, owned-child reconciliation, exact resume membership and expiry handling;
  test worker/provider faults hermetically before attaching real compute.
  - [x] **AKU-07a — durable management-only campaign controller and service**: full resolved-config
    identity, lifetime store/named-lock ownership, native fsynced START/control events, strict replay,
    monotonic incarnation/stream/revision and idempotent pause/resume/drain acknowledgments.
    ✅ 2026-09-09 — main's 217 focused/adjacent tests and 15 subtests pass, plus a 256-case malformed
    native-event mutation sweep. Closed/replaced/uncertain writers refuse; accepted-but-unpublished
    commands recover from the journal. The authenticated loopback service owns initial/periodic full
    snapshot publication independent of dashboard traffic; health ticks advance no scientific cursor.
    Slow-client shutdown closes owned sockets and shares one join deadline. Arbitrary blocked filesystem
    I/O remains unbounded: shutdown refuses and retains ownership instead of claiming a clean handoff.
    Loaded producer identity describes only its enumerated bytecode/constants, not the whole package.
    Dry CLI does not write; management mode grants no compute and launches no workers. Exact trusted
    grant-consumer checks create no grants. Real launch intent/container recovery, worker/protocol/broker
    integration and deployment remain required; management-v1 dashboard integration is now AKU-09c.
    AKU-07/09 are not complete.
  - [x] **AKU-07b — owned-worker lifecycle and crash-safe v2 control consumer**: prospective durable
    acquisition and launch intent, exact grant/container/PID-start/boot identities, isolated pipe-gated
    bootstrap, bounded stage/teardown lifecycle and accepted-versus-completed pause/drain controls.
    ✅ 2026-09-09 — main's **307 tests and 15 subtests** pass, including independent descriptor-leak,
    credential/import-isolation, old-terminal fencing, command-semantic and actual-old-reader probes.
    Typed denial proves no acquisition; ambiguous provider I/O retains pending ownership for exact
    recovery. Returned journal errors do not disable owned cleanup, but uncertain durability cannot
    certify a terminal result. Pause can escalate to drain without a late superseded completion
    overwriting current control. Indexed replay accepts denied/no-launch generation gaps while
    refusing rollback; the v2 START fence makes the actual older reader refuse before admission.
    Snapshot v2 is explicit and management-v1 defaults remain. Provider calls must themselves enforce
    deadlines: a numerical deadline or fake cgroup test is not live containment proof. The generic
    parent-side planned-serving guard still refuses until the contained-child bridge is connected.
    Driver/native-result integration, real authority and deployment remain required for AKU-07.
  - [x] **AKU-07c — contained planned-worker bridge and parent-verified native result boundary**:
    fixed bounded child IPC, actual PID-start/boot/container HELLO before payload, isolated bootstrap,
    immutable deferred capture and all-captures-first parent validation. ✅ 2026-09-09
    Main independently accepted the same clean 17-file release as AKU-06c; final focused checks
    passed **42 tests** and Ruff. Parent evidence requests remain bounded after notice draining;
    arbitrary callbacks cannot run inside the watchdog. Default Linux containment verifies cgroup2
    mount/device/membership; an ordinary directory is not containment. Terminal result fencing follows
    durable native acceptance, and exact owned provider-held receipts retain all cost, including a
    late return that makes the scientific result stale. Provider I/O must enforce its own deadlines.
    Tiny owned fork/IPC fixtures and real-bootstrap containment refusal are separate tests, not live
    grants. Source `61a63c42`, main `8cbcce9f`. Driver-to-bridge execution/settlement, observer authority,
    versioned native attachment and real OP-41 provider/deployment remain required for AKU-07.
  - [x] **AKU-07d — bounded whole-lifecycle observation producer and serving hooks**: setup/load,
    placement, health, warmup, measurement and teardown markers enclose each serving unit, with
    bounded process census, NUMA/affinity/memory/PSI, prepared DSO and explicit target-GPU evidence.
    ✅ 2026-09-09 — accepted in the same clean release as AKU-04d. Six independent main probes
    cover loaded code/bound state and shutdown/cost edge cases. Loaded identities include constants,
    nested code and explicit instance state; unsupported native payload remains unproven. In-window
    DSO metadata and actual PID-start/boot/container attribution refuse replacement/reuse. Missing
    trusted foreign/runtime/GPU verifiers stay unknown; no name-based inference classifier or grader
    is introduced. Cleanup runs on every serving exception. Unjoined readers freeze unknown evidence,
    retain all incurred reader cost even for dropped samples, and fence successor units; late return
    cannot mutate the record. Source `04d73260`, main `d75bc9ec`. Native versioned attachment and
    containing-owner successor enforcement remain assigned AKU-04/07/08 integration work; no live
    observation, real grant, containment success or deployment is claimed by hermetic tests.
  - [x] **AKU-07e — actual controller-owned runtime execution and exact held-cost settlement**:
    one durable driver selection now traverses the real controller admission/acquisition/lifecycle
    path, contained planned-worker result ingestion and scheduler settlement. ✅ 2026-09-09
    Main's clean six-file release passed **1,729 loop/Journal/storage tests plus 165 subtests** and
    **136 focused/adjacent tests**, including an independent shutdown reproducer. No separate
    injected lifecycle can bypass controller ownership. Exact current-owner denial/pre-engine
    refusal is positive no-acquisition proof; unseen, old-incarnation or ambiguous state is not.
    Failed work retains provider-authored cost and settles once. A successful child followed by
    producer failure retains its immutable terminal/result diagnostically without native scientific
    acceptance; an unjoined producer fences successors, retains its handle, and makes close retryable
    rather than claiming teardown. Concurrent execution/close and exact lost-reply retries are
    covered. Source `59eb3f30`, main `6f869803`. The default parent evidence evaluator remains unknown,
    so this connector cannot produce a valid comparison. Observation-v2, A2 native invocation,
    actor/profile/semantic consumers, standalone composition and real provider acceptance remain
    assigned work. No live inference, service, resource grant or frozen kernel was changed.
  - [x] **AKU-07f — controller-owned authenticated bounded worker output**: exact current
    request/plan/lineage/stage/worker/generation/result binding exposes bytes, never a path or
    runtime handle. Terminal-time file identity and bootstrap-recorded length/SHA-256 bind the
    output; truncation, replacement, same-inode tampering, missing/nonregular files and lock
    contention refuse. ✅ 2026-09-09 — main's clean release passes **126 focused/adjacent tests**
    and **1,768 loop/Journal/storage tests plus 165 subtests**, with Ruff clean. Reads and hashing
    run outside the controller mutex, followed by an exact owner recheck. Optional output-capture
    failure preserves the durable terminal and provider-held accounting. Source `47ce0677`, main
    `6fc75192`. This supplies the actor's output consumer, not authority to apply its advice;
    native actor/profile persistence and actual execution remain assigned under AKU-06/07.
  - [x] **AKU-07g — authenticated standalone controls and durable shutdown**: closed command-v2
    semantics and command-transition-v3 replay bind the full campaign/config/supervisor/request/
    revision identity. SIGTERM reuses or records one durable drain, fences resume, and retains
    ownership until actual cleanup. ✅ 2026-09-09 — main reproduced **331 tests plus 15 subtests**
    and **1,810 loop/Journal/storage tests plus 165 subtests** in a clean composed checkout.
    The independent restarted-service probe exposed and corrected a client-side retry refusal:
    control submission preserves historical command bytes while allowing a newer authenticated
    supervisor to consult its journal; absent old commands still refuse and status pins remain
    exact. Typed v3 HTTP loopback, bounded transport/token handling and prior shutdown regressions
    pass. Source `29b8120b`, main `1fea54a5`. The template is deliberately not installed or enabled;
    runtime/service composition and actual provider/live acceptance are not completed by this slice.
  - [ ] **AKU-07h — finish standalone run-level recovery and service composition**: automatically
    retry the retained exact transaction/execution after transient authority or reply loss with
    bounded backoff; preserve unresolved ownership, stop responsiveness and no duplicate child.
    Connect the service-owned run thread and typed process-restart reconstruction of unsettled
    work. Source composition is accepted under AKU-07p; finish installed provider bindings,
    durable held-cost restart settlement (07j), all selected work-kind dispatch and native-v2
    scientific adapter configuration. A source-level runtime_factory is not standalone acceptance.
  - [x] **AKU-07p — compose bounded runtime, startup parser and service ownership**:
    exact issued-intent recovery, bounded same-outcome retry, one service-owned non-daemon run
    thread, recovery before listener admission and owned shutdown are connected. Closed startup
    manifests materialize existing typed inputs and resolve application-owned provider identifiers;
    unified CLI dry-run opens no store or claims. ✅ 2026-09-09 — main combined suite:
    **2,024 passed, one strict accounting xfailed, 83 subtests passed in 45.26s**; Ruff clean.
    Research source `38b29326`, main `2c7762dc`.
    Fixed the planning/drain race with a typed admission-closed refusal and indexed historical
    logical attempts without scanning or reusing old-incarnation denial proofs. Fixture CPU/GPU
    paths are not real provider acceptance. Runtime currently executes runtime_comparison only;
    actor/profile dispatch, continuous feed and production scientific witnesses remain open.
  - [x] **AKU-07i — native-v2 actual-descendant binding and replay**: published the narrowly
    approved lifecycle event/validator with legacy refusal, current-owner capture, immutable v2
    artifact references and restart/acquisition closure. ✅ 2026-09-09
    Every ancestry stat row checks PID/start identity; target, ancestor, ancestry, container and
    membership are rechecked before append outside the controller/watchdog lock. Expired, reused
    or reparented identities cannot publish. Loaded-builtin reads are bounded/stability checked.
    All nineteen final file hashes matched; main's final suite passed 1,905 tests plus 165 subtests
    and four independent PID/expiry/actual-ROOT-projector probes. Research source 3df1192b,
    main a3b251bc. Diagnostic refusal and fixture-scored child/v2/restart modes remain separate.
    Synthetic telemetry proves consumer wiring only; real test-owned cgroup membership/cleanup
    proves neither controller enforcement nor exclusivity. Production parent witnesses/runtime/GPU
    adapters remain AKU-07m, resource authority AKU-11, and live acceptance AKU-12. The operator's
    specific HIGH-impact approval does not cover held-cost/accounting events or frozen kernels.
  - [ ] **AKU-07j — persist provider-held cost for process-restart settlement**: add the exact
    versioned held-receipt lifecycle record after OWNED_TERMINAL and validated provider close,
    before WORKER_RESULT_ACCEPTED/STALE. Restore separate accounting-only indexes and bind lookup
    to the original unsettled driver selection. Handle crash after held append but before final
    result with deterministic stale accounting, one durable stale event and one settlement, no
    provider reacquisition/duplicate child/current measurement acceptance. The additional HIGH
    validator event (22 upstream, three processes) awaits its own operator approval, distinct from
    approved descendant capture; low-risk independent work continues. See OP-AKU-HELD in the router.
  - [ ] **AKU-07k — bind scheduled work through provider admission/accounting**: version the native
    StageRequest accounting binding with catalog/transition/selection/proposal digests, proposal ID,
    backend and scheduler stage class; include it in prospective request identity, launch contract,
    lifecycle events and recovery validation. Verify provider receipts against it before indexing;
    never rewrite receipts or infer classification from argv, setup stage or an opaque digest.
    Current provider authorize/close APIs receive no typed backend/class binding, so request-ID-only
    changes cannot fix profile settlement. The additional HIGH22/three-process validator scope awaits
    OP-AKU-BIND approval; descendant approval does not cover it. Preserve v1 and old-reader refusal.
  - [x] **AKU-07l — select and materialize native-v2 work through the public driver**:
    plan_iteration selects the existing schema-appropriate plan identity builder while preserving
    proposal recipe identities; materialize_runtime preserves the issued version and checks the
    v2 loaded-instrument pin against startup execution input. ✅ 2026-09-09
    Main reproduced 57 public scheduler/materialization tests (CPU/GPU v1/v2, bad instrument pin,
    wrong recipe identity) and 1,905 combined tests plus 165 subtests. No test upgrades an issued
    prepared stage. Exact two caller seams were LOW; the shared HIGH-impact serving_arm_identity
    helper remains unchanged. Native execution/producer acceptance is still AKU-07i/07m, not this
    selection/materialization slice; no hardware performance claim is implied.
    Research source c65af942, main 9eafac1f.
  - [x] **AKU-07m — derive parent witnesses from sealed native lifecycle evidence**:
    carry the exact sealed native-observation StoredArtifact through closed v2 completion IPC;
    reopen it and its lifecycle reference in the bounded parent evidence producer, joined to the
    parent-issued process/grant/container receipts and frozen plan/recipe/request identities.
    Derive each supported factual witness separately, retain underlying artifacts/source pins,
    and reconcile the same receipt during native capture. Generic request success cannot pass
    correctness, placement or contention. Unsupported purpose/GPU/runtime checks remain unknown
    until their concrete owning adapters are connected. Preserve v1 completion grammar, exact
    retry identity and existing grading/noise policy; configuration injection alone is insufficient.
    ✅ 2026-09-09 — research `0a4aada6`, main `d51f9de6`. Concrete parent service derives
    request completeness, placement and supported health readback; original issuance registry
    and receipt replay precede native capture. Parent-only descendant lookup, deadline-bounded
    serialized IPC and exact retry handling are exercised by an actual tiny-child/socket flow.
    Main combined suite: **1,941 passed, one strict accounting xfailed, 83 subtests passed**;
    after unused-import cleanup, 102 focused tests and Ruff pass. Hermetic observations prove
    integration only; unknown scientific witnesses and ROOT per-witness consumption remain open.
  - [ ] **AKU-07o — connect owning scientific and GPU witness verifiers**: use existing
    correctness, purpose, contention and GPU protocols with original in-window parent evidence.
    Derive each required witness from the actual held allocation and measured lifecycle; no
    generic success, late sample, synthetic telemetry or reduced required-witness list may
    substitute for the owning protocol. Coordinate ROOT per-witness receipt reopening under
    VB-AK-UNIFIED-PARENT and real standalone wiring before mixed CPU/GPU acceptance.
  - [x] **AKU-07r — retain original parent T0 and complete model identity issuance**:
    ✅ 2026-09-09 research f6e0cfe1 / main e495de82. Closed configured registry retains
    immutable original inputs, raw captures and full 17-gate reports; post-teardown replay
    uses the owning reducer, not fresh observation or independent reparsing. Claim-held
    preparation hashes the full model inventory once and binds the native entry-file digest;
    units check original receipts and metadata continuity without model rereads. Producer
    source closure v2 binds actual configured adapters; v1 remains supported. Main tests:
    2,004 loop tests plus 85 Journal tests, one existing expected failure, 83 subtests;
    Ruff/diff clean. Ordinary T0 collection is not contained same-server execution.
    AKU-07o remains open for actual scheduling, same-server multi-request correctness,
    remaining witnesses and ROOT receipt consumption. Proposed frozen-prompt v2 needs
    explicit seed/token-output fields; its HIGH-impact schema edits await OP-AKU-PROMPT.
  - [x] **AKU-07s — capture original contained server request/response evidence**:
    ✅ 2026-09-09 research 8f582b22 / main 361496f5. Actual contained serving retains
    bounded warmup/measurement bytes, ordered slots, request intervals and failures before
    teardown. Reopening joins original instrument/source, frame, requests and descendant PID;
    no retrospective source pin or invented token/seed evidence. Main full suite: 2,218 passed,
    one existing accounting xfailed, 83 subtests, no skips in 59.45s; Ruff/diff clean.
    Tiny HTTP integration uses a pre-enrollment ephemeral port and exact response PID checks.
    This is factual capture only: same-server T0 and remaining scientific witnesses stay
    open under AKU-07o. See research docs/autokernel-native-server-response.md.
  - [x] **AKU-07t — prepare selected complete-model identity before observation binding**:
    ✅ 2026-09-09 research b9d2151e / main f7e65365. Closed target/recipe/model inventory
    preparation runs on the existing parent evidence thread while the child waits for its
    binding. Full-byte verification occurs once; both recipes reuse original issuance and
    verify metadata continuity. Fresh claim checks after model and binding artifact publication
    prevent expired claims from releasing measurement; orphan CAS bytes confer no authority.
    Main full integration: 2,229 passed, one existing accounting xfailed, 83 subtests, no skips
    in 66.47s; eight code/test paths Ruff clean. Actual-child tests match each recipe's own
    entry path/SHA receipt before spawn and observe one original validator invocation without
    changing its pinned identity. Synchronous filesystem I/O is not claimed cancellable.
    Standalone configuration installation and remaining scientific witnesses stay AKU-07n/07o.
  - [x] **AKU-07u — install closed native startup configuration and prospective instrument**:
    ✅ 2026-09-09 research 9e2125b1 / main 625348f8. Startup v3 binds per-target/per-recipe
    complete-model preparation, explicit observation configuration and the installed adapter.
    Dry-run performs no model/store/grant I/O and labels the instrument planned_unpublished;
    runtime publishes/reopens exact instrument bytes before scheduling and retains one adapter
    instance. V1/v2 remain supported. The startup test proves configured owner construction;
    separate genuine-child tests prove raw receipt seal/reopen, not one installed end-to-end run.
  - [x] **AKU-07v — collect bounded same-attempt raw search windows**:
    ✅ 2026-09-09 research 9e2125b1 / main 625348f8. Original source-pinned marker IPC covers
    warmup, measurement, measurement end and teardown after model preparation. Parent polling
    retains bounded host/claim/storage observations and joins original lifecycle intervals.
    Cross-phase, zero-duration, incomplete and post-close coverage cannot become clean windows.
    Exact source/configuration/native/parent receipts seal and reopen; no WindowAttestations,
    calibration/control qualification or scientific verdict is invented. Main full suite:
    2,284 passed, one existing accounting xfailed, 83 subtests, no skips in 68.90s;
    fresh integration subset 56 passed in 8.39s. All 21 published files match accepted hashes.
    Same-server finalization and actual scientific feedback remain AKU-07o/08c.
  - [x] **AKU-07w — retain same-server owning reports and separate parent-final trial captures**:
    ✅ 2026-09-09 research 8f536e0e. Original server/anchor observations and complete owning T0
    reports feed immutable post-arm pairs; candidate-first completion never waits for a future
    anchor. Finalization requires the full original result/registry/lifecycle set, preserves
    failed/rejected facts and emits separate v3 carriers. Native prevalidation reopens originals
    outside the controller mutex; unchanged current-owner fences govern Journal append.
    Closed v3 Journal grammar and exact restart duplicates are tested. Main full acceptance:
    2,301 passed, one existing accounting xfailed, 83 subtests, no skips in 131.82s.
    Byte coherence is not token agreement or a full T0 PASS; missing seed/token/static/dispatch/
    control/calibration warrants stay unknown. Actual driver finish/search and ROOT reader
    composition remain AKU-07o/08c. See research docs/autokernel-server-final-trial.md.
  - [ ] **AKU-07x — connect the existing control-only bootstrap to the measured panel**:
    reuse live_controls' internal cycle-breaking evaluator path solely to compute actual
    control outcomes; never publish its provisional panel or let it admit a candidate.
    Main source review on2026-09-10 established that this does not require a new policy
    exception. Candidate admission must consume the actual measured ControlHarness panel.
    Historical CPU replay may use its own original Qwen frame and declaration; its band
    must not be transferred to GLM. Finish original runner/retained-result joins and prove
    failed controls cannot bank a runtime recipe. The earlier OP-AKU-CONTROLS request is
    superseded by this reuse path, not a remaining startup prerequisite.
  - [ ] **AKU-07n — build real standalone startup inputs and dry-run the installed chain**:
    add the non-test bounded factory/CLI from sealed production campaign_cli export and explicit
    candidate/resource configuration to typed StartupManifest (scheduler, anchors, profile requests,
    plans/execution inputs, evidence and installed provider/verifier identifiers). Factory code
    is accepted under AKU-07q, but no real export-backed manifest currently exists; hermetic CLI
    tests are not installed acceptance and do not prove dashboard projection. Reuse canonical recipe and
    campaign resolution; do not invent profiles, grants or witness receipts. Retain exact real
    input/output paths and a runnable command; satisfy AKU-12a's full chain after separately gated
    generated-export repair. Provider absence is reported debt, not permission to fabricate it.
  - [x] **AKU-07q — construct pinned startup bundles through the enrollment factory**:
    bounded offline CLI consumes sealed campaign_cli v2 output plus matching production export,
    explicit CPU/GPU/candidate configuration and existing typed scheduler/profile/plan/evidence
    inputs; emits closed startup manifest, original pins, preflight debt and exact dry-run command.
    ✅ 2026-09-09 — included in main's 2,024-test combined gate; subprocess factory/driver tests
    use the same composed tree and actual interpreter. No provider, profile, claim or epoch is
    invented. Real generated export repair and installed acceptance remain AKU-12c/12a.
  - [x] **AKU-07z — restart a reused factory from the original scheduler seed**:
    ✅ 2026-09-09. Each factory invocation now constructs a fresh scheduler from the immutable
    manifest, shares that exact instance between controller and runtime (including the feed path),
    and refuses an initially drifted materialized seed. The prior owner no longer leaks mutated
    scheduler state into Journal replay. Main **77 tests passed in5.69s**; all five file hashes
    match the worker packet. Settled same-factory restart, pending-issued replay and feed identity
    pass without modifying replay authority. Research `f1882475` promoted as `c1a8da09`.
    This fixes embedded/in-process reuse; standard process restart already rematerialized inputs.
    Native BIND/HELD recovery and installed live acceptance remain separate open tasks.
- [ ] **AKU-08 — prospective Vidya and scoped retrieval** (AK-AUTO-08): register current-loop source
  before writing new measurements; reuse SC75, shared grader and existing journal/cursors; mandatory
  pre-top-k conflicts, local invalidation generations and bounded asynchronous projection/outage recovery.
  - [x] **AKU-08a — scoped retrieval/route contracts and offline evidence consumer**: exact claim keys,
    mandatory applicable conflicts before top-k, directed nontransitive transfer, victim-directed
    noncomposable coexistence and bounded reject-audit decisions. ✅ 2026-09-09 — main's 173 regression
    tests pass, including 57 focused evidence tests. Cached reuse binds intended use, full support basis,
    relevant dependency content/generation/frontier, explicit semantic buckets, epoch and registered
    rule version; new broader conflicts, removed findings, missing state and quarantine/outage cannot
    preserve obsolete eligibility. Unrelated buckets stay reusable with O(bound dependencies/scopes)
    admission checks. Replay re-derives fences but cannot restore callback authority from JSON. Raw
    grade, retrieval completeness and supported use remain separate; absent registered verifiers fail
    closed. The offline CLI grants no execution authority. V1 broad lookup is deliberately exact in
    mechanism/model/quant/workload/effect question; unsupported candidate universes cannot be certified.
    Actual journal/ClaimTuple producer, asynchronous cursor/invalidation feed, policy adapters, planner,
    audit budget and scheduler consumers remain required; AKU-06/08 are not complete.
  - [x] **AKU-08b — strict prospective arm reader and existing corpus consumer**: full closed
    plan/view/native request and attempt rederivation, exact stored-byte verification, shared ClaimTuple
    projection and native-family-only deduplication. ✅ 2026-09-09 — main's 90 focused tests pass
    with the explicit research-root fixture enabled, including the real research producer → root reader and
    three malformed/tampered regression probes. Identical standalone/journal carriers coalesce by full
    measurement ID plus digest; conflicting carriers emit neither and report refusal. Other source
    families retain their existing semantics. Grade remains the shared ladder; protocol/current use
    and raw attestation are separate. Missing witnesses emit no scalar. No corpus was ingested; native
    controller events are now AKU-03c; bounded asynchronous feed and registered planner-use consumers
    remain required.
  - [ ] **AKU-08c — connect canonical v2 grade receipts and bounded live evidence feedback**:
    retain the registered projector and sole ClaimTuple grader; write immutable receipts from
    reopened native-v2 artifacts and reproject them at eligibility, discharging only the exact
    missing-adapter refusal. No actor string/dict supplies grading authority. Complete actual
    feed/frontier/ACK/invalidation consumers and the final producer-to-projector path. Main's 56
    projector tests include resealed PID mismatch refusal and existing v1 producer compatibility;
    the published native fixture also passes actual ROOT reopening, but remains fixture-only.
    The canonical receipt/readiness/LOO source bridge is published at research dc580b75 / ad86b9e3;
    the published ROOT v2 projector and exact default verifier pins are AKU-08e/08f. Old receipts
    remain compatibility-only until original-run producer capture is proved (AKU-08g). Connect
    typed receipt eligibility, owning comparison/validation decisions and incremental feedback.
    Keep experimental champion selection
    separate from deployment authority; always-Unavailable adapters do not complete this task.
  - [x] **AKU-08i — connect bounded continuous evidence to actual standalone planning**:
    ✅ 2026-09-09 research 50b0d23f. Startup/factory v2 installs explicit feed configuration;
    SQLite/reader ownership opens, drains and closes on the execution thread. The planner
    consumes one coherent retrieval/snapshot bundle through a stable view; relevant evicted
    conflicts remain incomplete before top-k and cached admission. Exact captured ROOT bytes
    avoid stale module/bytecode execution. Finite captured-frontier readiness prevents skipped
    queued invalidations without chasing unrelated writes forever. Durable projection precedes
    sole owned ACK; Journal v2 bounded proof/metadata reads preserve rotation, archive, retry
    and restart semantics. Main latest-native composition: 2,185 passed, one existing strict
    expected failure, 83 subtests, no skips (55.30s); 95 focused tests independently pass.
    Fourteen code/test paths pass Ruff; all sixteen publication files match tested bytes.
    Registered effect/use adapters, scientific eligibility, actual installed providers/export
    and hardware acceptance remain AKU-08c/07n/12, not granted by a live feed connection.
  - [x] **AKU-08d — execute exactly the pinned canonical source bytes**: stable bounded no-follow,
    nonblocking regular-file reads are hashed and those exact bytes compiled/executed, bypassing
    stale timestamp-valid bytecode. ✅ 2026-09-09
    Serialized registration and BaseException cleanup preserve module state; replacement, FIFO,
    cached bytecode, cancellation and concurrent constructors have permanent regressions. Main
    reproduced 13 focused/source-loader tests after composition; clean native-v2 acceptance passed
    1,916 tests plus 165 subtests (19 including independent edge/reopen probes). Research source
    dc580b75, main ad86b9e3. Sole ClaimTuple grading is unchanged; final pins and permitted-use
    decisions remain AKU-08c, and compatibility receipts grant no production-validation authority.
  - [x] **AKU-08e — reopen native-v2 artifacts through the existing registered ROOT projector**:
    preserve the v1 source class and shared ClaimTuple ladder while dispatching exact v2 plan,
    loaded-instrument, lifecycle, native-attempt and journal envelopes. ✅ 2026-09-09
    Main reproduced 133 projector/corpus/ladder/ledger tests plus the actual owned-child v2
    cross-repository probe (1.08s). The reader reopens exact native dependencies; operational and
    diagnostic records emit no scalar. Review reproduced a FIFO hang before fstat and corrected
    it with nonblocking open; resealed container/target-worker/boot mismatch tests now refuse.
    Adapter SHA-256 ad87bdec7afc4d07f04fe48375adf4fe476a20423481b2be662e776a2b590192.
    Fixture telemetry proves integration, not real measurement eligibility. Final semantic pins,
    typed receipt consumption and the bounded live feed remain AKU-08c; parent factual receipt
    authentication remains AKU-07m/VB-AK-UNIFIED-PARENT. No Ledger.append or grading changes.
  - [x] **AKU-08f — load the published canonical projector by default without retroactive authority**:
    install the exact six-field verifier closure and select it during ordinary construction;
    preserve explicit legacy compatibility loading. ✅ 2026-09-09
    Research source 9ed6fc35, main b83b1027; main reproduced 19 focused tests and independent
    source-loader/reopen probes. ROOT source 2010b713 and adapter ad87bdec are pinned exactly.
    Existing native-v2 records lack captured producer implementations, so receipts retain
    compatibility_only even with current verifier pins; receipt-pair decisions check that scope
    independently. This fixes the default loader, not the outstanding scientific-use consumer.
  - [ ] **AKU-08g — capture producer implementation identity before the original run**:
    seal a closed producer_source_closure in loaded-instrument used_constants before plan freeze,
    using existing loaded-callable/config identities for the selected deferred native sink and
    observation seal/validation path. Include actual builder/finalizer dependencies, not only a
    wrapper label or today's module hash. Bind the actual selected implementations during capture;
    canonical receipt reopening must match the captured closure to the installed expected closure.
    Old instruments lacking it stay compatibility-only. Connect only its supported provenance
    warrant to typed eligibility under AKU-08c; no new carrier grammar, grading ladder or
    numerical acceptance policy is implied. Lifecycle and semantic owners coordinate one writer.
    Original write-side capture is published in AKU-08h; finish canonical reopening/eligibility
    with genuine prospective evidence, retaining every owning protocol's required witness.
  - [x] **AKU-08h — prospective producer code/configuration capture**: before plan issue,
    seal selected deferred sink methods, observation seal/reopen and v2 validation methods plus
    actual configured verifier slots in loaded-instrument used_constants. Capture checks the
    selected implementation against those original bytes. Exact bounded immutable string-set
    constants now hash deterministically; other unsupported configurations remain unproven.
    ✅ 2026-09-09 — research `0a4aada6`, main `d51f9de6`; actual default closure is complete,
    with cross-hash-seed, changed-implementation/configuration and historical-absence tests.
    This captures provenance only, not scientific eligibility or retrospective authority.
  - [x] **AKU-08j — reopen original parent-final v3 evidence in the ROOT arm/corpus reader**:
    ✅ 2026-09-09. Closed final/original/pair/result/lifecycle/source joins preserve immutable
    original v2 carriers, exact owning gate membership and diagnostic status. Original schema
    is checked before dispatch to prevent recursive v3 chains resetting read budgets; malformed
    reference types refuse before field access. Same-unit foreign lifecycle and deferred-capture
    references fail exact joins. No v3-to-v2 relabelling or new grading ladder. Main acceptance:
    91 actual-producer/arm/corpus tests in 46.05s plus 65 claim-tuple/ledger tests in 0.09s.
    Actual child/HTTP/Journal artifacts yield no measurement tuples when diagnostic.
  - [x] **AKU-08k — include the final-trial helper in the registered verifier source closure**:
    ✅ 2026-09-09. Installed feed supports exact six/seven-file pinned closures; the current
    seven-file closure captures the final-trial helper and its exact lazy relative imports.
    All source bytes are verified before execution; no ambient helper fallback. Actual child
    v3 results drain through FeedRuntimeOwner/EvidenceFeed and restart idempotently with no
    scientific promotion. Main acceptance: 42 tests in 46.76s, no skips. Six-file v3 reads refuse.
  - [x] **AKU-08l — version the separate semantic receipt source closure**: ✅ 2026-09-09.
    Seven-file captured ROOT closure and original native producer/finalizer identities feed
    versioned canonical receipts. Diagnostics contain no tuple or grade. The actual validation
    consumer persists and reopens exact historical pairs through fresh stores/controllers without
    live issuance; CANDIDATE diagnostics cannot fill required OPTIMUM rows or advance validation.
    Main independently passed 90 tests in 64.27s; worker regression passed 132 in 70.71s, no skips.
    Historical two-file pins remain unchanged; legacy tests load their exact original source bytes.
  - [ ] **AKU-08m — connect qualified serving decisions to the registered semantic consumer**:
    supply original qualified calibration/control and measurement evidence through the same
    registered verifier/evaluator; prove actual required-row completion and restart. Diagnostic
    receipt replay alone does not authorize ranking, validation, or production promotion.
  - [x] **AKU-07y — prevent lifecycle sampling-budget starvation**: ✅ 2026-09-09.
    Native producer admission now requires ceil((stage+teardown)/cadence)+9 samples before
    thread creation, grants or child launch, using existing enforced durations and fixed hooks.
    Spurious wakes retain an absolute due time; periodic enqueue rechecks phase/pending/stop
    after unlocked clock reads. No new knob, automatic budget enlargement or marker reservation.
    Main independently passed 123 regression tests and the final 56-test lifecycle file;
    exact 109-slot success/108-slot teardown refusal covers the full 100-periodic-plus-nine-hook
    boundary. Missing/gap/byte/queue/shutdown failures remain unknown; no scientific threshold
    or historical identity changed. Prospective sampler/helper source identities are pinned.
- [ ] **AKU-09 — coherent existing dashboard/control surface** (AK-AUTO-11): producer-owned authenticated
  commands, ordered full snapshots, separate heartbeat/activity/science clocks, lifecycle-aware semantic
  health, hub registry/probes/freshness; no hub proxy or second dashboard.
  - [x] **AKU-09a — stop/join worker heartbeat before terminal publication**: no late `running` state;
    startup/claim/profile failures publish failure; original errors survive status errors; fake-race tests
    prove the real run path uses the lifecycle guard.
    ✅ 2026-09-09 — one deadline bounds close-lock/write-lock acquisition and thread join. Timeout
    refuses terminal publication; an arbitrary synchronous filesystem write itself is not claimed
    time-bounded. Heartbeats retain `starting` until the run advances; final artifact is durable before
    `complete`, and failure snapshots retain available outcomes. 46 focused lifecycle/status tests pass.
  - [x] **AKU-09b — current versus historical accumulator rendering**: both existing hub render sites
    withhold magnitude/progress unless validity is current and the threshold is positive/finite.
    ✅ 2026-09-09 — missing/stale/legacy magnitudes remain labelled history; membership/cadence remain
    visible. Stale threshold signals are producer-reported/unverified, not fresh warrant. Main's Node
    DOM harness covers these combinations (69 tests, 5 subtests); this is not a browser or live-soak test.
  - [x] **AKU-09c — existing hub consumes coherent management-v1 snapshots and direct controls**:
    explicit campaign/config selection, closed snapshot/ACK validation, monotonic stream fencing,
    separate producer/activity/science clocks and independently dated evidence cards.
    ✅ 2026-09-09 — main's full hub acceptance passed **414 tests and 125 subtests**; combined research
    service/controller/guard acceptance passed **198 tests and 4 subtests**. One lazy bounded health
    probe owner rejects stale/late/mismatched replies; selected unified health is not vetoed by absent
    legacy state. Bearer tokens remain in tab memory and commands go directly to the authenticated,
    exact-origin producer gateway, never through a hub proxy. Browser deadlines cover headers and body;
    uncertain ACKs retain the exact retry, while double-clicks serialize. The service bounds trickling
    connections with one owned watchdog and identifies loaded transport code with stable projection.
    Existing registry/nav/probes/freshness remain the surface; no second page. Legacy fixture repairs
    retain producer/anchor/authority assertions without hard-coded current-host percentages or age.
    V1 remains management-only with no active worker or compute authority. Gateway/service deployment,
    worker-aware v2 integration and unattended live reliability remain separate acceptance work.
  - [x] **AKU-09d — existing hub consumes the actual worker-aware v2 producer**: strict closed
    snapshot/result versions, monotonic worker/stream identity, lifecycle-aware semantic health and
    exact accepted-versus-completed controls, retaining v1 as a distinct management-only contract.
    ✅ 2026-09-09 — main's **296 tests and 79 subtests** pass, including real research-controller
    snapshots and execution of the actual page JavaScript. Acknowledged incomplete pause can escalate
    to a distinct drain; failed request construction retains the old pending pause, uncertain ACKs
    retain exact-ID retry, and late ACKs cannot erase a newer completion. Python/page validators agree
    on finite result semantics, acquisition-pending identities, permitted null-worker transition
    windows, protocol-version matching and same-campaign downgrade refusal. Cross-repo fixtures use
    explicit/standard checkout discovery and a post-release worker barrier; ordinary v2 unit tests
    remain independent of the optional checkout. The broader dashboard run separately reproduces
    **15 baseline-proved legacy failures** (11 tests plus four subtests); these are not v2 acceptance.
    No gateway configuration, service activation, resource grants or live reliability claim is made.
    Unified planner/resource/evidence projections and unattended deployment remain AKU-09 work.
  - [x] **AKU-09e — existing hub consumes closed unified snapshot v3**: scheduler, resources,
    actors, evidence, candidate and targets render within the existing `/loop` page with strict
    independent Python/page validation. ✅ 2026-09-09 — main reproduced **96 focused tests** against
    the published research producer, including execution of actual page JavaScript. Python rederives
    accounting content identity; page validation checks closed nested shapes, statuses and values.
    Unknown dependencies degrade a live producer without disabling identity-matched controls; a
    drained snapshot with an unknown producer remains history. V1/v2 compatibility, exact retry and
    same-campaign downgrade fences remain. Null grants/candidate/evidence values stay unknown, and
    declared capacity is not a grant. No new route, proxy, registry row, gateway configuration, service
    activation or live reliability claim is made; connected consumers and deployment remain AKU-09.
  - [x] **AKU-09f — connect runtime outcomes and separately dated owned-work observations**:
    ✅ 2026-09-09. Existing snapshot-v3 supports closed unified projection-v2; actual runtime
    result/wait reason, installed kinds and original selection/settlement are owner-bound.
    Publisher heartbeat cannot refresh operational observation. First-publication and post-settlement
    reporting faults preserve execution/retry semantics. Producer checks original current-domain
    worker deadlines; consumers age only its relative remainder, distinguishing long work, silence,
    expiry and unknown clocks. Python/page rollback fences and rejected-envelope rendering agree.
    Main integrated **181 research tests passed, one strict HELD xfail in33.09s** and **113 ROOT
    tests passed in2.37s**. Worker broader ROOT327 passed plus51 subtests. Ten exact packet file
    hashes match; the remaining documentation file additionally retains the published factory fix.
    Existing52 loop_status lint findings remain baseline-identical; changed logic adds no findings.
    Contract: research docs/autokernel-runtime-observation.md. No service reload, deployment,
    live reliability, resource grant or scientific-validation claim; AKU-09 remains open.
  - [x] **AKU-09h — connect bounded evidence, actor, profile and calibration observations**:
    ✅ 2026-09-09. Closed unified projection-v3 retains original owner reduction dates separately
    from attempts and publisher heartbeat; 64 total detail rows and a32KiB bound constrain payloads.
    Publisher performs no SQLite/artifact reopening. Diagnostic faults retain the prior dated cache
    and cannot change settlement; future timestamps are rejected before cache replacement.
    Main integration:165 research tests passed, two strict BIND/HELD xfails in81.65s, no skips;
    ROOT41 dashboard tests passed in0.51s. Changed research Python passes Ruff.
    Actor completion is not settlement, collected calibration is not qualification, and cached
    evidence totals are not current eligibility. Resource/candidate sections remain not_connected;
    no live deployment/reliability or scientific acceptance is claimed.
  - [ ] **AKU-09g — connect remaining aggregate producer state and finish dashboard acceptance**:
    replace remaining not_connected sections with bounded evidence-frontier, preparation/actor,
    resource and candidate projections from their actual owning indexes. Keep original expiry,
    settlement and validation authority distinct; no publisher-thread SQLite or artifact reopening.
    Runtime observation alone is not aggregate readiness. Finish existing service configuration,
    health/freshness/control acceptance and monitored reliability under AKU-12; do not create a
    second page or treat transport health as proof of scientific progress.
  - [x] **AKU-09i — label the displayed noise threshold without inventing its estimator**:
    ✅ 2026-09-10. The loop page now calls the value the measured dispersion of the anchor,
    instead of claiming every producer defines it against the anchor mean. The retained GLM
    v1 floor is p95 absolute deviation from the median (7.801%, n=5); other floor producers may
    use different estimators. Four focused terminal-render tests pass; no measurement changed.
  - [x] **AKU-09j — publish separately attributed champion capabilities without rewriting the
    numeric A/B record**: ✅ 2026-09-10. The existing champion card now merges bounded,
    schema-checked capability records whose exact commit is the current champion or its proven
    ancestor. Divergent lineage, malformed timestamps, partial SHAs and oversized records are
    ignored rather than presented as current capability. The live record adds DFlash2 speculative
    GPU serving and Flash-Next (`qwen4exp`) CPU/native-MTP support to the five retained historical
    GPU capabilities, with explicit source commits, artifact hashes and claim limits. The direct
    champion-vs-production percentage remains untouched. Focused reader tests pass 27/27; the live
    snapshot resolves seven capabilities from
    `/mnt/raid0/llm/autokernel/loop-memory/champion-capabilities.json` (SHA-256
    `264f16ad346634b2a0c7bbe5e7a83faa976db0a7f75162f38f38324393247ea7`).
- [ ] **AKU-10 — reproducible migration and artifact retention** (AK-AUTO-12): versioned import without
  invented provenance, unsupported-schema rollback refusal, retained ref/build closure, budgeted storage
  maintenance and documented validated CLI/config examples.
  - [x] **AKU-10a — retained-artifact closure and truthful legacy cleanup consumer**: immutable
    root/dependency snapshots, deterministic expiry previews through the existing storage policy,
    and exact owned-path legacy pruning with recoverable failure reporting.
    ✅ 2026-09-09 — main's **174 tests and 13 subtests** pass. Maintenance rederives closure instead of
    trusting a rehashed plan; permanent classes, shared paths, ancestor/descendant overlaps and their
    transitive dependencies remain retained. Missing/uncertain closure emits no expiry candidates.
    Legacy cleanup binds captured/opened parent identity, uses private 0700 descriptor-bound quarantine,
    preserves unexpected replacements, closes descriptors on I/O errors, and reports only actual owned
    remaining content as recoverable. Reclaimed bytes are unknown, not a fabricated fixed estimate.
    Current `loop.run` deliberately withholds pruning with `retention_unknown`; even complete caller
    JSON cannot enable unified deletion. Native current-controller roots, immediate generation checks,
    existing tombstone-before-bytes expiry and journaled maintenance results remain required. Tests
    use temporary fixtures only; no research artifacts were deleted and AKU-10 remains open.
  - [x] **AKU-10b — typed native retention consumer and exact tombstone recovery**: bounded
    candidate/native-root projection feeds existing retained-artifact closure and dry expiry policy;
    actual deletion requires a held generation/root-exclusion capability. ✅ 2026-09-09 — main
    reproduced **250 tests and 82 subtests**, including actual temporary CandidateTransactions,
    ArtifactStore and native Journal close/reopen recovery. One bounded tombstone index per operation
    checks complete descriptor/preconditions/policy identity; intent-after-removal recovery cannot
    delete twice. Generation, source/branch, protected kernels, changed content and shared DSO/ancestor
    roots fail closed. Sequential callers prove idempotence, not concurrency. Source `1be3cf79`,
    main `e678a2e2`. Default execution remains unavailable pending the assigned actual maintenance
    exclusion/native-root/provider-accounting consumer; slow I/O must not hold the controller mutex.
    Only disposable fixture bytes were deleted; no research artifacts or real cleanup were touched.
  - [x] **AKU-10c — versioned historical migration and verified store exclusion**: bounded
    noncreating dry-run and explicit immutable snapshot import reuse read-only accumulator recovery,
    actual ExperimentStore rows and the existing content-addressed ArtifactStore. ✅ 2026-09-09
    Main reproduced **110 targeted tests**; the combined clean eleven-file retention/migration
    release passed **1,750 tests and 165 subtests**, with **68 final focused tests** and Ruff clean.
    Public reentrant store exclusion serializes nested writes and same-root threads/processes;
    closed/replaced roots refuse. URI-escaped SQLite paths, active WAL/SHM, changing source frontier,
    strict row/byte bounds, unsupported versions and source/destination aliases are tested. Emitted
    snapshots must pass their installed v1 reader before publication, and exact retries preserve
    source bytes. Historical evidence stays `unknown_legacy`; no candidate/validated/serving
    authority is created. Source `1be3cf79`, main `e678a2e2`; live import/cutover and future durable
    legacy database schema marking remain outside this completed snapshot-reader slice.
  - [ ] **AKU-10d — finish native maintenance ownership and uncertain-provider recovery**:
    complete fresh admission and real execution using the native catalog and provider below.
    The durable ownership/replay slice is published as AKU-10e; absence of the remaining roots
    or actual provider must continue to refuse fresh cleanup, not become an eligibility bypass.
  - [x] **AKU-10e — durable maintenance ownership, replay and shutdown fences**: short controller
    transactions retain exclusion across unlocked provider/filesystem work; uncertain acquisition,
    tombstone publication and settlement preserve recovery ownership. ✅ 2026-09-09
    First holds bind to their token; completed accounting reconstructs the exact receipt digest
    and matches IO_COMPLETE cost; fresh and recovery intents enforce their distinct token chains
    and clear prior hold/cost state. Receiptless abort refuses; valid legacy non-abort bytes replay.
    Worker/candidate/new-native publication and clean shutdown cannot bypass owned exclusion.
    Clean six-file acceptance passed 1,873 tests plus 165 subtests; main's composed native/maintenance
    tree passed 1,899 plus 165, with 39 maintenance tests and six independent probes. Research
    source c5525fb8; fresh catalog/provider execution and real artifact deletion are not completed.
  - [ ] **AKU-10f — connect complete native retained-artifact/dependency catalog**: populate the
    controller-owned catalog from existing worker/evidence/candidate/DSO/RUNPATH/physical-root
    write hooks; prove completeness and exact protected/live dependencies before fresh admission.
    CandidateTransactions.retention_view currently verifies candidate manifests, then refuses
    incomplete external coverage. Caller-supplied roots or membership cannot replace owner records.
  - [ ] **AKU-10g — connect real maintenance holds and accounting**: implement the broker-owned
    hold/refresh/settlement provider and concrete controller backend, preserving bounded unlocked
    I/O, exact abort/completion receipts and uncertain replay. Default execution remains unavailable;
    source publication does not authorize live deletion or provider activation.
  - [x] **AKU-10h — installed native retention catalog and dependency frontier**: ✅ 2026-09-09.
    Actual standalone v3 derives and durably installs its catalog before runtime composition;
    restart replays the exact seed. Exact model inventories, recipe snapshots/aliases, executable,
    DSO/build/RUNPATH and protected roots join candidate, native, driver and worker/acquisition
    state. Collection performs filesystem work outside the controller mutex and rechecks the
    frontier before binding a job. Main passed 155 composed tests without skips, then 104 tests
    and 15 subtests for Journal/catalog/installed startup after byte-exact application.
    No owner-issued expiry descriptors or live deletion: the current native view retains all
    declared artifacts. This does not complete AKU-10f/10d/10g or authorize provider activation.
  - [ ] **AKU-10i — prospective source/build/evaluation expiry authority**: install the actual
    source/build execution owner and bind its verified BuildIdentity, exact recipe snapshot and
    retained source refs before opt-in candidate integration. Persist the enrollment pointer
    before integration so restart can reconcile it; ordinary/legacy integrations remain unchanged.
    Require closed original evaluation/native/worker/held-cost evidence and exclusive physical
    ownership before issuing any disposition. No inferred rejection, caller-label authority,
    historical backfill, temporary duplicate accounting record or deletion-policy change.
- [ ] **AKU-11 — real resource-provider/broker integration** (AK-AUTO-03/05): retained OP-41 ownership and
  finalise → promote → reboot gate. Implementation is authorized by the operator's instruction
  to implement this handoff; do not reopen broker-code authorization as a pending choice.
  other separately gated live activation still require their original authority. The serial selector
  now transports exact selections and the final v6 owner demonstrated live CPU/GPU rotation with
  exact held-resource settlement. The remaining broad finalise/promote/reboot scope is separate from
  the completed unified-loop trial and did not authorize production mutation.
- [ ] **AKU-12 — live cutover and unattended acceptance** (AK-AUTO-12): separate research-relaunch and
  compute authority; applicable post-BIOS calibration and owning serving protocol. Bounded mixed campaign
  and eventual soak demonstrate the actual CPU/GPU/candidate paths, not only helpers or fixtures.
  - [x] **AKU-12a — complete standalone dry run**: ✅ 2026-09-10 — exercise the installed unified entrypoint,
    real production export and explicit candidate enrollment, planner prerequisites/budgets,
    recovery and dashboard/control projections without acquiring compute or inventing grants.
    Retain the exact command/config, loaded code identities, output and refusal/debt evidence.
    Final research commit `377397fa` resolves all eight targets, selects `matched_process_v2` for
    every CPU target and preserves the GPU path without creating compute/state. The actual command
    exited 0 with eight target/dry-run blocks, seven 48-launch matched calibration plans and one
    native GPU five-launch plan; its requested state directory remains absent. Retained output:
    `/mnt/raid0/llm/tmp/aku-final-all8-dryrun-20260910-v2.log`, SHA-256
    `e0783ef73f31dbae760074aab09419b317e63cc52f8fca8af2b0671d5b36d315`.
  - [x] **AKU-12b — five-loop monitored acceptance and bug-fix rerun**: ✅ 2026-09-11 — after applicable real
    resource and operator gates, complete five monitored unified research iterations through the
    actual unified execution path, focusing this five-loop trial on **experimental GLM-5.3-Flash
    CPU kernel research**, as directed by the operator on 2026-09-09. Retain selections, held-resource receipts, lifecycle samples,
    results, evidence updates, dashboard freshness/control observations and teardown checks.
    Fix failures and rerun affected acceptance; five mock/helper iterations do not satisfy this
    operator-requested goal. Keep performance/validation claims within the owning protocol.
    Reuse [the GLM source handoff](../../docs/reference/models/glm53-autokernel-handoff.md) and
    [final progress log](../../progress/2026-09/2026-09-09-glm53-cpu-optimization.md): core
    c463f601bd39d0e313b744c214b8c22f9455bcd3 is experimental and NOT ACCEPTED; reference
    f8e2668b6a951d7c44f3264f87d1bc882299bae5 preserves default-off experiments/tests. Compare GLM
    against a validated experimental GLM control, not the GLM-incapable champion; champion remains
    the cross-model regression baseline. Preserve six-shard UD-Q4_K_XL identity, canonical48
    placement/environment, native MTP depth3 and exact trajectory/rejection/rollback gates.
    Reuse the four already-seeded measured_null records without duplicate ingestion. Resolve the
    Flash-Next CPU historical regression signal with matched evidence before any champion admission;
    do not infer causality from its single cross-session comparison. Rejected expert/Q8 experiments
    and the disproven copy route require new evidence before retry. Smaller partitions are distinct
    validated recipes, not automatic full-instance transfer. This CPU focus does not waive broader
    CPU/GPU integration acceptance, cross-model regressions or separate production-promotion gates.
    The pre-serial GLM controller completed 5/5 real measured iterations and a separate original GPU
    iteration completed 5 pairs/10 resident launches. Final acceptance then used one v6 serial owner
    for six alternating CPU/GPU batches. It completed without failed targets or unsettled selections;
    four v6 GLM attempts plus the valid v4 GLM attempt form the requested five-loop trial. The three
    measured effects were +0.186%, -3.360% and -2.152%, all below their applicable matched floor; two
    hypotheses refused formation. GPU work settled as refusal/transient rather than inventing a
    measurement. Research `3aa79c89` fixes the one observed resume/settlement fault and 136 relevant
    tests plus 3 subtests pass. Exact v6 state: `/mnt/raid0/llm/tmp/aku-final-glm-gpu-state-20260911-v6`
    (`serial-state.json` SHA-256 `40a1fa32ccf75ffef9e7f2056ef1d676df445b5acd2f12b042b6b81c26475265`).
    - [x] **AKU-12b-CPU-OBS — add bounded factual CPU lifecycle collection to the existing
      serving path on disk.** ✅ 2026-09-10 — Research packet `499ec92e…` adds process/task
      affinity and allowed-NUMA-list samples through the original serving lifecycle;
      main independently verified 43 tests plus 8 subtests. Raw facts/errors/gaps/bounds
      survive the existing comparison archive. Allowed lists do not establish actual NUMA
      page placement, clean contention or scientific eligibility; both existing proof labels
      remain `unproven`. GPU behavior is unchanged. No live PID was restarted or retroactively
      instrumented; this checkbox does not close AKU-12b or certify a new measured arm.
      Prospective direct-serving belief wiring is separately filed as
      [VB-AK-LEGACY-SERVING](vidya-belief-substrate-program.md#vb-ak-legacy-serving--direct-serving-comparison-and-cpu-facts-2026-09-10).
    - [x] **AKU-12b-TARGET-CLI — connect an explicitly enrolled target to the existing loop
      CLI.** ✅ 2026-09-10 — Research source `1f2d93aa` / main `195c4ea5` adds
      `--resolved-campaign` with `--target-id`, preserves original enrollment identity,
      binds CPU serving workload and retains the legacy GPU-screen label. Main verified
      68 focused tests. This is not serial all-target dispatch, artifact admission,
      a live-process restart or completion of the broader acceptance goal.
    - [x] **AKU-12b-SERIAL-CLI — rotate finite enrolled-target batches through the existing
      loop owner.** ✅ 2026-09-10 — Research `718f4108` / main `d5b3cc96` adds
      `loop.serial_run`, persistent STOP, distinct batch outputs and actual current/COR
      continuation. Restart no longer pairs a restored old COR commit with the current
      build. Switching reuses verified retained anchors and request-bound floors; no
      copy, forced rebuild or recalibration merely for a switch. Primary verification:
      82 focused tests passed (4.55s); the 14 serial tests include real tiny children
      and existing-owner synthetic keep/resume paths. No live hardware serial proof,
      fabricated GPU provenance, new grader or completion of AKU-12b is claimed.
    - [x] **AKU-12b-SERIAL-DASH — show serial routing and the exact active child without
      hiding canonical history.** ✅ 2026-09-10 — Research `237d82ec` / main `707639d4`
      publishes original batch directory/PID and routing totals; integrated ROOT support
      keeps canonical champion/history roots unchanged. Child detail requires matching
      target, directory and PID, with freshness independent of the router heartbeat;
      stopped, complete and all-failed sessions remain distinct. Main verified 42 producer
      tests (7.72s) and 18 ROOT tests (2.71s). ROOT publication is combined with this
      checkpoint; no dashboard environment change, process reload or live serial proof.
    - [x] **AKU-12b-OWNED-ROSTER — derive the existing serial runner's inputs from ready
      enrolled CPU/GPU/candidate targets.** ✅ 2026-09-10 — Research `8f67076c` / main
      `d5705634` adds resolved campaign + one concise owned-target map, deriving model,
      recipe, actor defaults and distinct output/lane roots without per-target argv files.
      Original source/branch/anchor/request facts remain explicit; aliases execute once,
      unavailable/unowned targets remain named, and old `--target-args` still works.
      Generated children are confined with existing `taskset`; original continuation,
      STOP and no-replay behavior remain. Actual corrected GLM metadata generation selected
      **1 ready seed and reported 17 unavailable targets** without model/binary hashing or
      output creation. This is partial coverage, not all-target or live-run acceptance.
    - [x] **AKU-12b-GPU-SERVING — execute explicitly selected GPU serving workloads and
      bind declared host resources through existing owners.** ✅ 2026-09-10 — The same
      research checkpoint adds `--gpu-serving-launch`, original frozen requests and
      request-bound calibration to the existing serving comparison. Experimental GPU
      candidates remain separate from canonical COR/accumulator semantics; ordinary GPU
      cheap screens are unchanged. Shared validation binds model/workload and
      supported GPU visibility, while declared host CPUs/build jobs govern affinity,
      builds and existing CPU-region claims alongside the original GPU claim. Main's
      combined **84 tests passed in 7.34s**, with synthetic hardware/provider boundaries,
      actual tiny children and dry-run owner validation. Main then ran the real GLM
      serial `--dry-run`: exit 0 in 0.19s, original c463 startup identity, n_embd=4096
      census and original request-bound 7.801% floor reopened. No build, resource claim,
      inference, current live-PID reload or qualified/promotion gate is claimed.
    - [x] **AKU-12b-SERVING-BELIEFS — connect the direct comparison write/read belief path.**
      ✅ 2026-09-10 — Research `86179a8c` / main `0a815338` captures inputs before launch,
      retains original comparison/CPU dependency bytes and exports through the existing archive.
      ROOT's strict reader reaches the existing corpus and Ledger; main verified 33 research
      tests plus 8 subtests and 15 ROOT tests. Protocol remains empty (`Judged/Located`);
      no historical backfill or qualified hardware gate is completed. The current live PID was
      not reloaded; live ingestion remains unverified and planner feedback follows below in the separate
      [VB-AK-LEGACY-SERVING tasks](vidya-belief-substrate-program.md#vb-ak-legacy-serving--direct-serving-comparison-and-cpu-facts-2026-09-10).
    - [x] **AKU-12b-SERVING-FEEDBACK — recall original serving observations in the existing
      planner context.** ✅ 2026-09-10 — Research `8360d3e1` / main `ba5abca4` plus
      ROOT's original-source/query helper add bounded incremental per-store ingestion
      and model/recipe/request/epoch/anchor-scoped observations beside unchanged historical
      recall. Main verified 55 research and 28 ROOT tests, including actual existing-loop
      keep/rebind/subsequent-null/restart with synthetic providers. No new grader, qualified
      gain or full-instance transfer; nulls remain worth remembering. Future starts must
      select the installed ROOT via the documented `--belief-root-repo` option. This is
      code-path integration only: no current live-PID reload or real post-hook ingestion,
      and AKU-12b/live hardware acceptance remains open.
  - [ ] **AKU-12c — repair and verify canonical generated export inputs**: real production export
    currently refuses stale descriptor/compiled-priors provenance. The supported writer is
    stack_change_pipeline.py update, regenerating lean registry, descriptors, priors, procedure
    enums and summary while preserving declared full/split instance mode; bare compile_stack_priors
    would lose the split mode. The isolated generated-file repair awaits explicit approval for its
    HIGH-impact scope (66 upstream); no compiler logic, service reload or frozen kernel change.
    Verify reproducibility and exporter closure, then supply exact artifact pins/configs to AKU-12a.
    See OP-AKU-STACK in the router; no stale digest bypass or fabricated export is permitted.
    The generated full-SMT campaign resolves seven production workloads plus the explicit GLM
    candidate and passes original-owner preflight. Final closure awaits the persisted final-code
    dry-run artifact and repair of the full-suite speculation-identity regression it exposed.

### Execution discipline and retained decisions

Use existing classes/functions where their contract is sufficient; new helpers must gain explicit
consumers before the corresponding parent slice is complete. Unit-tested interfaces alone do not
complete a service, broker, adapter or measurement gate. No deployment/restart is hidden in publication.
Defaults not fixed by policy are versioned configuration with dry-run validation; do not invent a
statistical acceptance threshold, ratification, resource grant or unsupported production capability.

The primary built-in dispatcher retained completed review threads; its implementation team uses one
built-in sol-medium worker and two explicitly configured `codex exec` workers. On the operator's
2026-09-09 request, a separate CLI coordinating session started three additional sol-medium workers
for dashboard v3, actor/target-profile preparation and the bounded belief feed. Its isolated root and
research worktrees are `autokernel-consumers-{root,research}-20260909`, on
`lane/autokernel-consumers-20260909`, starting at root `519acd08` and research `bb0c2c38`.
The secondary team cannot publish changes or edit primary core files without a precise seam release;
released core hunks stay in its isolated worktree and are applied only after primary review. The
primary owns final integration and publication. Exact shared seams are coordinated before edits,
not merged by assumption. A third coordinating CLI session, also requested by the
operator on 2026-09-09, started three sol-medium workers for candidate-validation consumption,
versioned legacy migration, and standalone CLI/service packaging. It owns only the isolated research
worktree `autokernel-delivery-research-20260909`, branch `lane/autokernel-delivery-20260909`, starting
at `bb0c2c38`; core and secondary-team files remain read-only except for explicitly released,
disjoint core hunks. The secondary dashboard worker moved
to retention after its package was frozen for review. The nine-worker arrangement is scheduling,
not a claim of completed source, live execution or greater measurement authority.
GitNexus impact results are supplemented by actual caller inspection and adversarial integration tests.

Every team performs per-package boundary wrap-up: owned documentation, exact validation evidence,
file hashes, remaining integration tasks, and proposed ledger/progress text. Team leads independently
review those handbacks and label them `awaiting_primary_acceptance` until the primary applies shared
handoff/index/progress updates and publishes accepted paths. No team waits for all peers before
submitting a completed package, and no unreviewed draft becomes a published checkpoint.

Per-task handoff/progress/checklist/publication follows the wrap-up workflow. Index pruning, handoff
compaction and wiki compilation are not part of this implementation request's routine checkpoints.
