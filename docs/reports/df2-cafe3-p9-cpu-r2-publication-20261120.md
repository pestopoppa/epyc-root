# CAFE-3 CPU P9 repaired scheduler publication — 2026-11-20

Published `df2-cafe3-p9-cpu-r2-20261120` with **smoke PASS**, cores **116–119**, rc0 at **11:30:24Z**. The standard publisher refused reuse of terminal `df2-cafe3-p9-cpu-20261119`; its original grant/result custody is preserved. The retry reuses retained scratch and qualified R4 build, with a new row identity.

The packet now contains the repaired `multi_arm.py` from root commit `ee5698c211fa28180e956ef96667555abdc51f93`, SHA-256 `b7d9a87f87cbe1dfdd7a014a412c10983e41eab687dcdc4af4ececa3c357e962`. Resealed its runtime entry, inventory, three launcher commands and predicate. Publication binding check PASS. No source tree, model, binary or log copied into evidence. Models, corpus, full-build receipt, protocol, five-arm schedule and P9 gates remain as previously qualified.

Smoke runs the compiled server CLI without model load. It establishes publication qualification only; native token identity, request-wall throughput and zero-state recovery remain unassessed. P9 requires identity 100%, adaptive throughput >=1.01 times the fastest static width 0..3 (higher is better), and post-exploration recovery within 128 rounds. Parent CAFE-3 stays open pending native results.

Evidence retained in place (SHA-256):

- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/inputs.json`: `92c7388781d4ec0d02fa31559358d33be48b05de061f8044e83c704955cd1079`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/launch.sh`: `b123920679caa25b89d73ca03581b5aebffa8a14117175335585ad6592f66241`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/spec.json`: `716d37f72235624935969f50847267dbbdcfb6634d84a6d8aa093b7d6f8a6d7c`.
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-p9-cpu-r2-20261120/PASS.json`: `4ed4e1324090592935cd8dfa369c828553ce808768f0dafc3ec0ca0bd42a7687`.

GitNexus status and impact were unavailable because the lane is unindexed. Packet-only change: scheduler API repair plus bindings; no kernel/build/policy changes.

[no-belief: publisher smoke qualification only; no native P9 verdict]
