# AutoKernel waste audit — 2026-11-24 11:00Z to 2026-11-25 11:30Z

**Owner:** pipeline-mgmt · **Scope:** read-only audit of the autokernel-owned rows on the shared calendar for 24.5 h,
with deterministic (pipeline-enforced) remediations. Operator question: *"Is it really so hard to make processes more
robust to this waste?"* Answer: no — every item below is a refusal or an alert the keeper / `publish_row.py` can
emit from data it already has. None of the eight remediations depends on an agent remembering anything.

Sources (all under `/mnt/raid0/llm/tmp/compute-flags/`): `ws58-calendar-keeper.log` (10,259 lines in window,
648 keeper ticks, median tick gap 161 s), `rowflow-alerts.jsonl` (402 alerts in window), `dryrun/*/FAIL-*.json`
(33) and `PASS.json` (152), `grants/*.ended` + `.autorequeue/*.ended` (205 ends), `filing-done/*.verdict.json`
(138 filed), row dirs `/mnt/raid0/llm/tmp/ak-*`, and `git log origin/main --since='2026-11-24 11:00'`.
Extraction scripts: `audit.py`, `verdicts2.py` in the pipeline-mgmt scratchpad (not committed; the numbers below
are reproducible from the files named).

## 1. Waste, quantified

Units: **GPU-h** = MI210 hours; **CPU-Qh** = quarter-hours (one 24-core NUMA quarter for one hour; a q0+q1+q2
host grant counts 3 Qh per hour). *Measured* = summed from `.ended` / `FAIL` / `PASS` records. *Estimated* =
keeper ticks × 2.2 min (the mean tick gap, 134 s), or stated otherwise.

