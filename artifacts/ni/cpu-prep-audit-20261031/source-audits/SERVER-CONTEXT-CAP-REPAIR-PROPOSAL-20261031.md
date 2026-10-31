# JetLong 4xJ context-cap repair proposal — source only, unapproved

The original Y arm failed before any token was processed: `runs/20261031T080522Z-2518304/Y.server.log` shows `-c 131072`, then `n_ctx_slot = 32768` and HTTP 400 for the unchanged 130000-token fixture. The running server reports `--version` **10308 (`ebbf9ad0c`)**; `build-cpu/bin/llama-server` and `libllama-server-impl.so` are dated 2026-10-06 21:24Z, before the checkout's `e6ea79421` commit at 21:40Z. The original manifest's `binary_proof.commit=e6ea79421` is untrue for the binary it actually invoked. Its source and binary identities must be requalified, including the small-ubatch fix symbols and post-build mtime, before any native run.

The server source at both `ebbf9ad0c` and `e6ea79421` unconditionally caps `n_ctx_slot` to the model's `n_ctx_train` in `tools/server/server-context.cpp` around lines 1316–1322. The GGUF says `qwen3.context_length=32768`; changing this metadata through `--override-kv` would misstate the model's native training context and is excluded. A narrow experimental source repair can permit a requested extension context only for the two explicitly configured modes used by this packet:

```diff
--- a/tools/server/server-context.cpp
+++ b/tools/server/server-context.cpp
@@
         const int n_ctx_train = llama_model_n_ctx_train(model_tgt);

         int n_ctx_slot = llama_n_ctx_seq(ctx_tgt);
-        if (n_ctx_slot > n_ctx_train) {
+        const bool explicit_yarn_extension = params_base.n_ctx > n_ctx_train &&
+            params_base.rope_scaling_type == LLAMA_ROPE_SCALING_TYPE_YARN &&
+            params_base.yarn_orig_ctx == n_ctx_train;
+        const bool explicit_jetlong_extension = params_base.n_ctx > n_ctx_train &&
+            params_base.jetlong_window > 0 && params_base.jetlong_native == n_ctx_train;
+        if (n_ctx_slot > n_ctx_train && !explicit_yarn_extension && !explicit_jetlong_extension) {
             SRV_WRN("the slot context (%d) exceeds the training context of the model (%d) - capping\n", n_ctx_slot, n_ctx_train);
             n_ctx_slot = n_ctx_train;
         }
```

This is a proposal, not a compiled fix. The server context path affects every serving request; run `gitnexus context` and upstream impact on the candidate symbol before any source edit and report the result. Verify C++ field/API names against the exact build source, test default-cap retention, explicit Y and J opt-in, and actual `/props` slot context at 131072. Then rebuild the **experimental** candidate and prove `--version`, ELF/DSO SHA, linkage and mtime. Do not edit or build frozen production/store trees. Run the real packet entry at R11 for ≤300 s: one short real response and result writer; one full-context 130000-token request accepted into active prefill, stopped at cutoff rc75/partial with owned PID death. This is lifecycle/context admission only, not 130000-token completion or recall.

Ownership: the only located JetLong checkout is `/mnt/raid0/llm/worktrees/llama-jetlong-hip-20261006`, branch `llama.cpp-experimental-jetlong-hip-20261006` @ `e6ea79421`; it is the workspace-ec experimental tree, not a verified NI-owned lane. It has untracked `cpu.rc` and `hip.rc`, so no agent may mutate it by assuming it is free. No NI-owned JetLong checkout or post-fix build path was located. After MAIN coordinates source ownership, reuse that checkout serially and build into a distinct output path under this packet (for example `experimental-build-cpu-r2/`) without a new full clone or production/store writes. A new binary becomes a new recipe identity; pin it and compare paired Y/J only within that new source-bound run. Coordinate any candidate integration with the JetLong owner and champion fold ledger; no v10 change or promotion follows this diagnostic.

Status: proposal only; no patch applied, build, model load, or READY successor.
