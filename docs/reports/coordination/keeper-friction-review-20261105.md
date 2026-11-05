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

---
---

# Pass 2 (2026-11-05, 12:00Z) — why it keeps happening one bug at a time, and the smallest change that ends the class

**Operator ask:** "more pipeline bugs/inefficiencies." Since pass 1 (`66c924949`, 10:53Z) seven more fixes were
deployed in 48 minutes — `4a4b8e2e3` 11:01, `fa00623d5` 11:03, `71d92b3e9` 11:15, `2134ef303` 11:20, `0dd38919e`
11:31, `0efbd47c8` 11:37, `d756221e8` 11:43, plus `c61a7430e` 11:49 — and eight new defects surfaced meanwhile. All
eight are verified below against the keeper log (10:40–11:57Z) and the code on `origin/main` (= deployed `bin/`,
byte-identical for `rowflow.py`, `publish_row.py`, `filler_run15.sh`, `auto_file.py`). Read-only; nothing live touched.

## P2.1 The pattern, with numbers

| Fact | Value |
|---|---|
| `rowflow.py` age | **5 days** (first commit 2026-11-01) |
| Size / functions / module tunables | 3,395 lines / 155 top-level `def` / **52 ALL_CAPS constants** |
| `plan()` rule branches | 25 `if/elif` on row attributes (47 with its helpers `:1644-1870`) |
| Commits touching `rowflow.py` | **59 in 5 days** (19 / 13 / 13 / 3 / **11 today**) |
| Deploy latency | minutes: the git copy *is* the deployed copy, swapped under running pollers (that is defect 3) |
| Tests | 29 files, 240 `def test_`, **zero** replay a real snapshot sequence; the three "replay" tests are hand-built single-snapshot candidate lists |
| Places that read a row's *declared* `shape` | 6 (`publish:739`, `shape_of:1333`, `coexist_host:1458`, `spec_from_legacy:878`, `status:2628`, `plan` cands `:3076`) |
| Live-measurement hooks that may **act** | **0** — `idle_held:2911` "never kills, never de-grants", `underused:2865` "never killed", `busy_flag:2234` annotates only |
| Operator alarm channel | **broken**: `ALERT-ROUTE … alarm_channel.py missing; alert only in ws58-keeper-alerts.jsonl` ×9 in the window |

**Why one bug at a time.** Every defect today has the same anatomy: a row *declares* something (`shape`, `regions`,
`busy_fraction`, `coexist_quiet_host`, a sealed digest), rowflow *trusts* it, holds are *computed once* at grant time
from the declaration, and nothing *compares* the declaration to the job's actual footprint or lock during the run. When
a declaration is wrong, the symptom shows up in whichever `plan()` branch that row type hits, the fix is a new
`need(...)` or a new `if` keyed on the same declared fields, and the next row type finds the next combination. The
fixes are correct as far as they go — and they are all **publish-time predicates over declared fields**, so they
cannot see what they are not told. Three structural facts make this permanent unless changed:

1. **Three resource models, no reconciliation.** *Declared* (manifest: `shape`, `regions`, `busy_fraction`,
   `declared_threads`), *reserved* (grant `holds=`, computed by `row_shape` once), *actual* (the region-lock flock the
   job takes — `GLOBAL.q3 EX` — plus `taskset`, `OMP`, VRAM, `/proc/stat`). rowflow infers the flock from argv
   (`parse_launcher` + the `GRANT_CPUS` marker, `:1250`) and never observes it; `host_snapshot` *does* measure actual
   CPU% / GPU% / VRAM each tick (`measure_util:2906`, `cpu_sample:2852`, `vram_used_bytes:2081`) and then only logs.
2. **Declared fields are the API.** `shape:` in the spec "wins" (`shape_of:1333`). The evidence gate added at 11:15
   (`:743-748`) fires for `host`/`quiet-host` only; `gpu`, `quarter`, `multi-quarter(n)` are still taken on faith, and
   `check_shape_evidence:1581` validates the *format* of `baseline_ref`, never the shape. Owners and agents keep
   over-declaring (defect 7) because nothing refuses them unless they hit exactly the gated string.
3. **The feedback loop is advisory.** `IDLE-HELD`, `UNDERUSED`, `OVER-DECLARED`, `IDLE-VIOLATION` all exist and all
   fired correctly today — and were disarmed on 11-03 after a single false positive (an engine spin-up de-granted r3,
   `:3071`). The alarm route they fall back to is missing (`alarm_channel.py`), so even the *advisory* path ends in a
   jsonl nobody reads. The system knows it is idle and tells no one who can act.

## P2.2 The eight new defects — verified

| # | Defect | Verified evidence | Deployed fix | Fix closes class? |
|---|---|---|---|---|
| 1 | Whole-host grant blocked new rows' smokes | `npd1-step5` GRANT 10:41:08Z `holds=gpu-quiet,q0-q3`, ran 2,453 s of a 3,900 s window. **Partly supported**: 10 `PASS.json` landed 10:41–10:59 on `WS58_REGIONS=0-3` *while q0 was held*; the two named victims failed on `smoke_predicate … never exited 0` (2,751 s wait for pareval) and `job-rc-1`, not on a slot. After the fix, pareval's requeued smoke waited 150 s (`SMOKE-WAIT` ×2). | `0efbd47c8` queue + WAIT | **No**: during a whole-host grant nothing is carved out, so a smoke waits the grant's whole window (`place_smokes:3002`); and `run_queued_smoke` (publish_row.py:269) turns *any* exception into FAIL + dequeue |
| 2 | Coexist rows beside a whole-host CPU row waited on `GLOBAL.q3` | 8 GRANTs 11:06:08Z on c72-87; kpf17-sq3 961 s, kpf41-sq3 955 s, both rc=1 within 1 s of npd1's `.ended` 11:22:05Z | `d756221e8` `coexist_host()` | **No**: still inferred from `declared_threads < 48`; a `quiet-host` gpu-lane row admitted via `baseline_ref`/`shape_override` with no parsable thread knob (`None < 48`) is coexist-eligible while its lock takes `GLOBAL.qN EX` → same 950 s wait |
| 3 | Sealed engine sha + mid-run redeploy killed jobs at start | poller.out `AssertionError: …/filler_run15.sh` (kpf17), `runtime helper digest mismatch: rowflow` (kpf41) | `0dd38919e` refuse packet | **No, wrong side**: it scans only the launcher dir for the *current* digest (`:1552-1578`), so a packet sealed to an *older* engine passes and still asserts; rowflow itself seals `engine.sha256` into the manifest (`:693`) and `PASS.json` (`:2625`). The redeploy under queued rows is the defect; sealing is the reproducibility feature |
| 4 | `inf34 A2 v15` (20 min GPU qual) published `mi210_0,0-95` + `shape: gpu` → drains GPU + q0-q3 to 01:50Z | 12× `DRAIN … (gpu) until 2026-11-06T01:50Z`, 5× IDLE-WHY `needs gpu-quiet,q0,q1,q2,q3`; withdrawn 11:54:35Z, v16 republished as `gpu-q3`. GPU was then taken by `kvu16g2-decstep` 11:54:43Z (util 100 %) | hand republish | **No**: `shape:` bypasses both gates; without it `shape_of` would have derived `gpu-q3` (`:1343-1348`). No test covers explicit `shape:` + wide regions |
| 5 | GPU row held gpu-quiet at 0 % for CPU post-processing | `hsf5p-profile6-q3-r1`: last non-zero util 11:41:56Z, `.ended` 11:50:38Z → **8.7 min 0 % tail**, 9× `IDLE-HELD gpu-quiet … 0%`, 2 ALERTs — nothing acted | none | **Open class**: no release path exists (`heal_grants:2822` only acts on a dead poller or a pre-START conflict) |
| 6 | Low-busy rows RANK-SKIP while q0 cores free | 14 lines: spec-gram3 (bf 0.3) ×8 at 11:06, kpf30-r9-sq3 (0.05) ×3, inf75 census (0.01) ×3; `free=` showed `q0,q1,q2` whole at 11:22:31 and partial q3 cores | none | **Semantics OK** (`own_block:1704`: a whole-quarter option needs 24 free cores; `_fits` is token-level) but a low-busy row never gets `rank_reservation` (`:1708-1737`) → can be starved indefinitely and logs RANK-SKIP every tick. spec-gram3 got q0 16 min later |
| 7 | 1-thread revival rows on whole-host bookings | xgrammar r3: `0-95`, 262 s, rc=1 (10:33); r4 republished `any-cpu-quarter`, bf 0.05, `declared_threads null`, est 7200 | `71d92b3e9` | **Partly**: `host` refusal works when derived; still nothing refuses `quarter` for a 1-thread job (est 7200 s on 24 cores for ~1 core of work) |
| 8 | kpf41 ignored STOP mid-analyze; gitnexus rebooked 5× | no STOP semantics lines for kpf41 in 10:40–11:30 (pre-fix); 24 manifests republished since 10:40, 9 suffixed `-sq3/-sq3b/-rN` | `2134ef303` | **Partly** — see P2.3 #8 |

Idle in the window (IDLE-HELD-based, floor): **0.94 gpu-quiet-hours** (npd1-step5 22 ticks, hsf5p 9 ticks) and
**~0.8 CPU quarter-hours**. Note npd1-step5's gpu-quiet 0 % is *correct* — it is a CPU-serving timing row that needs
the GPU *quiet*, not *used* — so the live audit also cannot yet tell *hold-for-quiet* from *hold-for-use*. That
distinction is the heart of the fix in P2.4 #1.

## P2.3 What is wrong in the deployed fixes themselves

