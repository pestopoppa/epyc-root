# PF1 C6 llama-bench load-thread CLI build

This is a separate, unpublished build prerequisite for PF1-EXPAND. The only source change is in
`../source/tools/llama-bench/llama-bench.cpp`; the worktree is detached at C6 commit
`729599d69871181d67af715a4c2f9162d5153a2e` and its base tree is
`51b0a4fda906ffd3d029fd21bf41204675f08167`.

The pinned C6 `include/llama.h` already exposes `llama_model_params.n_load_threads`:
`0` selects auto, `1` selects the single-thread path, and values above one select that many
readers. `src/llama-model-loader.cpp` consumes it for non-mmap host-buffer reads. The C6
`llama-bench` parser did not expose this field. The proposed `--load-threads <n>` option wires it
through at model load time; existing `-t` / `--threads` remains the runtime benchmark thread
count. The load setting only affects the intended `--mmap 0` path.

`BUILD-INPUTS.json` captures the exact approved C6 CPU and GPU build configure arguments, replacing
only source and output directories with this scratch worktree and isolated output directories.
The native dry-run configures a separate CPU smoke tree with `compile_commands.json`, then compiles
the actual patched benchmark translation unit and writes its real ELF object hash and numeric
object count to `FILLER_DRYRUN_RESULT_PATH` only after compiler success. The full job builds only
the `llama-bench` CMake target with four jobs for both backends, in separate `build-cpu` and
`build-gpu` trees, then verifies that each compiled `--help` accepts `--load-threads 1`.

The full job checks captured compiler/tool hashes and both existing C6 stores' source identities,
library hashes, and `SHA256SUMS` before and after. The final `BUILD-RECEIPT.json` binds both base
build identities and configure arguments, the shared source and patch, exact output configure/build
commands, output binaries, and their linked library hashes. No existing kernel-store path is a build
output.

`ROW-PROPOSAL.json` and `launch.sh` are an unpublished CPU4 build-row proposal. This agent did not
invoke the launcher, build anything, run inference, or publish a row. The build remains a
diagnostic candidate and does not promote C6 or authorize production changes.

Owner publication: native four-CPU smoke PASS compiled the actual patched benchmark TU into a validated x86-64 relocatable ELF object. The full CPU/GPU builds and compiled help witnesses remain pending. Source C6 is proven to contain frozen production ffc1bac82; the detached source plus one-file patch is diagnostic only. Nothing was built in the production tree or installed into the kernel store.
