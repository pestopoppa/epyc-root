# Frozen-Backbone Persistent Memory Cluster — 2026-05-19

**Cluster #6 of 8** — Two intakes covering complementary points in the frozen-backbone persistent-memory design space.

**Intakes in scope:**
- **intake-539** — δ-mem: Efficient Online Memory for LLMs (arxiv:2605.12357, Lei et al., declare-lab/MindLab)
- **intake-568** — Trained Persistent Memory for Frozen Encoder-Decoder LLMs (arxiv:2603.16413)

## Executive Summary

δ-mem provides a single, opinionated *online* memory mechanism: a compact state matrix updated by the delta rule, read out as low-rank corrections to the frozen backbone's attention — reported +10% avg, +31% MemoryAgentBench, +20% LoCoMo over the unmodified backbone on Qwen3-4B/8B and SmolLM3-3B. intake-568 instead provides a *comparative study* of six memory topologies (Prefix, parallel cross-attn, KV-extension, Hebbian outer-product, Gated branch, Slot) attached to a frozen Flan-T5-XL, with the key empirical finding that **the right topology depends on capacity**: M.2 XAttn / M.6 Slot win at low capacity, M.4 Hebbian wins at high capacity / long-lag. Together the two papers bracket the literature: δ-mem is the recommended *single-best-guess* mechanism, intake-568 is the *menu* with prior-art benchmarks. Both are frozen-backbone-validated and directly relevant to our completed `orchestrator-conversation-management.md` B1 (User Modeling) slot, which currently has only SQLite-backed snapshot persistence and zero in-attention memory.

## δ-mem Mechanism (intake-539)

**Architecture.** δ-mem augments a frozen full-attention backbone (Qwen3/SmolLM3) with a compact online associative-memory state and a learned readout that produces low-rank corrections to the backbone's attention output during generation. The paper's abstract advertises an "8×8 online memory state" though in code (declare-lab/delta-Mem) the state-matrix dimensions are parameterized per write strategy (TSW = Token Segment Write, SSW = Segment State Write, MSW = Multi-segment Write).

**Update rule (delta-rule learning).** Conceptually, for incoming key/value projections `k_t, v_t`:

```
S_t = S_{t-1} + β · (v_t − S_{t-1} · k_t) ⊗ k_t
```

i.e. the classical Widrow-Hoff / DeltaNet update — write the residual between the new value and what the current state would have predicted for this key, scaled by a learned write-rate β. This is *the same primitive* as DeltaNet (linear-attention family) but applied as a sidecar to a frozen quadratic-attention backbone, not as a backbone replacement. (Note: our active handoff `log-linear-gated-deltanet-readiness.md` is directly adjacent — the kernel work to make DeltaNet fast also accelerates δ-mem readouts.)

**Readout / injection point.** Memory readout produces a low-rank correction added to the backbone's attention output. The paper does not specify per-layer vs single-point in the abstract; the code organizes injection through an "adapter management" layer (`deltamem/core/`) suggesting per-layer hooks rather than a single bottleneck. Crucially, the backbone Q/K/V projections are *not* modified — the correction is post-attention residual.

**Frozen-backbone compatibility.** Yes, validated end-to-end. The whole point of the paper. No backbone fine-tuning, no replacement.

**Training.** Only the adapter (memory projections + readout) is trained. SFT scripts in repo (`scripts/run_qasper_multimodel_write8192_train_and_benchmark_suite.sh`). Released adapter checkpoint: Qwen3-4B-Instruct-2507.

**Benchmarks (vs frozen backbone, ratio reported).**
- Average across suite: **1.10×**
- MemoryAgentBench: **1.31×**
- LoCoMo: **1.20×**
- Other tasks covered in eval/: HotpotQA, IFEval, GPQA Diamond.

**Inference cost.** Per-token: one extra matrix update (O(d_h²) per layer if state matrix is d_h×d_h) plus one low-rank multiply for readout. With d_h=8 as the headline state, this is *negligible* per token — far below KV-cache growth costs at long context. The win is that state is constant-size regardless of context length.

