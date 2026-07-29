# DeepPlanning: Benchmarking Long-Horizon Agentic Planning with Verifiable Constraints — Deep Dive

- **Source**: https://arxiv.org/abs/2601.18137
- **Version surveyed**: v1.0 (2026-01-26), with v1.1 leaderboard update (2026-03-03)
- **Authors**: Yinger Zhang, Shutong Jiang, Renhao Li, Jianhong Tu, Yang Su, Lianghao Deng, Xudong Guo, Chenxu Lv, Junyang Lin (Qwen team, Alibaba)
- **Dataset**: https://huggingface.co/datasets/Qwen/DeepPlanning (Apache 2.0, 104 MB, 240 tasks)
- **Evaluation code**: https://github.com/QwenLM/Qwen-Agent/tree/main/benchmark/deepplanning
- **Project page**: https://qwenlm.github.io/Qwen-Agent/en/benchmarks/deepplanning/
- **Intake verdict delta**: `worth_investigating` holds. Novelty is in the *evaluation methodology* (rule-based, fully deterministic, multi-granularity scoring), not in the tasks themselves. The benchmark's strongest contribution to EPYC is empirical evidence for reasoning-mode routing and a transferable scoring architecture for the eval tower.

---

## 1. Evaluation Framework — Complete Architecture

DeepPlanning targets a blind spot in agentic benchmarks: most measure step-level tool-calling success (did the agent use the right API?), not global constrained optimization (did the agent produce a plan that satisfies all constraints simultaneously?). The key insight is that high constraint-level scores do not predict case-level accuracy — a single temporal overlap or budget violation invalidates an otherwise-strong plan.

### 1a. Task Domains

| Domain | Tasks | Languages | APIs | Avg DB Records/Task | Core Challenge |
|--------|-------|-----------|------|---------------------|----------------|
| Travel Planning | 120 | Chinese + English | 9 | 7,708 | Multi-day itinerary generation with time, budget, and preference constraints |
| Shopping Planning | 120 | English only | 15 | 171 | Combinatorial optimization: select products + apply coupons to minimize cost under attribute constraints |

**Travel Planning APIs** (9 tools):
1. `query_train_info` — Train schedules and prices
2. `query_flight_info` — Flight schedules and prices
3. `query_hotel_info` — Hotel availability, ratings, amenities
4. `query_road_route_info` — Driving/transit routes and durations
5. `query_attraction_details` — Opening hours, closure dates, admission
6. `query_restaurant_details` — Cuisine, ratings, hours, price range
7. `recommend_attractions` — Filtered attraction recommendations
8. `recommend_restaurants` — Filtered restaurant recommendations
9. `search_location` — Geographic search and proximity

**Shopping Planning APIs** (15 tools):
1. `search_products` — Full-text product search
2. `filter_by_brand` — Brand-specific filtering
3. `filter_by_color` — Color attribute filter
4. `filter_by_size` — Size attribute filter
5. `filter_by_applicable_coupons` — Find coupon-eligible items
6. `filter_by_range` — Price/rating range filter
7. `sort_products` — Sort by price, rating, popularity
8. `get_product_details` — Full product metadata
9. `calculate_transport_time` — Shipping estimate
10. `get_user_info` — User profile and preferences
11. `add_product_to_cart` — Cart add operation
12. `delete_product_from_cart` — Cart remove operation
13. `get_cart_info` — Cart state query
14. `add_coupon_to_cart` — Apply coupon
15. `delete_coupon_from_cart` — Remove coupon

The API design is critical: tools are hierarchically structured to encourage multi-step agent interaction. A model cannot solve a shopping task in one API call — it must search, filter, compare prices, check coupon applicability, compute cart totals, and optimize. Travel tasks require querying transit times between locations, checking opening hours against planned visit times, and verifying budget constraints across multi-day itineraries.

### 1b. Difficulty Levels (Shopping)

| Level | Constraint Complexity | Key Challenge |
|-------|----------------------|---------------|
| Level 1 | Straightforward item matching | Attribute filtering (brand, color, size) |
| Level 2 | Price-range requirements added | Must compare prices, check budget caps |
| Level 3 | Coupon timing constraints | Global optimization: item-coupon combinations that minimize total cost; stacking rules create NP-hard-like search spaces |

Travel tasks scale by itinerary length (2-7 days), with composite scores declining monotonically as trip length increases.

---

## 2. Solution-Centric Reverse Generation — Task Construction Pipeline

The core methodological contribution is a three-stage "reverse generation" pipeline that guarantees solvability. Instead of generating random tasks and hoping solutions exist, DeepPlanning starts from valid solutions and works backward to generate tasks.

