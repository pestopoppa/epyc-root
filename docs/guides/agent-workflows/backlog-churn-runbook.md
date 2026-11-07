# Backlog-churn pipeline: spin-up, verification, stop and audit runbook

Design (why the pieces exist and how rows flow): [`backlog-churn-flow.md`](backlog-churn-flow.md).
This page covers how to bring the pipeline up from git, check that it works by measurement, stop it, and audit it.
Every path and flag here was checked against the code on 2026-11-02 (ws58). If the code and this page disagree, the code is
right and this page has a bug.

`F` = `/mnt/raid0/llm/tmp/compute-flags` (runtime dir: installed copies, pidfiles, logs, state). `R` = an epyc-root checkout
on current `origin/main`. Git is the only source. `F` holds copies, and `churn_up.sh --status` proves each copy's sha equals git.

## 1. Component inventory

| Component | Git path (`R/…`) | Installed path (`F/…`) | How it runs | Pidfile / log (`F/…`) | Kind |
|---|---|---|---|---|---|
| Keeper watchdog | `scripts/coordination/churn/ws58-keeper-watchdog.sh` | `ws58-keeper-watchdog.sh` | bash loop, 120 s. It starts the keeper named in `ws58-calendar-keeper.current` when the pid in `ws58-calendar-keeper.pid` is gone. It never kills anything. | `ws58-keeper-watchdog.pid` (written by churn_up) / `ws58-keeper-watchdog.log` | deterministic |
| Keeper v12 (allocator) | `scripts/coordination/rowflow/ws58-calendar-keeper-v12.sh` | `ws58-calendar-keeper-v12.sh`, selected by `ws58-calendar-keeper.current` | bash loop. Each tick runs `rowflow.py allocate` (one snapshot, then dry runs and grants). It never reaps: since 2026-11-03 step 6 runs only as `--reap-now`, from the disk janitor (a ~100 s reap inside the tick blocked granting). It wakes within 5 s when `grants/` or `ready/` changes, with 120 s as the fallback. | `ws58-calendar-keeper.pid` (written by the keeper) / `ws58-calendar-keeper.log` | deterministic |
| Dispatcher | `scripts/coordination/handoff_sessions.py` | `bin/handoff_sessions.py` | `python3 -I F/bin/handoff_sessions.py dispatch --loop --interval 60` (cwd `F/bin`). It starts and resumes per-handoff Codex sessions in tmux windows `h-<slug>`, up to `max_live` in `handoff-sessions.json`. | `handoff-sessions.dispatcher.pid` / `handoff-sessions.log`, state `handoff-sessions.json` | deterministic, but it **starts AI sessions** |
| Backlog generator | `scripts/coordination/backlog_gen.py` (+ wrapper `churn/ws58-backlog-gen-v1.sh`) | `bin/backlog_gen.py`, `ws58-backlog-gen-v1.sh` | The wrapper execs `python3 -I F/bin/backlog_gen.py --loop --interval 600` and writes the per-worker `BACKLOG-<worker>` markdown files every 10 min. | `ws58-backlog-gen.pid` / `backlog-gen.log` | deterministic |
| Flow scoreboard | `churn/ws58-flow-scoreboard-v1.sh` → `flow_scoreboard.py` | `ws58-flow-scoreboard-v1.sh`, `bin/flow_scoreboard.py` | bash loop, 10 min → the `FLOW-SCOREBOARD` markdown file in `F` | `ws58-flow-scoreboard.pid` | deterministic |
| Disk trend | `churn/ws58-disk-trend.sh` | `ws58-disk-trend.sh` | bash loop, 10 min → `disk-trend.tsv` | `ws58-disk-trend.pid` | deterministic |
| Disk janitor | `scripts/coordination/churn/disk_janitor.sh` | `disk_janitor.sh` | bash loop. Every 30 min it runs the keeper's reap-only pass (`ws58-calendar-keeper-v12.sh --reap-now`: filed manifests, `.complete` or `.ended` + `filing-done/<id>.FILED`, and unmanifested dirs idle ≥ 1 day; a dir holding a `.git` only when every checkout in it is clean, unlocked, registered or a full clone, and `git cherry origin/main` is empty). It skips while `ws58-keeper-state/reap-last` (touched by every `--reap-now` pass, e.g. a manual one) is younger than 30 min. The reaper never deletes a file the job did not write: anything with an mtime before the group's first recorded job start (`started=` in `grants/<id>.ended`; `published_at` when none) is input and stays, whatever `keep` says. Hourly it runs `trash-sweep.sh --older-than 1` on `/mnt/raid0/llm/.trash` and on `/mnt/raid0/llm/.trash-reap` if that exists. Every 30 min it also runs `row_disk_budget.py --alert` (per-row disk budget: bytes the row wrote since its grant vs `budget_gib`, default 1 GiB; alert only). Once a day it runs the LIFECYCLE pass (operator 2026-11-07, automatic reclamation): `worktree_reaper.py --apply` (agent worktrees under `worktrees/` and `.worktrees/`: clean+landed idle ≥ 3 d removed, dirty/unlanded idle ≥ 7 d salvaged to `archive/worktree-salvage/<name>-<UTC>/` + a `salvage/<name>-<UTC>` branch, then trashed, then deregistered with `git worktree remove` on the missing path; `mains/`, `pool/`, locked and KEEP-marked trees skipped; never `--force`/prune), `kernel_store_gc.py --apply` (`kernels/builds/*` not a production/archive/candidate target, not named by a manifest, handoff, ready row or champion file, not busy, idle ≥ 7 d → trash), `owner_check.py --fix-modes` (root-owned or unwritable dirs under tmp/, .trash*, worktrees/ flagged with the exact `sudo chown` line; modes we own repaired), `scratch_lease.py backfill --apply --ttl-days 14` (every new KEEP marker gets a lease so none holds bytes forever) and `codex_retention_reaper.py report --json` (report only: ~/.codex is never touched, operator 2026-10-04). Each tool logs to its own `$F/<tool>.log`; `JANITOR_LIFECYCLE=0` disables the pass; `--dry-run` previews every step. Reclaim AT FILING is not the janitor's: `file_result.py` calls `reclaim_row.py <id> --apply` right after the FILED receipt (declared `raw` globs / `raw_globs=` notes, `raw_days` retention, row-owned worktrees under `scratch_root/worktrees/`), and refuses to file a row with no `scratch_root`. It deletes nothing itself. Own controls: `churn_up.sh --janitor=start\|stop\|status\|dry-run`. `churn_up.sh --stop` (the inference stop) leaves it running. | `disk-janitor.pid` / `disk-janitor.log` (`FREE <n>GiB` each pass, `REAP …`, `SWEEP <trash> rc= entries=`) | deterministic |
| Filing watch | `scripts/coordination/filing_watch.sh` | runs from `R` (not installed) | bash loop, 60 s | `ws58-filing-watch.pid` | deterministic |
| Row engine | `scripts/coordination/rowflow/{rowflow.py,publish_row.py,filler_run15.sh,filler_lib.sh,grant_ok_launcher.py}` | `bin/rowflow/…` | Invoked by the keeper (`allocate`), by owners (`publish`), and as each row's launcher. It has no daemon of its own. | `dryrun/<id>/{ARMED,RUNNING}.json`, `grants/<id>.{grant,ended,complete}`, `ready/` | deterministic |
| Wrap-up / index regen | `churn/wrapup.py`, `scripts/coordination/index_regen.py` (`--dry-run`) | `bin/churn/wrapup.py`, `bin/index_regen.py` | invoked per session turn end | `index-regen.log` | deterministic |
| Push serializer | `scripts/coordination/serialized_push.py` (`--status`, `--dry-run`) | `bin/serialized_push.py` | invoked per push | lock dir `--print-lock-dir` | deterministic |
| Region lock | epyc-orchestrator `src/runtime/region_lock_cli.py`, wrapper `/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock` | (orchestrator clone) | invoked by launchers. Under `FILLER_DRYRUN=1` or `FILLER_SMOKE=1` it takes **no lock**. | flock+pid records | deterministic |
| ws58 session, codex-gen session | n/a | tmux `agent:claude`, `agent:codex-gen` | **started by hand** (section 3, step 4) | n/a | **AI** |

