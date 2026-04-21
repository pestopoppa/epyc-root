# llama.cpp Kernel Push + Full Rebase — Holistic Plan

**Status**: in-progress (v4 branch: 23 commits on upstream, builds clean, Qwen3.6 validated; tree spec + TIDE hooks pending)
**Created**: 2026-04-20
**Priority**: HIGH
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`llama-cpp-fork-rebase.md`](llama-cpp-fork-rebase.md), [`tide-calibration-router-early-exit.md`](../../research/deep-dives/tide-calibration-router-early-exit.md)
**Repo**: `/mnt/raid0/llm/llama.cpp` (branch `production-consolidated-v3`, HEAD `cd5f4fcd0`)

## Objective

Execute the full upstream rebase, fix the `--reasoning auto` infinite-thinking issue, and implement TIDE Phase 1 — all in a single coordinated session. The three are coupled:

1. **Rebase** drops the old static layer-skip patch (which TIDE supersedes)
2. **TIDE Phase 1** needs the rebased `n_layer_exit` infrastructure as its foundation
3. **Reasoning fix** requires understanding server-side chat template handling (touched during rebase)

## Why Holistic (Not Sequential)

| If done separately... | Risk |
|----------------------|------|
| Rebase then TIDE later | TIDE implementation may conflict with upstream changes that the rebase introduced |
| TIDE then rebase later | TIDE built on old base; rebase would require re-doing TIDE work |
| Reasoning fix standalone | Root cause likely in `common/chat.cpp` chain (same files rebase touches) |

Doing all three together means: one set of conflicts to resolve, one validation pass, one binary to deploy.

---

## Execution Log (2026-04-20)

**v4 branch created**: `production-consolidated-v4` from `origin/master` (81df3f7cf)

### Applied (22 patches + 1 build fix = 23 commits):
All KV cache, paged attention, server slot management, OpenMP, --moe-n-expert, AM compaction, EA compression, DiffTransformer V2, IMROPE, MTP tools.

### Dropped during execution:
- `de0146fc1` (--lookup): **SUPERSEDED** by upstream `--spec-type ngram-simple` (commits 72d3b1898, dabaa2e77). Registry already uses ngram-simple. Flag retired.
- `f788d1b0a` (.gitignore/cleanup): Mixed commit with unrelated server-context.cpp changes. Not worth the conflict.
- `0f61bc70f` (docs): Stale v2 branch references.

### Deferred (need re-port against upstream's refactored speculative decoding):
- `2d72b9626` (Tree spec DySpec): Upstream refactored ALL speculative logic into `slot.update_batch()` with renamed fields (spec_draft, spec_i_batch, spec_ckpt). DySpec multi-path verification needs adaptation.
- `0ddff9ed1` (kv_unified auto-enable): Depends on tree spec.

### Build fix applied:
- DiffTransformer V2: Added `wo_s` nullptr param to `build_attn()` call (upstream API change).

### Validated:
- Build: clean ✓
- Qwen3.6 smoke test: reasoning-budget 4096, produces thinking + answer at 25.5 t/s ✓

---

## Phase 1: Full Rebase (Estimated: 2-4 hours)

### Branch Strategy

```bash
git branch production-v3-backup          # Already done (cf88fe409)
git branch production-v4-pre-rebase      # Snapshot current HEAD (cd5f4fcd0, with cherry-picks)
git checkout -b production-consolidated-v4  # New branch for the rebase
git rebase origin/master
```

### Patches to KEEP (24 patches → the production core)

