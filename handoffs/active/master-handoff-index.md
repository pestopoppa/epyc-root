# EPYC Handoff — Master Index

**Updated**: 2026-04-27 (added item 28 — Trinity-derived coordinator/routing tasks: 2 new handoffs + LRC P4.1-P4.4 + DAR-1.5 + index P19. Trinity (intake-474, ICLR 2026) is now standing comparative context for all orchestration/routing work. Deep-dive at `research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`.)
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
| 27a | ~~HIGH~~ | ~~**NPS BIOS reboot — CPU1 gate** (scheduled 2026-04-24)~~ ✅ **COMPLETED 2026-04-24**. Rebooted NPS2→NPS4. Full re-characterization and Phase 1.2/1.3 v1/v2 + Lever A' (replication) + Lever A (barrier) + CCD pool cpuset fix landed. See item #27 for current state. L3aaN deferred by user until NPS4 tracks exhausted. | [nps-reboot-runbook](nps-reboot-runbook.md) |
| 27 | HIGH | **Single-instance peak throughput backlog**. **2026-04-26 evening compounding-matrix update**: most prior CPU1/CPU2/CPU15 wins were sub-baseline artifacts (EP frontdoor +17% → +1.6% on proper canonical, REAP-246B EP regression −47% → 0%, auto-mbind +6% → 0%, CPU1 3-flag +1.8% → +0.6%). The biggest practical gain is the canonical config itself (`--mmap 0 + --interleave=all` = +44% on Q8_0, +39% on gemma-26B). CPU24 attribution scope simplified; CPU19 Tutel 2DH motivation evaporated. Wave-pipeline framing still applies: Wave 0 integrity gate (CPU20 — primary canonical revised), Wave 1 attribution (CPU21 OpenMP + CPU24 uncore), Wave 2 mechanism (CPU22, gated), Wave 3 regime coverage (CPU23). Compounding data: `data/cpu_optimization/2026-04-26-compounding/SUMMARY.md`. | [cpu-inference-optimization-index](cpu-inference-optimization-index.md) / [cpu-benchmark-rigor-and-revalidation](cpu-benchmark-rigor-and-revalidation.md) / [cpu-openmp-runtime-scheduling-matrix.md](cpu-openmp-runtime-scheduling-matrix.md) / [cpu-uncore-fabric-attribution.md](cpu-uncore-fabric-attribution.md) / [cpu-dynamic-moe-load-balancing.md](cpu-dynamic-moe-load-balancing.md) / [cpu-context-regime-coverage.md](cpu-context-regime-coverage.md) |
| 27b | ~~HIGH (GATE)~~ | ~~L3-as-NUMA BIOS reboot~~ ✅ **EVALUATED & REVERT REQUIRED 2026-04-26 evening**. Canonical sweep + audit-driven supplemental tweaks + 12-rank concurrent-split + literature review all confirm: every production model regresses 26–43% on single-engine, **−35% on concurrent aggregate** (the "designed-for L3aaN" pattern). Best Coder-30B single = 29.42 t/s vs NPS4 ref 43.57. Decision: revert BIOS to NPS4. **Post-reboot pickup**: `cpu-inference-optimization-index.md` POST-REVERT PICKUP block (verification steps + smoke command + Phase H entry). Raw data `data/cpu_optimization/2026-04-26-l3aan/`; writeup `progress/2026-04/2026-04-26.md`. | [cpu-inference-optimization-index](cpu-inference-optimization-index.md) / [nps-reboot-runbook](nps-reboot-runbook.md) |
| 27c | HIGH | **CPU15 — Large-MoE as primary target + expert parallelism** (new 2026-04-24). Strategic reframe: the 2.13× concurrent-aggregate gap (single-instance 48.81 → concurrent ~104 t/s on 30B-A3B Q4) indicates large sparse MoE is the hardware-matched target. Phase 0 is a cheap 4–6 h baseline re-measurement of Qwen3-235B-A22B + 480B-A35B on the current NPS4 + `GGML_NUMA_WEIGHTS=1` + AVX-512BW stack (no code). Phase 1+ implements per-CCD / per-process expert sharding in the llama.cpp fork. Expected 2–5× single-stream on ≥100B MoE. Contends with `orchestrator-nps4-48x4-notes.md` for NUMA topology (D2). Does not require BIOS reboot. | [cpu-inference-optimization-index](cpu-inference-optimization-index.md) / [large-moe-expert-parallelism.md](large-moe-expert-parallelism.md) |
| 27d | ~~MED-HIGH~~ | **CPU16/17/18/19 status (updated 2026-04-26 evening)**: ~~CPU16 disagg~~ ✅ **CLOSED** (no decode-stall problem to solve on single-user CPU; was meant to be obsoleted by CPU17 which itself shows no signal). ~~CPU17 Sarathi-Serve chunked-prefill~~ ✅ **CLOSED** — Phase 0 quick probe shows decode constant at 46-47 t/s across all -ub values; smaller -ub damages prefill -52% with no decode benefit on single-user regime. **Re-open trigger**: shift to multi-tenant API. CPU18 MegaBlocks indexing — pending; would compound CPU2 SIMD wins on expert-dispatch. ~~CPU19 Tutel 2DH~~ ✅ **CLOSED** — was meant to fix REAP-246B EP regression (which doesn't exist on proper canonical) AND sync overhead (which is only 15% per perf-record, not 96% as previously framed). Surfaced in cpu-inference-optimization-index ⚑ block. | [cpu-inference-optimization-index](cpu-inference-optimization-index.md) / [sarathi-serve-cpu-evaluation.md](sarathi-serve-cpu-evaluation.md) |
| 27e | HIGH (GATE) | **CPU20 — Benchmark rigor and revalidation gate**. Mandatory before declaring any CPU track exhausted/deployable. Enforces canonical baseline policy, process hygiene, library-path identity, compile-path verification, and targeted revalidation of previously drift-prone claims (EP frontdoor, >150B EP regressions, CPU1 stability, CPU2 mbind delta). | [cpu-benchmark-rigor-and-revalidation.md](cpu-benchmark-rigor-and-revalidation.md) / [cpu-inference-optimization-index](cpu-inference-optimization-index.md) |
| 28 | HIGH | **Trinity-derived coordinator/routing tasks** (intake-474, ICLR 2026, Sakana AI; deep-dive 2026-04-26). Trinity is direct prior art for our lightweight-learned-coordinator-over-heterogeneous-pool thesis. **Standing comparative context** for orchestration/routing work. New handoffs: [`tri-role-coordinator-architecture.md`](tri-role-coordinator-architecture.md) (TR-1..TR-5, +5 to +8 points expected from per-call role axis per Trinity ablation, optimizer-independent) + [`outer-coordinator-learned-head.md`](outer-coordinator-learned-head.md) (OC-0 scoping only, gated). Cross-handoff tasks: LRC Phase 4 P4.1-P4.4 (feature-position audit / block-ε diagnostic / SVD-FT / sep-CMA-ES cold-start) + DAR-1.5 (REINFORCE-pathology audit). Roll-up at `routing-and-optimization-index.md` P19. Recommended start: P19.6 (DAR-1.5 audit, 1 session). | [routing-and-optimization-index](routing-and-optimization-index.md) P19 / [tri-role-coordinator-architecture.md](tri-role-coordinator-architecture.md) / [outer-coordinator-learned-head.md](outer-coordinator-learned-head.md) / [Trinity deep-dive](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) |

---

## Domain Indices

| Domain | Index | Handoffs | Status |
|--------|-------|----------|--------|
| Routing & Optimization | [routing-and-optimization-index.md](routing-and-optimization-index.md) | 11 | P0-P4 complete, **P5 Phase 5 seeder refactor DONE**, P6 RI-10 canary, P7-P9 pending, P10/P11 DONE, P13 DAR-1/2 done, **P14 NEW: AutoPilot iteration strategy upgrade** (AP-28–31, 4-phase: strategy memory, knowledge distillation, context budget, mutation graph). AR-3 needs restart. |
| Inference Acceleration | [inference-acceleration-index.md](inference-acceleration-index.md) | 6 active + completed | KV quantization COMPLETED (moved), **KV compaction L1-L4+L4b merged to production** (native ggml), KV selection eval phase, ~~v3 PRODUCTION~~ (completed/), GPU acceleration path (researched, +vLLM Dflash plan), **Log-Linear GDN readiness** (stub — monitoring), Qwen3.6 production upgrade (GGUF downloaded, benchmark pending), ~~TIDE calibration-router early exit~~ **DEPRECATED 2026-04-23** (post-hoc dead end), **Hadamard KV smoothing + f16 fix merged** to v4 kernel, **NEW: GLM-5.1-REAP CPU eval** (intake-427 revised, 555B/14B-active GGUF, stack simplification candidate), **CPU20 rigor gate integrated** for all CPU throughput claims |
| Agent Integration | [hermes-agent-index.md](hermes-agent-index.md) | 3 | B1-B7 ALL COMPLETE + integration wired, shell low priority |
| Research & Evaluation | [research-evaluation-index.md](research-evaluation-index.md) | 8 + P7 + P3b + 2 new | tool-compression A/B done (+4pp), REPL S1-S2 done (S3a/S5 next), reasoning done, **P7 Ouro eval queued**, multiscreen → full sub-quadratic survey, **Log-Linear GDN** HIGH priority monitoring, P3b Tulving episodic benchmark, **NEW: MAD confidence scoring** (adopt_component), **TIDE early exit** (adopt_patterns) |
| Pipeline Integration | [pipeline-integration-index.md](pipeline-integration-index.md) | 4 | vision done, TTS blocked, PDF/Lean pending |

---

## Standalone Handoffs

Not covered by any sub-index. Small, focused, or cross-cutting.

| Handoff | Domain | Status | Priority | Last Updated |
|---------|--------|--------|----------|-------------|
| [colbert-reranker-web-research.md](colbert-reranker-web-research.md) | web_research pipeline | S1-S4 done (ONNX Runtime, 180ms, PyLate eliminated), S5 gated on AR-3 data, S7 surprisal chunking proposed | MEDIUM | 2026-04-18 |
| [internal-kb-rag.md](internal-kb-rag.md) | Internal markdown KB retrieval (wiki/, handoffs/, research/, progress/, docs/chapters/) | STUB 2026-04-25 — proposal from local-RAG architecture review. Reuses ColBERT/ONNX plumbing from colbert-reranker-web-research as a sibling consumer; no AR-3 gate. K1–K7 work items. | MEDIUM | 2026-04-25 |
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
| [unified-trace-memory-service.md](unified-trace-memory-service.md) | Cross-source provenance store (agent_audit.log + progress/ + autopilot_journal) | STUB 2026-04-25 — proposal from local-RAG architecture review. Read-only SQLite query layer over existing logs; no migration. T1–T7 work items. Distinct concern from autopilot evolutionary memory and Hermes conversation memory. | MEDIUM | 2026-04-25 |
| [agent-world-env-synthesis.md](agent-world-env-synthesis.md) | Autopilot 5th species: environment + task synthesis (DD6, intake-444) | stub / in-planning — Phase 1 training-free, Phase 2 GPU-gated | MEDIUM | 2026-04-22 |
| [minddr-deep-research-mode.md](minddr-deep-research-mode.md) | 3-agent Planning/DeepSearch/Report specialization (DD7, intake-438) | stub / in-planning — Phase 1 prompt-level, Phase 2 GPU-gated | MEDIUM | 2026-04-22 |
| [decision-aware-routing.md](decision-aware-routing.md) | Q-scorer decision-aware learning | DAR-1/2/3/4 done. Episodic memory routing intel added (reasoning models collapse at 100K). | HIGH | 2026-04-18 |
| [eval-tower-verification.md](eval-tower-verification.md) | Eval tower calibration + verification | NEW — ECE/AUC metrics, ThinkPRM T2, cross-family verification | MEDIUM | 2026-04-14 |
| [qwen36-production-upgrade.md](qwen36-production-upgrade.md) | Model upgrade evaluation | IN-PROGRESS — GGUF downloaded (Q4_K_M+Q8_0), deep dive confirms drop-in replacement. Benchmark pending. | **HIGH** | 2026-04-17 |
| [learned-routing-controller.md](learned-routing-controller.md) | Routing classifier training | Phase 1 ✅ (92% val acc, 157K samples, flag enabled); P1.5 logit probe + P2.3-2.6 hidden-state probes + P3 BGE elimination pending | **HIGH** | 2026-04-15 |
| [per-request-reasoning-budget.md](per-request-reasoning-budget.md) | Per-request `</think>` budget | Steps 1-2 DONE (root cause: SSM state race on hybrids, 3 fix options proposed). Steps 3-4 need running server. Workaround: `--jinja` removed from architect_general (coarse). | MEDIUM | 2026-04-17 |
| [readme-refresh.md](readme-refresh.md) | Documentation | GATED on AR-3 trial ≥100 (currently ~78). 4 numbered tasks: epyc-root + epyc-orchestrator + epyc-inference-research READMEs + autopilot plots snapshot. | LOW | 2026-04-14 |
| [root-archetype-linter-templates-upstream.md](root-archetype-linter-templates-upstream.md) | Cross-repo upstreaming | Epyc-root side DONE (KB linter, brevity templates, wiki.yaml, wiki compile). 3 tasks remain in root-archetype repo (no local clone). | LOW | 2026-04-14 |
| [qwen36-27b-cpu-feasibility.md](qwen36-27b-cpu-feasibility.md) | Model feasibility eval | STUB 2026-04-24 (intake-455 deep-dive). Hybrid GDN+attention dense-FFN; CPU spec-dec foreclosed. P1 throughput probe + P2 coder A/B vs Qwen2.5-Coder-32B + P3 spec-dec no-go recorded. | MEDIUM | 2026-04-24 |
| [privacy-hygiene-precommit-hooks.md](privacy-hygiene-precommit-hooks.md) | KB hygiene / pre-commit | STUB 2026-04-24 (intake-452 deep-dive). PII-1 regex-only pre-commit hook across 3 repos + PII-2 fixture + PII-3 30-day re-eval. NOT a close for opendataloader gap #5. | MEDIUM | 2026-04-24 |

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
