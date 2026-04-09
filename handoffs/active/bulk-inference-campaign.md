# Bulk Inference Campaign: Packages B-E

**Status**: active (A+E done, C ready, F ready + smoke script, B nearly complete — Arm A + telemetry + TrimR + Phase 4 done, Arm B RUNNING with web-search fix + tool-compression-OFF. Sentinels expanded 10→39. RI-10 canary extended to 2026-04-12.)
**Created**: 2026-04-06
**Updated**: 2026-04-09
**Categories**: evaluation, inference, coordination
**Priority**: HIGH
**Depends on**: Package A results (complete)
**Related**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md), [`research-evaluation-index.md`](research-evaluation-index.md), [`pipeline-integration-index.md`](pipeline-integration-index.md), [`hermes-agent-index.md`](hermes-agent-index.md), [`inference-acceleration-index.md`](inference-acceleration-index.md)

---

## Problem

14 inference-dependent tasks are scattered across 5 domain indices. Running them independently requires 14 separate stack launches with 5-15 minutes of NUMA warmup each — over 3 hours of dead time before any evaluation begins. Many tasks share the same stack configuration and can collect cross-task telemetry simultaneously via feature flags.

**Consolidation**: 14 tasks → 4 optimized runs. Each run maximizes the number of tasks resolved per inference session by piggybacking telemetry collection, A/B comparisons, and eval passes on shared model instances.

---

## Package A Recap (complete)

Package A ran as an instrumented seeding eval on 2026-04-05/06.

**Script**: `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/package_a_instrumented_eval.sh`
**Data**: `/mnt/raid0/llm/epyc-orchestrator/data/package_a/`

**Tasks bundled**: CF Phase 1 validation, session analytics token budgeting, difficulty signal calibration, RI-9 risk distribution profiling, TrimR reasoning collection.

**Key results** (635 routing decisions):

| Finding | Data | Action |
|---------|------|--------|
| Difficulty thresholds miscalibrated | 92.3% easy, 0% hard at 0.3/0.6 | Recalibrated to 0.15/0.35 for ~40/40/20 split |
| Risk distribution healthy for canary | 80.6% low, 18.7% medium, 0.6% high | RI-10 canary ready to activate |
| Risk scorer correlates with latency | low p50=25s, medium p50=31s, high p50=69s | Validates risk scoring |
| Scorer bug discovered | `debug_scorer.py` word_count NoneType | Fixed |

**Remaining gap**: Package A was underpowered — only 635 decisions vs 1000+ target for statistical significance. Package B reruns the seeding eval at scale with recalibrated thresholds.

**RI-10 canary activated**: As of 2026-04-06, RI-10 canary is live (25% enforce on frontdoor, verified 23/77 split). The 3-day canary period (ends ~2026-04-09) supersedes the need for a separate RI-7 large-sample re-run — every frontdoor request during canary generates enforce-vs-shadow comparison data at production scale. Package D's AR-3 relaunch will generate additional canary data.

---

## Package B: Instrumented Seeding Eval v2

**Duration**: ~1 day (1000 questions × 3-way routing × ~10s avg)
**Stack required**: Full production (all NUMA instances + API)
**Depends on**: Package A results (for recalibrated thresholds)

### Tasks Resolved

| Task ID | Source | Description |
|---------|--------|-------------|
| RI-9 | [routing-and-optimization-index](routing-and-optimization-index.md) P3, [routing-intelligence.md](routing-intelligence.md) Phase 5 | Threshold sweep — Pareto reports (factuality vs cost vs latency). RI-8 (risk fields on `RoleResult`) verified complete. |
| TrimR eval | [research-evaluation-index](research-evaluation-index.md) P0 | **NOT APPLICABLE to current stack.** No production models produce `<think>` blocks. Qwen3.5 models support thinking but llama-server lacks `--jinja` flag. Baseline accuracy captured (frontdoor + coder). See results below. |
| Difficulty re-validation | [research-evaluation-index](research-evaluation-index.md) P0 | Validate recalibrated 0.15/0.35 thresholds show predictive power |
| Omega metric | [research-evaluation-index](research-evaluation-index.md) P0 | Per-suite reasoning token waste (Action 6 from reasoning-compression.md) |
| Tool output A/B | [research-evaluation-index](research-evaluation-index.md) P1 | `TOOL_OUTPUT_COMPRESSION` on vs off comparison |

### Feature Flags

