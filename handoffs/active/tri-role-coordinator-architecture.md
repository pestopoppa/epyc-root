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

- [x] **TR-1.1** ✅ 2026-05-07 — Role mapping table written. Confirms roles are NOT model-permanent; every model participates in multiple roles depending on context. See "TR-1 Deliverable — Role Taxonomy" section below.
- [x] **TR-1.2** ✅ 2026-05-07 — Verifier as parallel mechanism initially; AND with existing review gate for early termination (TR-4.4). Autopilot telemetry to discover collapse opportunity after 1-2 weeks.
- [x] **TR-1.3** ✅ 2026-05-07 — Decoupled `(L + 3)` flat logits. Matches Trinity AND extends `RoutingClassifier` with +195 params (vs ~200K baseline).
- [x] **TR-1.4** ✅ 2026-05-07 — Role Taxonomy section appended below. All 5 open questions resolved with the user.
- [x] **TR-1.5** ✅ 2026-05-07 — `ROLE_AWARE_ROUTING` feature flag, default OFF. Toggle via `ORCHESTRATOR_ROLE_AWARE_ROUTING=1`.

**Gate**: TR-1 produces a written role schema and is reviewed before TR-2 begins. ✅ **GATE PASSED 2026-05-07** — TR-2 (data layer) is unblocked.

### TR-2: Data Layer — Add Role to Routing Payload ✅ LANDED 2026-05-07

- [x] **TR-2.1** Extended `RoleResult` (`scripts/benchmark/seeding_types.py:300`) and `RoutingResult` (`src/api/routes/chat_utils.py:67-72`) with `assigned_role: str = "worker"` field. **Naming note:** the field is `assigned_role`, NOT `role`, because `RoleResult.role` already exists as the model-role string ("frontdoor"/"worker_30b"/etc); collision would have silently broken every `RoleResult.role` consumer. Constants + feature flag live in new `src/classifiers/role_taxonomy.py` (TrinityRole enum + `normalise_role` + `role_aware_routing_enabled`).
- [x] **TR-2.2** Schema migration in `episodic_store.py` adds `assigned_role TEXT` via `ALTER TABLE memories ADD COLUMN assigned_role TEXT` (idempotent — `OperationalError` on existing column is swallowed, mirrors the precedent set by `model_id`). Index `idx_assigned_role` created. `MemoryEntry` dataclass + `to_dict`/`from_dict` carry the field. `store()`, `store_immediate()`, and `store_with_graphs()` all accept `assigned_role: Optional[str] = None`.
- [x] **TR-2.3** Reader paths surface the field — all four `SELECT … FROM memories` paths (`retrieve_by_similarity`, `get_by_id`, `get_all_memories`, `get_q_outliers`) now include `assigned_role` in their SELECT list and populate `MemoryEntry.assigned_role`. Downstream consumers (`routing_classifier.py`, `q_scorer.py`) read `MemoryEntry` via the dataclass surface, so no consumer-side changes were required to expose the field; TR-3 will populate it.
- [x] **TR-2.4** Backfill script at `scripts/memory/backfill_assigned_role.py`. Heuristic: action substring match — `review|verify|validate|compliance|critique|judge|qa` → VERIFIER; `architect|decompose|plan|design|strategy|synthes|ingest_long_context` → THINKER; default WORKER. Only writes rows where `assigned_role IS NULL`; idempotent on rerun; `--dry-run` flag prints classification counts without writing.
- [x] **TR-2.5** Tests: 21 unit tests in `tests/unit/test_episodic_store_assigned_role.py` cover taxonomy normalisation, feature-flag reading, schema migration idempotence, writer round-trip, legacy-NULL tolerance, backfill correctness + idempotence + dry-run + missing-DB error. All 21 pass; the existing 29 `test_episodic_store.py` tests still pass (no regressions).

**Validation**: feature flag `ORCHESTRATOR_ROLE_AWARE_ROUTING` is wired but defaults OFF — TR-3 classifier will populate the field in shadow mode without acting on it. The TR-5 A/B is what flips the flag.

### TR-3: Initial Role Classifier (Heuristic First)

