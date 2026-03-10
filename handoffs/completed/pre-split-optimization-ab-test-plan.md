# Pre-Split Optimization A/B Test Plan — Root Workload Infra

**Created**: 2026-02-21
**Archived**: 2026-03-04
**Status**: ARCHIVED — partially executed, no longer executable in current form

> **Archival Note (2026-03-04):**
> - **Concrete outcome**: 10.8 model-tier routing validated as **KEEP** (-15.2% cost, 0% quality delta). This is the only optimization that completed full live A/B testing.
> - **Remaining 0.x/10.7.x optimizations** were never A/B tested against live models.
> - **Not executable**: Scripts referenced below (in `scripts/root_workload/ab/`) were created in the pre-split monorepo and moved to `epyc-inference-research` during the repo split. Paths in this handoff are broken.
> - **Reference value**: The experiment design (Section 10), decision function (Section 10.6), and per-optimization flag map (Section 11) remain useful as methodology references if these optimizations are revisited.

**Primary Reference**: `handoffs/active/repo-split-strategy.md` (Section 10)

---

## 1. Objective

Determine which pre-repo-split root workload optimizations should be **kept**, **revised**, or **dropped** based on measured impact (cost, quality, throughput, and operator burden).

---

## 2. Scope

In scope: Section 10 optimizations only (Claude/Codex governance-side), including:
- Phase 0.1 through 0.6 controls
- Section 10.7.1 through 10.7.10 optimization patterns
- Both execution environments:
  - `codex`
  - `claude-code`

Out of scope:
- Orchestrator runtime behavior
- Model serving/routing internals
- Inference kernel/perf changes

---

## 3. Experiment Design Standard

For every optimization:
1. `A` (control): behavior disabled (or current baseline behavior).
2. `B` (treatment): optimization enabled behind explicit config flag.
3. Run on the same workload set and similar time windows in both environments:
   - `codex` A vs B
   - `claude-code` A vs B
4. Compare:
   - `quality_pass_rate`
   - `cost_per_task` (or normalized cost ratio)
   - `p95_task_latency`
   - `manual_intervention_rate`
5. Decision:
   - **KEEP**: quality non-inferior and cost/latency improve or remain neutral in both environments.
   - **REVISE**: quality non-inferior but cost/latency regress > threshold.
   - **DROP**: quality regression beyond threshold or operational instability.

Cross-platform consistency gate:
- Compute deltas separately for `codex` and `claude-code`.
- Flag optimization for **REVISE** if one platform improves and the other regresses materially.

Default non-inferiority threshold:
- Quality drop tolerated at most: `-1.0%` absolute.

Default cost target:
- Cost improvement target: `>= 8%` versus control, unless optimization is quality/safety-oriented.

---

## 4. Global Prerequisites

1. Add feature flags for each optimization in `.claude/agent-cost-policy.json` and/or hook config.
2. Enforce telemetry schema in `.session-stats` and run logs.
3. Define fixed benchmark workload pack:
   - `read/search` tasks
   - `plan/synthesis` tasks
   - `implementation/fix` tasks
   - `long-input summarization/review` tasks
   - `resume-from-compaction` tasks
4. Freeze operator rubric for quality scoring before running tests.

---

## 5. Per-Optimization A/B Matrix

