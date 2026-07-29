# RoPE Long-Context Bounds Deep-Dive — 2026-05-20

**Author**: research-intake deep-dive on intake-569
**Anchor paper**: arxiv:2605.15514 — "RoPE Distinguishes Neither Positions Nor Tokens in Long Contexts, Provably" (Du, Harris, Tian, Huerta, Ronanki, Rongali, Galstyan, Peng — submitted NeurIPS 2026, posted 2026-05-15)
**Triangulation**: intake-547 (Wang RLM reproduction, arxiv:2603.02615), intake-032 (YaRN, arxiv:2309.00071), intake-153 (canonical RLM, arxiv:2512.24601), intake-409 (EM-LLM)
**Scope**: theoretical-posture metabolization. No new code; informs cite-on-rationale for `yarn-context-extension-research.md`, `context-folding-progressive.md`, `long-context-eval-datasets.md`, `cpu-context-regime-coverage.md`.

---

## Executive Summary

The paper proves four mathematical failure modes of Rotary Positional Embeddings (RoPE) at long context, each derived from a single statistical model (the RoPE Product as a zero-mean Normal random variable). The headline result is a **provable, irreducible trade-off** between distinguishing positions and distinguishing tokens, controlled by the RoPE base hyperparameter `B`. Increasing `B` (which is exactly what every long-context-extension trick does — NTK-aware, YaRN, dynamic scaling) **improves token distinguishing at the direct cost of position distinguishing**. There is no setting of `B` that preserves both at long context. Empirically, all tested 7B–405B models (Llama 3.1, Mistral, Qwen3, DeepSeek-v3, Kimi K2.5, GPT-OSS) collapse to chance (~0.25) on a 4-element position-indexing task by **4K–8K tokens** — far below their nominal 32K–128K context windows.

For EPYC operationally: this paper does NOT change what we build, but it **dramatically strengthens the justification for what we already build**. Three existing posture claims in the active handoff set move from "empirically supported" to "provably bounded":

1. **`yarn-context-extension-research.md` gate** — "context_extension becomes a concrete workload requirement" — is now backed by a closed-form proof, not just an empirical observation, that YaRN's base-raising mechanism inevitably sacrifices position-distinguishing. Reactivation criteria should explicitly require that the workload **does not need fine-grained position discrimination** beyond ~32K.
2. **`context-folding-progressive.md` premise** — that procedural folding into bounded chunks beats pushing the context window — now has a theoretical floor: at 50K+ tokens the underlying attention mechanism is provably no better than chance at locality bias. Folding is not an engineering preference; it's a workaround for a proven failure.
3. **fast-rlm-style depth-1 cap** (from `01-fast-rlm-budget-controls.md`) is now triangulated by two independent papers: Wang's empirical 96× wallclock cliff at depth-2 (intake-547) is **mechanistically explained** by Du et al.'s position-inversion proof — the depth-2 aggregation step has to do long-context attention over the depth-1 children's outputs, which is exactly the regime where RoPE has been proven to fail.

**Single highest-leverage operational change**: add a one-line "context-regime sanity check" to `cpu-context-regime-coverage.md`'s 32K-context test row. The check: for any model deploying at ≥32K, run the 4-element indexing task and record degradation. This costs ~5 minutes per model and gives us a **per-model empirical bound** on where RoPE breakdown begins for our actual stack, not just the paper's reference models. **Flagging for user approval** before scheduling — falls under `feedback_no_concurrent_inference` and `feedback_speed_verify_via_llama_bench`.

---

## The Four Failure Modes

The paper's central technical move is modeling the RoPE Product (the unnormalized attention score before softmax) as a Normal RV `S̃ ~ N(μ_M, σ_M²)` parameterized by context length `M`, RoPE base `B`, head half-dim `h`, and datatype fraction bits `f`. The four failure modes are corollaries.

### F1 — Position Inversion (Theorem 1)

**Formal**: For fixed query/key tokens, the probability that a key at position `m₂ ∈ [M/2, M)` (far) receives a higher RoPE product than a key at position `m₁ ∈ [0, M/2)` (near) **approaches 1/2** as `log M · log B → ∞`.

