# llama.cpp Fork Rebase — Chat Template + Reasoning Fixes

**Status**: superseded — merged into [llama-cpp-kernel-push-rebase.md](llama-cpp-kernel-push-rebase.md). v4 branch has all cherry-picks + full rebase + TIDE.
**Created**: 2026-04-20
**Updated**: 2026-04-20
**Priority**: HIGH (blocking quality benchmarks for Qwen3.6, M2.7, Gemma4)
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`qwen36-production-upgrade.md`](qwen36-production-upgrade.md), [`bulk-inference-campaign.md`](bulk-inference-campaign.md)

## Objective

Rebase our `production-consolidated-v3` fork (41 custom patches on `b8721`) onto current upstream to fix broken chat template handling for Qwen3.6, M2.7, and Gemma4 models. Stock upstream produces 73.8%+ quality on Qwen3.6; our fork produces 0%.

## Current Fork State

| Property | Value |
|----------|-------|
| Branch | `production-consolidated-v3` |
| Base | `b8721` (tag), merge base `0ec191e1d` |
| Custom patches | 35 (31 original + 4 cherry-picked) |
| Commits behind upstream | 121 (was 125; 4 cherry-picked) |
| Backup branch | `production-v3-backup` at `cf88fe409` |
| Current HEAD | `cd5f4fcd0` |
| Repo | `/mnt/raid0/llm/llama.cpp` |

## Evidence: Stock Upstream vs Our Fork

### Qwen3.6-35B-A3B Q8_0

| Config | Our Fork | Stock Upstream |
|--------|----------|----------------|
| Simple prompt ("What is 2+2?") | `</think>` loop, 0 content | "4" — perfect |
| Complex math proof | `</think>` loop, 0 content | 2769 chars, correct real analysis |
| Fibonacci code | `</think>` loop, 0 content | 614 chars, correct Python |
| **Quality benchmark (70 questions)** | **0%** (all degenerate) | **73.8%** (95.7% when not looping) |

### M2.7 Q8_0 (230B-A10B)

| Config | Our Fork | Stock Upstream |
|--------|----------|----------------|
| Simple prompt | "4" (works) | "4" + reasoning_content (better) |
| Instruction precision | Echo prompt → training data leakage | Clean answer with reasoning |
| **Quality benchmark** | **55.7%** (best run) | **41.1%** (4x tokens caused more leakage) |

M2.7 actually scored worse on upstream with 4x tokens — the extra budget gives it room to generate more training data leakage. The model needs `max_tokens` tuning independent of the fork issue.

### Gemma4 (SG4-31b, SG4-26b-MM)

Gemma4 models work on our fork with `use_chat_api + repeat_penalty + --jinja`, scoring 60-66%. Upstream has 6 additional Gemma4 fixes that could improve this further.

## Upstream Commits We're Missing (Critical)

These are the commits between our fork base (`b8721`) and upstream that directly affect chat template / reasoning handling:

| Commit | Description | Impact |
|--------|-------------|--------|
| `56666fa60` | Skip reasoning budget sampler when no budget requested | Prevents spurious reasoning activation |
| `e21cdc11a` | Gemma4: handle parsing edge cases | Fixes Gemma4 chat output parsing |
| `3fc65063d` | Better align to updated official Gemma4 template | Template correctness |
| `d7ff074c8` | Enable reasoning budget sampler for Gemma4 | Controls thinking token budget |
| `ddf03c6d9` | Fix ambiguous grammar rule in Gemma4 | Prevents parsing ambiguity |
| `fcc750875` | Gemma4 model type detection | Correct model identification |
| `1c0d9081f` | Dedicated DeepSeek v3.2 parser + "official" template | Chat infrastructure improvements |

### Commits We Already Have

| Commit | Description |
|--------|-------------|
| `0ec191e1d` | Gemma4 tokenizer tests, fix edge case |
| `243532e55` | Jinja: support `ensure_ascii=true` (critical for M2.7 template) |
| `56666fa60` → `05a0a156c` | Skip reasoning budget sampler when no budget requested (cherry-picked 2026-04-20) |
| `ddf03c6d9` → `60fd2340f` | Fix ambiguous grammar rule in Gemma4 (cherry-picked 2026-04-20) |
| `d7ff074c8` → `942c68918` | Enable reasoning budget sampler for Gemma4 (cherry-picked 2026-04-20) |
| `3fc65063d` → `cd5f4fcd0` | Better align to updated official Gemma4 template (cherry-picked 2026-04-20) |

## Our 41 Custom Patches (Risk Assessment)