| ID | Optimization | A (Control) | B (Treatment) | Primary success criteria | Keep/Drop rule |
|---|---|---|---|---|---|
| 0.1 | Cost policy contracts | No enforced contract fields | Enforced `agent-cost-policy.json` contract + schema checks | Fewer policy drift incidents; no quality loss | Keep if drift incidents drop and quality non-inferior |
| 0.2 | Context budget enforcement | No hard budget discipline | Index-style context + facts cap + on-demand large artifacts | Lower prompt payload size and stable quality | Drop if quality falls >1% |
| 0.3 | Budget-aware subagent governance | Unbounded/default subagent behavior | Tier defaults + max turns + budget injection | Lower escalation and spawn cost | Revise if blocked useful work >5% |
| 0.4 | Hook governance/drift control | Existing mixed behavior | Hard-block protected files + fail-open non-critical + dedup | Fewer rework loops/config drift | Drop if false blocks materially slow throughput |
| 0.5 | Nightshift budget optimization | Current schedule | Priority-tuned nightshift + reserve floor + budget tracking | Lower overnight spend with no daytime starvation | Keep if daytime budget incidents do not increase |
| 0.6 | Split compatibility shim | Hardcoded path assumptions | `REPOS_DIR` + alias map + dual-layout validation | Same workflow success in mono + split layouts | Keep only if both layouts pass |
| 10.7.1 | Correctness-gated escalation | Escalate by looser heuristics | Escalate only after failed/low-confidence lower-tier result | Reduced expensive escalations; no quality drop | Drop if quality gate blocks needed escalations |
| 10.7.2 | THINK_HARDER one-shot | Immediate tier jump | One bounded same-tier retry before escalation | Higher escalation avoidance without net cost increase | Revise token multiplier if cost regresses |
| 10.7.3 | Routing override stack | Non-deterministic/implicit precedence | Deterministic precedence (session > user > task > default) | 100% attributable routing decisions | Keep if conflict ambiguity reaches zero |
| 10.7.4 | Admission + budget diagnostics | No strict burst control | Concurrency caps + budget envelopes | Fewer cost spikes and runaway loops | Revise if latency spikes from over-throttling |
| 10.7.5 | Structured context compaction | Free-form bulky structured artifacts | Compact schema blocks for repetitive artifacts | Payload size reduction on target artifacts | Drop if readability harms quality outcomes |
| 10.7.6 | Prompt canonicalization | Ad-hoc prompt scaffolding | Canonical templates with semantic slots | Lower prefill/context overhead in repeated workflows | Keep if repeated-run cost improves |
| 10.7.7 | Two-stage summarize/review | Direct handling at higher tier | Stage A cheap summary + Stage B mid-tier verification | Lower long-input handling cost with no quality loss | Drop if contradiction miss rate increases |
| 10.7.8 | Delta injection on resume | Full replay default | Delta-first resume with fallback trigger | Lower resume context size with no context loss | Drop if resume error rate increases |
| 10.7.9 | Failure taxonomy action map | Generic retry/escalate behavior | Deterministic category-to-action map | Fewer unnecessary escalations on non-complex failures | Keep if escalation efficiency improves |
| 10.7.10 | Role-normalized anomaly detection | Raw token totals only | Normalized ratio vs task-class baseline | Better anomaly detection precision | Keep if top regressions are more actionable |
| 10.8 | Model-tier routing | All tasks use default model (Opus) | Route tasks to Haiku/Sonnet/Opus by task class + difficulty tier | 50-80% cost reduction with quality non-inferior on easy/medium tasks | Drop if quality regresses >1% on any tier; Revise routing table if medium-tier quality drops |

---

## 6. Rollout Sequence

1. **Wave 1 (Foundational controls)**: `0.1`, `0.2`, `0.3`, `0.4`.
2. **Wave 2 (Split and overnight ops)**: `0.5`, `0.6`.
3. **Wave 3 (Optimization primitives)**: `10.7.1` through `10.7.5`.
4. **Wave 4 (Advanced workflow controls)**: `10.7.6` through `10.7.10`.
5. **Wave 5 (Model-tier routing)**: `10.8` — run after Wave 3/4 baselines are stable; interaction effects with workflow optimizations are significant.

Rule: run one optimization per A/B cycle first; run interaction tests only after single-change effects are stable.

---

## 7. Minimum Experiment Size

- Minimum per optimization per environment: `>= 100` representative tasks total (`50` A, `50` B).
- Combined minimum across both environments: `>= 200` tasks.
- For low-frequency flows (nightshift, resume): run for `>= 7` days before decision.
- Re-run any borderline result once to rule out workload skew.

---

## 8. Decision Log Contract

Create one decision record per optimization in:
- `docs/root-workload/decisions/<optimization-id>.md`

