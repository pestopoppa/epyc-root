# LOLLMS Smart Router Dataset — Deep-Dive (intake-687)

**Date**: 2026-06-12
**Intake**: intake-687
**Source**: https://huggingface.co/datasets/ParisNeo/lollms_smart_router_dataset
**License**: Apache-2.0 (464 rows, 446 kB)
**Prior verdict**: worth_investigating — "evaluate as cold-start/eval data for the blocked routing retrain — requires a relabel step from its generic public-model taxonomy to our 5 EPYC roles."
**Refined verdict**: **worth_investigating → reframe.** The *dataset* is NOT cold-start data for our retrain (wrong surface entirely — text-SFT vs embedding-MLP; wrong taxonomy; 464 rows vs our 8K–174K). The transferable asset is the **TTT generation METHODOLOGY** (synthetic, candidate-list-conditioned routing-label generation via multi-LLM prompting), which is only marginally useful to us because our blocker is *embeddings*, not *labels*. Net: **low-priority reference, not a drop-in.** Do not gate the retrain on it.

---

## TL;DR / Refined recommendation

- Our blocked retrain (`retrain-routing-models.md`) is **not** label-starved in the way the intake note implies — it is **embedding-starved**. The live `episodic.db` already holds **52K–53K routing memories with canonical role labels**; what's missing is their BGE embeddings (FAISS reset; `reembedded.npz` is a frozen 2026-04-15 snapshot 100% disjoint from live db). The fix is a BGE re-embed run, not more labels.
- Our classifier consumes a **1024-dim BGE embedding ⊕ task-type one-hot ⊕ log(ctx_len) ⊕ has_images = 1031-d feature vector**, labeled with a **canonical role index** (5 active of 8), Q-value-weighted. The lollms dataset is **raw text** (`task_prompt` with an enumerated candidate-model list → `task_solution` = model index + NL justification). These are **different surfaces**: lollms is generative-router SFT data; ours is a discriminative embedding-MLP. **The orchestrator has no generative/SFT router surface today** (grep-confirmed), so lollms feeds nothing that exists.
- The **win, if any, is the METHODOLOGY not the DATA**: lollms' value is demonstrating that a usable routing-label set can be *synthesized* by prompting multiple LLMs with `(task, candidate-list-with-capabilities)` and parsing `(index, rationale)`. We could regenerate an **EPYC-role-labeled** set the same way. But we don't need synthetic labels — we have 52K organic ones. So even the methodology is a "nice-to-have for cold-start of a NEW surface," not a current unblock.
- **Concrete next action**: do **not** wire lollms into the retrain. Keep it as a cited reference under "generative-router cold-start" should we ever add an SFT/text-router surface (e.g., a future "router LLM" head distinct from the MLP). **Gate**: only revisit if (a) we decide to build a generative router surface, OR (b) a brand-new role with zero organic memories needs cold-start labels and IRT-stratified seeding (Phase 5) proves insufficient.
- The single genuinely portable artifact is the **`task_prompt` format** (candidate-list-with-capability-descriptions + few-shot example + difficulty-tiered rationale). If we ever generate our own EPYC TTT set, copy that prompt scaffold; do not copy the data.

---

## What it is

**Schema** (2 string columns, train split, 464 rows):

| Column | Type | Content |
|---|---|---|
| `task_prompt` | string (284–1.08k chars) | A task plus an **enumerated candidate-model list** `{index} - {provider}/{model} {capability description}`, often with a one-shot example and an instruction to "choose the best model for this prompt: '…'". |
| `task_solution` | string (108–1.03k chars) | `{model_index} Explanation: {NL justification}` — the selected index followed by a free-text rationale. |

**Example row (coding)** — `task_prompt`: *"Given the following list of models: 0 - mistral-7b-v3.0 … 3 - deep-seek/deep-seek-v2 [coding-specialized] … Example: …'Write a function to calculate the factorial…' → deep-seek-v2 (option 3) …"*; `task_solution`: *"3 Explanation: This task involves implementing a simple coding project … deep-seek/deep-seek-v2 is specifically designed for coding tasks …"*.

**Candidate model taxonomy** (generic public models, NOT ours): tiny (`tinyllama-1B`, `distilbert`), small/medium (`mistral-7b`, `llama-3.2-8B`), large/advanced (`gpt-3.5`, `claude-2`, `gpt-4`), specialized (`deep-seek-v2`/`codellama` for code, `gpt-4-vision` for vision, `cohere/summarize-xlarge`, `whisper`). The candidate list **varies row-to-row** — it is baked into each `task_prompt`, so the label space is *prompt-relative indices*, not a fixed role set.

**Label distribution**: not published explicitly. Observed pattern: simple tasks → low indices (tiny/small), general tasks → mid indices (medium/large), complex/specialized → high indices. The signal that *does* transfer is the **difficulty-tier → capability-tier matching heuristic** encoded in the rationales.

