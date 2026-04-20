# TIDE Calibration-Router Early Exit — Deep Dive

- **Source**: https://github.com/RightNow-AI/TIDE + https://arxiv.org/abs/2603.21365
- **Date**: 2026-04-20
- **Intake IDs**: intake-422, intake-423
- **Authors**: Jaber Jaber, Osama Jaber (RightNow AI)
- **Verdict (initial)**: worth_investigating / not_applicable

---

## 1. Core Idea — What TIDE Actually Does

TIDE trains tiny MLP routers (~0.5M params each) at periodic "checkpoint" layers. During inference, after each checkpoint layer, the router examines the hidden state and decides: "has this token converged?" If yes, the token exits early and skips remaining layers.

The convergence criterion is simple: **cosine similarity between hidden states at consecutive checkpoint layers**. If `cos_sim(h[layer_i], h[layer_{i+1}]) > 0.98` during calibration, that layer pair is marked as "convergent by default." The router then learns to predict convergence at inference time.

**Key insight**: Most tokens converge long before the final layer. Only a few "hard" tokens (typically at decision boundaries or rare vocabulary) actually need all layers.

## 2. Calibration Process — How Routers Are Trained

1. Run 2,000 WikiText samples through the full model
2. At each checkpoint interval, record hidden state pairs
3. Compute cosine similarity between consecutive checkpoint outputs
4. Train a tiny MLP (input: hidden_dim, output: binary) to predict "converged?" vs "needs more layers"
5. Total calibration time: <3 minutes on A100

**The router architecture is trivial**: `Linear(hidden_dim, 128) → ReLU → Linear(128, 1) → Sigmoid`. The checkpoint file is ~4MB total for all routers.

## 3. Our Fork's Existing Infrastructure

The fork already has `n_layer_exit` support across **7 model architectures**:
- `src/models/qwen3.cpp` (our production model)
- `src/models/qwen3moe.cpp` (our MoE model)
- `src/models/qwen2.cpp`
- `src/models/llama.cpp`
- `src/models/qwen3vl-moe.cpp`
- `src/models/qwen3next.cpp`
- `src/models/diff-transformer.cpp`

Current implementation: `llama_set_n_layer_exit(ctx, N)` → all tokens exit at layer N. This is **static** — same exit point for every token. The HSD experiments found this yields near-zero acceptance because most tokens are wrong when you cut layers uniformly.

**TIDE's delta**: Instead of a fixed N for all tokens, let each token decide independently via a learned router. Some tokens exit at layer 10, others at layer 20, hard tokens go all the way.

## 4. Implementation Path in llama.cpp Fork

### 4a. What We Need to Add

| Component | Complexity | Description |
|-----------|-----------|-------------|
| Router weights in GGUF | Medium | Add router tensors to the model file (small — 4MB total) |
| Per-token exit logic | High | Branch the forward pass per-token after each checkpoint |
| Calibration script | Low | Python script to generate router weights from a calibration run |
| Batch compaction (optional) | High | Separate converged from non-converged tokens for efficient batch processing |

### 4b. Implementation Strategy

**Phase 1 — External router, static exit** (low risk, validates concept):
1. Calibrate router weights using the existing model (Python script, ~100 lines)
2. Store router weights as a sidecar file (not in GGUF initially)
3. At inference time, run the router after each checkpoint layer
4. If router says "converge" for ALL tokens in batch → set `n_layer_exit` dynamically
5. This gives per-batch (not per-token) early exit — still a win for single-sequence decoding

**Phase 2 — Per-token exit** (higher complexity):
1. After checkpoint layer, evaluate router per token
2. Tokens that "exit" get their final hidden state passed directly to the LM head
3. Tokens that "continue" proceed through remaining layers
4. Requires splitting the batch at each checkpoint — the main complexity

**Phase 3 — GGUF-embedded routers** (polish):
1. Add router tensors to GGUF format (custom tensor names)
2. Load automatically during model init
3. Expose via server API: `--early-exit-threshold 0.85`

### 4c. Why CPU Gets a Simpler Win

On GPU, the main challenge is batch compaction (different tokens at different layers = irregular computation). On CPU with batch_size=1 (our typical case), **there is no batch to compact**. Each token is processed individually. The router check is trivial:

```
for each checkpoint_layer:
    compute hidden state
    run router (tiny MLP: hidden_dim → 128 → 1)
    if sigmoid_output > threshold:
        skip to LM head
        break
```

