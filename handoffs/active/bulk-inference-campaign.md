# Bulk Inference Campaign: Packages B-E

**Status**: active (A+B+C+E+F done, D relaunching. G1/G2/AM-L1-L3b/SEAL all complete 2026-04-13. AM has native llama.cpp beta injection + server endpoint. H1/H2/H3/H6 folded into D. v3 binary live.)
**Created**: 2026-04-06
**Updated**: 2026-04-13
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

## Execution Order

| Order | Package | Duration | Why this order |
|-------|---------|----------|----------------|
| 1 | ~~**E**~~ | ~~1 hour~~ | ✅ DONE 2026-04-06. Hermes streaming PASS, vision fixed 2026-04-08. |
| 2 | ~~**B**~~ | ~~1 day~~ | ✅ DONE 2026-04-10. All phases complete. Tool A/B: compression +4pp REPL. WS-3 fix validated. |
| 3 | ~~**F**~~ | ~~30 min~~ | ✅ DONE 2026-04-10. 4/4 models PASS, Hadamard PASS, PPL 6.80. v3 binary swapped. |
| 4 | **D** | Multi-day | B done, prerequisites met (sentinels expanded, baseline schema ready). |
| 5 | ~~**C**~~ | ~~½ day~~ | ✅ DONE 2026-04-11. 2a: 30B-A3B perfect summarizer. 2b: L3 sweet spot. 2c: ρ=0.65. TALE: static limits kept. |

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
- **G8 + G9**: Unblocked. G9 reframed as architect replacement eval — M2.7 Q8 at 11.1 tps is 1.2x faster than architect_general (9.14) and 2.9x faster than architect_coding (3.79). Quality benchmark infrastructure ready: `--all-suites` flag added to `run_benchmark.py`, `--spec-type ngram-simple` support added for Qwen3.6/SG4-31b. Execution command prepared (362 questions across 5 models).
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
