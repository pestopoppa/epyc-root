# Source preparation

Run once outside a grant, before assembling and publishing a new row:

```bash
python3 scripts/coordination/kvfork/source_worktrees/prepare.py --preset kpf174d
python3 scripts/coordination/kvfork/source_worktrees/prepare.py --preset kpf20-v3
```

The helper uses `git worktree add --detach`, shares Git objects, validates the
repository and pinned commit, and refuses checkout copies, dirty trees and
attached branches. `--preset kpf20` serves the earlier KPF-20 launcher. Other
source paths require explicit `--repo`, `--ref`, and `--destination`; do not guess
historical refs or recreate superseded paths merely to fill disk.

KPF174d's source-file inventory ignores only the worktree's `.git` pointer and
continues to validate all source hashes and reference options. The existing tar
and source inventory hashes remain historical custody inputs; they are not used
to unpack a checkout. Do not copy or extract a source tree.

These repository changes do not update already published runtime manifests or
completed evidence. A future row must seal fresh script hashes after source
preparation. Never change a live row's files to match this candidate.