`churn_up.sh` also installs the codex-gen goal file (git `scripts/coordination/churn/GOAL-codex-gen.md`), `bin/flip_checkbox.py`,
`bin/keeper_qual_memo.py` and `bin/churn/{file_result,typed_classify,tokens_per_task}.py`. The full list is the `INSTALL=( … )`
array in `scripts/coordination/churn/churn_up.sh`, and that array is the inventory of record.

**Keeper versioning.** `F/ws58-calendar-keeper.current` holds the file name the watchdog starts. `churn_up.sh` pins it to
`KEEPER=ws58-calendar-keeper-v12.sh`. Older `ws58-calendar-keeper-v*.sh` files in `F` are inert history and run only if
`.current` names them. A new keeper version is a new git file plus a change to `KEEPER=`. Never edit a running `.sh` in place.

## 2. Preconditions (check all before spin-up)

1. **Operator clearance.** The 2026-11-02 ~11:55Z stop order still stands ("NOTHING SHOULD RUN INFERENCE ANYMORE";
   [progress](../../../progress/2026-11/2026-11-02-ws58.md)). Do not run a live spin-up until the operator lifts it.
2. **Disk.** Run `df -B1G --output=avail /mnt/raid0/llm`. The floor is 150 GiB (the `--status` "disk" line). Below it, reclaim first.
3. **No stray grants.** For every open `F/grants/*.grant` without `.ended`/`.complete`, check its pid (`--status` "grants"
   section). A dead-pid grant is moved aside by `churn_up.sh` (`grants/stale-reboot-<ts>/`). A live one that nobody owns must be
   resolved with its owner first.