**Generation method**: produced by the **lollms "TTT Dataset Builder"** app using a **multi-LLM prompting technique** — multiple LLMs are prompted to emit `(task, candidate-list)` → `(index, rationale)` examples. Two reference routers were fine-tuned on it: `ParisNeo/Llama-3.2-1B-Instruct-lollms-smart-router` and `…-3B-…` (both Nov 2024, single-digit downloads). These are **generative SFT** routers (an instruct LLM emitting the index+rationale), confirming the dataset's intended consumer is a text-in/text-out model, not an embedding classifier.

---

## Fit to EPYC

### Our actual surface (from code)

`scripts/graph_router/extract_training_data.py` + `train_routing_classifier.py` + `orchestration/repl_memory/routing_classifier.py`:

- **Feature vector**: `concatenate([emb(1024), task_type_onehot(5), norm_ctx_len(1), has_images(1)])` = **1031-d**. `emb` is a **BGE-large-en-v1.5** embedding of the task objective (CLS-pooled, per `orchestrator_stack.py:862`).
- **Model**: 2-layer numpy MLP, `1031 → 128 → 64 → 8`, Q-value-weighted cross-entropy, ~200K params, <0.1 ms inference. Serves as a fast first pass before FAISS KNN fallback.
- **Labels**: `CANONICAL_ACTIONS = [frontdoor, architect_general, architect_coding, coder_escalation, worker_explore, worker_math, worker_vision, ingest_long_context]` — **fixed 8-class role set** (5 with data). Raw episodic action strings are normalized to these via `ACTION_NORMALIZATION`.
- **Reported result**: 92% val acc (4 classes, 2026-04-15 snapshot).

### Why lollms does NOT slot into `retrain-routing-models.md`

1. **Wrong feature surface.** Our MLP never sees text — it sees a BGE embedding. lollms ships *text prompts*. To use a lollms row you would have to (a) strip the candidate-list/justification scaffolding to recover the bare task, (b) BGE-embed it, (c) discard `task_solution`'s index and **re-derive** an EPYC role label. At that point you've thrown away everything lollms-specific and kept only "a task string," of which we already have 52K organic, in-distribution examples.
2. **Wrong taxonomy, and not a simple table.** The intake note's "relabel from generic public-model taxonomy to our 5 roles" understates the problem: the lollms label is a **prompt-relative index into a per-row candidate list**, not a stable model identity. There is no fixed `gpt-4 → architect_general` mapping because the candidate list changes every row, and the capability tiers (tiny/small/large/specialized) don't line up with our role semantics (frontdoor is a *cheap-first MoE generalist*, not "tiny"; architect_general is a 122B reasoner; worker_explore is a 26B MoE). A mapping table would be lossy and largely guesswork.
3. **Wrong scale and provenance.** 464 synthetic rows vs our 8K–174K organic Q-weighted memories. Even as held-out *eval* data, 464 self-generated, taxonomy-mismatched rows can't validate a classifier trained on EPYC-role embeddings.
4. **The blocker is embeddings, not labels.** Per `learned-routing-controller.md` Operational Findings (2026-05-21): live db has 52,993 orphan routing memories with **no FAISS embeddings**; `reembedded.npz` is a frozen, 100%-disjoint 2026-04-15 snapshot. The retrain is gated on **one BGE re-embed run** (`repair_episodic_embeddings.py --repair` or `start --repair-embeddings`), not on acquiring more labels. lollms adds nothing to that critical path.

### Dataset vs methodology

- **Dataset value: ~nil for our current MLP.** It feeds a generative-router surface we do not have.
- **Methodology value: low-but-real, for a hypothetical NEW surface.** The transferable idea is: *synthesize routing labels by prompting LLMs with a candidate-list-with-capabilities and parsing `(index, rationale)`.* This is exactly the kind of cold-start generator we'd want **if** we ever (a) build a generative/text router, or (b) onboard a role with zero organic memories. But note we already have two cheaper cold-start levers in flight that dominate it for our embedding-MLP surface: **Phase 5 IRT-stratified seeding** (50 prompts to baseline a new specialist) and seeding scripts under `epyc-inference-research/scripts/benchmark/`. The lollms TTT method is the generative-router analogue of those — useful only on the surface we don't have.

---

## Decision gates & exact next steps

1. **Do NOT add lollms to the retrain pipeline.** No `extract_training_data.py` change, no relabel table. Rationale: surface + taxonomy + scale mismatch; the retrain blocker is embeddings.

2. **Unblock the retrain the right way (independent of intake-687).** The actual next action for `retrain-routing-models.md` is the BGE re-embed, which needs operator inference approval (per `feedback_no_concurrent_inference`):
   ```bash
   # OPERATOR — re-embed orphan routing memories, rebuild FAISS, then retrain.
   cd /mnt/raid0/llm/epyc-orchestrator
   python3 scripts/maintenance/repair_episodic_embeddings.py --diagnose-only   # confirm orphan state
   python3 scripts/maintenance/repair_episodic_embeddings.py --repair          # ~5–15 min, 8× parallel BGE
   python3 scripts/graph_router/extract_training_data.py
   python3 scripts/graph_router/train_routing_classifier.py
   ```
   intake-687 is irrelevant to every line of this.

