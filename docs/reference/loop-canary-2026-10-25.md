# WS58 planning-context canaries + native-ingest dry runs (2026-10-25)

> **Durable copy (2026-10-25 wrap-up, workspace-58).** Copied from `/mnt/raid0/llm/tmp/ws58-canary-20261025/CANARY.md`
> (tmp is scratch, MEASUREMENT.md §5). The source's Canary B section was a placeholder ("see section below") with no body;
> the summary below was added at the wrap-up from that run's own `B-summary.json` (`verdict`, `post_verification`,
> `views_reader_comparison`) and the defect list ws58 assigned to Codex in
> `codex-ni-20261024-scheduling/tasks-from-ws58/BATCH-2-20261025.md`. The harness scripts are in
> [`loop-canary-2026-10-25-harness/`](loop-canary-2026-10-25-harness/). Follow-up: VB-CANARY-GATE-1 in
> `handoffs/active/vidya-belief-substrate-program.md`.

No inference of any kind ran: no model server, no llama-* binary, no GPU, and no planner/actor LLM call.
Neither planner could be stopped at context assembly through its own entry point. AutoKernel's
`build_context` is a closure in `run.py` main() that runs only after profiling and anchor builds, and
AutoPilot is paused, with its daemon off limits. Each context was therefore assembled by calling the
same library functions from small read-only harnesses (`harness/canary_a.py`, `harness/canary_b.py`).

Every `loop_beliefs prepare` ran against a SCRATCH COPY of `/mnt/raid0/llm/state/vidya`: the ledger,
the sync marker, loop-memo, known-good and the read log all live in `state/<run>/`. Alarms went to a
scratch state with delivery disabled (`alarm/alarm_config.yaml`). The canonical ledger sha256 is still
`ddcf50b4…a21c6` and its mtime is still 10-24 17:14.
Reader side effects seen on live paths: the `-shm` files of `experiments.db` and `resume-claims.sqlite3`
had their mtimes touched. That is normal for read-only sqlite in WAL mode. No other live file changed.
`/workspace/coordination/session-bus/alarm_state.json` changed at 07:05:38. That write came from the
fleet watchers (`cpu-idle-with-queued-work` and `queue-aging-*` last_seen), not from this canary.

## Canary A: AutoKernel Q38FN (research origin/main 413f5b7f5, detached worktree, now removed)

Inputs:
- Store: `store-b0ba1d427`.
- Epoch: the 10-22 run's epoch `c5d9ecd6…` / measurement epoch `829b98d1…`. The champion is unchanged at dd3d9721c.
- Target: exactly what the 10-22 receipts sent: model UD-IQ4_XS shard 1, quant "", backend cpu, device epyc-9655, surface `serving:q38fn-802bf9ac6-cpu-t48-mtp-d4`.
- `current_regime`: as `run.py:3839-3843` builds it (census quant, NATIVE_CPU_RECIPE).
- Source roots: the store, as `run.py:686-693` sets them.
- Planner path replayed: `actors.AgentPlanner.propose` lines 3742-3758, with `belief_context.prepare`, then `render_context`, then `_HYPOTHESIS_TASK`. It stops before `_seated` / `_proposal_from_agent`.
- Omitted sections (they need a live launch or profile): target, kernel_hotspots, cpu/node profile, long_context, serving_observations and runtime_*. No belief receipt was written.

| | A1 default resolution | A2 ROOT=views | A3 views + current index (real-fetch equivalent) |
|---|---|---|---|
| ROOT used | `/workspace` (`resolve_root_repo`: env unset, so /workspace wins because it has the reader) | `/mnt/raid0/llm/views/epyc-root-main` | same |
| ROOT HEAD | 97268ec0f (stale; origin/main is 6f2011142 → dbf3cc506) | dbf3cc506 (the hub moved it from 6f2011142 during the canary) | dbf3cc506 |
| belief status | ready; index already fresh; store ingest +1 claim / 3 frames | ready; store ingest +103 claims / 309 frames | ready; intake sync **ingested 37 frames (14.3 s)**, plus 103 store claims |
| tiers (target/sibling/host/knob/lineup) | 372/0/24/0/0, shown 16 target + 2 host | 474/0/24/0/0, shown 16 + 2 | 371/0/24/0/0, shown 16 + 3 |
| usable claim ids | 23 (ak-exp, legacy-serving-v2, moerout, u4-noise) | 23 (adds 2 `clm_servedshape:…IQ4_NL`) | 23, **without row 337's `clm_ak-exp…ac8b3104…`** |
| row-337 query-major NULL −1.10% in context | yes: Already tried, belief line and tried index | yes | **only in-store "Already tried"; absent from the belief section** |
| row-335 visible-kv keep_candidate +1.33% | belief section only (missing from in-store history) | same | same |
| do-not-repeat guard on a query-major re-proposal | does not refuse | does not refuse | does not refuse |
| seed inbox | 13 notes: 00-gate-d0a61d080ab9-a1, 60…72 (all 10-03..10-06) | same | same |

