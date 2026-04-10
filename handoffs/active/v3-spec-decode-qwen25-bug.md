# v3 Spec Decode Bug: Qwen2.5-Coder-32B + Draft Model

**Status**: ACTIVE — coder_escalation non-functional with spec decode on v3
**Created**: 2026-04-10
**Priority**: HIGH (production regression — coder_escalation is the primary escalation path)
**Categories**: llama.cpp, inference, bug
**Depends on**: None
**Related**: [`llama-cpp-v3-upstream-rebuild.md`](llama-cpp-v3-upstream-rebuild.md), [`inference-acceleration-index.md`](inference-acceleration-index.md)

---

## Problem

Speculative decoding with any draft model on Qwen2.5-Coder-32B-Instruct returns `HTTP 500: Invalid input batch` on **every prompt** (including single-word prompts). All other models work fine with spec decode on v3.

## Reproduction

```bash
# Fails on v3 (production-consolidated-v3, version 8754, commit 7057025df):
/mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen2.5-Coder-32B-Instruct-GGUF/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf \
  -md /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen2.5-Coder-0.5B-GGUF/Qwen2.5-Coder-0.5B-Q4_K_M.gguf \
  --draft-max 32 --port 9994 -np 1 -c 4096 -t 48 --flash-attn on --jinja

curl http://localhost:9994/v1/chat/completions \
  -d '{"model":"auto","messages":[{"role":"user","content":"Hi"}],"max_tokens":16}'
# → 500 Invalid input batch

# Works on v2 (production-consolidated-v2) with identical flags.
```

## Isolation Tests (2026-04-10)

| Test | Result | Conclusion |
|------|--------|-----------|
| Coder-32B WITHOUT draft | WORKS | Not a model loading issue |
| Coder-32B + Coder-0.5B draft | **FAILS** | Spec decode broken |
| Coder-32B + Qwen3 0.75B draft | **FAILS** | Not draft-model-specific |
| Coder-32B + draft, no KV quant | **FAILS** | Not KV quant interaction |
| Coder-32B + draft, 10-word prompt | **FAILS** | Not prompt-length-dependent |
| REAP-246B (Qwen3) + draft | WORKS | Qwen3 arch unaffected |
| Qwen3.5-35B + draft | WORKS | Qwen3.5 arch unaffected |
| Worker 30B-A3B + lookup | WORKS | Lookup decoding unaffected |

**Root cause**: v3 upstream changes broke spec decode specifically for **Qwen2.5 architecture**. Qwen3.x and Qwen3.5 are fine.

## Likely Upstream Cause

538 upstream commits between v2 and v3. Candidates:
- Attention head dimension / GQA handling changes in spec decode validation
- `ggml_set_rows` batch construction for non-matching architectures (main vs draft)
- Server-side speculative decode batch assembly (`server.cpp` or `server-context.cpp`)

The stashed fix on v2 (`kv-cache f32 cast fix for ggml_set_rows`) may be related — it addressed f16→f32 type mismatches in the KV cache copy path.

## Current Workaround

Coder_escalation runs on v3 binary **without spec decode** (no `-md`, no `--draft-max`). Functional but slower (~7.4 t/s vs 10.8 t/s with spec decode on v2).

`orchestrator_stack.py` has `_V2_ROLES` / `LLAMA_SERVER_V2` infrastructure for per-role binary override, but the v2 worktree build also showed the same error (possibly contaminated by another agent modifying the repo during build). A clean v2 rebuild is needed to verify.

## Additional Findings (2026-04-10)

- **v2 worktree build also fails** — built from `/tmp/llama-v2-build` worktree, same "Invalid input batch". Likely contaminated (another agent session may have been modifying the production repo concurrently). The original v2 binary was overwritten during v3 swap and is unrecoverable.
- **NOT the draft model** — fails with both Qwen2.5-Coder-0.5B-Q4_K_M and Qwen3-Coder-0.75B draft
- **NOT KV quantization** — fails without `-ctk`/`-ctv` flags
- **NOT prompt length** — fails on "Hi" (single token)
- **Qwen2.5-Coder-32B WITHOUT draft works fine** on v3

## Resume Here

1. **Clean v2 build**: Clone fresh from `fork/production-consolidated-v2` into an isolated directory (NOT a worktree). Build and test spec decode with Coder-32B. This determines if the bug is v3-only or pre-existing.
2. If v3-only: `git bisect` between v2 and v3 (24 commits) to find the breaking cherry-pick
3. If also v2: check if the Qwen2.5-Coder-0.5B draft model GGUF was corrupted or replaced
4. Run v3 server with `LLAMA_LOG_LEVEL=debug` to get batch construction diagnostics
5. Check stashed `ggml_set_rows` f32 cast fix (stash@{0} in production repo)

## Key Files

- `/mnt/raid0/llm/llama.cpp/tools/server/server.cpp` — server-side spec decode orchestration
- `/mnt/raid0/llm/llama.cpp/src/llama-graph.cpp` — graph construction (batch validation)
- `/mnt/raid0/llm/llama.cpp/src/llama-kv-cache.cpp` — KV cache (stashed fix here)
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` — per-role binary path support (`_V2_ROLES`, `LLAMA_SERVER_V2`)