4. **No old keeper running.** Run `--status`. The keeper row must be DOWN or show the `.current` version. Also check that no
   process argv holds any `F/ws58-calendar-keeper-v*.sh` other than the `.current` one (`churn_up.sh --stop --dry-run` lists
   such pids in its step-2 WARN lines).
5. **No duplicate loops.** Any `--status` line reading `UP WITHOUT PIDFILE` means a copy is running that the pidfile does not
   record. Stop it by pid first (`churn_up.sh --stop`), otherwise the duplicate guard keeps it and refuses a second copy.
6. **No live legacy grant writers.** The `--status` line `legacy-writers none` must be present.
7. **Stack state.** The pipeline does not manage the serving stack. Check it with
   `python3 /mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py status` and
   `rocm-smi --showuse --showmemuse` before granting GPU rows. The region-lock lanes must read `free`
   (`/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock status`, also printed by `--status`).
8. **Installed == git.** Every `--status` install line must read `ok`. A `DIFFERS` line means the runtime copy carries edits
   that are not in git. Commit them, or accept that churn_up overwrites them (it backs up to `ws58-keeper-state/*.bak-<ts>`).

## 3. Spin-up

```bash
cd R && git fetch origin && git status   # R must be on current origin/main
bash scripts/coordination/churn/churn_up.sh --status    # read-only baseline
bash scripts/coordination/churn/churn_up.sh --dry-run   # the plan: every INSTALL / MOVE / START line, nothing changed
bash scripts/coordination/churn/churn_up.sh             # live (only with operator clearance)
```

The live run does these steps in order:
1. Install every `INSTALL` entry: cp to a temp file, mv into place, then `cmp` against git (any mismatch is a FAIL). Set `.current`.
2. Clean reboot residue: dead-pid grants are moved to `grants/stale-reboot-<ts>/`. Dead `handoff-sessions.json` entries are set to
   `suspended`/`unpushed` (only while the dispatcher is down).
3. Start loops in order: **watchdog → keeper** (the watchdog's first pass starts it, and churn_up waits up to 30 s for
   `ws58-calendar-keeper.pid` to name a live `.current` process, otherwise FAIL) **→ dispatcher → backlog-gen →
   flow-scoreboard → disk-trend → filing-watch**. A component is skipped when its pidfile pid is alive with the right argv. It is
   also skipped (WARN, "NOT starting a duplicate") when any process argv holds its exact installed path.
   It is never matched by name.
4. By hand (churn_up never starts an agent or sends keys): in tmux `agent:claude`, run `claude` as ws58. In `agent:codex-gen`, run `codex`
   with the codex-gen goal file. churn_up prints the exact first messages.

## 4. Verification after spin-up: measure, do not infer

A grant file, a pidfile or a SNAPSHOT `busy=` entry is **not** evidence that compute is used. Sample utilisation over a
window while work is supposed to run, and take two samples at least 60 s apart.

