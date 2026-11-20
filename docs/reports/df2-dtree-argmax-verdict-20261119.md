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

## DTREE-A2 determinism-controlled rerun (2026-11-20)

Row `ak-dtree-a-argmax-gpu-20261119-r2` ended rc=0 with
**FAIL / FUTILITY_IDENTITY**, at pair 0. Zero-based prompt 0 has identical
L and L2 content hashes but a different X hash; prompt 2 matches all arms.
Prompt 1 differs between L and L2 and is excluded by the registered gate.
Thus one of two judged prompts fails identity despite the lowest-index tie
fix in candidate `bf39c2509`. The cause remains unproven; the control excludes
host-repeat variability as an explanation under this registered gate, but
does not isolate the underlying numerical or implementation mechanism.

Higher decode tok/s is better. L=50.448668, L2=50.411904,
X=51.152357; X/mean(L,L2)=1.014318 (+1.4318%).
The native summary reports X/L=1.014318;
this differs from the registered X/mean(L,L2) denominator above. Neither
ratio earns a speed verdict: n=1, no estimable paired 95% CI, identity
futility stops the run before the minimum five-pair answer checkpoint.
No KEEP_CANDIDATE or LOSS speed conclusion is supported.

All arms show own HIP mappings, own libraries and nonzero owned VRAM
(~37.74 GB) in beginning/end snapshots; these are not continuous residency
proof. Do not enable this candidate by default. Reuse the matched-prefix
logit/first-divergence diagnostic requirement from A1 before another repaired
candidate qualification. Existing VB-DTREE-A-WIRE covers prospective belief
projection; this report records a committed-conclusion observation.

Original evidence SHA-256 (files retained by row policy; no copied blobs):

- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261119-r2/out/RESULT.json`: `370033a0860823dbe674502e309154552be5e35e0faa97d6a1588dbbba011ca5`
- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261119-r2/out/results.jsonl`: `4e1e95c894404826a77f58d2d4a809c0efb3944f8f0d152523149286079db344`
- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261119-r2/job.py`: `5532199422cbcf02d6bb5ab1c2a516e20a130ac53d3a7648cdadf30c2bdac5fc`
- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261119-r2/SOURCE.sha256`: `13b8945682fa82dd0bb670608b48c06b13497ed3978767bc6d9c4188a45b01f4`
- `/mnt/raid0/llm/tmp/compute-flags/ready/ak-dtree-a-argmax-gpu-20261119-r2.json`: `c550a1a24a259b29fe701031c46e9aa0d8d8fd5a7363b08a3a4010b8ea009e7d`