- [x] **TR-3.1** ✅ **DONE 2026-05-07** — `src/classifiers/role_classifier.py`. Deterministic regex-only classifier. Returns `RoleClassification(role, reason)`. Rule precedence (first-match wins): VERIFIER (review/verify trigger AND prior-content cue), THINKER (architect-class routing OR force_role architect_* OR thinking_budget>0 OR plan/decompose/design keyword), WORKER (default). Word-boundary anchored so `checkmate`/`above the line` don't false-positive. 27 unit tests in `tests/unit/test_role_classifier.py` + 7 routing-integration tests in `tests/unit/test_pipeline_routing.py::TestTrinityRoleShadow` cover precedence, return shape, distribution-non-degeneracy.
- [x] **TR-3.2** ✅ **DONE 2026-05-07** — wired into `_route_request` in `src/api/routes/chat_pipeline/routing.py`. Classifier invoked AFTER `routing_decision` is set so it can read the head model role. Field is **always** populated and logged via `task_extra(strategy="trinity_role_shadow")` regardless of the `ROLE_AWARE_ROUTING` flag — TR-4 gates *acting* on the role; TR-3.3 just collects telemetry. Defensive `try/except` around the classifier call falls back to `"worker"` on any failure (verified by integration test `test_classifier_failure_falls_back_to_worker`).
- [ ] **TR-3.3** **Inference-gated.** Run for ≥1 week shadow mode (flag still default OFF, classifier active in shadow). Collect role-distribution telemetry from production traffic. Expected log line: `Trinity role classified: role=X reason=Y` with `strategy=trinity_role_shadow`.
- [ ] **TR-3.4** **Inference-gated.** Diagnostic check: is the role distribution non-degenerate (e.g., not 99% Worker)? If degenerate, pause and revisit TR-1 taxonomy. (Will use the same telemetry pipeline that consumes factual_risk + difficulty_signal shadow data.)

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

---

## TR-1 Deliverable — Role Taxonomy (2026-05-07)

User-resolved decisions on the five open questions. This section is the ROLE SCHEMA referenced by the TR-1.4 directive ("write the conclusions into a Role Taxonomy section appended to this handoff"). TR-2 onward depends on this.

### TR-1 Q1 — Role-to-model mapping

**Roles are NOT model-permanent properties.** Every model in our stack participates in multiple roles depending on context. This is a sharp confirmation of Trinity's per-call role-axis insight (deep-dive Section 2.1: "role is a per-turn property of the dispatch, not of the model").

Concrete mapping:

| Existing model / role | T (Thinker) | W (Worker) | V (Verifier) | Notes |
|---|---|---|---|---|
| `architect_general` (Qwen3.5-122B-A10B Q4) | **always** | rare | rare | Either queried by frontdoor for an opinion on hard cases, OR receives an escalated task and takes ownership: makes a plan and delegates partial/incremental/entire work to a suitable worker. Thinker turns dominate; direct Worker execution is the exception when the plan is short enough to inline. |
| `coder_escalation` (Qwen3.6-35B-A3B Q8) | sometimes | **mostly** | rare | Default Worker. Becomes Thinker when it identifies a parallelizable bundle and delegates focused sub-tasks to `worker_*` models instead of executing all in-process. |
| `frontdoor` (Qwen3.6-35B-A3B Q8, shared GGUF with `coder_escalation`) | sometimes | sometimes | sometimes | Genuinely tri-role. Direct answer = W. Plan + delegate to `worker_*` = T. Review of prior model output (e.g., long-context ingestion result) = V. Per-call role assignment is essential here — this is where the architectural lever produces the most leverage. |
| `worker_general` / `worker_explore` / `worker_math` (Qwen3-Coder-30B-A3B Q4) | rare | **default** | rare | Pure Worker. Could be promoted to Verifier on cheap-quick verification turns (e.g., "did the previous answer satisfy the format?"), but Thinker capacity is bounded by base-model quality. |
| `ingest_long_context` (Qwen3-Next-80B-A3B Q4) | sometimes | sometimes | sometimes | Long-document ingestion is W (extract). Multi-document synthesis is T (plan the synthesis structure). Cross-document fact-checking is V. |
| `worker_fast` (Qwen2.5-Coder-1.5B Q4) | NEVER | **default** | NEVER | Phase 3 compliance verdict (2026-05-07): baseline recall 0.33-0.47 — model lacks the working-memory capacity to hold an agent file faithfully. By extension, it cannot reliably plan or verify. Restrict to W role only, simple deterministic dispatches. Per `agent_file_compression_operating_point: none` (BLOCKED) in the registries. |
| Existing review/escalation pipeline | n/a | n/a | partial mapping | Today's review/escalation is *operational*, not *structural*: a worker fails or low-confidence-flags, a different role is invoked. This is a Verifier turn under another name when the next role is review-class. The proposal: instead of treating review as a black-box pipeline construct, surface it as an explicit `verifier` role assignment so the routing policy can REASON about it (and the classifier can learn it). |

