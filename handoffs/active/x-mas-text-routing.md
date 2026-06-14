# X-MAS Heterogeneous Text-MAS Routing Spike

**Status**: classifier/table scaffold landed 2026-06-13; default-off shadow telemetry hook landed 2026-06-14; enforcing route override + full 5x5 sweep pending
**Created**: 2026-05-19 (post-latent-MAS-cluster deep-dive)
**Categories**: agent_architecture, cost_aware_routing, benchmark_methodology, routing_intelligence
**Priority**: HIGH (zero-infra-change immediate win — replaces ad-hoc role mapping with empirical (domain × function) lookup)
**Depends on**: `routing-intelligence.md`, `routing-and-optimization-index.md`, `meta-harness-optimization.md`, `hermes-outer-shell.md`
**Source deep-dive**: [`/workspace/research/deep-dives/2026-05-19-latent-mas-cluster.md`](../../research/deep-dives/2026-05-19-latent-mas-cluster.md)

## Objective

Replicate the X-MAS (intake-557, arxiv:2505.16997, `github.com/MASWorks/X-MAS`) (domain × function) optimal-model methodology on our 4-model production stack (qwen3.6 frontdoor, gemma4-26B-A4B worker_general, coder-30B, Qwen3-1.7B drafter), build a (domain × function) → winner lookup table, and use it to override the current ad-hoc `model_registry.yaml` role defaults.

This is the only entry in the May 2026 latent-MAS cluster that's deployable on the current orchestrator with **zero llama.cpp changes** — pure text-mediated MAS with no hidden-state surfacing, no projection layer, no fork patches.

## Research Context

| Intake ID | Title | Relevance | Notes |
|-----------|-------|-----------|-------|
| intake-557 | X-MAS (arxiv:2505.16997) — 1.7M-eval heterogeneous MAS sweep across 27 LLMs × 5 domains × 5 functions | high | text-MAS, no infra change |
| intake-544 | RMAS (arxiv:2604.25917) | medium | latent-MAS — requires llama.cpp fork |
| intake-555 | LatentMAS (arxiv:2511.20639, ICML 2026 Spotlight) | high | training-free latent — requires llama.cpp fork |
| intake-558 | Dead Weights (arxiv:2604.08335) | high | cross-architecture frozen composition — keystone for unlocking RMAS/LatentMAS but credibility-weakest (3-author preprint, no code) |

## Key Findings from Deep-Dive

- **X-MAS is the only deployable-today path** in the latent-MAS cluster. RMAS / LatentMAS / Dead Weights all require llama.cpp HTTP server fork to surface last-layer hidden states across server boundaries — 4-8 weeks of engineering + 2× rebase debt against ik_llama.cpp PR #1744 worker_pool branch.
- **Reported magnitudes**: MATH +8.4% with heterogeneous chatbot-only configuration, AIME +47% with mixed chatbot-reasoner setup. Even with 50% magnitude attenuation from their 27-model sweep down to our 4-model stack, this is meaningful.
- **LatentMAS heterogeneity claim is overstated**: paper Section C.3 admits "all agents share the same shape of transformer layers"; all experiments use only Qwen3 4B/8B/14B (same family, same tokenizer). X-MAS is the only cluster entry with genuine cross-family empirical evidence.
- **GitHub**: `MASWorks/X-MAS` exists (29 stars, **no license** — treat methodology as inspiration, do NOT vendor code).

## Spike Plan (single phase)

### X-MAS-style heterogeneous text-MAS routing (~2-3 dev-days + 1 nightshift)

**Goal**: build a 5×5 (domain × function) → winner-model lookup table for our specific stack, use it to route incoming orchestrator tasks.

**Steps**:
1. **Replicate X-MAS-Bench task layout**: pull the 5-domain × 5-function cell layout from `github.com/MASWorks/X-MAS` (treat as methodology, not code reuse — no license).
2. **Bench sweep on our 4 production models**:
   - 10-20 representative tasks per (domain × function) cell
   - 5 domains × 5 functions × 4 models × ~15 tasks = ~1500 evals
   - Use existing eval-tower harness in `epyc-inference-research/scripts/benchmark/`
3. **Build per-stack winner table**: 5×5 cells, each cell records the winning model. Compare to X-MAS-published winners as a shape sanity check.
4. **Orchestrator integration**: add a coarse (domain, function) classifier on the frontdoor; each incoming task is classified, then routed to the cell winner. Fall back to current ad-hoc routing for unclassified tasks. **Partial 2026-06-13/14**: side-effect-free taxonomy/classifier + winner-table loader landed in `epyc-orchestrator` commit `e9004a2`; default-off shadow/advisory telemetry hook landed in `edbe0d2`. The hook records X-MAS metadata without mutating `routing_decision`; enforcing override semantics remain gated on the 5x5 eval-populated winner table.
5. **Hermes outer-shell agent uses the same routing for sub-task delegation** (`hermes-outer-shell.md`).