### Stage 1: Database and Toolbox Design

**Travel**: Real-world data sourced from public APIs (Fliggy for flights/trains, Amap for routes, web search for restaurants/attractions). Covers Chinese tourist cities with full transportation, accommodation, dining, and attraction records. Average of 7,708 database records per task provides realistic search-space complexity.

**Shopping**: Synthesized product data with controlled complexity. Product attributes (brand, color, size, price, rating) are generated to create specific difficulty levels. Coupon rules are designed to create non-trivial optimization problems at Level 3.

### Stage 2: Layered Task Generation (Three Steps)

**Step 2a — Base Skeleton Generation**:
- Travel: Select departure city, destination city, travel dates. This defines the search space.
- Shopping: Select a thematic item set (e.g., "spring travel clothing" or "home electronics").

**Step 2b — Personalized Constraint Injection**:
- Travel examples: "must book a flight departing after 7:00 AM", "recommend the highest-rated restaurant near the hotel", "total budget under 8,000 yuan"
- Shopping examples: "find a ShockWave product with rating > 4.7", "total spending must exceed 4,500 yuan", "all items must ship within 3 days"
- These constraints are injected into the query in natural language but are paired with programmatic verification functions.

**Step 2c — Environment Constraint Injection**:
- Travel: Attractions closed on the planned dates (forcing rescheduling), limited flight availability (forcing train alternatives), restaurant hours conflicting with attraction visits (forcing reordering)
- Shopping: Coupon-stacking rules that create exactly one optimal combination, product-coupon eligibility creating hidden constraints
- **The database is adjusted** to ensure exactly one optimal solution exists. Candidate records are added, removed, or modified so that the constraints are satisfiable but non-trivially so.

### Stage 3: Manual Quality Control

Human experts review every LLM-generated query for:
1. Natural language fluency (no robotic constraint listings)
2. Unambiguous logic (every constraint has a single interpretation)
3. Reachable solutions (verified by running the solution path against the database)

**Solvability guarantee**: Because tasks are reverse-engineered from valid solutions, every task is provably solvable. The solution serves as the ground-truth answer key. This is the critical difference from forward-generation benchmarks where tasks may be unsolvable or have ambiguous optimal solutions.

---

## 3. Scoring Methodology — Complete Breakdown

DeepPlanning uses a three-level scoring hierarchy: dimension-level, composite-level, and case-level. All scoring is **fully deterministic and rule-based** — no LLM-as-judge, no human evaluation, no subjective rubrics.

### 3a. Commonsense Score (Travel Planning Only)

8 dimensions, 21 checkpoints. Each dimension scores 1/8 of the total if ALL its sub-checkpoints pass; 0/8 otherwise. This all-or-nothing design is harsh but realistic — a plan with one timing overlap is a broken plan.

| # | Dimension | Checkpoints | What It Verifies |
|---|-----------|-------------|------------------|
| 1 | **Route Consistency** | 3 | (a) Trip duration matches the requested days, (b) route forms a closed loop (depart from and return to origin), (c) seamless transfers between segments (no impossible jumps) |
| 2 | **Sandbox Compliance** | 4 | (a) All hotels exist in the database, (b) all attractions exist, (c) all meals reference real restaurants, (d) all transportation options are valid entries |
| 3 | **Itinerary Structure** | 4 | (a) Every night has traceable accommodation, (b) last day ends with accommodation or departure, (c) meal coverage (breakfast/lunch/dinner as appropriate), (d) attraction coverage (at least one per day) |
| 4 | **Time Feasibility** | 2 | (a) No temporal overlaps between activities (e.g., visiting two attractions simultaneously), (b) transfer times between locations are physically reasonable |
| 5 | **Business Hours** | 3 | (a) Attraction visits fall within opening hours, (b) dining falls within restaurant hours, (c) no visits on closure days |
| 6 | **Duration Rationality** | 2 | (a) Attraction visit durations are reasonable (not 5 minutes at a museum, not 8 hours at a café), (b) meal durations are reasonable |
| 7 | **Cost Calculation** | 1 | Total cost calculation is arithmetically correct and matches itemized breakdown |
| 8 | **Activity Diversity** | 2 | (a) Diverse meal choices (not same restaurant 3 times), (b) diverse attractions (not same park every day) |

**Total Commonsense Score**: Sum of passed dimensions / 8 (range: 0.0 to 1.0, scaled to 0-100 in reporting).

### 3b. Personalized Score

All user-injected constraints from Stage 2b are translated into programmatic verification functions. Binary scoring: 1 if **all** personalized constraints are satisfied, 0 otherwise.

