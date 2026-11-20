# AK-DTREE-2 r7: FAIL(oracle 27b)

The registered R5/R7 rule fails on Qwen3.8-27B Q8_0: tree disagreement against fresh prefill exceeds the width-control rate by 0.811688 percentage points, above the 0.5-point bound. Lower disagreement is better. Launcher rc=0; all eight GPU identity units rc=0. This is a correctness-gate failure, not a crash or speed verdict. AK-DTREE-2d and P5 remain gated.

| Model | Tree vs oracle | Width control vs oracle | Tree excess (points) | Registered comparison |
|---|---:|---:|---:|---|
| Qwen3.8-27B Q8_0 | 7/440 = 1.590909% | 3/385 = 0.779221% | +0.811688 | FAIL |
| Qwen3.6-35B-A3B-MTP Q8_0 | 6/240 = 2.500000% | 8/210 = 3.809524% | -1.309524 | PASS |

The CPU Qwen3.5-0.8B Q8_0 precheck passed: tree 0/32, original chain 0/16, width control 0/28. The source build record pins fork `419d3addd03e9e9679663e7ba4858555d67b9d57` and test executable SHA-256 `4aa4d81224c46794bc5d6174c4afaac17b337bb0eecd0b3b008fd26543f5da80`. This successor puts the seven-column width control in the scratch context.

Reported splits: 27B main 4/220, side 3/220, original chain 3/220; A3B main 5/120, side 1/120, original chain 2/120. Every recorded tree margin is below the 0.5-nat hard-failure threshold. Those small margins do not establish a numerical-noise cause or prove the absence of a structural error. The existing owner receipt's statements that these are coin flips and that the tree computes the right thing go beyond what this run isolates; its FAIL verdict agrees with the registered rule.

Several prompts ended on incremental-reference divergence: 27B delivered 440/512 planned tree columns (55/64 rounds), A3B 240/512 (30/64 rounds). Both models and all four prompts ran, but full planned denominators were not attained. Apply the registered rule to observed denominators and retain the coverage limitation; do not treat this as a power analysis or a basis to relax the threshold. Timing was not reached. Ops were inherited from the earlier passing op gate, not rerun here.

Every GPU identity record reports HIP mapped from the build and residency OK during the unit. The sampler's own_pid field is null; this summary does not independently establish PID identity. No production kernel was changed.

Existing evidence (SHA-256; no copied payloads):

- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r7/out/results.jsonl` — `b60f24637dec20aba351f0b38a4eabac05fc28d69370bdd962049f5cdb818ede`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r7/out/RESULT.json` — `d420b5ed9e5910f2813a7a7ad7e75d5b67b99fb0b4b789b538fa3b3a9fa9216b`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r7/SOURCE.sha256` — `e5c2adcb1d34897661f1e803f82b9408b00a79b09ff910893a82ec1f1c97c742`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r7/BIN.sha256` — `9d230a67fcf058a4628743b72afaa8baf8ec003ca30452b552ca92d541a39e32`.
- `/mnt/raid0/llm/tmp/compute-flags/ready/ak-dtree-batch-identity-gpu-20261120-r7.json` — `e19cd80452ab0f122a775ab381ce3d762b15ecdc9910ab346e9e273bc3824459`.

Disposition: reconcile the existing FAIL receipt and acknowledge the run-end alert. Do not retry this failed lineage or publish P5 speed rows on these data. Resume the existing target-precision native-cell binding task next.
