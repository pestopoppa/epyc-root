# Summary-Token Attention Readiness Tracker — KSA + GSA Cluster

**Status**: stub (MONITORING) — gates not met as of 2026-04-29
**Created**: 2026-04-29 (via research-intake of intake-502 KSA + intake-507 GSA)
**Updated**: 2026-04-29 (initial)
**Categories**: kv_cache, context_extension, context_management, ssm_hybrid, training_distillation
**Workstream**: Inference Acceleration
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**:
- [`multiscreen-attention-evaluation.md`](multiscreen-attention-evaluation.md) — sub-quadratic attention survey, intake-502 + intake-507 documented under same-day-expansion sub-section
- [`log-linear-gated-deltanet-readiness.md`](log-linear-gated-deltanet-readiness.md) — sibling readiness tracker (template for this stub)
- [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) — related but RETROFIT (post-hoc), not architectural CPT
- [`triattention-kv-selection.md`](triattention-kv-selection.md) — also RETROFIT KV selection
- [`lightning-attention-port.md`](lightning-attention-port.md) — sibling architectural-port handoff (different mechanism family)

## Objective

Track activation conditions for the **summary-token / gist-token cluster** of architectural attention mechanisms. Two papers from this cluster are in our intake (April 2026), both requiring continued pretraining (CPT) — neither has a path to retrofit our existing Qwen3.5/3.6/2.5 production stack on EPYC CPU. This handoff exists to monitor activation gates and provide an immediate execution plan when any gate fires.

## Cluster Members

| Intake | Paper | Mechanism | Distinguishing Feature |
|--------|-------|-----------|------------------------|
| **intake-502** | Kwai Summary Attention (Kuaishou OneRec, arxiv:2604.24432) | Learnable summary tokens injected at chunk boundaries (chunk size k=8 default); 3:1 KSA-to-Full layer ratio | **Persistent summary visibility**: all summary tokens always visible to text tokens. Soft compression, larger active context budget per query. |
| **intake-507** | Gist Sparse Attention / GSA + H-GSA (Stanford, arxiv:2604.20920) | Learnable gist tokens at chunk boundary (similar primitive); hard top-k chunk selection at decode time; selective unfolding restores raw KV pairs for selected chunks | **Hard top-k + selective unfolding**: unselected chunks invisible; selected chunks unfold to raw KV. Sharp compression, smaller active context budget. **Hierarchical H-GSA achieves log-linear decode** — only mechanism in cluster scaling naturally to 1M+ context. |

## Mechanism Comparison

| Axis | KSA (intake-502) | GSA (intake-507) |
|------|------------------|------------------|
| **Token primitive** | Summary tokens at chunk boundary | Gist tokens at chunk boundary |
| **Selection mechanism** | None (all summaries always visible) | Hard top-k via gist relevance score `q · k_g` |
| **Distant context access** | Through summaries only | Through selected chunks (raw KV restored) + selected gists |
| **Compression style** | Soft (linear KV growth, factor k reduction) | Sharp (hard top-k bounded context: k·(1+L)+M total) |
| **Hierarchical variant** | Not in paper | H-GSA: gist-of-gist, log-linear decode |
| **CPT recipe** | 3 stages (summary token adaptation + parameter annealing + sequence extension) | 2 stages (CPT with gist mask required; selective finetuning optional) |
| **Reported strengths** | RULER-128K +5.81 vs Full (CPT); +16.60 (scratch); decode 1.06× Full | LongBench 32× +5.77 vs ActivationBeacon; H-GSA at 16× = 46.48 (log-linear) |
| **Code released** | github.com/Kuaishou-OneRec/KSA (training scripts) | github.com/yuzhenmao/gist-sparse-attention (Stage 1 CPT + selective unfolding) |
| **Failure modes** | Compression ratio fixed by k regardless of input complexity; persistent visibility may dilute attention | Hard top-k starves model when info is spread weakly across many chunks; KSA's soft fallback handles this better |

**Why a JOINT readiness tracker (not split per-paper)**: identical gating, identical infrastructure needs in llama.cpp, same architectural-CPT blocker. Splitting would create maintenance overhead with no payoff. Mechanism differences are documented above and surfaced when activation occurs.

## Gate Criteria (any one triggers activation)

All gating is OR-logic: ANY of these fires → activate the implementation plan below.

- [ ] **Gate A** — Pretrained checkpoint of a model we serve (Qwen2.5/3.5/3.6 family, or any base we already deploy) released with KSA-style summary tokens OR GSA-style gist tokens
- [ ] **Gate B** — Community llama.cpp PR adding general support for: (i) dynamic top-k chunk masking + raw-KV restoration (covers GSA), or (ii) chunk-aligned summary KV cache layout (covers KSA)
- [ ] **Gate C** — GPU acquisition that lets us run our own CPT (covers KSA's three-stage recipe AND GSA's Stage-1-only recipe). Cross-ref `project_dgx_spark_target` memory.
- [ ] **Gate D** — Major-lab next-generation model adopts summary-token attention as default architecture (e.g., Qwen 4 with KSA, DeepSeek-V5 with summary tokens). Triggers automatic engagement when GGUF support lands.

## Monitoring Targets

