# FM-4 Codex dispatch projection preparation

The registered `fm4-gate-acceptance` source accepts both the existing
selected-gate bundles and an explicit read-only Codex replay descriptor.
Replay validates the filed census, input pins, collector version, original
read-only rollout bytes and exact receipt. The public claim points to the
filed census digest and pair ID. The new terminal-dispatch metric and
authority are scoped to a bound first child turn and preserve a null task
outcome. Both source inputs use the same `ClaimTuple` carrier and grade.

The Codex canary uses the registered ingest source, an isolated ledger, and
the real shared planning reader with consumer `coordination.fm4`. It checks
the selected claim IDs and locators, Judged/Located harness scope, exclusion
from reliance, exclusion from `autokernel.planner`, and zero selected-gate
claims. Each result keeps the scrubbed native receipt. There is no separate
production `coordination.fm4` reader call site in the inspected coordination
scripts. Suitable task-gate and end-to-end oracle acceptance are separate
from this dispatch replay. The local checkout lacks the D9 acceptance API.

## Validation

- Focused dispatch and projection controls passed, 37 tests. Controls include
  successful and interrupted first turns, launch only, ambiguous spawn and
  child turns, digest and identity drift, read-only snapshot custody, typed
  receipt mismatch, and attempted task-outcome promotion.
- The detached checkout passed an isolated system Python CLI synthetic
  replay. Its launcher passed `bash -n`. This preparation ran no live smoke
  or official native row.
- GitNexus found no index in the lane. Read-only impact against the canonical
  stale index returned UNKNOWN because its database format is version 41 and
  the installed CLI opens version 40. Source tracing limits the change to
  the existing FM-4 source entry point and canary.

## Packet

- ID `vb-fm4-codex-projection-20261118`.
- Spec `spec.json` SHA-256 `467a169cdb495a3a675883e07b5459899a7a31b154f1361b6baaadbd9b77f232`.
- Launcher SHA-256 `206658ac76644cc95d5d23220e70ba06522a7e5559c627ed5c04968c78af8820`.
- Job SHA-256 `38da35a7c3d92f0b935b12057f39c1c63c1febb8f3cd8edee06392106c9dc167`.
- Source manifest SHA-256 `1ba82267185a3bc98e151d6612e1a30a39b57d13e7ecf4f6347a333c8db272f6`.
- The 316-file manifest pins the sparse detached checkout at
  `1111b6b95363330db613c52a1759dea25a1aa982`, including the adapter, ingest
  and canary overlays. The row can run after lane reaping.
- Model-free smoke selects one original pair. Official replay selects both
  fixed pairs in one isolated ledger. Both operate on four granted CPUs with
  a 300-second estimate and hard cap or earlier allocator deadline.

After an actual publisher PASS, the owner can close
`VB-FM4-CODEX-PROJECTION-PREP` with a recorded native-smoke observation.
The official two-pair result and suitable task-gate/oracle acceptance
remain open in `VB-FM4-ORACLE-WIRE`.
