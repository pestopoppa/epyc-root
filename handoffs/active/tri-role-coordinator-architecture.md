# Tri-Role Coordinator Architecture (Thinker / Worker / Verifier)

**Status**: STUB
**Created**: 2026-04-26 (via Trinity deep-dive — intake-474, ICLR 2026)
**Priority**: HIGH (architectural — unblocks Trinity's strongest empirical lever)
**Categories**: agent_architecture, routing_intelligence, cost_aware_routing
**Related**: [decision-aware-routing.md](decision-aware-routing.md), [learned-routing-controller.md](learned-routing-controller.md), [routing-intelligence.md](routing-intelligence.md), [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Deep-dive**: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md)

---

## Objective

Add a per-call **role axis** (Thinker / Worker / Verifier) to the routing decision, orthogonal to model selection. Today our orchestrator collapses every dispatch to model-selection only — `(model)` — and review/escalation is a pipeline-level concern outside the routing policy. Trinity's evidence is that the role axis is *separable* from agent selection and worth **5–8 points** on benchmarks (their ablation: removing tri-role costs −5 to −8 across LCB/Math500/MMLU/RLPR; removing Thinker alone costs −6.0 on Math500 and −4.57 on RLPR). The change is architectural and *optimizer-independent* — it lands the same regardless of whether the routing head is trained by ES, SFT, or contrastive Q-update.

## Why this is the gap, not the optimizer choice

Trinity has two orthogonal contributions: (1) sep-CMA-ES as the trainer, (2) `(LLM, role)` as the action space. Our existing routing controller (`learned-routing-controller.md`) and Q-scorer (`decision-aware-routing.md`) work on the model-selection axis. Neither addresses the role axis. The role axis is **independent** — it matters whether we train via backprop or evolution. This handoff isolates the architectural change so it can ship without committing to the optimizer rewrite.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-474 | TRINITY: An Evolved LLM Coordinator (ICLR 2026, Sakana AI) | high | new_opportunity |

Key Trinity ablation evidence (from deep-dive section 1.5 / paper Table 2):

| Ablation | Δ vs full Trinity |
|---|---|
| Remove tri-role (single role) | −5 to −8 points across all four benchmarks |
| Remove Thinker role only | −6.0 Math500, −4.57 RLPR |
| Final-token instead of penultimate | >−10 on LiveCodeBench |
| Remove SVD-scale FT | −3 to −4 across tasks |

Tri-role removal is the second-largest ablation effect after the feature-position swap.

## Open Questions (must resolve in TR-1)

1. **Role taxonomy mapping**: Trinity defines *T = analyse/plan/decompose/critique*, *W = act on the task*, *V = check correctness/completeness*. Our existing labels (`frontdoor`, `architect_general`, `coder`, `reviewer`, `worker`) mix model identity with implied role. What is the clean separation? Is `architect_general` a Thinker or a Worker? Is the existing review/escalation pipeline a Verifier turn under another name?
2. **Pool-scale meaningfulness**: Trinity's pool has 7 LLMs with massive specialization variance (GPT-5 vs Gemma-3-27B). Our open-source-only inner pool is narrower. Do tri-role distinctions carry semantic weight at our scale, or do all three roles collapse to "ask the most capable available model"?
3. **Surface area**: does role assignment apply per individual orchestrator call, per multi-turn session, or both?
4. **Termination semantics**: Trinity terminates when Verifier returns ACCEPT (max K=5 turns). Our orchestrator already has retry/escalation logic. How do these compose? Is V acceptance equivalent to passing the existing review gate?
5. **Action space arithmetic**: Trinity uses decoupled `(L+3)`-dim flat logits (independent softmaxes over L LLMs and 3 roles). Should we adopt the same decoupling, or model `L × 3` directly (joint distribution)? Decoupled is cheaper and matches Trinity's evidence.

## Implementation Phases

### TR-1: Role Taxonomy Definition (SCOPING — required before TR-2+)

- [ ] **TR-1.1** Audit existing role-bearing fields in `epyc-orchestrator/src/`: `model_role`, `RoleResult.role`, escalation flags, retry markers, review-trigger paths. Produce a mapping table from current labels to {T, W, V}.
- [ ] **TR-1.2** Decide whether Verifier subsumes the existing review/escalation pipeline or is a parallel mechanism. Document the decision in this handoff and in `routing-intelligence.md` (which owns the review trigger).
- [ ] **TR-1.3** Decide on action-space encoding: decoupled `(N_models + 3)` logits vs joint `(N_models × 3)` logits. Default to decoupled per Trinity's ablation evidence; document if rejecting.
- [ ] **TR-1.4** Resolve open questions 1–5 above with the user; write the conclusions into a `Role Taxonomy` section appended to this handoff.
- [ ] **TR-1.5** Decide whether `ROLE_AWARE_ROUTING` feature flag is needed (default OFF) — likely yes, to enable A/B eval at TR-5.

**Gate**: TR-1 produces a written role schema and is reviewed before TR-2 begins.

### TR-2: Data Layer — Add Role to Routing Payload

- [ ] **TR-2.1** Extend `RoleResult` (and the routing-decision dataclass) with a `role: Literal["thinker", "worker", "verifier"]` field. Default to `"worker"` for backward compat.
- [ ] **TR-2.2** Schema migration for `episodic.db`: add `assigned_role` column to routing memories (nullable for legacy rows). Update `parallel_embedder.py` / `episodic_store.py` to write the new field.
- [ ] **TR-2.3** Update episodic-store query paths that consume routing memories to surface the role field (downstream consumers: `routing_classifier.py`, `q_scorer.py`, retraining scripts).
- [ ] **TR-2.4** Backfill: write a one-shot script that infers role for existing memories from the available signals (e.g., "this memory was a review trigger" ⇒ Verifier). Acceptable to leave NULL where inference is ambiguous.

### TR-3: Initial Role Classifier (Heuristic First)

- [ ] **TR-3.1** Implement a rule-based role classifier in `src/classifiers/role_classifier.py`: fixed mapping from request context (retry count, escalation flag, review-trigger flag, prompt features) to {T, W, V}. Deterministic, no ML.
- [ ] **TR-3.2** Wire the classifier into `routing.py` so each dispatch call carries an assigned role.
- [ ] **TR-3.3** Run for ≥1 week shadow mode with `ROLE_AWARE_ROUTING=0` (decision logged but not acted on). Collect role-distribution telemetry.
- [ ] **TR-3.4** Diagnostic check: is the role distribution non-degenerate (e.g., not 99% Worker)? If degenerate, pause and revisit TR-1 taxonomy.

### TR-4: Per-Call Dispatch Wiring (Execution)

- [ ] **TR-4.1** In `routing.py`, compose role with model selection: per-role model-affinity table OR independent role+model softmax (per TR-1.3 decision).
- [ ] **TR-4.2** Update `RoleResult` consumers to honour the assigned role — Thinker turns get the planning prompt template, Verifier turns get the verification prompt template, Worker turns get the standard execution template.
- [ ] **TR-4.3** Multi-turn composition: if our orchestrator runs multi-turn sessions, ensure subsequent turns can read the prior turn's role and adapt. (Trinity passes the full transcript + a brief role-specific prompt each turn.)
- [ ] **TR-4.4** Verifier-acceptance termination: if Verifier returns ACCEPT, short-circuit subsequent dispatch within the same session (echoing Trinity's K=5 termination semantics).

### TR-5: A/B Evaluation — Role-Aware vs Role-Agnostic

- [ ] **TR-5.1** Define benchmark suite for the A/B: must include at least one task family where role distinction is *expected* to matter (Math500-style multi-step reasoning, code-write-then-test). Reuse existing eval-tower benchmarks where possible.
- [ ] **TR-5.2** Run paired A/B with `ROLE_AWARE_ROUTING=1` vs `=0` for ≥N=200 per arm per benchmark. Use the same routing-classifier weights so the model-selection axis is constant.
- [ ] **TR-5.3** Decision gate: if Δ ≥ +2 points on at least one benchmark with no regression > −1 point on others, promote to default-on. If flat or regression, stay OFF and document negative result in `Open Questions` for future revisit (consider whether the role taxonomy from TR-1 was wrong).

## Dependency Graph

```
TR-1 (taxonomy + open questions) ──gate──
TR-2 (data layer)                    │
TR-3 (heuristic classifier)          │ ── needs TR-2
TR-4 (dispatch wiring)               │ ── needs TR-2, TR-3 (heuristic OK as starter)
TR-5 (A/B eval)                      │ ── needs TR-4 + benchmarks
```

TR-1 is a hard gate — do not start TR-2 without resolving the open questions, since the data-layer schema depends on the action-space decision (TR-1.3) and the Verifier-vs-review decision (TR-1.2).

## Relationship to Existing Systems

| System | Relationship | Impact |
|---|---|---|
| `learned-routing-controller.md` | Supplies the model-selection axis; this handoff adds the role axis | Routing classifier output dim grows from `N_models` to `N_models + 3` (decoupled) |
| `decision-aware-routing.md` | DAR-2/3/4 reshape Q-value learning on the model axis | Tri-role addition is independent — DAR fixes apply per-role after this lands |
| `routing-intelligence.md` | Owns the review-trigger and escalation pipeline | TR-1.2 decides whether Verifier subsumes or parallels the existing review path |
| `meta-harness-optimization.md` | Optimises prompt templates per role | Tri-role gives PromptForge a richer search space (one template per role × task family) |
| Episodic memory | Currently stores `(prompt, model, outcome)` | Add `assigned_role` so retraining can condition on role |

## Cross-Cutting Concerns

- **Backwards compatibility**: All existing memories pre-TR-2 lack the role field. Default to `"worker"` on read; backfill where inferable. Don't hard-fail on missing role.
- **Observability**: Add role to all telemetry surfaces (logs, metrics, eval-tower output) from TR-2 onward, before any A/B.
- **Optimizer-independence**: This handoff lands the architectural change. Whether the role classifier is rule-based (TR-3 starter), MLP-distilled (later, via `learned-routing-controller.md`), or sep-CMA-ES-trained (later, via the Trinity replication spike) is a separate decision.

## Reporting

After each TR-X completion, update:
- This handoff (mark task done, capture lessons)
- `routing-and-optimization-index.md` (subsystem-status row + P19 section)
- Progress log for the day

If TR-5 produces a negative result, also update [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) Section 6 ("Open Questions") with the empirical answer to "do tri-roles have semantic meaning at our scale?".

## Key Files (anticipated)

| Component | Path | Status |
|---|---|---|
| Role classifier (heuristic) | `epyc-orchestrator/src/classifiers/role_classifier.py` | NEW |
| Routing dataclass | `epyc-orchestrator/src/api/routes/chat_pipeline/routing.py` | EDIT (add role field) |
| RoleResult | locate via grep at TR-2 start | EDIT |
| Episodic store schema | `epyc-orchestrator/orchestration/repl_memory/episodic_store.py` | EDIT (migration) |
| Feature flag | `epyc-orchestrator/src/features.py` | EDIT (`role_aware_routing`) |
| Eval-tower benchmark | TBD at TR-5.1 | EDIT |

## Notes

This handoff isolates the *single biggest empirical lever* in Trinity's ablation set. It can ship under any optimizer choice and does not commit us to the sep-CMA-ES rewrite. Treat the existing routing controller and Q-scorer as compatible substrates — both can grow a role axis without re-architecture.

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-493] "Learning to Orchestrate Agents in Natural Language with the Conductor"** (arxiv:2512.04388, ICLR 2026, Sakana AI)
  - **Framing**: competitive intelligence — what others are publishing in the design space. Not an architecture EPYC is committing to copy.
  - Authors: Nielsen, Cetin, Schwendeman, Sun, Xu, Tang — six-author overlap with Trinity (intake-474), parallel design-space probes underpinning Sakana Fugu.
  - Distinct from Trinity: Trinity = 0.6B SLM + 10K linear head trained by sep-CMA-ES emitting `(LLM, role)` per turn. Conductor = 7B model trained via **GRPO** (2× H100, 200 iter × batch 256) emitting **`(worker_id, NL_subtask, access_list)`** per coordination step — communication topology emerges as a derived consequence of access-list selections; "role" is NOT a Conductor primitive (only Trinity has roles). Conductor adds recursive self-as-worker as a small (+1–2.2 pp) test-time scaling mechanism.
  - Reported results (concrete): LCB V6 +1.03 pp vs GPT-5 (within pass@1 noise); GPQA-D +2.7 pp vs Gemini-2.5-Pro; open-source-only inference +~10 pp vs Claude Sonnet 4 (strongest ablation). Code/weights promised in supplementary post-anonymization, NOT visible at intake date.
  - Delta from this handoff: this handoff scopes a *static heuristic* tri-role classifier (TR-1.x). Conductor and Trinity together demonstrate that learned, end-to-end-trained coordinators are a viable published design space — but neither is a target we are committing to. **One of several options for future escalation paths** if/when the tri-role classifier saturates; the current tri-role surface remains the substrate regardless of any future learning-head choice.
  - Caveats (Tier 2b): six-author overlap with Trinity means the two papers are not independent corroboration; multi-agent systems literature (MAST taxonomy, arxiv:2503.13657 — 36.9% inter-agent misalignment) documents failure modes terminal-reward RL does not directly address; +1.03 pp LCB headline is within noise.
  - Action: cross-link to `outer-coordinator-learned-head.md` (OC-0 scoping should reference Conductor + Trinity as design-space data points, NOT primary peer architectures). No tri-role scope change here — intake informational.
