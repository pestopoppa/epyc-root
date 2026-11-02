# EVL-46 execution-readiness audit — 2026-11-02

Audited the tool-use evaluation handoff against ROOT `2d95a8a371` and orchestrator
`9301fb7bc81663d176f11ebf21bf496d4ac725a3`, the retained CRM pilot entry and its filed
result. Added a current execution map, source/evidence boundaries and ordered acceptance plan.
`crm-benign-001` has no attack family; the retained service runner hard-codes that case and
cannot supply the originally described matched attack arm. The revised dispatch requires a
matched control and attack for one actual indirect case and records the benign result separately.
The generic native DTAP runner still returns placeholders for live tool calls; the separately
retained CRM service pilot has real effects only for its one benign case. Existing belief
registrations and the HS-4 catalog-comparator gap are explicitly carried forward.

This is source and operational review only: no inference, code execution change, new result,
qualification, task closure or retroactive measurement warrant. GitNexus reported CRITICAL
file impact (253 upstream, nine direct) on a stale index; operator directed continuation with
judicious review. The edit preserves existing task text and history. [no-belief: source review]

## Implementation checkpoint

- APP candidate `codex/evl46-seed-ledger-20261102` @ `9c51d450`: opt-in seed HTTP transport
  with explicit request trace and backward-compatible default; closed-trace single-call native
  validity and terminal timeout projection. Combined 163 DTAP tests passed under q0 from a
  protected worktree. An earlier test from the group-writable worktree correctly refused its
  private-capture ancestry; the protected retry passed. No provider determinism or completed
  TU-LED-1 claim. [no-belief: software controls]
- Timeout-report reader now accepts the exact reviewed APP runner/endpoint pair as an atomic
  source set, preserving old receipts and refusing mixed revisions. A protected producer and
  reader checkout passed 25 native producer-to-projection/CLI tests; not a live canary.
  [no-belief: software controls]
- Research candidate `codex/evl46-scorer-isolation-20261102` @ `ed1e69e7a`: optional
  bubblewrap isolation, fail-closed when setup fails; six controls and scorer smoke passed.
  Actual namespace setup refused on this host. Hidden tests are still visible in the candidate
  program. Neither isolation acceptance nor TU-GR-1 is complete. [no-belief: source controls]
- Research successor `39480fa8f` adds pinned-image Docker mode and caller-affinity-bounded CPU
  sets. Under a q0 claim the real scorer path denied a host file and network, used the expected
  CPU set and cleaned its own container on completion and timeout; nine tests passed. Different
  interpreter and visible embedded tests prevent a full grader-isolation claim. [belief: cc]
- Research `8a314b790`: fixed synthetic trusted-reference probe under a q1 claim passed seven
  reference/path/process/environment/FD/network/export/affinity controls; 13 focused tests
  passed. Scope is the Docker scorer probe, not live REPL, OpenCode or embedded tests. [belief: cc]
- APP `codex/evl46-crm-pair-20261102` @ `946aa705` prepares the paired core, source-pinned
  adapter and partial receipt. In actual model-free service startup the current Slack image
  refused missing auth, while a pinned legacy image started but exposed a FastMCP adapter mismatch;
  captured services and network were removed. A concurrently started R18-A smoke was stopped by
  its owner; this control was not a timing measurement. The adapter and launcher remain open.
  [no-belief: engineering setup]
- APP combined candidate `b61c4747` carries the paired core and judge attestation. The q1
  service-only control succeeded with actual private CRM and Slack, reset equality, native note
  and message, and owned-container/network cleanup; the receipt is in APP
  `docs/evidence/dtap-crm-service-control-20261102/`. Combined 174 DTAP tests passed from a
  protected checkout. No model or pair verdict. [belief: cc]
- APP `086a103d` adds producer-side native receipt sealing with explicit failed/not-attempted
  arms; a scripted pair reached the real services and native judge with suffix delivery. The
  integrated DTAP suite passed 177 tests under q2 from a protected checkout. Physical-grant
  authority, reader canary and live row remain open. [no-belief: fixture controls]
- Rowflow `evl46-crm-fullentry-fixture-20261102` passed exact-entry smoke and is grantable;
  its full scheduled run is a scripted-endpoint service/claim qualification, not model evidence.
  The live pair and separately scheduled post-run model hash remain in preparation.
  [no-belief: fixture controls]