| Target | Cadence | Signal |
|--------|---------|--------|
| github.com/Kuaishou-OneRec/KSA | Weekly | New releases, model checkpoints, llama.cpp port discussions |
| github.com/yuzhenmao/gist-sparse-attention | Weekly | New releases, scaled checkpoints (currently only Qwen2-7B + Llama3.2-1B) |
| HuggingFace model registry | Monthly | Search for "ksa", "summary token", "gist token" in model names/descriptions |
| llama.cpp upstream (ggml-org) | Monthly | PRs mentioning "summary token", "gist", "chunk attention", "selective unfolding" |
| arxiv.org cs.CL | Monthly | Follow-up papers in summary-token cluster; competing mechanisms |
| Major-lab model announcements | Monthly | Qwen, DeepSeek, Kimi, Meta, Google releases with summary-token mechanisms |

Optional: schedule a weekly background agent via `/schedule` to check the two GitHub repos and ping when commits or releases land.

## Activation Plan (when ANY gate fires)

### Phase 1 — Inference path port (~1-2 weeks)

For KSA:
- Implement chunk-aligned KV cache layout (Current Chunk + Sliding Chunk Text + Summary Token Buffer per paper Figure 4)
- Reuse contiguous-tensor decode pattern from KSA paper Section 2.3
- Mask construction: chunk-aligned sliding window + persistent summary visibility
- New ggml ops: likely none required; use existing attention with custom mask

For GSA:
- Implement gist-relevance scoring as standard `q · k_g` (no new op)
- Implement hard top-k chunk selection at decode (potentially reuse `ggml_top_k` from PR #21149's DSA work — cross-pollinate)
- Selective unfolding: dynamic restoration of raw KV pairs for selected chunks into active context window (this is the hard part; non-trivial mask construction)
- For H-GSA: hierarchical gist-of-gist routing (additional layer of indirection over Phase 1)

For both:
- Architecture-specific GGUF metadata (`architecture = "ksa"` or `"gsa"`, chunk size, summary/gist embedding indices)

### Phase 2 — GGUF converter (~3-5 days)

Extend `convert_hf_to_gguf.py` with appropriate architecture detection + tensor mapping. Reuse Lightning Attention port's converter pattern (intake-503) where possible — both deal with non-standard attention mechanisms.

### Phase 3 — Quality validation (~1 week, GATED on inference approval)

- RULER suite at 4K / 32K / 128K — replicate paper claims within tolerance
- NIAH / Multivalue / Multiquery / Variable Tracking — KSA reports +30 on VT vs Full at 128K; reproduce or refute
- Decode throughput vs MLA / GDN baselines — confirm 1.06× Full claim (KSA) or improvement signal (GSA)
- PPL bit-exact gates per `cpu-benchmark-rigor-and-revalidation.md` protocol

### Phase 4 — Integration (~1 week)

- Cherry-pick into `production-consolidated-v3` if production-viable
- Update model_registry.yaml with the new architecture
- Add to orchestrator stack management

## Why GSA's "Extremely Actionable" Framing Is Conditional

The user flagged GSA as "extremely actionable" during this intake session. This requires unpacking:

- **Actionable in research/architecture sense**: yes — clear mechanism, code released, immediate fit into existing intake/handoff structure.
- **Actionable in deployment sense**: NO — GSA still requires Stage 1 continued pretraining. Without a checkpoint of a model we serve, there's nothing to deploy. Without GPU, there's no path to produce one ourselves.
- **Actionable in port sense**: PARTIALLY — we COULD port the inference path to llama.cpp (Phase 1 above) preemptively, so when a checkpoint releases we're ready to test in days not weeks. But this has opportunity cost vs the Lightning Attention port (which has a model immediately) and the DSA contribution (which has an active upstream PR).

**Decision**: don't preemptively port GSA inference path. Keep this stub as a tracker; activate only when a gate fires.

## Why KSA / GSA Are NOT in the Lightning Attention Port

Lightning Attention is mechanically a constant-`g` GLA op (existing infrastructure). KSA and GSA require new mask construction, new KV cache layout (KSA's contiguous tensor design), and dynamic top-k + raw-KV restoration (GSA's selective unfolding). These are fundamentally different implementation tracks despite both being "sub-quadratic attention."

The Lightning Attention port is **active** (3-5 day effort) because the kernel exists.
The KSA/GSA port is **deferred** (1-2 week effort per paper) because the mask + KV-cache infrastructure doesn't exist.

If we ever decide to port preemptively, the GSA selective-unfolding mechanism shares some primitives with PR #21149's DSA top-k masking — there's potential cross-pollination if we end up working on both.

## Cross-References

- **intake-502** (KSA paper) — full architecture + benchmark numbers
- **intake-507** (GSA paper) — full architecture + benchmark numbers + comparison table to KSA
- `/workspace/research/deep-dives/` — no dedicated KSA or GSA deep-dive yet (architecture analysis is in the same-day-expansion sub-section of `multiscreen-attention-evaluation.md`)
- `feedback_no_concurrent_inference.md` (memory) — applies to all Phase 3 quality validation work

## Notes

This handoff is deliberately a STUB until a gate fires. Don't add implementation work here — that goes into a new active handoff (e.g., `ksa-port.md` or `gsa-port.md`) when activation occurs. The stub itself only tracks the gates and watch list.

The `log-linear-gated-deltanet-readiness.md` template was used as the structural model for this file.
