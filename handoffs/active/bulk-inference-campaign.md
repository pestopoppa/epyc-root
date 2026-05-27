# Bulk Inference Campaign: Packages B-J

**Status**: active. Completed: A, B, C, E, F, G1/G2/G7/G7a, AM-L1-L3b, SEAL, H1/H2/H3/H6 fold-in. Remaining inference-gated work is now led by Package J, especially J1-J3 parallel-dispatch validation; downstream D-tail/G/H/I/J4+ should not run before those gates pass.
**Created**: 2026-04-06
**Updated**: 2026-05-26
**Categories**: evaluation, inference, coordination
**Priority**: HIGH
**Depends on**: Package A results (complete)
**Related**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md), [`research-evaluation-index.md`](research-evaluation-index.md), [`pipeline-integration-index.md`](pipeline-integration-index.md), [`hermes-agent-index.md`](hermes-agent-index.md), [`inference-acceleration-index.md`](inference-acceleration-index.md), [`cross-role-nway-contention-matrix.md`](cross-role-nway-contention-matrix.md)

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
- [x] **Tool A/B**: DONE (2026-04-10). Original Arm B killed at 104/400 (WS-3 bug: `routing.py` hardcoded `task_type="chat"`, 100% web search). Fixed with role→task_type derivation. Controlled rerun: A' (compression ON, 100q) vs B' (compression OFF, 99q), 5 suites × 20q, WS-3 fix active. **Finding**: Compression slightly net-positive (+4pp REPL overall). Suite-dependent: math +25pp (noise reduction), hotpotqa -25pp (retrieval context helps), coder/general/gpqa near-neutral. WS-3 fix validated (near-zero web calls both arms). No change to default (compression ON).

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

- [x] **CF Phase 2a**: DONE (2026-04-10). 1.5B: faith=2.55, retain=1.45; **30B-A3B: faith=3.0, retain=3.0** (perfect); 32B: errors (v3 spec decode bug, now fixed). **30B-A3B is the minimum viable summarizer.** 1.5B adequate faithfulness but poor retention.
- [x] **CF Phase 2b**: DONE (2026-04-11). L3 is the sweet spot: 82% actual compression, 2.84/3 retention. Faithfulness stable (~2.9) across L1-L4. L5 (95%) hits 89.6% compression but retention drops to 1.58. Free-zone boundary = L3.
- [x] **CF Phase 2c**: Heuristic helpfulness scores correlate with ground truth — ✅ 2026-04-07. Spearman ρ=0.65 (threshold was >0.5). Best config: overlap-heavy (0.1/0.5/0.3/0.1). LLM-based Δ_k comparison deferred (heuristic ground truth sufficient).
- [x] **TALE budget**: DONE (2026-04-11). Static limits (Action 12) outperform TALE on OAA. Baseline 95% acc, static 75%, TALE 72.5%. TALE matches baseline on math (95%) but hurts general (50%). **Decision: keep static limits, TALE deferred.**

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
| RI-10 | [routing-and-optimization-index](routing-and-optimization-index.md) P6 | 🔄 Canary live since 2026-04-06 (25% enforce on frontdoor). Window extended to 2026-04-27 (was 2026-04-09) — n=16 high-risk too small for decision. Package D extends monitoring via AR-3 traffic. |
| CF Phase 3c | [context-folding-progressive.md](context-folding-progressive.md) | Quality monitor validation on real multi-turn sessions |
| DS-5 | [routing-and-optimization-index](routing-and-optimization-index.md) P7 | Model exploration via StructuralLab species |
| AP-19 | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P10 | GEPA frontdoor optimization — integrated as PromptForge mutation type (30% of PromptForge trials). Comparison data collected in journal. |
| AP-20 | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P10 | GEPA Full Program Adapter eval — resolved by comparing GEPA vs LLM mutation acceptance rates in AR-3 journal |
| MH-4 | [meta-harness-optimization.md](meta-harness-optimization.md) Tier 2b | GEPA search algorithm comparison — Pareto frontier contributions by mutation source analyzed from AR-3 journal |
| ~~LG Phase 3~~ | ~~[langgraph-migration.md](langgraph-migration.md)~~ | ✅ DONE (2026-04-11). All 7 per-node flags enabled in `orchestrator_stack.py`. Fixed append-field delta bug in `_run_via_langgraph`. 72 LG tests + 4495 unit tests pass. |
| ColBERT S1 | [colbert-reranker-web-research.md](colbert-reranker-web-research.md) | Passive data collection — S1 relevance instrumentation fires on all web_research calls. AR-3's web_research sentinel suite (50q) generates irrelevant-page-rate metrics. Post-AR-3: grep for `web_research relevance summary` to decide S3 go/no-go (>20% threshold). |

### AM KV Compaction Integration (NEW — 2026-04-13)

**Status**: ✅ Autopilot integration COMPLETE (2026-04-14). `slot_compact` action wired into controller + slot memory visibility added. Ready for AR-3.

**IMPORTANT: Passive by default.** The compact endpoint does NOTHING unless explicitly called. Normal inference is completely unaffected — no feature flags, no env vars, no config changes needed. The server behaves identically to pre-AM builds until a `compact` request is issued.

**Autopilot integration (2026-04-14)**:
1. **`slot_compact` action dispatch** — `autopilot.py:812-849`. Controller can issue `{"type": "slot_compact", "port": 8080, "keep_ratio": 0.3, ...}`. Calls `POST /slots/{id}?action=compact`, logs pre/post token counts, measures quality via `hybrid_eval()`.
2. **Slot memory visibility** — `_query_slot_memory()` queries `/slots` on primary production ports (8070-8084) every trial. Shows per-slot context size + state in controller prompt. Controller can now make informed compaction decisions.
3. **Action guideline** — Controller prompt guideline #7: "If any slot shows >4000 tokens cached, consider slot_compact."
4. **Strategy guidance** — `program.md` Tier 4.5 section documents validated parameters (keep_ratio=0.3, beta=0.5), target ports, constraints (only compact idle slots), and operational context.

**Long-context validation needed**: Production contexts are 8K-32K tokens. Our tests validated up to 2.7K. AM should perform better at longer contexts (more attention concentration). AR-3 traffic provides the opportunity to validate at production scale. Monitor answer quality on compacted vs non-compacted slots to establish the production compression-quality curve.

**Key files**:
- Server endpoint: `tools/server/server-context.cpp` → `handle_slots_compact()`
- Autopilot dispatch: `epyc-orchestrator/scripts/autopilot/autopilot.py:812-849` → `slot_compact` handler
- Slot visibility: `epyc-orchestrator/scripts/autopilot/autopilot.py:_query_slot_memory()` → queries `/slots` on production ports
- Strategy: `epyc-orchestrator/scripts/autopilot/program.md` → Tier 4.5 KV Compaction section
- Validation: compare quality metrics on compacted slots vs full-cache baseline during AR-3

### Config Changes (before launch)

