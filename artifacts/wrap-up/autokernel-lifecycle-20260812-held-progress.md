# Held progress insertion — AutoKernel source lifecycle and champion plane

**Date:** 2026-08-12

**Target after coordinator freeze lifts:** `progress/2026-08/2026-08-12.md`

**Why held:** the fleet merge still owns and freezes that daily progress path. This checkpoint records
the completed work durably without creating a competing edit.

## Problem

The runnable AutoKernel campaign could retain prospective evaluation events, but it did not yet turn
a source-changing proposal into one immutable, provenance-complete candidate record. The previously
removed broad controller also left no current lean path from validated banked outcomes to a composed,
directly remeasured champion.

## Changes

Research `main` merge `069e79fd53afc8f452dd2af80c684ae4cbc4273a` integrates:

- the source-candidate branch `06f0b75e` (integrated as `9083843a` plus `a381745d`): an embedded
  content-addressed patch is loaded
  before claim acquisition, strictly validated, applied only through the guarded worktree API, and
  converted into an idempotent candidate record from the exact clean built snapshot and the cached
  evaluation events produced while resources remain held;
- the lean lifecycle branch `57363905` (integrated as `8a2e6f5d`): journal-derived banking and
  frontier projection, compatibility checks, direct composed-candidate T0/T1/T2 evaluation, champion
  preservation on failed/rejected composition, exact-anchor drift refusal, and sealed-receipt-bound
  reanchoring; and
- a cross-branch fixture correction (`68055876`) proving the merged candidate rather than either
  source branch in isolation.

The sequencer has no host mutation, build, benchmark, release, or production-write implementation;
those operations remain injected authority boundaries. It cannot synthesize performance by adding
member gains: a champion cites only the combined candidate's passing evidence.

## Verification

The combined focused suite passed **577 tests with 790 subtests**. From the exact promoted merge
commit, the package-wide suite passed **4,530 tests**, **one expected failure**, and **2,039 subtests**.
Both implementation branches and the integrated branch were pushed, and `069e79fd` is on research
`main`. No inference, kernel build, profiler capture, or resident-stack operation occurred in this
checkpoint.

## Follow-up release and EPYC campaign restoration

Research `main` advanced again to `99fe3014f76f5d2a3dcd2bd7502a371abc0db1b0`. It restores the
operator-triggered readiness, T3, and release-package modules as a release-local plane that is not
reachable from the lean campaign. Pure preflight reducers consume supplied host/resource/storage
receipts; AST-enforced boundaries deny source mutation, process execution, production writes,
drafted-command execution, and self-triggering. Real release mode still refuses because
`P-KERNEL-FREEZE-1` is not ratified; the restored v8/speech paths are dry-run calibration fixtures.

The same merge replaces the add-only Arena task proxy with four hash-pinned EPYC-representative
tasks: add, Llama attention, MoE GEMM, and dequantize-matmul. The six available controller arms keep
their source/license/entrypoint pins, and the campaign still names EvoEngineer and ARGUS as missing.
No controller or GPU campaign ran. The exact final merge suite passed **1,267 tests** with
**849 subtests**.

An independent stale-checkbox audit also confirmed that AK9's speech release-plan compiler task is
complete rather than merely restored in source. Both adapters produce the generic compiler binding
for their own independently freezable tree; the compiler covers the speech source-tree shape; and T3
consults both speech readiness predicates, branch family, linkage requirements, and preserved freeze.
The exact-main adapter/plan/T3 slice passed **783 tests with 132 subtests**.

## Follow-up ROCm C3 and source-prerequisite authority

Research `main` advanced to `d8013a6c66decf023bf4efb7a83033d72ecc4f0f`. The EPYC C3 compiler
now requires exact frozen-v9 source, version, binary, linkage, and operator-attestation identity for
the native Q4_K dequant baseline; a provider label alone cannot authorize a comparison. The selected
attention/MoE cases remain hash-pinned C5 references with their explicit Torch-ROCm-compile floor.

The same commit makes the existing sensitivity, hostile-distribution, and checker-isolation reducers
real source-candidate T0 prerequisites. Their reports have no authority until measured provenance
binds the candidate source, evaluator bundle, suite version, trusted producer, and evidence digest;
missing, dry-run, or mismatched bindings fail closed and parameter candidates cannot carry them. The
exact-main C3/source-authority/correctness/execution suite passed **444 tests with 132 subtests**.
No inference, GPU capture, benchmark, or kernel build ran.

## Remaining empirical work

After the already-filed compliant-reboot dependency is satisfied, run AK6.5 Step 3's full-host CPU
IQK proposal. That real run must produce the first matched completed-proposal archive and then feed
AK-WM-2/AP-WM-1b observe-only. Synthetic candidate/champion fixtures remain regression tests and do
not satisfy either empirical gate.