Record must include:
1. Experiment window and workload pack version
2. Environment split (`codex`, `claude-code`)
3. Control/treatment config hashes
4. Metric deltas per environment and combined summary
5. Keep/revise/drop decision
6. If revised/dropped: exact failure mode and next action

---

## 9. Exit Criteria

This handoff is complete when:
1. Every optimization listed above has an A/B result.
2. Every result has a decision record.
3. Final retained set is reflected in:
   - `.claude/agent-cost-policy.json`
   - `docs/root-workload/*.md`
   - `handoffs/active/repo-split-strategy.md` (Section 10 status update)

---

## 10. Execution Playbook (Normative)

This section is the operational contract. Agents executing this handoff must follow this flow and artifact layout.

### 10.1 Canonical Artifact Layout

All outputs for this handoff must live under:

`benchmarks/root_workload/ab/`

Per optimization:

`benchmarks/root_workload/ab/<optimization-id>/<run-id>/`

Required files per run:
- `manifest.json` (workload manifest + seed + environment + A/B config hashes)
- `raw_events.ndjson` (task-level telemetry events)
- `summary_codex.json`
- `summary_claude_code.json`
- `summary_combined.json`
- `decision.md` (keep/revise/drop rationale)

### 10.2 Required Runner Interfaces

If absent, create these first:

- `scripts/root_workload/ab/generate_manifest.py`
- `scripts/root_workload/ab/run_arm.py`
- `scripts/root_workload/ab/aggregate.py`
- `scripts/root_workload/ab/decide.py`
- `scripts/root_workload/ab/run_full_plan.py`
- `scripts/root_workload/ab/build_quality_review_queue.py`

CLI contracts:

```text
python3 scripts/root_workload/ab/generate_manifest.py \
  --optimization-id 10.7.2 \
  --seed 42 \
  --tasks-per-arm 50 \
  --out benchmarks/root_workload/ab/10.7.2/<run-id>/manifest.json

python3 scripts/root_workload/ab/run_arm.py \
  --manifest .../manifest.json \
  --environment codex \
  --arm A \
  --out .../raw_events.ndjson

python3 scripts/root_workload/ab/run_arm.py \
  --manifest .../manifest.json \
  --environment claude-code \
  --arm B \
  --out .../raw_events.ndjson

python3 scripts/root_workload/ab/aggregate.py \
  --events .../raw_events.ndjson \
  --out-dir benchmarks/root_workload/ab/10.7.2/<run-id>/

python3 scripts/root_workload/ab/decide.py \
  --summary-codex .../summary_codex.json \
  --summary-claude-code .../summary_claude_code.json \
  --summary-combined .../summary_combined.json \
  --out .../decision.md

# one-command full matrix run (all optimization IDs)
python3 scripts/root_workload/ab/run_full_plan.py \
  --tasks-per-arm 50 \
  --seed 42 \
  --workload-pack benchmarks/root_workload/workload_pack_v1.json

# one-command full matrix run using debug-suite hard battery (recommended)
python3 scripts/root_workload/ab/build_coding_hard_pack.py
python3 scripts/root_workload/ab/run_full_plan.py \
  --tasks-per-arm 50 \
  --seed 42 \
  --workload-pack benchmarks/root_workload/workload_pack_curated_debug_hard50_v1.json

# anti-overfitting variant: random-stratified debug-suite hard100 battery
python3 scripts/root_workload/ab/build_coding_hard_pack.py \
  --size 100 \
  --selection-mode random_stratified \
  --seed 42
python3 scripts/root_workload/ab/run_full_plan.py \
  --tasks-per-arm 100 \
  --seed 42 \
  --workload-pack benchmarks/root_workload/workload_pack_curated_debug_hard100_v1.json

# after full run, build one final quality-review queue
python3 scripts/root_workload/ab/build_quality_review_queue.py \
  --index benchmarks/root_workload/ab/full_run_index_<timestamp>.json \
  --out benchmarks/root_workload/ab/quality_review_queue_<timestamp>.md
```

