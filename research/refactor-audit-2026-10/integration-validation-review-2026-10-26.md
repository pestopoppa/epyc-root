# Integration candidate validation review — 2026-10-26

This record captures owning-main review of the private orchestrator integration candidate. It does
not authorize merge to main, deployment, or production activation.

## Candidate and validation

- Branch: `refactor/orchestrator-integration-01a16fc3`
- Published candidate: `851955112b8ba8c2911a7684469551afa1541623`
- Immutable comparison base: `84f6f6f15f713d21098dbad2b153d32f8cc13624`
- Expanded union: 111 files, 2,897 passed, 8 skipped, 0 failed of 2,905; all four source coverage
  floors at 100%; no checkout-write warnings.
- Main reviewed the 17 source/test diffs and final proof. AST, focused suite, Ruff, scoped format,
  compile/diff, 32 NI63 pins, and four P5 file-preservation proofs passed.

## Formatter comparison correction

The historical final-proof run remains recorded as terminal `FAIL` because its formatter comparison
used mutable `origin/main` at `d825274d`, which reconstructed 232 files. The accepted immutable base
`84f6f6f1` has 182 scoped files. All 44 extra failing candidate blobs are byte-identical to that
base and lie among 50 scope additions; the exact 182-file intersection has the same 133 failing
paths as the stored baseline. Therefore the accepted scope has zero introduced formatter failures.
This is a correction to validation bookkeeping, not a new formatter run or source change.

Durable evidence: `/mnt/raid0/llm/tmp/refactor-01a16fc3/orchestrator-integration/format-scope-correction-20261026.json`.
The underlying final run artifacts remain under
`/mnt/raid0/llm/tmp/refactor-01a16fc3/orchestrator-integration/`; preserve its terminal status and
logs as historical proof.

## Scope boundary

The candidate is validated relative to immutable base `84f6f6f1` only. It is not a claim of latest
main compatibility, a main merge, deployment, or production activation. O8 and P3 remain WIP and
must complete their own package validation against this candidate.

## Dependent source progress later on Oct 26

CI now contains this candidate in local-only merge
`753e0287a1ae6b06f2a5c91269899ff8cc8452b5` (parents `713edf671` and `851955112`), with 13 focused
tests passing. Its official B1 attempt failed before collection on custody hashing through public
carrier directory symlinks; the corrected helper metadata proof passed, then attempt 2 collected
20,646 baseline tests plus an unregistered `slow` marker error, with no candidate collection.
The corrected strict collection later passed: baseline 20,658 total/20,645 selected, candidate
20,666 total/20,653 selected, 0 removed/8 intended additions and 13 identical exclusions.
This is collection parity only; full-suite baseline/native/coverage gates remain open.
P3's corrected final 12-file functional selection
passed 402 tests with one skip; official three-file formatter closure passed AST equality,
non-target bytes, format/protected/no-new-Ruff/diff/custody. Final private source
`fb5db1a0a24b92172643bb670c77a4343a508c96` is published and exact-remote verified on
`codex/refactor-autopilot-actions-01a16fc3`, with a clean worktree and owning-main acceptance.
The source checkpoint document maps all 16 findings to behavioral warrants. See the
[Oct 26 chronology](../../progress/2026-10/2026-10-26-refactor-next-packages-checkpoint-01a16fc3.md)
for failed runs and limits; this does not expand the integration candidate's validation claim.

The later B2 baseline completed at 13:13:11 UTC with 31 failed, 20,517 passed, 85 skipped,
19 xfailed and six passed subtest events in 2,146.45 s. Native conformance remained NULL for
an unnamed collection-skip case and shared grading emitted no JSON. Sixteen ignored runtime
paths leaked while tracked repository/harness custody matched. No candidate full run or accepted
known-failure set is established. Root `bb6410b1` is a private publication and was not accepted
or merged by workspace-58; the owner requested a separate evidence/index correction.

## Findings retained for the next operator wiki sweep

The private branch's wiki synthesis is withdrawn following the owner's 16:40 review. Its findings
remain in this research record and the linked Oct 26 chronology for operator compilation:

- Immutable comparison scope matters: the moving-base formatter failure remains an original failed
  receipt; only the separately reviewed 182-file immutable scope establishes zero introduced paths.
- Package states require separate evidence: local integration, a focused functional selection,
  private source publication and main acceptance are distinct. The P3 402/1 selection and final
  three-file closure do not establish a current all-1,930-pass aggregate.
- A region-lock waiter is not calendar authority. The canceled root waiter and later official q1
  run retain separate receipts; the official launcher owns admission, affinity and deadlines.
- Passing local root gates did not supply owner acceptance. B2's failed baseline, native NULL,
  missing grade JSON and ignored runtime leaks remain unresolved evidence, not an accepted baseline.

No new run, wiki compilation, manifest advance or grading is asserted by this extraction. The owner
compiles these existing findings at the next operator-cadence sweep; the newer canonical manifest
from `f6ba6877c` (41 sources) is preserved by dropping this branch's entire manifest contribution.
