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

### Scoped evidence boundary accepted

- Planned-serving root checkpoint: `c92af8a4`, main merge `45740647`.
- AKU-08a is accepted after main's **173 tests** pass, including **57 focused evidence tests**. Mandatory
  applicable conflicts precede top-k; raw grades, retrieval completeness and actual support remain
  distinct. Transfer is directed/nontransitive, coexistence victim-directed and noncomposable, and
  reject audits have explicit target-confirmation budgets. No new measurement ladder or execution
  authority is created. The offline CLI uses the real projection and remains non-executing.
- Main reproduced and required fixes for missing generation maps, malformed invalidation quarantine,
  new same-generation findings, new broader refutations, dropped older findings with unchanged maximum
  event number, epoch/rule changes and missing semantic bucket data. Relevant content and semantic
  fences now invalidate cached decisions without global re-query; explicit empty is not missing.
  Serialized state re-derives all fences but restores no trusted Python callback authority. V1 candidate
  lookup limits are explicit; registered verifiers cannot certify an unsupported candidate universe.
- Root index refresh succeeded; research incremental indexing crashed with exit 139. The normal wrapper
  then detected interrupted state and completed its recovery rebuild in 76.9 seconds. No metadata was
  manually deleted. Existing research consumer edits paused during recovery; new-file work continued.
- Prepared a clean orchestrator lane at `5a9442d31b716f64d408ed4a3908fc4bc22c69b1` for future canonical
  enrollment; no application files changed. Default Python3.13 lacked FastAPI; the existing project
  Python3.11 environment ran 23 registry/environment baseline tests successfully (one unrelated
  opentelemetry deprecation warning), so no dependencies were installed. Its index is fresh; canonical
  builder impacts are LOW/4, including live startup/autopilot. Export must preserve default behavior.
- Scoped source is published as research `77e536aa`, main merge `b6cf5f92`. Its worker now owns the
  existing dashboard campaign reader/control consumer and the narrow service transport seams; the
  native capture and candidate transaction workers retain their disjoint ownership. Publication does
  not activate the control service, evidence policy or any inference research.

The next consumer integrations are prospective native evidence, durable candidate transactions and the
existing dashboard's campaign surface. A helper is not a completed parent slice until real consumers
and integration acceptance exist. The Vidya source table/task registers the prospective current-loop
measurement hook. Operational journal snapshots are not claim tuples.

### Candidate/native/dashboard review in progress

- Scoped-evidence root checkpoint published as `8ff376cd`, main merge `c2c56571`. Both owned root and
  research indexes refreshed successfully after that publication; dashboard existing-consumer edits
  were released only after the refresh. No shared checkout was fast-forwarded or restaged.
- Main's isolated candidate regression fixtures reproduced two draft defects: an exact retry of an
  old initialization request rewrites the derived pointer over a newer keep, and a callback can pass
  its active append capability to another thread outside the controller's mutex ownership. Candidate
  acceptance is held for corrections and permanent tests. No real source refs or kernels were touched.
- Review also covers torn immutable-object publication, recoverable partially prepared transactions,
  historical validation reconstruction versus present eligibility, and avoiding whole-history Git/file
  replay on every operation. Native capture is checked against real frozen requests, unit/pair
  membership, lifecycle timestamps and exact raw artifacts before any prospective projection.
- Dashboard review is checking malformed-input totality, clock skew, identity-matched liveness,
  bounded network probes, stale response ordering and memory-only authenticated controls. These are
  ongoing review requirements, not accepted implementations or evidence of live service reliability.
- The four original candidate probes now pass: old-request retries preserve the latest projection,
  cross-thread append capabilities refuse, arbitrary non-owned refs refuse, and frozen llama checkouts
  refuse. Remaining review covers full-history copying on the hot path, speech-tree freeze coverage
  and use of the shared crash-safe artifact store. The transaction slice is not yet accepted.
- Main accepted the **ArtifactStore component for reuse** after **126 tests**, including partial-stage
  crash recovery, two descriptor-leak regressions and same-instance thread exclusion. Cooperative
  directory locks alone did not exclude threads sharing one descriptor; the corrected store also has
  an in-process nested lock. Noncreating verification, exact-inode quarantine/recovery, same-descriptor
  read/fsync, parent durability and pre-publication finite-JSON checks are covered. Native producer,
  adapter and controller-journal integration remain separate review boundaries.
