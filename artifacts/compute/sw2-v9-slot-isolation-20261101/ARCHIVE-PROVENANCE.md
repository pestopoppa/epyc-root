# cpu-20260810-0db32c06e — frozen production v9, CPU surface

Materialised 2026-09-21 by copying `/mnt/raid0/llm/llama.cpp/build/bin` (the frozen
production-consolidated-v9 source tree's artifact directory) into a VERSIONED build dir.

**Why this exists.** `kernels/production/cpu` pointed INSIDE the frozen source tree, at an
accretive artifact directory holding five library generations side by side
(`libllama.so.0.0.1012{1..5}`), which each build overwrites in place. The freeze runbook's step 6
says to archive "the old build dir" — there was none, so step 6 had never been executable and
`kernels/archive/` had been empty since the store was created on 2026-07-31.

- commit `0db32c06e3e550065b78311a6031ef3dd2c4f27c`, build **10125**
- `llama-server --version` verified: `10125 (0db32c06e)`
- `RUNPATH=$ORIGIN` — relocatable, so the copy is self-contained
- `verify_ggml_linkage.sh` PASS under `env -u LD_LIBRARY_PATH`
- `llama-server` sha256 IDENTICAL to the source-tree original (verified at copy time)
- the copy preserves all five library generations exactly as the source dir had them; the
  unversioned soname symlinks resolve to 10125
