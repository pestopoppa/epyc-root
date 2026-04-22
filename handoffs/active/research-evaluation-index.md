# Research & Evaluation — Coordination Index

**Status**: active
**Created**: 2026-04-04
**Purpose**: Entry point for agents working on pre-production research, evaluation, and monitoring tasks. These handoffs track techniques and tools not yet targeting production deployment.

---

## Agent Operating Instructions

1. Read the **Outstanding Tasks** section to find actionable work
2. Most handoffs here are stubs or monitoring — check status before investing time
3. After completing work: update the task checkbox here, update the handoff document, update `progress/YYYY-MM/YYYY-MM-DD.md`
4. Do NOT modify production orchestrator code from this index — production changes go through `routing-and-optimization-index.md`

---

## Subsystem Status

| Handoff | Domain | Status | Priority | Last Updated |
|---------|--------|--------|----------|-------------|
| [reasoning-compression.md](reasoning-compression.md) | Reasoning token optimization | in-progress (Tier 1 deployed, Actions 12-15 done, TALE eval complete — static limits kept) | HIGH | 2026-04-11 |
| [tool-output-compression.md](tool-output-compression.md) | Tool token optimization (output + definition) | Phase 2 done, A/B done (+4pp REPL), Phase 3a-b done (55% def compression). P3d A/B pending. **2026-04-20**: intake-414/415 deep dives add subprocess sandbox pattern (Phase 3 MCP workaround) + 5KB threshold gating + FTS5 indexing. | MEDIUM | 2026-04-20 |
| [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md) | Sub-quadratic attention survey | active (literature survey complete, priority ranking established) | LOW | 2026-04-14 |
| [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md) | Log-Linear GDN readiness | stub (MONITORING) — blocked on pretrained models | HIGH | 2026-04-14 |
| [yarn-context-extension-research.md](yarn-context-extension-research.md) | Context extension via YaRN | stub | LOW | 2026-03-25 |
| ~~[long-context-eval-datasets.md](long-context-eval-datasets.md)~~ | Eval dataset collection | COMPLETE (5 datasets, adapters integrated, moved to completed/) | — | 2026-04-05 |
| [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md) | TQ3/TurboQuant monitoring | monitoring (do NOT merge) | LOW | 2026-04-01 |
| ~~[11-conceptlm-monitoring.md](../archived/11-conceptlm-monitoring.md)~~ | Concept-level LM monitoring | ARCHIVED (stale, no models available) | — | 2026-03-03 |
| ~~[knowledge-base-governance-improvements.md](knowledge-base-governance-improvements.md)~~ | KB linter, credibility scoring, anti-bias, project-wiki skill | COMPLETE (moved to completed/) | — | 2026-04-07 |
| [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | Block-level reasoning compression (KV masking) | active (S1 llama.cpp feasibility) | HIGH | 2026-04-09 |
| [repl-turn-efficiency.md](repl-turn-efficiency.md) | REPL turn reduction (frecency + combined ops) | in-progress (S1-S3a ✅, S5 design ✅, S6a-f bug fixes ✅ 2026-04-16, S4 A/B pending inference) | MEDIUM | 2026-04-16 |
| [root-archetype-linter-templates-upstream.md](root-archetype-linter-templates-upstream.md) | Linter + brevity templates upstream | in-progress | MEDIUM | 2026-04-09 |
| Ouro LoopLM Evaluation (P7) | Looped LM reasoning verifier | NEW — download + CPU benchmark + T0 sentinel eval | MEDIUM | 2026-04-12 |
| [eval-tower-verification.md](eval-tower-verification.md) | Eval tower calibration + process verification | NEW — ECE/AUC metrics, ThinkPRM T2, cross-family verification, Scoring Verifiers benchmarks | MEDIUM | 2026-04-14 |
| (intake-412) DeepPlanning benchmark | Agent planning eval methodology | Reference — rule-based automated scoring, 26-model leaderboard, reasoning gap 7-16pp | LOW | 2026-04-20 |
| (intake-421) MAD confidence scoring | AutoPilot safety gate noise filter | **adopt_component** — ~20 LoC addition to safety_gate.py. Deep dive: [pi-autoresearch-mad-scoring.md](../../research/deep-dives/pi-autoresearch-mad-scoring.md) | MEDIUM | 2026-04-20 |
| (intake-422) TIDE early exit | Calibration-router for per-token layer skip | **adopt_patterns** — implement on fork n_layer_exit. Deep dive: [tide-calibration-router-early-exit.md](../../research/deep-dives/tide-calibration-router-early-exit.md) | MEDIUM | 2026-04-20 |
| [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) | GLM-5.1-555B-A14B-REAP CPU eval | **NEW** — download pending, storage-constrained (325GB model, 417GB free). 9-phase eval plan. | MEDIUM | 2026-04-22 |
| (intake-426) Compaction gap analysis | Map Claude Code five-layer pipeline vs our L1-L5 | Monitoring — design task from intake-426 deep dive | LOW | 2026-04-22 |

---

## Outstanding Tasks (Priority Order)

### P0 — Reasoning Compression (actionable now)

- [x] Run TrimR evaluation on math/gpqa suites — ✅ 2026-04-09 (Package B). DeepSeek-R1-7B 4×48t. GPQA: thinking helps ~6pp. Math: thinking irrelevant (151 tok avg). TrimR valuable on hard tasks only.
- [x] Collect shadow telemetry from `difficulty_signal.py` in production — ✅ 2026-04-06. 635 requests, Package A run.
- [x] Validate difficulty signal predictive power against benchmark accuracy — ✅ 2026-04-09 (Package B Phase 4). At 0.15/0.35: NO predictive spread — escalation rate flat across easy/medium/hard (62/61/62%). Signal does not differentiate routing needs at current thresholds.
- [ ] If validated: implement enforce mode — **BLOCKED**: difficulty signal has no predictive power at current thresholds. Need semantic features or different approach before enforce.
- [x] Compute Omega metric per-suite — ✅ 2026-04-09 (Package B Phase 4). **7/10 suites: tools HURT accuracy** (direct > REPL). Worst: agentic -54pp, coder -44pp, general -26pp. Only hotpotqa +12pp and gpqa +6pp benefit.
- [ ] **Action 10a (2026-04-22, DD3)**: STOP learnable path pruning probe — prefix-level learnable super-token fills an unoccupied quadrant (internal × learnable × selection) in the reasoning-compression taxonomy. Composes with all Tier 1 techniques (TrimR, short-m@k, difficulty bands). 5-inference-day probe plan with AUC ≥ 0.75 gate. **Gated on NIB2-32 difficulty-signal re-validation** (needs telemetry accumulated post-NIB2-35 fix). → `reasoning-compression.md` Action 10a + DD3 deep-dive (`/workspace/research/deep-dives/stop-learnable-path-pruning.md`).

### P1 — Tool Output Compression

- [x] ~~Install RTK binary~~ — SKIPPED: PostToolUse hooks cannot replace built-in tool output. Phase 0 RTK trial deferred.
- [x] Phase 2 native compression module — ✅ 2026-04-05. `compress_tool_output.py` with 7 handlers (pytest, cargo test, git status/diff/log, ls, build). 27 tests.
- [x] Orchestrator integration — ✅ 2026-04-05. Feature flag `tool_output_compression` (env `TOOL_OUTPUT_COMPRESSION`). Wired at `helpers.py:1497` before `_spill_if_truncated()`.
- [ ] Enable flag in production and measure net savings on real autopilot sessions
- [x] A/B comparison: tool_output_compression on vs off — ✅ 2026-04-10 (Package B). Controlled A'/B' rerun (5 suites × 20q, WS-3 fix active). **Compression +4pp REPL overall.** Suite-dependent: math +25pp (noise reduction), hotpotqa -25pp (retrieval context lost). No change to default (ON).
- [x] P3a: Token audit of tool definitions — ✅ 2026-04-09. `token_audit.py` + report. 841 tokens, 4 duplicates, 29.8% instruction ratio.
- [x] P3b: Manual compression of `DEFAULT_ROOT_LM_TOOLS` — ✅ 2026-04-09. 55% reduction (647→290 words). Old preserved as `VERBOSE_ROOT_LM_TOOLS`. Ratio → 16.0%.
- [ ] P3d: A/B test compressed vs original on seeding harness

### P2 — Reasoning Compression (deferred)

- [x] Generate SEAL control vectors — ✅ 2026-04-13. Multi-role regression test:
  - **Worker 30B-A3B Q4KM**: 7/7→7/7 correct, **-7.5% tokens**, NO regression
  - **Coder 32B Q4KM**: 7/7→7/7 correct, +2.2% tokens (neutral), NO regression
  - **Accuracy check (30B)**: cvector 5/5 vs baseline 4/5 — accuracy *improved*
  - Scale sweep (30B): 0.3=-10.3%, 0.5=-28.4%, 0.7=-28.5% (saturates at 0.5)
  - Frontdoor 35B SSM: BLOCKED — heterogeneous block architecture (SSM/attention alternating), loader expects uniform. Needs llama.cpp model arch fix.
  - REAP 246B: deferred (139GB cvector training too slow for this session)
  - Cvectors: `models/qwen3-coder-30b-seal-concise.gguf`, `models/qwen2.5-coder-32b-q4km-seal-concise.gguf`, `models/qwen2.5-7b-seal-concise.gguf`
  - **Production deployment**: CONDITIONAL — gains are task-type-dependent, not blanket. Worker reasoning tasks see -12% to -18% per problem, but code/concise tasks see 0%. Deploy via `orchestrator_stack.py --control-vector-scaled` gated by routing classifier `task_type == reasoning/math`. Coder role shows +2.2% (neutral). Implementation deferred until experimental kernel merges to production.
- [ ] Summarizer quality assessment — `eval_summarizer.py` READY (created 2026-04-07), needs model servers to run (→ Package C)
- [ ] Free-zone compression threshold sweep — `eval_compaction_sweep.py` READY (implemented 2026-04-07), needs model servers to run (→ Package C)
- [x] Helpfulness scoring calibration — ✅ 2026-04-07. `run_calibration()` implemented (pure heuristic). Tested on 250 traces: Spearman ρ=0.63-0.65, overlap-heavy config best (separation=0.37, NDCG=0.998). Package C LLM-based Δ_k eval still pending.

### P2.5 — Memento Block Reasoning Compression (Tier 3+ research)

See [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md). Deep-dive: `research/deep-dives/memento-iterative-reasoning-cluster.md`.

- [x] S1: llama.cpp block masking feasibility — ✅ 2026-04-13. **FEASIBLE**: `llama_memory_seq_rm()` (corrected API name) supports mid-sequence range eviction, position gaps preserved (correct for Memento dual-info-stream). Test skeleton at `llama.cpp-experimental/tests/test-memento-block-masking.cpp`. Paged attention block tracking has a gap for partial removal (metadata leak, non-blocking). Runtime validation awaiting model server.
- [ ] S2: LoRA SFT on Qwen3-32B using OpenMementos-228K. Two-stage (format + compression learning). Blocked on S1.
- [ ] S3: Deployment integration — block masking + Fold/Unfold toggle + m@k voting + Hadamard q4_0 stacking. Blocked on S1+S2.

### P3 — Long-Context Evaluation Datasets

- [x] Download LongBench — ✅ 2026-04-05. Using v2 (parquet-native, 503 MCQ). v1 uses deprecated HF scripts.
- [x] Download RULER — ✅ 2026-04-05. Cloned, adapter generates NIAH tasks at configurable lengths.
- [x] Download ZeroSCROLLS — ✅ 2026-04-05. 538 examples (10 tasks), raw zip download.
- [x] Download L-Eval — ✅ 2026-04-05. 514 examples (20 tasks), raw JSONL download.
- [x] Complete Needle-in-a-Haystack integration — ✅ 2026-04-05. Parameterized: 5 lengths × 5 depths = 25 tests. Paul Graham essays haystack.
- [x] Create adapter scripts — ✅ 2026-04-05. `long_context_adapters.py` (5 classes), registered in `dataset_adapters.py` + `suites.py`.
- [x] Validation — ✅ 2026-04-05. All 5 suites: OK (1,630 total questions).

### P3b — Tulving Episodic Memory Benchmark (from intake-408 deep-dive)

Source: "Episodic Memories Generation and Evaluation Benchmark for LLMs" (arXiv 2501.13121, ICLR 2025). 11 synthetic datasets (10K/100K/1M tokens), deterministic F1 scoring, 36 question templates testing entity tracking + temporal ordering. Complements existing RULER/NIAH/LongBench/ZeroSCROLLS suite — tests episodic memory (state tracking, chronological reasoning), not just retrieval.

**Key deep-dive findings**: Scoring is 95% deterministic (string matching against known ground truth tokens — dates, locations, entity names). LLM-as-judge only handles ~5% fuzzy cases. Reasoning models (o1, DeepSeek-R1) catastrophically fail at 100K tokens despite near-perfect scores at 10K. Gemini-2.5 is anomalously robust (-1.4% recall drop from 10K→100K vs -61% for o1).

- [ ] Download pre-generated 20ch dataset from Figshare (10K tokens, 456 QA pairs). No generation pipeline needed.
- [ ] Write llama-server adapter for answer generation (replace OpenAI/Anthropic API calls with `/completion` endpoint)
- [ ] Implement deterministic F1 scorer: exact + normalized string matching against known ground truth. Covers ~95% of cases. Optional LLM-as-judge fallback for remaining ~5%.
- [ ] Register as new suite in `dataset_adapters.py` + `suites.py`. Report Simple Recall Score + Chronological Awareness Score per model/quant.
- [ ] Run 20ch benchmark on all production models (10K context — any model handles this)
- [ ] (Deferred to P4) Download 200ch dataset (100K tokens, 686 QA pairs) for YaRN quality gating

### P4 — YaRN Context Extension (when datasets ready)

- [ ] Benchmark quality degradation curve from 256K → 512K → 1M with YaRN
- [ ] Measure KV cache memory impact at 1M context
- [ ] Measure speed impact of YaRN extension
- [ ] Run Tulving 200ch (100K) benchmark under YaRN — catches temporal reasoning failures that RULER/NIAH miss. Sharp cliff expected: most models lose 30-60% recall from 10K→100K. Chronological awareness degrades faster than recall at every scale transition.

### P5 — Harness Engineering Experiments (from intake-271/272/273/274 deep-dive)

- [ ] Bullet-vs-narrative consolidation A/B test: run CF Phase 2a eval suite with two compaction summary formats (structured narrative vs flat bullet-point). Tests whether context rot shuffled finding (intake-273) has signal for reasoning tasks. Low cost, high signal. (→ Package C)
- [ ] Documentation-stripped ablation: replicate intake-272 methodology on our repos. Strip all `.md`, run evals with vs without thin-map agent files. Isolates whether our agent files provide value beyond existing documentation. (→ Package B or standalone)
- [ ] `task_relevance` as candidate 5th signal in `segment_helpfulness()`: prototype semantic similarity (all-MiniLM-L6-v2, CPU) between segment text and current task description. Depends on bullet-vs-narrative results before shipping. (Design only until Package C data)

### P6 — REPL Turn Efficiency (from intake-295/301)

See [repl-turn-efficiency.md](repl-turn-efficiency.md). Addresses the Omega finding: 7/10 suites where REPL tools hurt accuracy. Complementary to WS-1/WS-3 prompt-level fixes.

- [x] S1a: Implement `file_recency.py` frecency module — ✅ 2026-04-09. `FrecencyStore` class, SQLite, 10 tests.
- [x] S1b-c: Wire into `_list_dir()` + `code_search()` (feature-flagged `REPL_FRECENCY`) — ✅ 2026-04-09. 7 wiring tests.
- [x] S2a-b: Mine autopilot logs + implement combined ops — ✅ 2026-04-09. Finding: only web_search/search_wikipedia used (file tools never called). `_CombinedOpsMixin` with `batch_web_search`, `search_and_verify`, `peek_grep`. Flag: `REPL_COMBINED_OPS`. 18 tests.
- **Note**: `batch_web_search` in `_CombinedOpsMixin` calls `web_search()` directly. When SearXNG backend is deployed (see [`searxng-search-backend.md`](/workspace/handoffs/active/searxng-search-backend.md), R&O P12), `batch_web_search` inherits SearXNG JSON API automatically — no code change needed in combined_ops.
- [ ] S4: A/B benchmark turn count reduction on seeding harness

### P7 — Ouro LoopLM Evaluation (from intake-332/341)

Source: Ouro-2.6B-Thinking (ByteDance, Apache-2.0) achieves 90.85% MATH-500 and AIME24 pass@10 90% at only 2.6B params via looped architecture. RLTT post-training adds +14.4% MATH-500. Not llama.cpp compatible (looped arch), but runs via `transformers` on CPU at ~5-10 tok/s.

- [ ] Download Ouro-2.6B-Thinking from HuggingFace (`ByteDance/Ouro-2.6B-Thinking`, Apache-2.0). Pin transformers==4.54.1 (KV cache bug in 4.56+).
- [ ] Run MATH-500 benchmark via transformers on EPYC CPU. Verify claimed 90.85% accuracy. Measure actual throughput (expect ~5-10 tok/s at 2.6B params with 192 threads).
- [ ] Evaluate as T0 sentinel verification candidate — can Ouro verify math/reasoning outputs from our larger models? (Cross-ref: autopilot AP-27 RLVR formalization)
- [ ] Monitor for RLTT-trained checkpoint release (Princeton). If released, rerun MATH-500 comparison.
- [ ] Monitor llama.cpp for LoopLM architecture support (would enable GGUF deployment).

### P8 — Eval Tower Verification Framework (2026-04-14 deep-dive research)

Source: Deep-dive synthesis of intake-363 (LLM-as-a-Verifier), intake-367 (Scoring Verifiers), intake-368 (SWE-RM), intake-370 (Aletheia), intake-371 (ThinkPRM). Provides calibration and process verification infrastructure for AP-27 RLVR formalization. See [`eval-tower-verification.md`](eval-tower-verification.md).

- [ ] **EV-0** (new, 2026-04-15): Audit eval datasets for question quality using MathQ-Verify (intake-379) stages 1-4. Skip stage 5 (completeness hurts F1 +0.57pp). Flawed questions waste budget AND inflate reasoning tokens (arxiv:2504.06514). Zero-code data cleaning step.
- [x] **EV-1**: Add `logprob_confidence` to `QuestionResult` — ✅ 2026-04-15. Binary confidence proxy (`float(correct)`); real logprob values pending infrastructure passthrough.
- [x] **EV-2**: Implement ECE + AUC in `_aggregate()` — ✅ 2026-04-15. 10-bin ECE, sklearn AUC with degenerate fallback, calibration violation count. Trivially 0 with binary proxy; meaningful once continuous confidence lands.
- [ ] **EV-3**: Download Scoring Verifiers benchmarks from HuggingFace `nvidia/Scoring-Verifiers`, create adapter (~50 lines)
- [ ] **EV-4**: Run calibration baseline on Scoring Verifiers benchmarks (needs inference)
- [ ] **EV-5**: Deploy ThinkPRM-1.5B-Q4KM for T2 process verification (~100 lines, needs model download)
- [x] **EV-6**: Cross-family verification constraint enforcement — ✅ 2026-04-15. `VERIFICATION_FAMILIES` dict + `check_cross_family()` in `eval_tower.py`. Supports Qwen/Llama/DeepSeek/Ouro/Mistral/Gemma. Permissive default (unknown families pass).
- [ ] **EV-7**: AP-27 RLVR integration (depends on EV-1–4 + Ouro P7)
- [ ] **EV-8** (NEW 2026-04-22, DD4): **Diversity metrics in EvalResult** — add `diversity_entropy`, `diversity_distinct2`, `diversity_self_bleu`, `diversity_ttr` fields to `EvalResult` at `safety_gate.py`. Implement `diversity_metrics.py` scoring. Wire `to_grep_lines()`. Baseline pass on 4 production roles (architect_general/architect_coding/coder/worker). SafetyGate rule: reject checkpoint if distinct-2 drops >20% AND quality not up. **Blocking prerequisite** for any future checkpoint swap — intake-441 shows post-training diversity loss is structural and inference-time-irrecoverable. Deep dive: `/workspace/research/deep-dives/diversity-collapse-posttraining.md`.
- [ ] **EV-9** (NEW 2026-04-22, DD7): **Multi-dimensional rubric extension** — extend `EvalResult` with reasoning-trajectory / tool-call / outline / content-stage rubric fields. 20-40 research-like sentinel queries (`deep_research_sentinel` suite). Supports `minddr-deep-research-mode.md` Phase 1 A/B evaluation (MD-7). LLM-as-judge with deterministic fallback for T1.
- **Math-Verify integration note** (intake-377, 2026-04-15): `score_answer_deterministic()` underestimates math capability by ~66%. EV-4 calibration baseline and S4 formalizer eval should use Math-Verify for answer comparison. See `eval-tower-verification.md` 2026-04-15 update for caveats (NOT symmetric, NOT thread-safe). Deep dive: `research/deep-dives/math-verify-integration-analysis.md`.

### P2.5 — Knowledge Base Governance (from intake-268/269/270/277)

- [x] **Phase 5a**: Create `wiki.yaml` config, fix hardcoded paths, create `wiki/SCHEMA.md` living taxonomy — ✅ 2026-04-07
- [x] **Phase 5b**: Build lint operation into project-wiki skill (5 passes, config-driven) — ✅ 2026-04-07
- [x] **Phase 5c**: Build query operation ("what do we know about X?") — ✅ 2026-04-07
- [x] Add credibility scoring to research-intake skill Phase 2 — ✅ 2026-04-07
- [x] Add anti-confirmation-bias directive to research-intake Phase 3 — ✅ 2026-04-07
- [x] Add parallel execution model (fan-out sub-agents for 3+ URLs, Phase 1+2) — ✅ 2026-04-17
- [x] Update intake-268/269/270 verdicts and cross-references — ✅ 2026-04-06
- [x] **Phase 5d**: Upstream project-wiki skill to root-archetype — ✅ 2026-04-07
- [x] Session persistence documentation for research workflows — ✅ 2026-04-07
- [x] qmd semantic search addon documentation — ✅ 2026-04-07

### P0.5 — Brevity Prompt Upgrade (from intake-276 deep-dive)

- [x] **Action 12**: Replace "be concise" with explicit word limits in worker prompts — ✅ 2026-04-09. Format-specific templates in worker_general.md + worker_math.md.
- [x] **Action 13**: Model-tier-differentiated conciseness — ✅ 2026-04-09. Audit + thinking_reasoning suffix update.
- [x] **Action 14**: Add OAA metric + per-token intelligence measurement to eval framework — ✅ 2026-04-07.
- [x] **Action 15**: TALE eval — ✅ 2026-04-11 (Package C). Static limits (Action 12) outperform TALE on OAA (baseline 95%, static 75%, TALE 72.5%). TALE matches baseline on math but hurts general. **Decision: keep static limits, TALE deferred.**
- [x] Upstream linter + templates to root-archetype — ✅ 2026-04-09. Generalized `lint_wiki.py` (dynamic root, configurable paths). 4 brevity templates in `_templates/prompts/`. Companion handoff: [root-archetype-linter-templates-upstream.md](root-archetype-linter-templates-upstream.md).

### Monitoring (no action unless triggered)

- [ ] **TQ3**: Watch PR #21038 for merge, evaluate PR #21089 when merged, read ChunkKV paper
- ~~**ConceptLM**: Quarterly check for open-weight concept-level models or framework support~~ (archived)
- [ ] **Multiscreen**: Monitor for community reproduction, model releases, or llama.cpp PRs
- [ ] **Log-Linear GDN**: Watch github.com/HanGuo97/log-linear-attention and NVlabs/GatedDeltaNet for pretrained model releases. Activates [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md).
- [ ] **Compaction gap analysis** (intake-426): Map Claude Code's five-layer pipeline (budget reduction, snip, microcompact, context collapse, auto-compact) against our L1-L5 tiers. Identify whether a "Budget Reduction" equivalent (per-message output size caps) is warranted. See [context-folding-progressive.md](context-folding-progressive.md) Research Intake Update 2026-04-21. Design task — no code until gap significance is assessed.

---

## Dependency Graph

```
P0 (reasoning-compression TrimR)  ──independent──
P1 (tool-output-compression RTK)  ──independent──
P2 (reasoning SEAL vectors)       ──depends on model server availability──
P2.5 (KB governance improvements) ──independent (companion: root-archetype linter)──
P3 (long-context datasets)        ──independent──
P3b (Tulving episodic benchmark)  ──independent (20ch); 200ch deferred to P4──
P4 (YaRN extension)               ──depends on P3 (datasets) + P3b 200ch──
P5 (harness engineering experiments)  ──depends on P3 (datasets) + Package B/C results──
P6 (REPL turn efficiency)            ──S1 independent; S2 depends on autopilot log data; S4 depends on seeding harness──
P7 (Ouro LoopLM eval)               ──independent (download + benchmark)──
P8 (eval tower verification)         ──EV-1/2/6 DONE (2026-04-15); EV-0/3 independent; EV-4/5 need inference; EV-7 depends on all + P7──
GLM-5.1-REAP eval                    ──independent (download + benchmark); stack simplification depends on quality results──
Compaction gap analysis               ──independent (design task from intake-426)──
TQ3 monitoring                    ──depends on upstream PR merges──
ConceptLM monitoring              ──depends on external model releases──
Multiscreen monitoring            ──depends on external adoption──
```

---

## Cross-Cutting Concerns

1. **Reasoning compression ↔ routing-intelligence**: TrimR evaluation uses `debug_scorer.py`, same scorer infrastructure as factual-risk routing. `difficulty_signal.py` (shadow mode) is shared between reasoning token budgets and routing decisions. Changes to scorer must be coordinated.

2. **Tool output compression ↔ context-folding**: Complementary layers — tool-output-compression reduces inputs, context-folding compresses conversation history. Together they multiplicatively reduce context pressure. Phase 0 RTK trial results should inform context-folding Phase 1 design (if RTK handles tool outputs, Phase 1 can focus purely on conversation history).

3. **Long-context datasets ↔ KV cache quantization**: Datasets collected here serve both YaRN evaluation and TurboQuant KV cache quality validation (kv-cache-quantization.md Phase 3d). Coordinate dataset format with benchmark scripts.

4. **Summarizer quality ↔ context-folding Phase 2a/2b/2c**: Phase 2b (free-zone sweep) and Phase 2c (helpfulness calibration) both require eval infrastructure. Helpfulness calibration (LLM-based Δ_k ground truth) is the most expensive eval — schedule with other benchmark runs. Literature basis: Skill0 (intake-261) helpfulness-driven curriculum, AgentOCR (intake-262) compression quality thresholds.: reasoning-compression's summarizer quality assessment and context-folding Phase 2 share the same eval methodology (Claude-as-Judge scoring). Implement once, use in both.

5. **Bulk Inference Campaign**: Tasks P0 (TrimR, Omega, difficulty validation), P1 (tool compression A/B), and P2 (summarizer quality, free-zone, helpfulness) are consolidated into Packages B and C of [`bulk-inference-campaign.md`](bulk-inference-campaign.md). Package B (seeding eval v2) resolves P0+P1 tasks in a single full-stack run. Package C (CF eval batch) resolves P2 tasks using individual model servers. See that handoff for execution schedule, feature flags, and success criteria.

7. **Knowledge base governance ↔ root-archetype**: The KB linter and skill template patterns from P2.5 are being upstreamed to root-archetype via a companion handoff (`/mnt/raid0/llm/root-archetype/handoffs/active/knowledge-base-linter.md`). Epyc-root deploys the linter first as an instance-specific validator, then the generalized version goes to root-archetype. The credibility scoring and anti-confirmation-bias changes are research-intake skill edits that may also be templated in root-archetype's skill scaffold.

8. **Tool output compression ↔ Complexity Trap validation**: intake-274 ("The Complexity Trap") validates our two-layer architecture — pattern-based tool compression upstream, LLM conversation summarization downstream. The hybrid finding (7-11% further cost reduction) confirms this design is near-optimal. Package B tool compression A/B will be the first empirical confirmation on our stack. This also informs context-folding: observation masking (stripping old tool outputs) is equivalent to high recency weight in `segment_helpfulness()`.

10. **Eval tower verification ↔ AP-27 ↔ Ouro P7**: `eval-tower-verification.md` (P8) provides calibration and process verification infrastructure that AP-27 (RLVR formalization) requires. Ouro P7 (Ouro-2.6B-Thinking eval) feeds into EV-7 as a T0 sentinel verifier candidate. ThinkPRM deployment (EV-5) adds cross-family verification distinct from the Ouro sentinel role. Decision-aware routing (R&O P13) changes the reward signal that the eval tower evaluates — calibration metrics (ECE, AUC) must validate the new signal. Source: 2026-04-14 deep-dive (intake-363/367/368/370/371).

9. **REPL turn efficiency ↔ Omega problem**: Turn reduction (P6) and WS-1/WS-3 prompt fixes address the same root cause — tools hurt accuracy on 7/10 suites — from different angles. P6 reduces wasted tool calls structurally (frecency, combined ops); WS-1/WS-3 tighten tool-use policy in prompts. Both should be measured together in WS-2 Omega re-run. Risk: contextual suggestions (S3) may worsen the problem if they encourage more tool use.

6. **Research intake deep-dive caveats (2026-04-06)**: intake-264 (SSD) downgraded to monitor-only — requires 8×B200 SFT, not actionable for inference-only stack. intake-266 (OPD Survey) downgraded to reference-only — training-only methods, agent distillation already solved by SkillBank. No new tasks generated from either. Caveats appended to reasoning-compression.md.

---

## Reporting Instructions

After completing any task:
1. Check the task checkbox in this index
2. Update the relevant handoff document with findings
3. Add entry to `progress/YYYY-MM/YYYY-MM-DD.md`
4. If findings affect production systems, flag in `routing-and-optimization-index.md`

---

## Key File Locations

| Resource | Path |
|----------|------|
| TrimR evaluation script | `epyc-inference-research/scripts/benchmark/eval_trimr.py` |
| Difficulty signal classifier | `epyc-orchestrator/src/classifiers/difficulty_signal.py` |
| Classifier config | `epyc-orchestrator/orchestration/classifier_config.yaml` |
| Reasoning length alarm | `epyc-orchestrator/src/graph/helpers.py` |
| Output spill utility | `epyc-orchestrator/src/graph/helpers.py` (`_spill_if_truncated()`) |
| Eval datasets target | `/mnt/raid0/llm/data/eval/` |
| Benchmark scripts | `epyc-inference-research/scripts/benchmark/` |
| Research intake index | `epyc-root/research/intake_index.yaml` |
| Cross-reference map | `epyc-root/.claude/skills/research-intake/references/cross-reference-map.md` |
| File exploration (REPL) | `epyc-orchestrator/src/repl_environment/file_exploration.py` |
| Tool definitions | `epyc-orchestrator/src/prompt_builders/constants.py` |
| TOON encoder | `epyc-orchestrator/src/services/toon_encoder.py` |
