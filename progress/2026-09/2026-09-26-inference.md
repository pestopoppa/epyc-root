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
