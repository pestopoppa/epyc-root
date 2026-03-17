# Handoff: DFlash Block Diffusion Speculative Decoding

**Status**: Phase 0 COMPLETE (inspection done). Phase 1 UNBLOCKED.
**Created**: 2026-03-17
**Updated**: 2026-03-17
**Related**: [`inference-acceleration-index.md`](inference-acceleration-index.md), [`tree-speculation-numa-drafting.md`](tree-speculation-numa-drafting.md), [`ssm-hybrid-acceleration.md`](ssm-hybrid-acceleration.md)

## Agent Operating Instructions

- After every significant step: update `progress/YYYY-MM/YYYY-MM-DD.md`
- After every task: `source scripts/utils/agent_log.sh && agent_task_end "description" "success|failure"`
- Before context compaction risk (~60% usage): persist findings to this handoff
- Build only on `feature/dflash-speculation` branch, never touch `production-consolidated-v2`
- Worktree: `/mnt/raid0/llm/llama.cpp-dflash` (isolated from production build)
- Pre-downloaded models are at `/mnt/raid0/llm/cache/dflash/` (see Phase 0)
- Update [`inference-acceleration-index.md`](inference-acceleration-index.md) if status changes

## Objective

Implement DFlash (block diffusion speculative decoding) in llama.cpp for CPU inference. DFlash uses a lightweight diffusion model to draft multiple tokens in parallel via iterative denoising, conditioned on the target model's hidden states. Unlike autoregressive drafting, DFlash generates all draft tokens simultaneously in O(1) sequential steps (fixed denoising iterations), making it a natural tree builder.

## Background

### What is DFlash?

DFlash trains a small (~0.5-1B) transformer as a block diffusion model. Given:
- Hidden states from specific layers of the target model (conditioning signal)
- A block of noisy token embeddings (initialized from noise)

The drafter iteratively denoises the block over T steps (typically T=8-16) to produce a block of draft tokens. All tokens in the block are generated in parallel — the drafter uses causal attention within the block but is conditioned on the target's context.

Key properties:
- **O(1) draft latency**: Fixed denoising steps, independent of block size
- **Block size 16**: Paper uses b=16 tokens per draft block
- **Conditioning layers**: Drafter receives hidden states from specific target model layers (typically 2-3 layer taps)
- **Acceptance**: Paper reports τ=6.49 accepted tokens per round on Qwen3.5-35B-A3B (GPU)

### DFlash Drafter Availability

| Production Role | Target Model | DFlash Drafter | Status |
|----------------|-------------|---------------|--------|
| frontdoor | Qwen3-Coder-30B-A3B | `z-lab/Qwen3-Coder-30B-A3B-DFlash` (0.5B) | **AVAILABLE** |
| coder_escalation | Qwen2.5-Coder-32B | None published | GAP — needs custom training |
| architect_general | Qwen3-235B-A22B | None published | GAP — needs custom training |
| architect_coding | Qwen3-Coder-480B-A35B | None published | GAP — needs custom training |
| ingest_long_context | Qwen3-Next-80B-A3B | None | HYBRID WALL + no drafter |

**Note**: `Qwen3-Coder-Next-DFlash` targets `Qwen/Qwen3-Coder-Next` (80B-A3B hybrid Coder), NOT our `Qwen3-Next-80B-A3B` (non-Coder). Different models, incompatible hidden state distributions. Both are hybrid → recurrent verification wall on CPU.

## Model Paths

All models verified on disk:

| Role | Model | Path |
|------|-------|------|
| Target (frontdoor) | Qwen3-Coder-30B-A3B Q4_K_M | `/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` |
| Current AR drafter | Qwen3-Coder-DRAFT-0.75B Q4_0 | `/mnt/raid0/llm/models/Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf` |
| DFlash drafter (safetensors) | Qwen3-Coder-30B-A3B-DFlash | `/mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash/` |
| DFlash dev drafter (safetensors) | Qwen3-8B-DFlash-b16 | `/mnt/raid0/llm/cache/dflash/Qwen3-8B-DFlash-b16/` |
| GGUF output (convention) | DFlash GGUFs | `/mnt/raid0/llm/cache/dflash/{model}-{quant}.gguf` |

