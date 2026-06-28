# AutoPilot Planner-Hint Distillation from Orchestrator Handoffs

**Status**: PHASE 1 SOURCE + DRY-RUN READY; PHASE 2A HELPER LANDED — no rows written, no restart. Orchestrator `dd4c572d` adds the curated seed file, dry-run/apply/purge CLI, and tested StrategyStore purge/rebuild support. Orchestrator `412392c3` completes the pre-apply identifier audit by requiring explicit `bind_status`/`bind_identifiers` for deterministic planner rows. Orchestrator `bac4db17` adds inert `StrategyStore.retrieve_conventions(...)` support for planner-usable convention rows. Phase 1 `--apply` still needs operator review; Phase 2b-2h wiring remains restart-gated.
**Created**: 2026-06-28
**Priority**: MEDIUM (cheap leverage on planner decision quality; prevents wasted trials)
**Categories**: autopilot, routing/optimization, strategy-store
**Depends on**: W4/W6 readiness clearance + N13/N14 kernel-era fence (E5 eras) settled — for Phase 2 restart only. Phase 1 source/dry-run has no dependency; Phase 1 `--apply` is no-inference but newly written FAISS-backed rows are not guaranteed visible to an already-running AutoPilot process until the strategy store is refreshed or AutoPilot restarts.
**Related**: [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md), [research-evaluation-index.md](research-evaluation-index.md), and the ~40 source handoffs cited in the inventory below.

---

## Problem / Motivation

We have 111 active handoffs plus a large completed/archived corpus. Much of that knowledge — both *runnable hypotheses* and *hard-won negative results* — could refine AutoPilot's planner decisions if injected into the strategy store as hints, **even for tasks we never intend to run manually**. The highest-value injections are the **negatives** ("X is a baseline artifact", "Y is net-negative", "Z is foreclosed by architecture"): they stop the optimizer from spending trials re-exploring falsified regimes.

A prior session established the mechanism (write to the strategy store with `metadata.seeded_by="operator"`; see existing 2026-06-25 precedent rows). `seed_campaign` is new metadata for this campaign, not an existing precedent field. This handoff is the **full audit + curated inventory + safe execution design** built on top of that mechanism.

## Survey result (what's hintable)

Of 111 active handoffs (≈100 real items after removing nav indices):

| Category | Count | Meaning |
|---|---|---|
| **A — Directly seedable hypotheses** | ~22 (~20%) | Maps onto a planner channel and is eval-tower-scorable. |
| **B — Context-only hints** | ~43 (~39%) | Not runnable (needs C++/kernel, new model, infra, governance) but carries a durable insight/constraint that should bias planner choices. |
| **C — Not hintable** | ~42 (~38%) | Pure kernel/build/infra/governance/measurement/data-collection + nav indices. |

→ **~65 of ~111 (~58%) carry signal worth writing into the strategy store.** A mining pass over `handoffs/completed/` + `handoffs/archived/` added ~18 more decision-grade negatives (Tranche B below).

## Decisive mechanism finding (constrains the whole design)

Strategy-store retrieval is wired into **only one path** today:
- **Reader:** `epyc-orchestrator/scripts/autopilot/actions.py:271` `_build_mutation_context()` → called only by `_action_prompt_mutation` and `_action_code_mutation` (**both PromptForge**). Query = `f"{target} {mutation_type} {description}"`, `k=3`, **no `species=` filter**.
- **NumericSwarm (Optuna), StructuralLab (flag chooser), Seeder, EvolutionManager never consult retrieved strategies.**

**Implication:** as wired, "hint the planner via its memory" is a **PromptForge-only channel**. A guardrail such as "don't toggle the EP flag" injected as a row would *not* be seen by StructuralLab when it picks flags. Reaching the other planners requires the Phase 2 code change.

#### Per-species reach (the crux — read before seeding)
This is the single most important fact in this handoff: **a row written to the strategy store only changes behaviour if the species that owns the relevant lever actually reads the store.** Today only one does.