| Env Var | Value | Purpose |
|---------|-------|---------|
| `ORCHESTRATOR_TWO_LEVEL_CONDENSATION` | 1 | Context folding Phase 1 (continue validation) |
| `ORCHESTRATOR_TASK_TOKEN_BUDGET` | 1 | Session token budgeting |
| `ORCHESTRATOR_SESSION_LOG` | 1 | Session journal for analysis |
| `ORCHESTRATOR_SESSION_COMPACTION` | 1 | Enable compaction pipeline |
| `ORCHESTRATOR_SEGMENT_CACHE_DEDUP` | 1 | Phase 1+ dedup telemetry |
| `ORCHESTRATOR_HELPFULNESS_SCORING` | 1 | Phase 2c heuristic telemetry |
| `ORCHESTRATOR_PROCESS_REWARD_TELEMETRY` | 1 | Phase 3a reward signals |
| `ORCHESTRATOR_TOOL_OUTPUT_COMPRESSION` | toggled | **Arm A** (first 500q): on. **Arm B** (second 500q): off. |

Classifiers: `factual_risk.mode: canary` (25% enforce on frontdoor, live since 2026-04-06), `difficulty_signal.mode: shadow` (both in `classifier_config.yaml`, difficulty thresholds recalibrated to 0.15/0.35).

### Commands

> **Important**: The `ORCHESTRATOR_*` env vars are read by the **orchestrator API process** (uvicorn), not the seeding script. The seeding script is an HTTP client. Either (a) restart the API with the flags, or (b) use `package_a_instrumented_eval.sh` as a template (it handles API restart with flags at lines 108-129).

**Step 0 — Restart orchestrator API with Package B flags** (if not already running with them):
```bash
cd /mnt/raid0/llm/epyc-orchestrator

# Kill existing API
fuser -k 8000/tcp 2>/dev/null || true
sleep 1

# Restart with all instrumentation flags
ORCHESTRATOR_MEMRL=1 \
ORCHESTRATOR_TOOLS=1 \
ORCHESTRATOR_SCRIPTS=1 \
ORCHESTRATOR_CACHING=1 \
ORCHESTRATOR_STREAMING=1 \
ORCHESTRATOR_GENERATION_MONITOR=1 \
ORCHESTRATOR_REACT_MODE=1 \
ORCHESTRATOR_CASCADING_TOOL_POLICY=1 \
ORCHESTRATOR_WORKER_CALL_BUDGET=1 \
ORCHESTRATOR_TASK_TOKEN_BUDGET=1 \
ORCHESTRATOR_SESSION_SCRATCHPAD=1 \
ORCHESTRATOR_SESSION_LOG=1 \
ORCHESTRATOR_SESSION_COMPACTION=1 \
ORCHESTRATOR_TWO_LEVEL_CONDENSATION=1 \
ORCHESTRATOR_APPROVAL_GATES=1 \
ORCHESTRATOR_RESUME_TOKENS=1 \
ORCHESTRATOR_SIDE_EFFECT_TRACKING=1 \
ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT=1 \
ORCHESTRATOR_SEGMENT_CACHE_DEDUP=1 \
ORCHESTRATOR_HELPFULNESS_SCORING=1 \
ORCHESTRATOR_PROCESS_REWARD_TELEMETRY=1 \
ORCHESTRATOR_TOOL_OUTPUT_COMPRESSION=1 \
  nohup python3 -m uvicorn src.api:app \
    --host 127.0.0.1 --port 8000 --workers 6 --limit-concurrency 4 \
    > logs/orchestrator.log 2>&1 &

# Wait for health
for i in $(seq 1 60); do
  curl -sf http://localhost:8000/health > /dev/null 2>&1 && echo "API healthy (${i}s)" && break
  sleep 1
done
```

**Phase 1a — Seeding eval, Arm A** (tool compression ON — already set in Step 0):
```bash
cd /mnt/raid0/llm/epyc-orchestrator

mkdir -p data/package_b

python3 scripts/benchmark/seed_specialist_routing.py \
  --3way \
  --suites math simpleqa hotpotqa gpqa coder thinking general agentic instruction_precision mode_advantage_hard \
  --sample-size 50 \
  --preflight \
  --output data/package_b/seeding_arm_a.json
```

