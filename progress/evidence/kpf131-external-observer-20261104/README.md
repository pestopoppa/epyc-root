# KPF-13.1 historical-image external observer feasibility

Result: PREREQUISITE_ONLY. The model-free own-child probe installed two hardware breakpoints in the unchanged historical libllama, at llama_max_devices and llama_kv_cache::find_slot. The single max-devices call hit exactly once; child exited 0. Before that call, five actually mapped llama/ggml DSOs matched the pre-run current-image pins. These are current mappings, not reconstructed historical DSO custody. No model was loaded or inference run. max-devices may initialize/enumerate the HIP runtime; it is not a GPU-residency measurement.

The old image has function symbols but no DWARF types. seq_pos_min disassembly demonstrates that concrete ABI offsets can be inspected in the actual old binary (e.g. stream/cell traversal); the offsets are NOT a validated decoder. A GDB source-level cast based only on matching source headers would be insufficient. Hardware breakpoints avoid the native instrumentation derivative and do not patch inferior instructions. The historical cache allocator breakpoint was installed but NOT HIT: no cache existed in this model-free fixture.

This makes an external observer technically plausible and disproves any inference that missing native trace markers alone imply impossibility. It does not implement the requested physical-layout witness. The scientific gate remains NOT_READY: physical prefix cells, used layout, allocator head, server task/request identity and batch rows have not been observed or independently decoded. No historical cell can be rejudged from this packet. Original FAILs remain unchanged.

The complete validation requirements are predeclared in PREDECLARATION.md: prove raw old-image ABI from machine code; validate native memory fixtures with placed owner/head/row mutations; observe allocator and decode boundaries and exact task/request binding; retain current mapped DSO custody throughout each run; predeclare five-cell and acceptance decisions separately. This is implementation work, not an operator decision.

Artifacts: RESULT.json and native.json record the single real probe. probe.executed.py is the exact executed script and its SHA matches RESULT.json. probe.py adds a post-probe one-shot refusal to prevent accidental evidence reuse and has not been rerun. pins.json, probe.gdb, fixture.py and raw GDB outputs are retained. seq_pos_min.disassembly.txt is retained offline old-image inspection. The raw readelf section listing was omitted from this durable packet after a commit scanner flagged zero-filled hexadecimal fields; its SHA-256 is `8e5543183c947b2c2e0de271442b9d68a0d789d03f9116e2e33ad51c52329c74` and it can be regenerated from the pinned historical library. No handoff, index, commit, run row, or inference dispatch was changed.

Validation: 9 unittest cases pass, including missing/changed/unpinned mapping, missing required fields, absent/extra hits, failed child, altered library pin, missing library and repeated exposure refusal. The real prerequisite run is separate from these offline tests. Full layout-observer validation is absent. Prior historical audit remains authoritative about readiness.

Reproduce offline checks from this directory:

```bash
python3 -m unittest discover -s progress/evidence/kpf131-external-observer-20261104 -p test_probe.py -v
```

The preserved probe.gdb contains original scratch absolute paths and is retained as execution evidence. probe.py generates paths for its own directory. Its one-shot guard refuses this exposed evidence directory. A future model-free reproduction must copy source and declaration into a new scratch directory without native.json/RESULT.json, review the declaration, and run probe.py there; it will re-pin current DSOs and is a new prerequisite observation. Never run inference or claim a layout witness from this packet.
