# Parakeet CPU observer canary preparation — 2026-10-27

Prepared and main-reviewed the one-clip owner-run calibration in `artifacts/operator/parakeet-cpu-observer-canary-20261027/`. The frozen CPU CLI initializes KFD even with `-ng`; its earlier false KFD rejection remains HELD. The observer checks actual same-process CPU device, scheduler, host weights and sampled per-process VRAM and mapped-library pins. Fake CPU/KFD and failure controls passed, as did source-bound first-effect preflight and synthetic normal admission for CPU 24–25. No actual audio inference was run during preparation.

The 40-clip CPU reference remains NOT READY until the native canary succeeds and the v2 writer is maintained and registered. Its existing `-t 1` recipe and exact transcript comparison are unchanged. No WER, quality or performance finding is asserted.
