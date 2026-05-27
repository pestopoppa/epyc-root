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
| [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md) | Sub-quadratic attention survey + non-transformer recurrent eval cluster | active (literature survey complete, priority ranking established; HRM-Text intake-598 + actions HRM-1/2/3 queued 2026-05-22) | LOW | 2026-05-22 |
| [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md) | Log-Linear GDN readiness | stub (MONITORING) — blocked on pretrained models | HIGH | 2026-04-14 |
| [yarn-context-extension-research.md](yarn-context-extension-research.md) | Context extension via YaRN | stub | LOW | 2026-03-25 |
| ~~[long-context-eval-datasets.md](long-context-eval-datasets.md)~~ | Eval dataset collection | COMPLETE (5 datasets, adapters integrated, moved to completed/) | — | 2026-04-05 |
| [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md) | TQ3/TurboQuant monitoring | monitoring (do NOT merge) | LOW | 2026-04-01 |
| ~~[11-conceptlm-monitoring.md](../archived/11-conceptlm-monitoring.md)~~ | Concept-level LM monitoring | ARCHIVED (stale, no models available) | — | 2026-03-03 |
| ~~[knowledge-base-governance-improvements.md](knowledge-base-governance-improvements.md)~~ | KB linter, credibility scoring, anti-bias, project-wiki skill | COMPLETE (moved to completed/) | — | 2026-04-07 |
| [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | Block-level reasoning compression (KV masking) | active (S1 llama.cpp feasibility) | HIGH | 2026-04-09 |
| [repl-turn-efficiency.md](repl-turn-efficiency.md) | REPL turn reduction (frecency + combined ops) + ColGREP integration | in-progress (S1-S3a ✅, S5 design ✅, S6a-f bug fixes ✅ 2026-04-16, **S7 ColGREP replaces NextPLAID for code_search ✅ 2026-04-29** — default flipped after live A/B 10/14 vs 2/14 top-1, S4 A/B + cold-start daemon decision pending soak) | MEDIUM | 2026-04-29 |
| [root-archetype-linter-templates-upstream.md](root-archetype-linter-templates-upstream.md) | Linter + brevity templates upstream | in-progress | MEDIUM | 2026-04-09 |
| Ouro LoopLM Evaluation (P7) | Looped LM reasoning verifier | NEW — download + CPU benchmark + T0 sentinel eval | MEDIUM | 2026-04-12 |
| [eval-tower-verification.md](eval-tower-verification.md) | Eval tower calibration + process verification | NEW — ECE/AUC metrics, ThinkPRM T2, cross-family verification, Scoring Verifiers benchmarks | MEDIUM | 2026-04-14 |
| (intake-412) DeepPlanning benchmark | Agent planning eval methodology | Reference — rule-based automated scoring, 26-model leaderboard, reasoning gap 7-16pp | LOW | 2026-04-20 |
| (intake-421) MAD confidence scoring | AutoPilot safety gate noise filter | **adopt_component** — ~20 LoC addition to safety_gate.py. Deep dive: [pi-autoresearch-mad-scoring.md](../../research/deep-dives/pi-autoresearch-mad-scoring.md) | MEDIUM | 2026-04-20 |
| (intake-422) TIDE early exit | Calibration-router for per-token layer skip | **adopt_patterns** — implement on fork n_layer_exit. Deep dive: [tide-calibration-router-early-exit.md](../../research/deep-dives/tide-calibration-router-early-exit.md) | MEDIUM | 2026-04-20 |
| [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) | GLM-5.1-555B-A14B-REAP CPU eval | **NEW** — download pending, storage-constrained (325GB model, 417GB free). 9-phase eval plan. | MEDIUM | 2026-04-22 |
| (intake-426) Compaction gap analysis | Map Claude Code five-layer pipeline vs our L1-L5 | Monitoring — design task from intake-426 deep dive | LOW | 2026-04-22 |
| [sliders-local-validation.md](sliders-local-validation.md) | SLIDERS (structured-DB+SQL alt to RAG) Coder-30B viability | **STUB / NEW 2026-04-28** — Phase 0 falsification gate (catalogue GPT-4.1 call sites, substitute Coder-30B, FinQ5 run, gate on schema-hallucination >20% OR call-count >5×). **Does NOT block `internal-kb-rag.md`.** Sequential evaluation only after KB-RAG K7 ships. Source: intake-494. | LOW | 2026-04-28 |
| (intake-574) Endless Terminals released-artifact re-eval (AW-7) | Independent TB-2.0 transfer-gap validation | **NEW 2026-05-20** — pull `obiwan96/endless-terminals` HF dataset + both PPO checkpoints (Qwen2.5-7B-instruct + Qwen3-8B-openthinker-sft); re-evaluate on TB-2.0 from EPYC inference-only. Confirms or refutes paper's +1-6pp transfer claim before pipeline mirroring (AW-8). Hours of inference. Deep dive in [agent-world-env-synthesis.md](agent-world-env-synthesis.md) Deep-Dive Refinement. | HIGH | 2026-05-20 |
| (intake-571) ECHO 3-gate tracking | GPU-side adoption trigger watch | **NEW 2026-05-20, gated** — `microsoft/echo-rl` watch (currently HTTP 404), independent-reproduction watch, DGX-Spark acquisition watch. Pure tracking, no immediate work. Mirror entry in [gpu-acceleration-path.md](gpu-acceleration-path.md) §ECHO. | LOW | 2026-05-20 |
| [strand-rust-coder-rustevo2-verification.md](strand-rust-coder-rustevo2-verification.md) | Independent RustEvo2 verification of Fortytwo's Strand-Rust-Coder-14B | **NEW 2026-05-27** — gate task for [swarm-dataset-distillation.md](swarm-dataset-distillation.md). Single-instance bench, ~half day, awaiting user approval to launch. Verifies founder claim of #1 on RustEvo2 / beats GPT-5 Codex on Rust (intake-616). Source: intake-614/615/616. | MEDIUM | 2026-05-27 |
| [swarm-dataset-distillation.md](swarm-dataset-distillation.md) | Swarm-as-dataset-generator pipeline replication for narrow-domain SFT | **STUB 2026-05-27** — HIGH-conditional, gated on [strand-rust-coder-rustevo2-verification.md](strand-rust-coder-rustevo2-verification.md). 5-phase pipeline (domain selection → fan-out → BT filter → SFT → eval). Requires user input for P1 domain selection. Source: intake-614/615/616. | HIGH-conditional | 2026-05-27 |

---

## Outstanding Tasks (Priority Order)

### P0 — Reasoning Compression (actionable now)

- [x] Run TrimR evaluation on math/gpqa suites — ✅ 2026-04-09 (Package B). DeepSeek-R1-7B 4×48t. GPQA: thinking helps ~6pp. Math: thinking irrelevant (151 tok avg). TrimR valuable on hard tasks only.
- [x] Collect shadow telemetry from `difficulty_signal.py` in production — ✅ 2026-04-06. 635 requests, Package A run.
- [x] Validate difficulty signal predictive power against benchmark accuracy — ✅ 2026-04-09 (Package B Phase 4). At 0.15/0.35: NO predictive spread — escalation rate flat across easy/medium/hard (62/61/62%). Signal does not differentiate routing needs at current thresholds.
- [ ] If validated: implement enforce mode — **BLOCKED**: difficulty signal has no predictive power at current thresholds. Need semantic features or different approach before enforce.
- [x] Compute Omega metric per-suite — ✅ 2026-04-09 (Package B Phase 4). **7/10 suites: tools HURT accuracy** (direct > REPL). Worst: agentic -54pp, coder -44pp, general -26pp. Only hotpotqa +12pp and gpqa +6pp benefit.
- [ ] **Action 10a (2026-04-22, DD3)**: STOP learnable path pruning probe — prefix-level learnable super-token fills an unoccupied quadrant (internal × learnable × selection) in the reasoning-compression taxonomy. Composes with all Tier 1 techniques (TrimR, short-m@k, difficulty bands). **Gates tightened 2026-04-22 post Tier 2b**: AUC ≥ 0.80 AND ≥0.05 delta over length-only baseline; Phase 3 must show parity-or-better vs DeepConf (training-free baseline, arxiv:2509.24944). **Gated on NIB2-32 difficulty-signal re-validation**. → `reasoning-compression.md` Action 10a + DD3 deep-dive (`/workspace/research/deep-dives/stop-learnable-path-pruning.md`).

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
- [x] Write llama-server adapter for answer generation — ✅ 2026-05-27. `scripts/benchmark/tulving_episodic_adapter.py` (`TulvingEpisodicAdapter`, loads QA parquet from configurable path; LLM-judge hook present, uncalled).
- [x] Implement deterministic F1 scorer: exact + normalized string matching against known ground truth — ✅ 2026-05-27. Token bag-of-words F1 with greedy matching + nb_pred capping; `compute_simple_recall_score` + `compute_chronological_awareness_score`; 77 unit tests.
- [x] Register as new suite in `dataset_adapters.py` + `suites.py` — ✅ 2026-05-27. Suite `tulving_episodic` registered. **Run gated → bulk-inference-campaign Package K (K-MEM-1)**; dataset = Figshare DOI 10.6084/m9.figshare.28244480.
- [ ] Run 20ch benchmark on all production models (10K context — any model handles this)
- [ ] (Deferred to P4) Download 200ch dataset (100K tokens, 686 QA pairs) for YaRN quality gating

### P3c — LongMemEval-V2 Agent-Memory Eval Target (from intake-612 deep-dive, 2026-05-27)

Source: "LongMemEval-V2" (arXiv:2605.12493, UCLA NLP). The updated memory benchmark — reframes from chat-history recall (V1, arXiv:2410.10813) to **web-agent environment expertise**: 451 human-curated questions over WebArena/WorkArena trajectories, multimodal screenshots, Small 100traj/~25M tok + Medium ~500traj/~115M tok, 5 abilities (static state recall, dynamic state tracking, workflow knowledge, environment gotchas, premise-awareness/abstention). Memory operationalized as `Insert(trajectory)/Query→evidence`, 200K reader budget, **fixed reader = Qwen3.5-9B (CPU-viable)**.

**Caveat (decisive for scoping)**: web-agent-specific — needs WebArena/ServiceNow environments or pre-collected trajectory haystacks to run; it is **not** a drop-in for our LoCoMo/MemoryAgentBench memory gates. Aspirational target for `delta-mem-reproduction.md`'s B1/M.3 prototypes, not part of its current gates. Our markdown RAG would land in the 42–51% RAG-baseline band.

- [ ] Decide whether to stand up WebArena/ServiceNow haystacks or wait for the authors to release pre-collected haystacks before adopting LME-V2 as a gate.
- [ ] Forward opportunity (separate from eval): AgentRunbook-C ("trajectories-as-files + coding-agent-in-sandbox + query-time manifest + workflow-doc", 72.5% vs RAG 48.5%) maps onto our REPL + skill-bank + `unified-trace-memory-service.md` SQLite trajectory store. Track as a candidate, not actioned. See `research/deep-dives/2026-05-27-agent-memory-cluster.md`.

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
- [x] **EV-3**: create adapter (~50 lines) — ✅ 2026-05-27. `scripts/benchmark/scoring_verifiers_adapter.py` (`ScoringVerifiersAdapter`), suite `scoring_verifiers` registered in `dataset_adapters.py`+`suites.py`, 36 unit tests. Dataset download is a one-liner manual step (`snapshot_download('nvidia/Scoring-Verifiers', repo_type='dataset', …)`). Feeds **EV-4 / campaign H5** calibration run (inference-gated).
- [ ] **EV-4**: Run calibration baseline on Scoring Verifiers benchmarks (needs inference)
- [ ] **EV-5**: Deploy ThinkPRM-1.5B-Q4KM for T2 process verification (~100 lines, needs model download)
- [x] **EV-6**: Cross-family verification constraint enforcement — ✅ 2026-04-15. `VERIFICATION_FAMILIES` dict + `check_cross_family()` in `eval_tower.py`. Supports Qwen/Llama/DeepSeek/Ouro/Mistral/Gemma. Permissive default (unknown families pass).
- [ ] **EV-7**: AP-27 RLVR integration (depends on EV-1–4 + Ouro P7)
- [ ] **EV-8** (NEW 2026-04-22, DD4): **Diversity metrics in EvalResult** — add `diversity_entropy`, `diversity_distinct2`, `diversity_self_bleu`, `diversity_ttr` + `diversity_semantic_embedding_agreement` fields to `EvalResult` at `safety_gate.py`. Implement `diversity_metrics.py` scoring. Wire `to_grep_lines()`. Baseline pass on 4 production roles. **CODE LANDED 2026-05-27**: `src/` side pre-existing (`src/safety_gate.py` fields + `src/tools/diversity/metrics.py`); autopilot-side `EvalResult` (5 fields, NaN defaults) + `scripts/autopilot/diversity_metrics.py` shim + `to_grep_lines()` NaN-gated wiring added; 50 tests pass. Baseline pass on 4 roles + semantic-embedding-agreement (needs embedder) remain inference-gated → bulk-inference-campaign Package K (K-DIV-1). **Amended 2026-04-22 post Tier 2b**: Verbalized Sampling (arXiv:2510.01171) refutes intake-441's load-bearing "inference-time-irrecoverable" claim — recovers 66.8% of diversity gap via inference-time prompting. SafetyGate moved from single-signal reject to **two-tier multi-signal gate**: (a) Tier 1 WARN on distinct-2 drop >20% + quality not up, (b) Tier 2 REJECT only when distinct-2 drop >20% AND semantic-embedding-agreement drop >10% AND quality not up AND Verbalized Sampling recovery probe fails to recover >50% of gap. Warn-only until VS probe replicated on Qwen3-30B-A3B. Deep dive: `/workspace/research/deep-dives/diversity-collapse-posttraining.md` § Tier 2b.
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

### P9 — Granite-97m-r2 Multilingual Embedder Bench (2026-04-30 deep-dive integration)

Pointer — full plan tracked in [`granite-97m-r2-bench-plan.md`](granite-97m-r2-bench-plan.md). Source: intake-519 deep-dive at [`research/deep-dives/granite-embedding-97m-r2-evaluation.md`](../../research/deep-dives/granite-embedding-97m-r2-evaluation.md).

**Phase A (2-3 inference-free engineering days)**: GGUF conversion + Q8_0/Q4_K_M quantization (ModernBERT supported in llama.cpp `convert_hf_to_gguf.py:12452`); deploy granite-97m-r2 on `:8096` (matches existing BGE-large `:8090–:8095` pattern); parallel-deploy multilingual-e5-base on `:8097`, BGE-M3 dense on `:8098`; build minimal eval corpus (cheapest: 100 code snippets from `epyc-orchestrator/src/` + 30 NL queries with manual labels, ~half day).

**Phase B (1 inference day)**: throughput bench (1000 docs across 6 length buckets), nDCG@10 / recall@10/50, 32K context probe (validate paper-vs-card discrepancy), end-to-end with ColBERT reranker.

**Gate**: K2 chunker activation in `internal-kb-rag.md` (currently STUB). Fallback corpus path (code snippets) is available without K2.

**Outcome decides**: dense first-stage retriever for KB-RAG, web-research, SearXNG. Three branches — adopt granite, adopt BGE-M3, or defer both pending K2-produced multilingual corpus. Code-search angle (60.5 MTEB Code, 9 training languages) is a deferred sub-track.

- [ ] **P9.1**: Phase A-1 GGUF + quantization
- [ ] **P9.2**: Phase A-2 comparator deployments
- [ ] **P9.3**: Phase A-3 server registry update
- [ ] **P9.4**: Phase A-4 eval corpus build
- [ ] **P9.5**: Phase A-5 bench script
- [ ] **P9.6**: Phase B-1/B-2/B-3 bench execution (gated, requires per-run inference approval)
- [ ] **P9.7**: Phase C decision + deployment recommendation; update consuming handoffs

### P10 — RoPE Long-Context Sanity Check, per-model (from intake-569 deep-dive, 2026-05-20)

Pointer — source deep-dive at [`research/deep-dives/2026-05-20-rope-long-context-bounds.md`](../../research/deep-dives/2026-05-20-rope-long-context-bounds.md). Anchor intake: intake-569 (arxiv:2605.15514, RoPE-distinguishes-neither-positions-nor-tokens). Companion empirical: intake-547 (Wang RLM reproduction, arxiv:2603.02615).

**Premise**: Du et al. prove four RoPE failure modes (position inversion, position aliasing, token inversion, token aliasing) and empirically show all tested 7B–405B models collapse to chance (~0.25) on a 4-element position-indexing task **by 4K–8K tokens** — far below their nominal context windows. The paper's reference models include Qwen3 + Llama-3.1 variants but not our specific GGUF quantizations / llama.cpp build. Running the same probe against OUR stack gives a **per-model empirical bound** on where RoPE breakdown actually begins in production.

**Protocol**: 4-element `arr = [v₁,v₂,v₃,v₄]`, vᵢ ∈ {0,1,2,3} (single-token); ask `arr[k]` with padding-extended context. 100 samples per (model, context_length) cell. Baseline = 0.25 (chance).

**Matrix**: 5 models × 4 context lengths = 20 cells. Models: `gemma4-26B-A4B Q4_K_M`, `qwen3.6-27B Q8_0` (or current frontdoor), `qwen3-next-80B`, `REAP-246B Q4_K_M`, `30B-A3B Q4_K_M`. Lengths: 4K, 8K, 16K, 32K.

**Cost**: ~5 min per cell × 20 cells ≈ **100 min total compute**.

**Inference gate**: per-run user approval (`feedback_no_concurrent_inference` + `feedback_speed_verify_via_llama_bench`).

**Priority**: LOW — user-flagged "not urgent" (2026-05-20). Bulk pickup eligible.

**Outcome**: per-model collapse point. Refines `cpu-context-regime-coverage.md` 32K test row, the YaRN gate criterion (intake-569 caveat already added), and informs whether any context-folding aggressiveness tier should kick in earlier for specific models.

- [x] **P10.1**: Write probe script (~30 LoC, no inference) — ✅ 2026-05-27. `scripts/benchmark/rope_position_probe.py` (4-element token-encoded list, neutral-filler padding to target ctx, 100-sample driver, `--dry-run` verified, `/completion` client). **P10.2 5×4 matrix run gated → bulk-inference-campaign Package K (K-ROPE-1)**, LOW priority / bulk-eligible.
- [ ] **P10.2**: 5×4 matrix run (inference-gated)
- [ ] **P10.3**: Record results + collapse-point per model into [`research/deep-dives/2026-05-20-rope-long-context-bounds.md`](../../research/deep-dives/2026-05-20-rope-long-context-bounds.md) Appendix
- [ ] **P10.4**: Cross-link finding back to `cpu-context-regime-coverage.md` 32K row and `yarn-context-extension-research.md` gate

### P11 — Fast-RLM REPL Output Truncation A/B (2000 vs 5000 chars; deferred since 2026-03-03)

Pointer — completed handoff [`handoffs/completed/01-fast-rlm-budget-controls.md`](../completed/01-fast-rlm-budget-controls.md) §4 ("Evaluate REPL truncation at 2000 chars — DEFERRED"). Source: fast-rlm `examples/structured_io.py`, default `max_output_chars=2000` vs our current `_repl_turn_token_cap` ≈ 5000 tokens.

**Premise**: fast-rlm defaults to a more aggressive REPL output truncation (2000 chars) than ours. Empirical question: does dropping to 2000 chars improve worker_general / coder accuracy by forcing tighter focus, OR degrade it by clipping useful intermediate output?

**Protocol**: Paired A/B at the existing eval-tower seeded suite. Two arms: arm A = current cap; arm B = 2000-char cap. Same seed, same suite, same routing.

**Cost**: small (single seeded suite × 2 arms). Estimated **~30–60 min** depending on suite size.

**Inference gate**: per-run user approval.

**Priority**: LOW. Has been deferred since 2026-03-03 without harm; no active workload signals this is load-bearing.

**Status update — 2026-05-20**: wired into autopilot. NumericSwarm now has a `repl_executor` surface with `ParamSpec("repl.turn_token_cap", 256, 4096, "int")`; `config_applicator.ENV_PARAMS["repl"]["turn_token_cap"] = "ORCHESTRATOR_REPL_TURN_N_TOKENS"` routes trials via env-restart. End-to-end smoke verified: `classify_params({"repl.turn_token_cap": 1500}) → env_restart`, `NumericSwarm.suggest_trial("repl_executor")` returns a sampled int in range. Autopilot will sweep this organically; no further manual eval needed.

**Caveat**: when `difficulty_signal` mode is `enforce`, `_repl_turn_token_cap()` returns the hardcoded band-adaptive value (1500/3500/7000 per easy/medium/hard) and ignores the env var. The sweep affects only the flat-cap path (mode != enforce, or no difficulty_band set). If autopilot's fANOVA importance shows `repl.turn_token_cap` is low-impact, the next step is to expose the band-adaptive dict to sweep too — not yet wired.

- [x] **P11.1**: Wire `repl.turn_token_cap` into NumericSwarm + config_applicator. **DONE 2026-05-20** (commit pending). Files: `scripts/autopilot/species/numeric_swarm.py` (+10 LoC), `scripts/autopilot/config_applicator.py` (+3 LoC). Smoke verified.
- [x] **P11.1b**: Wire **3 sibling caps** under the same `repl_executor` + new `repl_budget` surfaces. **DONE 2026-05-20**. Adds: `repl.frontdoor_non_tool_token_cap` (env: `ORCHESTRATOR_FRONTDOOR_REPL_NON_TOOL_N_TOKENS`), `repl.worker_call_budget_cap` (env: `ORCHESTRATOR_WORKER_CALL_BUDGET_CAP`, flag-gated by `worker_call_budget`), `repl.task_token_budget_cap` (env: `ORCHESTRATOR_TASK_TOKEN_BUDGET_CAP`, flag-gated by `task_token_budget`). 4 knobs total across 2 surfaces (2+2). Smoke verified.
- [x] **P11.1c**: Wire **KV compaction knobs** as a new `kv_compaction` surface with a new `apply_kv_compact` applicator path that calls `kv_compress.compress_slot()` at runtime (not env-restart, not POST /config). **DONE 2026-05-20**. Adds: `kv.keep_ratio` (0.25–0.90 float — lower bound clipped at 0.25 to avoid the format-degradation cliff), `kv.keep_first` (2–16 int), `kv.n_future` (64–1024 int). Per autopilot `program.md` Tier 4.5, this is the largest single-item leverage in the audit. Smoke verified via `classify_params({"kv.keep_ratio": 0.5}) → kv_compact` bucket.
- [x] **P11.1d**: Promote **3 default-off flags** to `HOT_SWAP_FEATURES` so StructuralLab can experiment with them. **DONE 2026-05-20**. Adds: `structured_tool_output` (Lobster ToolOutput envelope), `content_cache` (SHA-256 keyed response cache), `model_fallback` (same-tier alternatives on circuit-open). Each was previously listed as a default-off candidate in `rlm-orchestrator-roadmap.md` R6 candidate matrix; promotion makes them sweepable by autopilot's existing flag-mutation pool.
- [ ] **P11.2**: Observe autopilot results after ≥20 trials on the `repl_executor` surface; record fANOVA importance + cluster-selected best value.
- [ ] **P11.3**: If band-adaptive path dominates and the sweep is uninformative, optionally expose `_BAND_TOKEN_BUDGETS[easy/medium/hard]` as three sweepable params.
- [ ] **P11.4**: Record outcome + cross-link from `01-fast-rlm-budget-controls.md` Follow-up section when sufficient trial data is available.

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
P10 (RoPE per-model probe)            ──independent (inference-gated, ~100 min); informs cpu-context-regime-coverage + yarn gate──
P11 (REPL truncation A/B)             ──independent (inference-gated, ~30–60 min); or promotable to NumericSwarm wire-in──
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
