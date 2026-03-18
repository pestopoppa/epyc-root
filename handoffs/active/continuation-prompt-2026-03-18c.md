# Continuation Prompt — After Container Rebuild (2026-03-18c)

Copy everything below the line into your next Claude Code session.

---

Read first: handoffs/active/inference-acceleration-index.md

Then read: handoffs/active/dflash-block-diffusion-speculation.md (focus on "Session 2026-03-18c" at the bottom)

Context: Previous session applied the shared lm_head fix (commit 4c4cf2208 on feature/dflash-speculation). Per-token acceptance is 27% (correct), but block-mode (16 tokens) is only ~1.4% because positions 2-15 in each block fail. The multi-position issue needs further diagnosis. Container was rebuilt to add NUMA access.

Commits already made:
- 4c4cf2208 on feature/dflash-speculation (llama.cpp-dflash worktree): lm_head sharing fix
- b0f5d50 on main (epyc-root): handoff + progress + index updates

Immediate priorities (in order):

1. NUMA tests (highest priority — verify container has NUMA now)
   - Run: numactl --hardware (expect 2-node topology, EPYC 9655)
   - S2: NUMA parallel decode on Qwen3.5-35B-A3B Q4_K_M — benchmark 1 vs 2 vs 4 concurrent single-token decodes across NUMA nodes
   - T5: tree speculation on NUMA dual-node (Qwen2.5-Coder-32B f16)
   - T6: tree speculation on NUMA dual-node (Qwen3-Coder-480B-A35B Q4_K_M)
   - Use production llama.cpp binary: /mnt/raid0/llm/llama.cpp/build/bin/llama-server
   - Benchmark script: /mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_tree_speculation_server.sh
   - See tree-speculation-numa-drafting.md for full Phase 7 details

2. DFlash multi-position investigation (if NUMA tests complete or blocked)
   - The lm_head fix is already applied and working (27% per-token)
   - Block-mode failure: positions 2-15 produce wrong predictions, only position 1 works
   - Key diagnostic: install PyTorch + safetensors, run HF DFlash model on same prompt, compare per-position logits with C++ output
   - Also try: f32 drafter GGUF (rule out f16 precision), KV cache accumulation (HF accumulates past_key_values_draft across rounds, we clear each round)
   - DFlash worktree: /mnt/raid0/llm/llama.cpp-dflash (branch: feature/dflash-speculation, 21 commits)
   - DFlash GGUF: /mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash-f16.gguf
   - Target model: /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf
   - Server launch: LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-dflash/build/bin llama-server -m <target> -md <drafter> --draft-max 16 -t 96 --port 8199
   - NOTE: cmake + build-essential may need reinstalling after container rebuild

3. draft_max changes are already in model_registry.yaml — no action needed

Key finding from this session:
- HF utils.py extract_context_feature has offset=1, so target_layer_ids [1,12,23,34,45] maps to C++ layer outputs {1,12,23,34,45} (the original indices were correct all along)
- Position 1 argmax is IDENTICAL between draft-max 2 and draft-max 16 (the noise tokens don't corrupt position 1)
- The DFlash drafter genuinely cannot predict positions 2-15 in our implementation — needs PyTorch reference comparison to find the subtle difference