## Phase 0 — Drafter Inventory & Download

**Status**: ✅ COMPLETE (2026-03-17)

### Downloads

Models pre-downloaded to `/mnt/raid0/llm/cache/dflash/`:

```bash
# Development model (smallest, fastest iteration)
huggingface-cli download z-lab/Qwen3-8B-DFlash-b16 \
  --local-dir /mnt/raid0/llm/cache/dflash/Qwen3-8B-DFlash-b16

# Production frontdoor drafter
huggingface-cli download z-lab/Qwen3-Coder-30B-A3B-DFlash \
  --local-dir /mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash
```

### Inspection Results (2026-03-17)

**Qwen3-8B-DFlash-b16** (development model):

| Property | Value |
|----------|-------|
| Architecture | `DFlashDraftModel` |
| Layers | 5 (all `full_attention`, NO recurrent) |
| Target layers tapped | `[1, 9, 17, 25, 33]` (5 taps from 36-layer Qwen3-8B target) |
| Hidden size | 4096 |
| Attention heads | 32 (KV heads: 8, head_dim: 128) |
| Intermediate size | 12288 |
| Block size | 16 |
| Max context | 40,960 |
| Vocab size | 151,936 (matches Qwen3 family) |
| Dtype | bfloat16 |
| Mask token ID | 151669 |
| RoPE theta | 1,000,000 |
| Tied embeddings | false |
| Activation | silu |

**Qwen3-Coder-30B-A3B-DFlash** (production frontdoor drafter):

| Property | Value |
|----------|-------|
| Architecture | `DFlashDraftModel` |
| Layers | 8 (all `full_attention`, NO recurrent) |
| Target layers tapped | `[1, 12, 23, 34, 45]` (5 taps from 48-layer Qwen3-Coder-30B-A3B target) |
| Hidden size | 2048 |
| Attention heads | 32 (KV heads: 4, head_dim: 128) |
| Intermediate size | 6144 |
| Block size | 16 |
| Max context | 262,144 |
| Vocab size | 151,936 (matches Qwen3 family) |
| Dtype | bfloat16 |
| Mask token ID | 151669 |
| RoPE theta | 10,000,000 |
| Tied embeddings | false |
| Activation | silu |

**Key observations**:
- Both are pure attention transformers — no recurrent layers. Clean GGUF conversion path.
- Both use standard Qwen3 `model_type` — may allow reuse of existing Qwen3 converter with minimal changes.
- 5 target layer taps in both, but the dev model has 5 drafter layers while production has 8 drafter layers.
- Hidden size DIFFERS from target: dev drafter 4096 == Qwen3-8B's 4096 (matches), production drafter 2048 ≠ Qwen3-Coder-30B-A3B's 3584 (needs conditioning projection).
- `mask_token_id` 151669 is the diffusion noise token — used for initializing noisy blocks.
- Both have `auto_map` pointing to `dflash.DFlashDraftModel` — custom HF model class (not standard Qwen3ForCausalLM).

**Inspection CLI** (for verification):
```bash
python3 -c "
import json
for name, path in [
    ('Qwen3-8B-DFlash-b16', '/mnt/raid0/llm/cache/dflash/Qwen3-8B-DFlash-b16'),
    ('Qwen3-Coder-30B-A3B-DFlash', '/mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash')
]:
    cfg = json.load(open(f'{path}/config.json'))
    print(f'=== {name} ===')
    print(f'  layers: {cfg[\"num_hidden_layers\"]}')
    print(f'  layer_types: {cfg[\"layer_types\"]}')
    print(f'  target_layer_ids: {cfg[\"dflash_config\"][\"target_layer_ids\"]}')
    print(f'  hidden_size: {cfg[\"hidden_size\"]}')
    print(f'  heads: {cfg[\"num_attention_heads\"]} / kv_heads: {cfg[\"num_key_value_heads\"]}')
    print(f'  block_size: {cfg[\"block_size\"]}')
    print(f'  vocab_size: {cfg[\"vocab_size\"]}')
    print()
"
```

### Tensor Name Mapping

