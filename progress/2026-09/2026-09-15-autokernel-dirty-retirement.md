# AutoKernel archived dirty-worktree retirement — 2026-09-15

Implemented a separate dry-run-by-default retirement tool for exact `KEEP-dirty` rows that have
already been captured by `autokernel_dirty_preserve.py`. Retirement binds the reviewed sweep
manifest and SHA to the durable archive record, content-addressed archive, fresh source
fingerprint, exact path/repository/HEAD and, when needed, a verified standalone HEAD bundle.

Apply remains operator-only: it requires an interactive typed SHA prefix, a COMPLETE process
probe and no holder before each mutation. Durable per-row checkpoints authorize an exact tracked
reset, removal of only Git-enumerated nonignored untracked paths covered by the archive, and the
final exact non-force `git worktree remove`. Dirty drift, ignored content, incomplete probes,
identity changes and archive mismatches retain the tree. Interrupted rows resume from the last
durable authorization.

The focused suite passed 13 cases, including archive/fingerprint tamper, incomplete and live
process probes, missing confirmation, exact-root and ignored-content refusal, exact non-force
removal with an unpushed bundle, recovery after interruption immediately following reset, and
recovery when removal completed before its terminal receipt. No existing worktree was processed
or removed.
