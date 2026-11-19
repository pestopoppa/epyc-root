# KVU-11c HIP build packet

This is the retained source snapshot of the published scratch packet. Its launcher and integrity manifest intentionally refer to `/mnt/raid0/llm/tmp/kvfork/kvu11c-hip-build-20261104` and its detached qwentts/ggml source worktrees; the checked-in copy is not a replacement runtime seal. Publisher smoke builds only `ggml-base` on four CPUs. The full build must verify its own ggml linkage, `--threads` marker, and binary/library hashes. It is not GPU execution, a speech quality result, or a production promotion. The normal disk floor remains in force.
