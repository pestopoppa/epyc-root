# 2026-09-25 — main-ak-seat (overnight: DS41 run 9 → stop → ctx A/B → run 9b)

Overnight window 2026-09-24 20:15Z → 2026-09-25 04:05Z. The evening build and its learnings are in
`progress/2026-09/2026-09-24-main-ak-seat.md` (*Reduced-scope planner build*, root `a32ba396`/`dcadbe72`). This
entry starts where that file stops, at "run 9 LIVE". Owning handoffs:
- INF-77, `handoffs/active/deepseek-v41-flash-evaluation.md` (DS41 §C);
- INF-78, `handoffs/active/autokernel-orchestrator-actor-backend.md`.

Running plan: `/mnt/raid0/llm/tmp/stack-window-plan-20260924.md`.

## DS41 run 9: refused, fresh store, launched

- **First launch REFUSED at 20:14Z.** The store's champion of record was the old port anchor `ebb68dc55`, not the
  anchor `5a60152ae` (0 keeps, 1 experiment row). **The run-9 dry run (rc=0) never checks this.**
- **The operator approved the fresh-store route**, following the DS41-C13 precedent:
  - the store is archived as `store-run8-cor-ebb68dc55/` (`ARCHIVED.txt`; reversible);
  - a fresh `store/` carries over `inbox/`;
  - the refused state dir is kept as `state-run9-refused-cor/`.
- **Run 9 launched 20:14:55Z**: `serial_run` 2580766, `run.py` 2580771, `state-run9/`, research `6afc7eed`,
  target `ds41-5a60152ae-cpu-t48-dspark-b2`, :8083 on `-kvu` (196,608-token slot).

## Half-screen floor (00:25Z)

- Location: `store/runtime-source-floors/5b995a27…/3a0b8832…/serving-floor.ds41-5a60152ae-cpu-t48-dspark-b2.cpu-half-….json`.
- Setup: cores 0-47, `-t 48`, `matched_process_v2`, 48 launches, one every ~4.7 min.
- **Floor 5.789%** (interval 2.91-9.55%), between-launch SD 2.79%, MDE 3.0%. Run 7's floor on the old anchor was
  5.097%.

## Loop order learned (the pre-launch plan was wrong)

- **The real order:** half floor → batch 0's half-screen PROPOSAL and its measurement → batch 1's full-target
  calibration (~4 h, every CPU region lock).
- **The plan's assumption:** both floors back to back (~8.5 h). That was wrong.
- **Consequence:** an evening launch puts the full-target calibration into the next day.
- Recorded in DS41-C25 (run 9 / 9b block), DS41-C28, and `docs/guides/agent-workflows/agent-loop-design.md` →
  *Launching and stopping a DS41-style serial run*.

## Run 9 stopped at the boundary (01:30Z)

- **When:** at the half-floor → batch-0 boundary. The batch-0 planner had been live 61 min on the old inline
  code, and that call was discarded.
- **How:** TERM to `run.py` 2580771 and `serial_run` 2580766. Everything died, including opencode 3054534, with
  no KILL.
- **The DS41-C22 stop path works on a live actor call.** Its record is the first `actor-calls.jsonl` line, an
  `actor_call.v1` with rc −15 (this closes DS41-C24).
- The CPU locks were freed, and `state-run9/STOPPED.txt` was written.

## Research main and shared clone

- **Research main fast-forwarded** `170c763c` → `30631761` (`lane/ak-planner-integ-20260924`), pushed under the
  push lock.
- **Contents:** perf cache `f4a5d240`, ctx-variable `ce5800cb`, turn metrics `0bf2d7c2`, pre-existing test fixes
  `535391b6`, `node_profile` render in both modes `8a9d2a40` (DS41-C20e), metrics hardening `30631761`.
- **The shared clone was fast-forwarded after run 9 was dead.** Other sessions' dirty files were left untouched.

## INF-78 OAB-9: context-placement A/B — INLINE wins

**Setup.**
- Driver: `/mnt/raid0/llm/tmp/ak-ctx-ab/driver.py`, 2 ABAB pairs, 01:28Z → 04:03Z. Pair 3 needed 71 min and did
  not fit the 3.5 h budget.
- Seat and server: plain opencode seat; :8083 Qwen3.8-27B Q8_0, one server generation (pid 2009477, `-kvu`,
  `n_ctx_slot` 196,608).
- Prompts: the inline control is run 8's prompt plus `node_profile` (79,890 chars, sha `a265a03a`); the variable
  arm's prompt is the index only (18,055 chars).

| | inline p1 | inline p2 | variable p1 | variable p2 |
|---|---|---|---|---|
| wall (min) | 37.6 | 28.7 | 54.4 | 33.6 |
| steps | 23 | 24 | 49 | 29 |
| tool calls | 25 (bash 22, read 3) | 26 (bash 21, grep 1, read 4) | 54 (bash 35, read 19) | 35 (bash 26, grep 1, read 8) |
| decoded | 52.9k | 43.8k | 68.9k | 47.7k |
| first / peak context | 40.6k / 104k | 40.6k / 92k | 19.1k / 163k | 19.1k / 118k |
| compactions | 0 | 0 | 0 | 0 |
| reply (all schema-valid) | abstain | hypothesis `akm-q4k-x4-avx512` | abstain | abstain |