Known conclusion tested: the 10-22 it3 +4.73% (`akm-cpu-fa-query-major-row-schedule`) did not replicate.
Row 337 is a measured_null at −1.103% against a 1.365% floor. The original +4.73% was never recorded,
so only the replicate null can appear. The rendered context does carry it:
`- akm-cpu-fa-query-major-row-schedule → measured_null -1.103% … refused: effect -1.103% did not clear
the 1.365% noise floor`. That should let a planner that reads it avoid re-proposing the idea.
**Nothing enforces it, though. The formation guard returns None for every case: the same id, a renamed
id, and a control run with the row's own scope.**

Verdict A: **PASS (with caveats)** on "the assembled context contains the relevant historical
knowledge". The in-store channel carries it on every ROOT. The belief channel loses it on the first plan
after an intake sync (D-A1), and the mechanical do-not-repeat guard is inert (D-A2).

### Defects (A)
- **D-A1: a producer-time ingest is invisible to the plan that ran it.** `loop_beliefs.py:1939` fixes
  `as_of` before `ensure_current`. The scoped ingest stamps frames `created_at=_now()`
  (`loop_beliefs.py:252`, second resolution), and `visible_frames` (`:693`, used at `:891` and `:1958`)
  drops frames newer than `as_of`. Whenever sync or ingest crosses a second boundary, this loop's newest
  outcome is hidden from this plan. A3 reproduces it: the 14 s intake sync hid the row-337 null claim.
  The live ledger lacks that claim and the live intake index is ahead of the marker, so the next real
  prepare WILL hit this case.
- **D-A2: the do-not-repeat formation guard is inert for Q38FN.** It has three independent causes:
  1. `current_regime.quant` is None. The census of the split GGUF's first shard returns
     `dominant_quant=None` (`run.py:3840`, `workload_contract.py:111`). `dispatch_guard.py:177` then
     makes `project_regime` return None, so `same_regime` at `:190` is always False. All 337 store rows
     also have `research_scope.quant = None`.
  2. `research_scope` is dropped for payloads over 2 MiB (`experiments.py:605`). That covers 31 of 38
     answer rows; row 337 is 19.2 MB and row 335 is 19.2 MB. The same cap drops `claims`
     (`experiments.py:602`), so row 337 renders as `[mechanism claim: hypothesis]`.
  3. The surfaces disagree. `research_scope.measurement_surface` is the comparison surface
     `…-d4-lc64k-23eea2fa` (`run.py:6158`), while `current_regime` uses `args.surface` `…-d4`
     (`run.py:3843`).

  Even with all three fixed, `dispatch_guard.py:205` needs ≥3 comparable answers, and query-major has
  one. A one-shot measured null is never mechanically closed.
- **D-A3: ranked recall drops the current-epoch keep_candidate.** `run.prior_experiments` returns the
  ranked top-40 and skips `_with_pinned_history` when ranking is on (`run.py:1975-1981`, ranking on by
  default at `:2349`). Only 2 of the 6 same-epoch rows survive. Row 335 (visible-kv +1.33%,
  keep_candidate) and the 332/333 refusals are missing from "Already tried" and "Always shown", even
  though `render_context` promises every current-epoch keep_candidate. Only the belief section shows
  row 335.
- **D-A4: the default ROOT is the stale shared clone.** `belief_context.resolve_root_repo`
  (`belief_context.py:101-118`) picks `/workspace` whenever the reader file exists, without checking
  staleness. With that ROOT the reader and scoped_ingest are a day old: they ingest 1 store claim instead
  of 103 and miss the served-shape claims. The 10-22 run avoided this only by passing
  `--belief-root-repo` explicitly. `ak_run.sh` still exports `EPYC_ROOT_REPO=/workspace`, and
  `serving_beliefs.PlannerFeedback` (`serving_beliefs.py:157`) falls back to that env var. Its value
  here is moot because run.py passes the resolved root.
- Observation: the inbox seeds are all from 10-03..10-06, and `63-…new-base-champion-b0ba1d427` names a
  superseded champion. No note records the 10-22 FA DISCARD.

## Canary B: AutoPilot

*(Summary added at the wrap-up from `B-summary.json`; the run wrote no body for this section.)*

Inputs: AutoPilot paused (`trial_counter` 1506, no in-flight trial), its daemon untouched. The controller prompt was
assembled by `harness/canary_b.py` through the same library functions (82,598 characters). The StrategyStore was
opened on a COPY with a hash-fallback embedder, because the real BGE embedding is inference; semantic ranks are
therefore not reproduced. Two `socket.connect 127.0.0.1:8000` calls from `StructuralLab.current_flags` were blocked
by the guard. The canonical ledger, known-good file, telemetry and strategy DB were unchanged afterwards.
Belief ROOT resolved to `/workspace` (stale). The views reader (`6f2011142`) gave a different claim set
(20 ids, not the same section).

