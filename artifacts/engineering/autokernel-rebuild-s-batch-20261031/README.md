# Autokernel S-code wrap capsule — 2026-10-31

Three already reviewed software-contract completions are filed from their existing source commits. This ROOT capsule records evidence only; it does not claim a native workload, deployed change, production-kernel change, or newly wired belief reader.

## R23-30 boundary stop grace

Research main is `37dcdcd53f4cfbb27dd80564d5fc4bf407a0c566`. The confirm-rung grace is configurable workers × per-measurement budget and defaults to 7 × 1200 s = 8400 s (140 min); explicit `BOUNDARY_KILL_WAIT_S` still overrides it. Eleven focused tests passed, including virtual 87-minute drain and captured-child `/proc` absence; verified-PID stopping and survivor refusal remain. Evidence: `r23-30/summary.md`, compressed baseline and candidate logs, and the final combined research suite in `combined-test.log` / `lane-validation.log`.

## INF-70 sibling-expanded affinity reuse

The same research commit adds bounded native CPU-affinity observations to actual GPU serving residency export by reusing the existing topology and live CPU-tick sampler. Facts preserve kernel sibling topology, observed task permissions, `/proc` executable locator, identity-stable interval ticks, and potential physical overlap. Incomplete topology or task census remains unknown; this is not an interference rule or placement warrant. Ten focused tests passed, and the complete targeted set passed 63 tests plus 8 subtests. See `affinity/summary.md` and the combined/final logs.

## Deterministic FIFO-off control

Orchestrator main is `9e1155a10f809d9c63a818fd95b5e02276d0e43a`. The original test task uses native failed-poll/Event barriers and proves opposite FIFO-on/off order without xfails; the native module passed 24 tests. Restoring the previous fairness assertions yields exactly three FIFO-off failures. Production code and `EPYC_LOCK_FIFO` default remain unchanged (OFF). See `fifo-control/receipt.json`, `review.md`, and both logs.

## G2-CONC-LIB library fix

Research main `e95a9d2e25c3eeedc7a6f997e608d9bd338cbc31` adopts amendment-5 detector v2.1 in the shared full-text `classify`/paired-gate path. The original 19-case fixtures remain; the change is enrolled in `PYTEST_SMOKE`. The accepted package suite passed 87 tests. Stored-stat replay remains v2 and v1 remains frozen. No historical result was regraded and no live reload occurred. Evidence: `g2-conc-lib/receipt.json` and the full validation log.

## Belief capture follow-up

The existing AutoKernel direct-serving source family is extended prospectively with the captured `cpu_affinity_observation` facts. The existing `VB-AK-LEGACY-SERVING-LIVE` task remains the owner: add reader/tamper/unknown and planning-context-canary coverage for GPU facts, without creating a task split, grade, historical measurement warrant, or a wired-reader claim. Source path remains `scripts/vidya/adapters/README.md`.

## P17.BT-5c retirement note

The original producer-specific P17 pair has no current runtime caller after its earlier retirement, and its only prior evaluation was negative/non-certifying. Record the retirement as a prose finding only; the original checkbox remains unchecked because a future peer-judged experiment requires a new positive producer. This is outside the completion quota.

## Immutable source evidence

- Research landing receipt: `LANDING-RECEIPT.json` (full source SHA and changed-file hashes).
- Final research verification: `lane-validation-receipt.json` and `lane-validation.log`.
- FIFO landing receipt: `fifo-control/receipt.json`; original scratch review and logs retained beside it.
