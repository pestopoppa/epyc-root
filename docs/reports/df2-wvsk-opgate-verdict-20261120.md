# WVSK op-level correctness verdict, 2026-11-20

Row `ak-wvsk-opgate-gpu-20261119` completed rc 0. Its declared rule yields
**NO_WVSK_BUG**: all 15 n=2..16 cases passed in each of D (default), X
(`GGML_HIP_Q8_WVSK_MAX=16`) and C (`GGML_HIP_Q8_WVSK=0`), for **45/45
passing cases**. D and X record the WVSK path witness; C does not. Per-arm
reported wall times were 3.3 / 2.2 / 2.3 seconds; these are descriptive execution
times, not a comparative performance claim.

The op is Q8_0 × F32 MUL_MAT, m=6144, k=5120, n=2..16, bs/nr=1,
ROCm0 against the CPU reference. The test's native NMSE gate decides each
Boolean; captured numeric NMSE fields are null, so no numerical error bound
beyond the native pass is asserted. In particular, M=9..11 passed in both
WVSK arms. Stop-on-answer is met and the declared WVSK_BUG repair branch is
not triggered. No additional compute or replacement row is needed for this test.
This result is bounded to the tested cases and does not prove all served-model
workloads correct. The handoff separately records the H15 aliasing diagnosis;
this op-level verdict alone does not establish that separate causal claim.

Original retained evidence (no copies):

- `/mnt/raid0/llm/tmp/ak-wvsk-opgate-gpu-20261119/out/RESULT.json`, SHA-256
  `52832068634babad8f9de07efcff5a14d456bf6e5538c48b1c6aba839c71883a`.
- `/mnt/raid0/llm/tmp/ak-wvsk-opgate-gpu-20261119/out/results.jsonl`, SHA-256
  `330ae6de1a40f5b0c0c1f721e534d232cbe517fa00bb07c79122954872a2715b`.
- The existing `filing-done/ak-wvsk-opgate-gpu-20261119.FILED` receipt records
  PASS/rc0. This turn consumes that filing without duplicating it; alert
  `83155aa235c49ec6017281f8` is acknowledged.

This committed conclusion is an observation (`belief: cc`), with no invented
historical measurement warrant. Prospective producer wiring is tracked as
VB-WVSK-OPGATE-WIRE in the belief substrate handoff/source table; no adapter or
planning-context canary is claimed here.
