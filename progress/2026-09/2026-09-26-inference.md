# 2026-09-26 — EXL3 throughput research closure and Stage 4 integration

## Goal

Close the EXL3/SGLang throughput research wave and turn the verified material into a focused implementation path for native EPYC and MI210/gfx90a kernels. The operator requires useful serving throughput comparable in workload terms to the published NVIDIA deployments and explicitly authorizes project-owned custom kernels.

## Work completed

| Area | Durable result |
|---|---|
| Research closure | Resolved the final 27-source wave and closed the full 88-record follow-up corpus. No reviewed source supplied CPU, HIP, ROCm, gfx90a, or MI210 EXL3 compute code or measurements; broad expansion is stopped unless a source changes the ABI, correctness path, matched gate evidence, or supplies an actual local-hardware implementation. |
| Corrections | Separated EXL3 codec claims from expert-pruning effects; treated W4A16/NVFP4 as distinct deployment alternatives requiring matched teacher, architecture, module coverage, expert plan, tokenizer, runtime, KV precision, and evaluation panel. External NVIDIA throughput remains a workload target and attribution input rather than a local CPU/MI210 threshold. |
| Kernel contract | Filed projection-major native-packed tensors, per-logical-matrix metadata, independent MCG/MUL1 reconstruction oracles, a real K4/MCG fixture, synthetic K1–K8 fixtures, caller-owned persistent scratch, allocation-free `plan`/`bind`/`run`, fail-closed metadata/capacity checks, and a wave64-native gfx90a path. |
| Measurement contract | Filed separate reconstruction, GEMV/GEMM, layer, bare-target, and speculative-serving arms; mandatory c1/c8/c16 decode, declared prefill, route-distribution, memory/capacity, recurrent-state, absolute-reference, and same-box candidate/control measurements. |
| Stage 3 | Produced and received approval for `research/intake-stage3-plan-2026-09-25-exl3-throughput-followup.md`, retaining the existing `INF-80` and DFlash2 owners with no new handoff or index row. |
| Stage 4 | Integrated 86 records and retained `intake-1773`/`intake-1774` as trigger-gated LiLiCorr monitors. Added EXL3-R7–R11, tightened EXL3-1/3/5/7/9/10, and added `DF2-EXL3`, gated on codec-only CPU/HIP success. |

Research and integration commits before this wrap-up sync: `24d5547c`, `689b7b8c`, `1fd4f35e`, `59303e1e`, and `0bb2e96b`. The branch was then synchronized with current `origin/main` by merge commit `c3e5d40a`, preserving both concurrent September 25 progress sections and regenerating shared state from the combined handoffs.

## Verification

- Both intake validators passed with 1,778 entries.
- Semantic comparison against the pre-Stage-4 index found changes only in the three approved disposition fields for the intended 88 records: 86 `integrated`, two `monitor`.
- Changed-handoff citation checking passed: 107 citations, zero problems.
- Handoff state generation and `index_state.py --check` passed with zero problems; the wrap-up pruning screen returned zero candidates.
- Checkbox sync: five completed findings added (`EXL3-R7` through `EXL3-R11`); `EXL3-1` through `EXL3-10` and `DF2-EXL3` correctly remain open.
- Production verification passed at `production-consolidated-v10` commit `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`; CPU and HIP server version 10303 and kernel-store linkage were intact. No production kernel tree, binary, store target, launcher, or serving lineup was modified.
- The repository-wide citation sweep still reports two pre-existing overturned citations (`intake-1519`, `intake-1524`) in `docs/research-intake/p-kld-annex-proposals-20260923.md`; neither the document nor those records was changed by this EXL3 session.

## Next action

Execute `INF-80` task `EXL3-1`: freeze the content-addressed packed artifact and metadata contract, implement independent scalar MCG/MUL1 reconstruction, pin the real and synthetic fixtures, and land the prospective measurement/verifier writers before the first correctness or performance run. CPU and gfx90a implementation then fork from that shared oracle.

## Implementation session closure

The approved non-inference work is now implemented and promoted. `EXL3-1`, `EXL3-2`, and `VB-EXL3-CPU-GFX90A` are complete. The research repository contains the portable artifact/oracle, standalone EPYC operators, gfx90a decode and MFMA paths, mixed-K MoE dispatch, owner-run authority checks, and source-bound exact-target build evidence. The root repository contains the registered Vidya projections and the updated handoff/index state. Production kernels and serving paths were not modified.

| Qualification surface | Result |
|---|---|
| Portable contract | 17 tests passed |
| EPYC normal and sanitizer suites | 719,096 checks passed in each run |
| Vidya adapter/dispatcher | 44 tests passed; 78 native rows projected to 234 frames with zero refusals or declines |
| gfx90a host/static | 5,579 assertions passed across 5,120 dispatch cells; three real fixtures reproduced 384 canonical outputs each |
| Exact-target code object | SHA-256 `7dc947dcbaa055fbac49a19f606038229289ab99f721db0e76936136be676a71` |

The only remaining gates in this implementation wave are `G3`, `G4`, and `G5`: MI210 device correctness, MFMA regime measurements, and mixed-K routing/capacity measurements. They require a safe device window because the owner launcher correctly refuses foreign KFD occupancy; the review census observed about 67.16 GB allocated. No GPU execution or full-model inference was claimed. At the next safe drain boundary, run the owner-authorized correctness pass, followed by the separate MFMA and routing microbench observations.

The operator-invoked wrap-up found zero handoff prune candidates and no EXL3 compaction need: the active handoff's first screen still states the current objective and open device gates. README freshness checks emitted no warnings. Four changed EXL3 sources were compiled into `wiki/quantization.md`, and the wiki source watermark was advanced only after lint and manifest-policy checks.