Verdict: **PARTIAL/FAIL** on "the assembled context contains the relevant historical knowledge".
- Present: the numeric_trial 0+/15- insight (trials 1479-1500), the opseed convention (toolrunner/REPL fix and
  denylisted flags), and the vidya pbhol `short_slot_index_order` REGRESSED +2104% claim.
- Missing or wrong: the trial-1472 frontier keep (`ingest_triviality_guard=True`, q = 2.025) appears only as the bare
  id `latest_frontier=1472`, and the Pareto summary says 0 entries because the epoch fence (2026-08-10T16:23Z) postdates
  every trial. Seed-batch telemetry is 20/20 unit-test pollution (about 0 s per question).

### Defects (B)
- **D-B1:** `tests/unit/test_autopilot_actions.py:1160,1203` write to the LIVE seeding telemetry file.
- **D-B2:** the prompt carries two contradictory frontier sizes (`pareto_archive.py:945` vs
  `experiment_journal.py:1633-1641`, which ignores the epoch fence).
- **D-B3:** the default belief ROOT is the stale shared clone (same as D-A4).
- **D-B4:** the kvq block says "unavailable" while the belief block lists kvq claims.
- **D-B5:** the bridge prepare cannot forward a read log (`loop_beliefs_bridge.py:659-667`).

Assignment: D-A1..A3 and D-B1/B2/B4/B5 join Codex LOOP-SAFETY C2/C3 (BATCH-2, due 10-26 18:00Z); D-A4/D-B3 are C1.

## Ingest dry runs (writes nothing)

ROOT `/mnt/raid0/llm/views/epyc-root-main`, HEAD 6f2011142 at run time. Before running, `cli.py
cmd_ingest` was read to confirm `--dry-run` skips `write_lock` and the append. The CLI was pointed at a
scratch ledger copy, `state/ingest/`, with `--ledger`. The sha256 of the copy and of the canonical
ledger was unchanged before and after every run. Every invocation returned rc 0.

| tick | run dir | adapter | outcome | rows / frames |
|---|---|---|---|---|
| M4.2 | `f8-launchers-20261023/m4-srpf-pbhol` (root) | pb-hol | declined: no `summary.json` at root | 0 / 0 |
| M4.2 | same `/out` | pb-hol | projected (6 arms) | 6 / 18 |
| M4.2a | `f8-launchers-20261024/m4-srpf-pbhol-2a` (root) | pb-hol | declined: matched nothing | 0 / 0 |
| M4.2a | same `/out` | pb-hol | declined: single arm `off512`, no comparison | 0 / 0 |
| M4.2b | `f8-launchers-20261024/m4-2b-champion-control` (root and `/out`) | pb-hol | declined: summary at `out/w-*/L*/summary.json`, beyond the locator | 0 / 0 |
| KPF-17.4c | `f8-launchers-20261024/kpf17-4c-bisect` | kv-prefix-fork | projected (2 units; DESIGN said partial) | 2 / 6 |
| KPF-18.0b | `overnight-20261020/kpf18-run` | kv-prefix-fork | projected | 7 / 21 |
| KPF-18.0d item 3 | `overnight-20261020/kpf18-run-w1c` | kv-prefix-fork | projected (a dry run does not dedup against the 360 existing frames) | 1 / 3 |
| KPF-18-S1.R4 | `f8-launchers-20261024/kpf18-s1-r4` | kv-prefix-fork | declined: no `belief_measurements.jsonl` (pre-hook) | 0 / 0 |
| AKX-ALL-26b | `epyc-inference-research/artifacts/akx_all_26_cpu_20261020` | ak-width-cells-cpu | projected (CPU half; the HIP half has no adapter) | 10 / 30 |
| PB-QCOST-1 confirm | `f8-launchers-20261023/pb-qcost-1-confirm` | pb-qcost | projected | 18 / 54 |
| PB-QCOST-1 confirm-R | `f8-launchers-20261024/pb-qcost-1-confirm-r` | pb-qcost | projected | 18 / 54 |
| SEC-ART-POST-b, GPU-ZOS-2.1 | — | none listed in DESIGN | not run | — |
| NIB2-GNX-1 | — | README row, no module | not run | — |
| P1-PHASE2-SERVED-SHAPE-RECAL | — | autokernel_served_shape | not run: DESIGN marks it already ingested | — |

Nothing was refused. Run dirs are under `/mnt/raid0/llm/tmp/` unless noted. Raw output is in `ingest/<tick>.out`.
Two pb-hol gaps remain: the M4.2b nested `L*/summary.json` layout, and the M4.2a single arm. M4.2 only
needs `out/` passed as its path.
