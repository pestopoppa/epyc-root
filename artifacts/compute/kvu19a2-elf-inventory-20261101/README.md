# KVU-19a-2 ELF inventory component

This utility hashes the ELF files actually present under an identified build root, with sizes and deterministic paths. It detects file changes during reads, refuses symlinked directories and escaping or dangling file symlinks, and does not double-count internal library symlinks. Four synthetic tests pass; no build or inference has run.

This is a component for the future producer, not a rowflow launcher or a build receipt. It does not bind the files to a source commit, establish that all expected ELFs exist, prove ggml linkage or actual dlopen residency, secure a changing directory tree against concurrent mutation, or verify inherited toolchains. Run only after a captured build completes with an owned stable output tree; independently verify source/recipe custody, expected binary set and runtime linkage. No claim follows from the tool alone.
