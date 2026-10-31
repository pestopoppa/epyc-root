# C5 CPU post-link R6 — 2026-10-31

### 2026-10-31 C5 CPU post-link R6

`refactor-akxall8-c5-cpu-build-r6-20261031` completed rc0, recovering the original R5-linked C5 image `c72ec82f5417bb2937310326120f149b665e8400` after R5's host `rg` failure. The actual host `IDENTITY.json` and all eight listed server/library hashes revalidate; `GGML_FA_SPLIT_KV`, `GGML_FUSED_DECODE_OFF` and `GGML_FUSED_DECODE_ON` are present, and host `ldd` resolves the ggml/llama libraries from this build's own bin directory. The recorded server version is 10419. The factual target-card digest matches and its status is `built_unenrolled`; its declared fresh-store path does not presently exist and is a prospective declaration, not a deployed store. The CMake UI npm warning was nonfatal; no UI behavior is claimed. This is model-free build/post-link evidence only, not timing, serving equivalence, calibration or keep. [Identity, card and bounded audit](../../artifacts/compute/codex3-c5-cpu-r6-20261031/). [belief: cc]

No scientific checkbox changed.