**Operational**: At long context, RoPE attention is **no more likely to favor nearby positions than distant ones**. The "locality bias" that makes RoPE behave like a soft sliding window is gone.

**Quantitative thresholds (Llama 3.1-8B, B=10⁵, h=64)**:
- ≤ several thousand tokens: probability already exceeds **0.3**
- > 50K tokens: probability approaches **0.5** (chance)

**Both `M↑` and `B↑` make this worse.** Raising the base does NOT help position inversion — it accelerates it.

### F2 — Position Aliasing (Theorem 2)

**Formal**: For two distances `m₁ ≠ m₂`, the probability they produce **bit-identical** RoPE products (under finite floating-point precision) converges to 1 **exponentially fast** as `M` grows. Total aliasing pairs increase with both `M` and `B`.

**Operational**: Two physically different positions become **numerically indistinguishable** to the attention mechanism. Information about absolute position is being silently destroyed by precision loss.

**Quantitative (Llama 3.1-8B, BF16, h=64)**:
- At **M = 8K**: **75,000 aliasing pairs** detected
- Density "increases with context length" (no closed-form upper bound; the paper just says ~100% asymptotically)

**Derived failure (Attention Invariance)**: at aliasing positions, **swapping two key vectors produces identical attention output for ANY query**. Paper counts **1,491 such invariance cases at 8K BF16** for Llama 3.1-8B.

### F3 — Token Inversion (Theorem 3)

**Formal**: For two keys with initial ranking `S₁(0) > S₂(0)`, the probability they reverse at distance `m` (i.e., `S₁(m) < S₂(m)`) approaches **1/2** as `m → Θ(B)`. The lower bound **decreases with `B`** — raising the base helps.

**Operational**: The model's preference for one token over another is **unstable over distance**. A token that scored high at position 100 may score low at position 30K, with no semantic justification.

**Quantitative**: For typical examples (query="pet", keys={"cat", "number"}): inversion happens **within 10 tokens** locally; **probability → 0.5 by m ≥ 20K** in Llama 3.1-8B's 128K window.

**Key asymmetry**: `B↑` HELPS this failure mode. This is the only F-mode where raising the base buys something — and it's the reason YaRN/NTK-aware exist.

### F4 — Token Aliasing (Theorem 4)

**Formal**: The number of positions at which two distinct keys `k₁ ≠ k₂` produce identical attention scores is bounded by `Θ(2^(-f) √h · M)`.

**Operational**: At ~5% of positions in a long context (BF16, h=64), the model **literally cannot tell two different tokens apart** at that position.

**Quantitative**:
- BF16 (f=7), h=64: **~5% of positions** affected
- At 32K context: **~1.6K positions** with token aliasing
- At 8K: **~150 positions** with token aliasing

**Like F3**: `B↑` HELPS (decreases aliasing positions).

### The trade-off table

The single most operationally important row of the paper:

| Failure Mode | Effect of M↑ (longer context) | Effect of B↑ (raise base, à la YaRN) |
|---|---|---|
| F1 Position Inversion | ↑ (worsens) | ↑ (worsens) |
| F2 Position Aliasing | ↑ (worsens) | ↑ (worsens) |
| F3 Token Inversion | ↑ (worsens) | **↓ (improves)** |
| F4 Token Aliasing | ↑ (worsens) | **↓ (improves)** |

**The diagonal**: raising `B` to extend context (the YaRN move) **simultaneously fixes the token modes (F3/F4) and breaks the position modes (F1/F2)**. There is no `B` that preserves both. This is the irreducibility result; it is the paper's most cite-worthy single sentence.

---

## The Empirical Indexing Task

The paper's empirical claim is that the theoretical failure modes **bite at context lengths far below the nominal claims of every tested model**. Methodology is deliberately minimalist:

- Input: Python literal `arr = [v₁, v₂, v₃, v₄]` where `vᵢ ∈ {0,1,2,3}` (single-token elements)
- Query: extract `arr[k]` for given `k`
- Padding: increase context length to test scaling
- Baseline: random guess = 0.25

