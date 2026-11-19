CAFE-4 corrected-reference CPU build qualification
==================================================

Row `df2-cafe4-modes-cpu-build-r2-20261119` compiles corrected generator
output SHA-256 `41fc473a908b7c385d79d1941b6576cc993b985e691682d6598d6122e968fe1c`.
The generator correction is committed in epyc-root `d3cc84653989faa3e0257d985e8db0d2a34989db`;
see [decode-boundary rationale](../CAFE4.md#cold-reference-decode-boundary-correction-2026-11-19).
The fixed error gate remains **0.743863867**, lower error is better.
This build does not evaluate that gate or establish native rollback correctness.

The launcher/driver retain the original [CPU build qualification](../cafe4-build/README.md)
with a separate row id and scratch directory:
`/mnt/raid0/llm/tmp/df2/cafe4-modes-cpu-r2-20261119`.
Inputs are prepared before publication and individually hash-bound in `inputs.json`.
The detached experimental source remains pinned to v10
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115` and diagnostic patch SHA-256
`351a431702613a5cad8d165c6959dbcde12a928963b8833bfa4668abb743e4dd`.
The production source and previous build outputs are unchanged.

Smoke requires a fresh compiled object with all six load/rollback/rewind,
verify-batch and fault-control markers. Scheduled execution requires the full
executable, artifact hashes and all five llama/ggml libraries resolving locally.
Stop on source mismatch, compilation/linkage failure, deadline or STOP; stop on
answer when the full build receipt validates. No model is loaded by this row.
The HIP R3 row contains the original source and cannot qualify this correction.

Next: file the scheduled CPU build verdict, prepare a corrected-source HIP build,
then publish native width2/3 normal and explicit-fault controls under the fixed gate.
[no-belief: build qualification only; no native numerical measurement]

Publication (2026-11-19)
------------------------

Publisher four-CPU compiled-object smoke **PASS** on cores 116–119, clean
STOP rc75 at 06:49:22Z. Receipt: `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-cpu-build-r2-20261119/PASS.json`; SHA-256 `022bcfea4651e5f9dc8dc5121c89cca5c5f4a0224d186f0e05e7ca4d4e27bb0c`.
Full build remains scheduled. The environment warning is a static false positive:
`dict(os.environ, LD_LIBRARY_PATH=...)` preserves `FILLER_ID`.
