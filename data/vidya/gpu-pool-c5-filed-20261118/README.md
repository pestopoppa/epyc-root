# C5 elementwise support on MI210

The allocator completed `ni-gpu-pool-elementwise-20261118-v5` at 20:35:09 UTC on 2026-11-18. At seed `2026102603`, pinned C5 reported all 17 selected target descriptions as `not supported [ROCm0]`. Each of the three original supported controls passed. The run used model-free synthetic tensors on MI210 ROCm0 with CPU affinity 184–191. [Native result](native/RESULT.json) · [Allocator terminal receipt](grant.ended) · [Filed verdict](verdict.json)

| Operator | Target pass | Target unsupported | Target failure | Control pass | Qualified residency samples |
| --- | ---: | ---: | ---: | ---: | ---: |
| NORM | 0 | 10 | 0 | 1/1 | 14 |
| SUM | 0 | 1 | 0 | 1/1 | 13 |
| SUM_ROWS | 0 | 6 | 0 | 1/1 | 14 |
| Total | 0 | 17 | 0 | 3/3 | 41 |

The 20 observed cases cover every planned description. NORM targets were noncontiguous F32 rows at widths 64 and 1025 with five epsilon values. SUM targeted the F32 `[33,256,1,1]` permutation `[1,0,2,3]`. SUM_ROWS targeted F32 widths 11 and 16, each with the three nonbaseline permutation/slice combinations. The log bytes match the digests in the terminal receipts, which retain the same-PID in-window KFD, positive-VRAM, pinned-map and affinity samples. [Target descriptions](case-plan.tsv) · [Control descriptions](control-plan.tsv)

Strict ingest projected three `Judged/Located` observations with zero refusals and emitted nine frames. An identical retry emitted zero frames. The native planning replay validated the current reader checkout and returned one observation for each exact candidate/operator/run request. Five mutated selectors and the missing-operator selector returned zero. Both ordinary model planner contexts returned zero and rejected reliance on all three observations. The replay receipt records `native_planning_context=true`. [Planning replay](planning-replay.json)

Scope is the exact 17 single-seed target descriptions on pinned C5, with source commit `c72ec82f5417bb2937310326120f149b665e8400` and candidate digest `a682063facc6aec523c4e2383e4726958aa0c5bc16142581545e26ab0d7bccb6`. The historical 544 c463 unsupported observations span 32 seeds and fall outside this comparison. The removed C5 build worktree's dirty state is unknown, and the recreated shim source differs from the original source digest receipt. The observation grade supplies artifact-specific support dispositions only. Performance, production consumer adoption, promotion and RVP-C2-2 are outside scope. [Sealed capture](native/belief.json) · [Build provenance](../gpu-pool-c5-elementwise-20261118/packet/source/PROVENANCE.md)

The retained originals preserve their run-time paths. The producer pins retain the original artifact digests. Verify the retained packet files from this directory with `sha256sum -c SHA256SUMS`. [Producer pins](PINNED.sha256) · [Packet byte digests](SHA256SUMS)