| # | Commit | Description | Conflict Risk | Motivation |
|---|--------|-------------|---------------|------------|
| 1 | `cf88fe409` | IMROPE fix (Qwen3.5 hybrids seq_add/seq_div + K-shift) | NONE (KV cache, 0 upstream changes) | **Production-critical**: Without this, Qwen3.5-122B crashes during KV chunk reuse |
| 2 | `c1aa38e5d` | Initialize freeze_recurrent for hybrid SSM+MoE | NONE | **Only needed if SSM patches kept** — see note below |
| 3 | `de0146fc1` | Re-port `--lookup` (prompt lookup speculation) | MEDIUM (`common/arg.cpp`, `server-task.cpp`) | **+10% throughput** on ngram-heavy workloads. Our custom spec feature. |
| 4 | `51b9732c9` | `--moe-n-expert` flag (Hard Mask runtime override) | MEDIUM (`common/arg.cpp`, `common/common.h`, `llama-graph.cpp`) | **+21-48% speedup** at 50% experts. REAP deployment depends on this. |
| 5 | `a3f741f7d` | OpenMP tensor repacking parallelization | LOW (`ggml-cpu/repack.cpp`) | **1.5-2.5x model loading** on many-core. Isolated file. |
| 6 | `d8fd6f56e` | CPU paged attention — flash attention kernel | MEDIUM (`ggml.h`, `ggml.c` for new op `FLASH_ATTN_EXT_PAGED`) | **Foundation for multi-slot** — large patch but upstream has 0 changes to KV cache |
| 7 | `5257f6646` | Dynamic block allocation for paged attention | NONE | Part of paged attention stack |
| 8 | `ad3223564` | Block pool statistics for debugging | NONE | Part of paged attention stack |
| 9 | `58ac6491d` | KV cache memory reduction for paged attention | NONE | Part of paged attention stack |
| 10 | `de03bcc44` | CLI flags for paged attention | MEDIUM (`common/arg.cpp`, `common/common.h`) | Part of paged attention stack — conflicts in `common/common.h` |
| 11 | `b4c5853b8` | Trim verbose comments in llama-kv-block.h | NONE | Cleanup |
| 12 | `9f8139604` | Unit tests for block pool | NONE | Tests |
| 13 | `4eb4776f8` | Bump GGML_OP_COUNT for FLASH_ATTN_EXT_PAGED | LOW (`ggml.h`) | May conflict with upstream op additions |
| 14 | `8bc9f585d` | Fix block table construction (mctx_cur) | NONE | Bugfix |
| 15 | `72eea0c73` | SWA cell reuse mathematical correctness fix | NONE | Correctness fix |
| 16 | `62481a417` | SWA slot reuse forward-looking masking | NONE | Optimization |
| 17 | `142f5c457` | Slot erase without --slot-save-path | LOW | Server UX improvement |
| 18 | `3b265850d` | Error to HTTP handler on force-erase | LOW | Error handling |
| 19 | `7057025df` | MTP benchmark tools + Claude skills | NONE (additive files) | Tooling |
| 20 | `4babc8fe3` | Expected Attention KV compression | NONE (KV cache) | **Production feature** — EA scoring + server endpoint |
| 21 | `81c9ad1ec` | Attention Matching KV compaction L1-L4 | NONE (KV cache) | **Production feature** — 5x lossless compression |
| 22 | `80c72c0c6` | AM compaction state format versioning | NONE | Backward compat |
| 23 | `7784b3d9c` | L4b K-norm importance scoring | NONE | AM compaction enhancement |
| 24 | `8bd57177f` | Differential Transformer V2 | LOW (new model file) | **Keep** — awaiting pretrained models, architecture already merged |

### Patches to KEEP (additional — tree speculation is PRODUCTION)

| # | Commit | Description | Conflict Risk | Motivation |
|---|--------|-------------|---------------|------------|
| 25 | `2d72b9626` | Tree speculation with DySpec + multi-path verification | MEDIUM (`common/common.h`, `common/arg.cpp`) | **PRODUCTION** — deployed for `coder_escalation` with p_split=0.05 (+2.7% Q4KM, +17% f16) |
| 26 | `0ddff9ed1` | Auto-enable kv_unified for tree spec with draft models | LOW | Required dependency for tree speculation |

### Patches to DROP (5 patches — SSM/hybrid-only, superseded by TIDE)

| # | Commit | Description | Why Drop |
|---|--------|-------------|----------|
| 1 | `0286eaeaa` | Layer skip / early exit (static) | **Superseded by TIDE** — static layer-skip produces near-zero acceptance (HSD experiments). TIDE's learned router replaces this. |
| 2 | `10f31f752` | Layer skip for qwen3vl-moe + qwen3next | Same — TIDE Phase 2 will re-add this properly |
| 3 | `f70dc4f76` | HSD + freeze-recurrent speculation | **Not viable** — SSM/hybrid spec all net negative (Delta Net recurrence prevents path forking) |
| 4 | `02914928b` | SSM state checkpointing | Only needed for HSD — drop with it |
| 5 | `c1aa38e5d` | Initialize freeze_recurrent | Only needed for SSM checkpointing — drop with it |