| Rank | Category | Count | GPU-h | CPU-Qh | Example rows | Basis |
|---|---|---|---|---|---|---|
| 1 | **(d) Compute idle while rows were queued** | GPU 36 gaps ≥2 min; CPU 542 IDLE-WHY ticks on q0–q2 | **4.6** (2.4 smoke-held, 0.75 quiet-sampling, 0.3 host-core foreign load, ~1.2 grant-boundary latency) | **36.1** idle of 73.5 available (7.5 empty queue; ~9 quiet-host policy waits; ~1.1 drain/needs-q3; 0.6 keeper IDLE-VIOLATION; rest held-but-idle grants and boundaries) | GPU 20:22→20:53 "held by smoke … until 20:28" then "device quiet 1/2 samples"; cdr-a3b-q4kv-32k-cpu 16:09–16:18 "fits but was not placed" ×7 ticks | GPU: union of grant+smoke intervals vs window (measured). CPU: granted Qh 37.4 of 73.5 (measured); cause split from IDLE-WHY tick counts (estimated) |
| 2 | **(c) STOPped / preempted rows' lost partial work** (non-resumable, `complete:false`, no RESULT) | GPU 7 ends, CPU 7 ends | **4.2** | **4.7** | c21-gpu27b-identity-r2 (owner STOP after 10,740 s, 2.98 GPU-h; r3 redesigned and rerun from zero), ak-opperf-cal-27b r2+r3 (2,453+283 s, no RESULT), ak-27b-served-kvtype-screen-r4 (761 s, no RESULT), ak-27b-served-ub-arrival-sweep r1+r2 (201+~540 s, stopped twice for a smoke that failed in 28 s); CPU: c21-fold-cpu r2+r3 (1,457+2,796 s × 3 quarters at 3–4 % busy, IDLE-HELD alert unacked 31 min), ak-specpit1 ×4 stops (2,381 s), tf1 canary (1,586 s) | measured from `.ended` started/time |
| 3 | **(a) Failed smokes** | 33 (28 GPU, 5 CPU) | **0.5 measured run + ~0.6 est. slot-hold** | **0.54** (incl. 2 × 941 s `smoke_wiring` timeouts) | ak-c22-df2-devhandoff-gate ×5, ak-c22-i8pc-gate ×3, ak-gvfattn-q4kv ×3, ak-27b-served-kvtype-screen ×2 (257+252 s), ak-q38fn-cpu-iqk-q8-decode-r2 / tiny-solo-r2 (941+943 s, predicate never fired) | run time measured (`elapsed_s`); slot-hold = failed share (24 %) of 64 "held by smoke" idle ticks (estimated) |
| 4 | **(b) Republish chains ≥3 in one family** | 9 families, 42 ids | **~1.2** (devhandoff lane 09:53→11:07 = 74 min of the GPU's rank-2 slot incl. 2 preemptions + r6 FUTILITY_HARNESS run; i8pc r1–r3; gvfattn-q4kv r1–r3; kvtype r1–r4) | **2.1** (barrier-elide r2–r4 4,043 s; conv-state-fwd r2–r3 3,691 s; census-refresh r4 5 s × 3q) | ak-c22-df2-devhandoff-gate r1→r6 (5 smoke FAILs, r6 PASS then `FUTILITY_HARNESS_WITNESS` — 7th harness failure in the family), ak-df2-np4-parity-reuse r2–r6 (r2, r3 "complete" in 11 s each = no-op runs), ak-q38fn-draftwin-c22-cpu r1–r6 (legit iteration, not counted) | measured; overlaps partly with (a), (c), (f) — the chain is the *mechanism*, the other rows are the *cost* |
| 5 | **(f) Harness / wiring verdicts** (FUTILITY_HARNESS_*, INCONCLUSIVE-by-harness, INCOMPLETE, trivially-short "complete") | 11 filed | **0.27** | **1.5** | ak-c22-q8mc-gate (689 s GPU, WITNESS), ak-c22-df2-devhandoff-gate-r6 (160 s, WITNESS), ak-mmid-tile-gate (109 s, INCOMPLETE), ak-cpu-conv-state-fwd r2/r3 (INCONCLUSIVE 2,073+1,618 s), ak-cpu-a3b-barrier-elide r2 (1,616 s), ak-27b-tail-fuse2-gate-r3 "complete" in 16 s then r4 FUTILITY_WITNESS | measured from verdict.json × `.ended` duration |
| 6 | **(e) Contamination reruns** | 31 CONTAMINATION lines on 14 rows; 3 rows rerun | 0 | **0.67** | ak-cpu-a3b-barrier-elide r3, r4 (`FUTILITY_HARNESS_CONTENTION`, 1,606+821 s), ak-cpu-gdn-state-fwd-r2 (`FUTILITY_CONTENTION`). Foreign sources: rsync backup (8 hits, 23–75 % of a core), research-intake python (100 %), firefox, claude, `sim.py` | measured |
| 7 | **(g) Failed smoke silently abandoned** (coordinator addition) | 2 operator-approved rows + 2 others >12 h | 0 compute; **17 h latency** | 0 | ak-pernuma-contam-cpu-20261124 (FAIL 18:26Z, "placement proof can't pass on one smoke core"; `-r2` published ~11:00Z next day), ak-gpu-cpuload-contam-20261124 (FAIL 19:03Z, server did not start; superseded, never rerun); ak-mmid-n10-gate r1 FAIL 11:24Z → r2 ran 03:55Z (16 h); ak-rka-ipb-census 16:18Z → 20:14Z | measured timestamps; visible only in queue_status NEEDS-REPUBLISH, which today lists neither (`FAILED (0)`) |

**Totals (de-duplicated across categories): ≈ 10 GPU-h of 24.5 (≈40 %) and ≈ 43 CPU-Qh of 73.5 (≈58 %) did
not produce a candidate verdict.** Of the GPU total, 4.6 h is scheduler idle and 4.2 h is work thrown away by
STOPs; smokes and harness verdicts are small per event but are what *caused* the STOPs and the chains.

What was *not* counted: the 56 `build-autokernel-*` and 32 `build-pipeline-mgmt-*` light claims (84-87, 0 s
durations, released early — correct behaviour); rka-a3b-d-remeasure-q-20261123-r5's six 30-min `partial-native-stopped`
ends (resumable, each added a unit, `charged 3` then owner STOP — legitimate progress); the 118 smokes that
passed (7,721 s GPU, 7,037 s CPU).

### The devhandoff/devselect chain, minute by minute

| Row | spec.json written | smoke result | gap since previous FAIL | failure text |
|---|---|---|---|---|
| ak-c22-df2-devselect-gate-gpu-20261125 | 09:40:06Z | FAIL 09:45:31 (10 s) | — | `device unit test failed: {... 'n_rocm': 199, 'n_rocm_ok': 198, 'pass': True ...}` — unit said pass, smoke said fail (the spliced-log case count) |
| …devhandoff-gate (r1) | 09:53:43Z | FAIL 09:54:38 (16 s) | 9 min | `RemoteDisconnected` — server crashed (wrong sampling loop) |
| r2 | 09:57:22Z | FAIL 10:06:31 (26 s) | 2 min 44 s | `both-knob draft-path unit failed: identity_test rc 1 … LLAMA_DFLASH_DEV_SELECT=1` MISMATCH |
| r3 | 10:14:26Z | FAIL 10:16:14 (21 s) | 8 min | **identical** text to r2 |
| r4 | 10:18:50Z | FAIL 10:21:59 (28 s) | **2 min 36 s** | **identical** text to r2/r3; PREEMPT-PROPOSE 10:19:46 stopped ak-27b-served-ub-arrival-sweep (rank 30, 181 min left) for it |
| r5 | 10:42:50Z | FAIL 10:58:22 (60 s) | 21 min | same unit, `mode: separate-process` — the drafter near-tie variation |
| r6 | 11:00:54Z | PASS 11:06 (74 s) → run 160 s → `FUTILITY_HARNESS_WITNESS` | 2 min 32 s | the reversed switch check |

Every row carried `supersedes: [all predecessors]` and `priority_rank: 2`; none carried `fix_ref`. Each row's
`SMOKE-STRIKES.json` reads `count: 1` — the existing 3-strike park is keyed by **row id**, so a republish resets
it. The lineage-level `MAX_FAILS = 3` park (`rowflow.py:3587`) was reached at r4 but `fresh_attempt()`
(`rowflow.py:311`) grants one more attempt whenever the job sha is new to the lineage — and every republish
rewrites `job.py`, so the park never bites. The keeper log contains **zero** `parked` lines in the window.

## 2. Root causes

### 2a. Pipeline/keeper defects already fixed tonight (commits on origin/main, `scripts/coordination/`)

These produced the rc=75 autorequeue loops (ak-mmid-ub-ceil ×4, ak-i8gemm-pc-sol ×4), the `smoke_wiring` timeouts,
the IDLE-VIOLATION ticks and the quiet-host over-waiting. They are not re-proposed here.

| Defect | Fix |
|---|---|
| rc=75 deadline ends charged the auto-requeue cap; cap hit at 3 | `603fd7099` progressing ends do not charge; `d49681ce6` HARNESS-SKIP-PAUSE |
| Witness never printed (log level) | `b657ac2ff` WITNESS-LOGLEVEL preflight, `095acbc0f` `-lv 4` on every argv with a declared witness |
| `cpu_str` / CPUS-IN-ARGV | `0c60ce2a3` |
| Inputs missing/sha | `5d7c8d577`, `163017c95` |
| Quiet-host row blocks a better-ranked heavy row | `aab494157` QUIET-YIELD |
| Preempt advisory + urgent-smoke-ahead guard | `23ff4e3a1` |
| Complete RESULT re-requeued | `544ca0b4a`, `f95b97193`, `40db70505` |
| Build window never closed; builds starved by quiet rows | `682a286f5`, `c2886df1c`, `fd1e4001c`, `2b791da17` |
| Orphaned smokes, superseded evidence dropped | `618d24756`, `ec50ac9cf`, `0445b9a60` |
| Light claims onto quiet quarters / wrong NUMA half | `d5d0f3450`, `a53ab635d` |
| Static publish rehearsal (warn-only) | `fb70d6248` |

### 2b. Failures the pipeline STILL permits (this audit's targets)

1. **Republish is free.** `publish_row.py` accepts `-rN` for any N with no evidence that the new job behaves
   differently on the previous failure's own logs. Strikes are per id; the lineage park is bypassed by the job-sha
   "fresh attempt". → devhandoff r2–r5 identical failures 8–12 min apart; i8pc r1–r3; gvfattn-q4kv r1–r3.
2. **A failed smoke has no clock.** FAIL-N + `unpublished.json` sits forever; `queue_status` shows it under
   NEEDS-REPUBLISH only while that marker survives, and nothing escalates by age. → pernuma-contam 17 h.
3. **A harness-reason verdict is not a strike.** FUTILITY_HARNESS_*, INCONCLUSIVE-by-harness and a "complete"
   in 5–16 s with no units all file cleanly and the next `-rN` is accepted. → q8mc, devhandoff-r6, barrier-elide
   r2→r3→r4, conv-state-fwd r2→r3, df2-np4-parity r2/r3, tail-fuse2 r3→r4.
4. **Preemption is proposed for a row with a fresh FAIL.** PREEMPT-PROPOSE compares ranks only. → a rank-30
   3 h sweep stopped twice (10:20, 10:33) for devhandoff r4 (failed in 28 s) and aa-diag.
5. **A non-resumable STOP has no cost line.** Owner STOP of c21-gpu27b-identity-r2 at 2 h 59 min lost 2.98 GPU-h
   silently; the row-ended alert says `complete:false` and nothing else.
6. **GPU smoke holds are longer than the smokes.** 64 ticks (~2.4 h) of "gpu-quiet: held by smoke X until T"
   with the device idle: the SMOKE-SLOT books until T, the batch runs one smoke per keeper tick, and EXCLUSIVE rows
   additionally wait a second "device quiet" sample after the hold.
7. **Idle-held grants are only alerted.** c21-fold-cpu r2/r3 held q0–q2 at 3–4 % busy for 24 and 47 min;
   UNDERUSED-shrink is advisory; the alert went unacked 31 min.

## 3. Remediations — deterministic, pipeline-enforced, ranked by waste prevented

Effort: S < 1 day, M 1–2 days, L > 2 days. "Prevented" cites this window's rows.

### R1. Replay receipt gate on republish — `publish_row.py`, `preflight.py`, `mk_ak_row.py` · **M**

**Mechanism.** `publish_row.py` refuses a spec whose `id_stem` has a `FAIL-N.json` (or a harness-class verdict,
see R3) newer than the family's last PASS/RESULT, unless the spec carries a `replay_receipt` **and** the receipt
validates. The receipt is produced by a new `rowflow.py replay <prev_id> --job <new row dir>` that runs the new
`job.py --decide-from <prev out dir>` under `taskset -c 84-87 timeout 120` (mk_ak_row v2 jobs already have a pure
`decide(units)`, `mk_ak_row.py:177`; the template gains `--decide-from` which feeds the previous run's
`out/results.jsonl` and `launcher.out` into `decide()` with no server):

```json
"replay_receipt": {
  "prev_id": "ak-c22-df2-devhandoff-gate-gpu-20261125-r3",
  "prev_fail_sha256": "<sha of dryrun/<prev>/FAIL-1.json>",
  "prev_launcher_out_sha256": "<sha of dryrun/<prev>/launcher.out>",
  "job_sha256": "<sha of the NEW job.py>",
  "decide_cmd": "python3 job.py --decide-from /mnt/raid0/llm/tmp/<prev>/out",
  "prev_failclass": "correctness_gate",
  "observed": {"rc": 0, "verdict": "PASS|FAIL_<x>|...", "n_units": 4},
  "expected_not": "correctness_gate",
  "replayed_at": "2026-11-25T10:17:40Z", "host_cpus": "84-87", "elapsed_s": 3.1
}
```

Validation in `publish_row.py` (new check `REPLAY-RECEIPT`, enforced): the two shas match the files on disk
(so the receipt is for *this* failure), `job_sha256` matches the spec's launcher/job, and `observed.verdict`'s
failclass ≠ `prev_failclass`. A receipt that reproduces the same failclass is itself a refusal with the text
"your fix does not change the verdict on the log it failed on". `preflight.py` repeats the check at grant time.
Remove the job-sha-only `fresh_attempt()` bypass in `rowflow.py` (a new job sha is the *normal* republish, not
evidence); keep it only when `fix_ref` is present.

**Prevented here.** devhandoff r3, r4, r5 (identical MISMATCH text; `decide()` on r2's own log returns the same
class), i8pc r2/r3, gvfattn-q4kv r2/r3, kvtype-screen r2, mmvf r2, attn-kv-concat r2, tail-fuse2 r2 → **12 of 33
failed smokes**, the two preemptions of the 3 h sweep, and 74 min of the rank-2 GPU lane. **≈ 1.0 GPU-h.**

**False-positive risk.** Low: a fix that genuinely needs the server (e.g. a crash fix, devhandoff r1→r2) replays
to a *different* class (no crash → decide runs) and passes. Cost of the receipt: seconds on 84-87. Families
with no previous out dir are unaffected.

### R2. Two-strike family park with visible unpark — `publish_row.py`, `rowflow.py` · **S**

**Mechanism.** `record_smoke_outcome()` keys `SMOKE-STRIKES.json` by `id_stem(rid)` (file
`dryrun/.family/<stem>.json`) instead of `rid`; count resets only on PASS/RESULT. At `count >= 2` the keeper writes
`PARKED-FAMILY` (one log line + one `smoke-fail-parked` alert to the owner and the operator queue), SMOKE-PLACE and
the GPU batch skip the family, `publish_row.py` refuses further `-rN`. `rowflow.py unpark <stem> --reason "<text>"`
(existing `unpark` extended to stems) is the only exit; it logs `UNPARK <stem> by=<agent> reason=…` and the next
FAIL re-parks. R1's receipt is accepted as an unpark reason automatically (receipt present ⇒ one attempt).

**Prevented here.** Third-and-later failures: devhandoff r3–r5, i8pc r3, gvfattn-q4kv r3 → **5 smokes + both
preemptions** (≈ 0.6 GPU-h), and the attention of three subagents.

**False-positive risk.** A genuinely different third attempt costs one command with a reason that is logged —
that is the point.

### R3. Harness-reason verdicts and no-op completes count as strikes — `akloop/ak_runend.py`, `smoke_verdict.py`, `complete_check.py` · **S/M**

**Mechanism.** At filing, if `native_verdict` matches `FUTILITY_HARNESS_*|FUTILITY_WITNESS|FUTILITY_RESIDENCY|
INCOMPLETE|INCONCLUSIVE` with `side: harness` in failclass, **or** the run is `complete:true` with
`units < spec.units_min` or `elapsed_s < 60` (df2-np4-parity r2/r3 at 11 s, census-refresh-r4 at 5 s, tail-fuse2-r3
at 16 s), write a strike into the family file from R2 and tag the verdict `harness_strike: true`. The next `-rN`
then needs R1's receipt (replaying `decide()` on the harness-failed run must *not* return the same futility
class). `queue_status` shows the family as `STRIKE 1/2 (harness)`.

