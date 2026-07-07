# Evidence Plane — Per-Question Ledger + Sequential Verdicts (+ game layer)

**Current checkpoint - 2026-07-06T08:01Z W8 forced replay/AP-9 repair
deployed**: AutoPilot is live as PID `3935151` with
`--max-trials 3000`, launched through the canonical Fable authority daemon with
`AUTOPILOT_PLANNER_PRIMARY=local_frontdoor`,
`AUTOPILOT_PLANNER_CRITIC=local_worker`, Claude fallback, planner hints, tool
sentinels, sequential verdicts, and W6 audit flags. `phase_health_report.py
--require-current-code --json` reports trial `1217`,
`action_type=numeric_trial`, `phase=dispatch_action`, `pid_alive=true`, and
`code_stale=false` after the restart loaded orchestrator `e3b13edd`.

**2026-07-06T16:44Z report refresh**: regenerated
`orchestration/reports/w8_promotion_trajectory_20260706T164403Z.{json,md}`
and `orchestration/reports/fable5_gate_report_20260706T164403Z.{json,md}`.
W8 remains `progressing` with replay-eligible candidates
`80aa44d93a242af5`, `289c4fc0fb5a334d`, and `d3f28243801548b2`, but Fable5
is still blocked because phase health is stale (AutoPilot PID `131226` is
gone), the W6 gaming alarm is still triggered, and tool-use activation is now
ready because the orchestrator launcher now sets
`AUTOPILOT_TOOL_SENTINELS=1` alongside `ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT=1`.

Orchestrator `1639748a` is deployed in that daemon. It threads the current
`selectable_action_types` set into `planner_coordinator.plan_with_providers()`,
treats known-but-unavailable action types as unusable before critique, and
rejects critic revisions that reintroduce unavailable types. The first observed
post-restart planner turn used the fully local routine path: the spend breaker
selected `local_frontdoor/local_worker`, the local critic approved the draft,
and the higher-tier probe guard intentionally forced T3 pressure. This means the
old "deploy `1639748a` at boundary" instruction is complete.
Orchestrator `9522b76e` prevents the higher-tier probe guard from overriding a
planner-selected frontier-moving action while outcome progress is already
frontier-stalled, and `78ae65e6` escalates that stale-outcome signal from prompt
advice into a bounded pre-dispatch fallback: seed/eval/housekeeping actions are
replaced with a metric-bearing numeric trial when frontier admission is stale,
while `numeric_trial`, prompt/code/GEPA mutations, one-flag structural
experiments, and `train_routing_models` pass through unchanged.
Orchestrator `e3b13edd` repairs the last replay/dispatcher seam exposed by
trials `1213`-`1216`: W8 replay pressure now remains active while replay or
confirmation is still required, materialized multi-param NumericSwarm
candidates are force-replayable, and AP-9 is bypassed only for an exact
`seq_candidate_replay_forced` match on the current trial. Trial `1217` is now
evaluating the source-trial-`1197` `repl_executor` replay with
`repl.turn_token_cap=1964` and
`repl.frontdoor_non_tool_token_cap=866`; the earlier skipped rows remain audit
evidence and were not deleted.

Startup StrategyStore health remains exact (`1,420` SQLite rows, `1,420` FAISS
vectors, `1,420` FTS rows, `100.0%` coverage), so the stale-FAISS failure mode
is not active in this run. W8 itself remains open until a replayable candidate
becomes keepable and later receives sequential confirmation plus fresh
promotion-eval evidence. The next quiet-window evidence runs are DS-E1 KV
measurement, J12 think-loop probe, A9 contrast-replan collection,
`real_suite_v1`, then W8/Fable readiness reports. The same boundary reloaded the
orchestrator API, so dashboard fixes `554b71af` and `b81f3113` are now served:
tap-inferred holders stay visible when `/proc` reports the same physical holder,
and snapshot region-lock frames use the fresh scanner rather than the TTL cache.

**Prior checkpoint - 2026-07-05T23:58Z W8 local-planner canary live**:
AutoPilot is live as PID `3267768`; latest observed checkpoint is trial `1196`
`planner_invoke` with `--max-trials 3000`,
planner hints, tool sentinels, W6 audit accrual, sequential verdicts, and W4-W6
authority env. The running daemon is on orchestrator `a13a2948` and uses the
routine local planner path: `AUTOPILOT_PLANNER_PRIMARY=local_ingest`,
`AUTOPILOT_PLANNER_CRITIC=local_frontdoor`, and
`AUTOPILOT_PLANNER_CRITIC_FALLBACK=claude`. Startup verified StrategyStore
search health (`1,420` SQLite/FAISS/FTS rows, `100.0%` coverage).

The stale `2935890` / `local_worker` / Codex-critic restart target is
superseded. Orchestrator `3364bdd7` repaired the W8 critic-reject loop so W8
candidate-generation pressure rewrites fallback seed/deep/prune deferrals to a
replayable `numeric_trial` or one-flag `structural_experiment` before the
reject-loop guard. Orchestrator `a13a2948` repaired the empty-param contract:
a new `numeric_trial` with `params={}` is an Optuna request, while historical
rows that stayed empty remain unreplayable as logged. W8 only counts the row
after dispatch journals concrete applied params.

The first post-fix planner turn exercised the path: `local_ingest` drafted an
invalid no-op structural experiment, `local_frontdoor` rejected it, W8 fallback
substituted `numeric_trial` on `chat_pipeline`, and NumericSwarm materialized
`chat.try_cheap_first_quality_threshold=0.8742715026951258` before restarting
the API and entering T1 eval. Trial `1194` then failed safety on a `tool_use`
suite regression (`-1.200` vs `-0.600` threshold), was reverted, and
auto-blacklisted only the exact concrete `chat_pipeline` param. This proves the
local draft/local critic safety loop can recover into a replayable W8 candidate
attempt, but W8 remains open until a later candidate becomes keepable and
receives sequential confirmation plus fresh promotion-eval evidence.
Trial `1195` then invalid-skipped `structural_experiment` `graph_router=true`
because that exact action was already auto-blacklisted.

Clarification: ordinary `seed_batch`, `deep_eval`, and `structural_prune` are
not globally invalid AutoPilot strategies. They are currently unavailable only
for the specific W8 candidate-generation blocker because they cannot create the
replayable candidate row W8 needs. They remain valid for coverage, T2/T3
validation, and non-W8 work.