| Species | Owns lever | Reads strategy store today? | Effect of a seeded row now | What it takes to make hints bind |
|---|---|---|---|---|
| **PromptForge** | prompt/code `.md` mutations | **Yes** — `actions.py:271` `_build_mutation_context()` | **Live immediately** (top-k injected into the mutation LLM prompt) | nothing — already wired |
| **Seeder** | per-role Q-value seeds | No | Dormant | Phase 2b — inject `retrieve_for_journal(..., species="seeder")` into the seed prompt |
| **StructuralLab** | boolean feature-flag toggles | No | Dormant | Phase 2c — consume `convention` rows as a **flag denylist** before selection |
| **NumericSwarm** | Optuna numeric surfaces | No | Dormant | Phase 2d — consume `convention` rows to **suppress dead surfaces** / narrow bounds |
| **EvolutionManager** | distillation | No (write-only) | Dormant | out of scope |

**Consequences for this plan:**
- Seeding now is still correct: PromptForge hints (Tranche A prompt rows + any guardrail that constrains prompt/code mutations) become available to new or refreshed StrategyStore readers, and the `structural_lab`/`numeric_swarm`/`seeder` rows are written with correct species so they light up the moment Phase 2 lands — **dormant, not wasted.** This is intentional, not a bug. Do not claim guaranteed live PromptForge visibility for the already-running AutoPilot process unless a refresh/restart is performed.
- **Prose ≠ enforcement for deterministic choosers.** Even after Phase 2, injecting a guardrail as free-text for StructuralLab/NumericSwarm is weaker than a hard bind: an Optuna sampler or a flag chooser won't "read and obey" prose. That's why Phase 2c/2d turn `entry_type=convention` rows into a **flag denylist** and **surface suppression** at the decision point, rather than relying on prompt injection. Prose injection is reserved for the LLM-driven species (PromptForge, Seeder).
- A future reader must not assume "I seeded a StructuralLab guardrail, so the planner won't toggle that flag." Until Phase 2c is merged and activated by a restart, StructuralLab is blind to it. The corresponding correction has been written to memory ([[feedback_seed_autopilot_via_strategy_store]]).

### Other verified facts (drive correctness)
- **Writer = `StrategyStore.store(...)` in `orchestration/repl_memory/strategy_store.py` (~L632).** It updates the `strategies` row **and** the FTS5 table (~L698–706) **and** the FAISS index (~L684–686). **Raw SQL INSERT skips FTS5/FAISS → the row is never retrieved. Always use `store()`.** `_embed()` falls back to a hash embedding if the embedder is offline, so `store()` never fails and FAISS is always populated.
- **Idempotency:** `store()` returns early if `entry_id` already exists; no content-hash dedup. Use deterministic `entry_id`s.
- **Provenance precedent:** 2 existing rows have `metadata.seeded_by="operator"` + `seeded_reason`, `entry_type` ∈ {`convention`,`pattern`} (2026-06-25). Mirror that operator-seeded provenance and add a new purgeable `seed_campaign` tag for this campaign.
- **`source_trial_id`** is never NULL — set to the live `trial_counter` from `orchestration/autopilot_state.json` at write time.
- **`strategy_conventions` / `strategy_validity` tables are empty scaffolding** — not a usable channel. Guardrails live in `strategies` as `entry_type="convention"`.
- **Retrieval scoring:** `rrf * (0.5 + validity) * staleness`. New rows: validity≈0.5, staleness=1.0 (no penalty), not quarantined. Hybrid FAISS + FTS5 BM25 + RRF; BM25 honors `species=` if passed.

## Operator decisions (recorded)
1. **Reach:** *wire all four species* to consult the store so hints reach every planner (Phase 2).
2. **Timing:** *seed now, defer restart* — inject rows now (active for PromptForge, dormant for the rest); land the wiring + restart on the next coordinated restart after W4/W6 clears and the kernel-era (E5) baseline is settled.
3. **This session:** persist as this handoff. **Execute nothing.**

---

## Execution plan

### Phase 1 — Seed (no inference; safe mid-run write)
Writing mid-run is safe — AutoPilot writes `journal-frontier-*` rows every trial via the same `store()` API (SQLite concurrency). The write itself does not require an orchestrator restart or llama inference. Visibility is narrower: the running AutoPilot process loads `StrategyStore()` once and keeps its FAISS index in memory, so new rows are guaranteed visible only to new/refreshed store readers or after AutoPilot restarts. `numeric_swarm`/`structural_lab`/`seeder` rows remain dormant until Phase 2.

