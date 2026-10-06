# CTX-JETLONG-PROTO: plan for the real long-context tests on the :8070 model

Status: plan and script skeleton only (`longctx_skeleton.sh`). Nothing here has been run. The main session
schedules the CPU window. Binary: branch `llama.cpp-experimental-jetlong-proto-20261006` (worktree
`/mnt/raid0/llm/worktrees/llama-jetlong-proto-20261006`, `build-cpu/bin`). Production v10 is not touched.

Model and recipe: `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf`. The canonical :8070 argv is the same one
`../run_ab.sh` uses (`-np 4 -c 262144 -ub 2048 --flash-attn on -ctk q8_0 -ctv q8_0 --mlock --no-mmap
--spec-type draft-mtp --spec-draft-n-max 4`). The Jet-Long arm adds `--jetlong-window 2048`, with w0 = 2048 as in the
paper's Eq. 2. The native window w defaults to `n_ctx_orig` = 262144.

## Pre-flight (every arm)
- `strings build-cpu/bin/libllama.so | grep -c jetlong` is greater than 0, and `llama-server --help` lists `--jetlong-window`.
- The `.so` mtime is later than the branch tip commit time.
- `verify_ggml_linkage.sh` passes. `LD_LIBRARY_PATH` points at this tree's `build-cpu/bin` (three ggml generations live on this host).
- The server log contains `Jet-Long ON: w0 = 2048, w_native = 262144` for the main context and for the MTP context.

## A. In-window identity (gate: exact; this decides whether the prototype may go near production)
Arms: **S** = experimental binary without the flag, and **J** = the same binary with `--jetlong-window 2048`. Both use the canonical argv
at `-c 262144`. Note that S is the experimental binary, not production v10. A v10-vs-S check is a separate guard; it should also give
0, because the flag-off graph is the stock graph.
1. The 20 greedy prompts plus the MTP acceptance prompts from `../run_ab_client.py` (frozen manifest, with the digest recorded),
   plus the 20-prompt holdout from the CTX-1 controls.
2. Long in-window prompts at depths 10/30/50/70/90% of 250K, all of which stay at or below 262144 including generation.
3. Record per prompt: the token sequence; the first diverging token; the top-k logprobs (`n_probs`) at every step; and the MTP
   acceptance (accepted/drafted). The server's MTP statistics are in the `--verbosity 4` log.
4. Raw logits: for exact logit identity, run `llama-eval-callback`-style dumps (or `GGML_SCHED` debug of `result_output`) on
   prompts 1-3 for both arms.
Rule: 20/20 + 20/20 identical tokens, MTP acceptance identical (same accepted counts, not within 1 pp), and logits max-abs
exactly 0 on the dumped prompts. **Any non-zero difference rejects in-window use.** Expected by construction: no Jet-Long node is
built while every sequence of a ubatch has L <= 262144 (`llama_jetlong_plan_ubatch`), and graph reuse is unchanged.

## B. Above native: needle recall vs static YaRN (the accuracy claim)
Arms at `-c 1048576 -np 1` (one sequence, so that G is not shared with another slot):
- **J**: `--jetlong-window 2048`, no YaRN.
- **Y**: `--rope-scaling yarn --rope-scale 4 --yarn-orig-ctx 262144` (static YaRN, the incumbent for > 262K).
- **J-u** (optional, 300K only): `--jetlong-window 2048 --jetlong-uncached`. It must give the same tokens as J (cached == uncached).
Lengths 300K, 524K and 1M; depths 10/30/50/70/90%; 5 needles x 3 seeds. Prompts are built with
`epyc-inference-research/scripts/benchmark/long_context_adapters.py` and scored with `niah_scorer.py`, which reports strict and lenient
together. The denominator is complete: every item counts, including timeouts as failures.
Rule (from STAGE3 CTX-5): J >= Y on lenient recall at each length, with the native-window gate (A) passed first.
**Prototype cost caveat (must be in the window request):** the non-fused prototype computes the above-native attention with plain
ggml ops in f32. Each layer and ubatch materialises 3 score tensors of n_kv x n_ubatch x 16 x 4 B, plus an f32 transposed copy of V
(2 GiB per layer at 1M). Use `-ub 32 -b 32` for the J arms above native. That is 2 GiB of scores per tensor per layer at 1M, and
roughly 0.3 s per ubatch at 300K, so a 300K prefill takes minutes, 524K takes about 1-2 h and 1M takes several hours. Run Y at the
same `-ub` for comparability. If the window cannot hold 1M, run 300K and 524K and keep 1M for the fused kernel (self-fuse trigger).

## C. Decode tok/s at depth (a cost claim, separate full-host window)
Use the full-host canonical recipe (not quadrant-pinned) and `llama-bench`-style depth or server decode after a prefilled cache
(slot restore). Depths are 250K (in-window control: J must equal S within noise), 270K (G=2), 524K (G=2), 600K (G=3) and 1M (G=4).
Arms: S/Y, J (cached), J-u (uncached). Report tok/s, the MTP acceptance and the per-step side-cache rows. Rows are n_tokens of the step
in steady state, all cells at an epoch change, and all cells after any `state_read`/K-shift. Compare with CTX-3a: the cached correction
measured +2.4 ms/step at 262K and +9.4 ms at 1M across 10 layers, uncached +13.5/+46 ms. The prototype adds the non-fused overheads,
the 3 matmuls, the V cast and the concat/get_rows splice. That cost is the measured price of NON-fused; the fused kernel is a separate
follow-on.

## MTP notes for the window
- The MTP context gets the same `--jetlong-window` through `common_context_params_to_llama`. Its own full-attention layer (il 40,
  plain KV cache) gets its own side cache and the same G rule.
- Verify batches: one G per ubatch, the batch max, as in the reference M:146. A verify batch that straddles k*w uses the larger G for
  all of its tokens, while sequential decode would use the smaller G for the first ones. Expect a tiny acceptance loss at each epoch
  boundary only. Measure acceptance above native in J vs Y (trigger "MTP/DFlash2 mirroring" in STAGE3 section 2).
- In-window: no change. The flag builds nothing, so acceptance must be identical (gate A).