### 10.3 Workload Pack Contract

Workload source file:
- `benchmarks/root_workload/workload_pack_v1.json`
- `benchmarks/root_workload/workload_pack_curated_debug_hard50_v1.json` (debug-suite-only hard battery; recommended)
- `benchmarks/root_workload/workload_pack_curated_debug_hard100_v1.json` (debug-suite-only random-stratified hard battery; anti-overfitting)

Implemented scaffold:
- `benchmarks/root_workload/workload_pack_v1.json` exists as starter pack (`v1-starter`).
- `benchmarks/root_workload/workload_pack_curated_debug_hard50_v1.json` exists (coding-heavy, debug-suite-only hard battery; 50 tasks).
- `benchmarks/root_workload/workload_pack_curated_debug_hard100_v1.json` exists (coding-heavy, debug-suite-only random-stratified battery; 100 tasks).

Each task entry must include:
- `task_id`
- `task_class` (`read_search`, `planning_synthesis`, `implementation_fix`, `long_input`, `resume`)
- `input_payload`
- `quality_rubric_id`
- `expected_artifact_type`

Sampling rules:
- fixed random seed per run
- stratified sample across task classes
- identical sampled task IDs across `A` and `B`
- identical sampled task IDs across `codex` and `claude-code`

### 10.4 Arm Configuration Rules

For each optimization test:
- `A` sets the optimization flag(s) OFF.
- `B` sets the same flag(s) ON.
- No additional behavior changes are permitted.

Config snapshots:
- Persist full effective config for each arm:
  - `config_arm_a.json`
  - `config_arm_b.json`
- Include SHA-256 hashes in `manifest.json`.

### 10.5 Metrics Computation (Deterministic)

Per environment (`codex`, `claude-code`) compute:
- `quality_pass_rate = passed_tasks / total_tasks`
- `cost_per_task = total_cost / total_tasks`
- `p95_task_latency`
- `manual_intervention_rate = manual_interventions / total_tasks`

Cross-platform consistency:
- `delta_quality_env = B.quality_pass_rate - A.quality_pass_rate`
- `delta_cost_env = (B.cost_per_task - A.cost_per_task) / A.cost_per_task`
- `delta_latency_env = (B.p95_task_latency - A.p95_task_latency) / A.p95_task_latency`

Combined summary uses weighted average by task counts.

### 10.6 Decision Function (Deterministic)

Compute decision per environment, then combine:

1. If `delta_quality_env < -0.01` in either environment -> `DROP`.
2. Else if one environment improves and the other regresses materially:
   - material regression:
     - `delta_cost_env > +0.08`, or
     - `delta_latency_env > +0.10`, or
     - `manual_intervention_rate` increases by `> +0.03` absolute
   -> `REVISE`.
3. Else if both environments are non-inferior on quality and either:
   - both show cost improvement `>= 0.08`, or
   - one improves and the other is neutral (`|delta_cost_env| <= 0.02`)
   -> `KEEP`.
4. Otherwise -> `REVISE`.

### 10.7 Execution Steps Per Optimization

1. Pick optimization ID (example `10.7.2`).
2. Generate run ID: `<optimization-id>_<YYYYMMDD>_<HHMMSS>`.
3. Generate manifest (`tasks-per-arm=50`, fixed seed).
4. Execute 4 runs:
   - codex A
   - codex B
   - claude-code A
   - claude-code B
5. Aggregate metrics and generate summaries.
6. Run decision function.
7. Copy `decision.md` to:
   - `docs/root-workload/decisions/<optimization-id>.md`
8. Update status table in this handoff (Section 12).

### 10.8 Guardrails During Execution

- Do not run optimization interaction tests until single-optimization verdict is final.
- Do not modify workload pack mid-run.
- Do not change rubric definitions during an experiment window.
- Any aborted arm must be marked `invalid` and fully re-run.

### 10.9 Minimum Acceptance for “Executable”