- [x] **1a.** Author curated data file `epyc-orchestrator/scripts/autopilot/operator_seed_strategies.yaml` — one entry per inventory row (schema below). Done in orchestrator `dd4c572d`: `44` rows (`green=16`, `guardrail=26`, `frozen=2`).
- [x] **1b.** Author `epyc-orchestrator/scripts/autopilot/seed_operator_strategies.py`:
  - For each row call `StrategyStore.store(...)` with `entry_id=f"opseed-{tranche}-{slug}"`, `species`, `entry_type`, `title`, `description`, `insight`, `generalized_content=insight`, `source_trial_id=<live trial_counter>`, `evidence_trial_ids`, and `metadata={seeded_by:"operator", seeded_date:<apply-date>, seed_campaign:"operator-handoff-distillation", seeded_reason, source_handoff, confidence}`.
  - Modes: `--dry-run` (default; prints rows + summary, writes nothing), `--apply`, `--purge-campaign operator-handoff-distillation`. Log via `scripts/utils/agent_log.sh`.
- [x] **1c.** Pre-finalize: verify exact identifier strings — flag names against `config_applicator.py` `HOT_SWAP_FEATURES`; numeric surface ids against `species/numeric_swarm.py` — so guardrail keys bind for Phase 2. Done in orchestrator `412392c3`: `seed_operator_strategies.py --audit-identifiers --json` reports `ok=true`, `blocking_count=0`, `row_count=44`; non-current deterministic rows are explicitly marked `future` or `context` rather than silently passing as live bindings.
- [ ] **1d.** **Operator reviews `--dry-run` output, then approves `--apply`** (standing approval rule for store/index writes).
- [ ] **1e.** Phase-1 verification (read-only): (i) row-count delta == N; (ii) `json_extract(metadata_json,'$.seed_campaign')='operator-handoff-distillation'` count == N; (iii) FTS5 row count and FAISS `ntotal` each +N for a freshly opened store; (iv) retrieval probe on a fresh `StrategyStore()` — `store.retrieve_for_journal("frontdoor prompt conciseness brevity", k=5)` returns the reasoning-compression row; repeat for 2–3 others; confirm none quarantined. Do not call this a live PromptForge proof unless the running AutoPilot process has refreshed/restarted.

**Canonical campaign tag:** `operator-handoff-distillation`. The older provenance plan used `handoff-distillation-2026-06-27`; that name is superseded and must not be used for apply/purge/progress tracking.

**Apply contract:** expected insert set is the deduped operational YAML set, currently `44` rows (`16` green hypotheses, `26` guardrails, `2` frozen constraints). Apply only through `StrategyStore.store()` via `seed_operator_strategies.py --apply`, never raw SQL. Immediately after apply, prove row-count delta, campaign metadata count, FTS5 mirror count, FAISS `ntotal`, and fresh-store retrieval probes. Treat already-running AutoPilot visibility as unproven until a StrategyStore refresh or restart.

Curated row schema (YAML):
```yaml
- slug: ep-flag-baseline-artifact
  tranche: guardrail            # green | guardrail | frozen
  species: structural_lab       # prompt_forge|structural_lab|numeric_swarm|seeder|all
  entry_type: convention        # convention = guardrail/frozen ; pattern = green hypothesis
  title: "Expert-parallelism is not a standalone production win"
  description: "expert_parallelism flag — throughput claim"   # name the lever so BM25 + Phase-2 denylist match
  insight: "Do NOT toggle expert_parallelism as an optimization; the +56/+100% wins were baseline artifacts (vs --numa distribute / mmap=1). Canonical = +1.6% noise except Qwen3.6-35B-A3B Q8 (+17%, bit-exact)."
  evidence_trial_ids: []
  source_handoff: handoffs/completed/large-moe-expert-parallelism-completed-through-2026-05-28.md
  seeded_reason: "Prevent re-exploration of falsified EP throughput claim"
  confidence: high
```
> Content rule: every `description`/`insight` must name the concrete lever (flag name, surface id, role) so BM25 retrieval and the Phase-2 denylist key off real identifiers.

### Phase 2 — Wire all planners (staged; lands on next coordinated restart)
Planner-orchestration only → **outside the MEASUREMENT trust boundary** (safe to change). Activates on restart; do **not** restart until W4/W6 strict readiness passes (`--require-seq-cutover --require-w6-audit`) and the N13/N14 E5 era fence is settled.