**`classifier_config.yaml`** — already set as of 2026-04-06:
```yaml
factual_risk:
  mode: "canary"          # already live (changed from "shadow" on 2026-04-06)
  canary_ratio: 0.25      # 25% of frontdoor requests get enforce
  canary_roles: [frontdoor]
# Canary window extended to 2026-04-27 (n=16 high-risk insufficient for decision).
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

- [x] Package B results analyzed (risk thresholds finalized, difficulty signal validated, tool A/B complete)
- [x] AR-3 sentinel pool expanded 10 → 39 questions (2026-04-09). Tier 0 (easy) retained + 29 harder (GPQA, olympiad, multi-hop, tool-use). `per_suite_quality` schema added to baseline.
- [ ] `autopilot_baseline.yaml` updated with Package B metrics (per_suite_quality values still null — being populated by active autopilot run, trial ~78 as of 2026-04-11)
- [x] GEPA integration into PromptForge (2026-04-12). `gepa_optimizer.py` adapter + `gepa` mutation type + 30/70 split in `_auto_action`. AP-19/20/MH-4 resolved via AR-3 trial journal data. 10 tests pass.

### Success Criteria

- [ ] **AR-3**: ≥50 trials completed without corruption. ≥1 useful change accepted (Pareto-improving).
- [ ] **RI-7 re-run**: Canary data produces ≥500 enforce vs ≥1500 shadow decisions. Compare factuality F1, escalation rate, cost. Result is statistically significant (p < 0.05) or confirms NS with adequate power.
- [ ] **RI-10**: Extended canary window (ends 2026-04-27, was 2026-04-09). Need ≥50 high-risk samples (had n=16). No latency regression (p95 within 10% of shadow baseline). No accuracy drop on frontdoor. Decision: proceed to RI-11 (expand) or revert to shadow.
- [ ] **CF Phase 3c**: Quality monitor fires on ≥3 consolidation events. No false positives (degradation detected when quality is stable).
- [ ] **DS-5**: ≥3 model candidates tested via StructuralLab species.

### Post-AR-3 Analysis Index

After AR-3 completes (≥50 trials), run this checklist to extract all folded-in results. Each item lists the analysis command, where the data lives, and the decision it gates.

**Data locations** (all paths relative to `/mnt/raid0/llm/epyc-orchestrator`):
- Autopilot journal: `orchestration/autopilot_journal.jsonl` (+ `.tsv` human-readable)
- Autopilot state: `orchestration/autopilot_state.json` (Pareto archive, consecutive_failures)
- Seeding checkpoints: `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/eval/*.jsonl`
- Orchestrator logs: stdout/stderr from `autopilot.py` process

#### Phase 1: Autopilot Health (run first)

- [ ] **Trial count + corruption check**
  ```bash
  wc -l orchestration/autopilot_journal.jsonl
  # Expect ≥50 lines. Check for JSON parse errors:
  python3 -c "import json; [json.loads(l) for l in open('orchestration/autopilot_journal.jsonl')]" 2>&1 | tail -3
  ```
  Gate: ≥50 trials, zero corruption → AR-3 success criterion met.

- [ ] **Autopilot report** (generates plots + narrative)
  ```bash
  python3 scripts/autopilot/autopilot.py report
  # Outputs: autopilot_plots/ (hypervolume, quality trend, species contributions, failure breakdown)
  ```

- [ ] **Safety gate audit** — verify no accepted trial after 3+ consecutive failures
  ```bash
  python3 -c "
  import json
  for l in open('orchestration/autopilot_journal.jsonl'):
      t = json.loads(l)
      if t.get('accepted') and t.get('consecutive_failures', 0) >= 3:
          print(f'WARNING: trial {t[\"trial_id\"]} accepted after {t[\"consecutive_failures\"]} failures')
  " 
  ```

#### Phase 2: GEPA vs LLM Analysis (gates AP-21)

- [ ] **Mutation acceptance rates by type**
  ```bash
  python3 -c "
  import json
  from collections import Counter
  total, accepted = Counter(), Counter()
  for l in open('orchestration/autopilot_journal.jsonl'):
      t = json.loads(l)
      mt = t.get('mutation_type', 'unknown')
      total[mt] += 1
      if t.get('accepted'): accepted[mt] += 1
  for mt in sorted(total):
      rate = 100 * accepted[mt] / total[mt] if total[mt] else 0
      print(f'{mt}: {accepted[mt]}/{total[mt]} ({rate:.1f}%)')
  "
  ```
  Decision: If GEPA acceptance% > LLM by ≥10pp AND ≥3 GEPA trials on Pareto frontier → increase GEPA ratio to 100% (AP-21). Else keep 30/70.

- [ ] **Pareto frontier contributions by mutation source**
  ```bash
  python3 -c "
  import json
  state = json.load(open('orchestration/autopilot_state.json'))
  archive = state.get('pareto_archive', [])
  from collections import Counter
  sources = Counter(e.get('mutation_type', 'unknown') for e in archive)
  print(f'Pareto archive: {len(archive)} entries')
  for mt, n in sources.most_common():
      print(f'  {mt}: {n} ({100*n/len(archive):.0f}%)')
  "
  ```
  Same decision as above — also gates MH-4 (GEPA as search algorithm).

#### Phase 3: Routing Intelligence (gates RI-10 → RI-11)

- [ ] **Canary sample counts** — factual risk band distribution in seeding results
  ```bash
  python3 -c "
  import json, glob
  high, total = 0, 0
  for f in glob.glob('/mnt/raid0/llm/epyc-inference-research/benchmarks/results/eval/*.jsonl'):
      for l in open(f):
          try:
              e = json.loads(l)
              meta = e.get('metadata', {})
              band = meta.get('factual_risk_band', '')
              if band: total += 1
              if band == 'high': high += 1
          except: pass
  print(f'Total risk-scored: {total}, High-risk: {high} (need ≥50)')
  "
  ```
  Gate: ≥50 high-risk samples → sufficient for statistical test. If <50, extend canary window.

- [ ] **Enforce vs shadow factuality comparison** — extract from seeding checkpoint metadata
  ```bash
  # Factual risk scores are in ChatResponse.factual_risk_score/band, persisted to checkpoint metadata.
  # Compare pass rates for enforce-arm vs shadow-arm questions.
  # If p<0.05 factuality improvement + no latency regression → proceed to RI-11 (expand to 100%).
  # Else revert to shadow.
  ```

#### Phase 4: Context Folding (gates CF Phase 3c)

- [ ] **Quality monitor events**
  ```bash
  grep "COMPACTION_QUALITY_MONITOR\|compaction_quality" logs/agent_audit.log | wc -l
  # Need ≥3 events. Check for false positives:
  grep "COMPACTION_QUALITY_MONITOR" logs/agent_audit.log
  ```
  Gate: ≥3 events, <10% false positive rate → Phase 3c production-ready. Enable `role_aware_compaction` for AR-4.

- [ ] **SFT pair collection** (passive during AR-3)
  ```bash
  find /mnt/raid0/llm/tmp -name "compaction_sft_*.jsonl" 2>/dev/null | xargs wc -l 2>/dev/null
  # Target: ≥100 pairs for future Phase 2d fine-tuning
  ```

#### Phase 5: Dynamic Stack (gates DS-5 → DS-6)

- [ ] **StructuralLab model candidates tested**
  ```bash
  python3 -c "
  import json
  trials = []
  for l in open('orchestration/autopilot_journal.jsonl'):
      t = json.loads(l)
      if t.get('species') == 'structural_lab':
          trials.append(t)
  print(f'StructuralLab trials: {len(trials)}')
  for t in trials:
      print(f'  trial {t.get(\"trial_id\")}: action={t.get(\"action_type\")}, q={t.get(\"quality\",0):.2f}, accepted={t.get(\"accepted\")}')
  "
  ```
  Gate: ≥3 candidates tested. If any beats baseline on Pareto → recommend for DS-6 stack template.

#### Phase 6: ColBERT Reranker (gates S3 download)

- [ ] **Web research irrelevant page rate**
  ```bash
  cd /mnt/raid0/llm/epyc-inference-research
  python3 scripts/benchmark/analyze_web_research_baseline.py benchmarks/results/eval
  # Look for "Relevance Analysis" section.
  # >20% → proceed to S3. 10-20% → marginal. <10% → skip.
  ```
  See [colbert-reranker-web-research.md](colbert-reranker-web-research.md) § Post-AR-3 Analysis.

#### Phase 6b: SearXNG Backend Validation (if SEARXNG_DEFAULT=1 during AR-3)

- [ ] **SearXNG engine failure rate**
  ```bash
  grep "searxng unresponsive_engines" logs/*.log | wc -l
  # Count total queries with unresponsive engines.
  # >50% of queries with failures → SX-3 engine tuning needed.
  # <10% → engine set is reliable under load.
  ```

- [ ] **SearXNG vs DDG result quality**
  ```bash
  # Compare S1 irrelevant page rate with SearXNG vs without:
  grep "web_research relevance summary" logs/*.log
  # Look for backend=searxng vs backend=duckduckgo (logged in web_search() return).
  # If SearXNG irrelevant_rate > DDG irrelevant_rate: investigate engine tuning.
  # If SearXNG irrelevant_rate <= DDG: SX-6 swap confirmed.
  ```

- [ ] **SearXNG latency overhead**
  ```bash
  grep "elapsed_ms.*backend" logs/*.log
  # Compare SearXNG query latency vs DDG scraping latency.
  # SearXNG should be comparable or faster (JSON vs HTML parsing).
  ```

  See [`searxng-search-backend.md`](searxng-search-backend.md) SX-5/SX-6.

#### Phase 7: AM KV Compaction (if enabled during AR-3)

- [ ] **Compaction usage during AR-3** (only if autopilot issued compact requests)
  ```bash
  grep "compact\|compaction" logs/agent_audit.log | head -20
  # If no compaction was triggered, this is expected (passive-by-default).
  # If triggered: check quality metrics on compacted slots vs full-cache baseline.
  ```

#### Decision Summary Template

After completing all phases, fill in this table:

| Task | Metric | Threshold | Observed | Decision |
|------|--------|-----------|----------|----------|
| AR-3 health | Trials completed | ≥50 | ___ | pass/fail |
| AR-3 health | Useful changes accepted | ≥1 | ___ | pass/fail |
| AP-21 GEPA | GEPA acceptance% vs LLM | +10pp | ___% vs ___% | increase to 100% / keep 30-70 |
| MH-4 GEPA code | GEPA frontier share | >50% | ___% | adopt / keep LLM |
| SX-6 SearXNG swap | Engine failure rate | <10% queries affected | ___% | lock in SX-6 / revert to DDG |
| SX-6 SearXNG swap | Irrelevant page rate delta | ≤DDG baseline | ___% vs ___% | confirm / iterate SX-3 |
| RI-10 canary | High-risk samples | ≥50 | ___ | sufficient / extend window |
| RI-10 canary | Factuality F1 delta | p<0.05 | p=___ | RI-11 expand / revert shadow |
| CF Phase 3c | Quality monitor events | ≥3 | ___ | enable / defer |
| CF Phase 3c | False positive rate | <10% | ___% | pass / investigate |
| DS-5 models | Candidates tested | ≥3 | ___ | DS-6 ready / continue |
| ColBERT S1 | Irrelevant page rate | >20% | ___% | proceed S3 / deprioritize |
| AM compaction | Compaction quality | No degradation | ___ | production / defer |

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
**Related**: [`llama-cpp-v3-upstream-rebuild.md`](../completed/llama-cpp-v3-upstream-rebuild.md)

### Tasks Resolved

| Task ID | Source | Description |
|---------|--------|-------------|
| v3-smoke | [llama-cpp-v3-upstream-rebuild](../completed/llama-cpp-v3-upstream-rebuild.md) | All 4 production models load + generate at expected t/s |
| v3-features | [llama-cpp-v3-upstream-rebuild](../completed/llama-cpp-v3-upstream-rebuild.md) | Feature-specific tests: moe-n-expert, lookup, paged attention, slot erase, server health |
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

See full test matrix in [`llama-cpp-v3-upstream-rebuild.md`](../completed/llama-cpp-v3-upstream-rebuild.md) §Smoke Tests and §Feature-Specific Tests.

### Results (2026-04-10)

- [x] 4 production models load + generate — ALL PASS. Significant upstream speedups:
  - worker 30B-A3B: 38.6 t/s (baseline 39.0, -1%)
  - frontdoor 35B-A3B: 14.3 t/s (baseline 12.7, **+13%**)
  - coder 32B + draft: 21.7 t/s (baseline 10.8, **+101%**)
  - REAP-246B + draft: 12.0 t/s (baseline 8.0, **+50%**)
- [x] moe-n-expert works on REAP-246B — PASS
- [x] Paged attention — N/A as CLI flag. Our paged attention is registry-driven (`paged_attention.enabled_threshold_gb`), not a `--paged-attention` flag. Activated automatically for large models.
- [x] Slot erase — PASS. `POST /slots/{id}?action=erase` works (same as v2). Initial smoke test incorrectly used DELETE.
- [x] Server health returns HTTP 200 — PASS
- [x] Server completion returns HTTP 200 — PASS
- [x] `--lookup` — PASS. Present in v3 `llama-server` (only missing from `llama-cli`). No change needed.
- [x] NUMA throughput — 11.1 t/s on quarter (memory bandwidth shared with 27 running servers). Clean NUMA test not feasible without stopping stack. Smoke test model loads showed no regression.
- [x] Upstream Hadamard auto-rotation confirmed — PASS. No `LLAMA_ATTN_ROT_DISABLE` in server logs with `-ctk q4_0 -ctv f16`.
- [x] PPL (Coder-32B, -ctk q4_0 -ctv f16, wikitext2) — 6.80. No v2 wikitext2 baseline for direct comparison, but v2 Coder-32B PPL was 1.0034 on different dataset (short-context). No regression indicated.

### Production Binary Swap — DONE (2026-04-10)

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
  ├── ✅ PACKAGE B ──────────── DONE (2026-04-10, tool compression +4pp, WS-3 fix validated)
  │     │
  │     └── PACKAGE D ─────── AR-3 + RI-10 Canary + CF-3c + DS-5 (multi-day, full stack)
  │                            B done. Sentinels expanded 10→39. Baseline schema ready.
  │
  ├── ✅ PACKAGE C ──────────── DONE (2026-04-11, 30B summarizer, L3 sweet spot, TALE deferred)
  │
  ├── ✅ PACKAGE E ──────────── DONE 2026-04-06 (Hermes PASS, vision fixed 2026-04-08)
  │
  └── ✅ PACKAGE F ──────────── DONE 2026-04-10 (v3 binary swapped, coder +101%, REAP +50%)
```

## Remaining Execution Order

| Order | Work | Duration | Why this order / concurrency policy |
|-------|------|----------|--------------------------------------|
| 0 | **Parallel-dispatch integrity + live-affinity preflight** | ~30 min | Before any large run: confirm epyc-orchestrator main is `15350fe` or later plus the concurrency-metric patch if present, run the placement/migration unit subset, verify `AUTOPILOT_EVAL_CONCURRENCY` defaults to topology-safe `max_safe_concurrency(frontdoor)=3`, and confirm 4-way frontdoor traffic queues rather than placing on overlapping q0/q1. Also verify live llama-server process affinity against `NUMA_CONFIG` for every matrix role before trusting any matrix result. Abort the bulk train if this fails. |
| 1 | **J1** WP-2 placement state-machine gate | ~1h | First required inference gate. Proves safe fan-out (full + disjoint quarters + queued overlap) before any downstream task relies on parallel dispatch. |
| 2 | **J2** WP-3 forward-migration verification | ~2h | Verifies shipped session-handover migration semantics and sticky quarter affinity. This is not proactive mid-decode eviction; do not require an impossible in-flight full decode preemption. |
| 3 | **J3** WP-4 reverse-migration verification | ~30 min + analysis | Verifies solo-after-burst recovery before persistent parallel flags stay on. |
| 4 | **J4a/J4b** N-way contention-matrix closure | ~4-12h, runs alone | Required before using cross-role parallelism to accelerate the backlog. Enumerate every non-trivial all-lower-order-allowed active set up to the scheduler's maximum cross-role concurrency, bench it, write N-way verdicts, and fail closed until every candidate is either measured or explicitly pruned/excluded for this topology. |
| 5 | **J5** WP-6 within-role instance-pair matrix re-bench | overnight, runs alone | Completes the within-role side of the matrix. Must run alone because it launches controlled instance-pair benches. |
| 6 | **J10** URE-1 shadow logger | passive | Flip after the matrix gates are safe; it shapes no workload and can accumulate through all later traffic. |
| 7 | **J12** chat_template_kwargs wiring verification | ~2h | Cheap, high-leverage quality gate. Run before large quality-sensitive evals if wiring is still absent. |
| 8 | **J4** WP-5 ratification observation + **J9/J11** observe-only/paired gates where wired | 6-12h | Uses the newly verified parallel-dispatch path and completed matrix. J9 is observe-only; J11 runs per accepted mutation. Keep paired-eval attribution sequential unless explicit concurrent approval exists. |
| 9 | **J6** WP-7 24h rollout | 24h passive | Requires J4a/J4b/J5. J7/J8/J9/J10/J11 can co-run only when their own flags are observe/advisory, the N-way matrix allows the specific active set, and run metadata records concurrency. |
| 10 | **J7/J8** DCP/BEP inference gates | 3-4h each | Build missing live hooks first. J8 is the falsification gate and should run first within this harness cluster once wired. |
| 11 | **Package H/I/G residuals and D-tail** | variable | H7 before H5; I1 before I2; I3 independent. Standalone G benches can fill downtime, but do not co-run with J4a/J4b/J5 or any standalone throughput bench. |

**Completed historical ordering**: E/B/F/C and the completed G/AM/SEAL items remain documented below for provenance only. Do not use their April ordering as the current run order.

**Concurrent-run metric policy**: When `AUTOPILOT_EVAL_CONCURRENCY>1`, fan-out is allowed only inside a single trial's eval batch; do not run separate trials concurrently in one autopilot process. Individual request tokens/sec normally drops while aggregate batch throughput can improve. Every concurrent eval must record `speed_metric_mode`, `eval_concurrency`, median per-request t/s, aggregate batch t/s, and eval wall time. For concurrent eval batches, the SafetyGate/Pareto `speed` objective is aggregate batch t/s; the raw median request t/s is retained as audit metadata. This prevents the planner from treating safe same-trial fan-out as a regression while still exposing the per-instance slowdown for diagnostics. Cross-role bulk parallelism is stricter: pairwise-allowed is necessary but not sufficient; before J4b completion, unmeasured N-way active sets fail closed. After J4b completion for the current topology, there should be no unclassified N-way active set: each is measured `allow`, measured `block`, or explicitly pruned/excluded by a lower-order failure. This closed-world guarantee is scoped to the exact `topology_hash` / stack state measured by J4b; any future orchestration-stack, role, model, CPU binding, or server-launch topology change invalidates the matrix and requires re-derivation before using cross-role parallelism again.

**Baseline mutation hard rule**: Do not update production baselines, Pareto archives, regression thresholds, learned scheduling priors, routing speed priors, or trial-scheduling evidence from any run unless `speed_metric_mode`, `topology_hash`, and `matrix_status` are recorded and valid. Cross-role concurrent runs must also record the exact N-way active-set verdict or a same-trial within-role fan-out marker. Missing, stale, or inconsistent metadata means diagnostic-only quarantine.

**Live-affinity hard rule (2026-05-26 stack audit)**: `topology_hash` is necessary but not sufficient. It fingerprints the intended `NUMA_CONFIG`, not proof that the currently running llama-server processes were launched with the intended `taskset`/`numactl` prefix. Before J4/J5/J6 or any downstream concurrent run, compare each live port's `/proc/<pid>/task/*/status` `Cpus_allowed_list` union against the exact `NUMA_CONFIG[role].instances[idx]` CPU list. If any process has CPUs outside the expected set or misses expected CPUs, mark matrix status `diagnostic_only`, reload that role through `scripts/server/orchestrator_stack.py`, rerun the affinity check, and rerun all matrix rows involving the affected role/shape before baseline mutation or bulk parallelism.

**Frontdoor Half0/Half1 interpretation**: The dashboard's `Half0` cell for frontdoor is the current idx0 solo/full-speed anchor shape (`0-47,96-143`), not evidence that a validated second `Half1` frontdoor instance exists. Current certified frontdoor concurrency is via the existing q0-q3 quarter instances. Adding a dedicated frontdoor `Half1` replica is a new topology experiment, not a matrix-repair assumption: it requires a new server/port, explicit placement policy, fresh topology hash, isolated benchmarks comparing Half0+Half1 against the current Half0-plus-quarters policy, and a new matrix derivation before it can accelerate the bulk backlog.

**Autopilot dispatch-latency defaults (2026-05-26 hardening)**: before starting the long bulk train, run on an orchestrator containing `scripts/autopilot/phase_status.py`, the dashboard `autopilot_phase` panel, async auxiliary plot/digest scheduling, and contention-aware seed-role waves. Recommended environment:

```bash
AUTOPILOT_ASYNC_AUX=1
AUTOPILOT_ASYNC_WORKERS=2
AUTOPILOT_SEED_ROLE_CONCURRENCY=auto
AUTOPILOT_PAUSE_POLL_S=1
AUTOPILOT_HEALTH_BACKOFF_S=10
```

Use the dashboard phase panel to classify idle gaps before changing scheduling policy: stopped/down, paused, health backoff, planner prompt build, planner invoke, dispatch, journaling, checkpointing, or async artifact scheduling. Seeder fan-out is allowed only for background contention-matrix-safe role waves; missing/stale/unknown matrix evidence should collapse toward serial behavior. Request-level `trial_id`/`batch_id` propagation through benchmark HTTP callers is still deferred because those callers have high/critical GitNexus blast radius; the current phase heartbeat gives loop-level attribution without changing those contracts.

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

## Package G: Deferred Inference-Dependent Research Tasks

**Duration**: Variable (opportunistic — run during Package D downtime or after D completes)
**Stack required**: Individual model servers (like Package C)
**Depends on**: Nothing — independent research evaluation
**Status**: NOT STARTED — indexed here 2026-04-11 during handoff audit

These tasks are scattered across active handoffs and require inference compute but are not time-critical. Consolidated here so they can be scheduled opportunistically.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| G1 | Memento S2 feasibility | [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | Benchmark KV masking overhead on llama.cpp. Test if KV states from masked blocks preserve accuracy. | Any 8B+ model | ~4h |
| G2 | TriAttention/Expected Attention S1 | [triattention-kv-selection.md](triattention-kv-selection.md) | Validate Q/K concentration hypothesis on production models. Run KVPress Expected Attention vs baseline on Qwen2.5-Coder-32B. | coder_escalation | ~4h |
| G3 | TriAttention S2 stacking | [triattention-kv-selection.md](triattention-kv-selection.md) | Test KV selection + Hadamard q4_0 stacking. Quality cliff assessment under dual compression. | coder_escalation | ~4h |
| G4 | FlowSteer activation steering | [reasoning-compression.md](reasoning-compression.md) Tier 2 | Test nonlinear activation steering for concise reasoning on 30B-A3B worker. | worker_explore | ~6h |
| G5 | short-m@k voting baseline | [reasoning-compression.md](reasoning-compression.md) Tier 1 | Run k=3 parallel generations, majority vote. Measure accuracy vs single-shot on GPQA/math. | Any reasoning model | ~4h |
| G6 | v3 clean NUMA throughput | [llama-cpp-v3-upstream-rebuild.md](../completed/llama-cpp-v3-upstream-rebuild.md) | Isolated NUMA test (requires stopping production stack). Compare v3 vs v2 48t quarter throughput. | frontdoor or worker | ~1h |
| G7 | MiniMax M2.7 download + launch | Research intake (intake-328/329) | ✅ DOWNLOADING: Q8_0 (243GB) + UD-Q4_K_XL (141GB) from unsloth/MiniMax-M2.7-GGUF → `/mnt/raid0/llm/models/MiniMax-M2.7-GGUF/`. MoE 230B-A10B, 256 experts, 200K ctx. Launch with `--spec-type ngram-simple --draft-max 64`, `numactl --interleave=all`. No spec-dec (200K vocab, no compatible draft). Expected: Q4_K_XL ~12-16 tps w/ ngram, Q8_0 ~9-13 tps w/ ngram. | Standalone | ~2h |
| G7a | MiniMax M2.7 NUMA sweep | — | Sweep NUMA parallelization: 1×192t interleave vs 2×96t per-node vs 4×48t quarters. Model fits single node (~141-243GB vs ~560GB/node). 256-expert scatter pattern may favor interleave. | Standalone | ~3h |
| G8 | MiniMax M2.7 tool-calling | Research intake (intake-328/329) | Evaluate tool-calling reliability vs Qwen3 stack. Test orchestrator function-calling pipeline. | Standalone | ~4h |
| G9 | MiniMax M2.7 architect replacement eval | Research intake (intake-328/329) | **Goal: replace both architect_coding (Qwen3-Coder-480B, 3.79 tps) and architect_general (Qwen3-235B, 9.14 tps) with single M2.7.** Run standard eval suite (MATH, coding, general). Q4_K_XL is -6.0 pts from baseline (~22.8% more errors). M2.7 scored 56.22% SWE-Pro. Compare quality on architect-specific benchmarks. If quality ≥ both architects → consolidate to 1 model, freeing ~380GB RAM + simplifying stack. | Standalone | ~6h |

### Progress (updated 2026-04-13)

- **G1 (Memento S1)**: ✅ Feasibility CONFIRMED (2026-04-13). `llama_memory_seq_rm()` supports mid-sequence block eviction. Runtime validation passed (slot erase + continued generation). OpenMementos-228K downloading (`microsoft/OpenMementos`). S2 (LoRA) is next.
- **G2 (EA S1)**: ✅ Scaffold ready + proxy evaluation done (2026-04-13). KV compression at 50% removal: cosine=1.000 on NIAH tasks. Full KVPress integration needs compatible transformers version.
- **G3 (stacking)**: PENDING — depends on G2 full evaluation
- **AM P2**: ✅ Validated on Qwen2.5-7B (2026-04-13). 2x=1.000, 5x=0.906, 10x=0.807. Layer-adaptive strategy identified.
- **AM L1-L3b**: ✅ COMPLETE (2026-04-13). Beta bias kernel in llama.cpp-experimental, public `llama_memory_set_beta()` API, server `POST /slots/{id}?action=set-beta` endpoint, E2E test on Coder-32B f16. Full pipeline: Python compaction → HTTP beta injection → server decode. Next: quality comparison test.
- **SEAL cvector**: ✅ Pipeline validated (2026-04-13). Trained 28-layer concise reasoning vector on 7B. A/B: +1.8% tokens (minimal at 7B, real experiment targets 30B+). Fixed v3 GGML_OP_GLU build issue (stale libggml-cpu.so).

### New tasks for AR-3 fold-in assessment

The following medium-term tasks could piggyback on AR-3 stack sessions:

| Task | Can fold into AR-3? | Notes |
|------|---------------------|-------|
| **PPL sweep** (v3 baseline) | YES — run during AR-3 warmup/cooldown | `llama-perplexity` on wikitext2 for coder, frontdoor, worker, REAP. Independent of stack. ~1h total. |
| **AM P3** (AM vs EA head-to-head) | PARTIAL — needs model loaded, not full stack | Compare AM HighestAttnKeys-fast vs Expected Attention at 5x/10x/20x on same model. Python-only, ~4h. Can run during Package D downtime. |
| **RI-10 canary** | YES — this IS Package D | Extended to 2026-04-27, n=16/50 high-risk samples. AR-3 generates these samples. |
| **SEAL on 30B** | NO — needs dedicated server with cvector | Train + eval concise reasoning vector on Qwen3-Coder-30B-A3B. Separate from orchestrator stack. |
| **AM P2 on 32B** | ✅ DONE — E2E beta injection tested on 32B f16 | L1-L3b complete. Beta injection via server endpoint works on Coder-32B. Full compaction quality test next. |
| **ColBERT reranker S1 data** | YES — passive (already instrumented) | S1 relevance logging in `_web_research_impl()` fires on every web_research call. AR-3's 50-question `web_research` sentinel suite generates the data. After AR-3, grep logs for `web_research relevance summary` to measure irrelevant page rate. If >20%, proceed to S3 (model download). See [colbert-reranker-web-research.md](colbert-reranker-web-research.md). |
| **SearXNG backend validation (SX-5/SX-6)** | YES — activate via feature flag | SX-1/2/3/4 implemented (Docker service, `_search_searxng()`, settings.yml, telemetry). Activate `ORCHESTRATOR_SEARXNG_DEFAULT=1` during AR-3 warmup trial. The web_research sentinel suite (50q) validates SearXNG search quality under real query patterns. Telemetry: `searxng unresponsive_engines` logs engine failures; S1 relevance instrumentation measures page quality. If no regression on first warmup trial, lock in SX-6 swap. If regression, disable flag and iterate on SX-3 engine tuning. Post-AR-3: analyze engine failure rates + result quality delta vs DDG baseline. See [`searxng-search-backend.md`](searxng-search-backend.md) P12. |

### Prioritization (updated 2026-04-13)

- **G1 + G5 together**: Memento S1 DONE. G5 (short-m@k voting) still pending — run if any GPQA/math eval is scheduled.
- **G2 + G3 sequentially**: G2 proxy DONE (gate passed). Full KVPress evaluation + G3 stacking test pending. **AM compaction is now the primary path** — P2 results show structured attention compresses near-losslessly at 2-5x with layer-adaptive strategy.
- **G4**: Defer — FlowSteer library maturity unconfirmed.
- **G6**: Low priority — v3 smoke tests showed no regression.
- **G7**: ✅ COMPLETE (2026-04-17). All models downloaded and benchmarked. Q4_K_XL deleted (Q8 preferred for quality). M2.7 Q8 = 11.1 tps. Also swept: Qwen3.6 Q8 (27.4 tps), SG4-26b Q4 (42 tps), SG4-31b Q4 (9.0 tps), SG4-26b-MM Q8 (21.1 tps), Gemma4 E2B/E4B (deleted — no value).
- **G7a**: ✅ COMPLETE (2026-04-17). Full NUMA characterization with concurrent requests. Key findings: (1) --mlock + --membind required for multi-instance, (2) Q8 > Q4 for dense models < 40GB, Q4 > Q8 for large MoE, (3) concurrent benchmarks show ~40% less aggregate than serial sum. New deterministic `numa_sweep.py` with early stopping + scaling gates.
- **G8 + G9**: IN PROGRESS (2026-04-19). Quality benchmarks run with Claude-as-Judge scoring. Multiple iterations to fix model-specific serving issues (chat templates, reasoning mode, KV cache, repeat_penalty). Partial results: SG4-26b-MM 65.4%, SG4-31b 60.5%, M2.7 55.7%. Qwen3.6 still iterating (thinking model config). SG4-26b Q4KM deprecated (irrecoverable degeneration at Q4). Final run with `--reasoning off` in progress for all 4 remaining models.
- **G10 + G11 + G12**: AA-Omniscience hallucination calibration — can run per-model sequentially, ~6h total.

### G10-G12: AA-Omniscience Factual-Risk Calibration (2026-04-15 research intake)

**Source**: intake-381/intake-383 ([arxiv:2511.13029](https://arxiv.org/abs/2511.13029)), [routing-intelligence.md](routing-intelligence.md) Phase 4 calibration gap
**Dataset**: `ArtificialAnalysis/AA-Omniscience-Public` (600 Qs, Apache 2.0, already in HuggingFace cache)
**Goal**: Replace heuristic capability tiers in `factual_risk.py` (`_DEFAULT_ROLE_TIERS`: tier_1=0.6, tier_2=0.8, tier_3=1.0) with measured per-model hallucination rates

Scoring methodology (from paper): Omniscience Index = 50% accuracy + 50% (1 - hallucination_rate), where hallucination_rate = incorrect / (incorrect + partial + not_attempted). Answers graded as CORRECT/INCORRECT/PARTIAL_ANSWER/NOT_ATTEMPTED. Models prompted to say "I don't know" rather than guess.

| # | Task | Description | Models Needed | Effort |
|---|------|-------------|--------------|--------|
| G10 | AA-Omniscience: architect_general | Run 600 Qs through Qwen3-235B-A22B. Record per-domain accuracy + hallucination rate. Expect above-zero Omniscience Index. | architect_general (solo) | ~2h |
| G11 | AA-Omniscience: frontdoor + worker | Run 600 Qs through Qwen3-32B (frontdoor) and Qwen3-30B-A3B (worker). Compare hallucination rates to establish tier separation. | frontdoor, worker_general (sequential) | ~3h |
| G12 | Calibrate capability tiers | Use G10+G11 hallucination rates to compute empirical tier multipliers. Update `_DEFAULT_ROLE_TIERS` in `src/classifiers/factual_risk.py`. Augment with SimpleQA failures from seeding logs (`data/package_a/`, `data/package_b/`) for larger calibration set. | No inference — analysis only | ~1h |

**Implementation notes**:
- Prompt template from paper: `"You are answering questions about {domain}, and in particular {topic}. You will be given a question, answer with JUST the answer (no explanation). If you do not know the answer, or you need more context or tools to answer the question, be clear about this - it is better that you say this than get the wrong answer."`
- Grading: LLM-as-judge with 4-class output, or regex for exact-match answers (many are short factual: dates, names, section numbers)
- Results persist to `data/package_g/omniscience/` per model — incremental (one row per question)
- Key output: `{model}_{domain}_hallucination_rate.json` → feeds tier recalibration
- SimpleQA augmentation: grep seeding logs for `simpleqa` suite with `passed=False`, extract prompt+answer pairs, cross-reference with AA-Omniscience domains for combined calibration

**Exit criteria**:
- Per-model hallucination rate per domain computed
- Empirical tier multipliers differ from heuristic by >5% (otherwise heuristic was adequate)
- `factual_risk.py` `_DEFAULT_ROLE_TIERS` updated with measured values
- routing-intelligence.md Phase 4 calibration gap closed

## Package H: Research-Driven Inference Tasks (2026-04-12 research intake)

**Duration**: Variable (~12-16h total if sequential)
**Stack required**: Standard orchestrator stack (frontdoor + coder) for most; Ouro needs transformers separately
**Depends on**: Non-inference Tasks 10-11 (DSPy/GEPA install + dspy.RLM setup)
**Status**: NOT STARTED — indexed 2026-04-12 from research intake deep-dives

These tasks evaluate research-intake findings that require live inference. Ordered by dependency chain.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| ~~H1~~ | ~~GEPA frontdoor optimization (AP-19)~~ | ~~[autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P10~~ | → **Folded into Package D** (2026-04-12). GEPA integrated as PromptForge mutation type. AR-3 runs GEPA trials at 30% of PromptForge budget. | — | — |
| ~~H2~~ | ~~GEPA Full Program Adapter eval (AP-20)~~ | ~~[autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P10~~ | → **Folded into Package D**. Resolved by comparing GEPA vs LLM mutation acceptance rates in AR-3 journal. | — | — |
| ~~H3~~ | ~~PromptForge GEPA integration test (AP-21)~~ | ~~[autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P10~~ | → **Folded into Package D**. Decision from AR-3 data: if GEPA dominates Pareto frontier after 50+ trials → increase ratio to 100%. | — | — |
| H4 | dspy.RLM integration testing (AP-26) | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P11 | Test dspy.RLM for benchmark analysis via REPL exploration. Coder as main LM, frontdoor as sub_lm. **Post-AR-3** — controller change too risky mid-run. | coder + frontdoor | ~2h |
| H5 | RLVR eval tower validation (AP-27) + calibration baseline (EV-4) | [eval-tower-verification.md](eval-tower-verification.md) EV-4 + [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P11 | Run eval tower on Scoring Verifiers HE-R+ to establish ECE/AUC baseline (EV-4), then validate T0/T1/T2 as RLVR verification functions. **Depends on**: EV-1+EV-2+EV-3 (non-inference prep, now complete) + P7 Ouro results. **Post-AR-3** — modifies eval trust boundary. | full stack | ~4h |
| ~~H6~~ | ~~GEPA search algorithm eval (MH-4)~~ | ~~[meta-harness-optimization.md](meta-harness-optimization.md) Tier 2b~~ | → **Folded into Package D**. Pareto frontier contributions by mutation source analyzed from AR-3 journal. | — | — |
| H7 | Ouro-2.6B-Thinking benchmark (P7) | [research-evaluation-index.md](research-evaluation-index.md) P7 | Run MATH-500 + reasoning suite via transformers on CPU. NOT llama.cpp. Standalone. No stack conflict if needed, but not urgent — feeds H5 which is post-AR-3. | Ouro-2.6B (transformers, CPU-only) | ~4h |

### Prioritization (updated 2026-04-12)

- ~~**H1/H2/H3/H6**~~: **Folded into Package D** (2026-04-12). GEPA integrated into PromptForge as mutation type. AR-3 generates comparison data organically. See `scripts/autopilot/species/gepa_optimizer.py`.
- **H4 post-AR-3**: dspy.RLM testing. Controller architecture change — defer to AR-4.
- **H5 post-AR-3**: RLVR formalization + EV-4 calibration baseline. Non-inference prep (EV-1/2/3/6) now complete — ready for inference run. Defer to AR-4. Depends on H7.
- **H7 post-AR-3**: Ouro benchmark. Standalone (transformers CPU, no stack conflict). Feeds H5. Not urgent.

---

## Package I: Decision-Aware Routing Validation (post-AR-3)

**Duration**: ~2 days (DAR-3 exploration needs sustained traffic for counterfactual data)
**Stack required**: Full orchestrator stack
**Depends on**: DAR-1 regret analysis (DONE — 96% uniform Q, see scripts/analysis/dar1_regret_analysis.py) + DAR-2 code landing + Package H completion
**Status**: NOT STARTED — indexed 2026-04-15 from research deep-dive

These tasks modify routing behavior and need isolated measurement. Running exploration routing during Package H's research eval would contaminate both.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| I1 | DAR-3 SPO+ exploration | [decision-aware-routing.md](decision-aware-routing.md) DAR-3 | 10% epsilon-greedy exploration routing for counterfactual data collection. Convex SPO+ loss replaces TD update. | full stack | ~3-4 sessions |
| I2 | DAR-4 bilinear scorer A/B | [decision-aware-routing.md](decision-aware-routing.md) DAR-4 | Model-feature-conditioned Q vs current per-action Q-tables. Zero cold-start for new models. | full stack | ~2 sessions |
| I3 | EV-5 ThinkPRM-1.5B T2 | [eval-tower-verification.md](eval-tower-verification.md) EV-5 | Deploy ThinkPRM-1.5B-Q4KM for T2 process verification on uncertain questions. Cross-family constraint enforced. | ThinkPRM + eval stack | ~4h |

### Prioritization

- **I1 (DAR-3)**: Highest priority — generates counterfactual data needed for decision-aware training. Must run with sustained traffic.
- **I2 (DAR-4)**: Can run after I1 data collection. A/B comparison: bilinear scorer vs current Q-scorer on same traffic.
- **I3 (EV-5)**: Independent of I1/I2. Deploy ThinkPRM-1.5B, run T2 verification pass. Validate cross-family constraint (EV-6, already in code).

### DAR-1 Preliminary Results (2026-04-15)

Initial regret analysis on 7,211 routing decisions (Apr 10-14):
- 96% uniform Q-values — Q-scorer has barely learned preferences
- Selection score spread is non-trivial (median 0.107) — comes from cost/similarity, not Q-values
- 25% trivial spread (<0.01)
- Implication: DAR-2 contrastive training needs more routing memories. Consider seeding-driven memory accumulation before Package I.

---

## Package J: Within-Role Placement + Audit-Batch Inference Gates (2026-05-26)

**Duration**: ~1-3 days if sequenced; J5 (matrix re-bench) can run overnight
**Stack required**: Standard orchestrator stack; J1-J3 require `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1`; J3 additionally requires `ORCHESTRATOR_REVERSE_MIGRATION=1` set in the API env
**Depends on**: epyc-orchestrator main @ `15350fe` or later — both feature branches MERGED 2026-05-26 (`fe6805c` placement WP-0..WP-4 + WP-5 scaffold; `15350fe` intake-607 harness DCP/BEP/BSV/URE). 347 unit tests on main; all new code additive + flags default-OFF. No further branch merging needed before any J task.
**Status**: IN PROGRESS (claude 2026-05-26). Preflight PASS (67 tests). **J4a DONE** (`data/contention_matrix/bulk-2026-05-26-j4a/`). **J1 core PASS** — placement SM scales concurrent frontdoor 1.68×–1.91× across disjoint instances, no overlap; the `topology_overlap` queue is NOT observable via `/chat` (HTTP rate limiter 60rpm/10burst + a persistent dashboard client cap concurrent arrivals) → **J1 queue + J2/J3 migration verification re-vehicled to the autopilot eval-concurrency fan-out path** (the original WP-0 motivation). **J4b**: first full-instance pass exposed an operator-flagged methodology error → corrected to a **quarter-level disjoint-cpuset feasibility model** (`enumerate --feasibility`: 25 feasible / 32 `topology_infeasible`); quarter-level re-bench (`--safe-sampling`) IN PROGRESS (`data/contention_matrix/bulk-2026-05-26-j4b-feasible/`). **gemma4 worker_general full-instance crash FIXED** (uncaught PEG-parser throw → raw-content fallback; ik_llama.cpp `d84755dc`, rebuilt+redeployed+verified). Findings F1–F4 in [within-role-placement-state-machine.md](within-role-placement-state-machine.md); correction detail in [cross-role-nway-contention-matrix.md](cross-role-nway-contention-matrix.md). Remaining: finalize quarter-level matrix → J4c policy wiring → J5/J4/J6 → J7–J12.

**2026-05-27 Codex audit checkpoint**: this runbook is structurally correct, but several execution-state surfaces
need a consistency sweep before launching another nonstop bulk agent. Later certified-affinity results supersede
older manifest/handoff rows that still cite the `{frontdoor,ingest,vision}` `0.847` block as live proof; current
matrix/progress says that row was a bad-affinity artifact and remeasured `allow`. Runtime safety also needs two
code-level hardening items before baseline-eligible cross-role bulk parallelism: `ContentionGate.matrix_health()`
should check the live topology hash, and `SafetyGate.update_baseline()` should enforce the documented
`speed_metric_mode`/`topology_hash`/`matrix_status` baseline mutation rule. J2/J3 live migration verification
remains open; do not call J1-J3 complete until the dedicated probe produces evidence. See the 2026-05-27 progress
entry "Codex bulk-campaign audit + wrap-up skill checkpoint" for the full findings list.

Inference-gated verifications and observability runs for the within-role-placement-state-machine handoff. Also bundles the two sibling inference gates from the 2026-05-25 audit batch (DCP-6, BEP-2) because they share the same "needs autopilot-style eval workload" profile and benefit from one operator sitting + one cleared stack window. Add other-agent inference-gated items under this Package (or a successor) for shared sequencing.

### Priority-zero sequencing (RUN FIRST)

> **J1 → J2 → J3 → J4a/J4b/J5 must run BEFORE any downstream inference Package that relies on parallelism** (D-tail, G/H/I, J4/J6-J9, or other-agent items appended at the end). Reason: J1-J3 enable the within-role WP-2/3/4 parallelization flags, while J4a/J4b/J5 finish the cross-role and within-role matrix evidence needed to decide which concurrent active sets are actually throughput-positive. Once verified and left on, every subsequent autopilot/eval/bench task benefits from safe concurrency without corrupting throughput metrics or scheduling priors.
>
> Equivalent ordering rule for the global Execution Order table: insert **`J1, J2, J3, J4a, J4b, J5`** ahead of any not-yet-started inference Package that could use shared-stack concurrency. Don't backfill `Package E/B/F/C` ordering — those already completed.
>
> If the operator wants to mix flag-enablement validation with downstream work in the same sitting, the safe interleave is: J1 (~1h) → J2 (~2h) → J3 (~30-min profile) → J4a dry-run enumeration → J4b/J5 matrix benches in isolated slots → enable flags persistently → proceed with anything else.

### Parallel-dispatch integrity preflight (abort-on-fail)

Before starting the bulk train, run this preflight on the orchestrator checkout:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python3 -m py_compile src/backends/concurrency_aware.py src/scheduling/placement.py scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py scripts/autopilot/autopilot.py
pytest -q tests/unit/test_eval_tower_concurrency_metrics.py \
  tests/unit/test_topology_concurrency.py \
  tests/unit/test_dispatch_placement_state_machine.py \
  tests/unit/test_per_region_locks_migration.py \
  tests/unit/test_load_transition_migration.py \
  tests/unit/test_reverse_migration.py \
  tests/unit/test_migration_transaction.py
```

