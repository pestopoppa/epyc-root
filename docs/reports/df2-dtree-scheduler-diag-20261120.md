# Batch-tree scheduler diagnostic, 2026-11-20

Row `ak-dtree-diag-gpu-20261120` completed rc=0. The registered rule defines PASS as diagnostic collection, without a CPU-fallback gate. Both final model records were collected; the existing owner verdict is PASS and df2 filing returned NOOP.

Both models produced empty scheduler split maps and empty CPU-node lists. These records do not establish zero CPU fallback: no GPU split was observed either, so scheduler coverage is unproven. CPU fallback remains UNKNOWN. The owner receipt attributes the missing trace to insufficient server logging and describes an r2 successor adding `-lv 5`; this report does not establish successor qualification.

A3B reported 19.401151 tok/s and 27B 29.036110 tok/s on one 24-token request each. These diagnostic values support no comparative speed verdict. P5 remains open pending full identity qualification and measured A/B. [belief: cc]

Evidence (original files, SHA-256):

- `/mnt/raid0/llm/tmp/ak-dtree-diag-gpu-20261120/out/results.jsonl`: `3782b472ff47f1322cae5c14300a64743f219f251eaf25403699fc36961be6ef`.
- `/mnt/raid0/llm/tmp/ak-dtree-diag-gpu-20261120/out/logs/dbg-a3b.log`: `ca33315f193b86c647a05e8a1a3f500c8c725d6e433b6eeefb6cc5b6c53cf48c`.
- `/mnt/raid0/llm/tmp/ak-dtree-diag-gpu-20261120/out/logs/dbg-27b.log`: `0cc4d6f67179de715c573919c1e537f8c87969e8e04931e71cdcbd691deff274`.

## R2: scheduler coverage obtained

Row `ak-dtree-diag-gpu-20261120-r2` ended rc=0 at 04:11:23Z. Its diagnostic collection rule is PASS: both final model records exist. The owner already filed PASS and FILED; df2 filing returned NOOP.

With `GGML_SCHED_DEBUG=2` and server `-lv 5`, A3B recorded 68 ROCm0 scheduler splits and 27B recorded 65; both CPU-node lists were empty. No CPU split was recorded. This resolves the earlier UNKNOWN for these observed requests: the scheduler trace shows GPU placement throughout its recorded splits. This is one 24-token greedy request per model using the frozen experimental `dd26275d63168e29ee850c3b0ef72339997baf1b` server; it establishes no universal claim about other workloads or CPU-side host work. [belief: cc]

The diagnostic reports 20.737441 tok/s for A3B and 22.151420 tok/s for 27B. Logging was enabled and there was no paired control, so these are not comparative performance results. The owner proposes graph-reuse loss from varying tree width and identifies build row `ak-dtree-build-gpu-20261120-r3` as its test; the scheduler counts alone do not establish that cause. P5 remains open pending full identity qualification and measured A/B. [belief: cc]

R2 evidence (original files, SHA-256):

- `/mnt/raid0/llm/tmp/ak-dtree-diag-gpu-20261120-r2/out/results.jsonl`: `7d2a5ead40c5bff9c1e7cfc7bb0d24d0f2d8e91092978934233e37469db26994`.
- `/mnt/raid0/llm/tmp/ak-dtree-diag-gpu-20261120-r2/out/logs/dbg-a3b.log`: `4ff2064f16d5d1a1f8c734ee3714bb56e41ce3bc604375a97b1cbc78bdcf4315`.
- `/mnt/raid0/llm/tmp/ak-dtree-diag-gpu-20261120-r2/out/logs/dbg-27b.log`: `481b90b7b3e906e9d38ee7d511c9d0acc849d2e930018824576b29cb9cb41319`.

## R3: constant-width build and server smoke

