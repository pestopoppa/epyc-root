# DTREE-A1 device argmax identity verdict (2026-11-19)

Row `ak-dtree-a-argmax-gpu-20261119` ended rc0 and is filed **FAIL**:
the native result is `FUTILITY_IDENTITY` on pair 0. X and L disagree on
prompt 1 and match on prompts 2 and 3. The registered immediate identity
futility gate applies to this same-binary, same-width argmax comparison.
The oracle allowance for different tree widths does not replace this gate.

Higher decode tokens/s is better. L measured 49.598709 tok/s and X 50.421098,
ratio 1.016581 (+1.6581%). This is one pair, with no estimable paired 95% CI;
it does not establish a speed gain beyond the 0.84% floor. No keep is earned.
Both beginning and ending captures in each arm show owned HIP libraries and
nonzero owned VRAM (~37.74 GB); these snapshots do not establish continuous
residency.

Prompt 1 content hashes differ: L `60e66db0bd91ac8666ef6172ca3ea5f988fd6c9b1f02485af4906b5991e6cd11`,
X `e01ba49df01664beceb63de8929b3552f941d3990ea8e29dda0f3f8635b1e8b2`.
The record names candidate `70f7d1c09`. The mismatch's cause is unproven:
this result alone cannot distinguish argmax logic from graph/numerical effects.
Do not enable this candidate by default or repeat its timing unchanged.
DTREE-A's wider builder/acceptance requirements remain open. Diagnosis needs
matched-prefix host/device logits and first divergent-token evidence before
a repaired candidate can be qualified. No production files change.

This is a committed-conclusion observation, not a newly graded measurement
claim. Prospective projection is tracked under VB-DTREE-A-WIRE with the shared grading contract.

## Original evidence SHA-256

- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261119/out/RESULT.json`: `6347201e8446a813a72cdfeb32515bb02c614f71441568a872035e3464d8cee2`
- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261119/out/results.jsonl`: `7d878a131b3ba0fbacee37501e5ee41cb32931ef1aef037e0e4f5a90d4e4b865`
- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261119/job.py`: `d18a3e959a773562deacc485178a4323b84d2d3d454e6583ab0c6029ef2b39ec`
- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261119/SOURCE.sha256`: `62050750701a8a19d7fab9913b35fbf08c47f935930ed717f99fb3bc2fbc70db`
- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261119/spec.json`: `8aa0e540b60190a6fe2f3ac8d483ad55df801b879e36c02f60bb28e74f0a0bfe`
- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261119/launch.sh`: `08f8376712e07c54995bf72d1b0de1b3a87aec7c86e5eb8cc011ffae5035545d`
- `/mnt/raid0/llm/tmp/compute-flags/ready/ak-dtree-a-argmax-gpu-20261119.json`: `5b7729ee3a5bd1c6652aa09e32d3cbdf3895f874e8c5adfa56364b75674f5175`
