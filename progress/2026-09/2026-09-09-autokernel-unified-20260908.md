# Unified AutoKernel implementation — 2026-09-09

Owner: `autokernel-unified-20260908`. Operator authorized implementation of
`handoffs/active/autokernel-unified-surface-program.md`, using GPT-5.6-sol medium workers for bounded
execution and main-thread coordination/review. Root lane starts at `088427b0`; research at `1d9733f1`.
Shared/divergent checkouts and frozen kernels were not changed. Implementation is tracked in §9;
source completion, publication, deployment and live acceptance are separate.

## Accepted first slices

- AKU-02a: `Recipe.explicit_unsets` removes inherited treatment values from the actual launched
  environment. Set/unset conflicts, malformed keys and loader-owned overrides refuse. Unset identity
  is immutable, sorted and serialized; empty unset state preserves historical recipe hashes. The
  existing readback path tests both control and treatment. Main reviewed the diff and integration tests.
- AKU-03a: `status.write_json()` now file-syncs, replaces atomically and syncs the containing directory.
  It cleans only its own unpublished temporary file, closes descriptors on failure and propagates
  post-publication durability failures without deleting the new target. Main reviewed implementation
  and injected-failure fixtures; 28 focused tests pass.
- Full current-loop suite after both patches: **611 passed, 59 subtests passed**, 6.88s. These are
  hermetic source tests, not inference measurements or proof of CPU/GPU performance/soak readiness.

## In progress and boundaries

### Enrollment, recovery and worker-status checkpoint

- AKU-01a: immutable explicit-snapshot campaign resolver and offline CLI, with CPU/GPU targets, seed
  alias deduplication, pinned baselines, source identities and independent prerequisite states. Optional
  artifact verification does not grant admission or rewrite identities. Main's focused run: 52 passed.
- AKU-03b: authoritative `LOOP_BUNDLE_SAVED` before derived JSON; v1 import retains the original parsed
  snapshot/provenance, v2 requires validity, missing/corrupt history refuses. External tip movement
  preserves COR/keeps/cadence and labels prior magnitude stale. The current loop and manual serving gate
  use recovery; dry mode cannot create locks or state. Native snapshots confer zero ClaimTuples.
- AKU-09a/b: bounded heartbeat stop/join/lock waits before terminal publication, durable final artifact,
  preserved original exceptions and latest outcomes; both hub render sites distinguish current from
  historical magnitude and unverified threshold signals. 46 focused lifecycle/status tests and 69 root
  render tests / 5 subtests pass. No full browser or live producer was exercised.
- Main integration run after these slices: **707 passed, 59 subtests passed** in the loop suite.
  The changed unified handoff/progress citation check is clean. A separate repository-wide scan flags
  pre-existing citations in other documents (including citation-syntax examples); no claim in this
  implementation checkpoint relies on those entries.

Main rejected and corrected: silently repinned implicit baselines, legacy-as-current validity, stale
magnitude replaced with zero, v1 schema allowing unsafe old-reader fallback, ancestry checked after
import, dry inspection creating locks, an unbounded heartbeat shutdown lock wait, and historical values
labelled measured/current. Those corrections are in accepted code, not deferred recommendations.

First source checkpoint was published as research `93ce4bad` / main merge `585aef6f`, root `ca9a6fb7` /
main merge `8bf6f108`. Publication did not move shared worktrees or restart live processes.
The enrollment/recovery/heartbeat source checkpoint is research `6682e4af`, main merge `f5941fd0`.
Its root dashboard/handoff checkpoint is `971f91fe`, main merge `3eaca1cb`.

### Accepted source-commit isolation

- AKU-05a: `archive.keep()` uses a captured-parent private index and exact accepted paths. Peer staging
  and working bytes are retained; selected paths use the accepted working version rather than a peer's
  differently staged version. Hooks run against the private index; unexpected staged paths refuse.
- Branch/repository identity checks, expected-parent CAS, tracked deletion and post-commit notification
  failure have hermetic tests. Main run: **83 passed, 7 subtests passed** (26 focused cases included).
  The ref update is atomic against its old commit; HEAD binding is immediately rechecked, not claimed
  as an atomic symref-plus-ref transaction. The existing single integration owner remains required.
- A source commit is not proof of build or measurement; module documentation now makes that distinction.
  Cross-repository integration intent, manifests and validation debt are separate upcoming work.

### Accepted resolved recipe consumer

- AKU-02b: immutable snapshot and normalized execution identity, exact injected artifacts/DSO load names,
  effective allowlisted environment and absences, derived CPU/GPU/speculation capability, and real serving
  launcher consumption. The old template hash is preserved. CPU zero VRAM is not a GPU veto; missing
  CPU placement/contention and runtime-set/master-off witness samplers remain explicitly unproven.
- Main review required duplicate argv values, port/path normalization without erasing DSO load names,
  effective inherited readbacks, cross-field capability checks, unknown/mixed GPU-draft refusal and
  pre-launch template/environment integrity. **31 focused tests passed**, followed by **150 adjacent
  tests and 28 subtests**. No real server was launched.
- The loader now actually removes inherited `HSA_OVERRIDE_GFX_VERSION`, as its prior contract required.
  The floor writer uses `status.write_json`. Serving metric documentation now says sum of each slot's
  reported rate; the estimator, legacy identities and acceptance thresholds did not change.

These source/recipe slices are published as research `1b44675d`, main merge `d1611123`; publication
does not deploy the loop or move the shared checkout. Evidence-plan drafts remain unpublished pending
main-requested authority, pairing and calibration-cache corrections; candidate manifests and durable
management controls are the next disjoint assignments.

Resolved launch recipes, independent-unit ExperimentPlan validation and private-index accepted-patch
commits are the next disjoint sol-medium assignments. A helper is not a completed parent slice until
real consumers and integration acceptance exist. The Vidya source table/task registers the prospective
current-loop measurement hook. Operational journal snapshots are not claim tuples.

The built-in dispatcher retained two completed review threads and exhausted its thread limit; one new
sol-medium worker uses it and two use supported `codex exec` with explicit model/medium effort. Main
caps active concurrency at three, owns process handles, reviews proposals and publishes accepted files.
Research GitNexus was rebuilt at the starting commit. Recipe/status changes reported LOW impact;
heartbeat publication has MEDIUM scoped impact and needs race/consumer tests.

Retained gates: frozen production kernel set; no live research relaunch/soak without separate go and
held resources; no measurement-policy amendments; post-BIOS calibration/owning serving protocol.
OP-41 reserves real admission-control implementation to the operator after finalise → promote → reboot.
Main asked whether the new instruction delegates broker-code work now while retaining live gates;
no answer is inferred, and independent implementation continues.

Bus drain rejected this non-roster session ID. No peer identity or coordination file was impersonated.
Per-task wrap-up is being used for checklist/progress/index/publication. No index pruning, handoff
compaction or wiki compilation sweep is performed by this implementation checkpoint.