**Prior status — 2026-07-04T21:24Z W8 authority-env checkpoint**: W4/W6 authority wiring remains current, and AutoPilot is live as PID `1122670` at trial `1146` with `--max-trials 2000`, launched through `scripts/autopilot/start_fable_authority_daemon.py` in `epyc-orchestrator` `07883e63`. The launcher enforces `AUTOPILOT_SEQ_VERDICT=1`, W6 audit flags, `AUTOPILOT_PLANNER_HINTS=1`, `AUTOPILOT_TOOL_SENTINELS=1`, planner timeout `600`, and stepping stones. Strict Fable gate smoke (`fable5_gate_report.py --json --strict --require-current-code`) is clean: `ready=true`, blockers `[]`, and the only active next action is `collect_w8_promotion_eval_evidence`; phase health is current-code clean at trial `1146` in `planner_invoke` with `prompt_chars=62902`. The immediately prior bare-env daemon PID `3796930` was stopped after Fable detected missing authority/tool env; recovery journaled trial `1137` as `autopilot_killed_mid_trial`. `epyc-orchestrator` `0a6336c7` fixes the last W8 replay/report mismatch found in trial `1135`: benign AP-24 `keep_revert_decision=excluded` rows that are still `seq.state=accumulating` are now replay-eligible in AutoPilot, while reverted or failure-bearing excluded rows remain terminal. This aligns the live replay selector with the earlier report-plane fix `076699ff`, so the six stale accumulating W8 candidates are no longer silently skipped. The remaining W8 blockers are evidence, not wiring: `combined_E_below_required`, `fresh_promotion_eval_required`, and `seq_confirmation_required`. `epyc-orchestrator` `9b7a9ebe` closes the last StrategyStore startup-only path by refreshing planner-hint prompt rows and convention bindings before each controller prompt; with `AUTOPILOT_PLANNER_HINTS=1`, newly seeded StrategyStore rows are visible to planner prompts each turn. `epyc-orchestrator` `8185c0f7` extends `restart_readiness_report.py` with `--require-current-code`, phase heartbeat path/staleness controls, and Fable strict follow-up wiring, so W4/W6 restart/cutover checks fail closed when the live AutoPilot process predates runtime source changes.

**Current checkpoint — 2026-07-05T14:00Z**: AutoPilot is live as PID `2370903`
after the FAISS, tool-sentinel, and numeric-candidate harness repairs.
`phase_health_report.py --json --require-current-code` reports `status=active`,
trial `1168`, `phase=planner_invoke`, `code_stale=false`, blockers `[]`,
planner hints enabled, sequential verdict enabled, W6 audit accrual enabled,
and tool-sentinel env active. The API was reloaded with
`AUTOPILOT_TOOL_SENTINELS=1` plus `ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT=1`, and
sampled worker attestation passed across six workers. The indexed episodic
FAISS mirror is now exact after orchestrator `a0148edd`: `526,729/526,729`
indexed vectors, matching `id_map.npy` and `reembedded.npz`, `100.0%` live
overlap, and `0` missing/stale IDs. Orchestrator `4400df02` constrains stale
broad numeric-surface blacklists to explicit human-scoped surface bans or
concrete params, so W8 candidate generation is no longer exhausted by stale
surface-level skips. Orchestrator `8be68732` fixes the REPL-pinned
tool-sentinel prompt contract so sentinels demand executable
`TOOL("get_eval_secret", ...)` code. Orchestrator `6a0d60af` normalizes
planner-friendly numeric params such as `keep_ratio` into applicator keys like
`kv.keep_ratio` and returns structured skip outcomes instead of handler no-ops.
Trial `1167` exposed the pre-fix `keep_ratio` handler no-op and should be read
as harness-bug evidence, not negative `kv_compaction` evidence. Trial `1156`
completed as T3 `deep_eval` evidence but is not W8 replayable because
`deep_eval` is observational. Trial `1158` refuted the latest W8 replayable
candidate, and trial `1159` was infrastructure-poisoned while the CPU stack was
down. Current W8 state remains blocked on the real next action:
`w8_candidate_generation_required: no replay-eligible accumulating candidate`.
Fresh promotion-eval evidence and seq confirmation are still absent until
AutoPilot produces a new keepable, replayable `numeric_trial` or
`structural_experiment` candidate.

**Prior checkpoint — 2026-07-05T05:34Z**: AutoPilot is live as PID `1634689`
after the trial `1153` completion / trial `1154` boundary restart. Stale PID
`1527127` was paused at the boundary, terminated with SIGTERM, and verified
gone. Gate-3 hard tool telemetry passed, the API is reloaded with
`AUTOPILOT_TOOL_SENTINELS=1`, and `phase_health_report.py --json
--require-current-code` reports `status=active`, trial `1154`, phase
`planner_invoke`, `code_stale=false`, planner hints enabled, sequential
verdicts enabled, and W6 audit accrual enabled. Orchestrator `026f8e29` is now
live in the daemon planner-evidence path and surfaces aggregate W8
replay-pressure. Orchestrator `a53a74ad` fixed the remaining W8 report/selector
mismatch: the trajectory report now checks journal `config_snapshot` payloads
the same way live AutoPilot replay selection does, so empty-params
`numeric_trial` rows and `seed_batch` candidates are not treated as
replay-eligible. Current W8 state remains blocked on the real next action:
`w8_candidate_generation_required: no replay-eligible accumulating candidate`.
Fresh promotion-eval evidence and seq confirmation are still absent; W8 needs a
new keepable, replayable `numeric_trial` or `structural_experiment` candidate
before promotion evidence can accrue. Orchestrator `c7590be6` enriches
default-off BSV observe signatures with already-journaled tool/route/latency
process signals, still observe-only and outside the authority path. Orchestrator
`9a6815c8` makes `deep_eval tier=3` the concrete planner example for thin T3
workflow coverage/frontier evidence while preserving tier 2 for
comprehensive/W8 promotion-eval evidence. Orchestrator `231e5050` makes W8
planner evidence spell out that `seed_batch` candidates are observational and
unreplayable; orchestrator `fd9dd3bd` adds `planner_evidence.py` to the
phase-health current-code drift guard.