Gate expectations:
- `AUTOPILOT_EVAL_CONCURRENCY` unset resolves to `max_safe_concurrency(frontdoor)=3`; any explicit override above 3 is a deliberate stress test, not a production default.
- Four concurrent frontdoor requests show exactly 3 active safe placements and one queued/denied for `topology_overlap`; no q0/q1 overlap with full is allowed.
- Concurrent eval results include `speed_metric_mode`, separate median request t/s, and aggregate batch t/s metadata. If a run predates that telemetry, compute the two metrics manually from logs and mark the trial analysis as concurrency-audited before using it for scheduling decisions.
- Live process affinity matches `NUMA_CONFIG` for all roles used by J4/J5/J6. Minimum check: enumerate live llama-server ports, map port->role/index from `NUMA_CONFIG`, union all thread `Cpus_allowed_list` values for each PID, and assert exact equality with the expected CPU set. Record the result in the execution manifest as `live_affinity_verified: true` plus `affinity_artifact`.
- Specific 2026-05-26 audit hazard: frontdoor and ingest affinities were observed correct, but `worker_general` and `vision_escalation` quarter ports were observed with wrong live affinity when their special launcher paths used `_numa_prefix(role)` instead of `_numa_prefix(role, numa_instance)`. After applying/reloading the launcher fix, rerun the affinity check and treat pre-fix worker/vision matrix rows as diagnostic until re-measured.
- If any of these fail, stop. Do not run D-tail/G/H/I/J4+ on top of a suspect dispatcher, stale live affinity, or unlabelled concurrent speed metric.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| J1 | WP-2 placement state machine gate | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 2 | Enable `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1`, fan 4 concurrent requests at frontdoor, verify per-region-locks dashboard shows 3 active (full + 2 disjoint quarters) + 1 queued with `reason=topology_overlap`. Aggregate t/s ≥ 3-way Phase 1 baseline; p99 ≤ +20% vs serial. | frontdoor (Qwen3.6-35B-A3B Q8 ×5) | ~1h |
| J2 | WP-3 forward-migration verification | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 3 | Forward migration is shipped on the existing session-handover trigger (transactional, policy-gated), not as proactive mid-decode eviction. Verify: under sustained 2+ concurrent traffic with session handover on full, MigrationTransaction completes (state_history shows planned→saving→restoring→verified→source_erased→committed within budget), old session's NEXT request lands on the assigned quarter (sticky affinity preserved), and aggregate t/s under continuous fan-out approaches the matrix's 4-quarters baseline once all requests are placed on disjoint cpusets. | frontdoor (Qwen3.6-35B-A3B Q8 ×5) | ~2h |
| J3 | WP-4 reverse-migration verification | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 4 | Enable `ORCHESTRATOR_REVERSE_MIGRATION=1`, run a 30-min mixed traffic profile (alternating bursts of 4 concurrent and solo turns) on frontdoor. Verify reverse-migration log/stat evidence increments, per-session migration counts respect the cap (default 5), and solo-after-burst per-request latency regresses ≤+10% vs solo-only baseline. The Prometheus counter named in the original Phase 4 plan is not wired as of this audit; do not block on it unless a metrics patch lands first. | frontdoor (Qwen3.6-35B-A3B Q8 ×5) | ~30-min profile + analysis |
| J4a | XCM-1 N-way contention candidate enumeration | [cross-role-nway-contention-matrix.md](cross-role-nway-contention-matrix.md) + `scripts/server/contention_matrix.py` | Add/verify an enumeration mode that produces every non-trivial candidate N-way active set from the live role topology up to the scheduler's maximum cross-role concurrency. Prune trivial supersets containing any pair that is `block`, below `default_floor`, unknown, or same-role blocked. Keep candidates where all lower-order constituents are allowed under **background/bulk** policy; these are not certified until J4b measures them. Emit a manifest with `candidate_roles`, lower-order evidence, prune reason, topology hash, and `live_affinity_verified` status. | no inference if dry-run; full stack metadata | ~1h code/dry-run |
| J4b | XCM-2 N-way contention matrix re-bench | [cross-role-nway-contention-matrix.md](cross-role-nway-contention-matrix.md) + `orchestration/contention_matrix.yaml` | Run the J4a candidate manifest alone on the host after live affinity is clean. Measure triples first; skip any quad/superset containing a failing triple. For each measured N-way set, compute `seq_aggregate_tps`, `parallel_aggregate_tps`, ratio, CV across 3 runs, and verdict. Update `contention_matrix.yaml` with `n_way:` entries and `excluded_n_way:` entries for candidates pruned by known-bad pairs/triples. Gate: for the current topology hash and verified live affinity, every non-trivial N-way active set is classified as measured `allow`, measured `block`, or explicitly excluded; there must be no residual `unmeasured` bucket. Future stack/topology changes are out of scope and require matrix re-derivation. Any pre-affinity-fix row involving `worker_general` or `vision_escalation` quarters is diagnostic-only until rerun. | full production stack | ~4-12h, runs alone |
| J4c | XCM-3 N-way policy wiring / scheduling guard | [cross-role-nway-contention-matrix.md](cross-role-nway-contention-matrix.md) + `src/scheduling/contention_gate.py` | If runtime bulk scheduling can launch multiple cross-role tasks at once, teach it to consult the `n_way` matrix for the exact active-set union before treating an all-pairwise-allowed N-way combo as certified. Operator policy before J4b completes is fail-closed. Operator policy after J4b completes is closed-world for the current topology: launch only active sets classified in `n_way` as `allow`; treat `block`, `excluded_n_way`, missing entries, or topology-hash mismatch as queue/serialize. | no extra inference after J4b | ~2-4h |
| J4 | WP-5 ratification observability run | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 5 | With WP-2 + WP-3 + WP-4 enabled, and after J4a/J4b/J5 matrix gates complete, run autopilot for ~6-12h and collect: (a) per-role concurrency histogram, (b) full vs quarter utilization, (c) migration counts forward + reverse, (d) N-way active-set IDs and matrix verdicts for any cross-role overlap. Decide per-role `placement_policy` values: keep `solo_prefer_full` for autopilot-dominant low-concurrency roles; switch worker_general to `burst_prefer_quarters` if concurrent load grows; consider `full_disabled` for any role where full is wasted memory. Edit NUMA_CONFIG, commit, restart, re-run. | full production stack | ~12h observation + ~1h analysis |
| J5 | WP-6 matrix re-bench (within-role instance pairs) | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 6 | Extend `epyc-orchestrator/scripts/server/contention_matrix.py` (Phase F harness from cross-role-bw-aware-routing) to sweep within-role pairs `full+q0, full+q1, full+q2, full+q3, q0+q1, q0+q2, q0+q3, q1+q2, q1+q3, q2+q3` for each role with ≥2 instances. Update `orchestration/contention_matrix.yaml` schema with `instance_pairs` block + `topology_hash` + affinity artifact. Gate: live affinity exact-match before sampling; CV ≤ 5% across 3 runs; runtime fails closed on topology/YAML hash mismatch. **Stack-conflict risk** — runs llama-bench across many configurations; must run alone. Current repair priority is to rerun `worker_general` and `vision_escalation` after validated reload because their quarter-launch affinity was suspect; frontdoor's current certified path remains Half0 solo anchor plus q0-q3 quarters. | All multi-instance roles (frontdoor, worker_general, ingest_long_context, vision_escalation) | ~overnight (~8-12h) |
| J6 | WP-7 production rollout + 24h gate | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 7 | Switch `_eval_concurrency()` default from static `max_safe_concurrency(frontdoor)` to "matrix-aware" — query the gate at startup for the role's max sustainable concurrency given measured ratios (uses J4b + J5 data). Document operator override path in `wiki/autopilot-tuning.md`. Run a 24-hour autopilot pass; compare quality, median request t/s, aggregate batch t/s, and wall-clock throughput vs Phase 0 baseline; verify dashboard shows quarters actively rotating; assert `contention_timeout_count` stays at baseline. | full production stack | ~24h passive + ~1h analysis |
| J7 | DCP-6 delegation context pre-assembly eval | [delegation-context-preassembly.md](delegation-context-preassembly.md) DCP-6 | Measure on a delegation-heavy workload: prefill tokens, end-to-end latency, top-up count, bundle-build latency, downstream answer quality, hallucinated-file references, context-contamination failures vs reactive-discovery baseline. Run offline replay over historical tasks first (validates bundle size/coverage), then the inference gate. Default-off flag stays off until results justify. | frontdoor + worker_coder (delegation-heavy roles) | ~3-4h |
| J8 | BEP-2 batched edit CPU-latency A/B | [batched-edit-parallel-apply.md](batched-edit-parallel-apply.md) BEP-2 | Head-to-head bench: batch-edit mode vs interleaved Root LM loop on a coding/edit workload. Measure round-trip count, total prefill tokens, end-to-end latency, bundle/context size (if DCP enabled), patch-parse failure rate, apply failure rate, verification pass rate, quality. **Falsification gate** — if batch mode doesn't cut latency at equal quality, stop the BEP track. Offline replay first; then inference. | worker_coder + frontdoor | ~3h |
| J9 | HLE-4 harness metrics observe-only run | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) HLE-4 + [meta-harness-optimization.md](meta-harness-optimization.md) HLE-1/2/3 | Extend `EvalResult` + journal JSONL with `harness_metrics`, `oracle_adequacy`, `metric_schema_version` (non-inference code change first); retain the concurrency telemetry fields (`speed_metric_mode`, `eval_concurrency`, `median_request_tps`, `aggregate_tps`, `eval_wall_s`). Then run autopilot for N trials with metrics in **observe-only mode** (no Pareto promotion). Analyze: separation accepted-vs-rejected, correlation with future regressions, missingness rate, p95 metric-extraction cost. Cheap-kill: metric that never separates or has missingness >20% stays diagnostic, doesn't promote to Pareto co-objective. | full autopilot stack | ~6-12h observation |

