# Search-R1 Reward Design for Web Research

**Status**: IMPLEMENTED — Steps 0–4 complete, Step 5 blocked on #03
**Created**: 2026-03-03
**Assessed**: 2026-03-03
**Priority**: P1
**Effort**: Medium
**Depends On**: None at top level (only Step 5 blocked on `03-session-scratchpad-memory.md`)
**Source**: [Search-R1 (arxiv.org/pdf/2602.19526)](https://arxiv.org/pdf/2602.19526)

## Research Review

### Search-R1: Training Deep Research Agents
**Authors:** Yinuo Xu, Shuo Lu, Jianjie Cheng et al.

Systematic framework for training deep research agents across three dimensions: prompt engineering (query formulation), reward design (objective functions reflecting task success), and policy optimization (RL for decision-making). Demonstrates that integrated attention to all three dimensions substantially improves multi-hop reasoning and retrieval-augmented performance.

**Orchestrator Relevance: HIGH.** Our orchestrator performs exactly this type of multi-step research (web_research tool, deep search). Key applicable insights:
- **Prompt-reward-policy trinity**: We currently optimize prompts (prompt resolution system) but have no formal reward signal or policy learning
- **Reward design for information-seeking**: Could guide how we evaluate web_research quality beyond simple F1
- **Balancing exploration vs exploitation**: Directly relevant to our routing decisions — when to try new workers vs stick with known-good ones
- **Multi-hop reasoning training**: Our deep search synthetic data generation could adopt their methodology

### The Three Dimensions
1. **Prompt engineering**: Query formulation quality — how well does the model decompose a complex question into searchable sub-queries?
2. **Reward design**: Objective functions — factual accuracy, source coverage, answer completeness, retrieval efficiency
3. **Policy optimization**: RL for deciding when to search more vs synthesize — exploration/exploitation tradeoff

## Existing Infrastructure

These existing components should be extended rather than rebuilt:

| Component | Location | Relevance |
|-----------|----------|-----------|
| `seeding_rewards.py` | `epyc-orchestrator/scripts/benchmark/` | `success_reward()`, `compute_3way_rewards()`, `compute_tool_value()`, `detect_escalation_chains()` — extend with web_research dimensions |
| `debug_scorer.py` | `epyc-inference-research/scripts/benchmark/` | 6 scoring methods (exact_match, multiple_choice, code_execution, f1, substring, programmatic) — F1 already works for HotpotQA/SimpleQA/GPQA |
| `quality_detector.py` | `epyc-orchestrator/src/classifiers/` | Repetition/garbling/emptiness detection — could integrate with web_research output quality |
| `question_pool.py` | `epyc-inference-research/scripts/benchmark/` | 53K questions across 19 suites — needs web-research-specific suite |
| `dataset_adapters.py` | `epyc-inference-research/scripts/benchmark/` | Suite adapters with scoring thresholds — needs web-research adapter |
| `q_scorer.py` | `epyc-orchestrator/orchestration/repl_memory/` | Q-value TD learning — reward dimensions feed here |
| `retriever.py` | `epyc-orchestrator/orchestration/repl_memory/` | `get_best_action()` at line ~369 — selection policy swap point |
| `routing.py` | `epyc-orchestrator/src/api/routes/chat_pipeline/` | `HybridRouter.route()` — decision gateway |
| `research.py` | `epyc-orchestrator/src/tools/web/` | web_research implementation — add intermediate data logging |
| `ToolInvocation` | `epyc-orchestrator/src/tool_registry.py:158` | `.result` field holds full web_research return dict (data capture source) |
| `ChatResponse` | `epyc-orchestrator/src/api/models/responses.py:31` | Response model — `web_research_results` field added |
| `chat_delegation.py:1178` | `epyc-orchestrator/src/api/routes/` | Delegation path `get_invocation_log()` — web_research extraction added |

## References

- [Search-R1 paper](https://arxiv.org/pdf/2602.19526)
- [DeepSeek-R1](https://arxiv.org/abs/2401.10774) — RL-based reasoning model referenced by Search-R1
- Web research tool: `epyc-orchestrator/src/tools/web/research.py`
- Prompt resolution: `epyc-orchestrator/src/resolver.py`
- Seeding infrastructure: `epyc-inference-research/scripts/benchmark/`
- Question pool: `epyc-inference-research/scripts/benchmark/question_pool.py`

## Missing Items (Prerequisites)

### M1: Web-research-targeted question pool suite
No suite specifically targets web_research. Need questions that:
- Require current/factual information (not in training data)
- Have verifiable ground truth answers
- Force the model to use web_research (can't answer from parametric knowledge alone)
- HotpotQA and SimpleQA are closest, but models can often answer without web search

### M2: Intermediate data capture — RESOLVED
web_research results now captured end-to-end:
- `ToolInvocation.result` extracted in `repl_executor.py` and `chat_delegation.py`
- Surfaced via `ChatResponse.web_research_results` (url+title only, bounded size)
- Stored in `RoleResult.web_research_results` during seeding
- Rewards/telemetry computed per-config in `_compute_3way_metadata()`

### M3: Baseline metrics
Before adding reward signals, we need baseline data:
- What % of questions currently trigger web_research?
- What's the pass rate for questions where web_research was used vs not?
- What's the typical fetch/synthesis success rate?

### M4: Dependency scope correction — RESOLVED
Original handoff had top-level `Depends On: #03` which would block all work. Only Step 5 requires scratchpad memory — Steps 0-4 are independent. Corrected.

## Implementation Steps

### Step 0: Establish baselines (NEW)
- **Where**: `epyc-inference-research/scripts/benchmark/seed_specialist_routing.py`
- Run seeding with web_research logging enabled to capture current state:
  - % of questions triggering web_research tool calls
  - Pass rate for questions where web_research was used vs not
  - Typical fetch/synthesis success rate per web_research call
  - Average pages fetched, pages synthesized, elapsed time
- Store baseline metrics in checkpoint JSONL for later comparison

### Step 1: Define reward signals for web_research quality (REVISED)
- **Where**: `epyc-orchestrator/scripts/benchmark/seeding_rewards.py` (extend existing)
- **Extend** existing `success_reward()` and `compute_3way_rewards()` — do NOT build from scratch
- Design multi-dimensional reward, each with concrete metric:
  - **Factual accuracy**: Leverage existing F1/exact_match/substring scorers in `debug_scorer.py`. For web_research tasks, compare synthesized answer against ground truth.
  - **Source diversity**: Unique domain count from fetched URLs. Content overlap ratio via simhash or jaccard on synthesis outputs. Penalize single-source answers.
  - **Retrieval efficiency**: Quality-gated metric — fewer fetches to arrive at correct answer = higher reward. Only meaningful when answer quality is held constant (correct answers only).
  - **Answer completeness**: For multi-hop questions, fraction of sub-questions addressed. Use existing F1 scoring as proxy.
- Reference `quality_detector.py` for output quality checks (repetition, garbling, emptiness)

### Step 1.5: Add web-research-specific questions to question pool (NEW)
- **Where**: `epyc-inference-research/scripts/benchmark/question_pool.py`, `dataset_adapters.py`
- Curate or generate questions that require web lookup:
  - Recent events post training cutoff
  - Multi-source corroboration tasks
  - Fact-checking claims requiring external verification
- Add `web_research` suite to question pool with appropriate adapter
- Define scoring thresholds (likely F1-based, similar to SimpleQA)

### Step 2: Add reward scoring to seeding pipeline (REVISED)
- **Where**: `epyc-orchestrator/scripts/benchmark/seeding_rewards.py`, `seeding_eval.py`
- Extend `seed_specialist_routing.py` with reward computation
- **Add intermediate data capture** (M2): web_research tool call arguments and results must be captured in `RoleResult`:
  - Queries issued to web_search
  - URLs fetched and fetch success/failure
  - Synthesis content per page
  - Timing breakdown
- Log per-task reward breakdown alongside existing pass/fail metrics
- Store in structured format in checkpoint JSONL (format already supports arbitrary metadata)

### Step 3: Score root LM multi-turn query strategy (REVISED — was "query decomposition scoring")
- **Reframed**: Query decomposition is the ROOT LM's job, not the web_research tool's. web_research takes a single `query` string. The root LM decides how to break complex questions into sub-queries and calls web_research multiple times.
- Score the root LM's query formulation strategy:
  - Number of web_research calls per task
  - Query refinement patterns (did queries narrow/adapt based on earlier results?)
  - Information gain per query (did each call contribute new facts to the answer?)
- Requires tracing multi-step reasoning across the root LM's turns, not modifying the tool
- Feed decomposition quality into the reward signal from Step 1

### Step 4: Add reward signals to existing MemRL (REVISED — was "exploration/exploitation policy")
- **Where**: `epyc-orchestrator/orchestration/repl_memory/q_scorer.py`, `retriever.py`
- MemRL currently uses pure greedy (argmax on Q-values) with rule-based fallback below confidence threshold
- Add web_research reward dimensions to Q-value updates:
  - When a task completes, inject web_research quality rewards into the TD learning update
  - New reward dimensions become additional features for Q-value estimation
- Key files for integration:
  - `retriever.py` line ~369: `get_best_action()` — selection logic
  - `q_scorer.py`: Q-value storage and TD updates
  - `routing.py` line ~749: `HybridRouter.route()` — decision point
- Exploration/exploitation policy changes (Thompson sampling, UCB) deferred — requires more data first. Current greedy + fallback is adequate until reward signals are producing meaningful differentiation.

### Step 5: Integrate with scratchpad memory (BLOCKED on #03)
- **Depends on**: `03-session-scratchpad-memory.md`
- Use scratchpad insights as signal for reward computation
- "Did the model discover and record the key insight?" → reward component
- Track insight quality across turns
- **Interim**: Even without scratchpad, can check if model's final answer contains information from web_research syntheses (simple containment check)

## Acceptance Criteria

- [x] Baseline web_research quality metrics established (Step 0)
- [x] Multi-dimensional reward function defined with concrete metrics, extending existing `seeding_rewards.py`
- [x] Web-research-specific question suite added to question pool (50 questions, 5 categories)
- [x] Intermediate web_research data captured in seeding `RoleResult`
- [x] Reward scoring integrated into seeding pipeline
- [x] Root LM query strategy quality measurable across multi-turn usage
- [x] Reward dimensions feeding into MemRL Q-value updates
- [ ] At least one seeding run completed with new reward signals
- [ ] Comparison against Step 0 baselines documented
