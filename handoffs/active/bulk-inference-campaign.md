# Bulk Inference Campaign: Packages B-E

**Status**: active (Package A complete, Package E done 2026-04-06, Packages B-D pending)
**Created**: 2026-04-06
**Updated**: 2026-04-06
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
| TrimR eval | [research-evaluation-index](research-evaluation-index.md) P0 | Run `eval_trimr.py` on math/gpqa suites with full/think-strip/trimr strategies |
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

- [ ] **RI-9**: Pareto-optimal risk thresholds identified (factuality vs cost vs latency tradeoff curve)
- [ ] **TrimR**: Per-suite accuracy delta within 2% of full reasoning at ≥30% token savings
- [ ] **Difficulty**: Recalibrated thresholds show predictive spread (easy success > medium success > hard success)
- [ ] **Omega**: Identifies ≥2 suites where reasoning tokens are net-negative (accuracy drops with more thinking)
- [ ] **Tool A/B**: Token savings ≥15% without quality degradation (accuracy delta < 1%)

---

## Package C: Context Folding Eval Batch

**Duration**: ~half day (~160 inference calls)
**Stack required**: Individual model servers (NOT full orchestrator)
**Depends on**: None (independent of B)
**Status**: BLOCKED — all 3 eval scripts need implementation before this package can run (see Prerequisites)

### Tasks Resolved

| Task ID | Source | Description |
|---------|--------|-------------|
| CF Phase 2a | [context-folding-progressive.md](context-folding-progressive.md) | Summarizer quality across 3 model tiers (1.5B / 7B / 32B) |
| CF Phase 2b | [context-folding-progressive.md](context-folding-progressive.md) | Free-zone compression threshold sweep (5 levels × 20 logs) |
| CF Phase 2c | [context-folding-progressive.md](context-folding-progressive.md) | Helpfulness calibration — LLM Δ_k ground truth vs heuristic scores |

### Models Required

| Model | Role | Port | NUMA Config | Purpose |
|-------|------|------|-------------|---------|
| Qwen3-1.5B | worker_fast | any free | 1×24t | 2a: lowest-tier summarizer |
| Qwen3-Coder-30B-A3B Q4KM | worker_explore | any free | 1×48t | 2a: mid-tier summarizer + 2b: compaction engine |
| Qwen2.5-Coder-32B Q4KM | coder_esc | any free | 1×48t | 2a: high-tier summarizer |

These run one at a time on a single NUMA quarter — no concurrent instances needed.

### Commands

**Phase 2a — Summarizer quality eval** — **BLOCKED: script does not exist yet**:
```bash
cd /mnt/raid0/llm/epyc-inference-research

# BLOCKER: eval_summarizer.py must be created before Phase 2a can run.
# Spec: context-folding-progressive.md Phase 2a
# Input: 20 real session logs from /mnt/raid0/llm/tmp/session_*.md (250 available)
# Method: Run Tier 2 consolidation via each model tier (1.5B, 7B, 32B)
# Scoring: Claude-as-Judge on faithfulness (0-3), compression ratio, info retention (0-3)
# Output: CSV with per-model-tier scores
#
# python3 scripts/benchmark/eval_summarizer.py \
#   --traces-dir /mnt/raid0/llm/tmp \
#   --model-ports 8072,8071,8070 \
#   --output /mnt/raid0/llm/epyc-orchestrator/data/package_c/summarizer_quality.csv
```

**Phase 2b — Free-zone compression sweep** — **BLOCKED: live eval not implemented**:
```bash
cd /mnt/raid0/llm/epyc-inference-research

# BLOCKER: evaluate_compaction() raises NotImplementedError.
# Dry-run works (--dry-run produces mock results), but live eval needs implementation.
# Implementation: load trace → compact at target ratio via model → probe task → Claude-as-Judge score.

python3 scripts/benchmark/eval_compaction_sweep.py \
  --traces-dir /mnt/raid0/llm/tmp \
  --levels 1,2,3,4,5 \
  --output /mnt/raid0/llm/epyc-orchestrator/data/package_c/compaction_sweep.csv
```

**Phase 2c — Helpfulness calibration** — **BLOCKED: live eval not implemented**:
```bash
cd /mnt/raid0/llm/epyc-inference-research

# BLOCKER: evaluate_helpfulness() raises NotImplementedError.
# Dry-run works (--dry-run produces mock results), but live eval needs implementation.
# Implementation: leave-one-out segment scoring → measure accuracy delta (Δ_k).

python3 scripts/benchmark/eval_helpfulness_calibration.py \
  --traces-dir /mnt/raid0/llm/tmp \
  --weight-sweep \
  --output /mnt/raid0/llm/epyc-orchestrator/data/package_c/helpfulness_calibration.csv
```

### Prerequisites

- [ ] **BLOCKER 2a**: `eval_summarizer.py` does not exist — must be created per CF Phase 2a spec
- [ ] **BLOCKER 2b**: `eval_compaction_sweep.py` live eval raises `NotImplementedError` — needs implementation
- [ ] **BLOCKER 2c**: `eval_helpfulness_calibration.py` live eval raises `NotImplementedError` — needs implementation
- [x] Session trace files in `/mnt/raid0/llm/tmp/session_*.md` — **250 available** (need 20)
- [ ] Model servers started individually via `orchestrator_stack.py start --include-warm <role>`

**Unblocking Package C requires a code session before inference can begin.** The three scripts share a common pattern (load trace, call model, judge quality) — implement one and the others follow.

### Expected Output

| File | Content |
|------|---------|
| `data/package_c/summarizer_quality.csv` | Per-model-tier scores (faithfulness, compression, retention) |
| `data/package_c/compaction_sweep.csv` | Quality vs compression ratio at 5 levels |
| `data/package_c/helpfulness_calibration.csv` | Heuristic vs LLM-based Δ_k correlation |