**Note**: Dropping commits 1-2 removes the `n_layer_exit` infrastructure from the model files. TIDE Phase 1 will re-add it in a cleaner form (with router hooks). Tree speculation (commit 25) is kept — it's actively deployed for `coder_escalation`.

### Patches Already Upstream (4 cherry-picks — will auto-resolve during rebase)

| Commit | Upstream Equivalent |
|--------|-------------------|
| `05a0a156c` | `56666fa60` (reasoning budget sampler skip) |
| `60fd2340f` | `ddf03c6d9` (Gemma4 grammar fix) |
| `942c68918` | `d7ff074c8` (reasoning budget for Gemma4) |
| `cd5f4fcd0` | `3fc65063d` (Gemma4 template alignment) |

During rebase, these will conflict trivially (same change both sides) — resolve by accepting upstream's version (`git checkout --theirs <file>`).

### Conflict Resolution Strategy

| File | Our Patches | Upstream | Strategy |
|------|-------------|----------|----------|
| `common/common.h` | 5 (--lookup, --moe-n-expert, paged attn flags, tree spec flags, kv_unified auto) | 4 (libcommon rename, checkpoint, cache-idle-slots) | All 5 our flag additions KEPT. Add our flags AFTER upstream's additions. The `libcommon→libllama-common` rename changes the header guard and includes — apply rename to our additions. |
| `common/arg.cpp` | 3 (--lookup, --moe-n-expert, paged attn flags) | 2 (--clear-idle→--cache-idle-slots, checkpoint flags) | These are additive (each adds `add_argument` calls). Low conflict — just rebase each onto the new argument list. |
| `ggml.h` / `ggml.c` | 1 (FLASH_ATTN_EXT_PAGED op) | Unknown op additions | Check upstream's current `GGML_OP_COUNT`. Add our op after their last one. |
| `common/sampling.cpp` | 0 (HSD patch dropped) | 1 (budget sampler skip — already cherry-picked) | **ZERO conflict** — dropping HSD removes our only change here |
| `src/llama-context.cpp` | 1 (moe-n-expert) | Upstream refactoring (tensor parallelism) | Manual merge — apply our cparams change to new code structure |
| `src/llama-graph.cpp` | 1 (moe-n-expert hard mask) | Upstream QKV helper refactor | Manual merge — re-apply ggml_view masking to new helper functions |
| `include/llama.h` | 1 (paged attn API) | Upstream API additions | Additive — add our functions after their new ones |

### The libcommon→libllama-common Cascade

Upstream commit `6990e2f1f` renames the library. This changes:
- `#include "common.h"` → `#include "llama-common.h"` (or keeps it as `common.h` with different linkage)
- CMakeLists.txt target name
- Potentially header guards

**Mitigation**: After the rebase reaches this commit, run `git diff --name-only` to see all affected files. Apply the rename to our custom files mechanically (`sed -i`).

---

## Phase 2: Reasoning Mode Fix (Estimated: 1-2 hours)

### Problem Statement

With `--reasoning auto`, Qwen3.6 generates infinite reasoning tokens and never emits `</think>`. The model fills any token budget (tested up to 8192) without closing the thinking block. Without `--reasoning auto` (using `enable_thinking: false`), the model produces perfect answers.

### Root Cause (CONFIRMED 2026-04-20)

1. **Cherry-pick `56666fa60`** removes the reasoning budget sampler when `reasoning_budget_tokens = -1` (unlimited) and no `grammar_lazy`.
2. **Without the sampler**: There is no mechanism to force-inject `</think>`. The model must produce it naturally.
3. **Qwen3.6 behavior**: The Qwen3.5/3.6 template always prepends `<think>\n` to generation. The model enters thinking mode immediately. For simple questions it closes naturally; for complex questions it may never close.
4. **The PEG parser** correctly separates reasoning_content from content based on `<think>...</think>` boundaries — but it needs the model to actually emit `</think>`.

**Key insight**: Even with the OLD code (sampler at INT_MAX budget), the sampler would NOT force `</think>` until 2 billion tokens. The old code had the same theoretical bug but it was masked because the server would timeout first. The real fix is an explicit budget.