- Three additional root adapter probes exposed native process-identity mismatch, substitution of a
  different manifest prompt, and an uncaught malformed diagnostic payload. Positive fixtures also
  needed the complete producer plan/observation contract. The worker is correcting these plus exact
  interval/unit derivation and conflicting-carrier deduplication; no real corpus was ingested.
- Main independently reproduced the three preexisting INF70 adapter-test failures: stale expectations
  equated recorded hash/presence with verified attestation despite SC69. The historical adapter, grader
  and tests were unchanged from the lane base. A narrowly scoped expectation correction is assigned;
  no historical in-window witness or stronger measurement warrant will be invented.

### Candidate transactions and prospective evidence accepted

- Main accepted AKU-04c/05c after **382 tests and 15 subtests**, including Journal/recovery, the real
  planned-serving consumer, six candidate/cache adversarial probes and four artifact-store probes.
  Public cache aliases/setters no longer mutate authoritative state. The new shared store provides
  no-overwrite, byte-verified, fsynced immutable publication and recoverable partial staging. Candidate
  phases are durable INTENT/PREPARED/COMMITTED; exact retries preserve the latest projection, and
  historical state does not restore trusted verifier authority. All frozen kernel paths/branches refuse.
- Research source checkpoint **82ec8a11**, main merge **54c1f0fd**. No shared checkout, kernel, service
  or live research was changed. The next candidate worker task is actual controller-native arm capture;
  existing journal/controller edits wait for publication/index refresh, while new helper work proceeds.
- Main accepted AKU-08b after **90 focused tests**, including actual producer→reader conformance and
  three independently reproduced tamper/malformed cases. Full Vidya: **1,044 passed, 2 skipped** under
  default fixture configuration; the skipped research conformance case passed in the explicit-root run.
  The other skip requires an orchestrator repo location not present in that test's default context.
  Strict reader/corpus rederive complete closed native inputs and stored bytes; conflicting carriers
  sharing one full measurement ID emit neither. Only this native family deduplicates. Three stale
  INF70 expectations now reflect SC69's actual-byte-verification requirement; no grader or historical
  evidence was changed. No real corpus was ingested.
- Producer supports serving/process/level/median only and keeps unknown environment/placement or absent
  GPU residency diagnostic. Loaded evaluator identity, actual lifecycle samplers, native journal feed
  and registered current-use policy remain required. Source/schema success is not measured performance.
- The enrollment worker now owns the prepared orchestrator lane and a bounded non-mutating canonical
  exporter→research resolver task. The default launcher remains unchanged; no imported process manager,
  pre-eviction, build or inference is authorized. Dashboard final corrections remain separately reviewed.
- README freshness check emitted no warnings. Bus remains unavailable to this non-roster identity;
  no peer identity or coordination file is impersonated.

### Next consumer review boundary

- Root prospective evidence checkpoint **01710e5f**, main merge **5063370c**. Both owned indexes are
  fresh after normal wrapper runs; research incremental indexing again exited 139 and the wrapper's
  own full-recovery rebuild succeeded in 78 seconds. No manual metadata deletion occurred.
- Main's full dashboard-adjacent run found **328 passing tests / 51 subtests and 10 failures**. An
  isolated clean-HEAD worktree reproduces exactly nine host-artifact/wall-clock-dependent freshness
  failures; the new DOM-ID contract failure belongs to the dashboard draft. A separate real-page Node
  probe proves the browser abort timer expires only through headers, not body read. Dashboard acceptance
  remains held for body-size/deadline coverage, the DOM fix and narrow stable-fixture repairs.
- New native-controller draft review independently reproduces two mismatches: a rehashed/resealed
  carrier can change both its aggregate/per-launch values without changing raw units, or change its
  comparison backend without changing the frozen plan. Both probes are retained for the worker's
  corrective pass. Sealed bytes alone do not prove correct experimental attribution.
- Scoped new Vidya files pass Ruff. The separately edited INF70 test has nine existing Ruff warnings;
  reading its clean-HEAD bytes through Ruff reproduces the same nine. Only the approved three SC69
  expectations were changed; no unrelated lint rewrite or grader change was made.
- Five independent first-draft scheduler probes fail on semantics: unused optional K slots stall a
  production-only campaign; an unavailable frozen frontier blocks another ready frontier; a cheaper
  new seed jumps FIFO; one oversized optional proposal vetoes valid production; and an exact receipt
  accepts a different outcome silently. Main's review also requires actual held-resource deficit cost,
  usable capacity epochs, bounded indexed operation and retained incurred cost on bound violations.
  No scheduler source is accepted or connected to compute. Static hub metadata/docs are prepared but
  held with dashboard source pending the response-body correction. Their focused scope passes **208
  tests and 97 subtests**; this does not supersede the separately recorded dashboard failures.