For batch_size=1 decode, this is just an `if` statement + a tiny matmul at each checkpoint. The overhead is negligible (~0.01ms per router evaluation on CPU).

## 5. Expected CPU Gains — Realistic Assessment

TIDE reports 6.6-8.1% throughput gain on GPU. On CPU, the picture is different:

| Factor | GPU | CPU (ours) |
|--------|-----|-----------|
| Batch size | 1-128 | 1 (decode) |
| Batch compaction overhead | Significant | None |
| Router evaluation cost | Negligible | Negligible |
| Layer compute cost | ~0.3ms/layer | ~5-15ms/layer (model-dependent) |
| Typical exit point | Layer 24/32 (75%) | TBD — needs calibration |

**If tokens exit at layer 24/32 on average** (skipping 25% of layers), that's 25% fewer layer computations. For Qwen3.6-35B-A3B at ~8ms/layer:
- Full pass: 32 layers × 8ms = 256ms/token
- Early exit (75% layers): 24 layers × 8ms + router overhead = ~193ms/token
- **Potential gain: ~25% decode speedup** (much more than GPU's 6-8%)

CPU benefits MORE than GPU because:
1. No batch compaction overhead
2. Layer compute is the dominant cost (no memory bandwidth hiding)
3. Single-token decoding means no padding waste

## 6. Risk: Quality Degradation

The HSD experiment found that static layer-skip (removing layers uniformly) causes catastrophic quality loss. TIDE's key claim is that **the router prevents this** by only exiting tokens that have genuinely converged.

**Critical validation needed**: Run calibration on our production models (Qwen3.6-35B-A3B, Qwen3.5-27B) and measure:
1. What fraction of tokens exit early at various thresholds?
2. Does quality (perplexity, benchmark scores) hold?
3. Is the convergence pattern consistent across domains?

This is a cheap experiment — calibration is <3 minutes, validation is a standard benchmark run with early exit enabled vs disabled.

## 7. Comparison: TIDE vs LayerSkip vs SWIFT vs Our Static Approach

| Property | Our `n_layer_exit` | LayerSkip | SWIFT | TIDE |
|----------|-------------------|-----------|-------|------|
| Requires fine-tuning | No | Yes (EE head) | Yes (EE head) | **No** (calibration only) |
| Per-token decision | No (fixed N) | Yes | Yes | Yes |
| llama.cpp compatible | Yes (already in fork) | No | No | **Portable** (simple MLP) |
| Calibration cost | None | Training run | Training run | **3 minutes** |
| Quality preservation | Poor (HSD showed) | Good | Good | Claims good |
| Implementation complexity | Done | High | High | **Medium** |

**TIDE is the only approach that is (a) post-training, (b) per-token adaptive, and (c) simple enough to port to llama.cpp.**

## 8. Concrete Next Steps

1. **Write calibration script** (~100 lines Python): Load model via llama-cpp-python, run 2000 WikiText samples, record hidden states at checkpoint layers, train router MLPs, save weights
2. **Add router evaluation to forward pass**: After each checkpoint layer in `src/models/qwen3moe.cpp`, evaluate router and conditionally skip remaining layers
3. **Benchmark**: Compare full-model vs router-gated early exit on frontdoor benchmark
4. **Tune threshold**: Sweep confidence threshold (0.7-0.95) to find quality/speed Pareto

Estimated effort: 2-3 sessions for Phase 1 (external router, per-batch exit). Phase 2 (per-token) adds ~1 session.

## 9. Verdict Delta

| Aspect | Initial Assessment | Post Deep-Dive |
|--------|-------------------|----------------|
| Relevance | low (GPU-only) | **medium-high** (CPU gets bigger % gain, fork has infrastructure) |
| Novelty | medium / low | **medium** (calibration-router concept is the missing piece for our layer-skip patch) |
| Verdict | worth_investigating / not_applicable | **adopt_patterns** → implement calibration-router on our existing `n_layer_exit` infrastructure |
| Implementation feasibility | "requires substantial custom work" | **straightforward** — fork already has layer-skip, just add router logic |
| Expected gain | "6-8% modest" | **15-25%** decode speedup on CPU (no batch compaction overhead, layer compute is dominant cost) |

**Updated verdict: `adopt_patterns`** — The calibration-router concept directly fills the gap between our static `n_layer_exit` (which doesn't work well) and fine-tuning-based approaches (which we can't do). Implementation is medium complexity with high expected payoff on CPU.
