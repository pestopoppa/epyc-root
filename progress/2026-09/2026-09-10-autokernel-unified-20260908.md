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
