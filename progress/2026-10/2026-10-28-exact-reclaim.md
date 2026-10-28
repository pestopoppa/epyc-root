# Exact approved scratch reclaim — 2026-10-28

The operator approved the exact 19-path manifest SHA-256
`f4c7f90d69661011026c52adf5c3bb0c61ecbf42f56d967770487b6e34783291`,
including its scoped KEEP and early-retention exceptions. Fresh checks found
16 paths present and three already absent. The three missing paths were recorded
as `absent-no-action`; no credit or cause was assigned to their absence.
Workspace-58 retired the affected graph and NI08 launchers, and MAIN reviewed
the subset method and mapping before the operator and owner approved the purge.

The 16 present paths were staged into an isolated same-filesystem trash batch.
All 16 payload inode and metadata-tree identities, the exact batch children,
the three absent paths and two preserved research branch refs passed the
post-stage review. The subsequently scoped purge completed under q3 region-lock
on CPUs 72,73, OMP1, alongside the owner-authorized correctness workload.
The audit contains 16 fsynced purge intents and 16 completions; the batch
directory is empty and the original manifest, mapping, receipt and move journal
remain. No other paths were swept. [belief: cc]

Available filesystem bytes changed from `204514914304` immediately before
purge to `218723995648` immediately afterward: an increase of `14209081344`
bytes (14.21 GB, 13.23 GiB). This is an observed free-space delta on a shared
filesystem, not a controlled measurement attributing every byte to the batch.
The prior same-filesystem staging did not itself free space. [belief: cc]

Evidence in `/mnt/raid0/llm/tmp/codex-ni-20261027-priority-scratch-reclaim/`:
`data-only-actions.log` SHA-256
`7d976c565a70110cc403dc3ccabd11d2bc59fb51f3dac8dd77867b92e28aa664`;
`sweep-actions.log` SHA-256
`4a46a725a52725b5e62c572ac74869d6b7dee0f418ea83afa5f75e7724e0b4fc`.
Retained `/mnt/raid0/llm/.trash/kpf18-approved-r15-20261027-1900` sidecars:
mapping SHA-256 `8653225c20daf9a582078c4da320298b45ad590e73ed2a6d50508413ddc0c3f5`,
receipt SHA-256 `681d33c6e7174d4ad9d0112a154c7a375ed214a05c6b68b3e42470e9a97dd61b`,
and move journal SHA-256 `6662249f073c83c71b7c9e77a04b0cf2d8d0cdf2a54a2981cbef5b578fc063e0`.
The same-batch purge events are in `/workspace/logs/safety_audit.log` and copied
into the sweep log. These files are custody evidence and must be retained.

The separate scratch-retention tooling branch is proposed, not installed. The
human-only same-day policy draft was not ratified. Three identical native
`read-038.bin` files remain untouched because their individual receipts and
execution requests refer to their respective paths.
