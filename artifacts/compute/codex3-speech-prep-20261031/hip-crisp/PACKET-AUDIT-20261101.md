# CS-8.STT4 CrispASR HIP packet audit — 2026-11-01

Scope: static audit of the held row packet and recorded fixtures. No build, inference, grant, row publication, or GPU activity was performed.

## Build state and work units

- The retained `/mnt/raid0/llm/tmp/codex3-cs8-stt4-crisp-20261031/BUILD-PARTIAL` contains `disk reserve`. There is no `BUILD-SUCCESS` or full HIP build result.
- `qualified-smoke.log` and `SMOKE-OBJECTS.sha256` show a model-free `ggml-hip` object compile passed. `STOP-TEST-PUBLISH.log` records a direct build-guard STOP cutoff (rc 75), compiler observation, child drain, and captured PID absence.
- The current `build-guard.py` full mode invokes default `cmake --build`, which builds the `all` target and includes unrelated project targets. Source CMake names the runner target `crispasr-cli`; the HIP backend target is `ggml-hip`. A successor should build these explicit targets and their dependencies, then install/link-check the intended runner.
- The existing CMake cache and generated makefiles embed the missing old source path. They cannot be resumed unchanged after source restoration; configure a successor build tree against the restored source.

## STOP boundary

- The published `launch.sh` hash binds `filler_run13.sh`; it does not establish the currently held `launch.v15.sh` behavior.
- `launch.v15.sh` points to rowflow `filler_run15.sh`. Static inspection shows a pre-start STOP-file check and propagation of the same stop path into the inner launcher. The filed STOP fixture exercises `build-guard.py` directly, not rowflow's granted launcher boundary. Treat rowflow STOP as unverified until a model-free dry-run/fixture covers the actual launcher path.

## Source seal

- The published manifest points to `/mnt/micron/codex3-cs8-stt2-crisp-20261030/src`, which no longer exists.
- The restored `/mnt/raid0/llm/tmp/codex3-cs8-stt2-crisp-20261030/rebuild-src` is clean at pinned commit `2aa8d7669fcaa18d98d61a4bc8a077464e6b9919`.
- All 7,249 listed entries verify when only the source root is substituted with `rebuild-src`. The prospective substituted-manifest SHA-256 is `1c98abd305af44a3a810b5435de2e318aa0f371b23a3485629c44d3c58ab98a1`. This is an audit digest, not a published READY seal; launcher/job/guard hashes and generated build metadata must be resealed for a successor packet.

## Current outcome

The row remains open and the held READY artifact remains unchanged. The prior disk-reserve cutoff, missing source path, stale CMake source binding, default-all build scope, and absent rowflow STOP fixture are concrete successor-preparation defects. No HIP residency or transcript parity evidence exists.
