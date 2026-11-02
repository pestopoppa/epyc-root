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