Constraint types include:
- Temporal preferences ("flight after 7 AM")
- Quality preferences ("hotel rated 4.5+ stars")
- Budget constraints ("total under 8,000 yuan")
- Proximity constraints ("restaurant within walking distance of hotel")
- Dietary/attribute filters ("vegetarian options", "brand X only")
- Quantity constraints ("at least 3 attractions per day")

### 3c. Composite Score

```
Composite Score = (Commonsense Score + Personalized Score) / 2
```

Range: 0.0 to 1.0 (scaled to 0-100). This gives equal weight to "common sense" and "following instructions."

### 3d. Case Accuracy (Primary Metric)

```
Case Accuracy = 1  if  (Commonsense Score == 8/8) AND (Personalized Score == 1)
                0  otherwise
```

This is the strictest metric — an all-or-nothing pass/fail. A plan that scores 7/8 on commonsense and 1 on personalized scores 0 on case accuracy. This mirrors real-world planning quality: a trip itinerary with one impossible transfer is a failed itinerary, regardless of how good the other 90% is.

### 3e. Shopping Planning Metrics

Shopping uses a different scoring structure:
- **Match Rate**: Percentage of expected items correctly present in the cart
- **Weighted Average Case Score**: Average case completion across difficulty levels
- **Case Accuracy**: All required items present with correct coupons applied

### 3f. Cross-Domain Aggregation

```
Average Accuracy (Avg Acc.) = (Travel Case Accuracy + Shopping Case Accuracy) / 2
```

This is the primary leaderboard ranking metric.

---

## 4. Model Leaderboard — Full Results (v1.0 Paper)

### 4a. Reasoning-Enabled Models (Ranked by Avg Accuracy)

| Rank | Model | Org | Avg Acc. | Travel CS | Travel PS | Travel Comp | Travel Case | Shop Case |
|------|-------|-----|----------|-----------|-----------|-------------|-------------|-----------|
| 1 | GPT-5.2-high | OpenAI | 44.6% | 88.5 | 83.3 | 85.8 | 35.0% | 54.2% |
| 2 | Claude-4.5-Opus (thinking) | Anthropic | 33.9% | 79.3 | 70.9 | 75.1 | 22.7% | 45.0% |
| 3 | GPT-5-high | OpenAI | 31.6% | 78.7 | 65.9 | 72.3 | 18.9% | 44.2% |
| 4 | Gemini-3-Flash-Preview | Google | 28.8% | 67.1 | 57.7 | 62.4 | 5.9% | 51.7% |
| 5 | Qwen3-Max (thinking) | Alibaba | 28.7% | 64.0 | 61.7 | 62.8 | 13.8% | 43.5% |
| 6 | Claude-4.5-Sonnet (thinking) | Anthropic | 25.5% | 65.2 | 58.4 | 61.8 | 7.6% | 43.3% |
| 7 | o3 | OpenAI | 24.9% | 76.5 | 55.6 | 66.1 | 11.3% | 38.5% |
| 8 | Gemini-3-Pro-Preview | Google | 23.2% | 58.4 | 25.1 | 41.8 | 0.7% | 45.8% |
| 9 | DeepSeek-V3.2 (thinking) | DeepSeek | 21.6% | 47.4 | 35.0 | 41.2 | 0.7% | 42.5% |
| 10 | Seed-1.8-high | ByteDance | 20.4% | 43.6 | 56.7 | 50.1 | 0.0% | 40.8% |
| 11 | Grok-4.1-Fast (reasoning) | xAI | 17.2% | 57.1 | 37.7 | 47.4 | 2.7% | 31.7% |
| 12 | Qwen-Plus (thinking) | Alibaba | 17.1% | 35.4 | 22.4 | 28.9 | 0.0% | 34.1% |
| 13 | Gemini-2.5-Pro | Google | 17.0% | 62.3 | 42.0 | 52.2 | 3.2% | 30.8% |
| 14 | GLM-4.7 (thinking) | Z.ai | 14.0% | 44.0 | 44.6 | 44.3 | 0.4% | 27.5% |
| 15 | o4-mini | OpenAI | 12.4% | 58.0 | 36.6 | 47.2 | 3.0% | 21.7% |
| 16 | Kimi-K2-Thinking | Moonshot | 12.1% | 45.2 | 32.5 | 38.9 | 0.0% | 24.2% |

### 4b. Non-Reasoning Models (Ranked by Avg Accuracy)

