# Compute Fillers

Early-ending compute blocks leave gaps. Registered **fillers** use them, without ever competing with the calendar.

- Registry: `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md` (one row per filler: id, owner, launcher + PID, resources, minimum useful window, max private RAM, STOP file, status). This is a separate file from the calendar; never edit the calendar from it.
- Grants dir: `/mnt/raid0/llm/tmp/compute-flags/grants/`.

## Protocol

1. A block that ends before its booked end writes `/mnt/raid0/llm/tmp/compute-flags/<block>_FREED`. The calendar owner (workspace-58) consumes it.
2. The calendar owner grants the gap to a registered filler by writing `grants/<filler-id>.grant`, one line: `regions=<...> start=<UTC> end=<UTC hard>`.
3. The filler launcher polls its own grant file (every 30-60 s, shell `sleep` only, no LLM) and runs only between `start` and `end`, under its own **build-role** region-lock claim. **No grant, no run.** One grant is one run; then it waits for the next.
4. At `end`: stop new items, SIGTERM then SIGKILL the run (kill by captured PID / the process group the launcher itself created, never by name pattern), verify dead, release the claim, delete the grant, write `grants/<filler-id>.ended` (`rc=<n> time=<UTC> reason=<...>`).
5. All work done: write `grants/<filler-id>.complete`, mark the registry row COMPLETE, exit for good.

## Rules for a filler

- Resumable: a slice of any size must be useful (resume-skip on already-written rows).
- Honours a STOP file between items (a started item is finished).
- Build-role claims only; never runs inside a timing block unless the grant says so.
- Respects the host rule of at most ONE DS41-class CPU server (>= 200 GiB) at a time.
- Mutual exclusion: refuses to start while the scheduled runner for the same results file is live (its server port listening, or the per-arm runner lock held) and reports it as `.ended rc=4`.
- Test before arming: `bash -n`, then a dry-run with a fake grant in a temp grants dir (`FILLER_GRANTS_DIR`) and a stub runner (`FILLER_STUB_CMD`) proving poll, start, end, cleanup, `.ended`.

## Reference implementation

CT-18 Skill-Inject: `/mnt/raid0/llm/tmp/ct18-run-20261021/filler_worker.sh` (`ct18-worker`, CPU) and `filler_arch.sh` (`ct18-arch`, mi210_0 + host threads 184-191). They are generated from one template; `.ended` rc 124 = hard end, 4 = refused, 2 = unusable grant, 143 = launcher signalled.
