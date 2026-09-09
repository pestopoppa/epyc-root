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

### Owned-worker lifecycle and existing dashboard v2 accepted

- Research source **865c1e62**, main merge **bb0c2c38**, publishes eight reviewed lifecycle/control
  files. Main independently ran **307 tests and 15 subtests**, including 21 extra boundary probes;
  submitted file digests were confirmed before publication. The dashboard companion passed main's
  **296 tests and 79 subtests** across ten affected/adjacent files. Ruff, whitespace and README
  freshness checks pass. These are hermetic source/integration results, not live hardware evidence.
- Acquisition intent is durable before provider I/O, and launch intent precedes spawn. Typed denial
  proves no allocation; ambiguous authorization/inspection retains exact pending ownership. Recovery
  binds campaign, request, worker/grant generations, container inode, PID-start and boot identities.
  The isolated pipe-gated bootstrap excludes experimental import paths and inherited credentials.
  Stage/setup/native-I/O/teardown share one budget; provider methods still need their own enforced
  I/O deadlines. A returned journal error cannot disable exact owned cleanup, but uncertain durability
  cannot certify a terminal result or authorize a successor. Descriptor failure paths are covered.
- V2 separates accepted controls from actual quiescence. Pause-to-drain escalation retains the prior
  identity and cannot be overwritten by a superseded completion. Denied/no-launch worker generation
  gaps replay correctly. V2 START uses an explicit recognized version fence: an actual old reader is
  tested refusing before admission, not merely a current reader configured in a legacy mode.
- The existing hub consumes real producer snapshots and executes the actual page JavaScript in its
  tests. It rejects mixed result versions and same-campaign protocol downgrade; capability is not
  current grant authority. Pending acquisitions and failed teardown degrade semantic health even
  while transport/heartbeat are live. Failed digest/UUID construction retains an acknowledged pending
  pause; uncertain ACK retry keeps the same ID; newer completion wins over late HTTP responses.
- A fixture race was corrected with a deterministic post-release WORKER_STAGE barrier: observing an
  intent alone did not prove stage admission. Optional cross-repo tests locate explicit/standard
  checkouts, while ordinary v2 unit tests remain portable. The broader dashboard run's **15 legacy
  failures** (11 tests plus four subtests) reproduce at unchanged root HEAD `5ad7cbfd`; they are
  separately scoped ambient operator-gate/legacy v26 fixture failures, not attributed to this slice.
- Main accepted AKU-07b and AKU-09d only; their parent tasks remain open. The driver must still connect
  selected preparations, native intent, actual held accounting and evidence feedback. Its per-tick
  transition cannot copy receipt or retired-seed history, and caller-rehashed after-state is not
  scheduler authority. A contained planned-serving bridge now owns child-side execution/deferred
  artifact sealing and parent-only current-result ingestion. A third worker is implementing whole-
  lifecycle observation separately from protocol verdicts. No independent helper is labeled a
  complete autonomous campaign, and the generic parent-side serving guard still honestly refuses.
- Publication uses exact accepted paths/private indices and isolated main merges. Shared checkouts,
  frozen production kernels, real resource providers/cgroups, services, research runs and historical
  evidence stores remain unchanged. Bus drain and heartbeat again reject the non-roster session ID;
  no peer identity is impersonated. OP-41, research-relaunch and measurement-ratification gates remain.

### Expanded implementation team and in-progress acceptance review

- At the operator's request, started a separately coordinated CLI team with three explicit
  `gpt-5.6-sol` / medium workers, in isolated root/research consumer worktrees. The primary team
  retains driver/controller, contained-worker execution and lifecycle telemetry; the secondary team
  handles existing-dashboard v3, actor/target-profile preparation and bounded native belief feedback.
  Each team has disjoint file ownership, and primary review still precedes any publication. This
  corrects the earlier implication that the primary dispatcher's limit was machine-wide.
- Main independently ran **264 driver/planner/scheduler/controller/service/planned-serving/Journal
  tests and 15 subtests**, then **seven additional planner/driver boundary probes**. Review exposed
  duplicate/conflicting receipt preview deleting committed history, seed promotion not rolling back
  its queue/state, and old intent materialization rebinding to a new supervisor. The reproducing
  probes pass after correction. This package is still awaiting its worker-bridge dependency's
  acceptance; these counts do not claim a published or live autonomous campaign.
- Additional source review requires actual, bounded telemetry producers rather than fixture-only
  GPU paths; code-constant/bound-state instrument identity; unconditional observer shutdown; terminal
  result fencing after durable acceptance; and full held-allocation accounting. The real-bootstrap
  containment-refusal path and the successful owned-fork protocol fixture remain deliberately
  separate from any real-provider claim. All test processes are tiny, explicitly owned fixtures.
- Early secondary-team review identified full Ledger scans per event, rebuilt retrieval indices per
  request, display-only evidence invalidation, and actor execution outside the existing lifecycle.
  Corrections are assigned within the existing packages; no new database, grader, process supervisor
  or resource-authority shortcut is accepted. Runtime sweeps remain actor-free; arm levels do not
  become improvement effects by joining them on read.
