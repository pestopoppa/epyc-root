# AutoKernel archived dirty-worktree retirement — 2026-09-15

Implemented a separate dry-run-by-default retirement tool for exact `KEEP-dirty` rows that have
already been captured by `autokernel_dirty_preserve.py`. Retirement binds the reviewed sweep
manifest and SHA to the durable archive record, content-addressed archive, fresh source
fingerprint, exact path/repository/HEAD and, when needed, a verified standalone HEAD bundle.

Apply remains operator-only: it requires an interactive typed SHA prefix, a COMPLETE process
probe and no holder before each mutation. Durable per-row checkpoints authorize an exact tracked
reset, removal of only Git-enumerated nonignored untracked paths covered by the archive, and the
explicit discard of generated ignored artifacts only after exact dual Git enumeration and a
durable path/type/bytes/hash inventory, followed by the exact non-force `git worktree remove`.
Ignored symlinks are bound by `lstat` mode and exact `readlink` bytes/hash, then unlinked as inodes
without resolving or following their file or directory targets. Dirty drift, ignored evidence,
nested repositories, special files, incomplete probes, identity changes and archive mismatches
retain the tree. Interrupted rows resume from the last durable authorization.

The 19-case focused suite (46 tests with preserve and sweep regressions) covers archive/fingerprint
tamper, incomplete and live process probes, missing confirmation, exact-root refusal, cache/build
ignored-artifact discard, ignored evidence/nested Git/special-file refusals, escaping
file/directory symlink target-survival, exact non-force removal with an unpushed bundle, and
resumption across durable mutation stages. No existing worktree was processed or removed.

The evidence matcher shares the sweep's canonical cache-skip semantics. In particular,
`scripts/vidya/adapters/__pycache__/sealed_manifest.cpython-313.pyc` and evidence-shaped names
under `.ruff_cache` are generated artifacts, while the same evidence names outside a cache still
refuse retirement.