**Prior deployment note — 2026-07-05T05:44Z/06:00Z**: Orchestrator `0dd63df9`
tightens the W8 replay-pressure prompt text after trial `1154` selected
`structural_prune` while W8 candidate generation was the live blocker.
`structural_prune` remains valid as an AutoPilot action, but it is not
replayable under the W8 fresh-promotion contract; W8 replay accepts only
`numeric_trial` with non-empty applied `params` or `structural_experiment` with
non-empty `flags`. Trial `1154` reached its boundary, reverted, and PID
`1671008` ran current code with this guidance until the later trial `1155`
boundary restart recorded above.

**Prior report — 2026-07-04T20:58Z**: live strict Fable smoke after the `0a6336c7` restart reported `ready=true`, blockers `[]`, phase trial `1137`, W8 stale accumulating count `6`, and next actions `collect_w8_promotion_eval_evidence` plus `activate_tool_use_sentinel_lane`. The selector smoke over the current journal chose stale candidate `a5dd4182e654c21e` from source trial `932`, proving the replay lane can drain benign excluded accumulating candidates. That daemon was later found to be missing the authority/tool env and was replaced by PID `1122670`. W8 remains not promotable until a replayed candidate reaches joint sequential confirmation and then passes the fresh promotion eval.

**Current-code readiness guard — 2026-07-04T11:10Z**: live smoke of `restart_readiness_report.py --json --strict --require-seq-cutover --require-w6-audit --require-current-code` returned `restart_ready=true`, blockers `[]`, `phase_health_ok=true`, `phase_health_status=active`, `phase_health_trial_id=1119`, `phase_health_code_stale=false`, `seq_cutover_ready=true`, and `w6_audit_cutover_ready=true`. The aggregate Fable report with `--require-current-code` also keeps the `w4_w6_restart_cutover` section ready; remaining blockers are unrelated DS-E1/A9 gates.

**Prior report — 2026-07-03T15:55Z**: refreshed artifacts `epyc-orchestrator/orchestration/reports/seq_readiness_20260703T152547Z.{json,md}`, `restart_readiness_20260703T152547Z.json`, and `fable5_gate_report_20260703T152547Z.{json,md}` kept W4/W6 ready (`trusted_vectors=221/120`, `seq_shadow_rows=144/30`, W6 audited rows `58/30`, `gaming_alarm=false`, restart readiness `true`). W8 remained evidence-bound rather than code-blocked: latest seq trial `1086`, candidate `968b0a9da524bdbe`, `combined_E=0.932744` versus required `100.0`, `seq_state=accumulating`, no pending/finalized fresh promotion eval, and open requirements `combined_E_below_required`, `fresh_promotion_eval_required`, `seq_confirmation_required`. Trajectory artifact `epyc-orchestrator/orchestration/reports/w8_promotion_trajectory_20260703T155509Z.{json,md}` showed `143` W8 snapshots across `35` candidates, `2` active recent replays, `5` refuted candidates, and `22` stale accumulating candidates.

**Historical status — 2026-06-20 W4/W6 accrual context**: W1/W2/W3/W5 are landed, W7 game-layer hardening is complete, and W4 default-off mechanism + shadow wiring are live but authority was disabled. With `AUTOPILOT_SEQ_VERDICT` off, runtime behavior stays legacy. With it on, AutoPilot can dual-log sequential shadow rows, thread per-question/task-rate evidence through central and action-local gates, journal failed-trial seq blocks, and only finalize baseline promotion after the fresh-eval/update-baseline path accepts. Current blocker is evidence volume plus W6 transfer risk, not missing code: the current aggregate restart-readiness fold after trial `902` reports trusted vectors `68 / 120` and seq shadow rows `16 / 30`. The same report includes W6 audit cutover status from `epyc-orchestrator` `9a634a95` and trailing-window semantics from `ff4864ed`: `w6_audited_trial_count=38` crosses the default `30` row minimum, but `--require-w6-audit` still fails because the trailing-30 W6 gaming alarm is triggered (`potential_overfit_divergences=6`; cumulative divergences `7`; `619c1f6d` reports `28` future clean audited rows needed to age active alarm events out if no new divergences occur). `epyc-orchestrator` `2a5454b4` now makes W6 audit cutover evidence use the same explicit trust metadata as sequential readiness, excluding bug-corrupted, skipped/invalid, and tier-0 audit-bearing rows; the live fold currently reports `w6_raw_audited_trial_count=38`, `w6_audited_trial_count=38`, and `w6_untrusted_audited_trial_count=0`, so the current alarm is not caused by an explicitly untrusted audit row. Trial `900` increased core quality versus trial `899` but dropped audit quality from `2.100` to `1.500`, so it strengthened the hold rather than supporting cutover; trial `901` recovered audit quality to `2.400` but does not clear the active/cumulative W6 alarm or sample-size gates, and trial `902` advanced sequential shadow progress without clearing cutover readiness. The 2026-06-20 accrual window exposed live-eval fanout contamination when the stack was full-only: trials `889/890` produced broad 5xx/error/crosstalk symptoms, so `epyc-orchestrator` `c13e5ae` now caps default eval concurrency by reachable live fleet instances and keeps bounded `error_detail` in compact question rows. Trial `894` later wedged mid-`deep_eval`; `epyc-orchestrator` `97fa2843` added a phase-health report, the stale PIDs were killed after ordinary restart readiness passed, and recovery journaled `894` as `autopilot_killed_mid_trial`. `epyc-orchestrator` `63e4dcba` exposes the same phase-health classification in dashboard process status, `887f50f5` refreshes the phase heartbeat from eval question progress, `b7f75e47` surfaces the health field in the dashboard UI, and `418d2599` will surface eval batch progress in phase/Fable5 reports after the next safe AutoPilot restart. `epyc-orchestrator` `092abb39` repairs direct `seq_readiness_report.py` CLI execution from the repo root; live direct JSON smoke now reports the same blockers (`68 < 120`, `16 < 30`) instead of failing on imports. The active bounded W4/W6 accrual run is `/mnt/raid0/llm/tmp/autopilot_w4w6_codex_pair_after_alias_20260620T172927Z.log`, wrapper PID `1091014`, Python PID `1091018`, `--max-trials 930`; durable rows are recorded through trial `902`, and the current heartbeat shows trial `903` active in `dispatch_action`. Latest artifacts are in `epyc-orchestrator` `a4286a2d` (`seq_readiness_20260620T191636Z`, `w6_audit_block_20260620T191636Z`, and `fable5_gate_20260620T191636Z`).
**Pre-reboot snapshot — 2026-06-28T21:35Z wrap-up**: supersedes older trial-902/run-to-1048 counts in the status history above. AutoPilot is live under the v6+iqk era with `--max-trials 2000`, corrected W4/W6 env, and activated A10 planner hints (`AUTOPILOT_PLANNER_HINTS=1`); current pre-reboot Python PID is `2143322`, with latest observed runtime state trial `1051`, phase `planner_invoke`. Sequential sample volume is sufficient (`trusted_vectors=193/120`, `seq_shadow_rows=116/30`), archive authority is aligned through journal max `1050`, and the guarded baseline seed append made the baseline ledger fold ready. W6 audit cutover now also passes inside the v6 era (`w6_audited_trial_count=32/30`, `gaming_alarm=false`, `gaming_alarm_clearance_clean_trials_required=0`). Authority was still disabled then because no deliberate cutover had been performed. Current proof artifact: `epyc-orchestrator/orchestration/reports/restart_readiness_20260628T213549Z.json`. The next decision gate after reboot is to rerun `restart_readiness_report.py --json --strict --require-seq-cutover --require-w6-audit`, then run/review the disagreement/cutover report before enabling sequential verdict or baseline authority.
**Created**: 2026-06-12
**Priority**: HIGH — the keystone change; owner of the Queue-3 restart bundle
**Spec**: [fable5-findings-01-impl-plan.md](../completed/fable5-findings-01-impl-plan.md) Phase 1 + Phase 5, and [fable5-findings-01c-sequential-verdict-spec.md](../completed/fable5-findings-01c-sequential-verdict-spec.md) (the full e-process: update rule, thresholds, state schema, exact wiring sites) — read before claiming any waypoint
**Related**: [bulk-inference-campaign.md](bulk-inference-campaign.md) Queue 3 — **J11/BSV-2 + K-SKILL-1 co-land at the same restart, flag-isolated** (`AUTOPILOT_BSV2_ACCEPT_GATE` / `AUTOPILOT_SKILL_EFFICACY_GATE`) · [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md) (Phase 2.0/2.1 prereqs for full power) · [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) · [../../MEASUREMENT.md](../../MEASUREMENT.md) §P-QUAL-T1 (decision rule = this handoff)
**History**: [evidence-plane-ledger-and-sequential-verdicts-history-through-2026-06-19.md](../archived/evidence-plane-ledger-and-sequential-verdicts-history-through-2026-06-19.md) preserves completed W1-W7 implementation chronology compacted out of this active handoff.