**Phase 1b — Seeding eval, Arm B** (tool compression OFF — restart API with flag toggled):
```bash
# Restart API with TOOL_OUTPUT_COMPRESSION=0 (keep all other flags the same)
fuser -k 8000/tcp 2>/dev/null || true; sleep 1
# Same as Step 0 but with ORCHESTRATOR_TOOL_OUTPUT_COMPRESSION=0
# <repeat Step 0 command with ORCHESTRATOR_TOOL_OUTPUT_COMPRESSION=0>

python3 scripts/benchmark/seed_specialist_routing.py \
  --3way \
  --suites math simpleqa hotpotqa gpqa coder thinking general agentic instruction_precision mode_advantage_hard \
  --sample-size 50 \
  --output data/package_b/seeding_arm_b.json
```

**Phase 2 — TrimR eval** (dedicated reasoning compression pass):
```bash
cd /mnt/raid0/llm/epyc-inference-research

# NOTE: eval_trimr.py has a hardcoded 120s timeout (line 120) that is too short for GPQA
# reasoning-heavy prompts. Package A run timed out on GPQA. Either:
#   (a) increase timeout in eval_trimr.py before running, or
#   (b) run GPQA separately with --suites gpqa and a patched timeout

python3 scripts/benchmark/eval_trimr.py \
  --suites math gpqa \
  --n-questions 100 \
  --strategy all \
  --model-port 8070 \
  --output /mnt/raid0/llm/epyc-orchestrator/data/package_b/trimr_results.jsonl
```

**Phase 3 — Telemetry collection**:
```bash
cd /mnt/raid0/llm/epyc-orchestrator

python3 scripts/server/delegation_slo_report.py --date $(date +%Y-%m-%d) --json \
  > data/package_b/slo_report.json

python3 scripts/server/chain_anomaly_detector.py --date $(date +%Y-%m-%d) --json \
  > data/package_b/anomaly_report.json
```

**Phase 4 — Analysis** (post-processing, no inference):
- Difficulty signal: correlate shadow predictions with actual correctness at new thresholds
- Omega metric: `reasoning_tokens / total_tokens` per suite, cross-referenced with accuracy
- Tool compression: diff Arm A vs Arm B on token counts, latency, quality scores

### Expected Output

| File | Content |
|------|---------|
| `data/package_b/seeding_arm_a.json` | 3-way eval, tool compression ON |
| `data/package_b/seeding_arm_b.json` | 3-way eval, tool compression OFF |
| `data/package_b/trimr_results.jsonl` | Reasoning compression (full/strip/trimr) |
| `data/package_b/slo_report.json` | Delegation latency (p50/p95/p99) |
| `data/package_b/anomaly_report.json` | Chain anomaly detection |
| `logs/progress/<date>.jsonl` | Raw telemetry (difficulty + risk shadow predictions) |

### Success Criteria

- [x] **RI-9**: DONE (2026-04-09). 2433 routing→completion joins from progress JSONL. Risk distribution: low=1846 (64.4% escalated), medium=571 (54.3% escalated), high=16 (50.0% escalated). **Finding**: high-risk prompts escalate LESS than low-risk — counterintuitive, but sample size is tiny (n=16 high). Risk band doesn't predict escalation need at current thresholds. Recommend: larger sample before threshold changes.
- [x] **TrimR**: DONE (2026-04-09). Eval on DeepSeek-R1-Distill-Qwen-7B (4×48t NUMA). GPQA: thinking helps ~6pp (full 58.3% → strip 52.6%), TrimR prunes 45% of thinking while preserving correct count. Math (GSM8K): thinking minimal (151 tok avg), pruning has zero effect — model barely thinks on easy problems. **Verdict: TrimR valuable on hard tasks (GPQA), irrelevant on easy tasks (GSM8K). Aligns with difficulty-adaptive routing.** Prerequisites resolved: `chat.cpp` PEG parser fix, binary rebuild, `--jinja` in stack, `\boxed{}` scorer fix, per-strategy output files. Data: `data/package_b/trimr_r1_7b_gpqa_trimr.jsonl`, `trimr_r1_7b_math_{full,think-strip,trimr}.jsonl`.
- [x] **Difficulty**: DONE (2026-04-09). At 0.15/0.35 thresholds: easy=1834 (62.2% escalated), medium=517 (60.7%), hard=82 (62.2%). **Finding**: NO predictive spread — escalation rate is flat across difficulty bands. The difficulty signal at current thresholds does not differentiate routing needs. Recommend: re-examine feature weights or add semantic features before moving to enforce mode.
- [x] **Omega**: DONE (2026-04-09). **7 of 10 suites show tools HURT accuracy** (direct > REPL): agentic -54.5pp, coder -44pp, general -26pp, math -26pp, mode_advantage_hard -23.7pp, thinking -8pp, instruction_precision -6pp. Only hotpotqa (+12pp) and gpqa (+6pp) benefit from tools. **Verdict**: Tools are net-negative on most suites. Reasoning tokens via REPL are actively harmful for agentic, coder, general, and math tasks.
- [ ] **Tool A/B**: Arm B killed at 104/400 questions (2026-04-09). Checkpoint JSONL has full per-question results. **Key finding**: WS-3 was NOT firing — 100% web search in REPL mode. Root cause: `routing.py` hardcoded `task_type: "chat"`, so `NO_WEB_TASK_TYPES` never matched. Fixed with role→task_type derivation. **Arm A'** launched with `TOOL_OUTPUT_COMPRESSION=1` + WS-3 fix, 5 suites × 20q = 100 questions for controlled tool-compression-only comparison.

