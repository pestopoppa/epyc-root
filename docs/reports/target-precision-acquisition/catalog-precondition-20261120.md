# Target-precision catalog precondition — 2026-11-20

The pinned BF16 and non-UD Q4_K_M artifacts do not have identical tensor catalogs. Complete catalog reads of bounded 16 MiB prefixes found 835 + 31 = **866 BF16 tensors**, versus **851 Q4_K_M tensors**. The two BF16 headers declare split numbers 0/1, split count 2, and total 866. The 15 tensors present only in BF16 are the `blk.64.*` block, including `blk.64.nextn.*`. All 851 shared names have equal dimensions. This is a structural precondition finding; it does not prove a runtime confound when next-token prediction is unused, weight equality, tokenizer equivalence, exact base revision, or a target-precision cause.

The bounded prefixes cover complete catalogs: aligned tensor-data starts are 10,994,688 and 1,984 bytes for BF16, and 10,994,112 bytes for Q4_K_M. Source revisions and full-artifact expected hashes remain in [the pinned manifest](source-manifest.json). Both pinned API records name `Qwen/Qwen3.8-27B`; neither captured record binds that base to an exact revision. The precondition stays unresolved, so no matrix is published and the parent box remains open.

`compare_catalogs.py` uses the existing GGUF reader with tensor-payload construction disabled. It compares complete name/shape sets, refuses duplicate tensors and incomplete split sets, and always leaves the causal precision gate unresolved. Twelve structural controls pass; together with the downloader suite, **20 tests pass**. Catalog equality can never pass the causal gate on its own.

The durable pinned acquisition was started separately (captured PID 2380584). Its completion/failure event is `/mnt/raid0/llm/tmp/df2/target-precision-acquisition/result.json`, registered in df2 awaiting state. No transfer success or full-artifact integrity is claimed here. On success, determine whether the unused MTP block can be held consistently inactive across arms, establish exact base/weight provenance (or derive matched quantizations from a single pinned source), inspect the existing Q8 arm, and finish the write-time binding prerequisite before preparing the CPU matrix.

Evidence remains in place (SHA-256):

- `/mnt/raid0/llm/tmp/df2/target-precision-source-review/catalog-0.json`: `7aa8028459a80d5d630ee2e7f16838fd5579ac03d4b58fe921a2ef00600c4bb8`.
- `/mnt/raid0/llm/tmp/df2/target-precision-source-review/catalog-1.json`: `5eae4e0944cbf3fcc97ad0b43622afb855eca44b78bc0d5b523ac93e7330eb0a`.
- `/mnt/raid0/llm/tmp/df2/target-precision-source-review/catalog-2.json`: `69b5a0d631ec8fbb6719f12b0dae1a5f9a93c3802ac7202a176918a7f705652a`.
- `/mnt/raid0/llm/tmp/df2/target-precision-source-review/catalog-precheck.json`: `db2e967793a1c6f77c5bdb1a3393347e578a34d1a18fc77bedbfb6a7a072f581`.
- `/mnt/raid0/llm/llama.cpp/gguf-py/gguf/gguf_reader.py`: `91cb9e81f1a67f5856f012cf3f526ad9ffdb6b887d2aa66e2593ee6f63764aad`.
- `/mnt/raid0/llm/tmp/df2/target-precision-source-review/catalog_probe.py`: `f8d13f37b39782f37e55c8e5c860c84f74c649361dde60a28994772b273a4827`.
