CAFE-4 corrected-reference native CPU controls
===============================================

This row reuses the runner and parser from [the original CPU diagnostic](../cafe4-native/README.md), with only row/scratch paths and the qualified corrected CPU R2 build bindings changed. Runtime logic and stop-on-first-failure behavior are unchanged. It runs width2 normal/fault then width3 normal/fault with `-ngl 0`; normal requires rc0 PASS, explicit fault requires rc1 and the intended fault witness. The fixed numerical gate is **0.743863867** (lower error is better); the reference floor is separate. No threshold search or relaxation.

Inputs are prepared once before publication. `inputs.json` binds executable SHA-256 `b3776b70ee6a6736ed08aac9cb379de427b0574f3373ab9c304dd5e80d3cc764`, corrected candidate SHA-256 `41fc473a908b7c385d79d1941b6576cc993b985e691682d6598d6122e968fe1c`, five local libraries, runtime files and the original content-verified model receipt with unchanged full stat. Native execution checks model stat only. No source trees, binaries, logs or weights are copied.

Publisher smoke must witness actual native model and all five local library mappings, then clean STOP; it does not establish rollback correctness. Scheduled execution binds the official grant and retains per-case logs, numeric controls, mappings, cutoffs and child-reaped status. One fixed prompt with diagnostic partial acceptance, no sampling or performance claim. Stop after four valid cases or first missing/failed native control, STOP or deadline. Parent CAFE-4 remains open for native results and GPU controls. Existing prospective CAFE-4 source registration applies; producer not belief-wired.

Result: `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-cpu-r2-20261119/RESULT.json`.
[no-belief: native diagnostic qualification only; no rollback verdict]

Publication smoke PASS (2026-11-19), cores 116–119, clean STOP rc75 at 07:27:19Z. Receipt `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-native-cpu-r2-20261119/PASS.json`, SHA-256 `778ad6a050118ea0f40cd75bd9af9ef787b0959ff24f9496dd37dd292ece9c7d`. Scheduled rollback/fault verdict remains pending.


Failed-control evidence retention (2026-11-19)
---------------------------------------------

The original width2 CPU R2 case printed off/observe cold-reference errors
**0.907920361**, equal to its printed reference floor and above the fixed
**0.743863867** gate; off/observe difference was zero. Fault error was
18.5714054 and fault/observe difference 18.6988792. These printed differences
supply no explicit rc1 fault-control verdict. The original rc2 UNKNOWN remains;
the equal reference floor does not identify the numerical root cause or prove
rollback correctness. No rerun or threshold change was performed.

The runner previously returned `controls=null` before parsing any measurements
when the child exited rc2. The repository runner now writes a separate
`diagnostics` field into each case, preserving finite measurements, individual
failed predicates and native UNKNOWN/stage/control/reference messages even on
failed or interrupted cases. `controls`, mapping/cutoff requirements, stop after
the first failed case, and overall PASS/UNKNOWN logic are unchanged. Diagnostics
never qualify a result. Duplicate/malformed/nonfinite numeric markers remain
unusable and JSON-safe. Six focused tests (including a simulated scheduled rc2
child with persisted terminal receipt) and all five existing control tests run
against the modified runner **PASS (11/11)**. No native inference ran.

Only repository source changed. Historical pinned scratch runner, inputs,
original RESULT and logs remain immutable. A future row must bind the new
runtime digest and pass publication smoke; no existing row is redeployed.
Port this retention to the next HIP runner while using the qualified R5
failure-attribution build under the unchanged gate. Prospective source tracking
remains `VB-SERVING-DF2` / `VB-CAFE4-ROLLBACK-WIRE`; no new producer or warrant.

Evidence (in place, no copied log or binary):

- Original RESULT: `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-cpu-r2-20261119/RESULT.json`, SHA-256 `fc547d719c23e1d9c2cb8d9f4ac72fe1784c93497604a3c615ec5a44a95b3dc6`.
- Original width2 log: `runs/d456c48d8e2d4b2fae82d060c2b20ad7/width-2-fault-0.log` relative to that RESULT's directory, SHA-256 `fd799fc9335b25c8dab7b2a532d88c7b38a945212e70a6b2b625afbf2970af77`; numerical/failure lines 3428–3430.
- Modified repo `scripts/diagnostics/cafe4-native-r2/runtime.py`, SHA-256 `9b730f207305b9069b1bd231098ea7496743d107b9014e530b085671d5bb1351`.
- Regression `scripts/diagnostics/cafe4-native-r2/test_runtime.py`, SHA-256 `575b54ecc624d01f78b284602d37e11d3cc3309a57d5d4b7cd3bf6e9e341ccca`.

[no-belief: model-free harness repair; original native UNKNOWN unchanged]