### Fix (VALIDATED 2026-04-20)

```bash
--reasoning-budget 4096
```

This creates the budget sampler which, after 4096 thinking tokens, force-injects `</think>` via logit manipulation. Tested:
- Simple question: Model closes thinking naturally at 208 tokens (budget not needed)
- Complex math proof: Model closes at ~1200 thinking tokens, produces 1954-char structured answer
- Both produce proper `reasoning_content` + `content` separation with `finish_reason: stop`

Can also be set per-request: `"thinking_budget_tokens": 4096` in chat completions payload.

### Implementation (trivial)

Add `--reasoning-budget 4096` to server startup command. No code changes needed. Update `model_registry.yaml`:
```yaml
reasoning: auto
reasoning_budget: 4096  # Force </think> after 4K tokens if model doesn't close naturally
```

### Success Criteria — ALL MET

- [x] `--reasoning auto` produces bounded reasoning (model closes `</think>` naturally at 208-1200 tokens)
- [x] `reasoning_content` field populated with thinking (649-4175 chars)
- [x] `content` field populated with answer (clean structured output)
- [ ] Quality benchmark with thinking ON scores ≥ 73.8% (needs full 70-question run with `--reasoning-budget 4096`)

### Remaining for Phase 2 in dedicated session

The fix is validated but needs integration:
1. Update `model_registry.yaml` to add `reasoning_budget: 4096` field
2. Update executor.py to pass `--reasoning-budget` flag when starting servers
3. Run full 70-question benchmark with thinking ON to get quality score
4. Compare thinking-ON vs thinking-OFF quality (expected: higher with thinking)

---

## Phase 3: TIDE Phase 1 Implementation (Estimated: 2-3 hours)

### What We're Building

A calibration-based learned router that enables per-token early exit. Phase 1 targets **per-batch** exit (simpler than per-token) which is sufficient for our batch_size=1 decode workload.

### Components

| Component | File(s) | Complexity |
|-----------|---------|-----------|
| Calibration script | `scripts/calibrate_tide_router.py` (new) | LOW — 100 lines Python |
| Router weights sidecar | `models/*.tide.bin` (new format) | LOW — simple binary |
| Router loader | `src/llama-context.cpp` (extension) | LOW — load sidecar on init |
| Router evaluation | `src/models/qwen3moe.cpp`, `qwen3.cpp` | MEDIUM — insert after checkpoint layers |
| CLI flag | `common/arg.cpp`, `common/common.h` | LOW — `--early-exit-threshold` |
| Server integration | Automatic via CLI flag | NONE |

### Implementation Details

**Calibration script** (`scripts/calibrate_tide_router.py`):
```
1. Load model via llama-cpp-python
2. Run 2000 WikiText-103 samples (first 512 tokens each)
3. At every 4th layer (checkpoints): record hidden state h[i]
4. Compute cos_sim(h[i], h[i+4]) for each token at each checkpoint
5. Label: converged if cos_sim > 0.98
6. Train router MLP: Linear(hidden_dim, 128) → ReLU → Linear(128, 1)
7. Save as .tide.bin (one router per checkpoint, ~4MB total)
```

**Forward pass modification** (per-token during decode):
```c
// After each checkpoint layer (every 4 layers):
if (tide_router && batch_size == 1) {
    float confidence = tide_evaluate_router(router[checkpoint_idx], cur_hidden);
    if (confidence > threshold) {
        // Skip remaining layers, jump to LM head
        n_layer_exit = current_layer;
        break;
    }
}
```

**Why Phase 1 is per-batch (not per-token)**:
- Our decode is batch_size=1 — per-batch IS per-token
- Prompt processing (batch_size=N) doesn't exit early (all tokens need full attention)
- No batch compaction needed → dramatically simpler implementation

### Expected Gains

- Qwen3.6-35B-A3B: 32 layers, ~8ms/layer, 25.6 t/s baseline
- If average exit at layer 24 (skipping 25%): ~34 t/s (**+33% decode**)
- If average exit at layer 20 (skipping 37%): ~40 t/s (**+56% decode**)
- Conservative estimate (80% of tokens exit at 75%, rest use full): **+15-20%**