---

## Package C: Context Folding Eval Batch

**Duration**: ~half day (~200 inference calls)
**Stack required**: Individual model servers (NOT full orchestrator)
**Depends on**: None (independent of B)
**Status**: READY — all eval scripts implemented (2026-04-07/09). Phase 2c already has live results. Phases 2a/2b/TALE need model servers only.

### Tasks Resolved

| Task ID | Source | Description |
|---------|--------|-------------|
| CF Phase 2a | [context-folding-progressive.md](context-folding-progressive.md) | Summarizer quality across 3 model tiers (1.5B / 7B / 32B) |
| CF Phase 2b | [context-folding-progressive.md](context-folding-progressive.md) | Free-zone compression threshold sweep (5 levels × 20 logs) |
| CF Phase 2c | [context-folding-progressive.md](context-folding-progressive.md) | Helpfulness calibration — LLM Δ_k ground truth vs heuristic scores |
| TALE budget eval | [research-evaluation-index](research-evaluation-index.md) P0.5, [reasoning-compression.md](reasoning-compression.md) Action 15 | TALE dynamic budget estimation: baseline vs static word limits (Action 12) vs self-estimated budget. Determines if TALE can replace regex difficulty_signal.py. |

### Models Required

| Model | Role | Port | NUMA Config | Purpose |
|-------|------|------|-------------|---------|
| Qwen3-1.5B | worker_fast | any free | 1×24t | 2a: lowest-tier summarizer |
| Qwen3-Coder-30B-A3B Q4KM | worker_explore | any free | 1×48t | 2a: mid-tier summarizer + 2b: compaction engine |
| Qwen2.5-Coder-32B Q4KM | coder_esc | any free | 1×48t | 2a: high-tier summarizer |

These run one at a time on a single NUMA quarter — no concurrent instances needed.

### Commands

**Phase 2a — Summarizer quality eval** — READY (script created 2026-04-07):
```bash
cd /mnt/raid0/llm/epyc-inference-research

python3 scripts/benchmark/eval_summarizer.py \
  --traces-dir /mnt/raid0/llm/tmp \
  --model-ports 8072,8071,8070 \
  --n-traces 20 \
  --judge-port 8082 \
  --output /mnt/raid0/llm/epyc-orchestrator/data/package_c/summarizer_quality.csv
```

**Phase 2b — Free-zone compression sweep** — READY (implemented 2026-04-07):
```bash
cd /mnt/raid0/llm/epyc-inference-research

python3 scripts/benchmark/eval_compaction_sweep.py \
  --traces-dir /mnt/raid0/llm/tmp \
  --levels 1,2,3,4,5 \
  --model-port 8071 \
  --judge-port 8082 \
  --output /mnt/raid0/llm/epyc-orchestrator/data/package_c/compaction_sweep.csv
```

**Phase 2c — Helpfulness calibration** — DONE (heuristic-only, no model needed):
```bash
cd /mnt/raid0/llm/epyc-inference-research

# Already runnable — pure heuristic, no model servers required.
# Results from 2026-04-07: Spearman ρ=0.63-0.65, overlap-heavy config best.
python3 scripts/benchmark/eval_helpfulness_calibration.py \
  --traces-dir /mnt/raid0/llm/tmp \
  --weight-sweep \
  --output /mnt/raid0/llm/epyc-orchestrator/data/package_c/helpfulness_calibration.csv
```

**TALE budget eval** — READY (script created 2026-04-09):
```bash
cd /mnt/raid0/llm/epyc-inference-research

# Compares: baseline (no constraint) vs static word limits (Action 12) vs TALE self-estimated budget
# Uses any single model server. Best run on worker_math (port 8080) for math suites,
# worker_general for general suites.
python3 scripts/benchmark/eval_tale_budget.py \
  --suites math general \
  --n-questions 20 \
  --model-port 8080 \
  --output /mnt/raid0/llm/epyc-orchestrator/data/package_c/tale_budget.jsonl
```

