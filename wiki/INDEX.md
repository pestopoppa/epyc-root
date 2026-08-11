# Project Wiki — Knowledge Index

**Manifest reconciled**: 2026-08-11 (dense-day pass, second/closing tranche) — of 110 sources changed
since the 2026-08-10T16:08:43Z compile, the **settled** governance/kernel narrative was compiled into
six articles: **Hardware Optimization** (the production kernel freeze to v9 with region-locked
certification numbers; AutoKernel's own hardened sandbox refusing a stale-instrument receipt
post-freeze; the CPU-decode GEMV lever re-anchored from a shelved SIMD plan to barrier-count fusion;
the env-flag inventory's new trace-interpretation column; the RVP-T0 MFMA/`init_tensor_uniform`
static-probe results), **Benchmark Methodology** (the instrument-era registry's v9-cutover gap,
closed by three same-day operator ratifications; the eligibility-vs-kernel-identity scope collision
it surfaced; a sealed-capture scorer found systematically more permissive than its canonical
counterpart), **Agent Architecture** (a 243-hour coordinator-daemon outage reported healthy, the
nudge-guard deadlock that caused a ~10-hour fleet stall, the session-bus C-series hardening arc, and
the backlog dispatch queue's retirement as an unreliable instrument), **Knowledge Management** (a
same-day audit's four-state wiring test and its receipts-outrank-messages rule, the
filesystem-presence-is-not-provenance and closed-box-more-misleading-than-open findings, and a
129-item correction backlog made tractable by classifying what each item's own text demands),
**Inference Serving** (a fail-open 200 that masked backend outages as model answers across every eval
fan-out, and a recurring NUMA region-lock regression now in derived priors), and **Autonomous
Research** (AutoKernel's candidate-execution/input-rotation/roofline hardening with zero inference run
yet; AutoPilot's v10 multi-tier baseline sealed and applied while the loop stays stopped; a
sequential-verdict mechanism shipped deliberately neutral on the operator decision it exists to
inform). Three items are explicitly recorded as **IN-PROGRESS, not settled**: the `binary_version`
era-registry discriminator (Token 2, drafted but unsigned), full adoption of `backlog_queue_gen.py` as
the dispatch queue's replacement, and AutoKernel's first hardened candidate campaign. **Checked and
explicitly excluded, not merely deferred**: the day's `learned-routing-controller.md` and
`decision-aware-routing.md` edits, and the `gpu-serving-tie-in-program.md`, `mi210-big-model-and-
acceleration-roadmap.md`, `document-parser-table-bench.md`, `model-stack-change-standardization-
audit.md`, `model-stack-single-source-update-pipeline.md`, and `stale-open-audit-2026-07-18.md`
touches, were verified by diff against today's commits to be pure checkbox-corruption repairs or
citation-attribution fixes with no new measured finding — routing_intelligence and cost_aware_routing
carry no update this pass. **Correction to an earlier draft of this note**: `numa-topology-cutover-
resume-20260730.md` was initially miscategorized as excluded; it in fact carries a real, new P0-0
defect filing (`3c7edafc`, the derived-priors `NUMA_FULL` drop) that IS compiled, into Inference
Serving. `.last_compile` still NOT advanced pending final review by the session main. Prior notes
retained below.

**Manifest reconciled**: 2026-07-30 (scoped pass) — of 109 changed sources, the
*settled* knowledge from the day's agent-file/measurement track was compiled into
**Agent Architecture** (full-stack agent-file audit D1–D13, layered context
architecture, incident-log house style, enforcement hardening, frozen-tree
governance gap) and **Benchmark Methodology** (MEASUREMENT v2 core+annex
ratification, §1 metric scoping, P-BENCH-PLACEMENT-1, the retracted April
exemplar). The ~83 in-flight campaign handoff sources (NUMA/N24, batched-decode,
E5/E8) were **deliberately deferred, not compiled**: their numbers were revised
the same day (several suspended banners), and compiling mid-revision would mint
claims needing retraction — the exact failure the 2026-07-29 status-weighted
pass was designed to avoid. `.last_compile` NOT advanced, so the deferred
sources re-surface at the next controlled pass. Prior notes retained below.

**Manifest reconciled**: 2026-07-29 (third pass, backlog clearance) — the 7 sources
queued since the 12:24Z compile, and deferred by three consecutive wrap-ups, were
compiled into four articles: **Inference Serving** (the GPU shadow lane — built,
tested, and *not activated*; P2-2 tenant landing; the whisper capability blocker),
**Hardware Optimization** (the MI210 is on NUMA node 1, not node 3; placement
authority is measured lineage, not locality; E5 remains scout-only), **Benchmark
Methodology** (E8 has no baseline signature and E5 no decision-grade cell — both
campaigns have produced instruments, not results), and **Agent Architecture** (the
coordinator-daemon/coordinator-agent split, structural bus routing, and the
determinate-state polarity defect class). The pass is **status-weighted**: every
incomplete campaign is compiled with its incompleteness as the headline, since the
stated reason for the prior deferrals was the risk of minting a claim that would
later need retracting. Prior notes retained below.

**Manifest reconciled**: 2026-07-29 — the 21 sources changed since the
2026-07-29T10:16Z compile (19 active handoffs, 1 blocked handoff, 1 progress
log, almost all of them the output of a single 24-entry research-intake batch)
were synthesized into ten articles. The pass is **correction-weighted**: nine of
the batch's nineteen deep dives overturned the record they were checking, and in
every case the corrected version is what was compiled, not the original claim.
Prior 2026-07-26 note retained below.

**Manifest reconciled**: 2026-07-26 — the seven changed checkpoint sources
were synthesized into Benchmark Methodology, Multimodal, and Inference Serving.
The update records capture-integrity requirements, bounded MiniCPM-o evidence,
and the E8 rebaseline hold without converting open campaign gates into
completion claims.

Compiled knowledge base for the EPYC 9655 inference optimization project. Each article synthesizes findings from research deep-dives, intake entries, handoffs, progress logs, and child repo documentation into a single navigable reference.

**Last compiled**: 2026-08-11 (dense-day pass — see the manifest note above for the six articles updated and the two categories explicitly excluded this pass. Prior 2026-07-29 note: third incremental pass — cleared the 7-source deferral backlog into 4 articles; `session-bus-thin-dispatcher.md`, held back by the prior pass for falling below the 3-source minimum, now clears it via the progress log and the tie-in program and is compiled into Agent Architecture. Prior second pass follows.)

**Previously compiled**: 2026-07-29 (second incremental pass — merged 3 changed sources into 2 articles: Knowledge Management (the cross-reference defect *resolved* — the earlier pass recorded it while still open — plus the new "never round-trip a whole document to append to it" rule) and Multimodal (how a pre-deployment assessment ages: backend premise struck, latency forecast falsified, hardware extrapolation retired, a self-doubted hypothesis confirmed, VAE identity left open). `handoffs/active/session-bus-thin-dispatcher.md` was **NOT** compiled — with only itself and the progress log as sources it falls below the 3-source minimum in the manifest's `writer_evidence_policy`, the same rule that held back `routing_intelligence` in the prior pass. Prior pass follows.)

**Previously compiled**: 2026-07-29 (incremental — merged 21 changed sources into 10 articles: Benchmark Methodology (eval-instrument correctness, the (model, scaffold) unit of report, four provenance downgrades), Agent Architecture (harness re-targetability; merged ≠ running), Memory-Augmented (store shape, budget-conditional retrieval, the missing per-window curve), Context Management (mandatory masking anchor, verbatim-log A/B, total-token accounting), Speculative Decoding (weight-map verification over config), Knowledge Management (the correction pass and the Stage-2b intake gate), Search & Retrieval (the struck GGUF-availability premise), Multimodal (LongText-Bench comparability + the ROCm f32 candidate fix), Training & Distillation (the inverted Experience-Distillation premise), LLM Prompting (GEPA-class optimizer of record + the compile cost line). `routing_intelligence` was NOT updated — its single new source does not meet the 3-source minimum in the manifest's `writer_evidence_policy`. Prior 2026-07-26 note follows.)
**Previously compiled**: 2026-07-26 (incremental — merged 7 checkpoint sources into Benchmark Methodology, Multimodal, and Inference Serving: lossless v4 capture and agentic trajectory eligibility; MiniCPM-o M-1 observation/M-2 pinned-interface closure; and frozen-v8 E8 rebaseline sequencing. The Laguna prompt-fix/Docker score, E8 numeric completion, quality apply, and 27B observations remain open. Earlier 2026-07-24 pass merged 14 sources into 7 articles.)
**Articles**: 26 compiled, 4 stub categories
**Total sources**: 590+ scanned documents across 6 source types; 2026-08-11 pass merged 110 changed/new sources into 6 articles (2 categories checked and explicitly excluded); 2026-07-24 pass merged 14 changed/new sources into 7 articles; 2026-07-21 pass merged 28 changed/new sources into 2 articles; 2026-07-20 pass merged 23 changed/new sources into 8 articles; 2026-07-05 pass merged 49 changed/new sources into 10 articles; 2026-06-21 pass merged 36 changed/new sources into 21 articles

---

## Core Inference Optimization

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Speculative Decoding](speculative-decoding.md) | 63+ | Every production target ships a near-free native MTP head that beats external drafters (measured dead); per-model MTP depth is now measured for all 3 architect candidates (122B-IQ2 n-max=2, 27B-dense/35B-A3B n-max=4) and batching interacts with spec-dec **architecture-dependently** — the "don't batch long-context" rule is 122B-IQ2-specific, not generic MoE |
| [MoE Optimization](moe-optimization.md) | 37 | Reasoning ∝ ACTIVE FLOPs, knowledge ∝ TOTAL params; GLM-5.2 routing is near-uniform (top_32=15%) so generic hot-expert offload/REAP is not justified; IQ2 GPU residency is two-for-two viable but caps at ~122B |
| [KV Cache](kv-cache.md) | 39 | StreamingLLM pre-v7 floor sweep failed the quality floor → no simple KV cluster admitted yet; per-token KV streaming over PCIe is an anti-pattern (7-14× slower than DDR5); GDN residents' O(1) KV make teleport KV-copy near-moot |
| [Quantization](quantization.md) | 33 | The architect's degenerate `\boxed{}` repetition loop tracks the MODEL not the quant (Q4 loops identically to IQ2 on the same item — 2-bit-EOS-damage hypothesis REFUTED); fenced CPU-Q4 arm tracks at-or-above GPU-IQ2 on hard reasoning, undercutting the case for a real IQ2 reasoning penalty |
| [Hardware Optimization](hardware-optimization.md) | 97+ | **Production froze to v9** (`0db32c06e`, binary 10125) 2026-08-11, with AutoKernel's own hardened sandbox refusing a stale-instrument receipt post-freeze; a same-day audit found several surfaces (gpu_shadow_lane pins, `reasoning_effort_certifications.yaml`, a research runner that silently *prefers* v8) still assumed v8 as current. Earlier: the MI210 is on **NUMA node 1, not node 3** — the incumbent 184-191 host-thread placement is already cross-node and its authority is *measured lineage, not locality*; device-local candidates were never tried. E5 remains **scout-only** (W1-W4 blocked on an operator reboot). Earlier: CPU decode is BW-exhausted but CPU *prefill* is an open compute-bound regime; v8 is frozen as `production-consolidated-v8`; E5 W0 scout (69/69 cells) shows 4×quarters beats any big-instance shape for EVERY production model, and cross-architecture GPU batching is architecture-dependent (small-MoE ≫ dense > large-MoE-IQ2, with the large-MoE arm uniquely collapsing at long context) |

## Serving & Systems

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Inference Serving](inference-serving.md) | 69 | A fail-open 200 had every eval fan-out through `:8000` scoring backend outages as low-quality generations (fixed 2026-08-11); a NUMA region-lock regression recurred a second time, now in derived priors rather than launch config (IN-PROGRESS, gated on a stack relaunch). Earlier: a GPU shadow lane is built, tested (170 lane tests) and **not activated** — no production traffic, registry frozen, no apply path in the module; an idle MI210 still does not imply a startable lane because its host threads sit in region `q3`. Earlier: the v7-cutover quarters-only launch was ruled an accidental regression and the big+quarters lineup was restored same-day via a new additive, no-outage `--numa-mode both` promotion path; the WP-12 fleet layer flipped live and its case-10 gate found production within-role concurrency comes from 6-process OS fan-out, not a role-level semaphore (which resolves to `Semaphore(1)` for every role); within-role placement SM's live KV-migration path re-ratified on the restored lineup (fwd 6/rev 1, 0 aborts) |
| [Local Inference](local-inference.md) | 36 | v8 frozen as `production-consolidated-v8`; deployed-lane throughput table + living model-probe scoreboard (all observation-grade); MI210 fits everything but the 122B-Q4 architect and GLM-5.2 (238 GB) |
| [Chat Templates](chat-templates.md) | 2 | Per-family turn markers + when to use `/completion` (Qwen/gemma-3/Llama3) vs `/v1/chat/completions` (gemma-4 multi-channel) — checklist for onboarding new models without silent routing failures |

## Routing & Evaluation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Cost-Aware Routing](cost-aware-routing.md) | 42+ | CoT scaffold-transplant falsified in both regimes; the reasoning-effort ladder got its first real measurements — the accuracy lever is the PROMPT (+32pp CoT-in-content), not native `<think>` (loses via a non-termination tail, fixable with a budget cap); `max_tokens` is a silent third quality axis (a ~57pp finished-vs-truncated swing measured) coupled to admission control via per-architecture KV/slot cost |
| [Routing Intelligence](routing-intelligence.md) | 67+ | RI-10 decision-ready but first packet is `hold_quality_unscored` (proxies favor enforce; factuality unscored); X-MAS learned route-mutation is live in enforce — first learned routing layer in production |
| [Benchmark Methodology](benchmark-methodology.md) | 112+ | The instrument-era registry didn't track the v9 kernel cutover — three operator ratifications closed the gap same-day (2026-08-11), and a scope collision between eligibility rows and kernel-identity rows in the same registry surfaced a durable `binary_version`-discriminator design (drafted, not yet signed); a same-day scorer audit found a sealed-capture extractor systematically more permissive than its canonical counterpart. A whole-file sha pin on a registry the autopilot itself writes autonomously is dead on arrival. Earlier: **E8 has no baseline signature and E5 no decision-grade cell** — both campaigns have produced instruments, not results; a scorer sharing mutable execution state (`test.db` collision) produced a stored verdict with no execution witness; `decision_grade=true` and `proposal_only=true` co-occur, and a tally is only comparable when its invocation path is quoted. Earlier: architect model-selection retained deterministic replay rather than regeneration after scorer defects; the sealed ThinkingCap no-think row and bounded Laguna remediation are current authority, while G3's missing controls and E8's unapplied recovery evidence remain explicit non-decision work |

## Agent & Architecture

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Agent Architecture](agent-architecture.md) | 77+ | The coordinator-daemon was dead for **243.1 hours** while reporting itself healthy (2026-08-11 fix: fold liveness+identity+freshness into one verdict); a nudge guard that tightened exactly as staleness worsened caused a ~10-hour fleet stall; the C-series bus-hardening arc closed but stayed committed-not-live until a daemon restart; the backlog dispatch queue was retired (only 32% of its "ready now" rows were actually dispatchable) rather than repaired. Earlier: coordination splits into a deterministic **coordinator-daemon** and an LLM **coordinator-agent** (neither can do the other's job); routing intent is a schema field, not payload prose; and the recurring defect class is a determinate-state failure — an unreadable state treated as a benign value, four times in one day. A merged fix and a running fix are different states. Earlier: consult primitive went design→staged-v1 in one week, all default-off; Hermes is now one client of the shared `/v1/chat/completions` + `x_*` contract rather than a special routing path |
| [Autonomous Research](autonomous-research.md) | 101+ | AutoKernel hardened candidate-execution sandboxing, input/address rotation, and per-quant roofline discipline with **zero model executions run** under the checkpoint; AutoPilot's v10 multi-tier baseline is sealed and applied while the loop stays intentionally stopped; a sequential-verdict mechanism (`sticky_refuted`) shipped behaviorally neutral, deferring its own policy question to the operator. Earlier: ledger authority cutover is live; planner economics pivoted to local drafting/critique, with `frontdoor` drafting and `worker_general` critique queued for the next boundary restart |
| [Memory-Augmented Models](memory-augmented.md) | 25+ | Episodic FAISS writes require cross-process locking; K-MEM Tulving is a mixed baseline with weak chronology and no memory-routing promotion |

## Context & Compression

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Context Management](context-management.md) | 28 | 80-92% of agent context is redundant; reasoning context does not transplant capability (amplifier, not substitute); DCP-for-consult landed default-off |
| [Context Extension](context-extension.md) | 19 | MemAgent achieves 437x extrapolation; Memento reveals 15pp KV-vs-text ceiling; YaRN is the production path for 256K-1M |
| [SSM & Hybrid Architectures](ssm-hybrid.md) | 9 | Verification latency (220ms/tok, 90% of cost) is the real speculation killer; Log-Linear GDN (ICLR 2026) could unblock via 4-10x state reduction |