- ROOT `4f609b459` + `bb252dbc6` + `bf9dbd64c` add a fail-closed pair receipt reader;
  three tamper/fixture/aborted controls passed under q2. It is not CLI-registered and emits no
  claim without provider/source authority. A lock-provider receipt is being built. Research
  `544a240c9` adds a bounded synthetic client-tool endpoint broker (24 tests), without a live
  OpenCode or `/chat` isolation claim. [no-belief: software controls]
- APP `1e02f2e2` adds an opt-in provider-owned full-quarter CPU lock open/close receipt and
  source/grant bindings; three targeted tests passed in the combined checkout under q3. The
  receipt does not prove child affinity or independent grant issuance. Research `b2dc50a86`
  adds bounded buffered SSE transport; 10 fake-upstream broker tests passed, with actual
  OpenCode compatibility and timing still unverified. [no-belief: software controls]
- Rowflow `evl46-opencode-fake-20261102`: exact-entry smoke PASS, state grantable; real pinned
  OpenCode against fake upstream made three streaming calls, read a public file, could not read
  the host canary and exported its session. The synthetic config unexpectedly advertised shell,
  write and other tools despite its read-only intent; catalog enforcement stays open. No model
  inference or production isolation claim. [no-belief: synthetic control]
- Rowflow `evl46-crm-reader-b8-tests-20261102` is grantable after its isolated smoke passed five
  reader tests. Correction: its CPU-lock source pin is truncated, so that smoke is not current
  reader acceptance; b8 was withdrawn. Corrected successor `evl46-crm-reader-a656-tests-20261102`
  passed six smoke controls and is grantable. Neither row is a live inference claim.
  [no-belief: software controls]
- Rowflow `evl46-opencode-policy-20261102` smoke passed with explicit `permission` settings:
  only `read` advertised, injected `bash` rejected, workspace read and session export passed.
  Its grader-path refusal is a permission result rather than an OS syscall proof. The row is
  grantable and waits for allocator execution. [no-belief: synthetic control]
- The fake and policy rows' redundant scheduled repeats were withdrawn; their full smoke
  receipts remain. `evl46-opencode-schema-20261102` passed its own smoke with the pinned
  read-tool schema and broker refusal of injected `bash`, and is grantable. [no-belief: synthetic control]
- Added `docs/reference/tu-hr1-tool-render-audit-20261102.md`: source and runtime census;
  sampled local model endpoints were unavailable, so actual live model/template evidence and
  TU-HR-1 remain open. [no-belief: source and operational review]
- ROOT `df0b7b8c8` + `efcd010dd`: fresh public fixture preparation and synthetic REPL/OpenCode
  adapter controls; 46 tests plus five subtests passed under q0. No live driver, chosen scorer,
  isolation, SC86 result or TU-MH-1 completion. Updated EVL-46's thin index next action;
  stale GitNexus marked that index CRITICAL (316 upstream, 29 direct). [no-belief: software controls]
- ROOT `4e9d25de0`: fail-closed `/chat` and OpenCode transport plumbing with 49 tests and five
  subtests; no live I/O is enabled until real isolation, and child-tree drainage is unfinished.
  [no-belief: software controls]
- ROOT `eb870805e` adds captured-descendant timeout cleanup with PID/birth checks; 51 tests and
  five subtests passed. Escaped descendants remain unknown. The nearby exact-match scorer
  accepts wrong leading content before a correct final line and remains unqualified for the
  whole-answer file tasks. [no-belief: software controls]
- ROOT `1e699f931` adds task-specific canonical-JSON validation before the unchanged native
  exact-match scorer, plus six development and twelve acceptance synthetic fixtures. Native
  positive, wrong-answer and extra-line controls passed; 56 tests and five subtests passed.
  Scorer binding, sealed split and live isolation remain to be demonstrated. [no-belief: software controls]
- ROOT `69e9e3d5e` binds the native scorer's reviewed source digest and seals the prepared
  fixture/prompt/oracle hashes; 58 tests and five subtests passed. File permissions are
  owner-reversible and do not prove isolation. [no-belief: software controls]
