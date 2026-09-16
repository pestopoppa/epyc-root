# AutoKernel archived dirty-worktree retirement — 2026-09-16

The operator approved the exact reviewed sweep manifest SHA prefix `a49053c273ee`.
Its full SHA-256 was `a49053c273ee55d26e7d43e73fbb52735aa75d0cf3ad1c61f752a122c8e309e5`.
All 224 `KEEP-dirty` worktrees had previously been captured in 224 verified,
content-addressed archive records under
`/mnt/raid0/llm/archives/autokernel/dirty-worktrees/records`.

The retirement tool revalidated the complete set, then processed only those exact
records with interactive hash confirmation. One row was safely retained when an
unrelated `bfs` process briefly held that worktree open. After that process exited,
the same row resumed from its durable receipt and completed. Final verification
found **224 `removed` receipts for 224 archive records**, no remaining retirement
exception, and the retried row's worktree registration absent.

Free space on `/mnt/raid0/llm` rose from 382,977,454,080 bytes (about 356.7 GiB)
before retirement to 742,153,621,504 bytes (about 691.1 GiB) afterward, a net
gain of 359,176,167,424 bytes (about 334.5 GiB). The preserved dirty-source
archives and per-row receipts remain outside the removed trees. The 187 nested
pool lanes on the frozen production clone were not targeted. No production kernel,
campaign store, or model artifact was modified. AutoKernel remained stopped
throughout the cleanup.

Prospective controls are separate: the serial AutoKernel supervisor now bounds
each child stdout/stderr retention at 1 MiB while recording total byte counts
and hashes, and fails closed below its 400/500 GiB disk trigger/recovery reserve
when eligible build-cache retention cannot restore headroom. The W4 coverage-run
REPL incident was an output-file growth defect, not a demonstrated RAM leak;
the valid rerun used `--single-turn`, closed stdin, a 900-second timeout and a
16 MiB output cap. These controls prevent the observed runaway and protect the
serial loop, but do not claim that every ad-hoc harness is covered.
