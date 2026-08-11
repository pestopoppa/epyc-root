# S4 Omega: MultiPaper child-prompt arm — 2026-07-29

## Purpose

Add one controlled intervention arm to the existing S4 Omega A/B, not a runtime
default.  The intervention tests whether explicit REPL discipline changes turns per
task and token cost without reducing accuracy.

## Arm definition

Keep the model, tool surface, task set, decoding settings, and maximum-turn safety
cap identical to the S4 control.  The treatment prompt adds only these behavioral
constraints derived from the reviewed MultiPaper child-prompt pattern:

- state a useful-turn floor as well as the existing ceiling: do not end after a
  shallow two-to-three-turn attempt when the task needs investigation;
- follow the ordered search -> expand -> extract -> verify workflow when applicable;
- preserve same-block causality: an extraction may consume only a result available
  from a prior REPL block, not a search result produced in the same block;
- do not declare a final value in the same block that performs extraction.

This is a prompt-only arm.  It does not import SkyRL code, enforce unsupported
four-child/ten-round constants, add sub-model calls, or copy its cache-hostile query
layout.

## S4 record and decision rule

For every arm, record task IDs and prompt hashes; completed-task count; turns/task;
main-model, sub-call, and total tokens/task; accuracy; and latency p50/p95.  Report
accuracy delta against the no-intervention control.  Retain the existing maximum
turn guard and stop/revert the treatment if it has an accuracy regression, violates
the cap, or increases both total tokens/task and p95 latency without a compensating
accuracy gain.  A result must carry the normal measurement protocol, sample size,
date, and attestation reference before it gates further suggestion/verbosity work.
