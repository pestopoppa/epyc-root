# KPF-17 same-UID custody qualification packet

Prepared only; no fixture, publisher smoke or granted run executed. No row published.

The copied custody.py and binding.json match the retained r5 packet at /mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf17-oracle-r5 byte for byte. This runner imports that unchanged implementation and invokes validate_maps. Two private, deterministic fixture windows cover mutation before revalidation and after the last accepted check. The post-check case retains UNSAFE if a mapped data read sees overwritten bytes through a private same-UID hardlink. Qualification completion is not a safety pass.

This packet cannot establish native ELF loader behavior, build_identity coverage, model correctness, inference behavior, or whole-chain safety. Synthetic proc-map lines are paired with a non-ELF mmap data witness; they are not a live native process map capture. Shared build/runtime artifacts are never mutated.

The only authorized in-turn execution is the owning session's publisher smoke; this preparation does not execute it. Scratch: /mnt/raid0/llm/tmp/kvfork/kpf17-sameuid-custody-qual-20261105. Run output: out/RESULT.json with fresh out/attempt.json and nonce-scoped cases.json; smoke output uses FILLER_DRYRUN_RESULT_PATH and separate smoke-out. The wrapper completion predicate accepts only full out/RESULT.json with all source/evidence/attempt seals and the explicit UNSAFE outcome. STOP is checked before atomic result replacement; this is a sampled local-file stop check, not a proof against same-UID mutation after that check or full-wrapper stop precedence.

GitNexus status: lane unindexed. Upstream impact for validate_maps against /workspace returned UNKNOWN (symbol absent; index 5241 commits stale), so no graph blast-radius assurance is claimed. No retained function or existing caller is modified; the packet is a new isolated caller.