- Registered two prospective source families immediately in the Vidya source table, with
  VB-AK-UNIFIED-LIFECYCLE and VB-AK-UNIFIED-DISCOVERY tasks: lifecycle dependency observations and
  generic fixed-member A2 runtime-screen receipts. Native attachment/readers must be wired before
  real execution. No historical tuple invention, corpus ingestion or policy amendment occurred.
- Implementation sub-item count remains **26 accepted** at the prior checkpoint; parent AKU-01–12
  remain open. New source drafts and the new team's reported test counts are not counted as accepted.
  Shared checkouts, frozen kernels, real resource providers, running services and research campaigns
  remain untouched. Bus drain/heartbeat still reject this non-roster ID; no peer identity is used.

### Third team dispatch and boundary wrap-up discipline

- At the operator's further request, launched a third coordinating CLI session in a new isolated
  research worktree, `autokernel-delivery-research-20260909`, on
  `lane/autokernel-delivery-20260909` at `bb0c2c38`. Its actual three worker dispatches explicitly
  use `gpt-5.6-sol`, medium: candidate-validation consumer, versioned legacy migration, and
  standalone CLI/control/service packaging. These are separate end-to-end contexts, not a split
  into drafting/testing/review roles, and cannot edit the core or second team's files.
- The operator reiterated per-boundary wrap-up for every team. Each worker/lead now receives an
  explicit handback contract: owned docs, exact hashes/tests, real consumer versus fixture scope,
  remaining tasks and proposed checkbox/progress updates. Primary owns shared documentation and
  reviewed path-scoped publication, returning commit receipts. A handback awaiting acceptance is
  not described as a published checkpoint; no pruning, compaction or wiki sweep is triggered.
- Main independently reproduced **95 dashboard-v3 tests** against the actual in-flight producer
  and **142 worker/driver/native-capture tests** including current extra boundary probes. Dashboard
  impact is LOW, five internal consumers. Review still requires the historical-versus-live v3
  health case, bounded outstanding evidence requests and late provider-return handling before
  those packages are accepted. Existing owners are correcting them; no live services were changed.
- A2 review found missing common-frame semantics, unverified replay restoring nomination authority,
  and invalid-arm terminal/retrieval scope gaps. These are assigned source corrections, not operator
  blockers or protocol changes. The primary driver worker also owns the new end-to-end execution
  consumer; team 2 retains actor/feed/retention and team 3 retains validation/migration/CLI.
- This is an in-progress coordination/source-registration checkpoint. **No new implementation
  checkbox is marked complete**: the previously accepted count remains 26. The two prospective
  Vidya wiring tasks remain open; all live hardware, OP-41 and cutover gates are unchanged.

### Reviewed driver/worker foundation and dashboard-v3 boundary

- Published research source **61a63c42**, promoted to main **8cbcce9f**: 17 reviewed files connect
  durable unified driver issuance/settlement and the contained planned-worker/parent-native boundary.
  An independent clean checkout containing only those release files passed **1,444 tests and
  83 subtests**, twice; five main-owned boundary-probe files passed **20 tests**. After removing two
  unused imports, the final focused run passed **42 tests** and all 15 Python files passed Ruff.
  Draft A2, lifecycle-observation and end-to-end driver-execution files were excluded from publication.
- The driver binds current catalog, complete arm identity and supervisor before materialization;
  duplicate/conflicting preview cannot delete receipt history, and rollback preserves seed queues.
  Issuance and settlement are native/fsynced before state application. Indexed totals keep the
  operational projection independent of historical receipt length. The accepted v3 protocol fences
  old readers and reports genuinely disconnected consumers instead of inventing readiness.
- The worker bridge proves current child/process/container membership before releasing its payload,
  bounds IPC and pending parent-evidence requests, validates all sealed captures before the first
  native measurement callback, and fences terminal results only after durable acceptance. Late
  provider returns retain actual held cost but cannot preserve scientific freshness. Real-bootstrap
  cgroup2 refusal and tiny explicitly owned fork fixtures do not imply real-provider containment.
- Accepted and integrated the secondary team's exact four-file dashboard-v3 packet. Main independently
  reproduced **96 tests** against the published producer, including actual page JavaScript, and
  confirmed every submitted SHA-256. Refreshed GitNexus reports LOW impact, five internal consumers.
  The existing page preserves v1/v2 controls and downgrade fencing, rederives accounting identity in
  Python, and keeps disconnected values null. A live disconnected producer is degraded; an offline
  drained snapshot remains history. No route, proxy, registry or running service was changed.
- Per-task wrap-up now marks **AKU-06c, AKU-07c and AKU-09e** complete: **three new accepted sub-items**,
  **29 total accepted implementation sub-items**. All twelve parent tasks remain open. The actual
  driver-to-worker execution/held-settlement connection is still a separate assigned package; actor,
  evidence, retention, validation, migration and standalone packaging remain under their owners.
  Whole-lifecycle telemetry and A2 drafts still require main acceptance. These are active source
  implementation tasks, not operator blockers or unattended/live-completion claims.
- Teams received publication receipts and retain per-package wrap-up obligations. Main owns shared
  handoff/progress/index application and reviewed publication. Bus drain/heartbeat again refused the
  non-roster session ID; no peer identity was used. Frozen kernels, real grants, services, research
  runs and historical stores remain untouched; OP-41 and measurement/cutover gates remain intact.

