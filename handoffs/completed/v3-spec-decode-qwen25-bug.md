# v3 Spec Decode Bug: Qwen2.5-Coder-32B + Draft Model

**Status**: FIXED in experimental — tree speculation seq_id overflow when `kv_unified=false`
**Created**: 2026-04-10
**Fixed**: 2026-04-10
**Priority**: HIGH (production regression — coder_escalation is the primary escalation path)
**Categories**: llama.cpp, inference, bug
**Depends on**: None
**Related**: [`llama-cpp-v3-upstream-rebuild.md`](llama-cpp-v3-upstream-rebuild.md), [`inference-acceleration-index.md`](inference-acceleration-index.md)

---

## Problem

Speculative decoding with any draft model on Qwen2.5-Coder-32B-Instruct returns `HTTP 500: Invalid input batch` on **every prompt** (including single-word prompts).

## Root Cause

**Tree speculation multi-path verification creates seq_ids that exceed `n_seq_max` when `kv_unified=false`.**

Detailed trace:
1. Default `p_split=0.1` enables tree speculation (`COMMON_SPECULATIVE_TYPE_TREE`)
2. Tree speculation generates multiple draft paths (branching candidates)
3. Multi-path target verification (`server-context.cpp` ~line 2299) adds alternative paths to the batch with seq_ids: `tree_seq_base + k` where `tree_seq_base = n_parallel + slot.id * 8`
4. With `-np 1`, `tree_seq_base = 1`, so alternative paths get seq_ids 2, 3...
5. But `kv_unified=false` (default) means `n_seq_max = n_parallel = 1`
6. Batch validation rejects: `invalid seq_id[3][0] = 2 >= 1`

The auto-detection at line 679 that bumps `n_seq_max` for tree speculation only fires when `kv_unified=true`, leaving the non-unified path unprotected.

**Not Qwen2.5-specific**: The bug affects ALL architectures when `kv_unified=false` + draft model + default `p_split`. The original isolation tests for Qwen3/Qwen3.5 likely used `--kv-unified` or different spec decode configurations.

Debug log evidence:
```
init: invalid seq_id[3][0] = 2 >= 1
decode: failed to initialize batch
llama_decode: failed to decode, ret = -1
```

## Fix Applied (experimental)

**File**: `llama.cpp-experimental/tools/server/server-context.cpp` (load_model, ~line 675)

Auto-enable `kv_unified` when tree speculation is active (draft model + `p_split > 0`). Tree multi-path verification requires shared KV cache (`kv_unified=true`) and sufficient `n_seq_max` for alternative path seq_ids. Without `kv_unified`, `n_seq_max` partitions the context window, starving each tree path.

```cpp
// Before (broken): only bumped n_seq_max if user manually passed --kv-unified
if (p_split > 0 && has_dft && params_base.kv_unified) { ... }

// After (fixed): auto-enable kv_unified when tree speculation is configured
if (p_split > 0 && has_dft) {
    if (!params_base.kv_unified) {
        params_base.kv_unified = true;  // tree paths need shared context
    }
    params_base.n_seq_max = 9 * n_parallel;  // 8 tree paths + 1 primary per slot
}
```

Hybrid/recurrent models are still safe — the existing `has_recurrent` guard at the verification site (~line 2299) prevents tree multi-path from firing, so `kv_unified=true` has no negative effect.

## Verification

| Test | Result |
|------|--------|
| Fixed binary, default p_split, NO --kv-unified | PASS — auto-enables unified, tree verification, 5/9 accepted |
| Fixed binary, default p_split, explicit --kv-unified | PASS — tree verification, 5/9 accepted |
| Fixed binary, multi-request stability | PASS — 3/3 requests, 73-100% acceptance |
| Logs confirm auto-enable | `tree speculation: auto-enabling --kv-unified`, `n_seq_max=9` |

## Remaining Work

- [ ] **Port fix to production v3**: Apply one-line change to `/mnt/raid0/llm/llama.cpp` `production-consolidated-v3` and rebuild
- [ ] **Remove v2 workaround**: Switch coder_escalation back to v3 binary in orchestrator_stack
- [ ] **Stashed f32 cast fix**: `stash@{0}` in production repo (`kv-cache f32 cast fix for ggml_set_rows`) is a **separate issue** — f16→f32 type mismatch in KV cache copy. NOT the cause of this bug, but may be needed for quantized KV cache scenarios. Evaluate independently.

## Key Files

- `/mnt/raid0/llm/llama.cpp-experimental/tools/server/server-context.cpp` — fix applied (line ~2299)
- `/mnt/raid0/llm/llama.cpp/tools/server/server-context.cpp` — production file to port fix to
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` — per-role binary path (workaround to remove)