Row `ak-dtree-build-gpu-20261120-r3` ended rc=0 at 04:18:42Z. The R3 amendment selects experimental source `abda9a72c4709cc9d3d86112b1e39d1ab9e8ce82`, padding eligible batch-tree rounds to the column budget. Build and server-smoke verdict is PASS: the build record has rc=0, rebuilt server implementation, tree-reservation marker, tree-accept symbol and linkage rc=0; both models completed two 64-token tree requests with verified tree rounds. Owner PASS/FILED already existed when df2 filed; df2 returned NOOP and acknowledged the alert. [belief: cc]

27B text matched its chain control on 2/2 prompts; A3B matched on 0/2. Identity is recorded rather than gated by this smoke rule. P5 remains open pending full oracle qualification and measured A/B. The successful smoke does not waive A3B's mismatch. [belief: cc]

Recorded graph-reuse counts (two requests, tree versus chain) were 27B `[17, 26]` versus `[15, 24]`, and A3B `[24, 45]` versus `[26, 48]`. These are informational counts, not reuse rates or proof of a performance cause. Recorded tok/s was 27B `[32.607045, 46.948701]` versus `[32.176844, 63.208566]`, and A3B `[50.224953, 78.618767]` versus `[43.397098, 52.971713]`. This server smoke was not a timing-grade A/B experiment; no speedup verdict follows. [belief: cc]

Evidence: `/mnt/raid0/llm/tmp/ak-dtree-build-gpu-20261120-r3/out/results.jsonl`, SHA-256 `bb739e050c428fefada3bfec51985c29d4ef3f2b70fb04640400df2d32731b18`. The build record binds the artifacts to the source above: `llama-server` SHA-256 `02de65ccd76e4beb3387a7a2341e9017eae987b3e071975abcdb35076d54c7d1`, `libllama-server-impl.so` `efb1417a3ea0cfc2aafb3f851573e472d07e72407a6d49d8e817f56361485849`, `libllama.so.0.0.10613` `d9b416a842ddd3a614b94c268e6f23b58e694c61592eb67eeb6258a095f72121`, and `libggml-hip.so.0.16.0` `3b243ee959e627fb8715f5c67ad838c23a81eb579dba137b77f1866d31b4e690`.

## R4: HIP alias-fix build and server smoke

Row `ak-dtree-build-gpu-20261120-r4` completed rc=0 at 09:33:15Z. Applying the predeclared R4 amendment gives **PASS**: the final build record identifies experimental source `47f08e797c3dca352ebd6f7c5f80260d1e48aa90`, reports the matching version commit, rebuilt server implementation, reservation marker, tree-accept symbol, and linkage rc=0. Its HIP library differs from R3, as required. This is the R4 build/smoke gate only. [belief: cc]

Both 27B and A3B completed two 64-token tree requests with verified tree rounds. Each model matched its chain control on 2/2 prompts. Identity was recorded rather than gated by this rule; these four requests do not replace full oracle qualification. Graph-reuse counts and throughput remain informational. P5 stays open pending full qualification and the measured A/B. No comparative speed or alias-fix causal finding follows from this smoke. [belief: cc]

Df2 filed PASS with `file_result.py --no-reclaim`, which created the filing receipt; alert `246658bb188c1080360c4bf4` was acknowledged. The parent P5 checkbox remains open because this row did not execute its timing protocol.

Evidence: original `/mnt/raid0/llm/tmp/ak-dtree-build-gpu-20261120-r4/out/results.jsonl`, SHA-256 `670a2dab8dc897f311cc4effe50df25ed87b3cb9f070349ade21edd5d3bef759`. Recorded artifacts: `llama-server` SHA-256 `282b53f5db8670a27a39c4de9ef1ee70c5faed07e826777a6f568cb644a6f32c`; `libllama-server-impl.so` `efb1417a3ea0cfc2aafb3f851573e472d07e72407a6d49d8e817f56361485849`; `libllama.so.0.0.10614` `d9b416a842ddd3a614b94c268e6f23b58e694c61592eb67eeb6258a095f72121`; `libggml-hip.so.0.16.0` `e5535fc3dbde65a6bec841c8c54801954648211624f67b467d40c21dc413d013` (R3: `3b243ee959e627fb8715f5c67ad838c23a81eb579dba137b77f1866d31b4e690`).
