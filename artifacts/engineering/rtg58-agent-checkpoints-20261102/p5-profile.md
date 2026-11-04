# KPF-50 successor checkpoint, 2026-11-02

- Source successor `experimental/rtg58-kpf50-iteration-20261102` at
  `1e8a6d5da`, descends from merged candidate `3ec14227a0`, P3 phase
  instrumentation `805baaf5e`, and target-only scope `2c45b372c`.
- The target-step marker and its enclosing server-iteration marker use
  `CLOCK_MONOTONIC` and explicit target/draft synchronization. The iteration
  includes `pre_decode` draft generation, decode and post-decode but excludes
  inter-callback gaps. `KPF50_DRAFT_BEGIN/END` reports active drafting slot
  count and the synchronized draft-call interval. Synchronization changes
  scheduling; no production speed claim.
- Counterfactual mask is default-off and only drops exactly 60,000 visible
  cells common to all four active sequences in full-attention qualifying
  >=80k target ubatches. Every row must pass before any mutation. Input tokens,
  positions and a physical-layout signature are recorded. Only the first
  eligible masked step is comparable; later steps use diverged state. Matching
  inputs/layout does not prove equality of K/V values.
- Five direct mask/refusal assertions passed on CPU. The step-only predecessor
  `8a563944a` linked CPU server built, and Qwen3-0.6B CPU server flag-off/on
  smoke returned identical text, with markers absent off and present on. Its
  first generated-model smoke was invalid because that model lacks a tokenizer.
  The final successor's two changed translation units compiled under claim; object strings prove target-step, iteration, draft and mask markers. This is not a linked build.
- Research companion `scripts/benchmark/kpf50/` has HSA/host clock sampling,
  profiler clock-witness verifier, fail-closed dispatch analyzer, first-step
  pairing, a hash-pinned runner patch and 23 Python fixture tests. Direct trunk
  time remains unknown; tool does not issue a 20% verdict.
- At 14:26Z old step-only HIP build PID 228904 was active under CPU cores
  86–87. Durable upgrade PID 315661 waits for its successful receipt, advances
  its isolated source worktree to `1e8a6d5da`, incrementally rebuilds and hashes
  the final linked HIP binary. Final linked CPU build/smoke PID 353071 is active under CPU 84–85.
  GPU waiter PID 358506 waits for that CPU receipt, the upgrade and
  P3 phase predecessor PID 279983 with its FINISHED/EXIT_CODE receipt. It first
  runs a bracketed HSA/host + rocprof GPU clock witness; failure refuses the
  model profile. It then runs 4 × 80k, 60k fork-on full/mask/mask/full windows.
  Source/binary/profiler/runner pins are in `runner.sha256` and `BINARIES.sha256`
  after the build; all attempts are retained.
- Both queued processes are PENDING, not inference results. Parent session owns
  handoff/index/progress and must update them from actual receipts, not from this
  checkpoint. Once runs complete, validate clock alignment and first-step
  query/layout matches, derive only counterfactual estimates, and retain all
  refusals. KPF-50 stays open until decision-grade attribution and the governing
  gate are established.

- Research companion branch `codex/rtg58-kpf50-profile-20261102` commits `7ec57cf3c`, `8665616be`, `db8b43d21` (local, not merged), containing the 23 passing tests and hash-pinned profiler runner patch.