| Rank | Model | Org | Avg Acc. | Travel CS | Travel PS | Travel Comp | Travel Case | Shop Case |
|------|-------|-----|----------|-----------|-----------|-------------|-------------|-----------|
| 17 | Claude-4.5-Opus (no thinking) | Anthropic | 26.3% | 67.5 | 58.8 | 63.1 | 6.7% | 45.8% |
| 18 | Claude-4.5-Sonnet (no thinking) | Anthropic | 17.2% | 53.4 | 42.8 | 48.1 | 1.1% | 33.3% |
| 19 | Qwen3-Max (no thinking) | Alibaba | 12.8% | 36.7 | 30.7 | 31.8 | 0.8% | 24.7% |
| 20 | Seed-1.8-minimal | ByteDance | 11.3% | 43.0 | 47.5 | 45.3 | 0.0% | 22.5% |
| 21 | Qwen-Plus (no thinking) | Alibaba | 7.5% | 37.3 | 13.0 | 25.1 | 0.0% | 15.0% |
| 22 | GLM-4.7 (no thinking) | Z.ai | 7.1% | 38.9 | 22.5 | 30.7 | 0.0% | 14.2% |
| 23 | DeepSeek-V3.2 (no thinking) | DeepSeek | 5.3% | 37.4 | 12.1 | 24.7 | 0.0% | 10.6% |
| 24 | GPT-5.2-none | OpenAI | 4.5% | 54.3 | 29.9 | 42.1 | 0.4% | 8.6% |
| 25 | Grok-4.1-Fast (non-reasoning) | xAI | 3.0% | 39.6 | 19.7 | 29.6 | 0.0% | 5.9% |

**Note**: v1.1 leaderboard (2026-03-03) adds Claude-4.6-Opus at rank 1 (58.9% avg accuracy) and Qwen-3.5-Plus at rank 3 (37.6%). The v1.0 paper numbers are used throughout this deep dive for consistency with the published analysis.

### 4c. Key Observations from the Leaderboard

1. **Massive headroom**: Even the best model (GPT-5.2-high) achieves only 44.6% average accuracy. Travel case accuracy peaks at 35.0%. The benchmark is far from saturated.

2. **Travel is much harder than Shopping**: GPT-5.2-high scores 35.0% on Travel case accuracy but 54.2% on Shopping. This pattern holds across all models — travel planning requires more complex temporal reasoning and multi-constraint optimization.

3. **Domain specialization exists**: Gemini-3-Flash-Preview scores 5.9% on Travel but 51.7% on Shopping — a 45.8pp gap. Some architectures excel at combinatorial optimization (shopping) but fail at temporal sequencing (travel).

4. **Composite scores mislead**: Many models achieve respectable composite scores (60-80 range) but near-zero case accuracy. High average constraint satisfaction does not mean the plan works end-to-end.

---

## 5. Reasoning vs. Non-Reasoning Gap Analysis

This is the most EPYC-relevant finding. The paper systematically tests the same models with and without deliberate internal reasoning (thinking/chain-of-thought), providing controlled pairs.

### 5a. Controlled Pair Comparisons

| Model | Non-Reasoning Case Acc. | Reasoning Case Acc. | Absolute Gap | Relative Improvement |
|-------|------------------------|---------------------|-------------|---------------------|
| Claude-4.5-Opus | 26.3% | 33.9% | +7.6pp | +29% |
| Claude-4.5-Sonnet | 17.2% | 25.5% | +8.3pp | +48% |
| Qwen3-Max | 12.8% | 28.7% | +15.9pp | +124% |
| DeepSeek-V3.2 | 5.3% | 21.6% | +16.3pp | +308% |
| Qwen-Plus | 7.5% | 17.1% | +9.6pp | +128% |
| GLM-4.7 | 7.1% | 14.0% | +6.9pp | +97% |
| GPT-5.2 (none vs high) | 4.5% | 44.6% | +40.1pp | +891% |
| Grok-4.1-Fast | 3.0% | 17.2% | +14.2pp | +473% |

### 5b. Travel Case Accuracy (Where the Gap is Sharpest)

| Model | Non-Reasoning Travel | Reasoning Travel | Gap |
|-------|---------------------|-----------------|-----|
| Claude-4.5-Opus | 6.7% | 22.7% | +16.0pp |
| Qwen3-Max | 0.8% | 13.8% | +13.0pp |
| GPT-5.2 | 0.4% | 35.0% | +34.6pp |
| DeepSeek-V3.2 | 0.0% | 0.7% | +0.7pp |
| Qwen-Plus | 0.0% | 0.0% | +0.0pp |
| GLM-4.7 | 0.0% | 0.4% | +0.4pp |

