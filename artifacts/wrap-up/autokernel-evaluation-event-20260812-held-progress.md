# Held progress insertion — AutoKernel live evaluation-event writer

**Date:** 2026-08-12  
**Target after coordinator freeze lifts:** `progress/2026-08/2026-08-12.md`  
**Why held:** that daily progress path was temporarily frozen while the fleet merge landed. This
checkpoint intentionally did not edit it.

## Problem

The runnable AutoKernel campaign retained executed T0/T1 evidence but did not prospectively append
the corresponding schema-valid `EVALUATION_EVENT` before terminal STOP. Its first implementation
also risked laundering release-time facts into window attestations: a released claim receipt cannot
prove that the claim, anchor, evaluator bundle, runtime authority, or host stayed valid through the
last measured block.

## Changes

Research commit `d96e87047852cd854f743b0da146f8f2b4b070d5` on
`codex/autokernel-evaluation-event-20260812` now:

- builds T0 and T1 events from retained executed evidence, with raw paired-block vectors and the
  exact fixed-N reduction;
- appends evaluation evidence idempotently before terminal STOP, records early T0 refusals, and
  makes an evaluation append failure terminal without skipping cleanup or STOP;
- emits the exact Vidya AutoKernel write-side capture, bound to event/campaign/candidate identity,
  source/binary/model/resource identities, repetition count, and raw-sample hash;
- closes the evaluation window while claims and worktree are still held, using fresh CPU/device
  claim checks, native open/close inference-preflight receipts, host/storage reads, evaluator and
  runtime-authority hashes, and a fresh anchor capture for each exact tool;
- binds the complete CPU-plus-device release receipt and retains the exact recipe receipt used to
  create each T0/T1 request, so teardown cannot trigger a reconstructed recipe claim; and
- refuses missing stable holder identity and journals anchor, evaluator, claim, or host drift as
  INVALID evidence rather than constructing PASS.

## Verification

From the clean final commit, 1,231 tests passed in 33.726 seconds across campaign, campaign
footprint, control runner, journal, evaluator API/correctness/statistics/integration, and execution
chain suites. GitNexus was refreshed and reported the index current at `d96e8704`. The branch was
pushed to `origin`. No inference, kernel build, or resident-stack operation occurred.

## Remaining empirical work

After the already-recorded compliant reboot dependency is satisfied, run AK6.5 Step 3's full-host
CPU IQK proposal under the accepted frozen-v9 control bundle. Then materialize the first real matched
completed-proposal archive and run AK-WM-2/AP-WM-1b observe-only. Synthetic fixtures remain regression
tests and do not substitute for that evidence.