### Prerequisites

- [x] **BLOCKER 2a**: `eval_summarizer.py` — ✅ 2026-04-07. Created with 3-tier model support, dry-run mode, CSV output.
- [x] **BLOCKER 2b**: `eval_compaction_sweep.py` — ✅ 2026-04-07. `evaluate_compaction()` implemented with model/judge port args.
- [x] **BLOCKER 2c**: `eval_helpfulness_calibration.py` — ✅ 2026-04-07. `run_calibration()` implemented (pure heuristic, no model needed). Tested on 250 real traces: Spearman ρ=0.63-0.65, best config is overlap-heavy (0.1/0.5/0.3/0.1).
- [x] **BLOCKER TALE**: `eval_tale_budget.py` — ✅ 2026-04-09. Three-condition comparison (baseline/static/TALE), OAA/PTI output, dry-run mode.
- [x] Session trace files in `/mnt/raid0/llm/tmp/session_*.md` — **252 available** (need 20)
- [ ] Model servers started individually via `orchestrator_stack.py start --include-warm <role>`
- [x] Shared infrastructure: `eval_helpers.py` (trace parser, model API, judge helper, identifier extraction)

**Package C code is ready.** Only model servers needed to run live eval (2a summarizer, 2b compaction). Phase 2c (helpfulness calibration) is already runnable and has produced results.

### Expected Output

| File | Content |
|------|---------|
| `data/package_c/summarizer_quality.csv` | Per-model-tier scores (faithfulness, compression, retention) |
| `data/package_c/compaction_sweep.csv` | Quality vs compression ratio at 5 levels |
| `data/package_c/helpfulness_calibration.csv` | Heuristic vs LLM-based Δ_k correlation |
| `data/package_c/tale_budget.jsonl` | TALE budget eval: accuracy + OAA/PTI across 3 conditions |

### Success Criteria

- [ ] **CF Phase 2a**: Clear quality ranking across tiers — 32B > 7B > 1.5B on faithfulness. Identify minimum-viable tier.
- [ ] **CF Phase 2b**: Free-zone boundary identified. Expected: L1-L2 (20-40%) near-lossless, L3 (60%) is the knee.
- [x] **CF Phase 2c**: Heuristic helpfulness scores correlate with ground truth — ✅ 2026-04-07. Spearman ρ=0.65 (threshold was >0.5). Best config: overlap-heavy (0.1/0.5/0.3/0.1). LLM-based Δ_k comparison deferred (heuristic ground truth sufficient).
- [ ] **TALE budget**: TALE self-estimated budget outperforms static word limits on OAA metric. If yes → prototype integration with difficulty_signal.py. If no → static limits (Action 12) are sufficient, TALE deferred.

**Post-Package-C**: Phase 2c scoring formula may be updated with ByteRover compound retention scoring (intake-267). Current 4-signal heuristic evaluated during Package C. If ρ > 0.5, ByteRover 6-signal weights (adding importance + maturity_tier) calibrated using Package C Δ_k ground truth. Does NOT block Package C execution or change its success criteria.

---

## Package D: AR-3 Relaunch + Canary

**Duration**: Multi-day (AR-3 runs autonomously; RI-10 canary = 3-day passive)
**Stack required**: Full production (all NUMA instances + API)
**Depends on**: Package B results (threshold decisions inform canary config and AR-3 sentinel pool)

### Tasks Resolved

| Task ID | Source | Description |
|---------|--------|-------------|
| AR-3 | [routing-and-optimization-index](routing-and-optimization-index.md) P5 | Autoresearch relaunch with expanded T0 sentinels |
| RI-7 re-run | [routing-intelligence.md](routing-intelligence.md) Phase 4 | Large-sample A/B re-run (70q was underpowered). Canary data from RI-10 serves as the re-run — enforce-vs-shadow comparison at production scale. |
| RI-10 | [routing-and-optimization-index](routing-and-optimization-index.md) P6 | 🔄 Canary live since 2026-04-06 (25% enforce on frontdoor). Window extended to 2026-04-12 (was 2026-04-09) — n=16 high-risk too small for decision. Package D extends monitoring via AR-3 traffic. |
| CF Phase 3c | [context-folding-progressive.md](context-folding-progressive.md) | Quality monitor validation on real multi-turn sessions |
| DS-5 | [routing-and-optimization-index](routing-and-optimization-index.md) P7 | Model exploration via StructuralLab species |
| LG Phase 3 | [langgraph-migration.md](langgraph-migration.md) | Per-node flag flip + production validation. Infrastructure complete (7 flags, dispatch helper, 48 tests). Flip `ORCHESTRATOR_LANGGRAPH_INGEST=1` first, validate, then proceed down migration order. No inference needed — uses existing production traffic. |