**Key finding**: Reasoning mode is dramatically more important for planning tasks than for typical QA benchmarks. The GPT-5.2 gap (+40.1pp overall, +34.6pp on travel) is the largest documented reasoning-mode improvement across any benchmark in the literature.

### 5c. Efficiency of Reasoning

Reasoning does not simply mean "more compute = better results." It means *better-directed* compute:

- Claude-4.5-Opus (thinking): 12.5 turns, 72.9 tool calls per task
- Claude-4.5-Opus (no thinking): 16.9 turns, 79.5 tool calls per task

Reasoning mode achieved **higher accuracy with fewer tool calls and fewer turns** — a 26% reduction in turns and 9% reduction in tool calls. The reasoning step replaces trial-and-error API probing with directed information acquisition.

### 5d. Cost-Efficiency Analysis

GPT-5.2-high achieves 85.8 composite score but requires approximately 224 tool invocations per task. By contrast, o4-mini achieves 47.2 composite with far fewer invocations. The correlation between tool invocations and accuracy is positive but sublinear — there are diminishing returns.

GPT-5.2 uses sequential workflows (one tool call per turn). GPT-5.1-high uses parallel execution (bundled tool calls). GPT-5.2-high achieves +12.7% better composite scores but requires 10x more interaction turns. This suggests that sequential, deliberate planning outperforms parallel fire-and-forget API usage, but at significant cost.

---

## 6. Error Taxonomy — 140 Failed Trajectory Analysis

The authors analyzed 140 failed trajectories from Claude-4.5-Opus (reasoning mode) — 80 travel failures and 60 shopping failures. Three error categories emerge, with global optimization failures dominating.

### 6a. Pattern A: Information Acquisition Failures

Failures in the API-calling phase — the agent did not gather sufficient information to make good decisions.

| Sub-pattern | Description | Example |
|-------------|-------------|---------|
| A1: Insufficient Search | Omitting critical queries | Failing to query transit times between two attractions, then producing an itinerary with a physically impossible 10-minute transfer across a city |
| A2: Tool Misuse | Wrong tool or malformed arguments | Using `search_location` when `query_road_route_info` was needed; passing a restaurant name to `query_hotel_info` |
| A3: Fact Displacement | Retrieving correct information but misquoting it in the plan | Querying a hotel at 320 yuan/night, then citing 280 yuan in the itinerary's cost breakdown |

### 6b. Pattern B: Local Reasoning Failures

Correct information was gathered but individual constraints were violated.

| Sub-pattern | Count (Travel / Shopping) | Description |
|-------------|--------------------------|-------------|
| B1: Explicit Constraint Violations | Moderate | Ignoring a user-specified requirement ("must depart after 7 AM" but booking a 6:15 AM flight) |
| B2: Implicit Constraint Failures | 86 Travel / 21 Shopping | Conflicting with common sense despite no explicit prohibition (e.g., booking 4 people into a hotel room that only has 2 beds; scheduling a museum visit at 11 PM) |

B2 (implicit constraint failures) is disproportionately common — models are better at following explicit user requests than inferring unstated real-world constraints.

### 6c. Pattern C: Global Optimization Failures (Most Prevalent)

**101 Travel / 52 Shopping instances** — the dominant failure mode.

The agent gathered correct information and satisfied local constraints but failed to produce a globally optimal plan. Manifestations:
- **Temporal overlaps between steps**: Day 2 afternoon has two overlapping activities
- **Logical discontinuities between days**: Day 3 ends at location X but Day 4 starts at distant location Y with no transit plan
- **Suboptimal cart composition**: Found valid products but missed the coupon combination that would reduce total cost by 30%
- **Budget violation at aggregation level**: Each day's spending is reasonable but the multi-day total exceeds the budget
- **Diversity failures**: Technically valid plan but same restaurant for 4 consecutive meals

**Implication**: Global optimization is the frontier capability that separates 35% case accuracy (GPT-5.2-high) from 0% (most non-reasoning models). Models that excel at local step-level reasoning still fail catastrophically at maintaining global coherence.

---

## 7. Transferable Evaluation Methodology — Design Patterns

DeepPlanning's scoring architecture has several properties that make it transferable to other domains:

### 7a. Rule-Based Determinism

Every score is computed by programmatic rules, not LLM judgment. The verification functions are Python code that checks constraints against the agent's output. This eliminates:
- Inter-rater disagreement (inherent in human eval)
- Stochastic scoring variance (inherent in LLM-as-judge)
- Evaluation cost scaling (each eval is O(1) compute, not another LLM call)

The evaluation code is open-source at `benchmark/deepplanning/` in the Qwen-Agent repository.