- [x] **2a. Shared helper:** either add a small `StrategyStore.retrieve_conventions(species, k)` convenience wrapper or reuse the existing quarantine-aware entry-type helpers; avoid creating a parallel convention system. Done in orchestrator `bac4db17`: `StrategyStore.retrieve_conventions(...)` reads `strategies.entry_type='convention'` rows with species-plus-`all` filtering, folded-journal exclusions, quarantine/min-validity filtering, staleness diagnostics, and deterministic limits. It is inert until Phase 2 callers opt in.
- [ ] **2b. Seeder (LLM-driven):** replicate `_build_mutation_context()` retrieval (`actions.py:244–276`) in the seed_batch handler — `retrieve_for_journal(query, k, species="seeder")` injected into the seed prompt.
- [ ] **2c. StructuralLab (deterministic flag chooser):** consume `convention` rows to build a **flag denylist** — exclude any flag named in a "do NOT toggle / NO-GO / frozen" convention from the experimentable set before selection (`species/structural_lab.py` vs `HOT_SWAP_FEATURES`). Hard bind — prose alone won't stop a deterministic chooser.
- [ ] **2d. NumericSwarm (Optuna):** consume `convention` rows to **suppress dead surfaces** (e.g. `moe_spec_budget` no-consumer, op-coalesced-barriers neutral) and optionally narrow bounds (`species/numeric_swarm.py`) before surface/trial selection.
- [ ] **2e. PromptForge:** optionally inject `entry_type=convention` guardrails unconditionally (not only RRF-ranked) so hard constraints always appear.
- [ ] **2f. Planner prompt assembly:** if dead flags/surfaces should disappear before the planner proposes them, also thread convention-derived denylist/suppression summaries into the planner-visible feature-flag/action availability blocks; execution-time filtering alone is weaker and can create avoidable critic rejections.
- [ ] **2g. Tests:** extend the planner suite (~39 tests) — a "do not toggle EP" convention removes `expert_parallelism` from StructuralLab candidates; a dead-surface convention suppresses that NumericSwarm surface; seeded prose appears in Seeder context; planner-visible availability reflects denylisted levers; **no interaction with the W6 gaming-alarm logic**.
- [ ] **2h. Activation:** restart via `orchestrator_stack.py` / autopilot start using the settled safe preflight (registry attest + `stack_change_pipeline.py check --run-promotion-gate`), coordinated with the kernel-era baseline state.

### Rollback / rewind-purge (required)
Per the standing rule that a clean AutoPilot rewind must also purge the strategy store (injected rows otherwise re-inject narrative):
- [x] Implement a real purge/rebuild path before applying rows. `seed_operator_strategies.py --purge-campaign operator-handoff-distillation` must delete `opseed-*` rows **and** their FTS5 entries, then rebuild/compact FAISS from remaining rows. If the store lacks a delete API, add one or document and test a full reindex recipe. Run purge **while AutoPilot is stopped**. Done in orchestrator `dd4c572d`; `StrategyStore.purge_strategy_campaign()` is covered by `test_purge_strategy_campaign_removes_retrieval_mirrors`.
- [x] Record the campaign tag `operator-handoff-distillation` in [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) so any future rewind purges it. Done 2026-06-28 in the A10 index-refinement pass.

Purge proof: after `--purge-campaign operator-handoff-distillation`, verify campaign metadata count is `0`, no `opseed-*` rows for the campaign remain, FTS5 has no matching row ids, FAISS `ntotal` equals the rebuilt remaining-row id map, and fresh-store retrieval probes for campaign-specific phrases no longer return campaign entries.

---

## Curated row inventory (the YAML content)

Legend for `species`: PF=prompt_forge, SL=structural_lab, NS=numeric_swarm, R=routing/seeder, ALL=all.

