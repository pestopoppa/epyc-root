# Upstream Bug Report Draft: llama-finetune backward pass failures

**STATUS**: SUBMITTED - https://github.com/ggml-org/llama.cpp/issues/18805

**FOLLOW-UP COMMENT**: https://github.com/ggml-org/llama.cpp/issues/18805#issuecomment-3744233010
- Asked maintainers about why FLASH_ATTN_BACK is disabled with GGML_ABORT
- Awaiting response before attempting to revive the code

---

## Proposed Issue Title

`llama-finetune broken on modern transformers: cascading failures in SET_ROWS, FLASH_ATTN_EXT, and graph allocation`

---

## Issue Body (Copy below line for GitHub submission)

---

### Summary

`llama-finetune` fails on all modern transformer architectures (LLaMA 3.2, Qwen2.5, SmolLM2) due to three interconnected issues in the backward pass infrastructure. This affects builds b7405 through b7717 (current master).

**Related issues** (closed but not fixed):
- #15279 - `view_src` assertion failure (closed as "COMPLETED")
- #15090 - Graph node overflow (closed as "STALE")

Both issues describe the same fundamental problem. This report provides root cause analysis and reproduction steps.

**Note**: We considered filing this as a documentation bug since the README states "Finetuning of LLaMA 3.2 1b seems to work", but the issues run deeper than documentation—the backward pass infrastructure is missing support for operations that modern architectures require.

### Build Info

- **llama.cpp versions tested**: b7405, b7699, b7717 (537d4240d)
- **Platform**: Linux x86_64 (Ubuntu 24.04, GCC 13.3.0)
- **Hardware**: AMD EPYC 9655 (CPU-only, 96 cores, 1.1TB RAM)
- **GGUF format**: V3

### Models Tested

| Model | Size | Format | Result |
|-------|------|--------|--------|
| LLaMA 3.2 1B Instruct | 1.2B | F32 GGUF | **Crash #1** |
| Qwen2.5-0.5B-Instruct | 0.5B | F32 GGUF | **Crash #1** |
| SmolLM2-135M-Instruct | 135M | F32 GGUF | **Crash #2** (per #15090) |

All models crash. The README claims "Finetuning of LLaMA 3.2 1b seems to work" but this is not the case on current builds.

### Reproduction

```bash
# Convert model to F32 (required for training)
llama-gguf-hash --convert-to-f32 Llama-3.2-1B-Instruct-F16.gguf Llama-3.2-1B-Instruct-f32.gguf

# Download test prompt (~450 tokens for dataset initialization)
curl -sL https://gist.githubusercontent.com/pestopoppa/75931845aa001000403dc5107e3e60c0/raw/ttt_test_prompt.txt > test_prompt.txt

# Attempt finetune
OMP_NUM_THREADS=1 numactl --interleave=all \
  ./build/bin/llama-finetune \
  -m Llama-3.2-1B-Instruct-f32.gguf \
  -f test_prompt.txt -c 256
```

### Crash #1: SET_ROWS view_src assertion

```
ggml.c:6928: GGML_ASSERT(!node->view_src || node->op == GGML_OP_CPY ||
    node->op == GGML_OP_VIEW || node->op == GGML_OP_RESHAPE ||
    node->op == GGML_OP_PERMUTE || node->op == GGML_OP_TRANSPOSE) failed
```

**Debug output** (after adding logging before the assertion):
```
=== DEBUG: view_src tensor with disallowed op ===
  tensor name: cache_k_l0 (view)
  tensor op: 42 (SET_ROWS)
  view_src name: cache_k_l0
  tensor flags: 0x0 (PARAM=0, LOSS=0)
```

**Root cause**: `ggml_set_rows()` at `ggml/src/ggml.c:3842-3849` creates a view tensor:
```c
struct ggml_tensor * result = ggml_view_tensor(ctx, a);  // Creates view
result->op     = GGML_OP_SET_ROWS;  // Sets op NOT in allowed list
result->src[0] = b;
result->src[1] = c;
result->src[2] = a;
return result;
```

This pattern:
1. Creates a tensor with `view_src` set (shares memory)
2. Sets op to `SET_ROWS` which is NOT in the allowed view-ops list
3. Has NO backward pass implementation in `ggml_compute_backward()`

