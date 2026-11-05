# Keeper friction review — 2026-11-05

**Operator ask (verbatim):** "all this manual mgmt is really annoying. It makes me think that the pipeline is STILL
broken. Review all the manual keeper work that [the main session] and the parallel claude session had to wrangle with
today. Identify potential refinements, bloat/friction removal, and streamlining fixes."

**Scope.** Read-only review of 2026-11-04 18:00Z → 2026-11-05 10:40Z: the keeper log
(`/mnt/raid0/llm/tmp/compute-flags/ws58-calendar-keeper.log`, 80,615 lines dated 11-05), `grants/`, `ready/`,
`filing-watch.log`, `disk-janitor.log`, the 1,083 commits on `origin/main` since 11-04 12:00, and the deployed code
under `compute-flags/bin/rowflow/` versus git. Nothing was launched, killed or edited on the live system. Evidence
commands are in the appendix. This is a review, not a change set; the "proposed SKILL.md diff" in §6 is not applied.

**Verdict in one paragraph.** The pipeline is not "still broken" in the sense of one defect; it is *under-specified at
the boundaries where a row's declaration is taken on faith*. Every manual intervention today traces to one of three
structural gaps: (1) **declared shape is never checked against what the job actually uses** (a 5 %-CPU single-worker
analyze booked 96 cores for 149 min, 22 times; a 1-thread perf profile booked host+GPU for 2.5 h); (2) **liveness of
the people-side of the loop is assumed** (filing waits on an owner session; the alarm ran from a deleted checkout for
three days; the dispatcher has no quota model); (3) **a row has no lifecycle verbs** (no withdraw/supersede, STOP is a
one-shot pre-start check, FILLERS.md is a hand-edited mirror that scripts read as truth). Today's fixes closed three
*instances* well (STOP-granted rows, migrate refusal, alarm re-raise) and one *class* (scratch leases + disk
admission). The seven refinements in §4 close the remaining classes; the first two alone remove most of today's idle
compute, the third and fifth remove most of the hand-kills and hand-filings.

---

## 1. Headline numbers (2026-11-05, 00:00–10:40Z unless stated)

| Measure | Value | Source |
|---|---|---|
| GRANT lines / distinct rows | 547 / 168 | keeper log `GRANT` |
| Grants of ONE stopped row (`lsa-oracle-reference-build-f6dddb7`) | **378 today, 1,344 since 11-04 18:23Z**, every ~9 s, rotating q1/q2/q3 | §3 F4 |
| Whole-host (`0-95`) grants today | ~32; **22 were gitnexus "impact" rows booking 149 min for 2–30 min of ~5 % CPU work** | §3 F3/F6 |
| Host+GPU exclusive grants today | 4 (`npd1-step2/3/4/5`); 55–65 min windows, 4–23 min actual | §3 F6 |
| akxall8 declared-floor v10..v39 | 32 host+gpu-quiet grants of **4 h 53 min each**, 27 died at 0.0 min on `disk-floor` | §3 F1 |
| Idle while candidates existed (floor) | **≈7.2 quarter-hours + ≈9.1 gpu-quiet-hours**; 3.9 q-h draining, 3.0 q-h "no runnable row" | `IDLE-WHY` |
| DRAIN lines / DRAIN-HELD | 726 / 351; two episodes 00:00→08:19 and 09:10→10:39 | `DRAIN` |
| RANK-SKIP | 2,692, ~155 each for the eight whole-host impact rows | `RANK-SKIP` |
| smoke-fail notifies on three parked-but-ranked rows | 469 | `notify` |
| Filing alarm `unknown rc=2` | **3,981 lines (11-02 → 11-05 09:43Z), one per minute** | `filing-watch.log` |
| Commits on origin/main since 11-04 12:00 | 1,083: **99 "Regenerate handoff index files"**, ~170 lane-merge commits | `git log` |
| Keeper tick | 11–17 s median, p90 125 s (not the documented 120 s) | SNAPSHOT diffs |
| Free disk | 304 GiB 00:17 → 205 GiB latest (−100 GiB today, −60 in the last 2 h) | `disk-janitor.log` |

Two caveats. `IDLE-WHY` fires only when a region is free *and* candidates are visible, so the idle figure is a floor;
05–07h shows almost no IDLE-WHY because the quarters were *booked* (by 149-min impact grants) while running nothing.
And the keeper SNAPSHOT has no READY/ARMED/BACKLOG counters at all, so the operator's "291 BACKLOG / 160 closed" cannot
be verified from the keeper; the only trace is FILLERS.md CANCELLED going 57 → 279 between its 11-04 and
11-05-opclose backups.

---

## 2. Where the code and the deployment stand (orientation for the fixes)

- Deployed `rowflow.py` (10:16Z) == origin/main `62bcc3eb5`; deployed `publish_row.py`, `filler_run15.sh`, keeper
  v12 == git. **The shared clone `/workspace` HEAD lags origin/main** (at `db43f9dab`, 10:05Z) — anything that runs
  from `/workspace/scripts/...` (the filing watcher does) runs pre-fix code. (Friction 8.)
- Deployed `compute-flags/bin/handoff_sessions.py` (the dispatcher) **does not start**: `SyntaxError` at line 19 (a
  stray `!def awaiting_prompt`), per `handoff-sessions.dispatcher.out`; it also lags git (no mailbox import, no
  alert-wake loop). So "the dispatcher was stopped by hand" is now also "the dispatcher cannot be restarted as
  deployed".
- No git ref carries a gitnexus-guard change beyond `94bcd0003` (one quarter). The branch
  `gitnexus-q3-subquarter-20261105` touches handoffs only. The "sub-quarter on q3" rule the operator stated exists
  nowhere in code or docs.
- `scripts/queue_status.py` (named in CLAUDE.md) does not exist at that path.

---

## 3. The frictions — root cause, hand work, instance-or-class

### F1. Disk exhaustion and the scratch leak (KEEP markers; akagg death spiral)

