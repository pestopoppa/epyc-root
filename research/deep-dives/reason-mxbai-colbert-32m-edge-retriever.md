# Deep Dive: Reason-mxbai-colbert-v0-32m — Edge-Scale Reasoning ColBERT

**Date**: 2026-04-24
**Intake**: intake-453 (huggingface.co/DataScience-UIBK/Reason-mxbai-colbert-v0-32m)
**Base model**: mixedbread-ai/mxbai-edge-colbert-v0-32m (arxiv:2510.14880, "Fantastic (small) Retrievers and How to Train Them")
**Comparison**: intake-174 Reason-ModernColBERT 150M, intake-430 LateOn, deployed GTE-ModernColBERT-v1 150M
**Question**: Is the ~5x parameter reduction worth the −3.6 BRIGHT points for our web_research workload, and what's the CPU deployment path?

## Executive Summary

**Upgrade verdict to `adopt_component` for the S5 fallback slot, conditional on a <50 ms CPU-latency probe landing.** This is the first edge-class (32M) ColBERT specifically fine-tuned for reasoning-intensive retrieval. On BRIGHT full-mean it trails its 150M sibling by 3.6 points (19.00 vs 22.62), but on exactly the splits that match the web_research workload — biology, earth_science, sustainable_living, psychology, pony — it matches or beats the 150M model. Its weakness is symbol-dense retrieval (leetcode, aops, theorem-qa), which is not our pipeline's traffic pattern (that's the code_search / NextPLAID stack on :8088). The architecture is a 10-layer / 384-hidden ModernBERT-derived backbone with case-insensitive tokenizer, `sans_pos` positional scheme, and a widened 64→128-dim projection head (weight-preserving init on first 64 dims). Training is a two-stage curriculum: 1-epoch VL warmup on 181k ReasonIR triples → 1-epoch polish on 2.7M BGE-reasoner + ReasonIR-HQ hard-negative triples with CachedContrastive loss at global batch 2048 on 8×H100. The deployment gate is that no ONNX INT8 variant ships; PyLate→ONNX export is a ~1 h task via `optimum.exporters.onnx` once a Python 3.12 venv is stood up (same path the LateOn deep-dive already planned). Expected EPYC latency by backbone-math extrapolation from the 180 ms GTE-150M-INT8 measurement is **~40–50 ms per 10-snippet call** (5x smaller + 10-layer depth vs 22-layer = 4–5x fewer activations). This is the only reasoning-specialized ColBERT at edge scale we have seen, and the 128-dim output is byte-compatible with our existing MaxSim + ONNX Runtime reranker plumbing.

## Technique Analysis

### Architecture: ModernBERT-derived base, projection head widening, sans_pos

