# FM4 native dispatch projection readiness

This packet separates native dispatch observations from selected-gate and task
acceptance. The two original Codex parent/child pairs were captured and filed in
[`fm4-native-ready-20261118`](../fm4-native-ready-20261118/). Their first child
turns have terminal records; their task outcomes remain null. A terminal record
supplies no selected-gate or task-success verdict.

The projection uses the existing `fm4-gate-acceptance` source and shared carrier.
Native dispatch observations must replay the retained read-only private
snapshots and match the original sealed receipts. The prospective planning
canary uses an isolated ledger and the `coordination.fm4` consumer; it must
exclude unrelated consumers and selected-gate success claims. Official native
canary acceptance and suitable task-gate/oracle acceptance remain separate.
The inspected coordination scripts have no production `coordination.fm4`
reader call site. This packet exercises registered ingest and the shared
planning reader; integration into a running coordination loop remains open
in `VB-FM4-ORACLE-WIRE`.

## Scratch cleanup

[`scratch-cleanup.json`](scratch-cleanup.json) records removal of seven
superseded directories, reclaiming 59,016,028,160 allocated bytes (54.96 GiB).
The remaining scratch allocation was 11.88 GiB. Current qualified-row inputs,
FM4 private snapshots and active research worktrees were preserved. The EXP01
recovery and official results were already filed and archived before deletion;
the duplicate recovery completion notice required no new science verdict.

## Software validation

The combined FM4 collector, adapter, canary, acceptance and gate-runner suite
passed 162 tests, with two skips for the pending D9 oracle acceptance API.
The shared carrier checked eight tuples from one source kind, with zero
invariance violations. [`validation.json`](validation.json) records the
command and scope. These controls establish software behavior; they do not
supply original native oracle or task-gate acceptance.

## Published native replay row

Row `vb-fm4-codex-projection-20261118` publisher smoke PASSed at
16:39:16Z on CPUs116–119. The separate one-pair native smoke selected
one first-turn diagnostic observation with a null task outcome and zero
task-gate claims. Its exact context and unrelated-consumer exclusion are
in [`smoke-receipt.json`](smoke-receipt.json). The original publisher PASS
and ready manifest are retained beside it. The official two-pair replay
remains a separate allocator run, with a machine-checkable rule requiring
at least two selected dispatches, zero refusals and zero task-gate claims.

The initial publisher refusal was a canonical-handoff lookup of the new
lane-local software child. The corrected packet names the existing FM4
parent; source, launcher and input pins are unchanged.