### High-Value / Must-Preserve

| Patch | Description | Conflict Risk |
|-------|-------------|---------------|
| `cf88fe409` | IMROPE fix for Qwen3.5 hybrids (seq_add/seq_div + K-shift) | LOW — touches model-specific code |
| `c1aa38e5d` | Initialize freeze_recurrent for hybrid SSM+MoE | LOW — one-line fix |
| `de0146fc1` | Re-port `--lookup` (prompt lookup) to production | MEDIUM — touches server code |
| `51b9732c9` | `--moe-n-expert` flag for MoE expert count override | LOW — additive feature |
| `a3f741f7d` | OpenMP tensor repacking parallelization | LOW — ggml-cpu only |

### Experimental / Can Drop if Conflicts

| Patch | Description | Notes |
|-------|-------------|-------|
| `4babc8fe3` | Expected Attention KV compression | Experimental, not in production |
| `8bd57177f` | Differential Transformer V2 | Experimental architecture |
| `81c9ad1ec` | Attention Matching KV compaction (L1-L4) | Research prototype |
| `2d72b9626` | Tree speculation with DySpec | Not production-validated |
| `f70dc4f76` | HSD + freeze-recurrent speculation | SSM-specific, experimental |
| `02914928b` | SSM state checkpointing | Depends on HSD |
| `0286eaeaa` | Layer skip / early exit | Experimental |

### Infrastructure / Should Preserve

| Patch | Description | Conflict Risk |
|-------|-------------|---------------|
| `d8fd6f56e` - `5257f6646` | CPU paged attention (7 patches) | MEDIUM — touches KV cache |
| `142f5c457` | Slot erase without --slot-save-path | LOW |
| `3b265850d` | Error to HTTP handler on slot force-erase | LOW |
| `7057025df` | MTP benchmark tools | LOW — additive |

## Cherry-Pick Results (2026-04-20)

### Applied Commits (4 total, zero conflicts)

| Order | Commit | Description | Result |
|-------|--------|-------------|--------|
| 1 | `56666fa60` → `05a0a156c` | Skip reasoning budget sampler when no budget requested | CLEAN |
| 2 | `ddf03c6d9` → `60fd2340f` | Fix ambiguous grammar rule in Gemma4 | CLEAN |
| 3 | `d7ff074c8` → `942c68918` | Enable reasoning budget sampler for Gemma4 | CLEAN |
| 4 | `3fc65063d` → `cd5f4fcd0` | Better align to updated official Gemma4 template | CLEAN |

### Validation

- **Qwen3.6 think-loop fix: CONFIRMED.** CLI test with simple math prompt produced coherent thinking + correct answer ("2 plus 2 equals 4"). No `</think>` loops. The reasoning budget sampler skip (`56666fa60`) was the fix — the sampler was unconditionally activating and trapping the model.
- **Quality benchmark retest: 16/16 PASS.** All 16 questions that previously scored 0% (think-loops or empty responses) now produce substantive answers via `/v1/chat/completions` API on the patched server. Results saved to `benchmarks/results/reviews/qwen36_q8_0_retest_fork_fix.json`.
- **Build**: Clean incremental build, both `llama-server` and `llama-cli` binaries verified.
- **Backup branch**: `production-v3-backup` at `cf88fe409` (pre-cherry-pick HEAD).
- **Reasoning mode finding**: `--reasoning auto` with this model causes pathological verbosity (8K+ tokens of reasoning without closing `</think>`). Use `enable_thinking: false` in chat_template_kwargs for quality benchmarks (matches upstream conditions). The thinking mode interaction needs separate investigation.

### Current HEAD

`cd5f4fcd0` — 35 custom commits ahead of merge base, 121 commits behind upstream (was 125; 4 cherry-picked).

### Not Cherry-Picked

| Commit | Description | Reason |
|--------|-------------|--------|
| `fcc750875` | Gemma4 model type detection | Sits atop 6 major `src/llama-model.cpp` refactors (tensor parallelism, QKV helpers, llm_build consolidation). Cannot cherry-pick without manual adaptation. |
| `e21cdc11a` | Gemma4 parsing edge cases | Deep in `common/chat.cpp` dependency chain (6th commit). Feasible but adds risk for marginal gain. |
| `1c0d9081f` | DeepSeek v3.2 parser | 5th in `common/chat.cpp` chain, requires `b136b62cf` (structured output $refs fix) as intermediate dependency. Not needed for current models. |

### Investigation Findings — Conflict Risk Reassessment

