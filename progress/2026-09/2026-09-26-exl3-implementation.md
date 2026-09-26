# 2026-09-26 — EXL3 standalone CPU and gfx90a implementation

## Goal

Implement every `INF-80` task that can be completed without model inference or a production-kernel change. Work was delegated by component; the owning session reviewed and integrated the submitted commits in isolated worktrees. The frozen `production-consolidated-v10` tree, kernel store, launchers, and serving lineup were not modified.

## Delivered

| Area | Result |
|---|---|
| EXL3 artifact and oracle (`EXL3-1`) | Research `bc9ac47b` defines the closed content-addressed `epyc.exl3.artifact.v1` contract, independent MUL1 and MCG scalar decode, explicit normalized-H128 reconstruction, GEMV/GEMM references, synthetic K1–K8 fixtures, three revision-pinned real fixtures, backend-repack binding, and native measurement/verifier writers. Root `6b8f9e85` adds strict projection and registered CLI discovery. |
| EPYC operators (`EXL3-2`) | Research `0e683fc0` adds scalar dense/indexed operators, native and band8 layouts, AVX512BW/VNNI/VBMI MUL1, an independent vector MCG path, K1–K8 and rows 1–4 coverage, tails/padding/guards, preflight refusal before output writes, real-fixture binding, and provider-backed materialize-then-GEMM prefill. Research `e6dc43b9` adds payload-bound claimed timing evidence. |
| gfx90a decode (`EXL3-3`) | Research `9e4fa162` adds exact ROCm 6.2 `gfx90a:xnack-:sramecc+` builds, wave64 packed GEMV, K1–K8 specializations, real-fixture transports, and a claimed-run verifier. Research `b02b1889` adds the explicit Inference Main owner-run authority path without weakening delegated provider/lease checks; `48253e78` refreshes the source-bound exact-target build receipt. |
| gfx90a prefill (`EXL3-4`) | The same commit adds a separate FP16-input/FP32-accumulating 16×16×16 MFMA path. Disassembly contains the intended MFMA instructions; device correctness and regime measurements remain open. |
| Mixed-K MoE (`EXL3-5`) | The same commit adds the unified/grouped capability table, named fallbacks, 256-expert and E+1 sentinel separation, plan/bind/run over a fixed caller arena, strict runtime identity, deterministic and separately labeled atomic gather, and route/capacity/capture refusal paths. |
| Evidence substrate | `epyc.exl3.measurement.v1` and `epyc.exl3.verifier.v1` are live. The writer SHA-256 is `8caeb33dbb12986fadc385afe25d22bd791b036253c736f9527e67a55f85e268`; both source classes use the existing `ClaimTuple` grader and carry no production or promotion authority. |

## Review and verification

- Portable contract suite: 17 tests passed.
- Root adapter/dispatcher: 44 tests passed; the actual dispatcher projected 78 native rows into 234 frames with zero refusals or declines.
- CPU normal and ASan/UBSan qualification: 719,096 checks passed in each run. Main independently repeated the normal suite and saw the same 719,096 checks.
- CPU grouped-K versus runtime-K comparison: a q3/CPU95 claimed synthetic mixed-K1–K8 run emitted eight measurement rows and one verifier row. Median differences ranged from 0.33% to 5.98% by ISA in this fixed-order, cache-resident sample; no default winner was asserted. The rows are protocol-ineligible observations and have no promotion authority. The run released its own q3 claim; AutoKernel later reacquired the region.
- gfx90a host/static qualification: main independently ran the refreshed exact-target build and passed 5,579 assertions across all 5,120 dispatch truth-table cells. The current code object SHA-256 is `7dc947dcbaa055fbac49a19f606038229289ab99f721db0e76936136be676a71`; all three real fixtures reproduced 384 canonical outputs each, and all 11 source hashes match the committed build receipt.
- No full-model inference ran. No GPU kernel execution was represented by compilation or host checks.

## Remaining hardware gate

`G3`, `G4`, and `G5` remain open for MI210 execution. Delegated GPU execution still requires an enabled qualified provider and ACTIVE lease. The explicit Inference Main owner path validates the canonical roster and role policy, records `lease=null`, and then uses the existing cross-process `gpu_device_claim`; 13 authority/refusal tests and an independent main preflight pass. A read-only KFD census during review found live serving processes and about 67.16 GB allocated, so the conservative no-co-residency launcher correctly refused execution. The next action is an owner-run correctness pass at a safe drain boundary, followed by the separate MFMA and routing microbench observations. Build provenance is current and ready for that window.
