# KVU-19a-2 candidate tile source, 2026-11-01

This capsule preserves a candidate source for the historical branch-sensitive gfx90a investigation. The base tile byte-matches `git show 90c12df42:ggml/src/ggml-cuda/fattn-tile.cuh`; the candidate was recovered from `/mnt/raid0/llm/tmp/fa-maskskip-20261003/fattn-tile.cuh.patched`. Its added `KV_live_ptr` and KV-loop conditional branches match the historical description, but neither file is bound to the retained historical binaries or outputs. This is not a reproduction or proof of an upstream defect.

`candidate.patch` was generated from the two retained source files and independently applied to a temporary copy of the base, reproducing the candidate byte-for-byte. The candidate adds an interface argument and references `flash_attn_kv_chunk_is_dead`; its companion changes and build compatibility remain unverified. Do not substitute it into the frozen production tree.

Next, recover and bind compatible companion source, prospectively identify full baseline and candidate trees, toolchain and ELF/library hashes, and prepare a keeper-scheduled repeated identical-input GPU comparison with native output and residency custody. Different outputs across unidentified historical runs do not establish within-binary nondeterminism. No build, GPU execution, or external report was performed in this preparation.