### Config Changes (before launch)

**`classifier_config.yaml`** — already set as of 2026-04-06:
```yaml
factual_risk:
  mode: "canary"          # already live (changed from "shadow" on 2026-04-06)
  canary_ratio: 0.25      # 25% of frontdoor requests get enforce
  canary_roles: [frontdoor]
# Canary window extended to 2026-04-12 (n=16 high-risk insufficient for decision).
# Decision after extended window: keep canary, expand to RI-11, or revert.
```

**Feature flags**:

| Env Var | Value | Purpose |
|---------|-------|---------|
| `ORCHESTRATOR_ROLE_AWARE_COMPACTION` | 1 | CF Phase 3b role profiles active |
| `ORCHESTRATOR_PROCESS_REWARD_TELEMETRY` | 1 | CF Phase 3a reward signals |
| `ORCHESTRATOR_SEGMENT_CACHE_DEDUP` | 1 | Phase 1+ dedup |
| `ORCHESTRATOR_HELPFULNESS_SCORING` | 1 | Phase 2c heuristic active |

### Commands

**AR-3 launch**:
```bash
cd /mnt/raid0/llm/epyc-orchestrator

python3 scripts/autopilot/autopilot.py start --tui
```

**Daily monitoring** (run each day during the multi-day run):
```bash
cd /mnt/raid0/llm/epyc-orchestrator

python3 scripts/server/delegation_slo_report.py --date $(date +%Y-%m-%d) --json
python3 scripts/server/chain_anomaly_detector.py --date $(date +%Y-%m-%d) --json
```

### Safety Gates (from AR-3 Run 2 hardening)

| Gate | Threshold | Action | Deficiency Category (AP-14) |
|------|-----------|--------|---------------------------|
| Quality floor | avg < 2.0/3.0 (T0) or 1.0/3.0 (T1) | Reject trial | `quality_floor` |
| Regression | Δq < -0.05 vs baseline | Reject trial | `regression` |
| Per-suite regression | Δq < -0.1 any suite | Reject trial | `per_suite_regression` |
| Routing diversity | >80% architect-tier | Reject trial | `routing_diversity` |
| Throughput floor | <80% of baseline speed | Reject trial | `throughput` |
| Catastrophic shrinkage | >50% file size reduction | Reject + revert | `shrinkage` |
| Code mutation validation | Syntax + imports + public names | Reject on failure | `code_validation` |
| Consecutive failures | 3× consecutive fail | Auto-rollback | `consecutive_failures` |
| Worktree isolation | All PromptForge mutations in temp worktree | Auto-reject on timeout | — |
| Structural prune (AP-17) | quality < baseline OR instruction_ratio not decreased | Reject + revert | — |

### Prerequisites

- [ ] Package B results analyzed (risk thresholds finalized, difficulty signal validated)
- [x] AR-3 sentinel pool expanded 10 → 39 questions (2026-04-09). Tier 0 (easy) retained + 29 harder (GPQA, olympiad, multi-hop, tool-use). `per_suite_quality` schema added to baseline.
- [ ] `autopilot_baseline.yaml` updated with Package B metrics (per_suite_quality values pending)

### Success Criteria

- [ ] **AR-3**: ≥50 trials completed without corruption. ≥1 useful change accepted (Pareto-improving).
- [ ] **RI-7 re-run**: Canary data produces ≥500 enforce vs ≥1500 shadow decisions. Compare factuality F1, escalation rate, cost. Result is statistically significant (p < 0.05) or confirms NS with adequate power.
- [ ] **RI-10**: Extended canary window (ends 2026-04-12, was 2026-04-09). Need ≥50 high-risk samples (had n=16). No latency regression (p95 within 10% of shadow baseline). No accuracy drop on frontdoor. Decision: proceed to RI-11 (expand) or revert to shadow.
- [ ] **CF Phase 3c**: Quality monitor fires on ≥3 consolidation events. No false positives (degradation detected when quality is stable).
- [ ] **DS-5**: ≥3 model candidates tested via StructuralLab species.

---

## Package E: Vision + Hermes Validation