### Reviewed lifecycle-observation and advisory runtime-screen boundary

- Published research source **04d73260**, main **d75bc9ec**: nine exact reviewed files add the
  bounded lifecycle observer/serving hooks and generic A2 runtime screens. Main prepared an independent
  checkout from published `8cbcce9f`, copied only those nine files, checked every SHA-256 against the
  final packets, and ran **1,512 tests plus 83 subtests**. Final focused validation passed **143 tests
  plus 3 subtests**, all seven Python files passed Ruff, and scoped diff checks passed. Driver-execution
  drafts and other teams' packages were excluded. Fresh GitNexus impact was LOW (serving: two callers;
  eligibility: zero indexed upstream callers).
- Observer acceptance includes six independent main regressions: loaded constants/nested code, mixed
  dict/slot configuration, unsupported hidden native payload, dropped-sample cost accounting and an
  unjoined reader between probes. The actual finish path now preserves unknown reader cost even when
  no read is active. Frozen records cannot accept late samples/callbacks; serving cleanup cannot be
  skipped by observation/export errors. GPU attribution requires explicit trusted target evidence,
  not a fabricated proc path or global VRAM; missing purpose/runtime verification stays unknown.
- A2 screens bind complete same-artifact runtime/policy/host frames. They seal three anchor samples,
  run three candidate-only samples and require a live registered verifier for cache/nomination
  authority. Invalid terminal results are retained; ambiguous launch intent requires reconciliation.
  Actual different-epoch plans exercise A3 stale-history handling: conclusions survive, magnitudes
  are null. Mixed current frames cannot be ranked. Ordinary build/agent/filesystem load remains
  diagnostic noise; only the owning protocol's verified overlapping inference can veto an A2 arm.
- Per-task wrap-up adds **AKU-04d and AKU-07d**, bringing the accepted implementation sub-item count
  to **31**. All twelve parent tasks remain open. The two already-registered prospective Vidya tasks
  remain open until actual native attachment/phase projection is connected; no historical claims are
  invented. No extra task/decline is needed for these residuals: they are already owned by AKU-04/07/08.
- Main review also found the driver and actor connectors bypassing the actual controller-owned
  worker engine. Corrections now require the real Journal sink, admission/drain gates and active
  projection, with narrow public execution/terminal seams. These are active assigned implementation
  fixes, not operator blockers. Other teams retain separate file ownership and per-package wrap-ups.
  Bus drain/heartbeat again rejected the non-roster session ID; no roster/peer identity was changed.
  No frozen kernel, live service, real grant, inference run, corpus or historical artifact was touched.

### Reviewed retention and historical-migration boundary

- Published research source **1be3cf79**, main **e678a2e2**: the exact four-file team-2 retention
  packet and seven-file team-3 migration packet were reviewed and integrated. Migration's older
  measurement-capture module was not copied wholesale: only its public `ArtifactStore.exclusive()`
  method and focused tests were added, preserving the published native bridge/read APIs. All eleven
  resulting hashes matched the independent clean acceptance checkout. Main reproduced **250 tests
  plus 82 subtests** for retention and **110 tests** for migration; the combined clean release passed
  **1,750 tests plus 165 subtests**, final primary-tree focused checks **68 tests**, and Ruff/diff gates.
- The first combined run correctly refused fixture storage beneath the scratch directory used for
  the clean checkout (68 failed, 1,690 passed, 150 subtests passed). Main moved only its disposable
  checkout to the worktree area and reran the identical code successfully. No policy was relaxed.
  GitNexus refresh initially exited 139; the repository wrapper's next full recovery succeeded at
  `d75bc9ec` without deleting metadata. Fresh impacts were LOW: store exclusion nine upstream
  dependants, retention dry-selection helper zero indexed callers.
- Retention now exercises actual candidate/store/native-Journal reopen recovery, validates one
  bounded exact tombstone index per held operation, and requires matching descriptor, preconditions,
  source/path/content and prepared policy. Sequential replay is not called concurrency. Its actual
  maintenance-owner connection remains assigned: separate exclusion must survive slow provider/disk
  I/O without holding the health/control mutex or fabricating release/accounting. Only explicitly
  disposable fixture bytes were removed; these tests touched no research artifacts.
- Migration uses safely escaped read-only SQLite URIs, strict integer/record/byte bounds, and its own
  installed closed v1 reader before creating the destination snapshot. Public verified reentrant
  exclusion covers dedicated-destination checks and publication, with thread/process tests. Unknown
  legacy measurement authority remains unknown; import does not initialize candidate state or grant
  serving/validation rights. No real migration, cleanup, provider, service, or frozen tree was used.
- Per-task wrap-up adds **AKU-10b and AKU-10c**: **33 accepted implementation sub-items**, all twelve
  parents still open. No separate new source family or grader is introduced. Remaining native owner,
  evidence and live-cutover work is already tracked; no new task/decline is needed for this boundary.
  Teams receive publication receipts and keep the operator's per-package wrap-up discipline.
