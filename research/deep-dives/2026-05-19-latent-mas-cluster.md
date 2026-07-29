# Latent Multi-Agent Systems Cluster — 2026-05-19

Cluster authored: 2026-05-19 by deep-dive #2 of 8 (Phase 6).
Scope: intake-544 (RMAS), intake-555 (LatentMAS), intake-556 (Thought Communication), intake-557 (X-MAS), intake-558 (Dead Weights, Live Signals).
Index: `/workspace/research/intake_index.yaml`
Cross-refs: handoffs/active/hermes-outer-shell.md, meta-harness-optimization.md, tri-role-coordinator-architecture.md, dynamic-stack-concurrency.md, tool-output-compression.md, repl-turn-efficiency.md.

---

## Executive Summary

The five papers form a stacked stack: X-MAS empirically shows that heterogeneous text-mediated MAS dominates homogeneous MAS (zero infra change, deployable today); RMAS and LatentMAS attempt to remove the text bottleneck by routing last-layer hidden states between agents; Thought Communication supplies the theoretical identifiability layer; Dead Weights supplies the one missing puzzle piece (a single learned linear projection between heterogeneous frozen LLM latent spaces) that would unlock LatentMAS/RMAS for our exact mixed-tokenizer Qwen+Gemma+coder GGUF stack. The load-bearing claim is Dead Weights: 3-author preprint from University of Houston, no code, no independent reproduction, tested only on 5 small models in-process on a single A100. Of the cluster, **only X-MAS is production-ready for EPYC today**; LatentMAS is single-tokenizer (all Qwen3, despite its abstract framing); RMAS, Thought Communication, and Dead Weights all require fork patches to llama.cpp to surface hidden states across process boundaries plus a non-trivial training pipeline. Recommended ordering: ship X-MAS-style (domain × function) routing immediately, run a 1-week Dead Weights replication spike before committing any llama.cpp hidden-state-surfacing effort.

---

## Architectural Spectrum

| Paper | Training | Tokenizer assumption | Hidden interface | Empirical / theoretical | Cross-process? |
|---|---|---|---|---|---|
| **RMAS** (intake-544) | Trained (RecursiveLink inner+outer, ~0.31% of total params) | Heterogeneous in principle (W₃ alignment matrix) | Last-layer hidden H ∈ ℝ^(t×d_h) | Empirical (9 benchmarks, +8.3pp avg, 1.2-2.4x speedup) | No — assumes in-process |
| **LatentMAS** (intake-555) | Training-free (alignment matrix W_a via ridge regression, per run) | Homogeneous required (same shape transformer layers) — heterogeneous is future work | Last-layer hidden + layer-wise KV cache via HF `past_key_values` | Empirical (Qwen3 4B/8B/14B, all same family) | No — HF in-process only |
| **Thought Communication** (intake-556) | Trained autoencoder + adapters | Heterogeneous (tested Llama-3-8B, Phi-4-mini, Qwen3-0.6B/1.7B, DeepSeek-R1-Llama-8B) | Model states as observed variables; hidden thoughts as latent | Theoretical (3 identifiability theorems) + empirical | Not stated; HF-style |
| **X-MAS** (intake-557) | None — model assignment only | Heterogeneous text tokens (no latent state crosses agents) | None — text only | Empirical (1.7M evals, 27 LLMs, 21 test sets) | Yes — text MAS works anywhere |
| **Dead Weights** (intake-558) | Trained (5 projection matrices, ~17.6M params) | Heterogeneous tested: Llama-3.2-1B + Qwen2.5-1.5B + Gemma-2-2B → Phi-3-mini + Mistral-7B | Residual stream injection at relative depth lS=0.75, dim-1024 shared latent | Empirical (3 benchmarks, single run) | No — single A100 in-process |

Two axes matter for EPYC. **Cross-tokenizer**: only X-MAS, Thought Communication, and Dead Weights have actually demonstrated it; RMAS claims it architecturally but tested only Qwen-heavy mixes; LatentMAS does not claim it. **Cross-process**: zero papers demonstrate it. Every latent approach assumes Python in-process composition with HuggingFace `past_key_values` access. The llama.cpp HTTP server boundary is the universal blocker.

---

## The Cross-Tokenizer Bottleneck

The Dead Weights claim is the keystone. If a single 1024×d_h linear projection genuinely maps Qwen3.6 (d=5120 or similar) ↔ Gemma4-26B (d=4608) ↔ coder-30B residual streams into a shared 1024-dim latent that round-trips faithfully, then LatentMAS/RMAS-style latent inter-agent routing becomes plausible on EPYC. If that claim is weaker than advertised (e.g., works only for trivial classification, breaks on generative use), the cluster collapses to "X-MAS plus a research project."

