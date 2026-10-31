# C4-01 strip-plan reconciliation — 2026-10-31

## Decision

The old C4-01 deletion advice is superseded. Preserve all 19 INF64 candidate source/test/data units. In particular, preserve both `evaluator/c3_apex_runner.py` and `evaluator/c3_epyc_compiler.py`, as well as the three C3 evaluator modules the old C4-01 proposal also discussed. This closes only the ROOT follow-up to reconcile C4-01; it grants no runtime reachability finding, deletion authority, or campaign-owner approval.

## Pinned accepted source evidence

- The accepted manifest is ROOT `artifacts/ni08/inf64-source-reachability-review-20261007/completed-manifest.md`, source commit `1b2c0c0aa959e162d492ba367ce15b36074033eb`, committed in ROOT at `f219064ba` (current private-lane base `12ffc57a5b3e38d7a63d0a3e666e435c99fa97cb`).
- Its exact disposition is `exact-reference-disposition.json`, SHA-256 `e370c70cd7a75f279c39aacd21b7bb71e0ac358db27ea65886f3562e1096b518`; MAIN review is `MAIN-completed-manifest-review.json`, SHA-256 `3bee3b1d3b28d64f6d97f364552373f648b62a75e80dbd5fc4b46e9718e98a46`.
- `MAIN-completed-manifest-review.json` records `source_integrity_review: PASS`, the exact pins ROOT `1b2c0c0aa959e162d492ba367ce15b36074033eb` and Research `f770a52514f3193db44268d61da86f1235122a20`, 19 candidates, 19 paired tests, 2 adjacent data files, 3 guards, 64 unique verified source blobs, 145 verified incoming reference rows, and disposition `retain: 19`, `remove: 0`.
- `completed-manifest.md` states all 19 dispositions retain their source/test/data units. Its review explicitly limits this to pinned source evidence; it does not claim runtime reachability or authorize deletion.

## Current ROOT strip guidance cross-check

At ROOT `origin/main` base `12ffc57a5b3e38d7a63d0a3e666e435c99fa97cb`, `handoffs/active/autokernel-restart-and-strip.md` lines 78–95 contains the 19-member list, says the 2026-10-25 current-pin re-screen retained all 19 (12 positive-edge, 7 intentional off-path with invocation unestablished), and records zero proven obsolete / zero deletion candidates. Its lines 282–289 separately record the current-source correction, all-19 retain disposition, and INF64 manifest completion. The handoff banner at lines 3–4 directs readers to the completed manifest before any strip work.

The C4-01 historical proposal appears in `research/refactor-audit-2026-10/BUG-REPORT-autopilot-autokernel.md` under C4-01: remove `c3_epyc_suite`, `c3_epyc_tensor_capture`, and `c3_epyc_capture_provider`, while keeping `c3_apex_runner` and `c3_epyc_compiler` on the strip list. The later ROOT strip guidance and accepted INF64 disposition supersede that exact advice: all five modules are among the 19 retained candidates.

## Boundaries

This is a source/document reconciliation only. No source module, paired test, dataset, guard, campaign file, kernel, or historical evidence was modified or executed. No removal proposal was prepared. The existing `VB-INF64-REACHABILITY-CONFORMANCE` task remains separate and open for prospective native controls.

## Reproduction references

- Current ROOT base: `12ffc57a5b3e38d7a63d0a3e666e435c99fa97cb`.
- Accepted manifest introduction: ROOT commit `f219064ba`.
- Accepted manifest pins: ROOT `1b2c0c0aa959e162d492ba367ce15b36074033eb`; Research `f770a52514f3193db44268d61da86f1235122a20`.
- Candidate dispositions are the 19 entries in `exact-reference-disposition.json`; each has `disposition: retain`.
- Durable acceptance record: `MAIN-completed-manifest-review.json` (`source_integrity_review: PASS`, `retain: 19`, `remove: 0`).