**Workaround attempted**: Adding `SET_ROWS` to `ignore_src` in `ggml_build_backward_expand`:
```c
case GGML_OP_SET_ROWS:
    ignore_src[0] = true;
    ignore_src[1] = true;
    ignore_src[2] = true;
    break;
```

This bypasses Crash #1 but reveals Crash #2.

### Crash #2: FLASH_ATTN_EXT has no backward pass

```
ggml.c:6714: ggml_compute_backward: unsupported ggml op for backward pass: FLASH_ATTN_EXT
```

**Root cause**: Modern LLaMA/Qwen models auto-enable Flash Attention (`GGML_OP_FLASH_ATTN_EXT`). This op has no `case` in `ggml_compute_backward()` - it falls through to the default abort.

**Historical context**:
- The OLD flash attention (`GGML_OP_FLASH_ATTN`) had a backward pass (`GGML_OP_FLASH_ATTN_BACK`) added in PR #1652
- The NEW flash attention (`GGML_OP_FLASH_ATTN_EXT`) added in PR #5021 has **no backward pass**
- An external attempt to add FA backward (Pints-App/llama.cpp#1) was closed due to correctness issues
- PR #8542 mentions "work on the LLM backwards pass in the coming months"

**Workaround attempted**: `--flash-attn false` to disable Flash Attention. This reveals Crash #3.

### Crash #3: Graph node overflow

```
ggml.c:6763: GGML_ASSERT(cgraph->n_nodes < cgraph->size) failed
```

This is the same error reported in #15090 with SmolLM2-135M.

**Root cause**: When Flash Attention is disabled, the standard attention implementation creates many more intermediate nodes for the backward pass, overflowing the pre-allocated graph buffer.

### Summary of Missing Backward Pass Support

| Operation | Used For | Backward Pass? | Workaround |
|-----------|----------|----------------|------------|
| `GGML_OP_SET_ROWS` | KV cache updates | No | Can ignore sources |
| `GGML_OP_FLASH_ATTN_EXT` | Flash Attention | No | Disable FA, but causes #3 |
| Standard attention | Fallback | Creates too many nodes | Need larger graph |

### Questions

1. Is training on modern architectures (LLaMA 3+, Qwen2+) expected to work? The README suggests it should.
2. Is there active work on `FLASH_ATTN_EXT` backward pass?
3. Should `SET_ROWS` be added to the `ignore_src` list, or does KV cache need proper gradient flow?
4. What's the recommended graph size for training with standard attention?

### Environment Details

```
system_info: n_threads = 96 / 192 | CPU : SSE3 = 1 | SSSE3 = 1 | AVX = 1 |
AVX_VNNI = 1 | AVX2 = 1 | F16C = 1 | FMA = 1 | BMI2 = 1 | AVX512 = 1 |
AVX512_VBMI = 1 | AVX512_VNNI = 1 | AVX512_BF16 = 1 | LLAMAFILE = 1 |
OPENMP = 1 | REPACK = 1
```

### Suggested Labels

- `bug`
- `training`
- `high priority` (README claims functionality that doesn't work)

---

## References

### GitHub Issues
- [#15279](https://github.com/ggml-org/llama.cpp/issues/15279) - view_src assertion (closed "COMPLETED" but persists)
- [#15090](https://github.com/ggml-org/llama.cpp/issues/15090) - Graph overflow on SmolLM2 (closed "STALE")
- [#3404](https://github.com/ggml-org/llama.cpp/issues/3404) - Mistral finetune crash (actually fixed via PR #3437)

### Related PRs
- [#1652](https://github.com/ggml-org/llama.cpp/pull/1652) - Added FLASH_ATTN_BACK for old FA
- [#5021](https://github.com/ggml-org/llama.cpp/pull/5021) - Added FLASH_ATTN_EXT (no backward)
- [#8542](https://github.com/ggml-org/llama.cpp/pull/8542) - Mentions upcoming backward pass work
- [Pints-App#1](https://app.semanticdiff.com/gh/Pints-App/llama.cpp/pull/1/overview) - FA backward attempt (closed, correctness issues)

---

## Notes for User Review

**Before submitting**:
1. Test prompt gist created: https://gist.github.com/pestopoppa/75931845aa001000403dc5107e3e60c0
2. May want to tag @ggerganov or @JohannesGaessler (mentioned backward pass work in PR #8542)
3. Could offer to help test fixes if maintainers provide patches