### Native controller consumer accepted

- Main accepted AKU-03c after **278 tests and 15 subtests**, plus clean scoped Ruff and diff checks.
  The actual producer emits two process-unit measured carriers; both survive controller Journal replay
  and project through the independently implemented Vidya reader. Native values are fake test data,
  not performance evidence. Rehashed scalar/per-launch changes and full comparison-identity mismatch
  now refuse. Actual producer continuation remains diagnostic, not a fresh-launch measurement.
- The controller owns one serialized capture transaction: scoped same-thread/lifetime callback,
  exact-ID index, immutable raw/carrier byte verification, append/fsync/cursor/index update and poison
  on uncertainty. New capture requires an installed typed current worker-result fence. Replay returns
  the original exact event without inventing a current worker/grant. No grading or scientific-clock
  advancement is inferred from structurally valid arm captures.
- Research source checkpoint **384a8117**, main merge **ff708152**; five exact accepted files only.
  Frozen scheduler/enrollment/service drafts were excluded. Shared checkout and staging were untouched.
- Scheduler first draft remains unaccepted. Main stopped its own captured CLI PID after its core-suite
  checkpoint to prioritize bounded dashboard corrections; PID exit was verified. The later partial
  optional-adaptation change has one failing expectation and four of five original fairness/receipt
  probes still fail; FIFO now passes. This draft is frozen pending the prepared corrective review,
  not published or connected to execution. No foreign process was signaled.
- The next sol-medium worker owns only the archive/candidate frozen-kernel guard. Exact upstream
  impacts are LOW; manual review identifies the legacy pool caller despite absent indexed edges.
  New helper work proceeds while existing-file edits wait for checkpoint/index refresh. All testing
  remains temporary Git/fake execution; no frozen kernel tree, broker, live service or corpus changes.

### Freeze safety and management dashboard accepted

- AKU-05d closes the legacy archive freeze hole using the same dependency-light root/branch guard
  as candidate ref transactions. The canonical llama/whisper/qwentts roots, aliases, detached canonical
  checkouts and both production branch families refuse. Pre-CAS root/branch checks remain in place;
  experimental linked worktrees may share production objects. Main reviewed the exact six-file diff
  and ran **198 tests and 4 subtests** across guard/archive/candidate/controller/service consumers.
- Research source checkpoint **3ed96a9d**, main merge **1552744b**, publishes that guard and the
  previously held authenticated management transport: exact-origin CORS, loaded transport identity,
  no-I/O health probe, one owned connection-deadline watchdog and bounded close. Publication touched
  nine exact accepted files, excluding canonical enrollment and scheduler drafts. No live activation.
- AKU-09c now has a passing full hub acceptance: **414 tests and 125 subtests**, including actual page
  JavaScript timeout/body-stall, malformed/uncertain ACK, double-click, monotonic-stream, DOM, selected
  unified-versus-legacy health, registry/navigation, separate evidence clocks and existing headline
  behavior. New native reader/test files pass Ruff; all diffs pass whitespace checks.
- The expanded run found three additional old headline fixture failures, independently reproduced
  on clean baseline (**80 passed, 3 failed, 23 subtests**). The test-only fix derives its expected
  treatment/anchor from the exact copied producer record, preserving disambiguation, authority and
  collapsed-evidence checks. The helper's indexed impact was MEDIUM over six test callers and zero
  production processes; its full file now passes **83 tests and 23 subtests**. Main also restored the
  registry's explicit champion-headline/frozen-production wording after its wiring test caught an
  omission. No recorded measurements or renderer semantics were changed to make tests pass.
- Explicit selected campaign/config identity gates management-v1 snapshots and direct authenticated
  controls. Token and uncertain request remain tab-memory only; no hub command proxy, new page or
  deployment was added. V1 has no active worker/compute authority. Terminal history is not a live
  producer. Actual gateway/service deployment and unattended reliability remain untested here.