The initial handoff overstated conflict risk. Actual analysis:
- `src/llama-kv-cache*`: **ZERO conflict risk** — 10 of our patches, 0 upstream changes
- `common/chat*`: **ZERO conflict risk** — 0 of our patches, 10 upstream changes (all cherry-pickable)
- `tools/server/server.cpp`: **ZERO conflict risk** — 0 of our patches (handoff was wrong)
- `common/common.h`: **HIGH risk** — 6 of ours vs 4 upstream, including `libcommon→libllama-common` rename
- `common/sampling.cpp`: **LOW-MED risk** — 1 of ours (HSD) vs 1 upstream (budget sampler, now cherry-picked)

### Remaining Work

Full rebase (Option A) is still recommended for long-term health but is no longer blocking quality benchmarks. Schedule as a separate work item. Key considerations:
- Drop 7 experimental patches during rebase to reduce conflict surface (31→24 patches)
- The `libcommon→libllama-common` rename in upstream will cascade through includes — main conflict source
- `common/common.h` (6 ours vs 3 remaining upstream) is the real battleground

## Rebase Strategy

### Option A: Full Rebase (Recommended)
1. Create backup branch: `git branch production-v3-backup`
2. Rebase onto upstream: `git rebase origin/master`
3. Resolve conflicts patch-by-patch (41 patches)
4. Drop experimental patches if conflicts are complex
5. Build and validate: all production models still work
6. Run quality benchmarks on Qwen3.6 + M2.7 + Gemma4

**Risk**: Merge conflicts on KV cache and server code
**Reward**: Full upstream compatibility, all 120 commits of improvements

### Option B: Cherry-Pick Critical Fixes
1. Cherry-pick the 7 missing critical commits (listed above)
2. Build and test
3. Lower risk but may miss dependency commits

**Risk**: Cherry-picked commits may depend on intermediate changes
**Reward**: Minimal disruption, targeted fix

### Option C: Parallel Binary (Current Workaround)
Keep using `LLAMA_BIN_DIR` to point benchmarks at the experimental binary for Qwen3.6/M2.7, while production fork handles Gemma4 + existing models.

**Risk**: Two binaries to maintain, diverging behavior
**Reward**: Zero risk to production, immediate availability

## Validation Plan

After cherry-picks (partial) / full rebase:
1. [ ] Qwen3.5-35B-A3B (production frontdoor) — still works with IMROPE (cherry-picks don't touch IMROPE code, should be fine)
2. [x] Qwen3.6-35B-A3B — chat template works, no think-loops (CONFIRMED via CLI 2026-04-20)
3. [x] Qwen3.6-35B-A3B — 16/16 failing questions now PASS (retest 2026-04-20, enable_thinking=false)
4. [ ] M2.7 — Jinja template renders correctly, no training data leakage
5. [ ] Gemma4 (SG4-31b, SG4-26b-MM) — test with new Gemma4 template + grammar fixes
6. [ ] `--lookup` flag — still available (cherry-picks don't touch this)
7. [ ] `--moe-n-expert` — still available (cherry-picks don't touch this)
8. [ ] CPU paged attention — still functional (cherry-picks don't touch KV cache)
9. [ ] Production stack startup — all models load and serve

## Key Files to Watch During Rebase

| File | Our Changes | Upstream Changes | Conflict Likelihood |
|------|-------------|------------------|-------------------|
| `tools/server/server.cpp` | Slot erase, paged attn | 118 lines diff | HIGH |
| `common/chat.cpp` | None directly | 334 lines diff | LOW |
| `src/llama-kv-cache.cpp` | Paged attention, SWA fixes | Likely changed | HIGH |
| `common/sampling.cpp` | None | Reasoning budget sampler | LOW |
| `common/common.h` | Paged attn flags | 125 lines diff | MEDIUM |

## M2.7 Separate Issue: Training Data Leakage

The M2.7 training data leakage problem is NOT a fork issue — it happens on upstream too. This is an inherent model behavior where M2.7 regurgitates memorized training data (Rust test suites, TypeScript frameworks, exam banks) instead of answering prompts. Contributing factors:
- Low temperature (0.2) makes deterministic token selection favor memorized high-probability sequences
- High max_tokens gives room for extended leakage (4x made it worse: 55.7% → 41.1%)
- The model's 200K vocab and 256-expert MoE architecture may make it more prone to memorization

Potential mitigations (not yet tested):
- Temperature 1.0 (recommended by MiniMax) — increases sampling diversity
- min_p sampling — cuts low-probability memorized sequences
- Shorter max_tokens with retry on truncation
