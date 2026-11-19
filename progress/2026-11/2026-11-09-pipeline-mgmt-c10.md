# 2026-11-09 pipeline-mgmt: C10 / AITER-PORT-1

- Filed c10-gemmdown-prefill-ab-20261109 KEEP (27B pp2048@d32768 1.127x vs C9); AITER-PORT-1 box stays open for the quality gate.
- c9-q38fn-cpu-ppl-20261109 found vacuous (no GGML_IQK=1); republished as -r2. c10-gemmdown-correct-20261109 never ran (smoke held no VRAM); republished as -r2.
- C10 fold candidate branch llama.cpp-experimental-c10-fold-20261109 @ 7f1bd044b; manifest rows V11-136..140; box C10-FOLD-GATE; rows c10-fold-build / -gate / -cpu-gate published.