Document the mapping from HF safetensors to GGUF tensor names. Key tensors to identify:
- Embedding layer (likely shared with target)
- LM head (likely shared with target)
- Conditioning projection layers (hidden state → drafter input)
- Self-attention layers (Q/K/V/O)
- FFN layers
- Denoising schedule embeddings (timestep conditioning)
- Layer norms

**Tensor inventory CLI** (run during Phase 1):
```bash
python3 -c "
from safetensors import safe_open
import glob
path = '/mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash'
for f in sorted(glob.glob(f'{path}/*.safetensors')):
    with safe_open(f, framework='pt') as sf:
        for k in sorted(sf.keys()):
            t = sf.get_tensor(k)
            print(f'{k:60s} {list(t.shape)}  {t.dtype}')
"
```

### Registry

Registered in `epyc-inference-research/orchestration/model_registry.yaml` under `dflash_drafters` section.

## Phase 1 — GGUF Conversion & Loading

**Status**: Not started — UNBLOCKED (Phase 0 complete)
**Branch**: `feature/dflash-speculation` off `production-consolidated-v2`
**Worktree**: `/mnt/raid0/llm/llama.cpp-dflash`

### Tasks

1. Create branch and worktree:
   ```bash
   cd /mnt/raid0/llm/llama.cpp
   git worktree add /mnt/raid0/llm/llama.cpp-dflash -b feature/dflash-speculation production-consolidated-v2
   ```

2. Write `convert_hf_to_gguf.py` model class for DFlash drafter:
   - Handle shared embedding + LM head (precedent: MTP Steps 1-4 in `mtp-speculative-decoding.md`)
   - Map diffusion-specific tensors (timestep embeddings, conditioning projections)
   - Support block_size as GGUF metadata
   - Key: `dflash_config.target_layer_ids` and `dflash_config.mask_token_id` must be stored as GGUF metadata

3. Convert both models:
   ```bash
   cd /mnt/raid0/llm/llama.cpp-dflash

   # Dev model — start here (smaller, faster iteration)
   python convert_hf_to_gguf.py \
     /mnt/raid0/llm/cache/dflash/Qwen3-8B-DFlash-b16 \
     --outfile /mnt/raid0/llm/cache/dflash/Qwen3-8B-DFlash-b16-f16.gguf \
     --outtype f16

   python convert_hf_to_gguf.py \
     /mnt/raid0/llm/cache/dflash/Qwen3-8B-DFlash-b16 \
     --outfile /mnt/raid0/llm/cache/dflash/Qwen3-8B-DFlash-b16-Q4_K_M.gguf \
     --outtype q4_k_m

   # Production model
   python convert_hf_to_gguf.py \
     /mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash \
     --outfile /mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash-f16.gguf \
     --outtype f16

   python convert_hf_to_gguf.py \
     /mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash \
     --outfile /mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash-Q4_K_M.gguf \
     --outtype q4_k_m
   ```

4. Build and validate model loads:
   ```bash
   cd /mnt/raid0/llm/llama.cpp-dflash
   cmake -B build -DCMAKE_BUILD_TYPE=Release
   cmake --build build --target llama-server llama-cli -j$(nproc)

   # Load test (should print model metadata without errors)
   ./build/bin/llama-cli \
     -m /mnt/raid0/llm/cache/dflash/Qwen3-8B-DFlash-b16-f16.gguf \
     -p "test" -n 1
   ```

### Success Criteria
- [ ] Both models convert without errors
- [ ] GGUF metadata includes `dflash.block_size=16`, `dflash.target_layer_ids`, `dflash.mask_token_id`
- [ ] Both models load in llama.cpp without architecture errors
- [ ] `llama-cli` can run a single forward pass (even if output is garbage — just testing load/graph build)

### Files to Modify

| File | Change |
|------|--------|
| `convert_hf_to_gguf.py` | New model class for DFlash architecture |
| `gguf-py/gguf/constants.py` | New tensor types for DFlash |
| `src/llama-arch.cpp` | Register DFlash architecture and tensors |
| `src/llama-model.cpp` | Load DFlash model (hparams + tensors) |

### Precedent