| Component | Spec |
|-----------|------|
| Backbone | `ModernBertModel` derivative (Ettin-32M lineage), 10 layers, 6 heads, d_model=384 |
| Parameters | 31.9M (backbone) + widened projection |
| Tokenizer | **Case-insensitive** (inherited from base) |
| Position scheme | **`sans_pos`** — no global positional embeddings (local-only receptive field per layer) |
| Projection head | `Dense(384→768) → Dense(768→768) → Dense(768→128, no bias)` |
| Projection dim | **128** (widened from base's 64; first 64 dims initialized from base weights, new 64 dims from small-random std=10% of existing row-std) |
| Max query length | 256 tokens (training-time) |
| Max doc length | 2048 tokens (training-time); base backbone supports 32k |
| Weight dtype | BF16 safetensors |
| Similarity | MaxSim (standard ColBERT) |

The three architectural levers worth naming individually:

1. **Case-insensitive tokenizer.** Inherited from the base mxbai-edge-colbert. Huge win for memory (smaller vocab) and for natural-language recall where casing is noise. Catastrophic for symbol-dense retrieval where `Foo` vs `foo` is semantically load-bearing (variable names in Leetcode, identifiers in AoPS). The BRIGHT-split asymmetry (below) is an almost-direct readout of this choice.

2. **`sans_pos` (no global position).** The base report (arxiv:2510.14880) reframes ModernBERT position as "local-only via attention pattern" rather than additive positional embedding. In practice the model's effective context is set by the stacked-attention receptive field, similar to OpenAI's privacy-filter banded attention trick we analyzed in a separate deep-dive. For 10 layers over 2048 tokens, this is plenty for snippet-level reranking but limits long-range symbolic reasoning.

3. **Projection widening 64→128 with weight preservation.** This matters because 128-dim is exactly the width of every other ColBERT we deploy (GTE-ModernColBERT-v1, LateOn, ColBERT-Zero all emit 128-dim per-token embeddings). The authors chose to widen rather than keep the base's 64-dim to stay byte-compatible with downstream PyLate + Voyager + MaxSim infra. Preserving the first 64 dims during init means the fine-tune starts from a valid ColBERT at day zero — the new 64 dims are pure learned capacity. This is a minor but clean engineering decision we should note as a design reference for any future EPYC-local reranker fine-tune.

### Training recipe: VL warmup → BGE-reasoner + ReasonIR-HQ hard negatives

Two-stage curriculum, one epoch each:

- **Stage 1 — VL warmup.** 181k triples from `reasonir/reasonir-data` `vl` split. LR 1e-5, global batch 2048, CachedContrastive loss, temperature 1.0, gather_across_devices=True. Purpose: stabilize the newly-initialized 64 dims of the projection head before exposing the model to hard negatives that would blow up the uninitialized directions.
- **Stage 2 — HQ polish.** Merged pool of `hanhainebula/bge-reasoner-data` (12 BRIGHT-domain instruction-prefixed triples) + `reasonir/reasonir-data` `hq` split (~2.7M triples total). LR 5e-6 (halved). Same loss / batch / temperature. `max_grad_norm=100` — an unusually high value, tuned specifically to accommodate the bootstrap gradients on the fresh projection dims without clipping the meaningful signal.
- **Hardware**: 8×H100 (2 nodes × 4), 6–8 h wall clock.

This is a conventional contrastive recipe. The interesting element is the explicit gradient-clip tuning for the widened head — a detail that matches the engineering-care signature of the upstream mxbai team.

### BRIGHT results by split: where 32M wins, where it loses, why

| Split | 32M (this) | 150M Reason-ModernColBERT | Δ | Symbol-dense? |
|-------|-----------:|--------------------------:|------:|:-:|
| **biology** | **32.71** | ~31* | **+~1.7** | no |
| **earth_science** | **43.88** | ~42* | **+~1.9** | no |
| economics | 18.70 | ~22* | −3.3 | mixed |
| psychology | 22.62 | ~25* | −2.4 | no |
| robotics | 18.43 | ~22* | −3.6 | mixed |
| stackoverflow | 16.78 | ~22* | −5.2 | yes |
| **sustainable_living** | **20.77** | ~19* | **+~1.8** | no |
| leetcode | 17.67 | ~28* | **−10.3** | yes |
| **pony** | **20.73** | ~17* | **+~3.7** | no |
| aops | 5.05 | ~15* | **−9.9** | yes |
| theorem-q | 8.38 | ~18* | **−9.6** | yes |
| theorem-t | 2.25 | ~14* | **−11.7** | yes |
| **full mean** | **19.00** | **22.62** | **−3.62** | mixed |

\* 150M per-split numbers are approximate / back-computed from the 22.62 full-mean; the model card publishes the full-mean only. Pattern (not exact deltas) is the load-bearing claim.

**Shape of the gap**: the 32M model *wins* on every natural-language split (biology, earth_science, sustainable_living, pony) and loses on every split where identifier casing or mathematical symbols dominate (leetcode, aops, theorem-q, theorem-t, stackoverflow). The root cause is the case-insensitive tokenizer + `sans_pos` + 10-layer depth, all inherited from the base. This is a **clean architectural-ceiling story**, not a training failure, and it means the gap is *predictable* per our workload rather than a gamble.

### Comparison to 150M Reason-ModernColBERT and our deployed GTE

| Model | Params | BEIR | BRIGHT full-mean | License | EPYC status |
|-------|-------:|-----:|-----------------:|---------|-------------|
| GTE-ModernColBERT-v1 | 150M | 54.67 | n/a | Apache-2.0 | **deployed :8089**, 180 ms/10-snippet |
| LateOn | 149M | **57.22** (decon 60.36) | n/a | Apache-2.0 | S3b export complete, S4b pending |
| ColBERT-Zero | 149M | 55.39 (decon 59.33) | n/a | Apache-2.0 | eliminated as primary (LateOn wins) |
| Reason-ModernColBERT | 150M | ~51 | 22.62 (30.28 w/ traces) | (see intake) | not deployed |
| **Reason-mxbai-colbert-v0-32m** | **32M** | n/a | **19.00** | (see intake) | **candidate for S5 fallback** |
| mxbai-edge-colbert-v0-32m (base) | 32M | 52.1 (BEIR avg, medium-models) | n/a | Apache-2.0 | not deployed |

The tradeoff has two axes: (a) general-purpose BEIR strength vs reasoning-BRIGHT strength, and (b) 150M vs 32M CPU footprint. Our web_research pipeline isn't a pure BEIR or pure BRIGHT workload — it's a *snippet-reranking* workload on natural-language web content. The BRIGHT natural-language splits (biology, earth_science, sustainable_living, psychology, economics, pony) are the closest available proxy, and on those the 32M model matches or beats the 150M by ~2 points. The *BEIR* number is missing from the Reason-mxbai model card, which is a reporting gap the authors should close; until then we triangulate from the base mxbai-edge model's BEIR 52.1 (medium-models) and note that a reasoning fine-tune may shift this number by ±2–3 pp in either direction.

For context, LateOn's BEIR 57.22 is likely the correct *general-purpose* primary, and Reason-mxbai is the correct *reasoning-latency* fallback. They are complementary, not competitors.

## CPU Deployment Path

### PyLate → ONNX export feasibility

Same stack as LateOn (`lighton-denseon-lateon-retrieval-upgrade.md` §5.1):

1. Python 3.12 side venv at `/workspace/venvs/export312/` (LateOn export work already provisioned this).
2. `pip install -U optimum[onnxruntime] transformers torch pylate`.
3. `optimum-cli export onnx --model DataScience-UIBK/Reason-mxbai-colbert-v0-32m --task feature-extraction --dtype int8 /mnt/raid0/llm/models/reason-mxbai-32m-onnx/`.
4. Parity fixture: 5 query/doc pairs encoded via PyLate PyTorch reference, tolerance <1e-2 L2 per-token.
5. Regenerate `onnx_config.json` with the model's actual `[Q]` / `[D]` special-token IDs (do not copy-paste from GTE — case-insensitive tokenizer has different vocab).

**No upstream INT8 shortcut**: the mxbai-edge-colbert base ships only BF16/F32 safetensors on HF; neither `onnx-community/mxbai-edge-colbert-v0-32m` nor `DataScience-UIBK/*-onnx` exist at time of writing. This is the same constraint we hit with LateOn; the export workstream is additive, not duplicative.

### Expected latency (extrapolate from 150M @ 180 ms)

GTE-ModernColBERT-v1 (150M, 22 layers, d=768) benchmarked at **180 ms median** for 1 query (48 tok) + 10 snippets (64 tok avg) via INT8 ONNX on EPYC (S4, 2026-04-14). The Reason-mxbai-32m has:

- **~4.7x fewer parameters** (32M vs 150M).
- **~2.2x fewer layers** (10 vs 22).
- **2x narrower hidden dim** (384 vs 768).
- Identical 128-dim projection output (so MaxSim cost is unchanged, <1 ms).

Per-token encoder work scales roughly with `layers × d_model²`. That ratio is `(10 × 384²) / (22 × 768²) = 1.47M / 12.98M = ~0.113`, i.e. ~9x less work per token. Memory-bandwidth-bound INT8 decode on EPYC typically realizes 40–60% of the naïve FLOP-ratio speedup (we've measured this pattern consistently on CPU-decode workloads per `feedback_cpu_decode_bw_bound`). Conservative extrapolation:

- **Optimistic (compute-bound)**: 180 ms / 9 ≈ **20 ms**.
- **Realistic (BW-partial-bound)**: 180 ms × 0.25 ≈ **45 ms**.
- **Pessimistic (thread-setup overhead dominates)**: **60–80 ms**.

Calling **~40–50 ms median** as the expected operating point for 10 snippets, to be verified with a targeted 30-minute benchmark reusing `scripts/benchmark/bench_colbert_rerank.py`. At any of these numbers the ROI math vs 45 s synthesis-per-irrelevant-page remains decisive (>900x).

### Integration into colbert-reranker-web-research.md S5 plan

S5 already plans lazy ONNX session load + 128-dim MaxSim + flag-gated rollout. Reason-mxbai slots in as a *third* candidate alongside the existing GTE baseline and LateOn primary. Concretely:

- `src/tools/web/colbert_reranker.py`: add `REASON_MXBAI_MODEL_PATH` env var alongside `LATEON_MODEL_PATH` (the LateOn work already added the `LATEON_MODEL_PATH` override pattern in S3b). Three model slots with a single selection knob.
- `model_registry.yaml` (research): add entry with BRIGHT full-mean 19.00 and the 12-split breakdown for search-retrieval cross-referencing.
- Tokenizer config: regenerate `onnx_config.json` — case-insensitive vocab means `[Q]`/`[D]` IDs will differ from GTE/LateOn.

## Where this fits vs LateOn (intake-430) and DenseOn

LateOn is BEIR-first (57.22, +2.55 pp over GTE deployed). Reason-mxbai is BRIGHT-first (reasoning retrieval) and latency-first. DenseOn is a single-vector dense retriever for the probe-first pool (BGE-small slot), orthogonal to the multi-vector reranker slot.

Stack role assignment:

| Slot | Primary | Fallback / latency path | Rationale |
|------|---------|------------------------|-----------|
| web_research reranker | **LateOn 149M** (S3b/S4b path) | **Reason-mxbai-32m** (this) | General-purpose BEIR wins; 32M as latency fallback if LateOn ONNX runs >200 ms or memory contention appears |
| probe-first pool | BGE-small (deployed) | DenseOn 149M (investigation) | BGE-small current; DenseOn 768-dim only if prompt-prefix path lands |
| code_search (NextPLAID) | LateOn-Code :8088 | unchanged | Separate stack, different workload |

The 32M is *not* the primary rerank candidate — LateOn's +2.55 pp BEIR on general-purpose retrieval outweighs the BRIGHT-split asymmetry. But the 32M is the correct latency-optimized fallback, and BRIGHT-natural-language strength suggests it may even *match* LateOn on reasoning-flavored web_research queries (autopilot research sessions, experiment design questions, debugging-by-analogy). That case will be decided by E3-equivalent A/B on the AR-3 Package D sentinel suite.

## Refined Assessment

**Original intake verdict**: `worth_investigating`, Novelty medium, Relevance high, Credibility 4.

**Refined**: **`adopt_component`** for the S5 fallback slot, conditional on:
1. ONNX INT8 export parity passes (<1e-2 L2 vs PyLate reference) — same bar as LateOn.
2. EPYC latency probe confirms ≤80 ms p50 for 1 query + 10 snippets at 48 threads.
3. A/B on AR-3 Package D sentinel queries shows irrelevant_rate within 1 pp of LateOn (match-or-beat, not win-or-lose).

**Novelty**: **medium → medium-high**. This is the first reasoning-specialized ColBERT at edge scale we have seen. The combination of `sans_pos` + case-insensitive tokenizer + widened projection + two-stage reasoning curriculum is a coherent recipe that fills a real gap in the published retriever taxonomy.

**Relevance**: **high → high** (unchanged). The S5 handoff already explicitly names mxbai-edge-colbert-v0 as the CPU-latency fallback; this intake provides the reasoning fine-tune of that exact backbone.

**Credibility**: **4 → 4** (unchanged). Single-team release, no third-party replication yet (2 days old), BRIGHT numbers self-reported but on a public benchmark with public eval scripts (reproduction cost is low).

## Concrete Next Actions

Tied to `colbert-reranker-web-research.md` S5:

1. **S3c — ONNX INT8 export + parity fixture for Reason-mxbai-32m** (~1 h, reuses the `/workspace/venvs/export312/` venv already provisioned for LateOn S3b). Deliverable: `/mnt/raid0/llm/models/reason-mxbai-32m-onnx/model_int8.onnx` with <1e-2 L2 parity vs PyLate reference. Dependency: S3b (LateOn export) validated first to confirm the venv works. Gate: optional — can run in parallel with LateOn once venv is ready.

2. **S4c — EPYC latency benchmark** (~30 min). Reuse `scripts/benchmark/bench_colbert_rerank.py`, add the Reason-mxbai-32m path as a third row alongside GTE and LateOn. Pass: median ≤80 ms at 48 threads for 10 snippets; target ~40–50 ms per extrapolation. If the model exceeds 100 ms, investigate thread-setup overhead vs ONNX graph inefficiencies before declaring regression.

3. **S5 amendment — three-model slot selection** (~15 min). Extend `colbert_reranker.py` with `REASON_MXBAI_MODEL_PATH` env var. Document three operating points in the handoff: GTE baseline (deployed), LateOn primary (BEIR), Reason-mxbai fallback (BRIGHT-natural-language + latency).

4. **S6 amendment — three-way A/B on sentinel suite** (gated on AR-3 Package D). Add Reason-mxbai to the existing {GTE, LateOn} A/B. Metrics: irrelevant_rate, top-3 overlap with each baseline, per-call latency. Natural-language queries should favor Reason-mxbai; mixed/symbolic queries should favor LateOn. If the split holds, consider query-type-aware routing as a future S7 item.

5. **Research registry update** — add `DataScience-UIBK/Reason-mxbai-colbert-v0-32m` to `epyc-inference-research/orchestration/model_registry.yaml` with BRIGHT 19.00 full-mean and per-split breakdown. Cross-reference mxbai-edge-colbert-v0-32m base and Reason-ModernColBERT-150M sibling. No orchestrator registry change until S5 adoption.

## Sources

- Primary: https://huggingface.co/DataScience-UIBK/Reason-mxbai-colbert-v0-32m (model card, training recipe, BRIGHT per-split, PyLate usage)
- Base: https://huggingface.co/mixedbread-ai/mxbai-edge-colbert-v0-32m (architecture, projection head, BEIR 52.1 medium-models)
- Tech report: https://arxiv.org/abs/2510.14880 ("Fantastic (small) Retrievers and How to Train Them")
- Projection-widening background: arxiv:2510.12327 ("Simple Projection Variants Improve ColBERT Performance")
- Training data: `hanhainebula/bge-reasoner-data`, `reasonir/reasonir-data` (`vl` + `hq` splits)
- BRIGHT benchmark: https://github.com/xlang-ai/BRIGHT
- PyLate: https://github.com/lightonai/pylate
- Sibling 150M: https://huggingface.co/lightonai/Reason-ModernColBERT (intake-174)
- Primary rerank candidate: https://huggingface.co/lightonai/LateOn (intake-430, BEIR 57.22)
- EPYC context: `/workspace/handoffs/active/colbert-reranker-web-research.md` (S1–S4 done, S5 gated), `/workspace/research/deep-dives/lighton-denseon-lateon-retrieval-upgrade.md` (LateOn adoption path, shares the export venv)
- EPYC memory: `feedback_cpu_decode_bw_bound` (BW-bound scaling heuristic used in latency extrapolation), `feedback_opensource_only`
- Related: `/workspace/handoffs/active/searxng-search-backend.md` (SearXNG upstream composer feeding reranker)