### Sequencing notes

- **Preflight → J1 → J2 → J3 → J4a/J4b/J5 → J4** is the new parallelization block. J1-J3 prove dispatcher safety; J4a/J4b close cross-role N-way contention; J5 closes within-role instance-pair contention; J4 observes policy choices on the now-characterized stack.
- **J4b and J5 matrix benches** must run ALONE on the host and honor `feedback_no_concurrent_inference`. They are the highest stack-conflict risk in this Package and are required before using cross-role concurrency to speed up the remaining inference backlog.
- **Affinity repair outranks matrix reuse**: if live affinity differs from `NUMA_CONFIG`, the matrix is stale even when `topology_hash` matches. Reload/fix the affected role first, then rerun all matrix evidence involving that role/shape before J4/J6 or downstream parallel bulk work.
- **Optional frontdoor Half1 exploration is out-of-band**: do not add or assume a second half frontdoor inside the repair path. If pursued, create a separate topology experiment after current matrix repair: add Half1 port/config, validate affinity, measure Half0+Half1 and Half0/Half1+quarters against current q0-q3 policy, update `topology_hash` and rederive the matrix before use.
- **J6 (production rollout)** is 24-hour passive once flipped; can start as soon as J4a/J4b/J5 are done and any J4c policy wiring needed for bulk scheduling is in place.
- **J7, J8, J9** are independent of the WP implementation work but should run after J1-J3 so they inherit safe fan-out. J7/J8 are autopilot-style evals against the production stack and can interleave with J6's 24h pass only after their missing live hooks are built and the concurrent-run metrics are labelled. J9 is observe-only, but it should still record `speed_metric_mode`, median request t/s, and aggregate batch t/s so later scheduling does not learn from mixed semantics.