3. **Park lollms as a generative-router cold-start reference.** IF a future decision adds a generative/text router surface (an instruct LLM emitting role+rationale, distinct from the MLP), THEN revisit lollms as (a) a **prompt-format template** for `task_prompt` and (b) a worked example of TTT synthesis. **Gate to re-open**: a handoff explicitly scoping a generative router surface exists. Until then, no action.

4. **IF (and only if) we ever need EPYC-role-labeled cold-start data for a zero-memory role** and IRT-stratified seeding (Phase 5) is shown insufficient, regenerate our own set via a TTT-style pipeline. **Concrete plan (analysis only — do not run):**
   - Build a fixed EPYC candidate list (stable, not per-row): `0 - frontdoor (Qwen3.6-35B-A3B; cheap-first MoE generalist, chat/short tasks); 1 - architect_general (Qwen3.5-122B; deep reasoning, multi-domain); 2 - architect_coding (coding-specialist reasoner); 3 - coder_escalation (hard-code escalation target); 4 - worker_explore (gemma4-26B-A4B MTP; mid-tier exploration/summarize)`.
   - Prompt a panel of our own deployed models (multi-LLM, mirroring TTT) with `(real task drawn from seeding/eval pool, fixed candidate list above)` → parse `(role_index, rationale)`.
   - Convert each to a training row by **BGE-embedding the bare task** and emitting `(1031-d feature, role_index)` so it lands in *our* surface directly — i.e., adapt the methodology to our embedding-MLP rather than copying lollms' text format.
   - **Operator command sketch** (DO NOT RUN — needs inference approval): a new `scripts/calibration/ttt_role_seed.py` reading from the seeding pool, calling deployed model ports, BGE-embedding via the stack embedder on :8090, writing a `training_data_ttt.npz` in the existing schema. This is *new code*, gated behind a future handoff and explicit approval — flagged here per the "never dismiss a source without flagging" rule, not proposed for this session.
   - **Decision gate for this path**: only if a new role has <500 organic memories AND Phase 5 IRT cold-start (`learned-routing-controller.md` P5.2) misses its ≤5% agreement gate. Two conditions, both must hold.

5. **Eval-data gate.** lollms is unusable as held-out eval for our classifier (taxonomy mismatch). Do not add it to any eval tower. No action.

---

## Risks & contradicting evidence

- **Label noise / synthetic provenance.** lollms labels are LLM-generated, not outcome-verified. Our pipeline is the opposite: Q-values are TD-updated *outcomes*. Importing synthetic labels would inject un-grounded signal into an outcome-grounded store. Strong reason to keep it out.
- **Taxonomy mismatch is structural, not cosmetic.** The label is a per-row index into a varying candidate list — there is no stable model→role map to translate through. Any "relabel table" would be a fresh human judgement per capability tier, i.e., we'd be authoring labels, not translating them.
- **464 is too small** for training (vs 8K–174K) and too mismatched for eval. Even the reference Llama-3.2-1B/3B routers fine-tuned on it have single-digit downloads — no external validation of quality.
- **Contradicting the intake note's framing**: the note calls the retrain "data-starved (gated on accumulating ~500+ routing examples)" and positions lollms as bootstrap data. The handoff header says that, but the code + Operational Findings show the live db **already has 52K+ labeled routing memories** — the real gate is the missing **embeddings** (FAISS reset), not example count. So the premise that makes lollms attractive ("we're short on routing examples") does not hold against current state. This is the single most important correction.
- **Methodology is genuinely interesting, just not on the critical path.** Risk of *over*-dismissing: if we ever build a generative router, the TTT prompt scaffold and multi-LLM-panel synthesis are a real head start. Captured in gate 3/4 so it isn't lost.

---

## Cross-refs

- `handoffs/active/retrain-routing-models.md` — the blocked handoff. Real blocker = BGE re-embed of 52K orphan memories, not label count.
- `handoffs/active/learned-routing-controller.md` — feature schema (1031-d BGE⊕task-type⊕ctx⊕images), 92% val acc, Phase 5 IRT cold-start (the *right* cold-start lever for our surface), and the Operational Findings (2026-05-21) documenting the embedding-orphan blocker.
- `handoffs/active/decision-aware-routing.md` — DAR phases; verifier-vs-threshold framing (Phase 6) for any future correctness-gate surface.
- `handoffs/active/routing-and-optimization-index.md` — coordination index for routing work.
- `scripts/graph_router/extract_training_data.py`, `train_routing_classifier.py`, `orchestration/repl_memory/routing_classifier.py` — the discriminative surface lollms would have to feed (and doesn't).
- Memory: `project_learned_routing_controller.md` (Phase 1 done, 92% val acc), `feedback_no_concurrent_inference` (all BGE/inference runs need operator approval), `feedback_dont_dismiss_creative_uses` (basis for keeping the TTT methodology parked rather than rejected).