### Validation

1. Run calibration on Qwen3.6-35B-A3B with WikiText-103
2. Measure per-layer convergence distribution (what % of tokens converge at each checkpoint?)
3. Run quality benchmark with threshold 0.85, 0.90, 0.95
4. Find Pareto point (quality ≥ 95% of baseline, maximum speed gain)

---

## Phase 4: Validation & Deployment

### Build & Smoke Tests
- [ ] `cmake --build . -j$(nproc)` — clean compile
- [ ] All production models load (`--moe-n-expert`, `--lookup`, paged attention)
- [ ] Qwen3.5-35B-A3B: IMROPE still works (KV chunk reuse)
- [ ] Qwen3.6-35B-A3B: No think-loops (with `enable_thinking=false` and with reasoning fix)
- [ ] Gemma4: Template fixes work (repeat_penalty + --jinja)
- [ ] `--early-exit-threshold 0.9`: Loads router, exits early, quality holds

### Quality Benchmarks
- [ ] Qwen3.6 full 70-question benchmark: target ≥73.8% (current upstream baseline)
- [ ] Qwen3.6 with TIDE enabled: target ≥70% (≤5% quality loss for speed)
- [ ] Gemma4 SG4-31b: target ≥66% (current baseline, verify no regression)
- [ ] Speed test: Qwen3.6 decode t/s with TIDE vs without

### Deployment
- [ ] Push to fork remote (`git push fork production-consolidated-v4`)
- [ ] Update `model_registry.yaml` with new binary path and TIDE config
- [ ] Restart production stack
- [ ] Monitor for 1 hour (no crashes, quality holds)

---

## Session Checklist (for the executing agent)

```
□ Pre-flight
  □ Verify backup branch exists (production-v3-backup)
  □ Create pre-rebase snapshot (production-v4-pre-rebase)
  □ Confirm upstream is fetched (git fetch origin)
  □ Confirm no running servers using the fork binary

□ Phase 1: Rebase
  □ Create new branch (production-consolidated-v4)
  □ Drop 7 experimental patches (interactive or cherry-pick remaining 24)
  □ Rebase onto origin/master
  □ Resolve conflicts (see strategy table above)
  □ Handle libcommon→libllama-common rename cascade
  □ Build clean
  □ Smoke test (load Qwen3.6, generate one response)

□ Phase 2: Reasoning Fix
  □ Trace --reasoning auto code path
  □ Identify why </think> is never generated
  □ Implement fix
  □ Validate: curl with thinking enabled produces content

□ Phase 3: TIDE Phase 1
  □ Write calibration script
  □ Run calibration on Qwen3.6 (record hidden states)
  □ Train routers, save .tide.bin
  □ Add router loader to llama-context.cpp
  □ Add evaluation hook to qwen3moe.cpp forward pass
  □ Add --early-exit-threshold CLI flag
  □ Benchmark: speed gain vs quality loss at various thresholds

□ Phase 4: Validate & Deploy
  □ Full quality benchmark suite
  □ Speed benchmark (before/after TIDE)
  □ Push to fork remote
  □ Update registry
  □ Deploy to production
```

---

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Rebase conflicts cascade | MEDIUM | The `libcommon` rename is the only multi-file cascade. Apply mechanically with sed. Keep backup branch. |
| TIDE quality degradation | LOW-MEDIUM | Conservative threshold (0.95) for initial deployment. Easy to disable via flag. |
| Reasoning fix incomplete | MEDIUM | Fallback: keep `enable_thinking=false` (which already scores 73.8%). Reasoning fix is additive. |
| Build breaks after rebase | LOW | Incremental: build after each conflict resolution step, not just at the end. |
| Production regression | LOW | Full benchmark before deployment. Backup binary available. |

## Estimated Total Time

| Phase | Time | Parallelizable? |
|-------|------|----------------|
| Rebase (24 patches onto 121 upstream) | 2-4 hours | No |
| Reasoning fix investigation + implementation | 1-2 hours | After Phase 1 |
| TIDE calibration script + training | 1 hour | After Phase 1 |
| TIDE forward pass implementation | 1-2 hours | After calibration |
| Validation & deployment | 1 hour | After all above |

**Total: ~6-10 hours (one dedicated session)**