### Execution manifest template

Before launching the nonstop bulk train, create a run manifest with one row per task/gate. A JSONL file is preferred for machine checking; this table defines the required fields.

| Field | Required | Notes |
|-------|----------|-------|
| `run_id` | yes | Stable id shared by logs, artifacts, and progress notes. |
| `task_id` | yes | Package task id such as `J1`, `J4b`, `H7`, `I1`. |
| `allowed_concurrency_mode` | yes | `serial`, `same_trial_eval_fanout`, `cross_role_matrix_allow`, `observe_only`, or `isolated_bench`. |
| `required_topology_hash` | yes for concurrent/bench tasks | Must match runtime before launch. |
| `live_affinity_verified` | yes for concurrent/bench tasks | Boolean. True only after every live llama-server PID in scope has thread affinity exactly matching `NUMA_CONFIG` for its role/index. |
| `affinity_artifact` | yes for concurrent/bench tasks | Path to captured port->pid->expected-cpus->observed-cpus evidence. |
| `matrix_status` | yes | `not_required`, `preclosure`, `closed_world`, `stale`, or `diagnostic_only`. |
| `flags` | yes | Feature flags and env vars used for the task. |
| `command` | yes | Exact command or script invocation. |
| `output_path` | yes | Primary artifact directory/file. |
| `journal_quarantine_rule` | yes | When results must be kept out of baselines/Pareto/scheduling priors. |
| `pass_fail_gate` | yes | Concrete metric threshold or artifact condition. |
| `next_action` | yes | Continue, rerun, serialize downstream, stop, or open follow-up. |