- Scheduler corrections are dispatched (fixed v1 weights, indexed hot path, fair coverage/FIFO,
  receipt/campaign binding, scoped outages and honest overruns). The next worker owns opt-in worker
  lifecycle only and must propose/obtain approval for a closed v2 contract before controller/schema
  edits; new helper work may proceed. Tiny owned fixture children are permitted, not kernel/model/
  compiler jobs, real cgroup mutation, broker implementation or live research.
- Research incremental indexing exited139 again after the source checkpoint. The supported wrapper's
  full `--force` rebuild is running under the canonical lock; no metadata is manually removed and
  existing lifecycle edits remain held until the index/interface releases.

### Scheduler accounting accepted; enrollment/lifecycle integration continues

- Main accepted the five-file scheduler/accounting slice after **138 passing tests** across scheduler,
  CLI, campaign and scoped-evidence consumers; all four Python files pass Ruff. Nine independent main
  probes exposed/fixed unused-slot stalls, ineligible-frontier stalls, non-FIFO seeds, oversized optional
  work blocking production, receipt outcome mutation, unavailable coverage hiding seeds, and full-region
  backfill incorrectly skipping a reserved seed. Coverage debt records unserved work without pretending
  it was measured. Required reservations survive; repeated optional arrivals cannot erase them.
- CLI state binds the complete resolved campaign, not only its name. Alias groups bind the actual
  workload signature and share seed history. Typed prerequisites are distinct from serving-ready work.
  Indexed receipt/seed maps and per-backend FIFO heaps remove historical scans from operational updates.
  Actual held resources remain charged after invalid results/overruns; fixed-v1 weights are explicitly
  non-adaptive. No allocation, concurrency certificate, measurement grade or live execution is implied.
- Scheduler worker proceeds to narrowly scoped retention/legacy prune safety. Main retains publication
  ownership. Real Journal/provider wiring and the unified runner remain implementation work.
- Production enrollment passed **114 research tests** plus **19 orchestrator/cross-repository tests**
  before final readiness review. Sealed per-target recipe artifacts prevent full/partition identity
  collapse; true aliases still merge. A further main probe found that sealed bytes could erase exported
  unsupported/waiting status in the Campaign projection; the worker is correcting that before acceptance.
  Future-model seeds are explicit local pins, not downloads or proof of executable model compatibility.
- Worker lifecycle/controller v2 seams are approved under the existing provider boundary (Journal impact
  MEDIUM, controller LOW). Main is reviewing exact deadlines, partial-create/spawn crash cuts, current
  result fences and asynchronous control completion before accepting worker-aware dashboard integration.
  Tiny owned fixture children only; no live cgroup/provider/broker or inference activation.
- Earlier research forced indexing completed successfully (**76.1 seconds**, fresh at `1552744b`), and
  root refresh completed (**86.5 seconds**, fresh at `dc3d28e6`). Dashboard source `7868b919` and its main
  merge `dc3d28e6` are published. New source checkpoints will refresh affected indexes again.

### Production enrollment and canonical serving adapter accepted

- The readiness correction is main-verified: sealed unsupported rows remain `unsupported_capability`;
  sealed rows waiting on any artifact, including DSOs, remain unresolved/missing. Byte identity never
  creates capability readiness. The complete research acceptance now passes **118 tests**, including
  nine main probes; orchestrator exporter/cross-repository **19** plus adjacent command/thread/runtime/
  environment/NUMA **109** tests pass (**128 total**). New Python files and all research edits pass Ruff.
- The exporter derives the actual production roster, verifies loaded configuration against pinned
  source bytes, refuses stale prior dependency closure, and creates no runtime directories. Only
  explicit `--out` publishes owned, immutable, fsynced recipe sidecars and the bundle. Read-only
  consumers verify actual sidecar bytes and their correspondence to the exported launch. Hashes differ
  for full/partition recipes; cosmetic aliases preserve identity. No global-export hash stands in for
  all target recipes. Retry after interrupted publication and sidecar tamper are covered.
- A closed canonical recipe adapter preserves exact CPU/GPU launcher argv/environment while rederiving
  every semantic field; unknown/ambiguous NUMA/flag forms and secret-bearing environment refuse. The
  cross-repository fixture now resolves Campaign and fake serving from the SAME sealed export, rather
  than comparing independent pre/post-seal identities. Ordinary production builder defaults remain.
- Optional local seeds reuse existing TargetSpec/artifact contracts and pin their comparator. No
  production-ref override or opposite-backend production build/recipe reuse is allowed. These are
  prospective local model enrollments, not downloads or proof that the new model can execute. Speech
  and other unsupported rows remain explicit in the production-only dry-resolution v2 envelope.
