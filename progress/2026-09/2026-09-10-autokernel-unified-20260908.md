# Unified AutoKernel implementation — 2026-09-10

## First actual CPU iteration completed as a measured null

- Checkpoint source: research `2059e30e`, ROOT `be070987`. The running experimental
  GLM CPU trial uses the existing loop, PID1380863 (owning worker handle21102), and
  its dedicated trial store; canonical champion/history remain separate.
- Candidate `akm-q4k-avx512-paired-y` completed source authoring → build → existing
  MUL_MAT correctness gate → five serving A/B pairs → durable `measured_null`.
  Effect fraction `0.009501638190257289` (+0.95016%) is below the 7.801% calibrated
  floor. This is an actual measured null, not a failed build/gate or an accepted gain.
- The original loop advanced automatically into iteration 2. At this boundary:
  one completed iteration, one measurement, no keep. The five-iteration test remains
  incomplete; no canonical champion promotion or qualified performance claim is made.
- Durable evidence: trial-store `experiments.db` attempt `05843e3b…` retains five
  samples per arm, with comparison and floor request digest
  `b8475457d62a637a58cbe90e9b66864804122ed713ac14562a5f6c400c5154d0`.
  The candidate patch is retained at `patches/akm-q4k-avx512-paired-y.lane0.patch`;
  the worker source returned clean to `c463f601`. The five-launch calibration file
  was reused unchanged, not rerun. Runtime residency records explicitly report
  `cpu_placement=unproven`; requested CPU0–95 is not runtime placement proof.
  This and the existing host-uptime qualification limit prohibit treating this
  workflow trial as a qualified performance/admission result.
- This checkpoint records one completed execution subtask only. It does not close
  the broader CPU/GPU autonomy program or start another run. Documentation preparation
  made no runtime changes, index edits, commits or wiki sweep. README freshness check
  exited0 with no warnings.

## CPU lifecycle facts integrated on disk, not retrofitted into the running trial

- The first retained CPU comparison (`05843e3b…`) had ten launches and GPU-sampler
  readings, but no CPU-affinity readings. The direct serving path explicitly returned
  `cpu_placement=unproven`; declared CPU0–95 was launch intent, not an observation.
- Research PRIMARY received the bounded three-file collector packet based on
  `2059e30e`: `loop/residency.py`, `loop/serving.py`, and
  `loop/test_cpu_lifecycle_facts.py`. Packet SHA-256:
  `499ec92e1e9b5de5762c8446f3eb492369af03cd0b3c58270f88129dc0fb3232`.
  This is on-disk integration only. No running process was restarted/reloaded, and
  the already-running trial is not claimed to have loaded the collector.
- Future direct resolved-CPU launches retain factual `cpu_lifecycle` rows beside
  each arm's residency record: original attached PID/start ticks, TID/start ticks,
  CPU and NUMA allowed lists, phase/clock markers, gaps, errors and exhausted bounds.
  Default cadence is one second with phase-change wakeups; limits are 512 tasks,
  8,192 samples, 32 MiB sample bytes, 16 KiB per read and 100 ms per sample. Brief
  changes can still be missed. NUMA allowed lists are permissions, not page placement.
  Both placement and contention remain `unproven`; no qualified measurement,
  clean-host witness, resource authority or new grading rule was created. GPU and
  existing native/profile observation paths are unchanged.
- Main independently verified **43 passed, 8 subtests passed in 0.54s**; isolated
  verification was 43 passed/8 subtests in 0.26s, with Ruff and diff checks clean.
  Tests use synthetic procfs and mocked serving, not inference. A ten-read,
  one-task self-process check took median 0.0924 ms/max 0.3550 ms per sample;
  this is not a full-width inference-overhead measurement.
- Archive coverage is real but belief wiring is not: `ServingComparison.to_dict`
  preserves the full row through `Outcome.to_attempt` and `archive.record` into
  `ExperimentStore.record`'s JSON payload. This direct path emits no
  `belief_capture`/`belief_measurements`. The existing unified-arm reader requires
  its original planned/native carrier and cannot be asserted to cover these rows.
  The source-table/task draft files this precise prospective gap as
  **VB-AK-LEGACY-SERVING**; historical records must not be backfilled with today's
  observations or identities. AKU-12b remains open for actual monitored acceptance.

## Enrolled-target connector published for the existing loop CLI

- Research source `1f2d93aa` / main `195c4ea5` adds the paired
  `--resolved-campaign` / `--target-id` options to the existing `loop/run.py` CLI,
  using `legacy_targets.py`; no replacement runner was introduced. Selection
  preserves original campaign/request/manifest and target identity in planner
  context and status, and binds the selected target into epoch identity.
