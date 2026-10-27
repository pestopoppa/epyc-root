# Owner watchers and quarter locks (lessons, 2026-10-27)

1. **A relaunch watcher updates FILLERS pid, queue pid AND queue position atomically, then VERIFIES the FILLERS pid before exiting.**
   A stale pid makes the writer refuse the launch and reorders the queue (DF2 resume watcher, M4 timing ran out of order; CT21-after-R15 watcher died before updating, M4 GPU v1 ran first). Origin 2026-10-27.
2. **Region-lock is per quarter; the writer can still grant overlapping regions inside one quarter while its lock is held.**
   Never queue a second job on a quarter whose lock is held by a narrower-pinned job (INF-75 canary granted on 48-71 while the DF2 download held the q2 lock). Origin 2026-10-27.
3. **A single-threaded tail phase must be its own small row.**
   A single-threaded graph tail held all of q0 at 1/24 cores; the two-stage graph split fixed it. Origin 2026-10-27.
4. **Reclaim raw scratch at filing (operator-approved).**
   Every row declares `scratch_root=`, `raw_globs=` and `keep_globs=` in its notes; refuse rows without them. Once a run's result commit is on origin/main, the filing step's last action trashes that row's `raw_globs` with `guarded_rm.sh` and reports the GB reclaimed. Never touch models, kernels, KEEP-cited paths, live cwds, or dirs referenced by ARMED or BACKLOG rows.
   Origin 2026-10-27: the disk hit the 150 GB floor twice. Wrap-ups reclaim only declared handoff `**Scratch**` roots (133 handoffs lack one), nobody owned post-filing cleanup, every retry made a new 2-3 GB dir, and whole-dir KEEP markers froze large raw files. `trash-sweep.sh` removes only entries older than 1 day, so a same-day clear needs the operator.

5. **Remove merge worktrees right after push; KEEP must be per-file; trash does not free space.**
   Origin 2026-10-27 evening: free space fell below the 150 GiB run floor. Causes: about 25 leftover ws58 merge worktrees (now removed); Codex scratch marked KEEP at directory level; trash not freeing space until the 1-day sweep. The operator freed 29 GB of retired models and 8 batch worktrees (about 190 GiB free now). Remove your merge worktree with `git worktree remove` immediately after the push is verified, mark KEEP per file never per directory, and never count trashed bytes as free. NI owes a scratch-reclaim tooling packet.
