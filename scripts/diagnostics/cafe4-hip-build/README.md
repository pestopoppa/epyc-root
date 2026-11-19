CAFE-4 modes HIP build row
=========================

Row `df2-cafe4-modes-hip-build-20261119` passed publish's four-CPU smoke
on 2026-11-19 (cores 116–119, compiled-object predicate, STOP rc75).
Receipt: `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-hip-build-20261119/PASS.json`; SHA-256 `7bfb12aadb4db5070aacbe9e708b732d08421db64438538e7c4659cbe0177400`.
The full HIP executable is not built by this smoke. Native GPU execution,
rollback, fault sensitivity and performance remain untested by this row.

The CPU-scheduled build enables HIP for gfx90a in a fresh run build directory
under `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-20261119`.
It uses the unchanged detached experimental checkout
`/mnt/raid0/llm/tmp/df2/cafe4-modes-source`, pinned v10 commit
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115` plus diagnostic patch
`351a431702613a5cad8d165c6959dbcde12a928963b8833bfa4668abb743e4dd`.
Production and the existing published CPU row are unchanged.

The [input manifest](inputs.json) binds the generated candidate, modes header,
bridge, supervisor and this driver. Source generation and provenance are in
[the CPU row](../cafe4-build/README.md). The full-build validator requires
compiled MTP load/rollback/rewind and verify-batch/fault markers, HIP enabled
and gfx90a in CMakeCache, a hash-bound libggml-hip with HIP registration symbol
and gfx90a image string, and all required llama/ggml libraries resolving locally.
The child environment retains FILLER_ID. These are build-content checks;
GPU residency must be measured during a separate native row.

Stop on a validated full receipt, or on source/input mismatch, build/linkage
failure, STOP or deadline. Result:
`/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-20261119/RESULT.json`.
Next: file each CPU/HIP full-build result when it lands, then schedule native
CPU/GPU rollback and explicit rc1 injected-fault controls. CAFE-4 stays open.
