# KPF-60 fixed F16 writer-byte oracle

This independent, fixed 152-byte oracle targets the proposed native fixture at
`kpf60-native-fixture-prep-20261104/test-kpf60-cache-fixture.cpp`: two layers,
F16 K/V rows of eight bytes, physical cells 1, 2 and 5, non-transposed V, and
the fixture's deterministic per-layer/per-tensor byte pattern. It compares the
entire little-endian `state_write_data` data section, including headers, and
reports the first mismatch. `GGML_TYPE_F16` is 1 at pinned source 8952a0f.

Run `python3 oracle.py <captured-data-blob>` after independently capturing the
writer output. Exit 0 means all bytes match; 1 means mismatch; 2 means input
could not be read. The present native fixture checks length only and does not
yet emit this blob, so no native comparison has been performed.

The tests construct synthetic bytes independently, mutate every byte, reorder
and duplicate equal-length payloads, and check truncated input and CLI errors.
They do not establish native writer correctness, real cache geometry, hybrid or
GPU behavior, source/build custody, or transfer. This oracle is deliberately
fixed to the declared little-endian fixture and must not be generalized to
other lengths, types, transposed V, layouts, or byte patterns.
