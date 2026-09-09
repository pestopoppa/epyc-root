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

### Accepted ExperimentPlan structural boundary

- AKU-04a: the requested corrections are now reviewed and **72 focused tests pass** in main's run.
  The shared immutable plan freezes class/phase, identities, unit/prompt membership, pairing, order,
  fixed-N stopping and intended use. Invalid/partial pairs are excluded together and empty input is
  incomplete. Direct dataclass inputs and forged/foreign unit views are revalidated.
- Observation-to-release laundering, strict-search headlines, and BASELINE production/certificate uses
  refuse. Nomination remains policy-undefined until the exact A2 semantic attestation adapter exists;
  claim-bearing uses require the unimplemented shared-grade/registered-protocol adapters. Structural
  completeness is not measurement/independence warrant; every offline output denies execution authority.
- Calibration has exact registered replay and treatment-aware applicability seams, n/unit/interval
  structure, separate raw-replay versus plan/rule caches, and no cached transient callback failures.
  No estimator, acceptance threshold, statistical power classifier or bounded-null rule was invented.
- The source/recipe root checkpoint is `59d86f76`, main merge `fb70d74e`. Service/control drafts are
  still unpublished: main reproduced a closed incarnation accepting a command while its replacement
  held the lock in a disposable test store, and required lifetime fencing, validated event-order replay,
  complete resolved-config identity, append-fault recovery and bounded HTTP shutdown corrections.
  Candidate manifests and scoped retrieval/transfer are the other disjoint sol-medium assignments.
- ExperimentPlan source is published as research `93e049f1`, main merge `027e9ec7`. Only the five
  reviewed plan/CLI/test/documentation files were included; service and candidate drafts remain outside
  this checkpoint. Publication is not activation or scientific validation.
- Its root handoff/progress checkpoint is `2712b6ae`, main merge `f2d125a2`.

### Candidate contract accepted; control/evidence review in progress

- AKU-05b is now accepted: 28 focused tests within **159 adjacent tests** pass in main's run. Candidate
  source/build sets and per-target exact execution identities are separate, both candidate/comparator
  rows bind precisely, and complete carried production obligations/LOO cannot be bypassed with loaded
  state. Actual registered evidence verification remains required and is not supplied by JSON labels.
- Main required and reviewed monotonic gain-trigger generations, exact duplicate batch starts,
  preservation of keeps integrated after a batch was frozen, typed verifier failures, and optional
  seed rows remaining pending without blocking required production rows. Validation debt persists
  until trusted advancement; a completed gate's cadence reset is not validation. These are pure offline
  transitions and CLI validation, not journal transactions, live measurements or promotion authority.
- Candidate source is published as research `378fdc9c`, main merge `bf08bc25`; its five reviewed files
  are frozen. That worker is now implementing the optional planned-serving consumer using the actual
  launcher with fake processes/providers; the other two workers retain control/evidence ownership.
- The control draft fixes the reproduced closed-writer bug, normalizes the whole resolved campaign,
  validates replay order and poisons uncertain append failures until recovery. Main requested a final
  pass on named-lock replacement, nested store identity, slow-client shutdown and observer-independent
  producer heartbeat. A socket's per-read timeout is not a total service-shutdown deadline.
- Scoped retrieval/transfer is the third isolated draft. Main review requires local quarantine/outage
  fences to invalidate cached certificates, unknown generations to stay unknown, mandatory applicable
  conflicts before ranking, and complete retrieval to remain distinct from positive use authority.
  No draft is published merely because its happy-path fixtures pass.

### Accepted management service; native consumers continue

- The preceding candidate root checkpoint is `bfe58955`, main merge `52bf582f`.
- AKU-07a now has a real opt-in controller/HTTP/CLI consumer over the existing journal: full resolved
  config binding, persistent supervisor incarnation/stream, strict control replay and idempotent
  durable acceptance, one pinned store/named lock, in-process serialization, closed-writer fencing and
  poisoned uncertain writes. Resume without a trusted prerequisite remains waiting, not executable.