### 7b. Multi-Granularity Scoring

Three levels of granularity serve different analytical needs:
- **Dimension-level** (8 commonsense dimensions): Identifies *which* capability is weak
- **Composite-level** (average of commonsense + personalized): Overall constraint satisfaction
- **Case-level** (binary pass/fail): Ground truth for "does this plan actually work?"

This architecture avoids the common trap of reporting only one metric. A model at 85 composite / 3% case accuracy is fundamentally different from a model at 50 composite / 15% case accuracy — the first is "close on average but fragile", the second is "rough but occasionally perfect."

### 7c. Reverse Generation for Solvability

The solution-first, task-second approach guarantees every task has a known optimal answer. This enables:
- Automated scoring without human answer keys
- Difficulty calibration (adjust constraints to reach target solve rates)
- Dataset expansion (new tasks can be generated programmatically)

### 7d. Domain-Specific Constraint Taxonomies

The travel/shopping split shows that different domains require different constraint taxonomies. Travel emphasizes temporal consistency and geographic feasibility; shopping emphasizes combinatorial optimization. Both share the pattern of layered constraints (base + personalized + environmental).

---

## 8. Limitations and Bias Assessment

### 8a. Domain Coverage

Only 2 domains (travel, shopping). Both are consumer planning tasks. Missing:
- Technical planning (infrastructure deployment, project scheduling)
- Creative planning (event organization, menu design)
- Adversarial planning (negotiation, game strategy)
- Resource-constrained planning (logistics, supply chain)

The 2-domain scope limits generalizability. A model that excels at travel and shopping planning may fail at infrastructure planning, which has fundamentally different constraint structures (dependency DAGs, resource contention, failure modes).

### 8b. Synthetic Task Distribution

Tasks are generated by LLM + human review, not sampled from real user queries. The "reverse generation" approach guarantees solvability but may produce an unnatural distribution:
- Constraints may be more orthogonal (independently verifiable) than in real planning tasks
- Real user queries often have ambiguous or contradictory constraints
- The single-optimal-solution design does not reflect real planning where multiple good solutions exist

### 8c. Single-Turn Limitation

All tasks are single-turn: one user query, one agent response (with tool calls). Real planning involves multi-turn clarification, constraint negotiation, and iterative refinement. A model that scores 0% case accuracy might achieve 40% with one round of feedback.

### 8d. Author Affiliation Bias

The benchmark is produced by the Qwen team at Alibaba. Examining the results for Qwen favoritism:

| Qwen Model | Rank Among Reasoning | Rank Among Non-Reasoning |
|-------------|---------------------|--------------------------|
| Qwen3-Max (thinking) | 5th of 16 | N/A |
| Qwen3-Max (no thinking) | N/A | 3rd of 9 |
| Qwen-Plus (thinking) | 12th of 16 | N/A |
| Qwen-Plus (no thinking) | N/A | 5th of 9 |

Qwen models rank in the middle of the pack — they are not top-ranked, nor suspiciously boosted. GPT-5.2-high (OpenAI) dominates, and Claude-4.5-Opus (Anthropic) takes second. If anything, the benchmark makes Qwen look mediocre relative to the frontier. The v1.1 leaderboard adds Qwen-3.5-Plus at rank 3, which is strong but still below Claude-4.6-Opus at rank 1. **No clear favoritism detected.** The constraint-verification approach (rule-based, not LLM-as-judge) also makes result manipulation structurally harder — you cannot game a rule-based scorer by tuning prompts.

### 8e. What Aspects of Planning Are NOT Tested

- **Dynamic replanning**: What happens when a constraint becomes infeasible mid-execution (flight cancelled, product out of stock)?
- **Partial-information planning**: All database records are accessible via API — there is no "unknown unknowns" element
- **Multi-agent coordination**: All tasks assume a single planner; no delegation or consensus
- **Temporal uncertainty**: All durations and schedules are deterministic; no probabilistic reasoning about delays
- **Preference learning**: User preferences are explicit in the query, not inferred from history
- **Explanation quality**: Scoring only checks the plan, not whether the agent explains its reasoning to the user

---

## 9. EPYC Applicability — Concrete Integration Points

### 9a. Routing Intelligence — Reasoning Mode Selection

**Finding**: Reasoning mode provides +7.6pp to +40.1pp improvement on planning tasks, with the gap widening as task complexity increases. Non-reasoning Claude-4.5-Opus (26.3%) beats reasoning Qwen-Plus (17.1%), demonstrating that model quality still matters — but within a given model, reasoning always wins on planning.

