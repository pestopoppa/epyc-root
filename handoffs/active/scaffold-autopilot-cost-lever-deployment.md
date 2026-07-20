# Scaffold CoT Cost-Lever — Autopilot Deployment (DESIGN Handoff)

**Status**: 🟡 DESIGN — architecture + task breakdown only. **NOT implemented; no code written; no measurement run.**
**Created**: 2026-07-06
**Owner**: unassigned (design ready for pickup)
**Kind**: episodic-memory-gated cost-lever deployment into autopilot's existing blended-cost optimization.

**Source study (all numbers below are OBSERVATIONS — MEASUREMENT.md, not decision-gating):**
- `handoffs/completed/gpu-cot-scaffold-sidecar.md` — full research arc (G1/G2/verifier/dense-generalization).
- `progress/2026-07/2026-07-06-cot-study-complete.md` — study close-out + the deployment implication paragraph.

> ⚠️ **LIVE-AGENT HAZARD.** A parallel agent is actively working the autopilot daemon right now (trials ~1197–1200, planner/critic changes landing). **Do not edit anything under `scripts/autopilot/` and do not restart the daemon while it is live.** Every `scripts/autopilot/*` reference below is a *read/verify* target for design, not an edit target, until the owning agent hands the daemon back. Coordinate before touching the planner action space.

---

## 1. Objective

Deploy the CoT "scaffold sidecar" as an **episodic-memory-gated cost lever** inside autopilot's existing multi-objective optimization. The scaffold offloads a large CPU-hosted beneficiary's expensive reasoning to a GPU-resident Qwable-v1 reasoner (35B-A3B distilled; IQ4_XS fits MI210 residency), then runs the beneficiary in no-think mode guided by the injected scaffold. The three pieces of work: **(a)** register the composite *scaffold-then-nothink* route as a first-class fallback lever; **(b)** fold its **blended GPU+CPU** cost into the cost/speed signals autopilot already scores; **(c)** let episodic memory **learn per-task-class when to apply it** — gated to the beneficiary-must-answer regime where Qwable standalone cannot directly take the request because the beneficiary owns tools/context/role constraints. This is a gating + accounting problem on top of infrastructure that already exists; it is **not** a new optimizer.

---

## 2. The finding in brief (OBSERVATION-grade)

From the GPU study (seed 42, production sampling, GPU-only, single-sample n=10–48 cells — all OBSERVATIONS):

- **Scaffold = robust, architecture-independent COST lever.** Caps the beneficiary's expensive-device (CPU-decode) tokens at ~**100–175** vs the **3,000–9,000** it burns reasoning on its own — a **20–50× CPU-decode-token reduction**, reasoning moved to the cheap GPU. Held across sparse-MoE 35B, dense-GDN 27B (176 vs 9041), and pure-dense gemma-31B (98 vs 3049).
- **Scaffold QUALITY benefit is HEADROOM-CONDITIONAL.** Rescues weak-and-overthinking beneficiaries (Qwen3.6-27B GPQA 6→9/10; sparse-MoE 35B 48→73%) but **no-ops already-saturated ones** (gemma-31B 8=8). ⇒ must be **gated**, applied only where the beneficiary's no-think path FAILS and it would otherwise over-reason.
- **Blended wall-clock objective (the thing to minimize at quality-parity):**
  ```
  T_scaffold = N_gen/r_GPU(gen) + N_gen/r_CPU_prefill(ben) + N_ans/r_CPU_decode(ben)
  T_ownthink = (N_reason + N_ans)/r_CPU_decode(ben)
  ```
  Scaffold wins when the beneficiary would over-reason (large `N_reason` on slow CPU decode) — exactly the weak-and-overthinking regime. Win is driven by the `r_GPU/r_CPU` ratio.
- **Verifier/selector (best-of-N) is MARGINAL (+2pp captured of an +8pp structural ceiling; errors are systematic not stochastic) and is explicitly NOT part of this deployment.**
- **Single-shot scaffold as a capability-*transplant* was FALSIFIED** on code (amplifier-not-substitute, arXiv:2605.28913). It is deployed here **only as a cost lever** in the gated regime, not as a general quality booster.
- **Qwable standalone is the primary reasoning route when allowed.** The GPQA standalone control ran after the scaffold reversal: Qwable standalone **77%** beat scaffold(Qwable→35B) **73%**, so the scaffold is a lossy fallback for beneficiary-must-answer cases, not the preferred way to use Qwable.