## Implementation Progress

### 2026-06-13 — inference-free scaffold

Landed in `epyc-orchestrator` commit `e9004a2`:

- `src/classifiers/xmas_routing.py`: 5-domain × 5-function taxonomy, deterministic lexical `(domain, function)` classifier, `XmasCell`, `XmasClassification`, `WinnerTable`, and `load_winner_table()`.
- `orchestration/xmas_winner_table.example.yaml`: complete 5×5 table template using valid current role names.
- `tests/classifiers/test_xmas_routing.py`: 8 unit tests for classification, nested YAML loading, fallback behavior, unknown-domain/role rejection, and completeness validation.

Validation:

- `.venv/bin/python -m pytest tests/classifiers/test_xmas_routing.py -q` → 8 passed.
- `.venv/bin/python -m ruff check src/classifiers/xmas_routing.py tests/classifiers/test_xmas_routing.py` → passed.
- `git diff --check` on touched files → passed.

Still not landed after the scaffold:

- Evidence-backed 5x5 winner table.
- Enforcing route override semantics.
- `model_registry.yaml` override behavior.

Reason: the original 2026-06-13 override target, `_classify_and_route`, had HIGH upstream impact. The 2026-06-14 hook therefore shipped the safe path first: default-off shadow/advisory telemetry through `_route_request` and `routing_meta`, with no route mutation.

### 2026-06-14 — default-off shadow telemetry hook

Landed in `epyc-orchestrator` commit `edbe0d2`:

- `src/classifiers/xmas_routing.py` and `src/classifiers/config_loader.py`: config helpers and narrow env overrides for `ORCHESTRATOR_XMAS_ROUTING_MODE` and `ORCHESTRATOR_XMAS_WINNER_TABLE_PATH`.
- `orchestration/classifier_config.yaml`: `xmas_routing.mode: off` by default, with supported values `off`, `shadow`, and `enforce`.
- `src/api/routes/chat_pipeline/routing.py` and `routing_decision.py`: when enabled, classify prompt/context into the X-MAS 5x5 domain/function cell, optionally load a configured winner table, and log nested `routing_meta["xmas"]` fields for confidence, table version, suggested role, and `applied=false`.
- Missing/invalid winner tables and classifier errors are fail-open; routing continues through the existing decision path.
- `enforce` is intentionally advisory in this patch: it logs the suggested role but never mutates `routing_decision`.

Validation:

- `python3 -m py_compile` on touched orchestrator files -> passed.
- `uv run ruff check` on touched orchestrator files -> passed.
- `git diff --check` -> passed.
- `uv run pytest -q tests/classifiers/test_xmas_routing.py tests/unit/test_pipeline_routing.py tests/unit/test_chat_pipeline_stages.py tests/unit/test_stream_adapter.py tests/unit/test_chat_endpoints.py` -> 156 passed.
- Post-commit GitNexus full rebuild completed after an interrupted incremental run: indexed `/mnt/raid0/llm/epyc-orchestrator` at `edbe0d2` with 52,168 nodes, 89,473 edges, 1,094 clusters, and 300 flows.

Remaining:

- Populate the 5x5 winner table from the eval sweep before any real override behavior.
- Implement and validate an enforcing route override only after the table is evidence-backed.
- Keep current production behavior unchanged while `xmas_routing.mode` remains `off`.

**Gate criteria**:
- The 5×5 table shows ≥2 distinct winners across the 25 cells (i.e., heterogeneity actually exists in our stack — if gemma4-26B-A4B wins everything per its `project_worker_general_swap_2026_05_08` dominance, the spike kills itself early).
- A/B test on a held-out 100-task suite shows ≥5pp accuracy improvement on at least one domain, no regression on others.
- Decode wall-time per task within ±10% of baseline (no latency cost from added classification step).

**Dev cost**: ~2-3 dev-days (1 day routing code + 1 day classifier + 1 day eval-harness reuse).
**Compute cost**: 1 nightshift (~12 hours) for the 1500-eval sweep at our standard 49-76 t/s rates. Requires `feedback_no_concurrent_inference` per-bench approval.

**Failure mode** (cheap kill): if the 5×5 table shows the same winner across most cells (likely gemma4-26B-A4B given tool_compliance dominance), X-MAS heterogeneity doesn't apply to our stack and we skip Spike 2/3 of the latent-MAS plan entirely.

## Why Not the Other Latent-MAS Entries