1. **`71d92b3e9` evidence gate is bypassable by `shape:`** (defect 4) and gates two of five shapes. DEFECT.
2. **`71d92b3e9` supersede/withdraw + `2134ef303` STOP poll contradict each other.** `withdraw:764-797` touches the
   predecessor's STOP and returns PENDING "nothing is killed" (`:768`, `test_running_predecessor_not_killed_but_pending`);
   since `2134ef303` the filler polls STOP every 3 s and TERMs the job, so publishing `-rN` now **kills a running
   `-rN-1` within seconds**. The docstring and test describe pre-11:20 behaviour. Also: withdrawing an ARMED row (no
   grant) leaves its poller alive forever. DEFECT.
3. **`2134ef303` mid-job STOP kills only two process groups** (`$CUR` setsid group + recorded inner pgid); a
   `setsid`/`nohup` grandchild (llama-server from `job.sh`) survives unless registered in `$PIDFILE`, and `.ended rc=75
   reason=stopped` is written anyway. `gone()` uses `kill -0 -- -pgid`, which this sandbox cannot see
   (`feedback_kill0_blind_use_ps_for_liveness`). The "finish the current item" contract is gone (TERM immediately,
   KILL after 60 s) while `rowflow.py:100` still documents `STOP_GRACE_S = 600`. DEFECT.
4. **`0dd38919e` refuses the wrong side** (defect 3 row above). The right fix is a per-row engine snapshot under
   `scratch_root` (the launcher snapshot already does this for `snapshot: true`, `a41ff7610`) or asserting against the
   row's own `PASS.json` digest — and, structurally, **never redeploying the engine while a grant is open** (a deploy
   step that waits for `grants/*.grant` to be empty or snapshots per row). DEFECT.
5. **`fa00623d5`/`d756221e8` coexist criterion is a self-declaration.** `busy_fraction ≤ 0.1` (declared; hsf5p declared
   0.5, measured 0.019 — logged OVER-DECLARED, nothing else) and `declared_threads < 48` answer "does it perturb a CPU
   measurement", not "does its lock cover 72-87"; and they ignore L3 / memory-bandwidth interference on the shared NUMA
   node, which is the thing a *timing* row cares about. INCOMPLETE.
6. **`0efbd47c8` keeper smoke** has no carve-out under a whole-host grant (hours of SMOKE-WAIT), can take c72-75 and
   block a pending coexist row (COEXIST_Q3 reserved only while a quiet grant is open, `:3056`), and FAILs on any
   harness exception. INCOMPLETE.
7. **`auto_file.py` runs from `/workspace`** via the $0-relative `filing_watch.sh` (pid 798883, started 11:21:59 from
   the devcontainer tree) — the pass-1 B4 class, still open: nothing under `compute-flags/bin` carries the watcher.
8. **The alarm route is missing.** Every `ALERT` today ended as `ALERT-ROUTE … alarm_channel.py missing`. The
   escalation path pass 1 relied on for (e) and (f) does not exist on this host.

## P2.4 The smallest architectural change that ends the class — ranked by idle hours avoided

The five candidate changes the main session listed are not alternatives; four of them are one change seen from
different sides. **The one change: a single `Contract` per row, derived only from evidence, enforced at three points
(publish, start, every tick), with acting — not advisory — reconciliation.** The replay harness is how it is proved
before deploy. Everything else today is a special case of that.

### #1 Live reconciliation that acts: holds follow measured use (and declared phases) — ~1.5–2 gpu-h + ~1 q-h per day

- **Where.** `rowflow.py`: `idle_held:2911`, `underused:2865`, `heal_grants:2822`, `host_snapshot:2936`,
  `write_grant` holds (`:2783`); `filler_run15.sh` (phase file); the row manifest schema (`holds` gains a `purpose`).