- **Root cause (structural).** Three independent reapers and no owner for *inputs*: KEEP was a permanent, ownerless
  marker; re-derivable inputs (worktrees, 2 GB research snapshots) were freed only by the end-of-row reaper days
  later; admission never considered disk, so the allocator granted into a floor it then enforced by killing. A kill is
  a republish trigger for akagg (vN+1 with a fresh 2 GB snapshot), so the floor *caused* the next breach. 32
  whole-host+gpu-quiet 4 h 53 min bookings between 21:02 and 00:25, 27 of which died at 0.0 min.
- **By hand.** Takeover of 308 KEEP leases, 25 stale `.git/worktrees/owned-research*` entries removed one by one,
  56 GB akxall8 cleanup, 72 stale-armed FILLERS rows cleared.
- **Landed.** `c65eaf73f` (leases: owner + TTL), `abb927499` (release on `.ended`/supersession, 150 GiB admission
  WAIT, disk-floor predecessor reuses `scratch_root`), `7bbb70b01` (CAS hardlink snapshot, *not yet adopted* by akagg).
- **Class or instance?** Leases + admission is a **class** fix for the *leak* and the *grant-into-floor*. The death
  spiral is only **half** closed: a disk-floor kill still produces a republish, and until akagg adopts
  `akagg_research_snapshot.py` each republish still costs 2 GB. The six reaper code paths remain (§5 B3).

### F2. Dispatcher without quota awareness; filing tied to dead owner sessions; alarm rc=2 for three days; re-alarms

- **Root cause (structural).** (a) `handoff_sessions.py` treats a quota hit as a transient: `USAGE_RX` (`:74`) matches
  `usage limit|rate limit|quota exceeded|...` in a transcript tail → global `paused_until = now + 30 min` (`PAUSE_S`
  `:76`), then resumes. A weekly quota that resets 2026-11-11 07:36 therefore produces a resume-fail-pause cycle every
  30 min with no escalation and no reset-time model. (b) Filing is by design the owner's turn: the dispatcher resumes
  the owner with `result_path` + `decision_rule` and the owner touches `filing-done/<id>.FILED`
  (`backlog-churn-flow.md:56,235`). `file_result.py` *can* file any numeric `decision_rule` (`rc` is always a metric),
  but **nothing runs it on `.ended`** except the dispatcher — so when the dispatcher dies, machine-fileable rows wait
  for a human too. (c) `filing_watch.sh:10` computes `ROOT` from `$0`; launched by `churn_up.sh:237` from a worktree
  that was later removed, bash kept the already-read script alive and `python3 $ROOT/.../filing_takeover_alarm.py`
  failed every minute for three days — **3,981 `unknown rc=2` lines**, and the watcher logs only the rc, never the
  reason (`:46`). (d) The alarm re-raised rows no filer could act on (smoke-only, moved-aside `.false-complete-*`).
- **By hand.** Dispatcher stopped manually; ~40 run-ends filed by a takeover session across six commits
  (`615fdc35a`, `020bdd856`, `cfac40240`, `9a5f43e42`, `e4e306962`, `e5ad2fdd8`, `0fd588958`); watcher restarted from
  `/workspace` at 09:43Z; an ad-hoc second alarm consumer (`tail -F filing-due.jsonl | python3 -c ...`, 10:14Z) was
  started alongside it.
- **Landed.** `8bdfa5cb1` (alarm skips unfileable rows — **instance**: the two offending ids are still in
  `filing-alarm.sent.json`), `b35d36092` (inference mailbox — class fix for *alert delivery*, not for filing),
  `26b9202c2` (slot ordering only). Nothing landed for quota, for owner-less filing, or for the `$0`-relative ROOT.
- **Class or instance?** Instance only. The three classes remain: quota blindness (§4 f), filing depends on a live
  owner (§4 e), watcher path is launch-site-relative (§5 B4).

### F3. gitnexus impact rows booked the whole host for a single-worker analyze

- **Root cause (structural).** Two over-declarations the publisher accepts without question. The manifests say
  `shape: host, regions: 0-95, estimate_s: 7200, busy_fraction: null` for a `gitnexus analyze --workers 1` that
  measures ~5 % CPU. `row_busy()` treats absent `busy_fraction` as 1.0 ("never demoted"), so the row was *eligible to
  drain the host* (`DRAIN_MIN_BUSY = 0.5` only bites on a *declared* low value). `shape_of()` and `publish()` have
  exactly one check — `shape in SHAPES` — and no evidence requirement for `host`/`quiet-host`. Downstream, the
  gitnexus guard (`scripts/gitnexus-guard.py`, `admit_whole_host:251`) demanded four-quarter flocks for any analyze,
  so a quarter grant failed admission; `94bcd0003` added `admit_one_quarter` for an unambiguous `--workers 1`. The
  guard still has no notion of a sub-quarter CPU list and no notion of "q3 minus 184-191".
- **By hand.** 22 whole-host grants (149 min each, 2–30 min of actual work, 38 `job-rc-1`); 18 republications with
  `-q/-q2/-q3` suffixes (kpf131-r5 ×3, seven rows ×2) between 09:26 and 10:13Z; one `launch.sh` pointed at the wrong
  job dir; jobs ignored STOP mid-analyze and were killed by hand; guard rule changed once in git, the sub-quarter
  version never landed.
- **Class or instance?** `94bcd0003` is a **rule relaxation for one tool**, not a class fix: a *declared* host shape
  with a *known* 1-thread footprint is still accepted at publish, still books the host, and still blocks drains.

### F4. Keeper granted a STOPped row every pass; quiet-host drain deadlock

- **Root cause (structural).** `parse_launcher` (`rowflow.py:218`) resolves only `VAR=value` assignments matching
  `^VAR=("?)[^\n"]*\2$`; the launcher idiom `D=$(cd "$(dirname "$0")" && pwd)` contains inner quotes and never
  matches, so `publish:616` wrote `"stop_file": "$D/oracle-build.STOP"` literally. `os.path.exists("$D/...")` is
  always false; the keeper granted, `filler_run15.sh:275` saw the real STOP at start, released the grant *without
  writing `.ended`*, and the next tick re-granted. 1,344 grants in 16 h, 51 of them inside the npd1-step5 drain window.
  The keeper never logged "granting a STOPped row" — zero STOP-semantics lines in the log.
