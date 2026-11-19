# CAFE-3/CAFE-4 row verdicts — 2026-11-19

These are row-scoped outcomes. CAFE-3 P9 and CAFE-4 native rollback/fault qualification remain open. No serving kernel changed. Existing files are referenced by SHA-256; source trees, logs and binaries are not copied.

## df2-cafe3-full-cpu-build-20261119 — FAIL

Scheduled rc1; no RESULT.json. The build log reaches 100% Built target llama-server, but the supervised cmake build returns 75, caught as CAFE3 BUILD REFUSED. No validated full receipt, artifact identity or linkage qualification was produced. This fails build qualification, not evidence of a C++ compilation error; STOP/deadline/descendant-exit attribution remains unresolved.

Evidence (original files; availability follows the keeper retention policy):

- `/mnt/raid0/llm/tmp/df2/cafe3-cpu-build-20261119/runs/build-gfcy_3_0/build.log` — SHA-256 `373286ca6db3ed9e619f68f25b2df2a747f2e8c701aadd6608130b8a5ea9ea47`
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-full-cpu-build-20261119/state/df2-cafe3-full-cpu-build-20261119.fenced-job.out` — SHA-256 `b6e50e95fd3d98eeee40267f6e2d0c90477ef1cf99c07ad66e79b8e39c5cf028`
- `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe3-full-cpu-build-20261119.ended` — SHA-256 `0d8e08fd0248bdf4e36f558db2f7a8817cf079a80bd358564ea2449a2c0163b0`

## df2-cafe3-full-hip-build-20261119 — FAIL

Scheduled rc1; no RESULT.json. The build log reaches 100% Built target llama-server, but the supervised cmake build returns 75, caught as CAFE3 BUILD REFUSED. No validated full receipt, artifact identity, HIP/gfx90a/export or linkage qualification was produced. This fails qualification without establishing a compiler or HIP defect; supervisor exit attribution remains unresolved.

Evidence (original files; availability follows the keeper retention policy):

- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-20261119/runs/build-a_mq1ylo/build.log` — SHA-256 `2b4aa3c10766649ccc23dffa332a6b591fc568145fcfe5af46cb2e3a443b8ef4`
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-full-hip-build-20261119/state/df2-cafe3-full-hip-build-20261119.fenced-job.out` — SHA-256 `a3eac40fc2f5551f7d1701476dac4f48079fc78b6528d865bac5c7c1c37fda73`
- `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe3-full-hip-build-20261119.ended` — SHA-256 `0356e3d9015107327594f66f5bed7fc151d8756605616f6aefc9954fe18b4a1b`

## df2-cafe4-modes-hip-build-r5-20261119 — PASS

Scheduled rc0 complete. Retained R5 driver check returned rc0: exact v10/patch/generated-source bindings, full executable failure-attribution and rollback/verify/fault markers, hash-bound artifacts, local llama/ggml libraries, HIP gfx90a configuration/image and exact defined IQK/HIP exports validate. Build-only qualification; native rollback, GPU residency and performance remain unassessed.

Evidence (original files; availability follows the keeper retention policy):

- `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r5-20261119/RESULT.json` — SHA-256 `667dc2e6172db65e705f1084bd890e567615bfc97f4ea0aeda343c36d2359d75`
- `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe4-modes-hip-build-r5-20261119.ended` — SHA-256 `eb1383f5b0a908ada6c7c9bf55ac43c56f9329c669f09b71e243ae1d1df2c2d4`

## df2-cafe4-modes-native-cpu-r2-20261119 — INCONCLUSIVE

Scheduled rc2 UNKNOWN. Only width2 nonfault executed: native case rc2, controls null, mapping true, no cutoff, child reaped. Cold-reference error/floor 0.907920361 exceeds fixed lower-is-better tolerance 0.743863867; off/observe errors both 0.907920361, off_observe=0. Fault difference was printed but this was not the required explicit fault rc1 case. Three required cases unexecuted. Predeclared stop-on-first-failed-control applies; no threshold relaxation, CPU modes pass, GPU result or parent completion.

Evidence (original files; availability follows the keeper retention policy):

- `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-cpu-r2-20261119/RESULT.json` — SHA-256 `fc547d719c23e1d9c2cb8d9f4ac72fe1784c93497604a3c615ec5a44a95b3dc6`
- `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-cpu-r2-20261119/runs/d456c48d8e2d4b2fae82d060c2b20ad7/width-2-fault-0.log` — SHA-256 `fd799fc9335b25c8dab7b2a532d88c7b38a945212e70a6b2b625afbf2970af77`
- `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe4-modes-native-cpu-r2-20261119.ended` — SHA-256 `a40271a2c06a158a834749980b374dedb23d31407da08e78e5605eda3becf161`

## Next actions

CAFE-3: attribute the supervisor rc75 at the completed-build boundary, repair the qualified build path and publish replacement rows. Both logs reached the linked target; repeating the unchanged build is not justified. Preserve full source/build/library bindings and test marker checks against the actual linked component that carries the server implementation.

CAFE-4: use the already-qualified R5 failure-attribution candidate for a subsequent native diagnostic. The CPU R2 result predates those explicit failure labels; do not infer a rollback-specific defect from a failed cold-reference floor. Keep the original 0.743863867 gate. R5 HIP build qualification supplies no native GPU or rollback verdict.

[no-belief: build qualification outcomes and inconclusive native diagnostic; no performance or promotion claim]
