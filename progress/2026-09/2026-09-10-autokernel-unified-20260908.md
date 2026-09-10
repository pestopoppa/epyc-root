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