**Duration**: ~1 hour
**Stack required**: Vision model servers (ports 8086/8087) only
**Depends on**: None (independent)

### Tasks Resolved

| Task ID | Source | Description |
|---------|--------|-------------|
| Vision P0 | [pipeline-integration-index](pipeline-integration-index.md) P0 | Live validation with VL model servers |
| Hermes P2 | [hermes-agent-index](hermes-agent-index.md) P2 | Streaming + routing override param validation |

### Commands

**Vision validation**:
```bash
cd /mnt/raid0/llm/epyc-orchestrator

# Start vision models only
python3 scripts/server/orchestrator_stack.py start --include-warm worker_vision vision_escalation

# Test OpenAI-compat multimodal API
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}]}]}'
```

**Hermes streaming validation**:
```bash
# Test routing overrides
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "stream": true, "messages": [{"role": "user", "content": "Hello"}], "x_max_escalation": 1, "x_force_model": "frontdoor", "x_disable_repl": true}'
```

### Results (2026-04-06)

- [x] **Hermes P2 streaming**: PASS — SSE chunks arrive, `finish_reason: stop` clean
- [x] **Hermes P2 routing overrides**: PASS — `x_force_model`, `x_max_escalation`, `x_disable_repl` work (must be strings, not ints)
- [x] **Vision P0 OpenAI-compat**: FIXED 2026-04-08 — `content: str | list` in `OpenAIMessage`, `_extract_text()` helper in `openai_compat.py` handles both formats.
- [x] **Vision P0 `/v1/vision/analyze`**: FIXED 2026-04-08 — Removed invalid `--no-display-prompt` flag from `vl_describe.py:122`.
- [x] **`orchestrator_stack.py --only`**: PASS — New flag works, only touches specified roles, preserves healthy servers

### ~~Bugs Found~~ Bugs Fixed (2026-04-08)

1. ~~**OpenAI-compat multipart content**~~ — ✅ `content: str | list` + `_extract_text()` helper at 4 downstream locations
2. ~~**VL analyzer flag**~~ — ✅ Removed `--no-display-prompt` from `vl_describe.py` (invalid for `llama-mtmd-cli`)

---

## Package F: llama.cpp v3 Smoke Tests

**Duration**: ~30 min (4 model loads + feature checks)
**Stack required**: No production stack — uses experimental binary at `/mnt/raid0/llm/llama.cpp-experimental/build/bin/`
**Depends on**: v3 cherry-pick rebuild (DONE 2026-04-09)
**Related**: [`llama-cpp-v3-upstream-rebuild.md`](llama-cpp-v3-upstream-rebuild.md)

### Tasks Resolved

| Task ID | Source | Description |
|---------|--------|-------------|
| v3-smoke | [llama-cpp-v3-upstream-rebuild](llama-cpp-v3-upstream-rebuild.md) | All 4 production models load + generate at expected t/s |
| v3-features | [llama-cpp-v3-upstream-rebuild](llama-cpp-v3-upstream-rebuild.md) | Feature-specific tests: moe-n-expert, lookup, paged attention, slot erase, server health |
| v3-hadamard | [kv-cache-quantization](kv-cache-quantization.md) | Upstream Hadamard auto-rotation confirmed (`-ctk q4_0 -ctv f16` without `--kv-hadamard`) |
| v3-ppl | [kv-cache-quantization](kv-cache-quantization.md) | PPL regression test: v3 `-ctk q4_0 -ctv f16` matches v2 measurements (+-0.02) |
| v3-numa | [inference-acceleration-index](inference-acceleration-index.md) | NUMA throughput within 5% of v2 baseline |

### Commands

All commands use the experimental binary (not production):
```bash
cd /mnt/raid0/llm/llama.cpp-experimental

# Model load + generate (each model)
./build/bin/llama-cli -m <model_path> -n 64 -p "Hello" --no-cnv -t 48

# Feature: moe-n-expert
./build/bin/llama-cli -m <reap_path> -n 32 -p "Hello" --no-cnv --moe-n-expert 6 -t 96

# Feature: paged attention (check RSS)
./build/bin/llama-server -m <model> -t 48 -c 8192 --port 9999 --paged-attention

# Feature: slot erase
curl -X DELETE http://localhost:9999/slots/0

# PPL regression
./build/bin/llama-perplexity -m <model> -f <wiki_test> -ctk q4_0 -ctv f16 -fa
```