### Tranche A — green hypotheses (`entry_type=pattern`)
| slug | species | insight (one-line) | source handoff |
|---|---|---|---|
| agent-file-compression | PF | Serve compressed agent-file variants (mild→medium) per role; score obedience/quality vs uncompressed. | agent-file-prose-compression |
| reasoning-brevity-trimr | PF | Add conciseness/TrimR brevity to worker prompts; ~37% token cut at comparable accuracy on easy problems — gate on accuracy delta. | reasoning-compression |
| meta-harness-contrastive | PF | Feed contrastive (k_success=2,k_failure=2) traces to the PromptForge proposer; HLE fidelity stays diagnostic-only. | meta-harness-optimization |
| repl-verbosity-prompts | PF | A/B REPL verbosity/suggestion prompts to cut turns/tokens at zero accuracy loss (gated on S4 Omega A/B). | repl-turn-efficiency |
| context-folding-alpha | NS | Tune compaction dual-objective alpha toward 0.0 (retrieval-weighted); +5pp precision offline — validate live. | context-folding-progressive |
| kbrag-retrieval-weights | NS | Tune kb-rag recency_w∈[0.1,0.3], rerank_w, FTS5 lexical weight; optimize recall@10 (recency_w0.3_s90 = 0-miss baseline). | internal-kb-rag |
| per-role-reasoning-budget | NS | Tune per-role reasoning budget_tokens; budget=0 fails on Qwen3.5 hybrid SSM — **pure-MoE roles only**. | per-request-reasoning-budget |
| per-role-sampling-temp | NS | Per-role generation temperature 0.1–0.3 + fixed seed; architect_general needs chat-completions for enable_thinking=false. | prompt-construction-determinism |
| tool-output-compression | NS | Tune tool-output compression aggressiveness per role; A/B on REPL turns + token cost (+4pp shown). | tool-output-compression |
| triattention-keepratio | NS | Sweep Expected-Attention keep_ratio + layer_weights per role; persist Pareto profiles. | triattention-kv-selection |
| deep-research-mode | SL | Toggle deep_research_mode ON for research-like queries; promote only if rubric uplift ≥+5pp, no sentinel regression, ≤2× tool calls. | minddr-deep-research-mode |
| force-mode-edit | SL | A/B force_mode=edit one-shot edit-transaction for read-first coding edits; gap is protocol not model. | multi-file-coding-completion-capability / batched-edit-parallel-apply |
| dcp-pre-assembly | SL | dcp_pre_assembly: cut tokens but worsened p50 latency in first A/B — flip only on a quality-scored clean-window win. | delegation-context-preassembly |
| tool-use-sentinel-lane | SL | Enable tool-use sentinel lane so trials exercise tools; gate native OpenAI-tools seam ON/OFF. | tool-use-eval-contract |
| xmas-winner-table | SL | Enable X-MAS function-axis routing via xmas_winner_table under incumbent-constrained cheap-first; gate on held-out decision. | x-mas-text-routing |
| retrieval-risk-routing | SL | Stage retrieval-risk routing control (MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED) as enforce-vs-shadow canary; threshold tunable. | routing-intelligence |

### Tranche B — negative guardrails (`entry_type=convention`)
*Active-handoff negatives:*
| slug | species | guardrail | source |
|---|---|---|---|
| no-mmap-refuted | SL | no_mmap private node-local weights refuted on v6+iqk for frontdoor/ingest/vision_escalation — keep shared-mmap. | numa-private-weights-quarter-roles |
| ccd-vestigial | SL | GGML_CCD_* env vars are vestigial no-ops under prod OpenMP build — never propose enabling. | intra-process-tensor-parallel-decode / cpu-kernel-env-flags-inventory |
| decode-bw-saturated | ALL | CPU decode is BW-saturated; no kernel/numeric lever wins on batch=1 quantized decode — don't propose decode-kernel levers. | cpu-shape-specialized-gemv-decode / tidar |
| cross-family-drafter | SL | Cross-family drafters are tokenizer-incompatible (Qwen3-1.7B invalid for qwen35); only same-family drafts valid. | gpu-drafter-mi200-investigation |
| gdn-forecloses-specdec | SL | GDN/Delta-Net hybrid (Qwen3.6-27B, Qwen3.5) forecloses CPU spec-dec — recurrent layers block draft-verify. | qwen36-27b-cpu-feasibility / qwen35-architecture |
| moe-spec-budget-noconsumer | NS | moe_spec_budget has no live consumer (frontdoor zero spec-dec) — don't tune until frontdoor spec-dec is live + α measured. | moe-spec-cpu-spec-dec-integration |
| dual-half-negative | SL | Dual-half (Half0∥Half1) concurrency is negative ~0.5× (shared-weight BW contention); quarters are the granularity. | dynamic-stack-concurrency / project memory |
| slot-promotion-negative | SL | Slot-promotion dispatcher (--spec-numa-quarters) net-negative on Qwen3.6 + small drafter; default-off, documented reopen criteria. | project_slot_promotion_shelved |
| ep-needs-canonical | SL | Expert-parallelism flag is bit-correct but its prod win was a baseline artifact — no toggle without a fresh canonical matrix. | large-moe-expert-parallelism |