Minimum manifest example:

```json
{"run_id":"bulk-2026-05-26-j4b","task_id":"J4b","allowed_concurrency_mode":"isolated_bench","required_topology_hash":"<hash>","live_affinity_verified":true,"affinity_artifact":"data/contention_matrix/<run_id>/live_affinity.json","matrix_status":"preclosure","flags":{"feedback_no_concurrent_inference":true},"command":"python scripts/server/contention_matrix.py ...","output_path":"data/contention_matrix/<run_id>/","journal_quarantine_rule":"diagnostic_only_until_closed_world","pass_fail_gate":"all candidate_sets measured or excluded; CV <= 0.05; live affinity exact-match","next_action":"J5 if pass; stop if topology drift, affinity drift, or unmeasured bucket remains"}
```

### Baseline mutation rule

Baseline mutation is opt-in, never implicit. A run is baseline-eligible only if:

- `speed_metric_mode` is present and matches the evaluation shape.
- `topology_hash` matches the manifest and matrix artifact.
- `live_affinity_verified=true` for any run that depends on the contention matrix.
- `matrix_status` is `closed_world` for cross-role parallel runs, or `not_required` for serial/same-trial-only runs.
- Same-trial EvalTower fan-out records `eval_concurrency`, median per-request t/s, aggregate batch t/s, and eval wall time.
- Cross-role concurrent runs record the exact active-set verdict id and launch only `allow` sets.