## Training & Distillation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Training & Distillation](training-distillation.md) | 30 | LoRAX/S-LoRA are the code-backed adapter-serving references; MinT remains a closed-source scaling datapoint |
| [Reinforcement Learning](reinforcement-learning.md) | 14 | AReaL ruled out (6-order compute mismatch); GRPO/DAPO ubiquitous in deep-dive research |

## Multimodal & Domain

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Multimodal](multimodal.md) | 42+ | Benchmark deployed Qwen-VL field-placement before adding LocateAnything; Gemma 4 stays benchmark-first, not model-card-dismissed; the MiniCPM-o `vision_escalation` cutover now has a deterministic, model-agnostic promotion/rollback runbook, and `worker_vision` quartering has a quantitative demand/capability trigger gate replacing an unmeasured "in principle" |
| [Document Processing](document-processing.md) | 4 | ODL structured metadata and default-off body warnings now reach preprocessing; the hybrid sidecar is live on `127.0.0.1:5002`, so the remaining table gap is benchmark-backed comparison and routing policy |
| [Formal Verification](formal-verification.md) | 7 | Goedel-Code-Prover 8B beats GPT-5.3-Codex at 62.0%; RustEvo2 is now the gate for Rust specialist claims |

## Knowledge & Retrieval

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Search & Retrieval](search-retrieval.md) | 31 | K-RAG K7 seed eval picks recency-weighted recall@10, but final retrieval claim waits on the 70-case certification pool |
| [Knowledge Management](knowledge-management.md) | 19+ | A same-day audit's four-state wiring test (committed+live / committed-not-live / claimed-not-committed / live-wired-wrong) and its core rule — **artifacts on disk outrank any bus message when they disagree** — closed a phantom-pending-token defect; filesystem presence is not provenance (proven twice the same day); a closed checkbox with real, correct numbers is more misleading than an open one. Earlier: K-RAG K7 certification produced a zero-miss retrieval candidate; wiki compile remains a derived wrap-up artifact |
| [RAG Alternatives](rag-alternatives.md) | 2 | SLIDERS structured-DB+SQL alternative gated behind Phase 0 falsification (GPT-4.1 hard-wired adoption blocker; not on ColBERT upgrade path) |
| [Tool Implementation](tool-implementation.md) | 40 | Dashboards were built as liveness instruments, not value instruments; the regions-lock panel now separates `/proc` owners, live tap requests, and inferred activity instead of collapsing them into one ownership story |