**Code.** [github.com/declare-lab/delta-Mem](https://github.com/declare-lab/delta-Mem) and [github.com/MindLab-Research/delta-Mem](https://github.com/MindLab-Research/delta-Mem). CC-BY-4.0. ~9 commits as of intake. Adapter checkpoints released for Qwen3-4B-Instruct-2507.

## The Six Topologies (intake-568)

Flan-T5-XL (3B, bfloat16) tested as the frozen encoder-decoder. Memory bank sizes: n_P = 64 (1× scale) or 640 (10× scale), hidden d = 768. The paper organizes by (**injection point**, **write mechanism**) rather than the names I guessed in the request. Verified taxonomy:

| # | Name | New params | Memory state | Write | Read injection | Notes |
|---|------|-----------|--------------|-------|----------------|-------|
| **M.1** | **Prefix** | 4.2M | constant | attention-coupled | soft tokens prepended to encoder input | Collapses to ~0% at 1× capacity |
| **M.2** | **XAttn** (parallel decoder cross-attention) | 16.8M | constant | attention-coupled | parallel cross-attn branch in decoder, learned scalar | **Best at 1× short-lag (17.85%)** |
| **M.3** | **KV Extension** | 4.2M | constant | attention-coupled | extra K/V pairs concatenated into decoder cross-attn | Best 10× short-lag (15.58%) |
| **M.4** | **Hebbian** (outer-product) | **1.0M** | O(d_h²) | Hebbian outer product | decoder KV extension from associative read | **Best 10× long-lag (10.32%); most parameter-efficient** |
| **M.5** | **Gated** | 21.0M | constant | attention-coupled, content-gated | gated branch inside decoder | Collapses at 1×; largest param budget |
| **M.6** | **Slot** | 4.2M | O(S·d), S=64/640 | top-k sparse writes | decoder KV extension | Best knowledge-accumulation gain (+9.71% over 30 sessions) |

**Headline result.** No single winner: **capacity is the design knob**. At small memory budgets (1×, n_P=64) attention-coupled methods (M.2 XAttn, M.6 Slot) dominate; at large budgets (10×, n_P=640) the Hebbian outer-product M.4 wins long-lag retention with the smallest parameter count.

**Write mechanism observation.** M.4 (Hebbian) is the *direct ancestor* of δ-mem's delta-rule update — both are outer-product associative writes. δ-mem refines it with the delta correction term (write the residual, not the raw value) and a low-rank attention correction readout instead of a KV extension.

**Frozen-backbone compatibility.** Yes, all six. Encoder-decoder route preserved; memory enters only through controlled learnable pathways.

**Code.** Not released as of intake (paper mentions intended release, no link).

## EPYC Integration Path

**Immediate consumer: orchestrator B1 User Modeling.** Our completed `handoffs/completed/orchestrator-conversation-management.md` B1 slot implemented cross-session user modeling as a SQLite-backed *snapshot* (user_conclude/user_profile tools) injected into the system prompt. That is functionally equivalent to **M.1 Prefix** with a hand-written profile rather than a trained memory — and intake-568 measures M.1 Prefix collapsing to ~0% at the smaller capacity setting. This is a falsified-baseline signal: snapshot-in-prompt is the *weakest* memory topology in the literature. The orchestrator's User Modeling slot is the natural integration target for either δ-mem or M.4 Hebbian.

**Within-session vs cross-session complementarity.**
- δ-mem = within-session online state (resets per conversation, no persistence layer described in paper)
- intake-568 M.4 Hebbian / M.6 Slot = persistent bank that accumulates across sessions (+7-10% gain over 30 sessions demonstrated)
- The two are stackable: δ-mem for within-session fast adaptation + persistent bank (serialized to SQLite alongside threads/episodic_store from B1) for cross-session preferences.

**llama.cpp / GGML integration.** Of the six topologies, ranked by llama.cpp KV-cache compatibility:

1. **Easiest — M.3 KV Extension / M.6 Slot.** Both inject as additional K/V pairs into the decoder cross-attention. In llama.cpp this maps directly to extending the KV-cache with a fixed prefix of *learned* K/V vectors (loaded from a sidecar safetensors). **Zero custom GGML ops** — just prepend to the KV cache at decode start. Adapter parameter loader is the only new code.
2. **Moderate — δ-mem / M.4 Hebbian.** Need a custom GGML op for the per-token state update (outer product accumulator) plus a low-rank readout op. The state lives outside the KV-cache. This is structurally similar to the DeltaNet ops we'd need anyway for `log-linear-gated-deltanet-readiness.md` — shared engineering payoff.
3. **Harder — M.2 XAttn / M.5 Gated.** Require a *parallel* attention branch executed alongside backbone attention every block. Touches the hot path; needs careful fusion with our AVX-512BW kernels.
4. **Hardest — M.1 Prefix.** Trivial mechanically (soft tokens) but training requires gradients through the frozen backbone's embedding layer, which conflicts with our frozen-GGUF assumption unless we precompute the prefix once per user and persist as embedding-space vectors. Also literature-worst.

**Estimated dev cost (easiest path: M.3 KV-extension adapter for orchestrator B1).**
- ~1 week: adapter format spec + loader, KV-cache prefix injection in llama-server's request handler, serialization to/from SQLite
- ~1 week: training script for the adapter (4.2M params, fits on a single GPU rental for a few hours per backbone)
- ~1 week: integration with B1 user_conclude/user_profile tools — replace prompt-injection with KV-prefix injection
- **~3 engineer-weeks** for first prototype on one backbone (worker_general gemma4 is the highest-traffic candidate)

**δ-mem path is ~5-6 weeks** (custom GGML ops + state-matrix persistence + per-layer hook plumbing) but yields the within-session benefit too and amortizes against the DeltaNet kernel work.

## Spike Proposal

1. **(cheapest — ~3 days) Reference-impl reproduction.** Clone `declare-lab/delta-Mem`, run the released Qwen3-4B-Instruct-2507 adapter through MemoryAgentBench + LoCoMo on a GPU rental (or our CPU stack if HF transformers can run it). Confirm 1.31× / 1.20× claimed ratios on our hardware. Decision gate: if reproducible, proceed; if not, downgrade to intake-568 M.3 path (simpler primitive, weaker claim).

2. **(medium — ~3 weeks) M.3 KV-Extension adapter for gemma4 worker_general.** Pick M.3 KV-Extension as the lowest-risk topology with non-trivial expected gain (intake-568 reports 12.05% LoCoMo mean recall at 10× capacity). Train a 4.2M-param adapter against gemma4-26B-A4B Q4_K_M (our highest-traffic worker), wire into llama-server as a KV-cache prefix loaded per user from SQLite. Reuses B1's user_conclude/user_profile data path.

3. **(full — ~6 weeks) δ-mem GGML port + cross-session bank.** Land custom GGML ops for the delta-rule state update and low-rank readout. Wire state persistence into the orchestrator session store so a user's δ-mem state survives across conversations (paper doesn't specify this; we'd be extending). Combine with M.4-style persistent associative bank for cross-session knowledge. Shared kernel scaffolding with `log-linear-gated-deltanet-readiness.md`.

## Open Questions for User

1. **Backbone choice for first adapter.** δ-mem ships an adapter for Qwen3-4B; our production worker is gemma4-26B-A4B Q4_K_M. Train a new gemma4 adapter (real cost) or pilot first with Qwen3-4B (cheap, but not our production path)?
2. **Persistence scope.** δ-mem paper treats state as within-session; we want cross-session. Is per-user state acceptable, or do we need per-(user, project) keying? B1 currently keys by user.
3. **Train-on-our-conversations question.** Both papers train adapters on public corpora. Do we have / want a curated conversation dataset for adapter fine-tuning, or is off-the-shelf training data acceptable for the first prototype?
4. **Replace vs augment B1 snapshot injection.** Snapshot-in-prompt (M.1 Prefix analog) is the literature-worst topology but it's *already shipped and working*. Replace outright, or run side-by-side as a controlled experiment first?
5. **GPU rental budget.** Both spike-2 and spike-3 need a GPU for adapter training (a few hundred GPU-hours total for a 4.2M-param adapter against a 26B frozen backbone). Is that in scope?

## References

- **intake-539**: Lei et al., "δ-mem: Efficient Online Memory for Large Language Models", arXiv:2605.12357. Code: [github.com/declare-lab/delta-Mem](https://github.com/declare-lab/delta-Mem), [github.com/MindLab-Research/delta-Mem](https://github.com/MindLab-Research/delta-Mem). License: CC-BY-4.0.
- **intake-568**: "Trained Persistent Memory for Frozen Encoder-Decoder LLMs", arXiv:2603.16413. Six methods on Flan-T5-XL. Code: intended-but-not-yet-released.
- **Related active handoff**: `/workspace/handoffs/active/log-linear-gated-deltanet-readiness.md` — DeltaNet kernel work overlaps with δ-mem's delta-rule update primitive; shared engineering payoff.
- **Related active handoff**: `/workspace/handoffs/active/context-folding-progressive.md` — currently hand-waves cross-session persistence; this cluster's M.4/M.6 patterns are the principled replacement.
- **Related completed handoff**: `/workspace/handoffs/completed/orchestrator-conversation-management.md` — B1 User Modeling slot is the direct integration target; current snapshot-in-prompt implementation maps to intake-568 M.1 Prefix (literature-worst topology).
- **Tangentially related**: `internal-kb-rag.md` (RAG is the alternative to attention-resident memory), `multiscreen-attention-evaluation.md` (attention-modification methodology overlap), `cpu-context-regime-coverage.md` (long-context cost is exactly what persistent memory is meant to amortize).