*Completed/archived negatives:*
| slug | species | guardrail | source |
|---|---|---|---|
| batch1-decode-exhausted | ALL | batch=1 decode is exhausted (compute-idle AND per-thread-BW-saturated); no FLOPS lever exists. | fable5-findings-06-kernel-and-concurrency |
| coalesced-barriers-neutral | NS | Op-coalesced barriers measured neutral (+0.19%) under canonical OMP; MUL_MAT wdata race precludes aggressive coalescing. | cpu4-deferred-avenues-design-note |
| work-stealing-negative | SL | Global work-stealing for expert balancing −2.3% (single-atomic contention at 96t dominates) — don't re-attempt for single-user. | cpu-dynamic-moe-load-balancing |
| tree-spec-hybrid-negative | SL | Tree-spec / per-path-replay / checkpoint-clone all net-negative on Delta-Net (−53…−66%); keep `!has_recurrent` guard. | ssm-hybrid-acceleration / tree-speculation-numa-drafting |
| dflash-cpu-not-viable | SL | DFlash block-diffusion on CPU Q4_K_M loses decisively to AR (13.0 vs 36.5 t/s) — not viable CPU. | dflash-block-diffusion-speculation |
| paper-tree-shapes-no-transfer | NS | Paper EAGLE-3 tree shapes are GPU-bound; don't assume they transfer to CPU heap-spec at 96t. | mab-tree-shape-selector |
| nway-not-pairwise | R | N-way cross-role concurrency safety ≠ pairwise; defend with admission gating until per-workload re-measurement. | cross-role-nway-contention-matrix |
| intra-process-tp-negative | R | Intra-process tensor parallelism regresses −26% (4×48t frontdoor); single-instance routing is the baseline. | intra-process-tensor-parallel-decode (completed) |
| canonical-baseline-only | ALL | Never compare to mmap=1-warmed or `--numa distribute` baselines (artifacts); canonical = taskset 96t + mmap0 + interleave=all. | cpu-optimization-thesis-pause |
| numa-prewarm-mandatory | ALL | NUMA interleave prewarm is mandatory on cold cache; cold-start collapses to 24–35 t/s vs 55–70 post-prewarm. | numa-page-cache-prewarm |
| five-rep-for-small-delta | ALL | Require ≥5-rep canonical (+PPL gate) for any <5% delta claim; 3-rep shows noise as signal. | fable5-findings-01-measurement-and-integrity |
| gemv-kernel-bw-limited | NS | CPU2 8×8 AVX-512BW GEMV kernel: +31.8% @1t but +1–3% @12–96t (BW-saturated) — operationally narrow. | cpu-shape-specialized-gemv-decode (completed) |
| reap-pruning-arch-specific | R | REAP MoE pruning is architecture-specific (router saliency required) — does not generalize to dense/SSM/other MoE. | reap-moe-expert-pruning |
| heavy-model-lock | R | Heavy-model inference requires a global cross-process serialization lock; concurrent heavy models cause 600s timeouts. | infra-seeding-regression |
| rope-base-position-tradeoff | NS | Raising RoPE base aids token- but provably hurts position-distinguishing >32K — only extend when workload tolerates. | yarn-context-extension-research |
| ernie-q4-text-corrupt | SL | ERNIE-Image-Turbo Q4_K_M corrupts in-image text; keep Q8 for any text-to-image role. | ernie-image-turbo-evaluation |
| disagg-wrong-regime | SL | Prefill/decode disaggregation win-regime is multi-tenant/long-context — opposite our single-user regime; xGMI tax worsens it. | numa-prefill-decode-disaggregation |

### Tranche C — frozen / adjudicated (`entry_type=convention`, phrased "frozen until X")
| slug | species | constraint | source |
|---|---|---|---|
| routing-expansion-frozen | R | learned-routing / retrain-routing / tri-role / decision-aware routing expansion FROZEN until a replay shows ≥5% routing regret (last = 0.00%); keep DAR-2 ON. | learned-routing-controller / retrain-routing-models / tri-role-coordinator-architecture / decision-aware-routing |
| web-research-rerank-nogo | SL | web_research_rerank is NO-GO: representative sample showed 0% irrelevant pages (<20% threshold) — do not enable. | colbert-reranker-web-research |