---

## 3. Architecture / integration points (each grounded in verified code)

Repo root for all paths: `/mnt/raid0/llm/epyc-orchestrator` (symlinked `/workspace/repos/epyc-orchestrator`).

### 3.1 Autopilot multi-objective safety gate — VERIFIED
- `scripts/autopilot/safety_gate.py:329-330`
  ```python
  def objectives(self) -> tuple[float, float, float, float]:
      return (self.quality, self.speed, -self.cost, self.reliability)
  ```
- `EvalResult` fields (`safety_gate.py:230-234`): `quality` (0-3, `fraction_correct*3`), `speed` (t/s — median-request in serial / aggregate-batch in concurrent; `speed_metric_mode` at :259), `cost` (**normalized 0-1**), `reliability` (fraction non-error).
- The 4D Pareto lives in `scripts/autopilot/pareto_archive.py` (and `src/autopilot_core/pareto_math.py`). `objectives()` is the tuple it ingests.
- **CRITICAL NUANCE (corrects the study's shorthand).** The study handoff (§"FORMAL OBJECTIVE", line 227) says the scaffold's blended cost "surfaces directly as the speed/cost axes." That is only *half* right, and the design must respect the distinction:
  - Pareto **`cost` is NOT wall-clock.** It is a normalized **memory/capacity `cost_tier`** average: `scripts/autopilot/eval_tower.py:1383-1385` → `cost = mean(cost_tier)/4.0`. `cost_tier` is a residency/capacity diagnostic (see `scripts/autopilot/program.md:123`, which *explicitly* states the old wall-occupancy proxy `sum(tokens/tps)` is **not** a live Pareto objective).
  - Blended GPU+CPU **wall-clock therefore enters via `speed` (t/s), not `cost`** — and only if the composite route is issued as a single timed request (eval_tower wraps each request in `elapsed = time.time() - start`, `eval_tower.py:1063,1135`, so an internal GPU pre-decode *would* be counted). But `speed = tokens/elapsed` blends tokens generated on two devices over one wall clock, so the raw t/s number is semantically muddy for a composite route. **See Task (b) — this is the core accounting design decision.**

### 3.2 Reward / cost model (episodic Q-value) — VERIFIED
- `orchestration/repl_memory/q_reward.py:22` `compute_reward(...)`; the study's `cost_ratio` claim is real:
  - `q_reward.py:90-93`: `expected_elapsed = tokens_gen / baseline_tps`; `cost_ratio = elapsed / expected_elapsed`; `cost_penalty = cost_penalty_lambda * max(0, cost_ratio-1)`.
  - Correctness-gated: applied **only when `reward > 0`** (`q_reward.py:75`) — i.e. minimize-cost-subject-to-correctness, matching the study's framing.
  - `baseline_tps` is per-**role** (`config.baseline_tps_by_role`, `q_reward.py:78`); `elapsed` prefers `generation_ms` over `elapsed_seconds` (`q_reward.py:82-86`).
  - Also present: memory-tier penalty (dim 3, `q_reward.py:102-106`, `memory_cost_by_role`), quality-gap penalty (dim 2, :95-100).
- **This is a *different* cost surface from §3.1** — it is the **episodic-memory reward** driving Q-values (QScorer), keyed on a single role's single-device wall-clock. **A scaffold request spans two devices (GPU gen_ms + CPU decode_ms), which `cost_metrics` does not natively represent.** The `cost_metrics` dict keys consumed are `tokens_generated`, `role`, `generation_ms`, `elapsed_seconds`, `regret`, `speedup_vs_teacher` (`q_reward.py:76-116`) — none carries a second-device term today. **See Task (b).**
- Config object: `orchestration/repl_memory/q_scorer.py` `ScoringConfig` (:613), `QScorer` (:690); registry-derived priors `registry_baseline_tps_by_role` (:521), `registry_memory_cost_by_role` (:566).

### 3.3 Episodic memory (where the gating policy lives) — VERIFIED
- `orchestration/repl_memory/episodic_store.py` — `EpisodicStore` (:136), `MemoryEntry` (:73) with `q_value` (default 0.5), `action_type`, `assigned_role`, `model_id`, and **`sub_decision`** (:97; intake-548 5-class taxonomy → `src/classifiers/subdecision_taxonomy.py`). Methods: `store` (:293), `retrieve_by_similarity(min_q_value=…)` (:522), `update_q_value` (:618), `count_by_combo` (:813).
- `orchestration/repl_memory/retriever.py` — `TwoPhaseRetriever` (:74); decision entry points `retrieve_for_routing` (:160), `retrieve_for_escalation` (:180), `retrieve_for_exploration` (:196), `retrieve_for_classification` (:214). `_scalarized_selection_score` (:46) blends `q_value` with a perf term. **This is the natural home for a `retrieve_for_scaffold_eligibility` decision** (or a new `sub_decision`/`action_type` value consumed by the existing routing retrieval).
- **Gating key** = task embedding + `sub_decision` (task-class) + **difficulty band** from `src/classifiers/difficulty_signal.py` (used already in routing, see §3.5). Episodic memory learns the Q-value of "apply scaffold" per (task-class, difficulty-band) cell.

### 3.4 Planner / action space + capability registry — VERIFIED (READ-ONLY)
- `orchestration/capability_registry.yaml` — one row per tunable lever. Kinds (`:20-26`): `env | flag | numeric | prompt | registry-field | restart-class`. **All rows are `promotion_state: placeholder`, `actionable_by: "gated:evidence-plane-ledger.md Phase 1"`.** The closest analog to the scaffold lever is `per_role_enable_thinking` (`:141`, `kind: prompt`, `surface: chat_template_kwargs.enable_thinking`, `applicator: config_post`, roles `[architect_general, coder_escalation, frontdoor]`, evidence `+33pp`).
- W4 promotion preconditions (`capability_registry.yaml:8-13`): (1) applicator wired, (2) range validated vs a measurement protocol, (3) `kill_condition` written in the row, (4) one shadowed trial passes attestation.
- Loader/validator: `src/registry/capability_registry.py` `load_capability_registry` (:215), `CapabilityRegistryError`. Compiler: `scripts/registry/compile_capability_registry.py`. Tests: `tests/unit/test_capability_registry.py`.
- Planner reads it: `scripts/autopilot/autopilot.py:54-56` imports `load_capability_registry`.
- Action handlers keyed by `action_type` in `scripts/autopilot/actions.py`: `_action_numeric_trial` (:475), `_action_prompt_mutation` (:950), `_action_seed_batch` (:391), `_action_gepa_optimize` (:1020). A new lever is exercised through a handler of the matching kind.
- **OPEN QUESTION (design fork).** The scaffold is *not* a pure `prompt` kwarg like `enable_thinking` — it requires a **preceding GPU generator call** whose output is injected before the beneficiary decodes. So it is a **composite route**, not a single chat-template toggle. Options: (i) model it as a new `kind` (e.g. `route-composite`) in the registry with a dedicated applicator; (ii) model it as a `prompt`-kind lever whose applicator triggers the two-stage path at the routing layer (§3.5). **Decide this with the daemon-owning agent before adding any registry row** (see CLAUDE.md "Agents & Automation": no index/registry changes via sub-agents without explicit operator approval).

### 3.5 Orchestrator routing / role layer (where the composite route attaches) — VERIFIED
- `src/api/routes/chat_pipeline/routing_decision.py` — `select_initial_route` (:64), `apply_failure_veto` (:103), `apply_ingest_triviality_guard(..., difficulty_band, ...)` (:152). Consumes `classify_and_route` (def in `src/classifiers/keyword_matcher.py`).
- `src/routing_bindings.py` — `BindingRouter.resolve(task_type) -> role` (:80), `prior_distribution` (:168). `src/roles.py` — `Role` enum (:68), `Tier` (:52).
- **Existing reasoning-effort lever the scaffold joins:** `src/graph/think_harder.py` — `_should_think_harder` (:80), `_build_think_harder_config` (:130). It already implements per-role ROI tracking (`_expected_think_harder_roi`, :29) and an effort ladder ("high ROI → larger token budget + **CoT prefix**", :134). **The scaffold-then-nothink composite is naturally one more rung on this effort axis** (nothink → think-budget → scaffold-then-nothink → ownthink → escalate). Attaching here reuses the ROI accounting instead of building a parallel one.
- Beneficiary no-think path: `enable_thinking` is applied in the backends — `src/backends/llama_server.py`, `src/chat_completions_roles.py`, `src/registry/registry_loader.py`. Assistant-prefix / context-advisory injection modes are native to `llama-server` (`continue_final_message`), per the study.
- **OPEN QUESTION.** There is no existing two-stage/"sidecar" composite executor in `src/`. The grep for `continue_final_message|prefill_assistant|scaffold|sidecar|two_stage` hit only tangential files (features, draft_cache, placement_policy). **The composite executor (call GPU reasoner → inject → call beneficiary nothink, as one timed request) does not exist yet and must be built** (Task a). Verify against `src/api/routes/chat_pipeline/` before choosing the attach point.

### 3.6 GPU-reasoner hosting (Qwable on MI210) — VERIFIED
- MI210 HIP `llama-server` binary **exists**: `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip/bin/llama-server`.
- Qwable weights **staged**: `/mnt/raid0/llm/models/Qwable-v1-GGUF/Qwable-v1.IQ4_XS.gguf` (17.6 GB) and `Qwable-v1.Q8_0.gguf` (34.4 GB).
- **Quiet-host server/chat evidence added 2026-07-17**: `epyc-inference-research/data/qwable_reasoning_economics/qwable_quality_quiet_20260717T0645Z/` confirms bounded runner cleanup and sequential MI210 arms. IQ4 standalone returned valid fenced JSON at **99.27 t/s**, Q8 standalone returned valid fenced JSON at **103.04 t/s**, strict IQ4 prompt-only JSON returned exact JSON at **99.44 t/s**, and CPU IQ4 baseline returned strict JSON at **13.82 t/s**. Scaffold/selector stubs were parseable but semantically placeholder/arbitrary, so they are **not** deployment evidence.
- **Schema-mode acceptance closed for the harness boundary 2026-07-17**: after fixing `qwable_reasoning_economics_runner.py` so execute mode sends the planned payload, `epyc-inference-research/data/qwable_reasoning_economics/qwable_schema_fixed_quiet_20260717T0718Z/` returned exact strict JSON under top-level `json_schema` at **64.55 t/s**. This closes bounded schema acceptance, not task-quality acceptance.
- **Expanded standalone-routing quality gate closed 2026-07-17**: `epyc-inference-research/data/qwable_reasoning_economics/qwable_task_quality_iq4_plain_expanded_final_20260717T184136Z/` passed `18/18` on MI210 plain at **106.65 t/s**; `qwable_task_quality_iq4_ngram_expanded_final_20260717T184106Z/` passed `18/18` on MI210 `ngram-mod` at **106.66 t/s**; `qwable_task_quality_iq4_cpu_expanded_final_20260717T184207Z/` passed `18/18` on CPU plain at **15.96 t/s**. Treat plain reasoning-off IQ4_XS as the preferred standalone route; ngram is safe but neutral on this slice.
- **CPU standalone verifier artifact checked 2026-07-19**: `epyc-inference-research/data/qwable_reasoning_economics/qwable_cpu_verifier_standalone_20260719T021216Z/summary.compact.json` reports execute `exit_code=0`, `cpu_iq4_baseline` and `verifier_selector_stub` both `status=ok` on `--device none -ngl 0`, decode `13.9607/14.0744 t/s`, `finish_reason=stop`, and post-run ROCm `No KFD PIDs currently running`. The compact artifact has since been tracked in `epyc-inference-research`; raw run logs remain research scratch unless explicitly retained.
- **The GPU reasoner is NOT in `orchestration/model_registry.yaml`** — the only `device:` entry is `device: cpu` (:235); no mi210/gpu/sidecar role. In the study the MI210 server was launched ad-hoc (:8801/:8802).
- **No launcher script exists** for the MI210 reasoner (find over `epyc-orchestrator/scripts` + `epyc-inference-research/scripts` for `*mi210*` / `*hip*server*` returned nothing).
- **Managed-service template (the pattern to copy):** `scripts/server/orchestrator_stack.py` `start_whisper()` (:1836) and `start_handoff_dashboard()` (:1889) — both are non-CPU-model stack-managed services; whisper reuses a launcher script from another repo (`:1846`) and health-probes a port. A `start_scaffold_reasoner()` following this shape (launch MI210 `llama-server`, health-probe, register `ProcessInfo`) is the concrete hosting task.
- **Cross-cutting:** MI210 residency contends with any other GPU role (`fable5-window2-findings-05b` owns the residency budget / Gate R). Co-residency numbers from the study: Qwable-IQ4 (17.6) + qwen35 beneficiary (35.2) = 53 GB fits 64; Qwable-Q8 (34.4) + qwen35 (35.2) = 70 GB does **not** — Q8 co-resides only with the gemma beneficiary or runs sequentially.

---

## 4. Prioritized task list (dependency-ordered)

Each task = concrete file(s) + acceptance check. Flip `- [ ]` → `- [x] … ✅ YYYY-MM-DD` on completion (checkbox discipline, CLAUDE.md).

### Phase 0 — Coordinate & host
- [ ] **T0.1 — Coordinate with the live autopilot agent.** Confirm the daemon is idle/handed-back before any `scripts/autopilot/*` or registry edit. Get operator approval for the capability-registry row (CLAUDE.md: no registry changes via sub-agents without explicit operator request). *Accept:* written go-ahead recorded here.
- [x] **T0.1a — Close bounded Qwable strict-output/schema harness evidence.** Quiet-host runner evidence landed for IQ4/Q8 standalone format, strict IQ4 prompt JSON, CPU baseline, and top-level `json_schema`; scaffold/selector stubs remain non-deployable. ✅ 2026-07-17
- [x] **T0.1b — Close first Qwable IQ4_XS vs Q8_0 task-quality slice.** Bounded server/chat runner passed `6/6` on MI210 for IQ4_XS (`112.15 t/s`) and Q8_0 (`113.62 t/s`), and `6/6` on CPU for IQ4_XS (`17.11 t/s`) and Q8_0 (`13.66 t/s`); no Q8-only quality advantage in the small deterministic slice. ✅ 2026-07-17
- [x] **T0.1c — Close expanded Qwable IQ4_XS standalone-routing quality gate.** Calibrated `default+expanded` suite passed `18/18` on MI210 plain (`106.65 t/s`), MI210 `ngram-mod` (`106.66 t/s`, neutral), and CPU plain (`15.96 t/s`). Research routing now prefers plain reasoning-off IQ4_XS standalone; scaffold remains beneficiary-must-answer fallback. ✅ 2026-07-17
- [x] **T0.1d — Check CPU standalone verifier artifact.** Artifact `qwable_cpu_verifier_standalone_20260719T021216Z` is execution-clean (`exit_code=0`), CPU-only (`--device none -ngl 0`), cleanup-clean (`No KFD PIDs currently running`), and records strict/fenced JSON responses for the baseline and verifier-selector stub arms. The compact artifact is tracked; raw run logs remain scratch unless explicitly retained. ✅ 2026-07-19
- [ ] **T0.2 — Stand up the GPU reasoner as a stack-managed service.** Add `start_scaffold_reasoner()` to `scripts/server/orchestrator_stack.py` mirroring `start_whisper()` (:1836): launch `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip/bin/llama-server` with `Qwable-v1.IQ4_XS.gguf`, pick a stable port, health-probe. Add a `scaffold_reasoner` entry to `orchestration/model_registry.yaml` with `device: gpu`. *Accept:* `orchestrator_stack.py status` shows the reasoner healthy; a manual `/v1/chat/completions` to its port returns a `<think>` block. *(No autonomous llama-bench — speed characterization needs a per-run go-ahead, `feedback_speed_verify_via_llama_bench`.)*

### Phase 1 — Composite route (the mechanism)
- [ ] **T1.1 — Build the scaffold-then-nothink composite executor.** New path (verify attach point in `src/api/routes/chat_pipeline/`): call `scaffold_reasoner` → inject its output (assistant-prefix `continue_final_message` **or** system/context advisory — the study's mode answer is distribution-conditional, so make it a parameter) → call the beneficiary with `enable_thinking=false` (via the backend path in `src/backends/llama_server.py`). Issue as **one timed request** so `elapsed_s` (`eval_tower.py:1063`) captures both stages. *Accept:* one composite request returns the beneficiary's answer with the scaffold visible in the trace; beneficiary decode-token count is in the ~100–175 band the study observed.
- [ ] **T1.2 — Attach it to the reasoning-effort ladder.** Wire the composite as one rung in `src/graph/think_harder.py` (`_build_think_harder_config`, :130) rather than a parallel mechanism, so per-role ROI tracking (`_expected_think_harder_roi`, :29) already covers it. *Accept:* `think_harder` can select `scaffold_then_nothink` as an effort level for an eligible role.

### Phase 2 — Blended cost accounting (the objective)
- [ ] **T2.1 — Decide + implement the blended-cost representation.** Resolve the §3.1/§3.2 split: (i) ensure the composite request's total wall-clock (GPU gen + CPU prefill + CPU decode) lands in the `speed` axis via the single-timed-request design (T1.1); AND (ii) extend the episodic `cost_metrics` contract in `orchestration/repl_memory/q_reward.py` to carry a **second-device term** (GPU `generation_ms`) so `compute_reward`'s `cost_ratio` reflects blended cost, not just the beneficiary's single-role wall-clock. Options: a composite pseudo-role with a blended `baseline_tps`, or an additive GPU-cost term. *Accept:* a scaffold trial and an ownthink trial on the same task produce `cost_ratio`/`speed` values whose ordering matches the study's blended-cost inequality (scaffold cheaper in the over-reason regime).
- [ ] **T2.2 — Verify the Pareto `cost` axis is not misused.** Confirm the scaffold does **not** get mis-scored on the memory `cost_tier` axis (`eval_tower.py:1383-1385`) as if it were free — the GPU residency is a real capacity cost. Decide whether the reasoner's residency should raise the composite route's `cost_tier`. *Accept:* documented decision + `cost_tier` assignment for the composite route.

### Phase 3 — Episodic gating (learn when)
- [ ] **T3.1 — Add the scaffold-eligibility signal to episodic memory.** Introduce a `sub_decision`/`action_type` value (e.g. `scaffold_eligible`) in `src/classifiers/subdecision_taxonomy.py` + `orchestration/repl_memory/episodic_store.py` and a `retrieve_for_scaffold_eligibility` (or reuse `retrieve_for_routing`, `retriever.py:160`) keyed on task embedding × `difficulty_band` (`src/classifiers/difficulty_signal.py`). *Accept:* store/retrieve round-trips a scaffold Q-value for a (task-class, difficulty) cell; unit test alongside `tests/unit/test_episodic_store.py`.
- [ ] **T3.2 — Reward wiring so Q-values learn the gate.** Ensure the composite route's outcome feeds `q_reward.compute_reward` (T2.1) so `update_q_value` (`episodic_store.py:618`) reinforces "apply scaffold" only where it wins (correct **and** blended-cost-cheaper). *Accept:* replay of a synthetic weak-and-overthinking trace drives the scaffold Q-value up; a saturated-task trace drives it down (matches the headroom-conditional finding).

### Phase 4 — Offline replay + registry
- [ ] **T4.1 — Offline replay to learn the gating policy from existing traces.** Use the read-only journal replay path (`scripts/autopilot/journal_snapshot_replay.py` → `src/autopilot_core/journal_snapshot_replay.py`, `build_snapshot_replay_diagnostic`) and/or `scripts/autopilot/core_v2_select.py` to replay historical task traces and estimate, per task-class, where nothink fails + the beneficiary over-reasons (the eligible regime) — **without** live daemon perturbation. *Accept:* a per-task-class eligibility table with support counts, written to a report under `orchestration/reports/`.
- [ ] **T4.2 — Register the lever (operator-gated).** After T0.1 approval, add a `scaffold_then_nothink` row to `orchestration/capability_registry.yaml` (kind per the §3.4 fork decision; `promotion_state: placeholder`; `kill_condition` written; roles = the eligible beneficiaries). Validate with `scripts/registry/compile_capability_registry.py` + `tests/unit/test_capability_registry.py`. *Accept:* loader accepts the row; row stays `placeholder`/gated until the measurement gate (§8) passes.

### Phase 5 — Measurement gate + rollout
- [ ] **T5.1 — Codified measurement protocol for the deploy gate** (see §8). *Accept:* protocol-id assigned; quality-parity + blended-cost recipe written, operator-approved.
- [ ] **T5.2 — Canary / shadow rollout.** Shadowed trials on the eligible task-classes only; verify no regression on the saturated/nothink-works classes; then promote the registry row past `placeholder` per W4 preconditions. *Accept:* canary meets the §8 gate; W4 (1) applicator wired, (2) range validated, (3) kill_condition, (4) shadowed trial attested — all satisfied.

---

## 5. Dependency graph

```
T0.1 (coordinate/approve) ─┬─> T0.2 (host GPU reasoner)
                           │        │
                           │        v
                           │      T1.1 (composite executor) ──> T1.2 (effort ladder)
                           │                 │
                           │                 v
                           │      T2.1 (blended cost) ──> T2.2 (cost_tier decision)
                           │                 │
                           │                 v
                           │      T3.1 (episodic signal) ──> T3.2 (reward wiring)
                           │                 │
                           │                 v
                           │      T4.1 (offline replay) 
                           └─────> T4.2 (register lever, needs T0.1 approval + T2/T3)
                                             │
                                             v
                                   T5.1 (measurement protocol) ──> T5.2 (canary/rollout)
```
- **Blocking chain:** T0.2 → T1.1 → {T2.1, T3.1} → T4 → T5. T1.1 is the linchpin (nothing downstream measures without the composite request).
- T4.1 (offline replay) can run in parallel once T3.1's signal shape is fixed; it does **not** need the live daemon.
- T4.2 and T5.2 are **operator-gated** and must not proceed while the parallel autopilot agent holds the daemon.

---

## 6. Cross-cutting concerns

- **GPU-reasoner residency/contention.** The MI210 is a shared, budgeted resource; `fable5-window2-findings-05b-mi210-inference-architecture.md` owns the residency plan (Gate R). Adding a resident reasoner competes with any other GPU role. Respect the co-residency arithmetic (§3.6): IQ4_XS co-resides with a qwen35 beneficiary; Q8 does not.
- **Quality-parity gating (no regression where nothink already works).** The headroom-conditional finding is the whole point: the lever must be **inert on saturated/strong-nothink task-classes** (gemma-31B 8=8). The gate (§8) MUST include a no-regression check on those classes, not just a win check on the weak ones (`feedback_per_suite_gate_resolution_artifact`, `feedback_eval_saturation_masks_model_gap`).
- **Measurement-trust boundary.** The keep/deploy decision needs a **protocol-id**, not the study's observations (§8). MEASUREMENT.md and the eval tower are human-amendment-only.
- **Two distinct cost surfaces (do not conflate).** Pareto `cost` = memory `cost_tier` (§3.1); episodic reward `cost_ratio` = per-role wall-clock (§3.2); blended GPU+CPU wall-clock naturally lands on `speed` and on an *extended* `cost_metrics`. Getting this wrong makes the scaffold look free (it isn't — GPU residency + prefill tax are real).
- **Interaction with existing spec-dec/MTP routing.** The scaffold is orthogonal to MTP/NEXTN (text-level transfer, no vocab/KV sharing — study §"MTP is irrelevant"). It sits on the *reasoning-effort* axis (`think_harder`), not the draft/spec-dec axis. Verify the two levers compose (a scaffolded nothink request on an MTP-enabled beneficiary) rather than fight.
- **Live-parallel-agent hazard (autopilot).** Restated: no `scripts/autopilot/*` edits, no daemon restart, no registry/index change, while the owning agent is active. Design now; land under coordination.
- **Verifier/selector is out of scope.** Marginal on this stack (systematic not stochastic errors). Do not bundle it into this deployment.

---

## 7. Measurement / deploy gate

Per `/workspace/CLAUDE.md` (Measurement & Claims) and `MEASUREMENT.md`:

- **All study numbers in §2 are OBSERVATIONS** (single-sample, GPU-only, seed 42) — usable for hypotheses, **never** to gate keep/deploy/promote. A decision-gating claim = `(metric, protocol-id, n/reps, date, host-attestation ref)`.
- **Quality-parity gate → P-QUAL-T1** (`MEASUREMENT.md:25-35`, the production autopilot trial-gate instrument card): **paired (same questions both arms), N ≥ 100/arm** for a production-role decision (the X-MAS lesson — a 20pp effect at N=25 collapsed to 4pp at N=100), every failure classified by reason, flag-state attestation in the run header. Arms: `nothink` vs `scaffold_then_nothink` vs `ownthink`, on **both** an eligible (weak-and-overthinking) and a saturated task-class.
- **Blended-cost / speed gate → P-BENCH-1/P-BENCH-2** (`MEASUREMENT.md:19-23`) via `bench_canonical.sh` / `canonical_recipe.py`, **operator-approved, never hand-typed**, with the composite request's GPU+CPU wall-clock captured end-to-end. Axis = `task_rate` (questions/eval-wall-hour) per findings-05.
- **Deploy rule:** promote the registry row past `placeholder` only when (a) P-QUAL-T1 shows quality-parity-or-better on the eligible class **and** no regression on the saturated class, (b) the blended-cost protocol shows a real wall-clock win in the eligible regime, and (c) W4 preconditions (`capability_registry.yaml:8-13`) are met. Journal rows carry `protocol_id`.

---

## 8. Reporting instructions

- After each task: flip its `- [ ]` → `- [x] … ✅ YYYY-MM-DD` here; work discovered mid-flight gets its own `- [ ]` line. Prose-only status is invisible to the handoff dashboard (CLAUDE.md checkbox discipline).
- Log via `scripts/utils/agent_log.sh` (`agent_task_start`/`agent_task_end`); chronology to `progress/2026-07/`.
- Numbers stay **OBSERVATION** until run through the §7 codified recipes with operator approval; label them so in any update.
- The master-handoff-index pointer to this doc is added by the **main session**, not here (per task scope). Do not edit any index/master-index from this workstream.
- On promotion, fold the residency planning into `fable5-window2-findings-05b` (Gate R) rather than duplicating it.

---

## 9. Key file locations (verified implementation targets)

| Concern | Path : symbol | Verified |
|---|---|---|
| 4D Pareto objective tuple | `scripts/autopilot/safety_gate.py:329` `objectives()` | ✅ |
| EvalResult fields / cost | `scripts/autopilot/safety_gate.py:230-234`; `eval_tower.py:1383-1385` (`cost=mean(cost_tier)/4`) | ✅ |
| Pareto archive | `scripts/autopilot/pareto_archive.py`; `src/autopilot_core/pareto_math.py` | ✅ |
| Request wall-clock (speed) | `scripts/autopilot/eval_tower.py:1063,1135` (`elapsed = time.time()-start`) | ✅ |
| Episodic reward / cost_ratio | `orchestration/repl_memory/q_reward.py:22,90-93` | ✅ |
| Reward config / QScorer | `orchestration/repl_memory/q_scorer.py:613,690` | ✅ |
| Episodic store | `orchestration/repl_memory/episodic_store.py:73,136,293,522,618` | ✅ |
| Episodic retrieval policy | `orchestration/repl_memory/retriever.py:74,160` | ✅ |
| Task-class taxonomy | `src/classifiers/subdecision_taxonomy.py`; `episodic_store.py:97` `sub_decision` | ✅ |
| Difficulty band | `src/classifiers/difficulty_signal.py` | ✅ |
| Capability registry (lever) | `orchestration/capability_registry.yaml` (`per_role_enable_thinking` :141); loader `src/registry/capability_registry.py:215` | ✅ |
| Planner reads registry | `scripts/autopilot/autopilot.py:54-56` | ✅ |
| Action handlers | `scripts/autopilot/actions.py:391,475,950,1020` | ✅ |
| Routing decision | `src/api/routes/chat_pipeline/routing_decision.py:64,152` | ✅ |
| Reasoning-effort ladder | `src/graph/think_harder.py:29,80,130` | ✅ |
| nothink / enable_thinking | `src/backends/llama_server.py`; `src/chat_completions_roles.py` | ✅ |
| Offline replay | `scripts/autopilot/journal_snapshot_replay.py`; `src/autopilot_core/journal_snapshot_replay.py`; `scripts/autopilot/core_v2_select.py` | ✅ |
| GPU reasoner binary | `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip/bin/llama-server` | ✅ |
| Qwable weights | `/mnt/raid0/llm/models/Qwable-v1-GGUF/{Qwable-v1.IQ4_XS.gguf, Qwable-v1.Q8_0.gguf}` | ✅ |
| Managed-service template | `scripts/server/orchestrator_stack.py:1836` `start_whisper()` | ✅ |
| Prod model registry | `orchestration/model_registry.yaml` (only `device: cpu` :235 — **no GPU role yet**) | ✅ |

### Open questions (could not be verified — resolve during build, do not guess)
1. **Composite-route representation in the capability registry** — new `kind: route-composite` vs `prompt`-kind-with-two-stage-applicator (§3.4). Operator/daemon-owner decision.
2. **No existing two-stage/sidecar executor in `src/`** — the composite request path (§3.5) must be built; the exact attach point in `src/api/routes/chat_pipeline/` needs verification against the current pipeline.
3. **No MI210 reasoner launcher script exists** — must be written for T0.2 (whisper's launcher lives in `epyc-inference-research`; decide where the reasoner launcher lives).
4. **Blended `cost_metrics` extension** — whether to add a GPU `generation_ms` term to `q_reward.compute_reward` or model a composite pseudo-role with a blended `baseline_tps` (§3.2, T2.1).
5. **Injection mode** — assistant-prefix vs context-advisory is distribution-conditional in the study; make it a route parameter, characterize per task-class during T5.
