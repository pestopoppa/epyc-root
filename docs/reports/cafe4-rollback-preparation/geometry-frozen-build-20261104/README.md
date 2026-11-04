# CAFE-4 frozen matched-geometry diagnostic build

Scheduled cafe4-v10-geometry-holdout-frozen-build-20261104 ended rc0 at 2026-11-04T15:23:19Z. The native build receipt binds v10 ffc1bac82, target diagnostic patch, corrected V5 candidate/bridge, frozen token header and nine-prompt manifest, compiled geometry/MTP/load/rewind markers, artifact hashes and local library linkage. Executable SHA-256 4b779db62ab261f64316a4868e9c445b18306adb62de5c6b0107600fb0dde1a4. This meets the build-only rule; binaries and DSOs were hardlinked at /mnt/raid0/llm/tmp/df2/cafe4-geometry-v5-preserved/ before filing.

The eight held-out native controls, matched numerical references, fault sensitivity and parent CAFE-4 verdict remain untested. The existing CPU candidate leaves context threads at v10 default four; a CPU-quarter allocation must not be represented as an effective 24-thread context without runtime evidence.
