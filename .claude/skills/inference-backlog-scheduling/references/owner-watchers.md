# Owner watchers and quarter locks (lessons, 2026-10-27)

1. **A relaunch watcher updates FILLERS pid, queue pid AND queue position atomically, then VERIFIES the FILLERS pid before exiting.**
   A stale pid makes the writer refuse the launch and reorders the queue (DF2 resume watcher, M4 timing ran out of order; CT21-after-R15 watcher died before updating, M4 GPU v1 ran first). Origin 2026-10-27.
2. **Region-lock is per quarter; the writer can still grant overlapping regions inside one quarter while its lock is held.**
   Never queue a second job on a quarter whose lock is held by a narrower-pinned job (INF-75 canary granted on 48-71 while the DF2 download held the q2 lock). Origin 2026-10-27.
3. **A single-threaded tail phase must be its own small row.**
   A single-threaded graph tail held all of q0 at 1/24 cores; the two-stage graph split fixed it. Origin 2026-10-27.
