# Native Qwen3.8-27B D-LSA checkpoint — 2026-11-04

The scoped critical path is complete: fresh index, disabled graph integration, CPU/HIP correctness, then one successful native 27B sentinel. The broader LSA-SCREEN-1 acceptance remains open.

Candidate source: `088a77bd6ce5fac1ad3bf397912d884ae62b909e`, experimental C5-derived branch `experimental/lsa-native-c5-20261103`. Frozen production was not modified or used. Build and actual server/library digests are preserved in `build-receipt.json` and `approved-build.json`.

The 5,132-token no-thinking PCA request returned exact gold `92-8-E75FB6` in 10 output tokens. The request trace has 208 layer events, contiguous coverage of 5,141 positions (prompt plus nine decode inputs), native K/V pruning across all sixteen global layers and zero fallbacks. Own-PID KFD/VRAM was sampled during the request; the server was stopped and verified dead. The canonical keeper qualification completed the sole attempt; its real device flock and CPU affinity were witnessed, but it held no GPU-quiet region claim.

Native prompt/generation timings were 91.190734/3.100468 seconds. Client first token/request times were 91.196214259/94.296875612 seconds. These are descriptive, tracing-enabled observations. No matched speedup, broad quality or promotion claim is made, and no dense GPU baseline was repeated. Derived trace counts show only about 1.03% of prefill K/V row visits removed at this short length, and about 10.22% during decode; these counts do not predict end-to-end latency.

The port required matching pinned Torch CPU BF16 reduction order, supporting Qwen text M-RoPE, and matching the author's full-128 unstable Ward rank (including masked infinities). A prior full request returned gold but fell back; a stopped diagnostic identified `ambiguous_selection` at layer 3. The corrected CPU and fixed-size HIP sorts now pass the frozen author tied membership fixture, and the actual candidate passes CPU native/random/5K/PCA oracles plus HIP tied and 27B unit checks. Tolerances were not relaxed.

Files here are byte copies of original producer records and selected run artifacts. Embedded provenance paths deliberately retain the original host locations; receipt warrants were not rewritten. `native-ledger.jsonl` contains the native adapter's original failure and final pass projections, not promotion evidence. Inputs, map/model digests and producer sources are bound by `plan.json`, `native.manifest` and `approved-build.json`. Original run banks remain under `/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/`.

No additional inference is queued for this scoped goal. The full six-control quality/latency screen, held-out checks and candidate activation are not established by this single case.
