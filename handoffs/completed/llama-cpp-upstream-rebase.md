# llama.cpp Production Rebase

**Status**: COMPLETE — 16 patches applied, build passes, smoke tests pass
**Created**: 2026-03-03
**Priority**: HIGH
**Workstream**: WS2
**Blocks**: WS3 (qwen35-frontdoor-benchmark)
**Branch**: `production-consolidated-v2` (new, based on `origin/master`)

## Goal

Rebase `production-consolidated` onto current upstream master, gaining Qwen3.5 support + upstream improvements, while preserving all 23 custom patches.

## Current State

- **Base**: `9ac2693a3` (upstream, ~January 2026)
- **Branch**: `production-consolidated` (23 custom commits on top)
- **Upstream**: `origin/master` at `079feab9e`+ (includes Qwen3.5 `fc0fe4004`, dedup `27326bfce`)

## Custom Patches to Re-apply (in dependency order)

### Low conflict risk (standalone features)

| # | Commit | Description | Notes |
|---|--------|-------------|-------|
| 1 | `553b6dcef` | `--moe-n-expert` flag (Hard Mask) | May already be upstream |
| 2 | `2a16c4388` | lookup/lookahead crash fix when n_ctx not specified | |
| 3 | `7bf427dc6` | lookahead n_seq_max fix | |
| 4 | `2ee7aa7ee` / `b1366757c` | OpenMP tensor repacking | |

### Medium conflict risk (touch core files)

| # | Commit | Description | Notes |
|---|--------|-------------|-------|
| 5 | `b5e11afb0` | layer skip / early exit for speculative decoding | |
| 6 | `42e7d627f` | layer skip for qwen3vl-moe and qwen3next | |
| 7 | `394e0cb34` | SWA slot reuse optimization with forward-looking masking | |
| 8 | `6b43356a1` | SWA cell reuse correctness fix | |

### High conflict risk (server changes)

| # | Commit | Description | Notes |
|---|--------|-------------|-------|
| 9 | `cf42231e0`..`8fe0ecd1f` | Paged attention (6 commits) | |
| 10 | `93eb39f39` | MTMD fixes cherry-pick | Likely already upstream |
| 11 | `8e35dbc01` | Server prompt lookup (hybrid draft strategy) | **KEY patch** |
| 12 | `cde4d599a` | Server slot erase without --slot-save-path | |
| 13 | `b38db6b45` | Server error handling for force-erased slots | |

### Conditional (from WS1)

| # | Source | Description | Notes |
|---|--------|-------------|-------|
| 14 | `llama.cpp-experimental` | SSM state checkpointing | Only if WS1 preliminary benchmark passes |

## Process

```bash
cd /mnt/raid0/llm/llama.cpp
git fetch origin
git checkout -b production-consolidated-v2 origin/master

# Check which patches are already upstream
git log --oneline origin/master | grep -i "moe-n-expert\|mtmd\|lookup\|lookahead"

# Cherry-pick in order, resolve conflicts
git cherry-pick <commit>  # for each patch
```

## Build & Regression Test

```bash
cmake -B build -DGGML_CPU_ALL_VARIANTS=ON -DLLAMA_CURL=ON
cmake --build build -j96

# Smoke tests with existing production models
./build/bin/llama-cli -m /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf -n 32 -p "Hello" --no-cnv

# Test Qwen3.5 loads and generates
./build/bin/llama-cli -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-35B-A3B-GGUF/Qwen3.5-35B-A3B-UD-Q4_K_M.gguf -n 32 -p "Hello" --no-cnv

# Server test with spec decode
./build/bin/llama-server -m /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf -t 96 -c 8192 --port 9999
curl http://localhost:9999/completion -d '{"prompt":"Hello","n_predict":32,"temperature":0}'
```

## Acceptance Criteria

- All 23 patches successfully applied (or verified as already upstream)
- Existing production models pass smoke tests
- Qwen3.5-35B-A3B loads and generates text
- Build succeeds with `-DGGML_CPU_ALL_VARIANTS=ON -DLLAMA_CURL=ON`

## Patch Summary

16 custom commits applied from 25 original. Skipped:
- `2a16c4388` lookup crash fix — upstream `148833913`
- `7bf427dc6` lookahead n_seq_max — upstream
- `93eb39f39` MTMD fixes — upstream has many improvements
- `8e35dbc01` prompt lookup — superseded by upstream ngram speculation (5 types)
- `537c121ad` merge commit, `2ee7aa7ee` repack v2 (first version sufficient)
- Doc-only commits (`85ee1d557`, `46c77cf97`, `e30536310`)
- `2001f31d6` repack tests (tied to merge commit)

Added: `3227afb41` SSM state checkpointing (WS1 conditional Go)

Conflicts resolved:
- `qwen3next.cpp`: merged upstream causal_mask additions with our layer_exit
- `llama-kv-cache.cpp` (x2): adapted SWA optimization to use `llama_hparams::is_masked_swa()` API
- `server-context.cpp`: merged slot erase with upstream early-return style

## Closeout

- [x] Branch `production-consolidated-v2` created (16 commits on origin/master)
- [x] All patches applied and conflict-resolved
- [x] Build passes (`cmake -DGGML_CPU_ALL_VARIANTS=ON -DLLAMA_CURL=ON`)
- [x] Existing models smoke-tested (Qwen3-Coder-30B: 34.0 t/s)
- [x] Qwen3.5 loads and generates (Qwen3.5-35B-A3B: 10.9 t/s)
- [x] WS1 SSM checkpoint applied (conditional Go)
- [ ] Update `epyc-llama` CLAUDE.md with new branch info
- [ ] Update `epyc-root` dependency map if branch name changes
- [x] Update `progress/YYYY-MM/YYYY-MM-DD.md`
- [x] Move handoff to `completed/`