The existing review pipeline is **partially** equivalent to a Verifier turn. TR-1.2 decision (below) makes this explicit.

### TR-1 Q2 — Pool-scale meaningfulness

**Tri-role distinctions DO carry semantic weight at our scale, but the interpretation is inverted from Trinity.**

Trinity's pool spans GPT-5 to Gemma-3-27B — capability variance dominates, so Verifier ≈ "ask the most capable available". Our open-source-only inner pool has narrower capability variance; the binding constraint is **cost-per-token-of-correctness**, not raw capability. Roles in our system collapse to:

> "Ask the **cheapest** model that can be trusted to correctly perform a given **role** for this task."

This is the routing policy our orchestrator already implements implicitly (frontdoor first; escalate to coder_escalation if frontdoor fails; fall back to architect_general only if escalation insufficient). The tri-role addition makes this implicit cost-aware policy explicit and learnable: the routing classifier outputs `(model, role)` rather than `(model)`, where `role` constrains the prompt template + the verification expectation.

**Concrete implication**: routing should NEVER blanket-default to architect_general because it's the most capable. Architect_general is reserved for tasks where the Thinker role is binding AND the cheaper Thinker (frontdoor) has insufficient quality on the task class. The role axis surfaces this cost-quality tradeoff for the routing policy to reason about — that's the value, not "use the smartest model".

### TR-1 Q3 — Surface area: per-call

**DECISION**: per-call (per orchestrator dispatch). NOT per-session, NOT both.

Trade-offs the user asked about:

- **Per-call** (per dispatch): every orchestrator call carries an independently-assigned role. A multi-turn session with 3 dispatches gets 3 independent role decisions. Most flexible, matches Trinity's per-turn evidence, matches the Q1 mapping (`frontdoor` switches between T/W/V across calls within the same session).
- **Per-session**: role fixed at session start, all dispatches inherit. Simpler, lower overhead, BUT incompatible with "frontdoor as Thinker on turn 1, frontdoor as Verifier on turn 5". Falsified by Q1 answer.
- **Both** (hybrid): session-level default + per-call override. Over-engineered; per-call already subsumes both.

Per-call is the only choice consistent with the Q1 mapping. TR-2.1 (RoleResult.role field) and TR-3.2 (classifier wired into routing.py) make this concrete: each call to `routing.py:_route_request` carries a role decision in its payload, defaulting to `worker` for backward compat.

### TR-1 Q4 — Termination semantics: deferred to autopilot exploration

User declined to over-specify upfront. **DECISION**: TR-4.4 implements Verifier-acceptance termination as a parallel mechanism to the existing review/escalation pipeline (NOT subsuming it). Operate them side-by-side initially. The autopilot evolutionary memory will discover whether V acceptance correlates with passing the existing review gate (in which case they collapse to one mechanism in a future iteration) OR whether they're orthogonal (the right outcome is "early-exit if V says ACCEPT AND existing review gate doesn't escalate").

Concretely:

- **TR-4.4** (Verifier-acceptance termination): if a Verifier turn returns ACCEPT, short-circuit subsequent dispatches within the same session — but ONLY if the existing review/escalation pipeline did not flag the prior Worker turn for escalation. The two signals AND together for early termination.
- **Telemetry from TR-3.3 onward** (shadow-mode role assignment): log both signals on every dispatch so autopilot has observational data to learn the correlation. After 1-2 weeks of data, decide whether to collapse the two mechanisms.

### TR-1 Q5 — Action-space encoding: decoupled

