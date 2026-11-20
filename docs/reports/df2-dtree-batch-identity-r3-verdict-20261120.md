# DTREE batch identity r3 — 2026-11-20

Row `ak-dtree-batch-identity-gpu-20261119-r3` is **FAIL(oracle 27b)** under its preregistered first-match rule. Lower fresh-prefill oracle disagreement is better: tree **1/64 = 1.5625%**, linear chain **0/32 = 0%**, permitted excess **0.5 percentage points**. The measured excess is 1.5625 points, so the threshold fails. Both launcher and 27B identity child returned zero; process success does not pass the identity gate. `diverged=false` is a separate native field and does not override oracle disagreement.

Op comparisons on ROCm0 versus CPU passed **GATED_DELTA_NET 131/131** (24 tree cases) and **SSM_CONV 66/66** (21 tree cases). This completes AK-DTREE-2c's op gate for the pinned build; it does not complete AK-DTREE-2d's end-to-end graph/memory gate. A3B identity and performance timing were not reached because execution stopped at the failing 27B oracle gate. No speed or promotion conclusion follows.

The native records report pinned content proof and HIP residency. Op units contain owned PIDs, while the identity record reports `own_pid=null`; its residency summary cannot independently establish a specific identity-child PID. The failed numerical gate already prevents promotion regardless of that limitation.

The existing filing receipt discusses a near-tie and route-level numerical effects and proposes a larger successor. Those explanations are hypotheses beyond the aggregate result assessed here. The present record establishes disagreement and a failed predeclared gate; it does not isolate a kernel, graph, or numerical-route cause. A successor must retain this failure and declare its own sample-size/error rationale before execution; a larger denominator cannot retroactively pass this row.

The original row already had a FILED receipt; file_result.py returned NOOP, so no second filing or reclaim was attempted. Alert `686efd00cb83eef3e1246b35` was acknowledged. Parent AK-DTREE-2 and graph/memory child remain open; the CPU/HIP op child is completed from these results.

Evidence remains in place (SHA-256):

- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261119-r3/out/results.jsonl`: `91fa8c699c3491d6e10b7b9e6d2666370f7b7f949ecb96890c8fe7823cad4ad9`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261119-r3/out/RESULT.json`: `6302762da2db9e0ea76f24a0f9a6c99dacb5e41f1909393cf19f5f0f58c3b463`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261119-r3/BIN.sha256`: `6e4f160f0ed23497988619dcdbc8c0bc6426f0908686de2c50a17b1a151a7b26`.
- `/mnt/raid0/llm/tmp/compute-flags/filing-done/ak-dtree-batch-identity-gpu-20261119-r3.verdict.json`: `925cdfbdd03645b9b09324db4b00b587179b5fb94c53b7f5d280f80dea8a4753`.

This committed conclusion is an OBSERVATION, not a retrofitted measurement warrant. Prospective batch/op projection is tracked by VB-DTREE-BATCH-WIRE.