- Main's further validation review reproduced five sealed-row replay identity gaps (batch, row,
  candidate, comparator and row-set); that owner is correcting them before acceptance. Actual A2
  native persistence and versioned lifecycle attachment are also actively assigned, with disjoint
  controller/Journal ownership. Bus drain/heartbeat still reject the non-roster session ID; no peer
  file, roster entry, service ownership or live authority was changed.

### Reviewed controller-owned runtime execution boundary

- Published research source **59eb3f30**, main **6f869803fb49fb8afc334cebd55ed1cdfd328fa9**.
  Main built an independent six-file acceptance tree from `e678a2e2`, excluded the other owners'
  in-flight A2/observation/stdout hunks, and reproduced **136 focused/adjacent tests** plus
  **1,729 loop/Journal/storage tests and 165 subtests**. All five Python files passed Ruff and
  scoped diff checks. Publication staged exact accepted blobs through a private index; pending
  same-file worker/controller hunks remained untouched and unpublished. Fresh run-worker impact
  was LOW, zero indexed upstream callers; actual caller and failure-path review supplemented it.
- Selected runtime execution now uses the actual controller-owned engine, durable acquisition and
  lifecycle Journal, native result validation, provider-held costs and exact scheduler settlement.
  A positive current-lifetime pre-engine refusal or exact durable provider denial permits retry;
  empty active projections, unseen requests, old incarnations and ambiguous acquisition do not.
  Duplicate execution and execute/close are serialized. Failed work is charged once without
  granting a scientific comparison or rewriting immutable lifecycle results.
- Main independently reproduced a successful-child/producer-shutdown-error bug: accounting committed,
  then the receipt rejected its own accepted terminal. The corrected path retains the exact result
  diagnostically and returns an idempotent failed settlement with no scientific native admission.
  Further review caught lost ownership when close swallowed an unjoined producer and cleared its
  handle. Real finite blocked-thread tests now cover both post-terminal and partial-start cleanup;
  handles remain retained, new work is fenced, exact settlement retries remain possible, and close
  refuses/retries until the producer joins. The default evidence evaluator remains unknown.
- An initially overbroad historical test run encountered failures and was stopped. Main identified
  its exact owned pytest PID **160697** by command, start time and acceptance-tree cwd, sent SIGINT
  then SIGTERM, and verified the PID absent (exit 143); no name-pattern or foreign process signal was
  used. Subsequent `--maxfail=1` runs on unchanged `e678a2e2` and the six-file candidate produced the
  identical first failure: `ArenaAdapterTest.test_c5_reference_seed_is_bound_into_the_priced_task_context`,
  **365 passed, 58 subtests passed, one failed** on each. The C5 registry pins mutable
  `/workspace/handoffs/active/agentic-rocm-kernel-authoring.md`; its `ev-gfx90a-sol-bound-quality-20260815`
  digest differs. No all-historical-suite pass is claimed. Explicit decline: do not refresh or bypass
  this pre-existing external evidence pin in the unified-execution package; changing its warrant is
  outside this source slice. No new backlog row is filed for that deliberate non-change.
- Per-task wrap-up adds **AKU-07e**: **34 accepted implementation sub-items**, all twelve parent
  workstreams still open. Main separately reproduced the current actor (**71**) and feed (**88**)
  focused tests; these drafts remain unaccepted until their real owner connections are complete.
  The actor stdout accessor, versioned observation attachment, A2 native persistence/invocation,
  validation, standalone shutdown/composition and maintenance exclusion remain actively assigned.
- The precise Journal durable-reader/ACK and maintenance native-exclusion seams were released to
  separate secondary-team workers. A proposed shared Vidya `Ledger.append` modification returned
  **CRITICAL** impact (**25 upstream, 16 workflows**); main warned the operator and stopped that
  mutation. Feed implementation continues against the existing single-writer contract without
  private-cache authority or a new grader. Journal append/lock impacts were MEDIUM (17/15), cursor
  LOW (0). No shared Ledger writer or measurement trust-boundary change was made.
- Standalone composition now has the published execution dependency and a narrow driver-discriminator
  release. Unavailable actor/profile work must remain visible before issuance while other executable
  runtime work proceeds; shutdown retains unresolved ownership. Main's two additional controller-only
  probes found already-drained and management-v1 SIGTERM bugs; the CLI owner is fixing both. These
  are active source fixes, not operator-deferred work. ROOT/research GitNexus wrappers refreshed
  successfully; README freshness is clean. No live inference, service activation, real grant, corpus
  ingestion, production kernel or historical research artifact changed.

### Reviewed native validation consumer boundary

- Published research source **1ac8393e**, main **deab8f40a0a6e1bb96d17e4fa4f6d0097bc541d7**:
  exactly the three frozen validation-consumer files from team 3. Main reproduced their hashes in
  an independent checkout at `6f869803`, with **246 adjacent/edge tests** and the combined
  **1,762 loop/Journal/storage tests plus 165 subtests**, Ruff and scoped diff checks passing.
  The primary worker separately reproduced 252 tests in the in-flight primary tree; the clean
  release is the publication evidence, not an assertion that unrelated drafts are accepted.