- The CPU route checks the existing resolved serving workload against that
  enrolled target. GPU selection is explicitly labelled `legacy_gpu_screen`,
  not execution of an enrolled serving recipe. Unselected legacy inputs remain
  supported. Selection confers neither artifact verification nor admission.
- Main independently verified the focused combined source with **68 passed in
  1.38s**. This checkpoint is target-to-existing-CLI wiring only: not serial
  dispatch of all targets, not a restarted live trial and not completion of the
  unified CPU/GPU research or five-loop acceptance goal.

## Direct serving belief write/read path integrated; live feedback not yet connected

- Research source `86179a8c` / main `0a815338` adds the prospective hook in
  `serving.compare`, `serving_beliefs.py` and `archive.record`. Original recipe,
  request and arm inputs are copied before launch; completed native vectors produce
  two observation rows with reps counted as original server launches. Legacy
  unresolved builds retain their supplied paths without a fabricated binary attestation.
- The full comparison/capture stays in `experiments.db`; the existing atomic JSON
  writer exports a bounded original-source document plus its reference receipt under
  `serving-beliefs/`. Export failure is visible on stderr after durable archive and
  does not change the result, undo settlement or relaunch a measurement.
- ROOT `autokernel_legacy_serving.py` reopens and hashes that original source,
  rederives vectors and rows, and plugs into the existing `autokernel_corpus`
  dispatcher/CLI and ClaimTuple ladder. Empty `protocol_id` intentionally yields
  `Judged/Located`. CPU lifecycle facts are retained dependencies, not independent
  measurements or placement/contention warrants; no new grader was added.
- Main independently verified **33 research tests plus 8 subtests in 0.22s** and
  **15 ROOT tests in 0.38s**, including actual compare→SQLite archive→reader→corpus→
  Ledger integration with synthetic observations, replay identity, absent pre-hook
  records, moved/tampered source refusal and non-disruptive capture/export faults.
- This closes **VB-AK-LEGACY-SERVING write/read integration only**. The current live
  process was not reloaded, no live corpus ingestion ran and no planner read-feedback
  consumer was installed by this task. Those next steps are explicit separate tasks;
  no qualified hardware gate, scientific admission, canonical promotion or broader
  five-loop/unified acceptance checkbox was completed. No historical backfill occurred.

## Existing-loop serial target routing published

- Research source `718f410899abcaed72563eb64814d1bfa16c6897` / main
  `d5b3cc96e6fd195b057be633d5ac0b7110bb6bdb` adds `loop.serial_run` around the
  existing pool/measurement/keep owner. One invocation rotates finite batches across
  original enrolled-target argument files; rounds 0 continues until persistent STOP
  or all targets fail. Canonical/per-target history stays in its original store.
- Each child must produce a terminal, same-input `loop-continuation.json` after its
  full original result. It carries actual current/COR build identities; switching
  reuses those verified builds and the original request-bound CPU floor. The normal
  restart bug that paired an old restored COR commit with the current build now
  refuses unless the original COR build is supplied. Existing pruning protection
  and no-copy behavior remain intact. A post-launch status/export failure drains
  the captured child before another target can run.