**What Dead Weights actually shows:**

- Architecture: 3 small models project to a shared 1024-dim space via independent linear projections W₁, W₂, W₃; average-pooled; injected into 2 larger models' residual streams at relative depth 0.75 via `(1-α)·h + α·(z̃·‖h‖₂)` blend with α=0.25.
- Geometric compatibility evidence: cited from an earlier Armstrong-et-al. paper (armstrong2026thinking); offline Ridge R² ≈ 0.299 for Llama-1B → Qwen-1.5B projection (permutation control R² = -0.243). That is a low R² — the projection explains ~30% of variance. The authors themselves cite prior work noting "near-zero correlation (r ≈ -0.07) between offline geometric alignment quality and behavioral correction rate" — i.e., the offline R² may not predict downstream task performance at all.
- Training data: MMLU (14,042 ex) + ARC-Challenge (1,119 ex) + OpenBookQA (4,957 ex); ~20K examples, 3-4 epochs, AdamW, single A100 (80GB), batch 8.
- Gradient flow: 13% of gradient reaches layer-1 projections through the frozen-LLM boundary — usable but attenuated.
- Failure modes admitted: "Non-specializing L1 projections: W₁-W₃ converge to similar gradient norms despite distinct framing prefixes" (i.e., the projections don't specialize per-input-model; the diversity comes from model heterogeneity, not learned routing) and "Multiple-choice only: generalization to open-ended generation and longer contexts is untested."

**Independent reproductions:** none found in the cluster fetch. The paper is dated April 2026 (arxiv 2604.08335), 3 authors all from University of Houston CS, no code, no GitHub. Compare credibility to RMAS (12+ authors, James Zou + Markus Buehler + Pan Lu, project page at recursivemas.github.io) and LatentMAS (953 stars, Apache-2.0, ICML 2026 Spotlight, Yejin Choi + James Zou + Mengdi Wang co-authors). Dead Weights is a low-credibility-signal preprint making the highest-impact claim in the cluster. **This combination is exactly the closure-inflation hazard called out in `feedback_credibility_from_source_not_readme.md`.** It must be replicated locally before any infrastructure investment.

**Architecture pairs tested in Dead Weights:** exactly one configuration was reported — Llama-3.2-1B + Qwen2.5-1.5B + Gemma-2-2B as layer-1 encoders, Phi-3-mini + Mistral-7B as layer-2 refinement nodes. No ablation removing any single input model. No swap test (e.g., does Llama+Qwen alone work?). No scale-up (does the shared 1024-dim latent saturate at 7B? at 30B?). No alternative pooling (average pool is the only fusion). The single A100 80GB constrained the experiment envelope — our worker_general alone (26B Q4_K_M) is comparable to their total frozen budget.

**Why low R² may still suffice for our use case:** R² = 0.3 on offline Ridge is poor for "predict the next hidden state" but may be sufficient if downstream task supervision absorbs the residual. Their +11.4pp on ARC-Challenge over best single model demonstrates that the system as a whole learns to compensate. The risk is overfitting to multiple-choice signals — the explicit limitation they flag.

---

## X-MAS as the Actionable Today Path

X-MAS is fully text-mediated, zero new infra, runs on top of our current orchestrator stack. The 1.7M-evaluation matrix gives an empirical (domain × function × model) lookup that maps directly onto our role schema.

**5 domains × 5 functions matrix (X-MAS):**

| Function ↓ / Domain → | Mathematics | Coding | Science | Medicine | Finance |
|---|---|---|---|---|---|
| QA | Qwen2.5-32B (69.2%) | Qwen2.5-32B (80.3%) | — | — | — |
| Revise | — | — | — | — | — |
| Aggregation | — | — | — | Llama3-OpenBioLLM-70B (73.4%) | — |
| Planning | — | — | — | — | — |
| Evaluation | — | — | — | — | Qwen2.5-Math-72B (72.3%) |

(Only top-cell winners explicitly reported in the paper; full matrix in their Table 1. The key result: **no single model dominates across all 25 cells**.)

**Function definitions (verbatim, X-MAS §3):**

- **QA** — "comprehend a question and produce a correct answer in free-text form"
- **Revise** — "revise an initial answer to produce a corrected answer"
- **Aggregation** — "combine multiple candidate answers into a coherent, correct final answer"
- **Planning** — "decompose a task into sub-tasks and assign appropriate roles"
- **Evaluation** — "critically assess the quality or correctness of other agents' outputs"

**Mapping to EPYC roles (concrete proposal):**

| EPYC role | Current model | X-MAS function | X-MAS domain bias |
|---|---|---|---|
| frontdoor (qwen3.6) | qwen3.6 27B | Planning + QA | general / mixed |
| worker_general (gemma4-26B-A4B MTP) | gemma4-26B-A4B | QA + Revise | science / medicine |
| coder-30B (Qwen2.5-Coder-30B Q4_K_M) | coder-30B | QA | coding |
| drafter (Qwen3-1.7B) | drafter (1.7B) | (drafter — not in X-MAS) | speculative-decode only |
| (none) | — | Aggregation | varies — possibly use frontdoor in second pass |
| (none) | — | Evaluation | varies — possibly use coder-30B in second pass |

**Key empirical X-MAS findings (production-relevant):**

- Chatbot-only heterogeneous: +8.4% on MATH vs homogeneous configuration.
- Mixed chatbot + reasoner: AgentVerse 20% → 50% on AIME-2024; DyLAN 40% → 63%; +33-34% on AIME-2025 and MATH-MAS new benchmarks.
- "Increasing the number of candidate models generally enhances system performance" monotonically — so our 4-model stack (frontdoor / worker / coder / drafter) is structurally on the right side of this curve.

**Gaps that limit immediate adoption:**

- **No smaller-model coverage**: X-MAS evaluates only 7B-70B; drafter-scale (1.7B-2B) models are not benchmarked. We cannot use the X-MAS matrix to inform draft/target pairings.
- **No cost accounting**: paper acknowledges "improving both performance and cost" as motivation but does not quantify token-budget differences between models. Our cost-aware routing (q_scorer baseline_tps) is the missing complement.
- **License**: X-MAS GitHub repo (https://github.com/MASWorks/X-MAS, 29 stars, Python, last push 2025-05-30) has **no license file** — this is a real concern for direct code reuse. The matrix data and methodology are usable as research input; the code may be vendor-locked. Per `feedback_license_not_a_blocker.md` this is informational only.
- **Topology coupling**: X-MAS results are reported across specific topologies (LLM-Debate, AgentVerse, DyLAN, X-MAS-Proto). Different topology = different optimal assignment. Our orchestrator does not currently match any of these four; mapping requires adopting one or running our own small (domain × function) sweep.

**Recommended X-MAS action (Spike 1, see Concrete Spike Proposal):** replicate the (domain × function) lookup on our 4-model stack with 5-10 representative tasks per domain, use it to override `model_registry.yaml` defaults for routing. Estimated 2-3 days work, no infra change, expected +5-15% task accuracy on math/coding tasks per X-MAS magnitude norms.

---

## llama.cpp Integration Cost (Latent Path)

For RMAS/LatentMAS/Dead-Weights to run on our stack, we need to surface last-layer hidden states across the llama.cpp server HTTP boundary. Concrete cost analysis:

**Current llama.cpp server surface (`/mnt/raid0/llm/llama.cpp/tools/server/`):**

- `/embedding` endpoint exists but returns **pooled** sentence embedding (one vector per request), not per-token last-layer hidden states.
- `/completion` and `/chat/completions` return token streams only — discrete IDs and logprobs, no continuous activations.
- No KV-cache surface exposed externally; KV cache is per-slot internal state.
- ik_llama.cpp PR #1744 worker_pool branch (our current production) further specializes for MTP draft+target sharing within a single process — across-server hidden-state sharing was never a design target.

**What needs to change to support LatentMAS-style handoff:**

1. **New endpoint** (`/hidden_states`) returning per-token last-layer activations as float arrays — adds ~hidden_dim × n_tokens × 4 bytes per response (e.g., 5120 × 100 × 4 = 2 MB per typical reply, vs ~10 KB of tokens). Network cost is real but bounded.
2. **KV cache snapshot/inject API** — much harder. LatentMAS requires layer-wise KV caches to be exported from agent A and prepended to agent B's slot. llama.cpp's KV cache is tightly coupled to slot lifecycle, quantized (often Q8_0 KV), and uses a fused layout that does not map cleanly to HF's `past_key_values` tuple-of-tuples. Estimated 1-2 weeks of fork work, breaks upstream rebase compatibility, breaks ik_llama.cpp PR #1744 worker_pool branch invariants.
3. **Cross-tokenizer projection layer host** — would need a sidecar process (or new llama.cpp component) holding the trained Dead-Weights-style projection matrices and applying them between hidden_state retrieval (agent A) and KV inject (agent B). New code path.
4. **Numerical stability** — quantized weights mean per-token hidden states have q4_K_M-bounded precision. The Dead Weights paper used FP16 models on A100; we have no evidence the geometric-compatibility claim survives Q4_K_M-quantized residual streams.

**Compatibility with ik_llama.cpp PR #1744 (`feedback_ik_llamacpp_omp_idle_spin.md`, `project_worker_general_swap_2026_05_08.md`):** the worker_pool branch is our production critical path (76.5 t/s gemma4 frontdoor decode, +78% from OMP fix). Adding hidden-state export to worker_pool requires touching the slot scheduling layer where ik_llama already diverged from upstream. Risk: any rebase to upstream loses our hidden-state patches AND any future ik_llama PRs lose worker_pool. **This is a 2x rebase debt multiplier.**

**Alternative: in-process multi-model embedding in one llama-cli/server.** Theoretically possible — load multiple GGUFs into the same process, share `ggml_backend`, route between them via shared tensors. Pros: no HTTP boundary, no serialization, hidden states live in the same address space, can train Dead-Weights projections directly on internal activations. Cons: massive engineering — llama.cpp's `llama_context` is single-model by design; multi-model would require either parallel contexts (memory cost: sum of all model RAM, no sharing) or a new "model graph" abstraction (rewrite scope). Our stack-share-server policy (`feedback_same_model_roles_share_server.md`) is specifically about same-model-different-role sharing; this is the inverse problem and harder.

**Estimated cost summary:**

| Path | Engineering weeks | Rebase risk | Runtime cost | Probability of success |
|---|---|---|---|---|
| X-MAS text-only on existing stack | 0.5 | none | none | very high |
| `/hidden_states` endpoint + sidecar projection | 2-3 | medium (worker_pool conflict) | 2-10 MB/turn extra bandwidth | medium (Dead Weights claim unverified) |
| Full LatentMAS-style KV cache export/inject | 4-8 | high | KV-cache export bytes substantial | low (no precedent, quantized KV) |
| In-process multi-model llama-cli | 8-16 | very high | model RAM sum | low (architectural rewrite) |

The brutal conclusion is that the latent paths require 4-16x the engineering cost of the X-MAS text path, against unverified claims, against a working production stack. **Spike sequencing is mandatory — see below.**

---

## Speedup Claims vs Reality

Both RMAS and LatentMAS report speedups against a text-MAS baseline, not against our actual production path. Key audit:

**RMAS reported speedup:** 1.2x (r=1 recursion) → 1.9x (r=2) → 2.4x (r=3) vs **Recursive-TextMAS** (their constructed text-equivalent of the same recursive structure). They do not compare to single-model inference. Token reduction: 34.6% → 75.6% across same range.

**LatentMAS reported speedup:** 4-4.3x end-to-end vs **vLLM-accelerated TextMAS**. They cite 2.6x-7x speedup over "vLLM-optimized TextMAS" on AIME tasks where latent uses <50 steps vs 20K+ output tokens.

**Our actual production baseline:** single-server text orchestration with prefix-cache reuse. The orchestrator tool-call surface (no recursion, no debate, no aggregation pipeline) routes each request to one model, gets text back, returns to user. For the bulk of REPL turns (`handoffs/active/repl-turn-efficiency.md`) this is one llama-server call with full prefix-cache hit. Latent-MAS speedups vanish against this baseline because we already don't pay the text-MAS overhead they're optimizing against.

**Where latent could actually help:** the cases where our production path already does multi-turn agent reasoning — Hermes outer-shell agent loops (`handoffs/active/hermes-outer-shell.md`), tri-role coordinator (`handoffs/active/tri-role-coordinator-architecture.md`). For these, current cost is N text turns through the same or different models. If we replaced text turns with latent hand-offs:

- **Token savings**: RMAS-claimed 34-75% token reduction maps to direct decode-time savings (our decode is 49-76 t/s; halving emitted tokens halves wall-time linearly).
- **Quality**: RMAS +8.7pp on MATH500 over text-MAS is meaningful if applicable, but our current Hermes loop is not "recursive text-MAS" — it's a different topology. The gain may not transfer.
- **Prefix cache loss**: this is the hidden cost. Our prefix cache hits ~90-95% on common Hermes tool-call patterns. Latent hand-off has no equivalent — each agent re-processes the latent embedding from scratch. If we save 50% of output tokens but lose 90% of prefix-cache savings on input, **net effect could be negative**. Needs measurement.

**Realistic delta estimate** (Hermes outer-shell loop, hypothetical):

- Current path: 1 input pass (90% cache hit) + 1 output pass (200 tokens @ 76 t/s) ≈ 3-4 sec/turn
- LatentMAS path: 1 input pass (0% cache hit) + 1 latent pass (40-80 latent steps) ≈ 2-3 sec/turn
- **Best-case win: ~30%; worst-case loss: ~50%** depending on cache hit rate distribution. The X-MAS path delivers task-accuracy gains for similar or smaller engineering cost.

---

## Failure Modes

**Decision-theoretic dominance (contradicting_evidence per intake-544):** Reliability limits of LLM-based multi-agent planning (arxiv:2603.26993) argues multi-agent setups are decision-theoretically dominated by a centralized Bayes decision maker with the same information; no exogenous signal → no fundamental gain. Applies equally to latent-space MAS. **Latent transfer reduces lossy text compression but adds no new information.** The only escape is when individual models have different priors/training distributions — which X-MAS empirically exploits via heterogeneous role assignment. RMAS/LatentMAS speedups come from compression, not from information addition; the underlying decision-theoretic ceiling is unchanged.

**Multi-agent failure-mode breakdown (intake-544):** 42% specifications, 37% coordination, 21% verification. Latent-space communication addresses **none** of these directly. Bad specifications stay bad whether transmitted as text or as latent vectors; coordination breakdowns persist; verification gaps remain. The +8.7pp RMAS gain on MATH500 is a within-spec-type gain; the dominant production failure modes are not touched.

**Reward-hacking equivalents in latent space:** continuous latent channels are higher-bandwidth than text and provide more degrees of freedom for unintended optimization. Where text-mediated CoT can be inspected and verified (and is currently sampled by our reasoning audits), latent thoughts are opaque float vectors. The Thought Communication identifiability framework is the **only** mitigation in the cluster — and it requires training a separate sparsity-regularized autoencoder to recover the latent thought structure. Net additional infrastructure for safety parity with text MAS: substantial.

**Loss of llama.cpp prefix-cache reuse:** discussed above. Our prefix cache is currently the largest source of decode-time wins on repeat queries; any latent path that bypasses it inherits this loss.

**Cross-tokenizer projection failure modes (Dead Weights):**
- Non-specializing L1 projections converge to similar gradient norms — diversity comes from heterogeneous model behavior, not learned routing. This means the projection layer is partially redundant; the "shared latent space" may be doing less work than the abstract suggests.
- Single-run reporting on MMLU (+1.2pp gain) — within run-to-run noise for MMLU; the authors themselves caution "should be interpreted cautiously."
- Multiple-choice only — generalization to open-ended generation and longer contexts is **explicitly untested**. Our entire production workload is open-ended generation. **This is the single biggest gating risk for the cluster.**
- No quantization test — done in FP16 on A100. Our worker_general is Q4_K_M.

**LatentMAS engineering failure modes:**
- Section C.3 of the paper admits all agents must share identical transformer layer shape (d_h, n_layers). Our Qwen3.6 ≠ gemma4 ≠ coder-30B in layer shape. The trainable-adapter heterogeneous variant is explicitly future work and not validated.
- W_a alignment matrix computed via ridge regression once per run — adds per-session compute, not per-turn, so amortizes. But changes if model is swapped, which is exactly our `project_stack_simplification.md` adaptive scenario.
- HF `past_key_values` interface is incompatible with llama.cpp KV layout — porting cost is real (see llama.cpp integration cost section).

**RMAS failure modes:**
- Case studies in Appendix F show early recursion rounds producing incorrect answers requiring refinement. The 2.4x speedup at r=3 averages over cases where early rounds were wrong — single-shot quality may be worse than text.
- Latent thought generation length plateaus at m≈80 tokens — implicit cap on per-agent reasoning depth.
- "Semantic alignment analysis suggests r=1 outputs remain visibly shifted from ground-truth distribution" — the latent thoughts are not faithful reproductions of text reasoning, just goal-aligned approximations. Audit/interpretability is sacrificed.

---

## Concrete Spike Proposal

Three sequenced spikes, cheapest first. Each spike has explicit success criteria; failure of a cheaper spike kills the more expensive successors.

### Spike 1 (cheapest, ~2-3 days dev, ~1 day compute): X-MAS-style heterogeneous text-MAS

**Goal:** replace ad-hoc orchestrator role mapping with (domain × function) lookup table derived from X-MAS methodology, evaluated on our actual model set.

**Steps:**
1. Pull X-MAS-Bench task subset from https://github.com/MASWorks/X-MAS (no license — research replication only; treat as methodology, not code reuse). Focus on the 5-domain × 5-function cell layout.
2. Run 10-20 representative tasks per (domain × function) cell across our 4 production models (qwen3.6 frontdoor, gemma4-26B-A4B worker_general, coder-30B, Qwen3-1.7B drafter). Total: ~1000-2000 evals.
3. Build a 5×5 winner-model table for our specific stack. Compare to X-MAS published winners — sanity check that our results have similar shape.
4. Modify orchestrator routing: each incoming task gets a coarse (domain, function) classification, looks up the winner, routes accordingly. Fall back to current routing on unclassified tasks.
5. Hermes outer-shell agent uses the same routing for sub-task delegation (`handoffs/active/hermes-outer-shell.md`).

**Success criteria:**
- Routing table shows ≥ 2 distinct winners across the 5×5 = 25 cells (i.e., heterogeneity actually exists in our stack).
- A/B test on a held-out 100-task suite shows ≥ 5pp accuracy improvement on at least one domain, no regression on others.
- Decode wall-time per task within ±10% of baseline.

**Compute cost:** ~1 day of benchmark time (our standard llama-bench at 49-76 t/s, ~2000 evals × ~5 sec each ≈ 3 hours per model × 4 models = 12 hours, allowing for setup).

**Engineering cost:** ~2 days routing code + 1 day eval harness reuse from `epyc-inference-research/scripts/benchmark/`.

**Failure mode:** if the 5×5 table shows the same winner (likely gemma4-26B-A4B given its tool_compliance dominance from `project_worker_general_swap_2026_05_08.md`) across most cells, X-MAS heterogeneity does not apply to our stack and we can skip Spike 2 and Spike 3 entirely.

### Spike 2 (medium, ~1-2 weeks dev, ~3 days compute, requires borrowed GPU): Dead Weights replication

**Goal:** verify that a single learned linear projection between heterogeneous frozen-LLM latent spaces is real, on a model pair representative of our stack.

**Steps:**
1. Acquire short-term GPU access (single 80GB A100 or equivalent, ~3-day window — DGX Spark is not yet acquired per `project_dgx_spark_target.md`, would need rented A100).
2. Load Qwen3-1.7B and Gemma-2-2B in HuggingFace transformers (FP16, not quantized — replicate paper conditions first; quantization is Spike 3 territory).
3. Train a single dim-1024 linear projection from Qwen3-1.7B layer-N residual → Gemma-2-2B layer-M residual on ARC-Challenge training set (1119 examples, ~3 epochs, AdamW). Total trainable params ≈ 4-8M, well under their 17.6M total budget.
4. Evaluate the composed system on ARC-Challenge test set vs both single-model baselines.
5. Stretch: add a third frozen model (e.g., a small Llama variant) to test the 3→2 architecture exactly.

**Success criteria:**
- Composed system beats best single-model baseline by ≥ 5pp on ARC-Challenge (paper claimed +11.4pp; we accept any positive signal).
- Offline Ridge R² between projected and target hidden states ≥ 0.25 (paper baseline 0.299).
- No catastrophic instability — training converges in 3-4 epochs as paper claims.

**Compute cost:** ~3 days A100 time including failed runs; ~$200-500 if rented.

**Engineering cost:** ~1-2 weeks (the projection training is conceptually simple but the model-residual hook-extraction and gradient-through-frozen-LLM plumbing is fiddly; the paper's training pipeline is the artifact we'd need to reconstruct without code).

**Failure modes that kill the spike:**
- Cannot achieve R² > 0.10 — geometric compatibility claim does not generalize to our model pair.
- Composed system underperforms best single — projection is destructive, not additive.
- Training is unstable — gradient flow through frozen boundaries does not work as paper claims at our model scale.

**Kill criterion for downstream:** if Spike 2 fails on Qwen3-1.7B + Gemma-2-2B (FP16), do **not** attempt Spike 3. The whole latent path is invalidated for our heterogeneous-frozen-quantized configuration.

### Spike 3 (full, ~4-8 weeks dev, ~1 week compute, requires Spike 2 success): LatentMAS prototype on llama.cpp fork

**Goal:** end-to-end frontdoor → worker_general latent handoff on our actual production stack.

**Steps:**
1. Fork llama.cpp (specifically the ik_llama.cpp branch with PR #1744 + worker_pool, per `project_worker_general_swap_2026_05_08.md`). New branch `latent-mas-spike`.
2. Add `/hidden_states` HTTP endpoint returning per-token last-layer activations as FP16/FP32 arrays.
3. Train Dead-Weights-style projection between Qwen3.6 (frontdoor) and gemma4-26B-A4B (worker_general) residual streams. **Critical: train on Q4_K_M-quantized hidden states**, not FP16 — this is the production-realism gate Dead Weights skipped.
4. Implement sidecar projection service (Python) holding the trained projection matrices.
5. Modify orchestrator: frontdoor agent emits via `/hidden_states`, sidecar projects, worker_general consumes projected latent via injected residual hook.
6. Benchmark end-to-end: Hermes outer-shell turn with frontdoor → worker handoff. Compare wall-time, output quality, and prefix-cache hit rate degradation vs text baseline.

**Success criteria:**
- End-to-end task quality within 2pp of text baseline (no quality regression).
- Wall-time per turn ≥ 20% faster than text baseline on tasks with full frontdoor → worker handoff.
- llama.cpp fork remains rebaseable onto upstream main with <500 lines of conflict.

**Compute cost:** ~3-5 days projection retraining (Q4_K_M is novel), ~3-4 days end-to-end benchmark.

**Engineering cost:** 4-8 weeks. This is the biggest commitment and competes with all other CPU-optimization work.

**Failure modes:**
- Quantized hidden states do not project — Dead Weights claim is FP16-only artifact.
- KV-cache layout incompatibility forces rewriting slot scheduling (worker_pool branch conflict per `project_worker_general_swap_2026_05_08.md`).
- Prefix-cache loss exceeds latent compression gain — net wall-time regression.
- Upstream rebase debt becomes unmanageable.

---

## Revised EPYC Priority

The cluster-level picture meaningfully changes the per-intake priorities, mostly downward.

| Intake | Original verdict | Revised assessment |
|---|---|---|
| **544 RMAS** | worth_investigating | **shelve** — strictly dominated by LatentMAS (training-free is better than trained for frozen-stack deployment) and by X-MAS (text path is feasible today). Reopen only if Spike 3 succeeds and we want recursive depth. |
| **555 LatentMAS** | worth_investigating, ICML credibility | **worth_investigating, conditional on Spike 2** — paper itself admits homogeneous-only validation despite our intake's reading. The Apache-2.0 GitHub repo (953 stars) is the reproduction substrate, but transplanting to llama.cpp is Spike 3 cost. |
| **556 Thought Communication** | worth_investigating, theoretical | **shelve** — theoretical layer with no concrete operational lever for frozen GGUF stack. The agreement-based reweighting is implementable but requires Spikes 2 and 3 substrate. Reopen if either succeeds. |
| **557 X-MAS** | worth_investigating | **promote to Spike 1 — execute immediately** — the only cluster paper deployable on current infrastructure with zero llama.cpp changes. Highest expected value per engineering hour. |
| **558 Dead Weights** | worth_investigating HIGH priority | **demote to "verify before invest"** — original HIGH-priority rating is correct that this is the keystone, but the credibility/reproducibility gap is real. **Spike 2 is the verification gate.** |

**Net cluster scoring revision:** the original aggregation across the 5 intakes implied a serious latent-MAS engineering program. The cluster picture suggests one immediate spike (X-MAS) and one validation spike (Dead Weights replication) — total ~1 month of engineering — followed by a binary decision on the larger LatentMAS-on-llama.cpp investment.

**Connection to existing handoffs:**
- `handoffs/active/hermes-outer-shell.md` — Spike 1 directly applies; X-MAS routing can be Hermes's sub-task dispatcher.
- `handoffs/active/meta-harness-optimization.md` — X-MAS function definitions (Plan/QA/Revise/Aggregate/Evaluate) align with meta-harness role primitives; cross-pollinate.
- `handoffs/active/tri-role-coordinator-architecture.md` — three-role coordinator is a special case of X-MAS topology; the (domain × function) lookup could inform role assignment.
- `handoffs/active/dynamic-stack-concurrency.md` — X-MAS heterogeneity-helps result reinforces dynamic-stack rationale.
- `handoffs/active/tool-output-compression.md` — orthogonal to latent-MAS; text compression is independent from latent transmission.
- `handoffs/active/repl-turn-efficiency.md` — latent-MAS may hurt single-turn REPL via prefix-cache loss; relevant cost dimension.

---

## Open Questions for User

1. **Is borrowing a single A100 for 3 days feasible for Spike 2 (Dead Weights replication)?** Without this, we cannot verify the cross-tokenizer projection claim, which gates everything downstream. Rental cost ~$200-500; this is the cheapest way to de-risk a potential 4-8 week llama.cpp fork.

2. **Is the X-MAS license absence (no LICENSE file in the GitHub repo) a blocker for code reuse, or is methodology-only replication sufficient?** Per `feedback_license_not_a_blocker.md` this is informational, but I want to confirm we treat their 5-domain × 5-function methodology as research input rather than vendored code.

3. **Should Spike 1 (X-MAS replication on our stack) be folded into the existing meta-harness-optimization handoff or stood up as its own handoff?** The (domain × function × model) lookup table is closely related to meta-harness role primitives but the empirical work is distinct.

4. **What is the priority of latent-MAS vs the CPU-optimization remediation Phase 2.6 (dense generalization of NUMA_MIRROR per `project_numa_mirror_scoped.md`) and Phase 1.3 v2 per-CCD warm-up (per `project_cpu1_phase12_phase13v2_scaffolding.md`)?** The latent path is high-ceiling but high-risk; the remaining CPU work is incremental but compounds with all production workloads.

5. **For Spike 3, is divergence from upstream llama.cpp + ik_llama.cpp PR #1744 acceptable?** Adding `/hidden_states` and KV-cache export to the worker_pool branch creates 2x rebase debt. If we expect either upstream rebase or further ik_llama PRs in the next 3 months, Spike 3 should be reframed as upstream-PR work rather than fork work.

---

## References

**Primary papers (fetched 2026-05-19 via ar5iv.labs.arxiv.org):**
- intake-544 — RMAS — arxiv 2604.25917 — Xiyuan Yang, Jiaru Zou, et al. (incl. James Zou, Markus Buehler). Project page recursivemas.github.io; no GitHub.
- intake-555 — LatentMAS — arxiv 2511.20639 — Jiaru Zou, et al. (incl. Yejin Choi, James Zou, Mengdi Wang). ICML 2026 Spotlight. GitHub https://github.com/Gen-Verse/LatentMAS Apache-2.0, 953 stars, last push 2026-05-01.
- intake-556 — Thought Communication — arxiv 2510.20733 — Yujia Zheng, Zhuokai Zhao, et al. No code disclosed.
- intake-557 — X-MAS — arxiv 2505.16997 — Rui Ye, Xiangrui Liu, et al. GitHub https://github.com/MASWorks/X-MAS no license, 29 stars, last push 2025-05-30.
- intake-558 — Dead Weights, Live Signals — arxiv 2604.08335 — Marcus Armstrong, Navid Ayoobi, Arjun Mukherjee (University of Houston CS). No code, no GitHub, no independent reproductions found.

**Cited as decision-theoretic ceiling (from intake-544 contradicting_evidence):**
- arxiv 2603.26993 — Reliability limits of LLM-based multi-agent planning. Establishes that multi-agent setups are decision-theoretically dominated by a centralized Bayes decision maker with the same information.

**Related EPYC artifacts:**
- `/workspace/research/intake_index.yaml` entries intake-544, 555, 556, 557, 558 (read 2026-05-19).
- `/workspace/handoffs/active/hermes-outer-shell.md` (already updated per intake-544 entry).
- `/workspace/handoffs/active/meta-harness-optimization.md`
- `/workspace/handoffs/active/tri-role-coordinator-architecture.md`
- `/workspace/handoffs/active/dynamic-stack-concurrency.md`
- `/workspace/handoffs/active/tool-output-compression.md`
- `/workspace/handoffs/active/repl-turn-efficiency.md`
- `/mnt/raid0/llm/llama.cpp/tools/server/server-context.cpp` (current server surface, `/embedding` endpoint exists, `/hidden_states` does not).
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml` (target of Spike 1 routing change).
- `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` (source for any (domain × function) lookup additions).

**Cluster-internal references in EPYC memory:**
- `feedback_credibility_from_source_not_readme.md` — applied to Dead Weights credibility assessment (3-author preprint with no code, single-run reporting).
- `feedback_closure_inflation.md` — applied to avoid over-extrapolating from Dead Weights single result.
- `feedback_sanity_check_before_compute.md` — Spike 2 is the sanity check before Spike 3 compute commitment.
- `project_worker_general_swap_2026_05_08.md`, `feedback_ik_llamacpp_omp_idle_spin.md` — define ik_llama.cpp worker_pool branch rebase debt.
- `feedback_license_not_a_blocker.md` — informational treatment of X-MAS no-license repo.
- `project_orchestrator_stack_freeze.md` — Spike 1 X-MAS routing change should annotate research registry per stack-freeze policy.
- `project_dgx_spark_target.md` — Spike 2 GPU acquisition gap.