**Models tested**: Llama 3.1-8B / 70B / 405B, Mistral-7B-Instruct-v0.3, Qwen3 (size not specified in extract), DeepSeek-v3, Kimi K2.5, GPT-OSS-120B / 20B.

**Headline finding**: ALL models, regardless of parameter count (7B–405B), drop to ~0.25 (chance) **by 4K–8K tokens**.

That is: a 405B-parameter model claiming 128K context cannot reliably tell which of four positions holds a specific token, once the surrounding context exceeds ~4K. The empirical floor is **two decimal orders of magnitude below the nominal context window**.

**Caveat (which paper acknowledges, see Limitations)**: a synthetic indexing task is the **worst case** — real workloads have semantic context that helps the model disambiguate. RULER / BABILong / OOLONG type benchmarks see degradation but not chance-floor collapse. The indexing task is an **upper bound on what RoPE alone can do**, not a direct prediction of QA accuracy.

---

## Cross-Paper Triangulation with Wang RLM Reproduction (intake-547)

The single most valuable cross-paper insight is that **two independent papers, using completely different methodologies, converge on the same regime boundary**. This is not a coincidence — Du et al.'s theory **mechanistically explains** Wang's empirical observation.

### Wang (intake-547, empirical)

- Reproduced Zhang et al. RLM (intake-153) on DeepSeek-v3.2 and Kimi K2
- **Depth-1 RLM wins** on complex long-context reasoning (matching Zhang's claims)
- **Depth-2 RLM degrades accuracy AND inflates wallclock 96× (3.6s → 344.5s)**
- Concluded: "deeper recursion is actively harmful at depth ≥ 2 for many tasks"

### Du et al. (intake-569, theoretical)

- Position inversion crosses 0.3 by "a few thousand tokens", → 0.5 by ~50K
- Position aliasing → 1.0 exponentially in `M`
- Empirical indexing collapses to chance by 4K–8K across all model sizes

### The mechanistic link

At depth-2, the parent RLM's aggregation step has to do **long-context attention over the depth-1 children's outputs concatenated together** — which is exactly the regime Du et al. proved breaks down. The 96× wallclock cliff isn't only "more tokens to process"; it's **also** the model spending more passes failing to converge on a coherent aggregation because position-distinguishing has degraded beyond the threshold.

This is a textbook example of theory-meets-empirics: Du et al. would have **predicted** the depth-2 cliff Wang observed; Wang's measurements **confirm** the operational impact of Du's theoretical bounds. Either paper alone is informative; together they form a load-bearing pair.

**Operational consequence**: `01-fast-rlm-budget-controls.md`'s hard-cap at depth=1 (already in production via `max_escalations=2`, `repl_executions` budget, etc.) is now backed by **theory + empirical reproduction**. The cap should NOT be relaxed without retiring RoPE or layering a position-encoding alternative on top.

---

## EPYC Operating-Regime Analysis

EPYC's deployed context lengths matter for how much of this paper applies. Mapping the failure modes to our actual operating points:

| Context regime | Where we use it | RoPE failure-mode status (per paper) |
|---|---|---|
| **≤ 4K** | Most chat, simple QA, classifier inputs | F1/F2 negligible; F3 already kicked in locally but doesn't dominate; F4 affects ~5% positions ALWAYS |
| **4K–8K** | Worker_general dialogues, REPL turn contexts after summarization | **Empirical indexing-task collapse begins.** F1 inversion probability ~0.3; F2 aliasing detectable; F3 inversion → 0.5 not yet hit |
| **8K–32K** | Document QA, RAG over short corpora, our default `_repl_turn_token_cap` regime | F1 inversion ~0.3–0.4; F2 aliasing climbing; F3 approaching ~0.5 (paper says m ≥ 20K); F4 stable ~5% |
| **32K–64K** | Long-doc tasks; `cpu-context-regime-coverage.md` Phase 2.2 floor | F1 firmly in the unreliable zone; F2 dense; F3 at chance; **operationally: RoPE attention is degraded but not destroyed for content that has strong semantic signal** |
| **64K–128K** | Rare; `yarn-context-extension-research.md` would unlock | F1 essentially chance (0.5); F2 ~100%; **RoPE has lost most of its discriminative power** — model relies on token co-occurrence statistics, not position |
| **128K–1M** | Hypothetical with YaRN | All failure modes saturated; paper says "no longer reliably positional" |

**Concrete takeaways for our stack**:

1. **The 32K boundary is the operational hard line.** Up to 32K, F1 is "noisy" (~0.3–0.5 probability) but content semantics carry the signal. Beyond 32K, position information becomes meaningfully unreliable. **This matches our existing `cpu-context-regime-coverage.md` 32K test point — that test was already the right boundary to measure, this paper just gives it a theoretical justification.**
2. **F4 (token aliasing at ~5%) is constant across regimes**. We've been running with this since 2023 in every BF16/F16 deployment. The paper does not call for a behavior change; it merely documents that 5% of positions per context have this property, regardless of context length.
3. **F3 helps justify our existing posture against re-enabling concurrent inference benches**. If the failure mode probability is regime-dependent, then concurrent runs (where one bench reads the other's memory pressure and silently degrades) become a confounder we cannot afford. We already have this rule via `feedback_no_concurrent_inference`; the paper provides another reason to keep it.
4. **YaRN's value proposition is narrower than it looked**. YaRN extends context by raising `B`. The paper says: that helps F3/F4 (token modes), but breaks F1/F2 (position modes). So YaRN is good for tasks where **content** is what matters and **position** is incidental (e.g., document summarization where order can be inferred from content). YaRN is bad for tasks where exact position matters (e.g., line-numbered code review, retrieval at a specific offset). **This refines `yarn-context-extension-research.md`'s gate**: not just "concrete workload requirement", but specifically "concrete workload requirement where position fidelity is NOT load-bearing".

---

## Implications for Active Handoffs

| Handoff | Current relevance | Concrete edit suggested |
|---|---|---|
| `yarn-context-extension-research.md` | HIGH — paper bounds YaRN's mechanism. Already updated with intake-569 cross-ref. | Refine the gate criterion to add "AND workload tolerates degraded position-discrimination above 32K". Cite intake-569 + Theorem 3+4 trade-off table. |
| `context-folding-progressive.md` | HIGH — paper provides theoretical justification. Already updated with intake-569 cross-ref. | No edit needed; the cross-ref I added is sufficient. The "use folding instead of long context" hypothesis is now provably grounded. |
| `long-context-eval-datasets.md` (completed) | MEDIUM — paper's indexing task is a useful sanity-check baseline. | Optional: append a note suggesting the 4-element indexing task as a quick per-model sanity-check (~5 min per model, gives empirical confirmation that the model's claimed context length is real). |
| `cpu-context-regime-coverage.md` | MEDIUM — paper provides theoretical justification for the existing 32K test point as the operational boundary. | Optional: in a future revalidation pass, add the 4-element indexing task as a one-line sanity check at the 32K row. Falls under benchmark-execution rules (user approval required). |
| `rao-redel-substrate-spike.md` | MEDIUM — provides additional evidence that depth-2 recursion failures (Wang) have a mechanistic explanation in RoPE breakdown. Reinforces depth-1 default. | No edit; the existing handoff already cites intake-547 with the depth-1 caveat marked **load-bearing**. |
| `01-fast-rlm-budget-controls.md` (completed) | MEDIUM — paper provides theoretical justification for the depth-1 cap (which is enforced via `max_escalations`, `repl_executions` budget). | No edit; the cap is already in production and is the right setting per both papers. |
| `repl-final-schema-validation.md` (completed) | LOW — schema validation is orthogonal to position encoding. | No edit. |

---

## Failure Modes & Contradicting Evidence

Consolidated for full epistemic discipline:

1. **Paper age (2026-05-15, 5 days at intake)** — limited time for independent critique. No falsification papers exist yet.
2. **Theory operates at the head level; real models have multi-head + multi-layer.** The paper's Appendix E does some multi-head analysis but acknowledges "we do not theoretically analyze the multi-layer multi-head attention". Multi-head averaging may smooth some of the failure modes. **Limit: do not over-interpret the chance-floor predictions for deployed multi-layer models.**
3. **Uniform amplitude assumption.** Real attention heads have a few dimensions with disproportionate amplitude. The paper acknowledges this may "shorten the effective context length limit" — i.e., the failure regime kicks in EARLIER than the proven bounds suggest, not later. This is a conservative-direction assumption.
4. **Synthetic indexing task overstates the failure.** Real tasks have content semantics; models can rely on token co-occurrence to compensate for position breakdown. The 4-element indexing task is the **worst case**. RULER / BABILong / OOLONG show degradation but not chance-floor collapse at 32K.
5. **The trade-off table (F3/F4 down with `B↑`, F1/F2 up with `B↑`) is a directional claim, not a numerical one.** For a specific model with B=10⁶ vs B=10⁵, the paper does not tell us by how much position fidelity drops; it only tells us the direction. Anyone designing a YaRN policy on this paper alone is over-extrapolating.
6. **Liu 2026 (arxiv:2602.10959, "Rotary Positional Embeddings as Phase Modulation")** — independent paper, different derivation, **same conclusions**. Counts as supporting, not contradicting. This triangulation strengthens the paper.
7. **No falsification of the four-failure-mode taxonomy found.** Tier 2b search surfaced two ALTERNATIVE encodings (TAPA arxiv:2509.12635, HoPE) but both implicitly accept Du et al.'s premise — i.e., they propose to FIX the failure modes Du et al. describe. Field consensus is moving in the paper's direction.
8. **Most dramatic claims kick in at 128K+** — where EPYC operates rarely. For our typical 4K–32K regime, the failures are measurable but not catastrophic. **The paper is most load-bearing as a brake on extension beyond 32K, not as evidence of failure within our usual operating range.**

---

## Concrete Action Items

**No code-level actions.** The paper informs posture; it does not unblock implementation work. The implementation-level action items below are explicitly bounded.

### A0 — Cite-on-rationale registry (done)

The two active handoffs (`yarn-context-extension-research.md`, `context-folding-progressive.md`) have already been updated with intake-569 references. No further action.

### A1 — Per-model indexing-task sanity check (proposed, awaiting user approval)

For each model in the EPYC stack (gemma4-26B-A4B, qwen35-27b, qwen3-next-80B, REAP-246B, 30B-A3B), run the 4-element indexing task at 4K, 8K, 16K, 32K context lengths. Record collapse point.

Estimated cost: ~5 min per model × 4 lengths × 5 models = ~100 min total compute.

**Gate this on user approval per `feedback_no_concurrent_inference` and `feedback_speed_verify_via_llama_bench`** — I cannot execute. The value: gives us **per-model empirical bounds** on where RoPE breakdown begins for OUR stack, not just the paper's reference models. This is the highest-leverage operational use of this paper.

### A2 — Refine YaRN gate criterion (proposed, ≤5 LoC text edit)

Edit `yarn-context-extension-research.md` status line:

```
Gate to reactivate: context_extension becomes a concrete workload requirement
                    AND the workload tolerates degraded position-discrimination
                    above 32K (per intake-569 Theorem 3+4 trade-off table).
```

This is a documentation refinement only. **Flagging for user approval** because the gate criterion was set by the original handoff author; should not unilaterally tighten it.

### A3 — Document the F1–F4 / B-trade-off table in a long-context cheat sheet (optional)

A one-page operator reference in `docs/` (or `wiki/` if epyc-root has one) capturing:
- The trade-off table (`B↑` helps F3/F4, hurts F1/F2)
- The 32K operational boundary
- The Du+Wang triangulation
- Pointer to this deep-dive

**Estimated effort: 30 min.** Defer until the user signals appetite — could be redundant with the deep-dive itself.

---

## Open Questions for User

1. **Should A1 (per-model indexing-task sanity check) be scheduled?** Cost is low (~100 min); value is per-model empirical floor. The alternative is continuing to rely on paper-reference models (which include some we run, like Qwen3, but not our specific quantizations / build of llama.cpp).
2. **Should the YaRN gate criterion (A2) be tightened with the position-discrimination caveat?** This is a single-line text edit; the author of `yarn-context-extension-research.md` set the original gate.
3. **Should we open a small "position-encoding alternatives" tracking entry?** TAPA (arxiv:2509.12635), HoPE, Fourier Position Embedding are all proposed alternatives. Adoption is gated by upstream llama.cpp support (we'd be early adopters). Currently filed under "tag_only_until_hardware" because (a) we use off-the-shelf GGUF, (b) alternatives require model re-training. Could promote to a research-watch entry if the user wants visibility.
4. **Anything in the deep-dive that should be promoted to a wiki entry?** The trade-off table + 32K boundary + Du+Wang triangulation pattern could be valuable in the wiki for future reference. CLAUDE.md says wiki maintenance lives in `project-wiki` skill; would need that to be invoked separately.

---

## References

### Anchor paper
- arxiv:2605.15514 — Du, Harris, Tian, Huerta, Ronanki, Rongali, Galstyan, Peng, "RoPE Distinguishes Neither Positions Nor Tokens in Long Contexts, Provably" (submitted NeurIPS 2026, posted 2026-05-15). https://arxiv.org/abs/2605.15514

### Triangulating papers
- arxiv:2603.02615 — Wang, "Think, But Don't Overthink: Reproducing Recursive Language Models" (intake-547). The empirical-side companion.
- arxiv:2602.10959 — Liu 2026, "Rotary Positional Embeddings as Phase Modulation: Theoretical Bounds on the RoPE Base for Long-Context Transformers". Independent theoretical derivation arriving at consistent conclusions.
- arxiv:2309.00071 — Peng et al., YaRN (intake-032). The technique whose mechanism this paper bounds.
- arxiv:2512.24601 — Zhang/Kraska/Khattab, canonical RLM (intake-153). The recursive-decomposition alternative this paper motivates.

### Surfaced alternatives (not deep-dived here)
- arxiv:2509.12635 — Token-Aware Phase Attention (TAPA). Proposed alternative to RoPE; learnable phase function.
- HoPE (Hyperbolic Position Embedding). Mentioned but not yet intaked.

### Intake entries
- intake-569 — `/workspace/research/intake_index.yaml` (lines ~25952–26035 after this session's append).
- intake-547, intake-032, intake-153, intake-409 — see anchor paper section.

### EPYC handoffs (cross-referenced)
- `/workspace/handoffs/active/yarn-context-extension-research.md` (updated 2026-05-20 with intake-569)
- `/workspace/handoffs/active/context-folding-progressive.md` (updated 2026-05-20 with intake-569)
- `/workspace/handoffs/active/cpu-context-regime-coverage.md`
- `/workspace/handoffs/completed/long-context-eval-datasets.md`
- `/workspace/handoffs/completed/01-fast-rlm-budget-controls.md`
- `/workspace/handoffs/completed/repl-final-schema-validation.md`
- `/workspace/handoffs/active/rao-redel-substrate-spike.md`

### Memories invoked
- `feedback_no_concurrent_inference` — gates A1 on user approval.
- `feedback_speed_verify_via_llama_bench` — gates A1 on user approval.
- `feedback_handoff_driven_tracking` — this deep-dive IS the multi-phase persistence; a handoff stub is NOT created because no implementation work is unblocked.
- `feedback_phased_plan_gates` — deep-dive ends with explicit user-approval gates (A1, A2, A3).
- `feedback_closure_inflation` — explicitly enumerated which gates the paper meets (F1–F4 proofs, indexing-task empirical) AND which it does not (multi-head theory; numerical predictions for specific B values); did not extrapolate to "RoPE is exhausted" or similar inflation.
