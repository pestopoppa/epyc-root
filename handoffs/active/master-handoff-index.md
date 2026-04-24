# EPYC Handoff — Master Index

**Updated**: 2026-04-22 (Deep-dive integration pass: 8 deep dives landed; 2 new handoffs — agent-world-env-synthesis + minddr-deep-research-mode; priority queue #23/24/25 added; diversity-collapse cross-index §14; NIB2-40..48 supplement. **Tier 2b sweep same day**: intake-441 load-bearing claim REFUTED by Verbalized Sampling arXiv 2510.01171 → EV-8 amended to multi-signal gate; intake-437 STOP gates tightened; intake-444 Agent-World Phase 1.5 upgraded to corroboration probe.)
**Purpose**: Single entry point for any agent. Read this to discover active work and where to start.

---

## Quick Start

| Working on... | Read this index |
|---------------|----------------|
| Routing, orchestration, autopilot, stack config | [routing-and-optimization-index.md](routing-and-optimization-index.md) |
| Inference speed, benchmarks, model acceleration | [inference-acceleration-index.md](inference-acceleration-index.md) |
| Agent UX, conversation management, frontend | [hermes-agent-index.md](hermes-agent-index.md) |
| Pre-production research, evaluation, monitoring | [research-evaluation-index.md](research-evaluation-index.md) |
| New capability pipelines (vision, PDF, Lean, TTS) | [pipeline-integration-index.md](pipeline-integration-index.md) |
| Evaluating model candidates | See **Standalone Handoffs** below |
| Don't know where to start | See **Priority Queue** below |

---

## Priority Queue

Highest-impact work across all domains. Each item points to where the details live.

| # | Priority | Item | Index / Handoff |
|---|----------|------|----------------|
| 0 | ~~HIGH~~ | ~~llama.cpp v3~~ ✅ binary swapped 2026-04-10 (coder +101%, REAP +50%). Deferred: PPL, paged attn RSS, NUMA tests | [llama-cpp-v3-upstream-rebuild.md](../completed/llama-cpp-v3-upstream-rebuild.md) |
| 1 | HIGH | AR-3 relaunch (expand T0 sentinels, safety-hardened) | [routing-and-optimization-index](routing-and-optimization-index.md) P5 |
| 2 | ~~HIGH~~ | ~~Context folding Phase 1~~ ✅ 2026-04-04 | [routing-and-optimization-index](routing-and-optimization-index.md) CF Phase 1 |
| 2a | ~~MED~~ | ~~CF Phase 1+/2c/3a/3b~~ ✅ 2026-04-05 (code complete, 4 feature flags, 32 tests). Phase 2c ByteRover enhancement designed (intake-267). | [routing-and-optimization-index](routing-and-optimization-index.md) CF |
| 2b | MED | CF Phase 2a/2b eval + Phase 3c quality monitor (need inference) → Package C/D | [routing-and-optimization-index](routing-and-optimization-index.md) CF Phase 2 |
| 3 | HIGH | RI-10–12 routing rollout (shadow → enforce) → Package D | [routing-and-optimization-index](routing-and-optimization-index.md) P6 |
| 4 | ~~HIGH~~ | ~~B1/B2/B3/B5/B6/B7 conversation management~~ ✅ 2026-04-05 (6 modules, 99 tests, 4 feature flags) | [hermes-agent-index](hermes-agent-index.md) P0 |
| 4a | ~~MED~~ | ~~Brevity prompt upgrade~~ ✅ Actions 12-15 done, TALE eval 2026-04-11 (static limits kept) | [research-evaluation-index](research-evaluation-index.md) P0.5 |
| 5 | ~~MED~~ | ~~TrimR deployment~~ Package B ✅ 2026-04-10 (thinking +6pp GPQA, tool A/B +4pp, WS-3 validated) | [research-evaluation-index](research-evaluation-index.md) P0 |
| 6 | ~~MED~~ | ~~Tool output compression~~ Phase 2 native ✅ 2026-04-05, A/B ✅ 2026-04-10 (+4pp REPL, suite-dependent) | [research-evaluation-index](research-evaluation-index.md) P1 |
| 7 | MED | OpenDataLoader PDF integration | [pipeline-integration-index](pipeline-integration-index.md) P1 |
| 8 | ~~MED~~ | ~~CC local integration~~ Phase 0 ✅ 2026-04-05. Phases 1-3 **demoted to stub** 2026-04-11 — superseded by Hermes outer shell. Archived. | [claude-code-local-constellation-routing.md](../archived/claude-code-local-constellation-routing.md) |
| 9 | LOW | Multimodal vision live validation | [pipeline-integration-index](pipeline-integration-index.md) P0 |
| 10 | LOW | Hermes outer shell Phase 2 (routing API done, skills done, streaming validated. Auth deferred.) | [hermes-agent-index](hermes-agent-index.md) P2 |
| 11 | ~~MED~~ | ~~GEPA PromptForge integration~~ AP-18/19/20 ✅ 2026-04-12 (DSPy signatures + GEPA adapter + folded into AR-3 Package D). AP-21 conditional on AR-3 data. | [routing-and-optimization-index](routing-and-optimization-index.md) P10 |
| 12 | ~~MED~~ | ~~Autopilot controller upgrades~~ AP-22/23/24/25 ✅ 2026-04-12 (memory + criticism + RLM config). AP-26/27 → Package H | [routing-and-optimization-index](routing-and-optimization-index.md) P11 |
| 13 | ~~MED~~ | ~~Context folding provenance~~ CF-P1–P4 ✅ 2026-04-12 (all 4 implemented) | [routing-and-optimization-index](routing-and-optimization-index.md) P10b |
| 14 | MED | **Ouro-2.6B-Thinking eval** (P7). Download + MATH-500 CPU benchmark + T0 sentinel candidate | [research-evaluation-index](research-evaluation-index.md) P7 |
| 15 | MED | **MiniMax M2.7 eval** (G7–G9). ~~G7 download~~ ✅, ~~G7a NUMA sweep~~ ✅ (Q8 11.1 tps, architect replacement viable). G8 tool-calling + G9 quality eval pending | [bulk-inference-campaign](bulk-inference-campaign.md) Package G |
| 16 | ~~HIGH~~ | ~~Orchestrator refactoring audit~~ ✅ 2026-04-13 All 8 phases complete + InferenceResult success flip + TOON encoder + test suite 4893/0/7. Moved to completed/. | [orchestrator-refactoring-audit](../completed/orchestrator-refactoring-audit.md) |
| 17 | HIGH | **Decision-aware Q-scorer routing** (P13). Zero predictive spread diagnosed in Package B. 4-phase experiment: regret analysis → contrastive → SPO+ → bilinear. | [routing-and-optimization-index](routing-and-optimization-index.md) P13 |
| 18 | MED | **Eval tower verification framework** (P8). ECE/AUC calibration + ThinkPRM process verification + Scoring Verifiers benchmarks. Enables AP-27 RLVR. | [research-evaluation-index](research-evaluation-index.md) P8 |
| 19 | MED | **AutoPilot iteration strategy upgrade** (P14). 4-phase: strategy memory upgrade (RRF+staleness), knowledge distillation pipeline (L1→L2→L3), controller context budget, mutation knowledge graph. AP-28 through AP-31. | [routing-and-optimization-index](routing-and-optimization-index.md) P14 |
| 20 | ~~MED~~ | ~~TIDE calibration-router early exit~~ DEPRECATED 2026-04-23 — post-hoc exit <10% gain on modern LLMs (research confirmed dead end) | [inference-acceleration-index](inference-acceleration-index.md) |
| 21 | LOW | **MAD confidence scoring** (intake-421). Add Median Absolute Deviation noise filter to safety_gate.py (~20 LoC). Prevents false-positive eval waste. | [routing-and-optimization-index](routing-and-optimization-index.md) |
| 22 | MED | **GLM-5.1-REAP CPU eval** (intake-427 revised). 555B/14B-active GGUF (325GB). Stack simplification: replace 2 architect models (208GB) with 1. 88% Terminal-Bench, 66% SWE-bench Pro claimed. Storage tight (92GB remaining). | [inference-acceleration-index](inference-acceleration-index.md) / [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) |
| 23 | MED | **ColBERT reranker S5 — LateOn drop-in upgrade** (intake-428/430/431). +2.55pp BEIR vs deployed GTE-ModernColBERT-v1, same ModernBERT backbone, same Apache-2.0 license. **Tier 2b 2026-04-22**: no direct contradicting evidence, but no third-party replication either — added E4b local BEIR subset reproduction as non-vendor cross-check. **S3b code done 2026-04-22 (NIB2-47)**: export + parity script + `LATEON_MODEL_PATH` env override + 13/13 tests; execution run deferred pending `colbert-export` extras install. A/B gated on AR-3 Package D web_research data. | [colbert-reranker-web-research.md](colbert-reranker-web-research.md) S5 + DD1 deep-dive |
| 24 | MED | **STOP learnable path pruning** (intake-437). Prefix-level learnable super-token filling an unoccupied quadrant (internal × learnable × selection); composes with all Tier 1 reasoning-compression techniques. **Tier 2b 2026-04-22**: AIME25 84→90 is 2/30 questions single-seed (inside baseline 95% CI); gates tightened to AUC ≥0.80 + ≥0.05 delta over length-only baseline + parity vs DeepConf (arxiv:2509.24944). Credibility rec'd 6→4-5. 5-inference-day probe plan; gated on NIB2-32 re-validation. | [reasoning-compression.md](reasoning-compression.md) Action 10a + DD3 |
| 25 | LOW | **Qwen3.5-Omni audio-path feasibility** (intake-432, **DEFERRED**). DD2 found API-only release, not open-weight — file as reference. **Tier 2b 2026-04-22**: "215 SOTA" is marketing aggregate; Gemini-3.1 deltas mostly within noise; closed-source decision is structural not temporary. Re-open if Alibaba releases open weights OR Qwen3-Omni-30B-A3B (Apache 2.0) proves CPU-viable. | [multimodal-pipeline.md](multimodal-pipeline.md) + DD2 |
| 26 | ~~HIGH~~ | ~~TIDE calibration + router training + kernel push~~ ✅ v4 kernel finalized 2026-04-23. TIDE deprecated. Hadamard KV smoothing + f16 fix merged from experimental. Quality benchmarks queued. | [inference-acceleration-index](inference-acceleration-index.md) / [llama-cpp-kernel-push-rebase.md](llama-cpp-kernel-push-rebase.md) |
| 27 | HIGH | **Single-instance peak throughput backlog** (created 2026-04-23, **Phase 0 COMPLETE + CPU2 falsified 2026-04-23**). Revised priorities after measurement: **CPU1 intra-process TP decode — Phase 0 GATE PASSED, HIGH TOP** (192t at 8% of BW roofline; 96t/192t ratio 2.63×; Phase 1 is ~1 week, schedule dedicated session); **CPU4 per-CCD sync primitive — PROMOTED to HIGH standalone** (32–45% of decode cycles in OpenMP barriers measured via perf); **CPU3 system tuning — HIGH, zero-reboot knobs partially applied** (THP/numa_balancing/hugepages net within noise on canonical baseline); **CPU2 GEMV ukernels — DEPRIORITIZED** (AVX-512VNNI port of `ggml_vec_dot_q8_0_q8_0` delivered +1.7% at 96t / −3.6% at 1t on Qwen3.6-27B Q8_0; decode is BW-bound not compute-bound). Work in `llama.cpp-experimental` on `cpu-optimization/backlog-2026-04-23`. Bonus finding: 96t-single-NUMA-node peak at 49.11 t/s for Qwen3-Coder-30B-A3B Q4_K_M = +26% over production worker_explore (1×24t, 39.1 t/s) with no code change — actionable production sweep candidate. | [cpu-inference-optimization-index](cpu-inference-optimization-index.md) |

---

## Domain Indices

| Domain | Index | Handoffs | Status |
|--------|-------|----------|--------|
| Routing & Optimization | [routing-and-optimization-index.md](routing-and-optimization-index.md) | 11 | P0-P4 complete, **P5 Phase 5 seeder refactor DONE**, P6 RI-10 canary, P7-P9 pending, P10/P11 DONE, P13 DAR-1/2 done, **P14 NEW: AutoPilot iteration strategy upgrade** (AP-28–31, 4-phase: strategy memory, knowledge distillation, context budget, mutation graph). AR-3 needs restart. |
| Inference Acceleration | [inference-acceleration-index.md](inference-acceleration-index.md) | 6 active + completed | KV quantization COMPLETED (moved), **KV compaction L1-L4+L4b merged to production** (native ggml), KV selection eval phase, ~~v3 PRODUCTION~~ (completed/), GPU acceleration path (researched, +vLLM Dflash plan), **Log-Linear GDN readiness** (stub — monitoring), Qwen3.6 production upgrade (GGUF downloaded, benchmark pending), ~~TIDE calibration-router early exit~~ **DEPRECATED 2026-04-23** (post-hoc dead end), **Hadamard KV smoothing + f16 fix merged** to v4 kernel, **NEW: GLM-5.1-REAP CPU eval** (intake-427 revised, 555B/14B-active GGUF, stack simplification candidate) |
| Agent Integration | [hermes-agent-index.md](hermes-agent-index.md) | 3 | B1-B7 ALL COMPLETE + integration wired, shell low priority |
| Research & Evaluation | [research-evaluation-index.md](research-evaluation-index.md) | 8 + P7 + P3b + 2 new | tool-compression A/B done (+4pp), REPL S1-S2 done (S3a/S5 next), reasoning done, **P7 Ouro eval queued**, multiscreen → full sub-quadratic survey, **Log-Linear GDN** HIGH priority monitoring, P3b Tulving episodic benchmark, **NEW: MAD confidence scoring** (adopt_component), **TIDE early exit** (adopt_patterns) |
| Pipeline Integration | [pipeline-integration-index.md](pipeline-integration-index.md) | 4 | vision done, TTS blocked, PDF/Lean pending |

---

## Standalone Handoffs

Not covered by any sub-index. Small, focused, or cross-cutting.

| Handoff | Domain | Status | Priority | Last Updated |
|---------|--------|--------|----------|-------------|
| [colbert-reranker-web-research.md](colbert-reranker-web-research.md) | web_research pipeline | S1-S4 done (ONNX Runtime, 180ms, PyLate eliminated), S5 gated on AR-3 data, S7 surprisal chunking proposed | MEDIUM | 2026-04-18 |
| [searxng-search-backend.md](searxng-search-backend.md) | web_search infrastructure | SX-1–4 done, SX-5/6 folded into AR-3 Package D Phase 6b | MEDIUM | 2026-04-14 |
| [mathsmith-hc-formalizer-eval.md](mathsmith-hc-formalizer-eval.md) | Formal verification | S1 done; S2-S4 queued; ~~S5~~ ✅ proposal retired 2026-04-17. Priority elevated (formalizer-overthinking + Math-Verify intake-377 + cost-reduction hypothesis arxiv:2504.06514) | **MEDIUM** | 2026-04-17 |
| [bulk-inference-campaign.md](bulk-inference-campaign.md) | Cross-cutting eval | active (A-C+E+F done, D running, **G +3 MiniMax, H +7 GEPA/RLM/Ouro research, I +3 DAR/ThinkPRM**) | HIGH | 2026-04-15 |
| [non-inference-backlog.md](non-inference-backlog.md) | Cross-cutting code/infra tasks | **ACTIVE Round 2** — **35/43 done** (NIB2-01..30 original + NIB2-31/32/34/35 × 2026-04-21 supplement + NIB2-41/42/44/45/47/48 × 2026-04-22 Phases A/B/C/D; NIB2-33 excluded). 8 remaining (5 carry-forward + 3 open from 2026-04-22 deep-dive integration; NIB2-46 gate-bound on NIB2-32 live verdict). Round 1 (18/18) → [completed/](../completed/non-inference-backlog.md). | MEDIUM | 2026-04-22 |
| [triattention-kv-selection.md](triattention-kv-selection.md) | KV cache compression (EA) | **DEPLOYED** — EA scorer in production kernel + server endpoint + autopilot. S4/S5/S6/S7 done. Next: S8 autopilot exploration → S9 orchestrator auto-trigger | HIGH | 2026-04-14 |
| [attention-matching-kv-compaction.md](attention-matching-kv-compaction.md) | KV cache latent-space compaction | ACTIVE (L1-L4+L4b merged to production-consolidated-v3. P2 coding benchmarks pending) | MEDIUM | 2026-04-13 |
| [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | Block reasoning KV masking | ACTIVE — S1 runtime PASSED (5/5, 2026-04-14). S2 LoRA training unblocked. | HIGH | 2026-04-14 |
| [gpu-acceleration-path.md](gpu-acceleration-path.md) | Hardware acceleration | researched (vLLM DDTree+Dflash spec-dec plan added, activates on GPU acquisition) | LOW | 2026-04-15 |
| [orchestrator-refactoring-audit.md](../completed/orchestrator-refactoring-audit.md) | Code quality, observability | ~~COMPLETE~~ ✅ 2026-04-13 All 8 phases + success flip + TOON + test suite 4893/0/7 | ~~HIGH~~ | 2026-04-13 |
| [integration-test-coverage.md](integration-test-coverage.md) | Test coverage | ACTIVE — graph integration fixtures still needed; focused slice gate enforces specialist routing floors (`237 passed`, `seed_specialist_routing*` at `100%` floors), strict warning gate includes legacy tests (`255 passed`), and `integration-sanity` is now fully strict (includes `PytestUnraisableExceptionWarning` as error) and green (`372 passed, 12 skipped`) after sqlite/embedder lifecycle cleanup + integration client teardown hardening. GitNexus native `npx` path remains restored/reindexed (`status: ✅ up-to-date`). | MEDIUM | 2026-04-14 |
| [agent-world-env-synthesis.md](agent-world-env-synthesis.md) | Autopilot 5th species: environment + task synthesis (DD6, intake-444) | stub / in-planning — Phase 1 training-free, Phase 2 GPU-gated | MEDIUM | 2026-04-22 |
| [minddr-deep-research-mode.md](minddr-deep-research-mode.md) | 3-agent Planning/DeepSearch/Report specialization (DD7, intake-438) | stub / in-planning — Phase 1 prompt-level, Phase 2 GPU-gated | MEDIUM | 2026-04-22 |
| [decision-aware-routing.md](decision-aware-routing.md) | Q-scorer decision-aware learning | DAR-1/2/3/4 done. Episodic memory routing intel added (reasoning models collapse at 100K). | HIGH | 2026-04-18 |
| [eval-tower-verification.md](eval-tower-verification.md) | Eval tower calibration + verification | NEW — ECE/AUC metrics, ThinkPRM T2, cross-family verification | MEDIUM | 2026-04-14 |
| [qwen36-production-upgrade.md](qwen36-production-upgrade.md) | Model upgrade evaluation | IN-PROGRESS — GGUF downloaded (Q4_K_M+Q8_0), deep dive confirms drop-in replacement. Benchmark pending. | **HIGH** | 2026-04-17 |
| [learned-routing-controller.md](learned-routing-controller.md) | Routing classifier training | Phase 1 ✅ (92% val acc, 157K samples, flag enabled); P1.5 logit probe + P2.3-2.6 hidden-state probes + P3 BGE elimination pending | **HIGH** | 2026-04-15 |
| [per-request-reasoning-budget.md](per-request-reasoning-budget.md) | Per-request `</think>` budget | Steps 1-2 DONE (root cause: SSM state race on hybrids, 3 fix options proposed). Steps 3-4 need running server. Workaround: `--jinja` removed from architect_general (coarse). | MEDIUM | 2026-04-17 |
| [readme-refresh.md](readme-refresh.md) | Documentation | GATED on AR-3 trial ≥100 (currently ~78). 4 numbered tasks: epyc-root + epyc-orchestrator + epyc-inference-research READMEs + autopilot plots snapshot. | LOW | 2026-04-14 |
| [root-archetype-linter-templates-upstream.md](root-archetype-linter-templates-upstream.md) | Cross-repo upstreaming | Epyc-root side DONE (KB linter, brevity templates, wiki.yaml, wiki compile). 3 tasks remain in root-archetype repo (no local clone). | LOW | 2026-04-14 |

---

## Cross-Index Dependencies

Changes in one domain often affect others. Key coupling points:

| Source | Affects | Mechanism |
|--------|---------|-----------|
| Inference acceleration (benchmarks) | Routing & optimization (baselines) | Model speed/quality data feeds Q-scorer baselines and stack config |
| Research (reasoning compression) | Routing (difficulty signal) | `difficulty_signal.py` shared between reasoning token budgets and routing |
| Research (tool output compression) | Routing (context folding) | Upstream token reduction changes context compaction frequency |
| Hermes (B2 context compression) | Routing (context folding Phase 1) | Must sequence B2 after Phase 1 — both modify compaction |
| Routing (AR-3 autoresearch) | Routing (meta-harness) | Meta-harness Tier 1+2 validated via AR-3 autopilot runs |
| Pipeline (new models) | Routing (NUMA allocation) | Each pipeline model competes for RAM/quarters with production stack |
| Bulk inference campaign (B-E) | All 5 domains | 14 tasks → 4 optimized runs; produces data unblocking routing, research, pipeline work |
| Research (KB governance) | Root-archetype (KB linter) | KB linter + skill templates upstreamed to root-archetype; epyc-root deploys instance-specific version |
| Wiki compilation (24 articles) | All domains | Compiled wiki in `wiki/` synthesizes all research + handoff findings; update articles after new `/research-intake` runs |
| GPU hardware acquisition | Inference acceleration, Routing (NUMA allocation) | gpu-acceleration-path.md: CPU+GPU hybrid MoE changes expert routing, NUMA quarter allocation, and v3 build flags |
| Research (Ouro P7) | Routing (autopilot AP-27) | Ouro-2.6B-Thinking as sentinel verifier feeds autopilot T0 RLVR formalization |
| Routing (autopilot P10 GEPA) | Routing (meta-harness MH-4) | Same technique, two perspectives: autopilot owns implementation, meta-harness evaluates as search algorithm |
| Bulk inference (Package G) | Routing (stack config) | MiniMax M2.7 eval may introduce 229B-A10B model requiring standalone RAM allocation |
| SearXNG backend (search infra) | ColBERT reranker (richer snippets), Routing P8b (search pipeline) | SearXNG JSON API replaces DDG HTML scraping; engines[]/score metadata enhances ColBERT confidence; unresponsive_engines[] feeds monitoring |
| Decision-aware routing (R&O P13) | Routing (difficulty signal), Research (AP-27 RLVR) | Resolves zero-predictive-spread in difficulty_signal.py; new reward signal needs eval tower verification |
| Eval tower verification (RE P8) | Routing (AP-27 RLVR), Research (Ouro P7) | Provides calibration infrastructure (ECE/AUC) for RLVR formalization; Ouro as sentinel candidate |
| Dynamic stack concurrency (R&O, `dynamic-stack-concurrency.md` Phase F) | Inference acceleration (AM compaction P2 → KVCOMM F1) | Phase F1 blocks on AM compaction P2; Phase F's cross-NUMA anchor pool compounds with L4b compaction ratio measurements. **Ownership**: routing-and-optimization (primary); Phase F mirrored in inference-acceleration-index landscape for discoverability. |
| GLM-5.1-REAP evaluation (IA) | Routing (stack config, Q-scorer baselines), Research (model eval methodology) | If GLM-5.1 replaces architect_general + architect_coding: Q-scorer baselines (RI-0) must update, NUMA allocation changes (2x96t → new config), routing rules for 2-model→1-model architect tier need revision. |
| **Output diversity collapse (intake-441)** | Autopilot (PromptForge mutation space), Research eval (checkpoint validation), Reasoning compression (conciseness-prompt ceiling) | **Amended 2026-04-22 post Tier 2b**: Verbalized Sampling (arXiv 2510.01171) recovers 66.8% of diversity gap via inference-time prompting — intake-441's "inference-time cannot recover" claim is refuted. Revised implication: (a) `EvalResult` tracks diversity metrics + `semantic_embedding_agreement` + VS recovery probe, not distinct-2 alone; (b) checkpoint-swap gate is multi-signal not single-signal; (c) PromptForge diversity-coverage couples with semantic agreement. See `eval-tower-verification.md` EV-8 (amended) + `/workspace/research/deep-dives/diversity-collapse-posttraining.md` § Tier 2b. |
| **Env synthesis + 3-agent specialization (DD6/DD7)** | Autopilot (5th species), Meta-harness Tier 3, Routing intelligence, Eval tower | Both workstreams target Tier 3 outer-loop rebuild from different angles. Env synthesis expands the benchmark surface (autopilot-facing); 3-agent specialization refactors the routing pipeline (routing-facing). Shared Phase 2 gate on DGX Spark arrival. See `agent-world-env-synthesis.md` + `minddr-deep-research-mode.md` + `eval-tower-verification.md` EV-9 multi-dimensional rubric. |

---

## Freshness Protocol

| Age | Marker | Action |
|-----|--------|--------|
| < 14 days | current | None |
| 14-30 days | aging | Review if still active |
| > 30 days | **STALE** | Verify status, update or archive |

Run `scripts/validate/check_handoff_freshness.sh` to check all handoffs.

After completing work on any handoff:
1. Update the handoff document
2. Update the relevant sub-index (checkbox + status)
3. If priority queue items complete, update this master index
4. Add entry to `progress/YYYY-MM/YYYY-MM-DD.md`
