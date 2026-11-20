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
