# Memory-Augmented Systems

**Category**: `memory_augmented`
**Confidence**: verified
**Last compiled**: 2026-08-08
**Sources**: 35+ documents (2 deep-dives, 28+ intake entries, active handoffs, progress logs, K-MEM/Tulving measurement context, and the 2026-06-28 W4/W6 reboot-readiness checkpoint)

## Compiled Update — 2026-08-08: memory operations need provenance, calibrated verification, and a no-memory control

**Confidence: verified for artifact scope and local design routing; external for reported benchmark gains.**

The new memory sources agree on a useful operation vocabulary but not on evidence quality. VerMem's
paper defines versioned `ADD|UPDATE|DELETE|RETRIEVE|FILTER|SELECT_EPISODE|SUMMARIZE|NOOP` actions and
reports a material semantic-verifier ablation, while its released repository supplies only structural
and lexical rules—not the load-bearing DeepSeek semantic judges or a complete durable runtime. Mem0
adds practical local scoping, conflict retrieval, mutation history, and manual update/delete, but its
current default extraction path has drifted to ADD-only and the paper's efficiency figures omit memory
construction/write cost. Memory-R1 usefully separates a manager from an answer-time distiller and
applies downstream outcome credit, but releases no training implementation and shows non-uniform gains.

Two negative controls bound the design. Cognitive Workspace's apparent reuse advantage is structurally
forced by a zeroed RAG control, a truthy match predicate, cumulative counter leakage, and dependent
statistics; it is a regression fixture, not evidence for a memory system. ActiveMem's parallel gist
workers are worth comparing, but its memory is task-local, the runtime is unreleased, and raw content
can become unrecoverable unless every gist retains a resolvable evidence pointer.

The EPYC design consequence is a default-inert shadow layer over immutable raw events: append-only
operation envelopes, source references, actor/scope, before/after versions, rollback links, tombstones
that are explicitly distinct from physical erasure, separately calibrated structural and semantic
verification, and independent answer-time distillation. Evaluation must include no-memory/full-context,
raw append-log retrieval, Context-Folding, shadow mutation proposals, and gist extraction under
restart, cross-session, conflict, staleness, poisoning, deletion, rollback, and raw-source recovery.

### Source References

- [Unified Trace / Memory Service](../handoffs/active/unified-trace-memory-service.md) — UTM-V1…V6 shadow schema, verifier, distiller, credit, and lifecycle matrix
- [Context-Folding](../handoffs/active/context-folding-progressive.md) — CF-AM-1 matched parallel-gist versus folding/raw-evidence comparison
- [REPL Session Memory](../handoffs/active/repl-session-memory-maturity.md) — durable session ownership and uncertain-side-effect recovery requirements
- Intakes 1008/1015, 1017/1018, and 1022/1023 in [the research index](../research/intake_index.yaml) — Cognitive Workspace, ActiveMem, VerMem, Mem0, and Memory-R1 claim ledgers

## Compiled Update — 2026-08-03: the useful half of the memory literature does not need gradients

**Confidence: inferred — single-ablation results on small models, no CIs, no seed variance reported.
Recorded as a strong lead, not a settled result.**

The most stack-relevant number in this cluster sits in an ablation table that the paper citing it never
reports: on a 3B model, **principle distillation + retrieval with RL DISABLED scores 0.357, beating the
same system's RL-only arm at 0.325**, and reaching **93.5% of the full system's 0.382**. The citing
paper presents that work as its exhibit for "memory + RL is harmful"; the work's own ablation shows its
memory machinery *without gradients* outperforming pure RL.

**Why this matters here specifically**: we cannot train. A literature whose headline results all require
RL is one we can read but not use. This result says most of the value is on our side of the line.

Two further portables, both zero-training and both computable over traces we already have:

- **A redundancy metric over stored reflections** (`SequenceMatcher ≥ 0.85`) — pure log post-processing,
  no inference cost, and **computable retroactively** rather than needing new capture.
- **Programmatic feedback extraction**: parse tool output for the concrete failure fact instead of asking
  the model to self-diagnose. Measured effect on entity grounding: **0/121 → 134/156 (86%)** correct
  target-object mentions. The *mechanism* and the *metric* transfer; the rates are largely a weak-model
  artifact at n=2 environments and do not.

### Three methodological traps this cluster illustrates

1. **A "(reproduced)" baseline can reproduce nothing.** One paper's reported baseline for a cited system
   is labelled reproduced — but that system **never evaluates on those benchmarks at all**; the metric
   name appears zero times in it. There was no original to diverge from, and the label asserted fidelity
   to something that does not exist. *Check that the original number exists before treating a delta from
   it as a finding.*
2. **Reported decimals can rule out the stated denominator.** No common per-category denominator ≤200
   reproduces one paper's six reported cells; the minimum consistent denominators imply ~2,045 episode
   outcomes. **Recomputing the implied denominator from published decimals is a cheap integrity check**
   that needs no access to anything.
3. **The arm you want to port may be the weakest effect in the paper.** The test-time memory effect —
   exactly the gradient-free piece a port would target — is **+2.2 pp at z ≈ 1.94 on one seed with no
   CI**, while the effects that survive sampling noise are the training-time ones we cannot use. *Check
   the significance of the specific arm you intend to adopt, not the paper's headline.*


## Summary

Memory-augmented systems are the learning infrastructure that allows the EPYC orchestrator to improve across requests and sessions. The project implements a 3-store memory architecture: an episodic store (FAISS+SQLite) that records per-request outcomes with Q-value weighted retrieval for routing decisions, a strategy store (FAISS+SQLite) that holds LLM-distilled insights from autopilot trials for species proposal guidance, and a skill bank that accumulates reusable task-solving patterns with Q-value weighted selection. These stores are backed by MemRL -- a reinforcement learning system that trains routing Q-values from 3-way evaluation comparisons, updates reward signals based on task outcomes, and uses MLP+GAT classifiers trained on accumulated memories once 500+ entries exist.

The deep-dive research reveals a fundamental design tension in agent memory systems. MemAgent (intake-156, ByteDance/Tsinghua) demonstrates that RL-trained compaction can maintain 70-80% accuracy across 437.5x context extrapolation (8K training to 3.5M test) using a fixed 1,024-token memory buffer with complete overwrite at each segment. The key mechanism is Multi-Conversation DAPO training, where K segments produce K independent conversations but reward comes only from the final answer, with advantage broadcast uniformly. The 14B MemAgent beats 32B QwenLong-L1 at all context lengths, proving that learned memory management can substitute for raw context capacity. However, the sequential processing bottleneck (K inference calls, no parallelism) makes direct adoption infeasible on CPU: a 100K document would take ~24 minutes at EPYC 9655's inference speed, and 3.5M would take ~14 hours.

The broader research landscape (15 intake entries) maps a rich design space for agent memory. The foundational tension is between raw storage (lossless but inert -- all messages verbatim, no curation) and derived storage (compact but drifting -- LLM extracts and summarizes, introducing information loss and semantic drift). Neither works alone. The nine-axis design space from intake-316 provides the analytical framework: write triggers (every turn vs threshold vs explicit), storage backend (flat file vs SQLite vs vector DB vs knowledge graph), retrieval mode (always-injected vs hook-driven vs tool-driven), curation policy (append-only vs LLM-curated vs rule-based), forgetting policy (none vs recency vs importance-weighted), and four more axes. The EPYC system occupies a distinctive position: derived storage with RL-trained curation (Q-value weighting), FAISS vector retrieval with keyword fallback, importance-weighted forgetting via Q-value decay, and hook-driven injection at routing and proposal time.

Two high-relevance entries point toward concrete next steps. MemPalace (intake-326) achieves 96.6% LongMemEval R@5 -- the highest published result for zero-cost offline memory -- using a hierarchical palace architecture (wings for projects/people, rooms for topics, drawers for raw verbatim content) with ChromaDB semantic search on unsummarized text. The key finding: metadata filtering by wing/room provides 34% retrieval improvement over flat search, suggesting that the EPYC strategy store would benefit from hierarchical organization (by species, by optimization target, by model tier) rather than flat FAISS search. Lossless Claw (intake-140) and CMV (intake-141) both demonstrate DAG-based context management that preserves all messages verbatim while providing compact active contexts through hierarchical summarization -- a pattern directly applicable to the orchestrator's context folding pipeline.

