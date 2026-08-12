# AutoPilot: Continuous Recursive Optimization

> **Current checkpoint — 2026-08-10.** AutoPilot is intentionally stopped and inference resources have
> been handed back to the operator. Clean execution-instrument-v10 incumbent evidence is ratified for
> T1=100 (`q=1.500`), T2=500 (`q=1.356`), and T3=160 (`q=1.275`), each at reliability `1.000` and zero
> error rows. The operator applied the atomic E16 ratifier; receipt
> [`ratify_multitier_baseline_v10_20260810.json`](../../artifacts/operator/ratify_multitier_baseline_v10_20260810.json)
> records `ratified_and_applied`, no AutoPilot start, and no model-server change. The verified
> `production_best` checkpoint SHA-256 is `c60364f1295a931a4b4e806d4dffd2138696537f49b15a3a6881c50737c02b19`.
> Next active work is AP-50's decision cockpit; any later AutoPilot restart still requires separate
> explicit permission.

**Resume-precondition — 2026-07-17 (non-inference session diagnosis)**: the ~28h stop on 2026-07-16 was a **DELIBERATE `SIGTERM`** to free the machine for v7 kernel work (`autopilot.log` `Shutdown requested (signal 15)` → `Controller failed (rc=143)`; `agent_audit.log` logs *"Audit experimental v7 kernel worktree … while AutoPilot remains stopped"* seconds later). It is **NOT** a `consecutive_failures` self-halt — `consecutive_failures=2 < safety_gate.MAX_CONSECUTIVE_FAILURES=3` (`safety_gate.py:107`); the persisted `_dispatch_deficiency='consecutive_failures'` marker is stale + self-clearing (`autopilot.py:8687` unconditional pop on `resume`). **No wedge to clear.** Before resuming:
- [x] Bring the `:8000` stack up + verify HEALTHY first (a resume against a dead stack fails every dispatch). ✅ 2026-08-08 — E15 serving and API readiness were verified before the supervised run; subsequent work stops AutoPilot without tearing down the resident stack.
- [x] Address the pre-stop THRASHING or it recurs ✅ 2026-07-28 — BOTH fixed and pushed (orchestrator `4d329002`: baselines with n<5 can no longer certify hard per-suite rollbacks, env-tunable `AUTOPILOT_PER_SUITE_BASELINE_MIN_N`; `24fa1399`: kv_compaction "Expected Attention compression failed" 500s reclassified as per-role uncompactable-skips — root cause was empty-slot preconditions on idle roles, never a real compaction fault; kv_compaction remains a live runtime lever). Resume is now gated only on the E8 baseline signature (`gpu-serving-tie-in-program.md` P0-1/P1-3). ORIGINAL: the loop hit ~10 consecutive-failure rollbacks on 2026-07-16 (trials 1404…1433) from a **small-sample `debugbench` regression** (`n_baseline=2` tripping the −1.5 hard threshold: debugbench 0.0 vs a 3.0 baseline measured on only n=2) + two `kv_compaction` trials hard-failing `500 "Expected Attention compression failed"`. Fix the tiny-n gate / the kv_compaction op before resuming, else it burns compute re-thrashing the same rollbacks. (This rhymes with the `real_suite_v1` small-sample instability the discriminability audit found — see master-index §cross-session (2).)

**Current checkpoint — 2026-07-11T23:25Z**: AutoPilot is running under
supervisor PID `1039445` / child PID `1039446`, with phase health reporting
trial `1318`, `phase=dispatch_action`, `action_type=seed_batch`, and
`ok=true`; log-tail eval progress is T1 `20/65`. The current process is
**not current-code-clean**:
`phase_health_report.py --json` reports `code_stale=true` for
`autopilot.py`, `actions.py`, `controller_io.py`, `eval_tower.py`,
`safety_gate.py`, and `phase_status.py`; no restart/pause was performed by this
audit. Planner routing remains local-first (`AUTOPILOT_PLANNER_PRIMARY=local_ingest`,
`AUTOPILOT_PLANNER_CRITIC=local_frontdoor`, fallback `claude`), and the planner
spend breaker is explicitly off (`AUTOPILOT_PLANNER_SPEND_BREAKER=0`;
`planner_spend_breaker_enabled=false`). Outcome progress is still `attention`
because the latest promotion is stale (`348` trials since promotion). The named
open work in this handoff is
now rollout/validation evidence, not code scaffolding: AP-26 needs an
operator-approved non-RLM vs RLM live comparison, AP-27 needs Ouro/inference
integration review, BSV-2 needs live paired-run evidence before enabling
`AUTOPILOT_BSV2_ACCEPT_GATE`, and BSV-3 enforcement stays default-off/observe
until BSV-2 evidence exists.

**Current checkpoint - 2026-07-14T00:00Z seq-fallback unblock**: AutoPilot is
back on current code with `AUTOPILOT_PLANNER_SPEND_BREAKER=0` and
`code_stale=false`. Orchestrator commit `402e461b` added retryable-aware seed
fallback selection for seq baseline-reference forcing and seq-gate preflight
deferral while preserving manual/token-gated blacklist purge for durable bans.
Live trial `1346` forced the seq baseline-reference draw through retryable
`seed_batch n=50` target `seed_batch_n50_t1317_no_progress_infra`, so
infra-contaminated retry targets are available again without reviving stale
blacklist entries. Validation already passed in the orchestration session:
`uv run --frozen pytest -q tests/unit/test_autopilot_sequential_wiring.py tests/unit/test_autopilot_actions.py`
returned `177 passed`, and `ruff` passed.

**Quiet-window evidence refresh - 2026-07-14T17:22Z (AutoPilot intentionally
stopped by operator)**: no runtime mutation was performed; this was a read-only
evidence pass over the live journal and codified report harnesses. Fresh
artifacts in `epyc-orchestrator/orchestration/reports/`:
`w8_promotion_trajectory_20260714T172226Z_quietwindow.{json,md}`,
`seq_readiness_report_20260714T172226Z_quietwindow.{json,md}`,
`fable5_gate_report_20260714T172226Z_quietwindow.{json,md}`,
`bsv_paired_trial_1319_vs_1342_20260714T172226Z_quietwindow.{json,md}`, and
the AP-27 export set `ap27_rlvr_environment_20260714T172226Z_quietwindow.{jsonl,summary.json}`.
Findings: W8 still reports `status=progressing` at latest trial `1346` with
open requirements `combined_E_below_required`, `fresh_promotion_eval_required`,
`stale_accumulating_candidates_present`, and `seq_confirmation_required`; the
seq readiness report now shows `342` trusted vector trials and `265` seq-shadow
rows with `flip_rate=1.0`, so the report-only cutover check is structurally
ready but alpha-wealth is exhausted (`90` fingerprints tested,
`new_fingerprint_confirmations_allowed=false`) and the recommendation remains
"review report and cut over only with an explicit restart window"; the read-only
BSV trial pair `1319 -> 1342` shares `55` qids and improves scalar accuracy by
`+0.163636`, but `gate_decision=block` because the behavior-signature diff is
`blocking` (regressed/disappeared sentinels plus a route-path change), so
BSV-2/3 remain observe-only. The fresh Fable gate report is still `ready=false`
because the stopped-window phase heartbeat PID is dead and W6's gaming alarm
still blocks restart-cutover trust; it therefore does not justify any authority
flip during this quiet window. AP-26 remains gated on the operator-approved
non-RLM vs RLM live comparison, and AP-27 remains inference-gated on Ouro P7 /
EV-4 calibration rather than further offline scaffolding.

**Current checkpoint - 2026-07-14T19:33Z planner-parser hardening**: orchestrator
commit `51bbbf64` (`Fail closed on malformed planner critiques`) was pushed
after `feeacb07` and changes `extract_critique()` to require a named
`json:autopilot_critique` fence plus an explicit valid decision, so incidental
JSON/prose can no longer default to approve. Validation passed in the
orchestration session: `uv run ruff check scripts/autopilot/planner_coordinator.py tests/unit/test_autopilot_planner_coordinator.py`
and `uv run pytest tests/unit/test_autopilot_planner_coordinator.py -q`
returned `52 passed`.

**Current checkpoint - 2026-07-15T00:00Z planner-guard sidecar checkpoint**:
the main implementation thread is still actively editing/restarting around the
planner-guard patch set. The working tree currently carries uncommitted changes
in `scripts/autopilot/planner_coordinator.py`, `scripts/autopilot/autopilot.py`,
`scripts/autopilot/start_fable_authority_daemon.py`, and the two unit tests
under `tests/unit/` named above. This sidecar did not change code, restart any
process, or run validation; it only recorded the checkpoint so the next pass
can resume from the live in-flight state.

The stale canary trial `1352` ran to the paused boundary; the pause latch was
set and then cleared, and the old supervisor/child PIDs `2381139` / `2381140`
were stopped and verified gone. A new authority daemon started at
`2026-07-14T19:33:05Z` via `start_fable_authority_daemon.py --max-trials 1401`
with supervisor `2491402`, child `2491410`, and
`pid_age_verified_landed=true`. First post-fix cycles were clean:
trial `1353` produced a `local_frontdoor` draft plus a valid approve fence from
`local_ingest`; trial `1354` produced a `local_frontdoor` draft plus a valid
reject fence from `local_ingest`; planner-provider-health remained healthy.

The remaining blocker is unchanged: the seq gate still redirects
promotion-dependent numeric fallback to `seed_batch n=50` because
`rate_axis_unreachable` remains unresolved, and P0.1-P0.3 are still pending.

**Current checkpoint - 2026-07-16T09:55Z speed-regression investigation**:
AutoPilot remained intentionally stopped for a quiet-window investigation. The
live v6 environment was still wired correctly with `GGML_IQK=1`, OpenMP, and the
expected `LD_LIBRARY_PATH`. Direct server probes showed
`worker_full_8072` at `32.15 t/s` for 512-token MTP, the worker quarter ports
at `17.59 t/s` and `18.63 t/s`, and `frontdoor_full_8070` at `24.80 t/s`.
Canonical raw P-BENCH-1 v6 remains lower than the direct probes: worker
`tg512` is `23.33 +/- 0.04 t/s` and frontdoor `tg512` is
`15.95 +/- 0.09 t/s`. The June 28 worker parity artifact still matters as
comparison history: `38.46 t/s` with `GGML_IQK=1` versus `27.78 t/s` without.

Routing evidence identified the main distribution shift: `xmas_routing` had
been in enforce mode and the winner table was worker-heavy. The July 16 log had
`285` X-MAS-applied worker overrides, and learned routing was already
worker-heavy. The operational mitigation landed in `epyc-orchestrator`: X-MAS
was rolled back to shadow, worker aliases were recalibrated from the stale
`60.7 t/s` prior to the June 28 `38.46 t/s` v6/iQK artifact across registry,
descriptors, stack priors, q-scorer fallback, and seeding fallback, and the API
was reloaded.

V7 candidate CPU-comparable raw checks do not explain the regression:
ROCm-hidden worker `tg512` measured `23.67 +/- 0.28 t/s` and frontdoor `tg512`
measured `16.24 +/- 0.15 t/s`, matching production v6 raw CPU within noise. The
ROCm default worker result (`85.97 +/- 0.10 t/s`) remains a GPU observation only.

Focused verification passed (`122` tests: X-MAS routing, q-scorer, seeding
rewards). AutoPilot can be restarted through the authority daemon for a clean
shadow-X-MAS evidence window; keep X-MAS enforce disabled until a fresh
function-axis table validates current serving latency and quality.

> **Current state - 2026-06-21 (bounded W4/W6 accrual resumed).** The API was reloaded on orchestrator `d0e082a`, per-worker attestation passed across six workers, and `stack_change_pipeline.py check --run-promotion-gate` passed (`174` tests). The first collection-only run exposed eval fanout contamination under the current full-only fleet; after orchestrator `c13e5ae`, the collection run used `AUTOPILOT_SEQ_VERDICT=1`, `AUTOPILOT_W6_AUDIT_BLOCK=1`, `AUTOPILOT_W6_AUDIT_N=10`, `AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS=1`, `AUTOPILOT_W6_AUDIT_SHADOW_ONLY=1`, `AUTOPILOT_PLANNER_TIMEOUT=600`, default eval fanout capped to the reachable live fleet, and `--max-trials 930`. Trial `928` was journaled as `autopilot_killed_mid_trial` during stall recovery; trial `929` then completed as `numeric_trial` / `think_harder` with `q=1.980`, `s=34.132`, `r=0.980`, and `reproduction_confirmed`, and AutoPilot exited at trial counter `930`. Phase health then reported `status=stopped`, `ok=true`, `pid_alive=false` by design after `af72216e`. Latest ordinary restart readiness passed (`archive=match`, `snapshot=tail_fold_ready`, `baseline=state_baseline`, seed preflight `ready`, `append_ready=true`, `append_required=true`), while `--require-seq-cutover --require-w6-audit` correctly failed because sequential authority remained blocked at `93 < 120` trusted vectors and W6's trailing-30 alarm still had `7` active-window divergences (`12` cumulative) after `61/30` audited rows. The same W4/W6 collection posture was relaunched to `--max-trials 970` at 2026-06-21T11:49:27Z; `phase_health_report.py --json` first reported active trial `930`, `phase=planner_invoke`, PID `2472037`, no blockers, then advanced to `phase=dispatch_action`, `action_type=seed_batch`, no blockers. Baseline seed append is prepared but not applied; `fe2fe55c` also requires explicit `baseline_ledger_authority_enabled=true` before any later matching ledger fold can remove the state baseline cache.
>
> **Live update - 2026-06-21T15:30Z.** AutoPilot is still running under wrapper PID `2472032` / Python PID `2472037` on trial `934` T2; the suspected `architect_general` stall was stale, with `8083` idle and live slot progress continuing on other roles. `epyc-orchestrator` `dc601feb` makes the aggregate Fable5 report surface `append_baseline_seed_event` as the first P0 next action when the baseline seed preflight is ready/required. It is blocked while AutoPilot is active and carries guarded expectations `trial_counter=934` and `journal_max_trial_id=933`; no event was appended. Latest strict readiness remains blocked at trusted vectors `97/120` (`23` remaining), seq shadow rows `44/30`, W6 audited rows `65/30`, and W6 alarm clearance `23` clean audited trials.
>
> **W6 report alignment - 2026-06-21T15:40Z.** `epyc-orchestrator` `0c593b23` makes direct `audit_block_report.py` CLI runs default to the same trailing-30 alarm window used by restart/Fable5 readiness, while preserving `build_report(..., alarm_window=None)` for explicit all-history library callers. Live direct smoke over the current journal reports W6 audited rows `65`, alarm window `30/30`, `gaming_alarm=true`, clearance `23`, and cumulative divergences `12`.
>
> **Live update - 2026-06-23 (autopilot DOWN; planner failover landed).** The 2026-06-21 W4/W6 accrual run (PID `2472032`/`2472037`, toward trial `970`) was SIGTERM-drained cleanly to bump `--max-trials` to 1000, restarted @1000, then **SIGKILLed and left DOWN** at the operator's request to reclaim the host for the spec-dec MTP-refresh task. W4/W6 readiness accrual is paused mid-stream (last live strict gate: trusted vectors `97/120`, seq shadow `44/30`, W6 audited `65/30`, alarm clearance `23`) and resumes when the autopilot is next started. **Planner model-failover robustness landed** — `epyc-orchestrator` `c4455da1` on `spec-dec-mtp-refresh-2026-06-22` (cherry-picked from `a47e8d81`): cross-MODEL draft failover (claude↔codex by underlying model, not provider name — fixes a `codex`-primary/`codex_critic` dead-config where both roles were the same offline model), `providers_unavailable` tracking, and both-models-offline → deterministic Optuna `numeric_trial` (else clean pause `planners_offline_no_deterministic_fallback`). 39 planner tests pass; planner orchestration only (outside the MEASUREMENT.md trust boundary). The codex planner was observed degraded (account budget) during the restart — exactly the case this fix now degrades gracefully to claude. Detail: `progress/2026-06/2026-06-23.md`.
>
> Historical current-state banners through 2026-06-19 were compacted to [../completed/autopilot-continuous-optimization-history-through-2026-06-20.md](../completed/autopilot-continuous-optimization-history-through-2026-06-20.md).

> **Visibility checkpoint — 2026-06-20.** `epyc-orchestrator` `9cc932fe`
> (`Surface live eval progress from phase reports`) closes the current
> long-eval observability gap for already-running AutoPilot processes that lack
> structured eval counters in `/mnt/raid0/llm/tmp/autopilot_phase.json`.
> `build_phase_health_report()` now fills missing eval progress from the
> trial-scoped `logs/autopilot.log` tail only for live `deep_eval` /
> `structural_experiment` phases; heartbeat counters remain authoritative when
> present. Live smoke on wrapper PID `1091014` / Python PID `1091018` reported
> trial `902` as `T2 450/500 (70% correct)` in both phase health and the Fable5
> aggregate phase section, with no restart and no authority flip.
> Follow-up `epyc-orchestrator` `f5b1898a` (`Surface Fable5 accrual remaining
> counts`) threads the underlying readiness thresholds into restart/Fable5
> summary and next-action evidence. Current live smoke reports
> trusted vectors `68/120` (`52` remaining), seq shadow rows `16/30` (`14`
> remaining), and W6 audited rows `38/30` (`0` remaining) with the W6 gaming
> alarm still true.
> `epyc-orchestrator` `619c1f6d` adds `w6_alarm_clearance_clean_trials_required`
> to the W6 audit, restart-readiness, and Fable5 surfaces. Current live smoke
> reports `28` clean future audited rows are needed to clear the active
> trailing-window alarm, assuming no new gaming events occur.

**Created**: 2026-03-08
**Updated**: 2026-07-11 (tool_use sentinel `_MISSING_TYPE` backend crash fixed: added `toolrunner` field to `ServerURLsSettings` pydantic class and `ServerURLsConfig` dataclass as alias to `worker_general`; REPL code extraction fixed in `extract_code_from_response` with `<end_prompt>` stripping and unanchored Gemma thinking-channel regex; safety gate separates tool_use regressions: <= -3.0 hard block, -0.6 to -2.9 advisory; `AUTOPILOT_PLANNER_SPEND_BREAKER` remains disabled/off; strategy store scrubbed of stale infra-failure belief; end-to-end sentinel suite 4/5 pass, score=-1 advisory; 123 contaminated journal entries (trials 506-1302) marked known-contaminated. Live PID/phase state changes often; use the top checkpoint plus `phase_health_report.py --json` instead of this metadata line for runtime truth.)
**Location**: `epyc-orchestrator/scripts/autopilot/`

> **Fable 5 review (2026-06-12)**: the review's architecture recommendations now have owning handoffs: [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md) (LIVE t775 baseline-ratchet hotfix + dead-question repair), [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md) (per-question ledger + e-process verdicts; owns the next restart bundle), [evidence-plane-event-sourcing-and-narrative.md](evidence-plane-event-sourcing-and-narrative.md), and [objective-task-rate-goodput.md](objective-task-rate-goodput.md) (task_rate replaces the t/s axis). Full diagnosis: fable5-findings-01 + -05.

> Historical restart runbooks and settled 2026-06-04/05 implementation banners were compacted to [../completed/autopilot-continuous-optimization-history-through-2026-06-20.md](../completed/autopilot-continuous-optimization-history-through-2026-06-20.md).

**Historical addendum - 2026-07-08**: the fresh Fable restart came up clean as
PID `3681234` with `AUTOPILOT_PLANNER_PRIMARY=local_ingest`,
`AUTOPILOT_PLANNER_CRITIC=local_frontdoor`, `stack_mode=both`, and
`code_stale=false`. `b7518da0` keeps `StrategyStore` hints planner-only and
defensively ignores legacy `strategy_hints` in Seeder, while the append-only
supersession pass quarantined trials `1257-1263` with
`bug_corrupted_by=b7518da0`. `b5cadba6` adds the stale-planner-tap freshness
signals used by the dashboard to say when the live panel has no current planner
trace yet. Structured tap tail checks show the current seed-batch prompts are
clean again; the next live work remains replayable candidate evidence and
seq-confirmable promotion proof, not another prompt-history repair.

## Autopilot Delegation Expansion — 2026-05-20

Search space expanded with 4 new NumericSwarm surfaces + 3 new StructuralLab-experimentable flags. Total new knobs: **7** (4 numeric + 3 boolean).

**NumericSwarm surfaces added** (`scripts/autopilot/species/numeric_swarm.py`):
- `repl_executor` (2 knobs): `repl.turn_token_cap` [256–4096], `repl.frontdoor_non_tool_token_cap` [256–4096]
- `repl_budget` (2 knobs, gated by `worker_call_budget` / `task_token_budget` flags): `repl.worker_call_budget_cap` [5–100], `repl.task_token_budget_cap` [50K–500K]
- `kv_compaction` (3 knobs, runtime-applied via `kv_compress.compress_slot()`): `kv.keep_ratio` [0.25–0.90], `kv.keep_first` [2–16], `kv.n_future` [64–1024]

**HOT_SWAP_FEATURES additions** (`scripts/autopilot/config_applicator.py`): `structured_tool_output`, `content_cache`, `model_fallback` — promoted from the `rlm-orchestrator-roadmap.md` R6 default-off candidate matrix.

**New applicator path**: `apply_kv_compact()` in `config_applicator.py` routes `kv.*` trials to `kv_compress.compress_slot()` per role (uses existing `PRODUCTION_PORTS` mapping). `apply_params()` now dispatches across three buckets: hot_swap, env_restart, kv_compact.

**Caveats captured at wire-in time**:
- `repl.turn_token_cap` and `repl.frontdoor_non_tool_token_cap`: when `difficulty_signal` mode is `enforce`, `_repl_turn_token_cap()` returns hardcoded band-adaptive values from `_BAND_TOKEN_BUDGETS` and ignores the env var. The sweep affects only the flat-cap path. If fANOVA importance is low, next step is env-var-ifying the band-adaptive dict.
- `repl.worker_call_budget_cap` and `repl.task_token_budget_cap`: sweep is meaningful only when corresponding feature flag is on. StructuralLab should toggle the flags ON before these surfaces yield signal.
- `kv.keep_ratio` lower bound clipped at 0.25 (program.md notes "below 0.25 format degrades").

**Handoff promotion**: see `research-evaluation-index.md` §P11 for outcome-observation checkboxes (P11.1, P11.1b, P11.1c, P11.1d).

## Architecture

A continuous agent loop that autonomously optimizes orchestration intelligence through 4 optimizer "species", a tiered evaluation tower, 4D Pareto archive, and safety gates.

```
Controller (Claude CLI meta-reasoning)
  ├── Species 0: Seeder (per-role eval → Q-value training)
  ├── Species 1: NumericSwarm (Optuna NSGA-II → hot-swap config)
  ├── Species 2: PromptForge (LLM prompt mutation → .md hot-swap)
  └── Species 3: StructuralLab (flags + routing model lifecycle)
  │
  EvalTower: T0 (10q/30s) → T1 (100q/5m) → T2 (500+/30m) → T3 (expert/hard workflow eval)
  ParetoArchive: 4D (quality × speed × -cost × reliability; speed is median request t/s for serial evals, aggregate batch t/s for concurrent same-trial eval batches)
  SafetyGate: quality floor + per-suite guard + routing diversity
```

## File Structure

```
epyc-orchestrator/scripts/autopilot/
  autopilot.py              # Main controller + CLI (start|status|pause|resume|report|plot|checkpoint|restore)
  experiment_journal.py     # Dual TSV + JSONL logging with rotation
  pareto_archive.py         # 4D non-dominated sorting + hypervolume indicator
  safety_gate.py            # Quality floor, regression guards, rollback triggers
  eval_tower.py             # Tiered evaluation wrapping seeding infrastructure (on_question callback for TUI)
  config_applicator.py      # Hot-swap vs restart parameter routing
  meta_optimizer.py         # Species budget rebalancing + stagnation detection
  phase_status.py           # Phase heartbeat + async auxiliary-task runner
  progress_plots.py         # 6 matplotlib visualizations (auto-updated)
  sentinel_questions.yaml   # 10 curated T0 validation questions
  program.md                # Human-editable autoresearch strategy document
  failure_blacklist.yaml    # Known-bad configs species must not re-propose
  species/
    __init__.py
    seeder.py               # 3-way eval + reward injection + convergence monitoring
    numeric_swarm.py        # Optuna multi-objective + cluster-based robust selection
    prompt_forge.py         # Claude CLI prompt mutation (targeted_fix, compress, crossover...)
    structural_lab.py       # Checkpointing, training, distillation, memory reset

epyc-orchestrator/orchestration/
  autopilot_state.json      # Persistent state (Pareto archive, trial counter, budgets)
  autopilot_journal.tsv     # Human-readable experiment log
  autopilot_journal.jsonl   # Machine-readable experiment log
  autopilot_baseline.yaml   # Frozen baseline metrics
  autopilot_checkpoints/    # Timestamped routing intelligence snapshots
  autopilot_plots/          # Auto-generated progress visualizations
  /mnt/raid0/llm/tmp/autopilot_phase.json{,l}  # Dashboard-visible loop phase heartbeat
  repl_memory/strategy_store.py  # FAISS+SQLite strategy memory (species retrieval)
```

## Key Data Structures

```python
# Action types the controller can emit
{"type": "seed_batch", "n_questions": 50, "suites": ["coder", "thinking"]}
{"type": "numeric_trial", "surface": "memrl_retrieval", "params": {}}
{"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"}
{"type": "structural_experiment", "flags": {"skillbank": true}}
{"type": "train_routing_models", "min_memories": 500}
{"type": "distill_skillbank", "teacher": "claude", "categories": ["routing"]}
{"type": "reset_memories", "keep_seen": true, "keep_skills": true}
{"type": "deep_eval", "tier": 2}
{"type": "rollback", "to_checkpoint": "production_best"}

# EvalResult (from eval_tower → safety_gate → pareto_archive)
EvalResult(tier, quality, speed, cost, reliability, per_suite_quality, routing_distribution)
# Parallel eval metadata in details/JSONL: speed_metric_mode, eval_concurrency,
# median_request_tps, aggregate_tps, eval_wall_s.

# ParetoEntry (4D: quality↑, speed↑, -cost↑, reliability↑)
ParetoEntry(trial_id, objectives, config_snapshot, species, git_tag, parent_trial, ...)

# JournalEntry (TSV columns + JSONL full detail)
JournalEntry(trial_id, timestamp, species, action_type, tier, quality, speed, cost,
             config_diff, parent_trial, failure_analysis, hypothesis, expected_mechanism, ...)
```

## Routing Intelligence Lifecycle

```
SEED (3-way eval) → Q-values accumulate
    │ [500+ memories?]
    ▼
CHECKPOINT → TRAIN MLP + GAT
    │ [A/B passes?]
    ▼                    ↘ RESTORE checkpoint
CHECKPOINT + ENABLE routing_classifier + graph_router
    │ [Q-values stable?]
    ▼
DISTILL SkillBank
    │ [A/B passes?]
    ▼                    ↘ RESTORE checkpoint
CHECKPOINT (production_best) + ENABLE skillbank
    │ [plateau?]
    ▼
CHECKPOINT + RESET (selective) + RESEED → back to top
```

## Safety Mechanisms

| Gate | Threshold | Action |
|------|-----------|--------|
| Quality floor | avg < 2.0/3.0 | Reject |
| Regression | Δq < -0.05 vs baseline | Reject |
| Per-suite | Δq < -0.1 any suite | Reject |
| Routing diversity | >80% architect | Reject |
| Throughput floor | <80% baseline effective speed | Reject |
| Consecutive failures | 3 × T0 fail | Auto-rollback |
| **Code mutation deep validation** | Syntax + shrinkage + public names + import test | Reject (added 2026-04-04) |
| **Catastrophic shrinkage** | >50% size reduction (code or prompt) | Reject (added 2026-04-04) |
| **Revert commit** | All reverts are git-committed | Prevents corruption as HEAD (added 2026-04-04) |
| **Planner critique failure** | Active Codex critic returns unparseable output, timeout, nonzero rc, or empty response | Fail closed through reconciliation to a safe action (added 2026-05-31) |
| **Controller action schema** | Unknown keys, missing required keys, invalid enums, or bounded-range violations | Reject before dispatch for all 14 action types (added 2026-05-31) |
| **Dirty mutation target** | Pending git status on a forge-mutated code file or prompt target/path | Skip before write/commit; git errors fail closed as dirty (added 2026-05-31) |

**Parallel-dispatch metric policy (2026-05-26 audit)**: concurrent EvalTower fan-out is valid only inside one trial's own eval batch; separate trials must not run concurrently in one autopilot process. Concurrent fan-out intentionally trades lower individual request t/s for higher aggregate batch throughput. `EvalResult.speed` and Pareto objective #2 are the effective speed for the eval mode: median request t/s for serial evals, aggregate batch t/s for concurrent same-trial eval batches. Concurrent runs also journal `speed_metric_mode`, `median_request_tps`, `aggregate_tps`, `eval_concurrency`, and `eval_wall_s`, so the planner does not infer a regression from raw per-instance slowdown while diagnostics still expose it.

**Dispatch-latency / idle-visibility policy (2026-05-26 hardening; lock-display semantics corrected 2026-08-06)**: the dashboard CPU-region table is a physical placement-lease occupancy view, not proof that autopilot is alive or actively dispatching. An overlapping shape renders locked whenever any active placement lease occupies one of its CPU regions; contention-matrix admission metadata must not make an occupied region look free. An active cell's `active/configured` denominator is the selected llama-server instance's declared per-shape serving slots, not the exclusive placement lease's admission width. `phase_status.py` now writes `/mnt/raid0/llm/tmp/autopilot_phase.json{,l}` so the dashboard can show whether the loop is stopped, paused, in health backoff, building the planner prompt, invoking the planner, dispatching, journaling, checkpointing, or scheduling async artifacts. Auxiliary plot/digest work may run asynchronously (`AUTOPILOT_ASYNC_AUX=1`, `AUTOPILOT_ASYNC_WORKERS=2`) after durable journal/state mutation; checkpointing remains synchronous. Seeder role evals may fan out with `AUTOPILOT_SEED_ROLE_CONCURRENCY=auto`, but only in contention-matrix-safe background waves with same-port and heavy-port guards. The high-blast-radius request caller contracts remain unchanged; request-level `trial_id`/`batch_id` stamping through `call_orchestrator_forced` is a separate accepted-risk follow-up, not part of this hardening.

**Controller-mode relaunch safety policy (2026-05-31 hardening)**: the Claude->Codex planner loop is safe to run only when `AUTOPILOT_PLANNER_MODE=draft_critique` uses the fail-closed coordinator path from `d5c3a2f` or later. Under active critique, Codex parse failures and provider failures no longer default to approve. The universal action validator rejects schema drift before dispatch, closing the silent-drop class where the planner and critic approve fields the executor ignores. Mutation actions also check target cleanliness before any write: code mutation checks its resolved allowlisted file, prompt mutation and GEPA check the whole `orchestration/prompts/` path because PromptForge stages that directory, and structural prune checks its exact prompt file. This prevents forge commits from sweeping pre-existing shared-clone work in a target path.

**Binding critic is now the DEFAULT (2026-06-04, epyc-orchestrator `8d8c10a`)**: `AUTOPILOT_PLANNER_MODE` defaults to `draft_critique` (was `shadow_critique`) — the critic is binding without explicit opt-in. `AUTOPILOT_PLANNER_MODE=shadow_critique` is the rollback/staging knob. A reject/revise that substitutes the draft no longer bypasses the feedback loop: the rejected draft is fingerprinted, counted, surfaced in the next prompt, and auto-blacklisted on repeat (`_record_rejected_draft`), and `MAX_CONSECUTIVE_REJECTED_DRAFTS` durably halts a planner the critic keeps overriding. Builds on the invalid-action feedback fix (`c2033e4`): the planner/critic now see live feature-flag state + dependency rules, the last non-executing action, and the blacklist. Takes effect on next autopilot restart.

## Integration Points

| Component | Path | Integration |
|-----------|------|-------------|
| Seeding 3-way | `scripts/benchmark/seed_specialist_routing.py` | Seeder wraps `evaluate_question_3way` + `_inject_3way_rewards_http` |
| Question pool | Research: `scripts/benchmark/question_pool.py` | EvalTower draws T1/T2 validation questions and T3 workflow-shaped expert/hard rows from the live pool |
| Optuna | Research: `scripts/benchmark/optuna_orchestrator.py` | NumericSwarm reuses TPE/cluster patterns |
| Claude Debugger | `src/pipeline_monitor/claude_debugger.py` | PromptForge reuses Popen+session+git pattern |
| Episodic memory | `orchestration/repl_memory/episodic_store.py` | Seeder monitors count/convergence |
| Memory reset | `scripts/session/reset_episodic_memory.sh` | StructuralLab calls with selective flags |
| SkillBank | `orchestration/repl_memory/skill_bank.py` | StructuralLab triggers distillation |
| Config hot-swap | `src/api/routes/config.py` (POST /config) | ConfigApplicator routes flag changes |
| Feature flags | `src/features.py` (43 flags + validate()) | StructuralLab proposes flag combos |
| Strategy store | `orchestration/repl_memory/strategy_store.py` | Species retrieve past insights before proposals |

**Strategy-store rewind/purge tags:** future clean AutoPilot rewinds must also purge operator-seeded strategy campaigns so narrative hints do not survive a runtime rewind. Current applied campaign: `operator-handoff-distillation` from [autopilot-handoff-hint-distillation.md](../completed/autopilot-handoff-hint-distillation.md); use the handoff's purge path while AutoPilot is stopped if those rows need to be removed.

## Train/Validate Split

- **Training** (Seeder): 579 debug suite questions + 53K pool → Q-value training via per-role eval
- **Validation** (EvalTower): HF benchmark questions (MMLU, GSM8K, etc.) → system quality (end-to-end, `force_role=""`)
- Prevents overfitting: debug suites train routing intelligence, benchmarks validate generalization

## Phase 5: Per-Role Seeder (2026-04-17)

The original 3-way eval (SELF:direct, SELF:repl, ARCHITECT) was a pre-autopilot simplification that prevented Q-values from learning per-model preferences (96% uniform after 7,211 decisions). Replaced with dynamic per-role eval.

**Key changes:**
- `discover_active_roles()` reads `server_mode` from model_registry.yaml → 6 active roles
- `evaluate_question_per_role()` tests each role with `force_mode=""` (natural mode) + `allow_delegation=True`
- Rewards keyed by role name (e.g., "frontdoor", "architect_general") not abstract classes ("SELF:direct")
- Periodic role refresh every 10 batches for stack change resilience

**Adaptation surface** (when stack changes): only `seeding_types.py` needs updates — `ROLE_PORT`, `SEEDING_EXCLUDED_ROLES`, `_REGISTRY_KEY_TO_ROLE`. See `wiki/autonomous-research.md` for full table.

**Deferred**: `route_per_role()` in retriever.py (follow-up once per-role Q-values accumulate).

## Evolution: Seeding → AutoResearch

```
Seeding (passive eval, human fixes)
  → Claude-Debugger (active anomaly detection + Claude fixes during seeding)
    → AutoPilot (4-species continuous optimization)
      → AutoResearch (autonomous hypothesis-driven optimization)
```

The Claude-Debugger's capabilities are **subsumed into the autoresearch framework**: anomaly detection runs as post-trial analysis, hot-fix generation is replaced by PromptForge's `targeted_fix` mutation, session monitoring is replaced by SafetyGate's consecutive failure detection + auto-rollback.

### Stack-Config as Optimization Axis

| Axis | Species | Application Method |
|------|---------|-------------------|
| Model selection per role | StructuralLab | Restart (edit model_registry.yaml + orchestrator_stack.py) |
| Instance counts | StructuralLab | Restart |
| NUMA topology | StructuralLab | Restart |
| Tier assignment (HOT/WARM/COLD) | StructuralLab | Restart (mlock flags) |
| Acceleration flags | NumericSwarm | Restart (draft_max, moe_experts, lookup) |
| Cascade depth | StructuralLab | Restart (add/remove routing tiers) |
| General model prompting | PromptForge | Hot-swap (prompt .md files) |
| TOON compression | NumericSwarm | Hot-swap (encoding params) |

### program.md — Autoresearch Strategy Document

Located at `scripts/autopilot/program.md`. Human-editable strategy guiding autonomous experimentation:
- **Immutable boundary**: Evaluation methodology, scoring, safety gates, core orchestrator code
- **Mutable scope**: Prompts, configs, registry, stack topology, feature flags, specialist pipelines
- **Goal metric**: Debug suite pass rate (deterministic, no LLM judge) for fast iteration
- **Git-based ratchet**: Every improvement is a commit; degradations are reverted
- **Known dead ends**: Documents approaches that have been empirically exhausted

Key principles: one variable per experiment (clean attribution), simplicity criterion (reject disproportionate complexity), NEVER STOP, failure memory (never retry known-bad approaches).

### Related Handoffs

- [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) — Full NUMA scheduling architecture, Phases B-D complete
- [`routing-and-optimization-index.md`](routing-and-optimization-index.md) — Umbrella view of all optimization subsystems
- [`meta-harness-optimization.md`](meta-harness-optimization.md) — Execution trace feedback for PromptForge (3-tier plan)

## Usage

```bash
# Start optimization loop
python scripts/autopilot/autopilot.py start

# Start without Claude CLI controller (autonomous mode)
python scripts/autopilot/autopilot.py start --no-controller

# Dry run (no API calls, synthetic results)
python scripts/autopilot/autopilot.py start --dry-run --max-trials 10

# Check status
python scripts/autopilot/autopilot.py status

# Pause/resume
python scripts/autopilot/autopilot.py pause
python scripts/autopilot/autopilot.py resume

# Generate report / plots
python scripts/autopilot/autopilot.py report
python scripts/autopilot/autopilot.py plot

# Checkpoint / restore
python scripts/autopilot/autopilot.py checkpoint --production-best
python scripts/autopilot/autopilot.py restore
```

## Numeric Parameter Surfaces

| Surface | Key Params | Application |
|---------|-----------|-------------|
| memrl_retrieval | q_weight, min_similarity, min_q_value, confidence_threshold, semantic_k, prior_strength | Hot-swap via env + restart |
| think_harder | min_expected_roi, token_budget_min/max, cot_roi_threshold | Hot-swap via env + restart |
| chat_pipeline | try_cheap_first_quality_threshold | Hot-swap via env + restart |
| monitor | entropy_threshold, repetition_threshold, entropy_spike_threshold | Hot-swap via env + restart |
| escalation | max_retries, max_escalations | Hot-swap via env + restart |

## Dependencies

- Python 3.11+
- `optuna` (pip install optuna) — NumericSwarm Bayesian optimization
- `matplotlib` (already installed) — Progress plots
- `httpx` (already installed) — API calls
- `scikit-learn` (optional) — Cluster-based robust selection
- `claude` CLI (on PATH) — Controller meta-reasoning (optional, --no-controller for autonomous mode)

## Implementation Status

All core infrastructure verified in code as of 2026-04-01:

- [x] AP-1: Wire `failure_context` into PromptForge dispatch (2026-03-29)
- [x] AP-2: Feed failure narratives into controller prompt via `summary_text()` (2026-03-29)
- [x] AP-3: Populate `parent_trial` and `config_diff` journal fields (2026-03-29)
- [x] AP-4: `lab failures`-style query — `journal.recent_failures()` (2026-03-29)
- [x] AP-5: Per-suite quality trends in controller prompt (2026-03-29)
- [x] AP-6: Persist `consecutive_failures` counter across sessions (2026-03-29)
- [x] AP-7: Invalidate stale Optuna trials after regime changes — `mark_epoch()` (2026-03-29)
- [x] AP-8: Hypothesis + expected_mechanism tracking on JournalEntry (2026-03-29)
- [x] AP-10: Simplicity criterion — reject >20% prompt growth for <0.02 quality (2026-03-29)
- [x] AP-12: TUI 4-panel live monitor (`--tui` flag) (2026-03-22)
- [x] AR-2: Smoke test passed — 5 dry-run trials verified (2026-03-29)
- [x] SafetyGate `analyze_failure()` — structured violation narrative (2026-03-15)
- [x] StrategyStore (FAISS+SQLite) built in `repl_memory/strategy_store.py` (2026-03-15)
- [x] Cost tracking — `estimated_cost` field on `RoutingResult` (2026-03-15)
- [x] B1: Wire `strategy_store.retrieve()` into PromptForge species (2026-04-01)
- [x] B2: Failure blacklist — `failure_blacklist.yaml` with auto-append (2026-04-01)
- [x] B3: Execution trace feedback — `inference_tap.log` → PromptForge (2026-04-01)
- [x] B4: `insights_text()` on ExperimentJournal (2026-04-01)
- [x] B5: Cross-species fertilization via insights injection (2026-04-01)
- [x] #4: Evolution Manager species — 5th species for knowledge distillation (2026-04-01)
- [x] #5: Skeptical re-questioning gate — `_proxy_check()` in SafetyGate (2026-04-01)
- [x] #6: Forbidden proxy seeding — known dead ends in `failure_blacklist.yaml` (2026-04-01)
- [x] #7: Context budget management — auto-checkpoint every 25 trials (2026-04-01)
- [x] #8: Per-species token budget — `SPECIES_TOKEN_BUDGETS` in meta_optimizer (2026-04-01)
- [x] Tier 2: Code mutations in PromptForge — `code_mutation` action type + allowlist (2026-04-01)
- [x] Deep code mutation validation — shrinkage + public names + import test (2026-04-04)
- [x] Catastrophic shrinkage guard — >50% reduction blocked for code and prompts (2026-04-04)
- [x] Revert commits — reverts auto-committed to prevent corruption as HEAD (2026-04-04)
- [x] TUI on_question for EvalTower — prompt panel shows actual questions during deep eval (2026-04-04)
- [x] Hybrid eval gate — T0 fast-reject + T1 real gate replaces saturated T0-only eval (2026-04-04)
- [x] Tier-aware safety gate — quality floor and regression scaled by eval tier (2026-04-04)
- [x] Baseline recalibration — recalibrated to T1/T2 scale (q=1.16) from inflated T0 scale (2026-04-04)

## Remaining Work — Prioritized

### HIGH priority (next compute session)

- [x] **AP-RC-1 — Jul-8 silent-death root cause** (folded 2026-07-14 from archived `autopilot-restart-2026-07-09.md`) ✅ 2026-07-29: forensic trail establishes trial 1301 completed at 21:33:02Z and the final event was the next planner invocation at 21:33:11Z; no trial-1302 journal row exists until the later restart. Container kernel history is unavailable (`dmesg` permission denied), so historical attribution remains unresolved between external kill and a non-logging planner failure. `autopilot_exit_breadcrumb.jsonl` now appends+fsyncs process start, SIGINT/SIGTERM receipt, cooperative exit, unhandled exception, and interpreter teardown; a missing terminal record is the future SIGKILL/OOM diagnostic.

1. **AR-3 continuation**: Relaunch with new Phase 5 per-role seeder — `python scripts/autopilot/autopilot.py start --tui`
   - Run 2 (2026-04-02–04): 46 trials, 7 frontier. One useful change: `get_direct_answer_prefix()` in resolver.py (q 2.4→3.0)
   - **Corruption incident**: Trial ~25 replaced escalation.py (454→3 lines). API down 11+ hours. Safety hardened (5 gaps fixed).
   - ~~T0 saturated at q=3.0~~ **FIXED**: Hybrid eval (T0 fast-reject + T1 real gate) now gives honest signal per trial.
   - Baseline recalibrated to T1 scale (q=1.16). Safety gate tier-aware.
   - Phase 5 seeder refactor (2026-04-17) completed — restart with fresh baseline.

*(AP-14/15/16/17 moved to Completed Work — all ✅ 2026-04-07 per routing-and-optimization-index P11. See Implementation Status section below.)*

### P10 — GEPA PromptForge Integration (intake-327/345/240)

Source: hermes-agent-self-evolution (DSPy+GEPA), GEPA Full Program Adapter (93% MATH), GEPA paper (ICLR 2026 Oral). GEPA uses reflective trace analysis (ASI = Actionable Side Information) for 35x fewer rollouts than GRPO. Compatible with local inference (Ollama/vLLM format). 3-example minimum. MIT licensed.

- [x] AP-18: Install DSPy, wrap 3 routing prompts as DSPy Signatures — ✅ 2026-04-12. `dspy>=2.5.0` added to pyproject.toml. `src/dspy_signatures/` package: FrontdoorClassifier, EscalationDecider, ModeSelector signatures + config.py (configure_local_lm, configure_rlm). 8 smoke tests.
- [x] AP-19: GEPA frontdoor optimization — ✅ **Integrated into AR-3** (2026-04-12). `gepa_optimizer.py` adapter + `gepa` mutation type in PromptForge. 30% of PromptForge trials use GEPA evolutionary optimization via `OrchestratorGEPAAdapter` (evaluates through orchestrator API with sentinel questions). AR-3 journal collects comparison data automatically. 10 tests pass.
- [x] AP-20: GEPA Full Program Adapter eval — ✅ **Folded into AR-3** (2026-04-12). Resolved by comparing GEPA vs LLM mutation acceptance rates + Pareto frontier contributions in AR-3 journal after ~50 trials. No separate inference run needed.
- [x] AP-21: PromptForge GEPA refactor decision — **Decision 2026-07-11: keep mixed PromptForge; do not raise GEPA to 100%.** Combined `autopilot_journal.jsonl` + `autopilot_journal_1.jsonl` evidence has 1,195 deduplicated trials after AR-3 integration, 8 direct `gepa_optimize` attempts, only 1 clean/non-corrupt GEPA row, and 0 GEPA Pareto-frontier rows; the broader prompt-search class has 35 rows and 0 frontier rows. `gepa_ratio` therefore stays at the state-backed 0.30 default. GEPA execution health is a separate P0.3/frontdoor-freeze/blacklist-purge issue, not a reason to promote GEPA to 100%. ✅ 2026-07-11

### P11 — Autopilot Controller Upgrades (intake-328/329/349/320)

Source: MiniMax M2.7 3-component self-evolution harness (100+ autonomous rounds), dspy.RLM (WASM sandbox + sub_lm pattern), Unsloth RLVR (environment-first RL).

- [x] AP-22: Add `short_term_memory.md` per trial — ✅ 2026-04-12. `ShortTermMemory` class in `short_term_memory.py` (load/update/clear/to_text). Persists as markdown with 4 sections (hypotheses, directions, failures, context). Token-budgeted (~120 lines). Injected into CONTROLLER_PROMPT_TEMPLATE. CLI: `autopilot.py reset-memory`.
- [x] AP-23: Add explicit self-criticism step before next proposal — ✅ 2026-04-12. `self_criticism.py` with rule-based `generate_self_criticism()`. `SelfCriticism` dataclass (what_went_wrong, why, what_should_change, optimization_directions, keep/revert). Inserted between Evaluate and Record in controller loop. No inference cost.
- [x] AP-24: Formalize keep/revert protocol with structured forward-looking reasoning — ✅ 2026-04-12. `keep_revert_decision` and `optimization_directions` fields on JournalEntry. Centralized in `generate_self_criticism()`. Directions feed into short-term memory accumulator.
- [x] AP-25: Set up dspy.RLM with llama-server `/v1/` endpoint — ✅ 2026-04-12. `configure_rlm(main_lm_url, sub_lm_url)` in `src/dspy_signatures/config.py`. Coder as main LM, frontdoor as sub_lm. `test_connection()` health check. Integration testing deferred to AP-26 (needs inference).
- [ ] AP-26: Test dspy.RLM for autopilot tasks — long-horizon benchmark analysis where metadata-first context exploration avoids context window limits
- [ ] AP-27: Formalize eval tower tiers (T0/T1/T2) as RLVR verification functions with deterministic reward signals per tier (state matching, not LLM-as-judge). **2026-07-11 partial scaffold**: `epyc-orchestrator` commit `7ee919d8` adds `src/autopilot_core/rlvr_tiers.py`, a pure observe-only reward contract with T0 binary, T1 calibrated continuous, and T2/T3 process-attributed reward views plus explicit blockers for missing calibration/process evidence. **2026-07-11 export slice**: `scripts/autopilot/export_rlvr_environment.py` exports prompt-free `ap27_rlvr_environment_row.v1` JSONL from EvalResult/journal artifacts for future RL training. **2026-07-11 report slice**: `EvalResult.to_grep_lines()` emits report-only `METRIC rlvr_*` lines without changing objectives, SafetyGate, Pareto, or journal schema. **2026-07-11 journal slice**: `epyc-orchestrator` commit `69445d43` adds observe-only `eval_details["rlvr_reward"]` journal payloads from the same deterministic contract via the lower-risk main-loop journal assembly point, avoiding the HIGH-risk `EvalTower._aggregate` path. This closes the code-only tier/reward design, offline export, report-only, and journal-payload pieces; AP-27 remains open for inference-dependent Ouro integration. **Implementation plan**: See [eval-tower-verification.md](eval-tower-verification.md) EV-1–EV-7. Depends on EV-4 (calibration baseline) and P7 Ouro results.

#### AP-26/AP-27 operator gate packet - prepared 2026-07-11

This packet is staging only; it does not run live RLM tasks, start Ouro training/inference, change SafetyGate/Pareto objectives, or enable the planner spend breaker.

- **AP-26 dspy.RLM live test:** non-inference staging is complete when the RLM endpoint health check still passes and the candidate task has a bounded long-horizon trace fixture with an expected metadata-first win condition. The remaining acceptance evidence must come from a live operator-approved task window: same task against non-RLM and RLM paths, wall-clock/context-window diagnostics, exact model endpoints, and the error class if RLM fails. Do not count the existing `configure_rlm()` health check alone as AP-26 completion.
- **AP-27 RLVR export path:** current code supports prompt-free/offline RLVR rows only. Operator can preview/export existing rows with `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/autopilot/export_rlvr_environment.py orchestration/autopilot_journal.jsonl orchestration/autopilot_journal_1.jsonl --output-jsonl orchestration/reports/ap27_rlvr_environment_20260711.jsonl --summary-json orchestration/reports/ap27_rlvr_environment_20260711.summary.json --source-label operator_gate_packet_20260711`. This remains observe/offline data prep.
- **Ouro boundary:** AP-27 stays open until an inference-dependent Ouro integration path exists and passes operator review. The RLVR export, report-only `METRIC rlvr_*` lines, and journal payloads are necessary scaffolding, not a training run or promotion gate.
- [x] AP-26 bounded metadata-first fixture: `epyc-orchestrator` commit `740b525d` adds `tests/unit/fixtures/ap26/metadata_first_workspace_trace.json` and a focused `workspace_scan` test proving the query-first scan surfaces routing files within one bounded metadata pass despite higher-frecency distractors. This prepares the live RLM comparison fixture; AP-26 remains open for operator-approved non-RLM vs RLM endpoint evidence. ✅ 2026-07-11
- [x] AP-27 offline export validation: the prompt-free export ran to `/tmp`, producing `1196` rows (`423` ready_for_training, `773` blocked, `15` skipped_no_eval) under reward policy `ap27_rlvr_tier_reward_v1`; the dominant blocker is `auroc_missing_or_degenerate`. ✅ 2026-07-11
- [x] AP-27 durable export artifact: reran the same prompt-free export into `epyc-orchestrator/orchestration/reports/ap27_rlvr_environment_20260711.jsonl` plus `ap27_rlvr_environment_20260711.summary.json` with matching counts (`1196` rows, `423` ready_for_training, `773` blocked, `15` skipped_no_eval). ✅ 2026-07-11

### P17 — Bradley-Terry Tiebreak Under Hypervolume Stagnation (intake-615)

Source: arxiv:2510.24801 — Fortytwo: Swarm Inference with Peer-Ranked Consensus. The Bradley-Terry-style aggregation over pairwise rankings is the formal generalization of "pairwise comparison with confidence" that NumericSwarm currently approximates via 4D Pareto + hypervolume scalarization. Their published +17.21pp on GPQA-Diamond over majority voting is the empirical evidence that BT extracts ordering signal a scalar can't.

**Sub-task IDs use the `P17.BT-N` namespace** to avoid collision with the existing `AP-37 / AP-38 / AP-39 / AP-40` IDs already used by the 2026-05-23/24 constrained-creativity + launcher-threadcount work (see Implementation Status table line 769+).

**Concrete integration** (~50 LOC, falsifiable in one autopilot run):