- The consumer binds each submission to the current due frozen batch, both manifests, required
  row set, plan/lineage and full executable/loader-name/DSO identities. A sealed row retains and
  reopens exact carrier/raw/calibration bytes and repeats complete-measurement and structural-use
  checks. Main's earlier receipt substitution regressions and team 3's diagnostic/ineligible-pair
  corrections are included. Required CPU and GPU rows remain independent; optional seed debt
  cannot silently substitute for production coverage.
- Real semantic authority remains explicitly unavailable for v1's unproven loaded instrument.
  The same team-3 owner is now implementing the actual native-v2/ClaimTuple/owning-objective and
  row/LOO semantic consumer. This is assigned source work, not an operator-deferred proposal.
  No competing grading ladder or retrospective claim reconstruction was introduced. This
  package is a consumer of the already registered native arm source, not a new measurement source.
- Fresh research indexing initially exited 139 during incremental analysis; the wrapper's
  subsequent full recovery succeeded without metadata deletion (88,643 nodes, 152,016 edges).
  Exact `record_native_row` and `reopen_row` impacts are LOW with zero indexed upstream callers.
  Three-file publication preserves all in-flight A2, observation-v2 and stdout hunks.
- Additional review reproduced a controller-backed cached-bank regression: a second logical
  discovery screen could not use a verified sealed bank without creating a new anchor phase.
  The original A2 owner is correcting durable bank-reference/restart handling before acceptance.
  Stdout review found blocking lock acquisition and same-inode/same-size replacement exposure;
  its owner is binding reads to the bootstrap's recorded bytes/hash/truncation fields and
  preserving terminal/held-cost evidence on optional output failure. Both fixes remain assigned.
- Main released precise actor/profile native-owner hooks to team 2, independently of its
  disjoint feed and maintenance work. Existing Journal/ClaimTuple authorities remain reused.
  The user goal explicitly includes the complete dry run and five-loop monitored test;
  **AKU-12a/12b** now make those acceptance requirements discoverable, without treating mock
  loops as live acceptance or widening production/resource trust boundaries.
- Per-task wrap-up adds **AKU-05e**: **35 accepted implementation sub-items**, all twelve
  parents still open. Two explicit acceptance tasks were added; zero new declines. No index
  pruning, handoff compaction or wiki compilation sweep was run. Bus drain still refuses this
  non-roster session ID; no roster or peer bus file was changed. A continuation log initially
  used the default audit shard; subsequent logging restored the established session/shard IDs.

### Reviewed controller-owned stdout boundary

- Published research source **47ce0677**, main **6fc751920267dd031486df036b6fcf48c0c8aef2**:
  controller accessor, lifecycle metadata, actual-controller tests and execution documentation.
  Main applied only the reviewed stdout hunks to its independent acceptance tree, excluding
  the parallel A2 and observation-v2 changes. Exact clean acceptance passed **126 focused/adjacent
  tests** and **1,768 loop/Journal/storage tests plus 165 subtests**; Ruff/diff checks passed.
  The accessor's exact impact is LOW with zero indexed upstream callers.
- Review corrected blocking shared-lock acquisition, optional secure-open/fstat failures that
  could erase terminal/accounting publication, and same-inode/same-length output substitution.
  The accessor now uses nonblocking locking and verifies the original bootstrap-authored stdout
  length, SHA-256 and truncation state as well as file/worker/result identity. Main moved hashing
  before the final locked current-owner recheck; neither file reading nor hashing holds that
  mutex. Tests cover actual temporary child output, exact bytes, wrong result, size ceiling,
  lock contention, FIFO/directory/missing/replaced files, content tampering, truncation, close
  during a blocked read, and preserved terminal/held cost on optional identity-capture failure.
- The primary worker now integrates team 3's corrected CLI/command/shutdown package into a
  separate clean checkout. The original native-v2 worker is implementing the released actual
  descendant-capture/controller-token path and supported loaded builtin timing provenance.
  The A2 owner is correcting bank reuse. Team 2 retains separate actor/profile, feed/projection
  and maintenance ownership; team 3 retains runtime composition and semantic validation.
- Registered prospective target-profile and owning validation/LOO finding sources in the adapter
  table and added **VB-AK-UNIFIED-PROFILE / VB-AK-UNIFIED-VALIDATION** before those new producers
  execute. Reuse existing profiler/native sources and canonical source-class grading; missing
  profile observations or decided propositions cannot be fabricated on read. These are source
  wiring tasks, not new grading rules or live ingestion authority.
- Per-task wrap-up adds **AKU-07f**: **36 accepted implementation sub-items**, all twelve parent
  workstreams still open. Two prospective wiring tasks added, zero new declines. No production
  tree, service, real resource grant or research artifact was changed; only owned temporary test
  processes ran. README freshness is clean; index pruning/compaction/wiki sweep remain untouched.

### Reviewed standalone controls, restart retry and shutdown

- Published research source **29b8120b**, main **1fea54a57e377cfb86b27decffb09ca7ddd246f1**.
  Eleven reviewed CLI/control/service/test/template files were staged from a clean acceptance
  checkout through a private index. Moving A2 and native-observation hunks were preserved in the
  primary working tree and excluded from publication. The control method's exact indexed impact
  is LOW, two upstream callers; research index was current at `6fc75192` before integration.
