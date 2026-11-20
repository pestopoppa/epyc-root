# AK-DTREE-2 r6: FAIL(crash 27b)

FAIL(crash 27b) under the prospective R5/R6 rule: ident-27b-p0 child rc=-11, launcher rc=0. The recorded failure is tests/test-dtree-batch.cpp:214, llama_memory_seq_rm(llama_get_memory(lin), 0, pos + 1, -1) returned false. No stack, oracle-rate counts, A3B result or timing. The width-control question remains unanswered; no kernel-cause attribution. P5 and AK-DTREE-2d remain open.

The completed build record pins source `58679f4647d554241c565aa8397aca73c21770fa` and test SHA-256 `2a76bbe365595182099900c3731024c15902f102b84d2d5dc84f4fd98803bebf`. The unit reports HIP mapped from the build, residency OK, peak KFD VRAM 41,782,329,344 bytes over 64 samples. This records the sampler result; its own_pid field is null, so it does not independently establish PID identity.

R6 kept the R5 thresholds and changed the control to decode seven columns from the committed root. Both-model coverage was required, but the runner stopped at the first failed unit. No numerical identity comparison can be made. A successor needs a valid recurrent-memory control lifecycle and both-model coverage; check owner activity before duplicating a repair or row.

Existing evidence (no copied payloads):

- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r6/out/results.jsonl` — SHA-256 `f803b7893e41c6f7816331006c87f25dc3e92741acde5a7e39bde4dd9c812922`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r6/out/RESULT.json` — SHA-256 `a1b0f0d7fcca64d434cc5b3d3b31fe14c7dc5029a7ac3441972a80a7f94fb3ef`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r6/SOURCE.sha256` — SHA-256 `1fcde230f3255dec526a6dc8613a335fb8ebbfd6891d56ab2cbe6cd06e97cb3f`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r6/BIN.sha256` — SHA-256 `9d230a67fcf058a4628743b72afaa8baf8ec003ca30452b552ca92d541a39e32`.

Filing reconciliation: file_result returned NOOP because the owner had already filed FAIL at 2026-11-20T02:37:42+00:00 against the identical native-result digest. Its answer attributes this to the check program and reports a fix plus a tiny-model CPU preflight for the successor. That attribution is the owner's statement, not independently demonstrated by this run. The delayed alert was acknowledged.
