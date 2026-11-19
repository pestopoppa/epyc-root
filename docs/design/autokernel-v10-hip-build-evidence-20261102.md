# v10 GPU build configuration evidence

The production GPU symlink resolved on 2026-11-02 to
`/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin`. Its parent
`PROVENANCE.md` identifies commit `ffc1bac82`, build 10303 and promotion on
2026-09-22. The provenance file SHA-256 is
`a0e1870be9b043ac7cf0e3ca74b3835a5757c8641d5714321b512f942a9381ee`.

The adjacent `CMakeCache.txt` SHA-256 is
`81b3488deaeae05f0758dd6f092117951cacc0b36b9695106e1d3d5f81ed4581`.
It records `CMAKE_BUILD_TYPE=Release`, `AMDGPU_TARGETS=gfx90a`,
`BUILD_SHARED_LIBS=ON`, `GGML_HIP=ON`, `GGML_CPU=ON`, `GGML_NATIVE=ON`,
`GGML_HIP_GRAPHS=ON`, `GGML_HIP_MMQ_MFMA=ON`, `GGML_HIP_NO_VMM=ON`,
`GGML_HIP_ROCWMMA_FATTN=ON`, `GGML_HIP_RCCL=OFF`,
`LLAMA_BUILD_SERVER=ON`, and `LLAMA_BUILD_TESTS=ON`. The recorded HIP compiler
path is `/opt/rocm/lib/llvm/bin/clang++`; C and C++ compiler paths are
`/usr/bin/cc` and `/usr/bin/c++`.

This is an inspected cache, not a complete reconstruction of the original
command, the compiler version at build time, or content proof for a new build.
Use the full cache and compilation commands to prepare and review a candidate
configuration; capture fresh tool identities, source identity, explicit options,
output digests, and linkage in the candidate build receipt. The production
provenance records an empty trailing RUNPATH element: the candidate must avoid
or explicitly account for it. No production files were changed and no build or
inference was run.

The same cache records the `Unix Makefiles` generator and
`CMAKE_BUILD_RPATH_USE_ORIGIN=ON`. Release flags for C, C++ and HIP are
`-O3 -DNDEBUG`; `GGML_BACKEND_DL=OFF`, `GGML_LLAMAFILE=ON`, and
`GGML_CCACHE=ON` while its cache lookup reports `NOTFOUND`. These are recorded
configuration values, not evidence that the current host has the historical
compiler versions or that a new build will reproduce the production binary.