- Main independently reproduced **331 tests plus 15 subtests** (8.64 s) and **1,810 complete
  loop/Journal/storage tests plus 165 subtests** (31.52 s). The integrated primary's targeted
  smoke run passed **88 tests**. Main's extra real-service restart probe first failed: the CLI
  rejected an original supervisor pin before the journal could answer an exact accepted retry.
  The correction permits a newer coherent authenticated supervisor only for control submission,
  preserving original command bytes. Status stays exact-pinned; new old-incarnation commands
  still fail at the server. No silent repinning or duplicate application was introduced.
- Versioned controls bind campaign/config/supervisor/request/revision semantics. SIGTERM writes
  or reuses one durable drain; repeated signals and already-drained restart do not invent new
  commands. Status remains available and resume is fenced while ownership is unresolved. The
  source-only service template was neither installed nor enabled. These tests are not the
  required standalone dry run or five-loop mixed research acceptance.
- Additional independent probes changed the next implementation actions: standalone `run()`
  stopped after a transient authority refusal despite having an exact retry; maintenance cleared
  its exclusion after acquisition reply loss or a false aborted-settlement result. The original
  runtime and maintenance owners are correcting these paths, with three failed probes retained
  in the session's temporary evidence directory. Both maintenance tests failed before deletion
  and verified that their disposable artifact remained. Feed startup-lease cleanup and expired
  ACK deadline probes passed (2 tests). Cached A2 bank reuse passed 21 focused clean-tree tests;
  its separate full acceptance remains in progress.
- User approval was recorded for the precise HIGH-impact actual-descendant lifecycle validator
  change, not unrelated HIGH/CRITICAL code, production kernels or measurement policy. Its owner
  remains active on the native integration; loaded-builtin artifact bounds/stability are also
  under review. Main retained single ownership rather than launching a concurrent second writer.
- Per-task wrap-up adds **AKU-07g**: **37 accepted implementation sub-items**, all twelve parents
  remain open. Three newly explicit implementation tasks (AKU-07h/07i/10d), zero declines. The
  index next action is refreshed; no index pruning, compaction or wiki sweep is performed.

### Reviewed A2 phase persistence and original-bank reuse

- Published research source **6b5d5fda**, main **c36411a7b1ec8a386c161f30c4c1b4d9f649dc0b**.
  Main reviewed the eight-file persistence packet in an isolated acceptance worktree, composed
  the just-published CLI/control delta, and independently ran **1,831 loop/Journal/storage tests
  plus 165 subtests** (32.93 s), including the previously failing cached-bank probe. Ruff and
  diff checks pass. `append_a2_runtime_transition` has LOW exact indexed impact, zero upstream.
  Publication excludes the moving native-observation/worker changes through a private index.
- Root cause: generic bank verification did not supply a durable source in a second logical
  controller-backed screen. The corrected reuse adds a separately closed original-bank reference
  before candidate phases, preserving seven source anchor events and Journal IDs, plan/frame,
  seal and bank identities. Restart recomputes the reference from indexed original history;
  foreign stores, missing or ambiguous sources, changed frames and forged references refuse.
  It runs zero replacement anchors and exactly three candidate invocations in the fixture.
- The actual phase bound remains fourteen, plus at most one bank reference. In-flight INTENT
  replay remains fenced. The next assigned bridge must use one selected unit of the unchanged
  full plan and an opaque fresh-current-owner reservation; unknown after restart cannot become
  proof that acquisition never happened. No native launch, claim, grading or production authority
  was added by persistence tests. The prospective discovery source registration already exists;
  its native evidence/ClaimTuple consumer remains required rather than invented on read.
- Per-task wrap-up adds **AKU-04e**: **38 accepted implementation sub-items**, all twelve parents
  remain open. **AKU-04f** records the exact next native bridge task; zero declines. Main kept
  the native worker as the sole owner of its changing lifecycle/observation regions. No live
  inference, research artifact deletion, service activation or production-kernel change occurred.

### Review checkpoint: native identity, maintenance and standalone recovery

- No new research implementation packet is published by this checkpoint. Accepted implementation
  sub-items remain **38**, all twelve AKU parents open. This records a completed review batch,
  four newly explicit follow-ups (AKU-06d/07j/08c/12c), and two separately pending approval scopes;
  there are zero completed-task checkbox flips and zero declined follow-ups. Existing 07h/07i/10d
  tasks now carry current corrective work. No index pruning, compaction or wiki sweep occurred.
- Main independently tested the moving service/runtime composition: **84 passed in 8.10s**,
  including the external pipe2 startup-failure probe that previously leaked an entered controller.
  The service now handles both finite successful recovery statuses, recovered and settled. Actual
  restart after a completed worker remains fenced because provider-held accounting was memory-only.
  A read-only source review specified a versioned record before final result publication and
  accounting-only replay, including crash after held append but before final result. This is a
  missing implementation connection, not permission to fabricate zero cost or resurrect results.
- Four external maintenance probes plus its focused suite passed **35 tests in 1.17s** after
  fixes for acquisition reply loss, invalid aborted settlement, receiptless controller abort and
  stale receipt use after renewal. The follow-up legacy INTENT test then returned **1 failed,
  2 passed**: validation inserted abort_receipt into a v1 payload, breaking closed-shape revalidation.
  The owner is correcting this and preparing a clean six-file packet. All deletion tests use
  disposable fixtures; real retained-artifact roots/provider readiness remain separate requirements.