Everything else is diagnostic-only. Diagnostic-only data can be summarized in progress reports, but it must not update production baselines, Pareto archives, regression thresholds, learned scheduling priors, routing speed priors, or future trial scheduling evidence.

### Resume protocol

If the long-running session is interrupted:

1. Read the latest `progress/YYYY-MM/*.md` entry and the run manifest.
2. Verify the current orchestrator git sha, stack state, and topology hash before relaunching anything.
3. Inspect the last produced artifact, not just the final log line or process exit status.
4. Rerun only idempotent preflight steps automatically: py_compile, unit subset, health checks, topology hash capture, and J4a dry-run enumeration.
5. Continue from the first incomplete gate in the manifest.
6. Keep partially completed throughput benches quarantined unless every sample, CV, ratio, verdict, topology hash, and artifact path is present.
7. If topology hash, live affinity, or matrix status changed, stop cross-role parallelism and return to J4a/J4b before downstream bulk work.

### Other agents' inference-gated work — add here

This Package is designed to absorb additional inference-gated items from parallel agents so one operator-sitting window clears multiple. Append rows below (or open a Package K for a separate window). Suggested format: same table columns; surface dependencies in this sequencing section if any.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| J10 | URE-1 routing-uncertainty calibration | [decision-aware-routing.md](decision-aware-routing.md) URE-1 | Enable `ORCHESTRATOR_URE_UNCERTAINTY_SHADOW_LOG=1`; passively collect shadow routing-uncertainty records over normal traffic; compute ECE/AUC for "would escalation help?", abstention precision/recall, per-suite calibration drift. Pre-enforcement gate: ECE ≤ eval-tower P8 target + abstention precision > baseline escalation precision + ≤10% latency regression. **Shadow-only** — needs no dedicated window. Prereq: URE-1 shadow logger wired (approval_record schema done in `src/trace/harness_schema.py`). | none extra (shadow on existing frontdoor/escalation traffic) | passive collection + ~1h analysis |
| J11 | BSV-2 behavior-signature differential testing | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) BSV-2 | Before promoting a mutation, run new-vs-old paired on the same sentinels (sequential under identical model snapshot preferred; parallel only if explicitly approved per `feedback_no_concurrent_inference`); compare behavior_signature diff severity (benign/watch/blocking) + scalar score; gate accept on both. Catches silent Pareto-win regressions a scalar misses. Prereq: BSV-1 signature wired into archive accept-path + paired-eval lane (compute done in `src/behavior_signature.py`). | autopilot eval stack | paired eval per candidate mutation |
| J12 | chat_template_kwargs registry-driven wiring verification | epyc-orchestrator `cac4148` (chat_template_kwargs passthrough merge) + [x-mas-text-routing.md](x-mas-text-routing.md) | Data-plane shipped 2026-05-20: `src/backends/openai.py` now passes `request.extra["chat_template_kwargs"]` to llama-server's chat-completions endpoint. **Wiring follow-up**: add the small code change that auto-populates `request.extra["chat_template_kwargs"]` from `model_registry.yaml`'s per-role defaults (currently every caller has to set it manually). Then run the cheap-kill empirical comparison from the merge commit body — 15-task mixed-domain probe on frontdoor (Qwen3.6-35B Q8) + architect (Qwen3.5-122B): pre-wiring baseline vs post-wiring with `enable_thinking=False`. Gate: frontdoor +30pp or better, architect +15pp or better, ingest_long_context unchanged (its registry entry is untouched — thinking-on is load-bearing). | frontdoor + architect_general + ingest_long_context | ~1h wire + ~1h verify |

