# Bulk Inference Campaign — active backlog (Packages G–K)

**Status**: active — see *Current State* below. Packages A-F complete + archived (`../completed/bulk-inference-2026-04-packages.md`); cross-role N-way matrix closed/certified + archived. Live backlog: Package J open items (J2/J3 live probe, J7 DCP-6 eval, J9 observe-only run, J11/K-EVAL-1, J13-J15) + G/H/I tails + K. BEP-2 remediation is built; J8 is an optional decision experiment for the legacy batch-edit path, not the critical remediation gate.
**Created**: 2026-04-06
**Updated**: 2026-05-27
**Categories**: evaluation, inference, coordination
**Priority**: HIGH
**Depends on**: Package A results (complete)
**Related**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md), [`research-evaluation-index.md`](research-evaluation-index.md), [`pipeline-integration-index.md`](pipeline-integration-index.md), [`hermes-agent-index.md`](hermes-agent-index.md), [`inference-acceleration-index.md`](inference-acceleration-index.md), [`cross-role-nway-contention-matrix.md`](../completed/cross-role-nway-contention-matrix.md)

---

## Problem

14 inference-dependent tasks are scattered across 5 domain indices. Running them independently requires 14 separate stack launches with 5-15 minutes of NUMA warmup each — over 3 hours of dead time before any evaluation begins. Many tasks share the same stack configuration and can collect cross-task telemetry simultaneously via feature flags.

**Consolidation**: 14 tasks → 4 optimized runs. Each run maximizes the number of tasks resolved per inference session by piggybacking telemetry collection, A/B comparisons, and eval passes on shared model instances.

---

## Current State (2026-05-27) — Outstanding Work

The 2026-04 campaign (Packages A–F) is complete/overtaken and archived (see *Completed* below). The live inference-gated backlog is led by **Package J**:

| Item | Status | Detail / pointer |
|------|--------|------------------|
| **J2/J3 live migration probe** | OPEN | Forward/reverse migration SM verified in-process (`tests/unit/test_concurrency_aware_migration_sm.py`); genuinely-live under-traffic observation needs a single-worker API run (`--workers 6` makes CAB state per-worker, so a round-robin `/chat` probe can't observe it). → Package J · [`within-role-placement-state-machine.md`](within-role-placement-state-machine.md) |
| **BEP-2 multi-file completion** | REMEDIATION BUILT | One-shot ablation PASSED **5/5** (same tasks+verifiers, no REPL/`FINAL` choreography) → the multi-file failure is **agentic protocol/tooling, NOT coding capability**. Remediation shipped as default-off `force_mode="edit"` edit transaction (`bd87ceb` + `3c1f423` + `d4fafdf` + `fba6c84` + `0f00708`): assemble scoped files → one-shot full-file response → transactional apply/rollback → auto-finalize. Hardening validated (scope caps, fail-closed 412, side-effect-free compile, all-or-nothing unsafe-path rejection, cc-role default alignment). → [`multi-file-coding-completion-capability.md`](multi-file-coding-completion-capability.md) |
| **J8 / BEP-2 batched-edit A/B** | OPTIONAL DECISION EXPERIMENT | The shipped edit transaction solved the practical multi-file completion blocker through a different interface: full-file transaction + auto-FINAL instead of the read->edit->FINAL REPL contract. J8 still answers a distinct question: whether the older structured patchset/batch-edit path is worth keeping as a task-class knob for latency, large-repo patch economy, or provenance. It should not block edit-transaction rollout. |
| **DCP-6** | CODE-READY, INFERENCE-PENDING | No longer blocked by the BEP read-loop. DCP-4 advisory seed-bundle attach is already wired behind `features().dcp_pre_assembly` and validated by `tests/unit/test_dcp4_wiring.py`; remaining work is the DCP-6 offline replay + inference eval proving pre-assembly improves delegation without quality loss. |
| **J16 / RI-ITG-1** | code-ready, inference-pending | Ingest-triviality guard A/B (epyc-orchestrator `9203c00`, flag `INGEST_TRIVIALITY_GUARD` default-off). Enforce-mode demotion → **cannot co-run with passive J6**; dedicated host-quiet eval. Gate: leakage down, zero accuracy regression. THINK-ABL-1 (real ingest thinking ablation) folds into J12. → detailed row below + [`x-mas-text-routing.md`](x-mas-text-routing.md) § "Follow-up validation". |
| **J11 / BSV-2 · K-EVAL-1** | code-ready, inference-pending | Behavior-signature differential accept-test + `scoring_verifiers` eval; run in next host-quiet window. BSV-2's accept gate (`src/behavior_signature.py`) is **unwired autopilot-side** — wire it at the next AR-3 restart behind its own default-off flag **`AUTOPILOT_BSV2_ACCEPT_GATE`**, co-landing with EV-10a's `AUTOPILOT_SKILL_EFFICACY_GATE` (K-SKILL-1) but **flag-isolated** so the two accept-path changes stay attributable (verified collision-free 2026-05-27). |
| **Package G tail** (G3, G5, G10–G12) | partial | Full KVPress eval + stacking, short-m@k voting, AA-Omniscience factual-risk calibration. |
| **Package H** (H5) | deferred → AR-4 | RLVR eval-tower validation + EV-4 calibration baseline. |
| **Package I** | not started | Decision-aware routing validation (post-AR-3; depends on Package H). |

J6 24h autopilot soak runs on certified topology `df373c79cc4af06f`. The cross-role **N-way contention matrix is closed + certified** (all-allow on certified affinity; runtime policy is defensive, lives in `src/scheduling/contention_gate.py` + `orchestration/contention_matrix.yaml`) — handoff archived to [`../completed/cross-role-nway-contention-matrix.md`](../completed/cross-role-nway-contention-matrix.md).

> Operative sequencing + the baseline-mutation / live-affinity / concurrent-metric hard rules are in **Remaining Execution Order** below. Chronological history → `progress/2026-05/`.

## Completed — 2026-04 Campaign (Packages A–F)

Complete or overtaken by the Package J reprioritization. Full runbook detail (commands, expected outputs, results, telemetry plan) archived to **[`../completed/bulk-inference-2026-04-packages.md`](../completed/bulk-inference-2026-04-packages.md)**.

| Pkg | Outcome | Owning handoff |
|-----|---------|----------------|
| **A** | Routing thresholds recalibrated (635 decisions, 2026-04-06) | [`routing-and-optimization-index.md`](routing-and-optimization-index.md) |
| **B** | Instrumented seeding eval v2 — tool-compression +4pp, WS-3 fix validated (2026-04-10) | [`routing-intelligence.md`](routing-intelligence.md) |
| **C** | Context-folding eval batch — 30B summarizer, L3 sweet spot, TALE deferred (2026-04-11) | [`context-folding-progressive.md`](context-folding-progressive.md) |
| **D** | AR-3 relaunch + RI-10 canary (ran autonomously; canary live since 2026-04-06) | [`routing-and-optimization-index.md`](routing-and-optimization-index.md) · [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) |
| **E** | Vision + Hermes multimodal validation — Hermes PASS, vision fixed 2026-04-08 | [`pipeline-integration-index.md`](pipeline-integration-index.md) · [`hermes-agent-index.md`](hermes-agent-index.md) |
| **F** | llama.cpp v3 smoke tests + production binary swap (coder +101%, REAP +50%, 2026-04-10) | [`inference-acceleration-index.md`](inference-acceleration-index.md) |

---
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
| 10 | **J7** DCP inference gate + optional **J8** legacy BEP A/B | 3-4h each | J7's DCP-4 hook is already default-off/advisory, so only the offline replay + inference eval remain. J8 is not a remediation gate; run it only if its answer would change whether the legacy `batch_edit_mode` path is kept, retired, or exposed as a narrow task-class knob. |
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

## Package G: Deferred Inference-Dependent Research Tasks

**Duration**: Variable (opportunistic — run during Package D downtime or after D completes)
**Stack required**: Individual model servers (like Package C)
**Depends on**: Nothing — independent research evaluation
**Status**: NOT STARTED — indexed here 2026-04-11 during handoff audit

These tasks are scattered across active handoffs and require inference compute but are not time-critical. Consolidated here so they can be scheduled opportunistically.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| G1 | Memento S2 feasibility | [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | Benchmark KV masking overhead on llama.cpp. Test if KV states from masked blocks preserve accuracy. | Any 8B+ model | ~4h |
| G2 | Expected Attention S8 profile sweep | [triattention-kv-selection.md](triattention-kv-selection.md) | Sweep `keep_ratio` and `layer_weights` per production role; record Pareto profile with quality, speed, cost, and reliability axes. Historical S1 deployment evidence moved to completed ledger. | coder_escalation + one long-context role | ~4h |
| G3 | Expected Attention stacking/high-compression check | [triattention-kv-selection.md](triattention-kv-selection.md) | Reopen selection + quantization stacking only if S8 shows production need for higher compression; otherwise compare Attention Matching before adding kernel complexity. | coder_escalation | ~4h |
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

> **▶ STATUS UPDATE (2026-05-27) — supersedes the "Status" line below.** The 2026-05-26 status is stale. Current truth (reconciled against `orchestration/contention_matrix.yaml` + `data/bulk_inference_2026_05_26/execution_manifest.jsonl`):
> - **Contention matrix: CLOSED + certified, ALL-ALLOW.** The famous `{frontdoor,ingest,vision}=0.847` "block" was a **bad-affinity artifact** (launcher `_numa_prefix` bug mis-pinned quarters); re-benched on certified disjoint quarters (`live_affinity_verified=true`) it is **1.731 allow**, and every measured N-way set allows (`4363dae`). **No measured N-way block remains.** New hard gate: `live_affinity_verified` + `affinity_preflight.py` artifact (topology_hash alone is insufficient).
> - **J4b/J5: SUPERSEDED** by the certified re-bench (their verdicts were bad-affinity). **J4c: LIVE but now DEFENSIVE** (`nway_policy` wired; nothing currently queues). **J4: RATIFIED** (placement SM live; per-role policy decided). **J6: relaunched repeatedly** (soak runs on `df373c79`, production API; the live daemon pid changes on every relaunch — discover it at runtime via `pgrep -af "autopilot.py start"`, do not trust any pid written here).
> - **J1 core PASS; J2/J3 NOT live-closed** — migrations never naturally triggered in the ratification autopilot; a dedicated live migration probe is still pending.
> - **BEP-2 status changed after the 2026-05-27 edit-transaction work**: the read-loop is no longer the active remediation blocker. Qwen3.6 passed the direct one-shot ablation 5/5, and the default-off `force_mode="edit"` transaction path is built + hardened. **J8 is now optional for a narrower decision**: whether to keep, retire, or task-scope the legacy structured patchset/batch-edit path. **DCP-6 is no longer gated on BEP's read-loop**, and DCP-4 advisory attach is already wired/default-off; only its offline replay + eval remain.
> - **N-way runtime policy** is fail-OPEN for unmeasured foreground / closed-world for background-bulk (matches the code + cross-role-bw handoff); the older "closed-world serialize" wording is superseded.

**Duration**: ~1-3 days if sequenced; J5 (matrix re-bench) can run overnight
**Stack required**: Standard orchestrator stack; J1-J3 require `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1`; J3 additionally requires `ORCHESTRATOR_REVERSE_MIGRATION=1` set in the API env
**Depends on**: epyc-orchestrator main @ `15350fe` or later — both feature branches MERGED 2026-05-26 (`fe6805c` placement WP-0..WP-4 + WP-5 scaffold; `15350fe` intake-607 harness DCP/BEP/BSV/URE). 347 unit tests on main; all new code additive + flags default-OFF. No further branch merging needed before any J task.
**Status**: IN PROGRESS (claude 2026-05-26). Preflight PASS (67 tests). **J4a DONE** (`data/contention_matrix/bulk-2026-05-26-j4a/`). **J1 core PASS** — placement SM scales concurrent frontdoor 1.68×–1.91× across disjoint instances, no overlap; the `topology_overlap` queue is NOT observable via `/chat` (HTTP rate limiter 60rpm/10burst + a persistent dashboard client cap concurrent arrivals) → **J1 queue + J2/J3 migration verification re-vehicled to the autopilot eval-concurrency fan-out path** (the original WP-0 motivation). **J4b**: first full-instance pass exposed an operator-flagged methodology error → corrected to a **quarter-level disjoint-cpuset feasibility model** (`enumerate --feasibility`: 25 feasible / 32 `topology_infeasible`); quarter-level re-bench (`--safe-sampling`) IN PROGRESS (`data/contention_matrix/bulk-2026-05-26-j4b-feasible/`). **gemma4 worker_general full-instance crash FIXED** (uncaught PEG-parser throw → raw-content fallback; ik_llama.cpp `d84755dc`, rebuilt+redeployed+verified). Findings F1–F4 in [within-role-placement-state-machine.md](within-role-placement-state-machine.md); correction detail in [cross-role-nway-contention-matrix.md](../completed/cross-role-nway-contention-matrix.md). Remaining: finalize quarter-level matrix → J4c policy wiring → J5/J4/J6 → J7–J12.

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
| J4a | XCM-1 N-way contention candidate enumeration | [cross-role-nway-contention-matrix.md](../completed/cross-role-nway-contention-matrix.md) + `scripts/server/contention_matrix.py` | Add/verify an enumeration mode that produces every non-trivial candidate N-way active set from the live role topology up to the scheduler's maximum cross-role concurrency. Prune trivial supersets containing any pair that is `block`, below `default_floor`, unknown, or same-role blocked. Keep candidates where all lower-order constituents are allowed under **background/bulk** policy; these are not certified until J4b measures them. Emit a manifest with `candidate_roles`, lower-order evidence, prune reason, topology hash, and `live_affinity_verified` status. | no inference if dry-run; full stack metadata | ~1h code/dry-run |
| J4b | XCM-2 N-way contention matrix re-bench | [cross-role-nway-contention-matrix.md](../completed/cross-role-nway-contention-matrix.md) + `orchestration/contention_matrix.yaml` | Run the J4a candidate manifest alone on the host after live affinity is clean. Measure triples first; skip any quad/superset containing a failing triple. For each measured N-way set, compute `seq_aggregate_tps`, `parallel_aggregate_tps`, ratio, CV across 3 runs, and verdict. Update `contention_matrix.yaml` with `n_way:` entries and `excluded_n_way:` entries for candidates pruned by known-bad pairs/triples. Gate: for the current topology hash and verified live affinity, every non-trivial N-way active set is classified as measured `allow`, measured `block`, or explicitly excluded; there must be no residual `unmeasured` bucket. Future stack/topology changes are out of scope and require matrix re-derivation. Any pre-affinity-fix row involving `worker_general` or `vision_escalation` quarters is diagnostic-only until rerun. | full production stack | ~4-12h, runs alone |
| J4c | XCM-3 N-way policy wiring / scheduling guard | [cross-role-nway-contention-matrix.md](../completed/cross-role-nway-contention-matrix.md) + `src/scheduling/contention_gate.py` | If runtime bulk scheduling can launch multiple cross-role tasks at once, teach it to consult the `n_way` matrix for the exact active-set union before treating an all-pairwise-allowed N-way combo as certified. Operator policy before J4b completes is fail-closed. Operator policy after J4b completes is closed-world for the current topology: launch only active sets classified in `n_way` as `allow`; treat `block`, `excluded_n_way`, missing entries, or topology-hash mismatch as queue/serialize. | no extra inference after J4b | ~2-4h |
| J4 | WP-5 ratification observability run | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 5 | With WP-2 + WP-3 + WP-4 enabled, and after J4a/J4b/J5 matrix gates complete, run autopilot for ~6-12h and collect: (a) per-role concurrency histogram, (b) full vs quarter utilization, (c) migration counts forward + reverse, (d) N-way active-set IDs and matrix verdicts for any cross-role overlap. Decide per-role `placement_policy` values: keep `solo_prefer_full` for autopilot-dominant low-concurrency roles; switch worker_general to `burst_prefer_quarters` if concurrent load grows; consider `full_disabled` for any role where full is wasted memory. Edit NUMA_CONFIG, commit, restart, re-run. | full production stack | ~12h observation + ~1h analysis |
| J5 | WP-6 matrix re-bench (within-role instance pairs) | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 6 | Extend `epyc-orchestrator/scripts/server/contention_matrix.py` (Phase F harness from cross-role-bw-aware-routing) to sweep within-role pairs `full+q0, full+q1, full+q2, full+q3, q0+q1, q0+q2, q0+q3, q1+q2, q1+q3, q2+q3` for each role with ≥2 instances. Update `orchestration/contention_matrix.yaml` schema with `instance_pairs` block + `topology_hash` + affinity artifact. Gate: live affinity exact-match before sampling; CV ≤ 5% across 3 runs; runtime fails closed on topology/YAML hash mismatch. **Stack-conflict risk** — runs llama-bench across many configurations; must run alone. Current repair priority is to rerun `worker_general` and `vision_escalation` after validated reload because their quarter-launch affinity was suspect; frontdoor's current certified path remains Half0 solo anchor plus q0-q3 quarters. | All multi-instance roles (frontdoor, worker_general, ingest_long_context, vision_escalation) | ~overnight (~8-12h) |
| J6 | WP-7 production rollout + 24h gate | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 7 | Switch `_eval_concurrency()` default from static `max_safe_concurrency(frontdoor)` to "matrix-aware" — query the gate at startup for the role's max sustainable concurrency given measured ratios (uses J4b + J5 data). Document operator override path in `wiki/autopilot-tuning.md`. Run a 24-hour autopilot pass; compare quality, median request t/s, aggregate batch t/s, and wall-clock throughput vs Phase 0 baseline; verify dashboard shows quarters actively rotating; assert `contention_timeout_count` stays at baseline. | full production stack | ~24h passive + ~1h analysis |
| J7 | DCP-6 delegation context pre-assembly eval | [delegation-context-preassembly.md](delegation-context-preassembly.md) DCP-6 | DCP-4 advisory attach is wired/default-off (`features().dcp_pre_assembly`) and validated by `tests/unit/test_dcp4_wiring.py`. Measure on a delegation-heavy workload: prefill tokens, end-to-end latency, top-up count, bundle-build latency, downstream answer quality, hallucinated-file references, context-contamination failures vs reactive-discovery baseline. Run offline replay over historical tasks first (validates bundle size/coverage), then the inference gate. Default-off flag stays off until results justify. | frontdoor + worker_coder (delegation-heavy roles) | ~3-4h |
| J8 | BEP-2 batched edit CPU-latency A/B | [batched-edit-parallel-apply.md](batched-edit-parallel-apply.md) BEP-2 | **Optional decision experiment for the legacy batch-edit path.** The production-relevant remediation is the shipped edit transaction, which bypasses both the interleaved Root LM loop and the old patchset proposal. Run J8 if the answer would change whether `ORCHESTRATOR_BATCH_EDIT_MODE` is kept, retired, or exposed as a narrow task-class knob, especially for large-repo patch economy or structured-patch provenance. Do not run it merely to validate the already-built edit-transaction remediation. | worker_coder + frontdoor | ~3h |
| J9 | HLE-4 harness metrics observe-only run | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) HLE-4 + [meta-harness-optimization.md](meta-harness-optimization.md) HLE-1/2/3 | `EvalResult` + journal JSONL carry `harness_metrics`, `oracle_adequacy`, `metric_schema_version` and retain concurrency telemetry fields. Schema plumbing landed in `epyc-orchestrator` `931e43c`; rule-based HLE-1 metrics + HLE-2 oracle-adequacy defaults landed in `9222a19`. Remaining work: run autopilot for N trials with metrics in **observe-only mode** (no Pareto promotion). Analyze: separation accepted-vs-rejected, correlation with future regressions, missingness rate, p95 metric-extraction cost. Cheap-kill: metric that never separates or has missingness >20% stays diagnostic, doesn't promote to Pareto co-objective. | full autopilot stack | ~6-12h observation |

### Sequencing notes

- **Preflight → J1 → J2 → J3 → J4a/J4b/J5 → J4** is the new parallelization block. J1-J3 prove dispatcher safety; J4a/J4b close cross-role N-way contention; J5 closes within-role instance-pair contention; J4 observes policy choices on the now-characterized stack.
- **J4b and J5 matrix benches** must run ALONE on the host and honor `feedback_no_concurrent_inference`. They are the highest stack-conflict risk in this Package and are required before using cross-role concurrency to speed up the remaining inference backlog.
- **Affinity repair outranks matrix reuse**: if live affinity differs from `NUMA_CONFIG`, the matrix is stale even when `topology_hash` matches. Reload/fix the affected role first, then rerun all matrix evidence involving that role/shape before J4/J6 or downstream parallel bulk work.
- **Optional frontdoor Half1 exploration is out-of-band**: do not add or assume a second half frontdoor inside the repair path. If pursued, create a separate topology experiment after current matrix repair: add Half1 port/config, validate affinity, measure Half0+Half1 and Half0/Half1+quarters against current q0-q3 policy, update `topology_hash` and rederive the matrix before use.
- **J6 (production rollout)** is 24-hour passive once flipped; can start as soon as J4a/J4b/J5 are done and any J4c policy wiring needed for bulk scheduling is in place.
- **J7 and J9** are independent of the WP implementation work but should run after J1-J3 so they inherit safe fan-out. J7 is an autopilot-style eval against the production stack; its DCP-4 hook is already built, but concurrent-run metrics must still be labelled. J9 is observe-only, but it should still record `speed_metric_mode`, median request t/s, and aggregate batch t/s so later scheduling does not learn from mixed semantics. **J8 is optional** because edit-transaction mode solved the practical BEP-2 blocker; keep it out of the critical run order unless its result would change the legacy batch-edit path's keep/retire/task-scope decision.

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
| J12 | chat_template_kwargs registry-driven wiring verification | epyc-orchestrator `cac4148` (chat_template_kwargs passthrough merge) + [x-mas-text-routing.md](x-mas-text-routing.md) | Data-plane shipped 2026-05-20: `src/backends/openai.py` now passes `request.extra["chat_template_kwargs"]` to llama-server's chat-completions endpoint. **Wiring follow-up**: add the small code change that auto-populates `request.extra["chat_template_kwargs"]` from `model_registry.yaml`'s per-role defaults (currently every caller has to set it manually). Then run the cheap-kill empirical comparison from the merge commit body — 15-task mixed-domain probe on frontdoor (Qwen3.6-35B Q8) + architect (Qwen3.5-122B): pre-wiring baseline vs post-wiring with `enable_thinking=False`. Gate: frontdoor +30pp or better, architect +15pp or better, ingest_long_context untouched (its registry entry carries no kwarg override). **CORRECTION 2026-05-30**: `enable_thinking` is a documented **no-op for Qwen3-Next-80B (ingest) and gemma4** — their templates ignore the kwarg, so the gate clause "ingest unchanged because thinking-on is load-bearing" is moot (you can't toggle it via the kwarg anyway). The "thinking load-bearing" claim is itself confounded — see [x-mas-text-routing.md](x-mas-text-routing.md) conclusion #2 (the only "ablation" differed in max_tokens 4096→2048, 2/15 ingest tasks truncated at the cap). **Folds in THINK-ABL-1**: a real ablation for ingest needs a non-no-op suppressor (Qwen3 `/no_think` or empty-`<think></think>` injection) at fixed non-truncating max_tokens, same tasks both arms — do this alongside the J12 wiring verification, not as a separate run. | frontdoor + architect_general + ingest_long_context | ~1h wire + ~1h verify + ~1h ablation |
| J13 | P17.BT-3 axis-vote BT tiebreak falsification | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) § P17 BT-3 (epyc-orchestrator commits `2e51c86` + `60ed552` + `45df95c` + `56ee9fc` range-normalization fix) | Passive observation during one autopilot run. The `bt_tiebreak_hint` block is already wired into the rich-prompt template; the journal/digest already capture `"BT-tiebreak disagrees with hypervolume top"` when the axis-vote BT picks a different top-K seed than the range-normalized hypervolume-contribution top (post-`56ee9fc` the top-K key is per-axis range-normalized so the disagreement isn't an axis-magnitude artifact). Post-run analysis: among trials where stagnation fired AND BT disagreed with the hypervolume top, what fraction of BT-picked seeds reached the Pareto frontier within the next 10 trials? Compare to base rate of "hypervolume-top seed reaches Pareto within 10 trials." Pre-enforcement gate: BT-picked seed must reach Pareto-dominant at ≥1.2× the hypervolume-top base rate, with ≥10 disagreement events in the run. Prereq: orchestrator commits on main; falsification needs ≥50 stagnation-fired trials in one run. **Shadow-only** — wiring already lands a hint into the rich prompt; analysis is offline. | autopilot eval stack (no new models) | passive collection during a normal autopilot run + ~1h analysis |
| J14 | DAR-6.5 swarm-fanout adversarial-robustness A/B | [decision-aware-routing.md](decision-aware-routing.md) § DAR-6.5 | 2-arm A/B on a chosen injection suite (Garak / HouYi / PromptInject — pick one with active maintenance + Apache/MIT licence). Arm A: existing single-model escalation. Arm B: N≥2 heterogeneous concurrent serves via `dispatch_swarm_fanout` in `src/swarm_fanout.py`, aggregated via the shared BT module (`src/bradley_terry.py`). Replicates intake-615's published 0.12% vs 6.20% prompt-injection-degradation claim on our own suite. Pre-enforcement gate: ≥3pp absolute reduction in injection-success rate AND ≤30% per-stream throughput regression at the swarm-fanout setting. **Prereq status (2026-05-28)**: (1) P26.1 BT module ✅ (`src/bradley_terry.py`); (2) DAR-6.1 feature flag ✅ (`features().swarm_fanout`, default-off), DAR-6.3 dispatch ✅ (`dispatch_swarm_fanout`), DAR-6.4 BT-aggregator ✅ (`bradley_terry_aggregate`) — all in epyc-orchestrator commit pending; (3) injection-risk classifier is now explicitly tracked as [routing-intelligence.md](routing-intelligence.md) RI-13, but should **not** be built before the cheap-first unconditional J14 A/B clears its gate. | 2-3 heterogeneous concurrent serves (e.g., gemma4-26B-A4B + qwen3.6-35B + qwen3-coder, depending on injection-suite topic) + injection eval harness + a pairwise judge model OR the included `length_proxy_aggregator` baseline (the latter is documented as a deliberate weak baseline — see `src/swarm_fanout.py:length_proxy_aggregator`) | 1-2 days A/B harness assembly + one eval run (DAR-6.1/6.3/6.4 are no longer in this estimate — already ✅) |
| J15 | MD-9 deep_research_mode sentinel A/B | [minddr-deep-research-mode.md](minddr-deep-research-mode.md) MD-9 | Phase 1 MindDR readiness gate. Sentinel suite at `orchestration/deep_research_sentinel.yaml` (20 curated queries: 7 BrowseComp + 7 WideSearch + 6 mixed); each query is pre-tagged `is_research_like=True`. Run the suite with `ORCHESTRATOR_DEEP_RESEARCH_MODE=0` (control) then `=1` (treatment), score on the four NaN-safe rubric fields already wired into `EvalResult` (`rubric_reasoning_trajectory`, `rubric_tool_calls`, `rubric_outline`, `rubric_content_stage`). Promote to production default iff uplift ≥+5pp on the aggregate rubric AND no regression on the existing eval-tower sentinels. **All prereqs already landed 2026-04-22** (MD-1 flag, MD-2 classifier, MD-3/4/5 prompts, MD-6 pydantic_graph subpackage, MD-7 EvalResult rubric stubs, MD-8 sentinel suite). The LLM-as-judge scoring functions themselves are tracked separately as EV-9 in [`eval-tower-verification.md`](eval-tower-verification.md) (also inference-gated; if EV-9 hasn't landed at J15 run-time, fall back to structural-only scoring against the `expected_contains` hints baked into the sentinel YAML). | frontdoor + worker_coder + web-research backend (per the three-agent pydantic_graph pipeline) | ~1 day inference + ~2h analysis |
| J16 | RI-ITG-1 ingest-triviality guard A/B | epyc-orchestrator `9203c00` (flag `INGEST_TRIVIALITY_GUARD`, default OFF, depends on `specialist_routing`) + [x-mas-text-routing.md](x-mas-text-routing.md) § "Follow-up validation" | The learned MemRL router leaks ~8.5% of ingest_long_context traffic as trivial short prompts (153/1803 math in the 2026-05-30 tap analysis) — a ~19× latency tax (80B @ ~6.4 t/s) for work a cheap role answers identically. `apply_ingest_triviality_guard` demotes ingest→`worker_general` ONLY for positively-trivial requests (difficulty band ≠ medium/hard AND short AND no long-context). 2-arm enforce A/B vs flag-off baseline on the eval-concurrency fan-out; also enable `difficulty_signal` shadow/enforce so the easy-band path is live. **Gate**: ingest short-prompt leakage materially reduced AND **zero accuracy regression** vs baseline; long-context + short-but-hard reasoning routes unchanged. Then consider default-on. | frontdoor + ingest_long_context + worker_general (existing stack; no new models) | ~1-2h enforce A/B + ~1h analysis |

**Sequencing of the appended items (intake-607 residual gates + 2026-05-27 P17/DAR-6 additions):**
- **J16 (RI-ITG-1)** is an **active routing change** (enforce-mode demotion), so it **cannot co-run with the passive J6 24h soak** (would contaminate the baseline) — run it as a dedicated cheap eval in a host-quiet window after the matrix gates, like J11/K-EVAL-1. *Partial-fold option*: a shadow/observe mode (log would-demote without demoting) would be observe/advisory and could ride J6 to passively quantify leakage; that mode is **not yet built**, and the accuracy A/B needs enforce mode regardless. THINK-ABL-1 (real thinking ablation for ingest) is **not** a J16 item — it folds into **J12** (same chat_template_kwargs subsystem); see the corrected J12 row above.
- **J10 (URE-1) is shadow-only** — flip the flag and let it accumulate during ANY of J1–J9 or Package I traffic; it shapes no workload and needs no dedicated slot. Analyze once enough decisions accrue.
- **J11 (BSV-2)** runs per-mutation inside the autopilot accept loop; co-runs naturally with J9's autopilot observation window.
- **J13 (P17.BT-3) is also passive** — the rich-prompt hint is already wired; J13 just needs an autopilot run long enough to accumulate ≥50 stagnation-fired trials. Co-runs naturally with J9 / J11 / Package I traffic; no dedicated slot needed. Pure offline analysis after the run.
- **J14 (DAR-6.5)** had a real prereq backlog until 2026-05-27 when DAR-6.1/6.3/6.4 scaffolding landed. Remaining prereq is the conditional-routing trigger (DAR-6.2 injection-risk classifier in [`routing-intelligence.md`](routing-intelligence.md)); cheap-first variant runs unconditional A/B without it, decoupling J14 from the classifier work.
- **J15 (MD-9)** has zero outstanding prereqs as of 2026-04-22 (all of MD-1..MD-8 done). Sentinel YAML + EvalResult rubric fields + pydantic_graph subpackage all present. Can run any time inference window opens; results compare to existing sentinel baselines.
- J10/J11/J13 are gated on their wiring landing (URE-1 shadow logger; BSV-1 accept-wire; P17.BT-2 rich-prompt hint — all on main). Schemas + pure algorithms on `15350fe` and orchestrator `2e51c86`+`60ed552`+`45df95c`. DCP-6/BEP-2/HLE-4 are already covered above as J7/J8/J9 — no duplication.

### Per-gate conditional workflows + mitigation policies (intake-607 gates J7–J11 — READ BEFORE RUNNING)

Each gate is a **decision point**, not just a measurement: run → branch on the result → apply the mitigation. Deep specs are in the owning handoffs (linked); this is the operator decision tree so the run can proceed in one sitting without round-trips.

**Pre-run wiring status** (none is in production until wired AND its gate passes; all flags default-OFF):
- **J10 / URE-1**: shadow logger **WIRED** (`ORCHESTRATOR_URE_UNCERTAINTY_SHADOW_LOG`) on main (merged 2026-05-26) — runnable now.
- **J7 / DCP-6**: **DCP-1 + DCP-2 discovery + DCP-3 ast-codemap DONE** on main (merged 2026-05-26) and **DCP-4 advisory attach DONE** in the live specialist delegation path (`chat_delegation._maybe_dcp_seed_context`, flag `dcp_pre_assembly`, default-off; validated by `tests/unit/test_dcp4_wiring.py`). Remaining work is the DCP-6 offline replay + inference A/B.
- **J8 / BEP-2**: optional legacy path. `_execute_turn` batch divergence + sandboxed patchset path are wired behind `ORCHESTRATOR_BATCH_EDIT_MODE`, but the active remediation path is already the `force_mode="edit"` transaction, not this batch-vs-interleaved A/B.
- **J9 / HLE-4**: `EvalResult`/journal extension is DONE (`931e43c`), and rule-based HLE-1 metric computation + HLE-2 oracle-adequacy registration are DONE (`9222a19`) in observe-only form. Remaining work is the J9 observe-only run and metric-validity analysis. Shared trace schema is done.
- **J11 / BSV-2**: needs BSV-1 signature wired into the archive accept-path + paired-eval lane. Compute (`compute_behavior_signature`, `diff_signatures`) done.

**J8 — BEP-2 batched-edit A/B (optional decision experiment; NOT on the critical remediation path):**
- **What it decides**: whether the legacy structured patchset/batch-edit mode is worth keeping as a task-class knob, retiring, or preserving only for provenance/large-repo patch-economy cases.
- **What it does not decide**: whether Qwen3.6 can complete multi-file coding tasks, and whether the edit-transaction remediation works. Those were already answered by the direct one-shot ablation and the edit-mode unit/module/server validations.
- **Run J8 if** the answer would change `batch_edit_mode` ownership: keep/retire decision, large-repo/full-file-cost concern, need for structured-patch provenance, or evidence for BEP-3 task-class routing.
- **Defer J8 if** the immediate goal is routine coding completion reliability, because `force_mode="edit"` is the higher-leverage shipped path and J7/J9/J11/J13-J15 are more directly actionable in scarce inference windows.
- ✅ batch cuts end-to-end latency ≥15% AND quality within −1pp AND parse-failure ≤5% AND apply-failure ≤2% (whole-repo verify) → keep the legacy batch flag available for narrow task-class experiments; do **not** displace edit-transaction mode without a separate rollout decision.
- ⚠️ latency win but quality −1..−3pp OR parse/apply failures 5–15% → do NOT promote; keep the legacy flag off and treat the result as parser/prompt hardening evidence only.
- ❌ no latency win OR quality < −3pp OR failures >15% → retire the legacy batch-vs-interleaved path; record NEGATIVE in the handoff + intake-605. This does **not** invalidate the shipped edit-transaction remediation.
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

**J13 — P17.BT-3 axis-vote BT tiebreak falsification (offline post-run analysis):**
- Sample requirement: ≥50 stagnation-fired trials in the run with ≥10 disagreement events (axis-vote BT picks ≠ range-normalized hypervolume-contribution top).
- ✅ Among disagreement events, BT-picked seed reaches Pareto-dominant within 10 trials at ≥1.2× the naive-top base rate → **keep the hint in the rich-prompt template**; queue P17.BT-4 (true peer-judged BT) for evaluation against this baseline.
- ⚠️ Disagreement rate <10 events in the sample → run inconclusive; extend the window OR record "axis-vote BT rarely disagrees with hypervolume top on this workload" (negative-but-narrow result; don't kill the hint, but de-prioritize P17.BT-4).
- ❌ BT-picked seed reaches Pareto-dominant at ≤ naive-top base rate → axis-vote BT adds no signal on top of scalarization → **remove the `bt_tiebreak_hint` block from the rich-prompt template** (underlying `bt_tiebreak_topk` method stays for future re-eval but is no longer surfaced); kill P17.BT-4.
- **Mitigation**: hint is documented as "treat as hint, not directive" in the template itself; failure mode is at worst a cosmetic prompt addition with no routing impact; revert is a one-line edit to the template.

**J14 — DAR-6.5 swarm-fanout adversarial-robustness A/B (publishability falsification):**
- ✅ ≥3pp absolute reduction in injection-success rate AND ≤30% per-stream throughput regression at the chosen N=2 or N=3 swarm-fanout setting → enable the routing mode (separate enforce flag); also queue work on the conditional injection-risk classifier in [routing-intelligence.md](routing-intelligence.md) so swarm-fanout is reserved for high-risk prompts rather than always-on.
- ⚠️ Reduction in injection-success rate present but <3pp OR throughput regression 30–50% → keep DAR-6 code path but stay shadow-only; revisit if (a) lighter peer models (8B specialists) emerge from swarm-dataset-distillation or (b) hardware changes.
- ❌ No measurable reduction OR throughput regression >50% → **kill DAR-6 swarm-fanout mode**; document the kill in DAR § DAR-6 with the exact A/B numbers; the BT module remains available for the autopilot P17 and distillation P3 consumers.
- **Mitigation**: cheap-first variant runs the A/B unconditionally on a fixed injection-prompt set BEFORE building the conditional-routing trigger; this isolates "does swarm-fanout reduce injection success at all?" from "is our routing classifier good enough to gate it?"

**J15 — MD-9 deep_research_mode sentinel A/B (Phase 1 promotion gate):**
- ✅ Aggregate rubric uplift ≥+5pp on `deep_research_sentinel.yaml` AND no regression on existing eval-tower sentinels → set `deep_research_mode` production-default ON for queries matching `is_research_like()`; queue MD-7 LLM-as-judge wiring (EV-9 in [`eval-tower-verification.md`](eval-tower-verification.md)) if it wasn't already landed.
- ⚠️ Uplift 0–5pp OR regression on a sub-rubric (e.g., `tool_calls` worse but `outline` better) → keep `deep_research_mode` flag available but stay default-off; the rubric breakdown is the trigger for MD-3/4/5 prompt iteration before re-running.
- ❌ Uplift ≤0pp OR meaningful regression on existing sentinels → leave flag default-off; record the kill in [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) with rubric-level numbers; Phase 2 (RL) becomes unmotivated.
- **Mitigation**: flag-off is the default state; routing classifier `is_research_like()` shadow-logs without altering routing today (per MD-2); the pydantic_graph subpackage at `src/graph/minddr/` is decoupled from production `src/graph/` so a kill is just "stop calling the new entry point" — no rollback of routing infra needed.

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
| **K-SKILL-1** (EV-10a/b) — skill-efficacy gate validation | **Decision logic only** landed: `scripts/autopilot/skill_efficacy.py` (`evaluate_skill_efficacy`/`_split` negative-delta guard + dev/test discipline; surrogate `proxy_reward`/`feedback`/`require_cross_family`), 19 tests pass. **NOT turnkey** — unlike the rows above, the live no-artifact baseline eval arm + the `apply_mutation_isolated`→`ctx.accept()` call site are NOT yet wired; that wiring is deferred to the **next AR-3 restart** (AP-29/30/31 pattern, so a running campaign isn't perturbed). | Two-stage, **post-AR-3 / AR-4** (modifies the eval trust boundary, same class as H5/EV-4): (1) at the AR-3 restart, wire the no-artifact arm + accept-path hook; (2) paired A/B over a sample of PromptForge mutations — compute with-vs-without per-suite deltas through `evaluate_skill_efficacy`. **Gate**: the negative-delta guard flags ≥1 real per-suite regression that aggregate-only acceptance would have admitted (the SkillsBench 16/84 pattern), AND accepted edits show no held-out-split regression beyond threshold. EV-10b surrogate scoring adds a verifier-LLM assertion-authoring pass (cross-family, inference). **Sequencing**: does NOT fold into the *current* J6 soak — wiring the accept-path requires an autopilot restart and would contaminate the certified-topology (`df373c79cc4af06f`) Pareto measurement (the sidecar-deferral exists to avoid exactly that). It should **co-wire with J11/BSV-2 at the next AR-3 restart** (both modify the same accept-path / eval-trust-boundary, so one restart serves both), **behind independent feature flags** so the two changes are attributable (closure-inflation / one-change discipline). **Flag-isolation VERIFIED 2026-05-27**: both gates are currently unwired sidecars (`behavior_signature`/`mutation_ledger` not imported in `scripts/autopilot/`; `skill_efficacy.py` stdlib-only) → no co-mingling today, no flag yet for either. Reserved two collision-free default-off env flags (checked against src/+scripts/): EV-10a → `AUTOPILOT_SKILL_EFFICACY_GATE`, BSV-2 → `AUTOPILOT_BSV2_ACCEPT_GATE`. Contract pinned in `scripts/autopilot/skill_efficacy.py` docstring. The only residual is the flag-*wrap* itself, which is part of the restart-gated wiring. Stage-2 validation then **rides that fresh soak** (flag-on vs flag-off trial windows) — it needs no dedicated isolated window (unlike Package I), since it is measured inside the autopilot loop. Source: [eval-tower-verification.md](eval-tower-verification.md) EV-10 + [meta-harness-optimization.md](meta-harness-optimization.md) § 2026-05-27. |

**Run-command note**: each adapter is registered as a named suite, so existing seeding/eval harnesses pick them up by suite name (`scoring_verifiers`, `tulving_episodic`). K-RAG-1 + K-ROPE-1 are standalone scripts (env-var-swept / `--context-length` per cell). **K-SKILL-1 is the exception** — it is not a suite run; it gates on the AR-3-restart wiring first (no-artifact arm + accept-path hook), then a paired-mutation A/B, so it cannot be picked up turnkey like the others. Per `feedback_speed_verify_via_llama_bench` + `feedback_no_concurrent_inference`: the user/campaign runs these manually with per-run approval — code is prepared, not executed.

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

---

## Cross-Role Contention + Placement (shape-keyed-contention-gating) — TRACKING [added 2026-05-30]

Sibling to **Package J** (within-role placement). Where Package J makes *one role* fan out across disjoint quarters, this work (`handoffs/active/shape-keyed-contention-gating.md`) makes *different roles* co-reside on disjoint shapes — closing the seeder's non-work-conserving gap (heavy node-half runs while q2/q3 sit idle).

**State:** Part A + A-1 CODE-COMPLETE, and Step 1 is staged in `orchestrator_stack.py` to default `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` on the next API reload. Part B is now end-to-end code-complete/default-off: dispatch passes real `candidate_topology_idx` values to the authoritative shape-aware gate when both flags are armed, with 146 affected tests green. Live traffic is unchanged because `ORCHESTRATOR_SHAPE_AWARE_CONTENTION` is off and the API was not reloaded. C remains prep only (`select_backfill_candidate`); heavy veto/barrier/pressure-skip are untouched.

**⏳ ACTION ON J6 END (do immediately):** the live-observation gate must run *while the stack is quiesced*, in a flag-on bracket, then either revert or deliberately mark an epoch before resuming. Sequence: autopilot clears → reload orchestrator so the staged `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` default is live → verify `/proc/<api_pid>/environ` → run multi-role fan-out probe (extend `scripts/benchmark/placement_fanout_probe.py` to a multi-role burst) → confirm region-lock dashboard shows heavy+light on disjoint shapes + queue-on-overlap → bracket `ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1` smoke for Step 2 (disjoint quarters admit; true q-overlaps queue). Adopting flag-on for production traffic is a SEPARATE decision requiring a `mark_epoch`/archive reset, not a silent resume.

**Cross-ref:** Package J (`within-role-placement-state-machine.md`) J7 is the within-role analogue (`ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1` rollout); this is the cross-role layer above it.