**Bundle use and contention.**
- The variable arm used the bundle as designed: 6-7 bundle calls, all 3 required files read, 0 `INDEX.md`
  re-reads.
- It also read **all six file-only sections**, then explored lane source more (3-4x inline's tool output).
- Contention was negligible: 6 of 132 (inline) and 2 of 172 (variable) `/slots` samples had another slot busy.

**Predictions checked:**
- first-step context halves: **confirmed**;
- peak falls: **refuted**;
- 0 compactions instead of 1: **moot**, because inline no longer compacts on the 196k slot;
- wall gain: **refuted**.

**Learnings** (written into INF-78 §Techniques learned → 4 and the agent-loop guide):
- a thin prompt made the 27B explore MORE, so context placement alone does not reduce work;
- the RLM-style benefit presupposes a model or scaffold that pulls precisely;
- with 196k slots, compaction is no longer the binding cost;
- the next levers are the fixed overhead (OAB-10), lane reads and never building (OAB-11), and
  orchestration-side scouts (OAB-8), not hiding context.

**Limits.** n=2, and inline always ran first. A 3rd pair, a different model, a small slot, or pull caps could each
change the verdict (OAB-9b).

**Evidence:** research `605e8301` + `135b8492` + `0ac0b0c0`, `artifacts/autokernel_ctx_ab_20260925/`:
- README with the table, verdict and caveats;
- `driver.py`, the log, `results.jsonl`, the per-call results and `actor-calls.jsonl`;
- the two variable-arm bundle manifests and indexes.

The exports and bundle sections stay under `/mnt/raid0/llm/tmp/ak-ctx-ab/`.

## Run 9b launched (04:04Z)

- **Processes:** `serial_run` 3279632, `run.py` 3279639, `state-run9b/`, same store, research `30631761`.
- **Mode:** default **inline** (the winner), now with `node_profile` and per-call metrics.
- **`EPYC_ROOT_REPO`** = `/mnt/raid0/llm/worktrees/root-main-epyc-root-repo`, a detached root `origin/main`
  checkout, not a lane.
- **The half floor was reused.** The run went straight to the planner call (opencode 3284175, 04:09Z) with no
  re-calibration.
- **Known daytime impact.** Batch 1's full-target calibration (~4 h, every CPU region lock, blocks :8070 and the
  CPU speech cores) follows batch 0's proposal and measurement, so it will likely run mid-day on 2026-09-25
  (DS41-C28).

## Root documentation (this wrap-up)

| File | Change |
|---|---|
| `handoffs/active/autokernel-orchestrator-actor-backend.md` (INF-78) | `[x]` OAB-9. New §Techniques learned → 4 (A/B table, predictions checked, learnings, what could change the verdict). OAB-7 status: built, A/B'd, loses on the 27B plain seat. OAB-7s/4m/R4c merge status. OAB-12 progress. New `[ ]` OAB-9b |
| `handoffs/active/deepseek-v41-flash-evaluation.md` (INF-77) | `[x]` C20e, C20h, C24. Run 9 / 9b block under C25 (refusal, fresh store, half floor, loop order, stop, relaunch). C10a and C25 launch-line halves recorded; both stay open on run 9b's first planner reply. C11 re-check. New `[ ]` C27 (dry-run COR check) and C28 (batch-1 calibration off-hours) |
| `docs/guides/agent-workflows/agent-loop-design.md` | Run-9 launch lessons (loop order, COR refusal, `EPYC_ROOT_REPO`, stop path). A/B result and learnings in *Context as files*. Two unresolvable backtick references fixed so the reference guard passes |
| `scripts/vidya/adapters/README.md` + `handoffs/active/vidya-belief-substrate-program.md` | The metrics and bundle producers are now merged. VB-AK-METRICS-1 and VB-AK-CTX-1 updates point at the first post-hook rows and manifests |
| `handoffs/active/tool-output-compression.md` | TOC-RD-1b recurrence: the PII hook rewrote 14 perf-period cells in `135b8492` |
| `progress/2026-09/2026-09-25-main-ak-seat.md` | this file |

## Checklist sync / derived actionables

- **Flips: 4** (INF-78 OAB-9; DS41-C20e, C20h, C24).
- **Kept open on purpose:**
  - C10a and C25: their launch-line halves are satisfied, and their remaining clause is run 9b's first planner
    reply, in flight at wrap-up;
  - C11: `test_serial_roster` still fails 3 tests on `605e8301`, while `test_existing_cpu_run` now passes.
- **Filed: 3 new tasks** — DS41-C27, DS41-C28 and INF-78 OAB-9b.
- **Extended: 5** — OAB-7, OAB-12, VB-AK-METRICS-1, VB-AK-CTX-1 and TOC-RD-1b.
- **Declined: 3.**
  - A 3rd A/B pair on the unchanged setup: 2/2 on every cost metric, so it folds into OAB-9b's trigger.
  - A separate belief-kernel source for the A/B driver's `results.jsonl`: its columns are the
    `actor_call_metrics.v1` rows (VB-AK-METRICS-1) plus bundle reads (VB-AK-CTX-1).
  - Re-running the bounded arm now: that is DS41-C20d2, already filed. The A/B tested placement, not the seat.