- Main independently verified 14 serial tests (6.87s), then 82 focused tests on
  integrated PRIMARY (4.55s). Tiny children and synthetic existing-loop providers
  exercise rotation, STOP, keep/resume, missing/mismatched terminal output and
  cleanup. These are not live CPU/GPU serial measurements or qualified results.
  [Operating CLI and argument examples](../../docs/guides/agent-workflows/agent-loop-design.md#operating-the-existing-loop-across-targets)
  retain the original GPU-provenance requirement.

## Second CPU iteration completed; iteration 3 started automatically

- The already-running dedicated GLM trial durably recorded attempt `a88eb190…` as
  `measured_null`: five serving pairs, effect **+1.454288%**, below its unchanged
  **7.801%** floor. Original request/floor digest remains
  `b8475457d62a637a58cbe90e9b66864804122ed713ac14562a5f6c400c5154d0`.
  Worker cleanup returned to `c463f601`; the original loop entered iteration 3
  automatically. No keep or qualified gain; the five-iteration test is unfinished.
- This checkpoint does not claim that the running process loaded the newly
  published serial wrapper or CPU lifecycle/belief hooks. No restart, new hardware
  run, index edit or publication was performed by documentation preparation.

## Serial dashboard support integrated; live configuration unchanged

- Research source `237d82ec` / main `707639d4` adds optional original child batch
  directory/PID and serial routing totals. Integrated ROOT support uses the existing
  `/loop` page and retains canonical champion/history roots. Active child detail
  requires matching target, output directory and PID; old store reports cannot stand
  in for the current child. Router and child freshness remain separate, and the batch
  cursor is explicitly not an iteration or measurement count. STOP, completion and
  all-failed states are distinct.
- Main verified **42 producer tests in 7.72s** and **18 ROOT tests in 2.71s**, including
  tiny owned children and the actual reader/page path. Three broader pre-existing
  rendering expectations were reproduced on untouched ROOT `6c5f8c75`; those tests
  were not changed. ROOT code is included in this owning checkpoint publication.
- No dashboard environment or process reload, current GLM switch, live serial
  hardware proof or qualified gain is claimed. Broader mixed-target acceptance
  remains open.

## Scoped direct-serving planner feedback integrated; live trial unchanged

- Research source `8360d3e1` / main `ba5abca4` connects the existing archive's new
  receipt callback to one synchronous serving-feedback bridge. ROOT uses its strict
  original-source reader and existing Ledger/fold/query functions; no new service,
  carrier schema, grader or campaign identity was introduced.
- A bounded startup scan is followed by newly exported receipt IDs, not a repeated
  full-corpus ingest. The private ledger is `serving-beliefs/feedback-ledger.jsonl`
  under the selected original store. Context is limited to 12 rows/32 KiB, source
  reads to 128 MiB per query and ledger replay to 8 MiB/8192 frames; bounds/errors
  remain visible rather than claiming complete coverage. Query/export faults do not
  change durable experiments. A later export can recover transient initialization.
- Original model descriptor, recipe/request digests, epoch and anchor identity
  scope numeric observations. A keep reuses the actual comparison's rebound anchor
  identity, without extra prompt-time hashing. Existing historical recall remains
  unchanged: a null is worth remembering even without qualified measurement grade.
  `Judged/Located` is observation status, never a qualified gain or promotion warrant.
- Main independently verified **28 ROOT tests in 0.63s** and **55 research tests in
  4.17s**. The actual existing-loop→archive→ingest→context path includes synthetic
  provider/measurement boundaries, changed post-keep bytes, the subsequent null,
  restart without duplicate frames, scope/source refusals and nonfatal reader faults.
- Future owning starts should pass
  `--belief-root-repo /mnt/raid0/llm/worktrees/mains/autokernel-unified-20260908`;
  the existing operating guide and CPU serial-argument example now show it. No
  current live PID was reloaded, no real post-hook hardware/live ingest was proven,
  and no qualified hardware or broader acceptance checkbox was completed.

## Owned target roster and exact GPU serving integrated; live trial unchanged

- Research source `8f67076c` / main `d5705634` connects ready resolved production
  and candidate targets to the existing serial runner using one ownership map.
  It derives model/recipe/actor defaults and target-specific store/lane roots;
  original owned source, branch, anchor and frozen requests remain explicit.
  Existing `--target-args`, original continuation/COR identities, STOP and completed
  restart without relaunch remain supported. Missing ownership/artifacts are reported,
  not silently counted as target coverage.
- Explicit enrolled GPU serving now uses the original resolved launch and frozen
  requests through `serving.compare` and request-bound floors. Experimental GPU
  candidates do not become the canonical champion; canonical COR/accumulator paths
  and ordinary GPU cheap screens retain their distinct semantics. Shared workload/
  resource validation binds the supported GPU route, host CPUs and build
  jobs. Existing CPU-region/GPU claims and declared affinity cover owned work;
  generated serial children additionally use existing `taskset` confinement.
- Main independently verified **84 focused tests in 7.34s** and clean diff checks.
  Tests exercise actual CLI/dry-run/serial children and original restart paths with
  synthetic hardware/provider boundaries; these are not hardware measurements.
- Read-only generation against
  `/mnt/raid0/llm/tmp/aku12a-glm53-roster-inputs-20260910/campaign-resolved.json`
  (SHA-256 `1300442ea9f96f5a02eaa443aa56823e71aeb49a43d0025a1f8782ea2b3e4c1a`)
  selected **1 ready GLM seed and explicitly reported 17 unavailable targets**.
  The seed environment was corrected to the original launch's 14 effective entries,
  excluding only arm-specific `LD_LIBRARY_PATH`; the original prompts were unchanged.
  Generation retained the existing trial store/anchor and CPUs 0–95, created no
  output directories and did not hash model/binary bytes or invoke the real owner.
- Main subsequently ran the **real PRIMARY serial owner dry-run**, exit **0 in
  0.19s**, during iteration 4 authoring rather than its measurement window. It used
  the corrected resolved campaign, original `REAL-GLM-OWNED.json`,
  `--batch-iterations 1 --rounds 1`, state path
  `/mnt/raid0/llm/tmp/aku12a-glm53-roster-dry-run-20260910` and PRIMARY `EPYC_ROOT_REPO`.
  Original c463 startup identity was verified, the actual model census reported
  n_embd=4096, and the existing request-bound **7.801% floor** reopened as verified.
  This is startup/input proof, not a new performance result. No builds, resource
  claims, inference or current live-PID reload occurred. Generated planner effort
  defaults to high; the next GLM start must retain the original medium actor efforts
  through the optional common-args override. The current controller was unchanged.
- [Operating guide](../../docs/guides/agent-workflows/agent-loop-design.md#operating-the-existing-loop-across-targets)
  links the research roster contract. Scheduling remains serial round-robin, not
  mechanism-aware concurrent scheduling; real mixed-target acceptance and qualified
  correctness/performance/promotion gates remain open in AKU-12b.

## CPU profile connected to the existing loop and actual actor prompt

- Research `a1cdfe06` / main `203484a1` reuses the existing owned perf capture for
  the current CPU binary and original frozen request. Profiling runs separately
  at startup and after a source keep, not after nulls; acceptance A/B and floor
  semantics are unchanged. Actual actor prompts now receive observed symbol periods,
  their fractions and the original record, or an explicit unavailable reason.
- ROOT's existing profile measurement projector and corpus route consume the direct
  observation without issuing an integrity or PROFILE_VERIFIED row. Historical
  producer support remains; current exact source identity includes system Python 3.13.
- Main primary checks: 41 research tests in 7.07s and 40 ROOT tests in 6.41s.
  Worker broader checks: 114 research and 40 ROOT. Tests use tiny HTTP children and
  synthetic perf, not hardware profiling. An initial main ROOT run used the older
  orchestrator Python 3.11 producer and was correctly refused by the exact source
  identity check (11 failed, 29 passed); rerunning with the actual system producer
  passed without broadening identity acceptance.
- Two handoff subtasks completed. No live controller reload, hardware profile,
  production change, qualified gain or full handoff completion is claimed.

## Existing-loop runtime observation integration

- Integrated CPU same-binary runtime arms into the existing loop and serving owner:
  source authoring, diff critic, builds and source promotion are bypassed. Actual
  candidate environment/topology reaches correctness and measurement, while source
  routes retain their existing behavior. Source-only floors cannot certify a changed
  runtime recipe.
- Runtime results are explicitly `runtime_observed`, with original per-arm recipe
  identities in the existing belief adapter and measured counts on the dashboard.
  This is observation support, not runtime keeper/admission completion; prevalidated
  deterministic routing and accepted recipe retention/continuation remain in progress.
- Primary verification: 72 research tests passed in 4.84s; 10 ROOT legacy-serving
  reader/runtime-render tests passed in 4.42s. Tiny HTTP fixtures, no hardware run.
- Live PID1380863 remained running, four completed original five-pair comparisons;
  iteration4 +1.248272% was another measured null below the unchanged 7.801% floor.
  Fifth iteration is in flight. No reload, recalibration or production modification.

## CPU factual noise and original invalid-arm reschedule

- Research `64923e9f` / main `591616c0` extends the existing CPU sampler with bounded
  during-lifecycle CPU/load, swap, memory-PSI and non-target activity facts. Ordinary
  build/host noise never blocks; no numeric pressure gate or inference-name classifier.
- Two samples of the same TID/start outside the original CPU list, or an original
  PID/start substitution, invalidate after owned teardown. The existing experiment
  store retains `measurement_invalid` with original arm/request/build/lifecycle facts,
  not a null or an accepted measurement. The existing tail archives first, charges one
  additional iteration draw, and can retry that exact failed server launch once without
  resetting, rebuilding, reauthoring, profiling, recalibrating or repeating valid arms.
  STOP, exhausted budget, repeated invalidity and unresolved cleanup prevent retry.
- Source and runtime actual-main fixtures prove five budgeted outcomes with one invalid
  and four measured/exported comparisons. Main verification: 39 joined tests in 6.75s
  and 41 ROOT profile/corpus tests in 6.51s. Worker final set: 185 tests plus 16 subtests
  in 6.55s; ROOT 41 in 6.92s. The additive exact current profile source pin preserves
  both historical closures and original projected identity under system Python 3.13.
- One completed handoff subtask; no live process reload, hardware run, foreign signal,
  qualified gain or full contamination/restart recovery claim. In-memory continuation
  does not restore interrupted work after restart. README freshness check exited0 with
  no warnings. Boundary bus drain still refuses the absent `autokernel-unified-20260908`
  roster identity; no substitute identity, index edits or wiki sweep were introduced.

## Serial completed-child restart repair

- Fixed a concrete restart refusal: a child could finish and write its continuation,
  then the router could crash before clearing active state. Startup now reopens the
  exact original target/arguments/batch result and verifies original process absence
  or terminal identity, recording exit-status-unavailable rather than inventing exit0.
- Reconciles once without rerunning completed work; preserves STOP, refuses live or
  unreadable child ownership, and retains state/logs when terminal evidence is missing.
  Existing process identity helper is used read-only; no foreign signals or adoption.
- Main primary tests: 26 passed in 10.27s, including actual tiny child completion,
  crash/restart, idempotence, legacy absent-start identity, live-child refusal and
  tampered/missing-result cases. No hardware/reload or unfinished-work recovery claim.

## Preserve interrupted source before lane reset

- Fixed source loss when STOP arrives after authoring but before gate archival.
  The existing reset callback now archives original HEAD and exact tracked changes,
  plus bounded untracked kernel-source text, before the unchanged lane reset.
- Hash-qualified immutable patch names prevent repeated mechanism/lane overwrites;
  tracked recipe/docs changes and historical archives remain intact. No arbitrary
  untracked files or build artifacts are retained. Archive failure prevents reset.
- Main 56 focused tests passed in 5.75s, including actual patch application against
  original HEAD and exact empty/new/no-final-newline/CRLF file recovery. Existing CPU
  retry tests pass with new archive names. Build pruning and execution gates unchanged.
- Publication isolates this completed fix from pending owner/scheduler integration.
  No live reload, hardware measurement, or automatic interrupted-measurement resume.

## Serial dashboard producer/reader compatibility repair

- The completed-child restart fix added original process identity to serial active
  status. ROOT's closed six-key reader rejected that new field. Reader now accepts
  optional exact PID/start/boot identity matching the declared child PID, while keeping
  old payloads and exact batch/store/target joining. No scheduler-private fields admitted.
- Main actual producer-to-reader-to-browser-render suite: 26 passed in 3.08s, including
  canonical-history preservation and malformed optional-identity rejection. No inference
  reload or claim that a new hardware serial campaign was run.

## Five-loop GLM CPU trial completed

- Original exec21102 exited0 after248.2minutes: five actual source/build/correctness/
  serving-A/B iterations, five pairs each, zero keeps. Mechanisms/effects: paired-y
  +0.950164%, paired-x +1.454288%, r8-vector-transpose +1.181050%, fa-f16-kpack-16x16
  +1.248272%, q82x4-avx512-quant +0.332447%. All are measured_null against unchanged
  7.801% floor; experimental anchor remains c463f601bd39, no production promotion.
- Original loop-run artifact SHA256a489ee01fa6807e202ec69c44d2d59c2ae2c3be28fa766c48ea90d3b099ce408
  at `/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-output-continuation/loop-run.json`.
  Original request-bound floor remains SHA256479db985de12b4351f3d614fbd73341d1a97a5c11e2183415750e63e077d3cba.
- Main verified parent1380863 and final-iteration servers3777944,3784432,3792247,
  3798760,3805300,3811107,3819986,3825520,3834097,3844014 absent. Dashboard fresh,
  five measured/zero remaining, original2397 historical attempts still visible.
- Final worker lane retains rejected iqk_quantize_min.cpp source; not reset or promoted.
  This old loaded controller predates later continuation/target/telemetry/feedback hooks;
  missing continuation in its output does not establish a defect in current source.
- Completed actual five-loop workflow, not qualified performance/placement evidence,
  mixed CPU/GPU acceptance, or full handoff completion. No experiment rerun initiated.

### Split-GGUF production enrollment association

- Actual production inventory review found `_artifact_rows` associated only the argv
  shard, even when all sibling pins were verified. The exporter now expands exact
  five-digit split families for both models and drafters, requiring every sibling.
  Single-file behavior remains unchanged; no glob, hash pass or production write added.
- Main verification: 20 enrollment tests passed in 34.50s using the canonical
  orchestrator Python environment and ORCHESTRATOR_STACK_REEXEC=1. Tests cover complete
  and missing shards for both uses; existing export tests remain green. Diff check clean.
- GitNexus impact LOW (three upstream nodes). Requested stale-index refresh exited139;
  direct caller review remains the evidence, not a claimed successful re-index.
- README freshness check clean. Bus drain refused the existing session identifier as
  unregistered; no other session identity was substituted. One completed checkbox added.
  Broader scheduler/runtime/recall integration remains active; no additional hardware run.

### Shared historical mechanism recall integrated

- Existing serial rosters automatically include canonical and sibling target stores;
  standalone runs can supply repeated --shared-history-root. The existing SQLite store
  gains a read-only mode without schema writes. Missing/corrupt sources are advisory.
- Selection reads bounded keep/measured/other pools, avoiding transient-flood starvation,
  and rotates roots using the original serial batch identity across fresh child processes.
  Current local recall remains unchanged. Shared suggestions preserve original scope and
  caveats, redact structured magnitudes, and cannot become local gain/refutation evidence.
- Main combined verification: 104 tests passed in 2.67s, including held-claim compatibility.
  Actual canonical DB read returned one keep, three measured nulls, one refusal, no errors.
  No model process, schema migration or historical evidence backfill was performed.
- Six-file accepted source packet SHA256
  38ca85e35b8c214a214d14e1869caa7569f7a0603e8eb6400aabc77872b1f7c7.
  Publication excludes pending resource/scheduler hunks in shared run.py. One completed
  checkbox added; transfer validation, runtime admission and mixed-target gates remain open.

### Dashboard terminal report presentation

- Reproduced complete GLM 5/5 report aging into STALE and retaining a measuring step.
  Reader now supplies a presentation-only terminal step and explains that a declared
  completed producer needs no further heartbeat. Page shows FINAL REPORT/FAILED REPORT
  with original age; raw timestamp, freshness and producer step remain unchanged.
- Main 35 actual producer/reader/JavaScript tests passed in 1.96s, no skips. Running
  router/completed child remains running at router level; future timestamps remain
  malformed. Actual retained GLM artifact reads Run complete — final report, 5/5.
- Source packet SHA2562c86e349cdd01c689bbf087ccc6c3402f530ff8bfc18356f29076f580ef0b005.
  No research restart, benchmark or historical-result rewrite. One completed checkbox.

### Split-model importer follow-through

- Downstream review of the now-complete shard list found singular campaign and launch
  artifact projections overwrote the entry shard with the final sibling. Both now
  choose the exact argv entry when multiple model/drafter pins exist; original exported
  dependency pins remain intact. Main 21 enrollment tests passed in 0.21s, including
  actual split-model registry and resolved-launch projections. Impact LOW, two callers.
- Production export hit stale launch-manifest priors. Canonical compiler regenerated
  priors in isolated acceptance/autokernel-production-export-826008df-20260910, preserving
  primary generated-file edits. Actual --verify-artifacts export is running in exec86402;
  this option rereads pinned files. No completion claim or duplicate export launched.
- Prior dashboard fix is live: supervisor restarted hub as PID3894694 after source edit,
  API reports final complete5/5/history2397 and panel healthOK. Source/raw reports unchanged.

### Existing serial scheduling and original resource accounting

- Connected existing pure scheduler to serial selection, continuation and terminal
  accounting. Original CPU/GPU flock contexts publish actual held intervals after release;
  unequal CPU/GPU intervals partition resource cost without double-counting the attempt.
  Failed children retain released-claim evidence; terminal restart accounts before selection.
- Main review corrected fixed proposal reuse (continuous runs), failed-target starvation,
  optional-manifest-only setup friction and mutable orchestrator package imports. Derived
  owned-roster policy is printed by dry run: one iteration per stage, whole-invocation bound
  build_timeout+4*stage_timeout, finite runs rounds*targets attempts, continuous1000 attempts,
  corresponding charged-time budget. Memory reservation0 means undeclared, not observed0.
- Main 101 combined checks passed in 8.69s; actual original GLM roster --dry-run exited0
  in 0.23s with derived selection and unchanged7.801 request-bound floor. No hardware run.
- Connector v3 SHA075d02f5bc75dfef95cc27df43ed5677a9433cbf4741a0cbcbba9e1c0b22247a,
  composed with original held-owner v2 and component accounting. Old continuationv1 retained;
  v2 carries original resource evidence. Shared recall and bounded build pruning preserved.
  One completed checkbox; reduced-scope transfer, runtime banking and shared candidate work
  remain active. Original five-loop controller predates this integration.

### Actual production recipe compatibility

- Original production export process86402 completed exit0 with artifact verification:
  seven ready CPU/GPU targets, zero waiting, twelve unsupported. Original export
  `/mnt/raid0/llm/tmp/aku-production-enrollment-20260910/production-export.json`
  SHA25641c1380b1664f36de167eea6225fd52a2d9b4a99e1dbeeb6e17770b3e15061d6.
  The actual resolver then exposed unsupported emitted flags and omitted-ubatch handling.
- Parser now preserves --draft-p-min, --threads-draft and --log-colors; rejects duplicate
  probability aliases/nonfinite probabilities/invalid values. Omitted -ub is512 per frozen
  v9 common.h, not2048; original argv bytes are unchanged. Existing explicit-ub recipes
  are unchanged. Shared parser impactHIGH was reviewed before the bounded compatibility fix.
- Actual frozen GPU DSO dependency inspection found eight ROCm runtime libraries absent
  from the original supplied pins. Supplemental artifact-pins-with-rocm.json and
  production-export-with-rocm.json retain original files and add measured library hashes;
  supplemental export uses verification_not_requested, not a second full-model verification.
  All seven exported production commands now resolve. No inference or builds launched.
- Main112 parser/enrollment/profile tests passed32.16s and32 ROOT producer/reader tests
  passed5.71s with EPYC_RESEARCH_ROOT explicitly set (initial wrong variable skipped tests,
  not counted). CPU profile source pin926f9cce5fa92598e5120006611be5d97189952907af06c7561f6f5628c3b2ba
  uses the actual autokernel import path; earlier three accepted pins retained. No grading
  rule changed. One completed checkbox; mixed-target execution remains separate active work.

### Real GPU build rebinding

- CPU+GPU dry-run preparation exposed original10125 DSO basenames not existing in retained
  champion10301. Fixed the existing run._cpu_arm helper, not the production tree: preserve
  exact existing filenames; on missing version resolve actual original ELF SONAME through
  candidate build/bin, require containment and matching candidate SONAME, hash actual bytes.
  Fixed external libraries remain untouched. GitNexus impactLOW, six upstream uses.
- Main42 actual tiny-ELF/CPU/GPU/serial tests passed7.56s. Actual frozen production GPU
  recipe rebound to build-fold-ef81196d5 matches the separately pinned candidate launch
  exactly across16 DSOs. No inference, kernel rebuild, historical result rewrite or
  artifact provenance invented. One completed checkbox.
- Prospective mixed dry-run inputs live in
  `/mnt/raid0/llm/tmp/aku-cpu-gpu-dryrun-inputs-20260910`. They explicitly include CPU184–191
  for the production GPU recipe alongside GLM CPU0–95 and use new text requests (not GLM
  token IDs) for GPU. These are dry-run declarations, not a live allocation or performance
  measurement. Actual roster invocation exposed draft-mtp/self_draft enrollment mismatch;
  the existing implementation worker owns its correction together with the scheduled-child
  import bug. Original GLM inputs and historical stores remain unchanged.

### Actual CPU+GPU owned-roster dry run passes

- Worker launch packet SHA28bcbb98f4394e627f1ee79c76a6c976fef4892f6217d4542fa3d7bbcc318385
  fixes production mechanism naming at import (draft-mtp -> self_draft/external_draft,
  matching existing recipe semantics) and scheduled-child topology import. Both symbols
  impactLOW; original export/argv retained. Main75 joined tests pass1.47s.
- Actual dual dry run exited0 in0.44s with original GLM c463 and canonicalGPU ef811 retained
  source/builds; medium actors; automatically derived scheduler. CPU original floor7.801
  verified, new prospective GPU request floorabsent and hand-built provenance warning
  remain explicit. No model process, state directory or GPU store created. The prospective
  GPU requests use the actual recipe's sampling/decode settings; they do not reuse GLM
  token IDs or historical GPU measurements. Initial preparation-only JSON float formatting
  and prompt/template mismatch corrected before the successful run; neither was a loop bug.
- Full command/output retained at
  `/mnt/raid0/llm/tmp/aku-cpu-gpu-dryrun-inputs-20260910/dry-run.log`, SHA256
  130ba42ffe18405efe4824c3be5de2458189986a3ac88633e1c9f821e098d493.
  One completed checkbox. Runtime admission, automatic reduced-to-full confirmation,
  shared candidate integration and applicable live gates remain active work, not completion.

### All-target startup review and inherited CPU affinity

- Expanded actual prospective inputs to all seven exported production workloads plus GLM
  under `/mnt/raid0/llm/tmp/aku-full-roster-dryrun-inputs-20260910`. Explicit fullsmt resource
  declaration includes the eval_batch CPU0-47,96-143 placement; no hardware claim was made.
  The full serial dry run exposed shared-source-root rejection, assigned to the existing
  shared-candidate worker. It is not an unavailable model or a successful full-roster run.
- Individual original-owner preflights exposed worker_fast's inherited-affinity rejection.
  run now constructs its effective canonical taskset from explicit enrolled CPU resources,
  retaining original snapshot provenance and unchanged workload/environment/artifact bytes.
  Existing explicit-affinity paths are unchanged; unscoped standalone input still refuses.
  Main70 checks passed3.04s, impactLOW1. CPU profile source pin926f9cce... remains unchanged.
- All8 actual individual preflights now pass. Full command/output:
  `/mnt/raid0/llm/tmp/aku-full-roster-dryrun-inputs-20260910/individual-preflights.log`, SHA256
  4c6404ee1174177dac89dab0f017a1d48ee1c6755c2a4360f62a0cc6e2677101.
  New production request floors remain absent; original GLM7.801 floor unchanged. No model
  launch, kernel build, source fork or fabricated build receipt. One completed checkbox.
- Main reviewed the915-line reduced-screen packet and82 composed tests passed10.59s on
  current50a9. Publication awaits its automatic scheduler/resource join, not more core tests.
  Review also found production-frontier provenance was lost, allowing finite budget to
  spend on cheap CPU screens without GPU coverage; lifecycle worker owns the narrow existing
  coverage-policy connection. Existing historical ControlHarness supports a separate Qwen
  CPU replay frame, so lack of a GLM-specific historical band is not backend unavailability.
  Runtime and lifecycle workers are wiring that original runner, not transferring old gains.

### Automatic reduced CPU screening integrated

- Accepted the seven-file packet on research34b900ae after source review and exact hash
  verification (packet SHA256 b48a23014b6ffbd951561cd6819c8c5e6ef9e6ea7e5c13e5ee6b579d70a9f3c6).
  Original run/pool/build/promotion remains the owner; no replacement scheduler or ledger.
  Selection freezes quarter/half/full geometry before scheduling. Both measurement arms
  use the same scoped recipe and its own calibration. Original full recipe stays separate.
- Reduced positive retains the exact source patch and candidate build as keep_candidate.
  Full confirmation uses that build and original requests, reruns the applicable checks,
  and promotes only on an ordinary full keep. Pending aliases cannot supersede it.
  Unaffordable confirmation is visible scope debt, not another reduced experiment.
  Existing production coverage receives actual enrolled frontier identities; finite
  four-attempt regression proves GPU coverage despite cheaper CPU quarter stages.
- Main113 tests passed10.64s, including old CPU/GPU runs, scheduler, retained-build and
  affinity cases. Exact actual GLM --scheduler-selection dry run in primary exited0
  in0.21s: CPU0-23, quarter recipe, absent request-bound floor, sol-medium actors.
  Inputs: /mnt/raid0/llm/tmp/aku-cpu-screen-selected-dryrun-20260910/argv.json.
  No inference/build launched. Fixtures do not prove hardware transfer or coexistence.
  One completed checkbox added; broader runtime admission/shared-source integration
  remains active. No new operator decision or speculative gate added.

### Shared-source continuation and full-roster startup

- Accepted focused seven-file packet SHA256
  7fac0953bfa034d346d014fb1868713d840d4f5e8e95a4a298d7ff55ad8039cc on research98da9b22.
  Main corrected its doc's leftover staging claim: this slice has no fold consumer,
  receipt scaffolding or canonical promotion. Shared exact worktree/branch is serial;
  each target keeps its own store, requests and history while using the latest
  digest-bound source/build continuation. No checkout copy or rebuild just to switch.
- Main118 integrated checks passed12.72s. Actual-owner fixture executes synthetic
  A source/build keep, B newer keep, and A startup combining its older personal resume
  with B's newer exact anchor. Original CPU/GPU and partition-screening paths also pass.
- Actual full8 serial dry run passed in primary. Original GLM7.801 floor retained;
  all new production floors absent; canonical GPU hand-built provenance warning remains
  explicit. No state directory, inference or build created. Command/output retained at
  /mnt/raid0/llm/tmp/aku-full-roster-dryrun-inputs-20260910/shared-source-primary-dry-run.log,
  SHA256 b704dc907b9021f267c80e9be5552825581e856df3db2e14f2b3673c712c605a.
- One completed checkbox. Runtime receipt transport and actual whole-candidate fold
  remain assigned integration work, not inferred complete from this startup proof.