## Research & Analysis

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [LLM Prompting](llm-prompting.md) | 14 | CoT controllability is 0.1-15.4% (safety positive); FlowSteer blocked on hybrid SSM |
| [Mechanistic Interpretability](mechanistic-interpretability.md) | 6 | Qwen-Scope releases SAEs for production-stack Qwen3/3.5 (~687 GB FP32 full subset, qwen license); AxBench + Wang 2026 falsify SAE-steering against simpler baselines (DiffMean, prompting); Section 4 benchmark-redundancy is the strongest application — pilot first |
| [Safety](safety.md) | 4 | External-source text is now quarantined as data; security review uses exploit-path-gated STRIDE/OWASP/LLM checks |

---

## Stub Categories

These categories have intake entries but insufficient depth for a compiled article. Raw sources are accessible via the query operation:

```
python3 .claude/skills/project-wiki/scripts/query_wiki.py "<category>" --human
```

| Category | Intake Entries | Notes |
|----------|---------------|-------|
| `emotion_psychology` | 18 | Persona, cognitive science of LLMs — not central to inference optimization |
| ~~`knowledge_management`~~ | — | Promoted to full article 2026-04-28 → [Knowledge Management](knowledge-management.md) |
| ~~`mechanistic_interpretability`~~ | — | Promoted to full article 2026-05-04 → [Mechanistic Interpretability](mechanistic-interpretability.md) |
| ~~`rag_alternatives`~~ | — | Promoted to full article 2026-04-28 → [RAG Alternatives](rag-alternatives.md) |
| ~~`safety`~~ | — | Promoted to full article 2026-06-13 → [Safety](safety.md) |
| `swarm_techniques` | 7 | Partially covered by [Agent Architecture](agent-architecture.md) and [Autonomous Research](autonomous-research.md) |