- Native loaded-instrument readers now pass **8 tests in 0.41s**, including the independent
  changing-file probe. Opens are nonblocking, reads bounded, and before/after identity checked.
  Main subsequently reproduced an ancestry check accepting a reused target PID with different
  start ticks (**1 failed**). The approved native worker has the exact probe and review feedback;
  the complete contained-child/evidence/append/restart acceptance is still outstanding.
- The canonical ROOT v2 reader's serving-PID/lifecycle-target binding correction passes **56 tests
  in 0.21s** with explicit current research-root configuration. The cross-repo producer test is
  still the existing v1 path; v2 fixtures do not prove the final v2 producer. The semantic owner
  is connecting immutable reprojectable canonical-grade receipts, not a second grader or a
  permanently unavailable adapter. Feed and actual eligibility consumers remain required.
- Actor/profile source review requires clean composition on c36411a7 with the actual published
  driver issuer, public profile authority, real tiny fixture worker and reopen. Main's older-lane
  focused run returned **54 passed, 1 failed**: the budget-drift test lacked current producer
  receipt authority after restart and failed before reaching its intended budget assertion.
  The correction must repair the precondition and test both constraints, not weaken the regex.
- Real production export refuses `compiled priors are stale for descriptors`. The canonical
  stack-generation pipeline preserves declared both/full/split topology; bare priors compilation
  does not. Its generated-file-only repair is pending OP-AKU-STACK approval (HIGH 66 upstream).
  The extra held-cost event is separately pending OP-AKU-HELD approval (HIGH 22 upstream, three
  processes). Original descendant approval stays in force. OP-41 broker-code delegation remains
  unanswered and live finalise/promote/reboot gates stay unchanged; none blocks unrelated source work.
- Evidence/probes and owner packets are retained under the session's autokernel-implementation-20260908
  temporary directory; test names and assertions above distinguish failures from source-review
  concerns. No dry run, five-loop hardware campaign, grant, live service activation or production
  kernel change is claimed. README freshness check is clean. Bus drain/heartbeat still reject this
  non-roster session id; no peer roster/outbox was impersonated or modified.

### Public selected-profile materialization and integration-review checkpoint

- Published research source **c3303474**, main **1accc7f2**: public
  UnifiedCampaignDriver.materialize_profile and immutable SelectedProfileWork bind the exact
  issued catalog/transition/selection/profile request/plan/current controller. Public native
  controller tests require no private issued-state seeding. The advice grants no execution.
  Main reproduced **24 focused tests**, then **1,834 passed plus 165 subtests in 24.47s** on
  clean c36411a7 composition. Only unified_driver.py, its new focused test and test_storage.py
  are published; moving native/actor/service/maintenance hunks remain excluded.
- Broad acceptance initially returned 1 failure, 1,833 passes and 165 subtests: the unchanged
  storage boundary fixture sampled live free space twice while other sessions wrote files.
  The deterministic test now mocks one fixed statvfs observation; exact equality stays OK and
  a higher floor reports pressure. Production storage.py is untouched. Main's storage/profile
  focused rerun passed **183 tests and 82 subtests**; the final broad result above is green.
- Actual profile → scheduler E2E with --runxfail independently fails because provider receipt
  identity does not match selected proposal/backend/class. Source audit confirms those typed
  fields never reach provider authorize/close in current StageRequest. New AKU-07k and router
  OP-AKU-BIND request the exact additional HIGH22/three-process versioned contract extension.
  No request-ID-only workaround, argv classification or rewritten provider receipt is accepted.
  Independent selected admission and authenticated-output hardening remain assigned under 06d.
- Main native regression pass: **254 tests and 15 subtests in 12.59s**. The actual bootstrap,
  worker, four serving descendants, v2 artifact append and restart fixture also passes alone.
  Cross-repository replay through the actual team-2 projector returns None for both arms with
  **diagnostic:zero scored independent launches**. This is correct diagnostic refusal, not a
  scored-v2 integration success; synthetic containment/telemetry remain explicitly fixture-only.
  Separate PID-incarnation and expired-owner publication probes still fail pending owner fixes.
- New AKU-08d records a reproduced canonical-loader defect: verified new source SHA can still
  execute old timestamp/size-valid .pyc. The semantic owner must compile the exact bytes verified
  and test failure/concurrency cleanup. The existing 08c receipt/feed task remains open.
- OpenAI Docs/local CLI inspection identified an existing-session message queue. Main queued
  direct review nudges to all three exact live owner threads without starting duplicate owners.
  Queue acceptance is not acknowledgement; owners must still read, correct and refreeze. The
  control-socket proxy was unavailable and no daemon was started. Delivery evidence stays in
  tasktmp/owner-review-message-delivery.md.
- Checklist sync adds **one completed sub-item (AKU-06e)**, bringing accepted implementation
  sub-items to **39**; all twelve parents remain open. Two new open tasks (07k/08d), zero declines.
  No standalone dry run, five-loop hardware acceptance, grant, service activation, kernel change
  or real artifact deletion occurred. Per-task wrap-up only: no pruning, compaction or wiki sweep.
  README freshness is clean; lane identity passed. Bus drain/heartbeat again refused this
  non-roster ID; no other session's identity or outbox was used.

