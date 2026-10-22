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

## Queue semantics and launcher rules (2026-10-22)

The operator's ruling: "Being queued implies BEING ready."

- **QUEUED** means status ARMED and `ready=y`, with a live launcher pid that is polling its grant id. Every other row is **BACKLOG**, with a named `blocker=` and an owner. A row that is "ready but nobody armed it" is BACKLOG (`blocker=missing launcher`), not QUEUED. The calendar owner grants only QUEUED rows. `scripts/coordination/validate_fillers.py` enforces this (see *Grant validator* below).
- **One live launcher per grant id.** A launcher keeps polling its id after its window ends, so two live launchers on one id race for the next grant. To re-arm, kill the old poller by its captured PID, verify it is dead, then start the new one.
- **A filler's inner claim must match its FILLERS resources.** If the job claims more than the row books, it times out behind other holders. `akx-all-27b-run` asked for `gpu-quiet` excl + q0-q3 while booked for the GPU plus 184-191, hit rc=75, and left the MI210 idle for 40 min.
- **Never grant q3 while a GPU runner holds it.** A GPU job's host threads (184-191) are SMT siblings in q3 and claim that quarter. A CPU grant on q3 during a GPU window only queues behind the GPU job. On 2026-10-22 the calendar owner granted `v11-086-fa-vkq-build` q3 while f8's KPF-18 S1 GPU sweep held it until ~13:02Z, and the build waited. Check the GPU calendar before granting q3.
- **region-lock folds `--cpu-list 184-191` into a q3 claim.** The MI210 sat idle 12:24-12:41Z behind a q3 build that the calendar owner had granted (the second q3 violation on 2026-10-22). The first fix, `region-lock --no-fold-siblings`, does not work: `--cpu-list 184-191 maps to no regions`, rc=1 (12:44Z). The working pattern is `filler_run6.sh`: the GPU job claims **GPU-quiet only** (no CPU region) and tasksets 184-191 itself.
- **No timing-class CPU work on q3 during GPU windows.** Correctness and build work may use q3 only when no GPU runner holds it. An exception is a job that deliberately keeps its folded timing claim (`kpf60` does), which needs q3 empty for its short timing step.
- **No ungranted region-lock claims.** A subagent started `cs8l-asr2` (a CS-8.L second-ASR job) on q2 at 12:50Z with no grant. It was found from the region holder list, its owner was identified, and the owner killed it by its own PIDs (~12:55Z). Every claim needs a `grants/<id>.grant`; re-queue as a filler row if the work is wanted.
- **Use an explicit interpreter under region-lock**, for example `/usr/bin/python3` or the venv path you mean. A bare `python3` inside `region-lock run` resolves to the orchestrator `.venv` 3.11, and f8-day-q0 failed with rc=2 that way.
- **Never wrap a check in `strings <bin> | grep -q` under `set -o pipefail`.** `grep -q` exits on its first match and `strings` dies of SIGPIPE, so the pipeline fails even though the match was found (f8's "wrong build" false alarm). Capture first (`strings <bin> > f; grep -q PAT f`), or use `grep -c` with no early exit.

## Owner duties (2026-10-22)

Operator directive, relayed by the calendar owner. Every session that owns a filler is bound by these.

1. **Watch your own jobs.** Keep a zero-token watcher on your armed PIDs and their end/FAILED/SKIPPED flags and grant `.ended`/`.complete` files. On any change, investigate WHY, fix it, and re-queue through FILLERS.md and grant requests without waiting for the operator. A run over 1.5x its estimate is a failure to explain.
2. **RAM admission.** Host RAM is booked. FILLERS.md column 6 ("peak host RAM GiB") = private/anon peak + file-mapped weight bytes. Every subagent brief that loads a model runs `/mnt/raid0/llm/tmp/compute-flags/ram_admit.sh <peak_host_GiB> [ds41]` first and stops if it refuses. At most one DS41-class CPU server runs on the host at a time.
3. **Quiet windows.** While a quiet-host timing window is active, subagent briefs forbid clones, builds, tests, servers and heavy scripts. Any activity that happens anyway is logged in that run's HOST_ACTIVITY_DISCLOSURES file.
4. **Before idling for the night,** list every armed job with its end flag and confirm a watcher covers each one.
5. **Wrap-up** at each task boundary.
6. **Re-arming after killing a poller.** Use `/mnt/raid0/llm/tmp/fillers-3c4ca599/filler_run5.sh`; older launchers (`filler_run.sh` to `filler_run4.sh`) need the manual capture: their orphaned `sleep 45` child keeps the launcher lock fd, so an immediate re-arm exits with "another launcher ... already running"; capture the child sleep (`pgrep -P <pid>`) before killing, kill it too, verify both dead, and only then re-arm. `filler_run5.sh` is `filler_run2.sh` with the same CLI plus `--repeat`: it closes the lock fds (7 launcher lock, 8 runner lock) on its poll and watch `sleep`s and fd 7 on the job group (CTC-Q-H), exits after ONE window that started the job unless `--repeat` is given, and never deletes or ends a grant while another process holds the same id's runner lock (CTC-Q-G). A re-arm only swaps the script name (add `--repeat` to keep the old keep-polling behaviour). Dry-run evidence: `/mnt/raid0/llm/tmp/fillers-3c4ca599/dryrun5_out.txt` (the harness, `dryrun5_test.sh`, sits beside it). Seen twice on 2026-10-22.
7. **Never edit a job script a running poller may execute.** Version it instead (the `kpf64_job2.sh` pattern).
8. **Two pollers can split one experiment** only over disjoint result dirs. Analysis and the done-marker go to whichever job sees all arms complete.
9. **GPU jobs use `filler_run6.sh --no-fold-siblings`.** A GPU-class run claims `gpu-quiet` only and the job tasksets itself onto its host threads. Never pass region-lock's own `--no-fold-siblings` with an SMT-only `--cpu-list` (e.g. `184-191`): region-lock refuses with "maps to no regions" (akx died rc=1 in 4 s, 2026-10-22). Without it the same list folds into a whole-q3 claim and the MI210 idles behind a q3 build. A GPU-only claim is `--gpu-quiet` with no `--cpu-list`.
10. **Never edit a launcher a live poller is executing.** Version it (`filler_run5.sh` to `filler_run6.sh`), as item 7 does for job scripts, then re-arm pollers onto the new name.
11. **A subagent brief must say that ANY model execution needs a filler row plus a grant, ASR and TTS included.** "Allowed if no inference" is ambiguous for ASR: a subagent ran an ungranted whisper large-v3 second-ASR job on q2 (2026-10-22; killed and verified dead by main).
12. **The Bash containment hook refuses variable-expanded write targets.** Use literal paths in launch commands.
13. **New arms use `filler_run7.sh`** (`/mnt/raid0/llm/tmp/fillers-3c4ca599/`; run6 plus one change). `--class gpu --gpu-quiet exclusive` with neither `--claim-cpus` nor `--no-fold-siblings` exits 64 instead of silently claiming CPUs 0-95. Whole-host timing jobs say `--claim-cpus 0-95` explicitly; GPU-only jobs use `--no-fold-siblings`. Existing pollers migrate at their next re-arm (never edit a live launcher). Dry-run proof: `dryrun7_test.sh`. Containers launched by a GPU job must also carry `--cpuset-cpus "$FILLER_CPUS"`, since `taskset` on the docker client does not confine the container.

### Subagent brief rules (2026-10-22 additions)

14. **Never delete or modify the coordinator's scratchpad (`/tmp/claude-1000/...`) or any path you did not create.** A HIL-6 subagent's scratch cleanup deleted main's watcher script; main's watcher now lives at `/mnt/raid0/llm/tmp/fillers-3c4ca599/own_jobs_watch.sh`. Put anything long-lived under `/mnt/raid0/llm/tmp`.
15. **Qwen3.6+ endpoints: every harness request on the chat path sends `chat_template_kwargs {enable_thinking:false}`** unless thinking is pre-registered. It bit cme7 and hsprof1 the same way (empty content, all tokens spent on reasoning). Harnesses fail loudly on an empty reply. **Server side (source-level fix, 2026-10-22):** jobs launching Qwen3.x servers MUST `. jobs/qwen_thinking_lib.sh`, pass `$(qwen_reasoning_args "$MODEL")` (-> `--reasoning off`) in the server argv, and run `qwen_first_reply_preflight $PORT` after the own-PID port proof and before the workload (rc 9 = thinking still on / empty content). A per-request `enable_thinking:true` still overrides the server default (`server-common.cpp:1074-1087`), so pre-registered thinking-ON arms are unaffected.
16. **Never run a CPU-wide preflight or bench inside a GPU-only grant.** `run_benchmark` now auto-skips the canonical tripwire under `--existing-server-port`. Containers need `--cpuset-cpus` (item 13).
17. **Pinned-worktree jobs refuse a dirty tree,** and a shared lib must not reassign a job's pinned tree variable (the pyarrow/shared-lib clobber of RESEARCH in hsprof1 run 1). Yarn jobs are tracked in YARN-DIRTY-TREE-REFUSE.
18. **Never push when `index_state.py --check` reports a problem.** Fix the row first, then push.
19. **Never chain a check that only PRINTS with the action it should gate.** Gate in code, failing closed: `if check; then act; fi`. For a shared-clone fast-forward, run a read-only `/proc` cwd/argv walk (never `pgrep`) and refuse if any non-MCP, non-dashboard process uses the clone. Origin (2026-10-22): main's second orchestrator ff (`c69ba5a1` to `cdbca26b`) printed a live-process check but did not gate on it, and ran under workspace-7b's `ak-q38fn-fa` campaign (started 16:14:59Z). The changes were inert for that loop, but the gate was missing. Agreement with 7b: no shared-clone git ops until 18:00Z; later ffs are gated in code.
20. **Before asking the operator to lift a deferment or approve a run, show its compute cost estimate first** (whole-host hours, windows). The HIL-6 pilot lift was asked before its cost was known; the estimate then came back at about 232-300 whole-host hours, and the operator leaned to a redesign.
21. **Check a diagnosis of a slow harness against the server logs before naming a cause.** KPF-64 was attributed to thinking-on; the server logs show the cause was decode contention across 4 slots (0.80 tok/s per slot), with outputs feeding later prompts (`2026-10-22-kpf64-decode-fix.md`).

## RAM admission (2026-10-22)

Operator ask: structure the inference calendar with RAM in mind. Host RAM is a booked resource, like regions.

- Checker: `/mnt/raid0/llm/tmp/compute-flags/ram_admit.sh <need_gib> [ds41]` (live copy; the durable root copy `scripts/coordination/ram_admit.sh` is pending an operator D9 ack, since that path is loop plane). Read-only; exit 0 = admit, 1 = refuse with a reason.
- Rule: admit only if `MemAvailable - need >= 64 GiB` (earlyoom fires at 40 GiB available). With `ds41` it also refuses while any process maps or names a DS41-1017 shard (one DS41-class server host-wide).
- Unit: FILLERS.md column 6 is **peak host RAM in GiB = private/anon + file-mapped weights**. The DS41-1017 server is 739 GiB (276 private + 463 mapped).
- Callers: grant writers (evening chains v4 to v9, the day and night GPU chains, the day CPU grants), the W6.2 `memgate.sh` (`ram_admit 739 ds41`; W6.2 was cancelled 2026-10-22), f8's job 67 launcher (cancelled 2026-10-22), and every subagent brief that loads a model. The calendar carries a 24 h RAM ledger beside the region table.
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

`scripts/coordination/validate_fillers.py [--file F] [--row ID] [--for-grant]` checks the 18-column QUEUE table in `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md` (column 6 `peak host RAM GiB` (formerly `max private RAM`) must be a number in GiB such as `48` or `48 GiB` -- definition (workspace-58, 2026-10-22): private/anon peak PLUS file-mapped weight bytes, counting mapped weights even with mmap; `ram_admit.sh` compares it with MemAvailable (margin 64 GiB); `class`, `status`, `DS41-class`, `ready`, `substrate` enums; `prior` a path or `none found (<who>, <date>)`; `decision` one line; `min_effect` with a unit or `n/a (build)`; `block-timing-quiet` additionally needs a champion/candidate baseline in `decision` and a floor file cited in `notes` or `prior`). The grant writer runs it with `--row <filler-id> --for-grant` immediately before writing `grants/<filler-id>.grant`: exit 0 = grant, 2 = refused (violations printed as `REFUSE`), 3 = malformed table/row. Without `--for-grant` every violation is only a `WARN` (other owners' rows may still carry `-`). Queue semantics (2026-10-22 ruling "being queued implies being ready"): ready=y needs status ARMED plus a live launcher (`pid=<N>` in the launcher cell or notes; `/proc/<N>` must exist and name the row id, a grant id or the launcher path); every ready=n row is status BACKLOG with `blocker=<missing launcher|harness fix|build|operator decision>` in notes and an owner; REGISTERED with ready=n is an error. Since root `a367d1df0` (2026-10-22), finished rows (COMPLETE/CANCELLED) skip all field checks, and `min_effect` accepts `n/a (<reason>)`; a bare `n/a` is still refused. Rule text: the module docstring.

## Operator ruling: WINDOW_CONFIRMED (2026-10-22)

A compute-filler job may export `WINDOW_CONFIRMED=1` **only inside a calendar-granted window** (a live `grants/<id>.grant` naming its regions). Outside a grant the flag must not be set. Operator-approved 2026-10-22 (OP-KPF64-ARM).