**Per-quarter CPU% from `/proc/stat` deltas.** Quarter q is cpus `q*24..q*24+23` plus SMT siblings `q*24+96..q*24+119`.
```bash
python3 -I - <<'PY'
import time
def snap():
    d = {}
    for l in open("/proc/stat"):
        if l.startswith("cpu") and l[3].isdigit():
            f = l.split(); v = list(map(int, f[1:])); d[int(f[0][3:])] = (sum(v) - v[3] - v[4], sum(v))
    return d
a = snap(); time.sleep(30); b = snap()
for q in range(4):
    cpus = list(range(q*24, q*24+24)) + list(range(q*24+96, q*24+120))
    busy = sum(b[c][0]-a[c][0] for c in cpus); tot = sum(b[c][1]-a[c][1] for c in cpus)
    print(f"q{q} cpus {q*24}-{q*24+23},{q*24+96}-{q*24+119}: {100*busy/max(tot,1):.1f}%")
PY
```
**GPU.** Run `rocm-smi --showuse --showmemuse --showmeminfo vram`. Sample during the run: 0 % VRAM between kernels is normal
for `llama-bench`, so a single sample proves nothing.
**Ready rows.** `ls F/ready/*.json | wc -l` counts the published manifests. For one row, run `python3 -I F/bin/rowflow/rowflow.py --flags F status <id>`.
**Allocator plan without acting.** `python3 -I F/bin/rowflow/rowflow.py --flags F allocate --plan` (snapshot and plan, changes nothing).
**Live sessions.** The `churn_up.sh --status` section "handoff sessions" gives `live (N)` with pids, and `tmux list-windows -t agent`.
**Keeper.** `grep -E 'SNAPSHOT|IDLE-WHY|UNDERUSED' F/ws58-calendar-keeper.log | tail`. A `SNAPSHOT free=… busy=… cands=N assigned=M`
line appears every tick. `IDLE-WHY` names why a free lane got nothing. With rows ready (`cands>0`), a lane that stays in `free=`
for several ticks is a defect, not a quiet period.
**Disk.** `churn_up.sh --janitor=status` shows the janitor UP and its last log lines. Three checks: (1) the `FREE <n>GiB` lines
in `F/disk-janitor.log` are flat or rising across passes (`grep FREE F/disk-janitor.log | tail`); (2) `.trash` holds nothing
older than about 25 h (`ls /mnt/raid0/llm/.trash | head`: the `YYYYMMDD-HHMMSS-` prefix is the trash time); (3) no SCRATCH-COPY
is outstanding (`grep SCRATCH-COPY F/handoff-sessions.log | tail`: a path listed there that still exists is a copied checkout the
session was told to delete). The dispatcher also logs `SCRATCH-CLEANUP <slug> rc=…` when it retires a session (scratch_cleanup.py
apply on the handoff's `**Scratch**` roots, else `tmp/<slug>` + `worktrees/<slug>-*`), and wrapup.py removes the attempt dirs
a turn lists in `scratch_superseded`.
**Loops.** `churn_up.sh --status` must show every loop UP, no `DIFFERS`, no `DEAD` grant, and `churn_up status: OK` (exit 0).

## 5. Stop procedure

```bash
bash scripts/coordination/churn/churn_up.sh --stop --dry-run   # prints every STOP / MOVE it would do
bash scripts/coordination/churn/churn_up.sh --stop
```
The stop order is the one the operator gave on 2026-11-02. Each pid is found from its pidfile or by an exact installed-path argv
match. It gets TERM, then KILL after 10 s, and is verified gone with `ps -o pid= -p`. Nothing is matched by name.
1. Dispatcher. In-flight Codex turns already started finish and persist. The dispatcher starts no new ones.
2. Keeper watchdog(s), **then** the keeper main loop (`ws58-calendar-keeper.pid`). Stopping the keeper first lets the
   watchdog restart it. Other pids whose argv holds a keeper script are job-wrapper subshells. They are reported (WARN) and not signalled.
3. Revoke grants. Every open `grants/<id>.grant` (no `.ended`/`.complete`) and its `.wsg-`/`.wsq-granted-<id>` stamp is
   **moved** to `F/grants-revoked-<UTC ts>/`. Nothing is deleted.
4. Armed launchers. Each pid recorded in `dryrun/*/ARMED.json`, `dryrun/*/RUNNING.json` or `lane-*.queue` (field 2)
   whose argv names `filler_run` gets stopped.
5. The remaining zero-token loops: backlog-gen, flow-scoreboard, disk-trend, filing-watch.

The disk janitor is **not** stopped: disk hygiene is not inference. Stop it on its own with `churn_up.sh --janitor=stop`.

Afterwards, `--status` must show every loop DOWN and `== grants  no open grant`. Then sample CPU and GPU as in section 4 to
confirm the host is idle. Launchers that were never recorded (armed by hand outside rowflow) are not found by step 4. Look for
them with `ps -eo pid,lstart,args` and stop them by captured pid with their owner's agreement.

## 6. Audit checklist

| Question | Inspect | Proof line |
|---|---|---|
| Is every runtime file the git version? | `churn_up.sh --status` "install state" | `ok <sha16>` per file. Installs are logged in `F/churn-up.log` (`INSTALL …`). |
| Which keeper ran, and when? | `F/ws58-keeper-watchdog.log`, `F/ws58-calendar-keeper.log` | `keeper main loop (pid N) not alive; starting <file>`, then `keeper v12 start pid=N` |
| Who got compute, and why? | `F/ws58-calendar-keeper.log` | `SNAPSHOT …` (lanes free/busy, candidates, assigned), `GRANT …`, `IDLE-WHY …`, `UNDERUSED …`, `HEAL …` |
| Was the compute actually used? | `/proc/stat` and `rocm-smi` samples (section 4), the run's own result files | Utilisation measured during the window. Grants and SNAPSHOT `busy=` do not count. |
| Which row ran, and how did it end? | `F/grants/<id>.{grant,ended,complete}`, `F/dryrun/<id>/` | `.ended` rc and reason; `ARMED.json`/`RUNNING.json` pid and launcher sha256 |
| What did the dispatcher start? | `F/handoff-sessions.log`, `F/handoff-sessions.json`, `F/handoff-sessions/<slug>/*.jsonl` | `AUTO-START`, `RESUME <slug> pid=…`, `LANE-REAPED …` |
| Backlog fresh? | `F/backlog-gen.log` and the mtime of the `BACKLOG-*` files | one JSON count line every 10 min |
| Who stopped what? | `F/churn-up.log` | `STOP <label> pid …`, `KILL …`, `MOVE grant …` |
| Duplicates? | `churn_up.sh --status` | no `UP WITHOUT PIDFILE` line |

## 7. Known open defects

These are tracked as open boxes in [`handoffs/active/coordination-and-churn-pipeline.md`](../../../handoffs/active/coordination-and-churn-pipeline.md#track-churn-pipeline). Fix them there.
- Sub-quarter packing is unfixed (the packing agent was stopped).
- Rows with a non-inference payload get published as compute rows. On 2026-11-02 a gitnexus analyze row held all 96 cores.
- Row `estimate_s` is greatly overstated (estimator).
- Per-row `UNDERUSED` is only logged and never acted on.
- The dashboard's readied-waiting count is 0 (a row/handoff linking bug). The RTG-18 graph checkbox parse is broken.
- Sessions over-prepare instead of publishing. Row publication has not been measured since the 10:41Z fixes.
- SA-1/SA-2/SA-3 and JEV-3 (deferred) are open.
- Seen while writing this runbook (2026-11-02 12:18Z):
  - `backlog_gen.py` was running as pid 3814559 under `backlog-gen.pid`, not the wrapper's `ws58-backlog-gen.pid`. `--status`
    now reports this as `UP WITHOUT PIDFILE`.
  - filing-watch runs from a worktree (`worktrees/ws58-loop27`), not from `R`.
  - `bin/rowflow/publish_row.py` and `bin/churn/file_result.py` differ from git.
  - Five `filler_run13.sh` launchers armed on 10-30/10-31 were still alive after the stop.
  - A new grant (`codex-c6-gpu-route-20261102`, 12:17Z) appeared while the keeper was down.

## 8. Incident log

Today's incidents and the stop order: [`progress/2026-11/2026-11-02-ws58.md`](../../../progress/2026-11/2026-11-02-ws58.md)
→ *Incidents (recorded honestly)*. Record later incidents in that day's progress file and link them here.
