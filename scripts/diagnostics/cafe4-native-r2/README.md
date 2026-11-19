CAFE-4 corrected-reference native CPU controls
===============================================

This row reuses the runner and parser from [the original CPU diagnostic](../cafe4-native/README.md), with only row/scratch paths and the qualified corrected CPU R2 build bindings changed. Runtime logic and stop-on-first-failure behavior are unchanged. It runs width2 normal/fault then width3 normal/fault with `-ngl 0`; normal requires rc0 PASS, explicit fault requires rc1 and the intended fault witness. The fixed numerical gate is **0.743863867** (lower error is better); the reference floor is separate. No threshold search or relaxation.

Inputs are prepared once before publication. `inputs.json` binds executable SHA-256 `b3776b70ee6a6736ed08aac9cb379de427b0574f3373ab9c304dd5e80d3cc764`, corrected candidate SHA-256 `41fc473a908b7c385d79d1941b6576cc993b985e691682d6598d6122e968fe1c`, five local libraries, runtime files and the original content-verified model receipt with unchanged full stat. Native execution checks model stat only. No source trees, binaries, logs or weights are copied.

Publisher smoke must witness actual native model and all five local library mappings, then clean STOP; it does not establish rollback correctness. Scheduled execution binds the official grant and retains per-case logs, numeric controls, mappings, cutoffs and child-reaped status. One fixed prompt with diagnostic partial acceptance, no sampling or performance claim. Stop after four valid cases or first missing/failed native control, STOP or deadline. Parent CAFE-4 remains open for native results and GPU controls. Existing prospective CAFE-4 source registration applies; producer not belief-wired.

Result: `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-cpu-r2-20261119/RESULT.json`.
[no-belief: native diagnostic qualification only; no rollback verdict]

Publication smoke PASS (2026-11-19), cores 116–119, clean STOP rc75 at 07:27:19Z. Receipt `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-native-cpu-r2-20261119/PASS.json`, SHA-256 `778ad6a050118ea0f40cd75bd9af9ef787b0959ff24f9496dd37dd292ece9c7d`. Scheduled rollback/fault verdict remains pending.
