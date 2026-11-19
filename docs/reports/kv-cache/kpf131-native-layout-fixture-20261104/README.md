KPF-13.1 native-layout model-free prerequisite — revised 2026-11-04

Files in `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf131-native-layout-prep/`:
- `native_layout.py`: bounded parser for the captured textual `find_slot` grid and bound comparator.
- `test_native_layout.py`: synthetic positive case plus malformed header, grid, mapping, task/request/slot, receipt, allocator-count, owner and batch-partition controls.

Historical source check: exact image source commit `a1f0c8cf9bd7102415a72577474f307b8ba94db9` defines `get_used()` as `used.size()` and `used_max_p1()` as last used cell index + 1, or zero when empty (`src/llama-kv-cells.h`, SHA-256 `d9ab701ef4286b26bbd9ba8fc5de8162b647215cda7d4116b9caeae7a47b7d6d`); its `find_slot` debug line prints those values with head and cache size (`src/llama-kv-cache.cpp`, SHA-256 `a9aa9460b36e00123ede2fb22596fee648679f729ab17043b6c98e3f530064bc`). The parser now requires head and used_max_p1 <= size, grid occupied-cell count == used, and used_max_p1 == last occupied grid index + 1 (zero for empty). Negative occupied positions are INVALID; `.` remains the empty marker. Sparse occupied-cell fixture checks distinguish count from high-water index.

Evidence classification: absent/incomplete mappings, receipts, batches, allocator metadata, or unattributable multi-owner cells return UNKNOWN without a proof digest. Contradictory observed values return INVALID. MATCHED is emitted only for complete synthetic fixture bindings. The 262,144-cell parser ceiling is explicitly a local safety cap, not a proven historical cache geometry; larger otherwise-valid grids return UNKNOWN. A real log may contain repeated per-sequence/per-stream snapshots; decoding one complete textual grid does not bind it to a request/task/stream. The caller still must establish that exact scope.

Validation: `PYTHONDONTWRITEBYTECODE=1 python3 -B test_native_layout.py -v` — 29/29 passed, including header bounds/count/high-water mutations, negative positions, oversized UNKNOWN, incomplete receipt UNKNOWN, missing batch UNKNOWN, differing batch INVALID, and equal-but-malformed direct caller grids.

Limit: this is synthetic parser and binding plumbing only. It does not validate actual native output, the physical cache ABI, the correct live stream selection, or a runtime adapter. No inference, publisher, gate bypass, grant, or `NATIVE-ADAPTER-VALIDATED` marker was used or changed.