- **Rule.**
  1. Every hold carries a **purpose**: `use` (the job runs on it) or `quiet` (the job needs it *idle*). `row_shape`
     emits it: GPU timing → `gpu-quiet:quiet`, `t184-191:use`, `c72-95:quiet`; CPU-serving timing (npd1-step5) →
     `q0-q3:use`, `gpu-quiet:quiet`; correctness → everything `use`. A `quiet` hold measuring 0 % is *healthy*; a
     `use` hold measuring < `IDLE_PCT` for `IDLE_HELD_AFTER_S` is **reclaimable**. This alone removes the npd1-step5
     false positive that disarmed the audit on 11-03 and the 22 IDLE-HELD ticks today.
  2. **Reclaim, never kill.** For a `use` hold idle for 2 consecutive samples ≥ 120 s (the two-sample rule in
     `INVARIANTS.md`), the keeper **shrinks the grant**: rewrites `holds=` without that region, logs
     `RECLAIM <region> from <id> (measured 0 % for Ns)`, frees it for `plan()` this tick, and writes
     `dryrun/<id>/RECLAIMED.json` for the owner. The job keeps running; its own flock is untouched (region-lock holds
     are the job's, keeper holds are the keeper's — reclaiming the keeper's reservation does not break the job). The
     next tenant's region-lock will wait if the old job still holds a flock, which is the existing, correct behaviour.
     GPU: `gpu-quiet` is reclaimed when VRAM-used < 1 GiB and util 0 % for two samples **and** the hold purpose is
     `use` (hsf5p's 8.7-min tail; `kvu16g2` would have started ~9 min earlier).
  3. **Release-on-phase (cooperative, preferred).** The job may write `<scratch_root>/PHASE` (`gpu-done`,
     `cpu-done`, `postprocess`); `filler_run15.sh` relays it to `grants/<id>.phase`; the keeper releases the holds the
     manifest maps to that phase (`phases: {gpu-done: [gpu-quiet, t184-191]}`). Measured reclaim is the fallback for
     jobs that do not declare phases.
  4. **Over-booked windows shrink too.** A grant past `estimate_s × 1.5` with measured use still high is an alarm
     (already "a failure to explain"); a grant past its estimate with *zero* use on every `use` hold is ended
     (`.ended rc=75 reason=idle-reclaimed`) — this is the only kill, and it needs two samples plus a 10-min floor.
- **Tests.** `test_rowflow_reconcile.py`: `test_quiet_hold_at_zero_is_healthy` (npd1-step5 fixture: no IDLE-HELD);
  `test_use_hold_idle_two_samples_reclaims_region` (hsf5p fixture: gpu-quiet freed at sample 2, grant rewritten,
  job pid untouched); `test_phase_file_releases_mapped_holds`; `test_reclaim_never_before_two_samples`
  (one 0 % sample → nothing); `test_engine_spinup_not_reclaimed` (the 11-03 false positive: 45 s at 0 % then 90 %
  → no action); replay (see #4): today's trace → gpu-quiet idle-held hours drop from 0.94 to < 0.2.

### #2 One `Contract`, derived only from evidence; declared shape advisory; refuse on mismatch — ~1 q-h/day + every "rebook ×5" and "drains until tomorrow"

- **Where.** `rowflow.py`: new `contract_of(spec, launcher, job, pass_json) -> Contract` replacing the six readers
  of `shape`; `publish:739-753`, `shape_of:1333`, `row_shape:1360`, `coexist_host:1449`, `is_coexist:1476`,
  `check_shape_evidence:1581`; `publish_row.py`; `scripts/gitnexus-guard.py admit`; `dashboard/pipeline_status.py`.
- **Rule.**
  1. `Contract = {cpus: set, gpu: bool, gpu_threads: set, quiet: set, purpose: {region: use|quiet}, threads: int,
     busy: float, ram_gib, est_s, phases}` is computed **only** from: launcher argv (`--class`, `--claim-cpus`,
     `--gpu-quiet`, `--no-fold-siblings`, `-t/--threads/--workers`, `OMP_NUM_THREADS`, `taskset`), `job.sh`, the
     region-lock claim the engine will take (`GRANT_CPUS` marker, else the parsed cpu list → `GLOBAL.qN EX` rule), and
     — after the smoke — `PASS.json` `measured_threads` / `measured_busy_fraction`.
  2. **The spec's `shape`, `regions`, `busy_fraction` become advisory**: `publish` computes the Contract, derives the
     shape from it, and if the spec disagrees prints both and **refuses** (`rc 65`) unless the spec carries
     `shape_override: "operator: <who> <date>: <why>"` — the override is logged in the manifest and in the keeper's
     GRANT line (`override=`). A `baseline_ref` admits `quiet-host` only when the Contract's `threads ≥ 48` *or* the
     referenced floor file names a CPU-serving measurement (`purpose q0-q3 = use`). `shape: gpu` + `--claim-cpus 0-95`
     → Contract says gpu-q3 → refuse with the right-sized spec printed. inf34 v15 would have been refused at 10:5x.
  3. **Width follows threads for every shape**, not only host: `threads ≤ 4` → a 4-core sub-quarter option (`c<n>-<n+3>`
     + siblings), `≤ 24` → quarter, `≤ 48` → multi-quarter(2). A 1-thread profile is a 4-core row; xgrammar r4's 24-core,
     7,200-s quarter booking becomes 4 cores.
  4. **Coexist is decided by the Contract's lock, not by `busy_fraction`:** a row may coexist on c72-87 beside a hold
     H iff `Contract.lock ∩ H.exclusive_lock = ∅` and `H.purpose[c72-87] ≠ quiet-for-cpu-timing`. That is a set test
     over two Contracts, replacing `is_coexist`/`coexist_host`/`QUIET_SHAPES`/the `coexist_quiet_host` marker.
  5. The gitnexus guard, the dashboard and `rowflow.py status` read the Contract (`rowflow.py contract <id> --json`);
     the guard's `admit_one_quarter`/`admit_whole_host` become `admit(contract.cpus)`.
- **Tests.** `test_rowflow_contract.py`: `test_spec_shape_gpu_with_claim_0_95_refused_contract_says_gpu_q3` (inf34
  v15 fixture); `test_omp1_quarter_spec_refused_contract_says_4_cores` (xgrammar r4); `test_override_admits_and_is_logged`;
  `test_coexist_is_lock_set_test` (npd1-step5 Contract vs kpf17-sq3 Contract → not coexist; gpu-q3 vs kpf17-sq3 →
  coexist); `test_six_shape_readers_gone` (grep guard: no `d.get("shape")` outside `contract_of`); replay: today's 24
  republished manifests → every `-sq3/-sq3b/-q2..-q5` republish is produced by `publish` itself as the right-sized
  shape, zero human rebooks.

### #3 Deploy = atomic, grant-aware; the engine a row ran its smoke on is the engine it runs on — removes defect 3's class and the "fix landed but not running" class (B4)

- **Where.** New `scripts/coordination/rowflow/deploy.sh`; `filler_run15.sh` engine resolution; `rowflow.py publish:693`
  (`engine.sha256`), `dryrun_run:2625`; `check_engine_not_sealed:1552` (delete).
- **Rule.** `deploy.sh <commit>` copies the pinned set into `bin/rowflow/<sha>/`, flips a `bin/rowflow/current`
  symlink, writes `DEPLOYED.json`. A row's manifest records `engine_dir=bin/rowflow/<sha>` at publish (it already
  records the sha); the poller and job use *that* dir, so a redeploy never changes a queued or running row's engine. Old
  engine dirs are reaped when no manifest references them. `check_engine_not_sealed` is deleted (sealing is now
  harmless). Every long-running script (`filing_watch.sh`, dispatcher, keeper) resolves `ROOT` from `DEPLOYED.json`.
- **Tests.** `test_deploy_pinned_engine.py`: `test_redeploy_does_not_change_queued_rows_engine`;
  `test_job_asserting_engine_sha_passes_after_redeploy`; `test_deploy_check_fails_on_unpinned_bin` (today's `bin/`);
  shell test: watcher started from a worktree, worktree removed, watcher's next pass still finds the alarm script.

### #4 Replay harness over the real keeper trace — prevents the next eight

- **Where.** `rowflow.py allocate` already builds one snapshot per tick; add `--trace <path>` that appends
  `{ts, free, cands, grants, util, vram}` as one JSON line per tick to `compute-flags/keeper-trace.jsonl` (≈ 2 KB/tick,
  ~15 MB/day, rotated with the log). New `scripts/coordination/tests/replay/replay_allocator.py` feeds a trace through
  `plan()` (pure since `db43f9dab`) and `reconcile()` and asserts **invariants**, not outcomes.
- **Invariants to assert** (each is one of today's defects): no id granted twice without an `.ended` between (F4);
  no `IDLE-VIOLATION` ≥ 3 ticks (a grantable row fits free regions and is not placed); no `use` hold at 0 % for
  > 2 samples without a RECLAIM (defect 5); no smoke queued > 600 s while ≥ 4 cores are free or reclaimable
  (defect 1); no coexist grant whose Contract lock intersects a live exclusive lock (defect 2); no drain promoted for a
  row whose Contract width < the drained region (defect 4); no RANK-SKIP of the same row > 30 consecutive ticks while
  a sub-option fits (defect 6); declared vs measured busy ratio > 5 flagged once, not per tick (defect 7).
- **Gate.** `deploy.sh` runs the replay over the last 24 h trace and refuses to flip `current` on an invariant failure.
  Cost: a few seconds (today's day is 805 snapshots).
- **Tests.** The harness is the test; seed it with today's trace reconstructed from the log (`SNAPSHOT` + `GRANT` +
  `IDLE-HELD` lines are enough for a coarse trace) and check in that fixture as
  `tests/replay/fixtures/2026-11-05.jsonl.gz`; `test_replay_2026_11_05_pre_fix_fails_four_invariants`;
  `test_replay_2026_11_05_post_fix_passes`.

### #5 One state model; everything else is a view — removes the F5/F7/B2 class

- **Where.** `rowflow.py` already is the state machine (`status:2540-2649` knows ready/armed/running/parked/stopped/
  withdrawn/ended/filed). Make its store authoritative: one `compute-flags/rows/<id>/` directory holding `spec.json`,
  `contract.json`, `events.jsonl` (publish, smoke, grant, start, phase, reclaim, ended, filed — append-only), with
  `ready/`, `grants/`, `dryrun/`, `filing-due.jsonl`, `filing-done/` and FILLERS.md **generated** from it or deleted.
- **Rule.** `rowflow.py status --json` is the only reader for the dashboard (`pipeline_status.py:_rows` deleted), the
  gitnexus guard, `backlog_priority.py`, `auto_file.py`, the alarm. Filing becomes an event (`filed_by: keeper |
  standing-filer | owner`), so "unfiled" is a query, not a second file. FILLERS.md is rendered read-only for humans.
- **Tests.** `test_rows_store.py`: `test_every_transition_appends_one_event`; `test_status_json_is_the_dashboard`
  (parked → "parked"); `test_no_second_writer` (grep guard: nothing outside rowflow writes under `rows/`).

### #6 "Idle with candidates" SLO that names the rule — smallest change, biggest visibility gain

- **Where.** `rowflow.py` `IDLE-VIOLATION` (`:3160-3227`) already computes "free regions + a grantable row fits + no
  grant this tick"; `IDLE-WHY` already names the reason per region. Join them: the alert line carries the `IDLE-WHY`
  reason of the blocking rule and the `plan()` branch name (add a `why` field to each refusal in `plan()`'s helpers:
  `own_block`, `rank_reservation`, `drain`, `coexist_host`), e.g. `IDLE-SLO q0 idle 14 min: rule=own_block
  (busy_fraction<0.5) row=spec-gram3`. SLO: any region idle with a fitting candidate > 10 min, or gpu-quiet held by a
  `use` hold at 0 % > 5 min, alerts **once** and escalates to the operator route.
- **Fix the route first**: `alarm_channel.py` is missing on this host; until it exists every alert is a jsonl line.
  `ALERT-ROUTE` must fail loudly (one `route-missing` operator mailbox entry per boot), not per tick.
- **Tests.** `test_idle_slo.py`: `test_slo_alert_names_blocking_rule_and_row`; `test_alert_once_per_episode`;
  `test_missing_route_is_one_mailbox_entry_not_per_tick`.

## P2.5 What NOT to do next

- **No more publish-time predicates on declared fields.** Each one is correct and each one leaves the next shape open.
  After #2 there is exactly one predicate: *spec ≠ Contract → refuse*.
- **No more `if shape == ...` branches in `plan()`.** `plan()` reads Contracts and purposes; the shape string is a
  display label.
- **No more same-hour deploys under live grants** until #3 lands; today's engine redeploy at 11:20 cost two 16-min
  jobs and produced a fix (`0dd38919e`) that forbids a legitimate reproducibility feature.
- **Do not re-arm `UNDERUSED`/`IDLE-HELD` as kills.** Re-arm them as *reclaims of `use` holds* (#1); the 11-03 false
  positive was a `use` hold during spin-up, and the two-sample + purpose rule handles it.

## P2.6 Expected effect

| Change | Idle avoided / day | Interventions avoided / day | Defects it would have prevented today |
|---|---|---|---|
| #1 reconcile (purpose + reclaim + phase) | ~1.5–2 gpu-h, ~1 q-h | 2–3 | 5, F6 tail, the 22 npd1 false IDLE-HELDs |
| #2 Contract from evidence | ~1 q-h + the "until tomorrow" drains | **all rebooks** (24 republishes today) | 4, 7, 2 (lock set test), F3, F6 |
| #3 pinned engine per row | 0 direct; 2 × 16-min jobs today | 1–2 | 3, B4 |
| #4 replay harness | prevention | the next eight | all eight, before deploy |
| #5 one state model | 0 direct | 3–5 (dashboard, FILLERS.md, filing) | F5, F7, B2 |
| #6 idle SLO + fixed route | makes the rest visible | — | silent 0.94 gpu-h today |

Of these, **#1 and #2 are the change**; #4 is how it is deployed safely; #3, #5, #6 are the hygiene that stops the
instance-fix treadmill from restarting. The order matters: #6's route fix is a one-hour job and should go first because
every other change reports through it.

## P2.7 Evidence commands (pass 2)

```
L=/mnt/raid0/llm/tmp/compute-flags/ws58-calendar-keeper.log
W() { grep -E '^2026-11-05T1[01]' $L | awk '$1>="2026-11-05T10:40"'; }
W | awk '{print $2}' | sort | uniq -c | sort -rn | head                    # IDLE-HELD 61, ALERT-ROUTE 9, IDLE-VIOLATION 0
W | grep 'ALERT-ROUTE' | head -2                                           # alarm_channel.py missing
W | grep hsf5p | grep -oE 'gpu=[0-9]+|IDLE-HELD.*' | head -20               # 0 % tail 11:44 -> 11:50
W | grep 'inf34' | grep -c DRAIN                                           # 12 drains to 01:50Z
grep -oE 'shape": "[a-z0-9()-]+' /mnt/raid0/llm/tmp/compute-flags/ready/.withdrawn/refactor-inf34-a2-gpu-qual-v15-20261105.json
cat /mnt/raid0/llm/tmp/compute-flags/grants/kpf17-*-sq3-*.ended            # 961 s, rc=1 (digest)
git -C /workspace log origin/main --since=7.days --format=%ad --date=short -- scripts/coordination/rowflow/rowflow.py | sort | uniq -c
git -C /workspace show origin/main:scripts/coordination/rowflow/rowflow.py | grep -c '^[A-Z_]* = '     # 52 tunables
cmp /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/rowflow.py <(git -C /workspace show origin/main:scripts/coordination/rowflow/rowflow.py)
```

## P2.8 Operator refinement (12:0xZ, folded into #1 and #2): q3 is quiet ONLY for GPU timing rows

Operator, watching btop with the GPU at 100 % and q3 cores 88-95 at ~1 %, verbatim: "when not performing timing work
on the GPU/CPU and, most importantly, in production we should totally allow q3 CPU use to take place in parallel with
the GPU use." This sharpens pass-1 fact 2 and fact 5 and is what `feedback_gpu_cpu_coresidency_policy.md` already
measured (pinned GPU threads: CPU decode −1 %, prefill −4.8 %).

**Invariant (replaces pass-1 §6 facts 2 and 5):**

- A GPU row's Contract has **two** forms, chosen by its *class*, never by its declared shape:
  - `gpu-timing` (bench/qual rows whose `decision_rule` is a GPU latency/throughput metric, or `role == bench`): holds
    `gpu-quiet:use`, `t184-191:use`, **`c72-95:quiet`** — q3 cores idle, q0-q2 free (shape `gpu-q3`).
  - `gpu-work` (everything else: correctness, builds, qualification by output, **and production serving**): holds
    `gpu-quiet:use`, `t184-191:use` **only**. q3 cores are ordinary CPU capacity; the only co-residency rule left is
    that a *CPU timing* row is not placed on c88-95 while a GPU job runs (the −9.6 % SMT channel), which the lock-set
    test in #2.4 expresses as `purpose[c88-95] = quiet-for-cpu-timing` on the *CPU* row, not on the GPU row.
- Today's `hsf5p-profile6-q3-r1` (`regions=mi210_0,88-95,184-191`, `holds=c88-95,gpu-quiet,t184-191`) and
  `kvu16g2-decstep` (`holds=gpu-quiet,t184-191`) are the two forms; the first is right only if it is a timing row, and
  the Contract decides that from its `decision_rule`, not from the owner's `regions:` string.
- SKILL.md §2 wording (supersedes the pass-1 diff's first bullet): "**A GPU timing run needs a quiet q3; a GPU work
  run needs nothing but its own threads.** `gpu-timing` holds gpu-quiet + t184-191 + c72-95 quiet. `gpu-work`
  (correctness, builds, output-qualified runs, production serving) holds gpu-quiet + t184-191 only, and q3 cores are
  scheduled normally; CPU *timing* rows alone avoid c88-95 while the GPU is busy."
- Test additions to `test_rowflow_contract.py`: `test_gpu_qual_by_output_is_gpu_work_holds_threads_only` (inf34 v16
  fixture → `holds={gpu-quiet, t184-191}`); `test_gpu_latency_rule_is_gpu_timing_holds_q3_quiet`;
  `test_cpu_timing_row_avoids_c88_95_under_gpu_work`; `test_cpu_correctness_row_placed_on_c88_95_under_gpu_work`.

## P2.9 Two more defects (INF-22 session), verified

### D9 — No deadline on a dry run; a stuck smoke holds its cores for 20 h with holder `?`

- **Verified.** `codex-ifbench-cj6a-27b-v4-20261104`: `dryrun/<id>/grants/*.grant` says `regions=0-3 start=15:29Z
  end=2026-11-04T16:04Z`; pid 3114401 (`sudo -n --preserve-env=… setpriv …`) started 2026-11-04 15:30:02 and is **still
  alive at 20 h 33 m**; `RUNNING.json` (15:30) is still present, no `FAIL-*.json`, no ALERT; a `stop` file was touched
  12:00Z today by hand. `dry_running:2967` feeds `RUNNING.json` cpus into the busy set, so c0-3 (and whole-q0 options)
  were blocked with no grant to point at. The dry-run grant's own `end=` is never enforced by anything.
- **Root cause.** The dry run's timer is the Python harness's `first_progress_s` wait (`dryrun_run:2452`); when the
  harness exits or the engine never reaches START, nothing else owns the deadline — the grant's `end=`, `RUNNING.json`
  and the child process group are three facts with no reconciler (the P2.1 pattern again). `0efbd47c8` made it
  **worse** for this case: the timer now starts at engine START, and "never reached START" is WAIT, not FAIL, so a smoke
  whose engine polls the wrong grants dir (D10) waits forever by design.
- **Fix.** `rowflow.py`: `dryrun_run` writes `deadline = start + max(first_progress_s, 300) + LOCK_WAIT_MAX_S (600)`
  into `RUNNING.json` and the dry-run grant; new keeper step in `allocate` (`reconcile_dryruns`, beside `heal_grants`)
  — for every `RUNNING.json` past `deadline`: `kill -TERM -- -<pgid>` (the pgid recorded in `RUNNING.json`; the engine
  already `setsid`s), 30 s, `-KILL`, verify with `ps -o pid= -p`, write `FAIL-n.json {reason: deadline, phase:
  pre-START|post-START}` **or** `WAIT.json` if the engine never reached START *and* its lock wait is observable, remove
  `RUNNING.json`, release the cpus the same tick, alert once. Status shows `dryrun-stale` instead of `dryrun-running`
  when `deadline` has passed and the process is gone. A WAIT is re-queued at most `SMOKE_MAX_WAITS` (3) times, then FAIL
  with `reason: never-started` — "waiting is WAIT, never FAIL" must have a ceiling.
- **Tests.** `test_rowflow_dryrun_deadline.py`: `test_running_json_carries_deadline`;
  `test_past_deadline_pre_start_kills_pgid_and_requeues_as_wait`; `test_past_deadline_post_start_is_fail`;
  `test_three_waits_then_fail_never_started`; `test_stale_running_json_without_process_is_cleared_and_cpus_freed`;
  replay invariant (P2.4 #4): no `RUNNING.json` older than `deadline + 120 s`.

### D10 — Dry-run env lost across `sudo --preserve-env`; the engine polls the MAIN grants dir

- **Verified.** `/mnt/raid0/llm/tmp/canonical-judge-suite-revamp/ifbench-v3-cj6a-20261104/launch.sh:33`:
  `exec sudo -n --preserve-env=WS58_REGIONS,FILLER_CPUS,FILLER_SMOKE,FILLER_DRYRUN,FILLER_DRYRUN_DIR,FILLER_DRYRUN_RESULT_PATH …`
  — no `FILLER_GRANTS_DIR`, `FILLER_FLAGS_DIR`, `FILLER_STATE_DIR`, `FILLER_STOPFILE`. `dryrun_run` passes
  `FILLER_GRANTS_DIR=<dryrun dir>/grants` (`rowflow.py:2465`); `filler_run15.sh:81` reads
  `GRANTS=${FILLER_GRANTS_DIR:-$FLAGS/grants}`, so the engine fell back to the main dir: `launcher.out` 15:30:03Z
  `grants=/mnt/raid0/llm/tmp/compute-flags/grants`. It polled for a grant the keeper writes into a different directory
  — forever (D9).
- **Root cause.** The dry-run contract is carried as a *set of env vars across a privilege boundary that the row author
  controls*; one omitted name silently changes the engine's world. Same pattern: a declaration (`--preserve-env` list)
  trusted, never checked against the receiver's needs.
- **Fix (three layers, all small).**
  1. `filler_run15.sh:94` — when `FILLER_DRYRUN=1`, **derive** the whole family from the one variable that did
     survive: `GRANTS=$FILLER_DRYRUN_DIR/grants`, `STATE=$FILLER_DRYRUN_DIR/state`, `FLAGS_DIR` from the dry-run dir's
     parent, and refuse (`exit 64`, `.ended rc=64 reason=dryrun-env-incomplete`) if `FILLER_DRYRUN_DIR` is unset or
     the grants dir does not exist. A dry run must never be able to read the main grants dir.
  2. `rowflow.py parse_launcher` — detect `sudo … --preserve-env=LIST` (and `env -i`, `setpriv`) wrappers; the
     Contract records `env_passthrough`; `publish` refuses when a required name
     (`FILLER_DRYRUN FILLER_DRYRUN_DIR FILLER_GRANTS_DIR FILLER_STOPFILE WS58_REGIONS FILLER_CPUS`) is missing, printing
     the corrected `--preserve-env=` line. Simplest robust form to recommend to authors: pass **one** variable
     (`FILLER_DRYRUN_DIR`) and let layer 1 derive the rest.
  3. `dryrun_run` launcher.out check — after START the harness greps `grants=` from `launcher.out` and FAILs the smoke
     immediately with `reason: wrong-grants-dir` if it is not the dry-run dir (a 5-second failure instead of a 20-hour
     hang).
- **Tests.** `test_filler_dryrun_env.py`: `test_dryrun_derives_grants_dir_from_dryrun_dir`;
  `test_dryrun_without_dryrun_dir_exits_64`; `test_rowflow_contract.py::test_sudo_preserve_env_missing_grants_dir_refused`
  (the exact `launch.sh:33` line as fixture) and `test_preserve_env_complete_admitted`;
  `test_rowflow_dryrun_deadline.py::test_wrong_grants_dir_in_launcher_out_fails_fast`.

## P2.10 D11 — `auto_file.py` cannot tell a live owner from a dead one: no join key between a row and a session

- **Verified.** `ready/npd1-step5-20261105.json`: `owner: "ws58"`, `publisher.session:
  "73998e9f-8009-47d6-bac6-2835f05c3e04"`, `handoff_task: handoffs/active/mi210-serving-program.md:NPD1-STEP5`. The
  row is in `filing-owner-less.jsonl` although its owner (the INF-22 main) was live and filed it at 11:35Z
  (`4eee3159f`). `owner_live()` (`churn/auto_file.py`) looks up the literal owner string (plus `h-`/`handoff-`
  prefixes) in three places: `handoff-sessions.json` sessions (71 slugs like `mi210-big-model-and-acceleration-roadmap`;
  no `ws58`), `session-bus/heartbeats/<owner>.json` (no `ws58.json`; the `mainA-D.json` that exist are dated
  **2026-08-13/25** — birth certificates, exactly the stale-heartbeat hazard `CLAUDE.md` warns about), and
  `outbox/<owner>.jsonl` mtime. None of the three is keyed by anything a row carries. `ws58` is a historical alias of
  the calendar-owner session; the Claude session id in `publisher.session` is written to no registry at all.
- **Root cause.** Same pattern: the row *declares* an owner string; liveness is *observed* in registries keyed by other
  names; nothing reconciles the two. The question auto_file actually needs answered is not "is the owner alive" but
  "**has anyone claimed this filing**".
- **Fix — a claim, then a mapping (in that order).**
  1. **Filing claim (authoritative, cheap).** When a session is resumed for a run end (dispatcher `end_prompt`) or an
     interactive owner reads a row alert (`rowflow.py alerts --ack`), it touches `filing-claims/<id>.json {session,
     roster_id, at}`. `auto_file.py` routes a prose-rule row to `filing-owner-less.jsonl` **only** if no claim exists
     after `OWNERLESS_AFTER_S` (1200) *and* the mapping below says no candidate owner is live; a claim older than
     `CLAIM_TTL_S` (7200) without a `.FILED` re-opens the row. `rowflow.py alerts --ack` already exists — the claim is
     a one-line side effect of acking a `row-ended` alert.
  2. **Owner → liveness mapping (`resolve_owner_sessions(row) -> set[candidate]`)** in `auto_file.py`, tried in
     order, each returning `(live, why)`:
     - `publisher.session` → `session-bus/heartbeats/by-session/<session-id>.json`: the mailbox watcher every
       publisher must arm (SKILL.md 2026-11-05 note) writes this heartbeat on every pass, so an interactive owner
       that is actually watching its rows is live by construction; `ts` fresh ≤ 1800 s **and** `state != idle`.
     - `handoff_task` → slug = basename of the handoff file without `.md` → `handoff-sessions.json[slug]`
       `status == running` and `ps -o pid=` alive (the headless-owner case; `mi210-serving-program` would resolve).
     - `owner` → roster alias → `coordination/session-bus/roster.json` (or `config.yaml` aliases) → heartbeat as
       above. A heartbeat is evidence only if fresh **and** `state ∈ {working, draining}`; an `idle` or stale one is
       "unknown", never "live" (`SESSION_LIFECYCLE.md` → three states).
     - Fallback: any session whose outbox wrote a line naming the row id within `max_age_s` is live for that row.
  3. **Publish writes the join key.** `publish()` already records `publisher.session`; add `owner_roster_id`
     (from `$EPYC_ROSTER_ID` / bus `--agent`) and refuse `owner: "?"`. A row with no resolvable owner at publish is
     routed to the standing filer *at publish time*, not discovered at filing time.
- **Tests.** `scripts/coordination/tests/test_auto_file_owner_map.py`:
  `test_claim_present_never_ownerless`; `test_publisher_session_heartbeat_working_is_live` (npd1-step5 fixture +
  `by-session/73998e9f….json {ts: now, state: working}` → live);
  `test_handoff_slug_running_pid_is_live` (`mi210-serving-program` running, pid alive → live);
  `test_roster_alias_idle_heartbeat_is_unknown_not_live` (`mainB.json` dated 2026-08-13 → not live);
  `test_stale_claim_without_filed_reopens`; `test_owner_question_mark_refused_at_publish`;
  regression: npd1-step5 at 11:35Z with the owner's heartbeat fresh → **not** in `filing-owner-less.jsonl`.

## P2.11 D12 — Two filing paths that do not reconcile: the handoff tick and the `.FILED` record

- **Verified.** `4eee3159f` ("mi210-serving: NPD1-STEP5 V11_ITEM_STANDS …") ticked `handoffs/active/mi210-serving-program.md`
  and the master index at ~11:35Z; `filing-done/` has **0** files for `npd1-step5-20261105`; `filing-owner-less.jsonl`
  has 1 entry for it. The watcher, the alarm and `auto_file.py` all key on `filing-done/<id>.FILED`, so a row filed
  the way `SESSION_LIFECYCLE.md` tells an owner to file (tick + evidence + commit) is "unfiled" forever to the machine,
  and every automation downstream (alarm, standing filer, reaper's "superseded+filed" skip, dashboard) is wrong about it.
- **Root cause.** The filing *record* (`.verdict.json` + `.FILED`, schema `epyc.filed.verdict.v1`) and the filing
  *act the owner performs* (a committed checkbox tick with `[belief: …]`) were designed separately; `file_result.py`
  writes the record and *optionally* flips the box, but flipping the box never writes the record. Two writers, one
  fact, no reconciler — the P2.1 pattern applied to filing.
- **Fix — one sanctioned path, plus a reconciler for the transition.**
  1. **The sanctioned path is `file_result.py`, and it is the only thing that ticks a row's box.** An owner files by
     `file_result.py <id> --verdict-json V` (or the auto path); `file_result.py` writes `.verdict.json`, `.FILED`,
     flips the checkbox via `flip_checkbox` and stages the handoff edit — the owner then commits. Direct editing of a
     row's checkbox is a lint failure: `scripts/hooks/` pre-commit (`commit_hygiene`) refuses a diff that flips a
     checkbox whose task text cites a row id (`[a-z0-9-]+-2026[01][0-9][0-3][0-9](-r[0-9]+|-v[0-9]+)?` or a
     `FILLERS:`/`ready/` reference) when no `filing-done/<id>.FILED` exists, printing the `file_result.py` command.
     `SESSION_LIFECYCLE.md` → *Two axioms* gets one sentence: "a compute row's tick goes through `file_result.py`".
  2. **Reconciler (`filing_watch`/keeper step 7): recognise a committed result tick.** For each due row without
     `.FILED`: `git -C <repo> log origin/main --since=<grant start> -S<row-id> --format=%H -- <handoff_task file>`;
     if a commit flips the row's box (the diff adds `- [x]` on a line containing the row id or its handoff token), write
     `filing-done/<id>.verdict.json {outcome_class: SCIENCE-VERDICT|PARTIAL-VERDICT (from the tick's
     pass/fail/inconclusive word), filed_by: "handoff-commit:<sha>", rationale: <commit subject>}` and `.FILED`. This
     closes npd1-step5 today and every historical row filed by commit, and it stays as the backstop after step 1.
  3. **One query, one answer.** `rowflow.py status <id>` reports `filed_by` from the record; the dashboard, alarm,
     reaper and auto_file read only that. `filing-due.jsonl` becomes a derived view (P2.4 #5).
- **Tests.** `scripts/coordination/tests/test_filing_reconcile.py`:
  `test_committed_tick_citing_row_id_writes_filed_record` (fixture repo: one commit flipping `NPD1-STEP5` box →
  `.verdict.json filed_by handoff-commit:<sha>`, `.FILED` present, row leaves `filing-due`);
  `test_tick_without_row_id_does_not_file`; `test_file_result_flip_and_record_are_atomic` (either both or neither);
  `tests/hooks/test_commit_hygiene_row_tick.py::test_checkbox_flip_citing_row_without_filed_is_refused` and
  `::test_flip_after_file_result_admitted`; regression: today's `4eee3159f` + `grants/npd1-step5-20261105.ended` →
  reconciler files it, `auto_file.py` no longer lists it owner-less.

## P2.12 D13 — The filler's grant-WAIT loop ignores the STOP file (current `filler_run15.sh` too)

- **Verified.** `dryrun/codex-ifbench-cj6a-27b-v4-20261104/stop` was touched at 12:00Z — the exact path the engine
  logged as `stop=` at 15:30:03Z yesterday. Engine pid 3114437 (pre-`2134ef303` script) kept `sleep 5`-looping on the
  main grants dir for 6+ minutes afterwards. **The current script has the same gap**: the main loop on `origin/main`
  (`filler_run15.sh` ~L408-425) is
  `while :; do … if [ ! -e "$GRANT" ]; then sleep_poll "$POLL"; continue; fi …` — `$STOPFILE` is read only in
  `run_one` at grant time (`:285`, `stopped-before-start`) and mid-run (`:362-364`). A poller with no grant never
  reaches either. So STOP has three phases and two are covered: *mid-run* (`2134ef303`), *at grant* (`62bcc3eb5` +
  `2134ef303`), **not *waiting***. Every armed-but-never-granted poller (and every withdrawn ARMED row, P2.3 #2) is
  therefore un-stoppable except by pid.
- **Fix.** `filler_run15.sh` main loop: before the grant test,
  `if [ -e "$STOPFILE" ]; then write_ended 75 stopped-while-waiting; log "STOP seen while waiting for a grant ($STOPFILE): releasing claim, exiting"; release_claim; exit 21; fi`
  — `release_claim` removes any `.grant` addressed to this id that has not been consumed (so the keeper sees a terminal
  `.ended` and never re-grants; this is the record F4 lacked) and, in a dry run, removes `RUNNING.json` so the keeper
  frees the cpus the same tick (D9). Poll interval for the STOP check is `$POLL` (5 s); no grace is needed because no
  job is running. `rowflow.py withdraw` and `supersede` then stop an ARMED predecessor in ≤ 5 s instead of leaving its
  poller alive forever.
- **Tests.** `test_filler_stop_midrun.py::test_stop_while_waiting_for_grant_exits_21_and_writes_ended`
  (start the engine with no grant, touch STOP, assert exit within 2 polls, `.ended rc=75 reason=stopped-while-waiting`,
  no `.grant` left); `::test_stop_while_waiting_in_dryrun_removes_running_json`;
  `test_rowflow_supersede.py::test_withdraw_armed_row_stops_its_poller` (poller pid gone within 10 s).

## P2.13 D14 — The new GPU-shape publish check (`8fbe18182`, 12:06Z) refuses legitimate whole-host CPU serving; and fixed-core sub-quarter rows

- **Verified.** `8fbe18182` adds `gpu_lane_overreach()` (`rowflow.py:1657`): a row is GPU-lane if `lane == gpu` **or**
  `mi210` in regions **or** launcher `--class gpu|cpu+gpu`; cpus beyond q3+siblings are refused unless
  `whole_host_evidence()` (`:1564`: `declared_threads ≥ 48`, `baseline_ref`, or `shape_override`). A dry run reports
  27 live rows refused, including `npd1-step2..5`. `npd1-step5` is legitimate whole-host CPU serving: `--class cpu+gpu
  --gpu-quiet exclusive --claim-cpus 0-95 --role bench`, job `taskset -c 0-95 numactl --interleave=all llama-server …
  -t THREADS` (`job.py:43,157`). Its manifest has `declared_threads: null`, `baseline_ref: null` — because **the thread
  count is a Python variable (`"-t", THREADS`), not a literal**, so `parse_launcher`'s argv extraction cannot see 48.
  The check is wrong on two counts:
  1. **Lane is decided by `--class`, not by GPU *use*.** `cpu+gpu` with `--gpu-quiet exclusive` and a 0-95 claim is a
     CPU timing row that needs the GPU *quiet* (purpose `gpu-quiet: quiet`, `q0-q3: use`); it is not GPU work and q3
     is not its "overreach". `c61a7430e` (11:49) already introduced the right signal — `gpu_use: "quiet-only"` (rows
     that skip the VRAM residency check). **Exact condition:** in `gpu_lane_overreach`, return `set()` when
     `row.get("gpu_use") == "quiet-only"` or (`o.get("gpu_quiet") == "exclusive"` and `o.get("class") == "cpu+gpu"`
     and the smoke's `PASS.json vram_used_max_bytes < 1 GiB`); i.e. `lane = gpu` iff the row *uses* the GPU. Then
     `npd1-step*` fall under the ordinary host/quiet-host evidence gate of `71d92b3e9`, which is where they belong.
  2. **Evidence is read from a literal argv only.** `whole_host_evidence` must accept **measured** evidence:
     `max(declared_threads, PASS.json measured_threads) ≥ 48` — the smoke ran the server with `THREADS` and measured
     it. And a `--check`/dry-run sweep over *existing* rows must evaluate against the stored `PASS.json`, never refuse a
     row whose smoke already measured ≥ 48 threads, and never retro-refuse a row published before the field existed
     (`declared_threads` absent ≠ `0`; today `int(None or 0)` makes absence a refusal).
  3. Fallback for variables: when `-t`/`--threads` is followed by an identifier, resolve a single `NAME = "<int>"` /
     `NAME = <int>` assignment in the job file (same idiom `resolve_stop_path` uses for `D=`); otherwise record
     `declared_threads: unknown` and defer to measurement.
- **Tests.** `test_rowflow_shape_evidence.py::test_cpu_plus_gpu_quiet_exclusive_is_not_gpu_lane` (npd1-step5
  launcher fixture → `gpu_lane_overreach == set()`); `::test_measured_threads_48_is_whole_host_evidence`
  (`declared None`, `PASS.json measured_threads 48` → admitted); `::test_absent_declared_threads_is_unknown_not_zero`;
  `::test_python_variable_threads_resolved_from_job_file` (`THREADS = "48"` → 48);
  `::test_check_sweep_over_live_rows_refuses_zero_of_npd1_rows` (fixture: the four npd1 manifests + PASS.json).

- **kpf30-sq3 pinned to fixed cores.** `ready/kpf30-impact-8952-20261104-r9-sq3.json`: `regions: 72-73`, `shape:
  quarter`. A sub-quarter row that names *specific* cores can be placed only when exactly those two are free, so it
  RANK-SKIPs (3× today) while c74-c75/c78-c79/c84-c87 sat free. The Contract (#2) should express sub-quarter width,
  not identity: `regions: any-2-of q3` (or `width: 2, within: q3`), and `grant_regions` picks the free pair and writes
  the concrete list into the grant (it already does this for `any-cpu-quarter` → `cpu_list(q)`). Publishing a concrete
  sub-quarter list stays allowed only with `pin_cores: true` and a reason (NUMA/L3 experiments).
  Test: `test_rowflow_contract.py::test_any_2_of_q3_places_on_free_pair` (free `c74,c75` → grant `74-75`);
  `::test_concrete_pair_without_pin_reason_rewritten_to_width`.


---
---

# Pass 3 — simplification audit (2026-11-05, 16:00Z)

**Operator order:** "review/audit the pipeline for overcomplications." Read-only against the live system; code read
from `origin/main` (`eae8228a3`, two commits past `75e930e05`), keeper log 12:00–15:57Z. Pass 1 and 2 argued for
*adding* a Contract and a reconciler. Pass 3 says the opposite half out loud: **most of what exists must be deleted
first**, because the last six hours prove that adding rules to this allocator produces regressions faster than it
removes defects.

## P3.1 The six-hour experiment, measured

| | 10:00Z | 12:00Z (pass 2) | 16:00Z (now) |
|---|---|---|---|
| `rowflow.py` lines | 3,395 | 3,395 | **4,088** (+693) |
| top-level defs / tunables | 155 / 52 | 155 / 52 | **189 / 62** (85 with `_`-prefixed) |
| commits to `rowflow.py` today | 11 | 11 | **19** (66 in 5 days) |
| redeploys of `rowflow.py` since 12:00 | — | — | **7** (12:06, 12:44, 14:09, 14:28, 14:48, 15:09, 15:15); 17 `.bak-*` today |
| ways a row's width is stated | 4 | 4 | **5** (`regions`, `shape`, launcher `-t`, `shape_override`, + `contract_of`) |
| spec keys `publish()` reads / fields it derives | — | — | **35 / 13** (manifests carry 44 keys) |
| new keeper log tags since 12:00 | — | — | `WAIT`, `NO-DRAIN`, `DRYRUN-REAP`, `DRYRUN-DEADLINE`; gone: `DRAIN-HELD`, `IDLE-VIOLATION`, `UNDERUSED` |
| idle 12:00–15:57 | — | — | **~6.9 quarter-hours + ~2.0 gpu-quiet-hours** (vs 0.8 + 0.94 in 10:40–11:57) |
| `SMOKE-WAIT` lines | 2 (whole morning) | — | **117** ("no 4 free cores outside the whole quarters 3 queued row(s) need" ×112) |

Idle **went up** after the machinery meant to reduce it. The regressions are verified in P3.2; every one of them is
caused by code that did not exist at noon.

## P3.2 Today's self-inflicted regressions — verified

| Regression | Evidence | Cause (file:line on `eae8228a3`; `pre:` = `75e930e05`) | Status |
|---|---|---|---|
| **Every multi-core CPU row shrunk to 4 cores**, including explicit `regions: q2` + `shape_override: "operator: … needs one whole quarter"` | `iqk-q8-prefill-ab-r3`: `ARMED.json regions=q2`, `GRANTED.json regions=80-83,176-179`; keeper wrote **two GRANT lines for the same pid 242433** at 15:51:06Z (72-75 and 80-83, `claim_regions=q3`, manifest said q2); `-ab`, `-ab-r2`, `-step0` same; `inf75 census r2` offered 4 cores against a declared 2-quarter claim (`refuse rc=13 … missing q2`); yarn v38 ×2 and STT5 r5 shrunk at *publish* (`declared_threads=1` → `sub-quarter`). 8 GRANTs on 7 rows. **No `SHAPE-DOWNSIZE` line was ever logged** | `contract_of` `pre:1547-1640`: `row_threads` = max(declared, **PASS.json measured_threads**) — a 4-core smoke measuring 2.2 threads became "threads 2"; `pre:1598` `pinned` is true only for *concrete* cpu lists, so `q2` is not pinned; `pre:1603` `threads <= SUB_CORES → "sub-quarter", _sub_blocks()` enumerates 4-core blocks of **all** quarters, ignoring `regions`; `shape_override` feeds only `evidence` (`pre:1573`), which only decides `whole` | `eae8228a3` drops measured_threads and adds a `declared_shape` floor; **still open**: `q2` regions still non-pinned (`:1679`), `shape_override` still reaches only `evidence` (`:1654,1659`) — an override on a < 24-thread row without `spec.shape` still shrinks |
| **CPU-declared rows given `gpu-quiet`**, GPU idle behind them | STT5 r5 GRANT 15:30:49 `holds=c72-75,gpu-quiet,…` (`lclass=cpu`), held 12.7 min at 0 %; also `iqk-q8-prefill-build` 15:14, `-step0` 15:30; at 15:43:41 **eight** EXCLUSIVE GPU rows logged `WAIT … device quiet 1/2 samples` | `pre:1579` `gpu_tok = {GPU} if (gpu_row or gq=="exclusive" or gpu_touch(d,o))`; `gpu_touch` → `_kfd_capable` regex `_KFD` (`:1508`) matches the string `build-hip` in job text → whisper-cli path → token added to every CPU option (`pre:1633`) | `eae8228a3` adds `cpu_declared()`; the regex inference remains |
| **Rank-100 quiet-host row drains the host over higher-ranked GPU rows** | In-window only `c6-port35186-remeasure` `DRAIN (quiet-host) until 2026-11-06T07:14Z` ×4 ticks (15.6 h horizon = STT5 r5's own end; its ready manifest is gone so rank is unverifiable). GPU rows' actual wait was on gpu-quiet (row above). **Partial** | `plan()` `:2078-2092`: `plan_order:1934` keys on `min(rank, URGENT_RANK)` so every rank ≥ 10 **ties**, then `lane_count` puts the starved CPU lane first; `:2080` promotes *any* quiet-host row regardless of age; `drain_blocker:1947-1958` keeps only better-ranked rows **placeable this tick**, and EXCLUSIVE GPU rows are removed from `cands` by the quiet gate (`:3645`) → no blocker → `T = max(grant ends)`; quiet-host options reserve `gpu-quiet` idle until T | **unfixed** |
| **GPU-blocked whole-quarter rows reserve quarters, starving smokes** | 117 `SMOKE-WAIT`, 112 of them the reservation template; yarn v38 ×2, STT5 r5, iqk build waited 14:30–15:14 | `whole_quarter_reservation` (fdb7348fe) reserved for any queued whole row | `75e930e05`: reserve only for rows placeable now |
| **Smoke that wrote outputs marked COMPLETE** | `c6-features-cpu`: SMOKE-PLACE 13:26:24 → PASS 13:26:30 → GRANT 13:26:34 → `.complete` 13:27:02 (28 s into a 1,200 s window); `c6-kp1-longctx` same; 26 `.complete` since 12:00 | `publish_row.file_if_complete` (`:399-430`) → `smoke_completion_check`; the smoke runs the real job, the job writes its summary, `--complete-cmd` sees it | in flight |
| **2-sample GPU-quiet check delays every GPU grant** | `WAIT` tag born 14:15:05; 52 `device quiet 1/2 samples`; median WAIT→GRANT 101 s (one tick); 9 GPU grants before 14:15 had zero WAIT | `GPU_QUIET_SAMPLES=2` (`:3761`), one sample per 120 s tick (`gpu_quiet_gate:3800`) | by design; costs ~2 min × every GPU grant |
| **`file_result` prints TICK lines it never writes** | `grep -c TICK filing-watch.log` → **0 ever** in 4,048 lines; three sampled boxes were ticked **by hand** (`f0d4879a2`, `92be684d9`, `987c99809`) | `file_result.py:264,280` unreachable from the auto path | **unfixed**; the D12 two-paths defect in practice |
| **The replay gate passed all of these** | `DEPLOYED.json` gate "unit+replay PASS" at 15:09 | see P3.6 | — |

## P3.3 Where it is overcomplicated — the diagnosis in one sentence

**The keeper tries to *infer* what a row needs from five partial declarations plus regexes over job text, and then
tries to *optimise* placement (drains, reservations, coexist, packing, smoke-as-filler) on top of those guesses.**
Inference is where every regression today was born (`measured_threads` → shrink; `_KFD` regex → gpu-quiet on a CPU
row; `min(rank,10)` → rank ties → wrong drain). Optimisation is where the guesses turn into idle hours (reservations
starving smokes, quiet-host drains holding the GPU, 2-sample waits). Neither is needed for the actual workload: ~40
grants/day on 5 bins. A 5-bin, 40-item/day scheduler does not need a planner; it needs a correct *admission* test and
a correct *release*.

### Mechanism inventory and verdict

| Mechanism (fns / lines / tunables) | Verdict | Why |
|---|---|---|
| launcher parsing + declared-threads inference (7 / 210) | **DELETE inference; keep arg parsing for `--class/--stop/--claim-cpus`** | the owner states threads; `_scan_threads`, `_job_chain`, Python-list argv scanning, `OMP` heuristics all guess |
| shape derivation `contract_of`/`shape_of`/`row_threads`/`_sub_blocks` (8 / 147 / 10) | **DELETE** | shape = declared cpus; there is nothing to derive once `cpus` is a required field |
| evidence gates `gpu_touch`/`_kfd_capable`/`gpu_lane_overreach`/`gpu_timing_row`/`check_engine_not_sealed`/vacuous-GPU test (15 / 171) | **DELETE all but one** | replaced by one admission test + measured-busy feedback (P3.5); the engine-seal check is on the wrong side (pass 2); the vacuous-test scanner is a job-correctness concern, not the scheduler's |
| coexist (`COEXIST_Q3`, `coexist_holds`, logic inside `contract_of`/`_avail`) | **DELETE** | with `quiet:` a per-row boolean and tokens per core, "coexist" is just two rows whose token sets do not intersect |
| drains + `rank_reservation` + `own_block` + `drain_blocker` + `URGENT_RANK` + `DRAIN_*` ×5 (11 / 260 / 6) | **DELETE drains; replace with one rule** | *strict priority with a hold*: the top-ranked runnable row that does not fit **holds** the bins it needs as they free (no backfill into them longer than its own ETA); nothing else. No promotion, no ties, no `min(rank,10)` |
| packing / `whole_quarter_reservation` / `_avail` / smoke-as-filler `place_smokes` (11 / 211) | **DELETE** | smokes run on a **fixed, permanent 4-core smoke lane** (c20-23 + siblings, never granted to rows); no reservation logic at all. Cost: 4 of 96 cores. Benefit: 117 SMOKE-WAITs → 0 and 200 lines gone |
| GPU fence (env + LD_PRELOAD shim) + `GPU-FENCE-BREACH` + vacuous detection (11 / 172) | **KEEP the fence, DELETE the inference around it** | the fence is the one *enforcement* added today — a CPU row cannot touch the GPU, by construction. That is the model: enforce, don't infer. The `gpu_fence_override` and job-text scanning go |
| 2-sample `gpu_quiet_gate` | **REPLACE** with the KFD process count (already measured for the fence): `gpu free ⇔ no KFD pid outside token grants`. Zero wait |
| dry-run harness (12 / 421) | **SHRINK** to: run the job on the smoke lane with a deadline; PASS = first progress; FAIL otherwise; never COMPLETE (a smoke's outputs are discarded — `scratch_root/smoke/`) |
| supersede/withdraw/lineage (7 / 99) | **KEEP**, simplify: withdraw = STOP + `.ended`; lineage counts FAILs since `fix_ref` only |
| heal / idle_held / underused / alerts (7 / 150) | **COLLAPSE** into one `reconcile()`: measured vs held per token; release `use` holds idle 2 samples; alert once; fix the missing `alarm_channel.py` |
| host_snapshot / measurement (14 / 179) | **KEEP** — this is the only ground truth |
| status / CLI / util | KEEP |
| `publish()` 213-line function reading 35 keys | **REPLACE** with a 12-key schema + `jsonschema` validation |

Outside `rowflow.py`: **delete** FILLERS.md as a read source (7 readers → `rowflow.py status --json`), `filing-due.jsonl`,
the dashboard's `_rows` derivation, `filing_watch.sh` (folded into the keeper tick), `scratch_cleanup.py`'s overlap with
the keeper reaper, keeper `v2…v11` copies, 17 `.bak` copies in `bin/`, `grant_ok_launcher.py`, `run_direct.sh`
(duplicate of `publish_row --run-smoke`), `ws58-calendar-keeper-v11.sh`.

## P3.4 The minimal model

**Resources are tokens.** `c0..c95` (cores; siblings follow their core, never separate tokens), `gpu` (the MI210 with
184-191 — the host threads are part of the GPU token, not CPU tokens), `ram` (GiB, counted), `disk` (GiB, counted).
That is the whole bin set: 96 + 1 + 2 counters. No `qN` tokens (a quarter is a 24-core *shorthand* in the spec, expanded
at publish), no `t`-tokens, no `gpu-quiet` token.

**A row declares what it needs** (the schema, complete):

```json
{ "id": "…", "owner": "…", "handoff_task": "handoffs/active/x.md:ROW",
  "launcher": "/abs/launch.sh", "stop_file": "/abs/STOP",
  "cpus": 24 | "48-71" | "q2" | "any-quarter" | "any-2-of-q3",
  "threads": 24,
  "gpu": "none" | "shared" | "exclusive",
  "quiet": false | true,
  "ram_gib": 48, "disk_gib": 20, "estimate_s": 3600, "min_window_s": 1800,
  "decision_rule": "rc == 0 and …", "priority_rank": 50 }
```

Twelve fields; five are new or renamed (`cpus`, `threads`, `gpu`, `quiet`, `disk_gib`); the rest exist. **No
`shape`, no `regions`+`claim_cpus`, no `busy_fraction`, no `lane`, no `class`, no `gpu_use`, no `timing`, no
`admission_class`, no `baseline_ref`, no `shape_override`, no `coexist_*`, no `declared_threads`.**

Semantics, each one line: `cpus` is the set the job may run on (the filler `taskset`s exactly it); `threads ≤ |cpus|`
or publish refuses; `gpu: exclusive` = no other GPU row at the same time, `shared` = any number, `none` = fenced off
(the LD_PRELOAD fence is the enforcement); `quiet: true` = no other row anywhere on the host while it runs (the
*only* way to get a quiet host, and it needs `priority_rank < 10` or an operator string in `quiet_reason`); a `quiet`
row with `gpu: none` still takes the `gpu` token (quiet means quiet).

**A grant is the row's declaration stamped with a window**: `{id, cpus, gpu, ram_gib, start, end}`. Nothing is
"derived" into it. `holds=` disappears: the grant *is* the holds.

**The keeper does three things per tick, in order**, ~300 lines total:

1. **reconcile()** — for every open grant: measured busy per core (`/proc/stat`), KFD pids, VRAM. A `gpu: exclusive`
   grant with no KFD pid of its own tree for 2 samples → `gpu` released (the row keeps running; CPU post-processing
   continues on its cores). A core at 0 % for 2 samples under a non-`quiet` grant → released. A grant past
   `1.5 × estimate_s` → alert once. A dry run past its deadline → killed by pgid, cores released. Dead poller →
   grant removed. (This replaces `heal_grants`, `idle_held`, `underused`, `reconcile_dryruns`, `gpu_quiet_gate`.)
2. **admit()** — walk rows by `priority_rank` (ties by publish time). For the first row that *does not fit*, mark its
   needed tokens **held-for** it (no new grant longer than `now + its ETA` may take them). For every row that fits the
   remaining free tokens → grant. That is the whole planner. Smokes are not in this loop: they run on the fixed smoke
   lane, FIFO, one at a time, with a deadline.
3. **file()** — for every `.ended` without `.FILED`: machine `decision_rule` → file; else claim/route (pass 2 D11/D12).

**Where the old mechanisms went:** drains → the hold in step 2; coexist → disjoint token sets; gpu-q3 → `gpu:
exclusive` on a row whose `cpus` names q3's cores or not (the owner says); quiet-host → `quiet: true`; busy_fraction
→ measured in step 1; over-declaration → refused at publish when `threads > |cpus|`, and corrected after the fact by
`reconcile()` releasing idle cores plus one `OVER-DECLARED <id> declared 24 measured 1` line that becomes the row's
next-version lint. **The keeper never guesses a row's footprint; it validates the declaration and releases what is
not used.**

## P3.5 "Refuse over-declaration via feedback, not inference"

Publish-time checks (all O(1), no job-text scanning): `threads ≤ |cpus|`; `|cpus| ≥ 24` requires `threads ≥ 12`;
`quiet` requires `priority_rank < 10` or `quiet_reason`; `gpu: exclusive` requires `estimate_s ≤ 7200` or
`quiet_reason`; `stop_file` absolute; `launcher` exists and its `--stop` equals `stop_file`; `decision_rule` parses or
`owner` resolves (D11). That is the complete admission test — seven lines.

Run-time feedback (the only "evidence"): after each run, `reconcile()` writes `measured: {threads_p95, busy_p95,
gpu_used, ram_peak}` into the `.ended`. `publish` of a successor (`-rN`, `supersedes`) **refuses** when the predecessor
measured `busy_p95 < 0.25` of its declared `cpus` and the successor declares the same or more — unless the spec
carries `measured_ack: "<who>: <why>"`. Over-declaration therefore costs the owner one refused republish, with the
numbers printed, instead of costing the host a quarter for two hours. Nothing is inferred from argv, `OMP`, Python
lists, or `build-hip` strings ever again.

## P3.6 Why the replay gate passed everything — and how to make it catch the class

The gate (`deploy_rowflow.sh` → `tests/replay/test_replay_gate.py`, harness `replay_lib.run_replay`) replays **314
reconstructed ticks (00:00–12:32Z) through `rf.allocate()` only**, with `admit`/`arm_one`/`gpu_occupancy`/`rl_status`
stubbed. Its eleven invariants (`INV-NO-CRASH, STOP, REGRANT, 1THREAD, EVIDENCE, GPU-TIMING-Q3, LOCKSET,
DRYRUN-DEADLINE, DEADPID-RELEASE, IDLE-NAMED, IDLE-WHY-ALL`; only four day-blocking) are all **upper bounds on
width** written from the *morning's* defects. Specifically:

| Regression | Gap |
|---|---|
| 4-core shrink | no invariant says *granted ⊇ declared* (every invariant bounds from above); fixture has no row with quarter regions + small threads and no `measured_threads` in `pass` blobs |
| CPU row holds gpu-quiet | no invariant says *holds ⊆ declared tokens*; fixture `files` empty so `_kfd_capable` never fires |
| rank-100 drain | no priority invariant at all; `DRAIN`/`RANK-*` lines are captured and never asserted |
| reservation starving smokes | smokes are not candidates; no smoke invariant |
| smoke marked COMPLETE | `publish_row.file_if_complete` and the filler stop path are not executed in replay |
| 2-min GPU delay | the wait emits a *named* IDLE-WHY, so IDLE invariants pass; `idle_gpu_hours` is printed, not gated |

**Fix the design, not the list.** Three changes:

1. **Invariants are a two-sided contract between declaration and grant, stated once:** (i) `grant.cpus == row.cpus`
   when `row.cpus` is concrete, `|grant.cpus| == width(row.cpus)` and `⊆ allowed` when it is a class
   (`any-quarter`, `any-2-of-q3`); (ii) `grant.gpu == row.gpu`; (iii) no two open grants share a token; (iv) for any
   tick, if a row of rank r is granted while a row of rank < r that fit the same tokens was pending ≥ 1 tick → fail;
   (v) `idle_token_hours ≤ budget` (gated, not printed: 0.5 q-h and 0.25 gpu-h per replayed day); (vi) every
   `.ended` has a reason from the closed set and every COMPLETE came from a *grant*, never from a smoke. Six
   invariants, all **properties of the (spec, grant) pair**, none of them a transcription of yesterday's bug.
2. **Fixture = generated, not reconstructed.** A property-based generator (`hypothesis`) emits random specs over the
   12-field schema (including explicit regions + 1 thread, `quiet` with low rank, `gpu: none` rows whose job text says
   `build-hip`, 8 rows per tick) and random measured-use traces; each day's real trace is *added* as one more case,
   never the only one. Today's fixture had 0 `shape_override`, 8 `declared_threads` (all 1), 0 `kfd` ticks — it
   could not express the inputs that broke.
3. **Replay the whole tick, not `allocate()`:** `reconcile → admit → file` plus `publish_row` for every new row and a
   fake filler that writes `.ended`/`.complete` — so filing and completion are inside the gate.

## P3.7 Size and migration

**Target `rowflow.py`: ~900 lines** (util 130, token algebra 60, schema+publish 120, reconcile 120, admit 80, smoke
lane 80, file 60, supersede 60, status/CLI 120, measurement 70) — from 4,088. Tunables: 8 (`SMOKE_CORES`,
`IDLE_SAMPLES=2`, `IDLE_PCT`, `SMOKE_DEADLINE_S`, `OVERRUN_FACTOR=1.5`, `QUIET_MAX_RANK=10`, `FILE_OWNERLESS_S`,
`CLAIM_TTL_S`) — from 62. `filler_run15.sh` → ~350 lines (keep: grant consume, taskset, fence, STOP in all three phases,
`.ended` writing; drop: class/region parsing, `--gpu-quiet`, `--claim-cpus`, `--role`, FILLERS.md lookups).
`publish_row.py` → ~200.

**Migration (one week, no big-bang):**

1. *Day 0 (today):* freeze `rowflow.py` — no new rules; only P3.2's two open items (`q2` pinned; override honoured) as
   the last hotfix. Switch deploys to require the six two-sided invariants (P3.6.1) on the existing replay; they will
   fail on current code — mark them `xfail` with the issue, so the gate at least *reports*.
2. *Day 1:* add `cpus/threads/gpu/quiet` to the schema; `publish` fills them **from the existing fields** for old rows
   (`regions`→`cpus`, `declared_threads`→`threads`, `gpu_quiet exclusive`→`gpu: exclusive` + `quiet: true`, class
   gpu→`gpu: exclusive`, else `none`) and refuses *new* rows that omit them. Every manifest now carries both forms.
3. *Day 2–3:* write `rowflow2.py` (reconcile/admit/file over the new fields, fixed smoke lane) beside the old one;
   run it in **shadow** on the live snapshot each tick, logging `SHADOW-GRANT` lines; the replay gate runs both.
   Differences are the review list.
4. *Day 4:* cut over (one deploy, grants in flight honoured by both because the grant format is the same minus
   `holds=`); delete the mechanisms in P3.3 in one commit; delete FILLERS.md readers, `filing-due.jsonl`, the dashboard
   derivation, 17 `.bak`, keeper v2…v11.
5. *Day 5–7:* owners re-publish rows that fail the new admission (the refusal prints the corrected spec); measured
   `OVER-DECLARED` lines from the first days feed the republish lint.

## P3.8 Stop doing — for every agent operating this pipeline, this session included

1. **Stop adding a rule per incident.** If a fix is an `if` on a row attribute inside `plan()`/`contract_of`, it is
   the wrong fix. Today: 19 commits, 7 deploys, +693 lines, idle up 8×.
2. **Stop inferring.** No regex over job text (`_KFD`, `build-hip`), no Python-list argv scanning, no `OMP` heuristics,
   no `measured_threads` from a 4-core smoke feeding a width decision. Owners declare; the keeper validates and
   measures.
3. **Stop deploying under live grants** and more than once per day. Seven redeploys in four hours produced the engine-
   seal incident class and made every regression impossible to attribute from the log.
4. **Stop writing invariants that transcribe yesterday's bug.** Write properties of `(spec, grant)`; generate inputs.
5. **Stop treating the replay gate's PASS as evidence** until it replays the whole tick with generated fixtures and
   gates idle hours. Today it passed seven regressions.
6. **Stop filing by hand-editing checkboxes** and stop printing TICK lines nothing writes. One path: `file_result.py`.
7. **Stop publishing `shape:`/`regions:`+`claim_cpus`/`busy_fraction`/`shape_override` combinations** and asking the
   keeper to reconcile them. One row = one `cpus`, one `threads`, one `gpu`, one `quiet`.
8. **Stop running smokes as fillers in the production bins.** A fixed 4-core smoke lane costs 4 % of the host and
   deletes 200 lines plus 117 SMOKE-WAITs a day.
9. **Stop reporting "fixed" without the keeper log showing the symptom gone for one full cycle** (this report's own
   standard: every claim above carries a timestamp or a line number).
10. **Stop this report growing.** Pass 3 is the last pass that adds analysis; the next artefact is `rowflow2.py` in
    shadow mode and a one-page diff of SHADOW-GRANT vs GRANT.
