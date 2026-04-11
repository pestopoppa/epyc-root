# v3 Hybrid SSM+MoE Regression: Empty/Gibberish Output

**Status**: ACTIVE — all hybrid models produce empty or gibberish output on v3 binary
**Created**: 2026-04-11
**Priority**: CRITICAL (frontdoor + architect_general non-functional = stack unusable)
**Categories**: llama.cpp, inference, bug
**Depends on**: None
**Related**: [`llama-cpp-v3-upstream-rebuild.md`](llama-cpp-v3-upstream-rebuild.md), [`v3-spec-decode-qwen25-bug.md`](v3-spec-decode-qwen25-bug.md)

---

## Problem

All hybrid SSM+MoE models produce empty or gibberish output on the v3 binary (`production-consolidated-v3`, version 8755, commit `0ddff9ed1`). Pure MoE and dense models work correctly.

## Affected Models

| Model | Architecture | Ports | Symptom |
|-------|-------------|-------|---------|
| Qwen3.5-35B-A3B (frontdoor) | Hybrid SSM+MoE | 8070/8080/8180/8280/8380 | Empty response |
| Qwen3-235B-A22B (architect_general) | Hybrid SSM+MoE | 8083/8183 | Empty response |
| Qwen3-Next-80B-A3B (ingest) | Hybrid SSM+MoE | 8085 | Gibberish: "To do the, are the, is the..." |
| Qwen3-VL-30B-A3B (vision_escalation) | Hybrid SSM+MoE | 8087 | Timeout |

## Working Models (same binary)

| Model | Architecture | Ports | Status |
|-------|-------------|-------|--------|
| Qwen2.5-Coder-32B | Dense | 8071/8081/8181/8281/8381 | OK |
| Qwen3-Coder-30B-A3B | Pure MoE | 8072/8082/8182/8282/8382 | OK |
| REAP-246B-A35B | Pure MoE (pruned) | 8084 | OK |
| Qwen2.5-VL-7B | Dense | 8086 | OK |

## Reproduction

```bash
# Gibberish via /completion (raw, no chat template)
curl http://localhost:8070/completion \
  -d '{"prompt":"What is the capital of France?","n_predict":32,"temperature":0}'
# → {"content":"\n# 199999930/ 20/ 20/ 20/ 20/ 20/ 20/ 20/ 20/ / 20/ 20/ /usr/bin/ 20/ 2"}

# Empty via /v1/chat/completions (chat template applied)
curl http://localhost:8070/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is the capital of France?"}],"max_tokens":32}'
# → {"choices":[{"message":{"content":""}}]}

# Compare with working pure MoE model on same binary:
curl http://localhost:8072/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is the capital of France?"}],"max_tokens":32}'
# → {"choices":[{"message":{"content":"The capital of France is Paris."}}]}
```

## Key Observations

1. **Architecture-specific**: Only hybrid SSM+MoE models affected. Dense and pure MoE work fine.
2. **Both endpoints broken**: `/completion` (raw) and `/v1/chat/completions` (chat template) both fail.
3. **Not a chat template issue**: Raw completion produces gibberish too.
4. **v2 worked**: These exact models worked on `production-consolidated-v2` (same GGUF files, same launch flags except `--kv-hadamard` which v3 auto-enables).
5. **Gibberish pattern**: Numbers, slashes, fragments (`199999930/ 20/ 20/`). Looks like attention over wrong positions or corrupted KV state.
6. **v3 has 538 upstream commits**: Many touch SSM/recurrent model handling.

## Likely Upstream Cause

The hybrid SSM+MoE architecture (Qwen3.5, Qwen3-Next) has both transformer attention layers AND Delta Net recurrent (SSM) layers. Upstream changes to:

- Recurrent/SSM state management (`llama-memory`, `llama-kv-cache`)
- `has_recurrent` guards and conditional paths
- Attention masking for SWA (sliding window attention) — hybrids interleave SWA and full attention
- The `kv_unified` auto-enable from the spec decode fix may interact with hybrid memory

The stashed fix (`stash@{0}: kv-cache f32 cast fix for ggml_set_rows`) adds f32 casts in `cpy_k` and `cpy_v` — this may be relevant if hybrid models use f16 intermediate KV types that v3's `ggml_set_rows` can't handle.

## Investigation Plan

### Phase 1: Quick checks
1. **Apply stashed f32 cast fix**: `git stash pop` in production repo, rebuild, test frontdoor. If this fixes it, the root cause is `ggml_set_rows` type mismatch on hybrid KV.
2. **Test with `--kv-unified` explicitly**: Hybrid models may need different KV handling.
3. **Test without KV quantization** (`-ctk` / `-ctv` removed): Isolate if KV quant interacts with hybrid architecture.
4. **Test without `--flash-attn`**: Flash attention paths differ for hybrid vs pure attention.
5. **Test without `--jinja`**: Chat template processing may differ.

### Phase 2: Bisect if Phase 1 doesn't find it
6. **Binary search**: The v3 branch has 24 cherry-picked commits. Bisect which commit broke hybrid models.
7. **Compare v2 vs v3 for hybrid-specific code**: `git diff v2..v3 -- src/llama-kv-cache.cpp src/llama-graph.cpp src/llama-memory*`

### Phase 3: Fix
8. Apply fix, rebuild, verify all 4 hybrid models produce coherent output.
9. Verify pure MoE and dense models still work (no regression).

## Workaround (if fix takes time)

Run hybrid model servers with v2 binary (`/mnt/raid0/llm/llama.cpp/build-v2/bin/llama-server`).
The `orchestrator_stack.py` already has `_V2_ROLES` / `LLAMA_SERVER_V2` infrastructure for per-role binary override — extend `_V2_ROLES` to include `frontdoor`, `architect_general`, `ingest_long_context`, `worker_vision_escalation`.

Note: v2 hybrid servers need `--kv-hadamard` flag (v3 auto-enables, v2 requires explicit).

## Key Files

- `/mnt/raid0/llm/llama.cpp/src/llama-kv-cache.cpp` — KV cache (stashed f32 fix here)
- `/mnt/raid0/llm/llama.cpp/src/llama-graph.cpp` — graph construction (hybrid attention paths)
- `/mnt/raid0/llm/llama.cpp/src/llama-memory.cpp` — memory management (recurrent state)
- `/mnt/raid0/llm/llama.cpp/tools/server/server-context.cpp` — server (has_recurrent guards)
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` — `_V2_ROLES` for workaround

## Test Matrix (for verification after fix)

| Model | Port | Test |
|-------|------|------|
| Qwen3.5-35B-A3B | 8070 | "What is the capital of France?" → contains "Paris" |
| Qwen3-235B-A22B | 8083 | Same |
| Qwen3-Next-80B-A3B | 8085 | Same |
| Qwen3-VL-30B-A3B | 8087 | Same |
| Qwen3-Coder-30B-A3B | 8072 | Same (regression check — must still work) |
| Qwen2.5-Coder-32B | 8071 | Same (regression check) |