> **Live visibility update — 2026-06-20.** `epyc-orchestrator` `9cc932fe`
> (`Surface live eval progress from phase reports`) makes
> `build_phase_health_report()` fill missing in-flight eval counters from the
> active `logs/autopilot.log` tail when the heartbeat belongs to the live phase
> path and the running process predates structured eval counters. Heartbeat
> counters still win when present, and log-tail matches are trial-scoped. Live
> smoke during trial `902` reported `T2 450/500 (70% correct)` in both
> `phase_health_report.py --json` and the aggregate Fable5 phase section,
> without restarting or disturbing the W4/W6 accrual process.
> `epyc-orchestrator` `f5b1898a` then surfaced threshold-derived remaining
> counts in restart/Fable5 reports. Current live smoke after durable trial `902`
> shows `52` trusted-vector trials and `14` sequential-shadow rows still needed
> for N2 sample-size gates, while
> W6 audited rows are above floor (`38/30`) but blocked by the gaming alarm.
> `epyc-orchestrator` `619c1f6d` adds the W6 alarm clearance horizon: live
> smoke reports `28` future clean audited trials are needed to age the active
> alarm events out of the trailing-30 window, assuming no new divergences occur.

> **Live visibility update — 2026-06-21.** `epyc-orchestrator` `4cfe6567`
> (`Surface W4/W6 cutover horizon`) adds a combined strict-cutover horizon to
> `restart_readiness_report.py` and `fable5_gate_report.py`. The horizon is a
> read-only lower bound over remaining trusted-vector rows, seq-shadow rows,
> W6 audited rows, and W6 alarm-clearance rows; it does not change gate
> semantics. Live smoke during active trial `916` reports trusted vectors
> `81/120` (`39` remaining), seq-shadow rows `29/30` (`1` remaining), W6 audited
> rows `51/30` (`0` remaining), W6 alarm clearance `26`, and combined horizon
> `39` with blocker `seq_trusted_vectors`.
> Follow-up live smoke after durable trial `916` reports trusted vectors
> `82/120` (`38` remaining), seq-shadow rows `30/30` (`0` remaining), W6 audited
> rows `52/30` (`0` remaining), W6 alarm clearance `25`, and combined horizon
> `38` with blocker `seq_trusted_vectors`.
> `epyc-orchestrator` `bfd29e96` (`Wait for seeding responses after idle slots`)
> fixes a HIGH-risk seeding observability/evidence-quality issue in
> `_call_orchestrator_with_slot_poll`: after a slot reports idle while the HTTP
> request is still pending, the wrapper now gives the orchestrator response a
> short completion grace before emitting `slot_idle_orphan`. This targets false
> `[INFRA_SKIP] worker_general` rows without changing reward semantics.
> Follow-up live smoke after durable trial `917` reports trusted vectors
> `83/120` (`37` remaining), seq-shadow rows `31/30` (`0` remaining), W6 audited
> rows `53/30` (`0` remaining), W6 alarm clearance `29`, and combined horizon
> `37` with blocker `seq_trusted_vectors`.
> A guarded stop-window watcher is now resident as PID `1862928`. It waits for
> the current AutoPilot Python PID `1091018` to exit, requires
> `trial_counter >= 930`, `paused=False`, and no `_dispatch_deficiency`, runs
> ordinary `restart_readiness_report.py --json --strict`, appends the prepared
> baseline seed only if the report says append-ready/required with exact guard
> values, then restarts the same W4/W6 collection flags to
> `autopilot.py start --max-trials 970`. Runtime logs are under
> `/mnt/raid0/llm/tmp/w4w6_seed_then_continue_20260621T0358.log`. The watcher
> runs from a temp Python script so pgrep-based AutoPilot guards see only the
> real `autopilot.py start` process.

