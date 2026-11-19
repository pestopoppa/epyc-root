# KPF-17.4d r4 fresh build-only successor

Fresh row `kvu-kpf174-custody-r4-20261104` supersedes exactly `kvu-kpf174-custody-r3-20261104` in lineage `kvu-kpf174-custody` after r3 rc75 disk-floor. Scratch spec: `/mnt/raid0/llm/tmp/kvu/kpf174-custody-r4-20261104/spec.json`. The original 150 GiB disk floor and 48 GiB reservation remain enforced. No predecessor result is inherited.

Source is the dedicated detached git worktree `/mnt/raid0/llm/worktrees/kpf174-custody-r4-source-20261104`, materialized with `git worktree add --detach` at `6ec877068936588b6d63dbba5842bbd540b92031`, parent `84d0a31603d495377dee24e1159bbbf02f1e2f21`. It is independent of reclaimable r3 scratch. No production checkout was copied or changed. Exact 3,304-file source content and all pinned input hashes were verified; source and input stat inventories were regenerated. Runtime source and compile-command proof paths point to this worktree.

All seven shared-library receipt hashes, custody of every ggml DSO, pinned linkage helper, compiled knobs, completion reopening and host compiler digests remain required. CPU allocation builds the full HIP candidate. First-object smoke only proves progress. No compute or publisher smoke ran during preparation; no grants or publication were made. Owner must perform canonical publisher smoke before publication.

`PREPARATION.json` pins spec, launcher, runtime and scratch `input/PREPARED.json`. The large stat inventory stays in scratch to avoid scanner timestamp false positives. The inherited metadata guard cannot prevent same-UID mutation followed by metadata restoration. Witness must pin future validated receipt and custody hashes before GPU publication.

The owner subsequently published this row after a four-CPU first-object smoke PASS; no full-build outcome is established by that smoke.