The connection between memory and the autopilot is especially significant. Before the strategy store and Evolution Manager were implemented, species operated statelessly: Seeder never read past trial outcomes, NumericSwarm used only Optuna's internal state, PromptForge built mutation prompts without past mutation outcomes, and StructuralLab did not consult experiment history. The experiment journal existed but was passive -- consumed only by the Controller's prompt template as flat text (last 20 entries). EvoScientist's finding that memory-augmented proposals dramatically outperform memoryless ones (ablation: -45.83 gap without evolution) motivated the strategy store implementation. Species now retrieve relevant past insights before making proposals via semantic search against the strategy store.

## Key Findings

### New Finding (2026-07-28) — An internally-consistent store can be completely wrong; the fix is a standing assertion, not a repair

- **The 22-day lesson is codified: nothing checked the store, so it rotted invisibly.** `check_episodic_integrity.py` now asserts the four properties the incident actually violated — index/id_map sync, `embedding_idx` round-trip, vector diversity per **distinct objective** (a row denominator flags healthy benchmark replay as collapse), and the decisive **semantic self-match** (re-embed a row's own objective, cosine against its stored vector — the one check internal consistency cannot fake: 0.9956 healthy vs 0.5505 during the incident). Wired into `health_check.sh` §6 (metadata-only, 0.23 s) and AutoPilot `cmd_start` as a fail-closed gate that retries through an embedder boot window then refuses. Validated against deliberately-broken stores — injected mis-resolution reproduces the incident signature (cosine 0.4372). Sources: [episodic-memory-integrity.md](../handoffs/active/episodic-memory-integrity.md) M-17, [progress 2026-07-28](../progress/2026-07/2026-07-28.md). `verified`
- **Fail-open embedder fallbacks are a store-poisoning class, and the guard belongs at the index boundary.** `use_fallback=True` is the default everywhere and every live site builds a bare `TaskEmbedder()`, so a BGE outage silently writes SHA-256 pseudo-vectors — measured 89.0% all-zero (float32 norm overflows to inf), 2.8% NaN (FAISS scores −inf, permanently unretrievable), 8.1% well-formed-but-meaningless. The well-formed slice defeats every metadata check and its only detector needed the embedders that were down. Guarantee now sits at `FAISSEmbeddingStore.add()` — the single function every vector passes to reach ANY index (episodic, SkillBank, StrategyStore) — plus exact hash-fallback detection at text-bearing chokepoints (a 0.99-cosine detector had a 45% false-positive rate; exact comparison has 0 over 3,000 live vectors). Sources: [episodic-memory-integrity.md](../handoffs/active/episodic-memory-integrity.md) M-17e-i/M-18. `verified`
- **The `distill_skillbank` autopilot surface never worked once** — wrong constructor kwargs plus a sync call of async `run()` meant every invocation since the action existed returned `{"status": "error"}`; separately its embed call used a nonexistent method, so even a working pipeline would have stored every skill unindexed, and it embedded a different text convention from what retrieval queries. Repaired, unified on one canonical `skill_embedding_text()`, smoke-tested zero-inference (MockTeacher: distill → dedup → store → indexed). Teacher policy: Claude CLI autonomous default, one-env-line shift to local. First real run is gated on fresh trajectories (readiness probe in the handoff; note **0 of 58,655 rows carry a `work` payload** — write sites never pass it, filed M-11a2). Sources: [episodic-memory-integrity.md](../handoffs/active/episodic-memory-integrity.md) M-11a. `verified`

### New Finding (2026-07-29) — Semantic integrity must be live, and health status must expose absent declared dependencies

- **The decisive semantic assertion is now a live, fail-closed health contract rather than a test-only repair.** The health path runs with the repository interpreter and requires a real semantic self-match; it cannot silently skip the check because an unrelated shell lacks dependencies. External Q-score updates also reject fallback/degenerate embeddings and require an exact normalized `(objective, task_type, action)` identity after FAISS candidate lookup. The live post-reload check reported `ntotal=id_map=58,749`, desync `0`, mapping round-trip `500/500`, and mean self-match cosine **0.9824** over 8 samples. This is strong integrity evidence, not a retrieval-value claim; the memory-on/off A/B remains open. Sources: [episodic-memory-integrity.md](../handoffs/active/episodic-memory-integrity.md) M-17j, [autopilot decision-plane audit](../handoffs/active/autopilot-decision-plane-audit-2026-07-22.md), and [2026-07-29 progress](../progress/2026-07/2026-07-29.md). `verified`
- **A health view that omits a declared but state-missing service is a false negative.** The stack status now reconciles active manifest-declared non-optional services against launch state and emits `state-missing` with its observed healthy/unavailable condition; inactive warm roles remain excluded deliberately. Optional auxiliary services retain an explicit `unavailable_optional` row. This closes the audit's service-disappearance residual without claiming that an unavailable service is healthy or changing the production lineup. Sources: [episodic-memory-integrity.md](../handoffs/active/episodic-memory-integrity.md) M-17k, [2026-07-29 progress](../progress/2026-07/2026-07-29.md), and [Inference Serving](inference-serving.md). `verified`


### New Finding (2026-06-21) — Evidence-pruned reconstruction (MRAgent) is a second instance of the parked two-pass-retrieval pattern, not a new workstream

- **MRAgent's "active reconstruction" is the same evidence-conditioned retrieval family already parked on the KB-RAG handoff, approached from the pruning side.** MRAgent (intake-698, arXiv:2606.06036, Ji/Li/Hooi) replaces static "retrieve-then-reason" with a Cue-Tag-Content associative memory graph traversed by interleaving LLM reasoning with retrieval — iteratively exploring and pruning retrieval paths on intermediate evidence rather than fetching a flat top-k. This is the same self-correcting two-pass pattern recorded from agent-oss (intake-610): "evidence incomplete → gap-query → re-retrieve at a lower threshold," but realized as path-pruning instead of re-retrieval. It is logged as a **comparative datapoint** against `internal-kb-rag.md`'s parked note, and stays **deferred-pending-a-consumer-that-emits-an-incompleteness-signal** — no new K-track, no plan delta.
- **MRAgent's only transferable lever is token-cost discipline, not its accuracy headline.** Reported token consumption is ~118k vs 245k–3.3M for baselines, with LoCoMo/LongMemEval gains — but all numbers are **cloud-LLM-bound (Gemini-2.5-Flash / Claude-Sonnet-4.5) with NO CPU/local/quantized results**, and MRAgent actually **loses to Mem0 on LoCoMo multi-hop F1 (43.69 vs 45.17)**. Under EPYC's token-budget constraints, the reusable idea is evidence-pruned traversal's cost behavior; the accuracy figures are observations (per MEASUREMENT.md), never decision-gating. Routing note: do NOT attach this to `delta-mem-reproduction.md` (its open gates are GPU-bound accuracy reproduction, not retrieval token-cost). Sources: [internal-kb-rag.md](../handoffs/active/internal-kb-rag.md) (2026-06-20 MRAgent RIU), [intake-698](https://arxiv.org/abs/2606.06036). `external (preprint, cloud-bound)`

### New Finding (2026-06-21) — DecentMem dual-pool structure transfers; its LLM-judge reweighting conflicts with autopilot policy

- **Only the decentralized dual-pool STRUCTURE of DecentMem maps onto the autopilot strategy store — the per-stage LLM-judge reweighting must be dropped.** DecentMem (intake-715, arXiv:2605.22721, Hao/Long/Zhao) gives each agent its own dual-pool memory — an *exploitation* pool of consolidated past trajectories plus an *exploration* pool of LLM-generated candidates for unseen contexts — reweighted online by stage-wise LLM-as-a-judge feedback, with a claimed O(log T) cumulative regret bound matching the stochastic-bandit lower bound. The exploitation/exploration split is a clean comparative datapoint for the `autopilot-continuous-optimization.md` strategy_store (the real per-agent evolutionary-memory home), alongside queued HCC tiered-memory + staleness work — but it is **not new scope**.
- **DecentMem's judge-reweighting collides head-on with two standing autopilot decisions.** The per-stage LLM-as-judge reweighting conflicts with autopilot **AP-27 ("state matching, not LLM-as-judge")** and with the 2026-06-12 **P17.BT-4 KILL of judge-model scoring on cost grounds** — and on CPU-only EPYC every extra per-stage judge call is a real token/latency cost. So the dual-pool structure transfers; the reweighting mechanism does not. Confidence is low: no released code, results use cloud-favorable small backbones (Qwen3 4B-14B, Gemma4 E2B/E4B) on AutoGen/DyLAN/AgentNet frameworks we do not run, so the regret bound and +23.8%/+52.5% accuracy / 49% token-reduction claims are hypotheses pending reproduction. The shipped B1 user-modeling (M.1-Prefix) already occupies the slot delta-mem aims to replace; `unified-trace-memory-service` is read-only by charter and is NOT an exploitation-pool source. Sources: [intake-715](https://arxiv.org/abs/2605.22721), [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md). `external (preprint, no code)`

### New Finding (2026-06-20) — K-MEM Tulving baseline corrected to mixed recall with weak chronology

- **The Tulving episodic-memory benchmark is complete for the first `ingest_long_context` baseline, but it is not a memory-routing promotion signal.** Research run `20260619_141212` used production/default GGUF expert settings (`--skip-moe-reduction`); raw artifacts were packaged in `epyc-inference-research` commit `b6edc64`, and corrected score artifacts landed in `9e63af0` after fixing Tulving ground-truth parsing. The corrected scorer covered `456/456` questions with no missing ground truth, avg F1 `0.4309`, Simple Recall `0.5530`, Chronological Awareness `0.1593`, and avg decode `17.27 t/s`; the benchmark log ended `448 completed, 8 skipped, 0 errors` because the corrected resume reused the first 8 rows. Failure shape: lexical entity/time/location recall is usable, event-content/full-detail retrieval and chronology are weak, and zero-answer hallucination checks fail. This clears the throughput-sensitive K-MEM lane and creates a targeted follow-up task, not a change to episodic retrieval/write behavior. Sources: [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md), [research-evaluation-index.md](../handoffs/active/research-evaluation-index.md), [progress 2026-06-20](../progress/2026-06/2026-06-20.md).

### New Finding (2026-06-28) — Sequential evidence is cutover-ready but still default-off

- **Sequential verdict authority has cleared the W4/W6 evidence-volume gates, but the authority flip is still a deliberate restart-boundary decision.** The W4/W6 path journals per-question sequential evidence, failed-trial seq blocks, and action-local seq gate checks behind `AUTOPILOT_SEQ_VERDICT`; as of the 2026-06-28T21:35Z reboot wrap-up, strict readiness is green with sequential trusted vectors `193 / 120`, seq shadow rows `116 / 30`, W6 trusted audited rows `32 / 30`, no W6 gaming alarm, and archive alignment through journal trial `1050`. Baseline fold readiness is also green, but `baseline_authority_enabled=false`, so future agents should rerun strict readiness after reboot and only then make the explicit authority cutover decision. Sources: [evidence-plane-ledger-and-sequential-verdicts.md](../handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md), [evidence-plane-instrument-repair.md](../handoffs/active/evidence-plane-instrument-repair.md), [progress 2026-06-28](../progress/2026-06/2026-06-28.md).

### New Finding (2026-07-05) — Exact episodic FAISS health is now observable and current

- **The episodic mirror health check now reports the exact indexed-memory invariant, not just a coarse routing count.** Orchestrator `a0148edd` makes the indexed FAISS diagnostic exact: `orchestrator_stack.py status` now reports `526,729/526,729` indexed vectors, matching `id_map.npy` and `reembedded.npz`, with `100.0%` live overlap and `0` missing/stale IDs. The same repair path sits on top of the stale-snapshot hardening from `8af5fa6e` and the earlier lock-aware FAISS/id-map protections, so the live status is a real health signal rather than a best-effort estimate. Sources: [progress 2026-07-05](../progress/2026-07/2026-07-05.md), [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md).
- **The current AutoPilot state is healthy but still W8-bound, so memory repair is not the remaining blocker.** The same 2026-07-05 repair session relaunched AutoPilot on the canonical Fable launcher as PID `2370903`; phase health reported `trial 1168`, `planner_invoke`, `code_stale=false`, and `blockers []`. The handoff-level current state now treats W8 candidate generation as the live blocker, not episodic-memory corruption. Sources: [progress 2026-07-05](../progress/2026-07/2026-07-05.md), [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md).

### New Finding (2026-06-19) — Strategy compression now honors folded-journal quarantine

- **Derived strategy promotion now reads strategy rows through the same evidence quarantine used by planner retrieval and mutation context.** The first gap was `StructuralLab.mdl_compress_strategies()`, which selected raw `StrategyStore` rows directly; orchestrator commit `b5e71f8` routes MDL compression through `StrategyStore.strategy_rows_for_compression()`. The follow-up gap was `KnowledgeDistiller` raw-to-pattern and pattern-to-convention promotion; orchestrator commit `c9871a8` adds `StrategyStore.strategy_entries_for_distillation()` and lets distillation receive a folded journal or explicit exclusion set. Refuted evidence can no longer be reintroduced through derived compression or distillation patterns when the caller supplies journal context. Remaining W6 work is final W1 ledger-keyed strategy-view integration. Sources: [evidence-plane-event-sourcing-and-narrative.md](../handoffs/active/evidence-plane-event-sourcing-and-narrative.md), [progress 2026-06-19](../progress/2026-06/2026-06-19.md).

### New Finding (2026-06-03) — FAISS episodic-memory durability repair

- **FAISS-backed episodic memory must treat index assignment as a cross-process critical section, not a local write-behind detail.** The 2026-06-03 repair found `episodic.db` current while `reembedded.npz`, `embeddings.faiss`, and `id_map.npy` were stale by six days; DB rows had many duplicate `embedding_idx` values because multiple long-lived `EpisodicStore` instances assigned from stale local FAISS `ntotal` state. The fix reloads the durable FAISS/id-map under an exclusive file lock, assigns the next vector index, saves immediately, then writes SQLite metadata. Rebuilding with temporary BGE servers restored routing-memory coverage from 31.9% to 93.4% (163,444 FAISS vectors / IDs for 174,932 routing memories). [2026-06-03 progress log](../progress/2026-06/2026-06-03.md) `verified`

- **RAM drift from llama-server residency is observability/recycle territory, not page-cache remediation.** The same session found day-over-day RAM growth dominated by llama-server private-dirty KV/context arenas and mlocked model pages. `drop_caches` cannot reclaim that class of memory. Host-health telemetry now surfaces llama-server PSS, Private_Dirty, Locked, and system Mlocked as advisory signals to the planner; automatic role-aware idle server recycling remains the next implementation step. [2026-06-03 progress log](../progress/2026-06/2026-06-03.md) `verified`

### New Finding (2026-05-25) — Track A measured outcome

- **n-gram-augmented MoE inference is viable on CPU at production-relevant rates, but the only available open-weight checkpoint (LongCat-Flash-Lite Q4_K_M) is dominated by our deployed worker on both speed and quality.** Three-way head-to-head on EPYC 9655: LongCat-Lite at 37.08 t/s decode and 53.8% on the 39-question sentinel suite vs gemma4-26B-A4B Q4_K_M MTP (the deployed worker_general) at ~76.5 t/s decode and 66.7% sentinel. Suite-level: LongCat loses math 0/6 vs 4/6 (genuine reasoning failure, confirmed by re-running at 4× token budget — `4^3 = 16` arithmetic error mid-chain despite Meituan's published MATH500 = 96.8%); wins hotpotqa 3/4 vs 1/4 (the n-gram-augmented input embedding plausibly helping literal multi-hop retrieval); ties at agentic 1/3 (both weak, VitaBench 7.0 concern validated for the family). The 31.4B-param n-gram embedding table fits fully resident in our 1.1 TB DDR5 with room to spare; the bandwidth math from the CXL follow-up paper (arxiv:2603.10087, ~10 KB/token at FP8 = <0.2% of DDR5 aggregate) holds in practice. **Track A closed as NEGATIVE** in `engram-conditional-memory.md`. Track B (frozen-backbone retrofit research bet) is unaffected — different architecture (paper-faithful, not LongCat-simplified-input-only) and different optimization (training own model, not adopting an existing checkpoint). [longcat-flash-lite-engram-cpu-poc.md](../research/deep-dives/longcat-flash-lite-engram-cpu-poc.md) `verified`

### New Finding (2026-05-24)

- **Parametric n-gram memory (Engram) is an architectural axis orthogonal to MoE/KV/spec-dec that targets exactly our hardware shape.** DeepSeek + Peking University (arxiv:2601.07372, intake-599) propose a deterministic-lookup memory module where 2-3-token suffix n-grams are hashed via multiplicative-XOR (K=8 heads per order, distinct prime moduli) and the retrieved vector is added through a scalar sigmoid gate + zero-init depthwise causal Conv1D at early Transformer layers (best ablation: [2, 6] of 30). The "Sparsity Allocation Law" says 25% of sparse-param budget → Engram, 75% → MoE under iso-FLOPs. Engram-27B reports +5.0 BBH, +3.7 ARC-C, +2.4 MATH, NIAH 84.2 → 97. The CXL follow-up paper (arxiv:2603.10087, intake-600) gives the only published bandwidth figure: **~10 KB/token total at FP8, 0.7 GB/s at 70k tok/s — <0.2% of EPYC 9655's DDR5 aggregate**. The technique is a near-perfect fit for our 1.1 TB single-socket regime but is **architectural, not a runtime knob** — the paper releases code-as-demo only (no weights, no training loop, no offload kernels), and DeepSeek V4 production line does NOT ship Engram per V4 architecture writeups (research-track only). [engram-conditional-memory.md](../handoffs/active/engram-conditional-memory.md) `verified`

- **LongCat-Flash-Lite (Meituan) is the only deployed Engram-family open-weight checkpoint but it is architecturally simpler than the paper.** 68.5B total / 2.9-4.5B active, ~31.4B in n-gram tables, MIT-licensed. Critical deviation from paper Engram: injection at the input embedding only (NOT per-layer mid-stream), no gate, no conv, just additive + /13 normalization. Polynomial rolling hash (not multiplicative-XOR), 4 hash heads per order (not 8), n ∈ {2,3,4} (paper {2,3}), custom 131k tokenizer with no canonicalization. A working GGUF (`InquiringMinds-AI/LongCat-Flash-Lite-GGUF` Q4_K_M = 37.4 GB) and a non-upstreamable llama.cpp fork (Claude-Code-generated, violates ggml-org AI policy; fine for local research) already exist; ik_llama.cpp has zero LongCat code. Upstream PRs #19167 / #19182 stalled in draft for 4+ months. **No CPU performance number for LongCat exists anywhere — we would be the first benchmarkers.** A successful LongCat CPU POC validates the n-gram-lookup family, not the paper's specific gating-and-conv architecture. [intake-502, intake-504, engram-conditional-memory.md](../handoffs/active/engram-conditional-memory.md) `verified`

- **Frozen-backbone retrofit of paper-faithful Engram is a research bet, not a port.** The paper provides NO direct evidence for retrofit feasibility — its closest result (§6.3 post-hoc Engram suppression) shows the co-trained backbone has learned to *delegate* to Engram, which means the frozen-backbone setting has structurally less headroom. Zero-init conv is gradient-compatible (no backbone shock at step 0), which is the architectural reason to hope. The deepseek-ai/Engram repo is 422 LoC single-file demo: module clean (~250 LoC of substantive logic, Apache-2.0, vendorable), but training loop / dataloader / freeze hooks / KV-cache / offload all absent — maintainer disengaged after day 3 (2026-01-14), 20 issues open with zero answers. The DeepSeek-V3 vocab canonicalization map P (~23% reduction) is also not released and must be rebuilt for any non-DeepSeek tokenizer. Estimated effort: ~400 LoC new glue + ~280 LoC vendored, single-week single-GPU proxy spike. Phase 0 derisk gate: frozen-Engram must recover ≥30% of co-trained-Engram gain on a 1.5B proxy (SmolLM-1.7B or TinyLlama) before committing GPU-weeks to Qwen3.6 or gemma4 surgery. [engram-conditional-memory.md](../handoffs/active/engram-conditional-memory.md) `verified`

### New Finding (2026-04-21)

- **Memory Transfer Learning's four-tier abstraction (Trajectory → Workflow → Summary → Insight) is a concrete template for EPYC's strategy store.** MTL (arxiv:2604.14004, intake-425) empirically shows cross-domain memory transfer gains +3.7% on coding benchmarks, but **only when stored at the Insight level** (title + description + generalizable content, no task-specific details). Concrete traces induce negative transfer. Notable size-vs-quality result: MTL's 431 curated Insights beat AgentKB's 5,899 raw memories by +1.7% — curated abstraction beats raw accumulation. Simple embedding retrieval (cosine on `text-embedding-3-small`) outperforms LLM reranking, validating EPYC's FAISS-based strategy_store. The negative transfer taxonomy (domain-mismatched anchoring, false validation confidence, misapplied best-practice transfer) is directly actionable for PromptForge safety gates. Worth noting: the "Memory Transplants" ICLR 2026 Workshop caveat — architecture transfer is system-dependent and weaker solvers benefit most, so the +3.7% may not scale to stronger base models. [autopilot-continuous-optimization.md 2026-04-21 update] `verified`
- **Strategy-store configuration epoch hashes now follow the live worker prompt file.** `orchestration/repl_memory/strategy_store.py` fingerprints `worker_general.md` instead of the legacy worker prompt path, so AP-28 validity checks stay aligned with the canonical worker prompt used elsewhere in the stack. Sources: [progress 2026-06-15](../progress/2026-06/2026-06-15.md), [Model Stack Single-Source Update Pipeline](../handoffs/active/model-stack-single-source-update-pipeline.md), `orchestration/repl_memory/strategy_store.py`.

- **RL-trained compaction can maintain near-flat accuracy across 437.5x context extrapolation.** MemAgent's 14B model achieves 84.4% at 28K and 78.1% at 3.5M on RULER-HotpotQA, with only 5.47pp degradation. All baselines (QwenLong-L1-32B, Qwen2.5-14B-1M, DS-R1-Distill-32B) collapse beyond 224K. The mechanism is surprisingly simple: a fixed 1,024-token memory buffer completely overwritten at each 5,000-token segment, trained with Multi-Conversation DAPO where reward from the final answer broadcasts uniformly across all segment conversations. However, the approach has critical failure modes: irreversible information loss from overwrite, memory capacity ceiling at 1,024 tokens, single-question bias (must reprocess entire document for a different query), and no streaming or backtracking. [memagent-rl-memory.md](../research/deep-dives/memagent-rl-memory.md)

- **MemAgent is not viable for direct CPU inference adoption but its concepts are extractable.** Per-segment overhead on EPYC 9655 (Qwen2.5-14B at Q4_K_M, ~14 t/s) is ~73 seconds per segment. A 100K document (20 segments) takes ~24 minutes; 3.5M (700 segments) takes ~14 hours. The sequential chain allows no parallelism. For the orchestrator's 32K-128K native windows, YaRN RoPE scaling is the right tool. MemAgent concepts worth extracting: RL-trained compaction quality (train compaction model where reward = downstream task success), fixed-size memory buffer (target fixed token budget rather than percentage-based compaction), question-guided compaction (guide by relevance when task type is known), and multi-conversation advantage broadcasting (applicable to MemRL routing training). [memagent-rl-memory.md](../research/deep-dives/memagent-rl-memory.md)

- **The raw vs derived storage tension is the foundational design question.** Raw storage preserves everything but retrieval over inert text is unreliable. Derived storage is compact and semantically organized but drifts from ground truth as LLM extraction introduces errors. MemPalace (intake-326) sidesteps this by storing raw verbatim content in "drawers" while organizing via semantic metadata in a hierarchical structure -- achieving 96.6% LongMemEval R@5, the highest published zero-cost offline result. Mem0 (intake-346, $24M funded) achieves ~85% with derived LLM extraction. The EPYC system uses derived storage (Q-value weighted, LLM-distilled strategy insights) which risks drift but enables compact retrieval. [intake-316, intake-326, intake-346]

- **Hierarchical memory organization provides 34% retrieval improvement over flat search.** MemPalace's palace architecture (wings/rooms/drawers) with metadata filtering by wing/room demonstrates that hierarchical organization is not just organizational convenience -- it materially improves retrieval accuracy. The EPYC strategy store currently uses flat FAISS search. Adding hierarchical organization (by species, by optimization target, by model tier) as metadata filters would improve retrieval relevance when species query for past insights. [intake-326](https://github.com/MemPalace/mempalace)

- **DAG-based context management can be structurally lossless.** Lossless Claw (intake-140) implements an immutable store (all messages verbatim) plus an active context (summaries + recent messages) with deterministic three-level compaction escalation. CMV (intake-141) extends this with version-controlled state using DAG structure -- snapshot/branch/trim primitives and three-pass structurally lossless trimming that removes mechanical overhead while preserving all user/assistant content. Both are directly applicable to the orchestrator's context folding pipeline, which currently uses summarization that loses information. [intake-140, intake-141]

- **Agent-native memory (LLM as curator) eliminates external infrastructure dependency.** ByteRover (intake-267) uses the LLM itself to curate, structure, and retrieve knowledge through a Hierarchical Context Tree (Domain to Topic to Subtopic to Entry) with importance scoring and recency decay. No external vector DB or graph DB required. While less scalable than FAISS-backed stores, this pattern could be useful for per-session working memory where the LLM maintains a structured scratchpad of current task state. [intake-267](https://arxiv.org/abs/2604.01599)

- **In-context RL can internalize skills into model parameters.** Skill0 (intake-261) presents the first RL framework where agents internalize external skills (documentation, examples) into model weights during training, then operate without skill access at inference. The Helpfulness-Driven Dynamic Curriculum adjusts skill exposure based on demonstrated competence. Applicable to the orchestrator's SkillBank: if skills could be internalized via fine-tuning, the SkillBank's context overhead would be eliminated. Blocked on GPU access for training. [intake-261](https://arxiv.org/abs/2604.02268)

- **Optical self-compression is a novel approach to agent history management.** AgentOCR (intake-262) converts observation-action histories to compact rendered images for token reduction, with segment optical caching via hashable decomposition. While exotic, the compression quality threshold finding (c_t <= 1.2 = "free zone" where compression has no task impact) is applicable to the context folding pipeline's compaction quality evaluation. [intake-262](https://arxiv.org/abs/2601.04786)

- **The strategy store closes the "memoryless optimizer" gap.** Before implementation, the experiment journal was comprehensive but passive -- consumed only by the Controller as flat text. Seeder never read past trial outcomes, NumericSwarm used only Optuna internal state, PromptForge built mutation prompts without past outcomes. EvoScientist's ablation (-45.83 gap without evolution) motivated the strategy store. Species now retrieve relevant past insights before proposals, and the Evolution Manager distills knowledge every 5 trials. [evoscientist-multi-agent-evolution.md, autopilot-continuous-optimization.md]

- **Long-term conversational memory remains an unsolved problem.** The intake-316 survey identifies nine axes of the design space and concludes that no existing system adequately handles all of them. The most promising approaches combine raw and derived storage (MemPalace's drawers + rooms, EPYC's episodic + strategy stores). Forgetting policies are the least explored axis -- most systems either never forget or use simple recency, while the EPYC system uses Q-value decay which is more principled but still simplistic. [intake-316](https://x.com/chrysb/status/2043020014035570784)

## Actionable for EPYC

### High Priority
1. **Hierarchical strategy store organization** -- add species, optimization_target, and model_tier metadata to strategy store entries. Filter by metadata during retrieval (MemPalace finding: +34% retrieval accuracy). Low effort: metadata already partially present in JournalEntry; needs FAISS index partitioning or pre-filter.
2. **Fixed-size compaction target** -- replace percentage-based compaction trigger (current: 60% of context window) with a fixed token budget for the compacted summary (MemAgent insight). The target budget should vary by role: worker context is more expendable than architect context. Aligns with context-folding-progressive.md Phase 2.
3. **Question-guided compaction** -- when task type is known (coding, QA, review), guide compaction by task-type relevance rather than generic summarization. The difficulty_signal.py classifier already produces task type; feed this to the compaction model. [memagent-rl-memory.md]

### Medium Priority
4. **Hybrid retrieval for episodic/strategy stores** -- add BM25 lexical matching alongside FAISS semantic search, using Reciprocal Rank Fusion (k=60) as demonstrated by GitNexus. Improves retrieval for exact function names, model names, and configuration keys that semantic search handles poorly.
5. **RL-trained compaction quality** -- train a compaction model (could reuse existing worker_general Qwen2.5-7B) where the reward signal is downstream task success, not just summary quality. MemAgent's DAPO training achieves this for segment reading; the same principle applies to session compaction. Depends on having a fast evaluation loop.
6. **DAG-based session history** -- evaluate Lossless Claw/CMV patterns for the session_log. An immutable store (all turns verbatim, stored to disk) plus active context (summaries + recent turns) would enable lossless recovery of any prior turn while keeping the active context compact. Currently, compacted turns are lost.
7. **Strategy store cross-species fertilization** -- when a PromptForge insight is relevant to NumericSwarm's parameter search (e.g., "higher temperature helps creative tasks"), the strategy store should surface it. Currently, retrieval is species-scoped.

### Lower Priority
8. **Multi-conversation advantage broadcasting for MemRL** -- MemAgent's DAPO training pattern (broadcast final-answer reward uniformly across all segment conversations) is applicable to MemRL routing training, where a single task outcome should inform routing decisions at multiple points in the escalation chain.
9. **Per-session working memory via LLM curation** -- ByteRover's agent-native memory pattern (LLM maintains structured scratchpad) could replace or supplement the current in-memory TaskState for long-running REPL sessions. Lower priority because TaskState already serves this role.
10. **Skill internalization research** -- Skill0's ICRL framework for internalizing SkillBank entries into model weights via fine-tuning. Eliminates SkillBank context overhead at inference. Blocked on GPU access.

### Blocked
11. **RL-trained compaction** -- requires fast eval loop + GPU for training. Possible via RLVR formalization of eval tower (AP-27).
12. **Skill internalization** -- requires GPU for fine-tuning.

## Open Questions

- What is the optimal forgetting policy for the strategy store? Current Q-value decay is simple but may preserve outdated strategies that were optimal under old configurations. Should strategies have a "staleness" field that increases when the underlying config changes?
- How should the raw vs derived tension be resolved for episodic memory? Currently fully derived (Q-value weighted summaries). Adding a raw layer (verbatim request/response pairs) would enable post-hoc re-analysis but increases storage. MemPalace's approach (raw in drawers, derived in room structure) is a viable hybrid.
- Can MemAgent's multi-conversation DAPO training be adapted for MemRL routing training without GPU access? The training requires multiple conversation rollouts per sample, which is expensive on CPU.
- What is the right compaction quality threshold for "free zone" compression? AgentOCR (intake-262) found c_t <= 1.2 has no task impact. Does this transfer to text summarization, and does it vary by task type?
- Should the context folding pipeline adopt DAG-based management (Lossless Claw/CMV) or continue with the current summarization approach? DAGs preserve information but add complexity. The context-folding-progressive.md handoff explores multi-tier condensation as a middle ground.
- How does memory capacity interact with the Omega problem (REPL tools hurting accuracy)? If episodic memory provides better tool-use strategies from past successful sessions, it could guide more effective tool use rather than naive exploration.

## Related Categories

- [Agent Architecture](agent-architecture.md) -- memory stores are a core subsystem of the multi-agent orchestrator
- [Routing Intelligence](routing-intelligence.md) -- MemRL episodic memory provides Q-value signals that train routing decisions
- [Autonomous Research](autonomous-research.md) -- strategy store and Evolution Manager are the autopilot's learning infrastructure
- [Context Management](context-management.md) -- session compaction and context folding are the interface between memory and active context
- [Tool Implementation](tool-implementation.md) -- BM25+semantic hybrid search pattern applicable to memory retrieval

## Source References

- [MemAgent deep dive](../research/deep-dives/memagent-rl-memory.md) -- fixed-size buffer with complete overwrite, Multi-Conversation DAPO training, 437.5x extrapolation, O(N) complexity, CPU infeasibility analysis, extractable concepts (RL-trained compaction, fixed-size budget, question-guided compaction)
- [EvoScientist deep dive](../research/deep-dives/evoscientist-multi-agent-evolution.md) -- Evolution Manager's three knowledge distillation channels, strategy store motivation, ablation evidence (-45.83 gap without evolution)
- [Paperclip & AgentRxiv deep dive](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md) -- retrieval-augmented iteration (AgentRxiv: plateau without retrieval, continued improvement with N=5), knowledge accumulation protocol
- [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md) -- strategy store implementation, Evolution Manager species, species retrieval integration
- [context-folding-progressive.md](../handoffs/active/context-folding-progressive.md) -- multi-tier condensation, compaction quality evaluation methodology, RL-trained compaction roadmap
- [intake-117](https://github.com/NousResearch/hermes-agent) Hermes Agent -- FTS5+LLM summarization memory, periodic knowledge reinforcement (worth_investigating)
- [intake-140](https://github.com/martian-engineering/lossless-claw) Lossless Claw -- DAG-based hierarchical summarization, immutable store + active context, deterministic three-level compaction (worth_investigating)
- [intake-141](https://arxiv.org/abs/2602.22402) CMV -- DAG-based context versioning with snapshot/branch/trim, three-pass structurally lossless trimming (worth_investigating)
- [intake-144](https://github.com/langchain-ai/deepagents) Deep Agents -- automatic conversation summarization, sub-agent isolation with separate contexts (worth_investigating)
- [intake-156](https://arxiv.org/abs/2507.02259) MemAgent -- segment-based reading with memory overwrite, Multi-Conversation DAPO, 437.5x extrapolation (worth_investigating)
- [intake-261](https://arxiv.org/abs/2604.02268) Skill0 -- in-context RL for skill internalization, helpfulness-driven dynamic curriculum (worth_investigating)
- [intake-262](https://arxiv.org/abs/2601.04786) AgentOCR -- optical self-compression, segment optical caching, compression quality threshold c_t <= 1.2 (worth_investigating)
- [intake-265](https://arxiv.org/abs/2604.01007) Omni-SimpleMem -- autoresearch-guided memory framework discovery, 23-stage autonomous pipeline (worth_investigating)
- [intake-267](https://arxiv.org/abs/2604.01599) ByteRover -- agent-native memory, hierarchical context tree, importance scoring with recency decay (worth_investigating)
- [intake-291](https://github.com/rowboatlabs/rowboat) Rowboat -- knowledge graph as persistent memory, Markdown+backlinks (Obsidian-compatible) (worth_investigating)
- [intake-316](https://x.com/chrysb/status/2043020014035570784) Long-Term Memory survey -- nine-axis design space, raw vs derived tension, unsolved forgetting policies (worth_investigating, high relevance)
- [intake-326](https://github.com/MemPalace/mempalace) MemPalace -- 96.6% LongMemEval R@5, palace hierarchical architecture (wings/rooms/drawers), +34% from metadata filtering (new_opportunity, high relevance)
- [intake-346](https://mem0.ai/blog/state-of-ai-agent-memory-2026) Mem0 -- $24M cloud memory platform, ~85% LongMemEval, LLM-based extraction (worth_investigating)
- [intake-698](https://arxiv.org/abs/2606.06036) MRAgent ("Memory is Reconstructed, Not Retrieved") -- Cue-Tag-Content associative graph + active reconstruction (LLM-reasoning-in-the-loop, evidence-conditioned path-pruning); ~118k tokens vs 245k-3.3M baselines; cloud-LLM-bound (Gemini-2.5-Flash / Claude-Sonnet-4.5), no CPU/local results, loses to Mem0 on LoCoMo multi-hop F1 (43.69 vs 45.17). Logged as a comparative datapoint against internal-kb-rag's parked two-pass retrieval; transferable lever = token-cost discipline (adopt_patterns)
- [intake-715](https://arxiv.org/abs/2605.22721) DecentMem ("Self-Evolving Multi-Agent Systems via Decentralized Memory") -- decentralized per-agent dual-pool memory (exploitation + exploration) with online LLM-judge reweighting + claimed O(log T) regret bound; only the dual-pool structure transfers to the autopilot strategy_store, the per-stage judge-reweighting conflicts with AP-27 + the P17.BT-4 KILL; no released code, cloud-favorable small backbones on frameworks we don't run (adopt_patterns)
- [progress 2026-07-05](../progress/2026-07/2026-07-05.md) -- exact episodic FAISS health (`526,729/526,729`, `100.0%` overlap, `0` missing/stale IDs) and current AutoPilot live state after the Fable restart
- [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md) -- current-state banner for the live AutoPilot PID, W8 blocker, and exact FAISS diagnostic summary

## Updates — 2026-04-28

This update records two Flywheel patterns from intake-492 — the wikilink learning-loop scorer (deferred) and the read-side `memory(action=brief)` token-budgeted assembler — both as design references, not adopt_component.

### Flywheel wikilink learning-loop scorer pattern (intake-492, K8 deferred)

Per [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) K8:

- **Pattern**: auto-wikilink suggestion uses accept/reject feedback to update a graph-edge scorer over time. Scorer combines alias matching + co-occurrence statistics + graph topology + semantic context. Each accepted suggestion increments the edge weight; each rejected suggestion decrements. Over time the scorer learns the project's actual link conventions.
- **Adapted use**: for `wiki/INDEX.md` compilation pipeline, weight cross-document links by validation feedback. When the linter or user rejects a cross-link suggestion, the scorer learns to suppress similar suggestions; when accepted, it learns to surface them.
- **Deferred** until KB-RAG K1–K7 ships and measured wiki-cross-link quality gaps emerge. No point training a scorer when the underlying retrieval pipeline is in flux.
- **Harness is Node/MCP-specific.** Python re-implementation non-trivial: Flywheel's scorer lives inside the Obsidian-coupled MCP runtime. The pattern is portable; the code is not.

### Flywheel `memory(action=brief)` token-budgeted assembler with confidence decay (intake-492)

- **Read-side**, NOT promote-to-persistent. Earlier framing was inaccurate (corrected in `wiki/context-management.md` 2026-04-28 Updates).
- **What it does**: assembles a query-scoped brief from already-persisted vault content within a token budget. Confidence decay weights older entries lower; budget cap prevents unbounded growth.
- **Why useful as design reference for memory-augmented systems**: shows how a folded-summary side-car *should be queried*. Not "give me everything tagged X"; instead "give me the highest-confidence brief for query Q within token budget B." This shape applies to the EPYC strategy-store and skill-bank as a future query-API upgrade.
- **NOT a write primitive.** Persistence in Flywheel happens via separate write tools.

### Sources

- [`handoffs/active/internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) — K8 wikilink learning-loop scorer (deferred)
- intake-492 (Flywheel) — wikilink scorer pattern + read-side `memory(action=brief)` assembler

## Frozen-backbone persistent memory cluster (2026-05-19)

Two May 2026 papers bracketing the design space for attaching trained persistent-memory modules to frozen LLM backbones — directly addressing the open question of how to give the orchestrator cross-session memory without retraining 26-30B production models.

**δ-mem** (intake-539, arxiv:2605.12357, Lei et al. — declare-lab) — lightweight delta-rule online associative memory sidecar to a frozen full-attention backbone. Historical context compressed into a compact online state matrix (e.g. 8×8) updated via delta-rule; low-rank corrections injected into attention. **Released code + adapter checkpoint**: [github.com/declare-lab/delta-Mem](https://github.com/declare-lab/delta-Mem) CC-BY-4.0 with Qwen3-4B-Instruct-2507 adapter. Reported 1.10× avg over frozen backbone, **1.31× MemoryAgentBench, 1.20× LoCoMo**. Validation cost: 3-day reproduction is the cheapest first-week validation in the May 2026 batch.

**Six-topology comparative study** (intake-568, arxiv:2603.16413) — catalogues six topologies for attaching memory to frozen Flan-T5-XL: M.1 Prefix, M.2 XAttn (parallel cross-attn), M.3 KV Extension, M.4 Hebbian (outer-product, 1.0M params — direct ancestor of δ-mem), M.5 Gated, M.6 Slot (top-k sparse). Headline empirical: **no single winner — capacity is the design knob**. M.2/M.6 win at low capacity; M.4 wins at high capacity / long-lag. No code released.

**Falsified baseline finding** — the cluster deep-dive identifies that our shipped B1 User Modeling (SQLite snapshot of user_conclude/user_profile injected into the system prompt per `orchestrator-conversation-management.md` completed handoff) is **functionally M.1 Prefix**, which intake-568 measures collapsing to **~0% at low capacity**. The orchestrator User Modeling slot is the natural integration target for δ-mem (online) or M.4 Hebbian (long-lag).

**Easiest llama.cpp integration path**: **M.3 KV Extension** (4.2M params) needs zero custom GGML ops — just prepend learned K/V vectors to the cache at decode start. Estimated **~3 engineer-weeks** for a first prototype against gemma4 worker_general. δ-mem path is ~5-6 weeks but shares kernel scaffolding with the active `log-linear-gated-deltanet-readiness.md` handoff (delta-rule primitive is shared with DeltaNet).

**Spike ladder** at [`delta-mem-reproduction.md`](../handoffs/active/delta-mem-reproduction.md): Phase 1 (3 days) reproduce released δ-mem Qwen3-4B adapter on EPYC; Phase 2 (3 weeks) ship M.3 KV-Extension adapter for gemma4 wired into B1 User Modeling data path; Phase 3 (6 weeks) full δ-mem GGML port + cross-session persistent bank combined with M.4-style Hebbian for long-lag retention.

**Sources**: [intake-539](https://arxiv.org/abs/2605.12357) δ-mem · [intake-568](https://arxiv.org/abs/2603.16413) Six-topology comparative study · [Deep-dive](../research/deep-dives/2026-05-19-frozen-memory-cluster.md) · [Reproduction spike](../handoffs/active/delta-mem-reproduction.md)

### Phase 1 reproduction result (2026-05-20, EPYC CPU)

The δ-mem Phase 1 reproduction landed on EPYC CPU on 2026-05-20 with the released `declare-lab/delta-mem_qwen3_4b-instruct` adapter against the released `Qwen/Qwen3-4B-Instruct-2507` base. Gates 1 + 4 PASS, Gate 3 PASS directionally, Gate 2 deferred:

| Gate | Spec | Result | Verdict |
|---|---|---|---|
| 1 | Adapter loads cleanly on Qwen3-4B-Instruct-2507 | 4.028B base + 2.5M delta-mem params, loads in **1.7 s** on CPU/fp32 | ✅ PASS |
| 4 | CPU inference within ≤2× of baseline | baseline 1.56 t/s, with adapter 1.48 t/s = **−5% overhead** | ✅ PASS (20× margin) |
| 3 | LoCoMo F1 ratio within ±20% of 1.20× (i.e. 0.96-1.44×) | base 0.324 / delta 0.533 = **1.65× at N=5** (1 conv × 5 q × 2 arms) | ✅ PASS directionally, magnitude inconclusive at small N |
| 2 | MemoryAgentBench F1 ratio within ±20% of 1.31× | INFEASIBLE on CPU — smallest source is 65K-ctx prefill (~22 min/sample at fp32; full eval 12-24+ h) | ⏸ DEFERRED until GPU |

**Per-question LoCoMo F1 (delta arm)**: 0.44, 0.0, 0.22, **1.0, 1.0** — the +1.65× ratio comes from two questions where δ-mem cleanly lifts from {0.67, 0.29} to {1.0, 1.0}. Two questions stayed flat (0.44, 0.22), one stayed 0.0 (a question the model is confidently wrong on regardless of memory).

**Operating cost reality check**: 1.5 h wall for 10 LoCoMo task-pairs at fp32 CPU eager attn. Extrapolating to the full LoCoMo benchmark (10 conv × ~200 q × 2 arms ≈ 4000 task-pairs) = **600 h ≈ 25 days on CPU**. Gate 3 magnitude reproduction is GPU-only realistic even at ±20% tolerance. Phase 1 conclusion: directional gate passes are enough to clear the "kill the spike" threshold; Phase 2 (M.3 KV-Extension on gemma4 worker_general) remains viable.

**Phase 1 artifact**: `/mnt/raid0/llm/epyc-inference-research/data/research/2026-05-20-dmem-locomo-smoke/results.json` + `.jsonl`.

**Model-agnostic caveat (2026-05-20)**: the M.3 topology is **not gemma4-specific** — it learns K/V vectors matching any frozen backbone's cache geometry (head_dim × num_heads × num_layers). Gemma4 is just the target Phase 2 will be tested against because worker_general is the highest-traffic role; the same recipe applies to frontdoor (Qwen3.6-35B), coder, or ingest_long_context with per-backbone param counts that scale with cache geometry.

### REPL session memory: what our checkpoint/restore actually persists (2026-07-27)

The orchestrator's cross-turn REPL state is a **third memory surface**, distinct from the episodic /
strategy / skill-bank trio above: it carries a single session's *working set* (variables, artifacts,
exploration log) across turns and requests, rather than learned signal across sessions. A 2026-07-27
comparison against `fast-rlm` (intake-901, dive-verified) established what it does and does not hold.

**Two persistence tiers, plus an explicit third bucket:**

| Tier | Mechanism | What it holds |
|---|---|---|
| JSON | `_is_json_serializable` gate in `src/repl_environment/state.py` | plain data — dicts, lists, scalars, strings |
| Signed pickle | `src/repl_environment/safe_pickle.py`, allowlisted + HMAC'd + 5,000,000-byte cap | numpy arrays/scalars, collections, datetime/Decimal/Fraction |
| Unavailable | reported, never silently dropped | REPL-defined functions/classes, pandas DataFrames, open handles, anything failing the allowlist |

**The design rule that matters: report what is missing, not only what survived.** `restore()`
reconciles against the **live namespace** rather than trusting the checkpoint payload, and
`get_state()` renders a `## Not Restored` section so the model is told which names are gone and why.
Before this, a variable dropped at restore time (an engine-builtin name collision) was reported as a
successful restore in telemetry — the count came from what the checkpoint *claimed*. The general
lesson generalizes past the REPL: **a memory system that reports only its hits cannot be debugged**,
because the consumer silently references state that is not there.

**Deserialization is a trust boundary, not a serialization detail.** The objects being persisted are
authored by model-written REPL code, so any pickle path is deserialization of untrusted input inside
the orchestrator process. `pickle` is listed in `ASTSecurityVisitor.FORBIDDEN_MODULES` precisely for
this reason. The boundary that made it acceptable has four layers — a `find_class` allowlist of inert
data types (load-bearing), an HMAC (tampering at rest only — it cannot establish content safety when
*we* are the ones pickling model-authored objects), a size cap, and an AST rule refusing REPL code
that binds a serialization hook. Two failure modes found during review are worth remembering
generally: a library-internal **nested unpickle** (numpy's object-dtype `multiarray.scalar` calls
plain `pickle.loads` on its data buffer, escaping any outer guard), and a **key-provisioning race**
that briefly published a zero-length HMAC key file readable as an empty, guessable key.

**Contested-claim status.** Whether carrying prior REPL *code* into a resumed prompt is cheaper than
re-deriving state is **not settled for our workloads**. The one published measurement (fast-rlm,
n=1 per arm, synthetic corpus, maintainer-measured) reports ~2.6× fewer input tokens, but its own
caveat says the saving holds only when follow-ups add a line or two of new code — "a session where
every query does heavy multi-step work is the case to watch", which is our regime. Measurement was
deliberately moved off a synthetic replication arm and onto real T3 hard-workflow/tool-use/REPL
traffic.

**Sources**: [intake-901](https://github.com/avbiswas/fast-rlm) fast-rlm REPL memory (dive-verified
2026-07-27) · [intake-783](https://github.com/avbiswas/fast-rlm) fast-rlm re-review ·
[Handoff](../handoffs/active/repl-session-memory-maturity.md) · [Progress](../progress/2026-07/2026-07-27.md)

### The 2026-07-05 vector-resolution corruption: a two-file publish that could not be atomic

The episodic store's vector lookups were silently wrong store-wide for three weeks. The mechanism is
worth recording because it is a general hazard for any index-plus-sidecar persistence scheme, not a
quirk of this codebase.

**`FAISSEmbeddingStore.save()` published two files with two separate renames.** POSIX cannot rename a
pair atomically, so a crash between them *always* leaves a mismatch. The only real choice is **which**
mismatch — and the two directions are not equally recoverable:

| published first | crash leaves | recoverable? |
|---|---|---|
| index | index ahead of id_map — trailing vectors have no id | **No.** `_load()`'s "truncate id_map to match index" is a silent no-op in this direction. |
| id_map | id_map ahead of index — trailing ids have no vector | **Yes.** `_load()` drops them. Self-healing. |

The old order was index-first. Worse, `add()` then took its position from `index.ntotal` while
appending the id at `len(id_map)`, so once the two diverged **every subsequent write inherited the
offset and persisted it into the metadata table**. Drift accumulated at +1 per interrupted publish
and reached 42; 57,721 of 57,960 rows ended up with a wrong `embedding_idx`. 19.7 GB of orphaned
`.tmp` files were the fossil record — including a 0-byte id_map temp beside a 2.79 GB index temp.

**Three generalizable rules this produced:**

1. **When two artifacts must agree and cannot be published atomically, choose the publish order so a
   crash lands in the self-healing direction** — then make the loader actually heal it, and log the
   unrecoverable direction as an error rather than pretending a no-op repaired it.
2. **Derive an append position from the structure you look up through**, not from a parallel one.
   Here `id_map` is what resolves a memory to a vector, so `len(id_map)` is the only defensible
   position; taking `index.ntotal` let the two disagree by construction.
3. **Fail closed on detected inconsistency.** Writing into a desynced store is what turned a
   recoverable outage into permanent data corruption.

**Repair was exact, not inferred.** `id_map` is a list of memory ids, so a row's true position is its
index in that list — a reverse lookup, no offset model, no re-embedding. Worth checking for before
reaching for a statistical alignment fit.

**Two measurement traps encountered while diagnosing this**, both of which produced confident wrong
findings:

- **Never compare embeddings with a byte hash.** float32 sub-ULP jitter changes the bytes but not the
  vector; 16 concurrent embeddings of one text hashed to different values while agreeing at pairwise
  cosine **1.0000**. This produced a false "the embedding server is non-deterministic" finding twice.
- **When classifying a store by field presence, check every key that could carry the field.** Two
  writer paths stored the same task text under `objective` and `task_description`; a classifier
  checking only the first read half the store as contentless and produced a false "half the store is
  telemetry" finding.

Sources: `handoffs/active/episodic-memory-integrity.md`, `orchestration/repl_memory/faiss_store.py`,
`scripts/maintenance/repair_faiss_id_map.py`, `progress/2026-07/2026-07-27.md`.

### Terminal reseed acceptance (2026-07-28)

The exact id-map repair restored pointer consistency but could not repair the separate
id-map-position-to-vector offset. The live store was therefore rebuilt from its task text under a
strict no-fallback BGE embedding contract. Receipt `20260727T220715Z` re-embedded **58,281** task
memories; the published FAISS/id-map pair is `58,281/58,281`, with `desync=0` and no metadata row
resolving to the wrong id.

The acceptance test deliberately re-embedded a sampled row's own text and compared it with the
published vector by cosine, not by byte hash. All **12/12** samples exceeded 0.9 and the mean was
**1.0000000496705372**, clearing the pre-registered `>0.95` gate; the same test before reseed was
mean `0.5505`, 0/12 above 0.9. This proves that the new vectors belong to their metadata rows, not
merely that the rebuilt index is structurally self-consistent. The API-only reload after publication
returned service health to `6/6` without changing the lineup.

The repair is a clean baseline, not recovery of historical trajectory fidelity: 41,057 source
objectives were already truncated to 200 characters, and answers/tool calls/reasoning were never
stored. New fixed-contract writes are required to accumulate richer trajectory data.

Sources: [episodic-memory integrity handoff](../handoffs/active/episodic-memory-integrity.md),
[2026-07-28 progress](../progress/2026-07/2026-07-28.md),
[`dry-run.log`](../artifacts/episodic-memory-reseed-20260727/dry-run.log),
[`apply.log`](../artifacts/episodic-memory-reseed-20260727/apply.log), and
[`cosine-acceptance.log`](../artifacts/episodic-memory-reseed-20260727/cosine-acceptance.log).

## Compiled Update — 2026-07-29: agent-experience memory — store shape, budget-conditional retrieval, and the curve nobody has measured

**Confidence**: the design conclusions are **verified** in the sense of resting on
convergent independent evidence plus a first-party falsification precedent; every
external number is **observation-grade** under MEASUREMENT.md and gates nothing.
Note that these items were filed by a single session across four handoffs — the
corroboration is between the *external sources*, not between our own records.

### Store shape: append-only, raw trajectory retained alongside the derived item

The strongest design signal in the batch is a convergence from opposite
directions: one external system arrives at "keep the raw trajectory alongside the
derived `{title, description, content}` item" **by construction**, and our own
prior work arrives at it **by falsification**. This settles a previously open
question in the autopilot distiller: **promotion must NOT remove raw
trajectories from L1.** The dual-layer experience bank is therefore scoped as an
**additive upper layer** over the existing per-case store (SQLite + FTS5); what
is missing is pattern distillation and similarity retrieval, and since FTS5 is
lexical this needs an embedding column (BGE servers already resident on
`:8090-8095`). The reference design leaves its own retrieval parameters and
eviction policy undefined — those are our decisions, and an unbounded bank is a
real hazard for a long-running autopilot.
[`unified-trace-memory-service.md`](../handoffs/active/unified-trace-memory-service.md) §UTM-M1, §UTM-M2

**Auditable `delete` is the structural differentiator.** A three-verb write API
(`insert` / `update` / `delete`) plus a mandatory "When NOT to Use" section on
every stored record maps onto the existing `APPEND`/`CREATE`/`UPSERT` surface;
the missing verb is the **auditable delete**, and first-class deletion rather
than implicit decay is what separates the systems that worked in these
comparisons from the heuristic-management systems that underperformed.
[`unified-trace-memory-service.md`](../handoffs/active/unified-trace-memory-service.md) §UTM-M3

### Retrieval: k is a measured parameter, and it must be budget-conditional

Do not port cosine-top-1. Two convergent facts: the k-ablation **loses half the
benefit by k=4** (49.7 / 46.0 / 45.5 / 44.4), and the one independent 35B
replication **failed specifically at the retriever** after an embedder swap —
which is exactly the substitution we would make with local BGE. Any sweep needs
**k=1** and **episodic-only** control arms.
[`engram-conditional-memory.md`](../handoffs/active/engram-conditional-memory.md) §Research Intake Update 2026-07-29

More consequentially, **k must be a fraction of remaining window budget, not a
fixed integer**. An independent third-party benchmark on a different backbone
finds **six of fifteen memory methods scoring BELOW the no-memory baseline at a
128K budget** (worst: −7.0pp), with the count of sub-baseline methods running
3 / 4 / 3 at 16K / 32K / 64K and **doubling at 128K**. The mechanism is
**context-budget competition** — injected memory displacing live history — and it
**must not be conflated** with our own recorded late-decay-from-store-growth
failure. Two different diseases; conflating them produces the wrong fix. Design
consequences: inject retrieved items only while live history occupies more than a
fraction of the window and **inject nothing once the untruncated history fits**;
cap injection as a fraction of remaining budget; and add a **no-memory control
arm** to every memory A/B — six published methods lose to no-memory at 128K and
**would have shipped undetected without one**.
[`unified-trace-memory-service.md`](../handoffs/active/unified-trace-memory-service.md) §UTM-M6–M9;
[`engram-conditional-memory.md`](../handoffs/active/engram-conditional-memory.md) §budget-conditional rider

### Budget the write gate DOWN, not up

The admission judge in one system measures at **72.7% accuracy** and the paper's
own simulation shows ground-truth labels buy only **+4.8pp of a 13.4pp effect**,
with judge accuracy in the **70–90% band forming a plateau**. Therefore the
distiller's write gate should use the **cheapest adequate local judge** — not an
eval-tower call, not a frontier model. A second system reinforces this: its
advantage comes from the auditable three-verb write API, not from an expensive
admission judge. **Contrast**: in a third system the admission test *is*
load-bearing. The two gate different things, so do not generalize one budget to
the other.
[`autopilot-continuous-optimization.md`](../handoffs/active/autopilot-continuous-optimization.md) §AP-29a

### Correction — do not carry "best overall" forward

An independent benchmark places the memory system whose **schema** we are
adopting **LAST of 13** on Cross-Episode Knowledge (Easy split); the earlier
"second behind ACE" reading recorded in this repo was **wrong**. It *is* best
among memory methods on In-Episode Execution at 16K/32K/128K — but even there a
**plain long-context baseline beats all fifteen methods**. Keep the store-shape
adoption; drop the ranking claim wherever it appears. (The same source carries an
unflagged defect of its own: one table's 64K column duplicates a different
table's progress-score column, invalidating that paper's 64K conclusions — so
even the corrected ranking is quoted only at the budgets that survive.)
[`unified-trace-memory-service.md`](../handoffs/active/unified-trace-memory-service.md) §UTM-M10;
[`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) §dive table

### The measurement that does not exist — an EPYC-original deliverable

**No paper in this set reports a per-window (non-cumulative) success-rate versus
store-size curve** — and one of them concedes the gap in its own Future Work. The
published figures are **cumulative**, and a cumulative curve is *structurally
incapable* of showing late decay: the per-window curve can fall while the
cumulative curve still rises. Building that instrument is blocked on no external
dependency and is required in any memory A/B before an adoption decision.
[`unified-trace-memory-service.md`](../handoffs/active/unified-trace-memory-service.md) §UTM-M5

### Retrieval alongside grep, not instead of it

A widely-relayed reading of an agent-retrieval paper — "14.92 / 9.84 / 8.33"
treated as retrieval scores — is wrong: those are **counts of grep/rg/find shell
invocations**, and the same paper's Table 2 has the **dense retriever winning**
(90.0/86.0 vs 89.0/83.0). The transferable finding is **behavioural
substitution**: it argues for retrieval *alongside* grep, not against an
embedding index.
[`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) §2026-07-29 dive corrections

### Source References

- [`unified-trace-memory-service.md`](../handoffs/active/unified-trace-memory-service.md) — UTM-M1..M10: store shape, additive layering over `src/trace/`, three-verb write API, the missing per-window instrument, 128K context-budget competition, and the ranking correction
- [`engram-conditional-memory.md`](../handoffs/active/engram-conditional-memory.md) — utility-aware retrieval over the adopted schema; k-ablation and the replication that failed at the retriever; budget-conditional k
- [`autopilot-continuous-optimization.md`](../handoffs/active/autopilot-continuous-optimization.md) — AP-29a write-gate budget and the judge-accuracy plateau; the CORE contrast
- [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) — corrected retriever reading (call counts, not scores)
- [`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) — dive-outcome table incl. the duplicated-column defect in the ranking source