> **Live update — 2026-06-21T15:40Z.** The resumed W4/W6 accrual process is
> active on trial `934` T2. Latest strict readiness remains blocked at trusted
> vectors `97/120` (`23` remaining), seq shadow rows `44/30`, W6 audited rows
> `65/30`, and W6 alarm clearance `23` clean audited trials. Direct W6 audit
> reporting now matches the aggregate gate: `epyc-orchestrator` `0c593b23`
> defaults standalone `audit_block_report.py` CLI runs to a trailing-30 audited
> trial alarm window, while preserving all-history library semantics for
> explicit callers. Live direct smoke reports window `30/30`,
> `gaming_alarm=true`, clearance `23`, and `12` cumulative divergences.

## Start Here

1. Let AutoPilot PID `3935151` continue current trial `1217` unless phase health
   fails. This is the current-code-clean forced replay of source trial `1197`;
   the next target is candidate outcome evidence, not another restart or a
   repeat AP-9 investigation.
2. Watch provider traces for local-planner quality.
   Under W8 pressure the prompt menu should no longer expose `seed_batch`,
   `deep_eval`, or `structural_prune` schemas. If local drafts still propose
   unavailable actions, repair the drafter prompt/normalizer or add a measured
   two-stage local provider rather than weakening the W8 dispatcher guard.
3. Finish W8 promotion eval evidence: orchestrator `33c16b47` makes forced fresh-promotion deep evals replay the pending candidate's exact numeric params or structural flags and fail closed for unreplayable candidates. Orchestrator `b62bc205` adds the Phase-2.4 confidence-interval non-regression guard: fresh promotion evals now need effective paired-question evidence (`r_eff`) and a one-sided delta lower bound that excludes regression before finalization, with the CI object recorded into promotion state. Orchestrator `2aa3b40c` wires the P-QUAL-PROMO draw contract: forced promotion evals use trial-seeded fresh T2 draws, n bounded to 200-500, qids seen in the last 60 days excluded, broken/artifact suites excluded via the latest item-analytics suite-health table, and fail closed if fewer than 200 fresh healthy scoreable questions remain. Continue live accrual until AutoPilot produces a keepable replayable candidate, then collect sequential confirmation and fresh promotion-eval evidence.
4. Run/review the disagreement/cutover report as follow-up documentation, not as a prerequisite to the already-executed authority restart.
5. Coordinate any future restart-bundle accept-path flips with J11/BSV-2 and K-SKILL-1 because all three are accept-path gates.

## Why

