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

## Owner duties (2026-10-22)

Operator directive, relayed by the calendar owner. Every session that owns a filler is bound by these.

1. **Watch your own jobs.** Keep a zero-token watcher on your armed PIDs and their end/FAILED/SKIPPED flags and grant `.ended`/`.complete` files. On any change, investigate WHY, fix it, and re-queue through FILLERS.md and grant requests without waiting for the operator. A run over 1.5x its estimate is a failure to explain.
2. **RAM admission.** Host RAM is booked. FILLERS.md column 6 ("peak host RAM GiB") = private/anon peak + file-mapped weight bytes. Every subagent brief that loads a model runs `/mnt/raid0/llm/tmp/compute-flags/ram_admit.sh <peak_host_GiB> [ds41]` first and stops if it refuses. At most one DS41-class CPU server runs on the host at a time.
3. **Quiet windows.** While a quiet-host timing window is active, subagent briefs forbid clones, builds, tests, servers and heavy scripts. Any activity that happens anyway is logged in that run's HOST_ACTIVITY_DISCLOSURES file.
4. **Before idling for the night,** list every armed job with its end flag and confirm a watcher covers each one.
5. **Wrap-up** at each task boundary.

## RAM admission (2026-10-22)

Operator ask: structure the inference calendar with RAM in mind. Host RAM is a booked resource, like regions.

- Checker: `/mnt/raid0/llm/tmp/compute-flags/ram_admit.sh <need_gib> [ds41]` (live copy; the durable root copy `scripts/coordination/ram_admit.sh` is pending an operator D9 ack, since that path is loop plane). Read-only; exit 0 = admit, 1 = refuse with a reason.
- Rule: admit only if `MemAvailable - need >= 64 GiB` (earlyoom fires at 40 GiB available). With `ds41` it also refuses while any process maps or names a DS41-1017 shard (one DS41-class server host-wide).
- Unit: FILLERS.md column 6 is **peak host RAM in GiB = private/anon + file-mapped weights**. The DS41-1017 server is 739 GiB (276 private + 463 mapped).
- Callers: grant writers (evening chains v4 to v7, the GPU chain), the W6.2 `memgate.sh` (`ram_admit 739 ds41`), f8's job 67 launcher, and every subagent brief that loads a model. The calendar carries a 24 h RAM ledger beside the region table.
- Not yet wired: AutoKernel `run.py` server launches (tracked in `handoffs/active/deepseek-v41-flash-evaluation.md`, DS41-W8d).

## Owner duty: watch, why, fix, re-queue

Canonical list: *Owner duties* above. The incident behind it (2026-10-22 overnight): CT-18 HTTP 400 context overflow, chunk-KV P0 and speech D1 rc=64 from a bad region-lock argv, and D4 k5_s4 rc=125 all sat unnoticed, and the 05:19Z CPU gap went unused because the calendar owner's FREED watcher died on a zsh no-match glob. The replacement watcher keys on mtime over `FAILED`, `.ended`, `_ENDED` and `_FREED` flags under `/mnt/raid0/llm/tmp` (`compute-flags/event-watch-ws58.sh`); quote or `setopt nonomatch`-guard every glob in a watcher. Owner flow on any event: why (read the log), fix, re-queue, wrap up. Worked example: D4 root cause in `/mnt/raid0/llm/tmp/d4-why-20261022/REPORT.md` (the estimator was wrong, not contention).

## Reference implementation

CT-18 Skill-Inject: `/mnt/raid0/llm/tmp/ct18-run-20261021/filler_worker.sh` (`ct18-worker`, CPU) and `filler_arch.sh` (`ct18-arch`, mi210_0 + host threads 184-191). They are generated from one template; `.ended` rc 124 = hard end, 4 = refused, 2 = unusable grant, 143 = launcher signalled.

## Prior check (proposed 2026-10-21, pending workspace-58 / stage-3 agreement)

Origin: `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` section 4 (change B) -- bookings were armed without anyone checking prior results, so the same instrument was booked twice on one build. This is a **proposal**: nothing validates it yet, and no queue row or GRANT line is required to carry it until workspace-58 (calendar owner) and stage-3 agree.

- Before a row enters the QUEUE table (and before a GRANT is written for it), run `scripts/coordination/prior_check.py` (stdlib, zero compute, read-only, nice 19, self-limits to 20 s). It searches the belief ledger, AutoKernel campaign stores (`experiments.db` opened `mode=ro`, `serving-floor.*`, `serving-beliefs/`), research `artifacts/`, and the run records under `/mnt/raid0/llm/tmp/*/`.
- Pass the model (file or basename), the recipe/argv (file, hash or `--argv "..."`), the decision/metric keywords, and the build sha or execution digest the booking will use: e.g. `prior_check.py --model <gguf> --argv "<launch argv>" --metric floor --decision KVU-12.1 --build <sha>`. Add `--tag` for campaign aliases the model name does not contain (`ds41`, `q38fn`).
- Put its last line in the row notes / GRANT context, verbatim: `prior=<path> [(<flag>)]` or `prior=none (checked <UTC ts>)`. `none` is a dated statement that the lookup ran; a path is a **lead the booker opens and cites or rejects in one line** -- the tool never declares a booking redundant. Flags: `STALE-transferable` (other build, quality axis -- transfers once parity is proven, MEASUREMENT_POLICY), `STALE` (other build, axis unclear), `build-unknown` (the record states no build), `RETRACTED`. A `STALE-speed` hit (other build, speed axis: era-fenced) is listed in the output but never emitted as `prior=` -- the speed axis must be re-measured.
- `--json` gives the ranked candidate list for machine use (`epyc.prior_check.v1`). Exit 0 always except 2 for malformed inputs. Full contract: the module docstring.

### Grant validator (proposed 2026-10-21, pending workspace-58 agreement)

`scripts/coordination/validate_fillers.py [--file F] [--row ID] [--for-grant]` checks the 18-column QUEUE table in `FILLERS.md` (column 6 `peak host RAM GiB` (formerly `max private RAM`) must be a number in GiB such as `48` or `48 GiB` -- definition (workspace-58, 2026-10-22): private/anon peak PLUS file-mapped weight bytes, counting mapped weights even with mmap; `ram_admit.sh` compares it with MemAvailable (margin 64 GiB); `class`, `status`, `DS41-class`, `ready`, `substrate` enums; `prior` a path or `none found (<who>, <date>)`; `decision` one line; `min_effect` with a unit or `n/a (build)`; `block-timing-quiet` additionally needs a champion/candidate baseline in `decision` and a floor file cited in `notes` or `prior`). The grant writer runs it with `--row <filler-id> --for-grant` immediately before writing `grants/<filler-id>.grant`: exit 0 = grant, 2 = refused (violations printed as `REFUSE`), 3 = malformed table/row. Without `--for-grant` every violation is only a `WARN` (other owners' rows may still carry `-`). Rule text: the module docstring.
