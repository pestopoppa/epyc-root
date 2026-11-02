# Autokernel quantize reciprocal candidate provenance

Prepared: 2026-11-02
Status: extracted candidate patch only; no build, compute run, cherry-pick, or kernel-tree mutation.

## Source object

- Source repository: `/mnt/raid0/llm/llama.cpp-experimental` (read only)
- Commit: `9f85ba2fbe325e54a6dab607227f5a9ab4607250`
- Commit subject: `akc-discovery-4: c635f1702880b81d7ae462f82b7175d44b101daecd6f19afc7de9d854df32851`
- Commit timestamp: 2026-08-28 09:56:03 +0000
- Parent: `5c278648a4af2735587b4023613310ccf2341f46`
- Changed path: `ggml/src/ggml-cuda/quantize.cu`
- Change: compute reciprocal `id` in the first lane of each QK8_1 subgroup, broadcast it with `__shfl_sync`, and use `roundf(xi * id)`.
- Parent source SHA-256: `9f0074ec27a46a78c4c4709d00163acc35dae772854c290ba9592574d30bd3d9`
- Commit source SHA-256: `d1133dd84cfb27e1631dc838b6f03012dca2fb26580f1d2e18b87e0c1744269f`
- Parent/commit Git blob IDs: `af7fe105b6` / `b873ec480e`
- Patch file SHA-256: `7ec6bfc98a4e907c05d474a8009739ebad4ecaedcbf8cee8f63df042349cc600`

## Kernel lineage and intended application

This is a historical experimental change from the v9-era line, not a patch against the current production tip. The current production tree is `/mnt/raid0/llm/llama.cpp`, branch `production-consolidated-v10`, commit `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`. The v9 rollback anchor is `0db32c06e3e550065b78311a6031ef3dd2c4f27c`; the experimental checkout itself is at that v9 commit and has unrelated local modifications. The source commit is a separate historical commit object whose parent is listed above.

Intended next use: apply this patch as a candidate change on a fresh experimental branch created from the current production v10 tip, then build and validate the complete candidate against production before any promotion decision. Do not apply it to or build the frozen production tree. This artifact does not claim the change is correct, compatible with v10, or performance-positive.

## Verification and boundaries

- `git diff --check <parent> <source-commit> -- ggml/src/ggml-cuda/quantize.cu`: passed.
- Source hashes above were computed from the parent and commit Git objects, not from the experimental checkout's locally modified file.
- No production or experimental files were changed. No build or compute workload was run.