**Integration point**: The routing classifier at `/mnt/raid0/llm/epyc-orchestrator/src/classifiers/` currently has Category A (input classification) that detects summarization, coding, and direct-mode tasks. DeepPlanning data suggests adding a **planning-complexity signal** to the Category A classifier:

- Queries with multi-step temporal constraints, budget optimization, or combinatorial search should trigger reasoning mode
- The routing decision should consider the *type* of reasoning: planning tasks benefit from reasoning far more than factual QA tasks
- Implementation: Add planning-detection keywords/patterns to `orchestration/classifier_config.yaml`

**Relevant handoff**: `/workspace/handoffs/active/routing-intelligence.md` (RI-1 calibration dataset could include planning-complexity examples)

### 9b. Eval Tower — Multi-Granularity Scoring Architecture

**Finding**: DeepPlanning's dimension-level / composite / case-level hierarchy catches failure modes that single-metric scoring misses. High composite scores (60-80) can coexist with 0% case accuracy.

**Integration point**: The eval tower at `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py` currently uses `EvalResult` with 4 metrics (quality, speed, cost, reliability). The quality metric is a single scalar from `score_answer_deterministic()`. DeepPlanning's approach suggests:

1. **Add dimension-level quality decomposition**: Instead of one quality score, track sub-dimensions (factual accuracy, constraint satisfaction, coherence, completeness). This mirrors the 8 commonsense dimensions.
2. **Add a case-level "all constraints pass" binary metric** alongside the averaged quality score. A config that scores 90% average quality but fails 5% of sentinel questions is worse than one scoring 80% average quality with 100% sentinel pass rate.
3. **Track the gap between composite and case accuracy** as a calibration signal. A growing composite-vs-case gap indicates the model is getting "close on average but fragile" — a red flag for deployment.

**Relevant handoff**: `/workspace/handoffs/active/eval-tower-verification.md` (EV-3/4/5 pending)

### 9c. PromptForge — Constraint-Verifiable Prompt Testing

**Finding**: DeepPlanning's reverse-generation approach (start from solution, generate task) guarantees every test case has a known-correct answer. This is exactly what PromptForge needs for prompt mutation testing.

**Integration point**: PromptForge at `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/species/prompt_forge.py` proposes prompt mutations and evaluates them against the eval tower. Currently, "does this mutation improve quality?" depends on the eval tower's scoring. DeepPlanning suggests:

1. **Construct constraint-verifiable test cases**: For each prompt mutation being evaluated, generate test inputs with known-correct outputs (reverse-generation). This eliminates the need for LLM-as-judge in the mutation evaluation loop.
2. **Use the commonsense checkpoint pattern**: Define domain-specific "must-pass" checks (not just "answer matches expected"). E.g., for a resolver prompt mutation, check: (a) response uses correct formatting, (b) response includes required sections, (c) response respects length constraints, (d) response references source material correctly.

### 9d. Benchmark Suite Construction (ch07)

**Finding**: The 8-dimension commonsense taxonomy with 21 checkpoints provides a concrete template for building rule-based benchmark suites.

**Integration point**: The scoring infrastructure at `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/score_outputs.py` already uses pattern-matching criteria (CRITERIA dict with score_3/score_2/score_1 levels and wrong_indicators). DeepPlanning's architecture suggests evolving this toward:

1. **Dimension-based scoring**: Group criteria into dimensions (factual correctness, reasoning quality, formatting compliance, etc.)
2. **All-or-nothing dimension scoring**: Score a dimension as pass only if all sub-criteria pass — matches DeepPlanning's harsh-but-realistic model
3. **Case accuracy alongside average quality**: Track "what fraction of questions does the model get completely right" vs "what is the average partial score"

### 9e. Q-Scorer Calibration

**Finding**: DeepPlanning shows that models with high average constraint satisfaction (composite 60-80) can have near-zero case accuracy. This calibration gap is directly relevant to q_scorer's `baseline_tps` approach.

**Integration point**: The scoring at `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_scoring.py` uses `score_answer_deterministic()` with binary exact-match. DeepPlanning suggests adding a **partial-credit layer** that tracks *which* dimensions of quality are satisfied, enabling finer-grained routing decisions. A model that always fails on "cost calculation" but passes everything else should be routed differently than one that fails randomly.

### 9f. Learned Routing Controller Training Data

**Finding**: The 26-model leaderboard with per-dimension scores constitutes a rich dataset of model capabilities across task types. The domain-specialization finding (Gemini-3-Flash: 5.9% travel, 51.7% shopping) proves that task-specific routing is not optional — it is essential.

