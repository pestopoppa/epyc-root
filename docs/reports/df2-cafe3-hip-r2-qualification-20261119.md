# CAFE-3 HIP R2 build qualification

FAIL full HIP build qualification: scheduled rc1 at 2026-11-19T21:52:11Z; no RESULT.json. Configure, build and ldd supervisor records each show command-exit rc0, child_rc0, no captured children and drain not-required. The build log reaches 100% linked llama-server. The fenced job output explicitly reports `CAFE3 BUILD REFUSED: missing required libraries`.

The retained driver requires unversioned library names; linkage records local numeric SONAMEs including libllama.so.0, libggml.so.0, libggml-base.so.0, libggml-cpu.so.0 and libggml-hip.so.0. This is the same qualification-validator mismatch as CPU R2. Compilation success alone does not satisfy the row's validated-receipt decision rule. No native inference, GPU residency, token identity, speed or P9 verdict follows. CAFE-3 remains open.

The SONAME repair and refusal tests are already landed, and replacement HIP R3 is running. Do not change the sealed R2 packet or publish a duplicate replacement. See `scripts/diagnostics/cafe3-hip-build/README.md` (SONAME-repaired build publication, 2026-11-19).

Evidence references (existing files; no copied logs or binaries):

- `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe3-full-hip-build-r2-20261119.ended` — SHA-256 `d67d6cfae244276eecbf5089854bea67155aafb96d554c439e43e1e9ad1c799f`.
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-full-hip-build-r2-20261119/state/df2-cafe3-full-hip-build-r2-20261119.fenced-job.out` — SHA-256 `a9f21fa118980eb4373b7a8c32a7198c3b645f0909459c21254bf48607e7a0c0`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r2-20261119/driver.py` — SHA-256 `a3c426fcb758326ef56f811d69adadcc5ea37d42d5e6405cd9471b0d20cd03b8`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r2-20261119/runs/build-ojk54iax/configure.supervisor.json` — SHA-256 `b6864c6bed1a78833111bff0dd065fd0727a778310bfdaf56f09bdc87b0f756f`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r2-20261119/runs/build-ojk54iax/build.supervisor.json` — SHA-256 `4bb3ccb722b89b7fb35f9b02312d38a772c6aaca1ec1d2712869f6c63d6e30d0`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r2-20261119/runs/build-ojk54iax/linkage.supervisor.json` — SHA-256 `976bf31cd3e1317dadf8824fb1388bf66c33d7297dd328db90350201379b7997`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r2-20261119/runs/build-ojk54iax/linkage.log` — SHA-256 `16e53d60543124357a0ee7e713d20043ef177375fd928d83fe07718921f1baff`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r2-20261119/runs/build-ojk54iax/build.log` — SHA-256 `ec00146b7667a5ce236a8a5dc7901778594f6e91248efd166a22fdb6bf961b2b`.

[no-belief: build qualification failure and validator diagnosis only]
