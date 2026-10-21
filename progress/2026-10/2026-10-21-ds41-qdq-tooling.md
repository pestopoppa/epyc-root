# 2026-10-21 ds41-qdq-tooling (workspace-58 subagent)

Non-inference tooling for the queued DS41-1017 items DS41-W5.1a, DS41-T3.2 and DS41-T7.1a. Code only: nothing has been built or run yet. Builds and runs go through the shared compute queue.

## llama.cpp branch

`experimental/ds41-qdq-flag-20261021`. It starts from champion `dd3d9721c`, lives in the worktree `/mnt/raid0/llm/worktrees/llama-ds41-qdq-flag-20261021`, and is pushed to `fork`. There is one feature per commit (OP-58):

- `ac496d6f3`: the QDQ graph op and its test.
  - `src/llama-qdq.{h,cpp}` provides `llama_build_qdq`, built on `ggml_map_custom1`. It adds no new ggml op and runs on CPU only.
  - It has three modes, copied bit for bit from the 1017 `inference/kernel.py` act_quant/fp4_quant (inplace): FP8 e4m3 ue8m0/32, FP4 e2m1 ue8m0/32, and FP4 e2m1 + e4m3/16.
  - The commit also adds the `LLAMA_DSV41_QDQ` site parser. It aborts on an unknown token and logs the parsed set once.
  - `tests/test-dsv41-qdq.cpp` checks:
    - the element rounders against an enumerated-code oracle;
    - the blocks against an independent oracle;
    - hand goldens;
    - the graph op against the scalar reference at 1 and 7 threads, contiguous and permuted;
    - that NONE adds no node;
    - the parser.
- `c17db6af9`: DS41-W5.1a. `LLAMA_DSV41_QDQ=wo_a` applies the FP8 round trip of o before wo_a, in the main and DSpark attention.
- `156b3ea94`: DS41-T3.2 step (2). The sites are kv_win (main window KV, plus the DSpark ring and block KV), kv_comp, idx_k and idx_q; the alias `kv` sets all four. Every site sits before the Hadamard K rotation.
- `206f9ef34`: DS41-T7.1a. `common_speculative_process()` is now timed. A new INFO line, `draft timing <type>: draft = .. / process = ..`, prints at each slot release. It is default on because the cost is zero.

Every QDQ site is off by default. With all sites off, no node is added and the graph is byte-identical.

Validation so far: every touched TU passes `g++-15 -fsyntax-only` with the project warning flags and gives no new warnings. Nothing has been linked or run.

## Queue rows (`/mnt/raid0/llm/tmp/compute-flags/FILLERS.md`)

All four rows are REGISTERED but not armed. Scripts are in `/mnt/raid0/llm/tmp/ds41-qdq-20261021/`; each row uses the shared `grant_launcher.sh`.

| Row | Class | DS41-class | Ready | Content |
|---|---|---|---|---|
| `ds41-qdq-build-test` | block-correctness | n | y | Build, the new test, 5 DS41 regression tests, `strings` proofs, linkage check. test-backend-ops is omitted because on a CPU-only build it would pass vacuously. |
| `ds41-w51a-ab` | block-correctness | y | after build | Three arms on the W5 ppl recipe: off; champion vs off (KLD must be 0, which proves off matches the champion bit for bit); wo_a. |
| `ds41-t32-kvfq` | block-correctness | y | after build | Port-side sensitivity at ctx 2048, five arms. Labelled `kv_fakequant_port_sensitivity`. |
| `ds41-t71a-drafter-timing` | filler | y | after build | Drafter ms per step and its share of eval time, through `t71a_parse.py`. |

## Finding: no layer-truncated reference fixture for T3.2 step (1)

There is no layer-truncated reference fixture for T3.2 step (1). Three things are missing:

- **The 1017 weights.** No 1017 safetensors are on disk; the dive dir holds code and the index only. A fixture up to layer 3 needs 1017 shards 00002, 00003-00006, 00047 and 00043. The alternative is a dequant of the GGUF, labelled `dequantized_from_quant`.
- **A tilelang-free kernel.py shim.**
- **The DS41-T3 comparison harness itself.**

The handoff notes are under W5.1a, T3.2 and T7.1a in `handoffs/active/deepseek-v41-flash-evaluation.md`.