Per-question outcomes are computed every trial and discarded at aggregation — pairing is free
statistical power already paid for (spec §2.2). Persisting the 43-bit vector enables McNemar
replay of 120 historical keep/revert decisions, and the 01c e-process (anytime-valid under the
planner's own optional stopping/continuation) replaces the single-shot MAD argument:
`mad_noise` and `reproduction_confirmed` collapse into `accumulating`, and the t775 ratchet
class becomes impossible by construction (baseline raises require `confirmed_improvement`).
This handoff owns the restart bundle: ledger + verdicts + the two campaign accept-path gates
land at ONE autopilot restart, each behind its own flag.

## Waypoints

- [x] **W1 — qid + outcome vectors** (impl 1.1–1.2, ~1–2 days): derived stable `qid` from `suite + "\0" + prompt`; `eval_tower._aggregate` carries compact `question_results` on `EvalResult`; AutoPilot mirrors it to `eval_details.question_results`; TSV untouched. **Landed live 2026-06-13** on `epyc-orchestrator` branch `fix/substring-scorer-digit-separators` as `22a3874a` (`Journal per-question eval vectors`) after focused restart-bundle validation. Original stale-lineage worktree remains at `/mnt/raid0/llm/tmp/paired-stats-worktree`, branch `feat/paired-question-stats`, commit `3c17460`; prior current-lineage checkpoints are retained for provenance. Trusted vector history restarts at the clean epoch: `#799/#800` each carried 55 question results; `#789-#797` vector rows are quarantined and must not feed W4 evidence.
- [x] **W2 — paired replay tool** (impl 1.3, ~1 day, zero inference): `scripts/autopilot/paired_stats.py` (`summary`, `mcnemar`, `config-vs-baseline`). Decision gate: after ~2 weeks of vectors, replay historical keep/revert — ≥30% verdict flips ⇒ proceed to W3; <10% ⇒ hold and report (findings-01 §4). **Landed on current orchestrator branch 2026-06-13** as `9f6fc8e` (`Add paired question replay stats`), a clean cherry-pick of restart-bundle commit `c67575b`; validation: py_compile, `tests/unit/test_paired_stats.py` (3 passed), ruff on touched files, diff-check, and historical pre-restart live-journal summary `667 rows / 0 vector trials`. Follow-up `d21bbee` makes `iter_journal_rows()` fold append-only supersession events and drop non-trial event rows before paired-stat inputs. Trusted clean-epoch vector trials currently are `#799/#800`; W4 evidence should use the supersession-aware read path.
- [x] **W3 — sequential_verdict.py** (01c §1–2,§4; 2–3 days): landed in `epyc-orchestrator` `7e6ac9c` as pure `src/autopilot_core/sequential_verdict.py` plus package exports and `tests/unit/test_sequential_verdict.py`. Implements capped-Kelly e-process state, baseline per-qid profile statistic, rate non-inferiority transform, JSON-ready `seq` journal block, and rebuildable per-candidate view from journal rows or `(trial_id, z)` observations. Acceptance: 100,000-run deterministic null simulation returned false-positive rate `0.00551` at α=0.05; focused validation `26 passed`.
- [x] **W4 — joint verdict + wiring** (01c §3,§5): default-off mechanism, central AutoPilot shadow wiring, baseline/fresh-eval finalization, cached-verdict upgrade, fallback reselection, action-local gate threading, failed-trial denominator repair, fresh-eval pre-dispatch repair, and the post-reboot authority cutover are live. Current strict readiness on 2026-07-02 reports baseline authority enabled from `ledger_fold`, archive authority aligned through journal max `1061`, sequential cutover ready with trusted vectors `202 / 120`, and seq shadow rows `125 / 30`. Remaining authority tail is W8 promotion-eval evidence, not W4 wiring/cutover.
- [x] **W5 — planner power line + candidate blocks** (impl 1.5 + 01c §5.3, ~half day): landed in `epyc-orchestrator` `0bc1f32` as `src/autopilot_core/planner_evidence.py` plus the `### Evidence Power and Sequential Candidate Status` planner section after Pareto geometry. This is planner-only/read-only context: no safety gate, baseline authority, archive authority policy, or inference behavior changed. Dispatch-gate policy remains future work with W4/cutover decisions.
- [x] **W6 — shadow rollout + cutover** (01c §5.5, 2 weeks passive): dual-log `seq` alongside MAD verdicts; the post-reboot cutover is live under `AUTOPILOT_SEQ_VERDICT=1`. Current strict readiness on 2026-07-02 reports `seq_shadow_rows=125/30`, W6 current-era audited rows `41/30`, trailing-window `gaming_alarm=false`, `0` potential overfit divergences, and no W6 blockers. Continue W8 promotion-eval evidence collection and fail closed on any future strict-readiness regression or instrument-era reset.
- [x] **W7 — game layer** (impl 5.1–5.3, 2–3 days): critic measurement-view foundation landed in `epyc-orchestrator` `41c5c71` (`build_critique_prompt` stops echoing the 80KB planner prompt and now carries bounded power/constraint context); server-side production eval sampling clamp landed in `7492cf5` (`EvalTower.evaluate()` pins T1/T2 `n`/`seed`, dispatcher rejects malformed `deep_eval`, and calibration uses direct tier helpers for operator overrides); audit-stream gaming alarm landed in `8e4b1ec` as read-only `gaming_alarm` / `gaming_events` report fields; PEAF surprise budget credit landed in `4b09661` via `information_rate` / `budget_rate` while preserving legacy Pareto `rate`; per-question diff/provenance context landed in `749d38f` by adding truthy-only compact row flags (`scoring_method`, route/tools, error/partial/degraded/exogenous/retry markers) and planner evidence summaries (`diff=prev#...`, suite/partition counts, provenance flags) without exposing prompt or answer text.
- [x] **W8a — candidate-generation deferral guard**: orchestrator `854eff06` prevents W8 pressure from being spent on unreplayable ordinary deferrals by replacing `seed_batch`, `deep_eval`, `structural_prune`, and invalid structural actions with the first unblacklisted numeric trial fallback unless a sequential due-action owns the turn; planner evidence now states that new Optuna numeric trials are replayable when dispatch journals applied params. ✅ 2026-07-05
- [x] **W8a.1 — local-planner/W8 fallback contract repair**: orchestrator `3364bdd7` converts critic-fallback seed/deep/prune deferrals into replayable W8 candidate attempts before the reject-loop guard; orchestrator `a13a2948` teaches the critic/repeat shield that empty `numeric_trial.params={}` is an Optuna request, not the final replay artifact. Live AutoPilot PID `3267768` verified the path through `local_ingest` draft, `local_frontdoor` critique, W8 fallback, and concrete `chat_pipeline` applied param `0.8742715026951258` in trial `1194`; the candidate itself was reverted for `tool_use` regression, so this closes wiring proof but not W8 evidence. ✅ 2026-07-05
- [x] **W8a.2 — selectable-action provider coordination**: orchestrator `1639748a` threads the live `selectable_action_types` allowlist into `plan_with_providers()`, rejects known-but-currently-unavailable drafts before critique, applies the same guard to critic revisions, and adds regression coverage for the W8 `deep_eval` drafter waste case. The commit is pushed/indexed and live in AutoPilot PID `3795561`; trial `1210` verifies the post-deploy local `frontdoor` draft / local `worker` critique path before the higher-tier guard forced T3. ✅ 2026-07-06
- [x] **W8a.3 — outcome-stall dispatch guard**: orchestrator `9522b76e` stops the higher-tier probe guard from overriding an already frontier-moving planner action under frontier-stall pressure, and `78ae65e6` adds a bounded outcome-progress fallback that forces a metric-bearing numeric trial only when frontier admission is stale and the selected action is seed/eval/housekeeping rather than a frontier-moving action. Focused validation passed (`140` AutoPilot action/phase/provider tests), ruff, `py_compile`, `git diff --check`, push, and GitNexus refresh. A boundary restart loaded the patch; W8a.4 below is the current live replay-dispatch checkpoint. ✅ 2026-07-06
- [x] **W8a.4 — forced replay/AP-9 dispatcher repair**: orchestrator `e3b13edd` keeps W8 replay pressure active while replay/confirmation remains open, allows materialized multi-param NumericSwarm candidates to be replayed as one force-matched candidate, and bypasses AP-9 only when the current action exactly matches `seq_candidate_replay_forced`. Trial `1213`-`1216` skips exposed the seam; the state was cleaned without deleting journal evidence, GitNexus refreshed, focused validation passed (`203` tests + Ruff + diff-check), and live PID `3935151` is evaluating trial `1217` with the intended AP-9 replay bypass. ✅ 2026-07-06
- [ ] **W8b — live candidate evidence after guard deploy**: continue W8 candidate attempts under the live selectable-action coordinator plus outcome-stall guard. Verify a keepable replayable candidate, then collect sequential confirmation and fresh promotion-eval evidence. The old restart/local-worker verification clause is superseded by the current `local_frontdoor`/`local_worker` canary and selectable-action coordinator.

## Gates & pitfalls

- Restart discipline: W1 + J11/BSV-2 + K-SKILL-1 shared the 2026-06-13 API reload boundary and are flag-isolated for attribution. Future authority flips still need a deliberate restart boundary and attribution plan.
- W4/W6 are now gated on readiness, not code availability. Do not wire authority on vibes: collect enough trusted vectors and seq shadow rows, then run the disagreement/cutover report.
- GitNexus impact for `EvalTower._aggregate` is HIGH (19 impacted symbols/modules across all eval/action paths on the 2026-06-13 current index), so W1 writer changes should land in a deliberate restart-bundle branch with focused aggregate/journal compatibility tests, not as opportunistic mid-run edits.
- Update the e-process per TRIAL, never per question (within-trial outcomes are dependent — 01c §1); core-version or policy-version change resets all `accumulating` candidates.
- Works on the accidental 43-set at lower power, but instrument-repair W4/W5 should land first or R_eff stays ~10–14.
- Sequential machinery credits improvements only — never let it delay damage control (01c §3).

## Progress

- 2026-06-12: W1+W2 original branch-ready at `epyc-orchestrator` `feat/paired-question-stats` commit `3c17460`. Validation: 22 focused eval/journal/paired-stat tests passed; full ruff on new/nearby files passed; `ruff --select F821` on touched AutoPilot files passed; `py_compile`; `git diff --check`.
- 2026-06-12: Rebased/cherry-picked W1+W2 onto the current paused live lineage as `feat/paired-question-stats-current` commit `8dbdba5b`. Validation: `python3 -m py_compile` on touched AutoPilot files passed; focused suite `tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py` -> 30 passed, 1 pytest config warning; `git diff --check HEAD~2..HEAD` passed. Full ruff/format checks are not claimed because current-lineage `scripts/autopilot/autopilot.py` has pre-existing unused-import and formatting debt outside this branch's behavioral delta. Residual: merge/deploy at the restart bundle, then collect vector-bearing trial history before W3/W4.
- 2026-06-13: Refreshed W1+W2 onto current live lineage `ab5df87` as `feat/paired-question-stats-restart-current` tip `0855e3b`. GitNexus refreshed first; impact for `EvalTower._aggregate` was HIGH and `EvalResult` LOW, so this remains restart-bundle-only. Validation: `python3 -m py_compile scripts/autopilot/autopilot.py scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py scripts/autopilot/paired_stats.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py` passed; `uv run --with pytest pytest -q tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_item_analytics.py` -> 34 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/autopilot/paired_stats.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_item_analytics.py` passed; `git diff --check HEAD~2..HEAD` passed; `paired_stats.py --journal /mnt/raid0/llm/epyc-orchestrator/orchestration/autopilot_journal.jsonl summary` -> 667 rows / 0 vector trials.
- 2026-06-13: Ported J11 observe-only BSV diagnostics onto the combined restart branch as `feat/restart-bundle-bsv-observe-current` tip `4c0e1b6`. Resolved the only conflict by preserving both N2 `question_results` and task-rate shadow fields alongside `eval_details.bsv_observe`. Validation: `python3 -m py_compile scripts/autopilot/autopilot.py scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py scripts/autopilot/paired_stats.py scripts/autopilot/bsv_observe.py tests/unit/test_paired_stats.py tests/unit/test_bsv_observe.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py` passed; `uv run --with pytest pytest -q tests/unit/test_bsv_observe.py tests/unit/test_behavior_signature.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_item_analytics.py` -> 64 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/autopilot/paired_stats.py scripts/autopilot/bsv_observe.py tests/unit/test_paired_stats.py tests/unit/test_bsv_observe.py tests/unit/test_behavior_signature.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_item_analytics.py` passed; `git diff --check 0855e3b..HEAD` passed.
- 2026-06-13: Rebased the restart bundle onto live branch `924ca50` after DCP-6a and K-SKILL default-off wiring landed. New N2-only tip: `feat/paired-question-stats-restart-current` `83cb36c`; new combined N2+J11 observe tip: `feat/restart-bundle-bsv-observe-current` `c20985e`. Validation: `python3 -m py_compile` on AutoPilot/eval/paired/BSV/K-SKILL changed surfaces passed; `uv run --with pytest pytest -q tests/unit/test_bsv_observe.py tests/unit/test_behavior_signature.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_item_analytics.py tests/unit/test_autopilot_actions.py tests/unit/test_skill_efficacy.py` -> 107 passed, 1 pytest config warning; focused `ruff check` passed; `git diff --check 924ca50..HEAD` passed; paired-stats smoke over the live journal still reports 667 rows / 0 vector trials.
- 2026-06-13: After W7 planner-session hygiene landed live at `9e5d861`, rebased the restart bundle again. New N2-only tip: `feat/paired-question-stats-restart-current` `d32fafd`; new combined N2+J11 observe tip: `feat/restart-bundle-bsv-observe-current` `c63816b`. Validation: `python3 -m py_compile` on AutoPilot/eval/paired/BSV/K-SKILL/planner changed surfaces passed; `uv run --with pytest pytest -q tests/unit/test_bsv_observe.py tests/unit/test_behavior_signature.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_item_analytics.py tests/unit/test_autopilot_actions.py tests/unit/test_skill_efficacy.py tests/unit/test_autopilot_planner_providers.py tests/unit/test_autopilot_planner_coordinator.py tests/unit/test_autopilot_controller_io.py` -> 170 passed, 1 pytest config warning; focused ruff passed; `git diff --check 9e5d861..HEAD` passed; paired-stats smoke over the live journal still reports 667 rows / 0 vector trials.
- 2026-06-13: Landed the W2 replay tool on current orchestrator branch `fix/substring-scorer-digit-separators` as `9f6fc8e` while leaving W1's HIGH-impact writer out of the live branch. Validation: `python3 -m py_compile scripts/autopilot/paired_stats.py tests/unit/test_paired_stats.py`; `uv run --with pytest pytest -q tests/unit/test_paired_stats.py` -> 3 passed; `uv run --with ruff ruff check scripts/autopilot/paired_stats.py tests/unit/test_paired_stats.py`; `git diff --check HEAD~1..HEAD`; `paired_stats.py --journal orchestration/autopilot_journal.jsonl summary` -> 667 rows / 0 vector trials.
- 2026-06-14: W2 replay read path became supersession-aware in `epyc-orchestrator` `d21bbee`. `scripts/autopilot/paired_stats.py iter_journal_rows()` folds append-only supersession events and drops non-trial event rows before paired summaries/McNemar/config-vs-baseline inputs. Regression coverage in `tests/unit/test_paired_stats.py` verifies supersession folding; combined validation with item analytics, task-rate replay, and journal supersession tests passed (`15 passed`), with focused ruff and diff-check clean on touched analytics files.
- 2026-06-13: Refreshed W1 onto the actual current orchestrator HEAD in isolated worktree `/mnt/raid0/llm/tmp/paired-stats-head-worktree`. New branch `feat/paired-question-stats-current-head` tip `22a3874a`, based on `9f6fc8e` (current branch with W2 replay, X-MAS scaffold, ColGREP telemetry, BT cleanup, and controller guidance). Validation: `python3 -m py_compile scripts/autopilot/autopilot.py scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py scripts/autopilot/paired_stats.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py`; `uv run --with pytest pytest -q tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_item_analytics.py` -> 34 passed, 1 known pytest config warning; focused ruff passed; `git diff --check HEAD~2..HEAD` passed; paired-stats live-journal smoke remains 667 rows / 0 vector trials.
- 2026-06-13: Merged/deployed the combined restart bundle onto live orchestrator branch: `22a3874a` W1 vectors, `fd84655e` J11/BSV observe-only, `d89b4a9` BSV review fixes, followed by launch-hygiene commit `954d8fd`. API reload PID `3447078` was healthy and OOM-protected; `paired_stats.py --journal orchestration/autopilot_journal.jsonl summary` reported `667 rows / 0 vector trials` because AutoPilot remained paused. Initial full preflight after `954d8fd` passed 8/9 and exposed a Question Pool capacity gap; `a3ec440` superseded that blocker below.
- 2026-06-13: W4b sampler/preflight follow-up landed as `a3ec440`; API reload PID `3460290` is healthy, OOM-protected, and has tool sentinel/structured output flags in the process environment. Full preflight now passes 9/9: T1 sampled 100/100 unique and T2 sampled 500/500 unique. Gate-3 hard telemetry passed, but the soft `web_research` full `/chat` probe returned 500 after stale `architect_coding` escalation/fallback; SearXNG itself is healthy. Superseded quarantine status: existing AutoPilot rows `#786-#792` are now tagged `resource_contention_20260612`, and state is paused cleanly at `trial_counter=793`.
- 2026-06-13: Stale-role hygiene landed as `a338738` and API reload PID `3486453` passed Gate-3 hard telemetry. The soft probe still returned 500, but the task completed successfully through `frontdoor -> coder_escalation -> architect_general`; repeated health probes showed worker-local six-worker circuit inconsistency. Later single-worker follow-up landed response JSON hardening (`4a7efbe`) and API-boundary failure logging (`c62dbd8`); a bounded soft `web_research` probe stayed slow and was killed by the client with server health still ok and no new 500/traceback. Next vector-history run should start from a clean API process, preferably `ORCHESTRATOR_UVICORN_WORKERS=1`, instead of treating the soft probe as an evidence-plane blocker.
- 2026-06-13: W3 pure sequential verdict module landed as `7e6ac9c`. Validation: `py_compile`; focused `ruff`; `pytest -q tests/unit/test_sequential_verdict.py tests/unit/test_autopilot_core_contracts.py tests/unit/test_paired_stats.py` -> 26 passed; deterministic `empirical_ville_false_positive_rate(runs=100000, horizon=12)` -> `0.00551`. API reload on `7e6ac9c` PID `3531008` passed full preflight 9/9, but Gate-3 hard telemetry stalled twice before first sentinel output and was stopped both times. After the second attempt, `/health` was degraded only by the known `http://localhost:8102` fallback circuit while direct probes stayed healthy and no new 500/traceback appeared. This stall was superseded by `b1985be`; W4 remains the safety-gate/update-baseline wiring step after clean vector-bearing history exists.
- 2026-06-13: Gate-3 hard-only driver hygiene landed as `b1985be` and passed after a fresh one-worker API reload. The contaminated AutoPilot restart window is treated conservatively by operator instruction: rows `#786-#797` are tagged `resource_contention_20260612` except killed placeholders `#796/#798`; runtime projection was restored from clean backup through `#785`, and the polluted Optuna base study was renamed/quarantined. Clean completed rows `#799/#800` each wrote 55 vectors after the repair window, were dominated, and left T1 frontier unchanged. Live state is paused at `trial_counter=801`; W4 remains gated on more trusted vector history rather than code availability.
- 2026-06-14: W5 planner evidence context landed in `epyc-orchestrator` `0bc1f32` (`Add planner evidence context to AutoPilot`). It adds read-only planner evidence context after Pareto geometry and validation passed on the main lane: py_compile; focused ruff; focused pytest `tests/unit/test_planner_evidence.py tests/unit/test_autopilot_system_card.py tests/unit/test_sequential_verdict.py` -> 22 passed; expanded pytest over core contracts/paired stats/archive authority/baseline authority -> 25 passed; preflight 10/10 passed; archive authority strict passes after runtime repair. W4 remains pending for clean vector history and safety-gate/update-baseline wiring.
- 2026-06-14: Clean AutoPilot window after repair ran through `trial_counter=813`; clean rows `#807-#812` include `#808` q=1.98 s=60.1 r=1.00, `#809` q=2.04 s=57.2 r=0.98, `#810` numeric `memrl_retrieval` q=2.04 s=56.7 r=1.00, `#811` q=1.92 s=58.1 r=0.98, and `#812` q=1.98 s=47.1 r=0.98. No infrastructure-collapse signature was observed. Archive repair wrote runtime backup `/mnt/raid0/llm/epyc-orchestrator/orchestration/autopilot_state.json.bak-archive-repair-20260614T045917Z` and restored state/journal match.
- 2026-06-14: Read-only sequential verdict readiness report landed in `epyc-orchestrator` `d446f68` as `scripts/autopilot/seq_readiness_report.py` plus `tests/unit/test_seq_readiness_report.py`. Validation on the main lane: py_compile for new files; ruff for new files; focused pytest `tests/unit/test_seq_readiness_report.py` -> 4 passed; adjacent pytest `tests/unit/test_seq_readiness_report.py tests/unit/test_paired_stats.py tests/unit/test_planner_evidence.py tests/unit/test_sequential_verdict.py` -> 26 passed. Live report over `orchestration` was blocked: trusted vectors 14, raw 21, untrusted 7 (`#789/#790/#791/#793/#794/#795/#797`), seq shadow rows 0, blockers `trusted history <120`, `seq shadow <30`, and no flip-rate denominator. This is W4/W6 readiness/reporting progress only; W4 enforcement and W6 cutover remain pending.

## Reporting

Tick waypoints + one-line progress entry; verdicts claimed per MEASUREMENT.md grammar (`[P-QUAL-T1/seq-v1, E=…, k=…, date]`); on completion delete this handoff's master-index row and move to `completed/`.