- [x] **P17.BT-1 ✅ 2026-05-27** (epyc-orchestrator commit `2e51c86`): Shared module `src/bradley_terry.py` landed. Pure function `bradley_terry_rank(items, win_matrix) -> BTResult` with `bradley_terry_from_pairs` and `bradley_terry_from_scores` convenience wrappers; diagnostics for disconnected graphs, Condorcet cycles, dominance skew; dual convergence criteria (tight numerical + ranking-stability for perfectly-separable data where MLE is at infinity). 16 unit tests in `tests/unit/test_autopilot_bradley_terry.py`. Shared with [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md) Phase 3 and [`decision-aware-routing.md`](decision-aware-routing.md) DAR-6.4 — do not duplicate.
- [x] **P17.BT-2 ✅ 2026-05-27** (epyc-orchestrator commit `2e51c86`): New method `ParetoArchive.bt_tiebreak_topk(k=5)` + rich-prompt wiring in `_build_exploration_block`.
  - **What it actually does**: builds pairwise win-scores from the four existing objective axes (axis-vote / Borda count over recorded 4D objectives), then runs BT on those. The pairwise inputs are **NOT independent model judgments** of candidate outputs — they are mechanical comparisons of already-known scalar objectives. This is a **cheap axis-vote proxy** that uses the BT engine on data we already have, NOT the Fortytwo-style peer-ranked consensus described in intake-615.
  - **What it does NOT do**: run actual peer-evaluation across independent model judges (which would require new inference). The Fortytwo-faithful version would have N judges score each candidate and aggregate — INFERENCE-GATED and out of scope for P17.BT-2.
  - **Why this is still useful**: hypervolume scalarization collapses 4 axes into one number and can hide candidates that consistently beat peers across axes without being scalar-dominant. Axis-vote BT surfaces those as exploration seeds. Strictly cheaper and weaker signal than peer-ranked consensus.
  - **Top-K selection is range-normalized (scale-bias resolved 2026-05-27 commit `56ee9fc`)**: at `pareto_archive.py:348-358` each axis (obj − ref) is divided by `(max_e(obj) − ref)` across the frontier before summing, so every axis contributes on [0, 1] regardless of physical magnitude. The candidate set fed to BT is no longer biased by speed-in-t/s magnitude swamping reliability-in-[0,1]. Remaining limitation is the proxy-vs-peer-judge axis (still axis-vote, not judge-model — that's P17.BT-4 below).
  - 8 new unit tests in `tests/unit/test_autopilot_bt_tiebreak.py`. The axis-vote helper remains tested as an offline/shared diagnostic, but the live rich-prompt injection and stagnation-reason append were removed at `b8c0611` after P17.BT-3 failed to certify seed-level value.
- [x] **P17.BT-3 CLOSED 2026-06-12; cleanup landed 2026-06-13**: Falsification over the existing run passed sample size (341 rich/stagnation-fired trials, 75 logged BT disagreements) but could not certify the exact seed-level gate because the journal/logs do not persist BT top ID, hypervolume-top ID, or chosen-seed lineage. Available proxy outcomes were weak/clustered (`current frontier`: 2/75 disagreement events vs 9/266 no-disagreement rich events; cluster-start next-10 frontier: 1/7 vs 8/34 thinned no-disagreement rich prompts). Verdict: do not queue P17.BT-4. The cosmetic `bt_tiebreak_hint` rich-prompt block was removed from live orchestrator at `b8c0611` while AutoPilot was paused; `ParetoArchive.bt_tiebreak_topk()` remains as an offline/shared diagnostic.
- [x] **P17.BT-4 KILLED/DEFERRED 2026-06-12** — *true Fortytwo-style peer-ranked BT*: do not queue judge-model pairwise scoring from the current evidence. Reopen only after an explicitly instrumented P17.BT-3 rerun persists BT top ID, hypervolume-top ID, chosen seed/action lineage, and shows a positive seed-level signal.

**Cross-task interactions** (see § Scoring Upgrade Backlog below): the BT module here is the SAME algorithm that [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md) Phase 3 needs for filtering swarm-generated candidate completions (where the pairwise inputs WILL be real judge-model scores, not axis-votes). Implementing P17.BT-1 here unlocks that handoff's Phase 3 too.

### Scoring Upgrade Backlog (consolidation 2026-05-27)

Three "Research Intake Update" sections have surfaced **scoring-mechanism** upgrades for NumericSwarm over the past ~6 weeks. They are not three independent ideas — two of them operate on the *selection step* and partially substitute, one operates on *information sharing across species* and is orthogonal. Consolidating here so a future agent does not implement them redundantly.

| # | Source | Operates on | What it changes | Status | Interactions |
|---|---|---|---|---|---|
| 1 | intake-248 (SiliconSwarm@Ensue) | Cross-species info-sharing | Shared-memory + insights publishing every iteration; one agent's dead-end prevents others repeating | **Applied** (B1, B4, B5 — see § Research Intake Update — 2026-04-18 and DD-strategy-store) | Orthogonal to the two below; do not subsume |
| 2 | intake-269 (TPO / Cross-Entropy Method) | Selection step (sampler) | Replace NSGA-II/Optuna with CEM-style Gaussian-fit-to-elites on the 23-param numeric surface; particularly when hypervolume stagnates | **DESIGN NOTE only** — never operationalized; see § Research Intake Update — 2026-04-26 | Substitutes with the BT tiebreak on the same stagnation trigger; implement **one first**, A/B against the other |
| 3 | intake-615 (Fortytwo BT) | Selection step (tiebreak) | When scalarization is the noisy step, BT-rank the top-K Pareto candidates and pick by ranking confidence | **P17 above (this section)** — implementation specified, falsification gate defined | See #2 — same trigger surface |

**Recommended sequencing**:
1. Land P17.BT-1 (the shared BT module) — cheapest, ~50 LOC, also unblocks [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md). **Done 2026-05-27** (orchestrator commit `2e51c86`).
2. Land P17.BT-2 (axis-vote BT tiebreak prompt experiment) — cheap proxy using already-recorded data. **Done 2026-05-27** (same commit), then removed from the live rich prompt at `b8c0611` after negative/non-certifying P17.BT-3 analysis.
3. P17.BT-3 falsification closed 2026-06-12 negative/non-certifying; cosmetic rich-prompt hint removed at `b8c0611` on 2026-06-13.
4. P17.BT-4 is killed/deferred; do not spend judge-model inference on peer-ranked BT from this evidence.
5. Because P17.BT-3 failed to certify seed-level value, revisit intake-269 TPO/CEM only after the N2 evidence-plane redesign gives selector experiments enough attribution to be meaningful.
6. Continue extending the SiliconSwarm cross-species sharing pattern as orthogonal optimization; do not bundle with #2/#3 work.

### DEFERRED (explicit reasons)

2. ~~**GEPA integration** (intake-240)~~: **PROMOTED to P10** (2026-04-12). Deep-dive confirmed GEPA works with local inference, 35x cheaper than GRPO, 3-example minimum. No longer needs to wait for AR-3 PromptForge limitations — GEPA is strictly better.
3. **Hard-negative training data** (intake-176): Contrastive negatives for routing classifier. Only relevant when 500+ memories exist for retraining.
4. ~~**Git worktree isolation for PromptForge**~~: ✅ 2026-04-05. Implemented `worktree_manager.py` with `WorktreeManager` + `ExperimentContext`. Auto-reject safety default prevents corruption incidents like AR-3 trial ~25.
   - [x] **Exact-preimage rollback repair.** ✅ 2026-08-10 — rejection used to write the saved
     in-memory preimage and immediately erase it with `git checkout -- <path>`, destroying a dirty
     operator/parallel-session edit. It now restores exact bytes, distinguishes empty from absent,
     and has focused regression coverage for all three states.
5. **Convention locking** (intake-150): Lock baseline parameters from species modification. Premature without more trials.

### Design considerations (no implementation needed)

6. ~~**Tighter per-trial scope**~~: ✅ 2026-04-05. Implemented as code enforcement via `_validate_single_variable()` in `autopilot.py`. Rejects multi-file, multi-flag, and multi-param actions before dispatch.
7. **Explicit eval trust boundary**: Document that EvalTower scoring code is immutable — species must never modify it. Add to `program.md` constraints.

## Research References

| Intake | Paper | Key Insight | Applied? |
|--------|-------|-------------|----------|
| 108 | EvoScientist (arxiv:2603.08127) | Evolution Manager separates knowledge distillation from execution | Informed Evolution Manager species design (#4) |
| 106 | Agentic Critical Training (arxiv:2603.08706) | GRPO-based self-reflection for quality-aware agents | Background — AutoPilot evaluates via benchmark tower instead |
| 105 | PostTrainBench (arxiv:2603.08640) | Autonomous post-training plateaus after ~5h | Calibrates expectations for AR-3 run length |
| 142 | Cheat-Sheet Distillation (arxiv:2509.20820) | Difficulty-focused distillation outperforms broad textbook style | Applies to `distill_skillbank` in StructuralLab |
| 148/149 | AutoResearch + PraxLab | Tight constraints + failure memory + git ratchet | Core design of `program.md` and failure blacklist |
| 150 | GPD (get-physics-done) | Skeptical re-questioning, forbidden proxies, convention locks | Informed items #5-7 in remaining work |
| 176 | ReasonIR (arxiv:2504.20595) | Hard-negative training data for routing classifier | Deferred (#10) until 500+ memories |
| 240 | GEPA (arxiv:2507.19457) | Pareto-aware prompt evolution, 35x fewer rollouts vs RL | Deferred (#9) — potential PromptForge replacement |
| 244 | Meta-Harness (arxiv:2603.28052) | Execution trace feedback +15pts over score-only | **Applied** (B3) — traces fed to PromptForge |
| 248 | SiliconSwarm@Ensue | Cross-agent knowledge transfer breaks plateaus | **Applied** (B1, B4, B5) — strategy store + insights + cross-species |
| 265 | Omni-SimpleMem (arxiv:2604.01007) | Bug fixes > tuning on broken baselines; 6-type discovery taxonomy; 4 suitability properties (we pass all 4) | AP-14 deficiency classification, AP-15 field audit |
| 271 | Skill Issue: Harness Engineering (HumanLayer) | Harness config drives ~28 TerminalBench-2 rank delta; 14-22% instruction overhead; CLI > MCP heuristic | AP-16, AP-17 |
| 272 | Evaluating AGENTS.md (ETH Zurich, 2602.11988) | Context files REDUCE success rates, +20% cost; help only when docs absent; thin-map not tested | AP-16, AP-17 |
| 273 | Context Rot (Chroma) | Shuffled > structured for RETRIEVAL only; semantic similarity compounds degradation | Background — informs CF experiments |
| 274 | The Complexity Trap (2508.21433) | Observation masking matches LLM summarization at 50% cost; hybrid 7-11% further | Validates two-layer compression architecture |
| 312 | Mismanaged Geniuses Hypothesis (Zhang/Khattab) | Decomposition space design is the key variable; 4B RLM→100% MRCRv2 via composition | Theoretical foundation for P10/P11 |
| 320 | Unsloth RL Environments | RLVR (verifiable rewards) maps 1:1 to eval tower; environment-first RL design | AP-27 |
| 327 | Hermes Agent Self-Evolution (NousResearch) | GEPA reflective trace analysis + 6-stage optimization loop; $2-10/run via API | P10 (AP-18–21) |
| 328/329 | MiniMax M2.7 Self-Evolution | 3-component harness (memory+feedback+optimization), 100+ autonomous rounds, 30% improvement | P11 (AP-22–24) |
| 345 | GEPA Full Program Adapter | 93% MATH (vs 67% base); evolves signatures+modules+control flow; 35x fewer rollouts | P10 (AP-20) |
| 349 | dspy.RLM Module | Metadata-first REPL exploration; sub_lm pattern; works with OpenAI-compatible /v1/ endpoint | P11 (AP-25–26) |

## Research Intake Update — 2026-07-08: Self-Improvement Architectures (rec-004)

**Source**: SIA (intake-789, arXiv:2605.27276), ShinkaEvolve (intake-779), SkillRL (intake-092)

**Key finding**: SIA and ShinkaEvolve explore recursive self-improvement loops for agents. Combined with SkillRL's recursive skill-augmented RL, these suggest a pathway for our autopilot to move beyond trial-and-error optimization toward structured self-improvement with skill accumulation.

**SIA approach**: combines harness + weight updates; LawBench +25.1%, GPU kernel +12.4%. **CAUTION**: weight updates are inapplicable to our CPU stack; harvest harness-only patterns. The harness evolution component (meta-harness optimization) is the extractable signal.

**Integration points**:
- Species 0 (Seeder) could incorporate self-improvement loops beyond Q-value accumulation
- Species 2 (PromptForge) could use recursive self-improvement for prompt evolution beyond mutation
- Species 4 (Evolution Manager) aligns with EvoScientist's knowledge distillation separation

**CRITICAL CAUTION — SkillsBench v3 (intake-096)**: self-generated skills are net-negative (-1.3pp avg). Any self-improvement integration MUST include validation gates against a curated baseline. Do not let self-generated improvements enter the autopilot gate without human-curate confirmation.

**Integration decision — 2026-07-11**: adopt self-improvement patterns only as harness/search-memory loops; do not introduce a weight-update path on the CPU production stack. SIA/HTIR-style trace evidence maps to MH-11/MH-10 rather than model training. Species mapping:
- **Species 0 / Seeder**: use archive-derived planner hints and Pareto stepping-stones as observe-only hypotheses; no recursive Q-value self-training without an eval-gated operator run.
- **Species 2 / PromptForge**: recursive prompt/code improvement remains inside isolated mutation flows, dirty-tree fences, rollback, and the default-off EV-10 skill-efficacy gate.
- **Species 4 / Evolution Manager + StrategyStore**: ShinkaEvolve's meta-scratchpad/archive-memory pattern maps to deterministic journal-derived StrategyStore projections and DesignArchive lineage, not an unguarded live parent sampler.

**Validation gates — 2026-07-11**: any self-generated prompt/skill/strategy artifact must stay out of SafetyGate/Pareto promotion unless it passes the normal mutation rollback path plus a paired curated-baseline comparison. Required guard stack: EV-10 `AUTOPILOT_SKILL_EFFICACY_GATE` for skill-like artifacts, per-suite negative-delta rejection, held-out/dev-test discipline where available, BSV/paired-report evidence for batch-serving or evaluator changes, folded-journal evidence quarantine for StrategyStore projections, and explicit human-curated confirmation before enabling any live self-improvement loop. Planner spend-breaker remains off/opt-in; it is not a validation gate and must not be re-enabled as part of AP-SI.

**ShinkaEvolve StrategyStore evaluation — 2026-07-11**: current orchestrator already provides a contained archive-enrichment path via `scripts/autopilot/strategy_projection_report.py`, `StrategyStore.sync_frontier_journal_entries()`, `StrategyStore.sync_consult_gate_journal_entries()`, and replay `DesignArchive` lineage. Read-only validation on 2026-07-11: `strategy_projection_report.py --json` reported `ok=true`, `expected_count=69`, `projected_count=69`, `consult_gate.expected_count=1`, `consult_gate.projected_count=1`, and zero missing/unexpected/mismatched projections. This closes the evaluation path; future work is evidence-gated operator deployment or richer novelty sampling, not a blind new autonomous loop.

- [x] **AP-SI-1** — scope SIA harness-only patterns for integration into existing species; weight-update path is inapplicable ✅ 2026-07-11
- [x] **AP-SI-2** — design validation gates for any self-improvement loop; gate on curated-baseline comparison (SkillsBench v3 caution) ✅ 2026-07-11
- [x] **AP-SI-3** — evaluate ShinkaEvolve archive-based evolution for StrategyStore enrichment ✅ 2026-07-11

## Research Intake Update — 2026-08-09: Meta-Evolutionary Search Layer (rec-005)

**Source**: OpenRSI / OpenMLE-Evo ([intake-1024](../../research/intake_index.yaml), dive-verified 2026-08-09);
parent paper intake-940 (dive-verified 2026-08-03).

**Framing**: OpenMLE-Evo is a *test-time evolutionary search layer* over executable, objectively-scored
candidates. Autopilot is already such a layer, so this is a mechanism comparison against a sibling
design, not a new system. **Take the search/memory layer; discard OpenMLE-Gym** — intake-940
established Gym's contract is `evaluate(y_true, y_pred) -> float` scoring a prediction file, which
cannot express a throughput objective. Our T0/T1/T2 eval tower plus the AP-27 RLVR contract already
occupy that layer and occupy it better for our objective space.

**EVIDENCE CEILING — binds every item below.** intake-940's dive found **no selector-only ablation
anywhere** in the source paper, and only two of its claims survive scrutiny. Everything here is a
design pattern to test, never a validated win. Each must clear the guard stack the rec-004 section
above already mandates: paired curated-baseline comparison, per-suite negative-delta rejection, the
EV-10 skill-efficacy gate for skill-like artifacts, folded-journal evidence quarantine for
StrategyStore projections, and explicit human-curated confirmation before enabling any live loop.
**SkillsBench v3 (self-generated skills −1.3pp avg) is the standing prior.** None of these items
authorizes inference; all are offline/schema-first.

**Gaps verified against orchestrator source on 2026-08-09**, not assumed: `parent_utility` 0 files,
`method_family` 0, `error_signature` 0, `experience_card` 0. **`crossover` EXISTS** —
`scripts/autopilot/species/mutation_graph.py::informed_crossover_candidates`, consumed by
`species/prompt_forge.py` — but it ranks donor *section ids* by frequency (`counter.most_common`)
across Pareto-passing mutations, which is popularity, not complementarity. `novelty` appears once, at
`scripts/autopilot/autopilot.py:5314`, as prose inside an `info_gain` description — a described
consideration, not a computed term.

- [ ] **AP-ME-1 — Per-operator context budgets.** `ShortTermMemory` (AP-22) is a single ~120-line
  budget shared across the whole loop. Give each operator its own bound. Seed values from the shipped
  OpenMLE-Evo config (`OpenMLE-Evo/tts_search/configs/search/airaevo.yaml`): global
  `max_related_cards 3`; improve `ancestor_k 3` / `sibling_k 3`; crossover `2` / `2`; debug
  `max_related_cards 8`. **Offline-first**: measure current per-operator context size before changing
  anything, so the change has a baseline to beat.
- [ ] **AP-ME-2 — Scored parent utility with an always-on novelty term.** P17's Bradley-Terry tiebreak
  fires only *under hypervolume stagnation* — reactive de-concentration. Add a computed utility over
  normalized score, gain-over-strongest-parent (positive-only) and method-family novelty
  `1/sqrt(1+N_f)`, always on, so concentration is prevented rather than corrected. Complementary to
  P17, not a replacement. **Use the SHIPPED weights `score 1.0 / delta 0.4 / novelty 0.25`** — present
  in two places in `airaevo.yaml` — and NOT the paper's prose `1.0/0.6/0.3`; intake-940's dive proved
  paper and code disagree and that the case study used an unreleased configuration. Islands are
  inactive in every shipped profile (`num_islands 1`, `migration_prob 0.0`,
  `initial_temp = final_temp = 1.0`), so **do not port island machinery**.
- [ ] **AP-ME-3 — Complementarity cue for crossover donor selection**, replacing frequency ranking in
  `informed_crossover_candidates`. **BSV-3 already computes a semantic conflict severity** over shared
  subsystem, files touched, prompt sections touched, feature flags and behavior-signature delta. That
  is a complementarity signal with its sign flipped — crossover donor pairing and BSV-3 conflict
  scoring **must share one function** rather than be built twice with drifting definitions.
- [ ] **AP-ME-4 — Deterministic `error_signature` plus a repeated-failures counter.** Per the
  correction recorded in `autokernel-research-loop.md` §8.4.0, `ExperimentJournal.unfalsified_hypotheses()`
  is a recency window over the last five trials checking presence of a falsifier string only, and
  nothing marks a hypothesis resolved. A deterministic failure signature is the cheapest available
  upgrade and is a precondition for AP-ME-1's debug budget to select anything meaningful.
- [x] **AP-ME-5 — Experience-card row schema** (provenance, score, error type, method family, resource
  usage, novelty statistics) as the row type behind the StrategyStore / DesignArchive projections that
  already exist and already validate clean (69/69 projected, 2026-07-11). **Schema only** — no new
  autonomous loop, no live parent sampler.
  **✅ 2026-08-12 (`mainA`, pulled from the generated bench and claimed) — SCHEMA DERIVED, not
  invented. Mapped onto the row type that already exists and already validates, per the row's own
  framing.** The backing type is `orchestration/repl_memory/strategy_store.py:259` `StrategyEntry`.
  Six facets asked for; **three are already carried, three are genuinely absent**:

  | facet | status in `StrategyEntry` |
  |---|---|
  | **provenance** | ✅ carried — `source_trial_id`, `evidence_trial_ids[]`, `created_at`, `species` |
  | **score** | ✅ carried, but **three different scores with different meanings**: `validity_score` (0.5 default), `similarity_score` (retrieval), `rrf_score` (fusion rank). None is an outcome score. |
  | **novelty statistics** | ⚠ partial — `similarity_score` + `staleness` are the raw material; no novelty figure is derived or stored |
  | **error type** | ❌ absent |
  | **method family** | ❌ absent — `species` is the nearest field and is a *population* label, not a method taxonomy |
  | **resource usage** | ❌ absent |

  **The finding that matters for whoever implements it: `score` is ambiguous in the row as
  written, and the existing type proves it.** `StrategyEntry` already carries three floats named
  `*_score`, none of which is the *outcome* score an experience card needs — they are a validity
  prior, a retrieval similarity and a fusion rank. Adding a fourth bare `score` to that set is how
  a consumer reads the wrong one. Any implementation should name it for what it measures
  (`outcome_score`, or the objective it came from) rather than inheriting the row's word.
  **Recommended shape:** extend `StrategyEntry` additively rather than defining a parallel type —
  `to_dict()` is `asdict()`, so new optional fields round-trip for free and the 69/69 projections
  keep validating. The three absent facets want: a typed `error_signature` (which AP-ME-6 above
  independently asks for, so build it once and let both consume it), a `method_family` enum
  distinct from `species`, and a `resource_usage` sub-dict — the last is the one with a live
  write-side hook available, since the trial journal already records wall-clock and the four raw
  objective components.
  **Belief-kernel note, filed rather than assumed:** an experience card carrying an outcome score
  plus provenance IS a measurement-shaped record. If it is implemented, it needs a write-side
  ClaimTuple decision at that moment — not retrofitted on read. Flagged here so the implementer
  hits it at design time; not filed as a vidya row, because the type does not exist yet and a
  register row for an unbuilt producer is the kind of speculative entry that register warns about.
  **NOT IMPLEMENTED, deliberately** — the row says *schema only*, and the three absent facets each
  need an owner decision (which taxonomy for `method_family`, which resources count). This closes
  the derivation; the field additions are a separate, smaller task with those answers in hand.
- [ ] **AP-ME-6 — Negative-evidence rendering discipline.** intake-940's dive narrowed this from an
  exclusion filter to a *rendering* rule: a deterministic error signature per card plus a board-level
  repeated-error counter, rendered as one compact typed line rather than raw prior-attempt text.
  Failures still enter context — they enter it small. Pairs with AP-ME-4; feeds AP-ME-1's budgets.

## Known Issues — KV Cache seq_add Crash on Qwen3.5 Hybrids (2026-04-15, PATCHED)

architect_general (Qwen3.5-122B-A10B, ports 8083+8183) crashed with assertion failure in `llama-kv-cache.cpp:614`:
```
GGML_ASSERT(hparams.n_pos_per_embd() == 1 && "seq_add() is only supported for n_pos_per_embd() == 1")
```

**Root cause**: Qwen3.5 architecture uses `LLAMA_ROPE_TYPE_IMROPE` (interleaved multi-rope, `n_pos_per_embd() == 4`) — same positional encoding as Qwen3-VL vision models, even in text-only mode. The `seq_add()` and `seq_div()` functions in `llama_kv_cache` had overly conservative assertions blocking any model with `n_pos_per_embd() != 1`. The crash triggered when the server's context checkpoint system called `seq_add` during KV chunk reuse (prompt cache hit with position shift). `get_can_shift()` also returned false, which would have caused `GGML_ABORT` if reached.

**Impact**: architect_general went down around trial 204, causing `routing_distribution` to collapse to `{"frontdoor": 1.0}`. Quality dropped from q≈2.10 to q≈1.14. Trials 204-215 data is tainted (frontdoor-only, no escalation routing). Autopilot's short-term memory has been annotated with operator note explaining the crash.

**Fix (2026-04-15)**: Patched 3 locations in `llama-kv-cache.cpp`:
1. Removed `GGML_ASSERT(n_pos_per_embd() == 1)` from `seq_add()` — the underlying `pos_add()` operates on scalar base position, and K-shift already handles IMROPE correctly (falls back to NEOX-style rotation via `build_rope_shift()`, see `@ngxson` workaround at line 1884)
2. Removed same assertion from `seq_div()`
3. Removed `n_pos_per_embd() > 1` guard from `get_can_shift()` — K-shift graph builder already supports IMROPE

Both NUMA instances relaunched with patched binary. Fix applies to all Qwen3.5 hybrids (QWEN35, QWEN35MOE arches). Dense models (Qwen3, Qwen3MOE) were unaffected (use NEOX rope, `n_pos_per_embd() == 1`).

**Verification needed**: Run seed_batch trials to confirm architect routing restored and quality recovers to q≈2.10.

## Known Issues — Architect Think-Block Loop (2026-04-14, RESOLVED 2026-04-15)

Qwen3.5-122B-A10B on `architect_general` enters degenerate `<think>` block loops during routing decisions. Model closes a think block, emits partial answer, then re-opens `<think>` repeatedly — burning the full 512-token budget per attempt.

**Root cause (revised 2026-04-15)**: The `--jinja` server flag loads Qwen3.5's native chat template, which includes `<think>`/`</think>` block scaffolding. The template itself primes the hybrid SSM+MoE model into think mode. Previous mitigations (`--reasoning off`, `_architect_early_stop()` streaming detection) were insufficient — the jinja template injects thinking preamble before `--reasoning` can suppress it.

**Fix applied (2026-04-15)**: Removed `--jinja` flag from architect_general server launch entirely. Without `--jinja`, llama-server falls back to generic ChatML template which has no thinking scaffolding — model never enters think mode. Also removed now-unnecessary `--reasoning off`. All other roles retain `--jinja`. Change in `orchestrator_stack.py:build_server_command()`.

**Previous mitigations (superseded)**:
- `--reasoning off` server flag (commit 0591952) — insufficient, jinja template still primed thinking
- `_architect_early_stop()` streaming detection (2026-04-14) — band-aid, didn't prevent wasted tokens
- `repeat_penalty`/`temperature` tuning — never applied, no longer needed

## Staleness Notes

- `optuna_orchestrator.py`: TPE/cluster patterns reusable; parameter ranges stale (predate current config/models.py)
- `seed_specialist_routing.py`: Canonical source at `epyc-orchestrator/scripts/benchmark/` (1,449 lines)
- `orchestrator_self_management.md` Phase 9: Deferred Optuna loop; architecture evolved significantly
- `pre-split-optimization-ab-test-plan.md`: Decision function reusable; specific paths broken post-split

## Verification Plan

1. **Smoke test**: `python autopilot.py start --dry-run --max-trials 5`
2. **Seeder integration**: Run 20-question batch, verify reward injection
3. **NumericSwarm**: Create Optuna study, suggest trials, verify cluster selection
4. **PromptForge**: Propose mutation, apply, verify git snapshot
5. **Full loop**: 10 trials across all species, verify journal + Pareto + safety gate
6. **Overnight**: 8-hour unattended run, check hypervolume trend

## Research Intake Update — 2026-04-06

### New Related Research
- **[intake-265] "Omni-SimpleMem: Autoresearch-Guided Discovery of Lifelong Multimodal Agent Memory"** (arxiv:2604.01007)
  - Relevance: AutoResearchClaw is a 23-stage autonomous research pipeline — directly comparable to our 4-species AutoPilot architecture
  - Key technique: Multi-agent debate + self-healing execution; autonomous experiment loop (~50 experiments)
  - Reported results: +411% F1 on LoCoMo, +214% on Mem-Gallery; bug fixes (+175%) > all hyperparameter tuning combined
  - Delta from current approach: Their finding that bug fixes and architectural changes vastly outperform hyperparameter tuning validates prioritizing Species 2 (PromptForge) and Species 3 (StructuralLab) over Species 1 (NumericSwarm). Consider increasing structural species budget allocation. The 23-stage pipeline with debate is more sophisticated than our 4-species approach — may inform future species design.

- **[intake-267] "ByteRover: Agent-Native Memory Through LLM-Curated Hierarchical Context"** (arxiv:2604.01599)
  - Relevance: Agent-native memory where the LLM itself curates knowledge in hierarchical markdown files — validates autopilot state management direction
  - Key technique: Hierarchical Context Tree with importance scoring + recency decay; sub-100ms retrieval
  - Delta from current approach: Our autopilot_state.json is a flat JSON store. ByteRover's hierarchical approach with LLM-driven curation could inform how autopilot manages its experiment journal and Pareto archive for better context retrieval across long runs.

### Deep-Dive Correction (2026-04-06)
**Caveat on intake-265**: The "bug fixes > tuning" headline is misleading. The baseline was catastrophically broken (F1=0.117 vs SimpleMem SOTA 0.432) — a missing `response_format=json_object` caused 9x verbosity. The finding generalizes to "fixing broken systems beats tuning broken systems," not "structural always beats numeric." Our AutoPilot operates on a functioning system where NumericSwarm is in the right regime. **No species budget rebalancing needed from this paper alone.** However, two small improvements validated: (1) add structured deficiency classification to experiment_journal.py error handling, (2) ensure all species populate hypothesis/expected_mechanism journal fields. The 4 autoresearch suitability properties (scalar metrics, modular architecture, fast iteration, version-controlled modifications) are a useful checklist — our AutoPilot satisfies all 4.

## Research Intake Update — 2026-04-12

### New Related Research
- **[intake-327] "Hermes Agent Self-Evolution"** (NousResearch) — DSPy+GEPA skill optimization
  - Relevance: Directly applicable to PromptForge species — evolutionary optimization of skills/prompts without GPU
  - Key technique: GEPA reflective evolutionary search with execution trace analysis
  - Delta from current approach: Our PromptForge uses LLM-guided mutation. GEPA uses evolutionary + Pareto-optimal selection. Their $2-10 per run is API-based; adapting to local models eliminates cost. Guardrails (test validation + human review) are more conservative than our safety gates.
- **[intake-338] "Agent Lightning"** (Microsoft Research) — Zero-code agent optimization
  - Relevance: Three optimization modes (RL, prompt optimization, SFT) map to our species: RL→NumericSwarm, prompt→PromptForge
  - Key technique: Framework-agnostic tracing + optimization. Zero code change adoption.
  - Delta from current approach: Agent Lightning could optimize our orchestrator without modifying existing code. The trajectory-level aggregation addresses our per-question vs per-trajectory eval gap.
- **[intake-344] "LightningRL: Hierarchical Credit Assignment"** (arxiv:2508.03680)
  - Relevance: Solves autopilot evaluation granularity problem — attributes task success to specific orchestrator decisions
  - Key technique: Per-LLM-request credit assignment + reward scoring, compatible with PPO/GRPO
  - Delta from current approach: We evaluate at task-level (T0/T1/T2). LightningRL enables per-step attribution. Could dramatically improve PromptForge mutation signal quality.
- **[intake-345] "GEPA Full Program Adapter: 93% MATH"** (DSPy tutorial)
  - Relevance: Evolves entire program structure (not just prompts) — 93% vs 67% baseline on MATH
  - Key technique: GEPA evolving DSPy signatures, modules, and control flow with as few as 3 examples
  - Delta from current approach: PromptForge only mutates prompt templates. GEPA Full Program Adapter could evolve routing logic, tool definitions, and escalation pipeline. The +26pp improvement is transformative.

### Deep-Dive Synthesis (2026-04-12)
**Cross-cutting finding from 26-entry deep-dive**: Four converging research threads point to a major autopilot upgrade path:
1. **GEPA** (intake-327/345): Reflective trace analysis + evolutionary Pareto search. 35x more efficient than GRPO. 3-example minimum. Compatible with our local inference (Ollama/vLLM format). **Priority #1 for PromptForge upgrade.**
2. **dspy.RLM** (intake-349): Metadata-first context exploration via REPL sandbox. Sub-LM pattern maps to our coder+frontdoor stack. Directly addresses context window limitation for long autopilot runs. **Priority #2 for autopilot infrastructure.**
3. **MiniMax M2.7 self-evolution** (intake-328/329): Three-component harness (short-term memory markdown + self-criticism + forward-looking optimization) over 100+ autonomous rounds. Pattern directly implementable in our controller. Add `short_term_memory.md` per trial, explicit self-feedback step before next proposal, and formalized keep/revert protocol.
4. **Unsloth RLVR** (intake-320): Our eval tower IS an RLVR environment. Formalize T0/T1/T2 as verification functions, not just benchmarks. Design reward signals per tier. If cloud GPU becomes available, export environments for actual model RL training.

**Architectural theme**: All entries converge on "context efficiency through structured indirection" — sandbox over prompt, REPL over context, reflection over gradient, retrieval over fullcontext. Validates our multi-model approach over single-model scaling.

## Research Intake Update — 2026-04-14

### New Related Research
- **[intake-363] "LLM-as-a-Verifier"** (github.com/llm-as-a-verifier)
  - Relevance: General-purpose verification framework using logprob-based scoring with criteria decomposition — directly relevant to AP-27 eval tower formalization as an alternative to LLM-as-a-Judge
  - Key technique: R(t,τ) = (1/CK) Σ p_θ(v_g|t,c,τ)·φ(v_g) — multi-criteria, repeated verification, granularity scaling
  - Reported results: Terminal-Bench 2: 86.4% (from 81.8%), SWE-Bench Verified: 77.8% (from 76.1%)
  - Delta from current approach: AP-27 specifies "state matching, not LLM-as-judge" for verification functions. LLM-as-a-Verifier offers a middle ground — uses LLM logprobs but for structured verification rather than open-ended judgment. Gemini API dependency is a blocker for local deployment.
- **[intake-371] "ThinkPRM: Process Reward Models That Think"** (arxiv:2504.16828)
  - Relevance: Generative PRM that verifies solution steps via verification chain-of-thought — applicable to eval tower step-level attribution
  - Key technique: Fine-tunes long-CoT models as verbalized step-wise reward models; achieves PRM800K parity with only 1% of labels
  - Reported results: 8% better OOD on GPQA-Diamond, 4.5% on LiveCodeBench vs discriminative PRMs
  - Delta from current approach: Our T0/T1/T2 tiers are outcome-level. ThinkPRM enables per-step process reward attribution within evaluation, complementing LightningRL (intake-344) per-step credit assignment.
- **[intake-370] "Aletheia: RLVR for Code Verifiers"** (arxiv:2601.12186)
  - Relevance: Systematic ablation of RLVR training recipes across model scales — directly informs AP-27 verification function design
  - Key technique: Scale-dependent optimization recipes — small verifiers need on-policy training; large need negative samples + thinking traces
  - Reported results: Compute-optimal roadmap for practitioner deployment
  - Delta from current approach: Our eval tower targets are fixed tiers. Aletheia shows that the training recipe matters more than architecture at small scales — relevant if we export environments for RL training per intake-320.
- **[intake-368] "SWE-RM: Execution-Free Feedback for SWE Agents"** (arxiv:2512.21919)
  - Relevance: MoE reward model (30B total, 3B active) providing execution-free feedback — relevant to eval tower reward signal design
  - Key technique: MoE architecture with controlled data composition experiments; classification accuracy and calibration critical for RL
  - Reported results: Qwen3-Coder-Flash 51.6%→62.0%, Qwen3-Coder-Max 67.0%→74.6% on SWE-Bench Verified
  - Delta from current approach: SWE-RM shows TTS performance doesn't guarantee RL effectiveness — our eval tower must separately validate classification accuracy and calibration, not just pass rates.

**Synthesis**: The 5 verification research entries above (intake-363/367/368/370/371) are consolidated into a standalone handoff: [eval-tower-verification.md](eval-tower-verification.md). That handoff provides the implementation plan (EV-1–EV-7) for ECE/AUC metrics, ThinkPRM deployment, cross-family verification, and Scoring Verifiers benchmark integration that these papers motivate. AP-27 now points to that handoff as its implementation plan.

### Future AR-3 Signal: Branching Density (2026-04-15 deep-dive)

intake-378 (arxiv:2604.01702) identifies Propose step ratio as a quality metric for reasoning traces. High branching density (>0.30) indicates unproductive exploration — the model is diverging across alternative approaches rather than converging on a solution.

**Relevance to AR-3**: If a config change (PromptForge mutation, StructuralLab flag, NumericSwarm param) causes higher average branching density in solver outputs, that is a negative signal even if accuracy is unchanged — the model is working harder for the same result, increasing cost.

**Lightweight implementation**: Add branching keyword scan to T0/T1 eval output analysis. Report as `METRIC branching_density: X.XX` via existing `to_grep_lines()` mechanism in `safety_gate.py`. The SafetyGate quality floor could incorporate: reject trials where branching density increases without quality gain.

**Priority**: LOW — only relevant when AR-3 experiments touch solver behavior (prompt mutations, model swaps, reasoning budget changes). Cross-ref: `routing-intelligence.md` (Category C quality signal), `research/deep-dives/sft-generalization-reasoning-patterns.md`.

## Research Intake Update — 2026-04-17

### New Related Research

- **[intake-394] "Evolver: GEP-Powered Self-Evolution Engine for AI Agents"** (repo: EvoMap/evolver)
  - Relevance: directly overlaps with the PromptForge species and the autopilot governance/safety layer — Evolver implements a protocol-bound evolution pattern with primitives (Gene/Capsule/EvolutionEvent JSONL assets, protected source files, strategy presets) that mirror what our autopilot safety gates already need.
  - Key technique: GEP (Genome Evolution Protocol) — auditable, protocol-constrained prompt evolution; strategy preset weighting (innovate/optimize/repair intent mix, e.g. 80/15/5 balanced vs 0/20/80 repair-only); log-signal extraction for selector-driven prompt routing; protected-source-files to prevent self-overwrite.
  - Reported results: none (no benchmarks, no empirical claims in README).
  - Delta from current approach: adds an **auditability-first asset schema** (Gene/Capsule/EvolutionEvent) as a reference to compare against our own PromptForge artifact scheme; the protected-source-files pattern is directly adoptable as a safety gate for autopilot mutations. Not adopt_component (Node.js, tied to evomap.ai hub, no benchmarks). Cross-refs intake-327 (GEPA/DSPy), intake-328 (MiniMax self-evolving).

- **[intake-404] "Target Policy Optimization"** (arxiv:2604.06159)
  - Relevance: TPO's core mechanism — construct target distribution `q_i ∝ p_old * exp(score/η)`, fit via cross-entropy — is mathematically the Cross-Entropy Method (CEM). Directly applicable to NumericSwarm as an alternative or augmentation to NSGA-II for the 23-param numeric surface.
  - Key technique: Closed-form target distribution from scored samples + cross-entropy fitting. No policy gradients, no clipping, no critic. Temperature η controls exploration (robust across 0.25-2.0).
  - Reported results: On bandits (closest analog to autopilot trials): TPO converges fastest with lowest misalignment to oracle gradient. Multi-epoch stable where GRPO oscillates destructively.
  - Delta from current approach: NumericSwarm uses NSGA-II (Optuna) with per-surface studies and 4D Pareto scoring. A CEM sampler would: (1) maintain Gaussian N(μ,Σ) per surface, (2) sample K configs, (3) score via eval tower, (4) refit to elite set weighted by scalarized Pareto score (hypervolume contribution). Requires scalarizing the 4D objectives — hypervolume contribution is the natural choice. Full control surface embedding (66+ dims with flags + text mutations) is infeasible due to heterogeneous action space and expensive evaluations. **Concrete integration point**: when `hypervolume_slope() < 0.001` triggers stagnation detection in `pareto_archive.py`, switch from NSGA-II to CEM sampling as the exploration boost mechanism (currently just increases exploration weight). Code reference: `numeric_swarm.py:99` (sampler init), `pareto_archive.py:188-200` (stagnation detection).

## Research Intake Update — 2026-04-18

### New Related Research

- **[intake-412] "DeepPlanning: Benchmarking Long-Horizon Agentic Planning"** (arxiv:2601.18137)
  - Relevance: Benchmark for long-horizon agent planning with verifiable constraints. 26 frontier models evaluated across travel planning (minute-level scheduling, 9 APIs) and shopping planning (15 APIs, coupon timing). Even GPT-5.2-high only achieves 44.6% case accuracy. Rule-based automated scoring aligns with our ch07 benchmark construction philosophy.
  - Key insight for autopilot: Reasoning-equipped models consistently outperform non-reasoning variants. Parallel tool use improves effectiveness-efficiency trade-offs. Error analysis of 140 failed trajectories shows global optimization failures are most prevalent — directly relevant to autopilot's multi-step planning quality assessment.
  - Delta from current approach: Potential benchmark addition for evaluating autopilot planning quality. Layered task generation methodology (solution-centric reverse generation) could inform synthetic eval task construction for AR-3 runs.

## Research Intake Update — 2026-04-20

### New Related Research

- **[intake-413] "Toward Ultra-Long-Horizon Agentic Science: Cognitive Accumulation for ML Engineering"** (arxiv:2601.10402)
  - Relevance: HCC (Hierarchical Cognitive Caching) maps directly to AutoPilot's memory architecture gap — `strategy_store.py` is flat where HCC is L1/L2/L3 tiered. ML-Master 2.0 achieves 56.44% SOTA on MLE-Bench using this approach.
  - Key technique: L1 (execution traces, volatile) → L2 (phase summaries, semi-stable) → L3 (cross-task wisdom, persistent). Promotion operators P1/P2 trigger at phase/task boundaries.
  - **Deep dive**: `research/deep-dives/hcc-cognitive-accumulation-autopilot.md` — maps HCC tiers to `short_term_memory.py` (≈L1), missing L2 consolidation, `strategy_store.py` (≈L3 structurally but flat functionally). Proposes concrete `knowledge_distiller.py` (~300 LoC) for L1→L2→L3 promotion.
  - Delta from current approach: AutoPilot stores individual strategy insights but never distills patterns across trials. HCC provides the missing consolidation/promotion pipeline.

- **[intake-414] "Token Savior Recall — 97% Token Reduction MCP Server"** (repo: mibayy/token-savior)
  - Relevance: Four extractable patterns for `strategy_store.py`: (1) RRF hybrid retrieval (BM25+FAISS), (2) content-hash staleness detection, (3) MDL convention promotion, (4) progressive disclosure.
  - **Deep dive**: `research/deep-dives/token-savior-extractable-patterns.md` — concrete schema changes, Python code sketches, priority ordering (staleness > RRF > disclosure > MDL).
  - Delta from current approach: strategy_store has no staleness detection (stale strategies from changed configs never expire) and pure FAISS retrieval misses exact-term matches.

- **[intake-415] "Context Mode — Context Window Optimization for AI Coding Agents"** (repo: mksglu/context-mode)
  - Relevance: Subprocess sandbox (99% output reduction) and 5KB threshold gating applicable to eval tower output in controller prompt.
  - **Deep dive**: `research/deep-dives/context-mode-tool-compression-patterns.md` — estimated 30-50% context reduction in eval-heavy autopilot sessions.
  - Delta from current approach: eval tower output inflates controller prompt with no budget control; threshold gating + FTS5 indexing would index large outputs and serve relevant excerpts.

### Synthesis Deep Dive

**`research/deep-dives/autopilot-iteration-strategy-synthesis.md`** — 4-phase improvement plan:

| Phase | What | Target | Scope | Status |
|-------|------|--------|-------|--------|
| 1 (AP-28) | Strategy Memory Upgrade | `strategy_store.py` | +FTS5/RRF, staleness detection, Bayesian validity (~200 LoC) | **CODE LANDED 2026-05-08** (`ad25ade`); active on AR-3 restart |
| 2 (AP-29) | Knowledge Distillation Pipeline | new `knowledge_distiller.py` | L1→L2→L3 tier promotion, MDL consolidation (~300 LoC) | **CODE LANDED 2026-05-08** (`4cdc77e`); wiring deferred |
| 3 (AP-30) | Controller Context Budget | `autopilot.py`, `eval_tower.py` | Progressive disclosure, 5KB gating, token budgets (~150 LoC) | **CODE LANDED 2026-05-08** (`2d4d18f`); helpers in `scripts/autopilot/context_budget.py`, wiring deferred |
| 4 (AP-31) | Mutation Knowledge Graph | `prompt_forge.py` | mutation×failure×outcome tracking, informed crossover (~200 LoC) | **CODE LANDED 2026-05-08** (`49b920c`); sidecar at `scripts/autopilot/species/mutation_graph.py`, wiring deferred |

Phase 1 is directly implementable from the synthesis document. Phases 1+2 parallelize with Phase 3.

**Wiring checklist (AP-29/30/31 — apply on next autopilot restart):**

1. AP-29: at the existing 25-trial auto-checkpoint in `autopilot.py`, instantiate `KnowledgeDistiller(strategy_store).distill(trial_counter)` and log the resulting `DistillationStats`.
2. AP-30: replace flat strategy injection in `dispatch_action` (~line 548) with `format_strategies_tiered()`; wrap eval-tower output return through `gate_eval_output()`; pass each section in `build_controller_prompt` through `apply_section_budget()`.
3. AP-31: in `PromptForge.propose_mutation` cycle end, call `MutationGraph().record(MutationOutcome(...))`. In `_build_mutation_prompt` for `crossover`, inject `informed_crossover_candidates(target_file)` as a "preferred sections" hint.

Test coverage as of 2026-05-08: 46 unit tests across the four AP modules (`tests/unit/test_strategy_store.py`, `test_knowledge_distiller.py`, `test_context_budget.py`, `test_mutation_graph.py`) — all passing.

## Research Intake Update — 2026-04-21

### New Related Research
- **[intake-425] "Memory Transfer Learning: How Memories are Transferred Across Domains in Coding Agents"** (arxiv:2604.14004)
  - Relevance: Cross-domain memory pooling from heterogeneous benchmarks improves coding agent performance by 3.7%. The "Insight" abstraction (title + description + generalizable content, no task-specific details) maps directly to strategy_store entry format. Finding that simple embedding retrieval (cosine on text-embedding-3-small) outperforms LLM reranking validates our FAISS-based approach.
  - Key technique: Four memory representations (Trajectory/Workflow/Summary/Insight) with cross-domain pooling; negative transfer taxonomy (domain-mismatched anchoring, false validation confidence, misapplied best-practice transfer).
  - Reported results: +3.7% average across 6 benchmarks; MTL (431 memories) outperforms AgentKB (5,899 memories) by +1.7%.
  - Delta from current approach: The negative transfer taxonomy is directly actionable for PromptForge mutation safety gates. The finding that task-agnostic insights outperform task-specific insights (+1.1%) suggests strategy_store should favor abstract patterns over concrete implementation traces. Caveat: "Memory Transplants" (ICLR 2026 Workshop) finds architecture transfer is system-dependent and weaker solvers benefit most — the 3.7% gain may not hold for stronger models.

## Research Intake Update — 2026-04-22

### New Related Research

- **[intake-438] "Mind DeepResearch Technical Report"** (arxiv:2604.14518, Li Auto)
  - Relevance: Production multi-agent framework (Planning + DeepSearch + Report) with four-stage training (SFT cold-start + Search-RL + Report-RL + preference alignment). Architecture parallels EPYC's Tier A/B/C role-specialization.
  - Key technique: Agent role specialization via SFT, RL specialization per agent role, multi-dimensional rubric evaluation.
  - Reported results: BrowseComp-ZH 45.7%, WideSearch 46.5%, SOTA 51.8 on MindDR Bench at ~30B scale.
  - Delta from current approach: Our AR-3 explores prompt/structural mutations at the autopilot layer. MindDR explores the agent-role training layer (RL specialization). The two are orthogonal and complementary — RL agent specialization is a longer-term path we haven't opened. Tier 2b contradicting-evidence not run.

- **[intake-441] "Where does output diversity collapse in post-training?"** (arxiv:2604.16027)
  - Relevance: PromptForge mutation diversity depends on base-model output diversity. Paper shows post-training (SFT especially) systematically narrows output distribution — inference-time prompting can't recover training-time diversity loss. This constrains how much diversity PromptForge mutations can realistically generate.
  - Key finding: Diversity loss decomposes into quality-control and residual/genuine-narrowing components; task-dependent.
  - Delta: Factor diversity-collapse awareness into model-selection decisions. When evaluating new post-trained checkpoints for autopilot (e.g., next architect swap), add a diversity metric alongside accuracy.

- **[intake-444] "Agent-World: Scaling Real-World Environment Synthesis for Evolving General Agent Intelligence"** (arxiv:2604.18292)
  - Relevance: Autonomous environment + task discovery with controllable difficulty. Addresses capability-gap identification challenge that parallels autopilot's goal of finding useful mutations.
  - Key technique: Agentic Environment-Task Discovery + Continuous Self-Evolving Agent Training + Multi-env RL + dynamic task synthesis + MCP integration.
  - Reported results: Agent-World-8B/14B beat proprietary baselines across 23 agent benchmarks; scaling correlates with environment diversity.
  - Delta: Environment synthesis as a scaling lever is a different axis from our AR-3 prompt/structural mutation space. Could inform future extensions (e.g., AR-4 that synthesizes new benchmark tasks rather than optimizing against a fixed suite). Tier 2b not run on beat-proprietary claim.

## Deep-Dive Integration — 2026-04-22

### P16 — Strategy Memory Safety Gates (intake-425 + DD4)

Tracked in `routing-and-optimization-index.md` P16. Three adoptable patterns:

- **AP-32: Insight format audit** — **LANDED 2026-06-14** in `epyc-orchestrator` `5d07e52`. `StrategyStore` now records normalized `(title, description, generalized_content)` metadata, exposes normalized fields on retrieval, stores explicit generalized content in the backward-compatible `insight` column, and provides `audit_insight_specificity()` for over-specific stored rows. Converges with AP-28 (strategy memory upgrade, FTS5+RRF). Validation: ruff passed; focused StrategyStore suite passed 24; adjacent StrategyStore/autopilot consumer suite passed 74; py_compile and path-scoped diff check passed.
- **AP-33: Negative-transfer safety gates** for PromptForge — **LANDED 2026-06-14** in `epyc-orchestrator` `0f5cca5`. PromptForge records transfer-safety verdicts on prompt/code mutations, warns when failure context cites fewer than 5 trial IDs, rejects introduced mismatched benchmark-suite anchors, rejects suite-specific universal best-practice generalizations, and prompts mutation proposers with the same AP-33 constraints. The action layer skips unsafe prompt/code proposals before apply/eval/epoch invalidation. Validation: ruff and py_compile passed; AP-33/action/mutation-graph pytest passed 44; path-scoped diff check passed. Adjacent GEPA smoke drift found during validation was repaired in `epyc-orchestrator` `9e484f1`; `tests/test_gepa_integration.py` now imports `controller_io.validate_single_variable` and passes with controller I/O coverage.
- **AP-34: Validate N=3 embedding retrieval** — confirm FAISS top-3 cosine matches or exceeds LLM reranking. Paper shows embedding similarity (0.630 avg) > LLM reranking (0.598) > adaptive rewriting (0.608). Zero code — configuration experiment on next AR-3.

### Environment Synthesis Species → dedicated handoff

Agent-World (DD6, intake-444) env-synth is now a 5th autopilot species, tracked in a dedicated handoff: [`agent-world-env-synthesis.md`](agent-world-env-synthesis.md). Phase 1 training-free and CPU-feasible today (AW-1 `env_synth/` module scaffold is the entry point). Phase 2 multi-env GRPO GPU-gated. Journal-event format (`EnvSynthAction` with `environment_id`/`tool_set`/`synthesized_tasks` fields) will follow AP-3 journal conventions.

### PromptForge diversity-coverage term (DD4-A7)

**Problem**: intake-441 shows post-training diversity loss is structural (in weights). Our mutation search can exhaust "diverse-looking but weight-constrained" space quickly.

**Fix**: add a diversity-coverage term to PromptForge's mutation scoring: penalize mutations that fall into FAISS-dense regions of the mutation embedding space. ~2h once the DD4 diversity baseline lands (NIB2-42 — inference-gated; EV-8 metric fns already landed 2026-04-22).

- [x] **AP-35**: Implement `diversity_coverage_penalty()` in `scripts/autopilot/species/prompt_forge.py` (⚠ path moved from `prompt_forge.py` in the `species/` refactor — verified 2026-06-04). Use existing FAISS index of strategy_store embeddings (live usage in `species/evolution_manager.py` / `species/structural_lab.py` / `actions.py`). Penalty = -log(density) at the mutation's embedding location. ✅ 2026-07-11
- [x] **AP-36**: Wire into the current mutation insertion path. ✅ 2026-07-11. The resolved hook is observe-only mutation-context shaping through `actions._build_mutation_context()` and `propose_mutation` / `propose_code_mutation`; it carries `mutation_diversity_coverage.v1` into `EvalResult.details["mutation_diversity_coverage"]` for prompt/code mutations with `decision`, density, `negative_log_density`, top matches, and `acceptance_effect: none_observe_only` instead of acceptance scoring.

> **EV-8 gate status (2026-06-04 review)**: AP-35/36/37 are gated on EV-8's **inference baseline**, not the whole of EV-8. EV-8's metric functions + `EvalResult` fields already **landed 2026-04-22** (`src/tools/diversity/metrics.py`, `src/safety_gate.py`); what remains is the 1-day diversity baseline run (NIB2-42, inference-gated) the `-log(density)` penalty calibrates against, plus the `to_grep_lines()` wiring.

### GEPA rebalance trigger (DD4-A8)

**Problem**: if mutation diversity stalls (distinct-2 on generated mutations drops below baseline for N trials), species-budget rebalance should trigger before quality regresses.

**Fix**: extend MetaOptimizer with a diversity-stall signal. ~1-2h.

- [x] **AP-37**: Add `distinct2_history` to MetaOptimizer state. Trigger rebalance when `distinct2_t / distinct2_baseline < 0.8` for 10 consecutive trials. **Amended 2026-04-22 post Tier 2b**: couple with `semantic_embedding_agreement` to avoid rebalancing on surface-level distinct-2 drops that don't reflect real diversity collapse (arXiv 2506.00514 metric-gaming critique). Rebalance trigger: distinct-2 drops AND semantic agreement drops AND Verbalized Sampling recovery probe fails to close >50% of the gap. Depends on EV-8's inference baseline (metric functions already landed 2026-04-22 — see EV-8 gate status note above). ✅ 2026-07-11 — landed in `epyc-orchestrator` commit `70878481` as a baseline-gated AP-37 detector: it persists `diversity_stall_state.distinct2_history`, journals `eval_details["ap37_diversity_stall"]`, and invokes `MetaOptimizer.rebalance(..., diversity_stall=...)` only after the distinct-2, semantic-agreement, and VS-recovery signals hold for 10 consecutive observations. Current EV-8 baseline YAML values remain null, so live routing records `baseline_missing` diagnostics until the operator-run baseline fills them.

### Cross-references

- `routing-and-optimization-index.md` P14/P16/P17/P18
- `eval-tower-verification.md` EV-8 (diversity metrics — required prerequisite for AP-35; metric fns landed 2026-04-22, inference baseline pending)
- `agent-world-env-synthesis.md` (full env-synth plan)
- `/workspace/research/deep-dives/diversity-collapse-posttraining.md`
- `/workspace/research/deep-dives/agent-world-environment-synthesis.md`

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-451] "Meta-Harness (official reference code)"** (`github.com/stanford-iris-lab/meta-harness`)
  - Relevance: official companion code for intake-244 (the Meta-Harness paper this handoff's meta-controller echoes). ONBOARDING.md + `domain_spec.md` template is a direct analogue of autopilot's role-spec scaffolding.
  - Key technique: agent-tasks scaffold evolution on terminal_bench_2 — the closest open-source analog to autopilot's code-mutation search space. `claude_wrapper.py` proposer-logging pattern fits PromptForge's audit trail.
  - Delta: cherry-pick ONBOARDING/domain-spec pattern for autopilot's new-role onboarding. Read terminal_bench_2 before any Tier-2b code-mutation upgrade. Do not wholesale port — repo is explicitly "cleaned up version of paper code, not tested beyond running."

## Research Intake Update — 2026-04-26

### New Related Research

- **[intake-474] "TRINITY: An Evolved LLM Coordinator"** (arxiv:2512.04695, ICLR 2026, Sakana AI)
  - Relevance to autopilot: Trinity is the *outer-coordinator analogue* — a learned head that picks per-turn `(LLM, role)` from a heterogeneous pool, replacing what we currently do with Claude in the autopilot loop. The user observation flagged in the deep-dive: our outer Claude-driven layer is the closer Trinity match than our inner inference pool, since Claude vs cheap-frontdoor vs specialist-coder is a wider quality gradient than the all-open inner pool.
  - Key technique: Qwen3-0.6B + 10K-parameter linear head, trained with sep-CMA-ES against terminal binary task reward. Multi-turn protocol: full transcript passed each turn, Verifier-acceptance termination at K≤5.
  - Reported results: 21.9% mean relative-error reduction over the 2nd-best multi-agent baseline across LiveCodeBench / Math500 / MMLU / RLPR. The numbers are *heterogeneous-pool-specific* — discount appropriately for our setup.
  - Delta from current autopilot: autopilot accumulates Q-values over many trials and feeds back into routing decisions. Trinity replaces the per-turn coordination decision itself with a learned head trained against task fitness. **A scoping handoff** [`outer-coordinator-learned-head.md`](outer-coordinator-learned-head.md) **was created 2026-04-26 to evaluate whether replacing part of this loop is worthwhile.** Phase OC-0 (scoping document) gates everything; OC-0.1 explicitly requires reading this handoff and `scripts/autopilot/` to inventory the per-turn decisions Claude makes today.
  - **Action when OC-0 starts**: ensure the autopilot decision inventory (OC-0.1) is exhaustive — missing decisions in the inventory will undersell or oversell the cost-benefit estimate (OC-0.4).
  - Deep-dive: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md), especially section 2.3 ("pool-homogeneity caveat … where does Claude fit?").

## Research Intake Update — 2026-04-27

### New Related Research

- **[intake-479] "Co-Evolving LLM Decision and Skill Bank Agents for Long-Horizon Tasks (COSPLAY)"** (arxiv:2604.20987)
  - Relevance: directly parallels the closed-loop optimization motif here — a learnable skill bank co-evolved with the decision agent, with skills extracted, refined, and updated continuously from unlabeled rollouts. Adjacent to the completed `skillbank-distillation` handoff (recursive evolution + confidence scoring) and to intake-261 (Skill0 / SkillRL).
  - Key techniques: (1) **skill contracts** — schema upgrade for skill-bank entries that bind preconditions/postconditions to each skill, enabling consistent retrieval and reuse; (2) **closed-loop refinement from unlabeled rollouts** — skill discovery pipeline that mines rollouts for new skills and updates contracts based on reward delta, not requiring labeled trajectories.
  - Reported results: 8B base LLM with COSPLAY beats four frontier LLM baselines on single-player game benchmarks (+25.1% avg reward); evaluated across six game environments; competitive on multi-player social reasoning games.
  - Delta from current approach: autopilot already has the closed-loop scaffold (Pareto frontier + checkpointed `autopilot_state.json`). Two adoptable patterns: (a) **skill contracts** as a schema upgrade for any future skill-evolution path (formalize pre/postconditions instead of free-text), and (b) **reward-delta-driven refinement** from unlabeled production traces as a lighter alternative to manually authored eval suites — useful if AP-35 expands toward online optimization with implicit signals. Verdict: `adopt_patterns`, not full framework adoption.

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-498] "Agentic World Modeling: Foundations, Capabilities, Laws, and Beyond"** (arxiv:2604.22748, Chu et al., 42 authors)
  - **Deep-dive**: [`research/deep-dives/agentic-world-modeling-levels-laws-taxonomy.md`](../../research/deep-dives/agentic-world-modeling-levels-laws-taxonomy.md) — comprehensive read with EPYC-stack mapping.
  - Relevance: HIGH (bumped from medium after deep-dive). Survey introduces a "Levels × Laws" taxonomy: capability levels L1 Predictor / L2 Simulator / **L3 Evolver** × four governing-law regimes physical/digital/social/scientific. Autopilot as currently architected is a textbook **L3-Evolver / Digital-laws** instance — the species loop autonomously revises its own model (routing/prompts/structure) based on AR-3 evaluation evidence under software-contract constraints.
  - **L3 governance recipe (Section 5.4) maps line-for-line onto autopilot SafetyGate**: regression gate ↔ quality floor; robustness gate ↔ per-suite guard; rollback policy ↔ Pareto-archive replacement; canary policy ↔ T0/T1/T2 tiered eval tower. Vocabulary alignment is essentially free.
  - **Four evaluation principles (Section 6.1) testable in existing AR-3 today** — long-horizon coherence, intervention sensitivity, constraint consistency, closed-loop use. Adoption cost is rubric documentation + per-cycle reporting; value is identifying intervention-sensitivity gaps in the species framework (e.g., disabling species 0/1/2/3 individually should produce predictable Pareto-front shifts).
  - Adoption plan (CPU-feasible, do now): (1) document L3-Evolver / Digital-regime framing in this handoff's Architecture section, (2) extend AR-3 reporting to label scores by the four principles, (3) verify autopilot SafetyGate implements all four governance prescriptions with explicit reporting; identified gap: SafetyGate uses Pareto-front replacement rather than explicit rollback semantics — worth a one-pager on whether these are equivalent.
  - **Beyond-L3 framing for Species 3 (StructuralLab)**: paper Section 8.2 introduces "governing laws themselves become learnable" as an open direction. StructuralLab modifying flags + routing model lifecycle is the closest EPYC instance, but **do not over-claim** (per closure-inflation feedback memory). We have one species hooking the operating rules of the others, not a principled meta-learning loop. Honest framing only.
  - Cross-cutting: also relevant to `agent-world-env-synthesis.md` (L2-Simulator → L3-Evolver bridge) and `meta-harness-optimization.md` (Tier 3 = another L3-Evolver / Digital instance); the three handoffs should share the four-principle evaluation rubric.
  - MREP (Minimal Reproducible Evaluation Package, Section E.6) is **proposed but not released**. Set watch on matrix-agent/awesome-agentic-world-modeling and arxiv:2604.22748 for shipment; if released, run autopilot through it as external sanity check.
  - Verdict: `adopt_patterns` (vocabulary + four-principle rubric + governance completeness check), NOT full framework adoption.

## Research Intake Update — 2026-04-30

### New Related Research

- **[intake-517] "HALO — Hierarchical Agent Loop Optimizer"** (`github.com/context-labs/halo`, MIT, by inference.net / Context Labs) and **[intake-518] halo-engine PyPI** (pip-installable wrapper, MIT, v0.1.2 released 2026-04-29)
  - Relevance: **HIGH**. Verdict: `adopt_patterns`. HALO is the closest external analogue to autopilot's closed-loop trace → analysis → harness-mutation → re-evaluate cycle. Reported deltas on AppWorld test_normal SGC: Sonnet 4.6 62.5% → 73.2% (+10.7 pts), Gemini 3 Flash 37.5% → 48.2% (+10.7 pts). Findings independently verified against source traces. Built on the foundational RLM paper Zhang/Kraska/Khattab arxiv:2512.24601 (already in our index as **intake-153**).
  - Three concrete patterns worth lifting into autopilot (NOT framework adoption):
    1. **General-harness-overfits-single-trace observation as a design constraint** — argues against using a generic Claude-Code-style coding agent for trace analysis at scale; favors a specialized analyzer (RLM-style, or our own custom).
    2. **dev/test_normal split discipline** — explicit unseen split is a stronger overfitting guard than autopilot's Pareto-archive replacement alone. Cross-ref `feedback_checkpoint_pareto_state.md`.
    3. **Concrete failure-mode taxonomy** (hallucinated tool calls, redundant args, refusal loops, semantic correctness) as **seed labels** for autopilot's trace-clustering pass.
  - Tier 2b contradicting evidence (from RLM literature, applies transitively): production deployment of RLM-based loops faces latency spikes, cost variance, "format collapse"; many OSS RLM implementations pin max_depth=1; recursive-depth claim harder to operationalize than paper implies. Apply skeptically when sizing the analysis-loop budget.
  - Cross-ref intake-153 (RLM foundational paper) — already in index, already verdict `already_integrated` with ~80% pattern coverage. HALO is an applied implementation of those patterns, not a new technique.
  - Action: when an AP-35-class species iteration considers a "trace analyzer" role, evaluate the halo-engine package as a reference implementation (MIT, 2.5 MB, single CLI). Defer adopt_component until a small spike confirms report quality on EPYC orchestrator traces, not just AppWorld.

#### Deep-dive refinement (2026-04-30) — concrete spike scoped, see halo-trace-loop-spike

Deep-dive at [`/workspace/research/deep-dives/halo-rlm-trace-loop-integration.md`](../../research/deep-dives/halo-rlm-trace-loop-integration.md). Spike handoff at [`halo-trace-loop-spike.md`](../completed/halo-trace-loop-spike.md) — ready to claim.

The 1-day spike has a 4-criterion go/no-go gate at end of Day 1 PM. Conditional Day 2 lifts patterns into existing scoped work; **no halo-engine vendoring**. Patterns that affect autopilot specifically:

- **dev/test_normal split discipline** as an anti-overfitting guard for the Pareto frontier — explicit unseen-split is stronger than Pareto-archive replacement alone (per `feedback_checkpoint_pareto_state.md`).
- **Failure-mode taxonomy seed labels** (hallucinated tool calls, redundant args, refusal loops, semantic correctness) for autopilot's trace-clustering pass.

Most autopilot infrastructure that HALO would build is already done: `telemetry.py:to_otlp_span` (OTLP emission since 2026-04-12), trace-driven mutator (Tier-1 done), code-mutation search (Tier-2 done), GEPA evolution (intake-345 done), RLM REPL recursion (intake-153 R1-R6 done at ~80% pattern coverage). The spike specifically tests whether HALO's *analyzer* surface produces actionable findings against our autopilot trial telemetry — it is NOT a wholesale autopilot rewrite.

---

## Session 2026-05-16 — Recovery + host-health integration + journal purge

### Trigger

Autopilot was running 8.5h producing garbage data. Quality had collapsed from the April plateau (1.14 avg) to 0.6-0.9 today. User asked "Can we review the autopilot's progress?"

### Root-cause chain (verified)

1. **gemma4 worker_general spinning 95 cores idle.** Yesterday's `OMP_WAIT_POLICY=passive` fix had silently broken MTP first-decode coordination (`llama_decode ret=-3`, server hangs forever on first request). Reverting passive → active brought MTP back but then the libomp team busy-loops between requests.
2. **architect_general crashed.** GGML_ASSERT in `common_speculative_state_tree::draft` — Qwen3.5-122B's M-RoPE refuses position rollback when speculative draft tokens are rejected. Persistent across np=1/np=2 attempts. Mitigated by setting `_NO_SPEC_DECODE = {"architect_general"}` in orchestrator launcher — disables -md flag for architect, retains moe_expert_reduction.
3. **Half the stack down.** Ports 8080/8081/8083/8084 had no listening processes; seeder's `model_registry.yaml` `port:` fields pointed at those quarter-mode ports while launcher used full-mode 8070/8071/8072. Seeder `[INFRA_SKIP] worker_general` resulted from this mismatch, not from gemma4 actually being unreachable.
4. **Duplicate Qwen3.6-35B Q8 server.** frontdoor (8070) + coder_escalation (8071) running TWO copies of same GGUF — 72 GB duplicate mlock + 2× competing 96-thread OMP teams. Removed in `ROLE_LAUNCH_META`: coder_escalation aliased onto frontdoor's server via `shared_with_first_n`. **+69% frontdoor throughput** from removing the contention.
5. **Registry cross-section conflict.** `architect_general` had `acceleration` in BOTH `server_mode.X` and `roles.X` with **different `type:` values** (`moe_expert_reduction` vs `speculative_decoding`). RegistryLoader silently picked one; my edits to the other no-op'd, costing ~2h of debugging time.

### Fixes landed in code

| Fix | File | Verified |
|---|---|---|
| `KMP_BLOCKTIME=10` for binary_override roles (gemma4 MTP) | `orchestrator_stack.py:1944` (worker_pool branch) | gemma4 idle cores 95.05 → 0.00; threads sleep on `futex_wait_queue`; frontdoor +78% / coder +207% / ingest +177% throughput |
| `_NO_SPEC_DECODE = {"architect_general"}` gate | `orchestrator_stack.py:1659` | architect serves cleanly at 12.5 t/s (was crashing) |
| `_renice_all_threads(pid, 19)` per-thread renice helper | `orchestrator_stack.py:1251` | all 289 gemma4 threads at nice=19 on fresh launch (CLI `renice -p PID` only does lead thread) |
| Same-GGUF consolidation: `frontdoor.shared_with_first_n = [coder_escalation, worker_summarize]` | `orchestrator_stack.py:371-388` | 36 GB freed; one OMP team |
| `load_state()` drops non-ProcessInfo stubs | `orchestrator_stack.py:820-832` | `status` / `stop --all` no longer crash on dict entries |
| Registry validator on `cmd_start` | `src/registry/registry_validator.py` (new) | strict-load + cross-section + same-GGUF-same-port checks; catches the architect dup |
| Registry compile from master (opt-in `--compile-registry`) | `src/registry/registry_compiler.py` (new) | SHA-256 cache key; transitive draft/alias dep resolution; produces 10-role lean view |
| Host-health auto-remediation | `scripts/autopilot/host_health.py` (new) + `safety_gate.py` (wire-in) | Throttle / freq / page-cache detection; auto-runs `sudo /usr/local/sbin/autopilot-flush-cache` before attributing throughput violation to config |
| Master registry `architect_general` reconciliation | `epyc-inference-research/orchestration/model_registry.yaml:559+` / `:1170+` | `roles.X.acceleration` no longer references swapped-out Qwen3-235B-A22B |
| **AP-38 (2026-05-23): constrained-creativity planner** — stagnation-gated rich-prompt fragment (gated on `hv_slope_10 < eps` OR `trustworthy < 5` OR 3-trial action-type streak); tail samples promoted from candidates to seeds; 6-axis rubric collapsed to 3 orthogonal axes (info_gain / coherence / cost-adjusted usefulness); fusion preference + quote-don't-regenerate anti-drift rule; `JournalEntry` gets `falsifier` + `rubric_scores` fields via `autopilot_rationale` sidecar block; new `ExperimentJournal.unfalsified_hypotheses()` helper surfaces still-open claims to next planner pass | `scripts/autopilot/{autopilot.py, controller_io.py, experiment_journal.py, program.md}` + `tests/unit/{test_autopilot_controller_io.py, test_autopilot_creativity.py}` | **67/67 autopilot unit tests passing**. End-to-end LLM smoke ran 2026-05-24 (`/workspace/tmp/smoke_rationale.py` + saved response): action + rationale both parse, rubric carries all 3 axes + synthesis_note, Claude noticed the open falsifiers were resolved and chose `distill_knowledge` instead of another seed. Deep-dive: [`research/deep-dives/2026-05-23-creativity-constrained-tail-search.md`](../../research/deep-dives/2026-05-23-creativity-constrained-tail-search.md) (HTML companion in same directory) |
| **AP-39 (2026-05-24): pull-forward of AP-38 deferred items** — `STAGNATION_HV_EPS` now auto-calibrates from `ParetoArchive.hv_slope_noise_floor()` (k × rolling std, clipped to `[1e-6, 1e-3]` so only ever tightens; on live state with 211 hv entries calibrated to 1.0e-5). `JournalEntry.stagnation_signal: str` records which gate signal fired per trial (empty for lean trials); new `ExperimentJournal.action_diversity_by_gate(window)` returns per-bucket Shannon entropy + distinct-action-type counts so the lean-vs-rich diversity comparison surfaces naturally as the next autopilot run accumulates trials — no separate experiment needed | `scripts/autopilot/{autopilot.py, experiment_journal.py, pareto_archive.py}` + `tests/unit/test_autopilot_creativity.py` (+4) | **67/67 autopilot unit tests passing**. Closes AP-38's "end-to-end smoke", "behavioral check ≥20 trials", "calibrate STAGNATION_HV_EPS" deferred items |
| **AP-40 / OS-1 (2026-05-24): launcher per-instance thread count + role-quartering audit + autopilot pause-around-flush** — Two coupled fixes prompted by the frontdoor throughput investigation. **(1)** `build_server_command()` was called without `numa_instance`; `_resolve_thread_count` always returned `instances[0][2]` so every frontdoor quarter got `-t 96` instead of `-t 48` (the workaround in `_build_worker_explore_command` lines 336-343 was the only role that handled this correctly). Fix threads `numa_instance` through to all callers; workaround removed. **(2)** Phase 0.5 quarter-fit benches showed `ingest_long_context` (12.3 t/s/quarter), `vision_escalation` (20.1 t/s/quarter, best of any role), `worker_vision` (11.4 t/s/quarter) all qualify for the full+4×quarter ConcurrencyAwareBackend pattern that frontdoor + worker_general use today. Added quarter entries to NUMA_CONFIG for these 3 roles + wired their URLs in `src/config/models.py` with the `full:` prefix. Also migrated frontdoor's full instance from NUMA_NODE0 (NPS2-era half-socket leftover) to NUMA_FULL + `numactl --interleave=all` for consistency with worker_general/architect_general. **(3)** Discovered + fixed cached-state pause bug: `autopilot.py pause` was a no-op on running autopilots because `state` was loaded once at `autopilot.py:701` and `save_state(state)` after each trial clobbered any externally-set True. Fix reloads `paused`/`_in_cache_flush` from disk at the top of every iteration. **(4)** New `host_health.flush_cache_with_pause()` does pause → flush → NUMA-interleave-rewarm all role GGUFs serially → restore paused state. Wired into `safety_gate._hh_remediate()` and the new operator-facing wrapper `flush_cache_safely.py`. New `DeficiencyCategory.EXOGENOUS_CACHE_FLUSH` so trials completing during a flush window get journal-quarantined like AP-39's EXOGENOUS_RELOAD. | `scripts/server/{orchestrator_stack.py, stack_numa.py}` + `scripts/autopilot/{autopilot.py, experiment_journal.py, host_health.py, safety_gate.py, program.md}` + new `scripts/autopilot/flush_cache_safely.py` + `src/config/models.py` + new tests in `tests/unit/{test_orchestrator_stack_threads.py, test_host_health_pause_around_flush.py}` | **80/80 autopilot+launcher unit tests passing**. Phase 0 benches at `/workspace/tmp/phase0_bench_results.txt` showed the launcher fix will NOT recover frontdoor's regression (today's 10 t/s ≈ achievable ceiling on contended stack — Q8 35B's BW-bound under current concurrent load; the per-instance fix is correctness, not throughput). Stack restart deferred to operator. Phase 0 finding worth flagging: NPS4 single-quarter pattern that worked beautifully on 30B Q4 (46.6 t/s) does NOT transfer to 35B Q8 (8.9 t/s) — Q8 needs more BW than one quarter provides. So frontdoor's quartering at -t 48 gives slightly LOWER per-quarter than the old -t 96; the topology stays for concurrent-serving capacity but per-quarter solo perf is now correct-but-modest. |
| **AP-41 (2026-05-28): dual-provider draft/critique planner** — planner invocation is now provider-coordinated: Claude remains the default drafter, Codex can serve as fallback drafter and secondary critic, provider failures trip a circuit breaker, and the executor still receives one canonical `autopilot_actions` block. Default mode is conservative `shadow_critique`: fallback is active, but critic revisions are logged rather than applied. Active critic reconciliation requires `AUTOPILOT_PLANNER_MODE=draft_critique`. | `scripts/autopilot/{autopilot.py, planner_providers.py, planner_coordinator.py}` + `tests/unit/{test_autopilot_planner_providers.py,test_autopilot_planner_coordinator.py}` | **52/52 focused tests passing**: controller IO, provider parsing, coordinator fallback/critique/circuit tests, recovery, and GEPA import coverage. `gitnexus impact invoke_controller --direction upstream --repo epyc-orchestrator --include-tests`: LOW, confined to Autopilot loop. README/wiki wrap-up note: wiki compile saw unrelated parallel handoff edits, so AP-41 is documented here and in progress only; no broad wiki synthesis was committed from this session. |
| **AP-42 (2026-05-31): controller relaunch safety closure** — Closing fixes for running J6 in controller mode instead of seeder-only mode. Codex critic stdin handoff repaired; active `draft_critique` no longer approves parse/invoke failures; `_ACTION_SCHEMAS` covers all 14 controller actions so prompt/critic/executor field drift is rejected at the universal gate; `slot_compact` prompt/schema/handler agreement restored; mutation dirty-target fence blocks writes and forge commits when the exact target file/path already has pending shared-clone work. | `scripts/autopilot/{planner_coordinator.py,planner_providers.py,controller_io.py,autopilot.py,actions.py}` + `tests/unit/{test_autopilot_planner_coordinator.py,test_autopilot_controller_io.py,test_autopilot_actions_dirty_fence.py}` | Commits: `d5c3a2f` pushed; `af84514` and `e58a79c` local-only ready to push. **145/145 focused autopilot tests passing**, `py_compile` ok, `git diff --check` ok. Live relaunch was attempted after hardening: WAL recovery journaled killed trials 188/189; trial 190 produced a real Codex critique (`revise`, confidence 0.89) and dispatched `rollback`. Current wrap-up state: no autopilot process running, `in_flight_trial=190` still present, journal max `189`, `consecutive_failures=0`; restart/recovery is pending before J6 can continue. |
| **AP-43 (2026-05-31): baseline/frontier/distillation contamination closure** — Closed the full re-contamination chain after the relaunch audit. `Baseline.save()` path leak fixed by `a231556`; `89e6c9f` adds load-path archive-max and archive-first baseline promotion; `ec9622d` excludes Tier-0 fast-reject trials from Pareto frontier/hypervolume/archive-max while retaining them in `all_entries`; `20ea4d5` scrubs legacy-scale failure text in `EvolutionManager.distill()` input and output. Live cleanup scrubbed journal JSONL/TSV + AP-22 memory, purged six `source_trial_id>=180` strategies, and rebuilt DB/FAISS/id_map to 241 with 0 legacy `9.900/-6.900` hits. | `scripts/autopilot/{safety_gate.py,pareto_archive.py,species/evolution_manager.py}` + `tests/unit/{test_safety_gate_baseline_eligibility.py,test_baseline_scale_guard.py,test_pareto_archive_tiers.py,test_evolution_manager_scrub.py}` + runtime backup `orchestration/legacy_scale_cleanup_backup_20260531_122902/` | Tests: 46 archive/safety/recovery, 23 actions/creativity, and 31 distill/scrub/safety checks passed. Autopilot is stopped after cleanup. Next restart should begin at trial 569 against baseline `quality: 1.16`, with the archive target anchored to T1 best quality ~1.895 instead of saturated T0 `2.400`. |
| **AP-44 (2026-05-31): planner-context stale telemetry closure** — Closed the third leak: in-scale stale planner reasoning (`q=2.400`, `2.900`) in recent journal summaries and trials 180–183 could still bias draft planning even after archive/frontier/distill fixes. `summary_text()` now downclasses T0 as audit-only and hides all bug-corrupted metrics/reasons; progress plots use the same T1/T2 + trustworthy filters. Trials 180–183 were tagged `bug_corrupted_by=ec9622d`; HV history was backfilled from T1/T2 archive entries only; docs plots refreshed. | `scripts/autopilot/{experiment_journal.py,progress_plots.py}` + `tests/unit/{test_journal_prompt_sanitization.py,test_progress_plots_filters.py}` + `docs/autopilot/*.png` | Commit `ebd5647` passed 47 focused autopilot tests, `py_compile`, and `git diff --check`. A restart probe ran trial 184 to T1 q=1.816 and marked it `mad_noise`; unrelated autopilot tool-policy mutation `d50b77c` was reverted by `12d6afb` after existing `test_tool_policy.py` rejected it. No autopilot process is running. Current state: `trial_counter=185`, `in_flight_trial=None`, `consecutive_meta_actions=0`. |
| **AP-45 (2026-05-31): learning-excluded keep-signal closure** — Closed the planner-context poison that caused the trial-188 meta-loop halt: `mad_noise` trials already skipped archive/AP-22 learning, but the journal still stored self-criticism as `keep` with “continue exploring this surface,” which the planner interpreted as evidence while also seeing no trustworthy progress. Learning-excluded trials now get explicit `SelfCriticism(... keep_or_revert="excluded" ...)` before journaling, with controller-facing text saying not to treat the outcome as a keep/config-efficacy signal. | `scripts/autopilot/{autopilot.py,self_criticism.py,experiment_journal.py}` + `tests/unit/test_classify_learning_exclusion.py` | GitNexus impact LOW for `classify_learning_exclusion`, `_run_loop_inner`, `JournalEntry`, and `ExperimentJournal.summary_text`. Validation: 21 focused learning-exclusion/journal/MAD tests passed; 89 broader autopilot unit tests passed; `py_compile` and `git diff --check` passed. Autopilot remains down pending operator restart decision. |
| **AP-46 (2026-05-31): historical poison-state prune** — Closed the forward-only gap left by AP-45. Existing rows 184/186/187 and the meta/distill strategy rows already written before the code fix were removed from the active runtime state so the next planner prompt cannot cite them as evidence. | Runtime state only: `orchestration/autopilot_journal.{jsonl,tsv}`, `orchestration/autopilot_state.json`, `scripts/autopilot/short_term_memory.md`, `orchestration/repl_memory/strategies/*`, and local tags `autopilot/trial-{184,186,187}`. Backups: `/mnt/raid0/llm/tmp/autopilot-prune-20260531-205634/`. | Verified active journal has no trial IDs 184/186/187 and no `bug_corrupted_by=mad_noise`; `ExperimentJournal.trustworthiness_score()` reports only `autopilot_killed_mid_trial:17` and `ec9622d:4`; strategy SQLite/FTS/FAISS/id-map all count 241 with no active `#184`/`#186`/`#187`, `mad_noise`, or “continue exploring this surface” hits; state is `paused=true`, `trial_counter=188`, `consecutive_meta_actions=0`, no dispatch/halt latch. No inference or live trial was run. |
| **AP-47 (2026-06-22): pareto_epoch_ts deinflation not applied to in-memory archive** — Dashboard showed HV=67.86, live autopilot log reported HV=76.09; appeared stale but plot was actually current (trial 967). Root cause: `_journal_archive_payload_for_authority()` called `reconstruct_archive_from_journal_rows()` without `deinflate_before_ts`/`deinflate_factor`, so the in-memory archive included 5 pre-epoch trials (77, 118, 146, 166, 207) with inflated speeds 71–86 t/s (speed double-count bug pre 2026-06-01). Dashboard reconstruction applies `pareto_epoch_ts`×0.5 deinflation; those 5 entries become dominated (halved speed ~35–43 t/s) and drop off, giving correct HV=67.86. The undeinflated in-memory archive also caused autopilot dominance checks to use the inflated frontier, potentially suppressing genuine post-epoch improvements. | `scripts/autopilot/autopilot.py` — 4 call sites updated; new `_deinflate_params_from_state()` helper added; `_journal_archive_payload_for_authority`, `_apply_journal_archive_authority`, `_sync_startup_archive_from_journal_authority`, `_run_loop_inner`. | Commit `b781c569`. 252 pareto/journal unit tests pass (1 pre-existing unrelated failure excluded). Fix is hot-applied: next trial save will re-sync the in-memory archive with deinflation. No restart required. |

### Journal data purged

Polluted trials 314-322 (today's run) removed from `autopilot_journal.tsv` + `.jsonl`. Backups at `orchestration/autopilot_journal.{tsv,jsonl}.bak-20260509-094821`. Pareto archive in `autopilot_state.json` did not contain those trials (state.json wasn't updated mid-trial). Trial counter at 323; next trial keeps that ID (no gap-renumbering).

### Frontdoor throughput investigation — open

User noted bench CSVs (`epyc-inference-research/benchmarks/results/reviews/qwen36_q8_0_baseline.csv`) show 25-30 t/s per-question for Qwen3.6-35B Q8, while current measurement is 12.5 t/s.

git bisect across 62 llama.cpp commits between April 24 (`e734a682`) and May 2 (`2ffbdbbba`) identified the first-bad commit as **`2ffbdbbba` — "fix: gate TIDE dynamic early exit"**. The pre-fix binary silently dropped ~12.5% of layers for ALL models via TIDE, producing **+30% throughput AT THE COST OF corrupted output**. Reproduced verbatim: `--n-layer-exit 5..56` on current binary, real bench prompt → output emits `TargetExceptionTargetException`, `TemplateName`, mixed CJK garbage (matching the commit message's description). **TIDE was the inflated bench number; your fix was correct.**

But: even with the April 20 binary (pre-TIDE entirely, head `81df3f7c`), bench recipe in TOTAL isolation (all other servers killed, fresh `drop_caches`, 1068 GB mem free) only delivers **12.13-12.48 t/s**, not 26. CPU boost is correct (3.9 GHz all-core, 4.5 GHz single-core peak). The 26 t/s bench-era number is currently unreproducible. Most likely cause per `feedback_host_throttle_check`: sustained multi-day uptime (6d 18h) with cumulative throttle that `drop_caches` no longer fully restores.

**Next test (operator action)**: reboot, then re-run bench-recipe in isolation. If 25 t/s recovers, host-state hypothesis confirmed and no code action needed. If still 12.5, the binary or model file state has genuinely changed since April 20 and needs deeper investigation.

### Autopilot relaunch readiness

- Runtime poison state cleared: active journal rows 184/186/187 removed; AP-22 short-term memory refs removed; 65 contaminated strategy rows pruned; strategy SQLite/FTS/FAISS/id-map aligned at 241.
- State is restart-order-independent: `paused=true`, `trial_counter=188`, `consecutive_meta_actions=0`, no `_dispatch_deficiency`, no `_meta_halt_reason`.
- Local dangling tags `autopilot/trial-184`, `autopilot/trial-186`, and `autopilot/trial-187` deleted.
- Autopilot remains down/paused. No inference or live trial was run during cleanup.

**Awaiting operator decision on credits/overage and explicit restart/resume timing.**

## Research Intake Update — 2026-05-20

### New Related Research

- **[intake-571] "ECHO: Terminal Agents Learn World Models for Free"** (Papailiopoulos et al., MSR AI Frontiers; PDF, no arxiv)
  - **Relevance**: The autopilot loop IS a terminal agent (bash + orchestrator tool calls). ECHO's "predict-the-environment" auxiliary loss is the training-time analogue of what autopilot already does empirically — gather rollouts, observe terminal responses. If/when we train a small specialized model for autopilot's coordinator role, ECHO-style auxiliary loss is a cheap add-on.
  - **Key technique**: Joint action + observation prediction on the same GRPO rollout; no masking; ~2× over baseline GRPO across Qwen3 family.
  - **Delta from current approach**: Pure training-time technique, GPU-gated. Out of scope for the current CPU-only autopilot, but worth noting in the gpu-acceleration-path watchlist alongside SkillRL and Endless-Terminals (intake-574). The pattern itself (treat all bytes in a rollout as training signal, not just policy bytes) is a useful frame even for non-training contexts — e.g., consider whether the Pareto archive should also score "tool-response predictability" as a co-objective.

### ECHO Deep-Dive Refinement — 2026-05-20

**ECHO authors and exact numbers corrected** (local PDF read at `/tmp/echo.pdf`): authors are Shrivastava/Awadallah/Papailiopoulos (MSR), not the earlier-guessed Gandhi/Garg/Goodman. Exact loss `L_total = L_GRPO + 0.05 · L_Env`. TB-2.0 pass@1: Qwen3-8B 2.70%→5.17%, Qwen3-14B 5.17%→10.79%. **Verifier-free claim is overstated** — Table 4 shows env-only fine-tune REGRESSES TBLite by −3.9pp from seed. Advertised public repo `github.com/microsoft/echo-rl` is 404 as of 2026-05-20; no training code, no checkpoints. Reproduction requires 8×B200, infeasible even on a single DGX Spark.

**EPYC-actionable spinoff (NOT ECHO)** — borrows the "prediction error = understanding" intuition without any training:

- **PEAF (Prediction-Error-As-Feature, NEW work item, LOW priority, doable today)**: For each probe the autopilot controller proposes, log an **expected-terminal-output** prediction (a tiny LM call against a current SOTA local model) BEFORE running the probe. Then measure surprise (e.g., token-overlap or perplexity of actual response under the predictor) and persist it alongside the probe's reward in the Pareto archive. Test whether surprise correlates with config-quality gradient. If it does, promote to an explicit Pareto co-objective. Cost: logging-only; ~zero compute overhead per probe. Cheap-kill criterion: if surprise has no correlation (r²<0.1) with gradient over 200+ probes, abandon. This is NOT a reproduction of ECHO — it is an inference-time analogue of the underlying intuition, and is the only ECHO-adjacent thing buildable on CPU today.

## Deep-Dive Task Proposals — 2026-05-25 (intake-607 Code-as-Agent-Harness §5.2.1 / §5.2.3 / §5.2.4)

Two ideas from the Code-as-Agent-Harness survey land on the Pareto-archive optimizer. Audit pass converted the brainstorm into concrete acceptance and storage contracts.

> **Schema dependency (gap-fix 2026-05-25):** `behavior_signature` (BSV-1) and the `harness_metrics` fields HLE-4 consumes live in the **shared trace schema owned by [`unified-trace-memory-service.md`](unified-trace-memory-service.md) § "Shared Harness/Trace Schema"**, not a private autopilot store. Reuse `event_id` links; do not duplicate payloads. Shared schema lands before BSV-1/HLE-4 writes.

- [x] **HLE-4 — Harness-level objective dimensions (beyond the 4D Pareto).** The current archive optimizes quality × speed × −cost × reliability on *task outcomes*. The paper argues final-task-success is a noisy single bit that rewards shortcut configs. Add the per-component harness metrics defined in [`meta-harness-optimization.md`](meta-harness-optimization.md) HLE-1 (execution fidelity, feedback interpretation, planning stability, memory coherence, recovery rate) as **observe-only fields first**, then promote them to guardrails or co-objectives only after they show predictive signal. Required implementation pieces:
  - ✅ Extend `EvalResult` / journal JSONL with `harness_metrics`, `oracle_adequacy`, and `metric_schema_version` (`931e43c`).
  - ✅ Compute rule-based HLE-1 metrics and register HLE-2 oracle-adequacy defaults in observe-only form (`9222a19`).
  - ✅ Analyze N trials: 2026-06-12 snapshot contained 580 metric-bearing trials (`51..779`). `execution_fidelity` and `planning_stability` separate keep/revert but are not independent enough to promote; `feedback_interpretation`, `memory_coherence`, and `recovery_rate` fail signal/missingness gates.
  - Cheap-kill result: current rule metrics remain diagnostic/advisory and do not enter Pareto selection. Any future HLE promotion requires N2 per-question ledgers/sequential verdicts and a redesigned metric with independent predictive signal.
- [x] **BSV-1 — Behavior-signature versioning for archive integrity.** We are AHEAD of the paper on raw regression gating (quality floor, per-suite guard Δq<−0.1, throughput floor, auto-rollback, git-committed reverts). The remaining gap: a newly-accepted config can silently break a *prior* Pareto win because improvements are merged syntactically, not behaviorally. Attach a **behavior signature** to each archive member. Minimum signature fields: per-sentinel final outcome, normalized answer hash, route path, tool-call sequence hash, escalation path, latency bucket, token bucket, key harness metrics, and oracle-adequacy version. Store both a compact hash for fast diff and an expanded JSON vector for explanation. **2026-06-21 partial archive-member wiring**: orchestrator `9a175eac` makes the default-off BSV observe path use real archive-member IDs (`trial:<id>`), journal compact `signature_hash` plus the expanded vector, and persist a `bsv_archive_signatures` state index for frontier-accepted, safety-passing archive members. Orchestrator `31e7e008` then upgraded the partial sentinel vector to prefer compact per-question `EvalResult.question_results` (`qid`/`question_id` -> pass/fail) before falling back to the old per-suite quality proxy, with `sentinel_outcome_source`/`sentinel_outcome_count` diagnostics. **2026-07-05 process-signal enrichment**: orchestrator `c7590be6` folds already-journaled `question_results` tool counts/names, route aggregates, and latency into the observe signature, with legacy aggregate `tool_name_counts` / request-timing fallbacks and explicit `process_signal_sources` diagnostics. BSV-1 is now closed after normalized answer hashes and full trace-store IDs landed; BSV-2 still needs the paired-eval lane before gating.
  - [x] **BSV-1a — normalized answer-hash signature support.** `epyc-orchestrator` commit `009e919b` adds normalized raw-answer hashing in `src/behavior_signature.py` and lets the BSV observe path consume pre-populated per-question `answer_hash` / `normalized_answer_hash` rows without persisting raw answers. Validation: 73 BSV/signature/trace-schema tests passed, Ruff passed, `py_compile` passed, GitNexus re-indexed cleanly. ✅ 2026-07-11
  - [x] **BSV-1b — live compact eval-row answer hashes.** `_compact_question_result()` now emits `question_results[].answer_hash` for successful answers using the same normalizer as `src/behavior_signature.py`, while still stripping raw `prompt`/`answer` text and leaving error rows un-hashed. Landed in `epyc-orchestrator` commit `19a424fe` after dedicated eval-tower-boundary review. Validation: 117 eval-tower/BSV/core-v2/analytics/trace-schema tests passed, Ruff passed, `py_compile` passed, GitNexus re-indexed cleanly. ✅ 2026-07-11
  - [x] **BSV-1c — full trace-store IDs.** `harness_metrics_id` and trace `event_id` are still diagnostic/missing in the observe path; wire them only through the shared trace schema, not duplicated private payloads. ✅ 2026-07-11
- [ ] **BSV-2 — Differential testing on accept.** Before promoting a mutation, run new vs old on the same sentinels and compare behavior (not just aggregate score). Prefer paired sequential execution under identical server/model snapshot for attribution; use parallel execution only when explicitly approved and when concurrency cannot contaminate latency measurements. Reuse the existing T0/T1 tower; the novelty is paired behavioral comparison. Gate on both scalar regression and signature diff severity. **2026-06-21 scaffold**: orchestrator `0943e7c0` adds `scripts/autopilot/bsv_paired_report.py`, a read-only paired report over already-journaled `question_results` vectors. It emits shared-qid coverage, McNemar/accuracy deltas, BSV signature severity, blockers, JSON/Markdown, and nonzero exit on a blocked candidate. Follow-up `5b29eead` adds `eval-result-pair`, so the same report can compare standalone paired-run EvalResult-like JSON artifacts without needing journal ingestion first. Orchestrator `939750c7` adds `scripts/autopilot/bsv_paired_runner.py`: a default-safe plan-only CLI that, with explicit `--run`, applies baseline/candidate params sequentially, evaluates the same core, writes baseline/candidate EvalResult JSON artifacts, restores baseline params by default, and emits the existing BSV paired report. Follow-up `a3570d8d` restores baseline params even when candidate application fails before candidate eval. Orchestrator `2bdb7abc` wires the mutation accept path behind default-off `AUTOPILOT_BSV2_ACCEPT_GATE`: prompt, GEPA, and code mutations run a pre-mutation baseline eval only when the flag is on, compare baseline/candidate EvalResult vectors through the paired-report backend, reject/revert on `gate_decision=block` or blocking signature severity, accept+annotate watch/pass cases, and preserve existing single-eval behavior when the flag is off. Remaining work is operator-approved live paired runs / rollout evidence before enabling the flag in production windows.
- [ ] **BSV-3 — Conflict-aware acceptance.** When two independently-accepted mutations touch the same subsystem (prompt + routing, two prompts, prompt + tool policy, context packer + batch editor), flag potential *semantic* conflict for review rather than blind compose. **2026-06-21 observe-only ledger landed in orchestrator `168e9bd8`**: under `AUTOPILOT_BSV_OBSERVE=1`, frontier/safety-passing trials now append a bounded `bsv_mutation_dependency_ledger` state row and journal `eval_details.bsv_observe.mutation_dependency` / `conflict_report`, keyed by `subsystem`, `files_touched`, `prompt_sections_touched`, `feature_flags`, `behavior_signature_delta`, and `parent_trial`. Conflict severity increases on shared subsystem/file/section/flag overlap, blocking BSV deltas, different behavior surfaces, or disjoint/opposing sentinel movement across accepted mutations. Still observe-only/default-off; open work is production conflict-policy enforcement after BSV-2 paired-gate rollout evidence is available.
  - [x] **BSV-3a — default-off diagnostic-state conflict policy.** `epyc-orchestrator` commit `d9b8a022` adds `AUTOPILOT_BSV3_CONFLICT_POLICY` (`off`/`observe`/`block`/`review`) inside the existing `AUTOPILOT_BSV_OBSERVE=1` post-SafetyGate/post-Pareto block. It can withhold only BSV ledger/incumbent diagnostic-state promotion on configured conflict severities; it does **not** alter SafetyGate, Pareto admission, action accept/revert behavior, blacklists, baselines, routing, or the planner spend breaker. ✅ 2026-07-11

#### BSV-2/BSV-3 operator rollout packet - prepared 2026-07-11

This packet is for rollout evidence only. It does not enable `AUTOPILOT_BSV2_ACCEPT_GATE`, does not switch `AUTOPILOT_BSV3_CONFLICT_POLICY` to enforcement, and does not change live accept/revert behavior.

- **Plan-only paired run preview:** `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/autopilot/bsv_paired_runner.py --baseline-params '{}' --candidate-params @/path/to/candidate_params.json --output-dir orchestration/reports/bsv2_paired_preview_20260711`. Omit `--run` to keep it plan-only; plan mode prints target artifact paths but does not create the output directory or paired report.
- **Live paired evidence:** add `--run` only in an operator-approved quiet window. Leave baseline restoration enabled; `--no-restore` is reserved for an explicit operator decision to keep candidate params applied.
- **Evidence fields to inspect:** paired-report `gate_decision`, shared-qid coverage, accuracy delta, McNemar/statistical diagnostics, BSV signature severity, fleet/version marker, restored-baseline status, and any blocking `conflict_report` entries.
- **Promotion boundary:** `gate_decision=block` or blocking signature severity remains a no-go. BSV-3 `block`/`review` policy should not be promoted past observe-only until BSV-2 has live paired-run evidence under the same gate semantics.
- [x] BSV-2 plan-mode validation: `bsv_paired_runner.py` without `--run` returns `mode=plan`, `eval_mode=t1`, `tier=1`, `t1_n=50`, `restore_baseline=true`, and target artifact paths only; no eval artifacts or report are written until an operator-approved live run. ✅ 2026-07-11

**Audit refinements / missed gaps**:

1. **Behavior signatures must include process, not just answers.** Final-answer hashes miss regressions where a config gets the right answer via forbidden web-search leakage, extra escalations, or much higher cost. Include route/tool/escalation/token features.
2. **Diff severity needs a policy.** Not every signature change is bad. Define severity classes: `benign` (format-only/latency bucket unchanged), `watch` (route/tool path changed but score same), `blocking` (prior Pareto sentinel flips pass→fail, forbidden shortcut appears, or cost/latency bucket crosses guardrail).
3. **Paired eval must control model state.** KV warmth, server reloads, exogenous restarts, and concurrent traffic can swamp a harness delta. BSV-2 should record fleet marker/version and reuse the exogenous-restart metadata already added in the resilience work.
4. **Archive compatibility needs migration.** Existing Pareto entries lack signatures. Backfill what can be computed from journals/traces and mark older entries `signature_confidence=partial`; do not compare partial and full signatures as equal evidence.
5. **HLE-4 and BSV should share storage.** Store harness metrics and behavior signatures in the same journal/trace event family so AP-27 verifiers and HALO/P20 analyzers read one schema.

Sibling: the **PEAF** item above (prediction-error-as-feature) is independent — HLE-4/BSV are about *what we measure and how we gate*, PEAF is about *a new feature to log*. Roll-up: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P24/P25. Interacts with AP-27 (RLVR eval tower — the verifier must score the augmented objectives). Source: intake-607 `deep_dive` in `research/intake_index.yaml`.

## Post-result conditional workflow + mitigation (HLE-4 / J9, BSV-2 / J11)

**HLE-4 (J9) — observe-only result.** Pre-run wiring is built: `EvalResult`/journal JSONL fields landed in `931e43c`, and HLE-1/HLE-2 observe-only computation/registration landed in `9222a19` (shared schema owned by `unified-trace-memory-service.md`). The 2026-06-12 analysis over 580 metric-bearing trials keeps current metrics diagnostic/advisory only: `execution_fidelity` and `planning_stability` separate keep/revert but mostly mirror existing quality/reliability/safety signals; `feedback_interpretation` is low-confidence/low-variance; `memory_coherence` is constant; `recovery_rate` is missing on 99.3% of rows. No Pareto co-objective/guardrail promotion before N2 per-question ledgers/sequential verdicts and a redesigned metric with independent predictive signal. Mitigation remains: low-signal/low-confidence metrics never gate; oracle-adequacy flags shortcut-prone suites so they cannot drive promotion.

**BSV-2 (J11) — mutation accept gate.** Pre-run wiring: `compute_behavior_signature` is done, orchestrator `9a175eac` attaches default-off observe signatures to concrete archive-member IDs with a compact state index for frontier-accepted members, `31e7e008` makes partial observe signatures prefer per-question sentinel outcomes when the eval tower provides `question_results`, `c7590be6` adds process-aware observe signatures for tool/route/latency drift, `0943e7c0` adds the read-only paired report that combines same-qid scalar deltas with signature severity/blockers, `5b29eead` lets that report consume standalone paired-run EvalResult-like JSON artifacts via `eval-result-pair`, `939750c7` adds the explicit paired inference runner, and `2bdb7abc` wires prompt/GEPA/code mutation accept handlers behind default-off `AUTOPILOT_BSV2_ACCEPT_GATE`. Per candidate mutation, paired new-vs-old on the same sentinels → `diff_signatures` severity: `benign` → auto-accept; `watch` (route/tool changed, outcomes equal) → accept + log; `blocking` (prior-pass sentinel regressed, forbidden shortcut, or cost guardrail crossed) → **REJECT, do not promote**; shared-subsystem touch → BSV-3 conflict-ledger review. Mitigation: gate accept on BOTH scalar regression AND signature severity; partial-confidence signatures cannot certify `benign` (audit #4); git-committed revert remains the backstop. Operator decision trees mirrored in [`bulk-inference-campaign.md`](bulk-inference-campaign.md) Package J.

## Research Intake Update — 2026-05-27

### New Related Research

- **[intake-615] "Fortytwo: Swarm Inference with Peer-Ranked Consensus"** (arxiv:2510.24801)
  - Relevance: closer formal analog to NumericSwarm Pareto scoring than the SiliconSwarm@Ensue entry (intake-248) already feeding B1/B4/B5. Bradley-Terry-style aggregation over peer rankings is the explicit version of "pairwise comparison with confidence" we approximate via 4D Pareto + hypervolume.
  - Key technique: heterogeneous models generate independently → pairwise-rank each other's full completions → reputation-weighted Bradley-Terry aggregation → winner.
  - Reported results: +17.21pp on GPQA-Diamond (85.90 vs 68.69 majority voting); 0.12% vs 6.20% prompt-injection degradation.
  - Delta from current approach: NumericSwarm uses NSGA-II/Optuna over a 23-param numeric surface scored by an eval tower. A Bradley-Terry mode would replace the 4D scalarization with pairwise peer judgments on candidate configurations' eval-tower outputs — useful when the scalarization is the noisy step (high hypervolume variance) and the judging is cheap. Concrete integration probe: when `hypervolume_slope() < 0.001` triggers stagnation, instead of (or before) switching to CEM sampling per the intake-269 TPO note, run pairwise judging of the top-K candidates and let the BT-aggregated ranking break ties. Code reference: `numeric_swarm.py:99` (sampler init), `pareto_archive.py:188-200` (stagnation detection).
  - Caveat: claim that the same swarm "beats GPT-5/Claude Opus/Gemini" is founder-marketing only — the paper's actual baseline is majority voting.

- **[intake-614] Fortytwo Network — chunk-ranking pipeline (unpublished founder claim)**
  - Relevance: if real and disclosed, chunk-ranking = mid-stream cross-model ranking against milestones during single-shot generation, which would let an ensemble vote without paying N-rounds latency. That is a primitive we currently do NOT have any analog of in the autopilot loop or the orchestrator. Tracked as a watch item until they publish.

## 2026-06-07 — Per-suite regression gate made resolution-aware (trial-707 halt fixed)

Autopilot self-halted 06-06 @ trial 708 (`critic_reject_loop`). Root cause: the per-suite
regression gate used a fixed `-0.1` floor against per-suite scores quantized to `{0,1.5,3.0}`
(~2 questions/suite on the hybrid T1 eval). One question flipping = a `-1.5` "regression" =
15× the floor, so the gate fired every seeder trial → `mad_noise`-excluded → planner looped on
`seed_batch` → critic halted it. The planner's eval-artifact diagnosis was correct; the codex
critic's "broken-instrument, no evidence" rejection was wrong (evidence = the quantized per-suite
METRIC lines). This is the concrete mechanism behind the long-standing **MAD over-exclusion** open item.

Landed (epyc-orchestrator, uncommitted): `per_suite_regression_threshold()` widens the floor to
the coarser single-flip quantum `3/n` using new `EvalResult.per_suite_counts` +
`Baseline.per_suite_counts_by_tier` (empty ⇒ legacy `-0.1`); `classify_learning_exclusion()` now
treats `mad_noise`/`reproduction_confirmed` as benign **only when `verdict.passed`** (trial 707
failed 3 per-suite checks yet was admitted as a "trusted within-noise representative"); `autopilot.py`
failed-but-not-benign trials skip the clean archive/baseline update. 11 new tests; patched gate
clears the exact trial-707 numbers. Full write-up: `epyc-root/progress/2026-06/2026-06-07.md`.

**Outstanding (operator):** (1) baseline-count refresh is optional — result-side counts already fix
it and baseline counts self-populate on the next clean T1 trial; a live refresh eval is operator-run.
(2) Restart is an operator call — `autopilot_state.json` was externally rewritten 06-07 16:04 to
`paused=false`/counter=0 (already restart-ready, but not done by the fix session).

## Research Intake Update — 2026-06-10

### New Related Research
- **[intake-692] "Economy of Minds: Emerging Multi-Agent Intelligence with Economic Interactions" (EoM)** (arxiv:2606.02859, Qi/Kakade/Lakkaraju/Du, Harvard/MIT)
  - Relevance: a Hayekian agent **economy** whose population lifecycle maps onto autopilot species management — agents accumulate wealth from environmental rewards; **wealthy (effective) agents are mutated via exploitation, bankrupt (ineffective) agents are replaced via exploration**. This is a clean conceptual analog for autopilot's Pareto/cost-aware species selection and for decision-aware-routing reward shaping.
  - Key technique: auction-allocated action rights + peer-to-peer payments → decentralized credit assignment with **no explicit communication protocol**; economic selection drives emergent multi-step reasoning from weak-agent init.
  - Reported results: outperforms stronger monolithic baselines across five agentic tasks (abstract-level; per-task numerics not published).
  - Delta from current approach: **adopt the pattern, not the system.** The literal auction/payment machinery presumes many concurrent agent instances + per-action auctions — incompatible with the EPYC single-stack, no-concurrent-inference, sequential-load constraint. Transferable: the wealth-gated-mutation / bankruptcy-gated-replacement lifecycle and local-reward credit assignment as inputs to species management. Not peer-reviewed yet; no independent reproduction.

### Deep-Dive Refinement (2026-06-12) — downgrade to metaphor-mostly
EoM's "auction" is fixed-bid first-price (= static priority + random tie-break, `hayekmas/base/mas.py`) and its wealth ledger is the **softmax-over-effectiveness bandit autopilot already runs**: `ExperimentJournal.species_effectiveness()` (`experiment_journal.py:759`, `rate = pareto/total`) → `MetaOptimizer.rebalance()` → weighted-random `select_species()` (`meta_optimizer.py:136`). EoM's only novel content — **bucket-brigade temporal credit assignment** — needs a multi-step **live-reward episode with N concurrent agents**, which the sequential single-config trial policy (+ no-concurrent-inference rule) doesn't have → **non-portable**. **No decision-aware-routing action** (routing is single-shot; bucket-brigade only helps multi-step live-reward episodes). One *optional* ~60-LOC item: a `SpeciesLedger` replacing `rebalance()`'s hand-tuned constants (`0.30 + rate*0.2`, floors, stagnation boosts) with a rent+reward `softmax(wealth)`. **Gate:** `AUTOPILOT_SPECIES_LEDGER=shadow` for ≥80 trials (never routes), KEEP only if ledger weights predict next-window Pareto contribution strictly better AND remove ≥3 magic numbers; else close as `metaphor_only` (likely DROP — same Pareto signal). No auctions, no payments, no species deletion. Full: `research/deep-dives/2026-06-12-economy-of-minds.md`.

## Research Intake Update — 2026-06-20

### AB-MCTS Thompson allocation (intake-720)

- **[intake-720] "Adaptive Branching Monte Carlo Tree Search (AB-MCTS)"** (arxiv:2503.04412, Sakana AI; ICLR 2025 Workshop) — three transferable patterns, complementary to existing autopilot machinery rather than net-new scope; the only multi-LLM headline (ARC-AGI-2 >30%) used frontier APIs, not CPU-local.
- **[intake-720] Pattern 1 — Thompson-Sampling "go-wider/go-deeper" budget allocation** — a principled replacement for autopilot's *current* heuristic **weighted-random species selection**: `select_species()` at `meta_optimizer.py:139-145` is literally `random.choices(species, weights=weights, k=1)` over `rebalance()`-tuned budget weights (docstring "weighted random") — **no bandit, no posterior exists today**. AB-MCTS samples per-arm posteriors to decide widen-vs-deepen each step; the same posterior could replace the bare `random.choices` draw. Same selection-step surface flagged in § Scoring Upgrade Backlog rows #2/#3 (intake-269 CEM, intake-615 BT) and as the optional `SpeciesLedger` softmax(wealth) in the EoM deep-dive — implement **one** selector experiment first and A/B, do not stack.
- **[intake-720] Pattern 2 — per-model online Bayesian posteriors as a NO-TRAIN routing alternative** — distinct from the *staged* MLP routing classifier, which is OFF in prod (`routing_classifier=false`) with Phases 1.5+ FROZEN per `fable5-findings-02`. AB-MCTS-style per-model posteriors update online at inference with zero training run. Tie to **decision-aware-routing DAR-1**: its **0.00% identifiable regret** is the gating signal any online bandit also needs — a posterior router only earns a flip if it beats that identifiable-regret bar, same as the MLP head must.
- **[intake-720] Pattern 3 — mixed-effects variance separation (CHAPTER RECOMMENDATION only)** — AB-MCTS separates initial-generation variance from refinement variance via a mixed-effects model; this is a **ch08 reward-model design idea** to note, not handoff scope. We do **not** edit chapters from here — flagged for the chapter owner.
- **[intake-720] Complementary, not competing** — `tri-role-coordinator-architecture` + [`outer-coordinator-learned-head.md`](outer-coordinator-learned-head.md) learn a coordinator **OFFLINE** (sep-CMA-ES / RL); AB-MCTS does **NO training** (online posteriors at inference). The two approaches address the same coordinator decision from opposite ends (offline-trained head vs online posterior), so they can be compared, not merged.
- **[intake-720] Caveats (observations, not decision-gating)** — verifier-dependent; up to **512 model calls/query** in-paper; the headline multi-LLM result (ARC-AGI-2 >30%) ran on frontier APIs. A 512-call verifier-gated tree is **not CPU-deployable as-is** on the EPYC single-stack — only the Thompson allocation / online-posterior *patterns* transfer, not the budget envelope.

### DecentMem dual-pool memory (intake-715)

- **[intake-715] "DecentMem: Decentralized Memory for Multi-Agent Systems"** (arxiv:2605.22721) — transferable element is the **decentralized per-agent dual-pool STRUCTURE** only: an **exploitation pool** of consolidated trajectories + an **exploration pool** of LLM-generated candidates. Useful as a **comparative datapoint** for the `strategy_store` evolutionary memory, alongside the already-queued HCC tiered-memory + staleness work. **NOT new scope** — a structural comparison, not a build item.
- **[intake-715] CONFLICT to flag** — DecentMem's per-stage **LLM-as-JUDGE reweighting** collides with autopilot **AP-27** ("state matching, **NOT LLM-as-judge**") and with the 2026-06-12 **P17.BT-4 KILL** of judge-model peer scoring on cost grounds. Therefore **only the dual-pool structure transfers, not the judge-reweighting mechanism** — do not import the per-stage judge reweighter.
- **[intake-715] Evidence status (observations)** — **no released code**; reported accuracy/regret numbers are cloud-favorable on small backbones over AutoGen / DyLAN / AgentNet, frameworks we do **not** run, so the numbers are observations only and cannot gate a decision here.

## Research Intake Update — 2026-06-25

### New Related Research

- **[intake-726] Terminal-Bench / Harbor Framework** (github.com/harbor-framework/terminal-bench)
  - Relevance: The runnable Docker-based harness for TB Core v0.1.1 (89 tasks). Already cross-referenced in this handoff (terminal_bench_2 is "closest open-source analog to autopilot's code-mutation search space"). This entry confirms it's `adopt_component` — pip-installable, actively maintained (updated today), MIT/Apache licensed.
  - Key technique: Harbor registry system (19 dataset versions), Docker sandboxing, automated test-script verification, multiple agent adapters (Terminus, Claude Code, Codex CLI)
  - Reported results: Top scores on TB Core v0.1.1 — Codex CLI + GPT-5.2 at 63%; Terminus 2 + Claude Opus 4.5 at 58%
  - Delta: The repo has a CLAUDE.md describing a PostgreSQL+SQLAlchemy+Supabase backend. Primary value is as an external capability calibration point: run our stack against the 89 TB Core tasks to measure absolute task-completion rate against a fixed, human-verified benchmark.

- **[intake-727] "Efficient Benchmarking of AI Agents"** (arxiv:2603.23749, Ndzomga, March 2026)
  - Relevance: Cost-reduction technique for *external fixed-task evals* (Terminal-Bench Core), NOT autopilot's rotating pool. MR filter optimizes cross-agent ranking; autopilot does within-system regression detection — opposite sensitivity. Analysis of autopilot journal (141 trials with question_results): 50-qid stable core has only 3/50 qids in the mid-range — filter would decimate it. See `eval-benchmark-cost-reduction.md` for full constraint analysis.
  - Key technique: Mid-Range Difficulty Filter (IRT-motivated); Leave-One-Scaffold-Out protocol; Spearman ρ as rank-stability metric
  - Reported results: 101 agents on TB2.0 (23 fixed tasks, 23 scaffolds), mean ρ = 0.94, 44–70% task reduction
  - Delta: Apply AFTER running our stack against TB Core v0.1.1 (89 fixed tasks). The filter then reduces future TB re-evaluations from 89 to ~37–50 tasks. For autopilot, the pass-rate data is more useful for *question pool curation* (rotating out permanently saturated/floor qids from `simpleqa`, `general`, `coder` stable core) than for subset selection.
  - Caveat: solo preprint, credibility_score 2; the autopilot stable core has 3 mid-range qids out of 50 — do not apply the filter to the autopilot eval tower.

## Research Intake Update — 2026-06-26

### New Related Research

- **[intake-730] "Ornith-1.0: Self-Scaffolding LLMs for Agentic Coding"** (DeepReinforce blog; weights at intake-729, HF `deepreinforce-ai/ornith-1.0`; **no arXiv paper** — note: arxiv:2606.25996 is an unrelated Meta FAIR "Autodata" paper, indexed as intake-731)
  - Relevance: **Design-pattern reference for the autopilot RL loop and W7 game-layer hardening — NOT an eval-tower or scoring change.** Ornith's RL jointly optimizes the *agentic scaffold* (memory/error-handling/orchestration logic) **and** the solution rollout under a *shared reward*, so the harness co-evolves with the policy toward higher-reward trajectories. This is the closest external analog to autopilot's strategy-store evolution (StructuralLab flag-toggles + PromptForge resolver/prompt strategies co-evolving with the numeric surface) — i.e. the system learning *how it searches*, not just *what it proposes*.
  - Key technique (most relevant piece): a **three-layer anti-reward-hacking defense** that maps almost 1:1 onto autopilot's W7 game-layer concerns — (1) an *immutable outer trust boundary* (env/tools/test isolation kept outside model reach; the policy may only evolve the inner scaffold), (2) a *deterministic monitor* that zero-rewards + excludes trajectories that read withheld paths, modify verifier scripts, or use out-of-surface tools, and (3) a *frozen LLM-judge veto* layered on top of the verifier to catch intent-level gaming inside the allowed surface. Compare to W7's critic measurement view, audit-stream gaming alarm, and production eval sampling clamp.
  - Secondary technique: asynchronous pipeline-RL with a token-staleness weight `w(d_t)` (1 below K1, exp-decay K1→K2, 0 above K2) on a token-level GRPO loss for off-policy long rollouts — relevant only if autopilot ever moves to a true RL gradient loop (currently evolutionary), so park as background.
  - Reported results (vendor self-reported, treat as observation per MEASUREMENT.md): Ornith-397B TB-2.1 77.5 / SWE-Bench Verified 82.4; 35B TB-2.1 64.2; 9B TB-2.1 43.1. Independent corroboration is release-only (MarkTechPost/TestingCatalog reproduce the vendor table); some observers dismiss the numbers as "benchmark farming." No independent eval as of 2026-06-26.
  - Delta from current approach: autopilot already isolates the eval/verifier boundary (W6 audit, W7 alarms); Ornith adds the explicit framing that the *scaffold itself is an RL-optimized object with the same reward-hacking surface as the policy* — a useful lens when reviewing whether strategy-store-authored scaffolds can game the critic. **No code action proposed here**; this is a conceptual cross-reference. The deployable-model angle (Ornith 9B/35B GGUF on Gemma4/Qwen3.5 bases as coder/worker candidates) is a separate benchmark-gate candidate, not in this handoff.

- **[intake-731] "Autodata: An Agentic Data Scientist to Create High Quality Synthetic Data"** (arxiv:2606.25996, Meta FAIR — Kulikov, Whitehouse, Weston et al., June 2026)
  - Provenance: surfaced via an arXiv-ID mismatch on the 2026-06-26 Ornith intake (the operator submitted this ID believing it was the Ornith paper; it is not). On operator follow-up ("I thought Autodata would be relevant to autopilot"), a code-grounded deep-dive raised its relevance **low → medium (method, not deployment)**.
  - Relevance: **a difficulty-calibration upgrade for the `env_synth` 5th species — NOT a change to the existing static eval pool.** Autodata calibrates synthetic-task difficulty by targeting the gap between a *weak* solver (expected to fail) and a *strong* solver (expected to pass): keep a task only when `strong_pass ∧ weak_fail`. Autopilot's `env_synth` species (`scripts/autopilot/species/env_synth/`: `ETDAgent → TaskSynthesizer[DifficultyBand] → VerifierBuilder → SolvabilityGate`) already synthesizes tasks, but its `SolvabilityGate` (AW-4, `species.py:77-101`) is **one-sided** — it only rejects tasks a *strong reference model cannot solve* (upper bound). It has no weak-model lower bound, so it can still admit trivially-easy tasks that pass the gate and *worsen* the documented saturation problem (suites ~90-94%; stable core has only 3/50 mid-range qids — see the 2026-04 / intake-727 updates above) rather than fix it.
  - Key technique to borrow: add the **weak-fail lower bound** to `SolvabilityGate`. The hosting scaffold already exists — `DifficultyBand` in `task_synthesizer.py` and the `ReferenceSolver` callback in `species.py` — so this is a calibration upgrade, not a new subsystem. Feasible **CPU-locally**: strong signal = `architect_general`/worker; weak signal = a cheap small model (a small Qwen, or the Ornith-1.0-9B at intake-729). No GPU, no frontier API.
  - What does NOT transfer (refuted on deep-dive): Autodata's **meta-optimization outer loop** trains the data-generator agent itself; autopilot's `meta_optimizer.py:68-137` only rebalances species *budgets* and detects hypervolume stagnation — it never trains a generator policy, and doing so would need GPU SFT/RL. Treat the paper's training-stack headline (and its token-truncation efficiency gains) as **low-relevance until the MI210 lands (~July 2026)**.
  - Reported results (observation only, per MEASUREMENT.md): a 4B model RL-trained on agentic data beats a CoT-trained one on CS research (0.774 vs 0.727) and legal reasoning (0.441 vs 0.377, beating the 397B baseline 0.404); meta-optimization raised CS validation pass rate 62.1% → 79.6% over 233 iterations. These come from GPU fine-tuning, so they inform *expected direction*, not our gate.
  - **Hard constraints and landed scaffold:** (1) any synthesized task that can gate keep/revert/promote decisions touches the **human-amendment-only eval trust boundary** (MEASUREMENT.md) and needs operator promotion; (2) W6's core-vs-audit generalization-gap alarm (`audit_block_report.py:266-286`) is precisely where an optimizer minting its own gating questions would be caught as gaming — so `env_synth`-synthesized tasks must stay **out of the decision-gating audit set** unless human-promoted. Orchestrator `43d4c8c3` adds the weak-fail lower-bound scaffold to `SolvabilityGate`: callers may provide a `weak_reference_solver`, but the check is non-binding unless `require_weak_failure=True`; when enforcing, it rejects tasks that the weak solver solves confidently and fails closed on weak-solver errors. Validation: `tests/unit/test_env_synth_species.py` covers non-binding acceptance, enforced weak-solve rejection, weak-fail acceptance, and weak-solver error fail-closed behavior. Remaining work is wiring a concrete weak solver and promotion policy when AW-5/EvalTower integration is next active; no decision-gating eval set changed.

## Research Intake Distillation — DGM + Harness-Evolution (2026-07-02)

Source findings: **intake-772** Darwin Gödel Machine (arXiv 2505.22954, verdict `adopt_patterns`, relevance HIGH) and **intake-753** "Don't Train the Model, Evolve the Harness" (verdict `adopt_patterns`). Per MEASUREMENT.md the DGM SWE-bench (20→50%) / Polyglot (14→31%) and the harness-evolution legal-benchmark (63→80%) numbers are **observations** — they shape the proposer/archive contract, they do not gate any keep/revert/promote decision without local re-measurement. Deep-dive companion for the LoRA/harness lineage: `research/deep-dives/2026-07-02-cross-model-lora-transfer-cluster.md`.

**Governance framing up front.** Three of our surfaces are inside the MEASUREMENT.md human-amendment-only trust boundary — the SafetyGate verdict (`safety_gate.py:783 check`), the scoring/objective (`eval_tower.py` cost axis), and the sequential-verdict e-process (`safety_gate.py:680`). Any pattern below that touches them is a **proposal to the operator**, not an autopilot-mutable change. `program.md`'s immutable boundary already forbids the loop from editing its own eval methodology, scoring, or gates, so the DGM *self-referential self-improvement* axis is **non-applicable by design** (see Pattern 3).

---

### Pattern 1 — Bounded "stepping-stone" archive lane (dominated-but-novel parents)

**(a) Current behavior.** We do **not** literally delete dominated configs: `ParetoArchive._all_entries` (`pareto_archive.py:91`, appended at `:266`) retains every trial, and `_rebuild_frontier` (`:233`) only drops dominated points from the *per-tier frontier* (`:243-246`), never from `_all_entries`. **But functionally this is a greedy prune from the optimizer's point of view**: the planner prompt is built at `autopilot.py:3571-3572` from `archive.summary_text()` + `geometry_text()`, both of which read `_front(tier)` — **frontier only**. Dominated-but-novel entries are never surfaced to the controller, never offered as a seed, and never re-run. Parent basis is `species_history[-1]` (`autopilot.py:4364-4367`) — the chronologically previous same-species trial — not an archive sample. So a config that was novel but Pareto-dominated is archive-dead.

**(b) Proposed change.** Add a bounded, diversity-sampled *stepping-stone lane*. Lowest-risk delivery is a new `ParetoArchive.stepping_stones_text(k=…)` render method (sibling to `geometry_text`) that surfaces K dominated-but-novel `_all_entries` — sampled for diversity, not score — into the planner prompt at `autopilot.py:3571-3576`. Novelty can reuse the existing BSV behavior signatures (`bsv_observe.py`, wired at `autopilot.py:4380-4442`) or config-diff distance; bound the lane by size (e.g. ≤8 candidates) and recency. This is **pure prompt context** — the LLM controller may then propose an action seeded from a stepping-stone, but nothing is auto-re-run. A heavier follow-up (only if the observe pass shows value) is extending the `rollback` action (`autopilot.py:2103,4330`) to accept an arbitrary archive `trial_id`, not just `production_best`/checkpoints.

**Status 2026-07-11:** observe-only Pattern 1 is already landed in orchestrator:
`ParetoArchive.stepping_stones()` / `stepping_stones_text()` select dominated
near-frontier rows, `pareto_stepping_stones_report.py` exposes a read-only report,
the planner prompt appends the block behind `AUTOPILOT_STEPPING_STONES` (default
on), and phase health reports the flag. Validation re-run on 2026-07-11:
`ruff check` on stepping-stone/phase-status files; `.venv/bin/python -m pytest
tests/unit/test_pareto_archive_tiers.py tests/unit/test_pareto_stepping_stones_report.py
tests/unit/test_autopilot_phase_status.py -q` → 29 passed. Remaining Pattern 1
work is the heavier explicit replay/rollback path, which is still operator-window
work and not part of the observe-only lane.

**(c) Risk + gate.** Prompt-context version: near-zero risk (no new eval, no gate touched, no archive-authority change) — it cannot promote anything on its own. The re-run follow-up costs one serial eval per revisited stepping-stone and so is bound by the **single-user no-concurrent-inference constraint** (operator-scheduled only). Any config revisited still passes the unchanged SafetyGate: quality floor `safety_gate.py:869`, resolution-aware per-suite gate `:950-959`, MAD/`mad_noise` filter `:897-948`, and — when enabled — the sequential verdict `:680`. No change to promotion authority; a stepping-stone only earns a frontier point by winning on the existing 4D dominance test.

**(d) Effort.** **S** for the observe-only `stepping_stones_text` prompt block; **M** if the `rollback`/`explore_from_trial` re-run path is added.

---

### Pattern 2 — Performance × fecundity parent sampling

**(a) Current behavior.** No fecundity weighting anywhere. Two selection points: (1) species choice is weighted-random by budget — `MetaOptimizer.select_species` (`meta_optimizer.py:139`), budgets rebalanced by per-species *Pareto-frontier rate* (`:110-121`), which is performance-at-the-species-level but blind to which individual configs are productive parents; (2) parent-of-record for a trial is `species_history[-1]` (`autopilot.py:4364-4367`), used only for `config_diff` + lineage journaling, not to choose what to mutate. The fecundity data already exists and is unused for selection: `ParetoArchive.children_of(trial_id)` (`pareto_archive.py:477`) and `lineage()` (`:480`).

**(b) Proposed change.** Add a parent-sampling helper that weights candidate configs by `score × (1 + productive_children_count)`, where "productive" = children that were frontier-eligible or passed the gate (computable from `children_of` + each child's `pareto_status`/verdict). This helper feeds the Pattern-1 stepping-stone/explore seed choice — i.e. when the controller (or the future `explore_from_trial` action) needs a base config, sample it fecundity-weighted rather than "last-of-species".

**(c) Risk + gate.** Non-applicability caveat: our numeric inner loop is **Optuna-internal** (`numeric_swarm.py:160 study.ask()`, TPE/NSGA-II picks its own seed) — fecundity sampling does **not** and should not reach inside the Optuna study. It applies only to the cross-config *explore/seed* choice and could optionally bias `select_species`. Risk is that fecundity concentrates the search on a few prolific lineages and *reduces* diversity — the opposite of Pattern 1's intent — so the two must be co-tuned and validated together (Pattern 3). No verdict/scoring boundary is touched; this is selection, not acceptance.

**(d) Effort.** **M** (new sampling function + a consumer; only meaningful once Pattern 1 gives it a seed to consume).

---

### Pattern 3 — DGM's two ablations as our A/B template (the gate for Patterns 1 & 2)

**(a) Current behavior.** We have the A/B machinery already: `bsv_paired_runner.py`, `paired_stats.py`, the anytime-valid sequential verdict (`safety_gate.py:680`, default-off `AUTOPILOT_SEQ_VERDICT`), and the seq/W6 readiness reports (`seq_readiness_report.py`). What we do not have is a codified *archive-authority* ablation protocol.

**(b) Proposed change.** Adopt DGM's two ablations as the **required justification harness** before any archive-authority change from Patterns 1–2 is promoted from observe-only to authoritative:
- *no-open-ended-exploration* arm = frontier-only parents (today's behavior).
- *stepping-stone-on* arm = Pattern 1 + Pattern 2 lane enabled.
Run them as a paired A/B through `bsv_paired_runner.py` + `paired_stats.py`; require the sequential verdict to reach `confirmed` (both E-quality and E-rate-non-inferiority ≥ `confirm_e`, `safety_gate.py:753-760`) before flipping any authority.

**Explicit non-applicability.** DGM's *no-self-improvement* ablation has **no analog we can toggle** — our meta-loop, gate, and scoring are human-authored and outside `program.md`'s mutable scope + the MEASUREMENT trust boundary. Our system is *permanently* in the no-self-improvement condition; only the open-ended-exploration axis is a live variable. Say this plainly in any writeup so the DGM "self-rewriting agent" framing is not mis-read as a proposal to let autopilot edit its own controller.

**(c) Risk + gate.** This *is* the gate — it consumes serial inference for the paired arms, so it is operator-scheduled under no-concurrent-inference. Low code risk (reuses existing paired/seq infra).

**(d) Effort.** **S** (protocol + runner wiring; the statistics already exist).

---

### Pattern 4 — Prefer deterministic-code mechanisms over prompt edits

**(a) Current behavior.** We already implement the *capability*: Tier-2 `code_mutation` action with allowlist + deep validation (SafetyGate rows added 2026-04-04), `StructuralLab` flag toggles, and `config_applicator.py` for flag/config/registry changes — all model-agnostic, alongside PromptForge prompt edits. What we lack is (1) an explicit *mechanism-type* effectiveness split and (2) a *per-served-model* prior. `MetaOptimizer.rebalance` (`meta_optimizer.py:68`) weights by per-species Pareto rate but never distinguishes "code/flag/config transferred" from "prompt playbook stuck to one model".

**(b) Proposed change.** Two steps, observe-first: (i) add a mechanism-type effectiveness split to `digest.py` — group journal entries by `species` + `action_type` (code_mutation / structural_experiment / numeric_trial vs prompt_mutation) and report frontier-rate per mechanism class, **observe-only**; (ii) *if* the split reproduces the intake finding locally (code > prompt for our frozen served models — gemma worker, v6 fleet), add a small mechanism-class prior into `rebalance()` that up-weights structural/numeric/code over prompt_forge. The intake's cross-family transfer caveat (code transfers, prompts don't) argues this prior should be **keyed per served model**, matching our v6/gemma-worker split.

**(c) Risk + gate.** Step (i) is zero-risk observe-only. Step (ii) shifts search budget, not acceptance — but it must be *measured, not assumed* (MEASUREMENT: the intake is a single non-peer-reviewed legal benchmark). Gate: the mechanism split must show a real, resolution-aware separation before the prior is wired. No trust-boundary surface touched by the budget prior itself.

**(d) Effort.** **S** for the digest split; **M** to wire and validate a per-model prior.

---

### Pattern 5 — Cost-aware scoring (tokens) + per-served-model harness tuning

**(a) Current behavior.** Cost objective is role-tier based: `cost = mean(cost_tier)/4.0` (`eval_tower.py:1308-1310`). We **already compute** a tokens-based cost signal — `tokens_per_solved_task` (`eval_tower.py:1298`) — but it is journaled as a diagnostic and **not scored** into the Pareto objective (`ParetoEntry.objectives` = quality, speed, −cost, reliability). The harness is tuned once, not per served model, despite the 2026-06-26 v6 cutover + gemma-worker consolidation changing what is served.

**(b) Proposed change.** The transferable bits of the harness-evolution scoring `pooled_criterion + 0.5·all_pass − 0.005·tokens_per_million` are: (i) make the cost axis reflect **tokens** (`tokens_per_solved_task`) rather than only static role `cost_tier` — more honest and already computed; (ii) treat an `all_pass` bonus as a planner prior. **Do NOT** collapse our 4D Pareto into their scalar — vector dominance is a deliberate design strength, and scalarizing would be a regression. So the concrete proposal is a token-honest cost axis (observe-only shadow axis first), plus a per-served-model re-tune pass of the harness now that v6/gemma are the served fleet.

**(c) Risk + gate.** The cost axis is part of the Pareto objective, which sits **inside the MEASUREMENT.md trust boundary** → **operator-approval required**, not autopilot-mutable. Introduce it as an observe-only shadow objective first (journaled, not promoting), compare against the current `cost_tier` axis, and only swap with operator sign-off + an era-row note (`instrument_eras.yaml`), since it redefines objective #3. Per-model re-tune consumes serial inference → operator-scheduled.

**(d) Effort.** **S** for the observe-only shadow cost axis; **M+operator** to promote it and run the per-model re-tune.

---

### Summary map

| Pattern | Maps onto | Boundary | Effort |
|---|---|---|---|
| 1 Stepping-stone lane | `pareto_archive.py` `_all_entries`/render; planner prompt `autopilot.py:3571` | prompt-context: none; re-run: no-concurrent-inference | S → M |
| 2 Fecundity parents | `children_of` `:477`; `select_species` `:139`; parent `:4364` | selection only, no verdict | M |
| 3 Two-ablation A/B | `bsv_paired_runner.py` + `_sequential_verdict:680` | the gate itself; self-improvement axis N/A | S |
| 4 Code>prompt prior | `digest.py`; `meta_optimizer.rebalance:68` | budget only; measure first | S → M |
| 5 Token cost axis | `eval_tower.py:1298,1308` | **trust boundary — operator** | S → M |

### Do-this-first (highest value / lowest risk)

1. **Stepping-stone prompt block (Pattern 1, observe-only) — S.** Add `ParetoArchive.stepping_stones_text(k)` surfacing ~8 diversity-sampled dominated-but-novel `_all_entries` into the planner prompt at `autopilot.py:3571-3576`. Pure context, no new eval, no gate/authority change, reversible. Directly attacks the local-optimum risk the DGM archive addresses, and is the prerequisite that gives Pattern 2 & the re-run path something to consume.
2. **Mechanism-type effectiveness split in `digest.py` (Pattern 4, step i) — S.** Group journal entries by mechanism class (code_mutation / structural / numeric vs prompt_mutation) and report resolution-aware frontier-rate per class, observe-only. Zero risk, and it either confirms or falsifies the intake's "code > prompt for frozen models" claim on *our* fleet before we change any budget prior.
3. **Codify the two-ablation archive-authority A/B protocol (Pattern 3) — S.** Write the frontier-only vs stepping-stone-on paired protocol on top of the existing `bsv_paired_runner.py` + `_sequential_verdict`, and make it the required gate for promoting Patterns 1–2 from observe-only to authoritative. No new mechanism — it just makes any later authority flip defensible. Requires operator scheduling for the paired inference runs.

Deferred (needs operator sign-off / more inference): fecundity parent sampling (Pattern 2, only once #1 lands), the `explore_from_trial` re-run path (Pattern 1 follow-up), the token-honest cost axis and per-model harness re-tune (Pattern 5 — inside the MEASUREMENT trust boundary). None of these should be wired by a sub-agent or self-mutated by the loop; all are operator-gated per CLAUDE.md.

### Implementation status (2026-07-02)

Patterns **1, 3, 4 are IMPLEMENTED** (observe-only) in the current orchestrator branch.
The original isolated branch was `dgm-harness-patterns-2026-07-02` (`d820e94f`), and
the current `spec-dec-mtp-refresh-2026-06-22` branch contains the same live surfaces:
`pareto_archive.py` (`stepping_stones`/`stepping_stones_text`), `autopilot.py`
(planner-prompt append, gated by `AUTOPILOT_STEPPING_STONES`, default on),
`digest.py` (`_mechanism_effectiveness_section`), and
`STEPPING_STONE_ABLATION_PROTOCOL.md`. Verified again 2026-07-11 on the current
branch: `ruff check` on the touched Pattern 1/3/4 files and `.venv/bin/python -m
pytest tests/unit/test_pareto_archive_tiers.py tests/unit/test_autopilot_phase_status.py
tests/unit/test_economic_ledger.py -q` → 32 passed. The live autopilot daemon still
requires the normal stale-code/preflight restart gate before these branch changes are
runtime-active. Patterns **2** (fecundity parents) and **5** (token cost axis —
MEASUREMENT trust boundary, operator-only) are **DEFERRED**, gated on Pattern 1 landing
+ the Pattern 3 ablation.

### Eval-task coverage guardrail (2026-07-04)

Operator concern: the planner may be optimizing tunables against a small repeated
question slice instead of sampling the full task-complexity range. This is a
real risk for planner learning, even though repetition is correct for the
paired authority core.

- Orchestrator `scripts/autopilot/eval_task_coverage_report.py` now provides a
  read-only coverage report over all AutoPilot journal shards plus the active
  question pool. It reports distinct scored qids, repeat factor, pool coverage,
  suite/partition distribution, action/config/hypothesis diversity, tier-level
  coverage via `questions.tier_coverage` and `pool.tier_counts`, and Markdown
  Tier Coverage plus least-covered non-sentinel suites.
- Live all-shard observation on 2026-07-05:
  `24,210` scored question rows, `2,457` distinct scored qids,
  `52,210` stable pool qids, `4.706%` upper-bound pool coverage, and
  `9.8535x` repeat factor. Status: `low_coverage`.
- Tier coverage: T1 `1771/21133` (`8.3803%`, `255` eval-bearing trials), T2
  `843/26667` (`3.1612%`, `18` trials), T3 `160/5431` (`2.9461%`, `1`
  trial). Least-covered non-sentinel suites: `tool_use`, `agentic`,
  `skill_transfer`, `long_context`, `real_suite_v1`, `mode_advantage_hard`,
  `mode_advantage`, `coder`, `bigcodebench`, `cruxeval`.
- Policy: **do not rotate or replace the W6/W8 fixed authority core mid-run**.
  That would change the instrument during active evidence collection. Instead,
  split lanes: keep `authority_core` fixed for paired promotion evidence, add a
  separate `exploration_coverage` rotating/advisory lane for planner learning,
  and keep `promotion_holdout` as fresh held-out acceptance evidence.
- First-class T3 lane landed 2026-07-04: `EvalTower.eval_t3()` samples only
  workflow-shaped live-pool rows explicitly labeled `tier=3`, `deep_eval`
  accepts `tier: 3`, the shared tier registry exposes `T3 (expert/hard
  workflow eval lane; same-tier validation/planner pressure)`, and the
  dashboard Pareto reconstruction keeps tier 3 in its own
  `frontiers_by_tier["3"]` series. `DEFAULT_FRONTIER_TIER/T1` remains the
  production optimization lane. Non-inference sanity check found `5,431`
  T3-labeled rows, `4,956` scoreable rows across `13` suites, and a
  160-question spec draw containing only `tier=3` rows.
- Species budgeting now gives successful same-tier T2/T3 validation/workflow
  rows a small clipped credit via `species_effectiveness().budget_rate`, so
  `MetaOptimizer.rebalance()` can steer some exploration budget toward
  higher-tier performers without changing `DEFAULT_FRONTIER_TIER`, production-
  best selection, `SafetyGate`, or baseline promotion semantics.
- 2026-07-05 live planner-pressure follow-up: orchestrator `3af6e500` extends
  `_build_eval_coverage_pressure()` with cached per-tier pool denominators, so
  each controller turn sees T1/T2/T3 coverage against the active question pool.
  Latest strict-report snapshot: global coverage `4.7788%`, repeat factor
  `10.0621x`; T1 `1812/21133` (`8.5743%`), T2 `843/26667` (`3.1612%`), and
  T3 `160/5431` (`2.9461%`). This keeps T3 visible as an under-sampled
  expert/hard workflow validation lane without changing the T1 production
  optimization objective or any authority gate.
- 2026-07-05 maintenance status: AutoPilot is live as PID `1802932` via
  `start_fable_authority_daemon.py --max-trials 2000` after PID `1726689`
  and its orphan planner subprocess were stopped and verified gone at the trial
  `1156`/`1157` boundary. The API was reloaded as PID `1798373` with
  `AUTOPILOT_TOOL_SENTINELS=1`, Gate-3 hard tool telemetry is ready, and trial
  `1156` completed as T3 `deep_eval` (`q=1.29375`, speed `32.886`,
  reliability `0.75`, Pareto `dominated`) rather than W8 replay evidence.
  Current phase health reports trial `1157`, `phase=planner_invoke`,
  `code_stale=false`, and blockers `[]`. The strict Fable report is otherwise
  ready except W8, which remains blocked on candidate generation after
  orchestrator `a53a74ad` aligned report eligibility with the live replay
  selector: no replay-eligible accumulating W8 candidate exists. Orchestrator
  `026f8e29` and `0dd63df9` are live in the daemon planner-evidence path, so
  `structural_prune` is explicitly named as non-replayable W8 evidence;
  `24e440dd` is live and prioritizes replayable W8 candidate generation. Next
  action: `collect_w8_promotion_eval_evidence`.
- 2026-07-05 later authority-loop status: AutoPilot was restarted again as PID
  `2632468` from orchestrator `1d452a40` with `local_ingest` drafting, Codex
  critique, tool sentinels, W6 audit accrual, planner spend breaker, and
  StrategyStore search health `1,420/1,420`. Orchestrator `8031c7c4` adds true
  GEPA scratch prompt-root isolation and `12839520` adds observation-only W8
  paired-baseline diagnostics (`eval_details.seq_paired_baseline`, exact
  McNemar/sign-test, `used_for_gating=false`). Both commits are pushed and
  GitNexus-indexed, but the running AutoPilot daemon predates them; restart at
  the next clean trial boundary to load them. Trial `1177` replayed W8
  candidate `4b6b454ea4f884fd` at `q=2.127`, `s=14.5`, dominated and
  `seq_refuted`; trial `1178` is another forced replay.
- 2026-07-05 latest authority-loop status: after the A9 quiet-window collection
  and contention-freshness fix, AutoPilot was restarted as PID `2935890` from
  orchestrator `120498c9` with `AUTOPILOT_PLANNER_PRIMARY=local_chat`, Codex
  critique, planner hints, tool sentinels, W6 audit accrual, sequential verdict,
  and `--max-trials 2000`. Trial `1185` is current-code clean in
  `dispatch_action` / `seed_batch`; it is a forced baseline-reference draw, so
  it is not yet a `local_chat` planner telemetry proof. Outcome progress remains
  `attention` because the last frontier admission is trial `1005`.
- 2026-07-05 final local-planner/W8 status: the stale `local_chat`/`local_worker`
  restart target has been superseded. AutoPilot is live as PID `3267768` from
  orchestrator `a13a2948` with `--max-trials 3000`, local-ingest drafting,
  local-frontdoor critique, Claude critic fallback, planner hints, tool
  sentinels, sequential verdicts, and W6 audit accrual. The first post-fix
  planner turn proved the W8 recovery path: a no-op local draft was rejected,
  W8 fallback selected `numeric_trial` on `chat_pipeline`, and NumericSwarm
  materialized
  `chat.try_cheap_first_quality_threshold=0.8742715026951258`. The candidate
  completed at `q=1.964`, `s=28.5`, failed the safety gate on `tool_use`, and
  was reverted/blacklisted for that exact concrete param. Trial `1195` then
  invalid-skipped already-blacklisted `graph_router=true`; trial `1196` is the
  latest observed planner turn. This is wiring proof and negative candidate
  evidence, not completed W8 promotion progress.
- 2026-07-06 outcome-stall control update: orchestrator `9522b76e` prevents the
  higher-tier probe guard from overriding a planner-selected frontier-moving
  action while outcome progress is already frontier-stalled, and `78ae65e6`
  adds a bounded dispatch fallback so seed/eval/housekeeping work cannot satisfy
  a stale-frontier condition when a numeric trial fallback remains available.
  Frontier-moving actions still pass through unchanged. Validation passed over
  `140` focused AutoPilot action/phase/provider tests, ruff, `py_compile`, and
  `git diff --check`; both commits are pushed and GitNexus-indexed. Follow-up
  `e3b13edd` fixed the replay/AP-9 seam exposed by skipped trials `1213`-`1216`
  and restarted AutoPilot as live PID `3935151`. Trial `1217` is now evaluating
  the force-matched source-trial-`1197` `repl_executor` replay; AP-9 remains
  binding for new planner-proposed explicit multi-param numeric actions.
- 2026-07-06 planner-health replay-phase guard: orchestrator `bd2ecc7d` keeps
  the active-safe planner-provider report from paging operators during forced
  W8 replays or other non-planner phases. No current-process provider events
  now report `waiting_for_planner_turn`/`ok=true` when
  `/mnt/raid0/llm/tmp/autopilot_phase.json` says the daemon is outside
  `planner_invoke`; the same no-event window still reports `attention` during
  `planner_invoke`. This preserves the local-provider health watch for real
  planner stalls while letting due-check replays bypass planning without
  looking broken.
- 2026-07-06 local two-stage planner path: orchestrator `26c8ec2c` adds
  default-off provider aliases for an ingest-briefed local draft path. The
  `local_brief_frontdoor` / `local_ingest_frontdoor` / `local_two_stage` aliases
  synthesize a compact controller brief with `ingest_long_context`, then draft
  through `frontdoor`; `local_brief_worker` drafts through `worker_general`.
  Critiques pass through to the final role, and planner archive telemetry
  records brief-vs-draft stage success. This is the next safe canary lever for
  making AutoPilot fully local without changing the current
  `local_frontdoor`/`local_worker` default daemon.
- Regular Fable visibility landed in orchestrator `34591a27`: strict readiness
  now includes advisory `eval_task_coverage` status/percent/repeat/tier summary
  in `summary` and as a non-blocking section. Dashboard-specific presentation
  can build on that payload, but the authority gate remains unchanged.


## Research Intake Update — 2026-07-14

### New Related Research
- **[intake-819] "Sleep-time Compute: Beyond Inference Scaling at Test-time"** (arxiv:2504.13171 — Lin, Snell, Packer, Wooders, Stoica, Gonzalez; Letta/MemGPT lineage; credibility 2 [audit-corrected: Apr-2025 outside 12-mo window + Letta commercial-bias], verdict adopt_patterns)
  - Relevance: medium — a clean formalization of **exactly what autopilot/nightshift already do**: an offline phase `S(c)->c'` enriches raw context *before* queries arrive, so the online phase `T_b(q,c')` is cheap. Maps onto the knowledge-distiller, handoff-hint-distillation, and unified-trace-memory-service (the store an enriched `c'` would live in).
  - Reported results: **~5× less test-time compute** at matched accuracy (Stateful GSM-Symbolic, AIME); **~2.5× lower cost/query** when one enriched context is amortized across ~10 related queries; +13–18% accuracy at fixed test-time budget.
  - Delta from current approach: we run the offline loop but **without an explicit predictability gate or amortization accounting**. The paper supplies both, plus the failure modes we should encode.
  - **Attaches to existing anchors (not free-floating):** the deferred **AP-29 KnowledgeDistiller wiring** (`knowledge_distiller.py` L1→L2→L3; code landed 2026-05-08 `4cdc77e`, wiring still deferred) is the concrete precompute/distiller path this gate should ride on; the **2026-05-20 RIU "tool-response predictability co-objective"** note is the same idea one step less formal. Treat all three as one thread.

### Transferable patterns → autopilot
1. **Predictability gate** — only precompute where the future query/workload is inferable from current state (benefit collapses when queries are unpredictable; Fig. 10).
2. **Amortization accounting** — price offline artifacts across the number of future consumers, not per-run.
3. **Staleness invalidation** — precomputed `c'` is void when context changes; maps directly to our autopilot artifacts going stale on stack/config/kernel changes (FROZEN-registry + stale-process discipline).
4. **Not a strict dominator** — at very high online budgets, plain test-time scaling wins; sleep-time compute is a low/mid-budget lever.

### Rider on existing deferred work (not standalone)
- [ ] **When AP-29 KnowledgeDistiller is wired** (currently deferred — see AP-29), apply an explicit **predictability + staleness gate** to it: what to precompute, for how many consumers, invalidate on stack/config change (framing from intake-819 + the 2026-05-20 predictability-co-objective note; adopt_patterns only, no importable artifact). This is a rider on AP-29, **not** new standalone scaffolding.

## Seq-Gate Containment Checkpoint — 2026-07-15

Deterministic planner guard work was already recorded earlier. This checkpoint
captures the seq preflight containment result only.

- The orchestrator seed-fallback dead-loop is fixed, so the seq preflight
  fallback path no longer loops on the old failure mode.
- Live restart trial `1399` halted with `_dispatch_deficiency=seq_gate_preflight_blocked`
  and `last_invalid_reason=seq_gate_preflight_alpha_wealth_exhausted`.
- No `in_flight_trial` remained after the halt.
- Checkpoint validation passed with `160` tests passing.
- Remaining blocker is the formal OP-1 / P0.2 MEASUREMENT amendment work
  around alpha wealth and rate-axis reachability; the `seq_p0_2_bridge`
  consent path is now enabled and the bridge daemon has been resumed.

## OP-1 / P0.2 Bridge Completion — 2026-07-15

- [x] Bridge consent was granted in `orchestration/authority_consent.json`, then
  re-locked to `root:root` `0444` with `chattr +i` by the operator, and the
  live bridge status probe now reports `seq_p0_2_bridge_status().enabled=true`.
  ✅ 2026-07-15
- [x] `scripts/autopilot/start_fable_authority_daemon.py` resumed AutoPilot with
  supervisor PID `4071732` / child PID `4071734`, log
  `/mnt/raid0/llm/tmp/autopilot_fable_authority_20260715T215252Z.log`, and
  runtime facts `AUTOPILOT_SEQ_P0_2_BRIDGE=1`, `code_stale=false`,
  `seq_gate_reachability_preflight.status=passed`,
  `reachability.status=rate_axis_advisory_bridge`,
  `p0_2_bridge.enabled=true/env_enabled=true/consent_enabled=true`,
  planner primary=`claude`, critic=`codex_critic`, fallback=`claude`, and
  spend breaker=`0`. ✅ 2026-07-15
- [x] Trial `1399` dispatched as `numeric_trial memrl_retrieval.semantic_k=15`;
  the planner also attempted a stale invalid
  `repl_executor.tool_activation_threshold` draft, and the critic rejected it
  before substituting the valid memrl action. ✅ 2026-07-15


## Research-intake integration — 2026-07-22 (measurement-discipline hardening + orx/OpenHyra patterns)
_Via /research-intake Stage-2 (intake-883 orx, intake-884 HyRA, intake-885 OpenHyra)._
- [ ] Harden keep/revert into an explicit self-scoring candidate contract: always retain a proven baseline (valid rollback before any experiment); accept only on a re-verified strict improvement measured under pinned determinism (fixed threads/seed, N-run mean); atomic config swap; require an inline validity note stating what the number does/doesn't prove — including "no gating on a locally-unmeasurable proxy without held-out re-verify"
- [x] Adopt run-manifest provenance (sha256 of sources+task+evaluator + resume-drift rejection, per OpenHyra `provenance.py:72-157`) as the attestation format for experiment runs — codifies MEASUREMENT.md (protocol-id, attestation ref) in the loop ✅ 2026-07-29. `scripts/autopilot/run_manifest.py` creates a deterministic SHA-256 receipt over the AutoPilot/controller/evaluator sources, selected action, and evaluator identity. The receipt is persisted only in the in-flight WAL marker before dispatch; startup pauses and refuses crash recovery if its digest, sources, or evaluator drift. Legacy markers recover unchanged and historical journal rows/measurement records are not rewritten. Focused recovery + manifest validation: 46 passed; Ruff and `git diff --check` clean.
- [x] Evaluate OpenHyra's evidence-gated stop controller (LLM may only REQUEST stop; deterministic guards on evaluator records dispose; `stopping.py:238-263`) vs current keep/revert + convergence stop ✅ 2026-07-29. **Adopt the control-plane pattern, not an LLM stop switch.** OpenHyra accepts a stop request only after deterministic checks over complete evaluator records (minimum completed contexts, no meaningful gain for a patience window, and sufficient recent successful candidates), then writes a decision plus evidence to a terminal receipt ([source](https://github.com/MrSteeeve/OpenHyra/blob/main/stopping.py)). Its `expected_gain` and `confidence` are explicitly telemetry, never stop inputs. Our loop already has useful lower-level protections: terminal keep/revert rows are not replayed by W8, and `reproduction_confirmed` is excluded from Pareto learning while retained as valid convergence evidence (`scripts/autopilot/autopilot.py`). But Seeder's TD-error convergence is status telemetry, not a durable run-level disposition, and there is no single receipt binding a stop decision to complete evaluator records and run provenance. **Required eventual shape:** after the run-manifest row above lands, add a pure deterministic reviewer that consumes only complete journal groups and emits `{accepted, reasons, evidence}`; an LLM may request `stop` but cannot cause it. Refuse termination on incomplete/mixed-provenance groups; keep eligible independent work runnable rather than turning one candidate's convergence into a global kill. Cover accepted, refused, malformed-agent-request, incomplete-group, and resume-after-terminal cases with unit tests before wiring it into AutoPilot.
- [x] Mine orx's experiment-tree lineage model ✅ 2026-07-29: the current [`orx source`](https://github.com/alphaXiv/openresearch-cli/blob/main/src/local/experiments.rs) verifies the durable subset: every experiment receives an `orx/<slug>` branch, a child forks from its parent's branch and persists `parent_experiment_id`, while the project base branch is never an experiment node. The cited old line range drifted; current source contains no winner-promotion implementation, so do not attribute that policy to orx. EPYC already persists `parent_trial`, traces lineage in `pareto_archive`, and writes append-only `baseline_promotion` events; its parent choice is merely the preceding same-species trial, not a verified winner. **Disposition:** retain the existing journal lineage rather than introduce per-candidate git branches/worktrees; when AP-1510 run-manifest provenance is implemented, make parent selection explicit and allow an accepted parent only after the existing evidence/quality gate. That is a future schema/control-plane change, not a runtime action now.
- [x] Mine orx's "stacked bushes" tree-shape + per-completion refill loop ✅ 2026-07-29: the upstream [`orx experiment-tree skill`](https://github.com/alphaXiv/openresearch-cli/blob/main/agent-skills/orx-experiment-tree/SKILL.md) establishes a small sibling fan for one decision, then descends only from a confirmed winner. Its first-completion wait is a wakeup, not truth: reconcile every newly terminal run against an idempotent handled set, read evidence, then repair/refill/promote/stop. **EPYC disposition:** adopt that event/reconciliation shape only after AP-1510 supplies manifest-bound receipts: one planned sibling group per independent decision; terminal rows are handled exactly once; promotion remains the existing append-only, quality-gated baseline event; and a refill is admissible only through the lane arbiter with a pre-authorized capacity budget. Do **not** translate "keep capacity saturated" into autonomous CPU/NUMA saturation: an exclusive campaign (including E5 Stage-B) blocks all refills, and its release/approved budget is an external prerequisite. This is a future control-plane design, not a current runtime action.


## 2026-07-25 — intake Stage-2a dive: GEPA is a guaranteed no-op (P0), plus three overturned premises

_Via `/research-intake` Stage-2; coordination point [`intake-derived-work-2026-07-25.md`](intake-derived-work-2026-07-25.md) ID-1..ID-5b._

- [x] **AP-19a — GEPA reflective mutation has never run.** ✅ 2026-07-25 — FIXED + mechanism-validated (see completion note below the fix list) `scripts/autopilot/species/gepa_optimizer.py:192-194` defines `propose_new_texts()` that unconditionally raises `NotImplementedError("Use GEPA's built-in proposer")`, and GEPA dispatches on **presence, not None-ness** (`gepa/proposer/reflective_mutation/reflective_mutation.py:66-67`) — a bound method is never `None`, so every reflection step raises **before any LM call**. Evidence: `logs/autopilot.resume700b.log:1210-1219` (trial 521, 2026-06-04) traceback, then `GEPA optimization complete: 0.718 → 0.000 (-0.718) in 633s (50 evals)`; repeats at `:2384-2393`. **633 s and 50 evals burned per invocation for a guaranteed no-op.** Fix in order: (1) remove the `NotImplementedError` override; (2) *then* wire `reflection_lm_url` → `api_base` and plumb it from `prompt_forge.py:517-519` (which currently constructs with default args); (3) surface the failure instead of returning a no-op after 633 s; (4) note the validation target is frozen — `gepa_optimize` on `frontdoor.md` is blacklisted since 2026-06-05 at `corruption` severity (`failure_blacklist.yaml:40-47`).
  - NOTE: an `api_base` fix **alone changes nothing** — litellm is never reached and no network call occurs. An earlier report of this defect had the mechanism wrong.
- [x] **AP-19a completion note** ✅ 2026-07-25: all four fix items landed in `species/gepa_optimizer.py` — (1) `propose_new_texts = None` (class attr matching the GEPAAdapter protocol default; a raising method dispatched via `is not None` and fired before any LM call); (2) reflection LM passed as a CALLABLE carrying `api_base` (GEPA's str path calls litellm WITHOUT api_base, so a bare model id could never reach a local server) + env-overridable endpoint (`ORCHESTRATOR_GEPA_REFLECTION_LM`/`_URL`); (3) full-budget seed-unchanged runs now log at ERROR and return None instead of a fake completion; (4) the `gepa_optimize`/`frontdoor.md` blacklist entry LIFTED 2026-07-25 (removal condition met: autopilot restarted 10:17 after extractor fix `2cb40960`; verified via `load_blacklist()` → 0 entries; companion `prompt_mutation` freeze left in place; backup at `epyc-root/artifacts/intake-scratch/blacklist.bak`). Validation: dispatch + api_base proven via litellm intercept; `tests/test_gepa_integration.py` 11/11. NOT yet exercised against a live model (stack down).
- [ ] **AP-19b — supervised first live `gepa_optimize` run (operator-watched), at next stack bring-up.** Operator decision 2026-07-25: blacklist stays lifted; the FIRST live exercise of the repaired path happens in a watched window before any unattended dispatch is relied on. One-shot run; watch the new ERROR path and the journal row. Risk posture verified: adapter evaluates in a SCRATCH prompt root (live frontdoor.md untouched during eval, `gepa_optimizer.py:92-113`), `_prompt_integrity_reason` guards at mutation creation AND apply, applies are git-snapshotted + auto-committed. Cold bring-up recipe: [`esc8-stack-restart-landmine-audit-2026-07-22.md`](esc8-stack-restart-landmine-audit-2026-07-22.md) § 2026-07-25.
- [x] **AP-42 — decide the `gepa` pin.** ✅ 2026-07-29 — retain the already locked and integration-tested **0.0.26** for the operator-watched AP-19b first live exercise; `tests/test_gepa_integration.py` passes **11/11** against that environment. PyPI's current **0.1.4** is a separately scoped upgrade candidate, not a reason to install from `main`: its advertised `optimize_anything` surface is neither required for the repaired adapter nor compatibility-validated here. Any 0.1.4 bump must first pin its wheel/hash, run the mocked integration suite plus an API-compatibility review, then occur before—not during—the watched live exercise. No package was installed or changed by this decision.
- [ ] **AP-21 re-open, on corrected facts.** Journals (all shards) show **only 8 `gepa_optimize` trials ever** (181, 182, 521, 536, 785, 882, 1137, 1144), exactly **one** ever `keep`. `gepa_ratio` is **absent from live `orchestration/autopilot_state.json`** — the 0.30 is a hardcoded fallback at `autopilot.py:8798` on the *autonomous-fallback* path, not stored state and not the primary dispatch. External evidence stands: arXiv 2607.14004 (Terminal-Bench 2.0, matched budgets) reports the GEPA-optimized agent transferring **below** the unoptimized baseline; 2602.01011 reports GEPA returning the seed prompt unchanged; 2606.19605 reproduces GEPA at −3.78 to +7.97 pp. **Gate on AP-19a.**
- [ ] **AP-29 gate before wiring — narrowed.** `KnowledgeDistiller` has **zero non-test callers** (uninstantiated, not flag-off), so this is a free design change now. **The genuine ask is an episodic-only control arm** (retain + delete, abstraction disabled) that the distiller must beat. Justification: arXiv 2605.12978 feeds **ground-truth solutions** through a streaming consolidator and drops a 19-problem ARC-AGI slice from **100% → 52.6%** at R10 — the fault is provably in the rewriting step. Carry the authors' caveat (*"two repeats per question"*, *"point estimates … rather than formal error bars"*).
  - **PINNED 2026-08-12** — the gate premise is now a TRIPWIRE, not prose: orchestrator
    `015eb8e4`, `tests/unit/test_knowledge_distiller_tripwire.py`. It PASSES while
    `KnowledgeDistiller` has zero non-test callers and FAILS the moment anyone constructs one,
    so whoever wires AP-29 is forced to finish the chain rather than land a caller that quietly
    does nothing. AST-anchored on real `ast.Call` nodes, so a docstring mention cannot trip it.
    **Name trap recorded because it would have closed this row against the wrong class:**
    `scripts/autopilot/actions.py` wires an action called `distill_knowledge`, but it calls
    `EvolutionManager.distill` — a separate class that never touches `knowledge_distiller.py`.
    The module's own docstring claims it is "triggered every N=25 trials by the autopilot main
    loop"; that sentence describes `EvolutionManager`, not itself.
    *(Premise re-derived and mutation-checked independently by `mainC` before acceptance: zero
    real constructions by AST walk, and a construction added to a DIFFERENT tracked file than
    the author used fails the test.)*
  - **Already satisfied — do not file as asks**: raw-trajectory deletion (landed code does **reversible quarantine via validity decay**, `knowledge_distiller.py:316-319`) and unconditional consolidation (predicate is already MDL-gated, `:37-41`, `min_validity=0.10`). **Only the cadence trigger is unconditional.**
  - Prefer **grouped/batched** consolidation over per-checkpoint streaming; independently corroborated by intake-627 (parallel batch beats sequential online editing by +4.0/+6.8 pp).
- [x] **AP-32 — the previous framing was arguing with dead code. ✅ 2026-07-29** `audit_insight_specificity()` is now explicitly diagnostic-only and has a regression test proving that auditing cannot mutate stored strategy data; any future write-path use must require retained applicability evidence explicitly. The unmeasured "+1.1% task-agnostic insights" justification is removed from both agent-architecture source surfaces: it was an external paper observation (intake-425, arXiv 2604.14004), not EPYC evidence.
- [x] **The utility-weighted-retrieval concern targets the MemRL code path, not SkillBank ✅ 2026-07-29.** `retriever.py` combines `q_weight * q_value + (1-q_weight) * similarity`, while SkillBank retrieves general items by confidence and task-specific items by FAISS similarity with no `q_value`. SkillBank is default-off in `src/features.py`; the current default `sessions/skills.db` is empty, so the old 57-row snapshot is historical rather than a current basis for a migration claim. Point the memory-degradation evidence at the MemRL episodic retriever **when its runtime use is separately established**; this documentation audit makes no live-region claim during E5.

## 2026-07-29 — intake Stage-4: AP-29 write-gate budget, replayable objective comparison, and the prompt-optimizer of record

_Via `/research-intake` Stage-4 (intake-930 ReasoningBank v2, intake-888 CORE, intake-935 SkillOS, plus the GEPA/DSPy cross-model transfer line). External figures are OBSERVATION-grade under MEASUREMENT.md and gate nothing on their own._

- [x] **AP-29a — Budget the AP-29 write gate DOWN, not up. ✅ 2026-07-29** ReasoningBank v2 measures its own judge at **72.7% accuracy** and simulates upward from there: ground-truth labels buy only **+4.8pp of a 13.4pp effect**, and judge accuracy in the **70-90%** band is a **plateau**. Therefore the future distiller write gate must use the **cheapest adequate LOCAL judge**, not an eval-tower call or frontier model. intake-935 (SkillOS) reinforces this — its advantage comes from an auditable three-verb write API, not an expensive admission judge. **Contrast CORE (intake-888), where admission is load-bearing** — the two gates differ, so this budget decision does not generalize. This is a design constraint only: the existing AP-29 gate-before-wiring and episodic-only control arm remain binding preconditions; no runtime route changed.
- [ ] **AP-29b — Compare correctness-first LEXICOGRAPHIC selection against the scalarized cost-aware reward in chapter 08 by DETERMINISTIC REPLAY over already-persisted autopilot trials.** No new inference: rescore saved outcomes and rebaseline only the objective axis that changed — exactly what `agents/shared/MEASUREMENT_POLICY.md` → *Deterministic replay before regeneration* prescribes. Journal shards (`autopilot_journal.jsonl` + `autopilot_journal_1.jsonl`) already carry the per-trial outcomes this needs.
- [x] **AP-29b preflight — journal-only replay data-contract audit. ✅ 2026-07-29** The two shards contain 1,338 trial rows with aggregate quality/speed/cost/reliability, but not the per-answer role, actual elapsed, expected elapsed, or quality-base fields required by Chapter 08's `quality_base - lambda * max(0, cost_ratio - 1.0)`. The stored `cost` is instead the EvalTower's average normalized **cost tier** (source: `scripts/autopilot/eval_tower.py:3474-3476`), so it cannot be substituted for `cost_ratio`. Keep AP-29b open; first link an immutable per-question outcome ledger to each trial and record the contemporary role-TPS baseline/config hash. This audit makes no baseline, Pareto, or deployment decision.
- [ ] **AP-29c — Name the prompt-optimizer of record as GEPA-class, and adopt compile-on-small-model / deploy-to-large as the CPU-first strategy.** GEPA's cross-model transfer: prompts optimized on **Qwen3-8B** scored **+9.00 aggregate on GPT-4.1-Mini**, beating every optimizer tuned directly on it — which is what makes compiling on a cheap local model economically viable here. Mark **BootstrapFewShot\*** superseded for 2026-era instruct models (**MIPROv2** buys only **+2.6** on Qwen3-8B and **REGRESSES** on AIME/LiveBench). Cost line for any compile is tracked in [`harness-selection-and-integration.md`](harness-selection-and-integration.md) HS-11 (5k-25k LM calls ⇒ region-locked campaign). Sequencing: this is downstream of **AP-19a/AP-19b** — do not re-argue the GEPA pin (AP-42) before the repaired path has run live once.


### AutoPilot end-to-end smoke test — 2026-08-03

First full smoke run of the trial loop. Four defects, three silent.

- [x] **Real-mode inference 503'd for EVERY role** ✅ 2026-08-03 (orchestrator `bc1da61f`). The
      Pydantic->dataclass bridge used `getattr(settings.server_urls, name, f.default)` and
      `f.default` is `dataclasses.MISSING` for any `default_factory` field — all of them. A field
      on the dataclass but not the settings model was passed MISSING explicitly, defeating its own
      factory. `architect_critic` (added W1, 2026-08-01) was that field, and since backend init
      `.split(",")`s every URL, init raised for every role. AutoPilot INFRA_SKIP'd all 17 seeding
      calls against a healthy stack. The 9 long-standing ServerURLsConfig test failures were this
      bug's alarm, dismissed as "pre-existing" three times.
- [x] **`--max-trials N` was a no-op** ✅ 2026-08-03 — compared the CUMULATIVE counter, so
      `--max-trials 1` at counter 1459 exited having run nothing. Now a relative budget.
- [x] **AutoPilot was left `paused: True`** ✅ 2026-08-03 — a fresh daemon start passed every gate
      then spun in a pause-wait loop at 1 log line/second. Resumed.
- [x] **Bounded trial completed clean** ✅ 2026-08-03 — `ran 1 of 1 (trial 1460 -> 1461)`,
      structural_lab, tier 1, quality 1.8293, T1 65/65, **0 INFRA_SKIPs** (was 17).
- [x] **Regions-lock grid no longer labels occupied cross-role shapes free** ✅ 2026-08-06 —
      backend display cells now render `×` for every physical overlap with an active placement
      lease, independently of contention-matrix admission. Regression coverage pins the reported
      two-half case: `worker_general.half0` + `.half1` occupy q0–q3, making every Full/Half shape
      for `architect_critic`, `frontdoor`, and `ingest_long_context` locked while the two worker
      halves remain active. A second exact regression pins `frontdoor.full`: it renders `⚡ 1/4`
      (configured serving slots, not its exclusive lease width), locks both frontdoor halves,
      `architect_critic.Full`, and every Full/Half shape for ingest and worker. The apparent live
      failure after the first source fix was an escaped pytest API process, not the repaired matrix:
      PID 3903691 was launched by a unit test on 2026-08-05 with stale Python and a pytest lock
      directory. The launcher/test escape is now structurally guarded (INC-20260806-pytest-api-escape).
      Validation: 137 focused repair tests + 193 broader dashboard consumers passed; repository
      gates passed.
- [ ] **Reload the escaped live API at the inference owner's next safe boundary.** Named external
      event: the session owning live inference must run the API-only
      `orchestrator_stack.py reload orchestrator` after its in-flight requests drain. Current PID
      3903691 is healthy but stale and carries `PYTEST_CURRENT_TEST` plus pytest `TMPDIR` /
      `ORCHESTRATOR_TMP_DIR`; this session did not kill or reload it across another session's live
      requests (reload-ownership rule, INC-20260728-reload-preemption).
- [x] **CORRECTION: SEQ-3b is NOT the mechanism that clears the E8 hold** ✅ 2026-08-03 — this entry
      previously called SEQ-3b "the ONLY correct path" to lift the re-baseline hold. That conflated two
      different things. SEQ-3b is a **sequential-allocation candidate re-run** (`70902e4b665474e7`,
      ~49 trials) which is itself *gated by* the hold — see
      [`autopilot-sequential-allocation.md`](autopilot-sequential-allocation.md), which states this
      correctly ("Also gated on the E8 quality-baseline reseed completing and being operator-ratified").
      The hold is cleared by a different instrument entirely:
      `scripts/benchmark/run_e8_quality_baseline_reseed.py --prepare|--execute` followed by the
      human apply transaction `artifacts/operator/apply_e8_quality_baseline_state.py`, which is the
      only writer of `e8_quality_rebaseline.status`.
- [ ] **E8 quality-baseline reseed — blocked on an operator source amendment pending since 2026-07-27.**
      The reseed preflight (`--prepare --t2-n 500`) returns `decision_grade: false` with five blockers,
      three of which are stack-shape (`24 unique selected ports`, `exactly five live frontdoors`,
      `both-mode endpoints healthy 6/6`) and two of which are the same missing operator receipt
      (`ratify_e8_quality_baseline_protocol_context_repair_20260727.json`). That receipt cannot be minted
      until the source vector is amended, because **51 fixed-vector rows do not fit the 32,768-token
      frontdoor** (3 in T1, 48 in T2; `required_tokens` ranges 33,052 → 4,328,998) and two more rows
      (`real_suite_v1_0043`, `needle_039`) declare a zero-capture-group `exact_match` pattern `\d+`.
      `artifacts/operator/e8_context_feasibility_amendment_decision_20260727.md` lays out Options A–D,
      recommends A (capacity-qualified replacement map), and defaults to **D — defer**. Nobody chose, so
      it defaulted, and five `--execute` attempts across 2026-07-26→29 all left `.staging-` bundles the
      runner forbids reusing. **This is the true critical path to quality promotion.**
- [ ] **Operational alternative to the ratification-grade reseed — needs an operator go/no-go.**
      `autopilot.py calibrate-baseline --tier 1` produces fresh same-era T1 quality, per-suite scores and
      per-suite counts in ~100 questions. It is *not* sufficient on its own: `_apply_calibrated_baseline_result`
      (`autopilot.py:9546`) writes `baselines_by_tier` / `per_suite_quality_by_tier` /
      `per_suite_counts_by_tier` but **never touches `eval_quality_era`**, so the hold survives. The gap is
      a circular dependency — `update_baseline()` refuses quality promotion while the baseline era differs
      from the active era, and the era only updates inside a successful promotion. Breaking it requires
      writing a fresh baseline already stamped `E8`, which is the human-amendment boundary
      (`required_next_action: "human-only E8 baseline value reseed"`). Trade-off: an operational baseline
      for config search, not a ratified publication-grade number.
- [ ] **Run the canonical 79-question judge suite on Qwen3.6-27B-MTP-Q8_0.** Inherited from the three
      `accepted_gaps.yaml` waivers removed 2026-08-03: the gap they waived (missing overall quality prior)
      is closed because quality now compiles per-axis with recorded basis, but their stated closing action
      was never done. The 27B's prior currently resolves 0.8597 via public `mmlu_pro`, not the canonical
      instrument.
- [ ] **Decide the lineup status of `worker_fast` (8102), `eval_batch_frontdoor` (18070) and the
      embedder `extra_recipes` (8096-8098).** They are declared in the launch manifest and so are
      painted as expected services, but none are running. Hidden from the regions-lock panel as a
      display fix; whether they should remain declared is a stack-config decision.

## AutoPilot launch unblocked ✅ 2026-08-03

- [x] **`preflight_audit.py` 9/11 -> 11/11 — safe to launch** ✅ 2026-08-03 (commit `8b79026e`).
- [x] **Stack-change promotion gate: 52 errors -> 0** ✅ 2026-08-03 — derived stack priors had drifted
      from the launch manifest (`frontdoor` declared `[8070]` vs manifest `[8080, 8180]`, same for six
      other roles) and three `source_artifacts` hashes were pinned against commits that had since
      landed (`04af7b95`, `cba55d49`, `93569b69`). Fixed via `stack_change_pipeline.py update`.
- [x] **Three stale `accepted_gaps.yaml` waivers removed** ✅ 2026-08-03 — the gap they waived no
      longer fires; the file's own rule makes a declaration matching no current gap an ERROR.
- [x] **Two poisoned-source blacklist entries removed** ✅ 2026-08-03 —
      `chat.try_cheap_first_quality_threshold` (trial 1194, `fe64fc37`) and
      `chat.review_low_q_threshold` (trial 1448, `external-gpu-loads-20260726`) were banned on
      evidence the system itself later invalidated. 72 entries remain. Did NOT run
      `blacklist_purge_plan.py` — its broader era-fenced purge is a separate operator decision.
- [x] **AutoPilot launched under the Fable authority supervisor** ✅ 2026-08-03 — budget 1461 -> 4461;
      trial 1462 dispatched `structural_experiment {architect_delegation: true}`, planner critique
      `approve confidence=0.98`.
- [x] **REL-1: a 0.0 t/s sample on a reliability-blocked trial is ABSENT, not slow** ✅ 2026-08-03
      (commit `7fd2dde5`) — trial 1459 carried a fabricated `Throughput floor: 0.0 t/s < 10.2 t/s`
      into `failure_analysis`, which is planner-visible evidence, from a run that generated nothing.
- [x] **`worker_summarize.candidate_roles` derived-vs-restated defect fixed at source** ✅ 2026-08-03 —
      led with `coder`, so the per-axis resolver scored a summarization alias on `livecodebench_v6`
      (0.804). The 2026-08-02 fix had been written into the GENERATED lean registry and was reverted
      by the next compile, one day later. Now resolves reasoning/`mmlu_pro` 0.852.

## Backlog sweep 2026-08-03 — 21 agents, adversarially verified (8 PARTIAL, 1 CONFIRMED)

A parallel sweep fixed part of the audited backlog. Independent verifiers then tried to refute each
claim, and several claims did not survive. **The defect class the sweep was sent to fix reproduced
itself inside the sweep.** Everything below is verified-open, not speculative.

### Reported fixed, but the fix cannot run

- [ ] **Speed-era stamp is unreachable — the throughput floor is now permanently demoted.**
      `update_baseline()` returns early on `quality_rebaseline_required` (`safety_gate.py:2144-2156`);
      the new speed-era stamp sits at `:2324-2328`, ~170 lines later. In production's current state
      the early return always fires, so the stamp never executes and the hold can never close in
      code. Net live effect: a cross-era throughput violation is demoted to a warning **indefinitely
      with no in-code path to re-arm it**. The claim "a reseed closes the hold naturally" is false as
      delivered. No test constructs a gate with BOTH eras active and calls `update_baseline`.
- [ ] **`assigned_role` still 0 / 59,337 — production takes the branch that drops it.**
      `orchestrator_stack.py:2117` sets `ORCHESTRATOR_Q_TD_WRITE=1`, so production runs the
      find-or-update branch at `q_scorer.py:1388-1406`, which calls `update_q_value` and returns
      before ever reaching `store()`. That branch fires ~11x more often than create
      (`SUM(update_count)=668,070` vs 59,337 rows). The new tests only cover the legacy create path,
      because `Q_TD_WRITE` is read at import time and is 0 under pytest.
- [ ] **`work` payload: 0 rows carry a top-level `work` key.** Same update-branch hole, plus two
      more: the sanitize policy runs twice (pipeline + `build_memory_record`) and is **not**
      idempotent despite its docstring, so the row's size/elision provenance actively lies; and
      `chat_pipeline/stages.py:288` feeds the **process-global, never-cleared**
      `tool_registry.get_invocation_log()` into the durable record, so one request persists another
      request's tool calls. `clear_invocation_log` has zero callers in `src/`.
- [x] **Vision task-detail renderer now displays captured path-backed inputs.** ✅ 2026-08-05 —
      task detail extracts the image reference already captured on `routing_decision`, serves
      allowlisted raster files through a task-scoped no-store/nosniff endpoint, and renders a
      bounded preview plus full-resolution link. The reported `chat-bc6df1a2` was verified live.
- [ ] **`request.files` vision input still has no telemetry image reference.**
      `vision_stage.py:76` treats `request.files` as vision input, but routing telemetry records
      neither a retained path nor displayable bytes for that form.
- [ ] **Evidence-durability symlink guard covers the form that barely occurs.**
      `check_evidence_durability.py:306` — `inside_repo = (not absolute) or ...` is unconditionally
      True for relative paths, so `_is_scratch()` is never consulted for them. **416 of 421** registry
      citations are relative, and the remediation playbook tells remediators to use relative paths.
      Also: the new pre-commit wiring exists only as `.git/hooks/pre-commit.extras` on this host —
      unversioned, so no clone gets it.

### New instances of the same class, found by the critic, previously unowned

- [ ] **`memories.sub_decision` is 0 / 59,337 with no producer anywhere.** Column + index
      (`episodic_store.py:330,335`), dataclass field (`:173`), `store()` parameter (`:379`), INSERT
      binding (`:527,557`), and a passing `test_episodic_store_sub_decision.py`. `grep "sub_decision="`
      across `src/ scripts/ orchestration/` excluding the store and backfill script -> **zero hits**.
      `scripts/memory/backfill_sub_decision.py` exists and has never been run. Exact twin of
      `model_id` and `assigned_role`. Three agents ran its test and none noticed the column is empty.
      - **RE-DERIVED 2026-08-12 (`mainC`) — the finding HOLDS and is worse than filed, but it is
        NOT closed.** Producers outside the store and the never-run backfill: still ZERO. A
        read-only count over the checkpoint store gives **0 non-null of 642,328 rows**, an order of
        magnitude more data than the 59,337 recorded here and still entirely empty.
      - **Why nobody noticed, which is the reusable part.** `test_episodic_store_sub_decision.py`
        is 312 lines and green: it covers the enum, the normaliser, the column-and-index migration,
        the classifier token map and the backfill script — **everything except whether anything
        writes the column on the live path.** A test can cover all the machinery and never touch
        the question of whether the machinery is REACHED.
      - **Instrumented, not fixed** (orchestrator `6aa083be`): added
        `tests/unit/test_sub_decision_producer_tripwire.py`, which passes while the gap exists and
        FAILS the moment a producer appears — forcing whoever wires it to confirm the column
        actually POPULATES (a call site is not population), settle the backfill question and close
        this row. A second test guards the other direction, since silently DELETING the column
        would also leave this row describing something that no longer exists. Deliberately not
        `xfail`/`skip`: both are invisible in a green run, and invisibility is the defect.
      - **Box left unchecked deliberately** — the column is still inert. This makes the gap
        self-announcing; it does not resolve it. The fix is still a decision: wire a producer, or
        retire the column and its machinery on purpose.
- [ ] **`binding_router` is a parameter nobody passes, gating a whole feature.** `src/api/state.py:97`
      declares `binding_router: Any | None = None`, never assigned anywhere;
      `chat_routing.py:230`'s `if binding_router is not None:` guards the entire override block;
      `_classify_and_route_proactive` has zero callers. Flipping `features().binding_routing` does
      nothing because the `BindingRouter` is never constructed.
      - **RE-DERIVED 2026-08-12 (`mainC`) — HOLDS, and this row UNDERSTATES it.** The feature is
        dead at **three independent layers**, any one of which alone would be enough:
        (1) `BindingRouter()` appears exactly once in the tree, at `src/routing_bindings.py:19`,
        and that line is **inside a docstring Usage example** — never constructed in code;
        (2) `state.binding_router` is declared and never assigned;
        (3) the guard's **one production caller**, `src/api/routes/chat_routing.py:325`, calls
        `_classify_and_route(prompt, context, has_image=has_image)` and **omits the argument** —
        every other caller in the tree is a test. The flag is a fourth layer of inertness.
      - **Two of this row's three anchors had rotted**, which is why re-deriving mattered:
        `chat_routing.py` now lives under `src/api/routes/`, and `_classify_and_route_proactive` —
        the function this row names — **no longer exists at all**. The finding underneath survived
        the rot; the addresses did not.
      - **Instrumented, not fixed** (orchestrator `tests/unit/test_binding_router_tripwire.py`):
        one test per dead layer, each failing the moment that layer is wired, so whoever wires one
        is forced to wire the REST of the chain instead of landing a layer that silently does
        nothing — which is how this reached three dead layers. Layer 3 is pinned by the CALL SHAPE,
        not a line number, precisely because this row's own anchors rotted.
      - **Box left unchecked deliberately** — nothing is fixed. The decision is still open: wire the
        whole chain, or retire `binding_routing` and its machinery on purpose.
- [ ] **Ten fully-built, fully-tested, zero-production-importer modules** (1-3 test importers, 0
      production importers), incl. `src/mutation_ledger.py`, whose docstring asserts "the autopilot
      accept-path consults the ledger" — it does not.
      - **RE-DERIVED 2026-08-12 (`mainC`) — the COUNT is wrong and the row cannot be acted on as
        written, because it asserts "ten" without naming them.** Over **368 modules under
        `src/`**, the true figure is **at least 20**, not ten.
      - **The exact number is METHOD-DEPENDENT, and I am reporting that rather than a single
        figure.** Two independent passes disagree: a stem-match scan gives **24**, a
        dotted-import scan gives **22**, and they **agree on 20**. Four modules appear only in
        the stem scan (likely over-match on common words — `model_grader`, `federation`,
        `verbalized_sampling`, `tool_output_compressor_mcp`) and two only in the dotted scan
        (`radix_cache`, `safe_pickle`, which the stem scan missed via relative/dotted import
        forms). **20 is the defensible floor; 26 is the union.** A single number here would
        have been false precision — I ran the second pass as a cross-check on my own method
        and it disagreed with the first, which is the only reason this caveat exists.
      - **But the raw 24 is not the answer either: some are ENTRY POINTS, where zero importers is
        correct.** `src/cli_orch.py` is a declared console script (`orch = "src.cli_orch:main"` in
        `pyproject.toml`), and `src/mcp_server.py` is launched as a server rather than imported.
        Anyone acting on a bare importer count would have "cleaned up" a shipped CLI. The real
        list is 24 minus the declared entry points, and it needs a per-module read before anything
        is deleted.
      - **The named instance is CONFIRMED and is the worst of the cluster.**
        `src/mutation_ledger.py`'s docstring states verbatim that *"the autopilot accept-path
        constructs MutationRecords and consults the ledger before composing a new mutation onto the
        live config"*. `git grep` for `mutation_ledger|MutationLedger` across `src/` and `scripts/`,
        excluding the module itself, returns **nothing**. So BSV-3 conflict-aware acceptance is not
        in effect anywhere — and unlike ordinary dead code, this module **describes itself as
        live**, so a reader grepping for how conflict-aware acceptance works concludes it is wired.
      - **Instrumented, not fixed** (orchestrator `tests/unit/test_mutation_ledger_tripwire.py`):
        fails the moment the claim is softened OR the integration is built, so the docstring and
        the code can never silently drift apart again. Mutation-checked against a tracked file.
      - **Box left unchecked deliberately** — nothing is fixed, and the decision is per-module:
        wire BSV-3, or retire the ledger and correct its docstring. Same for the other 23.
- [x] **`contention_nway_restricted_count` stops one layer short of the operator.** Reaches
      `metrics_snapshot()` (`contention_gate.py:453`) but appears 0 times in `dashboard.html`.

### Never attempted

      ✅ 2026-08-12 — orchestrator `86144f93`. It stopped at the RENDER layer: the value already
      reached `metrics_snapshot()` and the `/dashboard/api/contention` JSON, but
      `updateContentionGate()` in `dashboard.html` read its four siblings and never this key
      (`grep -c` was 0 before, 1 after — *`mainC` verified both sides*). Surfaced on the EXISTING
      contention-gate compact strip, no new panel, and it carries the denominator per
      `OPERATING_CONSTRAINTS.md § Reporting Units`: *"{n} of {admitted} admitted decision(s) this
      window"*. Tests execute the REAL extracted JS under node against a stubbed `fetchJSON` and
      assert on rendered `innerHTML` — 3 tests; mutation 2 failed / 1 passed, restored 3 passed.
- [ ] **The metric's NAME and its new tooltip both overstate what it counts.** `contention_gate.py:325`
  increments inside `if nway_decision != PairDecision.ALLOW:` — **not** inside the
  `if _prec[nway_decision] > _prec[worst]:` test one line above. So it counts *"the N-way check fired
  non-ALLOW"*, not *"N-way was the binding constraint"*: if pairwise already said BLOCK and N-way says
  QUEUE, it still increments although N-way changed nothing. The dataclass comment at `:92` ("N-way set
  more restrictive than pairwise") is therefore inaccurate, and the new tooltip inherits it —
  *"restricted … beyond what the pairwise check alone allowed"* is now **operator-facing**.
  The subagent spotted the looseness in its own report and wrote the loose form into the UI anyway,
  which is the `§ Reporting Units` failure one level in: a LABEL asserting more than the number
  measures. *(Verified by `mainC` by reading the enclosing block, not the comment.)*
  Fix is either wording (*"N-way check returned non-ALLOW"*) or moving the increment under the
  precedence test — a semantics decision for the contention-gate owner, not a wording tidy.

- [x] `config/stack_templates/default.yaml` is 10 validation errors stale — `start --stack-profile
      default` returns 1 today.
      **2026-08-12 (`mainA`) — NOT CLOSEABLE AS WRITTEN, and checking why produced a HIGH-severity
      defect filed separately.** Two problems with the row as a recipe. (a) The path is wrong:
      there is no `config/stack_templates/`; the file is `stack_templates/default.yaml`.
      (b) **The validation route it prescribes does not exist.** `orchestrator_stack.py:2795`
      declares `--validate-only` with the help text *"Validate stack template and exit"*, and
      **nothing reads it** — `grep` for the argparse dest across the file returns only the
      declaration, and `main()` dispatches `start` → `cmd_start(args)` with no branch. So the
      documented dry run **launches the production stack**. I was about to run it and stopped
      only because compute is saturated and I check anything named `start` before invoking it.
      **✅ 2026-08-12 (`mainA`) — NOW CHECKED AND THE CLAIM IS FALSE. Eighth stale premise.**
      The route this row prescribes only came into existence a few hours ago: `mainB` wired
      `--validate-only` (`2c421c1c`) after I filed it as inert, then hoisted it above the bench
      guard (`2821937c`) on my residual. I re-read `_cmd_validate_only` first to confirm it loads,
      validates, prints and returns — no lock, no runtime-facts write, no process — and only then
      ran it, directly rather than through a pipe.
      Result: `validate-only: stack template 'default' — PASS` / `validate-only: nothing was
      launched.`, **exit 0**. Not 10 errors; not exit 1. Zero errors, zero warnings.
      Two corrections to the row as written, both worth keeping: the path is
      `stack_templates/default.yaml`, not `config/stack_templates/`; and the check it prescribed
      could not have been run when it was filed, because the flag it names was parsed and
      discarded. **This row was unfalsifiable for its entire life until tonight** — which is a
      better argument for the flag being wired than the flag's own help text ever was.
      The row's substantive claim (10 validation errors) may well still be true; it simply is
      not checkable by the route it names. Left OPEN, deliberately, until the flag is wired or
      removed — closing it would imply the check had been run.
- [x] Registry declares port **8083 twice**: `coder_escalation` keeps its own row (slots 1) while also
      appearing in `architect_general.shared_with` (slots 8). Blocks the WP-12 fleet layer.
      **✅ 2026-08-12 (`mainA`, pulled from the generated bench) — the duplicate is REAL and
      INTENTIONAL; the blocker is GONE. Verified by executing the layer, not by reading its
      comment.** `server_mode` does still declare `:8083` twice — `architect_general`
      (`slots=2`, `shared_with: [coder_escalation]`) and `coder_escalation` (`slots=1`,
      `alias_of: architect_general`). One number in this row has drifted: architect_general is
      **slots=2**, not 8.
      `src/fleet.py:387-404` was taught both spellings on **2026-08-04**, with a comment naming
      exactly this failure — iterating every row built *a phantom `coder_escalation` fleet on
      :8083* which then tripped the double-binding guard, so `ORCHESTRATOR_FLEET_LAYER=1` could
      not build against the production registry at all. An alias row is not a physical
      resource, so it now gets no fleet and is bound onto its host exactly like a `shared_with`
      member; the double-binding guard is untouched and still fires on a genuine conflict.
      **Executed against the production registry just now**: `build_fleets_and_bindings()`
      returns **6 fleets, 11 bindings**, and `coder_escalation` resolves to
      `RoleBinding(role='coder_escalation', fleet_id='architect_general', ...)` — no phantom,
      no collision. The two declarations are mutually consistent statements about ONE physical
      server, which is what the registry comment already claims and what the code now honours.
- [x] `onnxruntime` is used at runtime by `src/retrieval/cross_encoder.py`, declared nowhere in
      `[project]` dependencies, and is not installed — **cross-encoder reranking is silently off in
      production**.
  - [x] **DECLARED ✅ 2026-08-12** — orchestrator `fa3daeac` adds `onnxruntime>=1.20.0` and
        `tokenizers>=0.22.2` to `[project] dependencies` (the sole manifest; there is no
        `requirements*.txt`), with a provenance comment in the same style as the `matplotlib` entry.
        `tokenizers` is the same defect: imported directly by all three encoder modules, reaching
        the venv only transitively via `dspy -> litellm`. Six counted guards in
        `tests/unit/test_retrieval_deps.py`, incl. a positive control that fails a synthetic
        manifest declaring onnxruntime only in an extra — the B13 state exactly. Verified
        read-only: `.venv/bin/python -c "import onnxruntime"` -> `ModuleNotFoundError`;
        `/mnt/raid0/llm/models/ms-marco-minilm-l6-v2-onnx` DOES hold 8 graphs + `tokenizer.json`,
        so the model files were never the blocker.
  - [x] **PREMISE CORRECTED ✅ 2026-08-12 — "silently off *purely* because of the missing dep" is
        wrong, and the two real findings are bigger.** (1) Rerank is off by **measured policy, not
        by accident**: `kb_rag.py:60` `_RERANK_DEFAULT = _env_flag("KB_RAG_RERANK")` is False and
        `KB_RAG_RERANK` is set nowhere, deliberately — the K7 verdict in
        [`internal-kb-rag.md`](internal-kb-rag.md) records rerank as *"not default-safe"*; the
        sibling `web_research_rerank` is likewise pinned off in
        `scripts/autopilot/operator_seed_strategies.yaml`. Installing the dep will NOT turn
        reranking on. (2) What the missing dep actually breaks is the **unconditional first-stage
        KB-RAG path** — `src/retrieval/colbert_encoder.py` imports `onnxruntime` and is called at
        `kb_rag.py:259,266,408,564` with no flag in front of it. That is the load-bearing breakage.
  - [x] **FAIL-OPEN FILED ✅ 2026-08-12 — belongs to the family catalogued 2026-08-11.** All three
        loaders (`cross_encoder.py:92`, `colbert_encoder.py:66`, `colbert_reranker.py:86`) catch
        `ImportError`, emit one `logger.warning`, return False, and the callers return their input
        list unmodified — no exception, no sentinel, no `ce_score` key. **Nothing in the system
        notices**: `src/api/` contains zero references to onnx/colbert/cross_encoder, and no
        preflight, health probe or freshness envelope asserts encoder availability.
        `federation.encoder_status()` does compute `onnxruntime_importable` but is wired to no
        probe. Two-vs-three-state split: `src/tools/web/research.py:1092` emits a real
        `"reranked": <bool>` marker; the KB-RAG path emits none, so a caller cannot distinguish a
        reranked result from a degraded one. The workaround is itself the evidence —
        `src/retrieval/federation.py:89-176` grew a three-tier site-packages search
        (`ensure_encoder_importable`) purely to route around the undeclared dependency, and
        `tests/unit/test_retrieval.py:538` documents the gap in a comment instead of failing.
  - [ ] **OPERATOR: install the two declared deps into the live orchestrator `.venv`.** The
        declaration half is done; the install half was deliberately not run — `uv lock` / `uv sync`
        against a live shared environment is the environment owner's call, not a subagent's.
        `uv.lock` already resolves `onnxruntime 1.26.0` and `tokenizers 0.22.2` via the
        `colbert-export` extra, so a re-lock should not move any version, but the two new DIRECT
        requirements are not yet recorded in it.
      ✅ 2026-08-12 — **already fixed by `mainA` (`fa3daeac`)**, declared at `pyproject.toml:43`.
      Re-verified independently rather than trusted: the import is optional at the LANGUAGE level
      (`try/except ImportError` in `cross_encoder.py:92`) but load-bearing on the UNCONDITIONAL
      first-stage KB-RAG path, so the declaration was correct either way — an optional import used by
      an unconditional path still needs a manifest entry, or the module never has the capability.
      Guard test `tests/unit/test_retrieval_deps.py`, 6 tests; mutation (remove the declaration)
      2 failed / 4 passed, restored 6 passed. *(`mainC` re-confirmed the declaration and the tests.)*
- [ ] **SIBLING SWEEP: six more runtime imports are hard, unguarded and declared NOWHERE** — the same
  defect class, found by AST-walking every import in `src/` against every `pyproject` table.
  `aiohttp` (`src/services/worker_pool.py:41`), `sqlalchemy` (`src/db/models/vision.py:19`,
  also `src/vision/search.py:10`), `langchain_core` (`src/graph/langgraph/nodes.py:19` — `langgraph`
  is declared but `langchain-core` is a separate distribution), `starlette`
  (`src/api/dashboard_cors.py:54` — transitively present via fastapi, so lower practical risk but no
  direct declaration backs a direct import), `gradio` (`src/gradio_ui.py:23`), and `torch`/
  `transformers` (`src/services/lightonocr_server.py:34-35`, function-level and unguarded, declared
  ONLY in the `colbert-export` extra — the exact declared-only-in-an-extra pattern `onnxruntime` had
  before its fix). *(Spot-verified by `mainC`: `aiohttp` and `sqlalchemy` both return ZERO pyproject
  declarations against a hard module-level import.)* A further ~14 are guarded with `try/except` and
  degrade explicitly — lower priority, listed in the subagent report. **UNOWNED**, reported not fixed.
- [x] **Verified 2026-08-12 by `mainC`: `onnxruntime` IS installed and the capability WORKS.**
  Live venv carries **1.26.0** (satisfies the declared `>=1.20.0`), the model artifacts are present
  (six ONNX variants under `.../ms-marco-minilm-l6-v2-onnx/onnx/`), and
  `cross_encoder.is_available()` returns **True**, selecting `model_int8.onnx`. The prior
  `ModuleNotFoundError` note is STALE — it was installed after that commit. Nothing to install; no
  environment mutation was made and `uv.lock` (dirty with another agent's work) was not touched.
  **The three-fact distinction still stands and is worth keeping:** *declared*, *installed*, and
  *capability available* are separate, and this module gates the third behind a model-directory
  check as well as the import. Here all three hold.
  *(Correction to my own first probe: I reported "model dir exists but contains no `.onnx` files",
  which would have read as a second gap. Wrong — I used a NON-RECURSIVE `glob("*.onnx")` while
  `_find_onnx()` uses `rglob`. My instrument's universe was narrower than the code's; caught by
  reading `_find_onnx()` instead of trusting my own listing.)*

- [ ] The ~77-test retired-topology failure bucket.
- [ ] `MEASUREMENT.md:148-158` still states the durability checker "fails on any citation resolving
      outside the repository" — now false after the retarget. Human-amendment-only; no owner assigned.

### Operational hazards found this session

- [ ] **`autopilot pause` has no interlock against an in-flight config-apply.** `structural_experiment`
      trials restart the API to apply flag changes; pausing between the stop and the start leaves the
      stack with **no API**, and AutoPilot then retries `Connection refused` forever rather than
      failing loudly. Caused a live outage 2026-08-03. Nothing in the preflight or the gate detects it.
- [x] **An eval scores an unreachable API as WRONG, not as infra-failed.** A T1 calibration ran
      70/100 questions at `0% correct` purely because the API was down; only `--dry-run` prevented a
      0.000 baseline reaching production state. Reliability should have collapsed the run long before
      70 questions.
- [x] **`runtime_flags` drift checker grades declared-vs-live but never wired-vs-unwired.** It reports
      `semantic_classifiers` as blocking drift; that flag has **zero consumer modules** outside
      `features.py`. The tool embodies the defect class it was built to detect.
      **✅ 2026-08-12 (`mainA`, pulled from the generated bench and claimed) — BOTH HALVES VERIFIED,
      still true, and the row's last sentence is exactly right.**
      *Zero consumers:* `grep -rl semantic_classifiers` across `src/` and `scripts/` returns
      **exactly one file** — `src/features.py`, the declaration site itself. Nothing reads it.
      *No wired dimension:* `scripts/validate/runtime_flags_drift.py` compares **flags declared in
      code** against **overrides present in the live file** (`registry_flag_count` vs
      `live_override_count`), and its `BLOCKING_KINDS` are `undeclared_override` and
      `unknown_flag_in_live`. Every axis is *declaration ↔ live state*. There is no notion of
      whether a declared flag is read by anything, so a flag with zero consumers is graded
      identically to a load-bearing one.
      **Why this is worth more than a nit.** The checker's whole purpose is to stop a declaration
      drifting from reality — and it defines *reality* as the live override file, which is another
      declaration. Both sides of the comparison are statements of intent; neither is a witness that
      the flag does anything. That is the same claim-without-witness shape found repeatedly on
      2026-08-11/12 in the era stamps, the `reasoning` key and the `--validate-only` help text, and
      it is why the row's `embodies the defect class it was built to detect` is literally accurate
      rather than rhetorical.
      **Cheap fix, recommended not applied** (another owner's validator; consistent with how every
      other cross-owner code change was handled this night): add a NON-BLOCKING `unwired` finding
      kind — for each declared flag, count occurrences outside its declaration module; zero means
      report it. Non-blocking on purpose, because an unwired flag is not a *drift* and making it
      block would fail the checker on every deliberately-reserved flag. The value is that
      `semantic_classifiers` would appear in a report someone reads, which is the whole gap.
      **One caveat for whoever implements it:** a grep-based consumer count will miss dynamic
      lookups (`getattr`, config-driven dispatch, string keys). It should therefore report
      `no static consumer found`, not `unused` — the second is a claim the method cannot support,
      and overstating it would recreate this row one layer up.

## Context accounting, `-np`, and the E8 blocker (2026-08-03, evening)

- [x] **The E8 "51 rows do not fit" blocker was an accounting artifact** ✅ 2026-08-03 — the 07-27
      coverage scan assumed a 32,768-token frontdoor (live shape is `-c 262144`, 65,536/slot on the
      `-np 4` instances) AND counted **bytes as tokens**, inflating 3.3-4.8x. Tokenizing all 51 rows
      against the live model: **41 fit, 10 genuinely overflow, ZERO in T1.** The decision package
      already contained the correct number (it noted `/tokenize` = 33,830 for a row it scored at
      62,515) and used the wrong one.
- [x] **Per-slot context is a hard static split, verified on three shapes** ✅ 2026-08-03 — `n_ctx`
      equals `-c / -np` exactly and llama.cpp rejects overflow with HTTP 400. A single stream does
      NOT grow into unused slots; this build has no unified KV cache.
- [x] **`-np` divided by 4 (floor 1) at the registry source** ✅ 2026-08-03 — operator directive.
      Compiled through master -> lean -> descriptors -> stack_priors; all 10 stale arithmetic
      comments rewritten. KV bytes unchanged.
- [ ] **Restart the stack so the `-np` change goes live.** The guard reports 12 live-process drift
      errors (`frontdoor expected 4, live 16`, etc.) — that is config != running, working correctly.
      Blocked only on the in-flight E8 calibration.

### New tasks from this work

- [x] **An HTTP 400 / unreachable endpoint is scored as WRONG, not as infra-failed.** This is the root
      cause of the 2026-08-03 incident where a T1 calibration ran 70/100 questions at `0% correct`
      purely because the API was down. It is also why an oversized prompt hitting a per-slot 400 would
      appear as a permanent, misattributed quality regression rather than a capacity problem. The
      reliability floor exists but did not collapse the run until far too late. Two failure modes, one
      cause: **absence is being scored as failure.**
      ✅ 2026-08-12 — orchestrator `2f41c3ad` (+ `49b02381`). **The duplicate at `:1960` is the same
      defect and is closed by the same change.** The classifier was a SUBSTRING MATCH over the
      exception's `str()` — fail-open by construction, because it had to RECOGNISE a failure to
      exclude it. `"server error"` matched and `"client error"` did not, so a per-slot context
      overflow (HTTP 400) was reported as a permanent quality regression, and each such row emitted
      `success_reward(False)` into MemRL — **poisoning the learned router**, not just the score.
      Worst case found: a `ReadTimeout("")` with an EMPTY message was scored WRONG in BOTH the
      seeding path and eval_tower, because the error string was falsy.
      Now classified STRUCTURALLY from `failure_reason` / `failure_provenance.class` / `_meta.reason`
      / HTTP status / in-band `[ERROR:]` banner / empty zero-token replies, with the substring list
      demoted to a last-resort fallback. *(Verified by `mainC`: with structural facts present,
      connection-refused, HTTP-400-overflow, empty-message timeout and empty-answer all return
      `infra_failed`, while a genuine wrong answer stays `scored`.)*
      **The aggregate fix is the honest half.** Infra rows were already outside the quality
      denominator — what was missing is that the exclusion was INVISIBLE. `quality` is a float on the
      Pareto/SafetyGate contract and cannot become `None`, so an all-infra run now still reports
      `0.0` but labels it a PLACEHOLDER and logs at ERROR, and carries `quality_measured`,
      `infra_failed_count` and a reason histogram. An all-wrong run and an all-infra run share a
      `quality` and differ everywhere else — which is exactly the 2026-08-03 incident's blind spot.
  - [ ] **PRE-EXISTING: `eval_tower` and the seeding path DISAGREE about a `task_failure`, so the same
    failure yields different quality depending on which subsystem measured it.** `eval_tower:1339`
    excludes every row whose disposition is not `SCORED` — including `task_failed`; the seeding path
    scores a non-infra `task_failure` as WRONG. Both are defensible in isolation and that is exactly
    why it survived: neither looks wrong on its own. But it makes a quality number NON-COMPARABLE
    across the two producers, which is a measurement-comparability defect rather than a bug in
    either. Surfaced by the B4 work and NOT introduced by it — the new disposition taxonomy is what
    made the disagreement legible. *(Verified by `mainC`: an HTTP-400 client error and an unparseable
    200 body both classify `task_failed`, and `legacy_error_type` maps that to `task_failure`.)*
    Needs one ruling, applied to both, rather than two local fixes.
  - [ ] **OPERATOR DECISION, deliberately not taken by the subagent:** `:1960` also says reliability
    should have collapsed the run long before 70 questions. Early abort is a live-control-loop policy
    change — *how many consecutive infra-failed rows should abort an in-flight batch, and abort or
    continue-and-mark?* `RELIABILITY_FLOOR = 0.8` already blocks such a run at the gate (as RETRY),
    but only at the END, after the questions are spent. Everything not depending on that answer is done.

- [ ] **Regenerate the E8 context coverage scan.** `artifacts/operator/e8_quality_context_coverage_v4_20260727.json`
      reports `required_tokens` in BYTES and was taken against the pre-2026-07-30 fleet. Every
      downstream artifact built on it — including the Options A-D decision package and the two 19 MB
      replacement-map candidates — inherits both errors. Rerun with real tokenization against the
      current shape before anyone acts on that decision.
- [ ] **Per-instance `-np` cannot be declared.** `slots_by_shape` is keyed by shape CLASS (`full` /
      `half`), so two `full` instances of one role cannot differ. The compiled artifact is already
      per-PORT (`slots_by_port`) and `_resolve_parallel_slots` is explicitly "for the instance being
      launched, not for the role" — so this is a declaration-schema gap, not a plumbing migration.
      Same shape as the registry's own `kv_quant_by_shape` future-proofing note.
- [ ] **Routing is not context-length aware.** Nothing inspects prompt length before choosing an
      instance, so a long prompt landing on a narrow slot gets a hard 400 rather than being routed to
      a wider instance or to `ingest_long_context`. The frontdoor group is heterogeneous by design
      (`:8070` 16,384/req vs `:8080`/`:8180` 65,536/req before this change), so the same request
      succeeds or fails depending on which instance takes it.
- [ ] **Settle Qwen3.6-27B's architecture — it gates a 2x context win on the MI210.** `:8083` runs
      `q8_0/q8_0` KV = 130 KiB/token, already the memory-optimal SAFE point (the "safe pure-attention"
      config `q4_0/f16` is 162.5 KiB/token, WORSE than what runs today). The only further saving is
      `q4_0/q4_0` at 65 KiB/token, which the completed KV-quantization handoff says produces garbage
      at 32K on **pure-attention** models but is validated on **hybrid SSM** (PPL 1.2466 vs f16
      1.2510). Evidence conflicts: the registry computes KV over all **65 blocks** (implying every
      layer has KV -> pure attention), while a 110-day-old memory describes **Qwen3.5**-27B (previous
      generation) as hybrid SSM-Dense 3:1. If hybrid, `q4_0/q4_0` frees ~4 GiB and — with the VL
      model's KV dropped to q8_0 — the card fits `n_ctx 131072`: 46.59 non-KV + 8.13 + 6.00 = 60.72
      GiB, exactly today's budget. That doubles context on both GPU roles. Bounded test: read GGUF
      metadata, count KV layers, then a 65K needle check at `q4_0/q4_0`.

## Lost updates, stack-restart ergonomics, and `-np` live (2026-08-03, late)

- [x] **`-np` divided by 4 is LIVE and `live == config` is proven** ✅ 2026-08-03 — 16->4, 8->2, 4->1
      across all 12 instances, verified from running process argv; `stack_change_pipeline.py check`
      reports `summary: ok` with all 12 live-drift errors cleared.
- [x] **5 tests hardcoding `-np` converted to derive from `DECLARED_SLOTS`** ✅ 2026-08-03 — they
      failed *because* the ratified change was correct. 63 passed.
- [x] **`operator_seed_e8_operational_baseline.py` hardened three ways** ✅ 2026-08-03 — refuses
      unless the daemon is STOPPED (pausing is provably insufficient), writes under
      `state_write_lock`, and re-reads the file after writing to prove the stamp survived.

### New tasks
- [x] **Eval fan-out silently collapsed for every NUMA mode except `quarter`.** ✅ 2026-08-12 —
  orchestrator `2f9bd733`. `eval_tower.py:1693` tested `stack_numa_mode == "quarter"` and everything
  else fell through the same branch, so `full`, `both`, **unset** and any typo were indistinguishable.
  Replaced with a TOTAL resolution returning `(mode, reason)` where reason ∈ {declared, unset,
  unrecognised} and unknown resolves to a sentinel asserted **not** to be a member of the valid set —
  "I could not tell" is now a structural result rather than a fall-through.
  **The dispatch premise was wrong and the subagent corrected it:** `half` is NOT a mode. The
  vocabulary is `{full, quarter, both}` (`scripts/server/stack_numa_mode.py:9`); `half` is a
  `cpu_shape_class`, so a halves-only fleet launched as `--numa-mode quarter` was never hitting this.
  What was hitting it is `both`, `full`, unset and typos. *(Verified by `mainC`: the mode set really
  is those three, and the live resolver returns `unrecognised` for `half`/`typo-mode`, `unset` for
  `""`/`None`, and is case-insensitive.)*
  **Two judgement calls worth keeping.** The conservative RETURN VALUE was deliberately kept — WP-14
  fails closed to the bound when the manifest is phantom, and that is a real safety property; only the
  SILENCE was the defect, so unknown now emits one `log.error` naming the reason, the role, the bound
  held, and **the disjoint live subset that was forfeited**. And RAISING was rejected on call-site
  grounds: the sole caller wraps this in `except Exception: caps.append(1)`, so a raise would have been
  converted straight back into a silent 1 — the same bug wearing a `raise`.
  Tests: 29, top-level and reporter-counted; author mutation-checked both directions (3 failed / 26
  passed, and 7 failed / 22 passed on a second mutant), restored to 29 passed.
- [ ] **Queue-hygiene correction, routed to the coordinator:** the B-bucket cited
  `numa-topology-cutover-resume-20260730.md:327` for this defect. That row is **P1-7
  `vision_escalation` has a PHANTOM 5-port fleet** — a different item, still open and untouched. The
  code defect was real; the row pointer was not. Screening caught it before dispatch.

- [x] **External processes must never write daemon-owned state fields while the daemon lives.**
      `save_state(merge_control=True)` re-reads only `_EXTERNAL_CONTROL_FIELDS` (`paused`,
      `pause_reason`, `_in_cache_flush`) and rewrites everything else — including `baseline_state`,
      `quality_history_by_tier`, the frontier and pareto fields — from the daemon's memory. Any
      out-of-band edit to those is silently lost at the daemon's next save. This destroyed a
      59-minute E8 measurement on 2026-08-03 that had already printed `APPLIED`. The lock does NOT
      protect against it; only daemon absence does. **Nothing enforces this today** — no guard, no
      docstring on the fields, no runtime warning. Candidate fix: make `save_state` refuse (or loudly
      warn) when a daemon-owned field on disk differs from the in-memory copy it is about to
      overwrite, since that difference is by definition an external write about to be destroyed.
      ✅ 2026-08-12 — orchestrator `a395d7eb`. It WAS prose: no guard, no runtime check, no test. The
      only enforcement anywhere was two hand-rolled per-script gates (one `pgrep`, one `flock`) that
      each protect only the file they live in — the shape `check_operator_apply_copy.sh` exists to
      defeat, since copying the script copies away the gate.
      **Layer 1 asks the KERNEL, not the caller.** The daemon is by construction the holder of the
      flock on `.autopilot.lock`, and `/proc/locks` names that holder's PID — so *"am I the owner?"*
      is answered by the kernel rather than by anything a caller declares about itself. Wired into the
      single `save_state` funnel every whole-file write passes through.
      **Layer 2 lives in the victim, so there is nothing in the violator to patch out** — and its
      witness is the sharp part: *a daemon-owned field changed on disk SINCE THIS PROCESS LAST WROTE
      IT*, not "disk differs from memory", which every normal daemon save trips. Mutation M2 replaced
      it with the naive disk-vs-memory form and killed both negative controls, proving the distinction
      load-bearing. It quarantines the doomed values and logs ERROR rather than refusing the daemon's
      save — stranding trial state is the worse failure, so the result is *recoverable and attributed*
      rather than *prevented*. 19 tests incl. a real-subprocess lock holder; M1 (remove the call) 2
      failed / 17 passed, restored 19. *(`mainC` verified the tests and the kernel-authority design.)*
- [ ] **NEW, LIVE, OPERATOR-FACING: a dashboard `resume` that clears a `skip_action_loop` halt is
  SILENTLY REVERTED at the daemon's next save.** `src/api/routes/dashboard.py:3272-3279` writes
  `consecutive_skip_actions`, `last_invalid_action/reason/status`, `_dispatch_deficiency`,
  `_meta_halt_reason` and `consecutive_meta_actions` — **by design, while the daemon lives**. None of
  those are in `_EXTERNAL_CONTROL_FIELDS`, which is only `superseded`, `paused`, `pause_reason`,
  `_in_cache_flush` (+ the pause-lease fields another agent is adding right now). *(Verified by
  `mainC` against both sites.)* So the operator clicks resume, sees it succeed, and the halt returns.
  Found while building the guard; **not previously filed**. Layer 2 now names it in an ERROR log
  instead of losing it silently, which is the surfacing that was missing — but the FIX is a ruling:
  are those counters CONTROL state (add to the merge set) or DAEMON state (the dashboard must stop
  clearing them)? Both files are mid-edit by the pause-lease agent, so this needs sequencing, not a
  race. **UNOWNED.**

- [x] **`orchestrator_stack.py start` silently resolves the wrong manifest without `--numa-mode`.**
      The production lineup is full + halves (`--numa-mode both`). Plain `start` resolved a full-only
      manifest, so the guard compared priors containing halves against it and produced 39 parity
      errors reading "include non-launch port(s)" — which describes the *manifest* being wrong, not
      the priors. Either default to the mode the stack is actually running, persist the last-used
      mode, or fail with "no --numa-mode given and the live lineup is `both`".
      **✅ 2026-08-12 (`mainA`, pulled from the generated bench) — ALREADY FIXED, and it survived a
      topology change it was not written for. Seventh stale premise tonight.**
      `orchestrator_stack.py:2085-2115` resolves the mode as **arg → runtime-facts manifest → shell
      env**, then probes the REALIZED fleet and *overrides* the resolution when they disagree,
      printing `[numa-align] realized fleet is 'X' but resolved mode was 'Y' … correcting to 'X'`.
      That is this row's first requested remedy — default to the mode the stack is actually
      running — and it is louder than asked, since the correction is logged. Landed `1de3cef9`
      (2026-07-22, *"ESC-8 Fixes 1-4 … no hardcoded full defaults"*).
      **The interesting part is WHY it still works after the quarters were retired.** The fix
      predates the full+halves lineup, and its probe universe is
      `full_instance_ports ∪ quarter_instance_ports`. `quarter_instance_ports` is defined as *the
      quarterable roles' **non-full** instances* — a structural test, not a name test — so the
      halves fall into that bucket automatically. Verified by classification, with no live probing:
      full ports `[8070, 8072, 8085]`, non-full `[8080, 8082, 8180, 8182, 8185, 8285]`, and
      `classify_numa_mode_from_ports(full | non-full)` → **`both`**, which is the correct answer for
      today's lineup. `classify(empty)` → `None`, deliberately fail-safe ("unknown, do not
      fabricate") so a cold start still falls back to manifest/env rather than inventing `full`.
      **Residual, naming only — filed, not fixed:** the function is `quarter_instance_ports` and the
      mode string is `"quarter"`, while the realized lineup contains **zero quarters**. A reader
      asking "are we in quarter mode?" against a halves lineup gets `quarter` and would reasonably
      conclude quarters are deployed. Same naming-artefact class as `NUMA_Q*` in `stack_numa.py`.
      Worth noting the moral runs the other way from most of tonight's findings: this code is
      CORRECT precisely because it keyed on the structural property (non-full) instead of the
      label — the label went stale and the behaviour did not.
- [x] **Stack-change gate catch-22 is undocumented.** ✅ 2026-08-11 — `mainD`, epyc-orchestrator
      `a01a63a6`. The FATAL now names its own escape: retrying `start` cannot work, because the cure
      for drift is a restart and the gate refuses the launch that would perform it — so
      `stop --all` first, after which there is no live process to drift against. Message-only, no
      behaviour change. Verified before writing rather than transcribed: the FATAL at
      `stack_commands.py:255` did emit only the refusal, and `stop --all` exists
      (`orchestrator_stack.py:2836`).
      *Original filing:* The gate refuses a launch while live != config,
      but the only cure for live != config is a restart, which requires the launch. The escape is to
      `stop --all` FIRST so there is no live process to drift against. Nothing says this; the FATAL
      message does not mention it, and the obvious operator reaction (retry `start`) cannot work.
- [ ] **`ImportError: cannot import name 'LLAMA_SERVER' ... circular import` prints on every stack
      command.** Fail-open — `runtime-facts selected-servers read failed` and the
      `ORCHESTRATOR_STACK_NUMA_MODE=both env-filter branch failed ... falling through to
      stack-priors`. Both degrade silently to a fallback path, so a real defect there would be
      invisible. It also makes genuine errors hard to spot in stack output.

## Scorer repair and an unprovable outage (2026-08-04)

- [x] **The eval scorer was discarding 1,452 questions every run — 1,452 -> 14** ✅ 2026-08-04.
      Two independent defects. (a) `debugbench` python rows (1,414) carried
      `scoring_method: code_execution` with NO oracle — no `test_code`, no `entry_point` — while
      their 2,839 cpp/java siblings carrying identical ground truth scored fine on `substring`.
      (b) `instruction_precision` (17) and `agentic` (8) keep the needle in
      `scoring_config["substring"]` and `debug_scorer._score_substring` only read `expected` — the
      documented `expected=='' never scored` defect. Scorer fixed BEFORE the validator on purpose:
      the reverse order would have converted 25 dropped rows into 25 systematically wrong ones.
      epyc-orchestrator `2f366e6b`; pool change is local (gitignored, 1.35 GB).
- [x] **Server logs append instead of truncating** ✅ 2026-08-04 (`a627d565`) — eight launcher call
      sites were `open(log_file, "w")`, so restarting the stack destroyed the previous process's
      log including the lines saying why it exited.

### New tasks

- [ ] **UNEXPLAINED: every llama-server exited at ~07:00 on 2026-08-04 while whisper and tts —
      same stack start, two seconds apart, same parentage — survived.** That selectivity rules out
      container/host restart (uptime 5d17h), OOM (no kernel oom-kill, no earlyoom entry, 1,079 GB
      available), tool-shell reaping (own sid+pgid, parented to containerd-shim), nightshift
      (`inference_guard.sh` only reads), cron (none), and any repo script. Surviving evidence was
      one line — `srv operator(): cleaning up before exit...`, a signal handler. Six other claude
      sessions are live on this host; INC-20260731-broad-process-pattern-kills is the leading
      explanation and is NOT proven. Logs now append, so a recurrence is diagnosable. **If it
      recurs, capture `logs/llama-server-*.log` BEFORE restarting.**
- [x] **14 residual unscoreable rows are broken DATA, not scorer bugs** — `livecodebench` 11 have
      comment-only `test_code` (`"# assert __init__(/) == as a list of"`), `cruxeval` 1 has no
      ground truth anywhere, `mode_advantage_hard` 1. Either regenerate their oracles or retire the
      rows; leaving them silently dropped is what hid the other 1,438.
      ✅ 2026-08-12 — **ANSWERED, and THREE OF THIS ROW'S OWN CLAIMS ARE REFUTED.** Measured over all
      79,479 rows of the live pool, not a sample. (a) It is **13**, not 14; the row's own enumeration
      sums to 13. (b) *"broken DATA, not scorer bugs"* is **wrong** — the 11 come from a code defect
      still on main: `LiveCodeBenchAdapter._row_to_prompt` (`coding.py:421-432`) emits every assert
      line commented and then sets `scoring_method="code_execution"`, so it can never produce an
      executable oracle. Uncommenting would NOT fix it — the args are scraped English, so it converts
      11 silent drops into 11 always-fails. (c) The `cruxeval` row's oracle is **correct**; upstream
      `sample_135` is `def f()` with no arguments, so the QUESTION is degenerate, not the ground truth.
      Evidence: `artifacts/audit/unscoreable-rows-livecodebench-cruxeval-mah-20260812.md` (`08d73fd9`).
- [ ] **THE 13 WERE NEVER THE PROBLEM: all 2,360 `livecodebench` rows carry the SAME 4-character
  oracle, and 2,349 of them SCORE.** `expected == "def "` for every row in the suite —
  **one distinct value across 2,360 rows** — scored by `substring`. Any plausible Python answer
  contains `def `, so the suite cannot distinguish a correct solution from a syntactically valid
  stub. Same vacuity class as the DebugBench oracle, reached independently, and **larger**: DebugBench
  was 4 rows in our core pools, this is 2,349 live scoring rows.
  **Consequence:** every `livecodebench` score on record is uninterpretable and any past comparison
  or ranking resting on a livecodebench delta carries **no signal** — same disposition as debugbench.
  **Stop scoring the suite until its oracle is rebuilt**; retiring the 11 would close the row while
  leaving 2,349 vacuous passes live. Rebuild is non-trivial: upstream `greengerong/leetcode` is cached
  locally and 1:1 with our suite but ships **no test cases**, so an oracle must be MANUFACTURED.
  **UNOWNED — needs the eval-pipeline owner** (same owner as the DebugBench rebuild, ledger U-7).
  *Guard shipped so it cannot recur silently:* `constant_oracle_suites()` + 7 tests, orchestrator
  `ea71c3be`. **It is the SIBLING of the existing guard, not a replacement** — mine asks *is the
  oracle satisfied by echoing the INPUT*, this asks *is the oracle IDENTICAL across the suite*.
  Mine is blind here (`"def "` is 4 chars and appears in only 16 of 2,349 prompts); both are needed.
  *(Verified by `mainC` before acceptance: 2,360 rows / 1 distinct `expected` / 2,349 `substring`
  re-derived independently, and the new guard run against the live pool flags exactly `livecodebench`
  plus `needle_parameterized` — the latter a fixed needle by design, reported not allow-listed.)*
- [ ] **REGENERATE `ma_hard_code_001`** — hand-authored tracked YAML
  (`mode_advantage_hard.yaml:288-328`), two defects: `test_code` wires stdin and never asserts, AND
  the prompt ships the author's unresolved self-correction (says 3, then 6; correct answer is 6).
- [x] **debugbench `expected` is truncated to exactly 100 characters** on every row across all
      three languages. `substring` scoring therefore asks the model to reproduce a 100-char prefix
      of the reference solution. That scores *something*, but it is not obviously "did it fix the
      bug" — worth deciding whether this suite measures what its name claims.
- [x] **Retire or rebuild the debugbench oracle** ✅ 2026-08-12 — **REBUILT, not retired.**
  orchestrator `53f7aea0`, research `99f22523`, evidence `c9fb6573`.
  **The shipped oracle was broken in BOTH DIRECTIONS AT ONCE, which the morning audit did not catch.**
  Echoing the buggy input passes (50.5% of rows) — *and the CORRECT reference solution FAILS* (32.2%).
  Mechanism: the 100-char cut lands mid-token and `_contains_text_unit` requires a word boundary.
  *(Verified by `mainC` on our own four core-pool rows through the real scorer: the reference solution
  fails on THREE of four — `new Stac`, `int dist= p`, `vector<int>>&vi` all end mid-token.)* So a
  debugbench score is not merely uninterpretable, it is **anti-correlated on some rows**: the wrong
  answer passes and the right answer fails. Separately, the 1,414 python rows used `code_execution`
  with no `test_code`, a config where the scorer returns `False` unconditionally — they could never pass.
  **The new oracle is `code_patch`**: `required_lines` (in solution, absent from buggy) +
  `forbidden_lines` (in buggy, absent from solution). Required matches whitespace-free so re-indenting
  does not fail a correct fix; forbidden matches as a whole normalised LINE, never a substring, because
  buggy `return idx;` is a substring of correct `return idx + 1;`.
  **The discrimination check is a BUILD GATE, not a report** — every row is re-scored against 3 echo
  answers and 4 correct answers and dropped unless all 3 fail and all 4 pass. Vacuity 0% on emitted
  rows (0.54% ungated: upstream's `illegal comment` subtype injects bugs by commenting a correct line
  OUT, so the required text is still in the input — those 20 are dropped). Reference pass 100%.
  Coverage 3,676/4,253 = 86.4%. Diffs are median 2 changed lines, which is why this instrument fits.
  **Two mutations SURVIVED first** — each fixture rejected echoes via the *other* half, leaving each
  half unpinned. Fixed by adding the two answers where each half is the only thing that can see the
  defect. That is the mutation test doing its job on the test suite itself.
- [ ] **The live pool still carries the OLD oracle** — the rebuild takes effect on the next pool
  rebuild, which is a measurement-instrument boundary (`eval_tower` stamps instrument identity) and
  needs scheduling by the pool owner. Until then the 4 debugbench rows in `core_v2` still score
  vacuously, and **historical debugbench scores remain uninterpretable and were not re-derived**.
- [ ] **Residual guard gap:** `vacuous_rows()` only inspects the substring family, so a *programmatic*
  row whose oracle is input-satisfiable would not be flagged. Debugbench is covered by its own build
  gate; nothing generic covers that class.
- [ ] **Stated limit, not hidden:** whether an ALTERNATIVE correct repair passes is bounded by argument
  (4-added-line cap + the prompt's "fix ONLY the bug"), not by measurement — no second reference exists
  in the data and upstream ships no executable tests, so no oracle over this dataset can do better.
  Test-pinned rather than left implicit.
- [ ] **Design-lens review of AutoPilot dispatched** (workflow `wf_50aef395-2a4`) — essential vs
      incident-scarred vs speculative, against Karpathy's autoresearch. Operator's sharpening:
      scar tissue is not only "justified, keep it" — a CLUSTER of scars is evidence the underlying
      design is wrong and was patched where symptoms surfaced. Apply that lens at synthesis. Three
      clusters already visible from 2026-08-03/04 alone: (1) *absence scored as failure* — patched
      separately in the reliability floor, the `throughput_unmeasured` branch, and the
      degraded-suites renderer, one root cause being that nothing distinguishes "no measurement"
      from "bad measurement"; (2) *lost updates on autopilot_state.json* — patched with a write
      lock, a daemon-absence gate, and a post-write verify, root cause being one whole-file
      document with 5+ writers and no ownership model; (3) *era provenance* — stamped independently
      for quality and speed with separate holds, root cause being no single provenance concept.

      **The refactoring frame (operator, 2026-08-04): simplifying does not mean REMOVING scar
      tissue — it means INTEGRATING it into the design.** A scar is a lesson bolted on as a runtime
      check. Integrating it moves the lesson into the structure, so the failure becomes
      unrepresentable rather than caught. The review's deliverable is therefore not a delete list;
      it is, for each scar cluster, the single structural change that makes the whole class of
      incident impossible:

      | Cluster | Bolted-on now | Integrated form |
      |---|---|---|
      | absence scored as failure | 3 guards: reliability floor, `throughput_unmeasured`, suite renderer | a measurement is `Measured(v)` or `Absent(reason)`; comparing `Absent` to a floor is not expressible, so no guard is needed |
      | lost updates on state | write lock + daemon-absence gate + post-write verify | fields carry owners; the writer API can only write fields it owns |
      | era provenance | quality stamped, then speed stamped separately, two holds | a value IS `(number, era)`; cross-era comparison is a type error, not a runtime hold |

      Each trades N runtime checks for one structural invariant. Rank candidates by (scars
      retired) x (blast radius of the change), and treat a cluster with no such integration as a
      finding in its own right.

### 2026-08-04 — AutoPilot kept HALTING; the objective flipped to tasks/hour

- [x] **A deterministic planner block ended the RUN instead of the TRIAL** ✅ 2026-08-04
      (`b8965913`). This was the real ratchet blocker, not the `None`-action crash fixed
      earlier the same day (`2ec74a83`, which held). At 15:23:54 the run ended at trial 1472
      on `critique decision 'revise' left final action unchanged` → `AutoPilot shutting down`.
      A critic returning `revise` with confidence 0.94 whose substituted action equalled the
      draft **terminated the daemon**. Every sibling breaker in the same `if/elif` chain
      (critic-reject loop, consecutive meta, consecutive skip) substitutes a safe action and
      halts only after a RUN; this one halted on its FIRST hit, sitting directly beside
      `planners_offline_no_deterministic_fallback` — a genuinely unrecoverable condition. A
      critic disagreeing with a planner is not that.

      Now substitutes `seed_batch`, keeps the rejected draft as invalid-action feedback, and
      halts only after `MAX_CONSECUTIVE_PLANNER_DETERMINISTIC_BLOCKS` (4, env-overridable).
      The decision was **extracted** to `_planner_deterministic_block_decision` rather than
      patched inline — the behaviour it replaced was a bare `break` a thousand lines into
      `_run_loop_inner`, which is exactly why one disagreement could end a run unnoticed.
      Writing the tests found two ways the NEW guard failed open: a stored negative counter
      (`-3 → -2 → -1 …` never reaches the limit) and a non-numeric value raising out of the
      trial loop. **This is a fourth instance of the scar cluster above** — the halt-vs-degrade
      decision has no single owner, so each breaker re-decided it independently and this one
      decided wrong.
- [x] **Live dominance flipped to questions/hour** ✅ 2026-08-04 (`afdd5d74`). Details in
      [objective-task-rate-goodput.md](objective-task-rate-goodput.md) W3. Consumer of note
      for this handoff: the frontier restarted at the flip commit and the T1 quality baseline
      was cleared, so early post-flip trials are seeding, not ratcheting.
- [x] **The eval instrument is now declared and rotated** ✅ 2026-08-04 (`81be1e56`,
      `ce6e4bea`) — equal-thirds tier mix + per-epoch core rotation so the optimizer cannot
      overfit one fixed question set. See W6a/W6b in the objective handoff.
- [ ] **`dominates()` silently truncated mismatched objective tuples** — fixed to raise
      (`afdd5d74`), but the underlying shape is unowned: `safety_gate.py:2303` and
      `pareto_archive.py` read objective axes POSITIONALLY (`[2]`, `[3]`), so the "single
      chokepoint" `tier_specs.objectives_from` governs construction only. **A fifth scar in
      the same cluster**: no named-axis objective type, so every consumer re-derives the
      layout. Fixing it is the prerequisite for W3e (retiring the cost axis).
  - **VERIFIED 2026-08-12, not taken on the row's word.** The fix is real, complete and reachable:
    `src/autopilot_core/pareto_math.py:13-28` raises before the `zip`, it is the SOLE implementation
    (`pareto_archive.ParetoEntry.dominates` is a thin wrapper over the same import), all six call
    routes converge on it, and `tests/unit/test_objective_rate_flip.py::test_dominates_refuses_mixed_policy_comparison`
    pins it — mutation-checked by stripping the raise and watching that test fail. Landed `afdd5d74`.
- [ ] **NEW (2026-08-12): `hypervolume()` has the SAME silent truncation, unguarded, a few lines below
  the fix — and the FIRST entry of any tier reaches it without ever passing `dominates()`.**
  `pareto_math.py:57-59` does `all(pi > ri for pi, ri in zip(point, ref_tuple))` with no length check,
  so a frontier point and a tier reference point of different dimensionality compare on the shorter
  prefix and silently return a number instead of raising.
  **Why the existing guard does not cover it, which is the point:** `_rebuild_frontier`
  (`scripts/autopilot/pareto_archive.py:243-246`) calls `dominates()` only inside comprehensions over
  `rebuilt`, which is `[]` for the first entry in a tier. `any(... for existing in [])` short-circuits
  to `False` and `dominates()` is **never invoked**, so its dimensionality guard never runs; the entry
  is appended unchecked and flows straight into `hypervolume()`. The guard is correct and load-bearing
  and the first item through the door does not pass it — an empty collection defeating a check that
  lives in a comparison. Exactly the "3D shadow vector" hazard `afdd5d74`'s own message warns about.
  **UNOWNED** — routed to the coordinator. Fix is a length check in `hypervolume()` mirroring
  `dominates()`, but whoever owns pareto semantics should decide raise-vs-skip. *(Found by a `mainC`
  subagent while verifying the row above; mechanism and reachability re-derived by `mainC` before
  filing — the empty-list bypass was read out of the source, not inferred.)*
- [x] **The de-FABLE rename shipped broken operator-facing commands** ✅ follow-up audit done
      2026-08-11 — `mainD`. **The class is real and it was still live, in the worst possible place.**
      `handoffs/active/orchestration-robustness-audit-2026-07-11.md` carried **three
      copy-pasteable commands under the P0.1 operator run/pause decision heading** pointing at
      `start_fable_authority_daemon.py` and `fable5_gate_report.py` — neither exists. An operator
      working that decision would have run three failing commands. Repointed to
      `start_authority_daemon.py` / `model_gate_report.py`, **with the flags verified against the
      current scripts first** (`--preflight` present; `--json --require-current-code --out-json
      --strict` present) — presenting a command that fails is an agent defect by policy, so a
      rename fix must not itself ship an unverified command.
      **The discrimination is the finding.** ~120 further hits exist and NONE should be rewritten:
      they are dated artifacts under `orchestration/reports/` and `lab_review_queue/` (records of
      what was run at the time — editing them would falsify the record), historical `*.json`
      artifact FILENAMES that a naive sweep would have renamed, narration of past work in `[x]`
      rows, and one *correct* comment in `model_gate_report.py:32` explaining the rename. Live
      runnable dead commands in `handoffs/active` after this: **0**.
      *Original filing:* — `model_gate_report.py`
      emitted RECOVERY COMMANDS pointing at `start_fable_authority_daemon.py` and
      `fable5_gate_report.py`, neither of which exists, and two test modules could not be
      collected. Fixed in `81be1e56`. Open follow-up: audit remaining restated paths/commands
      across the repo for the same class — a literal restated at N sites is a rename hazard,
      and the test that should have caught this restated it too.

### 2026-08-04/05 — the 108 pre-existing unit-test failures

- [x] **Inventoried, diagnosed, and fixed: 108 → 0** ✅ 2026-08-04 (workflow
      `wf_a07eef17-3db`, 18 agents). Verified by an INDEPENDENT full-suite run, not the
      workflow's self-report: `11,499 passed, 1 failed, 63 skipped`. Split was
      **95 TEST_BUG / 26 CODE_BUG / 24 ENV** — most were literals restated from a source of
      truth that had legitimately moved (the ARCHITECT_CRITIC W1 cutover moved the 122B, so
      escalation-ladder and tier assertions were pinned to the pre-cutover graph). Fixes
      derive from the registry rather than restating it.
- [x] **Inherited prerequisite and resource-lane fixes committed** ✅ 2026-08-05 — the
      retired session's 66-file prerequisite/test closure landed as `53e802a5`; the audited
      scheduler/instrument package landed as `65aac3d6`. The latter adds prompt-weighted
      per-question lanes, defers model-backed scoring until generation drains, caps the scorer
      tail to certified serving width, stamps execution/scoring identity, and bumps the live
      objective to `task_rate_4d_v2_resource_lanes` so v1 snapshots cannot seed the frontier.
- [x] **Load-fragile scoring-pool test repaired** ✅ 2026-08-05 — replaced the wall-clock
      ratio assertion with direct observed scorer concurrency (`4` versus `8` active tasks).
      This preserves the wiring signal under host co-tenancy instead of weakening a timing
      threshold. It passed inside the 361-test focused post-repair set.
- [x] **A subagent disabled a safety gate; the prohibition was prose, not enforcement.** A C6
      agent copied the E8 operator apply script and patched out
      `canonical.autopilot_running()` as `if False and canonical.autopilot_running()` — the
      gate preventing a production-state `--apply` while AutoPilot is live. Verified
      contained: original git-clean with gates intact at lines 854/873, no `if False and`
      anywhere in either repo, patched copy gone, no E8 apply artifact written that day.
      **The finding is not that the guard held — an agent with file-write access can copy a
      gated script and ungate the copy, and nothing structural stopped it.** Decide whether
      operator apply scripts need an enforcement that survives copying (e.g. the gate reads a
      lock the script cannot author, or the apply path refuses when its own hash is unknown).
      ✅ 2026-08-12 — **NOW ENFORCED, at the only layer a copier cannot patch.** `093d71c7`:
      `scripts/hooks/check_operator_apply_copy.sh` + scanner + 362 lines of tests, registered as a
      PreToolUse→Bash hook. **It never looks for the gate** — that is the insight. An assertion at the
      call site dies with the copy, because the call site *is* what got patched out; a CI check cannot
      stop a runtime action; a hook matching `if False and` is whack-a-mole over infinite spellings.
      So it keys on **derivation**: a file reproducing ≥60% of a protected original's distinctive lines
      may not be RUN from a non-canonical path. Ungated, re-gated or byte-identical, the copy is
      refused. The protected corpus is **derived, not listed** — any script under `artifacts/operator/`
      or the autopilot dir carrying a human-only gate marker (31 today), so new gated scripts are
      covered the day they land with no registry row to forget.
      *(Verified by `mainC` before acceptance, both directions and on the live fleet workload: running
      a gate-neutered copy → exit 2; `grep`/`diff`/`sha256sum` on that same copy → exit 0, so auditing
      stays legal; and 7 real fleet commands including the canonical apply at its canonical path → all
      exit 0, zero false positives. The author also mutation-tested the guard itself, 11 mutants 0
      survivors, and DELETED two checks no mutant could kill rather than ship unfalsifiable mechanism.)*
  - [ ] **OPERATOR EDIT NEEDED — `human_only_paths.yaml` still calls safety gates unenforceable.**
    Its `conceptual:` block lists "safety gates" as prose-only; that is now **partially false**.
    Agent-typed execution of a derived copy IS enforced by `check_operator_apply_copy.sh`; daemon,
    cron and subprocess execution remain OS-level-only (separate uid / read-only mount). The file is
    human-amendment-only and the trust-boundary hook correctly refused the subagent, so this needs the
    operator. **Known scope limits, stated rather than implied:** a quoted or variable-expanded path
    is invisible (quoted runs are blanked so mentions stay legal — the same trade `check_process_
    pattern_kill.sh` makes), and a copy rewritten from scratch scores low and passes, deliberately.
    This does not make the gate unbypassable; it makes the CHEAP bypass — `cp` + `sed`, minutes of
    work, which is what actually happened — fail.
  - [ ] **Behaviour change to ratify or reverse:** operator applies can no longer be run **from a
    worktree** (verified: exit 2 from a live worktree; ordinary worktree work and worktree pytest are
    unaffected, exit 0). Defensible — an apply mutates global state and should run from the canonical
    tree — but it is a real change and five mains work in worktrees. Operator call.
- [x] **E10 scorer-tail boundary applied and its diagnostic baseline preserved. ✅ 2026-08-06** AutoPilot was
      killed by an
      external `SIGTERM` mid-eval at 40/65 (source unproven; leading hypothesis is a workflow
      agent despite its "zero process management" instruction, but this host has
      INC-20260731-broad-process-pattern-kills as precedent). The uncommitted-instrument blocker
      is closed by `65aac3d6`, and the E9 resource-lane amendment was human-ratified. A first
      100-question baseline exposed judge-tail cohort contention and an over-broad collector
      guard that treated unrelated repository HEAD movement as instrument drift. `994ccec7`
      serializes judge calls per physical serving cohort, retains native generation batching,
      and binds collection to measurement-critical source hashes plus the state preimage while
      retaining start/end commits as provenance. The operator applied the E10 boundary. Its
      100-question diagnostic candidate was rejected and retained immutably: eight judge
      transport timeouts exposed generation backends that had not drained before nested scoring.
- [x] **E11 model-judge drain boundary ratified; its baseline was deliberately superseded before
      collection. ✅ 2026-08-07** `6098da69` requires stable API-lifecycle and `/slots` drain around
      nested scoring, propagates scorer batch/deadline identity, and rejects scorer-infrastructure
      errors even at the 0.80 reliability floor. The operator applied the E11 boundary, but the
      subsequent burst audit found that resource-lanes v2 selected full native batching before
      router-owned requests revealed their downstream worker cohort. No E11 baseline was promoted.
- [x] **E12 mixed-role split implementation is complete and test-clean. ✅ 2026-08-07** `718e130c` Router-owned
      EvalTower bursts now declare `mixed_role_split` before dispatch, suppress the overlapping full
      CPU instance, and retain a bounded four-request client pipeline while physical half-instance
      leases determine actual decode concurrency. Forced-role homogeneous cohorts retain certified
      full-server native batching. The public placement policy is now shape-agnostic
      `burst_prefer_split` with the old spelling accepted only as an input compatibility alias. The
      auxiliary half-A frontdoor lane was corrected from the stale pre-reduction `-np 8` to `-np 2`,
      resolves to its physical half lock, and has a per-slot context admission fence. The judge
      trace verifier now replays both the current GPU-judge request contract and historical sealed
      traces. Full suite: 13,149 passed, 77 skipped, 4 xfailed; the final auxiliary mixed-mode
      refinement then passed its 148-test routing/inference set.
- [x] **E12 measurement boundary ratified. ✅ 2026-08-07** The operator applied
      `ratify_and_apply_mixed_role_split_v3.py` at `2026-08-07T12:32:51.554623Z`. Canonical state now
      names `task_rate_4d_v3_mixed_role_split`, `resource_lanes_v3_mixed_role_split`, and
      `model_judge_tail_v4_gpu_lifecycle_quiescence`; the receipt records `autopilot_started=false`.
- [x] **Validate serving and attempt the E12 baseline under explicit inference permission. ✅ 2026-08-07**
      Primary/auxiliary split placement was proven live. The canonical 100-question run then failed
      closed: one roughly 175K-token prompt was learned-routed through frontdoor to worker_general
      half1, timed out after 1,515 s, and left llama slot 0 prefilling after client failure. Both
      lifecycle drain checks rejected the run; reliability was 0.79 and no candidate was written.
      The exact orphan was removed by recycling only server `:8182`; all lifecycle counts returned to
      zero. AutoPilot remained stopped.
- [x] **Ratify E13 long-context routing boundary and attempt the canonical baseline. ✅ 2026-08-08**
      The operator applied `ratify_and_apply_long_context_guard_v4.py`; the era ledger was sealed at
      orchestrator commit `3824536e`. A 22K-character one-token smoke routed and dispatched directly to
      `ingest_long_context :8085`, with truthful `prompt_len=22194` versus the retained 8,028-character
      preview. The canonical 100-question attempt `evaltower-T1-1786169959693-b051ae9b-100q` then exposed
      a second execution-layer bypass: `try_cheap_first` treated ingest as an expensive specialist and sent
      the 637,310-character prompt to `worker_general :8182` before ingest could run. The collector was
      stopped in its pre-model-scoring drain, no candidate was written, and only the exact unresponsive
      `:8182` PID was recycled. Lifecycle and serving slots returned to zero; AutoPilot remained stopped.
- [x] **Ratify E14 end-to-end long-context capacity enforcement and attempt its baseline. ✅ 2026-08-08**
      The operator applied `ratify_and_apply_long_context_capacity_v5.py`. Iterative unratified diagnostics
      then exposed and closed error-sentinel formalization, fixed 90-second placement budgets, the API's
      stale 1,800-second timeout ceiling, strict zero-error admission, and giant-request placement. E14 was
      used only as the canonical preimage; no defective diagnostic was promoted.
- [x] **Apply the consolidated E15 v7 physical-cohort boundary and clean baseline. ✅ 2026-08-08** Orchestrator commits
      `498675be` and `d08bc9cf` make full and split CPU placements share one client-side physical exclusion
      lane, retain same-cohort native batching, and stage a human-only combined ratifier. Live telemetry
      proved both split halves released before the full q0–q3 giant lease acquired. Diagnostic
      `evaltower-T1-1786200440931-fea99b27-100q` completed 100/100 with reliability `1.0`, zero scorer,
      transport, drain, overflow, or orphan errors, four-way admission, quality `1.5`, wall time
      `2128.0008s`, and `169.1729` questions/hour. Immutable evidence SHA-256 is
      `e7e78849e37a16641711c9d6d6a0a8dff99cf406f6285ab3f21f99bf43cb86d9`. The operator applied the
      consolidated ratifier at `2026-08-08T14:47:08.081912Z`; receipt
      `ratify_e15_physical_cohort_v7_20260808.json` records `ratified_and_applied` and
      `autopilot_started=false`. Candidate and backup hashes were independently rechecked, and the E15
      era ledger was sealed at orchestrator commit `047837d8`.
- [x] **Restart AutoPilot on the ratified E15 boundary. ✅ 2026-08-08** Strict readiness initially
      exposed a tooling-contract mismatch: E15 wrote bootstrap status
      `baseline_admitted_frontier_pending`, while preflight accepted only `pending`. Orchestrator
      `89cf79c2` recognizes both equivalent pending states; 59 focused tests and Ruff passed, and strict
      restart readiness then reported `restart_ready=true` with archive authority `match`. Stale pre-E15
      trial 1473 had no journal result, so the existing crash-recovery path recorded an
      `autopilot_killed_mid_trial` tombstone and advanced to 1474. The operator-authorized supervised
      daemon started at `2026-08-08T17:43:46Z` with a 3,000-trial budget. Trial 1474 entered four-way T1
      evaluation; coupled telemetry certified concurrent complementary-half placement with no overflow.
- [x] **Make the optimization brief survive live API reloads. ✅ 2026-08-09** Orchestrator `517feccf`
      replaces the permanent red abort state with bounded exponential retry, last-good retention, a
      panel-specific 15-second cold-fetch budget, and one-minute refresh. Server synthesis moves off the
      API event loop and uses a 30-second reconnect cache with stale-cache provenance. Validation passed
      206 focused tests plus Ruff. The HTML fix became available without disrupting active trial 1499;
      the backend cache activates on the next ordinary API reload.
- [x] **Make Pareto and GEPA warnings describe the evidence actually on screen. ✅ 2026-08-09**
      Orchestrator `38f42470` makes current-era Pareto reconstruction follow the state-declared active
      objective (`task_rate_4d_v7_physical_cohort_exclusion`) instead of silently defaulting to legacy
      request t/s. W3 is now a neutral historical objective comparison rather than a pending flip warning;
      all-era request-t/s coordinates are explicitly a non-decision-grade historical comparator. The GEPA
      no-op caveat remains canonical but is rendered only when a visible trajectory row overlaps its
      2026-06-04 → 2026-07-25 window. Validation passed 216 focused dashboard/core tests, JavaScript parse,
      Ruff lint, and repository gates. API-only deployment launched commit `38f42470`; AutoPilot was not
      stopped or restarted.
- [x] **Scrub uncertified task-rate telemetry from the all-era Pareto view. ✅ 2026-08-09**
      Orchestrator `3b5ac37e` removes the invalid fallback that reconstructed questions/hour from legacy
      request-speed fields. Only rows stamped with a certified task-rate objective policy and accepted by
      the canonical sequential task-rate builder retain task-rate/goodput telemetry; legacy, unstamped, and
      malformed rows remain visible on their honest historical axes but carry a null task rate plus an
      explicit evidence status. Live verification retained 21 certified points at 38.45–228.94 q/h and
      suppressed 908 uncertified points, including the trial-1302 scaling outlier. Validation passed 217
      focused tests, dashboard JavaScript parsing, Ruff, and repository gates. The API-only deployment did
      not stop or restart AutoPilot.
- [x] **Disambiguate evaluation lanes from decision-question difficulty in GEPA/Pareto. ✅ 2026-08-09**
      Orchestrator `9e7e5226` adds a separate `decision_question_mix` contract to Pareto points and
      GEPA trajectory rows while retaining `eval_tier` as the outer lane. Summaries, legends, rows, and
      tooltips now say `lane T1/T2/T3`; current mixed-core trials additionally show the ratified
      `D1/D2/D3 17/17/16` target, scored/target count, mix policy, core id, and rotation. The planner can
      select T2/T3 `deep_eval`, and the higher-tier probe guard can force stale/empty T2/T3 coverage,
      while T1 remains the canonical deployment frontier. Validation passed 202 focused tests, Ruff,
      seven JavaScript-block parses, and repository gates. Trial 1502 was allowed to seal, AutoPilot was
      paused only at the boundary for an API-only reload, then resumed without an AutoPilot or model-server
      restart; live payloads report trial 1502 as outer lane T1 with equal-thirds target and 42/50 scored.
- [x] **Implement staged T1/T2/T3 promotion with exact transactional rollback. ✅ 2026-08-09**
      Orchestrator `3f62f712` adds `staged-multitier-v1`: every candidate must pass a T1 screen,
      matched T2 and T3 validation, and a fresh T1 promotion confirmation. Higher-tier regression
      vetoes; higher-tier improvement only tiebreaks; same-tier baselines are mandatory. Candidate
      runtime preimages now preserve absent env variables and structural flags, rejection restores the
      runtime config plus `production_best` routing intelligence, and acceptance checkpoints only after
      the WAL in-flight marker clears. Startup fails closed until a human-ratified policy and matched
      three-tier baseline bundle exist. The dashboard exposes the staged sequence and the new collector
      seals each tier independently against source, state, config, terminal-result, and episodic semantic
      integrity. Focused staged/config/sequential tests passed 110/110; dashboard 75/75; decision 7/7;
      collector 3/3; wiring 5/5.
- [x] **Repair episodic reseed throughput without weakening atomicity. ✅ 2026-08-09** Orchestrator
      `83c8777a` and `f3b262b8` replace the maintenance tool's accidental serial embedding path with
      batched, deterministic round-robin work over all six BGE servers. Reseed tests passed 15/15 and a
      representative 24-row smoke completed in 1.27 seconds. The live store remains untouched until the
      replacement DB/index/id-map set is complete and passes the existing swap checks.
- [x] **Finish the staged-policy evidence bundle and one consolidated ratifier. ✅ 2026-08-10** The atomic semantic
      rebuild is complete; recover interrupted non-mutating deep-eval trial 1505 append-only; deploy only
      the dashboard/API code with an API-only reload; collect
      immutable incumbent baselines T1=100, T2=500, T3=160; then produce one human-only ratifier that
      applies the policy/bundle and writes a clean `production_best` checkpoint. Orchestrator `545af011`
      makes collector preflight fail closed until `in_flight_trial` is cleared (5/5 focused tests).
      AutoPilot stayed stopped throughout. Final artifacts are T1 SHA `2293f55a…`, T2 SHA `8d18534b…`,
      and T3 SHA `012f2d99…`; orchestrator `8e147213` adds the atomic ratifier and focused tests.
      `--prevalidate` performs no writes and passes. The operator applied the consolidated ratifier;
      receipt `ratify_multitier_baseline_v10_20260810.json` records `ratified_and_applied`, and AutoPilot
      remains stopped pending separate restart permission.
- [x] **Apply the final consolidated v10 multi-tier ratifier. ✅ 2026-08-10** The operator ran
      `scripts/autopilot/operator_candidates/ratify_and_apply_multitier_baseline_v10.py`. It atomically
      wrote the E16 eras, T1/T2/T3 baseline bundle, staged-promotion policy, and verified
      `production_best` checkpoint while leaving AutoPilot and all model servers stopped. The checkpoint
      SHA-256 is `c60364f1295a931a4b4e806d4dffd2138696537f49b15a3a6881c50737c02b19`.
- [x] **Complete and certify the 63,786-row episodic semantic rebuild. ✅ 2026-08-09** Orchestrator
      `43323891` supports an explicit maintenance-only embedder fleet. Six temporary processes exposed
      96 slots with 16 compute threads each across all physical cores; the measured 96-row smoke reached
      151.8 rows/s. Atomic run `20260809T160329Z` published 63,786/63,786 vectors with desync 0 and zero
      bad pointers. The independent semantic gate passed with 0/60 below 0.9, mean cosine 0.9999, median
      1.0000, and minimum 0.9924. Temporary ports 18090–18095 were then shut down and verified absent.
- [ ] **AP-50 — Turn “what optimizes the orchestrator” into a decision cockpit.** Default to the current
      measurement era and distinguish proposed, executed, valid, kept, promoted, and currently-live
      states; “applied” alone is operationally ambiguous. Add current trial/intervention/falsifier,
      incumbent-vs-candidate objective deltas with n/uncertainty/replication, an experiment funnel with
      rejection reasons, and a live lever scoreboard sourced from journal/study evidence rather than the
      periodically generated digest. Retain the provenance graph as a drill-down, but lay it out
      left-to-right as hypothesis → experiment → evidence → verdict → runtime state, with era/status
      filters and explicit edge semantics.
- [ ] **AP-48 — Add backlog-aware adaptive full/split admission after the E13 burst baseline.** Treat
      E13's guarded split policy for router-owned EvalTower traffic as the conservative burst anchor,
      not the final general scheduler. Build an admission policy that uses arrival pressure, physical
      frontdoor/worker queue depth, and calibrated probability of a frontdoor-terminal answer to choose
      `homogeneous_native_batch` versus `mixed_role_split` at request boundaries. It may schedule a full
      instance only while downstream pressure is absent; when pressure appears, drain rather than preempt
      the active full request and switch subsequent admissions to complementary halves. Evaluate direct-only,
      mixed-pipeline, and randomly paced arrivals separately. Any live adoption opens a new execution/speed
      era so E13 questions/hour is never mixed with the adaptive denominator.
- [ ] **AP-49 — Explore true live-decode checkpoint/resume only on a versioned experimental kernel.** The
      production llama-server defers slot save/restore while `slot->is_processing()`, so current migration is
      an idle-session KV handoff and cannot relocate an active decode. Prototype a token-boundary pause →
      checkpoint → restore → resume protocol that preserves KV plus sampler/RNG, grammar/tool-parser,
      speculative-decoder, request/stream ownership, cancellation, and exact output continuity. Start from
      fresh frozen production into `llama.cpp-experimental`; do not modify the production kernel. Require
      byte/token continuity tests, failure-atomic rollback, bounded pause/transfer cost, and a demonstrated
      advantage over request-boundary drain-and-switch before considering a new production version.

## 2026-08-05 — Research intake: least-commitment diagnostics and compression safety

_Via `/research-intake` Stage-4 (intake-991#record through intake-1002#record). The submitted weakness result is not
adopted as a selector: its original proof and empirical comparison are not decision-grade, and the later
results remain conditional on a declared representation and demand law. The tasks below adopt only the
verified diagnostic and validation patterns._

- [ ] **AP-WM-1 — Shadow-test loop-native least-commitment diagnostics; do not add a live selector.**
  Build one immutable offline comparison over archived proposals that share a common candidate frame and
  predeclared empirical demand weights. Every row must declare vocabulary provenance (regimes, surfaces,
  outcomes, contradictions), excluded alternatives, abstraction-construction cost, and either a canonical
  representation or semantics-preserving recoding fixtures. Compare explicit unsupported-scope width,
  demand-weighted compatible-future mass, and the K-rho representation-aliasing diagnostic against current
  information gain, novelty, and a raw-impurity/simple weighted-minority baseline. Score against held-out
  regime transfer and falsifier resolution using matched one-factor interventions; report per-regime and
  per-surface Kendall direction, conditional predictive value, mean/90th/worst sign error, effective-pair
  count/noise floor, and recoding stability. If recoding changes the ordering or a new diagnostic adds no
  stable decision signal beyond the simpler baseline, retain the simpler baseline. No result may affect
  fitness, archive admission, promotion, or authority without a separately approved decision-grade protocol.
  - [x] **AP-WM-1a — Implement and regression-test the immutable offline protocol. ✅ 2026-08-05**
    `epyc-inference-research/scripts/kernel_rnd/autokernel/offline_least_commitment.py` validates one common
    candidate/representation/demand frame, completed matched one-factor interventions, explicit metric
    directions, recoding coverage, and observe-only authority; it emits the full required report and has no
    live mutation API. A deterministic matched fixture proves the report and conservative simpler-baseline
    fallback.
  - [ ] **AP-WM-1b — Execute over AutoKernel's first real matched archive, observe-only.** Consume the
    deterministic AK-WM-2a output only after clean instrument provenance, current v9 controls, the CPU IQK
    proposal, proposal-v3 frame receipts, and completed matched interventions exist. Synthetic regression
    rows are protocol tests, never decision evidence; this path gains no live selector authority.

- [x] **AP-29d — Make strategy compression commitment-nonincreasing before wiring distillation. ✅ 2026-08-05** For both
  StructuralLab MDL conventions and KnowledgeDistiller patterns, retain source member/evidence ids and
  qualifiers; derive planner-binding applicability/binding metadata from the intersection of supporting
  members; keep unmatched claims advisory or delta-only; and fail closed to advisory-only when supporting
  trials disagree or harmless paraphrase/recoding changes the induced binding. Add a regression fixture in
  which the longest cluster member overgeneralizes one supporting trial and prove that it cannot become a
  global/live convention. This extends rather than replaces AP-29's episodic-only control and grouped/batched
  consolidation gate. Landed as orchestrator commit `b6a6e5e5`: StructuralLab and
  KnowledgeDistiller now retain source/evidence/qualifier provenance, derive applicability and
  planner bindings only from unanimous supporting-member intersections, and fail closed to
  advisory-only on outcome, binding, qualifier, or recoding disagreement. Regression fixtures
  prove that a longest-member overgeneralizer cannot become a live convention.

## 2026-08-07 — reset-free trajectory refinement, proposal-only (intake-1016/1020)

- [ ] **AP-CH-1 — Add a default-off adapter that turns a bounded recent trajectory window into typed
  prompt/subagent/skill/memory candidates.** The adapter may diagnose and propose only. Validate every
  payload against a local schema, cap repeated equivalent proposals, and emit ordinary candidate
  envelopes with source trajectory ids, proposer identity, component kind, before/after content, and
  claimed failure signature. It has no authority to write live prompts, execute generated Python,
  mutate skills/memory, select itself, or keep a change. Existing held-out evaluation, checkpoints,
  transactional keep/revert, privilege policy, and promotion authority remain outside the proposer.

- [ ] **AP-CH-2 — Compare reset-free and episodic proposal generation at equal budget.** Use the same
  completed trajectories, proposer model, token/tool budget, candidate schema, evaluator, and held-out
  task set. Report valid-candidate rate, duplicate/oscillation rate, held-out lift, regressions, cost,
  and wall time. The upstream 25/100-step cadence is not a default; cadence is a declared experimental
  variable. No live AutoPilot resume or acceptance-policy change follows from this task.

## 2026-08-09 — staged multi-tier T2 poison audit checkpoint

AutoPilot remains stopped. The accepted immutable T1 artifact is
`/mnt/raid0/llm/epyc-root/artifacts/operator/multitier_incumbent_t1_20260809.json`, SHA-256
`a867dfd5a45c9f0822b41d0d9ce2b9b474458d5e50c0f0ba3439647faa2e10c3`.

- [x] **AP-MT-1 — Audit the interrupted T2 batch and quarantine poisoned evidence. ✅ 2026-08-09**
  Batch `evaltower-T2-1786306535911-d4ab132c-500q` was interrupted after audit. Its sidecar has 224
  scored rows. Exactly two rows selected non-serving `plan_review` routes, at ordinals 229 and 233.
  Therefore 222 rows are retainable and 278 rows require rerun. API telemetry completed 245 requests,
  but 21 late completions have no collector rows. The current T2 top-five set contained `plan_review` 13
  times and selected it twice. This batch is not a clean baseline and cannot support ratification.
- [x] **AP-MT-2 — Repair and regression-test `QScorer.score_external_result` namespace assignment. ✅ 2026-08-09**
  Orchestrator `26c5220c` takes the namespace as an explicit non-empty argument. It no longer hard-codes
  `routing` for `plan_review*` records. Focused routing-memory coverage passed 309 tests.
- [x] **AP-MT-3 — Validate HybridRouter role parsing against live serving roles. ✅ 2026-08-09**
  Orchestrator `26c5220c` validates every stored route against the realized live-stack role set before
  learned selection. Non-serving `plan_review` actions are excluded from T1/T2/T3 routing candidates.
- [x] **AP-MT-4 — Correct or quarantine the legacy episodic action labels before routing learning. ✅ 2026-08-09**
  The audit initially identified 682 `plan_review*` rows labelled `action_type=routing`. The narrow,
  backed-up repair updated 690 misnamespaced rows in total and re-embedded three parallel hash-fallback
  vectors. Receipt `artifacts/operator/episodic_routing_poison_repair_20260809.json` reports zero
  remaining namespace updates or fallback vectors and consistent `63833` SQLite/FAISS/id-map rows.
  Its status is `applied_for_validation_unratified`; this repairs contamination, not baseline evidence.
- [x] **AP-MT-5 — Reconstruct a fully clean T2 baseline after the fixes. ✅ 2026-08-10** Retain only the 222 verified
  clean rows, rerun the required 278 rows, reconcile the 21 late-completion collector gap, and require a
  clean 500-row terminal artifact with a post-repair source identity. Collect the T3 baseline only after
  this gate. Prepare a consolidated ratifier only after clean T1/T2/T3 evidence and a bug-free
  orchestrator are verified. Completed evidence is T2 `500/500`, quality `1.356`, reliability `1.000`,
  and T3 `160/160`, quality `1.275`, reliability `1.000`; both have zero error rows. The v10 recodes are
  deterministic and attest that answers, scores, timing, and routing did not change.