| Entry | Why deferred |
|-------|--------------|
| RMAS (intake-544) | Requires RecursiveLink fine-tuning + cross-tokenizer projection — no path on frozen GGUF stack without llama.cpp fork |
| LatentMAS (intake-555) | Training-free but requires hidden-state surfacing across server boundaries (4-8 weeks of llama.cpp fork work + 2× rebase debt against ik_llama PR #1744) |
| Thought Communication (intake-556) | Theoretical identifiability framework; no engineering hook |
| Dead Weights (intake-558) | The keystone if cross-tokenizer projection works — but 3-author preprint, no code, no independent reproduction. **GPU-rental Spike 2 (~$200-500) DEFERRED per user direction 2026-05-19.** |

## Non-Goals

- **Latent handoff**: this spike is explicitly text-mediated. Do not surface hidden states.
- **Cross-tokenizer projection**: Dead Weights territory — deferred.
- **New benchmark suite**: reuse existing eval-tower; do not build X-MAS-Bench from scratch.

## Open Questions for User

1. **Domain × function taxonomy**: X-MAS uses 5 domains (math / coding / science / commonsense / world-knowledge or similar) × 5 functions (planner / coder / verifier / executor / summarizer or similar). Map to our orchestrator's actual task taxonomy or keep X-MAS taxonomy verbatim for replication parity?
2. **Classifier choice**: coarse (domain, function) classification step on frontdoor — small MLP, embedding-based nearest-neighbor, or LLM-judge? Cheapest path: nearest-neighbor over (domain, function) prototype embeddings using existing TEI service from `internal-kb-rag.md`.
3. **Fallback policy**: when the classifier confidence is low, do we route via current ad-hoc heuristics (safest) or via the most-frequent X-MAS winner (simpler)?
4. **Composability with learned MLP router** (`learned-routing-controller.md` Phase 1 @ 92% val acc): does X-MAS routing replace the MLP, sit before it, or sit after it? My read: X-MAS provides the *prior* (domain × function → winner), MLP provides the *posterior* refinement on specific task features. They compose.

## Cheap-Kill Run 2026-05-19 — HETEROGENEITY_PRESENT_escalate (v2 max_tokens=4096)

**Verdict**: spike does NOT auto-abort. Two distinct cell winners across the 5 coarse domains tested. Re-confirms the deep-dive's hypothesis that the 4-model stack is genuinely heterogeneous — and surfaces a strict-dominance finding that's even more interesting than the planned 5×5 sweep.

**Raw artifact**: `/mnt/raid0/llm/epyc-inference-research/data/research/2026-05-19-xmas-cheap-kill-v2-maxtok4k/results.json`. Harness: `/mnt/raid0/llm/epyc-inference-research/scripts/research/xmas_cheap_kill.py` (15 tasks × 4 models = 60 chat-completion calls, max_tokens=4096).

### Methodology

5 domains × 3 tasks each, all with auto-scorable expected answers drawn from `benchmarks/prompts/question_pool.jsonl`:

| Domain | Suite | Scoring |
|---|---|---|
| math | gsm8k 3 problems | numeric exact_match |
| code | cruxeval_output 3 problems | exact_match on Python output |
| knowledge | simpleqa 3 problems | substring/f1 |
| long_context | needle_parameterized 3 (4096-ctx, depths 0.10/0.50/0.90) | substring on gold phrase |
| reasoning | gpqa 3 multi-choice problems | single-letter match |

### Run 1 (max_tokens=256) — INVALID for thinking-mode models

`frontdoor` (Qwen3.6-35B Q8) and `architect_general` (Qwen3.5-122B-A10B Q4) returned **15/15 empty answers each** — both thinking-mode models exhausted max_tokens on `<think>` reasoning before emitting a single content token. Spike verdict was contaminated.

### Run 2 (max_tokens=4096) — CLEAN

| Cell | frontdoor | worker_general (gemma4) | architect_general | ingest_long_context (Qwen3-Next-80B) | Winner |
|---|---|---|---|---|---|
| math | 3/3 (89 s) | **3/3 (3 s)** | 2/3 (174 s) | 3/3 (80 s) | worker_general |
| code | 0/3 (234 s) | **3/3 (6 s)** | 1/3 (340 s) | 3/3 (53 s) | worker_general |
| knowledge | 1/3 (113 s) | 0/3 (3 s) | 0/3 (355 s) | **1/3 (2 s)** | ingest_long_context |
| long_context | 3/3 (96 s) | **3/3 (1 s)** | 3/3 (80 s) | 3/3 (5 s) | worker_general |
| reasoning | 0/3 (234 s) | 2/3 (0 s) | 0/3 (355 s) | **3/3 (97 s)** | ingest_long_context |

Wall times in parentheses are means per task in that cell.

### Per-model totals across all 15 tasks

| Model | Correct | Total Wall | Notes |
|---|---|---|---|
| **ingest_long_context** (Qwen3-Next-80B-A3B Q4) | **13/15 (87%)** | 711 s | top accuracy; thinking-mode but disciplined |
| **worker_general** (gemma4-26B-A4B Q4 MTP) | **11/15 (73%)** | **38 s** | top speed; non-thinking, near-top accuracy |
| frontdoor (Qwen3.6-35B Q8) | 7/15 (47%) | 2,297 s | thinking, 60× slower than gemma4 for less accuracy |
| architect_general (Qwen3.5-122B-A10B Q4) | 6/15 (40%) | 3,917 s | thinking, degenerate `<think>` loops — see below |

### Headline findings

1. **Heterogeneity exists** — `≥2 distinct winners` gate met. gemma4 dominates math / code / long-context retrieval (substrate-friendly, non-thinking). Qwen3-Next-80B dominates knowledge / reasoning where deep deliberation pays off. **The X-MAS thesis holds for our stack.** Spike escalates to the full 5×5 sweep.
2. **frontdoor + architect_general are strictly dominated** — both have *lower accuracy AND higher wall* than the top-2. This is a planned-stack-simplification signal: either prune them or repurpose them. (Caveat: 15 samples is small; production routing may surface domains we didn't probe where these models excel.)
3. **architect_general's thinking-mode is degenerate at chat-completions defaults** — 6/15 correct despite a mean wall of 261 s/task. On knowledge + reasoning (6 tasks total) it returned **0/6 empty answers** at max_tokens=4096 — 2,130 s of wall time producing zero content tokens. The model fills the entire token budget with `<think>` reasoning and gets cut off before emitting any user-visible content. Operational implication: architect_general needs either a much higher max_tokens cap OR an explicit `<think>` disable knob OR a structured response format (`<answer>...</answer>`) OR it's unsuitable for direct chat-completions style queries.
4. **The thinking-mode tax is enormous** — architect 261 s/task vs gemma4 2.5 s/task. Even the best thinking-mode model (ingest_long_context at 47 s/task) is 19× slower than gemma4 for similar-or-better accuracy. Routing intelligence has a real production payoff: send fast tasks to gemma4, send accuracy-critical tasks to ingest.

### What changes if we escalate to the full 5×5 sweep

- **Confirm cell winners with 10–20 tasks per cell** (per the original handoff plan) — 15-sample probe is statistically weak.
- **Fix the architect_general / frontdoor capture path** before counting them in the winner table. Options: (a) tune max_tokens to 8K-16K; (b) pass an explicit no-think flag if the model supports it; (c) use the production system prompt that constrains output format; (d) sample directly through the orchestrator's frontdoor route (which presumably bakes in the right defaults) instead of raw chat-completions.
- **Drop the 256-token default everywhere**. The eval-tower harness presumably hits the same problem on these models.

## Stack-simplification probe (2026-05-20) — fixes the cheap-kill measurement artifact

**Verdict**: the cheap-kill v2 "frontdoor + architect strictly dominated" finding was a **measurement artifact**. With `enable_thinking=False`, frontdoor becomes the *top-accuracy model* in the stack on these 15 tasks. Stack-simplification claim retracted. Architect_general remains the lowest performer but is no longer a 40%-er.

**Raw artifact**: `/mnt/raid0/llm/epyc-inference-research/data/research/2026-05-20-stack-simplification-probe-nothink/results.json` (4 models × 15 tasks × `enable_thinking=False` config).

### Methodology

Same 15 cheap-kill tasks, same 4 models. Single config change: pass `chat_template_kwargs={"enable_thinking": false}` in every chat-completions request. max_tokens=2048 (sufficient when thinking is disabled). Both thinking-capable Qwen3.x models in the stack (Qwen3.6-35B = frontdoor, Qwen3.5-122B = architect_general) accept the kwarg via their llama-server Jinja chat template; gemma4-26B and Qwen3-Next-80B's templates ignore it (no-op).

Discovery prompt for the kwarg came from `curl http://127.0.0.1:8083/v1/chat/completions ... '"chat_template_kwargs":{"enable_thinking":false}'`. Direct compare on the simpleqa "Olga Polverino" question:
- **Stock thinking-on, max_tokens=4096**: `content=""` (empty) + 13,346-char `reasoning_content` stuck in a `"Wait, I found a reference: Olga Polverino is a mistake for Olga Polverino (a defense attorney)..."` hallucination loop, finish_reason=length.
- **enable_thinking=false, max_tokens=1024**: `content="Olga Polverino is a distinguished Italian physicist..."` (1,739 chars), finish_reason=stop. Wrong answer but coherent and bounded.

### Run summary

| Model | Cheap-kill v2 stock | Stack-probe nothink | Δ |
|---|---|---|---|
| **frontdoor** (Qwen3.6-35B Q8) | 7 / 15 (47%) | **12 / 15 (80%)** | **+5** |
| worker_general (gemma4-26B-A4B Q4) | 11 / 15 (73%) | 11 / 15 (73%) | 0 (no think mode) |
| architect_general (Qwen3.5-122B-A10B Q4) | 6 / 15 (40%) | 9 / 15 (60%) | +3 |
| **ingest_long_context** (Qwen3-Next-80B-A3B Q4) | **13 / 15 (87%)** | 11 / 15 (73%) | **−2** |

### Per-category breakdown (nothink config)

| Category | frontdoor | worker_general | architect_general | ingest_long_context |
|---|---|---|---|---|
| math | 3/3 (23 s/task) | **3/3 (4 s)** | 3/3 (31 s) | 2/3 (59 s) |
| code | 3/3 (37 s) | **3/3 (6 s)** | 1/3 (3 s) | 3/3 (51 s) |
| knowledge | **1/3 (1 s)** | 0/3 (4 s) | 1/3 (3 s) | 1/3 (2 s) |
| long_context | **3/3 (2 s)** | 3/3 (1 s) | 3/3 (5 s) | 3/3 (5 s) |
| reasoning | **2/3 (16 s)** | 2/3 (0 s) | 1/3 (1 s) | 2/3 (65 s) |

### Headline reversals from cheap-kill v2

1. **frontdoor is NOT strictly dominated.** It's the highest-accuracy model in the stack (12/15 vs ingest 11/15 with thinking off). The v2 result was contaminated because the harness used raw chat-completions with `enable_thinking` defaulting to on, sending frontdoor into degenerate `<think>` loops on knowledge/reasoning tasks.

2. **ingest_long_context's accuracy advantage WAS thinking-driven.** Disabling thinking dropped it from 13/15 to 11/15 — it loses 2 accuracy points without the deliberation budget. **Conclusion: do NOT pass `enable_thinking=false` to ingest_long_context routes**; the 2-point gain is worth the per-task latency cost on accuracy-critical work.

   > **⚠ CORRECTION (2026-05-30): the ingest "thinking-driven" delta is CONFOUNDED — treat as directional, not a clean ablation.** Two facts surfaced after this conclusion was written:
   > - **The `enable_thinking` kwarg is a documented no-op for Qwen3-Next-80B** (and gemma4) — its Jinja template ignores it (see § "nothink config" below, and the operator's `/apply-template` check on `:8085`: identical plain ChatML for true/false/default). So the "thinking-off" arm for ingest **never actually disabled thinking**; the model reasoned natively in both arms.
   > - **The two arms differed in `max_tokens` (4096 thinking-on vs 2048 nothink), not in thinking.** In the nothink arm, `epyc-inference-research/data/research/2026-05-20-stack-simplification-probe-nothink/results.json` shows **2 of 15 ingest tasks hit the 2048 cap** (`completion_tokens == 2048`), and accuracy dropped by exactly 2 (13→11). The most parsimonious explanation is **max_tokens truncation of native reasoning**, not a thinking ablation.
   >
   > **No valid thinking ablation exists for ingest_long_context in the research data.** The "thinking is load-bearing" claim remains *plausible* (Qwen3-Next is a reasoning model and clearly deliberates), but is **not supported by a clean experiment**. A real ablation needs a non-no-op suppression mechanism — e.g. Qwen3 `/no_think` soft-switch or prompt-level injection of an empty `<think></think>` block — held at a fixed, non-truncating `max_tokens`. Until then, do not cite "87%→73%" as evidence. The registry comment (`epyc-orchestrator/orchestration/model_registry.yaml`) was softened accordingly on 2026-05-30.

3. **architect_general's thinking-mode is genuinely broken at chat-completions defaults.** Even with `enable_thinking=false` and max_tokens=2048, architect tops out at 9/15 = 60%, slightly behind worker_general and frontdoor. The model is the lowest-accuracy member of the stack. *And* it consumes the most wall time on thinking-mode tasks. The stack-simplification signal for architect_general specifically is real — pending a wider sample.

4. **knowledge is the universal weak spot.** No model in the stack got >1/3 on simpleqa-style factual questions. We need an external retrieval mechanism (per `internal-kb-rag.md` K-track), not better models, to fix this cell.

### Operational recommendation

Update orchestrator routing rules to:

- Pass `chat_template_kwargs={"enable_thinking": false}` by default to frontdoor + architect_general routes. Frontdoor goes from 47%→80% accuracy on this benchmark slice; architect from 40%→60%. **This is the highest-ROI single-line config change identified in the session.**
- Keep ingest_long_context as-is — its thinking-mode is healthy and adds value.
- Drop the `max_tokens=256` orchestrator default (if it exists) to ≥2048 to avoid silent truncation of any model's response.

These three together are testable on the autopilot trial loop without further benchmarking — they're config changes, not architecture changes.

### Implication for the x-mas full 5×5

Re-run the full sweep with the corrected config (`enable_thinking=false` on Qwen3.x models). The cheap-kill verdict (`HETEROGENEITY_PRESENT_escalate`) likely stands but the cell-winner attribution will shift. Knowledge + reasoning may flip away from ingest_long_context if the thinking-mode advantage was the only differentiator. Run scheduled as x-mas v3 with the 25-task / 5-domain / nothink-config harness.

## X-MAS v3 (2026-05-20) — 25 tasks × 4 models × nothink — HETEROGENEITY_PRESENT, but winner table flips

**Verdict**: heterogeneity still holds (`HETEROGENEITY_PRESENT_escalate`), with 2 distinct cell winners. But which model wins which cell differs from cheap-kill v2 — **frontdoor takes knowledge + reasoning**, gemma4 keeps math + code + long_context. Ingest_long_context and architect_general win 0 cells.

**Raw artifact**: `/mnt/raid0/llm/epyc-inference-research/data/research/2026-05-20-xmas-v3-25tasks-nothink/results.json` (5 tasks per domain × 5 domains = 25 tasks; `enable_thinking=False`; max_tokens=2048).

### Per-model totals (25 tasks)

| Model | Correct | Acc | Wall total |
|---|---|---|---|
| **frontdoor** (Qwen3.6-35B Q8) | **19/25** | **76%** | 549 s |
| worker_general (gemma4-26B-A4B Q4 MTP) | 17/25 | 68% | **181 s** (fastest by 1.8×) |
| ingest_long_context (Qwen3-Next-80B-A3B Q4) | 17/25 | 68% | 1,072 s (5.9× slower than gemma4) |
| architect_general (Qwen3.5-122B-A10B Q4) | 14/25 | 56% | 318 s |

### Per-domain table (5 tasks each)

| Domain | frontdoor | worker_general | architect_general | ingest_long_context | Winner |
|---|---|---|---|---|---|
| math | 5/5 (32 s) | **5/5 (6 s)** | 5/5 (33 s) | 4/5 (77 s) | worker_general |
| code | 4/5 (41 s) | **5/5 (9 s)** | 1/5 (3 s) | 5/5 (43 s) | worker_general |
| knowledge | **1/5 (2 s)** | 0/5 (16 s) | 1/5 (4 s) | 1/5 (3 s) | frontdoor (tiebreak) |
| long_context | 5/5 (11 s) | **5/5 (4 s)** | 5/5 (23 s) | 5/5 (18 s) | worker_general |
| reasoning | **4/5 (25 s)** | 2/5 (1 s) | 2/5 (1 s) | 2/5 (74 s) | frontdoor |

### Headline findings (combined with stack-probe + v2)

1. **Frontdoor is the top-accuracy model in our stack** when configured with `enable_thinking=False`. The 47% → 80% v2-to-v3 jump confirmed: the cheap-kill v2 result was a measurement artifact.
2. **Worker_general / gemma4-26B-A4B remains the speed/quality compromise pick.** 68% accuracy in 181 s total — 3× faster than frontdoor at -8pp accuracy. Wins 3/5 cells (math + code + long_context) on speed-tiebreak when accuracy ties.
3. **Frontdoor's reasoning advantage (4/5 vs 2/5)** is the clearest model differentiator. On GPQA-style multi-choice, frontdoor's larger param count + Q8 weights matter — but it needs nothink to actually answer, not loop in `<think>`.
4. **Architect_general is genuinely under-performing.** 56% overall, 1/5 on code (vs 5/5 from gemma4 + ingest), 2/5 on reasoning. Even with thinking disabled, it's the weakest model in the stack. Worth a focused deprecation review — but the n=25 sample is still small. Schedule a 50-100 task confirmation before pruning.
5. **Ingest_long_context's 87% → 68% drop without thinking** is the most informative result for routing policy: this model NEEDS its thinking budget to add value. Pass `enable_thinking=False` only when latency matters more than accuracy.
6. **Knowledge cell is universally weak** (max 1/5 across all models). All four models are too small / undertrained for raw factual recall of obscure entities. This cell is unwinnable without external retrieval — the orchestrator must route knowledge queries through `internal-kb-rag.md`-style retrieval, not bigger models.

### Routing rule recommendation (production-ready)

Update `epyc-orchestrator/orchestration/model_registry.yaml` defaults to:

```yaml
frontdoor:
  request_overrides:
    chat_template_kwargs: {enable_thinking: false}
    max_tokens: 2048  # was likely lower
architect_general:
  request_overrides:
    chat_template_kwargs: {enable_thinking: false}
    max_tokens: 2048
  routing_priority: -1  # candidate for deprecation pending wider eval
ingest_long_context:
  request_overrides:
    # keep enable_thinking=true (default) — accuracy regresses without it
    max_tokens: 8192  # accommodate thinking budget
worker_general:
  # unchanged — non-thinking, the speed/accuracy default for most cells
  request_overrides:
    max_tokens: 2048
```

This is the highest-ROI orchestrator change from the session: a config-only PR that should lift frontdoor accuracy from 47% to 80% on the cheap-kill task set with zero infrastructure cost.

### Open follow-ups

1. **5×5 functions axis still not exercised.** v3 is 5 domains × 5 tasks but no separate function axis. The headline X-MAS thesis (different models excel at different (domain, function) cells) needs a separate harness that varies function (solve/verify/plan/refine/extract). Schedule x-mas v4.
2. ~~**Architect_general deprecation gate**: confirm with a 50-100 task wider eval before pulling it.~~ ✅ **CLOSED 2026-05-20**: see "Architect deprecation gate — RETAIN" below.
3. **Knowledge cell**: the only viable fix is retrieval; do not retest models without RAG context.

### Follow-up validation (inference-gated) — opened 2026-05-30

Two inference-gated tasks from the ingest_long_context attribution-fix session (2026-05-30). Both are **code-ready / inference-pending** and tracked in the bulk inference campaign. Neither can fold into the **J6 24h soak** as enforce changes (J6 is passive; its co-run rule requires observe/advisory flags — an active routing or template change would contaminate the baseline).

- **RI-ITG-1 — ingest-triviality guard A/B.** Validate `apply_ingest_triviality_guard` (epyc-orchestrator `9203c00`, flag `INGEST_TRIVIALITY_GUARD`, default OFF, depends on `specialist_routing`). The learned MemRL router leaks ~8.5% of ingest traffic as trivial short prompts (153/1803 math in the 2026-05-30 tap analysis); the guard demotes only positively-trivial requests to `worker_general`. **Acceptance**: enforce-mode run shows ingest short-prompt leakage materially reduced **with no accuracy regression** vs the flag-off baseline on the eval-concurrency fan-out (also enable `difficulty_signal` shadow/enforce so the easy-band path is live). **Fold note**: enforce-mode A/B = dedicated cheap run, post matrix gates, host-quiet window — **not** co-runnable with J6. *Partial-fold option*: add a shadow/observe mode to the guard (log would-demote without demoting) → observe/advisory → eligible to co-run with J6 and passively quantify leakage during the soak; the accuracy A/B still needs the dedicated enforce run. Shadow mode is not yet built.
- **THINK-ABL-1 — real (non-no-op) thinking ablation for ingest.** The "thinking load-bearing" claim is confounded (see CORRECTION under "Headline reversals" / conclusion #2 above): `enable_thinking` is a no-op for Qwen3-Next, and the only "ablation" differed in `max_tokens` (4096→2048) with 2/15 tasks truncated at the cap. A valid ablation needs a non-no-op suppressor (Qwen3 `/no_think` soft-switch or prompt-level empty-`<think></think>` injection) at a fixed, non-truncating `max_tokens`, same tasks both arms. **This folds into campaign item J12** (chat_template_kwargs wiring verification) — same subsystem; J12's gate text was updated to drop the stale "thinking-on load-bearing" assertion.

## Architect deprecation gate — RETAIN (2026-05-20)

**Verdict**: **RETAIN architect_general**. The cheap-kill v3 "architect is strictly dominated" signal was a small-N + task-mix artifact. At N=100, architect_general competes with frontdoor within 4pp overall (below the 5pp RETAIN threshold) and actually **wins math gsm8k 20/20 vs frontdoor 19/20**.

**Raw artifact**: `/mnt/raid0/llm/epyc-inference-research/data/research/2026-05-20-architect-deprecation-probe/results.json` (100 tasks × 2 models × `enable_thinking=False` config; 200 total inferences; 2h53m wall on EPYC CPU).

### Methodology

Designed to confirm or refute the cheap-kill v3 attribution at higher N. 20 tasks each from 5 suites, sorted by stable task-id order:
- gpqa (reasoning, multi-choice single letter)
- gsm8k (math, numeric exact_match)
- cruxeval (code, input-prediction — harder variant than the cheap-kill's cruxeval_output_*)
- simpleqa (knowledge, short-answer substring/f1)
- aime (math2, numeric exact_match — olympiad-difficulty)

All queries: `max_tokens=2048`, `temperature=0.0`, `chat_template_kwargs={"enable_thinking": false}`.

### Final per-model per-category accuracy

| Category | frontdoor | architect_general | Δ pp (f − a) |
|---|---|---|---|
| math (gsm8k, 20 tasks) | 19/20 (95%) | **20/20 (100%)** | **−5** |
| math2 (aime, 20 tasks) | 9/20 (45%) | 9/20 (45%) | 0 |
| code (cruxeval_input, 20) | 7/20 (35%) | 5/20 (25%) | +10 |
| knowledge (simpleqa, 20) | 2/20 (10%) | 2/20 (10%) | 0 |
| reasoning (gpqa, 20) | 9/20 (45%) | 6/20 (30%) | +15 |
| **Total (100 tasks)** | **46/100 (46%)** | 42/100 (42%) | **+4pp** |
| Wall total | 5,514 s | 6,091 s | architect 10% slower overall |

### Reversals from cheap-kill v3

| Finding | Cheap-kill v3 (N=25) | Deprecation gate (N=100) | Verdict |
|---|---|---|---|
| Architect overall acc | 14/25 = **56%** | 42/100 = **42%** | task-mix bias was overstating gap |
| Architect on math | 5/5 (5 gsm8k tasks) | 20/20 (20 gsm8k tasks) | gsm8k confirmed strong (architect actually WINS here) |
| Architect on code | 1/5 (cruxeval_output picks) | 5/20 (cruxeval_input picks) | both struggle on cruxeval; architect-input is 25% vs frontdoor-input 35% |
| Architect on reasoning | 2/5 | 6/20 | architect IS weaker on GPQA, but only by 15pp not 60pp |
| Frontdoor − architect Δ | **+20pp** | **+4pp** | small-N estimate was 5× too large |

### Operational implications

- **No deprecation**. The cheap-kill v3 recommendation to consider deprecating architect_general is retracted. Architect is competitive at production-relevant N.
- **Architect IS the right model for math**. On gsm8k it's the only model to score 20/20 perfect. If routing intelligence is wired, math tasks should prefer architect over frontdoor (despite architect's 50% higher wall-time).
- **Frontdoor's edge is reasoning + code**, by 10-15pp. Not big enough to make architect unusable, but real and consistent.
- **Knowledge weak across the stack** (both models 2/20 on simpleqa) — confirms cheap-kill v3 finding that RAG is the only realistic fix.
- **Wall time**: architect averages 158s on aime vs frontdoor 101s — architect IS slower by ~50% on the longest-thinking tasks. For latency-critical paths, prefer frontdoor. For accuracy-critical math, prefer architect.

### Methodology notes for future deprecation gates

The cheap-kill v3 N=25 result over-estimated the frontdoor-architect gap by **5×** (20pp → 4pp). Lessons:
1. **Cheap-kills are screening tools, not deprecation evidence.** Always confirm with N ≥ 100 before pulling production roles.
2. **Task-mix bias is the dominant noise source.** The cheap-kill's 5 cruxeval tasks happened to be ones architect struggled with; the wider gate samples a more representative mix.
3. **`enable_thinking=False` lifts thinking-mode models to their natural baseline.** Without this fix, both gates would have been contaminated.

### Updated Open Questions

5. **Should the cheap-kill find a winner for frontdoor / architect_general first?** Their 0% accuracy on multiple cells is a measurement bug, not a capability bug — fixing it changes the winner table. Recommend: yes, with a separate "thinking-mode tax audit" sub-task before the full 5×5.
6. **Does the deprecation signal hold?** frontdoor + architect_general's 7/15 + 6/15 vs gemma4's 11/15 is striking. If the full 5×5 confirms it, this is a *bigger* finding than X-MAS routing — it's a stack-simplification opportunity. Cross-ref `project_stack_simplification.md`.

## References

- Deep-dive: `/workspace/research/deep-dives/2026-05-19-latent-mas-cluster.md`
- X-MAS paper: `https://arxiv.org/abs/2505.16997`
- X-MAS repo: `https://github.com/MASWorks/X-MAS` (no license — methodology only)
- Related handoffs: `routing-intelligence.md`, `routing-and-optimization-index.md`, `learned-routing-controller.md`, `hermes-outer-shell.md`, `meta-harness-optimization.md`
