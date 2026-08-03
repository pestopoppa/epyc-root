# AutoPilot: Continuous Recursive Optimization

**Resume-precondition — 2026-07-17 (non-inference session diagnosis)**: the ~28h stop on 2026-07-16 was a **DELIBERATE `SIGTERM`** to free the machine for v7 kernel work (`autopilot.log` `Shutdown requested (signal 15)` → `Controller failed (rc=143)`; `agent_audit.log` logs *"Audit experimental v7 kernel worktree … while AutoPilot remains stopped"* seconds later). It is **NOT** a `consecutive_failures` self-halt — `consecutive_failures=2 < safety_gate.MAX_CONSECUTIVE_FAILURES=3` (`safety_gate.py:107`); the persisted `_dispatch_deficiency='consecutive_failures'` marker is stale + self-clearing (`autopilot.py:8687` unconditional pop on `resume`). **No wedge to clear.** Before resuming:
- [ ] Bring the `:8000` stack up + verify HEALTHY first (a resume against a dead stack fails every dispatch). Use `orchestrator_stack.py`; ensure the GLM-5.2 probe on port 19402 doesn't contend with the stack's servers.
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

**Dispatch-latency / idle-visibility policy (2026-05-26 hardening)**: the dashboard CPU-region table is a placement-readiness view, not proof that autopilot is alive or actively dispatching. `phase_status.py` now writes `/mnt/raid0/llm/tmp/autopilot_phase.json{,l}` so the dashboard can show whether the loop is stopped, paused, in health backoff, building the planner prompt, invoking the planner, dispatching, journaling, checkpointing, or scheduling async artifacts. Auxiliary plot/digest work may run asynchronously (`AUTOPILOT_ASYNC_AUX=1`, `AUTOPILOT_ASYNC_WORKERS=2`) after durable journal/state mutation; checkpointing remains synchronous. Seeder role evals may fan out with `AUTOPILOT_SEED_ROLE_CONCURRENCY=auto`, but only in contention-matrix-safe background waves with same-port and heavy-port guards. The high-blast-radius request caller contracts remain unchanged; request-level `trial_id`/`batch_id` stamping through `call_orchestrator_forced` is a separate accepted-risk follow-up, not part of this hardening.

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

**Source**: SIA (intake-793, arxiv 2605.27276), ShinkaEvolve (intake-779), SkillRL (intake-092)

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
- [ ] **Vision panel reported `fixed` with zero panel changes.** `grep -ci image
      src/api/routes/dashboard.html` -> **0**. Capture works and the snapshot carries it; the
      renderer discards it. Also a capture hole: `vision_stage.py:76` treats `request.files` as
      vision input but records nothing for that form.
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
- [ ] **`binding_router` is a parameter nobody passes, gating a whole feature.** `src/api/state.py:97`
      declares `binding_router: Any | None = None`, never assigned anywhere;
      `chat_routing.py:230`'s `if binding_router is not None:` guards the entire override block;
      `_classify_and_route_proactive` has zero callers. Flipping `features().binding_routing` does
      nothing because the `BindingRouter` is never constructed.
- [ ] **Ten fully-built, fully-tested, zero-production-importer modules** (1-3 test importers, 0
      production importers), incl. `src/mutation_ledger.py`, whose docstring asserts "the autopilot
      accept-path consults the ledger" — it does not.
- [ ] **`contention_nway_restricted_count` stops one layer short of the operator.** Reaches
      `metrics_snapshot()` (`contention_gate.py:453`) but appears 0 times in `dashboard.html`.

### Never attempted

- [ ] `config/stack_templates/default.yaml` is 10 validation errors stale — `start --stack-profile
      default` returns 1 today.
- [ ] Registry declares port **8083 twice**: `coder_escalation` keeps its own row (slots 1) while also
      appearing in `architect_general.shared_with` (slots 8). Blocks the WP-12 fleet layer.
- [ ] `onnxruntime` is used at runtime by `src/retrieval/cross_encoder.py`, declared nowhere in
      `[project]` dependencies, and is not installed — **cross-encoder reranking is silently off in
      production**.
- [ ] The ~77-test retired-topology failure bucket.
- [ ] `MEASUREMENT.md:148-158` still states the durability checker "fails on any citation resolving
      outside the repository" — now false after the retarget. Human-amendment-only; no owner assigned.

### Operational hazards found this session

- [ ] **`autopilot pause` has no interlock against an in-flight config-apply.** `structural_experiment`
      trials restart the API to apply flag changes; pausing between the stop and the start leaves the
      stack with **no API**, and AutoPilot then retries `Connection refused` forever rather than
      failing loudly. Caused a live outage 2026-08-03. Nothing in the preflight or the gate detects it.
- [ ] **An eval scores an unreachable API as WRONG, not as infra-failed.** A T1 calibration ran
      70/100 questions at `0% correct` purely because the API was down; only `--dry-run` prevented a
      0.000 baseline reaching production state. Reliability should have collapsed the run long before
      70 questions.
- [ ] **`runtime_flags` drift checker grades declared-vs-live but never wired-vs-unwired.** It reports
      `semantic_classifiers` as blocking drift; that flag has **zero consumer modules** outside
      `features.py`. The tool embodies the defect class it was built to detect.

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

- [ ] **An HTTP 400 / unreachable endpoint is scored as WRONG, not as infra-failed.** This is the root
      cause of the 2026-08-03 incident where a T1 calibration ran 70/100 questions at `0% correct`
      purely because the API was down. It is also why an oversized prompt hitting a per-slot 400 would
      appear as a permanent, misattributed quality regression rather than a capacity problem. The
      reliability floor exists but did not collapse the run until far too late. Two failure modes, one
      cause: **absence is being scored as failure.**
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
