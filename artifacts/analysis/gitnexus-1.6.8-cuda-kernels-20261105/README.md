# GitNexus 1.6.8 CUDA kernel indexing fix (HYG-GITNEXUS-CUDA-KERNEL-IMPACT)

Operator approval 2026-11-05: "approved. Let me know if you need me to run somethign" (patching the root-owned global package).

tree-sitter-cpp has no CUDA grammar, so 1.6.8 mis-indexed CUDA kernels in `.cu`/`.cuh` files (KPF-41.DIRECT-VEC-IMPACT-R6/R8, `flash_attn_ext_vec` at `fattn-vec.cuh:21`):

1. `template<...> __launch_bounds__(N, M) static __global__ void k(...)` parsed with the attribute as the function name (`Template:...:__launch_bounds__`, `Function:...:__launch_bounds__~c:...`). On a small fixture the whole translation unit degrades into ERROR nodes.
2. `k<<<grid, block>>>(args)` parsed as shift expressions, so launches had no CALLS edge.
3. A kernel handed to a launcher as a handle (`fattn_kernel_t k = kern<D,...>; launch_fattn(..., k, ...)`, `const auto k = kern<...>;`). This is how llama.cpp launches `flash_attn_ext_vec`, so it had no edge either.

`fix.patch` changes three files:

- `dist/core/tree-sitter/safe-parse.js`: `maskCudaSyntax()` runs inside `parseSourceSafe`, which every parse goes through (worker, scope captures, range bindings, embeddings). It does nothing unless the text contains a CUDA marker. When one is present, it replaces `__launch_bounds__(...)` (with balanced parentheses), `__global__`, `__device__`, `__host__`, `__forceinline__`, `__noinline__` and each `<<<...>>>` launch configuration with spaces. A configuration is masked only if it contains no `;`, `{` or `}`. Newlines and length are preserved, so every byte offset and row/column still points into the original text. A launch then parses as `k(args)`.
- `dist/core/ingestion/languages/cpp/query.js` adds three `@reference.call.free` patterns. Each covers a `template_function` used as a value: an initializer, a call argument, or the right-hand side of an assignment. That records a kernel-handle reference as an edge from the enclosing function.

- `dist/storage/parse-cache.js`: `PARSE_CACHE_VERSION` gets the suffix `+epyc-cuda1`. Without it, a warm parse cache written by the unpatched package is replayed and the fix has no effect. The first r9 reindex hit exactly this (r9 INCONCLUSIVE: `__launch_bounds__` nodes still present, `cache replay` in the analyzer log).

Files: `manifest.json` pins the original and candidate SHA-256 for all three files. `originals/` holds the pristine copies and `SHA256SUMS`. `apply-or-rollback.sh` is the 20261104 script plus an idempotence check: if every file is already in the target state, it reports that and exits 0. It refuses a wrong package or version and any wrong preimage, dry-runs the patch, applies it, and verifies the postimage. `apply-test.txt` records a run on a disposable copy: apply, re-apply (no-op), rollback, re-rollback (no-op), and a refusal on a wrong preimage. `installed-apply.txt` records the apply on the host, run as `sudo -n`.

Regression fixture: `fixture/run.sh <package-root> <fresh-workdir> [<warm-cache-package-root>]` indexes `fixture/kern.cu` in a private `GITNEXUS_HOME`. It covers the `__launch_bounds__` template kernel, a plain `__global__` kernel, both `<<<>>>` launch forms and both handle forms. With the third argument, the repo is first indexed by that package, so a stale parse cache is present. Recorded runs use the pristine package as the warm-cache source. Results: on unpatched 1.6.8 it FAILS on every check (`fixture-before.json`); on the patched package it PASSES on every check (`fixture-after.json`).

Composition with the earlier patches: this patch touches neither `languages/cpp/captures.js` (enum fix, 20261104) nor `pipeline-phases/communities.js` (double-free fix, `doublefree/`). After the apply, both of those files are still at their candidate hashes (`installed-apply.txt`), and each patch's rollback stays independent of the others.

Rollback: `sudo -n bash ./apply-or-rollback.sh rollback /usr/local/share/npm-global/lib/node_modules/gitnexus` from this directory. Indexes built before the fix keep their wrong CUDA symbols and need a re-index.

Known limits: masking is lexical, so a `<<<` inside a string or comment on a CUDA-marked file is also blanked; this is harmless to the graph. A handle reference is recorded as CALLS, not as a separate reference type. Function names used as values without template arguments (`launch(kern)`) are not covered.
