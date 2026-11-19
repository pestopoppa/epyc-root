# KVU-11c host ASan build

Fresh build-only packet for detached qwentts and ggml commits; compiler, tools and scripts are pinned. The smoke configures HIP and builds only the host-ASan base library. The full row requires host ASan markers in server and ggml DSOs, own linkage and hashes. It runs no model or GPU workload and makes no device instrumentation claim. Runtime outputs remain under the packet scratch directory.