### Durable maintenance ownership and replay integration

- Published research source **c5525fb8**, main **b77215bb**: six-file maintenance ownership,
  native Journal replay, candidate/worker/publication fences, shutdown guards and focused tests.
  Exact accepted blobs came from a clean 1accc7f2-based acceptance tree through a private
  index; main composed only the additive hunks into moving native journal/controller files.
  Native nineteen-file work remains unpublished and was not swept into this commit.
- Final review reproduced five malformed replay cases: first misbound hold accepted, prior
  terminal hold/cost carried into a fresh job, changed completed cost, arbitrary accounting digest,
  and invalid fresh/recovery token chains. Corrections bind every hold, reconstruct exact completed
  accounting, preserve IO_COMPLETE cost, and reset state only under a valid distinct intent.
  A sixth active same-token/nonidentical-intent regression also refuses rather than losing a hold.
  Valid legacy non-abort rows retain their closed schema; unproved legacy abort remains refused.
- Clean acceptance: **1,873 passed plus 165 subtests**. Main's composition with the current native
  packet: **1,899 passed plus 165 subtests in 26.49s**. Main separately reproduced **39 maintenance
  tests** and **six independent shutdown/abort/uncertainty probes**. Unresolved ownership prevents
  close/drain completion; exact settlement wakes command waiters without holding locks across I/O.
- Fresh cleanup remains unavailable: candidate manifests alone do not establish the complete
  worker/evidence/DSO/RUNPATH/physical artifact catalog, and no concrete broker maintenance hold
  provider is installed. These requirements remain explicit in AKU-10d/10f/10g. No retained research
  artifact was deleted, and no live provider grant or service activation occurred.
- Native review advanced: main PID/expiry probes **3 passed**, broader lifecycle/driver/observation
  **67 passed**, and actual child/reopened ROOT projector **1 passed**. The cgroup fixture verifies
  real tiny-child membership and cleanup only; synthetic scored witnesses establish schema wiring,
  not correctness/contention/placement evidence. The canonical source-loader stale-bytecode and
  FIFO probes both pass in the delivery working tree (**2 passed**), pending its publication.
- New AKU-07l records public planner/materializer v2 routing, which the existing fixture bypassed
  by manually upgrading its prepared envelope. New AKU-07m records sealed-artifact completion IPC
  and concrete parent witness derivation; source configuration callbacks alone do not supply these
  facts. Both independent implementation slices are assigned without widening HIGH shared helpers.
- Checklist synchronization adds **one completed sub-item (AKU-10e)**, bringing the accepted count
  to **40**, and **four open tasks (07l/07m/10f/10g)**; zero declines. All twelve parent tasks remain
  open. No installed standalone dry run or five-loop hardware acceptance is claimed. Per-task
  wrap-up excludes index pruning, compaction and wiki sweep. ROOT code index refreshed successfully;
  bus drain still refuses this non-roster id and no peer identity/outbox was used.

### Public v2 scheduler/materialization connection

- Published research source **c65af942**, main **9eafac1f**: schema-aware expected arm
  identities in plan_iteration and original-version materialization in the public driver.
  Startup instrument identity must match the v2 plan's sealed instrument. V1 remains v1;
  proposal/claim recipe identity and the HIGH-impact shared identity helper are unchanged.
- Main independently reproduced **57 tests** on both the immutable composition snapshot and
  PRIMARY; final combined loop/Journal/storage regression passed **1,905 tests plus 165 subtests
  in 27.01s**. Tests use actual controller commands, scheduler selection and materialization for
  CPU/GPU v1/v2; no prepared envelope upgrade or private issued-map seed substitutes for planning.
  An initial isolated fixture needed its artifact-root parent created before instrument sealing;
  the final patch includes that setup correction. Preliminary acceptance commit 5ac25714 is
  superseded by the reviewed publication, not a separately deployed version.
- The nineteen-file native dependency was captured with before/after SHA equality for the
  composition tests. The native owner is still finalizing its manifest; that packet was excluded
  from publication. Main's strengthened actual-child/projector plus PID/expiry probes pass
  **4/4 in 1.11s**; scientific witnesses and production containment remain separate gates.
- Delivery team finished without publication. Its semantic loader/receipt and partial startup
  packets are retained for clean acceptance; final canonical pins remain unset/compatibility-only.
  Audit found no real StartupManifest artifact or non-test factory. Existing --dry-run consumes
  a prebuilt manifest, not the requested real production export→candidate enrollment→preflight→
  dashboard chain. New AKU-07n owns the bounded manifest builder and installed-chain verification;
  generated export repair retains its existing separate operator gate. No fake config is counted.
- Checklist: **one completed sub-item (AKU-07l), one new open task (AKU-07n), zero declines**.
  Accepted implementation sub-items now **41**; all twelve parent tasks remain open. No real
  dry run, five-loop hardware run, provider grant, service activation or production kernel change.
  Per-task wrap-up only; no pruning, compaction or wiki sweep. README freshness is clean.