MTP conversion (Steps 1-4 in completed `mtp-speculative-decoding.md`) solved similar problems:
- Shared embeddings/LM head
- Remapping tensor names from HF to GGUF
- Adding new architecture tensors to constants.py and llama-arch.cpp
- Handling non-standard layer counts

## Phase 2 — Hidden State Extraction API

**Status**: Not started

### Concept

The DFlash drafter needs hidden states from specific layers of the target model as conditioning input. This requires a general-purpose API to extract intermediate hidden states during inference.

### Tasks

1. Implement `llama_get_hidden_state(ctx, layer_idx)` public API
2. Generalize MTP Step 6's hidden state caching to N configurable layer taps
3. Add GGUF metadata for which layers to tap (read from drafter's config)
4. Cache hidden states after target model forward pass for drafter consumption

### Files to Modify

| File | Change |
|------|--------|
| `include/llama.h` | Public API: `llama_get_hidden_state()` |
| `src/llama-context.h/.cpp` | Hidden state cache buffers for N layers |
| `src/llama-graph.h/.cpp` | Hidden state extraction nodes in compute graph |
| `src/models/*.cpp` | Export hidden states at configured layer indices |

### Precedent

MTP Step 6 already implemented single-layer hidden state caching (`mtp_hidden_cache` in `llama-context.h`). This phase generalizes to N layers.

## Phase 3 — DFlash Forward Pass

**Status**: Not started — blocked by Phase 2

### Concept

Implement the DFlash drafter's forward pass: a small transformer that takes noisy token embeddings + conditioning hidden states and produces denoised token logits through iterative refinement.

### Tasks

1. New `src/models/dflash.cpp` — 5-8 layer transformer with:
   - KV injection from target hidden states at `target_layer_ids` (conditioning)
   - Iterative denoising loop (T steps)
   - Causal attention within draft block
   - Timestep embedding conditioning
2. Start with causal-only attention (skip block-sparse for simplicity)
3. Test acceptance rate vs paper's τ=6.49
4. Benchmark drafter latency on CPU

### Key Design Decisions

- **No KV cache for drafter**: Each denoising iteration processes the full block. Block size is small (16 tokens), so this is cheap.
- **Conditioning injection**: Target hidden states projected into drafter's key/value space (cross-attention or additive injection — determine from safetensors tensor inspection). Production drafter has hidden_size=2048 vs target's 3584 → conditioning projection layer required.
- **Noise schedule**: Read from model config. Typically cosine or linear schedule.
- **Mask token**: ID 151669 — used to initialize noisy blocks before denoising.

### Success Criteria
- [ ] Acceptance rate > paper's τ=6.49 tokens/round (on dev model first, then production)
- [ ] Drafter latency < 50ms per denoising iteration on EPYC 9655 (16 tokens × 5-8 layers)
- [ ] Total draft cycle (all denoising iterations) < 200ms

## Phase 4 — Linear Speculation Integration

**Status**: Not started — blocked by Phase 3

### Tasks

1. Wire DFlash drafter into `common_speculative` framework
2. Draft cycle: target decode → extract hidden states → DFlash denoise → sample draft tokens → verify
3. Benchmark on Qwen3-Coder-30B-A3B (frontdoor) vs current 0.75B AR drafter

### Benchmark Commands

```bash
cd /mnt/raid0/llm/llama.cpp-dflash

# Baseline: current AR drafter
./build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  -md /mnt/raid0/llm/models/Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf \
  --draft-max 16 -t 96 --port 8199

# DFlash drafter
./build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  --dflash-draft /mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash-Q4_K_M.gguf \
  --dflash-steps 8 -t 96 --port 8199
```

Also use the existing benchmark script with a new pair:
```bash
# Add as pair 15 in bench_tree_speculation_server.sh
bash /mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_tree_speculation_server.sh 15
```

### Success Criteria
- [ ] Throughput > current 47.11 t/s frontdoor baseline (from model registry)
- [ ] Throughput > current AR drafter throughput on same prompt set
- [ ] DFlash draft cycle time < AR draft cycle time for 16 tokens

### Expected Outcome

DFlash should outperform the 0.75B AR drafter because:
- AR drafter generates tokens sequentially (each depends on previous)
- DFlash generates all 16 tokens in parallel (fixed denoising steps)
- Even if acceptance rate is similar, draft throughput is higher

## Phase 5 — Tree Speculation Composition

**Status**: Not started — blocked by Phase 4

### Concept

DFlash naturally produces multiple candidate tokens per position (from the diffusion process). Use DFlash top-k logits at each position as tree branching candidates, then verify with DySpec tree infrastructure.

### Tasks

1. DFlash top-k logits → DySpec tree → tree verification
2. Reuse existing tree infrastructure from `tree-speculation-numa-drafting.md`
3. Benchmark tree mode vs linear mode on frontdoor model

### Benchmark Commands

```bash
cd /mnt/raid0/llm/llama.cpp-dflash

# Linear DFlash (baseline for this phase)
./build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  --dflash-draft /mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash-Q4_K_M.gguf \
  --dflash-steps 8 -t 96 --port 8199

# Tree DFlash (with --kv-unified for multi-path verification)
./build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  --dflash-draft /mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash-Q4_K_M.gguf \
  --dflash-steps 8 --draft-p-split 0.1 --kv-unified -t 96 --port 8199
```

### Success Criteria
- [ ] Tree mode throughput > linear mode DFlash throughput
- [ ] Tree DFlash throughput > tree AR drafter throughput (comparing tree builders)

### Why This Is Promising

Tree speculation's bottleneck was sequential AR draft generation (each draft token depends on previous). DFlash eliminates this — all draft positions are generated in parallel, and the diffusion process naturally provides uncertainty estimates (multiple candidates per position from different denoising trajectories).

Cross-reference: [`tree-speculation-numa-drafting.md`](tree-speculation-numa-drafting.md) Phase 4+ for tree infrastructure.

## Phase 6 — NUMA-Parallel Verification (Hybrid Reopener)

**Status**: Not started (deferred until Phase 4 results)

### Concept

Benchmark concurrent single-token decodes on Qwen3.5-35B-A3B across NUMA nodes. If aggregate throughput from parallel independent decodes exceeds serial throughput, this reopens speculation on hybrid models — each NUMA node verifies one draft token independently.

### Tasks

1. Benchmark 1 vs 2 vs 4 concurrent single-token decodes across NUMA nodes
2. Measure aggregate throughput vs serial throughput
3. If viable: wire DFlash draft distribution across NUMA verify workers

Cross-reference: [`tree-speculation-numa-drafting.md`](tree-speculation-numa-drafting.md) Phase 7, [`ssm-hybrid-acceleration.md`](ssm-hybrid-acceleration.md) Phase 4.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| DFlash drafter architecture incompatible with GGUF | MEDIUM | Phase 0 inspection before any code. Fallback: custom binary format. |
| Hidden state dimensions mismatch between target and drafter | HIGH | Verify in Phase 0 config inspection. Must match exactly. |
| CPU denoising too slow (T iterations × block) | MEDIUM | Start with T=4-8, measure. Block is small (16 tokens). |
| Only 1 production drafter available (frontdoor) | LOW | Validates approach. Other drafters need custom training when recipe publishes. |
| Hybrid models still blocked by recurrent verification | EXPECTED | Phase 6 NUMA-parallel is speculative reopener, not guaranteed. |
| Diffusion quality degrades on CPU quantization | MEDIUM | Test Q8_0 first (near-lossless), then Q4_K_M. |

## References

- [DFlash: Block Diffusion for Flash Speculative Decoding](https://arxiv.org/abs/2602.06036) — arxiv:2602.06036
- [DART: Diffusion-Inspired Speculative Decoding](https://arxiv.org/abs/2601.19278) — related diffusion approach
- `z-lab/Qwen3-Coder-30B-A3B-DFlash` — HuggingFace model
- `z-lab/Qwen3-8B-DFlash-b16` — HuggingFace model (dev/iteration)
- MTP-1 implementation: `handoffs/completed/mtp-speculative-decoding.md` — precedent for GGUF conversion, hidden state API
- Tree infrastructure: `handoffs/active/tree-speculation-numa-drafting.md` — DySpec tree for Phase 5 composition