- The service owns initial/periodic snapshot publication without observer traffic. Public transport
  health performs no journal read or fsync; snapshot/commands require authentication. Slow-client
  teardown closes captured sockets and shares a bounded join deadline. A blocked synchronous filesystem
  call cannot be forcibly bounded: stop refuses and retains ownership when its threads remain.
- Main's final test run passed **217 tests and 15 subtests**, with **69 focused control/service tests**
  included. A separate 256-case nested-field mutation sweep returned no uncaught validator exceptions.
  Main caught resume-state list/dict exceptions after the worker's first malformed-input fixtures; these
  are now regression-tested. Producer identity uses stable loaded bytecode projections, not adaptive
  marshal bytes or changing on-disk mtimes, and honestly excludes unmeasured package dependencies.
- Scoped-evidence review reproduced another cache failure: a newly added refutation left a previously
  supported cached decision eligible because only explicit invalidation events advanced its local
  fences. The worker must bind relevant evidence-set changes and broader-support dependencies without
  global cache churn. This draft is not accepted. Planned serving is addressing exact continuation
  membership/order and preserving partial slot observations before any completion callback.
- Root GitNexus is refreshed at `52bf582f`; research was refreshed at `bf08bc25`. The existing dashboard
  loop snapshot has one reported upstream consumer (LOW), and `_measure_once` has comparison/calibration
  callers (LOW); manually reviewed injected callbacks are additional edges the graph does not capture.
- The accepted management source is published as research `30316f05`, main merge `babf5b9b`. Only its
  six reviewed files were included; evidence/serving drafts stayed outside the checkpoint. That worker
  now owns durable candidate transactions and the narrow serialized controller/journal seam; the other
  two workers retain scoped evidence and planned serving. No service was deployed or activated.

### Frozen planned-serving consumer accepted

- The management root checkpoint is `94b8b93a`, main merge `40cfe499`.
- AKU-04b now connects immutable plan/recipes/prompts to the existing `_measure_once` path without
  rebuilding for runtime arms. Main's **117 tests and 3 subtests** pass across serving, resolved recipe,
  ExperimentPlan and planned consumer. Focused worker coverage is 26 tests plus 3 subtests; ruff and
  diff checks pass. The concurrently changing evidence draft prevented a clean full-loop worker run;
  those constructor mismatches were not suppressed or attributed to serving.
- Raw artifacts are retained before provider completion. No failed/missing/nonfinite timing becomes
  zero; native slot errors and warmup are preserved without increasing independent-unit N. Main
  required exact request count/digests before admission, previous-unit membership/prefix validation,
  prior-lineage binding, distinct typed witnesses, and stopping after an invalid unit. Legacy estimator
  and defaults remain unchanged. This is a real launcher consumer tested with fake processes/providers,
  not proof of a deployed enclosing guard or valid live CPU/GPU measurement.
- Research publication: `1d7de099`, main merge `b4d7db7b`; only its five reviewed files were included.
  That worker now owns prospective measurement capture and the root Vidya reader/corpus consumer.
  Candidate transactions retain exclusive journal/controller ownership; the native-kind delta must be
  reviewed/integrated by main, not concurrent worker writes. Existing source registration is reused.
- Production enrollment audit found that canonical command construction itself creates slot-save
  directories, and startup adds environment, placement and pre-eviction behavior beyond argv. A future
  canonical export must be genuinely non-mutating and pin these lifecycle declarations. Nothing was
  imported/launched/pre-evicted or changed in the orchestrator; only source was inspected.

The next consumer integrations are prospective native evidence, durable candidate transactions and the
existing dashboard's campaign surface. A helper is not a completed parent slice until real consumers
and integration acceptance exist. The Vidya source table/task registers the prospective current-loop
measurement hook. Operational journal snapshots are not claim tuples.

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
