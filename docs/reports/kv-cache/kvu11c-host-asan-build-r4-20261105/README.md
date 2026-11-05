# KVU-11c host ASan build

Fresh build-only packet for detached qwentts and ggml commits; compiler, tools and scripts are pinned. The smoke configures HIP and builds only the host-ASan base library. The full row requires host ASan markers in server and ggml DSOs, own linkage and hashes. It runs no model or GPU workload and makes no device instrumentation claim. Runtime outputs remain under the packet scratch directory.

R2 successor to kvu11c-host-asan-build-20261105, which stopped on unpinned ldd. Reuses the same detached source worktrees and additionally pins ldd, sed, and the Clang ASan runtime.

R3 adds a full-build binary proof of the source-bound --threads <n> option marker. R2 is held by STOP.

R4 retains the source lineage and proofs. Its supervisor ignores pidfds already readable as exited during capture, but rejects live identity or parent changes; adopted descendants remain swept and individually signaled. R3 failure evidence is preserved under r3-failure-evidence.
