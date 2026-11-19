# KPF-61 third-smoke source provenance review

## Identity and custody boundary

The native result for attempt `e4dfd06df16f49258ee5bdf2ab52c0e8` pins source commit
`3ec14227a0e293bfc223c9026ed761ea3bdda9bb`, with source manifest SHA-256
`399a401628688e34242c6c8ea410acce5d628ad3dd76b77596e3a61494726690`. The custody receipt
at `/mnt/raid0/llm/tmp/kvfork/kpf61-cpu-permutation-20261104/source-custody-receipt.json`
records 3,363 verified source-file hashes and zero mismatches. The receipt's row-local private
source destination no longer exists, so its files cannot be directly inspected there.

An accessible source tree at
`/mnt/raid0/llm/tmp/kvfork/kpf62-g3-build-20261104/source` has exactly the pinned commit at
HEAD. It is a separate KPF-62 G3 scratch tree and is dirty; it is not evidence that the KPF-61
private snapshot was clean. Its tracked dirty files are:

- `scripts/chunk-kv/G3_CORPUS_CONTRACT.md`
- `scripts/chunk-kv/g3_gate.py`
- `scripts/chunk-kv/g3_manifest.py`
- `scripts/chunk-kv/tests/test_g3_manifest.py`
- `tests/CMakeLists.txt`
- `tests/test-chunk-kv-g3.cpp`

Its untracked files are:

- `scripts/chunk-kv/g3_outcome_guard.py`
- `scripts/chunk-kv/tests/test_g3_outcome_guard_integration.py`
- `tests/kpf62-outcome-budget.h`
- `tests/test-kpf62-outcome-budget.cpp`

The KPF-61 source-custody receipt lists those four untracked files as copied during custody
creation. `source-tracked.patch` has SHA-256
`49f2153e64b314cd170cc1f63236933a1a08275cac2055c085c4dc9a304eb02b`; its changes are the
G3 work, not the KPF-61 reorder implementation. This note records provenance only and makes no
source-cleanliness claim.

## Bounded offline review scope

The retained smoke inputs show a useful exact comparison: both test requests use 256 prompt
tokens, seed 6104, temperature 0, `n_predict=32`, and `n_probs=32`. The cold test supplies the
canonical reordered token sequence with `cache_prompt=false`; the reuse arm begins with the
alternate segment order, enables `cache_prompt`, and requests `kv_reorder` for offset 32 / 192
tokens. The server log reports application and a reusable prefix of 32 to 224 tokens, with three
pieces and 192 moved tokens. Both generated 32-token ID sequences match; parsed top-probability
rows differ from row 0. This is a single tiny public-model smoke, not a gate result.

Without editing or running source, the following source review can separate source-level causes:

1. **Prompt permutation / pinned-region mismatch:** trace `kv_reorder_apply` in
   `tools/server/server-context.cpp` (around 2092–2229) and planner logic in
   `tools/server/server-reorder.h`. Compare its permutation, junctions, and reported prefix
   calculations against the retained request token ranges and planner witness. This tests
   whether the transformed prompt and cached prefix ought to be token-identical.
2. **Checkpoint/reuse execution path:** trace the reorder invocation and the prompt loop in
   `tools/server/server-context.cpp` (around 3631, 5114–5165), including where junctions force
   checkpoint creation, and compare that path with ordinary longest-prefix cache reuse and
   checkpoint restore. This can identify a source-path inconsistency between cache identity,
   checkpoint state, and the segments recomputed after the 224-token prefix.
3. **Probability capture / serialization:** inspect `populate_token_probs` and request-result
   serialization in `tools/server/server-context.cpp` (around 2756, 2932–2949, 5630) and
   `tools/server/server-task.cpp` (around 402–406). Confirm both arms request the same pre/post-
   sampling probability mode and that the first row refers to the same generated-token position.
   Compare retained generation settings, row token IDs/order, and float values; this distinguishes
   capture/serialization discrepancies from a genuine difference in logits without treating
   matching generated IDs as proof of equal distributions.
4. **Focused existing coverage:** inspect tests in `tests/test-server-reorder.cpp` and any server cache/checkpoint tests present in this commit for
   the exact invariants already covered. `tests/test-server-task.cpp` is absent. Record coverage
   gaps; do not run tests or infer the smoke's cause from unexecuted test code.

Relevant pinned-commit paths are `tools/server/server-context.cpp`,
`tools/server/server-reorder.h`, `tools/server/server-schema.cpp`, `tools/server/server-task.h`,
`tools/server/server-task.cpp`, and `src/llama-context.cpp` (`output_reorder`). No model payload,
request body, response body, or raw private prompt content is included in this review.