**DECISION**: decoupled `(L + 3)` flat logits — independent softmaxes over `L` LLMs and 3 roles. Matches Trinity's choice AND extends the existing `RoutingClassifier` infra minimally.

Rationale:

1. **Existing infra**: `epyc-orchestrator/orchestration/repl_memory/routing_classifier.py:50` defines `RoutingClassifier` as `Input(1031) → Dense(128) → Dense(64) → Dense(n_actions=6) → Softmax`. The 6-output softmax is over models. Decoupled extension: add a parallel `Dense(64) → Dense(3) → Softmax` role head sharing the Dense(64) trunk. Two independent softmaxes; combine at dispatch time. New parameter cost: (64 × 3) + 3 = 195 params. Negligible vs the 200K-param baseline.
2. **Joint `L × 3` encoding**: would change `n_actions` from 6 to 18. Every existing routing memory needs a `(model, role)` tuple label, NOT just `(model)`. Migration is heavier; backfill (TR-2.4) is harder because role inference for legacy memories is ambiguous. Ranking accuracy on 8K labels with 18 classes is sample-size-bounded.
3. **Trinity's evidence**: their decoupled design is what they ablated. Joint not tested. Default to the published-evidence version.
4. **Independent updates**: decoupled allows the role head to be retrained without retraining the model head, and vice versa. For instance, a new model can be added (model head expands by 1 logit) without touching the role head's weights. This is operationally important for the registry-driven model-pool.

### TR-1.2 decision — Verifier vs existing review pipeline

**DECISION**: parallel mechanism initially (per Q4 answer above), with TR-4.4 wiring V-acceptance to AND with the existing review gate for early termination. After 1-2 weeks of observational telemetry from TR-3.3, decide whether to collapse.

This DOES require updates to `routing-intelligence.md` (which owns the review trigger) — to flag that the review trigger now coexists with Verifier-acceptance, not replaces it. Cross-referenced below.

### TR-1.5 decision — feature flag

**DECISION**: yes, add `ROLE_AWARE_ROUTING` feature flag, default OFF. Required for the TR-5 A/B (`=1` vs `=0` paired comparison). Adding the flag now (TR-2 phase) avoids a retrofit. Toggle via env var `ORCHESTRATOR_ROLE_AWARE_ROUTING=1`.

### TR-1 sub-task closure

- [x] **TR-1.1** Role mapping table — written above (Q1 section).
- [x] **TR-1.2** Verifier vs review pipeline — parallel mechanism with eventual-collapse exploration via autopilot. See TR-1.2 decision section above.
- [x] **TR-1.3** Action-space encoding — decoupled `(L + 3)` flat logits, matches Trinity AND minimizes existing-infra change. See Q5 section above.
- [x] **TR-1.4** Open questions resolved — this whole section. ✅ DONE 2026-05-07.
- [x] **TR-1.5** Feature flag — yes, `ROLE_AWARE_ROUTING` default OFF.

**TR-1 GATE PASSED.** TR-2 (data layer) is unblocked.

### What TR-2 onward looks like under this taxonomy

- **TR-2.1**: Add `role: Literal["thinker", "worker", "verifier"]` to `RoleResult`, default `"worker"`.
- **TR-2.2**: Add `assigned_role` column to `episodic.db` `memories` table; new column NULLable for legacy rows. `parallel_embedder.py` writer + `episodic_store.py` reader.
- **TR-2.3**: Surface in `routing_classifier.py` (extend output to include role logits) + `q_scorer.py` (per-role Q-values? — to decide; default is "no, role is independent of Q") + retraining scripts.
- **TR-2.4**: Backfill via heuristic on existing 8K memories: review-flagged memories → V; first-pass non-escalated frontdoor calls → W; architect-class invocations → T. Acceptable to leave NULL where ambiguous.
- **TR-3** (heuristic classifier): rule-based mapping from request context (retry count, escalation flag, prompt features) to {T, W, V}. Lives at `src/classifiers/role_classifier.py`. Validates the schema before any ML.
- **TR-4**: dispatch wiring — per-call role drives prompt template + verification expectation. Verifier turns get a verification prompt; Thinker turns get a planning prompt.
- **TR-5**: paired A/B `=1` vs `=0` for ≥N=200 per arm per benchmark. Promote on Δ ≥ +2 points without regression > −1 point.