- Scheduler source `e3a7a073` and main merge `fb42601f` are published. Enrollment/canonical source is
  published as research `bed678d2` / main `8ea1e10e` and orchestrator `ee304926` / main `3b77bc5a`.
  Main owns root ledger/index changes; workers now own planner, lifecycle and
  retention scopes. No production kernel, live stack, research run or historical corpus was changed.

### Retention safety accepted; worker/planner consumer review continues

- Research source **3c273f7b**, main merge **5b1cf412**, publishes the six-file retention/legacy cleanup
  slice. Main ran **174 tests and 13 subtests** across retention, pipeline, anchor, gates and six
  independent graph probes. Ruff passes for changed production/new files; the legacy test file keeps
  only its independently identified pre-existing F841 exclusion. Whitespace checks pass.
- Deterministic closure is rederived at the maintenance boundary. Rehashing a forged plan cannot move
  a retained artifact into the expiry set. Permanent classifications retain dependencies, and distinct
  artifact IDs with equal/ancestor/descendant paths retain their overlapping bytes and dependency closure
  to a fixed point. Missing references/uncertain scopes withhold all expiry. The helper previews through
  existing storage policy; it creates no new expiry/grading authority.
- Legacy pruning captures/open-verifies parent identity before descriptor-based discovery, moves the
  exact target into an owned private 0700 quarantine, and deletes relative to its descriptor. Mutation
  fixtures cover store, generation and quarantine substitution. Discovery/finalization I/O failures close
  all owned descriptors. Replacement public paths are not mislabeled as recoverable owned artifacts;
  only remaining owned content gets a descriptor-derived recovery location. Byte reclamation is unknown.
- The current run-path cleanup now visibly returns `retention_unknown` instead of guessing that an old
  generation is unused. Even complete supplied JSON cannot enable unified deletion: current native root
  projection, generation recheck, existing storage tombstone expiry and native maintenance result wiring
  are still required. No live artifact cleanup or kernel/model/build work was performed.
- Planner review found target/recipe hashes supplied beside unmatched objects, source/build actors able
  to assert a final-plan hash, mutable dispatch carriers, and unnecessary canonical env-sweep refusal.
  Corrections are being tested against actual sealed CPU/GPU enrollment, exact prospective intent and
  persistent scheduler bindings; this draft is not accepted or published yet.
- Worker/control review passes the initial control/escalation/generation probes. A new prospective
  acquisition intent is approved before provider I/O, with typed denial versus unresolved recovery and
  stable v2 snapshot shape. Remaining review covers pipe cleanup, trusted bootstrap import origin and
  owned teardown despite returned Journal errors. The root worker-aware v2 consumer is now dispatched;
  neither lifecycle nor dashboard-v2 source is accepted or deployed by this checkpoint.

### Planner accepted; standalone consumer integration dispatched

- Research source **26171408**, main merge **1e5b766a**, publishes the scoped planner and its tests/docs.
  Main independently reran **228 tests** across planning, persistent scheduling/CLI, scoped evidence,
  canonical recipes, enrollment and experiment plans; Ruff and whitespace checks pass.
- Prepared runtime anchors validate unique exports/policies once, retain actual full/partition recipe
  provenance, and bind the complete resolved campaign. Repeated iterations read no export files. Typed
  runtime dimensions rederive actual launch semantics and require a matching full ExperimentPlan.
  Source/build actors cannot assert final-plan identity. Immutable dispatch records bind the exact
  proposal, ClaimKey and effect question; arm levels are not reported as gain evidence.
- Main's corrections cover mismatched target/model identity, hash labels beside unmatched recipes,
  mutable carriers, environment-sweep templates, cross-epoch ranking and stale same-manifest resolved
  artifacts. Startup validation is cached without promising that backing files cannot change before
  launch; execution-time checks remain required.
- The planner worker now owns a design-first standalone driver integration. It must select/budget
  expensive preparation before actor calls, persist prospective native intent, account actual held
  receipts and connect local seed profiling/runtime preparation. Existing lifecycle/controller files
  remain with their current worker until release. No isolated helper is labeled a completed service.
- Lifecycle and matching dashboard-v2 source remain under final review. Recovery, trusted bootstrap
  origin, teardown despite returned journal errors and accepted-versus-completed controls are tested
  with temporary fixtures only. No live service, provider, production kernel or research run changed.

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