- **By hand.** Diagnosis of a silent deadlock (drain waiting on a region that freed and refilled every 9 s), operator
  decision "Both: stop poller + fix keeper".
- **Landed.** `62bcc3eb5`: `resolve_stop_path()` (read-side substitution of a single `D=` assignment or dirname idiom),
  state `stopped` → never a candidate, dashboard uses the same helper.
- **Class or instance?** **Instance, read-side.** `publish()` still stores the unexpanded value, still has no
  `need(stop_file.startswith("/"))`, and an *unresolvable* stop_file is still "unknown = grantable" (`:1633`). The next
  launcher with a two-step `D=` assignment reproduces it. The class fix is a publish-time refusal (§4 c-ii).

### F5. Dashboard counted stopped / parked / done rows as "ready"

- **Root cause.** `dashboard/pipeline_status.py:_rows` (`161-217`) derives "ready" as *has `dryrun/<id>/PASS.json` and
  no grant/ended* (`:208-211`). It re-derives state instead of asking `rowflow.py status`, which is the only code that
  knows `parked` (3 lineage fails / 3 arm fails, `:1643-1648`) and now `stopped`. Two state machines, one authoritative.
- **By hand.** Operator read "28 readied" against an idle host and had to ask.
- **Landed.** `62bcc3eb5` adds `stopped`; **parked and held rows are still counted ready.** Instance.

### F6. GPU timing and a single-thread profile booked host + GPU; host ~94 % idle

- **Root cause (structural).** `shape_of()` (`rowflow.py:1130-1152`) maps `--gpu-quiet exclusive` + a claim covering
  ≥4 quarters to `quiet-host`, and `row_shape:1197` then books `REGIONS` = q0..q3 + gpu-quiet. `npd1-step5` is
  declared `cpu+gpu --gpu-quiet exclusive --claim-cpus 0-95`; `refactor-xgrammar-a2-alternated-profile-r3`
  (`OMP_NUM_THREADS=1`) was granted `0-95 gpuq=exclusive holds=gpu-quiet,q0-q3`, an 8,940 s window, ran 4.4 min
  rc=1. `parse_launcher` deliberately **skips** `--gpu-threads` and `--role` (`:247`) and reads no `OMP_NUM_THREADS`,
  `--workers`, `-t`/`--threads`; there is no thread field anywhere in the manifest schema. So a row may declare any
  shape and nothing — not the publisher, not the dry run (which *measures* the job and could record its busy
  fraction), not the keeper — compares declaration to footprint. SKILL.md §2 does say quiet host is "earned only by
  decision-grade baselines and AK keep gates", but no code reads `decision` for that purpose (`--print-class` is the
  retired `validate_fillers.py` path).
- **The operator's rule, verbatim:** a GPU timing run "just needs a quiet q3"; gitnexus may still use q3 if it avoids
  the GPU management threads; this "should be CORE project knowledge". It is consistent with the 2026-10-22
  co-residency measurement (pinned GPU threads: CPU decode −1 %, prefill −5 %, SMT channel −9.6 %) and with the
  memory `feedback_gpu_cpu_coresidency_policy.md`. **No code today distinguishes "q3 quiet" from "host quiet".** The
  rowflow building blocks exist — `qthreads:1017` knows 184-191 are q3's siblings, `cpu_tokens(gpu_threads=True)`
  yields `t184..t191`, `plan:1376,2640` frees them when gpu-quiet is free — but there is no shape that *holds gpu-quiet
  + c72-95 + t184-191 and leaves q0-q2 free*, and no rule that lets a non-GPU-thread row backfill c72-95.
- **By hand.** Nothing could be done except watch the drain (60 ticks, 09:54→10:39, target moved from 11:07Z to
  12:39Z) and ask why the host was idle.
- **Landed.** Nothing. **Open class** (§4 a, b).

### F7. Superseded rows pile up; FILLERS:<id> blocked `--migrate`; wrong handoff_task; 171 inherited lineage failures

- **Root cause (structural).** A row has no *withdraw* verb. `supersedes`/`lineage`/`lineage_reset` are
  pass-through fields (`rowflow.py:632,706`); nothing acts on `supersedes` at publish time to end the predecessor, so
  predecessors stay candidates until a human edits them out. FILLERS.md is a hand-kept mirror the keeper (`:186,207`),
  `backlog_priority.py`, `qualify_launcher.py`, `prior_check.py`, `science_scoreboard.py` and the fillers all read as
  truth; closing a row therefore means editing a 929-line markdown table (60+ `.bak-*` siblings prove it). `--migrate`
  refused every v3 manifest because `spec_from_legacy` read `handoff_task` only from legacy keys and fell through to
  `FILLERS:<id>`, which `check_handoff:163` rejects (8/8 refused). `lineage_fails()` sums FAIL files across the whole
  `supersedes` chain *and orphan `dryrun/*` dirs* (`:1514`); a chain whose early versions failed for reasons already
  fixed carries those failures forever unless `lineage_reset` is set by hand → `parked`.
- **By hand.** ~160 FILLERS.md CANCELLED edits (57 → 279), republish of orphaned rows as v15 successors
  (`86f83d8cb`), hand-set `handoff_task`, 171 lineage failures inherited by parked rows.
- **Landed.** `86a71ad63` (`legacy_handoff_task()`) — **instance**: migrate works again; nothing withdraws predecessors,
  nothing regenerates FILLERS.md, lineage still inherits unconditionally.

### F8. Stale shared-clone checkout; q38p filing; index_state stale block; index_regen churn

- **Root cause.** (a) Fixes are committed from side worktrees (correct), but two long-running processes execute code
  from `/workspace` (the filing watcher) or from an unpinned `compute-flags/bin` copy (the dispatcher), so a fix is
  "landed" in git and "not running" on the host at the same time; nothing deploys. (b) `index_state.py --check`
  (`:1176-1190`) requires the master-index generated block to match *verbatim*, including per-domain `age_days` and
  `generated_at`; any handoff edit stales it, so every wrap-up needs a regen commit, and the `index_regen.py` loop
  (dispatcher-spawned, 600 s min interval, worktree `/mnt/raid0/llm/worktrees/index-regen` reset to origin/main) commits
  **99 times in 23 h** mostly changing timestamps (`4fd5c16a7` is 1 line: `generated_at`). Two manual regens today
  (`852d1d108`, `7381fb878`) were needed because the loop regenerates origin/main while the committing checkout had
  newer handoff edits — and because the loop's parent, the dispatcher, is dead.
