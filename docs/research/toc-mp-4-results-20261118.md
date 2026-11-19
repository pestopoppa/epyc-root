# TOC-MP-4 exact-value recall screen, 2026-11-18

The decision is **UNKNOWN**. The first official cell completed its graph run
and received an immutable UNKNOWN grade when assessment could not verify the
native tail witness. The instrument stopped the allocator window and verified
that its private listener exited. [Prospective protocol](../design/toc-mp-4-needle-protocol-20261118.md)

| Arm | Scheduled | Recorded | Eligible | UNKNOWN | Unattempted |
| --- | ---: | ---: | ---: | ---: | ---: |
| `summary_only` | 40 | 1 | 0 | 1 | 39 |
| `summary_pointer` | 40 | 0 | 0 | 0 | 40 |
| `pointer_only` | 40 | 0 | 0 | 0 | 40 |
| Total | 120 | 1 | 0 | 1 | 119 |

All 40 paired comparisons are UNKNOWN. The protocol requires 120 eligible
grades and forbids retries or seed replacements. The frozen UNKNOWN limits
this matrix to at most 119 eligible grades, so the cohort ended inconclusive.
There was no successor grant for this matrix.

The first cell, `archive-01/0/summary_only`, recorded the required read-only
scope and all four private-source denials in `FIXTURE-AUDIT.json`. The native
trajectory and wire capture recorded the turn-3 boundary and continuation.
That response reached its 128-token cap with no executable REPL code. The
trial's audit sampled tail state only inside REPL execution on turn 3, so its
next execution on turn 4 could not supply the witness. The assessor recorded
`private_source_confinement_unverified`. The missing witness leaves the final
submission ungraded.

The corrected fixture snapshots the native tail and live request scope when
generation starts on the boundary turn. Assessment requires that witness and
checks the served continuation independently. A response can finish on the
wire with `[DONE]` and still report `finish_reason=length`. The corrected
assessor records that generation as UNKNOWN. Offline tests used the pinned
graph source and a network-blocked mock transport. They cover complete and
token-capped code-free boundary responses followed by a turn-4 submission.
They also verify rejection of missing or wrong-turn witnesses, mismatched
scope, a retained needle and corrupted wire custody. The original attempt
retains its UNKNOWN grade.

The original packet, native receipts, prepared artifacts, and keeper end
receipt were byte-compared with a private copy at
`/mnt/raid0/llm/tmp/delegation-context-preassembly/mp4-failed-20261118`.
The archived `packet/inputs.json` SHA-256 is
`169338675bcce48ef0400431e607f4a269d2d0ff8850630d6d27a23b44f47b29`.
The archived `native/PARTIAL.json` SHA-256 is
`f07f9af34c84c4bad4eb7aef2b6ab349786e903ab0d02cdbfe60198063c0007b`.
