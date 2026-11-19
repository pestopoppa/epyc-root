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

Scheduled build verdict (2026-11-19)
------------------------------------

`df2-cafe4-modes-cpu-build-r2-20261119` **PASS**, scheduled rc0,
07:10:36–07:11:21Z. The existing `driver.validate` accepted the complete
receipt: pinned source and patch, exact corrected source/header input hashes,
all artifact hashes, six compiled markers and five local llama/ggml linkages.
Executable SHA-256:
`b3776b70ee6a6736ed08aac9cb379de427b0574f3373ab9c304dd5e80d3cc764`.
Existing result: `/mnt/raid0/llm/tmp/df2/cafe4-modes-cpu-r2-20261119/RESULT.json`,
SHA-256 `18d72d8892a86d83635f7ebb6886aa63561a6f35323ead33801f446871ff6a30`.
End record: `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe4-modes-cpu-build-r2-20261119.ended`,
SHA-256 `bfc495c77f3d9cfb473538afff14ac628705446a664c4468a240e8302ebe395a`.
`file_result.py` recorded PASS and wrote the FILED receipt. Build-only verdict;
native rollback, GPU residency, fault sensitivity and performance remain unqualified.
The frozen native error gate **0.743863867** was not evaluated or changed.
CAFE-4 remains open. Next publish corrected-source native CPU controls bound to
this executable; corrected HIP R4 is already qualified-armed.
[no-belief: build qualification only; no native numerical measurement]
