# Acceptance-worktree hygiene — 2026-09-15

Added a prospective, owner-bound lifecycle helper for manually created acceptance worktrees. It
creates only new `accept/*` worktrees under the configured acceptance root and writes a durable
JSON receipt plus append-only JSONL event history outside the worktree before creation.

Closure is explicit: `commit-push` requires a clean tree, at least one commit beyond the recorded
base, and an exact network remote-tracking ref at HEAD; `discard` requires a clean tree still at
the recorded base. Both refuse live process holders and identity mismatches. An accepted closure
records the exact removal command durably, then uses `git worktree remove <exact-path>` without
`--force`. Dirty, ignored, unpushed, locally committed, or otherwise unverifiable trees remain in
place with a retained receipt.

Validation: `tests/test_acceptance_worktree.py` passed 8 tests; Ruff, Python compilation, CLI help,
and `git diff --check` passed. No pre-existing worktree or production tree was changed or removed.