This handoff is executable only if all are present:
- runner scripts in `scripts/root_workload/ab/`
- workload pack in `benchmarks/root_workload/workload_pack_v1.json`
- output summaries generated for at least one dry-run optimization
- deterministic decision script output matches Section 10.6 rules

Current state (2026-02-22):
- Scaffold scripts implemented.
- Dry-run verified end-to-end via:
  - `python3 scripts/root_workload/ab/run_full_plan.py --tasks-per-arm 6 --seed 7`
- Dry-run index generated:
  - `benchmarks/root_workload/ab/full_run_index_20260222_004020.json`
- Debug-suite hard50 full run completed:
  - `benchmarks/root_workload/ab/full_run_index_20260222_005711.json`
  - `benchmarks/root_workload/ab/quality_review_queue_20260222_005711.md`
- Debug-suite hard100 full run completed (random-stratified):
  - `benchmarks/root_workload/ab/full_run_index_20260222_013032.json`
  - `benchmarks/root_workload/ab/quality_review_queue_20260222_013032.md`
  - `benchmarks/root_workload/ab/quality_review_report_20260222_013032.md`

---

## 11. Optimization-to-Flag Map (Must Be Implemented)

| Optimization ID | Required flag key(s) (in `.claude/agent-cost-policy.json` unless noted) |
|---|---|
| 0.1 | `contracts.enforce_schema` |
| 0.2 | `context_budget.enable`, `context_budget.facts_line_cap`, `context_budget.on_demand_large_artifacts` |
| 0.3 | `routing.task_class_to_model_tier`, `subagent.max_turns`, `subagent.inject_budget_context` |
| 0.4 | `hooks.protected_files_blocklist` (plus `.claude/settings.json` hook wiring), `hooks.fail_open_non_critical`, `hooks.warning_dedup` |
| 0.5 | `nightshift.reserve_floor`, `nightshift.priority_profile`, `nightshift.budget_tracking` |
| 0.6 | `paths.repos_dir`, `paths.repo_alias_map`, `paths.enforce_no_hardcoded_children` |
| 10.7.1 | `escalation.correctness_gate_required`, `escalation.quality_guardrails` |
| 10.7.2 | `retry_policy.think_harder.enabled`, `retry_policy.think_harder.max_per_stage`, `retry_policy.think_harder.token_multiplier` |
| 10.7.3 | `routing.priority_order` |
| 10.7.4 | `admission.concurrency_limits`, `budget.thresholds` |
| 10.7.5 | `context_compaction.allowed_artifact_classes`, `context_compaction.enabled` |
| 10.7.6 | `prompt_canonicalization.enabled`, `prompt_canonicalization.template_ids` |
| 10.7.7 | `long_input.two_stage.enabled`, `long_input.stage_thresholds`, `long_input.escalation_conditions` |
| 10.7.8 | `resume.delta_injection_default`, `resume.full_replay_fallback_conditions` |
| 10.7.9 | `failure_action_map` |
| 10.7.10 | `cost_anomaly.normalized_ratio.enabled`, `cost_anomaly.thresholds` |
| 10.8 | `routing.model_tier.enabled`, `routing.model_tier.table` (task_class × tier → model), `routing.model_tier.aggression` (`conservative`/`moderate`/`aggressive`) |

---

## 12. Execution Status Table