**Sequencing of the appended items (intake-607 residual gates):**
- **J10 (URE-1) is shadow-only** — flip the flag and let it accumulate during ANY of J1–J9 or Package I traffic; it shapes no workload and needs no dedicated slot. Analyze once enough decisions accrue.
- **J11 (BSV-2)** runs per-mutation inside the autopilot accept loop; co-runs naturally with J9's autopilot observation window.
- Both are gated on their wiring landing (URE-1 shadow logger; BSV-1 accept-wire). Schemas + pure algorithms are on main (`15350fe`). DCP-6/BEP-2/HLE-4 are already covered above as J7/J8/J9 — no duplication.

### Per-gate conditional workflows + mitigation policies (intake-607 gates J7–J11 — READ BEFORE RUNNING)

Each gate is a **decision point**, not just a measurement: run → branch on the result → apply the mitigation. Deep specs are in the owning handoffs (linked); this is the operator decision tree so the run can proceed in one sitting without round-trips.

**Pre-run wiring status** (none is in production until wired AND its gate passes; all flags default-OFF):
- **J10 / URE-1**: shadow logger **WIRED** (`ORCHESTRATOR_URE_UNCERTAINTY_SHADOW_LOG`) on main (merged 2026-05-26) — runnable now.
- **J7 / DCP-6**: **DCP-1 + DCP-2 discovery + DCP-3 ast-codemap DONE** on main (merged 2026-05-26) (`context_discovery.py` `assemble_delegation_bundle()` end-to-end, 11 tests). Needs only **DCP-4** — the reviewed dispatcher *advisory* seed-bundle attach (wire the orchestrator's ColGREP + workspace reader into `assemble_delegation_bundle`).
- **J8 / BEP-2**: needs the `_execute_turn` batch divergence + BEP-4 runner + BEP-5 sandbox (`ORCHESTRATOR_BATCH_EDIT_MODE`). Parser/prompt/schema/pure-applier done. **Full deferred-wiring spec: [`batched-edit-parallel-apply.md`](batched-edit-parallel-apply.md) § "Deferred live-wiring spec (build before J8)".**
- **J9 / HLE-4**: needs HLE-1 metric computation over real traces + `EvalResult`/journal extension (observe-only). Schema done.
- **J11 / BSV-2**: needs BSV-1 signature wired into the archive accept-path + paired-eval lane. Compute (`compute_behavior_signature`, `diff_signatures`) done.

**J8 — BEP-2 batched-edit A/B (falsification gate; run FIRST in the harness cluster):**
- ✅ batch cuts end-to-end latency ≥15% AND quality within −1pp AND parse-failure ≤5% AND apply-failure ≤2% (whole-repo verify) → proceed to **BEP-3** (autopilot task-class knob); keep flag available, default-off until BEP-3 finds where batch wins.
- ⚠️ latency win but quality −1..−3pp OR parse/apply failures 5–15% → do NOT promote; loop back to BEP-1 prompt/parser hardening; flag stays off.
- ❌ no latency win OR quality < −3pp OR failures >15% → **STOP the BEP line** (this is the falsification gate); flag default-off permanently; record NEGATIVE in the handoff + intake-605.
- **Mitigation**: flag-off = instant rollback; **every apply is in a sandbox/worktree (BEP-5), never production files, until whole-repo verify passes AND accept**; stale-base rejection; parse=None/invalid → fall back to the normal REPL loop (zero behavior change).

**J7 — DCP-6 delegation pre-assembly eval (run advisory-first: bundle attached, reactive discovery still on):**
- ✅ prefill+latency down AND quality ≥ baseline AND top-up rate ≤20% → keep advisory; consider seed-bundle-primary mode after a second confirm.
- ⚠️ quality flat but top-up rate >20% → packer under-selecting; tune discovery depth / ColGREP top-k / budget; re-run.
- ❌ quality drop OR no latency improvement → keep reactive discovery; shelve pre-assembly; flag off.
- **Mitigation**: flag-off; advisory mode never removes reactive discovery; top-ups always allowed (no hard firewall); bundle freshness (repo_sha/content_sha256) re-checked per delegation.

**J9 — HLE-4 harness-metrics observe-only (no Pareto promotion during the run):**
- Per metric: promote to a Pareto co-objective/guardrail ONLY if it separates accepted-vs-rejected (AUC ≥ target) AND correlates with future regressions AND missingness ≤20%; else keep diagnostic-only.
- **Mitigation**: observe-only first; low-signal/low-confidence metrics never gate; oracle-adequacy flags shortcut-prone suites so they can't drive promotion.

**J10 — URE-1 calibration (shadow → enforce; J10 itself only collects + analyzes):**
- ✅ ECE ≤ eval-tower P8 target AND abstention precision > baseline escalation precision AND ≤10% shadow latency regression → enable uncertainty-routed escalation (separate enforce flag) + optionally URE-3 (uncertainty as a frozen-label routing feature).
- ❌ any gate fails → stay shadow-only; recalibrate (re-weight components / threshold) on a frozen shadow set; do NOT enforce.
- **Mitigation**: calibration-precedes-enforcement; shadow→enforce is a separate flag flip; frozen shadow-calibration set; re-run calibration after any DAR-3/DAR-4 change to avoid a feedback loop.

**J11 — BSV-2 differential testing (mutation accept gate; per candidate mutation):**
- `benign` → auto-accept; `watch` (route/tool changed, outcomes equal) → accept + log; `blocking` (prior-pass sentinel regressed, forbidden shortcut appeared, or cost guardrail crossed) → **REJECT, do not promote**; if it touches a shared subsystem → BSV-3 conflict-ledger review.
- **Mitigation**: gate accept on BOTH scalar regression AND signature severity; partial-confidence signatures cannot certify `benign`; git-committed revert remains the backstop.

---

## Package K: Audit-Batch Code-Ready Inference Gates (2026-05-27)

**Origin**: the 2026-05-27 `/research-intake` of agent-oss (intake-610–613) prompted an audit of `research-evaluation-index.md` + `pipeline-integration-index.md` for work that is *not* inference-gated. All code scaffolding was implemented that session (see `progress/2026-05/2026-05-27.md` + `research/deep-dives/2026-05-27-agent-memory-cluster.md`). The RUNS below are now unblocked — code has landed, models/datasets are downloaded or have a one-line fetch noted. **Independent of Package J** — pick up in any stack window; none block J.

**Stack required**: varies per row (most need only individual model servers, not the full orchestrator).

| Task | Code prereq (DONE this session) | Inference run / gate |
|------|----------------------------------|----------------------|
| **K-RAG-1** — KB-RAG hybrid-signal eval (K7 + K9/K10) | `kb_rag.query()` recency+rerank params (`src/retrieval/kb_rag.py`); `src/retrieval/cross_encoder.py`; cross-encoder ONNX on disk at `/mnt/raid0/llm/models/ms-marco-minilm-l6-v2-onnx`; 21 unit tests pass | Run the K7 HotpotQA/LoCoMo retrieval-recall harness (`internal-kb-rag.md` K7) sweeping `KB_RAG_RECENCY_WEIGHT` / `KB_RAG_RECENCY_SIGMA_DAYS` / `KB_RAG_RERANK=1` / `KB_RAG_RERANK_WEIGHT`. Gate: any config beats the MaxSim-only baseline on doc-recall@{3,5,10} by >2pp (Flywheel ~1pp noise floor). Decide default weights. |
| **K-EMB-1** (P9) | granite-97m-r2 bench Phase A (GGUF + comparator deploys) — see `granite-97m-r2-bench-plan.md` | Phase B: throughput + nDCG@10/recall@10/50 + 32K probe + end-to-end-with-reranker. Gate: dense first-stage retriever decision (granite vs BGE-M3 vs defer). |
| **K-EVAL-1** (EV-3 → H5/EV-4) | `scoring_verifiers` suite adapter landed (`scripts/benchmark/scoring_verifiers_adapter.py`, registered in `dataset_adapters.py`+`suites.py`) | EV-4 calibration baseline (ECE/AUC) on Scoring-Verifiers — **already tracked as H5**; the EV-3 adapter prereq is now DONE. One-line dataset fetch: `snapshot_download('nvidia/Scoring-Verifiers', repo_type='dataset', local_dir='/mnt/raid0/llm/data/eval/scoring_verifiers')`. |
| **K-MEM-1** (P3b) | `tulving_episodic` suite adapter + deterministic F1 scorer landed (`scripts/benchmark/tulving_episodic_adapter.py`); 77 unit tests | Run 20ch (10K-token, 456 QA) on production models; report Simple-Recall + Chronological-Awareness. Dataset: Figshare DOI 10.6084/m9.figshare.28244480 → `/mnt/raid0/llm/data/eval/tulving_episodic/`. |
| **K-DIV-1** (EV-8) | `diversity_metrics` + 5 `EvalResult` fields wired (`scripts/autopilot/diversity_metrics.py` + `safety_gate.py`; `src/` side pre-existing); 50 tests | Baseline diversity pass on 4 production roles; populate the SafetyGate two-tier WARN/REJECT thresholds (semantic-embedding-agreement needs an embedder pass). |
| **K-ROPE-1** (P10.2) | `scripts/benchmark/rope_position_probe.py` (`--dry-run` verified) | 5 models × 4 context lengths (4K/8K/16K/32K), 100 samples/cell ≈ 100 min. LOW priority, **bulk-pickup eligible**. Record collapse-point per model into the RoPE deep-dive appendix. |

**Run-command note**: each adapter is registered as a named suite, so existing seeding/eval harnesses pick them up by suite name (`scoring_verifiers`, `tulving_episodic`). K-RAG-1 + K-ROPE-1 are standalone scripts (env-var-swept / `--context-length` per cell). Per `feedback_speed_verify_via_llama_bench` + `feedback_no_concurrent_inference`: the user/campaign runs these manually with per-run approval — code is prepared, not executed.

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
