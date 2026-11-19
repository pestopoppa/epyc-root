# CAFE-3 CPU r2 build qualification

FAIL full CPU build qualification: scheduled rc1 at 2026-11-19T20:48:09Z; no RESULT.json. Configure, cmake build and ldd supervisor reports all record command-exit child_rc=0, no captured children, drain not-required. Build reached 100% linked llama-server. Driver output explicitly refuses missing required libraries. Local linkage records libllama.so.0, libggml.so.0, libggml-base.so.0 and libggml-cpu.so.0; validator requires unversioned SONAME strings. This establishes a qualification validator mismatch, not a compiler failure or P9 performance verdict. Parent CAFE-3 remains open.

The row decision rule requires a validated full receipt. A successful compiler exit alone does not satisfy it. The exact local-path and artifact-hash checks must remain when the validator learns the versioned library identities. Apply the same repair to CPU and HIP validators, with refusal regressions, before publishing new packets. Leave the already-armed HIP packet unchanged; file its result when delivered. No native inference ran.

Evidence references (original files, no copied logs or binaries):

- `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe3-full-cpu-build-r2-20261119.ended` — SHA-256 `2fd7c722a32401eff02add4c1aa5635a208cd3d0208e0c2966c6c6a8b5945f98`.
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-full-cpu-build-r2-20261119/state/df2-cafe3-full-cpu-build-r2-20261119.fenced-job.out` — SHA-256 `a9f21fa118980eb4373b7a8c32a7198c3b645f0909459c21254bf48607e7a0c0`.
- `/mnt/raid0/llm/tmp/df2/cafe3-cpu-build-r2-20261119/runs/build-i2r4n_hy/build.supervisor.json` — SHA-256 `29fa3ead8d6c63c5acba7bd7e3f0eba3b65d55d4bf6b62c464e473d3086faefc`.
- `/mnt/raid0/llm/tmp/df2/cafe3-cpu-build-r2-20261119/runs/build-i2r4n_hy/configure.supervisor.json` — SHA-256 `a18771375f15eb77d1fe0ec0a6f60dfd09ebe34ac653ab87cffb42e8a6358585`.
- `/mnt/raid0/llm/tmp/df2/cafe3-cpu-build-r2-20261119/runs/build-i2r4n_hy/linkage.supervisor.json` — SHA-256 `f24cebe8c5e997a46bbdfab2f3839cbe8b5da245b882446cb2b362431315a072`.
- `/mnt/raid0/llm/tmp/df2/cafe3-cpu-build-r2-20261119/runs/build-i2r4n_hy/linkage.log` — SHA-256 `22d020042c7b24718476dbba0cebdc2fcd09e75a0fd1b859af7d862a7f638152`.
- `/mnt/raid0/llm/tmp/df2/cafe3-cpu-build-r2-20261119/runs/build-i2r4n_hy/build.log` — SHA-256 `a22583284c443d7e3e5c1243351cf1aae727ae652742860916c354d85b0ecfae`.
- `scripts/diagnostics/cafe3-build/driver.py` — SHA-256 `d6893be6db6c5eed771c0eec2aea8099c8e21c60c4ced504ae877b92e3124e3d`.

[no-belief: build qualification failure and validator diagnosis only]