| Optimization ID | Runner-ready | A/B complete (codex) | A/B complete (claude-code) | Decision | Decision record |
|---|---|---|---|---|---|
| 0.1 | yes (proxy) | no | no | pending | pending |
| 0.2 | yes (proxy) | no | no | pending | pending |
| 0.3 | yes (proxy) | no | no | pending | pending |
| 0.4 | yes (proxy) | no | no | pending | pending |
| 0.5 | yes (proxy) | no | no | pending | pending |
| 0.6 | yes (proxy) | no | no | pending | pending |
| 10.7.1 | yes (proxy) | no | no | pending | pending |
| 10.7.2 | yes (proxy) | no | no | pending | pending |
| 10.7.3 | yes (proxy) | no | no | pending | pending |
| 10.7.4 | yes (proxy) | no | no | pending | pending |
| 10.7.5 | yes (proxy) | no | no | pending | pending |
| 10.7.6 | yes (proxy) | no | no | pending | pending |
| 10.7.7 | yes (proxy) | no | no | pending | pending |
| 10.7.8 | yes (proxy) | no | no | pending | pending |
| 10.7.9 | yes (proxy) | no | no | pending | pending |
| 10.7.10 | yes (proxy) | no | no | pending | pending |
| 10.8 | yes (live) | n/a | yes (confirmed) | **KEEP** (-15.2% cost, 0% quality Δ) | `benchmarks/root_workload/ab_tuning_live/confirm_20260223_233317/result.json` |

---

## 13. Per-Agent Tuning Strategy (Codex vs Claude-Code)

Cross-environment pass/fail is still required for global defaults, but optimization tuning should be run
per agent first to avoid discarding environment-specific wins.

### 13.1 Why per-agent tuning

- Some candidates fail quality in only one environment.
- A single shared parameter set underfits one agent and overfits the other.
- Agent-specific profiles (`codex`, `claude-code`) allow selective adoption while preserving safety gates.

### 13.2 Deterministic tuner (implemented)

Script:
- `scripts/root_workload/ab/tune_deterministic.py`

Purpose:
- Deterministic search over optimization effect parameters using debug-suite-only workload packs.
- Hard quality constraint first (`delta_quality >= -0.01` per environment), then objective ranking.

Dependencies in harness:
- `scripts/root_workload/ab/run_arm.py` supports `--effect-overrides`.
- `scripts/root_workload/ab/run_full_plan.py` supports `--effect-overrides`.

### 13.3 Optuna migration (next step)

Grid search is useful for initial sanity checks, but interaction effects across many on/off optimization switches
and mixed parameter types should be explored with Optuna.

Implemented script:
- `scripts/root_workload/ab/tune_optuna.py`

Study design:
1. One study per environment:
   - `study_codex`
   - `study_claude_code`
2. Trial variables:
   - `enable_<optimization_id>` (bool)
   - conditional params for enabled optimizations (numeric/discrete)
3. Objective:
   - hard quality constraints per environment
   - optimize cost/latency/manual intervention with quality-aware weighting
4. Validation:
   - deterministic-core run first (debug suites)
   - deterministic resampling to avoid question-set overfitting:
     - `--resample-mode fixed` (same set every trial)
     - `--resample-mode trial_seeded` (default; seed + trial number)
     - `--resample-mode fold_cycle` (cycle across deterministic folds)
   - finalists re-evaluated with external quality labels

Output contract:
- `benchmarks/root_workload/ab_tuning/optuna_<timestamp>/study_*.json`
- top candidate profile files:
  - `.claude/agent-cost-policy.codex.optimized.json`
  - `.claude/agent-cost-policy.claude_code.optimized.json`

Smoke validation completed:
- `python3 scripts/root_workload/ab/tune_optuna.py --environment codex --trials 2 --tasks-per-arm 20 --seed 42 --resample-mode trial_seeded --workload-pack benchmarks/root_workload/workload_pack_curated_debug_hard100_v1.json --out-root /tmp/root_ab_tuning_smoke`

---

## 14. Live API Validation Status (Codex + Claude Code)

To validate simulator/tuner conclusions against real model calls, the following live runner was added:

- `scripts/root_workload/ab/run_live_sample.py`

Runner behavior:
- Calls live CLIs (`codex exec --json`, `claude -p --output-format json`)
- Uses deterministic debug-suite scoring via source YAML scoring configs
- Writes A/B-compatible artifacts:
  - `manifest.json`
  - `raw_events.ndjson`
  - `summary_codex.json`
  - `summary_claude_code.json`
  - `summary_combined.json`
  - `decision.md`

### 14.1 Completed live run