**Integration point**: The learned routing controller at `/workspace/handoffs/active/learned-routing-controller.md` (Phase 1 complete, 92% val accuracy) could use DeepPlanning's model-capability matrix as training signal:

- Planning tasks should route to models with high Travel composite scores
- Combinatorial optimization tasks should route to models with high Shopping scores
- The reasoning-mode flag should be task-type-dependent, not global

---

## 10. Key Takeaways and Verdict Refinement

### 10a. What DeepPlanning Gets Right

1. **Rule-based scoring is the right call for benchmarks.** LLM-as-judge introduces systematic bias, costs money per evaluation, and produces noisy results. DeepPlanning's constraint-verification approach is cheaper, deterministic, and reproducible.

2. **Case accuracy is a better primary metric than composite/average scores.** The paper's central finding — that models can score 85 composite but 35% case accuracy — is a cautionary tale for any evaluation system that reports only averaged quality.

3. **The reasoning gap data is gold.** No other benchmark has such clean controlled-pair reasoning-mode ablations across 8 model families. This data alone justifies tracking the paper.

4. **Reverse generation is a practical methodology.** Starting from solutions and working backward to generate tasks is not novel in principle (it is standard in constraint-satisfaction testing), but its application to LLM agent benchmarking is well-executed and the code is open-source.

### 10b. What DeepPlanning Gets Wrong or Misses

1. **Two domains is not enough.** Consumer planning (travel + shopping) is a narrow slice. The error taxonomy (A/B/C) may look completely different for technical planning, creative tasks, or adversarial scenarios.

2. **Single-turn is unrealistic.** Real planning is iterative. The benchmark penalizes models that could improve with feedback — possibly unfairly ranking interactive models lower than one-shot planners.

3. **No cost normalization.** GPT-5.2-high wins but uses 224 tool calls per task. A cost-normalized leaderboard (accuracy per dollar) might favor different models — especially relevant for CPU inference where cost = wall-clock time.

4. **The difficulty scaling is implicit.** Travel difficulty scales with days (2-7) and shopping with levels (1-3), but there is no formal complexity measure. A 5-day trip with 2 constraints may be easier than a 3-day trip with 8 constraints.

### 10c. Updated Verdict

**Initial intake**: novelty=medium, relevance=medium, verdict=`worth_investigating`.

**Post-deep-dive**: 
- **Novelty** stays at medium. The individual techniques (rule-based scoring, reverse generation, multi-granularity metrics) are established in software testing and constraint-satisfaction literature. Their combination into an LLM agent benchmark is well-executed but not technically novel.
- **Relevance** upgrades to **medium-high**. The reasoning-gap data directly informs routing intelligence design. The scoring architecture provides a concrete template for eval tower evolution. The error taxonomy (global optimization as dominant failure mode) validates EPYC's investment in routing intelligence over raw model quality.
- **Verdict**: `adopt_patterns` (upgrade from `worth_investigating`). Specifically adopt: (1) multi-granularity scoring (dimension + composite + case) in eval tower, (2) planning-complexity signal in routing classifier, (3) reverse-generation methodology for PromptForge test case construction, (4) case-accuracy-alongside-average-quality reporting pattern.

---

## 11. Implementation References

| Resource | URL / Path |
|----------|-----------|
| Paper (HTML) | https://arxiv.org/html/2601.18137v1 |
| Dataset | https://huggingface.co/datasets/Qwen/DeepPlanning |
| Evaluation code | https://github.com/QwenLM/Qwen-Agent/tree/main/benchmark/deepplanning |
| Scoring entry point | `benchmark/deepplanning/run_all.sh` |
| Travel scoring | `benchmark/deepplanning/travelplanning/` |
| Shopping scoring | `benchmark/deepplanning/shoppingplanning/` |
| Result aggregation | `benchmark/deepplanning/aggregate_results.py` |
| Model config template | `benchmark/deepplanning/models_config.json` |
| Project leaderboard (v1.1) | https://qwenlm.github.io/Qwen-Agent/en/benchmarks/deepplanning/ |
| EPYC routing classifier | `/mnt/raid0/llm/epyc-orchestrator/src/classifiers/` |
| EPYC eval tower | `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py` |
| EPYC PromptForge | `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/species/prompt_forge.py` |
| EPYC scoring infrastructure | `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_scoring.py` |
| EPYC benchmark scorer | `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/score_outputs.py` |
| Routing intelligence handoff | `/workspace/handoffs/active/routing-intelligence.md` |
| Eval tower handoff | `/workspace/handoffs/active/eval-tower-verification.md` |
| Learned routing handoff | `/workspace/handoffs/active/learned-routing-controller.md` |