See full test matrix in [`llama-cpp-v3-upstream-rebuild.md`](llama-cpp-v3-upstream-rebuild.md) §Smoke Tests and §Feature-Specific Tests.

### Results

- [ ] 4 production models load + generate
- [ ] moe-n-expert works on REAP-246B
- [ ] Paged attention lowers RSS vs non-paged
- [ ] Slot erase returns HTTP 200
- [ ] Server health returns HTTP 200
- [ ] NUMA throughput within 5% of v2
- [ ] Upstream Hadamard auto-rotation confirmed
- [ ] PPL matches v2 (+-0.02)

### Post-Smoke-Test: Production Binary Swap

Once all smoke tests pass, swap the production binary:
```bash
cd /mnt/raid0/llm/llama.cpp
git checkout production-consolidated-v3
cmake -B build -DGGML_CPU_ALL_VARIANTS=ON -DGGML_BACKEND_DL=ON -DBUILD_SHARED_LIBS=ON -DLLAMA_CURL=ON
cmake --build build -j96
```

Then update orchestrator config:
- Remove `--kv-hadamard` from `orchestrator_stack.py:950`
- Update branch references in `model_registry.yaml`
- Update `verify_llama_cpp.sh` EXPECTED_BRANCH to `production-consolidated-v3`

---

## Cross-Package Dependency Graph

```
✅ PACKAGE A ────────────── DONE (2026-04-06, 635 decisions, thresholds recalibrated)
  │
  ├── PACKAGE B ──────────── Instrumented Seeding v2 (~1 day, full stack)
  │     │                     RI-9 + TrimR + difficulty + Omega + tool A/B
  │     │
  │     └── PACKAGE D ─────── AR-3 + RI-10 Canary + CF-3c + DS-5 (multi-day, full stack)
  │                            Depends on B for threshold decisions + sentinel expansion
  │
  ├── PACKAGE C ──────────── CF Eval Batch (~½ day, individual models) — READY
  │                            Scripts done, Phase 2c complete (ρ=0.65). 2a/2b need model servers.
  │
  ├── ✅ PACKAGE E ──────────── DONE 2026-04-06 (Hermes PASS, vision fixed 2026-04-08)
  │
  └── PACKAGE F ──────────── v3 Smoke Tests (~30min, experimental binary only)
                               Cherry-picks DONE 2026-04-09. Unblocks production binary swap.
```

## Execution Order

| Order | Package | Duration | Why this order |
|-------|---------|----------|----------------|
| 1 | ~~**E**~~ | ~~1 hour~~ | ✅ DONE 2026-04-06. Hermes streaming PASS, vision fixed 2026-04-08. |
| 2 | **F** | ~30 min | **Can run anytime** — uses experimental binary, no production stack conflict. Unblocks v3 swap. |
| 3 | **B** | ~1 day | All scripts ready. Needs full stack exclusive. Results feed D. |
| 4 | **D** | Multi-day | Depends on B. Longest run. |
| 5 | **C** | ~½ day | READY — scripts implemented 2026-04-07. Phase 2c done (heuristic). 2a/2b need individual model servers. |

**Parallelization note**: F can run anytime (experimental binary, loads models one-at-a-time). C uses individual model servers on a single NUMA quarter — can run during B/D downtime.

**Recommended approach**: Run F first (quick, unblocks v3 swap). Then B → D (full stack). Run C during B/D downtime or after.

---

## Telemetry Collection Plan

| Package | Data Streams |
|---------|-------------|
| B | Progress JSONL (difficulty + risk shadow), seeding results JSON (3-way scores), TrimR JSONL (reasoning traces), SLO report, anomaly report, tool compression delta |
| C | Summarizer quality CSV, compaction sweep CSV, helpfulness calibration CSV, TALE budget JSONL, SFT pairs JSONL (if `compaction_training_data` flag on) |
| D | Autopilot journal (TSV + JSONL), Pareto archive, canary telemetry (enforce vs shadow quality delta), quality monitor events, StructuralLab results |
| E | Vision API response logs, streaming validation results |
| F | Model load t/s, feature pass/fail, PPL measurements, NUMA throughput |

---

## Reporting

After each Package completes:
1. Update the task checkboxes in this file
2. Update the relevant domain index (routing, research, pipeline, hermes)
3. Update [`master-handoff-index.md`](master-handoff-index.md) priority queue
4. Add session to `progress/YYYY-MM/YYYY-MM-DD.md`

When all Packages complete:
- Move this handoff to `handoffs/completed/`
- Extract reusable findings to docs/research
- Update `CHANGELOG.md` with key results
