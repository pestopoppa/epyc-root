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
- Research candidate `codex/evl46-scorer-isolation-20261102` @ `ed1e69e7a`: optional
  bubblewrap isolation, fail-closed when setup fails; six controls and scorer smoke passed.
  Actual namespace setup refused on this host. Hidden tests are still visible in the candidate
  program. Neither isolation acceptance nor TU-GR-1 is complete. [no-belief: source controls]
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