---

## Cross-cutting concerns
- **Trust boundary:** never seed anything touching the Pareto objective / eval tower / scoring / era rows (human-amendment-only). Tranche C rows are constraints, **not** "go" hypotheses — they must stay `convention` so they never seed a trial.
- **W6 gaming alarm:** Phase 2 changes how trials are chosen; tests must confirm no interaction with the audit/gaming-alarm logic.
- **Era hygiene:** Phase 2 restart must respect the live `pareto_exclude_before_ts` (E5 fence) so injected hints don't reopen pre-v6 comparisons.

## Key files
- New: `epyc-orchestrator/scripts/autopilot/operator_seed_strategies.yaml`, `.../seed_operator_strategies.py`
- Phase 2 edits: `.../actions.py`, `.../autopilot.py` prompt-assembly/availability blocks, `.../species/structural_lab.py`, `.../species/numeric_swarm.py`, planner tests. `orchestration/repl_memory/strategy_store.py` Phase 2a helper exists as of orchestrator `bac4db17`.
- Reuse (don't reinvent): `StrategyStore.store()/retrieve()/retrieve_for_journal()`; existing quarantine-aware entry-type helpers; `_build_mutation_context()` (`actions.py:244`); `HOT_SWAP_FEATURES` (`config_applicator.py`); numeric surfaces (`species/numeric_swarm.py`).

## Reporting instructions
After each phase, update this handoff's checkboxes + Status, append a dated note to `progress/2026-06/`, and (Phase 1e / 2g) record verification evidence. On completion, move to `handoffs/completed/` and extract any durable findings to the wiki. Index entry is active in `master-handoff-index.md` as A10/MED after the 2026-06-28 audit/refinement pass.

## Audit note — 2026-06-28

Read-only audit of this handoff and `~/.claude/plans/caveat-on-a-distributed-wilkinson.md` found the design actionable and worth folding into the A queue, with three corrections now reflected above:

- Phase 1 is no-inference and safe for a mid-run write, but not guaranteed live-visible to the already-running AutoPilot process because `StrategyStore()` and its FAISS index are loaded once at startup.
- `seed_campaign` is new purge metadata; existing operator-seeded rows prove `seeded_by="operator"` / `seeded_reason`, not campaign tagging.
- Phase 2 should avoid a duplicate PromptForge enforcement layer, reuse existing strategy-store helpers where possible, and include planner prompt assembly if the goal is to keep dead flags/surfaces out of proposed actions before critic/dispatcher rejection.

## Implementation note — 2026-06-28

Orchestrator `dd4c572d` implemented the Phase 1 source/dry-run slice without applying rows to the live store:

- `scripts/autopilot/operator_seed_strategies.yaml` contains `44` deterministic seed rows (`16` green hypotheses, `26` guardrails, `2` frozen constraints).
- `scripts/autopilot/seed_operator_strategies.py --json` is dry-run by default and reported `before_count=1374`, `after_count=1374`, `would_insert_count=44`, `inserted_count=0`, `source_trial_id=1031`.
- `StrategyStore.purge_strategy_campaign()` plus `rebuild_search_indexes()` provide the required rewind purge path, including FTS5 and FAISS mirror rebuild.
- Validation: `uv run pytest tests/unit/test_strategy_store.py -q` -> `42 passed`; `uv run ruff check scripts/autopilot/seed_operator_strategies.py orchestration/repl_memory/strategy_store.py tests/unit/test_strategy_store.py` -> pass; `git diff --check` -> pass.

No `--apply` was run. The exact identifier audit is now closed by the 2026-06-28 follow-up below; remaining Phase 1 gates are operator review/approval, apply, and post-apply retrieval verification.

## Identifier audit note — 2026-06-28

Orchestrator `412392c3` closes Phase 1c:

- `operator_seed_strategies.yaml` now records `bind_status` and `bind_identifiers` for every StructuralLab/NumericSwarm seed row.
- `seed_operator_strategies.py --audit-identifiers` imports live `HOT_SWAP_FEATURES` and `SURFACES`, fails live rows that no longer bind, and reports explicitly documented `future`/`context` rows separately.
- Validation: `uv run python scripts/autopilot/seed_operator_strategies.py --audit-identifiers --json` -> `ok=true`, `blocking_count=0`, `finding_count=29`; dry-run still reports `before_count=1374`, `after_count=1374`, `would_insert_count=44`, `inserted_count=0`.
- Test coverage: `uv run pytest tests/unit/test_seed_operator_strategies.py tests/unit/test_strategy_store.py -q` -> `44 passed`; `uv run ruff check scripts/autopilot/seed_operator_strategies.py tests/unit/test_seed_operator_strategies.py tests/unit/test_strategy_store.py` -> pass.

Remaining gates are operator review/approval, `--apply`, and post-apply retrieval verification on a fresh `StrategyStore()`.

## Current dry-run review packet — 2026-06-28

The current operator-review packet was regenerated while AutoPilot was live at
trial `1035`; no rows were written:

- `uv run python scripts/autopilot/seed_operator_strategies.py --json` ->
  `campaign=operator-handoff-distillation`, `row_count=44`,
  `before_count=1374`, `after_count=1374`, `would_insert_count=44`,
  `inserted_count=0`, `existing_ids=[]`, `source_trial_id=1035`,
  species counts `prompt_forge=4`, `numeric_swarm=11`, `structural_lab=19`,
  `seeder=5`, `all=5`.
- `uv run python scripts/autopilot/seed_operator_strategies.py
  --audit-identifiers --json` -> `ok=true`, `blocking_count=0`,
  `finding_count=29`.
- Validation: `uv run pytest tests/unit/test_seed_operator_strategies.py
  tests/unit/test_strategy_store.py -q` -> `44 passed`; `uv run ruff check
  scripts/autopilot/seed_operator_strategies.py
  tests/unit/test_seed_operator_strategies.py tests/unit/test_strategy_store.py`
  -> pass.

This is sufficient for operator review. It is not an approval or apply event;
Phase 1d/1e remain open.

## Phase 2a helper implementation — 2026-06-28

Orchestrator `bac4db17` landed the shared convention retrieval helper without
changing live planner behaviour:

- `StrategyStore.retrieve_conventions(...)` returns planner-usable
  `strategies.entry_type='convention'` rows, not the separate MDL
  `strategy_conventions` compression table.
- Species callers receive rows for their own species plus global `all` rows.
- The helper applies folded-journal evidence exclusions, quarantine filtering,
  optional `min_validity`, context-hash staleness diagnostics, and deterministic
  `limit` truncation.
- Validation: GitNexus impact on the existing retrieval path was LOW
  (`retrieve` impactedCount `4`; `retrieve_for_journal` impactedCount `3`);
  `uv run pytest tests/unit/test_strategy_store.py -q` -> `46 passed`;
  `uv run ruff check orchestration/repl_memory/strategy_store.py
  tests/unit/test_strategy_store.py` -> pass.

Phase 2b-2h remain open. No seed rows were applied and AutoPilot was not
restarted.

### Phase 2 sidecar audit — 2026-06-28

Read-only Phase 2 audit confirmed the next live-behaviour surfaces:

- Startup/default-off activation is the safest shape. Do not add live file
  watchers, polling, or mid-run registry/YAML rereads for this hint path.
- High-attention planner-loop touch points are
  `scripts/autopilot/autopilot.py` `_build_feature_flags_block`,
  `_configured_numeric_surfaces`, `CONTROLLER_PROMPT_TEMPLATE`, and
  `_run_loop_inner`.
- Numeric suppression must update both the planner-visible surface list and the
  validation mirror in `scripts/autopilot/controller_io.py`
  `_configured_numeric_surfaces` / `_ACTION_SCHEMAS["numeric_trial"]` /
  `validate_single_variable`.
- Species-specific touch points are `Seeder.run_batch`,
  `StructuralLab.flag_schema` / `propose_flag_experiment`,
  `NumericSwarm.suggest_trial`, and PromptForge prompt builders only if Phase
  2 elects to add unconditional convention guardrails.
- Minimal Phase 2 test set should cover strategy-store exclusions, controller
  numeric validation, action quota surfaces, structural flag validation,
  controller template rendering, seeder YAML helpers, and PromptForge/GEPA only
  if mutation-path hinting changes.

## Provenance
Full design rationale + the verbatim two-phase plan: `~/.claude/plans/caveat-on-a-distributed-wilkinson.md` (this session, 2026-06-28). Survey + mechanism findings produced by read-only code/handoff analysis; no system state was modified.
