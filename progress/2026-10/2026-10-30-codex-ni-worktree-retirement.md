# NI-owned worktree cleanup checkpoint — 2026-10-30

Retired 10 task worktrees through `worktree_gate.py` after preserving dirty/untracked evidence and retaining branch refs. Exact paths, repositories, branches, HEADs, gate results, per-tree `du`, paired `df` readings, exclusions, and caveat are in `RETIREMENT-RESULTS.json`; archived file hashes are in `ARCHIVE-MANIFEST.json`.

- Sum of removed worktree `du` sizes: 3,544,301,568 bytes (~3.30 GiB).
- Sum of paired `df` deltas: 2,743,610,368 bytes. These are shared-volume samples during concurrent activity, so neither the aggregate nor individual deltas are exclusive attribution.
- Branch refs were retained. The duplicate CF root checkpoint was preserved as a format-patch plus `refs/archive/ni/compaction-root-wrap/ebcd4127788fbb6a345c5b10682ecff5b6b80dff`; the accepted CF source is already on main. Untracked validation, review, token, and draft evidence was archived with hashes; token mode remains 0600.
- Excluded Sol's D-f3a root-wrap, repl's C26 worktree, and SSUF's AP legacy-status worktree. No production/runtime, grants, queues, STOP files, or shared scheduler state were changed.

Custody: `/mnt/raid0/llm/tmp/codex-ni-worktree-retirement-20261030/`. [no-belief: workspace cleanup and evidence custody; no model measurement]
