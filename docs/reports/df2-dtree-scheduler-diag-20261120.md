# Batch-tree scheduler diagnostic, 2026-11-20

Row `ak-dtree-diag-gpu-20261120` completed rc=0. The registered rule defines PASS as diagnostic collection, without a CPU-fallback gate. Both final model records were collected; the existing owner verdict is PASS and df2 filing returned NOOP.

Both models produced empty scheduler split maps and empty CPU-node lists. These records do not establish zero CPU fallback: no GPU split was observed either, so scheduler coverage is unproven. CPU fallback remains UNKNOWN. The owner receipt attributes the missing trace to insufficient server logging and describes an r2 successor adding `-lv 5`; this report does not establish successor qualification.

A3B reported 19.401151 tok/s and 27B 29.036110 tok/s on one 24-token request each. These diagnostic values support no comparative speed verdict. P5 remains open pending full identity qualification and measured A/B. [belief: cc]

Evidence (original files, SHA-256):

- `/mnt/raid0/llm/tmp/ak-dtree-diag-gpu-20261120/out/results.jsonl`: `3782b472ff47f1322cae5c14300a64743f219f251eaf25403699fc36961be6ef`.
- `/mnt/raid0/llm/tmp/ak-dtree-diag-gpu-20261120/out/logs/dbg-a3b.log`: `ca33315f193b86c647a05e8a1a3f500c8c725d6e433b6eeefb6cc5b6c53cf48c`.
- `/mnt/raid0/llm/tmp/ak-dtree-diag-gpu-20261120/out/logs/dbg-27b.log`: `0cc4d6f67179de715c573919c1e537f8c87969e8e04931e71cdcbd691deff274`.