**2026-07-29 sources held back for insufficient corroboration (not compiled this pass):**
- `routing_intelligence` — the only new source is [`routing-intelligence.md`](../handoffs/active/routing-intelligence.md) §RI-CMP-1, filing a purpose-built prompt-router encoder as a `monitor_only` comparator against the MLP learned-routing controller. One source, and the entry is explicitly *not* a work item. It fails the manifest's `minimum_source_references: 3`, so it is recorded in [Search & Retrieval](search-retrieval.md) as a cross-reference only rather than driving a routing-intelligence update.

**2026-07-20 single-source stubs (not promoted to their own section this pass):**
- `cost_aware_routing` / `agent_architecture` — the [scaffold CoT cost-lever autopilot deployment](../handoffs/active/scaffold-autopilot-cost-lever-deployment.md) is a DESIGN handoff (episodic-memory-gated composite scaffold-then-nothink route; caps a beneficiary's CPU-decode tokens ~20-50×, quality benefit is headroom-conditional). All numbers are OBSERVATION-grade; nothing implemented. Its findings are already reflected in [Cost-Aware Routing](cost-aware-routing.md) (CoT scaffold-transplant falsified as a capability transplant, deployed only as a gated cost lever).

---

## How to Use This Wiki

**For humans**: Browse by section above. Each article has Summary, Key Findings, Actionable for EPYC, and Source References sections.

**For agents**: Query the knowledge base programmatically:
```
python3 .claude/skills/project-wiki/scripts/query_wiki.py "speculative decoding" --human
```

**To update**: Run the compile operation when new research is ingested:
```
python3 .claude/skills/project-wiki/scripts/compile_sources.py --full  # list sources
# Then invoke: "compile the wiki"
```

**Taxonomy**: See [SCHEMA.md](SCHEMA.md) for the full category ontology with 30 canonical categories and 34 aliases.