### Success Criteria

- [ ] **CF Phase 2a**: Clear quality ranking across tiers — 32B > 7B > 1.5B on faithfulness. Identify minimum-viable tier.
- [ ] **CF Phase 2b**: Free-zone boundary identified. Expected: L1-L2 (20-40%) near-lossless, L3 (60%) is the knee.
- [ ] **CF Phase 2c**: Heuristic helpfulness scores correlate with LLM Δ_k (Spearman ρ > 0.5)

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
| RI-10 | [routing-and-optimization-index](routing-and-optimization-index.md) P6 | 🔄 ACTIVE since 2026-04-06 (25% enforce on frontdoor, 3-day canary). Package D extends monitoring via AR-3 traffic. |
| CF Phase 3c | [context-folding-progressive.md](context-folding-progressive.md) | Quality monitor validation on real multi-turn sessions |
| DS-5 | [routing-and-optimization-index](routing-and-optimization-index.md) P7 | Model exploration via StructuralLab species |

### Config Changes (before launch)

**`classifier_config.yaml`** — already set as of 2026-04-06:
```yaml
factual_risk:
  mode: "canary"          # already live (changed from "shadow" on 2026-04-06)
  canary_ratio: 0.25      # 25% of frontdoor requests get enforce
  canary_roles: [frontdoor]
# No config change needed for Package D — canary is already active.
# Decision after 3-day canary (by ~2026-04-09): keep canary, expand to RI-11, or revert.
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

| Gate | Threshold | Action |
|------|-----------|--------|
| Quality floor | avg < 2.0/3.0 | Reject trial |
| Regression | Δq < -0.05 vs baseline | Reject trial |
| Per-suite regression | Δq < -0.1 any suite | Reject trial |
| Catastrophic shrinkage | >50% file size reduction | Reject + revert |
| Code mutation validation | Syntax + imports + public names | Reject on failure |
| Consecutive failures | 3× T0 fail | Auto-rollback |
| Worktree isolation | All PromptForge mutations in temp worktree | Auto-reject on timeout |

### Prerequisites

- [ ] Package B results analyzed (risk thresholds finalized, difficulty signal validated)
- [ ] AR-3 sentinel pool expanded beyond current 10 T0 questions (saturated at q=3.0)
- [ ] `autopilot_baseline.yaml` updated with Package B metrics

### Success Criteria

- [ ] **AR-3**: ≥50 trials completed without corruption. ≥1 useful change accepted (Pareto-improving).
- [ ] **RI-7 re-run**: Canary data produces ≥500 enforce vs ≥1500 shadow decisions. Compare factuality F1, escalation rate, cost. Result is statistically significant (p < 0.05) or confirms NS with adequate power.
- [ ] **RI-10**: 3 days of canary data. No latency regression (p95 within 10% of shadow baseline). No accuracy drop on frontdoor. Decision: proceed to RI-11 (expand) or revert to shadow.
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
- [ ] **Vision P0 OpenAI-compat**: FAIL — `content: str` in `OpenAIMessage` schema rejects multipart content arrays. Needs `str | list` union type. Bug: `src/api/models/openai.py:14`
- [ ] **Vision P0 `/v1/vision/analyze`**: PARTIAL — Endpoint reachable (200 OK), but VL describe fails: `--no-display-prompt` flag invalid for VL llama-server. Bug in vision analyzer CLI args.
- [x] **`orchestrator_stack.py --only`**: PASS — New flag works, only touches specified roles, preserves healthy servers

### Bugs Found

1. **OpenAI-compat multipart content**: `src/api/models/openai.py:14` — `content: str` needs `content: str | list` to support `[{"type": "text", ...}, {"type": "image_url", ...}]` format
2. **VL analyzer flag**: Vision analyzer passes `--no-display-prompt` which is invalid for Qwen2.5-VL llama-server. Likely in `src/vision/analyzers/` VL describe module.

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
  ├── PACKAGE C ──────────── CF Eval Batch (~½ day, individual models)
  │                            CF Phase 2a/2b/2c — independent of B
  │
  └── ✅ PACKAGE E ──────────── DONE 2026-04-06 (Hermes PASS, vision partial)
                               2 bugs filed: OpenAI multipart content + VL analyzer flag
```

## Execution Order

| Order | Package | Duration | Why this order |
|-------|---------|----------|----------------|
| 1 | ~~**E**~~ | ~~1 hour~~ | ✅ DONE 2026-04-06. Hermes streaming PASS, vision partial (2 bugs filed). |
| 2 | **B** | ~1 day | **NEXT** — all scripts ready. Needs full stack exclusive. Results feed D. |
| 3 | **D** | Multi-day | Depends on B. Longest run. |
| 4 | **C** | ~½ day | **BLOCKED** — needs code session to implement 3 eval scripts first |

**Parallelization note**: E can run during any other package (uses separate ports 8086/8087). C's code implementation can happen in parallel with B/D inference runs (different repos, no stack conflict).

**Recommended approach**: Run E → B → D immediately. Implement Package C scripts during or after B/D runs, then execute C when scripts are ready.

---

## Telemetry Collection Plan

| Package | Data Streams |
|---------|-------------|
| B | Progress JSONL (difficulty + risk shadow), seeding results JSON (3-way scores), TrimR JSONL (reasoning traces), SLO report, anomaly report, tool compression delta |
| C | Summarizer quality CSV, compaction sweep CSV, helpfulness calibration CSV, SFT pairs JSONL (if `compaction_training_data` flag on) |
| D | Autopilot journal (TSV + JSONL), Pareto archive, canary telemetry (enforce vs shadow quality delta), quality monitor events, StructuralLab results |
| E | Vision API response logs, streaming validation results |

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