**Prevented here.** barrier-elide r4 (821 s), conv-state-fwd r3 (1,618 s), tail-fuse2 r4, devhandoff r6's
successor if one is published → **≈ 0.7 CPU-Qh + 0.1 GPU-h**, and it makes the "a 5-second complete is a
result" failure impossible to file silently.

**False-positive risk.** Medium-low: a legitimately tiny row (ak-gdn-pscale-rocm-tests, 14 s complete) must
declare `units_min: 1` / `min_elapsed_s` in its spec; mk_ak_row v2 writes both from the estimate.

### R4. Replay smoke as a preflight check (no GPU) — `preflight.py`, `mk_ak_row.py` template · **M**

**Mechanism.** The same `--decide-from` entry point as R1, but run by `preflight.py` at publish for **every** row
whose family has any previous `out/` (FAIL or complete), not only after a failure: `REPLAY-DECIDE` FAILs if
`decide()` crashes, returns no verdict, or returns the previous FAIL's class. Runs under
`nice -n 19 taskset -c 84-87 timeout 60`. This is R1 made automatic — the agent never writes the receipt;
preflight does, into the spec's `preflight` block.

**Prevented here.** devselect (unit `pass: True`, smoke FAIL — `decide()` on its own log reproduces the
contradiction in 0.5 s), devhandoff r2 (identity_test parse), the two `smoke_wiring` predicate rows (predicate
`grep '"ok": true'` never matches `decide()`'s output format → caught before 941 s each) → **≈ 0.5 CPU-Qh +
0.1 GPU-h**, plus everything R1 catches.

**False-positive risk.** Rows whose `decide()` needs live server state. mk_ak_row v2 separates `measure_unit()`
from `decide(units)` already; legacy rows get `WARN` not `FAIL` until they carry the generator stamp
(same warn-first path `bb5c756d0` used).

### R5. Stale failed-smoke escalation — `rowflow.py` keeper tick, `queue_status.py` · **S**

**Mechanism.** Each tick: for every `dryrun/<id>/FAIL-N.json` with no newer `PASS`, republish (`ready/<stem>-r*`
newer than the FAIL), `.withdrawn` or `.superseded` marker, compute `age`. At **2 h** emit `smoke-fail-stale`
(warning, owner); at **8 h** escalate (critical, owner + operator queue + bus nudge, repeated every 8 h). For rows
with `priority_rank <= 10` or `spec.operator_approved: true` the thresholds are **1 h / 4 h**. `queue_status`
gains a `FAILED-STALE (age, rank, owner)` block that does not depend on `unpublished.json` surviving.

**Prevented here.** ak-pernuma-contam-cpu (17 h), ak-gpu-cpuload-contam (17 h, still not rerun), ak-mmid-n10-gate
(16 h), ak-rka-ipb-census (4 h). The two contamination rows were operator-approved and are the instrument for
category (e); they would have run overnight on an idle quarter.

**False-positive risk.** None — advisory, no refusal.

### R6. GPU smoke budget per family per day — `rowflow.py` SMOKE-PLACE / GPU-SMOKE-BATCH · **S**

**Mechanism.** The batch counts GPU smokes per `id_stem` in the last 24 h from `dryrun/*/{FAIL,PASS}.json`; at
**3** the 4th smoke is not placed and the row is marked `SMOKE-BUDGET` (same unpark exit as R2). Budget and
window are allocator.json knobs (`gpu_smoke_budget_per_family: 3`).

**Prevented here.** devhandoff r4–r6 (3 smokes), gvfattn-q4kv r4 would have waited for an unpark; **≈ 0.3 GPU-h**
of smoke run + slot holds. Mostly a backstop behind R1/R2.

**False-positive risk.** Families whose stems collide (`ak-c22-q8w{8,o,m,p}-op` are distinct stems — fine).
A multi-variant family that *legitimately* publishes four GPU rows in a day pays one unpark.

### R7. No preemption, no silent STOP, for a striking family — `rowflow.py` (PREEMPT-PROPOSE, `23ff4e3a1`), `filler_run15.sh` · **S**

**Mechanism.** (a) PREEMPT-PROPOSE is suppressed when the urgent row's family has a strike or a FAIL younger than
2 h — a row that just failed its smoke has not earned another row's slot. (b) An owner STOP of a running
**non-resumable** grant older than 60 min requires `rowflow.py stop <id> --reason`; the keeper's row-ended alert
and the `AUTOREQUEUE-END` line carry `lost_s=<elapsed>` and `lost_gpu_h`/`lost_qh`, and a daily `STOP-LOSS` summary
line totals them. The bare `touch STOP` path keeps working for resumable rows and for grants under 60 min.

**Prevented here.** ub-arrival-sweep r1 + r2 (≈ 0.2 GPU-h) stopped for devhandoff r4 / aa-diag. (b) does not
prevent c21-gpu27b-identity-r2's 2.98 GPU-h but makes it a logged number instead of a silent `complete:false`.

**False-positive risk.** (a) none measurable — a smoke waits ≤ one grant boundary anyway. (b) one `--reason`.

### R8. Smoke hold ends when the smoke ends — `rowflow.py` GPU-SMOKE-BATCH, SMOKE-SLOT · **M**

**Mechanism.** The batch runner runs the queued GPU smokes back-to-back inside one hold and releases the hold the
moment its queue is empty (not at the booked `until T`); the keeper wakes on `grants/*.ended` and
`dryrun/*/{PASS,FAIL}` via inotify (or a 20 s sub-tick for GPU boundaries only) instead of waiting for the next
161 s tick; EXCLUSIVE rows accept one quiet sample when the previous holder was a smoke the keeper itself ended.

**Prevented here.** Up to the 64 "held by smoke" idle ticks (**≈ 2.4 GPU-h**) plus part of the 36 boundary gaps
(**≈ 1 GPU-h**). Largest single item in the table; also the least AutoKernel-specific.

**False-positive risk.** None; purely latency.

### Ranking by waste prevented (this window)

| # | Remediation | GPU-h | CPU-Qh | Effort | Enforced by |
|---|---|---|---|---|---|
| 1 | R8 smoke-hold release + event-driven boundary | ~3.4 | — | M | keeper |
| 2 | R1 replay receipt on republish | ~1.0 | 0.3 | M | publish_row + preflight |
| 3 | R2 two-strike family park + logged unpark | ~0.6 | — | S | publish_row + keeper |
| 4 | R3 harness verdicts / no-op completes are strikes | 0.1 | 0.7 | S/M | ak_runend + smoke_verdict |
| 5 | R4 replay smoke in preflight | 0.1 | 0.5 | M | preflight |
| 6 | R7 no preemption for striking families; STOP cost line | 0.2 | — | S | keeper |
| 7 | R5 stale failed-smoke escalation | latency 17 h → 1 h | — | S | keeper + queue_status |
| 8 | R6 GPU smoke budget per family | 0.3 (backstop) | — | S | keeper |

R2, R5, R6, R7 are one-day items with the strike/unpark code already present (`publish_row.py:1260-1310`,
`rowflow.py:unpark`); they can ship together. R1+R4 share the `--decide-from` template change and should ship
as one PR. R8 is independent and worth the most GPU time.

### What this does to AutoKernel's four pledges

| Pledge | Becomes |
|---|---|
| replay before republish | R1/R4: `publish_row` refuses without the receipt; preflight generates it |
| one owner per row | unchanged (not a pipeline property) — but R2's unpark names who re-opened a family |
| check a diagnosis against the log before dispatching | R1: the receipt *is* that check, run by a script on the real log |
| two-strike pause | R2/R3/R6: a keeper state, not a pause the agent remembers |

Next: pipeline-mgmt — open the implementation handoff boxes for R2+R5+R6+R7 (one PR, S) and R1+R4 (one PR, M);
R8 as its own keeper box; R3 after R2 lands.