- **Class or instance?** Open. §5 B1, B4.

---

## 4. Ranked refinements

Ranking key: **idle compute-hours/week avoided** (from today's floor ×7, discounted where today was unusual) and
**operator interventions/week avoided**. Each item names file + function, the rule, and the test that proves it.
Items (a)–(g) are the ones requested; H–K were found in the review.

| # | Refinement | Idle h/wk avoided | Interventions/wk avoided |
|---|---|---|---|
| 1 | (a) Right-size shapes from evidence; refuse over-declared host/quiet-host | ~40 quarter-h + ~25 gpu-h | 15–20 (republish/rebook) |
| 2 | (b) GPU-timing shape = gpu-quiet + q3; q3 non-GPU-thread backfill | ~20 quarter-h | 3–5 ("why is the host idle") |
| 3 | (e) Keeper-side auto-filing; standing filer for owner-less rows | 0 direct; frees rows 1–3 h earlier | **~40 hand filings** |
| 4 | (c) STOP honoured mid-job; publish-time absolute stop_file | ~10 quarter-h (drain deadlocks) | 5–10 hand-kills |
| 5 | (d) Supersede withdraws predecessors; lineage reset on supersede | ~5 quarter-h (parked churn) | ~160 edits/wk → 0 |
| 6 | (f) Dispatcher quota model | 0 direct; prevents resume storms | 2–3 stops + the filing backlog they cause |
| 7 | (g)+§5 Bloat deletion (FILLERS.md as truth, 15 keeper copies, dual reapers, dual dashboard state) | — | ~10 (mystery states) |

### 1 — (a) Right-size shapes from evidence; refuse over-declaration at publish

- **Where.** `scripts/coordination/rowflow/rowflow.py`: `parse_launcher` (`:212`), `shape_of` (`:1130`),
  `check_busy_fraction` (`:1238`), `row_busy` (`:1247`), `publish` (`:598-640`); `publish_row.py` spec load; the
  dry-run runner (whatever writes `dryrun/<id>/PASS.json`).
- **Rule.**
  1. `parse_launcher` stops skipping thread knobs: record `threads` from `-t/--threads/--gpu-threads/--workers N`,
     `OMP_NUM_THREADS=N` / `GOMP_CPU_AFFINITY`, and `taskset -c LIST` found in the launcher or its `job.sh`. Store as
     `declared_threads` on the manifest.
  2. New `infer_busy(spec, launcher)` → `busy_fraction` default is **no longer 1.0**: it is
     `min(1, declared_threads / claimed_cpus)` when threads are known; unknown stays 1.0 but is logged `BUSY-UNKNOWN`.
  3. **Publish refusal** (`need(...)` in `publish`): a row whose derived shape is `host` or `quiet-host` must satisfy
     one of: `busy_fraction ≥ 0.5` with `declared_threads ≥ 48`; **or** `decision` cites a decision-grade baseline /
     AK keep gate (`baseline_ref:` path under `artifacts/` or `kernels/`, must exist) **or** `--shape-override
     "operator: <who> <date>: <why>"`. Otherwise publish prints the right-sized shape (`quarter` for `threads ≤ 24`,
     `multi-quarter(n)` for `ceil(threads/24)`, `gpu-q3` for a GPU row — item 2) and exits 65.
  4. **Dry run measures.** The qualifier already runs the real launcher; have it sample `/proc/<pgid>/stat` utime
     over its last 60 s and write `measured_busy_fraction` and `measured_threads` into `PASS.json`. The keeper then
     uses `min(declared, measured)` for drain eligibility and logs `SHAPE-DOWNSIZE <id> host→quarter (measured 0.05)`.
     The grant-time `.ended` already records `estimated_wall_s`; add `measured_busy_fraction` beside it so the
     filing step can flag "declared 1.0, measured 0.05" as a row-quality finding.
- **Why this ordering.** Refusal at publish is the cheap, deterministic half (catches `--workers 1`,
  `OMP_NUM_THREADS=1`, every gitnexus row — all 25 of today's `shape=host/regions=0-95` impact/census manifests would
  have been refused or right-sized). Measurement at dry run is the half that catches jobs whose footprint is not in
  the argv.
- **Tests.** `scripts/coordination/tests/test_rowflow_shape_evidence.py`:
  `test_workers1_host_refused` (gitnexus argv, shape host → rc 65, message names `quarter`);
  `test_omp1_quiet_host_refused` (xgrammar r3 argv); `test_quiet_host_with_baseline_ref_admitted`;
  `test_declared_threads_sets_busy_fraction` (`-t 24` on `0-95` → 0.25, `row_busy` returns 0.25, never drains host);
  `test_measured_busy_downsizes_drain` (PASS.json `measured_busy_fraction: 0.05` → `plan()` never promotes a drain);
  replay fixture: today's 25 manifests → 0 admitted as host.

### 2 — (b) GPU timing shape = gpu-quiet + q3 only, q3 backfill allowed

- **Where.** `rowflow.py` `SHAPES` (`:1126`), `shape_of` (`:1146`), `row_shape` (`:1169-1200`), `plan` (the hold
  computation at `:1376` and `:2640`, drain promotion `:1394`), `grant_regions` (`:1215`); `filler_run15.sh`
  `GPUTHR="184-191"` (`:46`) and its region parser; `scripts/gitnexus-guard.py` `admit_one_quarter` (`:197`).
- **Rule.**
  1. New shape `gpu-q3` = holds `gpu-quiet` + `t184..t191` + `c72..c95` *for timing-class rows* (so no CPU timing row
     and no whole-q3 claim may co-run), and leaves q0-q2 free. `shape_of` returns it for any row with
     `--gpu-quiet exclusive` whose class is `gpu` or `cpu+gpu`, **regardless of `--claim-cpus 0-95`** (log
     `SHAPE-DOWNSIZE quiet-host→gpu-q3`). `quiet-host` becomes reachable only via the baseline/override path of item 1.
  2. **Backfill rule.** While `gpu-q3` is held, `plan()` may place on `c72..c95` any row whose `class == correctness`
     (builds, analyzes, gitnexus) and whose `claim_cpus ⊆ 72-95` with `taskset` pinned; it may never place a
     `timing-pairable` or `quiet` row there. The grant line is the exact cpu list (`grant_regions` already does this
     for sub-quarter options). The keeper logs `BACKFILL <id> on c72-95 under gpu-q3 <gpu-id>`.
  3. The gitnexus guard gains `admit_cpu_list(cpus)`: a `--workers 1` analyze with a cpu list ⊆ one quarter is
     admitted on that list (flocks on the quarter + the list), which is the "sub-quarter on q3" rule the operator
     stated and that never landed.
  4. Write the rule into SKILL.md §2 (diff in §6) and into `docs/reference/gitnexus-compute-claims.md`.
- **Tests.** `test_rowflow_gpu_q3.py`: `test_npd1_step5_argv_maps_to_gpu_q3` (claim 0-95 + cpu+gpu + exclusive →
  `gpu-q3`, holds exactly `{gpu-quiet, t184..191, c72..95}`); `test_q0_q2_free_under_gpu_q3` (a quarter row is
  granted q0 while gpu-q3 runs); `test_correctness_backfills_q3_cores` (gitnexus row with `taskset -c 72-79` is placed);
  `test_timing_never_backfills_q3` (a `-t 8` llama-bench row is refused on c72-95 while gpu-q3 held);
  `tests/gitnexus/test_gitnexus_guard_cpulist.py::test_workers1_cpulist_q3_admitted`.

### 3 — (e) Filing that does not depend on a live owner session

- **Where.** `scripts/coordination/rowflow/ws58-calendar-keeper-v12.sh` (add step 7 `file_ended`, after
  `release_inputs` `:231`); `scripts/coordination/churn/file_result.py` (`decide` `:183`, `main`);
  `scripts/coordination/filing_watch.sh`; `handoff_sessions.py` filing slots.
- **Rule.**
  1. **Keeper files what a machine can file.** Each tick, for every `grants/<id>.ended|.complete` without
     `filing-done/<id>.FILED`, the keeper runs `file_result.py <id>`. Exit 0 → filed by `keeper` (`filed_by: keeper`),
     TICK line appended to `notify/inbox/inference.jsonl` as a *non-critical* alert for the owner to pick up at its
     next boundary (the tick itself is applied by `flip_checkbox` when `handoff_task` is `path:TOKEN`; the owner's
     review is a read, not a prerequisite). Exit 4 (`NEEDS-AGENT-VERDICT`) → the row goes to the **standing filer**.
  2. **Standing filer** = one headless clerk session (Opus/low; the model-routing table in `agents/README.md`) started
     by the keeper (not the dispatcher) when `filing-due` has ≥1 unfiled non-numeric row older than 20 min whose owner
     is not live (`handoff-sessions.json` status ≠ running, or heartbeat stale). It reads `result_path`,
     `decision_rule`, writes `--verdict-json`, and tags `filed_by: standing-filer`. The owner later confirms or amends
     (an amendment is a second verdict record, never an edit).
  3. `decision_rule` grammar grows two machine forms so fewer rows need an agent: `rc == 0 and exists(<path>)` and
     `jsonl_count(<path>) >= N` (both already implicit in PASS criteria at `backlog-churn-flow.md:53`).
  4. `filing_watch.sh` is folded into keeper step 7 and deleted (its two jobs — append `filing-due.jsonl`, run the
     alarm — become keeper calls); the alarm becomes `file_ended`'s report of what it could not file.
- **Tests.** `test_keeper_file_ended.py`: `test_rc0_numeric_rule_filed_by_keeper_without_owner`;
  `test_non_numeric_rule_routes_to_standing_filer_when_owner_dead`;
  `test_live_owner_keeps_first_claim` (owner running → no standing filer within 20 min);
  `test_filed_tick_lands_in_mailbox`; replay: today's 6 takeover-filing commits → ≥ 60 % of their rows would have
  been filed by the keeper (they were `rc`/count rules).

### 4 — (c) STOP honoured mid-job; stop_file absolute at publish

- **Where.** `/workspace/scripts/coordination/rowflow/filler_run15.sh` run loop (`:352-357`), `on_term` (`:247-252`),
  STOP check (`:275`); `rowflow.py` `publish` (`:616`), `parse_launcher` (`:218-227`), `resolve_stop_path` (`:263`).
- **Rule.**
  1. **Filler-side.** The run loop polls `FILLER_STOPFILE` every 10 s alongside hard-end and disk floor. On STOP:
     log `STOP seen, grace ${FILLER_STOP_GRACE_S:-600}s`, wait for the job to exit on its own (the contract at `:41`),
     then `kill -TERM -- -$PGID`, 30 s, `kill -KILL -- -$PGID`, verify with `ps -o pid= -p`, write
     `grants/<id>.ended rc=75 reason=stop-file` (rc 75 is already the clean-stop code at `backlog-churn-flow.md:53`).
     The dry-run already does exactly this ("a job that ignores the stop file after 600 s grace is truncated by
     signal", `:234`) — the live path simply never got it.
  2. **Pre-start STOP writes `.ended`.** `filler_run15.sh:275` currently releases the grant silently (that is what
     made F4 a *silent* 16-hour loop); it must write `.ended rc=75 reason=stop-file-before-start` so the keeper has an
     end record and can never re-grant.
  3. **Publish refusal.** `need(stop_file.startswith("/"))` in `publish`; `parse_launcher`'s assign regex accepts the
     two launcher-dir idioms *or* the publisher resolves via `resolve_stop_path` and refuses when the result is still
     not absolute. "Unknown = grantable" (`:1633`) becomes "unknown = refused at publish" so it cannot exist at
     allocation time.
- **Tests.** `test_filler_stop_midrun.sh` (bats or the existing shell harness): job that ignores STOP → SIGTERM at
  +grace, `.ended rc=75 reason=stop-file`, pgid dead; `test_stop_before_start_writes_ended`;
  `test_rowflow_stopped.py::test_publish_refuses_unexpanded_stop_file` (`$D/x.STOP` → rc 65);
  `test_publish_resolves_dirname_idiom`.

### 5 — (d) Supersede withdraws predecessors

- **Where.** `rowflow.py` `publish` (`:632` pass-through of `supersedes`), `lineage_of` (`:1497`), `lineage_fails`
  (`:1514`), `heal_grants` (`:2351`); `publish_row.py`.
- **Rule.**
  1. On publish of a row with `supersedes: [ids]` (or the implicit `-rN`/`-vN` → `-rN-1` stem match), the publisher
     **withdraws** each predecessor: moves `ready/<pred>.json` to `ready/.withdrawn/`, writes
     `grants/<pred>.ended rc=75 reason=superseded-by:<id>` if the predecessor is granted-but-not-started (a *running*
     predecessor is left alone and logged `SUPERSEDE-PENDING`; the keeper withdraws it at its `.ended`), touches
     `<pred>.STOP` if the predecessor's launcher is polling, and appends `SUPERSEDED by <id>` to its FILLERS.md row
     *if one exists* (transitional, until §5 B2 retires FILLERS.md as a read source).
  2. `lineage_fails` **resets at supersede when the successor declares `fix_ref: <commit>`** (the normal case: a new
     version exists because something was fixed). Only a successor with no `fix_ref` inherits the count. This replaces
     the hand-set `lineage_reset`.
  3. `rowflow.py withdraw <id> --reason TEXT` as an explicit verb for the operator/owner (today it is an edit).
- **Tests.** `test_rowflow_supersede.py`: `test_publish_r2_withdraws_r1_ready_manifest`;
  `test_running_predecessor_not_killed_but_pending`; `test_withdrawn_pred_never_candidate`;
  `test_fix_ref_resets_lineage_fails` (3 FAILs on r1, r2 with `fix_ref` → 0, not parked);
  `test_withdraw_verb_writes_ended_and_stop`.

### 6 — (f) Dispatcher quota awareness

- **Where.** `scripts/coordination/handoff_sessions.py` `USAGE_RX` (`:74`), `PAUSE_S` (`:76`), `dispatch_once`
  (`:1206-1238`), `paused` (`:1389`); state `compute-flags/handoff-sessions.json` `paused_until`.
- **Rule.**
  1. Parse the reset time: Codex's usage-limit message carries it (`resets <date/time>` / `try again in N h`); store
     `quota: {kind: weekly|5h, resets_at}` per *account*, not per session. `paused_until = resets_at`, not `now+30m`.
  2. Backoff when the reset is unknown: 30 min → 2 h → 6 h, and after the second hit in 24 h, raise exactly one
     operator alert (`route_alert`, already used for critical mailbox alerts) and stop resuming until acked.
  3. Quota is a **gate on resume/launch**, never on filing: while quota-paused, the dispatcher still runs
     `file_result.py` on `.ended` (overlaps item 3 — with keeper-side filing this becomes moot) and still spawns
     `index_regen` (or that moves to the keeper too, §5 B1).
  4. The deployed copy must be startable: `compute-flags/bin/handoff_sessions.py` has a `SyntaxError` at line 19;
     §5 B4's deploy step is the structural answer, a `python3 -m py_compile` in `churn_up.sh` before exec is the
     cheap guard.
- **Tests.** `test_handoff_sessions_quota.py`: `test_weekly_limit_sets_paused_until_reset`;
  `test_unknown_reset_backs_off_30m_2h_6h`; `test_second_hit_alerts_once_and_holds`;
  `test_paused_dispatcher_still_files`; `test_churn_up_refuses_uncompilable_dispatcher`.

### 7 — (g) Bloat to delete — see §5

---

## 5. Bloat and friction beyond the list

**B1. Index-regen commit churn (99 commits / 23 h; ~10 % of all commits).** `index_regen.py` commits when only
`generated_at`/`age_days` changed; `index_state.py --check` fails on those same fields. Rule: exclude timestamp and age
fields from both the commit test and the staleness test (compare the *row* content of the rollup block only); do not
commit when only `.index-graph.json` changed; run the loop from the keeper (always alive) rather than the dispatcher.
Test: regenerate twice with no handoff edits → zero commits; edit one row → one commit. Expected: ~90 fewer commits/day,
zero manual "Regenerate handoff index state" commits at wrap-up.

**B2. FILLERS.md as a read source.** 929 lines, 282 CANCELLED, 60+ `.bak-*` files, hand-edited, and read as truth by
keeper v12 (`:186,207` live-root guard), `backlog_priority.py:53,173`, `qualify_launcher.py`, `prior_check.py`,
`verdict_count.py`, `science_scoreboard.py`, and every `filler_run*.sh`. SKILL.md already calls it "the legacy
registry of rows armed before 2026-11-01". Rule: generate a read-only `FILLERS.generated.md` from `ready/` + `grants/`
+ `filing-done/` each tick for humans; move the seven readers to `rowflow.py status --json`; then delete FILLERS.md
and `validate_fillers.py`. Test: each reader's suite passes with FILLERS.md absent. Expected: the 160-edit class of
intervention disappears; the `FILLERS:<id>` handoff_task fallback (`rowflow.py:606-609`) is deleted with it.

**B3. Six reaper code paths, one real overlap.** Keeper step 6 `reap_filed` and `scripts/system/scratch_cleanup.py`
both remove dirs under `/mnt/raid0/llm/tmp` under the same KEEP/lease rule via different code; `disk_janitor.sh` then
sweeps the same trash a second time; `scratch_release.py` is a third deleter. Nothing ever deletes `grants/*.ended`
(2,400 files), `ready/*.json` (3,159), `filing-done/*` (1,969), `filing-due.jsonl` (1,212 rows, append-only), lease
files, or the hundreds of root-level `*_ENDED`/`*_FREED`/`*.flag`/`STOP.*` one-shot signals. Rule: one `reap`
entrypoint (`scratch_release.py`) with three policies (outputs after REAP_DAYS, inputs at `.ended`, records after
filing + 7 d → `compute-flags/archive/<month>/`); `scratch_cleanup.py` and the janitor's second sweep deleted. Test:
`--dry-run` on a fixture tree lists each path exactly once with one policy name.

**B4. Nothing deploys; two long-running processes run stale code.** The filing watcher computes `ROOT` from `$0`
(`filing_watch.sh:10`) and ran from a removed worktree for three days (3,981 silent `rc=2` lines); the deployed
dispatcher is a hand-copied `bin/handoff_sessions.py` that no longer compiles; `bin/` holds 8 `.bak-20261101-pre-*`
copies of two scripts; `compute-flags/` root holds keeper `v2…v11` + `v7b-e`. Rule: one `scripts/coordination/rowflow/deploy.sh`
that copies the pinned set from a named commit into `bin/`, writes `bin/DEPLOYED.json {commit, sha256s}`, and
`py_compile`s every `.py`; every long-running script resolves `ROOT` from `bin/DEPLOYED.json`, never from `$0`;
`verify_deploy` in the keeper's tick logs `DEPLOY-DRIFT` when `bin/` ≠ the manifest. Test: `deploy.sh --check` exits
non-zero on today's `bin/`. Also: the watcher must log the alarm's *stderr*, not only `rc=N` (`:46`).

**B5. Two state machines for row state.** `dashboard/pipeline_status.py:_rows` re-derives ready/running/ended from
files; `rowflow.py status` is authoritative and knows `parked`/`stopped`/`held`. Rule: the dashboard calls
`rowflow.py status --json` and renders; delete `_rows`' derivation. Test: a parked row shows `parked`, not `ready`.

**B6. Keeper SNAPSHOT lacks the counters people ask for.** SNAPSHOT has free/busy/cands/assigned/lanes/util but no
READY / ARMED / BACKLOG / PARKED / STOPPED / UNFILED counts, so "28 readied while nothing runs" and "291 BACKLOG"
cannot be checked against the log. Add them (one line, same tick) and the dashboard reads the same line.

**B7. Parked-but-ranked churn.** Three parked rows (kpf41-r5, kpf50-r2, kpf41-backend-gpu-qual) produced 469
smoke-fail notifies, 479 SKIP lines and 480 RE-PLANs in ten hours. A parked row must not be re-planned every tick: park
means *remove from candidates until the manifest sha changes*, and notify once.

**B8. Tick cadence vs documentation.** Documented 120 s, measured 11–17 s median with p90 125 s during reaps. The fast
tick is what turned F4 into 1,344 grants instead of ~500; the slow reap ticks are what delays everything else. Run
reaps in a separate process (they already have `--reap-now`), keep the allocator tick at a documented 30 s.

**B9. `scripts/queue_status.py` does not exist** at the path CLAUDE.md gives; `rowflow.py status` is the real tool.
Fix the pointer.

---

## 6. Core scheduling facts (one page, for SKILL.md)

These are the operator's rules restated as invariants. They are consistent with the 2026-10-22 gpu-cpu-noise
measurement (`feedback_gpu_cpu_coresidency_policy.md`) and with SKILL.md §2 as written; what is new is that they are
stated as *shapes the allocator enforces*, not as advice the publisher may ignore.

1. **The MI210's host threads are CPUs 184-191, the SMT siblings of q3 cores 88-95.** A GPU job touches nothing else on
   the CPU side when its threads are pinned (`HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` or `taskset -a -p` after health).
2. **A GPU timing run needs a quiet q3, not a quiet host.** Shape `gpu-q3` = `gpu-quiet` + `t184-191` + `c72-95`.
   q0-q2 stay free and are scheduled normally. Measured cost of a co-resident CPU job on q0-q2: decode −1 %, prefill
   −5 %; on the SMT channel (88-95 ↔ 184-191): prefill −9.6 %. That is why q3's *cores* are held and the other three
   quarters are not.
3. **Whole-host quiet (`quiet-host`) is earned, never declared.** It is admitted only for a decision-grade
   champion/candidate baseline or an AK keep gate that cites its floor file, or by an explicit operator override
   string. Indicative timing shares with a labelled GPU job; correctness shares with anything but CPU timing; builds
   and analyzes are correctness.
4. **Shape follows footprint.** A row that pins N threads (`-t`, `OMP_NUM_THREADS`, `--workers`, `taskset`) may claim
   at most `ceil(N/24)` quarters; the publisher right-sizes or refuses. A dry run records the measured busy fraction and
   the keeper trusts the smaller of declared and measured. `--workers 1` is a quarter at most; a 1-thread profile is a
   quarter at most.
5. **q3 is not reserved for the GPU.** While `gpu-q3` is held, correctness work (gitnexus analyze, builds) may backfill
   `c72-95` pinned by cpu list; CPU *timing* may not. The gitnexus guard admits a `--workers 1` analyze on any single
   quarter or on an explicit cpu list inside one quarter, q3 included, as long as it does not touch 184-191.
6. **Whole-host CPU models eat the SMT hit.** A model that needs all four quarters keeps 88-95 (dropping 8 cores costs
   about as much as the −9.6 % channel contention). A partial-host CPU model is placed off q3 when a GPU job is live.
7. **Production may run GPU + CPU inference concurrently** (operator, 2026-10-22). Idle compute costs more than the
   measured co-residency penalty. The only exceptions are rule 3's decision-grade windows.
8. **A row has a lifecycle, and every transition leaves a record.** STOP seen before start or mid-run → `.ended rc=75
   reason=stop-file`; supersede → predecessor withdrawn with `.ended reason=superseded-by:<id>`; filed → `.FILED` by
   keeper, standing filer or owner. A row the keeper cannot find a record for is a bug in the keeper, never a reason to
   re-grant.

### Proposed SKILL.md diff (not applied)

```diff
--- a/.claude/skills/inference-backlog-scheduling/SKILL.md
+++ b/.claude/skills/inference-backlog-scheduling/SKILL.md
@@ ## 2. Compatibility rules (what may share a bin)
-- **Quiet host** (gpu-quiet exclusive + all of 0-95, nothing else running) is earned only by
-  decision-grade baselines and AK keep gates. Indicative timing shares with a labelled GPU job (and
-  the GPU-on/off difference is itself a wanted measurement). Correctness shares with anything but
-  CPU timing. Builds are correctness.
+- **Core scheduling facts (operator, 2026-10-22 and 2026-11-05).** The MI210's host threads are CPUs
+  184-191, the SMT siblings of q3 cores 88-95. **A GPU timing run needs a quiet q3, not a quiet
+  host**: shape `gpu-q3` = `gpu-quiet` + `t184-191` + `c72-95`; q0-q2 stay schedulable (measured
+  co-residency cost off q3: decode -1 %, prefill -5 %; on the SMT channel -9.6 %, which is why q3's
+  cores are held). **Whole-host quiet (`quiet-host`) is earned, never declared**: only a
+  decision-grade champion/candidate baseline or an AK keep gate citing its floor file (or an explicit
+  operator override string) is admitted to it; `publish_row.py` refuses anything else and prints the
+  right-sized shape. Indicative timing shares with a labelled GPU job (the GPU-on/off difference is
+  itself a wanted measurement). Correctness shares with anything but CPU timing; builds and analyzes
+  are correctness. **Production may run GPU + CPU inference concurrently**; idle compute costs more
+  than the measured penalty (`feedback_gpu_cpu_coresidency_policy.md`).
+- **Shape follows footprint.** A row that pins N threads (`-t`, `OMP_NUM_THREADS`, `--workers`,
+  `taskset`) may claim at most `ceil(N/24)` quarters; the publisher right-sizes or refuses, the dry
+  run records `measured_busy_fraction`, and the keeper trusts the smaller of declared and measured.
+  `gitnexus analyze --workers 1` and a one-thread perf profile are a quarter at most. Origin
+  2026-11-05: 22 whole-host 149-min bookings for 2-30 min single-worker analyzes, and a 1-thread
+  profile holding host+GPU for 2.5 h while the host sat ~94 % idle.
+- **q3 is not reserved for the GPU.** While `gpu-q3` is held, correctness work (gitnexus, builds)
+  may backfill `c72-95` pinned by cpu list; CPU timing may not. The gitnexus guard admits a
+  `--workers 1` analyze on any single quarter or on a cpu list inside one quarter, q3 included, as
+  long as it does not touch 184-191.
@@ ## 4. Invariants, each bought by an incident
+- **A row has a lifecycle and every transition leaves a record** (2026-11-05). STOP seen before
+  start or mid-run -> `grants/<id>.ended rc=75 reason=stop-file` (filler-side SIGTERM to the job
+  group after the grace period; nobody hand-kills). Publishing `-rN` withdraws `-rN-1`
+  (`.ended reason=superseded-by:<id>`; lineage failures reset when the successor names `fix_ref`).
+  Filing never waits on a live owner: the keeper files machine-checkable `decision_rule`s itself and
+  routes the rest to the standing filer when the owner is not live. A row the keeper cannot find a
+  record for is a keeper bug, never a reason to re-grant. Origin: `lsa-oracle-reference-build`
+  granted 1,344 times in 16 h because a STOPped launcher released its grant without an `.ended`.
```

---

## 7. What today's fixes closed, in one table

| Friction | Landed today | Class closed? | Remaining class → §4 item |
|---|---|---|---|
| F1 scratch leak / disk | c65eaf73f, abb927499, 7bbb70b01 | **Yes** (leak, grant-into-floor) | akagg adoption; reaper consolidation (B3) |
| F2 dispatcher/filing/alarm | 8bdfa5cb1, b35d36092, 26b9202c2 | No | (e) keeper filing, (f) quota, B4 deploy |
| F3 gitnexus whole-host | 94bcd0003 | No (rule relaxed for one tool) | (a), (b)-3 guard cpu list |
| F4 STOPped row granted | 62bcc3eb5 | No (read-side) | (c) |
| F5 dashboard "ready" | 62bcc3eb5 (stopped only) | No | B5 |
| F6 GPU/1-thread host booking | — | No | (a), (b) |
| F7 supersede / migrate / lineage | 86a71ad63 | No | (d), B2 |
| F8 stale checkout / index block | manual regens | No | B1, B4 |

---

## Appendix — evidence commands

```
L=/mnt/raid0/llm/tmp/compute-flags/ws58-calendar-keeper.log
grep '^2026-11-05' $L | grep ' GRANT ' | awk '{print substr($1,1,13)}' | uniq -c          # grants/hour
grep '^2026-11-05' $L | grep ' GRANT ' | awk '{print $3}' | sort | uniq -c | sort -rn | head  # 378x lsa-oracle
grep ' GRANT lsa-oracle-reference-build' $L | wc -l                                        # 1344
grep '^2026-11-05' $L | grep ' IDLE-WHY ' | sed -E 's/[a-z0-9-]+-2026[0-9]+(-r[0-9]+)?//g; s/[0-9]+:[0-9]+Z//g' | sort | uniq -c | sort -rn | head
grep '^2026-11-05' $L | grep -c ' DRAIN '; grep '^2026-11-05' $L | grep -c 'DRAIN-HELD'
grep '^2026-11-05' $L | grep ' RANK-SKIP ' | wc -l
grep -c 'unknown rc=2' /mnt/raid0/llm/tmp/compute-flags/filing-watch.log                   # 3981
grep FREE /mnt/raid0/llm/tmp/compute-flags/disk-janitor.log | tail -12
python3 -c 'import json,glob;print(sum(1 for f in glob.glob("/mnt/raid0/llm/tmp/compute-flags/ready/*.json") if (d:=json.load(open(f))).get("shape") in ("host","quarter") and d.get("regions")=="0-95"))'
git -C /workspace log origin/main --since=2026-11-04T12:00 --format=%s | sed -E 's/[:(].*//' | sort | uniq -c | sort -rn | head
git -C /workspace branch -a --contains 62bcc3eb5; git -C /workspace rev-parse --short HEAD origin/main
```

Code references were taken from `origin/main` at `7381fb878` (`scripts/coordination/rowflow/rowflow.py` line
numbers), the deployed `/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh`, and
`/workspace/scripts/coordination/{handoff_sessions.py,filing_watch.sh,filing_takeover_alarm.py,churn/file_result.py}`.