- `benchmarks/root_workload/ab_live/live_sample_20260222_022333/`
- Decision: `DROP`
- Combined deltas:
  - `delta_quality = -0.083333`
  - `delta_cost = +0.019669`
  - `delta_latency = -0.014491`
- Interpretation:
  - codex B regressed quality on sampled tasks
  - claude-code B stayed quality-neutral on sampled tasks

### 14.2 Partial/interrupted runs (salvaged)

- `benchmarks/root_workload/ab_live/live_sample_20260222_060934/`
  - Partial coverage (`A=40`, `B=34`)
  - Decision artifact generated: `REVISE`
  - Combined deltas: `dq -0.004412`, `dc +0.112514`, `dl -0.645978`

- `benchmarks/root_workload/ab_live/live_sample_20260222_062539/`
  - Partial coverage (`A=18`, `B=12`; claude B incomplete)
  - Decision artifact generated: `DROP` (not conclusive due incompleteness)
  - Combined deltas: `dq +0.055556`, `dc +0.273804`, `dl +0.067086`

### 14.3 Optuna live tuning with model-tier routing (2026-02-23/24)

Scripts:
- `scripts/root_workload/ab/tune_optuna_live_claude.py` (live Optuna tuner, calls `claude` CLI)
- `scripts/root_workload/ab/confirm_trial.py` (full-pack confirmation runner)

30-trial Optuna study (`claude_live_ab_20260223_190832`):
- 12 tasks/arm, `trial_seeded` resampling, 180s timeout, scale bounds [0.5, 1.5]
- Best trial (#24, score 34.3): `{0.2, 10.7.4, 10.7.5, 10.7.7, 10.7.9, 10.8}`, moderate routing
- TPE converged on this "core 5 + routing" pattern across trials 19, 24, 27
- 10.8 (model-tier routing) present in 9/10 top trials

100-task confirmation run (`confirm_20260223_233317`):
- Full `workload_pack_curated_debug_hard100_v1.json`, trial 24 config
- **Quality: A=96.0%, B=96.0% (zero regression)**
- **Cost: A=$0.0932/task, B=$0.0791/task (Δ = -15.2%)**
- **Latency: A=38.3s, B=38.7s (Δ = +1.1%, flat)**
- **Decision: KEEP**
- Per-model: Haiku 94.4% quality at $0.020/task (-78%), Sonnet 96.2% at $0.091 (-2.7%), Opus 96.7% at $0.094 (+1.1%)
- Per-class: `implementation_fix` improved (93.2%→96.6%), `planning_synthesis` regressed slightly (100%→93.5%), `long_input` held (100%→100%)

Classifier-based routing confirmation (`confirm_20260224_010932`):
- Full `workload_pack_curated_debug_hard100_v1.json`, Haiku pre-routing classifier
- Classifier reads task prompt (~$0.018/call via CLI) and outputs HAIKU/SONNET/OPUS
- **Quality: A=96.0%, B=93.0% (−3.0pp regression)**
- **Cost: A=$0.0932/task, B=$0.0786/task (Δ = −15.7%)**
- **Latency: A=38.3s, B=37.8s (Δ = −1.1%, flat)**
- **Decision: DROP** (quality regression exceeds −1% threshold)
- Routing distribution: Haiku=47 (93.6% pass), Sonnet=46 (91.3%), Opus=7 (100%)
- Classifier overhead: $1.83 total (23.3% of B-arm cost) — CLI-invoked Haiku costs ~$0.018/call, not ~$0.001 as estimated
- Failure cluster: `planning_synthesis` at 87% pass (4/31 failed), classifier routed 19/31 to Haiku — too aggressive
- **Conclusion: classifier provides identical cost savings to static routing (−15.7% vs −15.2%) with worse quality (−3pp vs 0pp) and added classifier overhead. Static routing from trial 24 remains the best approach.**

### 14.4 Important caveat

Current live B-arm is a prompt-policy proxy for the optimized profile (derived from Optuna best trial),
not full runtime toggle wiring for every 0.x / 10.7.x optimization. Treat this as directional live validation,
not final production lock criteria.
